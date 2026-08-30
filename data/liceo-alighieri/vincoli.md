# I vincoli — l'asse Cardinalità (ondata 3)

Le otto famiglie di `ResourceTimeConstraint`, in **dieci righe**. La tabella è
la parte del banco che paga l'intero pezzo: prima di questa ondata il dataset
esercitava quattro builder su ventisette, e ventiquattro famiglie del motore
non avevano mai visto una riga di dato.

> 🔑 **Un vincolo che nessuno può violare non è un vincolo, è una riga.** Il
> pericolo di un banco non è dimenticare una famiglia — quello lo prende la
> [sonda](../../tests/sonda.py) — è metterci una riga così larga che l'orario
> la soddisfa da solo. Perciò ogni riga qui è scelta **al bordo**: una tacca
> più stretta e il dataset diventa `INFEASIBLE`. Dove non è così, è scritto.

## Le dieci righe

| Famiglia | Portatore | Riga | Cosa deve produrre |
|---|---|---|---|
| `min_distribution` | N02 Urbani (10 h) | `min_days 4`, `min_minutes_per_day 120` | le dieci ore di scienze del classico su almeno quattro giornate da due |
| `max_hours` | M03 Rinaldi (21 h) | `day_minutes 300`, `morning_minutes 180` | tetto mattutino **sotto** quello giornaliero ⇒ almeno **6 ore di pomeriggio** |
| `max_presence` | L06 Gentili (12 h) | `days 3`, `max_minutes 300` | il tempo parziale: **due giornate intere vuote**, presenza ≤ 5 fasce |
| `arrival_departure` | A01 Vitali (20 h) | `days 5`, `not_before_slot 1` | **la prima fascia libera tutti i giorni** |
| `free_guaranteed` | P01 Zanetti (12 h) | `free_days 2`, `free_half_days 2` | due giornate libere **scelte dal solver**, più due mezze giornate |
| `max_half_days` (`MMG`) | classe **2A** | `max_half_days 7` | 28 fasce in sette mezze giornate ⇒ **due pomeriggi, non tre** |
| `max_half_days` (`MG`) | R02 Donati (12 h) | `only_half_day_per_day` | mai mattina **e** pomeriggio nello stesso giorno |
| `max_presence` | R01 Colombo (12 h) | `days 2`, `max_minutes 480` | il **cappellano viene due giorni** — vedi sotto |
| `max_site_changes` | R01 Colombo | `per_day 1`, `per_week 1` | al più **un** cambio di sede, in tutta la settimana |
| `max_gap_hours` (`D.T.B.`) | L03 Cavalli (21 h) | `max_gap_minutes 60` | al più **un'ora di buco** in tutta la settimana |

Otto famiglie e dieci righe perché due famiglie ne portano due:
`max_half_days` è **una sola riga in EDT con due caselle** (il tetto di mezze
giornate e «lavorare solo mezza giornata al giorno»), e le due caselle vogliono
portatori diversi — un tetto ha senso su una classe, la seconda casella su un
docente sparso; `max_presence` ne ha due perché la seconda non è lì per sé.

## 🔑 Il cappellano, e perché due righe su R01

`max_site_changes` è l'unica famiglia che non ha un soggetto naturale: R01
insegna religione in tutte e dodici le classi, quindi in **entrambe** le sedi,
ma con cinque giornate a disposizione può dedicarne una intera alla succursale
e non spostarsi mai. Misurato: `per_day 0, per_week 0` su R01 senza altre
righe è `OPTIMAL`. Il vincolo c'era, e non vincolava niente.

La riga `max_presence days 2` è ciò che gli dà un soggetto, e **non è un
espediente**: è il caso vero delle scuole con una sede staccata — l'insegnante
di religione che viene due giorni e copre dodici classi. Con due sole giornate
le dieci ore della centrale non stanno in una, quindi la succursale deve
condividere una giornata con la centrale: il cambio di sede diventa
**inevitabile**, e limitarlo a uno diventa una scelta invece di una formalità.

⚠ Va dichiarato perché è esattamente il passo che un banco disonesto non fa: la
strada facile sarebbe stata lasciare la riga larga e scrivere «famiglia
coperta».

## ⚠ Il D.T.B. non è al bordo, ed è misurato

Nove righe su dieci stanno sul bordo del risolvibile. La decima no, e non si
finge il contrario: non solo `max_gap_minutes = 0` su L03 resta `OPTIMAL`, ma
lo resta **zero buchi per ogni docente e per ogni classe insieme**.

La ragione è strutturale e si conta: 40 fasce a settimana contro cattedre da
10–21 ore e classi da 28–32 fasce. La contiguità dentro una mezza giornata è
gratis. Per stringere il D.T.B. serve una griglia più densa o un carico più
alto — cioè il criterio di accettazione dell'ondata 7 (spec §4, «stretto ma
risolvibile»), non una taratura di questa riga.

Il fatto è tenuto fermo da un test che asserisce **l'`OPTIMAL`**
(`test_il_dtb_non_e_al_bordo_ed_e_una_misura`): diventerà rosso il giorno in
cui il banco si stringe, che è quando vogliamo saperlo.

## Le tacche più strette

Ogni riga qui rende il dataset `INFEASIBLE`, e ognuna è un argomento di
**conteggio** — non una taratura trovata provando.

| Famiglia | Tacca | Perché non ci sta |
|---|---|---|
| `min_distribution` | `min_days 5`, `min_minutes_per_day 180` | 5 × 3 h = 15 > 10 |
| `max_hours` | `day_minutes 240` | 5 × 4 h = 20 < 21 |
| `max_presence` | `days 1` | 12 h in una giornata da 8 fasce |
| `arrival_departure` | `not_before_slot 5` | 5 × 3 fasce = 15 < 20 |
| `free_guaranteed` | `free_days 4` | 12 h in una giornata da 8 fasce |
| `max_half_days` | `max_half_days 5` | 5 mattine = 25 < 28 |
| `only_half_day` | la stessa casella sulla 2A | idem: 28 fasce non stanno in cinque mezze giornate |
| `max_site_changes` | `per_day 0` | con due giornate sole la succursale deve condividerne una |

## ⚠ La mutazione per rimozione, provata e scartata

La spec (§6.4) chiede: *togliere la riga di una famiglia deve cambiare
l'orario*. È stata implementata e misurata, e **non regge come test** — vale la
pena scriverlo, perché la tentazione di scriverlo lo stesso è forte.

Il modello di fase 1 non ha una funzione di costo sopra lo scarto: ogni orario
a zero scarti è *ottimo*, e il solver ne restituisce **uno arbitrario** fra
milioni. Se l'orario che torna dopo la rimozione viola la riga tolta, quello è
un fatto sulla **ricerca**, non sulla riga. La misura: cambiando una sola riga
*estranea* alla famiglia osservata, il verdetto si è ribaltato per **tre
famiglie su nove**; e su una stessa configurazione, `workers=8` dava «viola» e
«non viola» a esecuzioni diverse.

Congelarlo in un test fisserebbe un artefatto della ricerca — lo stesso errore
che il tie-break di `_placed_of` ha insegnato a non fare. La direzione dello
**stringimento** non ha il difetto: `INFEASIBLE` è una proprietà del modello,
dimostrata dal solver, non del testimone che torna. È più forte, non più
debole: una riga che non può essere stretta di una tacca non può nemmeno
essere soddisfatta per caso.

## Quello che l'ondata 3 ha spostato

| | Ondata 2 | Ondata 3 |
|---|---:|---:|
| Righe `ResourceTimeConstraint` | 0 | **10** |
| Builder attivi (sonda) | 4 su 27 | **12 su 27** |
| Variabili, fase 1 | 14 372 | 15 372 |
| Constraint, fase 1 | 7 704 | 8 758 |
| Fase 1 | `OPTIMAL`, 0 scarti | `OPTIMAL`, 0 scarti |
| Fase 2 | 71 su 71 | 71 su 71 |
