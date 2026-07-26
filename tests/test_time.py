import datetime

import pytest

from domain import weeks
from domain.models import Break, Period, Schedule, SchoolYear, TimeGrid


@pytest.mark.django_db
def test_half_day_derives_from_morning_end_line():
    grid = TimeGrid.objects.create(days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4)
    assert grid.half_day(0) == "morning"
    assert grid.half_day(3) == "morning"
    assert grid.half_day(4) == "afternoon"


@pytest.mark.django_db
def test_break_is_a_separator_not_a_slot():
    grid = TimeGrid.objects.create(days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4)
    brk = Break.objects.create(grid=grid, boundary_slot=2)  # fra il rango 1 e il 2
    assert brk.straddles(start_slot=1, duration_slots=2) is True   # blocco 1-2 a cavallo
    assert brk.straddles(start_slot=2, duration_slots=2) is False  # blocco 2-3 dopo
    assert brk.straddles(start_slot=0, duration_slots=2) is False  # blocco 0-1 prima


def test_week_masks():
    assert weeks.full_mask(33) == (1 << 33) - 1
    assert weeks.single_week(0) == 1
    assert weeks.week_in_mask(weeks.single_week(12), 12) is True
    assert weeks.week_in_mask(weeks.single_week(12), 11) is False


@pytest.mark.django_db
def test_schedule_belongs_to_a_period():
    year = SchoolYear.objects.create(
        start_date=datetime.date(2026, 9, 14),
        end_date=datetime.date(2027, 6, 8),
        first_week_monday=datetime.date(2026, 9, 14),
    )
    q1 = Period.objects.create(
        school_year=year, name="Primo quadrimestre",
        start_date=datetime.date(2026, 9, 14), end_date=datetime.date(2027, 1, 31),
    )
    sched = Schedule.objects.create(period=q1, label="bozza 1")
    assert sched.period.school_year == year
