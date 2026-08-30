# Aule

Venti aule, divise per sede. La sede è sull'aula (`Resource.site`), e la
seconda fase non assegna mai un'aula di una sede a un'attività dell'altra.

## Centrale (16)

| Aula | Capienza | Qtà | Uso |
|---|---:|---:|---|
| A101–A105 | 28 | 1 | aule preferenziali di 1A–5A |
| B101–B105 | 24 | 1 | aule preferenziali di 1B–5B |
| LAB-FIS | 30 | 1 | fisica |
| LAB-SCI | 30 | 1 | scienze |
| **LAB-INF** | 25 | 1 | **condiviso**: fisica, scienze e disegno |
| AUL-DIS | 30 | 1 | disegno |
| PALESTRA | 60 | **2** | scienze motorie — due classi insieme |
| AULA-MAGNA | 100 | 1 | — |

## Succursale (4)

| Aula | Capienza | Qtà | Uso |
|---|---:|---:|---|
| C101, C102 | 26 | 1 | aule preferenziali di 1C, 2C |
| LAB-SUCC | 28 | 1 | fisica, scienze **e** informatica: il laboratorio unico |
| PAL-SUCC | 50 | 1 | scienze motorie |

## Le due asimmetrie, che sono deliberate

🔑 **`LAB-INF` è conteso da tre materie con docenti diversi.** È la stessa
scelta del Fermi, e la ragione è la stessa: a candidata unica l'occupazione se
la prende già il piazzamento, quindi la seconda fase confermerebbe una scelta
già fatta — zero gradi di libertà, e una misura che non può fallire.

🔑 **La succursale ha un laboratorio solo, e nessun ripiego.** Fisica e scienze
di 1C e 2C, più le tre ore di informatica della 2C articolata — **undici** ore
a settimana — si contendono `LAB-SUCC`, senza il `LAB-INF` su cui la centrale
ripiega. È il posto in cui la stretta si farà
sentire per prima quando le ondate 3–6 aggiungeranno i vincoli, ed è per questo
che le due sedi non sono simmetriche.

⚠ **`PALESTRA` a `Qtà` = 2** è il `Numero di aule` di EDT (colonna `Qtà`), non
un gruppo di aule e non una sotto-aula: la correzione documentata in
`docs/edt/aule.md`. `PAL-SUCC` sta a 1, e le due cose insieme fanno sì che il
campo non sia costante nel dataset.

## Cosa non vincola

La **capienza in alunni non è un vincolo**: la finestra `Aule disponibili` di
EDT dichiara `Sedi distaccate`, `Indisponibilità opzionali` e
`Indisponibilità`, e nient'altro. Qui è il **terzo livello** della catena delle
aule (`eccedenza_capienza`) — un criterio, come in EDT. Le B da 24 posti per 22
alunni e le A da 28 per 26 danno al criterio qualcosa da misurare senza che
nulla lo forzi.

⚠ E dall'ondata 2 `expected_students` è dichiarato anche su **ogni parte**, non
per completezza: `_effettivo` (`domain/solver/rooms.py`) restituisce `None`
appena un'unità non ce l'ha, e un'eccedenza sparirebbe in silenzio. Un
laboratorio a mezza classe porta dentro 13 alunni, non 26.

Categoria e tipologie non esistono nel nostro modello, e non sono un debito:
`docs/edt/aule.md` documenta che non vincolano.
