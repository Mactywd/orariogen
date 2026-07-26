# Entità EDT — Aule

## Cos'è

Gli spazi fisici in cui si svolgono i corsi: aule ordinarie, laboratori, palestra,
aula magna.

## ⚠ Stato della fonte

> **Le aule non sono mai state inserite nella base del Fermi.** L'header
> `CARTEIDENTITE` di `example_2.edt` dichiara `NBSALLES = 0` (verificato
> 2026-07-26). Quindi
> [`data/liceo-fermi/aule.md`](../../data/liceo-fermi/aule.md) resta **progetto,
> non osservazione**, e va creato in EDT prima di poter provare qualunque cosa
> *sul nostro dataset*.
>
> **Il meccanismo però è ormai osservato in UI**, sulla base di esempio fornita
> con il prodotto (18 aule, 3 sedi, gruppi, tipologie): tutto ciò che segue senza
> marcatore è visto a schermo il 2026-07-26.

## La vista Aule, com'è

Orario > **Aule**, `Elenco delle aule`. Colonne osservate:

| Colonna | Cosa contiene |
|---|---|
| `Nome` | |
| `Sedi` | la sede di appartenenza (`Principale`, `Succ. 1`, `Succ. 2`) |
| `Cap.` | capienza — **vuota su tutte e 18** nella base di esempio |
| **`Qtà`** | **numero di attività simultanee ammesse** — vedi sotto |
| `Occ.` | ore occupate (calcolato) |
| `TOP` | tasso di occupazione % (calcolato) |
| `Gestori` | responsabile dell'aula |
| `Categoria` | categoria dei locali scolastici |
| `Assegnate` / `Picco d'occ.` | calcolati, valorizzati solo per `Qtà > 1` |

## 🔑 L'occupazione simultanea è un campo dell'aula

> ⚠ **Correzione.** Una versione precedente di questo file affermava che
> l'occupazione simultanea si modella creando un **gruppo di N aule**. È
> **sbagliato**: l'ipotesi veniva dalle stringhe di localizzazione, e
> l'osservazione in UI l'ha smentita.

Il menu contestuale dell'aula espone **`Modifica → Numero di aule`**: è una
proprietà scalare, modificabile direttamente, che si legge nella colonna `Qtà`.

La prova decisiva: nella base di esempio l'aula `PALESTRE succ` ha `Qtà = 2` **e
nessuna sotto-aula**. Se `Qtà` fosse il conteggio dei figli, quel record sarebbe
incoerente.

> **«La palestra regge 2 classi in parallelo» si dichiara con `Numero di aule =
> 2`.** Non servono due aule fittizie raggruppate.

Nella finestra `Aule disponibili` la stessa quantità compare come **frazione**
(`1 / 2`): occupazione corrente su capienza simultanea, calcolata sullo slot.

### Le sotto-aule sono un meccanismo separato

Esiste *anche* una gerarchia padre/figlio, ma serve ad altro: dare **identità e
nome ai singoli spazi**. Nella base, `PALESTRE` (`Qtà = 2`) contiene `Palestra 1`
e `Palestra 2`, mostrate in corsivo e nascoste finché non si espande il nodo.

Sui figli si osserva una **cascata di default**: il campo `Gestori` riporta
`Tosco Luisa (Gr.)` — il suffisso `(Gr.)` significa *ereditato dal gruppo* — e
`Sedi` è vuoto, quindi anch'esso ereditato. È lo stesso meccanismo di
[`Al./Rid.`](materie.md), su un'altra entità: conferma che la cascata è un
pattern trasversale del prodotto, non un caso isolato ([ADR-003](../decisioni.md)).

L'occupazione è contabilizzata **sul padre** (`48h00 / 48%`), non sui figli
(`0h00` entrambi).

Nota: `Modifica → Categoria dei locali scolastici` è **disabilitata** su un
contenitore. La categoria è un attributo delle aule foglia.

## Le tipologie — dotazioni, non tipi d'aula

`Modifica → Tipologie → Tipologie predefinite` apre un albero **a due livelli**,
interamente definito dall'utente:

```
Attrezzature            ← categoria
├── PC docente
└── Videoproiettore
```

con caselle a scelta multipla: un'aula può portare più tipologie. `Nuova
tipologia` permette di aggiungerne, e la voce di raggruppamento nella finestra di
scelta aula si chiama `Attrezzature (Tipologie)` — cioè **prende il nome dalla
categoria**, quindi più categorie darebbero più voci.

⚠ **Non è il "tipo d'aula"** (laboratorio / palestra / aula magna) che questo
documento ipotizzava. È un sistema di **etichette di dotazione**.

Sovrapposizione da notare: `Videoproiettore` esiste **sia** come tipologia **sia**
come `Materiale` (3 esemplari). Come tipologia è una dotazione fissa dell'aula;
come materiale è una risorsa prenotabile e assegnabile a un'attività. EDT offre
entrambi i modelli per lo stesso oggetto fisico, e lascia scegliere.

## 🔑 Cosa vincola davvero la scelta dell'aula

La finestra `Aule disponibili` (dal pannello di composizione dell'attività, riga
`Aule`) espone la lista dei **vincoli ignorabili** — e sono tre soli:

| Vincolo | Marcatore in colonna `Diagnostica` |
|---|---|
| `Sedi distaccate` | rosa |
| `Indisponibilità opzionali` | giallo |
| `Indisponibilità` | arancione |

La colonna **`Diagnostica`** dice, aula per aula, *perché* non va bene. Nella
schermata osservata la `S` rosa compare su tutte e 18 (l'attività è in `Succ. 2`,
le aule quasi tutte in `Principale`) e il quadratino arancione su 7 aule occupate
in quello slot.

Ci sono poi due filtri booleani — `Solamente le estratte`, `Solo le aule della
stessa sede dell'attività` — e un raggruppamento `Presenta per:` con le voci
`Tutto` · `Categoria` · `Sede` · `Attrezzature (Tipologie)`.

**Conclusione importante, in negativo:** capienza, categoria e tipologia **non
sono vincoli**. Non compaiono fra i vincoli ignorabili e servono solo a
raggruppare la lista per chi sceglie a mano. L'unico vincolo reale sull'aula è la
sua **disponibilità**, più la sede se attiva.

### Ma la classe ha un'aula preferenziale

La vista Classi ha una colonna **`Aula preferenziale`**. Quindi il legame
aula↔didattica esiste, solo che passa dalla **classe**, non dalla materia — che è
poi come funziona una scuola reale: la classe ha la sua aula e si sposta solo per
laboratorio e palestra. Vedi [classi.md](classi.md).

Non esiste invece nulla di simile a *"questa materia richiede un laboratorio"*: se
lo vogliamo, è **nostra estensione**, da marcare come tale.

## Altri campi dell'aula

- `Prenotabile da` + `Soglia di prenotazione` (*"numero di giorni prima dei quali
  può essere fatta una prenotazione"*) — 📦, l'aula ha un **regime di
  prenotazione**.
- `Gestori` — *"personale o docente designato come responsabile dell'aula"*
  (osservato: valorizzato su tutte le 18 aule della base).
- `Sede di appartenenza` (= `Site` dello schema).
- `Categoria dei locali scolastici` (= tipo interno `TNetCategorieSalle`).
- `Tasso di occupazione`, `Numero di posti occupati` / `disponibili` — calcolati.

## Cosa dice lo schema di scambio 📦

Lo schema ufficiale ([schema-scambio.md](schema-scambio.md)) modella l'aula in
modo più povero di quanto ipotizzato qui:

```
Salle
├── @Nom
├── @Capacite     (opzionale)
└── Site  (0..1)
```

Nessun campo "tipo", **nessun vincolo di occupazione**. L'occupazione simultanea
esiste invece su un'altra entità:

```
Materiel
├── @Nom
├── @Informations
└── @NbOccurences    numero di esemplari disponibili
```

Nel formato di scambio l'aula è quindi implicitamente a occupazione 1.

⚠ **Lo schema qui inganna.** Il campo `Numero di aule` esiste nel prodotto ma non
viaggia nello scambio: chi importasse da `Partenaire_Index` perderebbe la
capienza simultanea di ogni aula. È un argomento concreto contro l'adozione dello
schema come contratto unico.

Sulle stringhe della localizzazione una nota metodologica: parlano di `Gruppo di
aule` e di `Nr` — *"Numero di aule (=1 per un'aula; > 1 per un gruppo)"* — e
questa formulazione mi aveva portato a concludere che l'occupazione simultanea
**fosse** il gruppo. La UI dice altro: `Qtà > 1` non implica alcun membro. Le
stringhe descrivono il caso tipico, non il modello. È esattamente il motivo per
cui [ADR-009](../decisioni.md) mette le stringhe estratte dai binari all'ultimo
posto della gerarchia di autorevolezza.

**Nota per il solver.** Non esiste un tipo `TNetContraintesSalle` fra le entità
persistenti 📦: le indisponibilità dell'aula non sono una tabella di vincoli
dedicata come per il docente. Stanno nella tabella generica delle **assenze
risorsa**, insieme a quelle di docenti e classi — vedi [vincoli.md](vincoli.md).

## ⚠ Limite: la tabella delle aule è cifrata

Nel file `.edt` la tabella `SALLE` è **cifrata**, insieme a sei tabelle di dati
personali (docenti, alunni, responsabili, personale, contatti, credenziali). Le
sei hanno una ragione ovvia; l'aula no, e non c'è una spiegazione. Vedi
[formato-file.md](formato-file.md).

**Conseguenza:** nomi, capienza, sito e categoria delle 18 aule della base di
esempio **non sono leggibili nel file**.

🔑 **Il limite è stato aggirato aprendo la base in EDT.** La cifratura protegge i
dati a riposo, non la vista: l'elenco delle 18 aule è perfettamente leggibile in
UI (`AULA SOSTEGNO`, `LAB.ARTISTICA`, `LAB.INFORMATICO`, `PALESTRE`, `SALA
MENSA`, …), con sede, quantità, gestore e categoria. Per questo documento il
limite non morde più; resta valido per chiunque volesse leggere le aule
programmaticamente dal `.edt`.

Si recupera comunque, in chiaro dalla stessa base:

- **`CATEGORIESALLE`** con due categorie reali: `AULA DI INSEGNAMENTO GENERALE` e
  `CDI` (biblioteca). La categorizzazione esiste e si popola.
- **`SITE`**: 3 siti, con colore.
- **`RELATIONSALLES`**: la relazione fra aule, cioè i gruppi.
- **`MATERIEL`**: `Videoproiettore ×3`, `PC portatile ×5`, `Tablet ×50`.

Quest'ultima chiarisce un punto: l'**attrezzatura prenotabile è una risorsa
distinta dall'aula**, non un modo alternativo di modellare l'aula. Il
`Materiel/@NbOccurences` dello schema serve a "ho 3 videoproiettori", non a "la
palestra regge 2 classi".

### Le aule ammettono davvero corsi simultanei — verificato

Espandendo la collocazione dei 984 corsi piazzati della base di esempio, le 9
aule effettivamente usate mostrano **34 collisioni su 97 slot**: più corsi nella
stessa aula nello stesso momento, in una base che EDT considera risolta senza
errori.

Non è un difetto della base: è la conferma che **l'occupazione simultanea è un
attributo reale dell'aula**, che EDT rispetta. E ora sappiamo qual è il campo:
`Numero di aule`, colonna `Qtà`.

⚠ Confronto utile: sui docenti le collisioni sono 7 su 1333, sulle classi 1 su
1320 — cioè quasi zero, come atteso. Le aule sono l'unica risorsa dove la
sovrapposizione è sistematica.

## Semantica

- La **capienza** (`Cap.`) è il tetto di alunni dello spazio. In EDT è
  **descrittiva**: non compare fra i vincoli di assegnazione, e nella base di
  esempio non è nemmeno compilata. Se noi volessimo confrontarla col massimo di
  alunni del corso ([`Al./Rid.`](materie.md)), sarebbe **nostra estensione**.
- Il **vincolo di occupazione** (`Numero di aule`) è distinto dalla capienza ed è
  quello vero: la palestra regge 2 attività in parallelo, i laboratori 1. È il
  vincolo di risorsa condivisa per il solver.
- L'idea che *"FIS/SCI vanno in laboratorio, MOT in palestra"* sia un legame
  **materia → tipo d'aula** non trova riscontro in EDT: il legame passa dalla
  classe (`Aula preferenziale`) o è deciso a mano sull'attività. Resta un'ipotesi
  di nostra progettazione, non un campo osservato.

## Risorsa contesa (nota per il solver)

La palestra regge 2 classi, ma il docente di MOT (D17) è **uno solo**: di fatto la
palestra è mono-classe finché c'è un solo docente. Idem per l'aula disegno con D16.
La capienza dell'aula non è il collo di bottiglia: lo è il docente. Vedi
[`data/liceo-fermi/vincoli-attesi.md`](../../data/liceo-fermi/vincoli-attesi.md).

## Implicazioni per il nostro modello

- L'aula ha `nome`, `sede`, `capienza` (descrittiva) e un intero
  **`simultaneous_capacity`** — l'unico attributo che il solver deve rispettare.
  Default 1.
- La **gerarchia padre/figlio** fra aule è un extra rimandabile: serve a nominare
  gli spazi, non a esprimere la capienza. Se la implementiamo, va con la
  **cascata di default** sui campi ereditabili (gestore, sede).
- Le **tipologie** sono tag a due livelli (categoria → tipologia), molti-a-molti
  con l'aula, definiti dall'utente. Puramente descrittivi in EDT.
- L'**aula preferenziale sta sulla classe**, non sulla materia.
- Una eventuale relazione **materia → dotazione richiesta** sarebbe **nostra
  estensione** oltre EDT. Da valutare, e comunque da marcare come tale
  ([convenzione "non inventare campi"](../../CLAUDE.md)).

## Dataset di esempio

Le aule del Liceo Fermi:
[`data/liceo-fermi/aule.md`](../../data/liceo-fermi/aule.md).
