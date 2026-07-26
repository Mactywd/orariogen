# EDT — Il motore di risoluzione

> Fonte 📦: enumerazioni RTTI estratte da `EDT Monoposto.exe` e stringhe di
> interfaccia da `EDT Monoposto.dll`. Non sono tabelle persistite: sono il modello
> che EDT costruisce in memoria per risolvere. Livello di autorevolezza medio —
> i nomi dei valori sono certi, la loro semantica è inferita (vedi
> [ADR-009](../decisioni.md)).

## Perché documentarlo

Non per copiarlo. Per **sapere cosa un motore maturo ritiene necessario** prima
di decidere cosa entra nel nostro v1 ([ADR-008](../decisioni.md)). EDT risolve lo
stesso problema da trent'anni: la struttura delle sue scelte è informazione, non
prescrizione.

## Il piazzamento è una pipeline a 7 fasi

`TypeEtatPlacementAuto`:

```
cCalculDebut → cCalculPlacement → cCalculReevaluation → cCalculOptimisation
             → cCalculResolRapide → cCalculResolIntegre → cCalculFin
```

Quattro cose da notare:

1. **Piazzamento e ottimizzazione sono fasi distinte.** Prima si trova *una*
   soluzione ammissibile, poi la si migliora. Non è un unico problema di
   ottimizzazione vincolata.
2. C'è una fase di **rivalutazione** separata fra le due.
3. **Due modalità di risoluzione**, rapida e integrale — cioè la profondità di
   ricerca è un parametro utente, non una costante.
4. Il nostro prototipo CP-SAT fa *tutto in una volta*. Funziona sul problema
   ridotto; su quello reale, la separazione trova/migliora è probabilmente
   necessaria — se non altro per dare risultati intermedi all'utente.

## Si ottimizza per docenti **o** per classi, mai insieme

`TypeTypeOptim = ttoProfs, ttoClasses`

È una scelta di progetto forte: EDT non cerca un ottimo congiunto, chiede
all'utente **per chi** ottimizzare. I criteri disponibili
(`TypeChoixOptim`) sono quattro:

| Valore | Criterio |
|---|---|
| `tcoDJLibres` | mezze giornate libere |
| `tcoTrous` | buchi |
| `tcoIsoles` | attività isolate |
| `tcoMemesHoraires` | stessi orari (regolarità settimanale) |

Coerente con le due leve separate viste in UI: `Riduci i buchi (docenti)` e
`Riduci i buchi (classi)` sono comandi distinti.

**Implicazione per noi.** Se il nostro solver espone una funzione obiettivo
unica con pesi, stiamo facendo una cosa che EDT ha deliberatamente evitato.
Vale la pena capire perché prima di divergere: probabile che l'ottimo congiunto
sia instabile o incomprensibile all'utente.

## La strategia a due passate: rispetta tutto, poi alleggerisci

Testo letterale del prodotto:

> `Il piazzamento delle attività scartate rispetta automaticamente tutti i
> vincoli. Se dopo un primo calcolo rimangono delle attività scartate, potete
> alleggerire certi vincoli. Attivate l'opzione "Alleggerisci" e sbloccate i
> vincoli che desiderate alleggerire.`

Cioè: **tutti i vincoli sono hard di default**, e il rilassamento è un atto
esplicito dell'utente su vincoli scelti. Non esistono penalità implicite.

### Confermato in UI (2026-07-26)

La finestra di creazione di un **vincolo fra attività** riporta, in una casella
**spuntata di default**:

> ✔ `Vincolo opzionale (può essere alleggerito durante il piazzamento delle
> attività scartate)`

Tre conferme in una riga: l'`allègement` esiste col nome di *alleggerimento*, la
seconda passata sulle **attività scartate** è quella descritta qui sopra, e
l'opzionalità è dichiarata **per singolo vincolo** al momento della creazione.

⚠ Una sfumatura che corregge la lettura precedente: i vincoli fra attività
**nascono opzionali**, non hard. Il "tutto hard di default" vale per la famiglia
dei vincoli di risorsa, non universalmente. Vedi [vincoli.md](vincoli.md).

### Quali vincoli EDT sa rilassare

La finestra `Alleggerimenti` (FR `Assouplissements`) è di fatto la dichiarazione
ufficiale di cosa è rilassabile:

| Alleggerimento | |
|---|---|
| Massimo di ore | dei docenti · delle classi · delle materie |
| Presenza massima | dei docenti |
| Massimo ½ giornate lavorate | dei docenti · delle classi |
| Giorni e ½ giornate libere | (le garanzie `G`) |
| Gestione Entrate/Uscite | dei docenti · delle classi |
| Incompatibilità materie | |
| Sequenze indesiderate di materie | |
| Peso didattico delle materie | |
| Cambi di sede | dei docenti · degli alunni |

Più un tetto globale: `Numero massimo di vincoli da alleggerire per risorsa`.

### Il rilassamento è sempre a quota, mai a interruttore

Non esiste "spegni il vincolo". Le formule sono tutte del tipo:

> `Autorizza un supplemento di … una volta per settimana e per docente`
> `Togli se necessario … mezze giornate libere per settimana`
> `Non considerare le incompatibilità … per settimana e per classe, una sola
> volta al giorno`

**Implicazione per noi, importante.** Un vincolo rilassabile non diventa soft:
resta hard con una **quota di violazioni** limitata e attribuita (per risorsa,
per periodo). Nel modello CP-SAT questo si esprime con variabili di violazione
vincolate in somma, non con penalità nell'obiettivo. È una differenza sostanziale
di formulazione.

## Le indisponibilità hanno un modello a tre enum

`TypeVEnumIndispo`, `TypeVPresenceIndispo` e `TypeGenreVZoneContrainteSimple`
(`Matin` / `ApresMidi` / `Jour`) formalizzano il rosso/giallo/verde della griglia
e distinguono l'indisponibilità **della risorsa** da quella **dell'attività** —
sono cose diverse e cumulabili (`eVIIndispoRessourceEtCours`).

`TypeJourGaranti = jgJournee, jgDemiJour, jgMatin, jgApresMidi, jgDemiJourParJour`
— le garanzie di giorno libero hanno cinque forme, non una.

## Validazione dell'allineamento: 11 modi di fallire

`TypeRefusAlignementCours` elenca perché EDT rifiuta di costruire un'attività
complessa:

| Causa | |
|---|---|
| `JoursIncompatibles` | giorni incompatibili |
| `EtatsIncompatibles` | stati incompatibili |
| `FrequencesIncompatibles` | frequenze incompatibili |
| `CalendriersIncompatibles` | calendari incompatibili |
| `ProfesseurManquant` | docente mancante |
| `Superposition` | sovrapposizione |
| `CoursFilsUnique` | un solo corso figlio |
| `EnveloppeTropPetite` | involucro troppo piccolo |
| `RecreationsIncompatibles` | ricreazioni incompatibili |
| `CoursAvecContrainteCaC` | attività già soggetta a vincolo attività↔attività |
| `ErreurInattendue` | errore imprevisto |

È **già la specifica di validazione** da implementare quando costruiremo gli
allineamenti. Vale la pena riusarla così com'è: sono i casi che si presentano
davvero.

## Perché un'attività non è piazzabile in blocco

`TypeHeterogeneiteElementaireCours` dà sette ragioni di "non omogeneità":
`Physique`, `MalPrecise`, `Domaine`, `PartiesNonLiees`, `Matiere`,
`ContrainteMatiere`, `Site`. Utile come lista di controlli preventivi: prima di
tentare il piazzamento, EDT verifica che l'attività sia coerente.

## L'assegnazione delle aule è un problema separato

Non fa parte del piazzamento: ha criteri propri (`TypeChoixOptimSalle`), le aule
si annidano (`dcsSousSalle`) e `TypeIncompatibiliteSalle` ha 11 valori.

**Implicazione per noi.** Assegnare le aule *dopo* aver piazzato le attività è
una semplificazione legittima, validata da un prodotto maturo — non una scorciatoia.
Il nostro v1 può farlo in due fasi senza sensi di colpa.

**Confermato in UI (2026-07-26)**, e il problema è più piccolo del previsto: la
finestra `Aule disponibili` dichiara **tre soli vincoli** rilassabili —
`Sedi distaccate`, `Indisponibilità opzionali`, `Indisponibilità`. Capienza,
categoria e tipologia dell'aula non sono vincoli. La seconda fase è quindi un
matching su disponibilità e sede, con capacità simultanea per aula. Vedi
[aule.md](aule.md).

## Un vincolo normativo italiano cablato nel motore

Fra le ~90 classi `TContrainte*` dell'eseguibile ce n'è **una sola
paese-specifica italiana**: `TContrainteItalieProfReglementaire`. Non è stata
trovata alcuna etichetta UI corrispondente.

**Cercato in UI il 2026-07-26, senza trovarlo.** Due posti battuti sulla base di
esempio italiana:

- il pannello completo `Indisponibilità e vincoli` di un docente: sette gruppi di
  vincoli, **tutti generici**, nessuno che nomini l'Italia o una norma;
- l'intero menu `Parametri` (28 voci su sei sezioni: ISTITUTO, GENERALI, OPZIONI,
  COMUNICAZIONE, PIAZZAMENTO, GESTIONE PER SETTIMANA): nessuna voce
  paese-specifica.

⚠ **Stato: probabile codice morto o vincolo cablato senza interfaccia.** Resta un
ultimo candidato non ispezionato, `Parametri → PIAZZAMENTO → Piazzamento
automatico delle attività`. Se nemmeno lì compare nulla, la conclusione operativa
è che **non esiste un vincolo normativo italiano da replicare**: qualunque limite
di legge sull'orario dei docenti va cercato nella normativa, non in EDT.

Nota a sostegno di questa lettura: la distribuzione italiana **non incorpora
nemmeno le classi di concorso** ([discipline.md](discipline.md)). La
localizzazione italiana di EDT è, dal punto di vista del dominio normativo,
piuttosto sottile.

## Cosa NON si ricava da qui

- I **parametri** dei vincoli (soglie di default, pesi): sono dati, non tipi.
- L'**algoritmo**: sappiamo le fasi e le euristiche per nome
  (`optHeuristiqueSolutionEchec`, `optIncNiveau1/2`), non cosa fanno.
- Se queste funzionalità siano tutte **attive nella distribuzione italiana**:
  `EDT Monoposto.distrib` contiene `PaysDistribution=ITALIE`, quindi esiste un
  filtro per paese che non è stato ispezionato.
