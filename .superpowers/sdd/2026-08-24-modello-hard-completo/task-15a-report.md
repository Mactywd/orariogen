# Task 15a — report

Worktree `modello-hard-completo`, HEAD `41ae062`. Nessun commit, nessun push.
Toccati due file soli: `tests/solver_harness.py` e `tests/test_solver_witness.py`.
`domain/analysis/` non e' stato toccato, e nemmeno `domain/solver/`.

## Esito

```
venv/bin/pytest -q   →  379 passed, 6 skipped
```

Baseline (HEAD, prima dell'arricchimento): **375 passed, 4 skipped**.
Punto di partenza dopo il solo arricchimento: **34 failed, 342 passed,
3 skipped** — identico alla misura del brief, quindi l'arricchimento
applicato e' quello del piano.

**Il criterio «4 skipped» non e' centrato: gli skip sono 6.** Due skip nuovi
in piu' (netto), misurati e spiegati sotto: **non sono stati nascosti
aggiustando un test**, e non c'e' nessun rosso residuo.

## 1. L'arricchimento

`_school`: una `ClassPartition` («LINGUA») sulla **prima** classe, due
`ClassPart` (`1A_ING`, `1A_TED`), e `"parts": parts` nel dizionario.
La seconda classe resta senza parti, cosi' ogni derivatore attraversa
entrambi i casi nello stesso testimone. Con una sola partizione `AtomMap`
non costruisce alcun atomo (ne servono due, ADR-017): le due parti restano
disgiunte fra loro e confliggono solo con la classe intera — che e'
esattamente lo sdoppiamento.

`_make_activities`: **in coda**, un'attivita' per parte (durata 1, maschera
casuale, un docente a caso, nessuna sede, `Service` sincronizzato sul
`effective_study_plan` della parte). In coda per non spostare nessuna
estrazione delle attivita' di classe dal flusso casuale condiviso.

Nessun seed e' diventato infattibile: **`capienza // 2` e' rimasto**, non
serviva scendere a `capienza // 3`.

## 2. I punti generalizzati

Helper unico `_chiavi_unita(w, klass)` = `{klass.pk, *parti della classe}`,
la stessa espansione di `_unit_keys`
(`domain/analysis/checkers/subject_constraints.py`).

**⚠ Il brief contraddice il codice, e vince il codice**: dice «sei
occorrenze» di `klass.pk in w.tokens[aid]`; a HEAD `41ae062` ne sono **nove**,
distribuite su **sette** derivatori (`_derive_forbidden_sequence` ne ha tre da
sola). Sostituite tutte con l'intersezione contro `_chiavi_unita`:

| derivatore | occorrenze |
|---|---|
| `_derive_same_day` | 1 |
| `_derive_same_half_day` | 1 |
| `_derive_two_days` | 1 |
| `_derive_max_hours_subject` (MAX_HOURS_DAY + MAX_HOURS_HALF_DAY) | 1 |
| `_derive_forbidden_sequence` | 3 |
| `_derive_weekly_order` | 1 |
| `_derive_imposed_succession` | 1 |
| `_derive_half_day_gap` | 1 |

Tolti i **quattro** `assert not ClassPart.objects.exists()`
(`_capienza_secchio`, `_derive_weekly_order`, `_derive_imposed_succession`,
`_derive_half_day_gap`): la condizione che asserivano e' ora falsa per
costruzione. Le loro docstring sono state riscritte, non cancellate — dicono
adesso che il filtro *usa* l'espansione, invece di dichiarare che non serve.

**Non solo il filtro.** I due punti dove cambia *cosa puo' coesistere*:

1. **`_ci_stanno`** presupponeva «stessa unita' ⇒ niente sovrapposizione». Con
   le parti e' falso: due attivita' su parti diverse della stessa partizione
   non condividono nessuna chiave di occupazione, quindi possono partire
   nella **stessa** fascia, e il checker le conta comunque entrambe nel
   secchio. Adesso il divieto di sovrapposizione si applica solo se
   `w.tokens[a] & w.tokens[b]` — che copre anche il caso, sulle stesse parti,
   di due attivita' che condividono il **docente**. La modifica va nella
   direzione generosa (piu' coppie dichiarate violabili), mai in quella
   stretta.
2. **`_capienza_secchio`** — sotto.

**Verificati e lasciati invariati** (ripercorsi uno per uno):

- `_derive_max_gap`, `_derive_max_hours`, `_derive_max_half_days`,
  `_derive_min_distribution`, `_derive_arrival_departure`,
  `_derive_free_guaranteed`, `_derive_max_presence`,
  `_derive_max_site_changes`: sono famiglie `ResourceTimeConstraint`, ancorate
  a `row.resource_id` (`checkers/time_constraints.py` riga 29), non a un'unita'
  espansa. Per una classe la chiave e' la sola `klass.pk`, e le attivita' di
  parte **non** occupano quella chiave — nel derivatore come nel checker.
  Espandere li' sarebbe stato un errore. Questo e' scritto nella docstring di
  `_chiavi_unita`, cosi' il prossimo che passa non «uniforma» i due casi.
- il conteggio per secchio di `_derive_same_day` / `_derive_same_half_day`:
  con due occorrenze nella stessa cella il conteggio fa 2 e la riga si scarta —
  che e' giusto, perche' il checker (`_BucketIncompatible`, `len(la) > 1`)
  la vedrebbe violata. Non serviva cambiare la regola, serviva che il filtro
  vedesse quelle occorrenze.
- `_coppie_sedi_vicine` (`structural:site_transition`) usa gia'
  `w.tokens[aid] & w.tokens[altro]`, cioe' «chiave condivisa», che e'
  esattamente il criterio del checker (che cammina per chiave di occupazione,
  parti incluse).
- `_derive_half_day_gap`: con due attivita' di parti diverse nella stessa
  mezza giornata lo scarto minimo osservato e' 0, quindi nessuna riga. Prima
  della generalizzazione il derivatore ne vedeva una sola e avrebbe creato una
  riga che il testimone stesso viola — e' il fallimento «il testimone viola la
  riga» della seconda specie del brief.

## 3. `_capienza_secchio`: da esatta a dichiaratamente generosa

La ricerca esatta di impacchettamento (`_massimo_pacchetto`) vieta la
sovrapposizione, e questo era un limite **superiore** solo finche' due
attivita' della stessa unita' non potevano partire insieme. Con le parti e'
diventata **stretta**, cioe' avrebbe scartato righe violabili.

Adesso la capienza si calcola per **strati** (`_strato`: `None` per le
attivita' di livello classe, l'insieme delle parti toccate altrimenti) e si
sommano:

```
capienza = pacchetto massimo delle attivita' di livello classe
         + somma, su ogni parte, del pacchetto massimo di quella parte
```

**Perche' resta generosa per costruzione**: la somma ignora i conflitti *fra*
strati, che esistono davvero — una attivita' di classe intera e una di parte
condividono la chiave della parte, e due attivita' qualunque possono
condividere il docente. Ignorare conflitti puo' solo alzare il valore, mai
abbassarlo: `capienza >= capienza vera`. E resta molto piu' fine della somma
nuda dei minuti, che e' cio' che serve alla guardia.

Sulla classe **senza** parti il calcolo e' identico a prima (uno strato solo).

La precondizione `simultaneous_capacity == 1` **resta e resta asserita**;
quella «nessuna `ClassPart`» e' sparita. Il costo e' dichiarato in docstring:
qualche riga inviolabile rientra nel banco — un caso di banco debole, non
copertura persa in silenzio.

Aggiornata anche la docstring di `_derive_max_hours_subject`, che ragionava su
`_capienza_secchio` come «massimo **esatto** sulla geometria»: la sussunzione
delle due guardie vecchie regge lo stesso (se la capienza supera `param`
servono ancora almeno due attivita', e due attivita' di strati diversi «ci
stanno» a maggior ragione), ma l'aggettivo non era piu' vero.

## 4. Gli skip: 4 → 6, misurati

Baseline (4): `arrival_departure` 2 e 4, `same_half_day_incompatible` 2,
`structural:site_transition` 3.
Adesso (6): `arrival_departure` 3 e 5, `same_day_incompatible` 3 e 5,
`same_half_day_incompatible` 2, `two_days_incompatible` 5.

Cioe': **uno sparito** (`site_transition` 3), **due spostati di seed**
(`arrival_departure`, sempre due, e' una famiglia di risorsa che le parti non
toccano: e' solo il rimescolamento di `_try_place`, che con due attivita' in
piu' pesca diversamente), **tre nuovi**.

Misura su venti semi, derivatore per derivatore, vecchio codice contro nuovo
(`potere == 0` = derivazione vacua):

| famiglia | vacui prima | vacui dopo | potere totale prima → dopo |
|---|---|---|---|
| `same_day_incompatible` | 3/20 | 6/20 | 26 → 22 |
| `two_days_incompatible` | 3/20 | 5/20 | 64 → 42 |
| `same_half_day_incompatible` | 2/20 | 2/20 | 48 → 38 |
| `half_day_gap` | 0/20 | 0/20 | 143 → 119 |
| `forbidden_sequence` | 0/20 | 0/20 | 119 → 107 |
| `weekly_order` | 0/20 | 0/20 | 82 → 79 |
| `imposed_succession` | 0/20 | 0/20 | 153 → 156 |
| `max_hours_day` / `max_hours_half_day` | 0/20 | 0/20 | 83 → 85 / 84 → 85 |
| `arrival_departure` | 12/20 | 11/20 | 8 → 9 |
| `structural:site_transition` | 1/20 | 2/20 | 19 → 18 |
| tutte le altre | 0/20 | 0/20 | invariato |

**Causa dei tre skip nuovi, verificata caso per caso** (non dedotta):

- **`same_day_incompatible` seed 3 — le parti, davvero.** Delle sei coppie
  (classe, materia), cinque erano gia' fuori gioco senza parti (due
  occorrenze nello stesso giorno, o materia assente/singola). La sesta,
  `1A/STO`, aveva `{giorno 0: 2, giorno 1: 1}` e **il doppione del giorno 0 e'
  l'attivita' di parte**: senza di essa la coppia avrebbe qualificato. Con
  essa la riga non e' derivabile — e non deve esserlo, perche' il checker
  vede la stessa occorrenza e boccerebbe il testimone.
- **`two_days_incompatible` seed 5 — le parti, davvero.** Su `1A` la materia
  `MAT` occupa i giorni `{0, 4}` senza le parti e `{0, 2, 3, 4}` con le parti.
  Con i giorni `{0,4}` la coppia orientata `MAT → STO` non e' mai consecutiva
  e la riga si crea; con `{0,2,3,4}` lo diventa, e cade l'ultima coppia
  derivabile della classe (`1B`, senza parti, non ne ha nessuna a questo
  seed).
- **`same_day_incompatible` seed 5 — non sono le parti.** Diagnosticate tutte
  e sei le coppie: sono **tutte** `doppio-senza-parte`, cioe' due occorrenze
  della stessa materia nello stesso giorno fra attivita' di classe. E' il
  rimescolamento di `_try_place` (griglia 5x6, 15 attivita' per classe: la
  densita' rende questa famiglia fragile a qualunque perturbazione), non
  l'arricchimento.

**Non sono un difetto della generalizzazione**: includere le occorrenze di
parte puo' solo *ridurre* le righe derivabili, perche' i due vincoli sono
della forma «non accade mai» e con piu' occorrenze accade piu' spesso. Una
riga derivata ignorandole nascerebbe **gia' violata dal testimone** — cioe' il
fallimento di prima specie del brief. Il banco perde due casi; non perde
copertura in silenzio.

Non ho toccato `SEEDS`: cambiare i semi per far sparire gli skip sarebbe
esattamente l'«aggiustare il test» che il brief vieta.

## 5. La prova che l'arricchimento morde

Due test nuovi in `tests/test_solver_witness.py`.

1. `test_le_parti_entrano_nel_testimone` (parametrizzato sui cinque semi del
   banco): esistono **esattamente due** attivita' piazzate i cui token
   contengono una parte e **non** la classe, una per parte. Verde su 5/5.

2. `test_due_parti_della_stessa_partizione_condividono_una_cella`: le due
   attivita' di parte partono nella **stessa cella**, hanno **settimane in
   comune** (simultaneita' vera, non riuso della cella in settimane diverse) e
   **nessuna chiave di occupazione in comune** — la proprieta' di ADR-017 che
   nessun banco esercitava.

   ⚠ **Nessuno dei cinque semi del banco la esibisce**: misurato 0/5, e 4/80
   sui primi ottanta semi (22, 28, 31, 53). Il test usa quindi il seme **22**,
   dichiarato in una costante con la misura accanto. L'informazione richiesta
   dal punto 5 del brief e' questa: l'arricchimento e' entrato, ma la
   *co-collocazione* delle due attivita' di parte e' un evento al ~5% per
   seme — le attivita' di parte sono due sole, e le celle libere per loro
   sono molte.

   **Misurato in piu'**: `run_family` su **tutte e ventuno** le famiglie ai
   quattro semi che esibiscono la co-collocazione (22, 28, 31, 53) →
   **78 passed, 6 skipped, zero rossi**. Cioe' derivatori e builder reggono
   la stessa cella. Non ho aggiunto quei semi a `SEEDS` (sarebbero +21 test e
   +3 skip, ed e' un allargamento del banco che il brief non chiede): se il
   Task 15 volesse un caso di banco *permanente* sulla co-collocazione, il
   seme 22 e' quello, e la misura e' gia' fatta.

## 6. Punti da segnalare

- **Il brief contro il codice**: sei occorrenze dichiarate, nove trovate
  (§2). Vince il codice, come da istruzione.
- **Copertura del monte ore**: le attivita' di parte sincronizzano il
  `Service` sul piano effettivo della parte, che e' quello della classe. Da
  quando la classe ha parti, `state.student_units` sostituisce la classe con
  le **parti** (`domain/analysis/state.py`), quindi `structural:coverage`
  confronta ogni parte con un piano che contiene anche i minuti dell'**altra**
  parte: il testimone produce `coverage_mismatch`. **Non e' un problema per il
  banco** — `run_family` filtra i finding sulle causali della famiglia sotto
  test, e `coverage` non e' un builder, quindi nessun test lo guarda. Lo
  segnalo perche' un futuro oracolo differenziale sul testimone (stile
  `test_solver_oracle.py`) lo incontrerebbe: li' andrebbe o dato a ciascuna
  parte un `Service` proprio, o dato alle parti un `study_plan` proprio.
  Nessuna riga di `domain/analysis/` e' da cambiare: e' la fixture a essere
  incompleta rispetto a quel checker.
- **Nessun rosso residuo**, quindi nessuna causa da attribuire al checker.
- Il tie-break di `_placed_of` (voce aperta in `CLAUDE.md`, Task 12) non e'
  stato toccato ed e' rimasto innocuo qui: il banco cancella tutti i
  piazzamenti prima di risolvere, quindi non ci sono attivita' congelate, e
  `_hard` confronta con l'insieme vuoto — l'identita' dell'argmin non entra
  nel confronto.
