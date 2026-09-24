"""Ajustes de la aplicación, guardados en data/config.json (nunca se suben a git)."""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

CONGELADO = getattr(sys, "frozen", False)  # True cuando se ejecuta como .exe / .app
RAIZ = Path(__file__).resolve().parent.parent
RECURSOS = Path(getattr(sys, "_MEIPASS", RAIZ))  # donde está la carpeta static
# En el ejecutable los datos van a Documentos, fáciles de encontrar y de copiar
_DATA_POR_DEFECTO = Path.home() / "Documents" / "Asistente de Procura" if CONGELADO else RAIZ / "data"
DATA = Path(os.environ.get("PROCURA_DATA") or _DATA_POR_DEFECTO)
REPO = "AI-PHI-DESIGN/MUM.ASSISTANT.PHI-"
URL_DESCARGA = f"https://github.com/{REPO}/releases/latest"
ARCHIVOS = DATA / "archivos"
CONFIG_PATH = DATA / "config.json"

# Festivos autonómicos (Comunitat Valenciana) y locales (València) de 2026.
# Son una sugerencia inicial: revísalos con el calendario oficial del Colegio.
FESTIVOS_INICIALES = """# Una fecha por línea (AAAA-MM-DD). Los nacionales ya van incluidos.
# Comunitat Valenciana 2026 (REVISAR con el calendario oficial)
2026-03-19  # San José
2026-04-06  # Lunes de Pascua
2026-06-24  # San Juan
2026-10-09  # Día de la Comunitat Valenciana
# Locales València 2026 (REVISAR)
2026-01-22  # San Vicente Mártir
2026-04-13  # San Vicente Ferrer
"""

POR_DEFECTO = {
    "nombre_procuradora": "",
    "ciudad": "Valencia",
    "anthropic_api_key": "",
    "modelo": "claude-opus-5",
    "imap_host": "imap.gmail.com",
    "imap_puerto": 993,
    "imap_usuario": "",
    "imap_password": "",
    "imap_carpeta": "INBOX",
    "revisar_cada_min": 5,
    "correo_activo": False,
    "festivos": FESTIVOS_INICIALES,
    "agosto_inhabil": True,
    "navidad_inhabil": True,
    "arrancar_con_el_ordenador": True,
    "bienvenida_hecha": False,
}

_lock = threading.Lock()


def cargar() -> dict:
    with _lock:
        datos = {}
        if CONFIG_PATH.exists():
            datos = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {**POR_DEFECTO, **datos}


def guardar(cambios: dict) -> dict:
    actual = cargar()
    actual.update({k: v for k, v in cambios.items() if k in POR_DEFECTO})
    with _lock:
        DATA.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(actual, ensure_ascii=False, indent=2), encoding="utf-8")
    return actual


def publico(cfg: dict) -> dict:
    """Versión para enviar al navegador: sin contraseñas en claro."""
    out = dict(cfg)
    for k in ("anthropic_api_key", "imap_password"):
        out[k] = "********" if cfg.get(k) else ""
    return out
