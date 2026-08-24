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
