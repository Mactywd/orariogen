"""Gli otto tipi di ResourceTimeConstraint (l'asse Cardinalità), sulla risorsa
generica: stessa tabella per docenti e classi. Presenza ≠ attività: la
presenza include i buchi. I buchi si contano per mezza giornata: la pausa
pranzo non è mai un buco (linea di fine mattinata, vincoli.md)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.analysis.state import site_occupation
from domain.models import ResourceTimeConstraint

T = ResourceTimeConstraint.Type


def _finding(state, code, row, **quantities):
    name = state.resource_names.get(row.resource_id, str(row.resource_id))
    return Finding(code, causali.message(code, resource=name), Severity.HARD,
                   resources=(row.resource_id,), quantities=quantities)


class _TimeChecker(Checker):
    TYPE = None

    def check(self, state, resources=None):
        for row in state.time_rows:
            if row.type != self.TYPE:
                continue
            if resources is not None and row.resource_id not in resources:
                continue
            yield from self.violations(state, row, state.resource_days(row.resource_id))

    def violations(self, state, row, days):
        raise NotImplementedError


def _presence_minutes(state, slots):
    return (slots[-1] - slots[0] + 1) * state.grid.slot_minutes


def _halves(state, slots):
    """(fasce di mattina, fasce di pomeriggio)."""
    boundary = state.grid.morning_end_slot
    return [s for s in slots if s < boundary], [s for s in slots if s >= boundary]


def _gap_spans(state, key, slots):
    """I perimetri su cui contare i buchi di `key`: le due mezze giornate,
    oppure la giornata intera.

    🔑 Non è una variante del calcolo, è **il parametro di EDT**: la casella
    «Non conteggiare come buchi le ore libere prima o dopo la linea di fine
    mattinata», separata per classi e per docenti. Vedi
    `InstituteSettings.gaps_split_at_lunch`, dove sta la dimostrazione che
    spuntarla e spezzare alla linea sono la stessa cosa."""
    if state.settings.gaps_split_at_lunch(state.kinds.get(key)):
        return _halves(state, slots)
    return [slots]


@register(T.MIN_DISTRIBUTION)
class MinDistributionChecker(_TimeChecker):
    """⚠ Non monotono: la violazione è una **deficienza** (meno giornate
    qualificanti del minimo), e piazzare la **ripara**. A stato vuoto è
    massimamente violata — `days=0` — e ogni piazzamento la migliora
    cambiandone la chiave. Vedi `admissible_starts`."""
    TYPE = T.MIN_DISTRIBUTION
    PLACEMENT_MONOTONE = False

    def violations(self, state, row, days):
        threshold = row.params["min_minutes_per_day"]
        qualifying = [d for d, slots in days.items()
                      if len(slots) * state.grid.slot_minutes >= threshold]
        if len(qualifying) < row.params["min_days"]:
            yield _finding(state, "min_distribution", row,
                           days=len(qualifying), min_days=row.params["min_days"])


@register(T.MAX_HOURS)
class MaxHoursChecker(_TimeChecker):
    TYPE = T.MAX_HOURS

    def violations(self, state, row, days):
        sm = state.grid.slot_minutes
        for day, slots in days.items():
            morning, afternoon = _halves(state, slots)
            checks = [("max_hours_day", "day_minutes", len(slots)),
                      ("max_hours_morning", "morning_minutes", len(morning)),
                      ("max_hours_afternoon", "afternoon_minutes", len(afternoon))]
            for code, key, n_slots in checks:
                cap = row.params.get(key)
                if cap is not None and n_slots * sm > cap:
                    yield _finding(state, code, row,
                                   day=day, minutes=n_slots * sm, max_minutes=cap)


@register(T.MAX_PRESENCE)
class MaxPresenceChecker(_TimeChecker):
    TYPE = T.MAX_PRESENCE

    def violations(self, state, row, days):
        cap = row.params.get("max_minutes")
        for day, slots in days.items():
            presence = _presence_minutes(state, slots)
            if cap is not None and presence > cap:
                yield _finding(state, "max_presence", row,
                               day=day, minutes=presence, max_minutes=cap)
        max_days = row.params.get("days")
        if max_days is not None and len(days) > max_days:
            yield _finding(state, "max_presence_days", row,
                           days=len(days), max_days=max_days)


@register(T.ARRIVAL_DEPARTURE)
class ArrivalDepartureChecker(_TimeChecker):
    TYPE = T.ARRIVAL_DEPARTURE

    def violations(self, state, row, days):
        not_before = row.params.get("not_before_slot")
        not_after = row.params.get("not_after_slot")
        compliant = 0
        for day in range(state.grid.days_per_cycle):
            slots = days.get(day)
            if not slots:
                compliant += 1  # giornata vuota: rispettata
                continue
            ok = ((not_before is None or slots[0] >= not_before)
                  and (not_after is None or slots[-1] < not_after))
            compliant += ok
        if compliant < row.params["days"]:
            yield _finding(state, "arrival_departure", row,
                           days=compliant, min_days=row.params["days"])


@register(T.FREE_GUARANTEED)
class FreeGuaranteedChecker(_TimeChecker):
    """⚠ Non monotono, e in **entrambe** le direzioni. `free_days` cala
    piazzando, ma `free_half_days` si conta solo sui giorni **con** attività:
    occupare un giorno prima vuoto *aggiunge* una mezza giornata
    libera. La stessa asimmetria che ha costretto `FreeGuaranteedBuilder` alla
    disgiunzione reificata. Vedi `admissible_starts`.

    🔑 **E la soglia è quella raggiungibile, non quella scritta** — L8, chiuso
    il 2026-08-31. Una mezza giornata libera conta solo su un giorno
    **lavorato** (`libera = attivo AND NOT metà`), e un giorno lavorato ne può
    offrire al più una: il conteggio non supera mai il numero di giorni
    lavorati. Ne discendeva che una riga «due mezze giornate libere» diventava
    insoddisfacibile **perché si lavora meno** — spenta la palestra, il
    docente di scienze motorie restava con un giorno solo, e il modello
    rispondeva `INFEASIBLE` invece di scartare le ore che non ci stavano. Una
    famiglia che conta una quantità *sui giorni in cui si lavora* non può
    pretendere più di quanto quei giorni offrano.

    La soglia effettiva è quindi `min(richieste, giorni lavorati)`. Dove i
    giorni bastano — cioè ovunque la riga fosse soddisfacibile — non cambia
    nulla; dove non bastano chiede il massimo che *può* essere dato, che è
    ogni giorno lavorato con una mezza giornata libera. ⚠ Non è
    un'attenuazione della garanzia: è la garanzia detta senza la parte che
    nessun orario potrebbe onorare.

    ⚠ `free_days` non ha lo stesso problema e non prende lo stesso
    trattamento: lavorare meno *aumenta* i giorni liberi, quindi quel minimo
    non è mai reso irraggiungibile dallo scarto."""
    TYPE = T.FREE_GUARANTEED
    PLACEMENT_MONOTONE = False

    def violations(self, state, row, days):
        free_days = [d for d in range(state.grid.days_per_cycle) if d not in days]
        free_halves = 0
        for day, slots in days.items():
            morning, afternoon = _halves(state, slots)
            free_halves += (not morning) + (not afternoon)
        min_mezze = row.params.get("free_half_days", 0)
        soglia_mezze = min(min_mezze, len(days))
        short_days = len(free_days) < row.params.get("free_days", 0)
        short_halves = free_halves < soglia_mezze
        if short_days or short_halves:
            yield _finding(state, "free_guaranteed", row,
                           free_days=len(free_days), free_half_days=free_halves,
                           min_free_days=row.params.get("free_days", 0),
                           min_free_half_days=min_mezze)


@register(T.MAX_HALF_DAYS)
class MaxHalfDaysChecker(_TimeChecker):
    TYPE = T.MAX_HALF_DAYS

    def violations(self, state, row, days):
        worked, both = 0, []
        for day, slots in days.items():
            morning, afternoon = _halves(state, slots)
            worked += bool(morning) + bool(afternoon)
            if morning and afternoon:
                both.append(day)
        cap = row.params.get("max_half_days")
        if cap is not None and worked > cap:
            yield _finding(state, "max_half_days", row,
                           half_days=worked, max_half_days=cap)
        if row.params.get("only_half_day_per_day"):
            for day in both:
                yield _finding(state, "only_half_day", row, day=day)


@register(T.MAX_SITE_CHANGES)
class MaxSiteChangesChecker(_TimeChecker):
    """🔑 **Dentro una fascia non si viaggia.** Una fascia contribuisce
    l'**insieme** delle sedi che la occupano, e un cambio è una transizione
    fra due fasce consecutive (nella sottosequenza di quelle con sede nota)
    i cui insiemi **differiscono**. Due sedi diverse simultanee valgono
    quindi zero cambi, non uno: la risorsa non si è spostata, è in due posti
    insieme — cosa che `structural:site_transition` giudica *impossibile*,
    ma che non è un **viaggio**. Le due domande sono diverse («è fisicamente
    possibile?» contro «quante volte si è spostato?») e meritano risposte
    diverse.

    ⚠ È la decisione che mancava, non un dettaglio d'implementazione. Prima
    la sequenza si leggeva dalla lista `occupancy` in ordine d'inserimento,
    quindi `[A, B, A]` dava due cambi e `[B, A, A]` uno solo **sullo stesso
    orario**: il verdetto dipendeva dai pk. `domain/solver/builders/time_sites.py`
    si era fermato davanti a questo e aveva rifiutato di tradurre l'artefatto,
    lasciando `MaxSiteChangesBuilder` esatto solo a capienza 1.

    A capienza 1 — cioè ovunque, salvo l'aula col `Numero di aule` di EDT e
    gli stati già illegali — ogni fascia ha al più una sede e la nuova regola
    coincide con la vecchia riga per riga. Dove differisce conta **meno**
    cambi del massimo che l'ordine poteva produrre, cioè sbaglia verso il
    richiamo e mai verso la precisione: è il verso giusto per un checker, che
    mandando l'utente a smontare un vincolo sano fa il danno peggiore."""
    TYPE = T.MAX_SITE_CHANGES

    def violations(self, state, row, days):
        per_week = 0
        for day, slots in days.items():
            sites = [set(per_slot) for _, per_slot
                     in site_occupation(state, row.resource_id, day, slots)]
            changes = sum(a != b for a, b in zip(sites, sites[1:]))
            per_week += changes
            cap = row.params.get("per_day")
            if cap is not None and changes > cap:
                yield _finding(state, "max_site_changes", row,
                               day=day, changes=changes, max_changes=cap)
        cap = row.params.get("per_week")
        if cap is not None and per_week > cap:
            yield _finding(state, "max_site_changes", row,
                           changes=per_week, max_changes=cap)


@register(T.MAX_GAP_HOURS)
class MaxGapChecker(_TimeChecker):
    """⚠ Non monotono, e non era nell'elenco della review: il buco è
    `ultima − prima + 1 − conteggio`, quindi un piazzamento **dentro** un buco
    esistente alza il conteggio senza toccare gli estremi e il totale
    **cala**. Riparare una violazione ne cambia la chiave, e con la baseline
    già oltre il tetto (congelate) ogni cella risulterebbe nuova. Non si vede
    sul banco a testimone perché lì non c'è nessuna congelata, e con la sola
    attività di prova nessuna mezza giornata arriva a due fasce — ma il caso
    esiste appena una congelata lascia un buco. Vedi `admissible_starts`."""
    TYPE = T.MAX_GAP_HOURS
    PLACEMENT_MONOTONE = False

    def violations(self, state, row, days):
        sm = state.grid.slot_minutes
        total = 0
        for day, slots in days.items():
            for span in _gap_spans(state, row.resource_id, slots):
                if len(span) >= 2:
                    total += (span[-1] - span[0] + 1 - len(span)) * sm
        cap = row.params["max_gap_minutes"]
        if total > cap:
            yield _finding(state, "max_gap", row,
                           gap_minutes=total, max_gap_minutes=cap)
