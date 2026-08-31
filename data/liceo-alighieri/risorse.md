# Risorse, peso didattico e indisponibilità — l'ondata 5

Tre famiglie in un'ondata sola, e stanno insieme per una ragione aritmetica:
sono **tutto ciò che mancava** perché la sonda arrivasse al registro intero.
Dopo l'ondata 4 restavano due builder senza dati — `structural:unavailability`
e `structural:didactic_weight` — e due delle cinque risorse di piazzamento che
nessun dataset del progetto aveva mai avuto: il **personale** e i
**materiali**.

Esito: **27 builder su 27**, che è il criterio di accettazione della spec (§6),
raggiunto all'ondata 5 invece che alla 7.

---

## 1. Le indisponibilità — sei righe, tre livelli, tre tipi di risorsa

Il meccanismo rosso / giallo / verde è **generico sulla risorsa**
(`docs/edt/vincoli.md`): la stessa tabella vale per docenti, classi e aule. Un
dataset che le mettesse solo sui docenti non lo mostrerebbe, quindi le sei
righe si distribuiscono apposta.

| Riga | Livello | Portatore | Celle | Perché lì |
|---|---|---|---|---|
| `ricci` | 🔴 rossa | docente **I01** Ricci | tutte tranne mer 14–17 | lo **spezzone**: tre ore, un pomeriggio |
| `orientamento` | 🔴 rossa | classe **5A** | mer 14–17 | la classe non c'è |
| `palestra` | 🔴 rossa | aula **PALESTRA** | lun 08–13 | concessa alla scuola media |
| `permesso` | 🟡 gialla | docente **M04** Sartori | ven 14–17 | il permesso settimanale |
| `manutenzione` | 🟡 gialla | aula **LAB-SUCC** | lun 08–10 | la manutenzione del laboratorio |
| `preferenza` | 🟢 verde | docente **L01** Amato | la prima ora, tutti i giorni | non la vorrebbe |

### 🔑 I tre livelli non fanno la stessa cosa, e si provano in tre modi diversi

Questa è la sostanza della prima metà dell'ondata. Tre affermazioni, tre test:

- **la rossa vieta.** Testimone puntato (ondata 4): si impone la cella
  vietata, `INFEASIBLE` con la riga e `OPTIMAL` a zero scarti senza. Su due
  tipi di risorsa diversi — una classe e un'aula — con lo stesso identico
  contratto: è ciò che significa *«generico sulla risorsa»*.
- **la gialla vieta finché non la si autorizza.** Stesso testimone, più
  l'override. E l'override è **per tipo di risorsa**, mai per la singola riga
  (A4): autorizzare i docenti non tocca la gialla dell'aula, e viceversa. Le
  due righe gialle sono su due categorie diverse apposta, perché è l'unico
  modo di distinguere «per categoria» da «per riga» avendone una per
  categoria.
- **la verde non vieta.** Contro-testimone: si impone la cella *preferita
  libera* e si pretende `OPTIMAL`. Se un giorno restringesse, quel test
  diventerebbe rosso — ed è il verso giusto, perché sarebbe il solver a farsi
  più severo di EDT.

⚠ **Il meccanismo è un pre-filtro del dominio, non un constraint**, e si vede
dall'esterno: la cella sparisce prima che il modello nasca, quindi il pin
finisce **fuori dominio** e il solver lo dichiara (`pin_fuori_dominio`). I
test lo asseriscono, così il giorno in cui l'indisponibilità diventasse un
vincolo postato lo si saprebbe.

### 🔑 E una riga rossa ha spento un testimone dell'ondata 4 — che lo ha detto

La `palestra` rende indisponibile il lunedì mattina, e lì il testimone puntato
di `forbidden_sequence` (ondata 4) metteva le due ore di scienze motorie della
4A. Da quel momento il suo primo `assert` restava verde **per il motivo
sbagliato** — `INFEASIBLE` per il pre-filtro invece che per la riga osservata —
e il secondo, il ramo «senza la riga», è diventato rosso.

⚠ È il caso per cui la spec ha reso quel ramo **obbligatorio**: senza, il
testimone si sarebbe svuotato in silenzio e nessuno se ne sarebbe accorto. Il
pin si è spostato al martedì.

### La tacca: lo spezzone di RICCI

L'unica riga dell'ondata che ammette la verifica dell'ondata 3, e per una
ragione che si legge in una frase: **tre ore in tre fasce**. RICCI ha un
completamento da tre ore e viene un pomeriggio a settimana. Una fascia rossa
in più e le tre ore non ci stanno — `INFEASIBLE`, con un argomento di
conteggio e non una taratura.

### ⚠ Nessuna riga datata, e non è una dimenticanza

`ResourceUnavailability.date` distingue l'indisponibilità ricorrente
dall'**assenza puntuale** — una tabella sola, come EDT
(`docs/edt/vincoli.md`). Ma una sola riga datata spacca l'anno in **due firme
di settimana** (`domain/analysis/conformity.week_signatures`), e le firme sono
materia dell'ondata 6. Il banco resta quindi a una firma, e la seconda arriva
con la materia quindicinale.

---

## 2. Il peso didattico — tre tetti che formano, uno che ammette

⚠ In una base reale del prodotto i quattro tetti d'istituto sono a «nessuno» e
ogni materia pesa 1 (osservato in EDT, changelog 2026-07-26 sera). Il Fermi è
fedele, ed è per questo che `structural:didactic_weight` non aveva mai visto
un dato. Il banco dichiara invece una politica di scuola.

| | Valore | Perché non è vacuo |
|---|---|---|
| Peso 2 | MAT, LAT, GRE | le materie d'indirizzo dei due corsi |
| `max_weight_morning` | 9 | cinque fasce d'indirizzo in una mattina pesano 10 |
| `max_weight_afternoon` | 5 | tre fasce d'indirizzo in un pomeriggio pesano 6 |
| `max_weight_day` | 12 | otto fasce con cinque d'indirizzo pesano 13 |
| `max_weight_week` d'istituto | `None` | lo porta la **classe**, ed è il ramo che prevale |
| 3B `max_weekly_weight_per_student` | 40 | è **esattamente** il peso settimanale delle sue unità |

### 🔑 Il tetto settimanale non ha un testimone puntato, e non è una lacuna

I tre tetti per giornata e per mezza giornata **formano** l'orario: vietano
configurazioni, quindi un pin le può imporre e i tre testimoni funzionano
(pesi 10, 6 e 13 contro tetti 9, 5 e 12 — e ogni pin sfora *un solo* secchio,
o direbbe `INFEASIBLE` per il tetto sbagliato).

Il settimanale no. La somma dei pesi di un'unità-studente lungo la settimana
**non dipende da dove le attività vanno**: ogni ora pesa ovunque la si metta.
Nessun pin lo può violare, perché non esiste una configurazione vietata da
imporre — l'unica leva che il modello ha per rispettarlo è **scartare**. È il
caso che `CLAUDE.md` chiama *il tetto inevadibile*, e il suo contratto è
quindi la tacca: 40 regge, 39 è `INFEASIBLE`.

Vale la pena averlo scritto: è la differenza fra un vincolo che *forma*
l'orario e uno che si limita ad ammetterlo o rifiutarlo, e i due non si
provano allo stesso modo.

### ⚠ E costano — il primo vincolo del banco che cambia il regime di ricerca

Misurato sullo stesso modello, senza altro cambiare:

| | Un lavoratore | Otto lavoratori |
|---|---:|---:|
| Con i tetti per giornata e mezza giornata | **439 s** | **7 s** |
| Senza (solo il tetto di classe) | 7 s | 7 s |

Sono ~510 constraint, uno per (unità-studente, secchio), ciascuno con
migliaia di letterali. Conseguenza pratica: i due test delle ondate 3 e 4 che
cercavano con `workers=1` per riproducibilità sono passati a `workers=8` — le
loro asserzioni sono **invarianti** e non celle, quindi il portafoglio
parallelo non toglie niente.

---

## 3. Il tecnico e i carrelli — le due risorse che mancavano

`Resource` prevede cinque tipi da sempre — è il pannello dell'attività di EDT,
che conta docenti, classi, aule, personale e materiali fra le risorse di
piazzamento. Il personale e i materiali non ne avevano mai visto uno.

| Risorsa | Capienza | Chi la usa |
|---|---|---|
| **TECN**, tecnico di laboratorio | 1 | i 3 blocchi da due ore di fisica del triennio scientifico + le 4 ore di scienze a mezza classe + (dall'ondata 6) la metà di laboratorio dell'ora quindicinale del 5B |
| **CARRELLO**, carrelli di portatili | 4 | i 2 livelli d'inglese (2 l'uno), l'informatica della 2C articolata (1), i 4 laboratori a mezza classe (2 l'uno) |

**Il tecnico è uno solo**, quindi due laboratori non possono essere
simultanei. Non è una famiglia nuova nel modello: è una **chiave di
occupazione** come un docente o un'aula — ed è il vincolo vero delle scuole.

**I carrelli sono una capienza cumulativa**, ed è il campo `quantity` di
`ActivityMaterialRequirement` a renderla tale: uno ogni dodici alunni, cioè
due per un gruppo d'inglese da ventiquattro, due per un laboratorio a mezza
classe da tredici e uno per la mezza classe articolata da dieci. Il testimone: due livelli d'inglese più un laboratorio nella stessa
fascia fanno `2 + 2 + 2 > 4`. È il ramo cumulativo di
`structural:occupation`, che nessun dataset aveva mai acceso.

### ⚠ Quattro carrelli e non tre, e il numero l'ha deciso l'ondata 2

A tre, i due livelli d'inglese (due carrelli l'uno) non potrebbero più stare
nella stessa fascia. Ma stare nella stessa fascia è **il senso** di un
raggruppamento trasversale, non un dettaglio: gli stessi alunni si dividono
per livello *nella stessa ora*. Un banco che rompesse una forma dell'ondata
precedente per accendere un builder starebbe misurando sé stesso. Il test
dell'ondata 2 lo ha detto per primo, diventando rosso.

---

## 4. I due difetti che l'ondata ha trovato — chiusi il 2026-08-31

Erano dichiarati e non riparati, perché la spec (§8) vietava al banco di
modificare il motore; ognuno aveva un test che asseriva il comportamento
**corrente**, per diventare rosso il giorno della riparazione. Quel giorno è
arrivato: i test sono stati capovolti, e qui resta il racconto con le misure
di prima e di dopo.

### L6 — un insieme non viaggia

Il carrello è l'unica risorsa del banco **senza sede**: quattro carrelli sono
della scuola, non di un edificio, e servono l'inglese alla centrale e
l'informatica in succursale. Ma `structural:site_transition` postava la
clausola «due sedi sulla stessa fascia» su **ogni** chiave di occupazione, e
per un insieme di quattro carrelli quella clausola è falsa: un insieme non è
un corpo solo, e non viaggia.

La dimostrazione che il colpevole era la sede e non la capienza stava in tre
esecuzioni, e la seconda è quella che decideva:

| | Prima | Dopo |
|---|---|---|
| capienza 4, domanda 2 + 1 = 3, sedi diverse | `INFEASIBLE` | `OPTIMAL`, zero scarti |
| capienza **3**, cioè esattamente la domanda | — | `OPTIMAL`: il bordo |
| capienza **2**, stessa cella | — | `INFEASIBLE`: i posti non bastano |
| capienza **9**, stessa cella, sedi diverse | `INFEASIBLE` — quindi non era capienza | — |

🔑 **La riparazione non toglie il vincolo: ne cambia la domanda.** «Due sedi si
toccano?» era la domanda sbagliata; quella giusta è «**ci stanno**?», cioè
`carico(sa, s) + carico(sb, t) <= posti`. A capienza 1 — ogni docente, ogni
classe, ogni parte, ogni atomo — la nuova regola coincide **riga per riga**
con la vecchia clausola: due carichi valgono almeno due, un posto solo non li
regge, e la coppia resta vietata. Cambia solo dove la vecchia diceva una cosa
falsa, cioè sull'aula col `Numero di aule` e sul materiale con quantità.

🔑 **E il carrello resta l'unica risorsa del progetto che possa mostrare
[ADR-019](../../docs/decisioni.md)** — *dentro una fascia non si viaggia*.
`MaxSiteChangesChecker` conta **zero cambi** su due sedi simultanee, e ora
`SiteTransitionChecker` non nomina più nemmeno l'impossibilità, perché
impossibile non è: tre carrelli reggono due impegni. L'impossibilità torna
appena i posti non bastano — un carrello solo per due sedi — ed è il ramo di
controllo del test.

⚠ La vecchia versione di questo paragrafo diceva *«e `SiteTransitionChecker`
nomina comunque l'impossibilità: sono due domande diverse con due risposte
diverse»*. Le due domande restano diverse; era la seconda risposta a essere
sbagliata.

### L6bis — il giallo lo legge anche la fase 1

Le tre letture della stessa indisponibilità **opzionale** su un'aula erano
tre, e due andavano d'accordo:

- `structural:unavailability` (il pre-filtro) la rispetta come una rossa;
- `RoomsContext._filtra` (fase 2) toglie l'aula dalle candidate, se non si
  autorizza l'override;
- `structural:room_pool` (fase 1) ne contava i posti **come se fosse libera**,
  perché «l'opzionale è violabile per definizione».

Su un'aula a **candidata unica** non si vedeva: l'aula è un token, e il
pre-filtro toglieva la cella prima che si arrivasse lì. Su un'aula a più
candidate la fase 1 piazzava e la fase 2 **rinunciava**, che è esattamente ciò
che [ADR-021](../../docs/decisioni.md) esiste per non far succedere.

Ora la fase 1 il giallo lo conta, e chi paga decide: l'ostacolo è duro
*finché non lo si autorizza*, che è la frase letterale della documentazione.
Due attività di fisica delle sole `{LAB-FIS, LAB-INF}` imposte sulla fascia
gialla sono `INFEASIBLE` **prima**, invece di diventare una rinuncia dopo; con
`ignora_opzionali=(ROOM,)` il posto torna a contare e lo stesso pin è
`OPTIMAL`, in entrambe le fasi.

⚠ **La gialla del dataset resta su `LAB-SUCC`**, a candidata unica. La ragione
per cui ci stava — non portare un difetto noto dentro il banco — è caduta, ma
quella riga prova l'interazione col pre-filtro, e spostarla ora vorrebbe dire
cambiare un dato per comodità invece che per una lettura.

---

## I giorni esenti dal conteggio delle giornate libere

La casella per giorno di `Parametri → Istituto → Orari` — *«i giorni spuntati
saranno ignorati durante il calcolo delle giornate libere»* — implementata il
2026-08-31 come `InstituteSettings.free_day_exempt_mask`. ⚠ **Non è la maschera
dei giorni lavorativi**: il giorno resta in griglia e ci si lavora, non vale
come giornata libera.

🔑 **Sul banco si prova col testimone puntato, e la forma è misurata e non
scelta.** La tacca non ci arriva: con otto fasce al giorno le dodici ore di
ZANET stanno comodamente nei giorni esenti, e stringere la maschera a **tre**
giorni su cinque restituisce `OPTIMAL` con zero scarti. È la stessa lezione
dell'ondata 4 in un'altra veste — un parametro che cambia *quali giorni
contano* non sparpaglia un carico, quindi il verdetto non si ribalta
stringendolo.

Il testimone si costruisce invece dall'orario che il banco trova da sé: si
congela ZANET dov'è atterrato e si esentano **esattamente i giorni che gli
erano rimasti liberi**, che restano lavorativi per tutti gli altri. Ciò che
era una garanzia soddisfatta diventa una garanzia senza appoggio, e i due rami
sono la stessa istanza con gli stessi pin — l'unica differenza è il parametro
d'istituto.

⚠ **Ha portato un secondo clamp**, con una ragione diversa da quella di L8:
quello nasce dal piazzamento (una mezza giornata libera la offre solo un giorno
lavorato), questo dalla maschera — con k giorni contabili non se ne possono
avere più di k liberi. Senza, esentare quattro giorni su cinque renderebbe
`INFEASIBLE` una riga da due giorni liberi per colpa di un parametro
d'istituto invece che dell'orario.

---

## Cosa esercita, in una riga

| Famiglia | Prova |
|---|---|
| `structural:unavailability` | testimone puntato ×2 (rosse), ×2 (gialle, con e senza override), contro-testimone (verde), tacca (spezzone) |
| `structural:didactic_weight` | testimone puntato ×3 (mattina, pomeriggio, giornata), tacca (settimana) |
| `structural:occupation`, ramo **personale** | testimone puntato (due laboratori, un tecnico) |
| `structural:occupation`, ramo **cumulativo** | testimone puntato (`2 + 2 + 2 > 4`) |
| `structural:site_transition` su una risorsa senza sede | tacca sulla capienza (4 / 3 / 2) — era il difetto **L6** |
| ADR-019 | misurato nell'analisi, su un orario scritto a mano |
| `free_day_exempt_mask` | testimone puntato (ZANET congelato, esenti i suoi giorni liberi) — la tacca è misurata e non arriva |
