# Estratto — delimitazione dei moduli EDT (oltre a Orario)

Fonte: `it_fr_en.tsv` (69 888 stringhe, dump del binario condiviso EDT/PRONOTE).
Metodo: famiglie di chiavi `<Finestra>_RS_<Campo>` filtrate per parola chiave e
lette per intero o a campione. Ogni voce marcata **[STRINGA]** (letterale dal
dump) o **[INFERENZA]** (dedotta, da confermare in UI). Nessuna scrittura
effettuata su file EDT/Wine: solo lettura del tsv già estratto in precedenza.

⚠ Il binario è condiviso con PRONOTE (registro elettronico). Molte famiglie
polinomiali (`ScoGlossaire*`, `Glossaire_CP_*`, `EcnExtraction*`) appartengono a
PRONOTE (competenze, stage, orientamento, ecc.) e sono state scartate a vista.

---

## 1. Gestione per settimana e assenze (FR *Gestion par semaine et absences*)

**[STRINGA]** Titolo del modulo: `VieQuotidienne` → IT "Gestione per settimana e
assenze" / FR "Gestion par semaine et absences" (`GroupeDeTravailEDT_VieQuotidienne_RS_VieQuotidienne`).//
Sottotitolo breve: "Gestione settimanale" / "Gestion semaine".

Il modulo copre l'intera vita quotidiana della scuola: inserimento assenze,
sostituzioni, modifiche/cancellazioni puntuali dell'orario annuale, statistiche.
Non è un solver: è **workflow + query manuale**, con l'eccezione della "Tabella
di assegnazione delle sostituzioni per fascia oraria" che è un cruscotto di
assegnazione assistita (vedi 1.2).

### 1.1 Struttura: orario annuale → orario per settimana/ciclo

**[STRINGA]** (`FicheEDT_FrameParametreGestionParSemaine_Placement`) EDT
distingue esplicitamente due grigliati:
- `EdtActualise` = "Orario della settimana" / "EDT à la semaine" — la vista
  operativa, settimana per settimana, che **deriva** dall'orario annuale ma può
  divergere (modifiche puntuali).
- `EdtCycle` = "Orario per ciclo" / "EDT par cycle" — stesso meccanismo su un
  ciclo (rotazione multi-settimana, coerente con quanto già emerso in
  `schema-scambio.md` sul ciclo che eccede la settimana).

Ogni settimana/ciclo può essere **ripristinato** all'orario annuale
(`ReinitialiserEDTSEmaine` / `ReinitialiserEDTCycle` = "Ripristina tutto
l'orario per settimana/ciclo") o **bloccato automaticamente una volta
trascorso** (`CheckBoxCloture` = "Blocca automaticamente le settimane
trascorse", `FicheEDT_FrameParametreGestionParSemaine_Verrouillage`). Questo è
**esattamente** il meccanismo di "eccezione puntuale su una struttura
ricorrente": l'orario annuale è il template, la settimana è l'istanza
modificabile e poi congelata. [INFERENZA] è rilevante per il nostro modello se
vogliamo supportare eccezioni puntuali (festività, gite, supplenze) senza
duplicare l'intero orario.

Altri campi di piazzamento: `FicParametrePlacementAnuulerGenant` = "Non
annullare le attività che creano problemi", `ReintegrerElevesDetaches` = "in
caso di annullamento, reintegra gli alunni dissociati nella loro attività di
origine" — gestione delle eccezioni a cascata sugli alunni raggruppati
diversamente.

### 1.2 Come EDT sceglie un sostituto

**Non c'è un solver combinatorio globale**: la selezione del sostituto è un
**filtro multi-criterio su una lista**, ordinata per priorità dichiarate, con
assegnazione manuale finale (o assegnazione singola guidata). È un problema
"greedy/manuale assistito", non un CSP.

**[STRINGA]** Criteri di filtro esposti in `FrameSco_DecoSelectionRemplacement`
(finestra "Cerca un docente tra:" — `ChercherParmi`):
- `FiltreDispo` — Disponibili per tutta la durata / *Disponibles sur tout le
  créneau*
- `FiltreMatiere` — Della stessa materia / *Remplaçants dans la matière*
- `FiltreNiveau` — Dello stesso livello della classe / *Remplaçant dans le
  niveau*
- `FiltreEquipePeda` — Dello stesso consiglio di classe / *Dans l'équipe
  pédagogique*
- `FiltreMemeSite` — Presenti nella sede dell'attività / *Présents sur le site
  du cours*
- `FiltreAuSitePres` — Alla sede più vicina, ignorando la sede
- `IgnorerContraintes` — Ignora i vincoli (bypass esplicito, azione utente)
- `CocheNiveauUp` — Tenere conto del livello delle classi
- `BoutonImageEquipePedaUp` / `SelonEquipe` — Docenti del consiglio di classe
- `BoutonImageMemeSiteUp` — Docenti già presenti nella sede
- `BoutonImageDisposUp` — Autorizza i sostituti **parzialmente** disponibili
- `ResteEngagement` — Solo docenti con ore residue d'incarico non assegnate
- `TenirCompteMatiere` — Prendi in considerazione le materie definite nelle
  **priorità di sostituzione**

**[STRINGA]** Modalità di reclutamento alternative, da `Type_SelectionRemplacant`:
- `OptionRemplacantsLibre` — Tutti i sostituti liberi
- `OptionRemplacantsTous` — Tutti i docenti liberi (senza restrizione a chi è
  "sostituto")
- `OptionRemplacantsTousSansControle` — Tutti i docenti non assenti, **senza
  controllo sull'occupazione** (bypassa la verifica di conflitto oraria)
- `OptionRemplacantsPresentJournee` / `...DemiJournee` — presenti in istituto
  nella (mezza) giornata
- `OptionRemplacantsTrou` — sostituti liberi che hanno **un buco** nel proprio
  orario in quella fascia (preferisce riempire un buco esistente piuttosto che
  spezzare un orario compatto)
- `OptionRemplacantsSurAbsenceClasse` — sostituti liberati da un'assenza della
  classe stessa (es. un docente che perde un'ora perché la sua classe è in
  gita, diventa disponibile)
- `OptionRemplacantsPriorite` — sostituti liberi **con priorità %s** per ogni
  attività → rimanda al sistema di priorità (sotto)

**[STRINGA]** Sistema di priorità a 3 livelli, per docente e per fascia oraria
(`Type_GenreDisponibilite`): `PrioriteRemplacement1/2/3` = "Priorità 1/2/3". Si
configura per ciclo (`FrameSco_PrioritesRemplacementCycle`,
`FicheEDT_PrioritesRemplacementCycle` = "Parametri delle priorità") — **è una
griglia docente × fascia oraria**, strutturalmente identica alla griglia
disponibilità/preferenze già documentata per il piazzamento in
`docs/edt/vincoli.md` (rosso/giallo/verde + terzo pennello "Preferenze"), ma
dedicata specificamente alla propensione a fare sostituzioni. [INFERENZA] È
probabile che sia la stessa infrastruttura UI riusata con semantica diversa.

Segnali di preferenza spontanea del docente: `VolontaireSpontane` = "Docente
volontario per la sostituzione", `VolontaireCommentaire` = "Docente volontario
che ha lasciato un commento" — **workflow di richiesta/accettazione**: EDT invia
una `PropostaDiSostituzione` (richiesta) a uno o più docenti, che possono
accettare (`DemandeAcceptee`), rifiutare (`DemandeRefusee`), rispondere con
disponibilità parziale (`Disponibilite` = "Docente disponibile per una parte
dell'attività"), o essere forzati ignorando vincoli
(`IgnorerContrainte` = "Docente disponibile ignorando alcuni vincoli").

**Nessun punteggio numerico o ottimizzazione globale osservato**: la lista dei
candidati (`TitreRemplacant` = "Sostituti potenziali" / *Professeurs
disponibles*) è **filtrata e forse ordinata per priorità dichiarata**, ma
l'assegnazione finale è un clic umano (`ValiderRemplacant` = "Assegna il
sostituto"). Non risulta un motore che minimizzi buchi/spostamenti su scala
d'istituto per le sostituzioni — a differenza del piazzamento dell'orario
annuale (che ha CP vero) o dei Colloqui/Consigli (che hanno un risolutore vero,
vedi sotto).

**[STRINGA]** Distinzione **sostituzione puntuale vs a lungo termine**
(`FrameSco_ParametresRemplacementsLongs`): sotto una soglia configurabile di
`DureeMinDebut` giorni di calendario, la sostituzione resta "puntuale"; sopra,
diventa un `remplacement long` che genera un **binario parallelo di attività**
per il sostituto (`MettreAJourRemplacementLong` = "Aggiorna le attività delle
sostituzioni a lungo termine associate") — cioè per assenze lunghe, invece di
sostituire slot per slot, si duplica/reindirizza l'intera cattedra.

**[STRINGA]** `AffectationMission` / `AffectationMatiere` / `AffectationSalle`
(`FicheEDT_OptionsAffectationRemplacement`) — opzioni automatiche al momento
dell'assegnazione: eredita automaticamente materia e aula del sostituto se
possibile, assegna un "incarico" (mission) al sostituto.

### 1.3 RCD — Remplacement de Courte Durée

**[INFERENZA, alta confidenza]** `RCD` = *Remplacement de Courte Durée*
(sostituzione di breve durata). Non ho trovato lo scioglimento letterale della
sigla nel tsv, ma il contesto lo conferma in modo univoco: `UniquementAbsCourte`
= "Filtra assenze di breve durata" / *Absences de courte durée* compare nella
stessa finestra `FicheEDT_AffecterRemplacements`, e l'intera tassonomia
`Type_IndicateursRCD` classifica **chi sorveglia la classe durante un'assenza
breve non formalmente sostituita**: incrocio fra
- chi (`ircd*`): `ProfDeLEtablissement` (docente interno), `ProfHorsEtablissement`
  (esterno), `AEDDeLEtablissement`/`AEDHorsEtablissement` (assistente
  educativo, figura francese, interno/esterno), `AutreDeLEtablissement`
  (altro interlocutore interno), `Aucun` (alunni autonomi/`Élèves en
  autonomie`), `LuiMeme` (il docente stesso recupera su un'altra fascia)
- cosa fanno (`arcd*`): `Aucun` (niente), `AutreActivite`, `CoursAutreMatiere`,
  `CoursMemeMatiere`, `CoursSequenceNumerique` (sequenza pedagogica digitale
  sorvegliata), `Etude` (tempo di studio assistito)

Questa tassonomia alimenta solo **statistiche/esportazioni ministeriali**
(`GlossaireSco_ExportRCD`, `FicheSco_StatistiquesRCD`,
`AutoriserRCD` = "Autorizzo l'esportazione automatica degli indicatori legati
alle sostituzioni di breve durata"). **[INFERENZA]** È un adempimento normativo
francese (rendicontazione ministeriale delle ore non coperte), senza
equivalente noto nella normativa italiana sulle supplenze — **candidato a
fuori scope**, salvo che il committente abbia un obbligo equivalente italiano
di reportistica sulle ore di sostegno/vigilanza.

### 1.4 GAEV — gestione con alunni a effettivo variabile

**[STRINGA]** `Type_GAEV`: un meccanismo di validazione che **rifiuta**
l'inserimento di una sostituzione quando l'attività o il sostituto hanno
caratteristiche incompatibili con "gruppi a effettivo (numero alunni) variabile"
— es. `RefusGAEV_CoursMixte` (contiene una classe intera, non solo un gruppo),
`RefusGAEV_CoursPartiesMultiples` (più gruppi della stessa classe),
`RefusGAEV_LiensEleves` (il gruppo ha alunni in comune con un altro gruppo),
`RefusGAEV_PartiePronote` (gruppo generato da PRONOTE). [INFERENZA] È una
validazione di integrità sui gruppi/sdoppiamenti nel contesto specifico della
sostituzione — rilevante solo se decidiamo di supportare gli sdoppiamenti
(punto aperto in `docs/edt/gruppi.md`) **e** le sostituzioni nello stesso
prodotto.

### Cosa NON fa questo modulo (verificato per assenza di stringhe)

Nessuna traccia di un algoritmo di **ottimizzazione automatica** delle
sostituzioni su scala istituto (niente "resoluteur" o "optimiseur" nelle
famiglie `Remplacement*`/`Substitut*`/`RCD*`, a differenza di Colloqui e
Consigli sotto). La ricerca del sostituto resta un filtro + workflow di
richiesta/risposta con assegnazione manuale.

**Proposta di scope: FUORI** — Il committente ha già in produzione un SaaS di
gestione sostituzioni; EDT stesso qui non offre un solver ma un
filtro+workflow manuale, quindi non c'è "tecnologia di scheduling" da
recuperare — solo criteri di filtro (materia, sede, consiglio di classe, buco
esistente, priorità docente, ore residue d'incarico) potenzialmente utili come
*checklist* per arricchire il prodotto già esistente, non per il generatore
d'orari.

---

## 2. Colloqui genitori/docenti (FR *Rencontres parents-professeurs*)

**[STRINGA]** È un vero **problema di scheduling con risolutore dedicato**,
strutturalmente analogo (nei nomi delle finestre) al motore descritto in
`motore-risoluzione.md` per l'orario principale.

### 2.1 Architettura: sessione → desiderata → piazzamento → risolutore → ottimizzatore

**[STRINGA]** Una `SessionRencontre` ("Sessione colloqui") è definita da:
durata di default di un colloquio (`DureeRencontre`, con un minimo e massimo
configurabile — `DureeRencontreCompriseEntre_SS`), raddoppio automatico per i
"professori coordinatori" (`DoublerDureeRencontreParDefaut` /
`ChoixMatierePreferentielleRencontre` = "professor principale"/coordinatore),
periodo di apertura/chiusura desiderata (`DateDebutDesiderata`/
`DateFinDesiderata`), data di pubblicazione del planning
(`DatePublication`).

**[STRINGA]** Ogni partecipante (alunno/responsabile, docente, personale)
esprime **desiderata** (preferenze) per fasce orarie, con una semantica a
semaforo esplicita: `DesiderataLegende` = "I colloqui saranno creati solo
quando i desiderata dei partecipanti producono una spunta verde" —
**esattamente il meccanismo rosso/giallo/verde già visto per le indisponibilità
docente e (ora) per le priorità di sostituzione**: un pattern UI riusato in
tre moduli diversi.

**[STRINGA]** Priorità del colloquio stesso (`Type_Rencontre`):
`Indispensable` ("Colloquio prioritario") vs `Facultative` ("Colloquio
facoltativo") vs `Souhaitee` ("Colloquio desiderato") — una gerarchia a tre
livelli sul *colloquio*, indipendente dalla disponibilità del *partecipante*.

### 2.2 Il risolutore (`FicResoluteurRencontres`)

**[STRINGA]** Interfaccia identica nello spirito al piazzamento
dell'orario:
- Multi-fase esplicita: `ErePasse` = "1° fase", `EmePasse` = "° fase" (fase N)
- `LancerRecherche` = "Lancia la ricerca di soluzioni"
- Metriche di esito: `SolutionsTrouvees`, `RencontresTraitess` (elaborati),
  `RencontresSansSolution` (senza soluzione), `EchecsAResoudre` ("Attività da
  piazzare" — stessa dicitura usata per l'orario principale)
- Interruzione/ripresa: `ResolutionInterrompue`, `TempsEcoule`
- **Modalità esclusiva durante il calcolo**: `RelanceResolution` avverte che si
  può passare in "Utilizzo esclusivo" per impedire modifiche concorrenti
  durante il ricalcolo — stesso meccanismo di lock già noto dal motore
  principale.

C'è poi un **ottimizzatore separato** (famiglia `FrameSco_RencontreStatistique`,
non approfondita in dettaglio ma presente nelle famiglie elencate) e
un'estrazione dedicata (`FicheEDT_ExtractionRencontre`,
`FicheEDT_ExtractionRessourceRencontre`) — **stesso pattern estrai → piazza →
risolvi scarti** del modulo Orario.

### 2.3 Vincoli usati (dedotti dai filtri di estrazione/creazione sessione)

**[STRINGA]** Dalla creazione sessione (`FicCreationSessionRencontre`):
generazione automatica dei colloqui per: `CoursDeMemeMatiere` (stessa materia),
`CoursEnCoEnseignement` (compresenza), `CoursGAEV` (alunni a effettivo
variabile), con scelta di **quale attività** conta per generare l'elenco
docenti-alunno: `ChoixMatiereLaPlusEnseignataRencontre` (materia più insegnata
all'alunno), `ChoixMatierePreferentielleRencontre` (materia preferenziale del
docente), `ChoixMatieresToutesRencontre` (tutte le materie). Disponibilità
esplicite: `Disponibilites`. Vincoli di indisponibilità dedicati:
`FrameSco_IndispoRencontre` (famiglia vista nell'elenco, non approfondita).

**Proposta di scope: DA DECIDERE** — è un problema di scheduling reale, con un
motore CP-like proprio (fasi, ricerca di soluzione, esclusione reciproca), ma
il dominio (colloqui genitori-docenti) è probabilmente **fuori dal perimetro
dichiarato del progetto** (generatore di orario scolastico settimanale). Vale
la pena **studiarne l'architettura come riferimento di design** (stesso pattern
estrazione→piazzamento→risolutore→ottimizzatore visto ovunque in EDT) ma non
implementarlo in v1. Se il committente in futuro vuole coprire anche i
colloqui, questo è il punto di partenza.

---

## 3. Consigli di classe (FR *Conseils de classe*)

**[STRINGA]** Confermato: **motore a tre componenti indipendenti**, tutti e tre
osservati esplicitamente come finestre separate:
- `FicheEDT_PlacementAutoConseils` — "Piazzamento automatico dei consigli"
- `FicheEDT_ResoluteurConseils` — "Ricerca soluzione per i consigli scartati"
- `FicheEDT_OptimiseurConseils` — "Ottimizza i consigli"

Questo è **lo stesso schema a tre stadi** già documentato in
`motore-risoluzione.md` per l'orario (piazzamento iniziale → risoluzione degli
scarti → ottimizzazione secondaria), riapplicato pari pari a un dominio
diverso: conferma che è un **pattern architetturale generale del prodotto**, non
specifico dell'orario.

**[STRINGA]** Stati delle unità da piazzare, identici a quelli dell'orario
(`FicheEDT_PlacementAutoConseils`): `Poses` (piazzati), `Reste` (non
piazzati), `Echecs`/`EnEchec` (scarti), `Verrous` (bloccati),
`Extraits` (estratti — stesso meccanismo di selezione persistente), opzione
`ArretEchec` = "Interrompi al primo scarto".

**[STRINGA]** L'ottimizzatore (`FicheEDT_OptimiseurConseils`) usa **3 criteri
ordinati e configurabili** (`Critere1`/`Critere2`/`Critere3` — etichette non
risolte nel dump, verosimilmente scelti dall'utente in un altro pannello) e
riporta esiti quantitativi: `NbReplacement` (numero di sostituzioni fatte),
`NbSuperpositionsConseils` (numero di sovrapposizioni residue) — quindi
**l'obiettivo esplicito è minimizzare le sovrapposizioni fra consigli** (un
docente non può essere in due consigli alla stesso tempo), con un'opzione per
tollerarle sui docenti non indispensabili
(`SuperposerProfsNonObligatoires` = "Sovrapponi i consigli dei docenti non
indispensabili").

**[STRINGA]** Anche qui: modalità "usage esclusivo" durante il ricalcolo, e
avvertenza che l'ottimizzazione **considera solo i consigli piazzati
estratti** (non i bloccati) — stesso vincolo di dipendenza da `Estrai` visto
per l'orario (sezione 5).

**Proposta di scope: FUORI** — problema di scheduling reale con motore CP-like
completo, ma dominio (piazzare riunioni periodiche del consiglio di classe
evitando sovrapposizioni docente) strutturalmente diverso dall'orario
settimanale ricorrente. Prezioso come **prova indipendente del pattern
architetturale a 3 stadi** del motore EDT (utile per progettare il nostro
motore in modo analogo, se vogliamo un'architettura simile per fasi diverse
del nostro dominio), ma non va implementato.

---

## 4. Comunicazioni

**[STRINGA]** Le famiglie `*Communication*` nel tsv (`ScoGlossaireIdentiteCommunication`,
`Glossaire_CP_Communication`, `FrameSco_IdtEditionIndividuCommunication`,
`SequenceurCommunication`) riguardano quasi interamente **dati di contatto e
canali di comunicazione delle persone** (email, telefono, identità multipla di
alunni/responsabili) — infrastruttura anagrafica di PRONOTE (registro
elettronico), non scheduling.

Uniche stringhe di sostituzione/orario già coperte altrove (`CourrierEnvoye`,
`MessageEnvoye`, `SMSEnvoye` — "notifica inviata" per le richieste di
sostituzione, sezione 1) sono canali di invio, non logica di scheduling.

**Proposta di scope: FUORI** — nessun contenuto di scheduling; è messaggistica
anagrafica di PRONOTE.

---

## 5. Il meccanismo `Estrai` (FR *Extraire*)

**[STRINGA]** `Estrai` è un **filtro multi-criterio che produce una selezione
persistente e nominata** di risorse (attività, classi, gruppi, docenti,
personale, aule, materiali), non un'azione una tantum né una semplice vista.
Confermato da `FicheEDT_ExtractionCours` ("Estrai le attività") e
`FicheEDT_ExtractionRessource` ("Estrazione delle classi/raggruppamenti/
materiali/personale/aule").

**Caratteristiche osservate:**

1. **Criteri di filtro combinabili** su un'estrazione di attività:
   stato (`Places` piazzate / `NonPlaces` non piazzate / `EnEchec` scartate /
   `EnAttente` in attesa / `Verrouilles` bloccate / `Coursfixes` fisse /
   `Coursvariables` variabili), sovrapposizione con una fascia oraria
   (`CoursEntierement` interamente nella fascia / `CoursChevauchant`
   parzialmente), rispetto o meno dei vincoli
   (`CoursNeRespectantPasContraintes`), classi/docenti/aule/materiali/sedi
   coinvolti, incarico (`Mission`), coefficiente (`Ponderation`), alunni
   dissociati (`ElevesDetaches`).

2. **Composabilità cumulativa esplicita**: ogni estrazione di risorsa espone
   un flag "Limita la ricerca a quelli **già estratti**" (`Classes` = "Limita
   la ricerca alle classi già estratte", stesso pattern per
   `Eleve`/`Groupes`/`Materiels`/`Personnels`/`Professeurs`/`Salles`,
   `ExtraireListeCourante` = "Limita la ricerca alle attività già estratte") —
   cioè si può **raffinare progressivamente** un insieme già estratto
   applicando altri criteri, invece di ripartire da zero. È più vicino a una
   query SQL incrementale con stato persistito che a un filtro di vista.

3. **Il piazzamento automatico e l'ottimizzazione operano SOLO sull'estrazione
   corrente.** Confermato letteralmente:
   `FicheEDT_PlacementAuto_RS_PlacementExtraits` = "%d attività da piazzare tra
   quelle **estratte**" — non un sottoinsieme implicito, ma il perimetro
   esplicito su cui gira il piazzamento automatico. Stesso vincolo per
   Consigli (`FicheEDT_OptimiseurConseils_RS_Avertissement_DDDD`: "l'ottimizzazione
   tiene conto **solo** dei consigli piazzati estratti").

**[INFERENZA]** Il motivo architetturale: EDT non separa "seleziona → agisci"
in due UI diverse per ogni azione (piazza, ottimizza, esporta, stampa) — usa
**un'unica primitiva di selezione condivisa fra tutte le azioni successive**,
coerente col fatto che la stessa dicitura "Estratti/Extraits" compare
identica nei pannelli di Orario, Colloqui e Consigli. Per il nostro prodotto
questo suggerisce: se vogliamo dare all'utente controllo su "piazza/ottimizza
solo questo sottoinsieme", conviene modellarlo come **una selezione
persistente e riusabile**, non come un parametro ad hoc di ogni singola
azione.

**Proposta di scope: DENTRO (come pattern UX, non come funzionalità
1-a-1)** — il concetto di "selezione di lavoro persistente e componibile su
cui si applicano piazzamento/ottimizzazione" è utile indipendentemente dal
fatto che copriamo Colloqui o Consigli: è rilevante già per **Orario**, per
permettere "rigenera solo le classi del biennio" o "ottimizza solo il
sostegno" senza toccare il resto.

---

## 6. Importazioni / Esportazioni

### 6.1 Formati/ecosistemi osservati

**[STRINGA]** L'elenco delle famiglie `Import*`/`Export*` mostra che EDT
importa/esporta prevalentemente verso **sistemi ministeriali francesi**, non
verso standard aperti generali:
- `SIECLE` (`ImportSco_SIECLE`, `ExportSco_SIECLE`, `FicheSco_DonneesImportSIECLE`,
  `FicheSco_ImportSIECLE`) — sistema informativo alunni del Ministero francese
- `STS-Web` (`FicSTSWEBAssistantExport`, `FrameSco_ImportENT` — con ENT =
  Espace Numérique de Travail) — dati struttura/organico
- `Cyclades` (visto in `GlossaireImportExportSco`: `CycladesContraintesEleve`,
  ecc.) — esami di stato francesi
- `Parcoursup` (`ScoGlossaireExportParcoursup`) — orientamento post-diploma
  francese
- `LSU`/`LSL` (`FicheNOT_ExportLSUN`, `FicheNOT_ExportLSL`) — Livret Scolaire
  Unique/LSL, pagelle francesi
- `Sconet` (`FicheSco_ExportElevesSconet`, `FicheSco_CorrectionInfosSconet`) —
  altro sistema alunni ministeriale francese
- `SCOPE`/`FREGATA` (`ExportSco_SCOPE`, `ExportSco_FREGATA`) — non identificati
  con certezza, verosimilmente altri flussi ministeriali/regionali francesi
- **`Partenaire_Index`** (`FrameSco_ExportStandardPartenaire`,
  `FrameCP_ExportParPartenaire`, `TraitementSco_ReImportExportStandard`,
  `Type_ImportStandard`) — è il formato XSD **già documentato** in
  `docs/edt/schema-scambio.md`: qui appare confermato come "standard" generico
  di scambio fra applicativi terzi/partner, non solo un artefatto trovato
  nell'installazione.

**[STRINGA]** Blocco **italiano dedicato**, isolato e piccolo rispetto al resto:
`FicheNOT_ExportAvvioAnnoScolIT` (chiavi con suffisso `IT` esplicito):
"Esportazione frequenze" (inizio anno), "Esportazione Scrutini Finali
Analitici", "Esportazione Esami di Stato Crediti Scolastici", "Esportazione
Esami di Stato Piani Orario", "Esportazione Esiti Finali". Più
`ScoGestioneAlunnoSidi_IT` e `ScoRemplisseurSidi_IT` (2 chiavi ciascuna, non
approfondite: gestione/compilazione **SIDI**, il sistema informativo del MIM)
ed `ExportInvalsi_IT` (1 chiave: dati INVALSI). **[INFERENZA]** Questi sono
flussi verso il ministero italiano (verosimilmente per il registro elettronico
PRONOTE Italia, non per l'orario) — confermano che EDT/PRONOTE Italia esiste
come build localizzata con propri export ministeriali, coerente con quanto già
trovato su `TabellaSIDI.xml` (changelog 2026-07-26).

### 6.2 Import/export specifici dell'orario

**[STRINGA]** `FicheEDT_ImportEmploi` — "Importazione degli orari delle
classi/dei docenti": import di un orario **da un'altra base EDT**, con opzioni
di merge esplicite: `RemplacerCoursExistants` (sostituisci tutto) vs
`AjouterAuxCoursExistants` (aggiungi) vs priorità in caso di conflitto
(`ConserverPrioritePlaceExistants`/`...Importes`), gestione delle attività
complesse che coinvolgono risorse non presenti nella base di destinazione
(`ConserverComplexesClasse`/`...Prof` = "mantenere, sospendendole, le attività
complesse contenenti altre classi/docenti"). **Formato: proprietario
(EDT→EDT)**, non un formato di interscambio pubblico.

**[STRINGA]** `FicheEDT_ExportAscii` — esportazione tabellare **ASCII/CSV** con
opzioni granulari: per fascia oraria intera/parziale, con o senza componenti
dei gruppi, un file per famiglia/colonna per famiglia/riga per famiglia,
durate in decimale. È l'export "di servizio" per fogli di calcolo esterni, non
un formato semantico.

**[STRINGA]** **iCal** è supportato in tre punti distinti e indipendenti,
ciascuno per il proprio dominio: `ImpEDT_ExportICALRencontre` (colloqui),
`ImpEDT_ExportICALConseil` (consigli), `UtilitaireSco_ExportICal`/
`ImpSco_ExportICAL` (generico — verosimilmente l'orario personale). Contenuto
osservato per i colloqui: classe, alunno, materia, docente, indispensabilità
per genitore/docente, riga di generazione con branding
("generato dal software EDT ©Index Education"). **[INFERENZA]** iCal è quindi
il canale di export "verso l'esterno/verso il calendario personale", mentre
`Partenaire_Index` è il canale "verso altri applicativi gestionali".

**Proposta di scope: DA DECIDERE, con indicazione chiara** — nessuno di questi
formati è un candidato ovvio come **contratto di import** per noi: sono o
ministeriali francesi (fuori contesto Italia), o proprietari EDT→EDT
(inutilizzabili senza EDT stesso), o export minori (ASCII, iCal). L'unico
formato con valore dichiarato di "standard di scambio generico" resta
`Partenaire_Index` (XSD, già raccomandato per adozione in
`docs/decisioni.md`/`docs/edt/schema-scambio.md`); iCal è comunque utile **in
uscita** dal nostro prodotto (verso calendari personali dei docenti), a basso
costo di implementazione, indipendentemente dallo scope generale.

---

## Riepilogo domande

1. **Per ciascun modulo, scheduling? solver? scope?** → vedi le righe
   "Proposta di scope" in fondo a ciascuna sezione.
2. **Come funziona la ricerca del sostituto?** → Filtro multi-criterio
   (disponibilità totale/parziale, materia, sede, livello classe, consiglio di
   classe, buco esistente, ore residue d'incarico) + priorità dichiarata a 3
   livelli per docente/fascia oraria, **senza ottimizzazione globale**:
   workflow di richiesta/accettazione con assegnazione manuale finale. Nessun
   punteggio combinato osservato; le "priorità" sono un filtro/ordinamento, non
   un peso in una funzione obiettivo.
3. **Cos'è `Estrai`?** → Una selezione persistente e componibile
   (query incrementale, non semplice vista) su cui **tutte** le azioni
   successive (piazzamento automatico, risoluzione scarti, ottimizzazione)
   operano esclusivamente — confermato testualmente sia per Orario che per
   Consigli.
4. **Formati import/export?** → Ecosistema ministeriale francese (SIECLE,
   STS-Web, Cyclades, Parcoursup, LSU/LSL, Sconet) dominante; blocco italiano
   minore e isolato (SIDI, INVALSI, adempimenti fine anno); import/export
   orario proprietario (EDT→EDT) o minore (ASCII, iCal); `Partenaire_Index`
   resta l'unico formato con vocazione di "standard di scambio" generico.
