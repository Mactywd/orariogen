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


@register(T.MIN_DISTRIBUTION)
class MinDistributionBuilder(ResourceBuilder):
    """MinDistributionChecker (`domain/analysis/checkers/time_constraints.py`,
    `MinDistributionChecker.violations`) conta i giorni con
    `len(slots) * slot_minutes >= min_minutes_per_day` e ne vuole almeno
    `min_days`.

    ⚠ Minimo garantito, non tetto (spec §3.1, vedi `residual.py`): niente
    `residual_cap`. Le attivita' congelate contribuiscono alla somma dentro
    `occupied` come qualunque altra — se da sole bastano gia' a soddisfare
    `min_days`, il vincolo `sum(qualificati) >= min_days` e' vacuo per
    costruzione, mai infattibile."""
    TYPE = T.MIN_DISTRIBUTION

    def post(self, ctx, model, row, rep):
        sm, v, key = ctx.grid.slot_minutes, ctx.vocab, row.resource_id
        soglia = row.params["min_minutes_per_day"]
        qualificati = []
        for day in range(ctx.grid.days_per_cycle):
            occ = [v.occupied(key, day, s, signature=rep)
                   for s in range(ctx.grid.slots_per_day)]
            q = model.NewBoolVar(f"qualifies_{key}_{rep}_{day}")
            model.Add(sm * sum(occ) >= soglia).OnlyEnforceIf(q)
            model.Add(sm * sum(occ) < soglia).OnlyEnforceIf(q.Not())
            qualificati.append(q)
        model.Add(sum(qualificati) >= row.params["min_days"])


@register(T.ARRIVAL_DEPARTURE)
class ArrivalDepartureBuilder(ResourceBuilder):
    """ArrivalDepartureChecker (`ArrivalDepartureChecker.violations`) legge
    `slots = days.get(day)`: **un giorno senza attivita' conta come
    conforme** (`if not slots: compliant += 1`), non come violazione — la
    prima trappola di questo task. Per un giorno *con* attivita', e' conforme
    se `slots[0] >= not_before_slot` e `slots[-1] < not_after_slot`.

    ⚠ Non servono variabili di prima/ultima fascia. «La prima fascia e' >=
    not_before» equivale a «nessuna occupazione prima di not_before»;
    «l'ultima e' < not_after» a «nessuna occupazione da not_after in poi». Un
    giorno senza occupazioni in nessuna fascia proibita non ha letterali (o li
    ha tutti a 0): `viola` risulta 0 e il giorno e' conforme — combacia col
    `compliant += 1` del giorno vuoto, senza doverlo trattare come caso a
    parte.

    Minimo garantito: niente `residual_cap`. Se i giorni gia' conformi per
    via delle congelate bastano a `days`, `sum(conformi) >= days` e' vacuo."""
    TYPE = T.ARRIVAL_DEPARTURE

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        not_before = row.params.get("not_before_slot")
        not_after = row.params.get("not_after_slot")
        proibite = [s for s in range(ctx.grid.slots_per_day)
                    if (not_before is not None and s < not_before)
                    or (not_after is not None and s >= not_after)]
        conformi = []
        for day in range(ctx.grid.days_per_cycle):
            viola = model.NewBoolVar(f"ad_viola_{key}_{rep}_{day}")
            lits = [v.occupied(key, day, s, signature=rep) for s in proibite]
            if lits:
                model.AddMaxEquality(viola, lits)
            else:
                model.Add(viola == 0)
            conforme = model.NewBoolVar(f"ad_ok_{key}_{rep}_{day}")
            model.Add(conforme + viola == 1)
            conformi.append(conforme)
        model.Add(sum(conformi) >= row.params["days"])


@register(T.FREE_GUARANTEED)
class FreeGuaranteedBuilder(ResourceBuilder):
    """FreeGuaranteedChecker (`FreeGuaranteedChecker.violations`) conta
    `free_days` sui giorni **assenti da `days`** (`d not in days`, esatto: un
    giorno assente e' un giorno libero, e sommare `not day_active` su tutti i
    giorni coincide). Ma conta `free_halves` iterando `for day, slots in
    days.items()`: **solo sui giorni con almeno un'attivita'**. Un giorno
    completamente vuoto non compare in `days` e contribuisce **zero** mezze
    giornate libere, non due — la seconda trappola di questo task. Sommare
    `not half_active` su tutte le mezze giornate (ignorando se il giorno e'
    attivo) conterebbe di piu', renderebbe la soglia piu' facile e
    accetterebbe orari che il checker boccia: la direzione sbagliata.

    Percio' `libera` (mezza giornata libera-che-conta) e' congiunta con
    `giorno attivo`: vera solo se il giorno lavora e quella meta' e' scarica.

    Minimo garantito: niente `residual_cap`. Se le congelate bastano gia' a
    coprire `free_days`/`free_half_days`, le somme risultano vacue."""
    TYPE = T.FREE_GUARANTEED

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        giorni_liberi, mezze_libere = [], []
        for day in range(ctx.grid.days_per_cycle):
            attivo = v.day_active(key, day, signature=rep)
            libero = model.NewBoolVar(f"freeday_{key}_{rep}_{day}")
            model.Add(libero + attivo == 1)
            giorni_liberi.append(libero)
            for half, span in enumerate(v.halves()):
                if not len(span):
                    continue
                meta = v.half_active(key, day, half, signature=rep)
                libera = model.NewBoolVar(f"freehalf_{key}_{rep}_{day}_{half}")
                # libera  <->  giorno attivo AND mezza giornata scarica
                model.AddBoolAnd([attivo, meta.Not()]).OnlyEnforceIf(libera)
                model.AddBoolOr([attivo.Not(), meta]).OnlyEnforceIf(libera.Not())
                mezze_libere.append(libera)
        minimo_giorni = row.params.get("free_days", 0)
        if minimo_giorni:
            model.Add(sum(giorni_liberi) >= minimo_giorni)
        minimo_mezze = row.params.get("free_half_days", 0)
        if minimo_mezze and mezze_libere:
            model.Add(sum(mezze_libere) >= minimo_mezze)
