# EDT — I moduli, e cosa sta dentro o fuori dal nostro scope

> Fonte 📦: etichette di interfaccia dai binari (69 888 stringhe IT/FR/EN).
> ⚠ Binario condiviso con PRONOTE, il registro elettronico gemello: molte famiglie
> di stringhe (competenze, stage, bollettini, punizioni, vita scolastica) **non sono
> funzionalità di EDT**. Tracciare quel confine è metà del lavoro di questo file.

## Perché questo documento

Il catalogo delle funzionalità di EDT dev'essere **completo**, e completo significa
anche dire con chiarezza *cosa abbiamo deciso di non fare*. Una feature dimenticata
e una feature esclusa consapevolmente si assomigliano nel codice ma non nel
progetto: fra sei mesi solo la seconda è una decisione.

Ogni sezione chiude con una **proposta di scope**. Sono proposte, non decisioni
prese: le decisioni stanno in [decisioni.md](../decisioni.md).

---

## Gestione per settimana e assenze

Il modulo `Gestione per settimana e assenze` (FR *Gestion par semaine et
absences*): assenze, sostituzioni, modifiche puntuali dell'orario, statistiche.

**È il modulo più vicino al SaaS già in produzione del committente**, quindi vale
la pena guardarlo bene anche se non lo implementiamo.

### Due griglie sovrapposte

| | |
|---|---|
| `Orario della settimana` (`EDT à la semaine`) | la vista operativa, che **deriva** dall'orario annuale ma può divergere |
| `Orario per ciclo` | lo stesso su un ciclo |

Ogni settimana si può **ripristinare** all'orario annuale, e si può
`Bloccare automaticamente le settimane trascorse`.

🔑 È lo stesso meccanismo degli `Amenagement` descritto in
[tempo-e-calendario.md](tempo-e-calendario.md): **template ricorrente + istanza
modificabile, poi congelata**. Questa separazione ci serve comunque, a prescindere
dalle sostituzioni.

### 🔑 Come EDT sceglie un sostituto: non è un solver

Questo è il risultato più utile della sezione. **Non c'è ottimizzazione
combinatoria**: è un filtro multi-criterio su una lista, più un workflow di
richiesta/accettazione, con **assegnazione manuale finale**.

I criteri di filtro (`Cerca un docente tra:`):

| Criterio | Testo |
|---|---|
| disponibilità | `Disponibili per tutta la durata` (+ opzione «parzialmente disponibili») |
| materia | `Della stessa materia` |
| livello | `Dello stesso livello della classe` |
| team | `Dello stesso consiglio di classe` |
| sede | `Presenti nella sede dell'attività` / `alla sede più vicina` |
| incarico | `Solo docenti con ore residue d'incarico non assegnate` |
| bypass | `Ignora i vincoli` |

E modalità di reclutamento alternative, fra cui due interessanti:

- **`sostituti liberi che hanno un buco`** in quella fascia — riempire un buco
  esistente invece di spezzare un orario compatto;
- **`sostituti liberati da un'assenza della classe`** — il docente la cui classe è
  in gita diventa disponibile.

Più un sistema di **priorità a 3 livelli per docente × fascia oraria**, configurato
su una griglia strutturalmente identica a quella delle indisponibilità (terzo caso
di riuso dello stesso pattern UI rosso/giallo/verde).

E un workflow: proposta → `accettata` / `rifiutata` / `disponibile per una parte`,
con `Docente volontario per la sostituzione`.

**Nessun punteggio, nessuna funzione obiettivo.** A differenza dell'orario, dei
colloqui e dei consigli — che hanno tutti un risolutore vero — le sostituzioni no.

Distinzione utile: sotto una soglia configurabile di giorni la sostituzione è
**puntuale**; sopra diventa una **sostituzione lunga**, che genera un binario
parallelo di attività per il sostituto invece di rimpiazzare slot per slot.

### RCD — adempimento francese

`RCD` = *Remplacement de Courte Durée*. Una tassonomia che incrocia **chi** sorveglia
(docente interno/esterno, assistente educativo, nessuno — *alunni in autonomia*, il
docente stesso che recupera altrove) con **cosa fa** (niente, altra attività, lezione
di altra materia, stessa materia, sequenza digitale, studio assistito).

Alimenta solo statistiche ed esportazioni ministeriali francesi. Nessun equivalente
noto nella normativa italiana.

> **Proposta di scope: FUORI.** Il committente ha già il prodotto. EDT qui non offre
> tecnologia di scheduling da recuperare — offre una **checklist di criteri di
> filtro** che potrebbe arricchire il SaaS esistente (in particolare «chi ha già un
> buco lì» e «chi è stato liberato da un'assenza di classe»). Utile come nota per
> l'altro prodotto, non per il generatore.

---

## Colloqui genitori/docenti

Un **vero problema di scheduling con risolutore dedicato**.

Una `Sessione colloqui` definisce: durata di default del colloquio (con minimo e
massimo), raddoppio automatico per il coordinatore, finestra di raccolta delle
preferenze, data di pubblicazione.

Ogni partecipante esprime **desiderata**, con semantica a semaforo:

> *"I colloqui saranno creati solo quando i desiderata dei partecipanti producono
> una spunta verde"*

— quarto riuso dello stesso pattern UI.

I colloqui hanno una priorità propria: `Colloquio prioritario` / `desiderato` /
`facoltativo`.

Il risolutore (`FicResoluteurRencontres`) è, nello spirito, identico a quello
dell'orario: multi-fase, `Lancia la ricerca di soluzioni`, contatori
`elaborati` / `senza soluzione`, interruzione e ripresa, e la stessa modalità
`Utilizzo esclusivo` durante il calcolo.

> **Proposta di scope: FUORI da v1, ma vale come riferimento di architettura.** È
> scheduling vero, ma di un dominio diverso (eventi in sessione, non ricorrenza
> settimanale). Se un giorno il committente lo vorrà, si riparte da qui.

---

## Consigli di classe

Stesso quadro, e con una prova architetturale importante: il motore è a **tre stadi
separati**, con tre finestre distinte —

1. `Piazzamento automatico dei consigli`
2. `Ricerca soluzione per i consigli scartati`
3. `Ottimizza i consigli`

🔑 È **esattamente lo stesso schema a tre stadi** dell'orario (piazza → risolvi gli
scarti → ottimizza), riapplicato pari pari a un dominio diverso. Conferma che non è
una scelta specifica dell'orario: è il **pattern architetturale del prodotto**.

Anche gli stati coincidono: `Piazzati` / `Non piazzati` / `Scarti` / `Bloccati` /
`Estratti`, con `Interrompi al primo scarto`.

L'ottimizzatore usa **tre criteri ordinati** e riporta `Numero di sostituzioni` e
`Numero di sovrapposizioni di consigli`: l'obiettivo dichiarato è **minimizzare le
sovrapposizioni fra consigli** (un docente non può stare in due consigli insieme),
con l'opzione `Sovrapponi i consigli dei docenti non indispensabili`.

> **Proposta di scope: FUORI.** Ma il pattern a tre stadi, confermato su due domini
> indipendenti, è un argomento forte per adottarlo anche noi.

---

## Comunicazioni

Dati di contatto e canali (email, telefono, SMS). Infrastruttura anagrafica di
PRONOTE.

> **Proposta di scope: FUORI.** Nessun contenuto di scheduling.

---

## 🔑 `Estrai` — la selezione di lavoro

Non è un filtro di visualizzazione. È una **selezione persistente, nominata e
componibile** su cui operano tutte le azioni successive.

Tre proprietà osservate:

**1. Criteri combinabili.** Sull'estrazione delle attività:

| Asse | Valori |
|---|---|
| stato | `Piazzate` · `Non piazzate` · `Scartate` · `In attesa` · `Bloccate` · `Fisse` · `Variabili` |
| collocazione | `Interamente nella fascia` · `Parzialmente nella fascia` |
| conformità | **`Attività che non rispetta i vincoli`** |
| risorse | classi · docenti · aule · materiali · personale · sedi · incarichi |
| proprietà | `Durata` · `Frequenza` · `Coefficiente` · `Alunni dissociati` |

**2. Composabilità cumulativa.** Ogni estrazione espone
`Limita la ricerca alle attività già estratte` — si raffina progressivamente un
insieme, come una query incrementale con stato.

**3. Le azioni operano solo lì.** Letterale: *"%d attività da piazzare tra quelle
estratte"*, e per i consigli *"l'ottimizzazione tiene conto solo dei consigli
piazzati estratti"*.

### Il menu `Estrai` sulle attività — osservato in UI

**Osservato il 2026-07-26.** Il menu cambia contenuto secondo la scheda attiva
(estrae la risorsa che si sta guardando) ed è disabilitato su `Materie`. Sulla
scheda `Attività` contiene **26 voci**.

**Operazioni insiemistiche** — `Definisci un'estrazione` (`Ctrl+E`),
`Estrai tutto` (`Ctrl+T`), `Estrai la selezione` (`Ctrl+X`),
`Aggiungi all'estrazione`, `Togli la selezione`,
`Estrai le risorse delle attività selezionate` (`Ctrl+U`),
`Estrai le attività previste per le classi e i raggruppamenti della selezione`.

🔑 **Estrazioni salvate e richiamabili** — quattro voci con sottomenu:
`Memorizza le attività estratte` · `Richiama un elenco di attività` ·
`Aggiungi l'estrazione` · `Togli l'estrazione`.

Conferma rafforzata dell'ipotesi: la selezione non è solo persistente, è
**nominabile, salvabile e ricombinabile** (unione e differenza fra insiemi salvati).
È una struttura dati di prima classe, non uno stato di UI.

#### 🔑 I rilevatori di problemi

Dodici voci sono **controlli di qualità preconfezionati**. Vale la pena riprodurre
l'elenco così com'è: è la checklist di ciò che, in trent'anni, si è rivelato utile
saper trovare in fretta.

| Comando | Cosa individua |
|---|---|
| `Estrai le attività non sufficientemente dettagliate per il piazzamento` | attività non ancora candidabili al calcolo |
| `Estrai le attività non sufficientemente dettagliate per la stampa` | idem, per l'output |
| **`Estrai le attività che non rispettano i vincoli`** | l'orario esistente viola dei vincoli |
| `Estrai le attività non conformi ai piani di studi di EDT` | scostamento dal quadro orario |
| `Estrai le attività con problemi di aule` | |
| `Estrai le attività con problemi di sede` | |
| `Estrai le attività a cavallo dell'intervallo` | violano `Rispetta gli intervalli` |
| `Estrai le attività non costanti durante l'anno` | cambiano fra i periodi |
| `Estrai le attività sezionate asincrone` | parti scoordinate |
| `Estrai le attività spostate` | divergono dall'orario annuale (gli `Amenagement`) |
| `Estrai le attività con raggruppamenti ad alunni variabili` | i gruppi GAEV |
| `Estrai le attività complesse` / `di compresenza` / `con almeno un incarico` | per tipologia |

**Per noi.** Ognuna di queste è una query sul modello, non una funzione del solver.
Costano poco e valgono molto: sono le domande che un vicepreside si pone davvero.
Le prime quattro in particolare — *«cosa non è pronto per il calcolo»*, *«cosa nel
mio orario è illegale»*, *«dove sto sgarrando sul quadro orario»* — sono
essenzialmente gratuite una volta che il modello esiste.

### Le colonne della lista attività

Osservate nella stessa schermata, utili come conferma del modello:
`Durata` · `Giorno` · **`P.P.`** · `Freq.` · `Stato` · **`S.P.`** · **`Nr G.`** ·
`Sezion.` · `Docente` · `Materia` · `Modalità di scelta` · `Classe` ·
`Sett. App.` · `Alu.` · `Nr A.` · `Aula` · `Sede` · `Int.` · `Periodicità` ·
`Compr.` · `Coeff.` · `Alu. Var.` · `Tipologia`.

Quattro sigle sciolte 📦 (le prime due sono **scoperte**, non conferme):

| Colonna | Chiave / FR | Significato |
|---|---|---|
| **`S.P.`** | `NbPlacesLibresCourt` / `Nb. P.` | *«Numero di fasce orarie possibili per il piazzamento dell'attività nel rispetto di tutti i vincoli»* — **la dimensione del dominio**, vedi [motore-risoluzione.md](motore-risoluzione.md) |
| **`Nr G.`** | `NbJoursLibresCourt` / `Nb. J.` | *«Numero di giorni possibili per l'attività nel rispetto di tutti i vincoli»* |
| **`P.P.`** | `FractionnableCourt` / `P.P.` (EN `P.F.`) | **Proprietà di Piazzamento**: *«influisce sulla collocazione dell'attività: fissa o variabile»* — il badge `F` è `Fascia fissa`, ed è il default |
| **`Int.`** | `InterclasseLong` / `Récréation` | **Intervallo** — falso amico, vedi [vincoli.md](vincoli.md) |

⚠ Su `P.P.` la premessa era doppiamente sbagliata. Non sono due colonne `P.P.` e
`P.F.`: è **la stessa colonna in due lingue** (IT/FR `P.P.`, EN `P.F.`). E non
significa «Parte Principale/Finale»: è `Fractionnable`, cioè il nome interno di
`Fascia fissa` / `Fascia variabile` già documentato in
[tempo-e-calendario.md](tempo-e-calendario.md) — **non è un vincolo nuovo**, è la
feature esclusa da [ADR-010](../decisioni.md).

E c'è una distinzione che l'italiano fa e il francese no: **frazionare** (spezzare
sui *periodi*, questa colonna) contro **sezionare** (spezzare la *durata*, cioè lo
spezzamento padre/figlio di [attivita.md](attivita.md)). Due meccanismi diversi con
nomi vicini. ⚠ Terza collisione di sigla: `Type_Contrainte_RS_LegendePP` è
`Peso didatt.`, un altro `PP` ancora.

Due valori istruttivi:

- **`Periodicità = 42`** su tutte le attività della base. È il **numeratore** del
  modello numeratore/denominatore ([tempo-e-calendario.md](tempo-e-calendario.md)):
  42 settimane su 42, cioè «ogni settimana». Conferma diretta che la periodicità
  è un conteggio, non un'etichetta.
- **`Coeff. = 60/60`** — il coefficiente (FR *pondération*) è una **frazione di
  minuti**, non un numero puro. È il `Durata/Coeff.` della formula delle ore
  supplementari ([risorse.md](risorse.md)): serve a contare un'ora di lezione come
  più o meno di un'ora di servizio.

In fondo alla finestra: `984 / 984 (1.371h00 / 1.371h00)` — la base ha **1 371 ore**
di lezione — e la barra dei periodi `Anno completo | Quadrimestre 1 | Quadrimestre 2`
con il righello delle settimane colorato per quadrimestre.

**Perché conta per noi.** EDT non ha una UI «seleziona → agisci» separata per ogni
azione: ha **una primitiva di selezione condivisa**. Per il nostro prodotto è la
risposta a richieste concrete e frequenti — *«rigenera solo il biennio»*,
*«ottimizza solo il sostegno»*, *«ripiazza solo quelle tre lezioni»* — senza
toccare il resto dell'orario.

> **Proposta di scope: DENTRO, come pattern.** Non serve replicare la finestra: serve
> che il modello accetti «risolvi questo sottoinsieme, il resto è dato».

---

## Importazioni ed esportazioni

L'ecosistema è **dominato dai sistemi ministeriali francesi**: SIECLE, STS-Web,
Cyclades, Parcoursup, LSU/LSL, Sconet.

Il blocco italiano esiste ma è piccolo e isolato: `Esportazione frequenze`,
`Scrutini Finali Analitici`, `Esami di Stato Crediti Scolastici`,
`Esami di Stato Piani Orario`, `Esiti Finali`, più SIDI e INVALSI. Sono flussi
verso il MIM, e riguardano il **registro elettronico**, non l'orario.

Per l'orario in senso stretto:

| Formato | Cosa | Valore per noi |
|---|---|---|
| `Importazione degli orari` | **EDT → EDT**, proprietario, con opzioni di merge (`sostituisci` / `aggiungi` / priorità in caso di conflitto) | nullo senza EDT |
| `Esportazione ASCII` | tabellare/CSV, opzioni granulari | export di servizio |
| **iCal** | in tre punti indipendenti (orario, colloqui, consigli) | 🔑 **utile in uscita**, costo basso |
| **`Partenaire_Index`** | lo XSD già documentato, qui confermato come «standard» di scambio verso applicativi partner | il candidato serio |

Nota: che `Partenaire_Index` compaia nel prodotto come
`Esportazione standard partner` conferma che non è un artefatto trovato per caso
nell'installazione, ma **il formato di scambio dichiarato** di Index Education.

> **Proposta di scope.** Import: `Partenaire_Index` resta l'unico candidato serio
> (decisione già in sospeso, vedi [schema-scambio.md](schema-scambio.md)).
> Export: **iCal è dentro**, indipendentemente da tutto il resto — i docenti vogliono
> il proprio orario nel telefono, costa poco e si vede subito.

---

## Riepilogo

| Modulo | È scheduling? | Ha un solver? | Proposta |
|---|---|---|---|
| **Orario** | sì | sì, a 3 stadi | **il nostro dominio** |
| Gestione per settimana e assenze | in parte | **no** — filtro + workflow | fuori (già coperto dal SaaS) |
| Colloqui genitori/docenti | sì | sì | fuori da v1 |
| Consigli di classe | sì | sì, a 3 stadi | fuori |
| Comunicazioni | no | no | fuori |
| `Estrai` | — | — | **dentro, come pattern** |
| Import/export | — | — | `Partenaire_Index` in ingresso (da decidere), iCal in uscita |

Un'osservazione trasversale che vale più delle singole righe: **lo stesso motore a
tre stadi e lo stesso pattern di selezione compaiono in tre domini diversi**. EDT non
ha un generatore di orari: ha un *framework di piazzamento* di cui l'orario è
un'istanza. Non dobbiamo copiarlo — ma se un giorno vorremo aggiungere i colloqui, la
differenza fra averlo previsto e non averlo previsto sarà tutta lì.
