"""La catena lessicografica: risolvi per il criterio 1, **fissa** quel valore
come vincolo, passa al 2. Mai `minimize(w1*a + w2*b)`.

Non è una preferenza di stile. In EDT non esiste alcuna funzione di costo
numerica (`docs/edt/motore-risoluzione.md`): i compromessi si governano a
quote, a criteri ordinati e a perdita di qualità tollerata, e nessuno dei tre
è una somma pesata. Un peso è ingovernabile per chi usa il prodotto — nessun
vicepreside sa dire se un buco vale 3 o 5 — mentre un ordine di priorità si
spiega in una frase.

🔑 **E la strategia a due passate di EDT è questa catena, non due esecuzioni.**
«Il piazzamento rispetta automaticamente tutti i vincoli; se rimangono delle
attività scartate, potete alleggerire» è esattamente «L3 dopo L1»: il modello
consuma un alleggerimento solo quando quell'alleggerimento riduce gli scarti,
perché a scarti pari il livello successivo preferisce zero violazioni.

La catena ha quattro livelli: gli scarti in ore e in numero (D1), le
violazioni nuove che il modello si concede, e la stabilità fra periodi."""

import time
from dataclasses import dataclass, replace

from ortools.sat.python import cp_model

from domain.solver.quality import livelli_di_qualita

STATUS_NAME = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


#: Il budget predefinito di un livello di **qualità**, in secondi.
#:
#: 🔑 Serve dove un livello **non sa dimostrare l'ottimo**, e la ragione è
#: misurata: i livelli che contano un **fallimento** (ore scartate, attività,
#: violazioni nuove, spostamenti) chiudono dimostrando l'ottimo — sul Fermi in
#: 1,7 s e 0,7 s — perché il loro ottimo è zero e zero è anche il limite
#: inferiore banale, quindi valore e limite si toccano subito. I criteri di
#: qualità hanno ottimi **non nulli** con limiti inferiori inutili (misurato
#: sul Fermi: `free_half_days` 202 con limite 6, `regularity` 236 con limite
#: 18), quindi non concludono mai e senza budget `manage.py solve` **non
#: torna**: nove minuti senza risposta, misurati.
#:
#: ⚠ Un comando la cui configurazione predefinita non termina è un difetto, e
#: metterci un budget globale sarebbe stato il rimedio sbagliato — punirebbe
#: proprio i livelli che l'ottimo lo dimostrano. Il valore viene dalla curva:
#: dopo ~15 s il guadagno è marginale (`free_half_days` 202 a 15 s, 199 a 60 s;
#: `regularity` 236 e 226). `--limite` lo sovrascrive in entrambi i versi.
#:
#: ⚠ **Non è una proprietà della famiglia, ma della posizione**: la stabilità
#: dimostra l'ottimo finché sta in testa (conserva tutto e arriva a zero), e
#: lo perde quando l'arbitrato la manda in coda sotto i criteri. Lì prende
#: questo stesso budget — vedi `livelli()`.
BUDGET_QUALITA = 15.0


@dataclass(frozen=True)
class Level:
    nome: str
    var: object     # IntVar: il valore da minimizzare
    limite: float | None = None   # budget proprio, se il livello ne ha uno


@dataclass(frozen=True)
class Esito:
    nome: str
    valore: int | None   # None se il livello non ha concluso
    ottimo: bool         # False se ha restituito una soluzione senza dimostrarla
    secondi: float
    limite: int | None = None   # il limite inferiore dimostrato

    @property
    def divario(self):
        """Quanto manca, al peggio, all'ottimo di questo livello.

        🔑 **«Ottimo non dimostrato» da solo non è un'informazione.** Un
        livello che si ferma a 66 con un limite inferiore di 64 ha finito il
        lavoro; uno che si ferma a 66 con un limite di 10 non ha ancora
        cominciato, e i due si leggevano identici. CP-SAT il numero ce l'ha
        (`BestObjectiveBound`) e lo buttavamo via."""
        if self.valore is None or self.limite is None:
            return None
        return self.valore - self.limite

    def as_dict(self):
        return {"nome": self.nome, "valore": self.valore,
                "ottimo": self.ottimo, "secondi": self.secondi,
                "limite": self.limite, "divario": self.divario}


def livelli(ctx, model, arbitrato=None):
    """La catena, da L1 a L4. ⚠ **L'ordine è la decisione D1 della spec**:
    prima le ore, poi
    il numero di attività come spareggio. Uno scarto da 3h fa più danno al
    monte ore di una classe di tre da 1h; EDT conta le attività nella propria
    finestra ma riporta entrambi («284 attività / 288h00»), quindi la scelta
    non contraddice il prodotto: ne fissa lo spareggio.

    Entrambi i livelli passano da un `IntVar` con **dominio dichiarato**: è il
    posto dove leggere il valore del livello dopo il solve, e non costa nulla.
    ⚠ Il dominio da solo **non** difende dall'espansione dell'obiettivo in
    presolve — quella la spegne `presolve_substitution_level = 0` in
    `solve_chain`, con la misura scritta lì."""
    if not ctx.placed_var:
        # `placed_var` è vuoto in **due** casi distinti, e la catena si spegne
        # in entrambi: nessuna attività libera (niente da decidere), oppure
        # `allow_unplaced=False`, il modello che pretende il piazzamento.
        #
        # ⚠ Nel secondo caso la rinuncia non esiste, quindi L1/L2 non hanno
        # oggetto — ma L3 e L4 sì, e restano spenti lo stesso. È una scelta,
        # non una dimenticanza: `allow_unplaced=False` serve a chiedere
        # «questo vincolo morde?», e la risposta dev'essere quella del modello
        # hard nudo, non quella di un modello che sceglie *anche* fra le
        # violazioni ammissibili. Chi lo usa (i test dei builder, e la
        # direzione 1 dell'oracolo di Hall) misura l'ammissibilità, mai la
        # preferenza. Conseguenza da conoscere: in quella modalità le quote
        # non sono minimizzate, il ramo status quo di ADR-018 torna a essere
        # alla pari con la riparazione, e **nessun criterio di qualità** viene
        # posto — per la stessa ragione, non per dimenticanza: chi chiede
        # «questo vincolo morde?» non vuole un modello che sceglie anche fra
        # gli orari legali.
        return []

    minuti_totali = sum(ctx.activities[aid].duration_minutes for aid in ctx.placed_var)
    minuti = model.NewIntVar(0, minuti_totali, "minuti_scartati")
    model.Add(minuti == sum(ctx.activities[aid].duration_minutes * (1 - piazzata)
                            for aid, piazzata in ctx.placed_var.items()))

    numero = model.NewIntVar(0, len(ctx.placed_var), "attivita_scartate")
    model.Add(numero == sum(1 - piazzata for piazzata in ctx.placed_var.values()))

    catena = [Level("minuti_scartati", minuti), Level("attivita_scartate", numero)]

    # L3 — le violazioni **nuove** che il modello si concede: le quote
    # consumate e le riparazioni mancate. Due conteggi distinti sommati in un
    # livello solo: nessuno dei due pesa più dell'altro, ed è un conteggio, non
    # una somma pesata.
    #
    # 🔑 Ed è qui che si chiude il debito di §9.7 della spec del modello hard.
    # I rami disgiuntivi di ADR-018 offrono «ripara **oppure** non peggiorare»,
    # e senza funzione di costo i due rami erano alla pari: CP-SAT non aveva
    # nessun motivo di preferire la riparazione, e nel solve incrementale il
    # ramo status quo diventava vacuo. Minimizzare `riparato.Not()` non cambia
    # cosa il modello **ammette** — cambia cosa preferisce, che è esattamente
    # la forma di rimedio senza rischio semantico.
    #
    # ⚠ I due conteggi restano separati dove conta: una riparazione mancata
    # **non consuma quota**, perché non è un alleggerimento.
    quote = ctx.relax.letterali()
    mancate = [r.Not() for r in ctx.riparazioni]
    if quote or mancate:
        nuove = model.NewIntVar(0, len(quote) + len(mancate), "violazioni_nuove")
        model.Add(nuove == sum(quote) + sum(mancate))
        catena.append(Level("violazioni_nuove", nuove))
    stabilita = _stabilita(ctx, model)
    # I criteri di qualità. Tabella vuota ⇒ nessun livello e nessuna variabile:
    # è la catena di prima di quel pezzo, byte per byte. Con un `Arbitrato`, i
    # criteri della popolazione sacrificata non arrivano fin qui: restano nel
    # modello come tetti di non-regressione.
    qualita = [Level(nome, var, BUDGET_QUALITA)
               for nome, var in livelli_di_qualita(ctx, model, arbitrato)]

    # 🔑 **L'ordine fra stabilità e qualità dipende da che corsa è questa, e la
    # ragione è una misura, non un'opinione.** Con un orario di partenza
    # completo la stabilità raggiunge zero conservando tutto, e il suo
    # fissaggio inchioda ogni cella: **tutti i livelli di qualità diventano
    # inerti**. Misurato — quattro attività su una griglia 2×2, con la qualità
    # dei docenti che potrebbe scendere da 4 a 2 e restava a 4.
    #
    # In EDT i comandi sono due e il conflitto non si pone: `Piazzamento
    # automatico` costruisce, `Ottimizza gli orari dei docenti / delle classi`
    # rimescola un orario che c'è già — e rimescolare *è* lo scopo, non un
    # danno. Qui il comando è uno solo, quindi la corsa deve dichiararsi, e
    # `arbitrato` è esattamente quella dichiarazione: nominare la popolazione
    # da ottimizzare vuol dire «questa è un'ottimizzazione».
    #
    # Senza arbitrato vince la stabilità (ADR-010: rigenerando per il secondo
    # quadrimestre non si stravolge l'orario di tutti). Con l'arbitrato la
    # stabilità scivola in coda e diventa lo **spareggio**: fra due orari di
    # pari qualità, il più vicino a quello che c'è.
    #
    # 🔑 E scivolando in coda la stabilità prende **il budget della qualità**,
    # perché il budget appartiene alla posizione e non al livello. In testa la
    # stabilità è un livello che dimostra l'ottimo — conserva tutto e arriva a
    # zero, che è anche il suo limite inferiore banale. In coda quell'ottimo
    # non è più zero: i criteri sopra di lei hanno già spostato l'orario, e
    # dimostrare quanti spostamenti servano *davvero* è duro esattamente quanto
    # dimostrare un criterio di qualità. ⚠ Misurato sul Fermi con cinque
    # criteri: senza questa riga `--popolazione teachers` non torna in dodici
    # minuti; con `--limite 15` chiude in 52 s a `spostamenti 219`, ottimo non
    # dimostrato, non sotto 8. È lo stesso difetto che aveva prodotto
    # `BUDGET_QUALITA`, ricomparso al posto lasciato libero.
    coda = []
    if stabilita is not None:
        coda = [replace(stabilita, limite=BUDGET_QUALITA)
                if arbitrato is not None else stabilita]
    catena += (qualita + coda) if arbitrato is not None else (coda + qualita)
    return catena


def _stabilita(ctx, model):
    """L4 — la stabilità, o `None` senza un orario di partenza.

    Rigenerando l'orario a ogni periodo (ADR-010) serve un criterio «mantieni
    il più possibile le collocazioni precedenti», o il secondo quadrimestre
    viene stravolto per tutti: è la conseguenza che il progetto si porta dietro
    da luglio, ed è un livello lessicografico, non un'architettura. È anche ciò
    che EDT minimizza nel risolutore passo-passo («il numero di variabili che
    cambiano valore rispetto alla soluzione corrente»).

    ⚠ Cede sempre a L1-L3: un orario che conserva le collocazioni ma scarta
    un'ora in più è peggiore, non migliore. Dove si colloca rispetto alla
    **qualità** lo decide `livelli()`, e non è un dettaglio d'ordine."""
    mosse, fisse = [], 0
    for aid, cella in sorted(ctx.placed_before.items()):
        lit = ctx.x.get((aid, cella[0], cella[1]))
        if lit is None:
            # la vecchia cella non è più ammissibile (pre-filtri, o griglia
            # cambiata): l'attività è spostata comunque, e va contata perché
            # il numero riportato sia vero.
            fisse += 1
        else:
            mosse.append(lit)
    if not (mosse or fisse):
        return None
    spostate = model.NewIntVar(0, len(mosse) + fisse, "spostamenti")
    model.Add(spostate == len(mosse) + fisse - sum(mosse))
    return Level("spostamenti", spostate)


def solve_chain(model, levels, *, estrai, suggerisci=None, time_limit=None,
                workers=None, solver=None):
    """Percorre la catena e restituisce `(stato, soluzione, esiti)`.

    `estrai(solver)` fotografa la soluzione corrente: serve perché un livello
    che non conclude **non annulla il lavoro dei precedenti**. La catena si
    ferma lì, e ciò che si restituisce è la fotografia dell'ultimo livello
    concluso — con il livello mancato dichiarato negli esiti, non nascosto.

    `suggerisci(model, soluzione)` riporta la soluzione dell'ultimo livello
    concluso come **suggerimento** per il successivo. ⚠ Non è un'ottimizzazione
    opzionale quanto sembra: senza, ogni livello riparte da zero e rifà un
    lavoro già fatto — misurato sul Fermi, il secondo livello costava 4,07 s
    contro gli 0,47 s del primo, per riscoprire lo stesso orario. Il
    suggerimento non cambia cosa il modello ammette: se è infattibile, CP-SAT
    lo scarta.

    ⚠ Il limite di tempo è **per livello**, non per la catena: è la forma
    naturale (ogni livello è un `Solve`) e va detta, perché una catena di
    quattro livelli con `time_limit=60` può spendere quattro minuti. Un livello
    che scade lascia il proprio fissaggio all'ultimo valore trovato invece che
    all'ottimo: la catena resta corretta, diventa meno ambiziosa.

    ⚠ E `time_limit=None` non significa «nessun limite»: significa «vale il
    budget proprio di ogni livello», che è `None` per i livelli che dimostrano
    l'ottimo e `BUDGET_QUALITA` per i criteri di qualità, che non lo dimostrano
    mai. Vedi la misura in testa a quella costante.
    """
    # `solver` iniettabile: e' la cucitura con cui un test puo' far mancare un
    # livello **deterministicamente**, invece di sperare che un limite di tempo
    # morda. Il ramo «un livello non conclude» altrimenti non sarebbe affermato
    # da nessun test.
    solver = solver if solver is not None else cp_model.CpSolver()
    if workers is not None:
        solver.parameters.num_workers = int(workers)

    def budget(level):
        """`time_limit` esplicito vince su tutto — in entrambi i versi, anche
        allungando il budget di un livello di qualità: chi passa un numero sta
        rispondendo alla domanda «quanto tempo mi costa», e non gli si mette
        davanti un default. Senza, vale il budget proprio del livello, e per i
        livelli che dimostrano l'ottimo quel budget è `None`."""
        return time_limit if time_limit is not None else level.limite

    if not levels:
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = float(time_limit)
        stato = solver.Solve(model)
        ammesso = stato in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        return stato, (estrai(solver) if ammesso else None), ()

    # ⚠ Misurato, e non è un dettaglio di prestazioni: senza questo, la
    # presolve **espande l'obiettivo** («objective: expanded via tight
    # equality», 36 volte su un testimone da 32 attività). I booleani
    # `piazzata` spariscono, al loro posto entrano nell'obiettivo 723
    # letterali di cella, e il dominio iniziale passa da [0, 660] a
    # [-35460, 2040]. Il solver trova `best:0` in un decimo di secondo e poi
    # spende **sessanta secondi** a dimostrare che non esiste un ottimo
    # negativo — vero per costruzione, ma non più per lui. Con la sostituzione
    # spenta: `OPTIMAL` in 0,09 s.
    solver.parameters.presolve_substitution_level = 0

    esiti, soluzione, stato_buono = [], None, None
    for level in levels:
        limite = budget(level)
        solver.parameters.max_time_in_seconds = (
            float(limite) if limite is not None else 1e9)
        model.Minimize(level.var)
        inizio = time.monotonic()
        stato = solver.Solve(model)
        secondi = round(time.monotonic() - inizio, 3)
        if stato not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            esiti.append(Esito(level.nome, None, False, secondi))
            if soluzione is None:
                return stato, None, tuple(esiti)
            break
        valore = solver.Value(level.var)
        esiti.append(Esito(level.nome, valore, stato == cp_model.OPTIMAL,
                           secondi, int(solver.BestObjectiveBound())))
        soluzione, stato_buono = estrai(solver), stato
        if suggerisci is not None:
            suggerisci(model, solver)
        # il fissaggio: `<=` e non `==`, perché è un tetto sul livello già
        # deciso e la soluzione appena trovata resta ammissibile per costruzione
        model.Add(level.var <= valore)

    return stato_buono, soluzione, tuple(esiti)
