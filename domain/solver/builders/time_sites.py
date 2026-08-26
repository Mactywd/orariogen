"""Le sedi. Due vincoli che condividono la stessa costruzione: una coppia di
fasce della stessa giornata, occupate da attivita' di **sedi diverse**, con
solo occupazioni **senza sede nota** in mezzo.

⚠ Entrambi i checker ragionano su coppie **consecutive nella sottosequenza
delle occupazioni con sede nota** (`_site_sequence` in
`domain/analysis/checkers/time_constraints.py`, e la stessa idea in
`domain/analysis/checkers/sites.py`): un'attivita' **senza sede** interposta
non spezza l'adiacenza, perche' non entra nemmeno nella sequenza.

⚠ **Correzione al piano (Ruling 27).** La prima stesura di questo file
chiedeva, per la coppia `(s, t)`, che **tutte** le fasce intermedie fossero
libere (`occupied(m).Not()`): "tutto vuoto in mezzo". E' la condizione
sbagliata. Con un'attivita' senza sede alla fascia intermedia, quella fascia
e' **occupata** ma non ha sede — il checker la salta e vede comunque
`s` e `t` come adiacenti nella sua sottosequenza, mentre la vecchia
condizione del builder non trovava mai la coppia (perche' la fascia di mezzo
non era libera) e quindi **non contava nulla**. E' un *under-count*: il
solver accettava un orario che il checker boccia — il criterio di riuscita
(oracolo differenziale) rotto. Riprodotto con un'istanza a tre fasce (sede A
/ senza sede / sede B, `per_day=0`): il vecchio builder trovava `OPTIMAL`
piazzando esattamente quell'arrangiamento, e `check_schedule` sulla soluzione
riportava un `max_site_changes` `HARD` che il solver non aveva visto (vedi il
report del Task 9 per l'output verbatim). La condizione corretta e' «nessuna
occupazione **con sede nota** in mezzo»: per ogni fascia `m` fra `s` e `t`,
nessuna sede la occupa (`site_occupied(..., site).Not()` per ogni sede). Con
questa condizione la coppia `(s, t)` con `sa != sb` diventa *esattamente*
l'adiacenza nella sottosequenza del checker, e la costruzione torna a essere
piu' stretta, mai piu' larga (spec §4.3): per le coppie lontane il vincolo e'
comunque vacuo (la coppia non forza nulla se in mezzo c'e' un'altra sede
nota, che a sua volta partecipa alle proprie coppie adiacenti), e le coppie
vicine includono tutte le consecutive.

⚠ **Due attivita' di sede diversa sulla STESSA fascia della stessa chiave —
riparato solo in `SiteTransitionBuilder` (Important 1 + Ruling 33, giro di
correzione 1).** Il checker le conta entrambe (appende una voce per **ogni**
attivita' che occupa la fascia, `state.occupancy[(key, day, s)]`), quindi due
attivita' di sede diversa simultanee sulla stessa fascia sono **sempre** un
cambio per `SiteTransitionChecker`: con `s1 == s2`, `gap_slots = s2-s1-1 =
-1`, che e' `< needed` per **qualunque** `needed >= 0` — anche `needed = 0`.
La violazione non dipende dalla soglia. La costruzione a coppie `s < t` (qui
sotto) non puo' esprimerla: non esiste una coppia con `s == t`. Di norma e'
irraggiungibile perche' la stessa fascia della stessa chiave e' gia' vietata
da `structural:occupation` (capienza 1) — ma **raggiungibile** quando la
chiave ha capienza cumulativa `simultaneous_capacity > 1` (il campo esiste
sulla `Resource` base, quindi anche su classi/docenti, ma il caso reale e'
l'aula col `Numero di aule`/`Qta'` di EDT, documentato in `docs/edt/aule.md`
— non un caso di laboratorio): un'aula a capienza 2 con due attivita' di
classi diverse, sedi diverse, piazzate sulla stessa fascia produce zero
finding di occupazione ma un `site_transition` `HARD` dal checker — l'oracolo
differenziale rotto (solver `OPTIMAL`, checker boccia con un finding nuovo).

**Riparato**: `SiteTransitionBuilder.build` posta ora, per ogni `(chiave,
giorno, fascia)` e ogni coppia di sedi distinte che tocca davvero quella
cella, la clausola `s == t` (`site_occupied(key, day, s, sa).Not() OR
site_occupied(key, day, s, sb).Not()`) — **indipendente da `needed`**, perche'
il checker non la esenta mai, nemmeno a `needed = 0`. Esatto, non
conservativo; costo trascurabile (una clausola per chiave × giorno × fascia ×
coppia di sedi effettivamente compresenti in quella cella, filtrate da
`_sedi_raggiungibili` — Minor 2 sotto). Test:
`test_site_transition_due_sedi_sulla_stessa_fascia_a_capienza_cumulativa` in
`tests/test_solver_sites.py`.

⚠ **`MaxSiteChangesBuilder` — NON riparato, deliberatamente (Ruling 33).** Lo
stesso buco esiste anche qui (due sedi diverse sulla stessa fascia sono un
cambio per il checker), ma qui la riparazione non e' univoca, perche' la
semantica del checker stesso non lo e'. `ScheduleState.occupancy`
(`domain/analysis/state.py`) e' un `defaultdict(list)`, e `_site_sequence` la
scorre **in ordine di lista** — l'ordine in cui `ScheduleState.build` ha
inserito le occupazioni. Sotto capienza cumulativa il **conteggio** dei
cambi dipende quindi dall'**ordine di inserimento**: la stessa coppia di
attivita' simultanee da' un conteggio diverso a seconda che la sequenza
letta sia `[A, B]` o `[B, A]` seguita da una terza occupazione. Non e' una
proprieta' del piazzamento, e' un artefatto di implementazione del checker —
e il checker e' **l'autorita'** su cosa significhi il vincolo. Tradurre
l'artefatto nel builder (per esempio imponendo un ordine arbitrario fra le
due sedi simultanee) significherebbe replicare un comportamento che nessuno
ha deciso essere corretto, non tradurre una semantica. **Va prima deciso in
`domain/analysis` cosa significhi «cambio di sede» quando due sedi
coesistono nella stessa fascia** (per esempio: ordinare la sequenza
intra-fascia in modo deterministico, o dichiarare che sedi diverse
simultanee valgono un cambio e basta indipendentemente da quante sono e in
che ordine) — solo allora questo builder ha una semantica bersaglio univoca
da tradurre. Fino a quella decisione resta **esatto solo per chiavi a
capienza 1** (confronto esaustivo nel report del Task 9, giro di correzione
1 e nella review). Voce gia' in CLAUDE.md, elenco «Ancora aperto».

⚠ **ADR-018.** `MaxSiteChangesBuilder` posta somme su variabili derivate
(i letterali di cambio `c`), non su termini `(peso, id, letterale)`
separabili: stesso schema di `MaxGapBuilder`/`MaxPresenceBuilder`
(`time_presence.py`) — un tetto **clampato**, mai un salto del vincolo (il
`continue` e' stato sbagliato due volte su questo piano: review Task 6
Important 2, e Ruling 23 sul Task 8).

⚠ **`SiteTransitionBuilder` invece non aveva ADR-018 affatto**, e fino al
2026-08-26 il commento qui ha dichiarato il contrario («ha gia' ADR-018 nella
forma della regola dell'implicazione (`any_free`): non toccato»). `any_free` guarda
chi **tocca** le due fasce, non chi **realizza** la coppia di sedi vietata:
con due congelate di sede diversa a distanza insufficiente — gia' una
violazione per il checker — basta una libera qualunque che tocchi una delle
due fasce perche' la clausola venga postata, e quella clausola ha **entrambi**
i letterali forzati a 1 dalle congelate. `INFEASIBLE` per colpa del solo
passato, cioe' la meta' vietata del criterio di ADR-018. Trovato dal banco che
congela (`tests/test_solver_frozen.py`, seme 38) il 2026-08-26; il guardiano
vero e' `_sede_congelata` qui sotto.

⚠ **Minor 2 (review Task 9): filtro a costo zero sul numero di clausole —
applicato, ma misurato a effetto nullo sul Fermi.** Entrambi i builder
ciclavano su **tutte** le sedi conosciute nell'istituto per ogni `sa`/`sb`,
anche quando nessuna attivita' di quella sede tocca davvero la cella in
questione — in quel caso `site_occupied(...)` e' costante a zero per
costruzione (nessun letterale in `ctx.by_cell`) e la clausola che lo
coinvolge e' vera per costruzione, quindi inutile da postare.
`_sedi_raggiungibili` restituisce, per una cella, solo le sedi di cui esiste
**davvero** un'attivita' il cui dominio tocca quella cella (lettura diretta
di `ctx.by_cell`, senza filtrare per firma di settimana — filtro grosso ma a
costo zero in complessita' del codice): e' logicamente corretto e non
costa nulla in leggibilita', quindi resta. **Ma misurato sul Fermi (giro di
correzione 1) non taglia nulla**: a 2 sedi il conteggio dei constraint di
`SiteTransitionBuilder` e' identico con e senza il filtro (5604, sia al 50%
sia al 100% di attivita' con sede), e lo stesso a 4 sedi (21830 con e senza).
La ragione e' strutturale, non un errore del filtro: sul Fermi le attivita'
di ogni chiave (classe o docente) non hanno restrizioni di dominio ulteriori
(nessuna indisponibilita', nessun vincolo di griglia in questi scenari di
misura), quindi `ctx.by_cell` per quella chiave contiene gia' rappresentanti
di (quasi) tutte le sedi in (quasi) ogni cella — non c'e' nulla da filtrare.
Il filtro tornerebbe utile su dati con domini davvero ristretti per sede
(indisponibilita', griglia, congelate), che il Fermi con le sedi aggiunte
sinteticamente per la misura non esercita. La crescita superlineare col
numero di sedi resta comunque reale e superiore a quella del piano originale
(la clausola `s == t` aggiunge una famiglia intera di vincoli): misurato qui,
`SiteTransitionBuilder` da solo (senza righe MAX_SITE_CHANGES) passa da 5604
constraint a 2 sedi a 21830 a 4 sedi sul Fermi — piu' del baseline
pre-riparazione (4008 → 12254) perche' la riparazione dell'Important 1 e'
un'intera famiglia di vincoli in piu', non un'ottimizzazione."""

from domain.models import ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import Builder, register
from domain.solver.residual import any_free

T = ResourceTimeConstraint.Type


def _sedi(ctx):
    return sorted({a.site_id for a in ctx.activities.values()
                   if a.site_id is not None})


def _sedi_raggiungibili(ctx, key, day, slot):
    """Le sedi di cui esiste **davvero** un'attivita' il cui dominio tocca
    questa cella (Minor 2, review Task 9): fuori da questo insieme,
    `site_occupied(key, day, slot, sito)` e' costante a zero per
    costruzione (nessun letterale in `ctx.by_cell`), quindi ogni clausola
    che lo coinvolge sarebbe vera per costruzione — inutile da postare.
    Non filtra per firma di settimana (sarebbe piu' preciso ma complica il
    chiamante): un falso positivo qui costa al piu' una clausola vera per
    costruzione, mai una sbagliata."""
    return {ctx.activities[aid].site_id
            for aid, _ in ctx.by_cell.get((key, day, slot), ())
            if ctx.activities[aid].site_id is not None}


def _coppie_di_sede(ctx, key, day, s, t, sa, sb, rep, sedi):
    """I letterali di «fascia s sulla sede sa, fascia t sulla sede sb, e
    nessuna sede nota in mezzo» — l'adiacenza nella sottosequenza dei
    checker. Vedi la correzione in testa al modulo: non e' «tutto vuoto in
    mezzo», e' «nessuna sede nota in mezzo»."""
    v = ctx.vocab
    lits = [v.site_occupied(key, day, s, sa, signature=rep),
            v.site_occupied(key, day, t, sb, signature=rep)]
    for m in range(s + 1, t):
        for sito in sedi:
            lits.append(v.site_occupied(key, day, m, sito, signature=rep).Not())
    return lits


def _frozen_site_changes(ctx, key, day, rep, sedi):
    """I cambi di sede (per giornata) indotti dalle **sole** attivita'
    congelate su `key`, per la firma `rep`. Le celle delle congelate sono
    fisse e note a build time (`ctx.by_cell`, filtrato su `aid not in
    ctx.free` e, se attivo, `aid in ctx.states[rep].activities`): stesso
    schema di `_frozen_gap_minutes`/`_frozen_presence_minutes` in
    `time_presence.py`, qui sulla sequenza di sede invece che sui minuti di
    buco/presenza."""
    active = ctx.states[rep].activities
    sequenza = []
    for slot in range(ctx.grid.slots_per_day):
        for aid, _lit in ctx.by_cell.get((key, day, slot), ()):
            if aid in ctx.free or aid not in active:
                continue
            sito = ctx.activities[aid].site_id
            if sito is not None:
                sequenza.append(sito)
    return sum(a != b for a, b in zip(sequenza, sequenza[1:]))


@register(T.MAX_SITE_CHANGES)
class MaxSiteChangesBuilder(ResourceBuilder):
    TYPE = T.MAX_SITE_CHANGES

    def post(self, ctx, model, row, rep):
        key, sedi = row.resource_id, _sedi(ctx)
        if len(sedi) < 2:
            return
        per_giorno = row.params.get("per_day")
        per_settimana = row.params.get("per_week")
        tutti = []
        consumo_settimana = 0
        for day in range(ctx.grid.days_per_cycle):
            cambi = []
            # Minor 2: le sedi davvero raggiungibili in ogni fascia,
            # calcolate una volta per giornata invece che ad ogni coppia
            # (s, t) — stesso filtro, meno lavoro ripetuto.
            per_fascia = [_sedi_raggiungibili(ctx, key, day, s)
                          for s in range(ctx.grid.slots_per_day)]
            for s in range(ctx.grid.slots_per_day):
                for t in range(s + 1, ctx.grid.slots_per_day):
                    for sa in per_fascia[s]:
                        for sb in per_fascia[t]:
                            if sa == sb:
                                continue
                            lits = _coppie_di_sede(ctx, key, day, s, t,
                                                   sa, sb, rep, sedi)
                            c = model.NewBoolVar(
                                f"chg_{key}_{rep}_{day}_{s}_{t}_{sa}_{sb}")
                            # la congiunzione implica il cambio; c puo'
                            # essere 1 in piu' solo a danno del solver (mai a
                            # suo vantaggio), e i vincoli sotto sono tutti
                            # «<=»: sovra-contare non introduce mai un
                            # falso negativo.
                            model.AddBoolOr([c] + [l.Not() for l in lits])
                            cambi.append(c)
            # ADR-018: il tetto giornaliero non scende mai sotto il debito
            # gia' contratto dalle sole congelate — clamp, non salto (il
            # `continue` e' stato sbagliato due volte su questo piano).
            consumo_giorno = _frozen_site_changes(ctx, key, day, rep, sedi)
            consumo_settimana += consumo_giorno
            if per_giorno is not None and cambi:
                model.Add(sum(cambi) <= max(per_giorno, consumo_giorno))
            tutti += cambi
        if per_settimana is not None and tutti:
            model.Add(sum(tutti) <= max(per_settimana, consumo_settimana))


def _sede_congelata(ctx, key, day, slot, site_id, rep):
    """La sede `site_id` e' occupata in quella cella da una **congelata**?

    Rispecchia letteralmente la selezione dei letterali di
    `Vocabulary.site_occupied` (domain/solver/vocabulary.py): stessa lettura
    di `ctx.by_cell`, stesso filtro su `site_id`, stesso filtro di attivita'
    attiva nella firma. Se la selezione divergesse anche di un letterale il
    residuo sarebbe peggiore del difetto — e' la regola della casa sul modo di
    leggere `B`, applicata qui a una costante invece che a una soglia."""
    active = ctx.states[rep].activities
    return any(aid not in ctx.free
               and ctx.activities[aid].site_id == site_id
               and aid in active
               for aid, _ in ctx.by_cell.get((key, day, slot), ()))


@register("structural:site_transition")
class SiteTransitionBuilder(Builder):
    """Fra due lezioni su sedi diverse servono `site_transition_slots` fasce
    libere. Vale su **ogni** chiave di occupazione, non su una riga di
    vincolo: e' strutturale, come l'occupazione.

    ADR-018 si applica in **due** forme, e per mesi ce n'e' stata una sola.
    La regola dell'implicazione (`any_free`): se nessuna delle attivita' che
    toccano le due fasce e' libera, il vincolo e' un fatto sul passato e non si
    posta. ⚠ E — aggiunta il 2026-08-26 — il salto della **singola coppia gia'
    realizzata dalle congelate**: se `sa` e `sb` sono entrambe forzate da
    attivita' congelate (`_sede_congelata`), la clausola avrebbe entrambi i
    letterali a 1 ed e' insoddisfacibile comunque vada il piazzamento delle
    libere. La prima forma non copre la seconda: basta **una** libera che
    tocchi una delle due fasce — anche senza sede, anche incapace di riparare
    niente — perche' `any_free` sia vero e la clausola venga postata.
    Con una sola delle due sedi forzata la clausola resta, ed e' un divieto su
    una decisione del solver: ADR-018 lo concede anche quando produce
    `INFEASIBLE` (stesso caso 3 di `ImposedSuccessionBuilder` con finestra
    vuota).

    `build` posta due famiglie di clausole: `s == t` (due sedi diverse sulla
    stessa fascia, indipendente da `needed` — Important 1, Ruling 33) e
    `s < t` (le coppie a distanza insufficiente, vacua se `needed == 0`).
    Vedi il docstring del modulo per i dettagli e i limiti."""

    def build(self, ctx, model):
        sedi = _sedi(ctx)
        if len(sedi) < 2:
            return
        needed = ctx.states[ctx.signatures[0][0]].settings.site_transition_slots
        chiavi = sorted({k for (k, _d, _s) in ctx.by_cell}, key=str)
        posted = set()
        for rep, _ in ctx.signatures:
            active = ctx.states[rep].activities
            for key in chiavi:
                for day in range(ctx.grid.days_per_cycle):
                    per_fascia = [_sedi_raggiungibili(ctx, key, day, s)
                                  for s in range(ctx.grid.slots_per_day)]

                    # s == t (Important 1, riparazione Ruling 33): due sedi
                    # diverse sulla STESSA fascia sono sempre un cambio per
                    # il checker (gap_slots = -1, sempre < needed qualunque
                    # sia needed >= 0), quindi questa clausola non dipende
                    # da `needed` — postata anche a needed = 0. Di norma
                    # irraggiungibile (structural:occupation la vieta gia'
                    # a capienza 1), raggiungibile a
                    # simultaneous_capacity > 1 (vedi docstring del modulo).
                    for s in range(ctx.grid.slots_per_day):
                        tocca = {aid for aid, _ in ctx.by_cell.get((key, day, s), ())
                                  if aid in active}
                        if not any_free(ctx, tocca):
                            continue
                        for sa in per_fascia[s]:
                            sa_congelata = _sede_congelata(
                                ctx, key, day, s, sa, rep)
                            for sb in per_fascia[s]:
                                # `sb <= sa`, non `sb == sa`: qui s e t sono
                                # la stessa fascia, quindi la clausola e'
                                # simmetrica in (sa, sb) — `AddBoolOr` lo e'
                                # per costruzione — e `posted`, che tiene
                                # conto dell'ordine, non la deduplica. Senza
                                # questo ogni coppia di sedi veniva postata
                                # due volte identica (Minor 2 della ri-review
                                # del giro 1: sul Fermi 5604 -> 4806
                                # constraint a 2 sedi, 21830 -> 17042 a 4).
                                # ⚠ Nel blocco `s < t` sotto la simmetria non
                                # c'e': (s, sa) e (t, sb) sono fasce diverse,
                                # e scambiare le sedi e' un'altra clausola.
                                if sb <= sa:
                                    continue
                                if sa_congelata and _sede_congelata(
                                        ctx, key, day, s, sb, rep):
                                    continue   # vedi _sede_congelata
                                firma = (key, day, s, s, sa, sb,
                                         frozenset(tocca))
                                if firma in posted:
                                    continue
                                posted.add(firma)
                                model.AddBoolOr([
                                    ctx.vocab.site_occupied(
                                        key, day, s, sa, signature=rep).Not(),
                                    ctx.vocab.site_occupied(
                                        key, day, s, sb, signature=rep).Not(),
                                ])

                    if not needed:
                        continue   # la coppia s < t sotto e' interamente vacua
                    for s in range(ctx.grid.slots_per_day):
                        for t in range(s + 1, ctx.grid.slots_per_day):
                            if t - s - 1 >= needed:
                                continue   # gia' abbastanza lontane: vacuo
                            tocca = {
                                aid
                                for m in (s, t)
                                for aid, _ in ctx.by_cell.get((key, day, m), ())
                                if aid in active
                            }
                            if not any_free(ctx, tocca):
                                continue
                            for sa in per_fascia[s]:
                                sa_congelata = _sede_congelata(
                                    ctx, key, day, s, sa, rep)
                                for sb in per_fascia[t]:
                                    if sa == sb:
                                        continue
                                    if sa_congelata and _sede_congelata(
                                            ctx, key, day, t, sb, rep):
                                        continue   # vedi _sede_congelata
                                    firma = (key, day, s, t, sa, sb,
                                             frozenset(tocca))
                                    if firma in posted:
                                        continue
                                    posted.add(firma)
                                    model.AddBoolOr([
                                        ctx.vocab.site_occupied(
                                            key, day, s, sa, signature=rep).Not(),
                                        ctx.vocab.site_occupied(
                                            key, day, t, sb, signature=rep).Not(),
                                    ])
