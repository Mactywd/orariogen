"""HALF_DAY_GAP: scarto minimo fra occorrenze di materia, in mezze
giornate (`domain/solver/builders/subject_order.py`, `HalfDayGapBuilder`).

⚠ Niente `test_half_day_gap_sul_banco` qui (Ruling 16, settima applicazione
della stessa correzione — vedi `tests/test_solver_subject_order.py`):
`tests/solver_harness.py` registra `_derive_half_day_gap` sotto
`T.HALF_DAY_GAP`, e `tests/test_solver_witness.py::test_famiglia` gia'
parametrizza su `sorted(DERIVERS) x [1..5]` — i cinque seed della famiglia
esistono in automatico appena il derivatore e' registrato. Scriverli anche
qui sarebbe un duplicato esatto."""
import pytest
from ortools.sat.python import cp_model

from domain.models import Subject, SubjectConstraint
from domain.solver.model import build_model
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


def test_half_day_gap_a_uguale_b_morde():
    """A = B, coppia forzata a distanza < param: due occorrenze nelle mezze
    giornate 0 e 1 (giorno 0, `slot` 0 e 4), `param = 2`. Distanza reale 1,
    sotto la soglia: crossed = same = True (righe A = B sono sempre
    incrociate per il checker), quindi HalfDayGapChecker emetterebbe il
    finding. Forma avversaria (Ruling 85): si forza la violazione e si
    attende INFEASIBLE, non «risolvi e guarda dove finisce».

    Buckets diversi (u=0, w=1): passa per il ramo `same, w != u` ->
    `post_cross(A, half, 0, A, half, 1)`.

    Verificato per mutazione: con `HalfDayGapBuilder.post` reso no-op, lo
    stesso scenario risponde FEASIBLE invece di INFEASIBLE."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.HALF_DAY_GAP, param=2)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a.id, 0, 0)] == 1)   # mezza 0
    model.Add(ctx.x[(b.id, 0, 4)] == 1)   # mezza 1, distanza 1 < 2
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_half_day_gap_a_uguale_b_distanza_legale():
    """Gemello «risolvi e asserisci» del test sopra, a distanza legale:
    stesse due occorrenze, ma nelle mezze giornate 0 e 4 (`day` 0 e 2,
    `slot` 0), distanza 4 >= `param = 2`. Copre il builder che vieta *tutto*
    incondizionatamente (finestra troppo larga, o `minimo` ignorato): un
    builder cosi' supererebbe il test avversario sopra (resta INFEASIBLE
    sempre) ma fallirebbe qui, perche' qui serve che un piazzamento legale
    esista davvero.

    Verificato per mutazione: sostituendo `min(u + minimo, n)` con `n`
    nel ciclo di `HalfDayGapBuilder.post` (cioe' ignorando `minimo` e
    vincolando *tutte* le coppie della settimana, non solo quelle entro
    `param`), questo scenario diventa INFEASIBLE."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.HALF_DAY_GAP, param=2)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a.id, 0, 0)] == 1)   # mezza 0
    model.Add(ctx.x[(b.id, 2, 0)] == 1)   # mezza 4, distanza 4 >= 2
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_half_day_gap_a_uguale_b_stessa_mezza_giornata_morde():
    """A = B, `param = 1`: due occorrenze forzate nella **stessa** mezza
    giornata (`u == w == 0`). Ramo diverso dal primo test: qui `w == u`,
    quindi il builder passa per `post_separable(A, "half", 0)` — «al piu'
    un'occorrenza per secchio» — non per `post_cross`. Con `param = 1` il
    ciclo (`for w in range(u, min(u + 1, n))`) non produce mai una coppia
    con `w > u`: solo il ramo separabile e' esercitato.

    Verificato per mutazione: saltando il ramo `if w == u:
    post_separable(...)` (sostituito con un `continue`), lo stesso scenario
    risponde FEASIBLE invece di INFEASIBLE."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.HALF_DAY_GAP, param=1)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a.id, 0, 0)] == 1)   # mezza 0
    model.Add(ctx.x[(b.id, 0, 1)] == 1)   # mezza 0, stesso secchio
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_half_day_gap_a_diverso_b_morde_in_entrambi_i_versi():
    """A != B: il checker e' **simmetrico** anche fra materie diverse
    (`crossed = same or s1 != s2`, nessun verso privilegiato). Con
    `param = 2`, la coppia (u=0, w=1) genera **due** chiamate a
    `post_cross` — `(A@0, B@1)` e `(B@0, A@1)` — perche' entrambi gli
    ordinamenti sono coppie incrociate corte. Si forzano separatamente i
    due versi: entrambi devono risultare INFEASIBLE.

    ⚠ Test di mutazione mirato (il punto esplicito del brief): rimuovendo
    la **seconda** chiamata a `post_cross` (quella per `w != u`, verso
    B@u/A@w) da `HalfDayGapBuilder.post`, lo scenario 2 sotto (B prima, A
    dopo) diventa FEASIBLE mentre lo scenario 1 resta INFEASIBLE — un solo
    verso resterebbe scoperto. Verificato manualmente (vedi il report)."""
    env = mini_school()
    matematica = env["subject"]
    italiano = Subject.objects.create(
        code="ITA2", name="Italiano2", discipline=env["discipline"])
    a = make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(italiano, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=matematica, subject_b=italiano,
        school_class=env["klass"], type=T.HALF_DAY_GAP, param=2)

    # scenario 1: A (mezza 0) prima di B (mezza 1), distanza 1 < 2
    model1, ctx1 = build_model(env["schedule"])
    model1.Add(ctx1.x[(a.id, 0, 0)] == 1)
    model1.Add(ctx1.x[(b.id, 0, 4)] == 1)
    solver1 = cp_model.CpSolver()
    assert solver1.Solve(model1) == cp_model.INFEASIBLE

    # scenario 2: verso invertito, B (mezza 0) prima di A (mezza 1)
    model2, ctx2 = build_model(env["schedule"])
    model2.Add(ctx2.x[(b.id, 0, 0)] == 1)
    model2.Add(ctx2.x[(a.id, 0, 4)] == 1)
    solver2 = cp_model.CpSolver()
    assert solver2.Solve(model2) == cp_model.INFEASIBLE


def test_adr018_half_day_gap_non_pretende_la_riparazione():
    """ADR-018: due occorrenze **congelate** a distanza inferiore al
    `param` (baseline gia' violata) piu' una libera. `HalfDayGapBuilder`
    non implementa nessun trattamento suo per ADR-018 — lo eredita
    interamente da `post_separable`/`post_cross` (subject_buckets.py, gia'
    verificati la' per mutazione). Qui si esibisce che l'eredita' regge sul
    builder concreto: il modello non deve diventare INFEASIBLE per colpa
    del passato.

    Congelate a mezza 0 e mezza 1 (distanza 1), `param = 2`: baseline gia'
    in violazione (ramo A = B, `w != u` -> `post_cross`, `fa = fb = True`,
    quarto ramo della tabella). La libera viene fissata **fuori**
    dall'intervallo fra le due congelate (mezza 6, ben lontana): non e' una
    riparazione, quindi dev'essere ammessa.

    ⚠ Asserzione **strutturale** (Ruling 85), non «risolvi e guarda dove
    e' finita»: si fissa la libera con `model.Add` e si chiede FEASIBLE.

    Verificato per mutazione: forzando temporaneamente il quarto ramo di
    `post_cross` a postare `ha + hb <= 1` anche quando `fa` e `fb` sono
    entrambi veri (cioe' ignorando ADR-018, la stessa mutazione gia'
    verificata nei test di `subject_buckets.py`), questo scenario diventa
    INFEASIBLE — vedi il report per il dettaglio della prova."""
    env = mini_school()
    congelate = [make_activity(env["subject"], classes=[env["klass"]],
                               immobility="fixed") for _ in range(2)]
    libera = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], congelate[0], day=0, slot=0)   # mezza 0
    place(env["schedule"], congelate[1], day=0, slot=4)   # mezza 1
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.HALF_DAY_GAP, param=2)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(libera.id, 3, 0)] == 1)   # mezza 6, lontana dal buco
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
