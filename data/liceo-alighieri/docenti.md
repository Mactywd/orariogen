# Docenti — le 21 cattedre

Ogni riga quadra a `+/- = 0`: le ore assegnate sono esattamente il monte ore
contrattuale (`Mh/s`), e il test lo verifica cattedra per cattedra.

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
| N01 | Tosi Alberto | TOSI | SCI in 1A 2A 1C 2C 3A 4A 5A | 17 |
| N02 | Urbani Chiara | URBAN | SCI in 1B–5B | **10** |
| A01 | Vitali Renzo | VITAL | DIS nelle 7 scientifiche, STA in 3B 4B 5B | 20 |
| P01 | Zanetti Luca | ZANET | MOT in 1A 2A 3A 4A 5A 1C | **12** |
| P02 | Bruni Sofia | BRUNI | MOT in 2C 1B 2B 3B 4B 5B | **12** |
| R01 | Colombo Padre Egidio | COLOM | IRC in tutte e dodici | **12** |
| | | | **Totale** | **345** |

## I quattro tempi parziali

🔑 **L06** (12 h), **N02** (10 h), **P01/P02** (12 h) e **R01** (12 h) esistono
perché `max_presence` — *«lavora al più N giorni»* — **non ha soggetto su un
collegio di sole cattedre piene**: con 21 ore un docente sta a scuola comunque
tutti i giorni, e il vincolo è vero per costruzione. Il portatore designato è
L06 (ondata 3): dodici ore su cinque giorni si comprimono a tre.

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

Sei cattedre su ventuno: R01, A01, N01, E01, P01, E02. Vedi [sedi.md](sedi.md).
