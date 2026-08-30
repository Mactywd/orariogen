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
servizi, classi, docenti, aule, attività.

**Ondata 2 — gli sdoppiamenti.** Partizioni, parti, raggruppamenti trasversali:
la voce ✅ di scope v1 ([ADR-013](../docs/decisioni.md)) che nessun dataset
rappresentava. Quattro forme, tutte diverse fra loro — vedi `EROGAZIONI` e
`data/liceo-alighieri/gruppi.md`.

Niente vincoli ancora: arrivano dalle ondate 3 in poi, e ognuna aggiunge righe
a `esiti-attesi.md` prima del codice che le esercita."""

import datetime as dt

from domain import weeks
from domain.models import (
    Activity, Break, ClassPart, ClassPartition, CompetitionClass, Discipline,
    Group, InstituteSettings, Period, Room, Schedule, SchoolClass, SchoolYear,
    Service, Site, SlotLabel, StudyPlan, Subject, Teacher, TeachingAssignment,
    TimeGrid,
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
    "INF": ("Informatica", ["A041"]),
    # ⚠ Senza classi di concorso, e non è una dimenticanza: l'attività
    # alternativa all'IRC non ha una classe di concorso propria — la copre chi
    # ha ore a disposizione. È anche l'unico caso in cui la M2M resta vuota.
    "ALV": ("Attività alternativa", []),
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
    "INF": ("Informatica", "INF"),
    "ALT": ("Attività alternativa", "ALV"),
}

#: 🔑 Le due righe in **alternativa** (ADR-020): un alunno ne segue esattamente
#: una. Senza questa dichiarazione la copertura darebbe due scostamenti su ogni
#: classe italiana, ed è il comportamento giusto — non è deducibile da nessuna
#: proprietà dell'orario.
ELECTION_GROUP = {"IRC": "RELIGIONE", "ALT": "RELIGIONE"}

# I quadri orari dei due indirizzi, per fascia d'anno.
#
# ⚠ **La somma di una riga non è il monte ore di un alunno**, ed è la lezione di
# ADR-020: il piano è un **catalogo**, non un curriculum. Con IRC e ALT dentro,
# ogni riga somma un'ora in più di quelle che un alunno fa — perché di quelle
# due ne fa **una**. Le ore per alunno restano 27 nei due bienni, 30 allo
# scientifico e 31 al classico nei trienni.
CURRICULUM = {
    ("SCI", "biennio"): {"ITA": 4, "LAT": 3, "ING": 3, "STG": 3, "MAT": 5,
                         "FIS": 2, "SCI": 2, "DIS": 2, "MOT": 2, "IRC": 1, "ALT": 1},
    ("SCI", "triennio"): {"ITA": 4, "LAT": 3, "ING": 3, "STO": 2, "FIL": 3,
                          "MAT": 4, "FIS": 3, "SCI": 3, "DIS": 2, "MOT": 2,
                          "IRC": 1, "ALT": 1},
    ("CLA", "biennio"): {"ITA": 4, "LAT": 5, "GRE": 4, "ING": 3, "STG": 3,
                         "MAT": 3, "SCI": 2, "MOT": 2, "IRC": 1, "ALT": 1},
    ("CLA", "triennio"): {"ITA": 4, "LAT": 4, "GRE": 3, "ING": 3, "STO": 3,
                          "FIL": 3, "MAT": 2, "FIS": 2, "SCI": 2, "STA": 2,
                          "MOT": 2, "IRC": 1, "ALT": 1},
}

# classe: (indirizzo, anno, sede, alunni previsti). Tre sezioni, due indirizzi:
# A scientifico e B classico a corso intero, C un secondo biennio scientifico
# in succursale. 🔑 La C esiste per la **sede**: senza una sezione staccata non
# ci sono due sedi, e senza due sedi `structural:site_transition` resta muto
# come sul Fermi. ⚠ Il raggruppamento trasversale sta invece su 1A e 1B, alla
# centrale: fra due sedi chiederebbe agli stessi alunni di essere in due
# edifici alla stessa ora.
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
                   "INF": ("LAB-SUCC",), "MOT": ("PAL-SUCC",)},
}

# Il piano della **classe articolata** 2C (ondata 2): metà classe prosegue lo
# scientifico ordinario, metà segue Scienze Applicate — niente latino, tre ore
# di informatica al suo posto. È il caso reale delle scuole piccole, ed è la
# condizione 3 di ADR-015, provata finora solo su fixture sintetiche.
#
# 🔑 Le ore **comuni** sono dichiarate in **entrambi** i piani, perché sono ore
# che entrambe le popolazioni ricevono: la copertura misura per atomo, e un
# atomo che non trova nel proprio piano una materia che riceve è uno
# scostamento.
CURRICULUM[("SAP", "biennio")] = {
    "ITA": 4, "INF": 3, "ING": 3, "STG": 3, "MAT": 5, "FIS": 2, "SCI": 2,
    "DIS": 2, "MOT": 2, "IRC": 1, "ALT": 1,
}

# Le partizioni: classe → nome → [(parte, alunni previsti, piano proprio)].
# ⚠ `expected_students` è dichiarato su **ogni** parte, e non per completezza:
# `_effettivo` (domain/solver/rooms.py) restituisce `None` appena un'unità non
# ce l'ha, e un'eccedenza di capienza sparirebbe in silenzio.
PARTITIONS = {
    # 🔑 Ogni classe ha la partizione IRC / alternativa: è la forma che
    # `docs/edt/gruppi.md` documenta — **due parti della stessa classe**, non
    # due gruppi e non una compresenza.
    **{name: {"RELIGIONE": [(f"{name}_REL", rel, None), (f"{name}_ALT", students - rel, None)]}
       for name, _t, _y, _s, students in CLASSES
       for rel in [round(students * 0.78)]},
}
# I livelli di inglese di 1A e 1B, che si mescolano: è il **raggruppamento
# trasversale**, e il caso che rompe la decomposizione per classe.
for _c, _n in (("1A", 13), ("1B", 11)):
    PARTITIONS[_c]["INGLESE"] = [(f"{_c}_ING_B", _n, None), (f"{_c}_ING_A", _n, None)]
# Lo sdoppiamento a effettivo ridotto: un'ora di laboratorio di scienze a
# mezza classe, in 3A. È ciò che dà un senso ad `Al./Rid.`.
# ⚠ `Service.split_minutes` (`Sdop.`) resta `NULL`, e non per dimenticanza: la
# semantica del monte ore tripartito è **O3** in `docs/todo.md`, un esperimento
# ancora da fare in EDT. Riempirlo qui sarebbe inventare un campo, che è
# esattamente ciò che la convenzione della casa vieta.
PARTITIONS["3A"]["LABSCI"] = [("3A_G1", 13, None), ("3A_G2", 13, None)]
# La classe articolata: la parte ordinaria **eredita** il piano della classe
# (`NULL` = eredita, ADR-003), quella di Scienze Applicate ne porta uno proprio.
PARTITIONS["2C"]["ARTICOLAZIONE"] = [("2C_ORD", 14, None), ("2C_APP", 10, "SAP2")]

# I raggruppamenti trasversali: nome → parti, di classi diverse.
GROUPS = {
    "ING1-BASE": ["1A_ING_B", "1B_ING_B"],
    "ING1-AVANZ": ["1A_ING_A", "1B_ING_A"],
}

# 🔑 Le erogazioni che **non** sono a classe intera: (classe, materia) →
# [(unità, ore, allineamento)]. `None` come unità significa «a classe intera»,
# e una coppia assente da qui è interamente a classe intera.
#
# ⚠ L'`allineamento` è il campo `Activity.alignment_ident` — 📦 lo XSD dichiara
# che *l'allineamento genera l'attività complessa*. Qui si dichiara, e
# l'ondata 2 misura se il motore lo onora: vedi `esiti-attesi.md`.
EROGAZIONI = {
    # Lo sdoppiamento: due ore a classe intera, la terza a metà classe — e
    # quell'ora il docente la fa **due volte**, che è il costo dello
    # sdoppiamento e la ragione per cui N01 passa da 17 a 18 ore.
    ("3A", "SCI"): [(None, 2, ""), (("part", "3A_G1"), 1, "3A-LABSCI"),
                    (("part", "3A_G2"), 1, "3A-LABSCI")],
    # L'articolata: latino per gli ordinari, informatica per gli applicati,
    # nelle stesse tre ore.
    ("2C", "LAT"): [(("part", "2C_ORD"), 3, "2C-ART")],
    ("2C", "INF"): [(("part", "2C_APP"), 3, "2C-ART")],
    # Il raggruppamento trasversale: i due livelli attraversano 1A e 1B.
    ("1A", "ING"): [(("group", "ING1-BASE"), 3, "ING1")],
    ("1B", "ING"): [(("group", "ING1-AVANZ"), 3, "ING1")],
}
EROGAZIONI.update({(c[0], "IRC"): [(("part", f"{c[0]}_REL"), 1, f"REL-{c[0]}")]
                   for c in CLASSES})
EROGAZIONI.update({(c[0], "ALT"): [(("part", f"{c[0]}_ALT"), 1, f"REL-{c[0]}")]
                   for c in CLASSES})

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
    # ⚠ 18 e non 17: l'ora di laboratorio sdoppiata in 3A la fa **due volte**.
    ("N01", "Tosi Alberto", "TOSI",
     [("SCI", ["1A", "2A", "1C", "2C", "3A", "4A", "5A"])], 18, "SCI"),
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
    # 🔑 R02 esiste perché l'alternativa esiste: dodici classi, dodici ore, e
    # una materia senza classe di concorso. Senza di lei la partizione
    # IRC/alternativa sarebbe una parte vuota, cioè niente.
    ("R02", "Donati Marta", "DONAT", [("ALT", None)], 12, "ALT"),
    # ⚠ Tre ore. È lo **spezzone** che un'articolata produce davvero in una
    # scuola piccola, e il nostro modello lo rappresenta senza dire niente:
    # `Mh/s` è un numero, non una cattedra.
    ("I01", "Ricci Dario", "RICCI", [("INF", ["2C"])], 3, "INF"),
]


def _band(year):
    return "biennio" if year <= 2 else "triennio"


def _hours(track, year, subject_code):
    return CURRICULUM[(track, _band(year))].get(subject_code)


def _erogazione(class_name, subject_code, ore):
    """Come si eroga la coppia (classe, materia): una lista di
    `(unità, ore, allineamento)`. Il caso normale — tutto a classe intera — è
    la riga di default, così che le quattro forme dell'ondata 2 restino
    **eccezioni dichiarate** invece di un meccanismo generale."""
    return EROGAZIONI.get((class_name, subject_code), [(None, ore, "")])


def _ore_docente(class_name, subject_code, ore):
    """Le ore che il **docente** lavora per quella classe. ⚠ Non coincidono con
    quelle del quadro orario appena c'è uno sdoppiamento: l'ora di laboratorio
    a mezza classe si insegna due volte, e la riga di `TeachingAssignment` deve
    dire la verità sul carico, non sul curriculum."""
    return sum(h for _u, h, _i in _erogazione(class_name, subject_code, ore))


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
    quadri = [(f"{t}{y}", f"{label} - {y} anno", y, CURRICULUM[(t, _band(y))])
              for t, label in (("SCI", "Liceo Scientifico"),
                               ("CLA", "Liceo Classico"))
              for y in range(1, 6)]
    quadri.append(("SAP2", "Liceo Scientifico opz. Scienze Applicate - 2 anno",
                   2, CURRICULUM[("SAP", "biennio")]))
    for code, label, year, quadro in quadri:
        plan = StudyPlan.objects.create(code=code, name=label, year=year)
        for subject_code, hours in quadro.items():
            Service.objects.create(
                study_plan=plan, subject=subjects[subject_code],
                class_minutes=hours * 60,
                election_group=ELECTION_GROUP.get(subject_code))
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

    parts = {}
    for class_name, partizioni in PARTITIONS.items():
        for nome, righe in partizioni.items():
            partizione = ClassPartition.objects.create(
                school_class=classes[class_name], name=nome)
            for parte, alunni, piano in righe:
                parts[parte] = ClassPart.objects.create(
                    partition=partizione, name=parte, expected_students=alunni,
                    study_plan=plans[piano] if piano else None)
    groups = {}
    for nome, membri in GROUPS.items():
        gruppo = Group.objects.create(name=nome)
        gruppo.parts.set([parts[m] for m in membri])
        groups[nome] = gruppo

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
                    school_class=classes[class_name],
                    weekly_minutes=_ore_docente(class_name, subject_code, ore) * 60,
                )
                site = class_sites[class_name]
                for unita, quante, ident in _erogazione(class_name,
                                                        subject_code, ore):
                    for block in BLOCKS.get((subject_code, quante),
                                            [1] * quante):
                        activity = Activity.objects.create(
                            subject=subjects[subject_code],
                            duration_slots=block, duration_minutes=block * 60,
                            week_mask=year_mask, site=sites[site],
                            alignment_ident=ident,
                            # ⚠ Solo i blocchi lunghi: un'ora singola non può
                            # attraversare niente, e dichiararlo su tutte
                            # renderebbe la casella indistinguibile dal default.
                            respects_breaks=block > 1,
                        )
                        activity.teachers.add(t)
                        if unita is None:
                            activity.classes.add(classes[class_name])
                        elif unita[0] == "part":
                            activity.parts.add(parts[unita[1]])
                        else:
                            activity.groups.add(groups[unita[1]])
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
        "parts": parts, "groups": groups,
        "teachers": teachers, "subjects": subjects, "rooms": rooms,
        "year": year, "period": period, "schedule": schedule,
    }
