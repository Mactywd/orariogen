# Review del Task 12 — `WEEKLY_ORDER`

Revisore. Worktree `modello-hard-completo`, HEAD `9e8471a`, lavoro non
committato. Suite verificata a inizio e fine review: **351 passed, 4 skipped**
(`venv/bin/pytest -q`). L'albero e' stato lasciato **esattamente** come
trovato: ogni mutazione e' stata applicata da una copia di riserva in
scratchpad e ripristinata; tutte le sonde sono state cancellate.

```
$ git status --porcelain
 M domain/solver/builders/__init__.py
 M tests/solver_harness.py
 M tests/test_solver_registry.py
?? domain/solver/builders/subject_order.py
?? tests/test_solver_subject_order.py
```

Verdetto in una riga: **il builder e' corretto nel ramo dominante e la
traduzione e' la piu' debole corretta**, ma la nona occorrenza del difetto
ricorrente c'e' ed e' proprio dove il brief indicava — l'affermazione
«`Finding.key` resta identico alla baseline» e' **falsa**, misurata.

---

## Critical 1 — Nel ramo status-quo `Finding.key` **non** resta identico alla baseline

### Il fatto misurato

`Finding.key` (letto in `domain/analysis/findings.py`, non dedotto) e':

```python
return (self.code, self.resources, self.activities,
        tuple(sorted(self.quantities.items())))
```

e per questa famiglia `activities` e' `tuple(sorted({a[0].activity_id,
b[0].activity_id}))` — cioe' **l'identita' delle due attivita' argmin**, non
la loro posizione. `WeeklyOrderChecker` non passa `quantities`, quindi
`activities` e' l'unica parte della chiave che varia.

Il ramo status-quo posta `prima_a >= FA`. `prima_a` e' un **minimo su
posizioni**: fissa il valore del minimo, non chi lo realizza. Se una libera di
A puo' finire **in pareggio esatto** con la congelata a `FA`, `prima_a == FA`
resta vero ma `a[0]` puo' cambiare identita', perche' `_placed_of` ordina per
`(day, start_slot)` con `sorted` (stabile) e a parita' l'ordine e' quello di
inserimento di `state.placed`, cioe' l'ordine del queryset `Activity`.

Il pareggio e' realizzabile: due attivita' della stessa materia su **parti
diverse della stessa partizione** (sdoppiamento — `ADR-013`, in scope v1) non
confliggono sull'occupazione e possono stare nella stessa cella, e i loro
token intersecano entrambi `_unit_keys(row) = {class_id, *parts}`.

Sonda (usa-e-getta, cancellata; riprodotta qui per intero):

```python
env = mini_school()
part = ClassPartition.objects.create(school_class=env["klass"], name="SD")
p1 = ClassPart.objects.create(name="1A_g1", partition=part)
p2 = ClassPart.objects.create(name="1A_g2", partition=part)
mat = Subject.objects.create(code="MAT", name="Matematica", discipline=env["discipline"])

ita_free   = make_activity(env["subject"], parts=[p2])                       # pk piu' basso
ita_frozen = make_activity(env["subject"], parts=[p1], immobility="fixed")
mat_frozen = make_activity(mat, classes=[env["klass"]], immobility="fixed")
place(env["schedule"], ita_frozen, day=2, slot=0)   # FA = 12
place(env["schedule"], mat_frozen, day=0, slot=0)   # FB = 0
SubjectConstraint.objects.create(subject_a=env["subject"], subject_b=mat,
                                 school_class=env["klass"], type=T.WEEKLY_ORDER)

prima = {f.key for f in check_schedule(env["schedule"])
         if f.severity == Severity.HARD and f.code == "subject_weekly_order"}
model, ctx = build_model(env["schedule"])
model.Add(ctx.x[(ita_free.id, 2, 0)] == 1)          # pareggio esatto con FA
stato = cp_model.CpSolver().Solve(model)
Placement.objects.update_or_create(schedule=env["schedule"], activity=ita_free,
                                   defaults={"day": 2, "start_slot": 0})
dopo = {...stessa cosa...}
```

Output:

```
BASELINE : [('subject_weekly_order', (1,), (2, 3), ())]
ids: ita_free=1 ita_frozen=2 mat_frozen=3
stato: OPTIMAL
DOPO     : [('subject_weekly_order', (1,), (1, 3), ())]
NUOVE    : [('subject_weekly_order', (1,), (1, 3), ())]
```

Il modello **ammette** il piazzamento (`OPTIMAL`), e quel piazzamento produce
un finding `HARD` con chiave `(1, 3)` contro la baseline `(2, 3)`: sotto il
calcolo differenziale di ADR-018 (`nuove()` in `tests/test_solver_oracle.py`)
e' una violazione **nuova**. E' esattamente il fallimento che il criterio di
riuscita dello spike dichiara inaccettabile.

Lo stesso vale simmetricamente per `prima_b >= FB` (una libera di B in
pareggio con `FB` puo' rubare la posizione di `b[0]`).

### Perche' e' un problema

1. La frase in docstring («Il risultato: se non si ripara, `Finding.key` resta
   **identico** alla baseline») e' l'**intera giustificazione** del ramo
   disgiuntivo, ed e' registrata come decisione nella Ruling 80. E' falsa.
2. Nessun test la difende: e' insieme *non difesa* e *non vera*, la coppia che
   il brief chiama il difetto ricorrente.
3. La configurazione che la rompe (sdoppiamento) e' in scope v1 e non e'
   esotica; e' irraggiungibile solo dal banco, che non crea nessuna
   `ClassPart` (vedi Important 4).

### Correzione minima

Il pareggio e' ammissibile **solo** perche' il tie-break del checker
(`sorted` stabile su `state.placed`) e' un artefatto dell'ordine di
inserimento, non una semantica — la stessa forma del problema gia' registrato
per `MaxSiteChangesChecker` in CLAUDE.md. Due strade:

- **Conservativa, una riga per gruppo** — nel ramo status-quo, vietare alle
  libere anche il pareggio:

  ```python
  for aid in a:
      if aid in ctx.free:
          model.Add(v.pos(aid) >= FA + 1).OnlyEnforceIf(riparato.Not())
  for bid in b:
      if bid in ctx.free:
          model.Add(v.pos(bid) >= FB + 1).OnlyEnforceIf(riparato.Not())
  ```

  E' un **divieto**, quindi ammesso da ADR-018; rende `prima_a >= FA`
  ridondante e la proprieta' «argmin invariato» vera per costruzione. Costo:
  vieta anche i pareggi che *non* avrebbero cambiato `a[0]` — ma quali siano
  dipende dall'ordine dei pk, cioe' non e' una semantica su cui vincolare.
- **Alternativa** — dichiarare l'ambiguita' del tie-break come questione di
  `domain/analysis` (non toccabile qui), registrarla accanto a
  `MaxSiteChangesChecker` nella voce «Ancora aperto» di CLAUDE.md, e nel
  frattempo correggere la docstring che oggi afferma il falso.

In entrambi i casi serve **il test che la difende**: la sonda qui sopra e'
gia' nella forma giusta (asserisce `dopo - prima == set()`), e va verificata
per mutazione rimettendo il builder consegnato.

---

## Important 1 — `prima_b >= FB` e' vera e **nessun test la difende**

`test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo` non contiene **nessuna
attivita' libera di B**: esercita solo la meta' A della congiunzione.

Mutazione applicata (poi ripristinata): sostituito
`model.Add(prima_b >= FB).OnlyEnforceIf(riparato.Not())` con un commento.

```
$ venv/bin/pytest -q -p no:randomly   # suite intera, sonde escluse
351 passed, 4 skipped in 35.14s
```

Controprova sull'altra meta': rimuovendo invece
`model.Add(prima_a >= FA).OnlyEnforceIf(riparato.Not())`

```
$ venv/bin/pytest tests/test_solver_subject_order.py -q -p no:randomly
FAILED ...::test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo
E       assert (0, 1) >= (2, 0)
1 failed, 5 passed
```

Quindi `FA` e' difeso, `FB` no. La proprieta' **e' vera** (vedi «Controllato e
trovato sano», punto 2), ma e' indifesa: e' la variante sottile del difetto
ricorrente, la stessa gia' registrata come Ruling 66.

**Correzione minima**: aggiungere al test una libera di B e asserire che non
puo' finire prima di `FB` (forzarla con `model.Add(ctx.x[(b_free.id, d, s)] ==
1)` su una cella con `pos < FB` e attendersi `INFEASIBLE`), verificando per
mutazione che il test cada rimuovendo la riga.

---

## Important 2 — La spiegazione in docstring del seed 5 non mordente e' **falsa**, misurata

La docstring di `_derive_weekly_order` scrive:

> ⚠ Anche cosi', un seed del banco non morde: la guardia geometrica vede solo
> la geometria della coppia, non il resto del modello (stesso limite
> dichiarato per `_capienza_secchio`). Non e' un bug da inseguire.

e il report ripete «coerente con [...] la natura necessaria-non-sufficiente
della guardia geometrica». **Misurato: non e' la causa.**

Sonda: per ogni riga creata dal derivatore e ogni firma, si ricostruisce il
modello col builder `WEEKLY_ORDER` reso no-op (monkeypatch, sorgente
intatto), si aggiunge `model.Add(prima_b < prima_a)` sulle stesse variabili
che il builder costruirebbe, e si risolve.

```
seed=1 potere=5 righe=5
  riga pk=1 2->1 : [(1,'OPTIMAL'), (2,'OPTIMAL')]
  riga pk=2 2->3 : [(1,'OPTIMAL'), (2,'OPTIMAL')]
  riga pk=3 1->2 : [(1,'OPTIMAL'), (2,'OPTIMAL')]
  riga pk=4 1->3 : [(0,'OPTIMAL'), (1,'OPTIMAL'), (2,'OPTIMAL')]
  riga pk=5 2->3 : [(1,'OPTIMAL'), (2,'OPTIMAL')]

seed=5 potere=4 righe=4
  riga pk=1 1->2 : [(0,'OPTIMAL'), (1,'OPTIMAL'), (2,'OPTIMAL')]
  riga pk=2 3->2 : [(0,'OPTIMAL'), (1,'OPTIMAL'), (2,'OPTIMAL')]
  riga pk=3 2->1 : [(0,'OPTIMAL')]
  riga pk=4 3->1 : [(0,'OPTIMAL')]
```

Tutte e quattro le righe del seed 5 sono **realmente violabili**: esiste un
piazzamento legale in tutto il resto del modello che le viola. La guardia
geometrica non ha creato nessuna riga vacua. Il seed 5 non morde solo perche'
il banco chiede «risolvi e guarda se la soluzione restituita e' pulita», e
CP-SAT restituisce (deterministicamente) una soluzione che le rispetta per
conto suo.

Questo **chiude la Ruling 81 con un dato**: le quattro righe non sono
inviolabili, sono fortunate.

**Perche' e' un problema**: la spiegazione falsa e' scritta in una docstring
che sopravvivera' ai Task 13-17, e indirizza chi legge verso «rendere la
guardia meno generosa» — che qui non servirebbe a niente — invece che verso la
forma del banco, che e' la causa vera.

**Correzione minima**: riscrivere quel capoverso dicendo cio' che si e'
misurato (le righe sono violabili, il banco non le fa mordere perche' accetta
una soluzione qualunque), oppure toglierlo e lasciare solo la dichiarazione di
generosita' della guardia, che resta vera.

---

## Important 3 — `test_weekly_order_impone_la_prima_occorrenza` non morde (confermato), e la riparazione minima e' misurata

### (a) Conferma indipendente

Mutazione `post()` reso no-op completo:

```
$ venv/bin/pytest tests/test_solver_subject_order.py -q
FAILED ...::test_weekly_order_posta_per_firma_di_settimana
FAILED ...::test_adr018_ramo_secco_vieta_la_libera_dopo_la_congelata
FAILED ...::test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo
3 failed, 3 passed
```

e il test «mordente» resta verde in modo **deterministico** (8 esecuzioni
consecutive, `-p no:randomly`, `1 passed` ogni volta).

La causa e' visibile: col builder spento CP-SAT piazza le attivita' in ordine
di creazione, e il test crea le due di A **prima** delle due di B.

```
[builder no-op] ITA=[(4, 2), (4, 3)]  MAT=[(4, 4), (4, 5)]
```

`min(ITA) = (4,2) <= min(MAT) = (4,4)`: l'asserzione e' soddisfatta per
costruzione della fixture, non dal vincolo.

### (b) E' rimediabile, e la forma minima e' una sola parola

Invertendo l'**orientamento** della riga (`subject_a=matematica,
subject_b=italiano`, lasciando invariato tutto il resto) il test chiede
l'ordine *contrario* a quello che la fixture produce da sola. Misurato:

- col builder no-op: `1 failed` — `assert (4, 4) <= (4, 2)` — su **8/8**
  esecuzioni consecutive;
- col builder consegnato: `2 passed` (entrambi gli orientamenti), con
  `ITA=[(0,4),(4,2)] MAT=[(0,2),(2,0)]` nel caso invertito, cioe' il solver
  ha **dovuto** spostare le attivita' per soddisfare la riga.

Correzione minima: scambiare `subject_a`/`subject_b` nel test esistente (o,
meglio, tenere entrambi gli orientamenti in un `parametrize`, cosi' il caso
«l'ordine coincide col naturale» resta comunque coperto).

### (c) Ma la forma «assert su una soluzione» resta una lotteria — raccomandazione per i Task 13-17

L'inversione funziona perche' *oggi* la soluzione di default di CP-SAT va
nell'altro verso; non e' una garanzia. La forma che discrimina in modo
deterministico e' **avversaria**: costruire il modello, forzare la violazione
sulle stesse variabili che il builder costruisce, e attendersi `INFEASIBLE`.

Misurato su tutti e cinque i seed del banco, riga per riga e firma per firma:

```
seed=1 righe=5  SPENTO ['OPTIMAL']  ACCESO ['INFEASIBLE']  morde: True
seed=2 righe=4  SPENTO ['OPTIMAL']  ACCESO ['INFEASIBLE']  morde: True
seed=3 righe=3  SPENTO ['OPTIMAL']  ACCESO ['INFEASIBLE']  morde: True
seed=4 righe=5  SPENTO ['OPTIMAL']  ACCESO ['INFEASIBLE']  morde: True
seed=5 righe=4  SPENTO ['OPTIMAL']  ACCESO ['INFEASIBLE']  morde: True
```

**5/5, seed 5 incluso** — contro 4/5 della forma attuale. La sonda e' cinque
righe di CP-SAT (`AddMinEquality` × 2 + `Add(pb < pa)`), cioe' esattamente la
Ruling 81: per la famiglia d'ordine la condizione di violazione **e'** una
clausola sulle variabili che il builder gia' costruisce, quindi l'obiezione
della Ruling 65 (una seconda implementazione di diciotto vincoli) qui non si
applica.

Raccomandazione per i Task 13-17: **il test «morde» di un vincolo d'ordine si
scrive forzando la violazione e asserendo `INFEASIBLE`, mai risolvendo e
guardando la soluzione**. Nota che questo distingue correttamente anche i test
gia' scritti: dei sei, i due che forzano una cella e attendono `INFEASIBLE`
(firme, ramo secco) muoiono sotto il no-op; l'unico «risolvi e asserisci» che
muore (ramo disgiuntivo) lo fa per fortuna, come si vede dal fatto che il
terzo «risolvi e asserisci» sopravvive.

---

## Important 4 — `klass.pk in w.tokens[aid]` contro `_unit_keys(row)`: precondizione taciuta, e qui e' **stretta** su B

Il checker espande l'unita' a `{class_id, *parts}`
(`checkers/subject_constraints._unit_keys`); il derivatore filtra su
`klass.pk in w.tokens[aid]` (`tests/solver_harness.py`, dentro
`_derive_weekly_order`). Con una `ClassPart` in gioco, un'attivita' legata
alla sola parte ha `tokens = {part_pk, ...}` e **non** contiene `klass.pk`:
il derivatore la perde, il checker no.

Conseguenze, direzione per direzione:

- su **A** la perdita rende `ceil_a = min(max pos)` piu' **grande** → guardia
  piu' larga → generosa, innocua;
- su **B** rende `floor_b = min(min pos)` piu' **grande** → guardia piu'
  **stretta**: puo' scartare righe violabili, che e' il modo di sbagliare che
  la docstring dichiara di evitare;
- e soprattutto sul **passo 1** (`il testimone deve soddisfarla`): una
  occorrenza di B su una parte, piazzata prima di A, sarebbe invisibile al
  derivatore e visibilissima al checker → riga nata gia' violata → fallimento
  duro di `run_family`, la stessa modalita' della Ruling 78.

**Oggi non morde** — misurato indirettamente: `tests/solver_harness.py:720`
contiene gia' `assert not ClassPart.objects.exists()` dentro
`_capienza_secchio`, e `_school`/`_make_activities` non creano nessuna parte
(`grep -n "ClassPart\|parts=" tests/solver_harness.py` → solo l'import e
quell'assert).

E' un **pattern preesistente**, condiviso con i derivatori dei Task 10-11
(`grep -n "klass.pk in w.tokens"` → righe 540, 586, 623, 805, 899-908, 1002).
Il precedente del Task 11 e' pero' istruttivo: li' la stessa precondizione
taciuta e' stata **asserita invece che sperata**, con la motivazione scritta
(«si manifesta come copertura che non c'e' piu'»).

**Correzione minima, qui**: una riga in `_derive_weekly_order`, sul modello di
`_capienza_secchio`:

```python
assert not ClassPart.objects.exists(), (
    "_derive_weekly_order filtra su klass.pk: con le parti, le occorrenze "
    "legate alla sola parte sfuggono al derivatore e non al checker")
```

La **generalizzazione** del pattern agli altri derivatori resta materiale da
Task 17: la nomino e vado oltre.

---

## Minor 1 — Il capoverso `FA is None or FB is None` e' confuso, e una sua frase e' falsa

Testo attuale:

> Include il caso in cui una delle due materie non ha alcuna congelata: li' il
> checker sulla baseline uscirebbe con `not a or not b` **solo se** la materia
> fosse del tutto assente, ma qui "a"/"b" sono gia' garantiti non vuoti
> (guardia sopra) — semplicemente non c'e' ancora nulla di fissato da
> rispettare, quindi non c'e' nulla da riparare.

Confonde due `a`/`b` diversi: quelli del **builder** (`subject_activities` —
tutte le attivita' della materia, piazzate o no) e quelli del **checker**
(`_placed_of` — solo le piazzate). La guardia «sopra» garantisce i primi, non
i secondi.

E la frase «solo se la materia fosse del tutto assente» e' **falsa**, misurata:
un'attivita' **libera ma gia' piazzata** rende `FB is None` e la baseline del
checker **non** pulita.

```
BASELINE weekly_order: [('subject_weekly_order', (1,), (1, 2), ())]
b_free in ctx.free: True
stato: INFEASIBLE
```

(A congelata a pos 29, B libera gia' piazzata a pos 0.)

**La conclusione operativa regge comunque** — vedi «Controllato e trovato
sano», punto 3 — ma la motivazione scritta non e' quella giusta e non reggera'
la rilettura fra sei mesi.

**Correzione minima**: dire cio' che il ramo fa davvero — «`FA`/`FB` contano
solo le **congelate**, perche' solo quelle il solver non puo' toccare. Se una
delle due manca, non esiste una violazione che le libere non possano
sciogliere da sole: qualunque `INFEASIBLE` che ne segua e' un divieto di
peggiorare, non una pretesa di riparare, anche quando la baseline non e'
pulita per via di una libera gia' piazzata.»

---

## Minor 2 — Il limite superiore di `NewIntVar` non e' il dominio di `pos`

```python
prima_a = model.NewIntVar(0, ctx.grid.days_per_cycle * ctx.grid.slots_per_day, ...)
```

Il massimo raggiungibile e' `(days-1)*slots + (slots-1) = days*slots - 1`
(per `mini_school`, 5x6: **29**, non 30). Il vincolo non e' mai attivo
(`AddMinEquality` fissa il valore), quindi e' innocuo — ma e' un limite
dichiarato che non corrisponde al dominio, e i sei vincoli d'ordine dei Task
13-17 lo copieranno. `-1` sul limite, o `max(v.pos(x).Proto()...)`; la prima
basta.

---

## Minor 3 — `_pos_bounds` dichiara come fatto una proprieta' vera solo per la fixture attuale

> Il dominio e' un prodotto cartesiano giorni x fasce — nessuna delle due
> dipende dall'altra

E' vero oggi perche' i due soli pre-filtri che tagliano celle si decompongono:
`GridBuilder` taglia per giorno (festivi) e per fascia (durata, intervalli),
separatamente. Ma `UnavailabilityBuilder.restrict`
(`domain/solver/builders/unavailability.py`) taglia per **coppia**
`(day, slot)`, e appena il banco creasse indisponibilita' per questa famiglia
il dominio smetterebbe di essere un prodotto.

La direzione dell'errore sarebbe **generosa** (min/max su un sovrainsieme →
`floor_b` piu' piccolo, `ceil_a` piu' grande → guardia piu' larga), quindi non
e' un difetto. Ma la frase e' scritta come invariante, non come «vale finche'
nessun pre-filtro taglia per coppia»: e' la stessa forma di «basta questo» che
questo branch ha gia' pagato otto volte.

**Correzione minima**: una subordinata — «e' un prodotto finche' nessun
pre-filtro taglia per coppia `(giorno, fascia)`; se lo facesse, questa
decomposizione resterebbe un rilassamento, cioe' ancora dalla parte generosa».

---

## Controllato e trovato sano

1. **Il potere vincolante, rimisurato con metodologia mia** (monkeypatch di
   `WeeklyOrderBuilder.post`, senza toccare il sorgente; `run_family` chiamata
   direttamente e le eccezioni catturate). Riproduce **esattamente** i numeri
   del report:
   - 60 seed: `potere` mai zero, distribuzione `1×1, 10×2, 14×3, 14×4, 9×5,
     12×6` (range 1-6), **0/60 testimoni violati**;
   - seeds 1-20 col builder sano: **20/20 PASS**, nessuno skip;
   - seeds 1-20 col builder no-op: **19/20 MORDE**, unico non mordente il
     seed 5.
   - Determinismo del seed 5: **6/6** esecuzioni singole `NON-MORDE`, e
     l'insieme dei seed non mordenti e' identico su **3** esecuzioni complete
     della batteria. Non oscilla.

2. **La disgiunzione e' la forma piu' debole corretta** (punto 2 del brief).
   L'insieme vietato e' `prima_a > prima_b ∧ (prima_a < FA ∨ prima_b < FB)`.
   Entrambi i disgiunti implicano un finding **nuovo**:
   - `prima_a < FA` significa una libera di A **strettamente** prima della
     congelata a `FA` → `a[0]` cambia identita' → `activities` cambia →
     chiave nuova;
   - `prima_b < FB` idem su `b[0]`;
   e in entrambi i casi `prima_a > prima_b` garantisce che un finding ci sia.
   Non ho trovato nessun piazzamento vietato dalla disgiunzione che non
   produca un finding nuovo: **il builder non e' piu' stretto della spec**.
   ⚠ L'errore va nell'altro verso — la disgiunzione e' troppo **larga** nel
   caso di pareggio (Critical 1).

3. **`prima_a >= FA` equivale davvero a `prima_a == FA`**. La congelata che
   realizza `FA` appartiene sempre al gruppo su cui gira `AddMinEquality`
   (`subject_activities(keys, subject_a_id, signature=rep)` non filtra per
   `ctx.free`, e `_frozen_pos` pesca dallo stesso `a`), quindi `prima_a <= FA`
   e' un invariante. Verificato anche il presupposto:
   `SolverContext.build` da' `cells[aid] = {placed[aid]}` a ogni non-libera
   piazzata e **scarta** le non-libere mai piazzate, quindi
   `|ctx.cells[aid]| == 1` per costruzione e `_frozen_pos` e' lecito. Ne'
   `GridBuilder` ne' `UnavailabilityBuilder` toccano le celle delle congelate
   (entrambi ciclano su `ctx.free`).

4. **Il ramo `FA is None or FB is None` e' semanticamente corretto**, benche'
   mal motivato (Minor 1). Caso concreto richiesto dal brief — `FA` finito
   (congelata a pos 29), `FB is None`, libera di B senza celle dopo `FA`
   (l'unica, `(4,5)`, e' occupata dalla congelata di A sulla stessa classe):

   ```
   BASELINE weekly_order: []
   stato: INFEASIBLE
   ```

   Baseline **vuota** → l'`INFEASIBLE` e' «divieto di peggiorare», ammesso da
   ADR-018, esattamente come dichiarato nel docstring di
   `ForbiddenSequenceBuilder`. Anche nella variante con B libera gia' piazzata
   (Minor 1) la lettura regge: il colpevole e' **libero**, quindi chiedergli
   di stare in regola non e' pretendere una riparazione del congelato.

5. **`vocab.pos` memoizzato per attivita' e non per firma: corretto, e non e'
   la forma del difetto D.T.B.** `pos(aid)` legge solo `ctx.cells[aid]` e
   `ctx.x[(aid, d, s)]` — niente attraversa i confini dell'attivita', quindi
   non c'e' nessun aggregato che possa mescolare settimane. Il difetto del
   2026-08-24 stava in `occupied`/`covered`, che aggregano **per risorsa** su
   piu' attivita': li' i letterali di un'altra firma cambiano il valore
   dell'aggregato. Qui il filtro per firma sta dove deve stare, cioe' nella
   **membership del gruppo** su cui gira `AddMinEquality` (`subject_activities(...,
   signature=rep)`), non dentro `pos`. Il limite superiore passato a
   `NewIntVar` e' invece leggermente incoerente col dominio reale: Minor 2.

6. **Il test sulle firme testa cio' che dichiara, non un artefatto.**
   `mini_school` crea `days_per_cycle=5, slots_per_day=6`, quindi
   `pos = day*6 + slot`: `(0,0)→0` ✓, `(2,0)→12` ✓, `(3,0)→18` ✓, `(1,0)→6` ✓
   — tutte le posizioni citate nei commenti dei sei test corrispondono. E
   l'`INFEASIBLE` non viene dall'occupazione: `a2` e `b1` condividono la cella
   `(0,0)` ma appartengono a settimane disgiunte (firme diverse), che il
   modello ammette; col `post()` no-op lo stesso scenario diventa `FEASIBLE`
   (il test e' fra i tre che muoiono).

7. **Le tre mutazioni gia' misurate dal committente** (`signature=rep`, i due
   rami ADR-018, la guardia `A = B`) non sono state rifatte, come da brief; le
   ho invece **estese** ai singoli congiunti del ramo disgiuntivo, che e' dove
   e' saltato fuori l'Important 1.

8. **Le altre parti del diff** (`builders/__init__.py`,
   `test_solver_registry.py`) sono corrette e minime: la chiave registrata e'
   `SubjectConstraint.Type.WEEKLY_ORDER`, l'insieme atteso e la docstring sono
   allineati, e `test_ogni_builder_ha_un_derivatore` copre l'accoppiamento.

---

## Riepilogo

| # | Rilievo | Classe |
|---|---|---|
| 1 | `Finding.key` cambia nel ramo status-quo sotto pareggio (sdoppiamento): il solver ammette un finding `HARD` **nuovo** | **Critical** |
| 2 | `prima_b >= FB`: proprieta' vera, zero test la difendono (suite verde rimuovendola) | **Important** |
| 3 | La docstring spiega il seed 5 con una causa falsa: le sue 4 righe sono violabili — chiude la Ruling 81 | **Important** |
| 4 | `test_weekly_order_impone_la_prima_occorrenza` non morde; riparazione minima misurata, piu' la forma da adottare ai Task 13-17 | **Important** |
| 5 | `klass.pk in w.tokens[aid]` vs `_unit_keys`: precondizione taciuta, **stretta** su B — assert qui, generalizzazione al Task 17 | **Important** |
| 6 | Capoverso `FA/FB is None` confuso, con una frase falsa (conclusione salva) | Minor |
| 7 | Limite superiore di `NewIntVar` fuori dal dominio di `pos` | Minor |
| 8 | `_pos_bounds`: la struttura a prodotto e' dichiarata come invariante | Minor |

Nessun commit, nessun push, nessuna modifica al codice. `domain/analysis/`
non e' stato toccato; dove ritengo che il **checker** abbia un'ambiguita' (il
tie-break di `_placed_of`) l'ho detto senza correggerlo.
