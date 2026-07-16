# Dataset — Liceo Scientifico "Enrico Fermi"

Scuola fittizia usata per il reverse engineering di EDT. Dimensionata per generare
**conflitti reali** (docenti single-point, risorse contese, spezzoni) senza rendere
l'inserimento manuale in EDT interminabile.

## Parametri

| Parametro | Valore |
|---|---|
| Sezioni | A, B |
| Classi | 10 (1A–5A, 1B–5B) |
| Alunni per classe | ~26 |
| Docenti | 18 |
| Materie | 12 |
| Giorni | lunedì – venerdì |
| Ore giornaliere | 6 (08:00 – 14:00), moduli da 60' |
| Monte ore | 27 h/sett. biennio, 30 h/sett. triennio |
| **Ore-classe totali** | **288** |

## Quadratura

Le 288 ore-classe totali coincidono con la somma delle ore delle 18 cattedre
(vedi [docenti.md](docenti.md)) e con la somma del quadro orario per le 10 classi
(vedi [classi.md](classi.md)). La coerenza è verificata.

## Indice del dataset

- [discipline.md](discipline.md) — discipline + mappatura classe di concorso
- [materie.md](materie.md) — 12 materie e campo `Al./Rid.`
- [classi.md](classi.md) — 10 classi + quadro orario (monte ore per materia/livello)
- [docenti.md](docenti.md) — 18 cattedre
- [aule.md](aule.md) — aule e vincoli di occupazione
- [vincoli-attesi.md](vincoli-attesi.md) — conflitti inseriti apposta come test del solver

Per la **semantica** delle entità (non i dati) vedi [`docs/edt/`](../../docs/edt/).
