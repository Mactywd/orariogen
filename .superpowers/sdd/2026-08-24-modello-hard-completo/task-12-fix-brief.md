# Task 12 — giro di correzione

Sei l'implementatore del giro di correzione. Worktree
`modello-hard-completo`, HEAD `9e8471a`, il lavoro del Task 12 e' **non
committato**. Python: `venv/bin/pytest`. Suite ora: **351 passed, 4 skipped**.

Leggi prima, per intero:
- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-review.md` — la
  review. Ha un Critical, quattro Important e tre Minor, ognuno con la misura
  che lo dimostra e la correzione minima suggerita.
- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-brief.md` — il
  brief originale (per il contesto ADR-018).

Il Critical l'ho **riprodotto io** dopo la review, con una sonda mia: e' reale.

```
ids free=1 frozen=2 mat=3
PRIMA [('subject_weekly_order', (1,), (2, 3), ())]
stato OPTIMAL
DOPO  [('subject_weekly_order', (1,), (1, 3), ())]
NUOVE [('subject_weekly_order', (1,), (1, 3), ())]
```

Le decisioni sotto sono **prese**: implementale, non riaprirle. Se una si
scontra col codice, fermati e scrivilo nel report — ma il codice vince solo
se hai la misura che lo dimostra.

---

## 1. Critical — il pareggio che cambia l'argmin

**Decisione: si stringe il ramo status-quo, e la vera causa si registra come
questione aperta di `domain/analysis`.**

Nel ramo disgiuntivo di `WeeklyOrderBuilder.post`, sostituire

```python
model.Add(prima_a >= FA).OnlyEnforceIf(riparato.Not())
model.Add(prima_b >= FB).OnlyEnforceIf(riparato.Not())
```

con il divieto **per attivita' libera**, che esclude anche il pareggio:

```python
for aid in a:
    if aid in ctx.free:
        model.Add(v.pos(aid) >= FA + 1).OnlyEnforceIf(riparato.Not())
for bid in b:
    if bid in ctx.free:
        model.Add(v.pos(bid) >= FB + 1).OnlyEnforceIf(riparato.Not())
```

Perche' cosi': `prima_a >= FA` fissa il **valore** del minimo, non **chi** lo
realizza; il divieto per attivita' rende «l'argmin resta la congelata
colpevole» vero **per costruzione**, quindi `Finding.key` invariato diventa
una proprieta' strutturale invece di una speranza. E' un divieto, quindi
ADR-018 lo ammette. Nota che `prima_a >= FA` diventa **implicato** (ogni
libera sta sopra `FA`, la congelata sta esattamente in `FA`): non tenerlo
accanto, sarebbe un vincolo ridondante che maschera le mutazioni.

⚠ Costo consapevole: si vietano anche i pareggi che *non* avrebbero cambiato
`a[0]`. Quali siano dipende dall'ordine dei pk in `state.placed`, cioe' da un
artefatto dell'ordine di inserimento — non e' una semantica su cui si possa
vincolare. Scrivilo in docstring.

**E correggi la docstring del builder**: oggi afferma che `Finding.key` resta
identico *grazie a* `prima_a >= FA`. Con la correzione l'affermazione diventa
vera, ma per un motivo diverso — dillo per il motivo giusto, e cita il
pareggio come il caso che l'aveva falsificata.

**Il test che la difende** (nuovo, in `tests/test_solver_subject_order.py`):
la sonda della review, nella forma «nessun finding nuovo». Costruzione:
`ClassPartition` + due `ClassPart` sulla stessa classe, una libera di A su una
parte e una congelata di A sull'altra (non confliggono: parti della **stessa**
partizione non condividono atomi, vedi `activity_tokens` in
`domain/analysis/state.py`), piu' una congelata di B prima di tutte. Forza la
libera nella cella della congelata di A e attendi **`INFEASIBLE`**.
**Verifica per mutazione**: col builder consegnato (`prima_a >= FA`) il
modello risponde `OPTIMAL` e il test dev'essere rosso.

**Poi registra la causa a monte** in `CLAUDE.md`, nell'elenco «Ancora
aperto», accanto alla voce esistente sul cambio di sede (`MaxSiteChangesChecker`
— stessa forma: un ordine d'inserimento che diventa semantica). In sostanza:
`_placed_of` ordina per `(day, start_slot)` con `sorted` stabile, quindi a
parita' di collocazione **l'identita' di `a[0]` dipende dall'ordine del
queryset**, e `Finding.key` con lei. Va deciso in `domain/analysis`; qui si e'
scelto di vincolare di piu' per non dipenderne. **Non modificare
`domain/analysis/`.**

## 2. Important 1 — `prima_b >= FB` indifeso

Dopo la correzione del Critical il congiunto e' quello su `b`. Estendi
`test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo` (o aggiungi un gemello)
con una **libera di B**, e asserisci che non puo' finire a `pos <= FB`.
Verifica per mutazione che rimuovendo il ciclo su `b` il test cada — oggi la
suite intera resta verde a rimuoverlo, ed e' il punto.

## 3. Important 2 — la docstring del seed 5 dice il falso

Le quattro righe del seed 5 **sono violabili** (misurato: forzando la
violazione col builder spento, tutte rispondono `OPTIMAL`). Non e' la
generosita' della guardia geometrica. Riscrivi quel capoverso di
`_derive_weekly_order` con la causa vera: il banco chiede «risolvi e guarda se
la soluzione e' pulita», e CP-SAT restituisce da solo una soluzione che le
rispetta. La dichiarazione di generosita' della guardia resta vera e va
tenuta, ma separata da questa spiegazione. Niente numeri in docstring
(Ruling 50).

## 4. Important 3 — il test «mordente» non morde, e la forma da adottare

**Decisione: si adotta la forma avversaria, qui e per i Task 13-17.** Per un
vincolo d'ordine, il test che dimostra che il vincolo morde si scrive
**forzando la violazione e attendendo `INFEASIBLE`**, mai risolvendo e
guardando la soluzione: la review l'ha misurata 5/5 sui seed del banco (seed 5
incluso) contro 4/5 della forma «risolvi e asserisci».

Riscrivi `test_weekly_order_impone_la_prima_occorrenza` in forma avversaria.
Tienine anche una versione «risolvi e asserisci» **con l'orientamento
invertito** rispetto all'ordine di creazione della fixture (misurato dalla
review: cosi' morde 8/8), perche' copre l'altro modo di sbagliare — un builder
che vieta *tutto*. **Verifica per mutazione** (`post()` no-op) che entrambe
cadano: l'obiettivo e' **6/6 rossi** sotto no-op, contro i 3/6 di oggi. Se non
arrivi a 6/6, dillo nel report con quali restano verdi e perche'.

## 5. Important 4 — la precondizione taciuta del derivatore

Aggiungi in testa a `_derive_weekly_order` l'assert sul modello di quello gia'
presente in `_capienza_secchio` (`tests/solver_harness.py:720`):

```python
assert not ClassPart.objects.exists(), (
    "_derive_weekly_order filtra su klass.pk: con le parti, le occorrenze "
    "legate alla sola parte sfuggono al derivatore e non al checker")
```

⚠ E' un pattern **preesistente** condiviso coi derivatori dei Task 10-11: la
generalizzazione e' materiale del Task 17, **non farla qui**.

## 6. I tre Minor

- **Minor 1**: riscrivi il capoverso `FA is None or FB is None` del docstring.
  Confonde gli `a`/`b` del builder (tutte le attivita') con quelli del checker
  (solo le piazzate), e contiene una frase falsa. La review propone il testo
  corretto: usalo o migliora, ma dev'essere vero.
- **Minor 2**: `NewIntVar(0, days*slots, ...)` → `days*slots - 1`.
- **Minor 3**: in `_pos_bounds`, la struttura a prodotto e' una **condizione**,
  non un invariante — `UnavailabilityBuilder.restrict` taglia per coppia
  `(giorno, fascia)`. Aggiungi la subordinata, notando che se accadesse la
  decomposizione resterebbe un rilassamento, cioe' ancora dalla parte generosa.

---

## Regole del giro

- **Ogni** proprieta' che scrivi in docstring dev'essere difesa da un test, e
  la prova e' la **mutazione**. Nel report elenca ogni mutazione provata, con
  quale test e' diventato rosso e a quale riga. Una mutazione che lascia la
  suite verde e' un difetto da segnalare, non da nascondere.
- `domain/analysis/` non si tocca. Mai. Non deve importare `ortools`.
- Non fare commit, non fare push.
- Suite attesa alla fine: **351 + i test nuovi**, sempre **4 skipped**. Uno
  skip nuovo significa derivatore vacuo su un seed del banco: segnalalo, non
  aggiustare il test.
- Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-fix-report.md`.
