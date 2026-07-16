# Entità EDT — Piani di studi

## Cos'è

Il **piano di studi** è il curriculum/indirizzo (es. Liceo Scientifico ordinario):
il livello di raggruppamento *sopra* le classi. È il posto naturale dove agganciare
il quadro orario (monte ore per materia) e i default d'effettivo.

## Campi osservati nella UI

| Campo | Tipo | Note |
|---|---|---|
| Nome | testo (≤ 40 car.) | **Obbligatorio.** La denominazione estesa. |
| Piano di studi | testo (≤ 6 car.) | **Obbligatorio.** La **sigla** del piano (è questo il codice corto, non "Nome" — invertito rispetto al pattern Codice/Nome di discipline e materie). |
| Alunni inseriti | numero | **Calcolato** (confermato: `0` su tutti i piani appena creati, senza input). Conteggio degli alunni collegati al piano. |
| Livello | enum | Obbligatorio. Valori osservati: **primo, secondo, terzo, quarto, quinto** = l'**anno di corso**. Quindi un piano di studi = indirizzo × anno (es. "Scientifico, terzo anno"), non l'indirizzo intero. |
| Al./Cl. | numero | Tooltip: *"numero alunni atteso per classe per il piano di studio"*. **Default d'effettivo per le classi del piano** → altro livello della cascata (piano → classe), come `Al./Rid.` per le materie ([ADR-003](../decisioni.md)). |
| Spec. | ? | "Specializzazione". Semantica da osservare. |

## Implicazioni per il nostro modello

- Entità `study_plan` sopra la classe: le classi puntano al piano; il quadro orario
  (materia × ore settimanali) appartiene al piano, non alla singola classe.
- `Al./Cl.` = default nullable d'effettivo atteso, ereditato dalle classi
  (cascata, `NULL` = eredita).
- Il piano è **indirizzo × anno** (Livello = primo…quinto): la granularità giusta
  per il quadro orario, che al Fermi cambia fra biennio e triennio
  ([classi.md](classi.md)). Nel nostro schema: `study_plan(track, year)` con il
  quadro orario appeso al piano.

## I servizi — il quadro orario del piano

Selezionando un piano si apre il pannello **"Servizi"** (`<Piano> – Servizi`): qui
si risponde alla domanda "dove sta il quadro orario". Un **servizio** è una riga
materia × ore appartenente al piano di studi. Colonne osservate (tooltip letterali,
valori dalla compilazione di SCI1, 2026-07-09):

| Colonna | Tooltip / semantica | Osservato su SCI1 |
|---|---|---|
| A | *"Stato di attivazione del servizio"* | pallino verde (attivo). Il flag "Visualizza i servizi inattivi" filtra i disattivati. |
| Materia (Nome, Codice) | FK → Materie | |
| Disciplina | derivata dalla materia (mostrata `Nome (COD)`) | non si inserisce |
| Alu. | *"Numero di alunni del piano di studi che segue la materia"* | `-` finché non ci sono alunni (coerente con "Alunni inseriti" calcolato) |
| Coeff. | *"Coefficiente del servizio"* | default **`60/60`** — peso della durata (minuti conteggiati / minuti reali?), da approfondire |
| MS | *"Modalità di scelta del servizio"* | vuoto — probabile rilevante per materie opzionali/a scelta |
| Istituto: H/Classe | **ore settimanali per classe** — il monte ore del quadro orario | input (`4h00`…) |
| Istituto: Ridotto | *"Durata con alunni ridotti"* | vuoto |
| Istituto: Sdop. | *"Durata con alunni sdoppiati"* | vuoto — **quota ore in sdoppiamento**: i gruppi si dichiarano qui ([gruppi.md](gruppi.md)) |
| Istituto: Alu./… | *"Numero di alunni ridotto del servizio"* | **`15` su tutte le righe, mai digitato** → è l'`Al./Rid.` delle materie che **eredita in cascata** fin dentro il servizio ([ADR-003](../decisioni.md)) |
| Istituto: H/Al. | *"Durata per alunno"* | = H/Classe quando non c'è sdoppiamento |

Il monte ore è quindi **tripartito per servizio**: `H/Classe` (classe intera) +
`Ridotto` (effettivo ridotto) + `Sdop.` (sdoppiata in gruppi). "Totale delle ore di
servizio" somma la colonna: per il Fermi **27h00 al biennio (verificato su SCI1)**,
30 atteso al triennio.

## Aperto / da osservare

- Semantica di **Spec.** sul piano.
- Semantica fine di **Coeff.** (quando si usa un valore ≠ 60/60?) e di **MS**
  (modalità di scelta — materie opzionali?).
- Cosa comporta un servizio **inattivo**.
- Compilare **Ridotto/Sdop.** su un servizio (es. ING) per osservare come nascono i
  gruppi → [gruppi.md](gruppi.md).
