# Dataset — Liceo "Dante Alighieri"

> ⚠ **Questo non è una scuola osservata: è un banco.**
>
> Il [Fermi](../liceo-fermi/README.md) è la trascrizione di una scuola
> realmente inserita nella UI di EDT, campo per campo, durante il reverse
> engineering: le sue righe sono **osservazioni**, e per questo non si toccano
> mai per far passare un test. Le righe dell'Alighieri sono **costruzioni
> nostre**, scelte per far scattare un checker, e si modificano quando una
> famiglia nuova entra nel registro.
>
> La convenzione della casa — *ciò che è nostra estensione va segnalato come
> tale, non spacciato per campo EDT* — vale anche per i dataset.

|  | Fermi | Alighieri |
|---|---|---|
| Origine | osservazione in EDT | costruzione nostra |
| Domanda | «lo schema regge una scuola vera?» | «il motore regge tutte le famiglie insieme, a scala vera?» |
| Si modifica | mai per far passare un test | quando una famiglia entra nel registro |
| Se fallisce | lo schema è sbagliato | il motore è sbagliato |

Il perché sta nella spec
[2026-08-30-alighieri-banco-a-scuola-intera-design.md](../../docs/superpowers/specs/2026-08-30-alighieri-banco-a-scuola-intera-design.md).
In breve: il Fermi esercita **tre builder su ventisette** — misurato, non
stimato — e lascia tredici tabelle su trentatré vuote, `ClassPartition`,
`ClassPart` e `Group` comprese, cioè voci ✅ dello scope v1 che nessun dataset
rappresenta.

## Stato: ondata 1 di 7 — l'anagrafica

Fatto: sedi, indirizzi, materie, piani di studi e servizi, classi, docenti,
aule, attività. **Nessuna riga di vincolo**: arrivano dalle ondate successive,
e ognuna aggiorna `esiti-attesi.md` *prima* del codice che le esercita.

## Parametri

| Parametro | Valore |
|---|---|
| Indirizzi | 2 — Scientifico, Classico |
| Sezioni | 3 — A (scientifico), B (classico), C (biennio scientifico in succursale) |
| Classi | 12 — 1A–5A, 1B–5B, 1C–2C |
| Sedi | 2 — Centrale, Succursale (spostamento: 1 fascia) |
| Docenti | 21 |
| Materie | 14 |
| Aule | 20 |
| Piani di studi | 10 (2 indirizzi × 5 anni) |
| Giorni | lunedì – venerdì |
| Fasce | 8 — mattina 08:00–13:00 (5), mensa, pomeriggio 14:00–17:00 (3) |
| Monte ore | 27 h/sett. nei due bienni; 30 h allo scientifico e 31 h al classico nei trienni |
| **Ore-classe totali** | **345** |
| **Attività** | **323** |

🔑 **Le otto fasce non sono decorazione.** `max_hours` con tetto mattutino
diverso da quello giornaliero, `max_half_days` e le mezze giornate libere non
hanno soggetto su una griglia senza pomeriggio — e il Fermi, a sei fasce, non
ce l'ha.

🔑 **Le due sedi nemmeno.** `structural:site_transition` legge
`Activity.site`; il Fermi ha zero righe `Site`, quindi quel builder non ha mai
visto un dataset. Qui ogni attività ha una sede, e sei docenti su ventuno
insegnano in entrambe.

## Quadratura

Le 345 ore-classe coincidono per costruzione con tre somme indipendenti, e i
test le verificano tutte e tre
([`tests/test_alighieri_representation.py`](../../tests/test_alighieri_representation.py)):

- la somma dei quadri orari delle 12 classi (`piani-di-studi.md`);
- la somma dei monte ore delle 21 cattedre (`docenti.md`), ciascuna a `+/- = 0`;
- la somma delle durate delle 323 attività.

⚠ E la terza verifica è **per (classe, materia)**, non sui totali: è la lezione
del Fermi, dove due materie invertite quadravano lo stesso.

## Misure dell'ondata 1

| | |
|---|---|
| Modello fase 1 | 13 583 variabili, 5 493 constraint, 0,7 s di costruzione |
| Fase 1 | `OPTIMAL`, **zero scarti**, ~2,5 s a 8 lavoratori |
| Richieste d'aula | 66 |
| Fase 2 | `OPTIMAL`, **66 su 66**, zero rinunce, ~0,2 s |
| Sonda dei builder | **4 su 27** (Fermi: 3) |

⚠ **Quattro su ventisette non è un risultato, è un punto di partenza.** Il
criterio di accettazione della spec è ventisette su ventisette all'ondata 7, e
il cricchetto che ci arriva è
[`tests/test_alighieri_sonda.py`](../../tests/test_alighieri_sonda.py): ogni
ondata deve allargare l'insieme dichiarato lì.

⚠ E il dataset **non è ancora stretto**. La spec chiede che una sola aula o un
solo docente in meno faccia comparire gli scarti; senza una riga di vincolo la
tensione non c'è ancora. È il lavoro delle ondate 3–6.

## Indice del dataset

- [sedi.md](sedi.md) — le due sedi e chi le attraversa
- [materie.md](materie.md) — 14 materie e le loro discipline
- [piani-di-studi.md](piani-di-studi.md) — i 10 piani e i quadri orari
- [classi.md](classi.md) — le 12 classi
- [docenti.md](docenti.md) — le 21 cattedre
- [aule.md](aule.md) — le 20 aule, per sede
- [esiti-attesi.md](esiti-attesi.md) — 🔑 cosa deve succedere, scritto prima di eseguire

Per la **semantica** delle entità (non i dati) vedi [`docs/edt/`](../../docs/edt/).
