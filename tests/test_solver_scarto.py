"""Lo scarto come stato del modello — la prima meta' del pezzo 3.

Il solver ha smesso di pretendere il piazzamento: `AddExactlyOne` e' diventato
`somma(celle) == piazzata`, e cio' che non ci sta resta **scartato** invece di
rendere infattibile tutto l'orario. E' lo stato in cui EDT crea le attivita'
(«Non piazzata»), e ha due meta' che vanno provate insieme: il solver risponde,
e `check_schedule` **nomina** cio' che e' rimasto fuori. Senza la seconda,
«scarta tutto» sarebbe un orario pulito."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import Subject, SubjectConstraint
from domain.solver.model import apply, solve
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _scarti(schedule):
    return {f.activities[0] for f in check_schedule(schedule)
            if f.code == "activity_unplaced"}


def test_l_istanza_sovravincolata_da_scarti_contati_e_nominati():
    """Sette ore di lezione su una griglia da sei fasce per la stessa classe:
    una non ci sta, e l'aritmetica non lascia scelta.

    ⚠ L'assert che conta e' **quante**, non «lo status non e' INFEASIBLE»:
    scartare tutte e sette e' anch'essa una risposta senza infattibilita', e
    passerebbe il criterio debole."""
    env = mini_school(days=1)
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["scartate"] == 1, soluzione.stats
    assert soluzione.stats["minuti_scartati"] == 60

    apply(soluzione, env["schedule"])
    assert _scarti(env["schedule"]) == set(soluzione.unplaced)


def test_l1_conta_le_ore_non_le_attivita():
    """La decisione D1 della spec, resa un test. Sei fasce in un giorno, e
    sette ore da piazzare: un'attivita' da 2h piu' cinque da 1h. Si deve
    rinunciare a un'ora, e ci sono due modi — lasciar fuori l'attivita' da 2h
    (2 ore perse) o una da 1h (1 ora persa).

    Minimizzando le **ore**, il blocco da 2h resta dentro. Minimizzando il
    **numero** di attivita' le due risposte pareggerebbero, ed e' esattamente
    la differenza che D1 sceglie."""
    env = mini_school(days=1)
    lungo = make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]], slots=2)
    for _ in range(5):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["minuti_scartati"] == 60, soluzione.stats
    assert lungo.id in soluzione.placements, (
        "scartato il blocco da 2h: L1 sta contando le attivita', non le ore")


def test_apply_cancella_il_piazzamento_di_cio_che_e_stato_scartato():
    """Un'attivita' piazzata ieri e scartata oggi non puo' restare piazzata nel
    database: l'orario che `check_schedule` legge non sarebbe quello che il
    solver ha deciso, e l'oracolo misurerebbe un orario che non esiste.

    ⚠ Perche' il test morda davvero, l'attivita' scartata deve **avere** una
    riga da cancellare: quindi si piazzano a mano tutte e sette, due sulla
    stessa fascia. Un orario illegale e' uno stato ammesso — e' il
    comportamento di EDT, ed e' cio' che rende osservabile la cancellazione.
    Nella prima stesura di questo test le sette nascevano senza piazzamento e
    la mutazione «apply non cancella» **non** lo faceva diventare rosso: un
    test che non afferma niente."""
    from domain.models import Placement
    env = mini_school(days=1)
    attivita = [make_activity(env["subject"], teachers=[env["teacher"]],
                              classes=[env["klass"]]) for _ in range(7)]
    for i, a in enumerate(attivita):
        Placement.objects.create(schedule=env["schedule"], activity=a,
                                 day=0, start_slot=min(i, 5))
    assert Placement.objects.filter(schedule=env["schedule"]).count() == 7

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 1, soluzione.stats
    apply(soluzione, env["schedule"])

    piazzate = set(Placement.objects.filter(schedule=env["schedule"])
                   .values_list("activity_id", flat=True))
    assert piazzate == set(soluzione.placements)
    assert set(soluzione.unplaced) & piazzate == set()
    assert len(piazzate) == 6


def _due_docenti_una_cella_ciascuno(env):
    """T1 puo' insegnare solo in (1,4), T2 solo in (1,5). Serve a fissare le
    posizioni senza congelare niente: il dominio lo restringono le
    indisponibilita', non i piazzamenti."""
    from domain.models import ResourceUnavailability, Teacher
    t2 = Teacher.objects.create(name="Bianchi Ugo", last_name="Bianchi",
                                first_name="Ugo")
    for giorno in range(2):
        for fascia in range(6):
            if not (giorno == 1 and fascia == 4):
                ResourceUnavailability.objects.create(
                    resource=env["teacher"], day=giorno, slot=fascia, level="hard")
            if not (giorno == 1 and fascia == 5):
                ResourceUnavailability.objects.create(
                    resource=t2, day=giorno, slot=fascia, level="hard")
    return t2


def test_la_posizione_di_una_scartata_e_oltre_la_griglia_non_zero():
    """La sentinella di `vocabulary.pos`, provata dove nient'altro la copre.

    La riga chiede «prima Italiano, poi Matematica». Matematica ha **due** ore:
    una piazzabile in (1,5) — posizione 11 — e una che non sta da nessuna parte
    (dura piu' di una giornata). Italiano sta solo in (1,4), posizione 10.
    Il vincolo guarda il **minimo** delle posizioni di Matematica: con la
    scartata a «oltre la griglia» il minimo e' 11, e 10 <= 11 e' vero.

    Se invece la scartata valesse **zero** — la prima cella, la piu' precoce di
    tutte — il minimo diventerebbe 0 e il vincolo pretenderebbe Italiano prima
    dell'inizio della settimana: `INFEASIBLE` per colpa di un'ora che
    nell'orario non c'e'.

    ⚠ Qui la guardia del builder non protegge: Matematica **ha** un'occorrenza
    piazzata, quindi il vincolo si posta. E' il caso che il test precedente,
    scritto con un lato interamente scartato, non riusciva a vedere — e
    infatti la mutazione lo lasciava verde.

    Verificato per mutazione: rimettendo in `pos` la canalizzazione
    incondizionata questo test diventa rosso."""
    env = mini_school(days=2)
    _due_docenti_una_cella_ciascuno(env)
    from domain.models import Teacher
    t2 = Teacher.objects.get(last_name="Bianchi")
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    ita = make_activity(env["subject"], teachers=[env["teacher"]],
                        classes=[env["klass"]])
    mat = make_activity(matematica, teachers=[t2], classes=[env["klass"]])
    fantasma = make_activity(matematica, teachers=[t2], classes=[env["klass"]],
                             slots=7)   # la giornata ne ha 6: dominio vuoto
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=SubjectConstraint.Type.WEEKLY_ORDER)

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.unplaced == (fantasma.id,), soluzione.stats
    assert soluzione.placements[ita.id] == (1, 4)
    assert soluzione.placements[mat.id] == (1, 5)


def test_un_lato_interamente_scartato_non_trascina_l_altro():
    """La guardia del builder, provata dove la sentinella da sola non basta.

    Qui l'ordine e' invertito: la riga chiede «prima Matematica, poi Italiano»,
    e di Matematica esiste **solo** l'ora impiazzabile. `WeeklyOrderChecker`
    in questo caso non dice niente (`if not a or not b: return`, e `a` sono le
    occorrenze *piazzate*), quindi il modello non deve dire niente nemmeno lui.

    Senza guardia il vincolo si posta lo stesso, e con la sentinella diventa
    «la prima ora di Italiano dev'essere oltre la fine della griglia» — cioe'
    Italiano va scartato anche lui. Un'ora impiazzabile ne trascinerebbe fuori
    una piazzabilissima.

    Verificato per mutazione: togliendo `guardie` dall'`OnlyEnforceIf` questo
    test conta due scarti invece di uno."""
    env = mini_school(days=2)
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    ita = make_activity(env["subject"], teachers=[env["teacher"]],
                        classes=[env["klass"]])
    fantasma = make_activity(matematica, teachers=[env["teacher"]],
                             classes=[env["klass"]], slots=7)
    SubjectConstraint.objects.create(
        subject_a=matematica, subject_b=env["subject"],
        school_class=env["klass"], type=SubjectConstraint.Type.WEEKLY_ORDER)

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["scartate"] == 1, soluzione.stats
    assert soluzione.unplaced == (fantasma.id,)
    assert ita.id in soluzione.placements
