# Sedi

Due sedi, che è il minimo perché esista un cambio.

| Sede | Cosa ospita |
|---|---|
| **Centrale** | le dieci classi delle sezioni A (scientifico) e B (classico), i laboratori specializzati, la palestra, l'aula magna |
| **Succursale** | il biennio della sezione C (1C, 2C), un laboratorio unico e una palestra |

`InstituteSettings.site_transition_slots = 1`: fra due lezioni in sedi diverse
serve **una fascia libera**. ⚠ È un vincolo *hard*, e non è simmetrico con
nulla — `docs/edt/tempo-e-calendario.md` documenta che in EDT lo spostamento è
dichiarato per **coppia orientata**; qui il parametro è unico, che è la forma
minima del nostro modello.

## Chi attraversa

🔑 Senza un docente che insegna in entrambe le sedi, due sedi sono due scuole e
nessun vincolo di transizione ha soggetto. **Otto cattedre su ventitré**
attraversano:

| Docente | Materie | Perché attraversa |
|---|---|---|
| **R01** Colombo | IRC | insegna in **tutte e dodici** le classi |
| **A01** Vitali | DIS, STA | il disegno è dello scientifico, e la C è scientifica |
| **N01** Tosi | SCI | le sette classi scientifiche, C compresa |
| **E01** Novelli | ING | le cinque della A più 1C |
| **P01** Zanetti | MOT | le cinque della A più 1C |
| **E02** Orlandi | ING | 2C più tutta la B |
| **R02** Donati | ALT | l'alternativa, in **tutte e dodici** come l'IRC |
| **P02** Bruni | MOT | 2C più tutta la B |

⚠ **L02** (lettere) e **M02** (matematica e fisica) sono invece *solo*
succursale: una sezione staccata ha sempre qualche cattedra che non si muove,
e senza di loro il vincolo di transizione sarebbe uniforme su tutti.

R01 è il portatore di `max_site_changes` (ondata 3): dodici ore
sparse su due sedi sono il caso in cui un tetto giornaliero di cambi morde
davvero.

## Cosa esercita

- `structural:site_transition` — **muto sul Fermi**, che ha zero righe `Site`.
- `max_site_changes` (ondata 3).
- Il filtro delle aule per sede nella seconda fase: nessuna attività della
  succursale può chiedere un'aula della centrale, e un test lo verifica.
- [ADR-019](../../docs/decisioni.md) — *dentro una fascia non si viaggia*.
  🔑 **Misurato all'ondata 5**, e il portatore non è un docente: è il carrello
  di portatili, l'unica risorsa del banco senza sede e a capienza cumulativa.
  A capienza 1 la regola coincide riga per riga con la vecchia, quindi non
  c'era modo di vederla prima. Vedi [risorse.md](risorse.md).

⚠ E lì l'ondata 5 ha trovato **L6**: `structural:site_transition` posta la
clausola «due sedi sulla stessa fascia» su *ogni* chiave di occupazione,
carrelli compresi — cioè pretende un tempo di viaggio da una risorsa che non
viaggia.
