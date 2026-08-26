"""I vincoli orari che sono puro **conteggio**: quante fasce in un giorno,
quante mezze giornate nella settimana. Nessuno di questi guarda *quali* fasce:
la prima e l'ultima sono affare di time_presence.py."""

from collections import defaultdict

from domain.analysis.checkers.time_constraints import (
    FreeGuaranteedChecker, MinDistributionChecker,
)
from domain.models import ResourceTimeConstraint
from domain.solver.builders.base import ResourceBuilder
from domain.solver.registry import register
from domain.solver.residual import frozen_occupies, residual_cap

T = ResourceTimeConstraint.Type


# --- ADR-018 sui due minimi non separabili ------------------------------
#
# MIN_DISTRIBUTION e FREE_GUARANTEED contano una quantita' che **non e'** una
# somma di contributi per attivita': giorni qualificanti, giorni liberi, mezze
# giornate libere. Il residuo non e' quindi additivo — una congelata non
# «consuma una quota», toglie gradi di liberta' — e ne' `residual_cap` ne'
# `residual_floor` lo esprimono. Il trattamento e' quello gia' in uso su
# `WeeklyOrderBuilder` (domain/solver/builders/subject_order.py), con lo
# stesso principio della spec §9.5:
#
#     INFEASIBLE che nasce dal **vietare un peggioramento** e' ammesso;
#     INFEASIBLE che nasce dal **pretendere una riparazione** non lo e'.
#
# Per ogni riga e per ogni firma si calcola `B`, il valore che la quantita'
# **contata dal checker** assume sul piazzamento corrente, e si sceglie fra tre
# esiti: soglia grezza se `B` gia' la soddisfa (il passato non e' il problema);
# soglia grezza se nessuna congelata tocca la risorsa (istanza infattibile per
# conto proprio, o solve da zero: clampare la spegnerebbe); altrimenti la
# disgiunzione reificata «ripara **oppure** non peggiorare».


def _quantita_baseline(checker, state, row, days):
    """Le `quantities` del finding che **il checker** produce su `days`, o
    `None` se `days` non viola la riga.

    Si chiama il checker di `domain/analysis` invece di riscriverne la
    condizione: se il conteggio del builder e quello del checker divergessero
    di uno, il residuo sarebbe peggio del difetto che corregge. `days` ha la
    forma di `ScheduleState.resource_days` — la stessa che `_TimeChecker.check`
    passa a `violations`."""
    for finding in checker.violations(state, row, days):
        return finding.quantities
    return None


def _congelate_sulla_risorsa(ctx, key, rep):
    """Almeno una congelata tocca questa risorsa in questa firma?"""
    fasce = range(ctx.grid.slots_per_day)
    return any(frozen_occupies(ctx, key, day, fasce, rep)
               for day in range(ctx.grid.days_per_cycle))


def _libere_sulla_risorsa(ctx, key, rep):
    attive = ctx.states[rep].activities
    return [aid for aid in ctx.free
            if aid in attive and key in ctx.tokens.get(aid, frozenset())]


def _status_quo_rappresentabile(ctx, key, rep):
    """Il piazzamento corrente e' riproducibile dentro il modello?

    Il ramo «non peggiorare» e' soddisfacibile **solo** se ogni attivita'
    libera che tocca la risorsa puo' restare dov'e'. Non puo' se non e'
    piazzata affatto (solve da zero, o parziale) o se un pre-filtro
    strutturale — griglia, festivo, indisponibilita' rossa — ha tolto dal
    dominio la cella dove si trova adesso. In quel caso chiedere di
    conservare `B` sarebbe una pretesa, non un divieto: e' il caveat
    sollevato dalla review, ed e' verificato qui invece che assunto."""
    placed = ctx.states[rep].placed
    for aid in _libere_sulla_risorsa(ctx, key, rep):
        pl = placed.get(aid)
        if pl is None or (pl.day, pl.start_slot) not in ctx.cells.get(aid, ()):
            return False
    return True


def _giorni_garantiti(ctx, key, rep):
    """`{giorno: [fasce]}` sulla risorsa contando **solo** le attivita' la cui
    collocazione attuale sopravvive nel modello: le congelate (dominio di
    cardinalita' uno per costruzione di `SolverContext.build`) e le libere
    gia' piazzate in una cella ammissibile.

    Serve a MIN_DISTRIBUTION, dove l'occupazione e' **monotona**: aggiungere
    ore a un giorno non puo' toglierlo dai qualificati. Il conteggio su un
    sottoinsieme dell'occupazione finale e' quindi un valore *raggiungibile*
    da ogni assegnazione, non solo osservato su questa — che e' cio' che
    rende sempre soddisfacibile il ramo status quo. Su FREE_GUARANTEED lo
    stesso trucco non vale (li' piu' occupazione **toglie** giorni liberi):
    la' serve la rappresentabilita' piena, vedi
    `_status_quo_rappresentabile`."""
    stato = ctx.states[rep]
    per_giorno = defaultdict(set)
    for aid, pl in stato.placed.items():
        if aid not in stato.activities or key not in stato.tokens[aid]:
            continue
        if aid in ctx.free and (pl.day, pl.start_slot) not in ctx.cells.get(aid, ()):
            continue
        per_giorno[pl.day].update(pl.slots)
    return {d: sorted(s) for d, s in sorted(per_giorno.items())}


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

    ⚠ Qui vale una proprieta' **locale al singolo giorno** che gli altri due
    minimi di questo file non hanno (review Task 7, Important 2 — corregge
    un'affermazione precedente che diceva troppo): una congelata puo' solo
    *aumentare* `sum(occ)` per il giorno che occupa, mai renderlo non
    qualificante — non esiste un modo per una congelata di far scendere
    `sm * sum(occ)` sotto la soglia per un giorno che altrimenti l'avrebbe
    superata. Ma questa proprieta' e' locale al giorno, **non implica
    l'immunita' al passato a livello di vincolo**: il congelamento toglie
    gradi di liberta', e puo' ridurre i giorni *distinti* raggiungibili sotto
    `min_days`. Controesempio: 3 attivita', `min_minutes_per_day=60,
    min_days=3` — tutte libere e' `OPTIMAL`; congelandone due sullo
    **stesso** giorno (day 0, due fasce) restano al piu' due giorni
    distinti raggiungibili (quello congelato e quello dell'unica libera
    residua): `INFEASIBLE`, per colpa del passato.

    ⚠ Quel controesempio era scritto qui e il vincolo si postava **grezzo**
    lo stesso, fino alla review finale (Finding 1) che l'ha misurato: il
    modello rifiutava perfino lo *status quo*. Ora il trattamento ADR-018 e'
    quello descritto in testa al modulo, con `B` = i giorni qualificanti su
    `_giorni_garantiti` — non su tutto il piazzamento corrente, perche' il
    ramo «non peggiorare» dev'essere soddisfacibile e le libere che siedono
    su una cella tolta dai pre-filtri non ci sarebbero piu'. Per la
    monotonia dell'occupazione un giorno qualificante in `_giorni_garantiti`
    resta qualificante in **ogni** assegnazione: `sum(qualificati) >= B` e'
    quindi soddisfatto per costruzione dal presente, mai una pretesa sul
    futuro.

    ⚠ Costo consapevole del ramo disgiuntivo, misurato e non nascosto: il
    solver **puo'** scegliere di non riparare anche quando potrebbe, perche'
    il modello non ha funzione di costo e i due rami sono alla pari. Nel
    caso «poche congelate + molte libere non ancora piazzate» la baseline
    del checker e' quasi sempre gia' violata (nulla e' piazzato) e `B` vale
    quanto le sole congelate qualificano: il ramo status quo diventa allora
    vacuo e la riga, di fatto, non vincola. E' una perdita di *qualita'*, non
    di correttezza (nessun finding nuovo), e vale per l'intera famiglia
    d'ordine di questo branch — `WeeklyOrderBuilder` ha la stessa forma.
    Vedi il report di questo giro.

    `ArrivalDepartureBuilder` resta invece sul residuo **per forzatura**: li'
    una congelata puo' *consumare* il minimo gia' a livello di un singolo
    giorno (occupare una fascia vietata), e nessuna libera puo' recuperare
    quel giorno — la soglia si abbassa a quanto resta raggiungibile senza
    bisogno di guardare il piazzamento corrente."""
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

        minimo = row.params["min_days"]
        quantita = _quantita_baseline(MinDistributionChecker(),
                                      ctx.states[rep], row,
                                      _giorni_garantiti(ctx, key, rep))
        if quantita is None or not _congelate_sulla_risorsa(ctx, key, rep):
            model.Add(sum(qualificati) >= minimo)
            return
        riparato = model.NewBoolVar(f"mindist_fix_{row.pk}_{key}_{rep}")
        model.Add(sum(qualificati) >= minimo).OnlyEnforceIf(riparato)
        model.Add(sum(qualificati) >= quantita["days"]).OnlyEnforceIf(riparato.Not())


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

    ⚠ Minimo garantito, **ma non immune al passato** (review Task 7,
    Important 2 — la spec del brief affermava il contrario, ed era falsa).
    Una congelata piazzata in una fascia proibita forza `viola = 1` per
    quel giorno: nessuna libera puo' farlo rientrare a conforme, spostando
    attivita' altrove non cambia nulla per **quel** giorno. Letta alla
    lettera, `sum(conformi) >= days` diventerebbe insoddisfacibile per
    colpa del solo passato — l'errore che ADR-018 esiste per evitare, qui
    nella direzione «minimo», non «tetto». Il residuo si applica **per
    forzatura** come in `MaxHalfDaysBuilder.post` (`frozen_occupies`, non
    `residual_cap`): i giorni gia' persi non generano letterali (il loro
    contributo e' 0 per costruzione, comunque), e la soglia si abbassa a
    quanto resta raggiungibile — `min(days, days_per_cycle - persi)`, mai
    sotto zero, mai clampata a zero se raggiungibile: e' un pavimento più
    basso, non uno spento."""
    TYPE = T.ARRIVAL_DEPARTURE

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        grid = ctx.grid
        not_before = row.params.get("not_before_slot")
        not_after = row.params.get("not_after_slot")
        proibite = [s for s in range(grid.slots_per_day)
                    if (not_before is not None and s < not_before)
                    or (not_after is not None and s >= not_after)]
        conformi, persi = [], 0
        for day in range(grid.days_per_cycle):
            if frozen_occupies(ctx, key, day, proibite, rep):
                persi += 1  # gia' non conforme per costruzione: nessuna
                continue    # libera puo' recuperarlo, non serve il letterale
            viola = model.NewBoolVar(f"ad_viola_{key}_{rep}_{day}")
            lits = [v.occupied(key, day, s, signature=rep) for s in proibite]
            if lits:
                model.AddMaxEquality(viola, lits)
            else:
                model.Add(viola == 0)
            conforme = model.NewBoolVar(f"ad_ok_{key}_{rep}_{day}")
            model.Add(conforme + viola == 1)
            conformi.append(conforme)
        soglia = min(row.params["days"], grid.days_per_cycle - persi)
        model.Add(sum(conformi) >= soglia)


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

    ⚠ Niente `if not len(span): continue` sulla meta' vuota (review Task 7,
    Important 1 — corretto qui, non in `MaxHalfDaysBuilder` dove e' giusto
    cosi': li' il checker fa `bool(afternoon)`, che vale 0 su una lista
    vuota e la salta correttamente da solo; qui il checker fa
    `(not afternoon)`, che vale **1** su ogni giorno lavorato quando il
    pomeriggio e' strutturalmente vuoto — saltare quella meta' azzerava un
    contributo che il checker conta gratis, rendendo insoddisfacibile
    qualunque `free_half_days >= 1` su una griglia senza pomeriggio.
    `v.half_active` su uno span vuoto e' gia' una costante 0 via
    `_max_or_zero`: non serve saltarla, basta lasciarla contribuire.

    ⚠ Minimo garantito, **ma non immune al passato** (Important 2, stessa
    correzione di `ArrivalDepartureBuilder`, sull'altra parte del
    ragionamento: qui le congelate possono *consumare* la soglia, non solo
    aiutarla). Una congelata che occupa un giorno forza quel giorno
    "attivo" — `libero` non potra' mai valere 1 li'; una congelata in una
    meta' specifica forza quella meta' "occupata" — `libera` non potra' mai
    valere 1 li', anche se l'altra meta' dello stesso giorno resta
    negoziabile. I termini gia' persi non generano letterali: restano fuori
    dalle due somme perche' varrebbero 0 comunque.

    ⚠ **Le due soglie non si clampano una per volta** (review finale,
    Finding 2). Fino al 2026-08-25 il residuo era
    `min(free_days, days_per_cycle - giorni_persi)` e
    `min(free_half_days, days_per_cycle - giorni_interamente_persi)`,
    calcolati **indipendentemente**. Ma i due conteggi si escludono a
    vicenda: `libera = attivo AND NOT meta` conta una mezza giornata solo se
    il **giorno lavora**, quindi un giorno che la soglia dei *giorni*
    obbliga a lasciare vuoto contribuisce **zero** mezze — mentre
    `days_per_cycle - giorni_interamente_persi` lo contava come se potesse
    contribuirne una. Ciascuna soglia era raggiungibile da sola, la
    congiunzione no, e il modello rispondeva INFEASIBLE per colpa del solo
    passato.

    Percio' il trattamento ADR-018 e' quello descritto in testa al modulo, e
    i due rami stanno sotto **lo stesso** booleano `riparato`: o si riparano
    entrambe le soglie, o si conservano entrambi i valori della baseline. Due
    booleani indipendenti riprodurrebbero esattamente il difetto.

    `B` viene dal **checker**, sul piazzamento corrente
    (`ScheduleState.resource_days`), e si usa **grezzo**, non clampato alla
    soglia. Il finding e' uno solo per entrambe le quantita', quindi una puo'
    essere gia' conforme (`B >= soglia`) mentre l'altra viola: clampare a
    `min(B, soglia)` renderebbe ciascun ramo implicato dall'altro e la
    disgiunzione collasserebbe in `>= min(B, soglia)` per quantita' — cioe'
    esattamente i due booleani indipendenti che il Finding 2 vieta
    (verificato: con il clamp,
    `test_free_guaranteed_le_due_soglie_stanno_sotto_un_solo_booleano`
    diventa rosso). `B` grezzo non autorizza mai una violazione nuova: su una
    quantita' conforme vale gia' `B >= soglia`, quindi il ramo status quo e'
    piu' stretto della soglia, non piu' largo.
    ⚠ A differenza di MIN_DISTRIBUTION qui non basta un
    sottoinsieme dell'occupazione: piu' occupazione **toglie** giorni e
    mezze libere, quindi `B` e' un valore osservato e non raggiungibile per
    monotonia. Se lo status quo non e' rappresentabile
    (`_status_quo_rappresentabile` falso: una libera non piazzata, o su una
    cella tolta dai pre-filtri) il ramo scende a zero — vacuo, mai una
    pretesa. Nella pratica quel caso si presenta di rado con la baseline
    gia' violata: con le libere non piazzate l'occupazione e' minima e i
    giorni liberi sono **tanti**, quindi la baseline e' quasi sempre pulita
    e si posta la soglia grezza."""
    TYPE = T.FREE_GUARANTEED

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        grid = ctx.grid
        giorni_liberi, mezze_libere = [], []
        halves = v.halves()
        for day in range(grid.days_per_cycle):
            attivo = v.day_active(key, day, signature=rep)
            if not frozen_occupies(ctx, key, day, range(grid.slots_per_day), rep):
                libero = model.NewBoolVar(f"freeday_{key}_{rep}_{day}")
                model.Add(libero + attivo == 1)
                giorni_liberi.append(libero)
            for half, span in enumerate(halves):
                if frozen_occupies(ctx, key, day, span, rep):
                    continue  # quella meta' e' gia' occupata dal passato
                meta = v.half_active(key, day, half, signature=rep)
                libera = model.NewBoolVar(f"freehalf_{key}_{rep}_{day}_{half}")
                # libera  <->  giorno attivo AND mezza giornata scarica
                model.AddBoolAnd([attivo, meta.Not()]).OnlyEnforceIf(libera)
                model.AddBoolOr([attivo.Not(), meta]).OnlyEnforceIf(libera.Not())
                mezze_libere.append(libera)

        minimo_giorni = row.params.get("free_days", 0)
        minimo_mezze = row.params.get("free_half_days", 0)
        stato = ctx.states[rep]
        quantita = _quantita_baseline(FreeGuaranteedChecker(), stato, row,
                                      stato.resource_days(key))
        if quantita is None or not _congelate_sulla_risorsa(ctx, key, rep):
            if minimo_giorni:
                model.Add(sum(giorni_liberi) >= minimo_giorni)
            if minimo_mezze:
                model.Add(sum(mezze_libere) >= minimo_mezze)
            return

        if _status_quo_rappresentabile(ctx, key, rep):
            b_giorni = quantita["free_days"]
            b_mezze = quantita["free_half_days"]
        else:
            b_giorni = b_mezze = 0
        riparato = model.NewBoolVar(f"freeguar_fix_{row.pk}_{key}_{rep}")
        if minimo_giorni:
            model.Add(sum(giorni_liberi) >= minimo_giorni).OnlyEnforceIf(riparato)
            model.Add(sum(giorni_liberi) >= b_giorni).OnlyEnforceIf(riparato.Not())
        if minimo_mezze:
            model.Add(sum(mezze_libere) >= minimo_mezze).OnlyEnforceIf(riparato)
            model.Add(sum(mezze_libere) >= b_mezze).OnlyEnforceIf(riparato.Not())
