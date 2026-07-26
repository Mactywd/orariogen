# EDT 2026 — estrazione delle stringhe di interfaccia (IT / FR / EN)

> Reverse engineering delle **etichette UI** di EDT 2026 (Index Education) a partire
> dai binari installati sotto Wine. **Sola lettura**: nessun file di `~/.wine` è stato
> modificato; tutto il lavoro è avvenuto su copie in scratchpad.
>
> Convenzione di questo documento:
> - **[STRINGA]** = testo letterale estratto dal binario → **certo**.
> - **[INFERENZA]** = mia deduzione dalla coppia IT/FR/EN o dal nome della chiave → **da confermare**.

---

## 1. Metodo

### Cosa NON ha funzionato

- `strings -el` (UTF-16LE) sulla DLL: **1054 stringhe**, quasi tutte nomi di risorsa
  in francese maiuscolo (`ACCUEILBOUTONCREERUNEBASE`, `MFICHECONTRAINTESCLASSES`…).
  Le etichette UI **non** sono in RT_STRING né in UTF-16.
- `pefile` non è installato (e non è stato installato, come richiesto). Non è servito.
- I file `italian.adm`, `French.adm`, `british.adm`, `spanish.adm` **non sono file di
  lingua**: sono dizionari del correttore ortografico. Header letterale del file:
  `Addict Dictionary Compiler, Version 4.0 / (c) 1995-2000 Addictive Software /
  Title: Italian / Words: 145277 / Nodes: 47688`. Irrilevanti.
- `EDT Monoposto.lng` è solo un puntatore:
  `[Module_1] Fichier=EDT Monoposto.dll / LangueParDefaut=1040 / Langues=1040,1033,1036`.

### Cosa ha funzionato

Le etichette sono memorizzate **in chiaro, in UTF-8, come blocchi XML** dentro
`EDT Monoposto.dll` (55 MB, PE32 DLL a 2 sezioni). Formato di ogni voce:

```xml
<chaine numero="1909000" cle="ActionsEDT_Client_RS_FicMenusAffecterHSMax2">Assegna il massimo di ore supplementari</chaine>
```

Nella DLL ci sono **10 tag `<chaines>`**; sei di essi sono le tabelle di lingua
complete, riconoscibili dal valore della prima chiave
(`AbonneChangementModeExclusifClientsGraphiqueCP_RS_MessagePassageConsultationMEAnonyme`):

| Offset apertura | Offset chiusura | Lingua | Stringa di riconoscimento |
|---|---|---|---|
| 119008 | 8522069 | EN | `Operations must be conducted on the database.` |
| 10289512 | 18844450 | ES | `Unas operaciones deben ser efectuadas en la base de datos.` |
| 19444016 | 28047426 | **FR** | `Des opérations doivent être effectuées sur la base de données.` |
| 32236912 | 40768050 | **IT** | `È necessario effettuare alcune operazioni sulla base dati.` |
| 42454184 | 45467527 | NL | `Er wordt aan de databank gewerkt.` |
| 46784744 | 54997816 | EU (basco) | `Eragiketak datu-basean egin behar dira.` |

Estrazione con `re.finditer(rb'<chaine numero="(\d+)" cle="([^"]*)">(.*?)</chaine>')`
su ciascun blocco, decodifica UTF-8, unescape delle entità HTML.

**Risultato: 69 888 stringhe italiane, 69 888 francesi, 69 887 inglesi**
(ES 68 972, EU 68 849, NL 27 396 — parziale). La chiave `cle` è **identica fra le
lingue**, quindi la correlazione IT↔FR↔EN è esatta, non euristica.

File prodotti in scratchpad:

- `it_fr_en.tsv` — 69 888 righe, colonne `chiave · IT · FR · EN` (il file di lavoro).
- `strings_it.tsv`, `strings_fr.tsv`, `strings_en.tsv`, … — `numero · chiave · testo`.
- `all_langs.json` — tutte le lingue in un dizionario.

Le chiavi hanno forma `<Form/Contesto>_RS_<Campo>`, quindi si può risalire alla
**finestra** in cui una stringa compare (es. tutto ciò che inizia per
`FicheEDT_FramePrefsContraintes_RS_` è il pannello dei vincoli orari).

---

## 2. Vincoli orari del docente — le lettere D, M, P, E, G **risolte**

### 2.1 Il pannello: `FicheEDT_FramePrefsContraintes_RS_*` [STRINGA]

Tutte le righe che seguono sono letterali, nell'ordine `IT · FR · EN`.

| Chiave (`FicheEDT_FramePrefsContraintes_RS_…`) | IT | FR | EN |
|---|---|---|---|
| `RepartitionImposeeTitre` | `Distribuzione oraria` | `Répartition imposée` | `Imposed distribution` |
| `RepartitionImposeeTravailler` | `Minimo` | `Travailler` | `Work` |
| `RepartitionImposeeJoursParSemaine` | `giorni a settimana con un minimo di` | `jours par semaine avec un minimum de` | `days per week with a minimum of` |
| `RepartitionImposeeHeuresParJour` | `per giorno` | `par jour` | `by day` |
| `MaximumHoraire` | `Massimo di ore di attività` | `Max horaire` | `Time max. :` |
| `J` / `M` / `AM` | `Giornata:` / `Mattino:` / `Pomeriggio:` | `Journée :` / `Matin :` / `Après-midi :` | `Day:` / `Morning:` / `Afternoon :` |
| `MaxPresentiel` | `Massimo di ore di presenza` | `Maximum présentiel` | `Maximum on site presence` |
| `NbJoursParSemaineAuPlusNbHeuresMaxPresentiel` | `giorni alla settimana, presenza massima in istituto:` | `jours par semaine, faire des journées d'au plus` | `days per week, establish days of not more than` |
| `NbJoursParCycleAuPlusNbHeuresMaxPresentiel` | `giorni per ciclo, lavorare al massimo` | `jours par cycle, faire des journées d'au plus` | `days per cycle, establish days of not more than` |
| `JoursEcourtesGarantis` | `Gestione Entrate / Uscite` | `Horaires aménagés` | `Flexible working hours` |
| `JoursEcourtesGarantisNb` | `giorni alla settimana` | `jours par semaine` | `day(s) per week` |
| `JoursEcourtesGarantisNbCycle` | `giorni per ciclo` | `jours par cycle` | `days per cycle` |
| `JoursEcourtesGarantisMatin` | `non iniziare prima delle` | `commencer au plus tôt à` | `begin at the earliest at` |
| `JoursEcourtesGarantisApresMidi` | `non finire oltre le` | `terminer au plus tard à` | `finish, at the latest at` |
| `PlagesLibresGaranties` | `Giorni e 1/2 giornate libere` | `Plages libres garanties` | `Guaranteed free time frames` |
| `Liberer` | `Assegna...` | `Garantir` | `Guarantee` |
| `JourneesLibres` | `giornate libere` | `Journées libres` | `Free days` |
| `DemiJourneesLibres` | `mezze giornate libere` | `Demi-journées libres` | `Free half-days` |
| `MaxDemiJournees` | `Massimo di mezze giornate di lavoro` | `Maximum de demi-journées de travail` | `Maximum of worked half-days` |
| `UneDemiJourneeParJour` | `Lavorare solo mezza giornata al giorno` | `Ne travailler qu'une demi-journée par jour` | `Only work a half-day per day` |
| `NbMaxChangementSite` | `Numero massimo di cambi di sede` | `Maximum de changements de site` | `Maximum number of site changes` |
| `NbMaxChangementSiteJour/Semaine/Cycle` | `per giorno` / `per settimana` / `per ciclo` | `par jour` / `par semaine` / `par cycle` | — |
| `PuceTitrePrefsOptim` | `Preferenze di ottimizzazione` | `Préférences d'optimisation` | `Optimization preferences` |

**Le etichette troncate del pannello destro sono così complete.** In particolare:

- **`D` — Distribuzione oraria**: `Minimo` **N** `giorni a settimana con un minimo di`
  **X** `per giorno`. Il francese chiarisce che è un *minimo imposto* di distribuzione
  (`Répartition imposée`, `Travailler N jours par semaine avec un minimum de X par jour`).
- **`P` — Massimo di ore di presenza**: **N** `giorni alla settimana, presenza massima
  in istituto:` **X**. Il francese è più esplicito: `faire des journées d'au plus X`.
- **`G` — Giorni e 1/2 giornate libere**: pulsante `Assegna...` (FR `Garantir`) +
  **N** `giornate libere` + **N** `mezze giornate libere`. Il francese
  `Plages libres garanties` dice che sono **garanzie**, non desiderata.

### 2.2 Le lettere-badge: `ScoGlossaireDiagnostic_RS_LettreBitmap*` [STRINGA]

Questa famiglia contiene esattamente le lettere disegnate sui badge. Correlando
IT/FR con i titoli del pannello (§2.1) la mappa è univoca:

| Chiave | IT | FR | EN | Vincolo corrispondente |
|---|---|---|---|---|
| `LettreBitmapRIRessource` | **D** | R | R | **R**épartition **I**mposée = Distribuzione oraria |
| `LettreBitmapMHRessource` | **M** | M | M | **M**aximum **H**oraire = Massimo di ore di attività |
| `LettreBitmapMPRessource` | **P** | P | O. S. | **M**aximum **P**résentiel = Massimo di ore di presenza |
| `LettreBitmapJoursEcourtesGarantis` | **E** | A | F | Horaires **A**ménagés = Gestione **E**ntrate/Uscite |
| `LettreBitmapGarantie` | **G** | G | G | Plages libres **G**aranties = **G**iorni e ½ giornate libere |

Le altre lettere della stessa famiglia (utili per leggere la diagnostica):

| Chiave | IT | FR | EN |
|---|---|---|---|
| `LettreBitmapJournee` | G | J | D |
| `LettreBitmapDemiPension` | M | D | H |
| `LettreBitmapEnchainement` | C | E | S |
| `LettreBitmapSuccession` | S | S | S |
| `LettreBitmapIncompatibilite` | I | I | I |
| `LettreBitmapOrdreHebdo` | O | O | A |
| `LettreBitmapQuinzaine` | Q | Q | F |
| `LettreBitmapPoids` | P | P | W |
| `LettreBitmapFixe` | F | F | S |
| `LettreBitmapVariable` | V | V | V |
| `LettreBitmapSite` | S | S | S |
| `LettreBitmapRecreation` | I | R | R |
| `LettreBitmapCycleAlterne` | C | C | C |
| `LettreBitMapCaCIncompatibilite` / `CaCOrdre` / `CaCQuinzaineInterdite` / `CaCSuccession` | I / O / Q / S | I / O / Q / S | I / O / F / S |

### 2.3 La legenda dei tipi di vincolo: `Type_Contrainte_RS_Legende*` [STRINGA]

È il catalogo **completo** dei vincoli che il motore EDT conosce.

| Chiave | IT | FR | EN |
|---|---|---|---|
| `LegendeRepartitionImposee` | `Distribuzione oraria` | `Répartition imposée` | `Imposed distribution` |
| `LegendeMH` | `Max. di ore superato` | `Max. horaire dépassé` | `Time max. exceeded` |
| `LegendeMP` | `Massimo di presenza` | `Max. présentiel` | `Max. on site presence` |
| `LegendeJEG` | `Gestione Entrate/Uscite` | `Horaires aménagées` | `Flexible working times` |
| `LegendePG` | `Giorni e 1/2 giornate libere` | `Plages libres non garanties` | `Non guaranteed free time frames` |
| `LegendeDJ` | `Mezze giornate di lavoro` | `Demi-journées de travail` | `Working half-days` |
| `LegendeIndisp` | `Indisponibilità` | `Indisponibilité` | `Unavailability` |
| `LegendeIndispSouple` | `Indisponibilità opzionali` | `Ind. optionnelle` | `Optional unavail.` |
| `LegendeContrainteMatiere` | `Vincolo materia` | `Contrainte matière` | `Subject constraint` |
| `LegendeCoursACours` | `Vincolo tra attività` | `Contrainte cours à cours` | `Course-by-course constraint` |
| `LegendePP` | `Peso didatt.` | `Poids pédago.` | `Pedag. weight` |
| `LegendeS` | `Sedi distaccate` | `Sites distants` | `Split-sites` |
| `LegendeDP` | `Mensa` | `Demi-pension` | `Half-board` |
| `LegendeRecreation` | `Intervallo` | `Récréation` | `Recess` |
| `LegendeCGP` / `LegendeCG` | `Attività prioritaria` / `Attività non prioritaria` | `Cours prioritaire` / `Cours non prioritaire` | — |
| `LegendeJCM` | `Numero massimo di giorni di consigli` | `Nombre de jours de conseils maximum` | — |
| `LegendeAbsenceRessource` | `Assenza` | `Absence` | `Absence` |
| `LegendeDebutPossible` | `Inizio possibile` | `Début possible` | `Possible beginning` |
| `LegendeConsG` | `Con consiglio` | `Conseil gênant` | `Problematic committee` |

### 2.4 I tre pennelli della griglia — nome del terzo **risolto** [STRINGA]

| Chiave | IT | FR | EN |
|---|---|---|---|
| `AffScoGrilleAnnuelM_RS_IndispoLong` | `Indisponibilità` | `Indisponibilités` | `Unavailability` |
| `AffScoGrilleAnnuelM_RS_OptionnellesLong` | `Indisponibilità Opzionali` | `Indisponibilités Optionnelles` | `Optional Unavailability` |
| `AffScoGrilleAnnuelM_RS_VoeuxLong` | **`Preferenze`** | **`Voeux`** | **`Wishes`** |
| `Chaines_ClientGraphiqueEdT_RS_WinArborescenceIndispoRessources` | `Indisponibilità e preferenze` | `Indisponibilités et voeux` | `Unavailability and wishes` |
| `Chaines_ClientGraphiqueEdT_RS_WinArborescenceContraintesRessources` | `Indisponibilità e vincoli` | `Indisponibilités, voeux et contraintes` | `Unavailability, wishes and constraints` |

Il terzo pennello (verde) si chiama **`Preferenze`** (FR `Voeux`). Confermata anche la
simmetria: le indisponibilità *opzionali* esistono per docenti, **classi**, **aule**,
**materiali**, **personale** e **attività** — le stringhe di diagnostica lo dicono una
per una:

- `AffSco_UtilDiagnostic_RS_IndispoSoupleProf` → `Il docente ha un'indisponibilità opzionale`
- `…_IndispoSoupleClasse` → `La classe ha un'indisponibilità opzionale`
- `…_IndispoSoupleSalle` → `L'aula ha un'indisponibilità opzionale`
- `…_IndispoSoupleMateriel` → `Il materiale ha un'indisponibilità opzionale`
- `…_IndispoSouplePersonnel` → `La risorsa del personale ha una indisponibilità opzionale`
- `…_IndispoSoupleCours` → `L'attività ha un'indisponibilità opzionale`

### 2.5 Buchi (`trous`) e la colonna `D.T.B.` [STRINGA]

| Chiave | IT | FR | EN |
|---|---|---|---|
| `UtilitairesEdt_ColonnesRessources_RS_ColTrousToleresCourt` | `D.T.B.` | `H.T.T.` | `T.G.H.` |
| `UtilitairesEdt_ColonnesRessources_RS_ColTrousToleresLong` | `Durata tollerata dei buchi` | `Nombre d'Heures de Trous Tolérées` | `Number of Tolerated Gaps Hours` |
| `FrameEDT_PrefsOptim_RS_LabelTrous` | `Numero di ore di buco tollerate` | `Nombre d'heures de trous tolérées` | — |
| `Chaines_ClientGraphiqueEdT_RS_HintTrousToleresProfesseur` | `Numero di ore dei buchi tollerati per il docente (ottimizzazione)` | — | — |
| `Chaines_ClientGraphiqueEdT_RS_AutoriserDepassementSeuils` | `Autorizza il superamento del massimo di buchi tollerati` | `Autoriser le dépassement des seuils de trous tolérés` | — |
| `FicPreferencesPlacement_RS_Trous` | `Gestione dei buchi` | `Gestion des trous` | `Gap management` |
| `FicPreferencesPlacement_RS_PlageCommeTrou` | `Non conteggiare come buchi le ore libere prima o dopo la linea di fine mattinata:` | `Ne pas compter comme des trous les plages libres autour de la mi-journée :` | — |
| `FicPreferencesPlacement_RS_LaisserTrousDemiHeure` | `Lascia i buchi di 1/2 ora` | `Laisser les trous d'1/2 heure` | — |
| `Chaines_EdT_RS_WinBouclPenaliserLesTrousProfesseur` | `Riduci i buchi (docenti)` | `Pénaliser les trous (professeur)` | — |
| `Chaines_EdT_RS_WinBouclPenaliserLlesTrousClasse` | `Riduci i buchi (classi)` | `Pénaliser les trous (classe)` | — |
| `Chaines_ClientGraphiqueEdT_RS_NePasCompterChangementSiteDansTrou` | `Non considerare i cambi di sede come dei buchi` | — | — |

**[INFERENZA]** `D.T.B.` = **D**urata **T**ollerata dei **B**uchi (dal `…Long`).
Il buco è quindi sia un **vincolo di soglia** (D.T.B. per risorsa, superabile solo se
si attiva `Autorizza il superamento…`) sia un **termine di ottimizzazione**
(`Riduci i buchi`, `Durata totale dei buchi`). La riga
`FicPreferencesPlacement_RS_PlageCommeTrou` conferma **[INFERENZA]** che la linea
magenta a metà griglia è la *linea di fine mattinata* (`mi-journée`) e serve proprio a
non contare come buco l'intervallo pranzo.

---

## 3. Vincoli di materia (classe × materia A/B)

Corrisponde ai tipi interni `TNetContrainteMatiereClassep` / `TNetContraintesClasse`.
Griglia `FicAffContrainteClasse` — titolo `Vincoli delle materie delle classi`
(`Contraintes matières des classes`). Tutte [STRINGA]:

| Vincolo | IT | FR |
|---|---|---|
| Incompatibilità ½ giornata | `Incompatibilità nella stessa mezza giornata: perché due attività delle materie selezionate non siano piazzate nella stessa mezza giornata` | `Incompatibilité dans la même demi-journée : …` |
| Incompatibilità giornata | `Incompatibilità nella stessa giornata: …` | `Incompatibilité dans la même journée : …` |
| Incompatibilità 2 giorni | `Incompatibilità in due giorni consecutivi: perché due attività delle materie selezionate non siano piazzate in due giorni consecutivi` | `Incompatibilité sur deux jours consécutifs : …` |
| **Scarto in ½ giornate** (`Ecart`) | `Numero minimo di 1/2 giornate: per inserire un certo numero di mezze giornate tra due attività delle materie selezionate` | `Incompatibilité en 1/2 journées : pour que deux cours des matières sélectionnées soient espacés d'un certain nombre de demi-journées` |
| Max ore ½ giornata | `Massimo di ore nella mezza giornata: perché il numero di ore di attività di questa materia nella mezza giornata non superi mai il valore indicato` | `Maximum horaire dans la demi-journée : …` |
| Max ore giornata | `Massimo di ore nella giornata: …` | `Maximum horaire dans la journée : …` |
| Sequenza vietata | `Sequenza di materie indesiderata: perché un'attività della materia B non si svolga subito dopo un'attività della materia A` | `Succession de matières interdite : …` |
| Concatenazione imposta | `Concatenazione imposta: determina l'intervallo temporale massimo tra due attività della stessa materia` | `Enchaînement imposé : détermine le délai maximum entre deux cours de la même matière` |
| Ordine settimanale | `Ordine settimanale: perché un'attività della materia A si svolga sempre prima di un'attività della materia B` | `Ordre hebdomadaire : …` |
| Ordine nel ciclo | `Ordine nel ciclo: perché un'attività della materia A si svolga sempre prima di una della materia B` | `Ordre dans le cycle : …` |
| Successione imposta ½ g. | `Un'attività della materia B deve svolgersi nella mezza giornata che segue un'attività della materia A` | `… au plus tard dans la demi-journée qui suit …` |
| Successione imposta J+1 | `Un'attività della materia B deve svolgersi nella giornata che segue un'attività della materia A` | `… au plus tard dans la journée qui suit …` |

Colonne della griglia: `Materie A` / `Materia B` / `Incompatibilità` /
`Max ore` (FR `Max. horaire`) / `Conc. Imp.` (FR `Ench. Imposé`, EN `Imposed seq.`).

**Quindi `TNetInfosContrainteEcart` = il vincolo "Numero minimo di 1/2 giornate"**
fra due materie [INFERENZA, ma la coppia `HintContrainteEcartDemiJ` +
`ActionsEDT_Client_RS_LabelEcartDemiJ` = `N. 1/2 g:` / `Nbre 1/2j :` la rende solida].
Attenzione: `Écart` altrove significa semplicemente **`Scarto`** (differenza numerica,
es. `Dotazione – Bisogni`), quindi il termine è sovraccarico nel prodotto.

Peso didattico (vincolo di materia a livello classe) [STRINGA]:
`TableAffEDT_ClassesPoidsMatieres_RS_Col_PoidsClasseHint` →
`Peso didattico massimo per settimana per un alunno` / `Poids pédagogique maximum par semaine pour un élève`.

---

## 4. Vincoli fra attività (`TNetContrainteCoursACours`)

Titolo: `Vincoli tra attività` / `Contraintes cours à cours`. Tipi creabili
(`FicheSco_CreationContrainteCaC_RS_Description*`) — tutte [STRINGA]:

| IT | FR |
|---|---|
| `Impone che le attività selezionate abbiano luogo nella stessa giornata` | `Imposer que les cours sélectionnés aient lieu la même journée` |
| `Evita il piazzamento delle attività nella stessa giornata` | `Interdire que les cours sélectionnés aient lieu dans la même journée` |
| `Impone che le attività selezionate abbiano luogo nella stessa mezza giornata` | `… la même demi-journée` |
| `Evita il piazzamento delle attività nella stessa mezza giornata` | `Interdire … dans la même demi-journée` |
| `Impone che le attività selezionate abbiano luogo in un numero definito di mezze giornate` | `… sur un nombre personnalisé de demi-journées` |
| `Impedisce che le attività selezionate abbiano luogo in un numero definito di mezze giornate` | `Interdire … dans les mêmes demi-journées` |
| `Impone che le attività selezionate abbiano luogo nella stessa settimana` | `Imposer que les cours en quinzaine sélectionnés aient lieu la même semaine` |
| `Impedisce che le attività selezionate abbiano luogo nella stessa settimana` | `Interdire … la même semaine` |
| `Definisce l'ordine delle attività selezionate nella settimana` | `Définir l'ordre des cours sélectionnés dans la semaine` |
| `Impone la sequenza delle attività selezionate` | `Imposer que les cours sélectionnés se succèdent` |
| `Impedisce la sequenza delle attività selezionate` | `Interdire que les cours sélectionnés se succèdent` |

Parametri e limiti [STRINGA]:

- `FicheSco_CreationContrainteCaC_RS_NbDemiJournees` → `Numero di mezze giornate` /
  `Nombre de demi-journées` ← **questo è il `TNetInfosContrainteEcart` in versione
  cours-à-cours**.
- `FicheSco_ContrainteCoursACours_RS_QuinzaineImpossible` → `Impossibile vincolare più
  di due attività ad essere piazzate su settimane alterne.`
- `FicheSco_ContrainteCoursACours_RS_SuccessionSansSuperposition` → `Non possono
  esserci più di due attività consecutive.`
- **Opzionalità**: `Vincolo opzionale (può essere alleggerito durante il piazzamento
  delle attività scartate)` / FR `Contrainte optionnelle (vous aurez le choix d'ignorer
  les contraintes cours à cours optionnelles lors de la résolution des échecs)`.
  Colonna `Opz.` / `Opt.`.

Quindi i tipi interni si mappano così **[INFERENZA basata sulle stringhe sopra]**:

- `TNetInfosContrainteEcart` → scarto/distanza in mezze giornate (materie *e* attività).
- `TNetInfosContrainteQuinzaine` → stessa/diversa quindicina (settimane alterne Q1/Q2).
- `TNetInfosContrainteSuccession` → sequenza imposta/vietata fra attività.
- `TNetContrainteCoursACours` → il contenitore dei vincoli fra attività.
- `TNetContraintesClasse` / `TNetContrainteMatiereClassep` → §3.
- `TNetContraintesProfesseur` → §2.

### 4.1 Riscontro coi nomi di classe RTTI dentro `EDT Monoposto.exe` [STRINGA]

I nomi `TContrainte*` **esistono davvero** nell'eseguibile (verificati con
`grep -ac` su `EDT Monoposto.exe`; fra parentesi il numero di occorrenze). Confermano
la mappa lettera→vincolo del §2.2 in modo indipendente dalle etichette:

| Classe nell'exe | Vincolo UI | Lettera IT |
|---|---|---|
| `TContrainteRepartitionDemiJournees` (2) | Distribuzione oraria / `Répartition imposée` | **D** |
| `TContrainteMaxHoraireRessource` | Massimo di ore di attività | **M** |
| `TContrainteMaxPresentielRessource` (5) | Massimo di ore di presenza | **P** |
| `TContrainteJEG` (2) / `TContrainteJoursEcourtesGarantis` | Gestione Entrate/Uscite | **E** |
| `TContraintePLG_DJT` (2) | **P**lages **L**ibres **G**aranties + **D**emi-**J**ournées **T**ravaillées | **G** |
| `TContrainteEcartMatieresDj` (2) | Scarto in mezze giornate fra materie | — |
| `TContrainteMaxDemiJourneesTravaillees` | Massimo di mezze giornate di lavoro | — |
| `TContrainteSeuilDemiJournee` (2) / `TContrainteSeulementDemiJournee` | soglia / `Lavorare solo mezza giornata al giorno` | — |
| `TContrainteCaCEcart`, `TContrainteCaCOrdre`, `TContrainteCaCQuinzaine`, `TContrainteCaCSuccession` | i quattro vincoli fra attività del §4 | I/O/Q/S |
| `TContrainteIndisponibilitesEtVoeuxRessource` | griglia indisponibilità **e preferenze** (§2.4) | — |
| `TContraintePoidsPedagogique` | Peso didattico | PP |
| `TContrainteSiteNbChangements`, `TContrainteSiteDureeTrajet`, `TContrainteSiteChangementPause` | vincoli di sede | S |
| **`TContrainteItalieProfReglementaire`** (3) | **vincolo normativo docente specifico Italia** | — |

⚠ `TContrainteItalieProfReglementaire` è l'unica classe di vincolo **paese-specifica
italiana** trovata. Non ho individuato l'etichetta UI corrispondente nel dizionario
stringhe — **da indagare**: potrebbe codificare un limite di legge italiano (ore
massime, giorni) che ci riguarda direttamente.

---

## 5. Alleggerimenti (`Assouplissements`) — la lista dei vincoli rilassabili

Questo è, di fatto, la **dichiarazione ufficiale di quali vincoli EDT tratta come hard
e quali sa rilassare**. Molto rilevante per il modello del solver. Tutte [STRINGA]:

| Chiave `FicAssouplissements_RS_…` | IT | FR |
|---|---|---|
| `RespectContraintes` | `Rispetta tutti i vincoli` | `Respect de toutes les contraintes` |
| `Assouplissement` | `Alleggerisci` | `Assouplissement` |
| `DeContraintes` | `Alleggerimento dei vincoli` | `Assouplissement de contraintes` |
| `MaxContraintes` | `Numero massimo di vincoli da alleggerire per risorsa:` | `Nombre maximum de contraintes à assouplir par ressource :` |
| `MaxHProf` | `Massimo di ore dei docenti` | `Maxima horaires des professeurs` |
| `MaxHClasse` | `Massimo di ore delle classi` | `Maxima horaires des classes` |
| `MaxHMat` | `Massimo di ore delle materie` | `Maxima horaires des matières` |
| `MaxPresentielProf` | `Presenza massima dei docenti` | `Maximum présentiel des professeurs` |
| `DemiJourneeTrav` | `Massimo 1/2 gg lavoro per i docenti` | `Maximum de 1/2 journées travaillées` |
| `DemiJourneeTravClasse` | `Massimo 1/2 gg lavoro per le classi` | `Maximum de 1/2 journées travaillées` |
| `PlagesLibres` | `Giorni e 1/2 giornate libere` | `Plages libres garanties` |
| `JoursEcourtesProf` | `Gestione Entrate / Uscite dei docenti` | `Horaires aménagés des professeurs` |
| `JoursEcourtesClasse` | `Gestione Entrate / Uscite delle classi` | `Horaires aménagés des classes` |
| `IncompMat` | `Incompatibilità materie` | `Incompatibilités matières` |
| `SuccMat` | `Sequenze indesiderate di materie` | `Successions interdites matières` |
| `PoidsPedag` | `Peso didattico delle materie` | `Poids pédagogiques des matières` |
| `ChangementSiteProf` / `ChangementSiteClasse` | `Cambi di sede dei docenti` / `… degli alunni` | `Changement de site des professeurs / des classes` |

Testo esplicativo integrale (utile: descrive la strategia a due passate del risolutore
EDT) [STRINGA]:

> `Il piazzamento delle attività scartate rispetta automaticamente tutti i vincoli.`
> (FR: `Par défaut le résoluteur automatique respecte toutes les contraintes.`)
> `Se dopo un primo calcolo rimangono delle attività scartate, potete alleggerire certi vincoli.`
> `Attivate l'opzione "Alleggerisci" e sbloccate i vincoli che desiderate alleggerire.
> Potete parametrare ogni vincolo. Il calcolo cercherà delle nuove soluzioni tenendo
> conto degli alleggerimenti definiti.`

Granularità del rilassamento (sempre a **quota**, mai "spegni il vincolo"):
`Autorizza un supplemento di …` `una volta per settimana e per docente.` /
`… e per classe.` / `una volta per ciclo …`; `Togli se necessario … mezze giornate
libere per settimana.`; `Non considerare le incompatibilità … per settimana e per
classe, una sola volta al giorno.`

---

## 6. Aule (`Salles`)

[STRINGA], famiglia `ScoGlossaireSalles_RS_*`:

| IT | FR | EN |
|---|---|---|
| `Capienza` / `Cap.` | `Capacité` / `Cap.` | `Capacity` |
| `Capienza inserita: AULA (numero di posti) - GRUPPO (numero minimo di posti per ognuna delle sue aule)` | `Capacité saisie : SALLE (nombre de places) - GROUPE (nombre de places minimum de chacune de ses salles)` | — |
| `Nr` / `Numero di aule (=1 per un'aula; > 1 per un gruppo)` | `Nb.` / `Nombre de salles (= 1 pour une salle; > 1 pour un groupe)` | — |
| `Gruppo di aule` | `Groupe de salles` | `Room group` |
| `Gestione del gruppo di aule` | `Gestion du groupe de salles` | `Room group management` |
| `Prenotabile da` | `Réservable par` | `Reservable by` |
| `Soglia di prenotazione` / `Numero di giorni prima dei quali può essere fatta una prenotazione` | `Seuil de réservation` | — |
| `Sede di appartenenza` | `Site d'appartenance` | `Adherent site` |
| `Categoria dei locali scolastici` | `Catégorie des locaux scolaires` | — |
| `Gestori` — `Personale o docente designato come "responsabile" dell'aula` | `Gestionnaires` | `Managers` |
| `Tasso di occupazione` | `Taux de remplissage` | `Occupancy rate` |
| `Numero di posti occupati` / `Numero di posti disponibili` | `Nombre de places occupées` / `restantes` | — |

**Risposta al punto aperto "vincoli di risorsa / occupazione simultanea di un
laboratorio"**: EDT lo modella come **gruppo di aule** con un **numero di occorrenze**
(`Nr` > 1). La capienza del gruppo è il *minimo* fra quelle delle sue aule. Ovvero
"max N in parallelo" = *gruppo con N aule*. **[INFERENZA]** dalla stringa
`Numero di aule (=1 per un'aula; > 1 per un gruppo)` + dal messaggio
`Attenzione, per alcuni gruppi di aule il numero di aule definito …`.

Diagnostica aule [STRINGA]:
`L'aula %s deve essere prenotata %d giorno/i prima`,
`Solo le aule prenotabili possono essere selezionate`,
`Dovete selezionare almeno un'aula prenotabile`.

---

## 7. Gruppi, sdoppiamenti, suddivisioni — **attenzione a un'inversione di termini**

Scoperta importante: la terminologia italiana di EDT **non** ricalca quella francese
1:1. Le coppie sono [STRINGA]:

| Francese | Italiano | Inglese |
|---|---|---|
| `partition` | **`Suddivisione`** | `Partition` |
| `groupe` | **`Raggruppamento`** | `Group` |
| `partie` | **`Gruppo`** | `Part` |
| `dédoublement` | **`Sdoppiamento`** | `Splitting` |

Prove letterali:

- `UtilitaireEDT_Dedoublement_RS_CreerEtRemplirDedoublementClick_Titre`:
  IT `EDT crea, al bisogno, i gruppi e i raggruppamenti dello sdoppiamento. Confermate?`
  ← FR `EDT va créer, si besoin, les parties et les groupes de dédoublement.`
- `ScoGlossaireGroupe_RS_CreerGroupeLong`: IT `Crea un raggruppamento` ← FR `Créer un groupe`.
- `ParametresSco_Ressources_RS_NommagePartitionArbitraire`: IT `Suddivisione` ← FR `Partition`.
- `UtilitairesEdt_ColonnesClasse_RS_MatiereLong`: IT `Materia dei gruppi` ← FR `Matière` (hint FR `Matière des parties`).

**Implicazione per `docs/edt/gruppi.md`**: quando la guida francese o l'inglese parlano
di *groupe*, in UI italiana si legge **raggruppamento**; quando parlano di *partie*, in
UI italiana si legge **gruppo**. Un modello dati che riusa "gruppo" per entrambi
sbaglia livello.

### Nomi di default delle suddivisioni [STRINGA]

`ParametresSco_Ressources_RS_Nommage*` — sono esattamente le sigle citate nel task:

| Chiave | IT | FR | EN |
|---|---|---|---|
| `NommagePartitionDedoublement` | `Sdoppiamento` | `Dédoublement` | `Splitting` |
| `NommagePartitionArbitraire` | `Suddivisione` | `Partition` | `Partition` |
| `NommagePartitionGarconsFilles` | `Maschio/Femmina` | `Fille/Garçon` | `Male/Female` |
| `NommagePartition1TiersDeuxTiers` | **`UnTerzoDueTerzi`** | `UnTiersDeuxTiers` | `OneThirdTwoThirds` |
| `NommagePartie1Tiers` | **`1Terzo`** | `1Tiers` | `1Third` |
| `NommagePartie2Tiers` | **`2Terzi`** | `2Tiers` | `2Thirds` |
| `NommagePartieGarcon` / `NommagePartieFille` | `Maschi` / `Femmine` | `Garçons` / `Filles` | `Male` / `Female` |
| `NommagePartieStandard` | `G` | `_` | `_` |
| `SuffixePartieDedoublement_ParDefaut` | `G.` | `P` | `BD.` |

Tipi di sdoppiamento (`TableAffEDT_Classe_RS_Dedoublement_*`) [STRINGA]:
`sdoppiamento - prima metà`, `sdoppiamento - seconda metà`, `sdoppiamento - un terzo`,
`sdoppiamento - due terzi`, `sdoppiamento - maschi`, `sdoppiamento - femmine`.

Regola strutturale [STRINGA]:
`FrameStructurePRVMEF_RS_InfoMatiereNonSpeDedoublee` →
`- per le ore in sdoppiamento, il numero di raggruppamenti per classe è sempre uguale a 2.`
(FR: `pour les heures dédoublées, le nombre de groupes par classe est toujours égal à 2.`)

Creazione [STRINGA]: `Crea lo sdoppiamento` (FR `Gérer le dédoublement`),
`Crea e riempi i raggruppamenti dello sdoppiamento`,
`Confermate la creazione di 2 nuovi raggruppamenti e di tutti i gruppi necessari?`,
`La suddivisione di sdoppiamento esiste già`.
Criteri di riempimento: `Alfabetico` / `Maschio/Femmina`.

### Attività complessa — modalità di sezionamento [STRINGA]

`FicCoursComplexe_RS_*` — i codici a 1–3 lettere che compaiono in UI:

| Codice IT | IT | FR |
|---|---|---|
| `S` | `Una lezione per docente (S)` | `Une séance par professeur (S)` |
| `SQ` | `Una lezione per docente ogni 15 giorni (SQ)` | `… pour chaque quinzaine (SQ)` |
| `SC` | `Una lezione per docente per ogni ciclo (SC)` | `… pour chaque cycle (SC)` |
| `SP` | `Una lezione per docente, gli alunni dipendono dal periodo (SP)` | `…, les élèves dépendent de la période (SP)` |
| `A` | `I docenti cambiano raggruppamento a metà dell'attività (A)` | `… changent de groupe à la moitié du cours (A)` |
| `AQ` | `… e si alternano ogni 15 giorni (AQ)` | `… alternent à chaque quinzaine (AQ)` |
| `AC` | `… e si alternano ad ogni ciclo (AC)` | `… alternent à chaque cycle (AC)` |
| `AP` | `I docenti cambiano raggruppamento ogni periodo (AP)` | `… chaque période (AP)` |
| `DP` | `Un unico raggruppamento cambia docente ogni periodo (DP)` | `… (PP)` |
| `CQ` | `I docenti cambiano classe ogni 15 giorni (CQ)` | `… (CQ)` |
| `CC` | `I docenti cambiano classe ad ogni ciclo (CC)` | `… (CC)` |
| `3R` | `3 raggruppamenti per 2 classi (3R)` | `3 groupes pour 2 classes (3G)` |

Codifica breve: `FicCoursComplexe_RS_CodageDedoublement` = IT `S`, FR `D`;
`CodageFilleGarcon` = IT `F/M`, FR `F/G`.

**Compresenza** = FR `Co-Enseignement` [STRINGA]: `Metti in compresenza`
(`Mettre en co-enseignement`), `Cancella la compresenza`,
`Un'attività di compresenza non può essere dettagliata.`
→ è la pista per IRC vs. alternativa citata negli aperti del progetto.

### Trasformazione / spezzamento in blocchi [STRINGA]

Finestra `FicTrans_RS_*`, titolo `Trasformazione in più attività`
(`Transformer en plusieurs cours`). Testo integrale della spiegazione:

> `Ogni linea corrisponde ad un tipo di attività, a cui potete modificare la DURATA,
> la FREQUENZA e il NUMERO di attività desiderato. Selezionate, attivandole, tutte le
> linee necessarie per definire la trasformazione desiderata.`
> FR: `Chaque ligne correspond à un type de cours, dont vous pouvez modifier la DURÉE
> et la FRÉQUENCE et en fixer le nombre d'exemplaires. …`

Altre etichette: `attività di una durata totale di`, `Settimanale` / `Hebdomadaire`,
`Regolare` / `Regulier`, `Quindicinale` / `en Quinzaine`, `a Ciclo Alternato` /
`en Cycle Alterné`, colonne `Classe intera` / `Sdoppiamento`,
`Ripercuoti sui servizi di tutte le classi con lo stesso piano di studi`
(FR `Répercuter sur les services de toutes les classes du MEF`).

Conferma quindi che i **blocchi di ore consecutive = durata dell'attività**, fissata
qui. `FicAffPreparationService_RS_FicServiceClassePRVNbCours` = `Nr attività` / `Nb. cours`.

---

## 8. Servizi del piano di studi — colonne A, Coeff., MS, Ridotto, Sdop., Spec.

Famiglia `InfoColonneEDT_ListeServicesPrevisionnels_RS_*` e
`InfoColonneSco_ListeServicesPrevisionnelsMEF_RS_*`. Tutte [STRINGA]:

| Colonna (IT) | Nome esteso IT | FR corto | FR esteso |
|---|---|---|---|
| **`A`** | `Stato di attivazione` | `A` | `État d'activation` |
| **`Coeff.`** | `Coefficiente` | `Pond.` | `Pondération` |
| **`MS`** | `Modalità di scelta` | `ME` | `Modalité d'élection` |
| `Classe` / `H/Classe` | `Durata a classe intera` | `Classe` | `Durée en classe` |
| **`Ridotto`** / `Ridotta` | `Durata alu. ridotti` | `Réduit(e)` | `Durée eff. réduit` |
| **`Sdop.`** | `Durata alu. sdoppiati` | `Ddb.` | `Durée eff. dédoublé` |
| `Alu.` | `Alunni inseriti` / `Alunni iscritti` | `Eff.` | `Effectif` |
| **`Alu./Rid.`** | `Alunni ridotti` | `El./Réd.` | `Effectif réduit` |
| `H. Alu.` / `H./Al.` | `Durata per alunno` | `H. El.` | `Durée par élève` |
| `Min/Max` | `Durata min/max a classe intera` | `Min/Max` | `Durée min/max en classe` |
| `Disciplina`, `Codice`, `Nome` | — | — | — |
| `P.S.` | `Piano di studi` | `MEF` | `MEF` (EN `ETM`) |

Valori della **Modalità di scelta** (`Type_ModaliteDElection_RS_ModaliteDElection_Code_*`)
[STRINGA] — i codici sono identici IT/FR:
`N` Normale · `O` Obbligatoria (EN `C`) · `F` Facoltativa (EN `O`) ·
`L` Accademica · `D` DNL · `R` Religioso · `X` Extra.

### `Spec.` — attenzione, è ambiguo [STRINGA + INFERENZA]

Ci sono **due** colonne abbreviate `Spec.` in italiano, con origini diverse:

1. `Chaines_ClientGraphiqueEdT_RS_FicAffServiceProfesseurMod` → IT **`Spec.`**, FR
   **`Mod.`**, EN `Mod.` — stessa cosa per `FicAffServiceClasseMod`,
   `FicAffListeMatiereGEP_RS_Mod`, `FicAffListeServiceGEP_RS_FicGEPModalite`.
   → Nelle liste **Servizi dei docenti / Servizi delle classi**, la colonna
   italiana `Spec.` è in realtà la **Modalità** (`Modalité d'élection`), **non** la
   specializzazione. Sembra una scelta (o un errore) del traduttore italiano.
2. `Chaines_ClientGraphique_RS_ColSepcialiteAbr` → IT `Spec.`, FR `Spéc.`,
   EN `Spec.`, esteso `Specializzazione` / `Spécialité`. Questa è la vera
   specializzazione del piano di studi (`Chaines_ClientsServeurs_RS_SpecialiteMEFLong`).

Quale delle due sia la colonna vista in `piani-di-studi.md` va deciso guardando in
quale griglia compare. **[INFERENZA]**: se è nella lista dei *servizi*, è la #1
(= Modalità di scelta).

---

## 9. TRCD / TRMD e bisogni previsionali

**TRCD è la resa italiana della sigla francese TRMD** [STRINGA]:
`Chaines_ClientGraphiqueEdT_RS_FicAffServiceProfesseurBesoinsTRMD` →
IT `TRCD` · FR `TRMD` · EN `DTMD (TRMD)`.
La chiave interna è `…BesoinsTRMD`, e la vista si chiama `FicAffPrevisionTRMD`.
**La DLL non contiene lo scioglimento della sigla in nessuna lingua** — ho cercato
"Répartition des Moyens" e simili senza risultati. **[INFERENZA]** dal contesto della
finestra (dotazione vs. bisogni per disciplina): TRMD = *Tableau de Répartition des
Moyens par Discipline*; TRCD sarebbe l'analogo italiano (*Tabella di Ripartizione delle
Cattedre per Disciplina*) — **non provato dal binario**, da confermare altrove.

Cosa contiene concretamente la vista TRCD [STRINGA], famiglia `FicAffPrevisionTRMD_RS_*`:

| IT | FR |
|---|---|
| `Gestione della vostra dotazione` | `Gestion de votre dotation` |
| `Dotazione` / `Bisogni` / `Scarto` | `Dotation` / `Besoins` / `Écart` |
| `Globale` | `Global` |
| `Ore posto` | `Heures poste` |
| `Bisogni derivanti dai servizi previsionali (colonna B)` | `Besoins issus des services prévisionnels (colonne B)` |
| `Bisogni in H.Suppl.` | `Besoins en HSA` |
| `Bisogni in ore posto (bisogni totali - bisogni in H.Suppl.)` | `Besoins en heures poste (besoins globaux - besoins en HSA)` |
| `Bisogni in IMP (colonna I)` | `Besoins en IMP (colonne I)` |
| `Dotazione globale - Bisogni globali` | `Dotation globale – Besoins globaux` |
| `Superamento dei plafond regolamentari (D. 2014-940 et 941):` | `Dépassement des plafonds réglementaires …` |
| `Coefficiente dinamico a partire dai servizi` | `Pondération dynamique à partir des services` |

**Nota:** questa vista è **fortemente legata alla normativa francese** (HSA, IMP,
décret 2014-940). Utile come conferma che TRCD in Italia è una traduzione di comodo di
uno strumento amministrativo francese → candidato ragionevole a **fuori scope**.

Modalità di calcolo dei bisogni [STRINGA]:
`FicListeClassePrev_RS_MsgModeCalcul` → `EDT propone 2 modalità di calcolo per i
bisogni previsionali e per la TRCD:` (FR `… pour les besoins prévisionnels et le TRMD :`).

Bisogni nella vista di preparazione [STRINGA], `FicAffPreparationAlignement_RS_*`:
`Bisogni` / `Besoins`; `Previsionale` / `Prévisionnel`;
`Calcolati in funzione del numero di alunni delle classi previsionali`
(FR `Calculés en fonction des effectifs des classes prévisionnelles`);
`Calcolati in funzione delle attività definite`.

---

## 10. Allineamenti

[STRINGA], `FicAffPreparationAlignement_RS_*` + `Glossaire_Alignement_RS_*`:

- `Allinea` / `Aligner`; `Cancella gli allineamenti` / `Désaligner` (e `Supprimer les alignements`).
- `Crea le attività` / `Créer les cours` ← il pulsante che chiude la Preparazione.
- `Allineamento dei servizi` / `Alignements des services`;
  `Allineamento delle classi` / `Alignement des classes`.
- **Semantica**, dalla colonna dei percorsi:
  `Tutti i raggruppamenti con la stessa lettera potranno avere attività contemporaneamente.`
  (FR `Tous les groupes ayant la même lettre pourront avoir cours en même temps.`)
  → l'allineamento è un **vincolo di simultaneità** fra gruppi/servizi.
- Precondizioni per allineare (utili come regole del modello):
  - `Per poter essere allineate, le attività devono avere lo stesso calendario.`
  - `Per poter essere allineate, le attività devono svolgersi lo stesso giorno.`
  - `Per poter essere allineate, le attività devono avere lo stesso stato di piazzamento o di blocco`
  - `Per poter essere allineate, le attività devono avere almeno un docente.`
  - `Per poter essere allineate, le attività devono avere lo stesso statuto rispetto agli intervalli`
  - `Le attività coinvolte nei vincoli tra attività non possono essere allineate`
  - `Le frequenze delle attività da allineare sono incompatibili.`
  - `Alcune risorse saranno occupate nello stesso momento.`
- Stampa: `Con la dicitura S per le ore di sdoppiamento` (FR `… la mention D pour les
  heures en dédoublement`) e `Con la dicitura R per le ore a numero di alunni ridotto`.
- `Definisci il numero di docenti supplementari` / `Désigner le nombre de professeurs supplémentaires...`

---

## 11. Colonne del docente / risorsa (utili per `docs/edt/docenti.md`)

[STRINGA]:

| Chiave | IT corto | IT esteso | FR corto | FR esteso |
|---|---|---|---|---|
| `UtilitairesEdt_ColonnesRessources_RS_App*` | `Mh/s` | `Monte ore settimanale` | `App.` | `Apport` |
| `…_Occ*` | `Occ.` | `Occupazione` | `Occ.` | `Occupation` |
| `…_OccupationType*` | `Occ. sett.` | `Occupazione settimana tipo` | `Occ. sem.` | `Occupation semaine type` |
| `…_OccupationAnnuelle*` | `Occ. ann.` | `Occupazione annuale` | `Occ. an.` | `Occupation annuelle` |
| `UtilitairesEdt_ColonnesProfesseur_RS_OccPrev_*` | `Occ. prev.` | `Occupazione previsionale` | `Occ. prév.` | `Occupation prévisionnelle` |
| `…_OccPrev_Hint` | — | `Occupazione previsionale (in funzione dei docenti desiderati)` | — | `… (en fonction des professeurs souhaités)` |
| `…_OccSim_*` | `Occ. simu.` | `Occupazione simulata` | — | `… (en fonction des professeurs proposés)` |
| `…_HSAPreRentrePrev_*` | `HS prev.` | `Ore supplementari previsionali` | `HSA prév.` | `Heures supplémentaires prévisionnelles` |
| `…_HSAPreRentreSimu_*` | `OSA simulate` | `Ore supplementari simulate` | `HSA simulées` | — |

**`Mh/s` = `Monte ore settimanale` = FR `Apport`** — chiude un dubbio: non è un
"massimo ore/settimana" ma il **monte ore contrattuale**. La stessa parola `Apport` è
tradotta `Monte ore` anche nella vista Consumo per disciplina
(`UtilitairesEdt_ColonnesConsoDiscipline_RS_Apport`).

Nota: `Chaines_ClientGraphiqueEdT_RS_WinAffVSProfesseurAffectation` traduce FR
`Affectation` con IT **`Statuto`** — quindi in almeno una griglia la colonna italiana
`Statuto` corrisponde all'**assegnazione**, non allo *statut* francese. **[INFERENZA]**:
attenzione a non confondere le due colonne `Statuto` (`Chaines_EdT_RS_WinColonStaLong`
= IT `Statuto` ← FR `Statut`).

---

## 12. Altre corrispondenze IT↔FR utili per leggere la UI

[STRINGA], sparse:

| IT | FR | EN |
|---|---|---|
| `Attività` | `Cours` | `Course` |
| `Lezione` (dentro attività complessa) | `Séance` | `Class meeting` |
| `Piano di studi` | `MEF` | `ETM` |
| `Materia` | `Matière` | `Subject` |
| `Disciplina` | `Discipline` | `Discipline` |
| `Fascia oraria` | `Séquence` | `Sequence` |
| `Quindicinale` / `Q1`, `Q2` | `Quinzaine` / `Q1`, `Q2` | `Fortnight` / `F1`, `F2` |
| `Ciclo alternato` | `Cycle alterné` | `Alternating cycle` |
| `Piazzamento` / `Attività scartate` | `Placement` / `échecs` | `Placement` / `failures` |
| `Trova una soluzione...` | `Lancer le résoluteur pas à pas ...` | `Launch the step-by-step solver` |
| `Alunni inseriti` | `Effectif` | `Population` |
| `Buco` | `Trou` | `Gap` |
| `Scarto` | `Écart` | `Differential` |
| `Sede` | `Site` | `Site` |
| `Intervallo` | `Récréation` | `Recess` |
| `Mensa` | `Demi-pension` | `Half-board` |
| `Docente coordinatore` | `Professeur principal` | `Homeroom teacher` |
| `Tasso di occupazione potenziale` (TOP) | `Taux d'occupation potentiel` | — |
| `Tasso d'occupazione reale` | `Taux d'occupation réel` | — |

---

## 13. Cosa NON sono riuscito a estrarre / limiti

1. **Lo scioglimento della sigla TRCD/TRMD** non esiste in nessuna delle 6 lingue
   della DLL. La sigla è usata sempre nuda.
2. **La corrispondenza lettera↔vincolo non è dichiarata esplicitamente** in una
   singola stringa: l'ho ricostruita incrociando `LettreBitmap*` (che dà la lettera)
   con `FicheEDT_FramePrefsContraintes_RS_*` (che dà il titolo) tramite l'acronimo
   francese nel nome della chiave (`RI` = Répartition Imposée, `MH` = Maximum Horaire,
   `MP` = Maximum Présentiel). È solida ma resta un'inferenza sui **nomi delle chiavi**,
   non una stringa che dica "D = Distribuzione oraria".
3. **`EDT Monoposto.exe`** (142 MB, Delphi) non è stato analizzato: le etichette UI sono
   tutte nella DLL, l'exe conterrebbe al più i nomi dei tipi RTTI (`TNetInfos…`), che
   erano già noti dal file `.edt`.
4. **I nomi dei tipi interni** (`TNetInfosContrainteEcart` ecc.) **non compaiono** nel
   dizionario delle stringhe: la mappa tipo→etichetta del §4 è inferenza semantica.
5. Non ho verificato **quali di queste voci siano effettivamente visibili** nella
   configurazione italiana del prodotto: la DLL contiene anche funzionalità
   francesi (HSA, IMP, STSWEB, Cyclades, LSU, Parcoursup) che in Italia potrebbero
   essere nascoste. `EDT Monoposto.distrib` contiene `PaysDistribution=ITALIE`, quindi
   **[INFERENZA]** esiste un filtro per paese che non ho ispezionato.
6. `Esempio.edt` (1.9 MB) nella cartella d'installazione non è stato aperto — è un
   dataset di esempio, potrebbe servire per confermare i tipi interni.

---

## 14. Come rifare / interrogare l'estrazione

I file di lavoro restano in scratchpad. Query tipiche:

```bash
# tutte le stringhe di una finestra
awk -F'\t' '$1 ~ /^FicheEDT_FramePrefsContraintes/' it_fr_en.tsv

# cercare a partire dal francese (più affidabile: è la lingua sorgente)
awk -F'\t' 'tolower($3) ~ /plages libres/' it_fr_en.tsv

# cercare a partire dall'italiano visto in UI
grep -i "massimo di ore di presenza" it_fr_en.tsv
```

Colonne di `it_fr_en.tsv`: `chiave · IT · FR · EN` (i `\n` interni sono resi `\n`).
