# Piani di studi e quadri orari

Undici piani: **indirizzo × anno**, che è la chiave `Formation + Specialite`
dello schema di scambio — i due indirizzi per cinque anni, più `SAP2` (Scienze
Applicate) che esiste per la sola 2C articolata. **128 righe di servizio.**

⚠ **Le tabelle qui sotto sono il curriculum di un alunno**, e non la somma
delle righe del piano. Ogni piano porta anche la riga `ALT` (attività
alternativa) in **alternativa** all'IRC: la somma delle righe è quindi un'ora
più alta, perché di quelle due un alunno ne fa una. Il piano è un **catalogo**,
non un curriculum ([ADR-020](../../docs/decisioni.md)), e le due righe portano
`election_group = "RELIGIONE"` a dirlo. Vedi [gruppi.md](gruppi.md).

## Liceo Scientifico (`SCI1`…`SCI5`)

| Materia | Biennio | Triennio |
|---|---:|---:|
| ITA Italiano | 4 | 4 |
| LAT Latino | 3 | 3 |
| ING Inglese | 3 | 3 |
| STG Storia e Geografia | 3 | — |
| STO Storia | — | 2 |
| FIL Filosofia | — | 3 |
| MAT Matematica | 5 | 4 |
| FIS Fisica | 2 | 3 |
| SCI Scienze naturali | 2 | 3 |
| DIS Disegno e St. dell'Arte | 2 | 2 |
| MOT Scienze motorie | 2 | 2 |
| IRC Religione **o** ALT alternativa | 1 | 1 |
| **Totale per alunno** | **27** | **30** |

## Liceo Classico (`CLA1`…`CLA5`)

| Materia | Biennio | Triennio |
|---|---:|---:|
| ITA Italiano | 4 | 4 |
| LAT Latino | 5 | 4 |
| GRE Greco | 4 | 3 |
| ING Inglese | 3 | 3 |
| STG Storia e Geografia | 3 | — |
| STO Storia | — | 3 |
| FIL Filosofia | — | 3 |
| MAT Matematica | 3 | 2 |
| FIS Fisica | — | 2 |
| SCI Scienze naturali | 2 | 2 |
| STA Storia dell'Arte | — | 2 |
| MOT Scienze motorie | 2 | 2 |
| IRC Religione **o** ALT alternativa | 1 | 1 |
| **Totale per alunno** | **27** | **31** |

🔑 **I due quadri divergono per forma, non per totale**: il classico ha greco e
non ha disegno, il triennio classico fa un'ora in più. Due indirizzi che
differissero solo nei numeri non eserciterebbero niente che un indirizzo solo
non eserciti già.

## `SAP2` — il piano della classe articolata

Come lo scientifico del biennio, con **informatica al posto del latino** (3
ore, stesso totale). Le ore comuni sono dichiarate in **entrambi** i piani,
perché sono ore che entrambe le popolazioni della 2C ricevono. Vedi
[gruppi.md](gruppi.md) §2.

## Lo spezzamento in blocchi

Il monte ore diventa attività. Ciò che non compare qui è un'ora singola per
ogni ora del quadro.

| Materia e ore | Blocchi | Perché |
|---|---|---|
| MAT 5 (biennio scientifico) | 2 + 1 + 1 + 1 | gli stessi quattro blocchi osservati al Fermi |
| FIS 3 (triennio scientifico) | 2 + 1 | l'ora doppia di laboratorio |
| SCI 3 (triennio scientifico) | 2 + 1 | idem |
| MOT 2 (ogni classe) | 2 | la palestra si prende due ore di fila |

⚠ In **3A** le scienze non fanno più un blocco: l'ondata 2 le sdoppia in due
ore a classe intera più un'ora di laboratorio a mezza classe, quindi i blocchi
lunghi sono **21** e non 22.

⚠ I 22 blocchi lunghi dichiarano `respects_breaks`, quindi **non attraversano
la pausa mensa**: è ciò che rende `structural:grid` non inerte. Le ore singole
no, e deliberatamente — dichiararlo su tutte renderebbe la casella
indistinguibile dal default.

## Quadratura

**345 ore-alunno** = 4×27 (biennio scientifico: 1A, 2A, 1C, 2C) + 3×30 (triennio
scientifico) + 2×27 (biennio classico) + 3×31 (triennio classico).

**361 ore erogate** = 345 + 12 (l'attività alternativa, una per classe) + 3
(l'informatica della 2C articolata) + 1 (l'ora di laboratorio di 3A, insegnata
due volte). ⚠ Sono i due numeri da non confondere: il primo è ciò che un alunno
riceve, il secondo ciò che qualcuno insegna.
