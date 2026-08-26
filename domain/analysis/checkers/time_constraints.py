"""Gli otto tipi di ResourceTimeConstraint (l'asse Cardinalità), sulla risorsa
generica: stessa tabella per docenti e classi. Presenza ≠ attività: la
presenza include i buchi. I buchi si contano per mezza giornata: la pausa
pranzo non è mai un buco (linea di fine mattinata, vincoli.md)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
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
    disgiunzione reificata. Vedi `admissible_starts`."""
    TYPE = T.FREE_GUARANTEED
    PLACEMENT_MONOTONE = False

    def violations(self, state, row, days):
        free_days = [d for d in range(state.grid.days_per_cycle) if d not in days]
        free_halves = 0
        for day, slots in days.items():
            morning, afternoon = _halves(state, slots)
            free_halves += (not morning) + (not afternoon)
        short_days = len(free_days) < row.params.get("free_days", 0)
        short_halves = free_halves < row.params.get("free_half_days", 0)
        if short_days or short_halves:
            yield _finding(state, "free_guaranteed", row,
                           free_days=len(free_days), free_half_days=free_halves,
                           min_free_days=row.params.get("free_days", 0),
                           min_free_half_days=row.params.get("free_half_days", 0))


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


def _site_sequence(state, key, day, slots):
    sequence = []
    for s in slots:
        for aid in state.occupancy[(key, day, s)]:
            site = state.activities[aid].site_id
            if site is not None:
                sequence.append(site)
    return sequence


@register(T.MAX_SITE_CHANGES)
class MaxSiteChangesChecker(_TimeChecker):
    TYPE = T.MAX_SITE_CHANGES

    def violations(self, state, row, days):
        per_week = 0
        for day, slots in days.items():
            sites = _site_sequence(state, row.resource_id, day, slots)
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
            for half in _halves(state, slots):
                if len(half) >= 2:
                    total += (half[-1] - half[0] + 1 - len(half)) * sm
        cap = row.params["max_gap_minutes"]
        if total > cap:
            yield _finding(state, "max_gap", row,
                           gap_minutes=total, max_gap_minutes=cap)
