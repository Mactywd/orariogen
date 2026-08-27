# L'assegnazione delle aule, la seconda fase

**Data**: 2026-08-27
**Stato**: approvato, da implementare
**Chiude**: l'ultimo pezzo dichiarato fuori nella nota di stato di `CLAUDE.md`

## 0. Il pezzo

Il solver piazza le attività e non assegna le aule. `Placement.assigned_room`
esiste nello schema dal giorno del modello di dominio, con la sua docstring che
lo chiama *«l'esito della seconda fase»*, e `activity_tokens` lo legge già come
chiave di occupazione — ma nessuno lo scrive mai.

**In EDT è un problema separato, e non per pigrizia del prodotto.** Ha criteri
propri (`TypeChoixOptimSalle`), un ottimizzatore dedicato
(`FicheEdt_OptimiseurSalles`, 30 stringhe) e una `ripartizione delle aule`
distinta dal calcolo dell'orario, con l'opzione letterale *«se possibile
mantenendo le assegnazioni della precedente ripartizione»*.
`motore-risoluzione.md` ne trae la conclusione che vale anche per noi:

> Assegnare le aule *dopo* aver piazzato le attività è una semplificazione
> legittima, validata da un prodotto maturo — non una scorciatoia.

🔑 **E il problema è più piccolo di quanto sembri**, per due misure indipendenti
già nei documenti. La prima: i vincoli veri sono **tre soli** — la finestra
`Aule disponibili` dichiara `Sedi distaccate`, `Indisponibilità opzionali`,
`Indisponibilità`, e nient'altro. La seconda: su 27 attività di una classe
intera della base di esempio, **una sola ha un'aula** (il laboratorio
linguistico). L'aula è un'eccezione dichiarata, non una colonna di ogni lezione.

## 1. Ambito: chi chiede un'aula

Entrano nel problema le attività **piazzate** con `Activity.rooms` non vuoto.
L'insieme delle aule dichiarate diventa l'insieme **candidato**: la fase ne
sceglie una e la scrive in `Placement.assigned_room`, che è già una FK singola —
lo schema approvato ha quindi già deciso che a un piazzamento corrisponde al
massimo un'aula.

Un'attività senza aule dichiarate non entra: vive implicitamente nell'aula
preferenziale della classe, e nessuno la assegna. Un'attività non piazzata non
entra: senza collocazione non c'è nessuna cella da occupare.

> **Perché `Activity.rooms` e non un modello nuovo.** Le alternative erano il
> gruppo di aule di EDT (`RELATIONSALLES`, `dcsSousSalle`), che `aule.md`
> dichiara *«un extra rimandabile»* e che costerebbe la gerarchia con la sua
> cascata; e un `ActivityRoomRequirement` accanto a `rooms`, cioè un secondo
> modo di dire quasi la stessa cosa, con un campo che in EDT non esiste. La
> convenzione della casa è non inventare campi.

### 1.1 ⚠ Il ramo `else` di `activity_tokens` diventa sbagliato

Oggi `activity_tokens` fa: se c'è `assigned_room` occupa quella, **altrimenti
occupa tutte le aule dichiarate**. Con l'insieme candidato quel ramo
sovrastimerebbe — un'attività che chiede «una fra le due palestre» le
occuperebbe entrambe — e produrrebbe conflitti `HARD` che l'assegnazione
risolverebbe da sola. Cioè manderebbe l'utente a smontare vincoli sani, che è
precisamente il difetto per cui il violatore di Hall è stato riscritto.

**Decisione: senza assegnazione, nessuna aula occupata**, e la richiesta
insoddisfatta si **nomina** invece di stimarla:

`structural:room_assignment` (ventinovesimo checker del registro), causale
*«l'attività chiede un'aula e non ne ha una assegnata»*, `HARD`, sulle sole
attività piazzate. È la stessa forma di `structural:placement` nato col pezzo 3:
descrive **un orario incompleto, non illegale**, e impedisce che «non assegnare
niente» sia una soluzione pulita per costruzione — la vacuità che il pezzo 3 ha
dovuto chiudere appena `AddExactlyOne` è caduto.

Il checker è **monotono sotto piazzamento** (`PLACEMENT_MONOTONE = True`, il
default): piazzare un'attività che chiede un'aula *aggiunge* la sua chiave, non
la ripara. Con una sola candidata il comportamento prima e dopo la fase
coincide, perché la scelta è forzata.

## 2. I vincoli — quattro, e tre sono quelli del prodotto

### 2.1 Indisponibilità dell'aula

L'aula è una `Resource`, quindi la tabella è già `ResourceUnavailability`:
nessun modello nuovo, e le indisponibilità dell'aula stanno dove stanno quelle
di docenti e classi (in EDT non esiste un `TNetContraintesSalle` fra le entità
persistenti — anche là è la tabella generica).

Pre-filtro sulle candidate, su **tutta la durata** del piazzamento e non sulla
sola fascia iniziale: è l'errore che il docstring di `UnavailabilityBuilder`
dichiara di aver già commesso una volta.

Il **giallo si rispetta come il rosso**, con l'override per **tipo** di risorsa
— `ignora_opzionali` con `Resource.Kind.ROOM`, la stessa forma del parametro che
già esiste, mai selettivo sulla singola aula. Il **verde non restringe nulla**:
è una preferenza, e questa fase ha un criterio solo.

### 2.2 Sede

L'aula dev'essere della sede dell'attività **quando `Activity.site` è
valorizzato**; se è `NULL`, nessun filtro.

⚠ **Non deduciamo la sede dall'aula.** `SiteTransitionChecker` legge la sede da
`Activity.site_id`: dedurla anche dall'aula assegnata creerebbe due sorgenti di
verità per la stessa cosa, e cambierebbe il significato di un checker che questo
pezzo non tocca. Corollario utile: **il punto aperto sul conteggio dei cambi di
sede non blocca questo pezzo**, perché la fase non produce cambi di sede.

### 2.3 Capienza simultanea

Per (aula, giorno, fascia, **firma di settimana**): la somma dei letterali sta
sotto `Resource.simultaneous_capacity`. È l'unico attributo dell'aula che il
solver deve rispettare, ed è lo stesso meccanismo dei materiali con quantità —
una risorsa cumulativa sola, come già fa `OccupationChecker`.

Le **firme di settimana** sono una dimensione, non un dettaglio: due attività di
settimane disgiunte non competono per la stessa cella. Si riusa
`week_signatures` di `conformity.py`, la stessa firma su cui posta il modello di
piazzamento. È la dimensione su cui questo repository ha già sbagliato una volta
(il D.T.B. del 2026-08-24), e su cui il Fermi non può fare da guardia perché ha
una firma sola.

### 2.4 ADR-018, ancora

Le attività **immobili** (`FIXED`, `LOCKED_IN_PLACE`) tengono l'aula che hanno:
bloccare una lezione in EDT significa non toccarla. Consumano quindi capienza
senza essere decisioni, e il tetto si posta sul **residuo clampato a zero**.

⚠ Il blocco riguarda **l'aula che hanno, non quella che non hanno**:
un'immobile che chiede un'aula e ha `assigned_room` a `NULL` resta una
decisione della fase. Leggerlo nell'altro modo — «immobile ⇒ fuori dal
problema» — renderebbe impossibile assegnare l'aula a una lezione bloccata in
griglia, che è il caso normale di un laboratorio fissato a mano su una fascia.

Se due immobili saturano da sole una palestra il modello resta **fattibile**: il
checker nomina la violazione e la fase assegna il resto. `INFEASIBLE` che nasce
dal vietare un peggioramento è ammesso; `INFEASIBLE` che nasce dal **pretendere
una riparazione** no — il criterio che unifica i cinque casi di ADR-018 nel
modello hard.

### 2.5 In negativo: cosa non è un vincolo

**Capienza in alunni, categoria dei locali e tipologie non vincolano.** Non
compaiono fra i vincoli ignorabili di `Aule disponibili`, e nella base di
esempio `Cap.` non è compilata su nessuna delle 18 aule: servono a raggruppare
la lista per chi sceglie a mano. Confrontare la capienza col massimo di alunni
del corso (`Al./Rid.`) sarebbe **nostra estensione**, e non entra in v1.

## 3. La rinuncia, e i due livelli

### 3.1 La rinuncia

Se per un'attività non resta nessuna aula legale, `assigned_room` resta `NULL` e
il modello **non** risponde `INFEASIBLE`. Stessa scelta del pezzo 3, stessa
ragione: la risposta utile a «il laboratorio non ci sta» è *quale* laboratorio è
rimasto fuori — materia, classe, docente, giorno e ora — non una parola sola su
tutta la scuola.

⚠ **E cambia la forma dei test**, esattamente come là. «Forza la violazione e
attendi `INFEASIBLE`» smette di funzionare, perché con la rinuncia ammessa la
risposta a un vincolo violato è `OPTIMAL` con un'assegnazione in meno. Serve
l'equivalente di `build_model(allow_unplaced=False)`: un interruttore
`allow_unassigned=False` che ripristina «ogni richiesta va soddisfatta», ed è il
modo di chiedere *questo vincolo morde?*.

### 3.2 I livelli

`solve_chain` è **già generica** sui livelli: prende una lista di
`Level(nome, var)`, fissa il valore raggiunto, passa al livello dopo, con limite
di tempo per livello e il suggerimento che porta la soluzione avanti. La parte
specifica del piazzamento sta tutta in `livelli()`, non nella catena. La fase
costruisce i suoi due e riusa il resto senza toccarlo.

- **L1 — i minuti senza aula.** Le ore, non il numero di attività: un
  laboratorio da 3h che resta senza spazio fa più danno di uno da 1h. Stessa
  unità di L1 del piazzamento.
- **L2 — i cambi rispetto alla ripartizione precedente.** Il criterio che EDT
  dichiara alla lettera. Conta le attività la cui aula assegnata differisce da
  quella che avevano prima; alla prima ripartizione, con `assigned_room` a
  `NULL` ovunque, il livello è muto e non costa niente.

**Uno spareggio lasciato fuori, e dichiarato**: nel pezzo 3 L1 ha come spareggio
il *numero* di attività scartate (decisione D1). Qui no — le rinunce sono poche
per costruzione e L2 spareggia già. Se servisse è un `IntVar` e una riga.

## 4. Il comando

`manage.py assign_rooms`, nella forma di `solve`: `--schedule` obbligatorio, più
`--limite`, `--lavoratori`, `--ignora-opzionali`, `--applica`. Legge i
piazzamenti già scritti dello schedule e **non li tocca mai**.

**Il rendiconto**, nello stesso ordine di `solve`: stato, dimensioni del
modello, i due livelli con valore, ottimo dimostrato o no, secondi; poi le
**rinunce nominate una per una**, con materia, classe, docente, giorno, ora e le
candidate che erano state chieste. Un'assegnazione mancata deve dire *quale*
laboratorio è rimasto fuori e *dove*, o il comando non serve a chi lo lancia.

**Non scrive niente senza `--applica`**: una ripartizione sovrascrive le aule di
una scuola intera, e il default non può essere scrivere.

⚠ **`--applica` deve anche cancellare.** Un'attività che prima aveva un'aula e
che la fase lascia senza deve tornare a `assigned_room = NULL`. È letteralmente
la mutazione che nel pezzo 3 era passata inosservata — il test su `apply()`
restava verde con la cancellazione rimossa, perché in quello scenario non
c'era una riga da cancellare — quindi il test qui nasce sull'istanza in cui una
riga c'è.

**Uscita ≠ 0 se resta una richiesta insoddisfatta**, come `analyze`. Dopo
`--applica` si rieseguono i checker e si dichiarano le **violazioni residue**:
un orario illegale è uno stato ammesso, ed è ciò che EDT fa con le sue 21
attività su 984.

## 5. Perché un solver, e non un flusso

Il progetto ha già scelto il flusso dove era **esatto**: il violatore di Hall
non usa il solver, perché il teorema di Hall in forma deficitaria si calcola su
flusso massimo e taglio minimo.

Qui non lo è. Per una singola fascia l'assegnazione sarebbe un matching
bipartito con capacità, risolvibile con `domain/analysis/flow.py`. Ma
un'attività dura più fasce e deve tenere **la stessa** aula per tutte, e la
stabilità è un costo: le fasce non si disaccoppiano. Il problema è **list
colouring di un grafo di intervalli**, NP-hard in generale.

Un greedy con riparazione — la forma del risolutore passo-passo di EDT —
darebbe una risposta senza nozione di ottimo dimostrato, cioè senza saper
distinguere «non c'è soluzione» da «non l'ho trovata». È l'opposto di ciò che il
resto del solver garantisce.

## 6. Criteri di riuscita

1. **L'oracolo differenziale**: assegna → scrivi → rileggi con `check_schedule`,
   e non compaiono finding `HARD` **nuovi** (occupazione sulle chiavi aula e
   `structural:room_assignment`). Nuovi, non zero: la premessa di ADR-018 è che
   un orario già illegale resti uno stato ammesso.
2. **Il banco a testimone**: si genera **prima** un'assegnazione valida a caso —
   aule con capienze diverse, indisponibilità che quell'assegnazione rispetta —
   e solo dopo si chiede alla fase di ricostruirla da zero, attendendo **zero
   rinunce**. Il generatore dichiara il proprio **potere vincolante**: un seme
   che non produce righe che stringano **salta**, invece di spacciarsi per un
   successo.
3. **Cinque casi scritti a mano** (§7).
4. **La mutazione**: spento ciascuno dei quattro vincoli, un insieme di rossi
   **distinto** per ciascuno. Due mutazioni con gli stessi rossi significano un
   test che misura la base e non la foglia — il corollario pagato coi quattro
   `PARTS_*`.

## 7. I casi scritti a mano

Ciascuno per una dimensione che il banco casuale non garantisce di esercitare.

- **Il vincolo morde**: due attività contemporanee, una sola candidata a
  capienza 1 → una rinuncia; con `allow_unassigned=False` → `INFEASIBLE`. È la
  regola della casa: forzare la violazione. «Risolvi e guarda dove è finita» su
  questo repository è misurato come rilevatore **debole** — coglieva un builder
  rotto 1 volta su 11.
- **ADR-018**: due immobili che saturano da sole una palestra. Si **forza lo
  status quo** e si attende che il modello non risponda `INFEASIBLE`.
- **Le firme di settimana**: due attività nella stessa cella su settimane
  disgiunte condividono un'aula a capienza 1. Scritto **prima** del codice, come
  le due trappole previste in spec per il violatore di Hall.
- **La durata**: un'aula indisponibile solo nella **seconda** fascia di un
  blocco da 2h esce dalle candidate.
- **La stabilità**: un'istanza dove L1 e L2 tirano in direzioni **opposte**, non
  a pareggio. Nell'ondata 2 del pezzo 3 il primo test del fissaggio usava
  un'istanza a pareggio, e la mutazione «togli `model.Add(level.var <= valore)`»
  lo lasciava verde: non affermava il meccanismo centrale.

## 8. Il Fermi

Il dataset va arricchito: laboratori per FIS/SCI/INF, palestra per MOT, aula
disegno per ARTE — le aule che `data/liceo-fermi/aule.md` progetta già e che
`tests/fermi.py` crea senza che nessuna attività le chieda. Oggi il problema sul
Fermi è **vuoto**.

⚠ Con l'avvertenza di sempre: anche arricchito misurerà il **costo**, non la
copertura — una firma di settimana sola, nessuna indisponibilità d'aula, e
capienze che non stringono. E `docs/edt/aule.md` resta marcato «le aule non sono
mai state inserite nella base del Fermi»: il nostro dataset le avrà,
l'osservazione in EDT no.

## 9. Cosa **non** entra

**Nessun ritorno sul piazzamento.** Se un laboratorio non c'è, la fase rinuncia;
non sposta la lezione per far entrare l'aula. È la conseguenza diretta delle due
fasi, accettata come la accetta EDT. Chi vede una rinuncia rilancia `solve` con
un vincolo in più, a mano.

**Del prodotto**, cose che esistono e che non facciamo:

- la **gerarchia padre/figlio** delle aule: nomina gli spazi, non esprime la
  capienza, che è già `simultaneous_capacity`;
- **`TypeIncompatibiliteSalle`** (11 valori) e i criteri **`TypeChoixOptimSalle`**:
  di entrambi conosciamo il **nome e non i valori** — mai osservati in UI, mai
  decodificati. Implementarli significherebbe inventarli. Vanno in «Ancora
  aperto» come punti da **osservare**, non come debito di codice;
- il **regime di prenotazione** (`Prenotabile da`, `Soglia di prenotazione`):
  altro dominio;
- **gli alleggerimenti a quota sulle aule.** La finestra dichiara i tre vincoli
  *ignorabili*, quindi una deroga esisterebbe; ma il giallo ha già il suo
  override per tipo di risorsa, il rosso in EDT non si alleggerisce mai, e la
  sede la teniamo hard in v1. Nessuna famiglia nuova in `RelaxationQuota` — ed è
  scritto perché la tentazione di aggiungerla è la stessa forma di errore che
  l'ondata 4 del pezzo 3 ha già corretto, quando «le quote nei pre-filtri» si è
  rivelata una premessa falsa.

**Nostro**, estensioni oltre EDT che non prendiamo:

- **materia → dotazione richiesta** («FIS va in laboratorio»): non esiste in
  EDT, il legame passa dalla classe o è deciso a mano sull'attività. Le aule
  candidate si **dichiarano**, non si deducono;
- la **capienza in alunni** confrontata col massimo del corso;
- ⚠ **`SchoolClass.preferred_room` resta descrittiva**, e la conseguenza va
  dichiarata perché è controintuitiva: due classi con la stessa aula
  preferenziale **non confliggono**, e nessun checker lo dirà. Farne
  occupazione reale è un pezzo suo.

## 10. Ondate

1. Il checker `structural:room_assignment` e il ramo `else` di
   `activity_tokens` (§1.1), con i test del registro.
2. Il modello: variabili, pre-filtri (§2.1, §2.2), capienza per firma (§2.3) e
   il residuo di ADR-018 (§2.4), con l'interruttore `allow_unassigned`.
3. I due livelli e il riuso di `solve_chain` (§3.2).
4. Il comando `assign_rooms` con `--applica` e il rendiconto (§4).
5. Il banco a testimone, l'oracolo differenziale e i cinque casi a mano
   (§6, §7).
6. Il Fermi arricchito, la misura e l'aggiornamento dei documenti (§8).
