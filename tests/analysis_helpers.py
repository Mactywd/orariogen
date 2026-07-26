"""Fixture minima per i test dell'analisi: una scuola giocattolo con griglia
5×6, anno di 4 settimane, una classe, un docente, una materia."""
import datetime as dt

from domain import weeks
from domain.models import (
    Activity, Discipline, Period, Placement, Schedule, SchoolClass, SchoolYear,
    StudyPlan, Subject, Teacher, TimeGrid,
)

N_WEEKS = 4
FULL = weeks.full_mask(N_WEEKS)


def mini_school():
    grid = TimeGrid.objects.create(
        days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4
    )
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 10, 11),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1",
        start_date=year.start_date, end_date=year.end_date,
    )
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    teacher = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")
    return {
        "grid": grid, "year": year, "period": period, "schedule": schedule,
        "discipline": disc, "subject": subject, "plan": plan,
        "klass": klass, "teacher": teacher,
    }


def make_activity(subject, *, teachers=(), classes=(), parts=(), groups=(),
                  rooms=(), slots=1, mask=FULL, **flags):
    a = Activity.objects.create(
        subject=subject, duration_slots=slots, duration_minutes=slots * 60,
        week_mask=mask, **flags,
    )
    for t in teachers:
        a.teachers.add(t)
    for c in classes:
        a.classes.add(c)
    for p in parts:
        a.parts.add(p)
    for g in groups:
        a.groups.add(g)
    for r in rooms:
        a.rooms.add(r)
    return a


def place(schedule, activity, day, slot, room=None):
    return Placement.objects.create(
        schedule=schedule, activity=activity, day=day, start_slot=slot,
        assigned_room=room,
    )
