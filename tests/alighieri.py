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

**Ondata 3 — l'asse Cardinalità.** Le otto famiglie di
`ResourceTimeConstraint`, dieci righe, ognuna su un portatore scelto perché
quella famiglia abbia un soggetto vero — vedi `TIME_CONSTRAINTS` e
`data/liceo-alighieri/vincoli.md`.

**Ondata 5 — le risorse, il peso e le indisponibilità.** Il tecnico di
laboratorio e i carrelli di portatili (due delle cinque risorse di
piazzamento, e le uniche due che nessun dataset aveva), i tetti di peso
didattico e le sei righe di `ResourceUnavailability` nei tre livelli — vedi
`INDISPONIBILITA` e `data/liceo-alighieri/risorse.md`.

**Ondata 4 — l'asse Relazione.** I tredici tipi di `SubjectConstraint`, uno
per riga — vedi `SUBJECT_CONSTRAINTS` e `data/liceo-alighieri/relazioni.md`.
⚠ È l'ondata che ha fatto **crescere il dataset**: i quattro tipi `PARTS_*`
vogliono quattro portatori che non si implichino a vicenda, e con la sola 3A
sdoppiata non esistono. Da qui il secondo laboratorio, in 4A.

Le altre famiglie arrivano dalle ondate 5 in poi, e ognuna aggiunge righe a
`esiti-attesi.md` prima del codice che le esercita."""

import datetime as dt

from domain import weeks
from domain.models import (
    Activity, ActivityMaterialRequirement, Break, ClassPart, ClassPartition,
    CompetitionClass, Discipline, Group, InstituteSettings, Material, Period,
    QualityCriterion, RelaxationQuota, ResourceTimeConstraint,
    ResourceUnavailability, Room, Schedule, SchoolClass, SchoolYear, Service,
    Site, SlotLabel, StaffMember, StudyPlan, Subject, SubjectConstraint,
    Teacher, TeachingAssignment, TimeGrid,
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
# 🔑 E lo stesso laboratorio in 4A, che l'**ondata 4** aggiunge per una ragione
# sola e dichiarata: i quattro tipi `PARTS_*` vogliono quattro portatori che
# non si implichino a vicenda, e con una sola classe sdoppiata non esistono.
# Una riga d'ordine *per giornata* su un'unità implica l'omogeneità su ogni
# sotto-unità e su ogni mezza giornata, quindi con 3A da sola due dei quattro
# tipi sarebbero **presenti e implicati** — cioè il difetto che §6.4 esiste per
# non avere. È la stessa mossa del cappellano dell'ondata 3: una famiglia senza
# soggetto ne riceve uno.
PARTITIONS["4A"]["LABSCI"] = [("4A_G1", 13, None), ("4A_G2", 13, None)]
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
#
# 🔑 **Un ident per attività complessa, non per coppia di servizi** — la
# seconda correzione del 2026-08-31 (L5), e viene dalla stessa riga dello XSD:
# *«il convient de définir autant d'alignements que de cours complexes
# souhaités»*. Tre ore di latino parallele a tre di informatica sono **tre**
# attività complesse, non una da sei ore; scrivere un ident solo le avrebbe
# fuse tutte e sei sulla stessa fascia. Qui la tabella dichiara l'ident della
# **famiglia** e `_erogazione` lo numera per ora (`2C-ART-1`, `-2`, `-3`)
# quando le ore sono più d'una — vedi `_ident`.
EROGAZIONI = {
    # Lo sdoppiamento: due ore a classe intera, la terza a metà classe — e
    # quell'ora il docente la fa **due volte**, che è il costo dello
    # sdoppiamento e la ragione per cui N01 passa da 17 a 18 ore.
    #
    # ⚠ E l'allineamento è **vuoto**, corretto il 2026-08-31 chiudendo L5:
    # l'ondata 2 aveva scritto `3A-LABSCI` sulle due metà, ed era la stessa
    # confusione che l'ondata 6 avrebbe poi respinto sull'ora quindicinale.
    # Le due metà hanno lo **stesso docente** e non sono mai simultanee:
    # allinearle dice il contrario di ciò che sono, ed è insoddisfacibile per
    # costruzione. *Sdoppiare non è allineare*, come alternare non lo è.
    ("3A", "SCI"): [(None, 2, ""), (("part", "3A_G1"), 1, ""),
                    (("part", "3A_G2"), 1, "")],
    ("4A", "SCI"): [(None, 2, ""), (("part", "4A_G1"), 1, ""),
                    (("part", "4A_G2"), 1, "")],
    # L'articolata: latino per gli ordinari, informatica per gli applicati,
    # nelle stesse tre ore.
    ("2C", "LAT"): [(("part", "2C_ORD"), 3, "2C-ART")],
    ("2C", "INF"): [(("part", "2C_APP"), 3, "2C-ART")],
    # Il raggruppamento trasversale: i due livelli attraversano 1A e 1B.
    ("1A", "ING"): [(("group", "ING1-BASE"), 3, "ING1")],
    ("1B", "ING"): [(("group", "ING1-AVANZ"), 3, "ING1")],
}
# 🔑 **L'ondata 6: l'ora quindicinale.** La seconda ora di scienze del 5B è a
# settimane alterne — una in laboratorio col tecnico, una di teoria in aula —
# e le due metà portano maschere **complementari**. È la quinta forma di
# erogazione del banco, e l'unica che **non costa un'ora**: in ogni settimana
# ne è attiva esattamente una, quindi il docente lavora due ore e l'alunno ne
# riceve due, come prima. Lo sdoppiamento delle ondate 2 e 4 costa invece
# l'ora in più che il docente ripete.
#
# ⚠ È anche l'unica riga del dataset che dà a `week_signatures` più di una
# firma: fino all'ondata 5 ogni maschera era l'anno intero, e metà del motore
# — l'occupazione che distingue le firme, i criteri di qualità che **non** le
# distinguono — non aveva mai avuto un dato su cui mostrarsi.
# ⚠ E l'allineamento resta **vuoto**, che è una scelta e non una dimenticanza:
# 📦 lo XSD dichiara che *l'allineamento genera l'attività complessa*, cioè una
# collocazione sola per le attività allineate. Le due metà non sono simultanee
# — non lo sono **mai** — quindi allinearle direbbe il contrario di ciò che
# sono. Alternare non è allineare.
EROGAZIONI[("5B", "SCI")] = [
    (None, 1, ""),                                   # l'ora settimanale
    (None, 1, "", {"settimane": "pari",
                   "aule": ("LAB-SCI", "LAB-INF"), "tecnico": True}),
    (None, 1, "", {"settimane": "dispari", "aule": ()}),
]
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
    # ⚠ 19 e non 17: le **due** ore di laboratorio sdoppiate — 3A (ondata 2) e
    # 4A (ondata 4) — le fa due volte ciascuna.
    ("N01", "Tosi Alberto", "TOSI",
     [("SCI", ["1A", "2A", "1C", "2C", "3A", "4A", "5A"])], 19, "SCI"),
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
    # sedi: è il portatore di `max_site_changes` (ondata 3), ed è già da qui
    # ciò che rende `structural:site_transition` non muto.
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


# 🔑 **L'asse Cardinalità** (ondata 3): le otto famiglie di
# `ResourceTimeConstraint`, in dieci righe. Ogni riga dichiara la famiglia che
# deve far scattare e il **portatore** scelto perché quella famiglia abbia un
# soggetto vero: un tetto su un docente che non arriverebbe mai a toccarlo non
# è un vincolo, è una riga.
#
# ⚠ Non sono valori realistici a caso: sono valori **al bordo**. Per otto delle
# nove famiglie una tacca più stretta rende il dataset INFEASIBLE, ed è la
# prova che la famiglia morde invece di essere soddisfatta per caso — vedi
# `tests/test_alighieri_cardinalita.py` e `data/liceo-alighieri/vincoli.md`.
# La nona (il D.T.B.) non ci arriva, ed è misurato e dichiarato lì.
#
# (nome, "t"|"c", portatore, tipo, params)
TIME_CONSTRAINTS = [
    # Le dieci ore di scienze del classico su almeno quattro giorni da due:
    # senza, il solver le accorpa. N02 ha dieci ore, quindi 4 × 2 = 8 le sta
    # dentro, e 5 × 3 = 15 no — che è la tacca più stretta.
    ("min_distribution", "t", "URBAN", "min_distribution",
     {"min_days": 4, "min_minutes_per_day": 120}),
    # Il tetto della mattina **sotto** quello della giornata: 21 ore con al più
    # 3 in mattinata fanno almeno 6 ore di pomeriggio. È la forma che EDT usa
    # per spingere un docente fuori dalla fascia contesa.
    ("max_hours", "t", "RINAL", "max_hours",
     {"day_minutes": 300, "morning_minutes": 180}),
    # Il tempo parziale: dodici ore in tre giorni, e presenza (buchi compresi)
    # al più cinque fasce. Due giornate intere vuote.
    ("max_presence", "t", "GENTI", "max_presence",
     {"days": 3, "max_minutes": 300}),
    # Non entra alla prima ora, e vale per tutte e cinque le giornate.
    ("arrival_departure", "t", "VITAL", "arrival_departure",
     {"days": 5, "not_before_slot": 1}),
    # Due giorni liberi garantiti più due mezze giornate libere: le due soglie
    # della stessa riga, che il builder tiene sotto **un solo** booleano.
    ("free_guaranteed", "t", "ZANET", "free_guaranteed",
     {"free_days": 2, "free_half_days": 2}),
    # Il `MMG` della classe: 2A lavora 28 fasce, cinque mattine ne fanno 25,
    # quindi sette mezze giornate sono due pomeriggi e non tre.
    ("max_half_days", "c", "2A", "max_half_days", {"max_half_days": 7}),
    # Il `MG`, l'altro ramo della stessa famiglia: mai mattina **e** pomeriggio
    # nello stesso giorno. Su P02 Bruni, dodici ore di scienze motorie sparse
    # su sei classi e due sedi.
    #
    # ⚠ **Era sull'insegnante di alternativa, e L5 l'ha dovuta spostare**
    # (2026-08-31). Onorato l'allineamento, l'orario di R02 Donati *è* quello
    # del cappellano — le stesse dodici celle — e il cappellano viene due
    # giorni (la riga qui sotto, che serve alle sedi). Dodici ore in due
    # giornate con una sola mezza giornata ciascuna fanno al più dieci: le due
    # righe erano incompatibili, e la deroga le teneva in piedi consumandosi
    # tutta. Il `MG` su Donati aveva quindi smesso di essere un vincolo su di
    # lei per diventarne uno sul cappellano — cioè aveva perso il **soggetto**,
    # che è la condizione con cui questa tabella sceglie i portatori.
    ("only_half_day", "t", "BRUNI", "max_half_days",
     {"only_half_day_per_day": True}),
    # 🔑 **Il cappellano viene due giorni.** Questa riga non è qui per
    # `max_presence` — quello ce l'ha già GENTI — ma per dare un soggetto a
    # `max_site_changes`: senza, R01 spalma le dodici ore su cinque giorni e
    # dedica una giornata intera alla succursale, e allora *zero* cambi di sede
    # è soddisfacibile e il vincolo non vincola niente. Con due sole giornate
    # le dieci ore della centrale non stanno in una, quindi la succursale deve
    # condividere una giornata: il cambio diventa **inevitabile**, e limitarlo
    # a uno è una scelta. È il caso vero delle scuole con una sede staccata.
    ("cappellano", "t", "COLOM", "max_presence", {"days": 2, "max_minutes": 480}),
    ("max_site_changes", "t", "COLOM", "max_site_changes",
     {"per_day": 1, "per_week": 1}),
    # Il D.T.B.: al più un'ora di buco in tutta la settimana. ⚠ È l'unica delle
    # nove righe che **non** è al bordo, ed è misurato: zero buchi per *ogni*
    # docente e per *ogni* classe resta OPTIMAL. Con 40 fasce e cattedre da
    # 10–21 ore la contiguità è gratis, e stringerla vuole una griglia più
    # densa — cioè l'ondata 7. Vedi `esiti-attesi.md`.
    ("max_gap_hours", "t", "CAVAL", "max_gap_hours", {"max_gap_minutes": 60}),
]


# 🔑 **L'asse Relazione** (ondata 4): i tredici tipi di `SubjectConstraint`,
# una riga per tipo. Qui il portatore non è una risorsa ma una **coppia
# (unità, materia)**: la riga vive su una classe, su una parte o su un
# raggruppamento, e mette in relazione due materie — con A = B come caso
# dominante, che è come le scuole scrivono davvero questi vincoli.
#
# ⚠ **La verifica di questa ondata non è la tacca dell'ondata 3, ed è più
# forte.** Un vincolo di cardinalità si stringe di un'unità e diventa
# `INFEASIBLE`; un divieto di relazione no — trentanove fasce libere assorbono
# quasi ogni proibizione, e una riga può essere soddisfatta *per caso*. Il
# testimone di questa ondata è quindi **puntato**: si impone con `pinned` la
# configurazione che la riga vieta e si pretende `INFEASIBLE`, e si rifà lo
# stesso solve **senza la riga** pretendendo che torni risolvibile. Sono due
# affermazioni sul **modello**, non su quale ottimo la ricerca abbia scelto —
# cioè esattamente ciò che all'ondata 3 mancava alla mutazione per rimozione.
# Vedi `tests/test_alighieri_relazione.py` e `data/liceo-alighieri/vincoli.md`.
#
# (nome, unità, materia A, materia B, tipo, param)
SUBJECT_CONSTRAINTS = [
    # Mai matematica e fisica nella stessa mezza giornata: è la riga che le
    # scuole scrivono per non concentrare le materie scientifiche.
    ("same_half_day", ("c", "5A"), "MAT", "FIS",
     "same_half_day_incompatible", None),
    # Le due lingue del classico mai lo stesso giorno. ⚠ Il divieto non impone
    # nessuno sparpagliamento: più ore della stessa materia possono stare nello
    # stesso giorno, quindi da solo è sempre soddisfacibile — e per questo il
    # suo testimone è puntato.
    ("same_day", ("c", "4B"), "LAT", "GRE", "same_day_incompatible", None),
    # Il greco del 3B mai a un giorno di distanza da sé stesso: tre ore che non
    # possono stare su giorni adiacenti stanno **solo** su {lun, mer, ven}.
    ("two_days", ("c", "3B"), "GRE", "GRE", "two_days_incompatible", None),
    # Dopo le due ore di educazione fisica, non matematica.
    ("forbidden_sequence", ("c", "4A"), "MOT", "MAT",
     "forbidden_sequence", None),
    # Al più tre ore di matematica in una mezza giornata: in 2A la matematica è
    # 2 + 1 + 1 + 1, quindi il tetto morde solo sulle concentrazioni.
    ("max_hours_half_day", ("c", "2A"), "MAT", "MAT",
     "max_hours_half_day", 180),
    # 🔑 Al più due ore di italiano al giorno in 3B — e questa riga si intreccia
    # con l'**ondata 3**: l'italiano del 3B lo insegna GENTI, che ha
    # `max_presence {days: 3}`. Portare il tetto a un'ora sola vorrebbe quattro
    # giornate distinte per quattro ore, e GENTI ne lavora tre: è la tacca, ed
    # è un argomento di conteggio che attraversa i due assi.
    ("max_hours_day", ("c", "3B"), "ITA", "ITA", "max_hours_day", 120),
    # La prima ora di latino della settimana precede la prima di greco.
    ("weekly_order", ("c", "5B"), "LAT", "GRE", "weekly_order", None),
    # Le due sessioni di fisica di 3A (il blocco da due ore e l'ora singola)
    # concatenate: al più una mezza giornata di ritardo fra l'una e l'altra.
    ("imposed_succession", ("c", "3A"), "FIS", "FIS",
     "imposed_succession", 1),
    # 🔑 Il latino del 1B distanziato di almeno **due** mezze giornate: cinque
    # ore con passo ≥ 2 occupano un arco di almeno otto mezze giornate su
    # dieci, cioè una sola ora di latino al giorno. A tre il passo vorrebbe un
    # arco di dodici, e le mezze giornate sono dieci: la tacca è aritmetica.
    ("half_day_gap", ("c", "1B"), "LAT", "LAT", "half_day_gap", 2),
    # 🔑 I quattro `PARTS_*`, e i loro quattro portatori scelti perché **non si
    # implichino**. Le due metà di 3A ruotano attorno all'ora di teoria — la
    # prima fa laboratorio *prima*, la seconda *dopo* — mentre sulla classe
    # intera vale la regola più debole: dentro una mezza giornata niente
    # interlacciatura. In 4A resta solo quest'ultima, per giornata.
    ("parts_before", ("p", "3A_G1"), "SCI", "SCI", "parts_before_class", None),
    ("parts_after", ("p", "3A_G2"), "SCI", "SCI", "parts_after_class", None),
    ("parts_h", ("c", "3A"), "SCI", "SCI",
     "parts_before_or_after_class_h", None),
    ("parts_ab", ("c", "4A"), "SCI", "SCI",
     "parts_before_or_after_class_ab", None),
]


# 🔑 **L'ondata 5**: le due risorse che nessun dataset aveva, i tetti di peso
# didattico e le indisponibilità.

#: Il **peso didattico** (ADR-011). ⚠ In una base reale del prodotto i quattro
#: tetti d'istituto sono a «nessuno» e ogni materia pesa 1 — il Fermi è fedele,
#: e `structural:didactic_weight` non ha quindi mai visto un dato. Qui la
#: scuola dichiara una politica: le **materie d'indirizzo** pesano due, e i
#: tetti tengono la giornata dell'alunno sotto controllo.
PESI_DIDATTICI = {"MAT": 2, "LAT": 2, "GRE": 2}

#: I tre tetti d'istituto, e nessuno è vacuo: una mezza giornata di cinque
#: fasce tutte d'indirizzo pesa 10 (> 9), un pomeriggio di tre ne pesa 6
#: (> 5), una giornata piena di otto fasce con cinque d'indirizzo ne pesa 13
#: (> 12). ⚠ Il tetto **settimanale** d'istituto resta `None`: al suo posto
#: c'è quello della classe, che secondo il checker **prevale**, ed è l'unico
#: modo di esercitare quel ramo.
TETTI_PESO = {"morning": 9, "afternoon": 5, "day": 12}

#: Il tetto settimanale **della classe**, sul 3B: 40 è esattamente il peso
#: settimanale delle sue due unità-studente (39 di classe + l'ora di IRC o di
#: alternativa). ⚠ È un tetto **indipendente dal piazzamento** — la somma non
#: dipende da dove le attività vanno — quindi non ha un testimone puntato: o
#: l'orario esiste, o non esiste. La sua verifica è la tacca.
TETTO_SETTIMANALE_CLASSE = ("3B", 40)

#: 🔑 Le **altre due risorse di piazzamento**: il tecnico di laboratorio e i
#: carrelli di portatili. `Resource` le prevede da sempre (cinque tipi, come
#: nel pannello dell'attività di EDT) e nessun dataset ne aveva una: né il
#: Fermi né l'Alighieri fino a qui.
TECNICO = ("TECN", "Tecnico di laboratorio", "Centrale")
#: Quattro carrelli, dodici portatili l'uno. La capienza simultanea è il
#: numero di carrelli; la **quantità** di ogni richiesta è quanti ne serve
#: quell'unità — ed è il campo che rende l'occupazione *cumulativa* invece
#: che binaria.
#:
#: ⚠ **Quattro e non tre, e il numero l'ha deciso l'ondata 2.** A tre i due
#: livelli d'inglese (due carrelli l'uno) non potrebbero più stare nella
#: stessa fascia — e stare nella stessa fascia è *il senso* di un
#: raggruppamento trasversale, non un dettaglio. Un banco che rompesse una
#: forma dell'ondata precedente per accendere un builder starebbe misurando
#: sé stesso.
CARRELLI = ("CARRELLO", 4)
POSTI_PER_CARRELLO = 12

#: 🔑 Le **indisponibilità**, rosse gialle e verdi, e su tre tipi di risorsa
#: diversi: il meccanismo è generico sulla risorsa (`docs/edt/vincoli.md`), e
#: un dataset che le mettesse solo sui docenti non lo mostrerebbe.
#:
#: ⚠ I tre livelli **non** si comportano allo stesso modo, ed è il punto:
#: la rossa vieta, la gialla vieta *ma* può essere autorizzata per **tipo** di
#: risorsa (`ignora_opzionali`, mai per la singola — A4), la verde non vieta
#: affatto. Le sei righe qui sotto sono scelte perché ciascuna delle tre
#: affermazioni sia misurabile: vedi `tests/test_alighieri_risorse.py`.
#:
#: (nome, "t"|"c"|"r", portatore, livello, celle)
INDISPONIBILITA = [
    # 🔑 Lo **spezzone**: RICCI ha tre ore e viene due pomeriggi — due fasce il
    # mercoledì e una il venerdì. Le tre ore stanno in tre fasce, quindi la
    # riga è al bordo — una fascia rossa in più e l'orario non esiste. È
    # l'unica famiglia dell'ondata che ammette la tacca dell'ondata 3.
    #
    # ⚠ **Le tre fasce erano un pomeriggio solo, e L5 le ha spezzate**
    # (2026-08-31). L'articolata dichiara latino e informatica *nelle stesse
    # tre ore*: onorato l'allineamento, quelle tre ore sono le tre di RICCI, e
    # tre ore di latino nello stesso pomeriggio pesano 6 contro il tetto di 5.
    # Le tre affermazioni — l'articolata parallela, lo spezzone concentrato, il
    # peso d'indirizzo — erano incompatibili, e nessuno se ne accorgeva perché
    # nessun builder leggeva l'allineamento. Il bordo non si è mosso: tre
    # fasce libere per tre ore, come prima.
    ("ricci", "t", "RICCI", "hard",
     [(d, s) for d in range(5) for s in range(8)
      if (d, s) not in {(2, 5), (2, 6), (4, 7)}]),
    # Il pomeriggio di orientamento della 5A: la classe non c'è.
    ("orientamento", "c", "5A", "hard", [(2, s) for s in (5, 6, 7)]),
    # La palestra è concessa alla scuola media il lunedì mattina. ⚠ Vale come
    # vincolo di **fase 1** perché è candidata unica per le scienze motorie
    # alla centrale: con due candidate l'aula non entra nei token.
    ("palestra", "r", "PALESTRA", "hard", [(0, s) for s in range(5)]),
    # Il permesso del venerdì pomeriggio: **gialla**, cioè rispettata come una
    # rossa finché non si autorizza il motore a ignorarla.
    ("permesso", "t", "SARTO", "optional", [(4, s) for s in (5, 6, 7)]),
    # La manutenzione del laboratorio della succursale: gialla su un'**aula**,
    # cioè su un tipo di risorsa diverso — è ciò che rende visibile che
    # l'autorizzazione è per categoria e non per riga.
    # 🔑 **E su un'aula a candidata unica, non per caso.** Su un'aula con più
    # candidate la fase 1 e la fase 2 leggono il giallo in modo diverso, e il
    # prezzo è una rinuncia: è il difetto **L6bis**, che ha un test suo
    # (`tests/test_alighieri_risorse.py`) invece di stare nel dataset — un
    # banco che porta un difetto noto smette di misurare le regressioni.
    ("manutenzione", "r", "LAB-SUCC", "optional", [(0, 0), (0, 1)]),
    # La preferenza: AMATO non vorrebbe la prima ora. **Verde**, quindi non
    # vieta niente — il suo posto è un livello di qualità, non un pre-filtro.
    ("preferenza", "t", "AMATO", "preference", [(d, 0) for d in range(5)]),
]


# 🔑 **L'ondata 6: le quote di alleggerimento**, nelle due forme che la
# finestra `Alleggerimenti` di EDT distingue — il **margine** («Autorizza un
# supplemento di …») e la **deroga** («Non considerare …»).
#
# ⚠ **Nessuna delle due è consumata dal dataset**, ed è una scelta obbligata:
# l'ondata 3 pretende che l'orario di base non porti nessun finding `HARD`
# oltre alle aule non assegnate, e una quota consumata **è** una violazione
# nominata — la quota autorizza, non nasconde (`domain/solver/relaxation.py`).
# Le righe stanno qui perché i builder le leggano e postino i letterali su
# dati veri; la tensione la mette il testimone, come per i divieti
# dell'ondata 4. Vedi `tests/test_alighieri_quote.py`.
#
# ⚠ E i due portatori sono scelti perché **non sono bordi**: allentare un
# bordo dell'ondata 3 renderebbe risolvibile la sua tacca, cioè spegnerebbe
# un test scritto tre ondate fa. Il bordo del `MG` sta sulla 2A e non su
# BRUNI; quello di `max_presence` sta su GENTI e non su COLOM.
#
# (nome, famiglia, portatore, max_violations, params)
QUOTE = [
    # La deroga: P02 può fare mattina **e** pomeriggio una volta a settimana.
    # ⚠ Segue il portatore del `MG`, che L5 ha spostato da R02 a P02: una
    # deroga senza la sua riga non autorizza niente.
    ("mg_bruni", "half_days", "BRUNI", 1, {}),
    # Il margine: il cappellano può allungare la giornata di tre ore, e due
    # volte — una per giornata. ⚠ Il letterale è **per giorno**, non per riga:
    # «una volta per settimana e per docente» conta le volte che il
    # supplemento si usa, e un letterale solo direbbe «una volta, ovunque».
    ("presenza_cappellano", "max_presence", "COLOM", 2, {"margine": 180}),
]


#: 🔑 **L'ondata 6: la gerarchia dei criteri di qualità.** Sette generi, otto
#: righe, e le due popolazioni: è la tabella intera di `QualityCriterion`, che
#: nessun dataset aveva. (Erano cinque e sei fino a O5, che ha aggiunto i due
#: criteri di *piazzamento* tradotti — ADR-025.) L'ordine è un **dato** e non codice, perché è il punto
#: dichiarato del meccanismo — un criterio che non compare è un criterio
#: *ignorato*, e la tabella vuota dà la catena senza qualità.
#:
#: ⚠ **`build()` non la installa**, e la ragione è una misura: con questi sei
#: livelli un solo `solve` sul banco passa da 9 a **82 secondi**, e ogni test
#: dell'Alighieri li pagherebbe. È la stessa ragione per cui esiste
#: `BUDGET_QUALITA`: un livello di qualità non è lento perché difficile da
#: ottimizzare, è lento perché **impossibile da dimostrare**. Chi vuole la
#: qualità la chiede — `build(qualita=True)`.
#:
#: (genere, popolazione, rango)
CRITERI_QUALITA = [
    # I buchi per primi, e prima quelli dei docenti: in EDT i buchi occupano
    # **quattro** degli undici criteri di piazzamento, e le posizioni 1, 2, 5
    # e 6. Separati per popolazione perché EDT li dichiara tali.
    ("gaps", "teachers", 1),
    ("gaps", "classes", 2),
    ("isolated", "all", 3),
    ("free_half_days", "teachers", 4),
    # ⚠ L'equilibrio didattico solo sulle **classi**: nella base di esempio di
    # EDT l'orario delle classi ha questo come primo e unico criterio, e quello
    # dei docenti non lo ha affatto. L'asimmetria è del prodotto, non nostra.
    ("regularity", "classes", 5),
    # 🔑 I due di O5, e sulle popolazioni che EDT dichiara: la
    # **distribuzione** nella settimana è un bene degli studenti, la
    # **varietà** di fascia è un bene dei docenti. ⚠ `regularity` e
    # `slot_spread` sono i due versi opposti dello stesso conto, e stanno qui
    # su popolazioni **diverse**: sulla stessa il secondo sarebbe inerte, e un
    # test lo misura invece di dichiararlo.
    ("weekly_spread", "classes", 6),
    ("slot_spread", "teachers", 7),
    # Il pennello **verde**, undicesimo e ultimo: cede a tutto il resto. È il
    # criterio che dà un posto alla riga `preferenza` dell'ondata 5, la sola
    # indisponibilità che non vieta niente.
    ("preferences", "all", 8),
]


def criteri_di_qualita():
    """Installa `CRITERI_QUALITA`. Sta fuori da `build()` perché in EDT
    l'ottimizzazione è un comando **separato**, che si lancia su un orario che
    già c'è: `Ottimizza gli orari dei docenti` non è una fase del calcolo. E
    perché quei livelli costano: erano 82 secondi a `solve` in sei."""
    for genere, popolazione, rango in CRITERI_QUALITA:
        QualityCriterion.objects.create(
            kind=QualityCriterion.Kind(genere),
            population=QualityCriterion.Population(popolazione), rank=rango)


def _serve_tecnico(subject_code, block, unita, extra):
    """Il tecnico sta in laboratorio: le due ore di fisica del triennio
    scientifico, le ore di scienze a mezza classe e — dall'ondata 6 — la metà
    di laboratorio dell'ora quindicinale, che lo dichiara per nome. ⚠ È
    **uno**, quindi due laboratori non possono essere simultanei — che è il
    vincolo vero delle scuole, e nel nostro modello è occupazione come tutte
    le altre."""
    if extra.get("tecnico"):
        return True
    return (subject_code == "FIS" and block == 2) or (subject_code == "SCI"
                                                      and unita is not None)


def _carrelli(subject_code, unita, alunni):
    """Quanti carrelli servono a un'attività: uno ogni dodici alunni, e solo
    dove si lavora a piccoli gruppi — i due livelli di inglese, l'informatica
    della classe articolata e le ore di laboratorio a mezza classe. ⚠ Metterli
    anche sulle lezioni a classe intera li renderebbe una risorsa contesa da
    trenta attività, cioè un vincolo di esclusione mutua travestito da
    materiale."""
    if unita is None or subject_code not in ("ING", "INF", "SCI"):
        return 0
    return -(-alunni // POSTI_PER_CARRELLO)

def _band(year):
    return "biennio" if year <= 2 else "triennio"


def _hours(track, year, subject_code):
    return CURRICULUM[(track, _band(year))].get(subject_code)


def _erogazione(class_name, subject_code, ore):
    """Come si eroga la coppia (classe, materia): una lista di
    `(unità, ore, allineamento, extra)`. Il caso normale — tutto a classe
    intera — è la riga di default, così che le forme dell'ondata 2 restino
    **eccezioni dichiarate** invece di un meccanismo generale.

    ⚠ `extra` è la quarta voce **opzionale** che l'ondata 6 ha aggiunto, e la
    sua opzionalità è la ragione per cui la tabella non è stata riscritta: le
    dieci righe che c'erano non dichiarano niente di nuovo, e continuano a
    leggersi come prima. Le chiavi sono `settimane` (`"pari"` / `"dispari"`,
    la maschera), `aule` (le candidate, che sostituiscono `SPECIAL_ROOMS`) e
    `tecnico`."""
    righe = EROGAZIONI.get((class_name, subject_code), [(None, ore, "")])
    return [(u, h, i, resto[0] if resto else {}) for u, h, i, *resto in righe]


def _ident(ident, quante, n):
    """L'ident dell'**attività complessa** n-esima della famiglia `ident`.

    📦 *«autant d'alignements que de cours complexes souhaités»*: una famiglia
    di tre ore parallele sono tre attività complesse, quindi tre ident. Con
    una sola ora la numerazione non aggiunge niente e l'ident resta quello
    dichiarato (`REL-1A`), che è anche il nome con cui i test lo cercano."""
    if not ident or quante == 1:
        return ident
    return f"{ident}-{n}"


def _settimane(spec):
    """Le settimane in cui una riga di erogazione è attiva. ⚠ 17 e 16 su 33,
    non 16,5: un anno con un numero dispari di settimane dà a una delle due
    metà una volta in più, ed è un fatto del calendario e non un difetto."""
    if spec is None:
        return range(WEEKS_IN_YEAR)
    resto = 0 if spec == "pari" else 1
    return [w for w in range(WEEKS_IN_YEAR) if w % 2 == resto]


def _maschera(spec):
    return sum(weeks.single_week(w) for w in _settimane(spec))


def _carico_docente(class_name, subject_code, ore):
    """Le ore che il **docente** lavora per quella classe, **in una settimana**
    e **per unità**: `{unità: ore}`, con l'unità nella stessa forma di
    `EROGAZIONI` (`None`, `("part", …)`, `("group", …)`).

    ⚠ Non coincidono con quelle del quadro orario appena c'è uno sdoppiamento:
    l'ora di laboratorio a mezza classe si insegna due volte, e la riga di
    `TeachingAssignment` deve dire la verità sul carico, non sul curriculum.

    🔑 E dall'ondata 6 il conto è **per settimana**, non una somma: una coppia
    quindicinale porta due righe da un'ora e costa **un'ora**, perché in ogni
    settimana ne è attiva una sola. Che il totale non dipenda dalla settimana
    non è un'ipotesi: si calcola su tutte e trentatré e si pretende che sia lo
    stesso numero. Un dataset le cui maschere non compongono un monte ore
    costante fa fallire il `build`, che è il posto giusto in cui accorgersene
    — la stessa proprietà per cui `CoverageChecker` legge la maschera invece
    di sommare le durate.

    🔑 **Dal 2026-08-31 il conto è anche per unità** (L10), ed è ciò che rende
    la cattedra capace di dire *a chi* l'ora è erogata e non solo quanta ne
    è. La costanza si pretende ora su ogni unità separatamente, che è una
    condizione più forte della vecchia sul totale: una coppia quindicinale che
    alternasse la classe intera con una sua parte la violerebbe, e il `build`
    lo direbbe. Nessuna riga del banco lo fa.

    ⚠ **La derivazione è dichiarata, e con essa il suo prezzo**: le cattedre
    del banco escono da `EROGAZIONI`, cioè dalla stessa tabella che genera le
    attività, quindi su questo dataset `structural:workload` **non può**
    fallire. È voluto — è così che le due dichiarazioni non tornano a
    divergere — ma vuol dire che qui il banco fa da controllo su scala (23
    docenti, 144 cattedre, zero scostamenti) e non da prova. La prova sta sul
    testimone puntato di `test_workload.py`, che le scrive discordi apposta e
    porta il proprio ramo di controllo."""
    righe = _erogazione(class_name, subject_code, ore)
    out = {}
    for unita in {u for u, _h, _i, _e in righe}:
        per_settimana = {
            sum(h for u, h, _i, extra in righe
                if u == unita and w in _settimane(extra.get("settimane")))
            for w in range(WEEKS_IN_YEAR)
        }
        assert len(per_settimana) == 1, (class_name, subject_code, unita,
                                         per_settimana)
        out[unita] = per_settimana.pop()
    return out


def build(qualita=False):
    """Costruisce il banco. `qualita=True` installa anche `CRITERI_QUALITA` —
    fuori dal default perché quei sei livelli costano 82 secondi a `solve`,
    misurati, e la gran parte dei test del banco misura il modello **hard**."""
    settings = InstituteSettings.load()
    settings.default_max_reduced_students = 15
    settings.site_transition_slots = 1
    # I tetti di peso didattico (ondata 5). ⚠ Il settimanale resta `None`:
    # sul 3B lo porta la **classe**, ed è il ramo che prevale.
    settings.max_weight_morning = TETTI_PESO["morning"]
    settings.max_weight_afternoon = TETTI_PESO["afternoon"]
    settings.max_weight_day = TETTI_PESO["day"]
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
            code=code, name=name, discipline=disciplines[disc],
            didactic_weight=PESI_DIDATTICI.get(code, 1))

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
            max_weekly_weight_per_student=(
                TETTO_SETTIMANALE_CLASSE[1]
                if name == TETTO_SETTIMANALE_CLASSE[0] else None),
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

    # Le due risorse dell'ondata 5. Il tecnico ha una sede (sta alla
    # centrale, dove sono i laboratori); i carrelli no — sono della scuola, e
    # girano fra le due sedi. ⚠ Quel `site=None` è ciò che rende il carrello
    # il portatore di una domanda che nessun'altra risorsa poneva: vedi
    # `data/liceo-alighieri/risorse.md`.
    codice, ruolo, sede_tecnico = TECNICO
    tecnico = StaffMember.objects.create(name=codice, role=ruolo,
                                         site=sites[sede_tecnico])
    nome_carrelli, quanti_carrelli = CARRELLI
    carrelli = Material.objects.create(name=nome_carrelli,
                                       simultaneous_capacity=quanti_carrelli)

    def _alunni(unita):
        if unita is None:
            return None
        if unita[0] == "part":
            return parts[unita[1]].expected_students
        return sum(p.expected_students for p in groups[unita[1]].parts.all())

    teachers = {}
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
                # L10: una cattedra per **unità servita**, non una per
                # classe. Sul raggruppamento trasversale è la differenza fra
                # dire il vero e dire il falso: NOVEL non fa l'inglese della
                # 1A, fa metà 1A e metà 1B.
                for unita, ore_doc in sorted(
                        _carico_docente(class_name, subject_code, ore).items(),
                        key=lambda kv: (kv[0] is not None, kv[0] or ())):
                    TeachingAssignment.objects.create(
                        teacher=t, subject=subjects[subject_code],
                        school_class=(classes[class_name] if unita is None
                                      else None),
                        class_part=(parts[unita[1]] if unita
                                    and unita[0] == "part" else None),
                        group=(groups[unita[1]] if unita
                               and unita[0] == "group" else None),
                        weekly_minutes=ore_doc * 60,
                    )
                site = class_sites[class_name]
                for unita, quante, ident, extra in _erogazione(
                        class_name, subject_code, ore):
                    for n, block in enumerate(
                            BLOCKS.get((subject_code, quante), [1] * quante),
                            start=1):
                        activity = Activity.objects.create(
                            subject=subjects[subject_code],
                            duration_slots=block, duration_minutes=block * 60,
                            week_mask=_maschera(extra.get("settimane")),
                            site=sites[site],
                            alignment_ident=_ident(ident, quante, n),
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
                        candidate = extra.get(
                            "aule", SPECIAL_ROOMS[site].get(subject_code, ()))
                        for room_name in candidate:
                            activity.rooms.add(rooms[room_name])
                        if _serve_tecnico(subject_code, block, unita, extra):
                            activity.staff.add(tecnico)
                        quanti = _carrelli(subject_code, unita,
                                           _alunni(unita) or 0)
                        if quanti:
                            ActivityMaterialRequirement.objects.create(
                                activity=activity, material=carrelli,
                                quantity=quanti)
        teachers[tid] = t

    # L'asse Cardinalità (ondata 3). Il portatore si nomina per abbreviazione
    # o per nome di classe: `TIME_CONSTRAINTS` resta leggibile come una tabella
    # e non come una lista di pk.
    per_abbr = {t.abbreviation: t for t in teachers.values()}
    for _nome, kind, ref, tipo, params in TIME_CONSTRAINTS:
        ResourceTimeConstraint.objects.create(
            resource=per_abbr[ref] if kind == "t" else classes[ref],
            type=ResourceTimeConstraint.Type(tipo), params=params)

    # L'asse Relazione (ondata 4). L'unità si nomina per tipo e nome — "c"
    # classe, "p" parte, "g" raggruppamento — così la tabella resta leggibile.
    unita = {"c": classes, "p": parts, "g": groups}
    for _nome, (kind, ref), a, b, tipo, param in SUBJECT_CONSTRAINTS:
        campo = {"c": "school_class", "p": "class_part", "g": "group"}[kind]
        SubjectConstraint.objects.create(
            **{campo: unita[kind][ref]}, subject_a=subjects[a],
            subject_b=subjects[b], type=SubjectConstraint.Type(tipo),
            param=param)

    # Le indisponibilità (ondata 5). La risorsa si nomina per abbreviazione,
    # per nome di classe o per nome d'aula: la tabella resta leggibile, e i
    # tre tipi accanto sono ciò che mostra che il meccanismo è **generico**.
    portatori = {"t": per_abbr, "c": classes, "r": rooms}
    for _nome, kind, ref, livello, celle in INDISPONIBILITA:
        risorsa = portatori[kind][ref]
        for day, slot in celle:
            ResourceUnavailability.objects.create(
                resource=risorsa, day=day, slot=slot,
                level=ResourceUnavailability.Level(livello))

    if qualita:
        criteri_di_qualita()

    # Le quote di alleggerimento (ondata 6).
    for _nome, famiglia, ref, quante, params in QUOTE:
        RelaxationQuota.objects.create(
            family=RelaxationQuota.Family(famiglia), resource=per_abbr[ref],
            max_violations=quante, params=params)

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
        "tecnico": tecnico, "carrelli": carrelli,
        "year": year, "period": period, "schedule": schedule,
    }
