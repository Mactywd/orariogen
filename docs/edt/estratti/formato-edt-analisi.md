# Reverse engineering del formato `.edt` (EDT 2026, Index Education)

Base analizzata: `~/.wine/drive_c/Program Files/Index Education/EDT 2026/Monoposto/Esempio.edt`
(1 969 100 byte, md5 `b156b202753e35ae0421e3d3ef6f4e54`).
Base di confronto: `~/Desktop/EDT/example_2.edt` (310 416 byte, md5 `550bbf23bc5f2103e814713d677432ba`).

Entrambi i file sono stati **copiati** in scratchpad e analizzati in sola lettura.
Nessun file sotto `~/.wine` o `~/Desktop/EDT` è stato modificato.

Convenzione di questo documento:
**[F]** = fatto osservato (byte/stringa citabili) · **[I]** = inferenza · **[?]** = non determinato.

---

## 0. Sintesi

| Priorità richiesta | Esito |
|---|---|
| 1. Aule (attributi) | **Parzialmente fallito**: la tabella `SALLE` è **cifrata**. Recuperati categoria, siti, materiali, id aule usate dai corsi, e il vincolo "più corsi simultanei per aula". |
| 2. Parti di classe | **Riuscito**: struttura record decodificata, FK verso `CLASSE` confermata su nomi reali. |
| 3. Gruppi | **Riuscito**: 3 gruppi, nomi e struttura letti. |
| 4. Vincoli / indisponibilità | **In gran parte riuscito**: 227 record decodificati, genere risorsa e intervallo temporale identificati. |
| 5. Griglia oraria e collocazione | **Riuscito e validato**: `place`, `durata`, `materia` decodificati; verifica di non-collisione al 99,5%. |

---

## 1. Formato contenitore

### 1.1 Header e carta d'identità

Il file inizia con un blocco binario, poi un header XML **in chiaro** a offset `0x4B0`:

```
00000480:  ab cd ef ff 0d 05 00 00  <?xml version="1.0" encoding="UTF-8"?><CARTEIDENTITE>...
```

**[F]** `0x4B0` (dec 1200) — `<CARTEIDENTITE>`; contenuto letterale rilevante:

```
<VERSION>Millesime2018</VERSION>
<DATECONSTRUCTION>2011-07-12T09:24:03.446+02:00</DATECONSTRUCTION>
<DATEECRITURE>2026-06-16T10:12:08.894+02:00</DATEECRITURE>
<NOMBASEORIGINAL>Esempio</NOMBASEORIGINAL>
<NBMATIERES>20</NBMATIERES><NBPROFS>76</NBPROFS><NBCLASSES>40</NBCLASSES>
<NBPARTIES>187</NBPARTIES><NBGROUPES>3</NBGROUPES><NBSALLES>18</NBSALLES>
<NBSITES>3</NBSITES><NBELEVES>744</NBELEVES><NBCOURS>984</NBCOURS>
<NBCOURSPLACES>984</NBCOURSPLACES><NBCOURSNONPLACES>0</NBCOURSNONPLACES>
<NBABSENCESRESSOURCES>227</NBABSENCESRESSOURCES><NBMEFS>4</NBMEFS>
<NBSERVICEPREVISIONNELS>467</NBSERVICEPREVISIONNELS><NBAMENAGEMENTS>141</NBAMENAGEMENTS>
```

**[F]** La stringa XML è preceduta da `AB CD EF FF` + `uint32 lunghezza` (`0d 05 00 00` = 1293 = lunghezza esatta dell'XML).

### 1.2 Magic di sezione: `AB CD EF FF`

**[F]** `AB CD EF FF` marca l'inizio dei blocchi di testata (parametri globali). Esempi letterali:

```
000009a0:  ab cd ef ff 03 00 00 00 04 00 00 00 4e 54 46 53   ....NTFS
000009b8:  04 00 00 00 50 52 4f 54 ff ff ff 7f ff ff ff 7f   PROT
000009f0:  ab cd ef ff 00 05 00 00 00 30 30 30 30 31         "00001"
00000a10:  ab cd ef ff 03 00 00 00 47 52 4c                  "GRL"
```

**[F]** Le stringhe sono **Delphi longstring**: `uint32 lunghezza` + byte ANSI (Latin-1). Nessuna terminazione a zero.

### 1.3 Corpo: 744 tabelle auto-descrittive

**[F]** Il corpo è una sequenza di sezioni con questa intestazione:

```
"DATA" (longstring)  |  NOMETABELLA (longstring)  |  TNetXxx (longstring)  |  uint32 paylen | uint32 maxIdent | uint32 nRecord
```

Esempio letterale a `0x000a6d5a`:

```
000a6d5a:  04 00 00 00 44 41 54 41 07 00 00 00 4d 41 54 49   ....DATA....MATI
000a6d6a:  45 52 45 0b 00 00 00 54 4e 65 74 4d 61 74 69 65   ERE....TNetMatie
000a6d7a:  72 65 a8 05 00 00 30 00 00 00 15 00 00 00 41 72   re....0.......Ar
000a6d8a:  54 69 ...                                          Ti
```

→ tabella `MATIERE`, classe Delphi `TNetMatiere`, payload `0x5a8`=1448 byte, maxIdent `0x30`=48, **21** record.

**[F]** Entrambe le basi contengono **esattamente le stesse 744 tabelle, nello stesso ordine**: lo schema è fisso, indipendente dal contenuto.

### 1.4 Magic di record: `ArTi`

**[F]** Ogni record inizia con i 4 byte ASCII `ArTi` (`41 72 54 69`), seguiti da un `uint32`.

Due framing distinti:

* **Tabelle in chiaro** — `ArTi | uint32 ident | corpo a lunghezza fissa` (la lunghezza si ricava dalla distanza dal `ArTi` successivo; è costante per tabella).
* **Tabelle cifrate** — `ArTi | uint32 lunghezzaPayload | payload`. **[F]** Verificato: in `SALLE`, `PROFESSEUR`, `ELEVE`, `RESPONSABLE`, `PERSONNEL`, `COORDONNEES`, `AUTHENTIFIANT` il `uint32` è **sempre uguale** alla lunghezza del payload, mai un ident crescente.

### 1.5 Entropia

**[F]** `Esempio.edt`: entropia globale 6,23 bit/byte; blocchi a 7,98 bit/byte in `0x00000–0x70000` (tabella `AUTHENTIFIANT`) e `0x110000–0x140000` (dentro `ELEVE`).
`example_2.edt`: 4,735 bit/byte globale (nessuna tabella persona popolata a parte `PROFESSEUR`).

**[I]** La descrizione "non cifrato" vale per lo **scheletro** e per le tabelle dell'orario; **non** per le tabelle di dati personali.

---

## 2. Le tabelle cifrate (blocco sui dati personali — e sulle aule)

**[F]** Delle 744 tabelle, **7** hanno record il cui `uint32` post-`ArTi` non è un ident crescente:

| Tabella | Classe | n record | lunghezze payload |
|---|---|---|---|
| `AUTHENTIFIANT` | `TNetAuthentifiant` | 1792 | 272, 288, … |
| `COORDONNEES` | `TNetCoordonnees` | 623 | 176, 208, … |
| `PERSONNEL` | `TNetPersonnel` | 12 | 112 |
| **`SALLE`** | **`TNetSalle`** | **19** | **48, 64** |
| `PROFESSEUR` | `TNetProfesseur` | 78 | 272, 288, 304 |
| `ELEVE` | `TNetEleve` | 744 | 368 |
| `RESPONSABLE` | `TNetResponsable` | 62 | 128 |

**[F]** Tutte le lunghezze payload sono **multipli di 16**. Nei 68 blocchi da 16 byte di `SALLE` non c'è **alcuna ripetizione**.
**[F]** In `example_2.edt` solo `AUTHENTIFIANT` e `PROFESSEUR` sono in questo stato; i nomi dei docenti del Fermi (Conti, Marino, Ricci, Esposito) **non** compaiono in chiaro da nessuna parte del file.

**[I]** Cifratura a blocchi da 16 byte (AES o simile), applicata per record. Le 6 tabelle di persone sono coerenti con una protezione dei dati personali; **`SALLE` è l'anomalia** e non ho una spiegazione.

**Conseguenza diretta sulla richiesta n. 1: nomi, capienza e attributi delle 18 aule non sono estraibili da questo file.**
Quello che si recupera sulle aule è indiretto ed è nella sezione 3.

Dump letterale dell'inizio di `SALLE` (`0x000a6858`), a riprova:

```
000a6858:  04 00 00 00 44 41 54 41 05 00 00 00 53 41 4c 4c   ....DATA....SALL
000a6868:  45 09 00 00 00 54 4e 65 74 53 61 6c 6c 65 e0 04   E....TNetSalle..
000a6878:  00 00 38 00 00 00 13 00 00 00 41 72 54 69 30 00   ..8.......ArTi0.
000a6888:  00 00 74 f9 65 97 bf 69 fe 0c 24 68 67 f6 53 47   ..t.e..i..$hg.SG
```

→ paylen `0x4e0`, **maxIdent 56**, **19 record**; primo record: `ArTi` + lunghezza `0x30`=48 + 48 byte ad alta entropia.
(19 record vs `NBSALLES=18`: **[F]** tutte le tabelle hanno un record "riservato" con ident 1 — es. `MATIERE` 21 record per 20 materie, `GROUPE` 4 record per 3 gruppi.)

---

## 3. Aule: quello che si ricava comunque

### 3.1 `CATEGORIESALLE` / `TNetCategorieSalle` — in chiaro

**[F]** Offset `0x00076406`, 2 record:

```
00076436:  7f 00 00 00 02 00 00 00 02 00 00 00 41 72 54 69   ............ArTi
00076446:  01 00 00 00 03 02 00 00 00 30 33 1d 00 00 00 41   .........03....A
00076456:  55 4c 41 20 44 49 20 49 4e 53 45 47 4e 41 4d 45   ULA DI INSEGNAME
00076466:  4e 54 4f 20 47 45 4e 45 52 41 4c 45 1d 00 00 00   NTO GENERALE....
00076476:  41 75 6c 61 20 64 69 20 69 6e 73 65 67 6e 61 6d   Aula di insegnam
00076486:  65 6e 74 6f 20 67 65 6e 65 72 61 6c 65 01 41 72   ento generale.Ar
00076496:  54 69 02 00 00 00 1a 02 00 00 00 32 36 03 00 00   Ti.........26...
000764a6:  00 43 44 49 0a 00 00 00 42 69 62 6c 69 6f 74 65   .CDI....Bibliote
000764b6:  63 61 01                                          ca.
```

**[F]** Layout: `ArTi | ident | byte | codice(str) | libellé maiuscolo(str) | libellé(str) | byte`.

| ident | byte | codice | etichetta MAIUSC. | etichetta |
|---|---|---|---|---|
| 1 | `0x03` | `03` | `AULA DI INSEGNAMENTO GENERALE` | `Aula di insegnamento generale` |
| 2 | `0x1a` (26) | `26` | *(assente)* | `CDI` / `Biblioteca` |

**[I]** `codice` è la nomenclatura ministeriale francese dei locali (03 = salle banalisée, 26 = CDI); il byte è il codice numerico. L'esistenza del tipo `TNetCategorieSalle` (**[F]** stringa a `0x00076420`) conferma che **l'aula ha un attributo "categoria" come FK a questa tabella** — ma il campo sta dentro il record cifrato.

### 3.2 `SITE` / `TNetSite` — in chiaro

**[F]** Offset `0x000926cf`, 3 record, corpo variabile:

```
id=1  01 0a 00 00 00 "Principale"  ff 00 00 00
id=2  00 07 00 00 00 "Succ. 2"     00 ff 40 00
id=3  00 07 00 00 00 "Succ. 1"     00 ff ff 00
```

**[F]** Layout: `byte flag (1 = sito principale) | nome(str) | RGB + 00`.
Colori: `Principale` = `#FF0000`, `Succ. 2` = `#00FF40`, `Succ. 1` = `#00FFFF`.

**[I]** L'aula ha un attributo "sito" (FK a `SITE`), ma anche questo è dentro il record cifrato: **non verificabile qui**.

### 3.3 `RELATIONSALLES` / `TNetRelationSalles` — in chiaro

**[F]** Offset `0x000e43ca`, 2 record:

```
000e43fa:  30 00 00 00 03 00 00 00 02 00 00 00 41 72 54 69   0...........ArTi
000e440a:  01 00 00 00 1b 00 00 00 33 00 00 00 01 00 00 00   ........3.......
000e441a:  41 72 54 69 03 00 00 00 1b 00 00 00 34 00 00 00   ArTi........4...
000e442a:  02 00 00 00                                       ....
```

| ident | campo A | campo B | campo C |
|---|---|---|---|
| 1 | 27 (`0x1b`) | 51 (`0x33`) | 1 |
| 3 | 27 (`0x1b`) | 52 (`0x34`) | 2 |

**[I]** Relazione fra due aule: 27 è un'aula "contenitore" e 51/52 le aule contenute (o viceversa). Tutti e tre gli ident (27, 51, 52) stanno sotto il `maxIdent`=56 di `SALLE`. **[?]** La semantica esatta (aula divisibile? aula di ripiego?) non è determinabile.

### 3.4 `MATERIEL` / `TNetMateriel` — in chiaro

**[F]** 3 record, corpo `nome(str) | uint32 quantità | zeri`:

```
id=1  0f 00 00 00 "Videoproiettore"  03 00 00 00
id=2  0c 00 00 00 "PC portatile"     05 00 00 00
id=3  06 00 00 00 "Tablet"           32 00 00 00   (= 50)
```

**[I]** Il materiale è una **risorsa prenotabile con quantità**, distinta dall'aula. Rilevante per il modello: EDT separa aula e attrezzatura.

### 3.5 Aule effettivamente usate dai corsi

**[F]** Dalle relazioni corso→risorsa di genere 4 (vedi §5.3): **9 aule distinte** su 18, ident `20, 21, 22, 24, 25, 26, 27, 31, 50`, con 167 relazioni totali (`27` è la più usata, 46 volte).

**[F]** Controllo di occupazione: contando gli slot (aula, place) occupati dai corsi piazzati si ottengono **97 slot, di cui 34 con più di un corso**. Per confronto, sugli stessi dati: docenti 1333 slot / 7 conflitti, classi 1320 slot / 1 conflitto.

**[I]** Le aule **non** sono a occupazione esclusiva: coerente con l'attributo EDT "numero di corsi simultanei" dell'aula (aula 27 = palestra, usata contemporaneamente da più classi di SCIENZE MOTORIE — vedi §5.4). Questo è un attributo reale dell'aula, anche se il suo valore è cifrato.

**Riepilogo attributi aula.** Attestati indirettamente: **categoria** (`TNetCategorieSalle` esiste come tabella FK), **sito** (`SITE` esiste), **relazione fra aule** (`TNetRelationSalles`), **capacità di corsi simultanei** (dedotta dai conflitti). **[?] Capienza in posti: nessuna evidenza recuperabile da questo file.**

---

## 4. Parti di classe e gruppi

### 4.1 Le modalità di sdoppiamento sono **parametri globali**, non dati

**[F]** Offset `0x00001360`, sezione `RESS` della testata — presente **identica in entrambe le basi**:

```
00001360:  00 00 52 45 53 53 01 01 01 00 00 00 47 01 00 00   ..RESS......G...
00001370:  00 07 00 00 00 46 65 6d 6d 69 6e 65 06 00 00 00   .....Femmine....
00001380:  4d 61 73 63 68 69 06 00 00 00 31 54 65 72 7a 6f   Maschi....1Terzo
00001390:  06 00 00 00 32 54 65 72 7a 69 0c 00 00 00 53 64   ....2Terzi....Sd
000013a0:  6f 70 70 69 61 6d 65 6e 74 6f 0c 00 00 00 55 6e   oppiamento....Un
000013b0:  54 65 72 7a 6f 44 75 65 54 65 0c 00 00 00 4d 61   TerzoDueTe....Ma
000013c0:  73 63 68 69 6f 2f 46 65 6d 6d 0c 00 00 00 53 75   schio/Femm....Su
000013d0:  64 64 69 76 69 73 69 6f 6e 65 01 02 00 00 00 47   ddivisione.....G
000013e0:  2e 01 ...                                          .
```

Ordine: `Femmine`, `Maschi`, `1Terzo`, `2Terzi`, `Sdoppiamento`, `UnTerzoDueTe[rzi]`, `Maschio/Femm[ina]`, `Suddivisione`; poi `G.` e (a `0x1409`) `Gr.`.

**[F]** In `Esempio.edt` le ultime tre sono **troncate a 12 caratteri**; in `example_2.edt` sono complete (`UnTerzoDueTerzi` a `0x1399`, `Maschio/Femmina` a `0x13ac`). `Esempio.edt` ha `DATECONSTRUCTION` 2011.

**[I]** Sono **modelli di denominazione** configurabili usati per battezzare automaticamente le parti generate, non un enum applicato ai singoli record. `G.` / `Gr.` sono i prefissi per i gruppi. Nessuna di queste stringhe compare nei record di `PARTIEDECLASSE`.

### 4.2 `PARTIEDECLASSE` / `TNetPartieDeClasse`

**[F]** Offset `0x0014b915`, paylen 7460, maxIdent 212, **188 record** (187 parti + il record riservato). Corpo **a lunghezza variabile**, layout:

```
uint32 lunghezzaNome | nome (ANSI) | 5 byte (sempre 00) | uint32 A | uint32 B | 14 byte di coda
```

Record letterali:

```
id=20  09 00 00 00 "1 B/R_ALT" 00 00 00 00 00 | 18 00 00 00 | 0a 00 00 00 | 00×14
id=21  09 00 00 00 "1 B/R_REL" 00 00 00 00 00 | 18 00 00 00 | 0a 00 00 00 | 00×14
id=26  06 00 00 00 "1C_ALT"    00 00 00 00 00 | 04 00 00 00 | 0d 00 00 00 | 00×14
id=32  00 00 00 00             00 00 00 00 00 | 09 00 00 00 | 10 00 00 00 | 00 00 00 00 00 00 00 00 0b e0 00 00 00 00
```

#### Campo A = ident di `CLASSE` — **confermato**

**[F]** Mappa ident→nome estratta da `CLASSE` (§4.4):
`4 = 1C`, `17 = 1F`, `21 = 1 A/R`, `24 = 1 B/R`.

**[F]** Corrispondenza con i nomi delle parti:

| parte | nome | A | nome classe A |
|---|---|---|---|
| 20/21 | `1 B/R_ALT` / `1 B/R_REL` | 24 | `1 B/R` ✔ |
| 22/23 | `1 A/R_ALT` / `1 A/R_REL` | 21 | `1 A/R` ✔ |
| 24/25 | `1F_ALT` / `1F_REL` | 17 | `1F` ✔ |
| 26/27 | `1C_ALT` / `1C_REL` | 4 | `1C` ✔ |

Quattro corrispondenze indipendenti su nomi non banali: **A è l'ident della classe**.

#### Campo B = ident di raggruppamento (ripartizione)

**[F]** Le coppie ALT/REL della stessa classe **condividono B** (10, 11, 12, 13). Distribuzione completa di (A,B):

```
(9,16)×20  (3,18)×20  (12,19)×20  (7,20)×20  (21,23)×20  (2,24)×20
(20,17)×17 (45,21)×17 (37,22)×17
(24,10)×2  (21,11)×2  (17,12)×2   (4,13)×2
A distinti: 17   B distinti: 18
```

**[I]** B identifica la **ripartizione** (il "taglio" della classe): tutte le parti nate dallo stesso sdoppiamento condividono B. Le coppie da 2 sono gli sdoppiamenti IRC/alternativa; i blocchi da 17–20 parti sono ripartizioni molto fini della stessa classe.

#### Due famiglie di parti

**[F]** Solo **8 parti hanno un nome**: `1 B/R_ALT`, `1 B/R_REL`, `1 A/R_ALT`, `1 A/R_REL`, `1F_ALT`, `1F_REL`, `1C_ALT`, `1C_REL`. Le altre ~179 hanno nome vuoto e portano nella coda un byte `0x0b` seguito da un `uint32` crescente e unico per record (224, 235, 260, 272, 281, 284, 287, 299, …, 395, 405, 438, 454, 499, 503).

**[I]** Le parti **nominate** sono la coppia **IRC / attività alternativa** (`_REL` = religione, `_ALT` = alternativa) — esattamente il caso che il progetto ha aperto. EDT la modella come **due parti della stessa classe che condividono lo stesso ident di ripartizione B**, non come un gruppo.
**[?]** Il significato del `uint32` nella coda delle parti anonime non è determinato (l'ipotesi più naturale è un rimando alla tabella alunni/iscrizioni, ma non l'ho verificata).

**[F]** Delle 187 parti, solo **16** sono referenziate da un corso (§5.3, genere 3): gli ident `20–27` (le 8 nominate IRC/ALT) e `205–212`. Le parti anonime `32…204` **non compaiono in nessun corso**.

### 4.3 `GROUPE` / `TNetGroupe`

**[F]** Offset `0x0014d6c5`, paylen 261, maxIdent 24, **4 record** (3 gruppi + riservato). Corpo variabile:

```
id=20  00 | 10 00 00 00 "FRANCESE 1AA-1BA"   | 00×8 | ff ff 99 00 | 06 00 00 00 | 01 00 00 00 | 01 00 00 00 | 00×8 | 01 00 00 00 | 00×8
id=21  00 | 10 00 00 00 "SPAGNOLO 1AA-1BA"   | 00×8 | ff ff 99 00 | 06 00 00 00 | ...
id=24  00 | 11 00 00 00 "ALTERNATIVA 1H-2D"  | 00×8 | ff ff 99 00 | 05 00 00 00 | ...
```

**[F]** Layout: `byte | nome(str) | 8 byte | RGB(ff ff 99) + 00 | uint32 (6/6/5) | uint32 1 | uint32 1 | … `.
**[F]** Colore `#FFFF99` (giallo pallido) per tutti e tre.
**[I]** Il `uint32` a 6/6/5 è plausibilmente un contatore di effettivi o di parti costituenti. **[?]** Non determinato.

**Semantica dei nomi** (**[F]**, leggibili): i gruppi attraversano **più classi** — `FRANCESE 1AA-1BA` unisce 1AA e 1BA, `ALTERNATIVA 1H-2D` unisce 1H e 2D. È la differenza strutturale rispetto alle parti, che appartengono a **una sola** classe (campo A).

**[F]** I 3 gruppi sono usati in soli **5 corsi** (genere 1, §5.3).

### 4.4 `CLASSE` / `TNetClasse` — mappa ident → nome

**[F]** Offset `0x000fe7b9`, 41 record, corpo **fisso 263 byte** (il riservato 259). Layout iniziale: `byte | uint32 len | nome | …`.

```
2=1A  3=1B  4=1C  5=1D  6=1E  7=2A  8=2B  9=3C 10=2D 11=2E 12=3A 13=3B 14=2C
15=3D 16=3E 17=1F 18=2F 20=3F 21=1 A/R 22=2 A/R 23=3 A/R 24=1 B/R 25=2 B/R
26=3 B/R 27=1 A/A 28=2 A/A 29=3 A/A 30=1 B/A 31=2 B/A 32=3 B/A 33=1 C/A
34=2 C/A 35=3 C/A 36=1 D/A 37=2 D/A 41=3G 42=3 D/A 43=1G 44=1H 45=1I
```

**[F]** Gli ident **non sono contigui** (mancano 19, 38, 39, 40): le cancellazioni lasciano buchi, gli ident non si riusano.
**[F]** Ogni record contiene un colore RGB (`ae 3d db` per 1A, `56 b3 42` per 1B, …) e due `double` uguali (`00 00 00 00 00 31 e6 40`) — **[I]** `TDateTime` (date di inizio/fine validità).

---

## 5. Griglia oraria, corsi e collocazione

### 5.1 `SEQUENCEHORAIRE` / `TNetSequenceHoraire` — 10 sequenze al giorno

**[F]** Offset `0x00001957`, 10 record, ident 41–50. Layout `uint32 rango | uint32 lunghezzaEtichetta | etichetta | 01 01`:

```
id=41  00 00 00 00 | 01 00 00 00 | "1" | 01 01     rango 0
id=42  01 00 00 00 | 01 00 00 00 | "2" | 01 01     rango 1
...
id=49  08 00 00 00 | 01 00 00 00 | "9" | 01 01     rango 8
id=50  09 00 00 00 | 02 00 00 00 | "10"| 01 01     rango 9
```

→ **10 posti (place) per giornata**, etichettati «1»…«10».

### 5.2 `LIBELLEHORAIRE` / `TNetLibelleHoraire` — orari in `TDateTime`

**[F]** Offset `0x00001729`, 22 record, corpo fisso 15 byte: `uint32 indice | byte griglia | double ora | 01 | byte`.
Il `double` è una frazione di giorno (TDateTime).

```
id=1   idx=0 griglia=0  55 55 55 55 55 55 d5 3f = 0,333333 -> 08:00
id=2   idx=1 griglia=0  00 00 00 00 00 00 d8 3f = 0,375000 -> 09:00
id=3   idx=2 griglia=0                            0,416667 -> 10:00
...
id=11  idx=10 griglia=0                           0,750000 -> 18:00
id=12  idx=0 griglia=1                            0,375000 -> 09:00
id=13  idx=1 griglia=1  8e e3 38 8e e3 38 da 3f = 0,409722 -> 09:50
id=14  idx=2 griglia=1                            0,458333 -> 11:00
id=15  idx=3 griglia=1  e4 38 8e e3 38 8e df 3f = 0,493056 -> 11:50
...
id=22  idx=10 griglia=1                           0,791667 -> 19:00
```

**[F]** Due serie da 11 etichette, distinte dal byte a offset 4 (0 / 1).
**[I]** La base definisce **due griglie orarie** (probabilmente per siti diversi): una a scansione oraria piena 08:00–18:00, una con moduli da 50 minuti 09:00–19:00.

### 5.3 `RELATIONCOURSRESSOURCE` — l'enum dei generi di risorsa

**[F]** Offset `0x0019301a`, **3008 record** (3007 da 39 byte + 1 da 56). Layout:

```
off 0   uint32  ident del corso
off 4   uint32  ident della risorsa
off 8   uint32  GENERE
off 13  8 byte  maschera settimane (default fe ff ff ff ff ff ff 7f)
off 21  uint32  = 1 (costante)
off 29  uint32  = 1 quasi sempre
```

Record letterale (`id=1934`): `da 03 00 00 | 1f 00 00 00 | 00 00 00 00 | 00 | fe ff ff ff ff ff ff 7f | 01 00 00 00 | …`
→ corso 986, risorsa 31, genere 0.

**Enum dei generi, derivato per conteggio** (**[F]** i numeri; **[I]** l'assegnazione dei nomi):

| genere | n relazioni | ident distinti | intervallo ident | tabella corrispondente | prova |
|---|---|---|---|---|---|
| 0 | 1165 | **76** | 3–100 | `PROFESSEUR` | 76 = `NBPROFS` esatto; `PROFESSEUR` maxIdent 100 |
| 1 | 5 | **3** | 20–24 | `GROUPE` | ident `{20,21,24}` = esattamente gli ident di `GROUPE` |
| 2 | 1200 | **40** | 2–45 | `CLASSE` | 40 = `NBCLASSES` esatto; `CLASSE` maxIdent 45 |
| 3 | 21 | 16 | 20–212 | `PARTIEDECLASSE` | maxIdent 212 identico; ident 20–27 = le parti nominate |
| 4 | 167 | 9 | 20–50 | `SALLE` | ≤ maxIdent 56; validato semanticamente (§5.4) |
| 7 | 21 | 5 | 1–12 | `PERSONNEL` | `PERSONNEL` ha 12 record, maxIdent 17 |
| 10 | 428 | **3** | 1–3 | `MATERIEL` **[I]** | ident `{1,2,3}`; vedi nota |

**Nota su genere 10.** **[F]** 428 relazioni su 329 corsi distinti → alcuni corsi ne hanno **due**. **[F]** Sia `SITE` sia `MATERIEL` hanno ident `{1,2,3}`. **[I]** Un corso non può stare in due siti, ma può richiedere due attrezzature: **`MATERIEL` è la lettura coerente** (§5.4 mostra un corso di INGLESE con `10:1` + `10:2` = Videoproiettore + PC portatile). Non è però una prova formale.

**[F]** La materia **non** passa da questa tabella: è un campo diretto del corso (§5.4).

### 5.4 `COURS` / `TNetCours` — corpo fisso di 107 byte

**[F]** Offset `0x000a9106`, paylen 140768, maxIdent 5124, **1224 record**, **tutti di 107 byte**.

Campi identificati (offset relativi all'inizio del corpo, dopo `ArTi`+ident):

| offset | tipo | contenuto | evidenza |
|---|---|---|---|
| 0–7 | — | sempre 0 | **[F]** |
| 8 | byte | 0/1/2/4 | **[F]** |
| 9 | byte | costante `0x03` | **[F]** |
| **10–15** | **48 bit** | **maschera settimane (effettiva)** | **[F]** valore dominante `fe ff fb 7f ff 1f` in 999 record |
| **18–25** | **64 bit** | **maschera settimane (piena)** | **[F]** valore dominante `fe ff ff ff ff ff ff 7f` in 1063 record = bit 1..62 |
| **42–45** | uint32 | **place (0–45)** | **[F]** |
| **46–49** | uint32 | **durata in sequenze** | **[F]** istogramma 1×885, 2×293, 3×41, 4×1, 8×4 |
| 60–63 | uint32 | 2 … 34095 | **[F]** **[?]** non identificato |
| **67–70** | uint32 | **ident `MATIERE`** | **[F]** i 18 valori sono un sottoinsieme stretto dei 21 ident di `MATIERE` |
| 71 | byte | 0–3 | **[F]** |
| 99–102 | uint32 | costante `ff ff ff ff` | **[F]** |
| **103–106** | uint32 | **place effettiva, `0xFFFFFFFF` = non piazzato** | **[F]** |

#### Maschera settimane — decodifica

**[F]** `fe ff fb 7f ff 1f` letto come intero LE a 48 bit ha i bit accesi:
`1–17, 19–30, 32–44` → **44 settimane, con la 18 e la 31 spente**.
**[I]** Sono le settimane di vacanza (Natale, Pasqua). Il campo a 64 bit con bit 1–62 è il dominio pieno delle settimane gestibili da EDT.

**[F]** La stessa maschera a 8 byte compare **per relazione** in `RELATIONCOURSRESSOURCE` (offset 13): una risorsa può partecipare a un corso solo in certe settimane.

#### Place — decodifica confermata

**[F]** `place` a offset 103 vale `0xFFFFFFFF` in **231** record; nei restanti **993**.
**[F]** I due campi place (42 e 103) coincidono in **esattamente 984** record = **`NBCOURSPLACES` = 984**.

**[F]** Istogramma dei valori piazzati: presenti 0–5, 7–15, 20–25, 27–35, 37–45. **Assenti: 6, 16–19, 26, 36 e tutto ≥ 46.**

**[I]** `place = giorno × 10 + rango`, con 10 sequenze/giorno (§5.1):
giorno 0 = 0–9, 1 = 10–19, 2 = 20–29, 3 = 30–39, 4 = 40–49. Il giorno 5 (sabato) è **inutilizzato**; il rango 6 (`place % 10 == 6`, ore 14:00) è quasi sempre vuoto — pausa pranzo.

#### Validazione: decodifica end-to-end

**[F]** Unendo `COURS` + `RELATIONCOURSRESSOURCE` + `CLASSE` + `MATIERE`:

```
cours 986   place=33 -> Gio seq4 (11:00) durata=1 materia='ITALIANO PER STRANIERI' | PROF:31
cours 2645  place=2  -> Lun seq3 (10:00) durata=2 materia='MATEMATICA'      | PROF:24 CLASSE:1A
cours 2646  place=5  -> Lun seq6 (13:00) durata=1 materia='SCIENZE MOTORIE' | PROF:8  CLASSE:1C SALLE:27
cours 2647  place=1  -> Lun seq2 (09:00) durata=1 materia='SCIENZE MOTORIE' | PROF:27 CLASSE:1A SALLE:27
cours 2648  place=0  -> Lun seq1 (08:00) durata=1 materia='SCIENZE MOTORIE' | PROF:27 CLASSE:1E SALLE:27
cours 2650  place=0  -> Lun seq1 (08:00) durata=1 materia='INGLESE'         | PROF:17 CLASSE:1A  10:1 10:2
cours 1651  place=11 -> Mar seq2 (09:00) durata=8 materia="ATTIVITA' DI SEGRETERIA" | PERS:5 PERS:2
```

Tre riscontri semantici indipendenti:
1. **Tutte** le SCIENZE MOTORIE cadono nell'aula 27 → genere 4 = aula, e l'aula 27 è la palestra.
2. Il corso da `durata=8` è ATTIVITÀ DI SEGRETERIA con due `PERSONNEL` → genere 7 = personale ATA.
3. Il corso di INGLESE ha due risorse di genere 10 → attrezzature (Videoproiettore + PC portatile).

**[F] Prova di consistenza globale** — contando gli slot `(risorsa, place)` occupati dai 993 corsi piazzati, espandendo per la durata:

| risorsa | slot occupati | slot con >1 corso |
|---|---|---|
| docenti (genere 0) | 1333 | **7** (0,5 %) |
| classi (genere 2) | 1320 | **1** (0,08 %) |
| aule (genere 4) | 97 | 34 (35 %) |

**[I]** Docenti e classi risultano praticamente privi di sovrapposizione: la decodifica di `place`, `durata` e dell'enum dei generi è corretta. I pochi residui si spiegano con corsi su settimane disgiunte (maschera settimane). Le aule sovrapposte confermano che l'aula ammette corsi simultanei (§3.5).

**[?]** I 1224 record di `COURS` contro `NBCOURS=984`: 231 non piazzati e 9 con i due campi place discordanti. Non ho stabilito cosa siano i record in eccesso (modelli? corsi di sostituzione? attività dei personali, che infatti compaiono qui?).

---

## 6. Vincoli e indisponibilità

### 6.1 `ABSENCERESSOURCE` / `TNetAbsenceRessource`

**[F]** Offset `0x0014d7ee`, paylen 12493, maxIdent 430, **227 record** = `NBABSENCESRESSOURCES` esatto. Corpo **fisso 47 byte**:

| offset | tipo | contenuto |
|---|---|---|
| 0–3 | uint32 | **A — place iniziale nell'anno** (0 … 2689) |
| 4–7 | uint32 | **B — place finale** (sempre ≥ A) |
| 8–11 | uint32 | C — 15 valori distinti: 1–9, 11, 12, 13, 27, 28, 30 |
| 12 | byte | 0 (194) / 2 (31) / 7 (2) |
| 13–16 | uint32 | **E — ident della risorsa** (non allineato) |
| 17–20 | uint32 | 0 |
| 21–24 | uint32 | **G — genere: 3 (198 record) / 2 (29)** |
| 28–35 | double | **`TDateTime`** — 0 in 28 record |
| 36–39 | uint32 | 13 (197) / 17 (2) / 0 (28) |
| 40–43 | uint32 | 2 (199) / 0 (28) |

Record letterali:

```
id=28   02 00 00 00 02 00 00 00 04 00 00 00 00 48 00 00 00 00 00 00 00 03 00 00 00 00×22
id=49   96 00 00 00 9f 00 00 00 0d 00 00 00 00 29 00 00 00 00 00 00 00 03 00 00 00 00×22
id=53   1a 08 00 00 1b 08 00 00 04 00 00 00 00 29 00 00 00 00 00 00 00 03 00 00 00 00×22
```

#### Genere G — separazione netta

**[F]** Suddividendo E per G:

| G | n record | ident distinti | intervallo | datati |
|---|---|---|---|---|
| 3 | 198 | 67 | 3 – 99 | 174 |
| 2 | 29 | 17 | 2 – 43 | 25 |

**[I]** G=3 → `PROFESSEUR` (76 docenti, ident 3–100); G=2 → `CLASSE` (40 classi, ident 2–45). Gli intervalli sono disgiunti e combaciano esattamente con le due tabelle.
**[!] Attenzione**: `2 = CLASSE` coincide con l'enum di `RELATIONCOURSRESSOURCE`, ma il docente lì è **0** e qui è **3**. **[?]** Non ho spiegato la discrepanza — o sono due enum diversi, o uno dei due campi non è il genere che credo. La separazione statistica per intervallo di ident resta però solida in entrambi i casi.

#### A/B — place assoluta nell'anno

**[F]** Nei record datati, A e B formano intervalli **allineati a multipli di 10 e ampi 10**:
`A=70 B=79`, `A=90 B=99`, `A=110 B=119`.
**[F]** A max = 2689 → 2689 / 10 ≈ 269 giornate. Con 6 giorni/settimana ≈ 45 settimane.

**[I]** `place_anno = giornata_assoluta × 10 + rango`. Gli intervalli di ampiezza 10 allineati sono **assenze di giornata intera**. È la stessa unità della place settimanale di `COURS`, ma estesa all'anno.

**[F]** Le date (`TDateTime` a offset 28) spaziano da 2024-07-01 a 2026-06-05; **28 record hanno data 0** e sono i primi per ident (28, 30, 31, 32, 46, 49, 51, 53, 55, 56 …), con anche i campi a 36 e 40 azzerati.

**[I]** Due famiglie: **28 record senza data** = indisponibilità ricorrenti (vincolo strutturale) e **199 con data** = assenze effettive. Il campo a offset 36 (valore 13) è plausibilmente un motivo/tipo, azzerato nei record strutturali.

### 6.2 Tabelle di vincolo presenti (in chiaro, non decodificate in dettaglio)

**[F]** Presenti nello schema e popolate in `Esempio.edt` (dimensione sezione, confronto con `example_2.edt`):

| tabella | classe | Esempio | example_2 |
|---|---|---|---|
| `CONTRAINTEMATIERECLASSE` | `TNetContrainteMatiereClasse` | 21 450 | 3 510 |
| `CONTRAINTESPROFESSEUR` | `TNetContraintesProfesseur` | 6 080 | 1 614 |
| `DISPONIBILITE` | `TNetDisponibilite` | 29 518 | 58 |
| `PREFSOPTIM` | `TNetPrefsOptim` | 2 086 | 52 |
| `MODIFICATIONCOURS` | `TNetModificationCours` | 31 890 | 7 450 |
| `ANNULATIONCOURS` | `TNetAnnulationCours` | 37 184 | 62 |
| `RELATIONCOURSSUBSTITUT` | `TNetRelationCoursSubstitut` | 6 033 | 76 |

**[F]** `TNetContraintesClasse`, `TNetContrainteCoursACours`, `TNetInfosContrainteEcart`, `TNetInfosContrainteQuinzaine`, `TNetInfosContrainteSuccession` — **non trovati** né come nome di sezione `DATA` né come stringa in nessuna delle due basi.
**[I]** O non esistono con quei nomi in questo millesimo, o sono strutture annidate dentro altri record (non tabelle di primo livello).

---

## 7. Ricapitolazione del diff fra le due basi

**[F]** Stesse 744 tabelle. Tabelle presenti solo/soprattutto in `Esempio.edt`, ordinate per delta di dimensione:

```
AUTHENTIFIANT     471002 vs  10154     ELEVE            279866 vs     42
RELATIONCOURSRESSOURCE 141469 vs 26772 COURS            140802 vs  32702
COORDONNEES        72910 vs     54     DISPONIBILITE     29518 vs     58
CONTRAINTEMATIERECLASSE 21450 vs 3510  PROFESSEUR        23140 vs   5972
ABSENCERESSOURCE   12549 vs     64     CLASSE            11259 vs   3021
PARTIEDECLASSE      7512 vs     99     GROUPE (297 vs ~40)
SALLE (1282 vs vuota)                  SITE (115 vs vuota)
```

Il diff isola correttamente ciò che è stato chiesto: aule, siti, parti, gruppi, piazzamento, assenze.

---

## 8. Cosa resta ignoto

1. **Contenuto di `SALLE`** — cifrato. Nome, capienza, categoria, sito e numero di corsi simultanei delle 18 aule **non sono leggibili** da questo file. Idem per docenti, alunni, responsabili, personale, recapiti.
2. **Chiave e algoritmo di cifratura** — non cercati (starebbero nel binario da 142 MB). Indizi: blocchi da 16 byte, `REFERENCECLIENT` a `0x578` (`31E22EF2E1A66FD4037F3EC4736F676D93C8D92D01000000`), il GUID a `0x2C` (`{215FE779-8E94-4328-A1D7-7C6E51F2D694}`) e la sezione `PROT` a `0x9BC`.
3. **Discrepanza dell'enum dei generi** fra `RELATIONCOURSRESSOURCE` (docente = 0) e `ABSENCERESSOURCE` (docente = 3).
4. **Genere 10** — `MATERIEL` o `SITE`: argomentato ma non provato.
5. **`COURS` offset 60–63** (2 … 34095) e i byte a 8, 54–59, 65, 71–96.
6. **Coda delle parti anonime** — il `uint32` unico per record (224 … 503).
7. **I 240 record di `COURS` in eccesso** rispetto a `NBCOURS=984`.
8. **`DureeMinutes` / `DureeSequences`** dello XSD ufficiale: nel binario esiste solo una **durata in sequenze** (offset 46). Nessun campo in minuti individuato; la durata in minuti si ricava dalla griglia `LIBELLEHORAIRE`.
9. **Campo C di `ABSENCERESSOURCE`** (15 valori distinti) e i byte a 12, 36, 40.

---

## 9. Nota metodologica

Script prodotti in `<scratchpad>/edt/`: `scan.py` (stringhe Delphi con offset), `sections.py` (enumerazione delle 744 tabelle), `recs.py` (testate di record + rilevamento tabelle cifrate), `raw.py` / `split.py` (dump per record), `prof.py` / `an2..an9.py` (profilazione per colonna e verifiche incrociate).

La tecnica che ha reso decodificabile il formato è la **profilazione per colonna** su tabelle a record fisso: per ogni offset si contano i valori distinti e l'intervallo, poi si confronta la cardinalità con i totali dichiarati in `CARTEIDENTITE`. È così che l'enum dei generi è caduto (76 = `NBPROFS`, 40 = `NBCLASSES`, 3 = ident di `GROUPE`) e che place/durata sono stati validati (984 = `NBCOURSPLACES`, zero collisioni docente/classe).
