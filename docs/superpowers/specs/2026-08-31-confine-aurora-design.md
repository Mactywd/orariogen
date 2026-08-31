# Il confine con Aurora

**Data**: 2026-08-31
**Stato**: 📐 **design** — nessun codice, due decisioni da prendere
**Chiude**: D2 (la via d'ingresso dei dati) e D4 (serve un'interfaccia?), che
dal 2026-08-28 il todo dichiarava *«la stessa domanda: il confine con Aurora»*
**Fonte**: `Mactywd/aurora` a `ff0a750` (2026-08-31), letta da questa sessione

## 0. Perché questo documento esiste

Il generatore è consolidato: niente blocca il calcolo, la sezione `Lavoro` del
todo è vuota, 972 test verdi. Restano due decisioni, e sono di prodotto: dove
finisce il generatore e dove comincia il gestionale dentro cui vivrà.

Il todo le formulava così — *«formato nostro, CSV, o aggancio al SaaS»* per D2,
*«quali comandi diventano API e quale stato vive dove»* per D4. Sono le domande
giuste, ma **poste prima di aver guardato Aurora**. Guardandola cambiano, e
questo documento è il racconto di come.

## 1. Le cinque misure

Tutto ciò che segue poggia su queste, e nessuna è una stima.

### 1.1 Le due tenancy sono incompatibili per costruzione

**orariogen è a scuola singola.** Non per scelta dichiarata: per forma dello
schema. `InstituteSettings` è un singleton (`id = 1`), e sono **globalmente
uniche** `Site.name`, `Subject.code`, `Discipline.code`,
`CompetitionClass.code`, `StudyPlan.code`, `Group.name`, `Extraction.name`.
Nessuna delle 33 tabelle porta una chiave di scuola.

**Aurora è multi-tenant, e lo è con disciplina.** Ogni modello ha una FK
`school`; la risoluzione passa da **un chokepoint solo**
(`tenancy.get_request_school`) e un test verifica che nessun altro file legga
`user.school_profile` da sé; e ogni FK/M2M scrivibile che punta a un modello di
tenant va dichiarata in `school_scoped_fields`, o un payload può indicare le
righe di un'altra scuola.

Non è un dettaglio d'integrazione: è la prima cosa da decidere, e decide le
altre.

### 1.2 Il dominio interroga l'ORM in 77 punti

Fuori da `domain/models/`: **77** siti di query, di cui **21 nei comandi**
(che diventerebbero rotte comunque) e **36 in tre file** — `analysis/state.py`
(16), `extraction.py` (10), `analysis/capacity.py` (10). Il resto è sparso a
uno o due per file.

Il trapianto è quindi **meccanico ma non gratuito**: non c'è un chokepoint da
cui passa tutto, che è invece esattamente la disciplina di Aurora.

> ⚠ **Sciolto la sera stessa da [ADR-031](../../decisioni.md), e due cose qui
> sopra sono da leggere con quello accanto.** I 77 erano **116** poche ore
> dopo — L12 e L13 — cresciuti di metà senza che niente lo dicesse: il numero
> non è uno stato, è una fotografia. E *«non c'è un chokepoint»* nasconde il
> motivo: non ce n'è uno perché **non c'è ancora niente da fargli portare** —
> lo `Schedule`, che dodici porte d'ingresso su diciotto già portano, delimita i
> piazzamenti e non l'anagrafica. Il chokepoint arriva con la `School` di §1.1;
> nel frattempo il confine è **dichiarato e sorvegliato**
> (`tests/test_confine_orm.py`), e il nucleo del calcolo — 28 builder su 28,
> 13 file di checker su 14 — non interrogava già allora.

### 1.3 Appiattire perde tre chiavi su 142 — e non a caso

`ScheduleEntry` di Aurora è `(school, teacher, weekday, period_number,
school_class, subject)`: una griglia settimanale piatta, cinque giorni scritti
nel codice, senza aule, senza parti di classe, senza maschere di settimana,
senza identità di attività.

Appiattendo l'Alighieri su quella chiave e confrontando con le cattedre:

| | |
|---|---|
| chiavi `(docente, classe, materia)` | **142** |
| tornano identiche | **139** |
| non tornano | **3** |

E le tre non sono rumore: sono **esattamente le due strutture che una griglia
piatta non tiene**.

- **due** sono il *raggruppamento trasversale*. `ING1-AVANZ` unisce parti di 1A
  e 1B; appiattito dice «Orlandi insegna a 1A», dove nessuna cattedra lo
  dichiara. È la conseguenza che ADR-013 aveva già scritto — *si perde la
  decomposizione per classe* — qui in forma numerica.
- **una** è l'*ora quindicinale* del 5B: due ore diventano **tre**, perché
  un'ora a settimane alterne occupa una cella settimanale come una piena.

🔑 **E delle due, una sola è un errore di sostituzione.** Il gruppo trasversale
fa dire ad Aurora una cosa **vera e incompleta** (Orlandi insegna a metà di 1A,
Aurora crede a tutta): il supplente serve comunque, ed è la stessa
approssimazione con cui Aurora già convive dandosi classi dal nome composto
(`3B/5O`). L'ora quindicinale fa dire una cosa **falsa una settimana su due**:
in quella sbagliata il motore cerca un supplente per un'ora che non si tiene.

### 1.4 Risalire dalla griglia inventa, e inventa in una direzione sola

L'altra metà della stessa misura, e la più utile per D2. Dalla griglia piatta:

| si ricava | esito |
|---|---|
| le **cattedre** | **139 chiavi su 142** identiche |
| i **quadri orari** | **6 classi su 12** |

I sei scarti sono sistematici, non sparsi:

- **1A e 1B, inglese: 6 ore ricavate contro 3 dovute.** Due gruppi fanno la
  stessa ora insieme, la griglia le conta tutte e due. È lo **sdoppiamento**,
  ed è il caso di gran lunga più comune in una scuola italiana.
- **3A, 4A, 5B: un'ora di troppo** — l'articolata e l'ora quindicinale.
- **2C: tre ore di una materia che nel suo piano non c'è.**

E i **profili distinti sono 9 contro 11 piani dichiarati**: raggruppare le
classi per quadro orario non ricostruisce i piani, ne **fonde due coppie**.

🔑 **Appiattire e ricavare non sono l'inverso l'uno dell'altro.** Scendere
perde; risalire *inventa*, e sempre **per eccesso**: gonfia il monte ore di
ogni classe sdoppiata. Un import che risalisse in silenzio darebbe alla scuola
un piano che **nessun orario può soddisfare**, e il generatore risponderebbe
`INFEASIBLE` senza che nessuno sappia perché.

### 1.5 Aurora ha l'11% dell'ingresso — ma è il numero meno interessante

L'Alighieri, 12 classi: **970 righe su 33 tabelle**. Tolte le 343 `Activity`
(generate dalla ripartizione, non inserite) e le 91 `Resource` (la base
dell'ereditarietà multi-tabella, non un dato a sé), restano **536 righe di
dato inserito**. Aurora ne ha già ~59 — 23 docenti, 12 classi, 16 materie, 8
fasce — cioè l'**11%**, e sono la parte a buon mercato: i nomi.

Il grosso è quello che nessuno ha mai digitato: **128 righe di quadro orario,
140 di cattedra, 55 di indisponibilità, 51 di suddivisione**.

> ✅ **Corretto il 2026-08-31 da L10 / [ADR-030](../../decisioni.md):** le
> cattedre sono **144**, non 140, perché una cattedra nomina ora l'**unità che
> serve** — 112 su classe, 30 su parte, 2 su raggruppamento. Il conteggio non
> cambia la conclusione di questo paragrafo, ma cambia la sua ragione: quelle
> quattro righe in più sono precisamente il dato che una griglia settimanale
> **non può contenere**, e quindi la parte dell'ingresso che nemmeno il
> gradino 1 recupera. La misura sul giro completo lo dice per numeri: `ricava`
> ritrova 141 chiavi di cattedra su 142, e l'unica storta è l'ora quindicinale
> — cioè una cecità già dichiarata, non un errore. Prima erano 139, e le due
> mancanti erano il raggruppamento trasversale: `ricava`, che legge l'orario
> vero, aveva **ragione**; era la dichiarazione a sbagliare.

## 2. Il precedente dentro Aurora, e le due collisioni

Aurora ha già un modulo che genera con CP-SAT: **Classi Prime**. Forma le
classi prime, pubblica una generazione, la congela come riferimento, e a una
rigenerazione dice **esattamente chi si muove**. È, alla lettera, il criterio
di stabilità che ADR-010 ci obbliga ad avere.

Va quindi letto come il modello da seguire — e **due sue regole non
sopravvivono al generatore**, misure alla mano.

**Collisione 1 — un solve per richiesta.** Classi Prime non ha coda: il caso
peggiore è `MAX_TIME_LIMIT + EXPLAIN_TIME_LIMIT` e **deve stare dentro il
`--timeout` di gunicorn**, con un test che legge `entrypoint.sh` per tenerlo
vero. Il generatore non ci sta: l'Alighieri è **9 s senza i criteri di qualità
e 82 s con**; `solve --popolazione` sul Fermi è **49 s**, e prima della
correzione del budget veniva ucciso a **dodici minuti**. E non è una costante
da alzare: la catena lessicografica è un `Solve` **per livello**, quindi il
tempo cresce con quanti criteri la scuola dichiara — cioè con un dato, non con
una costante.

**Collisione 2 — un lavoratore e un seme fisso.** Classi Prime fissa
`num_search_workers = 1`, e la ragione è ottima: *«una commissione che rilancia
e vede classi diverse smette di fidarsi»*. Sul generatore quella regola costa
un **fattore 60**: i tetti di peso didattico dell'Alighieri misurano **439 s
con un lavoratore contro 7 s con otto**. La riproducibilità va comprata
altrove — congelando la **soluzione pubblicata**, non la ricerca. Ed è ciò che
Aurora già fa: `IntakeGeneration.assignment` non si riscrive mai.

## 3. D4 — la decisione sul confine

**Il generatore è un modulo di Aurora; i suoi dati d'ingresso sono dati di
Aurora; il calcolo è un lavoro e non una richiesta; e l'uscita è la griglia
che Aurora già legge.** Quattro parti.

### 3.1 La tenancy: le 33 tabelle prendono la scuola

Le sette unicità globali diventano per scuola e `InstituteSettings` diventa una
riga per scuola. L'alternativa — tenere il generatore a scuola singola e fare
multi-tenancy per **istanze**, un database per cliente — è stata considerata e
scartata: vorrebbe dire una migrazione per cliente e un secondo modello di
tenancy in un prodotto che ne ha uno solo, con un chokepoint e un test che lo
difende.

⚠ **La parte che si dimentica** è l'invariante di Aurora, non la FK: ogni
FK/M2M scrivibile verso un modello di tenant va in `school_scoped_fields`. Su
`Activity` sole sono **sette M2M**.

### 3.2 L'uscita è `ScheduleEntry`, e la perdita si nomina

Il generatore **pubblica nella griglia piatta** che il motore delle
sostituzioni già legge. Non un secondo orario accanto: sarebbero due risposte
alla domanda per cui il prodotto esiste.

Ma §1.3 dice che pubblicando si perde, quindi la crescita minima di Aurora è
**un campo di validità sulla `ScheduleEntry`** — non un modello nuovo. È la
maschera di ADR-014 che attraversa il confine, e serve al caso che è **falso**
(l'ora quindicinale), non a quello che è vero e incompleto (il gruppo).

🔑 **E qui i due prodotti si scoprono uguali.** La sostituzione che Aurora
genera ogni mattina e la sostituzione di ADR-014 sono la **stessa cosa**: una
riga con la maschera di una settimana che oscura l'originale. Aurora la
produce, orariogen la modella, e oggi non si parlano. Il campo di validità è il
punto in cui cominciano.

### 3.3 Lo stato: tre livelli, e il criterio è chi lo scrive

| livello | cosa | dove | perché |
|---|---|---|---|
| **ingresso** | piani, cattedre, aule, vincoli, suddivisioni | tabelle di Aurora, School-scoped | lo **scrive la scuola**, e ciò che la scuola scrive è di Aurora |
| **calcolo** | `Activity`, `Placement`, `Schedule`, `Extraction`, `RelaxationQuota` | tabelle del modulo | è lo stato di un lavoro |
| **uscita** | `ScheduleEntry` | Aurora | è il record permanente |

Sul livello di mezzo vale l'invariante di `IntakeGeneration`, identica: **la
generazione non si riscrive**, gli spostamenti a mano sono append-only e si
applicano in lettura. È ciò che distingue quel che ha deciso il modello da quel
che ha deciso una persona — e in un orario quella distinzione è la cosa che una
segreteria chiede per prima.

Il passaggio al terzo livello è una **pubblicazione esplicita**, fotografata
con `ScheduleSnapshot` come già fa l'import.

### 3.4 Quali comandi diventano API — non sei rotte per sei comandi

- **`solve`, `assign_rooms`, `place_and_fix` → lavori.** Coda, stato, polling.
  È la prima differenza vera rispetto a Classi Prime, ed è misurata (§2).
- **`analyze` → una lettura, sincrona.** Non ha un solver dentro: il violatore
  di Hall è flusso massimo e taglio minimo, la classifica dei vincoli è dominio
  residuo. È la rotta che rende utile il modulo **prima** che il calcolo parta,
  ed è la lacuna di EDT che `scope-v1.md` dichiarava.
- **`extract` → non è una rotta.** È un criterio di selezione, cioè un
  **parametro** degli altri tre. `Extraction` resta una riga; nessuno «esegue
  un'estrazione».
- **`export_ical` → una rotta, e la sola già finita**: consegna, non calcola.
  ⚠ Ha un prerequisito che Aurora non soddisfa: le `SlotLabel`. Aurora ha i
  `TimeSlot` con `start_time`/`end_time` — è lo **stesso dato**, e va mappato,
  non reinventato.

## 4. D2 — la decisione sulla via d'ingresso

**L'orario dell'anno scorso è la via d'ingresso; il dialogo chiede il terzo che
non c'è dentro.** Tre gradini, e il secondo è il punto.

1. **Si ricava ciò che l'orario dice.** Docenti, classi, materie, fasce, e le
   **cattedre** — 139 su 142 (§1.4). Aurora ha già il motore che legge i file
   d'orario delle scuole, con descrittori, giudice e verdetto.
2. **Si dichiara ciò che l'orario non distingue: dove una classe si sdoppia.**
   È la domanda sola che sblocca i quadri orari, ed è piccola — 17 partizioni
   sull'Alighieri. ⚠ E **in parte è già scritta nei nomi**: Aurora esporta e
   rilegge celle come `3B/5O - Fisica`, e il `celltemplate` le taglia già. Un
   nome composto **è** una suddivisione dichiarata, e la scuola che la scrive
   non deve dirla due volte.
3. **Si chiede il resto**, che è nominabile e finito: aule (20),
   indisponibilità (55), vincoli di materia e orari (23), discipline e classi
   di concorso (22). **~170 righe su 536, un terzo.**

✅ **Il gradino 1 è implementato lo stesso giorno** (`domain/bootstrap.py`,
`manage.py bootstrap`), e implementandolo il **gradino 2 si è ridotto**: lo
sdoppiamento non è una domanda da fare ma un **sospetto da nominare**, perché
la griglia l'evidenza ce l'ha — la stessa classe due volte nella stessa fascia.
Contare le **celle** invece delle lezioni porta i quadri esatti da 6 a **8 su
12**, e il rilevatore è **sicuro ma non completo**: zero falsi allarmi su due
dataset, 28 coppie su 30. Le due mancate sono il *turno di laboratorio*, che
per costruzione non collide — stesso docente, mai simultanee. Resta da chiedere
**chi** sta in quale metà, che è anagrafica di alunni e non sta in nessun
orario.

✅ **Anche il gradino 3 è implementato lo stesso giorno**
(`domain/questionario.py`, `manage.py questionario`), e implementandolo l'elenco
di §4.3 si è corretto in tre punti.

**Il primo: una delle quattro voci non tocca il calcolo.** Discipline e classi
di concorso stavano nell'elenco accanto ad aule e indisponibilità. L'ablazione
sull'Alighieri — si tolgono le righe della famiglia e si ripassa la sonda —
dice **zero builder, zero celle, zero constraint**: il solve è identico riga
per riga. La domanda si fa lo stesso, ma per il gestionale (ADR-001, ADR-002:
le sostituzioni ragionano per classe di concorso), non per l'orario. È l'unica
del catalogo così, e senza la misura sarebbe rimasta indistinguibile dalle
altre.

**Il secondo: l'elenco non era ordinabile per gravità.** I tre effetti che il
modulo dichiara — `MUTO` (senza risposta il calcolo sbaglia e nessuno lo dice),
`ASSENTE` (un pezzo non si fa, e si vede), `FUORI_CALCOLO` — suggerirebbero di
chiedere prima le mute. Ma `indisponibilita` è muta e `aule` è solo assente, e
le aule vengono comunque prima: *quando* un'aula è occupata non si sa nemmeno
formulare finché non si sa *quali* aule ci sono. 🔑 **La possibilità viene
prima della gravità**, e la gravità ordina ciò che è ugualmente possibile.

**Il terzo, ed è quello che ha aggiunto una tabella.** Un questionario che
chiama «aperta» una famiglia vuota **non può terminare**: una scuola che
davvero non ha vincoli di materia ha le stesse zero righe di una a cui nessuno
li ha chiesti. Da qui `SetupQuestion`: una domanda si chiude perché qualcuno la
chiude, e la tabella porta *che* è stata posta, non la risposta — che sta nelle
tabelle vere. **Il silenzio non è una risposta**, ed è la stessa obiezione con
cui §4.1 scarta un secondo lettore di file: due verità sullo stesso dato.

⚠ **La sonda ha un punto cieco, e le due voci che ci cadono lo dichiarano.**
Misura `build_model`, cioè il modello **duro**; le quote di alleggerimento e i
criteri di qualità sono livelli della catena lessicografica, costruiti uno alla
volta sopra di esso. L'ablazione li misura a zero, e zero lì non vuol dire
inerte.

⚠ **E togliere le indisponibilità fa *crescere* il modello** — 13 645 → 13 861
constraint. Una cella potata non genera letterali, quindi nemmeno i constraint
che li nominerebbero: **potare costa meno che vincolare**. Il criterio
dell'ablazione conta quindi i builder che *calano*, non quelli che *cambiano*.

🔑 **La misura che dice quanto è grande il gradino 3 viene dal Fermi**, che è
l'unico dataset osservato invece che costruito: delle dodici famiglie del
catalogo ne porta **quattro** (aule, indisponibilità, discipline, calendario),
e delle sei mute ne lascia **quattro** senza una riga. L'Alighieri, che è
costruito apposta, ne porta undici su dodici. È la stessa forma della misura
che aprì L4 — tre builder su ventotto — vista dalla parte di chi deve chiedere
invece che da quella di chi calcola.

### 4.1 Alternative scartate

- **Un formato nostro, o CSV** — la formulazione originale di D2. Non è
  sbagliata: è **già fatta, e da qualcun altro**. Scriverne un secondo per gli
  stessi file sarebbe una seconda verità sullo stesso dato, e Aurora ha
  costruito attorno al primo una proprietà che non si butta: ogni scuola che
  importa un formato nuovo **lascia dietro di sé un test**.
- **Il dialogo come via principale** — la formulazione aggiornata, del
  2026-08-28. Scartata perché **chiede ciò che si sa già**: due terzi
  dell'ingresso sta nell'orario che la scuola ha già mandato. Il dialogo resta,
  e resta necessario, ma sul terzo che manca — dove è l'**unica** via, perché
  indisponibilità e aule non stanno in nessun file d'orario.
- **`Partenaire_Index`** resta escluso (ADR-012), ora con un motivo in più:
  importerebbe da EDT una scuola che in Aurora c'è già.

### 4.2 Il rischio, dichiarato

La derivazione dalla griglia è una **proposta da verificare, mai un dato
salvato in silenzio**. È la disciplina del giudice dell'import — `analyze`
propone, l'utente vede, `import` scrive — e va estesa qui, perché **qui
l'errore è peggio**: un descrittore sbagliato produce un orario visibilmente
storto, un quadro orario gonfiato produce un `INFEASIBLE` muto.

## 5. Cosa questo documento non decide

- **Il calendario.** Non dice quando, e non dice in che ordine rispetto al
  resto del roadmap di Aurora.
- **Il prezzo.** Il generatore sarà un `module_` come `module_classi_prime`, ma
  la politica commerciale è la stessa che quel modulo dichiara **non scritta**.
- **La UI.** D4 chiedeva *«serve un'interfaccia?»* e la direzione era già
  dichiarata il 2026-08-28 — griglie come quelle di EDT, semplificate, più una
  bolla AI. Questo documento non la disegna: decide dove passa il confine, che
  è ciò che al disegno serve sapere prima.
- **La purezza del dominio.** Classi Prime tiene `api/intake/` senza Django,
  con un test specchio sul confine. Sarebbe la cosa giusta anche qui, ma §1.2
  la misura: **77 siti di query**. È un pezzo a sé, e va deciso col suo costo
  davanti, non come corollario di questo.
  → **Deciso la sera stessa, [ADR-031](../../decisioni.md): no.** Il pacchetto
  comprerebbe una purezza già in cassa, e il conto dei siti misurava la cosa
  sbagliata.
