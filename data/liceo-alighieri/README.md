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

## Stato: ondate 1–5 di 7

1. ✅ **L'anagrafica** — sedi, indirizzi, materie, piani di studi e servizi,
   classi, docenti, aule, attività.
2. ✅ **Gli sdoppiamenti** — partizioni, parti, raggruppamenti trasversali: la
   voce ✅ di scope v1 che nessun dataset rappresentava. Vedi
   [gruppi.md](gruppi.md).
3. ✅ **L'asse Cardinalità** — le otto famiglie di `ResourceTimeConstraint` in
   dieci righe, ognuna scelta **al bordo**. Vedi [vincoli.md](vincoli.md).
4. ✅ **L'asse Relazione** — i tredici tipi di `SubjectConstraint`, uno per
   riga, ognuno provato col **testimone puntato**. Vedi
   [relazioni.md](relazioni.md).
5. ✅ **Risorse, peso e indisponibilità** — le sei righe di indisponibilità nei
   tre livelli, i tetti di peso didattico, il tecnico di laboratorio e i
   carrelli di portatili. 🔑 La sonda arriva al **registro intero**. Vedi
   [risorse.md](risorse.md).

Le famiglie restanti arrivano dalle ondate successive, e ognuna aggiorna
`esiti-attesi.md` *prima* del codice che le esercita.

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
| Partizioni / parti / raggruppamenti | 17 / 34 / 2 |
| Righe di vincolo orario | 10 (8 famiglie) |
| Righe di vincolo di materia | 13 (13 tipi) |
| Righe di indisponibilità | 55 (6 righe logiche, 3 livelli, 3 tipi di risorsa) |
| Personale / materiali | 1 tecnico / 4 carrelli di portatili |
| Peso didattico | 3 materie a 2; tetti 9 / 5 / 12 e uno di classe a 40 |
| **Ore-alunno** | **345** — 27 nei bienni, 30 e 31 nei trienni |
| **Ore erogate** | **362** |
| **Attività** | **342** |

🔑 **Le otto fasce non sono decorazione.** `max_hours` con tetto mattutino
diverso da quello giornaliero, `max_half_days` e le mezze giornate libere non
hanno soggetto su una griglia senza pomeriggio — e il Fermi, a sei fasce, non
ce l'ha.

🔑 **Le due sedi nemmeno.** `structural:site_transition` legge
`Activity.site`; il Fermi ha zero righe `Site`, quindi quel builder non ha mai
visto un dataset. Qui ogni attività ha una sede, e **otto docenti su ventitré**
insegnano in entrambe.

## Quadratura

⚠ **Due totali, e non sono lo stesso numero.** Le **345** ore-alunno sono la
somma dei quadri orari; le **362** erogate sono le ore che qualcuno insegna. Lo
scarto sta tutto negli sdoppiamenti: dodici ore di attività alternativa
affiancate all'IRC, tre di informatica affiancate al latino nella 2C
articolata, e le due ore di laboratorio — 3A e 4A — insegnate **due volte**
ciascuna. Confonderli è il modo in cui un monte ore torna e una cattedra no.

Le 362 ore erogate coincidono per costruzione con tre somme indipendenti, e i
test le verificano tutte e tre
([`tests/test_alighieri_representation.py`](../../tests/test_alighieri_representation.py)):

- la somma dei quadri orari delle 12 classi, con le erogazioni per parte
  (`piani-di-studi.md`, `gruppi.md`);
- la somma dei monte ore delle 23 cattedre (`docenti.md`), ciascuna a `+/- = 0`;
- la somma delle durate delle 342 attività.

⚠ E la verifica è **per (classe, materia)**, non sui totali: è la lezione del
Fermi, dove due materie invertite quadravano lo stesso. Dall'ondata 2 quella
somma grossolana non basta più — dove entrano parti e raggruppamenti l'unità
vera è l'**atomo** (ADR-020), e il predicato che la usa è
`structural:coverage`, verificato sul dataset intero.

## Misure, ondata 5

| | |
|---|---|
| Modello fase 1 | **15 233** variabili, **12 251** constraint (ondata 4: 15 545 / 11 783) |
| Fase 1 | `OPTIMAL`, **zero scarti**, ~7 s |
| Richieste d'aula | 73 |
| Fase 2 | `OPTIMAL`, **73 su 73**, zero rinunce |
| Sonda dei builder | **27 su 27** — il registro intero (ondata 4: 25; ondata 3: 12; ondata 2: 4; Fermi: 3) |

⚠ **Le variabili sono *scese*, ed è la prima volta.** Le indisponibilità sono
un pre-filtro del dominio: 55 righe tolgono celle, e con esse i letterali di
avvio che ci vivevano. I constraint salgono comunque, per i tetti di peso.

⚠ **E i tetti di peso cambiano il regime di ricerca** — stesso modello,
**439 s** con un lavoratore contro **7 s** con otto. È il primo vincolo del
banco a farlo, e ha portato due test delle ondate 3 e 4 da `workers=1` a
`workers=8`. Dettaglio in [risorse.md](risorse.md).

⚠ **L'ondata 2 non aveva allargato la sonda, ed era corretto così.** Partizioni,
parti e raggruppamenti non hanno un builder proprio: entrano nel modello
attraverso le **chiavi di occupazione** (ADR-017), cioè facendo lavorare di più
`structural:occupation` — da 1440 a **3440** constraint — e attraverso
`structural:coverage`, che un builder non ce l'ha per costruzione. Un
cricchetto che contasse i constraint direbbe «cresciuto» senza dire niente di
vero.

L'ondata 3 la allarga invece di **otto** in un colpo e l'ondata 4 di
**tredici**: una riga per famiglia, e ogni riga sceglie il proprio portatore
perché quella famiglia abbia un soggetto vero.

🔑 **E l'ondata 5 la chiude**: le indisponibilità svegliano
`structural:unavailability`, i tetti di peso `structural:didactic_weight`, e
l'insieme diventa il registro intero. Il criterio di accettazione della spec
(ventisette su ventisette) è quindi raggiunto **all'ondata 5** invece che alla
7 — ma non chiude il pezzo: la sonda dice che ogni builder *fa qualcosa*, non
che ciò che fa morda. Da qui in avanti il cricchetto
([`tests/test_alighieri_sonda.py`](../../tests/test_alighieri_sonda.py)) non
deve più salire, deve **restare fermo**.

⚠ E il dataset **non è ancora stretto** nel senso della spec (una sola aula o
un solo docente in meno e compaiono gli scarti). Ma lo è **famiglia per
famiglia**, con due prove diverse perché i due assi vogliono prove diverse:
sulla cardinalità otto righe su nove non sopportano una tacca più stretta
(la nona — il D.T.B. — no, ed è misurato: [vincoli.md](vincoli.md)); sulla
relazione tredici su tredici non sopportano il **testimone puntato**, cioè la
configurazione vietata imposta con `pinned` ([relazioni.md](relazioni.md)); e
l'ondata 5 usa **entrambe** le prove, scegliendo secondo la natura della riga
([risorse.md](risorse.md)).

## Indice del dataset

- [sedi.md](sedi.md) — le due sedi e chi le attraversa
- [materie.md](materie.md) — 16 materie e le loro discipline
- [piani-di-studi.md](piani-di-studi.md) — i 10 piani e i quadri orari
- [classi.md](classi.md) — le 12 classi
- [docenti.md](docenti.md) — le 23 cattedre
- [aule.md](aule.md) — le 20 aule, per sede
- [gruppi.md](gruppi.md) — 🔑 le quattro forme di sdoppiamento, e il debito che hanno trovato
- [vincoli.md](vincoli.md) — 🔑 le dieci righe dell'asse Cardinalità, e perché stanno al bordo
- [relazioni.md](relazioni.md) — 🔑 i tredici tipi dell'asse Relazione, e il testimone puntato
- [risorse.md](risorse.md) — 🔑 indisponibilità, peso didattico, tecnico e carrelli; e i due difetti trovati
- [esiti-attesi.md](esiti-attesi.md) — 🔑 cosa deve succedere, scritto prima di eseguire

Per la **semantica** delle entità (non i dati) vedi [`docs/edt/`](../../docs/edt/).
