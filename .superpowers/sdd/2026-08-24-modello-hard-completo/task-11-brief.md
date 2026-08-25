# Task 11 — `MAX_HOURS_DAY`, `MAX_HOURS_HALF_DAY`, `FORBIDDEN_SEQUENCE`

Implementi il Task 11 del piano
`docs/superpowers/plans/2026-08-24-modello-hard-completo.md` (riga 2709).
Lavori nel worktree `.claude/worktrees/modello-hard-completo` e **non ne esci**.
Test con `venv/bin/pytest` dalla radice del worktree. **Non fare commit.**

Stato di partenza pulito: **315 passed, 4 skipped**. I quattro skip sono
onesti e preesistenti (`arrival_departure` seed 2 e 4,
`structural:site_transition` seed 3, `same_half_day_incompatible` seed 2).

## Prima di scrivere una riga

Leggi, in quest'ordine:

1. `domain/analysis/checkers/subject_constraints.py` — **il checker e' la
   verita'**. In particolare `_MaxHours.violations` (righe 149-159) e
   `ForbiddenSequenceChecker.violations` (righe 135-142). Ogni affermazione che
   scriverai in una docstring dev'essere verificata **li'**, non contro il piano.
2. `domain/solver/builders/subject_buckets.py` e `domain/solver/builders/base.py`
   — lo scheletro del Task 10, su cui questo task si appoggia.
3. `tests/solver_harness.py`, righe 433-640 — `_collocazioni`, `_ci_stanno`,
   `_coppia_violabile` e i tre derivatori del Task 10. **Sono il modello da
   imitare**, guardie comprese.
4. Il fondo di `.superpowers/sdd/2026-08-24-modello-hard-completo/progress.md`,
   Rulings **54-62**: sono le decisioni gia' prese su questo task, misurate
   prima del dispatch. Non sono suggerimenti.

## Il difetto ricorrente di questo branch

Sette volte su questo branch il difetto non e' stato codice sbagliato, ma una
**proprieta' dichiarata vera che non lo era**, scoperta falsa solo
controllandola contro il checker o contro i dati. Corollario operativo: **un
test verde non e' copertura**. Un caso di banco che passerebbe anche col
builder spento e' un difetto, non un successo.

⚠ **Il piano, in questo task, e' sbagliato in tre punti — gia' misurati.** Le
sonde stanno nelle Rulings 54-57. Non ripetere il codice del piano alla lettera.

## Cosa costruire

### 1. `_Bucketed`, estratto (Ruling 58)

`_BucketIncompatible` (Task 10) e il nuovo `_MaxHoursSubject` hanno bisogno
degli stessi tre elementi: `KIND`, `buckets(ctx)` e l'assert
`assert self.KIND in ("day", "half")`. **Non duplicarli**: estrai
`_Bucketed(SubjectBuilder)` in `subject_buckets.py` e falla ereditare da
entrambi. L'assert esiste perche' `vocab.bucket_of` tratta **ogni**
`kind != "day"` come mezza giornata: senza, una sottoclasse che dimentichi
`KIND` prende in silenzio la semantica sbagliata.

### 2. I due tetti di ore

⚠ **`_MaxHours.violations` somma solo `a`, mai `b`** — anche quando A != B, il
tetto vale sulle ore della **sola** materia A. Sommare anche B sarebbe un
vincolo diverso e piu' stretto.

Lo schema del piano (Step 3) e' corretto nella sostanza: `residual_cap` sui
termini `(duration_minutes, aid, letterale)` di `subject_literals`, tetto
`row.param`, `if row.param is None: return`. Tienilo, con `_Bucketed` come base.

Scrivi in docstring, verificandola sul checker, **anche** la nota della Ruling
60: con A != B il gate di riga e la deduplicazione per `coinvolte` guardano
anche le attivita' di B, che a questo vincolo non servono; l'effetto e' al piu'
una riga postata due volte identica, mai una saltata.

### 3. `ForbiddenSequenceBuilder`

Lo schema del piano e' corretto. Due punti da **dichiarare e difendere**:

- il `continue` quando `pa` e `pb` sono **entrambe** congelate e' legittimo — e'
  `any_free`, «un fatto, non una decisione» — e **non** e' il `continue` su un
  tetto che le Rulings 14/23/28 vietano. Scrivi la distinzione;
- con **una sola** congelata la clausola forza a zero il letterale libero, e
  **puo' rendere il modello INFEASIBLE** se quella libera non ha altro posto
  dove andare. E' cio' che ADR-018 concede testualmente. Per il precedente del
  Task 10 (Minor 5), una proprieta' scritta per non essere rilitigata **deve
  avere il suo test**: esibisci quell'INFEASIBLE.

## I tre derivatori — qui il piano e' sbagliato

Il piano crea righe che **nessun piazzamento puo' violare**. Misurato su 60
seed, prima del dispatch:

| derivatore del piano | seed vacui |
|---|---|
| `max_hours` secchio giornata | **19/60** |
| `max_hours` mezza giornata | **17/60** |
| `forbidden_sequence` | **10/60** |

Il **seed 2 e' vacuo in tutti e tre** — e i seed del banco sono 1-5. Senza
correzione, **tre dei quindici casi** sarebbero verdi incapaci di fallire.

Ogni derivatore restituisce il proprio **potere vincolante** (numero di righe
create capaci di essere violate); `run_family` salta con `pytest.skip` se e'
zero. Vale la convenzione dichiarata in `deriver()` (riga 240 dell'harness).

### `_derive_max_hours_subject` — tre correzioni

1. **`param` per firma di settimana, non sull'unione** (Ruling 56).
   `_try_place` permette a due attivita' di settimane disgiunte di condividere
   la cella, e il checker valuta uno `ScheduleState` **per firma**. Calcola
   `param` come massimo, sulle firme, della somma massima per secchio **dentro
   quella firma**.
2. **Guardia di violabilita'** (Ruling 55), due condizioni congiunte:
   - il **totale per firma** della coppia (classe, materia) deve superare
     `param` — se non lo supera, nessun piazzamento puo' superarlo, e con una
     sola attivita' questo e' automatico perche' `param` e' la sua stessa
     durata;
   - almeno una coppia co-attiva deve poter partire nello **stesso secchio**:
     riusa `_ci_stanno(w, kind, a, b)`, non riscriverlo. (Se nessuna coppia ci
     sta, il massimo raggiungibile e' la durata piu' lunga, che `param` domina
     per costruzione.)
3. **Accumula su tutte le coppie (classe, materia)**, non `return` alla prima —
   come fanno i tre derivatori del Task 10.

Con queste tre: **0/60 seed vacui**, 2-6 righe per seed (misurato).

### `_derive_forbidden_sequence` — tre guardie

Al seed 2 la vacuita' e' la forma piu' cruda: la materia scelta come antecedente
**non ha alcuna attivita'** in quella classe (`|A| = 0`), quindi
`_placed_of` e' vuota e il checker non entra mai nel ciclo. «Mai adiacente nel
testimone» e' banalmente vero per una materia assente.

1. **entrambe** le materie devono avere attivita' in quella classe;
2. una coppia (attivita' di A, attivita' di B) dev'essere **co-attiva** in
   qualche firma di settimana;
3. l'adiacenza dev'essere **geometricamente raggiungibile**: esiste `sa`
   ammessa per un'attivita' di A tale che `sa + durata_slots` sia ammessa per
   una di B. Usa `_collocazioni`, che gia' applica le regole di `_try_place`
   (dentro la giornata, niente scavalcamento dell'intervallo per chi lo
   rispetta). Scrivi un helper accanto a `_ci_stanno`, con la stessa forma di
   docstring: **condizione necessaria, non sufficiente**, e la direzione in cui
   e' giusto sbagliare.

Piu' l'accumulo su tutte le coppie. Con queste: **0/60 seed vacui**, 5-9 righe
per seed (misurato).

⚠ Non mettere nelle docstring i numeri qui sopra (Ruling 50): sono misure
datate, e stanno nel registro. Scrivi la **proprieta'**, non il numero.

## I test — `tests/test_solver_subject_maxhours.py`

**Non scrivere `test_sul_banco`** (Ruling 61, quarta applicazione):
`tests/test_solver_witness.py::test_famiglia` parametrizza gia' su
`sorted(DERIVERS, key=str) × [1..5]`, quindi registrare i tre derivatori genera
gia' i quindici casi. In testa al modulo metti la nota ⚠ nella **stessa forma**
di `tests/test_solver_sites.py` e `tests/test_solver_max_presence.py` — copiala,
non inventarne una nuova.

⚠ `tests/test_solver_time_counting.py` ne ha ancora due: sono residui anteriori
alla Ruling 16, **non un precedente da imitare**. Non toccarli.

Scrivi invece i test mirati, tutti su `mini_school()`:

- i due del piano (`test_max_hours_day_limita_la_materia`,
  `test_forbidden_sequence_vieta_l_adiacenza`) — verificali **per mutazione**:
  spegnendo il `post` del builder corrispondente devono fallire. Se uno passa
  comunque, non e' un test, e va reso discriminante;
- `MAX_HOURS_HALF_DAY` con un tetto che morde solo su una meta' giornata;
- **ADR-018 su `MAX_HOURS`**: due congelate che sforano gia' il tetto piu' una
  libera. Il modello **non** dev'essere INFEASIBLE, e la libera non deve
  aggiungersi a quel secchio (`residual_cap` clampa a zero);
- **ADR-018 su `FORBIDDEN_SEQUENCE`**, i tre rami: entrambe congelate (nessun
  vincolo postato — verificalo, non darlo per scontato); una congelata e una
  libera (la libera evita l'adiacenza); e il caso dichiarato sopra in cui la
  clausola rende il modello **INFEASIBLE**;
- `FORBIDDEN_SEQUENCE` con **A = B**: il checker lo permette (`b = a`,
  con la guardia `pb.activity_id != pa.activity_id`), e il builder ha il
  `if pb == pa: continue` che gli corrisponde. Nessun derivatore lo crea
  (`if a.pk != b.pk`), quindi se non lo testi qui non e' coperto — e' la Minor 4
  del Task 10, in anticipo.

Aggiorna `tests/test_solver_registry.py::test_i_builder_tradotti_finora` con le
tre chiavi nuove, e il docstring che elenca i task.

## Alla fine

`venv/bin/pytest -q` per intero, e `-rs` per vedere le ragioni degli skip.
Attesi: **315 + i test che aggiungi**, con **4 skip** — se ne compaiono altri,
spiega quale seed salta e **perche' quella riga e' davvero inviolabile**.

⚠ I numeri attesi scritti nel piano (`291 passed`, `17 test`) sono **stantii**
(Ruling 62). Ignorali e riporta quelli che misuri.

Rapporto in sei punti:

1. cosa hai costruito, file per file;
2. la **prova per mutazione** di ogni test mirato: quale `post` hai spento e
   quali test sono falliti. Se un test non e' fallito, dillo;
3. il potere vincolante misurato delle tre famiglie nuove sui seed 1-5
   (spegnendo il `post` del builder: quanti dei cinque casi falliscono?), e se
   hai ripetuto la misura, la varianza;
4. gli skip finali, con seed e motivo;
5. i numeri della suite;
6. **cosa non hai fatto o non hai verificato**, senza arrotondare. E' la
   sezione piu' utile del rapporto: non arrotondarla.
