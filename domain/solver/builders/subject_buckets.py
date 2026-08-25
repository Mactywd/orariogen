"""I vincoli di materia che si esprimono come cardinalita' su un **secchio**
(giornata o mezza giornata), piu' FORBIDDEN_SEQUENCE, che non usa secchi ma
vive nello stesso file perche' e' lo stesso asse di vincolo (SubjectBuilder).
L'attivita' si attribuisce al secchio della sua fascia di **partenza**, come
nei checker (`domain/analysis/checkers/subject_constraints.py`).

ADR-018 — un secchio (o una coppia di celle, per FORBIDDEN_SEQUENCE) gia'
violato da attivita' **congelate** non deve rendere il modello INFEASIBLE per
colpa del passato. Sui tetti di cardinalita' con A = B il residuo e'
separabile (ogni letterale pesa allo stesso modo — 1 per l'incompatibilita',
i minuti di durata per il tetto di ore): `residual_cap` clampa il tetto a
zero. Con A != B — e per TWO_DAYS, sempre, anche con A = B — il residuo
dell'incompatibilita' non e' separabile: `ha`/`hb` sono indicatori derivati
(un massimo, non una somma), e serve la tabella a quattro rami di
`post_cross` sotto. Il tetto di ore (`_MaxHoursSubject`) resta invece
separabile anche con A != B, perche' somma solo i minuti di A."""

from domain.models import SubjectConstraint
from domain.solver.builders.base import SubjectBuilder
from domain.solver.registry import register
from domain.solver.residual import any_free, residual_cap

T = SubjectConstraint.Type


def post_separable(ctx, model, v, subject_id, kind, bucket, keys, rep):
    """A = B: «al piu' un'occorrenza per secchio». Separabile, quindi
    `residual_cap` e' esatto: il tetto residuo e' `1 - (occorrenze congelate
    in questo secchio)`, clampato a zero quando le congelate lo hanno gia'
    sforato — invece di lasciare il modello infattibile per colpa del passato
    (ADR-018). Il checker emette il finding con `count=len(la)` fra le
    `quantities`, dentro `Finding.key`: un'aggiunta libera a un secchio gia'
    violato e' un finding *nuovo*, quindi `cap = 0` e' il valore giusto, non
    un eccesso di zelo."""
    termini = [(1, aid, lit) for aid, lit in
               v.subject_literals(keys, subject_id, kind, bucket, signature=rep)]
    free, cap = residual_cap(ctx, termini, 1)
    if not free:
        return
    # ⚠ residual_cap/split restituiscono (peso, letterale): l'id attivita' non
    # sopravvive alla separazione. Le attivita' libere distinte si contano
    # dai `termini` originali (dove l'id c'e' ancora), filtrati a ctx.free —
    # non da `free`, dove `aid` leggerebbe in realta' il peso (sempre 1: un
    # set a un solo elemento per costruzione, indipendentemente dal caso).
    distinte = {aid for _, aid, _ in termini if aid in ctx.free}
    if cap >= 1 and len(distinte) <= 1:
        # Implicato da AddExactlyOne: si contano le attivita' distinte, non i
        # letterali, perche' una sola attivita' puo' contribuire piu'
        # letterali allo stesso secchio (piu' celle candidate li'), ma la sua
        # somma sulle proprie celle resta comunque <= 1.
        return
    model.Add(sum(lit for _, lit in free) <= cap)


def post_cross(ctx, model, v, subject_a_id, kind_a, bucket_a,
                subject_b_id, kind_b, bucket_b, keys, rep):
    """A != B (e TWO_DAYS, sempre — anche con A = B, perche' li' i due secchi
    sono distinti: giorno d per A, giorno d+1 per B). Il residuo qui non e'
    separabile — `ha`/`hb` sono `AddMaxEquality`, non somme — quindi la regola
    meccanica `max(0, 1 - fa - fb)` sarebbe **troppo stretta**: il checker
    emette il finding solo `if la and lb` (righe 93-94 di
    subject_constraints.py), quindi occorrenze libere di A in un secchio dove
    B e' assente non creano e non peggiorano nulla.

    Siano `fa`/`fb` due costanti note a build time — «una attivita'
    **congelata** di A (risp. B) abita gia' quel secchio» — calcolate
    guardando `aid not in ctx.free` sui letterali di `subject_literals`.
    Quattro rami:

        fa=0, fb=0 -> ha + hb <= 1        (nessuna congelata: gli indicatori
                                            pieni coincidono con quelli sulle
                                            sole libere)
        fa=1, fb=0 -> hb == 0             (le libere di A restano libere)
        fa=0, fb=1 -> ha == 0
        fa=1, fb=1 -> si azzerano uno per uno i letterali **liberi** di A e di
                      B in quel secchio — non `ha`/`hb`: sono gia' forzati a 1
                      dalla congelata (AddMaxEquality), e forzarli a 0
                      sarebbe un conflitto immediato, sempre INFEASIBLE.

    Il quarto ramo serve perche' il secchio e' *gia'* violato, e ogni aggiunta
    libera ingrossa la tupla `activities` che sta dentro `Finding.key`.

    ⚠ Il quarto ramo **puo'** rendere il modello infattibile se una libera non
    ha altro posto dove andare. E' voluto: e' la stessa proprieta' del clamp a
    zero di `residual_cap`, ed e' testualmente cio' che ADR-018 concede.

    Guardia `if not la or not lb: return`: e' un'ottimizzazione, ma la sua
    giustificazione e' l'**esattezza**, non il risparmio. Il checker emette il
    finding solo `if la and lb` (subject_constraints.py, righe 93-94): con un
    lato vuoto non puo' mai emettere nulla, quindi tutti e quattro i rami sono
    vacui — postarli sarebbe un vincolo vero ma inutile. Il risparmio misurato
    e' consistente sul banco (ordine del 10-15% di variabili e constraint al
    seed peggiore) e **zero sul Fermi**, che non crea alcun SubjectConstraint;
    i numeri esatti stanno nel registro (ri-review Task 10) e non qui, perche'
    in docstring invecchierebbero in silenzio (Ruling 50). ⚠ Sul banco il
    risparmio e' tutto di TWO_DAYS: le righe con A = B passano da
    `post_separable`, che questa guardia non attraversa."""
    la = v.subject_literals(keys, subject_a_id, kind_a, bucket_a, signature=rep)
    lb = v.subject_literals(keys, subject_b_id, kind_b, bucket_b, signature=rep)
    if not la or not lb:
        return
    fa = any(aid not in ctx.free for aid, _ in la)
    fb = any(aid not in ctx.free for aid, _ in lb)
    if not fa and not fb:
        ha = v.subject_bucket(keys, subject_a_id, kind_a, bucket_a, signature=rep)
        hb = v.subject_bucket(keys, subject_b_id, kind_b, bucket_b, signature=rep)
        model.Add(ha + hb <= 1)
    elif fa and not fb:
        hb = v.subject_bucket(keys, subject_b_id, kind_b, bucket_b, signature=rep)
        model.Add(hb == 0)
    elif fb and not fa:
        ha = v.subject_bucket(keys, subject_a_id, kind_a, bucket_a, signature=rep)
        model.Add(ha == 0)
    else:
        for aid, lit in la:
            if aid in ctx.free:
                model.Add(lit == 0)
        for aid, lit in lb:
            if aid in ctx.free:
                model.Add(lit == 0)


class _Bucketed(SubjectBuilder):
    """Base comune a `_BucketIncompatible` e `_MaxHoursSubject` (Ruling 58):
    entrambe hanno bisogno degli stessi tre elementi — `KIND`, `buckets(ctx)`
    e l'assert su `KIND` — e prima di questa estrazione ognuna li duplicava
    per conto proprio.

    L'assert esiste perche' `vocab.bucket_of` tratta **ogni** `kind != "day"`
    come mezza giornata: senza, una sottoclasse che dimentichi `KIND`
    prenderebbe silenziosamente la semantica "half" invece di rompersi. Vive
    dentro `buckets()` (Ruling 67, non in un metodo `_check_kind()` a parte
    che ogni `post()` dovrebbe ricordarsi di chiamare): `buckets()` e' cio'
    che ogni `post()` di questa base **deve** invocare per funzionare, quindi
    l'assert e' inevitabile invece che opt-in."""

    KIND = None   # "day" | "half"

    def buckets(self, ctx):
        assert self.KIND in ("day", "half"), type(self).__name__
        n = ctx.grid.days_per_cycle
        return range(n) if self.KIND == "day" else range(n * 2)


class _BucketIncompatible(_Bucketed):
    """Con A = B (il caso dominante nei dati reali di EDT: non due ore della
    stessa materia nello stesso giorno) e' «al piu' un'occorrenza per
    secchio», via `post_separable`. Con A != B e' «le due materie non
    coesistono nel secchio», via `post_cross` (tabella a quattro rami di
    ADR-018)."""

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        for bucket in self.buckets(ctx):
            if row.subject_a_id == row.subject_b_id:
                post_separable(ctx, model, v, row.subject_a_id, self.KIND,
                                bucket, keys, rep)
            else:
                post_cross(ctx, model, v, row.subject_a_id, self.KIND, bucket,
                           row.subject_b_id, self.KIND, bucket, keys, rep)


@register(T.SAME_DAY_INCOMPATIBLE)
class SameDayBuilder(_BucketIncompatible):
    TYPE, KIND = T.SAME_DAY_INCOMPATIBLE, "day"


@register(T.SAME_HALF_DAY_INCOMPATIBLE)
class SameHalfDayBuilder(_BucketIncompatible):
    TYPE, KIND = T.SAME_HALF_DAY_INCOMPATIBLE, "half"


@register(T.TWO_DAYS_INCOMPATIBLE)
class TwoDaysBuilder(SubjectBuilder):
    """A nel giorno d e B nel giorno d+1 non coesistono. Stessa tabella a
    quattro rami di `post_cross`, applicata su due secchi **distinti** (il
    giorno d per A, il giorno d+1 per B) — vale anche con A = B, perche' il
    checker confronta `a_days[d]` con `b_days[d+1]`, due letture dello stesso
    insieme su giorni diversi: non e' il caso `_BucketIncompatible` A = B, che
    e' un secchio solo.

    ⚠ Il checker richiede `len(set(acts)) > 1` per emettere il finding: serve
    a non segnalare una singola attivita' contro se' stessa. Qui e' automatico
    perche' un'attivita' non puo' stare in due giorni contemporaneamente."""
    TYPE = T.TWO_DAYS_INCOMPATIBLE

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        for day in range(ctx.grid.days_per_cycle - 1):
            post_cross(ctx, model, v, row.subject_a_id, "day", day,
                       row.subject_b_id, "day", day + 1, keys, rep)


class _MaxHoursSubject(_Bucketed):
    """Tetto di minuti per secchio, sulla **sola** materia A — anche quando
    A != B: `_MaxHours.violations` (domain/analysis/checkers/
    subject_constraints.py, righe 149-159) itera su `a` e non tocca mai `b`.
    Sommare anche B sarebbe un vincolo diverso e piu' stretto di quanto la
    riga chieda.

    Separabile come `post_separable` (ogni letterale pesa i propri minuti,
    la somma e' lineare): `residual_cap` clampa il tetto residuo a zero
    quando le congelate lo hanno gia' sforato, invece di rendere il modello
    infattibile per colpa del passato (ADR-018).

    ⚠ Con A != B il gate di `SubjectBuilder.build` e la deduplicazione per
    `coinvolte` guardano l'unione delle attivita' di A **e** B (Ruling 60),
    ma questo vincolo dipende solo da A: l'effetto e' al piu' una riga
    postata due volte in modo identico (due firme con lo stesso `coinvolte`
    ma B che le distingue), mai una firma saltata — la deduplicazione lo
    assorbe comunque."""

    def post(self, ctx, model, row, keys, rep):
        # `buckets()` per prima, non dopo il `return`: e' li' che vive
        # l'assert su KIND (Ruling 67), e con `param` nullo non scatterebbe
        # mai — la rete di sicurezza deve valere anche sulle righe che non
        # postano nulla (Minor 3, ri-review Task 11).
        secchi = self.buckets(ctx)
        if row.param is None:
            return
        for bucket in secchi:
            lits = ctx.vocab.subject_literals(keys, row.subject_a_id, self.KIND,
                                              bucket, signature=rep)
            terms = [(ctx.activities[aid].duration_minutes, aid, lit)
                     for aid, lit in lits]
            liberi, residuo = residual_cap(ctx, terms, row.param)
            if liberi:
                model.Add(sum(w * lit for w, lit in liberi) <= residuo)


@register(T.MAX_HOURS_DAY)
class MaxHoursDayBuilder(_MaxHoursSubject):
    TYPE, KIND = T.MAX_HOURS_DAY, "day"


@register(T.MAX_HOURS_HALF_DAY)
class MaxHoursHalfDayBuilder(_MaxHoursSubject):
    TYPE, KIND = T.MAX_HOURS_HALF_DAY, "half"


@register(T.FORBIDDEN_SEQUENCE)
class ForbiddenSequenceBuilder(SubjectBuilder):
    """B non puo' iniziare esattamente dove A finisce, nello stesso giorno
    (`ForbiddenSequenceChecker.violations`, subject_constraints.py righe
    135-142). Proibizione di coppie di celle: per ogni cella ammissibile
    `(day, slot)` di un'attivita' di A la cui fine `(day, slot + durata)` e'
    anche una cella ammissibile di un'attivita' di B, si vieta che le due
    valgano insieme. Nessuna variabile derivata serve.

    Il `continue` con `pa` e `pb` **entrambe congelate** e' `any_free`: «un
    fatto, non una decisione» — e' diverso dal `continue` su un **tetto** che
    le Rulings 14/23/28 vietano (li' saltare perderebbe il clamp a zero di
    `residual_cap`). Qui non c'e' alcun tetto: e' una clausola fra due
    letterali, e con entrambi gia' fissati dal passato non c'e' nulla da
    decidere — il piazzamento congelato o rispetta gia' il vincolo o non lo
    rispetta, e non e' compito di questo `post()` giudicarlo.

    Con **una sola** congelata la clausola resta e forza a zero il
    letterale libero corrispondente a quella cella — cio' che impedisce la
    sequenza. ⚠ Questo **puo' rendere il modello INFEASIBLE** se la libera
    non ha altro posto dove andare: e' testualmente cio' che ADR-018 concede
    (esibito in tests/test_solver_subject_maxhours.py,
    test_adr018_forbidden_sequence_una_congelata_forza_infattibile)."""
    TYPE = T.FORBIDDEN_SEQUENCE

    def post(self, ctx, model, row, keys, rep):
        v = ctx.vocab
        a = v.subject_activities(keys, row.subject_a_id, signature=rep)
        b = v.subject_activities(keys, row.subject_b_id, signature=rep)
        for pa in a:
            durata = ctx.activities[pa].duration_slots
            for pb in b:
                if pb == pa:
                    continue
                if not any_free(ctx, (pa, pb)):
                    continue   # un fatto, non una decisione
                for (day, slot) in sorted(ctx.cells[pa]):
                    fine = slot + durata
                    if (day, fine) not in ctx.cells[pb]:
                        continue
                    model.AddBoolOr([ctx.x[(pa, day, slot)].Not(),
                                     ctx.x[(pb, day, fine)].Not()])
