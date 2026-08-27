"""I vincoli di materia che ragionano sull'**ordine** fra le occorrenze.

WEEKLY_ORDER e' il primo della famiglia: la prima occorrenza di A deve
precedere (o coincidere in posizione con) la prima occorrenza di B. Non
richiede di ordinare davvero le occorrenze nel modello: due AddMinEquality
sulla posizione canalizzata (vocab.pos) e un confronto bastano.

HALF_DAY_GAP e' il terzo: uno scarto minimo fra occorrenze, in mezze
giornate. Si traduce senza ordinare esplicitamente, riusando i due helper
gia' scritti per i secchi di materia (subject_buckets.py, post_separable e
post_cross): ogni coppia di mezze giornate a distanza inferiore al param e'
uno dei quattro casi che quella tabella gia' risolve."""

from domain.models import SubjectConstraint
from domain.solver.builders.base import SubjectBuilder
from domain.solver.builders.subject_buckets import post_cross, post_separable
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

        # ⚠ Il limite superiore comprende la sentinella di `vocab.pos`: se
        # tutte le occorrenze di un lato sono scartate, il loro minimo *è* la
        # sentinella, e un limite più stretto renderebbe infattibile lo scarto.
        fuori = ctx.grid.days_per_cycle * ctx.grid.slots_per_day
        prima_a = model.NewIntVar(0, fuori, f"weekorder_a_{row.pk}_{rep}")
        model.AddMinEquality(prima_a, [v.pos(aid) for aid in a])
        prima_b = model.NewIntVar(0, fuori, f"weekorder_b_{row.pk}_{rep}")
        model.AddMinEquality(prima_b, [v.pos(bid) for bid in b])

        # `WeeklyOrderChecker` legge le sole occorrenze **piazzate** e non dice
        # nulla quando un lato non ne ha (`if not a or not b: return`). Il
        # vincolo va quindi condizionato: senza, un lato interamente scartato
        # varrebbe la sentinella e `prima_a <= prima_b` costringerebbe a
        # scartare anche l'altro lato.
        guardie = [g for g in (v.qualcuna_piazzata(a), v.qualcuna_piazzata(b))
                   if g is not None]

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
            model.Add(prima_a <= prima_b).OnlyEnforceIf(guardie)
            return

        riparato = model.NewBoolVar(f"weekorder_fix_{row.pk}_{rep}")
        ctx.riparazioni.append(riparato)
        model.Add(prima_a <= prima_b).OnlyEnforceIf(guardie + [riparato])
        # status quo: divieto per attivita', non sul solo minimo aggregato
        # (vedi il docstring) -- esclude anche il pareggio con la congelata.
        for aid in a:
            if aid in ctx.free:
                model.Add(v.pos(aid) >= FA + 1).OnlyEnforceIf(riparato.Not())
        for bid in b:
            if bid in ctx.free:
                model.Add(v.pos(bid) >= FB + 1).OnlyEnforceIf(riparato.Not())


@register(T.IMPOSED_SUCCESSION)
class ImposedSuccessionBuilder(SubjectBuilder):
    """Lo scarto fra occorrenze consecutive di una materia (A = B), o fra
    ogni occorrenza di A e la B piu' vicina che la segue (A != B) —
    `ImposedSuccessionChecker.violations`, domain/analysis/checkers/
    subject_constraints.py righe 191-207:

        delay = row.param or 1
        if row.subject_a_id == row.subject_b_id:
            halves = [(_half(...), p.activity_id) for p in a]
            for (h1, a1), (h2, a2) in zip(halves, halves[1:]):
                if h2 - h1 > delay: yield ...
        else:
            b_halves = [_half(...) for p in b]
            for pa in a:
                ha = _half(...)
                if not any(0 < hb - ha <= delay for hb in b_halves):
                    yield ..., [pa.activity_id], ...

    ⚠ **Il checker ha due semantiche in una riga, e nessuna guardia
    d'uscita.** A differenza di WEEKLY_ORDER (che esce con `not a or not b`),
    qui con `b` vuoto il ramo A != B **non esce**: `any(...)` su una lista
    vuota e' falso, quindi *ogni* occorrenza di A diventa una violazione. Non
    si ragiona per analogia con WeeklyOrderBuilder: il trattamento sotto lo
    riflette esplicitamente.

    Sia `n = ctx.grid.days_per_cycle * 2` (le mezze giornate del ciclo).

    **Ramo A = B** (`_post_same`). Il checker guarda gli scarti fra
    occorrenze **consecutive**. Si traduce senza ordinare esplicitamente le
    occorrenze: per ogni coppia di mezze giornate `u < w` con letterali
    (`sa[h] = vocab.subject_bucket(..., "half", h, signature=rep)`) tali che
    `w > u + delay`,

        AddBoolOr([sa[u].Not(), sa[w].Not()] + [sa[m] per m in (u, w) con
                                                 letterale])

    Il termine `+ [sa[m] ...]` e' cio' che rende la clausola vera quando
    esiste un'occorrenza strettamente in mezzo: in quel caso `u` e `w` non
    sono consecutive per il checker (la coppia consecutiva vera diventa
    `(u, m)`/`(m, w)`), e la clausola su `(u, w)` diventa un vincolo vero ma
    ridondante — corretto lasciarlo postato, perche' e' gia' soddisfatto per
    costruzione, non perche' vada rimosso.

    **ADR-018, ramo A = B.** Si salta la coppia `(u, w)` quando una
    **congelata** occupa `u`, una occupa `w`, e **nessuna congelata** occupa
    una mezza giornata strettamente in mezzo. In quel caso `sa[u]` e `sa[w]`
    sono gia' entrambi forzati a 1 dalle congelate (nessun altro letterale
    libero puo' cambiarlo), quindi la clausola — se postata — si ridurrebbe
    a "una libera deve riempire una mezza giornata fra `u` e `w`": una
    pretesa di riparare una violazione gia' scritta nella baseline, vietata
    da ADR-018. ⚠ **Non si salta quando uno solo dei due estremi e'
    congelato**: li' l'altro estremo e' ancora una decisione del solver (una
    libera che scegliesse di occupare quella mezza giornata creerebbe una
    violazione **nuova**, con un id di attivita' nuovo in `Finding.key` — non
    la stessa gia' presente nella baseline), quindi il vincolo resta un
    divieto legittimo su quella decisione, non una riparazione del passato.
    Se esiste una congelata strettamente in mezzo, la coppia non viene
    saltata ma la clausola e' comunque trivialmente vera per costruzione (il
    termine `sa[m]` di quella congelata vale 1): saltarla o no e' equivalente
    in quel caso, quindi la guardia si limita al caso in cui salterebbe
    davvero qualcosa — nessuna congelata in mezzo.

    **Ramo A != B** (`post_cross`). Il checker chiede, per **ogni
    occorrenza** di A: esiste una B strettamente dopo, entro `delay` mezze
    giornate. Il finding e' per occorrenza (`[pa.activity_id]`), quindi il
    trigger dev'essere il singolo letterale di A, **non** l'indicatore
    aggregato `subject_bucket` (che confonderebbe congelate e libere nello
    stesso secchio, perdendo la distinzione che ADR-018 richiede): per ogni
    mezza giornata `u`, sia `finestra` l'insieme dei letterali di B nelle
    mezze giornate `(u, min(u + delay, n - 1)]`. Se una **congelata** di B
    occupa gia' una di quelle mezze giornate, la clausola sarebbe comunque
    vera per costante — non si posta nulla per `u`. Altrimenti, per ogni
    occorrenza **libera** di A in `u`:

        AddBoolOr([lit(A, u).Not()] + finestra)

    Le occorrenze **congelate** di A in `u` non generano nessun trigger: la
    loro eventuale violazione (nessuna B nella finestra) e' gia' scritta
    nella baseline, e forzare una libera di B a comparire li' sarebbe una
    riparazione vietata da ADR-018. Una libera di A nella stessa mezza
    giornata `u` produrrebbe invece un finding **nuovo** (id diverso), quindi
    il suo letterale resta soggetto al vincolo.

    ⚠ Con `finestra` vuota (nessun letterale di B in quell'intervallo, ne'
    libero ne' congelato) la clausola diventa `lit(A, u).Not()`: vieta a
    quella libera di stare li'. Corretto e voluto — e' un divieto su una
    decisione del solver, non una pretesa di riparare qualcosa che gia'
    esiste. **Puo' rendere il modello INFEASIBLE** se quella libera non ha
    altrove dove andare: e' esattamente cio' che ADR-018 concede (stessa
    proprieta' del ramo disgiuntivo di WeeklyOrderBuilder e del quarto ramo
    di `post_cross` in subject_buckets.py).

    Nota di implementazione: questo builder **non** riusa il `post_cross` di
    subject_buckets.py — quella funzione posta una cardinalita' aggregata
    (`ha + hb <= 1`), un vincolo diverso da quello per-occorrenza richiesto
    qui. Il nome del metodo privato sotto e' volutamente distinto per non
    suggerire una parentela che non c'e'."""
    TYPE = T.IMPOSED_SUCCESSION

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        n = ctx.grid.days_per_cycle * 2
        delay = row.param or 1
        if row.subject_a_id == row.subject_b_id:
            self._post_same(ctx, model, v, row.subject_a_id, keys, rep, n, delay)
        else:
            self._post_ordered(ctx, model, v, row.subject_a_id, row.subject_b_id,
                               keys, rep, n, delay)

    def _post_same(self, ctx, model, v, subject_id, keys, rep, n, delay):
        # sa[h]: indicatore aggregato della materia nella mezza giornata h,
        # solo per le mezze giornate che hanno almeno un letterale (le altre
        # sarebbero costanti 0, e la clausola sarebbe banale). frozen[h]:
        # una congelata occupa gia' quella mezza giornata, nota a build time.
        sa, frozen = {}, {}
        for h in range(n):
            lits = v.subject_literals(keys, subject_id, "half", h, signature=rep)
            if not lits:
                continue
            sa[h] = v.subject_bucket(keys, subject_id, "half", h, signature=rep)
            frozen[h] = any(aid not in ctx.free for aid, _ in lits)
        halves = sorted(sa)
        for u in halves:
            for hi in halves:
                if hi <= u + delay:
                    continue
                if frozen.get(u) and frozen.get(hi):
                    # ADR-018: gia' violato dalla baseline (entrambi gli
                    # estremi congelati, nulla di congelato in mezzo) --
                    # postare pretenderebbe che una libera ripari il passato.
                    if not any(frozen.get(m) for m in range(u + 1, hi)):
                        continue
                model.AddBoolOr(
                    [sa[u].Not(), sa[hi].Not()]
                    + [sa[m] for m in range(u + 1, hi) if m in sa])

    def _post_ordered(self, ctx, model, v, subject_a_id, subject_b_id,
                      keys, rep, n, delay):
        for u in range(n):
            finestra = []
            b_frozen = False
            for h in range(u + 1, min(u + delay, n - 1) + 1):
                lits = v.subject_literals(keys, subject_b_id, "half", h, signature=rep)
                finestra.extend(lit for _aid, lit in lits)
                if any(aid not in ctx.free for aid, _ in lits):
                    b_frozen = True
            if b_frozen:
                # la finestra e' gia' coperta da una B congelata: la
                # clausola sarebbe vera per costante per ogni A in u.
                continue
            for aid, lit in v.subject_literals(keys, subject_a_id, "half", u,
                                               signature=rep):
                if aid in ctx.free:
                    model.AddBoolOr([lit.Not()] + finestra)


@register(T.HALF_DAY_GAP)
class HalfDayGapBuilder(SubjectBuilder):
    """Scarto minimo fra occorrenze, misurato in mezze giornate
    (HalfDayGapChecker.violations, domain/analysis/checkers/
    subject_constraints.py righe 211-229):

        same = row.subject_a_id == row.subject_b_id
        merged = [(_half(...), p.activity_id, "a") for p in a]
        if not same:
            merged += [(_half(...), p.activity_id, "b") for p in b]
        merged.sort()
        for (h1, a1, s1), (h2, a2, s2) in zip(merged, merged[1:]):
            crossed = same or s1 != s2
            if crossed and a1 != a2 and h2 - h1 < row.param:
                yield ...

    Il checker ordina le occorrenze e confronta solo le coppie
    **consecutive** nell'ordinamento fuso; con A != B soltanto quelle
    **incrociate** fra le due sorgenti ("a"/"b" nella tupla, non l'identita'
    delle materie: con A = B ogni coppia e' incrociata per definizione).

    ⚠ **Non e' il caso "piu' stretto, mai piu' largo" — e' equivalente.**
    Vincolare tutte le coppie incrociate (quello che fa questo builder) e
    vincolare solo le consecutive incrociate nell'ordinamento (quello che fa
    il checker) ammettono esattamente lo stesso insieme di piazzamenti.

    Dimostrazione: se esiste una coppia incrociata a distanza < param, ne
    esiste una **adiacente** (consecutiva in `merged`) altrettanto corta o
    piu' corta. Si prenda, fra tutte le coppie incrociate corte, quella con
    il minor numero di occorrenze strettamente in mezzo. Se qualcosa c'e' in
    mezzo, quel qualcosa ha sorgente "a" o "b": rispetto a **uno** dei due
    estremi originali (same=True: sempre incrociata; same=False: incrociata
    se ha sorgente diversa da quell'estremo — e almeno uno dei due estremi
    ha per forza sorgente diversa dall'occorrenza in mezzo, visto che i due
    estremi hanno sorgenti diverse fra loro nel caso same=False, o sono
    comunque "a" nel caso same=True dove ogni sorgente incrocia) forma una
    coppia incrociata di distanza non maggiore e con **meno** occorrenze in
    mezzo — contro la minimalita' scelta. Quindi la coppia minima e'
    adiacente: vincolare tutte le incrociate o solo le adiacenti incrociate
    produce lo stesso vincolo. (Verificata anche empiricamente su un gran
    numero di casi sintetici casuali prima di scrivere questo builder, zero
    divergenze — i numeri esatti nel report del task, non qui: Ruling 50.)

    Ogni coppia (u, w) di mezze giornate con `u <= w < u + param` e'
    esattamente uno dei quattro casi gia' risolti da subject_buckets.py:

        A = B,  w == u  -> post_separable(A, "half", u)
        A = B,  w != u  -> post_cross(A, "half", u,  A, "half", w)
        A != B, w == u  -> post_cross(A, "half", u,  B, "half", u)
        A != B, w != u  -> post_cross(A@u, B@w)  E  post_cross(B@u, A@w)

    ⚠ L'ultimo caso vuole **due** chiamate, non una: il checker e' simmetrico
    anche con A != B (`crossed` non guarda il verso della relazione), quindi
    sia "A a u, B a w" sia "B a u, A a w" sono coppie incrociate corte da
    vietare. Una sola chiamata coprirebbe solo un verso.

    ⚠ `post_cross` con A = B su due secchi **distinti** e' gia' l'uso che ne
    fa `TwoDaysBuilder` (Task 10, subject_buckets.py): non e' un abuso
    dell'helper, e' un caso gia' previsto.

    ⚠ `post_separable` giustifica il clamp a zero di ADR-018 dicendo che
    `count` sta dentro `Finding.key` — qui il finding di questo checker porta
    `gap`/`min_gap`, non `count`, fra le sue `quantities`. Ma la tupla
    `activities` (gli id delle due occorrenze) cresce comunque a ogni
    aggiunta libera dentro un secchio gia' violato, ed e' quella tupla a
    entrare in `Finding.key` — la stessa conclusione di `post_separable`
    regge, per la stessa ragione: un'aggiunta libera e' un finding *nuovo*,
    quindi `cap = 0` resta il valore giusto, non un eccesso di zelo."""
    TYPE = T.HALF_DAY_GAP

    def post(self, ctx, model, row, keys, rep):
        minimo = row.param
        if not minimo:
            return
        v = ctx.vocab
        n = ctx.grid.days_per_cycle * 2
        same = row.subject_a_id == row.subject_b_id
        for u in range(n):
            for w in range(u, min(u + minimo, n)):
                if same:
                    if w == u:
                        post_separable(ctx, model, v, row.subject_a_id,
                                       "half", u, keys, rep)
                    else:
                        post_cross(ctx, model, v, row.subject_a_id, "half", u,
                                   row.subject_a_id, "half", w, keys, rep)
                else:
                    post_cross(ctx, model, v, row.subject_a_id, "half", u,
                               row.subject_b_id, "half", w, keys, rep)
                    if w != u:
                        post_cross(ctx, model, v, row.subject_b_id, "half", u,
                                   row.subject_a_id, "half", w, keys, rep)
