# Inventario piatto delle funzionalità — vincoli e diagnostica

Estratto da `docs/edt/vincoli.md` e `docs/edt/diagnostica.md` (letti integralmente,
2026-07-26). **Non contiene decisioni di scope**: la colonna `Già deciso` riporta
solo ciò che un ADR ha già stabilito.

Legenda colonne:

- **Costo** — `banale` / `medio` / `strutturale` rispetto a un solver CP-SAT +
  schema Django. `strutturale` = cambia la **forma** del modello (nuove entità,
  nuove dimensioni delle variabili, nuovo componente), non aggiunge solo un vincolo.
- **Dipende da** — ID di altre righe di questo inventario che devono esistere
  perché questa abbia senso.
- **⚠** — la documentazione è marcata incerta / «da verificare» su questo punto.

---

## A — Disponibilità delle risorse (i tre pennelli)

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **A1** | Indisponibilità (rosso) | *"Mai violata"* — maschera hard risorsa × slot, per i casi imperativi (giorno libero richiesto, servizio in altro istituto) | vincoli.md § *Indisponibilità e preferenze docente* | banale | A5 | **alto** — è il vincolo che ogni scuola inserisce per primo | — | |
| **A2** | Indisponibilità opzionali (giallo) | Rispettata come una rossa, ma l'utente può autorizzare il motore a ignorarle per risolvere le attività scartate | vincoli.md § *Indisponibilità e preferenze docente* | medio | A5, D8 | alto | — | |
| **A3** | Preferenze (verde) | *"Fascia in cui il docente vorrebbe lezione"* — desiderata, nessuna garanzia | vincoli.md § *Indisponibilità e preferenze docente* | medio (termine di obiettivo, non vincolo) | A5 | medio | — | |
| **A4** | Esclusione **globale** delle gialle | L'override delle opzionali non è selettivo: si attivano/disattivano tutte insieme, per tutti i docenti | vincoli.md § *Indisponibilità e preferenze docente* | banale | A2 | basso — è un limite di EDT, non una feature desiderabile | — | |
| **A5** | 🔑 Disponibilità **generica sulla risorsa** | Un solo meccanismo rosso/giallo/verde valido per docenti, classi, aule, materiali, personale **e attività** — una sola tabella `resource_unavailability(resource, slot_range, date?)` | vincoli.md § *Il vincolo è generico sulla risorsa*; diagnostica.md § *Indisponibilità e preferenze* (9 tipi di risorsa) | **strutturale** — decide la forma dell'entità disponibilità e quante risorse esistono | G2 | **alto** — semplifica tutto il resto; sbagliarla costa una riscrittura | — | |
| **A6** | Indisponibilità **sull'attività** | La stessa griglia a tre pennelli si apre sulla singola attività, non solo sulle risorse (lun–ven × 08h–18h) | vincoli.md § *Indisponibilità e preferenze docente* | banale se c'è A5 | A5 | medio | — | |
| **A7** | Indisponibilità **datata** = assenza | Stessa tabella: `data` nulla → indisponibilità ricorrente; `data` valorizzata → assenza effettiva (28 vs 199 record nella base demo) | vincoli.md § *Indisponibilità e assenze sono la stessa tabella* | medio | A5 | **alto** — è **la stessa entità** che serve al SaaS sostituzioni già in produzione | ADR-014 (una sola entità attività con maschera temporale) | |
| **A8** | Frequenza `Settimanale` / `Settimane Q1-Q2` sulla griglia | L'indisponibilità può valere ogni settimana o solo su una delle due quindicine | vincoli.md § *Indisponibilità e preferenze docente* | medio | A5, D3 | basso in Italia | — | |

## B — Vincoli orari numerici sulla risorsa (sette gruppi + buchi)

Pannello osservato per intero: sono **sette gruppi più le preferenze di
ottimizzazione**, e l'elenco è completo.

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **B1** | **D** — Distribuzione oraria imposta | *"Minimo N giorni a settimana con un minimo di X per giorno"* — è un **minimo**, evita che il solver concentri tutto | vincoli.md § *vincoli orari* (`TContrainteRepartitionDemiJournees`) | medio | — | medio | — | |
| **B2** | **M** — Massimo di ore di attività | Tetto di ore di lezione su `Giornata:` / `Mattino:` / `Pomeriggio:` | vincoli.md § *vincoli orari* (`TContrainteMaxHoraireRessource`) | banale | F9 | **alto** — il classico «non più di 5 ore al giorno» | — | ⚠ manca dalle 10 famiglie violabili: non si sa se sia lacuna del controllo o verificato per costruzione |
| **B3** | **P** — Massimo di ore di **presenza** | *"N giorni alla settimana, presenza massima in istituto: X"* — **presenza ≠ attività**: la presenza include i buchi, sono due contatori distinti | vincoli.md § *vincoli orari* (`TContrainteMaxPresentielRessource`) | medio | B8 (nozione di buco) | medio | — | |
| **B4** | **E** — Gestione Entrate / Uscite | Su N giorni alla settimana: `non iniziare prima delle` / `non finire oltre le` | vincoli.md § *vincoli orari* (`TContrainteJEG`) | medio | — | **alto** — è il part-time e il pendolarismo, richiesta ricorrente | — | |
| **B5** | **G** — Giorni e ½ giornate libere **garantite** | `Assegna N giornate libere + N mezze giornate libere`. FR `Plages libres *garanties*`: EDT si impegna, non è un desiderata | vincoli.md § *vincoli orari* (`TContraintePLG_DJT`) | medio | F9 | **alto** — il «giorno libero» è la contrattazione sindacale più visibile | — | |
| **B6** | **⅁** — Massimo di mezze giornate di lavoro | `Mattino:` / `Pomeriggio:` + casella `Lavorare solo mezza giornata al giorno` | vincoli.md § *vincoli orari* | medio | F9 | medio | — | |
| **B7** | **S** — Numero massimo di cambi di sede | Tetto `per giorno` / `per settimana` (e per ciclo) di trasferimenti fra plessi | vincoli.md § *vincoli orari* | medio | F6 | medio — solo scuole su più plessi, ma per loro alto | — | |
| **B8** | `D.T.B.` — Durata tollerata dei buchi | Soglia di ore di buco per risorsa (default `2h00`), FR *Nombre d'Heures de Trous Tolérées* | vincoli.md § *`D.T.B.`* | medio | F9, B11 | **alto** — il buco è la lamentela numero uno dei docenti | — | |
| **B9** | Autorizza il superamento del massimo di buchi tollerati | Override esplicito della soglia `D.T.B.` | vincoli.md § *`D.T.B.`* | banale | B8 | basso | — | |
| **B10** | `Riduci i buchi (docenti)` / `(classi)` | Due leve **distinte** di ottimizzazione: il buco è insieme soglia e termine della funzione obiettivo | vincoli.md § *`D.T.B.`* | medio | B8 | alto | — | |
| **B11** | Linea di fine mattinata | `Non conteggiare come buchi le ore libere prima o dopo la linea di fine mattinata` — serve a non contare la pausa pranzo come buco | vincoli.md § *`D.T.B.`* | banale | — | alto (senza, il conteggio dei buchi è inutilizzabile) | — | |
| **B12** | Opzioni minori sul conteggio dei buchi | `Lascia i buchi di 1/2 ora`; `Non considerare i cambi di sede come dei buchi` | vincoli.md § *`D.T.B.`* | banale | B8, F6 | basso | — | |
| **B13** | Gli stessi vincoli orari **sulla classe** | `MMG` / `MG` della vista Classi = `Massimo di mezze giornate di lavoro` e `Lavorare solo mezza giornata al giorno`, applicati alla classe | vincoli.md § *vincoli orari*; CLAUDE.md → classi.md | banale se c'è A5 | A5, B6 | **alto** — «le prime non fanno pomeriggio» è normale in Italia | — | |

## C — Vincoli di materia (matrice classe × materia A × materia B)

Dieci colonne, attivabili una per una, ciascuna con la propria icona a matita
(prendono valori, non solo flag). La relazione è **orientata**: `A→B` e `B→A` sono
record distinti.

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **C0** | La griglia stessa (contenitore per classe) | Matrice materie × materie **per classe**; il pannello resta vuoto finché non si seleziona una classe | vincoli.md § *La griglia com'è davvero* | medio | — | **alto** — è il contenitore di tutto il gruppo C | — | |
| **C1** | `Incompatibilità 1/2g` | *"perché due attività delle materie selezionate non siano piazzate nella stessa mezza giornata"* | vincoli.md § *I dodici tipi* | banale | C0, F9 | alto | — | |
| **C2** | `Incompatibilità 1g` | *"LATIN and GREEK should not be held in the same day"* — 🔑 usata soprattutto **materia con sé stessa**: 15 righe su 19 nei dati reali | vincoli.md § *I dati reali della base di esempio* | banale | C0 | **altissimo** — *"se il nostro solver ne supportasse uno solo, sarebbe questo"* | — | |
| **C3** | `Incompatibilità 2g` | *"…non siano piazzate in due giorni consecutivi"* | vincoli.md § *I dodici tipi* | banale | C0 | medio | — | |
| **C4** | `Incompatibilità N. 1/2g` — scarto in mezze giornate | *"Numero minimo di 1/2 giornate: per inserire un certo numero di mezze giornate tra due attività"* | vincoli.md § *I dodici tipi* (`EcartDj`) | medio | C0, F9 | medio | — | |
| **C5** | `Seq. Ind.` — sequenza vietata | *"perché un'attività della materia B non si svolga subito dopo un'attività della materia A"* — **orientata** | vincoli.md § *Cosa fa ogni colonna* | banale | C0 | alto — «no matematica dopo educazione fisica» | — | |
| **C6** | `Max ore 1/2g` | Tetto orario della materia sulla mezza giornata | vincoli.md § *I dodici tipi* | banale | C0, F9 | alto | — | |
| **C7** | `Max ore 1g` | *"No more than 2 hours of language in the same day"* — **tetto, non divieto**: nei dati reali `LETTERE` = `2h00` | vincoli.md § *I dati reali* | banale | C0 | alto | — | |
| **C8** | `Ordine Sett.` (e `Ordine nel ciclo`) | *"perché un'attività della materia A si svolga sempre prima di un'attività della materia B"*. Le due varianti differiscono solo per l'orizzonte (settimana/ciclo) | vincoli.md § *Perché dieci colonne e dodici tipi* | medio | C0 | medio | — | |
| **C9** | `Attività in gruppo` (`Parties…Classe`) | Ordine `Prima`/`Dopo` fra le ore **in gruppo** e le ore **a classe intera**: *"The courses in a group for BIOLOGY should not be held after the courses in a full class"* | vincoli.md § *Cosa fa ogni colonna*; diagnostica.md § *Chiuso: i quattro valori* | medio (ma **esiste solo** se ci sono gli sdoppiamenti) | C0, **sdoppiamenti** | medio | **ADR-013** lo cita come conseguenza diretta dello scope sdoppiamenti | ⚠ resta inferenza quale dei 4 valori `Parties…` mappi su quale valore di parametro |
| **C10** | `Conc. Imp.` — concatenazione imposta | *"determina l'intervallo temporale massimo tra due attività della stessa materia"*: **ritardo massimo** parametrico. Assorbe `Successione imposta ½ g.` e `J+1` come valori del parametro | vincoli.md § *Cosa fa ogni colonna* | medio | C0, F9 | alto — *"due SCIENZE in due giorni consecutivi"* | — | ⚠ la corrispondenza tipo→valore di parametro non è la tabella ufficiale, è ricostruita |

## D — Vincoli fra attività (`TNetContrainteCoursACours`)

Undici tipi dal menu reale. La colonna `Ordine` della griglia dice che hanno un
verso. **Limiti dichiarati dal prodotto**: max due attività su settimane alterne,
max due attività consecutive, e — 🔑 — *"le attività coinvolte nei vincoli tra
attività non possono essere allineate"*.

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **D0** | L'entità «vincolo fra attività» | Vincolo dichiarato dall'utente su una **coppia (o n-upla) di attività** selezionate a mano; `Aggiungi un vincolo` disabilitato finché non se ne selezionano almeno due | vincoli.md § *Vincoli fra attività* | **strutturale** — introduce vincoli dato-driven fra oggetti arbitrari, non fra risorse; interferisce con l'allineamento | — | medio | — | |
| **D1** | `Imporre la collocazione` (stessa ½ giornata / stessa giornata) | Due attività devono cadere nella stessa mezza giornata o nella stessa giornata | vincoli.md § *Gli undici tipi* | medio | D0, F9 | medio | — | |
| **D2** | `Impedire la collocazione` (stessa ½ giornata / stessa giornata) | Le due attività non possono cadere insieme | vincoli.md § *Gli undici tipi* | medio | D0, F9 | medio | — | |
| **D3** | Vincolo di **quindicina** (stessa / diversa settimana) | Lavora sulla **maschera delle settimane**, non sulla griglia oraria (risulta disattivato se le due attività hanno la stessa periodicità) | vincoli.md § *Gli undici tipi* (`TNetInfosContrainteQuinzaine`) | **strutturale** — richiede la maschera settimanale sull'attività | D0 | basso in Italia (settimane alterne rare) | ADR-014 introduce comunque la maschera temporale; ADR-010 esclude la collocazione per periodo | |
| **D4** | Scarto in un **numero definito di mezze giornate** | L'unico degli undici che prende un parametro (`Numero di mezze giornate:` a tendina) | vincoli.md § *L'opzionalità, testo letterale* (`TNetInfosContrainteEcart`) | medio | D0, F9 | medio | — | ⚠ `Écart` è termine sovraccarico nel prodotto |
| **D5** | `Definire l'ordine delle attività selezionate` | A prima di B, presumibilmente non adiacenti | vincoli.md § *Gli undici tipi* | medio | D0 | medio | — | ⚠ **la distinzione ordine/sequenza è presunta, non verificata** |
| **D6** | `Imporre la sequenza` | Le attività devono essere **consecutive** | vincoli.md § *Gli undici tipi* (`TNetInfosContrainteSuccession`) | medio | D0 | medio | — | ⚠ stessa incertezza di D5 |
| **D7** | `Impedire la sequenza` | Le attività non possono susseguirsi | vincoli.md § *Gli undici tipi* | medio | D0 | medio | — | ⚠ stessa incertezza di D5 |
| **D8** | 🔑 Flag **`Vincolo opzionale`** + passata di alleggerimento | Casella **spuntata di default**: *"può essere alleggerito durante il piazzamento delle attività scartate"* — cioè la strategia a **due passate**: tutto hard, poi una seconda passata coi vincoli opzionali allentati | vincoli.md § *L'opzionalità, testo letterale* | **strutturale** — la risoluzione diventa a due fasi, e ogni vincolo porta un livello di durezza | D0 | **alto** — è ciò che rende il fallimento recuperabile invece che terminale | — | |
| **D9** | Nome del vincolo dato dall'utente | `Personalizza il nome del vincolo (facoltativo)` — campo libero | vincoli.md § *L'opzionalità* | banale | D0 | basso, ma aiuta la diagnostica leggibile | — | |

## E — Peso didattico (carico cognitivo)

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **E1** | Peso didattico **per materia** | Intero per materia; `Totale = Peso × Durata` (formula letta a schermo). Default osservato **`1`**, non 0 | vincoli.md § *Osservato in UI — e la feature è spenta di serie* | banale | — | **alto** — *"non mettete matematica, fisica e latino lo stesso giorno"*, problema che ogni scuola ha e nessuno modella | **ADR-011: dentro v1** | ⚠ la scala `0–10` viene **solo dalla guida**; nessun messaggio di validazione la conferma |
| **E2** | Tetti d'istituto su mattino / pomeriggio / giornata / settimana | `Peso didattico massimo per l'istituto:` con quattro `Limite…` (cinque con il ciclo). In CP-SAT sono tre `sum(...) <= limite` per classe | vincoli.md § *Come è strutturato* | banale | E1, F9 | alto | **ADR-011: dentro v1** | ⚠ nella base demo **tutti e quattro valgono `nessuno`**: il produttore non esercita la feature |
| **E3** | Tetto di **classe**, con cascata dal default d'istituto | `Peso didattico massimo per settimana per un alunno`, ridefinibile per classe | vincoli.md § *Come è strutturato* | banale | E2 | medio | ADR-011 + **ADR-003** (cascata `NULL` = eredita) | ⚠ non verificato se il `33` in lista classi sia un tetto o un totale calcolato |
| **E4** | 🔑 Il totale è **per alunno**, non per classe | Il conteggio scarta le materie alternative che nessuno studente segue insieme (`RELIGIONE` vs `ALTERNATIVA`): `1 B/R` = 33, non 34 | vincoli.md § *Il totale è per alunno* | medio — richiede il modello a **parti** della classe | E1, sdoppiamenti/parti `_REL`/`_ALT` | alto (è l'unico modo in cui il vincolo abbia senso) | ADR-013 (parti/gruppi in v1) | |
| **E5** | Peso didattico sui **raggruppamenti** | *"Alcuni raggruppamenti (%d) superano il limite dei pesi didattici"* | vincoli.md § *Dove riappare*; diagnostica.md § *Diagnostica sui raggruppamenti* | medio | E2, raggruppamenti trasversali | basso | ADR-013 | |
| **E6** | Totale dei pesi **mostrato in griglia** | `Totale dei pesi didattici della mattinata / del pomeriggio / della giornata` in fondo alle colonne, visibile mentre si lavora | vincoli.md § *Dove riappare* | banale (UI) | E1 | medio — rende il vincolo comprensibile | — | |

## F — Tempo, intervalli, mensa, sedi

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **F1** | `Intervallo` come oggetto d'istituto | Tabella `RECREATION` con **durata e rango** (demo: intervallo del mattino rango 2, del pomeriggio rango 4) | vincoli.md § *Due colonne che non sono vincoli* | medio | — | alto | — | |
| **F2** | `Rispetta gli intervalli` per attività | Booleano sull'attività: se spuntato, l'attività non può stare **a cavallo** dell'intervallo | vincoli.md § *Due colonne che non sono vincoli* | banale | F1, G3 | alto | — | |
| **F3** | Intervallo applicato a un **insieme di classi** | `NONRESPECTCLASSERECREATION`: l'intervallo vale per le classi scelte, non per tutte | vincoli.md § *Due colonne che non sono vincoli* | banale | F1 | medio | — | |
| **F4** | `Ignora gli intervalli` (interruttore del solver) | Disattivazione in blocco del vincolo intervallo durante il calcolo | vincoli.md § *Due colonne che non sono vincoli* | banale | F1 | basso | — | |
| **F5** | **Mensa** come vincolo hard | Compare fra le dieci famiglie violabili: conferma indipendente che è un vincolo vero e non un'impostazione di visualizzazione | vincoli.md § *Le dieci famiglie violabili* | medio | F9 | **alto** in scuole con tempo pieno / rientri | — | |
| **F6** | **Sedi distaccate** | Vincolo di plesso; unico vincolo di aula oltre alla disponibilità. Marcatore rosa nella diagnostica di `Aule disponibili` | vincoli.md § *Cosa dicono gli artefatti*; § *Le dieci famiglie violabili* | **strutturale** — introduce la geografia nel modello (sede per risorsa e per attività) | — | medio (alto per scuole multi-plesso, sempre più frequenti) | — | |
| **F7** | Tempo di trasferimento fra sedi | *"Tempo insufficiente per il trasferimento di sede"* — vincolo di transizione fra slot consecutivi | diagnostica.md § *Vincoli di sede* | medio | F6 | medio | — | |
| **F8** | Cambio di sede solo durante un intervallo/pausa | *"Cambio di sede al di fuori delle pause/intervalli definiti"* | diagnostica.md § *Vincoli di sede*; vincoli.md § *Due colonne* | medio | F6, F1 | medio | — | |
| **F9** | 🔑 La **mezza giornata** come concetto di prima classe | *"La granularità dei vincoli è la mezza giornata, non l'ora"* — derivata dalla linea di fine mattinata; quasi tutti i vincoli di relazione si esprimono in giornate o mezze giornate | vincoli.md § *Implicazioni per il nostro modello*, punto 6 | **strutturale** — è una dimensione del modello da cui dipendono ~25 righe di questo inventario | B11 | **alto** — non averla obbliga a riscrivere ogni vincolo di relazione | — | |

## G — Attività, risorse, capacità

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **G1** | Capacità simultanea della risorsa (`Qtà`) | *"L'aula accetta `Numero di aule` attività in parallelo"*; per aule e materiali esiste la causale *"ha raggiunto il suo picco d'occupazione"* | vincoli.md § *Implicazioni*, asse Capacità; diagnostica.md § *Risorsa occupata* | **strutturale** — da `AllDifferent`/`NoOverlap` a un vincolo **cumulativo** | A5 | medio-alto (palestre, laboratori) | — | ⚠ non compare fra i vincoli ignorabili, «verosimilmente perché non è negoziabile» |
| **G2** | **Personale** e **materiali** come risorse di piazzamento | Le causali di occupazione e indisponibilità esistono identiche per personale e materiali: sono risorse sullo stesso piano di classi/docenti/aule | diagnostica.md § *Risorsa occupata*, § *Indisponibilità e preferenze* | **strutturale** — cambia il numero e la forma delle risorse del modello | A5 | basso in Italia (raro), ma gratis se A5 è generica | — | |
| **G3** | Durata dell'attività / blocchi di ore consecutive | Non è un vincolo separato: è la **durata** fissata nello spezzamento del servizio (numero/durata/frequenza dei blocchi) | vincoli.md § *Blocchi di ore consecutive* | medio | — | **alto** — «due ore di laboratorio di fila» è ovvio per una scuola | — | |
| **G4** | **Blocco** dell'attività (`Verrouille`) | Stato che rende l'attività non spostabile dal motore | diagnostica.md § *I quattro stati* | medio | — | alto | — | |
| **G5** | 🔑 **Priorità** dell'attività | `Rendi prioritarie le attività` / `Rendi non prioritarie` — distinta dal blocco: il blocco dice *non toccare*, la priorità dice *toccabile ma solo per una causa migliore* | diagnostica.md § *Le attività hanno una priorità* | medio | G4, H2 | medio | — | ⚠ mai osservato in UI |
| **G6** | I **quattro stati** dell'attività | `NonPlace` · `EnEchec` (**Scartata**) · `Place` · `Verrouille` — non è un booleano piazzata/non piazzata | diagnostica.md § *I quattro stati* | banale | — | medio | — | ⚠ da chiarire se `NonPlace` e `EnEchec` siano davvero distinti per l'utente |
| **G7** | Audit trail per attività | `Type_OperationCours`: `Piazzamento automatico` / `manuale` / `Risolvi` / `Trova una soluzione` / `Sospensione` / `Piazza / Sistema` — ogni operazione loggata e distinguibile | diagnostica.md § *I quattro stati*, «Tracciabilità» | medio | G6 | alto — *"chi ha spostato questa lezione e perché"* arriva sempre | — | |
| **G8** | Attività isolate (`Cours isolés`) | **Criterio di ottimizzazione, non vincolo**: *"attività isolata in una mezza giornata **e** di durata inferiore a due fasce orarie"*. Contatore per docente/classe (`A.iso.`) | vincoli.md § *Due colonne che non sono vincoli* | medio | F9, G3 | medio | — | prova negativa solida: non compare in nessuna causale di diagnostica |

## H — Diagnostica e analisi

| ID | Nome | Cosa fa | Riferimento | Costo | Dipende da | Valore | Già deciso | ⚠ |
|---|---|---|---|---|---|---|---|---|
| **H1** | Catalogo delle **causali nominate** | ~170 frasi intere invece di «infeasible»: *"La classe è già occupata in un'attività bloccata"*. Riusabile quasi così com'è | diagnostica.md § *Il catalogo delle causali* | **strutturale** — ogni vincolo del modello deve saper dire perché ha fallito, cioè portare un'etichetta e una spiegazione | — | **alto** — *"un generatore che risponde solo «fatto»/«non ce l'ho fatta» è inutilizzabile"* | — | ⚠ nessuna di queste finestre osservata in UI: i testi sono certi, la disposizione no |
| **H2** | 🔑 Occupata **spostabile** vs occupata **bloccata** | Cinque varianti per ogni risorsa: occupata / con collocazione altrove / bloccata / in permanenza / in permanenza bloccata. *"È il perno di tutto"*: abilita il risolutore a catena | diagnostica.md § *Risorsa occupata* | **strutturale** — non basta sapere che uno slot è occupato: serve sapere **da cosa** e **se è mobile** | G4, G5 | alto | — | |
| **H3** | Causale «picco d'occupazione» | *"il gruppo di aule/materiale ha raggiunto il suo picco d'occupazione"* | diagnostica.md § *Risorsa occupata* | banale | G1, H1 | medio | — | |
| **H4** | **Analisi fase 1** — attività senza fasce disponibili | Caso **individuale**: un'attività che presa da sola non ha nessuna collocazione ammissibile (intersezione vuota delle disponibilità delle sue risorse) | diagnostica.md § *Cosa significano le fasi 1 e 5* | medio | A5 | **alto** — errore frequentissimo, facile da spiegare | — | |
| **H5** | **Analisi fase 2** — occupazione delle risorse | Verifica di capienza per risorsa; internamente si articola nelle **cinque** risorse (classi, docenti, aule, personale, materiali) | diagnostica.md § *Le cinque fasi* | medio | H10 | alto | — | ⚠ una sola voce in UI, cinque sotto-fasi interne |
| **H6** | **Analisi fase 4** — vincoli delle materie, con aritmetica | *"Classe 1B, LETTERE, 6 attività, durata da piazzare 10h00, durata piazzabile 9h00 » 1h00 non potrà essere piazzata"* — quantifica lo scarto | diagnostica.md § *Come EDT presenta una diagnosi* | medio | C0, H10 | **altissimo** — è il verdetto verificabile invece di «non ci sta» | — | |
| **H7** | 🔑 **Analisi fase 5** — insieme di attività non piazzabili | Caso **collettivo**: 25 attività, 11 docenti + 1 classe + 1 aula, 33h di domanda contro 32h di finestra di disponibilità comune. È la ricerca di un **violatore di Hall** | diagnostica.md § *C — Un insieme di attività* | **strutturale** — un componente di ricerca combinatoria a sé, che CP-SAT non dà gratis (l'UNSAT core è illeggibile) | H10, A5 | **alto** — *"è metà della differenza di UX che vogliamo ottenere"* | — | è anche la fase **più lenta** del prodotto |
| **H8** | Diagnosi su **vincoli incrociati** di due risorse | *"I vincoli incrociati della classe e del docente non permettono il piazzamento"*: due vincoli di **famiglie diverse** innocui separatamente e fatali insieme, mostrati affiancati | diagnostica.md § *B — Vincoli incrociati* | **strutturale** — la spiegazione deve poter nominare **combinazioni** di vincoli, non un colpevole singolo | H10 | alto | — | |
| **H9** | La struttura a **quattro riquadri** della diagnosi | `Enunciato del problema` in italiano corrente · `Azioni che permettono di risolvere il problema` (rimedi, non errori) · `Dettaglio` con l'aritmetica · `Soluzione` con la riga di vincolo colpevole | diagnostica.md § *Come EDT presenta una diagnosi* | medio (UI) | H10 | **alto** — è il formato riusabile quasi identico | — | |
| **H10** | 🔑 Il **motore di analisi di capienza**, separato dal solver | *"Non serve un solver per dirlo. È un conteggio di capienza: date le ore richieste e i vincoli di distribuzione, quante ne entrano al massimo? Si calcola in millisecondi"* | diagnostica.md § *Perché conta per noi, in concreto* | **strutturale** — *"da progettare fin dall'inizio come componente a sé, non come interpretazione a posteriori dell'output del solver"* | — | **alto** — è la funzione più preziosa trovata nel reverse engineering | — | l'analisi di EDT è **esatta**, verificato: asticella da tenere, un falso allarme distrugge la fiducia |
| **H11** | Riquadro `Soluzione` **operativo** | Non mostra il vincolo, lo **rende modificabile lì**: tendine e griglia delle indisponibilità sul posto, poi `Rilancia la verifica`. Diagnosi → correzione → riverifica senza cambiare finestra | diagnostica.md § *Il riquadro Soluzione è operativo* | medio (UI, ma tocca tutte le form dei vincoli) | H9 | **alto** — *"è la differenza fra uno strumento che si usa e uno che si abbandona"* | — | |
| **H12** | `Estrai le materie, le risorse coinvolte e le attività` | Riversa la diagnosi nella **selezione di lavoro** su cui operano tutte le altre azioni: diagnostico → seleziono i colpevoli → agisco su quelli | diagnostica.md § *Le azioni offerte* | medio | H10, primitiva `Estrai` | alto — *"è architettura, non comodità"* | — | |
| **H13** | 🔑 **Controllo di conformità a posteriori** | `Estrai le attività che non rispettano i vincoli`: **21/984 (38h00)** nella base demo. Serve ogni volta che si modifica a mano, si importa, o si cambia un vincolo dopo aver piazzato | vincoli.md § *Le dieci famiglie violabili*; diagnostica.md § *L'analisi è esatta* | medio (riusa i vincoli come predicati valutabili su una soluzione data) | H14 | **alto** | — | |
| **H14** | 🔑 Un orario valido **non è un invariante** | Le violazioni sono uno stato **ammesso e interrogabile**, non un errore da impedire. *"Vietare a priori significa costringere l'utente a mentire al sistema"* | diagnostica.md § *E un corollario che vale da solo* | **strutturale** — nessun vincolo di integrità sul DB; ogni vincolo deve esistere due volte: come constraint del solver e come **predicato valutabile** | — | **alto** — è una scelta di progetto esplicitamente «da imitare» | — | |
| **H15** | Le **dieci famiglie violabili** selezionabili | Finestra `Criteri di estrazione`: `Massimo di presenza`, `Giorni e 1/2 giornate libere`, `Mezze giornate di lavoro`, `Vincolo materia`, `Mensa`, `Sedi distaccate`, `Intervallo`, `Indisponibilità opzionali`, `Indisponibilità`, `Vincolo tra attività` | vincoli.md § *Le dieci famiglie violabili* | banale | H13 | medio | — | ⚠ **mancano `Massimo di ore` e `Peso didattico`**, pur essendo vincoli a pieno titolo. Da chiarire |
| **H16** | Colonne `S.P.` / `Nr G.` — dominio residuo | *"Numero di fasce orarie possibili per il piazzamento dell'attività nel rispetto di tutti i vincoli"* e *"numero di giorni possibili"*. Ordinando per `S.P.` crescente si vede **cosa sta per diventare impiazzabile** | diagnostica.md § *Le colonne che rivelano lo stato* | banale — *"il solver quel numero lo calcola comunque durante la propagazione"* | — | **alto** — diagnostica preventiva a costo zero | — | ✅ confermato in UI, l'inferenza era esatta |
| **H17** | Modalità diagnostica del piazzamento manuale | Comando esplicito `Passa alla modalità diagnostica`: la diagnostica **non è sempre attiva** | diagnostica.md § *La modalità diagnostica* | medio | H1 | medio | — | ⚠ differenza visiva reale mai osservata |
| **H18** | Preferenze di trascinamento | `Consenti lo spostamento delle attività bloccate` · `Blocca le attività piazzate manualmente` · `Impedisci la sospensione delle attività bloccate` · `Nascondi le attività che non rientrano nella diagnostica` | diagnostica.md § *La modalità diagnostica* | banale | G4, H17 | medio | — | |
| **H19** | Legenda della griglia | `Risorsa in rosso` (occupata / occupata in attività bloccata), `Risorsa assente`, `Risorsa barrata`, `Risorsa in rosso +` (c'è altro da vedere), `Mezza giornata non lavorativa`, `Giorno festivo` | diagnostica.md § *La legenda della griglia* | banale (UI) | H2 | medio | — | |
| **H20** | Diagnostica sui **raggruppamenti** (`DiagnosticCliques`) | Avvisi quando un raggruppamento supera il massimo di ore e/o il limite dei pesi didattici, in forma aggregata o puntuale | diagnostica.md § *Diagnostica sui raggruppamenti* | medio | E5, raggruppamenti | basso-medio | ADR-013 | ⚠ non si sa in che punto del flusso compaia |
| **H21** | Tabella di coerenza (`FicCoherenceVariable`) | Matrice **risorse × famiglie di vincolo** con `Totale della settimana` e `Totale ciclo` | diagnostica.md § *La tabella di coerenza* | medio | H10 | medio | — | ⚠ **da chiarire se sia la vista dei risultati dell'analisi o uno strumento separato** |
| **H22** | *(nostro)* Riepilogo finale navigabile dell'analisi | EDT chiude con `Verifica terminata / Rimangono delle incoerenze` e **nessun riepilogo**: chi ha scorso dieci problemi non può rivederli. *"Un miglioramento facile e ovvio"* | diagnostica.md § *Come si chiude* | banale | H10 | medio | — | è una **lacuna di EDT**, non una sua feature |
| **H23** | *(nostro)* Ordinare i vincoli per numero di fallimenti causati | Il ponte mancante fra il fallimento di un calcolo e la scelta del rilassamento: *"le causali sono già nominate e contabili… e nessuno lo fa"* | diagnostica.md § *Cosa NON fa EDT* | medio | H1, D8 | **alto** — è l'occasione di prodotto identificata esplicitamente | — | è una **lacuna di EDT** |

---

## Nota trasversale sulle dipendenze

Tre righe di questo inventario sono **prerequisiti di massa**, e il loro costo va
imputato una volta sola ma pesato su tutto ciò che ne dipende:

- **A5** (disponibilità generica sulla risorsa) — da cui dipendono A1–A8, B13, G1, G2, H4, H7.
- **F9** (la mezza giornata come concetto di prima classe) — da cui dipendono
  B2, B5, B6, B8, C1, C4, C6, C10, D1, D2, D4, E2, F5, G8.
- **H10** (motore di analisi di capienza, separato dal solver) — da cui dipende
  l'intero gruppo H4–H12, H21, H22.

E una dipendenza **esterna** già decisa: **C9** e **E4** esistono solo perché
[ADR-013](../../docs/decisioni.md) ha messo gli sdoppiamenti in v1.
