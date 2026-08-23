"""ADR-017: parti di partizioni diverse condividono studenti e confliggono.
Parti della stessa partizione no — quello è lo sdoppiamento."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.state import AtomMap
from domain.models import ClassPart, ClassPartition, Group
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _partition(klass, name, *part_names):
    partition = ClassPartition.objects.create(school_class=klass, name=name)
    return [ClassPart.objects.create(name=n, partition=partition) for n in part_names]


def _codici(schedule):
    return [f.code for f in check_schedule(schedule)]


def test_parti_di_partizioni_diverse_confliggono():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    ing, ted = _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[ing])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" in _codici(env["schedule"])


def test_parti_della_stessa_partizione_non_confliggono():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[alt])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" not in _codici(env["schedule"])


def test_una_sola_partizione_non_genera_atomi():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    atoms = AtomMap.build()
    assert atoms.klass == {} and atoms.part == {}
    a = make_activity(env["subject"], parts=[rel])
    b = make_activity(env["subject"], parts=[alt])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" not in _codici(env["schedule"])


def test_conflitto_anche_per_la_via_del_raggruppamento():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    ing, ted = _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    g = Group.objects.create(name="ALTERNATIVA")
    g.parts.add(rel)
    a = make_activity(env["subject"], groups=[g])
    b = make_activity(env["subject"], parts=[ing])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" in _codici(env["schedule"])


def test_la_classe_intera_confligge_con_ogni_parte():
    env = mini_school()
    rel, alt = _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(env["subject"], parts=[alt])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)
    assert "resource_occupied" in _codici(env["schedule"])


def test_l_atomo_ha_un_nome_leggibile():
    env = mini_school()
    _partition(env["klass"], "IRC", "1A_REL", "1A_ALT")
    _partition(env["klass"], "LINGUA", "1A_ING", "1A_TED")
    atoms = AtomMap.build()
    assert len(atoms.klass[env["klass"].pk]) == 4          # prodotto 2 x 2
    assert set(atoms.names.values()) == {"1A (studenti in comune fra partizioni)"}
