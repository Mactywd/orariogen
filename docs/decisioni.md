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
produzione, di cui questo generatore è modulo. Nota: la classe di concorso è **nostra
estensione**, non un campo EDT osservato. Vedi
[docs/edt/discipline.md](edt/discipline.md).

**Data.** 2026-07-09

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
