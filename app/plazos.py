"""Cómputo de plazos procesales (LEC / LOPJ).

Reglas aplicadas (todas configurables desde Ajustes):
- Inhábiles: sábados, domingos, festivos nacionales, autonómicos y locales
  (los de la lista de Ajustes), 24 y 31 de diciembre, agosto y, si se
  activa, del 24 de diciembre al 6 de enero.
- Notificación a procurador por medios electrónicos (art. 151.2 LEC): se tiene
  por realizada el día hábil siguiente a la recepción.
- El plazo empieza a contar el día hábil siguiente a la notificación (art. 133 LEC).
- Día de gracia (art. 135.5 LEC): el escrito puede presentarse hasta las 15:00
  del día hábil siguiente al vencimiento.

El resultado es orientativo: la procuradora debe revisarlo siempre.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta


def domingo_de_pascua(anyo: int) -> date:
    """Algoritmo de Butcher (calendario gregoriano)."""
    a = anyo % 19
    b, c = divmod(anyo, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(anyo, mes, dia)


def festivos_nacionales(anyo: int) -> set[date]:
    fijos = [(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)]
    dias = {date(anyo, m, d) for m, d in fijos}
    dias.add(domingo_de_pascua(anyo) - timedelta(days=2))  # Viernes Santo
    return dias


@dataclass
class Calendario:
    festivos: set[date]
    agosto_inhabil: bool = True
    navidad_inhabil: bool = True  # 24 dic - 6 ene

    def es_habil(self, d: date, urgente: bool = False) -> bool:
        """urgente=True: agosto y Navidad cuentan como hábiles (p. ej. instrucción penal)."""
        if d.weekday() >= 5:
            return False
        if d in self.festivos or d in festivos_nacionales(d.year):
            return False
        if (d.month, d.day) in ((12, 24), (12, 31)):
            return False
        if urgente:
            return True
        if self.agosto_inhabil and d.month == 8:
            return False
        if self.navidad_inhabil and ((d.month == 12 and d.day >= 24) or (d.month == 1 and d.day <= 6)):
            return False
        return True

    def siguiente_habil(self, d: date, urgente: bool = False) -> date:
        d += timedelta(days=1)
        while not self.es_habil(d, urgente):
            d += timedelta(days=1)
        return d

    def habil_o_siguiente(self, d: date, urgente: bool = False) -> date:
        return d if self.es_habil(d, urgente) else self.siguiente_habil(d, urgente)


@dataclass
class ResultadoPlazo:
    recepcion: str
    notificacion: str
    inicio: str
    vencimiento: str
    dia_gracia: str
    explicacion: str

    def dict(self) -> dict:
        return asdict(self)


def _sumar_meses(d: date, meses: int) -> date:
    m = d.month - 1 + meses
    anyo, mes = d.year + m // 12, m % 12 + 1
    for dia in (d.day, 30, 29, 28):
        try:
            return date(anyo, mes, dia)
        except ValueError:
            continue
    raise ValueError(d)


def calcular(cal: Calendario, recepcion: date | datetime, dias: int, computo: str = "habiles",
             urgente: bool = False, notificacion_dia_siguiente: bool = True) -> ResultadoPlazo:
    """Calcula el vencimiento de un plazo.

    computo: "habiles" | "naturales" | "meses"
    notificacion_dia_siguiente: aplicar art. 151.2 LEC (notificación a procurador
    el día hábil siguiente a la recepción). Desactivar si la fecha dada ya es la
    de notificación.
    """
    if isinstance(recepcion, datetime):
        recepcion = recepcion.date()
    pasos = []
    rec = cal.habil_o_siguiente(recepcion, urgente)
    if rec != recepcion:
        pasos.append(f"Recibida en día inhábil ({recepcion:%d/%m/%Y}); se tiene por recibida el {rec:%d/%m/%Y}.")
    if notificacion_dia_siguiente:
        notif = cal.siguiente_habil(rec, urgente)
        pasos.append(f"Notificación efectiva (art. 151.2 LEC): {notif:%d/%m/%Y}.")
    else:
        notif = rec
    if computo == "habiles":
        d = notif
        for _ in range(dias):
            d = cal.siguiente_habil(d, urgente)
        inicio = cal.siguiente_habil(notif, urgente)
        pasos.append(f"Cuenta {dias} días hábiles desde el {inicio:%d/%m/%Y}.")
    elif computo == "naturales":
        inicio = notif + timedelta(days=1)
        d = cal.habil_o_siguiente(notif + timedelta(days=dias), urgente)
        pasos.append(f"Cuenta {dias} días naturales desde el {inicio:%d/%m/%Y} (si acaba en inhábil, pasa al siguiente hábil).")
    elif computo == "meses":
        inicio = notif + timedelta(days=1)
        d = cal.habil_o_siguiente(_sumar_meses(notif, dias), urgente)
        pasos.append(f"Cuenta {dias} mes(es) de fecha a fecha desde la notificación (si acaba en inhábil, pasa al siguiente hábil).")
    else:
        raise ValueError(f"Cómputo desconocido: {computo}")
    gracia = cal.siguiente_habil(d, urgente)
    pasos.append(f"Vence el {d:%d/%m/%Y}; día de gracia hasta las 15:00 del {gracia:%d/%m/%Y} (art. 135.5 LEC).")
    return ResultadoPlazo(
        recepcion=recepcion.isoformat(), notificacion=notif.isoformat(), inicio=inicio.isoformat(),
        vencimiento=d.isoformat(), dia_gracia=gracia.isoformat(), explicacion=" ".join(pasos),
    )


def parsear_festivos(texto: str) -> set[date]:
    """Acepta una fecha por línea en formato AAAA-MM-DD o DD/MM/AAAA; ignora comentarios (#)."""
    out = set()
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                out.add(datetime.strptime(linea, fmt).date())
                break
            except ValueError:
                continue
    return out
