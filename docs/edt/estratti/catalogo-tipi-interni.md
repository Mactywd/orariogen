# Catalogo del modello dati interno di EDT 2026

Reverse engineering **in sola lettura** di tre file. Nessun file di EDT o di Wine
è stato modificato.

| Sorgente | Percorso | Ruolo |
|---|---|---|
| `exe` | `~/.wine/drive_c/Program Files/Index Education/EDT 2026/Monoposto/EDT Monoposto.exe` (142 MB) | catalogo completo dei tipi (RTTI Delphi) |
| `ex2` | `~/Desktop/EDT/example_2.edt` (310 KB) | base Liceo Fermi — quali tabelle vengono realmente scritte |
| `esem` | `.../Monoposto/Esempio.edt` (1.9 MB) | base demo Index — idem, con dati più ricchi |

Il `.dll` da 55 MB è stato controllato: **zero** nomi `TNet*`, tutto sta nell'EXE.

## Metodo

I nomi di classe Delphi sono memorizzati come *shortstring* (byte di lunghezza +
caratteri). Un `strings | grep TNet` produce nomi **sporchi**: il byte successivo
finisce nel match (`TNetAlignementPrevisionnelx`, `TNetDisciplineR`…). Estraendo
invece solo le occorrenze in cui il byte precedente è uguale alla lunghezza del
nome si ottiene l'elenco **esatto**; i candidati sporchi vengono poi ricondotti al
nome confermato togliendo fino a 5 caratteri di coda.

Effetto pratico: i ~750 nomi che `strings` restituisce da un `.edt` contengono
un centinaio di varianti fasulle. Le cifre qui sotto sono già ripulite.

Le enumerazioni sono state estratte parsando il `TTypeInfo` Delphi
(`tkEnumeration = 3`, nome, `OrdType`, `MinValue`, `MaxValue`, puntatore al tipo
base, poi i nomi dei valori consecutivi).

Artefatti grezzi nella stessa cartella:
`TNET_FINAL.tsv` (tipo → sorgenti), `TYPES_FINAL.tsv` (tutti i tipi Delphi),
`ENUMS.txt` (2 565 enum), `tcontrainte_clean.txt`.

## Conteggi

| Insieme | N |
|---|---|
| Tipi Delphi totali confermati (tutti i prefissi `T*`) | **30 924** |
| Classi persistenti `TNet*` | **1 039** |
| — di cui presenti in almeno un `.edt` (tabelle realmente scritte) | **749** |
| — solo nell'EXE (feature non usate dalle due basi) | 290 |
| — varianti legacy di migrazione (`*Avant2024`, `*Avant_8_0_4`…) | 179 |
| Tabelle di relazione `TNetRelation*` | **227** (208 nei `.edt`) |
| Classi di vincolo del risolutore `TContrainte*` | **90** |
| Classi di validazione `TVerificateur*` | **1 557** |
| Enumerazioni RTTI ricostruite | **2 565** |

Nel resto del documento **†** = tipo presente solo nell'EXE, mai scritto nei due
`.edt` esaminati.

### Formato del file `.edt`

Header in chiaro, poi corpo compresso a tratti. L'header è un XML
`<CARTEIDENTITE>` con le metriche della base (per `example_2.edt`: `NBMATIERES 12`,
`NBPROFS 18`, `NBCLASSES 10`, `NBCOURS 284`, `NBCOURSNONPLACES 284`, `NBMEFS 5`,
`NBSERVICEPREVISIONNELS 212`, `NBPARTIES 0`, `NBGROUPES 0`, `NBSALLES 0`).
Segue un **dump tabella per tabella**: tag di sezione in maiuscolo
(`COURS`, `CLASSE`, `PARTITION`, `SERVICEPREVISIONNEL`…) + nome della classe
(`TNetCours`, `TNetClasse`, `TNetPartition`, `TNetServicePrevisionnel`), poi
un marcatore `ArTi` per riga. I nomi dei campi **non** sono in chiaro: gli
attributi sono indicizzati numericamente. I nomi dei campi si recuperano dalle
enum `TypeColonne*` (vedi §Enumerazioni).

---

# 1. Dominio orario / attività (Cours)

`TNetCours` è **l'attività** (il "corso" nel senso EDT: una lezione ricorrente non
ancora o già piazzata), non la singola occorrenza oraria.

```
TNetCours                      TNetCoursPrevisionnel        TNetAnnulationCours
TNetModificationCours          TNetContenuDeCours           TNetMemoCours
TNetLibelleCours               TNetEtiquetteCours           TNetRecreation
TNetSequenceHoraire            TNetLibelleHoraire           TNetCoursGenantSession
TNetNonRespectClasseRecreation TNetPrecisionELeveNonAccompagneDeCours
TNetModelePrefsGrille          TNetParametresGrille †       TNetCoursAvant2025 †
```

Relazioni (vedi §5 per il quadro completo):

```
TNetRelationCours              cours ↔ cours   (padre/figlio: spezzamento)
TNetRelationCoursRessource     cours ↔ risorsa (prof, classe, gruppo, aula, materiale)
TNetRelationCoursContrainte    cours ↔ vincolo
TNetRelationCoursEtiquette     cours ↔ etichetta
TNetRelationCoursSubstitut     cours ↔ corso sostitutivo
TNetRelationViolationCours †   cours ↔ violazione diagnosticata
TNetRelationConseilCoursMaintenu
TNetRelationCoursServiceGEP
```

Punti chiave letti dalle enum:

- `TypeParenteCours = CoursSimple, CoursPere, CoursFils` — lo **spezzamento**
  (`Nr attività` → Trasforma) è modellato come gerarchia padre/figlio sulla stessa
  entità, non come tabella separata. `TNetRelationCours` è l'auto-relazione.
- `TypeEtatCours = EnEchec, Impose, Pose, APoser` — lo stato di piazzamento è a
  4 valori. La variante UI ne ha 8: `TypeEtatCoursCDR = EC_Indefini, EC_EnEchec,
  EC_Impose, EC_NonPose, EC_Pose, EC_APoser, EC_VerrouSouple, EC_VerrouRouge`
  → **i due lucchetti** (giallo = souple, rosso = dur) sono stati del corso.
- `TypeStatutCours = EnseignementNormal, ConseilDeClasse, EnseignementRemplacement,
  EnseignementHistorique, EnseignementSuppleant`.
- `TypeModeRepartitionCours = rModeRepartitionQuelconque, …Std, …Quinzaines,
  …Alternance, …AlternanceQuinzaines, …StdPermutable, …QuinzainesClasses,
  …StdParPeriode, …AlternanceParPeriode, …ProfParPeriode` — la **ripartizione**
  settimanale/quindicinale è un attributo del corso.
- `TypeModeDuplicationCours = dupFractionnement, dupFractionnementAvecDepose,
  dupCreerSurModele, dupCreerSurModeleAccepterFils, dupCreerSurModeleSansLesSalles,
  dupDupliquerEnSimple, dupFractionnementHistorique, dupFractionnementFils`.
- `TypeOperationCours` (41 valori) è il **log delle operazioni** su un corso:
  `opcCreation, opcDuplication, opcDuree, opcFrequence, opcMatiere, opcProfesseur,
  opcClasse, opcSalle, opcRepartitionSalle, opcPlaceManuel, opcPlaceAuto,
  opcPlaceAmenager, opcResoluteur, opcResoluteurPasAPas, opcOptimisation,
  opcDepose, opcAlignement, opcPonderation, opcAlternance, opcCoEnseignementON/OFF…`
  → conferma che *piazzamento manuale*, *risolutore* e *ottimizzazione* sono tre
  fasi distinte, tracciate separatamente.

# 2. Dominio vincoli (Contrainte)

Due livelli, da non confondere.

**(a) Vincoli persistiti** (`TNet*`, stanno nel `.edt`):

```
TNetContraintesProfesseur     TNetContraintesClasse     TNetContrainteMatiereClasse
TNetContrainteCoursACours     TNetPonderation           TNetPrefsOptim
TNetInfosContrainteEcart      TNetInfosContrainteQuinzaine  TNetInfosContrainteSuccession
TNetInfosRelCoursContrainteOrdre                        TNetViolation †
TNetIndisponibiliteConseil    TNetIndisponibiliteParticipantConseil
TNetRelationAssouplissementMatiereRessource
TNetRelationProfsIncompatibles
TNetRelationRemplacantNiveauIncompatible
TNetRelationIncompatibiliteEleveClassePrev
TNetContraintesProfesseurAvant2024 †  TNetContraintesProfesseurAvant2025 †
```

Da notare: **non esiste `TNetContraintesSalle`**. Le indisponibilità di aula
passano per `TNetSalle` stessa e per `TypeIncompatibiliteSalle` (§3).
`TNetContraintesClasse` e `TNetContraintesProfesseur` esistono e sono separate.

**(b) Vincoli runtime del risolutore** — 90 classi `TContrainte*`, **non**
persistite: sono il modello che EDT costruisce in memoria per il piazzamento.
È qui che si legge davvero cosa il solver sa fare.

```
strutturali        TContrainteSuperposition · TContrainteSuperpositionCours
                   TContrainteNonSimultaneiteRessource · TContrainteHorsGrille
                   TContrainteCousins · TContrainteDirecte · TContrainteIndirecte
                   TContrainteIndirecteCours · TContrainteTransitoireGlobale
disponibilità      TContrainteIndisponibilitesEtVoeuxCours
                   TContrainteIndisponibilitesEtVoeuxRessource
                   TContrainteAbsenceRessource · TContrainteHoraireRessource
                   TContrainteDebutsImposes · TContrainteJoursFeries · TContrainteJourFerie
carico orario      TContrainteMaxHoraireRessource · TContrainteMaxPresentielRessource
                   TContrainteMaxHoraireMatiere · TContrainteMaxHeuresMatiere
                   TContrainteMaxDemiJourneesTravaillees · TContrainteCumulDemiJournee
                   TContrainteSeuilDemiJournee · TContrainteSeulementDemiJournee
                   TContrainteOccupationDJ · TContrainteJoursEcourtesGarantis
                   TContraintePLG_DJT · TContrainteJEG
distribuzione      TContrainteRepartitionDemiJournees · TContrainteRepartitionQuinzaine
                   TContrainteRepartitionQuinzaineMemeMatiere · TContrainteQuinzaineImposee
                   TContrainteQuinzaineFilsVide · TContrainteOrdreCycle
                   TContrainteOrdreHebdo · TContrainteEnchainementMemeMatiere
                   TContrainteDeuxJoursMatiere · TContrainteEcartMatieresDj
materie            TContraintesMatieres · TContrainteCoupleMatieres
                   TContrainteMatieresIncompatibles · TContrainteIncompatibiliteMatiere
                   TContrainteSuccessionMatieres · TContrainteSuccessionImposee
                   TContraintePoidsPedagogique
cours-à-cours      TContrainteCaC · TContrainteCaCEcart · TContrainteCaCOrdre
                   TContrainteCaCQuinzaine · TContrainteCaCSuccession
classi/parti       TContrainteOrdreClassePartieFixe · TContrainteOrdreClassePartieTore
                   TContrainteMatiereOrdreClassePartiesFixe
                   TContrainteMatiereOrdreClassePartiesComplexeH / …ComplexeTore
                   TContrainteRegroupementCoursDePartie
sedi               TContrainteSite · TContrainteSiteDureeTrajet
                   TContrainteSiteNbChangements · TContrainteSiteChangementPause
mensa/ricreaz.     TContrainteDemiPension · TContrainteDeDemiPension · TContrainteRecreation
sostituzioni       TContraintePrioriteRemplacementProf · TContrainteRemplacementDansTrou
                   TContrainteRemplacementHorsTrou · TContrainteRemplacementHorsSite
                   TContrainteRemplacementOuDejaPresent
consigli/incontri  TContrainteConseilDeClasse · TContraintePresenceConseil
                   TContrainteIndispoConseil · TContrainteNbJoursConseils
                   TContrainteSuperpositionConseil · TContrainteJourFerieConseil
                   TContrainteConseilValeurPlace · TContrainteSiteTrajetConseil
                   TContrainteIndisponibilitesRessourceRencontre
                   TContrainteIndisponibilitesSessionRencontre
                   TContrainteNonSimultaneiteRessourceRencontre
                   TContrainteQualiteRessourceRencontre · TContrainteSuccessionRencontre
                   TContrainteIndirecteRencontre
altro              TContrainte · TContrainteCours · TContrainteRessource
                   TContrainteCloture · TContrainteChangementCycleGAEV
                   TContraintePicOccupation · TContrainteRegroupementVP
                   TContrainteItalieProfReglementaire
```

`TContrainteItalieProfReglementaire` è **specifico per l'Italia**: esiste un
vincolo di legge italiano cablato nel risolutore.

`TypeNiveauContrainte = ncContrainteDInitialisation, ncContrainteDeCours,
ncContrainteDeRessource, ncContrainteDeCousin, ncContrainteDeGroupeDeRessources,
ncContrainteDePseudoCousin` — i vincoli sono stratificati per portata
(inizializzazione / corso / risorsa / "cugini" = corsi che condividono risorse).

# 3. Dominio risorse: aule e materiali

```
TNetSalle          TNetCategorieSalle   TNetMateriel     TNetSite
TNetTrajetSite     TNetRelationSalles   TNetChambre      TNetDortoir
TNetSalleAvant2026_0_0 †  TNetParametresSite †
TNetRelationSessionRencontreProfSalle   TNetRelationSessionRencontrePersonnelSalle
(kiosque digitale, fuori scope: TNetRessourceNumeriqueKiosque,
 TNetAttributionRessourceKiosque, TNetPanierRessourceKiosque,
 TNetPreferenceRessourceKiosque, TNetDCPRessourceKiosque, TNetAccesRessourceKiosquePourStat,
 TNetInfoRessourceKiosquePourStat, TNetExecutionDevoirKiosque)
```

`TNetRelationSalles` è aula ↔ aula: è il **gruppo di aule** (risorsa che si
consuma da un pool). Confermato da
`TypeIncompatibiliteSalle = isElleMeme, isSite, isCapacite, isSalleDansGroupe,
isDejaDansLeGroupe, isNbOccurences, isGroupeDansGroupe, isGroupeDeGroupe,
isIndisponibilites, isOccupation, isGroupeDansConseil`
e da `TypeSalleInserable = SalleIncompatible, SalleTotalementNecessaire,
SallePartiellementNecessaire, SalleDejaDansGroupe`.

Altre enum di dominio:
`TypeUsageSalle = US_Cours, US_CDI`;
`TypeDeductionCapaciteSalle = dcsPropre, dcsGroupe, dcsSousSalle` (le aule si
annidano: sotto-aula);
`TypeAffectationSallePreferentielle = spCoursAvecSalle, spCoursAvecGroupeSalle,
spCoursSansSalle, spSansSalleOuAvecGroupe, spTous`;
`TypeReaffectabiliteSalle = cSalleReaffectableRepartition,
cSalleReaffectableOptimisation`;
`TypeChoixOptimSalle = tcosChangements, tcosSallePref, tcosCapacite,
tcosChangementsConfort, tcosAucun` (l'assegnazione aule è un'**ottimizzazione
separata** dal piazzamento, con criteri propri).

# 4. Dominio classi e partizioni

```
TNetClasse             TNetPartition          TNetPartieDeClasse      TNetGroupe
TNetExceptionLienPartiesDeClasse              TNetGroupeCompatibiliteEleve
TNetClassePrev         TNetStructureClassePrev    TNetClasseHistorique
TNetGroupeParcours     TNetOffreParcours      TNetChoixParcours
TNetPrecisionGroupeParcours   TNetParcoursEducatif   TNetInfosParcoursDifferencie †
TNetDivisionGEP        TNetGroupeGEP          TNetConseilDeClasse
legacy †: TNetClasseAvant2025, TNetClasseAvant2026, TNetGroupeAvant2025_0,
          TNetPartieDeClasseAvant2024_0, TNetOffreParcoursAvant2024_0,
          TNetParcoursEducatifAvant2026
```

**La gerarchia è a tre livelli, non a due.**
`Classe → Partition → PartieDeClasse`, e `Groupe` è ortogonale: un gruppo è
composto da *parti* (`TNetRelationGroupeComposante`), non da una classe.
`TNetRelationGroupe` è gruppo ↔ gruppo.

`TypeGenreRessource = Professeur, Groupe, Classe, PartieDivision, Salle, Eleve,
Responsable, Personnel, Matiere, Partition, Materiel` — **Partition e
PartieDivision sono risorse di prima classe**, allo stesso livello di Classe e
Salle: possono comparire in `TNetRelationCoursRessource`.

`TypeGenreGenerationAutomatiquePartie = GAPAucun, GAPMatiere, GAPDedoublement,
GAPUnTiersDeuxTiers, GAPFillesGarcons, GAPAutre, GAPPronoteNonGAEV, GAPPronoteGAEV,
GAPSconet, GAPDedoublementManuel, GAPPermanence, GAPEleve, GAPMatiereManuel`
→ le partizioni si generano automaticamente e la loro *origine* è tracciata.

`TypeNomPartiePredefini = partieFille, partieGarcon, partie1Tiers, partie2Tiers`
→ **le stringhe "Sdoppiamento", "Suddivisione", "1Terzo", "2Terzi",
"UnTerzoDueTerzi", "Maschio/Femmina", "Maschi", "Femmine", "Da definire" trovate
nei `.edt` NON sono valori di enum**: sono le etichette italiane delle partizioni
predefinite, scritte come dato nella sezione `RESS` della base. Compaiono anche in
una base con `NBPARTIES 0` perché EDT le crea sempre a vuoto.

Altre enum:
`TypeChainePartieDeClasse = Partie_Nom, Partie_PartitionNom, Partie_ClasseNom,
Partie_ClassePartitionNom, Partie_UniquementClasse` (come si compone il nome
visualizzato);
`TypeRemplissagePartie = RPAucun, RPOptions, RPNiveauScolaire, RPAlphabetique,
RPSexe, RPUtilisateur` (criterio di riempimento);
`TypeFantomitudePartie = fPartieNonFantome, fPartieFantomeSubstituableClasse,
fPartieFantomeCarToutesSoeursEnsembles` — esistono **parti "fantasma"**: se tutte
le parti sorelle sono insieme, la parte si comporta come la classe intera;
`TypeCreationGroupePourCours = TCGPC_AucunGroupe, TCGPC_UnSeulGroupe,
TCGPC_UnGroupeParPartie`;
`TEnumOptionsNomGroupe = eongVide, eongNiveau, eongClasse, eongCodeMatiere,
eongCL1, eongCL2, eongNumABC, eongNum123, eongNumParClasse` (nomenclatura
automatica dei gruppi);
`TypeLienPartiesAffiche = LPA_SansLien, LPA_LienManuel, LPA_LienEleve`.

# 5. Dominio docenti

```
TNetProfesseur          TNetProfesseurPrevisionnel   TNetProfesseurHistorique
TNetPersonnel           TNetPersonnelHistorique      TNetDiscipline
TNetStatut              TNetGrade                    TNetFonctionProf
TNetIndemnite           TNetAHE                      TNetRemplacementLong
TNetInfosDemandeRemplacement   TNetAutorisationProfesseur  TNetAutorisationPersonnel
TNetAbsenceRessource    TNetMotifAbsenceRessource    TNetDisponibilite
TNetMissionComplementaire      TNetDomaineProfessionnel    TNetPoleDisciplinaire
```

Relazioni docente (tutte N-N):

```
TNetRelationProfMatiere               capacità: materie insegnabili
TNetRelationProfesseurDiscipline      disciplina/e (classe di concorso)
TNetRelationProfNiveau                livelli abilitati
TNetRelationProfMetaMatiere           meta-materia
TNetRelationProfsIncompatibles        due docenti che non possono coincidere
TNetRelationProfAHE                   ore aggiuntive
TNetRelationProfesseurIndemnite       indennità
TNetRelationProfesseurPrevisionnel    cattedra previsionale
TNetRelationRemplacantMatiere         supplente ↔ materia
TNetRelationRemplacantNiveauIncompatible
TNetRelationAbsenceRessourceProf      assenza ↔ docente
TNetRelationPersonnelRessource · TNetRelationRessourceMissionComplementaire
TNetRelationDisciplineStructurePRV · TNetRelationProfPoleDisciplinaire
```

`TypeStatutProfesseur = STP_Definitif, STP_Provisoire, STP_Aucun`.
`TypeRechercheProfRemplacant = rrRemplacantLibre, rrRemplacantP1, rrRemplacantP2,
rrRemplacantP3, rrRemplacantTrou, rrRemplacantPresentJournee,
rrRemplacantPresentDemiJournee, rrRemplacantLibreSurAbsenceClasse, rrTousLibres,
rrTous` — rilevante per il SaaS sostituzioni già in produzione: **P1/P2/P3 sono
livelli di priorità del supplente**, memorizzati sul docente
(`ColProfRempNiveau`, `ColProfRempPotentiel`, `ColProfHeuresP1/P2/P3`).

L'enum `TypeColonneProfesseur` (100 valori) è di fatto **lo schema della scheda
Docente**. Estratto delle colonne d'orario:
`ColProfOcc, ColProfOccCumul, ColProfTOP, ColProfTOPReel, ColProfTrousToleres,
ColProfTrouGlobal, ColProfTrouCumul, ColProfTrouDemiHeure, ColProfTrou1h,
ColProfTrouNh, ColProfCoursIsoles, ColProfDemiJour, ColProfNbDJTravaillees,
ColProfNbJourneesTravaillees, ColProfPond, ColProfAHE, ColProfDecharge,
ColProfHSA, ColProfHSMax, ColProfMh, ColProfMp, ColProfRi, ColProfJEG, ColProfPLG,
ColProfDJT, ColProfTravDemi, ColProfMatierePref, ColProfSallePref,
ColProfMatieresEnseignables, ColProfQuotiteAnnuelle, ColProfCritere1AvOptim,
ColProfCritere2AvOptim`.
→ conferma ADR-006 (capacità ≠ assegnazione) e scioglie le sigle della UI
italiana: `Mh` = max ore/giorno, `Mp` = max presenza, `Ri` = ripartizione,
`JEG` = *jours écourtés garantis* (giorni ridotti garantiti), `PLG` = *plages
libres garanties* (fasce libere garantite), `DJT` = mezze giornate lavorate,
`TOP` = tasso di occupazione.

# 6. Dominio materie

```
TNetMatiere      TNetSousMatiere      TNetSurMatiere      TNetMetaMatiere
TNetCoefficientMatiereParDomaine      TNetAlignementMatierePrevisionnel
TNetMatiereGEP   TNetMatiereAvant2024 †
```

Quattro livelli di aggregazione: `SousMatiere ⊂ Matiere ⊂ SurMatiere`, più
`MetaMatiere` trasversale (usata per esami/livretto, non per l'orario).

```
TNetRelationMatiereMEF                materia ↔ piano di studi
TNetRelationRelationsMatiereMEF       relazioni fra materie dentro un MEF
TNetRelationStructureMatiereMEF       struttura oraria materia↔MEF
TNetRelationClasseMatiere · TNetRelationClasseSurMatiere
TNetRelationMatiereEleve · TNetRelationEleveNiveauMatiere
TNetRelationServicePrevisionnelMatiereMEF
TNetRelationNiveauMetaMatiere · TNetRelationMatiereEtablissementBase
```

`TypeColonneMatiere = ColMatiereCouleur, ColMatiereCode, ColMatiereLibelle,
ColMatiereDiscipline, ColMatiereEffectifParGroupe, ColMatiereFamille,
ColMatiereAP, ColMatiereEPI, ColEstSpecialite, ColMatiereEstGroupeDeNiveau,
ColMatiereSallePref, ColMatiereIDPartenaire, ColMatiereCodeSTS`
→ `ColMatiereEffectifParGroupe` è il campo `Al./Rid.` già documentato;
`ColMatiereSallePref` è l'aula preferenziale **sulla materia** (sorgente della
cascata di default aula).

`TypeIncompatibiliteMatiereClasse = MemeDemiJournee, MemeJournee, DeuxJours,
SuccessionInterdite, MaxHDemiJournee, MaxHJournee, OrdreHebdo, SuccessionImposee,
EcartDj, PartiesAvantClasse, PartiesApresClasse, PartiesAvantOuApresClasseH,
PartiesAvantOuApresClasseAB, Rien` — **è l'elenco completo dei vincoli di materia
per classe** che si possono impostare in EDT. Sono 13 tipi, tutti su
`TNetContrainteMatiereClasse`.

# 7. Dominio piani di studi (MEF)

```
TNetMEF          TNetNiveau       TNetFiliere      TNetSpecialite
TNetMEFGEP       TNetMEFStat4GEP  TNetNiveauAvant2026 †  TNetFiliereAvant2025 †
TNetRelationClasseMEF · TNetRelationMatiereMEF · TNetRelationStructureMatiereMEF
TNetRelationDivisionMEFGEP · TNetRelationSpecialiteEtablissement
TNetRelationSpecialiteOption · TNetRelationOrientationNiveau
```

`TypeColonneMEF = ColLibelleMef, ColFormationMef, ColEffectifMef, ColNiveauMef,
ColEffectifMefParClasse, ColSpecialiteMef, ColDiplomeMef, ColLibelleMefGEP,
ColFormationMefGEP, ColCodeSTSMefGEP`.
`TypeVoieMefStat5 = tvGenerale, tvTechnologique, tvProfessionnelle, tvAutre`.

# 8. Dominio previsionale (Previsionnel / Service / Alignement)

```
TNetServicePrevisionnel      TNetAlignementPrevisionnel
TNetAlignementMatierePrevisionnel   TNetCoursPrevisionnel
TNetProfesseurPrevisionnel   TNetClassePrev        TNetStructureClassePrev
TNetStructurePRV             TNetService           TNetModaliteService
TNetSimulation               TNetSimulationRepartitionEleve
TNetParametresPrevisionnel †
TNetRelationServicesPrevisionnels        auto-relazione servizio↔servizio
TNetRelationServicePrevisionnelMatiereMEF
TNetRelationProfesseurPrevisionnel · TNetRelationDisciplineStructurePRV
TNetRelationStructureServiceClassePrev · TNetRelationClassePrevMef
TNetRelationSimulationClassePrev · TNetRelationClasseSimulation
```

`TNetRelationServicesPrevisionnels` è **servizio ↔ servizio**: i servizi hanno
padre/figlio (`TVerificateurCoherenceNombreDeFilsDuServicePrevisionnel`,
`…DureeServicePrevisionnelFils`, `…tDuServicePrevisionnelPere`) — è il
sotto-servizio del piano di studi.

`TypeColonneServicePRV = ColActivationService, ColMatiereService, ColModaliteService,
ColEffectifService, ColDureeEleve, ColDureeClasseEntiere, ColDureeReduite,
ColDureeDedoublee, ColPonderation, ColNombreCours, ColDureeCours, ColProfesseur`
→ **le quattro durate sono campi distinti sullo stesso servizio**: durata alunno,
classe intera, ridotta, sdoppiata. Corrisponde a
`TypeGenreDureePrev = gdpClasse, gdpDedoublee, gdpReduite`.
Questo scioglie le colonne "Ridotto"/"Sdop." aperte in `piani-di-studi.md`.

`TypeColonneStructPrevClasse = ColSPrevC_Matiere, ColSPrevC_Discipline,
ColSPrevC_MEF, ColSPrevC_Effectif, ColSPrevC_Ponderation, ColSPrevC_ClassesHrs,
ColSPrevC_ClassesNbr, ColSPrevC_GroupesHrsRed, ColSPrevC_GroupesNbr,
ColSPrevC_HrsDdb, ColSPrevC_Besoins, ColSPrevC_BesoinsPond`
→ i **bisogni previsionali** sono `Besoins` e `BesoinsPond` (ponderati),
calcolati da effettivo × ore × numero classi/gruppi.

`TypeEtatServiceRepart = NonAttribue, Attribue, VerrouilleRepart, EnEchecRepart`
— stato della ripartizione docente→servizio.
`TypeGenreService = GS_SousMatiere, GS_Matiere`.

# 9. Dominio calendario e periodi

```
TNetCalendrier      TNetPeriodeCalendrier   TNetRegroupementPeriode
TNetJourDeCycle     TNetDateDeJourCycle     TNetJourFerie
TNetAlternance      TNetPreselectionSemaine TNetHoraireSession
TNetSequenceHoraire TNetLibelleHoraire      TNetPeriodeNotation
TNetRelationAlternancePeriodeCalendrierCalendrier
TNetRelationRegroupementPeriodePeriodeCalendrier
```

`TypeGenrePeriode = SemaineA, SemaineB, SemaineAB, SemaineQ` (quindicina).
`TypeSemaineFrequence = S1, S2`.
`TypeModeleCalendrier = Trimestriel, Semestriel, Hebdomadaire, Personnalise,
PourTestAuto`.
`TypeGenreElementHoraire = GEH_JourOuverture, GEH_PeriodeFermeture,
GEH_OuvertureExceptionelle, GEH_PeriodeDemiPension`.
`TypeCodeLigneHoraire = cLigneRecreation, cLigneDemiJournee, cLigneDemiPension,
cLigneDemiMixte` — la griglia oraria ha righe *speciali*: ricreazione, confine
mezza giornata, mensa.
`TypeZoneJournee = ZMatin, ZDemiPension, ZApresMidi`;
`TypePartieDuJour = PDJ_Indefini, PDJ_Matin, PDJ_Midi, PDJ_ApresMidi`;
`TypeNomJoursSemaine = tjs_Lundi … tjs_Dimanche` (7 giorni, domenica inclusa).

# 10. Motore di risoluzione e ottimizzazione

Non sono tabelle, ma dicono cosa fa il solver.

```
TNetPrefsOptim   TNettoyeurAvantPlacement †   TNetParametresCalculateur †
TVerificateur*   (1 557 classi di validazione dell'integrità del modello)
```

`TypeEtatPlacementAuto = cCalculDebut, cCalculPlacement, cCalculReevaluation,
cCalculOptimisation, cCalculResolRapide, cCalculResolIntegre, cCalculFin`
→ **il piazzamento è una pipeline a 7 fasi**, con due modalità di risoluzione
(rapida / integrale) e un passo di *rivalutazione* separato.

`TypeResolutionOptimisation = roAucun, roResolutionCours, roPlacerAmenager,
roOptimisationPermanence`.
`TypeOptionResolutionOptimisation = optGenantsIndirects,
optGenantsIndirectsHeuristiqueJour, optIncNiveau1, optIncNiveau2,
optHeuristiqueSolutionEchec` — **euristiche esplicite**, incluse due di
"incremento livello" e una per uscire dalle soluzioni in fallimento.
`TypeChoixOptim = tcoDJLibres, tcoTrous, tcoIsoles, tcoMemesHoraires, tcoAucun` —
i criteri di ottimizzazione: mezze giornate libere, buchi, corsi isolati, stessi
orari.
`TypeTypeOptim = ttoProfs, ttoClasses` — si ottimizza per docenti **o** per
classi, non insieme.
`TypeModeEvaluationCours = meEvaluerCoursMeilleurePlace,
meEvaluerCoursPlacesPossibles, meEvaluerCoursSolutionEchec,
meEvaluerCoursRessourcePossible, meEvaluerCoursPermutations,
meEvaluerCoursPlaceUniqueSansGenants, meEvaluerCoursPlaceUniqueAvecGenants,
meEvaluerSubstitutPlacesPossibles, meEvaluerProblemesRessources`.
`TypeVerifPlacement = cVerifInutile, cVerifSeulementPicOccup,
cVerifSeulementGenantsNonGeres, cVerifTousDiags`.
`TypeHeterogeneiteElementaireCours = cHeterogenePhysique, cHeterogeneMalPrecise,
cHeterogeneDomaine, cHeterogenePartiesNonLiees, cHeterogeneMatiere,
cHeterogeneContrainteMatiere, cHeterogeneSite` — perché un corso non è
"omogeneo" e quindi non piazzabile in blocco.
`TypeRefusAlignementCours = cAlignementJoursIncompatibles,
cAlignementEtatsIncompatibles, cAlignementFrequencesIncompatibles,
cAlignementCalendriersIncompatibles, cAlignementProfesseurManquant,
cAlignementSuperposition, cAlignementCoursFilsUnique,
cAlignementEnveloppeTropPetite, cAlignementErreurInattendue,
cAlignementRecreationsIncompatibles, cAlignementCoursAvecContrainteCaC`
— **le 11 ragioni per cui un allineamento viene rifiutato**: è di fatto la
specifica di validazione dell'allineamento.
`TypeCritereRepartitionGroupe` (13 valori) — strategie di ripartizione alunni nei
gruppi, incluse varianti "exhaustif" e "laxiste".
`TypeOptionCalculQuinzaines = oqRepartirQuinzaineMemeMatiere,
oqMaxHoraireMatiereStrictChaqueQuinzaine, oqMaxHoraireProfStrictChaqueQuinzaine,
oqMaxHoraireClasseStrictChaqueQuinzaine`.

Indisponibilità (le tre enum che formalizzano il rosso/giallo/verde della UI):
`TypeVEnumIndispo = eVISansIndispo, eVIIndispoRessource, eVIIndispoCours,
eVIIndispoRessourceEtCours`;
`TypeVPresenceIndispo = eVIndispoAucune, eVIndispoCoursSeulement,
eVIndispoRessourcesSeulement, eVIndispoCoursEtRessources`;
`TypeGenreVZoneContrainteSimple = eGVZCSMatin, eGVZCSApresMidi, eGVZCSJour`;
`TypeFonctionnaliteIndispoDebutImpose = tfidiClasse, tfidiCours`;
`TypeJourGaranti = jgJournee, jgDemiJour, jgMatin, jgApresMidi, jgDemiJourParJour`;
`TypeGenrePlageHoraire = extrac_erreur, extrac_Libre, extrac_Occup, extrac_Indispo`.

---

# 11. Le 227 tabelle `TNetRelation*`

Sono le N-N del modello. Elenco integrale, raggruppato.

## Rilevanti per un generatore di orari (≈45)

```
orario         Cours (auto, padre/figlio)          CoursRessource
               CoursContrainte                     CoursEtiquette
               CoursSubstitut                      ViolationCours †
               CoursServiceGEP                     ConseilCoursMaintenu
aule           Salles (auto, gruppo di aule)
               SessionRencontreProfSalle           SessionRencontrePersonnelSalle
classi         ClasseMEF          ClasseMatiere        ClasseSurMatiere
               ClasseResponsable  ClassePP             ClasseSessionRencontre
               ClasseSimulation   ClassePrevMef        ClassePrevPP
               PartiesDeClasseAvant2025 †
gruppi         Groupe (auto)      GroupeComposante (gruppo ↔ parte di classe)
               GroupeDivisionGEP  GroupeEleveGEP       GroupeChoixParcours
               GroupeParcoursProfesseur              EleveGroupeCompatibilite
               ElevePartieExclue
docenti        ProfMatiere        ProfesseurDiscipline ProfNiveau
               ProfMetaMatiere    ProfAHE              ProfsIncompatibles
               ProfesseurIndemnite ProfesseurPrevisionnel
               RemplacantMatiere  RemplacantNiveauIncompatible
               AbsenceRessourceProf PersonnelRessource
               RessourceMissionComplementaire        ProgressionProfesseur
               DisciplineStructurePRV                ProfPoleDisciplinaire
materie        MatiereMEF         RelationsMatiereMEF  StructureMatiereMEF
               AssouplissementMatiereRessource       MatiereEleve
               NiveauMetaMatiere
previsionale   ServicesPrevisionnels (auto, padre/figlio)
               ServicePrevisionnelMatiereMEF        StructureServiceClassePrev
               SimulationMatiere  SimulationClassePrev
piani/livelli  DivisionMEFGEP     OffreParcoursMEF     OffreParcoursMatiere
               ChoixParcoursMatiere ClasseExclueParcours ClasseExclueOffreParcours
               SpecialiteEtablissement SpecialiteOption OrientationNiveau
calendario     AlternancePeriodeCalendrierCalendrier
               RegroupementPeriodePeriodeCalendrier  PeriodeNotationClasse
               RessourceJourDemiPension
sostituzioni   DetachementCDTRessource               RessourceEleve
```

## Fuori scope orario (le restanti ~180)

Alunni e famiglie (`EleveResponsable`, `EleveClasseRattachement`, `EleveTuteur`,
`ResponsableElevePostulant`, `Famille`, `ObservationIndividu`…), valutazione e
pagelle (`EvaluationEleve`, `EvaluationSousItem`, `PalierBulletin`,
`AttestationBulletin`, `EleveCompetence`, `ElevePilierDeCompetence`,
`CompetenceItemLivretScolaire`, `EleveJeuCoefficient`…), disciplina
(`IncidentProtagoniste`, `IncidentSanction`, `SanctionSanctionsPrecedentes`,
`MesureDisciplinaireObjetDossier`…), infermeria (`ActeMedicalPassageInfirmerie`,
`SymptomeMedicalPassageInfirmerie`, `DossierInfoMedical`…), mensa
(`AlimentAllergene`, `RepasAlimentAllergene`, `AlimentLabelAlimentaire`…),
stage/alternanza (`StageProfesseur`, `StageMaitreDeStage`, `OffreDeStageMEF`,
`SessionDeStageRessource`, `QuestionQuestionnaireStage`…), orientamento
(`AutreOrientationMatiere`, `SessionInscriptionChoixDOrientation`…), QCM
(`EtiquetteQCM`, `QCMContributeur`, `QuestionQCMElementCompetence`…), documenti,
messaggistica, elezioni, tutorato, harcèlement, OAuth/sync.

---

# 12. Fuori scope per un generatore di orari (compresso)

594 classi `TNet*` su 1 039 non hanno alcun ruolo nella generazione dell'orario.
Delimitano lo scope: sono ciò che EDT+PRONOTE fanno **oltre** l'orario.

| Area | Esempi rappresentativi |
|---|---|
| Alunni e responsabili | `TNetEleve`, `TNetResponsable`, `TNetElevePostulant`, `TNetLienParente`, `TNetRegimeEleve`, `TNetMemoEleve` |
| Assenze e ritardi alunni | `TNetAbsenceEleve`, `TNetRetard`, `TNetMotifAbsenceEleve`, `TNetDeclarationAbsenceEleve`, `TNetPresenceEleve`, `TNetAppelFait`, `TNetDispense`, `TNetSuiviAbsenceRetard` |
| Voti, pagelle, competenze | `TNetNoteDEleve`, `TNetDevoir`, `TNetEvaluation`, `TNetBulletin`, `TNetAppreciation`, `TNetCompetence`, `TNetPilierDeCompetence`, `TNetItemLivretScolaire`, `TNetMoyenneBrevet`, `TNetJeuCoefficient`, `TNetPalier` |
| Registro elettronico | `TNetCahierDeTexte`, `TNetCahierJournal`, `TNetTravailAFaire`, `TNetProgression`, `TNetElementProgramme`, `TNetVisaCahierDeTexte` |
| QCM | `TNetQCM`, `TNetQuestionQCM`, `TNetCopieQCM`, `TNetCorrectionQCM`, `TNetExecutionQCM` |
| Disciplina | `TNetIncident`, `TNetPunition`, `TNetSanction`, `TNetReponseEducative`, `TNetProgrammationSanction`, `TNetSituationHarcelement` |
| Infermeria e salute | `TNetPassageInfirmerie`, `TNetActeMedical`, `TNetSymptomeMedical`, `TNetDossierMedical`, `TNetVisiteMedicale`, `TNetInfoMedicale`, `TNetMutuelle` |
| Mensa e convitto | `TNetInternetRepas`, `TNetAbsenceRepas`, `TNetAllergeneAlimentaire`, `TNetLabelAlimentaire`, `TNetAbsenceInternat`, `TNetDortoir`, `TNetRetardInternat`, `TNetCreneauAppelInternat` |
| Stage / alternanza | `TNetStage`, `TNetOffreDeStage`, `TNetMaitreDeStage`, `TNetEntreprise`, `TNetSessionDeStage`, `TNetFraisStage`, `TNetTaxeApprentissage` |
| Orientamento | `TNetOrientation`, `TNetChoixDOrientationEleve`, `TNetAvisProfParcoursup`, `TNetReponseOrientation`, `TNetDiplome` |
| Comunicazione | `TNetMessage`, `TNetBillet`, `TNetBlog`, `TNetPostForum`, `TNetSMSEnvoye`, `TNetListeDiffusion`, `TNetPostit`, `TNetAlerte`, `TNetNotificationApplicative` |
| Documenti e firma elettronica | `TNetDocumentJoint`, `TNetArchivageDocument`, `TNetSignature`, `TNetDocumentSignatureCP`, `TNetMaquetteReleve`, `TNetModeleDocument`, `TNetMediatheque` |
| Elezioni e organi | `TNetElection`, `TNetCandidatEP`, `TNetVotantElection`, `TNetCommission`, `TNetMembreBureauEP` |
| Incontri scuola-famiglia | `TNetRencontre`, `TNetSessionRencontre`, `TNetRendezVous`, `TNetSessionRDV`, `TNetCreneauSessionRDV`, `TNetDisponibiliteRencontre` |
| Consigli di classe | `TNetConseilDeClasse`, `TNetSessionConseil`, `TNetConvocationConseil`, `TNetIndisponibiliteConseil` |
| Infrastruttura | `TNetUtilisateur*`, `TNetServeurDonnees*`, `TNetTokenAuthentification`, `TNetJetonOAuth2*`, `TNetXi*`, `TNetFormatter*`, `TNetParametres*` (≈30 classi di configurazione), `TNetEntiteSync`, `TNetRapportDImport` |
| Geografia / anagrafiche BU | `TNetVille`, `TNetPays`, `TNetProvince`, `TNetDepartement`, `TNetRegionBU`, `TNetSecteurDActivite`, `TNetProfession`, `TNetMetier` |

**Nota sul confine.** Alcune di queste **toccano** l'orario e non vanno scartate
del tutto per il modulo sostituzioni: `TNetAbsenceRessource` (assenza docente/aula),
`TNetMotifAbsenceRessource`, `TNetAnnulationCours`, `TNetRemplacementLong`,
`TNetInfosDemandeRemplacement`, `TNetMissionComplementaire`,
`TNetConseilDeClasse` e `TNetSessionConseil` (occupano slot e docenti).

---

# 13. Nota metodologica: cosa *non* si ricava da qui

- **I nomi dei campi delle tabelle non sono in chiaro** nei `.edt`: gli attributi
  sono indicizzati per posizione. Le enum `TypeColonne*` danno i nomi delle
  colonne come le vede la UI, che è quasi certamente un superinsieme ordinato
  diversamente rispetto al record su disco. Non assumere corrispondenza 1:1.
- Le classi `TContrainte*` e `TVerificateur*` sono **runtime**: la loro esistenza
  prova che EDT sa gestire quel vincolo, non che la base del Fermi lo usi.
- I 290 tipi solo-EXE possono essere feature disattivate, moduli PRONOTE, o
  tabelle create solo alla prima scrittura. Assenza da un `.edt` ≠ inesistenza.
- Le versioni `*Avant2024`/`*Avant_8_0_4` sono classi di **migrazione** lette in
  sola lettura: vanno ignorate nel disegnare uno schema nuovo, ma dicono quali
  entità sono cambiate di recente (`Professeur`, `Classe`, `Groupe`,
  `PartieDeClasse`, `Salle`, `Matiere`, `Niveau`, `Filiere`,
  `ContraintesProfesseur` hanno tutte varianti legacy → sono entità **instabili**
  nel modello di Index).
