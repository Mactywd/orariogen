"""I criteri di qualità: i livelli della catena che parlano di **come** è
l'orario, non di quanto è fallito.

I quattro livelli di `objective.py` misurano tutti un fallimento — ore
scartate, attività scartate, violazioni nuove, spostamenti. Un orario che
piazza tutto senza violare nulla è indistinguibile, per quella catena, da un
altro che fa lo stesso lasciando a un docente quattro buchi al giorno. Questi
livelli li distinguono, e stanno **sotto** i quattro: la qualità cede a tutto
il resto, come già la stabilità.

🔑 **La proprietà che rende il pezzo economico**: quasi tutte queste quantità
sono già calcolate da un checker di `domain/analysis`, dove servono a essere
confrontate con un tetto. Qui la stessa quantità si **minimizza**. Dove il
checker esiste, la definizione si legge da lì e non si riscrive — la stessa
regola che vale per `B` nei rami disgiuntivi di ADR-018, e per la stessa
ragione: una divergenza di uno renderebbe il livello la misura di
qualcos'altro.

⚠ **Un criterio non cambia ciò che il modello ammette.** Posta variabili e
uguaglianze di definizione, mai un vincolo che escluda una soluzione. Ne
discende che ADR-018 non ha niente da dire su questa famiglia — ed è la prima
di cui è vero: le congelate contribuiscono termini costanti a una somma da
minimizzare, e non esiste il «pretendere una riparazione» perché non esiste
alcuna pretesa.

🔑 **Le firme di settimana, dal 2026-08-31 (L7).** Queste quantità si
calcolavano sull'**unione** delle settimane (`signature` omessa), ed era il
difetto che l'ora quindicinale del banco ha reso misurabile: il 5B con
l'italiano alla prima e alla quarta fascia, la metà di laboratorio alla
seconda e quella di teoria alla terza, ha un buco di 60 minuti in *ogni*
settimana dell'anno — la 2 nelle settimane pari, la 1 nelle dispari — e
sull'unione (0-1-2-3 occupate) di buchi non ce n'è nessuno. Lo stesso orario
valeva 60 minuti per `check_schedule` e **zero** per il criterio `gaps`.

Ora ogni criterio si calcola **per firma** (`firme()` qui sotto) e il valore
del livello è quello della **settimana peggiore** (`peggiore()`).

⚠ **Il massimo, e non la somma**, e la ragione è la regola della casa: *dove
il checker esiste, la definizione si legge da lì*. Il checker produce un
verdetto **per firma** e porta le settimane in un campo a parte
(`Finding.weeks`); la sua unità è la settimana. Sommare le firme direbbe 120
dove il checker dice 60, cioè misurerebbe qualcos'altro — e il numero
dipenderebbe da quante firme ha il dataset invece che da com'è l'orario.
Pesare per il numero di settimane sarebbe la quantità annuale, vera ma di
un'altra unità: romperebbe la stessa identità, e con essa
`Arbitrato.tolleranza`, che è un numero **nell'unità del criterio** e che
l'utente scrive a mano.

⚠ Il prezzo è dichiarato: sul massimo, migliorare una firma che non è la
peggiore non muove il livello. Non è la perdita che sembra — il massimo
trascina comunque *tutte* le firme fino al proprio pavimento — ma all'ottimo
una firma già sotto il massimo non ha più incentivo a scendere.

⚠ E il costo: le firme sono una dimensione moltiplicativa. È mitigato dalla
deduplicazione di `firme()`, la stessa di `ResourceBuilder` — due firme con
le stesse attività attive *sulle chiavi del criterio* sono un calcolo solo — e
su un dataset a firma unica, cioè ogni dataset senza corsi quindicinali né
sostituzioni, non c'è nessun costo e nessun numero cambia.

🔑 **E l'invariante «solo definizioni» incassa qui un dividendo non previsto.**
Perché un criterio non posta vincoli di ammissibilità, lo si può valutare su un
orario **dato** semplicemente chiamandolo con i letterali di cella sostituiti da
costanti: è così che `Arbitrato` calcola la base della non-regressione senza
riscrivere una seconda volta la definizione del criterio."""

from dataclasses import dataclass, replace

from ortools.sat.python import cp_model

from domain.models import QualityCriterion, Resource
from domain.solver.vocabulary import Vocabulary

_CRITERI = {}

_POPOLAZIONI = {
    QualityCriterion.Population.TEACHERS: {Resource.Kind.TEACHER},
    QualityCriterion.Population.CLASSES: {Resource.Kind.CLASS,
                                          Resource.Kind.CLASS_PART},
}


def register(kind):
    """Un criterio è una funzione `(ctx, model, chiavi) -> (espressione, max)`.
    Restituisce l'espressione da minimizzare e il suo estremo superiore, che
    serve a dichiarare il dominio dell'`IntVar` del livello."""
    def deco(fn):
        _CRITERI[kind] = fn
        return fn
    return deco


def chiavi_di(ctx, popolazione):
    """Le chiavi di risorsa su cui il criterio conta.

    ⚠ Gli **atomi** di ADR-017 restano fuori. Non compaiono in `state.kinds`
    perché non sono risorse: sono celle del prodotto delle partizioni, cioè una
    congiunzione sintetica. Contarne i buchi significherebbe contare i buchi di
    nessuno — e comunque li conta già la parte da cui l'atomo nasce.

    ⚠ Le chiavi di **parte di classe** contano invece per conto proprio accanto
    a quelle di classe, e non è un doppio conteggio per distrazione: il
    contatore `A.iso.` di EDT è dichiarato «per docente/classe/**gruppo**»."""
    kinds = ctx.states[ctx.signatures[0][0]].kinds
    ammessi = _POPOLAZIONI.get(popolazione)
    viste = {key for aid in ctx.activities for key in ctx.tokens[aid]}
    return sorted(
        (k for k in viste
         if k in kinds and (ammessi is None or kinds[k] in ammessi)),
        key=str)


def firme(ctx, chiavi):
    """Le firme di settimana che un criterio su `chiavi` deve distinguere.

    Deduplica come `ResourceBuilder`: due firme che hanno le stesse attività
    attive **su quelle chiavi** producono la stessa espressione, quindi si
    calcolano una volta sola. Su un dataset a firma unica restituisce una voce
    e il criterio è, riga per riga, quello di prima."""
    ammesse = set(chiavi)
    viste = {}
    for rep, _settimane in ctx.signatures:
        attive = frozenset(
            aid for aid in ctx.states[rep].activities
            if aid in ctx.activities and (set(ctx.tokens[aid]) & ammesse))
        viste.setdefault(attive, rep)
    return sorted(viste.values())


def peggiore(model, nome, per_firma):
    """`(espressione, massimo)` del criterio a partire da una voce per firma.

    Il valore è quello della **settimana peggiore**: con una firma sola è
    l'espressione stessa, senza una variabile in più — la proprietà
    conservativa che tiene fermi tutti i numeri già misurati."""
    if not per_firma:
        return 0, 0
    massimo = max(m for _e, m in per_firma)
    if len(per_firma) == 1:
        return per_firma[0][0], massimo
    var = model.NewIntVar(0, massimo, f"qualita_max_{nome}")
    model.AddMaxEquality(var, [e for e, _m in per_firma])
    return var, massimo


def _nome(riga):
    return f"{riga.kind}_{riga.population}"


@dataclass(frozen=True)
class Arbitrato:
    """La separazione per popolazione, con la **perdita di qualità tollerata**.

    EDT non cerca mai un ottimo congiunto: i comandi sono due, `Ottimizza gli
    orari dei docenti` e `... delle classi`, e l'enum interna è
    `TypeTypeOptim = ttoProfs, ttoClasses`. Chi lancia dichiara quale
    popolazione si ottimizza e **quanto è disposto a peggiorare l'altra**.

    ⚠ Non è un peso in una somma: è un **vincolo di non-regressione con
    budget**, che è la frase con cui `motore-risoluzione.md` lo descrive. La
    popolazione sacrificata non si ottimizza — i suoi criteri smettono di
    essere livelli e diventano tetti — e questo è il punto del meccanismo, non
    un effetto collaterale: ordinare i `rank` avrebbe dato la priorità senza
    togliere il costo.

    `tolleranza` è **per criterio, nell'unità del criterio** (minuti per i
    buchi, conteggi per gli altri). Un budget unico su criteri di unità diverse
    sarebbe la somma pesata che qui si rifiuta a ogni livello; ed è la stessa
    forma di `RelaxationQuota.params["margine"]`, che è pure un numero per
    famiglia nell'unità della famiglia."""

    popolazione: str
    tolleranza: int = 0

    def __post_init__(self):
        ammesse = (QualityCriterion.Population.TEACHERS,
                   QualityCriterion.Population.CLASSES)
        if self.popolazione not in ammesse:
            # ⚠ `ALL` non è una popolazione di EDT: è la nostra estensione per
            # il criterio che **non prende parte**, e non può quindi essere né
            # quella ottimizzata né quella sacrificata.
            raise ValueError(f"popolazione non arbitrabile: {self.popolazione}")

    @property
    def sacrificata(self):
        P = QualityCriterion.Population
        return P.CLASSES if self.popolazione == P.TEACHERS else P.TEACHERS

    def sacrifica(self, riga):
        return riga.population == self.sacrificata


def livelli_di_qualita(ctx, model, arbitrato=None):
    """I livelli di qualità, nell'ordine dichiarato dalle righe.

    Tabella vuota ⇒ lista vuota ⇒ la catena di prima di questo pezzo, senza
    una variabile in più. È la proprietà conservativa per costruzione, e come
    per le quote è un test e non un corollario.

    Con un `Arbitrato`, le righe della popolazione **sacrificata** non
    diventano livelli: la loro quantità si costruisce lo stesso — serve a
    essere confrontata — ma finisce sotto un tetto di non-regressione invece
    che dentro un `Minimize`.

    🔑 **Restituisce fabbriche, non variabili** (2026-08-31, con O5). Un
    criterio costruisce migliaia di variabili derivate, e costruirle tutte
    prima che la catena parta le faceva pagare anche ai livelli **sopra** di
    lui, che non ne fanno alcun uso: sul banco, un criterio al sesto livello
    portava il primo da 9,2 s a 33,6 s. Ogni fabbrica si chiama immediatamente
    prima del proprio `Solve` — vedi il docstring di `Level`.

    ⚠ I **tetti** della popolazione sacrificata restano invece costruiti
    subito, e devono: quelli restringono."""
    from domain.solver import criteria  # noqa: F401 — forza la registrazione

    def fabbrica(riga):
        def costruisci(model):
            espressione, massimo = _CRITERI[riga.kind](
                ctx, model, chiavi_di(ctx, riga.population))
            if massimo <= 0:
                return None   # niente da misurare su queste chiavi
            var = model.NewIntVar(0, massimo, f"qualita_{_nome(riga)}")
            model.Add(var == espressione)
            return var
        return costruisci

    livelli, sacrificati = [], []
    for riga in QualityCriterion.objects.all():   # Meta.ordering: rank, kind
        if riga.kind not in _CRITERI:
            # Un criterio dichiarato nell'enum ma non ancora tradotto. Si
            # salta invece di fallire: l'enum è il vocabolario del prodotto,
            # e una riga che nessun builder legge è un criterio *ignorato* —
            # esattamente ciò che la lista «Criteri ignorati» di EDT esprime.
            continue
        if arbitrato is not None and arbitrato.sacrifica(riga):
            var = fabbrica(riga)(model)
            if var is not None:
                sacrificati.append((riga, var))
        else:
            livelli.append((_nome(riga), fabbrica(riga)))

    if sacrificati:
        _posta_i_tetti(ctx, model, arbitrato, sacrificati)
    return livelli


def _posta_i_tetti(ctx, model, arbitrato, sacrificati):
    """`valore <= base + tolleranza`, e il rendiconto su `ctx.arbitraggi`.

    ⚠ Un tetto può rendere il modello **infattibile**: l'orario di partenza lo
    soddisfa per costruzione, ma può essere illegale rispetto ai vincoli hard
    (qui un orario in violazione è uno stato ammesso) e quindi irraggiungibile.
    Cade dalla parte giusta del criterio di ADR-018 — vietare un peggioramento
    è ammesso, pretendere una riparazione no — e un tetto di non-regressione è
    la definizione stessa di «vieta un peggioramento»."""
    base = _valori_di_base(ctx, [riga for riga, _ in sacrificati])
    for riga, var in sacrificati:
        nome = _nome(riga)
        if base is None:
            ctx.arbitraggi.append({"nome": nome, "base": None, "tetto": None})
            continue
        tetto = base[nome] + arbitrato.tolleranza
        model.Add(var <= tetto)
        ctx.arbitraggi.append({"nome": nome, "base": base[nome], "tetto": tetto})


def _assegnazione_di_partenza(ctx):
    """`{(id, giorno, fascia): 0|1}` dall'orario che c'è, o `None` se non c'è
    un orario di partenza utilizzabile.

    Due condizioni, e cadono entrambe dalla parte prudente. **Ogni** attività
    libera dev'essere già piazzata: su un orario parziale la base sarebbe
    ottimisticamente bassa — un orario vuoto non ha buchi — e il tetto
    diventerebbe una pretesa assurda. E ogni vecchia collocazione dev'essere
    **sopravvissuta ai pre-filtri**: se non è più ammissibile, quell'orario non
    è rappresentabile in questo modello e non è una base.

    ⚠ È la stessa precondizione di L4, che pure esiste solo con un orario
    precedente; e l'avvertimento letterale di EDT dice la stessa cosa dal suo
    lato — *«l'ottimizzazione tiene conto unicamente delle attività
    estratte»*."""
    scelte = {}
    for aid in ctx.activities:
        # la congelata ha per dominio la sola cella in cui sta (SolverContext)
        cella = (ctx.placed_before.get(aid) if aid in ctx.free
                 else next(iter(ctx.cells[aid]), None))
        if cella is None or cella not in ctx.cells[aid]:
            return None
        scelte[aid] = cella
    return {(aid, d, s): int((d, s) == scelte[aid])
            for aid in ctx.activities for (d, s) in ctx.cells[aid]}


def _valori_di_base(ctx, righe):
    """Il valore di ogni criterio **sull'orario di partenza**, o `None`.

    🔑 **Non è una seconda definizione del criterio: è la stessa funzione.** Un
    criterio posta solo definizioni — l'invariante dichiarato in testa a questo
    modulo — quindi basta chiamarlo su un modello usa-e-getta in cui i
    letterali di cella sono le **costanti** `0`/`1` dell'orario esistente:
    ogni booleano derivato è determinato per propagazione, e un `Solve`
    istantaneo restituisce il numero.

    L'alternativa era riscrivere i cinque criteri in Python su `ScheduleState`,
    cioè una seconda definizione della stessa quantità. È il difetto che questo
    progetto ha già intercettato due volte: `B` nei rami disgiuntivi di ADR-018
    si **legge** chiamando il checker, mai riscrivendone la condizione."""
    fissi = _assegnazione_di_partenza(ctx)
    if fissi is None:
        return None
    model = cp_model.CpModel()
    base = replace(ctx, x=fissi, placed_var={}, by_cell={}, vocab=None,
                   riparazioni=[], arbitraggi=[])
    base.index_cells()
    base.vocab = Vocabulary(base, model)

    variabili = {}
    for riga in righe:
        espressione, massimo = _CRITERI[riga.kind](
            base, model, chiavi_di(base, riga.population))
        var = model.NewIntVar(0, max(massimo, 0), f"base_{_nome(riga)}")
        model.Add(var == espressione)
        variabili[_nome(riga)] = var

    solver = cp_model.CpSolver()
    if solver.Solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None   # non può accadere: tutto è determinato. Ma se accadesse,
                      # nessun tetto è meglio di un tetto inventato.
    return {nome: solver.Value(var) for nome, var in variabili.items()}
