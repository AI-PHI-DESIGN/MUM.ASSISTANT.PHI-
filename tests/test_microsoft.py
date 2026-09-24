import time


class FalsaApp:
    """Imita msal.PublicClientApplication."""
    cuentas = []

    def __init__(self, client_id, authority=None, token_cache=None):
        self.cache = token_cache

    def initiate_device_flow(self, scopes=None):
        return {"user_code": "ABC123", "verification_uri": "https://microsoft.com/devicelogin"}

    def acquire_token_by_device_flow(self, flujo):
        time.sleep(0.2)
        FalsaApp.cuentas = [{"username": "maria@outlook.com"}]
        return {"access_token": "tok"}

    def get_accounts(self):
        return FalsaApp.cuentas

    def acquire_token_silent(self, scopes, account=None):
        return {"access_token": "tok-renovado"}


def test_flujo_microsoft(tmp_path, monkeypatch):
    monkeypatch.setenv("PROCURA_DATA", str(tmp_path))
    import importlib
    from app import config
    importlib.reload(config)
    from app import microsoft
    importlib.reload(microsoft)
    monkeypatch.setattr(microsoft.msal, "PublicClientApplication", FalsaApp)
    config.guardar({"ms_client_id": "id-de-prueba"})

    r = microsoft.iniciar()
    assert r == {"codigo": "ABC123", "url": "https://microsoft.com/devicelogin"}
    assert microsoft.estado()["estado"] == "esperando"
    time.sleep(0.5)
    e = microsoft.estado()
    assert e["estado"] == "conectado" and e["usuario"] == "maria@outlook.com"

    class Imap:
        def authenticate(self, mecanismo, fn):
            self.mecanismo, self.cadena = mecanismo, fn(None)
    imap = Imap()
    assert microsoft.autenticar_imap(imap) == "maria@outlook.com"
    assert imap.mecanismo == "XOAUTH2"
    assert imap.cadena == b"user=maria@outlook.com\x01auth=Bearer tok-renovado\x01\x01"
