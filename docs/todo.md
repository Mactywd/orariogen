# Cose da fare

**Questo è l'unico elenco.** Ogni volta che una voce si apre o si chiude, si
aggiorna qui — non si aprono liste parallele in `CLAUDE.md` o in `scope-v1.md`,
che rimandano a questo file. Il *racconto* di come una voce è stata chiusa
resta in [changelog.md](changelog.md); qui resta una riga con la data.

**Come si legge una voce.** Ogni riga porta il tipo di risposta che aspetta,
perché è ciò che decide chi può muoverla:

| | Tipo | Chi la sblocca |
|---|---|---|
| 🧭 | **decisione** | una persona: cambia il prodotto o i dati che una scuola deve inserire |
| 👁 | **osservazione** | EDT: si guarda la UI e si scrive cosa fa |
| 🔧 | **lavoro** | nessuno: si può fare adesso |
| ⚖ | **debito dichiarato** | nessuno, ma è già stato deciso di non pagarlo: si riapre solo con un motivo nuovo |

Stato: `[ ]` aperta · `[~]` in corso · `[x]` chiusa (scende in fondo, con la data).

> **Stato al 2026-08-30.** Nessuna voce ✅ di [scope-v1.md](scope-v1.md) è
> rimasta senza implementazione: il motore, l'analisi, le due fasi, `Estrai`,
> `Piazza e sistema` e l'export iCal ci sono tutti. E **D1 è sciolta**
> ([ADR-020](decisioni.md)): la copertura misura l'atomo e l'alternativa è un
> dato dichiarato, quindi **l'import non è più bloccato**.
>
> **Niente blocca il calcolo.** Restano **tre decisioni** di prodotto
> (D2, D4, e O5 che è una decisione travestita), **una sola osservazione
> sostanziale** in EDT — l'ultimo residuo di O2, il `Ciclo personalizzato` —
> più le due minuzie da tooltip di **O7**, **due esperimenti** che nessun dato
> esistente può sostituire (O3, O6), e **nove debiti** già decisi. O1 è chiusa
> il 2026-08-30.
>
> 🔧 **La sezione 3, `Lavoro`, ha aperto e chiuso tre voci lo stesso giorno**
> — L1 (il perimetro del buco), L2 (la capienza come criterio e il lucchetto
> sull'aula) e L3 (il materiale per decidere O5) — e **una quarta è aperta**:
> L4, il dataset Alighieri. Con L3 è arrivato anche **un debito nuovo**, che ha
> trovato per strada: i criteri di qualità contano su una settimana sola.
>
> ⚠ **E provando il prodotto invece dei test si è visto che il Fermi misura
> pochissimo**: tre builder su ventisette fanno qualcosa, tredici tabelle su
> trentatré sono vuote.
> È L4, ed è ciò che va fatto prima di D2.

---

## 1. Decisioni — aspettano una persona

### D2 🧭 La via d'ingresso dei dati anagrafici

Da scegliere da quando `Partenaire_Index` è escluso
([ADR-012](decisioni.md)): formato nostro, CSV, o aggancio al SaaS di
sostituzioni già in produzione. Aspettava **D1**, che decideva cosa c'è da
inserire: ora si sa, ed è un'etichetta in più sulle righe in alternativa
([ADR-020](decisioni.md)), non un piano per combinazione.

⚠ **Il contesto è cambiato**: il modulo andrà dentro **Aurora**, il gestionale
scolastico in sviluppo, dove l'ingresso dei dati passa da un agente — l'utente
scrive a parole o carica un file (PDF, testo, markdown), l'agente popola la
tabella e **chiede ciò che manca**, l'utente verifica la griglia. La via
d'ingresso non è quindi un formato ma un **dialogo**, e ciò che il modello deve
saper dire è *quale dato manca*: la stessa cosa che i checker con causali
nominate già dicono. ⚠ Da implementare **dopo** che il generatore è
consolidato, non prima.

### D4 🧭 Serve un'interfaccia? — **una direzione c'è**

Oggi il prodotto è un insieme di **management command** (`analyze`, `solve`,
`assign_rooms`, `place_and_fix`, `extract`, `export_ical`) e `config/` è un
progetto Django senza view. Non è una mancanza rispetto a `scope-v1.md` — quel
documento decide funzionalità, non consegna.

**La direzione, dichiarata il 2026-08-28**: non una UI nostra, ma un **modulo
di Aurora** — griglie come quelle di EDT, semplificate e spiegate, più una
bolla AI che segue l'utente passo passo e carica i dati per lui (vedi D2). Ciò
che resta da decidere è il **confine**: quali comandi diventano API e quale
stato vive dove.

---

## 2. Da osservare in EDT

### O2 👁 La configurazione della griglia oraria — **chiusa, un residuo**

**Osservata il 2026-08-29** la finestra `File → Strumenti → Cambia i parametri
della griglia oraria`: giorni lavorativi come **maschera** a sette caselle con
primo giorno configurabile, `Numero di fasce orarie` **in sola lettura** (si
aggiungono o tolgono fasce a un'**estremità** della giornata, mai al centro),
durata di fascia 60 min, suddivisione a **sei valori** con `Nessuno` di default.
La demo è `5 × 10 × 1`, il che chiude per osservazione la codifica
`place = giorno × 10 + rango`. → [tempo-e-calendario.md](edt/tempo-e-calendario.md)

**Osservata lo stesso giorno** anche `Parametri della base dati → Istituto →
Orari`, che è una procedura in tre passi. Il passo 1, **Mezza giornata**: la
pausa **consuma fasce** (6 + 1 + 3 = 10, il `NombreSequencesParJour` della
griglia), le linee sono verdi e trascinabili, la divisione è **globale** e non
per giorno, e la casella *«riprendi all'inizio dell'ora successiva»* è la stessa
discontinuità dell'orologio che l'export iCal già gestisce. Ha aperto un debito
(i giorni esclusi dal conteggio delle giornate libere) e confermato il fuori
scope della mensa, che è un problema di assegnazione a turni con capienze.

Osservati anche i passi **2 Intervalli** e **3 Orari / Fasce orarie**.
L'intervallo è un **confine** e non una fascia (linee gialle *fra* le righe,
contro la riga intera della pausa), e la UI mostra il **salto** dove il file
memorizza il **rango** — `2` e `2` cumulano ai ranghi 2 e 4 della tabella
`RECREATION`, che è una verifica su una trasformazione e non su un numero. Il
passo 3 è il generatore delle **`SlotLabel`**: `Primo orario`, `Durata reale
delle fasce orarie` e `Durata tra le fasce orarie` — la *durata reale* è un
campo **diverso** dalla durata della fascia di calcolo, e sta in un'altra
finestra.

👁 **Il primo dei due residui è chiuso il 2026-08-30**: il pulsante
`Inserisci / cancella una fascia oraria` è **una migrazione, non un
parametro**. L'unità non è la fascia ma la **durata** (`Durata di`, e *«EDT
visualizzerà sempre un numero intero di lezioni»*), la posizione è libera
(`A partire da`), e ciò che sta dopo viene **scalato** — la finestra elenca
attività, intervalli e limiti della mezza giornata. Le due strade sono quindi
davvero diverse: una **converte** la griglia ai bordi, l'altra **manutiene** un
orario esistente da qualunque punto. → [tempo-e-calendario.md](edt/tempo-e-calendario.md)

Resta **un solo** residuo, ed è l'unica osservazione ancora aperta in tutto
questo elenco: dove si imposta il **`Ciclo personalizzato`**
(`NombreJoursParCycle > 7`). Nella finestra di conversione **non c'è**, quindi
vive nel solo wizard di creazione — da confermare.

👁 Nello stesso giro, due cose in più sul passo 3: la radio
`Orari / Fasce orarie` **commuta il pannello** invece di filtrarlo (in modo
`Fasce orarie` il generatore sparisce, perché le etichette ordinali *sono* i
ranghi e non si generano), e l'orologio conferma per la **terza** via i ranghi
2 e 4 degli intervalli e il 6+1+3 della mezza giornata. ⚠ E ha aperto una
minuzia, che sta in **O7**: `Intervallo del pomeriggio` alle 11:50.

### O3 🧪 La semantica del monte ore tripartito — **esperimento, non osservazione**

`Ridotto` (*durata con alunni ridotti*) e `Sdop.` (*durata con alunni
sdoppiati*) sono nel nostro schema dal primo giorno (`reduced_minutes`,
`split_minutes`) e **letti da nessuno**.

⚠ Riclassificata il 2026-08-29: **nessuna delle due basi che abbiamo le
compila** — né il Fermi né quella del produttore, dove sono vuote su tutte le
righe di tutti i piani. Non c'è niente da guardare: «come nascono i gruppi» si
vede solo **compilandole**. E D1 è sciolta, quindi non sblocca più niente: la
domanda che resta è se tenere i due campi o toglierli.

### O4 👁 Quali aule chiede ogni materia

Le aule **non esistono nella base del Fermi** (`NBSALLES = 0`), quindi
`data/liceo-fermi/aule.md` è progetto e non osservazione. Dal 2026-08-28 il
*nostro* dataset le ha (`tests/fermi.py`, `SPECIAL_ROOMS`) perché senza la
seconda fase avrebbe un problema vuoto — ma *quali* aule chieda ogni materia
resta nostra scelta di dimensionamento. → `docs/edt/aule.md`

### O5 🧭 I dieci criteri di piazzamento non tradotti — **non è un'osservazione**

⚠ Riclassificata il 2026-08-29: era marcata 👁, ma **la lista è già osservata e
scritta** — gli undici nomi stanno in
[motore-risoluzione.md](edt/motore-risoluzione.md), rilevati il 2026-07-26 e
**riconfermati** da una seconda schermata della stessa base, valore per valore.
Non manca uno screenshot: manca una **decisione**, una per criterio.

🔧 **Il materiale per rispondere c'è, da L3**:
[criteri-di-piazzamento.md](criteri-di-piazzamento.md) prende i dieci uno per
uno — cosa fa in EDT, cosa già abbiamo che lo tocca, il costo, e la
raccomandazione. La proposta è **sette no e tre forse**; resta da dire sì o no,
che è l'unica cosa che il file non poteva fare.

In EDT i meccanismi sono due e confonderli era l'errore di partenza:
`Ordinamento dei criteri` è la lista degli **undici** criteri di *piazzamento*;
`Ottimizzazione degli orari` è una fase separata con **cinque** valori. Sono
implementati i quattro dell'ottimizzazione più `Rispetta le preferenze`, che è
l'undicesimo criterio di piazzamento. Restano **dieci** nomi su cui dire
dentro/fuori, e tre sono già quasi decisi dalla struttura: `Equilibra i turni di
mensa` cade con la mensa (fuori scope), `Riduci i buchi di mezza fascia oraria`
e `Comincia dall'inizio delle fasce orarie intere` valgono solo con la
suddivisione sub-oraria attiva, che è a `Nessuno` ovunque l'abbiamo vista.

---

### O6 🧭 `MS` — la modalità di scelta del servizio — **letta; resta una scelta**

Nata da [ADR-020](decisioni.md), che ne ha usato la *forma* senza poterne
copiare l'enumerazione. `MS` (*Modalità di scelta*, FR `Modalité d'élection`) è
una colonna della riga di servizio, **vista in UI** e vuota su tutte le righe
del Fermi; i sette codici — `N` Normale, `O` Obbligatoria, `F` Facoltativa, `L`
Accademica, `D` DNL, **`R` Religioso**, `X` Extra — vengono dalle **stringhe**
(📦) e il loro *comportamento* non è mai stato osservato: cosa cambia per il
piazzamento, e se EDT ne derivi qualcosa o sia solo un'etichetta.

👁 **Osservata il 2026-08-29**, e il risultato è un'assenza: la colonna esiste,
il tooltip conferma il nome — *«Modalità di scelta del servizio»* — ed è
**vuota su ogni riga della base del produttore**, `RELIGIONE` compresa, che lì
è un servizio ordinario dovuto da tutti i 390 alunni del piano. **EDT ha il
campo, non il dato**: nemmeno la sua base di riferimento distingue chi fa
religione da chi fa alternativa. → emendamento ad [ADR-020](decisioni.md).

👁 **E la tendina è stata aperta**: i codici sono **otto** più il vuoto, non
sette. Mancava `S = Senza`, che non è «nessun valore» ma **`Tronc commun`**, il
percorso curricolare — la riga che tutti seguono. Tutti gli altri sono forme di
**opzione**. E `L` è `Locale` (`Ajout académique au programme`, aggiunta locale
al programma), non «Accademica»: falso amico, corretto anche nel
[glossario](edt/glossario-it-fr.md). Tabella completa con le spiegazioni in
[piani-di-studi.md](edt/piani-di-studi.md).

**Resta una decisione, non un'osservazione.** `MS` risponde a *«questa riga è
dovuta da tutti?»*; `Service.election_group` a *«di queste se ne segue una»*.
Sono complementari, e noi abbiamo solo il secondo — quindi una riga che fosse
opzione **fuori** da ogni gruppo verrebbe ancora contata come dovuta da tutti,
lo stesso falso positivo che [ADR-020](decisioni.md) ha corretto su un altro
ingresso. Da decidere se aggiungere l'asse (un booleano basta: *tronco comune*
contro *opzione*), sapendo che **nessun dato lo esercita** — `MS` è vuota su
entrambe le basi.

L'esperimento residuo — compilare `MS = R` e guardare se cambia il piazzamento —
è sceso di priorità: un campo che il produttore non compila nemmeno nella
propria base difficilmente muove il motore.

### O7 👁 Due minuzie da un tooltip ciascuna

Non bloccano niente e costano uno screenshot. Stanno qui perché due
affermazioni del repo sono oggi marcate **[INFERENZA]** e un passaggio del
mouse le promuove o le smentisce.

1. L'intestazione **`TOP`** nell'elenco delle aule: la formula `Occ. / (Qtà ×
   50h)` torna su quattro righe su cinque, e su `LAB.ARTISTICA` no (21h su 50
   farebbe 42%, il prodotto dice 72%). L'ipotesi che le riconcilia è che il
   denominatore sia il tempo **disponibile** — cioè che le indisponibilità
   dell'aula escano dal conto. → [aule.md](edt/aule.md)
2. L'**ingranaggio ⚙** accanto a `Intervallo` nel passo 3 di `Parametri →
   Istituto → Orari`: `Intervallo del pomeriggio` sta alle 11:50, cioè nella
   mezza giornata del mattino. O il nome è posizionale, o l'ingranaggio nasconde
   un altro asse. → [tempo-e-calendario.md](edt/tempo-e-calendario.md)

---

## 3. Lavoro — si può fare adesso

Nessuno le sblocca: hanno una risposta tecnica e non aspettano né EDT né una
decisione. **Le tre di apertura sono chiuse il 2026-08-30**; il racconto è in
[changelog.md](changelog.md), e qui restano le righe con la data.

- [ ] **L4 — il Liceo "Alighieri": il banco a scuola intera.** Il modello hard
      è completo, ma il dataset su cui gira il prodotto esercita **tre builder
      su ventisette** — misurato avvolgendo `restrict` e `build` di ciascuno — e
      sul Fermi in un database vero **tredici tabelle su trentatré sono
      vuote**, fra cui `ClassPartition`, `ClassPart` e
      `Group`, cioè le voci ✅ di scope v1 (ADR-013) che **nessun dataset
      rappresenta**. Un secondo dataset costruito apposta, con almeno una riga
      per famiglia e l'esito atteso dichiarato prima dell'esecuzione.
      🔑 **Accanto al Fermi, non al posto suo**: il Fermi è la trascrizione di
      una scuola osservata, e il suo valore sta tutto nel non essere stato
      progettato per superare i nostri test. ⚠ E la regola che lo tiene onesto
      è la **verifica per mutazione**: togliere la riga di una famiglia deve
      cambiare l'orario, o quella famiglia è presente e non esercitata.
      Spec: [2026-08-30-alighieri-banco-a-scuola-intera-design.md](superpowers/specs/2026-08-30-alighieri-banco-a-scuola-intera-design.md)
      — **da approvare**, sette ondate.

- [x] **L1 — il buco misurato sulla mezza giornata.** Il perimetro è ora un
      parametro d'istituto, separato per classi e per docenti
      (`InstituteSettings.gaps_split_at_lunch_*`), letto insieme dal checker
      `MaxGapChecker`, dal builder del D.T.B. e dal criterio `gaps`. 🔑 La
      casella di EDT e lo spezzare alla linea sono **la stessa cosa**, e non è
      un'assunzione: la differenza fra i due perimetri è esattamente la corsa
      libera attorno alla linea, misurata in `tests/test_gap_span.py`.
      ⚠ Il default resta lo status quo (mezza giornata per entrambe), che
      **non** è il default di EDT sulle classi: la scelta cambia la quantità di
      un vincolo hard, quindi è della scuola.
- [x] **L2 — le due voci lasciate da O1 sulla fase 2.** La capienza in alunni è
      ora il **terzo livello** della catena delle aule (`eccedenza_capienza`),
      dopo i minuti senza aula e i cambi, come in EDT sta dopo il cammino e
      l'aula preferenziale — e resta un criterio, non un vincolo: l'aula troppo
      piccola si assegna lo stesso e l'eccedenza si **dichiara**. E c'è il
      lucchetto sulla singola assegnazione (`Placement.room_locked`), distinto
      dall'immobilità della collocazione: si blocca l'aula lasciando l'attività
      libera di spostarsi.
- [x] **L3 — il materiale per decidere O5**, in
      [criteri-di-piazzamento.md](criteri-di-piazzamento.md): i dieci criteri
      uno per uno, con cosa fanno in EDT, cosa già abbiamo, il costo e la
      raccomandazione. Esito: **sette no e tre forse**, e una cosa da fare
      comunque (vedi il debito nuovo qui sotto). ⚠ Il file è un giudizio
      nostro, non documentazione di EDT, ed è marcato come tale.

---

## 4. Debiti dichiarati

Già decisi, e la decisione è stata «non adesso». Si riaprono con un motivo
nuovo, non per fastidio.

- ⚖ **L'oracolo differenziale perde il peggioramento** di una violazione già
  presente, per le famiglie che nominano il secchio invece del violatore: la
  chiave grossolana `(causale, risorsa, settimana)` non distingue «peggio» da
  «uguale». L'alternativa sarebbe riscrivere fuori dai checker la nozione di
  «quale numero è quello cattivo».
- ⚖ **Il testimone del banco resta sporco su `coverage_mismatch`**, per le
  maschere di settimana casuali. Riparazione quantificata (comprendere le
  maschere in coppie complementari, cioè riscrivere `_make_activities` e
  spostare ogni seme appuntato) e **dichiarata inutile**: `coverage_mismatch` è
  `PLACEMENT_INDEPENDENT`, quindi la differenza è vuota per costruzione.
- ⚖ **«Ignora i vincoli dell'attività selezionata»** di `Piazza e sistema`: da
  noi non è separabile per attività, perché i vincoli di A non sono *di* A. Una
  versione parziale sarebbe un modello mentale incoerente, peggiore
  dell'assenza.
- ⚖ **L'arbitrato non dice dove è atterrato** il criterio sacrificato: il
  rendiconto porta base e tetto, non il valore raggiunto. Costerebbe una
  seconda valutazione riappaiata per nome.
- ⚖ **La sostituzione non oscura l'originale** nell'export iCal: per
  [ADR-014](decisioni.md) il sostituto compare da sé, ma l'originale è annuale
  e continua a comparire nella stessa settimana — manca la relazione fra i due
  (`RELATIONCOURSSUBSTITUT` di EDT).
- ⚖ **I giorni esclusi dal conteggio delle giornate libere** non esistono da
  noi. EDT ha una casella per giorno in `Parametri → Istituto → Orari` — *«I
  giorni spuntati saranno ignorati durante il calcolo delle giornate libere»* —
  che **non** è la maschera dei giorni lavorativi: il giorno resta in griglia e
  ci si lavora, ma non conta come giornata (o mezza giornata) libera.
  `FreeGuaranteedChecker` e `FreeGuaranteedBuilder` contano su tutti i
  `days_per_cycle`. Costo: un campo maschera sulla griglia e un filtro nei due
  posti. Non adesso perché nessun dato lo esercita — sul Fermi il sabato non c'è
  proprio. 👁 2026-08-29.
- ⚖ **L'indisponibilità gialla di un'aula: la fase 1 la conta piena, la fase 2
  la toglie.** `structural:room_pool` (ADR-021) azzera i posti di un'aula
  **rossa** e lascia pieni quelli di una gialla, perché un finding `HARD` per
  un ostacolo violabile sarebbe falso; `RoomContext._filtra` invece toglie
  anche le gialle, salvo l'opzione di calcolo. Resta quindi un angolo in cui la
  fase 1 riempie una fascia che la fase 2 non serve. Costo: passare
  `ignora_opzionali` al builder e accettare che builder e checker leggano
  diversamente, o portare l'opzione dentro il checker. Non adesso perché
  nessun dato lo esercita — le due basi non hanno indisponibilità d'aula.
- ⚖ **I criteri di qualità ignorano le firme di settimana.** Contano su una
  settimana sola (`v.occupied(...)` senza `signature`), mentre i vincoli le
  distinguono già — `MaxGapBuilder` posta un budget per firma. Su una scuola con
  attività quindicinali il numero che il rendiconto stampa non è quello di
  nessuna settimana reale. Trovato il 2026-08-30 scrivendo L3, dal criterio di
  piazzamento `Riduci i buchi quindicinali`: EDT ha un criterio apposta, e
  averlo vuol dire che il fenomeno lo conosce. Costo: il ciclo sulle firme
  dentro ogni criterio, e una decisione su cosa il livello minimizzi (la somma
  sulle settimane, o la peggiore). Non adesso perché nessuna delle due basi ha
  attività quindicinali.
- ⚖ **Sei delle dodici voci del menu `Estrai`**, ognuna per una ragione scritta
  accanto al registro: tre riguardano la fascia variabile e il sezionamento
  (fuori per ADR-010), una la formazione classi, due sono filtri di forma e non
  problemi. E gli stati `Scartate` / `In attesa`, che sono sfumature di «non
  piazzata» che il modello non distingue.

---

## 5. Fuori scope, dichiarato

Deciso in [ADR-015](decisioni.md) e in [scope-v1.md](scope-v1.md). Qui solo
perché nessuno debba ricostruire *perché*.

- **Risolutore passo-passo interattivo** — fuori v1, ma la porta è rimasta
  aperta: la condizione 1 di ADR-015 è sciolta da `Piazza e sistema`, che è lo
  stesso motore.
- **Vincoli fra attività** (11 tipi): nella base del produttore quella griglia
  è vuota.
- **Sezionamento**, **alternanza docenti**, **fascia variabile** ([ADR-010](decisioni.md)).
- **Formazione classi** e tutto ciò che richiede l'anagrafica alunni nominativa;
  **multi-istituto**.
- **Mensa** come vincolo, **prenotazione** di aule e materiali, **incarichi** e
  loro effetto sul monte ore.
- **Import `Partenaire_Index`** ([ADR-012](decisioni.md)); **modulo
  sostituzioni** (il committente ce l'ha già). ⚠ Da recuperare però i due
  criteri di reclutamento non ovvi — *«chi ha già un buco lì»* e *«chi è stato
  liberato da un'assenza di classe»* — come nota per **l'altro** prodotto.
- **TRCD/TRMD**, IMP/PACTE e tutta la normativa francese; tutto ciò che è
  PRONOTE.

---

## Chiuse

Il racconto è in [changelog.md](changelog.md), alla data.

- [x] **2026-08-30** — **O1, i criteri dell'ottimizzatore aule**: i quattro
      default sono `Limita gli spostamenti tra attività consecutive`,
      `Favorisci l'utilizzo delle aule preferenziali`, `Minimizza il superamento
      della capienza`, `Nessuno`. 🔑 Il criterio dominante non è «quale aula è
      più adatta» ma **«quanto camminano le persone»**. ⚠ Ne escono tre voci in
      meno dichiarate: la nostra fase 2 non implementa nessuno dei quattro, la
      capienza in alunni è un **criterio** (non un vincolo, ma nemmeno inerte),
      e manca il lucchetto sulla singola assegnazione d'aula.
      → [aule.md](edt/aule.md)
- [x] **2026-08-30** — **Il primo residuo di O2**: `Inserisci / cancella una
      fascia oraria` è una **migrazione**, non un parametro — unità in
      **durata**, posizione libera, e ciò che segue viene scalato (attività,
      intervalli, limiti di mezza giornata). Le due strade per cambiare il
      numero di fasce sono davvero diverse: una converte, l'altra manutiene.
      → [tempo-e-calendario.md](edt/tempo-e-calendario.md)
- [x] **2026-08-29 (sera)** — **D3, la fase 1 cieca alle aule**, sciolta con
      [ADR-021](decisioni.md): non era una decisione di prodotto ma
      un'osservazione già nel repo e letta male — in EDT le aule si **contano**
      mentre si piazza (la causale del picco del gruppo sta nella diagnostica
      del piazzamento), e l'ottimizzatore dedicato sceglie soltanto *quale*.
      Il deficit misurato era esattamente il numero di rinunce (8 e 8), tutto
      su un insieme solo. Ora: **92 richieste su 92**, zero rinunce.
      ⚠ Ha aperto un debito (l'indisponibilità gialla d'aula) e scoperto un
      difetto di integrazione nel filtro `resources` del dominio residuo.
- [x] **2026-08-28 (sera)** — ⛔ **D1, l'unità del monte ore**, sciolta con
      [ADR-020](decisioni.md): la copertura misura l'**atomo**, e le righe in
      alternativa sono un **dato dichiarato** (`Service.election_group`) invece
      che una fusione indovinata. Erano due difetti, non uno: il lato osservato
      (4 scostamenti su una classe sdoppiata due volte) e il lato atteso (2 su
      ogni classe italiana). L'import non è più bloccato. ⚠ Ha aperto **O6**.
- [x] **2026-08-28** — La classe articolata regge (condizione 3 di ADR-015): la
      parte porta un piano proprio, la copertura lo legge, le due articolazioni
      sono simultanee. ⚠ Ha aperto **D1**.
- [x] **2026-08-28** — Il tie-break di `_placed_of` e il cambio di sede dentro
      una fascia: due artefatti dell'ordine d'inserimento, decisi in
      [ADR-019](decisioni.md).
- [x] **2026-08-28** — `Estrai`, `Piazza e sistema`, la classifica dei vincoli
      per fallimenti causati, l'assegnazione delle aule, l'export iCal.
- [x] **2026-08-26** — Il violatore di Hall (condizione 2 di ADR-015: l'analisi
      di capienza è un componente a sé) e gli alleggerimenti a quota con
      l'ottimizzazione lessicografica.
- [x] **2026-08-25** — Il modello CP-SAT hard completo: ventisei builder.
- [x] **2026-07-26** — L'osservazione di EDT, chiusa con
      [ADR-016](decisioni.md); il modello di dominio, approvato.
