"""Catálogo de placas soportadas por Integrated (FQBN de Arduino CLI)."""

# nombre visible → (fqbn, baudio_recomendado, core_necesario)
PLACAS = {
    "ESP32 S2 Mini": ("esp32:esp32:lolin_s2_mini", 115200, "esp32:esp32"),
    "ESP32 Dev Module": ("esp32:esp32:esp32", 115200, "esp32:esp32"),
    "ESP32-S3 Dev Module": ("esp32:esp32:esp32s3", 115200, "esp32:esp32"),
    "ESP32-C3 Dev Module": ("esp32:esp32:esp32c3", 115200, "esp32:esp32"),
    "ESP8266 NodeMCU": ("esp8266:esp8266:nodemcuv2", 115200, "esp8266:esp8266"),
    "Arduino Uno": ("arduino:avr:uno", 9600, "arduino:avr"),
    "Arduino Nano": ("arduino:avr:nano", 9600, "arduino:avr"),
    "Arduino Mega 2560": ("arduino:avr:mega", 9600, "arduino:avr"),
    "Arduino Leonardo": ("arduino:avr:leonardo", 9600, "arduino:avr"),
    "Arduino Micro": ("arduino:avr:micro", 9600, "arduino:avr"),
    "Arduino Pro Mini": ("arduino:avr:pro", 9600, "arduino:avr"),
}

# URLs de índices adicionales para cores de terceros
CORE_INDEX_URLS = [
    "https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json",
    "https://arduino.esp8266.com/stable/package_esp8266com_index.json",
]


def nombres_placas():
    return list(PLACAS.keys())


def info_placa(nombre: str):
    return PLACAS.get(nombre)


def fqbn_de(nombre: str):
    info = PLACAS.get(nombre)
    return info[0] if info else None


def baud_de(nombre: str, default: int = 115200):
    info = PLACAS.get(nombre)
    return info[1] if info else default


def core_de(nombre: str):
    info = PLACAS.get(nombre)
    return info[2] if info else None


def familia_de_fqbn(fqbn: str | None) -> str:
    """Devuelve la familia de hardware a partir del FQBN."""
    if fqbn and fqbn.startswith("esp32:"):
        return "esp32"
    if fqbn and fqbn.startswith("esp8266:"):
        return "esp8266"
    return "avr"


def capacidades_de(nombre: str) -> set[str]:
    """Enumera capacidades que el traductor puede validar antes de compilar."""
    familia = familia_de_fqbn(fqbn_de(nombre))
    capacidades = {"gpio", "serial", "sensores"}
    if familia in {"esp32", "esp8266"}:
        capacidades.update({"wifi", "servidor", "filesystem"})
    return capacidades
