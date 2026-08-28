"""`manage.py export_ical`."""
import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain import extraction as ex
from tests.analysis_helpers import make_activity, mini_school, place
from tests.test_ical import etichette, eventi

pytestmark = pytest.mark.django_db


def _scuola():
    env = mini_school(days=1, slots=2)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0)),
                            (1, dt.time(9, 0), dt.time(10, 0))])
    env["a"] = make_activity(env["subject"], classes=[env["klass"]],
                             teachers=[env["teacher"]])
    env["b"] = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], env["a"], 0, 0)
    place(env["schedule"], env["b"], 0, 1)
    return env


def _esegui(**kw):
    out = StringIO()
    call_command("export_ical", stdout=out, **kw)
    return out.getvalue()


def test_senza_out_scrive_sullo_standard_output():
    env = _scuola()
    testo = _esegui(schedule=env["schedule"].pk)
    assert testo.startswith("BEGIN:VCALENDAR")
    assert len(eventi(testo)) == 8       # due attività per quattro settimane


def test_la_risorsa_restringe_e_da_il_nome_al_calendario():
    env = _scuola()
    testo = _esegui(schedule=env["schedule"].pk, risorsa=env["teacher"].pk)
    assert len(eventi(testo)) == 4
    assert "X-WR-CALNAME:Orario — Rossi Anna" in testo


def test_l_estrazione_restringe():
    env = _scuola()
    ex.salva("solo-b", [env["b"].pk])
    testo = _esegui(schedule=env["schedule"].pk, estrazione="solo-b")
    assert {e["DTSTART"][-6:] for e in eventi(testo)} == {"090000"}


def test_risorsa_ed_estrazione_si_intersecano():
    """Due criteri sono una **congiunzione**: il docente non ha niente in
    comune con `solo-b`, e il calendario è vuoto invece di essere l'unione."""
    env = _scuola()
    ex.salva("solo-b", [env["b"].pk])
    testo = _esegui(schedule=env["schedule"].pk, risorsa=env["teacher"].pk,
                    estrazione="solo-b")
    assert eventi(testo) == []


def test_senza_etichette_il_rifiuto_nomina_le_fasce():
    env = mini_school(days=1, slots=2)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    place(env["schedule"],
          make_activity(env["subject"], classes=[env["klass"]]), 0, 1)

    with pytest.raises(CommandError) as errore:
        _esegui(schedule=env["schedule"].pk)
    assert "[1]" in str(errore.value)
    assert "1 su 2" in str(errore.value)


def test_risorsa_inesistente():
    env = _scuola()
    with pytest.raises(CommandError):
        _esegui(schedule=env["schedule"].pk, risorsa=999999)


def test_out_scrive_il_file(tmp_path):
    env = _scuola()
    percorso = tmp_path / "orario.ics"
    resa = _esegui(schedule=env["schedule"].pk, out=str(percorso))
    assert "8 eventi" in resa
    # ⚠ `newline=""` in scrittura: senza, Python tradurrebbe i CRLF di RFC
    # 5545 in CRCRLF su Windows e in LF altrove. Si legge in binario perché
    # è l'unico modo di vedere davvero i terminatori.
    grezzo = percorso.read_bytes()
    assert grezzo.startswith(b"BEGIN:VCALENDAR\r\n")
    assert b"\n\n" not in grezzo and b"\r\r" not in grezzo
