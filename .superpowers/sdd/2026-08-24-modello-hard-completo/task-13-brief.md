# Task 13 — `IMPOSED_SUCCESSION`

Implementatore. Worktree `modello-hard-completo`, HEAD `84a2aca`. Python:
`venv/bin/pytest`. Baseline: **354 passed, 4 skipped** (i conteggi del piano
sono vecchi, ignorali). Docstring e commenti in italiano senza accenti,
identificatori in inglese. `domain/analysis/` **non si tocca mai**.

Piano: `docs/superpowers/plans/2026-08-24-modello-hard-completo.md`, sezione
**Task 13** (riga 3095). Leggilo, ma **il suo derivatore e' rotto e il suo
builder e' incompleto su ADR-018**: qui sotto c'e' la versione corretta,
gia' misurata.

## 0. Leggi prima

1. `domain/analysis/checkers/subject_constraints.py`, `ImposedSuccessionChecker`
   (righe 191-208) e `_SubjectChecker.check`, `_placed_of`, `_half`. **E'
   l'autorita'.**
2. `domain/solver/builders/subject_order.py` — il file dove aggiungerai il
   builder; leggi `WeeklyOrderBuilder` per il trattamento ADR-018 gia'
   adottato e il principio che lo governa.
3. `domain/solver/builders/subject_buckets.py` — `_post_cross`,
   `residual_cap`, `subject_literals` / `subject_bucket`.
4. `tests/solver_harness.py`, `_derive_weekly_order` — lo stile del
   derivatore per firma, con la guardia di violabilita' e l'assert sulle
   precondizioni.

⚠ **Il checker ha due semantiche in una riga**, e non ha nessuna guardia
d'uscita:

```python
delay = row.param or 1
if row.subject_a_id == row.subject_b_id:
    halves = [(_half(...), p.activity_id) for p in a]
    for (h1, a1), (h2, a2) in zip(halves, halves[1:]):
        if h2 - h1 > delay: yield finding(..., gap=h2-h1, max_gap=delay)
else:
    b_halves = [_half(...) for p in b]
    for pa in a:
        ha = _half(pa)
        if not any(0 < hb - ha <= delay for hb in b_halves):
            yield finding(..., [pa.activity_id], max_gap=delay)
```

⚠⚠ **Con `b` vuoto non esce: `any(...)` su lista vuota e' falso, quindi
*ogni* occorrenza di A e' una violazione.** `WeeklyOrderChecker` invece esce
(`not a or not b`). **I checker di questa famiglia non sono uniformi**: non
ragionare per analogia, leggi questo.

---

## 1. Cosa consegnare

- `domain/solver/builders/subject_order.py`: `ImposedSuccessionBuilder`
  (`T.IMPOSED_SUCCESSION`), nello stesso file.
- `tests/solver_harness.py`: **un** derivatore per `ST.IMPOSED_SUCCESSION`,
  che crea **entrambe** le forme di riga.
- `tests/test_solver_subject_order.py`: i test nuovi.
- `tests/test_solver_registry.py`: aggiungere la chiave e aggiornare la
  docstring.

Solo il Task 13. Niente `HALF_DAY_GAP` (Task 14) ne' i `PARTS_*` (Task 15).

---

## 2. Il builder

Sia `n = ctx.grid.days_per_cycle * 2` (le mezze giornate del ciclo) e
`delay = row.param or 1`.

### Ramo A = B

Il checker guarda gli scarti fra occorrenze **consecutive**. Equivale a: per
ogni coppia di mezze giornate **occupate consecutive** `u < w` (nessuna
occupata in mezzo), `w - u <= delay`. Si dice senza ordinare, con una
clausola per coppia:

```
per ogni u, per ogni w > u + delay:
    AddBoolOr([sa[u].Not(), sa[w].Not()] + [sa[m] for m in range(u+1, w)])
```

dove `sa[h] = vocab.subject_bucket(keys, A, "half", h, signature=rep)`.
Salta le mezze giornate senza alcun letterale (`sa[h]` sarebbe costante 0 e
la clausola banale).

**ADR-018 (Ruling 92)**: salta la coppia `(u, w)` se una **congelata** di A
occupa `u`, una occupa `w`, e **nessuna congelata** occupa una mezza giornata
strettamente in mezzo. In quel caso la coppia e' gia' una violazione della
baseline, e la clausola chiederebbe a una libera di infilarsi in mezzo —
cioe' di **riparare il passato**, che ADR-018 vieta. In tutti gli altri casi
la clausola si posta: ⚠ in particolare **non** si salta quando uno solo dei
due estremi e' congelato, perche' li' l'altro estremo e' una decisione.

Per sapere se una congelata occupa la mezza giornata `h`:
`any(aid not in ctx.free for aid, _ in vocab.subject_literals(keys, A, "half", h, signature=rep))`.

### Ramo A != B

Il checker chiede: **per ogni occorrenza** di A esiste una B strettamente
dopo, entro `delay` mezze giornate.

⚠ **Non usare l'indicatore aggregato `sa[u]` come trigger.** Il finding e'
per **occorrenza** (`[pa.activity_id]`), quindi:

- una **congelata** di A senza B nella finestra ha gia' il suo finding nella
  baseline, e chiedere a una libera di B di andarla a salvare e' una pretesa
  di riparazione → quel trigger non si posta;
- una **libera** di A nella stessa mezza giornata produrrebbe un finding
  **nuovo**, col proprio id → quel trigger **si posta**.

Quindi il trigger e' il singolo letterale, non l'aggregato:

```
per ogni u in range(n):
    finestra = tutti i letterali di B nelle mezze giornate (u, min(u+delay, n-1)]
    se una congelata di B occupa una di quelle mezze giornate:
        continue        # clausola gia' vera per costante
    per (aid, lit) in subject_literals(keys, A, "half", u, signature=rep):
        se aid in ctx.free:
            AddBoolOr([lit.Not()] + finestra)
```

Usa i letterali di B direttamente (`subject_literals`), non
`subject_bucket`: evita una variabile derivata per mezza giornata, e la
clausola e' esattamente la stessa.

⚠ Con la finestra **vuota** la clausola diventa `lit.Not()`, cioe' vieta a
quella libera di A di stare li'. E' corretto e voluto: e' un divieto, non
una pretesa. Puo' rendere il modello INFEASIBLE — ADR-018 lo concede, come
gia' scritto per `ForbiddenSequenceBuilder`.

---

## 3. Il derivatore — misurato, non da inventare

Il derivatore del piano crea **solo** righe A = B (quindi il ramo incrociato
resterebbe senza banco di prova), si ferma alla prima con `return`, deriva
sull'**unione** delle settimane e non ha guardia di violabilita'. Da
riscrivere per intero.

Per ogni classe:

**Righe A = B**, una per materia presente:
- per ogni firma, prendi le mezze giornate delle occorrenze di quella materia
  **attive in quella firma**, ordinate; se sono meno di due, quella firma non
  dice nulla;
- `param` = **massimo fra le firme** del massimo scarto fra mezze giornate di
  occorrenze consecutive, e almeno 1;
- **guardia di violabilita'**: scarta se `param >= n - 1` — con un ritardo
  cosi' grande nessuna coppia dentro la settimana puo' sforare, e la riga
  sarebbe inviolabile;
- se nessuna firma ha almeno due occorrenze, niente riga.

**Righe A != B**, una per coppia ordinata di materie distinte:
- per ogni firma dove A ha occorrenze: **se B non ne ha, la riga non e'
  derivabile** (il checker segnerebbe *ogni* A come violazione — vedi §0) →
  scarta la coppia;
- altrimenti, per ogni occorrenza di A calcola lo scarto **minimo positivo**
  verso una occorrenza di B; se per una qualunque A non esiste nessuna B dopo
  di se', la coppia si scarta;
- `param` = massimo di quei minimi su tutte le firme e tutte le A, almeno 1;
- stessa guardia `param >= n - 1`.

**Accumula**: niente `return` alla prima riga; restituisci il numero di righe
create.

Aggiungi in testa l'assert sulla precondizione, come in `_derive_weekly_order`:
`assert not ClassPart.objects.exists(), (...)` — il derivatore filtra su
`klass.pk`, il checker espande a `{class_id, *parts}`.

**Numeri che questa formulazione deve riprodurre** (40 seed, misurati prima
di scriverti): **0 vacui**, **0 testimoni violati**, **4-12 righe** per seed,
**entrambe le forme su tutti e cinque i seed del banco** (A=B: 3-6 righe,
A!=B: 1-3), potere vincolante col builder assente **39/40**. Se non li
riproduci, dillo nel report. **Niente numeri in docstring** (Ruling 50):
vanno nel report.

---

## 4. I test

Niente `test_imposed_succession_sul_banco`: `test_solver_witness.py::test_famiglia`
li genera gia' (Ruling 16, sesta applicazione).

**Forma obbligatoria (Ruling 85)**: il test che dimostra che il vincolo
*morde* si scrive **forzando la violazione e attendendo `INFEASIBLE`**, mai
risolvendo e guardando la soluzione. Nel Task 12 la forma «risolvi e
asserisci» restava verde col builder reso no-op, in modo deterministico.

Servono almeno:

1. **A = B morde** — forma avversaria: due occorrenze forzate a piu' di
   `delay` mezze giornate di distanza → `INFEASIBLE`.
2. **A = B, la coppia con qualcosa in mezzo e' legale**: tre occorrenze, la
   terza a colmare il buco → FEASIBLE. Difende la parte `+ [sa[m] ...]` della
   clausola, che senza questo test si potrebbe cancellare.
3. **A != B morde** — avversaria: una A forzata dove non c'e' nessuna B nella
   finestra → `INFEASIBLE`.
4. **A != B, la B nella finestra basta**: stesso scenario con una B forzata
   dentro la finestra → FEASIBLE.
5. **ADR-018, A = B**: due congelate a distanza > delay senza congelate in
   mezzo, piu' almeno una libera. Il modello **non** dev'essere INFEASIBLE, e
   la libera non dev'essere costretta a infilarsi in mezzo.
6. **ADR-018, A != B**: una congelata di A senza B in finestra (baseline gia'
   violata) piu' una **libera** di A nella stessa mezza giornata. Il modello
   non dev'essere INFEASIBLE **e** la libera non deve poter restare li' se
   nessuna B puo' arrivare nella sua finestra — cioe' il trigger per
   letterale, non per aggregato. ⚠ E' il test che distingue il trattamento
   corretto da «salta la clausola intera»: verifica per mutazione che
   saltandola questo test cada.

**Criterio di mutazione (Ruling 89)**: ogni test che afferma la **presenza**
di un vincolo dev'essere rosso con `post()` reso no-op. I test che affermano
un'**assenza** (guardie) non possono esserlo, e vanno difesi dalla mutazione
mirata sulla loro guardia. Nel report elenca ogni mutazione con l'esito.

---

## 5. Chiusura

- `venv/bin/pytest -q`: **354 + i tuoi**, sempre **4 skipped**. Uno skip nuovo
  = derivatore vacuo su un seed del banco: segnalalo, non aggiustare il test.
- **Non committare, non pushare.** Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/task-13-report.md`.
- Se il brief contraddice il codice, **vince il codice**: segnalalo.
