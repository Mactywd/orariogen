# Task 14 — `HALF_DAY_GAP`

Implementatore. Worktree `modello-hard-completo`, HEAD `e10a2cc`. Python:
`venv/bin/pytest`. Baseline: **365 passed, 4 skipped** (i conteggi del piano
sono vecchi). Docstring e commenti in italiano senza accenti, identificatori
in inglese. `domain/analysis/` **non si tocca mai**.

Piano: sezione **Task 14** (riga 3226). ⚠ **La sua premessa e' sbagliata e il
suo builder ha un buco**: leggi il piano per il contesto, ma implementa questo.

## 0. Leggi prima

1. `domain/analysis/checkers/subject_constraints.py`, `HalfDayGapChecker`
   (righe 211-229) — **l'autorita'**.
2. `domain/solver/builders/subject_buckets.py` — `_post_separable` e
   `_post_cross`, che riuserai; leggi le loro docstring per intero, sono la
   giustificazione di ADR-018 che erediti.
3. `domain/solver/builders/subject_order.py` — dove vivono i due builder
   d'ordine gia' scritti (`WeeklyOrderBuilder`, `ImposedSuccessionBuilder`).
4. `tests/solver_harness.py`, `_derive_imposed_succession` — lo stile del
   derivatore per firma con entrambe le forme di riga e l'assert sulle
   precondizioni.

Il checker:

```python
same = row.subject_a_id == row.subject_b_id
merged = [(_half(p), p.activity_id, "a") for p in a]
if not same:
    merged += [(_half(p), p.activity_id, "b") for p in b]
merged.sort()
for (h1, a1, s1), (h2, a2, s2) in zip(merged, merged[1:]):
    crossed = same or s1 != s2
    if crossed and a1 != a2 and h2 - h1 < row.param:
        yield finding(..., gap=h2-h1, min_gap=row.param)
```

---

## 1. La premessa del piano e' sbagliata: **e' esatto, non conservativo**

Il piano intitola questo task «il conservativo dimostrato» e sostiene che
vincolare **tutte** le coppie incrociate sia piu' stretto del checker, che
vincola le sole **consecutive**. Le due regole sono **equivalenti**.

Dimostrazione: se esiste una coppia incrociata a distanza `< param`, ne
esiste una **adiacente** altrettanto corta. Si prende la coppia incrociata
corta con il minor numero di elementi in mezzo; se qualcosa c'e' in mezzo,
quel qualcosa ha sorgente `a` o `b`, quindi forma con **uno** dei due estremi
una coppia incrociata di distanza non maggiore e con meno elementi in mezzo —
contro la minimalita'. Quindi la minima e' adiacente.

Verificato prima di scriverti su **200 000** casi sintetici casuali: **zero
divergenze**.

Cosa cambia per te: il builder resta quello (e' corretto in entrambe le
letture), ma **la docstring deve dichiarare l'equivalenza con la
dimostrazione**, non una direzione conservativa. Non scrivere «piu' stretto,
mai piu' largo»: e' vero ma fuorviante, e questo progetto ha gia' pagato otto
volte le affermazioni piu' deboli o piu' forti del vero.

---

## 2. Il builder — riusa i due helper, non riscriverli

Il builder del piano posta a mano `a_u + a_w <= 1` su indicatori derivati
(`subject_bucket`), che e' **esattamente** la forma per cui esiste la tabella
a quattro rami di `_post_cross`. E **non ha alcun trattamento ADR-018**: con
due congelate nelle due mezze giornate il modello diventerebbe INFEASIBLE per
colpa del passato.

Ogni coppia di questo vincolo e' gia' uno dei due casi noti:

| caso | helper |
|---|---|
| A = B, **stessa** mezza giornata (`w == u`) | `_post_separable(ctx, model, v, A, "half", u, keys, rep)` |
| A = B, mezze giornate diverse | `_post_cross(ctx, model, v, A, "half", u, A, "half", w, keys, rep)` |
| A != B, `w == u` | `_post_cross(..., A, "half", u, B, "half", u, ...)` |
| A != B, `w > u` | **due** chiamate: `(A@u, B@w)` e `(B@u, A@w)` — il checker e' simmetrico, `crossed` non guarda il verso |

Il ciclo e' quello del piano: `for u in range(n)` e
`for w in range(u, min(u + param, n))`, con `n = days_per_cycle * 2`. Esce
subito se `row.param` e' falso (niente da vincolare).

⚠ `_post_cross` con A = B su **due secchi distinti** e' gia' cio' che
`TwoDaysBuilder` fa dal Task 10: e' un uso previsto, non un abuso.

**I due helper non sono piu' privati di un modulo**: rinominali
`post_separable` e `post_cross` (togli l'underscore), aggiorna le loro
chiamate in `subject_buckets.py` e le menzioni nelle docstring che li
nominano. Sono quattro righe; un import di un nome con underscore da un altro
modulo e' esattamente il genere di cosa che una review segnala.

⚠ Nota da scrivere in docstring: `_post_separable` giustifica il clamp a zero
con «`count` sta dentro `Finding.key`». Qui il finding porta `gap`/`min_gap`,
non `count` — ma la tupla `activities` cresce lo stesso, quindi la
conclusione regge per la stessa ragione. Dillo, non lasciarlo implicito.

Dove metterlo: `domain/solver/builders/subject_order.py`, accanto agli altri
due della famiglia.

---

## 3. Il derivatore

Il derivatore del piano crea solo righe A = B, si ferma alla prima con
`return`, deriva sull'**unione** delle settimane e non ha guardia di
violabilita'. Da riscrivere.

Per ogni classe, per ogni coppia **ordinata** di materie (A, B), **inclusa
A = B**:

- per ogni firma di settimana, costruisci `merged` con le occorrenze attive
  in quella firma (solo A se `same`, A e B altrimenti; con `same=False` salta
  la firma se una delle due e' vuota — li' il checker non produce nessuna
  coppia incrociata);
- calcola il minimo, su **tutte** le coppie incrociate (non solo le
  adiacenti — §1 dice che e' lo stesso, e derivare contro la regola del
  builder tiene onesta la dimostrazione), della distanza in mezze giornate;
- `param` = **minimo fra le firme** di quei minimi;
- guardie: niente riga se `param` e' `None` (nessuna coppia in nessuna
  firma), se `param < 1`, o se `param >= n` (piu' largo dell'intera
  settimana: inviolabile);
- accumula, restituisci il conteggio.

Aggiungi in testa l'assert `not ClassPart.objects.exists()`, come negli altri
due derivatori d'ordine.

**Numeri da riprodurre** (40 seed, misurati prima di scriverti): **0
testimoni violati**, **0-13 righe** per seed (il seed 33 e' vacuo, fuori dal
banco), potere vincolante col builder assente **36/40**, **4/5 nel banco** —
⚠ **il seed 2 non morde, in modo deterministico**. Non inseguirlo: e' in
linea con le altre famiglie (10/15 e 12-14/15 per le due delle sedi), e il
peso della dimostrazione lo porta il test avversario, non il banco.
Dichiaralo in docstring; **i numeri vanno nel report, non in docstring**
(Ruling 50).

---

## 4. I test — `tests/test_solver_half_day_gap.py`

Niente `test_half_day_gap_sul_banco`: `test_solver_witness.py::test_famiglia`
lo genera gia' (Ruling 16, settima applicazione). Copia in testa al modulo la
nota ⚠ che sta in testa a `tests/test_solver_subject_order.py`.

**Forma obbligatoria (Ruling 85)**: il test che dimostra che il vincolo morde
si scrive **forzando la violazione e attendendo `INFEASIBLE`**, con
`build_model` e `model.Add(ctx.x[...] == 1)`, mai risolvendo e guardando la
soluzione. La griglia di `mini_school` e' 5 giorni x 6 fasce con
`morning_end_slot = 4`, quindi la mezza giornata e'
`giorno * 2 + (fascia >= 4)`.

Servono almeno:

1. **A = B morde**: due occorrenze forzate a distanza `< param` → INFEASIBLE.
2. **A = B, la distanza giusta e' legale**: le stesse a distanza `>= param` →
   FEASIBLE. (Copre il builder che vieta tutto.)
3. **A = B, stessa mezza giornata**: due occorrenze forzate nella stessa
   mezza giornata con `param = 1` → INFEASIBLE. Difende il ramo `w == u`.
4. **A != B morde**, e **in entrambi i versi**: A prima di B e B prima di A,
   entrambi INFEASIBLE. Il checker e' simmetrico; senza la seconda chiamata a
   `post_cross` un verso resterebbe scoperto. ⚠ Verifica per mutazione che
   togliendo la seconda chiamata questo test cada.
5. **ADR-018**: due **congelate** a distanza `< param` (baseline gia'
   violata) piu' una libera. Il modello **non** dev'essere INFEASIBLE. Usa
   un'asserzione **strutturale** (fissa la libera in una cella legale e
   chiedi FEASIBLE), non «risolvi e guarda dove e' finita».

**Criterio di mutazione (Ruling 89)**: ogni test che afferma la **presenza**
di un vincolo dev'essere rosso con `post()` reso no-op; quelli che affermano
un'**assenza** vanno difesi da una mutazione mirata. Nel report elenca ogni
mutazione con l'esito.

---

## 5. Chiusura

- `venv/bin/pytest -q`: **365 + i tuoi**, sempre **4 skipped**. Uno skip nuovo
  = derivatore vacuo su un seed del banco: segnalalo, non aggiustare il test.
- Aggiungi `T.HALF_DAY_GAP` a `tests/test_solver_registry.py` e aggiorna la
  docstring.
- **Non committare, non pushare.** Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/task-14-report.md`.
- Se il brief contraddice il codice, **vince il codice**: segnalalo.
