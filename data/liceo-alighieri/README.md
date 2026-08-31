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

## Stato: **completo** — sette ondate su sette

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
6. ✅ **Quote, qualità e firme di settimana** — l'ora quindicinale del 5B (la
   seconda firma, e la quinta forma di erogazione), le due forme di
   alleggerimento e la gerarchia completa dei criteri di qualità. 🔑 E il
   difetto **L7**, che da sospetto diventa misura — e che il 2026-08-31 è
   stato chiuso. Vedi
   [quindicinale-e-quote.md](quindicinale-e-quote.md).
7. ✅ **I comandi** — la domanda che sta a valle di tutte le altre: i cinque
   comandi diagnostici hanno qualcosa di vero da dire su questa scuola? Vedi
   [comandi.md](comandi.md).

Ogni ondata ha aggiornato `esiti-attesi.md` *prima* del codice che la
esercita, e l'ondata 7 non fa eccezione.

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
| Quote di alleggerimento | 2 — una deroga e un margine |
| Criteri di qualità | 6 (5 generi, 2 popolazioni) — ⚠ non installati da `build()` |
| Firme di settimana | **2** — 17 settimane pari, 16 dispari |
| Personale / materiali | 1 tecnico / 4 carrelli di portatili |
| Peso didattico | 3 materie a 2; tetti 9 / 5 / 12 e uno di classe a 40 |
| **Ore-alunno** | **345** — 27 nei bienni, 30 e 31 nei trienni |
| **Ore erogate** | **362** — *in ogni settimana* |
| **Attività** | **343** |

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
- la somma delle durate delle attività **attive in quella settimana**.

⚠ E quest'ultima riga è cambiata all'ondata 6: le attività sono **343** per
362 ore, e non è una contraddizione. L'ora quindicinale del 5B è scritta come
due attività di cui ogni settimana ne vede una; sommare le durate ignorando la
maschera darebbe 363, cioè il falso scostamento che `CoverageChecker` dichiara
per esteso — *«una coppia Q1/Q2 della stessa materia darebbe 120 minuti contro
i 60 del piano»*. Si somma per settimana, e si pretende che tutte e trentatré
diano lo stesso numero.

⚠ E la verifica è **per (classe, materia)**, non sui totali: è la lezione del
Fermi, dove due materie invertite quadravano lo stesso. Dall'ondata 2 quella
somma grossolana non basta più — dove entrano parti e raggruppamenti l'unità
vera è l'**atomo** (ADR-020), e il predicato che la usa è
`structural:coverage`, verificato sul dataset intero.

## Misure, ondata 6

| | |
|---|---|
| Modello fase 1 | **15 330** variabili, **13 817** constraint (ondata 5: 15 233 / 12 251) |
| Fase 1 | `OPTIMAL`, **zero scarti**, ~9 s |
| Richieste d'aula | 73, invariate |
| Fase 2 | `OPTIMAL`, **73 su 73**, zero rinunce |
| Sonda dei builder | **27 su 27**, **ferma** — il cricchetto non deve più salire |

⚠ **Dopo la chiusura dei cinque difetti** (2026-08-31) il modello è **14 785
variabili e 13 996 constraint**: l'allineamento ne aggiunge (i gruppi si
vincolano) e il vincolo di sede ne toglie (i letterali `site_occupied` di
`SiteTransitionBuilder` lasciano il posto a somme di celle). Fase 1 `OPTIMAL`
a zero scarti in ~8 s, fase 2 ancora 73 su 73, e la sonda sale a **28 su 28**
col ventottesimo builder.
| Con i sei criteri di qualità | `solve` da 9 a **82 s** |
| Il primo livello della catena, prima e dopo la costruzione pigra dei criteri (O5) | **9,2 s → 2,6 s** |

🔑 **Una seconda firma di settimana non raddoppia il modello.** L'attesa
diceva «circa il doppio, il vocabolario è per firma», ed era sbagliata: le
variabili derivate nascono solo dove un builder posta qualcosa e
`OccupationBuilder` deduplica i constraint identici fra firme, quindi la
seconda firma costa **quanto le attività che la distinguono** — +86 variabili
e +1562 constraint, cioè +0,6 % e +12,7 %. Le due quote ne costano 11 e 4.
Dettaglio in [quindicinale-e-quote.md](quindicinale-e-quote.md).

⚠ **All'ondata 5 le variabili erano *scese*, ed è stata la prima volta.** Le
indisponibilità sono un pre-filtro del dominio: 55 righe tolgono celle, e con
esse i letterali di avvio che ci vivevano. I constraint salivano comunque, per
i tetti di peso.

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

✅ **E dall'ondata 7 il dataset è stretto anche nel senso della spec**: una
sola aula o un solo docente in meno e compaiono gli scarti — misurato,
[comandi.md §7](comandi.md). ⚠ Ma «stretto» ha **due nozioni**, e la spec ne
dichiarava una sola: quella è stretta rispetto alle **risorse**, mentre la
contiguità che il D.T.B. chiede è stretta rispetto alla **densità della
griglia** e resta gratis. Il banco lo è **anche famiglia per famiglia**, con due prove diverse perché i due assi vogliono prove diverse:
sulla cardinalità otto righe su nove non sopportano una tacca più stretta
(la nona — il D.T.B. — no, ed è misurato: [vincoli.md](vincoli.md)); sulla
relazione tredici su tredici non sopportano il **testimone puntato**, cioè la
configurazione vietata imposta con `pinned` ([relazioni.md](relazioni.md)); e
l'ondata 5 usa **entrambe** le prove, scegliendo secondo la natura della riga
([risorse.md](risorse.md)). L'ondata 6 ne aggiunge una terza forma, per gli
alleggerimenti: si mette il dataset **in tensione** e si pretende che la quota
lo rimetta in piedi — e che senza la quota non ci stia, e che con una quota
troppo piccola nemmeno ([quindicinale-e-quote.md](quindicinale-e-quote.md)).

## Misure, ondata 7 — i comandi

Nessuna riga nuova nel dataset: l'ondata 7 misura ciò che i comandi sanno dire
su ciò che c'è. Il dettaglio, con le due attese smentite, sta in
[comandi.md](comandi.md).

| Comando | Fermi | Alighieri |
|---|---|---|
| `analyze`, classifica | 3 righe, **1** causale | 63 righe, **15** causali (variante satura) |
| `analyze`, fase 5 | — | **2** insiemi deficienti, uno dentro l'altro, quando si stringe il laboratorio della succursale |
| `extract` | — | tutti e **sei** i rilevatori con almeno un'attività |
| `place_and_fix` | **1** attività spostata | **3**, e almeno due per costruzione |
| `solve --popolazione` | — | il tetto morde **solo in tensione**: 0 e 60 `INFEASIBLE`, 180 `FEASIBLE` |
| `assign_rooms` | 8 rinunce senza ADR-021 | `INFEASIBLE` col gruppo di aule, rinuncia senza |
| §4, «stretto ma risolvibile» | — | ✅ **verificato**: `LAB-SUCC` spento costa 14 scarti — le sue undici ore più le tre allineate |

Sedici test in
[`tests/test_alighieri_comandi.py`](../../tests/test_alighieri_comandi.py), e
la suite passa da 930 a **946 verdi** (**953** dopo la chiusura dei cinque
difetti).

🔑 **E misurando il bordo l'ondata ha trovato il quinto difetto del banco,
`L8`**: spegnendo la palestra il modello rispondeva `INFEASIBLE` invece di
scartare, per una sola riga — `free_guaranteed` conta le mezze giornate libere
**solo sui giorni lavorati**, e con un giorno solo il massimo è uno. Una
famiglia così poteva diventare insoddisfacibile *perché si lavora meno*, e lì
lo scarto non era una via d'uscita.

## 🔑 I cinque difetti sono chiusi (2026-08-31)

Il banco ha prodotto cinque difetti e nessuno l'ha riparato, perché la spec
(§8) vietava di modificare il motore mentre lo si misurava. Sono stati
riparati dopo, tutti insieme, e ogni test che ne fissava il comportamento
sbagliato è stato **capovolto**: L5 (l'allineamento genera l'attività
complessa, ventottesimo builder), L6 (un insieme non viaggia: il vincolo di
sede è un tetto di capienza), L6bis (il giallo lo conta anche la fase 1), L7
(i criteri di qualità contano per firma, e il livello è la settimana
peggiore), L8 (la soglia delle mezze giornate libere è quella raggiungibile).

⚠ **E uno di essi ha corretto il dataset in quattro punti, non solo il
motore.** Leggere l'allineamento ha reso visibile che il banco ne dichiarava
di impossibili (le due metà di uno sdoppiamento, che hanno lo stesso docente)
e ne fondeva tre in uno (un ident per coppia di servizi invece che per
attività complessa); che l'articolata parallela, lo spezzone di RICCI
concentrato in un pomeriggio e il tetto di peso d'indirizzo erano insieme
incompatibili; e che il `MG` sull'insegnante di alternativa aveva perso il
**soggetto**, perché il suo orario è ora quello del cappellano. Vedi
[gruppi.md](gruppi.md) e
[quindicinale-e-quote.md](quindicinale-e-quote.md).

⚠ **Due attese smentite, e sono di natura diversa.** La classifica dei vincoli
a riposo dà tre causali e non cinque, e la sbagliata era **l'attesa**: su un
orario dove niente è congelato le famiglie relazionali non hanno soggetto, e
la classifica va misurata dove serve, cioè su un orario quasi fatto. Il tetto
di non-regressione invece non morde affatto, e lì la sbagliata era il
**dataset**: quaranta fasce per ventinove ore lasciano a docenti e classi
abbastanza spazio da non competere.

## Indice del dataset

- [sedi.md](sedi.md) — le due sedi e chi le attraversa
- [materie.md](materie.md) — 16 materie e le loro discipline
- [piani-di-studi.md](piani-di-studi.md) — i 10 piani e i quadri orari
- [classi.md](classi.md) — le 12 classi
- [docenti.md](docenti.md) — le 23 cattedre
- [aule.md](aule.md) — le 20 aule, per sede
- [gruppi.md](gruppi.md) — 🔑 le quattro forme di sdoppiamento, e l'allineamento (L5) con le tre dichiarazioni false che ha corretto nel dato
- [vincoli.md](vincoli.md) — 🔑 le dieci righe dell'asse Cardinalità, e perché stanno al bordo
- [relazioni.md](relazioni.md) — 🔑 i tredici tipi dell'asse Relazione, e il testimone puntato
- [risorse.md](risorse.md) — 🔑 indisponibilità, peso didattico, tecnico e carrelli; e i due difetti trovati, L6 e L6bis, con le misure di prima e di dopo
- [quindicinale-e-quote.md](quindicinale-e-quote.md) — 🔑 l'ora quindicinale, le due forme di alleggerimento, la gerarchia della qualità e L7, con l'aggregazione scelta fra tre
- [comandi.md](comandi.md) — 🔑 cosa i cinque comandi sanno dire su questo banco, e le due attese smentite
- [esiti-attesi.md](esiti-attesi.md) — 🔑 cosa deve succedere, scritto prima di eseguire

Per la **semantica** delle entità (non i dati) vedi [`docs/edt/`](../../docs/edt/).
