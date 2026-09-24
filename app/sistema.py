"""Integración con el sistema operativo: arranque automático y apertura del navegador."""
from __future__ import annotations

import os
import plistlib
import sys
import webbrowser
from pathlib import Path

from .config import CONGELADO

PUERTO = 8765
URL = f"http://127.0.0.1:{PUERTO}"
_NOMBRE = "AsistenteProcura"


def abrir_navegador(ruta: str = "") -> None:
    webbrowser.open(URL + ruta)


def _orden_arranque() -> list[str]:
    return [sys.executable, "--segundo-plano"]


def _plist_mac() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "es.asistente.procura.plist"


def configurar_arranque(activar: bool) -> str | None:
    """Registra (o quita) el programa para que se abra al encender el ordenador.

    Solo tiene sentido en el ejecutable; en desarrollo no hace nada. Devuelve un
    mensaje de error o None.
    """
    if not CONGELADO:
        return None
    try:
        if sys.platform == "win32":
            import winreg
            clave = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                                   0, winreg.KEY_SET_VALUE)
            with clave:
                if activar:
                    orden = " ".join(f'"{x}"' if " " in x else x for x in _orden_arranque())
                    winreg.SetValueEx(clave, _NOMBRE, 0, winreg.REG_SZ, orden)
                else:
                    try:
                        winreg.DeleteValue(clave, _NOMBRE)
                    except FileNotFoundError:
                        pass
        elif sys.platform == "darwin":
            p = _plist_mac()
            if activar:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(plistlib.dumps({"Label": "es.asistente.procura",
                                              "ProgramArguments": _orden_arranque(), "RunAtLoad": True}))
            elif p.exists():
                os.remove(p)
    except Exception as e:
        return f"No se pudo configurar el arranque automático: {e}"
    return None
