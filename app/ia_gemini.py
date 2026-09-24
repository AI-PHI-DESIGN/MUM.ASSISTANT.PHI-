"""Google Gemini (plan gratuito de Google AI Studio) como alternativa a Claude.

Mismo comportamiento que las funciones de Claude en ia.py: clasificar con ficha JSON y asistente en
streaming. Ojo: en el plan gratuito Google puede usar lo enviado para mejorar sus productos.
"""
from __future__ import annotations

import json
import re

from google import genai
from google.genai import errors, types

MODELO_POR_DEFECTO = "gemini-2.5-flash"


def _error(e: Exception):
    """Traduce los errores de Google a ErrorIA."""
    from .ia import ErrorIA
    if isinstance(e, errors.ClientError):
        texto = str(e)
        if "API_KEY_INVALID" in texto or "API key not valid" in texto:
            return ErrorIA("La clave de Gemini no es válida. Cópiala de nuevo (empieza por AIza).")
        if e.code == 429:
            return ErrorIA("Se ha alcanzado el límite gratuito de Gemini por ahora; se reintentará solo más tarde.",
                           reintentable=True)
        if e.code == 404:
            err = ErrorIA("El modelo de Gemini configurado ya no existe. Pulsa «Comprobar clave» en Ajustes.")
            err.modelo_perdido = True
            return err
        if e.code == 403:
            return ErrorIA("Gemini no permite usar esta clave (¿está en un país o cuenta sin acceso?).")
        return ErrorIA(f"Error de Gemini ({e.code}): {getattr(e, 'message', '') or texto[:200]}")
    if isinstance(e, errors.ServerError):
        return ErrorIA("Gemini no responde ahora mismo; se reintentará más tarde.", reintentable=True)
    return ErrorIA("Sin conexión con Gemini. ¿Hay internet?", reintentable=True)


def _cliente(clave: str) -> genai.Client:
    return genai.Client(api_key=clave)


def elegir_modelo(clave: str) -> str:
    """Comprueba la clave y elige el mejor modelo «flash» estable disponible (el del plan gratuito)."""
    try:
        cliente = _cliente(clave)  # hay que mantenerlo en una variable: si no, se cierra antes de usarlo
        nombres = [m.name.removeprefix("models/") for m in cliente.models.list()]
    except Exception as e:
        raise _error(e)
    estables = []
    for n in nombres:
        m = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-flash", n)
        if m:
            estables.append((float(m.group(1)), n))
    if estables:
        return max(estables)[1]
    if "gemini-flash-latest" in nombres:
        return "gemini-flash-latest"
    return MODELO_POR_DEFECTO


# ---------------------------------------------------------------- esquema

_TIPOS = {"string": types.Type.STRING, "integer": types.Type.INTEGER, "boolean": types.Type.BOOLEAN,
          "object": types.Type.OBJECT, "array": types.Type.ARRAY, "number": types.Type.NUMBER}


def a_esquema_gemini(s: dict) -> types.Schema:
    """Convierte el JSON Schema de ia.ESQUEMA al formato de Gemini (nullable en vez de ["x", "null"])."""
    tipo = s.get("type")
    nullable = False
    if isinstance(tipo, list):
        nullable = "null" in tipo
        tipo = next(t for t in tipo if t != "null")
    campos: dict = {"type": _TIPOS[tipo]}
    if nullable:
        campos["nullable"] = True
    if "enum" in s:
        campos["enum"] = [v for v in s["enum"] if v is not None]
    if "properties" in s:
        campos["properties"] = {k: a_esquema_gemini(v) for k, v in s["properties"].items()}
        campos["property_ordering"] = list(s["properties"])
        campos["required"] = list(s.get("required", []))
    if "items" in s:
        campos["items"] = a_esquema_gemini(s["items"])
    return types.Schema(**campos)


# ---------------------------------------------------------------- llamadas

def clasificar(clave: str, modelo: str, sistema: str, contenido: str, esquema: dict) -> dict:
    from .ia import ErrorIA
    cliente = _cliente(clave)
    try:
        resp = cliente.models.generate_content(
            model=modelo,
            contents=contenido,
            config=types.GenerateContentConfig(
                system_instruction=sistema,
                response_mime_type="application/json",
                response_schema=a_esquema_gemini(esquema),
                max_output_tokens=16000,
            ),
        )
    except Exception as e:
        raise _error(e)
    if resp.prompt_feedback and resp.prompt_feedback.block_reason:
        raise ErrorIA("Gemini no ha querido procesar este documento.")
    fin = resp.candidates[0].finish_reason if resp.candidates else None
    if fin == types.FinishReason.MAX_TOKENS:
        raise ErrorIA("La respuesta de Gemini quedó cortada.")
    try:
        return json.loads(resp.text or "")
    except json.JSONDecodeError:
        raise ErrorIA("Gemini devolvió una ficha que no se pudo leer.", reintentable=True)


def asistente_stream(clave: str, modelo: str, sistema: str, mensajes: list[dict]):
    contenidos = [types.Content(role="model" if m["role"] == "assistant" else "user",
                                parts=[types.Part(text=m["content"])]) for m in mensajes]
    cliente = _cliente(clave)
    try:
        for trozo in cliente.models.generate_content_stream(
                model=modelo, contents=contenidos,
                config=types.GenerateContentConfig(system_instruction=sistema, max_output_tokens=32000)):
            if trozo.text:
                yield trozo.text
    except Exception as e:
        yield f"[{_error(e)}]"
