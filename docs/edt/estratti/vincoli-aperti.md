# Quattro punti aperti sui vincoli — chiusura

Fonti usate, in ordine di autorevolezza:
**📦-str** = 69 888 stringhe di interfaccia (`it_fr_en.tsv`) · **📦-dat** = dati reali
della base demo `Esempio.edt` (letta in sola lettura, copiata in scratchpad) ·
**📦-typ** = enum interni (`docs/edt/estratti/catalogo-tipi-interni.md`) ·
**📖** = guida ufficiale online (`doc.index-education.com`), da confermare in UI.

Nessun file sotto `~/.wine` o `~/Desktop/EDT_COMPLETE` è stato modificato.

---

## 1. `Fractionnable` — la colonna `P.P.` / `P.F.`

### 1.1 La premessa da correggere: `P.P.` e `P.F.` sono la stessa colonna

**📦-str, prova letterale:**

```
UtilitairesEdt_ColonnesRessources_RS_FractionnableCourt
   IT: P.P.        FR: P.P.        EN: P.F.
UtilitairesEdt_ColonnesRessources_RS_FractionnableLong
   IT: Proprietà di piazzamento     FR: P.P.     EN: P.F.
```

`P.P.` = **Proprietà di Piazzamento** = FR *Propriété de Placement* = EN *Placement
Feature* (`P.F.`). **Non** sono due colonne (`Parte Principale` / `Parte Finale`):
sono l'**abbreviazione della stessa colonna in due lingue diverse**. L'ipotesi di
partenza è smentita.

⚠ **Collisione di sigla da non confondere**: esiste un *altro* `PP` in EDT —
`Type_Contrainte_RS_LegendePP | IT: Peso didatt. | FR: Poids pédago.` — che è la
lettera di legenda della **diagnostica del peso didattico** (punto 4). Stessa
sigla, due significati.

### 1.2 Cosa significa

**📦-str, prova letterale (il tooltip della colonna):**

```
UtilitairesEdt_ColonnesCours_RS_HintFractionnable
   IT: Proprietà di piazzamento, influisce sulla collocazione dell'attività:
       fissa o variabile
   FR: Propriété de placement, influe sur la place du cours : fixe ou variable
```

E l'altro capo della catena, che lega *non-fractionnable* → *cours fixe*:

```
AffEDT_RechercheSallesLibres_RS_NonFractionnable
   IT: La ricerca dell'aula per un'attività fissa è possibile solamente
       sull'insieme dei suoi periodi!
   FR: La recherche de salle pour un cours fixe n'est possible que sur
       l'ensemble de ses périodes !
```

I due valori della colonna sono già documentati altrove nel prodotto:

```
FicheEDT_CreationCours_RS_PlaceFixe        IT: Fascia fissa      FR: Place fixe
FicheEDT_CreationCours_RS_PlaceVariable    IT: Fascia variabile  FR: Place variable
FicheEDT_ExtractionCours_RS_Coursfixes     IT: Attività fisse    FR: Cours fixes
FicheEDT_ExtractionCours_RS_Coursvariables IT: Attività variabili FR: Cours variables
```

**Conclusione (solida).** `Fractionnable` è il **nome interno** di ciò che la UI
chiama `Fascia fissa` / `Fascia variabile` — cioè esattamente il campo già
documentato in `docs/edt/tempo-e-calendario.md` §"Fascia fissa / fascia variabile"
e in `motore-risoluzione.md`. "Frazionabile" significa **frazionabile fra i
periodi**: un'attività variabile può assumere una collocazione diversa in ogni
periodo, quindi la sua collocazione annuale si "frantuma" in *n* collocazioni.
Non ha nulla a che vedere con lo spezzamento di un blocco di ore.

Il badge `F`/`V` osservato in UI (`docs/edt/attivita.md:272`, `diagnostica.md:479`)
è quindi confermato: `F` = fissa, `V` = variabile.

**Default = `F` (fissa)** — 📖, guida ufficiale, pagina *Périodes*: *"By default,
courses are fixed: EDT finds the same place for all periods of the course. If you
want to give more possibilities to the calculator and accept having different
schedules depending on the periods, you can make the courses variable."*
Coerente con l'osservazione in UI (`P.P.` = `F` su tutte le righe della base demo).
La stessa pagina aggiunge che la proprietà di piazzamento è fra le caratteristiche
**sempre modificate sull'intero anno** (con materia, statuto di export e blocco) —
cioè non è un attributo per-periodo.

### 1.3 Relazione con lo spezzamento padre/figlio di `attivita.md`

**Nessuna: sono due meccanismi ortogonali, e l'italiano li distingue con due
parole diverse** ("frazionare" vs "sezionare").

| | `Fractionnable` = `P.P.` | spezzamento padre/figlio |
|---|---|---|
| colonna | `P.P.` (*Proprietà di piazzamento*) | `Ri`/`Sudd.` (*Modalità di sezionamento*) |
| chiave | `…ColonnesCours_RS_HintFractionnable` | `…ColonnesCours_RS_HintRepartition` |
| testo | "fissa o variabile" | "Modalità di sezionamento: S - standard,… P - personalizzata" |
| enum interno (📦-typ) | — | `TypeModeRepartitionCours` (10 valori) |
| asse | **periodi** (una collocazione per periodo) | **durata** (madre → lezioni figlie) |

Prove di supporto sul lato "sezionamento":

```
FicEDT_FrameCours_RS_AfficherLesCoursFils
   IT: Nascondi le lezioni delle attività sezionate
   FR: Masquer les séances des cours personnalisés
FicCoherenceVariable_RS_DureeCoursPereNonDiminuable
   IT: Non è possibile diminuire la durata dell'attività madre direttamente qui…
```

Le 12 conferme di permuta (`FournisseurAccesFichePermutationEDT_RS_ConfC*Fractionne`,
es. *"Le due attività saranno frazionate. Confermate il loro scambio?"*) sono
coerenti: scambiando due attività che non esistono sugli stessi periodi, l'attività
deve diventare variabile — cioè **frazionarsi per periodo**.

⚠ Una sola stringa mescola i due termini ed è con ogni probabilità un errore di
traduzione: `Types_TraitementEmploiDuTemps_RS_refusFractionnement | IT: "L'attività
non può essere sezionata" | FR: "Le cours ne peut pas être fractionné"`.

### 1.4 Implicazione per noi

Il campo è già coperto da [ADR-010](../../decisioni.md) (collocazione per periodo
**fuori scope**, si rigenera a ogni periodo). Quindi: `P.P.` **non è un vincolo
nuovo**, è la stessa feature già dichiarata fuori scope. Nel nostro modello
corrisponde all'assunzione implicita "tutte le attività sono fisse".

---

## 2. `Cours isolés` — Attività isolate

### 2.1 La definizione, letterale

**📦-str:**

```
Chaines_ClientGraphiqueEdT_RS_DefCoursIsoles
   IT: Attività isolata: attività isolata in una mezza giornata e di durata
       inferiore a due fasce orarie.
   FR: Cours isolé : cours seul dans une demi-journée et dont la durée est
       inférieure à 2 séquences.
   EN: Isolated course: single course in a half-day whose duration is inferior
       to 2 sequences.
```

Confermata da fonte indipendente 📖 (guida, *Cours isolé*): *"Un cours est
considéré comme isolé lorsqu'il est seul dans une demi-journée et que sa durée est
inférieure à 2 séquences horaires."* — identica.

Quindi la definizione ha **due condizioni congiunte**: (a) unica attività della
mezza giornata, (b) durata < 2 fasce. Un'attività da 2h da sola in una mattinata
**non** è isolata.

### 2.2 Che cosa è: criterio di ottimizzazione + contatore. Non è un vincolo.

**Criterio di ottimizzazione** — è una delle cinque voci della tendina dei criteri:

```
AffEDT_ParametresOptimisation_RS_Aucun        IT: Nessuno            FR: Aucun
AffEDT_ParametresOptimisation_RS_Isoles       IT: Attività isolate   FR: Cours isolés
AffEDT_ParametresOptimisation_RS_JourneeLibres IT: 1/2 giornate libere FR: 1/2 journées libres
AffEDT_ParametresOptimisation_RS_Regularite   IT: Equilibrio didattico FR: Régularité des cours
AffEDT_ParametresOptimisation_RS_Trous        IT: Durata totale dei buchi FR: Durée cumulée des trous
FrameEDT_GraphiqueOptim_RS_Isoles             IT: Attività isolate   FR: Cours isolés
```

📦-typ: `TypeChoixOptim = tcoDJLibres, tcoTrous, tcoIsoles, tcoMemesHoraires,
tcoAucun` — `tcoIsoles` è lì. Già a indice in `motore-risoluzione.md` §criteri.
📖 conferma l'uso: *"Lors de l'optimisation, EDT réduit le nombre de cours isolés."*

**Colonna/contatore** su docenti, classi e gruppi:

```
UtilitairesEdt_ColonnesRessources_RS_CoursIsolesCourt  IT: A.iso.       FR: C.iso.
UtilitairesEdt_ColonnesRessources_RS_CoursIsolesLong   IT: Att.isolate  FR: C. isolés
UtilitairesEdt_ColonnesClasse_RS_HintCoursIsoles
   IT: Classi: Numero di attività isolate per tutti gli alunni della classe
       Gruppi: Scarto in numero di attività isolate per un alunno che appartiene
       a questo gruppo e a tutti i gruppi collegati
```

📦-typ: `ColProfCoursIsoles` è una delle 100 colonne di `TypeColonneProfesseur`.

**Non è un vincolo.** Prova negativa, robusta: la legenda `Type_Contrainte_RS_*`
elenca **tutte** le famiglie di vincolo diagnosticabili (Indisponibilità, Ind.
opzionali, Mensa, Intervallo, Max ore, Max presenza, Peso didatt., Vincolo materia,
Vincolo tra attività, Mezze giornate di lavoro, Giorni e 1/2 giornate libere, Sedi
distaccate, Gestione entrate/uscite, Inizio possibile, Distribuzione oraria,
Assenza, attività prioritaria/non prioritaria) — **`attività isolate` non c'è**.
Non esiste nessuna stringa "massimo di attività isolate", nessun parametro,
nessuna causale di diagnostica.

**Conclusione (solida).** `Cours isolés` è (a) una **funzione obiettivo** selezionabile
in ottimizzazione e (b) una **colonna diagnostica di conteggio** per risorsa. Mai un
vincolo. Per noi: è un termine della funzione obiettivo, con una definizione
operativa esatta e facile da implementare (`unica attività della mezza giornata AND
durata < 2 fasce`).

⚠ Da non confondere con `FicCoursComplexe_RS_IsolerSeances` ("Trasforma in attività
semplice e indipendente"): là "isolare" è un **comando** che scorpora una lezione da
un'attività complessa, un'omonimia.

---

## 3. `Interclasse` — è il **falso amico**: significa *intervallo/ricreazione*

### 3.1 Prova letterale

```
UtilitairesEdt_ColonnesRessources_RS_InterclasseCourt   IT: Int.   FR: Ré   EN: Rec
UtilitairesEdt_ColonnesRessources_RS_InterclasseLong    IT: Intervallo  FR: Récréation  EN: Recess
UtilitairesEdt_ColonnesCours_RS_HintInterclasse
   IT: Le attività spuntate devono rispettare gli intervalli
   FR: Les cours marqués sont soumis aux récréations
FicParametreEtablissementRecreations_RS_WinEtatGestionInterclasses
   IT: Gestione degli intervalli    FR: Gestion des récréations
```

FR `interclasse` = *intervallo fra due lezioni*, sinonimo interno di `récréation`.
**Non** ha niente a che vedere con "trasversale alle classi".

### 3.2 Il modello completo

È un **vincolo hard di terza parte**, con tre entità:

1. **La ricreazione** è un oggetto d'istituto, non una proprietà della griglia.
   📦-dat, tabella `RECREATION` / `TNetRecreation` della base demo, **2 record in
   chiaro**:
   ```
   ArTi ident=1 … "Intervallo del mattino"    02 00 00 00 … 01 01
   ArTi ident=2 … "Intervallo del pomeriggio" 04 00 00 00 … 01 02
   ```
   (il `u32` = rango della fascia a cui l'intervallo è agganciato: 2 e 4).
   Si definisce in `Parametri > ISTITUTO > Intervalli`, trascinando linee gialle
   sulla griglia (`FicParametreEtablissementRecreations_RS_DeplacerLesTraitsRecreations`),
   e ha una **durata** modificabile (`ModifierDuree`).

2. **L'intervallo è associato a un insieme di classi**, non a tutte.
   ```
   EditSco_Cours_RS_AucuneRecreationConcerneClasse_Bis
     IT: Per fare in modo che un'attività rispetti gli intervalli, dovete
         associare le sue classi agli intervalli che devono rispettare in
         Parametri > ISTITUTO > Intervalli
   FicParametreEtablissementRecreations_RS_ModifierClassesConcernees
     IT: Modifica le classi coinvolte
   ```
   📦-dat: esiste una tabella `NONRESPECTCLASSERECREATION` /
   `TNetNonRespectClasseRecreation` (0 record nella demo) — la deroga per classe.

3. **Ogni attività porta un booleano** `Interclasse` (`Rispetta gli intervalli`),
   spuntabile alla creazione e in colonna:
   ```
   FicheEDT_CreationCours_RS_Interclasses  IT: Rispetta gli intervalli
   FicheSco_ParamCreationCours_RS_Interclasses  IT: Rispetta gli intervalli
   ```

### 3.3 Che è davvero un vincolo hard, e cosa vincola

- è nella **legenda dei vincoli**: `Type_Contrainte_RS_LegendeRecreation | IT:
  Intervallo | FR: Récréation`;
- ha una **causale di diagnostica**: `AffSco_UtilDiagnostic_RS_Recreation | IT:
  Intervallo non rispettato`;
- è una **riga dell'analisi dei vincoli**: `FicCoherenceVariable_RS_RespecterRecres
  | IT: Rispettare gli intervalli`;
- ha un **motivo di infattibilità dedicato**: `FicEDT_FrameCours_RS_PlageAvecInterclasse
  | IT: "Il rispetto degli intervalli è incompatibile con la durata dell'attività."`
- si può **disattivare esplicitamente** nel solver: `FicSolut_RS_IgnorerRecreation`,
  `FicheEDT_PlacerAmenagerAnnuel_RS_IgnorerRecreation` (*Ignora gli intervalli*),
  e c'è un indicatore di stato globale `FicheEDT_PlacementAuto_RS_RecreationsAttive/Inattive`;
- **blocca l'allineamento**: `Glossaire_Alignement_RS_AlignementRecreationsIncompatibles
  | IT: "Per poter essere allineate, le attività devono avere lo stesso statuto
  rispetto agli intervalli"` (è una delle 11 ragioni di rifiuto dell'allineamento,
  `cAlignementRecreationsIncompatibles`);
- interagisce con le **sedi**: `AffSco_UtilDiagnostic_RS_SitesIncompatiblesHeureTransitionRecreation
  | IT: "Cambio di sede al di fuori degli intervalli"` — i trasferimenti fra sedi
  sono ammessi solo durante un intervallo.

**Semantica del vincolo**: un'attività spuntata **non può stare a cavallo** di un
intervallo che riguarda le sue classi (cfr. il comando `Estrai le attività a cavallo
dell'intervallo`, `ActionsEDT_Client_RS_FicMenusExtraireCoursAvecRecreation`, e il
messaggio "incompatibile con la durata dell'attività").

**Conclusione (solida).** `Interclasse` = `Intervallo` = vincolo hard, opzionale
per attività, definito per (intervallo × classi). Conferma diretta della nota già
in CLAUDE.md ("`Mensa` e `Intervallo` sono fra le dieci famiglie violabili → sono
hard"). Per noi è un vincolo **facile e a valore alto**: impedisce blocchi da 2h a
cavallo della ricreazione, cioè un vincolo che le scuole italiane hanno davvero.

---

## 4. Peso didattico — scala, default, combinazione dei tetti

### 4.1 La scala: **0–10 per materia** (📖, non ancora confermato in UI)

Guida ufficiale, pagina *Poids pédagogique* / *Peso didattico*, entrambe le lingue:
è possibile assegnare a ogni materia **un peso da 0 a 10**, da `Orario > Materie`,
icona *Pesi didattici*, oppure in multiselezione con
`Modifica > Peso didattico` (comando confermato dalle stringhe:
`ActionsEDT_Client_RS_FicMenusMenuAffecterPoidsPedagogique | IT: Peso didattico`,
e il titolo della finestra di inserimento
`Chaines_ClientGraphiqueEdT_RS_TitreSaisiePoidsPedagogique | IT: Peso didattico`).

Nelle 69 888 stringhe **non esiste** alcun messaggio di validazione che citi
l'intervallo del peso (l'unico bound numerico affine è di un altro campo:
`FicSaisiePonderation_RS_ValeurTropGrande | IT: "Il coefficiente di ponderazione
deve essere compreso tra 0 e 10."`, che riguarda la **ponderazione** dei servizi,
non il peso). **La scala 0–10 poggia quindi solo sulla guida 📖.**

⚠ Il peso è dichiarato **per materia e per ora**, non per attività:
```
Chaines_EdT_RS_Col_PoidsMatiereHint      IT: Peso unitario per materia e per ora
Chaines_EdT_RS_Col_PoidsMatiereTitreLong IT: Peso     FR: Poids
Chaines_EdT_RS_Col_TotalPoidsMatiereHint IT: Peso didattico delle attività della materia
```
Il peso di un'attività è quindi `peso_materia × durata_in_ore`. E la guida dice che
il peso si assegna **per una selezione di classi**, quindi è overridabile per classe
(finestra `FicEDT_AffClassesPoidsMatieres`, che affianca l'elenco classi a
`Peso didattico per materia`).

### 4.2 Il valore di default: **non trovato nelle stringhe; nella base demo è 0**

📦-dat, tabella `MATIERE` / `TNetMatiere` della base demo, **tutti e 21 i record
letti in chiaro**. Layout decodificato:

```
ArTi | ident(u32) | u32 | codice(str) | nome(str) | u32 | colore RGB(4B)
     | flags(u32) | FK METAMATIERE(u32) | u32 | FK DISCIPLINE(u32) | 3 × u32 = 0
```

I due FK sono verificati su dati reali (es. `ARTE` → METAMATIERE ident 41 "ARTE",
DISCIPLINE ident 1 = `A-01 ARTE E IMMAGINE`; `MATEMATICA` → METAMATIERE 2
"MATEMATICA", DISCIPLINE 8 = `A-28 MATE-SCIENZE`; `SCIENZE MOTORIE` → DISCIPLINE
14 = `A-49`).

**Le tre `u32` di coda sono zero su tutte e 21 le materie.** Coerentemente,
`CONTRAINTESCLASSE` (41 record) ha tutti i campi di limite a zero tranne un
`08 00 00 00` ricorrente (max ore/giorno = 8).

**Conclusione:** nella base di riferimento del prodotto — 40 classi, 20 materie,
984 attività **tutte piazzate** — il **peso didattico non è usato affatto**. Non
posso quindi ricavarne un default né una distribuzione reale di valori. Il default
è **plausibilmente 0** ("nessun peso", funzione spenta), ma è un'inferenza dal
fatto che il campo è a zero in una base per il resto completa: **non è provato**.

Corollario utile: nessuna delle due basi disponibili mostra la feature in uso.
La scala 0–10 e la semantica dei tetti restano **da confermare in UI**.

### 4.3 I tetti: cinque finestre annidate, non componibili

Le etichette, tutte dalla stessa finestra (`Orario > Materie > Pesi didattici`):

```
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaLimitesTitre
   IT: Peso didattico massimo per l'istituto:
   FR: Limites des poids pédagogiques pour l'établissement :
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaLimiteMatin     IT: Limite del mattino:
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaLimiteApMidi    IT: Limite del pomeriggio:
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaLimiteJournee   IT: Limite della giornata:
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaLimiteSemaine   IT: Limite della settimana:
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaLimiteCycle     IT: Limite del ciclo:
FicEDT_AffClassesPoidsMatieres_RS_FicPoidsMaAucune          IT: nessuno   FR: aucune
```

**Come si combinano.** Non si combinano: sono **cinque tetti indipendenti su
finestre temporali annidate** (mezza giornata mattino ⊂ giornata ⊂ settimana ⊂
ciclo; mezza giornata pomeriggio ⊂ giornata), ciascuno con valore proprio o
`nessuno`. La grandezza confrontata è sempre la stessa: la **somma** dei pesi
didattici delle attività dell'alunno in quella finestra. Le tre somme sono
mostrate in fondo alla griglia oraria:

```
AffScoGrilleAnnuelV_RS_HintPoidsPiedGrille1Fin  IT: Totale dei pesi didattici della mattinata.
AffScoGrilleAnnuelV_RS_HintPoidsPiedGrille2Fin  IT: Totale dei pesi didattici del pomeriggio.
AffScoGrilleAnnuelV_RS_HintPoidsPiedGrille3Fin  IT: Totale dei pesi didattici della giornata.
AffScoGrilleAnnuelV_RS_HintPoidsPiedGrilleDepasse
   IT: Il totale appare in rosso quando il limite viene superato
AffScoGrilleAnnuelV_RS_HintPoidsPiedGrilleLimite      IT: - Limite definito: %s
AffScoGrilleAnnuelV_RS_HintPoidsPiedGrilleLimiteAucune IT: nessuno
```

**Settimana e ciclo sono alternativi**, come per i massimi orari: è la stessa
dualità *per settimana / per ciclo* già documentata in `motore-risoluzione.md`;
la base è su settimana **oppure** su ciclo, non su entrambi.

**Due livelli, non uno.** Oltre ai tetti d'istituto esiste un tetto **per classe**:

```
TableAffEDT_ClassesPoidsMatieres_RS_Col_PoidsClasseTitreLong  IT: Peso didattico
TableAffEDT_ClassesPoidsMatieres_RS_Col_PoidsClasseHint
   IT: Peso didattico massimo per settimana per un alunno
   FR: Poids pédagogique maximum par semaine pour un élève
TableAffEDT_ClassesPoidsMatieres_RS_HintPoidCoursPlaces      IT: Pesi attività piazzate
TableAffEDT_ClassesPoidsMatieres_RS_HintPoidCoursNonPlaces   IT: Pesi attività non piazzate (max.)
TableAffEDT_ClassesPoidsMatieres_RS_HintPoidCoursTotal       IT: Peso totale attività settimana
```

⚠ **Discrepanza fra guida e stringhe.** La guida 📖 nomina solo tre tetti
(giornata, mattino, pomeriggio) e dice che *"valgono per tutte le classi
dell'istituto"*. Le stringhe ne mostrano **cinque** (+ settimana, + ciclo) e in più
un tetto settimanale **per classe**. Le stringhe sono la fonte più recente
(build 2026); la guida è probabilmente arretrata. **Da verificare in UI.**

### 4.4 Diagnostica e alleggerimento

Le causali sono **quattro, tutte infragiornaliere**:

```
AffSco_UtilDiagnostic_RS_PoidsPedagogiquesMatin        IT: Limite di pesi didattici superato nel mattino
AffSco_UtilDiagnostic_RS_PoidsPedagogiquesSoir         IT: Limite di pesi didattici superato nel pomeriggio
AffSco_UtilDiagnostic_RS_PoidsPedagogiquesMatinOuSoir  IT: Limite di pesi didattici superato nel mattino o nel pomeriggio
AffSco_UtilDiagnostic_RS_PoidsPedagogiquesJournee      IT: Limite dei pesi didattici superato nella giornata
```

**Non esiste una causale per settimana né per ciclo** — indizio che i tetti
settimana/ciclo siano informativi (colonna di bilancio) e non applicati dal
risolutore, mentre i tre infragiornalieri sono hard. Da confermare in UI.

Nell'analisi dei vincoli il peso ha **due azioni suggerite proprie**:

```
WinCoherenceInterpretation_RS_AugmenterLimitesPoids IT: Aumentare i limiti dei pesi didattici
WinCoherenceInterpretation_RS_DiminuerPoids         IT: Diminuire i pesi didattici di alcune materie
WinCoherenceInterpretation_RS_PoidsPedagogiques     IT: I pesi didattici
FicCoherenceVariable_RS_ColonnePoidsLong            IT: Pesi didattici
Type_Contrainte_RS_LegendePP                        IT: Peso didatt.   FR: Poids pédago.
FicheT_Legende_RS_DiagPoidsPedagogique_S            IT: %s Peso didattico
```

E un alleggerimento dedicato:

```
FicAssouplissements_RS_PoidsPedag       IT: Peso didattico delle materie
FicAssouplissements_RS_PoidsPedag1      IT: Autorizza un supplemento di
FicAssouplissements_RS_PoidsPedag2      IT: un giorno per settimana.
FicAssouplissements_RS_PoidsPedagCycle2 IT: un giorno per ciclo.
```

### 4.5 🔑 Effetto collaterale: chiuso l'enigma dei «punti» negli alleggerimenti

CLAUDE.md ha aperto il punto *«Il significato dei punti nella finestra degli
alleggerimenti: l'unico indizio di un punteggio in un motore che altrove usa solo
quote.»* La coppia singolare/plurale lo scioglie:

```
FicAssouplissements_RS_FicAssouplissementPoint   IT: punto   FR: point
FicAssouplissements_RS_FicAssouplissementPoints  IT: pesi    FR: points
```

Il traduttore italiano ha reso il plurale `points` con **`pesi`**: l'unità è il
**punto di peso didattico**, usata nella riga `Peso didattico delle materie`
("Autorizza un supplemento di *N* pesi un giorno per settimana"). **Non è un
punteggio globale del motore, e non c'è nessuna funzione di penalità nascosta:**
resta vero che ogni alleggerimento è una **quota**, mai un peso. Il punto aperto
si può chiudere.

---

## Riepilogo di ciò che resta da guardare in UI

| # | Cosa | Dove |
|---|---|---|
| 1 | Nulla — chiuso da tre fonti concordi. | — |
| 2 | Nulla — chiuso da due fonti concordi. | — |
| 3 | Nulla di essenziale. Se serve la conferma visiva: `Parametri > ISTITUTO > Intervalli` (associazione classi + durata). | — |
| 4a | **La scala 0–10** — solo 📖, mai vista in UI. | `Orario > Materie`, icona *Pesi didattici*, cella `Peso` |
| 4b | **Il valore di default** di una materia nuova (0? 1?). Non ricavabile: la base demo ha tutto a zero. | creare una materia nuova e leggere la colonna `Peso` |
| 4c | **Quanti tetti esistono davvero** (3 secondo 📖, 5 secondo le stringhe) e se settimana/ciclo siano hard o solo informativi. | riquadro inferiore della stessa finestra |
| 4d | Se il tetto settimanale **per classe** conviva con quello d'istituto o lo sostituisca. | colonna `Peso` della tabella classi nella stessa finestra |
