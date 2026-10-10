"""Inicia Integrated Web en localhost con acceso al compilador/subidor local."""

from __future__ import annotations

import codecs
import json
import mimetypes
import serial
import socketserver
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import serial.tools.list_ports
from serial.tools import list_ports

import build_manager as build
from placas import fqbn_de, nombres_placas

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
PUERTO_INICIAL = 8765
_CARGA_LOCK = threading.Lock()
_SERIAL_MONITOR_LOCK = threading.Lock()
_SERIAL_WRITE_LOCK = threading.Lock()
_SERIAL_MONITOR = None


class IntegratedHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "public, max-age=0")
        super().end_headers()

    def do_GET(self):
        ruta = urlsplit(self.path)
        if ruta.path == "/api/serial/read":
            self._leer_monitor_serial(parse_qs(ruta.query))
            return
        if ruta.path == "/api/ports":
            if not self._origen_local_valido():
                self._json(403, {"error": "Origen no permitido"})
                return
            puertos = []
            try:
                for puerto in list_ports.comports():
                    puertos.append({
                        "device": puerto.device,
                        "description": puerto.description or "Puerto serie USB",
                        "manufacturer": puerto.manufacturer,
                        "vid": puerto.vid,
                        "pid": puerto.pid,
                        "hwid": puerto.hwid,
                    })
            except (OSError, serial.SerialException) as error:
                self._json(500, {
                    "error": f"No se pudieron consultar los puertos serie: {error}",
                    "ayuda": "Revisa el controlador USB-serie y vuelve a iniciar Integrated Web."
                })
                return
            if not puertos and sys.platform == "win32":
                puertos.extend(self._puertos_registro_windows())
            self._json(200, {
                "puertos": puertos,
                "placas": [{"nombre": nombre, "fqbn": fqbn_de(nombre)} for nombre in nombres_placas()],
                "compilador": build.cli_disponible() or build.platformio_disponible(),
                "diagnostico": (
                    "Windows no reporta ningún puerto COM. Prueba un cable USB de datos, "
                    "instala el controlador USB correspondiente (CP210x, CH340 o el de la placa), "
                    "revisa el Administrador de dispositivos y vuelve a pulsar Puertos."
                    if not puertos else ""
                ),
            })
            return
        super().do_GET()

    @staticmethod
    def _puertos_registro_windows():
        try:
            import winreg

            clave = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DEVICEMAP\SERIALCOMM",
            )
            puertos = []
            indice = 0
            while True:
                try:
                    _, dispositivo, _ = winreg.EnumValue(clave, indice)
                except OSError:
                    break
                indice += 1
                if isinstance(dispositivo, str) and dispositivo.upper().startswith("COM"):
                    puertos.append({
                        "device": dispositivo,
                        "description": "Puerto COM detectado por Windows",
                        "manufacturer": None,
                        "vid": None,
                        "pid": None,
                        "hwid": "Datos USB no disponibles",
                    })
            winreg.CloseKey(clave)
            return puertos
        except OSError:
            return []

    def do_POST(self):
        ruta = urlsplit(self.path).path
        if ruta == "/api/launcher/background":
            self._poner_en_segundo_plano()
            return
        if ruta == "/api/serial/write":
            self._escribir_monitor_serial()
            return
        if ruta != "/api/upload":
            self._json(404, {"error": "Ruta no encontrada"})
            return
        if not self._origen_local_valido():
            self._json(403, {"error": "Origen no permitido"})
            return
        try:
            longitud = int(self.headers.get("Content-Length", "0"))
            if longitud <= 0 or longitud > 2_000_000:
                self._json(413, {"error": "El código está vacío o supera el tamaño permitido"})
                return
            solicitud = json.loads(self.rfile.read(longitud).decode("utf-8"))
            codigo = solicitud.get("codigo", "")
            placa = solicitud.get("placa", "")
            puerto = solicitud.get("puerto", "")
            fqbn = fqbn_de(placa)
            if not isinstance(codigo, str) or not codigo.strip():
                self._json(400, {"error": "No hay código traducido para cargar"})
                return
            if "// AVISO:" in codigo:
                self._json(400, {"error": "Corrige los avisos del traductor antes de cargar"})
                return
            if not fqbn or not isinstance(puerto, str) or not puerto.strip():
                self._json(400, {"error": "Selecciona una placa y un puerto serie válido"})
                return
            with _SERIAL_MONITOR_LOCK:
                if _SERIAL_MONITOR is not None:
                    self._json(409, {"error": "Cierra el monitor serial antes de cargar código a la placa."})
                    return
                if not _CARGA_LOCK.acquire(blocking=False):
                    self._json(409, {"error": "Ya hay una compilación o carga en curso"})
                    return
            try:
                self._iniciar_stream()
                self._cargar(codigo, fqbn, puerto)
            except Exception as error:
                self.log_error("Error preparando o cargando el programa: %s", error)
                self._emitir_evento({
                    "tipo": "resultado",
                    "ok": False,
                    "error": f"No se pudo compilar o cargar: {error}",
                })
            finally:
                self._cerrar_stream()
                _CARGA_LOCK.release()
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._json(400, {"error": f"Solicitud inválida: {error}"})
        except Exception as error:
            self.log_error("Error preparando o cargando el programa: %s", error)
            self._json(500, {"error": f"No se pudo compilar o cargar: {error}"})

    def _poner_en_segundo_plano(self):
        if not self._origen_local_valido():
            self._json(403, {"error": "Origen no permitido"})
            return
        if sys.platform != "win32":
            self._json(501, {"error": "La opción de minimizar el iniciador está disponible en Windows."})
            return
        try:
            import ctypes

            ventana = ctypes.windll.kernel32.GetConsoleWindow()
            if not ventana:
                self._json(200, {"mensaje": "El iniciador ya está ejecutándose sin ventana de consola."})
                return
            self._json(200, {
                "mensaje": "Iniciador minimizado. Sigue activo en la barra de tareas; restaura su ventana para cerrarlo."
            })
            threading.Timer(0.2, lambda: ctypes.windll.user32.ShowWindow(ventana, 6)).start()
        except (AttributeError, OSError) as error:
            self._json(500, {"error": f"No se pudo minimizar la ventana del iniciador: {error}"})

    def _leer_monitor_serial(self, consulta: dict):
        if not self._origen_local_valido():
            self._json(403, {"error": "Origen no permitido"})
            return
        puerto = consulta.get("puerto", [""])[0]
        try:
            velocidad = int(consulta.get("baud", ["115200"])[0])
        except ValueError:
            self._json(400, {"error": "Velocidad serial inválida"})
            return
        velocidades_permitidas = {9600, 19200, 38400, 57600, 74880, 115200, 230400}
        if velocidad not in velocidades_permitidas:
            self._json(400, {"error": "Selecciona una velocidad serial válida"})
            return
        puertos_disponibles = {entrada.device for entrada in list_ports.comports()}
        if sys.platform == "win32":
            puertos_disponibles.update(
                entrada["device"] for entrada in self._puertos_registro_windows()
            )
        if not puerto or puerto not in puertos_disponibles:
            self._json(400, {"error": "El puerto seleccionado ya no está disponible. Actualiza la lista de puertos."})
            return

        global _SERIAL_MONITOR
        with _SERIAL_MONITOR_LOCK:
            if _CARGA_LOCK.locked():
                self._json(409, {"error": "Espera a que termine la carga a la placa antes de abrir el monitor serial."})
                return
            if _SERIAL_MONITOR is not None:
                self._json(409, {"error": "El monitor serial ya está conectado."})
                return
            try:
                conexion = serial.Serial(puerto, velocidad, timeout=0.25, write_timeout=2)
            except (OSError, ValueError, serial.SerialException) as error:
                self._json(409, {"error": f"No se pudo abrir {puerto}: {error}"})
                return
            _SERIAL_MONITOR = conexion

        try:
            self._iniciar_stream()
            self._emitir_evento({"tipo": "estado", "mensaje": f"Conectado a {puerto} a {velocidad} baudios."})
            decodificador = codecs.getincrementaldecoder("utf-8")("replace")
            ultimo_heartbeat = time.monotonic()
            while conexion.is_open:
                datos = conexion.read(512)
                if datos:
                    texto = decodificador.decode(datos)
                    if not texto:
                        continue
                    self._emitir_evento({
                        "tipo": "datos",
                        "texto": texto,
                    })
                elif time.monotonic() - ultimo_heartbeat >= 1:
                    self._emitir_evento({"tipo": "heartbeat"})
                    ultimo_heartbeat = time.monotonic()
                if self._stream_desconectado:
                    break
        except (OSError, serial.SerialException) as error:
            self._emitir_evento({"tipo": "error", "mensaje": f"Se perdió la conexión serial: {error}"})
        finally:
            with _SERIAL_MONITOR_LOCK:
                if _SERIAL_MONITOR is conexion:
                    _SERIAL_MONITOR = None
            if conexion.is_open:
                conexion.close()
            self._cerrar_stream()

    def _escribir_monitor_serial(self):
        if not self._origen_local_valido():
            self._json(403, {"error": "Origen no permitido"})
            return
        try:
            longitud = int(self.headers.get("Content-Length", "0"))
            if longitud <= 0 or longitud > 4096:
                self._json(413, {"error": "El mensaje está vacío o supera el tamaño permitido"})
                return
            solicitud = json.loads(self.rfile.read(longitud).decode("utf-8"))
            texto = solicitud.get("texto")
            if not isinstance(texto, str) or not texto:
                self._json(400, {"error": "Escribe un mensaje para enviar a la placa"})
                return
            with _SERIAL_MONITOR_LOCK:
                conexion = _SERIAL_MONITOR
            if conexion is None or not conexion.is_open:
                self._json(409, {"error": "Conecta el monitor serial antes de enviar datos."})
                return
            with _SERIAL_WRITE_LOCK:
                enviados = conexion.write(texto.encode("utf-8"))
            self._json(200, {"enviados": enviados})
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._json(400, {"error": f"Solicitud inválida: {error}"})
        except (OSError, serial.SerialException) as error:
            self._json(409, {"error": f"No se pudo enviar el mensaje por el puerto serie: {error}"})

    def _iniciar_stream(self):
        self._stream_desconectado = False
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _emitir_evento(self, evento: dict):
        if getattr(self, "_stream_desconectado", True):
            return
        cuerpo = (json.dumps(evento, ensure_ascii=False) + "\n").encode("utf-8")
        bloque = f"{len(cuerpo):X}\r\n".encode("ascii") + cuerpo + b"\r\n"
        try:
            self.wfile.write(bloque)
            self.wfile.flush()
        except OSError:
            self._stream_desconectado = True

    def _cerrar_stream(self):
        if getattr(self, "_stream_desconectado", True):
            return
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except OSError:
            self._stream_desconectado = True

    def _cargar(self, codigo: str, fqbn: str, puerto: str):
        if not build.cli_disponible() and not build.platformio_disponible():
            self._emitir_evento({
                "tipo": "resultado",
                "ok": False,
                "error": "No se encontró Arduino CLI ni PlatformIO. Instala/configura el compilador desde Integrated y vuelve a intentar.",
            })
            return

        sketch = build.preparar_sketch(codigo, fqbn)

        def reenviar_evento(evento: dict, etapa: str):
            if evento.get("tipo") == "progreso":
                base = 0 if etapa == "compilacion" else 70
                rango = 70 if etapa == "compilacion" else 29
                self._emitir_evento({
                    "tipo": "progreso",
                    "porcentaje": base + int(evento["porcentaje"] * rango / 100),
                })

        def guardar_linea(linea: str):
            self._emitir_evento({"tipo": "salida", "texto": linea})

        self._emitir_evento({
            "tipo": "fase",
            "mensaje": f"Compilando para {fqbn}…",
        })

        codigo_compilacion = build.ejecutar_comando(
            build.comando_compilar(sketch, fqbn),
            guardar_linea,
            on_event=lambda evento: reenviar_evento(evento, "compilacion"),
            timeout=900,
        )
        if codigo_compilacion != 0:
            self._emitir_evento({
                "tipo": "resultado",
                "ok": False,
                "error": "Falló la compilación. Revisa la salida de compilación para ver el detalle.",
            })
            return

        self._emitir_evento({
            "tipo": "fase",
            "mensaje": f"Subiendo el programa a {puerto}…",
        })
        self._emitir_evento({"tipo": "progreso", "porcentaje": 70})
        codigo_subida = build.ejecutar_comando(
            build.comando_subir(sketch, fqbn, puerto),
            guardar_linea,
            on_event=lambda evento: reenviar_evento(evento, "subida"),
            timeout=300,
        )
        if codigo_subida != 0:
            self._emitir_evento({
                "tipo": "resultado",
                "ok": False,
                "error": "Compiló, pero falló la carga a la placa. Revisa la salida de compilación para ver el detalle.",
            })
            return
        self._emitir_evento({"tipo": "progreso", "porcentaje": 100})
        self._emitir_evento({
            "tipo": "resultado",
            "ok": True,
            "mensaje": "Programa compilado y cargado correctamente",
        })

    def _origen_local_valido(self) -> bool:
        origen = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if not host.startswith(("127.0.0.1:", "localhost:")):
            return False
        if origen:
            return origen == f"http://{host}"
        if self.headers.get("Sec-Fetch-Site") == "same-origin":
            return True
        referer = urlsplit(self.headers.get("Referer", ""))
        return referer.scheme == "http" and referer.netloc == host

    def _json(self, estado: int, datos: dict):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, formato: str, *args):
        print(f"[Integrated Web] {self.address_string()} - {formato % args}")


class LocalThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _crear_servidor():
    try:
        return LocalThreadingServer(("127.0.0.1", PUERTO_INICIAL), IntegratedHandler)
    except OSError as error:
        raise OSError(
            f"No se pudo abrir http://127.0.0.1:{PUERTO_INICIAL}. "
            "Cierra otra instancia de Integrated Web y vuelve a iniciarla."
        ) from error


def main():
    mimetypes.add_type("application/manifest+json", ".json")
    servidor = _crear_servidor()
    url = f"http://127.0.0.1:{servidor.server_address[1]}/index.html"
    print("Integrated Web está disponible en:", url)
    print("Mantén esta ventana abierta mientras uses la aplicación.")
    if not (build.cli_disponible() or build.platformio_disponible()):
        print("Aviso: falta Arduino CLI/PlatformIO; la web abre, pero no podrá cargar a la placa.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando Integrated Web.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
