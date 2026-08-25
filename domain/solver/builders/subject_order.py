"""I vincoli di materia che ragionano sull'**ordine** fra le occorrenze.

WEEKLY_ORDER e' il primo della famiglia: la prima occorrenza di A deve
precedere (o coincidere in posizione con) la prima occorrenza di B. Non
richiede di ordinare davvero le occorrenze nel modello: due AddMinEquality
sulla posizione canalizzata (vocab.pos) e un confronto bastano."""

from domain.models import SubjectConstraint
from domain.solver.builders.base import SubjectBuilder
from domain.solver.registry import register

T = SubjectConstraint.Type


@register(T.WEEKLY_ORDER)
class WeeklyOrderBuilder(SubjectBuilder):
    """La prima occorrenza di A precede la prima occorrenza di B
    (WeeklyOrderChecker.violations, domain/analysis/checkers/
    subject_constraints.py righe 179-188):

        if row.subject_a_id == row.subject_b_id or not a or not b:
            return
        if (b[0].day, b[0].start_slot) < (a[0].day, a[0].start_slot):
            yield ...

    Il checker esce senza vincolare in **due** casi, non uno. A = B e' il
    caso dominante in tutte le altre famiglie di materia; qui invece non
    vincola nulla — e' il guardiano principale di questo builder.

    `a[0]`/`b[0]` sono la prima occorrenza **piazzata** (ordinata per
    (day, start_slot) da _placed_of): `vocab.pos(aid) = day * slots_per_day
    + start_slot` e' ordine-isomorfo a quella coppia finche' start_slot <
    slots_per_day, garantito dalla griglia. Quindi «prima occorrenza» si
    traduce in AddMinEquality su pos, e il confronto del checker in
    prima_a <= prima_b.

    ADR-018 — il principio che vale per l'intera famiglia d'ordine:

        INFEASIBLE che nasce dal divieto di peggiorare e' ammesso;
        INFEASIBLE che nasce dalla pretesa di riparare non lo e'.

    Siano FA/FB il minimo di pos sulle attivita' **congelate** (di A e di B
    rispettivamente) attive in questa firma — None se non ce ne sono.
    Costanti note a build time: un'attivita' congelata ha ctx.cells di
    cardinalita' uno, quindi la sua posizione non dipende da nessuna
    variabile del modello.

    Due rami:

    - `FA is None or FB is None or FB >= FA`: le congelate (se ci sono) non
      violano gia' la riga, quindi il vincolo secco prima_a <= prima_b sta
      **prevenendo** una violazione nuova, mai riparando una vecchia. Che
      possa risultare INFEASIBLE e' esattamente cio' che ADR-018 concede
      (vedi il docstring di ForbiddenSequenceBuilder in subject_buckets.py).
      Include il caso in cui una delle due materie non ha ancora nessuna
      congelata attiva in questa firma: `FA`/`FB` contano **solo** le
      congelate, perche' solo quelle il solver non puo' toccare — "a"/"b"
      (i gruppi del builder, tutte le attivita' della materia in firma) sono
      gia' garantiti non vuoti dalla guardia sopra, ma possono non contenere
      nessuna congelata. Se una delle due manca, non esiste ancora una
      violazione che le libere non possano sciogliere da sole: qualunque
      INFEASIBLE che ne segua e' un divieto di peggiorare, non una pretesa
      di riparare — anche quando la baseline del checker (che conta solo le
      **piazzate**, un insieme diverso da "a"/"b" del builder) non e' pulita
      per via di una libera gia' piazzata prima dell'altra congelata.
    - `FA is not None and FB is not None and FB < FA`: le congelate **gia'**
      violano la riga (la prima occorrenza congelata di B precede quella di
      A). Un vincolo secco prima_a <= prima_b pretenderebbe che le libere
      **riparino** un difetto preesistente — vietato da ADR-018. Si posta
      invece una disgiunzione reificata con `riparato = NewBoolVar(...)`:

        - `prima_a <= prima_b` sotto `OnlyEnforceIf(riparato)` — la
          riparazione resta **ammessa**, mai imposta;
        - lo status quo, sotto `OnlyEnforceIf(riparato.Not())`: **ogni**
          attivita' **libera** di A e' vietata dalla cella di `FA` in poi
          (`pos(aid) >= FA + 1`), e simmetricamente ogni libera di B da
          `FB + 1`. Non e' `prima_a >= FA` (un vincolo sul *minimo*, che
          fissa il valore ma non chi lo realizza): due attivita' della
          stessa materia su parti diverse della stessa partizione
          (sdoppiamento) possono stare nella stessa cella, quindi una
          libera puo' **pareggiare** la posizione della congelata senza
          violare `prima_a >= FA` pur cambiando *chi* e' l'argmin — e
          `Finding.key` include l'identita' delle due attivita', non la
          loro posizione. Vietando la cella per **attivita'** (non solo il
          valore aggregato) l'argmin resta la congelata colpevole **per
          costruzione**: e' un divieto sulle libere, quindi ammesso da
          ADR-018. Nota che questo rende `prima_a >= FA` (e simmetricamente
          per B) **implicato** — ogni libera sta sopra `FA`, la congelata ci
          sta esattamente — quindi non si posta piu' come vincolo a se':
          tenerlo accanto sarebbe ridondante e maschererebbe le mutazioni
          che rompono il divieto per-attivita'.
          ⚠ Costo consapevole: si vietano anche i pareggi che *non*
          avrebbero cambiato l'argmin (quando la libera non e' comunque la
          prima nell'ordine di inserimento del queryset). Quali siano
          dipende da quell'ordine — un artefatto di `_placed_of`
          (`sorted` stabile su `state.placed`), non una semantica su cui
          vincolare; vedi la voce corrispondente in CLAUDE.md, «Ancora
          aperto», accanto a `MaxSiteChangesChecker`.

    ⚠ Il ramo disgiuntivo **puo'** rendere il modello INFEASIBLE se ne'
    riparare ne' mantenere lo status quo hanno spazio (es. le libere non
    hanno altrove dove andare). E' voluto: e' la stessa proprieta' del
    clamp a zero di `residual_cap`, ed e' testualmente cio' che ADR-018
    concede."""
    TYPE = T.WEEKLY_ORDER

    def post(self, ctx, model, row, keys, rep):
        if row.subject_a_id == row.subject_b_id:
            return
        v = ctx.vocab
        a = v.subject_activities(keys, row.subject_a_id, signature=rep)
        b = v.subject_activities(keys, row.subject_b_id, signature=rep)
        if not a or not b:
            return

        prima_a = model.NewIntVar(
            0, ctx.grid.days_per_cycle * ctx.grid.slots_per_day - 1,
            f"weekorder_a_{row.pk}_{rep}")
        model.AddMinEquality(prima_a, [v.pos(aid) for aid in a])
        prima_b = model.NewIntVar(
            0, ctx.grid.days_per_cycle * ctx.grid.slots_per_day - 1,
            f"weekorder_b_{row.pk}_{rep}")
        model.AddMinEquality(prima_b, [v.pos(bid) for bid in b])

        width = ctx.grid.slots_per_day

        def _frozen_pos(aid):
            # dominio congelato: cardinalita' uno, per costruzione di
            # SolverContext.build (elif aid in placed: cells[aid] = {...}).
            (day, slot) = next(iter(ctx.cells[aid]))
            return day * width + slot

        fa_vals = [_frozen_pos(aid) for aid in a if aid not in ctx.free]
        fb_vals = [_frozen_pos(bid) for bid in b if bid not in ctx.free]
        FA = min(fa_vals) if fa_vals else None
        FB = min(fb_vals) if fb_vals else None

        if FA is None or FB is None or FB >= FA:
            model.Add(prima_a <= prima_b)
            return

        riparato = model.NewBoolVar(f"weekorder_fix_{row.pk}_{rep}")
        model.Add(prima_a <= prima_b).OnlyEnforceIf(riparato)
        # status quo: divieto per attivita', non sul solo minimo aggregato
        # (vedi il docstring) -- esclude anche il pareggio con la congelata.
        for aid in a:
            if aid in ctx.free:
                model.Add(v.pos(aid) >= FA + 1).OnlyEnforceIf(riparato.Not())
        for bid in b:
            if bid in ctx.free:
                model.Add(v.pos(bid) >= FB + 1).OnlyEnforceIf(riparato.Not())
