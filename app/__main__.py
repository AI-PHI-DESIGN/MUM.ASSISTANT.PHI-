"""Arranca la aplicación y abre el navegador:  python -m app  (o el .exe)

--segundo-plano: no abre el navegador (se usa al encender el ordenador).
"""
import sys
import threading
import urllib.request


def _ya_esta_en_marcha(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/api/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> None:
    from app import config, sistema

    segundo_plano = "--segundo-plano" in sys.argv
    if _ya_esta_en_marcha(sistema.URL):
        # Doble clic con el programa ya abierto: solo mostrarlo
        if not segundo_plano:
            sistema.abrir_navegador()
        return

    config.DATA.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or config.CONGELADO:
        # El .exe no tiene consola: los mensajes van a un archivo de registro
        registro = open(config.DATA / "registro.log", "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = registro

    cfg = config.cargar()
    if cfg.get("arrancar_con_el_ordenador") and cfg.get("bienvenida_hecha"):
        sistema.configurar_arranque(True)  # por si el programa se ha movido de carpeta

    import uvicorn
    from app.main import app

    if not segundo_plano:
        threading.Timer(1.5, sistema.abrir_navegador).start()
    print(f"\n  Asistente de Procura en marcha: {sistema.URL}\n  (no cierres esta ventana mientras lo uses)\n")
    uvicorn.run(app, host="127.0.0.1", port=sistema.PUERTO, log_level="warning", log_config=None)


if __name__ == "__main__":
    main()
