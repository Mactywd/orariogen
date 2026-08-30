# Entità EDT — Aule

## Cos'è

Gli spazi fisici in cui si svolgono i corsi: aule ordinarie, laboratori, palestra,
aula magna.

## ⚠ Stato della fonte

> **Le aule non sono mai state inserite nella base del Fermi.** L'header
> `CARTEIDENTITE` di `example_2.edt` dichiara `NBSALLES = 0` (verificato
> 2026-07-26). Quindi
> [`data/liceo-fermi/aule.md`](../../data/liceo-fermi/aule.md) resta **progetto,
> non osservazione**, e va creato in EDT prima di poter provare qualunque cosa
> *sul nostro dataset*.
>
> **Il meccanismo però è ormai osservato in UI**, sulla base di esempio fornita
> con il prodotto (18 aule, 3 sedi, gruppi, tipologie): tutto ciò che segue senza
> marcatore è visto a schermo il 2026-07-26.
>
> **Aggiornamento 2026-08-28.** Il *nostro* dataset ha ora le aule e le
> attività che le chiedono (`tests/fermi.py`, `SPECIAL_ROOMS`): laboratori per
> FIS e SCI, aula di disegno per DIS, palestra per MOT, più `LAB-INF`
> **condiviso** fra le tre materie di laboratorio. Serve alla seconda fase
> (`domain/solver/rooms.py`), che senza attività richiedenti avrebbe un
> problema vuoto. ⚠ Resta **progetto e non osservazione**: in EDT le aule del
> Fermi non sono mai state inserite (`NBSALLES = 0`), quindi le candidate per
> materia sono una nostra scelta di dimensionamento, plausibile ma non vista a
> schermo. ⚠ E la condivisione di `LAB-INF` è deliberata: a **candidata unica**
> l'aula entra già nei token del piazzamento
> (`domain/analysis/state.py`, `_activity_tokens`), quindi la ripartizione si
> limiterebbe a confermare una scelta già fatta — zero gradi di libertà, e una
> misura incapace di fallire.

## La vista Aule, com'è

Orario > **Aule**, `Elenco delle aule`. Colonne osservate:

| Colonna | Cosa contiene |
|---|---|
| `Nome` | |
| `Sedi` | la sede di appartenenza (`Principale`, `Succ. 1`, `Succ. 2`) |
| `Cap.` | capienza — **vuota su tutte e 18** nella base di esempio |
| **`Qtà`** | **numero di attività simultanee ammesse** — vedi sotto |
| `Occ.` | ore occupate (calcolato) |
| `TOP` | tasso di occupazione % (calcolato) |
| `Gestori` | responsabile dell'aula |
| `Categoria` | categoria dei locali scolastici |
| `Assegnate` / `Picco d'occ.` | calcolati, valorizzati solo per `Qtà > 1` |

### 👁 L'elenco intero della base del produttore (2026-08-30)

Diciotto aule, e le sole righe con `Qtà > 1` portano le due colonne calcolate:

| Nome | Sede | Qtà | Occ. | TOP | Assegnate | Picco d'occ. |
|---|---|---|---|---|---|---|
| ▷ **PALESTRE** | Principale | 2 | 48h00 | 48% | **2** | **2** |
| **LAB.MUSICA** | Principale | 2 | 35h00 | 35% | **0** ⚠ | **2** |
| **PALESTRA succ** | Succ. 1 | 2 | 26h00 | 26% | **0** ⚠ | **2** |
| LAB.ARTISTICA | Principale | 1 | 21h00 | 72% | — | — |
| LAB. LINGUISTICO | Succ. 2 | 1 | 0h30 | 1% | — | — |

*(le altre tredici sono a `Qtà = 1` e `0h00`; `Cap.` è vuota su tutte e 18, e
il gestore è `Tosco Luisa` su tutte)*

🔑🔑 **`Picco d'occ.` è la quantità che ADR-021 calcola, e EDT la mette in una
colonna.** La prova sta in `LAB.MUSICA`: `Qtà = 2`, **`Assegnate = 0`**,
`Picco d'occ. = 2`. Cioè EDT conosce il picco di un gruppo a cui non è stata
assegnata **nessuna** aula — quindi il picco è calcolato **sul piazzamento**,
non sull'assegnazione. È esattamente il `load` di `structural:room_pool`, ed è
la conferma più diretta che abbiamo che **la fase 1 conta le aule**: il numero
esiste prima che qualunque aula sia scelta.

⚠ **E `Assegnate` costringe a rileggere `Qtà`.** Il paragrafo qui sotto
concludeva che `Qtà` non è il conteggio dei figli, perché `PALESTRA succ` ha
`Qtà = 2` e nessuna sotto-aula. Il **fatto** resta vero, ma l'interpretazione va
stretta: `Assegnate = 0` in **arancione** dice che per EDT quel record è
**incompleto**, non normale. La lettura che regge entrambe le osservazioni è una
sola, e la dà il titolo della finestra — *«PALESTRE - Gestione del gruppo di
aule (**2 aule massimo**)»* con `Assegnate al gruppo: **2/2**`:

- `Qtà` è la **capienza simultanea**, cioè quante attività il gruppo regge in
  parallelo — ed è quindi anche quante aule *dovrebbe* contenere;
- `Assegnate` è quante ne contiene **davvero**;
- `Assegnate < Qtà` è uno stato ammesso ma segnalato, e blocca l'ottimizzatore
  (*«Solamente i gruppi di aule interamente assegnati possono essere
  ottimizzati»*).

Per noi non cambia niente — `simultaneous_capacity` è `Qtà`, ed è ciò che il
piazzamento conta — ma cambia la frase: non è che il gruppo sia irrilevante, è
che **la capienza si dichiara prima e si popola dopo**.

⚠ **`TOP` non è spiegato.** Su quattro righe su cinque torna
`Occ. / (Qtà × 50h)` — 0h30→1%, 26h→26%, 35h→35%, 48h→48% su una settimana di
50 fasce, che è la griglia `5 × 10` della demo. **`LAB.ARTISTICA` no**: 21h su
50 farebbe 42%, non 72%. L'ipotesi che le riconcilia è che il denominatore sia
il tempo **disponibile** e non quello totale (21/29 ≈ 72%), cioè che le
indisponibilità dell'aula escano dal conto — ma è **[INFERENZA]**, e si conferma
con un passaggio del mouse sull'intestazione della colonna.

## 🔑 L'occupazione simultanea è un campo dell'aula

> ⚠ **Correzione.** Una versione precedente di questo file affermava che
> l'occupazione simultanea si modella creando un **gruppo di N aule**. È
> **sbagliato**: l'ipotesi veniva dalle stringhe di localizzazione, e
> l'osservazione in UI l'ha smentita.

Il menu contestuale dell'aula espone **`Modifica → Numero di aule`**: è una
proprietà scalare, modificabile direttamente, che si legge nella colonna `Qtà`.

La prova decisiva: nella base di esempio l'aula `PALESTRE succ` ha `Qtà = 2` **e
nessuna sotto-aula**. Se `Qtà` fosse il conteggio dei figli, quel record sarebbe
incoerente.

> **«La palestra regge 2 classi in parallelo» si dichiara con `Numero di aule =
> 2`.** Non servono due aule fittizie raggruppate.

Nella finestra `Aule disponibili` la stessa quantità compare come **frazione**
(`1 / 2`): occupazione corrente su capienza simultanea, calcolata sullo slot.

### Le sotto-aule sono un meccanismo separato

Esiste *anche* una gerarchia padre/figlio, ma serve ad altro: dare **identità e
nome ai singoli spazi**. Nella base, `PALESTRE` (`Qtà = 2`) contiene `Palestra 1`
e `Palestra 2`, mostrate in corsivo e nascoste finché non si espande il nodo.

Sui figli il campo `Gestori` riporta `Tosco Luisa (Gr.)`, dove il suffisso `(Gr.)`
significa *proveniente dal gruppo*, e `Sedi` è vuoto.

⚠ **Correzione (2026-07-26).** Avevo letto questa osservazione come conferma che la
cascata di default fosse *«un pattern trasversale del prodotto»*. **Non lo è.**

Il marcatore `(Gr.)` ha **due sole occorrenze** in tutte le 69 888 stringhe di
interfaccia, entrambe la stessa etichetta in due pannelli di **permessi su risorse
prenotabili** — accanto a `(G)` = *«è gestore»*. Riguarda `Gestionnaire` e
`Réservable par`, cioè **diritti**, non valori di configurazione. Nessun campo che
incida sul piazzamento lo porta.

L'osservazione in sé resta valida — un'aula figlia eredita davvero il gestore dal
contenitore — ma è un'**ereditarietà di ACL**, non la cascata di
[`Al./Rid.`](materie.md). Sono due meccanismi diversi che si somigliano in UI. Vedi
[ADR-003](../decisioni.md), emendato di conseguenza.

L'occupazione è contabilizzata **sul padre** (`48h00 / 48%`), non sui figli
(`0h00` entrambi).

Nota: `Modifica → Categoria dei locali scolastici` è **disabilitata** su un
contenitore. La categoria è un attributo delle aule foglia.

## Le tipologie — dotazioni, non tipi d'aula

`Modifica → Tipologie → Tipologie predefinite` apre un albero **a due livelli**,
interamente definito dall'utente:

```
Attrezzature            ← categoria
├── PC docente
└── Videoproiettore
```

con caselle a scelta multipla: un'aula può portare più tipologie. `Nuova
tipologia` permette di aggiungerne, e la voce di raggruppamento nella finestra di
scelta aula si chiama `Attrezzature (Tipologie)` — cioè **prende il nome dalla
categoria**, quindi più categorie darebbero più voci.

⚠ **Non è il "tipo d'aula"** (laboratorio / palestra / aula magna) che questo
documento ipotizzava. È un sistema di **etichette di dotazione**.

Sovrapposizione da notare: `Videoproiettore` esiste **sia** come tipologia **sia**
come `Materiale` (3 esemplari). Come tipologia è una dotazione fissa dell'aula;
come materiale è una risorsa prenotabile e assegnabile a un'attività. EDT offre
entrambi i modelli per lo stesso oggetto fisico, e lascia scegliere.

## 🔑 Cosa vincola davvero la scelta dell'aula

La finestra `Aule disponibili` (dal pannello di composizione dell'attività, riga
`Aule`) espone la lista dei **vincoli ignorabili** — e sono tre soli:

| Vincolo | Marcatore in colonna `Diagnostica` |
|---|---|
| `Sedi distaccate` | rosa |
| `Indisponibilità opzionali` | giallo |
| `Indisponibilità` | arancione |

La colonna **`Diagnostica`** dice, aula per aula, *perché* non va bene. Nella
schermata osservata la `S` rosa compare su tutte e 18 (l'attività è in `Succ. 2`,
le aule quasi tutte in `Principale`) e il quadratino arancione su 7 aule occupate
in quello slot.

Ci sono poi due filtri booleani — `Solamente le estratte`, `Solo le aule della
stessa sede dell'attività` — e un raggruppamento `Presenta per:` con le voci
`Tutto` · `Categoria` · `Sede` · `Attrezzature (Tipologie)`.

**Conclusione importante, in negativo:** capienza, categoria e tipologia **non
sono vincoli**. Non compaiono fra i vincoli ignorabili e servono solo a
raggruppare la lista per chi sceglie a mano. L'unico vincolo reale sull'aula è la
sua **disponibilità**, più la sede se attiva.

⚠ **E questa è la lista di ciò che vincola la scelta di *quale* aula — non di
quante ne servano.** La distinzione è stata letta male fino al 2026-08-29, ed è
costata otto rinunce su novantadue nel nostro Fermi
([ADR-021](../decisioni.md)). Il conteggio dei posti **non è in questa
finestra** perché non è una domanda dell'assegnazione: è una domanda del
**piazzamento**, e in EDT ha la sua causale nella diagnostica del piazzamento —
*«il gruppo di aule ha raggiunto il suo picco d'occupazione»*
([diagnostica.md](diagnostica.md)) — più il conto `Aule` fra le cinque risorse
del pannello dell'attività ([motore-risoluzione.md](motore-risoluzione.md)).
Cioè: **le aule si contano mentre si piazza, e si scelgono dopo.** I cinque
`TypeChoixOptimSalle` qui sotto sono tutti criteri di *scelta*; nessuno conta i
posti, perché quel conto è già stato fatto.

### 📦 I due enum dell'assegnazione: come sceglie, e cosa la rende incompatibile

⚠ Sono **valori estratti dai binari**. Le loro **etichette di interfaccia** sono
anch'esse estratte (§ *La finestra dell'ottimizzatore*, 2026-08-29) e ne fissano
la semantica; resta non osservato il solo comportamento a runtime. Ma dicono una cosa che vale: l'assegnazione delle aule è
un'**ottimizzazione separata** dal piazzamento, con criteri propri.

`TypeChoixOptimSalle` — i criteri con cui EDT sceglie *quale* aula fra quelle
ammissibili:

| Valore | Lettura |
|---|---|
| `tcosChangements` | limitare gli **spostamenti** fra attività consecutive — ⚠ *non* i cambi rispetto alla ripartizione precedente, vedi sotto |
| `tcosSallePref` | privilegiare l'**aula preferenziale** (della classe, vedi sotto) |
| `tcosCapacite` | ⚠ la **capienza** — che *non* è un vincolo, ma qui è un **criterio**: è la distinzione che spiega perché non compare fra i vincoli ignorabili |
| `tcosChangementsConfort` | lo stesso fra attività **non** consecutive: il tragitto scomodo ma non immediato |
| `tcosAucun` | nessun criterio |

`TypeIncompatibiliteSalle` — le undici ragioni per cui un'aula non è
assegnabile: `isElleMeme`, `isSite`, `isCapacite`, `isSalleDansGroupe`,
`isDejaDansLeGroupe`, `isNbOccurences`, `isGroupeDansGroupe`, `isGroupeDeGroupe`,
`isIndisponibilites`, `isOccupation`, `isGroupeDansConseil`. Le tre della
finestra `Aule disponibili` si riconoscono (`isSite`, `isIndisponibilites`,
`isOccupation`); le altre riguardano i **gruppi di aule** e il numero di
occorrenze — cioè la struttura, non la didattica.

Fonte: [estratti/catalogo-tipi-interni.md](estratti/catalogo-tipi-interni.md).

### 📦 La finestra dell'ottimizzatore, dalle sue etichette

Le etichette della finestra `FicheEdt_OptimiseurSalles` (📦, estratte il
2026-08-29) mappano **uno a uno** sull'enum, e ne fissano la semantica che il
catalogo lasciava aperta:

| Valore | Etichetta in UI |
|---|---|
| `tcosChangements` (chiave `CritereDeplacements`) | `Limita gli spostamenti tra attività consecutive` |
| `tcosSallePref` | `Favorisci l'utilizzo delle aule preferenziali` |
| `tcosCapacite` | `Minimizza il superamento della capienza` |
| `tcosChangementsConfort` (`CritereDeplacementsConfort`) | `Limita gli spostamenti tra attività non consecutive`\* |
| `tcosAucun` | `Nessuno` |

\* *«Questo criterio comporterà un'ottimizzazione più lunga, deve essere
utilizzato solo se necessario.»*

🔑 **`tcosChangements` non è «i cambi rispetto alla ripartizione precedente»**, che
è la lettura che avevamo dato: è lo **spostamento dell'utente fra due attività
consecutive** — quanto cammina una classe fra un'ora e la successiva. E
`tcosChangementsConfort` è la stessa cosa fra attività **non** consecutive, cioè
il tragitto che non è immediato ma resta scomodo. Le due nozioni di «cambio» sono
distanze fisiche, non differenze fra due ripartizioni.

⚠ Il che significa che il **secondo livello della nostra seconda fase — «i cambi
rispetto alla ripartizione precedente» — non è nessuno dei cinque criteri di
EDT.** È nostro, ed è la stabilità, l'analogo per le aule di L4 nella catena del
piazzamento. Non è un errore: è una voce in più, da dichiarare come tale.

Tre cose in più che la finestra dichiara, e che dicono la sua forma:

- `Criteri di ottimizzazione` sono **quattro caselle numerate** (`1.` `2.` `3.`
  `4.`), ciascuna con i cinque valori sopra: è una **catena lessicografica a
  quattro livelli**, la stessa forma della nostra;
- `Ottimizza per` **`Classi`** oppure **`Docenti`**, con `Classi prioritarie` /
  `Docenti prioritari` da spuntare — la **separazione per popolazione**, di
  nuovo, esattamente come nel piazzamento (`Arbitrato`);
- `Blocco delle aule nelle attività coinvolte`, con `Blocca` / `Sblocca`: *«Potete
  sbloccare alcune aule per consentire a EDT di esplorare altre combinazioni.»*

E l'ottimizzatore lavora **su un gruppo di aule alla volta**, non globalmente:
*«Solamente i gruppi di aule interamente assegnati possono essere ottimizzati»*,
e la ripartizione va lanciata prima (`Assegna le aule alle attività`).

📖 **Dove sta quel comando**, che nelle stringhe non si vedeva: non è una voce
di menu ma un **pulsante dentro una finestra**, e il percorso è
**`Orario → Aule → Gestione del gruppo di aule`** → si seleziona un gruppo
dall'elenco → `Assegna le aule alle attività`. Ne discende perché il menu
`Elabora`, trascritto per intero il 2026-07-26, non ha nessuna voce sulle aule:
l'assegnazione non passa da lì. `Gestione del gruppo di aule` era già fra le
stringhe (`Gestion du groupe de salles`) e non era stata collegata.

📖 La guida elenca anche **tre precondizioni**, che sono la conferma dell'ordine
delle fasi: le aule assegnate ai gruppi, i gruppi assegnati alle attività, e
*«gli orari chiusi con tutte le attività piazzate»*. Cioè la ripartizione delle
aule si lancia **su un orario finito** — la seconda fase, alla lettera.
→ [guida ufficiale, scheda 54-244](https://docs.index-education.com/docs_it/it-edt-supporto-scheda-54-244-assegnare-le-aule-alle-attivita.php)

### 👁 La finestra `Gestione del gruppo di aule`

Osservata il 2026-08-30 su `PALESTRE`. Titolo: *«PALESTRE - Gestione del gruppo
di aule (2 aule massimo)»*. È divisa in quattro riquadri, e i due in basso sono
**le nostre due fasi di assegnazione, separate**.

**In alto a sinistra, `Assegnate al gruppo: 2/2`** — le aule membre (`Palestra
1`, `Palestra 2`) con `Capienza` e `Occ.`. È la frazione «quante ne ha su quante
ne dovrebbe avere».

**In alto a destra, `Scelta delle aule`** — le candidate da aggiungere al gruppo,
con i pulsanti `<<` / `>>`, un `Solo le risorse estratte` e **tre caselle di
filtro con altrettanti pallini colorati**:

| | Etichetta |
|---|---|
| 🟢 | `Totalmente libere` |
| 🟠 | `Parzialmente libere` |
| 🔴 | `Non disponibili` |

Ogni riga porta il suo pallino nella colonna `Disp.`. Sulla demo sono verdi le
quattro aule libere da ogni gruppo (`Lab. Musica 1/2`, `Palestra succ 1/2`) e
rosse tutte le altre — fra cui, **in grassetto**, `LAB.MUSICA` e `PALESTRA
succ`, che sono gruppi a loro volta.

🔑 I tre pallini sono gli **undici `TypeIncompatibiliteSalle`** (📦) collassati in
tre secchi. Il grassetto sui gruppi rende visibili due di quei valori —
`isGroupeDansGroupe` e `isGroupeDeGroupe`: **un gruppo non entra in un gruppo**.

**In basso, `Assegnazione delle aule`:**

- ☐ **`Considera solo le attività estratte`** — 🔑 il perimetro dell'estrazione
  **dentro la ripartizione delle aule**, che è esattamente il nostro
  `assign_rooms --estrazione`;
- un radio **`Limita gli spostamenti dei docenti`** / **`Limita gli spostamenti
  delle classi`** (sulla demo: **classi**), più una barra di avanzamento a `0%`;
- il pulsante `Assegna le aule alle attività`.

🔑 **Due cose insieme, e sono entrambe nostre lacune dichiarate.** La prima: la
**separazione per popolazione** non vive solo nel piazzamento e
nell'ottimizzatore — c'è già nella *ripartizione*, ed è un radio a due valori
senza tolleranza. La seconda: `spostamenti` qui è di nuovo il **cammino fisico**
di docenti e classi, cioè `tcosChangements`, e conferma da un terzo posto la
correzione del 2026-08-29. La nostra seconda fase non ha **nessuno** dei due:
i suoi livelli sono `minuti senza aula` e la stabilità rispetto alla
ripartizione precedente. Non è un errore — è una voce in meno, da dichiarare.

**In basso, `Ottimizzazione dell'assegnazione`:** una sola frase — *«È necessario
assegnare tutte le aule prima di lanciare l'ottimizzazione»* — e il pulsante
`Ottimizza l'assegnazione delle aule`. Premuto prima della ripartizione risponde
`Ottimizzazione impossibile` / *«Solamente i gruppi di aule interamente assegnati
possono essere ottimizzati»*.

🔑 **Quindi le fasi di EDT sulle aule sono due, non una**, e stanno in due
riquadri distinti della stessa finestra: **ripartire** (assegnare un'aula a ogni
attività del gruppo) e poi **ottimizzare** (rimescolare le assegnazioni secondo i
quattro criteri). La nostra `solve_rooms` le fa **insieme**, in una catena a due
livelli. Da dichiarare come differenza di forma.

⚠ **E la ripartizione distrugge le modifiche per settimana.** La conferma prima
di lanciarla dice, testualmente:

> *«Certe modifiche dell'orario per settimana saranno cancellate.
> Confermate l'assegnazione di tutte le attività del gruppo di aule PALESTRE?»*

È un'operazione **massiva** (tutte le attività del gruppo, non le selezionate) e
**distruttiva** su ciò che [ADR-014](../decisioni.md) modella come righe con
maschera a una settimana — sostituzioni e aggiustamenti. Il nostro `apply_rooms`
scrive `assigned_room` senza toccare nient'altro: **non** ha questo effetto, ed
è la scelta migliore, ma va saputo che EDT qui è più brutale di noi.

La nostra seconda fase (`domain/solver/rooms.py`) ha **due** livelli — minuti
senza aula, poi i cambi rispetto alla ripartizione precedente — e non implementa
nessuno dei cinque criteri di EDT.

### 👁 La finestra dell'ottimizzatore, aperta — e i quattro default

Osservata il 2026-08-30, dopo aver lanciato la ripartizione su `PALESTRE`.
Titolo: *«Ottimizzazione della ripartizione delle aule di PALESTRE»* — quindi
**si ottimizza la ripartizione**, non si assegna: sono due verbi diversi, come
sono due riquadri diversi.

🔑 **I quattro criteri, coi valori che il produttore ci trova dentro:**

| | Default osservato | Enum |
|---|---|---|
| **1.** | `Limita gli spostamenti tra attività consecutive` | `tcosChangements` |
| **2.** | `Favorisci l'utilizzo delle aule preferenziali` | `tcosSallePref` |
| **3.** | `Minimizza il superamento della capienza` | `tcosCapacite` |
| **4.** | `Nessuno` | `tcosAucun` |

Il quinto valore — `Limita gli spostamenti tra attività **non** consecutive`
(`tcosChangementsConfort`) — **non è fra i default**, coerentemente con la nota
a piè di finestra: *«Questo criterio comporterà un'ottimizzazione più lunga, deve
essere utilizzato solo se necessario.»*

🔑 **Il criterio dominante non è «quale aula è più adatta»: è «quanto camminano
le persone».** Il cammino sta al primo posto, l'aula preferenziale al secondo, la
capienza al terzo. Chiude O1 e conferma per la quarta volta la correzione del
2026-08-29 su `tcosChangements`.

⚠ **E la capienza torna, ma come criterio.** `Minimizza il superamento della
capienza` dice due cose insieme: che la capienza in alunni **si può superare**
(quindi non è un vincolo — § *Cosa vincola davvero la scelta dell'aula* resta
vero) e che EDT **preferisce non farlo**. Non è quindi inerte come sembrava: è
un criterio soft, il terzo. Il campo `Cap.` esiste nel nostro schema
(`Room.capacity`, dichiarato descrittivo) e non è letto da nessuno. Voce in
meno, dichiarata.

**Il resto della finestra:**

- **`Ottimizza per`** è una **tendina** `Classi` / `Docenti` (nella finestra di
  ripartizione la stessa scelta è un *radio*: due UI per la stessa cosa). Sotto,
  `Classi prioritarie` oppure `Docenti prioritari` — sulla demo **22 classi** e
  **4 docenti**, con contatore `0 / 22` e `0 / 4`, cioè nessuna selezione.
  La frase è esplicita: *«La ripartizione delle aule è ottimizzata per tutte le
  classi relative al gruppo di aule. Selezionate le classi da ottimizzare
  prioritariamente»*.

  🔑 **La priorità è una selezione, non un peso.** Il nostro `Arbitrato` dichiara
  invece una **tolleranza numerica** di peggioramento sulla popolazione
  sacrificata. Due meccanismi diversi per lo stesso scopo, e il nostro è più
  fine — ma il loro dice qualcosa che il nostro non sa dire: *queste* classi
  prima delle altre.
- **`Blocco delle aule nelle attività coinvolte`**: la tabella delle assegnazioni
  che l'ottimizzatore rimescolerebbe — `Classe | Aula | 🔒 | Materia | Docente |
  Collocazione`, e le prime due colonne si **scambiano** quando si ottimizza per
  docenti. Sulla demo **43 righe**, contatore `0 / 43`. Il lucchetto blocca la
  singola assegnazione: *«Potete sbloccare alcune aule per consentire a EDT di
  esplorare altre combinazioni.»* È il nostro `Activity.immobility` applicato
  all'**aula** invece che alla collocazione, e non ce l'abbiamo.

**E la ripartizione, misurata.** Prima: `Palestra 1` e `Palestra 2` entrambe a
`0h00`. Dopo `Assegna le aule alle attività`: **29h00** e **19h00**, somma 48h00
= l'`Occ.` del gruppo. Cioè la ripartizione da sola **non bilancia** — 43
attività distribuite 29/19 — ed è precisamente il lavoro che l'ottimizzatore
farebbe dopo. La separazione fra le due fasi non è formale: la prima trova *una*
assegnazione, la seconda la rende buona.

### Ma la classe ha un'aula preferenziale

La vista Classi ha una colonna **`Aula preferenziale`**. Quindi il legame
aula↔didattica esiste, solo che passa dalla **classe**, non dalla materia — che è
poi come funziona una scuola reale: la classe ha la sua aula e si sposta solo per
laboratorio e palestra. Vedi [classi.md](classi.md).

Non esiste invece nulla di simile a *"questa materia richiede un laboratorio"*: se
lo vogliamo, è **nostra estensione**, da marcare come tale.

## Altri campi dell'aula

- `Prenotabile da` + `Soglia di prenotazione` (*"numero di giorni prima dei quali
  può essere fatta una prenotazione"*) — 📦, l'aula ha un **regime di
  prenotazione**.
- `Gestori` — *"personale o docente designato come responsabile dell'aula"*
  (osservato: valorizzato su tutte le 18 aule della base).
- `Sede di appartenenza` (= `Site` dello schema).
- `Categoria dei locali scolastici` (= tipo interno `TNetCategorieSalle`).
- `Tasso di occupazione`, `Numero di posti occupati` / `disponibili` — calcolati.

## Cosa dice lo schema di scambio 📦

Lo schema ufficiale ([schema-scambio.md](schema-scambio.md)) modella l'aula in
modo più povero di quanto ipotizzato qui:

```
Salle
├── @Nom
├── @Capacite     (opzionale)
└── Site  (0..1)
```

Nessun campo "tipo", **nessun vincolo di occupazione**. L'occupazione simultanea
esiste invece su un'altra entità:

```
Materiel
├── @Nom
├── @Informations
└── @NbOccurences    numero di esemplari disponibili
```

Nel formato di scambio l'aula è quindi implicitamente a occupazione 1.

⚠ **Lo schema qui inganna.** Il campo `Numero di aule` esiste nel prodotto ma non
viaggia nello scambio: chi importasse da `Partenaire_Index` perderebbe la
capienza simultanea di ogni aula. È un argomento concreto contro l'adozione dello
schema come contratto unico.

Sulle stringhe della localizzazione una nota metodologica: parlano di `Gruppo di
aule` e di `Nr` — *"Numero di aule (=1 per un'aula; > 1 per un gruppo)"* — e
questa formulazione mi aveva portato a concludere che l'occupazione simultanea
**fosse** il gruppo. La UI dice altro: `Qtà > 1` non implica alcun membro. Le
stringhe descrivono il caso tipico, non il modello. È esattamente il motivo per
cui [ADR-009](../decisioni.md) mette le stringhe estratte dai binari all'ultimo
posto della gerarchia di autorevolezza.

**Nota per il solver.** Non esiste un tipo `TNetContraintesSalle` fra le entità
persistenti 📦: le indisponibilità dell'aula non sono una tabella di vincoli
dedicata come per il docente. Stanno nella tabella generica delle **assenze
risorsa**, insieme a quelle di docenti e classi — vedi [vincoli.md](vincoli.md).

## ⚠ Limite: la tabella delle aule è cifrata

Nel file `.edt` la tabella `SALLE` è **cifrata**, insieme a sei tabelle di dati
personali (docenti, alunni, responsabili, personale, contatti, credenziali). Le
sei hanno una ragione ovvia; l'aula no, e non c'è una spiegazione. Vedi
[formato-file.md](formato-file.md).

**Conseguenza:** nomi, capienza, sito e categoria delle 18 aule della base di
esempio **non sono leggibili nel file**.

🔑 **Il limite è stato aggirato aprendo la base in EDT.** La cifratura protegge i
dati a riposo, non la vista: l'elenco delle 18 aule è perfettamente leggibile in
UI (`AULA SOSTEGNO`, `LAB.ARTISTICA`, `LAB.INFORMATICO`, `PALESTRE`, `SALA
MENSA`, …), con sede, quantità, gestore e categoria. Per questo documento il
limite non morde più; resta valido per chiunque volesse leggere le aule
programmaticamente dal `.edt`.

Si recupera comunque, in chiaro dalla stessa base:

- **`CATEGORIESALLE`** con due categorie reali: `AULA DI INSEGNAMENTO GENERALE` e
  `CDI` (biblioteca). La categorizzazione esiste e si popola.
- **`SITE`**: 3 siti, con colore.
- **`RELATIONSALLES`**: la relazione fra aule, cioè i gruppi.
- **`MATERIEL`**: `Videoproiettore ×3`, `PC portatile ×5`, `Tablet ×50`.

Quest'ultima chiarisce un punto: l'**attrezzatura prenotabile è una risorsa
distinta dall'aula**, non un modo alternativo di modellare l'aula. Il
`Materiel/@NbOccurences` dello schema serve a "ho 3 videoproiettori", non a "la
palestra regge 2 classi".

### Le aule ammettono davvero corsi simultanei — verificato

Espandendo la collocazione dei 984 corsi piazzati della base di esempio, le 9
aule effettivamente usate mostrano **34 collisioni su 97 slot**: più corsi nella
stessa aula nello stesso momento, in una base che EDT considera risolta senza
errori.

Non è un difetto della base: è la conferma che **l'occupazione simultanea è un
attributo reale dell'aula**, che EDT rispetta. E ora sappiamo qual è il campo:
`Numero di aule`, colonna `Qtà`.

⚠ Confronto utile: sui docenti le collisioni sono 7 su 1333, sulle classi 1 su
1320 — cioè quasi zero, come atteso. Le aule sono l'unica risorsa dove la
sovrapposizione è sistematica.

## Semantica

- La **capienza** (`Cap.`) è il tetto di alunni dello spazio. In EDT è
  **descrittiva**: non compare fra i vincoli di assegnazione, e nella base di
  esempio non è nemmeno compilata. Se noi volessimo confrontarla col massimo di
  alunni del corso ([`Al./Rid.`](materie.md)), sarebbe **nostra estensione**.
- Il **vincolo di occupazione** (`Numero di aule`) è distinto dalla capienza ed è
  quello vero: la palestra regge 2 attività in parallelo, i laboratori 1. È il
  vincolo di risorsa condivisa per il solver.
- L'idea che *"FIS/SCI vanno in laboratorio, MOT in palestra"* sia un legame
  **materia → tipo d'aula** non trova riscontro in EDT: il legame passa dalla
  classe (`Aula preferenziale`) o è deciso a mano sull'attività. Resta un'ipotesi
  di nostra progettazione, non un campo osservato.

## Risorsa contesa (nota per il solver)

La palestra regge 2 classi, ma il docente di MOT (D17) è **uno solo**: di fatto la
palestra è mono-classe finché c'è un solo docente. Idem per l'aula disegno con D16.
La capienza dell'aula non è il collo di bottiglia: lo è il docente. Vedi
[`data/liceo-fermi/vincoli-attesi.md`](../../data/liceo-fermi/vincoli-attesi.md).

## Implicazioni per il nostro modello

- L'aula ha `nome`, `sede`, `capienza` (descrittiva) e un intero
  **`simultaneous_capacity`** — l'unico attributo che il solver deve rispettare.
  Default 1.
- 🔑 **E lo rispettano entrambe le fasi, per due domande diverse.** La fase 1
  conta i posti di un **insieme** di aule candidate (`structural:room_pool`,
  [ADR-021](../decisioni.md)): non «quale aula», ma «quante ne servono qui», che
  è un vincolo di Hall e non un totale — sul Fermi, su nessuna delle 26 celle
  contese l'unione delle candidate era in deficit, e le rinunce c'erano lo
  stesso. La fase 2 sceglie *quale*, ed è lì che valgono i tre vincoli della
  finestra `Aule disponibili`.
- La **gerarchia padre/figlio** fra aule è un extra rimandabile: serve a nominare
  gli spazi, non a esprimere la capienza. Se la implementiamo, va con la
  **cascata di default** sui campi ereditabili (gestore, sede).
- Le **tipologie** sono tag a due livelli (categoria → tipologia), molti-a-molti
  con l'aula, definiti dall'utente. Puramente descrittivi in EDT.
- L'**aula preferenziale sta sulla classe**, non sulla materia.
- Una eventuale relazione **materia → dotazione richiesta** sarebbe **nostra
  estensione** oltre EDT. Da valutare, e comunque da marcare come tale
  ([convenzione "non inventare campi"](../../CLAUDE.md)).

## Dataset di esempio

Le aule del Liceo Fermi:
[`data/liceo-fermi/aule.md`](../../data/liceo-fermi/aule.md).
