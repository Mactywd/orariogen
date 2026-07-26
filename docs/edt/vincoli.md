# Entità EDT — Vincoli

> Indisponibilità e vincoli orari docente: semantica dalla guida **confermata in
> UI** (2026-07-15). Le famiglie di vincoli mancanti — **materie** e
> **attività↔attività** — sono state ricostruite il 2026-07-26 dalle tabelle di
> lingua del prodotto (📦, vedi [ADR-009](../decisioni.md)) e **osservate in UI lo
> stesso giorno** sulla base di esempio fornita con EDT, dove entrambe le griglie
> sono raggiungibili e una delle due è popolata con dati reali.

## Ambito

Come EDT permette di dichiarare i vincoli che il motore di generazione deve
rispettare. Distinto dai **conflitti attesi del dataset Fermi** (quelli sono il
banco di prova del solver e stanno in
[`data/liceo-fermi/vincoli-attesi.md`](../../data/liceo-fermi/vincoli-attesi.md)).

## Indisponibilità e preferenze docente (guida + UI osservata 2026-07-15)

Si inseriscono in **Orario > Docenti > Indisponibilità e vincoli**, "dipingendo"
la griglia oraria con tre pennelli (frequenza *Settimanale* oppure *Settimane
Q1/Q2* — radio osservati in UI). Griglia osservata: lun–ven × 08h–18h (= i 50
slot del tasso `TOP`, vedi [docenti.md](docenti.md)), con una linea magenta alle
12h (⚠ probabile confine mattino/pomeriggio o fascia mensa):

| Pennello | Nome | FR | Semantica per il piazzamento automatico |
|---|---|---|---|
| **Rosso** | Indisponibilità | `Indisponibilités` | **Mai violata.** Per i casi imperativi (giorno libero richiesto, servizio in altro istituto). |
| **Giallo** | Indisponibilità Opzionali | `Indisponibilités Optionnelles` | Rispettata come una rossa, ma l'utente può **autorizzare EDT a ignorarle** per risolvere le attività scartate. Attenzione: l'esclusione è **globale** (tutte le gialle di tutti i docenti insieme) → la guida avverte di **non** usare il giallo per impegni improrogabili (part-time, completamento di servizio altrove). |
| **Verde** | **Preferenze** | `Voeux` | Fascia in cui il docente *vorrebbe* lezione. EDT cerca di tenerne conto, **nessuna garanzia**. |

Il nome del terzo pennello — rimasto ⚠ finora — è **`Preferenze`**, dedotto 📦
dalla chiave `AffScoGrilleAnnuelM_RS_VoeuxLong` (IT `Preferenze`, FR `Voeux`,
EN `Wishes`) e poi **letto a schermo** (2026-07-26). I tre radio del pannello
`Indisponibilità e preferenze` sono, testuali:

> `Indisponibilità` · `Indisponibilità opzionali` · `Preferenze`

Osservato anche che la stessa griglia a tre pennelli si apre **sulla singola
attività** (Orario > Attività > *Visualizza le indisponibilità*), non solo sulle
risorse: conferma diretta in UI della genericità descritta qui sotto. La griglia
dell'attività va **lun–ven × 08h00–18h00**, senza sabato.

**Le indisponibilità opzionali non sono solo del docente.** Esistono, una stringa
di diagnostica per ciascuna, anche per **classi, aule, materiali, personale e
attività**:

> `La classe ha un'indisponibilità opzionale` · `L'aula ha un'indisponibilità
> opzionale` · `Il materiale ha un'indisponibilità opzionale` · `La risorsa del
> personale ha una indisponibilità opzionale` · `L'attività ha un'indisponibilità
> opzionale`

Il meccanismo rosso/giallo/verde è quindi **generico sulla risorsa**, non
specifico del docente — semplificazione importante per il nostro modello.

In più esistono i **vincoli orari** numerici, separati dalla griglia (la guida
li consiglia al posto di riempire la griglia di gialli). Catalogo osservato nel
pannello destro della stessa vista (2026-07-15; alcune etichette troncate a
destra dello schermo, ⚠ da completare):

**Etichette complete 📦** (le troncature sono risolte; fra parentesi il francese,
che è la lingua sorgente e disambigua):

| Badge | Vincolo | Parametri, testo letterale | Classe nel motore |
|---|---|---|---|
| **D** | Distribuzione oraria (`Répartition imposée`) | `Minimo` N `giorni a settimana con un minimo di` X `per giorno` | `TContrainteRepartitionDemiJournees` |
| **M** | Massimo di ore di attività (`Max horaire`) | `Giornata:` / `Mattino:` / `Pomeriggio:` | `TContrainteMaxHoraireRessource` |
| **P** | Massimo di ore di presenza (`Maximum présentiel`) | N `giorni alla settimana, presenza massima in istituto:` X — oppure `giorni per ciclo, lavorare al massimo` | `TContrainteMaxPresentielRessource` |
| **E** | Gestione Entrate / Uscite (`Horaires aménagés`) | N `giorni alla settimana` + `non iniziare prima delle` / `non finire oltre le` | `TContrainteJEG` |
| **G** | Giorni e ½ giornate libere (`Plages libres garanties`) | `Assegna...` N `giornate libere` + N `mezze giornate libere` | `TContraintePLG_DJT` |
| **⅁** | Massimo di mezze giornate di lavoro | `Mattino:` / `Pomeriggio:` + casella `Lavorare solo mezza giornata al giorno` | |
| **S** | **Numero massimo di cambi di sede** | `per giorno` / `per settimana`, a `Valori predefiniti` | |
| — | Preferenze di ottimizzazione | `Numero di ore di buco tollerate`, default `2` | |

**Pannello osservato per intero il 2026-07-26** (`AMLETO Amleto - Indisponibilità
e vincoli`, base di esempio): sono **sette gruppi di vincoli più le preferenze di
ottimizzazione**, e l'elenco qui sopra è completo — non c'è nient'altro. I valori
non impostati si mostrano come `Niente` o `0`, coerentemente con la cascata di
default ([ADR-003](../decisioni.md)).

Gli ultimi due gruppi, prima privi di badge, ce l'hanno: `Massimo di mezze
giornate di lavoro` e `Numero massimo di cambi di sede`. E i primi due — che
esistono anche sulla classe — sono le colonne `MMG` e `MG` della vista Classi
([classi.md](classi.md)).

Due precisazioni che il francese chiarisce e l'italiano no:

- **`D` è un minimo imposto, non un massimo**: `Travailler N jours par semaine
  avec un minimum de X par jour`. È il vincolo "lavora almeno N giorni, e in
  quei giorni almeno X ore" — serve a evitare che il solver concentri tutto.
- **`G` sono garanzie, non desiderata** (`Plages libres *garanties*`): a
  differenza del pennello verde, qui EDT si impegna.

Il **cambio di sede** con tetto giornaliero/settimanale/di ciclo era del tutto
ignoto: rilevante per scuole su più plessi.

Nota per il modello: **presenza ≠ attività** (la presenza include i buchi) — EDT
le vincola separatamente.

### `D.T.B.` = Durata Tollerata dei Buchi — risolto 📦

La colonna `D.T.B.` dell'elenco docenti (`2h00`) è **`Durata tollerata dei
buchi`** (FR `Nombre d'Heures de Trous Tolérées`). L'ipotesi che venisse dalle
preferenze di ottimizzazione è confermata: stessa quantità, due punti di accesso.

Il buco è insieme **soglia** e **termine di ottimizzazione**:

- soglia per risorsa (`D.T.B.`), superabile solo attivando `Autorizza il
  superamento del massimo di buchi tollerati`;
- obiettivo di ottimizzazione: `Riduci i buchi (docenti)` e `Riduci i buchi
  (classi)` sono due leve **distinte**.

E la linea magenta a metà griglia è confermata come **linea di fine mattinata**:
la preferenza si chiama `Non conteggiare come buchi le ore libere prima o dopo la
linea di fine mattinata` (FR `autour de la mi-journée`). Serve esattamente a non
contare la pausa pranzo come buco. Altre opzioni: `Lascia i buchi di 1/2 ora`,
`Non considerare i cambi di sede come dei buchi`.

**Implicazione per il dataset Fermi:** gli spezzoni D06, D09, D15 (completamento
su altra scuola) vanno espressi col **rosso**, non col giallo.

**Implicazione per il nostro modello:** tre livelli di durezza (hard /
soft-trattata-come-hard-salvo-override-globale / desiderata) più vincoli di
conteggio (cardinalità per settimana), non solo maschere sulla griglia.

## 🔑 Indisponibilità e assenze sono la stessa tabella 📦

Nella base di esempio ci sono **227 record `ABSENCERESSOURCE`** (record fissi da
47 byte: intervallo di collocazione, ident risorsa, genere, data `TDateTime`).
La ripartizione è istruttiva:

| | Conteggio |
|---|---|
| Su docenti | 198 |
| Su classi | 29 |
| **Senza data** → indisponibilità **ricorrenti** | **28** |
| **Con data** → assenze **effettive** | **199** |

Cioè EDT **non ha due concetti separati**: l'indisponibilità ricorrente ("il
martedì pomeriggio non c'è") e l'assenza puntuale ("il 12 marzo è a un corso di
aggiornamento") sono righe della stessa tabella, distinte dalla presenza della
data. Gli intervalli datati sono allineati a multipli di 10 e ampi 10 — cioè
**giornate intere** nella codifica `place = giorno × 10 + rango`
([formato-file.md](formato-file.md)).

**Implicazione per il nostro modello.** Una sola entità
`resource_unavailability(resource, slot_range, date?)`, dove `date` nullo
significa "ogni settimana". Coerente col fatto che il meccanismo
rosso/giallo/verde è generico sulla risorsa: una tabella, tre livelli di durezza,
data opzionale.

Questo tocca direttamente il SaaS sostituzioni, che gestisce assenze: **è la
stessa entità** che serve al generatore per le indisponibilità. Vale la pena
progettarla una volta sola.

## Vincoli di materia (classe × materia) — osservati in UI

**Dove.** Orario > **Classi** > icona *Visualizza i vincoli delle materie*. Il
pannello resta vuoto finché non si seleziona una classe (*"Selezionate una classe
per vedere i vincoli"*): i vincoli sono **per classe**, coerentemente col tipo
interno `TNetContrainteMatiereClassep`. Titolo del pannello: `2 A/R - Vincoli
delle materie`. In alto una casella `Visualizza solo le materie seguite dalla
selezione`.

### La griglia com'è davvero

È una **matrice `Materie A` × `Materie B`** — una riga per coppia di materie — con
le colonne raggruppate. Ogni gruppo porta una lettera-badge:

| Gruppo (badge) | Sotto-colonne |
|---|---|
| `Incompatibilità` **I** | `1/2g` · `1g` · `2g` · `N. 1/2g` |
| `Seq. Ind.` **S** | — |
| `Max ore` **M** | `1/2g` · `1g` |
| `Ordine Sett.` **O** | — |
| `Attività in gruppo` **G** | — |
| `Conc. Imp.` **C** | — |

Ogni intestazione ha un'**icona a matita**: la cella non è un semplice flag, si
apre e si compila. Infatti nei dati convivono croci (✗) e **valori** (`2h00`).

### 🔑 Cosa fa ogni colonna — dall'aiuto contestuale del prodotto

Il pulsante `?` del pannello apre la scheda **`What constraints should be
used?`**, che elenca sette casi d'uso concreti e li mappa alle colonne. È la
fonte migliore disponibile su questa griglia, perché è il prodotto che spiega sé
stesso. (⚠ Nota: **l'aiuto è in inglese anche nell'installazione italiana** — non
è una fonte affidabile per la terminologia IT.)

| Caso d'uso (testo dell'aiuto) | Colonna |
|---|---|
| *"LATIN and GREEK should not be held in the same day"* → `incompatibility in the same day` | `Incompatibilità 1g` |
| *"MATHEMATICS and SCIENCES should be separated by a certain number of half-days"* → `incompatibility in number of half-days` | `Incompatibilità N. 1/2g` |
| *"No PHYSICAL EDUCATION before MATHEMATICS"* → `succession prohibited` **arranged in the order** Phys Ed - Math | `Seq. Ind.` |
| *"No more than 2 hours of language in the same day"* → `hourly maximum` for 2 hours | `Max ore 1g` |
| *"BIOLOGY must be held before TECHNOLOGY during the week"* → `the weekly order` | `Ordine Sett.` |
| *"The courses **in a group** for BIOLOGY should not be held **after** the courses **in a full class**"* → specify `"After"` for the `course in a group` | **`Attività in gruppo`** |
| *"Two SCIENCES courses must be held on two consecutive days"* → specify the **maximum delay** for the `imposed sequencing` | **`Conc. Imp.`** |

Le due colonne che erano oscure sono quindi risolte:

**`Attività in gruppo`** è **esattamente** l'ordine fra ore in gruppo e ore a
classe intera, cioè i quattro valori `Parties…Classe` dell'enumerazione interna.
Prende valori del tipo `Prima` / `Dopo` — coerente con `PartiesAvantClasse` /
`PartiesApresClasse` e le due varianti `AvantOuApres`. Non è più inferenza.

**`Conc. Imp.`** = **Concatenazione imposta**, e il parametro è un **ritardo
massimo** fra due attività della stessa materia. Combacia con la stringa già
documentata (*"determina l'intervallo temporale massimo tra due attività della
stessa materia"*).

### Perché dieci colonne e dodici tipi

La discrepanza si spiega: **tre tipi condividono `Conc. Imp.` e due condividono
`Ordine Sett.`**, perché la differenza fra loro è il **valore del parametro**,
non un vincolo diverso.

- `Concatenazione imposta`, `Successione imposta ½ g.` e `Successione imposta
  J+1` sono la stessa colonna con ritardo massimo diverso — l'aiuto lo dice
  esplicitamente parlando di *"maximum delay for the imposed sequencing"*.
- `Ordine settimanale` e `Ordine nel ciclo` differiscono per l'orizzonte
  (settimana o ciclo), che è un parametro globale della griglia oraria.

Fanno 9 colonne per i 12 tipi, più `Attività in gruppo` che nell'elenco delle
stringhe non compariva: **10**. Torna.

⚠ Resta inferenza il *quale* tipo mappi su quale valore di parametro: l'aiuto dà
i casi d'uso, non la tabella di corrispondenza.

### I dati reali della base di esempio

Sulla classe `2 A/R`, 19 righe già impostate. Sono istruttive perché mostrano
**come una scuola vera usa questa griglia**:

| Coppia | Colonna marcata | Lettura |
|---|---|---|
| quasi ogni materia con sé stessa (`ARTE`/`ARTE`, `STORIA`/`STORIA`, …) | `Incompatibilità 1g` ✗ | non due ore della stessa materia nello stesso giorno |
| `FRANCESE`/`FRANCESE`, `MUSICA`/`MUSICA` | `Incompatibilità 2g` ✗ | vincolo più largo: tenute a distanza su due giorni |
| `FRANCESE`→`INGLESE` **e** `INGLESE`→`FRANCESE` | `Seq. Ind.` ✗ | le due lingue non si susseguono |
| `LETTERE`/`LETTERE` | `Max ore 1g` = **`2h00`** | tetto, non divieto |

Due cose che i dati insegnano e le stringhe non dicevano:

1. **Il caso dominante è la materia con sé stessa.** La griglia non serve
   soprattutto a mettere in relazione materie diverse: serve a **distribuire nel
   tempo le ore della stessa materia**. Nel nostro modello questo è il vincolo
   più importante da supportare, non un caso limite.
2. **I vincoli direzionali occupano due righe.** `FRANCESE`→`INGLESE` e
   `INGLESE`→`FRANCESE` sono record distinti: la relazione è **orientata**, e
   la simmetria si ottiene inserendola due volte.

### I dodici tipi dalle stringhe 📦

Descrizione letterale che EDT mostra all'utente:

| Vincolo | Descrizione (testo di EDT) |
|---|---|
| Incompatibilità ½ giornata | *"perché due attività delle materie selezionate non siano piazzate nella stessa mezza giornata"* |
| Incompatibilità giornata | idem, stessa giornata |
| Incompatibilità 2 giorni | *"…non siano piazzate in due giorni consecutivi"* |
| **Scarto in ½ giornate** | *"Numero minimo di 1/2 giornate: per inserire un certo numero di mezze giornate tra due attività delle materie selezionate"* |
| Max ore ½ giornata | *"perché il numero di ore di attività di questa materia nella mezza giornata non superi mai il valore indicato"* |
| Max ore giornata | idem, giornata |
| Sequenza vietata | *"perché un'attività della materia B non si svolga subito dopo un'attività della materia A"* |
| **Concatenazione imposta** | *"determina l'intervallo temporale massimo tra due attività della stessa materia"* |
| Ordine settimanale | *"perché un'attività della materia A si svolga sempre prima di un'attività della materia B"* |
| Ordine nel ciclo | idem, sul ciclo |
| Successione imposta ½ g. | *"un'attività della materia B deve svolgersi nella mezza giornata che segue un'attività della materia A"* |
| Successione imposta J+1 | idem, giornata successiva |

L'enumerazione interna corrispondente è `TypeIncompatibiliteMatiereClasse`, con
13 valori: `MemeDemiJournee, MemeJournee, DeuxJours, SuccessionInterdite,
MaxHDemiJournee, MaxHJournee, OrdreHebdo, SuccessionImposee, EcartDj,
PartiesAvantClasse, PartiesApresClasse, PartiesAvantOuApresClasseH,
PartiesAvantOuApresClasseAB`.

Gli ultimi quattro valori non hanno etichetta fra quelle sopra e riguardano
l'**ordine fra ore in gruppo e ore a classe intera** (`Parties…Classe`): sono la
colonna **`Attività in gruppo`**, confermata dall'aiuto contestuale — *"The
courses in a group for BIOLOGY should not be held after the courses in a full
class"*. Il vincolo si esprime scegliendo `Prima`/`Dopo` per le ore in gruppo
rispetto a quelle a classe intera.

**Perché ci riguarda:** è un vincolo che esiste **solo se supportiamo gli
sdoppiamenti**. Entra quindi nella decisione di scope aperta in
[gruppi.md](gruppi.md), non è un dettaglio a sé.

Esiste anche un **peso didattico**: *"Peso didattico massimo per settimana per un
alunno"* (`Poids pédagogique maximum par semaine pour un élève`) — un vincolo di
carico cognitivo per classe, mai emerso finora.

## Vincoli fra attività (`TNetContrainteCoursACours`) — osservati in UI

**Dove.** Orario > **Attività** > icona *Vincoli tra attività*. La griglia ha le
colonne `Ordine` · `Materia` · `Doc.` · `Personale` · `Classe`, ed è **vuota**
nella base di esempio. Il pulsante `Aggiungi un vincolo` è disabilitato finché
non si selezionano almeno due attività:

> *"Per creare un vincolo, selezionate almeno due attività e cliccate su
> «Aggiungi un vincolo»"*

La presenza della colonna **`Ordine`** dice già che questi vincoli hanno un
verso.

### Gli undici tipi, dal menu reale

Selezionate due attività, `Aggiungi un vincolo` apre un menu a tre blocchi.
**Undici voci esatte**, che coincidono con la ricostruzione dalle stringhe:

| | stessa settimana | stessa ½ giornata | stessa giornata | numero definito di ½ giornate |
|---|---|---|---|---|
| **Imporre la collocazione** | ✔ | ✔ | ✔ | ✔ |
| **Impedire la collocazione** | ✔ | ✔ | ✔ | ✔ |

più tre voci di ordinamento, fuori dalla matrice:

- `Definire l'ordine delle attività selezionate`
- `Imporre la sequenza delle attività selezionate`
- `Impedire la sequenza delle attività selezionate`

Osservazioni:

- **`ordine` e `sequenza` sono nozioni distinte** — tre voci separate non
  servirebbero altrimenti. ⚠ Presumibilmente *ordine* = A prima di B non
  necessariamente adiacenti, *sequenza* = consecutive. Da confermare.
- **`nella stessa settimana` risulta disattivato** quando le due attività hanno
  la stessa periodicità (nella base: `42`, cioè tutto l'anno). Conferma indiretta
  che quel vincolo lavora sulla **maschera delle settimane**
  ([formato-file.md](formato-file.md)), non sulla griglia oraria.
- La granularità è di nuovo la **mezza giornata**, in positivo e in negativo.

### 🔑 L'opzionalità, testo letterale

L'unica delle undici che prende un parametro (`in un numero definito di mezze
giornate`) apre una finestra `Aggiungi un vincolo` con:

- `Numero di mezze giornate :` — menu a tendina;
- `Personalizza il nome del vincolo (facoltativo)` — campo libero: **il vincolo
  ha un nome dato dall'utente**;
- una casella, **spuntata di default**:

> ✔ **`Vincolo opzionale (può essere alleggerito durante il piazzamento delle
> attività scartate)`**

Tre cose in una riga:

1. **I vincoli fra attività nascono opzionali.** Chi ne vuole uno inviolabile
   deve togliere la spunta. È l'opposto del default che avremmo scelto noi.
2. **"Alleggerito"** è l'`allègement` del motore
   ([motore-risoluzione.md](motore-risoluzione.md)) visto dal lato utente.
3. **"durante il piazzamento delle attività scartate"** conferma in UI la
   strategia a due passate dedotta dalla pipeline: prima passata con tutto hard,
   poi una seconda sulle attività rimaste fuori in cui i vincoli opzionali
   vengono allentati.

### Limiti dichiarati dal prodotto 📦

- *"Impossibile vincolare più di due attività ad essere piazzate su settimane
  alterne."*
- *"Non possono esserci più di due attività consecutive."*
- *"Le attività coinvolte nei vincoli tra attività non possono essere allineate."*
  — **vincolo fra attività e allineamento si escludono a vicenda.**

Mappa dei tipi interni ai vincoli (⚠ inferenza semantica, i nomi di tipo non
compaiono nel dizionario delle stringhe):

| Tipo interno | Vincolo |
|---|---|
| `TNetInfosContrainteEcart` | scarto/distanza in mezze giornate (materie *e* attività) |
| `TNetInfosContrainteQuinzaine` | stessa/diversa quindicina (settimane alterne Q1/Q2) |
| `TNetInfosContrainteSuccession` | sequenza imposta/vietata |
| `TNetContrainteCoursACours` | il contenitore |

⚠ Attenzione al termine `Écart`: qui è "scarto temporale", ma altrove nel
prodotto significa "differenza numerica" (es. `Dotazione − Bisogni`). È
sovraccarico.

## Blocchi di ore consecutive — risolto

Non sono un vincolo separato: sono la **durata dell'attività**, fissata nello
spezzamento del servizio (doppio clic su `Nr attività` → numero/durata/frequenza
dei blocchi → Trasforma). Pista confermata dalla guida 📖 — la finestra parla
esplicitamente di "numero di blocchi". Vedi [attivita.md](attivita.md).

## Cosa dicono (e non dicono) gli artefatti 📦

Lo schema di scambio ufficiale `Partenaire_Index` V4.6
([schema-scambio.md](schema-scambio.md)) **non contiene vincoli**: zero
occorrenze di `Contrainte`, `Indisponibilite`, `Absence`. Trasporta solo
anagrafica, struttura e attività da piazzare.

Questo è esso stesso un risultato: **i vincoli non si possono ricavare dal
formato di scambio**, restano interni a EDT. La lista qui sotto va chiusa
osservando la UI (o, dove possibile, minando le basi dati binarie) — non c'è una
scorciatoia documentale.

Sulla **capacità simultanea di una risorsa** lo schema è invece fuorviante, e
l'osservazione in UI lo ha smentito: nel formato di scambio l'unico contatore è
`Materiel/@NbOccurences` e l'aula (`Salle`) ha solo `@Capacite`, cioè posti a
sedere. Nella UI l'aula **ha eccome un contatore di occupazione**
(`Modifica → Numero di aule`, colonna `Qtà`): è un campo interno che il formato
di scambio semplicemente non trasporta. Vedi [aule.md](aule.md).

I vincoli che governano l'**assegnazione di un'aula** a un'attività sono stati
osservati direttamente nella finestra `Aule disponibili`, sotto la voce
`Ignora i vincoli`, e sono **tre**:

| Vincolo | Marcatore nella colonna `Diagnostica` |
|---|---|
| `Sedi distaccate` | rosa |
| `Indisponibilità opzionali` | giallo |
| `Indisponibilità` | arancione |

Notevole per assenza: **né capienza, né categoria, né tipologia** sono vincoli di
assegnazione. Sono attributi descrittivi e assi di raggruppamento della lista, non
regole che il motore rispetta. L'unico vincolo reale sull'aula è la sua
**disponibilità**, più la sede se attiva.

⚠ Con una riserva: quella è la lista dei vincoli **ignorabili**. L'occupazione
(`Numero di aule`) non vi compare, ma verosimilmente perché non è negoziabile —
non perché non esista.

I binari contengono i nomi dei tipi interni dei vincoli — `TNetContraintesClasse`,
`TNetContraintesProfesseur`, `TNetContrainteMatiereClassep`,
`TNetContrainteCoursACours`, `TNetInfosContrainteEcart`,
`TNetInfosContrainteQuinzaine`, `TNetInfosContrainteSuccession` — che confermano
**quali famiglie di vincoli esistono** ma non cosa contengono (fonte 📦 di livello
basso, vedi [ADR-009](../decisioni.md)). Notevole: esiste
`TNetContrainteCoursACours`, cioè un vincolo **da attività ad attività**, che non
compare da nessuna parte nella nostra documentazione osservata.

## Da osservare

Questa lista è il **cancello del solver**: finché non è chiusa, il prototipo resta
fermo (vedi [ADR-008](../decisioni.md)). Non vogliamo scoprire un tipo di vincolo
nuovo a modello già scritto.

**Aggiornamento 2026-07-26**: la lista si è accorciata molto. Chiuso per via
documentale (📦):

- [x] ~~Etichette troncate dei vincoli orari~~ → complete, con testo letterale.
- [x] ~~Nome del terzo pennello~~ → **`Preferenze`** (FR `Voeux`).
- [x] ~~Vincolo attività↔attività~~ → 11 tipi, parametri e limiti documentati.
- [x] ~~Vincoli di materia~~ → 12 vincoli + enum a 13 valori.
- [x] ~~Indisponibilità di classi e aule~~ → il meccanismo rosso/giallo/verde è
      **generico sulla risorsa** (docenti, classi, aule, materiali, personale,
      attività), non specifico del docente.

Chiuso **osservando la UI** sulla base di esempio (sessione del 2026-07-26):

- [x] ~~Confermare in UI le due griglie ricostruite~~ → entrambe viste.
      `Vincoli delle materie delle classi` è **popolata con 19 righe reali**;
      `Vincoli tra attività` è vuota ma il suo menu espone **esattamente gli
      undici tipi** previsti.
- [x] ~~Nome del terzo pennello~~ → letto a schermo: `Preferenze`.
- [x] ~~Vincoli di risorsa / occupazione simultanea~~ → **non** è il gruppo di
      aule: è il campo `Numero di aule` sull'aula stessa. Vedi
      [aule.md](aule.md) — la versione precedente di questa riga era sbagliata.
- [x] ~~Opzionalità dei vincoli fra attività~~ → casella esplicita, **spuntata di
      default**, con la semantica scritta in chiaro nella finestra.

Resta aperto:

- [ ] **`Attività in gruppo`** e **`Conc. Imp.`**: due colonne della griglia dei
      vincoli di materia di cui non conosco la semantica. La prima è il candidato
      per i quattro valori `Parties…Classe` (ordine fra ore in gruppo e ore a
      classe intera), ma non è verificato. Basta il tooltip delle due
      intestazioni.
- [ ] **Dieci colonne contro dodici tipi**: la griglia espone dieci gruppi di
      colonne, l'elenco dalle stringhe dà dodici vincoli. Discrepanza da
      spiegare.
- [ ] La distinzione fra **`ordine`** e **`sequenza`** nei vincoli fra attività:
      tre voci distinte nel menu, semantica presunta ma non verificata.
- [ ] **Le aule non esistono nella base del Fermi** (`NBSALLES = 0`): vanno
      create prima di poter osservare i vincoli di aula *sul nostro dataset*. Il
      meccanismo però è ormai noto dalla base di esempio.
- [ ] `TContrainteItalieProfReglementaire`: **unica classe di vincolo
      paese-specifica italiana** nel motore, senza etichetta UI trovata. Potrebbe
      codificare un limite normativo che ci riguarda direttamente. Da indagare.

## Implicazioni per il nostro modello

Il quadro è ora abbastanza completo da progettare il modello dei vincoli.

**1. Il vincolo è generico sulla risorsa.** Docente, classe, aula, materiale,
personale e attività condividono lo stesso meccanismo di disponibilità
(rosso/giallo/verde). Nel nostro schema: un'unica entità
`resource_availability(resource_type, resource_id, slot, level)` con tre livelli
di durezza, non una tabella per tipo di risorsa.

**2. Tre livelli di durezza, più l'opzionalità per singolo vincolo.**

| Livello | Semantica |
|---|---|
| Hard | mai violato |
| Hard-con-override-globale | il "giallo": violabile solo attivando l'esclusione, che è **globale**, non selettiva |
| Soft | il "verde": desiderata, nessuna garanzia |

E i vincoli attività↔attività hanno un flag di opzionalità proprio, **attivo di
default**: l'opzionalità è un attributo del singolo vincolo, non solo un livello
della griglia. Insieme alla frase *"durante il piazzamento delle attività
scartate"* questo definisce la forma della risoluzione: **due passate**, la
seconda con l'insieme dei vincoli opzionali allentato.

**3. Quattro assi indipendenti di vincolo**, che il nostro modello deve tenere
separati perché EDT li tiene separati:

| Asse | Oggetto | Esempio |
|---|---|---|
| Disponibilità | risorsa × slot | il docente non c'è il lunedì |
| Cardinalità | risorsa × periodo | max 6 ore al giorno, min 4 giorni a settimana |
| Relazione | materia ↔ materia, attività ↔ attività | MAT e FIS non nella stessa mezza giornata |
| Capacità | risorsa condivisa | l'aula accetta `Numero di aule` attività in parallelo |

**Il caso d'uso dominante dell'asse Relazione è la materia con sé stessa.** Nei
dati reali della base di esempio, 15 righe su 19 sono `X`/`X`: il vincolo serve
soprattutto a **distribuire nel tempo le ore di una stessa materia**. Se il
nostro solver ne supportasse uno solo, sarebbe questo.

E la relazione è **orientata**: `A → B` e `B → A` sono due record distinti.

**4. Presenza ≠ attività.** La presenza include i buchi. Servono due contatori
distinti per docente, non uno.

**5. Il buco è insieme vincolo e obiettivo.** Soglia per risorsa (`D.T.B.`) *e*
termine di ottimizzazione, con leve separate per docenti e per classi. Il nostro
solver deve poter esprimere entrambi, e deve sapere che la pausa pranzo non conta
come buco (linea di fine mattinata).

**6. La granularità dei vincoli è la mezza giornata**, non l'ora. Quasi tutti i
vincoli di relazione (incompatibilità, scarto, successione) si esprimono in
giornate o mezze giornate. Il nostro modello deve avere la mezza giornata come
concetto di prima classe, derivato dalla linea di fine mattinata.
