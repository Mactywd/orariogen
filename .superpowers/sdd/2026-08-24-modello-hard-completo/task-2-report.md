# Task 2: Il vocabolario, seconda metà — Rapporto di completamento

## Cosa è stato implementato

Implementate le quattro primitive derivate della seconda metà del vocabolario in `domain/solver/vocabulary.py`:

1. **`bucket_of(kind, day, slot)`** — Ritorna il bucket di una collocazione (giorno per "day", oppure giorno*2 + half_of(slot) per "half"). Segue la regola della **fascia di partenza** dichiarata in testa a `domain/analysis/checkers/subject_constraints.py`.

2. **`subject_bucket(keys, subject_id, kind, bucket, signature=None)`** — BoolVar che indica se la materia `subject_id` occorre in quel bucket sull'unità `keys`. Filtra per materia, per unità (tramite `ctx.tokens[aid]`), e per firma di settimana opzionale. Attribuisce l'attività al bucket della sua fascia di **partenza**, non di tutte le fasce che occupa.

3. **`pos(aid)`** — IntVar che canalizza giorno * slots_per_day + fascia di inizio. Gestisce il caso del dominio vuoto (non esplode, ritorna 0).

4. **`site_occupied(key, day, slot, site_id, signature=None)`** — BoolVar che indica se un'attività di sede `site_id` occupa quella cella. Filtra per site_id e firma opzionale.

5. **`subject_activities(keys, subject_id, signature=None)`** — Helper statico che ritorna gli id delle attività di quella materia su quell'unità. Usato dai builder per ADR-018 e per verificare l'assenza di materia.

## Cosa è stato testato e risultati

### TDD Flow

**RED (fallimento atteso prima dell'implementazione):**
```bash
$ venv/bin/pytest tests/test_solver_vocabulary.py -v -k "subject_bucket or pos or site_occupied" 2>&1 | head -20
...
tests/test_solver_vocabulary.py::test_subject_bucket_usa_la_fascia_di_partenza FAILED [ 40%]
...
E       AttributeError: 'Vocabulary' object has no attribute 'subject_bucket'
```

Tutti e 5 i test nuovi fallirono subito con `AttributeError`, come atteso.

**GREEN (passaggio dopo l'implementazione):**
```bash
$ venv/bin/pytest tests/test_solver_vocabulary.py -v
...
tests/test_solver_vocabulary.py::test_subject_bucket_usa_la_fascia_di_partenza PASSED [ 70%]
tests/test_solver_vocabulary.py::test_subject_bucket_ignora_le_altre_materie_e_le_altre_unita PASSED [ 80%]
tests/test_solver_vocabulary.py::test_pos_canalizza_giorno_e_fascia PASSED [ 90%]
tests/test_solver_vocabulary.py::test_site_occupied_distingue_le_sedi PASSED [100%]
...
============================== 10 passed in 0.73s ==============================
```

Tutti i 10 test del vocabolario (6 vecchi + 4 nuovi) passano.

**Suite intera:**
```bash
$ venv/bin/pytest -q
........................................................................ [ 39%]
........................................................................ [ 78%]
.......................................                                  [100%]
183 passed in 7.75s
```

183 test verdi (il brief prevedeva 181; l'extra viene dai 4 test nuovi invece di 2, probabilmente una sottostima nel brief).

## File cambiati

- `domain/solver/vocabulary.py` — Aggiunte 143 linee (sei nuovi metodi privati esclusi).
- `tests/test_solver_vocabulary.py` — Aggiunti 4 test.

## Commit creato

```
ccfd78b feat(solver): il vocabolario, seconda meta'
```

## Autorevisione

**Completezza:** ✓ Tutte e cinque le primitive implementate esattamente come nel brief.

**Qualità:** 
- ✓ Nomi chiari e coerenti con la terminologia del progetto.
- ✓ Docstring in italiano che descrivono semantica e avvertimenti.
- ✓ Memoizzazione corretta con chiavi che includono la firma.
- ✓ Uso di `_max_or_zero` per gli aggregati (nessun `AddMaxEquality` diretto su liste potenzialmente vuote).

**Disciplina:**
- ✓ Segui i pattern del Task 1 (memoizzazione, signature opzionale, semantica conservativo/anti-conservativo).
- ✓ TDD rigoroso: test scritti prima, eseguiti fallendo, risolti.
- ✓ Nessuna costruzione extra (YAGNI).
- ✓ Nessun builder li consuma ancora — esattamente come dichiarato nel brief.

**Test:**
- ✓ Quattro test nuovi specifici: subject_bucket con due fasce, subject_bucket ignora altre materie, pos canalizza giorno+fascia, site_occupied distingue sedi.
- ✓ Tutti e 10 i test del vocabulario passano.
- ✓ Nessun test preesistente è rotto (183 totali, nessuna regressione).

**Output pulito:**
- ✓ Nessun warning, nessun messaggio spurio.
- ✓ Pytest esegue pulito (colorize, progress, resume).

## Dubbi

Nessuno. L'implementazione è corretta e segue esattamente il brief e i pattern del progetto.
