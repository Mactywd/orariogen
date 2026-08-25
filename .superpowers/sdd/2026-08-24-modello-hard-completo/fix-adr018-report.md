# Fix ADR-018 su `MIN_DISTRIBUTION` e `FREE_GUARANTEED` — report

Worktree `modello-hard-completo`. **Nessun commit, nessun push.** File toccati:
solo `domain/solver/builders/time_counting.py` e
`tests/test_solver_time_minimums.py`. Le tre sonde usa-e-getta
(`tests/test_sonda_fuzz_adr018.py`, `tests/test_sonda_seed_estesi.py`,
`tests/test_sonda_pigrizia.py`) sono state cancellate a fine lavoro; il codice
che serve a rifarle e' descritto qui sotto.

⚠ **HEAD e' cambiato durante il lavoro**: il branch e' avanzato da `8cf87b7` a
`a4ce417` (*fix(test): quattro findings della review finale sul banco di
prova*) mentre stavo misurando. Tutti i numeri qui sotto sono presi su
`a4ce417`.

## 0. Due correzioni al brief

1. **La baseline non e' «424 passed, 15 skipped» — e' 424 passed, *16*
   skipped.** Misurato ripristinando `time_counting.py` a HEAD e rilanciando la
   suite intera: 16 skip, tutti da `tests/solver_harness.py:340` (derivazione
   vacua), lista identica prima e dopo la correzione. Lo stesso conteggio vale
   su `8cf87b7` e su `a4ce417`. **La mia correzione non aggiunge nessuno
   skip.**
2. **Il ramo status quo di `FREE_GUARANTEED` usa `B` grezzo, non
   `min(B, soglia)`.** Avevo scritto il clamp per non autorizzare una
   violazione nuova sulla quantita' che alla baseline e' gia' conforme. E'
   sbagliato, e il test l'ha dimostrato: con `min(B, soglia)` ciascun ramo e'
   implicato dall'altro (`B <= soglia` da una parte, `soglia >= min(B,soglia)`
   dall'altra), la disgiunzione **collassa** in `>= min(B, soglia)` per
   quantita' — cioe' esattamente i due booleani indipendenti che il Finding 2
   vieta. Con `B` grezzo il problema che temevo non esiste: se una quantita' e'
   conforme alla baseline vale gia' `B >= soglia`, quindi il ramo status quo e'
   **piu' stretto** della soglia, non piu' largo. Il brief aveva ragione alla
   lettera.

## 1. Cosa e' cambiato in `time_counting.py`

Un blocco di helper condivisi in testa al modulo, piu' la riscrittura della
coda di `MinDistributionBuilder.post` e `FreeGuaranteedBuilder.post`.

**Gli helper.**

- `_quantita_baseline(checker, state, row, days)` — chiama **il checker di
  `domain/analysis`** (`MinDistributionChecker.violations`,
  `FreeGuaranteedChecker.violations`) e restituisce le `quantities` del
  finding, o `None` se quel piazzamento non viola. Cosi' `B` e la condizione
  «la baseline gia' soddisfa la soglia» non sono una riscrittura della regola
  del checker: sono la regola del checker. Il brief avvertiva che una
  divergenza di uno renderebbe il fix peggiore del difetto — questo la rende
  impossibile per costruzione.
- `_congelate_sulla_risorsa(ctx, key, rep)` — riusa `frozen_occupies` su tutti
  i giorni. E' la regola 3 del brief: senza congelate si posta la soglia
  grezza.
- `_status_quo_rappresentabile(ctx, key, rep)` — il **caveat del brief,
  verificato invece che assunto**. Puo' succedere: se una libera non e'
  piazzata affatto, o se un pre-filtro strutturale (griglia, festivo,
  indisponibilita' rossa) ha tolto dal dominio la cella dove si trova adesso,
  il ramo `>= B` chiederebbe di conservare un valore che nessuna assegnazione
  ammissibile riproduce. C'e' un test dedicato (vedi §2).
- `_giorni_garantiti(ctx, key, rep)` — l'occupazione delle sole attivita' la
  cui collocazione attuale sopravvive nel modello.

**Il ripiego quando lo status quo non e' rappresentabile e' diverso nelle due
famiglie**, e non e' quello suggerito dal brief («B calcolato sulle sole
congelate»):

- su `MIN_DISTRIBUTION` l'occupazione e' **monotona** (piu' ore in un giorno
  non possono toglierlo dai qualificati), quindi il conteggio su un
  *sottoinsieme* dell'occupazione finale e' un valore raggiungibile da ogni
  assegnazione: `B` si calcola sempre su `_giorni_garantiti`, che degrada da
  solo, e non serve un secondo ramo;
- su `FREE_GUARANTEED` quel trucco **non vale** — piu' occupazione *toglie*
  giorni e mezze libere, quindi `B` sulle sole congelate
  (`days_per_cycle - giorni_persi`) e' una **sovrastima**, non un valore
  raggiungibile: e' letteralmente il bound che causava il Finding 2. Li' il
  ripiego e' `B = 0`, cioe' ramo vacuo. Nella pratica il caso si presenta di
  rado con la baseline gia' violata: con le libere non piazzate l'occupazione
  e' minima e i giorni liberi sono tanti, quindi la baseline e' quasi sempre
  pulita e si posta la soglia grezza.

**`MinDistributionBuilder.post`** — invariata la costruzione dei `qualificati`;
la coda diventa:

```python
minimo = row.params["min_days"]
quantita = _quantita_baseline(MinDistributionChecker(), ctx.states[rep], row,
                              _giorni_garantiti(ctx, key, rep))
if quantita is None or not _congelate_sulla_risorsa(ctx, key, rep):
    model.Add(sum(qualificati) >= minimo)
    return
riparato = model.NewBoolVar(...)
model.Add(sum(qualificati) >= minimo).OnlyEnforceIf(riparato)
model.Add(sum(qualificati) >= quantita["days"]).OnlyEnforceIf(riparato.Not())
```

**`FreeGuaranteedBuilder.post`** — spariti `giorni_persi` e
`giorni_interamente_persi` (i due clamp del Finding 2); restano le guardie
`frozen_occupies` che decidono quali letterali creare, perche' quelli gia'
persi varrebbero 0 comunque. Le due soglie stanno sotto **un solo** booleano:

```python
quantita = _quantita_baseline(FreeGuaranteedChecker(), stato, row,
                              stato.resource_days(key))
if quantita is None or not _congelate_sulla_risorsa(ctx, key, rep):
    <soglie grezze>; return
b_giorni, b_mezze = (quantita["free_days"], quantita["free_half_days"]) \
    if _status_quo_rappresentabile(ctx, key, rep) else (0, 0)
riparato = model.NewBoolVar(...)
#   riparato      -> giorni >= free_days  AND  mezze >= free_half_days
#   riparato.Not() -> giorni >= b_giorni   AND  mezze >= b_mezze
```

Le docstring dei due builder riportano il ragionamento per esteso, incluso il
controesempio del Finding 1 (che era gia' li', e veniva ignorato dal codice) e
la ragione per cui il clamp indipendente e' insoddisfacibile.

## 2. I test — `tests/test_solver_time_minimums.py`

Undici test nuovi, tutti nella forma della Ruling 85 dove sono test di
presenza: `build_model` + `model.Add(ctx.x[...] == 1)` che forza la violazione,
INFEASIBLE atteso. L'helper e' `_stato_forzando(schedule, [(att, cella), ...])`.

| test | cosa fissa |
|---|---|
| `test_adr018_min_distribution_accetta_lo_status_quo` | riproduzione **Finding 1**: modello fattibile, status quo forzato accettato |
| `test_min_distribution_morde_da_zero_senza_congelate` | senza congelate la soglia irraggiungibile resta INFEASIBLE |
| `test_min_distribution_senza_congelate_ripara_anche_se_la_baseline_viola` | baseline sporca ma **tutte libere** → il solver deve riparare, non conservare |
| `test_min_distribution_congelate_che_lasciano_la_soglia_raggiungibile` | ramo di riparazione: baseline conforme con congelate presenti → soglia grezza, forzatura INFEASIBLE |
| `test_min_distribution_lo_status_quo_non_e_un_lasciapassare` | `B` include le congelate, e peggiorare sotto `B` e' vietato |
| `test_adr018_free_guaranteed_accetta_lo_status_quo_con_due_soglie` | riproduzione **Finding 2** (griglia 3x4, `morning_end_slot=2`) |
| `test_free_guaranteed_morde_da_zero_senza_congelate` | idem, altra famiglia |
| `test_free_guaranteed_senza_congelate_ripara_anche_se_la_baseline_viola` | idem, altra famiglia |
| `test_free_guaranteed_congelate_che_lasciano_la_soglia_raggiungibile` | ramo di riparazione, altra famiglia |
| `test_free_guaranteed_le_due_soglie_stanno_sotto_un_solo_booleano` | **le due soglie insieme**: una via di mezzo ne' riparata ne' conservata dev'essere vietata |
| `test_free_guaranteed_status_quo_non_rappresentabile_non_blocca` | il caveat: cella attuale tolta da un'indisponibilita' rossa |

Aggiornata anche la docstring di
`test_adr018_free_guaranteed_bound_delle_mezze_e_per_giorno`: il bound che
difendeva non esiste piu', l'istanza resta valida ma per un'altra strada, e il
bound per-giorno e' oggi difeso da
`test_free_guaranteed_bound_delle_mezze_morde_ancora_senza_congelate`.

### Criterio di mutazione (Ruling 89)

Sonda: sei mutazioni applicate una per volta al sorgente, suite del file
rilanciata ogni volta.

| mutazione | rossi |
|---|---|
| **M1** `MinDistributionBuilder.post` → no-op | **5**: `..._congelate_che_lasciano_la_soglia_raggiungibile`, `..._lo_status_quo_non_e_un_lasciapassare`, `test_min_distribution_morde`, `..._morde_da_zero_senza_congelate`, `..._senza_congelate_ripara...` |
| **M2** `FreeGuaranteedBuilder.post` → no-op | **6**: `..._bound_delle_mezze_morde_ancora_senza_congelate`, `..._congelate_che_lasciano_la_soglia_raggiungibile`, `..._le_due_soglie_stanno_sotto_un_solo_booleano`, `..._morde_da_zero_senza_congelate`, `..._non_regala_mezze_giornate_dei_giorni_vuoti`, `..._senza_congelate_ripara...` |
| **M3** `B` calcolato ignorando le congelate | **2**: `..._congelate_che_lasciano_la_soglia_raggiungibile`, `..._lo_status_quo_non_e_un_lasciapassare` |
| **M4** le due soglie sotto booleani **separati** | **1**: `..._le_due_soglie_stanno_sotto_un_solo_booleano` |
| **M5** ramo status quo attivo anche **senza congelate** | **6**: i tre `..._senza_congelate...`/`..._morde...` di entrambe le famiglie |
| **M6** rappresentabilita' dello status quo **ignorata** | **1**: `..._status_quo_non_rappresentabile_non_blocca` |

⚠ M6 era **scoperta** al primo giro (zero rossi): il test dedicato e' stato
scritto dopo averlo misurato, non prima. Costruirlo ha richiesto un
pre-filtro strutturale vero (indisponibilita' rossa sui giorni 0-2) — la
mutazione non e' intercettabile con sole congelate.

## 3. Le misure

### 3.1 Fuzzer ADR-018 (la misura che conta)

45 istanze «sporche» per famiglia — congelate gia' in violazione della riga
piu' attivita' libere piazzate — su griglia 5x6, riga su docente o classe
scelta a caso, seme fisso `20260825`. Su ciascuna: (a) `build_model` con ogni
libera **forzata dov'e'** → lo status quo dev'essere accettato; (b) `solve` →
`apply` → `check_schedule`, differenziale sulle coppie (causale, risorsa).

| | **prima** (`a4ce417`) | **dopo** |
|---|---|---|
| `min_distribution` — istanze sporche | 45 | 45 |
| — **status quo rifiutato** | **45 / 45** | **0** |
| — `solve()` INFEASIBLE | 33 / 45 | **0** |
| — coppie (causale, risorsa) nuove | 0 | **0** |
| — chiavi di finding nuove | 0 *(quasi tutto INFEASIBLE)* | 4 |
| `free_guaranteed` — istanze sporche | 45 | 45 |
| — **status quo rifiutato** | **43 / 45** | **0** |
| — `solve()` INFEASIBLE | 16 / 45 | **0** |
| — coppie (causale, risorsa) nuove | 0 | **0** |
| — chiavi di finding nuove | 13 | 11 |

I due criteri del brief sono soddisfatti: **zero** rifiuti dello status quo e
**zero** finding HARD su una coppia (causale, risorsa) prima pulita.

Il mio fuzzer e' piu' severo di quello della review (che dava 2/9 e 6/23): le
istanze sono costruite apposta perche' la baseline violi, quindi la
percentuale di rifiuti pre-fix e' quasi totale invece che parziale.

⚠ **Una misura in piu', non richiesta dal brief.** La riga «chiavi di finding
nuove» usa la stessa nozione di `nuove()` in `tests/test_solver_oracle.py`,
cioe' `Finding.key` — che per queste due famiglie **include le quantita'**
(`days`, `free_days`, `free_half_days`). Un miglioramento *parziale* (`days`
passa da 2 a 3 con `min_days=5`) cambia la chiave e conta come «nuovo» pur non
essendo una violazione nuova. Il fenomeno **preesiste alla correzione** (13
campioni su `free_guaranteed` gia' prima) e non e' introdotto qui, ma vale la
pena saperlo prima di usare `nuove()` come oracolo su una baseline sporca:
oggi nessun test della suite lo fa.

### 3.2 `run_family` sui seed 1-25

Le due famiglie x 25 seed = **50 casi, 50 passed, zero skip, zero rossi** — sia
prima sia dopo la correzione. Nessuno skip nuovo, nessun rosso nuovo.

### 3.3 Suite completa

| | passed | skipped |
|---|---|---|
| baseline `a4ce417` | 424 | 16 |
| dopo la correzione | **435** | **16** |

+11 test, **nessuno skip nuovo**. La lista degli skip e' identica riga per
riga (tutti `solver_harness.py:340`, derivazione vacua).

## 4. Un punto aperto che la correzione lascia dietro di se'

**Il ramo disgiuntivo e' pigro, e nel caso misto puo' spegnere la riga.**

Il modello non ha funzione di costo: `riparato` e `riparato.Not()` sono alla
pari, e CP-SAT non ha nessun motivo di preferire la riparazione quando anche
lo status quo e' soddisfacibile. Su `MIN_DISTRIBUTION` questo ha una
conseguenza concreta nel caso **«poche congelate + libere non ancora
piazzate»**, che e' il caso d'uso normale di un solve incrementale:

- la baseline del checker conta solo cio' che **e' piazzato**, cioe' le sole
  congelate, quindi e' quasi sempre gia' violata;
- `B` vale allora quanto le congelate qualificano da sole;
- il ramo status quo `sum(qualificati) >= B` e' **soddisfatto da ogni
  assegnazione** (monotonia), cioe' vacuo;
- la riga, di fatto, non vincola piu'.

Misurato (sonda `test_sonda_pigrizia.py`, cancellata): una congelata sul giorno
0, sei libere **mai piazzate**, `min_days=3`, `min_minutes_per_day=60`. La
soglia sarebbe largamente raggiungibile; la baseline viola comunque; forzare
tutte e sei le libere su **due soli giorni** e' **ammesso**. Prima della
correzione era vietato (soglia grezza), al prezzo pero' dei 33/45 INFEASIBLE
della tabella sopra.

Non e' una perdita di correttezza — nessun finding nuovo, l'oracolo
differenziale regge — ma e' una perdita di **qualita'** reale, ed e' la stessa
forma che ha `WeeklyOrderBuilder` da quando il Task 12 ha introdotto il ramo
status quo su questo branch. Tre strade possibili, nessuna adottata qui perche'
il brief prescrive esplicitamente la disgiunzione e mette in guardia contro il
clamp:

1. **`model.AddHint(riparato, 1)`** — zero rischio semantico (non cambia
   l'insieme delle soluzioni), guida CP-SAT verso la riparazione senza
   garantirla. Un meccanismo nuovo per questo branch: da approvare, non da
   introdurre di nascosto.
2. **Clamp sul massimo raggiungibile** — la «Direzione della correzione»
   del Finding 1 (`min(min_days, giorni_raggiungibili)`), calcolabile con un
   greedy esatto sulla rilassazione «ogni giorno qualificante costa
   `max(0, need - fasce_congelate_quel_giorno)` ore libere». Non e' pigro,
   ma e' una **sovrastima** (ignora indisponibilita' e conflitti), quindi
   puo' ancora dare INFEASIBLE per colpa del passato: sarebbe il quarto
   «bound dichiarato conservativo e non lo e'» di questo branch.
3. **Non fare nulla e dichiararlo**, che e' quel che ho fatto: il costo e'
   scritto per esteso nella docstring di `MinDistributionBuilder`.

Suggerisco di portarlo nella spec accanto alla voce gia' aperta su
`WeeklyOrderBuilder`, perche' e' una decisione sulla **famiglia dei rami
status quo**, non su questi due builder.
