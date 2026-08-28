# Cose da fare

**Questo è l'unico elenco.** Ogni volta che una voce si apre o si chiude, si
aggiorna qui — non si aprono liste parallele in `CLAUDE.md` o in `scope-v1.md`,
che rimandano a questo file. Il *racconto* di come una voce è stata chiusa
resta in [changelog.md](changelog.md); qui resta una riga con la data.

**Come si legge una voce.** Ogni riga porta il tipo di risposta che aspetta,
perché è ciò che decide chi può muoverla:

| | Tipo | Chi la sblocca |
|---|---|---|
| 🧭 | **decisione** | una persona: cambia il prodotto o i dati che una scuola deve inserire |
| 👁 | **osservazione** | EDT: si guarda la UI e si scrive cosa fa |
| 🔧 | **lavoro** | nessuno: si può fare adesso |
| ⚖ | **debito dichiarato** | nessuno, ma è già stato deciso di non pagarlo: si riapre solo con un motivo nuovo |

Stato: `[ ]` aperta · `[~]` in corso · `[x]` chiusa (scende in fondo, con la data).

> **Stato al 2026-08-28.** Nessuna voce ✅ di [scope-v1.md](scope-v1.md) è
> rimasta senza implementazione: il motore, l'analisi, le due fasi, `Estrai`,
> `Piazza e sistema` e l'export iCal ci sono tutti. Ciò che resta non è codice
> mancante — è **una decisione di modello**, una **via d'ingresso dei dati** e
> quattro cose da guardare in EDT.

---

## 1. Decisioni — aspettano una persona

### D1 🧭 L'unità del monte ore: la parte o l'atomo?

**Blocca l'import**, perché cambia i dati che una scuola deve inserire.

`structural:coverage` misura ogni **parte** contro il piano **intero** della
parte: è una lettura *per alunno*, ed è quella giusta. Ma un alunno non sta in
una parte, sta in una **combinazione** di parti — una per partizione — cioè
l'**atomo** di [ADR-017](decisioni.md). Con una sola partizione parte e atomo
coincidono e tutto quadra; con due, o con una sola le cui parti ricevono
materie diverse — **IRC e alternativa, cioè ogni classe italiana** — la
copertura dichiara che chi fa religione deve l'ora di alternativa, e viceversa.

Misurato: **due** scostamenti inesistenti sulla classe più ordinaria che ci
sia, **quattro** su una 3A articolata con IRC. Tenuto fermo da
`test_l_unita_della_copertura_e_la_parte_dove_dovrebbe_essere_l_atomo`.

Tre strade, con i prezzi misurati in [scope-v1.md](scope-v1.md):

1. **portare la copertura sull'atomo** — il modello gli atomi li costruisce
   già, per l'occupazione, ma non hanno un piano di studi e derivarlo
   dall'unione dei piani delle parti sarebbe inventare un campo;
2. **un `StudyPlan` per combinazione** — misurato: funziona e azzera i finding,
   al prezzo di **quattro piani per una classe**, cioè gli atomi come
   anagrafica, che ADR-017 ha deciso di *non* fare;
3. **il monte ore tripartito** (`reduced_minutes`, `split_minutes`) — è la
   risposta di EDT alla stessa domanda, ma dipende da **O3**.

### D2 🧭 La via d'ingresso dei dati anagrafici

Da scegliere da quando `Partenaire_Index` è escluso
([ADR-012](decisioni.md)): formato nostro, CSV, o aggancio al SaaS di
sostituzioni già in produzione. ⚠ Da prendere **dopo D1**, che decide cosa c'è
da inserire.

### D3 🧭 La fase 1 resta cieca alle aule?

L'assegnazione delle aule è una **seconda fase**, ed è la forma del prodotto
(EDT ha un ottimizzatore dedicato). Il prezzo è misurato invece che previsto:
sul Fermi **92 richieste, 84 assegnate, 8 rinunce**, 39 celle contese, fino a 5
richieste su una sola cella — perché il piazzamento è cieco alle aule con più
di una candidata e §6 della spec dichiara fuori scope il ritorno indietro.

Si accetta come conseguenza dichiarata, o la fase 1 impara a contare le aule?
La seconda costa una famiglia di vincoli cumulativi in più nel modello grande.

### D4 🧭 Serve un'interfaccia?

Oggi il prodotto è un insieme di **management command** (`analyze`, `solve`,
`assign_rooms`, `place_and_fix`, `extract`, `export_ical`) e `config/` è un
progetto Django senza view. Non è una mancanza rispetto a `scope-v1.md` —
quel documento decide funzionalità, non consegna — ma è una domanda che non è
mai stata posta, e la risposta cambia D2.

---

## 2. Da osservare in EDT

### O1 👁 `TypeChoixOptimSalle` e `TypeIncompatibiliteSalle`

Di entrambi conosciamo il **nome** dalle stringhe (📦) e non i valori: il primo
sono i criteri con cui EDT sceglie *quale* aula fra le ammissibili, il secondo
la famiglia delle incompatibilità fra aule (11 valori). La nostra seconda fase
non implementa nessuno dei due — sceglie una candidata qualunque fra quelle
legali, con la sola preferenza per la ripartizione precedente. → `docs/edt/aule.md`

### O2 👁 La configurazione della griglia oraria

Durata delle fasce, ciclo, linea di mezza giornata: **mai osservata in UI**, ed
è la base su cui poggia tutto il resto — l'unica parte del modello del tempo
che conosciamo solo per via documentale. Riguarda anche le `SlotLabel`
dell'export iCal, che oggi sul Fermi sono **nostra scelta di dimensionamento**.
→ `docs/edt/tempo-e-calendario.md`

### O3 👁 La semantica del monte ore tripartito

`Ridotto` (*durata con alunni ridotti*) e `Sdop.` (*durata con alunni
sdoppiati*) sono nel nostro schema dal primo giorno (`reduced_minutes`,
`split_minutes`) e **letti da nessuno**. `piani-di-studi.md` li elenca fra le
cose da osservare: *«compilare Ridotto/Sdop. su un servizio per osservare come
nascono i gruppi»*. **Sblocca la strada 3 di D1.**

### O4 👁 Quali aule chiede ogni materia

Le aule **non esistono nella base del Fermi** (`NBSALLES = 0`), quindi
`data/liceo-fermi/aule.md` è progetto e non osservazione. Dal 2026-08-28 il
*nostro* dataset le ha (`tests/fermi.py`, `SPECIAL_ROOMS`) perché senza la
seconda fase avrebbe un problema vuoto — ma *quali* aule chieda ogni materia
resta nostra scelta di dimensionamento. → `docs/edt/aule.md`

### O5 👁 I dieci criteri di piazzamento non tradotti

In EDT i meccanismi sono due e confonderli era l'errore di partenza:
`Ordinamento dei criteri` è la lista degli **undici** criteri di *piazzamento*;
`Ottimizzazione degli orari` è una fase separata con **cinque** valori. Sono
implementati i quattro dell'ottimizzazione più `Rispetta le preferenze`, che è
l'undicesimo criterio di piazzamento. Gli altri **dieci** non sono tradotti, e
non è mai stato deciso se servano: prima vanno letti uno per uno.

---

## 3. Debiti dichiarati

Già decisi, e la decisione è stata «non adesso». Si riaprono con un motivo
nuovo, non per fastidio.

- ⚖ **L'oracolo differenziale perde il peggioramento** di una violazione già
  presente, per le famiglie che nominano il secchio invece del violatore: la
  chiave grossolana `(causale, risorsa, settimana)` non distingue «peggio» da
  «uguale». L'alternativa sarebbe riscrivere fuori dai checker la nozione di
  «quale numero è quello cattivo».
- ⚖ **Il testimone del banco resta sporco su `coverage_mismatch`**, per le
  maschere di settimana casuali. Riparazione quantificata (comprendere le
  maschere in coppie complementari, cioè riscrivere `_make_activities` e
  spostare ogni seme appuntato) e **dichiarata inutile**: `coverage_mismatch` è
  `PLACEMENT_INDEPENDENT`, quindi la differenza è vuota per costruzione.
- ⚖ **«Ignora i vincoli dell'attività selezionata»** di `Piazza e sistema`: da
  noi non è separabile per attività, perché i vincoli di A non sono *di* A. Una
  versione parziale sarebbe un modello mentale incoerente, peggiore
  dell'assenza.
- ⚖ **L'arbitrato non dice dove è atterrato** il criterio sacrificato: il
  rendiconto porta base e tetto, non il valore raggiunto. Costerebbe una
  seconda valutazione riappaiata per nome.
- ⚖ **La sostituzione non oscura l'originale** nell'export iCal: per
  [ADR-014](decisioni.md) il sostituto compare da sé, ma l'originale è annuale
  e continua a comparire nella stessa settimana — manca la relazione fra i due
  (`RELATIONCOURSSUBSTITUT` di EDT).
- ⚖ **Sei delle dodici voci del menu `Estrai`**, ognuna per una ragione scritta
  accanto al registro: tre riguardano la fascia variabile e il sezionamento
  (fuori per ADR-010), una la formazione classi, due sono filtri di forma e non
  problemi. E gli stati `Scartate` / `In attesa`, che sono sfumature di «non
  piazzata» che il modello non distingue.

---

## 4. Fuori scope, dichiarato

Deciso in [ADR-015](decisioni.md) e in [scope-v1.md](scope-v1.md). Qui solo
perché nessuno debba ricostruire *perché*.

- **Risolutore passo-passo interattivo** — fuori v1, ma la porta è rimasta
  aperta: la condizione 1 di ADR-015 è sciolta da `Piazza e sistema`, che è lo
  stesso motore.
- **Vincoli fra attività** (11 tipi): nella base del produttore quella griglia
  è vuota.
- **Sezionamento**, **alternanza docenti**, **fascia variabile** ([ADR-010](decisioni.md)).
- **Formazione classi** e tutto ciò che richiede l'anagrafica alunni nominativa;
  **multi-istituto**.
- **Mensa** come vincolo, **prenotazione** di aule e materiali, **incarichi** e
  loro effetto sul monte ore.
- **Import `Partenaire_Index`** ([ADR-012](decisioni.md)); **modulo
  sostituzioni** (il committente ce l'ha già). ⚠ Da recuperare però i due
  criteri di reclutamento non ovvi — *«chi ha già un buco lì»* e *«chi è stato
  liberato da un'assenza di classe»* — come nota per **l'altro** prodotto.
- **TRCD/TRMD**, IMP/PACTE e tutta la normativa francese; tutto ciò che è
  PRONOTE.

---

## Chiuse

Il racconto è in [changelog.md](changelog.md), alla data.

- [x] **2026-08-28** — La classe articolata regge (condizione 3 di ADR-015): la
      parte porta un piano proprio, la copertura lo legge, le due articolazioni
      sono simultanee. ⚠ Ha aperto **D1**.
- [x] **2026-08-28** — Il tie-break di `_placed_of` e il cambio di sede dentro
      una fascia: due artefatti dell'ordine d'inserimento, decisi in
      [ADR-019](decisioni.md).
- [x] **2026-08-28** — `Estrai`, `Piazza e sistema`, la classifica dei vincoli
      per fallimenti causati, l'assegnazione delle aule, l'export iCal.
- [x] **2026-08-26** — Il violatore di Hall (condizione 2 di ADR-015: l'analisi
      di capienza è un componente a sé) e gli alleggerimenti a quota con
      l'ottimizzazione lessicografica.
- [x] **2026-08-25** — Il modello CP-SAT hard completo: ventisei builder.
- [x] **2026-07-26** — L'osservazione di EDT, chiusa con
      [ADR-016](decisioni.md); il modello di dominio, approvato.
