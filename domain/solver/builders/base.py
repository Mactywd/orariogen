"""Lo scheletro condiviso dai builder che vincolano **una risorsa** riga per
riga: il ciclo sulle firme di settimana e la deduplicazione.

Le firme non sono un dettaglio da ricordarsi: un vincolo che aggrega su una
risorsa lungo la settimana **deve** essere postato per firma, con i letterali
filtrati alle sole attivita' attive in quella firma. Trattare tutto come
co-attivo puo' vincolare *di meno*, non di piu' — e' il difetto trovato sul
D.T.B. il 2026-08-24. Qui la regola e' nella classe base, cosi' nessun builder
deve ricordarsene."""

from domain.solver.registry import Builder


class ResourceBuilder(Builder):
    TYPE = None

    def build(self, ctx, model):
        # Rete di sicurezza: una sottoclasse che eredita build() supera
        # sempre test_ogni_builder_implementa_almeno_un_hook (l'eredita'),
        # quindi dimenticare TYPE la renderebbe silenziosamente vacua — non
        # fa mai match con nessuna riga, e nessun test se ne accorgerebbe
        # (review Task 6, requisito del controller).
        assert self.TYPE is not None, type(self).__name__
        for row in ctx.time_rows:
            if row.type != self.TYPE:
                continue
            posted = set()
            for rep, _ in ctx.signatures:
                active = ctx.states[rep].activities
                touching = frozenset(
                    aid
                    for day in range(ctx.grid.days_per_cycle)
                    for slot in range(ctx.grid.slots_per_day)
                    for aid, _ in ctx.by_cell.get((row.resource_id, day, slot), ())
                    if aid in active
                )
                if not any(aid in ctx.free for aid in touching):
                    continue   # un fatto, non una decisione
                if touching in posted:
                    continue   # firma diversa, stesse attivita' attive
                posted.add(touching)
                self.post(ctx, model, row, rep)

    def post(self, ctx, model, row, rep):
        raise NotImplementedError


class SubjectBuilder(Builder):
    """Lo scheletro dei vincoli sull'asse Relazione (SubjectConstraint): una
    riga per volta, una firma di settimana per volta, con deduplicazione
    sull'insieme delle attivita' coinvolte — gemello di `ResourceBuilder`.

    Iterare per firma qui non e' strettamente necessario per i vincoli che
    vietano (piu' letterali = piu' stretto), ma lo e' per quelli d'ordine, dove
    fondere le settimane puo' spostare la *prima* occorrenza e rendere il
    vincolo piu' largo. Una regola sola per tutta la famiglia costa meno che
    ricordarsi caso per caso quale delle due si applica — ed e' esattamente il
    tipo di distinzione che in questo progetto e' gia' stato sbagliato.

    Il gate qui sotto («c'e' qualcosa di libero fra le attivita' coinvolte?»)
    e' un **corto circuito**, non l'invariante che difende ADR-018: risponde
    solo a «serve postare qualcosa per questa riga e questa firma?», a
    livello di **riga** intera. Il trattamento di ADR-018 (capacita' residua
    clampata a zero, o la tabella a quattro rami quando il residuo non e'
    separabile) e' compito di ciascun `post()`, sul **singolo secchio** — un
    livello piu' fine, dove "riga coinvolta con qualcosa di libero" non
    implica affatto "questo secchio ha qualcosa di libero".

    Il gate e' verificato semanticamente neutro (review Task 10, Minor 3):
    rimosso, la suite intera resta verde — ogni `post()` di questo branch e'
    gia' un no-op quando non c'e' nulla di libero nel proprio secchio (il
    `if not free: return` di `_post_separable`, il ramo `fa=0, fb=0` di
    `_post_cross` con nessun letterale, eccetera). Si tiene solo perche' fa
    risparmiare il giro sulle firme e sui secchi quando la riga intera non ha
    nulla da decidere — un'ottimizzazione, non una garanzia di correttezza."""

    TYPE = None

    def build(self, ctx, model):
        # Stessa rete di sicurezza di ResourceBuilder.build (review Task 6):
        # una sottoclasse senza TYPE erediterebbe build() e sarebbe
        # silenziosamente vacua, senza che nessun test se ne accorga.
        assert self.TYPE is not None, type(self).__name__
        for row, keys in ctx.subject_rows:
            if row.type != self.TYPE:
                continue
            posted = set()
            for rep, _ in ctx.signatures:
                v = ctx.vocab
                coinvolte = frozenset(
                    v.subject_activities(keys, row.subject_a_id, signature=rep)
                    + v.subject_activities(keys, row.subject_b_id, signature=rep))
                if not any(aid in ctx.free for aid in coinvolte):
                    continue   # un fatto, non una decisione
                if coinvolte in posted:
                    continue   # firma diversa, stesse attivita' coinvolte
                posted.add(coinvolte)
                self.post(ctx, model, row, keys, rep)

    def post(self, ctx, model, row, keys, rep):
        raise NotImplementedError
