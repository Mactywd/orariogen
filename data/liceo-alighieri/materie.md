# Materie e discipline

14 materie su 8 discipline. La disciplina è una tabella e non un enum
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

## Le due materie che il Fermi non ha

- **GRE** e **STA** esistono perché il secondo indirizzo esiste: sono la prova
  che due piani di studi divergono davvero, e non sono lo stesso quadro orario
  con un totale diverso.
- **A013** e **A054** accanto ad A011 e A017 nella stessa disciplina: una
  disciplina che mappa a **più** classi di concorso è il caso che la normativa
  sulle sostituzioni richiede, e il Fermi lo esercita su due discipline soltanto.

⚠ `max_reduced_students` (`Al./Rid.`) resta `NULL` su tutte le materie:
**eredita** dal default d'istituto (15), che è la cascata dichiarata di
[ADR-003](../../docs/decisioni.md). Diventerà un dato quando l'ondata 2
introdurrà lo sdoppiamento a effettivo ridotto.

⚠ `didactic_weight` resta al default **1** su tutte: i tetti di peso didattico
sono `None` in `InstituteSettings`, come in EDT dove i quattro tetti d'istituto
sono a `nessuno`. Li accende l'ondata 5.
