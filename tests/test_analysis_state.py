"""ScheduleState: la regola dei conflitti sulle unità e la meccanica del
piazzamento di prova."""
import datetime as dt

import pytest

from domain.analysis.state import ScheduleState, activity_tokens
from domain.models import ClassPart, ClassPartition, Group, ResourceUnavailability
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _with_parts(env):
    partition = ClassPartition.objects.create(school_class=env["klass"], name="LINGUE")
    p1 = ClassPart.objects.create(name="1A-fra", partition=partition)
    p2 = ClassPart.objects.create(name="1A-spa", partition=partition)
    return p1, p2


def test_classe_intera_occupa_se_stessa_e_le_parti():
    env = mini_school()
    p1, p2 = _with_parts(env)
    a = make_activity(env["subject"], classes=[env["klass"]])
    keys, _ = activity_tokens(a)
    assert keys == {env["klass"].pk, p1.pk, p2.pk}


def test_la_parte_occupa_solo_se_stessa():
    env = mini_school()
    p1, p2 = _with_parts(env)
    a = make_activity(env["subject"], parts=[p1])
    keys, _ = activity_tokens(a)
    assert keys == {p1.pk}


def test_il_raggruppamento_occupa_le_parti_membre():
    env = mini_school()
    p1, p2 = _with_parts(env)
    g = Group.objects.create(name="G-LINGUE")
    g.parts.add(p1, p2)
    a = make_activity(env["subject"], groups=[g])
    keys, _ = activity_tokens(a)
    assert keys == {p1.pk, p2.pk}


def test_build_indicizza_i_piazzamenti():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    place(env["schedule"], a, day=1, slot=2)
    state = ScheduleState.build(env["schedule"])
    assert state.placed[a.id].slots == (2,)
    assert state.occupancy[(env["teacher"].pk, 1, 2)] == [a.id]
    assert state.resource_days(env["klass"].pk) == {1: [2]}


def test_place_unplace_e_reversibile():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    state = ScheduleState.build(env["schedule"])
    state.place(a, day=0, start_slot=3)
    assert state.occupancy[(env["klass"].pk, 0, 4)] == [a.id]
    state.unplace(a.id)
    assert (env["klass"].pk, 0, 4) not in state.occupancy
    assert a.id not in state.placed


def test_attivita_fuori_settimana_esclusa():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], mask=0b0010)
    place(env["schedule"], a, day=0, slot=0)
    assert a.id not in ScheduleState.build(env["schedule"], week=0).activities
    assert a.id in ScheduleState.build(env["schedule"], week=1).activities


def test_indisponibilita_con_data_mappa_sulla_settimana():
    env = mini_school()
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=2, slot=0, level="hard",
        date=dt.date(2026, 9, 23),  # mercoledì della settimana 1
    )
    assert (env["teacher"].pk, 2, 0) not in ScheduleState.build(env["schedule"], week=0).unavailability
    state = ScheduleState.build(env["schedule"], week=1)
    assert state.unavailability[(env["teacher"].pk, 2, 0)] == "hard"


def test_livello_piu_severo_vince():
    env = mini_school()
    ResourceUnavailability.objects.create(resource=env["teacher"], day=0, slot=0, level="preference")
    ResourceUnavailability.objects.create(resource=env["teacher"], day=0, slot=0, level="hard")
    state = ScheduleState.build(env["schedule"])
    assert state.unavailability[(env["teacher"].pk, 0, 0)] == "hard"
