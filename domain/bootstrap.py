"""`Ricava`: da una griglia piatta a una **proposta**.

Il primo gradino della via d'ingresso decisa in [ADR-028]: l'orario che la
scuola ha già mandato è il dato migliore che abbiamo su di lei, e una riga di
quella griglia — *docente, giorno, fascia, classe, materia* — è la forma in cui
ce l'ha già Aurora (`ScheduleEntry`).

🔑 **Una cattedra si legge; un quadro orario si indovina.** Aggregare la
griglia per `(docente, classe, materia)` restituisce le cattedre quasi esatte
(139 chiavi su 142 sull'Alighieri). Aggregarla per `(classe, materia)` no, e
non per un difetto di questo codice: **scendere perde, risalire inventa**, e
inventa sempre *per eccesso*, perché due mezze classi che fanno la stessa ora
insieme nella griglia sono due ore.

Da qui le due regole di questo modulo.

**Prima: si contano le celle, non le lezioni.** Le ore che un *alunno* segue
sono le fasce distinte in cui la sua classe ha quella materia — una cella
occupata da due lezioni resta un'ora sola, perché lui ne frequenta una.
Misurato sull'Alighieri: contando le lezioni i quadri esatti sono **6 su 12**,
contando le celle **8 su 12**. La differenza sono esattamente le classi
sdoppiate.

**Seconda: ciò che non si vede si dichiara.** I quattro quadri che restano
storti sono quattro **meccanismi diversi**, tutti invisibili a una griglia
settimanale, e nessuno di essi è un caso patologico:

- il **turno di laboratorio** (3A e 4A): le due metà le prende lo stesso
  docente, quindi non sono mai simultanee e non c'è nessuna collisione da
  vedere. *Sdoppiare non è allineare*, ed è la stessa distinzione che L5 ha
  dovuto imparare sul dataset.
- l'**ora quindicinale** (5B): una griglia settimanale non ha un asse su cui
  dire «a settimane alterne».
- la **classe articolata** (2C): riceve una materia che il suo piano non porta,
  e senza il piano non c'è niente contro cui accorgersene.

Perciò `ricava` restituisce una **`Proposta`**, e non scrive. È la disciplina
del giudice dell'import di Aurora — `analyze` propone, l'utente vede, `import`
scrive — e qui serve di più che là: un descrittore sbagliato produce un orario
visibilmente storto, un quadro orario gonfiato produce un `INFEASIBLE` muto.

⚠ **Questo file non importa Django**, apposta. L'ingresso sono righe, l'uscita
è una proposta, e chi la scrive è `applica()` in fondo — l'unica funzione che
tocca l'ORM.
"""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lezione:
    """Una riga della griglia piatta: la forma di `ScheduleEntry`.

    `subject` è facoltativa perché lo è nella griglia di Aurora (e nel
    descrittore d'import, dove la materia è l'unico dei cinque ruoli non
    obbligatorio). Una lezione senza materia entra nel conteggio del docente e
    non in quello del quadro orario: si sa che qualcuno insegna, non cosa.
    """

    teacher: str
    day: int
    slot: int
    school_class: str
    subject: str | None = None


@dataclass(frozen=True)
class Sdoppiamento:
    """Una `(classe, materia)` vista **due volte nella stessa fascia**.

    È il gradino 2 di ADR-028 in forma di sospetto invece che di domanda: dove
    la collisione c'è, la scuola non deve dichiarare niente.

    🔑 **Il numero è giusto anche quando il nome è sbagliato.** Due docenti
    nella stessa cella sulla stessa classe possono essere due mezze classi
    *oppure* una **compresenza** — due insegnanti sulla classe intera. Le due
    cose sono diverse e questa griglia non le distingue, ma il quadro orario
    non se ne accorge: in tutt'e due i casi l'alunno fa **un'ora**. L'incertezza
    è sull'etichetta, non sul conto, e va sciolta da chi guarda — insieme alla
    partizione, che comunque va dichiarata a mano.

    ⚠ Il rilevatore è **sicuro ma non completo**, e le due metà della frase
    sono misurate. Sicuro: zero falsi allarmi su due dataset, e sul Fermi —
    che di partizioni non ne ha nessuna — zero sospetti. Non completo: 28
    coppie trovate su 30, e le due mancate sono il turno di laboratorio, che
    per costruzione non collide.
    """

    school_class: str
    subject: str | None
    cells: tuple
    streams: int  # il massimo di lezioni simultanee visto in una di quelle celle


@dataclass(frozen=True)
class Raggruppamento:
    """Un docente in **due classi nella stessa fascia**.

    È lo specchio dello sdoppiamento, e non è un errore del file: è il
    raggruppamento trasversale di ADR-013, dove un corso raccoglie alunni di
    classi diverse. La griglia lo registra come due righe, una per classe.

    ⚠ Non lo si distingue dalla **classe dal nome composto** (`3B/5O`), che è
    la stessa cosa scritta in un modo che Aurora già capisce. La differenza è
    di notazione, non di orario, e la scioglie chi guarda.
    """

    teacher: str
    subject: str | None
    classes: tuple
    cells: tuple


#: I meccanismi che gonfiano un quadro orario **senza lasciare traccia** nella
#: griglia. Non è un elenco di casi rari: sono tre strutture ordinarie di una
#: scuola italiana, e una proposta che non le nominasse mentirebbe per omissione.
CECITA = (
    ("turno_di_laboratorio",
     "Le due metà di una classe fanno l'ora a turno, con lo stesso docente: "
     "non essendo mai simultanee non collidono, e la griglia le conta tutte."),
    ("ora_quindicinale",
     "Un'ora a settimane alterne occupa una fascia settimanale come una piena: "
     "una griglia senza asse delle settimane non può dire il contrario."),
    ("classe_articolata",
     "Una classe segue una materia che il suo piano non porta. Senza il piano "
     "non c'è niente contro cui accorgersene — è il piano che si sta ricavando."),
)


@dataclass(frozen=True)
class Proposta:
    """Ciò che si ricava da una griglia, con dichiarato accanto ciò che non si
    ricava. Non è uno stato: è un referto."""

    teachers: tuple
    classes: tuple
    subjects: tuple
    days: int
    slots_per_day: int
    #: `(docente, classe, materia) → ore`. È la parte che **si legge**.
    assignments: dict
    #: `classe → {materia: ore}`, contando le **celle**. È la parte che si
    #: indovina, e `cecita` dice in che direzione può sbagliare.
    curriculum: dict
    splits: tuple = ()
    groupings: tuple = ()
    cecita: tuple = CECITA

    @property
    def uncertain_classes(self):
        """Le classi il cui quadro orario **non è affidabile**: quelle in cui
        una collisione è stata vista.

        ⚠ Non è l'insieme delle classi sbagliate — è l'insieme di quelle su cui
        *sappiamo* di aver corretto qualcosa. Le altre possono essere storte per
        uno dei tre motivi di `cecita`, e non c'è modo di saperlo da qui.
        """
        return tuple(sorted({s.school_class for s in self.splits}))


def ricava(lezioni):
    """Da un iterabile di `Lezione` a una `Proposta`. Non scrive niente."""
    # ⚠ **Le righe identiche si fondono**, e non è pulizia generica: due righe
    # uguali dicono la stessa cosa due volte, e una classe non può avere lo
    # stesso docente sulla stessa materia due volte nella stessa fascia. Senza
    # questo, un file che ripete una lezione — cosa che i file veri fanno —
    # regalerebbe un'ora a una cattedra **e** sembrerebbe uno sdoppiamento,
    # cioè romperebbe proprio la proprietà su cui il rilevatore poggia.
    righe = dict.fromkeys(lezioni)

    per_cella = defaultdict(list)   # (classe, giorno, fascia) → [(doc, materia)]
    per_docente = defaultdict(list)  # (docente, giorno, fascia) → [(classe, materia)]
    cattedre = defaultdict(int)
    celle_materia = defaultdict(set)  # (classe, materia) → {(giorno, fascia)}
    docenti, classi, materie = set(), set(), set()
    giorni, fasce = 0, 0

    for l in righe:
        docenti.add(l.teacher)
        classi.add(l.school_class)
        if l.subject is not None:
            materie.add(l.subject)
        giorni = max(giorni, l.day + 1)
        fasce = max(fasce, l.slot + 1)
        per_cella[(l.school_class, l.day, l.slot)].append((l.teacher, l.subject))
        per_docente[(l.teacher, l.day, l.slot)].append((l.school_class, l.subject))
        # ⚠ La cattedra conta le **righe**, non le celle, e non è una svista:
        # è il servizio del docente. Chi tiene mezza classe per tre ore ne ha
        # fatte tre, e l'altra metà le ha fatte qualcun altro. Dopo la fusione
        # qui sopra le due misure coincidono dentro una chiave `(docente,
        # classe, materia)`, ed è quella fusione a renderlo vero.
        cattedre[(l.teacher, l.school_class, l.subject)] += 1
        celle_materia[(l.school_class, l.subject)].add((l.day, l.slot))

    quadro = defaultdict(dict)
    for (classe, materia), celle in celle_materia.items():
        if materia is not None:
            quadro[classe][materia] = len(celle)

    splits = _sdoppiamenti(per_cella)
    groupings = _raggruppamenti(per_docente)
    return Proposta(
        teachers=tuple(sorted(docenti)),
        classes=tuple(sorted(classi)),
        subjects=tuple(sorted(materie)),
        days=giorni,
        slots_per_day=fasce,
        assignments=dict(cattedre),
        curriculum={k: dict(v) for k, v in quadro.items()},
        splits=splits,
        groupings=groupings,
    )


def _sdoppiamenti(per_cella):
    """Le `(classe, materia)` viste più di una volta nella stessa fascia."""
    celle = defaultdict(set)
    flussi = defaultdict(int)
    for (classe, giorno, fascia), lezioni in per_cella.items():
        if len(lezioni) < 2:
            continue
        for _doc, materia in lezioni:
            chiave = (classe, materia)
            celle[chiave].add((giorno, fascia))
            flussi[chiave] = max(flussi[chiave], len(lezioni))
    return tuple(
        Sdoppiamento(school_class=c, subject=m,
                     cells=tuple(sorted(celle[(c, m)])), streams=flussi[(c, m)])
        for c, m in sorted(celle, key=lambda k: (k[0], k[1] or "")))


def _raggruppamenti(per_docente):
    """I docenti visti in più classi nella stessa fascia."""
    classi = defaultdict(set)
    celle = defaultdict(set)
    for (docente, giorno, fascia), lezioni in per_docente.items():
        nomi = {c for c, _m in lezioni}
        if len(nomi) < 2:
            continue
        for _classe, materia in lezioni:
            chiave = (docente, materia)
            classi[chiave] |= nomi
            celle[chiave].add((giorno, fascia))
    return tuple(
        Raggruppamento(teacher=d, subject=m, classes=tuple(sorted(classi[(d, m)])),
                       cells=tuple(sorted(celle[(d, m)])))
        for d, m in sorted(classi, key=lambda k: (k[0], k[1] or "")))


# --- Da qui in giù si tocca l'ORM. -------------------------------------------

#: La disciplina che `applica` inventa. ⚠ È l'unico dato che questo modulo si
#: **inventa** invece di ricavarlo, e lo fa perché `Subject.discipline` è
#: obbligatoria e la griglia non ne parla. Il codice è quello che è apposta: va
#: guardato. La disciplina è una tabella che le scuole personalizzano
#: (ADR-001), e assegnarla è un lavoro umano, non un'inferenza.
DISCIPLINA_DA_ASSEGNARE = ("ND", "Da assegnare")


def _codice(nome, presi, massimo=10):
    """Un codice corto, unico e riconoscibile. Le collisioni si numerano."""
    base = "".join(ch for ch in nome.upper() if ch.isalnum())[:massimo] or "X"
    if base not in presi:
        presi.add(base)
        return base
    for n in range(2, 1000):
        suffisso = str(n)
        cand = base[:massimo - len(suffisso)] + suffisso
        if cand not in presi:
            presi.add(cand)
            return cand
    raise ValueError(f"non riesco a dare un codice a {nome!r}")


def _anno(nome_classe):
    """L'anno di corso dal nome della classe: `3B` → 3.

    ⚠ È una convenzione italiana, non un dato della griglia. Dove non si legge
    si mette 1, che è visibilmente sbagliato invece che plausibilmente sbagliato.
    """
    cifre = "".join(ch for ch in nome_classe if ch.isdigit())
    return int(cifre[0]) if cifre else 1


def applica(proposta, *, slot_minutes=60, morning_end_slot=None, replace=False):
    """Scrive la proposta: anagrafica, griglia, piani, quadri orari, cattedre.

    ⚠ **Non scrive tre cose, e ognuna per un motivo diverso.**

    - Le **partizioni**: `ricava` sa *che* una classe si sdoppia, non *chi* sta
      in quale metà, e quella è anagrafica di alunni che nessuna griglia porta.
      I sospetti restano su `proposta.splits`, da confermare.
    - Le **attività**: nascono dalla ripartizione, non da qui.
    - Il **calendario** (`SchoolYear`, `Period`, `Schedule`): sono date, e una
      griglia settimanale non ne ha.

    `replace=False` **rifiuta** su un database già popolato invece di
    raddoppiarlo: applicare due volte la stessa proposta non è un'operazione
    innocua, ed è l'errore che si fa per primo.
    """
    from django.db import transaction

    from .models import (Discipline, InstituteSettings, SchoolClass, StudyPlan,
                         Service, Subject, Teacher, TeachingAssignment, TimeGrid)

    if not proposta.classes:
        # Una griglia senza righe darebbe `days_per_cycle = 0`, che non è una
        # griglia povera ma una non-griglia. Meglio fermarsi qui che scrivere
        # un istituto in cui la settimana non esiste.
        raise ValueError("la proposta è vuota: non c'è nessuna griglia da scrivere")

    esistenti = {m.__name__: m.objects.count() for m in
                 (Teacher, SchoolClass, Subject, StudyPlan, Service,
                  TeachingAssignment, TimeGrid, Discipline)}
    pieno = {k: v for k, v in esistenti.items() if v}
    if pieno and not replace:
        raise ValueError(
            f"il database non è vuoto ({pieno}); applicare qui raddoppierebbe "
            f"i dati. Passa replace=True se è ciò che vuoi.")

    with transaction.atomic():
        if replace:
            # ⚠ L'ordine è quello che `PROTECT` impone: `Subject` prima
            # di `Discipline`, `SchoolClass` prima di `StudyPlan`. Dimenticare
            # la disciplina faceva fallire la **seconda** applicazione sul
            # codice unico, ed è il difetto che il test di `replace` ha trovato.
            for m in (TeachingAssignment, Service, SchoolClass, StudyPlan,
                      Subject, Discipline, Teacher, TimeGrid):
                m.objects.all().delete()

        InstituteSettings.load()
        griglia = TimeGrid.objects.create(
            days_per_cycle=proposta.days,
            slots_per_day=proposta.slots_per_day,
            slot_minutes=slot_minutes,
            # ⚠ Senza una linea dichiarata la giornata è **tutta mattina**. Non
            # è neutro: la linea è il perimetro su cui si misura un buco (L1) e
            # la soglia delle mezze giornate libere (L8). Meglio un valore che
            # si vede che uno che sembra scelto.
            morning_end_slot=(proposta.slots_per_day if morning_end_slot is None
                              else morning_end_slot))

        codice, nome = DISCIPLINA_DA_ASSEGNARE
        disciplina = Discipline.objects.create(code=codice, name=nome)

        # Il codice della disciplina si mette fra i presi anche se sta in
        # un'altra tabella: una materia e una disciplina omonime sarebbero
        # legali e illeggibili.
        presi = {codice}
        materie = {n: Subject.objects.create(code=_codice(n, presi), name=n,
                                             discipline=disciplina)
                   for n in proposta.subjects}
        docenti = {n: Teacher.objects.create(name=n, last_name=n[:50], first_name="")
                   for n in proposta.teachers}

        presi_piani = set()
        classi = {}
        for n in proposta.classes:
            # ⚠ **Un piano per classe, e non un piano per profilo.** Raggruppare
            # le classi che hanno lo stesso quadro orario sembra la cosa
            # economica ed è una perdita: sull'Alighieri i profili distinti sono
            # **9 contro 11 piani**, cioè due coppie si fondono. Due indirizzi
            # che quest'anno coincidono restano due indirizzi, e fonderli è una
            # decisione della scuola — che da un piano per classe la può sempre
            # prendere, mentre dal contrario non si torna indietro.
            piano = StudyPlan.objects.create(
                code=_codice(n, presi_piani), name=f"Piano di {n}", year=_anno(n))
            classi[n] = SchoolClass.objects.create(
                name=n, study_plan=piano, year=_anno(n))
            for materia, ore in sorted(proposta.curriculum.get(n, {}).items()):
                Service.objects.create(study_plan=piano, subject=materie[materia],
                                       class_minutes=ore * slot_minutes)

        for (docente, classe, materia), ore in sorted(proposta.assignments.items()):
            if materia is None:
                # Una lezione senza materia dice che qualcuno insegna, non cosa:
                # non c'è una cattedra da scriverne.
                continue
            TeachingAssignment.objects.create(
                teacher=docenti[docente], subject=materie[materia],
                school_class=classi[classe], weekly_minutes=ore * slot_minutes)

    return {"grid": griglia, "teachers": docenti, "classes": classi,
            "subjects": materie, "discipline": disciplina}
