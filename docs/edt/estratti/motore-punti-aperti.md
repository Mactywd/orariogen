# Punti aperti del motore — chiusura dagli artefatti

Fonti: `it_fr_en.tsv` (69 888 stringhe IT/FR/EN), base demo `~/Desktop/EDT_COMPLETE/Esempio.edt`
(sola lettura). Marcatori: **[F]** fatto verificato · **[I]** inferenza · **[?]** non chiuso.

---

## 1. I «punti» della finestra Alleggerimenti — **non sono un punteggio del motore**

### 1.1 La finestra, ricostruita per intero

Famiglia di chiavi **`FicAssouplissements_RS_*`** (+ `FicAssouplissementParMatiere_RS_*`).
Testo d'intestazione, letterale:

| chiave | IT | FR |
|---|---|---|
| `FicAssouplissements_RS_Info1` | Il piazzamento delle attività scartate rispetta automaticamente tutti i vincoli. | Par défaut le résoluteur automatique respecte toutes les contraintes. |
| `FicAssouplissements_RS_Info2` | Se dopo un primo calcolo rimangono delle attività scartate, potete alleggerire certi vincoli. | Si après une première résolution il reste des échecs, vous pouvez assouplir certaines contraintes. |
| `FicAssouplissements_RS_Info3` | Attivate l'opzione "Alleggerisci" e **sbloccate** i vincoli che desiderate alleggerire. Potete parametrare ogni vincolo. | Cochez l'option "Assouplissement" et **déverrouillez** les contraintes… |
| `FicAssouplissements_RS_Parametrage1/2/3` | Sbloccate i vincoli da alleggerire e / selezionateli per **quantificare il margine** / **di manovra concesso al calcolo** | …pour quantifier la **marge de manœuvre accordée au résoluteur** |
| `FicAssouplissements_RS_RespectContraintes` | Rispetta tutti i vincoli | Respect de toutes les contraintes |
| `FicAssouplissements_RS_ValeursStandard` | Valori standard | Valeurs standards |

**Il tetto globale è un conteggio di vincoli, non un budget di punteggio** — **[F]**:

> `FicAssouplissements_RS_MaxContraintes`
> IT: **«Numero massimo di vincoli da alleggerire per risorsa:»**
> FR: «Nombre maximum de contraintes à assouplir par ressource :»

### 1.2 Le nove righe alleggeribili e la loro unità di misura

Ogni riga è «autorizza *N* volte una deroga», mai «costa *N*»:

| riga | testo IT (composto dalle sotto-chiavi) | unità |
|---|---|---|
| `ChangementSiteProf` / `ChangementSiteClasse` | Cambi di sede dei docenti / degli alunni — «Autorizza *N* cambi di sede in ogni momento» | conteggio |
| `DemiJourneeTrav` / `…Classe` | Massimo 1/2 gg lavoro — «Autorizza una volta per settimana *N* mattinate / pomeriggi di lavoro supplementari» | conteggio |
| `IncompMat` | Incompatibilità materie — «Non considerare *N* incompatibilità per settimana e per classe, una sola volta al giorno.» | conteggio |
| `SuccMat` | Sequenze indesiderate di materie — «Autorizza *N* sequenze indesiderate per settimana e per classe…» | conteggio |
| `MaxHClasse` / `MaxHMat` / `MaxHProf` | Massimo di ore delle classi / materie / docenti — «Autorizza un supplemento di *N* una volta per settimana e per classe.» | ore |
| `MaxPresentielProf` | Presenza massima dei docenti — idem | ore |
| **`PoidsPedag`** | **Peso didattico delle materie — «Autorizza un supplemento di *N* … un giorno per settimana.»** | **punti** |
| `PlagesLibres` | Giorni e 1/2 giornate libere — «Togli se necessario *N* mezze giornate libere per settimana.» | conteggio |
| `JoursEcourtesProf` / `…Classe` | Gestione Entrate/Uscite — «Togli se necessario *N* gestione mezza giornata per classe» | conteggio |

Ogni riga ha la variante `…Cycle2` («per ciclo» invece di «per settimana»): la quota si
dichiara **per settimana o per ciclo**, coerente col modello del tempo già documentato.

### 1.3 Che cosa sono i «punti»

Due sole chiavi in tutto il prodotto usano la parola — **[F]**:

```
FicAssouplissements_RS_FicAssouplissementFois    IT: volta    FR: fois
FicAssouplissements_RS_FicAssouplissementFoiss   IT: volte    FR: fois
FicAssouplissements_RS_FicAssouplissementPoint   IT: punto    FR: point
FicAssouplissements_RS_FicAssouplissementPoints  IT: pesi     FR: points
```

**[F]** `Fois`/`Foiss` e `Point`/`Points` sono **fratelli nella stessa famiglia**, con la stessa
struttura singolare/plurale: sono i **suffissi del contatore numerico** della riga, non entità
proprie. Sono i due soli suffissi presenti.

**[F]** Ricerca esaustiva su tutte le 69 888 stringhe: `point(s)` in colonna FR compare in
contesto di motore **solo qui**. L'unica altra occorrenza è
`ActionsEDT_Client_RS_ConsulterSnapshot` = «punto di ripristino» / `point de restauration`
(backup, non orario).

**[F] La traduzione italiana di `points` è «pesi»** — il traduttore di Index ha reso FR
`points` con IT *pesi*, cioè **unità di peso didattico**, non «punteggio».

**[I] Conclusione (solidità alta).** I «punti» sono l'**unità di misura del peso didattico**,
usata nell'unica riga il cui tetto non si conta né in ore né in occorrenze:
*Peso didattico delle materie → «Autorizza un supplemento di N punti, un giorno per settimana.»*
**Non esiste alcuna funzione di costo numerica nel motore di EDT.** Il compromesso resta
sempre e solo una **quota**: quanti vincoli per risorsa (`MaxContraintes`), quante volte per
settimana o per ciclo, e — per il solo peso didattico — di quanti punti si può sforare il tetto.

⚠ L'associazione punti ↔ riga `PoidsPedag` è un'inferenza, per quanto forzata (è l'unica riga
misurata in una grandezza che non sia ore o occorrenze). **Da confermare in UI** aprendo
`Elabora → Alleggerimenti` e leggendo il suffisso a destra dello spinner della riga
«Peso didattico delle materie». Costo: uno screenshot.

### 1.4 Ricadute laterali

- **[F]** L'alleggerimento **si può restringere per materia e per classe**:
  `FicAssouplissementParMatiere_RS_Cochez` = «Mettete la spunta alle materie da alleggerire per
  classe», con tre colonne — `Incompatibilità alleggerite`, `Massimo di ore alleggerito`,
  `Sequenze alleggerite`. Non è un interruttore globale.
- **[F]** L'alleggerimento è consultato anche fuori dal risolutore automatico:
  `FicheEDT_PlacerAmenagerAnnuel_RS_TenirCompteAssouplissements` = «Tieni conto degli
  alleggerimenti definiti» (pannello *Piazza e sistema*).
- **[F]** E la diagnostica lo cita: `AffSco_UtilDiagnostic_RS_Assouplissement` = «nel rispetto
  del limite di alleggerimento definito». La diagnosi sa distinguere *violato* da
  *violato-ma-entro-quota*.
- **[F]** Il cambio di sede ha un alleggerimento proprio, e la durata del tragitto vi rientra:
  `FicParametreEtablissementSites_RS_IgnorerDureeSaufToutMoment` — «(In caso di alleggerimento,
  la durata viene considerata per gli spostamenti "in qualsiasi momento")».

---

## 2. `Amenagement` e sostituzione — **una sola struttura**, e le tabelle omonime sono un falso amico

### 2.0 Trappola terminologica risolta prima di tutto

**[F]** Nelle 743 sezioni di `Esempio.edt` esistono quattro tabelle il cui nome contiene
`AMENAGEMENT` — e **nessuna delle quattro riguarda l'orario**:

| tabella | classe Delphi | record |
|---|---|---|
| `AMENAGEMENTPERSONNALISE` | `TNetAmenagementPersonnalise` | **0** |
| `CATEGORIEAMENAGEMENT` | `TNetCategorieAmenagement` | **0** |
| `AMENAGEMENTPROJET` | `TNetAmenagementProjet` | **0** |
| `RELATIONAMENAGEMENTPROJETINDIVIDUELELEVE` | `TNetRelationAmenagementProjetIndividuelEleve` | **0** |

**[F]** Le stringhe lo confermano: `EcnAffAmenagementProjet_RS_ProjetDaccompagnement` = *«%s -
Bisogni educativi speciali del tipo»* / FR *«Projet d'accompagnement de type»*;
`EcnAffConsultationAmenagements_RS_Amenagements` = *«Adattamenti da fare»* / *«Aménagements à
mettre en place»*. **È PRONOTE: PDP/PEI, adattamenti didattici per alunno.** Vuote in EDT.

**[F]** L'`aménagement` dell'orario si chiama, in chiaro:
`Chaines_ClientGraphique_RS_WinConstSuppressionCertainsAmenagements` =
*«Certe **modifiche dell'orario per settimana** saranno cancellate»* /
*«Certaines **modifications de l'emploi du temps à la semaine** vont être supprimées»*
(+ variante `…Cycles` per ciclo). E `Chaines_ClientGraphique_RS_ConfirmationSuppressionAmenagement`
= *«Confermate la cancellazione di questo **spostamento**?»*.

⚠ Terzo senso ancora: `FicMenusMenuPlacerAmenager` = *«Piazza e **sistema** l'attività in
diagnostica»* — qui `aménager` = riorganizzare, niente a che vedere con la settimana.

### 2.1 Dove stanno davvero gli `Amenagement`: dentro `COURS`

`CARTEIDENTITE` dichiara `NBCOURS=984`, `NBCOURSPLACES=984`, **`NBAMENAGEMENTS=141`**.
Ma la tabella `COURS` (`TNetCours`) ha **1224 record**, ident 986–5122 — le 240 eccedenti erano
il punto 7 di «cosa resta ignoto» in `formato-edt-analisi.md`. **Chiuso.**

**[F]** Il byte a **offset 8 del corpo** di `COURS` (già noto come «byte 0/1/2/4», mai
identificato) è la **natura dell'attività**:

| valore | n record | maschera settimane (off. 10–15) | place effettiva (off. 103) | identificazione |
|---|---|---|---|---|
| **0** | 1001 | `fe ff fb 7f ff 1f` = tutte le 44 settimane (999 su 1001) | valorizzata | **attività annuale** |
| **1** | 62 | **tutta a zero** | `ffffffff` | **consigli di classe** — vedi §2.4 |
| **2** | **141** | **un solo bit acceso** (es. `020000000000`, `000020000000`) | `ffffffff` | **`Amenagement`: attività su UNA settimana** |
| **4** | 20 | **più bit contigui** (es. `000000387800`) | `ffffffff` | attività su **più settimane** |

**[F] 141 = `NBAMENAGEMENTS` esatto.** L'`Amenagement` **non è una tabella**: è **una riga di
`COURS` con la maschera delle settimane ridotta a una sola settimana**. Stessa entità, stesso
schema, stessi campi (place, durata, materia, risorse) delle attività annuali.

### 2.2 La sostituzione usa **la stessa struttura** — verificato sui dati

**[F]** `RELATIONCOURSSUBSTITUT` (`TNetRelationCoursSubstitut`, 161 record, 37 byte):

```
ArTi | uint32 ident | uint32 COURS_originale | uint32 COURS_sostituto | …
```

**[F]** Verifiche incrociate su tutti i 161 record:

| verifica | risultato |
|---|---|
| natura del COURS **sostituto** | **141 di natura 2 + 20 di natura 4 = 161** — nessun'altra |
| natura del COURS **originale** | **161/161 di natura 0** (annuale) |
| **docente diverso** fra originale e sostituto | **159 / 161** |
| classe identica | **161 / 161** |
| aula identica | **161 / 161** |
| collocazione (`place`) identica | 155 / 161 |
| durata identica | 151 / 161 |
| materia identica | 129 / 161 |

**[F] I 141 `Amenagement` sono esattamente i sostituti su una settimana.**
L'insieme dei sostituti coincide, senza residui, con l'unione delle nature 2 e 4.

**[I] Conclusione (solidità molto alta): una tabella sola.** Sostituire un docente per un'ora
significa creare **una nuova riga in `COURS`** — stessa classe, stessa aula, stessa
collocazione, docente diverso — con la maschera settimane ridotta alla settimana interessata, e
collegarla all'attività annuale con una riga di `RELATIONCOURSSUBSTITUT`. **Non esiste una
tabella «sostituzione» distinta dagli spostamenti settimanali.** «Spostare un'ora per una
settimana» e «far coprire un'ora da un altro docente» sono **lo stesso atto sul modello dati**;
cambia solo quale campo del sostituto differisce dall'originale (place, oppure docente).

### 2.3 Il contorno: cancellazione e sostituzione lunga

**[F]** `ANNULATIONCOURS` (`TNetAnnulationCours`, 807 record, 46 byte) — `uint32` a offset 8 =
ident del COURS, **807/807 di natura 0**, 483 originali distinti. È la **soppressione di
un'occorrenza dell'attività annuale**. Dei 122 originali sostituiti, **112 compaiono anche in
`ANNULATIONCOURS`**: il pattern normale è *annulla l'annuale su quella settimana + crea il
sostituto*.

**[F]** `REMPLACEMENTLONG` (`TNetRemplacementLong`, **3 record**, 32 byte). Record letterale:

```
41 72 54 69 | 03 00 00 00 | 97 01 00 00 | 64 00 00 00 | <double> | <double>
   ArTi        ident=3      0x197 = 407    0x64 = 100    inizio      fine
```

- **[F]** 407 e 415 esistono in `ABSENCERESSOURCE`, e **entrambi i record hanno il valore 37 a
  offset 21** = docente 37.
- **[F]** I **20** COURS di natura 4 (multi-settimana) sostituiscono **tutti** il docente **37**
  con il docente **100** — lo stesso 100 che è il secondo campo di `REMPLACEMENTLONG`.

**[I] Catena completa (solidità alta):**
`ABSENCERESSOURCE` (assenza del doc. 37) → `REMPLACEMENTLONG` (doc. 100, intervallo di date) →
**20 righe `COURS` di natura 4** → `RELATIONCOURSSUBSTITUT` → le attività annuali.
`REMPLACEMENTLONG` è solo la **testata** amministrativa della supplenza: **le ore restano
normali righe di `COURS`.** Un'unica meccanica di piazzamento, tre livelli di intestazione.

**[F]** `DEMANDEREMPLACEMENT` (`TNetInfosDemandeRemplacement`): **0 record**, `maxIdent = 22`
(quindi in passato popolata). `RELATIONREMPLACANTMATIERE` e
`RELATIONREMPLACANTNIVEAUINCOMPATIBLE`: 0 record — sono i **criteri di scelta del supplente**
(materia insegnabile, livello incompatibile), coerenti col fatto già documentato che le
sostituzioni **non hanno un solver** ma un filtro multi-criterio.

### 2.4 Sottoprodotto: `MODIFICATIONCOURS` non è ciò che sembrava

**[F]** `MODIFICATIONCOURS` (`TNetModificationCours`, 1224 record, 26 byte) ha **esattamente un
record per ogni riga di `COURS`** (1224/1224, biiettiva, tutti gli ident risolvono). Layout:
`ArTi | ident | uint32 COURS | byte origine | double TDateTime | 02 | byte`.
**[I]** È un **log di ultima modifica**, non una tabella di eccezioni. Il nome inganna.

**[F] Bonus:** i **62** COURS di natura 1 hanno maschera settimane **nulla**, materia costante,
e come risorse **esattamente una classe + un'aula, mai un docente**. `CARTEIDENTITE` dichiara
**`NBCONSEILS = 62`**. **[I]** Sono i **consigli di classe**, memorizzati come attività nella
stessa tabella `COURS` — conferma sui dati che colloqui/consigli e orario condividono il
modello, non solo lo schema a tre stadi.

### 2.5 Ricaduta di progetto

Il modello è **`attività annuale` + `eccezione datata` nella stessa tabella**, distinte da una
maschera di settimane e legate da una relazione sostituto→originale. Per il SaaS di
sostituzioni del committente è la conferma che **non serve un modello dati separato per le
supplenze**: una supplenza è una lezione con la stessa classe, la stessa aula, la stessa
collocazione, un docente diverso e una validità di una settimana.

---

## 3. Le tre domande minori

### 3.1 «Aree mobile» (FR `Espaces mobiles`) — **né vincolo né risorsa: è PRONOTE**

**[F]** Tutte le occorrenze, colonna EN inclusa:

```
ScoHttpNavigateur_RS_RedirectionEspaceMobile_Professeurs
   IT: l'Area Mobile Docenti | FR: l'Espace Mobile Professeurs | EN: Mobile Teachers Webspace
RequetesVisu_PublicationSurInternet_RS_NomMobile_Eleves
   IT: Area Mobile Alunni    | FR: Mobile Élèves              | EN: Cellphone Students
```

Varianti: Alunni, Genitori, Docenti, Tutor, Aziende, Segreteria, Doposcuola.

**[F]** L'unica occorrenza in un contesto di griglia oraria è
`FrameSco_PersoHorairesSequences_RS_InfosEspaces`: *«Sulle Aree mobile l'orario di fine viene
visualizzato solo se diverso da quello di inizio»* / EN *«On the **Mobile Webspaces**…»* — cioè
**come le etichette delle sequenze si rendono sul portale mobile**.

**Conclusione (solidità massima, la colonna EN è dirimente):** sono i **portali web mobili di
PRONOTE**, un canale di pubblicazione. Nessun rapporto con aule, spazi o piazzamento.
**Falso amico da annotare**: «Area/Espace» qui non è uno spazio fisico. **Fuori scope.**

### 3.2 L'intervallo occupa una `Place`? — **no: è un separatore fra ranghi**

Prova sui dati della base demo — **[F]**:

- `SEQUENCEHORAIRE` (`TNetSequenceHoraire`): **10 record**, ranghi 0–9, etichette `"1"`…`"10"`.
- `LIBELLEHORAIRE` (`TNetLibelleHoraire`): **22 record** = 11 inizi + 11 fini, orari
  `0.3333…0.75` = **08:00 → 18:00**, dieci fasce da un'ora.
- `RECREATION` (`TNetRecreation`): **tabella propria, 2 soli record**:

```
ArTi | 1 | "Intervallo del mattino"     | uint32 = 2 | uint32 = 0 | 01 01
ArTi | 2 | "Intervallo del pomeriggio"  | uint32 = 4 | uint32 = 0 | 01 02
```

L'intervallo è **un'etichetta + un indice di rango** (2 e 4), non una fascia oraria propria.

- **[F] Prova decisiva:** distribuzione dei ranghi delle 1001 attività annuali piazzate —
  `{0:216, 1:117, **2:168**, 3:141, **4:162**, 5:119, 6:**0**, 7:40, 8:16, 9:22}`.
  **I ranghi 2 e 4 sono fra i più usati.** Se l'intervallo consumasse un rango sarebbero vuoti.
  (Il rango **6** è l'unico vuoto: è la mensa.)

Conferme dalle stringhe — **[F]**:

- `ActionsEDT_Client_RS_FicMenusExtraireCoursAvecRecreation` = *«Estrai le attività **a cavallo
  dell'intervallo**»* / *«cours **chevauchant** une récréation»* — un'attività può **attraversare**
  un intervallo: impossibile se l'intervallo fosse una collocazione occupata.
- `FicParametreEtablissementRecreations_RS_DeplacerLesTraitsRecreations` = *«Spostate le **linee
  gialle** sulla griglia per definire l'orario degli intervalli»* — una **linea**, non una cella.
- `FicEDT_FrameCours_RS_PlageAvecInterclasse` = *«Il rispetto degli intervalli è incompatibile
  con la durata dell'attività.»* — il vincolo è *non attraversare la linea*.
- `FicheEDT_CreationCours_RS_Interclasses` = *«Rispetta gli intervalli»*: **flag per attività**.
- `FicheEDT_PlacementAuto_RS_RecreationsActives` / `…Inactives`: gli intervalli si **attivano e
  disattivano** globalmente prima del calcolo.
- `NONRESPECTCLASSERECREATION` (`TNetNonRespectClasseRecreation`, 0 record): **eccezione per
  classe** al rispetto degli intervalli.

**Conclusione (solidità massima, dati + stringhe concordi): l'intervallo è un separatore
ancorato a un indice di rango, non consuma `Place`.** Modello: `Place` = `giorno × 10 + rango`
invariato; l'intervallo è un insieme di *confini* `{2, 4}` e il vincolo «rispetta gli
intervalli» vieta a un'attività di durata > 1 di attraversarne uno. Flag per attività, con
disattivazione globale ed eccezione per classe.

⚠ Nota terminologica IT: **«intervallo» traduce sia `récréation` sia `interclasse`**
(`WinEtatGestionInterclasses` → «Gestione degli **intervalli**» ma FR «Gestion des
**récréations**»). Da tenere in conto nel glossario.

### 3.3 Tempo di spostamento fra sedi — **per coppia di sedi e orientato**

**[F]** Famiglia `FicParametreEtablissementSites_RS_*`, colonne della griglia:

```
_SiteA   IT: Sede A   FR: Site A
_SiteB   IT: Sede B   FR: Site B
_Sens    IT: Verso    FR: Sens
_Duree   IT: Durata   FR: Durée
```

**[I] È una tabella `(sede A, sede B, verso, durata)`: la durata è per coppia, e il campo
`Verso` la rende orientata** (A→B può costare diversamente da B→A). Solidità alta: quattro
colonne che, insieme, non hanno altra lettura.

**[F]** Attorno, i parametri **globali**, distinti per popolazione:

- `_CaptionChangementProf` «Cambio di sede docenti / personale» e `_CaptionChangementClasses`
  «Cambio sede delle classi» — **due blocchi separati**.
- `_PermettreChangement` «Permetti il cambio», `_Pauses` «Nelle pause»,
  `_MaximumDeChangements` «Numero massimo di cambi di sede», con `_ParJour` / `_ParHebdo` /
  `_ParCycle`.
- `_AucuneRecreActive` «**Nessun intervallo è attivo: il cambio tra queste sedi sarà vietato**»
  — **[F]** il cambio di sede è **agganciato agli intervalli**: senza intervalli, vietato.
- `_IgnorerDureeSaufToutMoment` «Ignorare la durata del cambio di sede per gli spostamenti
  "durante le pause" e "durante gli intervalli"».
- `_SiteUtiliseSupprimable` «alcune sedi sono utilizzate da **aule e/o attività**» — la sede è
  un attributo sia dell'aula sia dell'attività.

Causali di diagnostica corrispondenti — **[F]**:
`AffSco_UtilDiagnostic_RS_SitesIncompatiblesHeureTransition` = «Cambio di sede **al di fuori
delle pause definite**»; `…Recreation` = «al di fuori degli intervalli».

**Conclusione:** **durata per coppia orientata**, dentro una cornice di parametri globali
(permesso, momento consentito, numero massimo per giorno/settimana/ciclo), separati per docenti
e per classi. Non è un solo numero globale.

---

## 4. Cosa resta da guardare in UI

1. **Alleggerimenti → riga «Peso didattico delle materie»**: leggere il suffisso a destra dello
   spinner, per confermare che è lì che compaiono i «punti». (§1.3) — l'unico anello inferito.
2. **Alleggerimenti**: verificare che ogni riga sbloccabile abbia il proprio lucchetto e che
   `Numero massimo di vincoli da alleggerire per risorsa` sia un campo unico in fondo. (§1.1)
3. **Parametri → Sedi**: uno screenshot della griglia `Sede A / Sede B / Verso / Durata`
   chiuderebbe §3.3 da inferenza a osservazione.
4. **`Amenagement`**: aprire un'attività con eccezione settimanale in `Orario` e verificare che
   la UI la presenti come *variante della stessa attività* e non come attività nuova. (§2.2)

## 5. Punti aperti **non** chiusi

- **[?]** Il byte a offset 12 di `MODIFICATIONCOURS` (11 valori, dominante 22 su 986 record) —
  origine della modifica (utente? risolutore?). Non determinato.
- **[?]** La **scala** del peso didattico (valori ammessi, default): trovate le colonne
  (`Chaines_EdT_RS_Col_PoidsMatiereHint` = «Peso unitario per materia e per ora») e i totali per
  mattina/pomeriggio/giornata, ma **nessuna stringa dichiara l'intervallo dei valori**.
  Va letto dalla tabella `MATIERE` della base o osservato in UI.
- **[?]** I 3 record di `REMPLACEMENTLONG` contro 20 attività multi-settimana: la relazione
  «una supplenza lunga → N attività» è coerente ma non ho verificato l'aggancio riga per riga.
