"""Presenza e buchi: i vincoli che ragionano sulla **prima e sull'ultima**
fascia occupata, e non sul semplice conteggio. Entrambi passano da
`vocab.covered`, con `span` diverso — mezza giornata per il D.T.B., giornata
intera per MAX_PRESENCE.

MAX_GAP_HOURS — il D.T.B., «durata tollerata dei buchi».

⚠ È un **budget settimanale**, non una soglia per singolo buco: il checker
somma i minuti di buco su tutte le mezze giornate della settimana e confronta
il totale una volta sola. Qui la stessa cosa, in forma lineare e senza big-M:
per ogni mezza giornata, `covered[s] = before[s] AND after[s]` dice se la
fascia sta fra la prima e l'ultima occupata, e i minuti di buco sono
`slot_minutes * somma(covered[s] - occ[s])` — ogni termine non negativo perché
`occ[s]` implica `covered[s]`.

I buchi non si contano mai a cavallo del pranzo: le due mezze giornate sono
separate, come in `_halves` del checker.

⚠ Questo builder **distingue le firme di settimana**: posta un budget per
ogni `(rep, _)` di `ctx.signatures`, con i letterali `occ` filtrati alle sole
attività attive in quella firma. La semplificazione «tutte le attività
co-attive» — usata altrove nello spike (`subject_constraints.py`) — qui
**non è conservativa**, ed è il difetto trovato in review: il buco è
`ultima − prima + 1 − conteggio`. Un'occupazione che cade *dentro* il buco ma
viene da un'attività di un'**altra** firma di settimana alza il `conteggio`
senza toccare `prima` né `ultima` — quindi **riempie** il buco nel modello
unione, mentre nelle settimane reali quel buco resta scoperto. Trattare tutto
come co-attivo vincola quindi **di meno**, non di più: può accettare
piazzamenti che il checker, valutando ogni firma per conto proprio, rifiuta.
(Per `subject_constraints.py` la stessa semplificazione resta genuinamente
conservativa: più letterali significano una somma più vincolata, mai il
contrario — lì il caso pessimo è perdere qualche soluzione, mai accettarne di
illegali.)

Le firme diverse con lo stesso insieme di attività attive sulla risorsa
producono lo stesso vincolo: deduplicate con `posted`, come fa
`OccupationBuilder`. Il ciclo sulle firme e la deduplicazione sono ora nella
classe base `ResourceBuilder` (`domain/solver/builders/base.py`): qui resta
solo il corpo del vincolo, come `post`.

⚠ **ADR-018, esteso al D.T.B.** Il budget e' un aggregato non lineare (min/max
via `covered`), quindi il residuo non si separa in «costante + libere» come
sui tetti lineari (`residual_cap`): non si puo' sottrarre il contributo delle
congelate dalla somma. Qui il guardiano non e' un residuo sottratto dal
letterale, ma un **clamp sul tetto stesso**: si calcola il buco che le sole
attivita' congelate produrrebbero (`_frozen_gap_minutes`, a posizioni fisse e
note a build time), e il tetto effettivamente postato e'
`max(cap, _frozen_gap_minutes(...))` — mai sotto al debito gia' contratto dal
passato.

⚠ **Non saltare il vincolo quando le congelate sforano da sole** (era l'errore
della prima versione, corretto in review Task 6, Important 2): il vincolo
resta postato su **tutti** i giorni della firma, solo con un tetto piu' alto.
Il D.T.B. e' un budget settimanale che comprende giorni **mai toccati dalle
congelate**: se il vincolo sparisse del tutto, le attivita' libere potrebbero
aprire buchi illimitati anche li', e potrebbero perfino *richiudere* un buco
delle congelate — quindi il debito non e' irrecuperabile, ed «e' un fatto, non
una decisione» non vale. Il clamp concede esattamente il debito gia' contratto
e nulla di piu': mai infattibile per colpa del passato, ma vincolante ovunque
le libere abbiano ancora voce in capitolo — l'analogo esatto di
`max(0, cap - consumo)` in `residual_cap`, qui scritto come
`max(cap, consumo)` perche' il tetto e il consumo vivono sulla stessa scala
(entrambi minuti di buco), non sottratti l'uno dall'altro."""

from domain.models import RelaxationQuota, ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import register
from domain.solver.residual import frozen_occupies

T = ResourceTimeConstraint.Type


def _frozen_gap_minutes(ctx, key, rep):
    """Il buco settimanale (in minuti) indotto dalle sole attivita'
    **congelate** su `key`, per la firma `rep`. Le celle delle congelate sono
    fisse e note a build time (`ctx.cells[aid]`), quindi il calcolo e' lo
    stesso del checker (`MaxGapChecker`) ristretto alle sole congelate."""
    grid, active = ctx.grid, ctx.states[rep].activities
    total = 0
    for day in range(grid.days_per_cycle):
        for half in ctx.vocab.halves():
            if not len(half):
                continue
            occupate = sorted({
                s for s in half
                for aid, _ in ctx.by_cell.get((key, day, s), ())
                if aid not in ctx.free and aid in active
            })
            if len(occupate) >= 2:
                total += (occupate[-1] - occupate[0] + 1
                          - len(occupate)) * grid.slot_minutes
    return total


@register(T.MAX_GAP_HOURS)
class MaxGapBuilder(ResourceBuilder):
    TYPE = T.MAX_GAP_HOURS

    def post(self, ctx, model, row, rep):
        grid, v = ctx.grid, ctx.vocab
        key = row.resource_id
        # ADR-018: il tetto effettivo non scende mai sotto il debito gia'
        # contratto dalle sole congelate — clamp, non spegnimento del
        # vincolo (review Task 6, Important 2).
        cap = max(row.params["max_gap_minutes"], _frozen_gap_minutes(ctx, key, rep))
        terms = []
        for day in range(grid.days_per_cycle):
            for half in v.halves():
                if not len(half):
                    continue
                cov = v.covered(key, day, half, signature=rep)
                for s in half:
                    terms.append(cov[s] - v.occupied(key, day, s, signature=rep))
        if terms:
            model.Add(grid.slot_minutes * sum(terms) <= cap)


def _frozen_presence_minutes(ctx, key, day, rep):
    """La presenza (in minuti) indotta dalle sole attivita' **congelate** su
    `key`, nel giorno `day`, per la firma `rep`. Stesso schema di
    `_frozen_gap_minutes` (celle fisse, note a build time), ma sulla
    **giornata intera** — non per mezza giornata — perche' e' cosi' che
    MaxPresenceChecker misura la presenza (`_presence_minutes`, che non passa
    mai da `_halves`)."""
    grid, active = ctx.grid, ctx.states[rep].activities
    occupate = sorted({
        s for s in range(grid.slots_per_day)
        for aid, _ in ctx.by_cell.get((key, day, s), ())
        if aid not in ctx.free and aid in active
    })
    if not occupate:
        return 0
    return (occupate[-1] - occupate[0] + 1) * grid.slot_minutes


@register(T.MAX_PRESENCE)
class MaxPresenceBuilder(ResourceBuilder):
    """Presenza != lavoro: la presenza include i buchi, e si misura
    `ultima - prima + 1` **sulla giornata intera**.

    ⚠ Lo `span` e' la giornata, non la mezza giornata. MaxPresenceChecker usa
    `_presence_minutes`, che non passa da `_halves` — a differenza del D.T.B.,
    che i buchi non li conta mai a cavallo del pranzo. Sono due vincoli che si
    somigliano e non sono la stessa cosa: usare la mezza giornata qui
    produrrebbe un vincolo piu' largo del checker (due presenze corte a
    cavallo del pranzo passerebbero, mentre il checker le fonde in una sola).

    ⚠ **ADR-018, correzione al piano (Ruling 23): clampa, non saltare.** Il
    piano originale faceva `continue` sul giorno in cui le sole congelate
    avevano gia' sforato il tetto, con l'argomento che «le libere non possono
    ridurre una presenza, quindi il vincolo e' perso comunque». La premessa e'
    vera — la presenza e' monotona non decrescente — ma la conclusione e'
    sbagliata: saltare il vincolo lascia le libere **allargare** la presenza
    di quel giorno oltre il debito gia' contratto, e il finding porta
    `minutes=presence` fra le sue `quantities` (`Finding.key`,
    domain/analysis/findings.py) — una presenza peggiorata e' una violazione
    **nuova** per l'oracolo differenziale, non la stessa di prima. La forma
    corretta e' il clamp gia' usato da `MaxGapBuilder` sopra: il tetto
    effettivo e' `max(cap, presenza_indotta_dalle_sole_congelate)`
    (`_frozen_presence_minutes`), mai sotto al debito gia' contratto dal
    passato. Nel caso pulito coincide col tetto dichiarato; nel caso sporco
    il modello non e' mai infattibile per colpa del passato, ma le libere
    restano vincolate a non peggiorare ulteriormente la giornata.

    Il ramo `days` non passa da `residual_cap`: i termini sono variabili
    derivate (`day_active`), non `(peso, id_attivita', letterale)` per
    attivita' — il caso esplicitamente previsto da `frozen_occupies`
    (Ruling 25). Il consumo delle congelate si sottrae a mano dal tetto,
    come gia' fanno i Task 6 e 7."""
    TYPE = T.MAX_PRESENCE

    def post(self, ctx, model, row, rep):
        grid, v = ctx.grid, ctx.vocab
        key = row.resource_id
        giornata = range(grid.slots_per_day)
        # «Presenza massima dei docenti: autorizza un supplemento di … una
        # volta per settimana e per docente». Un solo letterale per riga: i due
        # parametri (minuti e giorni) sono due metà dello stesso
        # alleggerimento, e devono consumare una quota sola.
        margine = ctx.relax.margine(
            model, RelaxationQuota.Family.MAX_PRESENCE, key, f"{rep}")
        cap = row.params.get("max_minutes")
        if cap is not None:
            for day in range(grid.days_per_cycle):
                # ADR-018 (Ruling 23): clamp, non salto — vedi il docstring
                # di classe per l'argomento sulle quantities.
                cap_effettivo = max(cap, _frozen_presence_minutes(ctx, key, day, rep))
                cov = v.covered(key, day, giornata, signature=rep)
                model.Add(grid.slot_minutes * sum(cov[s] for s in giornata)
                          <= cap_effettivo + margine)
        max_days = row.params.get("days")
        if max_days is not None:
            terms, consumo = [], 0
            for day in range(grid.days_per_cycle):
                if frozen_occupies(ctx, key, day, giornata, rep):
                    consumo += 1
                else:
                    terms.append(v.day_active(key, day, signature=rep))
            if terms:
                model.Add(sum(terms) <= max(0, max_days - consumo) + margine)
