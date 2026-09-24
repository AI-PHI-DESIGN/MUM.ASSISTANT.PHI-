"""Arranca la aplicación y abre el navegador:  python -m app"""
import threading
import webbrowser

import uvicorn

PUERTO = 8765


def main() -> None:
    url = f"http://127.0.0.1:{PUERTO}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  Asistente de Procura en marcha: {url}\n  (no cierres esta ventana mientras lo uses)\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=PUERTO, log_level="warning")


if __name__ == "__main__":
    main()
