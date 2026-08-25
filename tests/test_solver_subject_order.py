"""I vincoli di materia che ragionano sull'ordine: qui solo WEEKLY_ORDER
(`domain/solver/builders/subject_order.py`).

⚠ Niente `test_weekly_order_sul_banco` qui (Ruling 16, correzione 3 del
brief Task 9, qui applicazione successiva): `tests/solver_harness.py`
registra `_derive_weekly_order` sotto `T.WEEKLY_ORDER`, e
`tests/test_solver_witness.py::test_famiglia` gia' parametrizza su
`sorted(DERIVERS) x [1..5]` — i cinque seed della famiglia esistono in
automatico appena il derivatore e' registrato. Scriverli anche qui sarebbe
un duplicato esatto, come gia' per i derivatori dei Task 7-11."""
import pytest
from ortools.sat.python import cp_model

from domain import weeks
from domain.models import ClassPart, ClassPartition, Subject, SubjectConstraint
from domain.solver.model import apply, build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


def _model_size(model):
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return len(proto.variables), len(proto.constraints)


def test_weekly_order_impone_la_prima_occorrenza():
    """La prima ora di A dev'essere prima (o uguale in posizione) alla
    prima ora di B: due attivita' per materia, nessuna congelata, quindi il
    ramo secco di ADR-018 (FA e FB entrambi None) posta il vincolo secco
    `prima_a <= prima_b`.

    Forma **avversaria** (Important 3 del giro di correzione Task 12), non
    «risolvi e guarda la soluzione»: quella forma non mordeva, perche' CP-SAT
    piazza di default in ordine di creazione e la fixture crea le due di A
    **prima** delle due di B, cosi' `prima(a) <= prima(b)` era vera per
    costruzione della fixture, non per il vincolo (misurato dalla review:
    il test restava verde anche col builder reso no-op). Qui si forzano
    esplicitamente le celle in modo che B occorra prima di A — la violazione
    diretta della riga — e si attende INFEASIBLE: la condizione discrimina
    per costruzione, non per fortuna del solver di default.

    Verificato per mutazione: con `WeeklyOrderBuilder.post` reso no-op,
    questo stesso scenario risponde OPTIMAL/FEASIBLE invece di INFEASIBLE."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = [make_activity(env["subject"], teachers=[env["teacher"]],
                       classes=[env["klass"]]) for _ in range(2)]
    b = [make_activity(matematica, teachers=[env["teacher"]],
                       classes=[env["klass"]]) for _ in range(2)]
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    model, ctx = build_model(env["schedule"])
    # forza min(pos_b) < min(pos_a): B interamente prima di A.
    model.Add(ctx.x[(a[0].id, 2, 0)] == 1)   # pos 12
    model.Add(ctx.x[(a[1].id, 3, 0)] == 1)   # pos 18
    model.Add(ctx.x[(b[0].id, 0, 0)] == 1)   # pos 0
    model.Add(ctx.x[(b[1].id, 0, 1)] == 1)   # pos 1
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_weekly_order_impone_la_prima_occorrenza_orientamento_invertito():
    """Gemello «risolvi e asserisci» del test avversario sopra, con
    l'**orientamento invertito** rispetto all'ordine di creazione della
    fixture: la riga chiede che la prima occorrenza di Matematica (creata
    per seconda) preceda quella di Italiano (creata per prima) — il verso
    *opposto* a quello che CP-SAT produce di default piazzando in ordine di
    creazione. Misurato dalla review: in questa forma morde deterministicamente
    (8/8 esecuzioni), a differenza dell'orientamento naturale sopra.

    Copre il modo di sbagliare complementare all'avversario: un builder che
    vieta *tutto* incondizionatamente supererebbe la prova avversaria (resta
    INFEASIBLE sempre) ma fallirebbe qui, perche' qui serve che un
    piazzamento **legale** esista davvero (OPTIMAL/FEASIBLE) e rispetti
    l'ordine richiesto.

    Verificato per mutazione: con `WeeklyOrderBuilder.post` reso no-op, la
    soluzione di default resta quella "naturale" (Italiano prima di
    Matematica) e l'assert sotto fallisce."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    italiano = [make_activity(env["subject"], teachers=[env["teacher"]],
                              classes=[env["klass"]]) for _ in range(2)]
    mat = [make_activity(matematica, teachers=[env["teacher"]],
                         classes=[env["klass"]]) for _ in range(2)]
    SubjectConstraint.objects.create(
        subject_a=matematica, subject_b=env["subject"],
        school_class=env["klass"], type=T.WEEKLY_ORDER)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats

    def prima(gruppo):
        return min(soluzione.placements[x.id] for x in gruppo)

    assert prima(mat) <= prima(italiano)


def test_weekly_order_con_a_uguale_b_non_vincola_nulla():
    """Il checker esce subito quando A = B (prima condizione di
    `WeeklyOrderChecker.violations`): il builder deve fare lo stesso.

    Test unilaterale per forma se ci si fermasse a «resta FEASIBLE»: con
    A = B i due `AddMinEquality` girano sullo stesso insieme di attivita',
    quindi `prima_a == prima_b` e `prima_a <= prima_b` e' banalmente vero —
    un builder SENZA la guardia risulta comunque FEASIBLE, e quel confronto
    da solo non lo coglierebbe mai. L'unica osservabile e' la **dimensione
    del modello**: con la riga presente il builder deve postare esattamente
    quanto posterebbe senza quella riga (cioe' nulla) — si confronta
    `build_model` con la riga e senza.

    Verificato per mutazione: rimuovendo `if row.subject_a_id ==
    row.subject_b_id: return` da `WeeklyOrderBuilder.post`, le due
    dimensioni divergono (la riga posta comunque due `AddMinEquality` e un
    confronto, anche se logicamente ridondanti) e questo test diventa
    rosso."""
    env = mini_school()
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    riga = SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    model_con, _ = build_model(env["schedule"])
    dim_con = _model_size(model_con)

    riga.delete()
    model_senza, _ = build_model(env["schedule"])
    dim_senza = _model_size(model_senza)

    assert dim_con == dim_senza


def test_weekly_order_materia_assente_non_crea_vincoli():
    """Il ramo `not a or not b`: la materia B non ha alcuna attivita' nel
    modello (assente, non solo priva di occorrenze piazzate), quindi
    `subject_activities` restituisce una lista vuota e il builder esce
    senza postare nulla.

    Senza la guardia, `AddMinEquality` con una lista di letterali vuota
    produce (misurato, non solo atteso) un modello INFEASIBLE invece di
    limitarsi a non vincolare nulla. Verificato per mutazione: rimuovendo
    `if not a or not b: return`, questo test fallisce — `solver.Solve(model)`
    torna INFEASIBLE invece di OPTIMAL/FEASIBLE."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    # matematica non ha nessuna attivita': la riga la nomina, ma resta
    # assente dal modello.
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)
    model, _ = build_model(env["schedule"])
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_weekly_order_posta_per_firma_di_settimana():
    """Il builder deve postare un vincolo **per firma**, coi soli letterali
    attivi in quella firma (`SubjectBuilder.build` itera su
    `ctx.signatures`, `post` chiama `subject_activities(..., signature=rep)`).
    Costruito apposta perche' una traduzione sull'**unione** delle
    settimane dia una risposta diversa da quella corretta — la stessa forma
    di difetto misurata per il derivatore (vedi il docstring di
    `_derive_weekly_order` in tests/solver_harness.py e il report del
    Task 12): a1/b1 attivi solo nella settimana 0, a2/b2 solo nella
    settimana 1.

    Si forza b1 (settimana 0) a una posizione presto e a1 (settimana 0) a
    una posizione tarda: dentro la sola settimana 0 l'ordine e' violato (a1
    dopo b1). a2 (settimana 1) va forzata presto, ma non c'entra nulla con
    la settimana 0 — un builder corretto, che vede solo {a1} contro {b1} in
    quella firma, deve rifiutare comunque l'assegnazione: INFEASIBLE.

    Una traduzione sull'unione vedrebbe invece min(pos(a1), pos(a2)) =
    pos(a2), presto quanto b1: la violazione di a1 contro b1 sparirebbe
    dietro a2, e il modello risulterebbe FEASIBLE.

    Verificato per mutazione (manuale — vedi il report del Task 12):
    rimuovendo `signature=rep` dalle due chiamate a `v.subject_activities`
    in `WeeklyOrderBuilder.post`, questo identico scenario diventa
    FEASIBLE invece di INFEASIBLE."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a1 = make_activity(env["subject"], classes=[env["klass"]],
                       mask=weeks.single_week(0))
    a2 = make_activity(env["subject"], classes=[env["klass"]],
                       mask=weeks.single_week(1))
    b1 = make_activity(matematica, classes=[env["klass"]],
                       mask=weeks.single_week(0))
    make_activity(matematica, classes=[env["klass"]],
                  mask=weeks.single_week(1))  # b2, tiene viva la firma 1
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(b1.id, 0, 0)] == 1)   # b1 presto (pos 0)
    model.Add(ctx.x[(a1.id, 2, 0)] == 1)   # a1 tardi (pos 12): viola la firma 0
    model.Add(ctx.x[(a2.id, 0, 0)] == 1)   # a2 presto, ma appartiene alla firma 1
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_adr018_ramo_secco_vieta_la_libera_dopo_la_congelata():
    """ADR-018, ramo secco: FA e' None (nessuna congelata di A), FB non lo
    e' (una congelata di B). Nessuna violazione preesistente da riparare,
    quindi il vincolo secco `prima_a <= prima_b` resta in vigore: la libera
    di A non puo' finire dopo la congelata di B."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(matematica, classes=[env["klass"]], immobility="fixed")
    place(env["schedule"], b, day=2, slot=0)   # FB = pos 12
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    # dopo la congelata (pos 18 > 12): vietato.
    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a.id, 3, 0)] == 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE

    # prima della congelata (pos 6 <= 12): ammesso.
    model2, ctx2 = build_model(env["schedule"])
    model2.Add(ctx2.x[(a.id, 1, 0)] == 1)
    solver2 = cp_model.CpSolver()
    assert solver2.Solve(model2) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo():
    """ADR-018, ramo disgiuntivo: FA e FB non sono None e FB < FA — le
    congelate (a_frozen a pos 12, b_frozen a pos 0) violano gia' la riga.

    Qui il ramo `riparato` e' reso impossibile dalla griglia stessa, non
    dal builder: per ripararsi servirebbe un'attivita' di A a pos 0 (la
    posizione della congelata di B), ma quella cella e' gia' occupata dalla
    congelata di B — `structural:occupation` vieta la sovrapposizione sulla
    stessa classe. Il test esercita quindi davvero lo status quo, non la
    riparazione.

    Il modello NON dev'essere INFEASIBLE (la disgiunzione ha sempre almeno
    il ramo status-quo). Il divieto e' ora per **attivita'**, non solo sul
    minimo aggregato (Critical del giro di correzione Task 12): nessuna
    libera di A puo' finire nella cella della congelata colpevole ne' prima
    (pos >= FA + 1, non solo pos >= FA) — vedi
    test_adr018_ramo_disgiuntivo_vieta_anche_il_pareggio per il caso che
    distingue le due forme."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_frozen = make_activity(env["subject"], classes=[env["klass"]],
                             immobility="fixed")
    a_free = make_activity(env["subject"], classes=[env["klass"]])
    b_frozen = make_activity(matematica, classes=[env["klass"]],
                             immobility="fixed")
    place(env["schedule"], a_frozen, day=2, slot=0)   # FA = pos 12
    place(env["schedule"], b_frozen, day=0, slot=0)   # FB = pos 0
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    # status quo: nessuna libera di A nella cella della congelata colpevole
    # ne' prima (pos > FA, non solo pos >= FA).
    assert soluzione.placements[a_free.id] > (2, 0)

    # verifica diretta che il ramo 'riparato' sia bloccato: forzare la
    # libera di A prima di FA (pos 6 < 12) dev'essere INFEASIBLE, sia
    # perche' violerebbe lo status quo (prima_a scenderebbe sotto FA) sia
    # perche' non basterebbe comunque a soddisfare la riparazione (prima_b
    # resta fissa a 0 dalla congelata di B).
    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a_free.id, 1, 0)] == 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_adr018_ramo_disgiuntivo_vieta_la_libera_di_b_sotto_lo_status_quo():
    """Important 1 del giro di correzione Task 12: il congiunto su B
    (`prima_b >= FB`, ora il divieto per attivita' `pos(bid) >= FB + 1`)
    era indifeso — misurato dalla review, la suite intera resta verde
    rimuovendo quel congiunto dal builder.

    Simmetrico al test sopra, ma isola il lato B: qui A non ha **nessuna**
    libera (solo a_frozen), cosi' il ramo 'riparato' resta bloccato per
    costruzione — prima_a e' fissa a FA = 12 e non puo' scendere sotto la
    posizione forzata di b_free — e la prova esercita esclusivamente il
    congiunto su B, senza la via di fuga della riparazione.

    Verificato per mutazione: rimuovendo il ciclo `for bid in b: ...` da
    `WeeklyOrderBuilder.post`, questo stesso scenario risponde OPTIMAL
    invece di INFEASIBLE (il ciclo su A da solo non protegge B: "a" qui non
    ha membri liberi, quindi il suo ciclo e' comunque un no-op)."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_frozen = make_activity(env["subject"], classes=[env["klass"]],
                             immobility="fixed")
    b_frozen = make_activity(matematica, classes=[env["klass"]],
                             immobility="fixed")
    b_free = make_activity(matematica, classes=[env["klass"]])
    place(env["schedule"], a_frozen, day=2, slot=0)   # FA = pos 12
    place(env["schedule"], b_frozen, day=0, slot=2)   # FB = pos 2
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(b_free.id, 0, 0)] == 1)   # pos 0 < FB (= 2): vietato
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_adr018_ramo_disgiuntivo_vieta_anche_il_pareggio():
    """Critical del giro di correzione Task 12 (review, sonda riprodotta
    dal committente): il ramo status-quo vietava solo `prima_a >= FA`, un
    vincolo sul **minimo aggregato**, non su chi lo realizza. Due attivita'
    della stessa materia su parti diverse della stessa partizione
    (sdoppiamento, ADR-013) non confliggono sull'occupazione — le parti
    della stessa partizione non condividono atomi (`activity_tokens`,
    `domain/analysis/state.py`) — e possono condividere la stessa cella:
    una libera poteva quindi **pareggiare** esattamente la posizione della
    congelata, lasciando `prima_a >= FA` soddisfatto ma cambiando *chi* e'
    l'argmin — e `Finding.key` include l'identita' delle due attivita', non
    la loro posizione (misurato dalla review: OPTIMAL, con un finding HARD
    nuovo dopo l'apply). Ora il divieto e' per attivita' (`pos(aid) >= FA +
    1` per ogni libera), che esclude anche il pareggio.

    Costruzione: una ClassPartition con due ClassPart sulla stessa classe;
    una libera di A sulla prima parte, una congelata di A sulla seconda,
    piu' una congelata di B prima di tutte (FB < FA, ramo disgiuntivo). Si
    forza la libera esattamente nella cella della congelata di A.

    Verificato per mutazione: col builder del Task 12 consegnato
    (`model.Add(prima_a >= FA)` al posto del divieto per attivita'), questo
    stesso scenario risponde OPTIMAL invece di INFEASIBLE."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    partition = ClassPartition.objects.create(
        school_class=env["klass"], name="SD")
    p1 = ClassPart.objects.create(name="1A_g1", partition=partition)
    p2 = ClassPart.objects.create(name="1A_g2", partition=partition)

    a_free = make_activity(env["subject"], parts=[p2])
    a_frozen = make_activity(env["subject"], parts=[p1], immobility="fixed")
    b_frozen = make_activity(matematica, classes=[env["klass"]],
                             immobility="fixed")
    place(env["schedule"], a_frozen, day=2, slot=0)   # FA = pos 12
    place(env["schedule"], b_frozen, day=0, slot=0)   # FB = pos 0
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.WEEKLY_ORDER)

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a_free.id, 2, 0)] == 1)   # pareggio esatto con FA
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE
