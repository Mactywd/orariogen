# Entità EDT — Lo schema di scambio `Partenaire_Index`

> Fonte 📦: `Schema/Partenaire_Index.xsd` e le sei versioni precedenti, dentro
> l'installazione di EDT 2026 Monoposto. È uno schema **ufficiale Index
> Education**, annotato in francese dall'autore. A differenza dell'osservazione
> in UI, qui i nomi dei campi, i tipi, le cardinalità e l'obbligatorietà sono
> **dichiarati formalmente**, non dedotti.

## Cos'è

Il formato con cui un software terzo ("partenaire") **importa dati in EDT**.
Namespace corrente `http://www.index-education.com/importpartenaireindexV4.6`.

Nell'installazione ci sono sette versioni affiancate:

| File | Namespace | Elementi |
|---|---|---|
| `Partenaire_IndexV4.0.xsd` | (nessuno) | 84 |
| `Partenaire_IndexV4.1.xsd` | (nessuno) | 86 |
| `Partenaire_IndexV4.2.xsd` | (nessuno) | 89 |
| `Partenaire_IndexV4.3.xsd` | (nessuno) | 91 |
| `Partenaire_IndexV4.4.xsd` | `…V4.4` | 145 |
| `Partenaire_IndexV4.5.xsd` | `…V4.5` | 145 |
| `Partenaire_Index.xsd` | `…V4.6` | 147 |

Il salto 4.3 → 4.4 (+54 elementi) è dove il formato si allarga; 4.5 → 4.6 non
introduce elementi nuovi.

## La scoperta che conta: è un formato di *input*

Lo schema **non contiene**:

- nessun elemento di **piazzamento** — un `Cours` ha una durata ma non ha giorno
  né ora;
- nessun **vincolo** — zero occorrenze di `Contrainte`, `Indisponibilite`,
  `Absence`.

Trasporta cioè il **problema**, non la soluzione: anagrafica, struttura e
l'elenco delle attività da collocare. Vincoli e collocazione restano interni a
EDT.

**Implicazione per noi.** Questo è esattamente il contratto di ingresso di un
generatore di orari. Se il nostro schema Django sa esprimere `Partenaire_Index`
V4.6, sa ricevere i dati di qualunque gestionale che già dialoga con EDT — e
sappiamo che l'elenco è chiuso: nient'altro entra da lì.

## Il modello del tempo

```
GrilleHoraire
├── @NombreJoursParCycle        giorni per ciclo (non per settimana: il ciclo può eccedere la settimana)
├── @NombreSequencesParJour     sequenze per giorno
├── @NombrePlacesParSequence    posizioni per sequenza
└── PlacesParJour
    └── Place  (1..N)
        ├── @Numero             la prima posizione del giorno è 0
        ├── @LibelleHeureDebut  time
        └── @LibelleHeureFin    time
```

Tre livelli: **ciclo → sequenza → posizione**. La *posizione* (`Place`) è
l'unità atomica; la *sequenza* la raggruppa. Un'attività dichiara la durata in
entrambe le unità (vedi `Cours` sotto).

⚠ Da chiarire: cosa distingue in pratica sequenza e posizione quando
`NombrePlacesParSequence = 1`. Ipotesi da verificare: la posizione serve alle
scuole con mezz'ore o quarti d'ora, la sequenza è "l'ora di lezione".

**Implicazione per noi.** Il nostro slot non va modellato come "ora di lezione"
piatta: serve una griglia a due livelli e un ciclo che può essere ≠ 7 giorni.
Il prototipo CP-SAT usa 5 giorni × 6 ore fisse — è un caso particolare di
questo, non il caso generale.

## Piani di studi (`Mef`)

`Mef` = *Module Élémentaire de Formation*, cioè il **piano di studi**.

```
Mef  — "Formation+Specialite constituent la clé unique"
├── @Ident, @Libelle, @Code
├── @Formation   ─┐ chiave unica composta
├── @Specialite  ─┘
├── Niveau        (0..1)
└── Matiere       (0..N)
    ├── @Ident
    ├── @DureeMinutesClasse      monte ore a classe intera
    ├── @DureeMinutesDedoublee   monte ore a classe sdoppiata
    └── @DureeMinutesReduite     monte ore a effettivo ridotto
```

**Tre monte ore per materia, non uno.** Una materia dentro un piano di studi
porta fino a tre durate distinte a seconda che la classe sia intera, sdoppiata
o a effettivo ridotto.

Questo è quasi certamente ciò che stanno le colonne **`Ridotto`** e **`Sdop.`**
dei servizi del piano di studi, rimaste senza semantica in
[piani-di-studi.md](piani-di-studi.md) — ⚠ da confermare in UI accostando i
valori.

Conferma anche la chiave del piano: `Formation` + `Specialite`, che nel dataset
Fermi corrisponde a *indirizzo × anno*.

## Classi, parti di classe, gruppi

```
PartieDeClasse
├── @Nom
└── @LibellePartition        etichetta della partizione di appartenenza

Classe
├── @Nom, @Couleur
├── Niveau               (0..1)
├── Mef                  (0..N)   ← una classe può avere PIÙ piani di studi
├── PartieDeClasse       (0..N)
├── ProfesseurPrincipal  (0..N)
├── Salle                (0..1)   aula abituale
└── Etablissement        (1..1)

Groupe
├── @Nom, @Couleur
├── Classe               (0..N)  + @LibellePartition
│                        "Libelle de la partition de la classe à l'origine du groupe"
└── PartieDeClasse       (0..N)
```

Il meccanismo è a due stadi: una classe si **partiziona** (partizione nominata →
parti di classe), e un **gruppo** si costruisce prendendo parti — anche **da
classi diverse**, perché `Groupe.Classe` è `0..N`.

Questo conferma [ADR-004](../decisioni.md) e lo precisa: il gruppo non è "un
pezzo di una classe", è un insieme di parti eventualmente trasversale a più
classi. Vedi [gruppi.md](gruppi.md).

⚠ Nota: `Classe.Mef` con cardinalità `0..N` non è ovvio — una classe con più
piani di studi. Da capire se è il caso delle classi articolate.

## Risorse

```
Salle
├── @Nom
├── @Capacite       (opzionale)
└── Site  (0..1)

Materiel
├── @Nom
├── @Informations
└── @NbOccurences   numero di esemplari disponibili
```

`Materiel.NbOccurences` è la **capacità simultanea di una risorsa**: quante
attività possono usarla nello stesso momento. È la risposta strutturale alla
domanda aperta "come si dichiara «max 2 laboratori in parallelo»" di
[vincoli.md](vincoli.md) — non come vincolo a sé, ma come attributo della
risorsa.

⚠ L'aula ha `Capacite` (posti a sedere) ma **non** un `NbOccurences`: un'aula è
implicitamente a occupazione 1. Per esprimere "due laboratori equivalenti"
serve un `Materiel`, non due `Salle`. Da confermare.

## Docente

```
Professeur
├── @Nom, @Prenom, @Abreviation
├── @Statut                        ← il campo "Statuto"
├── Civilite  (0..1)
├── Apport    (0..N)   "Liste des apports en minutes pour chaque discipline"
│   ├── @DureeMinutes
│   └── Discipline (0..1)
├── AHE       (0..N)   @Ident + @DureeMinutes
└── Salle     (0..1)   "Salle de préférence"
```

Tre conferme:

- `Statut` esiste come campo di scambio — è il "Statuto" della scheda docente,
  candidato sorgente della cascata su `Mh/s` ([docenti.md](docenti.md)).
- `Apport` è **capacità quantificata per disciplina**, in minuti. Rafforza
  [ADR-006](../decisioni.md): la capacità non è solo "quali materie", è "quanti
  minuti per disciplina".
- `Salle de préférence` conferma la distinzione preferenza vs. assegnazione.

## Attività e allineamenti — il punto centrale

```
Alignement
├── @Ident
└── Matiere  (0..1)     "Matière du cours complexe à générer"

Cours
├── DureeMinutes        (1..1)  durata in minuti
├── DureeSequences      (1..1)  durata in numero di sequenze
├── Matiere             (1..1)
├── Professeur          (0..N)  ← più docenti = compresenza
├── Groupe              (0..N)
├── PartieDeClasse      (0..N)
├── Classe              (0..N)
├── Salle               (0..N)
├── Personnel           (0..N)
├── Site                (0..1)
├── Materiel            (0..N)
├── Alignement          (0..1)
├── Libelle             (0..1)
└── Ponderation         (0..1)
```

L'annotazione dello schema su `Alignement` è testuale e chiude una domanda
aperta:

> *«permet de définir des alignements pour générer des cours complexes : tous
> les cours ayant le même Ident d'alignement seront regroupés au sein d'un même
> cours complexe. Il convient donc de définir autant d'alignements que de cours
> complexes souhaités.»*

Cioè: **l'allineamento è il meccanismo che genera l'attività complessa.** Tante
attività condividono un `Ident` di allineamento → EDT le fonde in una sola
attività complessa. La catena *allineamento → attività complessa → gruppi*, che
la guida 📖 lasciava intuire, è qui dichiarata.

Altre due cose degne di nota:

- **La durata è doppia** (`DureeMinutes` *e* `DureeSequences`): entrambe
  obbligatorie. Conferma che il "blocco di ore consecutive" è la durata
  dell'attività ([attivita.md](attivita.md)), e che va espressa nelle due unità
  della griglia.
- **`Professeur` è `0..N`**: la compresenza è nel formato base, non
  un'estensione. E `0` è ammesso — un'attività senza docente è legale.

## Cosa NON c'è, e perché conta

| Assente | Conseguenza |
|---|---|
| Piazzamento (giorno/ora dell'attività) | Il formato è input del solver, non output |
| Vincoli e indisponibilità | Restano interni a EDT: vanno osservati in UI, non si ricavano da qui |
| Monte ore aggregato per docente | Deriva dai `Cours`, coerente con [ADR-007](../decisioni.md) |
| Aule con occupazione simultanea | Si esprime con `Materiel`, non con `Salle` ⚠ |

## Implicazioni per il nostro schema

1. **Adottare `Partenaire_Index` V4.6 come contratto di import.** È stabile,
   documentato e già parlato dall'ecosistema italiano dei gestionali.
2. **Griglia a due livelli** (sequenza/posizione) e ciclo parametrico, non
   settimana fissa.
3. **Tre monte ore per (piano, materia)**, non uno.
4. **Partizione come entità**: classe → partizione nominata → parti → gruppi
   eventualmente trasversali.
5. **Capacità simultanea sulla risorsa** (`NbOccurences`), non come vincolo
   separato.
6. `Apport` docente×disciplina in minuti come forma quantificata della capacità.
