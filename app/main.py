"""Servidor web local (solo accesible desde este ordenador)."""
from __future__ import annotations

import io
import json
import os
import threading
import time
import urllib.request
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, correo, db, ia, servicio, sistema
from .config import ARCHIVOS, RECURSOS
from .version import VERSION
from .documentos import fecha_de_nombre_lexnet, nombre_seguro, texto_pdf

@asynccontextmanager
async def _ciclo(_app):
    db.iniciar()
    correo.arrancar_en_segundo_plano()
    threading.Thread(target=_buscar_actualizacion, daemon=True).start()
    yield


app = FastAPI(title="Asistente de Procura", lifespan=_ciclo)


# ------------------------------------------------------------------ versión

_actualizacion: dict = {"nueva": None}


def _numero(v: str) -> int:
    try:
        return int(str(v).lstrip("v"))
    except ValueError:
        return 0


def _buscar_actualizacion() -> None:
    if VERSION == "desarrollo":
        return
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{config.REPO}/releases/latest",
                                     headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            ultima = json.load(r).get("tag_name", "")
        if _numero(ultima) > _numero(VERSION):
            _actualizacion["nueva"] = ultima
    except Exception:
        pass  # sin internet o GitHub no responde: no pasa nada


@app.get("/api/version")
def version():
    return {"version": VERSION, "nueva": _actualizacion["nueva"], "descarga": config.URL_DESCARGA,
            "datos": str(config.DATA)}


@app.post("/api/salir")
def salir():
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"ok": True}


# ------------------------------------------------------------------ resumen

@app.get("/api/resumen")
def resumen():
    correo.estado["ultimo_contacto_navegador"] = time.time()
    hoy = date.today()
    semana = (hoy + timedelta(days=7)).isoformat()
    plazos = db.filas("""
        SELECT p.*, a.numero, a.tipo AS tipo_proc, a.juzgado, a.cliente
        FROM plazos p LEFT JOIN asuntos a ON a.id = p.asunto_id
        WHERE p.completado = 0 AND p.vencimiento <= ? ORDER BY p.vencimiento, p.hora""", (semana,))
    no_leidos = db.filas("""SELECT id, titulo, categoria, urgencia, recibido_en, estado, asunto_email
                            FROM documentos WHERE leido = 0 ORDER BY recibido_en DESC""")
    return {
        "hoy": hoy.isoformat(),
        "plazos": plazos,
        "no_leidos": no_leidos,
        "ultimo_documento_id": (db.fila("SELECT MAX(id) AS m FROM documentos") or {}).get("m") or 0,
        "correo": {**correo.estado, "activo": config.cargar().get("correo_activo")},
        "configurado": bool(config.cargar().get("anthropic_api_key")),
        "bienvenida_hecha": bool(config.cargar().get("bienvenida_hecha")),
    }


# ------------------------------------------------------------------ documentos

@app.get("/api/documentos")
def documentos(q: str = "", categoria: str = "", ocultar_publicidad: bool = True):
    sql = """SELECT d.id, d.origen, d.recibido_en, d.remitente, d.asunto_email, d.estado, d.error, d.categoria,
                    d.titulo, d.resumen, d.urgencia, d.leido, d.asunto_id, a.numero, a.juzgado
             FROM documentos d LEFT JOIN asuntos a ON a.id = d.asunto_id WHERE 1=1"""
    params: list = []
    if q:
        sql += " AND (d.texto LIKE ? OR d.titulo LIKE ? OR d.asunto_email LIKE ?)"
        params += [f"%{q}%"] * 3
    if categoria:
        sql += " AND d.categoria = ?"
        params.append(categoria)
    elif ocultar_publicidad:
        sql += " AND COALESCE(d.categoria, '') != 'publicidad'"
    return db.filas(sql + " ORDER BY d.recibido_en DESC LIMIT 300", params)


@app.get("/api/documentos/{doc_id}")
def documento(doc_id: int):
    d = db.fila("SELECT * FROM documentos WHERE id = ?", (doc_id,))
    if not d:
        raise HTTPException(404)
    d["archivos"] = json.loads(d["archivos"] or "[]")
    d["datos"] = json.loads(d["datos"]) if d["datos"] else None
    d["plazos"] = db.filas("""SELECT p.*, a.numero, a.tipo AS tipo_proc, a.juzgado, a.cliente
                              FROM plazos p LEFT JOIN asuntos a ON a.id = p.asunto_id
                              WHERE p.documento_id = ?""", (doc_id,))
    d["asunto"] = db.fila("SELECT * FROM asuntos WHERE id = ?", (d["asunto_id"],)) if d["asunto_id"] else None
    if d["asunto"] and d["asunto"]["abogado_id"]:
        d["abogado"] = db.fila("SELECT * FROM contactos WHERE id = ?", (d["asunto"]["abogado_id"],))
    return d


class CambioDoc(BaseModel):
    leido: int | None = None
    asunto_id: int | None = None
    recibido_en: str | None = None


@app.patch("/api/documentos/{doc_id}")
def cambiar_documento(doc_id: int, c: CambioDoc):
    db.actualizar("documentos", doc_id, c.model_dump(exclude_none=True))
    return {"ok": True}


@app.post("/api/documentos/{doc_id}/reprocesar")
def reprocesar(doc_id: int):
    # Borra los plazos que generó la vez anterior (los hechos a mano se conservan)
    db.ejecutar("DELETE FROM plazos WHERE documento_id = ? AND completado = 0", (doc_id,))
    db.actualizar("documentos", doc_id, {"estado": "pendiente", "error": None})
    threading.Thread(target=servicio.procesar, args=(doc_id,), daemon=True).start()
    return {"ok": True}


@app.delete("/api/documentos/{doc_id}")
def borrar_documento(doc_id: int):
    db.ejecutar("DELETE FROM plazos WHERE documento_id = ?", (doc_id,))
    db.ejecutar("DELETE FROM documentos WHERE id = ?", (doc_id,))
    return {"ok": True}


@app.post("/api/subir")
async def subir(archivos: list[UploadFile] = File(...), texto: str = Form(""), recibido_en: str = Form("")):
    ids = []
    carpeta = ARCHIVOS / f"subido_{datetime.now():%Y%m%d%H%M%S}"
    for f in archivos:
        datos = await f.read()
        nombre = nombre_seguro(f.filename)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_bytes(datos)
        contenido = texto_pdf(datos) if nombre.lower().endswith(".pdf") else datos.decode("utf-8", "replace")
        fecha = recibido_en or (fecha_de_nombre_lexnet(nombre) or datetime.now()).isoformat(timespec="seconds")
        ids.append(servicio.crear_documento("subido", fecha, contenido, archivos=[f"{carpeta.name}/{nombre}"],
                                            asunto_email=nombre))
    if texto.strip():
        ids.append(servicio.crear_documento("subido", recibido_en or db.ahora(), texto, asunto_email="Texto pegado"))
    for i in ids:
        threading.Thread(target=servicio.procesar, args=(i,), daemon=True).start()
    return {"ids": ids}


@app.get("/api/archivo/{ruta:path}")
def archivo(ruta: str):
    p = (ARCHIVOS / ruta).resolve()
    if not str(p).startswith(str(ARCHIVOS.resolve())) or not p.exists():
        raise HTTPException(404)
    return FileResponse(p, filename=p.name)


# ------------------------------------------------------------------ plazos

@app.get("/api/plazos")
def plazos(completados: bool = False):
    return db.filas(f"""
        SELECT p.*, a.numero, a.tipo AS tipo_proc, a.juzgado, a.cliente
        FROM plazos p LEFT JOIN asuntos a ON a.id = p.asunto_id
        WHERE p.completado = ? ORDER BY p.vencimiento {'DESC' if completados else 'ASC'}, p.hora
        LIMIT 500""", (1 if completados else 0,))


class Plazo(BaseModel):
    descripcion: str | None = None
    asunto_id: int | None = None
    clase: str | None = None
    recepcion: str | None = None
    dias: int | None = None
    computo: str | None = None
    urgente: bool | None = None
    vencimiento: str | None = None
    hora: str | None = None
    completado: int | None = None
    notas: str | None = None


def _recalcular(datos: dict) -> dict:
    if datos.get("computo") and datos["computo"] != "fecha_fija" and datos.get("dias") and datos.get("recepcion"):
        r = servicio.calcular_plazo(datos["recepcion"], datos["dias"], datos["computo"], bool(datos.get("urgente")))
        datos.update(vencimiento=r["vencimiento"], dia_gracia=r["dia_gracia"], explicacion=r["explicacion"])
    return datos


@app.post("/api/plazos")
def crear_plazo(p: Plazo):
    datos = _recalcular({**p.model_dump(exclude_none=True), "creado_en": db.ahora()})
    if "urgente" in datos:
        datos["urgente"] = int(datos["urgente"])
    if not datos.get("vencimiento"):
        raise HTTPException(400, "Indica la fecha o los días del plazo.")
    return {"id": db.insertar("plazos", datos)}


@app.patch("/api/plazos/{plazo_id}")
def cambiar_plazo(plazo_id: int, p: Plazo):
    actual = db.fila("SELECT * FROM plazos WHERE id = ?", (plazo_id,))
    if not actual:
        raise HTTPException(404)
    cambios = p.model_dump(exclude_none=True)
    if {"recepcion", "dias", "computo", "urgente"} & cambios.keys():
        cambios = {k: v for k, v in _recalcular({**actual, **cambios}).items()
                   if k in cambios or k in ("vencimiento", "dia_gracia", "explicacion")}
    if "urgente" in cambios:
        cambios["urgente"] = int(cambios["urgente"])
    db.actualizar("plazos", plazo_id, cambios)
    return {"ok": True}


@app.delete("/api/plazos/{plazo_id}")
def borrar_plazo(plazo_id: int):
    db.ejecutar("DELETE FROM plazos WHERE id = ?", (plazo_id,))
    return {"ok": True}


@app.get("/api/plazos.ics")
def plazos_ics():
    """Plazos pendientes como calendario (para importar en Outlook, Google Calendar, Aranzadi Fusión...)."""
    def e(t: str) -> str:
        return (t or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Asistente de Procura//ES", "CALSCALE:GREGORIAN"]
    for p in plazos():
        titulo = f"{'VISTA' if p['clase'] == 'senalamiento' else 'VENCE'}: {p['descripcion']}"
        proc = " ".join(x for x in (p.get("tipo_proc"), p.get("numero")) if x)
        dia = p["vencimiento"].replace("-", "")
        lineas += ["BEGIN:VEVENT", f"UID:plazo-{p['id']}@asistente-procura", f"DTSTAMP:{datetime.now():%Y%m%dT%H%M%S}"]
        if p.get("hora"):
            lineas.append(f"DTSTART:{dia}T{p['hora'].replace(':', '')[:4]}00")
        else:
            lineas += [f"DTSTART;VALUE=DATE:{dia}"]
        lineas += [f"SUMMARY:{e(titulo + (' · ' + proc if proc else ''))}",
                   f"DESCRIPTION:{e(' · '.join(x for x in (p.get('juzgado'), p.get('cliente'), p.get('explicacion')) if x))}",
                   "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", "DESCRIPTION:Plazo mañana", "END:VALARM",
                   "END:VEVENT"]
    lineas.append("END:VCALENDAR")
    return StreamingResponse(io.BytesIO("\r\n".join(lineas).encode()), media_type="text/calendar",
                             headers={"Content-Disposition": 'attachment; filename="plazos.ics"'})


class Calculo(BaseModel):
    recepcion: str
    dias: int
    computo: str = "habiles"
    urgente: bool = False


@app.post("/api/calcular")
def calcular(c: Calculo):
    return servicio.calcular_plazo(c.recepcion, c.dias, c.computo, c.urgente)


# ------------------------------------------------------------------ asuntos

@app.get("/api/asuntos")
def asuntos(archivados: bool = False):
    return db.filas("""
        SELECT a.*, c.nombre AS abogado,
          (SELECT COUNT(*) FROM documentos d WHERE d.asunto_id = a.id) AS n_docs,
          (SELECT MIN(vencimiento) FROM plazos p WHERE p.asunto_id = a.id AND p.completado = 0) AS proximo_plazo,
          (SELECT MAX(recibido_en) FROM documentos d WHERE d.asunto_id = a.id) AS ultima_novedad
        FROM asuntos a LEFT JOIN contactos c ON c.id = a.abogado_id
        WHERE a.archivado = ? ORDER BY ultima_novedad DESC""", (1 if archivados else 0,))


@app.get("/api/asuntos/{asunto_id}")
def asunto(asunto_id: int):
    a = db.fila("SELECT * FROM asuntos WHERE id = ?", (asunto_id,))
    if not a:
        raise HTTPException(404)
    a["abogado"] = db.fila("SELECT * FROM contactos WHERE id = ?", (a["abogado_id"],)) if a["abogado_id"] else None
    a["documentos"] = db.filas("""SELECT id, recibido_en, titulo, categoria, resumen, urgencia, estado
                                  FROM documentos WHERE asunto_id = ? ORDER BY recibido_en DESC""", (asunto_id,))
    a["plazos"] = db.filas("""SELECT p.*, a.numero, a.tipo AS tipo_proc, a.juzgado, a.cliente
                              FROM plazos p LEFT JOIN asuntos a ON a.id = p.asunto_id
                              WHERE p.asunto_id = ? ORDER BY p.vencimiento""", (asunto_id,))
    return a


class Asunto(BaseModel):
    juzgado: str | None = None
    tipo: str | None = None
    numero: str | None = None
    nig: str | None = None
    materia: str | None = None
    jurisdiccion: str | None = None
    cliente: str | None = None
    contrario: str | None = None
    abogado_id: int | None = None
    notas: str | None = None
    archivado: int | None = None


@app.post("/api/asuntos")
def crear_asunto(a: Asunto):
    return {"id": db.insertar("asuntos", {**a.model_dump(exclude_none=True), "creado_en": db.ahora()})}


@app.patch("/api/asuntos/{asunto_id}")
def cambiar_asunto(asunto_id: int, a: Asunto):
    db.actualizar("asuntos", asunto_id, a.model_dump(exclude_unset=True))
    return {"ok": True}


# ------------------------------------------------------------------ contactos

@app.get("/api/contactos")
def contactos():
    return db.filas("""SELECT c.*, (SELECT COUNT(*) FROM asuntos a WHERE a.abogado_id = c.id) AS n_asuntos
                       FROM contactos c ORDER BY c.rol, c.nombre""")


class Contacto(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    email: str | None = None
    telefono: str | None = None
    despacho: str | None = None
    notas: str | None = None


@app.post("/api/contactos")
def crear_contacto(c: Contacto):
    if not c.nombre:
        raise HTTPException(400, "El nombre es obligatorio.")
    return {"id": db.insertar("contactos", {**c.model_dump(exclude_none=True), "creado_en": db.ahora()})}


@app.patch("/api/contactos/{cid}")
def cambiar_contacto(cid: int, c: Contacto):
    db.actualizar("contactos", cid, c.model_dump(exclude_unset=True))
    return {"ok": True}


@app.delete("/api/contactos/{cid}")
def borrar_contacto(cid: int):
    db.ejecutar("UPDATE asuntos SET abogado_id = NULL WHERE abogado_id = ?", (cid,))
    db.ejecutar("DELETE FROM contactos WHERE id = ?", (cid,))
    return {"ok": True}


# ------------------------------------------------------------------ asistente

class Chat(BaseModel):
    mensajes: list[dict]
    asunto_id: int | None = None


@app.post("/api/asistente")
def asistente(c: Chat):
    cfg = config.cargar()
    contexto = ""
    if c.asunto_id:
        a = asunto(c.asunto_id)
        docs = db.filas("SELECT recibido_en, titulo, texto FROM documentos WHERE asunto_id = ? ORDER BY recibido_en",
                        (c.asunto_id,))
        contexto = ia.contexto_asunto({**a, "abogado": (a["abogado"] or {}).get("nombre")}, docs, a["plazos"])
    mensajes = [{"role": m["role"], "content": m["content"]} for m in c.mensajes
                if m.get("role") in ("user", "assistant") and m.get("content")]
    return StreamingResponse(ia.asistente_stream(cfg, mensajes, contexto), media_type="text/plain; charset=utf-8")


class Texto(BaseModel):
    texto: str
    nombre: str = "escrito"


@app.post("/api/word")
def a_word(t: Texto):
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Times New Roman"
    estilo.font.size = Pt(12)
    for linea in t.texto.split("\n"):
        doc.add_paragraph(linea)
    buf = io.BytesIO()
    doc.save(buf)
    nombre = nombre_seguro(t.nombre) + ".docx"
    return StreamingResponse(io.BytesIO(buf.getvalue()),
                             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


# ------------------------------------------------------------------ ajustes

@app.get("/api/ajustes")
def ver_ajustes():
    return config.publico(config.cargar())


@app.put("/api/ajustes")
def guardar_ajustes(cambios: dict):
    # Los campos secretos que vuelven enmascarados no se tocan
    cambios = {k: v for k, v in cambios.items() if v != "********"}
    cfg = config.guardar(cambios)
    if "arrancar_con_el_ordenador" in cambios:
        error = sistema.configurar_arranque(bool(cambios["arrancar_con_el_ordenador"]))
        if error:
            raise HTTPException(500, error)
    correo.pedir_revision()
    return config.publico(cfg)


class PruebaIA(BaseModel):
    anthropic_api_key: str = ""


@app.post("/api/probar/ia")
def probar_ia(p: PruebaIA):
    cfg = config.cargar()
    clave = p.anthropic_api_key if p.anthropic_api_key and p.anthropic_api_key != "********" else cfg["anthropic_api_key"]
    try:
        ia.probar_clave(clave, cfg.get("modelo") or "claude-opus-5")
    except ia.ErrorIA as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


class PruebaCorreo(BaseModel):
    imap_host: str
    imap_puerto: int = 993
    imap_usuario: str
    imap_password: str = ""


@app.post("/api/probar/correo")
def probar_correo(p: PruebaCorreo):
    clave = p.imap_password if p.imap_password and p.imap_password != "********" else config.cargar()["imap_password"]
    try:
        return {"ok": True, "mensajes": correo.probar(p.imap_host, p.imap_puerto, p.imap_usuario, clave)}
    except Exception as e:
        raise HTTPException(400, correo.explicar_error(e, p.imap_host))


@app.post("/api/correo/revisar")
def revisar_correo():
    try:
        return correo.revisar_ahora()
    except Exception as e:
        raise HTTPException(400, str(e))


app.mount("/", StaticFiles(directory=RECURSOS / "static", html=True), name="static")
