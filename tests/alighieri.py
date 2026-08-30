"""Il dataset del Liceo "Dante Alighieri" (data/liceo-alighieri/*.md)
trascritto in letterali Python.

⚠ **Non è un Fermi più grande, ed è di natura diversa.** Il Fermi è la
trascrizione di una scuola realmente inserita in EDT durante il reverse
engineering: le sue righe sono osservazioni, e per questo non si toccano mai
per far passare un test. L'Alighieri è un **banco**: le sue righe sono
costruzioni nostre, scelte per far scattare un checker, e si modificano quando
una famiglia nuova entra nel registro. Le due domande sono diverse — «lo schema
regge una scuola vera?» contro «il motore regge tutte le famiglie insieme, a
scala vera?» — e vogliono due dataset.

Vedi `data/liceo-alighieri/README.md` e la spec
`docs/superpowers/specs/2026-08-30-alighieri-banco-a-scuola-intera-design.md`.

**Ondata 1 — l'anagrafica.** Sedi, indirizzi, materie, piani di studi e
servizi, classi, docenti, aule, attività. Niente vincoli: arrivano dalle
ondate 3 in poi, e ognuna aggiunge righe a `esiti-attesi.md` prima del codice
che le esercita."""

import datetime as dt

from domain import weeks
from domain.models import (
    Activity, Break, CompetitionClass, Discipline, InstituteSettings, Period,
    Room, Schedule, SchoolClass, SchoolYear, Service, Site, SlotLabel,
    StudyPlan, Subject, Teacher, TeachingAssignment, TimeGrid,
)

WEEKS_IN_YEAR = 33  # come il Fermi: periodicità S (33/33) osservata in EDT

# La griglia: 5 × 8, mattina di cinque fasce e pomeriggio di tre, con la pausa
# mensa fra le 13 e le 14. 🔑 Le otto fasce non sono decorazione — `max_hours`
# con tetto mattutino diverso da quello giornaliero e `max_half_days` non hanno
# soggetto su una griglia senza pomeriggio, e il Fermi non ce l'ha.
SLOT_LABELS = [
    (0, dt.time(8, 0), dt.time(9, 0)),
    (1, dt.time(9, 0), dt.time(10, 0)),
    (2, dt.time(10, 0), dt.time(11, 0)),
    (3, dt.time(11, 0), dt.time(12, 0)),
    (4, dt.time(12, 0), dt.time(13, 0)),
    (5, dt.time(14, 0), dt.time(15, 0)),
    (6, dt.time(15, 0), dt.time(16, 0)),
    (7, dt.time(16, 0), dt.time(17, 0)),
]
MORNING_END_SLOT = 5          # prima fascia del pomeriggio
LUNCH_BOUNDARY = 5            # l'intervallo mensa, come `Break`

SITES = ["Centrale", "Succursale"]

DISCIPLINES = {  # codice: (nome, [classi di concorso])
    "LET": ("Lettere", ["A011", "A013"]),
    "STF": ("Storia e Filosofia", ["A019"]),
    "LIN": ("Lingue straniere", ["AB24"]),
    "MAF": ("Matematica e Fisica", ["A026", "A027"]),
    "SCN": ("Scienze", ["A050"]),
    "ART": ("Discipline artistiche", ["A017", "A054"]),
    "MOT": ("Scienze motorie", ["A048"]),
    "REL": ("Religione", ["IRC"]),
}

SUBJECTS = {  # codice: (nome, disciplina)
    "ITA": ("Italiano", "LET"), "LAT": ("Latino", "LET"),
    "GRE": ("Greco", "LET"), "STG": ("Storia e Geografia", "LET"),
    "STO": ("Storia", "STF"), "FIL": ("Filosofia", "STF"),
    "ING": ("Inglese", "LIN"),
    "MAT": ("Matematica", "MAF"), "FIS": ("Fisica", "MAF"),
    "SCI": ("Scienze naturali", "SCN"),
    "DIS": ("Disegno e Storia dell'Arte", "ART"),
    "STA": ("Storia dell'Arte", "ART"),
    "MOT": ("Scienze motorie", "MOT"), "IRC": ("Religione cattolica", "REL"),
}

# I quadri orari dei due indirizzi, per fascia d'anno. La somma di ogni riga è
# il monte ore settimanale della classe: 27 nei due bienni, 30 allo scientifico
# e 31 al classico nei trienni.
CURRICULUM = {
    ("SCI", "biennio"): {"ITA": 4, "LAT": 3, "ING": 3, "STG": 3, "MAT": 5,
                         "FIS": 2, "SCI": 2, "DIS": 2, "MOT": 2, "IRC": 1},
    ("SCI", "triennio"): {"ITA": 4, "LAT": 3, "ING": 3, "STO": 2, "FIL": 3,
                          "MAT": 4, "FIS": 3, "SCI": 3, "DIS": 2, "MOT": 2,
                          "IRC": 1},
    ("CLA", "biennio"): {"ITA": 4, "LAT": 5, "GRE": 4, "ING": 3, "STG": 3,
                         "MAT": 3, "SCI": 2, "MOT": 2, "IRC": 1},
    ("CLA", "triennio"): {"ITA": 4, "LAT": 4, "GRE": 3, "ING": 3, "STO": 3,
                          "FIL": 3, "MAT": 2, "FIS": 2, "SCI": 2, "STA": 2,
                          "MOT": 2, "IRC": 1},
}

# classe: (indirizzo, anno, sede, alunni previsti). Tre sezioni, due indirizzi:
# A scientifico e B classico a corso intero, C un secondo biennio scientifico
# in succursale. 🔑 La C esiste per due ragioni che arrivano dopo: è la sede
# che rende esistenti i cambi di sede (§3.4 della spec), ed è la sezione
# gemella della A nel biennio, cioè il posto naturale del raggruppamento
# trasversale che attraversa due classi (ondata 2).
CLASSES = (
    [(f"{y}A", "SCI", y, "Centrale", 26) for y in range(1, 6)]
    + [(f"{y}B", "CLA", y, "Centrale", 22) for y in range(1, 6)]
    + [(f"{y}C", "SCI", y, "Succursale", 24) for y in range(1, 3)]
)

ROOMS = [  # nome, sede, capienza, aule simultanee
    ("A101", "Centrale", 28, 1), ("A102", "Centrale", 28, 1),
    ("A103", "Centrale", 28, 1), ("A104", "Centrale", 28, 1),
    ("A105", "Centrale", 28, 1),
    ("B101", "Centrale", 24, 1), ("B102", "Centrale", 24, 1),
    ("B103", "Centrale", 24, 1), ("B104", "Centrale", 24, 1),
    ("B105", "Centrale", 24, 1),
    ("LAB-FIS", "Centrale", 30, 1), ("LAB-SCI", "Centrale", 30, 1),
    ("LAB-INF", "Centrale", 25, 1), ("AUL-DIS", "Centrale", 30, 1),
    ("PALESTRA", "Centrale", 60, 2), ("AULA-MAGNA", "Centrale", 100, 1),
    ("C101", "Succursale", 26, 1), ("C102", "Succursale", 26, 1),
    ("LAB-SUCC", "Succursale", 28, 1), ("PAL-SUCC", "Succursale", 50, 1),
]

HOME_ROOM = {  # classe → aula preferenziale
    **{f"{y}A": f"A10{y}" for y in range(1, 6)},
    **{f"{y}B": f"B10{y}" for y in range(1, 6)},
    "1C": "C101", "2C": "C102",
}

# materia → aule candidate, **per sede**: la succursale ha un laboratorio solo
# e una palestra sola, la centrale ne ha di specializzati. ⚠ Alla centrale le
# candidate sono due dove la materia ne ha davvero due — a candidata unica il
# piazzamento si prende già l'occupazione e la seconda fase non decide niente
# (la stessa nota di `tests/fermi.py`).
SPECIAL_ROOMS = {
    "Centrale": {"FIS": ("LAB-FIS", "LAB-INF"), "SCI": ("LAB-SCI", "LAB-INF"),
                 "DIS": ("AUL-DIS", "LAB-INF"), "MOT": ("PALESTRA",)},
    "Succursale": {"FIS": ("LAB-SUCC",), "SCI": ("LAB-SUCC",),
                   "MOT": ("PAL-SUCC",)},
}

# Lo spezzamento in blocchi, per (materia, ore). Ciò che non compare qui è
# un'ora singola per ogni ora del quadro orario.
BLOCKS = {
    ("MAT", 5): [2, 1, 1, 1],   # i quattro blocchi del biennio, come al Fermi
    ("FIS", 3): [2, 1],         # l'ora doppia di laboratorio
    ("SCI", 3): [2, 1],
    ("MOT", 2): [2],            # la palestra si prende due ore di fila
}

TEACHERS = [  # id, nome, abbr., [(materia, [classi])], Mh/s, materia preferita
    ("L01", "Amato Cristina", "AMATO",
     [("ITA", ["1A", "2A"]), ("LAT", ["1A", "2A"]), ("STG", ["1A", "2A"])], 20, "ITA"),
    ("L02", "Beltrami Nicola", "BELTR",
     [("ITA", ["1C", "2C"]), ("LAT", ["1C", "2C"]), ("STG", ["1C", "2C"])], 20, "ITA"),
    ("L03", "Cavalli Marta", "CAVAL",
     [("ITA", ["3A", "4A", "5A"]), ("LAT", ["3A", "4A", "5A"])], 21, "ITA"),
    ("L04", "De Santis Ilaria", "DESAN",
     [("ITA", ["1B", "2B"]), ("STG", ["1B", "2B"])], 14, "ITA"),
    ("L05", "Ferretti Ugo", "FERRE",
     [("LAT", ["1B", "2B"]), ("GRE", ["1B", "2B"])], 18, "GRE"),
    # 🔑 L06 è il **tempo parziale** del dataset: dodici ore. Esiste perché
    # `max_presence` («lavora al più N giorni») non ha soggetto su un collegio
    # di sole cattedre piene — con 21 ore un docente sta a scuola comunque.
    ("L06", "Gentili Marco", "GENTI", [("ITA", ["3B", "4B", "5B"])], 12, "ITA"),
    ("L07", "Iacopini Rosa", "IACOP",
     [("LAT", ["3B", "4B", "5B"]), ("GRE", ["3B", "4B", "5B"])], 21, "GRE"),
    ("S01", "Lanzi Federico", "LANZI",
     [("FIL", ["3A", "4A", "5A"]), ("STO", ["3A", "4A", "5A"])], 15, "FIL"),
    ("S02", "Manzoni Eleonora", "MANZO",
     [("FIL", ["3B", "4B", "5B"]), ("STO", ["3B", "4B", "5B"])], 18, "FIL"),
    ("E01", "Novelli Serena", "NOVEL",
     [("ING", ["1A", "2A", "3A", "4A", "5A", "1C"])], 18, "ING"),
    ("E02", "Orlandi Piero", "ORLAN",
     [("ING", ["2C", "1B", "2B", "3B", "4B", "5B"])], 18, "ING"),
    ("M01", "Pagani Diego", "PAGAN",
     [("MAT", ["1A", "2A"]), ("FIS", ["1A", "2A"])], 14, "MAT"),
    ("M02", "Quaranta Livia", "QUARA",
     [("MAT", ["1C", "2C"]), ("FIS", ["1C", "2C"])], 14, "MAT"),
    ("M03", "Rinaldi Tommaso", "RINAL",
     [("MAT", ["3A", "4A", "5A"]), ("FIS", ["3A", "4A", "5A"])], 21, "MAT"),
    ("M04", "Sartori Gaia", "SARTO",
     [("MAT", ["1B", "2B", "3B", "4B", "5B"]), ("FIS", ["3B", "4B", "5B"])], 18, "MAT"),
    ("N01", "Tosi Alberto", "TOSI",
     [("SCI", ["1A", "2A", "1C", "2C", "3A", "4A", "5A"])], 17, "SCI"),
    ("N02", "Urbani Chiara", "URBAN",
     [("SCI", ["1B", "2B", "3B", "4B", "5B"])], 10, "SCI"),
    ("A01", "Vitali Renzo", "VITAL",
     [("DIS", ["1A", "2A", "3A", "4A", "5A", "1C", "2C"]),
      ("STA", ["3B", "4B", "5B"])], 20, "DIS"),
    ("P01", "Zanetti Luca", "ZANET",
     [("MOT", ["1A", "2A", "3A", "4A", "5A", "1C"])], 12, "MOT"),
    ("P02", "Bruni Sofia", "BRUNI",
     [("MOT", ["2C", "1B", "2B", "3B", "4B", "5B"])], 12, "MOT"),
    # 🔑 R01 insegna in **tutte e dodici** le classi, quindi in entrambe le
    # sedi: è il portatore naturale di `max_site_changes` (ondata 5), ed è già
    # da qui ciò che rende `structural:site_transition` non muto.
    ("R01", "Colombo Padre Egidio", "COLOM", [("IRC", None)], 12, "IRC"),
]


def _band(year):
    return "biennio" if year <= 2 else "triennio"


def _hours(track, year, subject_code):
    return CURRICULUM[(track, _band(year))].get(subject_code)


def build():
    settings = InstituteSettings.load()
    settings.default_max_reduced_students = 15
    settings.site_transition_slots = 1
    settings.save()

    sites = {name: Site.objects.create(name=name) for name in SITES}

    grid = TimeGrid.objects.create(
        days_per_cycle=5, slots_per_day=8, slot_minutes=60,
        morning_end_slot=MORNING_END_SLOT,
    )
    for slot, inizio, fine in SLOT_LABELS:
        SlotLabel.objects.create(grid=grid, slot=slot,
                                 start_time=inizio, end_time=fine)
    Break.objects.create(grid=grid, boundary_slot=LUNCH_BOUNDARY)

    disciplines, subjects = {}, {}
    for code, (name, ccs) in DISCIPLINES.items():
        d = Discipline.objects.create(code=code, name=name)
        for cc in ccs:
            obj, _ = CompetitionClass.objects.get_or_create(code=cc)
            d.competition_classes.add(obj)
        disciplines[code] = d
    for code, (name, disc) in SUBJECTS.items():
        subjects[code] = Subject.objects.create(
            code=code, name=name, discipline=disciplines[disc])

    plans = {}
    for track, label in (("SCI", "Liceo Scientifico"), ("CLA", "Liceo Classico")):
        for year in range(1, 6):
            plan = StudyPlan.objects.create(
                code=f"{track}{year}", name=f"{label} - {year} anno", year=year)
            for subject_code, hours in CURRICULUM[(track, _band(year))].items():
                Service.objects.create(study_plan=plan,
                                       subject=subjects[subject_code],
                                       class_minutes=hours * 60)
            plans[plan.code] = plan

    rooms = {
        name: Room.objects.create(name=name, site=sites[site], capacity=cap,
                                  simultaneous_capacity=simult)
        for name, site, cap, simult in ROOMS
    }

    classes, tracks, class_sites = {}, {}, {}
    for name, track, year, site, students in CLASSES:
        classes[name] = SchoolClass.objects.create(
            name=name, study_plan=plans[f"{track}{year}"], year=year,
            site=sites[site], preferred_room=rooms[HOME_ROOM[name]],
            expected_students=students,
        )
        tracks[name], class_sites[name] = track, site

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
            for class_name in (class_names if class_names is not None
                               else [c[0] for c in CLASSES]):
                year = classes[class_name].year
                ore = _hours(tracks[class_name], year, subject_code)
                TeachingAssignment.objects.create(
                    teacher=t, subject=subjects[subject_code],
                    school_class=classes[class_name], weekly_minutes=ore * 60,
                )
                site = class_sites[class_name]
                for block in BLOCKS.get((subject_code, ore), [1] * ore):
                    activity = Activity.objects.create(
                        subject=subjects[subject_code],
                        duration_slots=block, duration_minutes=block * 60,
                        week_mask=year_mask, site=sites[site],
                        # ⚠ Solo i blocchi lunghi: un'ora singola non può
                        # attraversare niente, e dichiararlo su tutte
                        # renderebbe la casella indistinguibile dal default.
                        respects_breaks=block > 1,
                    )
                    activity.teachers.add(t)
                    activity.classes.add(classes[class_name])
                    for room_name in SPECIAL_ROOMS[site].get(subject_code, ()):
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

    return {
        "grid": grid, "sites": sites, "plans": plans, "classes": classes,
        "teachers": teachers, "subjects": subjects, "rooms": rooms,
        "year": year, "period": period, "schedule": schedule,
    }
