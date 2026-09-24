# Asistente de Procura

App local (FastAPI + SQLite + HTML/JS sin frameworks) para una procuradora: lee su correo, clasifica
notificaciones con Claude, calcula plazos procesales y redacta escritos.

- Receta completa, decisiones y problemas conocidos: `docs/COMO_SE_HIZO.md`. Si se pide un proyecto parecido,
  seguirla igual. Al terminar cambios relevantes, actualizarla.
- Manual de la usuaria (en español llano): `README.md`.
- Regla: la IA solo extrae datos; las fechas las calcula `app/plazos.py` (con tests).
- Nunca subir `data/` ni documentos reales de clientes al repositorio.
- Tests: `python -m pytest` (usan `PROCURA_DATA` en una carpeta temporal; no llaman a la IA).
- Interfaz y mensajes en español de España.
