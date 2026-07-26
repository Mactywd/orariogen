# Decisioni di modellazione (ADR leggeri)

Formato: decisione, alternative scartate, motivo, data. Le date riflettono la
**registrazione** della decisione (migrazione su Claude Code); molte sono emerse
nella sessione di analisi preliminare.

---

## ADR-001 — `discipline` è una tabella, non un enum

**Decisione.** Modellare le discipline come tabella, con FK in arrivo da `materie`.

**Alternative scartate.** Enum/costanti hardcoded nel codice.

**Motivo.** Le scuole personalizzano il raggruppamento delle materie in discipline;
un enum obbligherebbe a rilasciare codice per ogni scuola. Vedi
[docs/edt/discipline.md](edt/discipline.md).

**Data.** 2026-07-09

---

## ADR-002 — Mappare le discipline alle classi di concorso

**Decisione.** Aggiungere una mappatura disciplina → classe di concorso (A011,
A027…), potenzialmente molti-a-molti.

**Alternative scartate.** Non mappare; oppure mappare direttamente le materie alle
classi di concorso.

**Motivo.** La normativa sulle **sostituzioni** ragiona per classe di concorso, non
per materia. Questo impatta direttamente il SaaS di gestione sostituzioni già in
produzione, di cui questo generatore è modulo. Vedi
[docs/edt/discipline.md](edt/discipline.md).

**Aggiornamento 2026-07-26.** La nota originale — *"la classe di concorso è nostra
estensione, non un campo EDT osservato"* — va corretta a metà. Nella **base di
riferimento italiana fornita col prodotto** le discipline hanno per `Codice`
esattamente le classi di concorso (`A-01`, `A-22`, `A-25`, `A-28`, `A-30`,
`A-49`, `A-60`, più `REL` e `SOST`). Quindi non è un campo dedicato, ma è **il
posto dove EDT Italia si aspetta che la si metta**: una convenzione d'uso
documentata dal produttore, non una nostra invenzione.

Ciò che **non** cambia: EDT non incorpora la tabella ministeriale delle classi di
concorso (verificato: i codici stanno solo nei dati della base demo, non nei
binari né in `TabellaSIDI.xml`), non valida nulla, e il `Codice` è scalare mentre
la relazione reale è molti-a-molti in un liceo (Lettere → A-11/A-12/A-13). La
decisione resta quindi valida: **tabella di mappatura a sé**, con il `Codice`
della disciplina usato come sorgente di import quando è valorizzato.

**Data.** 2026-07-09 (aggiornato 2026-07-26)

---

## ADR-003 — `NULL` significa "eredita"; cascata risolta a runtime

**Decisione.** Non materializzare i default nelle righe. `NULL` = "eredita dal
livello superiore" (globale → entità → istanza); la cascata si risolve a runtime.

**Alternative scartate.** Copiare il default in ogni riga al momento della
creazione.

**Motivo.** Materializzare produrrebbe ~288 righe che ripetono "30" e renderebbe
impossibile distinguere un **override deliberato** da un default inerte. Scoperto sul
campo `Al./Rid.` delle materie. Vedi [docs/edt/materie.md](edt/materie.md).

**Data.** 2026-07-09

### Emendamento 2026-07-26 — la cascata è locale, non generale

La decisione **resta valida**, ma il suo ambito era stato sopravvalutato. Cercando
l'estensione della cascata è emerso che **in EDT non esiste alcun meccanismo
generale di ereditarietà**:

- il marcatore `(Gr.)`, che avevo preso per il segno visibile dell'ereditarietà, ha
  **due sole occorrenze** in 69 888 stringhe, entrambe in pannelli di **permessi**
  su risorse prenotabili (`Gestionnaire`, `Réservable par`): è provenienza di un
  **diritto**, non di un valore. Vedi [aule.md](edt/aule.md), corretto.
- nessun vocabolario dedicato: FR `propag` compare **zero** volte; FR `hérit` due,
  di cui una è un errore del framework Delphi; le 327 `par défaut` sono quasi tutte
  default di UI o di stampa.

**I campi su cui la cascata è dimostrata sono pochi:**

| Campo | Catena |
|---|---|
| `Al./Rid.` delle materie | globale → materia → istanza |
| `Apport` / `Mh/s` dei docenti | **globale → docente** (due livelli, non tre: lo Statuto non c'entra — vedi [docenti.md](edt/docenti.md)) |
| Aula del colloquio | docente → colloquio (modulo Colloqui, fuori scope) |

**Conseguenza pratica:** i campi nullable servono a **pochi** attributi, non a tutto
il modello. Materializzare i default è la scelta giusta quasi ovunque; `NULL =
eredita` è l'eccezione, e va applicata dove il prodotto la dichiara.

### ⚠ Un meccanismo diverso da non confondere: copia alla creazione

Le **indisponibilità standard** di docenti e classi non sono ereditate: sono
**copiate all'atto della creazione** dell'istanza. La differenza non è accademica.
Se le trattassimo come cascata, cambiare il default globale **riscriverebbe le
indisponibilità già personalizzate di tutti i docenti** — un bug silenzioso e
difficile da diagnosticare, perché si manifesterebbe solo mesi dopo.

Regola: *«eredita»* e *«copia dal modello»* sono due meccanismi distinti, e vanno
distinti anche nello schema.

---

## ADR-004 — I gruppi sono entità distinte dalle classi

**Decisione.** Modellare i **gruppi** (sdoppiamenti, corsi a effettivo ridotto) come
entità distinta, collegata alla classe.

**Alternative scartate.** Trattare la classe come blocco monolitico che si muove
sempre insieme.

**Motivo.** Gli sdoppiamenti rompono l'ipotesi "una classe = un blocco". Il campo
`Al./Rid.` non ha dove appoggiarsi se il gruppo non esiste come entità. Vedi
[docs/edt/gruppi.md](edt/gruppi.md). *(Scope v1 ancora da decidere — vedi Aperto in
[CLAUDE.md](../CLAUDE.md).)*

**Data.** 2026-07-09

---

## ADR-005 — `Al./Rid.` è un tetto massimo nullable, non un flag né un effettivo

**Decisione.** Modellare `Al./Rid.` come **numero massimo** di alunni (nullable, per
la cascata), non come flag classe-intera/ridotta né come conteggio effettivo.

**Alternative scartate.** Interpretarlo come flag; oppure come effettivo (numero
reale di alunni, es. "metà classe").

**Motivo.** Il tooltip EDT è *"Numero ridotto di alunni della materia"*: è il tetto
verificato contro la capienza dell'aula. Interpretarlo come effettivo ha già causato
un errore (FIS/SCI impostate a 13, "metà di 26"): un tetto a 13 si romperebbe con una
classe da 28 iscritti. Vedi [docs/edt/materie.md](edt/materie.md).

**Data.** 2026-07-09

---

## ADR-006 — Separare la capacità (materie insegnabili) dall'assegnazione (cattedra)

**Decisione.** Modellare la **capacità** del docente (M2M `docente ↔ materia`, le
"materie insegnabili") come relazione distinta dalla **cattedra** (le assegnazioni
concrete materia × classe/gruppo × ore).

**Alternative scartate.** Dedurre cosa un docente può insegnare dalle sole materie che
insegna quest'anno (cioè dalla cattedra).

**Motivo.** La capacità è più ampia dell'assegnazione: un docente abilitato a più
materie può quest'anno insegnarne solo una. È la **capacità**, non l'assegnazione, a
decidere l'eleggibilità alle **sostituzioni** — il cuore del SaaS di cui questo
generatore è modulo. EDT le tiene distinte (campo "Materie insegnabili" vs. la
cattedra). Vedi [docs/edt/docenti.md](edt/docenti.md) e [ADR-002](#adr-002--mappare-le-discipline-alle-classi-di-concorso).

**Data.** 2026-07-09

---

## ADR-007 — I campi previsionali/calcolati non si memorizzano

**Decisione.** Non memorizzare i campi derivati del docente (`Occ. prev.`, `HS Prev.`,
`+/-`, `Extra`): si ricalcolano a runtime dall'assegnazione e dal monte ore.

**Alternative scartate.** Salvare i valori previsionali come colonne del docente.

**Motivo.** Sono output della fase di pianificazione («ripartizione dei servizi»),
funzione della cattedra: `+/- = Mh/s − Occ. prev.`. Memorizzarli terrebbe in tabella un
valore che cambia a ogni modifica della cattedra e può divergere dalla realtà. Stesso
spirito di [ADR-003](#adr-003--null-significa-eredita-cascata-risolta-a-runtime) (non
materializzare ciò che è derivabile). Vedi [docs/edt/docenti.md](edt/docenti.md).

**Data.** 2026-07-09

---

## ADR-008 — Il solver si costruisce dopo il reverse engineering, non in parallelo

**Decisione.** Congelare il prototipo CP-SAT (`scripts/genera_orario.py`) allo stato
attuale. Nessun vincolo nuovo finché l'analisi di EDT non è completa e non abbiamo
deciso quali feature entrano in v1.

**Alternative scartate.** Far crescere il prototipo in parallelo all'analisi,
aggiungendo ogni vincolo appena viene documentato (aule, blocchi, indisponibilità).

**Motivo.** Il prototipo ha già risposto alla sua domanda — CP-SAT regge il
dimensionamento (288 ore, OPTIMAL in 0.14s) — e quella era la sola cosa che doveva
dimostrare. Aggiungere vincoli uno alla volta significherebbe fissare la struttura
del modello (variabili, granularità dello slot, come si rappresenta un gruppo)
mentre ancora non sappiamo cosa dovrà esprimere: le scelte prese presto sarebbero
poi da disfare. Il costo di aspettare è nullo, quello di riscrivere no. Vedi
[docs/edt/vincoli.md](edt/vincoli.md) per l'elenco di ciò che manca.

**Data.** 2026-07-26

---

## ADR-009 — Gli artefatti dell'installazione sono una terza fonte, marcata 📦

**Decisione.** Accettare come fonte documentaria i file dell'installazione di EDT
(schemi XSD, tabelle XML di nomenclatura, stringhe estratte dai binari, basi dati
di esempio), marcandoli **📦** e distinguendoli sia dall'osservazione in UI (fonte
di default, non marcata) sia dalla guida online (**📖**).

**Gerarchia di autorevolezza**, dalla più forte:

1. **📦 schemi XSD** — dichiarazioni formali con nomi, tipi, cardinalità e
   annotazioni dell'autore. Più forti dell'osservazione in UI, che è
   interpretazione di ciò che si vede.
2. **UI osservata** — comportamento reale del prodotto.
3. **📦 tabelle XML** (`TabellaSIDI.xml`) — dati di riferimento, non semantica.
4. **📖 guida online** — prosa divulgativa, talvolta imprecisa.
5. **📦 stringhe estratte dai binari** — indiziarie: dicono che una cosa *esiste*,
   non cosa *significa*.

**Alternative scartate.** Continuare col solo reverse engineering per
osservazione, screenshot per screenshot.

**Motivo.** L'installazione contiene lo schema di scambio ufficiale
`Partenaire_Index` V4.6, annotato dall'autore, che ha chiuso in un colpo domande
rimaste aperte per sessioni (allineamento → attività complessa; tre monte ore per
materia; capacità simultanea come attributo della risorsa). Un XSD è *più*
autorevole di uno screenshot: non va interpretato. Restava il rischio di
documentare come fatto ciò che è solo un nome di simbolo — da qui la gerarchia,
che tiene le stringhe dai binari all'ultimo posto.

**Conseguenza operativa.** Un elemento marcato 📦 al livello 1 non richiede
conferma in UI. Ai livelli 3–5 sì, come per 📖.

**Data.** 2026-07-26

---

## ADR-010 — Niente collocazione per periodo: si rigenera l'orario a ogni periodo

**Decisione.** L'attività ha **una sola collocazione**. Se l'orario cambia al
secondo quadrimestre, si **rigenera**: ogni periodo è un'istanza indipendente del
problema. Non implementiamo la `fascia variabile` di EDT.

**Alternative scartate.** Modellare la collocazione come `slot[attività, periodo]`,
con vincolo di uguaglianza fra periodi quando l'attività è dichiarata fissa — cioè
il modello di EDT ([tempo-e-calendario.md](edt/tempo-e-calendario.md)).

**Motivo.** La variante di EDT raddoppia la dimensione dello spazio di ricerca e
complica ogni vincolo (i massimi orari andrebbero valutati per periodo, con le
quattro modalità di applicazione già documentate). Rigenerare è concettualmente più
semplice e copre il caso reale: in Italia l'orario che cambia a metà anno si rifà,
non si "varia".

**⚠ Conseguenza da gestire.** Rigenerando da zero, il secondo quadrimestre può
risultare **completamente diverso** dal primo per tutti — cosa che docenti e classi
detestano. In EDT questo non accade perché il default è `fascia fissa`: la maggior
parte delle lezioni **non si muove** fra i periodi.

Il rimedio non è strutturale ma un **criterio di ottimizzazione**: *«mantieni il più
possibile le collocazioni del periodo precedente»*. Costa poco (è una distanza dalla
soluzione precedente, la stessa forma del «minimo insieme di attività da spostare»
del risolutore passo-passo) e recupera il beneficio senza il costo del modello. EDT
ha un criterio analogo sulle aule: *"Se possibile mantenendo le assegnazioni della
precedente ripartizione"*.

**Da implementare insieme alla rigenerazione, non dopo.**

**Data.** 2026-07-26

---

## ADR-011 — Il peso didattico entra in v1

**Decisione.** Implementare il **peso didattico**: un peso intero per materia e dei
tetti sulla somma per mezza giornata, giornata, settimana (e ciclo, se mai
servirà). Cascata di default istituto → classe, come in EDT.

**Alternative scartate.** Ottenere lo stesso effetto con le incompatibilità fra
materie a coppie.

**Motivo.** È il vincolo di **carico cognitivo**: impedisce l'orario con tre materie
pesanti nella stessa mattina. Le incompatibilità a coppie sono lo strumento
sbagliato — dichiarano «matematica e fisica non insieme» invece di «non troppa roba
pesante insieme», e vanno enumerate a mano per ogni coppia.

Costa pochissimo (una somma di interi confrontata con un limite; in CP-SAT tre
vincoli `sum(...) <= limite` per classe) e ha valore percepito alto: è una qualità
che un dirigente riconosce subito. EDT lo implementa completo — pesi per materia,
tetti su mattino/giornata/settimana/ciclo, diagnostica dedicata e alleggerimento a
quota. Vedi [vincoli.md](edt/vincoli.md).

**Da chiarire prima di implementare:** la scala dei pesi usata da EDT (interi? 1–10?)
e i valori di default.

**Data.** 2026-07-26

---

## ADR-012 — Non adottiamo `Partenaire_Index` come formato di import

**Decisione.** Non implementare l'import dello schema XSD `Partenaire_Index` V4.6 di
Index Education.

**Alternative scartate.** Adottarlo come via d'ingresso per le scuole che migrano da
EDT o da gestionali che parlano con EDT.

**Motivo.** Trasporta **solo la struttura** — anagrafiche, classi, docenti, materie,
piani di studi e attività da piazzare — e **nessun vincolo, nessun piazzamento**
([schema-scambio.md](edt/schema-scambio.md)). Una scuola che migrasse si porterebbe
dietro le cattedre ma dovrebbe reinserire a mano indisponibilità, giorni liberi e
incompatibilità: cioè tutto il lavoro vero. Il beneficio è quindi molto minore di
quanto il formato sembri promettere, a fronte di uno schema pensato per
l'ordinamento francese e pieno di campi che non ci riguardano.

**Cosa resta valido.** Lo schema **rimane la fonte documentaria più autorevole** sul
modello dati di EDT ([ADR-009](#adr-009--gli-artefatti-dellinstallazione-sono-una-terza-fonte-marcata-)):
non lo implementiamo, ma continuiamo a leggerlo.

**Conseguenza da affrontare più avanti.** Serve comunque *una* via d'ingresso dei
dati anagrafici, altrimenti ogni scuola parte da un foglio bianco. Da decidere
quando arriveremo all'import: formato nostro, CSV, o aggancio al SaaS esistente.

**Data.** 2026-07-26

---

## ADR-013 — Gli sdoppiamenti entrano in v1, raggruppamenti trasversali inclusi

**Decisione.** Supportare l'intera catena `Classe → Suddivisione → Gruppo` di EDT,
**inclusi i raggruppamenti che attraversano più classi** (le seconde lingue: tre
classi che si ricompongono in gruppi di francese, spagnolo e tedesco).

**Alternative scartate.** (a) Solo religione/alternativa, come due attività della
stessa classe vincolate allo stesso slot; (b) solo i gruppi **interni** a una classe
(laboratori, mezze classi), escludendo quelli trasversali.

**Motivo.** Gli sdoppiamenti sono una necessità reale della scuola italiana, non un
caso limite, e una v1 che non li copre non è utilizzabile in un liceo. Concretizza
[ADR-004](#adr-004--i-gruppi-sono-entità-distinte-dalle-classi), che già dichiarava
i gruppi entità a sé.

**⚠ Cosa costa davvero.** Questa è la decisione più onerosa presa finora, e il costo
non sta nei gruppi interni ma nei **trasversali**.

Un gruppo interno a una classe è gestibile: due gruppi della stessa classe occupano
lo stesso slot in aule diverse, e la classe resta l'unità di ragionamento.

Un raggruppamento trasversale **accoppia classi diverse**: se 1A, 1B e 1C si
ricompongono per la seconda lingua, quelle tre classi non si possono più piazzare
in modo indipendente — le loro ore di lingua devono cadere nello stesso slot per
tutte e tre. Si perde la possibilità di decomporre il problema per classe, che è la
semplificazione più naturale e più efficace su cui contare.

Ordini di grandezza dalla base di esempio di EDT: **187 suddivisioni interne contro
3 raggruppamenti trasversali**. Il caso costoso è raro ma non eliminabile.

**Conseguenze operative.**

- Le ore si assegnano al **gruppo**, non alla classe; il monte ore per (piano,
  materia) è già tripartito in classe intera / ridotta / sdoppiata nello schema
  ufficiale ([schema-scambio.md](edt/schema-scambio.md)).
- Serve il meccanismo dell'**attività complessa**: nello XSD è l'allineamento a
  generare il raggruppamento, non il contrario.
- Diventa rilevante il vincolo **`Attività in gruppo`** (l'ordine fra ore in gruppo
  e ore a classe intera, i quattro valori `Parties…Classe`): esiste **solo** se
  supportiamo gli sdoppiamenti. Vedi [vincoli.md](edt/vincoli.md).
- Va riusata la validazione dell'allineamento di EDT, che elenca **11 modi di
  fallire** ([motore-risoluzione.md](edt/motore-risoluzione.md)).
- ⚠ Attenzione all'**inversione terminologica IT↔FR**: in italiano «gruppo» traduce
  `partie`, non `groupe`. Vedi [glossario-it-fr.md](edt/glossario-it-fr.md).

**Data.** 2026-07-26

---

## ADR-014 — Una sola entità attività, con maschera temporale: la sostituzione non è un'entità a parte

**Decisione.** Modelliamo l'attività come **una sola entità** portatrice di una
maschera delle settimane. Uno spostamento puntuale e una **sostituzione** non sono
tipi diversi: sono la stessa entità con la maschera ridotta a una settimana, più un
riferimento all'attività annuale che rimpiazzano e la soppressione di quella
occorrenza.

**Alternative scartate.**

- *Ricorrenza + tabella di eccezioni datate.* È il modello che avevo dedotto e
  scritto in [tempo-e-calendario.md](edt/tempo-e-calendario.md) prima di guardare i
  dati. Sembra più pulito, ma raddoppia le entità e costringe a duplicare ogni
  vincolo: uno per le lezioni ricorrenti, uno per le eccezioni.
- *Sostituzione come entità del modulo supplenze, separata dall'orario.* È il
  confine naturale fra i due prodotti, e sarebbe la scelta di default. È proprio
  quella che i dati smentiscono.

**Motivo.** Verifica sui 161 record di `RELATIONCOURSSUBSTITUT` della base di
esempio ([formato-file.md](edt/formato-file.md)):

- i sostituti sono **esattamente** le attività con maschera a una settimana
  (nature 2 e 4, 141 + 20 = 161);
- gli originali sono **161/161** annuali;
- **159/161 cambiano solo il docente**, a parità di classe (161/161) e aula
  (161/161).

Cioè, nel modello dati di EDT, **sostituire un docente e spostare un'ora per una
settimana sono lo stesso atto**. E le 141 attività di natura 2 coincidono al record
con il `NBAMENAGEMENTS` dichiarato nell'header: non è un'interpretazione, è
un'identità.

**Perché ci riguarda più che EDT.** Il committente ha **già un SaaS di sostituzioni
in produzione**. Se il generatore adotta questo modello, generatore e sostituzioni
condividono l'entità invece di scambiarsi dati: una supplenza inserita nel SaaS è
già un'attività leggibile dal solver, e un orario rigenerato non invalida le
supplenze in corso. Se invece li teniamo separati, ogni funzione che tocca entrambi
va scritta due volte.

**Conseguenze.**

- La partecipazione risorsa↔attività **non è booleana ma temporale**: la maschera
  compare anche per singola relazione in `RELATIONCOURSRESSOURCE`.
- Serve un campo **natura** (o equivalente) sull'attività, e una relazione
  *sostituisce* verso l'attività annuale.
- Serve una **soppressione dell'occorrenza** annuale distinta dalla cancellazione
  dell'attività (in EDT: `ANNULATIONCOURS`).
- La supplenza lunga ha una **testata** che raggruppa (in EDT: `REMPLACEMENTLONG`
  = assenza + supplente + intervallo di date), ma **le ore restano attività**: la
  testata raggruppa, non sostituisce.
- ⚠ Da decidere al momento dell'integrazione: se il SaaS esistente possa adottare
  questo modello o se serva un adattatore. Non è una decisione presa qui.

**Data.** 2026-07-26
