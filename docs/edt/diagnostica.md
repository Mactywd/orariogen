# EDT — Diagnostica: perché un'attività non si piazza

> Fonte 📦: etichette di interfaccia estratte da `EDT Monoposto.dll` (69 888
> stringhe IT/FR/EN allineate per chiave). Vedi [ADR-009](../decisioni.md).
> ⚠ Il binario è condiviso con PRONOTE: qui compare solo ciò che è
> inequivocabilmente sul piazzamento delle attività.
>
> **Nessuna di queste finestre è stata ancora osservata in UI.** La struttura è
> certa (i testi sono letterali), la disposizione visiva no.

## Perché è il documento più importante per il prodotto

Un generatore di orari che risponde solo «fatto» / «non ce l'ho fatta» è
inutilizzabile. Nella pratica reale la domanda del vicepreside non è *"generami
l'orario"*, è *"perché questa lezione non ci sta?"* e *"cosa succede se la metto
qui lo stesso?"*.

EDT risponde a entrambe, e lo fa con un **catalogo di causali nominate**: non dice
"infeasible", dice *"La classe è già occupata in un'attività bloccata"*. Quel
catalogo è riusabile quasi così com'è: sono i casi che si presentano davvero.

## 🔑 Il catalogo delle causali

Famiglia `AffSco_UtilDiagnostic`, ~170 stringhe. Ogni causale è una frase intera,
formattata per essere concatenata in un elenco mostrato all'utente.

### Risorsa occupata — cinque varianti per **ogni** risorsa

Il pattern si ripete identico per classe, gruppo, raggruppamento, docente, aula,
materiale, personale:

| Variante | Testo (esempio sulla classe) | Conseguenza per il motore |
|---|---|---|
| occupata | *"La classe è già occupata in un'attività"* | conflitto |
| occupata, **spostabile** | *"...in un'attività che ha una collocazione altrove"* | **liberabile** |
| occupata, **bloccata** | *"...in un'attività bloccata"* | non liberabile |
| in permanenza | *"...in una permanenza"* | liberabile |
| in permanenza bloccata | *"...in una permanenza bloccata"* | non liberabile |

🔑 **La distinzione «spostabile» / «bloccata» è il perno di tutto.** È ciò che
permette al risolutore passo-passo di sapere se può spostare l'occupante attuale o
deve rinunciare allo slot. Nel nostro modello non basta sapere che uno slot è
occupato: serve sapere **da cosa** e **se quel qualcosa è mobile**.

Per aule e materiali esiste in più il **picco d'occupazione**: *"il gruppo di
aule/materiale ha raggiunto il suo picco d'occupazione"* — è il meccanismo `Qtà`
(capacità simultanea) documentato in [aule.md](aule.md).

### Indisponibilità e preferenze

Per **nove** tipi di risorsa (`Classe`, `Cours`, `Eleve`, `Groupe`, `Materiel`,
`Personnel`, `Prof`, `Responsable`, `Salle`) esistono in parallelo:

- `Indispo*` — *"Il docente ha una indisponibilità"*
- `IndispoSouple*` — *"Il docente ha un'indisponibilità opzionale"*
- `Voeu*` — *"Il docente ha una preferenza"*

Conferma diretta e indipendente dei **tre pennelli** già osservati in UI
(`Indisponibilità` / `Indisponibilità opzionali` / `Preferenze`, vedi
[vincoli.md](vincoli.md)), e della loro **genericità sulla risorsa**.

Nota terminologica: FR `voeu` (voto, desiderio) → IT `preferenza`.

### Vincoli di materia — le stesse dieci colonne, come messaggi

Le causali ricalcano esattamente le colonne della griglia dei vincoli di materia
già documentate, ma qui col nome della materia iniettato (`%s`):

| Causale | Testo |
|---|---|
| `MatieresIncompatibles2JoursFmt` | *"%s, troppe attività su 2 giorni"* |
| `MatieresIncompatiblesJourneeFmt` | *"%s, troppe attività nella giornata"* |
| `...MatinFmt` · `...SoirFmt` · `...MatinOuSoirFmt` | varianti mattina/pomeriggio |
| `MaxHoraireMatiereJourneeFmt` e varianti | *"%s, troppe ore nella giornata/mattinata/pomeriggio"* |
| `EcartDjMatieresFmt` | *"%s, numero di mezze giornate insufficiente"* |
| `EnchainementImposeDemiJourneeFmt` · `...JourneeFmt` | *"%s, sequenza in mezze giornate/giornate successive non rispettata"* |
| `OrdreCycleFmt` · `OrdreHebdoFmt` | ordine nel ciclo / settimanale non rispettato |
| `SuccessionMatiereFmt` | *"%s, sequenza indesiderata di attività"* |

#### 🔑 Chiuso: i quattro valori `Parties…Classe`

Era un punto aperto dal 2026-07-26 mattina. La causale `OrdreClasseParties_S` lo
scioglie con il testo letterale:

> *"%s, ordine delle attività in gruppo rispetto alle attività a classe intera non
> rispettato"*

Conferma quindi che i quattro valori `PartiesAvantClasse`, `PartiesApresClasse`,
`PartiesAvantOuApresClasseH`, `PartiesAvantOuApresClasseAB` dell'enum
`TypeIncompatibiliteMatiereClasse` sono i modi di ordinare **le ore in gruppo
rispetto alle ore a classe intera**, come già dedotto dall'aiuto contestuale.
Due fonti indipendenti concordano: il punto si può chiudere.

### Vincoli fra attività

Non legati a una materia: `CaCIncompatibilite` (*"Incompatibilità con un'altra
attività"*), `CaCRegroupement` (*"Collocazione imposta con un'altra attività"*),
`Ordre`, `SuccessionImposee` / `SuccessionInterdite`, `QuinzaineImposee` /
`QuinzaineInterdite`, `RepartitionQuinzaine` (*"Un'attività quindicinale della
stessa materia è già piazzata questa settimana"*), `RepartitionImposeeNonRespettee`.

### Vincoli orari sulla risorsa

`DemiJourneeTravaillee` (*"Massimo di 1/2 giornate di lavoro superate"*),
`MaxHoraireRessourceJournee/Matin/Soir/MatinOuSoir`, `MaxPresentielRessource`
(*"Massimo di ore di presenza superato"*), `PlageHoraireGarantie` (*"Il docente non
ha più giorni e 1/2 giornate libere"*), `Recreation` (*"Intervallo non
rispettato"*), `PoidsPedagogiquesJournee/Matin/Soir/MatinOuSoir` (*"Limite dei pesi
didattici superato"*), `DebutCoursInterdit*` (*"…non può iniziare un'attività su
questa fascia oraria"*).

### Vincoli di sede

| Causale | Testo |
|---|---|
| `SitesIncompatiblesDureeTrajet` | *"Tempo insufficiente per il trasferimento di sede"* |
| `SitesIncompatiblesHeureTransition` · `...Recreation` | *"Cambio di sede al di fuori delle pause/intervalli definiti"* |
| `SitesIncompatiblesNbTransitionsCycle/Hebdo/Jour` | *"Numero di cambi di sede superiore al limite fissato"* |

## 🔑 Le attività hanno una priorità

Causali `ClasseOccupeeCoursPrioritaire` / `...NonPrioritaire`, e le voci di menu:

- `Rendi prioritarie le attività`
- `Rendi non prioritarie le attività`

Esiste quindi un **flag di priorità per attività** che governa la sostituibilità:
un'attività non prioritaria può essere spostata per far posto a una prioritaria.
Non l'avevamo documentato. È un attributo del modello, distinto dal blocco: il
blocco dice *"non toccare"*, la priorità dice *"toccabile, ma solo per una causa
migliore"*.

## I quattro stati dell'attività

`Type_EtatCours` — non è un booleano piazzata/non piazzata:

| Stato | IT |
|---|---|
| `NonPlace` | Non piazzata |
| `EnEchec` | **Scartata** |
| `Place` | Piazzata |
| `Verrouille` | Bloccata |

⚠ Da chiarire in UI: se `NonPlace` («non ancora tentata») e `EnEchec` («tentata e
fallita») siano davvero distinti per l'utente, o due nomi dello stesso stato dopo
un calcolo incompleto.

**Tracciabilità.** `Type_OperationCours` mostra che ogni operazione è **loggata e
distinguibile**: `Piazzamento automatico`, `Piazzamento manuale`, `Risolvi`,
`Trova una soluzione`, `Sospensione`, `Piazza / Sistema`. Un audit trail per
attività — vale la pena averlo anche da noi, perché la domanda *"chi ha spostato
questa lezione e perché"* arriva sempre.

## La modalità diagnostica del piazzamento manuale

La diagnostica **non è sempre attiva**: c'è un comando esplicito
`Passa alla modalità diagnostica` (FR *Passer en mode diagnostic*).

Nelle `Preferenze di piazzamento manuale delle attività`:

> ☐ `Nascondi le attività che non rientrano nella diagnostica`
> *(altre attività del gruppo di aule, attività di gruppi senza legami...)*

più tre interruttori sul comportamento del trascinamento:

- `Consenti lo spostamento delle attività bloccate`
- `Blocca le attività piazzate manualmente`
- `Impedisci la sospensione delle attività bloccate`

### La legenda della griglia

- `Risorsa in rosso:` → `Occupata in un'attività` / `Occupata in un'attività bloccata`
- `Risorsa assente` · `Risorsa barrata`
- `Risorsa in rosso +` · `Gruppo in rosso +` → il `+` segnala che c'è altro da
  vedere (presumibilmente un tooltip con l'elenco delle causali)
- `Gruppi collegati occupati da alcune attività`
- `Mezza giornata non lavorativa` · `Giorno festivo`

## Diagnostica sui raggruppamenti

`UtilitaireEDT_DiagnosticCliques`: avvisi quando un raggruppamento supera il
proprio massimo di ore e/o il limite dei pesi didattici, in forma aggregata
(*"Alcuni raggruppamenti (%d) superano il loro massimo di ore e/o il limite dei
pesi didattici"*) o puntuale.

Il nome **`Cliques`** è terminologia da teoria dei grafi: suggerisce che il motore
modelli i raggruppamenti come cricche di compatibilità. Indizio sull'algoritmo, non
prova.

## 🔑 L'analisi dei vincoli — osservata in UI

`Elabora → Analisi → Lancia l'analisi dei vincoli`. **Osservata il 2026-07-26.**

È il primo comando del menu, **prima del piazzamento**. Dichiarazione d'intenti,
testo letterale del pannello destro:

> **Verifica della coerenza dei dati**
> *"EDT verificherà che tutti i dati inseriti (attività e vincoli) permettano il
> piazzamento di tutte le attività"*

### Le cinque fasi

Sono caselle **selezionabili singolarmente** (tutte spuntate di default), sotto
l'intestazione `LE FASI`:

| # | Fase |
|---|---|
| 1 | `Controllo delle attività senza fasce disponibili` |
| 2 | `Controllo dell'occupazione delle risorse` |
| 3 | `Controllo della coerenza dei consigli di classe` |
| 4 | `Controllo dei vincoli delle materie` |
| 5 | **`Controllo dell'insieme di attività non piazzabili`** |

Due pulsanti: `Chiudi` e `Lancia la verifica`. Selezionando una fase, il pannello
destro ne mostra la descrizione.

### Cosa significano le fasi 1 e 5 — e perché sono diverse

Sono i due estremi della stessa domanda, e la distinzione è tecnicamente
importante:

- **Fase 1** è il caso **individuale**: esiste un'attività che, presa da sola, non
  ha *nessuna* collocazione ammissibile. Facile da rilevare (intersezione vuota
  delle disponibilità delle sue risorse) e facile da spiegare all'utente.
- **Fase 5** è il caso **collettivo**: un *insieme* di attività che non entra,
  anche se ciascuna presa singolarmente entrerebbe. È il classico caso «sette
  lezioni che possono stare solo in sei slot»: nessuna è impossibile, l'insieme sì.

🔑 **La fase 5 è la funzione più sofisticata che abbiamo trovato in EDT.** Rilevare
un sottoinsieme infattibile è, in teoria, la ricerca di un *violatore di Hall* — e
si lega direttamente alla diagnostica sui raggruppamenti chiamata
`DiagnosticCliques` (le «cricche» della sezione sotto): la terminologia da teoria
dei grafi non era casuale.

**Per noi.** È esattamente il tipo di risposta che un solver CP-SAT **non** dà
gratis: l'UNSAT core esiste ma è illeggibile. Restituire *«queste 7 lezioni di 3ªA
non possono stare tutte nelle 6 fasce rimaste»* invece di *«infeasible»* è metà
della differenza di UX che vogliamo ottenere. Va previsto nel modello, non aggiunto
dopo.

⚠ La fase 2 è una sola voce in UI, ma internamente si articola nelle **cinque
risorse** (classi, docenti, aule, personale, materiali) — vedi
[risorse.md](risorse.md), dove le sotto-fasi sono elencate per nome.

⚠ La fase 3 riguarda i **consigli di classe**, cioè un altro dominio: conferma che
l'analisi è condivisa fra i moduli, come il resto del motore
([moduli-e-scope.md](moduli-e-scope.md)).

## 🔑🔑 Come EDT presenta una diagnosi — osservato in UI

**Questa è la funzione più preziosa trovata in tutto il reverse engineering.**
Osservata il 2026-07-26 lanciando l'analisi sulla base di esempio, che ha
effettivamente prodotto un problema (fase 4, vincoli delle materie).

La finestra si divide in **quattro riquadri**, e la struttura è la lezione:

### 1. `Enunciato del problema`

Una frase in italiano corrente:

> *"I vincoli della classe non permettono il piazzamento di tutte le attività."*

### 2. `Azioni che permettono di risolvere il problema`

Un elenco di **rimedi**, non di errori:

> - *"Rendere i vincoli delle materie meno vincolanti"*
> - *"Diminuire la durata delle attività"*

### 3. `Dettaglio` — l'aritmetica, esplicita

```
Classe : 1B
Materie: LETTERE
Numero di attività: 6
Durata da piazzare: 10h00
Durata piazzabile:   9h00
» 1h00 non potrà essere piazzata
```

🔑 **EDT quantifica lo scarto.** Non dice «non ci sta»: dice *quanto* non ci sta,
e rispetto a quale capienza. Il verdetto è un numero, verificabile.

### 4. `Soluzione` — il vincolo colpevole, mostrato in loco

Una mini-griglia `Vincolo materia` con le colonne
`Materie A` · `Materia B` · `Incomp.` (`1/2g` `g` `2g`) · `Max ore` (`1/2g` `g`),
contenente **la riga esatta responsabile**: `LETTERE` / `LETTERE`, con la **X rossa**
nella colonna `g`.

Cioè: *"LETTERE è incompatibile con sé stessa nella stessa giornata"* — e quel
singolo vincolo riduce la capienza settimanale da 10h a 9h. È il caso d'uso
dominante già visto nei dati reali (la materia con sé stessa, vedi sotto), qui
mostrato come causa.

Più un pulsante `Visualizza l'elenco delle attività`.

### Le tre forme di diagnosi osservate

L'analisi completa sulla base di esempio ha prodotto **tre problemi**, poi
`Verifica terminata — Rimangono delle incoerenze.` Le tre diagnosi hanno la stessa
struttura a quattro riquadri ma **contenuti di natura crescente**:

#### A — Un vincolo, una risorsa (fase 4)

> `I vincoli della classe non permettono il piazzamento di tutte le attività.`

`Classe: 1B` · `Materie: LETTERE` · 6 attività · 10h00 da piazzare · **9h00
piazzabili** · 1h00 no.
Colpevole: `LETTERE` incompatibile con sé stessa nella giornata.

#### B — Vincoli **incrociati** di due risorse (fase 4)

> `I vincoli incrociati della classe e del docente non permettono il piazzamento di
> tutte le attività.`

`Classe: 1E` · **`Docente: DI MILETO`** · `Materie: MATEMATICA` · 4 attività ·
6h00 da piazzare · 5h00 piazzabili · 1h00 no.

🔑 Qui il riquadro `Soluzione` mostra **due vincoli di famiglie diverse**, affiancati:

| Riquadro | Contenuto |
|---|---|
| `Vincolo materia` | `MATEMAT` / `MATEMAT`, X rossa nella colonna `g` |
| `Giorni e 1/2 giornate libere` | **`DI MILETO`** → `Giornate libere: 2`, `Mezze giornate libere: -` |

Cioè: né l'incompatibilità né il giorno libero sono un problema **da soli**; lo
diventano **insieme**. EDT lo dice e mostra entrambi. E l'elenco dei rimedi si
allunga di conseguenza: si aggiunge `Diminuire i giorni e 1/2 giornate libere`.

#### C — Un **insieme** di attività su un insieme di risorse (fase 5)

Descrizione della fase, letterale:

> *"EDT verifica che le attività che condividono uno stesso insieme di risorse
> possano essere tutte piazzate rispettando le disponibilità incrociate delle
> attività e delle risorse stesse."*

Enunciato:

> `La fascia di disponibilità comune delle attività e delle rispettive risorse non
> permette di piazzare tutte le attività.`

E il `Dettaglio` non nomina una risorsa ma **tutto l'insieme implicato**:

```
DA VINCI, SILVESTRI, HEYWOOD, DUMAS, DELEDDA, MARCONI,
DALAI, PENNETTA, BARICCO, PIANO, EPICURO, 1A, LAB. ARTISTICA

Numero di attività: 25
Durata da piazzare: 33h00
Durata piazzabile:  32h00
» 1h00 non potrà essere piazzata
```

Undici docenti, una classe e **un'aula**, insieme. Nessuna di queste risorse è
sovraccarica da sola: è la **finestra di disponibilità comune** a non bastare.

🔑 **Questo è un violatore di Hall trovato e nominato.** Non il caso banale
dell'attività bloccata: un sottoinsieme di 25 attività la cui unione di vincoli
lascia 32 ore di capienza per 33 di domanda. È la funzione tecnicamente più
difficile del prodotto, ed è anche la più lenta — la barra di avanzamento della
fase 5 procede molto più lentamente delle altre quattro.

I rimedi proposti cambiano di conseguenza: `Diminuire le indisponibilità delle
risorse` · `Diminuire le indisponibilità delle risorse **comuni**` · `Diminuire la
durata delle attività`.

### 🔑 Il riquadro `Soluzione` è operativo, non illustrativo

Non mostra il vincolo: lo **rende modificabile lì**.

- nel caso B, `Giornate libere` è una **tendina** (valore `2`), non un'etichetta;
- nel caso C compare direttamente la **griglia delle indisponibilità**
  (lun–ven × 08h00–18h00) con un selettore di risorsa (`Attività`, a tendina) e i
  radio `Indisponibilità` / `Opzionali`, più un pulsante `?` di aiuto contestuale.

Cioè si diagnostica e si ripara **nella stessa finestra**, poi si preme
`Rilancia la verifica`. Il ciclo diagnosi → correzione → riverifica non richiede di
andare a cercare la risorsa altrove.

**Per noi è un requisito di UI, non un dettaglio.** La distanza fra «ti dico cosa
c'è che non va» e «te lo faccio sistemare qui» è la differenza fra uno strumento
che si usa e uno che si abbandona.

### Le azioni offerte

| Pulsante | Cosa fa |
|---|---|
| **`Estrai le materie, le risorse coinvolte e le attività`** | 🔑 riversa la diagnosi nella **selezione di lavoro** |
| `Ignora e continua la verifica` | passa al problema successivo |
| `Rilancia la verifica` | ricontrolla dopo una correzione |
| `Chiudi` | |

Il primo pulsante è architettura, non comodità: la diagnosi **alimenta `Estrai`**,
che è la primitiva di selezione su cui operano tutte le altre azioni
([moduli-e-scope.md](moduli-e-scope.md)). Diagnostico → seleziono i colpevoli →
agisco su quelli. Il ciclo si chiude.

### ⚠ Correzione a quanto scritto prima in questo file

Avevo concluso che **«EDT non suggerisce quale vincolo allentare»**. È **sbagliato**,
e va corretto qui invece che accanto.

Quella conclusione era stata tratta dal solo pannello `Alleggerimenti`, dove
effettivamente l'utente sceglie a mano fra famiglie di vincoli. Ma
l'**analisi dei vincoli** fa esattamente il contrario: nomina il vincolo
responsabile, ne mostra la riga, quantifica il danno in ore e propone i rimedi in
italiano.

La lettura corretta è che i due strumenti stanno in **momenti diversi**:

| Momento | Strumento | Comportamento |
|---|---|---|
| **prima** del calcolo | `Analisi dei vincoli` | diagnostica **attiva**: trova, nomina, quantifica, suggerisce |
| **dopo** un calcolo fallito | `Alleggerimenti` | rilassamento **passivo**: l'utente sceglie e quantifica il margine |

### Come si chiude

Esauriti i problemi, il pannello destro dice soltanto:

> **`Verifica terminata`**
> `Rimangono delle incoerenze.`

Con `Chiudi` e `Rilancia la verifica`. Nessun riepilogo, nessun conteggio, nessun
elenco delle tre diagnosi viste. ⚠ **È la parte debole dello strumento**: chi ha
scorso dieci problemi non ha modo di rivederli se non rilanciando tutto. Un
riepilogo finale con l'elenco navigabile sarebbe un miglioramento facile e ovvio.

### 🔑 L'analisi è **esatta** — verificato

Il fatto da spiegare era questo: la base di esempio ha **984 attività su 984
piazzate**, eppure l'analisi dichiara che tre ore non sono piazzabili. O l'orario
viola davvero quei vincoli, o il calcolo di capienza è una sovrastima prudenziale.

**Verificato il 2026-07-26** con `Estrai → Estrai le attività che non rispettano i
vincoli`, tutte e dieci le famiglie attive. Risultato:

> **`21 / 984 (38h00 / 1.371h00)`**

e nell'elenco compaiono **entrambe le diagnosi**:

| Diagnosi | Attività estratte |
|---|---|
| A — `1B` / `LETTERE` | `EPICURO Epicuro`, 1B: lunedì 15h00 (2h00), mercoledì 1h00, mercoledì 3h00 |
| B — `1E` / `MATEMATICA` / `DI MILETO` | `DI MILETO Talete`, 1E: lunedì 11h00, lunedì 12h00 |

**Vale la prima lettura: lo strumento è esatto.** L'orario della base demo contiene
davvero lezioni piazzate in violazione dei vincoli — verosimilmente messe a mano, o
piazzate prima che i vincoli fossero aggiunti. EDT lo consente, e mette a
disposizione il comando per ritrovarle.

**Conseguenza per noi.** Un controllo esatto si può presentare come **verdetto**
(«questa istanza è impossibile, ecco perché»), uno prudenziale solo come
avvertimento. EDT si permette il verdetto perché il conto lo regge. Se replichiamo
la funzione, dobbiamo tenere la stessa asticella: un falso allarme distrugge la
fiducia in uno strumento diagnostico molto più in fretta di quanto un vero allarme
la costruisca.

**E un corollario che vale da solo:** un orario **valido non è un invariante** in
EDT. Le violazioni sono uno stato ammesso e interrogabile, non un errore da
impedire. È una scelta di progetto da imitare — vietare a priori significa
costringere l'utente a mentire al sistema.

### Le colonne che rivelano lo stato

Nella lista estratta, le 21 attività irregolari hanno **`S.P.` = 0** e
**`Nr G.` = 0**, mentre le attività regolari mostrano `1` e `1`.

**✅ Confermato il 2026-07-26, e l'inferenza era esatta.** I tooltip letterali:

| Colonna | FR | Tooltip |
|---|---|---|
| `S.P.` | `Nb. P.` | *«Numero di **fasce orarie possibili** per il piazzamento dell'attività **nel rispetto di tutti i vincoli**»* |
| `Nr G.` | `Nb. J.` | *«Numero di **giorni possibili** per l'attività nel rispetto di tutti i vincoli»* |

È **la dimensione del dominio residuo**, ricalcolata contro lo stato corrente
dell'orario: sospendendo una singola attività da un orario pieno, i valori delle
attività vicine si alzano, e si riabbassano appena il buco si richiude. Dettaglio,
misure e implicazioni in [motore-risoluzione.md](motore-risoluzione.md).

**Per la diagnostica**, il punto è questo: ordinando la lista per `S.P.` crescente
si ottiene, *prima* di lanciare qualunque calcolo, l'elenco di **cosa sta per
diventare impiazzabile**. È diagnostica preventiva che non costa nulla, perché il
solver quel numero lo calcola comunque durante la propagazione.

Altre colonne lette nella stessa schermata: `P.P.` vale `F` su tutte le righe —
confermato **`Fascia fissa`**, la colonna è `Fractionnable` = *Proprietà di
Piazzamento* (vedi [moduli-e-scope.md](moduli-e-scope.md) e
[tempo-e-calendario.md](tempo-e-calendario.md));
`Freq.` vale `S`, cioè il codice di periodicità **settimanale** confermato dalla
tabella delle alternanze; `Sede` assume i tre valori `Principale`, `Succ. 1`,
`Succ. 2`, coerenti con `NBSITES = 3`.

### Perché conta per noi, in concreto

Questa è la differenza fra un solver e un prodotto.

Un modello CP-SAT che riceve queste stesse 6 attività di LETTERE su 1B risponde
`INFEASIBLE`. Volendo si estrae un UNSAT core, che è un insieme di vincoli
numerati — illeggibile per un vicepreside. EDT invece dice: *sei attività, dieci
ore da piazzare, nove piazzabili, ne avanza una, e la colpa è di questa riga qui;
puoi allentarla o accorciare le lezioni.*

E il punto tecnico è che **non serve un solver per dirlo**. È un conteggio di
capienza: date le ore richieste e i vincoli di distribuzione, quante ne entrano al
massimo? Si calcola in millisecondi, prima e indipendentemente dal piazzamento.

🔑 **Da progettare fin dall'inizio come componente a sé**, non come interpretazione
a posteriori dell'output del solver. È l'unico modo per ottenere messaggi di questa
qualità.

### La tabella di coerenza

Distinta dall'analisi, c'è `FicCoherenceVariable`: una tabella che incrocia
**risorse × famiglie di vincolo**. Colonne: `Massimo di ore`,
`Mezze giornate di lavoro`, `Mezze giornate libere`, `Giornate libere`,
`Gestione Entrate / Uscite`, `Pesi didattici`, `Vincolo materia`,
`Rispettare gli intervalli`, con `Totale della settimana` e `Totale ciclo`.

⚠ Da chiarire se sia la vista dei risultati dell'analisi o uno strumento separato.

## Cosa NON fa EDT

Il pannello `Alleggerimenti`, **da solo**, non suggerisce nulla: è una lista neutra
che l'utente esplora a mano quantificando il margine per ciascuna famiglia (vedi
[motore-risoluzione.md](motore-risoluzione.md)). Non risulta che si pre-selezioni in
base allo scarto appena calcolato.

Ma questo non significa che EDT non diagnostichi: l'`Analisi dei vincoli` lo fa,
eccome — vedi sopra. La lacuna reale è più stretta: **manca il ponte fra il
fallimento di un calcolo e la scelta del rilassamento**. Chi ha appena visto 40
attività scartate deve comunque indovinare da sé quali vincoli allentare.

**Lì resta l'occasione di prodotto.** Le causali sono già nominate e contabili: da
lì a ordinare i vincoli per numero di fallimenti causati il passo è breve, e nessuno
lo fa.

## Cosa resta da verificare in UI

1. Il tooltip della colonna **`S.P.`**, per confermare che sia «spazi possibili».
2. La finestra `Piazza le attività scartate`: disposizione di metodo, livello,
   contatori, e da dove si apre il pannello `Alleggerimenti`.
2. Se il pannello `Alleggerimenti` **pre-seleziona** vincoli in base allo scarto
   reale — chiude la domanda "EDT suggerisce?".
3. Il trascinamento con e senza `modalità diagnostica`: differenza visiva reale,
   tooltip, elenco causali.
4. La griglia del risolutore passo-passo: esiste un **terzo colore** per le
   collocazioni impossibili, o semplicemente non sono cliccabili?
5. Se `Non piazzata` e `Scartata` siano visivamente distinti nella lista attività.
6. In che punto del flusso compare la diagnostica sui raggruppamenti: prima,
   durante o dopo il calcolo.
7. ⚠ Una stranezza di traduzione: la chiave `FicMenusMenuVerrous` è resa
   `&Piazzamento` in italiano ma `&Verrous` / `&Locks` in francese e inglese. Da
   controllare in UI se il sottomenu italiano riguarda davvero i **blocchi**: se sì
   è un errore di traduzione del prodotto, e va segnalato come tale nel glossario.
