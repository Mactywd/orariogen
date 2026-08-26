# Task 7 — I tre minimi garantiti — report

## Cosa ho implementato

Tre builder in `domain/solver/builders/time_counting.py`, appesi allo stesso
file di `MaxHoursBuilder`/`MaxHalfDaysBuilder` del Task 6:

- `MinDistributionBuilder` (`T.MIN_DISTRIBUTION`)
- `ArrivalDepartureBuilder` (`T.ARRIVAL_DEPARTURE`)
- `FreeGuaranteedBuilder` (`T.FREE_GUARANTEED`)

Tutti e tre ereditano `ResourceBuilder` (ciclo sulle firme + deduplicazione
gia' nella classe base) e implementano solo `post`. Nessuno usa
`residual_cap`: sono minimi garantiti, e le congelate contribuiscono a
favore dentro `occupied`/`day_active`/`half_active` — se gia' bastano, i
`model.Add(sum(...) >= soglia)` risultano vacui per costruzione, mai
infattibili (come da spec §3.1 citata nel brief e in `residual.py`).

Tre derivatori aggiunti in `tests/solver_harness.py`:
`_derive_min_distribution`, `_derive_arrival_departure`,
`_derive_free_guaranteed`. Il codice del brief non aveva il `return` nei
punti di vacuita' — l'ho aggiunto, e ho **rafforzato** la vacuita' oltre a
quanto scritto nel brief (vedi sezione "Deviazioni dal brief" sotto).

Registro (`tests/test_solver_registry.py`,
`test_i_builder_tradotti_finora`) aggiornato: da sette a dieci chiavi.

File di test mirati: `tests/test_solver_time_minimums.py`. Ho scritto i tre
test del brief (`test_min_distribution_morde`, i due `test_free_guaranteed_*`)
e **non** ho scritto `test_minimi_sul_banco` (il parametrizzato a 15 casi):
lo copre gia' `test_famiglia` in `tests/test_solver_witness.py`, che itera
`sorted(DERIVERS) × [1..5]` e trova i tre nuovi derivatori appena registrati.

Ho aggiunto io due test mirati per `ARRIVAL_DEPARTURE`
(`test_arrival_departure_morde`,
`test_arrival_departure_soddisfacibile_resta_soddisfacibile`), perche' il
brief non ne forniva per questa famiglia — solo la versione parametrizzata
sul banco, che il controller ha chiesto di non duplicare. Il mio primo
tentativo era piu' debole (un'unica attivita' con soglia sullo slot); l'ho
scartato e sostituito dopo aver scoperto empiricamente che non mordeva — vedi
sotto.

## Come ho derivato le tre traduzioni leggendo il checker

Checker in `domain/analysis/checkers/time_constraints.py`.

**`MinDistributionChecker`** (righe 45–52):
```python
def violations(self, state, row, days):
    threshold = row.params["min_minutes_per_day"]
    qualifying = [d for d, slots in days.items()
                  if len(slots) * state.grid.slot_minutes >= threshold]
    if len(qualifying) < row.params["min_days"]:
        yield _finding(...)
```
Nessuna trappola qui: un giorno "qualifica" se occupa almeno `soglia` minuti,
e serve che almeno `min_days` giorni qualifichino. Il builder ricalca questo
uno a uno con una variabile booleana `q` per giorno (vincolata da
`sm * sum(occ) >= soglia` sotto `OnlyEnforceIf`), e `sum(qualificati) >=
min_days`.

**`ArrivalDepartureChecker`** (righe 100–116) — **prima trappola**:
```python
for day in range(state.grid.days_per_cycle):
    slots = days.get(day)
    if not slots:
        compliant += 1  # giornata vuota: rispettata
        continue
    ok = ((not_before is None or slots[0] >= not_before)
          and (not_after is None or slots[-1] < not_after))
    compliant += ok
```
Riga 106: `if not slots: compliant += 1` — **un giorno senza attivita' conta
come conforme**, non come violazione. Il builder non tratta il giorno vuoto
come caso a parte: se nessuna fascia proibita e' occupata in quel giorno
(cosa vera anche quando il giorno e' vuoto, perche' `v.occupied` per una cella
senza attivita' risulta 0), `viola` e' 0 e `conforme` e' 1 — combacia col
`compliant += 1` del checker senza bisogno di un ramo esplicito.

**`FreeGuaranteedChecker`** (righe 119–133) — **seconda trappola**:
```python
def violations(self, state, row, days):
    free_days = [d for d in range(state.grid.days_per_cycle) if d not in days]
    free_halves = 0
    for day, slots in days.items():
        morning, afternoon = _halves(state, slots)
        free_halves += (not morning) + (not afternoon)
    ...
```
Riga 122: `free_days` e' esatto — "assente da `days`" e' proprio "giorno
libero", quindi `not day_active` sommato su tutti i giorni coincide.

Ma riga 124: `for day, slots in days.items()` — **`free_halves` si calcola
solo iterando sui giorni presenti in `days`**, cioe' i giorni con almeno
un'attivita'. `days` (uno `state.resource_days(...)`, verificato leggendo
`_TimeChecker.check`/`violations` — la struttura e' un dict costruito dalle
occupazioni reali) **non contiene affatto** i giorni completamente vuoti.
Un giorno vuoto quindi contribuisce **zero** a `free_halves`, non due (le sue
due meta' "libere"). Il builder rispetta questo: `libera` (mezza giornata
libera-che-conta) e' vera solo se `attivo AND meta.Not()` — congiunta col
giorno attivo, non solo "meta' scarica". Un giorno inattivo non genera mai un
letterale `libera` a 1, quindi non gonfia la somma.

Ho verificato sperimentalmente (vedi sotto, "Trappola dimostrata") che
un'implementazione che ignora `attivo` (somma `not half_active` su ogni
meta') fa passare da INFEASIBLE a OPTIMAL esattamente il test costruito per
scoprirlo.

## TDD

**RED** — `venv/bin/pytest tests/test_solver_time_minimums.py -q` prima
dell'implementazione (con solo i tre builder assenti dal registro,
`ArrivalDepartureBuilder`/`FreeGuaranteedBuilder`/`MinDistributionBuilder`
non ancora scritti):

```
            make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]])
        ResourceTimeConstraint.objects.create(
            resource=env["klass"], type=T.MIN_DISTRIBUTION,
            params={"min_minutes_per_day": 60, "min_days": 3})
        soluzione = solve(env["schedule"], time_limit=30)
        assert soluzione.status in ("OPTIMAL", "FEASIBLE")
>       assert len({day for (day, _s) in soluzione.placements.values()}) >= 3
E       assert 1 >= 3
E        +  where 1 = len({4})

tests/test_solver_time_minimums.py:32: AssertionError
_______ test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti ________
...
        soluzione = solve(env["schedule"], time_limit=30)
>       assert soluzione.status == "INFEASIBLE", soluzione.stats
E       AssertionError: {'attivita': 1, 'libere': 1, 'variabili': 30, 'constraint': 1, ...}
E       assert 'OPTIMAL' == 'INFEASIBLE'
...
_________________________ test_arrival_departure_morde _________________________
...
>       assert slot >= 1
E       assert 0 >= 1

tests/test_solver_time_minimums.py:79: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solver_time_minimums.py::test_min_distribution_morde - asse...
FAILED tests/test_solver_time_minimums.py::test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti
FAILED tests/test_solver_time_minimums.py::test_arrival_departure_morde - ass...
3 failed, 1 passed in 0.72s
```

Atteso: senza costruttori registrati, il solver ignora del tutto le righe di
`ResourceTimeConstraint` (`ResourceBuilder.build` non trova nemmeno la chiave
in `BUILDERS`), quindi cerca una soluzione qualsiasi — che quasi mai soddisfa
per caso le soglie richieste. (Il quarto test qui era la mia prima versione
di `test_arrival_departure_morde`, poi sostituita — vedi "Deviazioni".)

**GREEN** — dopo l'implementazione:
```
$ venv/bin/pytest tests/test_solver_time_minimums.py -q
.....                                                                    [100%]
5 passed in 0.85s
```

```
$ venv/bin/pytest tests/test_solver_registry.py tests/test_solver_time_minimums.py -q
...........                                                              [100%]
11 passed in 0.81s
```

```
$ venv/bin/pytest tests/test_solver_witness.py -v -k "min_distribution or arrival_departure or free_guaranteed"
tests/test_solver_witness.py::test_famiglia[arrival_departure-1] PASSED  [  6%]
tests/test_solver_witness.py::test_famiglia[arrival_departure-2] SKIPPED [ 13%]
tests/test_solver_witness.py::test_famiglia[arrival_departure-3] PASSED  [ 20%]
tests/test_solver_witness.py::test_famiglia[arrival_departure-4] SKIPPED [ 26%]
tests/test_solver_witness.py::test_famiglia[arrival_departure-5] PASSED  [ 33%]
tests/test_solver_witness.py::test_famiglia[free_guaranteed-1] PASSED    [ 40%]
tests/test_solver_witness.py::test_famiglia[free_guaranteed-2] PASSED    [ 46%]
tests/test_solver_witness.py::test_famiglia[free_guaranteed-3] PASSED    [ 53%]
tests/test_solver_witness.py::test_famiglia[free_guaranteed-4] PASSED    [ 60%]
tests/test_solver_witness.py::test_famiglia[free_guaranteed-5] PASSED    [ 66%]
tests/test_solver_witness.py::test_famiglia[min_distribution-1] PASSED   [ 73%]
tests/test_solver_witness.py::test_famiglia[min_distribution-2] PASSED   [ 80%]
tests/test_solver_witness.py::test_famiglia[min_distribution-3] PASSED   [ 86%]
tests/test_solver_witness.py::test_famiglia[min_distribution-4] PASSED   [ 93%]
tests/test_solver_witness.py::test_famiglia[min_distribution-5] PASSED   [100%]
================= 13 passed, 2 skipped in 3.75s ==================
```
I due skip su `arrival_departure` sono i miei guardrail di vacuita' (vedi
"Deviazioni" — seed 2 e 4 producono una finestra non restrittiva, e
`run_family` salta invece di spacciare per verde un test che non poteva
mordere).

**Suite intera:**
```
$ venv/bin/pytest -q
........................................................................ [ 27%]
........................................................................ [ 54%]
......................................................s.s............... [ 81%]
................................................                         [100%]
262 passed, 2 skipped in 20.75s
```
Totale 264 (262 + 2 skip). Partenza dichiarata 244; delta = 5 test mirati
nuovi (`test_solver_time_minimums.py`) + 15 casi parametrizzati nuovi da
`test_famiglia` (tre famiglie × 5 seed, di cui 2 skip) = 244 + 5 + 15 = 264.
Nessuna riduzione, nessun rosso.

## Verifica che ciascuno dei tre builder morde

Per ognuno: disabilitata la riga finale `model.Add(...)` (sostituita con
`pass  # DISABLED_FOR_BITE_CHECK`), rilanciato il test mirato, verificato il
rosso, poi ripristinato e riverificato il verde.

**MinDistributionBuilder** — disabilitato
`model.Add(sum(qualificati) >= row.params["min_days"])`:
```
$ venv/bin/pytest tests/test_solver_time_minimums.py::test_min_distribution_morde -q
...
        soluzione = solve(env["schedule"], time_limit=30)
        assert soluzione.status in ("OPTIMAL", "FEASIBLE")
>       assert len({day for (day, _s) in soluzione.placements.values()}) >= 3
E       assert 1 >= 3
E        +  where 1 = len({4})
1 failed in 0.64s
```
Ripristinato: rientra verde (vedi run GREEN sopra).

**ArrivalDepartureBuilder** — disabilitato
`model.Add(sum(conformi) >= row.params["days"])`:
```
$ venv/bin/pytest tests/test_solver_time_minimums.py::test_arrival_departure_morde -q
...
        soluzione = solve(env["schedule"], time_limit=30)
>       assert soluzione.status == "INFEASIBLE", soluzione.stats
E       AssertionError: {'attivita': 26, 'libere': 26, 'variabili': 795, 'constraint': 101, ...}
E       assert 'OPTIMAL' == 'INFEASIBLE'
1 failed in 0.77s
```
Ripristinato: rientra verde.

Ho anche confermato che disabilitare la stessa riga fa cadere il banco di
prova a testimone (non solo il mio test mirato):
```
$ venv/bin/pytest tests/test_solver_witness.py -v -k "arrival_departure"
...
E       AssertionError: arrival_departure accetta un piazzamento che il checker boccia (seed 3): [('arrival_departure', (5,), (), (('days', 2), ('min_days', 3)))]
2 failed, 1 passed, 2 skipped in 1.43s
```
(seed 1 e 3 falliscono, seed 5 passa per caso — dipendente dal
piazzamento non deterministico di CP-SAT su quell'istanza).

**FreeGuaranteedBuilder** — disabilitato
`model.Add(sum(mezze_libere) >= minimo_mezze)`:
```
$ venv/bin/pytest tests/test_solver_time_minimums.py::test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti -q
...
        soluzione = solve(env["schedule"], time_limit=30)
>       assert soluzione.status == "INFEASIBLE", soluzione.stats
E       AssertionError: {'attivita': 1, 'libere': 1, 'variabili': 90, 'constraint': 71, ...}
E       assert 'OPTIMAL' == 'INFEASIBLE'
1 failed in 0.68s
```
Ripristinato: rientra verde.

**Trappola dimostrata separatamente** (non solo builder assente, ma builder
*scorretto* nella direzione che il brief descrive): sostituita la
congiunzione `attivo AND meta.Not()` con la sola `meta.Not()` (somma le mezze
giornate scariche su **tutti** i giorni, ignorando se il giorno lavora):
```python
model.Add(libera == meta.Not())   # TRAPPOLA: ignora `attivo`
```
```
$ venv/bin/pytest tests/test_solver_time_minimums.py::test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti -q
...
>       assert soluzione.status == "INFEASIBLE", soluzione.stats
E       AssertionError: {'attivita': 1, 'libere': 1, 'variabili': 90, 'constraint': 62, ...}
E       assert 'OPTIMAL' == 'INFEASIBLE'
1 failed in 0.63s
```
Conferma esattamente il meccanismo descritto nel brief: contare le mezze
giornate libere su tutti i giorni (non solo quelli con attivita') rende il
vincolo piu' facile e fa accettare un orario che il checker boccia. Ripristinata
la versione corretta subito dopo.

## Deviazioni dal brief

**1. `_derive_arrival_departure` e `_derive_free_guaranteed`: aggiunto un
guardrail di vacuita' che il brief non aveva.**

Il brief le scrive senza controllo — tornano sempre `1`. Analizzando la
convenzione `deriver` (docstring in `tests/solver_harness.py`: "zero
significa derivazione vacua... nessuna condizione da violare in questo
testimone") ho verificato che in certi casi degeneri quelle due derivazioni
**non hanno potere vincolante** anche se creano una riga:

- `_derive_arrival_departure`: se il docente scelto a caso non compare in
  **nessuna** firma, il fallback e' `prima, ultima = 0, slots_per_day - 1`
  — una finestra che non vieta nessuna fascia (`proibite` vuoto nel
  builder). Il vincolo risultante e' vero per costruzione, non solo per il
  testimone: nemmeno un builder completamente vuoto potrebbe farlo fallire.
  Ho aggiunto: `if prima == 0 and ultima == grid.slots_per_day - 1: return 0`.
  Verificato che scatta davvero: seed 2 e 4 di `arrival_departure` sono ora
  skippati da `run_family` (vedi output sopra) invece di essere conteggiati
  come verdi senza aver testato nulla.
- `_derive_free_guaranteed`: se sia `min_giorni` sia `min_mezze` risultano 0,
  il builder non posta nulla (entrambi i rami `if minimo_giorni:` / `if
  minimo_mezze and mezze_libere:` sono falsi), quindi anche qui un builder
  vuoto passerebbe. Ho aggiunto: `if not min_giorni and not min_mezze:
  return 0`. Nei cinque seed provati non si e' mai verificato (0 skip), ma
  il guardrail resta corretto per costruzione — stessa logica difensiva gia'
  usata da `_derive_max_half_days` e `_derive_unavailability` nel file.

Ho scelto di applicare questo guardrail perche' e' esattamente il tipo di
vacuita' silenziosa che la convenzione `deriver` esiste per intercettare (lo
dice la sua stessa docstring, e la review del Task 5 aveva gia' trovato tre
casi analoghi). Non l'ho segnalato come domanda perche' la correzione era
meccanica una volta letta la convenzione — ma la registro qui per
trasparenza, visto che il testo del builder-brief non la prevedeva.

**2. Il mio primo `test_arrival_departure_morde` non mordeva, e l'ho
riscritto.**

Il brief non fornisce un test mirato per `ARRIVAL_DEPARTURE` (solo il
parametrizzato sul banco, che non riscrivo per direttiva del controller). Ho
scritto io una prima versione: un'unica attivita', `not_before_slot=1`, e
l'asserzione che lo slot scelto fosse `>= 1`. **L'ho verificata prima di
fidarmene**, disabilitando il vincolo nel builder: il test **passava lo
stesso**, 8 volte su 8 (`OPTIMAL {1: (0, 1)}` sempre, mai `(0, 0)`) — CP-SAT,
su un modello quasi vuoto (nessun obiettivo, un solo letterale libero),
sceglie deterministicamente uno slot diverso da 0 per ragioni sue interne,
non per via del vincolo. Un test del genere sarebbe passato anche con un
builder completamente vuoto: l'ho scartato.

Riscritto con un argomento di **capienza** (lo stesso schema dei due test
`FREE_GUARANTEED` gia' nel brief): griglia 5×6 = 30 celle, `not_before_slot=1`
+ `days=5` vieta la fascia 0 su tutta la settimana e riduce la capienza
utile a 25; 26 attivita' non ci stanno → INFEASIBLE atteso, con un
complemento a 25 attivita' → FEASIBLE e pulito. Verificato che morde (vedi
sopra): disabilitando il vincolo il test torna verde per errore (OPTIMAL
invece di INFEASIBLE), esattamente il segnale che serve.

## File cambiati

- `domain/solver/builders/time_counting.py` — i tre builder aggiunti in coda
  al file del Task 6.
- `tests/solver_harness.py` — i tre derivatori (con `return` e guardrail di
  vacuita' su due di essi).
- `tests/test_solver_registry.py` — `test_i_builder_tradotti_finora`
  aggiornato da sette a dieci chiavi.
- `tests/test_solver_time_minimums.py` (nuovo) — cinque test mirati.

## Osservazioni dell'autorevisione

- **Completezza**: i tre builder, i tre derivatori, l'aggiornamento del
  registro e i test mirati sono tutti presenti. Nessuna delle interfacce
  dichiarate nel brief (`T.MIN_DISTRIBUTION`, `T.ARRIVAL_DEPARTURE`,
  `T.FREE_GUARANTEED`) manca.
- **Qualita'**: i nomi seguono la convenzione gia' in uso nel file
  (`qualificati`, `conformi`, `giorni_liberi`, `mezze_libere` — italiano per
  le variabili di dominio, come nei builder del Task 6).
- **Disciplina (YAGNI)**: non ho aggiunto nulla oltre ai tre builder e ai
  test necessari a dimostrarli. Non ho toccato `residual.py` ne'
  `vocabulary.py`: le primitive esistenti bastavano.
- **Test**: verificano comportamento vero — ciascuno dei tre e' stato fatto
  fallire deliberatamente (builder disabilitato) e ripristinato, non solo
  eseguito una volta in verde.
- **Codice pulito**: nessun residuo delle mie disabilitazioni temporanee e'
  rimasto nel diff finale (verificato con `git diff` prima del commit).

## Dubbi

Nessuno bloccante. L'unico punto degno di nota e' gia' documentato sopra
("Deviazioni dal brief"): ho esteso la vacuita' dei derivatori oltre quanto
scritto nel codice fornito, perche' la convenzione del file lo richiede — se
il controller preferisce che i derivatori restino piu' vicini alla lettera
del brief (sempre `return 1`), è una modifica di una riga per derivatore, ma
la lascerei cosi': altrimenti due dei quindici casi parametrizzati
diventerebbero test verdi senza aver testato nulla, lo stesso difetto che la
review del Task 5 ha gia' dovuto correggere tre volte.

---

# Giri di correzione

> ⚠ Nota di provenienza. Il Task 7 ha attraversato **due** implementatori e
> un'interruzione. Il primo ha scritto l'implementazione e il giro 1, ed e'
> stato fermato prima di poter scrivere il rapporto del giro 1 e prima di
> lanciare la suite sul proprio lavoro; il suo contenuto in volo e' stato
> committato dal controller come `24a544d`, con un messaggio che dichiara
> apertamente l'istantanea non verificata. Un secondo implementatore ha
> scritto le due correzioni del giro 2 ed e' stato fermato a sua volta,
> prima della suite e dei test. Il controller ha chiuso il resto: test
> mirati, prove RED, suite. Questa sezione e' quindi **ricostruita** dal
> diff `8193f82..24a544d`, dal working tree e dal ledger — non e' il
> racconto in prima persona di chi ha scritto ogni riga, e va letta cosi'.

## Giro 1 (commit `8193f82..24a544d`)

Tre osservazioni, tutte chiuse.

1. **`FreeGuaranteedBuilder` saltava la mezza giornata vuota.** Con
   `morning_end_slot == slots_per_day` lo `span` del pomeriggio e' vuoto, e
   `if not len(span): continue` non generava alcun letterale per quella
   meta'. Ma `FreeGuaranteedChecker` conta `(not morning) + (not afternoon)`
   e con `afternoon == []` quel termine vale **1 gratis** su ogni giorno
   lavorato: il builder era percio' piu' stretto del checker, e qualunque
   `free_half_days >= 1` diventava insoddisfacibile. Rimosso il `continue`;
   la meta' vuota contribuisce ora come costante scarica.
   ⚠ Verificato che `MaxHalfDaysBuilder` (Task 6) **non** e' stato toccato:
   li' lo stesso `continue` e' corretto, perche' quello e' un tetto.
2. **Residuo per forzatura su `ARRIVAL_DEPARTURE` e `FREE_GUARANTEED`.**
   Sono soglie di *assenza*: una congelata puo' **consumare** il minimo
   (occupare una fascia vietata, o un giorno/meta' che doveva restare
   libero). Non e' il caso di `residual_cap` (che clampa un tetto) ma di un
   residuo per forzatura, calcolato con `frozen_occupies`: la soglia scende
   di uno per ogni giorno/meta' gia' perso al passato. Senza, il modello
   diventava INFEASIBLE **per colpa del solo passato**, cio' che ADR-018
   vieta.
3. **Test mirato sul giorno vuoto** di `ARRIVAL_DEPARTURE`
   (`if not slots: compliant += 1` nel checker — un giorno senza attivita'
   conta come conforme).

Nel diff di quel giro sono pero' entrate **due nuove osservazioni**, aperte
dalla re-review e chiuse nel giro 2.

## Giro 2 (working tree su `24a544d`)

### Important 1 — il bound di `free_half_days` era sovrastimato

`FreeGuaranteedBuilder` clampava la soglia delle mezze giornate a
`2 * days_per_cycle - mezze_perse`, cioe' assumendo che un giorno possa
contribuire **due** mezze libere. Non puo': `libera = attivo AND NOT meta`,
quindi un giorno **attivo** ha per forza almeno una meta' occupata (ne da'
al massimo una libera) e un giorno **inattivo** non ne da' nessuna. Il
massimo raggiungibile e' `days_per_cycle`, non il doppio.

La correzione, in `time_counting.py`:

- `mezze_perse` (un contatore piatto di meta' congelate) diventa
  `giorni_interamente_persi`, che conta i giorni con **entrambe** le meta'
  gia' occupate dal passato — sono i soli che non possono contribuire
  nemmeno una mezza libera;
- la soglia diventa `min(minimo_mezze, days_per_cycle - giorni_interamente_persi)`.

⚠ Il ramo adiacente `free_days` e `ArrivalDepartureBuilder` sono stati
riverificati e **non** toccati: li' il bound era gia' corretto.

**Prova RED**, eseguita rimettendo il vecchio bound
(`2 * days_per_cycle - giorni_interamente_persi`) e rilanciando il test
nuovo:

```
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
E        +  where 'INFEASIBLE' = Solution(status='INFEASIBLE', placements={},
E             stats={'attivita': 8, 'libere': 6, 'variabili': 237,
E                    'constraint': 132, 'secondi': 0.033}).status
FAILED tests/test_solver_time_minimums.py::test_adr018_free_guaranteed_bound_delle_mezze_e_per_giorno
1 failed, 1 passed, 10 deselected in 0.71s
```

L'istanza e' la sonda del revisore: due congelate sul giorno 0, una per
meta' (slot 0 mattina, slot 4 pomeriggio), piu' sei libere, con
`free_half_days=5`. Il massimo raggiungibile e' 4 — il giorno 0 e' perso
per intero — quindi col vecchio bound la soglia restava 5 e il modello era
infattibile per il solo passato. Il secondo test del `-k` (la controprova
**senza** congelate, `test_free_guaranteed_bound_delle_mezze_morde_ancora_senza_congelate`)
passa in entrambe le versioni: il difetto e' specifico al residuo, non un
allentamento generale del vincolo.

### Important 2 — la docstring di `MinDistributionBuilder` diceva troppo

Il codice e' corretto e **non** e' stato toccato. Era la docstring a
dichiarare un'immunita' al passato falsificabile in tre righe: «qui, e solo
qui, l'affermazione regge senza eccezioni». La proprieta' vera e'
**locale al singolo giorno** (una congelata puo' solo far salire
`sum(occ)` per il giorno che occupa, mai renderlo non qualificante), e non
implica immunita' a livello di vincolo — il congelamento toglie gradi di
liberta' e puo' ridurre i giorni *distinti* raggiungibili sotto `min_days`.
La docstring riporta ora anche il controesempio: tre attivita',
`min_minutes_per_day=60, min_days=3`; tutte libere e' OPTIMAL, congelandone
due sullo **stesso** giorno diventa INFEASIBLE.

⚠ Questa e' la correzione che la spec §3.1 dovra' recepire al Task 17:
quel paragrafo dichiara impossibile un comportamento riproducibile in due
righe (Ruling 17 del ledger).

### Prova RED anche per il giro 1

Richiesta dal controller perche' il giro 1 non aveva lasciato rapporto.
Rimesso temporaneamente `if not len(span): continue` in
`FreeGuaranteedBuilder`:

```
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
E        +  where 'INFEASIBLE' = Solution(status='INFEASIBLE', placements={},
E             stats={'attivita': 1, 'libere': 1, 'variabili': 60,
E                    'constraint': 47, 'secondi': 0.019}).status
FAILED tests/test_solver_time_minimums.py::test_free_guaranteed_meta_pomeriggio_vuota_non_blocca_una_sola_mezza
1 failed, 1 passed, 10 deselected in 0.65s
```

L'altro test selezionato dal `-k` e' la controprova sulla griglia 5x6
normale, che passa in entrambe le versioni.

In tutti e tre i casi il file e' stato ripristinato da una copia integra
prima di proseguire, e `git diff` conferma che nessun residuo delle
disabilitazioni temporanee e' rimasto.

### Test aggiunti nel giro 2

- `test_adr018_free_guaranteed_bound_delle_mezze_e_per_giorno` — la sonda
  del revisore, RED col vecchio bound;
- `test_free_guaranteed_bound_delle_mezze_morde_ancora_senza_congelate` —
  la controprova che il vincolo continua a mordere senza congelate.

### Suite

`venv/bin/pytest` sul working tree finale: **269 passed, 2 skipped**
(erano 267 + 2 su `24a544d`; +2 sono esattamente i due test qui sopra).
