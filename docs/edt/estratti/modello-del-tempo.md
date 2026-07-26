# Il modello del tempo in EDT — estrazione da stringhe, XSD e header basi dati

Fonti:
- `it_fr_en.tsv` (69 888 righe, tabella lingua IT/FR/EN condivisa EDT+PRONOTE)
- `Partenaire_Index.xsd` V4.6 (schema di scambio ufficiale, sola lettura)
- header `<CARTEIDENTITE>` di `Esempio.edt` (base demo completa) e `example_2.edt` (base Fermi)

⚠ Il binario delle stringhe è condiviso con PRONOTE. Le famiglie `Not*`, `*Bulletin*`,
`*Absence*Eleve*`, `*Devoir*`, `*Sanction*`, `*Internat*`, `*Bourse*` sono quasi certamente
PRONOTE e sono state escluse. Le famiglie riportate qui (`Sco*`, `FicheEDT_*`, `Fiche_*Grille*`,
`FicParametreEtablissement*`) appartengono al modulo di gestione oraria comune, quindi
plausibilmente EDT — marcato comunque [INFERENZA] dove la UI non è stata vista di persona.

---

## 1. La griglia oraria: giorni × fasce (séquences) × posizioni

### 1.1 Lo schema XSD (fonte più autorevole: struttura dati formale)

[STRINGA] da `Partenaire_Index.xsd`, elemento `GrilleHoraire` (righe 372-397):

```xml
<xs:element name="GrilleHoraire" minOccurs="0">
  <xs:complexType>
    <xs:sequence>
      <xs:element name="PlacesParJour">
        <xs:sequence>
          <xs:element name="Place" maxOccurs="unbounded">
            <!-- Numero: "Le numéro de la première place du jour est égal à 0" -->
            <xs:attribute name="Numero" type="xs:unsignedShort" use="required" />
            <xs:attribute name="LibelleHeureDebut" type="xs:time" use="required" />
            <xs:attribute name="LibelleHeureFin" type="xs:time" use="required" />
          </xs:element>
        </xs:sequence>
      </xs:element>
    </xs:sequence>
    <xs:attribute name="NombreJoursParCycle" type="xs:unsignedShort" use="required" />
    <xs:attribute name="NombreSequencesParJour" type="xs:unsignedShort" use="required" />
    <xs:attribute name="NombrePlacesParSequence" type="xs:unsignedShort" use="required" />
  </xs:complexType>
</xs:element>
```

Questo **conferma testualmente** l'ipotesi `place = giorno × 10 + rango`: la griglia dichiara
tre numeri — `NombreJoursParCycle` (giorni per ciclo, può eccedere 5/7), `NombreSequencesParJour`
(fasce per giorno) e `NombrePlacesParSequence` (posizioni dentro una fascia, per le suddivisioni
sub-orarie, vedi §1.3). Ogni `Place` del giorno ha un `Numero` 0-based e due etichette orarie
(`LibelleHeureDebut`/`LibelleHeureFin`) — le etichette sono **testo**, non necessariamente
coincidenti con l'ora "vera" (vedi nota su "orari personalizzati", §1.4).

L'elemento `AnneeScolaire` (righe 365-371) ancora il ciclo al calendario reale:
```xml
<xs:element name="AnneeScolaire" minOccurs="1">
  <xs:attribute name="DateDebut" type="xs:date" use="required" />
  <xs:attribute name="DateFin" type="xs:date" use="required" />
  <xs:attribute name="DatePremierJourSemaine1" type="xs:date" use="required" />
</xs:element>
```
`DatePremierJourSemaine1` è la data reale del primo giorno della "settimana 1": il ciclo
(che può essere più lungo di 7 giorni, vedi §1.5) si srotola a partire da lì.

Nell'elemento `Cours` (righe 1199-1283), la durata è un **choice** tra due unità:
```xml
<xs:choice>
  <xs:element name="DureeMinutes" type="xs:unsignedShort">
    <!-- "durée du cours en minutes" -->
  <xs:element name="DureeSequences" type="xs:decimal">
    <!-- "durée du cours en nombre de séquences" -->
</xs:choice>
```
[INFERENZA] `DureeSequences` è **decimale**, non intero: questo è coerente con la
possibilità di durate frazionarie di fascia (§1.3) — un'attività può durare p.es. 1,5
fasce. **Nessun campo di collocazione settimanale (place/giorno) e nessuna maschera di
settimane compare in `Cours`**: conferma quanto già scritto in `schema-scambio.md`, lo
XSD è puro input anagrafico/attività, il piazzamento vive altrove (nel motore/basi .edt).

### 1.2 La configurazione della griglia in UI (dalle stringhe)

[STRINGA] famiglia `Fiche_ConfigurationGrilleHoraire` (la finestra di configurazione iniziale
della griglia):

| Chiave | IT | FR |
|---|---|---|
| `CycleSemaine` | Ciclo di una settimana (dal %s al %s) | Cycle d'une semaine (du %s au %s) |
| `CyclePersonnalise` | Ciclo personalizzato | Cycle personnalisé |
| `DefinitionDuCycle` | Definizione del ciclo | Définition du cycle |
| `JoursOuvres` | giorni lavorativi | jours ouvrés |
| `ModifierPremierJour` | Modificate il primo giorno della settimana | Modifiez le premier jour de la semaine |
| `FicheParametresGrilleDureeSequenceTropGrande` | I parametri desiderati sono impossibili poiché determinano una giornata con oltre 24 ore (numero di fasce orarie × durata di un'unità) | ... journée de plus de 24h00 (nombre de séquence x durée d'une séquence) |
| `FicheParametresGrilleNombreMaximumSequenceAtteint` | I parametri definiti sono impossibili poiché determinano una giornata con oltre %d fasce orarie | ... journée de plus de %d séquences |
| `ModifierDureeSeq` | Modifica la durata definita per una fascia oraria | Modifier la durée définie pour une séquence |
| `SuppressionAmenagements` | Le modifiche dell'orario per settimana saranno cancellate | Les modifications de l'emploi du temps à la semaine vont être supprimées |
| `SuppressionAmenagementsCycle` | Le modifiche dell'orario per ciclo saranno cancellate | Les modifications de l'emploi du temps par cycle vont être supprimées |

[INFERENZA] Conferma: la giornata = N fasce orarie di durata fissa (in minuti), il totale
non può superare 24h; esiste un tetto massimo/minimo al numero di fasce configurabili
(valore parametrico, non fisso — il messaggio usa `%d`). "Giorni lavorativi" sono
attivabili/disattivabili singolarmente (vedi §1.2bis, `JoursOuvresInfo1`).

[STRINGA] famiglia `ScoGlossaireGrilleHoraire` (spiegazioni contestuali dello stesso wizard):

- `JoursOuvresInfo1` IT: *"La vostra settimana può avere da 1 a 7 giorni che potete mettere
  o togliere con un clic. I giorni con sfondo grigio non saranno presi in considerazione
  nella vostra base dati."* FR: *"Votre semaine peut comporter de 1 à 7 jours ... Les
  jours en gris ne seront pas pris en compte dans la base."*
- `SequencesInfo2` IT: *"10 fasce orarie da 60 minuti corrispondono a una giornata compresa
  tra le 8.00 e le 18.00."* — esempio canonico, coerente col caso tipico già noto
  (place = giorno×10+rango, 10 fasce/giorno).
- `ConservezDureePrServiceProfs` IT: *"Mantenere la durata predefinita di 60 minuti se una
  fascia oraria corrisponde a un'ora di servizio per i vostri docenti."* — [INFERENZA] la
  durata della fascia (séquence) è **anche** l'unità di calcolo delle ore di servizio
  docente (v. `DureeSeqUtilCalcul`, `SequencesInfo1`, `ModifDureeImpactServices`), quindi
  non è un dettaglio solo grafico: cambiarla ricalcola i monte-ore.
- `SequencesInfo1STS` IT: *"Attenzione, una durata diversa da 60 min potrebbe falsare o
  bloccare l'invio verso STSWEB"* — vincolo di interoperabilità col SIDI francese
  (equivalente del nostro contesto SIDI italiano), fuori scope diretto ma nota di cautela
  se mai si tocca la durata di fascia.

### 1.3 Le suddivisioni sub-orarie (découpage de séquence)

[STRINGA] famiglia `ScoGlossaireGrilleHoraire` / `InfoColonneSco_PersoHorairesSequences`:
la fascia oraria (séquence) può essere **suddivisa** in un numero fisso di parti uguali,
selezionabile fra: **2, 3, 4, 6, 12** (`DecoupageSequenceEn2/3/4/6/12`). Con una fascia da
60 minuti questo dà rispettivamente 30, 20, 15, 10, 5 minuti come "passo orario" minimo
(`DureePasHoraire` = "Durata di ogni frazione").

- `PasHoraireInfo2` IT: *"Una suddivisione in 2 crea 2 frazioni orarie da 30 min. che
  permettono la creazione di attività da 30 minuti, 1h, 1h30, 2h00, 2h30..."* FR:
  *"Un découpage en 2 crée 2 pas de 30 min. permettant la création de cours de 30 minutes,
  1h, 1h30, 2h00, 2h30..."*
- `InfoDecoupageSequence` IT: *"La suddivisione in %0:d rende più complesso il calcolo
  dell'orario, utilizzatela solo se dovete gestire attività di %1:d minuti."* — [INFERENZA]
  il motore sconsiglia esplicitamente la sub-divisione fine: complessità computazionale
  cresce con la granularità (coerente con `place` a interi, la subdivisione introduce
  una dimensione in più).
- `CocherDemiSeq` / `CocherTiersSeq` / `CocherQuartsSeq` (famiglia
  `InfoColonneSco_PersoHorairesSequences`): la UI di personalizzazione delle etichette
  permette di "mettere la spunta" a mezze, terzi, quarti di fascia — quindi **sì**, un'ora
  o un'attività può durare meno di una fascia intera, in frazioni discrete predefinite,
  non in minuti arbitrari.

Risposta alla domanda 1: **la griglia è `giorni_per_ciclo × sequenze_per_giorno`, e ogni
sequenza è a sua volta divisibile in un numero fisso di posizioni (`NombrePlacesParSequence`
nello XSD) — 1 (nessuna suddivisione), 2, 3, 4, 6 o 12.** Un'attività può quindi durare
meno di una fascia intera, ma solo in frazioni discrete di essa (mai minuti arbitrari), e
solo se la scuola ha attivato quella suddivisione (con l'avvertenza che aumenta la
complessità di calcolo).

### 1.4 Etichette orarie personalizzabili (durata "reale" ≠ durata di calcolo)

[STRINGA] `ScoGlossaireGrilleHoraire_RS_VousPourrezPersoLibHor` IT: *"È possibile
personalizzare la durata effettiva delle attività (ad esempio 55 minuti) modificando le
etichette dell'orario una volta creata la base dati (dal menu Parametri)"* FR: *"Vous
pourrez personnaliser la durée réelle des cours (par exemple 55 min) en modifiant les
libellés horaires une fois la base créée..."*

[INFERENZA] Questo separa **due nozioni di "ora"**: la sequenza di calcolo (usata dal
motore per piazzamento e per il calcolo delle ore di servizio, sempre un multiplo esatto
della durata di fascia) e l'**etichetta visualizzata/stampata**, che può essere
"accorciata" (es. 55 min invece di 60) senza toccare il modello di calcolo. Questo spiega
anche perché tutta la famiglia `FrameSco_PersoHorairesSequences` (§1.4bis) esiste come
passo separato del wizard, dopo la definizione della griglia vera e propria.

### 1.4bis Personalizzazione delle etichette (fase separata del wizard)

[STRINGA] `FrameSco_PersoHorairesSequences` / `FicheSco_Parametre_Horaire`:
- `LibelleHoraire` IT: *"Orari / Fasce orarie"*
- `InitialiserHoraires` IT: *"Inizializza gli orari secondo i miei criteri"*
- `InfosEspaces` IT: *"Sulle Aree mobile l'orario di fine viene visualizzato solo se
  diverso da quello di inizio"* — nota su un concetto "Aree mobile" (Espaces mobiles)
  non ulteriormente chiarito dalle stringhe raccolte: verosimilmente riguarda etichette
  per fasce non standard (pausa pranzo mobile?). **Da verificare in UI.**
- `IncoherenceChrono` IT: *"Incoerenza cronologica: quest'orario non è coerente con
  l'orario precedente o seguente"* — c'è validazione di coerenza cronologica sulle
  etichette personalizzate.

---

## 2. Ricreazioni / intervalli (récréations)

[STRINGA] `FicheSco_Parametre_Horaire_RS_Recreation` IT: *"Intervalli"* FR: *"Récréations"*
— è **un passo dedicato** del wizard di configurazione oraria (fianco a fianco con
`MiJournee` e `DemiPension`), non solo una fascia come le altre.

[STRINGA] `FicheEDT_CreationCours_RS_Interclasses` / `FicheSco_ParamCreationCours_RS_Interclasses`
IT: *"Rispetta gli intervalli"* FR: *"Respecte les récréations"* — parametro di creazione
attività, con hint `InterclassesHint` IT: *"Rispettare gli intervalli"*.

Risposta alla domanda (ricreazioni = fasce o marcatori?): [INFERENZA] **sono marcatori di
confine tra fasce**, non fasce a sé occupabili da attività: nella UI di configurazione
della griglia si "spostano le linee" per definirle (v. §3, `DeplacerLesTraitsMiJournee`
usa lo stesso pattern grafico per la mezza giornata), e a livello di vincolo di
piazzamento compaiono come flag booleano ("rispetta gli intervalli" sì/no) sulla singola
attività — cioè l'attività può essere marcata per **non poter mai essere spezzata a
cavallo di una ricreazione**. Questo è coerente con l'evidenza raccolta il 26/07 sui
vincoli materia/attività (nessuna menzione delle ricreazioni lì): il vincolo "rispetta
gli intervalli" vive sui **parametri di creazione del corso**, non nella griglia dei
vincoli materia↔materia.

`FicParametreEtablissementSites_RS_AucuneRecreActive` IT: *"Nessun intervallo è attivo: il
cambio tra queste sedi sarà vietato"* — le récréations sono anche **l'ancora temporale per
i cambi di sede** (v. §7): uno spostamento fra sedi può essere vincolato ad avvenire "alle
pause" o "agli intervalli".

**Da verificare in UI**: se un intervallo ha un orario di inizio/fine proprio (fascia con
zero capacità di accogliere lezioni) o se è puramente un marcatore fra due fasce
adiacenti senza durata propria.

---

## 3. La linea di mezza giornata (mi-journée) e le mezze giornate

[STRINGA] famiglia `FrameScoParametreAnneeScolaireMiJournee` (passo dedicato del wizard,
condiviso con la configurazione della mensa):

- `DelimitationDeLaMiJournee` IT: *"l'ora di fine mattinata:"* FR: *"l'heure de fin de la
  matinée :"*
- `DelimitationJourneeApresMidi` IT: *"e l'ora di inizio del pomeriggio:"* FR: *"et l'heure
  de début de l'après-midi :"*
- `JourneeContinue` / `JourneeNonContinue` IT: *"Giornata continua"* / *"Giornata con una
  pausa delimitata da"* — **due modalità alternative dichiarate esplicitamente**: giornata
  continua (nessuna pausa pranzo, mensa disattivata) oppure giornata spezzata in due mezze
  giornate da una pausa.
- `JourneeContinueCondition` IT: *"La giornata continua disattiva la mensa"* FR: *"La
  journée continue désactive la demi-pension"* — **collegamento diretto e dichiarato fra
  il modello del tempo e la mensa** (risposta parziale a domanda 4).
- `DeplacerLesTraitsMiJournee` IT: *"Spostare gli indicatori viola sulla griglia
  sottostante per definire il numero di fasce orarie di ogni mezza giornata"* — la mezza
  giornata è definita **in numero di fasce orarie** (non in orario assoluto): trascinando
  un indicatore sulla griglia visuale.
- `RecommencerEnHeuresPleines` IT: *"Dopo la pausa della mezza giornata, riprendi
  all'inizio dell'ora successiva"* — opzione per arrotondare l'inizio del pomeriggio a
  un'ora piena anche se la pausa dura meno di un multiplo esatto di fasce.
- `IncoherenceMiJournee` IT: *"Esiste almeno un docente il cui numero di giorni o mezze
  giornate libere è incompatibile con il numero di giornate da ignorare."* — [INFERENZA]
  **le mezze giornate sono anche l'unità del vincolo "giorno libero garantito" del
  docente** (coerente con `MMG`/`MG` sulla classe già documentati in `classi.md` — stesso
  meccanismo, applicato sia a classe sia a docente).

Risposta alla domanda: la "linea di mezza giornata" è un **confine configurabile in
termini di numero di sequenze**, condiviso fra mattina/pomeriggio; esiste in due varianti
(giornata continua / giornata spezzata) e la scelta ha effetto a cascata sulla mensa e
sui vincoli di mezza-giornata libera di classi e docenti.

---

## 4. La mensa (demi-pension)

[STRINGA] `FicheSco_Parametre_Horaire_RS_DemiPension` IT: *"Mensa (opzionale)"* FR:
*"Demi-pension (optionnelle)"* — è un passo **opzionale** del wizard di configurazione
oraria (si può disattivare interamente la gestione mensa).

Prova diretta che la mensa è un **vincolo hard nel piazzamento automatico**, dalla
famiglia `FrameEDT_RechercheCyclesCreneaux` (la finestra di ricerca di una fascia libera /
creazione manuale di un'attività), che elenca esplicitamente i vincoli **ignorabili**
durante la ricerca:

| Chiave | IT | FR |
|---|---|---|
| `IgnorerDemiPension` | Mensa | Demi-pension |
| `IgnorerIndispos` | Indisponibilità | Indisponibilités |
| `IgnorerJourFerme` | Mezze giornate non lavorative | Demi-journées non travaillées |
| `IgnorerSites` | Sedi | Sites |
| `IgnorerLesContraintes` | Ignora i seguenti vincoli: | Ignorer les contraintes ci-dessous : |

[INFERENZA] Il fatto che "Mensa" compaia **nella stessa lista** di "Indisponibilità" e
"Sedi" — vincoli hard già noti e documentati in `vincoli.md`/`schema-scambio.md` — conferma
che è trattata dal motore come un vincolo hard di piazzamento **della stessa famiglia**,
non come preferenza soft: di default il motore non piazzerà un'attività a cavallo/dentro
la fascia di mensa attiva, a meno di disattivare esplicitamente questo controllo (nella
ricerca manuale) o disattivare la mensa a livello di giornata (§3).

Confermato anche da `FrameEDT_PlacementAuto` (finestra parametri del piazzamento
automatico globale, non solo ricerca manuale):
- `DemiPensionActive` / `DemiPensionInactive` IT: *"Mensa attiva"* / *"Mensa non attiva"*
  con hint `HintDemiPensionActive` IT: *"La mensa è attiva"* — [INFERENZA] è uno stato di
  sistema che il piazzamento automatico legge e rispetta, non un parametro del singolo
  lancio del solver.

`MessagePauseMiJourneeEDT` IT: *"La mensa è attiva, verificate i turni di mensa se
modificate gli orari della mezza-giornata."* — i **turni di mensa** (`FrameSco_ServiceDemiPension`,
non approfondito qui — famiglia numerosa ma condivisa con PRONOTE per la gestione
nominativa degli alunni a mensa) sono un'entità separata, agganciata alla linea di mezza
giornata ma non identica ad essa.

Risposta alla domanda 4: **sì, è un vincolo hard**, espresso a livello di sistema come
"fascia di mensa attiva" derivata dalla linea di mezza giornata (§3); il motore di
piazzamento automatico e lo strumento di ricerca manuale la trattano esplicitamente come
vincolo di piazzamento, elencata insieme a indisponibilità e sedi, e disattivabile solo
esplicitamente (per l'intera giornata, o per la singola ricerca).

---

## 5. Il calendario: anno scolastico, vacanze, giorni non lavorativi

[STRINGA] `AnneeScolaire` nello XSD: `DateDebut`, `DateFin`, `DatePremierJourSemaine1` —
tre soli campi, l'anno scolastico è un intervallo di date più un ancoraggio del ciclo.

[STRINGA] famiglia `FrameScoParametresAnneeScolaireCalendrier` (interfaccia di gestione
vacanze/festivi):

- `CommentaireSaisieJoursFeries` IT: *"Cliccate su un giorno o selezionate più giorni
  tenendo premuto per renderli festivi"* — inserimento **per singolo giorno**, cliccando
  su un calendario visuale.
- `CalculJoursFeries` IT: *"Calcola i giorni festivi"* — [INFERENZA] esiste anche un
  calcolo automatico (probabilmente da un calendario ministeriale/regionale precaricato),
  non solo inserimento manuale.
- `TransformerFerie` / `TransformerSubstitusEnExeptionnels` IT: *"Trasforma in festivo"* /
  *"Conserva le attività spostate o riportate su dei giorni lavorativi"* — quando un
  giorno diventa festivo, le attività già piazzate lì vengono **spostate** ("sostituite"),
  e si può scegliere se preservarle come eccezioni.
- `JoursFeriesNonModifiesSurCyclesVerrouilles` / `JoursFeriesNonModifiesSurSemaineVerrouillees`
  IT: *"Solamente le vacanze e i giorni festivi al di fuori dei cicli bloccati [o delle
  settimane bloccate] possono essere modificati"* — [INFERENZA] esiste un meccanismo di
  **blocco (lock) per singolo ciclo o per singola settimana**, indipendente dal blocco dei
  periodi (§6): un ciclo/settimana "bloccato" è protetto da modifiche al calendario.

Header `<CARTEIDENTITE>` (Esempio.edt e example_2.edt): **nessun campo relativo a
griglia/settimane/periodi/vacanze** è esposto lì — solo conteggi di entità (materie,
docenti, classi, aule, siti, ecc., v. §9). Il calendario non è riassunto nell'header.

---

## 6. I periodi (quadrimestri/trimestri) — `Periode`, `Domaine`

[STRINGA] famiglia `FrameEDT_ParametrageCalendrier` (gestione dei periodi/quadrimestri):

- `FicEtatAlternancePeriode` IT: *"Periodicità"* — **ogni periodo ha una propria
  periodicità associata** (collega direttamente periodi e alternanze, §7).
- `FicEtatDateDebutPeriode` / `FicEtatDateFinPeriode` IT: *"Data di inizio"* / *"Data di
  fine"* — ogni periodo è un intervallo di date.
- `FicEtatCloturePeriode` / `CloturerPeriodeSelezionata` IT: *"P.Bloc."* / *"Blocca il
  periodo selezionato"* — un periodo può essere **bloccato/sbloccato** (chiuso); da
  bloccato, non è più modificabile né cancellabile (`PeriodesModifierCloturee`,
  `PeriodesPeriodeCloturee`).
- `EtablissementCoursPasSurLesperiodesAReunir` IT: *"Per riunire dei periodi, è necessario
  che le loro attività siano identiche"* — i periodi si possono **fondere** (`Riunisci i
  periodi`) o **dissociare** (`Dissocia il periodo`), ma la fusione richiede coerenza delle
  attività fra i periodi coinvolti — [INFERENZA] conferma che un'attività può esistere
  "solo su un periodo" e differire da un periodo all'altro.
- `PeriodesCoursPasAnnuels` IT: *"Per poter cancellare questa suddivisione, dovete rendere
  annuali le attività che avete definito su una parte di questa suddivisione"* — conferma
  esplicitamente l'esistenza di attività **definite solo su una parte dell'anno** (contro
  attività "annuali"): la suddivisione in periodi (`Decoupage`) è una partizione dell'anno
  di cui il "periodo unico anno intero" è solo un caso degenere.
- `MonterDecoupage` IT: *"Permette di spostare la suddivisione; quella in prima posizione
  sarà usata di default durante la creazione delle classi"* — possono coesistere **più
  suddivisioni** dell'anno (es. sia in trimestri sia in quadrimestri), una delle quali è
  quella di default.
- `NbSemainesOuvrees` / `NbCyclesOuvres` IT: *"Numero di settimane lavorative"* / *"Numero
  di cicli lavorativi"* — attributi calcolati per periodo.

### Place fixe / Place variable — la risposta diretta alla domanda 3

[STRINGA] famiglia `FicheEDT_CreationCours` / `FicheSco_ParamCreationCours` /
`FicAidePlacementCours` (proprietà di piazzamento di un'attività, sezione
"Proprietà di piazzamento" = "Propriétés de placement"):

| Chiave | IT | FR |
|---|---|---|
| `PlaceFixe` | Fascia fissa | Place fixe |
| `PlaceVariable` | Fascia variabile | Place variable |
| `ExplicationsPlaceFixe` | L'attività si svolge tutte le settimane nella stessa collocazione | Le cours a lieu toutes les semaines à la même place |
| `ExplicationsPlaceFixeCycle` | L'attività si svolge in tutti i cicli nella stessa collocazione | Le cours a lieu tous les cycles à la même place |
| `ExplicationsPlaceVariable` | **EDT può modificare la collocazione dell'attività a seconda dei periodi** | **EDT peut modifier la place du cours selon les périodes** |

**Risposta alla domanda 3: sì, esplicitamente supportato e nominato.** Un'attività è
`PlaceFixe` (stessa collocazione ogni settimana/ciclo, invariante) oppure `PlaceVariable`
(il motore può assegnarle collocazioni diverse a seconda del periodo — es. il lunedì
prima ora nel primo quadrimestre, il martedì terza ora nel secondo). Questa è una
proprietà dichiarata **al momento della creazione dell'attività**
(`FicheEDT_CreationCours_RS_ProprietesDePlacement` = "Proprietà di piazzamento"), non
un effetto collaterale casuale del solver.

Nella stessa finestra, `PeriodeDuCours` IT: *"Periodi dell'attività"* — un'attività
dichiara esplicitamente **su quali periodi esiste** (coerente con §6, un'attività può non
essere annuale), e altri campi correlati:
- `CoursHebdomadaire` "Attività settimanale" vs `CoursHebdomadaireCycle` "Attività
  regolare" vs `CoursCyclesAlternes` "Attività a cicli alternati" vs `CoursQuinzaine`
  "Attività quindicinale" — quattro **frequenze** possibili per un'attività, che
  corrispondono in modo diretto ai codici di periodicità del §7.

---

## 7. La periodicità: settimane, quindicine (Q1/Q2), cicli alternati — `Alternance`

### 7.1 Il modello: numeratore/denominatore, non una lettera A/B

[STRINGA] famiglia `NetTableSco_Alternance` — i **codici** di periodicità predefiniti:

| Codice (righe) | IT | FR | Significato [INFERENZA] |
|---|---|---|---|
| `CodeAlternanceH` | S | H | ogni Settimana / Hebdomadaire (tutte le settimane) |
| `CodeAlternanceQ` | Q | Q | Quindicinale generico |
| `CodeAlternanceQ1` | Q1 | Q1 | prima quindicina (equivalente "settimana A") |
| `CodeAlternanceQ2` | Q2 | Q2 | seconda quindicina (equivalente "settimana B") |
| `CodeAlternanceHCycle` | TC | TC | Tutti i Cicli |
| `CodeAlternanceQCycle` | C | C | Ciclo alterno generico |
| `CodeAlternanceQ1Cycle` | C1 | C1 | primo ciclo alterno |
| `CodeAlternanceQ2Cycle` | C2 | C2 | secondo ciclo alterno |

⚠ **Non esistono etichette letterali "Settimana A/B"** nelle 69 888 righe cercate: la
nomenclatura del prodotto è **Q1/Q2** ("quinzaine 1/2"), l'equivalente concettuale di
"settimana A/B" ma nominato diversamente — nota utile per non introdurre in
`glossario-it-fr.md` un'etichetta che il prodotto non usa.

[STRINGA] famiglia `FicEDTParametresBaseAlternances` (editor delle periodicità
personalizzate, oltre ai predefiniti sopra):

- `Numerateur` IT: *"Quantità"* FR: *"Numérateur"* — **ogni periodicità personalizzata è
  una coppia numeratore/denominatore** (es. "1 ogni 3 settimane" = numeratore 1,
  denominatore = numero di settimane dell'anno). Il denominatore non è un campo
  esplicito qui ma è vincolato: `NumNePeutEtreSupe` IT: *"La quantità non può essere
  superiore al numero di settimane nell'anno"* — quindi il denominatore effettivo è
  implicitamente **il numero totale di settimane (o cicli) dell'anno scolastico**.
- `FicParamGenerauxActualisationDesNumerateurs` IT: *"La modifica del numero di settimane
  dell'anno scolastico comporta l'aggiornamento delle quantità delle periodicità
  predefinite (S, Q, trimestrale e quadrimestrale)"* — [INFERENZA] **i "trimestri" e
  "quadrimestri" sono anch'essi codificati come periodicità numeratore/denominatore**,
  non come un concetto separato — coerente col fatto che un periodo (§6) porta con sé
  una propria `Alternance` (`FicEtatAlternancePeriode`).
- `AlternanceParDefaut` IT: *"Questa periodicità è predefinita"* — S/H, Q, Q1, Q2, TC, C,
  C1, C2 sono creati di default e non cancellabili (`AlternancesNonSupprimables`); si
  possono aggiungere periodicità arbitrarie oltre a queste.

[STRINGA] `EditSco_Alternance`:
- `HintAlternanceAucune` IT: *"la periodicità sarà calcolata in funzione del numero di
  settimane effettive dell'attività"* — modalità "Nessuna" = calcolo implicito dalla
  distribuzione reale delle lezioni piazzate.
- `HintAlternanceAutomatico` IT: *"la periodicità sarà calcolata in funzione del periodo
  e della frequenza dell'attività"* — modalità "Automatica" = derivata da `PeriodeDuCours`
  + `Frequence` (§6).

### 7.2 Quante settimane gestisce il ciclo?

[INFERENZA, da combinare con `FicParamGenerauxStrNbSemaines`/`StrNbCycles`]: **non un
numero fisso** — è un parametro dell'anno scolastico (`Numero di settimane` /
`Numero di cicli`, validati `> 0`), e il numero di quindicine/cicli-alterni gestiti dalle
periodicità predefinite (Q1/Q2, C1/C2) è sempre **2** (alternanza binaria), ma se ne
possono creare di **personalizzate** con denominatore arbitrario (es. "1 ogni 4",
alternanza a 4 vie) — coerente con `ConfirmModificationCyclesEnQuinzaine` /
`ConfirmModificationSemainesEnQuinzaine` che parlano di "definizione delle settimane
quindicinali (%s/%s)" con due segnaposto (il caso comune resta binario Q1/Q2).

### 7.3 Modalità di alternanza nei corsi complessi (compresenza / codocenza)

[STRINGA] famiglia `FicCoursComplexe` (attività complesse, già note da `schema-scambio.md`
per la generazione via allineamento):

| Chiave | IT | FR |
|---|---|---|
| `ModeStandardQuinzaine` (SQ) | Una lezione per docente ogni 15 giorni | Une séance par professeur pour chaque quinzaine |
| `ModeAlternanceGroupeQuinzaine` (AQ) | I docenti cambiano raggruppamento a metà dell'attività e si alternano ogni 15 giorni | Les professeurs changent de groupe à la moitié du cours et alternent à chaque quinzaine |
| `RepartitionQuinzaineClasse` (CQ) | I docenti cambiano classe ogni 15 giorni | Les professeurs changent de classe à chaque quinzaine |

[INFERENZA] Questi sono **modi di applicare Q1/Q2 alla composizione interna di
un'attività complessa** (allineamento), distinti dal "quando" piazzare l'attività:
qui l'alternanza quindicinale decide **quale docente/gruppo/classe** occupa lo stesso
slot settimana sì e settimana no, non se l'attività ha luogo. Rilevante per
`docs/edt/gruppi.md` più che per il modello del tempo puro, ma segnalato perché lega
esplicitamente Q1/Q2 alla composizione delle attività.

### 7.4 "Preferiti" di settimane/cicli — selezione manuale ad hoc

[STRINGA] famiglia `FicheEDT_FrameParametreGestionParSemaine_Alias`:
- `NouveauPreselectionSemaines` IT: *"Crea un preferito che raggruppa delle setttimane"*
- `NouveauPreselectionCycles` IT: *"Crea un preferito che raggruppa dei cicli"*

[INFERENZA] Oltre al sistema Q1/Q2/numeratore-denominatore, esiste un meccanismo
**indipendente** di selezione multipla arbitraria di settimane o cicli (bookmark
nominati), usato per operazioni bulk (es. "applica questa modifica alle settimane 3, 7,
12"), non per definire la periodicità di un'attività. Verosimilmente questo è il
meccanismo concreto dietro la "maschera di settimane a bit" già ipotizzata dal formato
file: una selezione libera di settimane, salvabile come preferito, è naturale da
codificare a bit piuttosto che come frazione.

---

## 8. Amenagement — l'eccezione puntuale (settimana singola / ciclo singolo)

[STRINGA], da `FicheEDT_PlacerAmenagerAnnuel` e famiglie correlate: esiste una
distinzione netta fra:
- **"l'orario annuale"** (`Placement... annuel`, la collocazione di base, valida secondo
  la periodicità dichiarata dell'attività, es. tutte le Q1);
- **"una modifica dell'orario per settimana"** o **"per ciclo"** (`Amenagement`,
  letteralmente "aggiustamento") — un'**eccezione puntuale** su una singola settimana o
  singolo ciclo che sovrascrive il piazzamento di base senza cambiare la definizione
  strutturale dell'attività.

Esempi:
- `PlacementEffectueAvec1AmenagementSupprime` IT: *"Piazzamento eseguito con successo ma
  è stato necessario cancellare una modifica dell'orario per settimana"* — il motore, per
  piazzare una nuova attività, può dover eliminare un `Amenagement` preesistente su una
  data settimana.
- Le operazioni sulla griglia (cambio fasce, festivi, mezza giornata) chiedono sempre
  conferma perché **cancellano gli `Amenagement`** esistenti oltre le attività
  (`SuppressionAmenagements`, `ConfirmerSuppressionAmenagement`).

[INFERENZA] Questo è, con ogni evidenza, il meccanismo che nel dominio "sostituzioni"
(il prodotto affiancato) diventa la sostituzione/spostamento puntuale di una singola
lezione in una singola settimana: la stessa tabella che modella "sposta l'attività X di
martedì prossimo" è probabilmente distinta dalla collocazione strutturale
dell'attività. **Rilevante per il nostro schema**: se vogliamo modellare spostamenti
puntuali (non ricorrenti) di una singola occorrenza, EDT lo tratta come layer separato
sovrapposto al piazzamento di base, non come una modifica della periodicità.

---

## 9. Le sedi (sites) e il tempo di spostamento

[STRINGA] famiglia `FicParametreEtablissementSites` (parametri di sistema, gestione sedi):

- `Sites` IT: *"Sedi"*, `SiteParDefaut` IT: *"Principale"* — c'è sempre una **sede
  principale** creata di default, non cancellabile (`AucunSiteSupprimable`).
- `OptionsChangementsSites` IT: *"Opzioni di trasferimento di sede"* — sezione dedicata
  al **vincolo di spostamento**, distinta per Classi (`CaptionChangementClasses`) e
  Docenti/Personale (`CaptionChangementProf`).
- `Duree` IT: *"Durata"* — la durata dello spostamento fra due sedi è **parametrizzata**
  (non risulta un valore fisso).
- `Pauses` IT: *"Nelle pause"* — i cambi di sede possono essere vincolati ad avvenire
  **solo durante le pause** (récréations, §2) o "in qualsiasi momento":
  `IgnorerDureeSaufToutMoment` IT: *"Ignorare la durata del cambio di sede per gli
  spostamenti 'durante le pause' e 'durante gli intervalli'\n(In caso di alleggerimento,
  la durata viene considerata per gli spostamenti 'in qualsiasi momento')"* — [INFERENZA]
  quando lo spostamento è confinato a una pausa, la sua durata **non consuma tempo di
  lezione** (si assume che la pausa sia abbastanza lunga); solo gli spostamenti "in
  qualsiasi momento" fanno slittare/bloccare il piazzamento in base alla durata.
- `MaximumDeChangements` IT: *"Numero massimo di cambi di sede"*, con periodicità
  `ParJour` / `ParHebdo` / `ParCycle` IT: *"per giorno"* / *"per settimana"* / *"per
  ciclo"* — tetto configurabile al numero di cambi di sede ammessi per risorsa
  (classe o docente), su tre granularità temporali.
- `AucuneRecreActive` IT: *"Nessun intervallo è attivo: il cambio tra queste sedi sarà
  vietato"* — se l'opzione di cambio è ristretta alle pause/intervalli ma **non esiste
  nessun intervallo attivo** nella griglia, il cambio fra quelle due sedi diventa
  semplicemente **impossibile** (vincolo hard di conseguenza, non solo di default).

[STRINGA] `Partenaire_Index.xsd`: elemento `Sites`/`Site` — solo `Ident`, `Nom`,
`Couleur`; l'elemento `Salle` referenzia un `Site`. **Nessun attributo di tempo di
spostamento nello XSD**: la durata di trasferimento è quindi **configurazione interna del
motore** (parametro di sistema in `FicParametreEtablissementSites`), non un dato di
scambio/importazione — coerente con quanto già scritto in `schema-scambio.md` (lo XSD non
porta vincoli).

Già noto (confermato il 26/07 in UI, v. `docs/edt/aule.md`): i tre soli vincoli sulla
finestra "Aule disponibili" sono `Sedi distaccate`, `Indisponibilità opzionali`,
`Indisponibilità` — **"Sedi distaccate" è quindi il vincolo runtime** che consulta questa
configurazione (durata, max cambi, ristretto alle pause) al momento di scegliere un'aula.

Risposta alla domanda 5: **sì**, il tempo di spostamento fra sedi è un parametro di
sistema esplicito (non per-coppia di sedi nelle stringhe viste — **da verificare in UI**
se è un valore unico globale o configurabile per coppia di sedi), con tre leve: durata
(eventualmente ignorata se il cambio è confinato alle pause), tetto massimo di cambi per
giorno/settimana/ciclo, e vincolo di "finestra" (solo pause/intervalli vs. in qualsiasi
momento). È un vincolo che può diventare hard-impossibile se non ci sono pause disponibili.

---

## 10. Header `<CARTEIDENTITE>` delle due basi

[STRINGA] `Esempio.edt` (base demo completa/risolta):
```
NBSITES=3  NBSALLES=18  NBPARTIES=187  NBGROUPES=3
NBCOURS=984  NBCOURSPLACES=984  NBCOURSNONPLACES=0
NBAMENAGEMENTS=141  NBSERVICEPREVISIONNELS=467
```

[STRINGA] `example_2.edt` (base Fermi, non piazzata):
```
NBSITES=1  NBSALLES=0  NBPARTIES=0  NBGROUPES=0
NBCOURS=284  NBCOURSPLACES=0  NBCOURSNONPLACES=284
NBAMENAGEMENTS=0  NBSERVICEPREVISIONNELS=212
```

Osservazioni:
- **Nessun campo relativo a griglia oraria, séquences, periodi o alternanze** compare
  nell'header — è confermato che la carta d'identità riassume solo conteggi di entità
  anagrafiche/organizzative, non la struttura del tempo.
- `NBAMENAGEMENTS` (141 sulla base demo, 0 sul Fermi non piazzato) conta esattamente le
  eccezioni puntuali del §8 — un numero non banale anche su una base "a regime": le
  eccezioni per-settimana sono un fenomeno frequente nell'uso reale, non un caso limite.
  [INFERENZA] utile indicatore: se mai importiamo/simuliamo un anno intero, aspettarsi che
  l'ordine di grandezza delle eccezioni puntuali sia comparabile al numero di attività
  diviso qualche decina, non zero.
  ⚠ **Da riconciliare con `NBRESEVALS`/`NBRENCONTRES` restando cauti**: `NBRENCONTRES=507`
  sulla base demo è alto e non ancora chiarito — plausibile PRONOTE (incontri
  scuola-famiglia) più che EDT, da non confondere con gli aménagements.
- `NBSITES=3` sulla base demo conferma che il meccanismo sedi (§9) è realmente usato lì
  (coerente con l'apertura della base fatta il 26/07 per studiare le aule); `NBSITES=1`
  sul Fermi conferma che lì non è mai stato configurato (una sola sede implicita).

---

## Cosa resta da verificare in UI

- [ ] **"Aree mobile" (Espaces mobiles)**: citate in `FrameSco_PersoHorairesSequences_RS_InfosEspaces`
      senza altro contesto reperito nelle stringhe. Ipotesi: etichette per fasce non
      standard (forse proprio la pausa pranzo mobile, o fasce facoltative). Da aprire in
      EDT: menu Parametri → Orari/Fasce orarie.
- [ ] **Se le récréations hanno una durata propria** (fascia a sé, magari a zero
      capacità) o sono solo un confine grafico fra due fasce adiacenti. Le stringhe
      parlano di "spostare le linee" ma non è chiaro se generano una `Place` propria
      nello XSD (che non ha un concetto di "récréation" esplicito).
- [ ] **Se il tempo di spostamento fra sedi è un valore unico globale o configurabile
      per singola coppia di sedi** (`Sens` = "Verso" nella tabella suggerisce che possa
      essere direzionale/per-coppia, ma non è stato trovato un campo tabellare esplicito
      nelle stringhe).
- [ ] **Il numero massimo di quindicine/cicli gestiti oltre il caso binario Q1/Q2**: le
      stringhe confermano che si possono creare periodicità personalizzate con
      denominatore arbitrario, ma non è stato osservato in UI un caso concreto con più di
      2 vie (es. un "ogni 3 settimane" reale).
- [ ] **La relazione esatta fra `Amenagement` (eccezione per-settimana/ciclo) e il layer
      "sostituzioni" del prodotto gemello**: se sono la stessa tabella o due tabelle
      distinte con logica di sincronizzazione. Rilevante per capire se il nostro modulo
      sostituzioni può/deve riusare questo stesso concetto.
- [ ] **Se `DureeSequences` (XSD, decimale) è mai stato osservato non intero** in un file
      di scambio reale, o se in pratica è sempre un intero nonostante il tipo XSD lo
      permetta.
- [ ] **Il significato preciso di "Numero di aule" già noto (Qtà) rispetto ai "Sites"**:
      se una sede distaccata ha sempre le sue aule proprie o se un'aula può teoricamente
      appartenere a più sedi (lo XSD lega `Salle` a un solo `Site` opzionale, quindi
      [INFERENZA] no — ma non verificato in UI).
