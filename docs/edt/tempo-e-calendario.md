# EDT — Il modello del tempo

> Tre fonti. Lo **schema XSD** `Partenaire_Index` V4.6 (📦, livello 1 — la più
> autorevole), le **etichette di interfaccia** dai binari (📦) e gli header
> `<CARTEIDENTITE>` delle due basi. Vedi [ADR-009](../decisioni.md).
>
> **La configurazione oraria non è mai stata osservata in UI.** Quello che segue è
> il modello ricostruito, con i testi letterali a supporto.

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

### Le suddivisioni sub-orarie

Una fascia si divide in **2, 3, 4, 6 o 12** parti uguali — con fasce da 60 minuti:
30, 20, 15, 10, 5 minuti.

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
  servizio del docente (*"Mantenere la durata predefinita di 60 minuti se una fascia
  oraria corrisponde a un'ora di servizio per i vostri docenti"*);
- l'**etichetta oraria visualizzata**, personalizzabile (55 min, orari sfalsati),
  con una validazione di coerenza cronologica.

⚠ Cambiare la durata di fascia **ricalcola i monte ore**. Non è un parametro
grafico.

## Intervalli, mezza giornata, mensa

### Gli intervalli (FR *récréations*)

Sono un passo dedicato del wizard, non fasce come le altre. A livello di vincolo
compaiono come flag sull'attività: **`Rispetta gli intervalli`** — cioè l'attività
non può essere spezzata a cavallo di una pausa.

Sono anche l'**ancora temporale dei cambi di sede** (vedi sotto).

⚠ Da verificare: se un intervallo occupi una `Place` propria o sia solo un confine
fra due fasce adiacenti. Lo XSD non ha un concetto di *récréation*.

### La linea di mezza giornata

Due modalità **alternative**, dichiarate esplicitamente:

| Modalità | Testo |
|---|---|
| `Giornata continua` | *"La giornata continua disattiva la mensa"* |
| `Giornata con una pausa delimitata da` | `l'ora di fine mattinata:` + `e l'ora di inizio del pomeriggio:` |

La linea si definisce **in numero di fasce**, non in orario assoluto:
*"Spostare gli indicatori viola sulla griglia sottostante per definire il numero di
fasce orarie di ogni mezza giornata"*. Con un'opzione di arrotondamento:
*"Dopo la pausa della mezza giornata, riprendi all'inizio dell'ora successiva"*.

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

**Per noi:** in una scuola italiana la pausa mensa quasi non esiste (tempo pieno a
parte). È un candidato ragionevole a *fuori scope v1*, ma va dichiarato, non
dimenticato — e il meccanismo generale «fascia di sistema che blocca il piazzamento»
serve comunque per le mezze giornate non lavorative.

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
uno spostamento puntuale — il dominio del SaaS già in produzione. EDT lo modella
come **layer separato sovrapposto**, non come modifica della ricorrenza. Vale la
pena adottare la stessa separazione: `attività` (ricorrente) + `eccezione`
(datata). ⚠ Da chiarire se in EDT `Amenagement` e sostituzione siano la stessa
tabella.

## Le sedi e il tempo di spostamento

Esiste sempre una sede `Principale`, non cancellabile. Le `Opzioni di trasferimento
di sede` sono configurate separatamente per **classi** e per **docenti/personale**:

| Leva | Dettaglio |
|---|---|
| `Durata` | il tempo di spostamento, parametrizzato |
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
   "posizione nel ciclo" fin dallo schema, anche se in v1 coincidono.
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
- [ ] Se un **intervallo** occupi una `Place` propria o sia un confine fra fasce.
- [ ] Se il **tempo di spostamento fra sedi** sia globale o per coppia di sedi (il
      campo `Verso` suggerisce che possa essere direzionale).
- [ ] Se esistano periodicità reali con denominatore **> 2** (oltre Q1/Q2).
- [ ] Se `Amenagement` e sostituzione siano la **stessa tabella**.
- [ ] Se `DureeSequences` sia mai davvero non intero in un file di scambio reale.
