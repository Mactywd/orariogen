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

⚠ **Caso verificato e non risolto (stesso Ruling, ultimo paragrafo): due
attivita' di sede diversa sulla STESSA fascia della stessa chiave.** Il
checker le conta entrambe (appende una voce per **ogni** attivita' che
occupa la fascia, `state.occupancy[(key, day, s)]`), quindi due attivita' di
sede diversa simultanee sulla stessa fascia sono un cambio. La costruzione a
coppie `s < t` (qui sotto) non puo' esprimerlo: non esiste una coppia con
`s == t`. Di norma e' irraggiungibile perche' la stessa fascia della stessa
chiave e' gia' vietata da `structural:occupation` (capienza 1) — ma
**verificato che e' raggiungibile** quando la chiave ha capienza cumulativa
`simultaneous_capacity > 1` (il campo esiste sulla `Resource` base, quindi
anche su classi/docenti, anche se il caso d'uso tipico e' aule/materiali):
costruita un'istanza con una classe a capienza 2, due attivita' di sede
diversa su docenti diversi piazzate sulla stessa fascia — zero finding di
occupazione, un `max_site_changes` `HARD` dal checker, nessuna coppia del
builder in grado di intercettarlo. **Non risolto qui**: e' un'osservazione
per il controller (il brief lo vieta esplicitamente come task di iniziativa),
non un difetto corretto in questo giro.

⚠ **ADR-018.** `MaxSiteChangesBuilder` posta somme su variabili derivate
(i letterali di cambio `c`), non su termini `(peso, id, letterale)`
separabili: stesso schema di `MaxGapBuilder`/`MaxPresenceBuilder`
(`time_presence.py`) — un tetto **clampato**, mai un salto del vincolo (il
`continue` e' stato sbagliato due volte su questo piano: review Task 6
Important 2, e Ruling 23 sul Task 8). `SiteTransitionBuilder` invece ha gia'
ADR-018 nella forma della regola dell'implicazione (`any_free`): non
toccato."""

from domain.models import ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import Builder, register
from domain.solver.residual import any_free

T = ResourceTimeConstraint.Type


def _sedi(ctx):
    return sorted({a.site_id for a in ctx.activities.values()
                   if a.site_id is not None})


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
            for s in range(ctx.grid.slots_per_day):
                for t in range(s + 1, ctx.grid.slots_per_day):
                    for sa in sedi:
                        for sb in sedi:
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


@register("structural:site_transition")
class SiteTransitionBuilder(Builder):
    """Fra due lezioni su sedi diverse servono `site_transition_slots` fasce
    libere. Vale su **ogni** chiave di occupazione, non su una riga di
    vincolo: e' strutturale, come l'occupazione.

    ADR-018 e' gia' presente nella forma della regola dell'implicazione
    (`any_free`): se nessuna delle attivita' che toccano le due fasce e'
    libera, il vincolo e' un fatto sul passato e non si posta."""

    def build(self, ctx, model):
        sedi = _sedi(ctx)
        if len(sedi) < 2:
            return
        needed = ctx.states[ctx.signatures[0][0]].settings.site_transition_slots
        if not needed:
            return
        chiavi = sorted({k for (k, _d, _s) in ctx.by_cell}, key=str)
        posted = set()
        for rep, _ in ctx.signatures:
            active = ctx.states[rep].activities
            for key in chiavi:
                for day in range(ctx.grid.days_per_cycle):
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
                            for sa in sedi:
                                for sb in sedi:
                                    if sa == sb:
                                        continue
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
