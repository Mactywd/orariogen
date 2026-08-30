# I dieci criteri di piazzamento — il materiale per decidere

> **Cos'è questo file.** [O5](todo.md) è una decisione travestita da
> osservazione: la lista degli undici criteri di `Ordinamento dei criteri` è
> osservata da luglio e riconfermata valore per valore, ma nessuno ha mai detto
> **dentro o fuori** per i dieci che non abbiamo tradotto. Qui c'è, per
> ciascuno, cosa fa in EDT, cosa già abbiamo che lo tocca, cosa costerebbe, e
> una raccomandazione motivata. Serve a rispondere, non a decidere al posto di
> chi risponde: la colonna che conta è l'ultima, ed è di chi fa il prodotto.
>
> ⚠ **Non è documentazione di EDT.** L'osservazione sta in
> [edt/motore-risoluzione.md](edt/motore-risoluzione.md); qui c'è solo il
> giudizio su cosa farne, che è nostro e va marcato come tale.

## Prima: i due meccanismi, e perché la domanda ha senso

Confonderli era l'errore di partenza, e senza scioglierlo la lista sembra
ridondante.

| Riquadro | Cosa contiene | Da noi |
|---|---|---|
| `Ordinamento dei criteri` | gli **undici criteri di piazzamento**, in ordine lessicografico | uno solo tradotto (l'undicesimo) |
| `Ottimizzazione degli orari` | una fase **separata**, cinque valori, tre slot per popolazione | quattro su cinque tradotti |

I due si somigliano perché parlano delle stesse cose — buchi, mezze giornate —
ma agiscono in momenti diversi: il primo guida **come si sceglie una cella
mentre si piazza**, il secondo **come si migliora un orario già fatto**. Un
criterio di piazzamento non è quindi «un criterio di qualità che non abbiamo
ancora scritto»: è un criterio in un motore che noi non abbiamo, perché il
nostro piazzamento è un modello CP-SAT e non una ricerca guidata.

🔑 **Ed è questa la ragione per cui la maggior parte della lista non si porta,
e non è un rimando.** In EDT l'ordine dei criteri governa un'euristica di
ricerca: la scelta della prossima cella. In CP-SAT la ricerca la governa il
solver, e ciò che possiamo dichiarare è un **obiettivo**. Un criterio di
piazzamento diventa da noi o un livello della catena — cioè un criterio di
qualità, il secondo meccanismo — o niente. La domanda vera non è «tradurlo sì o
no», è: **questo criterio dice qualcosa che i nostri quattro livelli non dicono
già?**

## I dieci, uno per uno

Numerazione e nomi come osservati (`docs/edt/motore-risoluzione.md`).

### 1. `Ottimizza le fasce orarie libere` — famiglia *buchi*

**In EDT.** Il primo della classifica: guida il piazzamento verso orari in cui
le fasce libere si aggregano invece di sparpagliarsi.

**Da noi.** È ciò che i livelli `gaps` e `free_half_days` misurano già, dai due
lati: meno buchi *e* più mezze giornate intere libere. Non aggiunge una
grandezza, aggiunge una priorità sulle stesse.

**Raccomandazione: ❌ fuori, perché è già dentro.** Ciò che di questo criterio
si può dichiarare è l'**ordine** fra `gaps` e `free_half_days`, e l'ordine da
noi è già un dato (`QualityCriterion.rank`). Tradurlo vorrebbe dire aggiungere
un terzo numero che misura la stessa cosa dei primi due.

### 2. `Riduci i buchi di mezza fascia oraria` — famiglia *buchi*

**In EDT.** Un mezzo buco è più fastidioso di un buco intero in più — sta al
posto 2, il conteggio generale al 6.

**Da noi.** Richiede la **suddivisione sub-oraria** della griglia, che è a
`Nessuno` in ogni base che abbiamo visto (la nostra e quella del produttore) e
che il nostro `TimeGrid` non ha: la fascia è l'unità.

**Raccomandazione: ❌ fuori, e dichiarato.** Non è una scelta di priorità, è una
dipendenza da una feature che non abbiamo. Se un giorno la mezza fascia entra,
questo criterio torna con lei — non prima.

### 3. `Comincia dall'inizio delle fasce orarie intere` — famiglia *allineamento*

**In EDT.** Stessa dipendenza del 2, dall'altro lato: con la suddivisione
attiva, preferisci far partire le attività sul confine dell'ora intera.

**Raccomandazione: ❌ fuori, per la stessa ragione del 2.**

### 4. `Distribuisci nella settimana le attività della stessa materia` — famiglia *distribuzione*

**In EDT.** Le tre ore di matematica su tre giorni diversi, non due il lunedì.

**Da noi.** ⚠ **Questo lo abbiamo già come vincolo hard**, non come criterio:
`SubjectConstraint` con `MIN_DISTRIBUTION` e le famiglie `SAME_DAY_INCOMPATIBLE`
/ `TWO_DAYS_INCOMPATIBLE` dicono la stessa cosa in forma di divieto. La
differenza è che il vincolo *impedisce*, il criterio *preferisce*.

**Raccomandazione: 🟡 la più difendibile della lista, e la prima da fare se se
ne fa una.** Il valore è concreto: oggi una scuola che non vuole due ore di
matematica lo stesso giorno deve dichiararlo come divieto, e un divieto rende
l'istanza infattibile dove un criterio l'avrebbe solo peggiorata. Costo: un
`QualityCriterion.Kind` nuovo, una funzione in `criteria.py` che conta le
coppie di occorrenze della stessa materia nello stesso giorno per unità, e una
riga di dati. Nessun vincolo nuovo, nessun rischio sull'ammissibilità — è la
proprietà dichiarata in testa a `quality.py`.

### 5. `Riduci i buchi quindicinali` — famiglia *buchi*

**In EDT.** Il buco che esiste solo in una delle due settimane di
un'alternanza A/B.

**Da noi.** Le firme di settimana ci sono e i vincoli le distinguono già
(`MaxGapBuilder` posta un budget per firma). I **criteri di qualità** invece
no: contano su una settimana sola.

**Raccomandazione: ❌ fuori per ora, ma è l'unico «fuori» che nasconde un
difetto e non una scelta.** Che i criteri di qualità ignorino le firme è una
semplificazione mai dichiarata: su una scuola con attività quindicinali il
numero che il rendiconto stampa non è il numero di nessuna settimana reale. Va
messo fra i debiti, indipendentemente da come si decide O5.

### 6. `Riduci il numero di buchi` — famiglia *buchi*

**Da noi.** È `gaps`, con un'unità diversa: noi contiamo i **minuti**, EDT qui
conta i **buchi**. Due orari con 120 minuti di buco — uno da due ore, due da
un'ora — sono uguali per noi e diversi per EDT.

**Raccomandazione: 🟡 tenibile a costo quasi nullo, se qualcuno lo chiede.**
Sarebbe un secondo criterio sulla stessa quantità con l'unità cambiata: la
funzione è già scritta (`buchi` in `criteria.py`), basta non moltiplicare per
`slot_minutes` e registrare un `Kind` diverso. Non lo farei senza che una
scuola l'abbia chiesto: due criteri quasi identici nella stessa lista sono una
UI peggiore, non migliore.

### 7. `Equilibra i turni di mensa` — famiglia *mensa*

**Raccomandazione: ❌ fuori, deciso altrove.** La mensa è fuori scope
([scope-v1.md](scope-v1.md)): è un problema di assegnazione a turni con
capienze, non di orario. Cade con lei, e non è una decisione nuova.

### 8. `Evita le attività della stessa materia nella stessa ora` — famiglia *distribuzione*

**In EDT.** Non «giorni diversi» (è il 4), ma **ore diverse**: la matematica non
sempre alla prima ora.

**Da noi.** ⚠ Sembra il contrario esatto di `regularity`, che è già nostro:
quel criterio minimizza il numero di fasce distinte usate da una coppia
(unità, materia), cioè **premia** la materia che torna alla stessa ora.

🔑 **Non è una contraddizione di EDT, ed è la cosa che vale la pena aver capito
qui.** Sono due meccanismi e due popolazioni. Il *piazzamento* evita la stessa
ora per tutti; l'*ottimizzazione* la ripristina per le sole **classi** —
`tcoMemesHoraires` nella base di esempio è il primo e unico criterio dell'orario
delle classi, e non compare affatto in quello dei docenti. Il verso opposto non
è un errore di traduzione: per la classe la ripetizione è una routine, per il
docente è una condanna.

**E da noi l'asimmetria è già esprimibile**: `QualityCriterion.population` fa
esattamente questo filtro, e la nostra riga di regolarità va dichiarata
`CLASSES` come in EDT (i test lo fanno già). Quindi qui **non c'è un difetto da
correggere** — c'è un'assenza: per i **docenti** non abbiamo niente che spinga
*via* dalla stessa ora, mentre EDT ce l'ha.

**Raccomandazione: 🟡 il secondo candidato, e costa poco.** È la stessa funzione
di `regularity` **massimizzata** invece che minimizzata — o, in forma di
minimo, `numero di occorrenze − fasce distinte`. Un `Kind` nuovo, dichiarabile
per la popolazione dei docenti, e la certezza che nessuna scuola dichiarerà
entrambi sulla stessa popolazione (che sarebbe un ordine lessicografico fra due
criteri opposti, cioè il secondo inerte).

### 9. `Distanzia le attività della stessa materia` — famiglia *distribuzione*

**In EDT.** Il terzo dei tre sulla distribuzione: non basta giorni diversi (4) e
ore diverse (8), si vuole anche **distanza** fra le occorrenze.

**Da noi.** `HALF_DAY_GAP` fra le famiglie di `SubjectConstraint` dice qualcosa
di simile, di nuovo come vincolo hard.

**Raccomandazione: ❌ fuori.** Con il 4 tradotto come criterio, questo aggiunge
un terzo numero sulla stessa famiglia per un guadagno che nessuno ha chiesto.
Se il 4 si fa e si dimostra utile, se ne riparla con una misura in mano.

### 10. `Favorisci le mezze giornate libere` — famiglia *tempo libero*

**Da noi.** È `free_half_days`, tradotto, con la sua quota e il suo livello.

**Raccomandazione: ❌ fuori, perché è già dentro.** Come l'1.

## Il riassunto, in una tabella

| # | Criterio | Raccomandazione | Perché |
|---|---|---|---|
| 1 | `Ottimizza le fasce orarie libere` | ❌ già dentro | è `gaps` + `free_half_days` |
| 2 | `Riduci i buchi di mezza fascia` | ❌ dipendenza mancante | serve la suddivisione sub-oraria |
| 3 | `Comincia dall'inizio delle fasce intere` | ❌ dipendenza mancante | idem |
| 4 | `Distribuisci nella settimana la stessa materia` | 🟡 **il candidato** | oggi è solo un divieto; come criterio non rende infattibile |
| 5 | `Riduci i buchi quindicinali` | ❌ … ma apre un debito | i criteri di qualità ignorano le firme di settimana |
| 6 | `Riduci il numero di buchi` | 🟡 a costo quasi nullo | `gaps` con l'unità cambiata; solo se richiesto |
| 7 | `Equilibra i turni di mensa` | ❌ già deciso | cade con la mensa, fuori scope |
| 8 | `Evita la stessa materia nella stessa ora` | 🟡 il verso che manca | `regularity` al contrario, per i **docenti** |
| 9 | `Distanzia la stessa materia` | ❌ | terzo numero sulla stessa famiglia |
| 10 | `Favorisci le mezze giornate libere` | ❌ già dentro | è `free_half_days` |

**Sette no e tre forse.** Non è un risultato deludente: è il risultato di aver
capito che i due meccanismi sono diversi. La lista degli undici governa
un'euristica di ricerca che noi non abbiamo, e le sue voci utili erano già state
prese — dall'altro riquadro, quello giusto.

⚠ **Una cosa da fare comunque, qualunque sia la decisione.** Il criterio 5 ha
scoperto che i **criteri di qualità ignorano le firme di settimana**: contano su
una settimana sola, mentre i vincoli le distinguono già. Su una scuola con
attività quindicinali il numero che il rendiconto stampa non è il numero di
nessuna settimana reale. È un debito, e va aperto anche se O5 si chiude con
dieci «no».

**Le tre cose da fare, se la decisione le approva**, in ordine di valore:

1. **Tradurre il 4** (`Distribuisci nella settimana la stessa materia`) come
   criterio: è l'unico che dice qualcosa che oggi sappiamo esprimere solo come
   divieto, e un divieto rende infattibile dove un criterio peggiora e basta.
2. **Tradurre l'8** per i docenti: `regularity` al contrario, la stessa funzione
   con il segno cambiato.
3. **Il 6**, se e solo se una scuola chiede di contare i buchi invece dei
   minuti.
