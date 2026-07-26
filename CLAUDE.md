# orariogen — generatore di orari scolastici

## Cos'è questo repository

Fase di **analisi** di un generatore di orari scolastici open source, pensato come
modulo affiancato a un SaaS di gestione sostituzioni già in produzione (React +
Django).

Il metodo di lavoro è **reverse engineering di EDT** (Index Education), il software
usato da quasi tutte le scuole italiane per l'orario. Inseriamo i dati di una
scuola di esempio (Liceo "Enrico Fermi") nella UI reale di EDT, campo per campo, e
documentiamo cosa ogni campo significa e cosa implica per il nostro schema Django.

Non è un porting: è reverse engineering delle feature, per decidere **cosa
implementare** e **cosa dichiarare fuori scope**.

## Struttura dei documenti

```
CLAUDE.md              questo file — stato, convenzioni, indice, changelog
docs/
  edt/                 un file per entità EDT (semantica, non dati)
    discipline.md      campi osservati, tooltip, default, semantica, implicazioni
    materie.md
    classi.md
    docenti.md
    aule.md
    gruppi.md          classe → suddivisione → gruppo; raggruppamenti trasversali; IRC/alternativa
    piani-di-studi.md  (in corso — campi visti, semantica in parte da confermare)
    bisogni-previsionali.md  fabbisogno ore per materia e allineamenti
    attivita.md        servizio → sotto-servizio → attività, assegnazione docenti
    vincoli.md         indisponibilità, vincoli orari, di materia e attività↔attività
    schema-scambio.md  📦 lo schema XSD ufficiale Partenaire_Index V4.6 — modello dati formale
    nomenclatura-sidi.md 📦 tabelle ministeriali MIM incorporate in EDT (indirizzi, materie, quadri orari)
    motore-risoluzione.md 📦 come EDT risolve: pipeline, criteri, alleggerimenti
    formato-file.md    📦 il formato binario .edt, per validare la semantica sui dati reali
    glossario-it-fr.md 📦 IT ↔ FR ↔ EN — ⚠ contiene l'inversione gruppo/raggruppamento
    estratti/          materiale grezzo di estrazione (NON documentazione — vedi il suo README)
  decisioni.md         ADR leggeri: decisione, alternative, motivo, data
data/
  liceo-fermi/         dataset della scuola di esempio, in markdown tabellare
    README.md          parametri, dimensionamento, indice del dataset
    discipline.md
    materie.md
    classi.md          elenco classi + quadro orario (monte ore)
    docenti.md         cattedre
    piani-di-studi.md  i 5 piani (indirizzo × anno) e i servizi
    aule.md
    vincoli-attesi.md  conflitti inseriti apposta come test del solver
preparazione/          screenshot delle viste del modulo Preparazione (sessione 2026-07-15)
scripts/
  genera_orario.py     prototipo solver CP-SAT — parcheggiato, vedi sotto
results.md             output dell'ultima esecuzione del prototipo
requirements.txt       ortools (serve solo al prototipo)
```

Ogni file in `docs/edt/` descrive **l'entità EDT** (campi visti nella UI, tooltip
letterale, default, semantica dedotta, implicazioni per il nostro modello). Ogni
file in `data/liceo-fermi/` contiene **i dati concreti** della scuola di esempio.

## Convenzioni

- **Cascate di default (globale → entità → istanza).** EDT eredita i default lungo
  una catena. Nel nostro schema `NULL` significa "eredita": **non** materializzare i
  default nelle righe, risolvere la cascata a runtime. Vedi
  [ADR-003](docs/decisioni.md).
- **La disciplina è una tabella, non un enum.** Le scuole la personalizzano. Va
  mappata alle classi di concorso (A011, A027…), perché la normativa sulle
  sostituzioni ragiona per classe di concorso. Vedi [ADR-001](docs/decisioni.md),
  [ADR-002](docs/decisioni.md).
- **I gruppi sono entità distinte dalle classi** (sdoppiamenti, corsi a effettivo
  ridotto). Una classe non è un blocco monolitico. Vedi [ADR-004](docs/decisioni.md).
- **Terminologia in italiano** nei doc; **codice e identificatori in inglese**.
- **Niente accumulo di versioni**: se una scoperta contraddice qualcosa di già
  scritto, si corregge esplicitamente il file dell'entità, non si aggiunge una
  variante accanto.
- **Non inventare campi**: si documentano solo i campi effettivamente osservati
  nella UI di EDT. Ciò che è nostra estensione (es. mappatura classe di concorso) va
  segnalato come tale, non spacciato per campo EDT.
- **Tre fonti, marcate.** Oltre all'osservazione diretta della UI (fonte di
  default, non marcata) usiamo la [guida online ufficiale](https://docs.index-education.com/docs_it/it-supporto-edt-personnel-client.php)
  di EDT (**📖**) e gli **artefatti dell'installazione** (**📦**: schemi XSD,
  tabelle XML, stringhe dai binari, basi di esempio). Ciò che proviene **solo
  dalla guida** va confermato in UI appena possibile (chiedere all'utente uno
  screenshot della vista corrispondente); alla conferma il marcatore si toglie.
  Gli artefatti 📦 hanno autorevolezza variabile — uno **schema XSD annotato vale
  più di uno screenshot**, una stringa estratta da un binario vale molto meno.
  Gerarchia completa in [ADR-009](docs/decisioni.md).

## Stato del progetto

Coperto finora (una scuola di esempio inserita in EDT):

- Discipline, materie e relativo monte ore.
- Cattedre dei 18 docenti (288 ore-classe, quadratura verificata).
- Aule e loro vincoli di occupazione.
- Il campo `Al./Rid.` sulle materie e la scoperta della **cascata di default**.
- La scheda **Docente** campo per campo: la distinzione fra capacità (materie
  insegnabili), preferenza e assegnazione, e i campi previsionali calcolati.
- I conflitti attesi da usare come test del solver.
- L'intera catena **Preparazione → Orario**: ripartizione puntuale (18 docenti a
  `+/- = 0`) e creazione delle attività — **284 attività / 288h00**, tutte "Non
  piazzata", in Orario > Attività (`docs/edt/attivita.md`).

### Prototipo solver — parcheggiato

`scripts/genera_orario.py` (commit `0ac80ac`) è un test **esplorativo** con OR-Tools
CP-SAT sul dataset Fermi: serviva a vedere se l'approccio poteva reggere, niente di
più. Modello minimo — monte ore per (classe, materia), una classe per slot, un
docente per slot — su 10 classi × 5 giorni × 6 ore: **OPTIMAL in 0.14s, 3180
variabili** (output in `results.md`).

**Cosa non copre:** aule, blocchi di ore consecutive, indisponibilità docente,
buchi, gruppi/sdoppiamenti — cioè quasi tutti i conflitti di
[`data/liceo-fermi/vincoli-attesi.md`](data/liceo-fermi/vincoli-attesi.md). Quel
OPTIMAL quindi **non dice nulla** sulla risolvibilità dell'istanza reale: è la
risposta a un problema più facile.

**Il solver resta fermo qui** finché il reverse engineering di EDT non è completo e
non sappiamo con sicurezza quali feature vogliamo implementare. Prima si capiscono
**tutti** i vincoli, poi si costruisce il modello — non si aggiungono vincoli al
prototipo un pezzo per volta. Vedi [ADR-008](docs/decisioni.md).

### Aperto / da verificare

**Chiuso il 2026-07-26** dagli artefatti dell'installazione (📦):

- [x] **Vincoli di indisponibilità docente** (già osservati in UI il 2026-07-15):
      etichette troncate ora **complete**, terzo pennello = **`Preferenze`**,
      `D.T.B.` = *Durata tollerata dei buchi*. → `docs/edt/vincoli.md`
- [x] **Vincoli di materia** (12 tipi + enum a 13 valori) e **vincoli
      attività↔attività** (11 tipi, con flag di opzionalità). → `docs/edt/vincoli.md`
- [x] ~~**Occupazione simultanea** = gruppo di aule con `Nr > 1`~~ → **conclusione
      sbagliata, corretta in UI**: è il campo `Numero di aule` sull'aula stessa
      (colonna `Qtà`). Le sotto-aule sono un meccanismo separato. →
      `docs/edt/aule.md`
- [x] **Indisponibilità di classi e aule**: il meccanismo rosso/giallo/verde è
      **generico sulla risorsa**. Indisponibilità e assenze condividono **una sola
      tabella**. → `docs/edt/vincoli.md`
- [x] **Colonne dei servizi**: `A`, `Coeff.` (= *Pondération*), `MS`, `Ridotto`,
      `Sdop.` → `docs/edt/piani-di-studi.md`. **`Spec.`**: due colonne omonime con
      significati diversi → `docs/edt/glossario-it-fr.md`
- [x] **Allineamenti**: l'allineamento **genera l'attività complessa** (dichiarato
      nello schema XSD ufficiale). → `docs/edt/schema-scambio.md`
- [x] **Gruppi e sdoppiamenti**: `Classe → Suddivisione → Gruppo`, con
      `Raggruppamento` trasversale a più classi. ⚠ Attenzione all'**inversione
      terminologica IT↔FR**. → `docs/edt/gruppi.md`
- [x] **IRC vs. attività alternativa**: modellato come **due parti della stessa
      classe** (`_REL` / `_ALT`), non come gruppi né come compresenza. Verificato
      sui dati. → `docs/edt/gruppi.md`
- [x] **`Mh/s`** = *Monte ore settimanale* = FR `Apport`: monte ore contrattuale,
      scomposto per disciplina. → `docs/edt/docenti.md`
- [x] **Blocchi di ore consecutive** = durata dell'attività; lo spezzamento è
      **padre/figlio** sulla stessa entità. → `docs/edt/attivita.md`

**Chiuso il 2026-07-26 osservando la UI** sulla base di esempio del prodotto
(`~/Desktop/EDT_COMPLETE/Esempio.edt`, copia di lavoro):

- [x] **Confermate in UI le due griglie di vincoli** ricostruite dalle stringhe.
      `Vincoli delle materie delle classi` è **popolata con dati reali** (19
      righe su `2 A/R`); `Vincoli tra attività` è vuota ma il suo menu espone
      **esattamente gli 11 tipi** previsti. → `docs/edt/vincoli.md`
- [x] **L'opzionalità dei vincoli fra attività** è una casella **spuntata di
      default**, con la semantica scritta in chiaro: *"può essere alleggerito
      durante il piazzamento delle attività scartate"*. Conferma in UI della
      strategia a due passate. → `docs/edt/motore-risoluzione.md`
- [x] **Cosa vincola l'assegnazione di un'aula**: tre soli vincoli
      (`Sedi distaccate`, `Indisponibilità opzionali`, `Indisponibilità`).
      Capienza, categoria e tipologia **non sono vincoli**. → `docs/edt/aule.md`
- [x] **Le `Tipologie` dell'aula** sono tag di dotazione a due livelli definiti
      dall'utente, non il "tipo d'aula". Il legame didattica↔aula passa dalla
      **classe** (`Aula preferenziale`), non dalla materia. → `docs/edt/aule.md`
- [x] **La cascata di default vale anche sulle aule** (suffisso `(Gr.)` sui campi
      ereditati dal contenitore). → `docs/edt/aule.md`
- [x] **Le dieci colonne dei vincoli di materia**, decodificate dall'aiuto
      contestuale del prodotto. `Attività in gruppo` = ordine fra ore in gruppo e
      ore a classe intera (i quattro valori `Parties…Classe`); `Conc. Imp.` =
      concatenazione imposta con **ritardo massimo**. La discrepanza 10-contro-12
      si spiega: alcuni "tipi" sono valori di parametro della stessa colonna.
      → `docs/edt/vincoli.md`
- [x] **`MMG`** e **`MG`** sulla classe = `Massimo di mezze giornate di lavoro` e
      `Lavorare solo mezza giornata al giorno` — **gli stessi vincoli orari del
      docente**, applicati alla classe. → `docs/edt/classi.md`

**Ancora aperto:**

- [ ] ⚠ **Le aule non esistono nella base del Fermi** (`NBSALLES = 0`):
      `data/liceo-fermi/aule.md` è progetto, non osservazione, e va creato in EDT
      per provare i vincoli di aula *sul nostro dataset*. Il meccanismo però è
      ormai noto dalla base di esempio. → `docs/edt/aule.md`
- [ ] `TContrainteItalieProfReglementaire`: **unico vincolo normativo italiano**
      cablato nel motore. **Cercato in UI senza successo** (pannello vincoli
      docente + intero menu `Parametri`): probabile codice morto. Ultimo
      candidato da guardare: `Parametri → Piazzamento automatico delle attività`.
      → `docs/edt/motore-risoluzione.md`
- [ ] La **cascata di default** oltre `Al./Rid.`: il candidato **Statuto → Mh/s**
      resta non confermato. → `docs/edt/docenti.md`
- [ ] Se l'**impegno degli incarichi** docente incide sul calcolo ore.
      → `docs/edt/docenti.md`
- [ ] **TRCD**: è la resa italiana di **TRMD**, ma lo scioglimento della sigla non
      esiste in nessuna delle sei lingue del prodotto. Vista pesantemente francese
      (HSA, IMP, décret 2014-940) → candidata a **fuori scope**. → `docs/edt/classi.md`
- [ ] I quattro valori `Parties…Classe` di `TypeIncompatibiliteMatiereClasse`
      (ordine fra ore in gruppo e ore a classe intera). → `docs/edt/vincoli.md`
- [ ] **Decisione di scope**: supportare gli **sdoppiamenti** in v1?
      → `docs/edt/gruppi.md`
- [ ] **Decisione**: adottare `Partenaire_Index` V4.6 come contratto di import.
      → `docs/edt/schema-scambio.md`

## Changelog

- **2026-07-26** — **Verifica in UI sulla base di esempio del prodotto.** Copiata
  la base demo di EDT (completa e risolta: 18 aule, 187 parti, 3 raggruppamenti,
  984 attività piazzate) in `~/Desktop/EDT_COMPLETE/` e aperta in EDT per
  osservare ciò che nella base del Fermi non è osservabile. Ha **confermato**
  gran parte del lavoro sugli artefatti — le due griglie di vincoli mai viste
  esistono e i conteggi coincidono (11 tipi attività↔attività) — e ha
  **smentito due conclusioni**.
  **1) L'occupazione simultanea dell'aula non è il gruppo di aule.** È il campo
  `Numero di aule` (colonna `Qtà`), scalare e modificabile: `PALESTRE succ` ha
  `Qtà = 2` e **zero** sotto-aule. Le sotto-aule servono a nominare gli spazi, e
  portano una cascata di default (suffisso `(Gr.)`). Le stringhe descrivevano il
  caso tipico, non il modello — motivo per cui [ADR-009](docs/decisioni.md) le
  mette in fondo alla gerarchia.
  **2) La `Tipologia` dell'aula non è il "tipo d'aula".** È un tag di dotazione a
  due livelli definito dall'utente (`Attrezzature → PC docente, Videoproiettore`),
  usato solo per raggruppare la lista. **Capienza, categoria e tipologia non sono
  vincoli**: la finestra `Aule disponibili` dichiara tre soli vincoli
  (`Sedi distaccate`, `Indisponibilità opzionali`, `Indisponibilità`). Il legame
  didattica↔aula esiste ma passa dalla **classe** (`Aula preferenziale`), non
  dalla materia — la relazione materia → tipo d'aula è **nostra estensione**.
  **Confermato in UI**, con testo letterale: i tre pennelli
  (`Indisponibilità` / `Indisponibilità opzionali` / `Preferenze`); i vincoli fra
  attività **nascono opzionali** (casella spuntata di default) e l'alleggerimento
  avviene *"durante il piazzamento delle attività scartate"* — cioè la strategia
  a due passate dedotta dal motore, scritta in una finestra; `Raggruppamenti` e
  `Gruppi` come righe distinte nella composizione dell'attività, che regge
  l'inversione terminologica IT↔FR.
  **Dai dati reali** della griglia dei vincoli di materia (19 righe su `2 A/R`):
  il caso d'uso dominante è la **materia con sé stessa** (non due ore di ARTE
  nello stesso giorno), non la relazione fra materie diverse — e la relazione è
  **orientata**, `A→B` e `B→A` sono record distinti.
  **Limite aggirato:** la tabella `SALLE` è cifrata nel file, ma le 18 aule sono
  perfettamente leggibili aprendo la base in EDT.
  **L'aiuto contestuale del prodotto** (pulsante `?` del pannello dei vincoli) ha
  chiuso le ultime due colonne oscure con sette casi d'uso: `Attività in gruppo`
  = ordine fra ore in gruppo e ore a classe intera — cioè i quattro valori
  `Parties…Classe` che erano aperti dal 26 luglio mattina — e `Conc. Imp.` =
  concatenazione imposta con ritardo massimo. Spiegata anche la discrepanza fra
  le 10 colonne della griglia e i 12 tipi delle stringhe: alcuni "tipi" sono
  **valori di parametro** della stessa colonna, non vincoli distinti.
  ⚠ Nota di metodo: **l'aiuto è in inglese anche nella build italiana**, quindi
  non è una fonte per la terminologia IT.
  **Le classi di concorso ci sono, ma come dato.** Nella base di riferimento
  italiana le discipline hanno per `Codice` le classi di concorso reali (`A-01`,
  `A-22`, `A-25`, `A-28`, `A-30`, `A-49`, `A-60`, `REL`, `SOST`): non è un campo
  dedicato, ma è **il posto dove EDT Italia si aspetta che la si metta**.
  Verificato però che il prodotto **non incorpora la tabella ministeriale** — i
  codici stanno solo nei dati della demo, non nei binari né in `TabellaSIDI.xml`.
  [ADR-002](docs/decisioni.md) aggiornato di conseguenza: resta valido (relazione
  molti-a-molti in una tabella a sé), ma la nota "è nostra estensione" era troppo
  netta.
  **Il vincolo normativo italiano non si trova in UI**: battuti il pannello
  vincoli del docente (sette gruppi, tutti generici) e l'intero menu `Parametri`
  (28 voci). Probabile codice morto.

- **2026-07-26** — **Reverse engineering degli artefatti dell'installazione.**
  EDT gira sotto Wine su questa macchina: l'installazione e le basi dati sono
  leggibili come file. Da lì sono usciti quattro filoni, ora documentati, e una
  nuova convenzione di fonte (**📦**, [ADR-009](docs/decisioni.md)).
  **1) Lo schema XSD ufficiale** `Partenaire_Index` V4.6 (`docs/edt/schema-scambio.md`):
  è un formato di *input* — trasporta anagrafica, struttura e attività da piazzare,
  **nessun vincolo e nessun piazzamento**. Ha chiuso da solo tre domande aperte:
  l'**allineamento genera l'attività complessa** (dichiarato testualmente), il
  monte ore per (piano, materia) è **tripartito** (classe intera / ridotta /
  sdoppiata — l'inferenza del 2026-07-09 era corretta), e la griglia oraria è a
  due livelli (sequenza → posizione) su un **ciclo** che può eccedere la settimana.
  **2) Le tabelle di lingua** del prodotto (`docs/edt/glossario-it-fr.md`): 69 888
  stringhe italiane allineate per chiave a francese e inglese. Hanno sciolto le
  **etichette troncate dei vincoli orari**, il nome del terzo pennello
  (**`Preferenze`**), `D.T.B.` (*Durata tollerata dei buchi*), `Mh/s` (= FR
  `Apport`, il monte ore contrattuale) e le colonne dei servizi. Hanno rivelato
  un'**inversione terminologica IT↔FR** che invalidava un'ipotesi di modello:
  «gruppo» in italiano traduce `partie`, non `groupe`.
  **3) Il modello interno e il motore** (`docs/edt/motore-risoluzione.md`):
  il piazzamento è una **pipeline a 7 fasi** con ottimizzazione separata, si
  ottimizza per docenti **o** per classi mai insieme, e i vincoli sono **tutti
  hard** con rilassamento esplicito **a quota** (non penalità). Sono emersi i
  vincoli di **materia** (12 tipi) e **attività↔attività** (11 tipi), mai
  osservati. Segnalato `TContrainteItalieProfReglementaire`: unico vincolo
  normativo italiano cablato nel motore, da indagare.
  **4) Le basi dati** (`docs/edt/formato-file.md`): il `.edt` è un contenitore
  Delphi non compresso con 744 tabelle auto-descrittive. Decodificata la
  collocazione (`place = giorno × 10 + rango`, validata contro `NBCOURSPLACES`).
  Due risultati sui dati: **IRC e attività alternativa sono due parti della stessa
  classe** (`_REL`/`_ALT`), non gruppi né compresenza — la pista della guida 📖 era
  sbagliata; e **indisponibilità e assenze condividono una sola tabella**,
  distinte dalla presenza della data.
  **Anomalia trovata e da sanare:** la base del Fermi dichiara `NBSALLES = 0` —
  **le aule non sono mai state inserite in EDT**, quindi `docs/edt/aule.md` e
  `data/liceo-fermi/aule.md` sono progetto, non osservazione. Marcato nei file.
  **Limite dichiarato:** la tabella `SALLE` del `.edt` è cifrata (con sei tabelle
  di dati personali), quindi i dati delle aule restano illeggibili.
  Materiale grezzo in `docs/edt/estratti/`.

- **2026-07-26** — Messi a indice tre elementi presenti nel repo ma mai
  documentati: il **prototipo solver** CP-SAT (`scripts/genera_orario.py`,
  `results.md`, commit `0ac80ac`), gli screenshot in `preparazione/` e
  `requirements.txt`. Deciso che il **prototipo resta parcheggiato** finché il
  reverse engineering di EDT non è completo: prima tutti i vincoli, poi il modello
  ([ADR-008](docs/decisioni.md)). Corretta una voce "Aperto" stantia: le
  indisponibilità docente risultavano da osservare, ma `docs/edt/vincoli.md` le dà
  confermate in UI dal 2026-07-15; l'elenco dei vincoli ancora da osservare
  (classi, aule, risorse, materie) è ora esplicito.
- **2026-07-15** — L'utente ha fornito la **guida online ufficiale** di EDT; nuova
  convenzione "due fonti, marcate" (📖 = solo guida, da confermare in UI).
  Osservate in UI le viste 3 e 4 di Preparazione delle attività (**Assegnazione
  dei docenti ai servizi** e **Ripartizione dei docenti per classe**); dalla guida
  risolti: la **ripartizione puntuale** docente→classe avviene nella vista 3, da
  cui **"Crea le attività"** genera le attività e reindirizza a Orario (Preparazione
  non si usa più fino all'anno dopo); i **blocchi** sono la durata dell'attività;
  le **indisponibilità docente** sono rosso/giallo/verde + vincoli orari;
  **gruppi/raggruppamenti** creati automaticamente dalle attività complesse;
  `Nr. doc. suppl.` chiude il punto "docenti supplementari". La **Formazione
  classi** riguarda gli alunni nominativi → si salta senza anagrafica alunni.
  Eseguita la **ripartizione puntuale** sul Fermi (allineamenti cancellati per
  lavorare per classe, un titolare per cella, supplementari a zero): **tutti i
  18 docenti quadrano a `+/- = 0h00`** — verifica in sospeso chiusa.
  (`docs/edt/attivita.md`, `vincoli.md`, `gruppi.md`, `docenti.md`)
- **2026-07-15** — Anomalia su `Occ. prev.` (Conti/Marino a 21h, Ricci/Esposito a
  23h contro gli 8h/5h/3h attesi) risolta **reinserendo il dataset su base EDT
  vuota**: tutti i 18 valori ora coincidono con la regola documentata ("ore del
  bisogno una volta sola"). Era stato corrotto del vecchio file (plausibile residuo
  dell'inversione STO/SCI), non un errore di semantica. Lezione: dopo correzioni al
  quadro orario, cancellare e rifare l'allineamento (`docs/edt/attivita.md`).
- **2026-07-09** — Documentata la catena previsionale **piani di studi → classi
  previsionali → bisogni** (`docs/edt/piani-di-studi.md`, `classi.md`,
  `bisogni-previsionali.md`; dataset in `data/liceo-fermi/piani-di-studi.md`).
  Scoperte: il quadro orario vive sui **servizi del piano** e cascata sulle classi;
  il **bisogno** è calcolato da `ore × classi necessarie` (dagli effettivi
  previsti); il Totale dei bisogni del Fermi dà **288h00**, quadratura verificata
  da EDT.
- **2026-07-09** — Documentata la scheda **Docente** di EDT campo per campo
  (`docs/edt/docenti.md`). Due scoperte: EDT separa **capacità** (materie insegnabili),
  **preferenza** (materia preferenziale) e **assegnazione** (cattedra), e quattro campi
  (`Occ. prev.`, `HS Prev.`, `+/-`, `Extra`) sono **calcolati, non inseriti**. Nuovi
  ADR-006 (capacità ≠ assegnazione) e ADR-007 (i campi previsionali non si memorizzano).
- **2026-07-09** — Migrazione su Claude Code. Il documento di partenza
  `docs/edt/_stato-attuale.md` è stato decomposto nella struttura definitiva:
  entità in `docs/edt/`, decisioni in `docs/decisioni.md`, dataset in
  `data/liceo-fermi/`. Chiarita una distinzione: nella tabella Discipline il campo
  "Classe di concorso" è nostra mappatura, non un campo EDT osservato. Il documento
  di partenza è stato rimosso a decomposizione completata (contenuto interamente
  ridistribuito).
