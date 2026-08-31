"""Le traduzioni dei criteri di qualità, una per `QualityCriterion.Kind`.

Ogni criterio è una funzione `(ctx, model, chiavi) -> (espressione, massimo)`:
l'espressione da minimizzare e il suo estremo superiore, che dichiara il
dominio dell'`IntVar` del livello. Nessuna posta vincoli di ammissibilità —
vedi il docstring di `quality.py`."""


from collections import defaultdict

from domain.models import QualityCriterion, ResourceUnavailability
from domain.solver.quality import firme, peggiore, register


@register(QualityCriterion.Kind.PREFERENCES)
def preferenze(ctx, model, chiavi):
    """`Rispetta le preferenze` — il pennello **verde**.

    ⚠ In EDT è l'**undicesimo e ultimo** dei criteri di piazzamento, e la sua
    posizione è la specifica: *«EDT cerca di tenerne conto, nessuna
    garanzia»*. Le preferenze cedono a tutto il resto. Che sia una riga di
    questa tabella e non un pre-filtro è la stessa affermazione, detta nel
    nostro modello: `UnavailabilityBuilder` restringe il rosso e il giallo e
    lascia passare il verde, rimandando qui per nome.

    La quantità è il numero di coppie **(chiave, fascia)** calpestate, non il
    numero di attività: è il conteggio che il checker già produce
    (`quantities={"slots": len(hit)}` per chiave in `UnavailabilityChecker`),
    e distingue un'attività di tre ore piazzata interamente su una mattinata
    sgradita da una che ne sfiora un'ora.

    ⚠ La copertura è su **tutta la durata**, non sulla sola fascia di
    partenza — lo stesso motivo per cui il pre-filtro guarda
    `range(slot, slot + duration_slots)` e il checker itera `pl.slots`.

    ⚠ Anche le **congelate** contribuiscono, e devono: il livello riporta il
    costo dell'orario, non quello della sola parte che il solver ha scelto. Il
    loro termine è una costante, il che è tutto ciò che ADR-018 ha da dire su
    un criterio di qualità.

    ⚠ Il verde è **datato quanto l'indisponibilità**: una preferenza che vale
    solo in certe settimane compare nello `state` di quelle firme e non delle
    altre, quindi va letta per firma come tutto il resto (L7)."""
    ammesse = set(chiavi)
    per_firma = []
    for rep in firme(ctx, chiavi):
        stato = ctx.states[rep]
        verdi = {(key, day, slot)
                 for (key, day, slot), livello in stato.unavailability.items()
                 if livello == ResourceUnavailability.Level.PREFERENCE}
        if not verdi:
            continue
        per_attivita = defaultdict(list)
        for aid in sorted(ctx.activities):
            if aid not in stato.activities:
                continue
            durata = ctx.activities[aid].duration_slots
            toccate = [k for k in ctx.tokens[aid] if k in ammesse]
            for (day, slot) in sorted(ctx.cells[aid]):
                colpi = sum(1 for key in toccate
                            for s in range(slot, slot + durata)
                            if (key, day, s) in verdi)
                if colpi:
                    per_attivita[aid].append((colpi, ctx.x[(aid, day, slot)]))
        if not per_attivita:
            continue
        # Il dominio dichiarato: ogni attività occupa **al più** una delle
        # proprie celle (`somma(celle) == piazzata`), quindi il massimo è la
        # somma dei peggiori casi individuali — un limite stretto, non
        # `len(termini)`.
        per_firma.append((
            sum(c * lit for celle in per_attivita.values()
                for c, lit in celle),
            sum(max(c for c, _ in celle)
                for celle in per_attivita.values())))
    return peggiore(model, "preferences", per_firma)


@register(QualityCriterion.Kind.FREE_HALF_DAYS)
def mezze_giornate_libere(ctx, model, chiavi):
    """`1/2 giornate libere` (`tcoDJLibres`). Massimizzare le mezze giornate
    libere è minimizzare quelle occupate, e il letterale esiste già.

    ⚠ Il criterio si calcola per **firma di settimana** e il livello è quello
    della peggiore (L7): vedi il blocco sulle firme in testa a `quality.py`.

    ⚠ **Non** è la quantità di `FreeGuaranteedChecker`, e la divergenza è
    deliberata: quel checker conta le mezze libere **solo sui giorni che
    lavorano**, perché il vincolo garantisce tempo libero *dentro* la settimana
    lavorativa. Il criterio invece ordina orari fra loro, e una giornata intera
    libera è il caso migliore — non un caso da non contare."""
    v, per_firma = ctx.vocab, []
    for rep in firme(ctx, chiavi):
        termini = [v.half_active(key, day, half, signature=rep)
                   for key in chiavi
                   for day in range(ctx.grid.days_per_cycle)
                   for half, span in enumerate(v.halves()) if len(span)]
        per_firma.append((sum(termini), len(termini)))
    return peggiore(model, "free_half_days", per_firma)


@register(QualityCriterion.Kind.ISOLATED)
def attivita_isolate(ctx, model, chiavi):
    """`Attività isolate` (`tcoIsoles`). Definizione letterale del prodotto:
    *«attività isolata in una mezza giornata **e** di durata inferiore a due
    fasce orarie»*.

    🔑 Le due condizioni collassano in una sola: **la mezza giornata ha
    esattamente una fascia occupata**. Sola e lunga due fasce dà conteggio 2;
    due attività da una fascia danno conteggio 2 e nessuna delle due è isolata;
    una mezza vuota dà 0. Non serve guardare né la durata né l'identità
    dell'attività, e non c'è nessun caso in cui le due formulazioni divergano.

    ⚠ La reificazione è a **due sensi**. Con il solo ramo «se isolata allora la
    somma è 1» il solver terrebbe `isolata` a zero sempre, e il livello
    misurerebbe la costante zero — un obiettivo che non fallisce mai è la forma
    più silenziosa di vincolo vacuo."""
    v, per_firma = ctx.vocab, []
    for rep in firme(ctx, chiavi):
        termini = []
        for key in chiavi:
            for day in range(ctx.grid.days_per_cycle):
                for half, span in enumerate(v.halves()):
                    if not len(span):
                        continue
                    occupate = sum(v.occupied(key, day, s, signature=rep)
                                   for s in span)
                    isolata = model.NewBoolVar(
                        f"isolata_{key}_{rep}_{day}_{half}")
                    model.Add(occupate == 1).OnlyEnforceIf(isolata)
                    model.Add(occupate != 1).OnlyEnforceIf(isolata.Not())
                    termini.append(isolata)
        per_firma.append((sum(termini), len(termini)))
    return peggiore(model, "isolated", per_firma)


@register(QualityCriterion.Kind.GAPS)
def buchi(ctx, model, chiavi):
    """`Durata totale dei buchi` (`tcoTrous`) — il criterio che in EDT
    presidia la testa della classifica: i buchi occupano **quattro** degli
    undici criteri di piazzamento, e le posizioni 1, 2, 5 e 6.

    La definizione si legge da `MaxGapChecker.violations`, dove la stessa
    quantità serve a essere confrontata con il D.T.B.: per ogni perimetro,
    `ultima − prima + 1 − conteggio`, in minuti. Qui è la stessa quantità senza
    il tetto.

    🔑 La forma `ultima − prima` chiederebbe due `IntVar` per mezza giornata.
    Si evita con l'equivalenza puntuale: una fascia è **di buco** quando è
    libera e ha almeno un'occupazione prima e almeno una dopo, **dentro lo
    stesso perimetro**. Le fasce fra la prima e l'ultima occupata sono
    `ultima − prima + 1`, di cui `conteggio` occupate: le restanti sono
    esattamente quelle che soddisfano la congiunzione.

    🔑 **Il perimetro è un parametro** (`vocab.gap_spans`), non la mezza
    giornata per sempre: è la casella di EDT `Non conteggiare come buchi le ore
    libere prima o dopo la linea di fine mattinata`, separata per classi e per
    docenti. Il criterio e il D.T.B. **devono** leggerla insieme — sono la
    stessa quantità, uno col tetto e uno senza — e un test lo tiene fermo.

    ⚠ Una fascia **indisponibile** in mezzo a due lezioni conta come buco, ed è
    voluto: conta così anche nel checker, che legge i piazzamenti e non sa
    nulla delle indisponibilità. Un docente fermo un'ora in istituto ha perso
    quell'ora comunque sia stata resa libera.

    🔑 **Ed è il criterio su cui L7 si misura** (2026-08-31). Sull'unione delle
    settimane il 5B con un'ora quindicinale non ha buchi — laboratorio alla 2
    nelle pari, teoria alla 3 nelle dispari, e insieme fanno 0-1-2-3 pieno —
    mentre ogni singola settimana ne ha uno. Ora il conto è per firma e il
    livello è quello della settimana **peggiore**, che è di nuovo il numero
    che `check_schedule` vede."""
    v, sm = ctx.vocab, ctx.grid.slot_minutes
    per_firma = []
    for rep in firme(ctx, chiavi):
        termini = []
        for key in chiavi:
            for day in range(ctx.grid.days_per_cycle):
                for perimetro, span in enumerate(v.gap_spans(key)):
                    fasce = list(span)
                    if len(fasce) < 3:
                        continue   # sotto le tre nessuna può stare in mezzo
                    occ = {s: v.occupied(key, day, s, signature=rep)
                           for s in fasce}
                    for i, s in enumerate(fasce[1:-1], start=1):
                        tag = f"{key}_{rep}_{day}_{perimetro}_{s}"
                        prima = model.NewBoolVar(f"gap_prima_{tag}")
                        model.AddMaxEquality(prima, [occ[t] for t in fasce[:i]])
                        dopo = model.NewBoolVar(f"gap_dopo_{tag}")
                        model.AddMaxEquality(dopo,
                                             [occ[t] for t in fasce[i + 1:]])
                        buco = model.NewBoolVar(f"gap_{tag}")
                        model.AddBoolAnd(
                            [prima, dopo, occ[s].Not()]).OnlyEnforceIf(buco)
                        model.AddBoolOr(
                            [prima.Not(), dopo.Not(),
                             occ[s]]).OnlyEnforceIf(buco.Not())
                        termini.append(buco)
        per_firma.append((sm * sum(termini), sm * len(termini)))
    return peggiore(model, "gaps", per_firma)


def _secchi(ctx, model, chiavi, rep, nome, secchio, minimo=1):
    """I **secchi distinti** che ogni coppia (unità, materia) occupa.

    🔑 **Tre criteri, una funzione.** `regularity` (l'`Equilibrio didattico`
    dell'ottimizzazione) e i due arrivati con O5 — il 4° e l'8° dei criteri di
    piazzamento — contano tutti quanti *secchi distinti* usa la stessa materia
    per la stessa unità. Cambiano solo il **secchio** e il **segno**:

    | Criterio | Secchio | Vuole |
    |---|---|---|
    | `regularity` | la fascia | **pochi** — la materia sempre alla stessa ora |
    | `slot_spread` | la fascia | **molti** — la materia mai alla stessa ora |
    | `weekly_spread` | il giorno | **molti** — la materia sparsa nella settimana |

    Che il 4 e l'8 di EDT si riducano a `regularity` con un parametro e un
    segno non era ovvio prima di scriverli, ed è il motivo per cui `_secchi`
    esiste invece di tre corpi quasi uguali: una divergenza di uno fra due di
    loro sarebbe un difetto invisibile.

    Restituisce, per coppia, `(usati, piazzate, quante)`: i booleani di secchio
    occupato, i letterali di cella (la cui somma è il numero di occorrenze
    **piazzate**) e il numero di attività della coppia, che serve a dichiarare
    l'estremo superiore.

    ⚠ `minimo` scarta le coppie con meno di così tante attività, e per
    `_sparpaglia` vale **2**: una coppia con un'occorrenza sola sta per forza
    in un secchio solo, quindi contribuisce zero e i suoi booleani sono peso
    morto. Non è un'approssimazione — è la stessa quantità senza i termini
    identicamente nulli — e sul banco toglie **700** variabili sulle 5108 che i
    due criteri costavano (13,7 %). ⚠ `regularity` **non** può usarla: là
    una coppia sola contribuisce 1, non 0, e toglierla cambierebbe il numero.

    ⚠ `usati` è un `AddMaxEquality`, cioè un'**uguaglianza**: vale in entrambi
    i versi, quindi la stessa costruzione serve chi vuole pochi secchi e chi ne
    vuole molti. Con una sola implicazione uno dei due verrebbe misurato su una
    costante."""
    ammesse = set(chiavi)
    stato = ctx.states[rep]
    per_coppia = defaultdict(lambda: defaultdict(list))
    quante = defaultdict(set)
    for aid in sorted(ctx.activities):
        if aid not in stato.activities:
            continue
        materia = ctx.activities[aid].subject_id
        for key in ctx.tokens[aid]:
            if key not in ammesse:
                continue
            quante[(str(key), materia)].add(aid)
            for (day, slot) in ctx.cells[aid]:
                per_coppia[(str(key), materia)][secchio(day, slot)].append(
                    ctx.x[(aid, day, slot)])

    fuori = []
    for coppia, per_secchio in sorted(per_coppia.items()):
        if len(quante[coppia]) < minimo:
            continue
        key, materia = coppia
        usati = []
        for valore, lits in sorted(per_secchio.items()):
            usa = model.NewBoolVar(f"{nome}_{key}_{materia}_{rep}_{valore}")
            model.AddMaxEquality(usa, lits)
            usati.append(usa)
        piazzate = [lit for lits in per_secchio.values() for lit in lits]
        fuori.append((usati, piazzate, len(quante[coppia])))
    return fuori


def _sparpaglia(ctx, model, chiavi, nome, etichetta, secchio):
    """`occorrenze piazzate − secchi distinti`, sommato sulle coppie.

    La forma in cui si minimizza il *volere molti secchi*. Il minimo per coppia
    è **zero** — ogni occorrenza in un secchio suo — e il massimo è
    `occorrenze − 1`, tutte nello stesso. Fra i due c'è esattamente il numero
    di occorrenze **di troppo**, che è la quantità che EDT descrive a parole:
    *«non due ore di matematica lo stesso giorno»*.

    🔑 **Perché la differenza e non le coppie.** «Coppie di occorrenze nello
    stesso secchio» è la lettura letterale, ed è quadratica: chiederebbe una
    moltiplicazione fra variabili per ogni secchio. La differenza è lineare,
    ha lo stesso minimo e lo stesso ordine — tre ore in un giorno costano 2
    invece di 3, ma nessun orario le scambia di posto.

    ⚠ **Dipende dal numero di occorrenze piazzate, che uno scarto abbassa.**
    In linea di principio il criterio preferirebbe quindi scartare; in pratica
    non può, perché `minuti_scartati` e `attivita_scartate` sono i livelli 1 e
    2 della catena e vengono **fissati** prima che un criterio di qualità
    esista. La riga resta perché è la ragione per cui il termine è scritto come
    somma di letterali e non come costante."""
    per_firma = []
    for rep in firme(ctx, chiavi):
        espressione, massimo = 0, 0
        for usati, piazzate, quante in _secchi(ctx, model, chiavi, rep, nome,
                                               secchio, minimo=2):
            espressione += sum(piazzate) - sum(usati)
            massimo += max(0, quante - 1)
        per_firma.append((espressione, massimo))
    return peggiore(model, etichetta, per_firma)


@register(QualityCriterion.Kind.REGULARITY)
def regolarita(ctx, model, chiavi):
    """`Equilibrio didattico` (`tcoMemesHoraires`).

    ⚠ **La traduzione italiana è fuorviante**, e il documento lo dice già:
    l'enum si chiama *stessi orari* e il francese è `Régularité des cours`. Il
    senso è che **la stessa materia ricada sempre nella stessa fascia**, non
    l'equilibrio del carico. Tradurre l'etichetta italiana alla lettera avrebbe
    prodotto un criterio diverso da quello di EDT.

    La quantità è il numero di **fasce distinte** usate da una coppia (unità,
    materia): minimizzarla spinge le occorrenze sulla stessa ora del giorno. Il
    minimo per coppia è 1 — una materia sempre alla terza ora — quindi il
    livello non scende mai a zero, e il suo valore assoluto conta meno della
    sua differenza fra due orari.

    🔑 È l'unico criterio che in EDT vale per le **classi** e non per i
    docenti: nella base di esempio l'orario delle classi ha questo come primo e
    unico criterio, e quello dei docenti non lo ha affatto. L'asimmetria è
    voluta — gli studenti hanno bisogno di un ritmo prevedibile e restano a
    scuola comunque, i docenti vanno e vengono. E dal 2026-08-31 il verso
    opposto ha un nome: `SLOT_SPREAD`, che è questo criterio per i docenti."""
    per_firma = []
    for rep in firme(ctx, chiavi):
        termini = [usa for usati, _piazzate, _quante
                   in _secchi(ctx, model, chiavi, rep, "regolare",
                              lambda _day, slot: slot)
                   for usa in usati]
        per_firma.append((sum(termini), len(termini)))
    return peggiore(model, "regularity", per_firma)


@register(QualityCriterion.Kind.WEEKLY_SPREAD)
def distribuzione_settimanale(ctx, model, chiavi):
    """4. `Distribuisci nella settimana le attività della stessa materia`.

    Le tre ore di matematica su tre giorni diversi, non due il lunedì.

    🔑 **Questo lo sapevamo già dire, ma solo come divieto**, ed è la ragione
    per cui è il primo dei tre approvati da O5 (ADR-025): `MIN_DISTRIBUTION`,
    `SAME_DAY_INCOMPATIBLE` e `TWO_DAYS_INCOMPATIBLE` dicono la stessa cosa
    **impedendo**. Una scuola che preferisce la distribuzione senza pretenderla
    doveva scegliere fra dichiarare un divieto — e rendere l'istanza
    infattibile dove un criterio l'avrebbe solo peggiorata — o rinunciare.

    ⚠ Il divieto **resta**, e non è un doppione: un vincolo e un criterio sulla
    stessa quantità sono la coppia «obbligo» / «preferenza», che è esattamente
    la scelta che la scuola ora ha. Dichiarare entrambi non è un errore: il
    criterio ordina ciò che il divieto lascia passare."""
    return _sparpaglia(ctx, model, chiavi, "distribuito", "weekly_spread",
                       lambda day, _slot: day)


@register(QualityCriterion.Kind.SLOT_SPREAD)
def fasce_sparse(ctx, model, chiavi):
    """8. `Evita le attività della stessa materia nella stessa ora`.

    Non «giorni diversi» — è il 4 — ma **ore diverse**: la matematica non
    sempre alla prima ora.

    🔑 **È `regularity` col segno opposto, e non è una contraddizione di EDT.**
    Sono due meccanismi e due popolazioni. Il *piazzamento* evita la stessa ora
    per tutti; l'*ottimizzazione* la ripristina per le sole **classi** —
    `tcoMemesHoraires` è il primo e unico criterio dell'orario delle classi
    nella base di esempio, e non compare affatto in quello dei docenti. Per la
    classe la ripetizione è una routine, per il docente è una condanna.

    ⚠ **Dichiararlo insieme a `REGULARITY` sulla stessa popolazione lo rende
    inerte**, e non per un difetto: la catena è lessicografica, quindi il primo
    dei due fissa `secchi distinti` al proprio ottimo e il secondo, che è
    `occorrenze − secchi distinti` con le occorrenze già fissate, non ha più
    niente da scegliere. Non c'è un vincolo che lo vieti — è una proprietà
    misurabile, e un test la misura invece di dichiararla."""
    return _sparpaglia(ctx, model, chiavi, "sparso", "slot_spread",
                       lambda _day, slot: slot)
