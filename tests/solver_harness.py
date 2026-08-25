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
    SchoolClass, SchoolYear, Site, StudyPlan, Subject, Teacher, TimeGrid,
    Service,
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
    # Le sedi (Task 9): create sempre, cosi' _sedi(ctx) ne vede almeno due
    # appena qualche attivita' ha una sede nota (_make_activities le assegna
    # a meta').
    sites = [Site.objects.create(name=n) for n in ("Centrale", "Succursale")]
    return {"grid": grid, "year": year, "period": period, "schedule": schedule,
            "discipline": disc, "subjects": subjects, "plans": plans,
            "classes": classes, "teachers": teachers, "sites": sites,
            "break_boundary": break_boundary,
            "holiday": (holiday_week, holiday_day)}


def _make_activities(rng, env, seed=0):
    """Per ogni classe, attivita' fino al 50% della capienza della griglia:
    il margine serve a rendere il piazzamento casuale quasi sempre possibile
    al primo tentativo. La prima attivita' di ogni classe attraversa
    l'intervallo (duration_slots=2, respects_breaks=True): e' l'unica forma
    capace di far scattare break_straddled se GridBuilder fosse vacuo
    (Important 1, review Task 5)."""
    grid = env["grid"]
    # Flusso casuale separato per le sedi: pescare dal flusso principale
    # sposterebbe ogni estrazione successiva e cambierebbe il testimone di
    # tutti gli altri derivatori a parita' di seed.
    sedi_rng = random.Random(f"sedi-{seed}")
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
            if sedi_rng.random() < 0.5:
                act.site = sedi_rng.choice(env["sites"])
                act.save()
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
    activities = _make_activities(rng, env, seed)
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


from domain.models import (
    ClassPart, InstituteSettings, ResourceTimeConstraint,
    ResourceUnavailability, SubjectConstraint,
)
from domain.models.resources import Resource

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


def _collocazioni(w, aid):
    """Le fasce di **partenza** ammissibili per un'attivita' in un giorno
    qualunque: dentro la giornata, e senza scavalcare l'intervallo quando
    l'attivita' lo rispetta. Stessa regola di `_try_place`."""
    grid, act = w.env["grid"], w.act(aid)
    boundary = w.env["break_boundary"]
    return [s for s in range(grid.slots_per_day - act.duration_slots + 1)
            if not (act.respects_breaks
                    and s < boundary < s + act.duration_slots)]


def _ci_stanno(w, kind, a, b):
    """Due attivita' possono partire nello **stesso secchio**, sulla stessa
    unita' (quindi senza sovrapporsi), in un giorno qualunque?

    Enumerazione esaustiva delle coppie di fasce di partenza — al piu' 36
    combinazioni — invece di una formula chiusa. La formula chiusa e' stata
    provata e scartata due volte:

    1. `somma delle durate <= larghezza del secchio` **non e' necessaria**:
       il secchio si attribuisce alla fascia di **partenza** (regola in testa
       a domain/analysis/checkers/subject_constraints.py), quindi la seconda
       attivita' puo' *sconfinare* nel pomeriggio restando attribuita alla
       mattina. Escludeva righe violabili: su 250 seed ne escludeva 22, di
       cui **13 violabili**, e zero sui seed 1-5 — invisibile esattamente
       dove si guarda di solito (Ruling 48);
    2. la versione corretta di quella formula e' necessaria ma **troppo
       generosa**: non modella l'intervallo, e riammetteva il seed 2, dove la
       riga e' inviolabile per via di un `Break` con `respects_breaks`.

    L'enumerazione le copre entrambe, e resta una condizione **necessaria**:
    se le due attivita' non coesistono nemmeno da sole, a maggior ragione non
    coesistono con il resto dell'orario addosso. Non e' sufficiente — ignora
    le altre attivita', le indisponibilita' e i giorni festivi — ma sbagliare
    in questa direzione costa un caso di banco debole, mentre sbagliare
    nell'altra costa **copertura persa in silenzio**."""
    grid = w.env["grid"]
    da, db = w.act(a).duration_slots, w.act(b).duration_slots

    def secchio(s):
        return 0 if kind == "day" else s >= grid.morning_end_slot

    for sa in _collocazioni(w, a):
        for sb in _collocazioni(w, b):
            if sa + da > sb and sb + db > sa:
                continue          # si sovrappongono
            if secchio(sa) == secchio(sb):
                return True
    return False


def _coppia_violabile(w, kind, aids):
    """La riga su queste attivita' e' violabile **in linea di principio**?
    Serve una coppia che sia insieme:

    1. **co-attiva** in qualche firma di settimana — due attivita' con
       maschere disgiunte non compaiono mai nello stesso `ScheduleState`,
       quindi `len(la) > 1` e' irraggiungibile e la riga e' inviolabile
       (quarta forma di vacuita', Ruling 49: assente sui seed 1-5, presente
       dal seed 8 in poi);
    2. **collocabile** nello stesso secchio senza sovrapporsi, secondo
       `_ci_stanno` (che tiene conto anche degli intervalli).

    Copre anche il caso «meno di due attivita'», che era una guardia a se'
    (con meno di due il ciclo non produce nessuna coppia).

    ⚠ E' una condizione **necessaria per la violabilita', non sufficiente**:
    ignora le altre attivita' che occupano le fasce, le indisponibilita' e i
    giorni festivi. Una riga che la supera puo' comunque risultare
    inviolabile. Va bene cosi': una guardia troppo generosa costa un caso di
    banco debole, una troppo stretta costa **copertura persa in silenzio**,
    che e' molto peggio."""
    for i, a in enumerate(aids):
        for b in aids[i + 1:]:
            if not any(rep in w.weeks_of[a] and rep in w.weeks_of[b]
                       for rep, _ in w.signatures):
                continue
            if _ci_stanno(w, kind, a, b):
                return True
    return False


@deriver(ST.SAME_DAY_INCOMPATIBLE, {"subject_same_day"})
def _derive_same_day(w):
    """Crea una riga per ogni coppia (classe, materia) del testimone con
    almeno due occorrenze totali e mai piu' di una nello stesso giorno: sotto
    due occorrenze totali il vincolo sarebbe soddisfatto per costruzione e
    non violabile — una terza forma di vacuita' scovata in review, distinta
    dal "nessuna coppia trovata" gia' gestito. Non si ferma alla prima
    coppia che qualifica: continua per sommare piu' potere vincolante
    possibile (Important 2, review Task 5).

    Le altre due forme di vacuita' — la coppia dev'essere co-attiva in
    qualche firma di settimana, e le due attivita' devono starci nello stesso
    giorno — stanno in `_coppia_violabile` (Rulings 48-49, review Task 10).
    Sul secchio giornata nessuna delle due morde oggi: su 250 seed la
    condizione geometrica non esclude **mai** nulla, e le maschere disgiunte
    compaiono dal seed 8 in poi. Sono qui perche' il testimone cambiera'
    forma, e allora nessuno se ne accorgerebbe.

    Restituisce il numero di righe create: zero se nessuna coppia qualifica
    per questo seed."""
    creata = 0
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            aids = [aid for aid in w.placement
                    if klass.pk in w.tokens[aid]
                    and w.act(aid).subject_id == subject.pk]
            per_giorno = defaultdict(int)
            for aid in aids:
                per_giorno[w.placement[aid][0]] += 1
            if not per_giorno or max(per_giorno.values()) != 1:
                continue
            if not _coppia_violabile(w, "day", aids):
                continue
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=ST.SAME_DAY_INCOMPATIBLE)
            creata += 1
    return creata


@deriver(ST.SAME_HALF_DAY_INCOMPATIBLE, {"subject_same_half_day"})
def _derive_same_half_day(w):
    """Come _derive_same_day, sul secchio mezza giornata invece che giorno:
    scorre tutte le coppie (classe, materia), accumula invece di fermarsi
    alla prima. Stessa vacuita' aggiuntiva scovata in review sull'originale:
    sotto due occorrenze totali il vincolo e' soddisfatto per costruzione e
    non violabile — una riga creata ma matematicamente impossibile da
    violare.

    Le altre due forme di vacuita' stanno in `_coppia_violabile` (Rulings
    48-49): co-attivita' in qualche firma di settimana, e compatibilita'
    geometrica col secchio. Qui la seconda **morde davvero** — al seed 2 la
    famiglia salta per questo — mentre sul secchio giornata non e' mai
    scattata.

    ⚠ Limite strutturale della famiglia, non solo di questo derivatore: il
    secchio mezza giornata e' due volte piu' fine di quello giornata, quindi
    una soluzione qualsiasi lo soddisfa per caso piu' spesso, e il potere
    vincolante e' strutturalmente piu' basso di quello di SAME_DAY. I due
    numeri misurati stanno nel registro (Rulings 43-44), non qui: in
    docstring invecchierebbero in silenzio a ogni cambio del banco
    (Ruling 50).

    Restituisce il numero di righe create: zero se nessuna coppia qualifica
    per questo seed."""
    grid = w.env["grid"]
    creata = 0
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            aids = [aid for aid in w.placement
                    if klass.pk in w.tokens[aid]
                    and w.act(aid).subject_id == subject.pk]
            per_meta = defaultdict(int)
            for aid in aids:
                day, slot = w.placement[aid]
                per_meta[(day, slot >= grid.morning_end_slot)] += 1
            if not per_meta or max(per_meta.values()) != 1:
                continue
            if not _coppia_violabile(w, "half", aids):
                continue
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=ST.SAME_HALF_DAY_INCOMPATIBLE)
            creata += 1
    return creata


@deriver(ST.TWO_DAYS_INCOMPATIBLE, {"subject_two_days"})
def _derive_two_days(w):
    """Cerca, per ogni classe, una coppia di materie **entrambe presenti** nel
    testimone che non compaiano mai in giorni consecutivi. Scorre tutte le
    coppie, accumula invece di fermarsi alla prima.

    Due vacuita' oltre a "nessuna coppia trovata": una materia **assente**
    dalla classe da' `giorni[pk]` vuoto, e con `defaultdict(set)` l'assenza
    non si distingue dalla presenza non-consecutiva — `not any(...)` sarebbe
    banalmente vero pur non esistendoci nulla da violare, e nascerebbe una
    riga che nessun piazzamento puo' violare. E su un ciclo a un solo giorno
    non esiste alcun successore (`d + 1` esce sempre dalla settimana), quindi
    ogni riga sarebbe vacua per costruzione della griglia, non del
    testimone."""
    if w.env["grid"].days_per_cycle < 2:
        return 0
    creata = 0
    for klass in w.env["classes"]:
        giorni = defaultdict(set)
        for aid, (day, _slot) in w.placement.items():
            if klass.pk in w.tokens[aid]:
                giorni[w.act(aid).subject_id].add(day)
        for a in w.env["subjects"]:
            if not giorni[a.pk]:
                continue
            for b in w.env["subjects"]:
                if a.pk == b.pk or not giorni[b.pk]:
                    continue
                if any(d + 1 in giorni[b.pk] for d in giorni[a.pk]):
                    continue
                SubjectConstraint.objects.create(
                    subject_a=a, subject_b=b, school_class=klass,
                    type=ST.TWO_DAYS_INCOMPATIBLE)
                creata += 1
    return creata


def _massimo_pacchetto(opzioni):
    """Il massimo di minuti impacchettabile scegliendo, per ciascuna
    attivita' selezionata (una voce di `opzioni`), una delle sue fasce di
    partenza ammissibili — senza che due selezionate si sovrappongano.
    Ricerca esatta con memoizzazione su (indice, maschera di fasce
    occupate): lo spazio di stati e' piccolo per costruzione (al piu'
    `slots_per_day` fasce, poche attivita' per coppia (classe, materia)),
    quindi l'esaustivita' costa poco."""
    memo = {}

    def rec(i, mask):
        if i == len(opzioni):
            return 0
        chiave = (i, mask)
        if chiave in memo:
            return memo[chiave]
        minuti, durata, starts = opzioni[i]
        migliore = rec(i + 1, mask)   # non selezionare questa attivita'
        for s in starts:
            occ = ((1 << durata) - 1) << s
            if occ & mask:
                continue   # si sovrappone a una gia' selezionata
            migliore = max(migliore, minuti + rec(i + 1, mask | occ))
        memo[chiave] = migliore
        return migliore

    return rec(0, 0)


def _capienza_secchio(w, kind, rep, aids):
    """Il massimo di minuti che possono **partire** nello stesso secchio, in
    un giorno qualunque, senza sovrapporsi — fra le attivita' di `aids` che
    sono co-attive nella firma `rep`. Stessa forma di `_ci_stanno`:
    enumerazione esaustiva sulle collocazioni ammissibili di ciascuna
    attivita' (`_collocazioni`), non formula chiusa — la formula chiusa su
    questo branch e' stata provata e scartata due volte (Ruling 51).

    E' un **limite superiore esatto sulla sola geometria** (Ruling 63): non
    vede le altre attivita' che occupano le fasce (di altre materie o
    classi), le indisponibilita', le sedi, i giorni festivi. Un secchio che
    qui risulta riempibile oltre `param` puo' quindi risultare comunque
    inviolabile per via del resto del modello — stabilirlo richiede di
    chiedere al solver (Ruling 64, rimandato al Task 17 dalla Ruling 65). E'
    la direzione giusta in cui sbagliare: generosa, mai stretta — sbagliare
    per eccesso costa un caso di banco debole, sbagliare per difetto costa
    copertura persa in silenzio.

    ⚠ **Ma «generosa, mai stretta» ha due precondizioni, e sono proprieta'
    del testimone, non del dominio** (Important 2, ri-review Task 11).
    `_massimo_pacchetto` vieta la **sovrapposizione**, e questo e' un limite
    superiore vero solo finche':

    1. la capienza simultanea delle risorse vale 1 — il default di
       `Resource.simultaneous_capacity`, che l'harness non tocca mai. Con
       capienza cumulativa (`OccupationBuilder` la supporta, ed e' feature
       EDT documentata) due attivita' co-attive della stessa materia possono
       **condividere** la fascia e sommarsi entrambe nello stesso secchio;
    2. la classe non ha **partizioni**. Il checker prende
       `keys = {classe, *tutte le sue parti}` (`_unit_keys`,
       subject_constraints.py righe 17-24): due attivita' su parti diverse
       (sdoppiamento, `_REL`/`_ALT`) sono legittimamente simultanee e cadono
       **tutte e due** nella stessa somma di secchio.

    In entrambi i casi il massimo reale supera questa capienza, la guardia
    diventa **stretta**, e scarta righe violabili — cioe' esattamente il
    modo di sbagliare che il capoverso qui sopra dichiara di evitare. Oggi
    non morde (misurato: capienza 1 ovunque, zero partizioni nel testimone),
    ma il testimone cambiera' forma: le due condizioni sono asserite sotto,
    cosi' chi le rompe se ne accorge invece di perdere copertura in
    silenzio."""
    grid = w.env["grid"]
    # Le due precondizioni del capoverso qui sopra. Asserite invece che
    # sperate: se il testimone acquista capienza cumulativa o partizioni,
    # questa guardia smette di essere un limite superiore e comincia a
    # scartare righe violabili — un modo di sbagliare che non si vede dai
    # verdi, perche' si manifesta come copertura che non c'e' piu'.
    assert not Resource.objects.filter(simultaneous_capacity__gt=1).exists(), (
        "_capienza_secchio presuppone capienza simultanea 1: con risorse "
        "cumulative due attivita' possono condividere la fascia, e il "
        "massimo reale supera questo limite")
    assert not ClassPart.objects.exists(), (
        "_capienza_secchio presuppone classi senza partizioni: due attivita' "
        "su parti diverse sono simultanee e cadono entrambe nella stessa "
        "somma di secchio (_unit_keys)")

    def secchio(s):
        return 0 if kind == "day" else int(s >= grid.morning_end_slot)

    buckets = (0,) if kind == "day" else (0, 1)
    migliore = 0
    for b in buckets:
        opzioni = []
        for aid in aids:
            if rep not in w.weeks_of[aid]:
                continue
            starts = [s for s in _collocazioni(w, aid) if secchio(s) == b]
            if starts:
                opzioni.append((w.act(aid).duration_minutes,
                               w.act(aid).duration_slots, starts))
        migliore = max(migliore, _massimo_pacchetto(opzioni))
    return migliore


def _derive_max_hours_subject(w, tipo, kind):
    """Comune a MAX_HOURS_DAY e MAX_HOURS_HALF_DAY: per ogni coppia (classe,
    materia) del testimone, calcola `param` e verifica che la riga sia
    **violabile in linea di principio** prima di crearla — altrimenti nasce
    una riga che nessun piazzamento puo' violare (Ruling 54, misurata prima
    del dispatch: il piano, senza queste correzioni, produceva righe vacue
    su una minoranza consistente dei seed di prova).

    **Correzione 1 (Ruling 56): `param` per firma di settimana, non
    sull'unione.** `_try_place` permette a due attivita' di settimane
    disgiunte di condividere la cella, e il checker valuta uno `ScheduleState`
    **per firma** — sommare i minuti per secchio su tutti i piazzamenti,
    ignorando le maschere, produrrebbe un tetto piu' largo del necessario (il
    testimone lo rispetterebbe comunque, ma il vincolo sarebbe piu' debole di
    quanto la riga dovrebbe essere). Qui `param` e' il massimo, sulle firme,
    della somma massima per secchio **dentro quella firma**.

    **Correzione 2 (Ruling 55, sostituita dalla Ruling 63): guardia di
    riempimento per firma.** La prima versione usava due condizioni
    congiunte e indipendenti — il totale della coppia per firma supera
    `param`, e una coppia co-attiva "ci sta" nello stesso secchio
    (`_coppia_violabile`/`_ci_stanno`) — ma nessuna delle due guarda **quanto
    ci sta davvero in un secchio**: la review (Ruling 63) ha mostrato che sul
    secchio mezza giornata 4 righe su 20 restano inviolabili nonostante
    superino entrambe, perche' *ci sta una coppia* non implica *la somma
    raggiungibile supera il tetto* (potrebbero starci solo le due piu'
    corte). La sostituisce `_capienza_secchio`: per ogni firma, il massimo di
    minuti impacchettabile nello stesso secchio (non solo in coppie) senza
    sovrapposizioni. E' un limite superiore **esatto sulla geometria**, quindi
    **sussume entrambe le guardie precedenti**: se la capienza supera
    `param`, il totale della firma la supera per forza (la capienza e' un
    sottoinsieme del totale), e la capienza non puo' essere raggiunta da una
    sola attivita' (ogni attivita' compare gia' da sola nel proprio secchio
    della sua firma nel testimone, quindi il suo stesso `param` la domina per
    costruzione — vedi Ruling 69c) — servono sempre almeno due attivita', cioe'
    una coppia che ci sta. — **Decisione presa qui**: le due guardie vecchie
    sono **rimosse**, non tenute in parallelo: duplicarle avrebbe significato
    portare avanti una versione piu' debole della stessa idea, ed e'
    esattamente il tipo di ridondanza che questo modulo evita altrove (una
    primitiva per concetto).

    ⚠ **Il residuo non si chiude qui (Ruling 64).** `_capienza_secchio` vede
    la sola geometria: non le altre risorse, le indisponibilita', le sedi.
    Una riga la cui capienza supera `param` puo' quindi restare comunque
    inviolabile per un motivo che il derivatore non puo' vedere — misurato
    dal revisore: due delle quattro righe originariamente inviolabili lo
    erano per `structural:site_transition` (le attivita' che sommerebbero
    abbastanza minuti hanno sedi diverse, e non possono stare in fasce
    adiacenti), e restano inviolabili anche dopo questa guardia. Non e' un
    difetto di questa guardia: e' il limite dichiarato di un derivatore che
    non puo' reimplementare l'intero modello per sapere se una riga e'
    davvero raggiungibile — quello e' compito della sonda esatta valutata e
    **non adottata** qui (Ruling 65), rimandata al Task 17.

    **Correzione 3: accumula su tutte le coppie (classe, materia)**, non
    `return` alla prima — come i tre derivatori di SAME_DAY/SAME_HALF_DAY/
    TWO_DAYS qui sopra."""
    grid = w.env["grid"]
    creata = 0
    for klass in w.env["classes"]:
        for subject in w.env["subjects"]:
            aids = [aid for aid in w.placement
                    if klass.pk in w.tokens[aid]
                    and w.act(aid).subject_id == subject.pk]
            if not aids:
                continue
            param = 0
            for rep, _ in w.signatures:
                per_secchio = defaultdict(int)
                for aid in aids:
                    if rep not in w.weeks_of[aid]:
                        continue
                    day, slot = w.placement[aid]
                    secchio = (day if kind == "day"
                               else day * 2 + (slot >= grid.morning_end_slot))
                    per_secchio[secchio] += w.act(aid).duration_minutes
                if per_secchio:
                    param = max(param, max(per_secchio.values()))
            if param == 0:
                continue
            if not any(_capienza_secchio(w, kind, rep, aids) > param
                       for rep, _ in w.signatures):
                continue
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, school_class=klass,
                type=tipo, param=param)
            creata += 1
    return creata


@deriver(ST.MAX_HOURS_DAY, {"subject_max_hours_day"})
def _derive_max_hours_day(w):
    return _derive_max_hours_subject(w, ST.MAX_HOURS_DAY, "day")


@deriver(ST.MAX_HOURS_HALF_DAY, {"subject_max_hours_half_day"})
def _derive_max_hours_half_day(w):
    return _derive_max_hours_subject(w, ST.MAX_HOURS_HALF_DAY, "half")


def _adiacenza_raggiungibile(w, a, b):
    """Esiste una fascia di partenza ammissibile per `a` la cui fine e' anche
    una fascia di partenza ammissibile per `b`, nello stesso giorno?

    Condizione **necessaria, non sufficiente** per la violabilita' di
    FORBIDDEN_SEQUENCE su questa coppia — stessa forma di `_ci_stanno`:
    ignora le altre attivita', le indisponibilita' e i giorni festivi.
    Sbagliare per eccesso (dire raggiungibile quando in pratica non lo sara'
    mai, per via del resto dell'orario) costa un caso di banco debole;
    sbagliare per difetto costa copertura persa in silenzio — quindi qui, se
    proprio si deve sbagliare, si sbaglia per eccesso."""
    da = w.act(a).duration_slots
    ammissibili_b = set(_collocazioni(w, b))
    return any(sa + da in ammissibili_b for sa in _collocazioni(w, a))


def _coppia_adiacente_violabile(w, aids_a, aids_b):
    """Guardie 2 e 3 della Ruling 57: serve una coppia (attivita' di A,
    attivita' di B) che sia insieme **co-attiva** in qualche firma di
    settimana e **geometricamente raggiungibile** come sequenza
    (`_adiacenza_raggiungibile`). Stessa forma di `_coppia_violabile`, ma su
    due liste distinte invece che sulle coppie interne a una sola: qui la
    relazione e' orientata (A prima, B dopo), mai il contrario."""
    for a in aids_a:
        for b in aids_b:
            if not any(rep in w.weeks_of[a] and rep in w.weeks_of[b]
                       for rep, _ in w.signatures):
                continue
            if _adiacenza_raggiungibile(w, a, b):
                return True
    return False


@deriver(ST.FORBIDDEN_SEQUENCE, {"subject_forbidden_sequence"})
def _derive_forbidden_sequence(w):
    """Cerca, per ogni classe, una coppia **ordinata** di materie (A prima, B
    dopo) che nel testimone non compaia mai adiacente. Scorre tutte le
    coppie, accumula invece di fermarsi alla prima.

    **Tre guardie di violabilita' (Ruling 57)**, oltre a "mai adiacente nel
    testimone":

    1. **entrambe** le materie devono avere attivita' nella classe — la forma
       piu' cruda di vacuita' (seed 2 del banco, misurato prima del
       dispatch): con una materia **assente**, `_placed_of` nel checker
       restituisce la lista vuota e il ciclo non entra mai, quindi "mai
       adiacente" e' banalmente vero pur non esistendo nulla da violare;
    2. una coppia (attivita' di A, attivita' di B) dev'essere **co-attiva**
       in qualche firma di settimana;
    3. l'adiacenza dev'essere **geometricamente raggiungibile**
       (`_coppia_adiacente_violabile`, che riusa `_collocazioni` con le
       stesse regole di `_try_place` invece di riscriverle)."""
    creata = 0
    for klass in w.env["classes"]:
        per_materia = defaultdict(list)
        for aid in w.placement:
            if klass.pk in w.tokens[aid]:
                per_materia[w.act(aid).subject_id].append(aid)
        adiacenti = set()
        for aid, (day, slot) in w.placement.items():
            if klass.pk not in w.tokens[aid]:
                continue
            fine = slot + w.act(aid).duration_slots
            for altro, (day2, slot2) in w.placement.items():
                if (altro != aid and day2 == day and slot2 == fine
                        and klass.pk in w.tokens[altro]):
                    adiacenti.add((w.act(aid).subject_id, w.act(altro).subject_id))
        for a in w.env["subjects"]:
            aids_a = per_materia.get(a.pk, [])
            if not aids_a:
                continue
            for b in w.env["subjects"]:
                if a.pk == b.pk:
                    continue
                aids_b = per_materia.get(b.pk, [])
                if not aids_b:
                    continue
                if (a.pk, b.pk) in adiacenti:
                    continue
                if not _coppia_adiacente_violabile(w, aids_a, aids_b):
                    continue
                SubjectConstraint.objects.create(
                    subject_a=a, subject_b=b, school_class=klass,
                    type=ST.FORBIDDEN_SEQUENCE)
                creata += 1
    return creata


def _pos_bounds(w, aid):
    """Il pos minimo e il pos massimo ammissibili per un'attivita', sullo
    stesso dominio che GridBuilder.restrict costruirebbe:
    `_collocazioni(w, aid)` per le fasce, il giorno festivo escluso quando
    la settimana festiva e' fra quelle attive dell'attivita' (stessa lettura
    di `_try_place`). Il dominio e' un prodotto cartesiano giorni x fasce —
    nessuna delle due dipende dall'altra, quindi il minimo/massimo di
    `pos = day * width + slot` si ottiene dai minimi/massimi separati senza
    enumerare le celle — **finche' nessun pre-filtro taglia per coppia**
    `(giorno, fascia)`: qui vale perche' i due soli pre-filtri che tagliano
    celle si decompongono (`GridBuilder` taglia per giorno i festivi e per
    fascia durata/intervalli, separatamente), ma `UnavailabilityBuilder.
    restrict` taglia per coppia. Se questa famiglia acquistasse
    indisponibilita', la decomposizione smetterebbe di essere un invariante
    — resterebbe pero' un rilassamento (min/max su un sovrainsieme sono
    sempre `<=`/`>=` quelli veri), cioe' ancora dalla parte generosa.

    Non enumera nulla: se l'attivita' e' stata piazzata dal testimone, il
    suo dominio non e' vuoto (`_try_place` pesca proprio da questo
    prodotto), quindi `giorni` e `fasce` sono garantiti non vuoti."""
    grid = w.env["grid"]
    width = grid.slots_per_day
    holiday_week, holiday_day = w.env["holiday"]
    vieta_festivo = holiday_week in w.weeks_of[aid]
    giorni = [d for d in range(grid.days_per_cycle)
              if not (vieta_festivo and d == holiday_day)]
    fasce = _collocazioni(w, aid)
    return (min(giorni) * width + min(fasce), max(giorni) * width + max(fasce))


@deriver(ST.WEEKLY_ORDER, {"subject_weekly_order"})
def _derive_weekly_order(w):
    """Per ogni classe, per ogni coppia **ordinata** di materie distinte (A,
    B) presenti nel testimone: la riga si crea solo se supera due controlli,
    entrambi per firma di settimana.

    ⚠ **Il derivatore del piano e' rotto, misurato**: calcola la prima
    occorrenza sull'**unione** delle settimane, mentre il checker valuta uno
    ScheduleState **per firma** — il minimo su un sottoinsieme e' sempre
    `>=` il minimo sull'unione, quindi la relazione `first_a <= first_b` puo'
    ribaltarsi dentro una singola firma pur valendo sull'unione. Misurato su
    60 seed prima della correzione: 60/60 righe=1 (mai vacuo), ma 19/60 il
    testimone stesso viola la riga appena creata — un fallimento duro al
    passo 1 di `run_family` — e il seed 1 e' fra questi. Nota di contrasto:
    per SAME_DAY/SAME_HALF_DAY/TWO_DAYS derivare sull'unione e' corretto,
    perche' sono vincoli di «non accade mai» e un sottoinsieme dei
    piazzamenti puo' solo averne di meno — qui e' un minimo, il caso opposto.

    1. **Il testimone deve soddisfarla, firma per firma.** Per ogni firma in
       cui sia A sia B hanno attivita' attive nel testimone: se la prima
       occorrenza *piazzata* di B precede quella di A, la coppia si scarta —
       basta una sola firma a smentirla. Una firma dove una delle due materie
       e' assente non dice nulla (il checker uscirebbe con `not a or not b`):
       si passa oltre.
    2. **Violabilita' geometrica**, in almeno una firma dove entrambe sono
       presenti: il minimo, su B, della posizione ammissibile piu' presto
       (`floor_b`, da `_pos_bounds`) deve essere minore del minimo, su A,
       della posizione ammissibile piu' tardi (`ceil_a`) — cioe' deve essere
       *possibile* che B arrivi prima di quanto A sia costretta ad
       arrivare. E' necessaria, non sufficiente, per costruzione: ignora le
       altre attivita' che occupano le fasce, le indisponibilita', le sedi.
       Sbagliare generoso costa un caso di banco debole; sbagliare stretto
       costa copertura persa in silenzio, che e' peggio — quindi si sbaglia
       generoso.

    ⚠ Anche cosi', un seed del banco (il 5) non morde nella forma «risolvi e
    guarda la soluzione» — misurato, e la causa **non** e' che la guardia
    geometrica avesse creato una riga vacua: rifatto il modello per ogni
    riga del seed 5 col builder spento e forzata la violazione sulle stesse
    variabili che il builder costruirebbe, tutte e quattro le righe
    rispondono OPTIMAL, cioe' sono **davvero violabili**. Non mordono perche'
    il banco (`run_family`) chiede solo «risolvi col builder acceso e guarda
    se la soluzione restituita e' pulita», e CP-SAT restituisce da solo,
    deterministicamente, una soluzione che le rispetta per conto proprio —
    non perche' il vincolo non morda. La guardia geometrica resta comunque
    generosa (vede solo la geometria della coppia, non il resto del modello,
    stesso limite dichiarato per `_capienza_secchio`): quella proprieta' e'
    vera, ma e' un'altra cosa, e non e' la causa del non-mordere del seed 5.

    Accumula su tutte le classi e tutte le coppie ordinate, non si ferma
    alla prima: restituisce il numero di righe create (il potere
    vincolante)."""
    # Precondizione taciuta, sullo stesso modello di _capienza_secchio:
    # il filtro `klass.pk in w.tokens[aid]` (sotto) usa solo la chiave
    # della classe, mentre il checker espande l'unita' a _unit_keys(row) =
    # {classe, *parti} (subject_constraints.py). Con una ClassPart in gioco,
    # un'attivita' legata alla sola parte ha tokens senza klass.pk: il
    # derivatore la perde, il checker no. Su A la perdita allarga la
    # guardia (innocuo); su B la stringe, e puo' scartare righe violabili —
    # esattamente il modo di sbagliare che questa funzione dichiara di
    # evitare. Asserita invece che sperata: se il testimone acquista
    # partizioni, questa guardia smette di essere quella descritta sopra e
    # comincia a scartare righe violabili senza che si veda dai verdi.
    assert not ClassPart.objects.exists(), (
        "_derive_weekly_order filtra su klass.pk: con le parti, le "
        "occorrenze legate alla sola parte sfuggono al derivatore e non "
        "al checker")
    grid = w.env["grid"]
    width = grid.slots_per_day
    creata = 0
    for klass in w.env["classes"]:
        per_materia = defaultdict(list)
        for aid in w.placement:
            if klass.pk in w.tokens[aid]:
                per_materia[w.act(aid).subject_id].append(aid)
        materie = sorted(per_materia)
        for a_id in materie:
            for b_id in materie:
                if a_id == b_id:
                    continue
                aa_tutte, bb_tutte = per_materia[a_id], per_materia[b_id]
                scartata, violabile = False, False
                for rep, _ in w.signatures:
                    aa = [aid for aid in aa_tutte if rep in w.weeks_of[aid]]
                    bb = [aid for aid in bb_tutte if rep in w.weeks_of[aid]]
                    if not aa or not bb:
                        continue
                    prima_a = min(w.placement[aid][0] * width + w.placement[aid][1]
                                 for aid in aa)
                    prima_b = min(w.placement[bid][0] * width + w.placement[bid][1]
                                 for bid in bb)
                    if prima_b < prima_a:
                        scartata = True
                        break
                    floor_b = min(_pos_bounds(w, bid)[0] for bid in bb)
                    ceil_a = min(_pos_bounds(w, aid)[1] for aid in aa)
                    if floor_b < ceil_a:
                        violabile = True
                if scartata or not violabile:
                    continue
                SubjectConstraint.objects.create(
                    subject_a_id=a_id, subject_b_id=b_id,
                    school_class=klass, type=ST.WEEKLY_ORDER)
                creata += 1
    return creata


def _half_of(w, aid):
    """La mezza giornata di un'attivita' **piazzata** nel testimone, stessa
    regola di `_half` nel checker (subject_constraints.py): giorno * 2 +
    (0 se la fascia di partenza e' mattina, 1 se pomeriggio)."""
    day, slot = w.placement[aid]
    return day * 2 + (slot >= w.env["grid"].morning_end_slot)


@deriver(ST.IMPOSED_SUCCESSION, {"subject_imposed_succession"})
def _derive_imposed_succession(w):
    """Per ogni classe: righe A = B (una per materia presente) e righe
    A != B (una per coppia ordinata di materie distinte). Accumula su tutte
    le classi e tutte le coppie, non si ferma alla prima riga.

    ⚠ **Il derivatore del piano e' rotto, misurato**: crea solo righe A = B
    (il ramo A != B resterebbe senza banco di prova), si ferma alla prima
    riga con `return`, deriva `param` sull'**unione** delle settimane e non
    ha guardia di violabilita'. Riscritto per intero, sullo stesso principio
    gia' visto in `_derive_weekly_order`: il checker valuta uno
    `ScheduleState` **per firma** (`domain/analysis/conformity.py`,
    `check_schedule`), quindi `param` va calcolato guardando ogni firma per
    conto proprio, mai sull'unione.

    **Righe A = B**: per ogni firma, le mezze giornate delle occorrenze di
    quella materia **attive in quella firma**, ordinate; con meno di due
    occorrenze quella firma non dice nulla (nessuno scarto da misurare).
    `param` e' il massimo, su tutte le firme, dello scarto massimo fra mezze
    giornate di occorrenze consecutive — e almeno 1. Se nessuna firma ha
    almeno due occorrenze, la materia non produce nessuna riga: e' la stessa
    vacuita' di "meno di due occorrenze totali" gia' vista in
    `_derive_same_day`/`_derive_same_half_day`, qui per firma invece che
    sull'unione.

    **Righe A != B**: il checker (`ImposedSuccessionChecker.violations`,
    subject_constraints.py righe 191-207) **non ha guardia d'uscita** sul
    ramo A != B — a differenza di WEEKLY_ORDER, con `b` vuoto `any(...)` su
    lista vuota e' falso e *ogni* occorrenza di A diventa una violazione.
    Quindi: per ogni firma dove A ha occorrenze, se B non ne ha in quella
    stessa firma, il testimone stesso violerebbe la riga appena creata — la
    coppia **non e' derivabile**, si scarta per intero (non solo quella
    firma). Altrimenti, per ogni occorrenza di A in quella firma si calcola
    lo scarto **minimo positivo** verso una occorrenza di B nella stessa
    firma; se una qualunque occorrenza di A non ha nessuna B strettamente
    dopo di se' (nella stessa firma), la coppia si scarta — stesso motivo:
    sarebbe una riga che il testimone viola gia'. `param` e' il massimo di
    quegli scarti minimi, su tutte le firme e tutte le occorrenze di A, e
    almeno 1.

    **Guardia di violabilita' comune a entrambe le forme**: scarta se
    `param >= n - 1` (`n = days_per_cycle * 2`, le mezze giornate del
    ciclo) — con uno scarto massimo cosi' grande nessuna coppia dentro la
    settimana puo' mai superarlo, e la riga sarebbe inviolabile per
    costruzione della griglia, non del testimone (stessa forma della
    guardia `days_per_cycle < 2` di `_derive_two_days`).

    Stessa precondizione taciuta di `_derive_weekly_order`: il filtro
    `klass.pk in w.tokens[aid]` usa solo la chiave della classe, mentre il
    checker espande l'unita' a `_unit_keys(row) = {classe, *parti}`. Con una
    ClassPart in gioco un'attivita' legata alla sola parte sfuggirebbe al
    derivatore e non al checker — asserita invece che sperata."""
    assert not ClassPart.objects.exists(), (
        "_derive_imposed_succession filtra su klass.pk: con le parti, le "
        "occorrenze legate alla sola parte sfuggono al derivatore e non "
        "al checker")
    grid = w.env["grid"]
    n = grid.days_per_cycle * 2
    creata = 0
    for klass in w.env["classes"]:
        per_materia = defaultdict(list)
        for aid in w.placement:
            if klass.pk in w.tokens[aid]:
                per_materia[w.act(aid).subject_id].append(aid)
        materie = sorted(per_materia)

        # --- righe A = B ---------------------------------------------
        for subj_id in materie:
            aids = per_materia[subj_id]
            ha_coppia, param = False, 0
            for rep, _ in w.signatures:
                halves = sorted(_half_of(w, aid) for aid in aids
                                if rep in w.weeks_of[aid])
                if len(halves) < 2:
                    continue
                ha_coppia = True
                for h1, h2 in zip(halves, halves[1:]):
                    param = max(param, h2 - h1)
            if not ha_coppia:
                continue
            param = max(param, 1)
            if param >= n - 1:
                continue
            SubjectConstraint.objects.create(
                subject_a_id=subj_id, subject_b_id=subj_id,
                school_class=klass, type=ST.IMPOSED_SUCCESSION, param=param)
            creata += 1

        # --- righe A != B, coppie ordinate ----------------------------
        for a_id in materie:
            aa_tutte = per_materia[a_id]
            for b_id in materie:
                if a_id == b_id:
                    continue
                bb_tutte = per_materia.get(b_id, [])
                scartata, param = False, 0
                for rep, _ in w.signatures:
                    aa = [aid for aid in aa_tutte if rep in w.weeks_of[aid]]
                    if not aa:
                        continue
                    bb = [aid for aid in bb_tutte if rep in w.weeks_of[aid]]
                    if not bb:
                        scartata = True
                        break
                    b_halves = sorted(_half_of(w, bid) for bid in bb)
                    for aid in aa:
                        ha = _half_of(w, aid)
                        candidati = [hb - ha for hb in b_halves if hb > ha]
                        if not candidati:
                            scartata = True
                            break
                        param = max(param, min(candidati))
                    if scartata:
                        break
                if scartata or param == 0:
                    continue
                param = max(param, 1)
                if param >= n - 1:
                    continue
                SubjectConstraint.objects.create(
                    subject_a_id=a_id, subject_b_id=b_id,
                    school_class=klass, type=ST.IMPOSED_SUCCESSION, param=param)
                creata += 1
    return creata


@deriver(ST.HALF_DAY_GAP, {"subject_half_day_gap"})
def _derive_half_day_gap(w):
    """Per ogni classe, per ogni coppia **ordinata** di materie (A, B),
    inclusa A = B: `param` e' lo scarto minimo, in mezze giornate, che il
    testimone rispetta gia' in **ogni** firma di settimana dove la coppia
    produce almeno una coppia incrociata.

    ⚠ **Deriva contro la regola del builder** (tutte le coppie incrociate,
    non solo le consecutive nell'ordinamento come il checker): sono
    equivalenti per la dimostrazione nel docstring di `HalfDayGapBuilder`
    (domain/solver/builders/subject_order.py), e derivare contro il builder
    tiene onesta quella dimostrazione a ogni esecuzione, invece di limitarsi
    a fidarsene una volta sola.

    Per ogni firma si costruisce `merged`: le occorrenze **attive in quella
    firma**, con l'etichetta di sorgente ("a"/"b") che il checker usa per
    decidere se una coppia e' incrociata — solo A se `same`, A e B
    altrimenti. Con `same = False` una firma dove uno dei due lati e' vuoto
    non produce nessuna coppia incrociata (il checker vedrebbe un `merged`
    con una sola sorgente, quindi nessuna coppia con `crossed` vero): si
    salta **quella firma**, non l'intera coppia — a differenza del ramo A
    != B di IMPOSED_SUCCESSION, qui non c'e' guardia d'uscita del checker da
    rispettare, quindi una firma senza B non e' una violazione, e' solo una
    firma senza informazione.

    Il minimo di una firma e' il minimo, su **tutte** le coppie incrociate
    di quel `merged` (non solo le adiacenti — la dimostrazione dice che e'
    lo stesso, e derivare contro la regola del builder invece che contro
    quella "ottimizzata" del checker e' cio' che rende il testimone un test
    indipendente della dimostrazione).

    `param` finale e' il minimo **fra le firme** di quei minimi — non il
    massimo, a differenza di WEEKLY_ORDER/IMPOSED_SUCCESSION: li' `param` e'
    un tetto (lo scarto reale deve stare **sotto**), quindi serve la firma
    piu' larga; qui `param` e' una soglia dal basso (lo scarto reale deve
    stare **sopra**), quindi serve la firma piu' stretta — chi vincola di
    piu' e' chi decide il valore che il testimone puo' ancora rispettare
    ovunque.

    Guardie: nessuna riga se nessuna firma produce alcuna coppia incrociata
    (`param is None`), se il minimo trovato e' sotto 1 (riga vacua o
    degenere), o se `param >= n` (`n = days_per_cycle * 2`, le mezze
    giornate del ciclo: uno scarto cosi' largo non puo' mai essere violato
    dentro la settimana, la riga sarebbe inviolabile per costruzione della
    griglia — stessa forma della guardia in `_derive_imposed_succession`).

    Accumula su tutte le classi e tutte le coppie ordinate, non si ferma
    alla prima: restituisce il numero di righe create.

    Stessa precondizione taciuta di `_derive_weekly_order`/
    `_derive_imposed_succession`: il filtro `klass.pk in w.tokens[aid]` usa
    solo la chiave della classe; con una ClassPart in gioco le occorrenze
    legate alla sola parte sfuggirebbero al derivatore e non al checker —
    asserita invece che sperata."""
    assert not ClassPart.objects.exists(), (
        "_derive_half_day_gap filtra su klass.pk: con le parti, le "
        "occorrenze legate alla sola parte sfuggono al derivatore e non "
        "al checker")
    grid = w.env["grid"]
    n = grid.days_per_cycle * 2
    creata = 0
    for klass in w.env["classes"]:
        per_materia = defaultdict(list)
        for aid in w.placement:
            if klass.pk in w.tokens[aid]:
                per_materia[w.act(aid).subject_id].append(aid)
        materie = sorted(per_materia)
        for a_id in materie:
            for b_id in materie:
                same = a_id == b_id
                aa_tutte = per_materia[a_id]
                bb_tutte = per_materia[b_id]
                param = None
                for rep, _ in w.signatures:
                    aa = [aid for aid in aa_tutte if rep in w.weeks_of[aid]]
                    merged = [(_half_of(w, aid), aid, "a") for aid in aa]
                    if not same:
                        bb = [bid for bid in bb_tutte if rep in w.weeks_of[bid]]
                        if not aa or not bb:
                            continue
                        merged += [(_half_of(w, bid), bid, "b") for bid in bb]
                    merged.sort()
                    minimo_firma = None
                    for i, (h1, id1, s1) in enumerate(merged):
                        for h2, id2, s2 in merged[i + 1:]:
                            if id1 == id2 or not (same or s1 != s2):
                                continue
                            d = h2 - h1
                            if minimo_firma is None or d < minimo_firma:
                                minimo_firma = d
                    if minimo_firma is None:
                        continue
                    if param is None or minimo_firma < param:
                        param = minimo_firma
                if param is None or param < 1 or param >= n:
                    continue
                SubjectConstraint.objects.create(
                    subject_a_id=a_id, subject_b_id=b_id,
                    school_class=klass, type=ST.HALF_DAY_GAP, param=param)
                creata += 1
    return creata


@deriver(RT.MIN_DISTRIBUTION, {"min_distribution"})
def _derive_min_distribution(w):
    """Chiede i giorni effettivamente lavorati nella firma **peggiore**: e'
    il massimo che il testimone garantisce in tutte le settimane. Vacua
    (ritorna 0) se la classe scelta a caso non lavora in nessuna firma —
    stessa convenzione di _derive_max_half_days."""
    klass = w.rng.choice(w.env["classes"])
    peggiore = min(len(w.resource_days(klass.pk, rep)) for rep, _ in w.signatures)
    if peggiore == 0:
        return 0
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": w.env["grid"].slot_minutes,
                "min_days": peggiore})
    return 1


@deriver(RT.ARRIVAL_DEPARTURE, {"arrival_departure"})
def _derive_arrival_departure(w):
    """La finestra osservata: la prima fascia usata e l'ultima piu' uno.
    Chiede che **tutti** i giorni siano conformi, e nel testimone lo sono.

    Vacua (ritorna 0) se la finestra risultante non vieta nessuna fascia —
    `prima == 0` e `ultima == slots_per_day - 1`, cioe' il docente scelto a
    caso non compare in nessuna firma (fallback alla griglia intera) o vi
    occupa gia' sia la prima sia l'ultima fascia: in entrambi i casi
    `proibite` nel builder e' vuoto, il vincolo `>= days` e' banalmente vero
    per qualunque piazzamento, e un builder vacuo non potrebbe farlo fallire
    (stessa convenzione di _derive_unavailability)."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    prima, ultima = grid.slots_per_day, 0
    for rep, _ in w.signatures:
        for _day, fasce in w.resource_days(docente.pk, rep).items():
            prima, ultima = min(prima, fasce[0]), max(ultima, fasce[-1])
    if prima > ultima:
        prima, ultima = 0, grid.slots_per_day - 1
    if prima == 0 and ultima == grid.slots_per_day - 1:
        return 0
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.ARRIVAL_DEPARTURE,
        params={"not_before_slot": prima, "not_after_slot": ultima + 1,
                "days": grid.days_per_cycle})
    return 1


@deriver(RT.FREE_GUARANTEED, {"free_guaranteed"})
def _derive_free_guaranteed(w):
    """I giorni e le mezze giornate libere osservati nella firma peggiore.
    ⚠ Le mezze giornate si contano **solo sui giorni con attivita'**, come fa
    il checker: derivare altrimenti produrrebbe un testimone che il checker
    stesso boccia, e run_family lo direbbe al punto 1.

    Vacua (ritorna 0) se entrambe le soglie derivate sono zero: il builder
    posta `sum(...) >= minimo` solo quando `minimo` e' vero (`if
    minimo_giorni:` / `if minimo_mezze and mezze_libere:`), quindi a
    zero-zero non posterebbe nulla — non c'e' nulla da far fallire se fosse
    vacuo."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    min_giorni, min_mezze = grid.days_per_cycle, grid.days_per_cycle * 2
    for rep, _ in w.signatures:
        giorni = w.resource_days(docente.pk, rep)
        liberi = grid.days_per_cycle - len(giorni)
        mezze = 0
        for _day, fasce in giorni.items():
            mezze += not any(f < grid.morning_end_slot for f in fasce)
            mezze += not any(f >= grid.morning_end_slot for f in fasce)
        min_giorni, min_mezze = min(min_giorni, liberi), min(min_mezze, mezze)
    if not min_giorni and not min_mezze:
        return 0
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.FREE_GUARANTEED,
        params={"free_days": min_giorni, "free_half_days": min_mezze})
    return 1


@deriver(RT.MAX_PRESENCE, {"max_presence", "max_presence_days"})
def _derive_max_presence(w):
    """Il picco di presenza (`ultima - prima + 1`, sulla **giornata intera**
    — non per mezza giornata, a differenza del D.T.B.) e il numero di giorni
    lavorati, per la firma peggiore. Con l'uguaglianza il vincolo e'
    soddisfatto e stretto.

    Vacua (ritorna 0, correzione 3 del brief, Ruling 24) in due casi:
    il docente scelto a caso non compare in nessuna firma (`giorni == 0`,
    stessa convenzione di `_derive_max_half_days` — nessuna soglia potrebbe
    mai essere violata); oppure il picco copre gia' l'intera giornata **e**
    i giorni coprono gia' `days_per_cycle`, cioe' entrambi i rami del
    checker diventano banalmente veri per costruzione (nessuna presenza puo'
    mai superare la giornata, nessun conteggio di giorni puo' mai superare
    il ciclo) — un builder rotto non potrebbe farlo fallire."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    picco, giorni = 0, 0
    for rep, _ in w.signatures:
        per_firma = w.resource_days(docente.pk, rep)
        giorni = max(giorni, len(per_firma))
        for _day, fasce in per_firma.items():
            picco = max(picco, (fasce[-1] - fasce[0] + 1) * grid.slot_minutes)
    if giorni == 0:
        return 0
    if (picco >= grid.slots_per_day * grid.slot_minutes
            and giorni >= grid.days_per_cycle):
        return 0
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.MAX_PRESENCE,
        params={"max_minutes": picco, "days": giorni})
    return 1


@deriver(RT.MAX_SITE_CHANGES, {"max_site_changes"})
def _derive_max_site_changes(w):
    """Formulazione **«segregato»** (Ruling 34, review Task 9 giro di
    correzione 1, §3): il derivatore **costruisce** lo scenario invece di
    osservarlo. La versione precedente sceglieva un docente a caso e si
    limitava a leggere le sedi che gli erano gia' toccate da
    `_make_activities` (assegnazione al 50%, indipendente dal docente): la
    review ha misurato il potere vincolante reale (builder reso no-op, il
    caso deve fallire) a **0/15** — la famiglia non testava niente, perche'
    quasi mai un docente a caso aveva due sedi distinte sulle proprie
    attivita' nello stesso giorno.

    Qui si sceglie il docente con **piu' attivita'** nel testimone e gli si
    assegna una sede **per giornata**: tutte le sue attivita' dello stesso
    giorno alla stessa sede, sedi alternate fra giorni consecutivi
    (`sites[day % len(sites)]`); tutte le altre attivita' (di lui e di
    chiunque altro) restano senza sede. Cosi' i cambi di sede **per
    giornata** del docente scelto sono sempre zero nel testimone — non serve
    dimostrarlo caso per caso, e' garantito dalla costruzione — quindi il
    tetto derivato e' `per_day = per_week = 0`, e qualunque soluzione che
    mescoli due sedi diverse nella stessa giornata di quel docente lo viola.
    Misurato qui (giro di correzione 1, builder reso no-op, 15 seed, piu'
    esecuzioni per il non determinismo di CP-SAT): **10/15** stabile su
    quattro esecuzioni consecutive. La review aveva misurato 12/15 sulla
    propria formulazione di riferimento (non il codice qui sopra, solo la
    descrizione): la differenza e' compatibile coi dettagli di
    implementazione (qui il docente e' scelto per numero totale di
    attivita', non specificamente per idoneita' a produrre sedi multiple) —
    resta comunque un miglioramento netto rispetto allo 0/15 in albero.

    Non tocca `_make_activities`: sovrascrive le sedi **dopo** che il
    testimone e' gia' completo, e ogni `run_family` costruisce il proprio
    testimone da zero — nessun altro derivatore vede questo cambiamento.

    Vacua (ritorna 0) in due casi, non uno solo. Il primo: il docente piu'
    carico ha **meno di due attivita'** nel testimone — con una sola, «cambio
    di sede» non e' strutturalmente possibile per lui. Il secondo, che la
    prima stesura di questo derivatore aveva perso: le sue attivita' cadono in
    **meno giorni distinti** di quante sono le sedi, e allora l'alternanza non
    riesce ad assegnargliene due — con una sede sola `per_day = per_week = 0`
    e' inviolabile, e il caso passerebbe anche col builder spento."""
    conteggio = defaultdict(int)
    for aid in w.placement:
        for t in w.act(aid).teachers.all():
            conteggio[t.pk] += 1
    docente_pk = max(conteggio, key=conteggio.get)
    docente = next(t for t in w.env["teachers"] if t.pk == docente_pk)
    attivita_docente = [aid for aid in w.placement
                        if docente.pk in w.tokens[aid]]
    if len(attivita_docente) < 2:
        return 0

    sites = w.env["sites"]
    # ⚠ Le sedi si alternano sui giorni **realmente usati** dal docente, non
    # sul numero del giorno. Con `sites[day % len(sites)]` un docente che
    # lavora solo in giorni della stessa parita' riceveva **una sola sede**, e
    # allora `per_day = per_week = 0` e' inviolabile: nessun piazzamento puo'
    # produrre un cambio, e il caso passa anche col builder spento. Era il
    # seed 1, cioe' dentro il banco (Important 1 della ri-review del giro 1).
    giorni_usati = sorted({w.placement[aid][0] for aid in attivita_docente})
    if len(giorni_usati) < len(sites):
        return 0   # non abbastanza giorni per esibire due sedi distinte
    for act in w.activities:
        act.site = None
        act.save()
    for aid in attivita_docente:
        day, _slot = w.placement[aid]
        act = w.act(aid)
        act.site = sites[giorni_usati.index(day) % len(sites)]
        act.save()

    per_giorno, per_settimana = 0, 0
    for rep, _ in w.signatures:
        settimana = 0
        for day, fasce in w.resource_days(docente.pk, rep).items():
            sequenza = []
            for f in fasce:
                for aid, (d, slot) in w.placement.items():
                    if (d == day and slot == f and docente.pk in w.tokens[aid]
                            and w.act(aid).site_id is not None
                            and rep in w.weeks_of[aid]):
                        sequenza.append(w.act(aid).site_id)
            cambi = sum(x != y for x, y in zip(sequenza, sequenza[1:]))
            per_giorno = max(per_giorno, cambi)
            settimana += cambi
        per_settimana = max(per_settimana, settimana)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.MAX_SITE_CHANGES,
        params={"per_day": per_giorno, "per_week": per_settimana})
    return 1


def _distanza_sedi(w, aid, slot, altro, slot2):
    """Distanza in fasce fra le occupazioni di due attivita' — sulle fasce
    **occupate**, non sulle fasce d'inizio (Important 2, review Task 9 giro
    di correzione 1): un'attivita' di durata > 1 occupa anche le fasce
    successive alla prima, e il checker cammina sulle fasce occupate
    (`_site_sequence`, `domain/analysis/checkers/time_constraints.py` e
    `sites.py`). La vecchia formula (`abs(slot2 - slot) - 1`, sulle sole
    fasce d'inizio) poteva dichiarare un `needed` che il testimone stesso
    viola: riprodotto con `run_family("structural:site_transition", 15)` sul
    codice in albero, seed 15 (vedi il report del Task 9, giro di correzione
    1, per l'output verbatim)."""
    if slot < slot2:
        return slot2 - slot - w.act(aid).duration_slots
    return slot - slot2 - w.act(altro).duration_slots


def _coppie_sedi_vicine(w):
    """Tutte le coppie (non ordinate) di attivita' con sedi note e diverse,
    chiave condivisa (stessa classe o stesso docente) e stesso giorno, in
    almeno una firma di settimana in cui sono entrambe attive — con la loro
    distanza (fasce occupate, `_distanza_sedi`)."""
    viste = set()
    coppie = []
    for rep, _ in w.signatures:
        for aid, (day, slot) in w.placement.items():
            a1 = w.act(aid)
            if a1.site_id is None or rep not in w.weeks_of[aid]:
                continue
            for altro, (day2, slot2) in w.placement.items():
                if altro == aid or day2 != day or rep not in w.weeks_of[altro]:
                    continue
                a2 = w.act(altro)
                if a2.site_id is None or a2.site_id == a1.site_id:
                    continue
                if not (w.tokens[aid] & w.tokens[altro]):
                    continue
                chiave = frozenset((aid, altro))
                if chiave in viste:
                    continue
                viste.add(chiave)
                coppie.append((aid, altro,
                               _distanza_sedi(w, aid, slot, altro, slot2)))
    return coppie


@deriver("structural:site_transition", {"site_transition"})
def _derive_site_transition(w):
    """Formulazione **«denso»** (Ruling 34, review Task 9 giro di correzione
    1, §3): il derivatore **costruisce** lo scenario invece di osservarlo.

    La versione precedente osservava le sedi assegnate a caso al 50% da
    `_make_activities` e derivava il minimo delle distanze fra le coppie
    trovate. La review ha dimostrato che nessuna riformulazione che si
    limiti a **osservare** puo' fare meglio: `site_transition_slots` e'
    un'impostazione d'istituto globale, quindi il `needed` derivabile e'
    *necessariamente* il minimo su tutte le coppie — e il minimo su coppie
    casuali e' quasi sempre zero (potere vincolante reale misurato: 1/15).
    Ridurre la densita' delle sedi peggiora, non aiuta: meno coppie significa
    piu' spesso *zero* coppie, che e' vacuo lo stesso.

    L'unica via che regge e' **riparare** il testimone: (i) calcolare la
    distanza sulle fasce occupate, non sulle fasce d'inizio (`_distanza_sedi`
    — chiude anche l'Important 2 per costruzione, non solo qui); (ii)
    assegnare una sede a **tutte** le attivita' del testimone (sovrascrive
    l'assegnazione al 50% di `_make_activities`, ma solo su questa copia del
    testimone: non tocca `_make_activities`, e nessun altro derivatore ne
    risente); (iii) finche' esiste una coppia a distanza <= 0, togliere la
    sede, greedy, a una delle due (converge sempre: ogni rimozione riduce di
    uno il numero di attivita' con sede, quindi il ciclo e' limitato da
    `len(w.activities)`); (iv) `needed` = minimo superstite, vacua
    (`return 0`) se non sopravvive nessuna coppia. Misurato qui (giro di
    correzione 1, builder reso no-op, 15 seed, piu' esecuzioni per il non
    determinismo di CP-SAT): **12-14/15** a seconda dell'esecuzione, contro
    l'1/15 della formulazione osservativa — in linea con la misura della
    review (12/15)."""
    sites = w.env["sites"]
    if len(sites) < 2:
        return 0
    for act in w.activities:
        act.site = w.rng.choice(sites)
        act.save()

    limite = len(w.activities) + 1
    for _ in range(limite):
        a_zero = [c for c in _coppie_sedi_vicine(w) if c[2] <= 0]
        if not a_zero:
            break
        _, altro, _ = a_zero[0]
        w.act(altro).site = None
        w.act(altro).save()
    else:
        raise AssertionError(
            "_derive_site_transition: la riparazione non converge, "
            "bug nel derivatore")

    coppie = _coppie_sedi_vicine(w)
    settings, _ = InstituteSettings.objects.get_or_create(pk=1)
    if not coppie:
        settings.site_transition_slots = 0
        settings.save()
        return 0
    needed = min(d for _, _, d in coppie)
    settings.site_transition_slots = needed
    settings.save()
    return 0 if needed == 0 else 1
