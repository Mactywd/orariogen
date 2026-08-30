# Scope di v1 — proposta

> **Stato: le sei decisioni contese sono state prese** il 2026-07-26 e sono
> registrate in [ADR-015](decisioni.md). Il resto del documento è una proposta
> motivata, non ancora ratificata riga per riga: se una scelta appare sbagliata, si
> corregge qui e si aggiorna l'ADR.

Base di partenza: l'inventario delle funzionalità di EDT censite dalla
documentazione del progetto — **308 voci** in tre estrazioni indipendenti
(`docs/edt/estratti/inventario-*.md`), di cui **59 marcate `strutturale`**.

Questo documento non ripete l'inventario. Decide.

---

## I cinque criteri usati per decidere

Sono la parte da contestare per prima: se cambiano i criteri, cambiano le righe.

**1. Il metro è la scuola italiana media, non EDT.** L'obiettivo non è la parità
funzionale con un prodotto che ha trent'anni di sedimentazione, ma un generatore
che una scuola possa usare. Molte funzionalità di EDT esistono per il mercato
francese o per casi che in Italia non si presentano.

**2. La diagnostica prima dell'esaustività dei vincoli.** Su *numero di vincoli*
non si vince: EDT ne ha decine, tutti già scritti. Il divario che possiamo colmare
è **la spiegazione del fallimento**, ed è il tema su cui EDT stesso è più forte e i
concorrenti open source sono assenti. Quindi a parità di costo, **la diagnostica
passa davanti a un vincolo in più**.

**3. Le `strutturale` si decidono adesso, le `banale` si aggiungono sempre.** Una
funzionalità che cambia la forma del modello, se esclusa, poi non si aggiunge: si
riscrive. Una che è un campo o un vincolo lineare entra quando serve. Da cui la
regola asimmetrica: **nel dubbio su una `banale`, dentro; nel dubbio su una
`strutturale`, fuori** — ma dichiarando cosa si perde.

**4. Niente funzionalità che richiedono dati che non abbiamo.** Tutto ciò che
poggia sull'**anagrafica alunni nominativa** (formazione classi, riempimento dei
gruppi per nome, alunni dissociati) è fuori per mancanza di input, non per scelta.

**5. Fuori la normativa francese e tutto ciò che è PRONOTE.** TRCD/TRMD, IMP/PACTE,
RCD, comunicazioni, export ministeriali sulle valutazioni. Il confine è già
tracciato in [moduli-e-scope.md](edt/moduli-e-scope.md).

---

## Parte I — Le decisioni strutturali

Sono le uniche che è davvero necessario prendere ora.

### A. La forma dell'attività

| | Funzionalità | Proposta | Perché |
|---|---|---|---|
| ✅ | **Attività come unità di piazzamento** | dentro | è il progetto |
| ✅ | **Durata > 1 fascia** (blocchi di ore consecutive) | dentro | «due ore di laboratorio di fila» è ovvio per una scuola; e ha una conseguenza tecnica precisa: l'attività è un **intervallo**, non una cella — `IntervalVar` + `NoOverlap`, non booleani per slot |
| ✅ | **Maschera temporale sull'attività** (periodicità + `Amenagement` + sostituzione) | dentro | [ADR-014](decisioni.md). È ciò che unifica generatore e SaaS sostituzioni |
| ✅ | **Allineamento → attività complessa** | dentro | [ADR-013](decisioni.md). Nello XSD è l'allineamento a *generare* i gruppi, non il contrario: modellare i gruppi come anagrafica a monte andrebbe contro il prodotto |
| ❌ | **Sezionamento** (`S`/`SQ`/`SC`/`SP`, 7 codici) | fuori | fa variare la composizione dell'attività complessa per docente/quindicina/ciclo/periodo. Costo alto, uso raro |
| ❌ | **Alternanza docenti** (`A`/`AQ`/`AC`) | fuori | *«i docenti cambiano raggruppamento a metà dell'attività»*. Stesso motivo |
| ❌ | **Fascia variabile** (una collocazione per periodo) | fuori | [ADR-010](decisioni.md), già deciso |

### B. Le unità di piazzamento

| | Funzionalità | Proposta | Perché |
|---|---|---|---|
| ✅ | **Parte di classe** (IT «gruppo») | dentro | [ADR-013](decisioni.md). L'unità di piazzamento diventa *classe **o** parte*: ogni vincolo scritto su «classe» va scritto su «unità didattica» |
| ✅ | **Raggruppamento trasversale** | dentro | [ADR-013](decisioni.md), con il costo già messo a verbale: **accoppia classi diverse** e distrugge la decomposizione per classe |
| ✅ | **IRC / alternativa** come due parti (`_REL`/`_ALT`) | dentro | conseguenza gratuita delle parti — e serve: il peso didattico è **per alunno**, e senza le parti quel conteggio è sbagliato |
| ✅ | **Classe articolata** — **gestita con le parti di classe**, senza entità dedicata | dentro (per approssimazione) | esiste davvero in Italia (professionali, tecnici): la 3A con 12 alunni di Manutenzione e 10 di Elettronica. La copriamo con le **parti**: la parte A segue un piano, la parte B un altro, le ore comuni si insegnano a classe intera. ⚠ **Condizione tecnica**: le parti devono poter portare **un piano di studi proprio** — se il quadro orario resta agganciato solo alla classe, la scorciatoia non regge. Da verificare presto, non a modello finito |
| ❌ | **Multi-istituto** | fuori | già dichiarato |
| ❌ | **Formazione classi** | fuori | è un secondo problema di ottimizzazione, e richiede l'anagrafica alunni (criterio 4) |

### C. Le risorse

| | Funzionalità | Proposta | Perché |
|---|---|---|---|
| ✅ | **Disponibilità generica sulla risorsa** (una tabella per tutte) | dentro | prerequisito di massa: da qui dipendono ~15 righe dell'inventario. È la voce che, sbagliata, costa una riscrittura — e farla giusta **non costa di più** |
| ✅ | **Risorsa come concetto generico** (5 tipi) | dentro **come forma** | classi, docenti, aule, personale, materiali. La *forma* generica è gratis se la disponibilità è generica; personale e materiali restano **dati opzionali**, non richiesti per usare il prodotto |
| ✅ | **Capacità simultanea** (`Qtà`) | dentro | palestre e laboratori. Tecnicamente: da `NoOverlap` a vincolo **cumulativo**. È lo stesso meccanismo per aule e materiali — **una risorsa cumulativa sola**, non due tabelle |
| ✅ | **Assegnazione delle aule come problema separato** | dentro | EDT ha un ottimizzatore dedicato con criteri propri. Risolvere in due fasi è una semplificazione **validata da un prodotto maturo**, non una scorciatoia |
| ✅ | **L'aula è un'eccezione dichiarata** | dentro | su 27 attività di una classe, **una sola** ha un'aula. Il resto vive nell'`Aula preferenziale` della classe. Un modello che pretende un'aula per ogni lezione si inventa un problema che la scuola non ha |
| ✅ | **Sedi distaccate** — campo **+ regola di transizione semplice** | dentro | gli accorpamenti hanno reso il multi-plesso normale. Si entra nel merito: la `sede` sta sulle risorse e sull'attività, **e** c'è un vincolo di transizione — per cambiare plesso servono **N slot liberi in mezzo**, con `N` parametro unico d'istituto. È qui che si paga il costo strutturale vero: il ragionamento su **slot consecutivi**, forma che nessun altro vincolo dell'inventario richiede. Pagato quello, raffinare dopo costa poco.<br>**Fuori da v1**: matrice orientata dei tempi (A→B ≠ B→A), massimo cambi per giorno/settimana, cambio ammesso solo durante un intervallo |

### D. Il tempo

| | Funzionalità | Proposta | Perché |
|---|---|---|---|
| ✅ | **Mezza giornata come concetto di prima classe** | dentro | *«la granularità dei vincoli è la mezza giornata, non l'ora»*: ~25 righe dell'inventario si esprimono in giornate o mezze giornate. Non averla obbliga a riscrivere ogni vincolo di relazione |
| ✅ | **Periodi** (partizioni dell'anno) | dentro | necessari: [ADR-010](decisioni.md) rigenera l'orario **a ogni periodo**, quindi i periodi devono esistere anche senza la fascia variabile |
| ✅ | **Periodicità** (maschera di settimane) | dentro | richiesta da [ADR-014](decisioni.md) |
| ❌ | **Ciclo ≠ settimana** | fuori | nessuna base osservata lo usa; in Italia la settimana è l'unità |
| ❌ | **Suddivisioni sub-orarie** (fasce da 30′, 20′…) | fuori | **il produttore stesso la sconsiglia** (*«rende più complesso il calcolo dell'orario»*). Se una scuola ha ore da 50′, si modella con una griglia da 50′, non con le suddivisioni |
| ❌ | **Massimi orari a quattro modalità** (media su 2 settimane, ecc.) | fuori | compaiono solo con le attività quindicinali |

### E. Il motore e la diagnostica

Qui il criterio 2 pesa più che altrove.

| | Funzionalità | Proposta | Perché |
|---|---|---|---|
| ✅ | **Pipeline a tre stadi** (piazza → risolvi gli scarti → ottimizza) | dentro | è **il pattern architetturale del prodotto**, confermato su due domini indipendenti. Un prodotto che espone solo «Genera» copre il primo passo di tre |
| ✅ | **Ottimizzazione lessicografica, senza pesi** | dentro | quote di violazione + criteri ordinati + perdita tollerata. **Non** `minimize(w1*a + w2*b)`: è un'architettura diversa, e quella che funziona da trent'anni in questo dominio |
| ✅ | **Alleggerimenti a quota** | dentro | un vincolo rilassabile non diventa soft: resta hard con **un numero massimo di violazioni** attribuito per risorsa. In CP-SAT sono variabili di violazione vincolate in somma, non penalità nell'obiettivo |
| ✅ | **Ottimizza docenti *oppure* classi** | dentro | EDT non cerca mai l'ottimo congiunto. Vale la pena copiare la rinuncia: l'ottimo congiunto è più costoso e meno spiegabile |
| ✅ | **`Estrai`** — selezione di lavoro persistente | **implementata il 2026-08-28** (`domain/extraction.py`, `manage.py extract`) | **la voce con più dipendenze in entrata di tutto l'inventario**. È la risposta a *«rigenera solo il biennio»*, *«ripiazza solo quelle tre»* — e in EDT il motore opera **esclusivamente** sull'estrazione.<br>La regola con cui è stata implementata: un'estrazione **restringe ciò su cui si agisce, mai ciò che si conta** — fuori dal perimetro le attività restano dove sono e continuano a occupare. Onorata da `solve`, `analyze` e `assign_rooms` |
| ✅ | 🔑 **Analisi di capienza separata dal solver** | dentro | *«non serve un solver per dirlo: è un conteggio di capienza, si calcola in millisecondi»*. È **la funzione più preziosa trovata nel reverse engineering**, e va progettata come componente a sé fin dall'inizio — non come interpretazione a posteriori dell'output del solver |
| ✅ | **Causali nominate** | dentro | ~170 frasi intere invece di `INFEASIBLE`, riusabili quasi così come sono. Implica che **ogni vincolo del modello porti un'etichetta e una spiegazione** |
| ✅ | **Un orario invalido è uno stato ammesso** | dentro | la base demo ha 984/984 piazzate e **21 attività che violano i vincoli**. Implica: nessun vincolo di integrità sul DB, e **ogni vincolo esiste due volte** — come constraint del solver e come predicato valutabile su una soluzione data |
| ✅ | **Occupata-spostabile vs occupata-bloccata** | dentro | lo slot non è un booleano. È il perno di ogni riparazione |
| ✅ | **`Piazza e sistema`** | dentro | *«sposta l'attività in una posizione già occupata; se ciò comporta lo spostamento di altre attività, queste verranno automaticamente ricollocate»*. È il modo più economico di dare all'utente il potere di forzare |
| ❌ | **Risolutore passo-passo interattivo** (catena a N step, reversibile) | **fuori v1** | è la funzione più bella vista in EDT, ed esce a malincuore. `Piazza e sistema` copre il caso d'uso principale a una frazione del costo: l'utente ottiene comunque la lezione dove la vuole, semplicemente non sceglie il danno collaterale.<br>⚠ **Il prerequisito comune va previsto lo stesso**: il modello deve saper rispondere a *«qual è l'insieme minimo di attività da spostare perché A stia qui?»* — serve a `Piazza e sistema`, ed è ciò che rende riapribile questa decisione senza riscrivere |
| ❌ | **Ricerca di sottoinsiemi infattibili** (violatore di Hall) | **rimandato**, non escluso | è metà del valore dell'analisi, ma è ricerca combinatoria che CP-SAT non regala (l'UNSAT core è illeggibile: elenca vincoli interni, non persone e classi). Le fasi facili — capienza per risorsa, aritmetica per materia — coprono la maggior parte dei casi reali.<br>⚠ Il componente di analisi va progettato **per accoglierlo**: è il motivo per cui sta separato dal solver |
| ❌ | **Vincoli fra attività** (11 tipi, dichiarati a mano su coppie) | fuori | **decisione basata su evidenza**: nella base di esempio del produttore quella griglia è **vuota**. Costo strutturale (vincoli dato-driven fra oggetti arbitrari), uso reale osservato zero |
| ❌ | **Colloqui**, **consigli di classe** | fuori | moduli separati, con problemi di scheduling propri |

---

## Parte II — Il resto, per famiglie

Le voci non strutturali non richiedono una decisione riga per riga: seguono la
famiglia. Elenco quelle in cui la scelta non è ovvia.

### Dentro

- **I vincoli orari sulla risorsa** — massimo ore/giorno, entrate e uscite, giorni
  liberi garantiti, mezze giornate, buchi con soglia (`D.T.B.`). Sono la
  contrattazione sindacale reale, e valgono **sia per i docenti sia per le classi**
  (una tabella sola con riferimento polimorfico, non due).
- **I vincoli di materia** — con una priorità dichiarata: se se ne implementasse
  **uno solo**, sarebbe `Incompatibilità 1g` **della materia con sé stessa** (*«non
  due ore di arte lo stesso giorno»*), che nei dati reali è **15 righe su 19**.
  Poi `Max ore 1g`, poi la sequenza vietata.
- **Peso didattico** — [ADR-011](decisioni.md), con la riserva già registrata: nella
  base del produttore i pesi sono tutti a 1 e i tetti tutti a `nessuno`, cioè **la
  feature esiste e nessuno la usa**.
- **I rilevatori di problemi** — le query preconfezionate sull'orario esistente
  (*«cosa non è pronto per il calcolo»*, *«cosa nel mio orario è illegale»*, *«dove
  sgarro sul quadro orario»*). Costano poco e sono le domande che un vicepreside si
  pone davvero.
- **Le due lacune di EDT**, che sono la nostra occasione: il **riepilogo finale
  navigabile** dell'analisi (EDT chiude senza riepilogare nulla) e
  l'**ordinamento dei vincoli per numero di fallimenti causati** — il ponte mancante
  fra «il calcolo è fallito» e «quale vincolo allento».
- **La colonna `S.P.`** (dimensione del dominio residuo): il solver la calcola
  comunque durante la propagazione. Diagnostica preventiva **a costo zero**.
- **Export iCal** — **implementato il 2026-08-28** (`domain/ical.py`,
  `manage.py export_ical`): i docenti vogliono il proprio orario nel telefono.
  🔑 Ed è il punto in cui la **fascia di calcolo smette di essere l'ora**: un
  calendario legge l'**etichetta oraria** (`SlotLabel`, il `Place` dello XSD con
  `@LibelleHeureDebut`/`@LibelleHeureFin`), non `slot_minutes`. Senza etichette
  l'export **rifiuta** invece di indovinare le 8:00.
- I dati anagrafici e le loro conseguenze già decise: disciplina come tabella
  ([ADR-001](decisioni.md)), mappatura alle classi di concorso
  ([ADR-002](decisioni.md)), capacità ≠ assegnazione ([ADR-006](decisioni.md)),
  previsionali non memorizzati ([ADR-007](decisioni.md)), durate in **minuti**.

### Fuori

- **Mensa** come vincolo (`G. Mensa`, turni): rilevante per la primaria, non per
  il target.
- **Prenotazione di aule e materiali** (chi può prenotare, preavviso): è un modulo
  di booking, non di generazione.
- **Incarichi e loro effetto sul monte ore**: la formula è documentata e resta
  disponibile, ma è contabilità del personale.
- **Import `Partenaire_Index`** ([ADR-012](decisioni.md)), import EDT→EDT.
- **Modulo sostituzioni**: il committente ce l'ha già. ⚠ Da recuperare però i due
  criteri di reclutamento non ovvi — *«chi ha già un buco lì»* e *«chi è stato
  liberato da un'assenza di classe»* — come nota per **l'altro** prodotto.

---

## Parte III — Le sei decisioni prese

Decise il **2026-07-26**, registrate in [ADR-015](decisioni.md).

| | Decisione | Esito |
|---|---|---|
| 1 | Risolutore passo-passo interattivo | ❌ **fuori** — `Piazza e sistema` al suo posto |
| 2 | Sottoinsiemi infattibili (Hall) | ⏳ **rimandato** — analisi di capienza semplice in v1 |
| 3 | Sedi distaccate | ✅ **dentro**, campo + regola di transizione semplice |
| 4 | Classe articolata | ✅ **dentro**, gestita con le parti di classe |
| 5 | Personale e materiali | ✅ **dentro come forma**, dati non richiesti |
| 6 | Vincoli fra attività | ❌ **fuori** |

### Le tre condizioni da non perdere

Tre decisioni non sono autosufficienti: reggono solo se qualcosa viene previsto ora.

1. ✅ **Sciolta il 2026-08-28.** **`Piazza e sistema` richiede comunque** la
   domanda *«qual è l'insieme minimo di attività da spostare perché A stia
   qui?»*. È lo stesso motore del risolutore passo-passo escluso: prevederlo
   tiene quella porta aperta. → `domain/solver/place_and_fix.py`: la
   collocazione è un vincolo hard (`pinned`), il minimo è **L4** della catena
   lessicografica, e la risposta alla domanda è `PlaceAndFix.moved`. Sul Fermi
   pieno, **una** attività su 284. ⚠ Fuori, dichiarata: la casella «Ignora i
   vincoli dell'attività selezionata», che da noi non è separabile per
   attività.
2. **Rimandare Hall funziona solo se l'analisi di capienza è un componente a sé**,
   non un'interpretazione a posteriori dell'output del solver.
3. ⚠ **Verificata il 2026-08-28, e regge a metà.** **La classe articolata retta
   dalle parti** presuppone che una **parte** possa portare un **piano di studi
   proprio**. → `tests/test_classe_articolata.py`. La prima metà tiene, misurata:
   il piano proprio esiste, la **copertura lo legge**, le due articolazioni
   stanno **nella stessa fascia** (è ciò che la scorciatoia compra) e l'ora
   comune a classe intera **occupa** entrambe le parti. La decisione 4 non
   decade.
   ✅ **E la seconda metà regge dal 2026-08-28 (sera)**: l'unità della copertura
   era la **parte** dove doveva essere l'**atomo** di ADR-017, e il piano era
   letto come un curriculum quando è un **catalogo**. Corretti entrambi con
   [ADR-020](decisioni.md) — la copertura misura l'atomo, e le righe in
   alternativa sono un dato dichiarato. Misura: quattro scostamenti inesistenti
   su una classe sdoppiata due volte e due su ogni classe italiana, ora zero.

---

## Cosa resta davvero aperto

Non sono decisioni di scope, ma condizionano il lavoro che segue, e stanno
tutte in **[todo.md](todo.md)** — l'unico elenco, per non averne due che
divergono. In sintesi: **D2**, la via d'ingresso dei dati anagrafici; **D4**, il
confine con l'interfaccia. Più **una sola** osservazione ancora aperta in EDT —
il `Ciclo personalizzato` — e due esperimenti che nessun dato esistente può
sostituire.

⛔ **D3 — se la fase 1 debba smettere di essere cieca alle aule — è sciolta** il
2026-08-29 con [ADR-021](decisioni.md), e non era una decisione: era
un'osservazione già nel repo e letta male. In EDT le aule si **contano** mentre
si piazza; l'ottimizzatore dedicato sceglie soltanto *quale*. Sul Fermi le
richieste servite passano da **84 su 92** a **92 su 92**.

⛔ **D1 — l'unità del monte ore — è sciolta** il 2026-08-28 con
[ADR-020](decisioni.md), e con essa cade il blocco sull'import: ciò che una
scuola deve inserire in più è un'etichetta sulle righe in alternativa, non un
piano di studi per combinazione di parti.
