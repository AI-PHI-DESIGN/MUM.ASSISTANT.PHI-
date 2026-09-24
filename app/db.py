"""Base de datos SQLite local (data/procura.db)."""
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from .config import DATA

DB_PATH = DATA / "procura.db"
_lock = threading.RLock()

ESQUEMA = """
CREATE TABLE IF NOT EXISTS contactos (
  id INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  rol TEXT DEFAULT 'abogado',          -- abogado | cliente | procurador | juzgado | otro
  email TEXT, telefono TEXT, despacho TEXT, notas TEXT,
  creado_en TEXT
);
CREATE TABLE IF NOT EXISTS asuntos (
  id INTEGER PRIMARY KEY,
  juzgado TEXT, tipo TEXT, numero TEXT, nig TEXT, materia TEXT, jurisdiccion TEXT,
  cliente TEXT, contrario TEXT,
  abogado_id INTEGER REFERENCES contactos(id),
  notas TEXT, archivado INTEGER DEFAULT 0,
  creado_en TEXT
);
CREATE TABLE IF NOT EXISTS documentos (
  id INTEGER PRIMARY KEY,
  origen TEXT,                          -- email | subido
  recibido_en TEXT,
  remitente TEXT, asunto_email TEXT, archivos TEXT,
  texto TEXT,
  estado TEXT DEFAULT 'pendiente',      -- pendiente | procesado | error
  error TEXT,
  categoria TEXT, titulo TEXT, tipo_resolucion TEXT, resumen TEXT, accion TEXT, urgencia TEXT,
  datos TEXT,
  asunto_id INTEGER REFERENCES asuntos(id),
  leido INTEGER DEFAULT 0,
  email_uid TEXT,
  creado_en TEXT
);
CREATE TABLE IF NOT EXISTS plazos (
  id INTEGER PRIMARY KEY,
  asunto_id INTEGER REFERENCES asuntos(id),
  documento_id INTEGER REFERENCES documentos(id),
  clase TEXT DEFAULT 'actuacion',       -- actuacion | recurso | senalamiento
  descripcion TEXT,
  recepcion TEXT, dias INTEGER, computo TEXT, urgente INTEGER DEFAULT 0,
  vencimiento TEXT, dia_gracia TEXT, hora TEXT, explicacion TEXT,
  completado INTEGER DEFAULT 0,
  notas TEXT, creado_en TEXT
);
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT);
"""


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def iniciar() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with conexion() as c:
        c.executescript(ESQUEMA)


@contextmanager
def conexion():
    with _lock:
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
            c.commit()
        finally:
            c.close()


def filas(sql: str, params=()) -> list[dict]:
    with conexion() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def fila(sql: str, params=()) -> dict | None:
    r = filas(sql, params)
    return r[0] if r else None


def ejecutar(sql: str, params=()) -> int:
    with conexion() as c:
        return c.execute(sql, params).lastrowid


def insertar(tabla: str, datos: dict) -> int:
    cols = ", ".join(datos)
    marcas = ", ".join("?" for _ in datos)
    return ejecutar(f"INSERT INTO {tabla} ({cols}) VALUES ({marcas})", tuple(datos.values()))


def actualizar(tabla: str, id_: int, datos: dict) -> None:
    if not datos:
        return
    sets = ", ".join(f"{k} = ?" for k in datos)
    ejecutar(f"UPDATE {tabla} SET {sets} WHERE id = ?", (*datos.values(), id_))


def get_estado(clave: str, defecto: str | None = None) -> str | None:
    r = fila("SELECT valor FROM estado WHERE clave = ?", (clave,))
    return r["valor"] if r else defecto


def set_estado(clave: str, valor: str) -> None:
    ejecutar("INSERT INTO estado (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
             (clave, valor))


def _norm(s: str | None) -> str:
    return re.sub(r"[^0-9a-z]", "", (s or "").lower())


def buscar_o_crear_asunto(p: dict) -> int | None:
    """Localiza el asunto por NIG o por (número + juzgado); si no existe lo crea."""
    nig, numero, juzgado = p.get("nig"), p.get("numero"), p.get("juzgado")
    if not (nig or numero):
        return None
    for a in filas("SELECT * FROM asuntos"):
        if nig and _norm(a["nig"]) == _norm(nig):
            return a["id"]
        if numero and _norm(a["numero"]) == _norm(numero) and _norm(a["juzgado"]) == _norm(juzgado):
            return a["id"]
    campos = {k: p.get(k) for k in ("juzgado", "tipo", "numero", "nig", "materia", "jurisdiccion", "cliente", "contrario")}
    return insertar("asuntos", {**campos, "creado_en": ahora()})


def buscar_o_crear_contacto(c: dict) -> int | None:
    nombre = (c.get("nombre") or "").strip()
    if not nombre:
        return None
    for x in filas("SELECT * FROM contactos"):
        if c.get("email") and _norm(x["email"]) == _norm(c["email"]):
            break
        if _norm(x["nombre"]) == _norm(nombre):
            break
    else:
        return insertar("contactos", {"nombre": nombre, "rol": c.get("rol") or "otro", "email": c.get("email"),
                                      "telefono": c.get("telefono"), "despacho": c.get("despacho"), "creado_en": ahora()})
    # Completa datos que falten sin pisar lo que ya haya escrito ella
    faltan = {k: c[k] for k in ("email", "telefono", "despacho") if c.get(k) and not x[k]}
    actualizar("contactos", x["id"], faltan)
    return x["id"]
