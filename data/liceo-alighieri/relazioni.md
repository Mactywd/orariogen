# I vincoli — l'asse Relazione (ondata 4)

I **tredici tipi** di `SubjectConstraint`, in tredici righe. Se l'asse
Cardinalità ([vincoli.md](vincoli.md)) limita *quanto* una risorsa lavora,
questo dice *come le materie stanno fra loro*: mai insieme, mai di seguito,
non più di tante ore per secchio, in quest'ordine, a questa distanza.

> 🔑 **E qui la prova che una riga morde è diversa, perché il vincolo è
> diverso.** All'ondata 3 bastava stringere di una tacca: un tetto su una
> risorsa dal carico fisso si rompe da solo. Un divieto di relazione no — **una
> proibizione non sparpaglia**. Vietare che il greco stia a un giorno di
> distanza da sé stesso non impedisce di metterne tre ore nello stesso giorno,
> e trentanove fasce libere assorbono quasi ogni altro divieto. È misurato, non
> supposto: vedi [«una proibizione non sparpaglia»](#-una-proibizione-non-sparpaglia-e-lattesa-smentita).

## Le tredici righe

| Tipo | Unità | Riga | Cosa vieta |
|---|---|---|---|
| `same_half_day_incompatible` | classe **5A** | MAT ↔ FIS | matematica e fisica nella stessa mezza giornata |
| `same_day_incompatible` | classe **4B** | LAT ↔ GRE | le due lingue del classico nello stesso giorno |
| `two_days_incompatible` | classe **3B** | GRE ↔ GRE | due ore di greco a **un giorno** di distanza |
| `forbidden_sequence` | classe **4A** | MOT → MAT | matematica **subito dopo** le due ore di educazione fisica |
| `max_hours_half_day` | classe **2A** | MAT, 180′ | più di tre ore di matematica in una mezza giornata |
| `max_hours_day` | classe **3B** | ITA, 120′ | più di due ore di italiano in un giorno |
| `weekly_order` | classe **5B** | LAT prima di GRE | che la settimana si apra col greco |
| `imposed_succession` | classe **3A** | FIS ↔ FIS, ritardo 1 | che le due sessioni di fisica si allontanino |
| `half_day_gap` | classe **1B** | LAT ↔ LAT, scarto 2 | due ore di latino a meno di due mezze giornate |
| `parts_before_class` | parte **3A_G1** | SCI | che il primo gruppo faccia laboratorio **dopo** la teoria |
| `parts_after_class` | parte **3A_G2** | SCI | che il secondo lo faccia **prima** |
| `parts_before_or_after_class_h` | classe **3A** | SCI | interlacciatura parte/classe **dentro una mezza giornata** |
| `parts_before_or_after_class_ab` | classe **4A** | SCI | interlacciatura parte/classe **dentro una giornata** |

Un tipo per riga, senza i doppioni che all'ondata 3 servivano: là il portatore
era una **risorsa** e due caselle della stessa riga di EDT volevano soggetti
diversi, qui il portatore è una coppia **(unità, materia)** e ogni tipo ne
riceve una sua.

⚠ **Nessuna riga sta su un raggruppamento**, ed è un fatto del dataset e non
una svista: i due raggruppamenti di inglese portano una materia che a classe
intera non esiste in nessuna delle due classi che attraversano, quindi una
riga su di loro sarebbe vera per vacuità. Il campo è esercitato dalle due
righe su **parte**.

## 🔑 Il testimone puntato, e la mutazione per rimozione che torna misurabile

L'ondata 3 ha scartato la regola 4 della spec — *togli la riga e l'orario deve
cambiare* — dopo averla misurata: senza funzione di costo sopra lo scarto ogni
orario a zero scarti è ottimo, e ciò che torna dopo la rimozione dice **quale
ottimo ha trovato la ricerca**, non se la riga mordeva.

L'ondata 4 la recupera, cambiando una cosa sola: invece di lasciare libero il
solver, si **impone** con `pinned` la configurazione che la riga vieta.

| | con la riga | senza la riga |
|---|---|---|
| esito | `INFEASIBLE` | `OPTIMAL`, zero scarti |
| che cosa afferma | la riga vincola | a vincolare è **lei** |

Le due frasi sono proprietà del **modello**, non del testimone che il solver
sceglie — che è precisamente ciò che alla mutazione per rimozione mancava. E
sono due, non una: la seconda è il controllo che rende la prima informativa.
Senza, un pin illegale per un'altra ragione qualunque — due attività della
stessa classe nella stessa fascia — direbbe `INFEASIBLE` e non proverebbe
niente.

⚠ Il pin va quindi scelto **minimale**: fasce distinte, attività che possono
legittimamente coesistere, e nessuna violazione di un'altra riga. Dove serve,
la scelta è dichiarata riga per riga in `_pin`
([tests/test_alighieri_relazione.py](../../tests/test_alighieri_relazione.py)).

### I tredici testimoni

| Tipo | Configurazione imposta | Con | Senza |
|---|---|---|---|
| `same_half_day_incompatible` | MAT alla 1ª e FIS alla 3ª dello stesso lunedì | `INFEASIBLE` | `OPTIMAL` |
| `same_day_incompatible` | latino e greco lo stesso lunedì | `INFEASIBLE` | `OPTIMAL` |
| `two_days_incompatible` | greco lunedì e martedì | `INFEASIBLE` | `OPTIMAL` |
| `forbidden_sequence` | MOT alle prime due ore, MAT alla terza | `INFEASIBLE` | `OPTIMAL` |
| `max_hours_half_day` | quattro ore di matematica in una mattina | `INFEASIBLE` | `OPTIMAL` |
| `max_hours_day` | tre ore di italiano in un giorno | `INFEASIBLE` | `OPTIMAL` |
| `weekly_order` | il greco alla 1ª ora di lunedì, il latino alla 2ª | `INFEASIBLE` | `OPTIMAL` |
| `imposed_succession` | le due sessioni di fisica lunedì e venerdì | `INFEASIBLE` | `OPTIMAL` |
| `half_day_gap` | due ore di latino nella stessa mattina | `INFEASIBLE` | `OPTIMAL` |
| `parts_before_class` | teoria alla 2ª, laboratorio del G1 alla 4ª | `INFEASIBLE` | `OPTIMAL` |
| `parts_after_class` | laboratorio del G2 alla 2ª, teoria alla 4ª | `INFEASIBLE` | `OPTIMAL` |
| `parts_before_or_after_class_h` | G1, classe, G2 alle prime tre ore | `INFEASIBLE` | `OPTIMAL` |
| `parts_before_or_after_class_ab` | idem in 4A | `INFEASIBLE` | `OPTIMAL` |

**Tredici su tredici, in tutte e due le direzioni** (2026-08-30).

## Le tre tacche che esistono

Dove il tipo ha un parametro, la tacca dell'ondata 3 si applica ancora, e
resta il modo più economico di dire la stessa cosa. Sono **tre su tredici**,
e non è una lacuna: sui divieti puri non c'è un parametro da stringere.

| Tipo | Tacca | Perché è infattibile | Esito |
|---|---|---|---|
| `max_hours_half_day` | 180′ → **60′** | il blocco da due ore di matematica non si spezza: 120′ in una mezza giornata sola | `INFEASIBLE`, 0,7 s |
| `max_hours_day` | 120′ → **60′** | 🔑 quattro ore di italiano a un'ora al giorno vogliono quattro giornate, e **GENTI ne lavora tre** (`max_presence`, ondata 3) | `INFEASIBLE`, 2,6 s |
| `half_day_gap` | 2 → **3** | cinque ore con passo ≥ 3 vogliono un arco di dodici mezze giornate, e la settimana ne ha dieci | `INFEASIBLE`, 2,1 s |

🔑 La seconda è la più interessante delle tre, perché **attraversa i due
assi**: la riga di relazione diventa impossibile per colpa di una riga di
cardinalità scritta un'ondata prima, su una risorsa e non su una materia. È
l'argomento di §1.1 della spec — *una scuola combina i vincoli come li combina
una scuola* — misurato invece che dichiarato.

## ⚠ Una proibizione non sparpaglia, e l'attesa smentita

Il disegno prevedeva una **quarta** tacca: spostare la riga `two_days` dal
greco del 3B (3 ore) al latino (4 ore). L'aritmetica sembrava chiusa —
quattro giornate a due a due non adiacenti non stanno in cinque, perché
l'insieme indipendente massimo di un cammino di cinque nodi è tre.

**Osservato: `OPTIMAL`.** Il conteggio è giusto, la premessa no. *Niente
obbliga quattro ore della stessa materia a stare su quattro giornate
distinte*: il solver le impila, e l'orario esiste.

*Quale delle due era sbagliata*: l'attesa. Ed è la stessa trappola che rende
`same_day_incompatible` fra due materie **sempre** soddisfacibile da solo — A
si concentra in un giorno, B in un altro — cioè il motivo per cui questa
ondata porta il testimone puntato invece della tacca. Un test asserisce
l'`OPTIMAL`, così diventerà rosso il giorno in cui il banco stringerà
abbastanza da forzare lo sparpagliamento: l'ondata 7.

## 🔑 Il secondo laboratorio, e perché il dataset è cresciuto

L'ondata 4 aggiunge una partizione al dataset — `LABSCI` in **4A**, gemella di
quella di 3A — e la ragione è una sola, dichiarata: **i quattro tipi `PARTS_*`
vogliono quattro portatori che non si implichino a vicenda.**

Un ordine *per giornata* su un'unità implica l'omogeneità su ogni sotto-unità
e dentro ogni mezza giornata: `parts_before_class` su una classe rende veri
per costruzione sia `_ab` sulla stessa classe sia `_h` su ogni sua parte. Con
una sola classe sdoppiata, due dei quattro tipi sarebbero stati **presenti e
implicati** — cioè esattamente il difetto che la regola 4 di
[esiti-attesi.md](esiti-attesi.md) esiste per non avere.

Con due classi sdoppiate i quattro portatori si separano, e la forma che ne
esce è anche quella che una scuola scriverebbe: in 3A le due metà **ruotano
attorno all'ora di teoria** — la prima fa laboratorio prima, la seconda dopo —
e sulla classe intera vale la regola più debole, niente interlacciatura dentro
una mezza giornata; in 4A resta solo quest'ultima, per giornata.

È la stessa mossa del [cappellano](vincoli.md#-il-cappellano-e-perché-due-righe-su-r01)
dell'ondata 3: una famiglia senza soggetto ne riceve uno. Il costo è dichiarato
— N01 Tosi passa da 18 a 19 ore, il dataset da 340 a 342 attività e da 361 a
362 ore erogate — e la quadratura `+/- = 0` resta su tutte e ventitré le
cattedre.

## Quello che l'ondata 4 ha spostato

| | Ondata 3 | Ondata 4 |
|---|---:|---:|
| Righe `SubjectConstraint` | 0 | **13** |
| Builder attivi (sonda) | 12 su 27 | **25 su 27** |
| Attività / ore erogate | 340 / 361 | 342 / 362 |
| Partizioni / parti | 16 / 32 | 17 / 34 |
| Variabili, fase 1 | 15 372 | 15 545 |
| Constraint, fase 1 | 8 758 | **11 783** |
| Fase 1 | `OPTIMAL`, 0 scarti | `OPTIMAL`, 0 scarti |
| Fase 2 | 71 su 71 | **73 su 73** |

⚠ **I due builder che restano sono nominati**: `structural:unavailability` (il
banco non ha ancora una riga di indisponibilità) e
`structural:didactic_weight` (i quattro tetti di `InstituteSettings` sono
tutti `None`, com'è fedele a EDT). Sono l'ondata 5. **27 su 27** resta il
criterio di accettazione dell'ondata 7.
