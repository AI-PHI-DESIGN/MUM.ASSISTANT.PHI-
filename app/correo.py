"""Lee el correo por IMAP y convierte cada mensaje nuevo en un documento."""
from __future__ import annotations

import email
import html
import imaplib
import re
import threading
import time
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from . import config, db, servicio
from .config import ARCHIVOS
from .documentos import fecha_de_nombre_lexnet, nombre_seguro, texto_pdf

_evento_revisar = threading.Event()
_lock_revisar = threading.Lock()
estado = {"ultima_revision": None, "ultimo_error": None, "revisando": False}


def _decodificar(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor)))
    except Exception:
        return valor


def _html_a_texto(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n\s*\n+", "\n\n", html.unescape(s)).strip()


def _extraer(msg: email.message.Message, carpeta_destino) -> tuple[str, list[str], list[tuple[str, str]]]:
    """Devuelve (cuerpo, nombres_archivos, [(nombre, texto_pdf)])."""
    plano, en_html, archivos, pdfs = [], [], [], []
    for parte in msg.walk():
        if parte.is_multipart():
            continue
        nombre = _decodificar(parte.get_filename())
        tipo = parte.get_content_type()
        datos = parte.get_payload(decode=True) or b""
        if nombre:
            nombre = nombre_seguro(nombre)
            carpeta_destino.mkdir(parents=True, exist_ok=True)
            (carpeta_destino / nombre).write_bytes(datos)
            archivos.append(nombre)
            if tipo == "application/pdf" or nombre.lower().endswith(".pdf"):
                pdfs.append((nombre, texto_pdf(datos)))
            continue
        juego = parte.get_content_charset() or "utf-8"
        texto = datos.decode(juego, errors="replace")
        if tipo == "text/plain":
            plano.append(texto)
        elif tipo == "text/html":
            en_html.append(_html_a_texto(texto))
    cuerpo = "\n".join(plano) if plano else "\n".join(en_html)
    return cuerpo.strip(), archivos, pdfs


def revisar_ahora() -> dict:
    """Descarga los correos nuevos. Devuelve {'nuevos': n}."""
    if not _lock_revisar.acquire(blocking=False):
        return {"nuevos": 0, "ocupado": True}
    try:
        return _revisar()
    finally:
        _lock_revisar.release()


def _revisar() -> dict:
    cfg = config.cargar()
    if not (cfg.get("imap_host") and cfg.get("imap_usuario") and cfg.get("imap_password")):
        raise RuntimeError("Falta configurar el correo en Ajustes.")
    estado["revisando"] = True
    nuevos = []
    try:
        with imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg.get("imap_puerto") or 993), timeout=60) as imap:
            imap.login(cfg["imap_usuario"], cfg["imap_password"])
            imap.select(cfg.get("imap_carpeta") or "INBOX", readonly=True)  # no marca como leídos
            ultimo_uid = int(db.get_estado("ultimo_uid", "0"))
            if ultimo_uid == 0:
                # Primera vez: solo los últimos 7 días
                desde = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
                _, datos = imap.uid("search", None, f"(SINCE {desde})")
            else:
                _, datos = imap.uid("search", None, f"UID {ultimo_uid + 1}:*")
            uids = [int(u) for u in (datos[0] or b"").split() if int(u) > ultimo_uid]
            for uid in sorted(uids):
                _, partes = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
                bruto = next((p[1] for p in partes if isinstance(p, tuple)), None)
                if not bruto:
                    continue
                msg = email.message_from_bytes(bruto)
                try:
                    recibido = parsedate_to_datetime(msg["Date"]).astimezone().replace(tzinfo=None)
                except Exception:
                    recibido = datetime.now()
                cuerpo, archivos, pdfs = _extraer(msg, ARCHIVOS / f"correo_{uid}")
                # Si el adjunto es un PDF de LexNET, su nombre lleva la fecha real de recepción
                for nombre, _ in pdfs:
                    fecha = fecha_de_nombre_lexnet(nombre)
                    if fecha:
                        recibido = fecha
                        break
                texto = cuerpo + "".join(f"\n\n=== Adjunto: {n} ===\n{t}" for n, t in pdfs)
                doc_id = servicio.crear_documento(
                    "email", recibido.isoformat(timespec="seconds"), texto,
                    remitente=_decodificar(msg["From"]), asunto_email=_decodificar(msg["Subject"]),
                    archivos=[f"correo_{uid}/{a}" for a in archivos], email_uid=str(uid))
                nuevos.append(doc_id)
                db.set_estado("ultimo_uid", str(uid))
        estado["ultimo_error"] = None
    except Exception as e:
        estado["ultimo_error"] = f"{type(e).__name__}: {e}"
        raise
    finally:
        estado["revisando"] = False
        estado["ultima_revision"] = db.ahora()
    for d in nuevos:
        servicio.procesar(d)
    return {"nuevos": len(nuevos)}


def pedir_revision() -> None:
    _evento_revisar.set()


def _bucle() -> None:
    while True:
        cfg = config.cargar()
        if cfg.get("correo_activo"):
            try:
                revisar_ahora()
            except Exception:
                pass  # queda anotado en estado["ultimo_error"]
        try:
            servicio.procesar_pendientes()  # reintenta los que fallaron por falta de conexión
        except Exception:
            pass
        _evento_revisar.wait(timeout=max(1, int(cfg.get("revisar_cada_min") or 5)) * 60)
        _evento_revisar.clear()


def arrancar_en_segundo_plano() -> None:
    threading.Thread(target=_bucle, daemon=True, name="correo").start()
