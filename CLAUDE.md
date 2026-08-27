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
  analysis/             il sottosistema di analisi: predicati con causali nominate, dominio residuo (S.P.), capienza,
                        il violatore di Hall (fase 5, hall.py) e lo scarto come
                        stato nominato (checkers/placement.py)
  solver/               il modello CP-SAT: vocabolario di variabili derivate,
                        residuo di ADR-018, ventisei builder su ventisette,
                        la catena lessicografica (objective.py), le quote
                        di alleggerimento (relaxation.py), i criteri di
                        qualità (quality.py + criteria.py) e la separazione
                        per popolazione con la perdita tollerata (Arbitrato)
tests/                 la suite; tests/fermi.py è il dataset Fermi come fixture, più i test dell'analisi (registro, ScheduleState, i vincoli orari/di materia, dominio residuo, capienza, il violatore di Hall e le famiglie non monotone che lo rilassano, il comando analyze) e i test del solver (registro dei builder e sua completezza, contesto, il modello, i ventisei builder uno per uno, il banco a testimone con il modello completo, l'oracolo differenziale, la catena lessicografica, le quote e lo scarto, i criteri di qualità, la separazione per popolazione, il comando solve)
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
> (`domain/analysis/`); e il **modello CP-SAT hard è completo**
> (`domain/solver/`): **ventisei builder su ventotto checker**, e i due senza
> builder non ne hanno uno per costruzione — `structural:coverage`
> (`PLACEMENT_INDEPENDENT`: il solver non crea né distrugge attività) e
> `structural:placement` (lo scarto *è* il meccanismo del modello, non un
> vincolo da postare). Il **violatore di Hall** (fase 5 dell'Analisi dei
> vincoli, `domain/analysis/hall.py`) **è anch'esso implementato**: nessun
> solver, teorema di Hall in forma deficitaria su flusso massimo e taglio
> minimo. **599 test verdi**, 16 skip tutti misurati e attribuiti
> (`venv/bin/pytest`).
>
> ⚠ **Il Fermi non misura il modello completo: misura il dataset.** Ha zero
> righe `ResourceTimeConstraint`, zero `SubjectConstraint` e i tetti di peso a
> `None`, quindi ventuno builder su ventisei non postano nulla — e infatti dà
> **gli stessi 8140 variabili e 1082 constraint dello spike a cinque vincoli**,
> `OPTIMAL` in ~0,56 s. La misura del modello è
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
> (`QualityCriterion`) e non dal codice. ⚠ E costano: sul Fermi cinque criteri
> senza limite di tempo non tornano in nove minuti, con `--limite 15` chiudono
> in 39,5 s lasciando due livelli su sei con l'ottimo non dimostrato.
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
> Resta **un solo pezzo dichiarato fuori** — l'assegnazione delle aule — più i
> punti aperti elencati sotto.

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
ora completo** — ventisei builder su ventisette checker. Ciò che manca non è
più la traduzione dei vincoli, ma i due pezzi dichiarati fuori dal piano: gli
alleggerimenti a quota con l'ottimizzazione lessicografica e l'assegnazione
delle aule (il violatore di Hall è implementato, vedi la nota di stato sopra
e il changelog). Vedi [ADR-008](docs/decisioni.md) e [ADR-016](docs/decisioni.md).

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
- [x] **Come si comporta un builder quando un constraint mescola attività
      congelate già in violazione e attività libere?** Deciso con
      [ADR-018](docs/decisioni.md): **capacità residua** clampata sui soli
      letterali liberi, e **oracolo differenziale** (nessun finding `HARD`
      *nuovo*, invece di nessun finding `HARD`). Un orario illegale è uno
      stato ammesso — è il comportamento di EDT, che con 21 attività in
      violazione piazzate a mano continua a lavorare. **Da implementare** nella
      spec del modello completo, prima dei ventidue builder restanti.
- [ ] ⚠ **Cosa significa «cambio di sede» quando due sedi coesistono nella
      stessa fascia?** Sotto capienza cumulativa (aula con `Qtà > 1`, feature
      EDT documentata) due attività di sedi diverse possono occupare la stessa
      fascia della stessa risorsa. `MaxSiteChangesChecker` **conta un cambio**,
      ma solo come conseguenza di un dettaglio implementativo:
      `state.occupancy` è una `list` e `_site_sequence` la scorre in ordine
      d'inserimento, quindi il conteggio dipende dall'ordine. È un **artefatto,
      non una semantica**, e va deciso in `domain/analysis` prima di poter
      essere tradotto — tradurre un artefatto sarebbe peggio che lasciare lo
      scarto. Il builder CP-SAT lo dichiara nel proprio docstring. Trovato
      nella review del Task 9 del piano `modello-hard-completo`. ⚠ Non tocca il
      Fermi, dove le aule non sono mai state inserite (voce qui sopra).
- [ ] ⚠ **Il tie-break di `_placed_of` è un artefatto dell'ordine
      d'inserimento, non una semantica** — la stessa forma del problema qui
      sopra su `MaxSiteChangesChecker`. `_placed_of` (in
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
- [x] ⚠ ~~**Il ramo «status quo» è pigro, e nel caso misto spegne la riga.**~~
      **Chiuso il 2026-08-26 (pezzo 3, ondata 5).** La causa era testuale — il
      modello non aveva funzione di costo, quindi `riparato` e `riparato.Not()`
      erano alla pari — e **L3 gliene ha data una**: minimizza le riparazioni
      mancate insieme alle quote consumate. Non cambia cosa il modello ammette,
      cambia cosa preferisce. La prova è una misura, non un argomento: su **60
      semi** del banco che congela il fenomeno non compare più (prima: 20, 35,
      41, 45, 52), e l'esenzione che lo perdonava è stata **rimossa** insieme
      al suo test. Il banco è ora più severo: se tornasse, sarebbe rosso.

- [~] ⚠ **ADR-018 non è applicabile ai vincoli indipendenti dal
      piazzamento**, e il tetto **settimanale** del peso didattico è il primo
      caso incontrato. ⚠ **Metà chiuso il 2026-08-26 (pezzo 3, ondata 1)**: la
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

## Changelog

- **2026-08-27 (separazione per popolazione)** — **EDT non cerca mai un ottimo
  congiunto, e adesso nemmeno noi.** I comandi del prodotto sono due —
  `Ottimizza gli orari dei docenti` / `... delle classi`, `TypeTypeOptim =
  ttoProfs, ttoClasses` — e chi lancia dichiara **quanto è disposto a
  peggiorare l'altra popolazione**. `Arbitrato(popolazione, tolleranza)`
  ([spec](docs/superpowers/specs/2026-08-27-separazione-popolazione-design.md)):
  i criteri della popolazione sacrificata escono dalla catena e diventano
  `valore <= base + tolleranza`, un vincolo hard di non-regressione — mai un
  peso in una somma, che è la frase con cui `motore-risoluzione.md` descrive il
  meccanismo.

  🔑 **Non basta riordinare i `rank`**, ed è il punto del pezzo. Con i soli
  `rank` i criteri dell'altra popolazione restano **livelli**: si ottimizzano
  comunque, e costano. L'arbitrato li declassa a tetti. Misurato in A/B sul
  Fermi: la stessa riga come tetto costa i suoi ~640 variabili di definizione e
  **zero** tempo di ricerca (31,6 s); come livello si prende una fetta intera
  del limite e chiude senza dimostrare l'ottimo (41,9 s). Il risparmio è
  limitato dal `--limite`, e senza limite non è limitato da niente.

  🔑 **La base non è una seconda definizione del criterio: è la stessa
  funzione.** Un criterio posta **solo definizioni** — l'invariante scritto in
  testa a `quality.py` quando il pezzo precedente è nato — quindi lo si può
  valutare su un orario *dato* chiamandolo con i letterali di cella sostituiti
  dalle costanti `0`/`1` di quell'orario: ogni booleano derivato è determinato
  per propagazione, e un `Solve` istantaneo restituisce il numero.
  L'alternativa era riscrivere i cinque criteri in Python su `ScheduleState`,
  cioè il difetto che questo progetto ha già intercettato due volte. Un test
  tiene ferme le due strade: la base dev'essere il numero che il **livello** dà
  sullo stesso orario.

  ⚠ **E il pezzo ha trovato che i criteri di qualità non funzionavano su
  nessun orario già scritto.** L'arbitrato ha bisogno di un orario di partenza,
  e un orario di partenza mette in catena **L4**: la stabilità arriva a zero
  conservando tutto, il suo fissaggio inchioda ogni cella, e da lì in giù ogni
  livello di qualità è **inerte**. Sul Fermi con l'orario già scritto la catena
  unica riporta `gaps_teachers 420`, `isolated_teachers 20`,
  `regularity_classes 265` **in 0,06 s per livello** — non sono risultati, sono
  i valori dell'orario che c'era, misurati e non migliorati. Un livello che
  chiude in sessanta millisecondi su 284 attività non sta ottimizzando niente.
  ⚠ Il difetto **non è di questo pezzo**: c'era dal giorno in cui i criteri
  sono nati, e non si vedeva perché **il Fermi non ha piazzamenti di suo**,
  quindi la misura che li aveva dichiarati funzionanti girava dove L4 non
  esiste. È la forma di sempre — una proprietà del dataset scambiata per una
  proprietà del codice — stavolta a ventiquattr'ore di distanza.
  **La correzione è d'ordine, e la decisione viene da EDT**: là i comandi sono
  due e il conflitto non si pone, perché `Ottimizza` rimescola un orario che
  c'è già e rimescolare *è* lo scopo. Qui il comando è uno, quindi la corsa
  deve dichiararsi: senza arbitrato vince la stabilità (ADR-010, il secondo
  quadrimestre da non stravolgere), con l'arbitrato la stabilità scivola in
  coda e diventa lo **spareggio**. Sul Fermi i buchi dei docenti passano da 420
  a **0**, e il prezzo è dichiarato: **231 attività spostate su 284**.

  ⚠ **L'istanza dei test è stata costruita dopo aver misurato che le ovvie non
  funzionano.** Due docenti per due classi su una griglia 2×2 sembra la
  tensione canonica e **non lo è**: due classi diverse possono occupare la
  stessa cella, quindi comprimere i docenti comprime anche le classi e i due
  ottimi coincidono — tolleranza 0 e tolleranza 2 davano la stessa risposta,
  cioè un test incapace di distinguere. La tensione vera è fra `regularity` (la
  materia sempre alla stessa fascia, quindi su giorni diversi) e
  `free_half_days` (tutto lo stesso giorno, quindi su fasce diverse): l'una a 1
  costringe l'altra a 2.

  **Nove mutazioni, nove esiti distinti.** ⚠ E due sono servite dove una
  sembrava bastare: sfasare il **tetto** non tocca il test che confronta la
  base col livello, perché quel test guarda la base. Ci vuole la mutazione
  sulla **fonte** per farlo diventare rosso.

  ⚠ Sul Fermi il tetto **non morde** — buchi e ore isolate arrivano a zero
  comunque — quindi tolleranza 0 e 10 danno lo stesso orario. Come sempre su
  questo dataset la misura è del **costo**, mai della **copertura**.

  Dichiarato fuori, e come decisione: il valore **raggiunto** dal criterio
  sacrificato. Il rendiconto dice base e tetto, non dove si è atterrati;
  leggerlo vorrebbe `solve_chain` che restituisce il solver, o una seconda
  valutazione con le righe ripescate e riappaiate per nome — parecchia coppia
  incidentale per un numero solo. **612 test verdi**, 16 skip.

- **2026-08-27 (criteri di qualità)** — **La catena impara a distinguere due
  orari legali.** Sei ondate
  ([spec](docs/superpowers/specs/2026-08-27-criteri-di-qualita-design.md)). I
  quattro livelli esistenti misurano tutti un **fallimento** — ore scartate,
  attività scartate, violazioni nuove, spostamenti — quindi un orario che
  piazza tutto senza violare nulla era indistinguibile da un altro che fa lo
  stesso lasciando a un docente quattro buchi al giorno. Ora ci sono i livelli
  che li separano: `domain/solver/quality.py` (il registro) e `criteria.py` (le
  cinque traduzioni).

  ⚠ **In EDT i meccanismi sono due, e confonderli era l'errore di partenza.**
  `Ordinamento dei criteri` è la lista degli **undici** criteri di
  *piazzamento*, riordinabile fra «considerati» e «ignorati»; `Ottimizzazione
  degli orari` è una fase **separata**, con **tre** slot ordinati **per
  popolazione** su cinque valori. Implementati i quattro valori
  dell'ottimizzazione — buchi, attività isolate, mezze giornate libere,
  equilibrio didattico — più `Rispetta le preferenze`, che in EDT è
  l'undicesimo e **ultimo** criterio di piazzamento, ed è il pennello verde che
  il pre-filtro lasciava passare rimandando qui per nome.

  🔑 **Il pezzo è economico perché le quantità esistono già.** Quasi tutte sono
  calcolate da un checker di `domain/analysis`, dove servono a essere
  confrontate con un tetto: qui la stessa quantità si **minimizza**. I buchi
  sono la formula di `MaxGapChecker` senza il D.T.B., e un test lo tiene fermo
  facendo guardare **lo stesso orario** al livello e al checker — devono dire
  lo stesso numero, o il criterio misura qualcos'altro.

  🔑 **E una definizione di EDT collassa.** *«Attività isolata in una mezza
  giornata **e** di durata inferiore a due fasce orarie»* sono due condizioni
  che diventano una: **la mezza giornata ha esattamente una fascia occupata**.
  Sola e lunga due dà 2; due ore singole danno 2 e nessuna è isolata. Non serve
  guardare né la durata né l'identità dell'attività.

  ⚠ **La traduzione italiana di un criterio dice un'altra cosa**, ed era già
  scritto nei documenti: `Equilibrio didattico` traduce `Régularité des cours`,
  ma l'enum è `tcoMemesHoraires` — *stessi orari*. Il senso è che la materia
  ricada sempre nella stessa fascia, non l'equilibrio del carico. Tradurre
  l'etichetta alla lettera avrebbe prodotto un criterio diverso da quello del
  prodotto.

  **L'ordine è un dato, non codice** (`QualityCriterion`, migrazione `0010`),
  perché è il punto dichiarato del meccanismo: *«"Criteri considerati /
  ignorati" è una UI onesta»*. Tabella vuota ⇒ la catena di prima, e un
  criterio dell'enum che nessuna traduzione legge è un criterio **ignorato**,
  non un errore.

  ⚠ **Il costo cambia una raccomandazione operativa.** Fermi, cinque criteri:
  **senza limite di tempo il calcolo non è tornato in nove minuti**; con
  `--limite 15` finisce in **39,5 s**, e due livelli su sei chiudono con
  l'ottimo **non dimostrato** — `regularity` e `free_half_days`, i due che
  aprono più simmetrie. La catena resta corretta (un livello che scade fissa
  l'ultimo valore trovato), ma il limite per livello smette di essere una
  precauzione. Dichiarato nel docstring di `manage.py solve`.

  ⚠ **Due difetti trovati nei test, non nel codice, e sono la stessa forma —
  il primo l'ha trovato la misura sul Fermi, non una rilettura.** Le dimensioni
  del modello non si muovevano di un bit con cinque criteri accesi, perché
  `_dimensioni` costruiva la sola `build_model` mentre i livelli di qualità
  nascono dentro `livelli()`: un'asserzione **incapace di fallire**. E
  correggendola è emerso il secondo: il test misurava **due volte lo stesso
  stato**, perché per la proprietà «tabella vuota» non esiste una riga da
  aggiungere in mezzo. Ora il confronto è contro il modello **nudo** con una
  differenza attesa esatta, ed è l'unica forma in cui la mutazione «una
  variabile di troppo» diventa rossa.

  ⚠ **Una previsione sbagliata, corretta dai numeri e non dal ragionamento**:
  un'ora isolata con `population=ALL` vale **due**, non una — è isolata per il
  docente e per la classe. Non è un doppio conteggio per distrazione: il
  contatore `A.iso.` di EDT è dichiarato «per docente/classe/**gruppo**». Due
  test attendevano 1 e sono stati corretti, non il codice.

  **Nove mutazioni, nove esiti distinti**: ciascun criterio spento rende rossi
  i suoi test e nessun altro; «nessun livello di qualità» ne rende rossi
  quindici su diciassette e lascia verdi esattamente i due conservativi, che
  devono sopravvivergli. Suite: **599 test verdi**, 16 skip.

  Resta fuori, dichiarato: la **separazione per popolazione** e la **perdita di
  qualità tollerata** — EDT ottimizza docenti *oppure* classi e dichiara quanto
  è disposto a peggiorare l'altra. Il fissaggio della catena è già metà del
  lavoro (`<= valore` diventa `<= valore + tolleranza`), ma *quale* popolazione
  ottimizzare è un parametro di lancio: va progettato col comando, non con
  l'obiettivo.

- **2026-08-27 (audit delle quote)** — **Dodici call site di alleggerimento,
  misurati uno per uno: nessun difetto di comportamento, due di
  documentazione.** È il seguito diretto della review. Là erano emersi un
  errore di unità (`MAX_PRESENCE`) e un'attribuzione decisa dall'ordine dei pk
  (`risorsa_di`), entrambi su call site che nessun test sapeva distinguere da
  quelli sani; gli altri dieci erano stati controllati **per lettura**, non per
  misura. Ora lo sono.

  🔑 **Il risultato positivo va detto per primo: ogni margine è la grandezza
  che dichiara, e ogni granularità è quella della riga di EDT.** Sonda su tutte
  le famiglie prima di scrivere un solo assert: il tetto delle mezze giornate
  concede mezze giornate, quello del peso concede pesi, quello delle sedi
  concede cambi, quello delle materie minuti — e nessuno concede il decuplo.

  ⚠ **Ma i test che c'erano non potevano dirlo.** La forma `_senza_poi_con` —
  «senza quota INFEASIBLE, con quota OPTIMAL» — prova che la quota è
  **collegata**, mai *quanto* concede né *quante volte*: un margine
  moltiplicato per mille e un letterale issato fuori dal ciclo la passano
  entrambi indisturbati. È precisamente la vacuità che aveva lasciato passare
  l'errore di unità di `MAX_PRESENCE`. **Undici test nuovi** la chiudono, uno
  per la grandezza e uno per la granularità, famiglia per famiglia.

  **Undici mutazioni, undici esiti distinti, esattamente un rosso ciascuna** —
  il margine di una famiglia decuplicato, oppure un letterale solo per
  (famiglia, risorsa) al posto del tag. Nessun test passa per caso, nessuno è
  ridondante con un altro.

  ⚠ **I due difetti sono nella documentazione, e sono la forma di sempre.** La
  tabella delle unità di `RelaxationQuota` **non nominava `ARRIVAL_DEPARTURE`**,
  che è una famiglia a margine con un suo test dal giorno in cui è nata; e dava
  `FREE_GUARANTEED` in *mezze giornate* mentre lo stesso numero si sottrae 1:1
  anche dalla soglia dei **giorni** — misurato: con `free_days = 2` un margine
  di 1 lascia la soglia a 1, non a 0.

  ⚠ E quella divergenza **resta, dichiarata invece che corretta**. Non è il
  gemello dell'errore di `MAX_PRESENCE`: là un margine in minuti finiva su un
  tetto in giorni e lo **spegneva**; qui le due soglie contano cose disgiunte
  (un giorno del tutto libero contribuisce zero mezze giornate libere, perché
  il checker le conta solo sui giorni che lavorano), quindi non esiste una
  conversione da applicare, e una riga che non alleggerisse `free_days`
  resterebbe inerte proprio sul vincolo che le scuole scrivono più spesso. La
  tabella porta ora anche la **granularità** accanto all'unità, che è la metà
  che non era scritta da nessuna parte.

  ⚠ **E una sonda ha misurato sé stessa invece del codice**, che vale
  registrare: tre attività su sedi A/B/A dovevano costare due cambi, e il
  modello rispondeva `OPTIMAL` con margine 1. Non era il builder — il solver
  **riordina**, e A/A/B costa un cambio solo. Con tre sedi distinte l'ordine
  non aiuta più e la misura torna quella voluta. Un caso di prova che il solver
  può aggirare non misura il vincolo: misura l'istanza.

  Nessun builder toccato, quindi il Fermi è invariato per costruzione (8426
  variabili, 1086 constraint, tenuti fermi dalla suite). **582 test verdi**, 16
  skip.

- **2026-08-27 (review)** — **La review del pezzo 3, applicata: un errore di
  unità che spegneva un vincolo, e un'attribuzione decisa dall'ordine dei pk.**
  Sei rilievi su alleggerimenti e catena lessicografica, tutti chiusi. Il
  risultato positivo va detto per primo: **nessun builder più largo del
  checker**, nessuna traduzione sbagliata. I difetti stanno nelle unità di
  misura, nell'attribuzione delle quote e nella forma delle API.

  🔑 **Il margine di `MAX_PRESENCE` è in *ore*, e veniva sommato anche al tetto
  dei *giorni*.** Con «margine 60» un tetto di «al massimo 1 giornata» diventava
  61: il vincolo si spegneva, in silenzio. La fonte lo dice per nome
  (`docs/edt/estratti/motore-punti-aperti.md`: *«MaxPresentielProf … | ore»*),
  e il tetto dei giorni non è alleggeribile con quella grandezza.
  ⚠ **Il test che c'era non poteva vederlo**: `mini_school(days=1)` contro un
  tetto `days: 5` rende quel ramo irraggiungibile. È la forma consueta di
  vacuità di questo progetto — un verde incapace di fallire — stavolta su una
  famiglia scritta il giorno prima.

  ⚠ **E lo stesso margine si consumava una volta per l'intera settimana.** Un
  letterale solo per riga, issato fuori dal ciclo sui giorni, significa «due
  giorni sforati al prezzo di una quota», mentre la riga di EDT dice «una volta
  per settimana e per docente» — cioè conta le **volte**. Ora è per giorno, come
  in `MAX_HOURS`, che quotava la stessa frase in modo opposto.
  ⚠ `SITES` **resta com'era**, ed è una divergenza ora **dichiarata** invece che
  accidentale: in francese quella riga dice *par semaine*, quindi un'allowance
  settimanale e un letterale per riga sono difendibili.

  ⚠ **La quota di una riga di materia si deduceva col minimo delle chiavi**, e
  dava tre risposte diverse: la classe (per un accidente di chiavi esterne —
  `ClassPartition` punta alla `SchoolClass`, quindi la classe prende il
  `Resource.pk` più basso), la **parte** su una riga di parte, e una parte
  **qualunque** su una riga di raggruppamento. Un raggruppamento è trasversale
  (ADR-013): non esiste «la» sua classe, e attribuirgli la quota di un membro a
  caso è un'attribuzione decisa dall'ordine di creazione delle righe.
  `risorsa_di(row)` ora **legge** il campo che il `CheckConstraint` obbliga la
  riga ad avere, e sul raggruppamento dà `None`, cioè la quota generica.

  🔑 **`deroga()` restituiva `letterale | None`, e la prova che l'astrazione
  mancava era già nel codice**: quattro call site ripetevano lo stesso
  null-check, e il quinto (`post_cross`) si era scritto una chiusura locale per
  non ripeterlo altre cinque volte. Quando un call site cresce un involucro
  attorno a un helper, l'involucro appartiene all'helper. Ora restituisce sempre
  un oggetto con `.applica(vincolo)`, e senza quota è l'oggetto nullo — la
  stessa forma per cui `margine()` restituisce l'intero `0`.

  Più tre pulizie: `AddExactlyOne([])` è **già** INFEASIBLE (verificato), quindi
  il ramo `dominio_vuoto` e il suo booleano contraddittorio spariscono;
  l'uscita anticipata di `livelli()` **dichiara** di confondere due condizioni
  («niente di libero» e `allow_unplaced=False`) e la conseguenza in quella
  modalità — quote non minimizzate, rami di ADR-018 di nuovo alla pari, con
  l'oracolo di Hall fra i chiamanti; e la guardia di `qualcuna_piazzata` porta
  gli id nel nome invece di un `hash(aids) & 0xffff`, che troncato a sedici bit
  collideva.

  **Tre test nuovi, tre mutazioni, tre esiti distinti** — nessuno passa per
  caso. Suite: **571 test verdi**, 16 skip. Fermi invariato (8426 variabili,
  1086 constraint): il dataset non ha righe `RelaxationQuota`, quindi nessuno
  di questi letterali nasce lì — che è, di nuovo, la ragione per cui il Fermi
  misura il costo e mai la copertura.

  **Igiene**, dai residui di una sessione lavorata senza worktree: `AGENTS.md`
  era una copia di `CLAUDE.md` ferma al 2026-07-26 — 615 righe contro 1922,
  senza solver, analisi, Hall e pezzo 3 — cioè il peggior tipo di documento
  invecchiato, autorevole e caricato in automatico. Verificato che non portasse
  nulla di suo, è diventata un **symlink**. E `.claude/` entra nel `.gitignore`:
  ci viveva un worktree registrato di 6,4 MB dentro il repository.

- **2026-08-27** — **Il merge delle due linee, e il criterio dell'oracolo di
  Hall che il pezzo 3 aveva reso vuoto.** `master` e `origin/master` erano
  divergenti — diciannove commit locali del violatore di Hall contro undici del
  pezzo 3, entrambi partiti dal merge della PR #1. Un solo conflitto testuale
  (questo file); tutto il codice si è fuso da solo. **Ma le due linee si
  contraddicevano nel merito**, e la suite l'ha detto: **cinque rossi**.

  🔑 **Il pezzo 3 ha tolto da sotto i piedi alla fase 5 la sua unica prova.**
  Il modello ha smesso di pretendere il piazzamento, quindi un insieme
  deficiente non risponde più `INFEASIBLE`: **rinuncia**. La direzione 1
  dell'oracolo — «se la fase 5 dichiara un insieme infattibile, il solver deve
  rispondere INFEASIBLE» — chiedeva al solver una risposta che il solver non dà
  più. Riscritta su **due** modelli: `allow_unplaced=False`, che è il modello di
  prima dello scarto e che il suo stesso docstring chiama «il modo di chiedere:
  questo vincolo morde?», deve dare `INFEASIBLE`; e col modello vero i **minuti
  scartati** devono essere **esattamente** quelli che la fase 5 ha dichiarato
  mancanti. La seconda metà è più forte di ciò che c'era prima: non conferma
  che una deficienza esista, ne conferma l'**aritmetica**. Misurato sull'istanza
  dell'oracolo: deficit dichiarato `420 − 360 = 60`, minuti scartati **60**.
  ⚠ E la prova che non è un'asserzione di comodo è una **mutazione che il
  vecchio criterio non avrebbe colto**: sbagliando di una fascia la capienza in
  `hall.py` (`capacity - 1`), il test diventa rosso — mentre l'`INFEASIBLE` di
  prima sarebbe passato indisturbato.

  ⚠ **E il test che *non* era rosso era il peggiore dei due.**
  `test_il_solver_conferma_anche_il_confine` continuava a passare: asserisce
  `OPTIMAL`, e col pezzo 3 `OPTIMAL` è la risposta anche all'istanza
  deficiente. La coppia era stata scritta perché la seconda metà impedisse a
  una fase 5 «tutto infattibile» di passare la prima — e aveva smesso di poter
  fallire in entrambe le direzioni. **L'ottava forma di vacuità di questo
  progetto**, e la prima arrivata non da una svista ma da un merge: nessuno dei
  due lati era sbagliato *da solo*. Ciò che separa le due istanze non è più lo
  stato ma la rinuncia — **60 minuti là, zero qui** — ed è così che il confine
  è riscritto.

  ⚠ **La terza prova per `INFEASIBLE` passava per la ragione sbagliata.** In
  `test_il_rilassamento_non_ha_spento_la_fase_5` la riga `MIN_DISTRIBUTION`
  (min_days 3, docente libero un giorno solo) è una causa **indipendente e
  sufficiente** di infattibilità: misurato, col modello che ammette lo scarto
  la risposta è `INFEASIBLE` con **zero** minuti scartati, cioè l'infattibilità
  non viene dalla capienza che il test crede di misurare. Passata a
  `allow_unplaced=False` e **dichiarata**: quella metà *corrobora e non isola*,
  l'isolamento è nell'oracolo.

  🔑 **Un difetto di prestazione trovato per lettura, non cercato.** Il checker
  nuovo del pezzo 3 (`structural:placement`) ereditava
  `PLACEMENT_MONOTONE = True`, ma piazzare **ripara** la sua violazione — che è
  la definizione stessa di non monotono scritta in `domain/analysis/domain_size.py`.
  Sotto il criterio `chiavi_nuove = dopo − baseline` un checker che sa solo
  *togliere* chiavi non ne produce mai di nuove, quindi la marcatura **non
  cambia il verdetto di nessuna cella**: cambia il **costo**. Senza,
  `admissible_starts` scorreva tutte le attività non piazzate per ogni cella di
  prova, e la fase 5 sul Fermi era passata da **0,326 s a 1,887 s** — una
  regressione di 5,8× che nessun test misurava, perché la soglia era `< 5.0`.
  Marcato non monotono: **0,326 s**, il numero che il changelog dichiarava.

  I quattro test di monotonia asserivano liste esatte di causali HARD, ora
  sporcate da `activity_unplaced`: l'attività libera lì è deliberatamente non
  piazzata, cioè la **premessa** e non un esito. Aggiunto `_violazioni()`, che
  toglie l'incompletezza e lascia le violazioni di vincolo — il checker stesso
  dichiara di descrivere «un orario incompleto, non illegale».

  Suite dopo il merge: **568 test verdi**, 16 skip in ~100 s.

- **2026-08-26 (notte, hall)** — **Il violatore di Hall: la fase 5,
  implementata senza solver.** Sette task sul branch `hall-violator`, sopra
  [`docs/superpowers/specs/2026-08-26-violatore-di-hall-design.md`](docs/superpowers/specs/2026-08-26-violatore-di-hall-design.md).
  `domain/analysis/hall.py` risponde alla domanda che la fase 4 non sa porre:
  non «questo vincolo impedisce il piazzamento», ma «questo *insieme* di
  attività non entra nella finestra di disponibilità comune delle sue risorse,
  anche se nessuna presa da sola è impossibile». Il metodo è il **teorema di
  Hall in forma deficitaria**: flusso massimo su una rete (attività → celle →
  risorsa `r`) per ogni (risorsa, firma di settimana) in `domain/analysis/flow.py`
  (nuovo, generico, senza semantica di orario — la stessa separazione che
  `domain/solver` ha fra `model.py` e i builder), e il **taglio minimo è
  l'insieme colpevole**. Una passata di riduzione greedy (`_reduce`) lo tiene
  **irriducibile** invece che massimale: senza, sul Fermi un finding
  nominerebbe centinaia di attività, una diagnosi che nessuno legge. Esposto
  in `manage.py analyze` come fase 5, dopo la fase 4, col flag `--no-hall` per
  spegnerla e la dichiarazione esplicita quando la salta (richiede
  `--schedule`, a differenza della fase 4 che lavora sull'anagrafica grezza).

  🔑 **Prima volta su questo progetto: due trappole scritte in spec *prima* di
  implementarle, non scoperte dopo.** Il pattern ricorrente qui — il
  changelog arriva a contarlo alla «tredicesima volta» entro il
  2026-08-26 (sera), sempre nella stessa forma — è che un documento dichiara
  vera una proprietà che si rivela falsa solo controllandola contro il
  checker o i dati. Questa volta la spec (§2, §4.1) ha **previsto** due falsi
  positivi specifici e ha chiesto un test dedicato per ciascuno, prima che il
  codice esistesse. Tengono entrambi.
  **§2 — le firme di settimana.** Due attività di settimane disgiunte non
  competono per la stessa cella; trattarle come concorrenti produrrebbe
  deficienze fantasma — il difetto peggiore possibile per una fase che dice
  «impossibile» e manda l'utente a smontare vincoli sani. `analyze_hall` riusa
  `week_signatures` di `conformity.py` (non `_week_groups` di `capacity.py`:
  la prima include le indisponibilità datate ed è la stessa firma su cui posta
  il modello CP-SAT), e `test_le_settimane_disgiunte_non_competono` lo tiene
  fermo.
  **§4.1 — lo spiazzamento.** Le attività candidate già piazzate (le
  «sorelle») vanno **tutte** spiazzate prima di calcolare i domini: se restano
  piazzate si tolgono il dominio a vicenda, la capienza calcolata scende sotto
  il vero e produce falsi positivi — un difetto che nessun caso positivo
  avrebbe rivelato. `_split` lo fa, e
  `test_le_sorelle_gia_piazzate_non_si_tolgono_il_dominio` lo dimostra.

  **Quattro scoperte durante l'esecuzione, non previste dalla spec.**
  `MaxFlow.max_flow` sollevava un loop infinito quando sorgente e pozzo
  coincidono (misurato: `exit 124`); irraggiungibile dalla rete di Hall così
  com'è costruita, ma un hang è il modo peggiore di fallire in uno strumento
  da riga di comando — ora solleva `ValueError`.
  `_cell_capacity` pesa le **quantità** dei materiali cumulativi, come
  `OccupationChecker.check` (`checkers/occupation.py` riga 25): contare le
  attività invece delle quantità avrebbe sovrastimato la capienza residua ogni
  volta che un'immobile già piazzata ne occupa più di una.
  I due test del Task 4 non dimostravano davvero il ciclo sulle firme — tre
  mutazioni realistiche passavano indisturbate, incluso il codice pre-task —
  corretti spostando la deficienza alla settimana 1 e aggiungendo un test
  portante sulla condivisione di `seen`.
  E un test del Task 3 non testava ciò che il suo nome diceva
  (`test_l_insieme_nominato_e_irriducibile` non esercitava `_reduce`, perché
  in quello scenario il taglio minimo restituisce già l'insieme irriducibile):
  rinominato `test_il_taglio_minimo_esclude_le_attivita_estranee`, e aggiunto
  `test_la_riduzione_toglie_la_terza_di_tre_sulla_stessa_cella`, costruito
  apposta perché il taglio minimo sia strettamente più largo dell'irriducibile.

  ⚠ **L'oracolo misura la precisione, mai il richiamo — per costruzione, non
  per pigrizia.** `tests/test_hall_oracle.py` verifica due direzioni: ogni
  finding dev'essere confermato dal solver (`INFEASIBLE`), e su istanze
  fattibili per costruzione (i testimoni di `solver_harness`) la fase 5 deve
  tacere — parametrizzata su **quaranta semi** (`range(1, 41)`), non i cinque
  del piano originale: **misurato**, 42 test in 6,4 s. Il richiamo — trovare
  *tutti* i sottoinsiemi infattibili — non si promette da nessuna parte:
  enumerare tutti i sottoinsiemi di risorse è esponenziale, ed è la ragione
  per cui l'alternativa è stata scartata già in §1.2 della spec. Il risultato:
  **zero finding sui 40 semi, nella suite** — non una misura di review
  rimasta fuori dal repository. E la qualificazione che conta quanto il
  numero resta: i testimoni di `build_witness` non aggiungono mai
  indisponibilità e lasciano circa metà griglia libera, quindi i 40 semi
  misurano **l'assenza di rumore su istanze lasche**, non la tenuta sul
  confine di Hall. Quel confine lo dimostrano solo i due casi scritti a mano
  (`test_un_finding_e_confermato_dal_solver`,
  `test_il_solver_conferma_anche_il_confine`).

  ⚠ **La proiezione di costo della spec era sbagliata di un ordine di
  grandezza, ed è stata corretta invece del changelog.** §4.2 stimava ~3,5 s
  sul Fermi intero, estrapolati linearmente dalla colonna S.P. di 26 attività
  (~12 ms/attività). Misurato (`test_fermi_intero_misurato` in
  `tests/test_analysis_hall.py`): **~0,4 s** su 284 attività — l'estrapolazione
  ignorava che i domini si calcolano una volta per attività dentro un solo
  `ScheduleState` condiviso fra tutte le risorse, non ricalcolati risorsa per
  risorsa. Come per il modello CP-SAT hard, sul Fermi questo misura il
  **costo**, mai la **copertura**: il dataset non ha righe di vincolo, quindi
  zero finding è l'esito atteso, non un risultato.

  Suite dopo i sette task: **516 test verdi**, 16 skip (i 35 in più sono i
  seed 6-40 dell'oracolo, appena portati nella suite). Corretto anche il
  **436** dichiarato nella nota di stato più sopra: era la misura di prima dei
  due commit di review della PR #1 (`modello-hard-completo`), non il numero
  corrente neppure a inizio di questo lavoro. E i **tre pezzi dichiarati
  fuori** nella nota di stato diventano **due**: resta l'assegnazione delle
  aule e gli alleggerimenti a quota con l'ottimizzazione lessicografica.

  ---

  ⛔ **E poi la review finale ha trovato un falso positivo dimostrato — il
  difetto che questa stessa voce si congratulava di aver prevenuto.** Tre righe
  di riproduzione: `mini_school()`, una riga `MIN_DISTRIBUTION`
  (`min_days = 3`) su un docente, tre attività da un'ora sui giorni 0, 1 e 2.
  `check_schedule` non emette **nessun** finding HARD, `solve` risponde
  `OPTIMAL` — e `analyze_hall` restituisce **tre** finding «L'attività non ha
  nessuna collocazione ammissibile». Cioè esattamente ciò che la fase 5 non ha
  il diritto di fare: mandare l'utente a smontare vincoli sani.

  🔑 **La causa sta nel punto che la spec dichiarava sano per definizione.**
  §4 diceva: *«Resta sano perché la condizione di `residual_domain` è
  precisamente l'ammissibilità»*. Non lo è. La condizione di
  `admissible_starts` è «la `Finding.key` è **cambiata** rispetto alla
  baseline», e `Finding.key` include le `quantities`. Per un checker la cui
  violazione è una **deficienza** — `MIN_DISTRIBUTION` esiste già a stato
  vuoto, con `days = 0` — ogni piazzamento *migliora* il conteggio e con esso
  cambia la chiave: chiave nuova a ogni cella, dominio vuoto, deficienza
  inventata. E §4.1 — la trappola che la spec aveva **previsto**, giustamente —
  è ciò che *crea* la condizione, perché spiazzando tutte le candidate insieme
  rende la baseline lo stato in cui i minimi sono massimamente violati. La
  precauzione giusta ha esposto il difetto sbagliato.

  ⚠ **Né le sette review per-task né l'oracolo a quaranta semi potevano
  vederlo, e il perché è il difetto vero.** `build_witness(seed)` lascia
  `ResourceTimeConstraint.objects.count() == 0`, `SubjectConstraint == 0`,
  `ResourceUnavailability == 0`: le righe di vincolo le creano i
  **derivatori**, che `build_witness` non chiama. I quaranta semi dell'oracolo
  esercitavano quindi lo stesso sottoinsieme dello spike a cinque vincoli — ed
  è **letteralmente** la frase che questo file porta già sul Fermi («non misura
  il modello completo: misura il dataset. Ha zero righe
  `ResourceTimeConstraint`, zero `SubjectConstraint`»), non applicata al banco
  nuovo. Un numero grande di semi ha fatto da anestetico: quaranta ripetizioni
  della stessa misura povera sembrano una copertura.
  **Corretto** estraendo da `run_tutte_le_famiglie` la metà che **non chiama il
  solver** — `costruisci_tutte_le_famiglie(seed)`, che deriva le righe di tutte
  e ventisei le famiglie e **asserisce** che il testimone le soddisfi insieme.
  Su quei testimoni densi la fase 5 era rossa **40 semi su 40** — da **1 a 29**
  falsi positivi per seme, **14,1 di media**; e l'oracolo resta a **~26 s** per
  i quaranta semi,
  perché alla fase 5 il solver non serve e non lo si paga.

  **La correzione**: `Checker.PLACEMENT_MONOTONE`, dichiarato nella stessa
  forma di `PLACEMENT_INDEPENDENT` — default `True`, `False` sulle famiglie in
  cui piazzare può *riparare* una violazione oppure spostare l'identità del
  finding senza aggravarlo. `admissible_starts(..., relaxed=False)`; con
  `relaxed=True` esclude i non monotoni, e `hall.py` passa `relaxed=True`.
  ⚠ Il default resta `relaxed=False`, quindi **S.P. non cambia di un bit** e
  nessun test esistente si muove: `S.P.` è una stima di difficoltà in una
  colonna ordinabile, e un dominio più stretto è per l'utente informazione, non
  un bug — la fase 5 è l'opposto, il suo verdetto negativo è una dimostrazione.
  Rilassare fa perdere **richiamo**, mai precisione: domini più larghi
  significano più capienza, quindi meno deficienze trovate. È il verso giusto
  in cui sbagliare.

  🔑 **E l'elenco della review era corretto ma non esaustivo, in entrambe le
  direzioni.** La review dava quattro famiglie, misurate su dieci semi.
  Rileggendo i checker uno per uno ne escono **sei**: le tre confermate
  (`MIN_DISTRIBUTION`, `FREE_GUARANTEED`, `IMPOSED_SUCCESSION` in **entrambi**
  i rami) più `MAX_GAP_HOURS` — il buco è `ultima − prima + 1 − conteggio`,
  quindi piazzare *dentro* un buco lo **riduce** — e tre casi di **deriva
  d'identità**: `WEEKLY_ORDER` (il finding nomina l'argmin), i quattro
  `PARTS_*` (nomina l'intero secchio) e `structural:didactic_weight` (nomina
  tutte le attività dell'unità, quindi un piazzamento di lunedì rikeya la
  violazione di venerdì). ⚠ Le ultime quattro **la misura non le vede**: hanno
  bisogno di un'attività **congelata** per manifestarsi, e il banco a testimone
  non congela niente — lo stesso buco che il 2026-08-26 (sera) aveva già
  costretto a costruire il banco che congela per il solver. La stessa cecità,
  su un banco diverso, sei giorni dopo.
  ⚠ E in senso opposto: `ARRIVAL_DEPARTURE`, la quarta dell'elenco, **non lo
  è**. La prova è per lettura del checker: `compliant` è **non crescente** sotto piazzamento, per due
  ragioni indipendenti: una giornata **vuota** contribuisce 1 e piazzandoci
  può solo restare 1 o passare a 0; una giornata **già occupata** ha `slots[0]`
  che può solo calare e `slots[-1]` che può solo crescere, quindi le due
  condizioni `>= not_before` e `< not_after` possono solo passare da vero a
  falso. Nessuna riparazione è possibile, e ogni cambio di chiave è un
  peggioramento causato dalla prova.
  Resta monotona, e la divergenza è dichiarata invece che appianata.
  ⛔ **E la misura che avevo messo a sostegno era vacua** — «marcandola non
  monotona, zero semi su quaranta cambiano esito» **non poteva dare altro
  risultato**: marcare una famiglia non monotona *allarga* i domini, e
  l'oracolo attende zero finding, quindi quel verde era incapace di fallire in
  entrambe le direzioni (42 passed con e senza). È la settima forma di vacuità
  di questo progetto, dentro la voce che si congratula di averle imparate a
  riconoscere — scritta qui invece che tolta in silenzio.
  ⚠ La misura **simmetrica** invece dice qualcosa: rimettere `MaxGapChecker` a
  monotono lascia anch'esso 42 passed, e lì il verde *poteva* fallire (marcarlo
  restringe i domini). Quel dato non è vacuo: è la misura di una **cecità del
  banco**, non di una proprietà del checker.
  ⚠ Su `WEEKLY_ORDER` e sui quattro `PARTS_*` il rilassamento costa richiamo e
  **oggi non compra precisione**: i loro builder trattano ADR-018 vietando ai
  liberi il secchio già sporco, quindi rispondono `INFEASIBLE` esattamente dove
  il dominio non rilassato si svuotava — misurato, ed è il motivo per cui i due
  test corrispondenti hanno il **checker** come metro e non il solver. Si
  rilassano lo stesso, perché `PLACEMENT_MONOTONE` è una proprietà del
  *checker*: legarla alla scelta di un builder metterebbe in `domain/analysis`
  una dipendenza dal solver — quella che il package esiste per non avere.

  **Ogni marcatura è verificata per mutazione**: rimettendo `True` su una sola
  famiglia, il test di *quella* famiglia diventa rosso e nessun altro (sette
  mutazioni, sette esiti distinti). E il banco morde anche nel verso opposto,
  che con una correzione fatta *restringendo ciò che si scarta* è il rischio
  vero: `analyze_hall` sostituita da `return []` incondizionato lascia **12
  test rossi** fra i quattro file della fase 5.

  ⚠ **Il costo è lineare nel numero di firme, e il numero dichiarato veniva
  dall'unico dataset che ne ha una sola.** Il Fermi ha **una** firma di
  settimana, quindi «~0,4 s, è anzi la più veloce delle famiglie di analisi»
  era una conclusione generale tratta dalla dimensione che il dataset non
  esercita — mentre §2 della spec chiama le firme *«una dimensione, non un
  dettaglio»*. Misurato aggiungendo indisponibilità **datate** (il meccanismo
  reale: le assenze): 1 firma 0,34 s · 3 firme 0,99 s · 6 firme 1,88 s ·
  11 firme 3,25 s · 21 firme 5,98 s — circa **0,3 s per firma**. Un anno reale
  ha 35-40 settimane, quindi nel caso limite **~10-13 s** sul Fermi. Resta
  accettabile per una fase diagnostica lanciata a mano, e `--no-hall` esiste
  apposta; ma va letto come «0,3 s per firma», non come un numero assoluto.
  Spec e nota di stato corrette in loco.

  **Chiusi nello stesso giro** i minori della review: il caveat degli archi a
  ∞ nel docstring di `_deficient_set` (§3.2 lo imponeva testualmente);
  `_labels` che deduplica per nome — senza, gli atomi di ADR-017 ripetevano il
  nome della classe una volta per atomo più una per `ClassPart`, e su una
  scuola vera la frase diventava illeggibile, che è l'UX del finding, cioè il
  punto del pezzo; i due `assert` mancanti (`findings == []` sul Fermi,
  `activities` sulla riduzione). E la decisione **dichiarata** sui due
  guardiani che si potevano togliere lasciando la suite verde: `required <=
  capacity` e il clamp `max(0, base - used)` sono **entrambi irraggiungibili
  per costruzione** — il primo perché con gli archi centrali a ∞ il lato
  sorgente del taglio minimo soddisfa sempre la disuguaglianza e `_reduce` la
  preserva; il secondo perché ogni cella che arriva a `_cell_capacity` è
  passata per `admissible_starts`, dove `structural:occupation` (monotono,
  quindi presente anche col rilassamento) scarta le celle sature. **Restano
  entrambi**, col perché nel docstring: il primo è la §3.3 della spec, cioè un
  argomento sui grafi residui trasformato in postcondizione controllata; il
  secondo è l'ultima porta prima di Dinic, dove una capacità negativa non
  fallirebbe — produrrebbe un certificato che non torna, in silenzio.

  **Suite a fine lavoro**: `venv/bin/pytest -q` → **525 test verdi**, 16 skip
  in ~85 s.

- **2026-08-26 (notte, pezzo 3 — ondata 7)** — **`manage.py solve`, e il pezzo
  3 è chiuso.** Il comando nella forma di `analyze`: stato, dimensioni del
  modello, i **criteri in ordine di priorità** con valore, se l'ottimo è
  dimostrato e quanto è costato, e gli scarti **nominati** uno per uno con
  materia, classe e docente — non «infeasible», ma *chi* è rimasto fuori.
  ⚠ Non scrive niente senza `--applica`: un solve sovrascrive l'orario di una
  scuola, e il default non può essere scrivere. Exit code ≠ 0 se resta qualcosa
  di scartato, come `analyze`; e dopo `--applica` le **violazioni residue** si
  dichiarano, perché un orario illegale è uno stato ammesso.

  🔑 **E il comando ha trovato un difetto della catena.** Sul Fermi L2 costava
  **4,07 s** contro gli 0,47 s di L1 — per riscoprire lo stesso orario da zero.
  Ogni livello ripartiva senza sapere nulla del precedente. Con la soluzione
  del livello concluso passata come **suggerimento**: 0,27 s, e il totale del
  comando da 4,9 s a **1,2 s**. ⚠ `AddHint` accumula, quindi `ClearHints`
  prima — senza, a quattro livelli il proto porta quattro copie dei
  suggerimenti; un test lo tiene fermo contandoli.

  **Il pezzo 3 è completo**: sette ondate su sette. Suite: **493 test verdi**,
  16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 6)** — **L4: la stabilità fra
  periodi.** L'ultimo livello minimizza le attività che cambiano cella rispetto
  ai `Placement` esistenti. È la conseguenza di [ADR-010](docs/decisioni.md)
  rimasta scoperta da luglio — rigenerando l'orario a ogni periodo serve un
  criterio «mantieni il più possibile le collocazioni precedenti», o il secondo
  quadrimestre viene stravolto per tutti — ed è anche ciò che EDT minimizza nel
  risolutore passo-passo. Come previsto da D4, è costato un `minimize`, non
  un'architettura.

  ⚠ **Ultimo, e l'ordine è provato da un test**: conservare una collocazione
  non vale uno scarto. ⚠ E il primo test scritto per quella proprietà **non
  discriminava** — due ore accatastate nella stessa cella danno un movimento in
  entrambi gli ordini, perché anche scartare un'attività già piazzata conta
  come spostamento. Riscritto su un'istanza dove i due ordini danno risposte
  diverse: con L1 prima si piazzano entrambe e la vecchia si sposta; con L4
  prima la vecchia resta e la nuova viene scartata.

  Suite: **486 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 5)** — 🔑 **L3, e il debito di §9.7
  chiuso da una misura.** Il terzo livello della catena conta le **violazioni
  nuove** che il modello si concede: le quote consumate e le riparazioni
  mancate dei rami disgiuntivi di ADR-018. Due conteggi distinti sommati in un
  livello solo — un conteggio, non una somma pesata — e restano separati dove
  conta: una riparazione mancata **non consuma quota**, perché non è un
  alleggerimento.

  **Il debito era testuale**: «il modello non ha funzione di costo, quindi
  `riparato` e `riparato.Not()` sono alla pari e CP-SAT non ha motivo di
  preferire la riparazione». Adesso ne ha uno. Non cambia cosa il modello
  ammette — cambia cosa preferisce — ed era la quarta strada, quella senza
  rischio semantico, delle tre che §9.7 elencava senza adottarne nessuna.

  ⚠ **E la prova non è un argomento, è una misura**: dopo L3 il ramo pigro non
  compare più su **60 semi** del banco che congela, dove prima c'era ai semi
  20, 35, 41, 45 e 52. Quindi **l'esenzione che lo perdonava è stata rimossa**
  da `_classifica_nuove`, insieme al test che la esercitava — un'esenzione che
  non scatta mai non è un'esenzione, è codice che nessun test afferma. Il banco
  è ora **più severo di prima**: se il fenomeno tornasse diventerebbe rosso
  invece di perdonarlo in silenzio, e rimetterlo sarebbe una decisione da
  prendere guardando la misura.

  ⚠ **Il primo test scritto per L3 non discriminava**, ed è la solita forma:
  provava che il solver *ripara*, ma senza L3 il solver può riparare **per
  caso** — misurato, restava verde con la mutazione. Sostituito da due test sul
  valore del livello: la riparazione mancata contata quando riparare è
  impossibile (una griglia di due giorni con `min_days=3`), e la quota non
  consumata quando non serve. Tre mutazioni, tre rossi, ciascuno sul test
  giusto.

  Suite: **484 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 4)** — **I pre-filtri, e il task che
  aveva la premessa sbagliata.** L'ondata era scritta come «le quote nei
  pre-filtri». Controllando i documenti **prima** di scrivere il codice, la
  premessa è caduta: in EDT l'indisponibilità **rossa non si alleggerisce
  mai**, e la **gialla si rispetta come la rossa** — l'utente può autorizzare
  il motore a ignorarla, ma con un'**opzione di calcolo per categoria di
  risorsa** («Piazza le attività anche sulle fasce con indisponibilità
  opzionali», declinata sulle cinque risorse), mai selettiva sulla singola.
  Non è una quota. È §9.8 di nuovo, stavolta su un piano scritto poche ore
  prima.

  ⚠ **E la verifica ha trovato un difetto vero: il solver era più permissivo
  di EDT su una famiglia intera.** Il pre-filtro ignorava il giallo del tutto —
  si comportava come se l'override fosse sempre acceso — e **il test che
  c'era affermava il comportamento sbagliato**, chiamandosi
  `test_giallo_e_verde_non_restringono`. Ora il giallo restringe come il
  rosso, l'override è il parametro `ignora_opzionali` per `Resource.Kind`, e
  il verde resta fuori: è una preferenza, e il suo posto è un livello di
  qualità della catena, non un pre-filtro.

  ⚠ **Due famiglie dell'enum non sono quote**, e ora è dichiarato invece che
  implicito: `UNAVAILABILITY` e `OPTIONAL_UNAVAILABILITY` restano nello schema
  approvato ma nessun builder le consulta. Un test lo tiene fermo — con una
  quota da cinque violazioni sull'indisponibilità rossa, il modello resta
  `INFEASIBLE` — così che chi volesse renderle quote debba prima cancellarlo e
  leggerne il perché.

  Suite: **483 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 3b)** — **Tutte le famiglie
  alleggeribili.** Agganciate le restanti: presenza massima, massimo di mezze
  giornate (tetto **e** «solo mezza giornata al giorno», che è una deroga),
  entrate/uscite, giorni e mezze giornate libere, cambi di sede, peso
  didattico, massimo di ore di una materia e sequenze indesiderate.

  ⚠ **Sulle soglie il margine si sottrae, e va al ramo giusto.** «Togli se
  necessario … mezze giornate libere per settimana» abbassa la soglia; ma nel
  ramo disgiuntivo di ADR-018 si applica **solo** alla riparazione, mai allo
  status quo — quello non è una soglia da alleggerire, è il divieto di
  peggiorare rispetto alla baseline, e alleggerirlo autorizzerebbe un
  peggioramento del passato, che è un'altra cosa da quella che la finestra di
  EDT concede.

  ⚠ **Un letterale per riga, non per parametro.** Presenza (minuti + giorni),
  giorni liberi (giorni + mezze), sedi (per giorno + per settimana): sono due
  parametri dello stesso alleggerimento, e due quote consumate per una sola
  concessione sarebbero state un errore che nessun test avrebbe visto.

  ⚠ **Le righe di materia sono tre famiglie, non una.** La finestra di EDT le
  tiene distinte — `Incompatibilità materie`, `Massimo di ore delle materie`,
  `Sequenze indesiderate di materie` — con quote separate, e il nostro enum ne
  aveva una sola: aggiunte `SUBJECT_MAX_HOURS` e `SUBJECT_SEQUENCE`
  (migrazione `0009`). Condividere una quota fra un margine e una deroga
  sarebbe stata una deviazione silenziosa dal prodotto.

  🔑 **E l'ondata 1 ha reso falso un argomento scritto in `weight.py`.** Il
  salto sul secchio settimanale inevadibile era giustificato dal fatto che «la
  somma dei letterali liberi è una costante» — vero solo con `AddExactlyOne`.
  Ora non lo è più: il clamp non sarebbe *contraddittorio*, sarebbe la pretesa
  che il presente **scarti** per espiare il peso del passato. La conclusione
  regge, l'argomento no, e il commento è stato riscritto invece di lasciarlo
  invecchiare. Stessa sorte per il commento di `post_separable` e per quello
  del peso, che citavano `AddExactlyOne` per una proprietà che oggi discende
  da `piazzata`.

  **Quindici test su diciassette cadono** con una sola mutazione — il
  meccanismo che non concede niente — e i due che restano verdi sono quelli
  che devono restarlo: «senza righe il modello è quello di prima» e «una quota
  a zero è come non averla». Suite: **481 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 3a)** — **Le quote: un vincolo
  rilassabile non diventa soft.** `domain/solver/relaxation.py`, il meccanismo
  e due famiglie. Istruzione letterale del prodotto: *«Sbloccate i vincoli da
  alleggerire e selezionateli per quantificare il margine di manovra concesso
  al calcolo»* — non esiste «spegni il vincolo», resta hard con un numero
  massimo di violazioni attribuito per famiglia e per risorsa.

  **Due forme, perché le righe della finestra `Alleggerimenti` sono di due
  tipi**: il **margine**, dove il vincolo si allarga di una quantità dichiarata
  (`expr <= tetto + margine·v`), e la **deroga**, dove semplicemente non si
  considera per quell'occorrenza (`OnlyEnforceIf(v.Not())`). Agganciate
  `MAX_HOURS` (margine) e le tre incompatibilità di materia (deroga), queste
  ultime in **entrambi** i rami `post_separable` e `post_cross`: alleggerirne
  uno solo avrebbe lasciato metà famiglia scoperta senza che un test se ne
  accorgesse.

  ⚠ **Lo schema è cresciuto di due campi, ed era un buco di modellazione già
  segnalato dalla spec**: `RelaxationQuota.params` (il *quanto*, che mancava
  accanto al *quante volte*) e `InstituteSettings.max_relaxed_constraints_per_resource`
  (il tetto globale «numero massimo di vincoli da alleggerire per risorsa»).
  Più `ARRIVAL_DEPARTURE` fra le famiglie: in EDT `Gestione Entrate / Uscite`
  è alleggeribile e non c'era. Migrazione additiva, nessun dato da riscrivere.

  🔑 **Un vincolo alleggerito resta una violazione nominata.** `check_schedule`
  continua a produrre il suo finding `HARD`, ed è il comportamento di EDT —
  l'orario risolto della base di esempio conteneva 21 attività su 984 che non
  rispettavano i vincoli, e il prodotto continuava a lavorare. La quota non
  nasconde la violazione: autorizza il solver a produrla, in numero limitato.
  Un test lo tiene fermo, contando i finding dopo il solve.

  ⚠ **Il margine si somma al *residuo*, non al tetto grezzo**, ed è il punto in
  cui questo pezzo poteva sbagliare in silenzio: alleggerire concede spazio
  **sopra lo stato corrente**, mai la pretesa che il passato venga riparato
  (ADR-018). Misurato per mutazione — con `cap + margine` al posto di
  `residuo + margine` due libere entrano dove ne entra una sola, e il test
  diventa rosso.

  **Sette mutazioni, sette rossi**: quota non postata, tetto globale non
  postato, margine decuplicato, quota a zero trattata come quota, deroga
  sempre assente, deroga tolta da `post_cross`, margine sul tetto grezzo.
  Suite: **472 test verdi**, 16 skip.

  Restano le famiglie dell'ondata 3b — presenza, mezze giornate, giorni
  liberi, entrate/uscite, sedi, peso didattico e le altre righe di materia —
  e le quote nei pre-filtri (ondata 4), che è il caso storto.

- **2026-08-26 (notte, pezzo 3 — ondata 2)** — **La catena lessicografica.**
  `domain/solver/objective.py`: risolvi per il criterio 1, **fissa** quel
  valore, passa al 2 — mai una somma pesata. Due livelli, L1 le ore scartate e
  L2 il loro numero come spareggio (D1), il fissaggio a `<=` e non `==`, il
  limite di tempo **per livello** (una catena di quattro livelli con
  `time_limit=60` può spendere quattro minuti: va detto, non scoperto), e gli
  `stats` che riportano ogni livello con nome, valore, **se l'ottimo è stato
  dimostrato** e quanto è costato.

  🔑 **La strategia a due passate di EDT è questa catena, non due esecuzioni.**
  «Il piazzamento rispetta tutti i vincoli; se restano attività scartate,
  potete alleggerire» è «L3 dopo L1»: si consuma un alleggerimento solo quando
  riduce gli scarti, perché a scarti pari il livello dopo preferisce zero
  violazioni.

  ⚠ **E la mutazione ha bocciato il test del meccanismo centrale.** Il primo
  test di monotonia usava un'istanza a **pareggio** — un blocco da 2h contro
  due ore singole — dove L1 e L2 indicano la stessa risposta: togliere
  `model.Add(level.var <= valore)`, cioè il fissaggio, lasciava la suite
  **verde**. Riscritto su un'istanza in cui i due livelli tirano in direzioni
  **opposte** (quattro fasce, un blocco da 3h più tre ore singole: L1 vuole
  fuori due ore in due attività, L2 vorrebbe fuori tre ore in una sola), dove
  la mutazione diventa rossa.

  ⚠ **Due rami che nessun test poteva affermare**, e la cucitura che li rende
  affermabili: un livello che **non conclude** (la catena si ferma, ma
  restituisce la fotografia dell'ultimo livello concluso invece di buttare via
  il lavoro) e uno che **non dimostra** l'ottimo. Farli scattare con un limite
  di tempo stretto sarebbe stato un test flaky su una macchina più lenta: da
  qui `solve_chain(solver=...)`, con due solver finti di sei righe. Entrambe le
  mutazioni corrispondenti diventano rosse.

  ⚠ **I due fenomeni del banco sporco si sono spostati per la terza volta**, ed
  era prevedibile: sono proprietà della **soluzione restituita**, e ogni ondata
  cambia l'obiettivo. Invece di ri-appuntare un seme, i due test ora
  **cercano** il fenomeno su una lista dichiarata — provando più semi dentro
  lo stesso test con un `transaction.atomic` annullato, perché ricostruire la
  scuola due volte nella stessa transazione violerebbe l'unicità delle
  anagrafiche. Il test afferma così la cosa che conta — *l'esenzione è
  esercitata da qualcosa* — invece di una coincidenza fra un seme e una
  configurazione del solver.

  ⚠ **Un difetto introdotto e colto dai test dell'ondata 1**: `unplaced`
  calcolato solo `if placements` faceva sparire lo scarto proprio nell'istanza
  in cui l'unica attività è impiazzabile — la distinzione è fra «nessuna
  soluzione» e «una soluzione senza piazzamenti», e va fatta sul `None`.

  **I numeri.** Fermi: `OPTIMAL`, zero scarti, due livelli conclusi e
  dimostrati, **8426 variabili e 1086 constraint** — +1 variabile per L2, +2
  constraint per le uguaglianze dei livelli e +2 per i fissaggi che la catena
  aggiunge percorrendola. Suite: **464 test verdi**, 16 skip, **92 s** contro i
  74,8 di ieri: è il costo di due solve per istanza invece di uno, ed è la
  ragione per cui il limite di tempo è per livello.

- **2026-08-26 (notte, pezzo 3)** — **Il modello smette di pretendere il
  piazzamento.** Comincia il **pezzo 3** — alleggerimenti a quota e
  ottimizzazione lessicografica — con la spec
  ([design](docs/superpowers/specs/2026-08-26-alleggerimenti-lessicografico-design.md))
  e le sue quattro decisioni chiuse in sessione: **L1 conta le ore** (il numero
  di attività è lo spareggio), lo scarto è **`HARD`**, il ramo pigro di §9.7 si
  chiude dentro **L3**, la stabilità fra periodi è **L4** di questa catena. Poi
  la prima delle sette ondate: `AddExactlyOne` diventa
  `somma(celle) == piazzata`, e ciò che non ci sta resta **scartato** invece di
  rendere infattibile tutto l'orario.

  ⚠ **Lo scarto va nominato, o l'oracolo diventa vacuo** — previsto scrivendo
  la spec, non scoperto dopo. In `domain/analysis` non esisteva alcuna causale
  sul non-piazzamento e nessun checker guardava le attività prive di
  `Placement` (l'occupazione si costruisce **dai** piazzamenti): appena cade
  `AddExactlyOne`, «scarta tutto» è una soluzione con zero occupazioni, zero
  findings, verde. Da qui `structural:placement`. **Il registro ha ora 28
  checker e 26 builder**, e la seconda assenza è dichiarata da un test come la
  prima: la traduzione dello scarto esiste — è `somma(celle) == piazzata` — ma
  non è un builder, perché crea le **variabili di decisione** e deve esistere
  prima che qualunque builder giri (`vocabulary.pos` la legge).

  🔑 **Il «tetto inevadibile» di §9.5 era inevadibile per colpa di
  `AddExactlyOne`.** L'argomento diceva che le libere «vanno collocate, e
  ovunque vadano pesano»: vero solo finché il piazzamento è obbligatorio. Con
  `somma(celle) == piazzata` la somma dei letterali liberi torna a dipendere
  dalle decisioni, e il tetto settimanale del peso didattico torna evadibile
  **nel modo in cui lo evade EDT: scartando**. La chiave grossolana per le
  famiglie indipendenti dal piazzamento diventa una scelta invece di un
  obbligo. ⚠ Resta la metà delle congelate, che è un fatto e non una decisione.

  ⚠ **E la regola della casa cambia forma.** «Forza la violazione e attendi
  `INFEASIBLE`» smette di funzionare: con lo scarto ammesso la risposta a una
  violazione forzata non è l'infattibilità ma la **rinuncia** — misurato,
  `OPTIMAL` con esattamente uno scarto in 23 test su 27 rossi. Da qui
  `build_model(allow_unplaced=False)`, che è il modello di prima e resta il
  modo di chiedere «questo vincolo morde?». I 23 test lo usano; la domanda che
  ponevano è intatta.

  ⚠ **Il banco a testimone si era indebolito in silenzio**, ed è la forma
  vecchia del difetto nuovo: cancella i piazzamenti, risolve e controlla che la
  soluzione sia pulita per la famiglia — ma **una soluzione che scarta è pulita
  per qualunque famiglia**, perché un'attività non piazzata non viola niente.
  Il testimone esiste, quindi l'ottimo è zero scarti: preteso in tre punti
  (`run_family`, `run_tutte_le_famiglie`, prova B del banco che congela).

  🔑 **La presolve espandeva l'obiettivo, e il banco ci passava dentro senza
  accorgersene.** Quattro test del testimone erano passati da ~0,5 s a **60 s
  esatti** — il limite di tempo — restando verdi. Il log lo dice per nome:
  *«objective: expanded via tight equality»*, 36 volte su un testimone da 32
  attività. I 32 booleani `piazzata` spariscono dall'obiettivo e al loro posto
  entrano **723 letterali di cella**; il dominio iniziale passa da `[0, 660]` a
  `[-35460, 2040]`. Il solver trova `best:0` in un decimo di secondo e poi
  spende un minuto a dimostrare che non esiste un ottimo negativo — vero per
  costruzione, ma non più per lui. Con `presolve_substitution_level = 0`:
  **`OPTIMAL` in 0,09 s**. ⚠ Il dominio dichiarato di un `IntVar` da solo
  **non basta** (misurato: bound −720, tempo pieno), e nemmeno `AddHint` sui
  `piazzata` (nessun guadagno: rimosso, perché un meccanismo che nessuna misura
  giustifica è peso morto).

  ⚠ **I due fenomeni del banco sporco dipendono da *quale* ottimo torna, e
  CP-SAT in parallelo non è riproducibile.** La deriva d'identità e il ramo
  pigro si sono spostati di seme due volte in una sessione — una per
  l'obiettivo, una per la presolve — e la prima volta erano **verdi da soli e
  rossi nella suite intera**. Non era il seme: con più lavoratori CP-SAT
  restituisce l'ottimo che il primo thread trova. Da qui `workers=1` nella
  prova B (e il parametro su `solve()`); rimisurati due volte di fila con lo
  stesso esito, il ramo pigro sta al **20** (e al 35, 41, 45, 52), la deriva
  d'identità all'**11**, unica su sessanta semi.

  ⚠ **Due mutazioni hanno bocciato metà del lavoro nuovo, di nuovo.** Il test
  su `apply()` che cancella il piazzamento di ciò che è stato scartato
  **restava verde** con la cancellazione rimossa: l'attività scartata non aveva
  una riga da cancellare. E i due guardiani di `pos` — la sentinella «oltre la
  griglia» e la guardia del builder d'ordine — erano coperti da **un solo**
  test che nessuna delle due mutazioni faceva diventare rosso, perché in
  quell'istanza ciascun meccanismo bastava da solo. Separati in due test, uno
  per meccanismo, ciascuno ucciso dalla propria mutazione.

  **I numeri.** Fermi: `OPTIMAL`, **zero scarti**, 0,74 s, **8425 variabili e
  1083 constraint** — la differenza dai vecchi 8140/1082 è tutta la macchina
  dello scarto, contata: +284 booleani `piazzata`, +1 per i minuti scartati, e
  sui constraint il solo +1 dell'obiettivo (i 284 `AddExactlyOne` sono
  diventati 284 uguaglianze). Suite: **458 test verdi**, 16 skip, e il tempo
  totale è **quello di prima** (74,8 s contro 74,6 s) — che è il vero verdetto
  sulla riparazione della presolve.

- **2026-08-26 (notte)** — **La review della PR #1, e il gemello del difetto
  nella famiglia che il banco non poteva vedere.** Quattro rilievi sistemati
  sopra il banco che congela.
  🔑 **`OccupationBuilder` aveva lo stesso difetto di `SiteTransitionBuilder`,
  ed è la conferma che «tocca» contro «realizza» è un pattern, non un
  incidente.** Il gate `any_free` guarda chi tocca la cella, non chi ne
  realizza la saturazione: due congelate in conflitto su una cella che una
  libera può toccare producevano `costante + libere <= capienza` con la sola
  costante oltre il tetto — `INFEASIBLE` per colpa del solo passato, con il
  checker che quello stato lo prevede e lo nomina (`resource_occupied_locked`,
  HARD). Corretto con `residual_cap`, come tutti gli altri tetti. ⚠ **Il banco
  che congela non poteva trovarlo**: `sporca()` ripacka solo in celle libere da
  conflitti di occupazione e lo asserisce, quindi la famiglia esclusa per
  costruzione dal banco è proprio quella in cui il difetto è sopravvissuto. La
  chiusura di Ruling 20 resta valida, ma **non è totale**: un banco ha sempre
  una cecità, e va detto dove.
  ⚠ **Metà del guardiano nuovo non era asserita da niente.** Misurato:
  rimuovendo il solo `continue` del ramo `s == t` di `SiteTransitionBuilder` e
  lasciando l'altro, la suite intera restava verde. Aggiunto il test del ramo
  (`test_adr018_site_transition_due_sedi_gia_sulla_stessa_fascia_non_blocca`),
  che è raggiungibile solo a capienza simultanea > 1. Entrambi i test nuovi
  sono **verificati per mutazione**: senza la correzione diventano rossi.
  ⚠ **Le due prove del banco passavano su `UNKNOWN`.** `!= INFEASIBLE` non è
  `in (OPTIMAL, FEASIBLE)`: al timeout la prova A passava senza soluzione, e la
  prova B pure — con i piazzamenti vuoti `apply()` è un no-op dichiarato e
  l'oracolo differenziale confrontava la baseline pre-solve con sé stessa.
  Verde per non aver misurato niente, cioè il criterio con cui questa stessa
  sessione aveva bocciato `test_famiglia_con_congelate`. Corretto in entrambe.
  Corretta infine una contraddizione interna: «Ancora aperto» dava
  `free_guaranteed` in peggioramento da 2 mezze giornate a 1, mentre la misura
  (spec §9.7) è uno **scambio** — `free_days 4 / free_half_days 1` →
  `free_days 1 / free_half_days 4`. **450 test verdi**, 16 skip.

- **2026-08-26 (sera)** — **Il banco congela, e il primo builder a cadere è
  quello che si dichiarava già a posto.** Chiude il debito che §9.7 chiamava
  «il buco strutturale più grande che resta» (Ruling 20): fino a qui **nessun
  test del banco congelava niente**, quindi in ogni modello che il banco
  costruiva `ctx.free` conteneva tutto — `split()` con `frozen = 0` sempre,
  `any_free` sempre vero, `frozen_occupies` sempre falso, `residual_cap` che
  non clampava mai, i rami disgiuntivi mai imboccati. Tutta la copertura di
  ADR-018 poggiava sui test scritti a mano.

  **La costruzione.** Si genera il testimone pulito, si derivano le righe di
  **tutte** e ventisei le famiglie, poi si **ripacka**: alcune attività si
  spostano in celle libere da conflitti di occupazione — «libere da conflitti»
  non è cosmetico, è ciò che lascia il resto dell'orario dov'è. Chi risulta
  **implicato** nelle violazioni così create viene congelato; gli altri restano
  liberi e i loro piazzamenti si cancellano. Il risultato è letteralmente la
  premessa di ADR-018: congelate **già in violazione**, libere da piazzare.

  🔑 **La prova che morde è la prima, non l'oracolo.** Si **forza** ogni libera
  nella cella dove il testimone la teneva e si attende che il modello non
  risponda `INFEASIBLE`. Quell'assegnazione non aggiunge niente — per
  costruzione, perché la baseline è calcolata su di essa e ogni attività
  implicata è congelata — quindi rifiutarla è *pretendere una riparazione*, la
  metà vietata del criterio di ADR-018. È la forma della casa (forzare e
  attendere uno stato), applicata a un modello intero invece che a una riga.

  ⚠ **`SiteTransitionBuilder` non aveva il guardiano ADR-018 che due commenti
  gli attribuivano.** Trovato al seme 38, ridotto alla forma minima in
  `tests/test_solver_sites.py`. `any_free` guarda chi **tocca** le due fasce,
  non chi **realizza** la coppia di sedi vietata: due congelate di sede diversa
  a distanza insufficiente sono già una violazione, ma basta una qualunque
  libera che tocchi una delle due fasce perché la clausola venga postata — e
  quella clausola ha **entrambi** i letterali forzati a 1 dalle congelate.
  `INFEASIBLE` per colpa del solo passato. Il commento di
  `builders/time_sites.py` diceva «ha già ADR-018 nella forma della regola
  dell'implicazione (`any_free`): non toccato», e il docstring di
  `test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca` lo ripeteva.
  **Il pattern di questo progetto per la tredicesima volta**, e stavolta l'ha
  trovato una misura, non una rilettura. Corretto con `_sede_congelata`, che
  rispecchia **letteralmente** la selezione dei letterali di
  `Vocabulary.site_occupied` — leggere il codice invece del proprio ricordo è
  la stessa regola che vale per `B` nei rami disgiuntivi.

  🔑 **E la mutazione ha bocciato metà del lavoro.** Il banco nasceva con
  **due** parti: oltre a quella sporca, un `test_famiglia_con_congelate` che
  congelava una parte del testimone dov'è, famiglia per famiglia, su baseline
  pulita — 78 test, 28 secondi, i due terzi del tempo aggiunto. Su **sette**
  mutazioni della macchina ADR-018 non è diventato rosso **una sola volta**,
  mentre il banco sporco le ha colte su **sei** delle sette (`split` 4 rossi,
  congelate a dominio pieno 8, `any_free` 2, `_sede_congelata` 1,
  `_status_quo_rappresentabile` 1, `frozen_occupies` 1 — e **zero** entrambi
  sul clamp di `residual_cap`, che resta difeso dai soli test scritti a mano).
  Rimosso: un test che non diventa rosso quando il codice che afferma sparisce
  non sta affermando niente. ⚠ Il banco **non sostituisce** i test a mano —
  aggiunge la sola cosa che nessuno di loro sapeva fare, trovare un difetto che
  nessuno cercava.

  **Due esenzioni dichiarate, entrambe misurate, entrambe esercitate da un test
  apposta.** ⚠ La prima estende §9.5 oltre le famiglie indipendenti dal
  piazzamento: la **deriva d'identità**. Diverse famiglie non nominano in
  `activities` il secchio intero ma la **coppia argmin** o la coppia
  consecutiva — chi viola, non chi partecipa; piazzare una libera accanto a una
  congelata cambia allora *quale* coppia è l'argmin senza cambiare la
  violazione. Misurato al seme 20: `subject_imposed_succession` sulla risorsa 1
  passa da `(5, 7)` a `(4, 5)` con `gap 3 / max_gap 2` **identici**. È la stessa causa a monte del
  tie-break di `_placed_of` già in «Ancora aperto».
  La seconda è il **ramo pigro** di §9.7, per la prima volta misurato invece
  che dichiarato — e con una forma più precisa di quella descritta lì: è uno
  **scambio**, non un peggioramento secco. Al seme 20 `free_guaranteed` passa
  da `free_days 4 / free_half_days 1` a `free_days 1 / free_half_days 4`:
  ripara la soglia delle mezze (min 3) e rompe quella dei giorni (min 2), che
  era soddisfatta. Le due soglie stanno sotto **lo stesso** booleano proprio
  per impedirlo (correzione del 2026-08-26 mattina), ma con le libere non
  ancora piazzate lo status quo non è rappresentabile, il ramo scende a `>= 0`
  e scavalca il booleano. Perdita di qualità, non di correttezza:
  l'esenzione è stretta apposta — una violazione su una risorsa **pulita**
  resta rossa anche per quelle tre famiglie.

  ⚠ **E un docstring del banco è stato falsificato entro l'ora.**
  `run_family_congelata` dichiarava «la baseline resta pulita»: falso.
  Cancellando i piazzamenti delle libere, le famiglie che contano una quantità
  *presente* — successione imposta, minimi, distribuzione — sono violate
  proprio **perché manca qualcosa** (misurato: `imposed_succession` al seme 3,
  finding `(2,) max_gap 2` già prima del solve). Il criterio giusto è il
  **contenimento** rispetto alla baseline pre-solve, non `== set()`.

  **Osservazione a margine, non risolta**: `residual_floor` non è chiamato da
  **nessun** builder — solo dal proprio test. I minimi di §3.1 non sono mai
  stati trattati per sottrazione di termini: i cinque casi di ADR-018 usano
  `frozen_occupies` o la disgiunzione reificata. È il gemello documentale di
  `residual_cap`, non codice morto per distrazione, ma va detto.

  **I numeri.** Su 40 semi, **36** producono una costruzione sporca
  utilizzabile (saltano 13, 14, 17 e 28: le violazioni implicano quasi tutto e
  restano meno di tre libere) e la dirt copre **26 causali distinte**. Dieci
  semi entrano nella suite, scelti per fenomeni diversi e non a caso; su quelli
  la costruzione **non può saltare**, così che una decadenza diventi rossa
  invece di svuotarsi in silenzio. Suite: **448 test verdi**, 16 skip.

- **2026-08-26** — **La review finale, e due builder che rifiutavano il
  presente.** Sei findings su tutte e ventisei le famiglie, con i seed allargati
  da 5 a 40. ⚠ **Il risultato più importante è positivo e va detto per primo**:
  **zero** builder più larghi del checker e **zero** più stretti del testimone.
  I difetti stanno su input **sporco** (ADR-018), copertura di test e vacuità
  del banco — non nella traduzione dei vincoli.

  **I due gravi erano lo stesso errore in due forme.**
  `MinDistributionBuilder` postava la soglia **grezza** pur avendo il
  controesempio scritto nella propria docstring: due congelate sullo stesso
  giorno, una libera, `min_days=3` → `INFEASIBLE` **anche forzando lo status
  quo**, cioè rifiutando un piazzamento che non introduce niente di nuovo.
  Spegnendo il solo builder, `OPTIMAL`. `FreeGuaranteedBuilder` clampava le due
  soglie **una per volta**, ma i due conteggi si escludono a vicenda —
  `libera = attivo AND NOT meta` conta una mezza solo se il giorno lavora,
  quindi un giorno che la soglia dei *giorni* obbliga a lasciare vuoto
  contribuisce **zero** mezze — e la congiunzione era irraggiungibile mentre
  ciascuna soglia da sola no. Entrambi passano alla **disgiunzione reificata**
  già in uso su `WeeklyOrderBuilder`, con le due soglie sotto **lo stesso**
  booleano. `B` si legge **chiamando il checker** di `domain/analysis`, mai
  riscrivendone la condizione: una divergenza di uno renderebbe il residuo
  peggiore del difetto. Misurato: status quo rifiutato 45/45 → **0** e 43/45 →
  **0**, `solve()` `INFEASIBLE` 33/45 e 16/45 → **0**, coppie (causale,
  risorsa) nuove **0** prima e dopo.
  ⚠ **ADR-018 ha quindi cinque casi, non quattro**, e la §9.5 della spec —
  scritta il giorno prima — **dichiarava vere due cose false**: che
  `FREE_GUARANTEED` fosse risolto dal residuo per forzatura e che
  `MIN_DISTRIBUTION` «reggesse davvero». Nessuna delle due si vedeva
  rileggendo il documento. È il pattern di questo progetto per l'ennesima
  volta, stavolta su un documento scritto da meno di ventiquattr'ore.

  🔑 **E la mutazione che avrebbe dovuto accorgersene non poteva.**
  `PartsHomogeneousHalfBuilder` non era difeso da **nessun** test: un `post()`
  no-op sulla sola sottoclasse `_H` lasciava la suite identica alla baseline,
  mentre le altre tre danno 5, 3 e 3 rossi. Tutte le mutazioni fatte fino a lì
  spegnevano `_PartsOrderBuilder.post`, cioè **tutte e quattro le sottoclassi
  insieme**: misuravano la base, non le foglie. **Corollario da portarsi
  dietro: quando un builder ha sottoclassi, la mutazione va fatta per
  sottoclasse.** Lo stesso corollario ha poi trovato un secondo buco —
  `_giorni_garantiti` sostituito da `resource_days` lasciava la suite verde,
  cioè il codice faceva una distinzione che nessun test affermava.

  **Settima forma di vacuità.** `_derive_max_gap` dichiarava «anche a budget
  zero è un vincolo vero»: falso, il buco è `ultima − prima + 1 − conteggio`,
  quindi serve una mezza giornata larga **almeno tre**, e la fixture pesca
  anche `(4, 2)` dove entrambe le metà sono larghe due. Otto righe inviolabili
  su 40 seed, e il **seed 2 era fra i cinque del banco** — un verde incapace di
  fallire. Ora salta onestamente: **uno skip in più, 15 → 16**, che è il numero
  giusto. E `_derive_two_days` era l'unico derivatore di materia senza la
  guardia di co-attività per firma; ⚠ `_coppia_violabile` **non** si può
  riusare, perché richiede lo **stesso** secchio mentre `TWO_DAYS` vuole
  l'opposto.

  **I quattro `parts_*` si invalidavano a vicenda**, e la precedenza fra
  derivatori introdotta al Task 17 non poteva proteggerli: tutti e quattro
  risintonizzano la **stessa** materia della **stessa** attività di parte, e
  non esiste un ordine che funzioni. Serviva un guardiano, non un riordino.
  Con `_sintonia_compatibile` la composizione passa da 34/40 a **40/40**
  puliti; le righe scendono da 48-73 a **36-76**, e il minimo cala perché i
  numeri di prima **includevano righe diventate vacue** — il sospetto che la
  review aveva segnalato senza quantificare era fondato.

  ⚠ **Debito nuovo, dichiarato e non risolto: il ramo status quo è pigro.**
  Senza funzione di costo i due rami sono alla pari, e nel solve incrementale
  con le libere non ancora piazzate la baseline è quasi sempre già violata
  perché **nulla è piazzato**: `B` vale quanto qualificano le sole congelate e
  il ramo diventa **vacuo**, cioè la riga smette di vincolare. Misurato. È
  perdita di qualità, non di correttezza, e va decisa sulla **famiglia** dei
  rami disgiuntivi — vedi «Ancora aperto» e §9.7 della spec.

  Suite: **436 test verdi**, 16 skip.

- **2026-08-25** — **Il modello hard completo: ventisei builder su
  ventisette.** Diciassette task sul branch `modello-hard-completo`, ciascuno
  scritto da un sottoagente su un brief e verificato per mutazione. Il registro
  dei builder è chiuso: la ventisettesima chiave (`structural:coverage`) non ha
  un builder **per costruzione** — è `PLACEMENT_INDEPENDENT`, confronta attività
  e servizi anagrafici e non guarda mai i piazzamenti, e il solver non crea né
  distrugge attività. L'assenza è **dichiarata da un test**
  (`tests/test_solver_registry_completo.py`), così che chi volesse aggiungerla
  debba prima cancellare il test e leggerne il perché. **436 test verdi**, 16
  skip tutti misurati e attribuiti.

  **Il vocabolario, e perché esiste.** I checker ragionano su quantità che i
  piazzamenti non contengono: «il docente lavora quel giorno», «quella mezza
  giornata è occupata», «la posizione della prima occorrenza di questa
  materia». Tradurle una per builder avrebbe prodotto ventisei definizioni
  incoerenti della stessa cosa. `domain/solver/vocabulary.py` le costruisce una
  volta sola — `occupied`, `day_active`, `half_active`, `pos` — memoizzate per
  chiave, e ⚠ **parametriche sulla firma di settimana**, che è la dimensione su
  cui questo progetto ha già sbagliato una volta.

  **ADR-018 nelle sue forme, che non erano due.** La spec ne prevedeva due —
  tetti (si clampa il residuo a zero) e minimi (nessun clamp, non sono mai
  infattibili per colpa del passato). Ne sono servite **quattro**.
  ⚠ I minimi **non** sono sempre innocui: su `ARRIVAL_DEPARTURE` e
  `FREE_GUARANTEED` una congelata in una fascia proibita **consuma** la
  quantità contata, e nessuna mossa sulle libere la recupera — corretto col
  residuo *per forzatura* (`frozen_occupies`), mentre `MIN_DISTRIBUTION` regge
  davvero, quindi l'asimmetria è reale e non generale.
  ⚠ E il caso che nessuno aveva previsto: il **tetto inevadibile**. Il secchio
  settimanale del peso didattico contiene *tutte* le celle candidate di ogni
  attività dell'unità, quindi `AddExactlyOne` rende la somma dei letterali
  liberi una **costante**: col residuo clampato a zero il vincolo diventa
  `costante positiva ≤ 0`, falso comunque vada il piazzamento. Non «inagibile»:
  **contraddittorio**. Il clamp, che altrove è il trattamento giusto, produce
  qui esattamente ciò che ADR-018 vieta — misurato, `INFEASIBLE` con due
  congelate e una libera. Il criterio che unifica i quattro casi è più preciso
  di «tetto o minimo»: **`INFEASIBLE` che nasce dal vietare un peggioramento è
  ammesso, `INFEASIBLE` che nasce dal pretendere una riparazione no.**

  **Il generatore a testimone.** Il banco genera **prima** un orario valido a
  caso, **poi** le righe di vincolo che quell'orario soddisfa, e solo allora
  chiede al solver di ricostruirlo da zero. Rende impossibile un oracolo vacuo:
  un builder che postasse `1 == 0` non trova il testimone, uno che non postasse
  nulla lascia passare un orario che il checker boccia. Ogni derivatore
  restituisce il proprio **potere vincolante** (quante righe ha creato), e zero
  fa saltare il seed invece di spacciarlo per un successo.

  **Le trappole trovate leggendo i checker invece di ricordarli.**
  `FREE_GUARANTEED` conta le mezze giornate libere **solo sui giorni con
  attività**, non su tutti; `MAX_PRESENCE` usa la **giornata intera** dove il
  D.T.B. usa la mezza; `_PartsOrder` bucketizza per giorno, ma
  `PartsHomogeneousHalfChecker` **sovrascrive** il bucket con la mezza giornata,
  e invertire le due cose non fa fallire niente di ovvio; `ImposedSuccession`
  non ha la guardia di vacuità che `WeeklyOrder` ha, quindi con B assente
  **ogni** occorrenza di A è in violazione. Nessuna di queste era nel piano.

  **I due conservativi previsti erano uno.** ⚠ `HALF_DAY_GAP` era il caso
  vetrina della sovra-approssimazione deliberata: si è rivelato **esatto**. Le
  due regole — coppie consecutive nel checker, tutte le coppie incrociate nel
  builder — sono equivalenti (dimostrato, e verificato su 200 000 casi sintetici
  con zero divergenze). Resta conservativo il solo `structural:site_transition`.
  A consuntivo: **venticinque builder esatti su ventisei**.

  **⚠ E la misura sul Fermi dice meno di quanto sembri.** `OPTIMAL` in ~0,56 s,
  284 attività, 8140 variabili, 1082 constraint — **gli stessi numeri, byte per
  byte, dello spike a cinque vincoli del 2026-08-09**. La ragione è che il
  dataset Fermi ha **zero** righe `ResourceTimeConstraint`, **zero**
  `SubjectConstraint` e i quattro tetti di peso a `None`: delle ventisei
  famiglie ne esercita cinque, e ventuno builder non postano nulla. «OPTIMAL sul
  Fermi col modello completo» è una frase vera e priva di contenuto, ed è ora
  scritta così nel test, con due assert che la tengono ferma.
  La misura vera è `test_modello_completo`, aggiunto qui: tutte le famiglie
  attive **insieme** sullo stesso testimone — 22–23 famiglie con righe su 26,
  48–73 righe, `OPTIMAL` su tutti e cinque i seed, oracolo pulito. Non esisteva:
  il banco provava ventisei modelli da una famiglia ciascuno, e due traduzioni
  corrette separatamente possono contraddirsi una volta postate insieme.

  **Comporre ha trovato una precedenza che nessuno aveva visto.** ⚠ I derivatori
  **non sono componibili in ordine qualunque**: due sono in formulazione densa e
  non osservano il testimone, lo **riparano**. `_derive_site_transition`
  riassegna le sedi — che sono ciò che `max_site_changes` conta;
  `_sintonizza_parti` riassegna la materia — che è ciò su cui ogni riga
  `SubjectConstraint` è ancorata. In ordine alfabetico la composizione risponde
  `INFEASIBLE` su 2 seed su 3. Entrambe le docstring dichiaravano di non
  disturbare nessuno: vero per il testimone *in sé*, falso per le righe già
  derivate da altri. Corrette, e la precedenza è ora esplicita.

  **L'oracolo differenziale era rimasto alle cinque famiglie dello spike** per
  dieci task: `CODICI` non era mai stato esteso, quindi copriva un ventesimo di
  ciò che sorvegliava di nome. Ora copre le ventisei, con una guardia che gli
  impedisce di reinvecchiare — una causale nuova deve finire in `CODICI` oppure
  in `FUORI`, per decisione esplicita.

  **Il passo «risolvi e guarda» è un rilevatore debole, misurato.** Sulle quattro
  famiglie `PARTS_*` le righe derivate sono violabili **118 volte su 120** —
  forzando la violazione: `INFEASIBLE` col builder acceso, `FEASIBLE` con quello
  spento — eppure il banco, che risolve e guarda, coglie un builder rotto **1
  volta su 11**. CP-SAT non cerca la soluzione cattiva e quasi mai la trova per
  caso. Da qui la regola della casa: **il test che dimostra che un vincolo morde
  forza la violazione e attende `INFEASIBLE`**, mai «risolvi e controlla dove è
  finita». La sonda esatta di violabilità è adottata in questa forma, e
  **non** come criterio del banco: farne il criterio richiederebbe di
  reimplementare in CP-SAT la condizione di violazione di tutte e ventisei le
  famiglie, dentro il banco che le verifica.

  **Il pattern, contato.** «Questa semplificazione è conservativa» era già stata
  asserita e falsificata tre volte prima di questo piano. Il piano l'ha ripetuta
  (`HALF_DAY_GAP`), e ne ha aggiunte altre: derivatori senza `return` (**tre
  volte** — avrebbero reso una famiglia intera verde per non aver fatto nulla),
  docstring che dichiarano di non disturbare nessuno, `residual_cap` dichiarato
  sufficiente per ogni tetto. Sempre la stessa forma: **il documento dichiara
  vera una proprietà che si rivela falsa solo controllandola contro il checker o
  contro i dati, mai a colpo d'occhio sul documento.** Le due contromisure che
  hanno funzionato sono misurare il derivatore del piano **prima** di scrivere
  il builder, e la mutazione — spegnere il builder e contare i rossi, perché un
  test che non diventa rosso quando il codice che afferma sparisce non sta
  affermando niente.

  **Debiti dichiarati**, tutti in «Ancora aperto» o nella §9 della spec: il
  banco **non congela mai nulla**, quindi la copertura di ADR-018 poggia
  interamente sui test scritti a mano; `coverage_mismatch` sul testimone, da
  riparare nella fixture prima di qualunque oracolo differenziale a tutto campo;
  i due tie-break di `domain/analysis` che sono artefatti dell'ordine
  d'inserimento; e ⚠ **una metà del tetto inevadibile che nessun builder può
  risolvere** — la `Finding.key` cresce comunque delle attività libere, quindi
  per le famiglie indipendenti dal piazzamento l'oracolo differenziale andrà
  formulato su una chiave più grossolana, o quelle famiglie andranno dove EDT le
  mette davvero: nell'analisi di capienza, che si esegue *prima* del calcolo.

- **2026-08-24** — **La review finale falsifica l'oracolo, e lo ripara.**
  L'oracolo dichiarato "tenuto" il 2026-08-09 aveva un limite non notato:
  scuola giocattolo, Fermi per una classe e Fermi intero condividono tutti
  **un'unica firma di settimana** (tutte le attività sono annuali), quindi la
  dimensione «settimane» di `domain/analysis/conformity.week_signatures` non
  era mai stata esercitata. La review finale l'ha trovato lì: `MaxGapBuilder`
  (il D.T.B.) dichiarava **conservativo** trattare tutte le attività come
  co-attive, ignorando le firme. **Non lo è.** Il buco è
  `ultima − prima + 1 − conteggio`: un'occupazione che cade *dentro* il buco
  ma viene da un'attività di un'**altra** firma alza il conteggio senza
  toccare `prima` né `ultima` — riempie il buco nel modello unione, mentre
  nelle settimane reali quel buco resta scoperto. Trattare tutto come
  co-attivo vincola quindi **di meno**, non di più: l'opposto di quanto
  dichiarato. Dimostrato con un'istanza a due firme costruita apposta
  (indisponibilità **datate**, non ricorrenti, su un docente con D.T.B. = 0):
  il solver rispondeva `OPTIMAL` piazzando una terza attività a riempire un
  buco che, settimana per settimana, nessuna attività attiva poteva colmare —
  e `check_schedule` bocciava il piazzamento con un `max_gap` `HARD`.
  Esattamente il fallimento che il criterio di riuscita dello spike dichiara
  inaccettabile.
  **Corretto**: `MaxGapBuilder` ora posta un budget **per firma di
  settimana** — un `model.Add(...)` per ogni `(rep, _)` di `ctx.signatures`,
  con i letterali `occ` filtrati alle sole attività attive in quella firma
  (`SolverContext.occupied` guadagna un parametro `signature` opzionale,
  memoizzato per `(firma, chiave, giorno, fascia)`; senza firma si comporta
  come prima). Firme diverse con lo stesso insieme di attività attive
  producono lo stesso vincolo: deduplicate con `posted`, come già fa
  `OccupationBuilder`. Nuovo test in `tests/test_solver_oracle.py` —
  `test_oracolo_su_istanza_multi_firma` — che nessuno dei banchi di prova
  esistenti poteva scrivere, perché il Fermi non ha la varietà di firme per
  farlo scattare.
  ⚠ **La stessa semplificazione in `subject_constraints.py` resta corretta**,
  e non è stata toccata: lì più letterali significano una somma più
  vincolata, mai il contrario — il caso pessimo è perdere qualche soluzione,
  mai accettarne di illegali.
  **Non è un errore di chi ha implementato: è il piano, la terza volta.** La
  semplificazione era scritta nei vincoli globali del piano con quella
  giustificazione. Sullo stesso branch: prima il D.T.B. tradotto come soglia
  per singolo buco invece che come budget settimanale (intercettato in fase
  di design, prima del commit); poi il modello dei token che non sapeva
  distinguere parti della stessa partizione da parti di partizioni diverse
  (ADR-017); ora questo. Tre volte lo stesso pattern: il piano dichiara una
  proprietà — soglia singola, insieme di chiavi sufficiente, semplificazione
  conservativa — che si rivela falsa solo quando la si controlla contro il
  checker o contro i dati, mai a colpo d'occhio sul piano stesso.
  **Rifiniture minori nello stesso giro**: `EMPTY_ATOMS` (dead code, zero
  riferimenti) rimosso da `domain/analysis/state.py`; in
  `subject_constraints.py` il ramo `A = B` ora conta attività distinte, non
  letterali, prima di postare il vincolo ridondante; `apply()` documenta di
  non fare nulla su `placements` vuoto; `test_fermi_intero_misurato` non può
  più spegnersi in silenzio se lo stato è feasible ma `placements` è vuoto;
  aggiunto un test di `AtomMap` con tre partizioni sulla stessa classe.
  **Chiusa la lacuna che restava**: il test multi-firma aggiunto qui sopra
  dimostra la correzione con un `INFEASIBLE`, ma nessun banco di prova
  portava una soluzione multi-firma **fattibile** lungo l'intera catena
  `solve → apply → check_schedule → violazioni() == []` — cioè il caso che il
  criterio di riuscita dello spike descrive davvero. Aggiunto
  `test_oracolo_su_istanza_multi_firma_fattibile`: due giorni per quattro
  fasce, due settimane, cinque attività. Il giorno 0 porta la dimensione
  D.T.B. (un buco che si chiude per firma e non si chiude nell'unione), il
  giorno 1 quella dell'occupazione (due attività di settimane diverse con
  docente, classe e unica collocazione ammissibile in comune: co-attive
  sarebbero un conflitto, e non lo sono mai). **Verificato che discrimina**,
  non solo che passa: rompendo `OccupationBuilder` (tutte le attività
  co-attive) e, separatamente, `MaxGapBuilder` (letterali `occ` senza firma),
  il test risponde `INFEASIBLE` in entrambi i casi. Suite completa a **173
  test verdi**.

  **Questione aperta, non risolta qui**: cosa fare quando un constraint
  mescola attività congelate già in violazione e attività libere nello stesso
  vincolo — va deciso nella spec del modello completo, prima degli altri
  ventidue builder. Aggiunta all'elenco **«Ancora aperto»**.

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
  finding atteso (`test_oracolo_puo_fallire` in
  `tests/test_solver_oracle.py` — un test della suite, non un esperimento una
  tantum: la prova resta nel repo, non solo nella sessione di review).
  ⚠ **Falsificato il 2026-08-24**: nessuno di quei tre banchi di prova
  esercita più di una firma di settimana, e proprio lì si annidava il
  difetto. Vedi la voce corrispondente più sopra.
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
