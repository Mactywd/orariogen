# La separazione per popolazione, con la perdita di qualità tollerata

**Data**: 2026-08-27
**Stato**: implementato
**Precede**: [criteri di qualità](2026-08-27-criteri-di-qualita-design.md) §8, dove
questo pezzo è dichiarato fuori scope

## 0. Il pezzo

I criteri di qualità esistono, e stanno tutti nella **stessa** catena: se una
scuola dichiara `gaps` per i docenti e `regularity` per le classi, il solve
ottimizza entrambe le popolazioni, nell'ordine dei `rank`.

**EDT non lo fa mai.** I comandi sono due — `Ottimizza gli orari dei docenti`
e `Ottimizza gli orari delle classi` — e l'enum interna è
`TypeTypeOptim = ttoProfs, ttoClasses`. `motore-risoluzione.md` lo scrive in
chiaro: *«EDT non cerca mai un ottimo congiunto»*. Al posto dell'ottimo
congiunto c'è un arbitrato dichiarato: si ottimizza una popolazione e si
dichiara **quanto si è disposti a peggiorare l'altra**, con i due campi
`Perdita di qualità tollerata per le classi:` / `... per i docenti:`, chiesti
**al lancio** e non nei parametri d'istituto.

> *«Non è un peso in una somma: è un vincolo di non-regressione con budget.»*
> — `motore-risoluzione.md`, §*La perdita di qualità tollerata*

Questo pezzo porta quel meccanismo: `Arbitrato(popolazione, tolleranza)`.

## 1. Perché non basta l'ordine dei `rank`

Obiezione naturale: la catena è già lessicografica, quindi «ottimizza per i
docenti» si scrive mettendo le righe dei docenti ai `rank` più bassi. Vero a
metà, e la metà che manca è il punto del pezzo.

Con i soli `rank`, i criteri delle classi restano **livelli**: il calcolo li
minimizza comunque, dopo. Costano — misurato nel pezzo precedente,
`regularity_classes` non dimostra l'ottimo in 15 s — e nessuno li ha chiesti.
L'arbitrato li declassa da livelli a **tetti**: non si ottimizzano, si
impedisce solo che peggiorino oltre il budget. È la differenza fra pagare
un'ottimizzazione e pagare una verifica.

## 2. La forma

```
Arbitrato(popolazione="teachers", tolleranza=10)
```

- le righe `QualityCriterion` con `population = teachers` diventano **livelli**,
  come oggi;
- le righe con `population = classes` — la popolazione **sacrificata** —
  diventano `valore <= base + tolleranza`, un vincolo hard;
- le righe con `population = all` restano livelli in ogni caso. `ALL` è una
  nostra estensione (EDT ha due popolazioni, non tre) e significa «questo
  criterio non prende parte»: non può essere la popolazione sacrificata.

Senza `Arbitrato` non cambia niente: catena unica, ogni riga un livello. È il
comportamento di oggi, e resta il default — un orario costruito **da zero** non
ha un'altra popolazione da preservare, perché non c'è ancora niente da
peggiorare.

### 2.1 La tolleranza è per criterio, nell'unità del criterio

Un solo numero per lancio, applicato **a ciascun** criterio sacrificato nella
sua propria unità: minuti per `gaps`, conteggi per gli altri. Sommare criteri
di unità diverse in un budget unico sarebbe la somma pesata che questo
progetto rifiuta a ogni livello.

⚠ Ed è esattamente la forma di `RelaxationQuota.params["margine"]`, che è pure
un numero per famiglia nell'unità della famiglia. Il precedente è nostro e la
tabella delle unità è già scritta.

## 3. La base — e perché non è una seconda definizione

`base` è il valore che quel criterio ha **sull'orario di partenza**: EDT
ottimizza un orario che c'è già, e «peggiorare» ha senso solo rispetto a
quello.

🔑 **Il valore si calcola con la stessa funzione del livello, non con una
copia.** Un criterio è una funzione `(ctx, model, chiavi) -> (espressione,
massimo)` che posta **solo definizioni** — è l'invariante dichiarato in testa a
`quality.py`, e qui incassa un dividendo che non era stato previsto quando è
stato scritto. Si costruisce un `CpModel` usa-e-getta, un `SolverContext` in
cui i letterali di cella sono le **costanti** `0`/`1` dell'orario esistente, un
`Vocabulary` nuovo su quel modello; si chiama la stessa funzione; ogni booleano
derivato è determinato per propagazione, e un `Solve` istantaneo restituisce il
numero.

L'alternativa era riscrivere i cinque criteri in Python su `ScheduleState`.
Sarebbe stata una seconda definizione della stessa quantità, cioè il difetto
che questo progetto ha già intercettato due volte (`B` nei rami disgiuntivi di
ADR-018 si **legge** chiamando il checker, mai riscrivendone la condizione).

### 3.1 Quando la base non esiste, il tetto non si posta

Due condizioni, entrambe verificate prima di postare qualcosa:

1. **ogni** attività libera ha un piazzamento precedente. Con un orario
   parziale la base sarebbe ottimisticamente bassa — un orario vuoto ha zero
   buchi — e il tetto diventerebbe una pretesa assurda;
2. ogni piazzamento precedente **sopravvive ai pre-filtri**. Se la vecchia
   cella non è più ammissibile, l'orario di partenza non è rappresentabile in
   questo modello e non è una base.

Se una delle due cade: **nessun vincolo**, e il comando lo **dichiara**. Un
tetto ottimistico renderebbe il calcolo infattibile per una ragione che
l'utente non può vedere, che è il modo peggiore di fallire.

⚠ È la stessa precondizione di L4, che pure esiste solo con un orario
precedente. E l'avvertimento letterale di EDT dice la stessa cosa dal suo lato:
*«l'ottimizzazione tiene conto unicamente delle attività estratte»*.

### 3.2 Un tetto può rendere il modello infattibile, ed è ammesso

`valore <= base + tolleranza` può non essere soddisfacibile: l'orario di
partenza soddisfa il tetto per costruzione, ma può essere illegale rispetto ai
vincoli hard (in questo progetto un orario in violazione è uno **stato
ammesso**), e allora non è raggiungibile.

⚠ Questo cade dalla parte **giusta** del criterio di ADR-018: *«`INFEASIBLE`
che nasce dal vietare un peggioramento è ammesso, `INFEASIBLE` che nasce dal
pretendere una riparazione no»*. Un tetto di non-regressione vieta un
peggioramento, per definizione. Il comando lo nomina nel messaggio d'errore,
perché alzare la tolleranza è la mossa che lo risolve.

## 3.3 ⚠ Non previsto dalla spec: la stabilità rendeva la qualità inerte

Trovato **implementando**, non scrivendolo: l'arbitrato ha bisogno di un
orario di partenza, e un orario di partenza mette in catena **L4**, la
stabilità. L4 raggiunge zero conservando tutto, e il suo fissaggio inchioda
ogni cella: da lì in giù **ogni livello di qualità è inerte**.

Misurato due volte. Sull'istanza minima — quattro celle, la qualità dei
docenti che potrebbe scendere da 4 a 2 — restava a 4. E sul Fermi con un
orario già scritto, dove la catena unica riporta `gaps_teachers 420`,
`isolated_teachers 20`, `regularity_classes 265` **in 0,06 s per livello**: non
sono risultati, sono i valori dell'orario che c'era già, misurati e non
migliorati. Un livello che chiude in sessanta millisecondi su 284 attività non
sta ottimizzando niente.

⚠ Il difetto **non è di questo pezzo**: c'era dal giorno in cui i criteri di
qualità sono nati, e non si vedeva perché il Fermi non ha piazzamenti di suo —
la misura che aveva dichiarato i criteri funzionanti girava su un orario vuoto,
dove L4 non esiste. È di nuovo la forma di sempre: una proprietà vera in un
dataset scambiata per una proprietà del codice.

**La correzione è d'ordine, e la decisione viene da EDT.** Là i comandi sono
due — `Piazzamento automatico` costruisce, `Ottimizza gli orari dei docenti /
delle classi` rimescola un orario che c'è già, e rimescolare *è* lo scopo. Qui
il comando è uno solo, quindi la corsa deve dichiararsi, e `arbitrato` è
esattamente quella dichiarazione. Senza arbitrato vince la stabilità (ADR-010:
rigenerando per il secondo quadrimestre non si stravolge l'orario di tutti);
con l'arbitrato la stabilità scivola in **coda** e diventa lo spareggio — fra
due orari di pari qualità, il più vicino a quello che c'è.

## 4. Cosa **non** entra

- **Due tolleranze insieme.** EDT mostra due campi perché la finestra è una
  sola; a ogni lancio ne morde uno, quello della popolazione non ottimizzata.
- **L'ottimizzazione individuale** (`FicheEDT_OptimIndividuelle`, su una
  singola risorsa, con `Numero di ore di buco tollerate per questa risorsa`).
- **La tolleranza come percentuale.** Unità assolute, come ogni quota qui.
- **Il valore *raggiunto* dal criterio sacrificato.** Il rendiconto dichiara
  base e tetto, non dove si è atterrati. Leggerlo richiederebbe che
  `solve_chain` restituisse il solver, oppure una seconda valutazione con le
  righe ripescate dal database e riappaiate per nome: parecchia coppia
  incidentale per un numero solo. Decisione, non dimenticanza.

## 5. Criteri di riuscita

1. Senza `Arbitrato` il modello è **identico** a quello di oggi, variabile per
   variabile.
2. Con `Arbitrato`, un criterio della popolazione sacrificata **non compare**
   fra i livelli, e uno della popolazione ottimizzata sì.
3. Il tetto **morde**: un'istanza in cui l'ottimizzazione dei docenti
   peggiorerebbe le classi risponde `INFEASIBLE` con tolleranza 0 e `OPTIMAL`
   con la tolleranza che serve.
4. La base calcolata dal modello usa-e-getta coincide con il valore che il
   **livello** dà sullo stesso orario. È il test che impedisce alle due strade
   di divergere, ed è la forma già adottata per i buchi contro il checker.
5. Base assente ⇒ nessun tetto, dichiarato, e il solve resta quello di prima.
6. Ogni proprietà è verificata per **mutazione**.

## 6. La misura, sul Fermi

284 attività, orario già costruito e scritto (`--applica`), poi
`--popolazione teachers --limite 15`:

| | catena unica | arbitrato, tolleranza 0 |
|---|---|---|
| `gaps_teachers` | 420 *(inerte)* | **0** |
| `isolated_teachers` | 20 *(inerte)* | **0** |
| `regularity_classes` | 265 *(inerte)* | tetto 265, base 265 |
| `spostamenti` | 0 | 231 |
| totale | 2,7 s | 32,2 s |

La catena unica è più veloce perché **non fa niente**: L4 la inchioda. Con
l'arbitrato l'orario dei docenti migliora davvero — buchi e ore isolate a zero
— e il prezzo è dichiarato: **231 attività su 284 si spostano**. È ciò che fa
`Ottimizza` in EDT, ed è la ragione per cui non può essere il default.

⚠ **Sul Fermi il tetto non morde**: buchi e ore isolate arrivano a zero
comunque, quindi con tolleranza 0 o 10 il risultato è lo stesso (`spostamenti`
231 contro 228). Come sempre su questo dataset, la misura è del **costo**, mai
della **copertura**: che il tetto morda lo dimostrano i test, su un'istanza
costruita perché le due popolazioni tirino in direzioni opposte.

### 6.1 Il tetto costa la definizione, il livello costa un `Solve`

L'A/B che sostiene §1, misurato:

| | var / constr | totale |
|---|---|---|
| due livelli, nessuna riga sulle classi | 9689 / 2712 | 32,9 s |
| due livelli **+ il tetto** | 10326 / 3350 | 31,6 s |
| **tre livelli** (la stessa riga non sacrificata) | 9870 / 2894 | **41,9 s** |

Un criterio declassato a tetto costa i suoi ~640 variabili di definizione e
**nessun** tempo di ricerca; da livello si prende una fetta intera del limite
(15 s) e chiude senza dimostrare l'ottimo. Il risparmio è quindi limitato dal
`--limite`, e **senza limite** non è limitato da niente.

⚠ Due avvertenze sulla lettura. La terza riga misura `regularity_teachers`,
non `regularity_classes`: è la stessa riga spostata di popolazione, quindi la
*quantità* è un'altra e ciò che l'A/B dimostra è strutturale — un livello
consuma una fetta di ricerca, un tetto no — non un confronto fra due numeri.
E sotto limite di tempo i risultati **non sono monotoni** nella dimensione del
modello: la prima riga, che ha meno vincoli, chiude con `isolated_teachers 18`
mentre la seconda arriva a `0`. È fortuna di ricerca, non semantica.

## 7. Ondate

1. spec (questa)
2. `Arbitrato`, la base, i tetti — `quality.py`, `objective.py`, `model.py`
3. `manage.py solve`: `--popolazione`, `--tolleranza`, il rendiconto
4. test e mutazioni
5. misura sul Fermi, `CLAUDE.md`

## 8. Esito — a consuntivo

Cinque ondate su cinque. **Tredici test**, **nove mutazioni con nove esiti
distinti** — ciascuna rende rosso esattamente ciò che afferma, e la mutazione
«niente è sacrificato» ne rende rossi undici su tredici.

⚠ Due mutazioni sono servite dove una sembrava bastare: sfasare il **tetto**
(`base + 1 + tolleranza`) non tocca il test che confronta la base col livello,
perché quel test guarda la base e non il tetto. Ci vuole la mutazione sulla
**fonte** (`solver.Value(var) + 1`) per farlo diventare rosso. Due numeri
vicini non sono lo stesso numero, e una sola mutazione avrebbe lasciato credere
che lo fossero.

⚠ **E l'istanza dei test è stata costruita dopo aver misurato che le ovvie non
funzionano.** Due docenti per due classi su una griglia 2×2 sembra la tensione
canonica e **non lo è**: due classi diverse possono occupare la stessa cella,
quindi comprimere i docenti comprime anche le classi e i due ottimi coincidono
— con tolleranza 0 e con tolleranza 2 la risposta era identica, cioè un test
incapace di distinguere. La tensione vera è fra `regularity` (la materia
sempre alla stessa fascia, quindi giorni diversi) e `free_half_days` (tutto lo
stesso giorno, quindi fasce diverse): l'una a 1 costringe l'altra a 2.

Suite: **612 test verdi**, 16 skip.
