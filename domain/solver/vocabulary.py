"""Le variabili derivate condivise dai builder: una primitiva per concetto,
costruita una volta sola e memoizzata sulla chiave completa — firma di
settimana inclusa.

Non e' un modulo di comodita'. Piu' builder hanno bisogno delle stesse
costruzioni non banali (il trittico prima/dopo/coperta serve al D.T.B. e a
MAX_PRESENCE; l'occorrenza di una materia in un secchio serve a sei vincoli di
materia). Riscriverle in ogni builder significa replicare in N posti ogni
difetto — e in questo progetto una di queste costruzioni e' gia' stata
sbagliata una volta."""


class Vocabulary:
    def __init__(self, ctx, model):
        self.ctx = ctx
        self.model = model
        self._cache = {}

    def _memo(self, kind, key, make):
        cell = (kind, key)
        if cell not in self._cache:
            self._cache[cell] = make()
        return self._cache[cell]

    def _max_or_zero(self, var, lits):
        """AddMaxEquality con lista vuota e' invalido. Una meta' giornata puo'
        essere vuota (morning_end_slot == slots_per_day), quindi il caso non e'
        teorico: capita in due test esistenti."""
        if lits:
            self.model.AddMaxEquality(var, lits)
        else:
            self.model.Add(var == 0)
        return var

    # --- griglia ---------------------------------------------------------

    def halves(self):
        """[mattina, pomeriggio]. La seconda puo' essere vuota."""
        g = self.ctx.grid
        return [range(0, g.morning_end_slot),
                range(g.morning_end_slot, g.slots_per_day)]

    def half_of(self, slot):
        return 0 if slot < self.ctx.grid.morning_end_slot else 1

    # --- occupazione -----------------------------------------------------

    def occupied(self, key, day, slot, signature=None):
        """La chiave e' occupata in quella cella.

        `signature`, se dato, e' il rappresentante di una firma di settimana:
        il letterale conta solo le attivita' attive in quella firma, come
        farebbe ScheduleState.build(schedule, week=rep) per il checker."""
        def make():
            var = self.model.NewBoolVar(f"occ_{key}_{day}_{slot}_{signature}")
            entries = self.ctx.by_cell.get((key, day, slot), ())
            if signature is not None:
                active = self.ctx.states[signature].activities
                entries = [(aid, lit) for aid, lit in entries if aid in active]
            return self._max_or_zero(var, [lit for _, lit in entries])
        return self._memo("occ", (signature, key, day, slot), make)

    def covered(self, key, day, span, signature=None):
        """{fascia: letterale} — la fascia sta fra la prima e l'ultima
        occupata **dentro `span`**.

        ⚠ `span` non e' un dettaglio: il D.T.B. lo vuole sulla mezza giornata
        (non conta mai buchi a cavallo del pranzo), MAX_PRESENCE sulla giornata
        intera (`_presence_minutes` non passa da `_halves`). Sono due cose
        diverse che si somigliano: qui la differenza e' un argomento visibile
        alla chiamata."""
        span = tuple(span)
        def make():
            occ = {s: self.occupied(key, day, s, signature) for s in span}
            out = {}
            for s in span:
                tag = f"{key}_{signature}_{day}_{span[0] if span else 'x'}_{s}"
                before = self.model.NewBoolVar(f"before_{tag}")
                self._max_or_zero(before, [occ[i] for i in span if i <= s])
                after = self.model.NewBoolVar(f"after_{tag}")
                self._max_or_zero(after, [occ[j] for j in span if j >= s])
                cov = self.model.NewBoolVar(f"covered_{tag}")
                self.model.AddMinEquality(cov, [before, after])
                out[s] = cov
            return out
        return self._memo("covered", (signature, key, day, span), make)

    # --- presenza per giornata e mezza giornata --------------------------

    def day_active(self, key, day, signature=None):
        def make():
            var = self.model.NewBoolVar(f"dayact_{key}_{signature}_{day}")
            lits = [self.occupied(key, day, s, signature)
                    for s in range(self.ctx.grid.slots_per_day)]
            return self._max_or_zero(var, lits)
        return self._memo("day_active", (signature, key, day), make)

    def half_active(self, key, day, half, signature=None):
        """`half`: 0 mattina, 1 pomeriggio."""
        def make():
            var = self.model.NewBoolVar(f"halfact_{key}_{signature}_{day}_{half}")
            lits = [self.occupied(key, day, s, signature)
                    for s in self.halves()[half]]
            return self._max_or_zero(var, lits)
        return self._memo("half_active", (signature, key, day, half), make)
