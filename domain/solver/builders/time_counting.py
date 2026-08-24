"""I vincoli orari che sono puro **conteggio**: quante fasce in un giorno,
quante mezze giornate nella settimana. Nessuno di questi guarda *quali* fasce:
la prima e l'ultima sono affare di time_presence.py."""

from domain.models import ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import register
from domain.solver.residual import frozen_occupies, residual_cap

T = ResourceTimeConstraint.Type


@register(T.MAX_HOURS)
class MaxHoursBuilder(ResourceBuilder):
    """MaxHoursChecker conta `len(slots)` per giornata, mattina e pomeriggio,
    dove `slots` sono le fasce **distinte** occupate.

    ⚠ Qui si somma un termine per ogni voce di by_cell, cioe' per ogni
    (attivita', fascia). Coincide con il conteggio delle fasce distinte finche'
    due attivita' non occupano la stessa cella sulla stessa chiave — che
    OccupationBuilder vieta. Nel caso residuo (capacita' simultanea > 1) la
    somma e' **piu' grande** del conteggio del checker, quindi il vincolo e'
    piu' stretto: direzione sicura."""
    TYPE = T.MAX_HOURS

    def post(self, ctx, model, row, rep):
        sm, v = ctx.grid.slot_minutes, ctx.vocab
        active = ctx.states[rep].activities
        for day in range(ctx.grid.days_per_cycle):
            spans = (("day_minutes", range(ctx.grid.slots_per_day)),
                     ("morning_minutes", v.halves()[0]),
                     ("afternoon_minutes", v.halves()[1]))
            for param, span in spans:
                cap = row.params.get(param)
                if cap is None or not len(span):
                    continue
                terms = [(sm, aid, lit)
                         for slot in span
                         for aid, lit in ctx.by_cell.get(
                             (row.resource_id, day, slot), ())
                         if aid in active]
                liberi, residuo = residual_cap(ctx, terms, cap)
                if liberi:
                    model.Add(sum(w * lit for w, lit in liberi) <= residuo)


@register(T.MAX_HALF_DAYS)
class MaxHalfDaysBuilder(ResourceBuilder):
    """MaxHalfDaysChecker somma bool(mattina) + bool(pomeriggio) sui giorni con
    attivita'. Un giorno vuoto contribuisce 0 in entrambi i sensi, quindi
    sommare half_active su **tutte** le mezze giornate e' esatto.

    ⚠ half_active e' una variabile derivata: il residuo di ADR-018 si applica
    per **forzatura**, non per sottrazione di termini. Vedi frozen_occupies."""
    TYPE = T.MAX_HALF_DAYS

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        cap = row.params.get("max_half_days")
        if cap is not None:
            terms, consumo = [], 0
            for day in range(ctx.grid.days_per_cycle):
                for half, span in enumerate(v.halves()):
                    if not len(span):
                        continue
                    if frozen_occupies(ctx, key, day, span, rep):
                        consumo += 1
                    else:
                        terms.append(v.half_active(key, day, half, signature=rep))
            if terms:
                model.Add(sum(terms) <= max(0, cap - consumo))
        if row.params.get("only_half_day_per_day"):
            mattina, pomeriggio = v.halves()
            if len(mattina) and len(pomeriggio):
                for day in range(ctx.grid.days_per_cycle):
                    # ADR-018 (review Task 6, Important 1): se le sole
                    # congelate occupano gia' entrambe le meta' di questo
                    # giorno, AddAtMostOne([1, 1]) sarebbe insoddisfacibile —
                    # colpa del passato, non della libera. Con una sola meta'
                    # congelata il vincolo degrada correttamente a «l'altra
                    # deve restare a 0», ed e' il residuo giusto: si posta.
                    if (frozen_occupies(ctx, key, day, mattina, rep)
                            and frozen_occupies(ctx, key, day, pomeriggio, rep)):
                        continue
                    model.AddAtMostOne([
                        v.half_active(key, day, 0, signature=rep),
                        v.half_active(key, day, 1, signature=rep)])
