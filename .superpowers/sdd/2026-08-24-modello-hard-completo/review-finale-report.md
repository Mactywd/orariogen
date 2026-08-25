# Review finale — branch `modello-hard-completo` (HEAD `8cf87b7`)

Baseline riprodotta: **424 passed, 15 skipped** (`venv/bin/pytest`, worktree
`modello-hard-completo`). Nessun commit, nessun push. I file di sonda usati per
misurare sono stati rimossi a fine review; il codice che serve a riprodurre
ogni finding e' incollato qui sotto per intero.

## Metodo — cosa e' stato misurato, e con cosa

| misura | ampiezza | esito |
|---|---|---|
| **A.** No-op di **ogni** builder (26 + i 2 `restrict`), conteggio dei rossi | 28 esecuzioni della suite | 1 builder con **zero** rossi |
| **B.** `run_family` su seed **6-25** invece dei 5 del banco | 26 famiglie x 20 seed | 462 passed, 58 skipped, **zero rossi** |
| **C.** `run_tutte_le_famiglie` su seed **6-45** | 40 seed | 34 puliti, **6 rossi al passo 1** (derivatore), 0 al passo 2 o 3 |
| **D.** Fuzzer ADR-018: congelate gia' in violazione + una libera, 17 famiglie x 40 istanze | 272 campioni «sporchi» | **2 famiglie** rifiutano lo status quo |
| **E.** Sonda esatta di violabilita' su `MAX_GAP_HOURS`, seed 1-40 | 40 righe derivate | **8 righe inviolabili**, una dentro il banco |

Le misure B e C sono le due piu' importanti in **positivo**: allargando il
range dei seed di quattro volte non e' emerso **nessun** builder piu' largo del
checker (passo 3) e **nessuno** piu' stretto del testimone (passo 2). Il
modello hard completo regge. Tutti i findings sotto riguardano input
**sporco** (ADR-018), copertura di test, e vacuita' del banco.

---

## Finding 1 — `MinDistributionBuilder` viola ADR-018, e la spec dichiara che non succede

**Gravita': alta.** E' la modalita' di fallimento che ADR-018 esiste per
escludere — un solver che rifiuta di lavorare su un orario gia' sporco — ed e'
l'unico dei ventisei builder rimasto **senza alcun trattamento** del residuo.

**File e riga**
- `domain/solver/builders/time_counting.py:140` —
  `model.Add(sum(qualificati) >= row.params["min_days"])`, sul parametro
  **grezzo**: nessun clamp, nessun residuo per forzatura.
- `docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md:540-541`
  (§9.5, caso 2) — «`MIN_DISTRIBUTION` invece **regge davvero**, quindi
  l'asimmetria e' reale e non generale».

**La proprieta' dichiarata e' falsa, misurata.** Istanza minima (5x6, un
docente, tre attivita' da un'ora, riga `min_minutes_per_day=60, min_days=3`):
due congelate sullo **stesso** giorno piu' una libera.

- baseline `check_schedule`: `min_distribution` HARD gia' presente,
  `{'days': 2, 'min_days': 3}` — cioe' le sole congelate violano;
- `solve()` → **INFEASIBLE**;
- forzando la libera **dov'e' gia'** (`model.Add(ctx.x[(c.id, 1, 0)] == 1)` su
  `build_model`) → ancora **INFEASIBLE**: il modello rifiuta lo *status quo*,
  che per definizione non introduce nessun finding nuovo;
- spegnendo **solo** `MinDistributionBuilder.post` con `monkeypatch` →
  **OPTIMAL**. Il responsabile e' lui, non un altro vincolo.

Fuzzer (misura D): **2 campioni su 9** con baseline gia' violata rispondono
INFEASIBLE pur ammettendo lo status quo.

⚠ **Il difetto era gia' scritto nel repo, in un altro documento.** La docstring
dello stesso builder (`time_counting.py:110-116`) contiene **il controesempio
verbatim**: «*Controesempio: 3 attivita', `min_minutes_per_day=60, min_days=3`
— tutte libere e' `OPTIMAL`; congelandone due sullo stesso giorno […]
`INFEASIBLE`, per colpa del passato*». Quindi codice e spec si contraddicono, e
la spec — il documento che il prossimo lettore consultera' — e' quella
sbagliata. E' il difetto tipico del branch nella sua forma piu' pura: una
proprieta' dichiarata vera che il codice accanto dichiara falsa.

**Costo se resta:** su un orario che l'utente ha sporcato a mano — il caso
d'uso per cui ADR-018 e' stato scritto, e il comportamento di EDT osservato con
21 attivita' in violazione — una sola riga `MIN_DISTRIBUTION` gia' violata
rende il solver **inutilizzabile**, non piu' largo. E chi legge la spec per
capire quali famiglie hanno il residuo trovera' scritto che questa non ne ha
bisogno.

**Direzione della correzione** (non applicata): il residuo per forzatura esiste
anche qui — i giorni **non piu' raggiungibili** vanno tolti dalla soglia,
`min(min_days, giorni_distinti_raggiungibili)`, dove i giorni raggiungibili
sono quelli gia' qualificati dalle congelate piu' quelli che le libere possono
ancora qualificare. Con quel clamp la soluzione porta lo **stesso**
`Finding.key` della baseline (`days=2`), quindi il differenziale resta pulito.

```python
# riproduzione: tests/test_rev_repro.py (rimosso a fine review)
grid, sch, sub, plan, k, t = _scuola(5, 6, 4)
a, b, c = _attivita(sub, plan, k, t, 3)
ResourceTimeConstraint.objects.create(
    resource=t, type=RT.MIN_DISTRIBUTION,
    params={"min_minutes_per_day": 60, "min_days": 3})
_congela(sch, [(a, (0, 0)), (b, (0, 1))])          # stesso giorno
Placement.objects.create(schedule=sch, activity=c, day=1, start_slot=0)
assert _baseline(sch, "min_distribution")          # la baseline gia' viola
assert solve(sch).status == "INFEASIBLE"
model, ctx = build_model(sch)
model.Add(ctx.x[(c.id, 1, 0)] == 1)                # status quo
assert cp_model.CpSolver().Solve(model) == cp_model.INFEASIBLE
monkeypatch.setattr(MinDistributionBuilder, "post", lambda *a, **k: None)
assert solve(sch).status == "OPTIMAL"
```

---

## Finding 2 — `FreeGuaranteedBuilder`: le due soglie residue sono clampate **una per volta**, e insieme sono insoddisfacibili

**Gravita': alta.** Stessa conseguenza del Finding 1 (INFEASIBLE per colpa del
passato), su un builder che la spec dichiara **gia' corretto**.

**File e righe** — `domain/solver/builders/time_counting.py:272-273` e
`285-287`:

```python
soglia_giorni = min(minimo_giorni, grid.days_per_cycle - giorni_persi)
model.Add(sum(giorni_liberi) >= soglia_giorni)
...
soglia_mezze = min(minimo_mezze, grid.days_per_cycle - giorni_interamente_persi)
model.Add(sum(mezze_libere) >= soglia_mezze)
```

**Proprieta' dichiarata** (`docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md:536-541`, §9.5 caso 2):
`ARRIVAL_DEPARTURE` e `FREE_GUARANTEED` sono «corretti col residuo *per
forzatura*». Per `ARRIVAL_DEPARTURE` il fuzzer conferma (0 rifiuti su 16
campioni sporchi). Per `FREE_GUARANTEED` **no**.

**Perche' e' falsa.** Le due soglie sono clampate su due conteggi
**indipendenti**, ma i due termini che contano **si escludono a vicenda**: una
mezza giornata libera si conta solo se il **giorno e' attivo**
(`libera = attivo AND NOT meta`, righe 261-263 — ed e' la traduzione corretta del
checker, che le mezze le conta solo `for day, slots in days.items()`). Quindi
un giorno che la soglia dei **giorni** obbliga a restare vuoto contribuisce
**zero** mezze libere, mentre `days_per_cycle - giorni_interamente_persi` lo
conta come se potesse contribuirne una. Ciascuna soglia e' raggiungibile da
sola; la congiunzione no.

**Istanza minima** (3 giorni x 4 fasce, `morning_end_slot=2`, un docente,
riga `free_days=2, free_half_days=2`), congelate a (1,3), (1,1), (2,0), libera
a (1,0):

- `giorni_persi = 2` → `soglia_giorni = min(2, 1) = 1` → il **giorno 0** deve
  restare vuoto;
- `giorni_interamente_persi = 1` (solo il giorno 1) →
  `soglia_mezze = min(2, 2) = 2`; ma le mezze libere ottenibili sono il
  pomeriggio del giorno 2 (**1**) piu' una del giorno 0 — che pero' conta solo
  se il giorno 0 e' **attivo**, cosa che la prima soglia vieta. Massimo
  raggiungibile: **1 < 2**.
- baseline `check_schedule`: `free_guaranteed` HARD gia' presente,
  `{'free_days': 1, 'free_half_days': 1, 'min_free_days': 2,
  'min_free_half_days': 2}`;
- `solve()` → **INFEASIBLE**; forzando la libera dov'e' gia' → **INFEASIBLE**;
  spegnendo solo `FreeGuaranteedBuilder.post` → **OPTIMAL**.

Fuzzer: **6 campioni su 23** sporchi rifiutano lo status quo.

⚠ E' la stessa forma della Ruling 19 (bound `2*giorni` sovrastimato), un
livello piu' in profondita': li' il bound sovrastimava il massimo di **una**
quantita', qui sovrastima il massimo di una quantita' **dato il vincolo
sull'altra**. La correzione del Task 7 giro 2 ha verificato che
`sum(mezze_libere)` coincide con `free_halves` del checker — vero, e non basta:
il difetto non e' nella traduzione, e' nel **residuo**.

**Costo se resta:** identico al Finding 1, su una famiglia che il registro
considera chiusa. E siccome §9.5 elenca `FREE_GUARANTEED` fra i casi
**corretti**, nessuno andra' a ricontrollarlo.

---

## Finding 3 — `PartsHomogeneousHalfBuilder` non e' difeso da **nessun** test

**Gravita': alta** come rischio, nulla come difetto attuale: il builder e'
corretto per quanto ho potuto verificare, ma **cancellabile senza che nulla
protesti**.

**Misura (A).** `MUT_BUILDER=PartsHomogeneousHalfBuilder` (il `build`
ereditato reso no-op) sulla suite **intera**, senza i file di sonda:

```
=== BASELINE ===                    424 passed, 15 skipped
=== PartsHomogeneousHalfBuilder === 424 passed, 15 skipped
```

Zero rossi. Per confronto, la stessa mutazione sugli altri venticinque:
`PartsAfterBuilder` e `MaxHalfDaysBuilder` 2 rossi (i minimi), `OccupationBuilder`
25, `WeeklyOrderBuilder` 16, `GridBuilder` 13, `UnavailabilityBuilder` 17.

**Perche' e' sfuggito.** La Ruling 112 misura «`build()` no-op → 10 rossi su
13» e la Ruling 104 «`post()` no-op → 7 rossi su 10»: quelle mutazioni
spengono `_PartsOrderBuilder.post`, cioe' **tutte e quattro** le sottoclassi in
un colpo solo. La mutazione **per classe** non e' mai stata fatta, e distingue:
`PartsHomogeneousDayBuilder` (`_AB`) → 3 rossi, fra cui
`test_h_e_ab_hanno_secchi_diversi`; `PartsHomogeneousHalfBuilder` (`_H`) → 0.
Il test scritto apposta per separare i due secchi difende **solo il lato
`_AB`**.

Sul banco la famiglia gira su due seed dei cinque (2, 4 e 5 saltano per
derivazione vacua) e nessuno dei due morde.

**Costo se resta:** `_H` e `_AB` differiscono per **un solo attributo**
(`KIND = "half"` contro `"day"`), ed e' esattamente la differenza che i
docstring di `subject_parts.py` segnalano come «silenziosa se la si inverte»
(⚠ righe 20-23 in testa al modulo, e di nuovo 269 e 276 sulle due classi). La rete di sicurezza costruita per quel
rischio (`assert self.KIND in (...)`) non serve a nulla contro un `KIND`
sbagliato-ma-valido, e nessun test lo intercetterebbe.

**Serve un test mirato di `_H`** con la forma gia' usata per `_AB`
(`test_omogeneo_vieta_l_interlacciatura` con il secchio a mezza giornata: due
occorrenze nella mattina e una nel pomeriggio dello stesso giorno devono
comportarsi in modo **diverso** dal caso giornata).

---

## Finding 4 — settima forma di vacuita': `_derive_max_gap` crea righe geometricamente inviolabili, e una cade **dentro i cinque seed del banco**

**Gravita': media.** Un caso del banco verde che non puo' fallire — l'ottava
occorrenza del pattern gia' censito sette volte.

**File e riga** — `tests/solver_harness.py:516-521`, docstring di
`_derive_max_gap`: «*Crea sempre una riga: anche a budget zero e' un vincolo
vero, perche' **qualunque buco lo violerebbe***», e `return 1` incondizionato.

**La proprieta' e' falsa.** Il buco di una mezza giornata e'
`ultima - prima + 1 - conteggio`: perche' sia positivo servono **almeno tre
fasce** nella mezza giornata. La fixture pesca
`slots_per_day ∈ {4, 6}` e `morning_end_slot ∈ {2, 3, 4}`: con
`(slots_per_day, morning_end_slot) = (4, 2)` entrambe le meta' sono larghe
**2**, e nessun piazzamento puo' produrre un buco. La riga nasce inviolabile,
il derivatore restituisce comunque `1`, `run_family` non salta, e il caso passa
senza aver testato niente.

**Misura (E), sonda esatta di violabilita'** — builder spento con
`monkeypatch`, e sulle stesse variabili che il builder costruirebbe
(`vocab.covered`, `vocab.occupied`) si chiede al solver di **superare** il
budget:

```python
m2, ctx2 = build_model(w.schedule)          # con MaxGapBuilder.post reso no-op
t2 = [cov[s] - v2.occupied(row.resource_id, day, s, signature=rep)
      for day in ... for half in v2.halves() if len(half)
      for s in half]                         # cov = v2.covered(..., signature=rep)
m2.Add(grid.slot_minutes * sum(t2) >= row.params["max_gap_minutes"] + 1)
violabile = CpSolver().Solve(m2) in (OPTIMAL, FEASIBLE)
```

Su seed 1-40: **8 righe inviolabili su 40** — seed 1, 2, 22, 23, 25, 32, 36,
40. Sette hanno `larghezze=(2, 2)` (vacuita' puramente geometrica); il seed 1
ha `(3, 1)` e budget 60, ed e' inviolabile per il resto del modello — il limite
gia' dichiarato dalla Ruling 64.

⚠ **Il seed 2 e' nel banco**: `test_famiglia[max_gap_hours-2]` e' oggi un verde
incapace di fallire. Coerente con la misura A, dove spegnere `MaxGapBuilder`
rende rossi solo i seed 4 e 5 della famiglia.

**Guardia mancante** (una riga): la riga si crea solo se
`max(morning_end_slot, slots_per_day - morning_end_slot) >= 3`, oppure —
meglio, perche' copre anche il seed 1 — solo se il massimo buco settimanale
geometricamente raggiungibile supera `peggiore`.

**Costo se resta:** un caso su cinque del banco `max_gap` non prova niente, e
il conteggio `potere = 1` dice il contrario. E' la famiglia su cui questo
progetto ha gia' sbagliato due volte (soglia invece che budget; firme di
settimana).

---

## Finding 5 — i quattro derivatori `parts_*` si invalidano **a vicenda**, e il messaggio d'errore indirizza sulla causa sbagliata

**Gravita': media.** Non tocca i builder; rende `run_tutte_le_famiglie` —
il banco del modello completo, la misura di punta del Task 17 — **rosso su 6
seed su 40**, e verde sui cinque del banco per fortuna, non per costruzione.

**File e righe** — `tests/solver_harness.py:1936` (`_sintonizza_parti`),
chiamata da `_derive_parts` (riga 2005, prima istruzione) per **ognuno** dei
quattro tipi; `MUTANTI` a riga 389.

**Cosa succede.** `_sintonizza_parti` **riassegna la materia** dell'attivita' di
ogni parte finche' la riga del proprio tipo non diventa ammissibile. I quattro
`parts_*` sono tutti in `MUTANTI` e girano di fila: il secondo ri-sintonizza
sotto le righe che il primo ha appena creato, il terzo sotto quelle dei primi
due, e cosi' via. La precedenza dei `MUTANTI` protegge le **altre** famiglie —
non i `parts_*` fra loro.

**Misura.** Eseguendo i quattro derivatori in `ordine_derivatori()` e
registrando l'assegnazione delle materie dopo ciascuno, seed 1-40:

- l'assegnazione **cambia dopo il primo derivatore** in **22 seed su 40**
  (fino a tre assegnazioni distinte nello stesso seed — es. seed 1:
  `(2,2) → (1,2) → (1,3) → (1,3)`);
- il testimone finisce per **violare** una riga `subject_parts_order` gia'
  derivata in **6 seed su 40**: 12, 13, 21, 30, 35, 39.

Su `run_tutte_le_famiglie` (misura C, seed 6-45) quei sei sono esattamente i
sei fallimenti, tutti al **passo 1**:

```
SEED 12: il testimone viola la congiunzione delle righe derivate:
         [('subject_parts_order', (1,), (11, 25), (('bucket', 3),))]
```

⚠ **Il messaggio d'errore dice «un derivatore ha sporcato le righe di un altro,
vedi `ordine_derivatori()`»** — e mandera' chi lo legge a riordinare i
derivatori, che non e' il rimedio: l'ordine e' gia' quello giusto, il problema
e' che quattro derivatori **mutanti sulla stessa risorsa** non sono componibili
in nessun ordine.

**Effetto collaterale, non misurato in dettaglio ma certo per argomento:** le
righe create dai `parts_*` che girano per primi sono ancorate a una materia che
i successivi possono togliere all'attivita' di parte. Quelle righe diventano
**vacue** (il secchio non ha piu' entrambe le etichette) senza che nessuno se
ne accorga: il `poteri` che `run_tutte_le_famiglie` restituisce, e i «48-73
righe / 22-23 famiglie» del changelog, **sovrastimano** il potere vincolante
della composizione. Non l'ho quantificato: **sospetto misurabile, non
dimostrato**.

**Direzione della correzione:** sintonizzare **una volta sola** prima dei
quattro (o dare a ciascun tipo un'attivita' di parte propria, invece di
contendersi la stessa), e riscrivere il messaggio del passo 1 perche' nomini la
causa vera.

---

## Finding 6 — `_derive_two_days` e' l'unico derivatore di materia senza la guardia di co-attivita' per firma

**Gravita': bassa.** Quarta forma di vacuita' (Ruling 49), applicata a
`_derive_same_day` e `_derive_same_half_day` e mai a questo.

**File e riga** — `tests/solver_harness.py:766-802`. Il derivatore verifica che
**entrambe** le materie siano presenti nella classe e che non
compaiano mai in giorni consecutivi, ma **non** che esista una coppia
(attivita' di A, attivita' di B) **co-attiva in qualche firma di settimana** —
la condizione che `_coppia_violabile` incapsula per le altre due famiglie di
secchio. Con maschere disgiunte `a_days` e `b_days` non sono mai entrambe
popolate nello stesso `ScheduleState`, e `TwoDaysChecker` non puo' emettere
nulla.

**Misura:** su 60 seed, righe con nessuna coppia co-attiva in **3 seed** (6,
22, 59), 1-2 righe ciascuno. **Nessuno sui cinque del banco** — stesso profilo
latente della Ruling 35 e della Ruling 48: invisibile dove si guarda di solito.

**Costo se resta:** `creata` conta righe che non provano niente, quindi il
`potere` di `two_days_incompatible` e' sovrastimato in un seed su venti.

---

## Cosa ho verificato e ha tenuto (per non farlo rifare)

1. **Nessun builder e' piu' largo del checker su input pulito**, misurato su
   quattro volte i seed del banco: `run_family` per **tutte e ventisei** le
   famiglie su seed 6-25 → **462 passed, 58 skipped, zero rossi**;
   `run_tutte_le_famiglie` su seed 6-45 → 34 OPTIMAL con oracolo pulito, e i 6
   rossi sono tutti il Finding 5 (passo 1), **mai** il passo 2 (INFEASIBLE con
   testimone) o il passo 3 (piazzamento illegale accettato).
2. **Nessun builder e' piu' largo del checker nemmeno su input sporco.** Nel
   fuzzer ADR-018 (272 campioni con congelate gia' in violazione, 17 famiglie)
   il numero di soluzioni che introducono una violazione **su una coppia
   (causale, risorsa) prima pulita** e': **zero**, in ogni famiglia.
3. **La composizione dei ventisei builder non si contraddice.** Cercata
   esplicitamente su 40 seed (misura C): nessuna coppia di builder produce
   INFEASIBLE insieme su un testimone che entrambi soddisfano separatamente.
4. **L'equivalenza dichiarata per `HALF_DAY_GAP`** (Ruling 95: «tutte le coppie
   incrociate» = «solo le adiacenti») **regge**: l'argomento di minimalita' vale
   perche' l'elemento interposto ha per forza sorgente diversa da almeno uno
   dei due estremi, e `a1 != a2` e' automatico (`_placed_of` non ripete mai
   un'attivita', e con A != B le due liste sono disgiunte).
5. **La complementarita' dei due rami di `_PartsOrderBuilder`** e' esatta,
   pareggio compreso: `entries.sort()` ordina `(fascia, etichetta, id)` e
   `"class" < "part"`, quindi «parti prima» ⟺ `sp < sc` e «classi prima» ⟺
   `sp >= sc`, che partizionano le coppie. Verificato contro il checker riga
   per riga.
6. **Il residuo di `ARRIVAL_DEPARTURE`** tiene: 0 rifiuti dello status quo su
   16 campioni sporchi.
7. **La deduplicazione per firma** di `ResourceBuilder.build` e
   `SubjectBuilder.build` e' corretta: due firme con lo stesso `touching`
   (risp. `coinvolte`) producono per costruzione gli stessi letterali, perche'
   il filtro `aid in active` si applica a sottoinsiemi di quell'insieme.

---

## Una misura che estende un debito gia' dichiarato (non un finding nuovo)

§9.5 e la Ruling 110 dichiarano che l'oracolo differenziale a **chiave fine**
segnala come «nuovo» anche un finding **migliorato**, e lo attribuiscono al
solo `weight_week` («*una meta' del caso 4 non e' risolvibile da nessun
builder*»). Il fuzzer lo quantifica su tutte le famiglie: su 272 campioni
sporchi, `nuove()` a chiave fine spara **42 volte** in **12 famiglie su 17**
(`max_half_days` 18, `free_guaranteed` 6, `arrival_departure` 3,
`max_presence` 3, `max_hours` 2, `two_days` 2, `weekly_order` 2,
`imposed_succession` 2, `same_day` 1, `max_site_changes` 1, `max_hours_day` 1,
`half_day_gap` 1) — e a **chiave grossolana** (causale + risorsa, la forma che
§9.5 propone) **zero volte**, sempre.

Esempio verbatim, `same_day_incompatible`: baseline
`(activities=(130,131,132), count=3)`, dopo il solve
`(activities=(130,131), count=2)` — un **miglioramento** contato come
violazione nuova.

Cioe': il criterio di riuscita, applicato a input sporco com'e' scritto oggi,
sarebbe rosso su **una famiglia su tre**, non su una. Non e' un difetto dei
builder, ed e' gia' deciso di rimandarlo — ma la stima nella spec e' di un
ordine di grandezza sotto, e chi la legge partira' credendo che riguardi una
sola causale. La misura sopra e' la prova che la chiave grossolana **basta**:
zero falsi positivi su 272 campioni.

---

## Ordine di priorita' suggerito

1. Finding 1 (`MIN_DISTRIBUTION`) e Finding 2 (`FREE_GUARANTEED`) — sono la
   stessa cosa, ADR-018 non tenuto, sull'unica famiglia dove la spec dichiara
   che non serve e sull'unica dove dichiara che e' gia' fatto. Vanno insieme,
   con la correzione della spec §9.5.
2. Finding 3 (`_H` indifeso) — un test, e chiude il buco di copertura piu'
   grosso del branch.
3. Finding 5 (`parts_*` non componibili) e Finding 4 (`_derive_max_gap`) — il
   banco dice piu' di quello che prova.
4. Finding 6 — una riga.

---

## Nota di metodo

Le due contromisure che hanno prodotto tutti i findings sono quelle gia'
scritte in §9.8, applicate **piu' fine di come erano state applicate**:

- la **mutazione per classe concreta** invece che sulla base condivisa ha
  trovato il Finding 3, che dieci giri di review non avevano visto perche'
  spegnevano `_PartsOrderBuilder.post` e vedevano i rossi delle altre tre
  sottoclassi;
- **allargare il range dei seed** ha trovato i Findings 4, 5 e 6 — e non ha
  trovato **nessun** difetto nei builder, che e' il risultato piu' importante
  di questa review;
- il **fuzzer sullo status quo** (congelate in violazione, e la libera che
  resta dov'e') e' la forma decidibile del criterio «vietare un peggioramento
  si', pretendere una riparazione no»: e' quello che ha trovato i Findings 1 e
  2. E' cinquanta righe, e sarebbe la risposta diretta al debito «il banco non
  congela mai nulla» della §9.7 — molto piu' economica che estendere il banco
  a testimone.

---

## Appendice — le riproduzioni, per intero

I file di sonda sono stati rimossi; questo e' quanto basta a rifarle. Helper
comuni (griglia parametrica, attivita' a un'ora sulla stessa classe e sullo
stesso docente, congelamento):

```python
def _scuola(days, slots, morning):
    grid = TimeGrid.objects.create(days_per_cycle=days, slots_per_day=slots,
                                   slot_minutes=60, morning_end_slot=morning)
    monday = dt.date(2026, 9, 14)
    year = SchoolYear.objects.create(start_date=monday,
                                     end_date=monday + dt.timedelta(days=6),
                                     first_week_monday=monday)
    period = Period.objects.create(school_year=year, name="P1",
                                   start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="L")
    subject = Subject.objects.create(code="ITA", name="ITA", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="P", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    teacher = Teacher.objects.create(name="R", last_name="R", first_name="A")
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    return grid, schedule, subject, plan, klass, teacher

def _attivita(subject, plan, klass, teacher, n):
    out = []
    for _ in range(n):
        a = Activity.objects.create(subject=subject, duration_slots=1,
                                    duration_minutes=60, week_mask=weeks.full_mask(1))
        a.teachers.add(teacher); a.classes.add(klass); out.append(a)
    srv, _ = Service.objects.get_or_create(study_plan=plan, subject=subject,
                                           defaults={"class_minutes": 0})
    srv.class_minutes += 60 * n; srv.save()
    return out

def _congela(schedule, coppie):
    for act, (d, s) in coppie:
        Placement.objects.create(schedule=schedule, activity=act, day=d, start_slot=s)
        act.immobility = Activity.Immobility.FIXED
        act.save()

def _baseline(schedule, code):
    return [f for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code == code]
```

**Finding 2 — `FREE_GUARANTEED`:**

```python
grid, sch, sub, plan, k, t = _scuola(3, 4, 2)
a, b, c, libera = _attivita(sub, plan, k, t, 4)
ResourceTimeConstraint.objects.create(
    resource=t, type=RT.FREE_GUARANTEED,
    params={"free_days": 2, "free_half_days": 2})
_congela(sch, [(a, (1, 3)), (b, (1, 1)), (c, (2, 0))])
Placement.objects.create(schedule=sch, activity=libera, day=1, start_slot=0)
assert _baseline(sch, "free_guaranteed")
assert solve(sch).status == "INFEASIBLE"
model, ctx = build_model(sch)
model.Add(ctx.x[(libera.id, 1, 0)] == 1)      # status quo
assert cp_model.CpSolver().Solve(model) == cp_model.INFEASIBLE
monkeypatch.setattr(FreeGuaranteedBuilder, "post", lambda *a, **k: None)
assert solve(sch).status == "OPTIMAL"
```

**Finding 3 — la mutazione per classe.** Plugin pytest usa-e-getta:

```python
# _rev_mutant.py, poi: PYTHONPATH=. MUT_BUILDER=<Classe> venv/bin/pytest -q -p _rev_mutant
def pytest_configure(config):
    spec = os.environ.get("MUT_BUILDER")
    if not spec:
        return
    import domain.solver.builders                      # noqa: F401
    from domain.solver.registry import BUILDERS
    name, _, hook = spec.partition(":")
    target = next(c for c in set(BUILDERS.values()) if c.__name__ == name)
    if not hook:
        hook = "post" if "post" in target.__dict__ else "build"
    setattr(target, hook, lambda *a, **k: None)         # shadowa l'ereditato
```

⚠ Per `GridBuilder` e `UnavailabilityBuilder` serve `:restrict`: implementano
solo quel hook, e mutare `build` non fa nulla (era la prima versione della
misura A, e per due builder su ventisei dava zero rossi **per errore mio**,
non per assenza di copertura — con `:restrict` danno 13 e 17).

**Findings 4, 5, 6 — le sonde sul banco.** Rispettivamente: `run_family` /
`run_tutte_le_famiglie` / i quattro `DERIVERS[parts_*].fn(w)` in sequenza su
`build_witness(seed)` per `seed in range(...)`, piu' — per il Finding 4 — la
sonda esatta gia' incollata nel corpo di quel finding.
