# Materie e discipline

16 materie su 10 discipline. La disciplina è una tabella e non un enum
([ADR-001](../../docs/decisioni.md)), e porta la mappatura alle classi di
concorso ([ADR-002](../../docs/decisioni.md)), che è **nostra estensione** e
non un campo EDT.

| Disciplina | Classi di concorso | Materie |
|---|---|---|
| LET Lettere | A011, A013 | ITA Italiano, LAT Latino, GRE Greco, STG Storia e Geografia |
| STF Storia e Filosofia | A019 | STO Storia, FIL Filosofia |
| LIN Lingue straniere | AB24 | ING Inglese |
| MAF Matematica e Fisica | A026, A027 | MAT Matematica, FIS Fisica |
| SCN Scienze | A050 | SCI Scienze naturali |
| ART Discipline artistiche | A017, A054 | DIS Disegno e Storia dell'Arte, STA Storia dell'Arte |
| MOT Scienze motorie | A048 | MOT Scienze motorie |
| REL Religione | IRC | IRC Religione cattolica |
| INF Informatica | A041 | INF Informatica |
| ALV Attività alternativa | **nessuna** | ALT Attività alternativa |

⚠ **`ALV` senza classi di concorso non è una dimenticanza**: l'attività
alternativa all'IRC non ne ha una propria — la copre chi ha ore disponibili. È
anche l'unico caso del dataset in cui la M2M resta vuota, ed è giusto che ce ne
sia uno.

## Le due materie che il Fermi non ha

- **GRE** e **STA** esistono perché il secondo indirizzo esiste: sono la prova
  che due piani di studi divergono davvero, e non sono lo stesso quadro orario
  con un totale diverso.
- **A013** e **A054** accanto ad A011 e A017 nella stessa disciplina: una
  disciplina che mappa a **più** classi di concorso è il caso che la normativa
  sulle sostituzioni richiede, e il Fermi lo esercita su due discipline soltanto.

⚠ `max_reduced_students` (`Al./Rid.`) resta `NULL` su tutte le materie, e
**dopo l'ondata 2 è una scelta e non un rinvio**: lo sdoppiamento di 3A c'è, i
due gruppi da 13 stanno sotto il tetto, e il tetto che vale è quello
d'istituto (15) — cioè la cascata di [ADR-003](../../docs/decisioni.md)
esercitata invece che dichiarata. Materializzarlo sulla materia toglierebbe
l'unico posto del dataset in cui l'ereditarietà si vede lavorare.

## Il peso didattico (ondata 5)

⚠ Fino all'ondata 4 `didactic_weight` restava al default **1** su tutte, e i
quattro tetti d'istituto erano `None` — come in EDT, dove sono a `nessuno`, e
come sul Fermi, che resta così. È per questo che `structural:didactic_weight`
non aveva mai visto un dato.

L'ondata 5 dichiara una politica di scuola: **MAT, LAT e GRE pesano 2**, cioè
le materie d'indirizzo dei due corsi. Tutte le altre restano a 1, e i tetti
sono in [risorse.md](risorse.md).

## L'ora quindicinale (ondata 6)

⚠ **SCI nel 5B vale 2 ore, e le attività sono tre.** La seconda ora è a
settimane alterne — laboratorio e teoria — quindi il piano dice 2, ogni
settimana ne eroga 2, e la somma cruda delle durate direbbe 3. È il falso
scostamento che `CoverageChecker` dichiara per esteso (*«una coppia Q1/Q2
della stessa materia darebbe 120 minuti contro i 60 del piano»*), e nel banco
è ora un dato invece che un esempio nel docstring. Vedi
[quindicinale-e-quote.md](quindicinale-e-quote.md).

🔑 E il peso si conta **per unità-studente**, non per classe
([ADR-011](../../docs/decisioni.md)): con le partizioni dell'ondata 2, una
classe non ha *un* peso settimanale, ne ha uno per parte. Il tetto di classe
del 3B (40) è il peso di 3B_REL e di 3B_ALT, non quello del 3B.
