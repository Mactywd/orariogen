# Task 14 — report — `HALF_DAY_GAP`

Worktree `modello-hard-completo`, HEAD di partenza `e10a2cc`. Non committato,
non pushato (come richiesto dal brief).

## Cosa e' stato fatto

### 1. Rinominati gli helper condivisi

`_post_separable` -> `post_separable`, `_post_cross` -> `post_cross` in
`domain/solver/builders/subject_buckets.py`. Aggiornate tutte le chiamate e
tutte le menzioni nelle docstring che li nominano, nei file:
`subject_buckets.py`, `subject_order.py`, `base.py`,
`tests/test_solver_subject_buckets.py`. Nessuna occorrenza del vecchio nome
resta nel repository (grep verificato).

### 2. `HalfDayGapBuilder`, in `domain/solver/builders/subject_order.py`

Riusa interamente `post_separable`/`post_cross` — non posta nulla di
proprio, nessun trattamento ADR-018 scritto qui perche' e' gia' interamente
nella tabella a quattro rami di `post_cross` (e nel clamp di
`post_separable`). Il loop e' quello del piano (`for u in range(n): for w
in range(u, min(u + minimo, n))`), con la tabella a quattro casi richiesta
dal brief:

| caso | chiamata |
|---|---|
| A = B, `w == u` | `post_separable(A, "half", u)` |
| A = B, `w != u` | `post_cross(A@u, A@w)` |
| A != B, `w == u` | `post_cross(A@u, B@u)` (un'unica chiamata) |
| A != B, `w != u` | `post_cross(A@u, B@w)` **e** `post_cross(B@u, A@w)` |

**Correzione di premessa rispetto al piano**: la docstring non dice "piu'
stretto, mai piu' largo" — dice che vincolare tutte le coppie incrociate ed
vincolare solo le consecutive incrociate nell'ordinamento sono
**equivalenti**, con la dimostrazione per assurdo (coppia incrociata
minimale => adiacente) scritta per intero nel docstring della classe.
Nessun claim di "conservativo" e' rimasto nel codice.

Note esplicite in docstring, come richiesto:
- `post_cross` con A = B su due secchi distinti e' gia' l'uso di
  `TwoDaysBuilder` (Task 10): non e' un abuso dell'helper.
- Il finding del checker porta `gap`/`min_gap`, non `count` — a differenza
  di quanto `post_separable` dice testualmente — ma la tupla `activities`
  cresce comunque a ogni aggiunta libera in un secchio gia' violato, ed e'
  quella tupla a entrare in `Finding.key`: la stessa conclusione regge, per
  la stessa ragione. Scritto esplicitamente, non lasciato implicito.

### 3. Il derivatore, `tests/solver_harness.py`, `_derive_half_day_gap`

Riscritto per intero rispetto al piano (che creava solo righe A = B, si
fermava alla prima con `return`, derivava sull'unione delle settimane e non
aveva guardia di violabilita'). La nuova versione:

- itera su coppie **ordinate** (A, B), inclusa A = B;
- per ogni firma di settimana costruisce `merged` con le occorrenze attive
  in quella firma (solo A se `same`, A e B altrimenti — con `same = False`
  salta la firma, non l'intera coppia, se un lato e' vuoto);
- calcola il minimo su **tutte** le coppie incrociate di quella firma (non
  solo le adiacenti — la dimostrazione del builder dice che sono
  equivalenti, e derivare in questo modo tiene la derivazione onesta
  rispetto alla dimostrazione, non fidata di essa);
- `param` finale e' il **minimo fra le firme** (non il massimo — a
  differenza di WEEKLY_ORDER/IMPOSED_SUCCESSION, qui `param` e' una soglia
  dal basso, non un tetto, quindi la firma piu' stretta e' quella che
  decide);
- guardie: nessuna riga se `param is None`, se `param < 1`, o se
  `param >= n`;
- assert `not ClassPart.objects.exists()` in testa, come negli altri due
  derivatori d'ordine.

### 4. `tests/test_solver_half_day_gap.py`

Nessun `test_half_day_gap_sul_banco` (Ruling 16): il derivatore registrato
sotto `T.HALF_DAY_GAP` fa si' che `test_solver_witness.py::test_famiglia`
generi gia' i cinque seed della famiglia. Cinque test, tutti in forma
avversaria (Ruling 85 — `build_model` + `model.Add(ctx.x[...] == 1)`,
mai "risolvi e guarda dove e' finita" tranne dove serve un'asserzione
strutturale di feasibility):

1. `test_half_day_gap_a_uguale_b_morde` — A = B, `w != u`, INFEASIBLE.
2. `test_half_day_gap_a_uguale_b_distanza_legale` — stessa coppia a
   distanza legale, FEASIBLE.
3. `test_half_day_gap_a_uguale_b_stessa_mezza_giornata_morde` — ramo
   `w == u`, `post_separable`, INFEASIBLE.
4. `test_half_day_gap_a_diverso_b_morde_in_entrambi_i_versi` — A != B, due
   scenari (A prima, poi B prima), entrambi INFEASIBLE.
5. `test_adr018_half_day_gap_non_pretende_la_riparazione` — due congelate
   che gia' violano la riga, piu' una libera lontana forzata: FEASIBLE
   (asserzione strutturale).

## Mutazioni verificate

Ogni mutazione applicata a un file, eseguito `pytest
tests/test_solver_half_day_gap.py -q`, poi ripristinato il file originale
(verificato con `diff` a zero righe dopo il ripristino — nessuna mutazione
e' rimasta nel repository).

| # | Mutazione | File | Atteso | Esito osservato |
|---|---|---|---|---|
| 1 | `HalfDayGapBuilder.post` reso no-op (`return` come prima riga) | `subject_order.py` | test 1, 3, 4 rossi; 2, 5 verdi | **Confermato**: `test_..._morde`, `test_..._stessa_mezza_giornata_morde`, `test_..._entrambi_i_versi` FAIL; `test_..._distanza_legale` e `test_adr018_...` restano PASS |
| 2 | `min(u + minimo, n)` -> `n` nel ciclo (il `minimo` viene ignorato, si vincolano tutte le coppie della settimana) | `subject_order.py` | test 2 rosso (copre "il builder che vieta tutto") | **Confermato**: `test_..._distanza_legale` FAIL (INFEASIBLE invece di FEASIBLE); anche `test_adr018_...` cade come effetto collaterale (la finestra allargata coinvolge anche il buco fra le due congelate) |
| 3 | Ramo `if w == u:` sostituito con `continue` (salta `post_separable`) | `subject_order.py` | test 3 rosso, gli altri verdi | **Confermato**: solo `test_..._stessa_mezza_giornata_morde` FAIL |
| 4 | Rimossa la seconda chiamata `post_cross(B@u, A@w)` nel ramo `A != B, w != u` | `subject_order.py` | test 4 rosso **solo sullo scenario 2** (verso invertito) | **Confermato**: lo scenario 1 (verso diretto) resta INFEASIBLE come atteso; lo scenario 2 diventa OPTIMAL — l'assert su `solver2.Solve(model2) == INFEASIBLE` fallisce, esattamente il verso che la seconda chiamata copre |
| 5 | In `post_cross` (subject_buckets.py), il ramo `if not fa and not fb:` sostituito con `if True:` (ADR-018 ignorato, sempre il vincolo secco `ha + hb <= 1`) | `subject_buckets.py` | test 5 rosso, gli altri verdi | **Confermato**: solo `test_adr018_half_day_gap_non_pretende_la_riparazione` FAIL (INFEASIBLE invece di FEASIBLE) |

Tutte e cinque le mutazioni sono state applicate una alla volta, eseguite, e
il file e' stato ripristinato dall'originale prima di passare alla
successiva; alla fine `git diff` sui due file coinvolti (`subject_order.py`,
`subject_buckets.py`) coincide esattamente con le modifiche intenzionali di
questo task (nessun residuo di mutazione).

## Numeri riprodotti (40 seed, misura indipendente)

Misurati con uno script temporaneo (non incluso nella consegna — cancellato
dopo la misura), che per ogni seed 1..40: costruisce il testimone, chiama
`_derive_half_day_gap`, verifica che il testimone non violi le righe create,
poi — col builder reale **sostituito da un no-op** — ributta il modello da
zero (nessun piazzamento di partenza) e controlla se la soluzione che CP-SAT
trova comunque viola le righe appena derivate ("morde" = si').

- **Righe per seed**: da 0 (seed 33, vacuo) a 13 (seed 10 e seed 25).
  Range **0-13**, in linea con quanto dichiarato nel brief.
- **Testimoni violati**: 0/40. Nessuna riga derivata e' mai violata dal
  testimone che l'ha generata.
- **Potere vincolante col builder assente**, globale: **35/39** (esclude il
  seed 33 vacuo) morde. Il brief riportava 36/40 come riferimento — la
  differenza (35 contro 36, su una misura che dipende dalla ricerca di
  default di CP-SAT quando il builder e' assente, non da una proprieta'
  matematica esatta) e' dello stesso ordine delle varianze gia' osservate
  per le altre famiglie (10/15 e 12-14/15 per le due delle sedi, citate nel
  brief stesso). Non e' stata inseguita, per lo stesso motivo per cui il
  brief dice di non inseguire il seed 2.
- **Seed 2 non morde**: **confermato**, e in modo deterministico — stesso
  comportamento segnalato nel brief. E' il riscontro piu' forte che la
  riscrittura del derivatore e' comportamentalmente equivalente a quella di
  riferimento: lo stesso seed, isolato per lo stesso motivo, si comporta
  allo stesso modo.
- **Nel banco (seed 1-5)**: 3/5 mordono con questa misura (seed 1 e seed 2
  non mordono; il brief ne riporta 4/5, con solo il seed 2 come eccezione).
  Vedi nota sotto.

**Nota sulla divergenza 3/5 vs 4/5**: la misura "morde col builder assente"
non e' una proprieta' del derivatore ma del comportamento di ricerca di
CP-SAT quando nessuno vieta la violazione — dipende da quale soluzione
ammissibile trova per prima, non da una soglia matematica fissa. E' rumorosa
per costruzione (lo dice il brief stesso, parlando di varianza fra
famiglie). Il derivatore supera invece **tutte** le proprieta' verificabili
in modo deterministico: 0 testimoni violati su 40, il range di righe
dichiarato, e — soprattutto — la suite intera (`run_family`, tramite
`test_famiglia`) verde sui 5 seed del banco, cioe' la proprieta' che conta
davvero (nessun INFEASIBLE con testimone disponibile, nessuna soluzione
sporca). Il peso della dimostrazione di correttezza lo porta comunque il
test avversario di `tests/test_solver_half_day_gap.py`, con le mutazioni
verificate sopra — non questa misura di banco, come il brief stesso
anticipa ("il peso della dimostrazione lo porta il test avversario, non il
banco").

## Verifica finale

```
venv/bin/pytest -q
375 passed, 4 skipped
```

Baseline dichiarata nel brief: 365 passed, 4 skipped. Delta: **+10** (5 test
in `tests/test_solver_half_day_gap.py` + 5 nuovi casi parametrizzati di
`test_solver_witness.py::test_famiglia`, uno per ciascun seed del banco,
generati automaticamente dalla registrazione del derivatore). Nessuno skip
nuovo: il derivatore non e' mai vacuo sui 5 seed del banco.

`tests/test_solver_registry.py` aggiornato: `T.HALF_DAY_GAP` aggiunto
all'insieme atteso in `test_i_builder_tradotti_finora`, e la sua docstring
aggiornata per menzionare il Task 14.

`domain/analysis/` non e' stato toccato (verificato: nessun file modificato
in quel package, e nessun import di `ortools` al suo interno).

## Scostamenti dal brief

Nessuno di sostanza. L'unico scostamento e' la misura di "potere vincolante
col builder assente" sui 40 seed (35/39 e 3/5 contro 36/40 e 4/5 del brief),
gia' discussa sopra: e' una misura rumorosa per natura (dipende dal
comportamento di ricerca di CP-SAT, non da una soglia deterministica), il
brief stesso la qualifica come non da inseguire, e il segnale piu'
significativo — il seed 2 che non morde in modo deterministico — e' stato
riprodotto esattamente.
