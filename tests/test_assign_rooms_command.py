"""Il comando della ripartizione: dichiara, e non scrive senza --applica."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import Placement, ResourceUnavailability, Room
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _esegui(schedule, **kw):
    out = StringIO()
    call_command("assign_rooms", schedule=schedule.pk, stdout=out, **kw)
    return out.getvalue()


def test_senza_applica_non_scrive_niente():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    testo = _esegui(env["schedule"])
    assert Placement.objects.get(activity=a).assigned_room_id is None
    assert "--applica" in testo


def test_con_applica_scrive_l_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    _esegui(env["schedule"], applica=True)
    assert Placement.objects.get(activity=a).assigned_room_id == lab.pk


def test_il_rendiconto_nomina_i_livelli():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    testo = _esegui(env["schedule"])
    assert "minuti_senza_aula" in testo and "cambi_aula" in testo


def test_la_rinuncia_e_nominata_e_l_uscita_e_diversa_da_zero():
    """Un'assegnazione mancata deve dire **quale** laboratorio e' rimasto
    fuori e **dove**, o il comando non serve a chi lo lancia."""
    env = mini_school()
    lab = Room.objects.create(name="LAB-FIS")
    a = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("assign_rooms", schedule=env["schedule"].pk, stdout=out)
    testo = out.getvalue()
    assert "LAB-FIS" in testo and env["klass"].name in testo


def test_l_estrazione_riassegna_solo_le_estratte():
    """Il perimetro nella seconda fase: chi sta fuori tiene la sua aula e ne
    consuma la capienza, quindi la ripartizione è **incrementale** invece di
    rifare tutto — che è ciò che serve dopo aver spostato tre lezioni."""
    from domain.models import Extraction

    env = mini_school(days=1, slots=2)
    lab = Room.objects.create(name="LAB")
    altra = Room.objects.create(name="A1")
    fuori = make_activity(env["subject"], rooms=[lab, altra])
    dentro = make_activity(env["subject"], rooms=[lab, altra])
    place(env["schedule"], fuori, 0, 0, room=lab)
    place(env["schedule"], dentro, 0, 0)
    estrazione = Extraction.objects.create(name="solo-dentro")
    estrazione.activities.add(dentro)

    testo = _esegui(env["schedule"], estrazione="solo-dentro", applica=True,
                    lavoratori=1)

    assert "Richieste d'aula: 1" in testo
    assert Placement.objects.get(activity=fuori).assigned_room_id == lab.pk
    # L'unica aula libera in quella cella è l'altra: la capienza di LAB la
    # consuma chi sta fuori, senza essere una decisione.
    assert Placement.objects.get(activity=dentro).assigned_room_id == altra.pk
