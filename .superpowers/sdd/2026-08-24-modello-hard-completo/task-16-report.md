# Task 16 — `structural:didactic_weight` — report

Worktree `modello-hard-completo`, HEAD `e83c104`. **Nessun commit, nessun push**
(come da brief). Suite finale: **412 passed, 16 skipped** (baseline 400/15).

## Cosa e' stato scritto

| File | Stato |
|---|---|
| `domain/solver/builders/weight.py` | nuovo — `DidacticWeightBuilder`, registrato su `"structural:didactic_weight"` |
| `domain/solver/builders/__init__.py` | modificato — import di `weight` |
| `tests/solver_harness.py` | modificato — `_unita_studente` + `_derive_weight` in coda |
| `tests/test_solver_weight.py` | nuovo — 8 test |
| `tests/test_solver_registry.py` | modificato — chiave nuova e docstring |

Il registro dei builder e' ora **completo**: ventisei chiavi su ventisette, e la
ventisettesima (`structural:coverage`) non ne ha una per costruzione
(`PLACEMENT_INDEPENDENT`).

`domain/analysis/` non e' stato toccato.

## Il builder

Struttura come da brief: ciclo sulle firme di settimana, tre secchi (giornata,
mezza giornata, settimana) di termini `(peso, id, letterale)`, chiusi con
`residual_cap` — ADR-018 nella forma **separabile**, perche' ogni letterale
porta i propri punti di peso. Dedup su `(bucket, frozenset(id), cap)`, come
`OccupationBuilder`.

Le cose che il brief chiedeva di **verificare invece che dare per buone**:

- **Il verso di `half_of`.** `Vocabulary.half_of` restituisce `0` per
  `slot < morning_end_slot`, cioe' `0 = mattina`; il checker usa
  `"morning" if pl.start_slot < state.grid.morning_end_slot`. Il confronto
  `meta == 0 → max_weight_morning` del piano e' quindi **giusto**. Difeso da un
  test che fallisce se lo si inverte (vedi tabella delle mutazioni).
- **Piu' letterali della stessa attivita' nello stesso secchio.** E' corretto e
  ora e' **scritto** in un commento nel punto in cui accade: `AddExactlyOne` sul
  dominio dell'attivita' limita a 1 la somma dei suoi letterali, quindi il peso
  entra una volta sola — la stessa osservazione che `post_separable` fa per il
  proprio caso.
- **Il silenzio a tetti spenti** e' dichiarato in docstring (in una base reale i
  quattro tetti d'istituto sono tutti a «nessuno»).
- **La direzione dell'errore sulle firme** e' scritta in docstring: qui e' un
  **tetto**, quindi fondere le settimane sarebbe *conservativo* (come in
  `subject_constraints.py`), all'opposto del D.T.B. dove fondere **allarga**. Il
  ciclo per firma resta perche' e' piu' preciso ed e' la regola della casa.

Aggiunta rispetto al piano: `_student_keys` e' una funzione a modulo che riceve
`state.kinds` e i token, e ordina con `resource_sort_key` — l'ordine di
`frozenset` non e' deterministico fra processi, e i nomi delle variabili e
l'ordine dei constraint ne dipendevano.

**Costo sul Fermi: nullo, misurato.** `test_fermi_intero_misurato` prima e dopo
la registrazione del builder: **8140 variabili, 1082 constraint** in entrambi i
casi (i tetti del Fermi sono tutti `None`), `0.562s` contro `0.568s`. Il builder
costruisce comunque i tre secchi prima di scoprire che i tetti sono spenti: e'
stata una scelta deliberata, perche' un'uscita anticipata «tutti i tetti a
`None` → esci» renderebbe **non falsificabile** la mutazione «tratta `None` come
0» che difende `test_i_tetti_spenti_non_postano_nulla`. Il costo misurato non la
giustificherebbe comunque.

## Il derivatore — i due difetti del piano

**Difetto fatale confermato.** `_derive_weight` del piano non ha `return`;
`run_family` fa `if not potere: pytest.skip(...)`, quindi la famiglia sarebbe
**saltata su ogni seed**. Il derivatore riscritto restituisce **quanti tetti ha
davvero acceso**.

**Secondo difetto, misurato invece che argomentato.** Il piano somma su tutti i
token e prende il massimo sull'**unione** delle settimane. Sonda usa-e-getta su
25 seed, con la stessa randomizzazione dei pesi didattici in entrambi i casi
(cosi' l'unica differenza sono l'insieme dei token, la guardia e il per-firma), e
il builder **spento**:

| derivatore | seed vacui (il banco li salta) | testimone violato (deve essere 0) | seed su cui **morde** a builder spento |
|---|---|---|---|
| del piano (tutti i token, unione, nessuna guardia) | — (nessun valore di ritorno: **salta sempre**) | 0 / 25 | **6 / 25** (4, 11, 13, 17, 20, 21) |
| riscritto (unita'-studente, per firma, con guardia) | **0 / 25** | 0 / 25 | **14 / 25** (3, 4, 7, 8, 10, 11, 12, 13, 16, 17, 18, 20, 21, 24) |

I tetti del piano sono sistematicamente piu' larghi: p.es. seed 5, tetto
giornaliero **16** contro **13**; seed 16, **15** contro **12**; seed 24, **15**
contro **12**. E il tetto **settimanale** del piano non e' mai stato violato su
**nessuno** dei 25 seed — vedi sotto, non e' fortuna.

### Le tre correzioni

1. **Somma sulle unita'-studente** (`_unita_studente`, stessa regola di
   `_student_keys`: le parti nei token, o la classe se non ha partizioni), non
   su tutti i token.
2. **Massimo fra le firme**, non sull'unione.
3. **Guardia di violabilita'**: nessun tetto se il valore osservato e' `0`, e
   nessun tetto se e' `>=` del limite superiore del secchio. Il limite e'
   `min(peso totale dell'unita' in quella firma, peso massimo per fascia x fasce
   del secchio)`: un'unita'-studente non puo' essere occupata da due attivita'
   nella stessa fascia, quindi ogni fascia vale al massimo il `didactic_weight`
   piu' alto fra le sue attivita'.

⚠ **La prima versione della guardia non era un maggiorante, e a scoprirlo e'
stata la misura, non la rilettura.** Per la mezza giornata avevo usato le fasce
della meta' (`morning_end_slot`, oppure `slots_per_day - morning_end_slot`). E'
sbagliato: il checker attribuisce il peso alla meta' in cui l'attivita'
**comincia**, quindi una che comincia nell'ultima fascia del mattino pesa tutta
sul mattino pur occupando il pomeriggio. Misurato sul **seed 9**: mattino
osservato **8** contro un «limite» di **6** — un limite superato dall'osservato,
cioe' non un limite. La guardia scartava percio' tetti perfettamente violabili
(direzione innocua: si perde potere, non si guadagna un falso successo, ma si
perde). Corretto allargando la finestra di `durata massima - 1`. Effetto
misurato: i **cinque seed vacui** (1, 9, 14, 15, 23) scendono a **zero**, i tetti
accesi passano da 2,15 a **2,6** di media e i seed che mordono da 11 a **14**.

**Aggiunta non prevista dal brief**: il derivatore assegna alle materie un
`didactic_weight` casuale in `1..3`. Col default `1` il peso coincide con
`duration_slots`, e un builder che **ignorasse del tutto `didactic_weight`**
passerebbe il banco senza che nessuno se ne accorga.

### ⚠ Il tetto settimanale non e' derivabile da un testimone

Non e' una limitazione della fixture: e' strutturale. `AddExactlyOne` obbliga a
piazzare **tutte** le attivita', quindi il peso settimanale di un'unita' e' lo
stesso in **ogni** soluzione — e' il totale delle sue attivita' attive in quella
firma. Il massimo osservato nel testimone coincide col totale della peggiore
unita', e nessun piazzamento potra' mai superarlo: **qualunque tetto settimanale
soddisfatto dal testimone e' soddisfatto da ogni soluzione**. Lo stesso vale per
il tetto della classe, che e' un tetto settimanale. Un tetto piu' stretto
farebbe fallire il **passo 1** di `run_family` (il testimone stesso lo
violerebbe).

Le due sonde lo confermano sui numeri: il derivatore del piano accende il tetto
settimanale su tutti e 25 i seed e **non viene mai violato**, nemmeno a builder
spento.

Quindi il derivatore **non accende** il tetto settimanale (la guardia lo scarta),
e le due semantiche settimanali — istituto e classe, con la precedenza della
classe e il passaggio da `part_class` — sono coperte da **tre test scritti a
mano** in forma avversaria. La ragione e' scritta nella docstring di
`_derive_weight`, cosi' non sembra una dimenticanza.

### I numeri del derivatore, 25 seed

- **tetti accesi** (su tre possibili: giornata, mattino, pomeriggio): `3` su 17
  seed, `2` su 6, `1` su 2, **`0` su nessuno**. Media **2,6**. Nessun seed viene
  saltato dal banco.
- **testimoni violati: 0 / 25** — il passo 1 di `run_family` non e' mai in
  pericolo.
- **morde a builder spento: 14 / 25** (3, 4, 7, 8, 10, 11, 12, 13, 16, 17, 18,
  20, 21, 24).
- con il builder acceso: **OPTIMAL su 25/25 e zero violazioni**.

⚠ **«Morde» e' una misura stocastica.** `CpSolver` gira multi-thread e non
restituisce la stessa soluzione a ogni esecuzione: quale seed intercetti un
builder rotto cambia di corsa in corsa (misurato: la mutazione no-op rende rosso
il solo seed 4 in una corsa, i seed 3 e 4 in un'altra; la sonda su 25 seed dice
che il seed 3 morde). Non tocca la suite verde
— con il builder corretto **qualunque** soluzione soddisfa i tetti — ma va
saputo prima di dedurre qualcosa da un singolo seed.

## I test — `tests/test_solver_weight.py`

Niente `test_peso_sul_banco` (Ruling 16): `test_solver_witness.py::test_famiglia`
parametrizza gia' su `sorted(DERIVERS) x [1..5]`. I test che affermano la
**presenza** di un vincolo sono tutti in forma avversaria (Ruling 85):
`build_model` + `model.Add(x[...] == 1)` che forza la violazione, e INFEASIBLE
atteso. Il test del piano `test_il_tetto_giornaliero_distribuisce_il_carico`
**non e' stato copiato**, come da brief.

1. `test_il_tetto_giornaliero_morde` — tre pesi da 2 forzati nello stesso giorno
   con `max_weight_day = 4` → INFEASIBLE; due soli → FEASIBLE.
2. `test_mattina_e_pomeriggio_sono_secchi_distinti_e_non_invertiti` — con
   `morning = 4` e `afternoon = 2`, due pesi da 2 stanno nel mattino e non nel
   pomeriggio. Le due direzioni insieme catturano l'inversione.
3. `test_il_tetto_settimanale_di_istituto_morde` — tetto 6 → FEASIBLE, tetto 5 →
   INFEASIBLE senza forzare nulla (il peso settimanale non dipende dal
   piazzamento).
4. `test_il_tetto_della_classe_prevale_su_quello_di_istituto` — classe **piu'
   stretta** (4 contro 6) → INFEASIBLE; classe **piu' larga** (6 contro 4) →
   FEASIBLE.
5. `test_il_tetto_della_classe_si_trova_passando_dalla_parte` — classe
   partizionata: il peso sta sulle **parti**, e il tetto della classe si ritrova
   solo risalendo `part_class`.
6. `test_le_unita_studente_non_sono_tutti_i_token` — due classi, **stesso
   docente**, `max_weight_day = 3`: il peso non deve sommarsi sul docente.
7. `test_i_tetti_spenti_non_postano_nulla` — conteggio dei constraint a tetti
   `None` contro un tetto acceso.
8. `test_adr_018_un_secchio_gia_oltre_il_tetto_non_blocca_il_modello` — due
   congelate a 4 punti con tetto 3: il modello resta **fattibile**, e la libera
   e' esclusa da **tutte** le fasce di quel giorno (forzata una per una).

### Mutazioni e esiti (Ruling 89)

Ogni mutazione applicata al solo `domain/solver/builders/weight.py`, suite
`tests/test_solver_weight.py` + `tests/test_solver_witness.py -k "weight or
didactic"` (13 test, nessuno skip).

| mutazione | rossi | quali |
|---|---|---|
| `build()` reso no-op | **8 / 13** | i sette test di presenza, piu' il banco (seed 4) |
| verso mattina/pomeriggio invertito | 5 / 13 | `test_mattina_e_pomeriggio...`, banco seed 1, 2, 3, 4 |
| `class_caps` ignorato (sempre `settings.max_weight_week`) | 2 / 13 | i due test del tetto di classe |
| `part_class` saltato (`class_caps.get(key)`) | 1 / 13 | `..._si_trova_passando_dalla_parte` |
| `None` trattato come `0` | **13 / 13** | tutti, incluso `test_i_tetti_spenti_non_postano_nulla` |
| somma su **tutti i token** | 2 / 13 | `test_le_unita_studente_non_sono_tutti_i_token`, `..._della_classe_prevale...` |
| residuo senza clamp (`cap - consumo`) | 1 / 13 | `test_adr_018...` |

I due test di **assenza** sono difesi da mutazioni mirate, come chiesto:
`test_le_unita_studente_non_sono_tutti_i_token` dalla somma su tutti i token,
`test_i_tetti_spenti_non_postano_nulla` da «`None` come 0». Nota:
`test_i_tetti_spenti_non_postano_nulla` e' **anche** rosso sotto no-op, perche'
la sua seconda meta' («col tetto acceso i constraint aumentano») e'
un'asserzione di presenza — il brief lo dava per non falsificabile sotto no-op,
la forma scritta qui lo e'.

## Chiusura

- `venv/bin/pytest -q` → **413 passed, 15 skipped** (baseline 400 / 15).
  I 13 test in piu' sono gli 8 di `test_solver_weight.py` piu' i **cinque** seed
  del banco. **Nessuno skip in piu'**: la famiglia nuova non ne aggiunge, perche'
  dopo la correzione della guardia nessuno dei 25 seed misurati e' vacuo.
  (Con la prima versione della guardia lo skip in piu' c'era — seed 1 — ed e'
  stato misurato prima di correggerlo, non nascosto.)
- Nessuna contraddizione fra brief e codice da segnalare: i due difetti
  annunciati erano entrambi reali, e il codice del builder del piano era
  effettivamente giusto nella sostanza.

## Cosa resta fuori, dichiarato

- Il derivatore **non** esercita il tetto settimanale (ne' d'istituto ne' di
  classe): non e' derivabile da un testimone, per la ragione strutturale scritta
  sopra. Coperto da tre test scritti a mano.
- Il builder **non** ha una guardia «questo secchio non potrebbe sforare nemmeno
  con tutte le attivita' dentro», che `OccupationBuilder` ha invece per la
  capienza. Con i tetti spenti (il caso reale) non posta comunque nulla, e con i
  tetti accesi il costo misurato e' irrilevante; aggiungerla renderebbe
  `test_i_tetti_spenti_non_postano_nulla` non falsificabile nella sua meta' di
  presenza.
