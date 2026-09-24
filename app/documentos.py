"""Extracción de texto de PDFs y datos del nombre de archivo de LexNET."""
from __future__ import annotations

import io
import re
from datetime import datetime

from pypdf import PdfReader

# Los PDFs descargados de LexNET llevan la fecha/hora de recepción justo antes de "_001_":
#   2026_0000123_VRB_20260000000000020260923105724_001_Diligencia....pdf  ->  23/09/2026 10:57:24
_FECHA_LEXNET = re.compile(r"(20\d{2}(?:0[1-9]|1[0-2])(?:[0-2]\d|3[01])(?:[01]\d|2[0-3])[0-5]\d[0-5]\d)_\d{3}_")


def fecha_de_nombre_lexnet(nombre: str) -> datetime | None:
    m = _FECHA_LEXNET.search(nombre or "")
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def texto_pdf(datos: bytes) -> str:
    try:
        lector = PdfReader(io.BytesIO(datos))
        return "\n".join((p.extract_text() or "") for p in lector.pages).strip()
    except Exception as e:  # PDF dañado o cifrado
        return f"[No se pudo leer el PDF: {e}]"


def nombre_seguro(nombre: str) -> str:
    return re.sub(r"[^\w.\- ]", "_", nombre or "archivo")[:150]
