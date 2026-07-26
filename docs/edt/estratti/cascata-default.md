# Estratto — quanto è estesa la cascata di default in EDT

Fonte: `it_fr_en.tsv` (69 888 stringhe, chiave / IT / FR / EN), estratte dai binari
dell'installazione EDT 2026. Marcatore di fonte: 📦.

---

## Passo 1 — il marcatore `(Gr.)` — RISULTATO NEGATIVO (correzione)

**Ricerca esaustiva del pattern letterale `(Gr.)` su tutte le 69 888 stringhe: due
sole occorrenze**, e sono la stessa etichetta duplicata in due pannelli gemelli.

```
UtilitaireSco_GestionnaireDeRessource_RS_GroupeDeSalleInitiale   IT (Gr.)  FR (Gr.)  EN (Gr.)
UtilitaireSco_RessourceReservablePar_RS_GroupeDeSalleInitiale    IT (Gr.)  FR (Gr.)  EN (Gr.)
```

Il suffisso `Initiale` nella chiave significa «iniziale / sigla», cioè **il glifo
compatto mostrato in cella**. Accanto a ciascuna c'è la versione estesa (`Hint`)
che ne dà la semantica letterale:

```
UtilitaireSco_GestionnaireDeRessource_RS_GroupeDeSalleHint   IT (Gruppo di aule)  FR (Groupe de salle)  EN (Room group)
UtilitaireSco_RessourceReservablePar_RS_GroupeDeSalleHint    IT (Gruppo di aule)  FR (Groupe de salle)  EN (Room group)
```

E nello stesso pannello esiste un **secondo marcatore**, con la stessa grammatica:

```
UtilitaireSco_RessourceReservablePar_RS_GestionnaireInitiale  IT (G)  FR (G)  EN (M)
UtilitaireSco_RessourceReservablePar_RS_GestionnaireHint      IT (Gestore)  FR (Gestionnaire)  EN (Manager)
```

### Cosa significa davvero `(Gr.)`

⚠ **Non è il marcatore generale dell'ereditarietà dei default.** È il marcatore di
**provenienza di un diritto** in due sole griglie, entrambe di **permessi sulle
risorse prenotabili** (aule *e* materiali). `(Gr.)` = «questo diritto non è stato
dato su questa aula, viene dal gruppo di aule»; `(G)` = «viene dal fatto che questa
persona è gestore della risorsa».

Le regole di propagazione sono scritte in chiaro nelle stringhe adiacenti:

| chiave | testo IT (letterale) |
|---|---|
| `GestionnaireDeRessource_RS_DroitGererGroupeDonneDroitSousSalles` | «I docenti/risorse del personale che possono gestire questo gruppo di aule avranno **automaticamente** diritto a gestire tutte le aule che esso contiene.» |
| `RessourceReservablePar_RS_DroitReserverGroupeDonneDroitSousSalles` | «I docenti/risorse del personale che possono prenotare questo gruppo di aule avranno **automaticamente** diritto a prenotare le aule che esso contiene.» |
| `RessourceReservablePar_RS_HintGestionnaireGroupeSalle` | «Questo docente/risorsa del personale è gestore del gruppo di aule, ha **automaticamente** diritto a prenotare il gruppo e le aule che esso contiene.» |
| `RessourceReservablePar_RS_HintGestionnaireSalle` | «Questo docente/risorsa del personale è gestore dell'aula, ha **automaticamente** diritto a prenotarla.» |
| `RessourceReservablePar_RS_HintReservationGroupeSalle` | «Questo docente/risorsa del personale ha diritto a prenotare il gruppo di quest'aula, ha **automaticamente** diritto a prenotare quest'aula.» |

### I due campi su cui la cascata è dimostrata dal marcatore

1. **Gestori della risorsa** (`Gestionnaire`) — aula, gruppo di aule, materiale.
2. **Prenotabile da** (`Réservable par`) — aula, gruppo di aule, materiale.

Nient'altro. **Nessun campo di piazzamento** (indisponibilità, capienza, tipologia,
sede, quantità) porta il marcatore `(Gr.)` nelle stringhe.

### Conseguenza per il modello

- La cascata visibile sulle aule **non è una cascata di valori di default sui campi
  di pianificazione**: è **ereditarietà di ACL** dal contenitore ai contenuti, e
  riguarda il modulo **prenotazione risorse**, non il solver.
- Non genera colonne nullable sull'entità `Room`: genera semmai una **risoluzione a
  runtime dei permessi** (`utente ha diritto su aula X ⟸ diritto diretto ∨ diritto
  sul gruppo ∨ è gestore`), che è esattamente l'unione mostrata in UI con `(G)`/`(Gr.)`.
- ⚠ Da rileggere la nota in `docs/edt/aule.md` («la cascata di default vale anche
  sulle aule, suffisso `(Gr.)`»): l'osservazione UI è corretta, l'**interpretazione**
  va ristretta ai due campi di permesso qui sopra.

---

## Passo 2 — il vocabolario dell'ereditarietà — NESSUN MECCANISMO GENERALE

Conteggi esaustivi sulle 69 888 stringhe:

| lingua | pattern | occorrenze |
|---|---|---|
| FR | `propag` | **0** |
| IT | `propag` | **0** |
| IT | `per difetto` | **0** |
| FR | `hérit` | **2** |
| IT | `eredita` / `ereditat` | **2** |
| FR | `par défaut` | 327 |
| IT | `predefinit` | 260 |

### Le due sole occorrenze di «eredita» — e nessuna è del solver

```
Data_DBConsts_SNestedDataSetClass
   IT: Il dataset integrato deve ereditare da %s
   FR: Le dataset imbriqué doit hériter de %s
```
→ messaggio d'errore del **framework Delphi** (`Data_DBConsts`). Non è EDT: è la
runtime del linguaggio. Da scartare.

```
FournisseurAccesFicheTCommandesSco_RS_HeritageSalle
   IT: Quando un colloquio non ha un'aula definita eredita l'aula associata al
       docente/personale. L'aula verrà quindi associata di default.
   FR: Lorsqu'une rencontre n'a pas de salle définie, elle hérite de la salle
       associée aux professeurs/personnels. La salle par défaut sera donc affectée
```
→ **modulo Colloqui** (`rencontre`), non Orario. Ma è l'**unica cascata di valore
descritta in chiaro in tutto il prodotto**, ed è esattamente la semantica ADR-003:
*campo vuoto sull'istanza ⟹ risolvi risalendo alla risorsa collegata*.

### Conclusione del passo 2

**Non esiste un meccanismo di ereditarietà generale e nominato in EDT.** Nessuna
etichetta parla di propagazione, nessuna famiglia di chiavi è dedicata alla
risoluzione dei default. La cascata è un **comportamento locale, dichiarato caso per
caso**, non un'infrastruttura del modello. Le 327 `par défaut` sono in larghissima
maggioranza default di **UI/stampa** o di **PRONOTE** (registri, medie, valutazioni),
non default di campo che cascatano.

### ⚠ Distinzione decisiva emersa: copia-alla-creazione ≠ cascata viva

```
FicheEDT_IndispoAnnuelStandard_RS_GrilleAppliqueeDefautSurNouveauProf
   IT: Questa griglia sarà proposta alla creazione di un nuovo docente
   FR: Cette grille sera appliquée par défaut à la création d'un nouveau professeur

FicheEDT_IndispoAnnuelStandard_RS_GrilleAppliqueeDefautSurNouvelleClasse
   IT: Questa è griglia predefinita proposta alla creazione di una nuova classe
   FR: Cette grille sera appliquée par défaut à la création d'une nouvelle classe
```

Le **indisponibilità standard** (di docenti e di classi) esistono a livello globale,
ma il testo FR è inequivocabile: `à la création`. Il valore viene **copiato nella
riga** al momento della creazione, e da lì è indipendente — modificare la griglia
standard **non** ritocca i docenti già esistenti.

Questo è il **contrario** di `NULL = eredita`: è materializzazione del default.
Per il nostro schema significa che le indisponibilità **non** vanno nullable: vanno
copiate, con la griglia globale trattata come *template*, non come *livello di
risoluzione*. È il caso d'uso opposto a `Al./Rid.`.

---

## Passo 3 — `Statuto → Mh/s` — CHIUSO, MA NON COME IPOTIZZATO

### Il default globale su `Apport` esiste — ed era invisibile in italiano

```
FicheEDT_ParametresBase_OptionsRessources_RS_Apport
   IT: Monte ore settimanale dei docenti
   FR: Apport par défaut pour les professeurs
```

Il francese dice **`par défaut`**; **la traduzione italiana lo perde**. In UI italiana
il campo si legge come una semplice etichetta descrittiva, e non si vede che è un
**default globale**. Sta in `Parametri → Opzioni delle risorse`
(`FicheEDT_ParametresBase_OptionsRessources_RS_Titre` = «Opzioni delle risorse»).

⚠ Nota di metodo: **la traduzione italiana omette la semantica di default**. Dove si
cerca la cascata, va interrogato il **francese**, non l'italiano.

### Ma lo `Statuto` non è il livello intermedio — risultato negativo

Battuta l'intera famiglia di chiavi `Statut` in ambito EDT (~30 etichette). Lo
`Statuto` compare **solo** come:

- attributo anagrafico del docente (`FicAffInfosProfesseurEnseignement_RS_Statut`),
  con la sua tabella editabile (`EditSco_StatutProfesseur`);
- **statuto del motivo di assenza** (risorsa/accompagnatore/nessuno) — altro dominio;
- statuto di **docente coordinatore**; statuti **DEPP** (statistica francese).

**Nessuna stringa lega `Statut` a `Apport`**, né a un monte ore, né a un default.

### Conclusione: la catena su `Mh/s` è a due livelli, non a tre

```
globale (Parametri → Opzioni delle risorse: «Apport par défaut»)  →  docente
```

Lo `Statuto` **non è un livello di cascata**: è un attributo di classificazione,
usato per raggruppare nelle stampe (`EtatsDeServices`) e nelle statistiche, non per
ereditare valori. L'ipotesi «Statuto porta un Mh/s di default» è **da considerare
smentita sulle stringhe**.

**Residuo da verificare in UI** (una sola schermata): aprire
`Parametri → Opzioni delle risorse` e leggere il campo «Monte ore settimanale dei
docenti»; poi aprire la tabella degli statuti (`Modifica degli statuti`, pulsante
sulla scheda docente) e verificare **se quella tabella ha una colonna di monte ore**.
Se non ce l'ha — come le stringhe indicano — il punto è chiuso definitivamente.

---

## Sintesi — quanto è estesa la cascata

**Poco.** La cascata di default in EDT **non è un'infrastruttura**: è un pugno di casi
locali. L'elenco completo di ciò che le stringhe dimostrano:

| campo | catena | natura |
|---|---|---|
| `Al./Rid.` (materie) | globale → materia → istanza | cascata viva (già acquisito) |
| `Apport` / `Mh/s` (docenti) | **globale → docente** | cascata viva — FR `par défaut` |
| Aula del colloquio | docente → colloquio | cascata viva (modulo Colloqui) |
| `Gestionnaire` (aule/materiali) | gruppo di aule → aula | ereditarietà di **ACL**, non di valore |
| `Réservable par` (aule/materiali) | gruppo di aule → aula | ereditarietà di **ACL**, non di valore |
| Indisponibilità standard doc./classi | globale → istanza | ⚠ **copia alla creazione**, non cascata |

### Implicazione diretta per lo schema Django

La domanda era «quante colonne devono essere nullable». Risposta: **poche, e non
quelle che ci si aspettava**.

1. **Non serve rendere nullable tutto il modello.** Non esiste un livello «entità»
   generalizzato in EDT; la cascata è dichiarata campo per campo.
2. **Nullable davvero**: `Al./Rid.` sulla materia, `Mh/s` sul docente. Poco altro.
3. **Non nullable, ma con template**: le indisponibilità. Servono due meccanismi
   distinti nel nostro modello — *risoluzione a runtime* per (2), *copia alla
   creazione* per (3) — e confonderli produrrebbe il bug in cui cambiare un default
   globale riscrive le indisponibilità già personalizzate di tutti i docenti.
4. **Permessi, non valori**: `(Gr.)` è ACL. Se e quando faremo prenotazione risorse,
   è una risoluzione di diritti (unione), non una colonna nullable.
