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

> **Stato al 2026-08-31.** Nessuna voce ✅ di [scope-v1.md](scope-v1.md) è
> rimasta senza implementazione: il motore, l'analisi, le due fasi, `Estrai`,
> `Piazza e sistema` e l'export iCal ci sono tutti. E **D1 è sciolta**
> ([ADR-020](decisioni.md)): la copertura misura l'atomo e l'alternativa è un
> dato dichiarato, quindi **l'import non è più bloccato**.
>
> **Niente blocca il calcolo, e nessuna decisione è aperta.** D2 e D4 — le due
> che dal 2026-08-28 erano la stessa domanda, il confine con **Aurora** — si
> chiudono il 2026-08-31 con [ADR-027](decisioni.md) e
> [ADR-028](decisioni.md), dopo aver **letto Aurora** invece di ragionarci
> sopra. Restano:
>
> - **tre voci di lavoro**, tutte nate da quella lettura: **L9** (la
>   `ScheduleEntry` non tiene l'ora quindicinale), **L10** (nessun dato
>   dichiara una cattedra su una parte o un raggruppamento) e **L11** (il
>   dominio interroga l'ORM in 77 punti, senza un chokepoint);
> - **tre osservazioni** che richiedono la UI e che nessuno può fare al posto
>   di chi ha il prodotto: l'ultimo residuo di O2 (il `Ciclo personalizzato`) e
>   le due minuzie da tooltip di **O7**;
> - **quattro debiti** dichiarati, tutti con la ragione scritta accanto.
>
> ⚠ **Guardare Aurora ha cambiato tutt'e due le domande, non solo le
> risposte.** D2 chiedeva *«un formato o un dialogo?»*, e la risposta è
> nessuno dei due: **l'orario dell'anno scorso**, perché un `ScheduleEntry`
> aggregato *è* una cattedra (139 su 142). D4 chiedeva *«quali comandi
> diventano API»*, e la prima cosa da decidere era un'altra: **due tenancy
> incompatibili** — 33 tabelle senza chiave di scuola contro un prodotto con
> un chokepoint e un test che lo difende.
>
> O1 è chiusa il 2026-08-30; il 2026-08-31 si chiudono **O5**
> ([ADR-025](decisioni.md): due criteri di piazzamento tradotti su dieci),
> **O6** ([ADR-026](decisioni.md): l'asse tronco comune/opzione), **O3** (i due
> campi restano, dichiarati osservazione e non funzionalità) e **tre dei sette
> debiti** — i giorni esenti dal conteggio delle giornate libere, il valore
> raggiunto dal criterio sacrificato, e la sostituzione che oscura l'originale
> (emendamento ad [ADR-014](decisioni.md)).
>
> 🔧 **La sezione 3, `Lavoro`, ha aperto e chiuso quattro voci lo stesso
> giorno** — L1 (il perimetro del buco), L2 (la capienza come criterio e il
> lucchetto sull'aula), L3 (il materiale per decidere O5) e **L4**, il dataset
> Alighieri, sette ondate su sette.
>
> ⚠ **L4 è nato da una misura che ha corretto ciò che il progetto credeva di
> sé**: provando il prodotto invece dei test, il Fermi esercitava **tre builder
> su ventisette** e lasciava tredici tabelle su trentatré vuote. Ora la sonda
> dice **28 su 28** — il registro è cresciuto di uno con L5 — ed è un test che
> deve **restare fermo**, non salire.
> 🔑 E il banco ha fatto il mestiere per cui esiste: ha prodotto **cinque
> difetti** — L5, L6, L6bis, L7 e L8 — nessuno riparato mentre lo si misurava,
> tutti fissati da un test. Ha anche corretto **due volte** il proprio metodo
> di verifica (la tacca dell'ondata 3, il testimone puntato della 4) e ne ha
> aggiunta una terza (la tensione con la quota, ondata 6), che l'ondata 7 ha
> riusato per l'arbitrato.
>
> ✅ **I cinque difetti sono chiusi il 2026-08-31**, tutti insieme e ognuno col
> proprio test capovolto. Il registro dei builder passa a **28 su 31** checker
> (`structural:alignment`), il vincolo di sede da divieto a **tetto di
> capienza**, il giallo lo conta anche la fase 1, i criteri di qualità si
> calcolano **per firma** (livello = la settimana peggiore) e la soglia delle
> mezze giornate libere è quella **raggiungibile**.
> ⚠ E tre delle correzioni hanno toccato il **dataset**, non il motore:
> leggere `alignment_ident` ha reso visibile che il banco dichiarava
> allineamenti impossibili (le due metà di uno sdoppiamento, stesso docente) e
> ne fondeva tre in uno, e che l'articolata parallela era incompatibile con lo
> spezzone concentrato di RICCI più il tetto di peso d'indirizzo. Il racconto
> sta in [changelog.md](changelog.md) e in
> [`data/liceo-alighieri/gruppi.md`](../data/liceo-alighieri/gruppi.md).

---

## 1. Decisioni — ✅ **nessuna aperta dal 2026-08-31**

### D2 🧭 La via d'ingresso dei dati — ✅ **chiusa il 2026-08-31**

Decisa con [ADR-028](decisioni.md): **l'orario dell'anno scorso è la via
d'ingresso**, e il dialogo chiede il terzo che non c'è dentro. Tre gradini — si
ricava ciò che l'orario dice (le **cattedre**: 139 chiavi su 142 sull'Alighieri),
si dichiara ciò che l'orario non distingue (**dove una classe si sdoppia**: 17
partizioni), si chiede il resto (aule, indisponibilità, vincoli, discipline —
~170 righe su 536).

🔑 Il gradino 2 non è un dettaglio: la griglia piatta **raddoppia ogni
sdoppiamento**, quindi i quadri orari ricavati tornano per **6 classi su 12** e
i profili distinti sono **9 contro 11 piani**. Appiattire e ricavare non sono
l'inverso l'uno dell'altro — scendere perde, risalire *inventa*, e sempre per
eccesso. Senza il gradino 2 il piano ricavato è un piano che nessun orario può
soddisfare, e il generatore risponde `INFEASIBLE` senza che nessuno sappia
perché.

⚠ Il formato nostro e il dialogo-come-via-principale sono **scartati con il
motivo scritto**: il primo perché Aurora ha già un motore d'import a grammatica
chiusa attorno a cui ha costruito una proprietà che non si butta (ogni scuola
che importa un formato nuovo lascia dietro di sé un test); il secondo perché
chiede ciò che si sa già.

### D4 🧭 Il confine con Aurora — ✅ **chiusa il 2026-08-31**

Decisa con [ADR-027](decisioni.md): il generatore è un **modulo di Aurora**, le
33 tabelle prendono la `School`, l'uscita è la `ScheduleEntry` che il motore
delle sostituzioni già legge, e **il calcolo è un lavoro** — coda, stato,
polling — perché un solve per richiesta non ci sta (misurato: 82 s
sull'Alighieri con i criteri di qualità, contro un `--timeout` di gunicorn).

Lo stato sta su tre livelli e il criterio è **chi lo scrive**: l'ingresso è di
Aurora perché lo scrive la scuola, il calcolo è del modulo perché è lo stato di
un lavoro, l'uscita è di Aurora perché è il record permanente.

E i sei comandi **non** diventano sei rotte: tre sono lavori, `analyze` è una
lettura sincrona, `extract` è un **parametro** degli altri e non una rotta,
`export_ical` è la sola già finita.

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

### O3 🧪 La semantica del monte ore tripartito — ✅ **chiusa il 2026-08-31**

`Ridotto` (*durata con alunni ridotti*) e `Sdop.` (*durata con alunni
sdoppiati*) restano nello schema (`reduced_minutes`, `split_minutes`), **letti
da nessuno**, con un commento sul modello che dice cosa sono: **osservazione
registrata e non funzionalità**.

La domanda era «tenerli o toglierli», e la risposta è tenerli. Non c'è niente
da guardare — nessuna delle due basi che abbiamo li compila, né il Fermi né
quella del produttore, dove sono vuoti su ogni riga di ogni piano — quindi
implementarli vorrebbe dire scrivere codice su un dato che non esiste;
toglierli vorrebbe dire perdere un campo che EDT **ha davvero**. Lo schema
dichiara quindi ciò che sa, e dichiara anche di non leggerlo.

### O4 👁 Quali aule chiede ogni materia

Le aule **non esistono nella base del Fermi** (`NBSALLES = 0`), quindi
`data/liceo-fermi/aule.md` è progetto e non osservazione. Dal 2026-08-28 il
*nostro* dataset le ha (`tests/fermi.py`, `SPECIAL_ROOMS`) perché senza la
seconda fase avrebbe un problema vuoto — ma *quali* aule chieda ogni materia
resta nostra scelta di dimensionamento. → `docs/edt/aule.md`

---

### O6 🧭 `MS` — la modalità di scelta del servizio — ✅ **chiusa il 2026-08-31**

Decisa con [ADR-026](decisioni.md): `Service.elective`, un booleano. **Non**
l'enumerazione a otto codici — `S` (`Tronc commun`) contro `N/O/F/L/D/R/X`, che
sono tutte forme di opzione — ma la **partizione** che quell'enumerazione
descrive, perché di quei codici nessun comportamento è mai stato osservato: la
colonna è vuota su ogni riga di entrambe le basi, `RELIGIONE` compresa nella
base del produttore, dove è dovuta da tutti i 390 alunni del piano. EDT ha il
campo, non il dato.

La copertura per alunno lo legge così: un'opzione **fuori** da ogni gruppo di
alternative si salta quando l'unità non ne ha nemmeno un'ora, e si misura
normalmente quando ne ha — *zero o tutta*. È lo stesso falso positivo che
ADR-020 ha corretto su un altro ingresso: un catalogo letto come curriculum.

⚠ **Nessun dataset lo esercita**, che è la condizione con cui la voce era
aperta e non una scoperta; e il banco non è stato piegato per averne uno. Lo
esercitano tre test unitari, ognuno col proprio ramo di controllo.

👁 **L'esperimento residuo resta possibile e resta ultimo**: compilare `MS = R`
in EDT e guardare se il piazzamento cambia. Un campo che il produttore non
compila nemmeno nella propria base difficilmente muove il motore.

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

### L12 ✅ Il gradino 1 di D2 — **fatto il 2026-08-31**

`domain/bootstrap.py` + `manage.py bootstrap`: da una griglia piatta a una
**proposta**. Le cattedre si leggono (**139 chiavi su 142** sull'Alighieri), i
quadri orari si indovinano, e la proposta dice in che direzione può sbagliare.

🔑 **Lo sdoppiamento non è una domanda da fare, è un sospetto da nominare**: la
griglia contiene l'evidenza — la stessa classe due volte nella stessa fascia —
e contare le **celle** invece delle lezioni porta i quadri esatti da **6 a 8 su
12**. Il rilevatore è **sicuro ma non completo**: zero falsi allarmi su due
dataset (sul Fermi, che di partizioni non ne ha, zero sospetti), 28 coppie
trovate su 30.

⚠ E le due mancate sono **un'altra struttura**: il *turno di laboratorio*, dove
le due metà le prende lo stesso docente e quindi non sono mai simultanee. È la
stessa distinzione che L5 aveva dovuto imparare — *sdoppiare non è allineare*.
I quattro quadri che restano storti sono quattro meccanismi diversi (turno di
laboratorio su 3A e 4A, ora quindicinale su 5B, classe articolata su 2C), tutti
fuori dalla portata di una griglia settimanale, e tutti **dichiarati** in
`CECITA` invece che taciuti.

🔑 I numeri sono stabili **per costruzione, non per fortuna** — misurato su
cinque ottimi distinti: le metà di uno sdoppiamento sono allineate (L5) quindi
sempre simultanee, e il turno di laboratorio non lo è mai. Il rilevatore misura
il dataset, non la ricerca.

⚠ **Non ricava tre cose, e le dichiara**: le partizioni (chi sta in quale metà
è anagrafica di alunni), le attività (nascono dalla ripartizione), il
calendario (sono date). E **non legge file**: ADR-028 esclude un secondo
lettore per gli stessi file, quindi entra la griglia già letta.

Resta il **gradino 3** — chiedere aule, indisponibilità e vincoli, che in
nessun orario stanno.

### L9 🔧 La `ScheduleEntry` di Aurora non tiene l'ora quindicinale

La crescita minima che ADR-027 nomina: **un campo di validità** sulla riga
della griglia piatta, non un modello nuovo. È la maschera di ADR-014 che
attraversa il confine.

⚠ Serve al caso **falso**, non a quello incompleto. Delle tre chiavi che la
pubblicazione perde, due sono il raggruppamento trasversale — Aurora sente
«Orlandi insegna a 1A», che è vero e incompleto, ed è la stessa
approssimazione con cui già convive dandosi classi dal nome composto
(`3B/5O`). La terza è l'ora quindicinale, che fa credere ad Aurora una lezione
che **una settimana su due non si tiene**: lì il motore cerca un supplente per
un'ora che non esiste.

🔑 Ed è il punto in cui i due prodotti si scoprono uguali: la sostituzione che
Aurora genera ogni mattina *è* la sostituzione di ADR-014 — una riga con la
maschera di una settimana che oscura l'originale. Aurora la produce, noi la
modelliamo, e oggi non si parlano.

### L10 🔧 Nessun dato dichiara una cattedra su una parte o su un raggruppamento

Misurato il 2026-08-31 mentre si misurava il confine: sull'Alighieri le
cattedre sono **140 su 140 su classe intera**, zero su `class_part`, zero su
`group` — e nessun test ne crea una (`test_teachers.py` prova il ramo a **zero**
unità, non gli altri due). Il `unit` di `TeachingAssignment` ha quindi due rami
su tre che nessun dato esercita, mentre le **attività** scendono eccome alle
parti (34) e ai gruppi (6).

⚠ È la stessa famiglia di L4 — *«il Fermi esercita tre builder su ventotto»* —
e va trattata come quella: prima si misura cosa cambierebbe, poi si decide se
è un buco del dataset o una forma che il dominio non usa davvero.

🔑 E ha già lasciato un'impronta: due delle tre chiavi che si perdono
appiattendo sono esattamente le ore di gruppo **senza cattedra corrispondente**,
perché la quadratura `+/- = 0` del banco è fatta sulle classi.

### L11 🔧 Il dominio interroga l'ORM in 77 punti, senza un chokepoint

Classi Prime tiene `api/intake/` **senza Django**, con un test specchio sul
confine, ed è la disciplina giusta anche qui. Ma la misura dice quanto costa:
**77 siti di query** fuori da `domain/models/` — 21 nei comandi (che diventano
rotte comunque), **36 in tre file** (`analysis/state.py` 16,
`extraction.py` 10, `analysis/capacity.py` 10), il resto sparso.

⚠ ADR-027 lo dichiara **non deciso**, apposta: è un pezzo a sé e va deciso col
suo costo davanti, non come corollario del confine. Ma è anche il prerequisito
pratico della `School` FK — senza un punto solo da cui passano le letture,
scoparle per scuola vuol dire toccarle a una a una.


Nessuno le sblocca: hanno una risposta tecnica e non aspettano né EDT né una
decisione. **Le tre di apertura sono chiuse il 2026-08-30**; il racconto è in
[changelog.md](changelog.md), e qui restano le righe con la data.

- [x] **L5 — l'allineamento genera l'attività complessa.** ✅ **Chiuso il
      2026-08-31**, con [ADR-022](decisioni.md). 📦 Lo XSD
      `Partenaire_Index` dichiara che *l'allineamento genera l'attività
      complessa*: le attività con lo stesso ident sono
      **una** collocazione. Da noi `Activity.alignment_ident` esisteva dal
      giorno dello schema e **nessun builder e nessun checker lo leggeva** —
      dei 16 allineamenti del banco, **14 uscivano dal solve senza una sola
      coincidenza**.
      Ora c'è `structural:alignment`, ventottesimo builder e trentunesimo
      checker. Le due decisioni che la voce chiedeva di prendere prima di
      scrivere il builder, prese: **hard**, non alleggeribile (EDT non lo
      elenca fra le famiglie allentabili, e non potrebbe — alleggerirlo
      significherebbe scomporre l'attività complessa, cioè cambiare
      l'anagrafica); e **tutto il gruppo sulla stessa cella o niente**, perché
      la forma debole «la stessa cella *se* entrambe piazzate» è soddisfatta
      anche dal gruppo mezzo scartato, che è la stessa mezza classe
      abbandonata con un altro nome. Durate diverse dentro un ident non sono
      vietate: l'intersezione dei domini fa già la cosa giusta, e nessuno
      inventa un divieto che l'anagrafica non dichiara. Dominio comune vuoto ⇒
      il gruppo si **scarta**, mai `INFEASIBLE`; congelate in disaccordo ⇒ non
      si posta nulla (ADR-018).
      🔑 **E leggere il campo ha corretto il dato in quattro punti**, che è il
      genere di scoperta per cui il banco esiste: *sdoppiare non è allineare*
      (le due metà hanno lo stesso docente e non sono mai simultanee — lo
      stesso argomento con cui l'ondata 6 aveva rifiutato di allineare l'ora
      quindicinale); **un ident per attività complessa** e non per coppia di
      servizi (📦 *«autant d'alignements que de cours complexes souhaités»* —
      con un ident solo il modello fondeva sei attività su una fascia); e lo
      spezzone di RICCI su **due** pomeriggi invece di uno, perché
      l'articolata parallela, le tre ore concentrate e il tetto di peso
      d'indirizzo erano insieme impossibili. Il bordo dello spezzone non si è
      mosso — tre fasce libere per tre ore — e la tacca dell'ondata 3 si è
      spostata da `(2, 7)` a `(4, 7)`. E infine il **`MG`** è passato da R02
      Donati a P02 Bruni: allineato all'IRC, l'orario dell'insegnante di
      alternativa è quello del cappellano, che viene due giorni, e dodici ore
      in due giornate con una mezza giornata ciascuna fanno dieci. La riga
      aveva perso il **soggetto**; la deroga l'ha seguita, e la sua tensione è
      diventata un pin.
      Dopo: **36 attività allineate su 18 ident, 18 gruppi coincidenti su 18**,
      `OPTIMAL` a zero scarti.

- [x] **L4 — il Liceo "Alighieri": il banco a scuola intera.** ✅ **Chiuso il
      2026-08-30**, sette ondate su sette; il racconto sta in coda a questa
      voce e in [changelog.md](changelog.md). Il modello hard
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
      è la **verifica per mutazione**: una famiglia che il dataset non può
      violare è presente e non esercitata. (La forma della regola è cambiata
      con l'ondata 3 — vedi sotto.)
      Spec: [2026-08-30-alighieri-banco-a-scuola-intera-design.md](superpowers/specs/2026-08-30-alighieri-banco-a-scuola-intera-design.md)
      — approvata, sette ondate.
      **Ondate 1 e 2 fatte il 2026-08-30** —
      [`data/liceo-alighieri/`](../data/liceo-alighieri/) e
      [`tests/alighieri.py`](../tests/alighieri.py). *L'anagrafica*: 12 classi su
      2 indirizzi e 2 sedi, 23 cattedre a `+/- = 0`, 345 ore-alunno e 361
      erogate, 340 attività, griglia 5×8 con la mensa. *Gli sdoppiamenti*: 16
      partizioni, 32 parti, 2 raggruppamenti — IRC/alternativa su tutte e
      dodici, la 2C **articolata** con un piano proprio, un laboratorio a mezza
      classe in 3A, i livelli di inglese che attraversano 1A e 1B. Due fasi
      `OPTIMAL` senza scarti né rinunce, copertura pulita.
      🔑 E la **sonda è ora un test** ([`tests/sonda.py`](../tests/sonda.py)):
      l'insieme dei builder attivi è un cricchetto che ogni ondata deve
      allargare — **4 su 27**, contro i 3 del Fermi, e 27 su 27 è il criterio di
      accettazione dell'ondata 7. ⚠ L'ondata 2 **non** lo allarga, ed è
      corretto: gli sdoppiamenti entrano dalle chiavi di occupazione (ADR-017,
      `structural:occupation` da 1440 a 3440 constraint) e da
      `structural:coverage`, che un builder non ce l'ha per costruzione.
      🔑 Ha già prodotto il suo primo difetto: **L5**, qui sopra.
      **Ondata 3 fatta il 2026-08-30** — l'asse Cardinalità
      ([`data/liceo-alighieri/vincoli.md`](../data/liceo-alighieri/vincoli.md)):
      le otto famiglie di `ResourceTimeConstraint` in **dieci righe**, e la
      sonda passa da 4 a **12 su 27**, il salto più grande che una singola
      ondata possa fare. Due fasi ancora `OPTIMAL` a zero scarti (15 372
      variabili, 8 758 constraint; 71 aule su 71).
      ⚠ **La regola della mutazione è stata corretta, e va saputo prima di
      leggere le ondate seguenti.** «Togliere la riga deve cambiare l'orario»
      non è misurabile: senza funzione di costo sopra lo scarto ogni orario a
      zero scarti è ottimo, e ciò che torna dopo la rimozione dice quale ottimo
      ha trovato la ricerca — misurato, cambiando una riga *estranea* alla
      famiglia il verdetto si ribaltava per tre famiglie su nove. Al suo posto
      si **stringe di una tacca** e si pretende `INFEASIBLE`, che è una
      proprietà del modello e non del testimone. Otto righe su nove la
      superano.
      ⚠ La nona no: il **D.T.B.** non arriva al bordo, e zero buchi per *ogni*
      docente e *ogni* classe resta `OPTIMAL` — 40 fasce contro cattedre da
      10–21 ore, la contiguità è gratis. Misurato e fissato da un test che
      asserisce l'`OPTIMAL`; si stringe all'ondata 7, con la griglia.
      **Ondata 4 fatta il 2026-08-30** — l'asse Relazione
      ([`data/liceo-alighieri/relazioni.md`](../data/liceo-alighieri/relazioni.md)):
      i **tredici tipi** di `SubjectConstraint`, uno per riga, e la sonda passa
      da 12 a **25 su 27**. Due fasi ancora `OPTIMAL` a zero scarti (15 545
      variabili, 11 783 constraint; 73 aule su 73). I due builder che restano
      sono nominati: `structural:unavailability` e
      `structural:didactic_weight`, entrambi dell'ondata 5.
      🔑 **Il testimone puntato, e la regola 4 che torna misurabile.** Sui
      divieti di relazione la tacca dell'ondata 3 non si applica — *una
      proibizione non sparpaglia*: vietare il greco a un giorno di distanza da
      sé stesso non impedisce di metterne tre ore lo stesso giorno, e la tacca
      che sembrava aritmetica torna `OPTIMAL` (misurato). Al suo posto si
      **impone con `pinned` la configurazione vietata** e si pretende
      `INFEASIBLE` con la riga e `OPTIMAL` senza: due proprietà del modello,
      in due direzioni, nessuna dipendente dall'ottimo che la ricerca sceglie.
      **13 su 13**, più tre tacche dove il tipo ha un parametro — e una delle
      tre attraversa i due assi (il tetto orario di una materia diventa
      impossibile per la riga `max_presence` di un docente, scritta
      un'ondata prima).
      ⚠ **Il dataset è cresciuto, ed è dichiarato**: un secondo laboratorio
      sdoppiato in **4A**, perché i quattro tipi `PARTS_*` vogliono quattro
      portatori che non si implichino a vicenda e con la sola 3A non esistono.
      +1 partizione, +2 parti, +2 attività, N01 da 18 a 19 ore, quadratura
      `+/- = 0` intatta.
      **Ondata 5 fatta il 2026-08-30** — risorse, peso e indisponibilità
      ([`data/liceo-alighieri/risorse.md`](../data/liceo-alighieri/risorse.md)):
      le **sei righe di indisponibilità** nei tre livelli e su tre tipi di
      risorsa (docente, classe, aula), i **tetti di peso didattico** (MAT, LAT
      e GRE a 2; 9 / 5 / 12 d'istituto e uno di classe a 40), il **tecnico di
      laboratorio** e i **quattro carrelli di portatili** — cioè le due
      risorse di piazzamento che nessun dataset del progetto aveva mai avuto.
      🔑 La sonda arriva a **27 su 27**, il registro intero: il criterio di
      accettazione della spec (§6) è raggiunto all'ondata 5 invece che alla 7.
      Non chiude il pezzo — la sonda dice che un builder *fa qualcosa*, non
      che ciò che fa morda — ma da qui il cricchetto non deve più salire, deve
      restare fermo. Due fasi ancora `OPTIMAL` a zero scarti (15 233 variabili,
      12 251 constraint; 73 aule su 73). ⚠ Le variabili **scendono** per la
      prima volta: l'indisponibilità è un pre-filtro del dominio.
      🔑 **E il contratto è misto, per la prima volta**: le indisponibilità e i
      tetti per giornata e mezza giornata si provano col testimone puntato
      dell'ondata 4, lo spezzone di RICCI (tre ore in tre fasce) con la tacca
      dell'ondata 3, e il tetto **settimanale** con la sola tacca — perché è
      indipendente dal piazzamento e nessun pin lo può violare. È *il tetto
      inevadibile* di `CLAUDE.md`, e la differenza fra un vincolo che **forma**
      l'orario e uno che si limita ad ammetterlo.
      ⚠ **Un'attesa smentita, e la sbagliata era il dataset**: a tre carrelli i
      due livelli d'inglese non potevano più stare nella stessa fascia, che è
      *il senso* di un raggruppamento trasversale — lo ha detto un test
      dell'ondata 2, diventando rosso. Quattro carrelli, e il testimone diventa
      a tre attività. La regola generale, per le ondate 6 e 7: **un'ondata che
      rompe una forma dell'ondata precedente per accendere un builder sta
      misurando sé stessa.**
      ⚠ **E una misura che ha cambiato due test**: i tetti di peso sono il
      primo vincolo del banco a cambiare il *regime di ricerca* — stesso
      modello, **439 s** con un lavoratore contro **7 s** con otto — quindi i
      due test delle ondate 3 e 4 che cercavano con `workers=1` per
      riproducibilità sono passati a `workers=8` (le loro asserzioni sono
      invarianti, non celle).
      🔑 **E il ramo di controllo dell'ondata 4 ha fatto il suo mestiere**: la
      riga rossa sulla palestra ha reso indisponibile la cella su cui il
      testimone puntato di `forbidden_sequence` metteva le due ore di scienze
      motorie, e da quel momento il primo `assert` restava verde *per il motivo
      sbagliato* (`INFEASIBLE` per il pre-filtro, non per la riga osservata)
      mentre il ramo «senza la riga» diventava rosso. È il caso per cui la spec
      ha reso obbligatorio quel ramo: senza, un testimone si sarebbe svuotato
      in silenzio.
      🔑 Ha prodotto **due difetti**: L6 e L6bis, qui sotto.

      **Ondata 6 (2026-08-30) — quote, qualità e firme di settimana.** L'ora
      **quindicinale** del 5B (una settimana in laboratorio col tecnico, una di
      teoria in aula) porta la **seconda firma di settimana** che il dataset non
      aveva; le due forme di alleggerimento — deroga e margine — su due
      portatori che non sono bordi di nessuna ondata precedente; e la gerarchia
      completa dei criteri di qualità, sei righe e cinque generi.
      🔑 **La quindicinale è la quinta forma di erogazione, e la sola che non
      costa un'ora**: in ogni settimana ne è attiva esattamente una, quindi la
      cattedra e il monte ore dell'alunno restano quelli. Sdoppiare e alternare
      sono cose diverse, e la differenza è tutta nella maschera. ⚠ E
      l'allineamento resta **vuoto**: 📦 lo XSD dice che l'allineamento genera
      *una* collocazione, e le due metà non sono simultanee mai.
      🔑 **Ed è il primo dataset a chiedere all'occupazione ciò che sa fare**:
      è l'unico builder che distingue le firme, e le due metà — stessa classe,
      stessa chiave — possono stare **nella stessa cella**. Testimone puntato:
      `OPTIMAL` con le due metà, `INFEASIBLE` con una metà e l'ora settimanale.
      ⚠ **Un'attesa smentita, e la sbagliata era l'attesa**: «variabili e
      constraint circa il doppio» — no. **15 330 / 13 817** contro 15 233 /
      12 251, cioè +0,6 % e +12,7 %. Una seconda firma non raddoppia il
      modello: costa **quanto le attività che la distinguono**, perché le
      variabili derivate nascono solo dove un builder posta qualcosa e
      `OccupationBuilder` deduplica i constraint identici fra firme. ⚠ E non
      contraddice la nota di `quality.py` sulle firme come «dimensione
      moltiplicativa»: quella misura è sulla **fase 5**, dove ogni checker gira
      una volta per firma. Le due quote costano 11 variabili e 4 constraint.
      🔑 **La forma di verifica delle quote è una terza**, accanto alla tacca e
      al testimone puntato: si mette il dataset in tensione e si pretende che
      la quota lo rimetta in piedi, che senza non ci stia, e che con una quota
      **troppo piccola** nemmeno. La riga di mezzo è quella che porta
      l'informazione — è l'unica che distingue «la quota c'è» da «la quota è
      quella giusta», ed è la mutazione che il docstring di `RelaxationQuota`
      chiede per nome.
      ⚠ **E le quote del dataset non sono consumate dal dataset**: una quota
      consumata *è* una violazione nominata (la quota autorizza, non nasconde),
      e l'ondata 3 pretende che l'orario di base non porti finding `HARD` oltre
      alle aule.
      ⚠ **Un test che misurava il propagatore invece del modello**: la prima
      taratura del margine faceva passare l'infattibilità dal cambio di sede, e
      il solver non ci arrivava — `UNKNOWN` a 180 s e a 120 s. Spostata
      l'aritmetica sulle ore e dichiarate le due giornate col **rosso** (che il
      pre-filtro toglie davvero) invece che col `days`, i tre casi chiudono in
      37 s.
      🔑 **E il verde dell'ondata 5 chiude il suo anello**: là si provava che
      **non vieta**, qui che **conta** — col solo criterio delle preferenze
      installato, `preferences_all` scende a zero e lo dimostra. Un pre-filtro
      che non filtra e un criterio che non conta si somigliano molto.
      ⚠ **E il «da solo» è una seconda attesa smentita**: sulla gerarchia
      intera la prima misura dava zero e la seconda **1**. 🔑 Un livello sotto
      un livello **non dimostrato** eredita l'indeterminatezza di quello — i
      tre livelli sopra il verde esauriscono il budget, quindi vengono fissati
      al valore che la ricerca *ha trovato*. È una proprietà della catena
      lessicografica che nessuna misura aveva ancora esposto, ed è perché il
      rendiconto si asserisce come «almeno un livello col divario aperto» e non
      quali.
      ⚠ I sei criteri di qualità portano un `solve` da 9 a **82 s**, quindi
      `build()` **non li installa**: li chiede chi li vuole. È anche la forma
      giusta — in EDT l'ottimizzazione è un comando a sé, che si lancia su un
      orario che già c'è.
      🔑 Ha prodotto **un difetto**: L7, qui sotto.

      **Ondata 7 (2026-08-30) — i comandi, e il pezzo si chiude.**
      ([`data/liceo-alighieri/comandi.md`](../data/liceo-alighieri/comandi.md))
      Nessuna riga nuova nel dataset: la domanda dell'ultima ondata è quella a
      valle di tutte, §7 della spec — *i cinque comandi diagnostici hanno
      qualcosa di vero da dire su questa scuola?* Un comando che gira e
      risponde «niente da segnalare» è verde e non prova niente.
      Il criterio di accettazione di §6 è già soddisfatto dall'ondata 5 e resta
      **fermo**: sonda a 27 su 27, asserita come insieme.
      🔑 **La classifica dei vincoli ordina quindici famiglie** contro l'unica
      del Fermi — che sono *letteralmente* le «tre indisponibilità» che §7
      dichiara insufficienti — e la prima riga è un vincolo di materia, non
      un'indisponibilità. La fase 5 nomina un insieme deficiente vero quando si
      stringe il laboratorio unico della succursale; tutti e **sei** i
      rilevatori di `Estrai` trovano almeno un'attività; `place_and_fix` costa
      **tre** attività spostate contro l'una del Fermi; `assign_rooms` è
      `INFEASIBLE` in fase 1 col gruppo di aule e rinuncia senza.
      ⚠ **Due attese smentite, e sono di natura diversa** — è la ragione per cui
      la regola 3 della spec chiede *quale* delle due era sbagliata.
      La prima è **dell'attesa**: la classifica a riposo dà tre causali e non
      cinque, perché `free_candidates` spiazza *tutte* le candidate prima di
      calcolare i domini — su un orario dove niente è congelato l'occupazione
      non occupa e un vincolo *fra due ore* non ha soggetto. La classifica va
      misurata dove serve, cioè su un orario **quasi fatto**: lì sono quindici.
      La seconda è del **dataset**: il tetto di non-regressione dell'arbitrato
      **non morde**, su nessuna delle sei configurazioni misurate — quaranta
      fasce per ventinove ore lasciano a docenti e classi abbastanza spazio da
      non competere, e i buchi della popolazione ottimizzata scendono a zero
      *dimostrato* in tutte. ⚠ E la strada del criterio non dimostrato è stata
      provata e scartata: sacrificando `free_half_days_teachers` i valori sono
      usciti 121 / 122 / 124 al crescere della tolleranza, cioè nella direzione
      sbagliata — l'ondata 6 che si paga due volte.
      🔑 **La risposta è la terza forma di verifica**: si mette il dataset in
      tensione (base portata a zero da un primo arbitrato sulle classi, una
      cella rossa in mezzo alla giornata della 1A, due ore puntate ai lati del
      buco) e i tre verdetti tornano quelli dell'ondata 6 — `INFEASIBLE` a
      tolleranza 0, `INFEASIBLE` a 60 e `FEASIBLE` a 180. Il buco vale 60
      minuti per **tre chiavi**, la classe e le sue due parti.
      🔑 **E due contratti si sono dovuti riscrivere come argomenti invece che
      come misure**, perché la prima stesura misurava l'ottimo che la ricerca
      aveva scelto: `place_and_fix` cerca una cella dove due attività *diverse*
      confliggono con la terza — una per la classe, una per il docente — così
      «almeno due si spostano» è vero per costruzione; e il gruppo di aule si
      prova col **testimone puntato** (tre ore di fisica sulle stesse due aule
      candidate, imposte sulla stessa cella) invece che con un calcolo libero,
      che aveva dato 1 rinuncia in una esecuzione e 2 nell'altra.
      ✅ **E il criterio di §4 della spec — «stretto ma risolvibile» — è
      verificato sul dataset intero**, che è ciò che tre file del banco
      rimandavano a quest'ondata: spegnendo `LAB-SUCC` il banco scarta **11**
      attività (le sue), spegnendo un docente le sue ore (3, 12, 20 sui tre
      campionati); l'aula magna, che nessuno usa, non costa niente ed è
      corretto. 🔑 **Ma «stretto» ha due nozioni, e la spec ne dichiarava una
      sola**: questa è stretta rispetto alle **risorse**, mentre la contiguità
      che il D.T.B. chiede è stretta rispetto alla **densità della griglia** —
      quaranta fasce contro cattedre da 10–21 ore la rendono gratis. I due
      test che asseriscono l'`OPTIMAL` (il D.T.B. dell'ondata 3 e la tacca dei
      divieti della 4) restano quindi verdi e restano giusti, e il «diventerà
      rosso all'ondata 7» che li accompagnava era sbagliato: corretto dove
      stava scritto.
      🔑 Ha prodotto **un difetto**: L8, qui sotto.
      **Il pezzo L4 è chiuso.** I **cinque** difetti che ha trovato — L5,
      L6, L6bis, L7 e L8 — sono suoi prodotti e non suoi residui, e sono stati
      chiusi il **2026-08-31**, tutti insieme, ognuno col proprio test
      capovolto e col proprio ramo di controllo.

- [x] **L7 — i criteri di qualità e le firme di settimana.** ✅ **Chiuso il
      2026-08-31**, con [ADR-024](decisioni.md). I criteri si calcolavano
      sull'**unione** delle settimane, e
      il testimone è aritmetico: il 5B col laboratorio quindicinale alla
      seconda fascia e la teoria alla terza ha un buco di 60 minuti in *ogni*
      settimana — la 2 nelle pari, la 1 nelle dispari — e nell'unione (0-1-2-3
      occupate) di buchi non ce n'è nessuno. Lo stesso orario valeva 60 minuti
      per `check_schedule` e **zero** per il criterio `gaps`. Era lo stesso
      difetto che `MaxGapBuilder` aveva fino al 2026-08-24: il builder passava
      `signature`, i criteri no.
      La decisione che la voce chiedeva — *è una decisione, non una correzione
      ovvia* — è stata presa sull'**aggregazione**, e contro le altre due per
      la regola della casa (*dove il checker esiste, la definizione si legge da
      lì*): il livello è il **massimo fra le firme**, cioè la settimana
      peggiore. La somma direbbe 360 dove il checker dice 180, e il numero
      dipenderebbe da quante firme ha il dataset; la somma pesata per settimane
      sarebbe la quantità annuale — vera, ma di un'altra unità, e
      `Arbitrato.tolleranza` è un numero che l'utente scrive nell'unità del
      criterio.
      ⚠ Il prezzo è dichiarato: sul massimo, migliorare una firma che non è la
      peggiore non muove il livello. Il costo moltiplicativo che la voce
      temeva è mitigato dalla deduplicazione delle firme (la stessa di
      `ResourceBuilder`): su un dataset a firma unica non cambia **nessun**
      numero, e infatti i venti test di `test_solver_qualita.py` sono passati
      senza toccarne uno.

- [x] **L8 — lo scarto è una via d'uscita universale.** ✅ **Chiuso il
      2026-08-31.** Spegnendo la **palestra** il modello non scartava:
      rispondeva `INFEASIBLE`, che è ciò che `allow_unplaced=True` dovrebbe
      rendere impossibile. La causa era una sola riga, isolata togliendone
      dieci una per volta: `free_guaranteed` su P01 Zanetti. Una mezza giornata
      libera conta solo su un giorno **lavorato** (`libera = attivo AND NOT
      metà`), e un giorno lavorato ne offre al più una: con un giorno solo il
      massimo è **uno**, e la riga ne chiedeva due.
      Delle due strade che la voce lasciava aperte è stata presa la **prima**:
      la soglia effettiva è `min(richieste, giorni lavorati)`, nel checker e
      nel builder insieme (`AddMinEquality`, una definizione e non un
      vincolo). Non è un'attenuazione della garanzia — è la garanzia detta
      senza la parte che nessun orario potrebbe onorare, e dove i giorni
      bastano non cambia un bit. La seconda strada (contare diversamente) resta
      esclusa per la ragione di sempre: contare le mezze libere su tutti i
      giorni accetterebbe orari che il checker boccia.
      ⚠ `free_days` **non** prende lo stesso trattamento, ed è la metà che
      spiega la prima: lavorare meno *aumenta* i giorni liberi, quindi quel
      minimo non è mai reso irraggiungibile dallo scarto.

- [x] **L6 — un insieme non viaggia.** ✅ **Chiuso il 2026-08-31**, con
      [ADR-023](decisioni.md). Il banco lo
      aveva trovato costruendo la sua unica risorsa **senza sede**: quattro
      carrelli di portatili sono della scuola, non di un edificio, e servono
      l'inglese alla centrale e l'informatica in succursale. Ma
      `SiteTransitionBuilder` postava la clausola «due sedi sulla stessa
      fascia» su **ogni** chiave di occupazione, e pretendeva in più
      `site_transition_slots` fasce libere fra due sedi diverse: per un
      *insieme* di carrelli entrambe le cose sono false. Misurato:
      `INFEASIBLE` a capienza 4 con domanda 3, `INFEASIBLE` ancora a capienza
      **9** — quindi non era capienza.
      La decisione che la voce chiedeva — *«la sede è una proprietà
      dell'attività, non della risorsa, quindi "questa chiave viaggia" non è
      deducibile dal tipo»*, col candidato `simultaneous_capacity > 1` e la
      sua obiezione (l'aula col `Numero di aule`, che un luogo ce l'ha) — si è
      sciolta **cambiando la domanda invece di rispondere a quella**. Non
      «questa chiave viaggia?», ma «**ci stanno?**»: il vincolo è ora un tetto
      di capienza, `carico(sa, s) + carico(sb, t) <= posti`. A capienza 1 —
      ogni docente, classe, parte, atomo — coincide **riga per riga** con la
      clausola di prima (due carichi valgono almeno due, un posto non li
      regge), quindi l'obiezione dell'aula cade da sola: nessuna chiave a
      capienza 1 cambia comportamento, e sulle due che cambiano la vecchia
      regola diceva il falso.
      Ne discendono due cose misurate: il ramo `s == t` è ora **implicato** da
      `structural:occupation` (un sottoinsieme del carico di una cella non può
      superare la capienza se il totale non la supera), e il checker conta con
      la stessa disuguaglianza — che è ciò che tiene in piedi l'oracolo
      differenziale.
      ⚠ **E una terza cosa era sbagliata**: la prima stesura tolse la guardia
      `_sede_congelata` credendo che `residual_cap` la contenesse, e il banco
      che congela ha risposto `INFEASIBLE` sulla prova A (semi 6 e 9). Col
      residuo a zero ogni **libera** viene cacciata dalle celle in cui la
      coppia è già rotta, comprese quelle in cui già stava. La guardia resta,
      generalizzata a «le sole congelate hanno già superato il tetto»; la
      differenza con `structural:occupation`, che clampa e fa bene, è la forma
      del finding — là la causale nomina tutta la cella, qui una **coppia**
      che nella baseline c'era già.
      🔑 E il carrello resta l'unica risorsa del progetto che possa mostrare
      [ADR-019](decisioni.md) — *dentro una fascia non si viaggia* — ma la
      seconda metà di quel test era falsa e ora è capovolta: due sedi
      simultanee su tre carrelli non sono nemmeno un'impossibilità. Lo tornano
      appena i posti non bastano.

- [x] **L6bis — il giallo su un'aula a più candidate.** ✅ **Chiuso il
      2026-08-31**, come emendamento a [ADR-021](decisioni.md). Le tre
      letture dello stesso giallo erano tre: il checker lo
      classifica `Severity.OPTIONAL`, il pre-filtro lo rispetta come una rossa,
      `structural:room_pool` lo **ignorava**. Due su tre erano d'accordo, e la
      terza pagava — su un'aula a più candidate la fase 1 piazzava e la fase 2
      **rinunciava**, cioè esattamente ciò che [ADR-021](decisioni.md) esiste
      per non far succedere.
      Ha cambiato la terza, nel checker e nel builder insieme: il giallo chiude
      il posto come il rosso. L'argomento che la teneva com'era — *«l'opzionale
      è violabile per definizione, contarlo come chiuso produrrebbe un finding
      HARD per un ostacolo che duro non è»* — si rovescia guardando chi paga:
      l'ostacolo è duro *finché non lo si autorizza*, ed è la frase letterale
      della documentazione. L'autorizzazione esiste e il builder la legge
      (`ignora_opzionali`, per **categoria** di risorsa — A4), la stessa che
      legge la fase 2. ⚠ Il checker no, e non può: legge un orario, non i
      parametri di un calcolo. È la stessa asimmetria che
      `structural:unavailability` ha fra le sue due facce da sempre.

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
nuovo, non per fastidio. **Erano sette; il 2026-08-31 se ne pagano tre** — i
giorni esenti dal conteggio delle giornate libere, il valore raggiunto dal
criterio sacrificato e la sostituzione che oscura l'originale — e i quattro che
restano sono quelli la cui riparazione costerebbe più di ciò che comprerebbe,
o che nessun dato esercita.

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

- [x] **2026-08-31** — ⛔ **D2 e D4, il confine con Aurora**, sciolte con
      [ADR-027](decisioni.md) e [ADR-028](decisioni.md) dopo aver **letto
      Aurora** (`Mactywd/aurora` a `ff0a750`) invece di ragionarci sopra.
      Il generatore è un **modulo di Aurora**, il calcolo è un **lavoro** e non
      una richiesta (82 s con i criteri di qualità, contro il `--timeout` di
      gunicorn), l'uscita è la `ScheduleEntry` che le sostituzioni già leggono;
      e la via d'ingresso è **l'orario dell'anno scorso**, con il dialogo sul
      terzo che manca. ⚠ Guardare ha cambiato **le domande**: la prima cosa da
      decidere non erano le rotte ma **due tenancy incompatibili**, e la
      risposta a D2 non era «un formato o un dialogo» ma un dato che Aurora ha
      già. Ha aperto **L9**, **L10** e **L11**.
- [x] **2026-08-31 (sera)** — **Tre debiti su sette pagati**, e ognuno ha
      portato una decisione più grande della riparazione. I **giorni esenti dal
      conteggio delle giornate libere** (`InstituteSettings.free_day_exempt_mask`)
      hanno aggiunto un **secondo clamp** accanto a quello di L8, con un'altra
      ragione: quello nasce dal piazzamento, questo dalla maschera — con k
      giorni contabili non se ne possono avere più di k liberi. ⚠ E il criterio
      di qualità `free_half_days` **non** li filtra, dichiarato: la casella
      parla di una *garanzia*, il criterio minimizza mezze giornate
      **occupate**, e filtrarlo trasformerebbe «occupa meno» in «occupa
      altrove». Il **valore raggiunto dal criterio sacrificato** si legge
      dallo stesso solver che chiude l'ultimo livello — nessun secondo
      `Solve` — e la prima misura ha subito detto qualcosa che base e tetto
      non dicevano: su `test_la_tolleranza_e_dichiarata_nel_rendiconto` il
      criterio *peggiora davvero* di un punto, e due dei tre concessi
      restano inutilizzati. La **sostituzione che oscura l'originale** è
      l'emendamento ad [ADR-014](decisioni.md): `Activity.substitutes` è la
      relazione *e* il campo `natura` che quell'ADR chiedeva, la soppressione
      dell'occorrenza **si deriva** invece di essere una seconda tabella, e
      🔑 il filtro **non vive nell'export** — `effective_week_masks` sta sul
      modello e la leggono tutti e quattro i lettori di maschere, perché
      l'orario di quella settimana è uno solo e un calendario che mostrasse
      una cosa e i checker un'altra sarebbe lo stesso difetto con un passo in
      più.
- [x] **2026-08-31** — **O6, la modalità di scelta del servizio**, decisa con
      [ADR-026](decisioni.md): `Service.elective`. Non l'enumerazione a otto
      codici ma la **partizione** che descrive — tronco comune contro opzione —
      perché di quei codici nessun comportamento è osservabile: `MS` è vuota su
      entrambe le basi. Chiude lo stesso falso positivo di ADR-020 su un altro
      ingresso: un'opzione **fuori** da ogni gruppo veniva contata come dovuta
      da tutti.
- [x] **2026-08-31** — **O3, il monte ore tripartito**: i due campi **restano**,
      dichiarati sul modello come osservazione registrata e non funzionalità.
      Implementarli sarebbe scrivere codice su un dato che non esiste;
      toglierli sarebbe perdere un campo che EDT ha davvero.
- [x] **2026-08-31** — **O5, i dieci criteri di piazzamento**, decisa con
      [ADR-025](decisioni.md): **due sì e otto no**. Entrano il 4
      (`Distribuisci nella settimana le attività della stessa materia`, sulle
      classi) e l'8 (`Evita le attività della stessa materia nella stessa ora`,
      sui **docenti**), come righe di `QualityCriterion`. 🔑 La decisione non
      è *quali due*: è che **cambiano meccanismo**. In EDT quegli undici
      governano un'euristica di ricerca, che in CP-SAT non esiste; tradurne uno
      vuol dire spostarlo nell'altro riquadro, dove diventa un livello. La
      direzione è quella prudente — un criterio non posta vincoli di
      ammissibilità, quindi non può rendere infattibile ciò che un'euristica al
      più rallentava. ⚠ **Una delle otto righe rosse ha cambiato motivo**: il 5
      (`Riduci i buchi quindicinali`) era «fuori per ora, ma nasconde un
      difetto», e L7 il difetto l'ha pagato — è **già dentro**, senza che
      nessuno lo traducesse. 🔑 E scrivere i due ha scoperto che con
      `regularity` sono **la stessa funzione**, con il secchio e il segno
      cambiati.

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
