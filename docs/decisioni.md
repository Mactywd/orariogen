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

---

## ADR-015 — Perimetro funzionale di v1: le sei decisioni contese

**Contesto.** La documentazione del reverse engineering è stata censita in un
inventario piatto di **308 funzionalità** (`docs/edt/estratti/inventario-*.md`), di
cui 59 marcate `strutturale`. La classificazione completa, con i cinque criteri
usati, sta in [scope-v1.md](scope-v1.md). Quasi tutte le voci seguono dai criteri;
sei no, e sono decise qui.

**Decisioni.**

| | Funzionalità | Esito |
|---|---|---|
| 1 | Risolutore passo-passo interattivo | **fuori** |
| 2 | Ricerca di sottoinsiemi infattibili (violatore di Hall) | **rimandato** |
| 3 | Sedi distaccate | **dentro**, campo + regola di transizione semplice |
| 4 | Classe articolata | **dentro**, gestita con le parti di classe |
| 5 | Personale e materiali come risorse | **dentro come forma**, dati non richiesti |
| 6 | Vincoli fra attività (11 tipi, dichiarati su coppie) | **fuori** |

**Motivi, uno per riga.**

1. **Risolutore passo-passo — fuori.** È la funzione più distintiva di EDT: una
   catena di espulsioni esposta all'utente, che negozia il danno collaterale un
   passo per volta. Ma `Piazza e sistema` — *«sposta l'attività in una posizione già
   occupata; se ciò comporta lo spostamento di altre attività, queste verranno
   automaticamente ricollocate»* — dà lo stesso risultato a una frazione del costo.
   L'utente ottiene la lezione dove la vuole; semplicemente non sceglie cosa si
   muove.
2. **Hall — rimandato, non escluso.** Distingue il caso in cui *nessuna* attività è
   individualmente impiazzabile ma un loro sottoinsieme sì (osservato in EDT: 25
   attività, 33h di domanda contro 32h di finestra comune). CP-SAT non lo regala:
   l'UNSAT core elenca vincoli interni, non persone e classi. Le fasi facili
   coprono la maggior parte dei casi reali.
3. **Sedi — dentro, con la regola semplice.** Non solo il campo: anche un vincolo
   di transizione (*per cambiare plesso servono N slot liberi*, `N` parametro unico
   d'istituto). È la scelta che **paga il costo strutturale vero** — il
   ragionamento su slot **consecutivi**, forma che nessun altro vincolo
   dell'inventario introduce. Pagato quello, la matrice orientata dei tempi e i
   massimi di cambi sono raffinamenti a basso costo, esclusi da v1.
4. **Classe articolata — con le parti.** Il caso (la 3A con due indirizzi) è reale
   nei tecnici e nei professionali, ma è esprimibile con le **parti di classe** già
   introdotte da [ADR-013](decisioni.md) per gli sdoppiamenti, senza un'entità
   dedicata né la relazione classe↔piani molti-a-molti dello XSD.
5. **Personale e materiali — forma sì, dati no.** Costa quasi nulla **perché** la
   tabella delle disponibilità è generica sulla risorsa, scelta presa comunque per
   altri motivi. Cablare tre tipi di risorsa costringerebbe a riscrivere per
   aggiungerli. Il prodotto funziona senza inserirli; chi ha il sostegno
   strutturato li usa.
6. **Vincoli fra attività — fuori, su evidenza.** Vincoli dato-driven su coppie di
   lezioni scelte a mano, da non confondere con i vincoli di **materia** (che sono
   su categorie e si applicano da soli). Nella base di esempio del produttore quella
   griglia è **vuota**: EDT li offre da anni e nella loro demo nessuno li usa. ⚠ È
   l'esclusione con meno margine: «vuota nella demo» non è «inutile nella pratica»,
   e la demo è una scuola media — un tecnico con laboratori potrebbe usarli.

**⚠ Tre condizioni che tengono in piedi le decisioni.**

- `Piazza e sistema` richiede comunque di saper rispondere a *«qual è l'insieme
  minimo di attività da spostare perché A stia qui?»* — lo stesso motore del
  risolutore escluso. Prevederlo tiene aperta la porta a riaprire la decisione 1.
- Rimandare Hall funziona **solo se** l'analisi di capienza è un componente a sé,
  separato dal solver, e non un'interpretazione a posteriori del suo output.
- La decisione 4 presuppone che una **parte** possa portare un **piano di studi
  proprio**. Se il quadro orario resta agganciato alla sola classe, decade e va
  ripresa.

**Data.** 2026-07-26

---

## ADR-016 — L'osservazione di EDT è conclusa: si progetta il modello di dominio

**Decisione.** Dichiarare soddisfatta la condizione di [ADR-008](decisioni.md) e
chiudere la fase di reverse engineering. La fase successiva è la **progettazione
del modello di dominio**, come documento di design
([modello-dominio.md](modello-dominio.md)) prima del codice. Il modello nasce
**autonomo dal SaaS** sostituzioni in produzione: schema proprio, nessuna tabella
condivisa ora, con le due entità di convergenza (attività con maschera temporale,
disponibilità con data opzionale) disegnate per l'aggancio futuro.

**Alternative scartate.** (a) Costruire subito il modello solver CP-SAT: fissa la
forma dei dati prima di averla disegnata. (b) Estendere da subito il DB del SaaS
(entità condivisa, massimo valore di ADR-014): vincola il design al legacy e
richiede una migrazione in produzione prima ancora di avere un modello maturo.
(c) Chiudere prima i punti aperti residui (griglia oraria in UI, aule del Fermi):
nessuno dei due è bloccante per il modello, e lo XSD copre la griglia con la fonte
più autorevole disponibile.

**Motivo.** ADR-008 chiedeva di capire *tutti* i vincoli prima di costruire il
modello: l'inventario delle 308 funzionalità, lo scope di v1
([ADR-015](decisioni.md)) e la chiusura di tutti i punti aperti non marginali lo
soddisfano. I due punti restanti (aule mai inserite nella base del Fermi,
estensione della cascata di default) sono dichiarati non bloccanti nello stato del
progetto. Il prototipo `scripts/genera_orario.py` resta parcheggiato: si sblocca
quando il modello di dominio è approvato e tradotto in codice, non prima.

**Data.** 2026-07-26

---

## ADR-017 — Parti di partizioni diverse della stessa classe confliggono

**Decisione.** Due parti della stessa classe possono essere piazzate in
parallelo **solo se appartengono alla stessa partizione** (il caso `_REL`/`_ALT`
resta valido: sono parti della stessa partizione, pensate per stare in
parallelo). Parti di **partizioni diverse** (es. `1A_REL` e `1A-fra`)
condividono studenti e **confliggono**, anche se il modello v1 attuale non lo
rileva.

**Alternative scartate.** Tenere la regola v1 così com'è (`activity_tokens` in
`domain/analysis/state.py`): «parti di partizioni diverse non confliggono» è la
lettura più diretta della specifica e costa meno da implementare, ma perde
conflitti reali — due sdoppiamenti indipendenti della stessa classe (uno per
lingua, uno per laboratorio) possono benissimo condividere lo stesso alunno.

**Motivo.** Segnalato dalla review finale: la regola v1 (`Parti di partizioni
diverse non confliggono`, documentata nel docstring di `activity_tokens` e
nella spec `docs/superpowers/specs/2026-07-26-analisi-vincoli-design.md`) tratta
ogni partizione come se esaurisse la classe, ma le partizioni sono
**indipendenti** e i loro alunni si sovrappongono. EDT risolve il caso generale
con i **«legami fra parti»** (*parties sans liens*, letteralmente "parti senza
legami"): un meccanismo dato-driven che dichiara esplicitamente quali parti di
partizioni diverse **non** condividono alunni (e quindi possono stare in
parallelo). Non lo modelliamo ancora.

**Conseguenze.** Implementare correttamente questa regola richiede una codifica
dei token di occupazione più fine (per alunno, o per legame dichiarato) e il
relativo constraint nel solver CP-SAT.

**Implementato** il 2026-08-09 nello spike CP-SAT: gli **atomi**, cioè le celle
del prodotto delle partizioni, calcolate in `domain/analysis/state.py`
(`AtomMap`). Le parti della stessa partizione restano disgiunte, quelle di
partizioni diverse condividono almeno un atomo. Nessun campo nuovo, nessuna
migrazione, e nessun effetto sulle classi con meno di due partizioni.

**Data.** 2026-07-26

---

## ADR-018 — L'input sporco non blocca il solver: capacità residua e oracolo differenziale

**Decisione.** Quando un vincolo mescola attività **congelate già in violazione**
e attività **libere**, il constraint si posta comunque, ma sui **soli letterali
liberi**, con il budget ridotto di quanto le congelate hanno già consumato e
**clampato a zero**. Il solver non è mai `INFEASIBLE` per colpa di una
violazione preesistente: al più non può aggiungere nulla lì.

Di conseguenza il criterio di riuscita dell'oracolo diventa **differenziale**:
non «zero finding `HARD`», ma «nessun finding `HARD` che non ci fosse già prima
del solve». I finding preesistenti restano visibili — non vengono nascosti, solo
non attribuiti al solver.

**Alternative scartate.** (a) **Input pulito come precondizione**: il solver si
rifiuta di partire e dichiara quali congelate sono in violazione. Modello più
semplice e oracolo invariato, ma trasforma in vicolo cieco il caso più comune —
l'utente ha piazzato a mano qualcosa di illegale e vuole solo riempire il resto.
(b) **Una regola per builder**: ogni vincolo dichiara come si comporta
sull'input sporco. Più fedele ai casi limite, ma sono ventidue decisioni invece
di una, e nessuna proprietà globale resta dimostrabile.
(c) Mantenere la regola dello spike («un constraint i cui letterali provengono
tutti da attività congelate non si posta»): è coerente ma non basta, ed è
esattamente il buco documentato in `CLAUDE.md` fino a oggi.

**Motivo.** È il comportamento osservato in EDT, non un'invenzione: un orario
valido **non è un invariante** del prodotto. Una base con 984/984 attività
piazzate dichiarava comunque 21 attività in violazione, piazzate a mano, e il
motore continuava a lavorare (`docs/edt/diagnostica.md`). La violazione è uno
stato ammesso e interrogabile; il solver è uno strumento che migliora l'orario,
non un guardiano che si rifiuta di toccarlo.

**Conseguenze.** Ogni builder dei ventidue restanti va scritto contro la
capacità residua, non contro il budget nominale — il calcolo del consumo delle
congelate va nel contesto, una volta sola, non dentro i builder. E i test
dell'oracolo vanno riscritti sul confronto prima/dopo: `violazioni()` diventa
una differenza di insiemi, non un totale.

**Data.** 2026-08-24

## ADR-019 — Dentro una fascia non si viaggia: il cambio di sede e il pareggio di collocazione

**Decisione.** Due decisioni gemelle, entrambe su verdetti che dipendevano
dall'**ordine d'inserimento** invece che dall'orario.

1. **Il cambio di sede.** Una fascia contribuisce l'**insieme** delle sedi che
   la occupano; un cambio è una transizione fra due fasce consecutive (nella
   sottosequenza di quelle con sede nota) i cui insiemi **differiscono**. Due
   sedi diverse sulla stessa fascia valgono **zero** cambi.
   ⚠ Ma restano una violazione di `structural:site_transition`: essere in due
   posti insieme è impossibile (`gap_slots = -1`, minore di qualunque soglia).
   Le due domande sono diverse — «è fisicamente possibile?» contro «quante
   volte ci si è spostati?» — e tengono risposte diverse.
2. **Il pareggio di collocazione.** `_placed_of` ordina per `(giorno, fascia,
   identità dell'attività)`. Il pareggio si rompe con il pk: arbitrario, ma
   **stabile e riproducibile**.

**Alternative scartate.** (a) **Ordinare la sequenza intra-fascia in modo
deterministico** e continuare a contare i cambi al suo interno: renderebbe il
conteggio riproducibile senza renderlo *sensato* — un ordine inventato fra due
occupazioni simultanee resta inventato, e il numero che ne esce non descrive
nessun viaggio. (b) **Sedi diverse simultanee valgono un cambio**, comunque e
indipendentemente da quante siano: riproducibile e semplice, ma afferma che
stare fermi in due posti sia uno spostamento, e sarebbe l'unico punto del
modello in cui un cambio non corrisponde a un tragitto. (c) Per il pareggio,
**nominare tutte le occorrenze in parità** invece di sceglierne una: sarebbe
funzione della sola forma dell'orario, che è meglio, e per `WEEKLY_ORDER`
funzionerebbe — ma non generalizza alle famiglie a **coppie consecutive**
(`IMPOSED_SUCCESSION` con A = B), dove il pareggio sposta la coppia invece di
allargare un secchio. Una regola sola per tutti i lettori di `_placed_of` vale
più di due contratti di finding diversi.

**Motivo.** Un checker è **l'autorità** su cosa significhi un vincolo: il
builder CP-SAT traduce lui. Finché il checker risponde in base all'ordine in
cui il queryset ha restituito le righe, non c'è nulla da tradurre — e infatti
`MaxSiteChangesBuilder` si era fermato, dichiarando l'artefatto invece di
replicarlo. La scelta fra le alternative è governata dal verso dell'errore: per
il conteggio dei cambi la nuova regola conta **meno** cambi del massimo che
l'ordine poteva produrre, quindi perde richiamo e mai precisione — che per un
checker è il verso giusto, perché mandare l'utente a smontare un vincolo sano è
il danno peggiore.

**Conseguenze.** A capienza 1 — cioè ovunque salvo l'aula col `Numero di aule`
di EDT e gli stati già illegali — le nuove regole coincidono riga per riga con
le vecchie, quindi nessun dataset reale si muove. `MaxSiteChangesBuilder` torna
traducibile: la sua costruzione a coppie `s < t` non esprime il caso `s == t`, e
ora **non deve** esprimerlo. Resta su di lui una sovra-approssimazione
**dichiarata** nel caso a più sedi per fascia (posta le coppie incrociate dove
il checker conta zero), cioè è più stretto del checker — il verso in cui una
sovra-approssimazione non rompe l'oracolo differenziale.
⚠ E il residuo di ADR-018 si conta invece nell'unità del **builder** — la
somma dei letterali che *lui* crea — non con la regola del checker: vedi
l'emendamento qui sotto, che corregge questa riga. Resta vero ciò che l'aveva
motivata: contarlo **appiattendo** le occupazioni sovrastimava il consumo
delle congelate, alzava il tetto clampato e faceva accettare al solver un
cambio che il checker non perdona — misurato, `OPTIMAL` con un
`max_site_changes` `HARD` nuovo sulla soluzione applicata.

**Data.** 2026-08-28

### Emendamento 2026-08-28 (sera) — il residuo si conta nell'unità del builder

Le due decisioni **restano valide**; è sbagliata la riga che ne derivava il
trattamento del residuo di ADR-018. Diceva che va calcolato «con **la stessa**
regola» del checker, e da lì `_frozen_site_changes` era stato allineato alle
transizioni fra **insiemi**. Ma il numero che quel conteggio produce non
descrive il checker: entra in `max(per_giorno, consumo_giorno)`, cioè clampa
un tetto la cui somma è fatta dei letterali del **builder**, uno per ogni
coppia **ordinata** di sedi diverse fra due fasce adiacenti.

⚠ Le due grandezze divergono esattamente dove questo ADR ha spostato la
semantica: a capienza cumulativa. `{A, B}` alla fascia 0 e `{C}` alla fascia 1
valgono **1** cambio per il checker e **due** letterali per il builder, quindi
il consumo calcolato alla maniera del checker è **più basso** di quello che le
sole congelate forzano a 1, e il clamp non clampa abbastanza. Misurato:
`check_schedule` non ha **niente** da ridire su quell'orario e `solve()`
risponde `INFEASIBLE` — la metà vietata del criterio di
[ADR-018](#adr-018--linput-sporco-non-blocca-il-solver-capacità-residua-e-oracolo-differenziale), quella
in cui l'infattibilità nasce dal **pretendere una riparazione** del passato.

🔑 **La regola che ne esce, e che vale per ogni residuo futuro:** il consumo
delle congelate si conta nell'**unità del vincolo che lo riceve**, non in
quella del checker che lo ispira. Sono due letture diverse dello stesso
orario, e coincidono solo dove builder e checker contano la stessa cosa.

⚠ Il che **non riabilita l'appiattimento**, che resta l'errore corretto sopra:
appiattire `by_cell` conta anche le coppie *dentro* una fascia — dove non si
viaggia, che è la decisione 1 — e per giunta in un ordine deciso dal queryset.
L'unità del builder è un'altra cosa: solo coppie fra fasce **diverse**, e
indipendente dall'ordine d'inserimento.

**Conseguenze.** A capienza 1 ogni insieme è un singoletto e i due conteggi
tornano a coincidere riga per riga: nessuna istanza esistente si muove, e il
Fermi — che non ha sedi — è invariato per costruzione. Il caso è tenuto fermo
da `test_adr018_due_sedi_sulla_stessa_fascia_non_bloccano_max_site_changes`
(`tests/test_solver_sites.py`), verificato per mutazione: ripristinando il
conteggio a insiemi, `solve()` torna `INFEASIBLE`.

---

## ADR-020 — La copertura è per alunno: l'unità è l'atomo, l'alternativa è un dato

**Decisione.** `structural:coverage` misura l'**atomo** — la combinazione di
parti in cui sta un alunno, una per partizione ([ADR-017](#adr-017--parti-di-partizioni-diverse-della-stessa-classe-confliggono)) — e non
la parte. E il piano di studi smette di essere letto come se ogni sua riga
fosse dovuta da ogni alunno: le righe **in alternativa** si dichiarano tali
(`Service.election_group`), e di un gruppo l'alunno ne segue **esattamente
una**.

Con meno di due partizioni l'atomo *è* la parte e la chiave non cambia di un
bit; il piano dell'atomo è quello della parte che lo dichiara, e se **due**
parti della stessa combinazione ne dichiarano di diversi l'unità **non si
misura**: si nomina l'errore (`ambiguous_study_plan`).

**Alternative scartate.**

1. **Portare solo l'unità sull'atomo.** Non basta, e la misura lo dice: il caso
   che aveva aperto la voce — IRC e attività alternativa — è una classe con
   **una sola** partizione, dove l'atomo *è* la parte. Chiude il lato
   osservato e lascia intatto quello atteso.
2. **Un `StudyPlan` per combinazione.** Chiude entrambi i lati, ed è misurato
   che funziona, ma materializza gli atomi come anagrafica — quattro piani per
   una 3A articolata con IRC — che è esattamente ciò che ADR-017 ha deciso di
   non fare. E costa dove costa di più: nei dati che una scuola deve inserire.
   ⚠ Il colpo di grazia è che quel documento **non esiste**: nessun quadro
   orario ministeriale descrive «il curriculum dell'alunno che fa religione e
   francese», quindi nessun import potrebbe alimentarlo.
3. **Il monte ore tripartito** (`reduced_minutes` / `split_minutes`). È la
   risposta di EDT a una domanda **diversa**: `Sdop.` è la *durata con alunni
   sdoppiati*, cioè la stessa materia divisa in gruppi, non due materie in
   alternativa. Non chiude il lato atteso, e resta da osservare per conto suo.
4. **Fondere i piani delle parti** quando la combinazione ne porta due. Sarebbe
   inventare il campo che ADR-017 ha rifiutato, e in silenzio.

**Motivo.** L'atteso della copertura è il piano **intero**, cioè il curriculum
di *un* alunno: la lettura è giusta, l'unità no. Un alunno non sta in una
parte, sta in una combinazione di parti; e il piano di classe è un **catalogo**
— contiene le righe che la classe riceve, non quelle che ogni alunno deve.
Senza il primo pezzo la copertura perde le ore ricevute attraverso l'altra
partizione; senza il secondo dichiara che chi fa religione è debitore dell'ora
di alternativa. Misurato prima della correzione: **quattro** scostamenti
inesistenti su una classe sdoppiata due volte, **due** sulla classe italiana
più ordinaria che ci sia.

Il dato che mancava non è «il piano dell'atomo»: è «questa riga non è dovuta da
tutti», ed è un dato che **EDT ha già**. La colonna `MS` del servizio
(*Modalità di scelta*, FR `Modalité d'élection`) porta sette codici — `N`
Normale, `O` Obbligatoria, `F` Facoltativa, `L` Accademica, `D` DNL, **`R`
Religioso**, `X` Extra — e le durate del servizio in EDT sono **quattro**, non
tre: `H/Classe` (*Durée en classe*) e `H/Al.` (*Durée par élève*) sono due
quantità distinte, ed è la distinzione che qui mancava.
📦 [piani-di-studi.md](edt/piani-di-studi.md), [estratti/stringhe-localizzazione.md](edt/estratti/stringhe-localizzazione.md).

**Conseguenze.**

- `Service.election_group` è la forma **minima** del meccanismo: un'etichetta,
  non l'enumerazione a sette codici. ⚠ `MS` è nota **dalle stringhe** e non è
  mai stata osservata in UI: l'enum si copia quando lo sarà, non prima
  ([todo.md](todo.md), O6).
- `Finding` porta un campo `group`, per la ragione già misurata su `subject`:
  il messaggio è fuori dalla chiave, quindi due gruppi insoddisfatti sulla
  stessa unità collasserebbero in un verdetto solo.
- Le risorse di un finding di copertura possono ora essere **chiavi-atomo**
  (stringhe). `Finding.resources` lo prevedeva già; i nomi leggibili passano
  da `state.resource_names`, che gli atomi li contiene.
- La copertura resta `PLACEMENT_INDEPENDENT`: nessun builder, nessun effetto
  sul modello CP-SAT.
- **D1 di [todo.md](todo.md) è sciolta**, e con essa il blocco sull'import: ciò
  che una scuola deve inserire in più è un'etichetta sulle righe in
  alternativa — una riga del piano, per un liceo — invece di un piano per
  combinazione.

**Emendamento 2026-08-29 — `MS` osservata: EDT ha il campo, non il dato.**

La colonna è stata vista in UI sulla base del produttore, e il tooltip conferma
il nome (*«Modalità di scelta del servizio»*). Ma è **vuota su tutte le righe**,
e la riga che conta lo dice meglio di tutte: `RELIGIONE` è un servizio ordinario
del piano — `Alu. 390`, `H/Classe 1h00`, `H/Al. 1h00` — dovuto da **tutti** gli
alunni, senza alternativa e senza modalità di scelta.

⚠ Va quindi corretta una frase del **Motivo**: dove dice che «è un dato che EDT
ha già», l'affermazione dimostrata è più debole — EDT ha la **colonna** dove il
dato starebbe, e non la riempie nemmeno nella propria base di riferimento. Le
due prove citate valgono ancora ma non sono *esercitate*: su questa base
`H/Al.` = `H/Classe` su ogni riga, perché non c'è nessuno sdoppiamento.

**La decisione non cambia, e semmai si rafforza.** Se la base del produttore
non distingue chi fa religione da chi fa alternativa, allora **nessun import**
poteva darci quel dato — che è esattamente l'argomento con cui era stata
scartata l'alternativa 2. `Service.election_group` va quindi dichiarato per
quello che è: **nostra estensione**, non traduzione di `MS`.

🔑 **E la tendina di `MS`, aperta lo stesso giorno, dice perché — sono due
domande diverse, non due risposte alla stessa.** I codici sono **otto** e non
sette (mancava `S`, ed è quello che conta): `S = Senza` è `Tronc commun`, il
**percorso curricolare**, cioè la riga che tutti seguono; `O F N X L R D` sono
tutte forme di **opzione**, con `R` a nominare il caso religioso.

L'asse di `MS` è dunque *«tronco comune oppure opzione»*. Non dice **quali
opzioni siano alternative fra loro**, che è la sola cosa che `election_group`
dice. I due meccanismi sono **complementari**:

| Domanda | Chi risponde |
|---|---|
| «questa riga è dovuta da tutti?» | `MS` (`S`/vuoto contro il resto) |
| «di queste righe l'alunno ne segue esattamente una» | `Service.election_group` |

⚠ Ne discende una cosa che il nostro modello **non** fa ancora: una riga marcata
opzione ma **fuori** da ogni gruppo di elezione è oggi contata come dovuta da
tutti, cioè lo stesso falso positivo che ADR-020 ha corretto, su un altro
ingresso. Nessun dato lo esercita — `MS` è vuota su entrambe le basi — quindi
resta una **decisione** e non un difetto: → [todo.md](todo.md), O6.

(⚠ Correzione di passaggio: `L` è `Locale`, non «Accademica». Il francese
`académique` è l'aggettivo di *académie*, la circoscrizione scolastica. Falso
amico, → [glossario-it-fr.md](edt/glossario-it-fr.md).)

**Data.** 2026-08-28

---

## ADR-021 — La fase 1 conta le aule; la fase 2 le assegna

**Decisione.** Il modello del **piazzamento** porta una famiglia di vincoli in
più, `structural:room_pool`: per ogni fascia e per ogni insieme *S* di aule, le
attività le cui candidate stanno **tutte** dentro *S* non possono superare i
posti di *S*. L'assegnazione resta una **seconda fase** con i suoi criteri, i
suoi due livelli e la sua rinuncia: non cambia niente di
[ADR-015](#adr-015--perimetro-funzionale-di-v1-le-sei-decisioni-contese) né
della spec dell'assegnazione. Cambia una cosa sola, ed è quella che D3
chiedeva: **contare non è assegnare**.

**Alternative scartate.**

1. **Accettare le rinunce come conseguenza dichiarata.** È ciò che il progetto
   ha scritto per un giorno — *«non è un difetto del modello: è la conseguenza
   dichiarata di assegnare le aule dopo»* — e la parte falsa è il **dopo**.
   Assegnare le aule dopo non obbliga a **contarle** dopo, e il prezzo era
   misurato: **8 richieste su 92** senza aula, su un dataset che ha quattro
   sole materie di laboratorio.
2. **Un tetto sull'unione delle candidate**, cioè «quante aule esistono in
   tutto per queste attività». Non morde: misurato sul Fermi, su **nessuna**
   delle 26 celle contese l'unione era in deficit, e le rinunce c'erano lo
   stesso. Il deficit vive in un **sottoinsieme** — è Hall, non un totale.
3. **Assegnare le aule dentro la fase 1**, cioè una variabile per (attività,
   aula) nel modello grande. Chiude il problema e ne apre uno peggiore:
   distrugge la forma del prodotto, che è di EDT — criteri propri
   (`TypeChoixOptimSalle`), ottimizzatore dedicato (`FicheEdt_OptimiseurSalles`)
   e una `ripartizione delle aule` distinta dal calcolo — e moltiplica il
   modello per il numero di candidate.
4. **Il ritorno indietro dalla fase 2 alla fase 1** quando una rinuncia
   accade. Dichiarato fuori scope da §6 della spec dell'assegnazione, e resta
   fuori: è la strada che costa di più e che nessun prodotto osservato
   percorre.

**Motivo — ed è un'osservazione, non una preferenza.** In EDT le aule si
contano **mentre si piazza**. Tre fonti indipendenti, tutte già nel repo e
tutte lette male fino a oggi:

- la causale *«il gruppo di aule ha raggiunto il suo picco d'occupazione»* sta
  nella famiglia `AffSco_UtilDiagnostic`, che è la diagnostica del
  **piazzamento** — l'elenco delle ragioni per cui un'attività non si piazza
  ([diagnostica.md](edt/diagnostica.md));
- nel risolutore passo-passo il pannello `Attività da piazzare` conta **tutte e
  cinque** le risorse (`Personale 0`, `Aule 0`, `Materiali 0`, …) e le risorse
  in conflitto **diventano rosse, aule comprese**
  ([motore-risoluzione.md](edt/motore-risoluzione.md));
- il `Qtà` dell'aula è una **capacità simultanea**, con le colonne calcolate
  `Assegnate` / `Picco d'occ.` ([aule.md](edt/aule.md)).

Ciò che l'ottimizzatore dedicato decide è *quale* aula fra le ammissibili, e i
suoi cinque criteri (`tcosSallePref`, `tcosCapacite`, …) sono tutti criteri di
**scelta**. Nessuno di essi conta i posti: quel conto è già stato fatto.

**Il metodo: Hall, non il totale.** L'insieme colpevole si trova come nella
fase 5 dell'analisi — flusso massimo su sorgente → attività → aule candidate →
pozzo, e il lato sorgente del taglio minimo *è* l'insieme deficitario
(`domain/analysis/flow.py`, già scritto per il violatore di Hall). Il checker
nomina l'**unione delle candidate del gruppo colpevole**, non il taglio grezzo:
i due contengono le stesse attività, ma il taglio può portarsi dietro aule che
nessuno di quel gruppo chiede, e mandare a smontare l'aula sbagliata è il
difetto peggiore di una diagnostica.

Il builder posta i tetti sulla **chiusura per unione** degli insiemi di
candidate dichiarati: un violatore stretto è sempre di quella forma, perché
restringere *S* all'unione delle candidate del gruppo non perde nessuna
attività e non guadagna nessun posto. La chiusura è esponenziale nel numero di
insiemi **distinti** — uno per materia che chiede un laboratorio, cioè pochi —
e oltre `TETTO_POOL = 256` si tronca. La troncatura non rende il modello
sbagliato: toglie tetti, quindi ammette di più, e ciò che passa lo nomina il
checker.

**Il vincolo è sano per costruzione.** Vieta esattamente le configurazioni che
*nessuna* assegnazione d'aula potrebbe servire — il principio dei cassetti —
quindi non toglie mai al piazzamento un orario che la fase 2 saprebbe
completare. Non può introdurre scarti nuovi: può solo spostare un problema da
«rinuncia d'aula» a «collocazione diversa».

**Misure.** Fermi, con le aule del nostro dataset:

| | prima | dopo |
|---|---|---|
| richieste d'aula servite | **84 / 92** | **92 / 92** |
| rinunce della fase 2 | 8 | 0 |
| deficit di Hall dopo la fase 1 | 8, su 7 celle | 0 |
| attività scartate dalla fase 1 | 0 | 0 |
| constraint del modello di piazzamento | 1116 | 1536 |
| secondi della fase 1 | 1,07 | 1,27 |

🔑 Il deficit misurato **era esattamente** il numero di rinunce — 8 e 8 — e
stava tutto su un insieme solo, `{LAB-FIS, LAB-INF}`, ripetuto su sette celle.
Non è una coincidenza: la fase 2 rinuncia una volta per ogni unità di deficit
che la fase 1 le lascia, perché non ha altra mossa.

**Conseguenze.**

- Il registro passa a **ventisette builder su trenta checker**. I tre senza
  builder restano tre, e `structural:room_assignment` è ancora fra loro: le due
  chiavi rispondono a due domande diverse — *quante* aule servono in una
  fascia (si sa prima, ed è piazzamento) e *quale* aula tocca a ognuno
  (seconda fase).
- ⚠ **Un difetto trovato integrando, non prevedendo.** Il filtro `resources` di
  `trial_placements` erano le **chiavi di occupazione** dell'attività, e
  un'aula con due candidate non è una chiave — `activity_tokens` la mette fra i
  token solo a candidata unica. S.P., il violatore di Hall e la classifica dei
  vincoli erano quindi ciechi all'intera famiglia: il checker girava e scartava
  ogni pool, perché nessuno toccava le risorse chieste. Il filtro ora
  comprende le candidate dichiarate. Allargarlo è sempre sano — è
  un'ottimizzazione, e un'ottimizzazione più larga costa, non sbaglia.
- Il checker conta un'aula **rossa** come zero posti e una **gialla** come
  posti pieni, e il builder fa lo stesso, così che l'oracolo differenziale
  confronti due letture identiche. ⚠ La fase 2 invece toglie anche le gialle
  (`RoomContext._filtra`): resta quindi un angolo in cui la fase 1 può
  riempire una fascia che la fase 2 non serve. Nessun dato lo esercita — è un
  debito, → [todo.md](todo.md).
  ✅ **Corretto il 2026-08-31 (L6bis).** L'ondata 5 dell'Alighieri il dato lo
  ha costruito, e il debito è diventato una rinuncia misurata. La gialla ora
  azzera il posto come la rossa, nel checker e nel builder; il builder legge
  l'override per **categoria** di risorsa (`ignora_opzionali`), lo stesso che
  legge la fase 2, il checker no — legge un orario, non i parametri di un
  calcolo. L'argomento che teneva la vecchia lettura («un finding HARD per un
  ostacolo che duro non è») si rovescia guardando chi paga: l'ostacolo è duro
  *finché non lo si autorizza*.
- L'assegnata non conta come fissa: `Placement.assigned_room` è una
  ripartizione rivedibile — `solve_rooms` la tratta da preferenza, non da
  vincolo — quindi contarla inventerebbe deficit che la fase 2 scioglie da
  sola. Un'assegnazione **senza** candidate dichiarate è invece un fatto, e
  consuma.

**Data.** 2026-08-29

---

## ADR-022 — L'allineamento genera l'attività complessa: una collocazione, o nessuna

**Decisione.** Le attività che condividono `alignment_ident` sono **una**
collocazione. Il modello lo impone con `structural:alignment` (ventottesimo
builder, trentunesimo checker): tutti i membri del gruppo sulla **stessa
cella**, o tutti **scartati**. È un vincolo **hard** e **non alleggeribile**.

**Alternative scartate.**

1. **«La stessa cella *se* entrambe piazzate».** È la forma debole, e sarebbe
   soddisfatta anche dal gruppo mezzo scartato — cioè dalla stessa mezza
   classe che resta a scuola senza lezione, che è il danno da cui l'intera
   decisione nasce. Lo XSD non lascia spazio: i corsi allineati *seront
   regroupés au sein d'un même cours complexe*, e un'attività si piazza o si
   scarta, non a metà.
2. **Una famiglia alleggeribile**, con una quota come le altre. Alleggerire un
   allineamento significherebbe **scomporre l'attività complessa**, cioè
   cambiare l'anagrafica e non un vincolo. EDT infatti non lo elenca fra le
   famiglie che il piazzamento può allentare.
3. **Vietare le durate diverse dentro un ident.** Lo XSD dà all'attività
   complessa una durata sola, quindi il caso non dovrebbe esistere; se esiste
   nel dato, l'intersezione dei domini fa già la cosa giusta (la più lunga
   restringe l'inizio comune) e non serve inventare un divieto che
   l'anagrafica non dichiara.
4. **Un finding sul gruppo intero** invece che sulle coppie. Più leggibile e
   **non monotono**: piazzare un terzo membro *sulla cella giusta*
   allargherebbe `activities`, cambierebbe la `Finding.key` e
   `admissible_starts` leggerebbe la cella corretta come inammissibile. Una
   voce per coppia in disaccordo è monotona per costruzione.

**Motivo.** 📦 L'annotazione dello XSD `Partenaire_Index` su `Alignement` è
testuale (→ [schema-scambio.md](edt/schema-scambio.md)), e il campo esisteva
dal giorno dello schema senza che nessun builder né checker lo leggesse: dei
16 allineamenti del banco Alighieri, **14 uscivano dal solve senza una sola
coincidenza**. Non è cosmetico — è la condizione perché gli sdoppiamenti (voce
✅ di scope v1, [ADR-013](#adr-013--sdoppiamenti-e-raggruppamenti-trasversali-dentro-v1))
producano orari usabili.

**Conseguenze, e due sono sul dato.** Un dominio comune vuoto fa **scartare**
il gruppo, mai `INFEASIBLE` (con `allow_unplaced=False` diventa `INFEASIBLE`,
ed è la domanda «questo vincolo morde?»); congelate in disaccordo fanno saltare
il vincolo, per la metà vietata di
[ADR-018](#adr-018--linput-sporco-non-blocca-il-solver-capacità-residua-e-oracolo-differenziale).
E leggere il campo ha reso visibile che il banco ne dichiarava di falsi:
*sdoppiare non è allineare* (le due metà hanno lo stesso docente e non sono mai
simultanee), e **un ident per attività complessa** e non per coppia di servizi
— 📦 *«il convient de définir autant d'alignements que de cours complexes
souhaités»*.

**Data.** 2026-08-31

---

## ADR-023 — Il vincolo di sede è un tetto di capienza: un insieme non viaggia

**Decisione.** `structural:site_transition` non vieta più che due sedi diverse
tocchino la stessa chiave di occupazione a distanza insufficiente: chiede che i
due carichi **ci stiano**, `carico(sa, s) + carico(sb, t) <= capienza
simultanea`. Il checker conta con la stessa disuguaglianza.

**Alternative scartate.**

1. **Esentare le chiavi con `simultaneous_capacity > 1`.** Era il candidato
   naturale — *un pool non viaggia* — ed è quello che il debito nominava. Ma
   vale anche per l'aula col `Numero di aule` di EDT, che invece un luogo ce
   l'ha, e un'esenzione secca toglierebbe il vincolo dove serve.
2. **Esentare per tipo di risorsa** (aule e materiali non viaggiano, docenti e
   classi sì). Toglie il vincolo alle aule senza metterci niente al posto, e
   il tipo non è la proprietà giusta: la sede è dell'**attività**, non della
   risorsa.
3. **La condizione esatta su tutta la finestra di trasferimento** invece che a
   coppie. Più stretta e più giusta, ma cambia la forma del vincolo (oggi è a
   coppie, come il checker); la forma a coppie è più larga, ed è il verso in
   cui un checker non inventa violazioni.

**Motivo.** Il tragitto lo fa un **corpo**, e una chiave a capienza cumulativa
è un *insieme*: quattro carrelli di portatili sono della scuola, non di un
edificio, e servono l'inglese alla centrale mentre l'informatica è in
succursale senza che nessuno si sposti. La domanda «due sedi si toccano?» è
sbagliata per un insieme; quella giusta è «ci stanno?».

🔑 **E la generalizzazione risolve l'obiezione dell'alternativa 1 da sé.** A
capienza 1 — ogni docente, classe, parte, atomo — la nuova regola coincide
**riga per riga** con la clausola booleana di prima: due carichi valgono almeno
2, la capienza è 1, la coppia resta sempre vietata. Cambiano solo le due
risorse per cui la vecchia regola diceva il falso.

**Conseguenze.** Il ramo `s == t` (la riparazione «Important 1 / Ruling 33»)
è ora **implicato** da `structural:occupation` — il carico di un sottoinsieme
di una cella non può superare la capienza se il totale non la supera — e resta
postato solo perché ogni builder dev'essere corretto da solo.

⚠ **E la guardia di ADR-018 resta, generalizzata**: il tetto non si posta
quando le **sole congelate** lo hanno già superato. La prima stesura la tolse
credendo che `residual_cap` la contenesse, e il banco che congela ha detto di
no (semi 6 e 9, `INFEASIBLE` sulla prova A): col residuo clampato a zero, ogni
**libera** viene cacciata dalle celle in cui la coppia è già rotta — comprese
quelle in cui già stava. 🔑 La differenza con `structural:occupation`, che
invece clampa e fa bene, è la forma del finding: là la causale nomina *tutte*
le attività della cella, quindi una libera che si aggiunge cambia la chiave;
qui nomina una **coppia**, e la coppia (libera, congelata) esisteva già nella
baseline.

⚠ **[ADR-019](#adr-019--dentro-una-fascia-non-si-viaggia-il-cambio-di-sede-e-il-pareggio-di-collocazione)
resta intatto e ne esce rafforzato**: *dentro una fascia non si viaggia* diceva
che due sedi simultanee valgono zero **cambi**, e aggiungeva che l'impossibilità
la nomina comunque `structural:site_transition`. La prima metà è confermata; la
seconda era vera solo a capienza 1, ed è ora detta con la disuguaglianza giusta.

**Data.** 2026-08-31

---

## ADR-024 — Un criterio di qualità vale quanto la settimana peggiore

**Decisione.** I criteri di qualità (`domain/solver/criteria.py`) si calcolano
**per firma di settimana**, e il valore del livello è il **massimo** fra le
firme. Le firme con le stesse attività attive *sulle chiavi del criterio* si
deduplicano, come in `ResourceBuilder`.

**Alternative scartate.**

1. **L'unione delle settimane**, cioè lo status quo. È il difetto: un'ora
   quindicinale col laboratorio alla seconda fascia e la teoria alla terza dà
   un buco in *ogni* settimana e **zero** sull'unione, perché nell'unione le
   fasce sono contigue. Lo stesso orario valeva 60 minuti per `check_schedule`
   e 0 per il criterio `gaps`.
2. **La somma sulle firme.** Direbbe 360 dove il checker dice 180, e farebbe
   dipendere il valore da **quante firme ha il dataset** invece che da com'è
   l'orario.
3. **La somma pesata per il numero di settimane.** È la quantità **annuale**:
   vera, e con il gradiente migliore dei tre. Ma è di un'altra unità, e
   `Arbitrato.tolleranza` è un numero **nell'unità del criterio** che l'utente
   scrive a mano — «tollero 60 minuti» diventerebbe «tollero 1980».

**Motivo.** La regola della casa: *dove il checker esiste, la definizione si
legge da lì*. Il checker produce un verdetto **per firma** e porta le settimane
in un campo a parte (`Finding.weeks`); la sua unità è la settimana, e 180 è il
numero che conta. Un criterio che ne dicesse un altro misurerebbe qualcos'altro
— è la stessa ragione per cui `B`, nei rami disgiuntivi di
[ADR-018](#adr-018--linput-sporco-non-blocca-il-solver-capacità-residua-e-oracolo-differenziale),
si **legge** chiamando il checker invece di riscriverne la condizione.

**⚠ Il prezzo, dichiarato.** Sul massimo, migliorare una firma che non è la
peggiore non muove il livello. È meno grave di quanto sembri — il massimo
trascina comunque tutte le firme fino al proprio pavimento — ma all'ottimo una
firma già sotto non ha più incentivo a scendere.

**⚠ E il costo moltiplicativo non si paga.** Era la ragione con cui
`quality.py` giustificava l'approssimazione (*«le firme sono una dimensione
moltiplicativa e un anno reale ne ha 35-40»*): con la deduplicazione, su un
dataset a **firma unica** — cioè ogni dataset senza corsi quindicinali né
sostituzioni — non nasce nemmeno una variabile in più e non cambia nessun
numero.

**Data.** 2026-08-31
