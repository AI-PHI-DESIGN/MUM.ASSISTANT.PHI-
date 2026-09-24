#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Primera vez: instalando el programa. Tarda un par de minutos..."
  python3 -m venv .venv || { echo "Instala Python desde https://www.python.org/downloads/"; read -r; exit 1; }
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
fi
.venv/bin/python -m app
