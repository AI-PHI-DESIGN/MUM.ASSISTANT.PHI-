"""Inicio de sesión con Microsoft (Outlook / Hotmail / Microsoft 365) para leer el correo por IMAP.

Microsoft ya no deja entrar por IMAP con usuario y contraseña: hay que usar OAuth2. Se usa el
«flujo de código de dispositivo»: el programa muestra un código, ella lo escribe en
microsoft.com/devicelogin, inicia sesión y acepta. El permiso se guarda en
data/microsoft_token.json y se renueva solo.

Requiere dar de alta la aplicación una vez en Microsoft Entra (ver docs/MICROSOFT.md) y poner su
«Id. de aplicación (cliente)» en CLIENT_ID_POR_DEFECTO o en Ajustes.
"""
from __future__ import annotations

import threading

import msal

from . import config

# Id. de aplicación (cliente) registrado en Microsoft Entra. No es secreto.
CLIENT_ID_POR_DEFECTO = "2139522e-3dfa-4648-8df9-a6b0ad0cd683"
AUTORIDAD = "https://login.microsoftonline.com/common"
PERMISOS = ["https://outlook.office.com/IMAP.AccessAsUser.All"]
HOST_IMAP = "outlook.office365.com"

_lock = threading.Lock()
_estado: dict = {"estado": "desconectado", "usuario": None, "error": None, "codigo": None, "url": None}


class ErrorMicrosoft(Exception):
    pass


def _client_id() -> str:
    cid = (config.cargar().get("ms_client_id") or CLIENT_ID_POR_DEFECTO).strip()
    if not cid:
        raise ErrorMicrosoft("Falta dar de alta el programa en Microsoft (lo hace quien lo instaló; "
                             "ver docs/MICROSOFT.md) y poner su identificador en Ajustes.")
    return cid


def _ruta_cache():
    return config.DATA / "microsoft_token.json"


def _app() -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache]:
    cache = msal.SerializableTokenCache()
    ruta = _ruta_cache()
    if ruta.exists():
        cache.deserialize(ruta.read_text(encoding="utf-8"))
    return msal.PublicClientApplication(_client_id(), authority=AUTORIDAD, token_cache=cache), cache


def _guardar(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        config.DATA.mkdir(parents=True, exist_ok=True)
        _ruta_cache().write_text(cache.serialize(), encoding="utf-8")


def usuario_conectado() -> str | None:
    try:
        app, _ = _app()
    except ErrorMicrosoft:
        return None
    cuentas = app.get_accounts()
    return cuentas[0]["username"] if cuentas else None


def estado() -> dict:
    with _lock:
        e = dict(_estado)
    if e["estado"] != "esperando":
        u = usuario_conectado()
        e.update(estado="conectado" if u else e["estado"] if e["estado"] == "error" else "desconectado", usuario=u)
    return e


def iniciar() -> dict:
    """Empieza el inicio de sesión y devuelve el código que hay que escribir en la web de Microsoft."""
    app, cache = _app()
    flujo = app.initiate_device_flow(scopes=PERMISOS)
    if "user_code" not in flujo:
        raise ErrorMicrosoft(f"Microsoft no ha dado un código: {flujo.get('error_description') or flujo.get('error')}")
    with _lock:
        _estado.update(estado="esperando", error=None, codigo=flujo["user_code"], url=flujo["verification_uri"])

    def esperar():
        resultado = app.acquire_token_by_device_flow(flujo)  # bloquea hasta que acepta o caduca (~15 min)
        _guardar(cache)
        with _lock:
            if "access_token" in resultado:
                _estado.update(estado="conectado", error=None, codigo=None)
            else:
                _estado.update(estado="error", codigo=None,
                               error=_explicar(resultado.get("error"), resultado.get("error_description")))

    threading.Thread(target=esperar, daemon=True).start()
    return {"codigo": flujo["user_code"], "url": flujo["verification_uri"]}


def _explicar(error: str | None, descripcion: str | None) -> str:
    if error == "authorization_declined":
        return "Se canceló el inicio de sesión."
    if error in ("expired_token", "code_expired"):
        return "El código caducó. Pulsa otra vez «Conectar con Outlook»."
    if descripcion and "AADSTS7000218" in descripcion:
        return ("Falta un ajuste en el alta de Microsoft: en Entra → la aplicación → Autenticación, activar "
                "«Permitir flujos de clientes públicos» y guardar. Después, volver a conectar.")
    if descripcion and ("AADSTS65001" in descripcion or "admin" in descripcion.lower()):
        return ("Tu cuenta es de una organización que no deja autorizar programas. "
                "Hay que pedir permiso al administrador del correo.")
    return f"No se pudo conectar con Microsoft: {descripcion or error}"


def token() -> tuple[str, str]:
    """Devuelve (usuario, token de acceso) renovándolo si hace falta."""
    app, cache = _app()
    cuentas = app.get_accounts()
    if not cuentas:
        raise ErrorMicrosoft("La cuenta de Outlook no está conectada. Ve a Ajustes → «Conectar con Outlook».")
    resultado = app.acquire_token_silent(PERMISOS, account=cuentas[0])
    _guardar(cache)
    if not resultado or "access_token" not in resultado:
        raise ErrorMicrosoft("Hay que volver a conectar la cuenta de Outlook (Ajustes → «Conectar con Outlook»).")
    return cuentas[0]["username"], resultado["access_token"]


def desconectar() -> None:
    ruta = _ruta_cache()
    if ruta.exists():
        ruta.unlink()
    with _lock:
        _estado.update(estado="desconectado", usuario=None, error=None, codigo=None, url=None)


def autenticar_imap(imap) -> str:
    """Inicia sesión en un imaplib.IMAP4_SSL con XOAUTH2. Devuelve el usuario."""
    usuario, tok = token()
    imap.authenticate("XOAUTH2", lambda _: f"user={usuario}\x01auth=Bearer {tok}\x01\x01".encode())
    return usuario
