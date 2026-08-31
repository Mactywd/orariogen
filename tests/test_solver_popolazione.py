"""La separazione per popolazione, con la perdita di qualità tollerata
(`domain/solver/quality.Arbitrato`).

EDT **non cerca mai un ottimo congiunto**: i comandi sono due, `Ottimizza gli
orari dei docenti` e `... delle classi`. Chi lancia dichiara quale popolazione
ottimizzare e quanto è disposto a peggiorare l'altra — un vincolo di
non-regressione con budget, mai un peso in una somma.
"""
import pytest

from domain.models import (Placement, QualityCriterion, ResourceUnavailability,
                           SchoolClass, Teacher)
from domain.solver.model import solve
from domain.solver.quality import Arbitrato
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db
K = QualityCriterion.Kind
P = QualityCriterion.Population


def _tensione():
    """L'istanza in cui le due popolazioni **tirano in direzioni opposte**.

    Due ore della stessa materia, una griglia 2×2, un docente e una classe.
    `regularity` per la classe vuole la materia sempre alla **stessa fascia**,
    quindi su due giorni diversi (valore 1); `free_half_days` per il docente
    vuole tutto lo **stesso giorno**, quindi su due fasce diverse (valore 1).
    L'una a 1 costringe l'altra a 2: non esiste orario che le accontenti
    entrambe.

    ⚠ Una tensione va costruita, non sperata. Le istanze simmetriche più ovvie
    — due docenti per due classi — **non** la producono: due classi diverse
    possono occupare la stessa cella, quindi comprimere i docenti comprime
    anche le classi e i due ottimi coincidono. Misurato prima di scrivere un
    assert."""
    env = mini_school(days=2, slots=2)
    a1 = make_activity(env["subject"], teachers=[env["teacher"]],
                       classes=[env["klass"]])
    a2 = make_activity(env["subject"], teachers=[env["teacher"]],
                       classes=[env["klass"]])
    return env, a1, a2


def _regolare(env, a1, a2):
    """L'orario di partenza: ottimo per la **classe** (stessa fascia, due
    giorni), pessimo per il docente (due mezze giornate)."""
    Placement.objects.create(schedule=env["schedule"], activity=a1, day=0, start_slot=0)
    Placement.objects.create(schedule=env["schedule"], activity=a2, day=1, start_slot=0)


def _criteri():
    QualityCriterion.objects.create(kind=K.FREE_HALF_DAYS, population=P.TEACHERS, rank=1)
    QualityCriterion.objects.create(kind=K.REGULARITY, population=P.CLASSES, rank=2)


def _livelli(soluzione):
    return {e["nome"]: e["valore"] for e in soluzione.stats["livelli"]}


def test_all_non_e_una_popolazione_arbitrabile():
    """`ALL` è la nostra estensione per il criterio che **non prende parte**:
    EDT ha due popolazioni, non tre. Non può essere né quella ottimizzata né
    quella sacrificata, e il contratto lo dice invece di sbagliare in
    silenzio."""
    with pytest.raises(ValueError):
        Arbitrato(P.ALL)


def test_il_criterio_sacrificato_smette_di_essere_un_livello():
    """Il punto del meccanismo, e ciò che l'ordine dei `rank` da solo non sa
    fare: la popolazione sacrificata non si **ottimizza**, le si impedisce solo
    di peggiorare. Il suo criterio esce dalla catena e diventa un tetto."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()

    catena = _livelli(solve(env["schedule"], workers=1,
                            arbitrato=Arbitrato(P.TEACHERS, 0)))
    assert "free_half_days_teachers" in catena
    assert "regularity_classes" not in catena, (
        "il criterio della popolazione sacrificata non è un livello")

    # e nella catena unica ci sono entrambi
    catena = _livelli(solve(env["schedule"], workers=1))
    assert {"free_half_days_teachers", "regularity_classes"} <= set(catena)


def test_il_criterio_di_ogni_popolazione_e_un_livello_a_sua_volta():
    """La simmetria: sacrificando i docenti si perde il loro livello e resta
    quello delle classi. Senza questo, un tetto piazzato sempre sulla stessa
    popolazione passerebbe indisturbato."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()

    catena = _livelli(solve(env["schedule"], workers=1,
                            arbitrato=Arbitrato(P.CLASSES, 0)))
    assert "regularity_classes" in catena
    assert "free_half_days_teachers" not in catena


def test_il_tetto_di_non_regressione_morde():
    """Con tolleranza zero la classe non può peggiorare, quindi il docente
    resta a 2 anche se potrebbe scendere a 1; con la tolleranza che serve,
    scende.

    È il criterio di riuscita numero 3 della spec, ed è misurato sul **valore
    del livello**, mai su «guarda dove è finita l'attività»."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()

    stretto = solve(env["schedule"], workers=1, arbitrato=Arbitrato(P.TEACHERS, 0))
    assert stretto.status == "OPTIMAL"
    assert _livelli(stretto)["free_half_days_teachers"] == 2, (
        "il tetto sulla classe impedisce al docente di compattarsi")

    largo = solve(env["schedule"], workers=1, arbitrato=Arbitrato(P.TEACHERS, 1))
    assert largo.status == "OPTIMAL"
    assert _livelli(largo)["free_half_days_teachers"] == 1, (
        "concessa una fascia di regolarità, il docente si compatta")


def test_la_tolleranza_e_dichiarata_nel_rendiconto():
    """Base e tetto sono il rendiconto del comando: un tetto che non si vede è
    un risultato che l'utente non sa spiegarsi.

    🔑 E **dove il criterio è atterrato** è il terzo numero, aggiunto il
    2026-08-31: base 1 e tetto 4 non dicono se la tolleranza è servita. Qui il
    valore è 2 — un punto peggio della base, due dei tre concessi rimasti
    inutilizzati — e senza quel numero non si saprebbe né che il
    peggioramento c'è stato né quanto margine è avanzato."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()

    stats = solve(env["schedule"], workers=1,
                  arbitrato=Arbitrato(P.TEACHERS, 3)).stats
    assert stats["arbitraggi"] == (
        {"nome": "regularity_classes", "base": 1, "tetto": 4, "valore": 2},)


def test_la_base_e_il_valore_che_il_livello_da_sullo_stesso_orario():
    """🔑 Il test che impedisce alle due strade di divergere.

    La base si calcola su un modello usa-e-getta con i letterali di cella
    sostituiti da costanti; il livello si calcola dentro il modello vero. Sono
    la **stessa funzione**, e devono dare lo stesso numero sullo stesso orario
    — è la forma già adottata per i buchi contro `MaxGapChecker`.

    ⚠ La premessa è asserita, non sperata: senza arbitrato la stabilità
    precede la qualità, raggiunge zero conservando tutto e **inchioda** ogni
    cella, quindi il livello riporta il valore dell'orario di partenza. Se
    `spostamenti` non fosse zero, il confronto misurerebbe due orari diversi."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()

    catena = _livelli(solve(env["schedule"], workers=1))
    assert catena["spostamenti"] == 0, "l'orario di partenza è conservato"
    sul_livello = catena["regularity_classes"]

    stats = solve(env["schedule"], workers=1,
                  arbitrato=Arbitrato(P.TEACHERS, 0)).stats
    assert stats["arbitraggi"][0]["base"] == sul_livello


def test_con_l_arbitrato_la_stabilita_diventa_lo_spareggio():
    """🔑 La misura che ha cambiato l'ordine della catena.

    Con un orario di partenza completo la stabilità arriva a zero conservando
    tutto, e il suo fissaggio rende **inerte** ogni livello di qualità sotto di
    lei. In EDT il conflitto non si pone perché i comandi sono due; qui il
    comando è uno, e `arbitrato` è la dichiarazione «questa è
    un'ottimizzazione»: la stabilità scivola in coda e diventa lo spareggio."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    QualityCriterion.objects.create(kind=K.FREE_HALF_DAYS,
                                    population=P.TEACHERS, rank=1)

    nomi = [e["nome"] for e in solve(env["schedule"], workers=1).stats["livelli"]]
    assert nomi.index("spostamenti") < nomi.index("free_half_days_teachers")
    assert _livelli(solve(env["schedule"], workers=1))[
        "free_half_days_teachers"] == 2, "la stabilità l'ha reso inerte"

    ottimizza = solve(env["schedule"], workers=1,
                      arbitrato=Arbitrato(P.TEACHERS, 0))
    nomi = [e["nome"] for e in ottimizza.stats["livelli"]]
    assert nomi.index("free_half_days_teachers") < nomi.index("spostamenti")
    assert _livelli(ottimizza)["free_half_days_teachers"] == 1


def test_senza_orario_di_partenza_non_c_e_tetto():
    """«Peggiorare» ha senso solo rispetto a qualcosa. Un orario vuoto non ha
    buchi, quindi una base calcolata lì sarebbe ottimisticamente bassa e il
    tetto una pretesa assurda: nessun tetto, e **dichiarato**."""
    env, a1, a2 = _tensione()
    _criteri()   # nessun Placement

    soluzione = solve(env["schedule"], workers=1,
                      arbitrato=Arbitrato(P.TEACHERS, 0))
    assert soluzione.status == "OPTIMAL"
    # ⚠ Il valore raggiunto si dice **anche** senza tetto, ed è lì che serve
    # di più: nessuno stava tenendo fermo quel criterio, e il rendiconto dice
    # dove è finito invece di tacere.
    assert soluzione.stats["arbitraggi"] == (
        {"nome": "regularity_classes", "base": None, "tetto": None,
         "valore": 2},)
    # senza tetto il docente si compatta liberamente
    assert _livelli(soluzione)["free_half_days_teachers"] == 1


def test_un_orario_di_partenza_parziale_non_e_una_base():
    """Una sola delle due piazzate: la base sarebbe calcolata su mezzo orario.
    La condizione è **ogni** attività libera, non «almeno una»."""
    env, a1, a2 = _tensione()
    Placement.objects.create(schedule=env["schedule"], activity=a1,
                             day=0, start_slot=0)
    _criteri()

    stats = solve(env["schedule"], workers=1,
                  arbitrato=Arbitrato(P.TEACHERS, 0)).stats
    assert stats["arbitraggi"][0]["base"] is None


def test_una_collocazione_non_piu_ammissibile_non_e_una_base():
    """La seconda condizione: se i pre-filtri hanno tolto la vecchia cella,
    quell'orario non è rappresentabile in questo modello e non è una base.

    Qui la toglie un'indisponibilità **rossa** sopravvenuta sulla cella in cui
    l'attività stava — il caso reale: la scuola cambia le disponibilità e
    rilancia."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()
    ResourceUnavailability.objects.create(
        resource=env["teacher"].resource_ptr, day=1, slot=0,
        level=ResourceUnavailability.Level.HARD)

    stats = solve(env["schedule"], workers=1,
                  arbitrato=Arbitrato(P.TEACHERS, 0)).stats
    assert stats["arbitraggi"][0]["base"] is None


def test_il_criterio_senza_popolazione_resta_un_livello():
    """`ALL` non prende parte, quindi non è mai la popolazione sacrificata: il
    suo criterio resta un livello in ogni corsa."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    QualityCriterion.objects.create(kind=K.ISOLATED, population=P.ALL, rank=1)
    QualityCriterion.objects.create(kind=K.REGULARITY, population=P.CLASSES, rank=2)

    catena = _livelli(solve(env["schedule"], workers=1,
                            arbitrato=Arbitrato(P.TEACHERS, 0)))
    assert "isolated_all" in catena
    assert "regularity_classes" not in catena


def test_in_coda_la_stabilita_prende_il_budget_della_qualita():
    """🔑 Il budget appartiene alla **posizione**, non al livello.

    `BUDGET_QUALITA` nasce da una diagnosi precisa: un livello è lento non
    perché difficile da ottimizzare, ma perché **impossibile da dimostrare** —
    i livelli che contano un fallimento chiudono subito perché il loro ottimo è
    zero e zero è anche il limite inferiore banale. La stabilità è uno di
    quelli **finché sta in testa**: conserva tutto e arriva a zero.

    Con l'arbitrato scivola in coda, e lì il suo ottimo non è più zero — i
    livelli di qualità sopra di lei hanno già spostato l'orario. Diventa
    indimostrabile esattamente come loro, e senza budget `manage.py solve` non
    torna. ⚠ Misurato sul Fermi con cinque criteri: `--popolazione teachers`
    ucciso dopo dodici minuti senza risposta; con `--limite 15` chiude in 52 s
    riportando `spostamenti 219`, ottimo non dimostrato, non sotto 8.

    È lo stesso difetto che aveva prodotto `BUDGET_QUALITA`, ricomparso al
    posto lasciato libero: allora la coda era la qualità, ora è la stabilità."""
    from domain.solver.model import build_model
    from domain.solver.objective import BUDGET_QUALITA, livelli

    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()
    model, ctx = build_model(env["schedule"])

    senza = {lv.nome: lv.limite for lv in livelli(ctx, model)}
    assert senza["spostamenti"] is None, "in testa dimostra l'ottimo: nessun budget"

    con = {lv.nome: lv.limite
           for lv in livelli(ctx, model, Arbitrato(P.TEACHERS, 0))}
    assert con["spostamenti"] == BUDGET_QUALITA


def test_il_rendiconto_dice_quando_la_tolleranza_e_servita_davvero():
    """Il terzo numero contro i primi due, sulla stessa istanza a due
    tolleranze diverse. Base e tetto crescono insieme e non distinguono niente;
    il valore raggiunto sì — a tolleranza 0 il criterio resta inchiodato alla
    base, a tolleranza 3 ne consuma uno.

    ⚠ È il debito che questo test chiude: fino al 2026-08-31 il rendiconto
    diceva *entro cosa* il criterio doveva restare e mai *dove è finito*, e le
    due corse qui sotto erano indistinguibili."""
    env, a1, a2 = _tensione()
    _regolare(env, a1, a2)
    _criteri()

    stretto = solve(env["schedule"], workers=1,
                    arbitrato=Arbitrato(P.TEACHERS, 0)).stats["arbitraggi"][0]
    assert (stretto["tetto"], stretto["valore"]) == (1, 1)

    largo = solve(env["schedule"], workers=1,
                  arbitrato=Arbitrato(P.TEACHERS, 3)).stats["arbitraggi"][0]
    assert (largo["tetto"], largo["valore"]) == (4, 2)
