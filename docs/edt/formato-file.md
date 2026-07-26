# EDT — Il formato del file `.edt`

> Fonte 📦: reverse engineering di `Esempio.edt` (base completa e risolta fornita
> con l'installazione) e di `example_2.edt` (la base del Fermi). Le decodifiche
> sono **verificate incrociando i conteggi dell'header con i dati**; quello che
> resta inferenza è marcato ⚠.

## A cosa serve saperlo

**Non** per leggere o scrivere file `.edt` — sarebbe fragile e fuori scope. Serve
per **validare la semantica sui dati reali**: una base risolta contiene le
risposte che né la UI né la guida danno, e permette di verificare le ipotesi
invece di crederle.

Concretamente è così che si è stabilito che IRC e attività alternativa sono
*parti della stessa classe* e non gruppi ([gruppi.md](gruppi.md)), e che le aule
ammettono davvero corsi simultanei ([aule.md](aule.md)).

## Contenitore

Binario Delphi, **non compresso e non cifrato** nel complesso (entropia ~4.7
bit/byte).

```
0x000   intestazione binaria + GUID della base
0x4B0   <CARTEIDENTITE> …XML in chiaro…      ← metriche della base
        magic di sezione  AB CD EF FF
        744 tabelle, in sequenza
```

**L'header `CARTEIDENTITE` è XML in chiaro** e dichiara le metriche: numero di
materie, docenti, classi, parti, gruppi, aule, corsi piazzati e non, MEF, servizi
previsionali. È il modo più rapido per sapere cosa contiene una base senza
aprirla in EDT — ed è quello che ha rivelato `NBSALLES = 0` sulla base del Fermi.

### Le tabelle sono auto-descrittive

Ogni tabella si presenta così:

```
"DATA" | NOMETABELLA | TNetXxx | paylen | maxIdent | nRecord
        └─ poi i record, ciascuno marcato  "ArTi"
```

Cioè il file **porta con sé i nomi delle tabelle e delle classi Delphi**. Le
stringhe sono `uint32 len` + testo ANSI.

**Le due basi hanno le stesse 744 tabelle nello stesso ordine**: lo schema è
fisso, non dipende dai dati.

⚠ **I nomi dei campi non sono nel file.** Gli attributi sono posizionali: si
identificano per offset, tipo e riscontro sui valori. Le enumerazioni
`TypeColonne*` estratte dall'eseguibile danno i nomi *come li vede la UI*, che è
probabilmente un superinsieme ordinato diversamente — **non assumere
corrispondenza 1:1**.

## Le sette tabelle cifrate

Sette tabelle hanno il payload cifrato (lunghezze multiple di 16, nessun blocco
ripetuto):

`PROFESSEUR` · `ELEVE` · `RESPONSABLE` · `PERSONNEL` · `COORDONNEES` ·
`AUTHENTIFIANT` · **`SALLE`**

Sei sono dati personali, il che spiega la cifratura. **`SALLE` è l'anomalia** e
non c'è una spiegazione: nomi, capienza, sito e categoria delle aule restano
illeggibili. È il limite principale di questa analisi.

Si recupera comunque, in chiaro:

| Tabella | Contenuto osservato in `Esempio.edt` |
|---|---|
| `CATEGORIESALLE` | 2 categorie: `AULA DI INSEGNAMENTO GENERALE`, `CDI`/Biblioteca |
| `SITE` | 3 siti, con colore |
| `RELATIONSALLES` | relazione fra aule (i "gruppi di aule") |
| `MATERIEL` | Videoproiettore ×3, PC portatile ×5, Tablet ×50 |

`MATERIEL` conferma che l'**attrezzatura prenotabile è distinta dall'aula**: sono
due risorse diverse, non due modi di dire la stessa cosa.

## Il record `COURS` — 107 byte

Struttura a corpo fisso. Offset relativi all'inizio del corpo (dopo `ArTi` e
l'ident):

| Offset | Tipo | Contenuto |
|---|---|---|
| 10–15 | 48 bit | **maschera delle settimane** (effettiva) |
| 18–25 | 64 bit | maschera delle settimane (dominio pieno) |
| 42–45 | uint32 | place |
| **46–49** | uint32 | **durata in sequenze** |
| 60–63 | uint32 | ⚠ non identificato |
| **67–70** | uint32 | **ident materia** |
| **103–106** | uint32 | **place effettiva** — `0xFFFFFFFF` = non piazzata |

Istogramma delle durate: `1×885, 2×293, 3×41, 4×1, 8×4`. Il corso da 8 sequenze è
`ATTIVITÀ DI SEGRETERIA` con due unità di personale — non una lezione.

### La collocazione: `place = giorno × 10 + rango`

Dieci sequenze al giorno (da `SEQUENCEHORAIRE`), orari in `LIBELLEHORAIRE` come
`TDateTime`. Nella base di esempio convivono **due griglie**: una oraria 08–18 e
una da 50 minuti 09–19.

Osservazioni sui valori:

- il **giorno 5 (sabato) è inutilizzato**;
- il **rango 6** (`place % 10 == 6`, ore 14:00) è quasi sempre vuoto → è la pausa
  pranzo.

**Validazione end-to-end.** I due campi `place` (42 e 103) coincidono in
**esattamente 984** record, che è il `NBCOURSPLACES` dichiarato nell'header. La
decodifica è quindi confermata dai dati, non solo plausibile.

### La maschera delle settimane

Il valore dominante ha accesi i bit `1–17, 19–30, 32–44`: **44 settimane, con la
18 e la 31 spente** — ⚠ verosimilmente le vacanze di Natale e Pasqua.

La stessa maschera compare **per singola relazione** in
`RELATIONCOURSRESSOURCE`: una risorsa può partecipare a un corso **solo in certe
settimane**. È un livello di granularità che né la UI né lo schema di scambio
lasciavano sospettare, e ha una conseguenza diretta sul nostro modello: la
partecipazione risorsa↔attività non è booleana, è **temporale**.

## L'enum dei generi di risorsa

Ricavato per cardinalità, incrociando i conteggi con l'header:

| Valore | Risorsa | Riscontro |
|---|---|---|
| 0 | docente | 76 = `NBPROFS` |
| 1 | raggruppamento | ident `{20,21,24}` = quelli di `GROUPE` |
| 2 | classe | 40 = `NBCLASSES` |
| 3 | parte di classe | |
| 4 | aula | |
| 7 | personale ATA | |
| 10 | materiale | |

⚠ Discrepanza non risolta: il docente è genere `0` in `RELATIONCOURSRESSOURCE` ma
`3` in `ABSENCERESSOURCE`. I due enum non coincidono.

Riscontro semantico che convalida la mappa: tutte le SCIENZE MOTORIE cadono
nell'aula 27 — la palestra.

## Cosa *non* c'è nel file

`TNetContraintesClasse`, `TNetContrainteCoursACours`, `TNetInfosContrainteEcart`,
`…Quinzaine`, `…Succession` **non esistono come tabelle né come stringhe** in
nessuna delle due basi.

Conferma quanto emerso dall'eseguibile: quelle classi di vincolo sono **modello a
runtime**, costruito in memoria, non dati persistiti. Chi volesse ricavare i
vincoli dal file `.edt` non li troverebbe. Vedi
[motore-risoluzione.md](motore-risoluzione.md).

## Limiti dichiarati

- **`SALLE` cifrata**: nessun dato di aula leggibile.
- 240 record `COURS` in eccesso rispetto a `NBCOURS = 984` ⚠ non spiegati
  (plausibilmente corsi cancellati o modelli, non verificato).
- Il campo a offset 60 di `COURS` resta ignoto.
- Il `uint32` in coda alle parti anonime resta ignoto (⚠ ipotesi: rimando alla
  tabella iscrizioni).
