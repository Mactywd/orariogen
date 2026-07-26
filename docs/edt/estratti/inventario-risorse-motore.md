# Inventario piatto delle funzionalità — motore, risorse, aule, docenti, materie, moduli

> Estratto dalla documentazione del repo (nessuna ricerca nuova, nessuna apertura di EDT).
> Fonti: `docs/edt/motore-risoluzione.md`, `risorse.md`, `aule.md`, `docenti.md`,
> `materie.md`, `discipline.md`, `moduli-e-scope.md`; ADR da `docs/decisioni.md`.
>
> **Non contiene decisioni di scope.** Le colonne `Costo` e `Valore percepito` sono
> stime per orientare la scelta, non una scelta.
>
> Legenda costo: `banale` = giorni, nessun impatto sul modello del solver ·
> `medio` = nuova tabella + vincolo CP-SAT localizzato ·
> `strutturale` = cambia la forma del modello (variabili, decomposizione, pipeline).
>
> ⚠ nella riga = la documentazione stessa segnala incertezza.

---

## A — Il motore: comandi e pipeline

Riferimento: `motore-risoluzione.md`, Parte I e Parte II.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| A1 | **Lancia un piazzamento automatico** (`Ctrl+G`) | Piazza le attività da piazzare fra quelle estratte; il motore di base | motore §*Il piazzamento automatico* | strutturale | E1 | alto | — |
| A2 | **Piazzamento in quattro fasi dichiarate, con progresso dal vivo** | `Fase calcolo (n / 4)` + percentuale dentro la fase + ciambella dei conteggi per stato aggiornata mentre gira | motore §*Il calcolo osservato mentre gira* | medio | A1 | alto | — |
| A3 | **Calcolo interrompibile con conservazione del piazzato** | `Lancia il calcolo` diventa `Interrompi`; ciò che è già piazzato resta | motore §*Il calcolo osservato mentre gira* | medio | A1 | alto | — |
| A4 | **Interrompi al primo scarto** | Opzione: ferma il calcolo appena un'attività non si piazza | motore §*Le opzioni e i parametri* | banale | A1 | basso | — |
| A5 | **Piazza le attività scartate** (risolutore degli scarti) | Fase annidata nel piazzamento (☑ di default, **4 passate**), rilanciabile da sola con più controllo | motore §*Il risolutore delle attività scartate* | strutturale | A1 | alto | — |
| A6 | **Metodo `Standard` / `Avanzato` + 3 livelli di approfondimento** | Due modalità di risoluzione (= `cCalculResolRapide` / `cCalculResolIntegre`) e un livello di sforzo 1–3. *"Iniziate sempre con il metodo standard"* | motore §*Il risolutore delle attività scartate* | medio | A5 | medio | — |
| A7 | **Trova una collocazione** / **Cerca un'altra collocazione** | Due comandi distinti su una singola attività: *«dammi un posto»* e *«dammene un altro»* (il secondo attivo solo se già piazzata) | motore §*Il menu `Elabora`* | medio | A1 | alto | — |
| A8 | **Metti in attesa / Sospendi (`Dépositionner`)** | Togliere un'attività dall'orario senza cancellarla; materializza lo stato `In attesa` | motore §*Il menu `Elabora`* | banale | S1 | alto | — |
| A9 | **Blocca / Sblocca la collocazione** | L'attività è inchiodata dove sta; il motore non la muove né la ottimizza. Nella base demo: 8 bloccate su 984 | motore §*Il menu `Elabora`*, §*Su cosa agisce* | banale | A1 | alto | — |
| A10 | **Rendi prioritarie le attività** | Attributo di priorità dell'attività, **distinto dal blocco** — l'ordine con cui il motore le tratta | motore §*Il risolutore delle attività scartate*; `diagnostica.md` | medio | A1 | medio | — |
| A11 | **Estrai le attività non sufficientemente dettagliate per il piazzamento** | Controllo preventivo: quali attività non sono neppure candidabili (7 ragioni di non-omogeneità) | motore §*Perché un'attività non è piazzabile in blocco* | banale | E1 | alto | — |

## B — Le funzioni di prodotto del motore (le più preziose)

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| B1 | 🔑 **Lancia l'analisi dei vincoli** | Analisi di fattibilità **prima** di calcolare, in cinque fasi (una per risorsa: classi, docenti, aule, personale, materiali) | motore §*Il menu `Elabora`*; `risorse.md` §*Le risorse sono cinque*; `diagnostica.md` | strutturale | R1 | alto | — |
| B2 | 🔑 **Diagnosi nominata a quattro riquadri** | `Enunciato del problema` in italiano corrente · `Azioni che permettono di risolvere` · `Dettaglio` con l'aritmetica esplicita (*"Classe 1B, LETTERE, 6 attività, durata da piazzare 10h00, durata piazzabile 9h00 » 1h00 non potrà essere piazzata"*) · `Soluzione` con la riga di vincolo colpevole | `diagnostica.md`; CLAUDE.md changelog | medio | B1 | alto | — |
| B3 | 🔑 **Riparazione sul posto + `Rilancia la verifica`** | Tendine e griglia delle indisponibilità **modificabili dentro** il riquadro `Soluzione`, poi si riverifica senza cambiare finestra | `diagnostica.md`; motore (analisi) | medio | B1, B2 | alto | — |
| B4 | 🔑 **Controllo dell'insieme di attività non piazzabili** (fase 5) | Ricerca di **sottoinsiemi infattibili** — un violatore di Hall, non la singola attività bloccata. Osservato: 11 docenti + 1 classe + 1 aula, 33h di domanda contro 32h di finestra comune | `diagnostica.md`; CLAUDE.md changelog | strutturale | B1 | alto | — |
| B5 | 🔑 **`Estrai le materie, le risorse coinvolte e le attività`** | Riversa la diagnosi corrente nella selezione di lavoro, così il calcolo successivo agisce esattamente su quello | `diagnostica.md`; motore | banale | B1, E1 | alto | — |
| B6 | 🔑 **Risolutore passo-passo** (`Trova una soluzione al massimo in N step`) | Ricerca a **catena di espulsioni** esposta all'utente: griglia annotata (bianco = libera, grigio = comporta lo spostamento di almeno un'altra attività), profondità 1/2/3 | motore §*Il risolutore passo-passo* | strutturale | A1, A8 | alto | — |
| B7 | 🔑 **Costo della mossa dichiarato per nome** | Non «3 conflitti»: le tre lezioni con giorno, ora, materia, docente e classe. E le risorse in conflitto diventano rosse nel pannello risorse | motore §*Il costo è dichiarato per nome* | medio | B6 | alto | — |
| B8 | **Catena a coda di lavoro, reversibile** | Ogni step etichettato `[n° step]`, `Indietro` lo disfa, commit solo con `Conferma tutti gli step` | motore §*La catena, confermata* | strutturale | B6 | alto | — |
| B9 | **Layout a tre pannelli del risolutore** | Scheda attività (con il conto di tutte e cinque le risorse) · griglia astratta annotata · orario reale del docente, *"a titolo indicativo"* | motore §*Osservato in UI, end-to-end* | medio | B6 | medio | — |
| B10 | 🔑 **Colonna `S.P.`** (numero di fasce orarie possibili) | *«Numero di fasce orarie possibili per il piazzamento dell'attività nel rispetto di tutti i vincoli»* — il dominio residuo, ordinabile, ricalcolato contro lo stato corrente | motore §*`S.P.` e `Nr G.`* | banale | A1 | alto | — |
| B11 | **Colonna `Nr G.`** (numero di giorni possibili) | *«Numero di giorni possibili per l'attività nel rispetto di tutti i vincoli»* | motore §*`S.P.` e `Nr G.`* | banale | A1 | medio | — |
| B12 | 🔑 **`Piazza e sistema`** | *"Permette di spostare l'attività selezionata in una posizione potenzialmente già occupata. Se ciò comporta lo spostamento di altre attività, queste verranno automaticamente ricollocate"* | motore §*`Piazza e sistema`* | strutturale | A1 | alto | — |
| B13 | 🔑 **`Ignora i vincoli dell'attività selezionata`** | *"non saranno presi in considerazione nella ricerca di una collocazione e non verranno risolti"* — l'utente impone una collocazione illegale e chiede al motore di riparare il resto | motore §*`Piazza e sistema`* | medio | B12, S2 | alto | — |
| B14 | 🔑 **Un orario invalido è uno stato ammesso e interrogabile** | La base demo ha 984/984 piazzate e **21 attività (38h00) che violano i vincoli**; la violazione è persistita, non impedita | CLAUDE.md changelog; `diagnostica.md` | strutturale | — | alto | — |
| B15 | **`Estrai → Attività che non rispettano i vincoli`** | Interroga l'orario esistente contro le **dieci famiglie violabili** scelte in `Criteri di estrazione`. ⚠ fra le dieci **mancano `Massimo di ore` e `Peso didattico`** — da chiarire | `diagnostica.md`; CLAUDE.md changelog | medio | B14, E1 | alto | — |
| B16 | ⚠ **Riepilogo di fine analisi** — *assente in EDT* | La chiusura (`Verifica terminata` / `Rimangono delle incoerenze`) **non riepiloga nulla**: chi ha scorso dieci problemi non può rivederli. Debolezza annotata, da fare meglio | CLAUDE.md changelog; `diagnostica.md` | banale | B1, B2 | alto | — |

## C — La funzione obiettivo, l'ottimizzazione e i rilassamenti

Riferimento: `motore-risoluzione.md`, §*La funzione obiettivo, esposta*, §*L'ottimizzazione*, §*La strategia a due passate*.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| C1 | **Ottimizza gli orari dei docenti** / **... delle classi** | Due comandi distinti: EDT **non cerca mai un ottimo congiunto** (`ttoProfs` / `ttoClasses`) | motore §*L'ottimizzazione* | strutturale | A1 | alto | — |
| C2 | 🔑 **`Ordinamento dei criteri`** — priorità lessicografica | Due liste (`Criteri ignorati` / `Criteri considerati`) con `>>`, `<<`, `Tutto >`, `< Niente` **e frecce su/giù per riordinare**. 11 criteri; `Rispetta le preferenze` è ultimo | motore §*`Ordinamento dei criteri`* | strutturale | C1 | alto | — |
| C3 | **Gestione dei buchi** con asimmetria docenti/classi | `Lascia i buchi di 1/2 ora`; `Non conteggiare come buchi le ore libere prima o dopo la linea di fine mattinata` — **separatamente `per le classi` e `per i docenti`** | motore §*`Scelta della migliore collocazione`* | medio | C2 | alto | — |
| C4 | **Raggruppa le attività** | ◉ `All'inizio della giornata` / ○ `Dalla fine della mattinata` | motore §*`Scelta della migliore collocazione`* | banale | C2 | medio | — |
| C5 | **Equilibra le giornate occupate** | ☑ `Distribuisci le attività sulla settimana per i docenti e le classi` (variante `sul ciclo`) | motore §*`Scelta della migliore collocazione`* | medio | C2 | alto | — |
| C6 | **Incompatibilità di materia su 2 giorni** | `Considera come consecutivi 2 giorni separati da giorni non lavorativi (es: venerdì e lunedì)` | motore §*`Scelta della migliore collocazione`* | banale | — | medio | — |
| C7 | 🔑 **Massimi orari con quattro modalità di applicazione** | Non un numero ma numero + finestra + tolleranza: `per ciascuna settimana` · `per ogni ciclo` · `media sulle 2 settimane - scarto massimo 30 min` · `media sui 2 cicli`. Compaiono solo con attività quindicinali | motore §*`Attività quindicinale`* | strutturale | — | medio | — |
| C8 | **Tre criteri di ottimizzazione ordinati, per popolazione** | Tendine 1/2/3 con: `Nessuno` · `Durata totale dei buchi` · `1/2 giornate libere` · `Attività isolate` · `Equilibrio didattico` (= FR *Régularité des cours*, ⚠ traduzione IT fuorviante) | motore §*Tre criteri, ordinati per priorità* | medio | C1 | alto | — |
| C9 | 🔑 **Perdita di qualità tollerata** | `Perdita di qualità tollerata per le classi:` / `... per i docenti:` — parametro **del singolo lancio**, non politica d'istituto. Vincolo di **non-regressione con budget**, non un peso | motore §*La perdita di qualità tollerata* | medio | C1 | alto | — |
| C10 | **Ottimizzazione individuale** | Su una singola risorsa, con `Numero di ore di buco tollerate per questa risorsa` | motore §*La perdita di qualità tollerata* | medio | C1 | alto | — |
| C11 | 🔑 **`Alleggerimenti`** — rilassamento a quota | *"Sbloccate i vincoli da alleggerire e selezionateli per quantificare il margine di manovra concesso al calcolo"*. **Non esiste «spegni il vincolo»**: 11 famiglie, ciascuna con una quota per risorsa/settimana (variante per ciclo) | motore §*Quali vincoli EDT sa rilassare* | strutturale | A5 | alto | — |
| C12 | **Tetto globale degli alleggerimenti** | `Numero massimo di vincoli da alleggerire per risorsa:` | motore §*Quali vincoli EDT sa rilassare* | banale | C11 | medio | — |
| C13 | **`Dettaglia le materie per classe`** | L'alleggerimento delle incompatibilità può essere mirato materia per materia | motore §*Quali vincoli EDT sa rilassare* | banale | C11 | basso | — |
| C14 | **`Vincolo opzionale` sui vincoli fra attività** | Casella **spuntata di default**: *"può essere alleggerito durante il piazzamento delle attività scartate"* | motore §*Confermato in UI*; `vincoli.md` | medio | C11 | medio | — |
| C15 | **`Durata se possibile` / `Frequenza se possibile` / `Periodi se possibile`** | Degradabilità dichiarata **sulla singola attività**: il motore può accorciare o diradare pur di piazzare | motore §*Il menu `Elabora`* | medio | A1 | medio | — |
| C16 | 🔑 **Stabilità rispetto alla soluzione precedente** | *"Se possibile mantenendo le assegnazioni della precedente ripartizione"* (osservato sulle aule). ADR-010 lo richiede come criterio *«mantieni il più possibile le collocazioni del periodo precedente»* | motore §*L'assegnazione delle aule*; ADR-010 | medio | C1 | alto | **ADR-010: da implementare insieme alla rigenerazione** |
| C17 | **Nessuna funzione di costo numerica** (scelta architetturale) | I compromessi si governano su tre livelli — quote di violazione, criteri lessicografici, priorità con perdita tollerata. *"in EDT non esiste alcuna funzione di costo numerica"* | motore §*Chiuso: i «punti» non sono un punteggio* | strutturale | C2, C9, C11 | medio | — |

## D — Le cinque risorse di piazzamento

Riferimento: `risorse.md`.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| D1 | 🔑 **Cinque risorse sullo stesso piano** | Classi · docenti · **aule** · **personale** · **materiali**. Prova: la verifica di coerenza ha una fase per ciascuna; il risolutore declina le indisponibilità opzionali sulle stesse cinque | `risorse.md` §*Le risorse sono cinque* | strutturale | — | alto | — |
| D2 | **Il personale come risorsa piazzabile** | Stesso corredo delle altre: indisponibilità hard/opzionale, *"Il personale è già occupato in un'attività"*. Ruolo che conta: **Educatore** (assistente all'autonomia e comunicazione) | `risorse.md` §*Il personale* | medio | D1 | alto | — |
| D3 | **Attività di accompagnamento** | *"Volete anche aggiornare le attività di accompagnamento del personale interessato?"* — gli incarichi generano **attività schedulate**, non righe contabili | `risorse.md` §*Ha attività proprie* | medio | D2 | medio | — |
| D4 | **`Autorizza al personale l'inserimento di indisponibilità`** | La risorsa dichiara da sé le proprie indisponibilità (self-service), come i docenti | `risorse.md` §*Il personale* | banale | D2 | medio | — |
| D5 | 🔑 **Materiale con quantità = risorsa cumulativa** | *"Il materiale %s non può essere modificato poiché %d quantità di questo materiale sono utilizzate simultaneamente"*. L'attività ne chiede N; è un vincolo **hard**. Stesso meccanismo del `Qtà` dell'aula → **una sola risorsa cumulativa**, non due tabelle | `risorse.md` §*La quantità è un vincolo hard* | medio | D1, F2 | medio | — |
| D6 | **Regime di prenotazione** (`Prenotabile da`, `Limite/Soglia di prenotazione`) | Chi può prenotare (docenti/personale, per settimana o per ciclo) e con quanti giorni di preavviso. Vale per materiali **e** aule | `risorse.md` §*I materiali*; `aule.md` §*Altri campi* | medio | D5 | basso | — |
| D7 | **`Gestori`** — responsabile della risorsa | Docente o personale responsabile dell'aula/materiale, destinatario delle email. Valorizzato su tutte le 18 aule della base | `risorse.md`; `aule.md` | banale | — | basso | — |
| D8 | 🔑 **Gli incarichi incidono sul monte ore** | Formula letterale: **`Ore supplementari = Durata/Coeff. + Extra − Monte ore`**; variante `(H.att + H.pond + ACP + CC) − Monte ore` | `risorse.md` §*Gli incarichi del docente* | medio | G1, G10 | medio | — |
| D9 | **`Coefficiente`** (`Pondération`) dell'attività | Frazione di minuti (`60/60` osservato): conta un'ora di lezione come più o meno di un'ora di servizio. Entra in `Durata/Coeff.` | `moduli-e-scope.md` §*Le colonne della lista attività*; motore §*Il menu `Elabora`* | medio | D8 | basso | — |
| D10 | **`Picco d'occupazione`, `Tasso di occupazione` (TOP), `Rempliss. Max/Min/Moy`** | Indicatori calcolati di saturazione della risorsa | `risorse.md`; `aule.md`; `docenti.md` | banale | — | medio | — |
| D11 | **`Retard de service`** — permessi / arretrato di servizio | Debito/credito ore da recuperare del docente | `risorse.md` §*Colonne mai viste* | medio | G1 | basso | — |
| D12 | ⚠ **`ProfHeuresP1/P2/P3`** — priorità 1/2/3 del docente | Sistema di priorità numerato. ⚠ *"Molto probabilmente sono le priorità di sostituzione, non un parametro del piazzamento — da confermare"* | `risorse.md` §*Colonne mai viste* | medio | — | basso | — |
| D13 | **TRCD / TRMD** — bilancio `Dotazione − Bisogni = Scarto` | Su `Globale` / `Ore posto` / `HSA` / `IMP`, con i plafond del decreto **francese** 2014-940/941 | `risorse.md` §*TRCD/TRMD è fuori scope* | strutturale | — | basso | **dichiarato fuori scope** (`risorse.md`) |
| D14 | **IMP / PACTE** — indennità per missione particolare | Compenso monetario annuale, contabilità separata; **non entra nella formula oraria**. Origine: riforma francese 2023 | `risorse.md` §*L'IMP invece no* | medio | — | basso | **fuori scope** (`risorse.md`) |
| D15 | **Alunni e responsabili fuori dal piazzamento** | Non compaiono in nessuna fase di verifica della coerenza: non sono risorse dell'orario | `risorse.md` §*Alunni e responsabili* | — | — | — | già escluso (`classi.md`) |

## E — `Estrai`: la selezione di lavoro e i rilevatori di problemi

Riferimento: `moduli-e-scope.md`, §*`Estrai` — la selezione di lavoro*.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| E1 | 🔑 **`Estrai`** — selezione persistente di lavoro | Non un filtro di vista: una selezione su cui **tutte** le azioni successive operano. Criteri combinabili su stato, collocazione, conformità, risorse, proprietà | `moduli-e-scope.md` §*`Estrai`* | strutturale | — | alto | proposta **DENTRO come pattern** (`moduli-e-scope.md`) |
| E2 | 🔑 **Il motore opera in esclusiva sull'estrazione** | *"%d attività da piazzare tra quelle estratte"*; **`Lancia il calcolo` è disabilitato** se l'estrazione non contiene nulla da piazzare. Il piazzamento incrementale con il resto congelato è **l'unica modalità** | motore §*Su cosa agisce*; `moduli-e-scope.md` | strutturale | E1, A1 | alto | — |
| E3 | **Composabilità cumulativa** | `Limita la ricerca alle attività già estratte` — si raffina progressivamente, come una query incrementale con stato | `moduli-e-scope.md` §*Composabilità* | banale | E1 | medio | — |
| E4 | 🔑 **Estrazioni salvate, nominabili, ricombinabili** | `Memorizza le attività estratte` · `Richiama un elenco` · `Aggiungi l'estrazione` · `Togli l'estrazione` — unione e differenza fra insiemi salvati | `moduli-e-scope.md` §*Il menu `Estrai`* | medio | E1 | medio | — |
| E5 | **Operazioni insiemistiche sull'estrazione** | `Definisci un'estrazione` (`Ctrl+E`), `Estrai tutto`, `Estrai la selezione`, `Aggiungi`, `Togli la selezione`, `Estrai le risorse delle attività selezionate` (`Ctrl+U`), `Estrai le attività previste per le classi e i raggruppamenti della selezione` | `moduli-e-scope.md` §*Il menu `Estrai`* | banale | E1 | alto | — |
| E6 | 🔑 **I dodici rilevatori di problemi** (famiglia) | Controlli di qualità preconfezionati sull'orario esistente. *"Ognuna è una query sul modello, non una funzione del solver. Costano poco e valgono molto"* | `moduli-e-scope.md` §*I rilevatori di problemi* | medio | E1 | alto | — |
| E7 | `Estrai le attività non conformi ai piani di studi` | Scostamento dal quadro orario | `moduli-e-scope.md` §*I rilevatori* | banale | E6 | alto | — |
| E8 | `Estrai le attività con problemi di aule` / `di sede` | Due rilevatori distinti | `moduli-e-scope.md` §*I rilevatori* | banale | E6, F1 | alto | — |
| E9 | `Estrai le attività a cavallo dell'intervallo` | Violano `Rispetta gli intervalli` | `moduli-e-scope.md` §*I rilevatori* | banale | E6 | medio | — |
| E10 | `Estrai le attività non costanti durante l'anno` / `spostate` / `sezionate asincrone` | Cambiano fra periodi; divergono dall'orario annuale (gli `Amenagement`); parti scoordinate | `moduli-e-scope.md` §*I rilevatori* | banale | E6 | medio | parz. **ADR-010** (niente fascia variabile) |
| E11 | `Estrai le attività complesse` / `di compresenza` / `con almeno un incarico` / `con raggruppamenti ad alunni variabili` | Rilevatori per tipologia | `moduli-e-scope.md` §*I rilevatori* | banale | E6 | medio | — |
| E12 | `Estrai le attività non sufficientemente dettagliate per la stampa` | Come A11 ma per l'output stampato | `moduli-e-scope.md` §*I rilevatori* | banale | E6 | basso | — |

## F — Aule

Riferimento: `aule.md`.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| F1 | 🔑 **L'assegnazione delle aule è un problema separato** | Non fa parte del piazzamento: ottimizzatore dedicato (`FicheEdt_OptimiseurSalles`), criteri propri, `ripartizione delle aule`. Farlo in due fasi è *"una semplificazione legittima, validata da un prodotto maturo"* | motore §*L'assegnazione delle aule*; `aule.md` | strutturale | A1 | alto | — |
| F2 | 🔑 **`Numero di aule` (`Qtà`) — capienza simultanea** | Campo **scalare** sull'aula: quante attività può ospitare in parallelo. `PALESTRE succ` ha `Qtà = 2` e **zero** sotto-aule. Verificato: 34 collisioni su 97 slot in una base che EDT considera risolta | `aule.md` §*L'occupazione simultanea è un campo dell'aula* | medio | F1 | alto | — |
| F3 | 🔑 **L'aula è un'eccezione dichiarata, non una colonna obbligatoria** | Su 27 attività di una classe intera, **una sola ha un'aula**. Il resto vive nell'`Aula preferenziale` della classe | `risorse.md` §*L'aula è l'eccezione*; `aule.md` | medio | F1 | alto | — |
| F4 | **`Aula preferenziale` sulla classe** | Il legame aula↔didattica passa dalla **classe**, non dalla materia | `aule.md` §*Ma la classe ha un'aula preferenziale* | banale | F1 | alto | — |
| F5 | **I tre soli vincoli sull'assegnazione dell'aula** | `Sedi distaccate` · `Indisponibilità opzionali` · `Indisponibilità`. **Capienza, categoria e tipologia non sono vincoli** | `aule.md` §*Cosa vincola davvero* | medio | F1 | alto | — |
| F6 | **Colonna `Diagnostica` nella finestra `Aule disponibili`** | Dice aula per aula *perché* non va bene, con marcatori colorati (rosa = sede, giallo = indisp. opzionale, arancione = indisponibile) + la frazione `1 / 2` di occupazione sullo slot | `aule.md` §*Cosa vincola davvero* | banale | F1, F2 | alto | — |
| F7 | **Sotto-aule** (gerarchia padre/figlio) con cascata di default | Danno **identità e nome** ai singoli spazi (`PALESTRE` → `Palestra 1`, `Palestra 2`); campi ereditati marcati `(Gr.)`; l'occupazione si contabilizza **sul padre** | `aule.md` §*Le sotto-aule* | medio | F2 | basso | ADR-003 (cascata) |
| F8 | **Sedi (`Site`) e cambi di sede** | Sede di appartenenza dell'aula, filtro `Solo le aule della stessa sede dell'attività`, alleggerimento `Cambi di sede` a quota | `aule.md`; motore §*Alleggerimenti* | medio | F1 | medio | — |
| F9 | **`Tipologie`** — tag di dotazione a due livelli | Albero `categoria → tipologia` definito dall'utente (`Attrezzature → PC docente, Videoproiettore`), molti-a-molti, **puramente descrittivo**: raggruppa la lista per chi sceglie a mano | `aule.md` §*Le tipologie* | banale | F1 | basso | — |
| F10 | **`Categoria dei locali scolastici`** | Attributo delle aule foglia (`AULA DI INSEGNAMENTO GENERALE`, `CDI`). Descrittivo | `aule.md` | banale | F1 | basso | — |
| F11 | **`Cap.`** — capienza dell'aula | Tetto di alunni. In EDT **descrittiva**: non è un vincolo, e nella base di esempio non è nemmeno compilata (vuota su tutte e 18) | `aule.md` §*Semantica* | banale | F1 | basso | — |
| F12 | ⚠ **Materia → dotazione/tipo d'aula richiesta** — *nostra estensione* | *"Non esiste nulla di simile a «questa materia richiede un laboratorio»"*. Confrontare `Cap.` con `Al./Rid.` sarebbe anch'essa nostra estensione | `aule.md` §*Semantica*, §*Implicazioni* | medio | F1, H3 | alto | — |

## G — Docenti

Riferimento: `docenti.md`.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| G1 | **`Mh/s`** — monte ore settimanale | *"Monte ore settimanale, numero ore dovute dal docente, ore extra comprese"* (= FR `Apport`). **Non è un massimo**: è il dovuto contrattuale | `docenti.md` §*Campi osservati*, §*Il docente nello schema* | banale | — | alto | — |
| G2 | **Monte ore scomposto per disciplina** | Nello schema di scambio un `Apport` per disciplina, in minuti; `Mh/s` in UI ne è la somma. *"Il nostro modello dovrebbe tenere la scomposizione"* | `docenti.md` §*Il docente nello schema* | medio | G1 | medio | — |
| G3 | 🔑 **`Materie insegnabili`** — la capacità | M2M docente↔materia: cosa **può** insegnare. È la capacità, non l'assegnazione, a decidere **chi può sostituire chi** | `docenti.md` §*Tre nozioni di "materia"* | banale | — | alto | **ADR-006** |
| G4 | **`Materia preferenziale`** | Fra le insegnabili, quella da preferire in assegnazione. Se non è fra le insegnabili, **EDT la aggiunge da sé** invece di rifiutare | `docenti.md` §*Tre nozioni*, §*Osservazioni* | banale | G3 | medio | ADR-006 |
| G5 | **`Salle de préférence`** — aula di preferenza del docente | Stesso pattern preferenza/assegnazione applicato all'aula | `docenti.md` §*Il docente nello schema* | banale | F1 | basso | — |
| G6 | **Campi previsionali calcolati** (`Occ. prev.`, `HS Prev.`, `+/-`, `Extra`) | Dashboard di bilanciamento carichi: `+/- = Mh/s − Occ. prev.`. **Non sono input**, si ricalcolano | `docenti.md` §*Campi calcolati* | banale | G1 | alto | **ADR-007** (non memorizzare) |
| G7 | **`HSMax`** — tetto delle ore supplementari | Default osservato `1h00`; probabile altro livello di cascata | `docenti.md` §*Monte ore, statuto* | banale | G1 | medio | — |
| G8 | ⚠ **`Statuto`** (Titolare / Supplente / Provvisorio) | Stato contrattuale. ⚠ **Ipotesi non confermata**: che guidi il default di `Mh/s` — sarebbe un livello di cascata. ⚠ Collisione: in un'altra griglia `Statuto` traduce `Affectation` = assegnazione | `docenti.md` §*Monte ore*, §*Ambiguità su `Statuto`* | banale | G1 | basso | — |
| G9 | **`Disciplina` del docente → classe di concorso** | FK singola. Nella base italiana il `Codice` della disciplina **è** la classe di concorso (`A-01`, `A-22`…). ⚠ EDT non incorpora la tabella ministeriale né valida nulla | `discipline.md` §*Il `Codice` porta la classe di concorso* | medio | H1 | alto | **ADR-002** (tabella di mappatura M2M a sé) |
| G10 | **Incarichi** — tabella catalogabile | `Codice`, `Nome corto`, `Nome lungo`, `Impegno` (`non definito` / `definito` con durata / `tutto l'anno`), assegnabile al docente | `docenti.md` §*Incarichi* | medio | — | medio | — |
| G11 | **`D.T.B.`** — durata tollerata dei buchi per docente | Default osservato `2h00` per tutti; combacia col default «ore di buco tollerate = 2» dei vincoli. Candidato cascata | `docenti.md` §*L'elenco Docenti in ambiente Orario* | banale | C8 | alto | — |
| G12 | **`G. Mensa`** — giorni di turno mensa del docente | *"i giorni che richiedono la gestione della mensa per risorsa"*. Attributo di giorno, non di ora. Default `Tutti` | `docenti.md` §*G. Mensa* | banale | — | basso | proposto fuori v1 (`docenti.md`) |
| G13 | **`Abbr.`** — nome abbreviato ≤ 5 caratteri | Sigla per la griglia stampata | `docenti.md` §*Campi osservati* | banale | — | medio | — |
| G14 | **Spezzone di cattedra** → giorni di indisponibilità | Sotto le 18h il docente è in servizio anche altrove, e porta indisponibilità su questa scuola | `docenti.md` §*Spezzoni* | banale | G1 | alto | — |
| G15 | **Le durate sono `h:mm`, non interi** | `20h00`, non `20` → nel nostro schema le ore vanno in **minuti** (o `DurationField`) | `docenti.md` §*Osservazioni dall'inserimento* | banale | — | alto | — |

## H — Materie e discipline

Riferimento: `materie.md`, `discipline.md`.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| H1 | **`Disciplina` come tabella, non enum** | Raggruppamento di materie affini, personalizzato dalla scuola. `Matiere → Discipline` è `0..1`: una materia **può non avere disciplina** | `discipline.md`; `materie.md` §*Schema di scambio* | banale | — | alto | **ADR-001** |
| H2 | **Mappatura disciplina → classe di concorso** | Molti-a-molti in tabella a sé (Lettere → A-11/A-12/A-13); il `Codice` EDT è la sorgente di import quando è valorizzato | `discipline.md` §*Implicazioni* | medio | H1 | alto | **ADR-002** |
| H3 | **`Al./Rid.`** — numero ridotto di alunni | *"Numero ridotto di alunni della materia"*, default 15. È un **tetto massimo nullable**, non un flag né un effettivo | `materie.md` §*Cosa NON è* | banale | — | medio | **ADR-005** |
| H4 | 🔑 **Cascata di default globale → entità → istanza** | `impostazione globale (30 / 15) → campo della materia → corso concreto`. `NULL` = «eredita». Confermata trasversale (materie, aule, docenti) | `materie.md` §*La cascata di default*; `aule.md` §*Le sotto-aule* | strutturale | — | medio | **ADR-003** |
| H5 | **Peso didattico delle materie** | Peso intero per materia + tetti su mezza giornata / giornata / settimana / ciclo; alleggerimento a quota (`Autorizza un supplemento di … punti, un giorno per settimana`). ⚠ **scala dei pesi e default ancora ignoti** | motore §*Quali vincoli EDT sa rilassare*; `vincoli.md` | medio | C11 | alto | **ADR-011: dentro v1** |
| H6 | **`@Couleur`** — colore di materia, classe, gruppo, sede | RGB esadecimale, attributo di prima classe. Serve alla resa a griglia | `materie.md` §*Schema di scambio* | banale | — | medio | — |
| H7 | **`CodeSIDI`** come codice materia interoperabile | Nomenclatura ministeriale italiana incorporata in EDT (4364 voci) | `materie.md` §*Codice esterno*; `nomenclatura-sidi.md` | banale | — | medio | — |
| H8 | **`@ID_Partenaire`** — identificativo esterno | Il campo dove agganciare il codice del gestionale chiamante | `materie.md` §*Schema di scambio* | banale | — | alto | — |
| H9 | ⚠ **Spazi di codici separati per materie e discipline** | `MOT` esiste come codice di entrambe. Uno spazio unico richiederebbe un prefisso di disambiguazione | `discipline.md` §*Collisione di codici* | banale | H1 | basso | — |

## I — Altri moduli, import/export, confine con PRONOTE

Riferimento: `moduli-e-scope.md`. ⚠ Le voci marcate **PRONOTE** non sono funzionalità di EDT e non sono censite come implementabili: compaiono solo per tracciare il confine.

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| I1 | 🔑 **Export iCal** | In tre punti indipendenti (orario, colloqui, consigli). *"utile in uscita, costo basso"* — i docenti vogliono il proprio orario nel telefono | `moduli-e-scope.md` §*Importazioni ed esportazioni* | banale | — | alto | proposta **DENTRO** (`moduli-e-scope.md`) |
| I2 | **`Esportazione ASCII`** (tabellare/CSV) | Export di servizio con opzioni granulari | `moduli-e-scope.md` §*Importazioni* | banale | — | medio | — |
| I3 | **Import `Partenaire_Index`** | XSD ufficiale V4.6, `Esportazione standard partner`. Trasporta **solo la struttura**: nessun vincolo, nessun piazzamento | `moduli-e-scope.md`; `schema-scambio.md` | strutturale | — | medio | **ADR-012: NON lo adottiamo** |
| I4 | **`Importazione degli orari`** EDT → EDT | Proprietario, con opzioni di merge (`sostituisci` / `aggiungi` / priorità in caso di conflitto) | `moduli-e-scope.md` §*Importazioni* | medio | — | basso | valore *"nullo senza EDT"* |
| I5 | **`Orario della settimana` / `Orario per ciclo`** | Vista operativa che **deriva** dall'orario annuale ma può divergere; ogni settimana **ripristinabile**; `Blocca automaticamente le settimane trascorse` | `moduli-e-scope.md` §*Due griglie sovrapposte* | strutturale | — | alto | **ADR-014** (una sola entità con maschera temporale) |
| I6 | **Filtro multi-criterio per il sostituto** | 7 criteri: `Disponibili per tutta la durata` · `Della stessa materia` · `Dello stesso livello` · `Dello stesso consiglio di classe` · sede · `Solo docenti con ore residue d'incarico` · `Ignora i vincoli`. **Nessun solver**: filtro + workflow + assegnazione manuale | `moduli-e-scope.md` §*Come EDT sceglie un sostituto* | medio | — | alto | proposta **FUORI** (già nel SaaS del committente) |
| I7 | 🔑 **`Sostituti liberi che hanno un buco`** / **`liberati da un'assenza della classe`** | I due criteri di reclutamento non ovvi — *"utile come nota per l'altro prodotto"* | `moduli-e-scope.md` §*Come EDT sceglie un sostituto* | banale | I6 | alto | fuori (nota per il SaaS) |
| I8 | **Priorità di sostituzione a 3 livelli, docente × fascia** | Griglia strutturalmente identica a quella delle indisponibilità (terzo riuso del pattern rosso/giallo/verde) | `moduli-e-scope.md`; cfr. D12 | medio | I6 | medio | fuori |
| I9 | **Sostituzione puntuale vs. sostituzione lunga** | Sotto una soglia configurabile di giorni è puntuale; sopra genera un **binario parallelo di attività** per il sostituto | `moduli-e-scope.md` §*Come EDT sceglie un sostituto* | medio | I5 | medio | ADR-014 (testata che raggruppa) |
| I10 | **Colloqui genitori/docenti** | Vero problema di scheduling con risolutore dedicato: desiderata a semaforo, priorità `prioritario`/`desiderato`/`facoltativo`, durata con min/max | `moduli-e-scope.md` §*Colloqui* | strutturale | — | medio | proposta **FUORI da v1** |
| I11 | **Consigli di classe** | Motore a tre stadi identico all'orario; obiettivo: minimizzare le sovrapposizioni fra consigli | `moduli-e-scope.md` §*Consigli di classe* | strutturale | — | basso | proposta **FUORI** |
| I12 | **RCD** (*Remplacement de Courte Durée*) | Tassonomia chi-sorveglia × cosa-fa per statistiche ministeriali **francesi**. Nessun equivalente italiano | `moduli-e-scope.md` §*RCD* | medio | I6 | basso | **fuori** (adempimento francese) |
| I13 | **Comunicazioni** (email, telefono, SMS) | Infrastruttura anagrafica di **PRONOTE**. Nessun contenuto di scheduling | `moduli-e-scope.md` §*Comunicazioni* | — | — | — | proposta **FUORI** |
| I14 | **Export ministeriali italiani** (SIDI, INVALSI, Scrutini, Esami di Stato) | Flussi verso il MIM che riguardano il **registro elettronico**, non l'orario → PRONOTE | `moduli-e-scope.md` §*Importazioni* | — | — | — | fuori (non è EDT) |
| I15 | 🔑 **Il pattern a tre stadi come architettura** | `piazza → risolvi gli scarti → ottimizza`, confermato su **due domini indipendenti** (orario e consigli): è il pattern architetturale del prodotto, non una scelta dell'orario | `moduli-e-scope.md` §*Consigli di classe*, §*Riepilogo* | strutturale | A1, A5, C1 | — | — |

## L — Attività complesse, allineamenti, tempo (voci di confine incontrate nei miei documenti)

| # | Nome (EDT, IT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso |
|---|---|---|---|---|---|---|---|
| L1 | **`Allinea le attività selezionate...`** | Costruzione dell'attività complessa dalla lista | motore §*Il menu `Elabora`* | strutturale | — | alto | **ADR-013** (sdoppiamenti dentro v1) |
| L2 | **Validazione dell'allineamento — 11 modi di fallire** | `JoursIncompatibles`, `EtatsIncompatibles`, `FrequencesIncompatibles`, `CalendriersIncompatibles`, `ProfesseurManquant`, `Superposition`, `CoursFilsUnique`, `EnveloppeTropPetite`, `RecreationsIncompatibles`, `CoursAvecContrainteCaC`, `ErreurInattendue`. *"È già la specifica di validazione da implementare"* | motore §*Validazione dell'allineamento* | medio | L1 | alto | ADR-013 (*"va riusata"*) |
| L3 | **`Trasforma le attività selezionate...`** | Riscrittura in blocco di durata e frequenza | motore §*Il menu `Elabora`* | banale | E1 | medio | — |
| L4 | **`Fascia fissa` / `Fascia fissa (ciclo)` / `Fascia variabile`** | *"EDT può modificare la collocazione dell'attività a seconda dei periodi"* — una collocazione **per periodo**, non una sola. Colonna `P.P.`, badge `F` di default | motore §*Fascia fissa e fascia variabile*; `moduli-e-scope.md` §*Le colonne* | strutturale | — | medio | **ADR-010: NON la implementiamo** (si rigenera) |
| L5 | **`Periodicità`** (`Alternance`) — quindicinali, settimane Q1/Q2 | Modello **numeratore/denominatore**: `Periodicità = 42` su tutte le attività della base = 42 settimane su 42 | motore §*Il menu `Elabora`*; `moduli-e-scope.md` §*Due valori istruttivi* | strutturale | — | medio | — |
| L6 | **Famiglie di vincoli attivabili in blocco** | Indicatori di stato: `Intervalli attivi/inattivi` · `Mensa attiva/non attiva` · `Sedi distanti attive/non attive`. E, nel risolutore, `Ignora gli intervalli` | motore §*Cosa mostra durante il calcolo*, §*Il risolutore degli scarti* | banale | A1 | medio | — |
| L7 | **`Piazza le attività anche sulle fasce con indisponibilità opzionali`**, per risorsa | Declinato su tutte e cinque: `dei docenti` · `delle classi` · `delle aule` · `dei materiali` · `del personale` | motore §*Il risolutore delle attività scartate* | medio | C11, D1 | medio | — |
| L8 | **`Includi le attività senza collocazione`** | Opzione del risolutore degli scarti | motore §*Il risolutore delle attività scartate* | banale | A5 | basso | — |
| L9 | **Salvataggio automatico ogni mezz'ora** | *"Il file viene salvato automaticamente ogni mezz'ora"* — rivelatore del costo del calcolo | motore §*Il risolutore delle attività scartate* | banale | — | medio | — |
| L10 | **Modalità `Utilizzo esclusivo` durante il calcolo** | La base si blocca in scrittura mentre il motore gira | `moduli-e-scope.md` §*Colloqui* | medio | A1 | medio | — |
| L11 | **I quattro stati dell'attività** (`Piazzate` · `Non piazzate` · `Scartate` · `In attesa`) + `Bloccate` / `Fisse` / `Variabili` | Categorie di `Type_EtatCours`, usate come assi di estrazione **e** come categorie del grafico ad anello. `Bloccate` e `Piazzate` sono **disgiunti** (8 + 976 = 984) | motore §*Su cosa agisce*; `moduli-e-scope.md` §*Estrai* | medio | — | alto | — |
| L12 | ⚠ **`TContrainteItalieProfReglementaire`** — vincolo normativo italiano | **Non esiste alcuna interfaccia**: tre ricerche indipendenti negative. *"Non esiste un vincolo normativo italiano da replicare"* | motore §*Parte III* | — | — | — | **chiuso: non c'è nulla da fare** |

---

# Conteggio e ripartizione

**134 voci** su 10 sezioni.

| Sezione | Voci |
|---|---|
| A — motore: comandi e pipeline | 11 |
| B — funzioni di prodotto del motore | 16 |
| C — obiettivo, ottimizzazione, rilassamenti | 17 |
| D — le cinque risorse | 15 |
| E — `Estrai` e rilevatori | 12 |
| F — aule | 12 |
| G — docenti | 15 |
| H — materie e discipline | 9 |
| I — altri moduli, import/export, confine PRONOTE | 15 |
| L — attività complesse, allineamenti, tempo | 12 |

| Costo | Voci |
|---|---|
| `banale` | **53** |
| `medio` | **50** |
| `strutturale` | **27** |
| n/a (già escluso o inesistente: D15, I13, I14, L12) | 4 |

## Le 27 voci `strutturale`

| # | Nome |
|---|---|
| A1 | Lancia un piazzamento automatico |
| A5 | Piazza le attività scartate (4 fasi annidate) |
| B1 | Lancia l'analisi dei vincoli |
| B4 | Controllo dell'insieme di attività non piazzabili (violatore di Hall) |
| B6 | Risolutore passo-passo (catena di espulsioni) |
| B8 | Catena a coda di lavoro, reversibile |
| B12 | `Piazza e sistema` |
| B14 | Un orario invalido è uno stato ammesso e interrogabile |
| C1 | Ottimizza docenti **o** classi, mai insieme |
| C2 | `Ordinamento dei criteri` — priorità lessicografica |
| C7 | Massimi orari con quattro modalità di applicazione |
| C11 | `Alleggerimenti` — rilassamento a quota |
| C17 | Nessuna funzione di costo numerica (scelta architetturale) |
| D1 | Cinque risorse di piazzamento sullo stesso piano |
| D13 | TRCD/TRMD *(già dichiarato fuori scope)* |
| E1 | `Estrai` — selezione persistente di lavoro |
| E2 | Il motore opera in esclusiva sull'estrazione |
| F1 | L'assegnazione delle aule è un problema separato |
| H4 | Cascata di default globale → entità → istanza *(ADR-003)* |
| I3 | Import `Partenaire_Index` *(ADR-012: escluso)* |
| I5 | Orario della settimana / per ciclo *(ADR-014)* |
| I10 | Colloqui genitori/docenti *(proposto fuori v1)* |
| I11 | Consigli di classe *(proposto fuori)* |
| I15 | Il pattern a tre stadi come architettura |
| L1 | `Allinea le attività selezionate` — attività complessa *(ADR-013)* |
| L4 | Fascia fissa / variabile *(ADR-010: escluso)* |
| L5 | Periodicità (quindicinali, Q1/Q2) |

## Le 21 voci `alto valore` × `costo banale`

Sono il gruppo con il rapporto migliore. Sette riguardano il motore, cinque i dati
del docente, quattro `Estrai`/aule.

| # | Nome | Perché costa poco |
|---|---|---|
| A8 | Metti in attesa / Sospendi | uno stato in più sull'attività |
| A9 | Blocca / Sblocca la collocazione | una variabile fissata |
| A11 | Estrai le attività non sufficientemente dettagliate per il piazzamento | validazione sui dati, prima del solver |
| B5 | `Estrai le materie, le risorse coinvolte e le attività` | scrive una selezione già calcolata |
| B10 | **Colonna `S.P.`** (fasce orarie possibili) | *"è esattamente ciò che il solver calcola comunque durante la propagazione"* |
| B16 | Riepilogo di fine analisi (assente in EDT) | accumulare i problemi già emessi |
| E5 | Operazioni insiemistiche sull'estrazione | operazioni su insiemi di id |
| E7 | Estrai le attività non conformi ai piani di studi | query, non solver |
| E8 | Estrai le attività con problemi di aule / di sede | query, non solver |
| F4 | `Aula preferenziale` sulla classe | una FK |
| F6 | Colonna `Diagnostica` in `Aule disponibili` | riuso del controllo di disponibilità |
| G1 | `Mh/s` — monte ore settimanale | un campo |
| G3 | `Materie insegnabili` (capacità) — ADR-006 | una M2M |
| G6 | Campi previsionali calcolati — ADR-007 | proprietà derivate, non colonne |
| G11 | `D.T.B.` — durata tollerata dei buchi per docente | un intero per risorsa |
| G14 | Spezzone → giorni di indisponibilità | dato già presente nella cattedra |
| G15 | Durate in `h:mm` → minuti nello schema | scelta di tipo di colonna |
| H1 | Disciplina come tabella — ADR-001 | una tabella |
| H8 | `@ID_Partenaire` — identificativo esterno | una colonna indicizzata |
| I1 | Export iCal | una libreria |
| I7 | Criteri «chi ha già un buco lì» / «liberato da un'assenza di classe» | ⚠ valore alto per il **SaaS sostituzioni**, non per il generatore |
