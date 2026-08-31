# EDT — Il motore di risoluzione

> Due fonti in questo file. Le **enumerazioni RTTI** estratte da `EDT Monoposto.exe`
> (📦, autorevolezza media: i nomi sono certi, la semantica è inferita) e le
> **etichette di interfaccia** estratte da `EDT Monoposto.dll` (📦, 69 888 stringhe
> IT/FR/EN allineate per chiave). Le etichette sono più forti delle enum: sono il
> testo che l'utente legge, e la chiave dice in quale finestra compare. Vedi
> [ADR-009](../decisioni.md).
>
> ⚠ **Limite della fonte.** Il binario è **condiviso con PRONOTE**, il prodotto
> gemello di Index Education. Migliaia di stringhe riguardano registro elettronico,
> valutazioni, competenze e vita scolastica, e **non** sono funzionalità di EDT. In
> questo file compare solo ciò che è riconducibile a finestre EDT (chiavi
> `*EDT*`/`*Edt*`) o inequivocabilmente al piazzamento delle attività.

## Perché documentarlo

Non per copiarlo. Per **sapere cosa un motore maturo ritiene necessario** prima
di decidere cosa entra nel nostro v1 ([ADR-008](../decisioni.md)). EDT risolve lo
stesso problema da trent'anni: la struttura delle sue scelte è informazione, non
prescrizione.

Fino al 2026-07-26 questo file descriveva il motore **dall'interno** (fasi,
enumerazioni, classi di vincolo). Da qui in poi descrive anche il motore **come lo
vede l'utente**: i comandi, le finestre, i parametri. È la parte che conta di più
per un prodotto che vuole la stessa potenza con una UI migliore.

---

# Parte I — Il motore visto dall'utente

## Il menu `Elabora` (FR `Calcul`) — osservato in UI

**Osservato il 2026-07-26** sulla base di esempio. Il menu ha **quattro sezioni**,
con intestazioni in grassetto:

```
Analisi
    Lancia l'analisi dei vincoli
Piazzamento
    Lancia un piazzamento automatico            Ctrl+G
    Passa alla modalità diagnostica
    Trova una collocazione
    Cerca un'altra collocazione                    (grigia)
    Sospendi                                          ▸
    Metti in attesa le attività selezionate
Risoluzione
    Piazza le attività scartate
    Trova una soluzione...                            ▸
        ... spostando 1 attività          Ctrl+Shift+1
        ... spostando 2 attività          Ctrl+Shift+2
        ... spostando 3 attività          Ctrl+Shift+3
Ottimizzazione
    Ottimizza gli orari dei docenti
    Ottimizza gli orari delle classi
```

*(Trascrizione completata il 2026-07-26 su un secondo passaggio: la prima
osservazione aveva colto solo le voci di intestazione.)* Le voci aggiunte dicono
qualcosa sul modello:

- **`Trova una collocazione`** / **`Cerca un'altra collocazione`** sono due comandi
  distinti: il secondo è grigio finché l'attività non è già piazzata. Cioè *«dammi
  un posto»* e *«dammene un altro»* sono operazioni diverse.
- **`Metti in attesa`** materializza in un comando lo stato `In attesa`, uno dei
  quattro stati dell'attività ([diagnostica.md](diagnostica.md)).
- Il sottomenu di `Trova una soluzione...` è **la profondità della catena**:
  1, 2 o 3 spostamenti, con scorciatoia dedicata a ciascuna.

Cosa aggiunge l'osservazione rispetto alla ricostruzione dalle stringhe:

- 🔑 Esiste una sezione **`Analisi`** che non avevamo previsto, con
  **`Lancia l'analisi dei vincoli`** *prima* del piazzamento. È verosimilmente la
  finestra di coerenza descritta in [diagnostica.md](diagnostica.md): si analizza
  **prima** di calcolare.
- `Trova una soluzione...` ha un **sottomenu** (▸) — sono le varianti
  *«spostando 1 / 2 / 3 attività al massimo»*.
- Il piazzamento automatico ha una scorciatoia dedicata, **`Ctrl+G`**.
- `Piazza e sistema` **non è qui**: sta nel menu contestuale dell'attività.
- `Ottimizza le permanenze` e `Ottimizza i consigli` non compaiono in questo menu:
  appartengono ad altri moduli ([moduli-e-scope.md](moduli-e-scope.md)).

Le quattro sezioni corrispondono a **quattro momenti distinti** del lavoro:
analizza → piazza → risolvi ciò che è fallito → ottimizza. È la struttura da
riprodurre.

**Implicazione per noi.** La generazione non è un bottone. È una **cassetta di
attrezzi** che l'utente usa in sequenza: piazza tutto → risolvi i fallimenti →
sblocca a mano i casi duri → ottimizza. Un prodotto che espone solo "Genera" copre
il primo passo di cinque.

### Gli altri comandi del menu, che rivelano il modello

| Comando | Cosa rivela |
|---|---|
| `Rendi fissa` / `Rendi variabile` | l'attività ha una **fascia fissa o variabile** (vedi sotto) |
| `Blocca` (`Verrouiller à la même place`) / `Sblocca` | blocco sulla collocazione |
| `Sospendi` (`Dépositionner`) | togliere dall'orario senza cancellare |
| `Durata se possibile` | la durata è **desiderata, non imposta** |
| `Frequenza se possibile` | idem per la frequenza |
| `Periodi se possibile` | idem per i periodi |
| `Periodicità` (`Alternance`) | settimane A/B, quindicinali |
| `Coefficiente` (`Pondération`) | peso contabile dell'attività (→ TRMD, non piazzamento) |
| `Allinea le attività selezionate...` | costruzione dell'attività complessa dalla lista |
| `Trasforma le attività selezionate...` | riscrittura in blocco di durata/frequenza |
| `Estrai le attività non sufficientemente dettagliate per il piazzamento` | **controllo preventivo di piazzabilità** |

**`Durata se possibile` / `Frequenza se possibile` sono importanti**: contraddicono
la lettura "in EDT è tutto hard". Durata e frequenza di un'attività possono essere
dichiarate come **preferenze degradabili**. Il motore può accorciare o diradare
un'attività pur di piazzarla, se l'utente lo ha permesso su quella attività.

### Fascia fissa e fascia variabile

Testo letterale della finestra `FicAidePlacementCours`:

| Modo | Spiegazione (letterale) |
|---|---|
| **Fascia fissa** | *"L'attività si svolge tutte le settimane nella stessa collocazione"* |
| **Fascia fissa (ciclo)** | *"L'attività si svolge in tutti i cicli nella stessa collocazione"* |
| **Fascia variabile** | *"EDT può modificare la collocazione dell'attività a seconda dei periodi"* |

Cioè un'attività **variabile** non ha *una* collocazione: ne ha una **per periodo**.
Questo rompe l'ipotesi implicita del nostro prototipo, dove una lezione occupa uno
slot e basta. Vedi [tempo-e-calendario.md](tempo-e-calendario.md).

## Il piazzamento automatico

Finestra `Piazzamento automatico` (`FicheEDT_PlacementAuto`).

### Su cosa agisce — osservato in UI

⚠ **Correzione.** Una lettura precedente di questo file dava `Tutte le attività` ed
`Estratte` come **due opzioni alternative** da scegliere. È sbagliato: sono le
**due corone di un grafico ad anello**, e il piazzamento agisce *sempre e solo*
sull'estrazione corrente.

In testa alla finestra: *"%d attività da piazzare tra quelle estratte"*. Sotto, il
doppio anello con il conteggio per stato:

| Stato | Tutte le attività | Estratte |
|---|---|---|
| `Bloccate` | 8 | 0 |
| `Piazzate` | 976 | 21 |
| `Non piazzate` | 0 | 0 |
| `Scartate` | 0 | 0 |

Due cose degne di nota: `Bloccate` e `Piazzate` sono conteggi **disgiunti**
(8 + 976 = 984), e sono i quattro stati di `Type_EtatCours`
([diagnostica.md](diagnostica.md)) usati come categorie di un grafico.

🔑 **`Lancia il calcolo` è disabilitato** quando l'estrazione non contiene nulla da
piazzare. È la conferma più netta possibile che il perimetro **è** l'estrazione: non
un filtro opzionale, ma l'unico ingresso del motore.

**Implicazione per noi.** Il piazzamento incrementale su un sottoinsieme, con il
resto dell'orario congelato, non è un extra: in EDT è **l'unica modalità**. Il
modello deve accettare «risolvi queste 30 attività, le altre 250 sono date» come
caso normale, non come variante.

### Cosa mostra durante il calcolo

Indicatori di stato accesi/spenti — sono **famiglie di vincoli attivabili in blocco**:

- `Intervalli attivi` / `inattivi` (le ricreazioni)
- `Mensa attiva` / `non attiva` (la pausa pranzo)
- `Sedi distanti attive` / `non attive` (i cambi di sede)

E il progresso per fasi: `Ricerca di collocazioni` → `Da riclassificare`
(`Reclassement des cours`) → `Soluzione attività scartate (%d fasi)`, con
`Fase calcolo (%d / %d)`.

Un'opzione: **`Interrompi al primo scarto`**.

Al termine: *"Alcune attività (%d) non sono state piazzate."* seguito dal consiglio
letterale che indica il passo successivo:

> *"Utilizzate gli strumenti di risoluzione nel menu «Elabora > Risoluzione > Piazza
> le attività scartate». EDT cercherà delle soluzioni alle attività scartate
> attraverso calcoli più approfonditi."*

### 🔑 Il calcolo osservato mentre gira (2026-07-26)

Esperimento sulla base di esempio (984 attività tutte piazzate): **sospese le 27
attività della classe `1 A/R`** — cioè una classe intera tolta da un orario per il
resto pieno — ed estratte solo quelle. È l'istanza difficile, non quella facile:
reinserire in uno spazio saturo.

| Momento | Estratte piazzate | Totale base |
|---|---|---|
| `Fase calcolo (1 / 4)` | 13 / 27 | 962 |
| `Fase calcolo (2 / 4)` — 18% | 25 / 27 | 974 |
| fine | **27 / 27**, 0 scartate | 976 + 8 bloccate = 984 |

**Risultato: nessuno scarto, ~10–15 secondi.** Un secondo esperimento con **una
sola** attività da reinserire: ~2 secondi.

Tre cose da imitare:

1. **Le quattro fasi sono dichiarate mentre girano** (`Fase calcolo (n / 4)`), con
   percentuale *dentro* la fase e la ciambella dei conteggi aggiornata dal vivo.
   L'utente vede il progresso parziale, non una barra indeterminata.
2. **La prima passata piazza circa metà** e si ferma; il grosso lo fa la seconda.
   Non è un solver monolitico che parla solo alla fine.
3. `Lancia il calcolo` si trasforma in **`Interrompi`** e le opzioni si
   disabilitano: **il calcolo è interrompibile e ciò che ha già piazzato resta**.

Il conteggio `Bloccate 8` su 984 dice anche quanto si usa davvero il blocco in una
base reale: pochissimo, ma non zero.

### 🔑 `S.P.` e `Nr G.` — EDT espone la dimensione del dominio

Scoperta di rimbalzo dallo stesso esperimento, e vale più dell'esperimento. Due
colonne della lista attività, con tooltip letterale
(`UtilitairesEdt_ColonnesCours_RS_HintNbPlacesPossibles` /
`…HintNbJoursPossibles`):

| Colonna | FR | Tooltip |
|---|---|---|
| **`S.P.`** | `Nb. P.` | *«Numero di **fasce orarie possibili** per il piazzamento dell'attività **nel rispetto di tutti i vincoli**»* |
| **`Nr G.`** | `Nb. J.` | *«Numero di **giorni possibili** per l'attività nel rispetto di tutti i vincoli»* |

È **il dominio residuo della variabile**, calcolato per propagazione, messo in una
colonna ordinabile. Osservato sui dati:

- l'ora singola di LETTERE su `1 A/R`: `S.P. 21`, `Nr G. 5`;
- il blocco da **3h00** della stessa materia: `S.P. 6`, `Nr G. 3` — la durata
  stritola il dominio;
- la RELIGIONE **in compresenza**: `S.P. 4`, `Nr G. 2`, la più incastrata delle 27;
- le due ore con periodicità `Q1`/`Q2`: `S.P. 34`, `Nr G. 10`, perché vivono in due
  quadrimestri distinti.

**Ed è ricalcolato contro lo stato corrente**, non statico: con l'orario pieno e
una sola attività sospesa, quel blocco da 3h00 scendeva a **`S.P. 1`** — una sola
collocazione legale in tutta la settimana; e le altre attività dello stesso docente,
che a orario pieno stavano a `1`, salivano a `4` finché il buco restava aperto.

**Per noi.** Questa colonna è **gratuita**: è esattamente ciò che il solver calcola
comunque durante la propagazione. Esporla dà all'utente, *prima* di lanciare il
calcolo, la lista di cosa sta per diventare impiazzabile — basta ordinare per `S.P.`
crescente. Diagnostica preventiva a costo zero.

### Le opzioni e i parametri — osservati in UI

Tre indicatori di stato in chiaro, allineati: `Mensa attiva` · `Intervalli attivi` ·
`Sedi distanti attive`.

**`Opzioni`**

| | Opzione |
|---|---|
| ☐ | `Interrompi al primo scarto` |
| **☑** | **`Soluzione attività scartate (4 fasi)`** |
| ☐ | `Memorizza le attività che saranno spostate` |

🔑 La seconda è **spuntata di default**, ed è la scoperta di questa schermata: il
risolutore degli scarti **non è un comando separato che si lancia dopo**, è una
fase **annidata dentro** il piazzamento, attiva di serie, con un numero di passate
dichiarato (**4**). Il comando di menu `Piazza le attività scartate` serve a
rilanciarla da sola, con più controllo.

Questo spiega il messaggio già noto: *"Questo comando interrompe il piazzamento
delle attività scartate (l'attività resterà scartata). Volete anche interrompere
tutto il piazzamento automatico?"* — due processi annidati, due comandi di stop.

⚠ **Correzione (2026-07-26).** Avevo letto `Memorizza le attività che saranno
spostate` come un'opzione di tracciabilità — *«si tiene l'elenco di ciò che il
calcolo ha mosso»*. **È sbagliato, ed è colpa della traduzione italiana.** La stessa
chiave (`FicEDT_ResoluteurPasAPas_RS_CheckInit`) in francese dice:

> `Réinitialiser la famille des cours déplacés` — *reinizializza* la famiglia delle
> attività spostate.

Significato opposto: non memorizza, **azzera**. EDT tiene traccia di una «famiglia»
di attività già mosse (verosimilmente per non ri-muovere sempre le stesse), e questa
casella la resetta prima di ricominciare.

Promemoria di metodo: su questo prodotto **il francese è la lingua di riferimento**
e l'italiano è una traduzione che in qualche punto sbaglia. Quando IT e FR
divergono, vince FR. Vedi [glossario-it-fr.md](glossario-it-fr.md).

**`Parametri di calcolo`** — due voci, ciascuna con il proprio valore corrente:

- `Scelta della migliore collocazione - ` **`Personalizzato`**
- `Ordinamento dei criteri - ` **`Personalizzato`**

con frecce su/giù per scorrere e una **matita** per aprirne la modifica. Sono le
stesse due voci di `Parametri → Piazzamento automatico delle attività`
(`FicheEDT_ParametresBase_PlacementAuto`), raggiungibili anche da qui.

Che valgano entrambe `Personalizzato` (invece di `Default`) dice che la base di
esempio è stata messa a punto a mano: i criteri del produttore non sono quelli di
serie.

⚠ **Questo chiude un punto aperto.** Era l'ultimo posto in cui poteva nascondersi
`TContrainteItalieProfReglementaire`: non c'è. Vedi la Parte III.

## 🔑 La funzione obiettivo, esposta — osservata in UI

`Parametri → Piazzamento → Piazzamento automatico delle attività` (raggiungibile
anche dalla matita nella finestra di piazzamento). **Osservata il 2026-07-26.**

⚠ **Precisazione rispetto alla ricostruzione dalle stringhe.** Non c'è *una* lista
di criteri: ce ne sono **due meccanismi distinti**, in due riquadri della stessa
scheda.

| Riquadro | Cos'è |
|---|---|
| **`Scelta della migliore collocazione:`** | come si **misura** la qualità — interruttori e modalità |
| **`Ordinamento dei criteri`** | quali criteri si applicano e **in che ordine di priorità** |

Il secondo è quello che avevo descritto come «criteri considerati / ignorati»; il
primo è un insieme separato di impostazioni di misura. Vanno tenuti distinti.

### `Scelta della migliore collocazione` — come si misura la qualità

Valori osservati sulla base di esempio (entrambi i parametri erano su
`Personalizzato`, quindi **non sono i default del produttore** ma le scelte di chi
l'ha costruita — il che è più istruttivo):

**`Gestione dei buchi`**
- ☐ `Lascia i buchi di 1/2 ora`
- `Non conteggiare come buchi le ore libere prima o dopo la linea di fine mattinata:`
  - ☐ `per le classi`
  - **☑ `per i docenti`**

🔑 L'**asimmetria è deliberata**: la pausa pranzo non conta come buco per i docenti,
ma conta per le classi. Ha senso — un docente con l'ora libera a mezzogiorno pranza,
una classe con un'ora scoperta a metà giornata è un problema di sorveglianza.
È il tipo di sfumatura che un obiettivo unico e pesato non sa esprimere.

⚠ **E qui il nostro modello diverge, in un modo scoperto solo confrontando**
(2026-08-29, seconda osservazione dello stesso pannello: valori identici, il che
rende la fonte replicabile). Per EDT il buco si misura sulla **giornata**, e
questa casella ne *toglie* la pausa; da noi `MaxGapChecker` e il criterio `buchi`
lo misuravano **sempre e solo dentro la mezza giornata**, cioè si comportavano
come se la casella fosse spuntata — per **entrambe** le popolazioni. Sulla base
di esempio saremmo stati giusti sui docenti e sbagliati sulle classi. Non era un
difetto di implementazione: era un parametro che non avevamo.

✅ **Colmato il 2026-08-30 (L1)**: `InstituteSettings.gaps_split_at_lunch_*`, un
campo per popolazione, letto insieme dal checker, dal builder del D.T.B. e dal
criterio `gaps`. 🔑 **La casella e lo spezzare alla linea sono la stessa cosa**,
e non è un'assunzione: sulla giornata il buco è `ultima − prima + 1 −
conteggio`, e spezzarlo alla linea toglie esattamente le fasce libere fra
l'ultima occupata del mattino e la prima del pomeriggio — cioè, alla lettera, le
ore libere prima o dopo la linea. ⚠ Il default resta la mezza giornata per
entrambe (lo status quo), **non** quello di EDT: la scelta cambia la quantità di
un vincolo hard, quindi è della scuola. → debito in
[todo.md](../todo.md).

**`Raggruppa le attività`** — ◉ `All'inizio della giornata` / ○ `Dalla fine della mattinata`

**`Incompatibilità di materia su 2 giorni`**
- ☐ `Considera come consecutivi 2 giorni separati da giorni non lavorativi (es: venerdì e lunedì)`

**`Equilibra le giornate occupate`**
- ☑ `Distribuisci le attività sulla settimana per i docenti e le classi`

**`Attività quindicinale`** — le modalità dei massimi orari, in due blocchi separati:

| Su cosa | Opzioni |
|---|---|
| `Massimo di ore delle materie:` | ○ `Rispetta la media sulle 2 settimane - scarto massimo 30 min` · **◉ `Rispetta il massimo in ciascuna settimana`** |
| `Massimo di ore dei docenti e delle classi:` | idem, **◉ la seconda** |

Conferma delle **quattro modalità** dedotte dalle stringhe, con una precisazione:
compaiono **solo per le attività quindicinali**, cioè hanno senso unicamente quando
esistono settimane Q1/Q2 in cui la media può differire dal massimo puntuale. La base
di esempio sceglie in entrambi i casi l'opzione **stretta**.

Pulsante `Valori predefiniti` per ciascun riquadro.

### 🔑 `Ordinamento dei criteri` — la priorità è **lessicografica**

Due liste affiancate — `Criteri ignorati` (**vuota** in questa base) e
`Criteri considerati` — con i pulsanti `>>`, `<<`, `Tutto >`, `< Niente` per
spostare, **e frecce su/giù per riordinare**.

L'ordine è il punto. Non è una lista di cose da fare: è una **gerarchia di
priorità**. L'elenco completo osservato, nell'ordine:

| # | Criterio | Famiglia |
|---|---|---|
| 1 | `Ottimizza le fasce orarie libere` | buchi |
| 2 | `Riduci i buchi di mezza fascia oraria` | buchi |
| 3 | `Comincia dall'inizio delle fasce orarie intere` | allineamento |
| 4 | `Distribuisci nella settimana le attività della stessa materia` | distribuzione |
| 5 | `Riduci i buchi quindicinali` | buchi |
| 6 | `Riduci il numero di buchi` | buchi |
| 7 | `Equilibra i turni di mensa` | mensa |
| 8 | `Evita le attività della stessa materia nella stessa ora` | distribuzione |
| 9 | `Distanzia le attività della stessa materia` | distribuzione |
| 10 | `Favorisci le mezze giornate libere` | tempo libero |
| 11 | **`Rispetta le preferenze`** | preferenze |

Sono **undici**, e in questa base **tutti considerati** (`Criteri ignorati` vuota).

> 🧭 **Cosa ne abbiamo fatto** (decisione nostra, non osservazione):
> [ADR-025](../decisioni.md) ne traduce **due** — il 4 e l'8 — come criteri di
> qualità, oltre all'11 che lo era già. Gli altri otto restano fuori, ognuno
> col proprio motivo. Il ragionamento, criterio per criterio, sta in
> [criteri-di-piazzamento.md](../criteri-di-piazzamento.md). ⚠ Tradurne uno
> **cambia meccanismo**: qui governano un'euristica di ricerca, da noi
> diventano livelli di un'ottimizzazione lessicografica.

Quattro cose che l'ordine rivela e che nessuna stringa diceva:

- 🔑 **`Rispetta le preferenze` è ultimo.** È il pennello verde
  ([vincoli.md](vincoli.md)), e la sua posizione conferma alla lettera quanto
  documentato: *"EDT cerca di tenerne conto, nessuna garanzia"*. Le preferenze dei
  docenti cedono a **tutto** il resto. È una politica, ed è scritta in un posto
  dove la scuola può cambiarla.
- **I buchi occupano quattro degli undici posti** (1, 2, 5, 6) e presidiano la testa
  della classifica. Se c'è una cosa che questo motore ritiene importante, sono i
  buchi.
- **I buchi di mezza fascia stanno sopra il conteggio generale dei buchi** (2 contro
  6): un mezzo buco è considerato più fastidioso di un buco intero in più. Sensato —
  mezz'ora non serve a nulla.
- **Tre criteri distinti sulla distribuzione della stessa materia** (4, 8, 9):
  spargerla nella settimana, evitare che cada sempre alla stessa ora, distanziarne
  le occorrenze. Sono obiettivi diversi che si confondono facilmente in uno solo.

**Implicazione per noi, e chiude un ragionamento aperto.** Avevo scritto che EDT
esprime i compromessi come quote e mai come pesi. Ora si vede il meccanismo
completo, ed è a **tre livelli**, tutti privi di pesi:

| Livello | Meccanismo |
|---|---|
| vincoli | **hard**, rilassabili a **quota** (`Alleggerimenti`) |
| qualità | criteri in **ordine lessicografico** (`Ordinamento dei criteri`) |
| arbitraggio docenti ↔ classi | **perdita di qualità tollerata** |

Nessuno dei tre è una somma pesata. È una scelta coerente e, credo, giusta: i pesi
sono ingovernabili per l'utente (nessun vicepreside sa dire se un buco vale 3 o 5),
mentre un ordine di priorità si spiega in una frase. In CP-SAT si realizza con
ottimizzazione lessicografica — risolvi per il criterio 1, fissa quel valore come
vincolo, passa al 2 — non con `minimize(w1*a + w2*b)`.

| Criterio (IT) | Criterio (FR) | Note |
|---|---|---|
| **Gestione dei buchi** | `Gestion des trous` | separatamente `per i docenti` e `per le classi` |
| `Lascia i buchi di 1/2 ora` | `Laisser les trous d'1/2 heure` | |
| `Lascia i buchi di una 1/2 fascia oraria` | `Laisser les trous d'une 1/2 séquence` | |
| `Non conteggiare come buchi le ore libere prima o dopo la linea di fine mattinata` | `Ne pas compter comme des trous les plages libres autour de la mi-journée` | |
| **Raggruppa le attività** | `Regrouper les cours` | `All'inizio della giornata` \| `Dalla fine della mattinata` |
| **Equilibra le giornate occupate** | `Equilibrer les journées occupées` | |
| **Distribuisci le attività sulla settimana** (o `sul ciclo`) `per i docenti e le classi` | `Répartir les cours sur la semaine / le cycle` | |
| **Massimo di ore delle materie** | `Maxima horaires des matières` | |
| **Massimo di ore dei docenti e delle classi** | `Maxima horaires des professeurs et des classes` | |
| `Incompatibilità di materia su 2 giorni` | `Incompatibilité matière sur 2 jours` | |
| `Considera come consecutivi 2 giorni separati da giorni non lavorativi (es: venerdì e lunedì)` | | |
| `Attività quindicinale` · `Attività a cicli alternati` | `Cours en quinzaine` · `en cycles alternés` | |
| `Favorisci le attività sulla 1/2 ora` | `Favoriser les cours en 1/2 heure` | |

I massimi orari hanno **quattro modalità di applicazione** quando esistono settimane
A/B o cicli, e sono una lezione di modellazione:

| Modalità | Testo letterale |
|---|---|
| per settimana | `Rispetta il massimo in ciascuna settimana` |
| per ciclo | `Rispetta il massimo per ogni ciclo` |
| media su 2 settimane | `Rispetta la media sulle 2 settimane - scarto massimo 30 min` |
| media su 2 cicli | `Rispetta la media sui 2 cicli - scarto massimo 30 min` |

(con varianti `scarto massimo 1/2 fascia oraria` invece di 30 min)

**Implicazione per noi, forte.** Un massimo orario non è un numero: è un numero +
una **finestra di applicazione** + una **tolleranza**. Modellarlo come semplice
`<= max` per settimana perde tre delle quattro modalità.

**Implicazione di prodotto.** «Criteri considerati / ignorati» è una UI onesta:
dichiara che l'ottimizzazione è una scelta editoriale della scuola, non una verità.
Vale la pena copiarla come impostazione, migliorandone la presentazione.

## L'ottimizzazione

Comandi distinti per docenti e per classi
(`Ottimizza gli orari dei docenti` / `... delle classi`), coerentemente con
`TypeTypeOptim = ttoProfs, ttoClasses`: **EDT non cerca mai un ottimo congiunto**.

### Tre criteri, ordinati per priorità — osservati in UI

`Parametri → Piazzamento → Ottimizzazione degli orari`. **Osservato il 2026-07-26.**

Due riquadri, tre tendine ciascuno. Valori della base di esempio:

| | Orario delle **classi** | Orario dei **docenti** |
|---|---|---|
| **1** | `Equilibrio didattico` | `Durata totale dei buchi` |
| **2** | `Nessuno` | `Attività isolate` |
| **3** | `Nessuno` | `Nessuno` |

🔑 **L'asimmetria è la lezione.** Per le classi conta **una sola cosa**, la
regolarità (`Equilibrio didattico` = FR *Régularité des cours*, cioè la materia che
ricade sempre nella stessa fascia). Per i docenti contano **i buchi e le ore
isolate**.

È una distinzione vera, non un caso: gli studenti hanno bisogno di un ritmo
prevedibile e stanno comunque a scuola tutta la mattina, quindi i buchi non li
riguardano; i docenti vanno e vengono, e per loro un buco è tempo perso in
istituto. Un obiettivo unico applicato a entrambe le popolazioni sbaglierebbe
bersaglio su una delle due.

Che due slot su tre restino a `Nessuno` per le classi dice anche che **la
gerarchia non va riempita**: si dichiara ciò che conta davvero e si lascia libero il
resto.

I valori selezionabili (`AffEDT_ParametresOptimisation`) sono:

| Valore (IT) | Valore (FR) | Enum corrispondente |
|---|---|---|
| `Nessuno` | `Aucun` | — |
| `Durata totale dei buchi` | `Durée cumulée des trous` | `tcoTrous` |
| `1/2 giornate libere` | `1/2 journées libres` | `tcoDJLibres` |
| `Attività isolate` | `Cours isolés` | `tcoIsoles` |
| `Equilibrio didattico` | `Régularité des cours` | `tcoMemesHoraires` |

Le enum RTTI e le etichette UI **coincidono esattamente**: quattro criteri più
"nessuno". È una conferma incrociata fra due fonti indipendenti.

⚠ Nota di traduzione: `Régularité des cours` è reso in italiano `Equilibrio
didattico`, ma l'enum si chiama `tcoMemesHoraires` — *stessi orari*. Il senso
francese è la **regolarità settimanale** (la materia ricade sempre nella stessa
fascia), non l'equilibrio del carico. La traduzione italiana è fuorviante.

### La perdita di qualità tollerata

Due campi, letterali: `Perdita di qualità tollerata per le classi:` e
`... per i docenti:`.

⚠ **Non stanno in questa scheda dei parametri**: la scheda contiene solo le tre
priorità per popolazione. La perdita di qualità è un parametro **del singolo
lancio**, chiesto nella finestra di ottimizzazione al momento di eseguirla. Ha
senso: è una decisione contestuale («stavolta accetto di peggiorare le classi»),
non una politica d'istituto.

È il meccanismo che rende sensata la separazione docenti/classi: quando ottimizzi
per i docenti, dichiari **quanto sei disposto a peggiorare** l'orario delle classi.
Non è un peso in una somma: è un **vincolo di non-regressione con budget**.

**Implicazione per noi.** È lo stesso pattern dei rilassamenti (vedi sotto): EDT
esprime i compromessi come **quote**, mai come pesi. Un solver che mette tutto in
una funzione obiettivo pesata sta facendo una cosa diversa, e più difficile da
spiegare all'utente.

C'è anche un'**ottimizzazione individuale** (`FicheEDT_OptimIndividuelle`), su una
singola risorsa, con `Numero di ore di buco tollerate per questa risorsa`.

E un avvertimento letterale che vale come specifica:

> *"l'ottimizzazione tiene conto unicamente delle attività estratte (%d/%d) e le
> attività bloccate non possono essere ottimizzate (%d/%d)"*

## Il risolutore delle attività scartate

Finestra `Piazzamento automatico delle attività scartate` (`FicSolut`).

| Parametro | Valori |
|---|---|
| `Metodo di elaborazione` | `Standard` \| `Avanzato` |
| `Scegliete il livello di approfondimento:` | `1° livello` · `2° livello` · `3° livello` |
| `Includi le attività senza collocazione (%d)` | ☐ |
| `Ignora gli intervalli` | ☐ |
| `Piazza le attività anche sulle fasce orarie con indisponibilità opzionali...` | `dei docenti` · `delle classi` · `delle aule` · `dei materiali` · `del personale` |

Consiglio letterale del prodotto: *"Iniziate sempre con il metodo standard. In
seconda battuta, utilizzate il metodo avanzato"*. E, rivelatore del costo:
*"Il file viene salvato automaticamente ogni mezz'ora."*

Avanzamento: `Attività da piazzare` / `Attività trattate` / `Soluzioni trovate` /
`Senza soluzione`, per fasi successive, con `Riprendi la ricerca (fase %u)`.

🔑 **Le cinque risorse con indisponibilità opzionali sono: docenti, classi, aule,
materiali, personale.** Materiali e personale sono quindi **risorse di piazzamento
di prima classe**, non anagrafiche. Vedi [risorse.md](risorse.md).

## 🔑 Il risolutore passo-passo — la catena di spostamenti

`Trova una soluzione...` (`FicEDT_ResoluteurPasAPas`) è la funzione più interessante
del prodotto, e non l'avevamo mai vista.

L'utente sceglie un'attività scartata. EDT mostra una griglia in cui **ogni
collocazione è annotata**:

| Annotazione (letterale) | Significato |
|---|---|
| `in bianco, le collocazioni senza attività che creano problemi` | libera |
| `in grigio, le collocazioni che comportano lo spostamento di almeno un'altra attività` | occupata ma forzabile |
| `Collocazione senza vincolo` | |
| `Collocazione con %d vincoli` | |
| `%d attività da ricollocare` | costo in spostamenti |
| `Nessuna attività da sostituire` | costo zero |

E la ricerca si parametrizza in **profondità di catena**:

> `Trova una soluzione al massimo in uno step`
> `Trova una soluzione al massimo in %d step` (FR: *en %d coups au maximum*)

con le categorie `Attività da piazzare` · `Attività che creano problemi` ·
`Attività sospesa da piazzare` · `Attività piazzata / ricollocata`, e infine
`Conferma tutti gli step` (`Valider tous les coups`).

**È una ricerca a catena di espulsioni** (*ejection chain*): per piazzare A sposto
B, che sposta C, fino a profondità N. È una tecnica classica di ricerca locale, e
EDT la espone **all'utente** come strumento interattivo, mostrando il costo di ogni
mossa prima di eseguirla.

### 🔑🔑 Osservato in UI, end-to-end (2026-07-26)

Finestra `Trova una soluzione al massimo in 3 step`, lanciata su un blocco da
**3h00 di LETTERE** sospeso da un orario per il resto pieno.

**Tre pannelli affiancati**, e il layout è la cosa da rubare:

| Pannello | Contenuto |
|---|---|
| `Attività da piazzare` | la scheda della lezione: durata, materia, docente, classe — e il conto di **tutte e cinque le risorse** (`Personale 0`, `Aule 0`, `Materiali 0`, `Gruppi 0`, `Raggruppamenti 0`) |
| `Seleziona una fascia oraria` | la **griglia annotata**, astratta: solo colori, nessun testo |
| `Visualizzazione dell'orario di <docente>` | la settimana **reale** del docente, con le lezioni vere |

Cioè: la mappa delle decisioni **accanto** al contesto che le rende comprensibili.
Il prodotto lo dice pure, per non lasciare equivoci:

> *«L'orario è visualizzato a titolo indicativo, utilizzate la piccola griglia a
> sinistra per selezionare la collocazione desiderata»*

**La predizione del dominio ha tenuto.** L'attività aveva `S.P. = 1`, e la griglia
mostrava **una sola cella bianca** e tutto il resto grigio.

#### Il costo è dichiarato per nome, non per numero

Cliccando una cella grigia (venerdì 08h00–11h00), il riquadro `Attività che creano
problemi` si è popolato così:

```
Venerdì 08h00-09h00 - S MATEMATICA / RUBBIA C. / 1 A/R
Venerdì 09h00-10h00 - S LETTERE    / ARIOSTO L. / 1 A/R
Venerdì 10h00-11h00 - S LETTERE    / ARIOSTO L. / 1 A/R
```

Non «3 conflitti», non `INFEASIBLE`: **le tre lezioni con giorno, ora, materia,
docente e classe**. E fra queste una MATEMATICA di un *altro* docente — perché il
conflitto non passa dal docente ma dalla **classe**, che è occupata. La catena
attraversa le risorse.

Contemporaneamente, nel pannello di sinistra, **le risorse in conflitto diventano
rosse** (lì: il docente e la classe), mentre `Personale`, `Aule`, `Materiali`
restano nere. La finestra non dice solo *quanto* costa: dice **su quale delle cinque
risorse** si sta consumando.

#### La catena, confermata

Premuto `Piazza`, la finestra si è **riconfigurata attorno al passo successivo**:

```
Attività piazzata / ricollocata
    Venerdì 08h00-11h00 - S LETTERE / ARIOSTO L. / 1 A/R

Attività che creano problemi [1° step]
    Nessuna

Attività sospesa da piazzare
  ▶ Venerdì 08h00-09h00 - S MATEMATICA / RUBBIA C. / 1 A/R
    Venerdì 10h00-11h00 - S LETTERE    / ARIOSTO L. / 1 A/R
    Venerdì 09h00-10h00 - S LETTERE    / ARIOSTO L. / 1 A/R
```

Le tre scacciate sono diventate una **coda di lavoro con un cursore** (`▶`). Il
pannello di sinistra descrive ora `1h00 · MATEMATICA · RUBBIA Carlo`, la griglia
mostra **i suoi** slot possibili, e il pannello di destra è passato da solo a
`Visualizzazione dell'orario di RUBBIA C.`. Il titolo del riquadro porta ora
`[1° step]`: ogni passo resta etichettato, `Indietro` lo disfa, e il commit avviene
solo alla fine con `Conferma tutti gli step`.

**Il punto di prodotto.** L'algoritmo lo conoscevamo; la scoperta è che **è
esibibile**. Una ricerca a catena si può mostrare a un umano un nodo per volta e
resta comprensibile, perché a ogni nodo il costo è espresso in entità che l'utente
conosce — non in unità del solver. EDT non decide la catena: la propone, la costeggia
di nomi, e lascia scegliere, con ogni passo reversibile.

**Implicazione per noi, la più importante di questo documento.** Questa è la
funzione che rende usabile un generatore di orari nel mondo reale, perché nessun
orario esce perfetto dal calcolo di massa: il vicepreside vuole spostare *quella*
lezione *lì*, e vuole sapere cosa costa. Un solver CP-SAT che risponde solo
SAT/UNSAT non offre niente di paragonabile. Serve prevederlo nel modello fin
dall'inizio — è un'interrogazione del tipo *"qual è l'insieme minimo di attività da
spostare perché A stia in questo slot?"*, che si formula bene come problema di
ottimizzazione a sé (minimizzare il numero di variabili che cambiano valore
rispetto alla soluzione corrente).

## `Piazza e sistema`

Variante non interattiva della stessa idea (`FicheEDT_PlacerAmenagerAnnuel`).
Descrizione letterale:

> *"Permette di spostare l'attività selezionata in una posizione potenzialmente già
> occupata. Se ciò comporta lo spostamento di altre attività, queste verranno
> automaticamente ricollocate tenendo conto dei loro vincoli e delle opzioni di
> ricerca."*

Opzioni: `livello di ricerca` 1..N; `Ignora gli intervalli`; il consueto blocco
`indisponibilità opzionali` sulle cinque risorse; `Tieni conto degli alleggerimenti
definiti`; e soprattutto:

> ☐ *"Ignora i vincoli dell'attività selezionata (non saranno presi in
> considerazione nella ricerca di una collocazione e non verranno risolti)"*

Cioè: **l'utente può imporre una collocazione illegale e chiedere a EDT di
riparare il resto**. È il "lo so io, fallo e basta" — indispensabile in produzione.

Nota collaterale: il piazzamento può distruggere le **modifiche settimanali**
dell'orario (*"è stato necessario cancellare %d modifiche dell'orario per
settimana"*): l'orario annuale e le variazioni settimanali sono due strati distinti,
e il primo sovrascrive il secondo.

---

# Parte II — Il motore visto dall'interno

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
3. **Due modalità di risoluzione**, rapida e integrale — ora confermate in UI come
   i metodi `Standard` e `Avanzato` della finestra `FicSolut`.
4. Il nostro prototipo CP-SAT fa *tutto in una volta*. Funziona sul problema
   ridotto; su quello reale, la separazione trova/migliora è probabilmente
   necessaria — se non altro per dare risultati intermedi all'utente.

Le etichette confermano la struttura a **fasi ripetute** (`Fase calcolo (%d / %d)`,
`Riprendi la ricerca (fase %u)`): non è una pipeline percorsa una volta, è un ciclo.

## Si ottimizza per docenti **o** per classi, mai insieme

`TypeTypeOptim = ttoProfs, ttoClasses` — confermato in UI da due comandi di menu
distinti e da due pannelli di priorità distinti. I quattro criteri `TypeChoixOptim`
coincidono con i valori esposti all'utente (tabella nella Parte I).

**Implicazione per noi.** Se il nostro solver espone una funzione obiettivo unica
con pesi, stiamo facendo una cosa che EDT ha deliberatamente evitato. Il
sostituto di EDT per il compromesso non è il peso: è la **perdita di qualità
tollerata**.

## La strategia a due passate: rispetta tutto, poi alleggerisci

Testo letterale del prodotto (`FicAssouplissements`):

> `Il piazzamento delle attività scartate rispetta automaticamente tutti i
> vincoli. Se dopo un primo calcolo rimangono delle attività scartate, potete
> alleggerire certi vincoli. Attivate l'opzione "Alleggerisci" e sbloccate i
> vincoli che desiderate alleggerire. Potete parametrare ogni vincolo. Il calcolo
> cercherà delle nuove soluzioni tenendo conto degli alleggerimenti definiti.`

Il francese è più diretto: *"Par défaut le résoluteur automatique respecte toutes
les contraintes."*

### Confermato in UI (2026-07-26)

La finestra di creazione di un **vincolo fra attività** riporta, in una casella
**spuntata di default**:

> ✔ `Vincolo opzionale (può essere alleggerito durante il piazzamento delle
> attività scartate)`

⚠ Una sfumatura che corregge la lettura precedente: i vincoli fra attività
**nascono opzionali**, non hard. Il "tutto hard di default" vale per la famiglia
dei vincoli di risorsa, non universalmente. Vedi [vincoli.md](vincoli.md).

⚠ Una seconda sfumatura, dal menu `Elabora`: **`Durata se possibile`**,
**`Frequenza se possibile`** e **`Periodi se possibile`** sono dichiarazioni di
degradabilità **sull'attività**. Anche qui il "tutto hard" va ristretto.

### Quali vincoli EDT sa rilassare

La finestra `Alleggerimenti` è la dichiarazione ufficiale di cosa è rilassabile.
Elenco completo con il testo letterale dei parametri:

| Alleggerimento | Parametro |
|---|---|
| `Massimo di ore dei docenti` | `Autorizza un supplemento di …` `una volta per settimana e per docente` |
| `Massimo di ore delle classi` | `… una volta per settimana e per classe` |
| `Massimo di ore delle materie` | `… una volta per settimana e per classe` |
| `Presenza massima dei docenti` | `… una volta per settimana e per docente` |
| `Massimo 1/2 gg lavoro` (docenti e classi) | `Autorizza una volta per settimana …` `mattinate` / `pomeriggi di lavoro supplementari` |
| `Giorni e 1/2 giornate libere` | `Togli se necessario …` `mezze giornate libere per settimana` |
| `Gestione Entrate / Uscite` (docenti e classi) | `Togli se necessario …` `giornata ridotta per docente` |
| `Incompatibilità materie` | `Non considerare le incompatibilità … per settimana e per classe, una sola volta al giorno` |
| `Sequenze indesiderate di materie` | `Autorizza una sequenza indesiderata … per settimana e per classe, una sola volta al giorno` |
| **`Peso didattico delle materie`** | `Autorizza un supplemento di … un giorno per settimana` |
| `Cambi di sede` (docenti e classi) | `Autorizza … cambi di sede` (FR: *hors récréation/pause par semaine*) |

Più un tetto globale: **`Numero massimo di vincoli da alleggerire per risorsa:`**.

Ogni riga esiste anche in **variante per ciclo** (`una volta per ciclo e per
classe`), coerentemente con il modello del tempo.

Un'opzione fine: `Dettaglia le materie per classe` — l'alleggerimento delle
incompatibilità può essere mirato materia per materia.

### Il rilassamento è sempre a quota, mai a interruttore

Non esiste "spegni il vincolo". Istruzione letterale all'utente:

> `Sbloccate i vincoli da alleggerire e selezionateli per quantificare il margine
> di manovra concesso al calcolo`

**Implicazione per noi, importante.** Un vincolo rilassabile non diventa soft:
resta hard con una **quota di violazioni** limitata e attribuita (per risorsa,
per periodo). Nel modello CP-SAT questo si esprime con variabili di violazione
vincolate in somma, non con penalità nell'obiettivo. È una differenza sostanziale
di formulazione.

### 🔑 Chiuso: i «punti» non sono un punteggio

Era la riserva più seria su tutta questa lettura del motore. La finestra degli
alleggerimenti contiene le stringhe `punto` / `pesi` (FR `point` / `points`), unico
indizio di un punteggio numerico in un motore che altrove ragiona solo a quote.

**Chiuso da due ricerche indipendenti**, convergenti:

1. `FicAssouplissements_RS_Point` / `…_RS_Points` sono i **suffissi singolare e
   plurale di uno spinner**, fratelli di `Fois` / `Foiss` nella stessa famiglia di
   chiavi. Non sono un campo: sono l'unità di misura scritta accanto a un numero.
2. **La traduzione italiana di `points` è `pesi`.** Sono i punti di **peso
   didattico** — l'unica riga alleggeribile che non si misura né in ore né in
   occorrenze ([vincoli.md](vincoli.md)).

Il tetto globale della finestra lo conferma, ed è testuale: *«Numero massimo di
**vincoli** da alleggerire **per risorsa**»*. Su 69 888 stringhe, `punto/punti` in
contesto motore compare **solo qui** (l'altra occorrenza è «punto di ripristino», un
backup).

**Conclusione, ora senza riserve: in EDT non esiste alcuna funzione di costo
numerica.** I compromessi si governano su tre livelli — quote di violazione, criteri
ordinati lessicograficamente, priorità di ottimizzazione con perdita tollerata — e
nessuno dei tre è una somma pesata. Il nostro modello deve essere lessicografico.

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
`ContrainteMatiere`, `Site`.

Ha un corrispettivo in UI: il comando `Estrai le attività non sufficientemente
dettagliate per il piazzamento` (FR *"les cours dont les précisions ne permettent
pas le placement"*). È un **controllo preventivo**: prima di calcolare, EDT sa
dire quali attività non sono neppure candidabili. Da replicare: è un errore
utente frequente e diagnosticarlo a monte costa poco.

## L'assegnazione delle aule è un problema separato

Non fa parte del piazzamento: ha criteri propri (`TypeChoixOptimSalle`), le aule
si annidano (`dcsSousSalle`) e `TypeIncompatibiliteSalle` ha 11 valori. Esiste un
**ottimizzatore di aule** dedicato (`FicheEdt_OptimiseurSalles`, 30 stringhe) e una
`ripartizione delle aule` con l'opzione letterale *"Se possibile mantenendo le
assegnazioni della precedente ripartizione"* — cioè **stabilità rispetto alla
soluzione precedente**, un criterio che vale la pena ricordare.

**Implicazione per noi.** Assegnare le aule *dopo* aver piazzato le attività è
una semplificazione legittima, validata da un prodotto maturo — non una scorciatoia.
Il nostro v1 può farlo in due fasi senza sensi di colpa.

**Confermato in UI (2026-07-26)**, e il problema è più piccolo del previsto: la
finestra `Aule disponibili` dichiara **tre soli vincoli** rilassabili —
`Sedi distaccate`, `Indisponibilità opzionali`, `Indisponibilità`. Capienza,
categoria e tipologia dell'aula non sono vincoli. Vedi [aule.md](aule.md).

---

# Parte III — Il vincolo normativo italiano non esiste

Fra le ~90 classi `TContrainte*` dell'eseguibile ce n'è **una sola
paese-specifica italiana**: `TContrainteItalieProfReglementaire`.

**Verdetto: non ha alcuna interfaccia.** Tre ricerche indipendenti, tutte negative:

1. **Pannello vincoli del docente** (UI, base di esempio italiana): sette gruppi di
   vincoli, tutti generici.
2. **Intero menu `Parametri`** (UI): 28 voci su sei sezioni, nessuna
   paese-specifica.
3. **Tutte le 69 888 stringhe di interfaccia** (📦, 2026-07-26): nessuna etichetta
   nomina l'Italia in senso normativo. Le uniche occorrenze italiane sono
   `ExportInvalsi_IT` e `FicheImpNOT_Bulletin_IT` — entrambe di PRONOTE, entrambe
   sulle valutazioni. Le uniche soglie regolamentari nominate nel prodotto sono
   **francesi** (`Superamento dei plafond regolamentari (D. 2014-940 et 941)`, nella
   finestra TRMD).

Anche l'ultimo candidato è caduto: `Parametri → Piazzamento automatico delle
attività` contiene due sole voci, entrambe sui criteri.

**Conclusione operativa: non esiste un vincolo normativo italiano da replicare.**
Qualunque limite di legge sull'orario dei docenti va cercato nella normativa
italiana, non in EDT. La localizzazione italiana del prodotto è, dal punto di vista
del dominio normativo, un guscio: non incorpora nemmeno le classi di concorso
([discipline.md](discipline.md)).

⚠ Resta un'inferenza, per quanto ben supportata: un vincolo cablato **senza**
etichetta resterebbe invisibile a questo metodo. Ma un vincolo senza interfaccia è
per definizione un vincolo che l'utente non può configurare, quindi irrilevante per
il nostro catalogo di funzionalità.

---

## Il solver funziona anche senza registrazione — verificato

La stringa francese di primo avvio dichiara disabilitate, nella versione non
registrata, *"l'impression, les exports de données, le transfert assisté vers
PRONOTE hébergé, **la résolution et l'optimisation des emplois du temps**"*. La
traduzione italiana omette la clausola sul solver.

**Verificato in UI il 2026-07-26: ha ragione l'italiano.** Con la copia marcata
`Versione non registrata`, tutte le voci del menu `Elabora` sono **attive**, incluse
`Piazza le attività scartate` e le due `Ottimizza`. Nessuna è in grigio.

Il motore è quindi **osservabile** su questa macchina. La clausola francese
descrive presumibilmente un'altra edizione o una restrizione rimossa.

## Cosa NON si ricava da qui

- I **valori di default** dei parametri (soglie, livelli iniziali, criteri attivi
  di serie): sono dati, non tipi né etichette.
- L'**algoritmo** vero: sappiamo le fasi, i metodi e le euristiche per nome
  (`optHeuristiqueSolutionEchec`, `optIncNiveau1/2`), non cosa fanno. In
  particolare non sappiamo cosa distingua i tre `livelli di approfondimento`.
- ~~Il significato dei `punti` nella finestra degli alleggerimenti.~~ → chiuso: sono
  punti di **peso didattico**, non un punteggio del motore (vedi sopra).
- Se queste funzionalità siano tutte **attive nella distribuzione italiana**:
  `EDT Monoposto.distrib` contiene `PaysDistribution=ITALIE`, quindi esiste un
  filtro per paese che non è stato ispezionato.
