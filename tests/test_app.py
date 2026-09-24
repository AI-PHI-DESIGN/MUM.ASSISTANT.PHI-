import email.message
import json

import pytest


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("PROCURA_DATA", str(tmp_path))
    import importlib

    from app import config, db
    importlib.reload(config)
    importlib.reload(db)
    from app import correo, servicio, main
    for m in (servicio, correo, main):
        importlib.reload(m)
    monkeypatch.setattr(main.correo, "arrancar_en_segundo_plano", lambda: None)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c, main


FICHA = {
    "categoria": "notificacion_resolucion", "titulo": "Diligencia: subsanar depósito",
    "tipo_resolucion": "Diligencia de ordenación", "fecha_resolucion": "2026-09-22",
    "resumen": "Hay que subsanar el depósito.", "accion_requerida": "Aportar justificante del depósito",
    "urgencia": "alta",
    "procedimiento": {"juzgado": "Sección Civil del Tribunal de Instancia de Ejemplo. Plaza nº 1",
                      "tipo": "Juicio verbal", "numero": "123/2026", "nig": "0000000000000000000",
                      "materia": "Reclamación de cantidad", "jurisdiccion": "civil",
                      "cliente": "Cliente Ejemplo S.L.", "contrario": "Contraria Ejemplo S.A."},
    "plazos": [
        {"clase": "actuacion", "descripcion": "Subsanar depósito", "dias": 2, "computo": "habiles",
         "fecha_fija": None, "hora": None, "urgente": False},
        {"clase": "senalamiento", "descripcion": "Vista", "dias": None, "computo": "fecha_fija",
         "fecha_fija": "2026-11-10", "hora": "10:30", "urgente": False},
    ],
    "contactos": [{"nombre": "Abogada Ejemplo", "rol": "abogado", "email": "abogada@ejemplo.es",
                   "telefono": None, "despacho": None}],
}


def test_flujo_completo(cliente):
    c, main = cliente
    assert c.get("/").status_code == 200
    r = c.post("/api/subir", files=[("archivos", ("2026_0000123_VRB_20260000000000020260923105724_001_Diligencia.txt",
                                                  b"texto de prueba", "text/plain"))])
    doc_id = r.json()["ids"][0]
    doc = c.get(f"/api/documentos/{doc_id}").json()
    assert doc["recibido_en"] == "2026-09-23T10:57:24"  # fecha sacada del nombre LexNET
    assert doc["estado"] == "pendiente"  # sin clave de IA se queda pendiente

    main.servicio.aplicar_ficha(main.db.fila("SELECT * FROM documentos WHERE id=?", (doc_id,)), FICHA, {})
    # un segundo documento del mismo asunto no duplica asunto ni contacto
    d2 = main.servicio.crear_documento("email", "2026-09-24T09:00:00", "x")
    main.servicio.aplicar_ficha(main.db.fila("SELECT * FROM documentos WHERE id=?", (d2,)), {**FICHA, "plazos": []}, {})

    asuntos = c.get("/api/asuntos").json()
    assert len(asuntos) == 1 and asuntos[0]["abogado"] == "Abogada Ejemplo"
    assert len(c.get("/api/contactos").json()) == 1
    plazos = c.get("/api/plazos").json()
    venc = {p["descripcion"]: p["vencimiento"] for p in plazos}
    assert venc == {"Subsanar depósito": "2026-09-28", "Vista": "2026-11-10"}

    # corregir el plazo recalcula el vencimiento
    pid = next(p["id"] for p in plazos if p["descripcion"] == "Subsanar depósito")
    c.patch(f"/api/plazos/{pid}", json={"dias": 5})
    assert next(p for p in c.get("/api/plazos").json() if p["id"] == pid)["vencimiento"] == "2026-10-01"

    ics = c.get("/api/plazos.ics").text
    assert "DTSTART:20261110T103000" in ics and "SUMMARY:VENCE: Subsanar depósito" in ics

    assert c.post("/api/word", json={"texto": "DIGO:\nhola", "nombre": "x"}).status_code == 200
    res = c.get("/api/resumen").json()
    assert res["configurado"] is False

    # ajustes: las claves no se devuelven en claro
    c.put("/api/ajustes", json={"anthropic_api_key": "sk-ant-xxx", "nombre_procuradora": "X"})
    assert c.get("/api/ajustes").json()["anthropic_api_key"] == "********"
    c.put("/api/ajustes", json={"anthropic_api_key": "********"})
    assert json.loads((main.config.CONFIG_PATH).read_text())["anthropic_api_key"] == "sk-ant-xxx"


def test_extraer_correo(tmp_path):
    from app.correo import _extraer
    m = email.message.EmailMessage()
    m["Subject"] = "Notificación"
    m.set_content("Cuerpo del aviso")
    m.add_attachment(b"%PDF-1.4 roto", maintype="application", subtype="pdf",
                     filename="2026_0000001_PAB_20260000000000020260923123645_001_AUTO.pdf")
    cuerpo, archivos, pdfs = _extraer(m, tmp_path)
    assert cuerpo == "Cuerpo del aviso"
    assert archivos == ["2026_0000001_PAB_20260000000000020260923123645_001_AUTO.pdf"]
    assert (tmp_path / archivos[0]).exists()
    assert "No se pudo leer" in pdfs[0][1]
