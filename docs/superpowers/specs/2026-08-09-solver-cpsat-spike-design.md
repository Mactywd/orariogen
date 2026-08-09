# Spike CP-SAT — design

**Data:** 2026-08-09
**Stato:** approvato in sessione
**Predecessori:** [modello-dominio.md](../../modello-dominio.md) (schema v1, implementato),
[2026-07-26-analisi-vincoli-design.md](2026-07-26-analisi-vincoli-design.md) (il registro
dei predicati, implementato)

## Perché uno spike e non «il piano 3»

Quello che finora è stato chiamato «il piano 3 — il modello CP-SAT» contiene almeno
cinque sottosistemi indipendenti:

1. **ADR-017** — la regola di conflitto fra partizioni, oggi provvisoria e sbagliata
   nel caso generale;
2. **il modello di fattibilità** — variabili di piazzamento e i ventisette vincoli del
   registro tradotti in constraint, con maschere di settimana ed estrazione;
3. **gli alleggerimenti a quota** — le violazioni come variabili contate, mai penalità;
4. **l'ottimizzazione lessicografica** — criteri ordinati, docenti *o* classi, perdita
   tollerata;
5. **l'assegnazione delle aule** (seconda fase) e il **violatore di Hall**, che il piano
   2 ha esplicitamente rimandato qui.

Sono troppi per una spec sola. Questo documento specifica **solo il primo pezzo**: uno
spike che valida l'encoding e l'aggancio al registro su cinque vincoli, prima di
impegnarsi a tradurne ventisette.

## Criterio di riuscita

**Uno solo.** Lo spike è riuscito se `solve()` sul Fermi produce piazzamenti che,
riletti da `check_schedule`, non generano **alcun finding di severità `HARD`
appartenente alle cinque famiglie modellate**.

Il registro del piano 2 è l'oracolo. Non si scrive nessun oracolo a mano: se il solver
e i predicati sono d'accordo, o sono entrambi giusti o sono sbagliati nello stesso
modo — e sono stati scritti da due lati opposti, dal dato al constraint e dal dato al
predicato.

Non sono criteri di riuscita, ma vanno **misurati e riportati** perché vengono gratis
eseguendo il test:

- tempo di risoluzione e dimensione del modello sul Fermi (numero di variabili e di
  constraint), da confrontare con le spec successive quando i vincoli saranno 27;
- se l'istanza risulta infattibile, la diagnosi corrispondente di `analyze_capacity`.

### Un'incognita dichiarata

Il dataset Fermi contiene conflitti inseriti apposta
([`data/liceo-fermi/vincoli-attesi.md`](../../../data/liceo-fermi/vincoli-attesi.md)) e
le indisponibilità a giornata intera di D06, D09 e D15. **Non è noto** se sotto le sole
cinque famiglie modellate l'istanza sia fattibile.

Ripiego dichiarato: se il Fermi intero risulta `INFEASIBLE`, il test dell'oracolo gira
sul **sottoinsieme fattibile più grande** — le attività di una classe libere, tutte le
altre congelate al loro piazzamento — e l'infattibilità del Fermi intero è registrata
come **risultato dello spike**, non come suo fallimento. In entrambi i casi la spec è
soddisfatta: ciò che si valida è la corrispondenza fra constraint e predicati, non la
risolvibilità di quel particolare dataset.

## ADR-017 — gli atomi

### Il problema

`activity_tokens` (`domain/analysis/state.py`) dà a ogni attività un `frozenset` di
chiavi di occupazione, e `OccupationChecker` dichiara un conflitto quando in una cella
`(chiave, giorno, fascia)` si supera la capacità. La regola v1, dichiarata provvisoria
nel commento del codice:

> la classe intera occupa sé stessa e tutte le sue parti; la parte occupa solo sé
> stessa; il raggruppamento occupa le parti membre. Parti di partizioni diverse non
> confliggono (v1).

L'ultima frase è sbagliata nel caso generale: due partizioni sono due modi diversi di
dividere **gli stessi** studenti, quindi una parte dell'una e una parte dell'altra
condividono studenti e non possono stare nella stessa fascia. Sul Fermi il caso è
reale: `_REL`/`_ALT` è una partizione che copre l'intera classe, e confligge con
qualunque altra partizione della stessa classe.

Un insieme di token non sa esprimere la regola, perché deve dire due cose opposte sulla
stessa coppia di oggetti: parti della **stessa** partizione sono disgiunte, parti di
partizioni **diverse** si sovrappongono.

### La soluzione: cambiare cosa sono i token

Per una classe con partizioni `X = {x1, x2}` e `Y = {y1, y2}`, gli **atomi** sono le
celle del prodotto:

```
atomi(C) = { x1y1, x1y2, x2y1, x2y2 }

x1 occupa { x1y1, x1y2 }        y1 occupa { x1y1, x2y1 }
x2 occupa { x2y1, x2y2 }        y2 occupa { x1y2, x2y2 }
```

Allora `x1 ∩ x2 = ∅` (lo sdoppiamento resta parallelo) e `x1 ∩ y1 = {x1y1} ≠ ∅` (gli
studenti in comune confliggono). L'architettura a intersezione di insiemi resta intatta:
cambia solo cosa c'è dentro gli insiemi.

Questa è la struttura scartata come **interfaccia** durante il brainstorming — «le
intersezioni andrebbero dichiarate a mano». Qui non la dichiara nessuno: è **derivata**
dalla regola «conflitto per default» decisa in sede di design. Nessun campo nuovo,
nessuna migrazione.

### Chirurgia

Gli atomi si aggiungono ovunque una parte entri nelle chiavi, il che in
`activity_tokens` sono **tre rami, non uno**: le parti dichiarate direttamente
sull'attività (`activity.parts`), le parti membre di un raggruppamento trasversale
(`activity.groups` → `g.parts`) e l'espansione della classe intera
(`activity.classes` → tutte le `ClassPart` della classe). Vanno tutti e tre per la
stessa funzione — se il ramo dei raggruppamenti restasse sui pk grezzi, il bug che
ADR-017 chiude si ripresenterebbe per la via del `Group`, che è proprio la via che
attraversa più classi.

Gli atomi si aggiungono **solo alle classi con almeno due partizioni**. Una classe con
una sola partizione, o senza partizioni, non cambia di un bit: il Fermi, l'analisi di
capienza e i 116 test esistenti restano intatti. Il costo è il prodotto delle
cardinalità — una classe con partizioni 2×2 fa quattro atomi, e le classi reali hanno
una, due, al massimo tre partizioni di due o tre parti.

Le chiavi esistenti (pk della classe, pk delle parti) **restano tutte**: servono da
chiave di risorsa per i vincoli orari, per la capacità, per i nomi nelle causali. Gli
atomi si aggiungono accanto. La ridondanza è innocua: sono tutti vincoli hard, e
scattare due volte sullo stesso conflitto è indistinguibile dallo scattare una volta
dopo la deduplicazione per `Finding.key`.

### Conseguenze da gestire

- Le chiavi di occupazione non sono più tutte pk di `Resource`. Tutti i punti di
  **lettura** di `state.capacity`, `state.kinds`, `state.resource_names` usano già
  `.get(chiave, default)`, quindi non c'è nulla da cambiare nei checker: il requisito è
  solo che resti così, e che nessun nuovo codice indicizzi quelle mappe con `[]`.
- L'atomo ha comunque bisogno di un **nome leggibile** per la causale — nella forma
  «1A (studenti in comune fra partizioni)», non della sua chiave sintetica: va
  popolato in `resource_names` insieme agli altri.
- La chiave sintetica non è un intero. Il tipo delle chiavi si allarga a
  `int | str`; `occupancy` resta indicizzata da `(chiave, giorno, fascia)`.

Il cambiamento vive in `domain/analysis/state.py`, **non** nel solver: il conflitto è
già oggi un predicato dell'analisi, e correggerlo lì lo corregge per entrambe le facce.

## Il modello CP-SAT

### Variabili

- `x[a][d][s]` booleana: «l'attività *a* comincia il giorno *d* alla fascia *s*».
  Una `AddExactlyOne` per attività.
- Le celle **inammissibili non diventano variabili**. Griglia (la durata sta nella
  giornata), `Break.straddles`, giorni festivi e indisponibilità di livello `hard` sono
  un **pre-filtro sul dominio**, non constraint postati. È più piccolo, più veloce, e
  rende impossibile per costruzione ciò che il checker corrispondente vieta.
- Attività `SUSPENDED`: escluse dal modello. `NOT_SUSPENDABLE` non ha effetto qui — è un
  vincolo su chi può sospendere, non sul piazzamento: resta una variabile libera.
- Attività `FIXED` o `LOCKED_IN_PLACE`, e ogni attività **fuori** dall'estrazione
  richiesta: fissate al piazzamento corrente. Il congelamento incrementale — «risolvi
  queste 30, le altre 250 sono date», dichiarato l'unica modalità operativa reale di
  EDT — viene gratis, senza un meccanismo dedicato.

### Canalizzazione

- `occupied[k][d][s]` booleana: la chiave *k* è occupata in quella cella. Definita da
  `AddMaxEquality` sui letterali che la coprono.
- `works[k][d]` booleana: la chiave *k* lavora quel giorno.

Create **solo per le chiavi che un vincolo di cardinalità richiede davvero**, non per
tutte: su un modello con poche righe di `ResourceTimeConstraint` la canalizzazione
completa sarebbe quasi interamente inutilizzata.

### Settimane

I vincoli di occupazione si postano **per firma di settimana**, riusando
`conformity.week_signatures`: lo stesso raggruppamento che usa l'oracolo, così le due
facce vedono esattamente le stesse settimane. Due attività le cui maschere non si
intersecano possono condividere una cella, ed è corretto che possano.

Il piazzamento resta **uno solo per attività** (`Placement` è unico per
`(schedule, activity)`): le settimane condizionano *quali* attività sono in conflitto,
non *quante* collocazioni ha un'attività. La fascia variabile per periodo è fuori scope
da ADR-010.

## I cinque builder

Scelti per attraversare **tutti e tre i pattern di traduzione**, non per essere i più
facili: due strutturali di pre-filtro, uno strutturale di conflitto, uno di cardinalità
sulla risorsa, uno di relazione fra materie.

⚠ Le chiavi di registro dei due vincoli parametrici sono i **valori** degli enum, cioè
`"max_gap_hours"` e `"same_day_incompatible"` in minuscolo — `TextChoices` deriva da
`str`, quindi è il valore a fare da chiave nel dict. Si registrino sempre passando il
membro dell'enum (`ResourceTimeConstraint.Type.MAX_GAP_HOURS`), mai una stringa scritta
a mano.

| chiave di registro | traduzione |
|---|---|
| `structural:grid` | pre-filtro del dominio: la durata sta nella giornata, `Break.straddles` se `respects_breaks`, giorni festivi esclusi |
| `structural:unavailability` | pre-filtro del dominio: uno start `(d, s)` è ammissibile solo se **nessuna** delle fasce `s … s+durata-1` porta un'indisponibilità di livello `hard` su una qualsiasi risorsa dell'attività. Il checker itera su tutta la durata del piazzamento: un pre-filtro che guardasse solo la cella di partenza lascerebbe passare attività di durata ≥ 2 con la coda sull'indisponibilità |
| `structural:occupation` | per ogni `(chiave, giorno, fascia, firma di settimana)`: somma dei letterali che coprono la cella ≤ capacità della chiave. **Qui entrano gli atomi**, e qui entra la capacità cumulativa di aule e materiali |
| `ResourceTimeConstraint.Type.MAX_GAP_HOURS` | ⚠ **non** è una soglia per singolo buco: il checker somma i minuti di buco su **tutte** le mezze giornate della settimana e confronta il totale una volta sola. È un budget settimanale. Vedi sotto |
| `SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE` | con `A = B` (il caso dominante nei dati reali di EDT): al più un'occorrenza per `(unità, giorno)`. Con `A ≠ B`: le due materie non coesistono nella giornata |

### `MAX_GAP_HOURS`: il budget settimanale, in forma lineare

Il checker calcola, per ogni mezza giornata con almeno due fasce occupate,
`(ultima - prima + 1 - conteggio) × minuti_fascia`, **accumula su tutta la settimana** e
confronta il totale con `max_gap_minutes`. La traduzione deve fare esattamente questo,
e si esprime senza big-M introducendo per ogni `(chiave, giorno, mezza giornata)`:

- `before[s]` = ⋁ `occ[i]` per `i ≤ s` nella mezza giornata;
- `after[s]` = ⋁ `occ[j]` per `j ≥ s`;
- `covered[s] = before[s] ∧ after[s]` — la fascia sta fra la prima e l'ultima occupata.

Allora i minuti di buco della mezza giornata sono
`minuti_fascia × Σₛ (covered[s] − occ[s])`, ogni termine non negativo perché
`occ[s] ⇒ covered[s]`, e il vincolo è la somma su tutte le mezze giornate della
settimana `≤ max_gap_minutes`. I casi limite tornano da soli: zero o una fascia occupata
danno buco nullo, come nel checker (`if len(half) >= 2`).

Ogni builder deve **ricalcare il checker corrispondente**, non una sua
approssimazione: dove il checker e il builder divergono, l'oracolo fallisce, ed è
esattamente il segnale che lo spike esiste per produrre.

## Dove vivono i builder

Package **separato**, `domain/solver/`, con i builder registrati sotto le **stesse
chiavi** del registro dell'analisi.

Motivo: `domain/analysis/` oggi non dipende da `ortools`, e questo ha valore — la
diagnostica è utilizzabile dal SaaS e in una CI leggera senza tirarsi dietro un solver.
Il principio «una riga di dato, due facce» è garantito dalla **chiave condivisa** e da
un test, non dalla colocazione fisica.

```
domain/solver/
  __init__.py
  context.py      SolverContext: griglia, attività, celle ammissibili, letterali canalizzati
  model.py        build_model(schedule, extraction=None) -> (CpModel, SolverContext)
                  solve(schedule, extraction=None, time_limit=…) -> Solution
                  apply(solution, schedule) -> None   (scrive le righe Placement)
  registry.py     Builder, register(*chiavi), BUILDERS, all_builders()
  builders/
    grid.py  unavailability.py  occupation.py  time_constraints.py  subject_constraints.py
```

### L'interfaccia `Builder`

I cinque builder si dividono in **due tempi diversi**, e l'interfaccia deve dirlo
esplicitamente: due pre-filtrano il dominio *prima* che le variabili esistano, tre
postano constraint *dopo*. Un'unica classe con due hook, entrambi no-op per default:

```python
class Builder:
    def restrict(self, ctx) -> None:      # pre-filtro: toglie celle da ctx.cells[activity_id]
        ...
    def build(self, ctx, model) -> None:  # posta constraint sulle variabili già create
        ...
```

`build_model` esegue in ordine: costruisce il `SolverContext`, chiama `restrict()` di
tutti i builder, **poi** crea le variabili sulle celle sopravvissute, **poi** chiama
`build()` di tutti. Un builder che implementa `restrict()` non è tenuto a implementare
`build()`, e viceversa; chi non implementa nessuno dei due è un errore, e il test del
registro lo intercetta.

`SolverContext` è l'analogo di `ScheduleState`: costruito **una volta sola**, contiene
tutto ciò che i builder leggono (celle ammissibili per attività, token, capacità, firme
di settimana, letterali canalizzati). Vale la stessa regola di prestazione imposta al
piano 2: **nessuna query ORM dentro un builder**.

## Test

| file | cosa verifica |
|---|---|
| `tests/test_solver_atoms.py` | ADR-017: due parti di partizioni diverse confliggono, due parti della stessa partizione no, una classe con una sola partizione non cambia comportamento — e **lo stesso per le tre vie**: parte diretta, parte raggiunta via `Group`, parte raggiunta via espansione della classe intera |
| `tests/test_solver_context.py` | celle ammissibili (griglia, intervalli, festivi, indisponibilità — incluso il caso di **durata ≥ 2 con la coda sull'indisponibilità**), letterali canalizzati creati solo dove servono, congelamento di `FIXED`/fuori estrazione |
| `tests/test_solver_builders.py` | un test per vincolo, su istanze minime costruite apposta: il modello è infattibile quando e solo quando il checker corrispondente segnalerebbe. Per `MAX_GAP_HOURS` va coperto esplicitamente il caso che distingue budget da soglia: **due buchi da 1h in due giorni diversi con `D.T.B.` = 1h30** — legali sotto una soglia per buco, illegali sotto un budget settimanale |
| `tests/test_solver_oracle.py` | il criterio di riuscita: Fermi → `solve` → `apply` → `check_schedule` → zero `HARD` nelle cinque famiglie |
| `tests/test_solver_registry.py` | `BUILDERS.keys() ⊆ REGISTRY.keys()`, l'elenco esplicito dei cinque, e che ogni builder implementi almeno uno dei due hook |

Sul test del registro: **inclusione, non uguaglianza**. Lo spike implementa cinque
chiavi su ventisette; l'uguaglianza fra i due insiemi diventa il cancello quando
arriverà la spec del modello completo, ed è lì che va scritta.

## Fuori da questo spike

- Gli **altri ventidue vincoli** del registro.
- **Alleggerimenti e quote** (`RelaxationQuota` è già a schema, resta inutilizzato).
- **Ottimizzazione lessicografica** e criteri di qualità: lo spike cerca una soluzione
  ammissibile, non una buona. `solve()` si ferma al primo `FEASIBLE`.
- **Assegnazione delle aule** come seconda fase.
- **Violatore di Hall** (fase 5 dell'analisi EDT).
- Un comando `manage.py solve`: lo spike è API e test.
- Qualunque **deroga dichiarata** alla regola di conflitto fra partizioni: la regola è
  «conflitto per default», senza eccezioni, e un meccanismo di deroga si aggiungerà
  solo se un caso reale lo richiederà.

## Interfacce esposte (per la spec successiva)

```
build_model(schedule, extraction=None) -> (CpModel, SolverContext)
solve(schedule, extraction=None, time_limit=None) -> Solution
apply(solution, schedule) -> None
SolverContext e le sue celle ammissibili
il registro: registry.BUILDERS, register(*chiavi), e il punto di aggancio
  dei ventidue builder mancanti
```
