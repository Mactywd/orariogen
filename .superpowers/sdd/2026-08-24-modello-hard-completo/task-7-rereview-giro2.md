# Task 7 — ri-review mirata del giro di correzione 2

Ambito: le due osservazioni **Important** del giro 1, e nient'altro se non
ciò che il diff `24a544d..7e88822` tocca.
Diff riesaminato: `.superpowers/sdd/2026-08-24-modello-hard-completo/review-24a544d..7e88822.diff`
(2 file, +98 / −14).

---

## Verdetto in una riga

Entrambe le Important sono **chiuse**, e verificate riproducendo le prove
invece di leggerle. Nessuna osservazione nuova di livello Important. Tre
Minor, tutte rimandabili. **Il Task 7 si può chiudere così com'è: non serve
un giro 3.**

---

## 1. Important 1 — il bound di `free_half_days` — **CHIUSA**

### 1.1 La prova RED del report è riproducibile

Rimesso il vecchio bound (`2 * grid.days_per_cycle - giorni_interamente_persi`)
in `domain/solver/builders/time_counting.py` e rilanciato il file mirato:

```
        soluzione = solve(env["schedule"], time_limit=30)
>       assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
E       AssertionError: {'attivita': 8, 'libere': 6, 'variabili': 237, 'constraint': 132, ...}
E       assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
FAILED tests/test_solver_time_minimums.py::test_adr018_free_guaranteed_bound_delle_mezze_e_per_giorno
1 failed, 11 passed in 1.07s
```

Numeri identici a quelli riportati (`attivita: 8, libere: 6, variabili: 237,
constraint: 132`). File ripristinato subito dopo.

### 1.2 Il nuovo bound è *corretto*, non solo *meno sbagliato*

Ho riletto `FreeGuaranteedChecker.violations`
(`domain/analysis/checkers/time_constraints.py`) e messo a confronto, caso per
caso, il contributo del checker e quello del modello per **ogni forma di
giornata**:

| giornata | checker `(not morning) + (not afternoon)` | modello `sum(libera_h)` |
|---|---|---|
| nessuna attività (fuori da `days`) | 0 | 0 (`attivo = 0` ⇒ ogni `libera = 0`) |
| attiva, una sola metà occupata | 1 | 1 |
| attiva, entrambe le metà occupate | 0 | 0 |
| una metà **congelata**, l'altra scarica | 1 | 1 (la metà congelata non genera letterale, l'altra vale 1) |
| entrambe le metà congelate | 0 | 0 (nessun letterale generato) |
| metà pomeridiana **strutturalmente vuota**, mattina occupata | 1 | 1 (`half_active` su span vuoto è la costante 0) |

`sum(mezze_libere)` **coincide esattamente** con il `free_halves` del checker,
per ogni giornata. Da qui:

- il massimo raggiungibile è **1 per giornata**, quindi `days_per_cycle` —
  il vecchio `2 * days_per_cycle` sovrastimava di un fattore 2: confermato;
- l'unica giornata che non può contribuire nulla è quella con **entrambe** le
  metà già occupate dal passato, cioè esattamente `giorni_interamente_persi`.

### 1.3 «Un giorno può essere reso incapace di contribuire in altri modi?»

Sì, ma **solo in direzione conservativa**, e l'ho verificato su due casi che
il difetto avrebbe potuto toccare:

**Sonda B — metà strutturalmente vuota + congelata sull'altra metà.**
Griglia `5×4` con `morning_end_slot == slots_per_day` (nessun pomeriggio), una
congelata al giorno 0 mattina, quattro libere, `free_half_days=5`.
`frozen_occupies` su uno span vuoto è `False`, quindi il giorno 0 **non** viene
contato fra i `giorni_interamente_persi` — ed è giusto, perché il checker gli
assegna comunque `(not afternoon) == 1`.

```
SONDA-B status: OPTIMAL {'attivita': 5, 'libere': 4, 'variabili': 128, 'constraint': 102, ...}
SONDA-B nuove(): []
```

**Sonda C — una sola metà congelata su tutti e cinque i giorni.**
Nessun giorno è interamente perso, la soglia resta 5, ed è raggiungibile
lasciando scarichi i pomeriggi.

```
SONDA-C status: OPTIMAL {'attivita': 8, 'libere': 3, 'variabili': 140, 'constraint': 119, ...}
SONDA-C nuove(): []
```

L'altro modo di rendere una giornata incapace di contribuire (nessuna attività
piazzabile lì) rende il modello **più stretto** del bound, mai più lasco:
direzione sicura.

### 1.4 Il modello resta ≥ il checker sulle istanze *soddisfacibili*

Poiché `soglia_mezze = min(minimo, D − IP) ≤ minimo`, il modello non è **mai**
più stretto del checker su questo ramo. E poiché il massimo raggiungibile è
`D − IP`, il clamp scatta **solo** quando il vincolo è insoddisfacibile per
qualunque orario. Conclusione: **sulle istanze soddisfacibili la traduzione è
esatta** — non perde soluzioni legali e non ne accetta di illegali.

Verificato empiricamente con un fuzz che il banco a testimone non può fare
(Ruling 20: `run_family` cancella tutti i `Placement`, quindi ADR-018 non è mai
esercitato sul banco). 40 istanze pseudocasuali su griglia `5×6`: 3–12 attività
in celle casuali, soglie `free_days`/`free_half_days` **derivate dal
testimone** (quindi sempre raggiungibili), e un sottoinsieme casuale del
testimone **congelato** (`LOCKED_IN_PLACE`); poi `solve → apply →
check_schedule`.

```
40 passed in 2.75s
```

Il fuzz **discrimina**: disabilitando `model.Add(sum(mezze_libere) >= soglia_mezze)`
diventa `24 failed, 16 passed`. Non è un fuzz vacuo.

### 1.5 Il ramo `free_days` e `ArrivalDepartureBuilder` non sono stati toccati

Verificato non a occhio ma per **confronto di AST dei corpi dei metodi**, con
le docstring escluse (`git show 24a544d:…` contro `HEAD`):

```
('ArrivalDepartureBuilder', 'post') IDENTICO
('FreeGuaranteedBuilder', 'post') *** CAMBIATO ***
('MaxHalfDaysBuilder', 'post')    IDENTICO
('MaxHoursBuilder', 'post')       IDENTICO
('MinDistributionBuilder', 'post') IDENTICO
```

**E il difetto di Important 1 non esiste lì in altra forma**:

- `free_days`: una giornata contribuisce al massimo **1** a `giorni_liberi`
  (`libero + attivo == 1`), e le giornate toccate dal passato non generano
  letterale — `D − giorni_persi` è il massimo **esatto**, non sovrastimato;
- `ARRIVAL_DEPARTURE`: una giornata contribuisce al massimo **1** a `conformi`,
  e i giorni `persi` sono esclusi — `D − persi` è di nuovo il massimo esatto.

Fuzz gemello su `ARRIVAL_DEPARTURE` con congelate (40 istanze, finestra
`not_before`/`not_after` casuale, sottoinsieme casuale congelato):

```
40 passed in 2.45s
```

**Nota positiva, non richiesta**: in giro 1 è caduta la guardia
`and mezze_libere` del `if minimo_mezze:` (era in `8193f82`). Il clamp del
giro 2 la rende **inoffensiva per costruzione**: `mezze_libere` è vuota se e
solo se ogni metà di ogni giorno è congelata, cioè `IP == D`, e allora
`soglia_mezze = min(minimo, 0) = 0` e il vincolo posta `0 >= 0`. Nessun buco.

---

## 2. Important 2 — la docstring di `MinDistributionBuilder` — **CHIUSA**

### 2.1 Il codice non è stato toccato

Confermato dal confronto di AST sopra: `MinDistributionBuilder.post` è
**identico** a `24a544d`, docstring esclusa. Il diff sul quel blocco è
interamente testuale.

### 2.2 Il controesempio della nuova docstring è riproducibile

Sonda esatta come descritta (3 attività, `min_minutes_per_day=60`,
`min_days=3`, griglia `5×6`):

```
PARTE1 (tutte libere):                        OPTIMAL {1: (0, 0), 2: (3, 5), 3: (4, 5)}
PARTE2 (due congelate su day 0, slot 0 e 1):  INFEASIBLE {'attivita': 3, 'libere': 1,
                                                          'variabili': 67, 'constraint': 48, ...}
```

La docstring dice il vero, e dice **solo** il vero: la proprietà rivendicata è
ora quella locale al giorno («una congelata può solo far salire `sum(occ)` per
il giorno che occupa»), che è effettivamente una proprietà del predicato, e la
non-immunità a livello di vincolo è dichiarata con il suo controesempio. Anche
la seconda metà del paragrafo — «`ArrivalDepartureBuilder` e
`FreeGuaranteedBuilder` non hanno **nemmeno** la proprietà locale» — è vera:
lì una congelata in una fascia proibita, o su una metà che doveva restare
libera, consuma il minimo già a livello di singola giornata.

---

## 3. I due test nuovi testano comportamento vero

### `test_free_guaranteed_bound_delle_mezze_morde_ancora_senza_congelate` — **morde**

Disabilitata la riga `model.Add(sum(mezze_libere) >= soglia_mezze)`
(sostituita con `pass`), il test è **rosso 5 volte su 5** — e per la ragione
giusta, cioè il verdetto del checker, non lo status del solver:

```
>       assert violazioni(env["schedule"], {"free_guaranteed"}) == set()
E       AssertionError: assert {(('free_guar...ys', 5))), 3)} == set()
E         Extra items in the left set:
E         (('free_guaranteed', (1,), (), (('free_days', 2), ('free_half_days', 2),
E           ('min_free_days', 0), ('min_free_half_days', 5))), 0)   … (e le settimane 1, 2, 3)
```

Non è un test vacuo.

### `test_adr018_free_guaranteed_bound_delle_mezze_e_per_giorno` — corretto per come è fatto

È un test di **non-sovra-restrizione** (ADR-018): può fallire solo se il
modello è troppo stretto, e passerebbe anche con il builder assente. È la
forma inevitabile per un test di questa classe, ed è appaiato al precedente,
che copre l'altra direzione. La coppia è ben congegnata: nessuno dei due da
solo basterebbe, insieme chiudono entrambi i versi. La prova RED riprodotta al
§1.1 conferma che discrimina la correzione specifica.

---

## 4. Osservazioni nuove

### Minor 1 — con un parametro **irraggiungibile** il clamp accetta ora un orario che il checker boccia, anche su input pulito

`soglia_mezze = min(minimo_mezze, D − IP)` clampa al massimo **strutturale**,
non solo a ciò che il passato ha tolto. Quando `IP == 0` (nessuna congelata) e
`free_half_days > days_per_cycle`, il clamp scatta lo stesso — e il modello
diventa più lasco del checker su **input pulito**, cosa che il vecchio bound
(`min(minimo, 2D)`) non faceva mai.

**Sonda A** — `mini_school()` (5 giorni), 6 attività libere, nessuna congelata,
`free_half_days=6`:

```
SONDA-A status: OPTIMAL
SONDA-A violazioni dopo: [(('free_guaranteed', (1,), (), (('free_days', 0), ('free_half_days', 5),
                            ('min_free_days', 0), ('min_free_half_days', 6))), 0) … settimane 1,2,3]
SONDA-A nuove():         [ … le stesse quattro … ]
```

Con il bound di `24a544d` la stessa istanza era `INFEASIBLE`. Il punto 3 di
`run_family` («qualunque soluzione restituisca dev'essere pulita») è violato.

**Caso di controllo** — stessa istanza con `free_half_days=5` (raggiungibile):

```
CONTROLLO-A status: OPTIMAL
CONTROLLO-A nuove(): []
```

Il difetto è dunque **specifico del parametro irraggiungibile**, non un
allentamento generale.

**Perché resta Minor.** Quando `free_half_days > D − IP`, *nessun* orario
soddisfa il vincolo: il finding del checker è inevitabile, e non si perde
alcuna soluzione legale (§1.4). Le formule alternative peggiorano: `minimo − IP`
smette di mordere proprio il caso D1 verificato qui sotto, e riportare il clamp
a `2D` resuscita l'INFEASIBLE-per-colpa-del-passato che Important 1 esisteva
per eliminare. È un problema di **validazione del parametro**
(`free_half_days ≤ days_per_cycle`, `free_days ≤ days_per_cycle`,
`ARRIVAL_DEPARTURE.days ≤ days_per_cycle`), non di traduzione.

⚠ Da notare che i tre rami **non si comportano allo stesso modo** sul parametro
impossibile, il che è di per sé un piccolo incoerenza da annotare:

| ramo | parametro impossibile | esito |
|---|---|---|
| `free_half_days` | 6 su 5 giorni | `OPTIMAL`, soluzione bocciata dal checker, `nuove()` ≠ ∅ |
| `free_days` | 7 su 5 giorni | `INFEASIBLE` |
| `ARRIVAL_DEPARTURE.days` | 7 su 5 giorni | `OPTIMAL`, finding presente ma **`nuove()` = ∅** (il massimo coincide con l'orario vuoto di partenza) |

Suggerimento: rimandare al Task 17 insieme alla correzione della spec §3.1
già in agenda (Ruling 17), come validazione dei `params` a monte.

### Minor 2 — la Ruling 19 dice «l'oracolo differenziale tollera», e con l'attuale `nuove()` non è letteralmente vero

Ruling 19 chiude con: *«Costo se sbagliato: il vincolo diventa più lasco del
checker su input sporco, che l'oracolo differenziale tollera.»* Non lo tollera,
perché `Finding.key` include le **quantities**
(`domain/analysis/findings.py`): appena il solver migliora `free_half_days` da
0 a 2, la chiave cambia e `nuove()` la conta come **nuova**.

**Sonda D2** — 3 giorni interamente congelati (mattina + pomeriggio),
2 libere, `free_half_days=3` (massimo raggiungibile 2, quindi il clamp morde):

```
D2 prima: [… ('free_days', 2), ('free_half_days', 0), ('min_free_half_days', 3) …]
D2 status: OPTIMAL
D2 dopo:  [… ('free_days', 0), ('free_half_days', 2), ('min_free_half_days', 3) …]
D2 nuove: [… le quattro settimane …]      ← non vuoto
```

**Caso di controllo D1** — stessa istanza con `free_half_days=2`
(= massimo raggiungibile, nessun clamp):

```
D1 status: OPTIMAL
D1 dopo:  []
D1 nuove: []
```

Nessun test attuale ne risente: `free_guaranteed` non è nel `CODICI` di
`tests/test_solver_oracle.py` (che è ancora l'insieme delle cinque famiglie
dello spike), e `run_family` non congela mai nulla (Ruling 20). È quindi una
**incoerenza latente fra la Ruling e la semantica di `nuove()`**, non un rosso.
Da annotare quando il Task 17 estenderà `CODICI` alle famiglie nuove:
`nuove()` come è scritta oggi non distingue «peggiorato» da «migliorato ma
ancora violato».

### Minor 3 — deriva fra commento e codice in `tests/solver_harness.py` (preesistente, fuori dal diff)

La docstring di `_derive_free_guaranteed` cita ancora la guardia
`if minimo_mezze and mezze_libere:` come motivazione del proprio guardrail di
vacuità. Quella guardia esisteva in `8193f82` ma è caduta in `24a544d`: oggi il
builder legge `if minimo_mezze:`. Il guardrail resta comunque corretto (a
zero-zero il builder non posta nulla), è solo la giustificazione scritta a
essere obsoleta. È esattamente il tipo di deriva che la nota di provenienza del
report mette in guardia; non è però nel diff `24a544d..HEAD`, quindi la lascio
annotata e non richiesta.

---

## 5. Vincoli globali del piano

| vincolo | esito |
|---|---|
| la suite non diventa rossa né si rimpicciolisce | ✅ 267+2 → **269+2**, +2 = i due test nuovi |
| `domain/analysis/` non importa `ortools` | ✅ verificato: zero occorrenze della stringa in tutto il package |
| nessun builder reinventa una primitiva del vocabolario | ✅ il diff usa `v.halves()` (anzi la issa in una variabile locale, riducendo le chiamate) e `frozen_occupies` |
| nessun residuo calcolato a mano | ✅ nessun conteggio di congelate fatto in proprio: passa da `frozen_occupies` di `domain/solver/residual.py` |
| traduzione derivata **leggendo** il checker | ✅ la nuova prosa cita la forma esatta di `(not morning) + (not afternoon)`, e la tabella del §1.2 la conferma riga per riga |
| commenti/docstring in italiano, identificatori in inglese | ⚠ i nuovi identificatori locali (`giorni_interamente_persi`, `meta_perse_nel_giorno`) sono in italiano — ma è la convenzione **già stabilita** in questo file dai builder del Task 6 (`giorni_liberi`, `mezze_libere`, `qualificati`, `conformi`, `consumo`), accettata nelle review precedenti. Cambiarla solo qui peggiorerebbe la coerenza del file: non la segnalo come difetto |
| non determinismo di CP-SAT | ✅ nessuna intermittenza: `tests/test_solver_time_minimums.py` + `tests/test_solver_witness.py` rilanciati **6 volte**, sempre `62 passed, 2 skipped` |

---

## 6. Esito della suite

`venv/bin/pytest`, riga di riepilogo verbatim:

```
======================= 269 passed, 2 skipped in 22.29s ========================
```

Corrisponde all'attesa dichiarata (269 passed, 2 skipped).

---

## 7. Verdetto complessivo

**Il Task 7 si può chiudere così com'è. Non serve un giro 3.**

- Important 1 è chiusa, e il bound nuovo non è solo «meno sbagliato»: è
  **esatto** su tutte le istanze soddisfacibili, dimostrato per tabella contro
  il checker e per fuzz di 40 istanze con congelate (che discrimina, 24/40
  rosse a builder disabilitato).
- Important 2 è chiusa: il controesempio della docstring gira, e il codice di
  `MinDistributionBuilder` è dimostrato invariato per confronto di AST.
- I due test nuovi sono onesti: la controprova morde 5 su 5, e l'altro è la
  forma giusta per un test ADR-018.
- Le tre Minor sono tutte **rimandabili**: la prima e la seconda vanno alla
  spec del Task 17 (validazione dei `params`, e semantica di `nuove()` quando
  `CODICI` si allargherà), la terza è una riga di docstring fuori dal diff.

Tutte le modifiche temporanee sono state ripristinate e le sonde cancellate;
`git status` è pulito.
