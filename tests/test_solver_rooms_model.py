"""Il modello della seconda fase: capienza, firme di settimana, ADR-018."""
import pytest
from ortools.sat.python import cp_model

from domain.models import Activity, Room
from domain.solver.rooms import build_room_model
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _risolvi(schedule, **kw):
    """`build_room_model` non porta obiettivo (e' compito di chi risolve, non
    del modello grezzo — vedi il suo docstring). Qui, per i test che vogliono
    osservare il modello da solo con `allow_unassigned=True`, la preferenza
    «assegna il possibile» e' locale a questo fixture di test: senza, «rinuncia
    a tutti» e' feasible quanto «assegna il possibile» e CP-SAT senza obiettivo
    restituisce il primo. Con `allow_unassigned=False` `ctx.assigned` resta
    vuoto (e' `AddExactlyOne` a decidere), quindi la riga e' un no-op."""
    model, ctx = build_room_model(schedule, **kw)
    if ctx.assigned:
        model.Maximize(sum(ctx.assigned.values()))
    solver = cp_model.CpSolver()
    return solver.Solve(model), solver, ctx


def test_due_attivita_nella_stessa_cella_non_stanno_in_un_aula_da_uno():
    """La regola della casa: si **forza** la violazione e si attende
    INFEASIBLE, invece di risolvere e guardare dove e' finita."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    a = make_activity(env["subject"], rooms=[lab])
    b = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE


def test_la_capienza_due_ne_ammette_due():
    env = mini_school()
    pal = Room.objects.create(name="PALESTRA", simultaneous_capacity=2)
    a = make_activity(env["subject"], rooms=[pal])
    b = make_activity(env["subject"], rooms=[pal])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_con_la_rinuncia_ammessa_una_resta_senza_aula():
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    a = make_activity(env["subject"], rooms=[lab])
    b = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    place(env["schedule"], b, 0, 0)
    stato, solver, ctx = _risolvi(env["schedule"])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assegnate = sum(solver.Value(v) for v in ctx.assigned.values())
    assert assegnate == 1


def test_settimane_disgiunte_non_competono():
    """Due attivita' nella stessa cella su settimane disgiunte condividono
    un'aula a capienza 1: le firme sono una dimensione, non un dettaglio."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    pari = make_activity(env["subject"], rooms=[lab], mask=0b0101)
    dispari = make_activity(env["subject"], rooms=[lab], mask=0b1010)
    place(env["schedule"], pari, 0, 0)
    place(env["schedule"], dispari, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_la_firma_successiva_alla_prima_non_si_salta():
    """Il ciclo su `ctx.signatures` in `_post_capacity` deve visitare
    **tutte** le firme, non fermarsi alla prima.

    Le due attivita' sono attive solo in settimana 1 (`mask=0b0010`): la
    settimana 0 — la prima firma incontrata scorrendo le settimane da zero,
    dato che ne' `prima` ne' `seconda` sono attive li' — non porta nessuna
    attivita' e quindi nessun conflitto. Il vincolo di capienza vero esiste
    **solo** nella firma della settimana 1, la seconda incontrata: un ciclo
    che si fermasse a `ctx.signatures[0]` non lo vedrebbe mai, e il modello
    risulterebbe erroneamente feasible."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    prima = make_activity(env["subject"], rooms=[lab], mask=0b0010)
    seconda = make_activity(env["subject"], rooms=[lab], mask=0b0010)
    place(env["schedule"], prima, 0, 0)
    place(env["schedule"], seconda, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE


def test_adr018_due_immobili_che_saturano_non_bloccano_il_modello():
    """`INFEASIBLE` che nasce dal vietare un peggioramento e' ammesso; quello
    che nasce dal **pretendere una riparazione** no. Due immobili che saturano
    da sole una palestra sono una violazione gia' scritta: la fase assegna il
    resto — su un'altra aula — e il checker la nomina.

    ⚠ `libera` dichiara **anche** `pal` fra le candidate apposta: se non lo
    facesse, `pal` non comparirebbe mai in `per_cella` (nessuna libera la
    tocca) e il test non discriminerebbe fra residuo e tetto grezzo — e'
    esattamente cosi' che la prima stesura di questo test passava anche con la
    capienza non clampata. L'assert sul letterale `ctx.y[(libera.id, pal.pk)]`
    e' la parte che conta: un bare `assigned[libera.id] == 1` varrebbe anche
    se la libera avesse preso `pal` invece di `altra`, cosa che il tetto
    grezzo permetterebbe (nessuna riga di capienza verrebbe postata, perche'
    con un solo letterale libero su quella cella `len(lits) <= tetto` e'
    sempre vero)."""
    env = mini_school()
    pal = Room.objects.create(name="PALESTRA", simultaneous_capacity=1)
    altra = Room.objects.create(name="ALTRA", simultaneous_capacity=1)
    for _ in range(2):
        bloccata = make_activity(env["subject"], rooms=[pal],
                                 immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], bloccata, 0, 0, room=pal)
    libera = make_activity(env["subject"], rooms=[pal, altra])
    place(env["schedule"], libera, 0, 0)
    stato, solver, ctx = _risolvi(env["schedule"])
    assert stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(ctx.assigned[libera.id]) == 1
    assert solver.Value(ctx.y[(libera.id, pal.pk)]) == 0


def test_il_dominio_vuoto_con_la_rinuncia_vietata_e_infattibile():
    env = mini_school()
    from domain.models import ResourceUnavailability
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    stato, _, _ = _risolvi(env["schedule"], allow_unassigned=False)
    assert stato == cp_model.INFEASIBLE
