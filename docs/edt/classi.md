# Entità EDT — Classi

## Cos'è

Il gruppo-classe (1A, 2A…). Nel dataset Fermi ci sono 10 classi: 1A–5A e 1B–5B, su
due sezioni (A, B), ~26 alunni ciascuna.

## Campi osservati nella UI

Colonne dell'`Elenco delle classi` (Orario > Classi), osservate il 2026-07-26
sulla base di esempio (40 classi):

| Colonna | Cosa contiene |
|---|---|
| `Nome` | |
| `Alu.ins.` / `N.Alu` | alunni inseriti (anagrafica) / numero di alunni previsto |
| `Livelli` | `1°`, `2°`, `3°` — l'entità `Niveau` |
| `Piano di studi` | es. `2° TEMPO NORMALE` |
| `Occ.` | ore occupate, calcolato (31h00–33h00) |
| `Docente coordinatore` | uno per classe nella base |
| `Referente didattico` | ruolo distinto dal coordinatore, vuoto nella base |
| `TOP` | tasso di occupazione, `100%` su tutte |
| **`Aula preferenziale`** | l'aula abituale della classe (= `Classe/Salle` dello schema) |
| **`MMG`** | **Massimo di mezze giornate di lavoro** |
| **`MG`** | **Lavorare solo mezza giornata al giorno** |
| *(colore)* | colore della classe |
| `N.Sedi` | numero di sedi frequentate (`1` su tutte) |

Due note.

**`Aula preferenziale` sta sulla classe, non sulla materia.** È l'unico legame
didattica↔aula che EDT modella nativamente, e riflette come funziona una scuola
reale: la classe ha la sua aula e si sposta solo per laboratorio o palestra. Vedi
[aule.md](aule.md).

**`MMG` e `MG` sono vincoli orari della classe**, e sono **gli stessi due che
esistono sul docente** (`Massimo di mezze giornate di lavoro` con la sua opzione
`Lavorare solo mezza giornata al giorno`, vedi [vincoli.md](vincoli.md)). Il
`*-*` è il valore "non impostato".

È l'ennesima conferma della **genericità sulla risorsa**: non esiste una famiglia
di vincoli "del docente" e una "della classe": esiste una famiglia di vincoli
orari che si applica a entrambi. Nel nostro schema è una tabella sola con una FK
polimorfica, non due.

Otto classi su 40 hanno il **triangolo di espansione**: sono quelle con parti
(`1 A/A`, `1 A/R`, `1 B/A`, `1 B/R`, `1C`, `1F`, `1H`, `2D`). `1C` e `1F` sono
due delle quattro che nel file portano le parti `_REL`/`_ALT` — vedi
[gruppi.md](gruppi.md).

Attributi impliciti nel dataset del Fermi:

- **Sezione** (A / B).
- **Anno / livello** (1–5), da cui deriva il regime **biennio** (anni 1–2) vs.
  **triennio** (anni 3–5).
- **Monte ore settimanale**: 27 h nel biennio, 30 h nel triennio. Non è un numero
  libero della classe: è la somma del quadro orario (monte ore per materia per
  livello) — vedi [`data/liceo-fermi/classi.md`](../../data/liceo-fermi/classi.md).

## La classe nello schema di scambio 📦

Colma in parte il "da completare" qui sopra
([schema-scambio.md](schema-scambio.md)):

```
Classe
├── @Nom, @Couleur, @ID_Partenaire
├── Niveau               (0..1)   ← l'anno/livello, entità a sé
├── Mef                  (0..N)   ← PIÙ piani di studi per classe
├── PartieDeClasse       (0..N)
├── ProfesseurPrincipal  (0..N)   ← più di un coordinatore è ammesso
├── Salle                (0..1)   aula abituale della classe
└── Etablissement        (1..1)   obbligatorio: l'istituto di appartenenza
```

Tre osservazioni:

- **`Niveau` è un'entità, non un intero.** L'anno di corso ha anagrafica propria
  (`Ident` + `Libelle`), e compare anche su `Mef`. La distinzione biennio/triennio
  dedotta qui sopra non è quindi un attributo della classe: si legge attraverso il
  livello e il piano.
- **`Mef` è `0..N`.** ⚠ Una classe può avere più piani di studi. Non è il caso del
  Fermi (un piano per classe), ma è il caso delle **classi articolate** — da tenere
  presente perché rompe l'ipotesi `classe → 1 piano` che il nostro schema
  adotterebbe naturalmente.
- **`Etablissement` è obbligatorio** e si riferisce alla tabella
  `EtablissementsGeres`: il formato prevede nativamente il **multi-istituto**. Fuori
  scope per noi, ma spiega perché `Site` compare un po' ovunque.

Nessun campo "monte ore" sulla classe: conferma che il monte ore sta sul piano di
studi e non sulla classe, come già dedotto.

## Semantica dedotta

- Il **biennio/triennio** determina quali materie esistono e con quante ore (es. STG
  solo nel biennio; STO e FIL solo nel triennio). È quindi una dimensione del quadro
  orario, non solo un'etichetta.

## ⚠️ Una classe non è un blocco monolitico

L'ipotesi ingenua "una classe = un blocco che si muove insieme" è **falsa**: gli
sdoppiamenti e i corsi a effettivo ridotto spezzano la classe in **gruppi**. Il
campo [`Al./Rid.`](materie.md) non avrebbe dove appoggiarsi se il gruppo non
esistesse come entità.

I gruppi sono un'entità distinta dalle classi: vedi [gruppi.md](gruppi.md) e
[ADR-004](../decisioni.md).

## Classi previsionali

Osservata (2026-07-09) la sezione **"Classi previsionali"**: la classe della fase di
*pianificazione* (prima che esista l'orario), agganciata a un piano di studi.
Colonne: **Nome, Piano di studi, Alunni inseriti, Livello, Docenti Coordinatori**;
opzione "Raggruppa per livello"; pulsante **"Recupera le classi dall'orario"**
(quindi classi previsionali e classi d'orario sono due insiemi distinti,
sincronizzabili).

Testo introduttivo di EDT (letterale): due modalità di calcolo per i **bisogni
previsionali** e per la **TRCD**:

1. **In funzione del numero di alunni delle classi previsionali** — "permette di
   calcolare i bisogni previsionali e la TRCD, nonché di gestire gli allineamenti e
   la creazione delle attività".
2. **In funzione del numero di alunni dei piani di studi** — solo bisogni
   previsionali e TRCD, passando direttamente all'ambiente «Bisogni previsionali».

Quindi: si può pianificare **senza creare le classi**, direttamente dagli effettivi
dei piani (`Al./Cl.`), ma solo la modalità con classi previsionali dà **allineamenti
e creazione delle attività** (le lezioni concrete). Acronimo **TRCD** ancora da
decifrare (tabella di ripartizione per disciplina?).

Osservazioni dalla creazione delle 10 classi (2026-07-09):

- Creata la classe con nome + piano, il **Livello deriva dal piano** e la classe
  **eredita automaticamente i servizi del piano**: il pannello `<Classe> – Servizi`
  mostra il quadro orario completo (27h00 su 1A) senza alcun inserimento. Il quadro
  orario si scrive una volta sul piano e cascata sulle classi
  ([ADR-003](../decisioni.md)); il pulsante **"Dettaglia il servizio"** suggerisce
  l'override per-classe (da osservare).
- Le colonne dei servizi della classe ricalcano quelle del piano
  ([piani-di-studi.md](piani-di-studi.md)) con nomi flessi: `Classe` (=H/Classe),
  `Ridotta`, `Sdop.`, `H. Alu.`; `Alu./…` mostra sempre il 15 ereditato.
- In basso c'è **"Ripartizione del numero di alunni dei piani di studi per
  classe"** (matrice piano × classi): è **l'input degli effettivi previsti** per
  classe (compilata a 26 per le 10 classi del Fermi). Da qui EDT calcola i
  [bisogni previsionali](bisogni-previsionali.md). Il totale del piano appare in
  rosso se non coincide con gli alunni reali (anagrafica, 0 per noi) — warning
  ignorabile in previsionale.

## Formazione Classi — fuori scope

Osservata (2026-07-09) e **saltata deliberatamente** la sezione "Formazione
Classi": composizione delle classi a partire dagli **alunni reali** (anagrafica
individuale; criteri Rendimento/Comportamento/Assenteismo/BES; preferenze di
raggruppamento e separazione fra alunni). È un problema di ottimizzazione diverso
dalla generazione dell'orario: il nostro generatore assume **classi già formate**
con un effettivo previsto — l'intera catena previsionale funziona senza creare un
solo alunno (verificato sui [bisogni](bisogni-previsionali.md)).

## Implicazioni per il nostro modello

- La classe ha una FK verso la sezione e un attributo anno/livello.
- Il regime biennio/triennio è derivabile dall'anno, ma pilota il quadro orario:
  modellare la relazione classe → (materia, ore) passando per il livello.
- Prevedere fin da subito la relazione classe → parti → gruppi, che è
  **molti-a-molti** e non uno-a-molti ([gruppi.md](gruppi.md)).
- La classe porta un'**aula preferenziale** (FK opzionale verso l'aula) e
  probabilmente vincoli propri sulle mezze giornate (`MMG`/`MG`).

## Dataset di esempio

Elenco classi e quadro orario del Liceo Fermi:
[`data/liceo-fermi/classi.md`](../../data/liceo-fermi/classi.md).
