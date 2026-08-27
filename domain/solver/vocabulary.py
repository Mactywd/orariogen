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
        farebbe ScheduleState.build(schedule, week=rep) per il checker.

        Omesso (`None`), conta tutte le attivita' che toccano la cella
        indipendentemente dalla settimana. Per un vincolo di **cardinalita'
        sulla singola cella** questo e' conservativo: piu' letterali vuol dire
        un vincolo piu' stretto, mai piu' lasco. Non e' piu' vero appena questo
        letterale entra in un aggregato per risorsa — vedi `covered`,
        `day_active`, `half_active`."""
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
        alla chiamata.

        ⚠ `signature` va passato quando il chiamante distingue le settimane:
        qui, a differenza di `occupied` da sola, ometterlo **non** e'
        conservativo. Un'occupazione che cade dentro il buco ma viene da
        un'attivita' di un'**altra** firma alza il conteggio senza spostare
        prima/ultima occupata — chiude nel modello unione un buco che,
        settimana per settimana, resta aperto. E' esattamente il difetto che
        MaxGapBuilder aveva prima della correzione del 2026-08-24 (vedi
        CLAUDE.md, changelog di quella data)."""
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
        """Vero se la chiave e' occupata in almeno una fascia della giornata.

        ⚠ Stesso avvertimento di `covered`: e' un aggregato per risorsa, non
        una singola cella. Omettere la firma non e' conservativo — un'attivita'
        di un'altra firma di settimana puo' far risultare 'attiva' una
        giornata che, per quella firma, non lo e'."""
        def make():
            var = self.model.NewBoolVar(f"dayact_{key}_{signature}_{day}")
            lits = [self.occupied(key, day, s, signature)
                    for s in range(self.ctx.grid.slots_per_day)]
            return self._max_or_zero(var, lits)
        return self._memo("day_active", (signature, key, day), make)

    def half_active(self, key, day, half, signature=None):
        """`half`: 0 mattina, 1 pomeriggio.

        ⚠ Stesso avvertimento di `covered` e `day_active`: e' un aggregato
        per risorsa. Omettere la firma non e' conservativo, per lo stesso
        motivo."""
        def make():
            var = self.model.NewBoolVar(f"halfact_{key}_{signature}_{day}_{half}")
            lits = [self.occupied(key, day, s, signature)
                    for s in self.halves()[half]]
            return self._max_or_zero(var, lits)
        return self._memo("half_active", (signature, key, day, half), make)

    # --- materia in un secchio -------------------------------------------

    def bucket_of(self, kind, day, slot):
        """Il secchio di una collocazione. ⚠ Si usa la fascia di **partenza**
        dell'attivita', non tutte quelle che occupa: e' la regola dichiarata
        in testa a domain/analysis/checkers/subject_constraints.py."""
        return day if kind == "day" else day * 2 + self.half_of(slot)

    def subject_literals(self, keys, subject_id, kind, bucket, signature=None):
        """[(id attivita', letterale)] delle collocazioni di quella materia in
        quel secchio, sull'unita' `keys`. Base comune di `subject_bucket`
        (l'indicatore aggregato) e dei builder che devono distinguere le
        attivita' **congelate** da quelle **libere** dentro un secchio, per
        ADR-018 — l'aggregato da solo non lo permette."""
        keys = frozenset(keys)
        def make():
            active = (None if signature is None
                      else self.ctx.states[signature].activities)
            out = []
            for aid, act in self.ctx.activities.items():
                if act.subject_id != subject_id:
                    continue
                if not (self.ctx.tokens[aid] & keys):
                    continue
                if active is not None and aid not in active:
                    continue
                for (day, slot) in sorted(self.ctx.cells[aid]):
                    if self.bucket_of(kind, day, slot) == bucket:
                        out.append((aid, self.ctx.x[(aid, day, slot)]))
            return out
        return self._memo("subject_literals",
                          (signature, keys, subject_id, kind, bucket), make)

    def subject_bucket(self, keys, subject_id, kind, bucket, signature=None):
        """La materia `subject_id` occorre in quel secchio, sull'unita' `keys`.
        `keys` e' l'espansione dell'unita' della riga di vincolo, gia'
        precalcolata in ctx.subject_rows."""
        keys = frozenset(keys)
        def make():
            var = self.model.NewBoolVar(
                f"subj_{subject_id}_{kind}_{bucket}_{signature}_{id(keys)}")
            lits = [lit for _, lit in
                    self.subject_literals(keys, subject_id, kind, bucket, signature)]
            return self._max_or_zero(var, lits)
        return self._memo("subj", (signature, keys, subject_id, kind, bucket), make)

    def subject_activities(self, keys, subject_id, signature=None):
        """Gli id delle attivita' di quella materia su quell'unita'. Serve ai
        builder per la regola dell'implicazione di ADR-018 (`any_free`) e per
        sapere staticamente se una materia e' assente."""
        keys = frozenset(keys)
        active = (None if signature is None
                  else self.ctx.states[signature].activities)
        return sorted(
            aid for aid, act in self.ctx.activities.items()
            if act.subject_id == subject_id
            and self.ctx.tokens[aid] & keys
            and (active is None or aid in active))

    # --- posizione e sede -------------------------------------------------

    def pos(self, aid):
        """giorno * slots_per_day + fascia di inizio, canalizzato da x.

        ⚠ La canalizzazione `var == somma(posizione * x)` vale **solo** finche'
        esattamente un letterale e' a 1. Da quando il modello ammette lo scarto
        (spec pezzo 3, §2.1) non e' piu' garantito: un'attivita' scartata ha
        tutti i letterali a zero, e la somma varrebbe zero — cioe' «giorno 0,
        fascia 0», che e' una posizione **vera** e la piu' precoce di tutte.
        Un builder d'ordine crederebbe che la scartata preceda tutto; e dove il
        dominio non contiene quella cella il modello diventerebbe infattibile
        proprio quando lo scarto e' la via d'uscita.

        Quindi la scartata vale `fuori` — una posizione oltre l'ultima della
        griglia, che ordina **dopo** ogni collocazione reale. E' il verso
        giusto: i checker d'ordine leggono le sole occorrenze piazzate
        (`_placed_of`), quindi una scartata non deve mai *anticipare* nulla.
        ⚠ Non basta da solo: un lato interamente scartato va escluso dal
        vincolo, e quello lo fa il builder (`subject_order.py`)."""
        def make():
            cells = sorted(self.ctx.cells[aid])
            width = self.ctx.grid.slots_per_day
            fuori = self.ctx.grid.days_per_cycle * width
            if not cells:
                # dominio vuoto: nessuna cella sopravvive ai pre-filtri, quindi
                # l'attivita' e' scartata per costruzione.
                return self.model.NewIntVar(fuori, fuori, f"pos_{aid}")
            values = [day * width + slot for (day, slot) in cells]
            canale = sum((day * width + slot) * self.ctx.x[(aid, day, slot)]
                         for (day, slot) in cells)
            piazzata = self.ctx.placed_var.get(aid)
            if piazzata is None:
                # congelata: piazzata per costruzione, la somma vale sempre 1.
                var = self.model.NewIntVar(min(values), max(values), f"pos_{aid}")
                self.model.Add(var == canale)
                return var
            var = self.model.NewIntVar(min(values), fuori, f"pos_{aid}")
            self.model.Add(var == canale).OnlyEnforceIf(piazzata)
            self.model.Add(var == fuori).OnlyEnforceIf(piazzata.Not())
            return var
        return self._memo("pos", aid, make)

    def qualcuna_piazzata(self, aids):
        """Letterale «almeno una di queste attivita' e' piazzata», o `None` se
        la risposta e' sempre si' (c'e' almeno una congelata fra loro).

        Serve ai vincoli che i checker valutano **sulle sole occorrenze
        piazzate** e dichiarano vacui quando non ce ne sono
        (`if not a or not b: return`, WeeklyOrderChecker)."""
        aids = tuple(sorted(aids))
        def make():
            lits = [self.ctx.placed_var[aid] for aid in aids
                    if aid in self.ctx.placed_var]
            if len(lits) < len(aids):
                return None
            if not lits:
                return None
            # ⚠ Il nome porta gli id, non un `hash(aids) & 0xffff`: troncato a
            # sedici bit collide, e due guardie diverse finivano con lo stesso
            # nome nel proto — innocuo per CP-SAT, illeggibile per chi lo apre.
            var = self.model.NewBoolVar(
                "qualcuna_" + "_".join(str(a) for a in aids))
            return self._max_or_zero(var, lits)
        return self._memo("qualcuna", aids, make)

    def site_occupied(self, key, day, slot, site_id, signature=None):
        """Un'attivita' di sede `site_id` occupa quella cella."""
        def make():
            var = self.model.NewBoolVar(
                f"site_{site_id}_{key}_{day}_{slot}_{signature}")
            active = (None if signature is None
                      else self.ctx.states[signature].activities)
            lits = [lit for aid, lit in self.ctx.by_cell.get((key, day, slot), ())
                    if self.ctx.activities[aid].site_id == site_id
                    and (active is None or aid in active)]
            return self._max_or_zero(var, lits)
        return self._memo("site", (signature, key, day, slot, site_id), make)
