# L'ora quindicinale, le quote e la qualità

L'ondata 6. Tre cose che stanno insieme perché sono **tutto ciò che il motore
ha e che nessun dataset aveva mai messo in moto**: gli alleggerimenti a quota,
i criteri di qualità e la seconda firma di settimana.

## 1. La quindicinale — la quinta forma, e la sola che non costa un'ora

La seconda ora di scienze del **5B** è a settimane alterne: una settimana in
laboratorio col tecnico, la settimana dopo teoria in aula. Nel nostro modello
sono **due attività con maschere complementari**.

| | Maschera | Aule candidate | Tecnico |
|---|---|---|---|
| Ora settimanale | l'anno intero (33) | LAB-SCI, LAB-INF | — |
| Metà di laboratorio | le 17 settimane **pari** | LAB-SCI, LAB-INF | ✔ |
| Metà di teoria | le 16 settimane **dispari** | — | — |

🔑 **Il monte ore non cambia, ed è il punto.** In ogni settimana ne è attiva
esattamente una: il docente lavora le stesse 2 ore, l'alunno ne riceve 2, e la
cattedra di N02 resta a 10. Lo sdoppiamento delle ondate 2 e 4 costa invece
l'ora che il docente ripete per la seconda metà classe (N01 da 17 a 19). È la
differenza fra **sdoppiare** e **alternare**, ed è tutta nella maschera.

⚠ **17 e 16, non 16,5.** Un anno con un numero dispari di settimane dà a una
delle due metà una volta in più. È un fatto del calendario, e va scritto
perché è il genere di asimmetria che dopo si scambia per un errore.

⚠ **L'allineamento resta vuoto**, e non è una dimenticanza: 📦 lo XSD dichiara
che *l'allineamento genera l'attività complessa*, cioè **una** collocazione per
le attività allineate. Le due metà non sono simultanee — non lo sono mai —
quindi allinearle direbbe il contrario di ciò che sono. **Alternare non è
allineare.**

⚠ Le **richieste d'aula restano 73**, non 74: la metà di teoria non prenota il
laboratorio, ed è ciò che rende la quindicinale una *scelta* invece di una
scrittura diversa della stessa ora. Il laboratorio conteso si spende una
settimana su due.

### Cosa esercita

- 🔑 `structural:occupation` **per firma di settimana**. È l'unico builder che
  le distingue (lo dice il suo docstring), e nessun dataset gliel'aveva mai
  chiesto. Le due metà stanno sulla stessa classe, quindi condividono la
  chiave: **possono stare nella stessa cella**, e solo perché le maschere non
  si intersecano. È poi come una scuola scrive davvero un'ora quindicinale —
  «scienze al martedì alla terza» — e cambia solo cosa ci si fa dentro.
- `week_signatures`, `SolverContext.states`, `solve_rooms` per firma.
- ⚠ E il debito **L7**, §3.

### La misura, e un'attesa smentita

L'attesa scritta prima diceva *«variabili e constraint circa il doppio, il
vocabolario è per firma»*. È **sbagliata l'attesa**, e la smentita è
istruttiva.

| | Variabili | Constraint |
|---|---:|---:|
| Ondata 5 | 15 233 | 12 251 |
| + le due quote | 15 244 | 12 255 |
| + la quindicinale | 15 319 | 13 813 |
| Ondata 6 | **15 330** | **13 817** |

🔑 **Una seconda firma non raddoppia il modello: costa quanto le attività che
la distinguono.** Il vocabolario memoizza per `(firma, chiave, giorno,
fascia)`, ma le variabili derivate nascono solo dove un builder posta
qualcosa, e `OccupationBuilder` deduplica i constraint identici fra firme
(`signature` è la coppia cella + insieme di attività). Le uniche chiavi che
distinguono le due settimane sono quelle toccate dalle due metà. **+86
variabili e +1562 constraint**, cioè +0,6 % e +12,7 %.

⚠ **E non contraddice la nota di `quality.py`** che chiama le firme *«una
dimensione moltiplicativa (~0,3 s per firma)»*: quella misura è sulla **fase
5**, cioè su `check_schedule`, che esegue *ogni* checker una volta per firma.
Là è moltiplicativo davvero. Nel solver no. Sono due cose diverse che si
somigliano.

## 2. Le quote — e perché il dataset non le consuma

Due righe, e sono le **due forme** che la finestra `Alleggerimenti` di EDT
distingue: il *quanto* e il *quante volte*.

| Riga | Forma | Portatore | Parametri |
|---|---|---|---|
| `mg_donati` | **deroga** | R02 Donati (il `MG`) | 1 violazione, nessun margine |
| `presenza_cappellano` | **margine** | R01 Colombo (`max_presence`) | 2 violazioni, margine 180 min |

⚠ **Nessuna delle due è consumata dal dataset**, e sembra una rinuncia. Non lo
è: l'ondata 3 pretende che l'orario di base non porti **nessun** finding
`HARD` oltre alle aule non assegnate, e una quota consumata *è* una violazione
nominata — la quota autorizza il solver a produrla e non la nasconde. Una
quota consumata dalla base spegnerebbe quel test. Quindi le righe stanno qui
perché i builder le leggano su dati veri (**+11 variabili, +4 constraint**: la
misura dice che le leggono), e la tensione la mette il **testimone**, come per
i divieti dell'ondata 4.

⚠ **E i due portatori non sono bordi di nessuna ondata precedente.** Allentare
un bordo dell'ondata 3 renderebbe risolvibile la sua tacca, cioè spegnerebbe
un test scritto tre ondate fa: il bordo del `MG` sta sulla 2A e non su DONAT,
quello di `max_presence` su GENTI e non su COLOM.

### La deroga

R02 insegna l'alternativa in tutte e dodici le classi, dodici ore. Il
testimone la fa venire **due giorni**: col `MG` — mai mattina *e* pomeriggio
nello stesso giorno — due giornate danno al più due mattine, cioè dieci fasce
per dodici ore. Derogare **una** volta apre un pomeriggio: 5 + 5 + 3 = 13.

| | Atteso | Osservato |
|---|---|---|
| Senza la quota | `INFEASIBLE` | ✅ |
| Con la quota | `OPTIMAL` | ✅ |
| Il finding `only_half_day` con la quota | **resta** | ✅ |

### Il margine, e la taglia

🔑 **Il numero della quota conta, non la sua presenza** — è la mutazione che il
docstring di `RelaxationQuota` chiede per nome: *«"la quota è collegata" passa
anche se il margine vale dieci volte quello dichiarato»*.

Il cappellano viene lunedì e martedì e la presenza scende a **quattro** fasce.

| Quota | Fasce disponibili | Esito |
|---|---|---|
| 0 | 4 + 4 = 8 | `INFEASIBLE` |
| 1 | 4 + 7 = 11 | `INFEASIBLE` |
| 2 | 7 + 7 = 14 | `OPTIMAL` |

Dodici ore, più la fascia libera che il cambio di sede si porta dietro: ne
servono tredici. La riga di mezzo è quella che porta l'informazione — è l'unica
che distingue «la quota c'è» da «la quota è quella giusta».

⚠ **E la prima taratura era sbagliata, in un modo che vale la pena scrivere.**
Diceva cinque fasce e un margine di due ore, e faceva dire al caso di mezzo
*5 + 7 = 12 fasce per dodici ore più il viaggio*. Vero, e il solver non ci
arrivava: `UNKNOWN` a 180 s e di nuovo a 120 s. Il legame «solo due giornate
sono attive» passa da booleani che il rilassamento lineare non lega ai minuti.
Due correzioni: le due giornate si dichiarano col **rosso** (il pre-filtro
toglie le celle, e le giornate diventano due *davvero*), e l'aritmetica si
sposta tutta sulle ore. I tre casi chiudono in 37 s.

🔑 La regola che ne esce: **un test che misura la potenza del propagatore
invece di una proprietà del modello è un test che un giorno diventa rosso da
solo.**

## 3. La qualità — e il debito che l'ondata rende misurabile

`CRITERI_QUALITA` porta **cinque generi, sei righe** e le due popolazioni:
la tabella intera di `QualityCriterion`, che nessun dataset aveva.

| Rango | Genere | Popolazione |
|---:|---|---|
| 1 | `gaps` | docenti |
| 2 | `gaps` | classi |
| 3 | `isolated` | tutte |
| 4 | `free_half_days` | docenti |
| 5 | `regularity` | **classi** — l'asimmetria è del prodotto |
| 6 | `preferences` | tutte |

⚠ **`build()` non la installa.** Non è pigrizia: sei livelli portano un `solve`
da 9 a **82 secondi**, e ogni test del banco li pagherebbe. È anche la forma
giusta, perché in EDT l'ottimizzazione è un comando a sé che si lancia su un
orario che già c'è — `Ottimizza gli orari dei docenti` non è una fase del
calcolo. Chi la vuole la chiede: `build(qualita=True)`.

### Cosa dice la catena

| Livello | Valore | Ottimo dimostrato |
|---|---:|---|
| `gaps_teachers` | 0 | ✔ |
| `gaps_classes` | 0 | ✔ |
| `isolated_all` | 71 | ✗ (divario 71) |
| `free_half_days_teachers` | 143 | ✗ (limite inferiore 19) |
| `regularity_classes` | 936 | ✗ (limite inferiore 101) |
| `preferences_all` | 0 | ✔ |

⚠ **L'ultima riga non è stabile, e il perché è la cosa da portarsi via.** In una
seconda misura `preferences_all` vale **1**, e non perché il verde sia
incerto: i tre livelli sopra di lui esauriscono il budget senza dimostrare il
proprio ottimo, quindi vengono fissati al valore che la ricerca *ha trovato* —
e con esso cambia la regione in cui il verde deve stare. Un livello sotto un
livello non dimostrato eredita l'indeterminatezza di quello. Il test del verde
lo installa quindi **da solo**: là lo zero è una proprietà del modello, qui
sarebbe un fatto sulla ricerca. È la lezione della mutazione per rimozione
dell'ondata 3, in un posto nuovo.

🔑 La lezione del Fermi si ripete a scala maggiore: **un livello di qualità non
è lento perché difficile da ottimizzare, è lento perché impossibile da
dimostrare.** `gaps` chiude subito perché zero è anche il suo limite inferiore
banale.

🔑 **E il verde dell'ondata 5 chiude il suo anello.** La riga `preferenza` mette
AMATO in verde sulla prima fascia di tutti i giorni. L'ondata 5 ha provato che
**non vieta**: l'orario esiste lo stesso. Qui si prova che **conta**: col solo
criterio delle preferenze installato, `preferences_all` scende a zero e lo
dimostra, cioè nessuna ora di AMATO finisce alla prima fascia. Un pre-filtro che non filtra e un criterio che non
conta si somigliano molto, e sono cose diverse.

### L'arbitrato

`solve --popolazione teachers --tolleranza 5`, su un orario che **già c'è**:
i due criteri delle classi smettono di essere livelli e diventano tetti di
non-regressione, e la stabilità scivola in coda a fare da spareggio.

| Criterio sacrificato | Base | Tetto |
|---|---:|---:|
| `gaps_classes` | 0 | 5 |
| `regularity_classes` | 947 | 952 |

## 4. ⚠ L7 — i criteri di qualità ignorano le firme di settimana

Il debito aperto il 2026-08-30 (L3) diceva che i criteri di qualità ignorano
le firme di settimana e che **nessuna delle due basi lo esercita**. La seconda
metà non è più vera.

Il testimone è aritmetico. Il 5B al lunedì, sulle prime quattro fasce:
l'italiano alla prima e alla quarta, la metà di laboratorio alla seconda,
quella di teoria alla terza.

| Settimana | Fasce occupate | Buchi |
|---|---|---|
| pari | 0, 1, 3 | **1** (la fascia 2) |
| dispari | 0, 2, 3 | **1** (la fascia 1) |
| unione — ciò che vede il criterio | 0, 1, 2, 3 | **0** |

Sullo stesso orario, la stessa quantità — *«la durata totale dei buchi»*, che
il criterio calcola senza tetto e il D.T.B. col tetto, e che `criteria.buchi`
dichiara letteralmente essere la stessa — vale **60 minuti in ogni settimana
dell'anno** per `check_schedule` e **zero** per il criterio.

🔑 **E non è un difetto nuovo: è lo stesso** che `MaxGapBuilder` aveva fino al
2026-08-24, descritto per esteso nel docstring di `Vocabulary.covered` —
*«un'occupazione che cade dentro il buco ma viene da un'altra firma alza il
conteggio senza spostare prima/ultima occupata, e chiude nel modello unione un
buco che, settimana per settimana, resta aperto»*. Il builder passa
`signature`; i criteri no.

⚠ `quality.py` lo dichiara come approssimazione, con l'argomento che un
obiettivo approssimato *ordina male orari tutti legali* e non ne ammette uno
illegale. L'argomento regge, e non è questo il posto per discuterlo. Ciò che
non regge più è la parte di contorno: che nessun dataset lo esercitasse.

**Non si ripara** (spec §8): è **L7** in [`docs/todo.md`](../../docs/todo.md),
fissato da un test che diventerà rosso il giorno in cui si chiude — come L5,
L6 e L6bis.

⚠ E il testimone ha un **ramo di controllo**, per la ragione che l'ondata 5 ha
imparato a sue spese: con la metà di teoria non piazzata l'unione diventa
0-1-3, il buco c'è anche lì e il criterio dice **180** (tre chiavi: la classe e
le sue due parti IRC/alternativa, che `chiavi_di` conta per conto proprio).
Senza quel ramo, uno zero da criterio spento e uno zero da firma di settimana
si somiglierebbero troppo.
