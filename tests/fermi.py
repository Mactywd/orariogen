"""Il dataset del Liceo Fermi (data/liceo-fermi/*.md) trascritto in letterali
Python. La trascrizione è essa stessa il test: se lo schema non riesce a
rappresentare una riga, il build fallisce."""

import datetime as dt

from domain import weeks
from domain.models import (
    Activity, CompetitionClass, Discipline, InstituteSettings, Period,
    ResourceUnavailability, Room, Schedule, SchoolClass, SchoolYear, Service,
    SlotLabel, StudyPlan, Subject, Teacher, TeachingAssignment, TimeGrid,
)

WEEKS_IN_YEAR = 33  # periodicità S (33/33) osservata in EDT

# Le etichette orarie delle sei fasce. ⚠ Come le aule e come `SPECIAL_ROOMS`,
# è **nostra scelta di dimensionamento**, mai osservata: `tempo-e-calendario.md`
# dichiara che la configurazione oraria di EDT non è mai stata vista in UI, e
# la base del Fermi non ha un orologio. La pausa fra le 12 e le 14 non è
# decorativa — è la discontinuità che fa esistere il caso del blocco spezzato,
# e senza di essa il dataset misurerebbe un export senza gradi di libertà.
SLOT_LABELS = [
    (0, dt.time(8, 0), dt.time(9, 0)),
    (1, dt.time(9, 0), dt.time(10, 0)),
    (2, dt.time(10, 0), dt.time(11, 0)),
    (3, dt.time(11, 0), dt.time(12, 0)),
    (4, dt.time(14, 0), dt.time(15, 0)),
    (5, dt.time(15, 0), dt.time(16, 0)),
]

# Spezzoni (vincoli-attesi.md): D06, D09, D15 indisponibili a giornata intera
# nei giorni elencati. Il dataset dichiara il bisogno, non i giorni: questa è
# la nostra istanza concreta, dimensionata per restare risolvibile.
UNAVAILABLE_DAYS = {"D06": [2, 4], "D09": [0, 1, 3], "D15": [0, 4]}

DISCIPLINES = {  # codice: (nome, [classi di concorso])
    "LET": ("Lettere", ["A011", "A013"]),
    "STF": ("Storia e Filosofia", ["A019"]),
    "LIN": ("Lingue straniere", ["AB24"]),
    "MAF": ("Matematica e Fisica", ["A027"]),
    "SCN": ("Scienze", ["A050"]),
    "ART": ("Discipline artistiche", ["A017"]),
    "MOT": ("Scienze motorie", ["A048"]),
    "REL": ("Religione", ["IRC"]),
}

SUBJECTS = {  # codice: (nome, disciplina)
    "ITA": ("Italiano", "LET"), "LAT": ("Latino", "LET"),
    "STG": ("Storia e Geografia", "LET"),
    "STO": ("Storia", "STF"), "FIL": ("Filosofia", "STF"),
    "ING": ("Inglese", "LIN"),
    "MAT": ("Matematica", "MAF"), "FIS": ("Fisica", "MAF"),
    "SCI": ("Scienze naturali", "SCN"), "DIS": ("Disegno e Storia dell'Arte", "ART"),
    "MOT": ("Scienze motorie", "MOT"), "IRC": ("Religione cattolica", "REL"),
}

CURRICULUM = {  # materia: (ore biennio, ore triennio); None = non presente
    "ITA": (4, 4), "LAT": (3, 3), "ING": (3, 3), "STG": (3, None),
    "STO": (None, 2), "FIL": (None, 3), "MAT": (5, 4), "FIS": (2, 3),
    "SCI": (2, 3), "DIS": (2, 2), "MOT": (2, 2), "IRC": (1, 1),
}

CLASSES = [f"{y}{s}" for s in "AB" for y in range(1, 6)]  # 1A..5A, 1B..5B

ROOMS = (
    [(f"A10{i}", 30, 1) for i in range(1, 6)]
    + [(f"B10{i}", 30, 1) for i in range(1, 6)]
    + [("LAB-FIS", 30, 1), ("LAB-SCI", 30, 1), ("LAB-INF", 25, 1),
       ("AUL-DIS", 30, 1), ("PALESTRA", 60, 2), ("AULA-MAGNA", 100, 1)]
)

SPECIAL_ROOMS = {  # materia → aule candidate, per le materie che ne chiedono una
    # ⚠ Le candidate sono **due** dove la materia ne ha davvero due, ed e'
    # deliberato: a candidata unica l'occupazione se la prende gia' il
    # piazzamento (`domain/analysis/state.py`, `_activity_tokens`), quindi la
    # seconda fase non deciderebbe niente. `LAB-INF` e' il laboratorio
    # condiviso — acquisizione dati per FIS e SCI, CAD per DIS — ed e' l'unica
    # riga del dataset che mette in concorrenza materie e docenti diversi.
    "FIS": ("LAB-FIS", "LAB-INF"),
    "SCI": ("LAB-SCI", "LAB-INF"),
    "DIS": ("AUL-DIS", "LAB-INF"),
    "MOT": ("PALESTRA",),
}

ALL = CLASSES
TEACHERS = [  # (id, nome, abbr, [(materia, [classi])], ore Mh/s, materia preferenziale)
    ("D01", "Rossi Anna", "ROSSI", [("ITA", ["1A", "2A", "3A"]), ("LAT", ["1A", "2A", "3A"])], 21, "ITA"),
    ("D02", "Bianchi Marco", "BIANC", [("ITA", ["4A", "5A"]), ("LAT", ["4A", "5A"])], 14, "ITA"),
    ("D03", "Verdi Chiara", "VERDI", [("ITA", ["1B", "2B", "3B"]), ("LAT", ["1B", "2B", "3B"])], 21, "ITA"),
    ("D04", "Neri Paolo", "NERI", [("ITA", ["4B", "5B"]), ("LAT", ["4B", "5B"])], 14, "ITA"),
    ("D05", "Ferrari Giulia", "FERRA", [("ING", ["1A", "2A", "3A", "4A", "5A", "1B"])], 18, "ING"),
    ("D06", "Russo Elena", "RUSSO", [("ING", ["2B", "3B", "4B", "5B"])], 12, "ING"),
    ("D07", "Conti Luca", "CONTI", [("FIL", ["3A", "4A", "5A"]), ("STO", ["3A", "4A", "5A"]), ("STG", ["1A"])], 18, "FIL"),
    ("D08", "Marino Sara", "MARIN", [("FIL", ["3B", "4B", "5B"]), ("STO", ["3B", "4B", "5B"]), ("STG", ["1B"])], 18, "FIL"),
    ("D09", "Greco Ilaria", "GRECO", [("STG", ["2A", "2B"])], 6, "STG"),
    ("D10", "Costa Davide", "COSTA", [("MAT", ["1A", "2A", "3A"]), ("FIS", ["1A", "2A", "3A"])], 21, "MAT"),
    ("D11", "Gallo Francesca", "GALLO", [("MAT", ["4A", "5A"]), ("FIS", ["4A", "5A"])], 14, "MAT"),
    ("D12", "Lombardi Andrea", "LOMBA", [("MAT", ["1B", "2B", "3B"]), ("FIS", ["1B", "2B", "3B"])], 21, "MAT"),
    ("D13", "Fontana Silvia", "FONTA", [("MAT", ["4B", "5B"]), ("FIS", ["4B", "5B"])], 14, "MAT"),
    ("D14", "Ricci Matteo", "RICCI", [("SCI", ["1A", "2A", "3A", "4A", "5A", "1B", "2B"])], 17, "SCI"),
    ("D15", "Esposito Laura", "ESPOS", [("SCI", ["3B", "4B", "5B"])], 9, "SCI"),
    ("D16", "Barbieri Giorgio", "BARB", [("DIS", ALL)], 20, "DIS"),
    ("D17", "Villa Roberto", "VILLA", [("MOT", ALL)], 20, "MOT"),
    ("D18", "Piani Stefano", "PIANI", [("IRC", ALL)], 10, "IRC"),
]


def _year(class_name):
    return int(class_name[0])


def _hours(subject_code, class_name):
    biennio, triennio = CURRICULUM[subject_code]
    return biennio if _year(class_name) <= 2 else triennio


def _blocks(subject_code, class_name):
    hours = _hours(subject_code, class_name)
    if subject_code == "MAT" and _year(class_name) <= 2:
        return [2, 1, 1, 1]  # i quattro blocchi da 2h di attivita.md
    return [1] * hours


def build():
    settings = InstituteSettings.load()
    settings.default_max_reduced_students = 15
    settings.save()

    grid = TimeGrid.objects.create(
        days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4
    )
    for slot, inizio, fine in SLOT_LABELS:
        SlotLabel.objects.create(grid=grid, slot=slot,
                                 start_time=inizio, end_time=fine)

    disciplines, subjects = {}, {}
    for code, (name, ccs) in DISCIPLINES.items():
        d = Discipline.objects.create(code=code, name=name)
        for cc in ccs:
            obj, _ = CompetitionClass.objects.get_or_create(code=cc)
            d.competition_classes.add(obj)
        disciplines[code] = d
    for code, (name, disc) in SUBJECTS.items():
        subjects[code] = Subject.objects.create(code=code, name=name, discipline=disciplines[disc])

    plans = {}
    for year in range(1, 6):
        plan = StudyPlan.objects.create(
            code=f"SCI{year}", name=f"Liceo Scientifico - {year} anno", year=year
        )
        col = 0 if year <= 2 else 1
        for subject_code, hours_pair in CURRICULUM.items():
            hours = hours_pair[col]
            if hours is not None:
                Service.objects.create(
                    study_plan=plan, subject=subjects[subject_code], class_minutes=hours * 60
                )
        plans[plan.code] = plan

    rooms = {
        name: Room.objects.create(name=name, capacity=cap, simultaneous_capacity=simult)
        for name, cap, simult in ROOMS
    }

    classes = {}
    for name in CLASSES:
        classes[name] = SchoolClass.objects.create(
            name=name, study_plan=plans[f"SCI{_year(name)}"], year=_year(name),
            preferred_room=rooms[f"{name[1]}10{name[0]}"],  # 1A→A101 … 5B→B105
        )

    teachers = {}
    year_mask = weeks.full_mask(WEEKS_IN_YEAR)
    for tid, full_name, abbr, assignments, hours, preferred in TEACHERS:
        last, first = full_name.split(" ", 1)
        t = Teacher.objects.create(
            name=full_name, last_name=last, first_name=first, abbreviation=abbr,
            weekly_minutes=hours * 60, preferred_subject=subjects[preferred],
        )
        for subject_code, class_names in assignments:
            t.teachable_subjects.add(subjects[subject_code])
            for class_name in class_names:
                TeachingAssignment.objects.create(
                    teacher=t, subject=subjects[subject_code],
                    school_class=classes[class_name],
                    weekly_minutes=_hours(subject_code, class_name) * 60,
                )
                for block in _blocks(subject_code, class_name):
                    activity = Activity.objects.create(
                        subject=subjects[subject_code],
                        duration_slots=block, duration_minutes=block * 60,
                        week_mask=year_mask,
                    )
                    activity.teachers.add(t)
                    activity.classes.add(classes[class_name])
                    for room_name in SPECIAL_ROOMS.get(subject_code, ()):
                        activity.rooms.add(rooms[room_name])
        teachers[tid] = t

    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14),
        end_date=dt.date(2026, 9, 14) + dt.timedelta(weeks=WEEKS_IN_YEAR) - dt.timedelta(days=1),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(school_year=year, name="Annuale",
                                   start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    for teacher_id, days in UNAVAILABLE_DAYS.items():
        for day in days:
            for slot in range(6):
                ResourceUnavailability.objects.create(
                    resource=teachers[teacher_id], day=day, slot=slot, level="hard")

    return {
        "grid": grid, "plans": plans, "classes": classes,
        "teachers": teachers, "subjects": subjects,
        "year": year, "period": period, "schedule": schedule,
    }
