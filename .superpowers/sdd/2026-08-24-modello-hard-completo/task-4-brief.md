### Task 4: Lo spostamento dei due builder nei file del proprio pattern

**Files:**
- Create: `domain/solver/builders/time_presence.py` (accoglie `MaxGapBuilder`)
- Create: `domain/solver/builders/subject_buckets.py` (accoglie `SameDayBuilder`)
- Delete: `domain/solver/builders/time_constraints.py`
- Delete: `domain/solver/builders/subject_constraints.py`
- Modify: `domain/solver/builders/__init__.py`
- Modify: `tests/test_solver_max_gap.py`, `tests/test_solver_same_day.py` (solo
  gli import, se importano il modulo invece del registro)

**Interfaces:**
- Consumes: niente di nuovo.
- Produces: `MaxGapBuilder` importabile da
  `domain.solver.builders.time_presence`; `SameDayBuilder` da
  `domain.solver.builders.subject_buckets`. **Le chiavi del registro non
  cambiano** (`T.MAX_GAP_HOURS`, `T.SAME_DAY_INCOMPATIBLE`).

- [ ] **Step 1: Verificare da dove i test importano**

Run: `grep -rn "time_constraints\|subject_constraints" tests/ domain/solver/`

Se i test raggiungono i builder solo attraverso `all_builders()` o `solve()`,
non c'è nulla da modificare nei test: è lo scenario atteso.

- [ ] **Step 2: Spostare i file**

```bash
git mv domain/solver/builders/time_constraints.py domain/solver/builders/time_presence.py
git mv domain/solver/builders/subject_constraints.py domain/solver/builders/subject_buckets.py
```

- [ ] **Step 3: Aggiornare i docstring di modulo**

In `time_presence.py`, premettere al docstring esistente:

```python
"""Presenza e buchi: i vincoli che ragionano sulla **prima e sull'ultima**
fascia occupata, e non sul semplice conteggio. Entrambi passano da
`vocab.covered`, con `span` diverso — mezza giornata per il D.T.B., giornata
intera per MAX_PRESENCE.
"""
```

In `subject_buckets.py`:

```python
"""I vincoli di materia che si esprimono come cardinalita' su un **secchio**
(giornata o mezza giornata). L'attivita' si attribuisce al secchio della sua
fascia di **partenza**.
"""
```

- [ ] **Step 4: Verificare che `builders/__init__.py` importi i moduli nuovi**

`all_builders()` fa `from domain.solver import builders` per forzare la
registrazione. Controllare `domain/solver/builders/__init__.py` e sostituire i
due nomi vecchi con quelli nuovi.

- [ ] **Step 5: Eseguire la suite**

Run: `venv/bin/pytest -q`
Expected: **186 passed** — identico al Task 3. Uno spostamento che cambia il
numero di test verdi non è uno spostamento.

- [ ] **Step 6: Commit**

```bash
git add -A domain/solver/builders tests/
git commit -m "$(cat <<'EOF'
refactor(solver): i builder nel file del proprio pattern

time_constraints.py -> time_presence.py, subject_constraints.py ->
subject_buckets.py. Le chiavi del registro non cambiano. Prepara le ondate
3-6, dove quei file accolgono altri undici builder.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Ondata 2 — Il banco di prova

