"""I punti in cui un verdetto dipendeva dall'**ordine d'inserimento** invece
che dall'orario.

`ScheduleState.occupancy` e' un `defaultdict(list)` e `state.placed` un `dict`:
entrambi conservano l'ordine in cui `build()` ha visto le attivita', cioe'
l'ordine del queryset `Activity` — un fatto del database, non dell'orario.
Tre checker lo lasciavano trapelare nel verdetto: non nel *valore* di una
quantita', ma in **quale** finding esce e **quali attivita'** nomina.

Un artefatto del genere non e' una semantica: lo stesso orario, ricostruito
con le stesse righe, dava due risposte diverse a seconda dei pk. Finche'
restava tale non era nemmeno **traducibile** —
`domain/solver/builders/time_sites.py` si era fermato davanti a questo per
`MaxSiteChangesBuilder`, dichiarandolo invece di replicarlo.

⚠ E i punti erano **quattro**: l'ultimo test qui sta nel solver, dove lo
stesso appiattimento calcolava il residuo di ADR-018 e regalava al modello un
cambio di sede che il checker non perdona. Vive in questo file e non fra i
test del solver perche' e' lo stesso difetto, e separarlo lo renderebbe di
nuovo invisibile.

I test si costruiscono lo stesso orario due volte, nei due ordini, e
pretendono la stessa risposta. E' la forma minima: non asseriscono *quale*
sia la risposta giusta — quella la decidono i checker, nei loro docstring —
asseriscono che ce ne sia **una sola**.
"""
import pytest

from domain.analysis.checkers.subject_constraints import _placed_of
from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.analysis.state import ScheduleState
from domain.models import (
    Activity, ClassPart, ClassPartition, InstituteSettings,
    ResourceTimeConstraint, Site, Subject, SubjectConstraint,
)
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


def _chiavi(schedule, code):
    return {f.key for f in check_schedule(schedule)
            if f.code == code and f.severity == Severity.HARD}


def _griglia(env, days, slots):
    env["grid"].days_per_cycle = days
    env["grid"].slots_per_day = slots
    env["grid"].morning_end_slot = slots
    env["grid"].save()


def _due_sedi_sulla_stessa_fascia(env, invertito, *, cap_transizione):
    """Una chiave a capienza cumulativa 2 con due sedi diverse sulla stessa
    fascia, piu' una terza attivita' sulla fascia dopo. `invertito` scambia
    l'ordine di **creazione** delle due simultanee, che e' l'ordine in cui
    `state.occupancy` le elenca."""
    _griglia(env, 1, 2)
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": cap_transizione})
    klass = env["klass"]
    klass.simultaneous_capacity = 2
    klass.save()

    a_site = Site.objects.create(name="A")
    b_site = Site.objects.create(name="B")
    prima, seconda = (b_site, a_site) if invertito else (a_site, b_site)

    sim1 = make_activity(env["subject"], classes=[klass], site=prima)
    sim2 = make_activity(env["subject"], classes=[klass], site=seconda)
    terza = make_activity(env["subject"], classes=[klass], site=a_site)
    place(env["schedule"], sim1, 0, 0)
    place(env["schedule"], sim2, 0, 0)
    place(env["schedule"], terza, 0, 1)


@pytest.mark.parametrize("invertito", [False, True])
def test_max_site_changes_non_dipende_dall_ordine_di_inserimento(invertito):
    """Sequenza letta come [A, B, A] → 2 cambi; come [B, A, A] → 1. Con un
    tetto di 1 la stessa giornata e' una volta in violazione e una volta no,
    e a decidere e' il pk delle due attivita' simultanee."""
    env = mini_school()
    _due_sedi_sulla_stessa_fascia(env, invertito, cap_transizione=0)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_SITE_CHANGES, params={"per_day": 1})

    assert _chiavi(env["schedule"], "max_site_changes") == set()


@pytest.mark.parametrize("invertito", [False, True])
def test_site_transition_non_dipende_dall_ordine_di_inserimento(invertito):
    """Stessa istanza, altro checker. Letta come [A@0, B@0, A@1] le coppie
    adiacenti sono (A,B) e (B,A): due violazioni. Letta come [B@0, A@0, A@1]
    sono (B,A) e (A,A): una sola. La seconda coppia esiste o no a seconda
    dei pk."""
    env = mini_school()
    _due_sedi_sulla_stessa_fascia(env, invertito, cap_transizione=2)

    chiavi = _chiavi(env["schedule"], "site_transition")
    # La simultaneita' fra sedi diverse e' sempre una violazione (gap -1), e
    # il passaggio dalla fascia 0 alla 1 la e' anch'esso: gap 0 < 2. Il numero
    # e' quello che non deve dipendere dall'ordine.
    assert len(chiavi) == 2, sorted(chiavi)


def _sdoppiamento_in_pareggio(env):
    """Due occorrenze della stessa materia su parti diverse della **stessa**
    partizione, sulla stessa cella: uno sdoppiamento, che non e' un conflitto
    di occupazione. Piu' una seconda materia prima di loro, che rende la riga
    `WEEKLY_ORDER` violata."""
    _griglia(env, 1, 2)
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="Lingue")
    p1 = ClassPart.objects.create(partition=partizione, name="L1")
    p2 = ClassPart.objects.create(partition=partizione, name="L2")
    altra = Subject.objects.create(code="MAT", name="Matematica",
                                   discipline=env["discipline"])

    x1 = make_activity(env["subject"], parts=[p1])
    x2 = make_activity(env["subject"], parts=[p2])
    y = make_activity(altra, classes=[env["klass"]])
    place(env["schedule"], y, 0, 0)
    place(env["schedule"], x1, 0, 1)
    place(env["schedule"], x2, 0, 1)

    SubjectConstraint.objects.create(
        school_class=env["klass"], type=SubjectConstraint.Type.WEEKLY_ORDER,
        subject_a=env["subject"], subject_b=altra)
    return x1, x2, y


def test_weekly_order_non_dipende_dall_ordine_di_state_placed():
    """Il tie-break di `_placed_of`. `sorted` per `(day, start_slot)` e'
    **stabile**, quindi a parita' esatta l'argmin — che il finding **nomina** —
    e' l'occorrenza che il queryset ha restituito per prima. Il valore
    aggregato non cambia: cambia solo *chi* viene incolpato, cioe' la
    `Finding.key`.

    ⚠ Qui l'ordine si scambia **sullo stato**, non creando le attivita' al
    contrario: e' quello il rischio vero. Un queryset senza `order_by`
    esplicito non promette nessun ordine, e lo stesso database puo' restituire
    le stesse righe in ordine diverso da un'esecuzione all'altra. Un test che
    scambiasse i pk misurerebbe un'altra cosa — a pk scambiati e' scambiato
    anche *cosa* c'e' dentro ciascuno."""
    env = mini_school()
    x1, x2, _ = _sdoppiamento_in_pareggio(env)

    state = ScheduleState.build(env["schedule"])
    keys = state.subject_rows[0][1]
    prima = _placed_of(state, keys, env["subject"].id)
    state.placed = dict(reversed(list(state.placed.items())))
    dopo = _placed_of(state, keys, env["subject"].id)

    assert [p.activity_id for p in prima] == [p.activity_id for p in dopo]
    assert {x1.id, x2.id} == {p.activity_id for p in prima}


def test_il_consumo_congelato_dei_cambi_segue_la_stessa_regola():
    """⚠ **Il builder contava i cambi delle congelate a modo suo, e il modo
    era quello vecchio.** `_frozen_site_changes` (`domain/solver/builders/
    time_sites.py`) e' il residuo di ADR-018: quanti cambi le sole congelate
    hanno gia' contratto, cioe' il pavimento sotto cui il tetto non scende.
    Appiattiva `by_cell` in una sequenza, quindi due congelate di sede diversa
    sulla **stessa** fascia gli valevano un cambio — mentre per il checker,
    che dentro una fascia non fa viaggiare nessuno, ne valgono zero.

    Un consumo sovrastimato non e' una svista simmetrica: **alza** il tetto
    clampato e regala al solver un cambio che il checker non gli perdona.
    Qui il tetto e' `per_day = 0`, le congelate non producono cambi, e
    l'unica libera — ovunque la si metta — ne produce uno: il modello deve
    dire di no. Col conteggio vecchio il consumo valeva 1, il tetto diventava
    `max(0, 1) = 1` e il solver piazzava; `check_schedule` sulla soluzione
    riportava un `max_site_changes` **nuovo** che il solver non aveva visto,
    cioe' l'oracolo differenziale rotto."""
    env = mini_school()
    _griglia(env, 1, 3)
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    klass = env["klass"]
    klass.simultaneous_capacity = 2
    klass.save()

    a_site = Site.objects.create(name="A")
    b_site = Site.objects.create(name="B")
    congelate = [
        make_activity(env["subject"], classes=[klass], site=sede,
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
        for sede in (a_site, b_site)
    ]
    for act in congelate:
        place(env["schedule"], act, 0, 0)
    make_activity(env["subject"], classes=[klass], site=a_site)
    ResourceTimeConstraint.objects.create(
        resource=klass, type=T.MAX_SITE_CHANGES, params={"per_day": 0})

    # La baseline e' pulita: le due congelate simultanee non sono un cambio.
    assert _chiavi(env["schedule"], "max_site_changes") == set()

    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats
