# Inventario piatto delle funzionalità — struttura, tempo, attività, gruppi

Estratto da `docs/edt/tempo-e-calendario.md`, `attivita.md`, `gruppi.md`,
`piani-di-studi.md`, `classi.md`. Nessuna ricerca nuova: solo censimento.

**Legenda costo.** `banale` = un campo o un vincolo lineare. `medio` = una tabella
in più e/o una famiglia di vincoli. `strutturale` = cambia la forma del modello
(la variabile di decisione, l'unità di piazzamento, la decomposizione del
problema), non aggiunge solo un vincolo.

**Legenda `Già deciso`.** Riferimento agli ADR di `docs/decisioni.md`; vuoto = da
decidere.

**Legenda `⚠`.** La documentazione è marcata incerta, mai osservata in UI, o
esplicitamente contraddittoria. Incide sul rischio.

---

## A — Il tempo e la griglia

| ID | Nome (EDT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| T1 | **Griglia oraria** (giorni × fasce) | `NombreJoursParCycle × NombreSequencesParJour`: la matrice di collocazioni; *"10 fasce orarie da 60 minuti corrispondono a una giornata compresa tra le 8.00 e le 18.00"* | tempo-e-calendario.md § *La griglia: giorni × fasce × posizioni* | banale | — | alto | — | ⚠ *"La configurazione oraria non è mai stata osservata in UI"* |
| T2 | **Ciclo ≠ settimana** | Il ciclo di ripetizione può eccedere 5 o 7 giorni; la settimana di calendario e la posizione nel ciclo sono due assi separati | tempo-e-calendario.md § *La griglia* | strutturale | T1 | basso | — | ⚠ nessuna base osservata con ciclo ≠ settimana |
| T3 | **Suddivisioni sub-orarie** (`NombrePlacesParSequence`) | Divide la fascia in 2/3/4/6/12 parti: *"Una suddivisione in 2 crea 2 frazioni orarie da 30 min."*, per attività da 30 min, 1h30, 2h30 | tempo-e-calendario.md § *Le suddivisioni sub-orarie* | strutturale | T1 | basso | — | il prodotto stesso la sconsiglia: *"rende più complesso il calcolo dell'orario"* |
| T4 | **Etichette orarie personalizzate** | Durata effettiva ≠ fascia di calcolo (*"ad esempio 55 minuti"*), con validazione di coerenza cronologica | tempo-e-calendario.md § *Due nozioni di «ora»* | banale | T1 | medio | — | ⚠ cambiare la durata di fascia **ricalcola i monte ore**: non è cosmetico |
| T5 | **Intervalli** (*récréations*) | Confine fra due ranghi, **non** una collocazione: 2 soli record, l'attività sta «a cavallo» dell'intervallo | tempo-e-calendario.md § *Gli intervalli* | banale | T1 | medio | — | chiuso sui dati (ranghi 2 e 4 fra i più occupati) |
| T6 | **`Rispetta gli intervalli`** (flag sull'attività) | L'attività multi-ora non può essere spezzata a cavallo di una pausa; hard, con eccezione per classe (`NONRESPECTCLASSERECREATION`) | tempo-e-calendario.md § *Gli intervalli* | medio | T5, A3 | medio | — | — |
| T7 | **Linea di mezza giornata** | `Giornata continua` **oppure** `Giornata con una pausa delimitata da` fine mattinata + inizio pomeriggio; definita **in numero di fasce**, non in orario | tempo-e-calendario.md § *La linea di mezza giornata* | banale | T1 | alto | — | — |
| T8 | **Mezza giornata come unità di vincolo** | Rende esprimibili `Massimo di mezze giornate di lavoro`, `mezze giornate libere garantite`, `Lavorare solo mezza giornata al giorno`, su docenti **e** classi | tempo-e-calendario.md § *La linea di mezza giornata*; classi.md § *Campi osservati* | medio | T7 | alto | — | *"è un asse del modello"*, non presentazione |
| T9 | **Mensa** (*demi-pension*) | Fascia di sistema che blocca il piazzamento; elencata fra i vincoli ignorabili insieme a indisponibilità e sedi; stato `Mensa attiva`/`non attiva` nel piazzamento automatico | tempo-e-calendario.md § *La mensa è un vincolo hard* | medio | T7 | basso | — | il doc la dà «candidato ragionevole a fuori scope v1, ma va dichiarato» |
| T10 | **Anno scolastico** (`DateDebut`/`DateFin`/`DatePremierJourSemaine1`) | Ancora il ciclo al calendario reale: da lì si srotolano le settimane numerate | tempo-e-calendario.md § *Il calendario* | banale | T1 | alto | — | — |
| T11 | **Festivi e vacanze** | Si marcano su calendario (anche `Calcola i giorni festivi`); le attività già piazzate lì vengono spostate, con *"Conserva le attività spostate o riportate su dei giorni lavorativi"* | tempo-e-calendario.md § *Il calendario* | medio | T10 | medio | — | — |
| T12 | **Blocco per settimana/ciclo** (`P.Bloc.`) | *"Solamente le vacanze e i giorni festivi al di fuori dei cicli bloccati possono essere modificati"* | tempo-e-calendario.md § *Il calendario*; § *I periodi* | banale | T10, T13 | basso | — | — |
| T13 | **Periodi / suddivisioni dell'anno** (*decoupage*) | Partizione dell'anno (l'anno intero è il caso degenere); **più suddivisioni coesistono** (trimestri *e* quadrimestri), una di default | tempo-e-calendario.md § *I periodi* | strutturale | T10 | alto | — | — |
| T14 | **Fusione / dissociazione di periodi** | Unisce o separa periodi contigui, con vincolo: *"Per riunire dei periodi, è necessario che le loro attività siano identiche"* | tempo-e-calendario.md § *I periodi* | medio | T13 | basso | — | — |
| T15 | **Attività su un sottoinsieme di periodi** (`PeriodeDuCours`) | Una lezione può non essere annuale: *"dovete rendere annuali le attività che avete definito su una parte di questa suddivisione"* | tempo-e-calendario.md § *I periodi* | medio | T13, A1 | alto | — | — |
| T16 | **`Fascia fissa` / `Fascia variabile`** | *"EDT può modificare la collocazione dell'attività a seconda dei periodi"*: la variabile del solver diventa `slot[attività, periodo]` | tempo-e-calendario.md § *Fascia fissa / fascia variabile* | strutturale | T13, T15 | medio | **ADR-010: fuori** (si rigenera a ogni periodo) | — |
| T17 | **Criterio «mantieni le collocazioni precedenti»** | Non è EDT-nativo sull'orario ma è la conseguenza obbligata di ADR-010; EDT ha l'analogo sulle aule: *"Se possibile mantenendo le assegnazioni della precedente ripartizione"* | ADR-010 (da tempo-e-calendario.md § *Fascia variabile*) | medio | T13 | alto | **ADR-010: dentro**, *"da implementare insieme alla rigenerazione, non dopo"* | — |
| T18 | **Periodicità** (`S`/`Q`/`Q1`/`Q2`/`TC`/`C`/`C1`/`C2`) | L'attività non ricorre necessariamente ogni settimana; `Q1`/`Q2` sono l'equivalente di «settimana A/B» | tempo-e-calendario.md § *La periodicità* | strutturale | T10, A1 | alto | — | ⚠ «settimana A/B» **non esiste** in 69 888 stringhe: è terminologia nostra |
| T19 | **Periodicità personalizzate** (numeratore/denominatore) | `Quantità` su denominatore implicito = settimane dell'anno; **trimestri e quadrimestri usano lo stesso meccanismo**, non sono un concetto a parte | tempo-e-calendario.md § *Il modello è numeratore/denominatore* | medio | T18 | basso | — | ⚠ aperto se esistano denominatori reali > 2 |
| T20 | **Le quattro frequenze dell'attività** | `Attività settimanale` · `regolare` · `a cicli alternati` · `quindicinale` | tempo-e-calendario.md § *Le quattro frequenze* | banale | T18 | medio | — | — |
| T21 | **Preferiti di settimane** | `Crea un preferito che raggruppa delle settimane / dei cicli`: selezione arbitraria e nominata, per operazioni in blocco. Sta dietro la maschera di settimane a bit | tempo-e-calendario.md § *I «preferiti» di settimane* | banale | T18 | basso | — | «plausibilmente» — inferenza, non osservazione |
| T22 | **`Amenagement`** = attività a maschera monosettimanale | *"una modifica dell'orario per settimana"*: non un layer, **una riga di `COURS`** con natura diversa e un solo bit di settimana acceso. 141 su 984 nella base demo | tempo-e-calendario.md § *Gli Amenagement*; § *Chiuso: è la stessa struttura della sostituzione* | strutturale | T18, A1 | alto | **ADR-014: dentro** (una sola entità attività + maschera) | — |
| T23 | **Soppressione dell'occorrenza annuale** (`ANNULATIONCOURS`) | Cancella una singola occorrenza dell'attività annuale, distinta dalla cancellazione dell'attività | ADR-014 (da tempo-e-calendario.md § *Chiuso: è la stessa struttura*) | medio | T22 | alto | **ADR-014: dentro** | — |
| T24 | **Sedi** (multi-sede) | Esiste sempre una sede `Principale` non cancellabile; ogni attività può portare un `Site` | tempo-e-calendario.md § *Le sedi e il tempo di spostamento* | medio | — | basso | — | il doc la dà «candidato onesto a fuori scope v1, ma da dichiarare» |
| T25 | **Tempo di spostamento fra sedi** | Griglia `Sede A · Sede B · Verso · Durata`: **matrice orientata**, non scalare (A→B ≠ B→A) | tempo-e-calendario.md § *Le sedi e il tempo di spostamento* | strutturale | T24 | basso | — | ⚠ la voce «da verificare in UI» in coda al file è ancora aperta, ma la sezione la dà chiusa |
| T26 | **Regole di cambio di sede** | `Nelle pause` (confina il cambio alle pause); `Numero massimo di cambi di sede` per giorno/settimana/ciclo; caso hard: *"Nessun intervallo è attivo: il cambio tra queste sedi sarà vietato"* | tempo-e-calendario.md § *Le sedi* | medio | T24, T25, T5 | basso | — | — |
| T27 | **Aree mobile** (*Espaces mobiles*) | Citate una sola volta, senza contesto | tempo-e-calendario.md § *Cosa resta da verificare in UI* | ? | ? | ? | — | ⚠ **semantica ignota**: non è censibile finché non si osserva |

## B — L'attività

| ID | Nome (EDT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| A1 | **Attività** (unità di piazzamento) | `(classe, materia, durata, docente, [aula])` con attributi di piazzamento — *"l'unità esatta su cui lavorerà il nostro solver"*. Nello schema **solo la materia è obbligatoria** | attivita.md § *L'attività in Orario*; § *L'attività nello schema di scambio* | strutturale | — | alto | implicito ovunque | — |
| A2 | **Composizione a risorse dell'attività** | Il pannello elenca una riga per tipo: `Materie · Docenti · Personale · Raggruppamenti · Classi · Gruppi · Alunni dissociati · Aule · Materiali` | attivita.md § *Il pannello di composizione* | strutturale | A1 | alto | — | — |
| A3 | **Durata dell'attività > 1 fascia** (blocchi) | Un'attività da `2h` è un blocco indivisibile: *"la risposta alla domanda aperta sui blocchi passa da qui, non da un vincolo separato"* | attivita.md § *Semantica dedotta*; § *L'attività in Orario* | strutturale | A1, T1 | alto | — | — |
| A4 | **Doppia unità di durata** (`DureeMinutes` + `DureeSequences`) | Obbligatorie entrambe nello schema; `DureeSequences` è **decimale** | attivita.md § *L'attività nello schema di scambio* | banale | A3 | basso | — | ⚠ aperto se sia mai davvero non intero in un file reale |
| A5 | **Spezzamento in blocchi** (`Nr attività` + durate) | Doppio clic → finestra con numero, durata e frequenza dei blocchi; totale verde se quadra col piano, rosso altrimenti; tasto `Trasforma`. EDT propone un default (ITA 4h → 4×1h; MAT 5h → `1h, 2h`) | attivita.md § *Dalla previsione alle attività*; § *Struttura osservata* | medio | A3, P2 | alto | — | 📖 finestra ancora da osservare in UI |
| A6 | **Relazione padre/figlio fra attività** | `TypeParenteCours = CoursSimple/CoursPere/CoursFils`, auto-relazione: le figlie restano legate al padre sulla **stessa entità** → FK ricorsiva | attivita.md § *Lo spezzamento è padre/figlio* | medio | A5 | medio | — | — |
| A7 | **Allineamento → attività complessa** | *«tous les cours ayant le même Ident d'alignement seront regroupés au sein d'un même cours complexe»*; è l'allineamento a **generare** gruppi e raggruppamenti | attivita.md § *L'attività nello schema di scambio*; gruppi.md § *La struttura* | strutturale | A1 | alto | **ADR-013: dentro** («serve il meccanismo dell'attività complessa») | — |
| A8 | **Sezionamento** (`Sezion.`, 7 codici) | Come si distribuiscono docenti e raggruppamenti dentro l'attività complessa: `S` *Una lezione per docente*, `SQ` *…ogni 15 giorni*, `SC` *…per ogni ciclo*, `SP` *…gli alunni dipendono dal periodo* | attivita.md § *La colonna `Sezion.`* | strutturale | A7, G3 | basso | — | — |
| A9 | **Alternanza docenti/raggruppamento** (`A`, `AQ`, `AC`) | *"I docenti cambiano raggruppamento a metà dell'attività"*, o si alternano ogni 15 giorni / a ogni ciclo — laboratori e compresenze | attivita.md § *La colonna `Sezion.`* | strutturale | A8, T18 | basso | — | il doc chiede esplicitamente di esprimerlo **o dichiararlo fuori scope** |
| A10 | **Compresenza** (`Professeur` 0..N, colonna `Compr.`) | Più docenti sulla stessa attività: *"la compresenza è nel formato base"* | attivita.md § *L'attività nello schema di scambio* | medio | A1 | alto | — | osservata **vuota** sul dataset Fermi |
| A11 | **Attività senza docente** (cardinalità zero) | *"un'attività senza docente è legale nel formato"*: «docente da definire» non è un caso speciale | attivita.md § *L'attività nello schema di scambio* | banale | A1 | medio | — | — |
| A12 | **`Coeff.` / `Ponderation`** | Coefficiente `60/60` che scende in cascata da servizio → attività; pesa la durata ai fini del conteggio | attivita.md § *L'attività in Orario*; piani-di-studi.md § *Le colonne dei servizi* | banale | A1, P5 | medio | — | ⚠ aperto: *"quando si usa un valore ≠ 60/60?"* |
| A13 | **Priorità di piazzamento** (`S.P.`) | Valore `50` di default, «metà scala»: ordine con cui il motore affronta le attività | attivita.md § *L'attività in Orario* | banale | A1 | basso | — | ⚠ semantica marcata come ipotesi |
| A14 | **`Nr G.`** (giorni utili) | Numero di giorni su cui l'attività può cadere (`5` = lun–ven) | attivita.md § *L'attività in Orario* | banale | A1, T1 | basso | — | ⚠ ipotesi |
| A15 | **Stati di immobilità** (4 livelli) | `Rendi fissa`/`Rendi variabile` (badge `F`/`V` in colonna `P.P.`), `Blocca senza spostare`, `Blocca non sospendibili`, `Sospendi` — *"più granulari del semplice booleano «pinned» che avremmo modellato"* | attivita.md § *Azioni sull'attività* | medio | A1 | alto | — | — |
| A16 | **`Metti in attesa` / attività sospesa** | Toglie l'attività dal piazzamento senza cancellarla | attivita.md § *Azioni sull'attività* | banale | A1 | medio | — | — |
| A17 | **`Modalità di scelta` dell'aula** | Criterio con cui l'attività sceglie l'aula (`Senza specifica` di default) | attivita.md § *L'attività in Orario* | medio | A1 | medio | — | ⚠ ipotesi; dettaglio in `aule.md`, fuori dal perimetro di questo inventario |
| A18 | **`1 spazio possibile`** (dominio residuo esposto) | EDT mostra all'utente il numero di collocazioni ancora ammesse — *"un dato del solver mostrato come informazione"* | attivita.md § *Il pannello di composizione* | medio | A1 | alto | — | — |
| A19 | **Alunni dissociati** (`Nr A.`) | Alunni della classe che non seguono l'attività, fuori dal meccanismo delle parti | attivita.md § *L'attività in Orario*; § *Il pannello di composizione* | medio | A1, G2 | basso | — | ⚠ ipotesi; mai osservato valorizzato |
| A20 | **Raggruppamenti ad alunni variabili** (`Alu. Var.`) | `Differenzia il raggruppamento per alunni variabili` nel menu contestuale | attivita.md § *L'attività in Orario*; § *Azioni sull'attività* | medio | G3 | basso | — | ⚠ solo il nome della colonna, nessuna semantica documentata |
| A21 | **`Tipologia` dell'attività** | Etichette libere sull'attività | attivita.md § *L'attività in Orario* | banale | A1 | basso | — | ⚠ colonna vuota, semantica non documentata |
| A22 | **`Trasforma in priorità di sostituzione`** | Marca l'attività come prioritaria per il modulo supplenze | attivita.md § *Azioni sull'attività* | banale | A1, T22 | medio | — | ⚠ solo la voce di menu |
| A23 | **`Ripristina gli orari per settimana`** | Riporta l'attività alla collocazione annuale, cancellando gli `Amenagement` | attivita.md § *Azioni sull'attività* | banale | T22 | medio | — | — |
| A24 | **`Estrai`** (selezione persistente) | Riversa attività/risorse in una selezione di lavoro su cui piazzamento e ottimizzazione operano | attivita.md § *Azioni sull'attività* | medio | A1 | medio | — | dettaglio in `moduli-e-scope.md`, fuori perimetro |

## C — La catena previsionale (piano → servizio → attività)

| ID | Nome (EDT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| P1 | **Piano di studi** = indirizzo × anno | `Mef` identificato da `Formation` + `Specialite`; il campo `Livello` (primo…quinto) è l'anno di corso | piani-di-studi.md § *Campi osservati*; § *I servizi* | medio | — | alto | — | — |
| P2 | **Servizio** = quadro orario sul piano | Riga materia × ore appartenente al piano; *"il quadro orario si scrive una volta sul piano e cascata sulle classi"* | piani-di-studi.md § *I servizi*; classi.md § *Classi previsionali* | medio | P1 | alto | — | — |
| P3 | **Monte ore tripartito** (`H/Classe` · `Ridotto` · `Sdop.`) | Le tre durate per (piano, materia): classe intera, effettivo ridotto, quota in sdoppiamento. **È qui che i gruppi si dichiarano** | piani-di-studi.md § *I servizi* | medio | P2, G2 | alto | **ADR-013: dentro** (le ore si assegnano al gruppo) | — |
| P4 | **`Al./Cl.` e `Al./Rid.`** (cascata degli effettivi) | Default d'effettivo per classe sul piano; il numero ridotto della materia eredita **fin dentro il servizio** (`15` mai digitato) | piani-di-studi.md § *Campi osservati*; § *I servizi* | banale | P1 | medio | **ADR-003** (NULL = eredita), **ADR-005** (è un tetto) | — |
| P5 | **`Coeff.` del servizio** | Coefficiente `60/60` = FR `Pondération`; cascata fino all'attività | piani-di-studi.md § *Le colonne dei servizi* | banale | P2 | basso | — | ⚠ aperto: quando è ≠ `60/60` |
| P6 | **Servizio attivo/inattivo** (`A`) | *"Stato di attivazione del servizio"*, con filtro «visualizza i servizi inattivi» | piani-di-studi.md § *I servizi* | banale | P2 | basso | — | ⚠ aperto: *"cosa comporta un servizio inattivo"* |
| P7 | **`MS` — Modalità di scelta** | Codici `N/O/F/L/D/R/X`; presumibilmente le materie opzionali / a scelta | piani-di-studi.md § *Le colonne dei servizi* | medio | P2 | medio | — | ⚠ **aperto**: i sette codici non sono decifrati. Se sono le opzionali, il valore sale ad alto |
| P8 | **Sotto-servizio** | Divide un servizio (quota classe intera vs quota sdoppiata, o docenti diversi sulla stessa materia); riga figlia in corsivo, con `Nr attività` proprio | attivita.md § *Struttura osservata*; § *Semantica dedotta* | medio | P2 | medio | — | ⚠ *"differenza esatta fra sotto-servizio e attività"* ancora aperta |
| P9 | **Override per-classe del servizio** (`Dettaglia il servizio`) | Permette a una classe di scostarsi dal quadro orario del piano | classi.md § *Classi previsionali* | medio | P2, C1 | medio | **ADR-003** (cascata) | «suggerisce l'override, da osservare» |
| P10 | **Classi previsionali** (insieme distinto) | Le classi della fase di pianificazione, con `Recupera le classi dall'orario`: due insiemi distinti e sincronizzabili | classi.md § *Classi previsionali* | medio | C1 | basso | — | — |
| P11 | **Pianificazione senza classi** (dai soli effettivi del piano) | Modalità 2: bisogni e TRCD dagli alunni dei piani — ma **non** dà allineamenti né creazione delle attività | classi.md § *Classi previsionali* | medio | P1 | basso | — | TRCD dichiarata fuori scope in CLAUDE.md |
| P12 | **Ripartizione alunni piano × classe** | Matrice che è **l'input degli effettivi previsti** per classe (26 sulle 10 classi Fermi); rosso se non coincide con gli alunni reali | classi.md § *Classi previsionali* | banale | P10 | medio | — | — |
| P13 | **Assegnazione docenti ai servizi** (ripartizione puntuale) | Matrice materie × classi: chi prende quale classe. È dove `+/- → 0` diventa verificabile | attivita.md § *Le quattro viste*; § *Allineamento vs. assegnazione* | medio | P2 | alto | — | la ripartizione **automatica** è *"solo versione francese"*: in Italia si fa a mano |
| P14 | **Docenti supplementari** (`Nr. doc. suppl.`) | Segnaposto anonimi sommati al conteggio dei docenti desiderati; contano nei Bisogni come i nominati | attivita.md § *Allineamento vs. assegnazione*; § *Le quattro viste* | banale | P13 | medio | — | confermato in UI |
| P15 | **Campi previsionali derivati** (`Occ. prev.`, `+/-`, `Residue`, `Extra max.`) | Dashboard di carico aggiornata live dentro il dialogo di assegnazione | attivita.md § *Il dialogo «Selezione dei docenti»*; § *Come conteggia `Occ. prev.`* | medio | P13 | alto | **ADR-007: non si memorizzano**, si ricalcolano | — |
| P16 | **Filtri di eleggibilità del docente** | `Docenti della disciplina del servizio` / `della materia del servizio` / `in sotto-servizio`: la **capacità filtra l'assegnazione** | attivita.md § *Il dialogo «Selezione dei docenti»* | banale | P13 | alto | **ADR-006** (capacità ≠ assegnazione) | resta da capire il filtro «in sotto-servizio» |
| P17 | **Allineamento dei servizi** (vista 2) | Verifica e creazione degli allineamenti in previsionale; allineabili solo servizi con la **stessa suddivisione** | attivita.md § *Le quattro viste* | medio | A7, G1 | alto | **ADR-013: dentro** (11 modi di fallire da riusare) | 📖 **vista mai osservata in UI** |
| P18 | **`Crea le attività`** (generazione rigenerativa) | *"Tutte le classi che corrispondono alla vostra selezione, i dati che le riguardano e le loro attività saranno cancellate…"*: non incrementale | attivita.md § *Il dialogo di conferma* | medio | P13, A1 | alto | — | — |
| P19 | **`Mantieni i vincoli e le indisponibilità delle classi e delle materie`** | Checkbox spuntata di default: i vincoli sopravvivono alla rigenerazione. I docenti non sono menzionati (non vengono rigenerati) | attivita.md § *Il dialogo di conferma* | medio | P18 | alto | — | rilevante anche per la rigenerazione per periodo di ADR-010 |

## D — Classi, parti, gruppi

| ID | Nome (EDT) | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| C1 | **Classe** | Il gruppo-classe, con `Nome`, `N.Alu`, colore, `N.Sedi` | classi.md § *Campi osservati* | banale | — | alto | — | — |
| C2 | **`Niveau`** (livello) come entità | *"L'anno di corso ha anagrafica propria (`Ident` + `Libelle`)"*, e compare anche su `Mef`; biennio/triennio si legge attraverso livello e piano | classi.md § *La classe nello schema di scambio* | banale | C1, P1 | medio | — | — |
| C3 | **Classe articolata** (`Mef` 0..N) | Una classe può avere **più piani di studi**: *"rompe l'ipotesi classe → 1 piano che il nostro schema adotterebbe naturalmente"* | classi.md § *La classe nello schema di scambio* | strutturale | C1, P1, P2 | medio | — | non è il caso del Fermi: mai osservato sui dati |
| C4 | **`Aula preferenziale` della classe** | *"l'unico legame didattica↔aula che EDT modella nativamente"*: la classe ha la sua aula e si sposta solo per laboratorio o palestra | classi.md § *Campi osservati* | medio | C1 | alto | — | ⚠ le aule **non esistono** nella base del Fermi (`NBSALLES = 0`) |
| C5 | **`MMG` / `MG` sulla classe** | `Massimo di mezze giornate di lavoro` e `Lavorare solo mezza giornata al giorno` — **gli stessi vincoli del docente** applicati alla classe | classi.md § *Campi osservati* | medio | T8, C1 | medio | — | implica una tabella sola con FK polimorfica, non due |
| C6 | **Coordinatore / referente didattico** | `Docente coordinatore` (uno per classe nella base) e `Referente didattico`, ruolo distinto; lo schema ammette `ProfesseurPrincipal` 0..N | classi.md § *Campi osservati*; § *La classe nello schema di scambio* | banale | C1 | basso | — | — |
| C7 | **Occupazione della classe** (`Occ.`, `TOP`) | Ore occupate e tasso di occupazione, calcolati | classi.md § *Campi osservati* | banale | C1, A1 | medio | **ADR-007** (derivati, non memorizzati) | — |
| C8 | **Multi-istituto** (`Etablissement`, `EtablissementsGeres`) | Obbligatorio nello schema: *"il formato prevede nativamente il multi-istituto"* | classi.md § *La classe nello schema di scambio* | strutturale | C1 | basso | dichiarato *"fuori scope per noi"* nel doc (non in un ADR) | — |
| G1 | **Suddivisione** (partizione della classe) | `partition` FR: la partizione nominata di una classe, con nomi predefiniti (`Sdoppiamento`, `Suddivisione`, `Maschio/Femmina`, `UnTerzoDueTerzi`). Nel motore è **risorsa di prima classe** | gruppi.md § *La struttura*; § *Lo sdoppiamento in concreto* | medio | C1 | alto | **ADR-013: dentro** | ⚠ nello schema di scambio è degradata a stringa: *"il nostro modello segua l'interno, non lo scambio"* |
| G2 | **Parte di classe** (`PartieDeClasse`, IT «gruppo») | Il sottoinsieme di alunni che è **unità di piazzamento al posto della classe**; porta l'ident di **una sola** classe | gruppi.md § *La struttura*; § *La differenza fra parte e raggruppamento* | strutturale | G1 | alto | **ADR-004** + **ADR-013: dentro** | ⚠ **inversione IT↔FR**: «gruppo» traduce `partie`, non `groupe` |
| G3 | **Raggruppamento trasversale** (`Groupe`, IT «raggruppamento») | Insieme di parti che **attraversa più classi** (`FRANCESE 1AA-1BA`); `Groupe/Classe` è `0..N` | gruppi.md § *La struttura*; § *La differenza fra parte e raggruppamento* | strutturale | G2, A7 | alto | **ADR-013: dentro**, dichiarata *"la decisione più onerosa presa finora"* | 3 raggruppamenti in 5 corsi su 984: *"strumenti di nicchia anche in una base realistica"* |
| G4 | **Sdoppiamento** (tipi e riempimento) | Tipi offerti in UI: *prima metà, seconda metà, un terzo, due terzi, maschi, femmine*; riempimento `Alfabetico` o `Maschio/Femmina`. Regola letterale: *"il numero di raggruppamenti per classe è sempre uguale a 2"* | gruppi.md § *Lo sdoppiamento in concreto* | medio | G1, G2, P3 | alto | **ADR-013: dentro** | il riempimento nominativo richiede l'anagrafica alunni, che il progetto non ha |
| G5 | **IRC / attività alternativa** | Due parti della stessa classe (`_REL` / `_ALT`) che condividono l'ident di ripartizione — **non** gruppi, non compresenza, non materie diverse | gruppi.md § *IRC vs. attività alternativa* | banale | G1, G2 | alto | implicato da **ADR-013** | *"se supportiamo le partizioni lo otteniamo gratis"*; la pista 📖 era **sbagliata** |
| G6 | **Generazione automatica di gruppi dall'allineamento** | *"EDT crea, al bisogno, i gruppi e i raggruppamenti dello sdoppiamento"*: gruppi e raggruppamenti **non si creano a mano** | gruppi.md § *Dalla guida ufficiale*; § *La struttura* | medio | A7, G1, G2, G3 | medio | **ADR-013** (*"nello XSD è l'allineamento a generare il raggruppamento, non il contrario"*) | 📖 + 📦, mai visto operare in UI |
| G7 | **Assegnazione docente a gruppo/parte** | *"Le assegnazioni docente devono poter puntare a un gruppo o a una parte, non solo a una classe intera"* | gruppi.md § *Implicazioni per il nostro modello* | medio | G2, G3, P13 | alto | **ADR-013: dentro** | — |
| C9 | **Formazione Classi** | Composizione delle classi dagli alunni reali (criteri Rendimento/Comportamento/Assenteismo/BES, preferenze di raggruppamento e separazione) | classi.md § *Formazione Classi — fuori scope* | strutturale | — | basso | dichiarato **fuori scope** nel doc: *"è un problema di ottimizzazione diverso"* | richiede anagrafica alunni nominativa, assente dal progetto |

---

## Note sulle dipendenze non ovvie

Le catene che **cambiano la forma del modello**, non solo il numero di vincoli:

1. **G3 (raggruppamenti trasversali) → distrugge la decomposizione per classe.**
   ADR-013 lo dice esplicitamente: se 1A, 1B e 1C si ricompongono per la seconda
   lingua, quelle classi non si piazzano più indipendentemente. È l'unica voce
   dell'inventario che tocca la *strategia di risoluzione*, non il modello dati.
2. **G2 (parti) → l'unità di piazzamento non è più la classe.** Ogni vincolo
   scritto su «classe» (C5, T8, occupazione, buchi) va riscritto su «unità
   didattica» = classe **o** parte. Si propaga a P3, G7, A19.
3. **T13 (periodi) + T16 (fascia variabile) → la variabile di decisione raddoppia.**
   ADR-010 taglia T16, ma T13 resta: T15 (attività non annuali) dipende da T13 e
   sopravvive al taglio.
4. **T18 (periodicità) + T22 (Amenagement) → l'attività ha una maschera temporale.**
   ADR-014 fonde attività, spostamento puntuale e sostituzione in una sola entità:
   la partecipazione risorsa↔attività diventa **temporale, non booleana**.
5. **A3 (durata > 1 fascia) → l'attività è un intervallo, non una cella.** Trascina
   T6 (rispetto degli intervalli) e cambia la codifica CP-SAT da booleani per cella
   a `IntervalVar` / `NoOverlap`.
6. **A7 (allineamento) → precede G3 e G6.** Nello XSD l'allineamento *genera* il
   raggruppamento: modellare i gruppi come anagrafica a monte va contro il prodotto.
7. **C3 (classi articolate, `Mef` 0..N) → un quadro orario per classe non basta.**
   Mai osservato sui dati, ma rompe l'ipotesi che P2 induce naturalmente.
8. **T25/T26 (sedi) → vincolo sulla sequenza**, non sul singolo slot: richiede di
   ragionare su collocazioni *consecutive* di una risorsa, forma che nessun altro
   vincolo di questo elenco introduce.

## Voci non censibili

- **T27 `Aree mobile`**: citata una sola volta, senza contesto. Non ha semantica
  nota, quindi non ha costo né valore stimabili.
- **P7 `MS`**: i sette codici `N/O/F/L/D/R/X` non sono decifrati. Se coprono le
  **materie opzionali**, la voce cambia di peso: da `medio/medio` a `strutturale/alto`,
  perché le opzionali producono gruppi trasversali (G3) di per sé.
