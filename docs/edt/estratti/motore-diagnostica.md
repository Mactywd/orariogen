# Estratto — Diagnostica e risoluzione delle attività scartate in EDT

Fonte: stringhe di interfaccia estratte dal binario (`it_fr_en.tsv`, 69 888 righe),
condivise fra EDT e PRONOTE. Di seguito solo le famiglie che, per nome e contenuto,
appartengono con ragionevole certezza a **EDT** (piazzamento orario). Le famiglie
scartate come PRONOTE/Sco sono elencate in fondo con la motivazione.

Marcatori: **[STRINGA]** = testo letterale estratto (certo). **[INFERENZA]** = mia
deduzione dalla struttura delle chiavi/dai raggruppamenti (da confermare in UI).

---

## 1. Il menu: percorso esatto

**[STRINGA]** La voce di primo livello del menu principale è:

| chiave | IT | FR | EN |
|---|---|---|---|
| `ActionsEDT_Client_RS_FicMenusConception` | **&Elabora** | &Calcul | &Calculation |

Da lì, la guida cita testualmente il percorso completo per la risoluzione degli
scarti (vedi §3):

> **[STRINGA]** IT: *"Utilizzate gli strumenti di risoluzione nel menu
> "Elabora > Risoluzione > Piazza le attività scartate". EDT cercherà delle
> soluzioni alle attività scartate attraverso calcoli più approfonditi."*
> FR: *"Vous pouvez utiliser les outils de résolution "Calcul > Résolution" afin
> qu'EDT cherche de manière plus approfondie des solutions à ces cours en échec."*
> (chiave `FicheEDT_PlacementAuto_RS_MsgUtilisationOutilsResol`)

Quindi il percorso di menu è: **Elabora → Risoluzione → Piazza le attività
scartate** (FR: Calcul → Résolution). La voce di comando esatta:

| chiave | IT | FR | EN |
|---|---|---|---|
| `Chaines_ClientGraphiqueEdT_RS_FicMenusMenuResoudreEchecs` | **Piazza le attività scartate** | Lancer le résoluteur automatique ... | Launch the automatic solver |

⚠ **Nota**: l'IT usa "Piazza le attività scartate" mentre l'FR letterale è
"Lancer le résoluteur automatique". Sono la stessa voce di menu (stessa chiave),
solo tradotta in modo diverso — l'italiano nomina il risultato, il francese lo
strumento.

**[STRINGA]** Un'altra voce di sottomenu confermata (submenu `&Piazzamento` in
italiano, ma la chiave FR/EN dice `&Verrous`/`&Locks` — probabile
**inversione terminologica IT↔FR** simile a quella già nota per gruppo/raggruppamento,
da verificare in UI):

| chiave | IT | FR | EN |
|---|---|---|---|
| `ActionsEDT_Client_RS_FicMenusMenuVerrous` | &Piazzamento | &Verrous | &Locks |

---

## 2. Le cause di mancato piazzamento nominate esplicitamente da EDT

Questa è la lista più ricca: la famiglia **`AffSco_UtilDiagnostic`** (170
stringhe) è il catalogo delle **causali di occupazione/conflitto** mostrate
nella diagnostica e nella colorazione della griglia durante il piazzamento
manuale. **[STRINGA]** Non è un elenco a caso: ogni causale ha un testo intero,
spesso già formattato per essere concatenato in una lista ("La classe è già
occupata in un'attività ..."). Le raggruppo per categoria.

### 2.1 Risorsa già occupata (per ciascun tipo di risorsa: classe, gruppo,
raggruppamento, materiale, personale, docente, aula) — con tre varianti

Per **ogni** tipo di risorsa esiste la stessa terna di causali (esempio sulla
classe, il pattern si ripete identico per Gruppo/Raggruppamento, Materiale,
Personale, Docente, Aula):

| causale | IT |
|---|---|
| occupata in un'attività "normale" | *"La classe è già occupata in un'attività"* |
| occupata in un'attività **spostabile altrove** | *"La classe è già occupata in un'attività che ha una collocazione altrove"* (= liberabile: se sposti quella, si libera lo slot) |
| occupata in un'attività **bloccata** | *"La classe è già occupata in un'attività bloccata"* (= non liberabile: verrouillé) |
| occupata in una **permanenza** (buco/studio) | *"La classe è già occupata in una permanenza"* |
| occupata in una **permanenza bloccata** | *"La classe è già occupata in una permanenza bloccata"* |

Per Aula e Materiale esiste anche la variante **"picco d'occupazione"**
(`SallePicOccupe...`, `MaterielPicOccupe...`): *"o il gruppo di aule/materiale
ha raggiunto il suo picco d'occupazione"* — collegato al meccanismo `Qtà`
(Numero di aule) già documentato in `docs/edt/aule.md`.

**[INFERENZA]** La distinzione "liberabile" vs "bloccata" è precisamente ciò
che permette al résoluteur pas-à-pas di sapere se, per piazzare l'attività in
scarto, può **spostare** l'occupante attuale (liberabile) o deve **rinunciare**
a quello slot (bloccata) — vedi §3.

### 2.2 Indisponibilità (rigide e opzionali), per ciascun tipo di risorsa

`IndispoClasse`, `IndispoCours`, `IndispoEleve`, `IndispoGroupe`,
`IndispoMateriel`, `IndispoPersonnel`, `IndispoProf`, `IndispoResponsable`,
`IndispoSalle` — e i corrispettivi **opzionali** `IndispoSouple*` (souple =
opzionale/morbido) per Classe, Attività, Materiale, Personale, Docente, Aula.
**[STRINGA]** Es. *"Il docente ha una indisponibilità"* /
*"Il docente ha un'indisponibilità opzionale"*. Conferma diretta della
distinzione rigida/opzionale già in `docs/edt/vincoli.md`.

### 2.3 Preferenze (voeu)

`VoeuClasse`, `VoeuCours`, `VoeuGroupe`, `VoeuMateriel`, `VoeuPersonnel`,
`VoeuProf`, `VoeuSalle` — **[STRINGA]** *"Il docente ha una preferenza"* ecc.
Nota terminologica: FR `voeu` (desiderio/richiesta) = IT "preferenza" — coerente
col terzo pennello `Preferenze` già documentato.

### 2.4 Vincoli materia↔materia e attività↔attività (causali con placeholder `%s`)

Queste ricalcano **esattamente** le 10 colonne dei vincoli di materia già
documentate in `docs/edt/vincoli.md`, ma qui appaiono come **messaggi di
diagnosi puntuale**, col nome della materia iniettato via `%s`:

- `MatieresIncompatibles2JoursFmt` → *"%s, troppe attività su 2 giorni"*
- `MatieresIncompatiblesJourneeFmt` → *"%s, troppe attività nella giornata"*
- `MatieresIncompatiblesMatinFmt` / `...SoirFmt` / `...MatinOuSoirFmt` →
  varianti mattina/pomeriggio
- `MaxHoraireMatiereJourneeFmt`, `...MatinFmt`, `...SoirFmt`,
  `...MatinOuSoirFmt` → *"%s, troppe ore nella giornata/mattinata/pomeriggio"*
- `EcartDjMatieresFmt` → *"%s, numero di mezze giornate insufficiente"*
- `EnchainementImposeDemiJourneeFmt` / `...JourneeFmt` → *"%s, sequenza in
  mezze giornate/giornate successive non rispettata"*
- `OrdreClasseParties_S` → *"%s, ordine delle attività in gruppo rispetto alle
  attività a classe intera non rispettato"* — **questa è la conferma letterale
  dei quattro valori `Parties…Classe` segnati come "ancora aperto" in
  CLAUDE.md**: il messaggio di diagnosi usa esattamente questa formulazione.
- `OrdreCycleFmt`, `OrdreHebdoFmt` → ordine nel ciclo / ordine settimanale non
  rispettato
- `SuccessionMatiereFmt` → *"%s, sequenza indesiderata di attività"*

E le causali attività↔attività **non legate a una materia specifica**:
- `CaCIncompatibilite` → *"Incompatibilità con un'altra attività"*
- `CaCRegroupement` → *"Collocazione imposta con un'altra attività"*
- `Ordre` → *"Ordine imposto con un'altra attività"*
- `SuccessionImposee` / `SuccessionInterdite` → *"Sequenza imposta/vietata con
  un'altra attività"*
- `QuinzaineImposee` / `QuinzaineInterdite` → *"Quindicina imposta/vietata da
  un'altra attività"*
- `RepartitionQuinzaine` / `RepartitionQuinzaineCycle` → *"Un'attività
  quindicinale/a cicli alternati della stessa materia è già piazzata questa
  settimana/su questo ciclo"*
- `RepartitionImposeeNonRespettee` → *"Distribuzione oraria non rispettata"*

### 2.5 Vincoli orari generali (non specifici di materia)

- `DemiJourneeTravaillee` → *"Massimo di 1/2 giornate di lavoro superate"*
- `MaxHoraireRessourceJournee/Matin/Soir/MatinOuSoir` → massimo ore
  giornata/mattino/pomeriggio superato **sulla risorsa** (non sulla materia)
- `PoidsPedagogiquesJournee/Matin/Soir/MatinOuSoir` → limite pesi didattici
  superato
- `MaxPresentielRessource` → *"Massimo di ore di presenza superato"*
- `PlageHoraireGarantie` → *"Il docente non ha più giorni e 1/2 giornate
  libere"* (le fasce libere garantite)
- `Recreation` → *"Intervallo non rispettato"*
- `DebutCoursInterditClasse/Cours/EleveDetache/Partie` → *"...non può iniziare
  un'attività su questa fascia oraria"*

### 2.6 Vincoli di sede (site — sedi distaccate)

- `SitesIncompatiblesDureeTrajet` → *"Tempo insufficiente per il trasferimento
  di sede"*
- `SitesIncompatiblesHeureTransition` / `...Recreation` → *"Cambio di sede al
  di fuori delle pause/intervalli definiti"*
- `SitesIncompatiblesNbTransitionsCycle/Hebdo/Jour` → *"Numero di cambi di sede
  superiore al limite fissato per ciclo/settimana/giorno"*

### 2.7 Priorità (attività prioritaria vs non prioritaria)

`ClasseOccupeeCoursPrioritaire/NonPrioritaire`, e lo stesso pattern per Alunno,
Personale, Docente, Aula. **[INFERENZA]** Questo implica che EDT tiene un flag
di priorità **per attività** che il résoluteur usa come criterio di
sostituibilità: un'attività non prioritaria può essere spostata per far posto a
una prioritaria. Confermato dalle voci di menu:

| chiave | IT |
|---|---|
| `ActionsEDT_Client_RS_FicMenusMettreCoursPrioritaires` | Rendi prioritarie le attività |
| `ActionsEDT_Client_RS_FicMenusMettreCoursNonPrioritaires` | Rendi non prioritarie le attività |

### 2.8 Legenda dei colori/simboli nella griglia (drag & drop)

- `LegendeRessourceEnRouge` → *"Risorsa in rosso:"*
- `LegendeRessourceOccupeeParUnCours` → *"Occupata in un'attività"*
- `LegendeRessourceOccupeeParUnCoursVerroulle` → *"Occupata in un'attività
  bloccata"*
- `LegendeRessourceAbsente` → *"Risorsa assente"*
- `LegendeRessourceBarree` → *"Risorsa barrata"*
- `LegendeRessEnRougeCadenassee` → *"Risorsa in rosso +"* (il simbolo "+" =
  ulteriore dettaglio disponibile, presumibilmente al passaggio del mouse)
- `LegendePartieEnRougeChainee` → *"Gruppo in rosso +"*
- `LegendePartiesLieesOccupeesParCours` → *"Gruppi collegati occupati da
  alcune attività"*
- `FicLegendeDiagnosticIndisponibiliteEtablissement` → *"Mezza giornata non
  lavorativa"*
- `FicLegendeDiagnosticJourFerie` → *"Giorno festivo"*

**[INFERENZA]** Il colore rosso segnala una risorsa **in conflitto/occupata**,
mentre le varianti "+" segnalano che c'è altro da vedere (tooltip con elenco
causali). Questo è coerente col meccanismo rosso/giallo/verde già documentato
per indisponibilità/assenze in `docs/edt/vincoli.md` — qui applicato
specificamente al piazzamento.

---

## 3. La finestra "Piazza le attività scartate" (résoluteur automatico)

**[STRINGA]** Titolo della finestra: `FicSolut_RS_TitreFicheCours` = **"Piazzamento
automatico delle attività scartate"** (FR: *"Résoluteur automatique pour les
cours en échec"*).

### 3.1 Cosa mostra e come si naviga

- Due **metodi di elaborazione** selezionabili (`GroupMethode`):
  - `MethodeCourante` = **Standard** (FR *Méthode standard*)
  - `MethodeAvancee` = **Avanzato** (FR *Méthode avancée*)
  - **[STRINGA]** Consiglio testuale in UI: *"Iniziate sempre con il metodo
    standard."* / *"In seconda battuta, utilizzate il metodo avanzato."*
- Un **livello di approfondimento** (`NiveauProfondeur`, "Scegliete il livello
  di approfondimento:") con tre gradini: `1erNiveau`/`2emeNiveau`/`3emeNiveau`
  (1°/2°/3° livello) — **[INFERENZA]** presumibilmente controlla quanta
  ricerca (backtracking) il solver fa prima di arrendersi su ciascuna
  attività.
- Contatori in tempo reale durante il calcolo:
  - `LabelEchecs` = "Attività da piazzare"
  - `LabelCoursTraites` = "Attività trattate"
  - `LabelSolution` = "Soluzioni trovate"
  - `LabelCoursSans` = "Senza soluzione" (= attività per cui non è stata
    trovata nessuna collocazione)
  - `TempsEcoule` = "Tempo trascorso:"
- Opzione `IgnorerRecreation` = "Ignora gli intervalli" (rilassamento rapido)
- Opzione `InclureCoursSansPlace` = "Includi le attività senza collocazione
  (%d)" — un contatore dinamico nel checkbox stesso.
- Sottopannello `SurIndisp` = **"Piazza le attività anche sulle fasce orarie
  con indisponibilità opzionali..."**, con sotto-opzioni granulari per tipo di
  risorsa: `SurIndispClasse`, `SurIndispProf`, `SurIndispPersonnel`,
  `SurIndispSalles`, `SurIndispMateriel` — cioè si può scegliere **su quali
  categorie di risorse** allentare le indisponibilità opzionali, non è
  tutto-o-niente.
- Pulsanti: `LabelBtnLancer` = "Lancia la ricerca", `LabelBtnFermer` = "Chiudi".
- `ReprendreResolution` = "Riprendi la ricerca (fase %u)" — il calcolo è
  **ripartito in fasi** (passe) e può essere ripreso da dove si era interrotto.
- Messaggio di conferma prima del lancio (`ConfirmSuppressionAmenagements`):
  *"Confermate di voler lanciare il calcolo?"*.
- Nota sul salvataggio automatico durante l'elaborazione (ogni mezz'ora), che
  suggerisce che l'operazione può durare a lungo.

### 3.2 In cosa differisce dal piazzamento automatico normale

**[STRINGA]** Messaggio esplicito che lo dichiara (`FicAssouplissements_RS_Info1/Info2`):

> IT: *"Il piazzamento delle attività scartate rispetta automaticamente tutti i
> vincoli. Se dopo un primo calcolo rimangono delle attività scartate, potete
> alleggerire certi vincoli."*
> FR: *"Par défaut le résoluteur automatique respecte toutes les contraintes.
> Si après une première résolution il reste des échecs, vous pouvez assouplir
> certaines contraintes."*

**[INFERENZA]** Quindi la differenza principale non è "vincoli più morbidi di
default", ma:
1. il piazzamento automatico normale (`FicheEDT_PlacementAuto`, prima passata)
   piazza tutte le attività che può in un colpo solo, poi si ferma;
2. il "Piazza le attività scartate" (résoluteur) è una **seconda fase
   dedicata**, che lavora *solo* sullo scarto residuo, con più tempo/calcolo
   per attività (metodo standard/avanzato, livelli di profondità), e con la
   possibilità esplicita di sbloccare margini di alleggerimento (§4) — che il
   primo passaggio non usa.
3. Conferma indiretta in `FicheEDT_PlacementAuto_RS_ConfirmArretResoluteur`:
   *"Questo comando interrompe il piazzamento delle attività scartate (l'attività
   resterà scartata). Volete anche interrompere tutto il piazzamento
   automatico?"* — cioè **il résoluteur degli scarti gira "dentro" o "dopo" il
   piazzamento automatico**, e i due processi hanno comandi di stop separati
   ma annidati.

Limite dichiarato del résoluteur (`ActionsEDT_Client_RS_ResolutionPasAPasImpossible`):

> IT: *"Questo comando non elabora: - le attività piazzate - le attività
> complesse dettagliate"*

**[INFERENZA]** Il résoluteur si applica solo alle attività **non ancora
piazzate**, e non tocca le "lezioni di insegnamento" (séances d'enseignement,
il dettaglio delle attività complesse/allineamenti) — coerente con quanto già
noto: le attività complesse vengono gestite a un livello diverso.

---

## 4. Il pannello "Alleggerimento dei vincoli" (Assouplissements) — risposta alla domanda 5

**[STRINGA]** Sì: esiste un meccanismo esplicito, ma **non è EDT che sceglie da
solo quale vincolo allentare** — è un pannello guidato in cui **l'utente
seleziona quali famiglie di vincoli sbloccare**, e per ciascuna **quantifica il
margine consentito**. Titolo: `DeContraintes` = **"Alleggerimento dei
vincoli"** (FR: *Assouplissement de contraintes*).

**[STRINGA]** Istruzioni testuali della finestra (`Info3`):

> IT: *"Attivate l'opzione "Alleggerisci" e sbloccate i vincoli che desiderate
> alleggerire. Potete parametrare ogni vincolo. Il calcolo cercherà delle nuove
> soluzioni tenendo conto degli alleggerimenti definiti."*

Le **famiglie di vincolo alleggeribili**, ciascuna con un parametro numerico
("una tantum per settimana/ciclo/classe/docente" ecc.):

| Famiglia | IT | Parametro tipico |
|---|---|---|
| `ChangementSite*` | Cambi di sede (alunni/docenti) | N cambi extra "in ogni momento"/fuori pausa |
| `DemiJourneeTrav*` | Massimo 1/2 gg lavoro (docenti e classi) | +1 mattina/pomeriggio extra per settimana o ciclo |
| `IncompMat*` | Incompatibilità materie | ignora, N volte per settimana/ciclo e per classe, max 1/giorno |
| `JoursEcourtesClasse/Prof` | Gestione Entrate/Uscite (orari flessibili) | "Togli se necessario" |
| `MaxHClasse/MaxHMat/MaxHProf` | Massimo di ore (classi/materie/docenti) | +N ore extra, una tantum/settimana o ciclo |
| `MaxPresentielProf` | Presenza massima docenti | +N, una tantum/settimana o ciclo |
| `PlagesLibres` | Giorni e 1/2 giornate libere garantite | "Togli se necessario", N mezze giornate/settimana o ciclo |
| `PoidsPedag` | Peso didattico delle materie | +1 giorno/settimana o ciclo |
| `SuccMat` | Sequenze indesiderate di materie | autorizza 1 volta/settimana o ciclo e per classe, max 1/giorno |

Controllo globale: `MaxContraintes` = **"Numero massimo di vincoli da
alleggerire per risorsa:"** — un tetto complessivo, non solo per tipo.

Due pulsanti di preset: `RespectContraintes` = "Rispetta tutti i vincoli"
(default) vs l'alleggerimento personalizzato; `ValeursStandard` = "Valori
standard" per resettare i parametri.

**[INFERENZA]** Questo è quindi un meccanismo di **rilassamento a menu
esplicito e quantificato**, non un "solver spiega quale vincolo blocca e
suggerisce di allentare quello": è l'utente che, guardando lo scarto residuo
(o semplicemente per tentativi), decide quali famiglie sbloccare e con che
margine — coerente con "i vincoli sono **tutti hard** con rilassamento
esplicito **a quota** (non penalità)" già scritto in
`docs/edt/motore-risoluzione.md`. **Non risulta** un algoritmo che analizza
automaticamente lo scarto e propone "allenta X perché è la causa più
frequente" — ma non posso escluderlo con certezza dalle sole stringhe: andrebbe
verificato se la finestra pre-seleziona/evidenzia dei vincoli in base allo
scarto reale (vedi §6).

---

## 5. Modalità diagnostica nel piazzamento manuale

**[STRINGA]** Nel menu contestuale del piazzamento manuale (`ActionsEDT_Client_RS_FicMenusMenuPlacementManuel`):

> IT: **"Passa alla modalità diagnostica"** — FR: *"Passer en mode diagnostic"*
> — EN: *"Switch into diagnosis mode"*

Quindi la diagnostica **non è sempre attiva**: è una modalità a cui si passa
esplicitamente (presumibilmente alternandola con la modalità di piazzamento
normale) durante il trascinamento manuale.

**[STRINGA]** Nella finestra **"Preferenze di piazzamento manuale delle
attività"** (`FicheEDT_ParametresPrefs_Placement_Manuel`, gruppo
`GroupeTitreDiagnostic` = "Diagnostica") c'è l'opzione:

> `EnDiagCacherCoursNonGenants` = *"Nascondi le attività che non rientrano
> nella diagnostica"*, con nota: *"(altre attività del gruppo di aule,
> attività di gruppi senza legami...)"*

**[INFERENZA]** Questo conferma che la modalità diagnostica, durante il
trascinamento, mostra **tutte le attività coinvolte nel calcolo di
compatibilità dello slot** (inclusi effetti collaterali come altre aule dello
stesso gruppo, altri gruppi collegati), e questa opzione permette di
filtrarle per vedere solo quelle realmente "che creano problemi" — stesso
concetto di `CoursGenants` visto nel résoluteur pas-à-pas (§7).

Altre preferenze nella stessa finestra, utili per il quadro generale del
piazzamento manuale:
- `WinEtatDeplacerCoursVerrouilles` = "Consenti lo spostamento delle attività
  bloccate"
- `WinEtatImposerCoursPlaces` = "Blocca le attività piazzate manualmente"
- `WinEtatPasDeposerCrsVerrouilles` = "Impedisci la sospensione delle attività
  bloccate"

---

## 6. Il "résoluteur pas-à-pas" (risolutore passo-passo) — collocazioni possibili

Questa è una finestra **diversa** dal résoluteur automatico di §3: qui EDT
non piazza da solo, ma **guida l'utente slot per slot**, mostrandogli l'effetto
di ciascuna scelta prima di confermarla.

**[STRINGA]** Titolo/istruzione: `CliquezPlaceDeVotreChoix` = *"Cliccate sulla
fascia oraria desiderata:"*, con la griglia intera visualizzata solo a titolo
indicativo (`UtilisezPetiteGrillePourSelectionnerPlace`: *"L'orario è
visualizzato a titolo indicativo, utilizzate la piccola griglia a sinistra per
selezionare la collocazione desiderata"*).

**[STRINGA]** Colorazione delle collocazioni possibili nella griglia:

| chiave | significato |
|---|---|
| `EnBlancPlacesSansDeplacement` | *"in bianco, le collocazioni senza attività che creano problemi"* — slot libero, nessun effetto collaterale |
| `EnGrisPlacesAvecDeplacements` | *"in grigio, le collocazioni che comportano lo spostamento di almeno un'altra attività"* — slot occupato ma **liberabile spostando** qualcos'altro |
| `PlaceAvecContraintes_D` | *"Collocazione con %d vincoli"* — quante regole tocca quella scelta |
| `PlaceAvecDeplacements_D` | *"%d attività da ricollocare"* — quante attività andrebbero spostate a cascata |
| `PlaceSansContrainte` | "Collocazione senza vincolo" |
| `PlaceSansDeplacement` | "Nessuna attività da sostituire" |

**[INFERENZA]** Non c'è una terza categoria "impossibile/rosso" esplicita in
questa famiglia — presumibilmente le collocazioni davvero impossibili
(risorsa bloccata, indisponibilità rigida) semplicemente **non vengono
proposte/cliccabili**, mentre bianco/grigio distinguono solo fra "nessun
effetto collaterale" e "effetto collaterale gestibile". Da verificare in UI se
esiste un terzo colore per "impossibile ma visibile".

**[STRINGA]** Il pannello di ricerca ha un parametro esplicito sul numero di
mosse a catena consentite, con tre preset di menu:

| chiave | IT |
|---|---|
| `TrouverSolutionEnUnCoup` | Trova una soluzione al massimo in uno step |
| `TrouverSolutionEnXCoups_D` | Trova una soluzione al massimo in %d step |
| `ActionsEDT_Client_RS_FicMenusMenuen1coup/en2coups/en3coups` | ... spostando &1/&2/&3 attività al massimo |

Distingue esplicitamente:
- `CoursAPlacer` = "Attività da piazzare" (l'attività in scarto, oggetto della
  ricerca)
- `CoursDepositionnes` = "Attività sospesa da piazzare" (un'attività **già
  piazzata altrove** che il solver ha temporaneamente tolto — "dépositionnée"
  — per fare spazio, e che ora va ricollocata)
- `CoursGenants` = "Attività che creano problemi" (gli ostacoli nello slot
  scelto)
- `CoursPlacesReplaces` = "Attività piazzata / ricollocata" (esito)

**[STRINGA]** Limite dichiarato identico al résoluteur automatico
(`ActionsEDT_Client_RS_TrouverUneAutrePlaceImpossible`): *"Questo comando non
elabora le attività complesse dettagliate"*.

**Esito nullo**: `FicMenusAucuneSolutionTrouvee` = *"Nessuna soluzione
trovata."*; interruzione manuale: `RechercheInterrompue` = *"La ricerca è
stata interrotta."*

---

## 7. Meccanismo collaterale: diagnostica sui raggruppamenti/gruppi (cliques)

**[STRINGA]** Famiglia `UtilitaireEDT_DiagnosticCliques` (12 stringhe,
inequivocabilmente EDT nel nome): avvisi che scattano quando **un
raggruppamento o gruppo supera il proprio massimo di ore e/o il limite dei
pesi didattici**, sia in forma aggregata (*"Alcuni raggruppamenti (%d) superano
il loro massimo di ore..."*) sia puntuale su un singolo gruppo (*"Questo
gruppo supera il suo massimo di ore e il limite dei pesi didattici."*).
**[INFERENZA]** Questo è un controllo di coerenza **preventivo/informativo**
(probabilmente eseguito prima o durante il piazzamento automatico, non un
esito di scarto in sé), distinto dalle causali di §2. Nome "Cliques"
(cricche, terminologia da teoria dei grafi) suggerisce che sotto il cofano il
motore modella i raggruppamenti come cricche di compatibilità in un grafo —
coerente con quanto già emerso su `motore-risoluzione.md`.

---

## 8. Stati dell'attività (enum) — vocabolario di base per il modello dati

**[STRINGA]** `Type_EtatCours`: `EnEchec` (Scartate/Failure), `NonPlace(e/i)`
(Non piazzata/Unplaced), `Place(e/i)` (Piazzata/Placed), `Verrouille(e/i)`
(Bloccata/Locked). Sono **quattro stati distinti**, non un booleano
piazzata/non piazzata: un'attività scartata (`EnEchec`) è una sotto-categoria
di non piazzata su cui il piazzamento automatico ha **già tentato e fallito**
(altrimenti sarebbe semplicemente "non ancora tentata" — da confermare se EDT
distingue le due cose o le tratta come sinonimi).

**[STRINGA]** Log/storico delle operazioni (`Type_OperationCours`) include voci
dedicate proprio a questi strumenti, utile per capire cosa viene tracciato
nell'audit trail:
`OpcResoluteur` = "Risolvi"/"Solver", `OpcResoluteurPasAPas` = "Trova una
soluzione"/"Step by step solver", `OpcPlaceAuto` = "Piazzamento automatico",
`OpcPlaceManuel` = "Piazzamento manuale", `OpcDepose` = "Sospensione". Questo
conferma che **ogni tipo di piazzamento/sospensione è un'operazione loggata e
distinguibile a posteriori**.

---

## 9. Famiglie scartate (PRONOTE/Sco, non EDT)

- **`ScoGlossaireDiagnostic`** (92 stringhe): a un primo sguardo sembrava la
  fonte principale, ma è in realtà **mista**: contiene sì causali di
  piazzamento condivise con `AffSco_UtilDiagnostic` (stessa terminologia,
  probabilmente lo stesso codice sorgente riusato), ma anche un blocco enorme
  di **lettere di bitmap** (`LettreBitmap*`) il cui uso preciso non è chiaro
  dalle sole stringhe, e voci amministrative (diritti insufficienti,
  prenotazione aule/materiali con soglia di preavviso, mensa) che sono
  **genericamente EDT/Sco condiviso**, non specifiche del motore di
  piazzamento delle lezioni. Le ho incluse solo dove il testo è
  inequivocabilmente sul piazzamento orario (§2, §8).
- **`FicResoluteurRencontres`** e **`FicheEDT_ResoluteurConseils`**: stesso
  meccanismo di risoluzione a fasi (passe), stessi contatori ("Attività da
  piazzare", "Soluzioni trovate", "Tempo trascorso") — ma applicato ai
  **colloqui genitori-docenti** e ai **consigli di classe**, non alle lezioni.
  **[INFERENZA]** È evidente che EDT riusa lo **stesso motore/UI generico di
  risoluzione degli scarti** per tre domini diversi (lezioni, colloqui,
  consigli) — utile saperlo concettualmente, ma le stringhe stesse non vanno
  citate come feature del piazzamento delle lezioni.
- **`FicheDiagnosticReseau`** (67 stringhe): diagnostica di **rete/connessione
  TCP** (ping, traceroute, MTU) — nulla a che vedere con la schedulazione.
  Esclusa.
- **`NotUtilitaireDiagnosticLSU`**, **`RequetesVisu_LSU`**: diagnostica per
  l'esportazione verso il **Livret Scolaire Unique** (pagelle), dominio
  PRONOTE. Esclusa.
- **`Type_ErreurDiagnosticCPRO`**, **`Type_DiagnosticImportCPRO`**: import
  "CPRO" (presumibilmente Chef de Projet/altro modulo amministrativo),
  dominio non chiaro ma **non piazzamento orario**. Esclusa.
- **`Type_RaisonEchecRepartitionEleve`** (11 stringhe): causali di fallimento
  della **ripartizione degli alunni nelle classi** ("Formazione classi" —
  numero massimo alunni, incompatibilità opzioni, sesso, ripetenti...). È un
  meccanismo di scarto **strutturalmente identico** (stesso pattern
  "causale nominata esplicitamente") ma applicato a un problema completamente
  diverso (assegnazione alunni↔classe, dominio Sco/Pronote). CLAUDE.md nota
  che la Formazione classi si salta per mancanza di anagrafica alunni: coerente
  con l'esclusione.
- **`FicheSco_ExportFregata`**, **`UtilitaireSco_ColonnesCoursSimplifie`**,
  **`Chaines_Scolys`**: export/interoperabilità con altri sistemi ministeriali
  francesi, non pertinenti.

---

## Cosa resta da verificare in UI

1. **La finestra "Piazza le attività scartate"**: uno screenshot della
   finestra stessa (`FicSolut`) per vedere come sono disposti visivamente
   metodo standard/avanzato, livello di profondità, contatori, e il pulsante
   che apre il pannello "Alleggerimento dei vincoli" — per confermare se è
   davvero raggiungibile solo da lì o anche da altrove.
2. **Il pannello Alleggerimento vincoli**: EDT **evidenzia o pre-seleziona**
   automaticamente qualche vincolo in base allo scarto appena calcolato, o è
   sempre una lista neutra che l'utente esplora a mano? Questo chiude
   definitivamente la domanda 5 (suggerimento automatico sì/no).
3. **"Passa alla modalità diagnostica"**: uno screenshot del trascinamento di
   un'attività scartata **con** e **senza** questa modalità attiva, per vedere
   la differenza visiva reale (colori, tooltip, elenco causali a comparsa).
4. **Il résoluteur pas-à-pas**: uno screenshot della "piccola griglia" a
   sinistra con le collocazioni bianche/grigie, per vedere se esiste un terzo
   colore per le collocazioni davvero impossibili (o se semplicemente non
   sono cliccabili/non appaiono).
5. **`&Piazzamento` / `&Verrous` / `&Locks`**: la stessa chiave menu ha
   traduzioni molto diverse (IT "Piazzamento" vs FR/EN "Locks/Verrous") — va
   controllato in UI se in italiano è davvero un sottomenu sul **blocco**
   delle attività (coerente con FR/EN) o se it è un refuso di traduzione che
   confonde con tutt'altro sottomenu.
6. **`Type_EtatCours`**: EDT distingue in UI (es. colore/icona nella lista
   attività) fra "non piazzata perché non ancora tentata" e "scartata perché
   il piazzamento automatico ha fallito"? Le stringhe suggeriscono quattro
   stati ma non è chiaro se "non piazzata" e "in scarto" siano visivamente
   distinti o se "scartata" sia semplicemente ciò che resta dopo un
   piazzamento automatico incompleto.
7. **Diagnostica cliques** (§7, raggruppamenti/pesi didattici): in che punto
   del flusso appare — è un controllo preventivo prima di lanciare il
   piazzamento, o un messaggio che appare durante, o dopo?
