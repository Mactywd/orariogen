# Alleggerimenti a quota e ottimizzazione lessicografica — design

**Data.** 2026-08-26
**Stato.** Bozza. Le **quattro decisioni aperte sono state chiuse in sessione**
il 2026-08-26 (D1–D4, marcate «deciso» dove comparivano); il resto del documento
resta rivedibile. **L'ondata 1 è implementata** — vedi il piano e il changelog
di `CLAUDE.md`; §2 è quindi consuntivo, non progetto.
**Segue.** Il modello hard completo ([spec](2026-08-24-modello-hard-completo-design.md),
merge `528cebe`): ventisei builder su ventisette, 450 test verdi.
**Precede.** Il piano di implementazione (§7).

---

## 0. Il pezzo che è, e la frase che lo motiva

È il **pezzo 3** dei quattro in cui §0 della spec precedente aveva decomposto il
lavoro dopo lo spike. Dipende dal pezzo 1 — non si allenta un vincolo che non è
stato modellato — ed è indipendente dal 2 (le aule) e dal 4 (il violatore di
Hall).

La frase che lo motiva è una sola: **oggi il solver sa rispondere solo «tutto o
niente»**. `build_model` posta `AddExactlyOne` su ogni attività, quindi
un'istanza sovravincolata — che è il caso normale di una scuola vera, non
l'eccezione — produce `INFEASIBLE` e nient'altro. EDT non lo fa mai: piazza quel
che può, lascia le altre **scartate** e le nomina, e solo allora offre
l'alleggerimento. Le tre righe di `motore-risoluzione.md` che descrivono il
governo dei compromessi in EDT sono anche l'indice di questa spec:

| Livello | Meccanismo in EDT | Qui |
|---|---|---|
| vincoli | **hard**, rilassabili a **quota** | §3 |
| qualità | criteri in **ordine lessicografico** | §4, parzialmente |
| arbitraggio docenti ↔ classi | **perdita di qualità tollerata** | **fuori** (§8) |

Nessuno dei tre è una somma pesata, ed è la ragione per cui questa spec non
contiene la parola «penalità» se non per escluderla.

## 1. Le tre cose che questo pezzo aggiunge

1. **Lo scarto diventa uno stato del modello**, non un fallimento del solve
   (§2). È il prerequisito di tutto il resto: l'alleggerimento in EDT esiste
   *per ridurre gli scarti*, quindi senza scarti non ha nulla da ridurre.
2. **L'alleggerimento a quota** (§3): un vincolo rilassabile non diventa soft,
   resta hard con un numero massimo di violazioni attribuito per famiglia e per
   risorsa.
3. **La catena lessicografica** (§4), che è il modo in cui la strategia a due
   passate di EDT si esprime in un modello solo.

E abilita il quarto: **`manage.py solve`**, che la spec precedente dichiarava
sensato «quando esistono gli alleggerimenti, perché prima saprebbe dire soltanto
`INFEASIBLE`».

## 2. Lo scarto

### 2.1 L'encoding

Oggi, in `model.py`:

```python
if lits:
    model.AddExactlyOne(lits)
else:
    ... # dominio vuoto → modello deliberatamente infattibile
```

Diventa, per ogni attività **libera**:

```python
piazzata[aid] = model.NewBoolVar(f"piazzata_{aid}")
model.Add(sum(lits) == piazzata[aid])
```

Le **congelate** non cambiano: il loro dominio ha cardinalità uno, `piazzata`
vale 1 per costruzione, e ogni proprietà di ADR-018 che poggia su «il letterale
di una congelata è noto a tempo di costruzione» resta vera parola per parola.

⚠ **Il ramo del dominio vuoto sparisce, e non è una perdita.** Un'attività i cui
pre-filtri non lasciano una sola cella oggi rende infattibile l'intero modello;
domani è semplicemente scartata, con la sua causale. È lo stato che EDT mostra
di suo — le 284 attività del Fermi nascono tutte «Non piazzata» — e trasforma
una diagnosi muta in una nominata. **Due test cambiano significato e vanno
riscritti**, non cancellati: `test_solver_model.py::test_dominio_vuoto_rende_il_modello_infattibile`
e `test_solver_prefilters.py:81`; entrambi devono continuare a dimostrare che il
dominio è vuoto, ma pretendendo lo **scarto nominato** invece di `INFEASIBLE`.

### 2.2 ⚠ Lo scarto va nominato in `domain/analysis`, o l'oracolo diventa vacuo

**Verificato leggendo il codice, non ricordandolo**: in
`domain/analysis/causali.py` non esiste alcuna causale sul non-piazzamento, e
nessun checker guarda le attività prive di `Placement` — `ScheduleState`
costruisce l'occupazione **dai piazzamenti**, quindi un'attività scartata non
produce nulla.

Conseguenza, ed è la trappola più grossa di questo pezzo: **appena
`AddExactlyOne` cade, «scarta tutto» diventa una soluzione perfettamente pulita
per l'oracolo differenziale.** Zero attività piazzate ⇒ zero occupazioni ⇒ zero
finding ⇒ verde. È la settima forma di vacuità di §9.8 della spec precedente,
questa volta prevista *prima* invece che scoperta dopo.

Quindi lo scarto entra nel registro dei predicati come tutti gli altri:

- causale nuova in `causali.py` — il testo di EDT è già scritto e si riusa:
  «l'attività non è piazzata»;
- checker nuovo sotto una chiave `structural:placement`, che emette un finding
  per ogni attività senza piazzamento;
- e il suo **builder è la macchina di §2.1**: il registro resta in parità
  («una riga di dato, due facce»), e il ventisettesimo checker senza builder
  resta uno solo — `structural:coverage`.

**D2 — deciso: `HARD`.** In EDT «Non piazzata» è uno *stato*, non una
violazione; nel nostro registro `HARD` significa «va risolto», ed è ciò che
l'oracolo deve contare. Una severità nuova avrebbe toccato `findings.py`,
l'ordinamento delle severità, i report di `analyze` e ogni test che filtra per
`HARD`, per una distinzione che nessuno di quei percorsi userebbe. La causale
dice in chiaro che l'orario è **incompleto**, non illegale.

### 2.3 🔑 Il tetto inevadibile smette di esserlo

§9.5 della spec precedente aveva trovato un caso che «nessun builder può
risolvere»: il tetto **settimanale** del peso didattico. L'argomento era che
`AddExactlyOne` obbliga a piazzare tutto, che il secchio settimanale
dell'unità-studente contiene *tutte* le celle candidate, e che quindi la somma
dei letterali liberi è una **costante** — il vincolo è vero sempre o falso
sempre, e le attività libere «vanno collocate, e ovunque vadano pesano».

**Quella costante era `AddExactlyOne`.** Con `sum(lits) == piazzata[aid]` la
somma torna a dipendere dalle decisioni, e il tetto torna evadibile nel solo
modo in cui EDT lo evade: **scartando**. Il rimedio che §9.5 proponeva — una
`Finding.key` più grossolana per le famiglie indipendenti dal piazzamento —
diventa una scelta invece di un obbligo.

⚠ **Non lo risolve del tutto, e va detto**: se a sforare il tetto sono le sole
congelate, il finding resta comunque, perché il passato non si scarta. La metà
che questo pezzo chiude è quella delle **libere**; l'altra resta ciò che
ADR-018 dice che sia — un fatto, non una decisione.

### 2.4 Cosa **non** cambia

`structural:coverage` è `PLACEMENT_INDEPENDENT` e — verificato rileggendo
`checkers/coverage.py` — conta `state.activities`, cioè le attività **piazzate o
no**, confrontandole con i servizi anagrafici. Ammettere gli scarti non lo
tocca: un'attività scartata esiste ancora. La ragione per cui non ha un builder
(«il solver non crea né distrugge attività») resta vera: scartare non è
distruggere.

## 3. L'alleggerimento a quota

### 3.1 La forma

Per ogni riga di vincolo **alleggeribile** con quota attiva:

```
expr <= cap + margine · v          v ∈ {0,1}
Σ v  <= max_violations             per (famiglia, risorsa)
```

Mai `minimize(w₁·a + w₂·b)`. Il letterale `v` **non entra in una somma pesata**:
entra in un conteggio con un tetto, ed eventualmente in un livello
lessicografico (§4).

Con `max_violations = 0` — cioè in assenza di una riga `RelaxationQuota` — non
si crea nessun `v` e si posta il vincolo di oggi, **identico**. È la proprietà
che rende questo pezzo conservativo per costruzione, ed è un test (§6.1), non
un'affermazione.

### 3.2 ⚠ Lo schema approvato non porta il margine

`RelaxationQuota` è `(family, resource?, max_violations)`. Ma il testo letterale
della finestra `Alleggerimenti` — riportato riga per riga in
`docs/edt/motore-risoluzione.md` — dice che quasi ogni alleggerimento ha **due**
parametri, non uno:

> `Massimo di ore dei docenti` → *«Autorizza un supplemento di … una volta per
> settimana e per docente»*
> `Giorni e 1/2 giornate libere` → *«Togli se necessario … mezze giornate libere
> per settimana»*
> `Peso didattico delle materie` → *«Autorizza un supplemento di … un giorno per
> settimana»*

Il **quanto** (il margine) e il **quante volte** (la quota). Il nostro schema ha
solo il secondo. Alcune famiglie hanno davvero solo la quota — `Incompatibilità
materie` è *«non considerare le incompatibilità … una sola volta al giorno»*,
puro conteggio — quindi il margine è **per famiglia**, non universale.

**Proposta**: un `params = JSONField(default=dict)` su `RelaxationQuota`, con la
stessa disciplina già in uso su `ResourceTimeConstraint` (chiavi attese
documentate per famiglia nel docstring), e un campo
`max_relaxed_constraints_per_resource` su `InstituteSettings` per il tetto
globale della finestra (*«Numero massimo di vincoli da alleggerire per
risorsa»*). Una migrazione piccola, additiva, senza dati da riscrivere.

### 3.3 La mappa delle undici righe di EDT sulle nostre famiglie

| Riga di EDT | Nostra famiglia | Parametro |
|---|---|---|
| `Massimo di ore dei docenti` / `delle classi` | `MAX_HOURS` | margine + quota |
| `Massimo di ore delle materie` | `SUBJECT_CONSTRAINT` (`max_hours_*`) | margine + quota |
| `Presenza massima dei docenti` | `MAX_PRESENCE` | margine + quota |
| `Massimo 1/2 gg lavoro` | `HALF_DAYS` | margine + quota |
| `Giorni e 1/2 giornate libere` | `FREE_GUARANTEED` | margine + quota |
| `Gestione Entrate / Uscite` | *(`ARRIVAL_DEPARTURE`)* | ⚠ non c'è in `Family` |
| `Incompatibilità materie` | `SUBJECT_CONSTRAINT` | quota sola |
| `Sequenze indesiderate di materie` | `SUBJECT_CONSTRAINT` | quota sola |
| `Peso didattico delle materie` | `DIDACTIC_WEIGHT` | margine + quota |
| `Cambi di sede` | `SITES` | margine + quota |
| *(indisponibilità gialle)* | `OPTIONAL_UNAVAILABILITY` | override globale |

Due cose da questa tabella. La prima: `RelaxationQuota.Family` ha dieci valori e
**non** ha `ARRIVAL_DEPARTURE`, che in EDT è alleggeribile — da aggiungere, o da
dichiarare fuori con una ragione. La seconda, più importante: **le famiglie che
non compaiono in questa tabella non sono alleggeribili**, e sono proprio quelle
strutturali — occupazione, griglia, `MIN_DISTRIBUTION`, `MAX_GAP_HOURS`. Restano
hard sempre, com'è in EDT: nessuna riga della finestra le nomina.

### 3.4 ⚠ I pre-filtri non si reificano

Griglia e indisponibilità rossa non sono constraint: vivono in `restrict()` e
**potano il dominio prima che le variabili esistano**. Un letterale di violazione
non ha nulla a cui agganciarsi, perché la cella proibita non è mai diventata una
variabile.

Quindi, per le sole famiglie con quota attiva che vivono nei pre-filtri
(`UNAVAILABILITY`, `OPTIONAL_UNAVAILABILITY`), l'alleggerimento **non è una
clausola: è un dominio più largo**. Il builder, quando la quota è > 0, non pota:
riammette le celle e posta su ciascuna un `v` che le è associato, con la somma
sotto il tetto. È l'unico punto di questa spec in cui cambia la *forma* di un
builder e non solo ciò che posta, e va scritto perché è anche l'unico in cui si
può sbagliare in silenzio: se il builder pota **e** riammette, la quota è
inerte e nessun test se ne accorge da solo.

### 3.5 ADR-018 × le quote

Due regole, entrambe conseguenze diritte di ADR-018:

1. **La violazione delle sole congelate non consuma quota.** È già la regola
   dell'implicazione (`any_free`): un vincolo i cui letterali vengono tutti da
   congelate non si posta, e quindi non crea nemmeno il suo `v`. Se il passato
   consumasse la quota, la scuola si troverebbe il margine di manovra già
   speso da un orario che non ha scelto.
2. **Il `v` si aggancia al residuo, non al tetto grezzo.** Dove oggi c'è
   `residual_cap(...)`, domani c'è `libere <= residuo + margine · v`. Il clamp a
   zero resta dov'è: alleggerire significa concedere un margine **sopra lo stato
   corrente**, mai pretendere che il passato venga riparato — che è la metà
   vietata del criterio di ADR-018.

## 4. La catena lessicografica

### 4.1 I livelli

CP-SAT non ha un lessicografico nativo: si realizza risolvendo per il criterio
1, **fissando** il valore ottenuto come vincolo, e ripartendo. Un solve per
livello.

I livelli proposti, nell'ordine:

| # | Criterio | Perché lì |
|---|---|---|
| **L1** | minimizza le **ore** scartate | è il danno che la scuola subisce |
| **L2** | minimizza il **numero** di attività scartate | spareggio a parità di ore |
| **L3** | minimizza le **violazioni nuove** (i `v` a 1) | si alleggerisce solo per salvare uno scarto |
| L4 | minimizza gli **spostamenti** rispetto ai piazzamenti esistenti | §4.3 |

🔑 **La strategia a due passate di EDT è questa catena, non due esecuzioni.**
*«Il piazzamento rispetta automaticamente tutti i vincoli; se rimangono delle
attività scartate, potete alleggerire»* è esattamente «L3 dopo L1»: il modello
consuma un alleggerimento solo quando quell'alleggerimento **riduce gli scarti**,
perché a scarti pari L3 preferisce zero violazioni.

**D1 — deciso: le ore prima, il numero come spareggio.** Uno scarto da 3h fa
più danno al monte ore di una classe di tre da 1h. EDT conta le attività nella
sua finestra ma riporta entrambi (*«284 attività / 288h00»*), quindi la scelta
non contraddice il prodotto: ne fissa lo spareggio.

### 4.2 🔑 L'obiettivo scioglie il debito del ramo pigro — se lo si vuole

§9.7 della spec precedente lascia aperto, sulla **famiglia** dei rami
disgiuntivi (`WeeklyOrderBuilder`, `MinDistributionBuilder`,
`FreeGuaranteedBuilder`), un debito la cui causa è testuale: *«il modello non ha
funzione di costo, quindi `riparato` e `riparato.Not()` sono alla pari e CP-SAT
non ha motivo di preferire la riparazione»*.

Questo pezzo introduce la prima funzione obiettivo del progetto. Se i booleani
di riparazione entrano in **L3** insieme ai `v`, il motivo di preferire la
riparazione esiste, e il debito si chiude come conseguenza invece che come
lavoro a sé. Le tre strade elencate in §9.7 — `AddHint`, clamp sul massimo
raggiungibile, o dichiararlo — ne guadagnano una quarta, che è anche l'unica
senza rischio semantico: **non cambia cosa il modello ammette, cambia cosa
preferisce**.

⚠ Con una distinzione da tenere ferma: un ramo non riparato **non è un
alleggerimento** e non deve consumare quota. Sono due cose che finiscono nello
stesso livello lessicografico ma in due conteggi separati.

**D3 — deciso: sì, i booleani di riparazione entrano in L3.** È la quarta
strada oltre alle tre elencate in §9.7, e l'unica senza rischio semantico. ⚠ Con
i due conteggi **separati** dentro lo stesso livello: una riparazione mancata non
consuma quota, perché non è un alleggerimento.

### 4.3 La stabilità, e ADR-010

`CLAUDE.md` porta da luglio una conseguenza di [ADR-010](../../decisioni.md) mai
implementata: rigenerando l'orario a ogni periodo serve un criterio **«mantieni
il più possibile le collocazioni precedenti»**, o il secondo quadrimestre viene
stravolto per tutti. È un livello lessicografico e nient'altro — minimizzare il
numero di attività che cambiano cella rispetto ai `Placement` esistenti — ed è
anche ciò che EDT fa nel risolutore passo-passo (*«minimizzare il numero di
variabili che cambiano valore rispetto alla soluzione corrente»*).

**D4 — deciso: dentro, come L4.** La macchina lessicografica la si scrive una
volta, e un quarto livello costa un `minimize` in più, non un'architettura.

### 4.4 Il costo, e il limite di tempo

Quattro livelli sono quattro solve. Il limite di tempo va **per livello**, e un
livello che scade lascia il vincolo di fissaggio all'ultimo valore trovato, non
al valore ottimo: la catena resta corretta, diventa solo meno ambiziosa. Da
misurare sul Fermi e sul banco a testimone, e da riportare nei `stats` della
`Solution` livello per livello — se non lo si misura, non si sa quale livello
costa.

## 5. Struttura dei file

```
domain/solver/
  relaxation.py     le quote: lettura di RelaxationQuota, creazione dei `v`,
                    i tetti per (famiglia, risorsa) e il tetto globale
  objective.py      la catena lessicografica: livelli, fissaggio, limite per livello
  model.py          `piazzata`, AddAtMostOne, solve() che percorre la catena
  builders/*.py     ogni builder alleggeribile chiede il proprio `v` a relaxation.py
domain/analysis/
  causali.py        la causale dello scarto
  checkers/placement.py   `structural:placement`
domain/models/constraints.py   RelaxationQuota.params (+ migrazione)
domain/models/institute.py     max_relaxed_constraints_per_resource (+ migrazione)
domain/management/commands/solve.py
```

## 6. Il criterio di riuscita

### 6.1 Le quote a zero danno il modello di oggi

Senza righe `RelaxationQuota`, tutti i 450 test verdi restano verdi — tranne i
due di §2.1, che cambiano significato e vanno riscritti. Non è un corollario: è
il primo test da scrivere, e la sua mutazione è banale (se un `v` viene creato
comunque, il conteggio dei constraint cambia).

### 6.2 Lo scarto è nominato, non muto

Su un'istanza deliberatamente infattibile — costruita dal banco a testimone
togliendo una fascia alla griglia, o stringendo un vincolo sotto la soglia — il
solver risponde **con degli scarti**, e `check_schedule` li nomina uno per uno.
⚠ Il test che conta non è «lo status non è INFEASIBLE»: è **quante** attività
sono scartate, perché «scarta tutto» supera il primo e fallisce il secondo.

### 6.3 La quota morde

La regola della casa, dalla spec precedente: *il test che dimostra che un
vincolo morde forza la violazione e attende `INFEASIBLE`*, mai «risolvi e
controlla dove è finita». Qui significa: con quota `k`, forzare `k+1`
violazioni della famiglia deve dare `INFEASIBLE`; con `k` deve essere fattibile.

### 6.4 L'alleggerimento fa il suo mestiere

Il test che lega i due pezzi, ed è quello che vale la spec: presa un'istanza in
cui **una** famiglia nota causa **uno** scarto, accendendo la quota di quella
famiglia lo scarto sparisce e `check_schedule` produce **esattamente una**
violazione, di quella famiglia, con la sua causale. Misurata dal checker, non
dal solver: è la stessa asimmetria che regge l'oracolo differenziale da agosto.

### 6.5 Cosa non si testa

La catena lessicografica **non** si testa sull'ottimalità dei livelli profondi
(un L4 subottimale non è un difetto di correttezza), ma sulla **monotonia**: L2
non peggiora L1, L3 non peggiora L2. È una proprietà, non un valore, e regge
anche quando un livello scade in tempo.

## 7. Le ondate

1. **Lo scarto, con L1 attaccato** — `piazzata`, il checker
   `structural:placement`, la causale, i due test da riscrivere, **e la
   minimizzazione delle ore scartate**.
   ⚠ **La prima stesura di questa spec metteva l'obiettivo nell'ondata 2 e
   dichiarava l'ondata 1 «già utile da sola»: è falso, ed è la stessa forma di
   §9.8.** Tolto `AddExactlyOne` senza metterci nulla sopra, «scarta tutto» è
   una soluzione *ammissibile* e CP-SAT la restituisce in un millisecondo: il
   modello non peggiora un po', smette di piazzare. L'obiettivo non è un
   miglioramento dell'ondata 1, è ciò che la rende un'ondata.
2. **La catena** vera e propria — L2, il fissaggio, il limite per livello e i
   `stats` livello per livello.
3. **Le quote** — schema (`params`, tetto globale), `relaxation.py`, e le
   famiglie a clausola (§3.1–3.3).
4. **Le quote nei pre-filtri** (§3.4), che è il caso storto e va da solo.
5. **L3**, e con esso la decisione D3 sul ramo pigro.
6. **L4**, la stabilità (se D4 = dentro).
7. **`manage.py solve`**, in stile `analyze`: scarti nominati, alleggerimenti
   consumati, livello per livello.

## 8. Fuori scope, dichiarato

- **Gli undici criteri di qualità** di `Ordinamento dei criteri` (buchi,
  distribuzione, preferenze verdi). Sono il *secondo* livello del governo dei
  compromessi in EDT, e in EDT stesso sono una **fase separata** dal
  piazzamento. La macchina lessicografica di §4 è ciò che li ospiterà, ma
  ospitarli non è questo pezzo.
- **La perdita di qualità tollerata** (arbitraggio docenti ↔ classi), che
  presuppone i criteri di cui sopra.
- **Il risolutore passo-passo** e `Piazza e sistema`: sono interfaccia
  interattiva sopra lo stesso motore, non motore.
- **Le aule** (pezzo 2) e **il violatore di Hall** (pezzo 4), invariati.
