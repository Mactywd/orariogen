"""I vincoli di materia che sono cardinalita' su un secchio: SAME_HALF_DAY e
TWO_DAYS sul nuovo scheletro di materia, piu' i quattro rami di ADR-018 su
SAME_DAY (A = B via `residual_cap`, A != B via la tabella a quattro rami di
`post_cross` in domain/solver/builders/subject_buckets.py).

⚠ Niente `test_secchi_sul_banco` qui (Ruling 16, correzione 3 del brief
Task 9): `tests/solver_harness.py` registra `_derive_same_half_day` sotto
`T.SAME_HALF_DAY_INCOMPATIBLE` e `_derive_two_days` sotto
`T.TWO_DAYS_INCOMPATIBLE`, e `tests/test_solver_witness.py::test_famiglia`
gia' parametrizza su `sorted(DERIVERS) × [1..5]` — i cinque seed di entrambe
le famiglie esistono in automatico appena i derivatori sono registrati.
Scriverli anche qui sarebbe un duplicato esatto, come gia' per i derivatori
dei Task 7, 8 e 9."""
import pytest
from ortools.sat.python import cp_model

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import SubjectConstraint, Subject
from domain.solver.model import apply, build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


def test_same_half_day_separa_le_meta_giornate():
    """Due ore della stessa materia, incompatibili nella mezza giornata: su una
    griglia con meta' giornata a 4 devono finire in mezze giornate diverse, o
    in giorni diversi."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.SAME_HALF_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    meta = {(day, 0 if slot < 4 else 1)
            for (day, slot) in soluzione.placements.values()}
    assert len(meta) == 2


def test_two_days_vieta_i_giorni_consecutivi():
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.TWO_DAYS_INCOMPATIBLE)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    giorno_a = soluzione.placements[a.id][0]
    giorno_b = soluzione.placements[b.id][0]
    assert giorno_b != giorno_a + 1


def test_two_days_con_a_uguale_b():
    """Minor 4 (review Task 10): la docstring di `TwoDaysBuilder` afferma che
    la tabella a quattro rami vale **anche con A = B** — il checker confronta
    `a_days[d]` con `b_days[d+1]`, due letture dello stesso insieme su giorni
    diversi, non il caso a un secchio solo di `_BucketIncompatible` A = B.
    `_derive_two_days` salta A = B con `if a.pk == b.pk: continue`, quindi
    nessun banco di prova lo esercita: nessun test lo difendeva.

    Due congelate ai giorni 0 e 1 (gia' in violazione fra loro: e' voluto,
    ADR-018) piu' una libera. Non deve essere INFEASIBLE, e la libera non
    deve creare una **nuova** violazione — verificato rileggendo il
    piazzamento col checker, non solo osservando dove il solver l'ha messa
    di sua scelta (potrebbe evitare una cella per un motivo estraneo a
    questo vincolo)."""
    env = mini_school()
    a_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    libera = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a_fissa, day=0, slot=0)
    place(env["schedule"], b_fissa, day=1, slot=0)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.TWO_DAYS_INCOMPATIBLE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    trovate = [f for f in check_schedule(env["schedule"])
               if f.code == "subject_two_days" and f.severity == Severity.HARD]
    # l'unica violazione ammessa e' quella preesistente fra le due congelate
    # (giorno 0 -> giorno 1, ADR-018): la libera non deve comparirci dentro.
    assert all(libera.id not in f.activities for f in trovate)


# --- ADR-018, i quattro rami --------------------------------------------
#
# Caso A = B: separabile, via residual_cap (rami 1-2 sotto).
# Caso A != B: non separabile, via la tabella a quattro rami di post_cross
# (rami 3-4 sotto; i rami fa=0,fb=0 e fa=0,fb=1 sono gia' esercitati da
# test_due_materie_diverse_non_coesistono_nella_giornata e da
# test_il_vincolo_asimmetrico_quando_a_e_congelata_e_b_libera in
# tests/test_solver_same_day.py, che restano invariati).


def test_adr018_same_day_due_congelate_piu_libera():
    """Ramo 1 (A = B, cap = 0 con due congelate): il secchio e' gia' violato
    da due congelate. Non deve essere INFEASIBLE, e la libera non deve
    finirci."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    c = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.SAME_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[c.id][0] != 0


def test_adr018_same_day_una_congelata_piu_libera():
    """Ramo 2 (A = B, cap = 0 con una congelata): la libera evita il giorno.
    Il meccanismo (residual_cap che clampa a zero) e' gia' testato a livello
    di unita' in test_residual_cap_clampa_a_zero_invece_di_andare_negativo
    (tests/test_solver_residual.py); qui si verifica end-to-end che
    SameDayBuilder lo applichi davvero sul secchio."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.SAME_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[b.id][0] != 0


def test_adr018_a_diverso_b_entrambe_congelate_piu_libera_di_a():
    """Ramo 3 (A != B, fa=1 e fb=1: il quarto ramo della tabella): entrambe le
    materie hanno gia' una congelata nello stesso giorno — il secchio e' gia'
    violato. Non deve essere INFEASIBLE (non si tocca ha/hb, gia' forzati a 1
    dalle congelate), e la libera di A non deve finire in quel giorno."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b_fissa = make_activity(matematica, classes=[env["klass"]], immobility="fixed")
    a_libera = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a_fissa, day=0, slot=0)
    place(env["schedule"], b_fissa, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.SAME_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[a_libera.id][0] != 0


def test_adr018_a_diverso_b_entrambe_congelate_piu_libera_di_b():
    """Ramo 3 (A != B, fa=1 e fb=1), lato **B**: simmetrico al test
    precedente, ma la libera e' di B invece che di A. `post_cross` azzera i
    letterali liberi di A **e** di B con due cicli distinti (`for aid, lit in
    la` e poi `for aid, lit in lb`); il test sopra mette una sola libera, di
    A, ed esercita solo il primo. Mutante di prova della review: togliendo il
    ciclo su `lb`, la suite restava interamente verde perche' nessun test
    metteva una libera dal lato B. Qui la libera di B non deve finire nel
    giorno gia' violato."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b_fissa = make_activity(matematica, classes=[env["klass"]], immobility="fixed")
    b_libera = make_activity(matematica, classes=[env["klass"]])
    place(env["schedule"], a_fissa, day=0, slot=0)
    place(env["schedule"], b_fissa, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.SAME_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[b_libera.id][0] != 0


def test_adr018_a_diverso_b_solo_a_congelata_libera_di_a_non_vincolata():
    """Ramo 4 (A != B, fa=1 e fb=0): la libera di B evita il giorno (hb == 0),
    ma la libera di A non e' toccata da questo vincolo — e' il ramo che
    distingue la regola giusta dalla regola meccanica max(0, 1 - fa - fb), che
    l'avrebbe vietata anche a lei.

    Non basta osservare dove il solver la mette di sua scelta (potrebbe
    evitare il giorno per un motivo estraneo a questo vincolo): si forza la
    libera di A al giorno 0 costruendo il modello direttamente, e si verifica
    che resti fattibile."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    a_libera = make_activity(env["subject"], classes=[env["klass"]])
    b_libera = make_activity(matematica, classes=[env["klass"]])
    place(env["schedule"], a_fissa, day=0, slot=0)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.SAME_DAY_INCOMPATIBLE)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a_libera.id, 0, 1)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), status

    # E la libera di B, nello stesso modello, resta vincolata a evitare il
    # giorno 0: il ramo non e' diventato simmetrico per errore.
    for (aid, day, slot), var in ctx.x.items():
        if aid == b_libera.id and day == 0:
            assert solver.Value(var) == 0


def test_adr018_il_quarto_ramo_puo_rendere_il_modello_infattibile():
    """Minor 5 (review Task 10): il docstring di `post_cross` avverte in ⚠
    che il quarto ramo (fa=1, fb=1) **puo'** rendere il modello infattibile
    se una libera non ha altro posto dove andare, e dichiara che e' voluto —
    e' testualmente cio' che ADR-018 concede («al piu' non puo' aggiungere
    nulla li'»). Nessun test lo esibiva.

    Griglia a **un solo giorno**: A congelata alla fascia 0, B congelata alla
    fascia 1 (materie diverse, gia' in violazione fra loro — il secchio e'
    gia' pieno). Una terza attivita' libera, sempre di materia A: l'unico
    giorno che esiste e' quello gia' zero forzato dal quarto ramo per
    entrambe le materie, quindi non ha nessun'altra cella legale — a
    differenza dei test precedenti (griglia a piu' giorni), dove la libera
    poteva semplicemente spostarsi altrove. Deve essere INFEASIBLE."""
    env = mini_school()
    env["grid"].days_per_cycle = 1
    env["grid"].slots_per_day = 3
    env["grid"].morning_end_slot = 3
    env["grid"].save()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b_fissa = make_activity(matematica, classes=[env["klass"]], immobility="fixed")
    make_activity(env["subject"], classes=[env["klass"]])  # a_libera
    place(env["schedule"], a_fissa, day=0, slot=0)
    place(env["schedule"], b_fissa, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.SAME_DAY_INCOMPATIBLE)
    soluzione = solve(env["schedule"])
    assert soluzione.status == "INFEASIBLE", soluzione.stats
