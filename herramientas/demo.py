"""Rellena una base de datos con casos INVENTADOS para hacer capturas de pantalla o enseñar el programa.

Uso:  PROCURA_DATA=/tmp/demo python herramientas/demo.py
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db, servicio  # noqa: E402

HOY = date.today()


def dia(n: int) -> str:
    return (HOY + timedelta(days=n)).isoformat()


def proc(juzgado, tipo, numero, nig, materia, jurisdiccion, cliente, contrario):
    return dict(juzgado=juzgado, tipo=tipo, numero=numero, nig=nig, materia=materia,
                jurisdiccion=jurisdiccion, cliente=cliente, contrario=contrario)


CIVIL = proc("Sección Civil del Tribunal de Instancia de Valencia. Plaza nº 3", "Juicio verbal", "412/2026",
             "4625042120260004120", "Reclamación de cantidad", "civil", "Parquets Levante S.L.", "Diseños Turia S.L.")
PENAL = proc("Sección de lo Penal del Tribunal de Instancia de Valencia. Plaza nº 8", "Procedimiento abreviado",
             "88/2026", "4625043220250008800", "Apropiación indebida", "penal", "Andrés Molina Pérez", "Ministerio Fiscal")
ORDINARIO = proc("Sección Civil del Tribunal de Instancia de Torrent. Plaza nº 1", "Procedimiento ordinario", "230/2025",
                 "4624442120250002300", "Nulidad de condiciones generales", "civil", "Elena Ruiz Navarro", "Banco Ejemplo S.A.")

ABOGADA = {"nombre": "Lucía Martínez Soler", "rol": "abogado", "email": "lucia.martinez@ejemplo-abogados.es",
           "telefono": "600 111 222", "despacho": "Martínez Soler Abogados"}
ABOGADO = {"nombre": "Javier Ortega Blasco", "rol": "abogado", "email": "jortega@ejemplo-penal.es",
           "telefono": "600 333 444", "despacho": None}
ABOGADA2 = {"nombre": "Carmen Vidal Ferrer", "rol": "abogado", "email": "cvidal@ejemplo.es", "telefono": None,
            "despacho": "Vidal & Asociados"}


def plazo(clase, descripcion, dias=None, computo="habiles", fecha=None, hora=None, urgente=False):
    return dict(clase=clase, descripcion=descripcion, dias=dias, computo=computo, fecha_fija=fecha, hora=hora,
                urgente=urgente)


CASOS = [
    (dia(-1) + "T10:57:24", "Diligencia de ordenación.pdf",
     "DILIGENCIA DE ORDENACIÓN (texto de ejemplo inventado)...",
     dict(categoria="notificacion_resolucion", titulo="Diligencia de ordenación: subsanar depósito para recurrir",
          tipo_resolucion="Diligencia de ordenación", fecha_resolucion=dia(-2), urgencia="alta",
          resumen="Se une nuestro recurso de reposición, pero falta constituir el depósito para recurrir. Se conceden "
                  "2 días para subsanarlo; si no, se pone fin al recurso y la resolución queda firme.",
          accion_requerida="Constituir el depósito y aportar el justificante en 2 días hábiles. Avisar a la abogada.",
          procedimiento=CIVIL, plazos=[plazo("actuacion", "Subsanar depósito para recurrir", 2)], contactos=[ABOGADA])),
    (dia(-1) + "T12:36:45", "Auto.pdf", "AUTO (texto de ejemplo inventado)...",
     dict(categoria="notificacion_resolucion", titulo="Auto: se deja sin efecto la busca y captura",
          tipo_resolucion="Auto", fecha_resolucion=dia(-1), urgencia="media",
          resumen="El acusado ha sido localizado y puesto a disposición judicial. Se deja sin efecto la orden de busca "
                  "y captura y el procedimiento continúa.",
          accion_requerida="Informar al abogado. Recurrible en reforma (3 días) o apelación directa (5 días).",
          procedimiento=PENAL,
          plazos=[plazo("recurso", "Recurso de reforma y subsidiario de apelación", 3),
                  plazo("recurso", "Recurso de apelación directo", 5)], contactos=[ABOGADO])),
    (dia(-3) + "T09:15:02", "Decreto señalamiento.pdf", "DECRETO (texto de ejemplo inventado)...",
     dict(categoria="senalamiento", titulo="Decreto: señalamiento de audiencia previa",
          tipo_resolucion="Decreto", fecha_resolucion=dia(-4), urgencia="media",
          resumen="Se convoca a las partes a la audiencia previa. Deben comparecer con la documentación y, en su caso, "
                  "los peritos.",
          accion_requerida="Anotar la audiencia previa y confirmar asistencia con la abogada.",
          procedimiento=ORDINARIO,
          plazos=[plazo("senalamiento", "Audiencia previa", computo="fecha_fija", fecha=dia(33), hora="10:30")],
          contactos=[ABOGADA2])),
]


def main():
    db.iniciar()
    config.guardar({"nombre_procuradora": "MARÍA GARCÍA LÓPEZ", "bienvenida_hecha": True,
                    "anthropic_api_key": "sk-ant-ejemplo", "imap_auth": "microsoft", "correo_activo": False})
    for recibido, nombre, texto, ficha in CASOS:
        doc_id = servicio.crear_documento("subido", recibido, texto, archivos=[nombre], asunto_email=nombre)
        servicio.aplicar_ficha(db.fila("SELECT * FROM documentos WHERE id = ?", (doc_id,)), ficha, config.cargar())
    # Un correo de abogada ya leído
    d = servicio.crear_documento("email", dia(-2) + "T17:40:00", "Hola, te paso el escrito para presentar mañana...",
                                 remitente="Lucía Martínez Soler <lucia.martinez@ejemplo-abogados.es>",
                                 asunto_email="Escrito para presentar - JV 412/2026")
    servicio.aplicar_ficha(db.fila("SELECT * FROM documentos WHERE id = ?", (d,)), dict(
        categoria="email_abogado", titulo="Lucía Martínez envía escrito para presentar", tipo_resolucion=None,
        fecha_resolucion=None, urgencia="media", resumen="La abogada adjunta el escrito de alegaciones y pide "
        "presentarlo mañana.", accion_requerida="Presentar el escrito por LexNET mañana.", procedimiento=CIVIL,
        plazos=[], contactos=[ABOGADA]), config.cargar())
    db.ejecutar("UPDATE documentos SET leido = 1 WHERE id = ?", (d,))
    print("Datos de ejemplo creados en", config.DATA)


if __name__ == "__main__":
    main()
