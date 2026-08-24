"""Il generatore a testimone.

Per ogni famiglia: si genera **prima** un orario valido a caso, **poi** le
righe di vincolo che quell'orario soddisfa, e solo allora si chiede al solver
di trovarne uno da zero.

L'orario di partenza e' un testimone: prova che una soluzione esiste. Quindi
un INFEASIBLE e' un fallimento duro, e una soluzione qualsiasi dev'essere
pulita. Le due direzioni sono coperte da un test solo — e soprattutto un
builder vacuo (che postasse `1 == 0`, o che non postasse nulla) non puo'
passare: nel primo caso non trova il testimone, nel secondo lascia passare un
orario che il checker boccia.

Le maschere di settimana sono randomizzate insieme al resto, cosi' ogni
famiglia esercita piu' di una firma fin dal primo test. E' deliberato: il
difetto del D.T.B. del 2026-08-24 e' passato proprio perche' ogni banco di
prova aveva un'unica firma."""

import datetime as dt
import random
from collections import defaultdict
from dataclasses import dataclass, field

import pytest

from domain import weeks
from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.analysis.state import activity_tokens
from domain.models import (
    Activity, Break, Discipline, Holiday, Period, Placement, Schedule,
    SchoolClass, SchoolYear, StudyPlan, Subject, Teacher, TimeGrid, Service,
)
from domain.solver.model import apply, solve

N_WEEKS = 3
# le maschere disponibili: garantiscono almeno due firme di settimana distinte
MASKS = [weeks.full_mask(N_WEEKS), weeks.single_week(0),
         weeks.single_week(1) | weeks.single_week(2)]


@dataclass
class Witness:
    schedule: object
    env: dict
    placement: dict            # id attivita' → (giorno, fascia)
    tokens: dict               # id attivita' → frozenset di chiavi
    weeks_of: dict             # id attivita' → tuple di settimane attive
    activities: list
    rng: random.Random
    signatures: list = field(default_factory=list)

    def resource_days(self, key, week):
        """giorno → fasce occupate, per una chiave, in una settimana."""
        out = defaultdict(set)
        for aid, (day, slot) in self.placement.items():
            if key not in self.tokens[aid] or week not in self.weeks_of[aid]:
                continue
            for s in range(slot, slot + self.act(aid).duration_slots):
                out[day].add(s)
        return {d: sorted(s) for d, s in sorted(out.items())}

    def act(self, aid):
        return next(a for a in self.activities if a.id == aid)


def _school(rng):
    grid = TimeGrid.objects.create(
        days_per_cycle=rng.choice([3, 4, 5]),
        slots_per_day=rng.choice([4, 6]),
        slot_minutes=60,
        morning_end_slot=rng.choice([2, 3, 4]),
    )
    grid.morning_end_slot = min(grid.morning_end_slot, grid.slots_per_day)
    grid.save()
    # Un intervallo vero (Important 1, review Task 5): break_straddled non
    # puo' mai scattare a duration_slots=1 (Break.straddles richiede
    # start_slot < boundary_slot < start_slot + duration_slots, impossibile
    # fra interi con durata 1) — serve una durata >= 2 apposta, creata in
    # _make_activities.
    break_boundary = rng.randrange(1, grid.slots_per_day)
    Break.objects.create(grid=grid, boundary_slot=break_boundary)
    monday = dt.date(2026, 9, 14)
    year = SchoolYear.objects.create(
        start_date=monday, end_date=monday + dt.timedelta(days=7 * N_WEEKS - 1),
        first_week_monday=monday)
    # Un giorno festivo vero (Important 1, review Task 5): senza, il codice
    # "holiday" non puo' mai comparire e un terzo dei codici dichiarati da
    # structural:grid resta fisicamente irraggiungibile.
    holiday_week = rng.randrange(N_WEEKS)
    holiday_day = rng.randrange(grid.days_per_cycle)
    Holiday.objects.create(
        school_year=year,
        date=monday + dt.timedelta(days=7 * holiday_week + holiday_day))
    period = Period.objects.create(
        school_year=year, name="P1",
        start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subjects = [
        Subject.objects.create(code=c, name=c.title(), discipline=disc)
        for c in ("ITA", "MAT", "STO")
    ]
    # Un piano di studi per classe, non condiviso (Important 3, review Task
    # 5): con un solo piano i class_minutes di Service si sommano sulle
    # attivita' di **entrambe** le classi, mentre il monte ore effettivo e'
    # per singola classe — la fixture diventava strutturalmente incoerente.
    plans = [StudyPlan.objects.create(code=f"P1-{n}", name=f"Piano {n}", year=1)
             for n in ("1A", "1B")]
    classes = [SchoolClass.objects.create(name=n, study_plan=plan, year=1)
               for n, plan in zip(("1A", "1B"), plans)]
    teachers = [Teacher.objects.create(name=f"Doc {i}", last_name=f"D{i}",
                                       first_name=str(i))
                for i in range(4)]
    return {"grid": grid, "year": year, "period": period, "schedule": schedule,
            "discipline": disc, "subjects": subjects, "plans": plans,
            "classes": classes, "teachers": teachers,
            "break_boundary": break_boundary,
            "holiday": (holiday_week, holiday_day)}


def _make_activities(rng, env):
    """Per ogni classe, attivita' fino al 50% della capienza della griglia:
    il margine serve a rendere il piazzamento casuale quasi sempre possibile
    al primo tentativo. La prima attivita' di ogni classe attraversa
    l'intervallo (duration_slots=2, respects_breaks=True): e' l'unica forma
    capace di far scattare break_straddled se GridBuilder fosse vacuo
    (Important 1, review Task 5)."""
    grid = env["grid"]
    capienza = grid.days_per_cycle * grid.slots_per_day
    out = []
    for klass in env["classes"]:
        n = max(2, capienza // 2)
        for i in range(n):
            subject = rng.choice(env["subjects"])
            sensibile = (i == 0)
            duration_slots = 2 if sensibile else 1
            act = Activity.objects.create(
                subject=subject, duration_slots=duration_slots,
                duration_minutes=duration_slots * 60,
                week_mask=rng.choice(MASKS), respects_breaks=sensibile)
            act.teachers.add(rng.choice(env["teachers"]))
            act.classes.add(klass)
            service, _ = Service.objects.get_or_create(
                study_plan=klass.study_plan, subject=subject,
                defaults={"class_minutes": 0})
            service.class_minutes += duration_slots * 60
            service.save()
            out.append(act)
    return out


def _try_place(rng, activities, tokens, weeks_of, grid, holiday, break_boundary):
    """Un orario valido a caso: nessuna chiave occupata due volte nella stessa
    cella **nella stessa settimana**. Due attivita' di settimane disgiunte
    possono condividere la cella — e' esattamente la proprieta' che il modello
    deve rispettare, quindi il testimone deve poterla esibire.

    Esclude anche le celle che GridBuilder.restrict escluderebbe: il giorno
    festivo per le settimane in cui l'attivita' e' attiva, le celle a
    cavallo dell'intervallo per le attivita' con respects_breaks — stessa
    lettura del builder (domain/solver/builders/grid.py), cosi' il testimone
    rispetta la griglia per costruzione invece che per fortuna (Important 1,
    review Task 5)."""
    holiday_week, holiday_day = holiday
    busy, out = set(), {}
    ordine = list(activities)
    rng.shuffle(ordine)
    for act in ordine:
        vieta_festivo = holiday_week in weeks_of[act.id]
        celle = [(d, s) for d in range(grid.days_per_cycle)
                 for s in range(grid.slots_per_day - act.duration_slots + 1)
                 if not (vieta_festivo and d == holiday_day)
                 and not (act.respects_breaks
                          and s < break_boundary < s + act.duration_slots)]
        rng.shuffle(celle)
        for (day, slot) in celle:
            fasce = range(slot, slot + act.duration_slots)
            occupa = [(w, k, day, t) for w in weeks_of[act.id]
                      for k in tokens[act.id] for t in fasce]
            if any(cell in busy for cell in occupa):
                continue
            busy.update(occupa)
            out[act.id] = (day, slot)
            break
        else:
            return None
    return out


def build_witness(seed, tentativi=20):
    rng = random.Random(seed)
    env = _school(rng)
    activities = _make_activities(rng, env)
    tokens = {a.id: activity_tokens(a)[0] for a in activities}
    weeks_of = {a.id: tuple(w for w in range(N_WEEKS)
                            if weeks.week_in_mask(a.week_mask, w))
                for a in activities}
    for _ in range(tentativi):
        placement = _try_place(rng, activities, tokens, weeks_of, env["grid"],
                               env["holiday"], env["break_boundary"])
        if placement is not None:
            break
    else:
        raise AssertionError(
            f"nessun orario valido dopo {tentativi} tentativi (seed {seed}): "
            "la fixture e' troppo densa, non il solver troppo debole")
    for aid, (day, slot) in placement.items():
        Placement.objects.create(schedule=env["schedule"], activity_id=aid,
                                 day=day, start_slot=slot)
    w = Witness(schedule=env["schedule"], env=env, placement=placement,
                tokens=tokens, weeks_of=weeks_of, activities=activities, rng=rng)
    w.signatures = week_signatures(env["schedule"])
    return w


# --- il registro dei derivatori -----------------------------------------

@dataclass(frozen=True)
class Deriver:
    fn: object
    codes: frozenset


DERIVERS = {}


def deriver(key, codes):
    """Registra il derivatore di una famiglia. `codes` sono le causali che
    quella famiglia puo' emettere: sono cio' che il test controlla.

    Convenzione per gli undici derivatori successivi (Important 2, review
    Task 5): la funzione registrata restituisce un intero, il **potere
    vincolante** del seed corrente — quante righe/condizioni ha davvero
    creato, capaci di essere violate se il builder fosse vacuo. Zero
    significa derivazione vacua per quel seed: `run_family` la salta con
    `pytest.skip` invece di lasciarla passare come un successo travestito
    (era il bug: una riga creata ma matematicamente impossibile da violare
    contava come test verde). Le famiglie strutturali che non creano righe
    ma sono rese non vacue dalla fixture stessa (griglia, occupazione)
    restituiscono una costante positiva."""
    def wrap(fn):
        DERIVERS[key] = Deriver(fn, frozenset(codes))
        return fn
    return wrap


def _hard(schedule, codes):
    # Collassato per chiave (non per (chiave, settimana) come violazioni() in
    # test_solver_oracle.py) perche' qui basta: run_family confronta sempre
    # con l'insieme vuoto, prima e dopo — se una violazione esiste anche in
    # una sola settimana, la sua chiave compare comunque, quindi l'espansione
    # per settimana non aggiungerebbe potere diagnostico. Serve solo per il
    # confronto differenziale con una baseline non vuota (vedi violazioni()
    # in tests/test_solver_oracle.py) — non e' il caso qui. Non copiare
    # questo helper in un contesto differenziale: e' esattamente l'errore
    # corretto il 2026-08-24 (voce di changelog).
    return {f.key for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codes}


def run_family(key, seed):
    """Il test completo di una famiglia. Fallisce in tre modi distinti (o si
    salta se la derivazione e' vacua per questo seed), e ciascuno dice una
    cosa diversa."""
    assert key in DERIVERS, f"nessun derivatore per {key}"
    d = DERIVERS[key]
    w = build_witness(seed)
    potere = d.fn(w)
    if not potere:
        pytest.skip(
            f"{key}: derivazione vacua per il seed {seed}, nessuna "
            "condizione da violare in questo testimone")

    # 1. il testimone dev'essere valido: se non lo e', e' il derivatore a
    #    essere sbagliato, non il builder
    prima = _hard(w.schedule, d.codes)
    assert prima == set(), (
        f"il testimone stesso viola {key} (seed {seed}): {sorted(prima)}")

    # 2. c'era un testimone, quindi INFEASIBLE e' un fallimento duro:
    #    il builder e' piu' stretto di quanto la spec consenta
    Placement.objects.filter(schedule=w.schedule).delete()
    soluzione = solve(w.schedule, time_limit=60)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), (
        f"{key} INFEASIBLE con un testimone disponibile (seed {seed}): "
        f"{soluzione.stats}")

    # 3. e qualunque soluzione restituisca dev'essere pulita
    apply(soluzione, w.schedule)
    dopo = _hard(w.schedule, d.codes)
    assert dopo == set(), (
        f"{key} accetta un piazzamento che il checker boccia (seed {seed}): "
        f"{sorted(dopo)}")
    return w


from domain.models import ResourceTimeConstraint, ResourceUnavailability, SubjectConstraint

RT = ResourceTimeConstraint.Type
ST = SubjectConstraint.Type


@deriver("structural:grid", {"slot_out_of_grid", "break_straddled", "holiday"})
def _derive_grid(w):
    """Nessuna riga da creare: il testimone rispetta la griglia per
    costruzione — _try_place esclude gia' il giorno festivo e le celle a
    cavallo dell'intervallo per le attivita' sensibili create da
    _make_activities (Important 1, review Task 5). Il derivatore esiste
    comunque, perche' il test di copertura non ammette famiglie senza banco
    di prova. Non vacuo per costruzione della fixture (non per il seed):
    restituisce una costante positiva, non un conteggio di righe — non ce ne
    sono da creare."""
    return 1


@deriver("structural:occupation", {"resource_occupied", "resource_occupied_locked",
                                   "resource_peak"})
def _derive_occupation(w):
    """Idem: _try_place non produce doppie occupazioni. Il valore del test sta
    tutto nel punto 2 di run_family — il solver deve **ritrovare** un orario
    senza conflitti, e con piu' firme di settimana in gioco. Non vacuo per
    costruzione: ogni testimone ha attivita' da ricollocare."""
    return 1


@deriver("structural:unavailability", {"unavailability"})
def _derive_unavailability(w):
    """Dichiara indisponibili alcune celle che il testimone **non** usa, su un
    docente scelto a caso. Ricorrenti (senza data), cosi' non alterano le
    firme. Restituisce quante righe ha creato: zero se il docente scelto non
    ha celle libere per questo seed, e run_family salta il caso invece di
    spacciarlo per un successo (Important 2, review Task 5)."""
    docente = w.rng.choice(w.env["teachers"])
    grid = w.env["grid"]
    usate = {(day, s) for aid, (day, slot) in w.placement.items()
             if docente.pk in w.tokens[aid]
             for s in range(slot, slot + w.act(aid).duration_slots)}
    libere = [(d, s) for d in range(grid.days_per_cycle)
              for s in range(grid.slots_per_day) if (d, s) not in usate]
    scelte = w.rng.sample(libere, min(3, len(libere)))
    for (day, slot) in scelte:
        ResourceUnavailability.objects.create(
            resource=docente, day=day, slot=slot, level="hard")
    return len(scelte)


@deriver(RT.MAX_GAP_HOURS, {"max_gap"})
def _derive_max_gap(w):
    """Il budget settimanale osservato nel testimone, per la firma peggiore.
    Con l'uguaglianza il vincolo e' soddisfatto e stretto: se il builder
    contasse i buchi anche solo di un minuto in piu', sforerebbe. Crea sempre
    una riga: anche a budget zero e' un vincolo vero, perche' qualunque buco
    lo violerebbe."""
    grid = w.env["grid"]
    klass = w.rng.choice(w.env["classes"])
    peggiore = 0
    for rep, _ in w.signatures:
        totale = 0
        for _day, fasce in w.resource_days(klass.pk, rep).items():
            for meta in ([f for f in fasce if f < grid.morning_end_slot],
                         [f for f in fasce if f >= grid.morning_end_slot]):
                if len(meta) >= 2:
                    totale += (meta[-1] - meta[0] + 1 - len(meta)) * grid.slot_minutes
        peggiore = max(peggiore, totale)
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MAX_GAP_HOURS,
        params={"max_gap_minutes": peggiore})
    return 1


@deriver(RT.MAX_HOURS, {"max_hours_day", "max_hours_morning", "max_hours_afternoon"})
def _derive_max_hours(w):
    """I tetti osservati nel testimone, per la firma peggiore. Con
    l'uguaglianza il vincolo e' soddisfatto e stretto. Crea sempre una riga
    e non e' mai vacua: ogni classe della fixture ha almeno due attivita'
    piazzate (_make_activities), quindi il picco di day_minutes e' sempre
    positivo su almeno una firma."""
    grid = w.env["grid"]
    klass = w.rng.choice(w.env["classes"])
    picchi = {"day_minutes": 0, "morning_minutes": 0, "afternoon_minutes": 0}
    for rep, _ in w.signatures:
        for _day, fasce in w.resource_days(klass.pk, rep).items():
            mattina = [f for f in fasce if f < grid.morning_end_slot]
            sera = [f for f in fasce if f >= grid.morning_end_slot]
            picchi["day_minutes"] = max(picchi["day_minutes"], len(fasce))
            picchi["morning_minutes"] = max(picchi["morning_minutes"], len(mattina))
            picchi["afternoon_minutes"] = max(picchi["afternoon_minutes"], len(sera))
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MAX_HOURS,
        params={k: v * grid.slot_minutes for k, v in picchi.items()})
    return 1


@deriver(RT.MAX_HALF_DAYS, {"max_half_days", "only_half_day"})
def _derive_max_half_days(w):
    """Il numero di mezze giornate lavorate dal docente scelto, per la firma
    peggiore. Vacua (ritorna 0) se il docente scelto a caso non compare in
    nessuna attivita' del testimone: in quel caso il vincolo, per quanto
    creato, non tocca mai una cella e ResourceBuilder non lo posta — non
    c'e' nulla da violare (Important 2, review Task 5, stessa convenzione di
    _derive_unavailability)."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    peggiore = 0
    for rep, _ in w.signatures:
        lavorate = 0
        for _day, fasce in w.resource_days(docente.pk, rep).items():
            lavorate += any(f < grid.morning_end_slot for f in fasce)
            lavorate += any(f >= grid.morning_end_slot for f in fasce)
        peggiore = max(peggiore, lavorate)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.MAX_HALF_DAYS,
        params={"max_half_days": peggiore})
    return 1 if peggiore > 0 else 0


@deriver(ST.SAME_DAY_INCOMPATIBLE, {"subject_same_day"})
def _derive_same_day(w):
    """Crea una riga per ogni coppia (classe, materia) del testimone con
    almeno due occorrenze totali e mai piu' di una nello stesso giorno: sotto
    due occorrenze totali il vincolo sarebbe soddisfatto per costruzione e
    non violabile — una terza forma di vacuita' scovata in review, distinta
    dal "nessuna coppia trovata" gia' gestito. Non si ferma alla prima
    coppia che qualifica: continua per sommare piu' potere vincolante
    possibile (Important 2, review Task 5). Restituisce il numero di righe
    create: zero se nessuna coppia qualifica per questo seed."""
    creata = 0
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            per_giorno = defaultdict(int)
            for aid, (day, _slot) in w.placement.items():
                if klass.pk in w.tokens[aid] and w.act(aid).subject_id == subject.pk:
                    per_giorno[day] += 1
            if not per_giorno or max(per_giorno.values()) != 1:
                continue
            if sum(per_giorno.values()) < 2:
                continue
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=ST.SAME_DAY_INCOMPATIBLE)
            creata += 1
    return creata
