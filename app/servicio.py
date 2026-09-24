"""Procesa documentos: IA → ficha, asunto, contactos y plazos."""
from __future__ import annotations

import json
from datetime import date, datetime

from . import config, db, ia
from .plazos import Calendario, calcular, parsear_festivos


def calendario(cfg: dict | None = None) -> Calendario:
    cfg = cfg or config.cargar()
    return Calendario(festivos=parsear_festivos(cfg.get("festivos", "")),
                      agosto_inhabil=cfg.get("agosto_inhabil", True),
                      navidad_inhabil=cfg.get("navidad_inhabil", True))


def calcular_plazo(recepcion: str, dias: int, computo: str, urgente: bool, cfg: dict | None = None) -> dict:
    fecha = datetime.fromisoformat(recepcion).date() if "T" in recepcion else date.fromisoformat(recepcion[:10])
    return calcular(calendario(cfg), fecha, dias, computo, urgente).dict()


def crear_documento(origen: str, recibido_en: str, texto: str, remitente: str = "", asunto_email: str = "",
                    archivos: list[str] | None = None, email_uid: str | None = None) -> int:
    return db.insertar("documentos", {
        "origen": origen, "recibido_en": recibido_en, "texto": texto, "remitente": remitente,
        "asunto_email": asunto_email, "archivos": json.dumps(archivos or [], ensure_ascii=False),
        "email_uid": email_uid, "estado": "pendiente", "creado_en": db.ahora(),
    })


def procesar(doc_id: int) -> None:
    cfg = config.cargar()
    doc = db.fila("SELECT * FROM documentos WHERE id = ?", (doc_id,))
    if not doc or not cfg.get("anthropic_api_key"):
        return  # sin clave se queda pendiente hasta que se configure
    cabecera = (f"Recibido: {doc['recibido_en']}\nOrigen: {doc['origen']}\nRemitente: {doc['remitente'] or '-'}\n"
                f"Asunto del correo: {doc['asunto_email'] or '-'}\nArchivos: {doc['archivos']}")
    try:
        ficha = ia.clasificar(cfg, doc["texto"] or "", cabecera)
    except ia.ErrorIA as e:
        db.actualizar("documentos", doc_id, {"estado": "error", "error": str(e)})
        return
    aplicar_ficha(doc, ficha, cfg)


def aplicar_ficha(doc: dict, ficha: dict, cfg: dict) -> None:
    proc = ficha.get("procedimiento") or {}
    asunto_id = db.buscar_o_crear_asunto(proc)

    abogado_id = None
    for c in ficha.get("contactos") or []:
        cid = db.buscar_o_crear_contacto(c)
        if c.get("rol") == "abogado" and cid and abogado_id is None:
            abogado_id = cid
    if asunto_id:
        a = db.fila("SELECT * FROM asuntos WHERE id = ?", (asunto_id,))
        # Rellena huecos del asunto con la información nueva
        huecos = {k: proc[k] for k in ("juzgado", "tipo", "nig", "materia", "jurisdiccion", "cliente", "contrario")
                  if proc.get(k) and not a[k]}
        if abogado_id and not a["abogado_id"]:
            huecos["abogado_id"] = abogado_id
        db.actualizar("asuntos", asunto_id, huecos)

    recepcion = doc["recibido_en"] or db.ahora()
    for p in ficha.get("plazos") or []:
        base = {"asunto_id": asunto_id, "documento_id": doc["id"], "clase": p["clase"],
                "descripcion": p["descripcion"], "recepcion": recepcion[:10], "hora": p.get("hora"),
                "urgente": int(bool(p.get("urgente"))), "creado_en": db.ahora()}
        if p["computo"] == "fecha_fija":
            if not p.get("fecha_fija"):
                continue
            db.insertar("plazos", {**base, "computo": "fecha_fija", "vencimiento": p["fecha_fija"][:10],
                                   "explicacion": "Fecha fijada en la resolución."})
        elif p.get("dias"):
            r = calcular_plazo(recepcion, p["dias"], p["computo"], bool(p.get("urgente")), cfg)
            db.insertar("plazos", {**base, "dias": p["dias"], "computo": p["computo"],
                                   "vencimiento": r["vencimiento"], "dia_gracia": r["dia_gracia"],
                                   "explicacion": r["explicacion"]})

    db.actualizar("documentos", doc["id"], {
        "estado": "procesado", "error": None, "categoria": ficha.get("categoria"), "titulo": ficha.get("titulo"),
        "tipo_resolucion": ficha.get("tipo_resolucion"), "resumen": ficha.get("resumen"),
        "accion": ficha.get("accion_requerida"), "urgencia": ficha.get("urgencia"),
        "datos": json.dumps(ficha, ensure_ascii=False), "asunto_id": asunto_id,
        # La publicidad no necesita su atención
        "leido": 1 if ficha.get("categoria") == "publicidad" else 0,
    })


def procesar_pendientes() -> int:
    n = 0
    for d in db.filas("SELECT id FROM documentos WHERE estado = 'pendiente' ORDER BY id"):
        procesar(d["id"])
        n += 1
    return n
