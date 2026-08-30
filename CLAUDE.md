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
CLAUDE.md              questo file — stato, convenzioni, indice
AGENTS.md              symlink a CLAUDE.md (non divergono per costruzione)
docs/
  changelog.md         📌 il racconto datato, con le misure — si legge, non si carica
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
    tempo-e-calendario.md griglia oraria (👁), periodi, periodicità, mensa (👁), sedi
    risorse.md         📦 le cinque risorse di piazzamento; personale, materiali, incarichi
    moduli-e-scope.md  📦 i moduli oltre l'Orario, e cosa sta dentro o fuori
    schema-scambio.md  📦 lo schema XSD ufficiale Partenaire_Index V4.6 — modello dati formale
    nomenclatura-sidi.md 📦 tabelle ministeriali MIM incorporate in EDT (indirizzi, materie, quadri orari)
    motore-risoluzione.md 📦 come EDT risolve: pipeline, criteri, alleggerimenti
    formato-file.md    📦 il formato binario .edt, per validare la semantica sui dati reali
    glossario-it-fr.md 📦 IT ↔ FR ↔ EN — ⚠ contiene l'inversione gruppo/raggruppamento
    estratti/          materiale grezzo di estrazione (NON documentazione — vedi il suo README)
  todo.md              📌 **l'unico elenco di cose da fare** — decisioni, osservazioni, debiti
  decisioni.md         ADR leggeri: decisione, alternative, motivo, data
  scope-v1.md          cosa entra in v1 e cosa no — proposta da rivedere
  criteri-di-piazzamento.md  il materiale per decidere O5: i dieci criteri non
                       tradotti, uno per uno, con la raccomandazione — ⚠ è un
                       giudizio nostro, non documentazione di EDT
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
  analysis/             il sottosistema di analisi: predicati con causali nominate, dominio residuo (S.P.), capienza,
                        la copertura misurata **per alunno** (ADR-020:
                        l'unità è l'atomo, non la parte), il **picco del gruppo
                        di aule** (ADR-021, room_pool.py: Hall su un insieme, non
                        un totale — le aule che la fase 1 conta senza assegnarle),
                        il violatore di Hall (fase 5, hall.py), lo scarto come
                        stato nominato (checkers/placement.py), la richiesta
                        d'aula insoddisfatta (checkers/room_assignment.py) e la
                        **classifica dei vincoli** per fallimenti causati
                        (blame.py)
  solver/               il modello CP-SAT: vocabolario di variabili derivate,
                        residuo di ADR-018, ventisette builder su trenta checker,
                        la catena lessicografica (objective.py), le quote
                        di alleggerimento (relaxation.py), i criteri di
                        qualità (quality.py + criteria.py), la separazione
                        per popolazione con la perdita tollerata (Arbitrato),
                        `Piazza e sistema` (place_and_fix.py) e la **seconda
                        fase** — l'assegnazione delle aule (rooms.py), modello
                        a sé con tre livelli propri: i minuti senza aula, i
                        cambi rispetto alla ripartizione precedente e
                        l'eccedenza di capienza (L2, un criterio non un
                        vincolo)
  ical.py               l'export iCalendar: l'orario nel telefono — l'unico
                        pezzo che *consegna* invece di calcolare, e il punto in
                        cui la fascia di calcolo smette di essere l'ora
  extraction.py         `Estrai`: la selezione di lavoro come operazione —
                        criteri, i sei rilevatori di problemi, le quattro
                        operazioni insiemistiche, e il perimetro che restringe
                        l'azione mai il conteggio
tests/                 la suite; tests/fermi.py è il dataset Fermi come fixture, più i test dell'analisi (registro, ScheduleState, i vincoli orari/di materia, dominio residuo, capienza, il violatore di Hall e le famiglie non monotone che lo rilassano, l'indipendenza dall'ordine d'inserimento, la classifica dei vincoli da allentare, il comando analyze), i test di `Estrai` (appartenenza, rilevatori, composizione, il perimetro su blame/Hall/aule, i comandi extract e analyze --estrazione) i test della **classe articolata** (condizione 3 di ADR-015: il piano proprio della parte, e il parallelismo che compra) e della **copertura per alunno** (ADR-020: l'unità è l'atomo, l'alternativa è un dato, il piano ambiguo si nomina), e i test del solver (registro dei builder e sua completezza, contesto, il modello, i ventisette builder uno per uno, il banco a testimone con il modello completo, l'oracolo differenziale, la catena lessicografica, le quote e lo scarto, i criteri di qualità, la separazione per popolazione, il comando solve, e per la seconda fase il contesto, il modello, la catena, il banco a testimone delle aule con il suo oracolo e il comando assign_rooms)
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
- **Le cose da fare stanno in [docs/todo.md](docs/todo.md), e solo lì.** Quando
  una voce si apre o si chiude si aggiorna quel file; il *racconto* di come è
  stata chiusa va in [docs/changelog.md](docs/changelog.md), alla data. Due
  elenchi paralleli divergono sempre, ed è come questo file si era riempito di
  voci stantie.
- **⚠ Questo file porta lo stato, non la storia.** È caricato in ogni sessione,
  quindi ogni riga si paga sempre: una voce nuova va nel changelog, e qui si
  *sostituisce* la riga che è diventata falsa. Se una sessione allunga
  `CLAUDE.md` invece di riscriverne un pezzo, quasi sempre sta scrivendo nel
  file sbagliato.
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

> **L'osservazione di EDT è conclusa** (2026-07-26 — con la sola O2 riaperta e
> chiusa il 2026-08-29, la griglia oraria), e la decisione è stata presa
> esplicitamente con [ADR-016](docs/decisioni.md): il design del modello di
> dominio è approvato in [docs/modello-dominio.md](docs/modello-dominio.md). Lo
> schema **è implementato** e il dataset Fermi **è interamente rappresentato**; i
> predicati e l'analisi di capienza **sono anch'essi implementati**
> (`domain/analysis/`); e il **modello CP-SAT hard è completo**
> (`domain/solver/`): **ventisette builder su trenta checker**, e i tre senza
> builder non ne hanno uno per costruzione — `structural:coverage`
> (`PLACEMENT_INDEPENDENT`: il solver non crea né distrugge attività),
> `structural:placement` (lo scarto *è* il meccanismo del modello, non un
> vincolo da postare) e `structural:room_assignment` (vive nel modello della
> **seconda fase**). Il **violatore di Hall** (fase 5 dell'Analisi dei
> vincoli, `domain/analysis/hall.py`) **è anch'esso implementato**: nessun
> solver, teorema di Hall in forma deficitaria su flusso massimo e taglio
> minimo. **814 test verdi**, 17 skip tutti misurati e attribuiti
> (`venv/bin/pytest`).
>
> ⚠ **Il Fermi non misura il modello completo: misura il dataset.** Ha zero
> righe `ResourceTimeConstraint`, zero `SubjectConstraint` e i tetti di peso a
> `None` — e prima delle aule dava gli stessi 8140 variabili e 1082 constraint
> dello spike a cinque vincoli, `OPTIMAL` in ~0,56 s.
>
> 🔑 **E sono tre builder su ventisette, non sei famiglie**: qui era scritto
> «griglia, indisponibilità, occupazione, sedi, D.T.B. e `room_pool`», ed era un
> elenco, non una misura. Avvolgendo `restrict` e `build` di ogni builder
> durante `build_model` (2026-08-30): `structural:occupation` posta **948**
> constraint, `structural:room_pool` **420**, `structural:unavailability` toglie
> **360** celle, e **gli altri ventiquattro non fanno nulla**. Tre dei sei
> elencati non reggono: `site_transition` non ha `Site`, `max_gap_hours` legge
> righe che non esistono, `structural:grid` è un no-op senza festività né
> intervalli. È la misura che apre **L4**. La misura del modello resta
> `test_modello_completo`, che attiva tutte le famiglie **insieme** sullo stesso
> testimone: 22–23 famiglie con righe su 26, 48–73 righe, `OPTIMAL` su tutti e
> cinque i seed, oracolo pulito.
>
> Dal 2026-08-26 il **pezzo 3 è completo** — alleggerimenti a quota e
> ottimizzazione lessicografica
> ([spec](docs/superpowers/specs/2026-08-26-alleggerimenti-lessicografico-design.md),
> [piano](docs/superpowers/plans/2026-08-26-alleggerimenti-lessicografico.md)),
> sette ondate su sette. Il modello **ha smesso di pretendere il piazzamento**:
> `AddExactlyOne` è diventato `somma(celle) == piazzata`, l'attività che non ci
> sta resta **scartata** e un checker la nomina (`structural:placement`,
> ventottesimo del registro). Sopra c'è la **catena lessicografica**
> (`domain/solver/objective.py`) a quattro livelli — ore scartate, numero di
> attività, violazioni nuove, spostamenti rispetto all'orario precedente — con
> fissaggio fra un livello e l'altro, limite di tempo **per livello** e il
> suggerimento che passa la soluzione al livello successivo. Le **quote**
> (`domain/solver/relaxation.py`) coprono tutte le famiglie che EDT dichiara
> alleggeribili, nelle due forme *margine* e *deroga*, con i tetti per
> (famiglia, risorsa) e per risorsa. E c'è **`manage.py solve`**.
>
> Con L3 si chiude anche il debito del «ramo pigro» di §9.7, e la prova è una
> misura: su 60 semi del banco che congela il fenomeno non compare più, quindi
> l'esenzione che lo perdonava è stata **rimossa**.
>
> Fermi: `OPTIMAL`, zero scarti, 8426 variabili e 1086 constraint, 1,2 s dal
> comando.
>
> Dal 2026-08-27 i **criteri di qualità** sono anch'essi implementati
> (`domain/solver/quality.py`, `criteria.py`,
> [spec](docs/superpowers/specs/2026-08-27-criteri-di-qualita-design.md)): i
> quattro valori di `Ottimizzazione degli orari` — buchi, attività isolate,
> mezze giornate libere, equilibrio didattico — più il pennello **verde**, come
> livelli in coda alla catena, con l'**ordine dichiarato dai dati**
> (`QualityCriterion`) e non dal codice.
>
> ⚠ **E costano — ma non per la ragione che era scritta qui.** Fino al
> 2026-08-28 questa nota diceva «senza limite di tempo non tornano in nove
> minuti, con `--limite 15` chiudono in 39,5 s lasciando due livelli su sei con
> l'ottimo non dimostrato», e la misura era a **un lavoratore**, che non è come
> il comando gira. 🔑 Il fenomeno vero: un livello di qualità non è lento
> perché difficile da ottimizzare, è lento perché **impossibile da
> dimostrare** — `gaps` chiude in un secondo perché zero è anche il suo limite
> inferiore banale, `free_half_days` si ferma a 202 con limite **6** e
> `regularity` a 236 con **18**. Da qui `BUDGET_QUALITA` (15 s): senza,
> `manage.py solve` non tornava, e un budget globale avrebbe punito proprio i
> livelli che l'ottimo lo dimostrano. E il rendiconto porta ora il **divario**,
> che distingue `isolated 0` (è l'ottimo, non dimostrato) da `regularity 236`
> (non sotto 18).
>
> ⚠ **E il budget appartiene alla posizione, non alla famiglia** — corretto il
> 2026-08-30 dopo che `solve --popolazione` è stato ucciso a dodici minuti
> sul Fermi. Qui c'era scritto «il budget dei **soli** livelli di qualità», ed
> era la generalizzazione sbagliata: la stabilità dimostra l'ottimo finché sta
> in testa (conserva tutto e arriva a zero), lo perde quando l'arbitrato la
> manda in coda sotto i criteri, e lì `Level("spostamenti", …)` la costruiva
> senza limite. Ora in coda prende `BUDGET_QUALITA`, e il comando torna in
> **49 s** — con `gaps_teachers` da 1260 a **0** e `isolated_all` da 50 a **5**,
> al prezzo di 169 spostamenti su 284.
>
> ⚠ **Il Fermi non ha righe `QualityCriterion`**: dalla riga di comando la
> qualità non è esercitata da quel dataset, e il difetto qui sopra è emerso
> solo seminandone cinque a mano.
>
> Dal 2026-08-27 (sera) c'è anche la **separazione per popolazione**
> (`Arbitrato` in `domain/solver/quality.py`,
> [spec](docs/superpowers/specs/2026-08-27-separazione-popolazione-design.md)):
> EDT ottimizza docenti *oppure* classi, mai insieme, e dichiara **quanto è
> disposto a peggiorare l'altra**. I criteri della popolazione sacrificata
> smettono di essere livelli e diventano **tetti di non-regressione**
> (`valore <= base + tolleranza`), dove la base è il valore che quel criterio
> ha sull'orario di partenza — calcolato con la **stessa funzione** del
> livello, su un modello usa-e-getta con i letterali di cella sostituiti da
> costanti. `manage.py solve --popolazione teachers --tolleranza N`.
>
> ⚠ **E il pezzo ha trovato che i criteri di qualità erano inerti su ogni
> orario già scritto.** L4 (la stabilità) precedeva la qualità, raggiungeva
> zero conservando tutto e inchiodava ogni cella. Non si vedeva perché il
> Fermi non ha piazzamenti di suo. Con l'arbitrato la stabilità scivola in
> coda e diventa lo spareggio; senza, resta prima (ADR-010). Misura sul Fermi:
> catena unica `gaps_teachers 420` in 0,06 s — cioè l'orario di prima,
> misurato e non migliorato; con l'arbitrato **0**, al prezzo di 231 attività
> spostate su 284.
>
> Dal 2026-08-28 anche l'ultimo pezzo dichiarato fuori — **l'assegnazione delle
> aule** — è implementato (`domain/solver/rooms.py`,
> [spec](docs/superpowers/specs/2026-08-27-assegnazione-aule-design.md),
> [piano](docs/superpowers/plans/2026-08-27-assegnazione-aule.md)). È una
> **seconda fase**, non un pezzo del piazzamento, ed è la forma del prodotto:
> in EDT l'assegnazione ha criteri propri, un ottimizzatore dedicato e una
> `ripartizione delle aule` distinta dal calcolo. I vincoli veri sono tre più
> la capienza — la finestra `Aule disponibili` dichiara `Sedi distaccate`,
> `Indisponibilità opzionali`, `Indisponibilità` e nient'altro: **capienza in
> alunni, categoria e tipologie non vincolano**. Due livelli propri (minuti
> senza aula, poi i cambi rispetto alla ripartizione precedente), la
> **rinuncia** ammessa come lo scarto, e `manage.py assign_rooms`.
>
> 🔑 **E dal 2026-08-29 la fase 1 le aule le conta** (`structural:room_pool`,
> [ADR-021](docs/decisioni.md)) — trentesimo checker, ventisettesimo builder.
> Fino a quel giorno il piazzamento era cieco alle aule con più di una
> candidata e la fase 2 rinunciava: **84 assegnate su 92**. Era scritto qui
> come «la conseguenza dichiarata di assegnare le aule *dopo*», e la parola
> falsa era *dopo*: assegnarle dopo non obbliga a **contarle** dopo, ed EDT
> infatti le conta mentre piazza (la causale del *picco d'occupazione del
> gruppo di aule* sta in `AffSco_UtilDiagnostic`, la diagnostica del
> piazzamento; il pannello dell'attività conta `Aule` fra le cinque risorse).
> Il vincolo è **Hall, non un totale** — su nessuna delle 26 celle contese
> l'unione delle candidate era in deficit, e le rinunce c'erano lo stesso — e
> il deficit misurato era *esattamente* il numero di rinunce: 8, tutte su
> `{LAB-FIS, LAB-INF}`. Ora: **92 su 92, zero rinunce**, zero scarti in fase 1,
> 1116 → 1536 constraint e 1,07 → 1,27 s. Contare non è assegnare: l'aula la
> sceglie ancora la seconda fase.
>
> Dal 2026-08-28 c'è anche la **classifica dei vincoli per fallimenti
> causati** (`domain/analysis/blame.py`, in `manage.py analyze`): la seconda
> delle «due lacune di EDT» di `scope-v1.md`, il ponte fra «il calcolo è
> fallito» e «quale vincolo allento». Ordina le coppie **(causale, risorsa)**
> per quante attività tornerebbero piazzabili allentandole — non per quante
> celle escludono, che è pressione e non azione. ⚠ Le famiglie **non
> monotone** ne restano fuori, il D.T.B. compreso: il criterio del dominio
> residuo su di loro è falso, e contarle le metterebbe in cima a qualunque
> classifica per un artefatto. La rinuncia la dichiara il comando.
>
> Dallo stesso giorno c'è **`Piazza e sistema`** (`domain/solver/place_and_fix.py`,
> `manage.py place_and_fix`): imporre una collocazione e lasciare che l'orario
> si ricomponga. Con esso è sciolta la **condizione 1** delle tre di ADR-015 —
> *«qual è l'insieme minimo di attività da spostare perché A stia qui?»* — che
> è ciò che tiene riapribile l'esclusione del risolutore passo-passo. Sul
> Fermi pieno: **una** attività spostata su 284, in ~4 s. ⚠ Resta fuori,
> dichiarata, la casella «Ignora i vincoli dell'attività selezionata»: da noi
> non è separabile per attività.
>
> Dal 2026-08-28 (sera) **`Estrai` è un'operazione** (`domain/extraction.py`,
> `manage.py extract`): la tabella c'era dal giorno dello schema e il solver la
> onorava già, ma **niente la popolava** e le due fasi diagnostiche la
> ignoravano. Ora ci sono i criteri (stato, risorsa, materia, finestra oraria),
> i **sei rilevatori** che il nostro modello sa davvero rispondere, le quattro
> operazioni insiemistiche del menu di EDT — `Limita la ricerca alle attività
> già estratte` compresa — e il perimetro su `analyze`, `assign_rooms` e
> `solve`. 🔑 La regola: **un'estrazione restringe ciò su cui si agisce, mai
> ciò che si conta.** Fermi, `--estrazione biennio`: 104 attività libere su
> 284, **3243 variabili contro 8426**, e 32 richieste d'aula contro 92.
>
> Dal 2026-08-28 (notte) c'è l'**export iCal** (`domain/ical.py`,
> `manage.py export_ical`), la sola voce ✅ di `scope-v1.md` che non riguarda il
> calcolo: tutto il resto produce un orario, questo lo **consegna**.
> 🔑 Ed è il punto in cui la **fascia di calcolo smette di essere l'ora**:
> `SlotLabel` (📦, il `Place` dello XSD con `@LibelleHeureDebut` /
> `@LibelleHeureFin`) porta l'orologio, e `slot_minutes` non compare nel file.
> Un'attività non è sempre **un** evento — dove l'orologio salta, il blocco si
> spezza in corse contigue. Fermi: 9372 eventi, 1,8 MiB, 0,6 s; un docente 693.
>
> Restano i punti aperti elencati sotto.

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

Questo script **resta parcheggiato ed è superato**: il codice vivo del solver
è `domain/solver/` (vedi la nota di stato sopra), che ne riprende l'idea sullo
schema del dominio approvato invece che sui dati grezzi. Il **modello hard è
ora completo** — ventisette builder su trenta checker. Ciò che manca non è
più la traduzione dei vincoli, ma i due pezzi dichiarati fuori dal piano: gli
alleggerimenti a quota con l'ottimizzazione lessicografica e l'assegnazione
delle aule (il violatore di Hall è implementato, vedi la nota di stato sopra
e [docs/changelog.md](docs/changelog.md)). Vedi [ADR-008](docs/decisioni.md) e [ADR-016](docs/decisioni.md).

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
      👁 **Confermato in UI il 2026-08-29** insieme al resto di O2: la pausa di
      mezza giornata **è** invece una fascia (6+1+3 = 10), la `Durata reale delle
      fasce orarie` è un campo diverso dalla durata di calcolo, e la demo è
      `5 × 10 × 1` a 60 min — il che chiude per osservazione `place = giorno × 10
      + rango`.

**Ancora aperto:** → **[docs/todo.md](docs/todo.md)**, che è l'unico elenco.
Tre decisioni, **una sola osservazione sostanziale** ancora aperta in EDT (il
`Ciclo personalizzato`) più due minuzie da tooltip, due esperimenti e nove
debiti dichiarati. **Nessuna blocca il calcolo**: ⛔ D1 è sciolta il 2026-08-28
con [ADR-020](docs/decisioni.md), ⛔ D3 il 2026-08-29 con
[ADR-021](docs/decisioni.md), e O1 — i criteri dell'ottimizzatore aule — il
2026-08-30.

🔧 La sezione **`Lavoro`** del todo ha aperto e chiuso tre voci il 2026-08-30,
e ne ha aperta una quarta — **L4**, il dataset «Alighieri»: il Fermi esercita
**tre builder su ventisette** e ne lascia **tredici tabelle su trentatré vuote**,
`ClassPartition`/`ClassPart`/`Group` comprese, cioè le voci ✅ di scope v1 che
nessun dataset rappresenta.
[Spec](docs/superpowers/specs/2026-08-30-alighieri-banco-a-scuola-intera-design.md),
da approvare. 🔑 **Accanto al Fermi, non al posto suo**: il Fermi vale perché
non è stato progettato per superare i nostri test. **L1**:
il perimetro su cui si misura il buco è ora un parametro d'istituto, separato
per classi e docenti, letto insieme dal checker, dal builder del D.T.B. e dal
criterio `gaps` — 🔑 la casella di EDT e lo spezzare alla linea sono **la stessa
cosa**, e la differenza fra i due perimetri è esattamente la corsa libera
attorno alla linea (misurata). Default allo status quo: la scelta cambia la
quantità di un vincolo hard, quindi è della scuola. **L2**: la capienza in
alunni è il **terzo livello** della catena delle aule (`eccedenza_capienza`) —
criterio e non vincolo, come in EDT — e c'è il **lucchetto sull'aula**
(`Placement.room_locked`), distinto dall'immobilità della collocazione. **L3**:
[docs/criteri-di-piazzamento.md](docs/criteri-di-piazzamento.md), i dieci
criteri uno per uno; esito **sette no e tre forse**, perché `Ordinamento dei
criteri` governa un'euristica di ricerca che in CP-SAT non esiste. ⚠ Ha trovato
un debito: i criteri di qualità **ignorano le firme di settimana**.

Quello che segue è la **storia delle voci chiuse**, con il perché: si legge, non
si aggiorna.

- [x] **Come si comporta un builder quando un constraint mescola attività
      congelate già in violazione e attività libere?** Deciso con
      [ADR-018](docs/decisioni.md): **capacità residua** clampata sui soli
      letterali liberi, e **oracolo differenziale** (nessun finding `HARD`
      *nuovo*, invece di nessun finding `HARD`). Un orario illegale è uno
      stato ammesso — è il comportamento di EDT, che con 21 attività in
      violazione piazzate a mano continua a lavorare. **Da implementare** nella
      spec del modello completo, prima dei ventidue builder restanti.
- [x] ⚠ ~~**Cosa significa «cambio di sede» quando due sedi coesistono nella
      stessa fascia?**~~ **Deciso il 2026-08-28: dentro una fascia non si
      viaggia.** Una fascia contribuisce l'**insieme** delle sedi che la
      occupano, e un cambio è una transizione fra due fasce consecutive i cui
      insiemi differiscono — sedi diverse simultanee valgono **zero** cambi.
      È la seconda delle due strade che il builder elencava, nella forma più
      netta. L'argomento: essere in due posti insieme è *impossibile*
      (`structural:site_transition` lo dice, e resta una violazione) ma non è
      un **viaggio**; le due domande sono diverse e meritano risposte diverse.
      A capienza 1 la nuova regola coincide riga per riga con la vecchia.
      → [ADR-019](docs/decisioni.md), `MaxSiteChangesChecker`,
      `domain/analysis/state.site_occupation`.
- [ ] ⚠ **Il tie-break di `_placed_of` è un artefatto dell'ordine
      d'inserimento, non una semantica** — la stessa forma del problema qui
      sopra su `MaxSiteChangesChecker`. **Chiuso il 2026-08-28** (vedi in coda
      alla voce). `_placed_of` (in
      `domain/analysis/checkers/subject_constraints.py`) ordina le occorrenze
      piazzate per `(day, start_slot)` con `sorted` **stabile**: a parità di
      collocazione, quale attività diventi `a[0]` dipende dall'ordine del
      queryset `Activity`, non da niente di dichiarato nel modello. Per
      `WEEKLY_ORDER`, `Finding.key` include l'**identità** delle due attività
      argmin (non la loro posizione): due occorrenze della stessa materia su
      parti diverse della stessa partizione (sdoppiamento) possono
      condividere la stessa cella senza confliggere sull'occupazione, quindi
      un pareggio esatto con la posizione della congelata può cambiare *chi*
      è l'argmin — e quindi la chiave del finding — mentre il valore
      aggregato resta invariato. Trovato nella review del Task 12: il builder
      `WeeklyOrderBuilder` (`domain/solver/builders/subject_order.py`) vietava
      solo il valore aggregato (`prima_a >= FA`), non l'identità, ed era
      quindi possibile che il solver ammettesse un finding `HARD` *nuovo*
      restando dentro ADR-018 solo in apparenza. **Corretto lì** stringendo il
      ramo status-quo (divieto per attività, non sul minimo aggregato) — ma
      la causa a monte resta nel tie-break di `domain/analysis`, non
      toccabile da questo giro: va decisa quando si generalizza la famiglia
      d'ordine ai Task 13-17. ⚠ **Il banco che congela lo vede** (2026-08-26
      sera): `subject_imposed_succession` cambia la coppia nominata lasciando
      causale, risorsa e quantità identiche, ed è per questo che l'oracolo del
      banco sporco porta una chiave grossolana **dichiarata** (`_grossa` in
      `tests/solver_harness.py`) invece di un'eccezione implicita. Il fenomeno
      è quindi più largo di quanto §9.5 dichiarasse: riguarda ogni famiglia il
      cui finding nomina l'argmin invece del secchio intero.
      ✅ **Chiuso il 2026-08-28**: il pareggio si rompe con l'identità
      dell'attività (`(day, start_slot, activity_id)`). È arbitraria — fra due
      occorrenze davvero intercambiabili nessuna proprietà dell'orario le
      distingue — ma **stabile e riproducibile**, che è ciò che l'ordine di un
      queryset senza `order_by` non promette. ⚠ L'alternativa di nominarle
      **tutte** è stata considerata e scartata: sarebbe funzione della sola
      forma dell'orario, e per `WEEKLY_ORDER` funzionerebbe, ma non
      generalizza alle famiglie a coppie consecutive (`IMPOSED_SUCCESSION`
      con A = B), dove il pareggio sposta la coppia invece di allargare un
      secchio. La **deriva d'identità sotto piazzamento** resta e resta
      giusta: è `PLACEMENT_MONOTONE = False`, non un artefatto.
- [x] ⚠ ~~**Il ramo «status quo» è pigro, e nel caso misto spegne la riga.**~~
      **Chiuso il 2026-08-26 (pezzo 3, ondata 5).** La causa era testuale — il
      modello non aveva funzione di costo, quindi `riparato` e `riparato.Not()`
      erano alla pari — e **L3 gliene ha data una**: minimizza le riparazioni
      mancate insieme alle quote consumate. Non cambia cosa il modello ammette,
      cambia cosa preferisce. La prova è una misura, non un argomento: su **60
      semi** del banco che congela il fenomeno non compare più (prima: 20, 35,
      41, 45, 52), e l'esenzione che lo perdonava è stata **rimossa** insieme
      al suo test. Il banco è ora più severo: se tornasse, sarebbe rosso.

- [x] ⚠ **ADR-018 non è applicabile ai vincoli indipendenti dal
      piazzamento**, e il tetto **settimanale** del peso didattico è il primo
      caso incontrato.
      ✅ **Chiuso il 2026-08-28 (sera)**, l'altra metà: l'oracolo differenziale
      confronta sulla chiave **grossolana** `(causale, risorsa, settimana)` per
      le famiglie che nominano il secchio invece del violatore — cioè i
      checker `PLACEMENT_MONOTONE = False`, letti dal registro — e solo dove
      quella coppia era **già** rotta nella baseline. Misurato invece che
      previsto: due congelate oltre il tetto, una libera, e il finding torna
      con `activities (1,2) → (1,2,3)` e `weight 6 → 9`. ⚠ Il prezzo è
      dichiarato: si perde il **peggioramento** di una violazione già presente
      (su `max_gap`, una libera piazzata dentro un buco già fuori budget non
      fa scattare nulla). L'alternativa — confrontare la quantità violata
      famiglia per famiglia — vorrebbe dire riscrivere fuori dai checker la
      nozione di «quale numero è quello cattivo». Il testo che segue è
      l'originale.
      ⚠ **Metà chiuso il 2026-08-26 (pezzo 3, ondata 1)**: la
      «somma costante» che rendeva il vincolo vero-sempre o falso-sempre era
      `AddExactlyOne`. Con lo scarto ammesso il tetto torna evadibile come lo
      evade EDT — scartando — e la chiave grossolana diventa una scelta invece
      di un obbligo. Resta il caso in cui a sforare sono le **sole congelate**,
      che è un fatto e non una decisione. Il testo che segue è quello
      originale, e vale per quella metà. `AddExactlyOne` obbliga a piazzare ogni attività, e il
      secchio settimanale di un'unità-studente contiene *tutte* le sue celle
      candidate: la somma dei letterali liberi è quindi una **costante**, e il
      vincolo è vero sempre o falso sempre. Ne discendono due cose. La prima è
      risolta: col residuo clampato a zero il vincolo diventava `costante
      positiva <= 0`, cioè la pretesa che il passato venga riparato — il
      modello rispondeva INFEASIBLE per colpa delle sole congelate (misurato:
      due congelate da 2 punti, tetto 3, una libera). `DidacticWeightBuilder`
      ora **non posta** il tetto settimanale quando a sforarlo sono le
      congelate da sole, e continua a postarlo quando il colpevole è il totale
      — due test tengono ferme le due metà. La seconda **non è risolvibile da
      nessun builder**: la soluzione restituita porta comunque il finding
      `weight_week`, e la sua `Finding.key` non è quella di prima, perché
      `activities` cresce delle libere e `quantities["weight"]` cambia. Le
      libere vanno collocate, e ovunque vadano pesano. Quindi **l'oracolo
      differenziale a tutto campo, quando lo si scriverà, va formulato su una
      chiave più grossolana** (causale + risorsa) per le famiglie
      placement-invariant, oppure quelle famiglie vanno spostate dove EDT le
      mette davvero: nell'**analisi di capienza**, che si esegue *prima* del
      calcolo e non dentro. Trovato verificando il Task 16.

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

## Changelog → [docs/changelog.md](docs/changelog.md)

Il racconto datato sta **lì**, e non più qui. ⚠ È stata una misura, non un
gusto: dentro questo file valeva **165 KB su 204** — l'81% di un documento che
entra nel contesto di *ogni* sessione, quindi decine di migliaia di token di
storia letti prima di qualunque domanda. Ciò che serve sempre è lo stato
corrente; il perché di una decisione già presa serve quando la si riapre, ed è
allora che si apre quel file.

**Dove va cosa**, così i tre elenchi non ricominciano a divergere:

| File | Cosa contiene | Quando si scrive |
|---|---|---|
| `CLAUDE.md` | stato corrente, convenzioni, indice, scope | quando cambia *ciò che è vero adesso* |
| [docs/todo.md](docs/todo.md) | le cose da fare, e solo lì | quando una voce si apre o si chiude |
| [docs/changelog.md](docs/changelog.md) | il racconto datato, con le misure | a ogni pezzo finito |

⚠ **Questo file non cresce con il lavoro fatto.** Una voce nuova va nel
changelog; qui si *sostituisce* la riga di stato che è diventata falsa. Se una
sessione allunga `CLAUDE.md`, quasi sempre stava scrivendo nel file sbagliato.
