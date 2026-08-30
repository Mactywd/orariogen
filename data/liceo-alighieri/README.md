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

## Stato: ondate 1–2 di 7

1. ✅ **L'anagrafica** — sedi, indirizzi, materie, piani di studi e servizi,
   classi, docenti, aule, attività.
2. ✅ **Gli sdoppiamenti** — partizioni, parti, raggruppamenti trasversali: la
   voce ✅ di scope v1 che nessun dataset rappresentava. Vedi
   [gruppi.md](gruppi.md).

**Nessuna riga di vincolo**: arrivano dalle ondate successive, e ognuna
aggiorna `esiti-attesi.md` *prima* del codice che le esercita.

## Parametri

| Parametro | Valore |
|---|---|
| Indirizzi | 2 — Scientifico, Classico (+ Scienze Applicate nella 2C articolata) |
| Sezioni | 3 — A (scientifico), B (classico), C (biennio scientifico in succursale) |
| Classi | 12 — 1A–5A, 1B–5B, 1C–2C |
| Sedi | 2 — Centrale, Succursale (spostamento: 1 fascia) |
| Docenti | 23 |
| Materie | 16 |
| Aule | 20 |
| Piani di studi | 11 (2 indirizzi × 5 anni, più `SAP2`) |
| Giorni | lunedì – venerdì |
| Fasce | 8 — mattina 08:00–13:00 (5), mensa, pomeriggio 14:00–17:00 (3) |
| Monte ore | 27 h/sett. nei due bienni; 30 h allo scientifico e 31 h al classico nei trienni |
| Partizioni / parti / raggruppamenti | 16 / 32 / 2 |
| **Ore-alunno** | **345** — 27 nei bienni, 30 e 31 nei trienni |
| **Ore erogate** | **361** |
| **Attività** | **340** |

🔑 **Le otto fasce non sono decorazione.** `max_hours` con tetto mattutino
diverso da quello giornaliero, `max_half_days` e le mezze giornate libere non
hanno soggetto su una griglia senza pomeriggio — e il Fermi, a sei fasce, non
ce l'ha.

🔑 **Le due sedi nemmeno.** `structural:site_transition` legge
`Activity.site`; il Fermi ha zero righe `Site`, quindi quel builder non ha mai
visto un dataset. Qui ogni attività ha una sede, e sei docenti su ventuno
insegnano in entrambe.

## Quadratura

⚠ **Due totali, e non sono lo stesso numero.** Le **345** ore-alunno sono la
somma dei quadri orari; le **361** erogate sono le ore che qualcuno insegna. Lo
scarto sta tutto negli sdoppiamenti: dodici ore di attività alternativa
affiancate all'IRC, tre di informatica affiancate al latino nella 2C
articolata, e l'ora di laboratorio di 3A insegnata **due volte**. Confonderli
è il modo in cui un monte ore torna e una cattedra no.

Le 361 ore erogate coincidono per costruzione con tre somme indipendenti, e i
test le verificano tutte e tre
([`tests/test_alighieri_representation.py`](../../tests/test_alighieri_representation.py)):

- la somma dei quadri orari delle 12 classi, con le erogazioni per parte
  (`piani-di-studi.md`, `gruppi.md`);
- la somma dei monte ore delle 23 cattedre (`docenti.md`), ciascuna a `+/- = 0`;
- la somma delle durate delle 340 attività.

⚠ E la verifica è **per (classe, materia)**, non sui totali: è la lezione del
Fermi, dove due materie invertite quadravano lo stesso. Dall'ondata 2 quella
somma grossolana non basta più — dove entrano parti e raggruppamenti l'unità
vera è l'**atomo** (ADR-020), e il predicato che la usa è
`structural:coverage`, verificato sul dataset intero.

## Misure dell'ondata 1

| | |
|---|---|
| Modello fase 1 | 14 370 variabili, 7 700 constraint |
| Fase 1 | `OPTIMAL`, **zero scarti**, ~3,6 s a 8 lavoratori |
| Richieste d'aula | 71 |
| Fase 2 | `OPTIMAL`, **71 su 71**, zero rinunce, ~0,3 s |
| Sonda dei builder | **4 su 27** (Fermi: 3) |

⚠ **L'ondata 2 non ha allargato la sonda, ed è corretto così.** Partizioni,
parti e raggruppamenti non hanno un builder proprio: entrano nel modello
attraverso le **chiavi di occupazione** (ADR-017), cioè facendo lavorare di più
`structural:occupation` — da 1440 a **3440** constraint — e attraverso
`structural:coverage`, che un builder non ce l'ha per costruzione. Un
cricchetto che contasse i constraint direbbe «cresciuto» senza dire niente di
vero.

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
- [materie.md](materie.md) — 16 materie e le loro discipline
- [piani-di-studi.md](piani-di-studi.md) — i 10 piani e i quadri orari
- [classi.md](classi.md) — le 12 classi
- [docenti.md](docenti.md) — le 23 cattedre
- [aule.md](aule.md) — le 20 aule, per sede
- [gruppi.md](gruppi.md) — 🔑 le quattro forme di sdoppiamento, e il debito che hanno trovato
- [esiti-attesi.md](esiti-attesi.md) — 🔑 cosa deve succedere, scritto prima di eseguire

Per la **semantica** delle entità (non i dati) vedi [`docs/edt/`](../../docs/edt/).
