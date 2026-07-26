# Estratto — le risorse di piazzamento non ancora documentate

Fonte: `it_fr_en.tsv` (69 888 stringhe IT/FR/EN, chiavi `<Finestra>_RS_<Campo>`),
più incroci mirati. Nessuna stringa dallo schema XSD o dai `.edt` è stata
necessaria in questa passata: il glossario da solo risponde alle quattro
domande.

⚠ Il binario è condiviso con PRONOTE. Ogni sezione segnala esplicitamente
cosa è dubbio/PRONOTE.

---

## 0. La pipeline di coerenza conferma le CINQUE risorse di piazzamento

**[STRINGA]**, famiglia `FicCoherenceBase_RS_Etape*` (il testo del pannello
"Verifica della coerenza della base" mostrato prima del piazzamento):

| Fase | IT | FR |
|---|---|---|
| `EtapeOccupationDesClasses` | Controllo dell'occupazione delle classi | Contrôle de l'occupation des classes |
| `EtapeOccupationDesProfesseurs` | Controllo dell'occupazione dei docenti | Contrôle de l'occupation des professeurs |
| `EtapeOccupationDesSalles` | Controllo dell'occupazione delle aule | Contrôle de l'occupation des salles |
| `EtapeOccupationDesPersonnels` | Controllo dell'occupazione del **personale** | Contrôle de l'occupation des personnels |
| `EtapeOccupationDesMateriels` | Controllo dell'occupazione dei **materiali** | Contrôle de l'occupation des matériels |

Ognuna ha un dettaglio identico nella forma: *"EDT verifica che tutte le
attività possano essere piazzate tenendo conto delle indisponibilità e dei
vincoli di [risorsa]"*. Più due controlli incrociati: `EtapeCroiseeParClasse`
(coerenza dei consigli di classe) e `EtapeCroiseeParProf` (coerenza dei
servizi), e uno per materie (`EtapeMatieres`) e uno per insiemi di risorse
condivise (`EtapeDispoClique`).

**[INFERENZA]** Le risorse di piazzamento della griglia oraria sono
esattamente **cinque, sullo stesso piano**: Classi, Docenti, Aule, Personale,
Materiali. Non c'è una fase equivalente per alunni o responsabili — vedi §4.

---

## 1. Il personale (ATA/educatori) — è una risorsa piazzabile

**Risposta alla domanda 1: sì, con hard limits.** Il personale condivide
esattamente il meccanismo di indisponibilità/occupazione di docenti e aule,
ed esistono attività ("cours") a cui il personale è assegnato.

### Indisponibilità e occupazione (identiche a docenti/aule)

**[STRINGA]**
- `AffSco_UtilDiagnostic_RS_IndispoPersonnel` → "La risorsa del personale ha una indisponibilità" / "Le personnel a une indisponibilité"
- `AffSco_UtilDiagnostic_RS_IndispoSouplePersonnel` → "...indisponibilità **opzionale**" / "...indisponibilité **optionnelle**" (stesso schema a due livelli hard/soft già visto per docenti/aule)
- `AffSco_UtilDiagnostic_RS_FicRubriPersonnelOccupeCours` → "La risorsa del personale è già occupata in un'attività" / "Le personnel est déjà occupé dans un cours"
- `AffSco_UtilDiagnostic_RS_PersonnelOccupeCoursPrioritaire` / `NonPrioritaire` → distinzione priorità identica a quella usata per le altre risorse
- `Chaines_ImpressionEdT_RS_AutorisationPersonnelSaisie` → "Autorizza al personale l'inserimento di indisponibilità" (il personale può inserire da sé le proprie indisponibilità, come i docenti)

### Il personale compare in attività ("cours")

**[STRINGA]**
- `ScoGlossairePersonnel_RS_HintFonction` = "Educatore" (`Type_GenreFonctionPersonnel_RS_Accompagnant` = "Accompagnant"/"Chaperone") — funzione dedicata
- `Chaines_ClientGraphique_RS_SouhaitezVousMajCoursAccompagnementDuPersonnel` → "Volete anche aggiornare le **attività di accompagnamento** del personale interessato dalle vostre modifiche?" — **[INFERENZA]** conferma che l'Educatore ha attività proprie in orario (probabile: affiancamento di un alunno con bisogni educativi speciali)
- `Chaines_ClientGraphiqueEdT_RS_Activitescomplementairespersonnelles` → "Attività complementari personali (ACP)" / "Activités complémentaires personnelles (ACP)" — attività extra assegnate, entrano nel calcolo ore (v. §3)
- `AffEDT_SelecRessource_RS_PersonnelsAdherents` → "Personale aderente agli incarichi" / "Personnels adhérents aux missions" — il personale (non solo i docenti) può aderire a un "incarico" (v. §3)
- `EditSco_EngagementMissionComplementaire_RS_RetraitMission_D` → "Quando si rimuove un incarico dai **docenti/personale**, lo si rimuove anche dalle loro **attività**" — **[STRINGA] conferma diretta**: un incarico genera un'attività nell'orario, sia per docenti sia per personale

### Il personale ha anche un modulo di riunioni distinto ("Rencontre"/Colloqui/Consigli)

**[STRINGA]** `FrameSco_IndispoRencontre_RS_*`, `FicheEDT_ListePersonnelConseil_RS_*`:
Il personale (in particolare i ruoli di segreteria/direzione) partecipa come
"Presidente, Segretario e altri" ai **consigli di classe** (`Conseil De
Classe`), con indisponibilità proprie per sessione
(`FrameEDT_IndispoConseil_RS_IndispoConseilSansSessionPersonnels`) e una
colonna di occupazione dedicata: `FicheEDT_ListePersonnelConseil_RS_HintOccupationPersonnel`
= "Occupazione: totale di ore di consigli in cui il personale è occupato
nella sessione". **[INFERENZA]** Questo è un secondo motore di piazzamento
distinto da quello della griglia oraria settimanale (i consigli/colloqui
sono eventi di sessione, non lezioni ricorrenti), ma usa lo stesso concetto
di risorsa + indisponibilità + occupazione.

### Ruoli osservati (`Type_GenreFonctionPersonnel`)

**[STRINGA]**, elenco completo: Educatore (Accompagnant), Admin Comune,
Amministrativo, Segreteria (Direzione / Vita Scolastica), Sorveglianza
(Encadrement), Gestione (Intendance), Comune (Mairie), Medico, Doposcuola
(Périscolaire), Psic. E.N., Sociale, Tutor.

**⚠ Confine con PRONOTE**: la maggior parte dei campi di `ScoGlossairePersonnel`
(chat alunni/genitori, SMS, sanzioni, contatto segreteria, `Espace
Accompagnant`/webspace) sono **[INFERENZA] quasi certamente PRONOTE**
(gestione vita scolastica, comunicazione). Solo Educatore/Accompagnamento e
la partecipazione ai consigli sono **[INFERENZA]** plausibilmente EDT
(piazzamento).

---

## 2. I materiali — vincolo hard di quantità, non solo prenotazione

**Risposta alla domanda 2: hard constraint per quantità**, modellato
**esattamente come le aule** (stessa finestra: "Aule e materiali").

### Il materiale ha un orario proprio

**[STRINGA]** `ScoGlossaireMateriel_RS_AffichageEDT` → "Orario" / "Emploi du
temps" / "Timetable": il materiale ha una vista orario dedicata, come aule e
docenti.

### La quantità è un vincolo enforced, non solo informativo

**[STRINGA]**, famiglia `UtilitaireSco_Materiel_RS_*`:
- `ModificationImpossibleNombreOccurrencesTropPetit_SD` → *"Il materiale %0:s
  non può essere modificato poiché %1:d quantità di questo materiale sono
  utilizzate **simultaneamente**"* / *"...car %1:d occurrences de ce matériel
  sont utilisées **simultanément**"* — **prova diretta**: il sistema blocca
  la riduzione della quantità se supererebbe l'uso simultaneo già piazzato.
- `ModificationImpossibleNombreMaterielsTropGrand_SD` → quantità limitata a
  un massimo.
- `ErreurNbOccurrences_DD` → "La quantità deve essere compresa tra %0:d e %1:d".

**[STRINGA]** `SelectionSco_Ressource_RS_HintTitreNbOccMateriel` → *"Per il
materiale, quantità da inserire nelle attività / quantità disponibile"* — 
un'attività può richiedere **N unità** di un materiale (es. 5 portatili),
verificate contro il totale disponibile.

**[STRINGA]** `FicCoherenceBase_RS_EtapeOccupationDetailDesMateriels` → *"EDT
verifica che tutte le attività possano essere collocate tenendo conto delle
**indisponibilità e dei vincoli** relativi ai materiali"* — il materiale
partecipa alla stessa fase di verifica di coerenza pre-piazzamento delle
altre risorse.

### Indisponibilità del materiale (hard/soft, identica alle altre risorse)

**[STRINGA]**
- `AffSco_UtilDiagnostic_RS_IndispoMateriel` → "Il materiale ha un'indisponibilità"
- `AffSco_UtilDiagnostic_RS_IndispoSoupleMateriel` → "...indisponibilità opzionale"

### Colonne del materiale (`UtilitairesEdt_ColonnesMateriel`)

**[STRINGA]**, elenco completo (22 stringhe, già ridotto a coppie
corto/lungo): Nome (max 30 caratteri), Quantità (`Nb. occurrences`), Gestori
(docente o personale "responsabile", destinatario email), Informazioni
libere, Picco d'occupazione, Prenotabile da (docenti/personale, per
settimana o per **ciclo**), Limite di prenotazione (`Seuil` = giorni di
preavviso richiesti).

**[INFERENZA]** Il modello del materiale è quindi identico a quello
dell'aula già documentato in `docs/edt/aule.md`: quantità scalare (come il
campo `Qtà`/Numero di aule), indisponibilità a tre pennelli, prenotabilità
per whitelist, nessun vincolo di "tipo"/categoria dichiarato (nessuna
stringa suggerisce categorie o tipologie per il materiale, a differenza
delle aule che hanno `CategoriesSalle` e `Tipologie`).

---

## 3. Gli incarichi del docente — SÌ, incidono sul monte ore (domanda aperta chiusa)

**Risposta alla domanda 3: sì.** La formula delle ore supplementari (HSA) è
esplicita nel glossario e include i termini extra-insegnamento:

**[STRINGA]** `FicheEDT_ServiceProfesseur_RS_HeuresSupp`:
> IT: *Ore supplementari = Durata/Coeff. + Extra - Monte ore*
> FR: *Heures supplémentaires = Durée/Pond. + ARE - Heures étab.*
> EN: *Overtime hours = Duration/Weight + ARE - Inst. hours*

**[STRINGA]** `FicheImpEDT_EtatsDeServices_RS_FormuleHSA` (variante estesa):
> IT: *(H.att + H.pond + ACP + CC) - Monte ore*
> FR: *(H.enseignées + H.pond + ACP + CSD) - Apport*
> EN: *(TaughtHr. + WeightedHr. + PSA + ASG) - Provision*

Decodifica dei termini (tutti confermati da hint separati):

| Sigla | IT | FR | Significato |
|---|---|---|---|
| **Monte ore / Apport** | Monte ore | Apport | il monte ore contrattuale (`Mh/s`, già in `docs/edt/docenti.md`) |
| **ARE / AHE** | Extra (Ist.) | ARE (Établissement) | `FicheEDT_ServiceProfesseur_RS_HintAHEE`: *"Attività extra Insegnamento a carico dell'istituto"* / *"Activité à Responsabilité Établissement"* — attività estranee alla didattica ma **a carico dell'istituto**: **aggiungono** ore al monte ore dovuto |
| **ARA / Decharge** | Extra (Uff. scol.) | ARA (Académie) | riduzione oraria a livello di Ufficio Scolastico Regionale/Ministero (esonero) — **sottrae** dalle ore dovute: `HintHeuresEtab`: *"Ore dovute all'istituto: Monte ore - Extra - CC"* / *"Apport - ARA - CSD"* |
| **CSD / CC** | Controllo del servizio | Contrôle du service | `UtilitairesEdt_ColonnesRessources_RS_CDS`: *"Controllo del servizio (HS: Ore supplementari, SI: Servizi Incompleti)"* — flag/aggiustamento manuale di verifica del servizio |
| **ACP** | Attività complementari personali | Activités complémentaires personnelles | attività extra assegnate (anche al personale, v. §1) che **si sommano** alle ore insegnate nel computo |
| **IMP** | IIP (probabile refuso IT per "Indennità Incarico Particolare") | IMP (*Indemnité pour Mission Particulière*) | **[STRINGA]** `FicheImpEDT_EtatsDeServices_RS_TitreIndemnitesIMP`: *"Indennità per missione particolare (IMP) - pagamento annuale"* — **compenso monetario annuale**, tracciato in una scheda previsionale separata (`FicAffPrevisionTRMD`: Dotazione IMP - Bisogni IMP = Scarto), **non** un termine della formula HSA sopra |

**[INFERENZA]** Quindi: **AHE/ARE** (extra a carico dell'istituto) e **ACP**
(attività complementari) **aumentano** le ore effettive di servizio contate;
**ARA/Decharge** (esonero) **riduce** le ore dovute. L'**IMP** è un compenso
economico separato (indennità annuale), non entra nella formula oraria — è
gestito a parte nella "TRCD/TRMD" (già segnalata come area francese-only nel
progetto).

**[STRINGA] Conferma indipendente**: `EditSco_EngagementMissionComplementaire_RS_RetraitMission_D`
→ rimuovendo un "incarico" (mission) da un docente o dal personale, **lo si
rimuove anche dalle loro attività piazzate in orario**. Gli incarichi
generano quindi attività schedulate, non solo righe contabili.

### ⚠ Il sistema IMP/PACTE è francese-specifico — chiude anche il dubbio TRCD

**[STRINGA]** `UtilitaireColonneSco_MissionComplementaire_RS_HintTitreMissionCode`
→ *"Codice per gli incarichi svolti nell'ambito degli incarichi docenti"* /
*"Code des missions réalisées dans le cadre du **PACTE enseignant**"* — il
"Pacte enseignant" è una riforma francese del 2023 per le missioni
aggiuntive dei docenti. **[INFERENZA]** Questo conferma e chiude il dubbio
già aperto nel progetto su `TRCD`/`TRMD`: l'intero impianto IMP/PACTE/HSA è
un meccanismo normativo-contrattuale **francese** (decreto 2014-940 +
riforma PACTE 2023), estraneo al sistema italiano (che usa FIS, incarichi
aggiuntivi, ecc. con logiche diverse). **Da dichiarare fuori scope.**

`Type_Engagement` (rappresentante di classe, eco-delegato, membro
associazione sportiva...) è invece **[INFERENZA] quasi certamente PRONOTE**
(impegni civici/associativi degli **alunni**, non incarichi docente) — da
non confondere con `EditSco_EngagementMissionComplementaire` (incarichi di
docenti/personale) nonostante il nome di famiglia simile.

---

## 4. Alunni e responsabili — solo anagrafica + modulo colloqui, NON la griglia oraria

**[STRINGA]** Nessuna fase `FicCoherenceBase_RS_Etape*` menziona alunni o
responsabili (l'elenco completo è: Classi, Docenti, Aule, Personale,
Materiali, più le due verifiche incrociate e quella sulle materie — v. §0).
**[INFERENZA]** Alunni e responsabili **non sono risorse del motore di
piazzamento della griglia oraria settimanale**.

Dove compaiono comunque:
- **Alunno dissociato** (`élève détaché`): meccanismo puntuale per
  formazione classi/gruppi con alunni nominativi — `AffSco_UtilDiagnostic_RS_EleveOccupeClasseOuPartie`,
  `IndispoEleve`, `DebutCoursInterditEleveDetache`. **[INFERENZA]** Rilevante
  solo se si modella la Formazione classi con alunni nominativi — il
  progetto l'ha già dichiarata fuori scope ("si salta senza anagrafica
  alunni", changelog 2026-07-15).
- **Consigli di classe / colloqui** (`Rencontre`/`Conseil`): sia alunni sia
  responsabili hanno indisponibilità proprie per sessione
  (`FrameSco_IndispoRencontre_RS_ResponsableSansSelecIndisp`,
  `FrameEDT_IndispoConseil_RS_IndispoConseilSansSessionResponsables`) — è lo
  stesso modulo di riunioni visto per il personale al §1, **non** la griglia
  oraria delle lezioni.

**Conclusione**: per delimitare lo scope, alunni e responsabili si possono
escludere dal modello di piazzamento delle lezioni; entrano in gioco solo se
in futuro si copre il modulo "colloqui/consigli di classe" (separato) o la
formazione classi nominativa (già esclusa).

---

## 5. `UtilitairesEdt_ColonnesRessources` — le colonne per risorsa

591 stringhe (224 coppie corto/lungo uniche + varianti). Raggruppate per
risorsa a cui si applicano (dedotto dal prefisso/nome/hint, **[INFERENZA]**
dove non ovvio dal nome).

### Docente (prefisso `Prof*`, + condivise)
`AbrevLong` (abbreviazione), `AHELong` (Ore extra/ARE), `DechargeLong` (Extra
Uff.scol./ARA), `AppLong` (Monte ore = Apport), `HSALong` (Ore Supplementari),
`HSAPreRentre_Long` (OSA previsionali), `HSLong` (Non Contabilizzata),
`IndemniteLong` (Indennità), `EngagementLong` (Impegni), `QuotiteAnnuelleLong`
(Monte ore annuale = App/An), `ResteHeure_Long` (Ore residue),
`ProfHeuresP1/P2/P3Long` (Priorità 1/2/3 — **mai vista in UI**, nuova),
`ProfHeuresRetardServiceLong` (Permessi/Retard de service — **nuova**),
`ProfHSMaxLong` (Ore Supp. Max.), `ProfCDSLong` (Controllo del servizio),
`ProfMatierePrefLong` (Materia preferenziale, già nota),
`ProfSallePrefLong` (Aula preferenziale, già nota),
`ProfRempNiveauLong`/`ProfRempPotLong` (Livelli sostituibili / Sostituto
potenziale — sistema di sostituzioni, **nuovo per EDT** anche se probabile
overlap col SaaS del committente), `ProfTutoratLong` (Tutor/N.alunni),
`MatieresEnseignablesLong` (già nota), `ProfNatureSupportLong`/`ProfSupportLong`
(Tipo di supporto/Supporto — **nuova**, terminologia HR francese),
`ProfModAffectatuinLong`/`ProfModServiceLong` (Modalità di assegnazione/servizio
— **nuova**), `ProfCodeGradeLong`/`ProfDateGradeLong`/`ProfEchelonGradeLong`/
`ProfDateEchelonLong`/`ProfDateInspectionLong` (carriera HR francese — **fuori
scope**, dati di stato giuridico non gestionali per l'orario).

### Vincoli orari (docente **e** classe — colonne condivise, già note da `vincoli.md` ma qui coi nomi colonna)
`ColTrousToleresLong` (D.T.B.), `DemiHLong`/`DemiSeqLong`/`Trou1hLong`/
`TrouNhLong`/`TrouCumulLong`/`TrouGlobalLong` (buchi, varie granularità),
`DemiJourLong` (mezze giornate libere), `DJTLong` (Massimo mezze giornate di
lavoro), `TravDemiLong` (Lavorare solo mezza giornata), `PLGLong` (Giorni e
mezze giornate libere = *Plage Libre Garantie*, **nuova sigla**), `MhLong`
(Massimo di ore di attività), `MpLong` (Massimo di ore di presenza — **nuova,
distinta da Mh**), `AltLong` (Periodicità).

### Aula (`Salle*`, + condivise — coerenti con `aule.md`)
`CapaciteLong`, `CategoriesSalleLong`, `AffecteesLong` (Aule assegnate),
`GestionnairesSalleLong`, `SalleNbProfLong`/`SalleNomsProfsLong` (numero/nomi
docenti che la usano — **nuova, utile per capire l'uso reale dell'aula**),
`SalleReservableParLong`, `SalleSeuilLong`, `NbSallesLong`, `NomsSallesLong`,
`RemplissMax/Min/MoyLong` (riempimento max/min/medio — **nuovo indicatore di
occupazione aula**), `TOPLong`/`TOPReelLong` (Tasso occupazione
potenziale/reale), `PicOccLong`, `OccupationAnnuelleLong`/`OccupationTypeLong`.

### Materiale (v. §2)
`MaterielLong`, `NombreLong` (Quantità), `NbPlacesLibresLong`.

### Personale (v. §1)
`PersonnelLong`, `FonctionLong`, colonne condivise di occupazione/indisponibilità.

### Classe / Alunno / Anagrafica — in gran parte **PRONOTE, non EDT**
Tutto il blocco anagrafico (indirizzi 1-4, email, telefono, SMS, stato
civile, stato/città di nascita, codice fiscale, assicurazione, mutua,
photo, provenienza scolastica, ripetenza, opzioni previsionali,
consiglio/CNS, parcours cittadino...) **[INFERENZA] è quasi certamente
PRONOTE** (registro/anagrafica alunno-famiglia), non EDT. Le uniche colonne
di classe rilevanti per l'orario già documentate altrove: `EffettivoLong`,
`EffectifParGroupeLong` (Al./Rid.), `GroupeLong`/`GroupesLong`/
`GroupesPartiesLong` (Raggruppamenti/Gruppi — coerente con `gruppi.md`),
`RiLong` (Distribuzione oraria imposta), `FractionnableLong` (Proprietà di
piazzamento, P.P./P.F. — **nuova sigla da verificare in UI**, probabile
"spezzabile/non spezzabile" sul blocco di ore), `SuffixeLong` (Suffisso per
raggruppamenti), `CoursIsolesLong` (Attività isolate — **nuova**, probabile
contatore di ore singole non concatenate), `RepartitionLong` (Sezionamento).

### Attività/materia (condivise)
`LibelleCoursLong` (Descrizione), `ModLong` (Specifiche/Modalités),
`DisciLong`/`DisciplineLong`, `InterclasseLong` (Intervallo — **nuova**,
probabile vincolo di ricreazione tra due attività).

---

## Colonne più significative mai viste in UI (selezione)

1. **`ProfHeuresP1/P2/P3`** — Priorità 1/2/3 del docente: un sistema di
   priorità numerato **mai osservato**, probabile criterio di
   ottimizzazione/alleggerimento per docente.
2. **`ProfHeuresRetardServiceLong`** (Permessi/*Retard de service*) — "arretrato
   di servizio" del docente: possibile debito/credito ore da recuperare.
3. **`MpLong`** (Massimo di ore di **presenza**) — distinto da `Mh` (Massimo
   di ore di **attività**): suggerisce due tetti orari separati,
   presenza-a-scuola vs. ore-di-lezione.
4. **`PLGLong`** (*Plage Libre Garantie* = "Giorni e mezze giornate libere
   garantite") — sigla mai vista, un vincolo di "tempo libero garantito" più
   forte della semplice mezza-giornata libera.
5. **`FractionnableLong`** (P.P./P.F. — "Proprietà di piazzamento") — sigla
   oscura sulla classe/attività, probabile flag spezzabile/non spezzabile.
6. **`CoursIsolesLong`** (Attività isolate) — contatore/vincolo su ore non
   concatenate ad altre, mai discusso.
7. **`InterclasseLong`** (Intervallo/*Récréation*) — la ricreazione come
   entità con colonna propria, possibile vincolo di separazione fra due
   attività adiacenti.
8. **`SalleNbProfLong`/`SalleNomsProfsLong`** — numero e nomi dei docenti che
   usano un'aula: utile per inferire "aula di fatto dedicata a una
   disciplina" senza doverlo dichiarare esplicitamente.
9. **`RemplissMax/Min/MoyLong`** (riempimento max/min/medio dell'aula) —
   indicatori statistici di occupazione, forse solo diagnostici e non
   vincoli.
10. **`ProfNatureSupportLong`/`ProfSupportLong`/`ProfModAffectatuinLong`/`ProfModServiceLong`**
    — terminologia HR francese (tipo di supporto/contratto, modalità di
    assegnazione e di servizio) — **[INFERENZA]** probabilmente fuori scope
    per l'Italia (assimilabile a "tipo di contratto" ma con categorie
    francesi specifiche), da verificare se EDT Italia le espone in UI.

---

## Cosa resta da verificare in UI

- [ ] **Il modulo "Personale"** in EDT (non PRONOTE): aprire la lista
  Docenti/Personale/Aule/Materiali sulla base demo `EDT_COMPLETE` e
  verificare se esiste una scheda "Personale" separata da quella "Docente",
  con lo stesso pannello a tre pennelli di indisponibilità (`Indisponibilità`
  / `Indisponibilità opzionali` / `Preferenze`) già documentato per aule e
  docenti.
- [ ] **"Attività di accompagnamento"**: verificare se nella base demo
  esistono educatori con attività assegnate in griglia oraria, per
  confermare che l'Educatore genera vere e proprie "attività" (cours) e non
  solo un flag anagrafico.
- [ ] **Il modulo Materiali**: la base Fermi non ha aule (`NBSALLES = 0`,
  già segnalato) — probabile che non abbia nemmeno materiali. Verificare
  sulla base demo (`Esempio.edt`) la finestra "Aule e materiali" e provare a
  creare un materiale con quantità 2, assegnarlo a 3 attività simultanee e
  vedere se il piazzamento lo rifiuta (conferma pratica del vincolo hard
  dedotto dalle stringhe).
- [ ] **`FractionnableLong` (P.P./P.F.)**: capire in UI su quale entità
  compare questa colonna (classe? attività?) e cosa significano i due valori.
- [ ] **`PLG` (Plage Libre Garantie)** e **`Mp` (Massimo di ore di
  presenza)**: cercare nel pannello vincoli orari del docente/classe, non
  ancora visti separatamente da `Mh`/`DJT`/`D.T.B.`.
- [ ] **`ProfHeuresP1/P2/P3`**: cercare un pannello "Priorità" sulla scheda
  Docente — potrebbe essere il meccanismo con cui EDT decide quali attività
  scartare per prime durante l'alleggerimento (rilevante per
  `motore-risoluzione.md`).
- [ ] **IMP/PACTE**: dato che è confermato francese-specifico, verificare
  che in EDT Italia il menu/scheda relativa sia effettivamente assente o
  disattivata (chiuderebbe definitivamente il punto aperto su `TRCD` in
  `docs/edt/classi.md`).
- [ ] **`CoursIsolesLong`** e **`InterclasseLong`**: cercare nel pannello
  vincoli materia/attività se compaiono come colonne aggiuntive non ancora
  documentate in `vincoli.md`.
- [ ] **Il modulo Consigli/Colloqui (`Rencontre`)**: è un motore di
  piazzamento a sé (sessioni, non settimana ricorrente) che usa personale,
  alunni e responsabili come risorse con indisponibilità proprie — da
  decidere esplicitamente se è dentro o fuori scope per il nostro modulo
  (probabile fuori scope, essendo scheduling di eventi singoli non di
  orario scolastico settimanale).
