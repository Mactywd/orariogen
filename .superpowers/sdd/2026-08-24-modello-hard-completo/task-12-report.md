# Task 12 — `WEEKLY_ORDER` — report

## Cosa ho implementato

`domain/solver/builders/subject_order.py` (nuovo): `WeeklyOrderBuilder`
(`T.WEEKLY_ORDER`, eredita `SubjectBuilder`). Registrato in
`domain/solver/builders/__init__.py`.

`tests/solver_harness.py`: un derivatore, `_derive_weekly_order`, registrato
sotto `ST.WEEKLY_ORDER`, con l'helper `_pos_bounds` per il minimo/massimo di
`pos` ammissibile di un'attivita' — **non** il derivatore rotto del piano,
la formulazione corretta descritta al §2 del brief.

`tests/test_solver_subject_order.py` (nuovo): sei test mirati, nessun
`test_..._sul_banco` (copre gia' `test_solver_witness.py::test_famiglia`).

`tests/test_solver_registry.py::test_i_builder_tradotti_finora`: aggiunto
`SubjectConstraint.Type.WEEKLY_ORDER` all'insieme atteso e alla docstring.

Nessun file di `domain/analysis/` toccato.

## Il derivatore — la formulazione corretta, misurata

Ho implementato esattamente la formulazione del §2 del brief, non quella del
piano (misurata rotta). Per ogni classe, per ogni coppia ordinata (A, B) di
materie distinte presenti nel testimone:

1. per ogni firma in cui sia A sia B hanno attivita' attive: se la prima
   occorrenza **piazzata** di B precede quella di A, la coppia si scarta
   (basta una sola firma a smentirla); una firma con una delle due materie
   assente non dice nulla, si passa oltre;
2. violabilita' geometrica, in almeno una firma dove entrambe sono presenti:
   `floor_b` (il minimo, su B, della posizione ammissibile piu' presto,
   calcolato con `_pos_bounds`) deve essere minore di `ceil_a` (il minimo,
   su A, della posizione ammissibile piu' tardi). E' necessaria non
   sufficiente per costruzione — ignora indisponibilita', sedi, altre
   attivita'.

`_pos_bounds` sfrutta il fatto che il dominio ammissibile di un'attivita' e'
un prodotto cartesiano giorni × fasce (nessuna delle due dipende
dall'altra, una volta esclusi giorno festivo e attraversamento
dell'intervallo): il minimo/massimo di `pos = day * width + slot` si ottiene
dai minimi/massimi separati di `giorni` e di `_collocazioni(w, aid)`, senza
enumerare le celle.

**Misure su 60 seed** (script ad-hoc, non nel repo — misura una tantum):

- **0/60 vacui** (`potere` sempre > 0, range 1-6 righe per seed);
- **0/60 testimoni violati** (il passo 1 di `run_family` non fallisce mai);
- **potere vincolante col builder reso no-op**: **19/20** seed (1-20)
  intercettano l'assenza del builder, **4/5** dentro il banco effettivo
  (seed 1-5). Il seed 5 non morde, deterministico su quattro esecuzioni
  consecutive — coerente con quanto il brief anticipava, e con la natura
  necessaria-non-sufficiente della guardia geometrica. Documentato nel
  docstring del derivatore, senza mettere i numeri in docstring (Ruling 50).

Ho anche verificato `venv/bin/pytest "tests/test_solver_witness.py::test_famiglia" -k WEEKLY_ORDER -v -rs`:
5 seed, tutti `PASSED`, nessuno skippato.

## Il builder — ADR-018, il quarto pattern

`post()`:

1. esce se `subject_a_id == subject_b_id` (guardia principale — nella
   famiglia WEEKLY_ORDER e' il caso che *non* vincola nulla, il rovescio
   delle altre tredici famiglie di materia dove A = B e' dominante);
2. esce se `a` o `b` (da `subject_activities(..., signature=rep)`) e' vuoto;
3. `AddMinEquality` su `pos` per i due gruppi (`prima_a`, `prima_b`);
4. calcola `FA`/`FB` — il minimo di `pos` sulle sole attivita' **congelate**
   di A/B in questa firma, `None` se non ce ne sono. Costanti note a build
   time: un'attivita' congelata ha `ctx.cells` di cardinalita' uno, quindi
   `_frozen_pos` legge direttamente la cella senza passare da `vocab.pos`;
5. due rami:
   - `FA is None or FB is None or FB >= FA` → vincolo secco
     `prima_a <= prima_b` (previene, non ripara);
   - `FA is not None and FB is not None and FB < FA` → disgiunzione
     reificata (`riparato`): `prima_a <= prima_b` sotto
     `OnlyEnforceIf(riparato)`, `prima_a >= FA` e `prima_b >= FB` sotto
     `OnlyEnforceIf(riparato.Not())` — che equivalgono a `prima_a == FA` e
     `prima_b == FB` perche' le rispettive congelate gia' realizzano quei
     minimi.

Questo e' il quarto pattern ADR-018 del branch (dopo il clamp a zero di
`residual_cap`, la tabella a quattro rami di `_post_cross`, e il `continue`
per-coppia di `ForbiddenSequenceBuilder`): qui il residuo non e' una somma ne'
un massimo su un secchio, ma un **minimo su un gruppo** — la disgiunzione
reificata e' la forma che quel tipo di residuo richiede.

## Le mutazioni — tutte verificate manualmente

Ho salvato una copia del builder originale, applicato ogni mutazione,
confermato il rosso, poi ripristinato l'originale e riverificato la suite
verde. Cinque mutazioni, cinque test rossi:

1. **Rimosso `if row.subject_a_id == row.subject_b_id: return`.**
   `test_weekly_order_con_a_uguale_b_non_vincola_nulla` rosso:
   `assert dim_con == dim_senza` fallisce, `(64, 67) != (60, 62)` — la riga
   posta comunque due `AddMinEquality` e un confronto ridondanti.

2. **Rimosso `if not a or not b: return`.**
   `test_weekly_order_materia_assente_non_crea_vincoli` rosso:
   `solver.Solve(model)` torna `INFEASIBLE` invece di
   `OPTIMAL`/`FEASIBLE` — `AddMinEquality` con letterali vuoti produce un
   modello infattibile (non un'eccezione Python, come avevo ipotizzato
   nella prima stesura del docstring: corretto per riflettere la misura,
   non l'attesa).

3. **Rimosso `signature=rep`** dalle due chiamate a `subject_activities`
   (tradotto sull'unione, come il derivatore rotto del piano).
   `test_weekly_order_posta_per_firma_di_settimana` rosso: lo scenario
   costruito apposta (a1/b1 attivi solo settimana 0, a2/b2 solo settimana 1,
   a1 forzata tardi e b1 presto dentro la settimana 0, a2 forzata presto ma
   fuori settimana) passa da `INFEASIBLE` (corretto: la violazione dentro
   la sola firma 0 e' rifiutata) a `OPTIMAL` (rotto: l'unione nasconde la
   violazione di a1/b1 dietro la posizione presto di a2).

4. **Condizione del primo ramo mutata da `or` a `and`**
   (`if FA is None and FB is None:`). `test_adr018_ramo_secco_vieta_la_libera_dopo_la_congelata`
   rosso: `TypeError: Linear constraints do not accept None as argument` —
   con `FA is None, FB is not None` lo scenario cade nel ramo disgiuntivo,
   che tenta `model.Add(prima_a >= FA)` con `FA = None`.

5. **Rimosso il ramo disgiuntivo** (sempre vincolo secco, indipendentemente
   da `FA`/`FB`). `test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo`
   rosso: `soluzione.status == 'INFEASIBLE'` invece di
   `OPTIMAL`/`FEASIBLE` — il vincolo secco pretende `prima_a <= prima_b`,
   cioe' un'attivita' di A a `pos = 0`, la stessa cella gia' occupata dalla
   congelata di B: bloccato da `structural:occupation`, sempre infattibile.

## Deviazioni dal brief

Nessuna deviazione sostanziale. Un solo dettaglio corretto rispetto alla mia
prima bozza di docstring (non rispetto al brief): avevo scritto che
`AddMinEquality` con lista vuota "solleva un errore"; misurato, produce
invece un modello `INFEASIBLE` — il docstring del test 2 e' stato corretto
per riflettere il comportamento osservato.

## Verifica finale

```
venv/bin/pytest tests/test_solver_subject_order.py -q
6 passed

venv/bin/pytest -q
351 passed, 4 skipped
```

Baseline dichiarata nel brief: 340 passed, 4 skipped. Delta: **+11** (6 test
dedicati + 5 seed di `test_famiglia` per `WEEKLY_ORDER`), stessi 4 skip di
prima — nessuno skip nuovo, quindi il derivatore non e' mai vacuo sui cinque
seed del banco.
