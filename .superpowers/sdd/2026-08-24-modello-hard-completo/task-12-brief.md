# Task 12 — `WEEKLY_ORDER`

Sei l'implementatore. Repo: worktree `modello-hard-completo`, branch
`worktree-modello-hard-completo`, HEAD `9e8471a`. Python: `venv/bin/pytest`.
Documentazione e commenti **in italiano**, identificatori in inglese.
Baseline della suite: **340 passed, 4 skipped** (i conteggi attesi scritti nel
piano sono vecchi — ignorali).

Il piano e' `docs/superpowers/plans/2026-08-24-modello-hard-completo.md`,
sezione **Task 12** (riga 2929). **Leggilo, ma non seguirlo alla lettera**:
tre parti sono gia' state misurate sbagliate prima di scriverti, e qui sotto
c'e' la versione corretta. Il codice del piano vale come traccia, non come
specifica.

---

## 0. Prima di scrivere qualunque riga

Leggi, nell'ordine:

1. `domain/analysis/checkers/subject_constraints.py` — **e' l'autorita'**. In
   particolare `_SubjectChecker.check`, `_placed_of` e
   `WeeklyOrderChecker.violations` (righe 179-188). Non fidarti del mio
   riassunto ne' del piano: guarda il codice.
2. `domain/solver/builders/base.py` — `SubjectBuilder`, il ciclo sulle firme
   e la deduplicazione. Il gate `any(aid in ctx.free ...)` sta **li'**, a
   livello di riga: nel tuo `post()` non ripeterlo.
3. `domain/solver/builders/subject_buckets.py` — i tre pattern ADR-018 gia'
   in albero (`residual_cap`, la tabella a quattro rami di `_post_cross`, il
   `continue` di `ForbiddenSequenceBuilder`). Il tuo caso e' un **quarto**
   pattern, descritto al §3.
4. `domain/solver/vocabulary.py` — `pos()` e `subject_activities()`.
   ⚠ `pos()` non e' mai stato usato da un builder: oggi lo tocca solo
   `tests/test_solver_vocabulary.py:177`. Sei il primo uso in produzione.
5. `domain/solver/residual.py` e `domain/solver/context.py` (righe 44-67, la
   definizione di `ctx.free` e di `ctx.cells`).

Il checker, per comodita' — ma **verificalo**, non copiarlo da qui:

```python
def violations(self, state, row, a, b):
    if row.subject_a_id == row.subject_b_id or not a or not b:
        return
    first_a = (a[0].day, a[0].start_slot)
    first_b = (b[0].day, b[0].start_slot)
    if first_b < first_a:
        yield self.finding(state, row, [a[0].activity_id, b[0].activity_id])
```

`a` e `b` vengono da `_placed_of`, che ordina per `(day, start_slot)`. Quindi
`a[0]` e' la **prima occorrenza piazzata**, e `pos = day * slots_per_day +
start_slot` e' ordine-isomorfo a `(day, start_slot)` finche' `start_slot <
slots_per_day` — che e' garantito dalla griglia.

---

## 1. Cosa consegnare

- Nuovo file `domain/solver/builders/subject_order.py` con
  `WeeklyOrderBuilder` registrato su `T.WEEKLY_ORDER`.
- `domain/solver/builders/__init__.py`: aggiungere `subject_order` all'import.
- `tests/solver_harness.py`: **un** derivatore per `ST.WEEKLY_ORDER`.
- `tests/test_solver_subject_order.py`: nuovo file di test.
- `tests/test_solver_registry.py`: aggiungere
  `SubjectConstraint.Type.WEEKLY_ORDER` all'insieme di
  `test_i_builder_tradotti_finora` e aggiornarne la docstring.

**Solo il Task 12.** Non anticipare `IMPOSED_SUCCESSION` (Task 13) ne' gli
altri vincoli d'ordine. Non toccare `domain/analysis/` — mai, per nessun
motivo: quel package non deve importare `ortools`.

---

## 2. Il derivatore — quello del piano e' rotto, misurato

Il derivatore scritto nel piano **non e' vacuo: fallisce**. Misurato su 60
seed prima di scriverti:

- produce sempre `righe=1` (60/60), quindi `run_family` non salta mai;
- ma su **19 seed su 60 il testimone stesso viola la riga appena creata** —
  cioe' il passo 1 di `run_family`, che e' un fallimento duro;
- e il **seed 1 e' fra questi**, cioe' dentro il banco.

Causa: calcola la prima occorrenza sull'**unione delle settimane**, mentre il
checker valuta uno `ScheduleState` per **firma**. Il minimo su un sottoinsieme
e' piu' **grande**, quindi la relazione `first_a <= first_b` puo' ribaltarsi
dentro una singola firma pur valendo sull'unione.

⚠ Nota di contrasto, perche' non generalizzi a sproposito: per `SAME_DAY`,
`SAME_HALF_DAY` e `TWO_DAYS` derivare sull'unione **e' corretto** — sono
vincoli di «non accade mai», e un sottoinsieme dei piazzamenti puo' solo
averne di meno. Qui e' un `min`, ed e' il caso opposto.

### La formulazione da implementare

Per ogni classe, per ogni coppia **ordinata** di materie distinte (A, B):

1. **Il testimone deve soddisfarla, firma per firma.** Per ogni firma `rep`:
   siano `aa` e `bb` le attivita' della classe di materia A e B **attive in
   `rep`**. Se una delle due e' vuota, quella firma non dice nulla (il
   checker esce con `not a or not b`): si passa oltre. Altrimenti, se
   `min(pos di bb) < min(pos di aa)`, la coppia si **scarta** — basta una
   sola firma a smentirla.
2. **Violabilita' geometrica**, in almeno una firma dove entrambe sono
   presenti: `min su bb della posizione ammissibile piu' presto` `<`
   `min su aa della posizione ammissibile piu' tardi`. Le posizioni
   ammissibili sono le stesse che `_try_place` e `GridBuilder` ammettono —
   `_collocazioni(w, aid)` per le fasce, e il giorno festivo escluso quando
   `holiday_week in w.weeks_of[aid]`.
3. **Accumula.** Niente `return` alla prima coppia buona: si scorrono tutte
   le classi e tutte le coppie ordinate, si contano le righe create, e il
   derivatore restituisce quel conteggio (il **potere vincolante**).

Misure che questa formulazione deve riprodurre (60 seed): **0 vacui**, **0
testimoni violati**, da **1 a 6 righe** per seed. Potere vincolante col
builder assente: **19/20 seed**, **4/5 dentro il banco**.

⚠ **Il seed 5 non morde**, e in modo **deterministico** (quattro esecuzioni
consecutive). Non e' un bug da inseguire: la guardia geometrica e'
*necessaria ma non sufficiente* per costruzione — ignora le altre attivita',
le indisponibilita', le sedi. Sbagliare **generoso** costa un caso di banco
debole; sbagliare **stretto** costa copertura persa in silenzio, che e'
peggio. **Dichiaralo nella docstring** del derivatore invece di nasconderlo
dietro il conteggio, come fa gia' `_derive_max_hours_subject`. Non mettere i
numeri misurati in docstring (Ruling 50: invecchiano in silenzio) — vanno nel
tuo report.

---

## 3. Il builder — e il ramo ADR-018 che il piano non ha

La parte facile e' quella del piano, e va bene com'e':

- uscire subito se `row.subject_a_id == row.subject_b_id` (il checker lo fa:
  **due** condizioni d'uscita, non una, e questa e' quella che in tutte le
  altre famiglie e' invece il caso dominante);
- uscire se `a` o `b` e' vuoto (`subject_activities(..., signature=rep)`);
- `AddMinEquality` su `v.pos(aid)` per i due gruppi, poi il confronto.

La parte che manca e' **ADR-018**. Il `SubjectBuilder.build` gia' scarta la
riga quando *nessuna* attivita' coinvolta e' libera. Resta il caso misto:
alcune congelate, altre libere.

Sia `FA` il minimo di `pos` sulle attivita' di A **congelate e attive in
`rep`** (`None` se non ce ne sono), `FB` idem per B. Un'attivita' congelata ha
`ctx.cells[aid]` di cardinalita' uno, quindi `FA`/`FB` sono **costanti note a
build time**.

**Il principio** (vale per tutta la famiglia d'ordine, scrivilo in docstring):

> INFEASIBLE che nasce dal **divieto di peggiorare** e' ammesso; INFEASIBLE
> che nasce dalla **pretesa di riparare** non lo e'.

E' la lettura che unifica i precedenti gia' in albero: il clamp a zero di
`residual_cap` non chiede mai alle libere di rientrare sotto il tetto, chiede
solo di non aggiungerne; il quarto ramo di `_post_cross` idem. Il vincolo
secco `prima_a <= prima_b` quando `FB < FA` fa invece l'opposto: pretende che
le libere riparino una violazione che esisteva gia'.

**I due rami:**

```
FA is None or FB is None or FB >= FA   ->  model.Add(prima_a <= prima_b)
FA is not None and FB is not None and FB < FA  ->  disgiunzione reificata
```

La disgiunzione, con `riparato = model.NewBoolVar(...)`:

- `prima_a <= prima_b` sotto `OnlyEnforceIf(riparato)` — la riparazione resta
  **ammessa**, non imposta;
- `prima_a >= FA` **e** `prima_b >= FB` sotto `OnlyEnforceIf(riparato.Not())`
  — lo status quo: nessuna libera davanti alle colpevoli. Siccome una
  congelata di A sta gia' in `FA`, vale sempre `prima_a <= FA`, quindi
  `prima_a >= FA` significa esattamente `prima_a == FA`. Il risultato e' che
  `Finding.key` resta **identico** alla baseline — che e' l'argomento gia'
  scritto in `_post_separable` («un'aggiunta libera a un secchio gia' violato
  e' un finding *nuovo*»), applicato a una tupla `activities` invece che a un
  `count`.

Il ramo `FA is None`/`FB is None` non e' un caso ADR-018: senza congelate di
una delle due materie il checker sulla baseline esce con `not a or not b`, non
c'e' nessun finding preesistente, e il vincolo secco sta **prevenendo** una
violazione nuova. Che possa risultare INFEASIBLE e' esattamente cio' che
ADR-018 concede (vedi il docstring di `ForbiddenSequenceBuilder`).

---

## 4. I test

Il test `test_weekly_order_sul_banco` **non va scritto**:
`tests/test_solver_witness.py::test_famiglia` genera gia' i casi di banco per
ogni chiave registrata (Ruling 16, e' la quinta volta). Copia in testa al
modulo la nota ⚠ che sta in testa a `tests/test_solver_sites.py`.

Servono, tutti scritti a mano:

1. **Il vincolo morde.** Due attivita' di A e due di B nella stessa classe,
   riga `WEEKLY_ORDER`; la soluzione deve avere `min(pos A) <= min(pos B)`.
2. **A = B non vincola nulla.** ⚠ **Il test del piano e' vacuo**: con A = B
   i due `AddMinEquality` girano sullo stesso insieme, quindi `prima_a ==
   prima_b` e `prima_a <= prima_b` e' banalmente vero — un builder **senza**
   la guardia resta FEASIBLE, e il test non puo' fallire. La guardia e'
   osservabile solo sulla **dimensione del modello**: usa `build_model` (che
   restituisce `(model, ctx)`) e confronta il numero di variabili e di
   constraint con la riga presente e con la riga assente; devono essere
   **identici**. Verifica per mutazione che il test fallisca togliendo la
   guardia.
3. **Una materia assente non crea vincoli** (il ramo `not a or not b`).
4. **Firme di settimana**: due attivita' di A e due di B con maschere tali
   che in una firma A precede B e in un'altra il vincolo non si applica; il
   builder deve postare per firma. Costruiscilo in modo che una traduzione
   sull'unione dia una risposta **diversa** — e verificalo per mutazione
   (togli `signature=rep`).
5. **ADR-018, ramo secco**: una congelata di B, nessuna congelata di A, e la
   libera di A che deve finire prima di lei.
6. **ADR-018, ramo disgiuntivo**: congelate di A e di B con `FB < FA`. Il
   modello **non** dev'essere INFEASIBLE, e la soluzione deve rispettare la
   disgiunzione. Fai in modo che il ramo `riparato` sia **impossibile** (le
   libere di A non possono andare prima di `FB`), cosi' il test esercita
   davvero lo status quo e non la riparazione — altrimenti stai testando
   l'altro ramo senza accorgertene.

**Regola non negoziabile, e' il difetto ricorrente di questo branch:** ogni
proprieta' che scrivi in una docstring deve avere un test che la difende, e
la prova che il test la difende e' la **mutazione** — rompi la proprieta' nel
builder e verifica che il test diventi rosso. Se la suite resta verde, il
test non difende niente. Nella review del Task 11 due proprieta' vere erano
completamente indifese, e una terza era difesa **a meta'** perche' il test era
unilateral per forma (asseriva che il modello resta *fattibile*, cosa che un
builder che non posta nulla soddisfa pure lui). Attenzione a questa forma: se
la tua asserzione e' «resta FEASIBLE», chiediti che cosa la renderebbe rossa.

Per congelare un'attivita': `immobility` fuori da `_IMMOBILE` la rende libera,
dentro la congela sulla propria `Placement`. Guarda come lo fanno i test
ADR-018 gia' scritti in `tests/test_solver_subject_maxhours.py`.

---

## 5. Come chiudere

1. `venv/bin/pytest tests/test_solver_subject_order.py -q` verde.
2. `venv/bin/pytest -q` — atteso **340 + i tuoi**, sempre **4 skipped**. Se
   compare uno skip nuovo, il derivatore e' vacuo su un seed del banco: dillo
   nel report, non aggiustare il test.
3. **Non committare.** Scrivi il report in
   `.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-report.md`:
   cosa hai fatto, ogni mutazione provata con l'esito (quale test e' diventato
   rosso, a quale riga), i numeri misurati del derivatore, e ogni punto in cui
   ti sei discostato da questo brief e perche'.

Se qualcosa in questo brief contraddice il codice in albero, **vince il
codice**: segnalalo nel report invece di piegare il codice al brief.
