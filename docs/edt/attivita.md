# Entità EDT — Attività (Preparazione delle attività)

## Cos'è

L'ambiente dove il **servizio previsionale** di una classe si concretizza in
**attività** — le lezioni che il solver dovrà piazzare sulla griglia — e dove a
ogni attività si assegna il **docente**. È la gerarchia finale:

```
piano di studi → servizio → sotto-servizio → attività (Nr × durata) → docente
```

## Struttura osservata (2026-07-09)

Pannello sinistro: le classi previsionali (raggruppate per "Bisogni del livello
N°"). Pannello destro, per la classe selezionata (`1A (SCI1/1) – Servizi
previsionali`): ogni servizio ha **sotto-servizi** (righe figlie in corsivo) con:

| Colonna | Semantica |
|---|---|
| MS, Alu., H/Al., Clas., Rid., Sdop, Coeff. | come nei servizi del piano ([piani-di-studi.md](piani-di-studi.md)) |
| Nr attività | **numero di attività** in cui il sotto-servizio è spezzato |
| *(durate)* | accanto al Nr: le **durate delle attività** (es. `1h`; Matematica 5h → `1h, 2h`) |
| Docenti | icona per **assegnare il docente** al sotto-servizio |

EDT ha **generato da sé i sotto-servizi** con uno spezzamento di default: ITA 4h →
4 attività da 1h; MAT 5h → mix `1h, 2h`. In basso: "Totale delle ore di attività"
(27h00 su 1A ✅) e i pulsanti **Crea/Cancella un sotto-servizio** e "Cancella i
sotto-servizi disattivati".

## Le quattro viste della scheda (osservate 2026-07-15)

La scheda "Preparazione delle attività" ha **quattro viste** (icone accanto al
titolo), che coprono l'intero percorso previsionale → attività:

1. **Servizi previsionali** — lo spezzamento in attività e la selezione dei
   docenti desiderati sul bisogno (la struttura descritta sopra).
2. **Allineamento dei servizi** 📖 — verifica e creazione degli allineamenti.
   Dalla guida: i servizi sono allineabili solo se hanno la **stessa
   suddivisione**; la colonna **`Nr. doc. suppl.`** aggiunge docenti "anonimi" al
   conteggio (docenti designati totali = colonna Docenti + Nr. doc. suppl.) —
   chiude il punto aperto su "Docenti supplementari". Per allineamenti di
   discipline diverse la guida consiglia di rinominare la materia generica (es.
   "seconda lingua"). *UI ancora da osservare.*
3. **Assegnazione dei docenti ai servizi** — matrice **materie × classi**: ogni
   cella elenca i docenti desiderati di quella materia per quella classe. È qui
   che si fissa la **ripartizione puntuale** (chi prende quale classe) e si
   lancia la creazione delle attività (vedi sotto).
4. **Ripartizione dei docenti per classe** — matrice **docenti × classi**, la
   dashboard di controllo della ripartizione: colonne `Cattedra` (= `Mh/s`),
   `Occ.`, `+/-`, poi una colonna per classe con le ore dei bisogni su cui il
   docente è desiderato. Celle **grigie** = classi fuori dai bisogni del docente
   (es. un docente desiderato solo sul bisogno del triennio ha il biennio in
   grigio). Qui `+/-` è mostrato col segno **negativo** (ore mancanti alla
   cattedra), inverso rispetto all'elenco Docenti.

### Colonne osservate nella vista 3

| Colonna | Semantica |
|---|---|
| Materie | una riga per materia (servizi aggregati su tutte le classi) |
| Previsionale | ore totali della materia su tutte le classi (es. ITA `40h00`) |
| Bisogni | **Σ (ore del bisogno × docenti desiderati)** — verificato su tutte le righe: FIL `6h00` = 3h×2, FIS `16h00` = 2h×2 + 3h×4, MAT `26h00` = 5h×2 + 4h×4. È l'aggregato per materia della regola di `Occ. prev.`. Formula **confermata dal tooltip** della cella (osservato 2026-07-15): `1A : 16h00 (4 docenti x 4h00)`. In **rosso** quando eccede il Previsionale (docenti desiderati in surplus). |
| *(una colonna per classe)* | i docenti desiderati della materia su quella classe |

### Allineamento vs. assegnazione per classe (osservato 2026-07-15)

Finché i servizi di più classi sono **allineati**, i docenti desiderati si
modificano solo **sul gruppo intero**: per assegnare classe per classe bisogna
prima usare **"Cancella gli allineamenti"** sui servizi selezionati. Effetto:

- il bisogno condiviso si **spezza in un bisogno per classe**; nella cella di
  ogni classe restano il **titolare nominato** più i **docenti supplementari**
  (icona 👤 con il numero, es. `Rossi A., 3👤` = 1 nominato + 3 supplementari).
  I supplementari **contano nei Bisogni come i nominati**: ITA passa da 1
  bisogno × 4h × 4 docenti = `16h00` a 10 bisogni × 4h × 4 = `160h00` in rosso.
  (Semantica di "docenti supplementari" così **confermata in UI**, non più solo
  📖: segnaposto anonimi sommati al conteggio dei docenti.);
- la riga torna a posto **azzerando il contatore "Docenti supplementari"** nel
  dialogo di selezione (lasciando il solo titolare): quando ogni cella ha un
  docente, `Bisogni = Previsionale` e il rosso sparisce;
- con i bisogni per-classe, `Occ. prev.` diventa il **carico reale** del docente
  → la quadratura `+/- = 0` sull'elenco Docenti è finalmente verificabile
  (chiude la riserva della sezione su `Occ. prev.` più sopra). **Verificato sul
  dataset Fermi (2026-07-15)**: completata la ripartizione puntuale (compresi i
  servizi a docente unico, il cui allineamento residuo teneva `Occ.` al valore
  "una volta sola"), tutti i 18 docenti quadrano a `+/- = 0h00` e ogni riga
  della vista 3 legge `Bisogni = Previsionale`.

In basso, due file di pulsanti: **"Agisci sui servizi selezionati"** (Cancella
gli allineamenti / Assegna i docenti / Togli i docenti) e **"Agisci sui servizi
visualizzati"** (Cancella gli allineamenti / Togli i docenti dai servizi /
**Crea le attività**).

## Dalla previsione alle attività 📖 (guida, procedura da confermare in UI)

La guida ufficiale (schede *Creare automaticamente le attività*, 99-6917 e
99-393) descrive il flusso finale:

1. **Spezzamento**: doppio clic sulla colonna `Nr attività` → finestra con
   numero, durata e frequenza dei **blocchi**; il totale è verde se quadra col
   piano di studi, rosso altrimenti; tasto **Trasforma** per applicare.
2. **Ripartizione puntuale** (vista 3): selezionare i servizi → clic destro →
   *"Vedi l'assegnazione dei docenti"* (o tasto *Assegna i docenti*), doppio
   clic nella colonna Docenti e spunta del docente per classe. La ripartizione
   **automatica** dei docenti è dichiarata **"solo versione francese"**: in
   Italia si fa a mano.
3. **Crea le attività** (vista 3, "Agisci sui servizi visualizzati"): con
   *Tutti i livelli* selezionato in alto a destra crea tutte le attività in una
   volta; conferma con *Sì*. Si può creare anche dalla vista Allineamenti,
   lasciando docenti non designati da assegnare poi a mano in Orario.
4. Dopo la creazione EDT **reindirizza all'ambiente Orario** e la guida è
   esplicita: *"non utilizzate ulteriormente l'ambiente Preparazione fino al
   prossimo anno"* — ogni modifica successiva si fa in Orario (dove si
   inseriscono anche i vincoli di materie, docenti e classi).

### Il dialogo di conferma di "Crea le attività" (osservato 2026-07-15)

Testo letterale: *"ATTENZIONE. Tutte le classi che corrispondono alla vostra
selezione, i dati che le riguardano e le loro attività saranno cancellate. Le
classi saranno create a partire dalle classi previsionali e le attività saranno
create a partire dagli allineamenti definiti nell'ambiente Preparazione."* Con
checkbox *"Mantieni i vincoli e le indisponibilità delle classi e delle
materie"* (spuntata di default).

Tre conferme UI:

- la creazione è **rigenerativa, non incrementale**: classi reali e attività
  vengono cancellate e ricreate dal previsionale — è il motivo concreto del
  "non usare più Preparazione" della guida (un rilancio spazza le modifiche
  fatte in Orario);
- le attività nascono **dagli allineamenti**: un servizio ancora allineato fra
  classi genera lezioni legate — per le materie senza compresenze gli
  allineamenti vanno cancellati *prima* di creare;
- vincoli e indisponibilità di **classi e materie** sopravvivono alla
  rigenerazione solo con la spunta; i **docenti** non sono menzionati (non
  vengono rigenerati, i loro vincoli restano).

Questo risolve il punto aperto principale: la cattedra puntuale per classe si
fissa nella vista **Assegnazione dei docenti ai servizi**, ed è lì che la
quadratura `+/- → 0` diventa verificabile.

## Il dialogo "Selezione dei docenti"

L'icona Docenti apre **"Selezione dei docenti"** (osservato 2026-07-09):

- Filtri: **"Docenti della disciplina del servizio"**, **"Docenti della materia
  del servizio"**, **"Docenti in sotto-servizio"**, più un contatore **"Docenti
  supplementari"**.
- Elenco docenti con colonne **Monte ore, Occ., Residue, Extra max.** — la
  dashboard di carico *dentro* il dialogo di assegnazione, aggiornata live man
  mano che si assegna (sono i campi calcolati di [docenti.md](docenti.md),
  [ADR-007](../decisioni.md)).
- Si selezionano **più docenti** (spunta) sullo stesso bisogno.

Tre conferme:

1. Il filtro "della materia" usa le **materie insegnabili**: la capacità filtra
   l'assegnazione — [ADR-006](../decisioni.md) osservato dal vivo.
2. L'assegnazione previsionale è sul **bisogno (materia × durata)**, condiviso da
   tutte le classi con lo stesso servizio, **non sulla singola classe** (MAT/FIS
   biennio vs. triennio sono bisogni separati). I "docenti desiderati" dei tooltip
   previsionali sono questo.
3. `Occ.`/`Residue` si muovono a ogni assegnazione → i previsionali sono derivati
   in tempo reale.

**Da osservare:** con più docenti sullo stesso bisogno, come si controlla *chi
prende quale classe* (o quante ore ciascuno)? In previsionale sembra restare
indeterminato — la cattedra puntuale per classe va fissata altrove.

### Come conteggia `Occ. prev.` (osservato 2026-07-09, confermato 2026-07-15)

Dopo la selezione dei docenti desiderati su tutti i bisogni, la scheda Docenti
mostra che **`Occ. prev.` somma le ore del bisogno una volta sola per docente**,
senza moltiplicarle per le classi né dividerle fra i docenti spuntati: Barbieri
(unico su DIS, 10 classi) ha `2h00`, non 20h; i quattro di Lettere hanno tutti
`7h00` (ITA 4h + LAT 3h) sia chi avrà 3 classi sia chi ne avrà 2; Costa
`14h00` = 5+4+2+3 (i quattro bisogni MAT/FIS). Conseguenza: in previsionale
`+/-` **non arriva a 0** — misura l'impegno *per tipo di bisogno*, non il carico
reale. La quadratura `+/- → 0` si potrà verificare solo alla ripartizione
puntuale per classe.

**Conferma sperimentale (2026-07-15).** Reinserito l'intero dataset Fermi su una
base EDT vuota, i 18 valori di `Occ. prev.` coincidono tutti con quelli predetti
dalla regola (Conti/Marino `8h00` = 3+2+3, Ricci `5h00` = 2+3, Esposito `3h00`,
`HS prev.` a zero ovunque). Sulla base precedente gli stessi quattro docenti
mostravano `21h00`/`23h00`: valori spuri da **stato corrotto del file**, non una
regola diversa — plausibilmente il residuo dell'inversione STO/SCI nei servizi
del triennio (vedi
[`data/liceo-fermi/vincoli-attesi.md`](../../data/liceo-fermi/vincoli-attesi.md)),
corretta senza rifare l'allineamento. Lezione operativa: i previsionali derivano
dallo **stato corrente** di allineamenti e selezioni; dopo una correzione al
quadro orario va usato "Cancella l'allineamento" e rifatta la catena, altrimenti
`Occ. prev.` può gonfiarsi in modo non ricostruibile.

## L'attività in Orario (osservato 2026-07-15)

Dopo "Crea le attività" EDT reindirizza a **Orario > Attività > Elenco delle
attività** (confermato il redirect 📖→UI). Sul dataset Fermi: **284 attività per
288h00** (contatore in basso: `284 / 284 (288h00 / 288h00)`), tutte da piazzare.
284 = 288 − 4: quattro attività da `2h00` (i blocchi `1h, 2h` di MAT biennio,
4 classi), il resto da `1h00`. DIS in una classe = 2 righe da 1h: **una riga per
attività**, non per servizio.

Colonne osservate (valori sul dataset appena creato; semantiche non ovvie
marcate come ipotesi ⚠):

| Colonna | Valore osservato | Note |
|---|---|---|
| Durata | `1h00` (4 × `2h00`) | la durata-blocco decisa nello spezzamento |
| Giorno e ora | `Non piazzata` | il piazzamento non è ancora avvenuto |
| Freq. | `S` | ⚠ settimanale |
| Stato | icona ⊗ | ⚠ stato di piazzamento (non piazzata) |
| S.P. | `50` | ⚠ priorità/sequenza di piazzamento, default a metà scala |
| Nr G. | `5` | ⚠ giorni utili (lun–ven) |
| Sezion. | vuoto | ⚠ sezionamento (legami con altre attività) |
| Docente / Materia / Classe | dal previsionale | corretti su tutte le righe visibili |
| Modalità di scelta | `Senza specifica` | ⚠ criterio di scelta dell'aula |
| Alu. / Nr A. | `26` / `0` | effettivo classe / ⚠ alunni dissociati |
| Aula | vuota | l'assegnazione aule è un passo successivo |
| Periodicità | `S (33/33)` | ⚠ settimanale su 33/33 settimane dell'anno |
| Compr. | vuoto | compresenza (cfr. [gruppi.md](gruppi.md)) |
| Coeff. | `60/60` | il coefficiente visto sui servizi, cascata fino all'attività |
| Alu. Var. / Tipologia / Personale | vuoti | raggruppamenti ad alunni variabili, etichette, personale |

Conferma del modello: l'attività concreta è `(classe, materia, durata, docente,
[aula])` con attributi di piazzamento (priorità, periodicità, stato) — l'unità
esatta su cui lavorerà il nostro solver.

### Il pannello di composizione (osservato 2026-07-26)

Selezionando un'attività si apre un riquadro fluttuante che ne mostra **le
risorse impegnate**, una riga per tipo, con il conteggio a destra. Su un'attività
della base di esempio:

```
1h00 - lunedì alle 13h00 - S
1 spazio possibile - 17 alunni - alu.ins: 17

Materie           1    LETTER - LETTERE
Docenti           1    ALIGHIERI Dante
Personale         0
Raggruppamenti    0
Classi            1    2 A/R
Gruppi            0
Alunni dissociati 0
Aule              0
Materiali         0
```

È l'elemento `Cours` dello schema di scambio visto dal vivo, e si clicca su ogni
riga per assegnare quella risorsa (la riga `Aule` apre `Aule disponibili`, vedi
[aule.md](aule.md)).

Due cose da qui:

- **`Raggruppamenti` e `Gruppi` sono righe distinte.** Conferma in UI che i due
  livelli sono separati e non sinonimi ([gruppi.md](gruppi.md)).
- **`1 spazio possibile`** nell'intestazione: EDT espone all'utente il numero di
  collocazioni ammesse dall'attività — cioè il dominio residuo della variabile.
  Un dato del solver mostrato come informazione.

### Azioni sull'attività (menu contestuale)

`Modifica` · `Duplica` · `Dividi` · `Cancella` · `Sospendi` · `Metti in attesa` ·
`Blocca non sospendibili` / `Sblocca non sospendibili` · `Blocca senza spostare` /
`Sblocca` · **`Rendi fissa` (F)** / **`Rendi variabile` (V)** · `Dettaglia` ·
`Allinea` · `Ripristina gli orari per settimana` · `Trasforma in priorità di
sostituzione` · `Assegna un nome al raggruppamento` · `Differenzia il
raggruppamento per alunni variabili` · `Estrai`.

La colonna `P.P.` dell'elenco porta il badge `F`/`V`: è lo stato **fissa /
variabile**, cioè se il piazzamento dell'attività può essere spostato dal motore.
Sono quattro livelli distinti di immobilità (fissa, bloccata-senza-spostare,
non-sospendibile, sospesa) — più granulari del semplice booleano "pinned" che
avremmo modellato.

⚠ `Allinea` risulta disattivato con una sola attività selezionata: coerente col
fatto che l'allineamento è una relazione fra attività.

## L'attività nello schema di scambio 📦

Lo schema ufficiale ([schema-scambio.md](schema-scambio.md)) dichiara `Cours`
così:

```
Cours
├── DureeMinutes     (1..1)   durata in minuti
├── DureeSequences   (1..1)   durata in numero di sequenze
├── Matiere          (1..1)   ← l'unico riferimento obbligatorio
├── Professeur       (0..N)
├── Groupe           (0..N)
├── PartieDeClasse   (0..N)
├── Classe           (0..N)
├── Salle            (0..N)
├── Personnel        (0..N)
├── Materiel         (0..N)
├── Site             (0..1)
├── Alignement       (0..1)
├── Libelle          (0..1)
└── Ponderation      (0..1)
```

Cinque cose che l'osservazione in UI non poteva dare:

1. **La durata è doppia e obbligatoria**: minuti *e* numero di sequenze. La
   colonna `Durata` (`1h00`, `2h00`) ne è la resa compatta. Un'attività va quindi
   sempre espressa nelle due unità della griglia.
2. **La sola cosa obbligatoria è la materia.** Docente, classe e aula sono tutti
   `0..N`: un'attività senza docente è legale nel formato. Utile a capire che
   "docente supplementare/da definire" non è un caso speciale ma il caso normale
   con cardinalità zero.
3. **`Professeur` è `0..N`** → la compresenza è nel formato base. È la colonna
   `Compr.` osservata vuota qui sopra.
4. **`Alignement` è il legame fra attività**: attività con lo stesso allineamento
   diventano una sola attività complessa.
5. **`Ponderation`** è la colonna `Coeff.` — confermato 📦: `Coeff.` traduce il
   francese `Pondération`, che è esattamente questo elemento. Scende in cascata
   dai servizi fino all'attività.

### La colonna `Sezion.` — sciolta 📦

`Sezion.` è il **sezionamento dell'attività complessa**: come si distribuiscono
docenti e raggruppamenti fra le lezioni che la compongono. Codici a 1–2 lettere
mostrati in UI (famiglia `FicCoursComplexe_RS_*`, testo letterale):

| Codice | Significato |
|---|---|
| `S` | `Una lezione per docente` |
| `SQ` | `Una lezione per docente ogni 15 giorni` |
| `SC` | `Una lezione per docente per ogni ciclo` |
| `SP` | `Una lezione per docente, gli alunni dipendono dal periodo` |
| `A` | `I docenti cambiano raggruppamento a metà dell'attività` |
| `AQ` | `…e si alternano ogni 15 giorni` |
| `AC` | `…e si alternano ad ogni ciclo` |

I codici `A*` sono il caso dell'**alternanza**: due docenti che si scambiano i
raggruppamenti a metà anno o a quindicine alterne — tipico di laboratori e
compresenze. Il nostro modello deve poterlo esprimere, o dichiararlo fuori scope
esplicitamente.

### Lo spezzamento è padre/figlio 📦

L'enumerazione interna `TypeParenteCours` ha tre valori — `CoursSimple`,
`CoursPere`, `CoursFils` — e `TNetRelationCours` è un'**auto-relazione**. Lo
spezzamento di un servizio in blocchi non produce quindi righe indipendenti: le
attività figlie restano legate all'attività padre sulla **stessa entità**, non in
una tabella separata. Da replicare nel nostro schema con una FK ricorsiva.

Nota: lo schema **non trasporta il piazzamento** (nessun giorno, nessuna ora).
Conferma che l'attività è l'input del solver e che giorno/ora sono output.

## Semantica dedotta

- L'**attività** è l'unità di piazzamento del solver: (classe, materia, durata,
  docente). Lo spezzamento in attività è dove nascono i **blocchi di ore
  consecutive**: un'attività da `2h` è un blocco indivisibile — la risposta alla
  domanda aperta sui blocchi passa da qui, non da un vincolo separato.
- I **sotto-servizi** permettono di dividere un servizio (es. quota classe intera
  vs. quota sdoppiata, o docenti diversi sulla stessa materia).

## Implicazioni per il nostro modello

- Serve l'entità **attività/lezione**: `activity(class/group, subject, duration,
  teacher)`; il monte ore del servizio è un vincolo di copertura (`Σ durate
  attività = ore del servizio`).
- La **durata dell'attività** (1h, 2h…) è il modo naturale di esprimere i blocchi
  consecutivi: modellare la durata sull'attività, non come vincolo esterno.
- L'assegnazione docente sta sull'attività/sotto-servizio → è qui che `Occ. prev.`
  e `+/-` del docente si muovono ([docenti.md](docenti.md), ADR-007).

## Aperto / da osservare

- ~~Con più docenti su un bisogno, dove si fissa **chi prende quale classe**~~ →
  risolto: vista **Assegnazione dei docenti ai servizi** (osservata; meccanica
  del dialogo di assegnazione ancora da osservare).
- ~~Semantica di **"Docenti supplementari"**~~ → risolto e **confermato in UI**
  (icona 👤 nelle celle della vista 3: segnaposto anonimi che contano nei
  Bisogni come i nominati); resta il filtro "Docenti in sotto-servizio".
- ~~Come si controlla lo spezzamento~~ → risolto 📖: doppio clic su `Nr
  attività` → finestra blocchi + Trasforma (finestra da osservare in UI).
- Vista **Allineamento dei servizi** (2ª icona): mai osservata in UI.
- Differenza esatta fra **sotto-servizio** e attività; quando servono più
  sotto-servizi (sdoppiamenti? → [gruppi.md](gruppi.md)).
