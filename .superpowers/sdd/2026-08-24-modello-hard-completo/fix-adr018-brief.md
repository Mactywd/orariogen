# Fix — ADR-018 su `MIN_DISTRIBUTION` e `FREE_GUARANTEED`

Implementatore. Worktree `modello-hard-completo`, HEAD `8cf87b7`. Python:
`venv/bin/pytest`. Baseline: **424 passed, 15 skipped**. Docstring e commenti
in italiano senza accenti, identificatori in inglese. `domain/analysis/` **non
si tocca mai**: se builder e checker divergono, **vince il checker**.

⚠ **Tocca solo questi due file:**
- `domain/solver/builders/time_counting.py`
- `tests/test_solver_time_minimums.py`

Sto lavorando in parallelo su `tests/solver_harness.py`,
`tests/test_solver_subject_parts.py` e la spec: **non aprirli in scrittura**.

## 0. I due difetti, gia' riprodotti

La review finale li ha misurati e io ho riprodotto il primo di persona. Il
report integrale e' in
`.superpowers/sdd/2026-08-24-modello-hard-completo/review-finale-report.md`,
Finding 1 e Finding 2 — leggili, contengono le istanze minime.

**Finding 1 — `MinDistributionBuilder` (riga ~140).** Posta
`sum(qualificati) >= row.params["min_days"]` sul parametro **grezzo**: nessun
residuo di alcun tipo. Riprodotto (`mini_school`, due congelate su
`(0,0)`/`(0,1)`, una libera su `(1,0)`, riga `min_minutes_per_day=60,
min_days=3` sulla **classe**): baseline gia' violata, `solve()` INFEASIBLE,
**status quo forzato ancora INFEASIBLE**, e col solo `post` reso no-op
OPTIMAL. ⚠ La **docstring del builder stesso** contiene il controesempio
verbatim e dice che la proprieta' locale al giorno «non implica l'immunita' al
passato a livello di vincolo». Il codice sapeva, e postava lo stesso.

**Finding 2 — `FreeGuaranteedBuilder` (righe ~272-273 e ~285-287).** Le due
soglie residue sono clampate **indipendentemente**, ma i due conteggi si
escludono a vicenda: una mezza libera si conta solo se il **giorno e' attivo**,
quindi un giorno che la soglia dei *giorni* obbliga a lasciare vuoto
contribuisce **zero** mezze — mentre `days_per_cycle - giorni_interamente_persi`
lo conta come se potesse contribuirne una. Ciascuna soglia e' raggiungibile da
sola, la congiunzione no.

## 1. Il trattamento da adottare

⚠ **Non e' `residual_floor`**: qui il residuo non e' additivo. Una congelata
non «consuma una quota» — toglie **gradi di liberta'**, e l'effetto sul massimo
raggiungibile non e' una sottrazione.

Il principio e' quello gia' fissato in §9.5 della spec:

> `INFEASIBLE` che nasce dal **vietare un peggioramento** e' ammesso;
> `INFEASIBLE` che nasce dal **pretendere una riparazione** non lo e'.

Traduzione operativa, per ogni riga e per ogni firma:

1. Calcola `B` = il valore che la quantita' contata dal checker assume **sul
   piazzamento corrente** (`ctx.states[rep].placed`): giorni qualificanti per
   `MIN_DISTRIBUTION`; giorni liberi **e** mezze libere per `FREE_GUARANTEED`
   (due valori separati). ⚠ Calcolalo **con la stessa regola del checker**, non
   con la tua: rileggi `domain/analysis/checkers/` e riusa la stessa
   condizione. Se il conteggio del builder e quello del checker divergono di
   uno, il fix e' peggio del difetto.
2. Se `B >= soglia`: posta la soglia **grezza**. Il passato non e' il
   problema.
3. Se non esiste **nessuna congelata** fra le attivita' che toccano quella
   riga: posta la soglia grezza. L'istanza e' infattibile per conto proprio, e
   `INFEASIBLE` e' la risposta onesta — ⚠ e questo e' il caso di un solve **da
   zero**, dove `B` vale zero e clampare spegnerebbe il vincolo. E' il modo
   piu' facile di rompere tutto: **scrivilo in un test**.
4. Altrimenti usa il **ramo status quo**, nella forma gia' in uso su questo
   branch da `WeeklyOrderBuilder` (`domain/solver/builders/subject_order.py`,
   il booleano `riparato`) — leggila prima, e' il precedente:

```python
riparato = model.NewBoolVar(...)
model.Add(<quantita>) >= soglia).OnlyEnforceIf(riparato)
model.Add(<quantita>) >= B).OnlyEnforceIf(riparato.Not())
```

Cosi' il solver **ripara se puo'** (ADR-018 vuole il contenimento, non
l'uguaglianza: riparare e' un successo) e altrimenti si limita a **non
peggiorare**, che lo status quo soddisfa per costruzione.

⚠ Per `FREE_GUARANTEED` i due rami vanno sotto **lo stesso** booleano, non due
booleani indipendenti: e' esattamente l'indipendenza fra le due soglie a
causare il Finding 2.

**Caveat da verificare, non da assumere**: il ramo `B` e' soddisfacibile solo
se il piazzamento corrente delle attivita' **libere** e' dentro `ctx.cells`.
Se un pre-filtro strutturale ha escluso la cella dove una libera si trova
adesso, lo status quo non e' rappresentabile nel modello. Controlla se puo'
succedere; se puo', ripiega su un `B` calcolato sulle **sole congelate** e
dichiaralo in docstring.

## 2. I test — `tests/test_solver_time_minimums.py`

Forma obbligatoria (Ruling 85) per i test di **presenza**: `build_model` +
`model.Add(ctx.x[...] == 1)` che forza la violazione, e INFEASIBLE atteso.
Mai «risolvi e guarda la soluzione».

Servono almeno:

1. **Le due riproduzioni della review**, come test di non regressione: il
   modello dev'essere **fattibile** e lo status quo forzato dev'essere
   accettato. Una per famiglia.
2. **⚠ Il vincolo morde ancora da zero**: nessuna congelata, soglia
   irraggiungibile → INFEASIBLE. Senza questo test la correzione puo'
   degenerare in «la soglia non si posta mai» e nessuno se ne accorge. Vale per
   entrambe le famiglie.
3. **Il ramo di riparazione**: congelate che lasciano la soglia ancora
   raggiungibile → il solver **deve** raggiungerla (forza una soluzione che
   non la raggiunge e attendi INFEASIBLE).
4. **`FREE_GUARANTEED`, le due soglie insieme**: l'istanza minima del
   Finding 2, dove ciascuna e' raggiungibile e la congiunzione no.

**Criterio di mutazione (Ruling 89)**: ogni test di presenza dev'essere rosso
con il `post()` del suo builder reso no-op; i test di assenza si difendono con
una mutazione mirata (per esempio: `B` calcolato ignorando le congelate;
i due rami di `FREE_GUARANTEED` sotto booleani separati; ramo status quo
sempre attivo). **Nel report elenca ogni mutazione con l'esito.**

## 3. Misura obbligatoria prima di dichiarare fatto

Il fuzzer della review e' la prova che conta. Riscrivilo in una sonda
usa-e-getta (non committarla) e misura, per **entrambe** le famiglie:

- N istanze con congelate gia' in violazione (almeno 40 per famiglia);
- quante rifiutano lo **status quo** — deve essere **zero**, prima era 2/9 e
  6/23;
- quante introducono un finding `HARD` su una coppia (causale, risorsa) prima
  pulita — deve restare **zero**.

E rilancia `run_family` per le due famiglie sui seed **1-25**, non solo sui
cinque del banco: la correzione non deve far comparire skip nuovi ne' rossi.
I numeri vanno nel report.

## 4. Chiusura

- `venv/bin/pytest -q`: **424 + i tuoi**, e **15 skipped**. ⚠ Uno skip in piu'
  va misurato e riportato, non nascosto.
- **Non committare, non pushare.** Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/fix-adr018-report.md`.
- Se il brief contraddice il codice, **vince il codice**: segnalalo. E' gia'
  successo tre volte su questo branch, e ogni volta aveva ragione chi ha
  guardato il codice.
