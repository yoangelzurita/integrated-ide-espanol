"""Gestión de compilación/subida con caché persistente para builds más rápidos."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

BASE_DIR = Path(__file__).resolve().parent
CLI_PATH = BASE_DIR / "arduino-cli.exe"
CACHE_ROOT = BASE_DIR / ".integrated_build"
PLATFORMIO_PATHS = (
    BASE_DIR / "pio.exe",
    Path.home() / ".platformio" / "penv" / "Scripts" / "platformio.exe",
)
_PROGRESS_RE = re.compile(r"(?:^|[^\d])(\d{1,3})\s*%")
RECURSOS_WEB_NOMBRES = ("web", "public", "recursos_web", "sitio_web")


def cli_path() -> Optional[Path]:
    """Busca el ejecutable arduino-cli en el directorio local, rutas estándar y PATH."""
    candidatos = [
        BASE_DIR / "arduino-cli.exe",
        BASE_DIR / "arduino-cli",
        BASE_DIR / "bin" / "arduino-cli.exe",
        Path.home() / "arduino-cli.exe",
        Path.home() / "AppData" / "Local" / "Arduino15" / "arduino-cli.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "arduino-cli.exe",
        Path("C:/Program Files/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe"),
        Path("C:/Program Files (x86)/Arduino IDE/resources/app/lib/backend/resources/arduino-cli.exe"),
        Path("C:/Program Files/Arduino/arduino-cli.exe"),
        Path("C:/arduino-cli/arduino-cli.exe"),
    ]
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    encontrado = shutil.which("arduino-cli") or shutil.which("arduino-cli.exe")
    return Path(encontrado) if encontrado else None


def cli_disponible() -> bool:
    return cli_path() is not None


def platformio_path() -> Optional[Path]:
    for candidato in PLATFORMIO_PATHS:
        if candidato.is_file():
            return candidato
    encontrado = shutil.which("platformio") or shutil.which("pio")
    return Path(encontrado) if encontrado else None


def platformio_disponible() -> bool:
    return platformio_path() is not None


def _platformio_board(fqbn: str) -> Optional[str]:
    placas = {
        # ESP32 y ESP8266
        "esp32:esp32:lolin_s2_mini": "lolin_s2_mini",
        "esp32:esp32:esp32": "esp32dev",
        "esp32:esp32:esp32s3": "esp32-s3-devkitc-1",
        "esp32:esp32:esp32c3": "esp32-c3-devkitm-1",
        "esp8266:esp8266:nodemcuv2": "nodemcuv2",
        # Placas Arduino AVR estándar
        "arduino:avr:uno": "uno",
        "arduino:avr:nano": "nanoatmega328",
        "arduino:avr:mega": "megaatmega2560",
        "arduino:avr:leonardo": "leonardo",
        "arduino:avr:micro": "micro",
        "arduino:avr:pro": "pro16MHzatmega328",
    }
    return placas.get(fqbn)


def backend_para(fqbn: str) -> str:
    """Selecciona el backend óptimo (PlatformIO o Arduino CLI) según compatibilidad y disponibilidad."""
    pio_soporta = _platformio_board(fqbn) is not None and platformio_disponible()
    if cli_disponible():
        if fqbn.startswith("arduino:avr:"):
            return "arduino-cli"
        if pio_soporta and fqbn.startswith(("esp32:", "esp8266:")):
            return "platformio"
        return "arduino-cli"
    if pio_soporta:
        return "platformio"
    return "arduino-cli"


def _preparar_platformio(sketch_dir: Path, fqbn: str) -> bool:
    board = _platformio_board(fqbn)
    if not board:
        return False
    sketch_dir.mkdir(parents=True, exist_ok=True)
    ini = sketch_dir / "platformio.ini"
    es_s2 = fqbn == "esp32:esp32:lolin_s2_mini"
    es_avr = fqbn.startswith("arduino:avr:")

    if es_avr:
        platform = "atmelavr"
        monitor_speed = 9600
        upload_extra = ""
    elif fqbn.startswith("esp32:"):
        platform = "espressif32"
        monitor_speed = 115200
        upload_extra = "upload_speed = 115200\nupload_protocol = esptool\n"
    else:
        platform = "espressif8266"
        monitor_speed = 115200
        upload_extra = "upload_speed = 115200\nupload_protocol = esptool\n"

    contenido = (
        "[env:integrated]\n"
        f"platform = {platform}\n"
        f"board = {board}\n"
        "framework = arduino\n"
        f"monitor_speed = {monitor_speed}\n"
        + upload_extra
        + ("build_flags = -DARDUINO_USB_CDC_ON_BOOT=1 -DARDUINO_USB_MODE=0\n" if es_s2 else "")
        + "build_type = release\n"
    )
    if not ini.exists() or ini.read_text(encoding="utf-8") != contenido:
        ini.write_text(contenido, encoding="utf-8")
    return True


def descubrir_recursos_web() -> Optional[Path]:
    """Encuentra automáticamente una carpeta web del proyecto, si existe."""
    for nombre in RECURSOS_WEB_NOMBRES:
        candidato = BASE_DIR / nombre
        if candidato.is_dir() and any(candidato.rglob("*.html")):
            return candidato
    return None


def _hash_sketch(contenido: str, fqbn: str, recursos_dir: Optional[Path] = None) -> str:
    h = hashlib.sha256()
    h.update(fqbn.encode("utf-8"))
    h.update(b"\0")
    h.update(contenido.encode("utf-8"))
    if recursos_dir and recursos_dir.is_dir():
        for archivo in sorted(recursos_dir.rglob("*")):
            if archivo.is_file():
                h.update(str(archivo.relative_to(recursos_dir)).encode("utf-8"))
                h.update(archivo.read_bytes())
    return h.hexdigest()[:16]


def preparar_sketch(
    codigo_cpp: str,
    fqbn: str,
    recursos_dir: Optional[Path] = None,
) -> Path:
    """Escribe el sketch en caché. El .ino DEBE llamarse igual que la carpeta (regla Arduino)."""
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    clave = _hash_sketch(codigo_cpp, fqbn, recursos_dir)
    nombre = f"sketch_{clave}"
    sketch_dir = CACHE_ROOT / nombre
    sketch_dir.mkdir(parents=True, exist_ok=True)
    ino = sketch_dir / f"{nombre}.ino"
    # Eliminar .ino antiguos con nombre incorrecto (builds previos rotos)
    for viejo in sketch_dir.glob("*.ino"):
        if viejo.name != ino.name:
            try:
                viejo.unlink()
            except OSError:
                pass
    if not ino.exists() or ino.read_text(encoding="utf-8") != codigo_cpp:
        ino.write_text(codigo_cpp, encoding="utf-8")
    src_dir = sketch_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    platformio_ino = src_dir / "main.ino"
    if not platformio_ino.exists() or platformio_ino.read_text(encoding="utf-8") != codigo_cpp:
        platformio_ino.write_text(codigo_cpp, encoding="utf-8")
    if "WebServer" in codigo_cpp or "__servidorIntegrated" in codigo_cpp:
        preparar_recursos_web(sketch_dir, recursos_dir)
    else:
        data_dir = sketch_dir / "data"
        if data_dir.exists():
            shutil.rmtree(data_dir, ignore_errors=True)
    _preparar_platformio(sketch_dir, fqbn)
    return sketch_dir


def preparar_recursos_web(sketch_dir: Path, recursos_dir: Optional[Path]) -> int:
    """Copia recursos web al directorio data del sketch y devuelve el total."""
    data_dir = sketch_dir / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)
    if not recursos_dir or not recursos_dir.is_dir():
        return 0
    total = 0
    for archivo in recursos_dir.rglob("*"):
        if not archivo.is_file():
            continue
        destino = data_dir / archivo.relative_to(recursos_dir)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archivo, destino)
        total += 1
    return total


def build_path_para(sketch_dir: Path) -> Path:
    path = sketch_dir / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cmd_base() -> list:
    cp = cli_path()
    return [str(cp)] if cp else [str(CLI_PATH)]


def comando_compilar(sketch_dir: Path, fqbn: str, jobs: Optional[int] = None) -> list:
    """Compila reutilizando --build-path para acelerar recompilaciones."""
    if backend_para(fqbn) == "platformio" and _preparar_platformio(sketch_dir, fqbn):
        return [str(platformio_path()), "run", "-d", str(sketch_dir)]
    build_path = build_path_para(sketch_dir)
    n_jobs = jobs if jobs is not None else 0  # 0 = todos los núcleos
    cmd = _cmd_base() + [
        "compile",
        "--fqbn", fqbn,
        "--build-path", str(build_path),
        "--jobs", str(n_jobs),
        str(sketch_dir),
    ]
    return cmd


def comando_subir(sketch_dir: Path, fqbn: str, puerto: str) -> list:
    if backend_para(fqbn) == "platformio" and _preparar_platformio(sketch_dir, fqbn):
        return [
            str(platformio_path()), "run", "-d", str(sketch_dir),
            "-t", "upload", "--upload-port", puerto,
        ]
    build_path = build_path_para(sketch_dir)
    return _cmd_base() + [
        "upload",
        "-p", puerto,
        "--fqbn", fqbn,
        "--input-dir", str(build_path),
        "--verify",
        str(sketch_dir),
    ]


def comando_compilar_y_subir(sketch_dir: Path, fqbn: str, puerto: str) -> tuple[list, list]:
    return comando_compilar(sketch_dir, fqbn), comando_subir(sketch_dir, fqbn, puerto)


def limpiar_cache() -> int:
    """Borra la caché de builds. Devuelve cuántas carpetas se eliminaron."""
    if not CACHE_ROOT.exists():
        return 0
    count = 0
    for hijo in CACHE_ROOT.iterdir():
        if hijo.is_dir():
            shutil.rmtree(hijo, ignore_errors=True)
            count += 1
    return count


def ejecutar_comando(
    cmd: list,
    on_linea: Callable[[str], None],
    cwd: Optional[str] = None,
    on_event: Optional[Callable[[dict], None]] = None,
    timeout: Optional[float] = None,
) -> int:
    """Ejecuta un comando con salida en vivo y límite para evitar bloqueos."""
    def emitir(evento: dict):
        if on_event:
            on_event(evento)

    proceso = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        cwd=cwd or str(BASE_DIR),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    assert proceso.stdout is not None
    emitir({"tipo": "iniciado", "comando": cmd})
    eventos = queue.Queue()

    def leer_salida():
        try:
            while True:
                bloque = proceso.stdout.read1(4096)
                if not bloque:
                    break
                eventos.put(bloque.decode("utf-8", errors="replace"))
        finally:
            eventos.put(None)

    threading.Thread(target=leer_salida, daemon=True).start()
    buffer = ""
    inicio = time.monotonic()
    salida_terminada = False
    while proceso.poll() is None or not salida_terminada or not eventos.empty():
        if timeout is not None and time.monotonic() - inicio > timeout:
            proceso.kill()
            emitir({"tipo": "timeout", "segundos": timeout})
            codigo = -1
            break
        try:
            bloque = eventos.get(timeout=0.1)
        except queue.Empty:
            continue
        if bloque is None:
            salida_terminada = True
            continue
        buffer += bloque
        partes = re.split(r"[\r\n]", buffer)
        buffer = partes.pop()
        for linea in partes:
            if not linea:
                continue
            texto = linea + "\n"
            on_linea(texto)
            emitir({"tipo": "salida", "texto": texto})
            coincidencia = _PROGRESS_RE.search(linea)
            if coincidencia:
                porcentaje = max(0, min(100, int(coincidencia.group(1))))
                emitir({"tipo": "progreso", "porcentaje": porcentaje, "fuente": "salida"})
    else:
        codigo = proceso.wait()
    if buffer:
        on_linea(buffer)
        emitir({"tipo": "salida", "texto": buffer})
    if "codigo" not in locals():
        codigo = proceso.wait()
    emitir({"tipo": "finalizado", "codigo": codigo})
    return codigo


def instalar_core(core: str, on_linea: Callable[[str], None], index_urls: Optional[list] = None) -> int:
    if index_urls:
        urls = ",".join(index_urls)
        code = ejecutar_comando(
            _cmd_base() + ["core", "update-index", "--additional-urls", urls],
            on_linea,
        )
        if code != 0:
            return code
        return ejecutar_comando(
            _cmd_base() + ["core", "install", core, "--additional-urls", urls],
            on_linea,
        )
    code = ejecutar_comando(_cmd_base() + ["core", "update-index"], on_linea)
    if code != 0:
        return code
    return ejecutar_comando(_cmd_base() + ["core", "install", core], on_linea)


def sketch_temporal_legacy(codigo_cpp: str) -> Path:
    """Fallback: sketch en temp (por si se necesita aislamiento total)."""
    temp_dir = Path(tempfile.mkdtemp(prefix="integrated_"))
    sketch_dir = temp_dir / "sketch_arduino"
    sketch_dir.mkdir(parents=True, exist_ok=True)
    (sketch_dir / "sketch_arduino.ino").write_text(codigo_cpp, encoding="utf-8")
    return sketch_dir
