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
    vincoli.md         indisponibilità, vincoli orari, di materia, attività↔attività, peso didattico
    diagnostica.md     📦 perché un'attività non si piazza: il catalogo delle causali
    tempo-e-calendario.md 📦 griglia oraria, periodi, periodicità, mensa, sedi
    risorse.md         📦 le cinque risorse di piazzamento; personale, materiali, incarichi
    moduli-e-scope.md  📦 i moduli oltre l'Orario, e cosa sta dentro o fuori
    schema-scambio.md  📦 lo schema XSD ufficiale Partenaire_Index V4.6 — modello dati formale
    nomenclatura-sidi.md 📦 tabelle ministeriali MIM incorporate in EDT (indirizzi, materie, quadri orari)
    motore-risoluzione.md 📦 come EDT risolve: pipeline, criteri, alleggerimenti
    formato-file.md    📦 il formato binario .edt, per validare la semantica sui dati reali
    glossario-it-fr.md 📦 IT ↔ FR ↔ EN — ⚠ contiene l'inversione gruppo/raggruppamento
    estratti/          materiale grezzo di estrazione (NON documentazione — vedi il suo README)
  decisioni.md         ADR leggeri: decisione, alternative, motivo, data
  scope-v1.md          cosa entra in v1 e cosa no — proposta da rivedere
  modello-dominio.md   il design del modello di dominio v1 — approvato, pre-codice
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
config/                progetto Django minimale (solo settings, niente view)
domain/                l'app Django del modello di dominio v1
  analysis/             il sottosistema di analisi: predicati con causali nominate, dominio residuo (S.P.), capienza
  solver/               lo spike CP-SAT: registro dei builder, contesto, modello, cinque vincoli
tests/                 la suite; tests/fermi.py è il dataset Fermi come fixture, più i test dell'analisi (registro, ScheduleState, i vincoli orari/di materia, dominio residuo, capienza, il comando analyze)
```

Ogni file in `docs/edt/` descrive **l'entità EDT** (campi visti nella UI, tooltip
letterale, default, semantica dedotta, implicazioni per il nostro modello). Ogni
file in `data/liceo-fermi/` contiene **i dati concreti** della scuola di esempio.

## Convenzioni

- **Cascate di default — ma poche, e dichiarate.** Dove EDT eredita un default, nel
  nostro schema `NULL` significa "eredita" e la cascata si risolve a runtime.
  ⚠ **Non è un meccanismo generale del prodotto**: i campi dimostrati sono
  `Al./Rid.` delle materie e `Mh/s` dei docenti (default **globale**, non dallo
  Statuto). Ovunque altrove si materializza. E **«eredita» ≠ «copia dal modello»**:
  le indisponibilità standard sono *copiate alla creazione*, e confonderle
  riscriverebbe le personalizzazioni di tutti. Vedi
  [ADR-003 + emendamento](docs/decisioni.md).
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
- **⚠ Il binario di EDT è condiviso con PRONOTE**, il registro elettronico gemello
  di Index Education. Delle 69 888 stringhe di interfaccia, molte migliaia
  riguardano competenze, stage, bollettini, punizioni e vita scolastica: **non sono
  funzionalità di EDT**. Ogni affermazione tratta dalle stringhe va accompagnata dal
  controllo che la famiglia di chiavi sia di EDT (`*EDT*`/`*Edt*`) o
  inequivocabilmente sul piazzamento. Vedi [moduli-e-scope.md](docs/edt/moduli-e-scope.md).

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
- **Il motore in esecuzione**: piazzamento automatico e risolutore passo-passo
  osservati mentre lavorano, con tempi e comportamento in caso di conflitto
  (`docs/edt/motore-risoluzione.md`).

> **L'osservazione di EDT è conclusa** (2026-07-26), e la decisione è stata presa
> esplicitamente con [ADR-016](docs/decisioni.md): il design del modello di
> dominio è approvato in [docs/modello-dominio.md](docs/modello-dominio.md). Lo
> schema **è implementato** e il dataset Fermi **è interamente rappresentato**; i
> predicati e l'analisi di capienza **sono anch'essi implementati**
> (`domain/analysis/`, 116 test verdi a suite completa, misurati con
> `venv/bin/pytest`); lo **spike CP-SAT è implementato** (`domain/solver/`):
> cinque vincoli su ventisette, scelti per attraversare i tre pattern di
> traduzione, e l'oracolo tiene — una soluzione del solver riletta da
> `check_schedule` non produce alcun finding `HARD` nelle famiglie modellate.
> Il passo successivo è la spec del **modello completo**: i ventidue vincoli
> restanti, gli alleggerimenti a quota, l'ottimizzazione lessicografica,
> l'assegnazione delle aule e il violatore di Hall.
> Restano due punti aperti, entrambi marginali e non bloccanti:
> le aule mai inserite nella base del Fermi, e l'estensione della cascata di
> default.

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

**Il solver resta fermo** finché il modello di dominio approvato
([docs/modello-dominio.md](docs/modello-dominio.md)) non è tradotto in codice:
prima la forma dei dati, poi il modello CP-SAT. Vedi [ADR-008](docs/decisioni.md)
e [ADR-016](docs/decisioni.md).

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

**Chiuso il 2026-07-26** dalle 69 888 stringhe di interfaccia (📦, seconda passata):

- [x] `TContrainteItalieProfReglementaire`: **non esiste alcuna interfaccia**.
      Terza ricerca indipendente, negativa: nessuna delle 69 888 etichette nomina
      l'Italia in senso normativo, e l'ultimo candidato (`Parametri → Piazzamento
      automatico`) ha due sole voci. **Non c'è un vincolo normativo italiano da
      replicare.** → `docs/edt/motore-risoluzione.md`
- [x] **TRCD/TRMD**: è la vista di **bilancio** `Dotazione − Bisogni = Scarto` su
      Globale / Ore posto / HSA / IMP, con i plafond del **decreto francese
      2014-940**. Non è orario, ed è normativa estera. → **fuori scope,
      dichiarato**. → `docs/edt/risorse.md`
- [x] **Gli incarichi incidono sul monte ore**: formula letterale
      `Ore supplementari = Durata/Coeff. + Extra − Monte ore`. Ma l'**IMP** è un
      compenso annuale (riforma francese *PACTE*), fuori dalla formula oraria.
      → `docs/edt/risorse.md`
- [x] I quattro valori `Parties…Classe`: confermati da una **seconda fonte
      indipendente**, la causale di diagnostica *"ordine delle attività in gruppo
      rispetto alle attività a classe intera non rispettato"*. → `docs/edt/diagnostica.md`

**Chiuso il 2026-07-26 (sera) — l'ultima passata su EDT:**

- [x] **Il motore visto girare.** Reinserite 27 attività (una classe intera) in un
      orario pieno: **27/27, zero scarti, ~10–15 s**; una singola attività, ~2 s.
      Quattro fasi dichiarate mentre girano, progresso parziale visibile,
      **interrompibile**. → `docs/edt/motore-risoluzione.md`
- [x] 🔑 **Il risolutore passo-passo**, osservato end-to-end. Il costo di una mossa
      è dichiarato **per nome** (le lezioni con giorno, ora, materia, docente,
      classe), le risorse in conflitto diventano rosse, e le attività scacciate
      diventano una **coda di lavoro** con cursore. Ogni passo reversibile, commit
      finale. → `docs/edt/motore-risoluzione.md`
- [x] 🔑 **`S.P.` e `Nr G.` sono la dimensione del dominio**, ricalcolata contro lo
      stato corrente e mostrata in una colonna ordinabile. Diagnostica preventiva
      **gratuita**. → `docs/edt/motore-risoluzione.md`, `docs/edt/diagnostica.md`
- [x] I **`punti`** degli alleggerimenti **non sono un punteggio**: sono punti di
      *peso didattico* (`points` → IT `pesi`). Cade l'ultimo dubbio: **in EDT non
      esiste alcuna funzione di costo numerica**. → `docs/edt/motore-risoluzione.md`
- [x] 🔑 **`Amenagement` e sostituzione sono la stessa struttura**: una riga di
      `COURS` con maschera a una settimana. Verificato sui 161 record di
      `RELATIONCOURSSUBSTITUT`. → [ADR-014](docs/decisioni.md),
      `docs/edt/formato-file.md`
- [x] **Peso didattico**: default **1** (non 0), `Totale = Peso × Durata`, quattro
      tetti d'istituto **tutti a `nessuno`**; e il totale è **per alunno**, non per
      classe. → `docs/edt/vincoli.md`
- [x] `Fractionnable`/`P.P.` = *Proprietà di Piazzamento* (fascia fissa/variabile,
      già fuori scope); `Cours isolés` = **criterio**, non vincolo; `Interclasse` =
      **intervallo**, falso amico, ma vincolo hard. → `docs/edt/vincoli.md`
- [x] L'**intervallo è un separatore**, non una `Place`; lo **spostamento fra sedi**
      è per **coppia orientata**. → `docs/edt/tempo-e-calendario.md`

**Ancora aperto:**

- [ ] ⚠ **Le aule non esistono nella base del Fermi** (`NBSALLES = 0`):
      `data/liceo-fermi/aule.md` è progetto, non osservazione. → `docs/edt/aule.md`
- [ ] Serve **una** via d'ingresso dei dati anagrafici, ora che
      `Partenaire_Index` è escluso ([ADR-012](docs/decisioni.md)): formato nostro,
      CSV, o aggancio al SaaS esistente. Da affrontare al momento dell'import.

## Scope di v1 — deciso il 2026-07-26

Le prime decisioni di prodotto, non più solo di modellazione. Dettaglio e
motivazioni in [docs/decisioni.md](docs/decisioni.md).

| | Decisione | ADR |
|---|---|---|
| ✅ | **Sdoppiamenti**, raggruppamenti trasversali **inclusi** | [ADR-013](docs/decisioni.md) |
| ✅ | **Peso didattico** delle materie | [ADR-011](docs/decisioni.md) |
| ❌ | **Collocazione per periodo** (`fascia variabile`) — si **rigenera** a ogni periodo | [ADR-010](docs/decisioni.md) |
| ❌ | **`Partenaire_Index`** come formato di import | [ADR-012](docs/decisioni.md) |
| ✅ | **Una sola entità attività** con maschera temporale: la sostituzione **non** è un'entità a parte | [ADR-014](docs/decisioni.md) |

Due conseguenze da non perdere di vista, entrambe scritte negli ADR:

- rigenerando l'orario a ogni periodo serve un criterio **«mantieni il più possibile
  le collocazioni precedenti»**, o il secondo quadrimestre verrà stravolto per tutti;
- i **raggruppamenti trasversali** accoppiano classi diverse: si perde la
  decomposizione per classe, che era la semplificazione più naturale su cui contare.

## Changelog

- **2026-08-09** — **Lo spike CP-SAT, e ADR-017 chiuso.** `domain/solver/`,
  package separato da `domain/analysis/` perché quest'ultimo resti senza
  `ortools`. Cinque vincoli tradotti, scelti per attraversare i **tre pattern
  di traduzione** dal predicato al modello CP-SAT: **pre-filtro strutturale**
  (`structural:grid`, `structural:unavailability` — le celle inammissibili non
  diventano nemmeno variabili), **cardinalità sulla risorsa**
  (`structural:occupation` come conflitto e capienza cumulativa,
  `MAX_GAP_HOURS`) e **relazione fra materie** (`SAME_DAY_INCOMPATIBLE`). I
  builder sono registrati sotto le **stesse chiavi** dei checker di
  `domain/analysis`.
  **ADR-017 chiuso.** Il problema che lo teneva aperto: un insieme di token
  non sa dire «parti della stessa partizione sono disgiunte, parti di
  partizioni diverse si sovrappongono» sulla stessa coppia di oggetti — sono
  due affermazioni opposte sulla stessa relazione. Gli **atomi** (`AtomMap` in
  `domain/analysis/state.py`), le celle del prodotto delle partizioni, la
  esprimono senza toccare l'architettura a intersezione di insiemi: aggiunti
  per tutte e tre le vie con cui una parte entra nelle chiavi (parte diretta,
  via raggruppamento, via espansione della classe intera), e **solo** per le
  classi con almeno due partizioni — altrove nulla cambia. Nessun campo nuovo,
  nessuna migrazione.
  **La correzione sul `D.T.B.`** Il vincolo era stato tradotto come soglia per
  **singolo** buco. Non lo è: il checker somma i minuti di buco su **tutte le
  mezze giornate della settimana** e confronta una volta sola — è un budget
  settimanale, dove due buchi da un'ora sforano un budget di un'ora e mezza.
  L'errore è stato intercettato in fase di design, rileggendo il checker
  invece del proprio ricordo di cosa facesse: è esattamente il tipo di svista
  che l'oracolo esiste per intercettare.
  **L'oracolo tiene.** Il criterio di riuscita è uno solo: una soluzione del
  solver, riscritta nei `Placement` e riletta da `check_schedule`, non produce
  alcun finding `HARD` nelle cinque famiglie modellate. Ha tenuto al primo
  colpo — sulla scuola giocattolo, sul Fermi ristretto a una classe e sul
  Fermi intero. E che potesse fallire è stato **verificato**: corrompendo
  deliberatamente i piazzamenti, tutte le famiglie provate hanno prodotto il
  finding atteso.
  **Le misure sul Fermi intero**: 284 attività (288h00), **tutte libere**
  (nessuna congelata dai pre-filtri strutturali), **8140 variabili**, **1082
  constraint**, `OPTIMAL` in **meno di un secondo** (~0,55s). ⚠ Come già una
  volta con `scripts/genera_orario.py`, quel risultato **non dice nulla**
  sulla risolvibilità dell'istanza reale: è la risposta a un problema con
  **cinque vincoli su ventisette**, non ai ventisette.
  **Cosa resta fuori**, esplicitamente: gli altri ventidue vincoli del
  registro, gli alleggerimenti a quota, l'ottimizzazione lessicografica,
  l'assegnazione delle aule, il violatore di Hall, un comando `manage.py
  solve`.

- **2026-07-26 (notte, analisi)** — **L'analisi dei vincoli, implementata:
  `domain/analysis/`.** Chiude il piano 2 (dodici task) sopra lo schema
  approvato: un package di predicati con causali nominate, sul modello
  dell'`Analisi dei vincoli` di EDT osservata dal vivo.
  **Il registro.** Findings e catalogo causali (`findings.py`, `causali.py`);
  `ScheduleState` che materializza una settimana (occupazione, indisponibilità,
  monte ore) **una volta sola per verifica** — i checker leggono lo stato, non
  fanno query dentro `check()` (`perf(analysis)`, commit `066efc8`); un
  registro con **copertura completa verificata da test**: gli **otto** vincoli
  orari sulla risorsa, i **tredici** di materia, e **sei** checker strutturali
  (griglia, sedi, occupazione/indisponibilità, copertura, peso). Sopra il
  registro: la conformità di una settimana contro tutti i checker in un colpo
  solo.
  **Il dominio residuo.** `S.P.`/`Nr G.` di EDT riprodotto come **piazzamento di
  prova**: quante fasce restano legali per un'attività contro lo stato
  corrente. Misurato sul Fermi: la colonna S.P. di un'intera classe (26
  attività) in **~0.3s**.
  **La capienza esatta.** L'algoritmo `Dotazione − Bisogni` di EDT, con
  **colpevoli per sottrazione** (non solo il verdetto, ma quali attività
  restano fuori e perché); le **due diagnosi osservate in EDT riprodotte sui
  numeri**: il caso semplice (`600` richiesti, `540` piazzabili) e
  l'incrociata classe+docente (`360`/`300`).
  **Il comando.** `manage.py analyze`: report in stile EDT (`Enunciato del
  problema` → `Dettaglio` → `Soluzione`) più un riepilogo finale.
  **Il Fermi, arricchito.** Aggiunte le indisponibilità attese di
  `vincoli-attesi.md` (D06/D09/D15, giornate intere), e un test che inverte
  deliberatamente STO/SCI in tre servizi: la copertura per (classe, materia)
  lo rileva anche se i **totali quadrano lo stesso** — il bug reale del
  2026-07-09 diventa un test di non regressione.
  **Le code del piano 1, chiuse.** `tests/test_constraint_negatives.py`: i sei
  test negativi rimandati (cattedra a due/zero unità, vincolo di materia a due
  unità, partizione duplicata, quota senza risorsa, `Break.straddles` con
  durata 1) confermano che i `CheckConstraint` **mordono davvero**. Corretto
  anche un refuso in `modello-dominio.md` (**12 tipi censiti** → **13**: l'enum
  implementato dei vincoli di materia ne ha 13) e annotato in `institute.py` il
  percorso di sola lettura di `domain/analysis` (`filter(pk=1).first()`, non
  `load()`, per non scrivere alla prima analisi). **116 test verdi** a suite
  completa (`venv/bin/pytest`). Prossimo passo: **il piano 3**, il modello
  CP-SAT sul registro.

- **2026-07-26 (notte, seguito)** — **Lo schema del dominio, implementato.** Per
  TDD dal design approvato in [docs/modello-dominio.md](docs/modello-dominio.md):
  progetto Django minimale `config/`, app `domain/` (modelli su istituto, risorse,
  curriculum, classi, docenti, tempo, attività, vincoli, più `domain/weeks.py`) e
  la suite in `tests/` — **39 test, tutti verdi**. `tests/fermi.py` è il dataset
  Fermi come fixture: primo test di rappresentazione, con la quadratura verificata
  sui dati reali (284 attività / 288h, 18 docenti a quadratura zero, copertura per
  ogni coppia (classe, materia)). Aggiunti anche i casi **oltre-Fermi** che il
  dataset da solo non esercita: parti IRC/ALT, raggruppamenti trasversali (2A-2B),
  sedi, sostituzione come maschera a un bit. I piani successivi: predicati e
  analisi di capienza, poi il modello CP-SAT.

- **2026-07-26 (notte)** — **Cambio di fase: da analisi a progettazione.**
  [ADR-016](docs/decisioni.md) chiude formalmente la condizione di ADR-008:
  l'osservazione di EDT è conclusa, si progetta. Scritto e approvato (sezione per
  sezione, in sessione) il **design del modello di dominio v1**
  ([docs/modello-dominio.md](docs/modello-dominio.md)). Le scelte portanti:
  modello **autonomo dal SaaS** con due entità di convergenza (attività con
  maschera temporale, disponibilità con data opzionale); le **tre condizioni di
  ADR-015 sciolte in forma** — piazzamento come entità separata con quattro
  livelli di immobilità, vincoli come righe di dato interrogabili (ogni vincolo =
  constraint CP-SAT + predicato + causale nominata), parte di classe con FK
  nullable al piano di studi (`NULL` = eredita); risorsa **generica** a sei tipi
  (le cinque di EDT + la parte) con una sola tabella di disponibilità a tre
  livelli e data opzionale, e capacità cumulativa unica per aule e materiali;
  griglia parametrica con **mezza giornata** e intervalli-separatori;
  rigenerazione per periodo tramite l'entità `schedule`; attività con la sola
  materia obbligatoria e maschera di settimane a bit; vincoli sui quattro assi con
  la relazione **orientata** e `A = B` come caso dominante; alleggerimenti **a
  quota**, modello lessicografico, niente funzione di costo. Prossimo passo: il
  piano di implementazione (schema Django + dataset Fermi come primo test di
  rappresentazione).

- **2026-07-26 (sera)** — **Il motore visto girare, e la scoperta che tocca il
  SaaS.** Ultima passata su EDT: chiusi tutti i punti aperti tranne due, e
  l'osservazione del prodotto si può considerare **conclusa**.
  **1) Il motore all'opera.** Esperimento sulla base di esempio: sospese le **27
  attività di una classe intera** da un orario per il resto pieno — l'istanza
  difficile, non quella facile — e rilanciato il calcolo. **27/27, zero scarti, in
  ~10–15 secondi**; una singola attività, ~2 s. Le **quattro fasi sono dichiarate
  mentre girano** (`Fase calcolo (n / 4)` più percentuale interna), la prima passata
  piazza circa metà e si ferma, il grosso lo fa la seconda; `Lancia il calcolo`
  diventa **`Interrompi`** e ciò che è già piazzato resta.
  **2) 🔑 EDT espone la dimensione del dominio.** Le colonne `S.P.` e `Nr G.` — che
  a orario pieno valgono quasi sempre `1` — si accendono appena si sospende
  qualcosa. Tooltip letterale: *«numero di **fasce orarie possibili** per il
  piazzamento dell'attività **nel rispetto di tutti i vincoli**»*. È il dominio
  residuo della variabile, **ricalcolato contro lo stato corrente** (sospendendo una
  lezione salgono i vicini, richiudendo il buco riscendono), messo in una colonna
  ordinabile. Sui dati: l'ora singola a 21 collocazioni, il blocco da 3h00 a 6, la
  religione in compresenza a 4, le ore `Q1`/`Q2` a 34 perché vivono in due
  quadrimestri. **Per noi è gratis** — il solver quel numero lo calcola comunque — e
  ordinando per `S.P.` crescente si ottiene *prima* del calcolo la lista di cosa sta
  per diventare impiazzabile.
  **3) 🔑 Il risolutore passo-passo, end-to-end.** Tre pannelli affiancati: la
  scheda dell'attività (con il conto di **tutte e cinque** le risorse), la griglia
  annotata astratta, e **l'orario reale del docente** accanto — la mappa delle
  decisioni vicino al contesto che le rende comprensibili. Cliccando una cella
  grigia, il costo è dichiarato **per nome**: non «3 conflitti» ma le tre lezioni con
  giorno, ora, materia, docente e classe — e fra queste la MATEMATICA di un altro
  docente, perché il conflitto passa dalla **classe**, non dal docente. Intanto **le
  risorse in conflitto diventano rosse** nel pannello di sinistra: la finestra dice
  anche *su quale* delle cinque si sta consumando. Premuto `Piazza`, le tre scacciate
  diventano una **coda di lavoro con cursore** e tutta la finestra si riconfigura
  attorno alla prima (cambia perfino l'orario mostrato a destra), con `[1° step]`,
  `Indietro` e commit finale `Conferma tutti gli step`. La scoperta non è
  l'algoritmo — quello si sapeva — ma che **è esibibile**: una ricerca a catena si
  mostra a un umano un nodo per volta, perché a ogni nodo il costo è espresso in
  entità che l'utente conosce.
  **4) 🔑🔑 `Amenagement` e sostituzione sono la stessa cosa.** Il byte a offset 8
  di `COURS` è la **natura** dell'attività: 0 = annuale (1001), 1 = **consigli di
  classe** (62, e `NBCONSEILS = 62`), 2 = **141** che è esattamente
  `NBAMENAGEMENTS`, 4 = 20. Le 141 sono le attività con **un solo bit** nella
  maschera settimane. Quindi l'`Amenagement` **non è una tabella**: è una riga di
  `COURS` con la maschera ridotta. E i 161 record di `RELATIONCOURSSUBSTITUT` lo
  confermano: i sostituti sono **esattamente** le nature 2+4, gli originali
  **161/161 annuali**, e **159/161 cambiano solo il docente** a parità di classe
  (161/161) e aula (161/161). **Sostituire un docente e spostare un'ora per una
  settimana sono lo stesso atto sul modello dati** → [ADR-014](docs/decisioni.md).
  Riguarda direttamente il **SaaS di sostituzioni già in produzione**: adottando
  questo modello i due sistemi condividono l'entità invece di scambiarsi dati.
  ⚠ Trappola evitata: le quattro tabelle `*AMENAGEMENT*` sono di **PRONOTE** (PDP/PEI)
  e tutte a zero record.
  **5) I «punti» non erano un punteggio.** Chiuso da due ricerche indipendenti e
  convergenti: sono i suffissi singolare/plurale di uno spinner, e la traduzione IT
  di `points` è **`pesi`** — punti di *peso didattico*. Cade l'ultima riserva: **in
  EDT non esiste alcuna funzione di costo numerica.** Il nostro modello dev'essere
  lessicografico.
  **6) Peso didattico, i numeri veri.** Osservato in UI: default **`1`** (non 0),
  `Totale = Peso × Durata`, e **quattro** tetti d'istituto — mattino, pomeriggio,
  giornata, settimana — **tutti a `nessuno`**. ⚠ Cioè in una base completa, risolta
  e messa a punto a mano, la funzione **è spenta**: ridimensiona
  [ADR-011](docs/decisioni.md), che l'ha messa in v1. 🔑 E un dettaglio non cercato:
  il totale di classe (33) è **1 in meno** della somma delle materie (34), e la
  differenza è `ALTERNATIVA` — **il peso si misura per alunno, non per classe**, il
  che conferma sui dati il modello `_REL`/`_ALT` di `gruppi.md`.
  **7) Tre colonne che sembravano vincoli e non lo erano.** `P.P.` = *Proprietà di
  Piazzamento* (⚠ e `P.F.` non è una seconda colonna: è la stessa in inglese) =
  fascia fissa/variabile, già fuori scope; `Cours isolés` = **criterio di
  ottimizzazione**, con definizione operativa esatta e prova negativa solida (non
  compare in nessuna causale di diagnostica); `Interclasse` = **falso amico**,
  significa *intervallo*, ed è un vincolo hard a tre entità. Chiusi anche:
  l'**intervallo è un separatore, non una `Place`** (prova: i ranghi 2 e 4 sono fra
  i più occupati), lo **spostamento fra sedi è per coppia orientata**, e `Aree
  mobile` è il portale mobile di PRONOTE.
  **⛔ Una traduzione italiana dice il contrario.** `Memorizza le attività che
  saranno spostate` in francese è `Réinitialiser la famille des cours déplacés`.
  Avevo documentato la casella come opzione di tracciabilità: **sbagliato**,
  corretto. Nuova regola operativa: **quando IT e FR divergono, vince il francese**.
  → `docs/edt/glossario-it-fr.md`

- **2026-07-26** — **Il motore, il tempo e le risorse mancanti.** Fino a qui
  avevamo documentato bene **cosa EDT sa rappresentare** (dati e vincoli) e quasi
  nulla di **cosa EDT sa fare**. Questa passata colma il buco, rileggendo le 69 888
  stringhe di interfaccia per finestra invece che per parola chiave. Quattro
  documenti nuovi e una riscrittura.
  **1) Il motore visto dall'utente** (`motore-risoluzione.md`, riscritto). La
  generazione non è un bottone: il menu `Elabora` ha **cinque comandi di
  risoluzione**, usati in sequenza. Fra questi due mai immaginati: il **risolutore
  passo-passo**, che è una **ricerca a catena di espulsioni** (*"Trova una soluzione
  al massimo in %d step"*) con la griglia annotata slot per slot — *"in bianco, le
  collocazioni senza attività che creano problemi; in grigio, quelle che comportano
  lo spostamento di almeno un'altra attività"*, più il costo in vincoli e
  spostamenti; e **`Piazza e sistema`**, che impone una collocazione occupata e
  ripara il resto, con l'opzione *"Ignora i vincoli dell'attività selezionata"*.
  Trovata anche la **funzione obiettivo esposta**: i `Criteri di calcolo` sono una
  lista che l'utente sposta fra *considerati* e *ignorati*, e i massimi orari hanno
  **quattro modalità** (per settimana / per ciclo / media su 2 settimane con scarto
  massimo / media su 2 cicli). L'ottimizzazione ha **tre criteri ordinati** più una
  **`perdita di qualità tollerata`** per l'altra popolazione: il compromesso è
  sempre una **quota**, mai un peso. ⚠ Due correzioni al «tutto hard di default»:
  `Durata se possibile`, `Frequenza se possibile` e `Periodi se possibile` sono
  degradabilità dichiarate **sull'attività**.
  **2) La diagnostica** (`diagnostica.md`, nuovo). ~170 causali **nominate**: non
  «infeasible», ma *"La classe è già occupata in un'attività bloccata"*. Il perno è
  la distinzione **occupata-spostabile / occupata-bloccata**, che è ciò che rende
  possibile il risolutore a catena. Scoperto un attributo mai visto: le attività
  hanno una **priorità** (`Rendi prioritarie le attività`), distinta dal blocco.
  **Poi verificato in UI, e ha smentito una conclusione:** EDT **sì** che
  diagnostica e suggerisce, nell'`Analisi dei vincoli` (vedi sotto).
  **3) Il modello del tempo** (`tempo-e-calendario.md`, nuovo). Lo XSD conferma
  formalmente `place = giorno × 10 + rango`
  (`NombreJoursParCycle × NombreSequencesParJour × NombrePlacesParSequence`). Ma la
  scoperta strutturale è **`Fascia fissa` vs `Fascia variabile`**: *"EDT può
  modificare la collocazione dell'attività a seconda dei periodi"* — cioè una
  lezione non ha *una* collocazione, ne ha **una per periodo**. Inoltre gli
  **`Amenagement`** (eccezioni su una singola settimana) sono un **layer separato**
  sovrapposto all'orario annuale, e non sono un caso limite: 141 su 984 attività
  nella base demo. ⚠ Le settimane «A/B» **non esistono col quel nome**: il prodotto
  usa `Q1`/`Q2`, e trimestri e quadrimestri sono codificati con lo stesso
  meccanismo numeratore/denominatore.
  **4) Le risorse** (`risorse.md`, nuovo). La verifica di coerenza pre-piazzamento
  elenca **cinque risorse sullo stesso piano**: classi, docenti, aule, **personale**,
  **materiali** — le ultime due mai documentate. Il materiale ha una **quantità che
  è un vincolo hard** (*"%d quantità di questo materiale sono utilizzate
  simultaneamente"*), cioè lo stesso meccanismo della capacità simultanea dell'aula:
  **una risorsa cumulativa sola**, non due tabelle.
  **5) I moduli** (`moduli-e-scope.md`, nuovo). Delimitato il confine EDT ↔ PRONOTE
  (nuova convenzione, sopra). Le **sostituzioni non hanno un solver**: filtro
  multi-criterio + workflow, assegnazione manuale — quindi non c'è tecnologia da
  recuperare per il SaaS del committente, solo criteri (due buoni: «chi ha già un
  buco lì», «chi è stato liberato da un'assenza di classe»). Colloqui e consigli
  invece hanno un motore vero, e i consigli usano **lo stesso schema a tre stadi**
  dell'orario: è un **pattern architetturale del prodotto**, non una scelta
  specifica. E `Estrai` non è un filtro di vista ma una **selezione persistente e
  componibile** su cui piazzamento e ottimizzazione operano *esclusivamente*.
  **Un vincolo mai censito:** il **peso didattico** delle materie, con tetti per
  mattina/pomeriggio/giornata/settimana/ciclo, diagnostica e alleggerimento propri
  (`vincoli.md`). È il vincolo di carico cognitivo — facile da implementare, alto
  valore percepito, e nessuno lo fa.
  **Quattro punti aperti chiusi:** il vincolo normativo italiano **non esiste**
  (terza ricerca, negativa: nessuna delle 69 888 etichette nomina l'Italia in senso
  normativo); **TRCD/TRMD** è contabilità di bilancio su decreti francesi → fuori
  scope; gli **incarichi incidono** sul monte ore, con formula letterale, ma l'IMP
  no; i quattro valori **`Parties…Classe`** confermati da una seconda fonte.
  **Verificato subito in UI:** il **solver funziona anche senza registrazione** —
  tutte le voci di `Elabora` sono attive (la clausola francese di primo avvio non si
  applica a questa build). E il menu ha una **quarta sezione mai prevista**,
  `Analisi → Lancia l'analisi dei vincoli`: si analizza *prima* di calcolare.
  Le quattro sezioni sono **analizza → piazza → risolvi gli scarti → ottimizza**.
  🔑 **L'analisi dei vincoli è la funzione più preziosa trovata finora**, e ha
  **smentito** la conclusione «EDT non suggerisce quale vincolo allentare»: quella
  vale per il pannello `Alleggerimenti`, non per l'analisi. Cinque fasi
  selezionabili, di cui la quinta è `Controllo dell'insieme di attività non
  piazzabili` — la ricerca di **sottoinsiemi infattibili**, cioè un violatore di
  Hall, non il caso banale della singola attività bloccata. E una diagnosi reale
  osservata è strutturata in quattro riquadri: `Enunciato del problema` in italiano
  corrente, `Azioni che permettono di risolvere il problema`, `Dettaglio` con
  **l'aritmetica esplicita** (*"Classe 1B, LETTERE, 6 attività, durata da piazzare
  10h00, durata piazzabile 9h00 » 1h00 non potrà essere piazzata"*) e `Soluzione`
  con **la riga di vincolo colpevole mostrata in loco** (LETTERE incompatibile con
  sé stessa nella giornata). Più il pulsante `Estrai le materie, le risorse
  coinvolte e le attività`, che riversa la diagnosi nella selezione di lavoro.
  Osservate **tre forme di diagnosi** di natura crescente: un vincolo su una
  risorsa; **vincoli incrociati** di classe *e* docente, dove il riquadro
  `Soluzione` mostra affiancati due vincoli di famiglie diverse (incompatibilità
  di materia **e** giornate libere del docente) che sono innocui separatamente e
  fatali insieme; e infine la fase 5, che ha trovato un **violatore di Hall** vero —
  *11 docenti + 1 classe + 1 aula* nominati insieme, 25 attività, 33h di domanda
  contro 32h di *finestra di disponibilità comune*. Il riquadro `Soluzione` è
  **operativo**: tendine e griglia delle indisponibilità modificabili sul posto,
  poi `Rilancia la verifica` — si diagnostica e si ripara senza cambiare finestra.
  È la differenza fra `INFEASIBLE` e un prodotto: **da progettare come componente a
  sé**, perché è un conteggio di capienza, non richiede il solver.
  🔑 **E l'analisi è esatta, verificato.** Una base con 984/984 attività piazzate
  dichiarava comunque incoerenze; `Estrai → Attività che non rispettano i vincoli`
  ha restituito **21 attività su 984 (38h00)**, fra cui **entrambe** le diagnosi
  (EPICURO/LETTERE su 1B, DI MILETO/MATEMATICA su 1E). Quindi l'orario contiene
  davvero lezioni illegali piazzate a mano: **un orario valido non è un invariante**
  in EDT, la violazione è uno stato ammesso e interrogabile. Scelta di progetto da
  imitare. Quel comando apre prima una finestra `Criteri di estrazione` con le
  **dieci famiglie violabili** (dove ci sono `Mensa` e `Intervallo` — conferma che
  sono hard — ma ⚠ **mancano `Massimo di ore` e `Peso didattico`**, da chiarire).
  ⚠ Debolezza annotata: la chiusura (`Verifica terminata / Rimangono delle
  incoerenze`) **non riepiloga nulla** — chi ha scorso dieci problemi non può
  rivederli. → `docs/edt/diagnostica.md`, `docs/edt/vincoli.md`

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
