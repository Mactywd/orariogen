# L'Alighieri: il banco a scuola intera

**Data**: 2026-08-30
**Stato**: approvata — **ondata 1 di 7 fatta** il 2026-08-30
**Apre**: la copertura del modello a scala reale — **ventiquattro builder su
ventisette** non hanno mai visto un dataset

## 0. Il pezzo

Il modello hard è completo da settimane e la suite è verde, ma il dataset su
cui gira il prodotto esercita **tre builder su ventisette** — misurato, non
stimato (§2.1). Gli altri ventiquattro sono provati solo da
`test_modello_completo`, che li accende tutti insieme su un testimone sintetico
da poche decine di attività.

Questo pezzo costruisce il **secondo dataset**, il Liceo "Dante Alighieri":
una scuola completa, a scala confrontabile col Fermi, che porta **almeno una
riga per ogni famiglia** del registro, con l'esito atteso dichiarato riga per
riga.

🔑 **Non sostituisce il Fermi, e la ragione è la ragione di tutto il pezzo.**
Vedi §1.

## 1. Perché due dataset e non un Fermi più ricco

Il Fermi ha un mestiere che l'Alighieri non può ereditare: è la trascrizione di
una scuola **realmente inserita in EDT**, campo per campo, durante il reverse
engineering. Il docstring di `tests/fermi.py` lo dichiara:

> La trascrizione è essa stessa il test: se lo schema non riesce a
> rappresentare una riga, il build fallisce.

⚠ **Quel test funziona solo perché nessuno ha progettato il Fermi per
superarlo.** È una prova, non una fixture. Arricchirlo finché esercita
ventisette builder distruggerebbe esattamente la proprietà che lo rende utile —
da quel momento in poi «lo schema rappresenta il Fermi» non direbbe più niente
sul mondo, direbbe solo che abbiamo scritto righe che il nostro schema accetta.

E l'Alighieri è uno strumento di **natura diversa**, che va dichiarato tale.
Le sue righe non sono osservazioni: sono costruzioni nostre, scelte per far
scattare un checker. La convenzione della casa — *non inventare campi, ciò che
è nostra estensione va segnalato come tale* — vale anche per i dataset. Il suo
README apre dicendo che è un **banco**, non una scuola osservata.

| | Fermi | Alighieri |
|---|---|---|
| Origine | osservazione in EDT | costruzione nostra |
| Domanda a cui risponde | «lo schema regge una scuola vera?» | «il motore regge tutte le famiglie insieme, a scala vera?» |
| Si modifica | mai per far passare un test | quando una famiglia nuova entra nel registro |
| Se fallisce | lo schema è sbagliato | il motore è sbagliato |

### 1.1 Cosa aggiunge rispetto a `test_modello_completo`

Domanda legittima, perché quel test **accende già tutte le famiglie insieme**
su cinque semi, con l'oracolo differenziale pulito. Tre cose, e sono reali:

- **La scala.** Il testimone ha poche decine di attività; il Fermi ne ha 284.
  Il difetto del budget in coda (changelog, 2026-08-30) è comparso *solo* a
  scala Fermi, e nessun test lo vedeva. L'interazione fra famiglie **a scala
  vera** è un fenomeno diverso dall'interazione fra famiglie.
- **La coerenza.** Il banco combina le famiglie per seme, cioè a caso. Una
  scuola le combina come le combina una scuola: il docente con l'indisponibilità
  è *anche* quello con il tetto di mezze giornate, e insiste sulle stesse
  classi. «Sopravvive a tutte» e «sopravvive a una configurazione
  **plausibile** di tutte» sono due affermazioni diverse.
- **I comandi, non il modello.** `analyze` (blame e fase 5), `Estrai` con i suoi
  sei rilevatori, `place_and_fix`, `assign_rooms` girano oggi su un dataset dove
  quasi tutto tace. Sul Fermi la classifica dei vincoli ordina **tre
  indisponibilità di docenti e nient'altro**: non è una classifica, è un elenco.

## 2. La misura del vuoto

### 2.1 🔑 Tre builder su ventisette fanno qualcosa

⚠ **E questo corregge una riga di `CLAUDE.md`.** Lì era scritto che le famiglie
esercitate dal Fermi sono *«sei: griglia, indisponibilità, occupazione, sedi,
D.T.B. e `room_pool`»*. Misurando invece di elencare — avvolgendo `restrict` e
`build` di ogni builder e contando celle tolte e constraint postati mentre
`build_model` gira sul Fermi — il quadro è più magro:

| Celle tolte | Constraint | Builder |
|---:|---:|---|
| 0 | **948** | `structural:occupation` |
| 0 | **420** | `structural:room_pool` |
| **360** | 0 | `structural:unavailability` |

**Gli altri ventiquattro non fanno assolutamente nulla.** Tre dei sei elencati
non reggono la verifica: `structural:site_transition` non ha `Site` da leggere,
`max_gap_hours` legge righe `ResourceTimeConstraint` che non esistono, e
`structural:grid` è un no-op perché il Fermi non ha né festività né intervalli e
ogni durata sta nella giornata.

🔑 La misura vale più dell'elenco perché è **eseguibile**, e diventa il criterio
di accettazione dell'Alighieri (§6.4, ondata 7): la stessa sonda, sul nuovo
dataset, deve mostrare **ventisette builder su ventisette** che fanno qualcosa.

### 2.2 Tredici tabelle vuote

Conteggio delle righe per modello sul Fermi caricato in un database vero
(`fermi.build()`, 2026-08-30). **Tredici tabelle su trentatré sono vuote** —
dodici nel conteggio a database, più `QualityCriterion`, che il conteggio non
mostra vuoto solo perché ne sono state seminate cinque a mano per la misura di
quel giorno (`fermi.py` non ne crea nessuna):

| Tabella | Righe | Cosa manca di conseguenza |
|---|---|---|
| `ResourceTimeConstraint` | **0** | otto famiglie dell'asse Cardinalità |
| `SubjectConstraint` | **0** | tredici tipi dell'asse Relazione |
| `ClassPartition` / `ClassPart` | **0** | gli sdoppiamenti — ✅ **in scope v1** (ADR-013) |
| `Group` | **0** | i raggruppamenti trasversali — ✅ **in scope v1** (ADR-013) |
| `Site` | **0** | sedi distaccate, spostamenti, `max_site_changes` |
| `StaffMember` / `Material` | **0** | due delle cinque risorse di piazzamento |
| `ActivityMaterialRequirement` | **0** | il fabbisogno di materiali |
| `Break` | **0** | l'intervallo come separatore |
| `Holiday` | **0** | il calendario |
| `RelaxationQuota` | **0** | tutti gli alleggerimenti a quota |
| `QualityCriterion` | **0** | i criteri di qualità, mai esercitati da riga di comando |

⚠ **Due di queste sono voci ✅ dello scope v1.** Sdoppiamenti e raggruppamenti
trasversali sono decisi *dentro* v1 da ADR-013, hanno i loro test
(`test_classe_articolata.py`) su fixture sintetiche, e **nessun dataset li
rappresenta**. È il buco più grave dell'elenco, perché non è una famiglia di
vincoli rara: è una forma che quasi ogni liceo italiano ha.

⚠ E `QualityCriterion` a zero è il motivo per cui il difetto del budget è
sopravvissuto: dalla riga di comando la qualità non era mai stata eseguita.

## 3. Cosa deve esercitare, famiglia per famiglia

La tabella è il **contratto della spec**: ogni riga dice quale entità
dell'Alighieri esiste per far scattare quel checker, e cosa deve succedere.
L'esito atteso si scrive **qui, prima** di lanciare il solver (§6).

### 3.1 Asse Cardinalità — `ResourceTimeConstraint` (8 famiglie)

| Famiglia | Portatore | Esito atteso |
|---|---|---|
| `min_distribution` | una materia da 4 h su 3 giorni minimi | il solver la sparpaglia; togliendo il vincolo si accorpa |
| `max_hours` | un docente con tetto mattina < tetto giornata | ore spinte al pomeriggio |
| `max_presence` | un docente a tempo parziale, 3 giorni | due giorni interi vuoti per lui |
| `arrival_departure` | un docente che non entra prima della 2ª | prima fascia libera tutti i giorni |
| `free_guaranteed` | un docente con 1 giorno libero garantito | un giorno interamente vuoto, **scelto dal solver** |
| `max_half_days` | una classe con tetto di mezze giornate | pomeriggi compattati |
| `max_site_changes` | un docente su due sedi, 1 cambio/giorno | vedi §3.4 |
| `max_gap_hours` | un docente con D.T.B. stretto | ⚠ questa riga diceva «l'unica già esercitata dal Fermi (via `InstituteSettings`)», e §2.1 la smentisce: il builder legge `row.params["max_gap_minutes"]` da righe `ResourceTimeConstraint`, di cui il Fermi ha **zero** |

### 3.2 Asse Relazione — `SubjectConstraint` (13 tipi)

| Famiglia | Portatore | Esito atteso |
|---|---|---|
| `same_half_day_incompatible` | MAT e FIS nella stessa mezza giornata | mai insieme in mattina/pomeriggio |
| `same_day_incompatible` | le due lingue | mai lo stesso giorno |
| `two_days_incompatible` | ITA con sé stessa, orizzonte 2 | mai a un giorno di distanza |
| `forbidden_sequence` | MOT → nessuna materia scritta subito dopo | nessuna successione immediata |
| `max_hours_half_day` | MAT, 2 h per mezza giornata | tetto rispettato |
| `max_hours_day` | MAT, 3 h al giorno | tetto rispettato |
| `weekly_order` | LAT prima di GRE nella settimana | ordine settimanale |
| `imposed_succession` | le 2 h di LAB-FIS consecutive | concatenazione con ritardo massimo |
| `half_day_gap` | due materie a distanza minima di mezze giornate | distanza rispettata |
| `parts_before_class` | il gruppo di recupero **prima** dell'ora a classe intera | vedi §3.3 |
| `parts_after_class` | l'ora di laboratorio **dopo** la teoria | vedi §3.3 |
| `parts_before_or_after_class_h` | variante omogenea | vedi §3.3 |
| `parts_before_or_after_class_ab` | variante A/B | vedi §3.3 |

⚠ Le quattro `parts_*` **richiedono le partizioni**: senza `ClassPart` non
hanno soggetto. Sono la ragione per cui §3.3 non è opzionale.

### 3.3 Gli sdoppiamenti, che sono in scope v1

L'Alighieri porta almeno:

- una **classe articolata** con due parti su piani di studi diversi (la
  condizione 3 di ADR-015, oggi provata solo su fixture);
- una partizione **IRC / alternativa** (`_REL` / `_ALT`), che `gruppi.md`
  dichiara modellata come due parti della stessa classe;
- uno **sdoppiamento a effettivo ridotto** (laboratorio a mezza classe), che
  è ciò che dà senso a `Al./Rid.` e a `expected_students`;
- un **raggruppamento trasversale** su due classi (le lingue di due sezioni
  che si mescolano), che è il caso che *rompe la decomposizione per classe* —
  la conseguenza che ADR-013 dichiara e che nessun dataset ha mai messo alla
  prova.

### 3.4 Le sedi

Due sedi, con un tempo di spostamento dichiarato per **coppia orientata**, e
almeno un docente che insegna in entrambe. Esercita `structural:site_transition`
(oggi muto: zero `Site`), `max_site_changes`, il filtro delle aule per sede
nella seconda fase, e ADR-019 — *dentro una fascia non si viaggia*.

### 3.5 Peso didattico, personale, materiali, quote

- **Peso didattico**: i quattro tetti di `InstituteSettings` oggi sono `None`
  (in EDT sono `nessuno`, quindi è fedele). L'Alighieri ne accende **almeno
  uno**, perché `structural:didactic_weight` non ha mai visto un dataset — ed è
  la famiglia su cui ADR-018 ha l'eccezione dichiarata.
- **Personale e materiali**: un tecnico di laboratorio e un carrello di
  portatili, cioè due delle cinque risorse di piazzamento che oggi non
  esistono in nessun dataset.
- **`RelaxationQuota`**: almeno una quota nelle due forme *margine* e *deroga*,
  su una famiglia che il dataset porta davvero in tensione. Senza, gli
  alleggerimenti sono codice mai eseguito su dati.
- **`QualityCriterion`**: la gerarchia completa, così che `solve` e
  `solve --popolazione` siano esercitati **dal dataset** e non a mano.

## 4. Dimensionamento

| Parametro | Proposta | Perché |
|---|---|---|
| Classi | 12 (tre sezioni, due indirizzi) | due indirizzi servono ai piani di studi diversi |
| Docenti | ~22 | qualcuno a tempo parziale, qualcuno su due sedi |
| Sedi | 2 | il minimo per avere un cambio |
| Griglia | 5 × 8, con pausa mensa | 8 fasce danno il pomeriggio, che serve a `max_hours` e `max_half_days` |
| Attività | ~330 → **323 realizzate** | scala confrontabile col Fermi (284) |
| Firme di settimana | almeno una **quindicinale** | vedi §4.1 |

🔑 **Stretto ma risolvibile.** Le misure interessanti stanno vicino al bordo: un
dataset largo produce `OPTIMAL` in un secondo e non dice niente, uno
infattibile non dice niente di diverso. Il criterio operativo: la fase 1 chiude
`OPTIMAL` **con zero scarti**, ma togliendo una sola aula o un solo docente
comincia a scartare.

### 4.1 ⚠ La firma di settimana, che paga un debito aperto

Il debito aperto il 2026-08-30 (L3) dice che **i criteri di qualità ignorano le
firme di settimana**, e che nessuna delle due basi lo esercita. L'Alighieri con
una materia quindicinale lo esercita — e a quel punto il debito smette di
essere un sospetto e diventa un test rosso, che è il modo giusto di chiuderlo.

## 5. Forma sul disco

Lo stesso paio del Fermi, perché serve a due cose diverse:

```
data/liceo-alighieri/
  README.md            ⚠ apre dichiarando che è un banco, non un'osservazione
  classi.md, docenti.md, materie.md, aule.md, sedi.md, piani-di-studi.md
  gruppi.md            partizioni, parti, raggruppamenti trasversali
  vincoli.md           🔑 una riga per famiglia, con il **perché esiste**
  esiti-attesi.md      🔑 cosa deve succedere, scritto prima di eseguire
tests/alighieri.py     la trascrizione in letterali Python
```

Il markdown non è decorazione: è **dove l'intento si scrive e si rivede**. Una
riga di `SubjectConstraint` in Python dice *cosa*; `vincoli.md` dice *perché
quella riga esiste*, ed è l'unica difesa contro il dataset che si aggiusta
finché passa.

## 6. La regola che lo tiene onesto

⚠ **Il rischio è preciso e fatale: un dataset lo si aggiusta finché è verde, e
a quel punto non prova più niente.** Il Fermi si difende con
`vincoli-attesi.md`, conflitti inseriti apposta e scritti *prima* di lanciare
il solver. L'Alighieri eredita la disciplina, rinforzata:

1. `esiti-attesi.md` si scrive **prima** della prima esecuzione, dal disegno.
2. Ogni riga di vincolo dichiara la famiglia che deve far scattare.
3. Se l'esito osservato smentisce quello atteso, si scrive **quale delle due**
   era sbagliata — e se era l'attesa, si dice perché. Non si riscrive l'attesa
   in silenzio.
4. **Verifica per mutazione**: per ogni famiglia, togliere la sua riga deve
   cambiare l'orario. Una famiglia la cui rimozione non cambia niente non è
   esercitata, è solo presente — ed è il modo in cui un dataset «completo» può
   essere vuoto.

🔑 Il punto 4 è il vero contratto. Senza, «l'Alighieri copre tutte le famiglie»
significa solo «l'Alighieri ha righe in tutte le tabelle».

E ha una forma **economica e automatica**, che diventa un test della suite: la
sonda di §2.1 — avvolgere `restrict` e `build` di ogni builder e contare celle
tolte e constraint postati durante `build_model` — deve riportare **zero
builder inerti** sull'Alighieri. Non sostituisce la mutazione riga per riga
(un builder può postare qualcosa di vacuo), ma la precede: è il filtro che
prende in un secondo il caso «la riga c'è e il builder non la vede», che sul
Fermi vale ventiquattro builder su ventisette.

⚠ E va scritto come test, non eseguito a mano una volta: senza, il primo
builder aggiunto dopo l'Alighieri tornerebbe silenziosamente inerte, che è
esattamente com'è nata questa situazione.

## 7. Cosa devono poter dire i comandi

Il dataset è progettato perché ogni comando abbia qualcosa di vero da dire:

- **`analyze`** — una classifica di blame che ordina **famiglie diverse**, non
  tre indisponibilità; e almeno una configurazione (in una variante *satura*
  del dataset) che produce un deficit di Hall vero.
- **`Estrai`** — almeno un'attività per ciascuno dei sei rilevatori.
- **`place_and_fix`** — un'imposizione che costa più di una attività spostata:
  sul Fermi ne costa **una**, che non mette alla prova niente.
- **`solve --popolazione`** — un arbitrato in cui il tetto di non-regressione
  **morde davvero**, cioè in cui alzare la tolleranza cambia il risultato.
- **`assign_rooms`** — una contesa che il gruppo di aule di ADR-021 risolve, e
  una rinuncia inevitabile quando la si stringe.

## 8. Cosa **non** entra

- **Nessuna modifica al Fermi.** Se una famiglia manca lì, resta mancante: è
  ciò che il Fermi *è*. L'unica eccezione ammessa resta quella già in atto —
  le aule e le etichette orarie, dichiarate nel docstring come dimensionamento
  nostro.
- **Nessuna modifica al motore.** Questa spec costruisce dati e attese. Se
  l'Alighieri trova un difetto — ed è il suo scopo — quello è un pezzo suo, con
  il suo test rosso. ⚠ Scritto perché la tentazione sarà forte: un dataset che
  non passa si fa passare aggiustando il dataset.
- **Nessun import da EDT.** ADR-012 ha escluso `Partenaire_Index` come formato
  di import, e questo dataset si scrive a mano come il Fermi.
- **Il `Ciclo personalizzato`**, che resta l'unica osservazione EDT aperta: il
  dataset usa un ciclo settimanale, come il Fermi.
- **Una seconda scuola *vera*.** Quella la porta D2, e varrà più di questa. Ma
  D2 dipende da dati che non abbiamo e l'Alighieri no — e l'Alighieri **riduce
  il rischio di D2**: quando arriveranno dati veri con tutti i loro vincoli,
  sapremo già che il motore ci sopravvive, invece di scoprire le due cose
  insieme.

## 9. Ondate

1. ✅ **L'anagrafica** (2026-08-30): sedi, classi, indirizzi, docenti, materie,
   aule, piani di studi, servizi; la quadratura per materia × piano verificata
   come sul Fermi. `data/liceo-alighieri/` (sette file) e `tests/alighieri.py`.
   **12 classi, 2 indirizzi, 2 sedi, 21 cattedre a `+/- = 0`, 345 ore-classe,
   323 attività**, griglia 5 × 8 con la mensa. Fase 1 `OPTIMAL` a zero scarti
   (13 583 var, 5 493 constraint, ~2,5 s), fase 2 66 su 66 senza rinunce.
   🔑 E la **sonda di §6 è già un test** (`tests/sonda.py`,
   `tests/test_alighieri_sonda.py`) invece di aspettare l'ondata 7: l'insieme
   dei builder attivi è un cricchetto che ogni ondata deve allargare — **4 su
   27** oggi contro i 3 del Fermi. Anticiparlo costa nulla e toglie il modo in
   cui una famiglia entra «presente ma non esercitata».
   ⚠ Non verificato, e dichiarato tale: il «stretto ma risolvibile» di §4.
   Senza righe di vincolo la tensione non esiste.
2. **Gli sdoppiamenti** (§3.3): partizioni, parti, IRC/alternativa,
   raggruppamento trasversale. È la voce ✅ di scope v1 senza dataset, quindi
   viene prima dei vincoli.
3. **L'asse Cardinalità** (§3.1): otto famiglie, con l'esito atteso e la
   verifica per mutazione di §6.4.
4. **L'asse Relazione** (§3.2): tredici tipi, idem.
5. **Sedi, peso didattico, personale e materiali** (§3.4, §3.5).
6. **Quote, criteri di qualità e firme di settimana** (§3.5, §4.1) — qui si
   attende il **rosso** sul debito delle firme.
7. **Il criterio di accettazione e i comandi**: il test della sonda (§6, zero
   builder inerti), la misura di ciascun comando su §7, e l'aggiornamento di
   `CLAUDE.md`, `docs/todo.md` e del changelog con i numeri veri.

Ogni ondata è verde prima della successiva, e ogni ondata aggiunge righe a
`esiti-attesi.md` **prima** del codice che le esercita.
