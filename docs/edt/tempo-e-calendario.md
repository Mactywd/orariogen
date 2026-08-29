# EDT — Il modello del tempo

> Tre fonti. Lo **schema XSD** `Partenaire_Index` V4.6 (📦, livello 1 — la più
> autorevole), le **etichette di interfaccia** dai binari (📦) e gli header
> `<CARTEIDENTITE>` delle due basi. Vedi [ADR-009](../decisioni.md).
>
> **La finestra di configurazione della griglia è osservata dal 2026-08-29**
> (§ *La finestra, osservata*). Il resto del documento — intervalli, periodi,
> periodicità, sedi — resta ricostruito dalle tre fonti, con i testi letterali a
> supporto.

## Perché serve

Il nostro prototipo assume implicitamente: cinque giorni, sei ore uguali, una
settimana che si ripete identica per tutto l'anno. **Nessuna delle tre ipotesi
regge** nel modello di EDT, e due di esse non reggono neanche in una scuola
italiana media. Questo documento dice quanto è profonda la tana del coniglio, così
da poter decidere consapevolmente cosa semplificare.

## La griglia: giorni × fasce × posizioni

Dichiarazione formale, dallo XSD:

```xml
<xs:element name="GrilleHoraire">
  <xs:attribute name="NombreJoursParCycle"      type="xs:unsignedShort" use="required"/>
  <xs:attribute name="NombreSequencesParJour"   type="xs:unsignedShort" use="required"/>
  <xs:attribute name="NombrePlacesParSequence"  type="xs:unsignedShort" use="required"/>
  <!-- PlacesParJour → Place[] : @Numero (0-based), @LibelleHeureDebut, @LibelleHeureFin -->
</xs:element>
```

Con l'annotazione dell'autore: *"Le numéro de la première place du jour est égal à
0"*. Questo **conferma formalmente** la codifica `place = giorno × 10 + rango` già
dedotta dal formato binario: 10 è semplicemente il `NombreSequencesParJour` del caso
tipico.

Tre livelli, non due:

| Livello | Attributo | Cos'è |
|---|---|---|
| **giorno** | `NombreJoursParCycle` | può eccedere 5 o 7 — il ciclo non è la settimana |
| **fascia** (FR *séquence*) | `NombreSequencesParJour` | l'"ora di lezione" |
| **posizione** | `NombrePlacesParSequence` | suddivisione sub-oraria |

Testo del prodotto per l'esempio canonico: *"10 fasce orarie da 60 minuti
corrispondono a una giornata compresa tra le 8.00 e le 18.00."*

Vincoli di configurazione dichiarati: la giornata non può superare le 24 ore
(*"numero di fasce orarie × durata di un'unità"*) e c'è un tetto parametrico al
numero di fasce.

### 👁 La finestra, osservata

`File → Strumenti → Cambia i parametri della griglia oraria`, sulla base demo
(2026-08-29). Titolo: *«Conversione della griglia oraria della base dati»* — la
stessa finestra che il wizard mostra alla creazione, riaperta su una base viva.

| Campo | Valore sulla demo | Note |
|---|---|---|
| `Modificate il primo giorno della settimana` | **lunedì** | menu a tendina: il ciclo non parte per forza da lunedì |
| `Modificate i vostri giorni lavorativi (in bianco)` | Lun–Ven bianchi, **Sab e Dom grigi** | sette caselle cliccabili |
| `Numero di fasce orarie` | **10 fasce orarie** | ⚠ **campo in sola lettura** — vedi sotto |
| `Durata della fascia oraria` | **60 Minuti** | modificabile (matita) |
| `Durata totale di una giornata` | **10h00** | derivato, non inseribile |
| `Suddivisione della fascia oraria` | **Nessuno** | radio: in 2 / 3 / 4 / 6 / 12 / Nessuno |
| `Durata di ogni frazione` | **1h00** | derivato dai due sopra |

🔑 **Il numero di fasce non si scrive: si aggiunge o si toglie a un'estremità.** Il
campo è grigio, e sotto ci sono due righe gemelle — `Aggiungi`/`Togli` *N* fasce
**all'inizio della giornata**, `Aggiungi`/`Togli` *N* fasce **alla fine della
giornata**. «Passare da 10 a 8 fasce» non è quindi una domanda ben posta qui:
bisogna dire **da quale capo**, e il perché è l'allineamento — il rango di una
fascia esistente cambia solo se se ne aggiunge una *prima* di essa.

⚠ Ma **ai bordi non è l'unico modo**: il pannello `Parametri → Istituto → Orari`
porta un pulsante `Inserisci / cancella una fascia oraria` (👁 2026-08-29), che è
un'operazione posizionale. Le due strade coesistono, e quale sia la differenza —
se non che una è di conversione e l'altra di manutenzione — **non è osservato**.

⚠ **Il ciclo pluri-settimanale non è raggiungibile da questa finestra.** I giorni
mostrati sono i sette della settimana e nient'altro; `NombreJoursParCycle > 7` — che
lo XSD ammette e le stringhe chiamano `Ciclo personalizzato` — vive quindi altrove,
verosimilmente nel solo wizard di creazione della base. Sulla demo il ciclo **è** la
settimana, cinque giorni.

E la nota che il prodotto stampa in chiaro dentro la finestra, che era
[INFERENZA] fino a oggi:

> *«La durata della fascia oraria serve per il calcolo dei servizi dei docenti. 10
> fasce orarie da 60 minuti corrispondono a una giornata compresa tra le 8.00 e le
> 18.00.»*

**Per noi**, la demo è `5 × 10 × 1` a 60 minuti — e questo **chiude per
osservazione** la codifica `place = giorno × 10 + rango` dedotta dal formato
binario: il 10 è davvero `NombreSequencesParJour`, letto nella finestra che lo
imposta.

### Le suddivisioni sub-orarie

Una fascia si divide in **2, 3, 4, 6 o 12** parti uguali — con fasce da 60 minuti:
30, 20, 15, 10, 5 minuti. **Confermato in UI** (2026-08-29): sono sei radio in
esclusione, e il sesto è `Nessuno`, che è il valore della demo. Non è quindi un
elenco aperto: `NombrePlacesParSequence` prende **sei valori e basta**.

> *"Una suddivisione in 2 crea 2 frazioni orarie da 30 min. che permettono la
> creazione di attività da 30 minuti, 1h, 1h30, 2h00, 2h30..."*

E l'avvertimento del prodotto, che vale anche per noi:

> *"La suddivisione in %d rende più complesso il calcolo dell'orario, utilizzatela
> solo se dovete gestire attività di %d minuti."*

Coerente con lo XSD, dove la durata dell'attività è un `choice` fra
`DureeMinutes` (intero) e **`DureeSequences` (decimale)**.

**Per noi.** La granularità dello slot va tenuta **parametrica**, non cablata a
un'ora. Ma il default resta 1 fascia = 1 ora, e la suddivisione è una feature di
secondo giro — con l'avallo del produttore, che la sconsiglia.

### 🔑 Due nozioni di «ora», da non confondere

> *"È possibile personalizzare la durata effettiva delle attività (ad esempio 55
> minuti) modificando le etichette dell'orario una volta creata la base dati"*

Esistono quindi:

- la **fascia di calcolo**, unità del motore **e** unità di conteggio delle ore di
  servizio del docente — scritto nella finestra stessa, 👁 osservato: *«La durata
  della fascia oraria serve per il calcolo dei servizi dei docenti»*;
- l'**etichetta oraria visualizzata**, personalizzabile (55 min, orari sfalsati),
  con una validazione di coerenza cronologica — 👁 e sono davvero **due campi in
  due finestre diverse**, entrambi a 60 sulla demo (§ *Orari / Fasce orarie*).

⚠ Cambiare la durata di fascia **ricalcola i monte ore**. Non è un parametro
grafico.

## Intervalli, mezza giornata, mensa

### Gli intervalli (FR *récréations*)

Sono un passo dedicato del wizard, non fasce come le altre. A livello di vincolo
compaiono come flag sull'attività: **`Rispetta gli intervalli`** — cioè l'attività
non può essere spezzata a cavallo di una pausa.

Sono anche l'**ancora temporale dei cambi di sede** (vedi sotto).

**🔑 Chiuso: è un separatore, non una `Place`.** Era aperto se l'intervallo
consumasse un rango della griglia. Non lo consuma. La tabella `RECREATION` ha **due
soli record** — etichetta più indice di rango (`Intervallo del mattino` = 2,
`Intervallo del pomeriggio` = 4) — mentre le dieci sequenze coprono 08:00–18:00.

Prova sui dati: i ranghi **2 e 4 sono fra i più occupati** della base (168 e 162
attività). Se l'intervallo consumasse un rango, sarebbero vuoti. L'unico rango
vuoto è il **6** — che avevamo attribuito «alla mensa» e che l'osservazione
precisa: è la **fascia di pausa della mezza giornata**, la riga senza nome fra
`M6` e `P1`. La mensa è ciò che ci si svolge dentro, e sulla demo non ha nemmeno
un turno attivo. Le stringhe concordano: le attività stanno «**a
cavallo** dell'intervallo», e l'utente «sposta le **linee gialle**» — è un confine
disegnato fra due ranghi.

**👁 Confermato in UI il 2026-08-29** (`Parametri → Istituto → Orari`, passo 2),
e la conferma è più stretta di quanto sperassi. Il pannello elenca due righe —
`Intervallo del mattino` e `Intervallo del pomeriggio` — con tre colonne: un
segno di spunta (attivo/no), il **`Nr. fasce orarie dopo l'ultimo intervallo`** e
le **`Classi`**.

| | Nome | Nr. fasce dopo l'ultimo | Classi |
|---|---|---|---|
| ✔ | Intervallo del mattino | **2** | Tutte |
| ✔ | Intervallo del pomeriggio | **2** | Tutte |

🔑 **La UI mostra il salto, il file memorizza il rango.** `2` e `2` cumulano a 2 e
4, che sono esattamente i due indici trovati nella tabella `RECREATION`. Le due
letture — binario e interfaccia — combaciano su una trasformazione, non su un
numero, il che è una verifica molto più forte di una coincidenza.

E sulla griglia a destra le linee sono **gialle** e stanno **fra** due righe, non
al posto di una: il contrasto con la pausa di mezza giornata, che è una riga
intera senza nome, si vede nella stessa immagine. È la differenza fra un confine e
una `Place`, disegnata.

Due cose nuove, che le stringhe non davano:

- gli intervalli hanno un **orario proprio** (§ *Orari / Fasce orarie*): sulla demo
  09:50–10:00 e 11:50–12:00, cioè **dieci minuti ritagliati prima del confine**.
  Non allungano la giornata — `M6` finisce lo stesso alle 14:00 — quindi mangiano
  l'etichetta della fascia precedente e lasciano intatta la fascia di calcolo.
  Ancora le due nozioni di «ora»;
- la colonna **`Classi`** (sulla demo `Tutte`): un intervallo può valere per un
  **sottoinsieme di classi**. Non è l'eccezione al vincolo — quella è
  `NONRESPECTCLASSERECREATION` — è l'intervallo stesso che può non esistere per
  tutti.

Il vincolo che ne discende è però **hard**, con eccezione per classe
(`NONRESPECTCLASSERECREATION`) — vedi [vincoli.md](vincoli.md).

⚠ In italiano «intervallo» traduce **due** parole francesi diverse: `récréation`
(questa) e `interclasse`. Vedi [glossario-it-fr.md](glossario-it-fr.md).

### 👁 La linea di mezza giornata

Osservata il 2026-08-29 in `Parametri della base dati → Istituto → Orari`, che è
una procedura in **tre passi**: `1 Mezza giornata`, `2 Intervalli`,
`3 Orari / Fasce orarie`.

Due modalità **alternative**:

| Modalità | |
|---|---|
| `Giornata continua` | *«La giornata continua disattiva la mensa»* |
| `2 mezze giornate separate da una pausa` | ← selezionata sulla demo |

🔑 **La pausa non è un confine: è un blocco di fasce, e consuma la giornata.** La
demo dichiara `della mattina (M): 6`, `della pausa: 1`, `del pomeriggio (P): 3` — e
**6 + 1 + 3 = 10**, cioè esattamente il `NombreSequencesParJour` della griglia. Le
righe a destra si chiamano `M1…M6`, poi una riga **senza nome** fra due linee
verdi, poi `P1…P3`. La fascia di pausa esiste nella griglia e non è piazzabile:
è la «fascia di sistema» che il modello nostro deve saper rappresentare.

La linea si sposta **trascinando le linee verdi** sulla griglia — *«Spostate le
linee verdi sulla griglia sottostante per definire il numero di fasce orarie di
ogni mezza giornata»* — quindi si definisce in **numero di fasce**, mai in orario
assoluto. Le linee attraversano tutti i giorni insieme: la divisione è **globale**,
non per giorno.

E la casella spuntata sulla demo:

> ☑ *«Dopo la pausa della mezza giornata, riprendi all'inizio dell'ora successiva.»*

🔑 È **la stessa discontinuità** che il nostro export iCal già gestisce: al confine
di mezza giornata l'orologio salta invece di proseguire, quindi un'attività a
cavallo non è **un** evento. Lì l'avevamo dedotta dalle `SlotLabel`; qui è un
parametro dichiarato, con una casella per accenderlo.

⚠ **E c'è una maschera che non abbiamo.** In fondo alla griglia, una casella per
giorno (`Lun. Mar. Mer. Giov. Ven.`, tutte vuote sulla demo) con la legenda:

> *«I giorni spuntati saranno ignorati durante il calcolo delle giornate libere.»*

Non è la maschera dei giorni lavorativi — quella sta nella griglia oraria e
toglie il giorno dalla base. Questa è un **secondo** filtro, che lascia il giorno
lavorativo ma lo esclude dal conteggio di `giornate libere` / `mezze giornate
libere`. I nostri `FreeGuaranteedChecker` e `FreeGuaranteedBuilder` contano su
tutti i `days_per_cycle` senza eccezioni: → fra i **debiti dichiarati** di
[todo.md](../todo.md).

🔑 **La mezza giornata è l'unità di misura di un'intera famiglia di vincoli**:
`Massimo di mezze giornate di lavoro`, `mezze giornate libere garantite`,
`Lavorare solo mezza giornata al giorno` — su docenti **e** classi
([classi.md](classi.md), [vincoli.md](vincoli.md)). Non è un dettaglio di
presentazione: è un asse del modello.

### La mensa è un vincolo hard

Prova diretta: nella finestra di ricerca di una fascia libera, la mensa è elencata
**nella stessa lista** di indisponibilità e sedi sotto l'intestazione
`Ignora i seguenti vincoli:`

| Opzione | |
|---|---|
| `Mensa` | `Demi-pension` |
| `Indisponibilità` | `Indisponibilités` |
| `Mezze giornate non lavorative` | `Demi-journées non travaillées` |
| `Sedi` | `Sites` |

E il piazzamento automatico mostra lo stato `Mensa attiva` / `Mensa non attiva` fra
i suoi indicatori di sistema.

#### 👁 Ed è più grosso di un vincolo: è un sotto-sistema

Osservata il 2026-08-29 la scheda `Parametri → Istituto → Mensa`. La mensa è una
**finestra oraria** — `☑ Attivata dalle 14h00 alle 15h00` — con una **maschera per
giorno** propria (sulla demo `Lun. Mer. Giov. Ven.`, con `Mar.` fuori), e dentro
quella finestra si definiscono dei **turni**:

- `Aggiungi un turno`, ciascuno con la sua sotto-finestra dentro 14h00–15h00,
  disegnata come una barra;
- ogni turno destinato a `Classi` (con un `N. Max.`) e/o a `Docenti`;
- `Gestione dei turni destinati agli alunni`: ☑ `Equilibra automaticamente`,
  ☐ `Gestisci un numero massimo di classi`, con `Statistiche di ripartizione`.

Sulla demo: quattro turni definiti ma `Nessun turno mensa attivo`.

🔑 Non è quindi «un'ora bloccata»: è un **problema di assegnazione a sé**, con
capienze e bilanciamento — la stessa forma dell'assegnazione delle aule, che da
noi è già una seconda fase.

**Per noi:** in una scuola italiana la pausa mensa quasi non esiste (tempo pieno a
parte), e questa osservazione **rafforza** il *fuori scope v1* invece di
indebolirlo: entrarci vorrebbe dire un terzo modello di ottimizzazione. Ciò che
serve comunque è il meccanismo generale «fascia di sistema che blocca il
piazzamento», che le mezze giornate non lavorative usano lo stesso — e che la
**fascia di pausa** della mezza giornata (§ *La linea di mezza giornata*) rende
necessario a prescindere dalla mensa.

### 👁 Orari / Fasce orarie — dove nascono le `SlotLabel`

Passo 3 della stessa procedura (👁 2026-08-29). In alto un radio,
`Definizione delle etichette relative a: ● Orari  ○ Fasce orarie`: le fasce si
possono etichettare con l'**orologio** oppure con il **rango** («1ª ora»).

`Creazione automatica degli orari` prende **tre** numeri:

| Campo | Demo |
|---|---|
| `Primo orario sulla griglia` | **08:00** |
| `Durata reale delle fasce orarie` | **60** Minuti |
| `Durata tra le fasce orarie` | **0** Minuti |

🔑 **`Durata reale` non è la durata della fascia di calcolo, ed è in un altro
pannello.** Il valore che serve al motore e al conteggio dei servizi si imposta in
`File → Strumenti → Cambia i parametri della griglia oraria`; questo genera solo
le **etichette**. È il campo che la guida evocava con l'esempio dei «55 minuti», e
qui si vede che sono davvero due caselle in due finestre diverse. E `Durata tra le
fasce orarie` aggiunge la terza possibilità: **etichette con un buco fra l'una e
l'altra**, senza che il modello di calcolo lo sappia.

Sotto, i due blocchi che riprendono gli altri due passi con l'orologio invece che
con i conteggi — `Mezza giornata` 14:00 → 15:00 (che è anche la finestra della
mensa) e `Intervallo` con i due orari sopra. Poi `Valori predefiniti` e **`Crea
gli orari`**: le etichette sono **generate**, e `Personalizza gli orari` permette
poi di riscriverle a mano una per una.

**Per noi.** È esattamente il nostro `SlotLabel`, e ne conferma il ruolo: il
generatore automatico è `primo_orario + rango × (durata_reale + durata_fra)`, e
tutto il resto è personalizzazione. L'export iCal fa la cosa giusta a leggere le
etichette invece di `slot_minutes` — con `Durata tra le fasce orarie > 0` le due
grandezze **divergono per costruzione**, non per un caso limite.

## Il calendario

Dallo XSD, tre soli campi:

```xml
<xs:element name="AnneeScolaire">
  <xs:attribute name="DateDebut"              type="xs:date" use="required"/>
  <xs:attribute name="DateFin"                type="xs:date" use="required"/>
  <xs:attribute name="DatePremierJourSemaine1" type="xs:date" use="required"/>
</xs:element>
```

`DatePremierJourSemaine1` **ancora il ciclo al calendario reale**: è da lì che si
srotolano le settimane numerate.

I festivi si inseriscono cliccando su un calendario (*"Cliccate su un giorno o
selezionate più giorni tenendo premuto per renderli festivi"*), con anche un
`Calcola i giorni festivi` automatico. Rendendo festivo un giorno, le attività già
piazzate lì vengono spostate, con l'opzione *"Conserva le attività spostate o
riportate su dei giorni lavorativi"*.

Esiste un **blocco per singola settimana o ciclo**: *"Solamente le vacanze e i
giorni festivi al di fuori dei cicli bloccati possono essere modificati"*.

## 🔑 I periodi — e le attività che non durano tutto l'anno

Un **decoupage** è una partizione dell'anno; l'"anno intero" è il caso degenere.
Possono coesistere **più suddivisioni** (trimestri *e* quadrimestri), una delle
quali è quella di default: *"quella in prima posizione sarà usata di default durante
la creazione delle classi"*.

Ogni periodo ha: data di inizio, data di fine, una **periodicità propria**, un
flag di blocco (`P.Bloc.`), e i calcolati `Numero di settimane lavorative` /
`Numero di cicli lavorativi`. I periodi si possono **fondere** e **dissociare**,
con un vincolo: *"Per riunire dei periodi, è necessario che le loro attività siano
identiche"*.

E la prova che un'attività può non essere annuale:

> *"Per poter cancellare questa suddivisione, dovete rendere annuali le attività che
> avete definito su una parte di questa suddivisione"*

L'attività dichiara esplicitamente `Periodi dell'attività` (`PeriodeDuCours`).

### Fascia fissa / fascia variabile

| Modo | Spiegazione letterale |
|---|---|
| `Fascia fissa` | *"L'attività si svolge tutte le settimane nella stessa collocazione"* |
| `Fascia fissa (ciclo)` | *"L'attività si svolge in tutti i cicli nella stessa collocazione"* |
| **`Fascia variabile`** | *"EDT può modificare la collocazione dell'attività a seconda dei periodi"* |

È una **proprietà di piazzamento dichiarata alla creazione dell'attività**, non un
effetto collaterale del solver.

🔑 **Implicazione forte per il modello.** Una lezione non ha *una* collocazione: ne
ha una **per periodo**. La variabile di decisione del solver non è `slot[attività]`
ma `slot[attività, periodo]`, con un vincolo di uguaglianza fra periodi quando
l'attività è dichiarata fissa. Ignorarlo significa non poter rappresentare un orario
che cambia al secondo quadrimestre — cosa ordinaria in Italia.

## La periodicità

### Non si chiamano «settimana A» e «settimana B»

⚠ In 69 888 stringhe **non esiste alcuna etichetta «Settimana A/B»**. La
nomenclatura del prodotto è:

| Codice IT | Codice FR | Significato |
|---|---|---|
| `S` | `H` | ogni settimana (*hebdomadaire*) |
| `Q` | `Q` | quindicinale generico |
| **`Q1` / `Q2`** | `Q1` / `Q2` | prima / seconda quindicina — l'equivalente di «A/B» |
| `TC` | `TC` | tutti i cicli |
| `C` · `C1` · `C2` | idem | ciclo alterno, primo / secondo |

Da non introdurre «settimana A/B» nel [glossario](glossario-it-fr.md): è
terminologia nostra, non del prodotto.

### Il modello è numeratore/denominatore

Le periodicità personalizzate si definiscono con una `Quantità` (FR `Numérateur`),
vincolata: *"La quantità non può essere superiore al numero di settimane
nell'anno"* — il denominatore implicito è il numero di settimane (o cicli)
dell'anno.

🔑 **Trimestri e quadrimestri sono codificati con lo stesso meccanismo**:
*"La modifica del numero di settimane dell'anno scolastico comporta l'aggiornamento
delle quantità delle periodicità predefinite (S, Q, trimestrale e quadrimestrale)"*.
Non sono un concetto a parte.

Due modalità automatiche:

- *"la periodicità sarà calcolata in funzione del numero di settimane effettive
  dell'attività"*
- *"la periodicità sarà calcolata in funzione del periodo e della frequenza
  dell'attività"*

### Le quattro frequenze dell'attività

`Attività settimanale` · `Attività regolare` · `Attività a cicli alternati` ·
`Attività quindicinale`.

### I «preferiti» di settimane

Meccanismo indipendente: `Crea un preferito che raggruppa delle settimane` /
`... dei cicli`. Una selezione arbitraria e nominata di settimane, per operazioni
in blocco.

È plausibilmente ciò che sta dietro la **maschera di settimane a bit** già osservata
nel formato file: una selezione libera si codifica naturalmente a bit, non come
frazione.

## 🔑 Gli `Amenagement` — l'eccezione puntuale

EDT distingue nettamente **due strati**:

| Strato | Cos'è |
|---|---|
| **orario annuale** | la collocazione strutturale, valida secondo la periodicità dell'attività |
| **`Amenagement`** | *"una modifica dell'orario per settimana"* — un'eccezione su **una singola settimana o ciclo** |

Il secondo sovrascrive il primo senza cambiare la definizione dell'attività. E il
primo può distruggere il secondo: *"Piazzamento eseguito con successo ma è stato
necessario cancellare %d modifiche dell'orario per settimana"*. Anche le modifiche
alla griglia li cancellano.

**Non è un caso limite.** Nella base demo, a regime: `NBAMENAGEMENTS = 141` su
`NBCOURS = 984`. Circa un'eccezione ogni sette attività.

**Per noi, molto rilevante.** È esattamente il livello a cui vive una sostituzione o
uno spostamento puntuale — il dominio del SaaS già in produzione.

### 🔑 Chiuso: è la stessa struttura della sostituzione — e non è un layer

Era aperto se `Amenagement` e sostituzione fossero la stessa tabella. **Lo sono**, e
la risposta corregge anche il modo in cui avevo descritto l'`Amenagement`.

Non è un «layer separato sovrapposto». È **una riga di `COURS`** come tutte le
altre, distinta solo da due cose: il byte di **natura** (offset 8) e una **maschera
delle settimane con un solo bit acceso**. Le 141 attività di natura 2 sono
esattamente le `NBAMENAGEMENTS` dichiarate nell'header.

E i sostituti di `RELATIONCOURSSUBSTITUT` sono **esattamente** quelle stesse nature:
una supplenza è la stessa lezione, stessa classe, stessa aula, **una sola
settimana**, docente diverso — più `ANNULATIONCOURS` che sopprime l'occorrenza
annuale. Verifica completa sui 161 record in
[formato-file.md](formato-file.md).

**Quindi la separazione da adottare non è «ricorrenza + eccezione datata», ma una
sola entità attività con una maschera temporale.** L'eccezione è il caso limite
della ricorrenza, non un'entità diversa. Vedi [ADR-014](../decisioni.md).

## Le sedi e il tempo di spostamento

Esiste sempre una sede `Principale`, non cancellabile. Le `Opzioni di trasferimento
di sede` sono configurate separatamente per **classi** e per **docenti/personale**:

🔑 **La durata è per coppia di sedi e orientata.** Era aperto se fosse un parametro
globale: non lo è. La griglia ha le colonne `Sede A` · `Sede B` · **`Verso`** ·
`Durata`, quindi A→B e B→A possono costare diverso — il che è realistico (salita,
traffico, senso unico) e va replicato: una matrice, non uno scalare.

| Leva | Dettaglio |
|---|---|
| `Durata` | il tempo di spostamento, **per coppia orientata di sedi** |
| `Nelle pause` | il cambio può essere confinato alle pause/intervalli |
| `Numero massimo di cambi di sede` | `per giorno` · `per settimana` · `per ciclo` |

Con una sottigliezza dichiarata: *"Ignorare la durata del cambio di sede per gli
spostamenti 'durante le pause' e 'durante gli intervalli' (In caso di
alleggerimento, la durata viene considerata per gli spostamenti 'in qualsiasi
momento')"* — se il cambio sta dentro una pausa, la durata non consuma tempo di
lezione.

E un caso limite che diventa hard: *"Nessun intervallo è attivo: il cambio tra queste
sedi sarà vietato"*.

⚠ Lo XSD porta solo `Ident`, `Nom`, `Couleur` per la sede: **la durata di
trasferimento non è un dato di scambio**, è configurazione interna del motore.
Coerente con [schema-scambio.md](schema-scambio.md): lo XSD non trasporta vincoli.

## Le due basi a confronto

| | `Esempio.edt` (demo, risolta) | `example_2.edt` (Fermi) |
|---|---|---|
| `NBSITES` | 3 | 1 |
| `NBSALLES` | 18 | **0** |
| `NBPARTIES` | 187 | 0 |
| `NBGROUPES` | 3 | 0 |
| `NBCOURS` | 984 | 284 |
| `NBCOURSPLACES` | 984 | 0 |
| `NBAMENAGEMENTS` | **141** | 0 |

Nota: l'header **non contiene nulla sulla griglia, i periodi o le periodicità**. La
carta d'identità riassume solo conteggi di entità.

## Implicazioni per il nostro modello

1. **Slot parametrico**, non "l'ora". `giorni_per_ciclo × fasce × suddivisione`.
   Default 5 × 6 × 1, ma la struttura deve reggere altro.
2. **Il ciclo non è la settimana.** Tenere separati "settimana di calendario" e
   "posizione nel ciclo" fin dallo schema, anche se in v1 coincidono. ⚠ Nella
   finestra di conversione (👁 2026-08-29) il ciclo pluri-settimanale **non
   compare**: lo XSD lo ammette, la UI corrente lo mostra solo alla creazione.
3. **Collocazione per periodo**, con vincolo di uguaglianza se l'attività è fissa.
   È la scelta strutturale più costosa da rimandare.
4. **Eccezioni datate come layer separato** dalla ricorrenza. Aggancio naturale al
   modulo sostituzioni.
5. La **mezza giornata** è un'entità di prima classe: molti vincoli la usano come
   unità.
6. Mensa e sedi distaccate sono candidati onesti a *fuori scope v1*, ma da
   dichiarare.

## Cosa resta da verificare in UI

- [ ] **`Aree mobile`** (FR *Espaces mobiles*): citate una sola volta, senza
      contesto. → `Parametri → Orari`
- [ ] Dove si imposta il **`Ciclo personalizzato`** (`NombreJoursParCycle > 7`):
      **non** è nella finestra di conversione della griglia (👁 2026-08-29).
- [x] ~~Se un **intervallo** occupi una `Place` propria o sia un confine fra
      fasce.~~ **Confine** — chiuso sui dati il 2026-07-26, 👁 confermato in UI il
      2026-08-29 (linee gialle *fra* le righe, contro la riga intera della pausa).
- [ ] Se il **tempo di spostamento fra sedi** sia globale o per coppia di sedi (il
      campo `Verso` suggerisce che possa essere direzionale).
- [ ] Se esistano periodicità reali con denominatore **> 2** (oltre Q1/Q2).
- [ ] Se `Amenagement` e sostituzione siano la **stessa tabella**.
- [ ] Se `DureeSequences` sia mai davvero non intero in un file di scambio reale.
