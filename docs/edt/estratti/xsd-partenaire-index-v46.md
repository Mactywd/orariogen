# Partenaire_Index.xsd
namespace: http://www.index-education.com/importpartenaireindexV4.6

## Tipi semplici ed enumerazioni

- **TypeIdentifiantPartenaire** (base `xs:string`)
  - Type représentant les identifiants uniques dans le référentiel du partenaire
- **JOUR** (base `xs:unsignedShort`)
- **IDENT** (base `xs:unsignedInt`)

## Struttura

- `PARTENAIRE_INDEX` [1..1]
    · @Version `string` **req**
    · @Date `dateTime` **req**
    · @Partenaire `string` **req** — ID du partenaire ayant généré ce fichier (fourni par Index-Education)
  - `Nomenclatures` [0..1]
    - `AHEs` [0..1]
      - `AHE` [1..unbounded]
          · @Ident `IDENT` **req**
          · @GenreEtablissement `boolean` **req** — AHE de genre Etablissement si vrai, Académie sinon.
          · @Libelle `string` **req**
          · @Code `string` opt
          · @LibelleLong `string` opt
    - `Alimentations` [0..1]
      - `Alimentation` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
    - `Allergies` [0..1]
      - `Allergie` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
          · @Alimentaire `boolean` opt
    - `AutorisationsSortie` [0..1]
      - `AutorisationSortie` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Code `string` **req**
          · @Libelle `string` **req**
    - `Bourses` [0..1]
      - `Bourse` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Code `string` **req**
          · @LibelleLong `string` **req**
          · @LibelleCourt `string` opt
          · @BourseNationale `boolean` **req**
    - `Civilites` [0..1]
      - `Civilite` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Abreviation `string` **req**
          · @Libelle `string` **req**
    - `CompagniesAssurances` [0..1]
      - `CompagnieAssurance` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Nom `string` **req**
    - `Disciplines` [0..1]
      - `Discipline` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Code `string` **req**
          · @Libelle `string` **req**
    - `Exonerations` [0..1] — Nouveauté pour les établissements privés
      - `Exoneration` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
          · @Code `string` **req**
    - `LiensParente` [0..1]
      - `LienParente` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Code `string` **req**
          · @LibelleLong `string` **req**
          · @LibelleCourt `string` opt
    - `MotifsPA` [0..1]
      - `MotifPA` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
          · @Confidentiel `boolean` opt
    - `Professions` [0..1]
      - `Profession` [1..unbounded]
          · @Ident `IDENT` **req**
          · @LibelleLong `string` **req**
          · @LibelleCourt `string` opt
          · @Code `string` opt — Code PCS (profession/catégorie socio professionnelle) / Obligatoire pour l'export vers SIECLE des privés
    - `ProjetsAccompagnement` [0..1]
      - `ProjetAccompagnement` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
    - `Provenances` [0..1]
      - `Provenance` [1..unbounded]
          · @Ident `IDENT` **req**
          · @LibelleLong `string` **req**
          · @LibelleCourt `string` opt
          · @Code `unsignedInt` opt — Code provenance -Obligtatoire pour l'export SIECLE des privés
    - `Regimes` [0..1]
      - `Regime` [1..unbounded]
          · @Ident `IDENT` **req**
          · @LibelleLong `string` **req**
          · @LibelleCourt `string` opt
          · @Code `string` opt
          · @RepasMidi `boolean` opt — Booléen initialisé à "False" par défaut : aucun repas du midi n'est pris en compte par défaut
          · @RepasSoir `boolean` opt — Booléen initialisé à "False" par défaut : aucun repas du soir n'est pris en compte par défaut
          · @Internat `boolean` opt — Booléen initialisé à "False" par défaut
    - `Situations` [0..1]
      - `Situation` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Code `string` **req**
          · @Libelle `string` **req**
    - `StatutsEleve` [0..1]
      - `StatutEleve` [1..unbounded]
          · @Ident `IDENT` **req**
          · @LibelleLong `string` **req**
          · @LibelleCourt `string` opt
          · @Code `string` opt
    - `Vaccinations` [0..1]
      - `Vaccination` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
    - `Libelles` [0..1]
      - `Libelle` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Libelle `string` **req**
          · @Abreviation `string` opt
          · @Couleur `string` opt
    - `Ponderations` [0..1]
      - `Ponderation` [1..unbounded]
          · @Ident `IDENT` **req**
          · @Numerateur `double` **req**
          · @Denominateur `double` **req**
  - `Etablissements` [1..1]
    - `Etablissement` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Numero `string` **req** — Code RNE/UAI de l'établissement
        · @Nom `string` **req**
        · @Adresse1 `string` opt
        · @Adresse2 `string` opt
        · @Adresse3 `string` opt
        · @Adresse4 `string` opt
        · @CodePostal `string` opt
        · @Ville `string` opt
        · @Pays `string` opt
        · @TelSecretariat `string` opt
        · @TelScolarite `string` opt
        · @Fax `string` opt
        · @EMail `string` opt
  - `EtablissementsGeres` [1..1] — Permet d'importer la liste des établissements à initialiser dans la base EDT/PRONOTE
    - `Etablissement` [1..unbounded]
        · @Ident `IDENT` **req**
  - `AnneeScolaire` [1..1]
      · @DateDebut `date` **req**
      · @DateFin `date` **req**
      · @DatePremierJourSemaine1 `date` **req**
  - `GrilleHoraire` [0..1]
      · @NombreJoursParCycle `unsignedShort` **req**
      · @NombreSequencesParJour `unsignedShort` **req**
      · @NombrePlacesParSequence `unsignedShort` **req**
    - `PlacesParJour` [1..1]
      - `Place` [1..unbounded]
          · @Numero `unsignedShort` **req** — Le numéro de la première place du jour est égal à 0
          · @LibelleHeureDebut `time` **req**
          · @LibelleHeureFin `time` **req**
  - `Niveaux` [0..1]
    - `Niveau` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Libelle `string` **req**
  - `Matieres` [0..1]
    - `Matiere` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Code `string` **req**
        · @Libelle `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @Couleur `string` opt — Couleur au format RVB hexadécimal
      - `Discipline` [0..1]
          · @Ident `IDENT` **req**
  - `Mefs` [0..1]
    - `Mef` [1..unbounded] — Formation+Specialite constituent la clé unique
        · @Ident `IDENT` **req**
        · @Libelle `string` **req**
        · @Formation `string` **req**
        · @Specialite `string` **req**
        · @Code `string` opt
      - `Niveau` [0..1]
          · @Ident `IDENT` **req**
      - `Matiere` [0..unbounded]
          · @Ident `IDENT` **req** — Ident de la matière
          · @DureeMinutesClasse `unsignedShort` opt
          · @DureeMinutesDedoublee `unsignedShort` opt
          · @DureeMinutesReduite `unsignedShort` opt
  - `Sites` [0..1]
    - `Site` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @Couleur `string` opt
  - `Salles` [0..1]
    - `Salle` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @Capacite `unsignedInt` opt
      - `Site` [0..1]
          · @Ident `IDENT` **req**
  - `Materiels` [0..1]
    - `Materiel` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @Informations `string` opt
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @NbOccurences `integer` opt
  - `Personnels` [0..1]
    - `Personnel` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @Prenom `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @IDPN `string` opt — Identifiant Pronote
        · @IDCAS `string` opt — Identifiant unique CAS
        · @Adresse1 `string` opt
        · @Adresse2 `string` opt
        · @Adresse3 `string` opt
        · @Adresse4 `string` opt
        · @CodePostal `string` opt
        · @Ville `string` opt
        · @Pays `string` opt
        · @TelFixe `string` opt
        · @TelPortable `string` opt
        · @EMail `string` opt
      - `Civilite` [0..1]
          · @Ident `IDENT` **req**
  - `Professeurs` [0..1]
    - `Professeur` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @Prenom `string` **req**
        · @DateNaissance `date` opt
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @IDPN `string` opt — Identifiant Pronote
        · @IDCAS `string` opt — Identifiant unique CAS
        · @Abreviation `string` opt
        · @Statut `string` opt
        · @Adresse1 `string` opt
        · @Adresse2 `string` opt
        · @Adresse3 `string` opt
        · @Adresse4 `string` opt
        · @CodePostal `string` opt
        · @Ville `string` opt
        · @Pays `string` opt
        · @TelFixe `string` opt
        · @TelPortable `string` opt
        · @EMail `string` opt
      - `Civilite` [0..1]
          · @Ident `IDENT` **req**
      - `Apport` [0..unbounded] — Liste des apports en minutes pour chaque discipline
          · @DureeMinutes `unsignedShort` **req**
        - `Discipline` [0..1]
            · @Ident `IDENT` **req**
      - `AHE` [0..unbounded]
          · @Ident `IDENT` **req** — Ident de l'AHE
          · @DureeMinutes `unsignedShort` **req**
      - `Salle` [0..1]
          · @Ident `IDENT` **req** — Salle de préférence
  - `PartiesDeClasses` [0..1]
    - `PartieDeClasse` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @LibellePartition `string` opt
  - `Classes` [0..1]
    - `Classe` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @Couleur `string` opt — Couleur au format RVB hexadécimal
      - `Niveau` [0..1]
          · @Ident `IDENT` **req**
      - `Mef` [0..unbounded]
          · @Ident `IDENT` **req** — Ident du mef
      - `PartieDeClasse` [0..unbounded]
          · @Ident `IDENT` **req**
      - `ProfesseurPrincipal` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Salle` [0..1]
          · @Ident `IDENT` **req**
      - `Etablissement` [1..1] — Identifie l'établissement d'appartenance de la classe parmi les établissements gérés (table EtablissementsGeres)
          · @Ident `IDENT` **req**
  - `Groupes` [0..1]
    - `Groupe` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @Couleur `string` opt — Couleur au format RVB hexadécimal
      - `Classe` [0..unbounded]
          · @Ident `IDENT` **req**
          · @LibellePartition `string` opt — Libelle de la partition de la classe à l'origine du groupe
      - `PartieDeClasse` [0..unbounded]
          · @Ident `IDENT` **req**
  - `Responsables` [0..1]
    - `Responsable` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @Prenom `string` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @IDPN `string` opt — Identifiant Pronote
        · @IDCAS `string` opt — Identifiant unique CAS
        · @Adresse1 `string` opt
        · @Adresse2 `string` opt
        · @Adresse3 `string` opt
        · @Adresse4 `string` opt
        · @CodePostal `string` opt
        · @Ville `string` opt
        · @Pays `string` opt
        · @TelFixe `string` opt
        · @TelPortable `string` opt
        · @TelProfessionnel `string` opt
        · @EMail `string` opt
        · @NbEnfantsACharge `unsignedInt` opt
        · @NbEnfantsSecondDegre `unsignedInt` opt
        · @NbEnfantsEtablissement `unsignedInt` opt
      - `Civilite` [0..1]
          · @Ident `IDENT` **req**
      - `Profession` [0..1] — Obligatoire pour l'export vers SIECLE des privés
          · @Ident `IDENT` **req**
      - `Situation` [0..1]
          · @Ident `IDENT` **req**
  - `ServicesPeriscolaires` [0..1] — périscolaire
    - `ServicePeriscolaire` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Libelle `string` **req**
        · @HeureDebut `time` opt
        · @HeureFin `time` opt
      - `JourOuverture` [1..7] — Jours d'ouverture du service périscolaire
          · @Jour `JOUR` **req**
  - `Eleves` [0..1]
    - `Eleve` [1..unbounded]
        · @Ident `IDENT` **req**
        · @Nom `string` **req**
        · @Prenom `string` **req**
        · @Prenom2 `string` opt
        · @Prenom3 `string` opt
        · @PaysNationalite `string` opt
        · @DateNaissance `date` **req**
        · @VilleNaissance `string` opt
        · @PaysNaissance `string` opt
        · @Sexe `` **req**
        · @ID_Partenaire `TypeIdentifiantPartenaire` opt
        · @IDPN `string` opt — Identifiant Pronote
        · @IDCAS `string` opt — Identifiant unique CAS
        · @IDSconet `string` opt
        · @NumeroNational `string` opt
        · @Adresse1 `string` opt
        · @Adresse2 `string` opt
        · @Adresse3 `string` opt
        · @Adresse4 `string` opt
        · @CodePostal `string` opt
        · @Ville `string` opt
        · @Pays `string` opt
        · @EMail `string` opt
        · @AdhesionTransport `boolean` opt — Obligatoire pour l'export vers SIECLE des privés
        · @Doublement `boolean` opt
        · @TelPortable `string` opt
      - `Mef` [0..1]
          · @Ident `IDENT` **req**
      - `Responsable` [0..unbounded]
          · @Ident `IDENT` **req**
          · @NiveauResponsabilite `unsignedShort` **req** — (1) Responsable légal (2) Personne en charge (3) Autre contact
          · @Financier `boolean` opt — Indique si le responsable légal ou la personne à charge est le responsable financier
          · @PercoitAides `boolean` opt — Si perçoit les aides
          · @Heberge `boolean` opt — Si héberge l'élève (possible uniquement et obligatoire pour un resp. légal ou une personne en charge (export SIECLE privé)
          · @Preferentiel `boolean` opt — Définit le responsable préférentiel de l'élève.
        - `LienParente` [0..1]
            · @Ident `IDENT` **req**
      - `AutorisationSortie` [0..1]
          · @Ident `IDENT` **req**
      - `Classe` [0..unbounded]
          · @Ident `IDENT` **req**
          · @DateEntree `date` opt
          · @DateSortie `date` opt
      - `CompagnieAssurance` [0..1]
          · @Ident `IDENT` **req**
          · @NumeroContrat `string` opt
      - `Groupe` [0..unbounded]
          · @Ident `IDENT` **req**
          · @DateEntree `date` opt
          · @DateSortie `date` opt
      - `PartieDeClasse` [0..unbounded]
          · @Ident `IDENT` **req**
          · @DateEntree `date` opt
          · @DateSortie `date` opt
      - `Option` [0..unbounded]
          · @Ident `IDENT` **req** — Ident de la matière
          · @Rang `` **req** — Positionnement de l'option: à partir de 1
          · @ModaliteElection `string` opt
      - `Bourse` [0..unbounded] — Pour la gestion financière
          · @Ident `IDENT` **req**
          · @Echelons `unsignedInt` opt — Nombre d'échelons de 1 à 6 (nouvelle codification) ou nombre de parts (ancienne codification) de la bourse
          · @MontantT1 `double` opt — Montant de la bourse au 1er trimestre
          · @MontantT2 `double` opt — Montant de la bourse au 2e trimestre
          · @MontantT3 `double` opt — Montant de la bourse au 3e trimestre
          · @MontantAnnuel `double` opt — Montant annuel de la bourse
      - `Regime` [0..1] — Pour la gestion de la restauration scolaire
          · @Ident `IDENT` **req** — Obligatoire pour l'export vers SIECLE des privés
        - `ServiceRestauration` [0..3] — Jours d'inscription à la restauration pour l'élève
            · @Genre `` **req**
          - `JourRestauration` [0..7] — Jours d'inscription à la restauration pour l'élève
              · @Jour `JOUR` **req**
        - `ServicePeriscolaire` [0..unbounded] — périscolaire
            · @Ident `IDENT` **req** — Se réfère à la table relationnelle "ServicesPeriscolaires"
          - `JourPeriscolaire` [0..7] — Sous-ensemble des jours d'ouverture du service périscolaire
              · @Jour `JOUR` **req**
      - `StatutEleve` [0..1]
          · @Ident `IDENT` **req**
      - `Etablissement` [0..1] — Identifie l'établissement d'appartenance de l'élève - Parmi les établissements gérés (table EtablissementsGeres)
          · @Ident `IDENT` **req**
          · @DateEntree `date` opt
          · @DateSortie `date` opt
      - `Provenance` [0..1] — Identifie le type d'établissement de provenance de l'élève (parmi la table des Provenances de la table des Nomenclatures) - Obligatoire pour l'export vers SIECLE des privés
          · @Ident `IDENT` **req**
      - `EtablissementAnDernier` [0..1]
          · @Ident `IDENT` **req** — Identifie l'établissement de l'an dernier de l'élève par référence à la table Etablissements - Obligatoire pour l'export vers SIECLE des privés
      - `EtablissementDOrigine` [0..1]
          · @Ident `` **req** — Identifie l'établissement d'origine de l'élève par référence à la table Etablissements
      - `MefAnDernier` [0..1]
          · @Ident `IDENT` **req**
      - `Exoneration` [0..unbounded]
          · @Ident `IDENT` **req**
      - `DossierMedical` [0..1]
          · @CommentaireMedical `string` opt
          · @Confidentiel `boolean` opt
          · @AutorisationHospitalisation `boolean` opt
        - `Alimentation` [0..unbounded]
            · @Ident `IDENT` **req**
        - `Allergie` [0..unbounded]
            · @Ident `IDENT` **req**
            · @Confidentiel `boolean` opt
        - `ProjetAccompagnement` [0..unbounded]
            · @Ident `IDENT` **req**
            · @ComplementInformation `string` opt
            · @DateDebut `date` opt
            · @DateFin `date` opt
          - `MotifPA` [0..unbounded]
              · @Ident `IDENT` **req**
        - `Vaccination` [0..unbounded]
            · @Ident `IDENT` **req**
            · @DateRappel `date` opt
            · @Confidentiel `boolean` opt
  - `Alignements` [0..1]
    - `Alignement` [1..unbounded] — permet de définiir des alignements pour générer des cours complexes : tous les cours ayant le même Ident d'alignement seront regroupés au sein d'un même cours complexe. Il convient donc de définir autant d'alignements que de cours complexes souahaités.
        · @Ident `IDENT` **req**
      - `Matiere` [0..1] — Matière du cours complexe à générer
          · @Ident `IDENT` **req**
  - `ListeCours` [0..1]
    - `Cours` [1..unbounded]
      - `DureeMinutes` [1..1] — durée du cours en minutes
      - `DureeSequences` [1..1] — durée du cours en nombre de séquences
      - `Matiere` [1..1]
          · @Ident `IDENT` **req**
      - `Professeur` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Groupe` [0..unbounded]
          · @Ident `IDENT` **req**
      - `PartieDeClasse` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Classe` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Salle` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Personnel` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Site` [0..1]
          · @Ident `IDENT` **req**
      - `Materiel` [0..unbounded]
          · @Ident `IDENT` **req**
      - `Alignement` [0..1]
          · @Ident `IDENT` **req** — Tous les cours partageant le même alignement seront regroupés au sein d'un même cours complexe
      - `Libelle` [0..1]
          · @Ident `IDENT` **req**
      - `Ponderation` [0..1]
          · @Ident `IDENT` **req**
