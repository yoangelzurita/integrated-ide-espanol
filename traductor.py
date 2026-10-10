"""Traductor de español natural (.int_esp) a C++ / Arduino.

Optimizado para máxima compatibilidad con hardware AVR (Arduino Uno, Nano, Mega)
y placas ESP (ESP32, ESP8266), gestionando memoria, anidación de bloques
y preservación de identificadores.
"""

from __future__ import annotations

import re
from pathlib import Path

TIPOS = {
    "entero": ("int", "0"),
    "decimal": ("float", "0.0"),
    "texto": ("String", '""'),
    "verdadero o falso": ("bool", "false"),
}

# Conjunto de palabras clave de C++ excluidas de entrecomillado
_PALABRAS_CLAVE_CPP = {
    "HIGH", "LOW", "INPUT", "OUTPUT", "INPUT_PULLUP",
    "true", "false", "null", "NULL",
}


def _reemplazar_operadores(condicion: str) -> str:
    """Reemplaza operadores en español por sus equivalentes C++ preservando identificadores."""
    condicion = condicion.strip()
    if condicion.endswith(":"):
        condicion = condicion[:-1].strip()

    reemplazos = [
        # Operadores compuestos primero (más específicos)
        (r"\bes\s+mayor\s+o\s+igual\s+(?:a|que)\b", " >= "),
        (r"\bmayor\s+o\s+igual\s+(?:a|que)\b", " >= "),
        (r"\bes\s+menor\s+o\s+igual\s+(?:a|que)\b", " <= "),
        (r"\bmenor\s+o\s+igual\s+(?:a|que)\b", " <= "),
        (r"\bno\s+es\s+igual\s+(?:a|que)\b", " != "),
        (r"\bes\s+diferente\s+(?:a|de)\b", " != "),
        (r"\bes\s+distinto\s+(?:a|de)\b", " != "),
        (r"\bdiferente\s+(?:a|de)\b", " != "),
        (r"\bdistinto\s+(?:a|de)\b", " != "),
        # Operadores simples
        (r"\bes\s+mayor\s+(?:a|que)\b", " > "),
        (r"\bmayor\s+(?:a|que)\b", " > "),
        (r"\bes\s+menor\s+(?:a|que)\b", " < "),
        (r"\bmenor\s+(?:a|que)\b", " < "),
        (r"\bes\s+igual\s+(?:a|que)\b", " == "),
        (r"\bigual\s+(?:a|que)\b", " == "),
        # Operadores lógicos
        (r"\by\b", " && "),
        (r"\bo\b", " || "),
        (r"\bno\b", " !"),
        # Constantes lógicas y de pines
        (r"\bencendido\b", "HIGH"),
        (r"\bapagado\b", "LOW"),
        (r"\balto\b", "HIGH"),
        (r"\bbajo\b", "LOW"),
        (r"\bverdadero\b", "true"),
        (r"\bfalso\b", "false"),
    ]
    for patron, op in reemplazos:
        condicion = re.sub(patron, op, condicion, flags=re.IGNORECASE)

    # Limpiar espacios redundantes
    condicion = re.sub(r"[ \t]+", " ", condicion).strip()
    return condicion


def _indent(nivel: int) -> str:
    return "  " * max(nivel, 1)


def _pin_analog(pin_val: str) -> str:
    """Normaliza un identificador de pin analógico.
    
    - Si es un número puro (p. ej. '0') lo convierte a 'A0'.
    - Si ya tiene forma 'A0' lo deja en mayúsculas.
    - Si es un GPIO con nombre (p. ej. '36') lo deja como está.
    """
    pv = pin_val.strip().upper()
    if pv.isdigit():
        return f"A{pv}"
    return pv


def traducir_codigo(
    codigo_espanol: str,
    baud_default: int = 115200,
    fqbn: str | None = None,
    recursos_web: str | Path | None = None,
) -> str:
    """Convierte código en español a un sketch Arduino / C++ completo y optimizado."""
    lineas = codigo_espanol.split("\n")

    includes = ["#include <Arduino.h>"]
    extras_globales: list[str] = []
    variables_globales: list[str] = []
    variables_tipos: dict[str, str] = {}
    familia = "esp32" if fqbn and fqbn.startswith("esp32:") else "esp8266" if fqbn and fqbn.startswith("esp8266:") else "avr"

    def asegurar_variable(nombre: str, tipo_cpp: str = "int", val_inicial: str = "0"):
        """Declara automáticamente una variable si no fue definida explícitamente."""
        nombre = nombre.strip()
        if not nombre or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", nombre):
            return
        if nombre.lower() in ("high", "low", "input", "output", "input_pullup", "true", "false", "led_builtin"):
            return
        if nombre not in variables_tipos and nombre.lower() not in variables_tipos:
            variables_tipos[nombre] = tipo_cpp
            variables_tipos[nombre.lower()] = tipo_cpp
            variables_globales.append(f"{tipo_cpp} {nombre} = {val_inicial};")

    def _str_lit(txt: str) -> str:
        """Formatea un literal de texto. En AVR usa F(...) para conservar memoria SRAM (Flash en vez de RAM)."""
        escapado = txt.replace("\\", "\\\\").replace('"', '\\"')
        if familia == "avr":
            return f'F("{escapado}")'
        return f'"{escapado}"'

    baud_personalizado: int | None = None
    cpp_setup: list[str] = [
        "void setup() {",
        f"  Serial.begin({baud_default});",
        "  delay(250);",
        f"  Serial.println({_str_lit('Integrated iniciado')});",
    ]
    cpp_loop: list[str] = ["void loop() {"]

    seccion_actual = "global"
    seccion_anterior_funcion = "global"
    funcion_actual: list[str] | None = None
    funciones_cpp: list[list[str]] = []
    pila_bloques: list[str] = []
    errores: list[str] = []
    usa_servo = False
    motores: dict[str, tuple[str, str, str]] = {}  # nombre → (pwm, in1, in2)
    ultra_trig: str | None = None
    ultra_echo: str | None = None
    usa_wifi = False
    usa_servidor = False
    rutas_servidor: list[tuple[str, str]] = []
    paginas_archivo: list[tuple[str, str]] = []
    recursos_web_embebidos: list[tuple[str, str, str]] = []
    pines_configurados: dict[str, str] = {}
    pines_salida: set[str] = set()
    puerto_servidor: str | None = None
    wifi_nombre: str | None = None
    wifi_clave: str | None = None
    bloque_html_ruta: str | None = None
    bloque_html_lineas: list[str] = []

    def nivel_actual() -> int:
        return 1 + len(pila_bloques)

    def agregar_include(inc: str):
        if inc not in includes:
            includes.append(inc)

    def agregar(codigo: str):
        if seccion_actual == "funcion" and funcion_actual is not None:
            funcion_actual.append(f"{_indent(nivel_actual())}{codigo}")
            if codigo.startswith("delay(") and familia in ("esp32", "esp8266"):
                funcion_actual.append(f"{_indent(nivel_actual())}yield();")
        elif seccion_actual == "loop":
            cpp_loop.append(f"{_indent(nivel_actual())}{codigo}")
            if codigo.startswith("delay(") and familia in ("esp32", "esp8266"):
                cpp_loop.append(f"{_indent(nivel_actual())}yield();")
        elif seccion_actual == "setup":
            cpp_setup.append(f"{_indent(nivel_actual())}{codigo}")
        else:
            errores.append(f"Comando fuera de sección: {codigo}")

    def cerrar_bloque():
        if pila_bloques:
            tipo = pila_bloques.pop()
            indent = _indent(nivel_actual())
            target = (
                funcion_actual if seccion_actual == "funcion" and funcion_actual is not None
                else cpp_loop if seccion_actual == "loop"
                else cpp_setup
            )
            target.append(f"{indent}}}")
            return tipo
        return None

    def cerrar_todos_los_bloques():
        while pila_bloques:
            cerrar_bloque()

    def configurar_red():
        nonlocal usa_wifi
        usa_wifi = True
        if familia == "esp32":
            agregar_include("#include <WiFi.h>")
        elif familia == "esp8266":
            agregar_include("#include <ESP8266WiFi.h>")

    def diagnostico_arranque():
        if familia != "esp32":
            return
        agregar_include("#include <esp_system.h>")
        cpp_setup[4:4] = [
            "  Serial.print(\"Motivo de arranque: \" );",
            "  Serial.println(esp_reset_reason());",
        ]

    def texto_cpp(texto: str) -> str:
        """Escapa contenido web para una cadena C++ conservando saltos."""
        return (texto.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\r", "")
                .replace("\n", "\\n"))

    def agregar_conexion_wifi(ssid: str, clave: str, num: int):
        if ssid.upper() in {"NOMBRE_DE_TU_WIFI", "SSID", "TU_WIFI"} or clave.upper() in {
            "CLAVE_DE_TU_WIFI", "CONTRASEÑA", "PASSWORD", "CLAVE",
        }:
            errores.append(f"Línea {num}: reemplaza el nombre y la clave por los datos reales de tu red WiFi")
            return
        configurar_red()
        comandos_wifi = [
            "  WiFi.mode(WIFI_STA);",
            "  WiFi.disconnect();",
            "  delay(250);",
            "  WiFi.setAutoReconnect(true);",
            f'  WiFi.begin("{texto_cpp(ssid)}", "{texto_cpp(clave)}");',
            "  unsigned long __wifiInicio = millis();",
            "  while (WiFi.status() != WL_CONNECTED && millis() - __wifiInicio < 20000) { delay(250); }",
            '  Serial.println(WiFi.status() == WL_CONNECTED ? "WiFi conectado" : "Error: no se pudo conectar al WiFi");',
            "  Serial.print(\"Estado WiFi: \");",
            "  Serial.println(WiFi.status());",
            "  if (WiFi.status() == WL_NO_SSID_AVAIL) { Serial.println(\"SSID no encontrado; redes detectadas:\"); int __redes = WiFi.scanNetworks(); for (int __i = 0; __i < __redes; __i++) { Serial.println(WiFi.SSID(__i)); } }",
            "  if (WiFi.status() == WL_CONNECTED) { Serial.println(WiFi.localIP()); }",
        ]
        cpp_setup.extend(comandos_wifi)

    def expresion_credencial(valor: str) -> str:
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] in "\"“" and valor[-1] in "\"”":
            return f'"{texto_cpp(valor[1:-1])}"'
        if valor in variables_tipos and variables_tipos[valor] == "String":
            return f"{valor}.c_str()"
        return f'"{texto_cpp(valor)}"'

    def agregar_conexion_wifi_expresiones(ssid: str, clave: str, num: int):
        if ssid.startswith('"') and clave.startswith('"'):
            agregar_conexion_wifi(ssid[1:-1], clave[1:-1], num)
            return
        if ssid in variables_tipos and clave in variables_tipos:
            configurar_red()
            comandos_wifi = [
                "  WiFi.mode(WIFI_STA);",
                "  WiFi.disconnect();",
                "  delay(250);",
                "  WiFi.setAutoReconnect(true);",
                f"  WiFi.begin({expresion_credencial(ssid)}, {expresion_credencial(clave)});",
                "  unsigned long __wifiInicio = millis();",
                "  while (WiFi.status() != WL_CONNECTED && millis() - __wifiInicio < 20000) { delay(250); }",
                '  Serial.println(WiFi.status() == WL_CONNECTED ? "WiFi conectado" : "Error: no se pudo conectar al WiFi");',
                '  Serial.print("Estado WiFi: ");',
                "  Serial.println(WiFi.status());",
                "  if (WiFi.status() == WL_NO_SSID_AVAIL) { Serial.println(\"SSID no encontrado; redes detectadas:\"); int __redes = WiFi.scanNetworks(); for (int __i = 0; __i < __redes; __i++) { Serial.println(WiFi.SSID(__i)); } }",
                "  if (WiFi.status() == WL_CONNECTED) { Serial.println(WiFi.localIP()); }",
            ]
            cpp_setup.extend(comandos_wifi)
            return
        errores.append(f"Línea {num}: las credenciales deben ser textos entre comillas o variables de texto")

    def configurar_servidor():
        nonlocal usa_servidor
        usa_servidor = True
        configurar_red()
        if familia == "esp32":
            agregar_include("#include <WebServer.h>")
            if "WebServer __servidorIntegrated(80);" not in extras_globales:
                extras_globales.append("WebServer __servidorIntegrated(80);")
        elif familia == "esp8266":
            agregar_include("#include <ESP8266WebServer.h>")
            if "ESP8266WebServer __servidorIntegrated(80);" not in extras_globales:
                extras_globales.append("ESP8266WebServer __servidorIntegrated(80);")

    def configurar_filesystem():
        if familia in ("esp32", "esp8266"):
            agregar_include("#include <LittleFS.h>")
        if "__integratedFilesystemListo" not in extras_globales:
            extras_globales.append("bool __integratedFilesystemListo = false;")
            if familia == "esp32":
                cpp_setup.append("  __integratedFilesystemListo = LittleFS.begin(true);")
            else:
                cpp_setup.append("  __integratedFilesystemListo = LittleFS.begin();")

    def cargar_recursos_web(recursos_dir: Path):
        extensiones = {
            ".html": "text/html", ".htm": "text/html", ".css": "text/css",
            ".js": "application/javascript", ".json": "application/json",
            ".svg": "image/svg+xml", ".txt": "text/plain",
        }
        for archivo in sorted(recursos_dir.rglob("*")):
            if not archivo.is_file() or archivo.suffix.lower() not in extensiones:
                continue
            try:
                contenido = archivo.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                errores.append(f"Recurso web omitido (no es texto UTF-8): {archivo.name}")
                continue
            relativo = archivo.relative_to(recursos_dir).as_posix()
            ruta = "/" + relativo
            if relativo.lower() == "index.html":
                ruta = "/"
            recursos_web_embebidos.append((ruta, texto_cpp(contenido), extensiones[archivo.suffix.lower()]))

    # ─────────────────────────────────────────────────────────────────────────
    # Bucle principal línea a línea
    # ─────────────────────────────────────────────────────────────────────────
    for num, linea in enumerate(lineas, start=1):
        l = linea.strip()
        l_lower = l.lower()

        # HTML embebido multi-línea
        if bloque_html_ruta is not None:
            if l_lower in ("fin html", "fin html:", "fin contenido html", "fin contenido html:"):
                rutas_servidor.append((bloque_html_ruta, texto_cpp("\n".join(bloque_html_lineas))))
                bloque_html_ruta = None
                bloque_html_lineas = []
            else:
                bloque_html_lineas.append(linea)
            continue

        # Líneas vacías y comentarios
        if not l or l_lower.startswith("//") or l_lower.startswith("#"):
            continue

        # Quitar dos puntos finales si no interfieren con sintaxis especial
        if l_lower.endswith(":") and not l_lower.startswith("servidor html"):
            l_sin_dos_puntos = l[:-1].strip()
            l_lower_sin = l_sin_dos_puntos.lower()
        else:
            l_sin_dos_puntos = l
            l_lower_sin = l_lower

        # --- Secciones principales ---
        m_funcion = re.fullmatch(r"funcion\s+([a-zA-Z_][a-zA-Z0-9_]*)", l_sin_dos_puntos, re.IGNORECASE)
        if m_funcion:
            cerrar_todos_los_bloques()
            nombre_funcion = m_funcion.group(1)
            seccion_anterior_funcion = seccion_actual
            funcion_actual = [f"void {nombre_funcion}() {{"]
            funciones_cpp.append(funcion_actual)
            seccion_actual = "funcion"
            continue

        if l_lower_sin in ("fin funcion", "terminar funcion"):
            if seccion_actual == "funcion" and funcion_actual is not None:
                cerrar_todos_los_bloques()
                funcion_actual.append("}")
                funcion_actual = None
                seccion_actual = seccion_anterior_funcion
            else:
                errores.append(f"Línea {num}: 'fin funcion' sin una función abierta")
            continue

        if l_lower_sin in ("al iniciar", "iniciar", "configuracion", "setup"):
            cerrar_todos_los_bloques()
            seccion_actual = "setup"
            continue

        if l_lower_sin in ("repetir siempre", "bucle principal", "bucle", "loop"):
            cerrar_todos_los_bloques()
            seccion_actual = "loop"
            continue

        # --- Cierre de condicionales y bucles ---
        if l_lower_sin in ("fin si", "terminar si", "cerrar si", "fin de si"):
            cerrar_bloque()
            continue

        if l_lower_sin in ("fin mientras", "fin repetir", "fin bucle", "terminar bucle"):
            cerrar_bloque()
            continue

        m_llamar = re.fullmatch(r"llamar\s+([a-zA-Z_][a-zA-Z0-9_]*)", l_sin_dos_puntos, re.IGNORECASE)
        if m_llamar:
            agregar(f"{m_llamar.group(1)}();")
            continue

        # --- Velocidad serie ---
        m_vel = re.search(r"velocidad\s+serie\s*(\d+)", l_lower)
        if m_vel:
            baud_personalizado = int(m_vel.group(1))
            continue

        # --- WiFi y Servidor Web (ESP) ---
        if l_lower.startswith("wifi ") or l_lower.startswith("servidor ") or l_lower.startswith("contenido html "):
            if familia == "avr":
                errores.append(f"Línea {num}: '{l}' requiere una placa ESP32 o ESP8266")
                continue
            if l_lower.startswith("wifi conectar"):
                m = re.match(r'wifi conectar\s+(\S+)\s+(\S+)', linea, re.IGNORECASE)
                if m:
                    agregar_conexion_wifi_expresiones(m.group(1), m.group(2), num)
                else:
                    errores.append(f"Línea {num}: usa wifi conectar \"nombre\" \"clave\"")
                continue
            if l_lower.startswith("wifi nombre"):
                m = re.search(r'wifi nombre\s+(?:=\s*)?(.+)', linea, re.IGNORECASE)
                if m:
                    wifi_nombre = m.group(1).strip()
                else:
                    errores.append(f"Línea {num}: usa wifi nombre \"red\"")
                continue
            if l_lower.startswith("wifi clave") or l_lower.startswith("wifi password"):
                m = re.search(r'wifi (?:clave|password)\s+(?:=\s*)?(.+)', linea, re.IGNORECASE)
                if m:
                    wifi_clave = m.group(1).strip()
                else:
                    errores.append(f"Línea {num}: usa wifi clave \"contraseña\"")
                continue
            if l_lower_sin == "wifi iniciar":
                configurar_red()
                if wifi_nombre is not None and wifi_clave is not None:
                    agregar_conexion_wifi_expresiones(wifi_nombre, wifi_clave, num)
                else:
                    errores.append(f"Línea {num}: define wifi nombre y wifi clave antes de wifi iniciar")
                continue
            if l_lower.startswith("wifi crear punto de acceso"):
                m = re.search(
                    r'wifi crear punto de acceso\s+["“]([^"”]+)["”]\s+["“]([^"”]+)["”]',
                    linea,
                    re.IGNORECASE,
                )
                if m:
                    if len(m.group(2)) < 8:
                        errores.append(f"Línea {num}: la contraseña del punto de acceso debe tener al menos 8 caracteres")
                        continue
                    configurar_red()
                    cpp_setup.extend([
                        "  delay(1000);",
                        "  WiFi.mode(WIFI_AP);",
                        f'  const char* __ssid = "{texto_cpp(m.group(1))}";',
                        f'  const char* __password = "{texto_cpp(m.group(2))}";',
                        '  Serial.println("Iniciando modo AP (Host)...");',
                        '  bool __apCreado = WiFi.softAP(__ssid, __password);',
                        '  if (__apCreado) { Serial.print("Red IP del Host: "); Serial.println(WiFi.softAPIP()); }',
                        '  else { Serial.println("Error: no se pudo crear el punto de acceso WiFi"); }',
                    ])
                else:
                    errores.append(f"Línea {num}: usa wifi crear punto de acceso \"nombre\" \"clave\"")
                continue
            if l_lower.startswith("wifi ip en"):
                m = re.search(r"wifi ip en\s+(\w+)", l_lower)
                if m:
                    configurar_red()
                    agregar(f'{m.group(1)} = WiFi.localIP().toString();')
                continue
            if l_lower_sin == "wifi mostrar ip":
                configurar_red()
                agregar("Serial.println(WiFi.localIP());")
                continue
            if l_lower_sin == "wifi desconectar":
                configurar_red()
                agregar("WiFi.disconnect();")
                continue
            if l_lower.startswith("servidor iniciar"):
                m = re.search(r"servidor iniciar\s+(\d+)", l_lower)
                if m:
                    configurar_servidor()
                    puerto_servidor = m.group(1)
                continue
            if l_lower.startswith("servidor al recibir"):
                # Acción en pin con redirección o respuesta:
                # Ej: servidor al recibir "/encender" encender pin 15 y redirigir "/"
                m_accion_pin = re.search(
                    r'servidor\s+al\s+recibir\s+["“]([^"”]+)["”]\s+(encender|apagar|alternar)\s+pin\s+([a-zA-Z0-9_]+)(?:\s+y\s+(?:responder\s+["“]([^"”]+)["”]|redirigir\s+["“]([^"”]+)["”]))?',
                    linea,
                    re.IGNORECASE,
                )
                if m_accion_pin:
                    configurar_servidor()
                    ruta = m_accion_pin.group(1)
                    accion = m_accion_pin.group(2).lower()
                    pin = m_accion_pin.group(3)
                    pin = pin.upper() if pin.upper().startswith("A") else pin
                    pines_salida.add(pin)
                    resp_txt = m_accion_pin.group(4)
                    redir = m_accion_pin.group(5)

                    if accion == "encender":
                        cod_act = f"digitalWrite({pin}, HIGH);"
                    elif accion == "apagar":
                        cod_act = f"digitalWrite({pin}, LOW);"
                    else:
                        cod_act = f"digitalWrite({pin}, !digitalRead({pin}));"

                    if redir:
                        resp_cpp = f'__servidorIntegrated.sendHeader("Location", "{redir}"); __servidorIntegrated.send(303);'
                    elif resp_txt:
                        resp_cpp = f'__servidorIntegrated.send(200, "text/plain", "{texto_cpp(resp_txt)}");'
                    else:
                        resp_cpp = f'__servidorIntegrated.sendHeader("Location", "/"); __servidorIntegrated.send(303);'

                    cpp_setup.append(
                        f'  __servidorIntegrated.on("{ruta}", []() {{ {cod_act} {resp_cpp} }});'
                    )
                    continue

                # Responder texto:
                m_resp = re.search(
                    r'servidor\s+al\s+recibir\s+["“]([^"”]+)["”]\s+responder\s+["“]([^"”]+)["”]',
                    linea,
                    re.IGNORECASE,
                )
                if m_resp:
                    configurar_servidor()
                    ruta = m_resp.group(1)
                    txt = m_resp.group(2)
                    cpp_setup.append(
                        f'  __servidorIntegrated.on("{ruta}", []() {{ __servidorIntegrated.send(200, "text/plain", "{texto_cpp(txt)}"); }});'
                    )
                    continue

                # Responder HTML:
                m_resp_html = re.search(
                    r'servidor\s+al\s+recibir\s+["“]([^"”]+)["”]\s+responder\s+html\s+["“]([^"”]+)["”]',
                    linea,
                    re.IGNORECASE,
                )
                if m_resp_html:
                    configurar_servidor()
                    ruta = m_resp_html.group(1)
                    txt = m_resp_html.group(2)
                    cpp_setup.append(
                        f'  __servidorIntegrated.on("{ruta}", []() {{ __servidorIntegrated.send(200, "text/html", "{texto_cpp(txt)}"); }});'
                    )
                    continue

            if l_lower.startswith("servidor ruta") or l_lower.startswith("servidor html") or l_lower.startswith("contenido html"):
                bloque = re.match(r'(?:servidor|contenido)\s+html\s+["“]([^"”]+)["”]\s*:\s*$', linea, re.IGNORECASE)
                if bloque:
                    configurar_servidor()
                    bloque_html_ruta = bloque.group(1)
                    bloque_html_lineas = []
                    continue
                m = re.search(r'servidor ruta\s+["“]([^"”]+)["”]\s+["“]([^"”]*)["”]', linea, re.IGNORECASE)
                if not m:
                    m = re.search(r'(?:servidor|contenido)\s+html\s+["“]([^"”]+)["”]\s+["“]([^"”]*)["”]', linea, re.IGNORECASE)
                if m:
                    configurar_servidor()
                    rutas_servidor.append((m.group(1), texto_cpp(m.group(2))))
                else:
                    errores.append(f"Línea {num}: usa servidor html \"/\" \"contenido\"")
                continue
            if l_lower.startswith("servidor pagina"):
                m = re.search(
                    r'servidor pagina\s+["“]([^"”]+)["”]\s+desde\s+["“]([^"”]+)["”]',
                    linea,
                    re.IGNORECASE,
                )
                if m:
                    configurar_servidor()
                    configurar_filesystem()
                    paginas_archivo.append((m.group(1), m.group(2)))
                else:
                    errores.append(f"Línea {num}: usa servidor pagina \"/\" desde \"index.html\"")
                continue
            if l_lower_sin == "servidor atender":
                configurar_servidor()
                agregar("__servidorIntegrated.handleClient();")
                continue

        # --- Declaración de Variables ---
        m_var = re.match(
            r"(?:variable\s+)?(entero|decimal|texto|verdadero\s+o\s+falso|booleano)\s+(?:=\s*([a-zA-Z0-9_]+)|([a-zA-Z0-9_]+)(?:\s*=\s*(.+))?)",
            linea.strip(),
            re.IGNORECASE,
        )
        if m_var:
            tipo_txt = re.sub(r"\s+", " ", m_var.group(1).lower())
            if tipo_txt == "booleano":
                tipo_txt = "verdadero o falso"
            tipo_cpp, val_defecto = TIPOS[tipo_txt]

            nombre_var = m_var.group(2) or m_var.group(3)
            val_inicial = m_var.group(4)

            if val_inicial is not None:
                val_inicial = val_inicial.strip()
                if tipo_cpp == "String" and not (val_inicial.startswith('"') and val_inicial.endswith('"')):
                    val_inicial = f'"{val_inicial}"'
                elif tipo_cpp == "bool":
                    val_inicial = "true" if val_inicial.lower() in ("verdadero", "true", "1") else "false"
            else:
                val_inicial = val_defecto

            variables_tipos[nombre_var] = tipo_cpp
            variables_tipos[nombre_var.lower()] = tipo_cpp
            variables_globales.append(f"{tipo_cpp} {nombre_var} = {val_inicial};")
            continue

        # --- Configurar pin ---
        m_pin = re.match(
            r"(?:configurar\s+pin|pin)\s+([a-zA-Z0-9_]+)\s*(?:,|\s+como|\s+para|\s+)?\s*(salida|entrada\s+con\s+resistencia|entrada\s+pullup|entrada)",
            l_lower,
        )
        if m_pin:
            pin_raw, modo_txt = m_pin.group(1), m_pin.group(2)
            pin = pin_raw.upper() if pin_raw.upper().startswith("A") else pin_raw
            if modo_txt == "salida":
                modo = "OUTPUT"
                pines_salida.add(pin)
            elif "resistencia" in modo_txt or "pullup" in modo_txt:
                modo = "INPUT_PULLUP"
            else:
                modo = "INPUT"
            pines_configurados[pin] = modo
            if seccion_actual == "loop":
                if modo == "OUTPUT":
                    agregar(f"digitalWrite({pin}, LOW);")
                agregar(f"pinMode({pin}, {modo});")
            else:
                if modo == "OUTPUT":
                    cpp_setup.append(f"  digitalWrite({pin}, LOW);")
                cpp_setup.append(f"  pinMode({pin}, {modo});")
            continue

        # --- Configurar ultrasonido ---
        m_ultra = re.match(r"configurar\s+ultrasonido\s+trig\s+([a-zA-Z0-9_]+)\s+echo\s+([a-zA-Z0-9_]+)", l_lower)
        if m_ultra:
            ultra_trig, ultra_echo = m_ultra.group(1), m_ultra.group(2)
            cpp_setup.append(f"  pinMode({ultra_trig}, OUTPUT);")
            cpp_setup.append(f"  pinMode({ultra_echo}, INPUT);")
            continue

        # --- Configurar servo ---
        m_srv = re.match(r"configurar\s+servo\s+pin\s+([a-zA-Z0-9_]+)", l_lower)
        if m_srv:
            usa_servo = True
            agregar_include("#include <Servo.h>")
            extras_globales.append("Servo __servoIntegrated;")
            cpp_setup.append(f"  __servoIntegrated.attach({m_srv.group(1)});")
            continue

        # --- LED integrado ---
        if l_lower_sin in ("configurar led integrado", "led integrado configurar"):
            cpp_setup.append("  pinMode(LED_BUILTIN, OUTPUT);")
            continue

        if l_lower_sin in ("encender led integrado", "apagar led integrado"):
            estado = "HIGH" if l_lower_sin.startswith("encender") else "LOW"
            if seccion_actual == "setup":
                cpp_setup.append(f"  digitalWrite(LED_BUILTIN, {estado});")
            else:
                agregar(f"digitalWrite(LED_BUILTIN, {estado});")
            continue

        m_parp = re.match(r"parpadear\s+led\s+integrado\s*(\d+)?", l_lower)
        if m_parp:
            ms = m_parp.group(1) or "500"
            agregar("digitalWrite(LED_BUILTIN, HIGH);")
            agregar(f"delay({ms});")
            agregar("digitalWrite(LED_BUILTIN, LOW);")
            agregar(f"delay({ms});")
            continue

        # --- Configurar motor ---
        m_mot = re.match(
            r"configurar\s+motor\s+(izquierdo|derecho|a|b)\s+pwm\s+([a-zA-Z0-9_]+)\s+in1\s+([a-zA-Z0-9_]+)\s+in2\s+([a-zA-Z0-9_]+)",
            l_lower,
        )
        if m_mot:
            nombre, pwm, in1, in2 = m_mot.group(1), m_mot.group(2), m_mot.group(3), m_mot.group(4)
            motores[nombre] = (pwm, in1, in2)
            cpp_setup.append(f"  pinMode({pwm}, OUTPUT);")
            cpp_setup.append(f"  pinMode({in1}, OUTPUT);")
            cpp_setup.append(f"  pinMode({in2}, OUTPUT);")
            continue

        # Si aún estamos en global y no es una directiva global, avisar sección
        if seccion_actual == "global":
            errores.append(f"Línea {num}: '{l}' debe ir dentro de 'al iniciar' o 'repetir siempre'")
            continue

        # --- Serial / Monitor ---
        if l_lower.startswith("escribir sin salto "):
            msg = linea.strip()[len("escribir sin salto "):].strip()
            if msg in variables_tipos or msg.lower() in variables_tipos:
                agregar(f"Serial.print({msg});")
            elif msg.startswith('"') and msg.endswith('"'):
                agregar(f"Serial.print({_str_lit(msg[1:-1])});")
            else:
                agregar(f"Serial.print({_str_lit(msg)});")
            continue

        if l_lower.startswith("escribe "):
            msg = linea.strip()[len("escribe "):].strip()
            if "," in msg:
                partes = msg.split(",", 1)
                txt_fijo = partes[0].strip().strip('"')
                val_var = partes[1].strip()
                if txt_fijo:
                    agregar(f"Serial.print({_str_lit(txt_fijo + ' ')});")
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", val_var):
                    asegurar_variable(val_var, "int", "0")
                agregar(f"Serial.println({val_var});")
            elif msg in variables_tipos or msg.lower() in variables_tipos:
                agregar(f"Serial.println({msg});")
            elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", msg):
                asegurar_variable(msg, "int", "0")
                agregar(f"Serial.println({msg});")
            elif msg.startswith('"') and msg.endswith('"'):
                agregar(f"Serial.println({_str_lit(msg[1:-1])});")
            else:
                agregar(f"Serial.println({_str_lit(msg)});")
            continue

        m_leer_ser = re.match(r"leer\s+([a-zA-Z0-9_]+)$", l_lower)
        if m_leer_ser and not any(p in l_lower for p in ("pin", "humedad", "temperatura", "luz", "distancia")):
            var_name = m_leer_ser.group(1)
            asegurar_variable(var_name, "String", '""')
            agregar("while (Serial.available() == 0) { delay(10); }")
            es_entero = any(f"int {var_name}" in g for g in variables_globales)
            es_decimal = any(f"float {var_name}" in g for g in variables_globales)
            if es_entero:
                agregar(f"{var_name} = Serial.readStringUntil('\\n').toInt();")
            elif es_decimal:
                agregar(f"{var_name} = Serial.readStringUntil('\\n').toFloat();")
            else:
                agregar(f"{var_name} = Serial.readStringUntil('\\n');")
                agregar(f"{var_name}.trim();")
            continue

        # --- Ultrasonido medir ---
        m_medir = re.match(r"medir\s+distancia\s+(?:en|para)\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_medir:
            if ultra_trig and ultra_echo:
                dest = m_medir.group(1)
                asegurar_variable(dest, "float", "0.0")
                agregar(f"digitalWrite({ultra_trig}, LOW);")
                agregar("delayMicroseconds(2);")
                agregar(f"digitalWrite({ultra_trig}, HIGH);")
                agregar("delayMicroseconds(10);")
                agregar(f"digitalWrite({ultra_trig}, LOW);")
                agregar(f"{{ long __dur = pulseIn({ultra_echo}, HIGH); {dest} = __dur * 0.0343 / 2.0; }}")
            else:
                errores.append(f"Línea {num}: falta 'configurar ultrasonido trig X echo Y'")
            continue

        # --- Sensores de proyecto ---
        m_hum = re.match(r"leer\s+humedad\s+suelo\s+([a-zA-Z0-9_]+)\s+en\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_hum:
            dest = m_hum.group(2)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest} = analogRead({_pin_analog(m_hum.group(1))});")
            continue

        m_lm35 = re.match(r"leer\s+temperatura\s+lm35\s+([a-zA-Z0-9_]+)\s+en\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_lm35:
            pin = _pin_analog(m_lm35.group(1))
            dest = m_lm35.group(2)
            asegurar_variable(dest, "float", "0.0")
            factor = "3.3 / 4095.0" if familia == "esp32" else "5.0 / 1023.0"
            agregar(f"{dest} = (analogRead({pin}) * ({factor})) * 100.0;")
            continue

        m_luz = re.match(r"leer\s+luz\s+([a-zA-Z0-9_]+)\s+en\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_luz:
            dest = m_luz.group(2)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest} = analogRead({_pin_analog(m_luz.group(1))});")
            continue

        # --- Pines analógicos y digitales genéricos ---
        m_la = re.match(
            r"(?:leer\s+pin\s+anal[oó]gico|leer\s+pin\s+analogico)\s+([a-zA-Z0-9_]+)\s*(?:en|para)?\s*([a-zA-Z0-9_]+)?",
            linea.strip(),
            re.IGNORECASE,
        )
        if m_la:
            pin_arg = _pin_analog(m_la.group(1))
            var_dest = m_la.group(2)
            if var_dest:
                asegurar_variable(var_dest, "int", "0")
                agregar(f"{var_dest} = analogRead({pin_arg});")
            else:
                agregar(f"analogRead({pin_arg});")
            continue

        m_ld = re.match(r"leer\s+pin\s+digital\s+([a-zA-Z0-9_]+)\s+(?:en|para)\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_ld:
            dest = m_ld.group(2)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest} = digitalRead({m_ld.group(1)});")
            continue

        # --- PWM ---
        m_pwm = re.match(r"(?:escribir\s+pwm|pwm)\s*(?:pin\s*)?([a-zA-Z0-9_]+)\s*(?:con|a|=)\s*([a-zA-Z0-9_]+)", l_lower)
        if m_pwm:
            agregar(f"analogWrite({m_pwm.group(1)}, {m_pwm.group(2)});")
            continue

        # --- Servo ---
        m_srv_g = re.match(r"girar\s+servo\s+(?:a|angulo|ángulo)\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_srv_g:
            if usa_servo:
                agregar(f"__servoIntegrated.write({m_srv_g.group(1)});")
            else:
                errores.append(f"Línea {num}: falta 'configurar servo pin N'")
            continue

        # --- Tono / buzzer ---
        m_tono = re.match(r"tono\s+pin\s+([a-zA-Z0-9_]+)\s+frecuencia\s+(\d+)\s+duracion\s+(\d+)", l_lower)
        if m_tono:
            agregar(f"tone({m_tono.group(1)}, {m_tono.group(2)}, {m_tono.group(3)});")
            continue

        m_sil = re.match(r"silencio\s+pin\s+([a-zA-Z0-9_]+)", l_lower)
        if m_sil:
            agregar(f"noTone({m_sil.group(1)});")
            continue

        # --- Motores ---
        m_mot_cmd = re.match(
            r"motor\s+(izquierdo|derecho|a|b)\s+(adelante|atras|atrás|parar)\s*(\d+)?",
            l_lower,
        )
        if m_mot_cmd:
            nombre, accion, vel = m_mot_cmd.group(1), m_mot_cmd.group(2), m_mot_cmd.group(3) or "200"
            if nombre not in motores:
                errores.append(f"Línea {num}: motor '{nombre}' no configurado")
            else:
                pwm, in1, in2 = motores[nombre]
                if accion == "adelante":
                    agregar(f"digitalWrite({in1}, HIGH);")
                    agregar(f"digitalWrite({in2}, LOW);")
                    agregar(f"analogWrite({pwm}, {vel});")
                elif accion in ("atras", "atrás"):
                    agregar(f"digitalWrite({in1}, LOW);")
                    agregar(f"digitalWrite({in2}, HIGH);")
                    agregar(f"analogWrite({pwm}, {vel});")
                else:
                    agregar(f"digitalWrite({in1}, LOW);")
                    agregar(f"digitalWrite({in2}, LOW);")
                    agregar(f"analogWrite({pwm}, 0);")
            continue

        if l_lower_sin in ("parar motores", "detener motores"):
            for pwm, in1, in2 in motores.values():
                agregar(f"digitalWrite({in1}, LOW);")
                agregar(f"digitalWrite({in2}, LOW);")
                agregar(f"analogWrite({pwm}, 0);")
            continue

        # --- Condicionales (if / else if / else) ---
        if l_lower.startswith("si no") or l_lower.startswith("sino"):
            # Comprobar si es "si no si" (else if)
            m_sino_si = re.match(r"(?:si\s+no|sino)\s+si\s+(.+)", l_sin_dos_puntos, re.IGNORECASE)
            if m_sino_si:
                cond = _reemplazar_operadores(m_sino_si.group(1))
                if pila_bloques:
                    pila_bloques.pop()
                    indent = _indent(nivel_actual())
                    target = (
                        funcion_actual if seccion_actual == "funcion" and funcion_actual is not None
                        else cpp_loop if seccion_actual == "loop"
                        else cpp_setup
                    )
                    target.append(f"{indent}}} else if ({cond}) {{")
                    pila_bloques.append("si")
                else:
                    agregar(f"else if ({cond}) {{")
                    pila_bloques.append("si")
                continue

            if pila_bloques:
                pila_bloques.pop()
                indent = _indent(nivel_actual())
                target = cpp_loop if seccion_actual == "loop" else cpp_setup
                target.append(f"{indent}}} else {{")
                pila_bloques.append("sino")
            else:
                agregar("else {")
                pila_bloques.append("sino")
            continue

        if l_lower.startswith("si "):
            resto = l_sin_dos_puntos[3:].strip()
            condicion = _reemplazar_operadores(resto)
            agregar(f"if ({condicion}) {{")
            pila_bloques.append("si")
            continue

        # --- Bucles ---
        m_rep_v = re.match(r"repetir\s+(\d+)\s+veces", l_lower)
        if m_rep_v:
            var_iter = f"__i_{len(pila_bloques)}"
            agregar(f"for (int {var_iter} = 0; {var_iter} < {m_rep_v.group(1)}; {var_iter}++) {{")
            pila_bloques.append("repetir")
            continue

        if l_lower.startswith("mientras "):
            resto = l_sin_dos_puntos[8:].strip()
            condicion = _reemplazar_operadores(resto)
            agregar(f"while ({condicion}) {{")
            pila_bloques.append("mientras")
            continue

        if l_lower_sin in ("romper", "break"):
            agregar("break;")
            continue

        if l_lower_sin in ("continuar", "continue"):
            agregar("continue;")
            continue

        # --- Digital Write / Encender / Apagar ---
        m_dig = re.match(
            r"(?:hacer\s+que\s+pin|digital|poner\s+pin)\s+([a-zA-Z0-9_]+)\s*(?:,|\s+en|\s+=\s*|\s+)?\s*(encendido|apagado|alto|bajo|high|low|1|0)",
            l_lower,
        )
        if m_dig:
            pin_raw, est_raw = m_dig.group(1), m_dig.group(2)
            pin = pin_raw.upper() if pin_raw.upper().startswith("A") else pin_raw
            estado = "HIGH" if est_raw in ("encendido", "alto", "high", "1") else "LOW"
            agregar(f"digitalWrite({pin}, {estado});")
            continue

        m_enc = re.match(r"(?:encender|activar)\s+pin\s+([a-zA-Z0-9_]+)", l_lower)
        if m_enc:
            pin_raw = m_enc.group(1)
            pin = pin_raw.upper() if pin_raw.upper().startswith("A") else pin_raw
            agregar(f"digitalWrite({pin}, HIGH);")
            continue

        m_apa = re.match(r"(?:apagar|desactivar)\s+pin\s+([a-zA-Z0-9_]+)", l_lower)
        if m_apa:
            pin_raw = m_apa.group(1)
            pin = pin_raw.upper() if pin_raw.upper().startswith("A") else pin_raw
            agregar(f"digitalWrite({pin}, LOW);")
            continue

        m_alt = re.match(r"(?:alternar|cambiar\s+estado|toggle)\s+pin\s+([a-zA-Z0-9_]+)", l_lower)
        if m_alt:
            pin_raw = m_alt.group(1)
            pin = pin_raw.upper() if pin_raw.upper().startswith("A") else pin_raw
            agregar(f"digitalWrite({pin}, !digitalRead({pin}));")
            continue

        # --- Temporización / Delays ---
        m_esp_us = re.match(r"esperar\s+microsegundos\s*(\d+)", l_lower)
        if m_esp_us:
            agregar(f"delayMicroseconds({m_esp_us.group(1)});")
            continue

        m_esp_seg = re.match(r"esperar\s+(\d+)\s*(?:segundos|segundo|s)\b", l_lower)
        if m_esp_seg:
            ms = int(m_esp_seg.group(1)) * 1000
            agregar(f"delay({ms});")
            continue

        m_esp = re.match(r"esperar\s+(\d+)\s*(?:ms|milisegundos)?\b", l_lower)
        if m_esp:
            agregar(f"delay({m_esp.group(1)});")
            continue

        # --- Asignaciones y operaciones aritméticas ---
        m_asig = re.match(r"(?:asignar\s+)?([a-zA-Z0-9_]+)\s*=\s*(.+)", linea.strip(), re.IGNORECASE)
        if m_asig and not l_lower.startswith("variable "):
            var_name = m_asig.group(1)
            expr = _reemplazar_operadores(m_asig.group(2).strip())
            if var_name not in variables_tipos and var_name.lower() not in variables_tipos:
                if expr.startswith('"') and expr.endswith('"'):
                    asegurar_variable(var_name, "String", '""')
                elif expr.lower() in ("true", "false", "verdadero", "falso"):
                    asegurar_variable(var_name, "bool", "false")
                elif re.match(r"^-?\d+\.\d+$", expr):
                    asegurar_variable(var_name, "float", "0.0")
                else:
                    asegurar_variable(var_name, "int", "0")
            agregar(f"{var_name} = {expr};")
            continue

        m_sum = re.match(r"(?:sumar|agregar)\s+(.+)\s+a\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_sum:
            cant = _reemplazar_operadores(m_sum.group(1).strip())
            dest = m_sum.group(2)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest} += {cant};")
            continue

        m_res = re.match(r"restar\s+(.+)\s+a\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_res:
            cant = _reemplazar_operadores(m_res.group(1).strip())
            dest = m_res.group(2)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest} -= {cant};")
            continue

        m_mul = re.match(r"multiplicar\s+([a-zA-Z0-9_]+)\s+por\s+(.+)", linea.strip(), re.IGNORECASE)
        if m_mul:
            dest = m_mul.group(1)
            cant = _reemplazar_operadores(m_mul.group(2).strip())
            agregar(f"{dest} *= {cant};")
            continue

        m_div = re.match(r"dividir\s+([a-zA-Z0-9_]+)\s+(?:por|entre)\s+(.+)", linea.strip(), re.IGNORECASE)
        if m_div:
            dest = m_div.group(1)
            cant = _reemplazar_operadores(m_div.group(2).strip())
            agregar(f"{dest} /= {cant};")
            continue

        m_inc = re.match(r"incrementar\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_inc:
            dest = m_inc.group(1)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest}++;")
            continue

        m_dec = re.match(r"decrementar\s+([a-zA-Z0-9_]+)", linea.strip(), re.IGNORECASE)
        if m_dec:
            dest = m_dec.group(1)
            asegurar_variable(dest, "int", "0")
            agregar(f"{dest}--;")
            continue

        # --- Funciones matemáticas avanzadas ---
        m_map = re.match(
            r"mapear\s+([a-zA-Z0-9_]+)\s+de\s+([a-zA-Z0-9_]+)\s+a\s+([a-zA-Z0-9_]+)\s+hacia\s+([a-zA-Z0-9_]+)\s+a\s+([a-zA-Z0-9_]+)\s+en\s+([a-zA-Z0-9_]+)",
            l_lower,
        )
        if m_map:
            agregar(
                f"{m_map.group(6)} = map({m_map.group(1)}, {m_map.group(2)}, {m_map.group(3)}, {m_map.group(4)}, {m_map.group(5)});"
            )
            continue

        m_lim = re.match(r"limitar\s+([a-zA-Z0-9_]+)\s+entre\s+([a-zA-Z0-9_]+)\s+y\s+([a-zA-Z0-9_]+)", l_lower)
        if m_lim:
            agregar(f"{m_lim.group(1)} = constrain({m_lim.group(1)}, {m_lim.group(2)}, {m_lim.group(3)});")
            continue

        m_aleat = re.match(r"aleatorio\s+entre\s+([a-zA-Z0-9_]+)\s+y\s+([a-zA-Z0-9_]+)\s+en\s+([a-zA-Z0-9_]+)", l_lower)
        if m_aleat:
            agregar(f"{m_aleat.group(3)} = random({m_aleat.group(1)}, {m_aleat.group(2)} + 1);")
            continue

        errores.append(f"Línea {num}: no se reconoció → {l}")

    # Cerrar cualquier bloque condicional o bucle pendiente
    cerrar_todos_los_bloques()
    if funcion_actual is not None:
        funcion_actual.append("}")
        errores.append(f"Función sin cerrar: {funcion_actual[0].split()[1]}")

    # Actualizar la velocidad serie si el usuario la personalizó
    if baud_personalizado is not None:
        cpp_setup[1] = f"  Serial.begin({baud_personalizado});"

    # Inyectar servidor web SOLO si el código del usuario solicitó explícitamente un servidor
    if usa_servidor:
        if familia != "avr" and (recursos_dir := (Path(recursos_web) if recursos_web else None)):
            if recursos_dir.is_dir():
                cargar_recursos_web(recursos_dir)

        for ruta, contenido in rutas_servidor:
            cpp_setup.append(
                f'  __servidorIntegrated.on("{ruta}", []() {{ __servidorIntegrated.send(200, "text/html", "{contenido}"); }});'
            )
        for ruta, contenido, tipo in recursos_web_embebidos:
            cpp_setup.append(
                f'  __servidorIntegrated.on("{ruta}", []() {{ __servidorIntegrated.send(200, "{tipo}", "{contenido}"); }});'
            )
        for ruta, archivo in paginas_archivo:
            contenido_tipo = "text/html" if archivo.lower().endswith((".html", ".htm")) else "text/plain"
            cpp_setup.append(
                f'  __servidorIntegrated.on("{ruta}", []() {{ if (!__integratedFilesystemListo) {{ __servidorIntegrated.send(503, "text/plain", "Filesystem no disponible"); return; }} File __pagina = LittleFS.open("/{archivo}", "r"); if (!__pagina) {{ __servidorIntegrated.send(404, "text/plain", "Pagina no encontrada"); return; }} __servidorIntegrated.streamFile(__pagina, "{contenido_tipo}"); __pagina.close(); }});'
            )
        if puerto_servidor is not None:
            cpp_setup.append(f"  __servidorIntegrated.begin({puerto_servidor});")
        else:
            cpp_setup.append("  __servidorIntegrated.begin(80);")

    cpp_setup.append("}")
    cpp_loop.append("}")
    if usa_servidor and not any("handleClient" in linea for linea in cpp_loop):
        cpp_loop.insert(1, "  __servidorIntegrated.handleClient();")

    # ── Ensamblar el sketch final ────────────────────────────────────────────
    seccion_global = []
    if extras_globales:
        seccion_global.extend(extras_globales)
        seccion_global.append("")
    if variables_globales:
        seccion_global.extend(variables_globales)
        seccion_global.append("")

    partes = includes + [""] + seccion_global
    for funcion in funciones_cpp:
        partes.extend(funcion)
        partes.append("")
    partes.extend(cpp_setup)
    partes.extend([""] + cpp_loop)

    if errores:
        comentario = "\n".join(f"// AVISO: {e}" for e in errores)
        partes = [comentario, ""] + partes

    return "\n".join(partes)
