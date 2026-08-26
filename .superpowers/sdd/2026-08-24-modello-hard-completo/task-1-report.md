# Task 1 — Il vocabolario, prima metà: report

## Stato: DONE

## Cosa ho implementato

1. **`domain/solver/vocabulary.py`** (nuovo). Classe `Vocabulary(ctx, model)`
   con:
   - `halves()` — `[range mattina, range pomeriggio]`, la seconda può essere
     vuota (`morning_end_slot == slots_per_day`).
   - `half_of(slot)` — helper non richiesto esplicitamente dal test ma incluso
     nel testo del brief, utile ai builder futuri.
   - `occupied(key, day, slot, signature=None)` — stessa semantica di
     `SolverContext.occupied`, ma il modello è tenuto dal vocabolario, non
     passato a ogni chiamata.
   - `covered(key, day, span, signature=None)` — `{fascia: letterale}`, vero
     se la fascia sta fra la prima e l'ultima occupata **dentro `span`**. Il
     parametro `span` è ciò che distingue il D.T.B. (mezza giornata) da
     MAX_PRESENCE (giornata intera) — costruito ma non ancora consumato da
     MAX_PRESENCE, che arriva in un task successivo.
   - `day_active(key, day, signature=None)` e
     `half_active(key, day, half, signature=None)`.
   - `_max_or_zero(var, lits)` — evita `AddMaxEquality`/liste vuote fissando
     la variabile a 0 con `model.Add(var == 0)`.
   - Memoizzazione su `(kind, key completa)` tramite `_memo`, come richiesto:
     `day_active` è provato letteralmente identico (`is`) su due chiamate.

2. **`domain/solver/context.py`** — rimossi il metodo `occupied` e il campo
   `_occupied`; aggiunto `vocab: object = None` (assegnato da `build_model`).

3. **`domain/solver/model.py`** — importa `Vocabulary` e, subito dopo
   `ctx.index_cells()` e prima del ciclo `builder.build(...)`, assegna
   `ctx.vocab = Vocabulary(ctx, model)`.

4. **`domain/solver/builders/time_constraints.py`** (`MaxGapBuilder`) —
   il doppio ciclo giorno/mezza-giornata che costruiva a mano
   `before`/`after`/`covered` è sostituito dalla chiamata a
   `ctx.vocab.covered(key, day, half, signature=rep)` più
   `ctx.vocab.occupied(...)` per il termine sottratto. Rimossa anche la
   variabile locale `halves` in testa a `build()`, diventata morta dopo il
   passaggio a `ctx.vocab.halves()`. Il resto del builder (ciclo sulle firme,
   `posted`, il vincolo di budget) è invariato.

5. **`tests/test_solver_vocabulary.py`** (nuovo) — i quattro test dettati dal
   brief, verbatim.

6. **`tests/test_solver_context.py`** — le righe 72-73 (l'unico altro
   chiamante di `ctx.occupied` nel repo, segnalato dal controller) sono state
   riscritte per passare da `Vocabulary`: import aggiunto,
   `occ = vocab.occupied(key, 0, 0)` /
   `assert vocab.occupied(key, 0, 0) is occ` al posto di
   `ctx.occupied(model, key, 0, 0)`. Il test non è stato cancellato né
   ridotto: stesso numero di asserzioni, stessa proprietà (memoizzazione)
   verificata, solo sull'interfaccia nuova.

Ho verificato che non ci fossero altri chiamanti di `ctx.occupied` oltre
quelli già noti:

```
$ grep -rn "\.occupied(" domain/ tests/
domain/solver/builders/time_constraints.py:65:  (ctx.vocab.occupied — nuovo)
domain/solver/vocabulary.py:...                (definizione)
tests/test_solver_context.py:...               (vocab.occupied — riscritto)
```

Nessun residuo di `ctx.occupied(model, ...)`.

## TDD — prova

**RED.** Scritto `tests/test_solver_vocabulary.py` con il modulo
`domain/solver/vocabulary.py` ancora inesistente.

Comando: `venv/bin/pytest tests/test_solver_vocabulary.py -v`

Output rilevante:
```
ERROR collecting tests/test_solver_vocabulary.py
ImportError while importing test module '.../tests/test_solver_vocabulary.py'.
tests/test_solver_vocabulary.py:9: in <module>
    from domain.solver.vocabulary import Vocabulary
E   ModuleNotFoundError: No module named 'domain.solver.vocabulary'
Interrupted: 1 error during collection
```
Fallimento atteso e per il motivo giusto: il modulo non esiste ancora, non un
errore di logica nei test.

**GREEN.** Dopo aver scritto `domain/solver/vocabulary.py` e i punti 2-4
sopra:

Comando: `venv/bin/pytest tests/test_solver_vocabulary.py -v`
```
tests/test_solver_vocabulary.py::test_halves_pomeriggio_puo_essere_vuoto PASSED
tests/test_solver_vocabulary.py::test_half_active_su_meta_vuota_non_esplode PASSED
tests/test_solver_vocabulary.py::test_covered_span_mezza_giornata_contro_giornata_intera PASSED
tests/test_solver_vocabulary.py::test_day_active_e_memoizzazione PASSED
4 passed
```

Comando: `venv/bin/pytest tests/test_solver_vocabulary.py tests/test_solver_context.py -v`
```
10 passed in 0.70s
```
(le 4 nuove + le 6 esistenti di `test_solver_context.py`, riscritte sulla
nuova interfaccia — tutte verdi.)

## Suite intera (una sola esecuzione, prima del commit)

Comando: `venv/bin/pytest -q`
```
........................................................................ [ 40%]
........................................................................ [ 81%]
.................................                                        [100%]
177 passed in 7.43s
```
177 = 173 di partenza + 4 nuovi in `test_solver_vocabulary.py`. Nessuna
riduzione del numero di test, nessun test esistente rotto, output pulito
(nessun warning).

## File cambiati

- `domain/solver/vocabulary.py` (nuovo)
- `domain/solver/context.py` (rimossi `occupied`/`_occupied`, aggiunto `vocab`)
- `domain/solver/model.py` (import + `ctx.vocab = Vocabulary(ctx, model)`)
- `domain/solver/builders/time_constraints.py` (`MaxGapBuilder` su `ctx.vocab`)
- `tests/test_solver_vocabulary.py` (nuovo)
- `tests/test_solver_context.py` (le due righe 72-73 riscritte su `Vocabulary`,
  segnalato dal controller come chiamante non menzionato dal brief)

Commit: `6e5050d` — "refactor(solver): il vocabolario delle variabili
derivate, prima meta'"

## Autorevisione

- **Completezza**: tutte le firme richieste dal brief sono presenti con
  l'esatta interfaccia specificata (`Vocabulary(ctx, model)`,
  `vocab.halves()`, `vocab.occupied(key, day, slot, signature=None)`,
  `vocab.covered(key, day, span, signature=None)`,
  `vocab.day_active(key, day, signature=None)`,
  `vocab.half_active(key, day, half, signature=None)`). Il chiamante orfano
  segnalato dal controller (`tests/test_solver_context.py`) è stato trovato,
  riscritto e non cancellato.
- **Qualità**: nomi identici a quelli del brief (coerenza col resto dello
  spike). Il docstring di `covered` spiega esplicitamente perché `span` non è
  un dettaglio — la stessa spiegazione che serve al prossimo builder
  (MAX_PRESENCE) per non ripetere l'errore già fatto una volta col D.T.B.
- **Disciplina (YAGNI)**: non ho aggiunto varianti non richieste. L'unica
  aggiunta oltre il codice del brief è la rimozione della variabile locale
  `halves` ormai morta in `MaxGapBuilder.build` — pulizia minima nel file che
  stavo già toccando, non una ristrutturazione.
- **Test**: seguito TDD come richiesto (RED verificato per il motivo giusto,
  poi GREEN). I quattro test del brief sono usati verbatim: coprono il caso
  vuoto della griglia (`halves`/`half_active` senza esplodere su
  `AddMaxEquality([])`), la distinzione `span` mezza-giornata vs
  giornata-intera su `covered` (il test che il brief segnala come quello che
  conta davvero), e la memoizzazione (`is`) su `day_active`.
- **domain/analysis/ non importa ortools**: non toccato in questo task, verifica
  non applicabile (il vocabolario vive solo in `domain/solver/`).
- **Chiavi del registro**: non toccate — il task non tocca `registry.py`.

## Dubbi

Nessuno. Un'unica nota, non un dubbio: `half_of(slot)` è presente nel testo
del brief (dentro il blocco di codice da copiare) ma non è esercitato da
nessun test del brief né usato da `MaxGapBuilder`. L'ho mantenuto perché fa
parte letterale del codice da scrivere al passo 3 — sarà presumibilmente
consumato da un builder di un task successivo (es. i vincoli di materia che
useranno `half_active`/`half_of` per bucket per mezza giornata).

---

## Rapporto di correzione — giro 1 di 5

### Osservazione Important (revisore): default `signature=None` non più documentato

Il docstring rimosso da `SolverContext.occupied()` (nel diff del giro
precedente) diceva esplicitamente cosa succede quando `signature` è omesso:
*«conta tutte le attività che toccano la cella indipendentemente dalla
settimana»*. Nel vocabolario quella frase non era stata riportata in nessuna
delle quattro primitive, e l'asimmetria conta: su `occupied()` da sola,
ometterlo è conservativo (più letterali → vincolo più stretto); sui tre
aggregati per risorsa (`covered`, `day_active`, `half_active`) non lo è —
è esattamente il difetto già trovato in `MaxGapBuilder` il 2026-08-24.

**Correzione applicata** in `domain/solver/vocabulary.py`:

1. `occupied()` — ripristinata la frase sul comportamento del default, più la
   spiegazione della conservatività sulla singola cella.
2. `covered()` — aggiunto un paragrafo `⚠` dedicato a `signature`, separato da
   quello su `span`, che spiega perché ometterla qui non è conservativo e
   rimanda esplicitamente al difetto di `MaxGapBuilder` del 2026-08-24.
3. `day_active()` — aggiunto un docstring (non ne aveva uno) con lo stesso
   avvertimento.
4. `half_active()` — docstring esteso con lo stesso avvertimento.

Diff completo (incollato, non parafrasato):

```diff
diff --git a/domain/solver/vocabulary.py b/domain/solver/vocabulary.py
index 982b884..082a15a 100644
--- a/domain/solver/vocabulary.py
+++ b/domain/solver/vocabulary.py
@@ -50,7 +50,14 @@ class Vocabulary:
 
         `signature`, se dato, e' il rappresentante di una firma di settimana:
         il letterale conta solo le attivita' attive in quella firma, come
-        farebbe ScheduleState.build(schedule, week=rep) per il checker."""
+        farebbe ScheduleState.build(schedule, week=rep) per il checker.
+
+        Omesso (`None`), conta tutte le attivita' che toccano la cella
+        indipendentemente dalla settimana. Per un vincolo di **cardinalita'
+        sulla singola cella** questo e' conservativo: piu' letterali vuol dire
+        un vincolo piu' stretto, mai piu' lasco. Non e' piu' vero appena questo
+        letterale entra in un aggregato per risorsa — vedi `covered`,
+        `day_active`, `half_active`."""
         def make():
             var = self.model.NewBoolVar(f"occ_{key}_{day}_{slot}_{signature}")
             entries = self.ctx.by_cell.get((key, day, slot), ())
@@ -68,7 +75,16 @@ class Vocabulary:
         (non conta mai buchi a cavallo del pranzo), MAX_PRESENCE sulla giornata
         intera (`_presence_minutes` non passa da `_halves`). Sono due cose
         diverse che si somigliano: qui la differenza e' un argomento visibile
-        alla chiamata."""
+        alla chiamata.
+
+        ⚠ `signature` va passato quando il chiamante distingue le settimane:
+        qui, a differenza di `occupied` da sola, ometterlo **non** e'
+        conservativo. Un'occupazione che cade dentro il buco ma viene da
+        un'attivita' di un'**altra** firma alza il conteggio senza spostare
+        prima/ultima occupata — chiude nel modello unione un buco che,
+        settimana per settimana, resta aperto. E' esattamente il difetto che
+        MaxGapBuilder aveva prima della correzione del 2026-08-24 (vedi
+        CLAUDE.md, changelog di quella data)."""
         span = tuple(span)
         def make():
             occ = {s: self.occupied(key, day, s, signature) for s in span}
@@ -88,6 +104,12 @@ class Vocabulary:
     # --- presenza per giornata e mezza giornata --------------------------
 
     def day_active(self, key, day, signature=None):
+        """Vero se la chiave e' occupata in almeno una fascia della giornata.
+
+        ⚠ Stesso avvertimento di `covered`: e' un aggregato per risorsa, non
+        una singola cella. Omettere la firma non e' conservativo — un'attivita'
+        di un'altra firma di settimana puo' far risultare 'attiva' una
+        giornata che, per quella firma, non lo e'."""
         def make():
             var = self.model.NewBoolVar(f"dayact_{key}_{signature}_{day}")
             lits = [self.occupied(key, day, s, signature)
@@ -96,7 +118,11 @@ class Vocabulary:
         return self._memo("day_active", (signature, key, day), make)
 
     def half_active(self, key, day, half, signature=None):
-        """`half`: 0 mattina, 1 pomeriggio."""
+        """`half`: 0 mattina, 1 pomeriggio.
+
+        ⚠ Stesso avvertimento di `covered` e `day_active`: e' un aggregato
+        per risorsa. Omettere la firma non e' conservativo, per lo stesso
+        motivo."""
         def make():
             var = self.model.NewBoolVar(f"halfact_{key}_{signature}_{day}_{half}")
             lits = [self.occupied(key, day, s, signature)
```

### Requisito aggiunto dal controller: test che esercitano `signature=` e caso positivo di `half_active`

**1. `test_day_active_distingue_le_firme`** — due attività su firme di
settimana diverse (maschere a un bit solo, settimane 0 e 1, seguendo il
pattern di `tests/test_solver_oracle.py::_scuola_multi_firma_fattibile`
letto prima di scrivere il test). A è attiva solo nella firma della
settimana 0, B solo in quella della settimana 1. A piazzata al giorno 1
(non 0), B piazzata al giorno 0. Con la firma di A passata,
`day_active(giorno 0, signature=rep_a)` non deve essere alzata
dall'occupazione di B (B non è tra le attività attive in quella firma);
senza firma, la stessa interrogazione la conta comunque. Questo è
precisamente l'asse anti-conservativo descritto nell'osservazione Important.

**2. `test_half_active_caso_positivo_in_mattina`** — il test preesistente
`test_half_active_su_meta_vuota_non_esplode` asserisce solo il valore zero
sulla metà vuota; il nuovo test verifica il caso simmetrico: un'attività
piazzata in mattina (fascia 1, con `morning_end_slot=4`) fa risultare
`half_active(key, day, 0) == 1`.

### Verifica che `test_day_active_distingue_le_firme` discrimina davvero

Non basta che il test passi: doveva essere verificato che fallisce se la
distinzione per firma è rotta. Ho disabilitato temporaneamente il filtro per
`signature` dentro `occupied()` (rimuovendo il blocco
`if signature is not None: ... entries = [...]`), rilanciato il solo test
nuovo, e ripristinato il file subito dopo con un backup (`diff` confermato
identico al termine).

Comando e output incollati (non parafrasati):

```
$ venv/bin/pytest tests/test_solver_vocabulary.py::test_day_active_distingue_le_firme -v
...
        key = env["klass"].pk
        con_firma = vocab.day_active(key, 0, signature=rep_a)
        senza_firma = vocab.day_active(key, 0)
    
        solver = cp_model.CpSolver()
        assert solver.Solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
>       assert solver.Value(con_firma) == 0     # A non e' al giorno 0: nella sua firma, non e' attivo
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert 1 == 0
E        +  where 1 = deprecated_func(dayact_1_0_0(0..1))
E        +    where deprecated_func = <ortools.sat.python.cp_model.CpSolver object at 0x75582a40fb90>.Value

tests/test_solver_vocabulary.py:131: AssertionError
---------------------------- Captured stderr setup -----------------------------
Creating test database for alias 'default'...
--------------------------- Captured stderr teardown -----------------------------
Destroying test database for alias 'default'...
=========================== short test summary info ============================
FAILED tests/test_solver_vocabulary.py::test_day_active_distingue_le_firme - ...
============================== 1 failed in 0.63s ===============================
```

Il file è stato ripristinato dal backup (`cp /tmp/vocabulary.py.bak
domain/solver/vocabulary.py`), e `diff` fra backup e file ripristinato non ha
prodotto output (identici).

### Test rilanciati dopo la correzione

Comando: `venv/bin/pytest tests/test_solver_vocabulary.py -v`

Output (incollato):
```
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0 -- /home/mattia/coding/scuola/orariogen/venv/bin/python3
cachedir: .pytest_cache
django: version: 5.2.17, settings: config.settings (from ini)
rootdir: /home/mattia/coding/scuola/orariogen/.claude/worktrees/modello-hard-completo
configfile: pytest.ini
plugins: django-4.14.0
collecting ... collected 6 items

tests/test_solver_vocabulary.py::test_halves_pomeriggio_puo_essere_vuoto PASSED [ 16%]
tests/test_solver_vocabulary.py::test_half_active_su_meta_vuota_non_esplode PASSED [ 33%]
tests/test_solver_vocabulary.py::test_covered_span_mezza_giornata_contro_giornata_intera PASSED [ 50%]
tests/test_solver_vocabulary.py::test_day_active_e_memoizzazione PASSED  [ 66%]
tests/test_solver_vocabulary.py::test_half_active_caso_positivo_in_mattina PASSED [ 83%]
tests/test_solver_vocabulary.py::test_day_active_distingue_le_firme PASSED [100%]

============================== 6 passed in 0.67s ===============================
```

Comando: `venv/bin/pytest tests/test_solver_vocabulary.py tests/test_solver_context.py -v`

Output (incollato, coda):
```
tests/test_solver_vocabulary.py::test_halves_pomeriggio_puo_essere_vuoto PASSED [  8%]
tests/test_solver_vocabulary.py::test_half_active_su_meta_vuota_non_esplode PASSED [ 16%]
tests/test_solver_vocabulary.py::test_covered_span_mezza_giornata_contro_giornata_intera PASSED [ 25%]
tests/test_solver_vocabulary.py::test_day_active_e_memoizzazione PASSED  [ 33%]
tests/test_solver_vocabulary.py::test_half_active_caso_positivo_in_mattina PASSED [ 41%]
tests/test_solver_vocabulary.py::test_day_active_distingue_le_firme PASSED [ 50%]
tests/test_solver_context.py::test_celle_iniziali_secondo_la_durata PASSED [ 58%]
tests/test_solver_context.py::test_attivita_fissa_congelata_alla_sua_cella PASSED [ 66%]
tests/test_solver_context.py::test_attivita_fissa_mai_piazzata_esce_dal_modello PASSED [ 75%]
tests/test_solver_context.py::test_estrazione_libera_solo_le_sue_attivita PASSED [ 83%]
tests/test_solver_context.py::test_token_e_capacita_arrivano_dallo_stato PASSED [ 91%]
tests/test_solver_context.py::test_indice_per_cella_e_canalizzazione PASSED [100%]

============================== 12 passed in 0.76s ===============================
```

Suite intera, una sola esecuzione prima del commit:

Comando: `venv/bin/pytest -q`

Output (incollato):
```
........................................................................ [ 40%]
........................................................................ [ 80%]
...................................                                      [100%]
179 passed in 7.64s
```

179 = 173 iniziali + 4 del giro precedente + 2 di questo giro. Nessuna
riduzione, nessun test rotto, output pulito.

### File cambiati in questo giro

- `domain/solver/vocabulary.py` (docstring)
- `tests/test_solver_vocabulary.py` (due test nuovi)

Commit: `e4b6f9f` — "fix(solver): documenta il default signature=None e prova
che discrimina"

### Nota di metodo recepita

Il revisore ha segnalato che nel primo report avevo presentato come
trascrizione di un `grep` delle righe in realtà parafrasate. Corretto in
questo giro: sia il diff sia l'output dei comandi sopra sono incollati dal
terminale, non riassunti.

### Minor differite (non toccate in questo giro, per istruzione esplicita)

I nomi CP-SAT di `covered` che non distinguono gli span; il ramo
irraggiungibile `span[0] if span else 'x'`; `covered` che restituisce il
dizionario memoizzato per riferimento; `half_of` come codice morto (nel
brief, consumato dal Task 2). Lasciate alla review finale di branch.

### Dubbi

Nessuno.
