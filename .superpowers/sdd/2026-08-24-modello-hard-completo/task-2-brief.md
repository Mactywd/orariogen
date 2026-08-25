### Task 2: Il vocabolario, seconda metà — materia, posizione, sede

**Files:**
- Modify: `domain/solver/vocabulary.py`
- Test: `tests/test_solver_vocabulary.py` (aggiunge test)

**Interfaces:**
- Consumes: `Vocabulary` del Task 1.
- Produces:
  - `vocab.subject_bucket(keys, subject_id, kind, bucket, signature=None) -> BoolVar`
    — `keys` è un `frozenset` di chiavi di occupazione (l'espansione
    dell'unità, già precalcolata in `ctx.subject_rows`); `kind` è `"day"` o
    `"half"`; `bucket` è il giorno, oppure `giorno * 2 + meta`.
  - `vocab.bucket_of(kind, day, slot) -> int`
  - `vocab.pos(aid) -> IntVar` — `giorno * slots_per_day + fascia di inizio`
  - `vocab.site_occupied(key, day, slot, site_id, signature=None) -> BoolVar`

⚠ La spec §2.2 elenca `site_at` come «la sede occupata in quella cella». La
forma concreta è `site_occupied`, **un booleano per sede** invece di un intero.
I due consumatori (`MAX_SITE_CHANGES`, `structural:site_transition`)
confrontano sedi fra loro e non hanno mai bisogno del valore numerico; un
booleano si compone direttamente con gli altri letterali senza canalizzazioni
aggiuntive.

⚠ **Un'attività si attribuisce al secchio della sua fascia di partenza**, non
di tutte le fasce che occupa. È scritto in testa a
`domain/analysis/checkers/subject_constraints.py` e vale per tutti e tredici i
vincoli di materia. Un'attività di 2 fasce che inizia alle 3 con
`morning_end_slot = 4` sta **in mattinata**, per intero.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# in coda a tests/test_solver_vocabulary.py

def test_subject_bucket_usa_la_fascia_di_partenza():
    """Un'attivita' di due fasce che inizia alle 3, con la linea di meta'
    giornata a 4, appartiene alla MATTINA per intero: i vincoli di materia
    attribuiscono l'attivita' al secchio della fascia di partenza."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=2)
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 3)] == 1)
    keys = frozenset({env["klass"].pk})
    mattina = vocab.subject_bucket(keys, env["subject"].pk, "half", 0 * 2 + 0)
    pomeriggio = vocab.subject_bucket(keys, env["subject"].pk, "half", 0 * 2 + 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(mattina) == 1
    assert solver.Value(pomeriggio) == 0


def test_subject_bucket_ignora_le_altre_materie_e_le_altre_unita():
    env = mini_school()
    from domain.models import SchoolClass, Subject
    altra_materia = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    altra_classe = SchoolClass.objects.create(
        name="1B", study_plan=env["plan"], year=1)
    a = make_activity(altra_materia, teachers=[env["teacher"]], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[altra_classe])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 0)] == 1)
    giorno = vocab.subject_bucket(
        frozenset({env["klass"].pk}), env["subject"].pk, "day", 0)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(giorno) == 0


def test_pos_canalizza_giorno_e_fascia():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 2, 3)] == 1)
    p = vocab.pos(a.id)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(p) == 2 * env["grid"].slots_per_day + 3


def test_site_occupied_distingue_le_sedi():
    env = mini_school()
    from domain.models import Site
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=centrale)
    ctx, model, vocab = _vocab(env)
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    key = env["klass"].pk
    qui = vocab.site_occupied(key, 0, 0, centrale.pk)
    altrove = vocab.site_occupied(key, 0, 0, succursale.pk)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.Value(qui) == 1
    assert solver.Value(altrove) == 0
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_vocabulary.py -v -k "subject_bucket or pos or site_occupied"`
Expected: FAIL con `AttributeError: 'Vocabulary' object has no attribute 'subject_bucket'`

- [ ] **Step 3: Aggiungere le primitive a `domain/solver/vocabulary.py`**

```python
    # --- materia in un secchio -------------------------------------------

    def bucket_of(self, kind, day, slot):
        """Il secchio di una collocazione. ⚠ Si usa la fascia di **partenza**
        dell'attivita', non tutte quelle che occupa: e' la regola dichiarata
        in testa a domain/analysis/checkers/subject_constraints.py."""
        return day if kind == "day" else day * 2 + self.half_of(slot)

    def subject_bucket(self, keys, subject_id, kind, bucket, signature=None):
        """La materia `subject_id` occorre in quel secchio, sull'unita' `keys`.
        `keys` e' l'espansione dell'unita' della riga di vincolo, gia'
        precalcolata in ctx.subject_rows."""
        keys = frozenset(keys)
        def make():
            var = self.model.NewBoolVar(
                f"subj_{subject_id}_{kind}_{bucket}_{signature}_{id(keys)}")
            active = (None if signature is None
                      else self.ctx.states[signature].activities)
            lits = []
            for aid, act in self.ctx.activities.items():
                if act.subject_id != subject_id:
                    continue
                if not (self.ctx.tokens[aid] & keys):
                    continue
                if active is not None and aid not in active:
                    continue
                for (day, slot) in self.ctx.cells[aid]:
                    if self.bucket_of(kind, day, slot) == bucket:
                        lits.append(self.ctx.x[(aid, day, slot)])
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
        """giorno * slots_per_day + fascia di inizio, canalizzato da x."""
        def make():
            cells = sorted(self.ctx.cells[aid])
            width = self.ctx.grid.slots_per_day
            if not cells:
                # dominio vuoto: build_model ha gia' reso il modello
                # infattibile in modo esplicito, qui basta non rompere
                return self.model.NewIntVar(0, 0, f"pos_{aid}")
            values = [day * width + slot for (day, slot) in cells]
            var = self.model.NewIntVar(min(values), max(values), f"pos_{aid}")
            self.model.Add(var == sum(
                (day * width + slot) * self.ctx.x[(aid, day, slot)]
                for (day, slot) in cells))
            return var
        return self._memo("pos", aid, make)

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
```

⚠ Nel nome della variabile di `subject_bucket` compare `id(keys)`: serve solo
a rendere il nome leggibile e univoco nel dump del modello, **non** fa parte
della chiave di memoizzazione, che è il `frozenset` stesso.

- [ ] **Step 4: Eseguire i test nuovi e la suite intera**

Run: `venv/bin/pytest tests/test_solver_vocabulary.py -v`
Expected: PASS (8 test)

Run: `venv/bin/pytest -q`
Expected: **181 passed**

- [ ] **Step 5: Commit**

```bash
git add domain/solver/vocabulary.py tests/test_solver_vocabulary.py
git commit -m "$(cat <<'EOF'
feat(solver): il vocabolario, seconda meta'

subject_bucket (con la regola della fascia di partenza), subject_activities,
pos e site_occupied. Nessun builder le usa ancora: le ondate 3-6 le
consumano.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

