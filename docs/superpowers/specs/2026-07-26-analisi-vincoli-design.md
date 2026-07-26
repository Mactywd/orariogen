# Analisi dei vincoli — design del sottosistema 2

> **Stato: approvato in sessione il 2026-07-26** (sei sezioni, con scelta
> esplicita di scope, copertura, deliverable e architettura). Realizza il
> principio 4 di [modello-dominio.md](../../modello-dominio.md) — «ogni vincolo
> esiste due volte» — nella sua prima metà: il **predicato** e la **causale
> nominata**. La seconda metà (il constraint CP-SAT) è il piano 3 e si
> aggancerà al registro definito qui.

**Obiettivo.** Dato lo schema Django del dominio v1 (implementato, 39 test
verdi), costruire il componente di analisi che risponde — senza solver e in
millisecondi — alle tre domande di [diagnostica.md](../../edt/diagnostica.md):

1. **Conformità**: questo orario rispetta i vincoli? Quali piazzamenti violano
   cosa, con quale frase?
2. **Dominio residuo** (`S.P.` / `Nr G.`): quante fasce e quanti giorni restano
   possibili per un'attività, nel rispetto di tutti i vincoli?
3. **Capienza** (fase 4 di EDT): per (unità, materia), quante ore *entrano al
   massimo* contro quante ne servono — il verdetto «10h00 da piazzare, 9h00
   piazzabili» con il vincolo colpevole mostrato.

## Scope

**Dentro:**

- predicato + causale per **ogni** famiglia e tipo rappresentato nello schema
  (copertura completa — un vincolo senza predicato è un buco silenzioso nel
  verdetto);
- dominio residuo calcolato, mai memorizzato ([ADR-007](../../decisioni.md));
- aritmetica di capienza per (unità, materia), incluso il caso **incrociato**
  unità × docente (diagnosi B osservata in EDT);
- comando `manage.py analyze` che stampa il report in stile EDT;
- le tre code del piano 1: test negativi sui CheckConstraint, correzione
  «12 tipi» → 13 in `modello-dominio.md`, nota su `InstituteSettings.load()`.

**Fuori (dichiarato):**

- il **violatore di Hall** (fase 5 di EDT: sottoinsiemi infattibili su risorse
  incrociate) → piano 3, dove può appoggiarsi al solver;
- la fase 3 di EDT (consigli di classe): altro dominio, fuori v1;
- ogni forma di UI oltre il comando; la serializzazione JSON arriverà con la UI;
- suggerimento automatico degli alleggerimenti (l'occasione di prodotto
  annotata in diagnostica.md resta per dopo: qui si producono i findings
  contabili su cui si costruirà).

## Architettura

Package `domain/analysis/` dentro l'app esistente — codice puro che legge i
modelli, nessuna nuova app Django, nessuna migrazione:

```
domain/analysis/
  findings.py       Finding (dataclass congelata) + Severity
  causali.py        catalogo: codice → template italiano (dal catalogo EDT)
  state.py          ScheduleState: snapshot in memoria di uno schedule
  registry.py       registro tipo-di-vincolo → checker; decoratore @register
  checkers/
    occupation.py           risorsa occupata + capacità simultanea (cumulativa)
    unavailability.py       i tre livelli rosso/giallo/verde, con data opzionale
    time_constraints.py     gli 8 tipi di ResourceTimeConstraint
    subject_constraints.py  i 13 tipi di SubjectConstraint
    weight.py               peso didattico (per parte, tetti in cascata)
    grid.py                 intervalli (respects_breaks), festivi, inizio vietato
    sites.py                transizione fra sedi (site_transition_slots)
    coverage.py             copertura monte ore per (materia × piano) — predicato
                            sui dati, anti-inversione STO/SCI
  conformity.py     check_schedule(schedule) → list[Finding]
  domain_size.py    residual_domain(activity, state) → DomainSize
  capacity.py       analyze_capacity(schedule|period) → list[CapacityFinding]
domain/management/commands/analyze.py
```

Tre principi ereditati e vincolanti:

- **findings mai su DB** (principio 2: i calcolati non si memorizzano);
- **l'orario invalido è ammesso** (principio 3): nessun predicato impedisce
  nulla — descrive;
- **esattezza**: ogni verdetto negativo dev'essere certo. La capienza si
  calcola come ottimo esatto di un rilassamento: se `richiesto > piazzabile`
  l'infattibilità è dimostrata, mai stimata. Un falso allarme distrugge la
  fiducia più in fretta di quanto un vero allarme la costruisca
  (diagnostica.md, verificato su EDT: 21/984 violazioni reali trovate).

## Findings e causali

```python
class Severity(StrEnum):
    HARD = "hard"            # rosso
    OPTIONAL = "optional"    # giallo
    PREFERENCE = "preference"  # verde

@dataclass(frozen=True)
class Finding:
    code: str                  # chiave della causale, es. "subject_same_day"
    message: str               # frase italiana già formattata
    severity: Severity
    resources: tuple[int, ...]   # pk delle Resource coinvolte
    activities: tuple[int, ...]  # pk delle Activity coinvolte
    quantities: Mapping[str, int]  # l'aritmetica: {"required_minutes": 600, ...}
```

- `causali.py` è un dizionario `codice → template` con le frasi riprese quasi
  alla lettera dal catalogo EDT (`AffSco_UtilDiagnostic`, ~170 causali — se ne
  trascrivono **solo quelle che i checker emettono davvero**, non l'intero
  catalogo):
  *«La classe è già occupata in un'attività»*, *«%s, troppe ore nella
  giornata»*, *«Massimo di ore di presenza superato»*…
- Le **quantità sono obbligatorie dove esistono**: il verdetto è un numero
  verificabile, non un aggettivo.
- La severità ricalca i tre pennelli: le violazioni `preference` si contano ma
  non rendono l'orario non conforme; le `optional` sono violabili solo con
  l'override globale ([modello-dominio.md](../../modello-dominio.md)).

`CapacityFinding` estende il concetto con i **quattro riquadri** osservati in
EDT: `statement` (enunciato in italiano), `detail` (l'aritmetica: attività,
minuti richiesti, minuti piazzabili, scarto), `culprits` (le righe di vincolo
responsabili, come riferimenti a `SubjectConstraint` / `ResourceTimeConstraint`
/ `ResourceUnavailability`), `remedies` (lista di codici rimedio con frase).

## ScheduleState e le settimane

Lo stato si costruisce **una volta** dal DB per un dato `Schedule`:

- occupazione `(resource_pk, day, slot) → [attività]`, con l'occupazione
  **propagata sulla gerarchia delle unità**: un'attività sulla classe intera
  occupa sé stessa e tutte le parti di tutte le sue partizioni; un'attività su
  una parte occupa solo quella parte; un raggruppamento occupa le parti
  membre. La regola operativa: due attività confliggono su un'unità se gli
  insiemi di parti espansi si intersecano, o se una è sulla classe intera e
  l'altra su qualunque sua parte. ⚠ Ne segue che due parti di **partizioni
  diverse** della stessa classe non confliggono mai fra loro in questa regola
  (v1): provvisorio, superato da [ADR-017](../../decisioni.md)
  (implementazione al piano 3);
- indice delle indisponibilità per risorsa (livello e data);
- aggregati per (risorsa, giorno): minuti di attività, minuti di presenza
  (**presenza ≠ attività**: la presenza include i buchi — due conteggi
  distinti, [modello-dominio.md](../../modello-dominio.md)), mezze giornate.

**Le maschere di settimane si trattano esattamente.** Lo stato è costruito
*per settimana*: `check_schedule` individua le **firme di settimana distinte**
(l'insieme delle attività attive in quella settimana), valuta ogni firma una
volta sola e fonde i findings identici annotando le settimane. Due attività
confliggono solo se le maschere si intersecano. Per il Fermi (tutto annuale)
la firma è una; per Q1/Q2 sono due; la sostituzione a un bit ne aggiunge una.

## Registro e copertura

```python
@register(SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
class SameDayIncompatibleChecker(Checker):
    causale = "subject_same_day"
    def check(self, state: ScheduleState) -> Iterator[Finding]: ...
```

- Una voce di registro per **ogni valore** di `ResourceTimeConstraint.Type`
  (8) e `SubjectConstraint.Type` (13), più i checker **strutturali** non
  legati a un enum: occupazione/capacità simultanea, indisponibilità,
  intervalli, festivi, transizione di sede, peso didattico, copertura monte
  ore.
- Il **test di completezza** fallisce se un valore di enum resta senza
  checker: la copertura completa è verificata dalla suite, non affidata alla
  disciplina.
- Nel piano 3 la stessa voce di registro riceverà il builder CP-SAT: il
  registro è il punto in cui «ogni vincolo esiste due volte» diventa una
  struttura, non una frase.
- Il peso didattico si conteggia **per parte, non per classe** (il caso
  `_REL`/`_ALT` verificato sui dati, [vincoli.md](../../edt/vincoli.md)), con
  i tetti in cascata (classe → istituto).

## Dominio residuo (`S.P.` / `Nr G.`)

```python
@dataclass(frozen=True)
class DomainSize:
    placements: int   # S.P.: fasce orarie possibili
    days: int         # Nr G.: giorni distinti possibili

def residual_domain(activity: Activity, state: ScheduleState) -> DomainSize: ...
```

Semantica del **piazzamento di prova**: per ogni (giorno, fascia di partenza)
in cui il blocco entra nella griglia, l'attività si piazza virtualmente e la
collocazione è ammissibile se non introduce **nuove violazioni hard** rispetto
alla baseline dello stato. Le violazioni preesistenti non squalificano: l'orario
invalido è ammesso, e il dominio residuo misura il *peggioramento*, non lo stato
assoluto. Se l'attività è già piazzata, il suo piazzamento si sospende prima del
conto (com'è in EDT: sospendendo un'attività i vicini salgono).

Prestazioni: la valutazione del delta è ristretta ai checker che toccano le
risorse dell'attività; obiettivo dichiarato «taglia Fermi (284 attività) ben
sotto il secondo per l'intera colonna `S.P.`», verificato da un test.

## Capienza (fase 4 di EDT)

Per ogni (unità, materia) con attività nel perimetro:

- `richiesto` = Σ durate delle attività (in minuti);
- `piazzabile` = **ottimo esatto** del sotto-problema isolato: i giorni/fasce
  disponibili dell'unità (indisponibilità hard, festivi) intersecati con quelli
  del docente assegnato quando unico (il caso incrociato), sotto i vincoli di
  materia applicabili (incompatibilità con sé stessa per mezza giornata /
  giornata / 2 giorni, max ore per giornata e mezza giornata) e i massimi orari
  dell'unità. L'istanza è minuscola (≤ 6 giorni × ~10 attività): si risolve
  per **enumerazione esatta** dell'assegnazione attività → giorno, senza
  euristiche.
- Se `richiesto > piazzabile`: `CapacityFinding` con i quattro riquadri, i
  vincoli colpevoli identificati per **sottrazione** (si rimuove una famiglia
  alla volta e si riottimizza: le famiglie la cui rimozione sana il deficit
  sono i colpevoli — è anche la base dei rimedi proposti).

Essendo il sotto-problema un rilassamento del problema vero, il verdetto
negativo è una dimostrazione. Il conto positivo (`richiesto ≤ piazzabile`) non
promette nulla — quello è il mestiere del solver e, per i casi collettivi, del
violatore di Hall (piano 3).

## Il comando

```
venv/bin/python manage.py analyze [--schedule N]
```

- senza `--schedule`: analisi di capienza sui **dati** (attività e vincoli),
  il momento «prima del calcolo» di EDT;
- con `--schedule`: anche conformità del piazzamento e colonna `S.P.` delle
  attività non piazzate, ordinata crescente (la lista di «cosa sta per
  diventare impiazzabile»);
- output in stile EDT: enunciato → dettaglio con l'aritmetica → soluzione
  (righe di vincolo colpevoli) → rimedi; chiusura con il **riepilogo
  navigabile** che a EDT manca (debolezza annotata in diagnostica.md);
- exit code ≠ 0 se restano incoerenze hard — usabile in CI.

## Test

1. **Completezza del registro** contro gli enum (vedi sopra).
2. **Unit test per checker** su scenari minimi costruiti a mano (una griglia
   piccola, due attività, il vincolo in esame).
3. **Le due diagnosi osservate di EDT, riprodotte come fixture**:
   - A — sei attività di LETTERE su una classe, incompatibilità della materia
     con sé stessa nella giornata, 5 giorni → `richiesto 600, piazzabile 540,
     scarto 60`, colpevole la riga di `SubjectConstraint`;
   - B — il caso incrociato: materia + giornate libere del docente, innocui
     separatamente e fatali insieme, con **entrambe** le righe nei culprits.
4. **Il Fermi arricchito**: i vincoli di
   [vincoli-attesi.md](../../../data/liceo-fermi/vincoli-attesi.md) entrano
   nella fixture (indisponibilità dei part-time D06/D09/D15, blocchi MAT del
   biennio); l'analisi di capienza sui dati Fermi senza piazzamenti non deve
   produrre verdetti negativi (il dataset è risolvibile per costruzione);
   la copertura monte ore rileva un'inversione STO/SCI iniettata ad arte.
5. **Conformità su orario costruito a mano**: un mini-orario con violazioni
   note produce esattamente i findings attesi (codici e quantità), e
   `manage.py analyze` esce con codice ≠ 0.
6. **Dominio residuo**: i valori si alzano sospendendo un'attività e si
   riabbassano richiudendo il buco (il comportamento osservato in EDT); test
   di prestazione sulla taglia Fermi.
7. **Le code del piano 1**: test negativi sui due `_EXACTLY_ONE_UNIT`,
   `uniq_partition_per_class`, quota globale con `resource NULL`,
   `straddles` con durata 1.

## Interfacce esposte (per il piano 3)

- `check_schedule(schedule) -> list[Finding]`
- `ScheduleState.build(schedule, week=None)` e le sue mappe di occupazione
- `residual_domain(activity, state) -> DomainSize`
- `analyze_capacity(period) -> list[CapacityFinding]`
- il registro: `registry.checkers_for(constraint_row)` e il punto di aggancio
  del futuro builder CP-SAT
