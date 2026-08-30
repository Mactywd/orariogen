# Docenti — le 23 cattedre

Ogni riga quadra a `+/- = 0`: le ore assegnate sono esattamente il monte ore
contrattuale (`Mh/s`), e il test lo verifica cattedra per cattedra.

⚠ **`Mh/s` non si legge dal quadro orario**, e l'ondata 2 lo rende visibile: N01
lavora **19** ore per 17 ore di curriculum, perché le due ore di laboratorio
sdoppiate — 3A dall'ondata 2, 4A dall'ondata 4 — le insegna due volte
ciascuna. Vedi [gruppi.md](gruppi.md) §3.

| ID | Docente | Abbr. | Insegna | Mh/s |
|---|---|---|---|---:|
| L01 | Amato Cristina | AMATO | ITA, LAT, STG in 1A 2A | 20 |
| L02 | Beltrami Nicola | BELTR | ITA, LAT, STG in 1C 2C | 20 |
| L03 | Cavalli Marta | CAVAL | ITA, LAT in 3A 4A 5A | 21 |
| L04 | De Santis Ilaria | DESAN | ITA, STG in 1B 2B | 14 |
| L05 | Ferretti Ugo | FERRE | LAT, GRE in 1B 2B | 18 |
| L06 | Gentili Marco | GENTI | ITA in 3B 4B 5B | **12** |
| L07 | Iacopini Rosa | IACOP | LAT, GRE in 3B 4B 5B | 21 |
| S01 | Lanzi Federico | LANZI | FIL, STO in 3A 4A 5A | 15 |
| S02 | Manzoni Eleonora | MANZO | FIL, STO in 3B 4B 5B | 18 |
| E01 | Novelli Serena | NOVEL | ING in 1A 2A 3A 4A 5A 1C | 18 |
| E02 | Orlandi Piero | ORLAN | ING in 2C 1B 2B 3B 4B 5B | 18 |
| M01 | Pagani Diego | PAGAN | MAT, FIS in 1A 2A | 14 |
| M02 | Quaranta Livia | QUARA | MAT, FIS in 1C 2C | 14 |
| M03 | Rinaldi Tommaso | RINAL | MAT, FIS in 3A 4A 5A | 21 |
| M04 | Sartori Gaia | SARTO | MAT in 1B–5B, FIS in 3B 4B 5B | 18 |
| N01 | Tosi Alberto | TOSI | SCI in 1A 2A 1C 2C 3A 4A 5A (3A e 4A sdoppiate) | **19** |
| N02 | Urbani Chiara | URBAN | SCI in 1B–5B | **10** |
| A01 | Vitali Renzo | VITAL | DIS nelle 7 scientifiche, STA in 3B 4B 5B | 20 |
| P01 | Zanetti Luca | ZANET | MOT in 1A 2A 3A 4A 5A 1C | **12** |
| P02 | Bruni Sofia | BRUNI | MOT in 2C 1B 2B 3B 4B 5B | **12** |
| R01 | Colombo Padre Egidio | COLOM | IRC in tutte e dodici | **12** |
| R02 | Donati Marta | DONAT | ALT (attività alternativa) in tutte e dodici | **12** |
| I01 | Ricci Dario | RICCI | INF in 2C (parte Scienze Applicate) | **3** |
| | | | **Totale erogato** | **362** |

## I tempi parziali, e lo spezzone

🔑 **L06** (12 h), **N02** (10 h), **P01/P02** (12 h), **R01/R02** (12 h) esistono
perché `max_presence` — *«lavora al più N giorni»* — **non ha soggetto su un
collegio di sole cattedre piene**: con 21 ore un docente sta a scuola comunque
tutti i giorni, e il vincolo è vero per costruzione. Il portatore designato è
L06 (ondata 3): dodici ore su cinque giorni si comprimono a tre.

⚠ **I01 sta a tre ore**, ed è lo **spezzone** che un'articolata produce davvero
in una scuola piccola: il nostro modello lo rappresenta senza dire niente,
perché `Mh/s` è un numero e non una cattedra.

⚠ Al Fermi i part-time ci sono (D09 a 6 h, D15 a 9 h) ma **non portano alcun
vincolo**: la tabella `ResourceTimeConstraint` è vuota, quindi otto famiglie su
otto non hanno mai visto un dato. È metà della ragione per cui questo dataset
esiste.

## Le cattedre monomateria e quelle a due materie

Undici cattedre insegnano una materia sola, dieci ne portano due o tre. La
distinzione conta per `preferred_subject` (la **preferenza**, distinta dalla
capacità e dall'assegnazione — `docs/edt/docenti.md`) e per le famiglie
dell'asse Relazione, che ragionano su coppie di materie: MAT e FIS sulla stessa
cattedra in M01, M02 e M03 è ciò che rende `same_half_day_incompatible` una
richiesta sensata invece di un capriccio.

## Chi attraversa le sedi

Sette cattedre su ventitré: R01, **R02**, A01, N01, E01, P01, E02 — l'attività
alternativa segue l'IRC in tutte e dodici le classi, succursale compresa. Vedi
[sedi.md](sedi.md).

## ⚠ Dove la contabilità della cattedra è una finzione

Le tre ore di E01 sul livello base di inglese sono registrate su **1A** e
quelle di E02 sul livello avanzato su **1B**, mentre entrambi insegnano ad
alunni di **entrambe** le classi: `TeachingAssignment` ha una FK alla classe, e
un raggruppamento trasversale non ci sta dentro. Il monte ore quadra e l'orario
è corretto — è la riga di bilancio a mentire. Scritto qui perché non venga
scoperto come sorpresa; vedi [gruppi.md](gruppi.md) §4.

## I vincoli orari che portano

Sette cattedre su ventitré portano una riga di `ResourceTimeConstraint`
(ondata 3): N02 la distribuzione minima, M03 il tetto orario con la mattina
sotto la giornata, L06 il tempo parziale, A01 l'entrata non prima della
seconda, P01 i giorni liberi garantiti, R02 «solo mezza giornata al giorno»,
R01 le due giornate del cappellano più il tetto ai cambi di sede, L03 il
D.T.B. Il perché di ciascun portatore — e perché la riga sta **al bordo** —
sta in [vincoli.md](vincoli.md).
