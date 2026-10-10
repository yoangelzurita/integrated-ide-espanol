"""Configuración persistente de Integrated (temas, placa, header, etc.)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    from app_paths import user_data_dir

    CONFIG_PATH = user_data_dir() / "integrated_config.json"
else:
    CONFIG_PATH = Path(__file__).resolve().parent / "integrated_config.json"

DEFAULTS = {
    "bg_principal": "#0D1117",
    "bg_secundario": "#161B22",
    "bg_editor": "#0D1117",
    "bg_elevado": "#21262D",
    "fg_texto": "#E6EDF3",
    "fg_muted": "#8B949E",
    "fg_editor": "#E6EDF3",
    "acento": "#3FB950",
    "acento_2": "#58A6FF",
    "peligro": "#F85149",
    "borde": "#30363D",
    "header_texto": "#E6EDF3",
    "header_titulo": "Integrated",
    "header_subtitulo": "IDE en español",
    "header_color": None,  # None = usar bg_secundario
    "tam_fuente": 11,
    "placa": "ESP32 S2 Mini",
    "baud_monitor": 115200,
    "geometry": "1400x900",
    "recursos_web": "",
}


def cargar() -> dict:
    data = dict(DEFAULTS)
    if CONFIG_PATH.is_file():
        try:
            guardado = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(guardado, dict):
                data.update({k: v for k, v in guardado.items() if k in DEFAULTS or k.startswith("header")})
        except (json.JSONDecodeError, OSError):
            pass
    return data


def guardar(data: dict) -> None:
    actual = cargar()
    actual.update(data)
    # Solo claves conocidas + header_*
    limpio = {k: actual[k] for k in DEFAULTS if k in actual}
    for k, v in actual.items():
        if k.startswith("header"):
            limpio[k] = v
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(limpio, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
