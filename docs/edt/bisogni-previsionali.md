# Entità EDT — Bisogni previsionali (Previsione per materia)

## Cos'è

L'ambiente che trasforma il quadro orario in **fabbisogno ore per materia**: per
ogni materia, quante ore totali servono all'istituto (bisogni), aggregando i
servizi delle classi previsionali. È il ponte fra i piani/classi e la
ripartizione dei servizi ai docenti.

## Struttura osservata (2026-07-09)

Filtri in alto: **Scelta del livello** (Tutti i livelli / per anno) e **Calcolo**
(dropdown, valore "Classi previsionali" — le due modalità viste in
[classi.md](classi.md)).

Pannello sinistro — *Previsione per materia*, una riga per materia:

| Colonna | Semantica |
|---|---|
| Materia, Disciplina | aggregazione per materia |
| Piani di studi | i piani in cui la materia compare (es. STG solo SCI1, SCI2) |
| Numero alunni | alunni che seguono la materia (0 senza alunni inseriti) |
| Classi: Ore / Nr | ore per classe e numero classi coinvolte |
| Bisogni | **il fabbisogno ore calcolato** — `0h00` finché non si esegue un allineamento |

In basso: **Totale dei bisogni** e tre pulsanti:

- **"Allinea le ore a classe intera"** — genera i bisogni assumendo la classe
  intera (ore × numero classi);
- **"Allinea le ore a numero di alunni ridotto"** — genera i bisogni sul modello a
  effettivo ridotto (richiede alunni/gruppi);
- **"Cancella l'allineamento"**.

Pannello destro — *Servizi previsionali associati ai bisogni selezionati*: i
servizi della materia selezionata, raggruppati come "Materie comuni ad almeno due
classi previsionali", con il totale ore (es. DIS: `2h00` × 10 classi = `20h00`).

Le righe materia sono **espandibili** (▶) in sotto-righe, una per **variante di
durata** (es. Matematica: `5h00` sulle classi del biennio, `4h00` sul triennio).
L'allineamento a classe intera fallisce sulla riga-materia se le durate
differiscono: va eseguito sulle **sotto-righe** — la granularità del bisogno è
(materia × durata), cioè la riga di servizio, non la materia intera.

L'allineamento **da solo non produce il bisogno**: con 0 alunni la colonna resta
`0h00` (l'avvenuto allineamento è indicato da una graffetta sulla sotto-riga e
dall'attivazione di "Cancella l'allineamento"). Il bisogno si materializza solo
dopo aver inserito gli **effettivi previsti** nella matrice "Ripartizione del
numero di alunni dei piani di studi per classe" ([classi.md](classi.md)): EDT
ricava da lì le classi necessarie (alunni ÷ `Al./Cl.`) e calcola
`bisogno = ore × classi necessarie`.

Con 26 alunni previsti su ognuna delle 10 classi, il **Totale dei bisogni dà
288h00** ✅ — la quadratura del dataset Fermi calcolata da EDT (2026-07-09).

Nella matrice di ripartizione il totale del piano appare in **rosso** se gli
alunni *reali* del piano (l'"Alunni inseriti" anagrafico, 0 per noi) non
coincidono con i distribuiti: è un warning anagrafica ↔ previsione, irrilevante
finché si lavora solo in previsionale.

## Semantica dedotta

- Il **bisogno** è derivato, non inserito: `ore per classe × classi` (allineamento
  a classe intera) oppure una funzione degli alunni (allineamento a effettivo
  ridotto). L'**allineamento** è l'operazione che materializza il fabbisogno.
- Con l'intero istituto allineato a classe intera, il **Totale dei bisogni** deve
  coincidere con il monte ore-classe: per il Fermi **288h00** — la quadratura di
  [`data/liceo-fermi/classi.md`](../../data/liceo-fermi/classi.md) calcolata da EDT.

## Implicazioni per il nostro modello

- Il fabbisogno per materia è un **report derivato** (stessa famiglia dei campi
  previsionali del docente, [ADR-007](../decisioni.md)): non si memorizza, si
  calcola da piani × classi.
- Il confronto bisogni ↔ monte ore docenti per disciplina è il check di
  **fattibilità pre-solver** (abbastanza docenti per coprire il fabbisogno?).

## Aperto / da osservare

- Cosa fa esattamente l'allineamento a **numero di alunni ridotto** (serve per
  gruppi/sdoppiamenti? → [gruppi.md](gruppi.md)).
- Cosa mostra la **TRCD** (probabile confronto bisogni ↔ risorse docenti per
  disciplina).
