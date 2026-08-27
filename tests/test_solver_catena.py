"""La catena lessicografica (`domain/solver/objective.py`).

Risolvi per il criterio 1, **fissa** quel valore, passa al 2. Mai una somma
pesata: e' la forma con cui EDT governa i compromessi, e la ragione sta nel
docstring del modulo. Qui si prova che i due livelli esistono davvero — che il
secondo decide **solo** a parita' del primo, e che non lo peggiora."""
import pytest

from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _istanza_con_pareggio_di_ore(env):
    """Quattro fasce per la classe, sei ore da piazzare: un blocco da 2h e
    quattro ore singole. Due ore vanno lasciate fuori, e ci sono **due modi
    che pareggiano in ore**: scartare il blocco da 2h (una attivita') oppure
    due ore singole (due attivita').

    E' il pareggio che L1 non sa sciogliere, e che L2 scioglie."""
    lungo = make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]], slots=2)
    singole = [make_activity(env["subject"], teachers=[env["teacher"]],
                             classes=[env["klass"]]) for _ in range(4)]
    return lungo, singole


def test_l2_scioglie_il_pareggio_di_l1():
    """A parita' di **ore** scartate, si scarta il minor numero di
    **attivita'**: il blocco da 2h esce da solo invece di far uscire due ore
    singole.

    Verificato per mutazione: con la catena troncata a L1 (`livelli_di_scarto`
    che restituisce il solo primo livello) questa istanza risponde con due
    attivita' scartate, cioe' l'altra faccia del pareggio."""
    env = mini_school(days=1, slots=4)
    lungo, singole = _istanza_con_pareggio_di_ore(env)

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["minuti_scartati"] == 120, soluzione.stats
    assert soluzione.stats["scartate"] == 1, soluzione.stats
    assert soluzione.unplaced == (lungo.id,)
    assert all(s.id in soluzione.placements for s in singole)


def test_la_catena_riporta_ogni_livello():
    """I livelli sono dichiarati negli `stats` — nome, valore, se l'ottimo e'
    stato **dimostrato** e quanto e' costato. Senza, non si sa quale livello
    consuma il tempo, e un livello che scade sarebbe indistinguibile da uno
    che ha concluso."""
    env = mini_school(days=1, slots=4)
    _istanza_con_pareggio_di_ore(env)

    livelli = solve(env["schedule"], workers=1).stats["livelli"]
    assert [l["nome"] for l in livelli] == ["minuti_scartati", "attivita_scartate"]
    assert [l["valore"] for l in livelli] == [120, 1]
    assert all(l["ottimo"] for l in livelli)
    assert all(l["secondi"] >= 0 for l in livelli)


def test_il_fissaggio_impedisce_a_l2_di_peggiorare_l1():
    """La monotonia della catena, che e' la sua unica proprieta' davvero
    necessaria — e l'istanza e' costruita perche' i due livelli **tirino in
    direzioni opposte**, altrimenti il test non afferma niente.

    Quattro fasce, e da piazzare un blocco da 3h piu' tre ore singole (6h in
    tutto). Due strade sole:

    - 3h + un'ora singola = 4 fasce piene → fuori **due ore** in **due**
      attivita';
    - le tre ore singole = 3 fasce → fuori **tre ore** in **una** attivita'.

    L1 (le ore) vuole la prima, L2 (il numero) vorrebbe la seconda. Con il
    fissaggio L2 sceglie *dentro* l'ottimo di L1 e la seconda strada non e'
    piu' disponibile; senza, L2 la prende e la catena peggiora cio' che il
    livello precedente aveva deciso.

    ⚠ Verificato per mutazione — ed e' la ragione per cui questo test esiste
    in questa forma: con l'istanza a pareggio del test precedente, togliere
    `model.Add(level.var <= valore)` lasciava la suite **verde**, perche' li'
    le due direzioni coincidevano."""
    env = mini_school(days=1, slots=4)
    lungo = make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]], slots=3)
    singole = [make_activity(env["subject"], teachers=[env["teacher"]],
                             classes=[env["klass"]]) for _ in range(3)]

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["minuti_scartati"] == 120, soluzione.stats
    assert soluzione.stats["scartate"] == 2, soluzione.stats
    assert lungo.id in soluzione.placements, (
        "scartato il blocco da 3h: L2 ha scavalcato L1, cioe' il fissaggio "
        "non sta mordendo")
    assert sum(1 for s in singole if s.id in soluzione.placements) == 1


def test_senza_scarto_la_catena_non_esiste():
    """Con `allow_unplaced=False` non c'e' niente da minimizzare: il modello
    torna a essere di pura soddisfacibilita', e gli `stats` lo dicono invece di
    fingere una catena vuota di livelli conclusi."""
    env = mini_school(days=1, slots=4)
    _istanza_con_pareggio_di_ore(env)

    soluzione = solve(env["schedule"], workers=1, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE"
    assert soluzione.stats["livelli"] == ()


def test_un_livello_che_non_conclude_non_annulla_i_precedenti():
    """Il ramo di caduta della catena. Un livello che non trova nulla entro il
    proprio limite di tempo ferma la catena, ma cio' che si restituisce e' la
    fotografia dell'**ultimo livello concluso** — non un `UNKNOWN` che butta
    via il lavoro gia' fatto. E il livello mancato resta dichiarato negli
    esiti, con `valore` a `None`.

    Il solver e' iniettato apposta: far scadere un livello davvero
    richiederebbe un'istanza difficile e un limite stretto, cioe' un test che
    fallisce a intermittenza su una macchina piu' lenta."""
    from ortools.sat.python import cp_model

    from domain.solver.objective import Level, solve_chain

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(4)]
    model.Add(sum(x) <= 2)
    primo = model.NewIntVar(0, 4, "primo")
    model.Add(primo == sum(1 - v for v in x))
    secondo = model.NewIntVar(0, 4, "secondo")
    model.Add(secondo == x[0] + x[1])

    class _SolverCheCadeAlSecondo:
        """Il primo livello passa da CP-SAT vero, il secondo torna UNKNOWN."""

        def __init__(self):
            self._vero = cp_model.CpSolver()
            self.parameters = self._vero.parameters
            self.chiamate = 0

        def Solve(self, m):
            self.chiamate += 1
            if self.chiamate == 1:
                return self._vero.Solve(m)
            return cp_model.UNKNOWN

        def Value(self, var):
            return self._vero.Value(var)

    finto = _SolverCheCadeAlSecondo()
    stato, soluzione, esiti = solve_chain(
        model, [Level("primo", primo), Level("secondo", secondo)],
        estrai=lambda s: {i: s.Value(v) for i, v in enumerate(x)},
        solver=finto)

    assert stato == cp_model.OPTIMAL          # lo stato dell'ultimo concluso
    assert soluzione is not None              # e la sua soluzione, non None
    assert [e.nome for e in esiti] == ["primo", "secondo"]
    assert esiti[0].valore == 2 and esiti[0].ottimo
    assert esiti[1].valore is None and not esiti[1].ottimo


def test_un_livello_che_non_dimostra_l_ottimo_lo_dichiara():
    """`ottimo` non e' decorativo: distingue «questo e' il minimo» da «questo
    e' il meglio che ho trovato prima che scadesse il tempo». La catena resta
    corretta in entrambi i casi — il fissaggio usa il valore trovato — ma meno
    ambiziosa, e chi legge gli `stats` deve poterlo vedere.

    Anche qui il solver e' iniettato: un livello che scade davvero renderebbe
    il test dipendente dalla velocita' della macchina."""
    from ortools.sat.python import cp_model

    from domain.solver.objective import Level, solve_chain

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(4)]
    model.Add(sum(x) <= 2)
    primo = model.NewIntVar(0, 4, "primo")
    model.Add(primo == sum(1 - v for v in x))

    class _SolverCheNonDimostra:
        """Risolve davvero, ma dichiara FEASIBLE invece di OPTIMAL."""

        def __init__(self):
            self._vero = cp_model.CpSolver()
            self.parameters = self._vero.parameters

        def Solve(self, m):
            stato = self._vero.Solve(m)
            return cp_model.FEASIBLE if stato == cp_model.OPTIMAL else stato

        def Value(self, var):
            return self._vero.Value(var)

    stato, soluzione, esiti = solve_chain(
        model, [Level("primo", primo)],
        estrai=lambda s: {i: s.Value(v) for i, v in enumerate(x)},
        solver=_SolverCheNonDimostra())

    assert stato == cp_model.FEASIBLE
    assert soluzione is not None
    assert esiti[0].valore == 2, "il valore trovato si legge comunque"
    assert not esiti[0].ottimo, "un livello non dimostrato non puo' dirsi ottimo"


def test_l3_conta_le_quote_consumate_e_le_riparazioni_mancate():
    """L3 — le violazioni **nuove** che il modello si concede — e i suoi due
    conteggi, provati sul conteggio che è più facile dimenticare.

    Qui la riparazione è **impossibile**: `min_days=3` su una griglia di due
    giorni, con una congelata che rende la baseline già violata. Il ramo
    disgiuntivo di ADR-018 esiste, il modello sceglie lo status quo, e L3 deve
    contare quella riparazione mancata: vale 1.

    ⚠ Il conteggio delle riparazioni mancate è la metà che una mutazione
    lascerebbe passare senza questo test: le quote consumate si vedono anche
    altrove, le riparazioni no.

    🔑 La **preferenza** per la riparazione — il debito di §9.7 — non si prova
    qui ma nel banco che congela: dopo L3 il fenomeno non compare più su 60
    semi, e l'esenzione che lo perdonava è stata rimossa
    (`tests/solver_harness.py::_classifica_nuove`). Un test giocattolo su
    questa proprietà non discriminerebbe, perché senza L3 il solver può
    scegliere la soluzione riparata **per caso**: misurato, restava verde con
    la mutazione."""
    from domain.models import Activity, Placement, ResourceTimeConstraint

    env = mini_school(days=2, slots=2)
    congelata = make_activity(env["subject"], teachers=[env["teacher"]],
                              classes=[env["klass"]])
    Activity.objects.filter(pk=congelata.pk).update(
        immobility=Activity.Immobility.FIXED)
    Placement.objects.create(schedule=env["schedule"], activity=congelata,
                             day=0, start_slot=0)
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"],
        type=ResourceTimeConstraint.Type.MIN_DISTRIBUTION,
        params={"min_days": 3, "min_minutes_per_day": 60})

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    livelli = {l["nome"]: l["valore"] for l in soluzione.stats["livelli"]}
    assert list(livelli) == ["minuti_scartati", "attivita_scartate",
                             "violazioni_nuove"]
    assert livelli["violazioni_nuove"] == 1, (
        "la riparazione mancata non è contata: L3 sta guardando solo le quote")


def test_l3_non_consuma_una_quota_se_non_serve():
    """L'altra metà: sotto il tetto della quota se ne consuma il **meno
    possibile**. Con un alleggerimento disponibile ma un orario che sta in
    piedi senza, L3 vale zero — la quota è un tetto, non un budget da spendere."""
    from domain.models import RelaxationQuota, ResourceTimeConstraint

    env = mini_school(days=2, slots=2)
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HOURS,
        params={"day_minutes": 60})
    RelaxationQuota.objects.create(
        family=RelaxationQuota.Family.MAX_HOURS, resource=env["klass"],
        max_violations=2, params={"margine": 60})

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    livelli = {l["nome"]: l["valore"] for l in soluzione.stats["livelli"]}
    assert livelli["violazioni_nuove"] == 0, (
        "il solver ha consumato una quota che non gli serviva")


def test_l4_conserva_le_collocazioni_precedenti():
    """La stabilità fra periodi, che è la conseguenza di ADR-010 rimasta
    scoperta da luglio: rigenerando l'orario a ogni periodo serve un criterio
    «mantieni il più possibile le collocazioni precedenti», o il secondo
    quadrimestre viene stravolto per tutti.

    ⚠ L'istanza è costruita perché il test **discrimini**: le tre ore sono
    piazzate a mano in una disposizione **insolita** — le ultime fasce degli
    ultimi giorni — che nessun solver sceglierebbe da sé. Con L4 restano dove
    sono; senza, CP-SAT le raccoglie all'inizio della settimana, che è il suo
    ordine naturale.

    Verificato per mutazione: togliendo L4 dalla catena, le collocazioni
    cambiano tutte e tre."""
    from domain.models import Placement

    env = mini_school(days=5, slots=2)
    attivita = [make_activity(env["subject"], teachers=[env["teacher"]],
                              classes=[env["klass"]]) for _ in range(3)]
    insolite = {attivita[0].id: (4, 1), attivita[1].id: (3, 1),
                attivita[2].id: (2, 1)}
    for aid, (day, slot) in insolite.items():
        Placement.objects.create(schedule=env["schedule"], activity_id=aid,
                                 day=day, start_slot=slot)

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.placements == insolite, (
        "le collocazioni precedenti non sono state conservate: L4 non sta "
        "mordendo")
    livelli = {l["nome"]: l["valore"] for l in soluzione.stats["livelli"]}
    assert livelli["spostamenti"] == 0


def test_l4_cede_a_tutto_il_resto():
    """L'**ordine** della catena, provato dove l'ordine cambia la risposta: la
    stabilità è ultima, quindi conservare una collocazione non vale uno scarto.

    Un giorno di due fasce. `vecchia` è già piazzata in (0,0). `nuova` non è
    mai stata piazzata e può stare **solo** in (0,0), perché il suo docente è
    indisponibile nell'altra fascia; le due condividono la classe, quindi in
    (0,0) non ci stanno insieme.

    - Con L1 prima: si piazzano entrambe, e `vecchia` si sposta in (0,1) —
      zero scarti, uno spostamento.
    - Con L4 prima: `vecchia` resta dov'è e `nuova` viene scartata — zero
      spostamenti (una mai piazzata non «si sposta»), un'ora persa.

    ⚠ Il primo test scritto per questa proprietà **non discriminava**: due ore
    accatastate nella stessa cella davano un movimento in entrambi gli ordini,
    perché anche scartare un'attività già piazzata conta come spostamento.
    Verificato per mutazione: mettendo `spostamenti` in testa alla catena,
    questo test diventa rosso."""
    from domain.models import ResourceUnavailability, Placement, Teacher

    env = mini_school(days=1, slots=2)
    vecchia = make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]])
    Placement.objects.create(schedule=env["schedule"], activity=vecchia,
                             day=0, start_slot=0)
    altro = Teacher.objects.create(name="Bianchi Ugo", last_name="Bianchi",
                                   first_name="Ugo")
    ResourceUnavailability.objects.create(resource=altro, day=0, slot=1,
                                          level="hard")
    nuova = make_activity(env["subject"], teachers=[altro],
                          classes=[env["klass"]])

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["scartate"] == 0, (
        "ha preferito scartare invece di spostare: la stabilità è finita "
        "davanti allo scarto nella catena")
    assert soluzione.placements[nuova.id] == (0, 0)
    assert soluzione.placements[vecchia.id] == (0, 1)
    livelli = {l["nome"]: l["valore"] for l in soluzione.stats["livelli"]}
    assert livelli["spostamenti"] == 1


def test_il_suggerimento_passa_da_un_livello_al_successivo():
    """Ogni livello riparte dalla soluzione del precedente. ⚠ Non è una
    rifinitura: senza, il secondo livello ricalcola da zero un orario già
    trovato — misurato sul Fermi, 4,07 s contro 0,27 s.

    Qui si guarda il **meccanismo**, non il tempo: un test sul cronometro
    sarebbe flaky su una macchina più lenta."""
    from ortools.sat.python import cp_model

    from domain.solver.objective import Level, solve_chain

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{i}") for i in range(4)]
    model.Add(sum(x) <= 2)
    primo = model.NewIntVar(0, 4, "primo")
    model.Add(primo == sum(1 - v for v in x))
    secondo = model.NewIntVar(0, 4, "secondo")
    model.Add(secondo == x[0] + x[1])

    chiamate = []
    solve_chain(model, [Level("primo", primo), Level("secondo", secondo)],
                estrai=lambda s: {i: s.Value(v) for i, v in enumerate(x)},
                suggerisci=lambda m, s: chiamate.append(s.Value(primo)))
    assert len(chiamate) == 2, (
        "il suggerimento non viene passato a ogni livello concluso")


def test_i_suggerimenti_si_sostituiscono_invece_di_accumularsi():
    """⚠ `AddHint` accumula: senza `ClearHints` il proto cresce di una copia
    dei letterali per ogni livello, e a quattro livelli sono quattro copie di
    tutto il modello. Qui si risolve con la **stessa** funzione che usa
    `solve()` e si conta quanti suggerimenti restano nel proto."""
    from domain.solver.model import build_model, solve
    from domain.solver.objective import livelli, solve_chain

    env = mini_school(days=2, slots=2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    model, ctx = build_model(env["schedule"])
    catena = livelli(ctx, model)
    assert len(catena) >= 2, "serve più di un livello perché la domanda esista"

    def suggerisci(m, s):
        m.ClearHints()
        for var in ctx.x.values():
            m.AddHint(var, s.Value(var))

    solve_chain(
        model, catena, suggerisci=suggerisci, workers=1,
        estrai=lambda s: {aid: (d, f) for (aid, d, f), v in ctx.x.items()
                          if s.Value(v)})
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    assert len(proto.solution_hint.vars) == len(ctx.x), (
        f"{len(proto.solution_hint.vars)} suggerimenti per {len(ctx.x)} "
        f"variabili: si stanno accumulando")
    assert solve(env["schedule"], workers=1).status == "OPTIMAL"
