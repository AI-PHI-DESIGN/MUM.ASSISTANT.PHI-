import json
from types import SimpleNamespace

import pytest
from google.genai import errors, types

from app import ia, ia_gemini
from tests.test_app import FICHA


def test_esquema_convertido():
    s = ia_gemini.a_esquema_gemini(ia.ESQUEMA)
    assert s.type == types.Type.OBJECT
    assert s.properties["tipo_resolucion"].nullable is True
    assert s.properties["procedimiento"].properties["jurisdiccion"].enum == ["civil", "penal", "contencioso", "social", "otro"]
    assert s.properties["plazos"].items.properties["dias"].type == types.Type.INTEGER
    assert s.property_ordering[0] == "categoria"


class Modelos:
    def __init__(self, respuestas):
        self.respuestas, self.llamadas = list(respuestas), []

    def generate_content(self, model, contents, config):
        self.llamadas.append(model)
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(text=json.dumps(r), prompt_feedback=None,
                               candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)])

    def list(self):
        return [SimpleNamespace(name=n) for n in ("models/gemini-2.5-flash", "models/gemini-3.0-flash",
                                                  "models/gemini-3.0-flash-lite", "models/gemini-2.5-pro")]


def _cfg():
    return {"proveedor_ia": "gemini", "gemini_api_key": "AIza-x", "modelo_gemini": "gemini-viejo",
            "nombre_procuradora": "X"}


def test_clasificar_y_modelo_retirado(monkeypatch, tmp_path):
    monkeypatch.setattr(ia.config, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(ia.config, "DATA", tmp_path)
    no_existe = errors.ClientError(404, {"error": {"code": 404, "message": "not found", "status": "NOT_FOUND"}})
    modelos = Modelos([no_existe, FICHA])
    monkeypatch.setattr(ia_gemini, "_cliente", lambda clave: SimpleNamespace(models=modelos))
    assert ia.clasificar(_cfg(), "texto", "cab") == FICHA
    assert modelos.llamadas == ["gemini-viejo", "gemini-3.0-flash"]  # eligió el flash estable más nuevo
    assert ia.config.cargar()["modelo_gemini"] == "gemini-3.0-flash"


def test_limite_gratuito_es_reintentable(monkeypatch):
    limite = errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    monkeypatch.setattr(ia_gemini, "_cliente", lambda clave: SimpleNamespace(models=Modelos([limite])))
    with pytest.raises(ia.ErrorIA) as e:
        ia.clasificar(_cfg(), "texto", "cab")
    assert e.value.reintentable


def test_clave_invalida_real():
    with pytest.raises(ia.ErrorIA) as e:
        ia.probar_clave("gemini", "", {})
    assert "Escribe la clave" in str(e.value)
