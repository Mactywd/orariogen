"""Le traduzioni dei criteri di qualità, una per `QualityCriterion.Kind`.

Ogni criterio è una funzione `(ctx, model, chiavi) -> (espressione, massimo)`:
l'espressione da minimizzare e il suo estremo superiore, che dichiara il
dominio dell'`IntVar` del livello. Nessuna posta vincoli di ammissibilità —
vedi il docstring di `quality.py`."""


from collections import defaultdict

from domain.models import QualityCriterion, ResourceUnavailability
from domain.solver.quality import register


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
    un criterio di qualità."""
    verdi = {
        (key, day, slot)
        for rep, _ in ctx.signatures
        for (key, day, slot), livello in ctx.states[rep].unavailability.items()
        if livello == ResourceUnavailability.Level.PREFERENCE
    }
    if not verdi:
        return 0, 0
    ammesse = set(chiavi)
    per_attivita = defaultdict(list)
    for aid in sorted(ctx.activities):
        durata = ctx.activities[aid].duration_slots
        toccate = [k for k in ctx.tokens[aid] if k in ammesse]
        for (day, slot) in sorted(ctx.cells[aid]):
            colpi = sum(1 for key in toccate
                        for s in range(slot, slot + durata)
                        if (key, day, s) in verdi)
            if colpi:
                per_attivita[aid].append((colpi, ctx.x[(aid, day, slot)]))
    if not per_attivita:
        return 0, 0
    # Il dominio dichiarato: ogni attività occupa **al più** una delle proprie
    # celle (`somma(celle) == piazzata`), quindi il massimo è la somma dei
    # peggiori casi individuali — un limite stretto, non `len(termini)`.
    massimo = sum(max(c for c, _ in celle) for celle in per_attivita.values())
    espressione = sum(c * lit for celle in per_attivita.values()
                      for c, lit in celle)
    return espressione, massimo


@register(QualityCriterion.Kind.FREE_HALF_DAYS)
def mezze_giornate_libere(ctx, model, chiavi):
    """`1/2 giornate libere` (`tcoDJLibres`). Massimizzare le mezze giornate
    libere è minimizzare quelle occupate, e il letterale esiste già.

    ⚠ **Non** è la quantità di `FreeGuaranteedChecker`, e la divergenza è
    deliberata: quel checker conta le mezze libere **solo sui giorni che
    lavorano**, perché il vincolo garantisce tempo libero *dentro* la settimana
    lavorativa. Il criterio invece ordina orari fra loro, e una giornata intera
    libera è il caso migliore — non un caso da non contare."""
    v = ctx.vocab
    termini = [v.half_active(key, day, half)
               for key in chiavi
               for day in range(ctx.grid.days_per_cycle)
               for half, span in enumerate(v.halves()) if len(span)]
    return sum(termini), len(termini)


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
    v, termini = ctx.vocab, []
    for key in chiavi:
        for day in range(ctx.grid.days_per_cycle):
            for half, span in enumerate(v.halves()):
                if not len(span):
                    continue
                occupate = sum(v.occupied(key, day, s) for s in span)
                isolata = model.NewBoolVar(f"isolata_{key}_{day}_{half}")
                model.Add(occupate == 1).OnlyEnforceIf(isolata)
                model.Add(occupate != 1).OnlyEnforceIf(isolata.Not())
                termini.append(isolata)
    return sum(termini), len(termini)


@register(QualityCriterion.Kind.GAPS)
def buchi(ctx, model, chiavi):
    """`Durata totale dei buchi` (`tcoTrous`) — il criterio che in EDT
    presidia la testa della classifica: i buchi occupano **quattro** degli
    undici criteri di piazzamento, e le posizioni 1, 2, 5 e 6.

    La definizione si legge da `MaxGapChecker.violations`, dove la stessa
    quantità serve a essere confrontata con il D.T.B.: per ogni mezza giornata,
    `ultima − prima + 1 − conteggio`, in minuti. Qui è la stessa quantità senza
    il tetto.

    🔑 La forma `ultima − prima` chiederebbe due `IntVar` per mezza giornata.
    Si evita con l'equivalenza puntuale: una fascia è **di buco** quando è
    libera e ha almeno un'occupazione prima e almeno una dopo, **dentro la
    stessa mezza giornata**. Le fasce fra la prima e l'ultima occupata sono
    `ultima − prima + 1`, di cui `conteggio` occupate: le restanti sono
    esattamente quelle che soddisfano la congiunzione.

    ⚠ **La mezza giornata come perimetro è una scelta, e in EDT è un
    parametro.** Là il buco si misura sulla *giornata*, e una casella
    `Non conteggiare come buchi le ore libere prima o dopo la linea di fine
    mattinata` — **separata per classi e per docenti** — ne toglie la pausa.
    Noi ci comportiamo come se fosse spuntata per entrambe le popolazioni.
    Debito dichiarato in `docs/todo.md`; toccarlo cambia anche il D.T.B., che
    è hard.

    ⚠ Una fascia **indisponibile** in mezzo a due lezioni conta come buco, ed è
    voluto: conta così anche nel checker, che legge i piazzamenti e non sa
    nulla delle indisponibilità. Un docente fermo un'ora in istituto ha perso
    quell'ora comunque sia stata resa libera."""
    v, sm = ctx.vocab, ctx.grid.slot_minutes
    termini = []
    for key in chiavi:
        for day in range(ctx.grid.days_per_cycle):
            for half, span in enumerate(v.halves()):
                fasce = list(span)
                if len(fasce) < 3:
                    continue   # sotto le tre fasce nessuna può stare in mezzo
                occ = {s: v.occupied(key, day, s) for s in fasce}
                for i, s in enumerate(fasce[1:-1], start=1):
                    tag = f"{key}_{day}_{half}_{s}"
                    prima = model.NewBoolVar(f"gap_prima_{tag}")
                    model.AddMaxEquality(prima, [occ[t] for t in fasce[:i]])
                    dopo = model.NewBoolVar(f"gap_dopo_{tag}")
                    model.AddMaxEquality(dopo, [occ[t] for t in fasce[i + 1:]])
                    buco = model.NewBoolVar(f"gap_{tag}")
                    model.AddBoolAnd([prima, dopo, occ[s].Not()]).OnlyEnforceIf(buco)
                    model.AddBoolOr([prima.Not(), dopo.Not(), occ[s]]).OnlyEnforceIf(buco.Not())
                    termini.append(buco)
    return sm * sum(termini), sm * len(termini)


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
    scuola comunque, i docenti vanno e vengono."""
    ammesse = set(chiavi)
    per_coppia = defaultdict(lambda: defaultdict(list))
    for aid in sorted(ctx.activities):
        materia = ctx.activities[aid].subject_id
        for key in ctx.tokens[aid]:
            if key not in ammesse:
                continue
            for (day, slot) in ctx.cells[aid]:
                per_coppia[(str(key), materia)][slot].append(ctx.x[(aid, day, slot)])
    termini = []
    for (key, materia), per_fascia in sorted(per_coppia.items()):
        for slot, lits in sorted(per_fascia.items()):
            usa = model.NewBoolVar(f"regolare_{key}_{materia}_{slot}")
            model.AddMaxEquality(usa, lits)
            termini.append(usa)
    return sum(termini), len(termini)
