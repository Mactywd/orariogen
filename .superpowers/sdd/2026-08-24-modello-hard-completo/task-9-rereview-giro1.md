# Task 9 — ri-review mirata del giro di correzione 1

Diff rivisto: `31ff9de..43c37ad`. Metodo: ogni affermazione qui sotto è
accompagnata dalla sonda che l'ha prodotta e, dove serve, dal caso di
controllo vicino. Tutte le sonde sono state eseguite in questo worktree come
file `tests/test_zz*.py` temporanei, poi **rimossi**; ogni file del repo
mutato per una sonda è stato **ripristinato bit-per-bit** (verificato con
`git status`, pulito in chiusura). Nessun commit.

**Verdetto complessivo: il Task 9 si chiude, con una Important da girare al
controller e tre Minor.** Le quattro cose del giro sono fatte, e tre delle
quattro sono verificate esatte con riproduzione indipendente. La Important
non è una regressione del solver: è un **derivatore che ha perso una guardia
di vacuità che il suo predecessore aveva**, e produce un caso di banco verde
che non può fallire — la quarta occorrenza dello stesso pattern su questo
piano. Costo della riparazione: tre righe.

---

## 1. Important 2 (Ruling 35) — `_derive_site_transition` e `duration_slots`

### **CHIUSA, e su un range più ampio di quello chiesto.**

**Riproduzione del difetto col codice pre-correzione.** Ripristinato
`tests/solver_harness.py` alla versione `31ff9de` e lanciato
`run_family("structural:site_transition", seed)` per i **seed 1-30**, senza
alcuna mutazione del builder:

```
E   AssertionError: il testimone stesso viola structural:site_transition (seed 15):
    [('site_transition', (1,), (1, 5), (('day', 2), ('gap_slots', 0), ('needed_slots', 1)))]
E   AssertionError: il testimone stesso viola structural:site_transition (seed 20):
    [('site_transition', (2,), (11, 19), (('day', 3), ('gap_slots', 0), ('needed_slots', 1)))]

2 failed, 15 passed, 43 skipped in 8.10s
```

Il seed 15 è quello che la review e il rapporto avevano trovato; il **seed 20
è nuovo**, mai riportato — la review si era fermata a 15. Il landmine era
quindi più esteso di quanto documentato.

**Con la correzione in albero, stessi 30 seed, entrambe le famiglie:**

```
57 passed, 3 skipped in 16.67s
SKIPPED structural:site_transition: derivazione vacua per il seed 3
SKIPPED structural:site_transition: derivazione vacua per il seed 23
SKIPPED structural:site_transition: derivazione vacua per il seed 29
```

Zero fallimenti «il testimone stesso viola» su 60 casi. Harness ripristinato
dopo la sonda.

**Verificata anche la formula, non solo l'esito.** `_distanza_sedi` con
`slot < slot2` restituisce `slot2 - slot - duration_slots(aid)`. L'ultima
fascia occupata da `aid` è `slot + d1 - 1`, quindi il `gap_slots` che il
checker calcolerà su quella adiacenza è `slot2 - (slot + d1 - 1) - 1 =
slot2 - slot - d1`: **coincide esattamente**, non è una maggiorazione
prudente. E `_coppie_sedi_vicine` prende il minimo su **tutte** le coppie a
sede diversa con chiave condivisa, che è un soprainsieme delle sole coppie
adiacenti nella sottosequenza del checker: il minimo sul soprainsieme è ≤ il
minimo sulle adiacenze reali, quindi la derivazione resta conservativa anche
quando in mezzo c'è una terza attività con sede. Le chiavi usate
(`w.tokens[aid]`) vengono da `activity_tokens`, **la stessa funzione** che
usa `ScheduleState`: nessuna chiave (aule comprese) può sfuggire al
confronto.

---

## 2. La riparazione parziale della fascia condivisa (Ruling 33)

### **CHIUSA. L'argomento dell'implementatore è vero, e la clausola è esatta, non più stretta.**

**Il checker, letto** (`domain/analysis/checkers/sites.py`):

```python
for (s1, site1, a1), (s2, site2, a2) in zip(sequence, sequence[1:]):
    if site1 != site2 and s2 - s1 - 1 < needed:
```

Con `s1 == s2` il termine è `-1`, che è `< needed` per **ogni** `needed >= 0`.
L'argomento regge. Di più: una fascia che contiene ≥ 2 sedi distinte produce
**sempre** almeno una coppia adiacente con sedi diverse nella sequenza,
qualunque sia l'ordine — quindi «due sedi distinte nella stessa cella» ⟺
«il checker emette un finding». La clausola del builder è quindi **esatta**,
non conservativa: non vieta niente che il checker permetta.

**Sonda diretta a `needed = 0, 1, 2`** (aula a `simultaneous_capacity = 2`,
griglia 1×1, due attività di classi e docenti diversi, sedi diverse). Per ogni
soglia: cosa dice il solver, e cosa dice il checker sullo **stesso**
piazzamento imposto a mano:

```
NEEDED=0 solver=INFEASIBLE checker_hard=1 [{'day': 0, 'gap_slots': -1, 'needed_slots': 0}]
NEEDED=1 solver=INFEASIBLE checker_hard=1 [{'day': 0, 'gap_slots': -1, 'needed_slots': 1}]
NEEDED=2 solver=INFEASIBLE checker_hard=1 [{'day': 0, 'gap_slots': -1, 'needed_slots': 2}]
```

A `needed = 0` il solver rifiuta e il checker boccia: **postare la clausola
anche a soglia zero è corretto**, non è un vincolo di troppo. E l'uscita
anticipata non la salta — verificato sia leggendo (`if not needed: continue`
sta **dopo** il blocco `s == t`) sia comportamentalmente (la riga
`NEEDED=0 solver=INFEASIBLE` è la prova: con l'uscita anticipata sarebbe
`OPTIMAL`).

**Due casi di controllo**, entrambi necessari perché la clausola non sia
troppo larga:

```
CONTROLLO capienza=1 needed=0     solver=INFEASIBLE   (per structural:occupation, altra ragione)
CONTROLLO stessa_sede needed=0    solver=OPTIMAL {1: (0, 0), 2: (0, 0)}
```

Il secondo è quello che conta: due attività **della stessa sede** sulla stessa
cella a capienza 2, con una seconda sede comunque esistente nell'istituto —
il solver le piazza insieme. La clausola colpisce solo le sedi diverse.

**La prova RED del rapporto, riprodotta.** Rimosso il solo blocco `s == t`
dal builder:

```
FAILED tests/test_solver_sites.py::test_site_transition_due_sedi_sulla_stessa_fascia_a_capienza_cumulativa
E       AssertionError: {'attivita': 2, 'libere': 2, 'variabili': 2, 'constraint': 2, ...}
E       assert 'OPTIMAL' == 'INFEASIBLE'
1 failed, 5 passed in 0.75s
```

Identica a quella del rapporto. Builder ripristinato.

### `MaxSiteChangesBuilder` — **toccato**, ma non per la ragione vietata

Confronto **di AST** dei corpi (docstring esclusi) fra `31ff9de` e `HEAD`,
`domain/solver/builders/time_sites.py`:

```
MODIFICATO MaxSiteChangesBuilder.post
MODIFICATO SiteTransitionBuilder.build
IDENTICO   _coppie_di_sede
IDENTICO   _frozen_site_changes
IDENTICO   _sedi
NUOVO      _sedi_raggiungibili
```

`MaxSiteChangesBuilder.post` **è** modificato. La modifica non è però la
riparazione `s == t` vietata dalla Ruling 33: è **solo** il filtro
`_sedi_raggiungibili` sui cicli `sa`/`sb` (punto 4 del giro), dichiarato
apertamente dal rapporto («usato al posto della lista completa delle sedi nei
cicli `sa`/`sb` di **entrambi** i builder»). Nessuna occultazione.

**Verificato che il filtro è semantica-preservante su questo builder**, per
due vie. Analitica: `Vocabulary.site_occupied` costruisce i letterali da
`ctx.by_cell` filtrati per `site_id`, e con lista vuota
`_max_or_zero` fa `Add(var == 0)` — la variabile è **inchiodata a zero**;
`_sedi_raggiungibili` legge lo **stesso** `by_cell` senza filtrare per firma,
quindi è un soprainsieme dei siti davvero presenti e non può mai escludere un
sito raggiungibile. Il letterale escluso rende
`AddBoolOr([c] + [l.Not() for l in lits])` vero per costruzione, `c` resta
libera e compare solo in vincoli `<=`: il solver la mette a 0. Empirica:
`run_family` per entrambe le famiglie, seed 1-15, **col filtro
monkeypatchato a `set(_sedi(ctx))`** (cioè disattivato):

```
29 passed, 1 skipped in 8.33s
```

Identico all'albero. Nessuna divergenza di esito.

### La nota nel docstring dice il vero — **dimostrato**

Il docstring afferma che sotto capienza cumulativa il conteggio del checker
dipende dall'**ordine di inserimento** in `ScheduleState.occupancy`. Non è
un'ipotesi: `place()` fa `self.occupancy[(key, day, s)].append(...)` e
`ScheduleState.build` itera un queryset `Activity.objects...` **senza
`order_by`**, quindi l'ordine è quello che il DB restituisce.

**Sonda.** Due istanze **fisicamente identiche** — aula a capienza 2, un
giorno × due fasce, due attività di sedi diverse alla fascia 0 e una di sede
A alla fascia 1, riga `MAX_SITE_CHANGES` con `per_day = 1` — che
differiscono **solo** per l'ordine di creazione delle due attività
compresenti:

```
ORDINE=AB cambi=[{'day': 0, 'changes': 2, 'max_changes': 1}] n_finding=1
ORDINE=BA cambi=[]                                            n_finding=0
```

Stesso orario, stesso vincolo: una volta è illegale e una volta no. La
Ruling 33 («non tradurre un artefatto») è giustificata, la voce aggiunta a
CLAUDE.md è accurata, e il docstring non esagera.

---

## 3. Il potere vincolante dei due derivatori (Ruling 34)

Metodo, identico a quello della review: builder reso no-op via `monkeypatch`
(`SiteTransitionBuilder.build` / `MaxSiteChangesBuilder.post` → `None`),
`run_family` su 15 seed, si conta MORDE (fallisce) / SKIP (vacuo) /
verde-ma-inerte. **Controllato anche a quale passo di `run_family` avviene il
fallimento** — solo il passo 3 (riga 304, «accetta un piazzamento che il
checker boccia») conta come morso; i passi 1 e 2 sarebbero difetti del
derivatore, non potere.

### `structural:site_transition` — **confermato, e migliore del dichiarato**

Sei esecuzioni consecutive:

```
run1: 13 failed, 1 passed, 1 skipped | step1=0 step2=0 step3=13
run2: 14 failed,           1 skipped | step1=0 step2=0 step3=14
run3: 14 failed,           1 skipped | step1=0 step2=0 step3=14
run4: 14 failed,           1 skipped | step1=0 step2=0 step3=14
run5: 13 failed, 1 passed, 1 skipped | step1=0 step2=0 step3=13
run6: 13 failed, 1 passed, 1 skipped | step1=0 step2=0 step3=13
```

**13-14 su 15**, sempre 1 solo skip (seed 3), **zero** fallimenti ai passi 1 e
2. Contro l'**1/15** misurato dalla review sulla formulazione in albero
precedente. La dichiarazione dell'implementatore (12-14/15) è confermata e
anzi il limite inferiore osservato qui è 13.

### `T.MAX_SITE_CHANGES` — **10/15 confermato, con varianza zero**

Sei esecuzioni consecutive:

```
run1..run6: 10 failed, 5 passed | step1=0 step2=0 step3=10   (identico tutte e sei)
```

**10/15, mai 11, mai 9.** Contro lo 0/15 della formulazione precedente. Il
numero del rapporto è esatto e la sua stabilità pure.

### Il divario 10-contro-12: reale o rumore? — **né l'uno né l'altro, ma c'è un difetto vero sotto**

L'ipotesi dell'implementatore («il docente è scelto per numero totale di
attività, non per idoneità a produrre sedi multiple») **è parzialmente
giusta, e la parte giusta è dimostrabile**. Ho isolato *perché* ciascuno dei
cinque seed inerti è inerte:

```
SEED 1  potere=1 docente=6 n_att=5  giorni=[0, 2]        sedi_distinte=1  n_sites=2
SEED 6  potere=1 docente=3 n_att=6  giorni=[0,1,2,3,4]   sedi_distinte=2  n_sites=2
SEED 7  potere=1 docente=3 n_att=5  giorni=[0,1,2,3]     sedi_distinte=2  n_sites=2
SEED 10 potere=1 docente=4 n_att=6  giorni=[1,2,3,4]     sedi_distinte=2  n_sites=2
SEED 14 potere=1 docente=5 n_att=5  giorni=[0,1,2]       sedi_distinte=2  n_sites=2
```

E cosa fa il mutante su ciascuno (sedi distinte del docente scelto, per
giornata, nella soluzione trovata col builder spento):

```
SEED 1  sedi_testimone=1  soluzione_per_giorno={0: 1, 1: 1, 2: 1}
SEED 6  sedi_testimone=2  soluzione_per_giorno={0: 1, 1: 1, 3: 1, 4: 1}
SEED 7  sedi_testimone=2  soluzione_per_giorno={1: 1, 2: 1, 3: 1}
SEED 10 sedi_testimone=2  soluzione_per_giorno={0: 1, 1: 1, 2: 1, 3: 1, 4: 1}
SEED 14 sedi_testimone=2  soluzione_per_giorno={0: 1, 1: 1}
```

Due cause **diverse**:

- **Seed 1 è inerte per costruzione, non per fortuna.** Il docente scelto ha
  attività solo nei giorni 0 e 2; il derivatore assegna
  `sites[day % len(sites)]` con `len(sites) == 2`, quindi entrambi i giorni
  ricevono **la stessa sede** e il docente finisce con **una sola sede
  distinta**. Con una sola sede, «cambio di sede» è impossibile per lui:
  `per_day = per_week = 0` non può essere violato **da nessuna soluzione**.
  È un verde che non può fallire, ed è **nel banco** (`SEEDS = [1..5]`).
  → vedi **Important 1** sotto.
- **Seeds 6, 7, 10, 14 sono inerti per caso.** Le sedi distinte ci sono, ma
  la soluzione che CP-SAT restituisce col builder spento tiene ogni giornata
  monosede. Non c'è niente da riparare nel derivatore: è la fortuna del
  mutante.

**Ho provato a recuperare il divario, con i numeri.** Due varianti misurate
su 15 seed, cinque esecuzioni ciascuna, mutante acceso e poi spento:

| variante | MORDE | SKIP | inerti | falsi fallimenti col builder integro |
|---|---|---|---|---|
| in albero | 10, 10, 10, 10, 10 | 0 | 5 | 0 (`15 passed`) |
| **A** = in albero + guardia `len(sedi distinte) < 2 → 0` | 10, 10, 10, 10, 10 | 1 (seed 1) | 4 | 0 (`14 passed, 1 skipped`) |
| **B** = alterna sui **giorni del docente**, non su `day % 2`, + la stessa guardia | 10, 11, 11, 11, 11 | 0 | 4 | 0 (`15 passed`) |

La variante B (`sites[giorni.index(day) % len(sites)]` dove `giorni` sono i
giorni **realmente usati** dal docente) garantisce due sedi distinte appena il
docente ha due giornate, e converte il seed 1 da inerte a mordente. Guadagno:
**+1 caso**, non +2.

**Conclusione sul divario.** Il 12/15 della review non è riproducibile con
nessuna delle due varianti a costo basso, e la review stessa aveva
riportato la propria misura oscillare `12 poi 11`; la sua formulazione non
esiste come codice. Il 10-contro-12 **non è dimostrabilmente una differenza
reale di formulazione**, e non è nemmeno rumore di CP-SAT (qui la varianza è
zero su sei esecuzioni): è, per almeno un quinto della differenza, il difetto
strutturale del seed 1 — quello sì reale, e reale indipendentemente dal
conteggio.

### I due vincoli espliciti del giro — rispettati

- **`_make_activities` non toccata**: confronto di AST sui corpi di
  `tests/solver_harness.py` fra `31ff9de` e `HEAD` → `_derive_max_site_changes`
  e `_derive_site_transition` MODIFICATO, `_distanza_sedi` e
  `_coppie_sedi_vicine` NUOVO, **nient'altro**. `_make_activities` non compare
  nella lista.
- **Flusso casuale delle sedi separato**: `sedi_rng = random.Random(f"sedi-{seed}")`
  è ancora lì (riga 138), dentro `_make_activities`, e i due usi
  (`sedi_rng.random() < 0.5`, `sedi_rng.choice(...)`) sono intatti.
- ⚠ I due derivatori riscrivono le sedi **dopo** che il testimone è completo,
  usando `w.rng` (il flusso principale). Non è una violazione della Ruling 31:
  quel flusso viene consumato dopo la costruzione del testimone, e ogni
  `run_family` ne costruisce uno da zero eseguendo **un solo** derivatore —
  nessun altro derivatore può vedere un testimone diverso. Verificato: i 30
  casi del banco con l'harness in albero danno lo stesso esito di prima
  (§5), e la sonda a 30 seed non mostra alcuna deriva.

---

## 4. Il filtro sulle clausole (Minor 2 della review)

### **Fatto, corretto — ma «effetto nullo» è una misura vera su uno scenario non rappresentativo. Il filtro NON è codice morto.**

**Prima domanda: filtra mai qualcosa?** Strumentato `_sedi_raggiungibili` con
un contatore e lanciati `tests/test_solver_sites.py` +
`tests/test_solver_witness.py`:

```
SONDA_FILTRO {'chiamate': 18308, 'filtra': 8277, 'tagliate': 11977}
```

**8277 chiamate su 18308 (45%) restituiscono un sottoinsieme proprio** delle
sedi dell'istituto. Filtra, e parecchio.

**Seconda domanda: quanto taglia in constraint?** Conteggi di
`build_model` sul **banco di prova** (le stesse istanze che i test
esercitano), con e senza il filtro:

| famiglia, seed | con filtro (var, constr) | senza filtro | taglio constraint |
|---|---|---|---|
| `site_transition` 1 | 220, **488** | 268, 644 | −24% |
| `site_transition` 2 | 264, **524** | 320, 678 | −23% |
| `site_transition` 4 | 452, **756** | 500, 892 | −15% |
| `site_transition` 5 | 1414, **2156** | 1426, 2190 | −2% |
| `max_site_changes` 2 | 224, **282** | 400, 766 | **−63%** |
| `max_site_changes` 3 | 246, **409** | 398, 763 | −46% |
| `max_site_changes` 4 | 500, **678** | 692, 1092 | −38% |
| `max_site_changes` 5 | 1306, **1290** | 1738, 2514 | **−49%** |
| `max_site_changes` 1 | 92, 76 | 92, 76 | 0 (una sola sede: entrambi i builder escono subito) |

**Terza domanda: perché sul Fermi risultava nullo?** Perché dipende da
**come** si assegnano le sedi sintetiche, e nessuno l'aveva variato:

| Fermi, `slots = 1` | con filtro | senza filtro |
|---|---|---|
| 2 sedi, **100%** delle attività | 9736, **5604** | 9736, 5604 → **uguali** |
| 4 sedi, **100%** delle attività | 11332, **21830** | 11332, 21830 → **uguali** |
| 2 sedi, 50% **interlacciato** (una sì una no) | 9736, **5604** | 9736, 5604 → **uguali** |
| 4 sedi, 50% interlacciato | 11308, **21542** | 11332, 21830 → −1,3% |
| 2 sedi, 50% **prima metà** (per pk) | 9220, **4142** | 9736, 5604 → **−26%** |
| 4 sedi, 50% prima metà | 10174, **13654** | 11332, 21830 → **−37%** |

I numeri `5604` e `21830` del rapporto sono **riprodotti esattamente**: la
misura non è sbagliata. Ma è la misura del caso **saturo** — quando ogni
chiave ha, in ogni cella, un'attività di ogni sede, non c'è nulla da
filtrare *per definizione*. Basta che le sedi siano distribuite in modo
correlato alle classi (che è ciò che succede in una scuola con due plessi
veri: le classi del plesso A non hanno attività nel plesso B) perché il
filtro tagli un quarto o un terzo dei constraint.

**Verdetto**: non è né «un filtro che non filtra» né «un filtro che non
filtra ciò che crede». Filtra esattamente ciò che dichiara. La conclusione
del rapporto («il beneficio pratico resta da dimostrare») è **falsificata dal
banco di prova stesso**, dove il beneficio arriva al −63%: sarebbe bastata
una misura sul testimone invece che solo sul Fermi sintetico. → **Minor 1**
(accuratezza del docstring e del rapporto, non del codice).

---

## 5. Vincoli globali

| | esito |
|---|---|
| Suite mai rossa, mai rimpicciolita | ✅ 297 passed / 3 skipped, **6 esecuzioni consecutive**, zero intermittenza |
| Test raccolti | 299 → **300** (+1, il test nuovo). Non rimpicciolita |
| `domain/analysis/` non importa `ortools` | ✅ `grep -rn ortools domain/analysis/` → nessuna occorrenza |
| Primitive del vocabolario riusate, non reinventate | ✅ solo `ctx.vocab.site_occupied(...)` e `any_free(ctx, ...)`; nessuna variabile nuova nel blocco `s == t` |
| Guardia `any_free` di `SiteTransitionBuilder` non toccata (Ruling 36) | ✅ il diff sulle righe `any_free` è di sole **aggiunte** (il nuovo blocco `s == t` ha la propria guardia); la guardia del blocco `s < t` è invariata. Questione non riaperta |
| Commenti in italiano, identificatori in inglese | ✅ conforme alla convenzione stabilita del file |

Suite, verbatim (`venv/bin/pytest -q`, sei esecuzioni dopo la rimozione di
ogni sonda e il ripristino di ogni file):

```
297 passed, 3 skipped in 26.61s
297 passed, 3 skipped in 26.00s
297 passed, 3 skipped in 26.67s
297 passed, 3 skipped in 26.61s
297 passed, 3 skipped in 26.77s
297 passed, 3 skipped in 26.44s
```

Skip, verbatim (`venv/bin/pytest -q -rs`):

```
SKIPPED arrival_departure: derivazione vacua per il seed 2
SKIPPED arrival_departure: derivazione vacua per il seed 4
SKIPPED structural:site_transition: derivazione vacua per il seed 3
```

Esattamente i tre dichiarati nel ledger. `git status` pulito in chiusura.

---

## 6. Osservazioni nuove, classificate

### Important 1 — `_derive_max_site_changes` ha **perso** la guardia di vacuità, e produce un caso di banco che non può fallire

Il derivatore precedente aveva, esplicitamente:

```python
if len(sedi_docente) < 2:
    return 0
```

con la motivazione scritta nel proprio docstring: *«non basta che la riga
esista, deve poter essere violata»*. La riscrittura «segregato» l'ha
**sostituita** con una guardia più debole — `if len(attivita_docente) < 2` —
e il nuovo docstring dichiara che quella è l'unica condizione di vacuità:

> *«Vacua (ritorna 0) solo se il docente piu' carico ha meno di due attivita'
> nel testimone»*

**È falso.** Il derivatore assegna `sites[day % len(sites)]`: se il docente
scelto lavora solo in giorni della stessa parità (con due sedi), tutte le sue
attività ricevono **la stessa sede**, e il tetto `per_day = per_week = 0`
diventa **matematicamente inviolabile** — nessun builder rotto potrà mai farlo
fallire.

**Non è teorico: è il seed 1, che sta nel banco** (`SEEDS = [1, 2, 3, 4, 5]`).
Prova, col builder reso no-op:

```
SEED 1 potere=1 docente=6 n_att=5 giorni=[0, 2] sedi_distinte=1 n_sites=2
        → run_family("max_site_changes", 1) PASSA col builder spento
```

Caso di controllo: il seed 2, stesso derivatore, stesso mutante —
`giorni=[0, 1]`, `sedi_distinte=2`, e `run_family` **fallisce** come deve.

Quindi uno dei cinque casi di banco della famiglia `max_site_changes` è un
verde che non dimostra niente, e lo è **per costruzione**, non per il seed.
Nel ledger la famiglia risulta «senza più skip su nessuno dei cinque seed»:
letto come miglioramento, è invece uno skip onesto trasformato in un verde
travestito. È la **quarta** occorrenza sul piano dello stesso pattern
(Ruling 16, 24, 31, e la §3 della review precedente).

**Riparazione, misurata.** Due opzioni, entrambe verificate su 15 seed × 5
esecuzioni, con e senza mutante (§3):

- minima (2 righe): ripristinare la guardia dopo l'assegnazione delle sedi —
  `if len({w.act(aid).site_id for aid in attivita_docente}) < 2: return 0`.
  Il seed 1 torna a essere uno **skip** dichiarato. MORDE resta 10/15.
- preferibile (3 righe): alternare le sedi sui **giorni realmente usati** dal
  docente (`sites[giorni.index(day) % len(sites)]`) **più** la guardia sopra.
  Il seed 1 diventa **mordente**, nessuno skip, MORDE 10-11/15, e col builder
  integro `15 passed` (nessun falso fallimento in cinque esecuzioni).

⚠ Il rapporto dell'implementatore aveva *dichiarato* il 10/15 e proposto
un'ipotesi; l'ipotesi era giusta nella direzione ma il difetto sotto è più
netto di come l'aveva formulato — non «un criterio di scelta subottimale», ma
**una guardia perduta**.

### Minor 1 — «effetto nullo del filtro» è vero solo sullo scenario saturo

Vedi §4 per numeri e casi di controllo. Il docstring di `time_sites.py` e la
§5 del rapporto vanno corretti: il filtro taglia il **26-37%** dei constraint
sul Fermi appena le sedi sono correlate alle classi (il caso realistico dei
plessi), e fino al **63%** sul banco di prova. La frase *«il beneficio pratico
resta da dimostrare»* è già dimostrata dai test esistenti. Non è un difetto di
codice: è una misura fatta su un solo scenario e generalizzata.

### Minor 2 — la clausola `s == t` è postata **due volte** per ogni coppia di sedi

Il doppio ciclo `for sa in per_fascia[s]: for sb in per_fascia[s]` scarta solo
`sa == sb`, quindi posta sia `(sa, sb)` sia `(sb, sa)`. La clausola
`AddBoolOr([X.Not(), Y.Not()])` è **simmetrica**: le due sono il medesimo
vincolo, e `posted` non le deduplica perché la firma contiene la coppia
ordinata. (Nel blocco `s < t` invece i due ordini sono vincoli **diversi** —
lì è giusto così.)

Misurato sostituendo `if sa == sb` con `if sb <= sa` nel solo blocco `s == t`:

| Fermi, 100% attività con sede | in albero | con la deduplicazione |
|---|---|---|
| 2 sedi | 5604 constraint | **4806** (−14%) |
| 4 sedi | 21830 constraint | **17042** (−22%) |

Suite mirata con la modifica: `127 passed, 6 skipped`
(`test_solver_sites.py` + `test_solver_witness.py` + i 30 seed delle due
famiglie) — nessuna regressione. Un carattere, esatto, e riduce di un quinto
la famiglia di vincoli che il rapporto stesso segnala come la voce di costo
cresciuta. File ripristinato dopo la misura.

### Minor 3 — il filtro non è applicato alle fasce intermedie di `_coppie_di_sede`

`_coppie_di_sede` cicla su `sedi` (tutte) per le fasce `m` fra `s` e `t`, e
per ognuna chiama `site_occupied`, che **crea una `NewBoolVar` più un
`Add(var == 0)`** anche quando la sede non è raggiungibile in quella cella.
Quei disgiunti sono costanti **false** nella clausola risultante, quindi
toglierli è semantica-preservante (non cambia il vincolo: un disgiunto falso
non contribuisce). È lo stesso ragionamento della Minor 2 della review,
applicato solo a metà. Effetto visibile nei conteggi di §4 (le variabili
scendono già da 11332 a 10174 col filtro attuale; il resto sta qui). Non
urgente, ma è dove sta il grosso delle variabili sprecate a molte sedi.

---

## 7. Verdetto

**Il Task 9 si chiude, con una Important da girare al controller.**

| cosa | esito |
|---|---|
| 1. Important 2 — `_distanza_sedi` sulle fasce occupate | **chiusa**, riprodotta pre-fix (seed 15 **e 20**), zero fallimenti su 30 seed post-fix |
| 2. Ruling 33 — clausola `s == t`, indipendente da `needed` | **chiusa**, argomento verificato sul checker, esattezza dimostrata con caso di controllo; `MaxSiteChangesBuilder` toccato **solo** dal filtro, semantica preservata, docstring **dimostrato** vero |
| 3. Ruling 34 — potere vincolante | **chiuso per `site_transition`** (1/15 → 13-14/15); **chiuso solo in parte per `max_site_changes`** (0/15 → 10/15 stabile), con un caso di banco su cinque strutturalmente inerte → Important 1 |
| 4. Minor — filtro sulle clausole | **fatto e corretto**; la sua valutazione («effetto nullo») è però sbagliata → Minor 1 |
| 5. Vincoli globali | tutti rispettati, suite 297/3 su sei esecuzioni |

**Serve un giro 2?** No, se la Important 1 si risolve con le tre righe
misurate in §6 (o le due della variante minima). È una riparazione locale al
solo `tests/solver_harness.py`, non tocca alcun builder, ed è verificata a non
produrre falsi fallimenti in cinque esecuzioni col builder integro. Le tre
Minor possono viaggiare con lo stesso commit (Minor 2 è un carattere e vale
il 14-22% dei constraint della nuova famiglia) o essere rimandate alla spec
senza rischio.

⚠ **Quello che il giro non ha cambiato, e va ricordato al controller**: lo
scarto della fascia condivisa **resta** su `MaxSiteChangesBuilder`, per
decisione (Ruling 33), e la ri-review lo **conferma come scelta giusta** —
la sonda `ORDINE=AB / ORDINE=BA` mostra che il checker, oggi, dà due verdetti
opposti sullo stesso orario. Finché `domain/analysis` non decide, non c'è
nulla da tradurre.
