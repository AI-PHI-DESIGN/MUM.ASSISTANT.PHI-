from datetime import date, datetime

from app.plazos import Calendario, calcular, domingo_de_pascua, parsear_festivos

CAL = Calendario(festivos=parsear_festivos("2026-10-09\n2026-03-19"))


def test_pascua():
    assert domingo_de_pascua(2026) == date(2026, 4, 5)
    assert domingo_de_pascua(2027) == date(2027, 3, 28)


def test_subsanar_deposito_dos_dias():
    # Diligencia recibida por LexNET el miércoles 23/09/2026 a las 10:57
    r = calcular(CAL, datetime(2026, 9, 23, 10, 57), 2)
    assert r.notificacion == "2026-09-24"
    assert r.inicio == "2026-09-25"
    assert r.vencimiento == "2026-09-28"  # viernes 25 + lunes 28
    assert r.dia_gracia == "2026-09-29"


def test_cinco_dias_salta_festivo_autonomico():
    # Recibida lunes 05/10; 9 de octubre festivo en la C. Valenciana; 12 festivo nacional
    r = calcular(CAL, date(2026, 10, 5), 5)
    assert r.notificacion == "2026-10-06"
    assert r.vencimiento == "2026-10-15"  # 7, 8, 13, 14, 15


def test_agosto_inhabil_y_urgente():
    r = calcular(CAL, date(2026, 7, 30), 3)
    assert r.notificacion == "2026-07-31"
    assert r.vencimiento == "2026-09-03"
    r2 = calcular(CAL, date(2026, 7, 30), 3, urgente=True)
    assert r2.vencimiento == "2026-08-05"


def test_recepcion_en_sabado():
    r = calcular(CAL, date(2026, 9, 26), 1)
    assert r.notificacion == "2026-09-29"
    assert r.vencimiento == "2026-09-30"


def test_navidad():
    r = calcular(CAL, date(2026, 12, 22), 1)
    assert r.notificacion == "2026-12-23"
    assert r.vencimiento == "2027-01-07"


def test_meses():
    r = calcular(CAL, date(2026, 1, 28), 1, computo="meses")
    assert r.notificacion == "2026-01-29"
    assert r.vencimiento == "2026-03-02"  # 28/02 sábado -> lunes 02/03
