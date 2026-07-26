"""I tredici tipi di SubjectConstraint, uno scenario minimo ciascuno."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import ClassPart, ClassPartition, Subject, SubjectConstraint
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = SubjectConstraint.Type


def _row(env, type_, subject_b=None, param=None):
    return SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=subject_b or env["subject"], type=type_, param=param)


def _lesson(env, day, slot, subject=None, slots=1):
    a = make_activity(subject or env["subject"], classes=[env["klass"]], slots=slots)
    place(env["schedule"], a, day=day, slot=slot)
    return a


def _other_subject(env):
    return Subject.objects.create(code="MAT", name="Matematica",
                                  discipline=env["discipline"])


def _codes(env):
    return [f.code for f in check_schedule(env["schedule"])]


def test_same_half_day_incompatible():
    env = mini_school()
    _row(env, T.SAME_HALF_DAY_INCOMPATIBLE)
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=2)          # stessa mattina
    assert _codes(env) == ["subject_same_half_day"]


def test_same_day_incompatible():
    env = mini_school()
    _row(env, T.SAME_DAY_INCOMPATIBLE)
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=5)          # mattina + pomeriggio: stessa giornata
    assert _codes(env) == ["subject_same_day"]


def test_same_day_orientato_fra_due_materie():
    env = mini_school()
    mat = _other_subject(env)
    _row(env, T.SAME_DAY_INCOMPATIBLE, subject_b=mat)
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=1, subject=mat)
    assert _codes(env) == ["subject_same_day"]


def test_two_days_incompatible():
    env = mini_school()
    _row(env, T.TWO_DAYS_INCOMPATIBLE)
    _lesson(env, day=1, slot=0)
    _lesson(env, day=2, slot=0)          # giorni consecutivi
    assert _codes(env) == ["subject_two_days"]


def test_forbidden_sequence():
    env = mini_school()
    mat = _other_subject(env)
    _row(env, T.FORBIDDEN_SEQUENCE, subject_b=mat)
    _lesson(env, day=0, slot=0, slots=2)
    _lesson(env, day=0, slot=2, subject=mat)  # MAT subito dopo ITA
    assert _codes(env) == ["subject_forbidden_sequence"]


def test_max_hours_half_day():
    env = mini_school()
    _row(env, T.MAX_HOURS_HALF_DAY, param=60)
    _lesson(env, day=0, slot=0, slots=2)      # 120' > 60' nella mattinata
    assert _codes(env) == ["subject_max_hours_half_day"]


def test_max_hours_day():
    env = mini_school()
    _row(env, T.MAX_HOURS_DAY, param=120)
    _lesson(env, day=0, slot=0, slots=2)
    _lesson(env, day=0, slot=4)               # 180' > 120' nella giornata
    assert _codes(env) == ["subject_max_hours_day"]


def test_weekly_order():
    env = mini_school()
    mat = _other_subject(env)
    _row(env, T.WEEKLY_ORDER, subject_b=mat)  # ITA prima di MAT nella settimana
    _lesson(env, day=1, slot=0)
    _lesson(env, day=0, slot=0, subject=mat)  # MAT arriva prima: violazione
    assert _codes(env) == ["subject_weekly_order"]


def test_imposed_succession():
    env = mini_school()
    _row(env, T.IMPOSED_SUCCESSION, param=2)  # occorrenze a distanza max 2 mezze g.
    _lesson(env, day=0, slot=0)
    _lesson(env, day=2, slot=0)               # 4 mezze giornate dopo: violazione
    assert _codes(env) == ["subject_imposed_succession"]


def test_half_day_gap():
    env = mini_school()
    _row(env, T.HALF_DAY_GAP, param=3)        # scarto minimo 3 mezze giornate
    _lesson(env, day=0, slot=0)
    _lesson(env, day=0, slot=5)               # scarto 1: violazione
    assert _codes(env) == ["subject_half_day_gap"]


def _with_part(env):
    partition = ClassPartition.objects.create(school_class=env["klass"], name="SDOPP")
    return ClassPart.objects.create(name="1A-g1", partition=partition)


def _part_lesson(env, part, day, slot):
    a = make_activity(env["subject"], parts=[part])
    place(env["schedule"], a, day=day, slot=slot)
    return a


def test_parts_before_class():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_BEFORE_CLASS)
    _lesson(env, day=0, slot=1)               # classe intera alla fascia 1
    _part_lesson(env, part, day=0, slot=2)    # gruppo dopo: violazione
    assert _codes(env) == ["subject_parts_order"]


def test_parts_after_class():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_AFTER_CLASS)
    _part_lesson(env, part, day=0, slot=1)    # gruppo prima: violazione
    _lesson(env, day=0, slot=2)
    assert _codes(env) == ["subject_parts_order"]


def test_parts_no_interleaving_half_day():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_BEFORE_OR_AFTER_CLASS_H)
    _part_lesson(env, part, day=0, slot=0)
    _lesson(env, day=0, slot=1)               # classe in mezzo al gruppo
    _part_lesson(env, part, day=0, slot=2)    # interlacciato: violazione
    assert _codes(env) == ["subject_parts_order"]


def test_parts_no_interleaving_day_ok_se_compatti():
    env = mini_school()
    part = _with_part(env)
    _row(env, T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
    _lesson(env, day=0, slot=0)
    _part_lesson(env, part, day=0, slot=4)    # tutte le ore classe, poi il gruppo
    _part_lesson(env, part, day=0, slot=5)
    assert _codes(env) == []
