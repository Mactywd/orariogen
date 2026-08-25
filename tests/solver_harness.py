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

⚠ **«Orario valido» ha un limite preciso, e va detto.** Il testimone e'
costruito valido per la **griglia** (festivi, intervalli, durate) e per
l'**occupazione** delle risorse; `run_family` ne verifica poi la validita'
sulle sole causali della famiglia sotto esame. Non e' invece pulito a tutto
campo: `structural:coverage` produce `coverage_mismatch` su tutti i seed del
banco, perche' i `Service` della fixture sono per (piano, materia) mentre
`student_units` attribuisce il monte ore alle **parti** quando la classe ne
ha. Non tocca la premessa del passo 2 — `structural:coverage` e' l'unico
checker senza builder, deliberatamente (e' `PLACEMENT_INDEPENDENT`: il solver
non crea ne' distrugge attivita'), quindi non compare mai nel modello e non
puo' rendere infattibile nulla. Ma un oracolo differenziale a tutto campo su
questo testimone lo incontrerebbe: si riparerebbe **nella fixture**, non in
`domain/analysis/`.

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
    Activity, Break, Discipline, Holiday, InstituteSettings, Period,
    Placement, Schedule, SchoolClass, SchoolYear, Site, StudyPlan, Subject,
    Teacher, TimeGrid, Service,
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
    # ⚠ `site_transition_slots` ha default **1** sul modello, e
    # `_make_activities` assegna una sede a meta' delle attivita' a caso: il
    # testimone violava quindi `site_transition` prima ancora che un
    # derivatore girasse (misurato: 4 seed su 5 del banco). Non e' un
    # dettaglio estetico — rende **falsa** la premessa del passo 2 di
    # `run_family` («c'era un testimone, quindi INFEASIBLE e' un fallimento
    # duro»): con quella soglia il testimone non e' un punto ammissibile del
    # modello completo, perche' `structural:site_transition` e' registrato e
    # attivo in ogni `solve()`. Si parte da zero — nessun vincolo — e
    # `_derive_site_transition` alza la soglia per conto proprio quando tocca
    # alla sua famiglia.
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    # Uno sdoppiamento vero (Task 15a): una sola partizione sulla **prima**
    # classe, due parti. Con una partizione sola AtomMap non costruisce alcun
    # atomo (ne servono almeno due, ADR-017), quindi le due parti restano
    # disgiunte fra loro e confliggono solo con la classe intera — che e'
    # esattamente la proprieta' dello sdoppiamento che nessun banco di prova
    # esercitava prima. La seconda classe resta senza parti, cosi' ogni
    # derivatore attraversa tutti e due i casi nello stesso testimone.
    partizione = ClassPartition.objects.create(
        school_class=classes[0], name="LINGUA")
    parts = [ClassPart.objects.create(name=nm, partition=partizione)
             for nm in ("1A_ING", "1A_TED")]
    return {"grid": grid, "year": year, "period": period, "schedule": schedule,
            "discipline": disc, "subjects": subjects, "plans": plans,
            "classes": classes, "teachers": teachers, "sites": sites,
            "parts": parts, "break_boundary": break_boundary,
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
    # Un'attivita' per parte (Task 15a). Sta in coda per non spostare nessuna
    # estrazione delle attivita' di classe: il flusso casuale principale e'
    # condiviso, e pescare prima avrebbe cambiato il testimone di tutte le
    # famiglie a parita' di seed senza che la fixture sia davvero diversa.
    # Durata 1 e nessuna sede: la forma minima che basta a far entrare le
    # parti nelle chiavi di occupazione.
    for part in env["parts"]:
        subject = rng.choice(env["subjects"])
        act = Activity.objects.create(
            subject=subject, duration_slots=1, duration_minutes=60,
            week_mask=rng.choice(MASKS))
        act.teachers.add(rng.choice(env["teachers"]))
        act.parts.add(part)
        service, _ = Service.objects.get_or_create(
            study_plan=part.effective_study_plan, subject=subject,
            defaults={"class_minutes": 0})
        service.class_minutes += 60
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


# ⚠ **I derivatori non sono componibili in ordine qualunque.** Due di loro
# sono in formulazione **densa** (Ruling 34): non osservano il testimone, lo
# **riparano** per rendere la propria famiglia non vacua. E la riparazione si
# vede dalle altre famiglie.
#
# - `_derive_site_transition` riassegna la **sede** a tutte le attivita', e
#   le sedi sono cio' che `max_site_changes` conta;
# - i quattro `parts_*` (`_sintonizza_parti`) riassegnano la **materia**
#   dell'attivita' di ogni parte, e la materia e' cio' su cui ogni riga
#   `SubjectConstraint` e' ancorata.
#
# Nessuna delle due tocca griglia od occupazione, ed e' per questo che le loro
# docstring dichiaravano di non disturbare nessuno: e' vero per il testimone
# *in se'*, falso per le **righe gia' derivate** da altri. Misurato mettendoli
# in ordine alfabetico: `parts_*` sporca `subject_half_day_gap`,
# `subject_imposed_succession`, `subject_max_hours_day/half_day`;
# `structural:site_transition` sporca `max_site_changes` — e la composizione
# risponde INFEASIBLE su 2 seed su 3.
#
# Non e' un difetto da riparare: e' una **precedenza**. Chi ripara il
# testimone va per primo, prima che qualcun altro derivi righe sullo stato che
# sta per cambiare.
MUTANTI = ("structural:site_transition", "parts_before_class",
           "parts_after_class", "parts_before_or_after_class_h",
           "parts_before_or_after_class_ab")


def ordine_derivatori():
    """Le chiavi dei derivatori con i **mutanti in testa**: vedi il commento
    qui sopra. Fuori da questo ordine la composizione non regge."""
    per_nome = {str(k): k for k in DERIVERS}
    testa = [per_nome[n] for n in MUTANTI if n in per_nome]
    return testa + [k for k in sorted(DERIVERS, key=str) if k not in testa]


def run_tutte_le_famiglie(seed, time_limit=120):
    """Il banco a **modello completo**: tutte le famiglie attive insieme sullo
    stesso testimone, invece di una per volta.

    E' la misura che il Fermi non puo' dare. Il dataset Fermi ha **zero** righe
    `ResourceTimeConstraint` e **zero** `SubjectConstraint`, e i quattro tetti
    di peso a `None`: ventuno builder su ventisei non postano nulla, e il
    modello «completo» sul Fermi e' identico byte per byte a quello dello
    spike a cinque vincoli. Qui invece ogni famiglia porta le proprie righe.

    Il testimone resta il testimone: ogni riga e' derivata perche' *lui* la
    soddisfa, quindi soddisfa anche la loro **congiunzione** — INFEASIBLE
    resta un fallimento duro, esattamente come in `run_family`.

    Restituisce `(w, soluzione, poteri)`."""
    w = build_witness(seed)
    poteri, codici = {}, set()
    for key in ordine_derivatori():
        d = DERIVERS[key]
        poteri[str(key)] = d.fn(w)
        codici |= set(d.codes)

    sporco = _hard(w.schedule, codici)
    assert sporco == set(), (
        f"il testimone viola la congiunzione delle righe derivate "
        f"(seed {seed}): {sorted(sporco)} — un derivatore ha sporcato le "
        f"righe di un altro, vedi ordine_derivatori()")

    Placement.objects.filter(schedule=w.schedule).delete()
    soluzione = solve(w.schedule, time_limit=time_limit)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), (
        f"modello completo INFEASIBLE con un testimone disponibile "
        f"(seed {seed}): {soluzione.stats}")

    apply(soluzione, w.schedule)
    dopo = _hard(w.schedule, codici)
    assert dopo == set(), (
        f"il modello completo accetta un piazzamento che il checker boccia "
        f"(seed {seed}): {sorted(dopo)}")
    return w, soluzione, poteri


from domain.models import (
    ClassPart, ClassPartition, InstituteSettings, ResourceTimeConstraint,
    ResourceUnavailability, SubjectConstraint,
)
from domain.models.resources import Resource

RT = ResourceTimeConstraint.Type
ST = SubjectConstraint.Type


def _chiavi_unita(w, klass):
    """L'espansione dell'unita' «classe» come la fa il checker (`_unit_keys`,
    domain/analysis/checkers/subject_constraints.py): la classe **piu' tutte
    le sue parti**. Filtrare sul solo `klass.pk` perderebbe le attivita'
    legate alla sola parte, che il checker invece vede — e una riga derivata
    senza vederle nasce gia' violata.

    Vale solo per le righe `SubjectConstraint` con `school_class`: le righe
    `ResourceTimeConstraint` sono ancorate alla **risorsa**
    (`row.resource_id`, domain/analysis/checkers/time_constraints.py), che per
    una classe e' la sola `klass.pk` — li' l'espansione sarebbe sbagliata, e
    infatti quei derivatori continuano a leggere `w.resource_days(klass.pk)`."""
    parti = ClassPart.objects.filter(
        partition__school_class=klass).values_list("pk", flat=True)
    return frozenset({klass.pk, *parti})


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
    unita', in un giorno qualunque?

    ⚠ «Senza sovrapporsi» vale solo se le due attivita' **confliggono**
    davvero (Task 15a). Due attivita' su parti diverse della stessa
    partizione non condividono nessuna chiave di occupazione: possono
    partire nella **stessa** fascia, e il checker le conta comunque
    entrambe nel secchio (`_unit_keys` espande l'unita' alle parti). La
    sovrapposizione si vieta quindi solo quando i token si intersecano —
    che e' anche il caso, sulle stesse parti, di due attivita' che
    condividono il docente.

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
    confliggono = bool(w.tokens[a] & w.tokens[b])

    def secchio(s):
        return 0 if kind == "day" else s >= grid.morning_end_slot

    for sa in _collocazioni(w, a):
        for sb in _collocazioni(w, b):
            if confliggono and sa + da > sb and sb + db > sa:
                continue          # si sovrappongono su una chiave condivisa
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
        chiavi = _chiavi_unita(w, klass)
        for subject in w.env["subjects"]:
            aids = [aid for aid in w.placement
                    if w.tokens[aid] & chiavi
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
        chiavi = _chiavi_unita(w, klass)
        for subject in w.env["subjects"]:
            aids = [aid for aid in w.placement
                    if w.tokens[aid] & chiavi
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
        chiavi = _chiavi_unita(w, klass)
        giorni = defaultdict(set)
        for aid, (day, _slot) in w.placement.items():
            if w.tokens[aid] & chiavi:
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


def _strato(w, aid):
    """A quale strato di simultaneita' appartiene un'attivita' dentro l'unita'
    «classe»: `None` se e' di livello classe (i suoi token contengono la
    chiave di una classe), altrimenti l'insieme delle parti che tocca.

    Due attivita' dello **stesso** strato non possono sovrapporsi (stessa
    parte, o stessa classe intera); due attivita' di strati diversi si',
    quando sono parti diverse della stessa partizione — e senza atomi in
    gioco non condividono nessuna chiave di occupazione."""
    classi = {k.pk for k in w.env["classes"]}
    if w.tokens[aid] & classi:
        return None
    return frozenset(w.tokens[aid] & {p.pk for p in w.env["parts"]})


def _capienza_secchio(w, kind, rep, aids):
    """Un **limite superiore** ai minuti che possono **partire** nello stesso
    secchio, in un giorno qualunque, fra le attivita' di `aids` co-attive
    nella firma `rep`. Enumerazione esaustiva sulle collocazioni ammissibili
    di ciascuna attivita' (`_collocazioni`), non formula chiusa — la formula
    chiusa su questo branch e' stata provata e scartata due volte
    (Ruling 51).

    Non vede le altre attivita' che occupano le fasce (di altre materie o
    classi), le indisponibilita', le sedi, i giorni festivi. Un secchio che
    qui risulta riempibile oltre `param` puo' quindi risultare comunque
    inviolabile per via del resto del modello — stabilirlo richiede di
    chiedere al solver (Ruling 64, rimandato al Task 17 dalla Ruling 65). E'
    la direzione giusta in cui sbagliare: generosa, mai stretta — sbagliare
    per eccesso costa un caso di banco debole, sbagliare per difetto costa
    copertura persa in silenzio.

    ⚠ **Con le parti in gioco non e' piu' un massimo esatto sulla geometria,
    ed e' voluto** (Task 15a). `_massimo_pacchetto` vieta la
    sovrapposizione, ma due attivita' su parti diverse della stessa
    partizione non condividono nessuna chiave di occupazione: sono
    legittimamente simultanee, e il checker le somma comunque tutte e due
    nello stesso secchio (`_unit_keys` espande l'unita' alle parti). Tenere
    il divieto di sovrapposizione avrebbe reso la guardia **stretta**,
    scartando righe violabili. Quindi la capienza si calcola per **strati**
    (`_strato`) e si sommano:

        capienza = pacchetto massimo delle attivita' di livello classe
                 + somma, su ogni parte, del pacchetto massimo di quella parte

    La somma ignora i conflitti fra strati (una attivita' di classe intera e
    una di parte confliggono davvero, e cosi' due attivita' che condividono
    il docente), quindi e' `>=` della capienza vera **per costruzione** — e
    resta molto piu' fine della somma nuda dei minuti, che e' cio' che conta
    per la guardia. Il costo dichiarato: qualche riga inviolabile rientra nel
    banco, cioe' un caso di banco debole invece di copertura persa in
    silenzio.

    **Una precondizione resta**, e resta asserita: la capienza simultanea
    delle risorse vale 1 — il default di `Resource.simultaneous_capacity`,
    che l'harness non tocca mai. Con capienza cumulativa
    (`OccupationBuilder` la supporta, ed e' feature EDT documentata) due
    attivita' dello **stesso** strato potrebbero condividere la fascia, e il
    massimo di ogni strato supererebbe il proprio pacchetto."""
    grid = w.env["grid"]
    # La precondizione del capoverso qui sopra. Asserita invece che sperata:
    # se il testimone acquista capienza cumulativa, questa guardia smette di
    # essere generosa e comincia a scartare righe violabili — un modo di
    # sbagliare che non si vede dai verdi, perche' si manifesta come
    # copertura che non c'e' piu'.
    assert not Resource.objects.filter(simultaneous_capacity__gt=1).exists(), (
        "_capienza_secchio presuppone capienza simultanea 1: con risorse "
        "cumulative due attivita' possono condividere la fascia, e il "
        "massimo reale supera questo limite")

    def secchio(s):
        return 0 if kind == "day" else int(s >= grid.morning_end_slot)

    buckets = (0,) if kind == "day" else (0, 1)
    migliore = 0
    for b in buckets:
        per_strato = defaultdict(list)
        for aid in aids:
            if rep not in w.weeks_of[aid]:
                continue
            starts = [s for s in _collocazioni(w, aid) if secchio(s) == b]
            if starts:
                per_strato[_strato(w, aid)].append(
                    (w.act(aid).duration_minutes,
                     w.act(aid).duration_slots, starts))
        totale = sum(_massimo_pacchetto(opzioni)
                     for opzioni in per_strato.values())
        migliore = max(migliore, totale)
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
    TWO_DAYS qui sopra.

    ⚠ **Con le parti (Task 15a) `_capienza_secchio` non e' piu' un massimo
    esatto sulla geometria ma un limite superiore per strati**: cambia il
    dettaglio, non l'argomento. La sussunzione regge lo stesso — se la
    capienza supera `param` servono ancora almeno due attivita' (ogni
    attivita' da sola e' dominata dal proprio `param`, che il testimone
    misura per costruzione), e due attivita' di strati diversi «ci stanno»
    a maggior ragione, perche' possono perfino partire nella stessa fascia.
    Le occorrenze si filtrano con `_chiavi_unita`, come le altre famiglie di
    materia."""
    grid = w.env["grid"]
    creata = 0
    for klass in w.env["classes"]:
        chiavi = _chiavi_unita(w, klass)
        for subject in w.env["subjects"]:
            aids = [aid for aid in w.placement
                    if w.tokens[aid] & chiavi
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
        chiavi = _chiavi_unita(w, klass)
        per_materia = defaultdict(list)
        for aid in w.placement:
            if w.tokens[aid] & chiavi:
                per_materia[w.act(aid).subject_id].append(aid)
        adiacenti = set()
        for aid, (day, slot) in w.placement.items():
            if not (w.tokens[aid] & chiavi):
                continue
            fine = slot + w.act(aid).duration_slots
            for altro, (day2, slot2) in w.placement.items():
                if (altro != aid and day2 == day and slot2 == fine
                        and w.tokens[altro] & chiavi):
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
    vincolante).

    Le occorrenze si filtrano con `_chiavi_unita` (Task 15a): il filtro sul
    solo `klass.pk` perdeva le attivita' legate alla sola parte, che il
    checker invece vede — su A la perdita allargava la guardia (innocuo), su
    B la stringeva, e poteva scartare righe violabili."""
    grid = w.env["grid"]
    width = grid.slots_per_day
    creata = 0
    for klass in w.env["classes"]:
        chiavi = _chiavi_unita(w, klass)
        per_materia = defaultdict(list)
        for aid in w.placement:
            if w.tokens[aid] & chiavi:
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

    Come `_derive_weekly_order`, le occorrenze si filtrano con
    `_chiavi_unita` (Task 15a): il filtro sul solo `klass.pk` perdeva le
    attivita' legate alla sola parte, che il checker invece vede."""
    grid = w.env["grid"]
    n = grid.days_per_cycle * 2
    creata = 0
    for klass in w.env["classes"]:
        chiavi = _chiavi_unita(w, klass)
        per_materia = defaultdict(list)
        for aid in w.placement:
            if w.tokens[aid] & chiavi:
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

    Come `_derive_weekly_order`/`_derive_imposed_succession`, le occorrenze
    si filtrano con `_chiavi_unita` (Task 15a): il filtro sul solo
    `klass.pk` perdeva le attivita' legate alla sola parte, che il checker
    invece vede. ⚠ Qui la perdita era particolarmente cattiva: due attivita'
    su parti diverse possono cadere nella **stessa** mezza giornata, e allora
    lo scarto minimo osservato e' zero — cioe' nessuna riga derivabile.
    Vedendone una sola, il derivatore avrebbe creato una riga che il
    testimone stesso viola."""
    grid = w.env["grid"]
    n = grid.days_per_cycle * 2
    creata = 0
    for klass in w.env["classes"]:
        chiavi = _chiavi_unita(w, klass)
        per_materia = defaultdict(list)
        for aid in w.placement:
            if w.tokens[aid] & chiavi:
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
    testimone: non tocca `_make_activities`); (iii) finche' esiste una coppia a distanza <= 0, togliere la
    sede, greedy, a una delle due (converge sempre: ogni rimozione riduce di
    uno il numero di attivita' con sede, quindi il ciclo e' limitato da
    `len(w.activities)`); (iv) `needed` = minimo superstite, vacua
    (`return 0`) se non sopravvive nessuna coppia. Misurato qui (giro di
    correzione 1, builder reso no-op, 15 seed, piu' esecuzioni per il non
    determinismo di CP-SAT): **12-14/15** a seconda dell'esecuzione, contro
    l'1/15 della formulazione osservativa — in linea con la misura della
    review (12/15).

    ⚠ **Correzione al Task 17**: «nessun altro derivatore ne risente» era
    scritto qui, ed e' falso. Riassegnare le sedi non tocca ne' la griglia ne'
    l'occupazione — vero — ma le sedi sono esattamente cio' che
    `max_site_changes` conta, quindi una riga gia' derivata da
    `_derive_max_site_changes` diventa violata. Invisibile finche' il banco
    provava una famiglia per volta. Vedi `MUTANTI` e
    `run_tutte_le_famiglie`."""
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


# --- i quattro PARTS_* (Task 15b) ---------------------------------------

_PARTE, _CLASSE = 1, 0


def _etichetta_parts(w, aid):
    """`_is_class_level` del checker (`subject_constraints.py`): l'attivita'
    e' «a classe intera» se **qualcuna** delle sue chiavi di occupazione e'
    una Resource di tipo CLASS. Nel banco le sole Resource di tipo CLASS sono
    le due classi di `_school`, quindi il test si riduce all'intersezione con
    i loro pk.

    La codifica numerica (`_CLASSE = 0`, `_PARTE = 1`) riproduce
    l'ordinamento del checker, che ordina tuple `(fascia, etichetta, id)` con
    la stringa `"class"` prima di `"part"`: a parita' di fascia la classe
    viene prima."""
    classi_pk = {k.pk for k in w.env["classes"]}
    return _CLASSE if (w.tokens[aid] & classi_pk) else _PARTE


def _secchi_parts(w, aids, rep, kind):
    """secchio → [(fascia, etichetta)] delle occorrenze **piazzate** attive
    nella firma `rep`. `kind` e' `"day"` per PARTS_BEFORE_CLASS,
    PARTS_AFTER_CLASS e PARTS_BEFORE_OR_AFTER_CLASS_AB, `"half"` per
    PARTS_BEFORE_OR_AFTER_CLASS_H — ⚠ e' l'unica differenza fra i due
    omogenei (`PartsHomogeneousHalfChecker` sovrascrive `bucket()`)."""
    grid = w.env["grid"]
    secchi = defaultdict(list)
    for aid in aids:
        if rep not in w.weeks_of[aid]:
            continue
        day, slot = w.placement[aid]
        bucket = (day if kind == "day"
                  else day * 2 + (slot >= grid.morning_end_slot))
        secchi[bucket].append((slot, _etichetta_parts(w, aid)))
    return secchi


def _parts_viola(tipo, voci):
    """Mirror di `_PartsOrder.violations` su un solo secchio, **scritto per
    conto proprio** e non importato da
    `domain/solver/builders/subject_parts.py`: un derivatore che chiedesse al
    builder «e' violato?» non potrebbe piu' accorgersi di un builder che
    sbaglia la semantica — direbbe di si' e di no esattamente quando lo dice
    lui."""
    voci = sorted(voci)
    parti = [s for s, lab in voci if lab == _PARTE]
    classi = [s for s, lab in voci if lab == _CLASSE]
    if not parti or not classi:
        return False          # il checker salta i secchi senza entrambe
    if tipo == ST.PARTS_BEFORE_CLASS:
        return max(parti) > min(classi)
    if tipo == ST.PARTS_AFTER_CLASS:
        return min(parti) < max(classi)
    etichette = [lab for _, lab in voci]
    return sum(x != y for x, y in zip(etichette, etichette[1:])) > 1


def _larghezza_secchio(w, kind, bucket):
    """Quante fasce d'inizio distinte entrano in quel secchio. Serve alla
    guardia di violabilita' dei due **omogenei**: due sole occorrenze non
    possono mai avere piu' di una transizione, quindi un secchio che non
    regge tre occorrenze rende la riga inviolabile per aritmetica.

    Due occorrenze non possono condividere la fascia dentro un'unita': una
    lezione a classe intera occupa la classe **e tutte le sue parti**, e due
    lezioni a classe intera occupano la classe — quindi confliggono
    sull'occupazione. Il numero di occorrenze in un secchio e' percio'
    limitato dal numero di fasce del secchio."""
    grid = w.env["grid"]
    if kind == "day":
        return grid.slots_per_day
    return (grid.morning_end_slot if bucket % 2 == 0
            else grid.slots_per_day - grid.morning_end_slot)


def _unita_parts(w):
    """Le unita' su cui provare a derivare una riga, con la loro espansione
    in chiavi di occupazione: `(kwargs per SubjectConstraint, chiavi)`.

    Due forme, non una. Sulla **classe** l'espansione e' `_chiavi_unita`
    (la classe piu' tutte le sue parti, come `_unit_keys` del checker), e
    la riga vede entrambe le parti insieme. Sulla **parte** l'espansione e'
    la sola parte (stessa lettura di `_unit_keys` per `class_part`): la riga
    vede l'attivita' di quella parte piu' tutte le attivita' a classe intera,
    che occupano ogni parte della classe e quindi entrano nell'unita'.

    La seconda forma non e' un di piu' cosmetico. Una riga sulla classe si
    scarta appena **una** delle due parti smentisce l'ordine in un qualunque
    secchio; la riga sulla singola parte sopravvive lo stesso, e il potere
    vincolante misurato ne dipende (i numeri nel report). In piu' e' l'unica
    forma che porta il ramo `class_part` di `_unit_keys` dentro il banco."""
    unita = [({"school_class": klass}, _chiavi_unita(w, klass))
             for klass in w.env["classes"]]
    unita += [({"class_part": part}, frozenset({part.pk}))
              for part in w.env["parts"]]
    return unita


def _riga_parts_ammissibile(w, tipo, kind, chiavi, subject_pk):
    """La riga `(unita', materia)` si puo' creare su questo testimone?

    Due condizioni, entrambe **per firma di settimana**, perche' e' cosi' che
    il checker guarda l'orario (`check_schedule` costruisce uno
    `ScheduleState` per firma):

    - il testimone la soddisfa in **ogni** firma e in ogni secchio (basta un
      secchio violato a scartarla: sarebbe un fallimento al passo 1 di
      `run_family`, e la colpa sarebbe del derivatore, non del builder);
    - e' **violabile**: almeno un secchio, in almeno una firma, con
      entrambe le etichette. Per i due omogenei serve anche che tre
      occorrenze ci stiano davvero (tre attivita' co-attive e un secchio
      largo almeno tre fasce): «piu' di una transizione» su due occorrenze e'
      aritmeticamente impossibile."""
    aids = [aid for aid in w.placement
            if w.tokens[aid] & chiavi
            and w.act(aid).subject_id == subject_pk]
    if not aids:
        return False
    omogeneo = tipo in (ST.PARTS_BEFORE_OR_AFTER_CLASS_H,
                        ST.PARTS_BEFORE_OR_AFTER_CLASS_AB)
    violabile = False
    for rep, _ in w.signatures:
        attive = sum(1 for aid in aids if rep in w.weeks_of[aid])
        for bucket, voci in _secchi_parts(w, aids, rep, kind).items():
            if len({lab for _, lab in voci}) < 2:
                continue
            if _parts_viola(tipo, voci):
                return False
            if not omogeneo or (attive >= 3
                                and _larghezza_secchio(w, kind, bucket) >= 3):
                violabile = True
    return violabile


def _sintonizza_parti(w, tipo, kind):
    """Formulazione **«densa»** (Ruling 34, come `_derive_site_transition`):
    il derivatore **costruisce** lo scenario invece di limitarsi a osservarlo.

    Osservando soltanto, questa famiglia e' quasi sempre vacua e non per
    colpa del derivatore: `_make_activities` crea **una** attivita' per
    parte e le pesca la materia a caso fra tre, quindi la probabilita' che
    l'attivita' di parte e una lezione a classe intera della **stessa**
    materia finiscano nello stesso secchio del testimone e' bassa. Misurato
    prima di questa correzione: 15 dei 20 casi del banco (4 famiglie x 5
    seed) saltavano per derivazione vacua.

    La riparazione e' minima e sta tutta dentro il derivatore: si prova a
    riassegnare la **materia** dell'attivita' di ogni parte, e si tiene la
    prima assegnazione che rende ammissibile la riga sull'unita' di quella
    parte. Non si tocca `_make_activities` (cambierebbe il testimone di tutte
    le altre famiglie a parita' di seed), non si sposta nessun piazzamento e
    non cambia nessuna chiave di occupazione: la materia non entra ne' nella
    griglia ne' nell'occupazione, quindi il testimone resta valido esattamente
    com'era. Se nessuna materia funziona, si rimette quella originale.

    Il monte ore del `Service` segue la materia, cosi' la fixture non
    accumula uno scarto di copertura in piu' di quello gia' dichiarato in
    testa a questo modulo (Ruling 102).

    ⚠ **Correzione al Task 17**: «il testimone resta valido esattamente com'era»
    vale per la griglia e per l'occupazione, **non** per le righe gia' derivate
    da altre famiglie. La materia e' cio' su cui ogni `SubjectConstraint` e'
    ancorata, quindi riassegnarla fa violare le righe di
    `subject_half_day_gap`, `subject_imposed_succession` e
    `subject_max_hours_day/half_day`. Vedi `MUTANTI` e
    `run_tutte_le_famiglie`."""
    classi_pk = {k.pk for k in w.env["classes"]}
    for part in w.env["parts"]:
        aids = [aid for aid in w.placement
                if part.pk in w.tokens[aid] and not (w.tokens[aid] & classi_pk)]
        if not aids:
            continue
        act = w.act(aids[0])
        originale = act.subject_id
        chiavi = frozenset({part.pk})
        piano = part.effective_study_plan
        for subject in w.env["subjects"]:
            _sposta_servizio(piano, act.subject_id, subject.pk,
                             act.duration_minutes)
            act.subject = subject
            act.save()
            if _riga_parts_ammissibile(w, tipo, kind, chiavi, subject.pk):
                break
        else:
            _sposta_servizio(piano, act.subject_id, originale,
                             act.duration_minutes)
            act.subject_id = originale
            act.save()


def _sposta_servizio(plan, da_subject, a_subject, minuti):
    if da_subject == a_subject:
        return
    vecchio = Service.objects.filter(study_plan=plan, subject_id=da_subject).first()
    if vecchio is not None:
        vecchio.class_minutes = max(0, vecchio.class_minutes - minuti)
        vecchio.save()
    nuovo, _ = Service.objects.get_or_create(
        study_plan=plan, subject_id=a_subject, defaults={"class_minutes": 0})
    nuovo.class_minutes += minuti
    nuovo.save()


def _derive_parts(w, tipo, kind):
    """Il derivatore comune ai quattro `PARTS_*`.

    ⚠ **Il derivatore del piano non restituisce niente**: con `None`,
    `run_family` fa `if not potere: pytest.skip(...)` e tutte e quattro le
    famiglie salterebbero su **ogni** seed — venti test verdi che non
    provano nulla, la forma piu' pura del successo travestito che la
    convenzione sul potere vincolante esiste per impedire. Riscritto:

    - filtro sull'unita' con `_chiavi_unita(w, klass)`, non su `klass.pk`:
      le attivita' legate alla **sola parte** sono meta' del vincolo, e col
      filtro sul solo pk della classe sparirebbero — un derivatore che non
      le vede non vede mai entrambe le etichette e resta vacuo per sempre.
      Le unita' provate sono due (`_unita_parts`): la classe e la singola
      parte;
    - **per firma di settimana**: un secchio si valuta con le sole attivita'
      attive in quella firma, perche' e' cosi' che il checker lo vede
      (`check_schedule` costruisce uno `ScheduleState` per firma). Una riga
      si crea solo se il testimone la soddisfa in **ogni** firma;
    - **guardia di violabilita'**: serve almeno un secchio, in almeno una
      firma, con **entrambe** le etichette. Senza, il checker salterebbe
      ogni secchio e la riga sarebbe inviolabile per costruzione — una riga
      creata che nessun piazzamento puo' violare, contata dal banco come un
      successo. Per i due **omogenei** la condizione non basta: «piu' di una
      transizione» chiede almeno **tre** occorrenze nello stesso secchio,
      quindi servono anche tre attivita' co-attive in quella firma e un
      secchio largo almeno tre fasce (`_larghezza_secchio`). Trovata
      misurando: senza, al seed 2 la famiglia `_H` creava due righe che
      nessun piazzamento poteva violare — la meta' giornata del banco puo'
      essere larga due fasce;
    - **accumula** su tutte le unita' e tutte le materie, e restituisce il
      conteggio.

    Le due condizioni stanno in `_riga_parts_ammissibile`; la formulazione
    «densa» che rende il banco non vacuo sta in `_sintonizza_parti`.

    Nel banco solo la prima classe ha parti, quindi le righe sulla seconda
    non superano mai la guardia di violabilita': e' voluto, ed e' anche il
    caso di controllo (una classe monolitica non puo' violare un vincolo
    d'ordine fra parti e classe intera).

    I numeri misurati — righe create, testimoni violati, seed mordenti col
    builder spento — stanno nel report del task, non qui (Ruling 50)."""
    _sintonizza_parti(w, tipo, kind)
    creata = 0
    for unita, chiavi in _unita_parts(w):
        for subject in w.env["subjects"]:
            if not _riga_parts_ammissibile(w, tipo, kind, chiavi, subject.pk):
                continue
            SubjectConstraint.objects.create(
                subject_a=subject, subject_b=subject, type=tipo, **unita)
            creata += 1
    return creata


@deriver(ST.PARTS_BEFORE_CLASS, {"subject_parts_order"})
def _derive_parts_before(w):
    return _derive_parts(w, ST.PARTS_BEFORE_CLASS, "day")


@deriver(ST.PARTS_AFTER_CLASS, {"subject_parts_order"})
def _derive_parts_after(w):
    return _derive_parts(w, ST.PARTS_AFTER_CLASS, "day")


@deriver(ST.PARTS_BEFORE_OR_AFTER_CLASS_H, {"subject_parts_order"})
def _derive_parts_homogeneous_half(w):
    """⚠ `_H` = **mezza giornata**: `PartsHomogeneousHalfChecker` sovrascrive
    `bucket()` con `_half`, mentre `_PartsOrder.bucket` torna `pl.day`."""
    return _derive_parts(w, ST.PARTS_BEFORE_OR_AFTER_CLASS_H, "half")


@deriver(ST.PARTS_BEFORE_OR_AFTER_CLASS_AB, {"subject_parts_order"})
def _derive_parts_homogeneous_day(w):
    """⚠ `_AB` = **giornata**: eredita il `bucket()` della base."""
    return _derive_parts(w, ST.PARTS_BEFORE_OR_AFTER_CLASS_AB, "day")


# --- il peso didattico (Task 16) ----------------------------------------

def _unita_studente(w, aid):
    """Le unita'-studente di un'attivita', con la regola del checker
    (`domain/analysis/checkers/weight.py::_student_keys`): le parti presenti
    nei token, o la classe se la classe non ha partizioni. Qui si legge dalla
    fixture invece che da `state.kinds` perche' le parti e le classi del banco
    sono note per costruzione — ma il criterio e' lo stesso, e in particolare
    un'attivita' a **classe intera** della classe partizionata pesa sulle sue
    **due parti**, non sulla classe."""
    parti = {p.pk for p in w.env["parts"]} & w.tokens[aid]
    if parti:
        return sorted(parti)
    return sorted({k.pk for k in w.env["classes"]} & w.tokens[aid])


@deriver("structural:didactic_weight", {"weight_day", "weight_morning",
                                        "weight_afternoon", "weight_week"})
def _derive_weight(w):
    """Accende i tetti d'istituto sui valori osservati nel testimone: senza
    questo, il banco proverebbe un builder spento (in una base reale i quattro
    tetti sono tutti a «nessuno»).

    Tre scelte che il derivatore ingenuo sbaglia:

    1. **Si somma sulle unita'-studente**, non su tutti i token. Sommare sui
       docenti sarebbe una sovrastima, e una sovrastima qui non e' innocua:
       produce un tetto piu' largo del massimo che un'unita'-studente possa
       mai raggiungere, cioe' un tetto **inviolabile** — che il banco
       conterebbe come successo.
    2. **Il massimo e' fra le firme**, non sull'unione: il checker valuta uno
       `ScheduleState` per firma, e il massimo sull'unione sarebbe piu' largo
       e quindi piu' debole.
    3. **Guardia di violabilita'**: un tetto che nessun piazzamento puo'
       superare e' vacuo. Il limite superiore di un secchio e' `min(peso
       totale dell'unita' in quella firma, peso massimo per fascia x fasce del
       secchio)` — un'unita'-studente non puo' essere occupata da due
       attivita' nella stessa fascia, quindi ogni fascia vale al massimo il
       `didactic_weight` piu' alto fra le sue attivita'. ⚠ Per la **mezza
       giornata** le fasce non sono la sua larghezza: il checker attribuisce
       il peso alla meta' in cui l'attivita' **comincia**, quindi una che
       comincia nell'ultima fascia del mattino pesa sul mattino occupando il
       pomeriggio. Vedi il commento nel corpo. Un tetto pari o superiore a
       quel limite non si accende.

    ⚠ **Il tetto settimanale non e' derivabile da un testimone, e la ragione
    e' strutturale**: `AddExactlyOne` obbliga a piazzare **tutte** le
    attivita', quindi il peso settimanale di un'unita' e' lo stesso in ogni
    soluzione — e' il totale delle sue attivita' attive in quella firma. Il
    massimo osservato coincide col totale della peggiore unita', e nessun
    piazzamento potra' mai superarlo: qualunque tetto settimanale soddisfatto
    dal testimone e' soddisfatto da ogni soluzione. Lo stesso vale per il
    tetto della classe, che e' un tetto settimanale. Le due semantiche sono
    percio' coperte da test scritti a mano in `tests/test_solver_weight.py`,
    in forma avversaria.

    Restituisce quanti tetti ha davvero acceso: zero fa saltare il seed,
    invece di spacciarlo per un successo travestito."""
    grid = w.env["grid"]
    # Pesi didattici diversi da 1: col default il peso coincide con la durata,
    # e un builder che ignorasse `didactic_weight` passerebbe il banco.
    for subject in w.env["subjects"]:
        subject.didactic_weight = w.rng.randint(1, 3)
        subject.save()
    pesi_materia = {s.pk: s.didactic_weight for s in w.env["subjects"]}

    def peso(aid):
        act = w.act(aid)
        return pesi_materia[act.subject_id] * act.duration_slots

    larghezze = {"day": grid.slots_per_day,
                 "morning": grid.morning_end_slot,
                 "afternoon": grid.slots_per_day - grid.morning_end_slot}
    massimi = {"day": 0, "morning": 0, "afternoon": 0}
    limiti = {"day": 0, "morning": 0, "afternoon": 0}
    for rep, _ in w.signatures:
        per_day, per_half = defaultdict(int), defaultdict(int)
        totale, max_peso, max_durata = (defaultdict(int), defaultdict(int),
                                        defaultdict(int))
        for aid, (day, slot) in w.placement.items():
            if rep not in w.weeks_of[aid]:
                continue
            act = w.act(aid)
            p = peso(aid)
            meta = "afternoon" if slot >= grid.morning_end_slot else "morning"
            for key in _unita_studente(w, aid):
                per_day[(key, day)] += p
                per_half[(key, day, meta)] += p
                totale[key] += p
                max_peso[key] = max(max_peso[key], pesi_materia[act.subject_id])
                max_durata[key] = max(max_durata[key], act.duration_slots)
        massimi["day"] = max(massimi["day"], max(per_day.values(), default=0))
        for nome in ("morning", "afternoon"):
            massimi[nome] = max(massimi[nome], max(
                (v for (_k, _d, m), v in per_half.items() if m == nome),
                default=0))
        for key, tot in totale.items():
            for nome, larghezza in larghezze.items():
                # Fasce al massimo occupabili nel secchio da attivita' che vi
                # **cominciano**. Per la giornata sono le sue fasce. Per la
                # mezza giornata **non** lo sono: un'attivita' che comincia
                # nell'ultima fascia del mattino pesa tutta sul mattino ma
                # occupa anche il pomeriggio (il checker guarda `start_slot`),
                # quindi la finestra va allargata di `durata - 1`. Senza questa
                # correzione il limite non e' un maggiorante: misurato sul
                # seed 9, mattino osservato 8 contro un «limite» di 6.
                if larghezza == 0:
                    continue
                fasce = larghezza + (0 if nome == "day"
                                     else max_durata[key] - 1)
                limiti[nome] = max(limiti[nome],
                                   min(tot, max_peso[key] * fasce))

    settings, _ = InstituteSettings.objects.get_or_create(pk=1)
    accesi = 0
    for campo, secchio in (("max_weight_day", "day"),
                           ("max_weight_morning", "morning"),
                           ("max_weight_afternoon", "afternoon")):
        valore = massimi[secchio]
        if valore and valore < limiti[secchio]:
            setattr(settings, campo, valore)
            accesi += 1
    settings.save()
    return accesi
