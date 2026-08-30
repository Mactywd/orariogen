# Piani di studi e quadri orari

Dieci piani: **indirizzo × anno**, che è la chiave `Formation + Specialite`
dello schema di scambio. 107 righe di servizio in tutto.

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
| IRC Religione | 1 | 1 |
| **Totale** | **27** | **30** |

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
| IRC Religione | 1 | 1 |
| **Totale** | **27** | **31** |

🔑 **I due quadri divergono per forma, non per totale**: il classico ha greco e
non ha disegno, il triennio classico fa un'ora in più. Due indirizzi che
differissero solo nei numeri non eserciterebbero niente che un indirizzo solo
non eserciti già.

## Lo spezzamento in blocchi

Il monte ore diventa attività. Ciò che non compare qui è un'ora singola per
ogni ora del quadro.

| Materia e ore | Blocchi | Perché |
|---|---|---|
| MAT 5 (biennio scientifico) | 2 + 1 + 1 + 1 | gli stessi quattro blocchi osservati al Fermi |
| FIS 3 (triennio scientifico) | 2 + 1 | l'ora doppia di laboratorio |
| SCI 3 (triennio scientifico) | 2 + 1 | idem |
| MOT 2 (ogni classe) | 2 | la palestra si prende due ore di fila |

⚠ I 22 blocchi lunghi dichiarano `respects_breaks`, quindi **non attraversano
la pausa mensa**: è ciò che rende `structural:grid` non inerte. Le ore singole
no, e deliberatamente — dichiararlo su tutte renderebbe la casella
indistinguibile dal default.

## Quadratura

345 ore-classe = 4×27 (biennio scientifico: 1A, 2A, 1C, 2C) + 3×30 (triennio
scientifico) + 2×27 (biennio classico) + 3×31 (triennio classico).
