@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Asistente de Procura
if not exist .venv\Scripts\python.exe (
  echo Primera vez: instalando el programa. Tarda un par de minutos...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist .venv\Scripts\python.exe (
    echo.
    echo No se encuentra Python. Instalalo desde https://www.python.org/downloads/
    echo marcando la casilla "Add python.exe to PATH" y vuelve a abrir este archivo.
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install --upgrade pip >nul
  .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python -m app
pause
