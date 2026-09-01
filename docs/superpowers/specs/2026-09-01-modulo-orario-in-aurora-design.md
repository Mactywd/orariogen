# Il modulo Orario dentro Aurora — il design dell'implementazione

> Stato: **proposta**, 2026-09-01.
> Implementa [ADR-027](../../decisioni.md). Non lo rediscute: ne prende le
> quattro parti e decide *come* si costruiscono, a partire da misure che il
> giorno dell'ADR non erano state prese.

## 0. Perché questo documento esiste

ADR-027 decide **cosa**: le tabelle prendono la scuola, l'uscita è
`ScheduleEntry`, il calcolo è un lavoro, lo stato sta su tre livelli. Dichiara
anche cosa *non* decide — calendario, prezzo, UI.

Ma c'è una quinta domanda che non compare in nessuna delle due liste, e senza
una risposta non si scrive una riga: **dove vive il codice.** Un modulo di
Aurora può essere un'app dentro il suo repository o un pacchetto che Aurora
installa, e la differenza non è di gusto — decide se la chiave esterna verso
la `School` si può scrivere in modo ordinario oppure no.

E c'è una sesta, che ADR-027 nomina di sfuggita nel livello «ingresso» — *le
tabelle di Aurora, School-scoped* — senza dire che **quattro di quelle tabelle
esistono già da tutt'e due le parti**, con lo stesso nome.

## 1. Le sette misure

### 1.1 La scuola serve su 13 tabelle, non su 33

ADR-027 dice «le 33 tabelle prendono la `School`». Contate oggi sono **34** —
`SetupQuestion` è nata lo stesso giorno, con L13, dopo che l'ADR era scritto.

Ma il numero che conta è un altro. Una tabella che ha una FK **non nullable**
verso un'altra tabella del dominio la scuola la eredita: non le serve un campo
proprio, e un campo proprio sarebbe un secondo posto dove la stessa verità può
diventare falsa. Misurando gli archi solidi:

| | quante | quali |
|---|---|---|
| **devono portare la scuola** | **13** | `CompetitionClass`, `Discipline`, `Extraction`, `Group`, `InstituteSettings`, `QualityCriterion`, `RelaxationQuota`, `Resource`, `SchoolYear`, `SetupQuestion`, `Site`, `StudyPlan`, `TimeGrid` |
| **la ereditano** | **21** | tutte le altre, `Activity` → `Subject`, `Placement` → `Schedule`, `Teacher`/`Room`/`Material`/`StaffMember`/`SchoolClass`/`ClassPart` → `Resource`… |

🔑 **E due delle tredici sono lì per una FK nullable**, non perché siano
radici: `Resource.site` e `RelaxationQuota.resource`. Una risorsa senza sede è
il caso normale in una scuola a plesso unico — cioè quasi tutte — quindi
l'albero delle risorse **non raggiunge la scuola per nessun cammino solido**,
e con lui i sei tipi concreti che ne discendono. È l'unico punto in cui la
tenancy dipende da una nullabilità, e va scritto perché non lo si scopra due
volte.

⚠ Le 21 che la ereditano restano comunque **da guardare una per una** quando
si scriverà l'API, per l'invariante di Aurora che non è la FK ma
`school_scoped_fields`: ogni FK/M2M scrivibile verso un modello di tenant va
validata. Su `Activity` da sole sono sette M2M.

### 1.2 Le unicità globali sono otto, e la nona non è un campo

ADR-027 ne elenca sette. Misurate: **otto** — manca `SetupQuestion.key`, per
la stessa ragione per cui le tabelle erano 33.

E ce n'è una che quell'elenco non poteva contenere perché non è un campo
`unique`: `QualityCriterion` ha un constraint su **`(kind, population)`**, che
è globale esattamente come gli altri — due scuole non potrebbero dichiarare
entrambe «buchi, sui docenti». Va nell'elenco.

Più `InstituteSettings`, che ADR-027 tratta a parte e giustamente: non è
un'unicità da estendere, è un singleton da moltiplicare.

### 1.3 Le quattro collisioni, e sono a senso unico

Aurora ha già `Teacher`, `SchoolClass`, `Subject` e — sotto altro nome — la
griglia oraria (`TimeSlot` + `DayConfiguration`). Non sono tabelle vicine alle
nostre: sono **le nostre proiettate su due colonne**.

| | Aurora | noi |
|---|---|---|
| `Teacher` | `school`, `name` | cognome, nome, sigla, stato, `Mh/s`, `HSMax`, materia preferita, M2M materie insegnabili, e la `Resource` sotto (sede, capienza simultanea) |
| `SchoolClass` | `school`, `name` | piano di studi, anno, aula preferenziale, tetto di peso per alunno, alunni attesi, e la `Resource` sotto |
| `Subject` | `school`, `name` | codice, disciplina, `Al./Rid.`, peso didattico |
| griglia | `TimeSlot(period_number, start_time, end_time)`, `DayConfiguration(weekday, periods_count)` | `TimeGrid` (giorni, fasce, minuti, prima fascia pomeridiana) + `SlotLabel` (l'orologio) + `Break` |

🔑 **La collisione è a senso unico**, e questo decide chi vince: ogni campo di
Aurora esiste anche da noi, nessuno dei nostri esiste da lei. Non c'è da
riconciliare due modelli, c'è da **sostituire una proiezione con l'originale**.

⚠ Con un'eccezione, e va detta: Aurora ha **un** campo `name` dove noi abbiamo
cognome e nome separati. Ricomporre è banale, scomporre no — `"Maria De Luca"`
non si taglia con una regola. Le righe che ci sono si migrano mettendo tutto
in `last_name` e lasciando `first_name` vuoto: è brutto e **si vede**, che è
ciò che serve perché qualcuno lo sistemi, invece di un taglio automatico che
sbaglia in silenzio sui cognomi composti.

Il raggio dell'esplosione, invece, è piccolo: **8 riferimenti** in tutta
Aurora — 4 a `Teacher`, 3 a `SchoolClass`, 1 a `Subject`, **0** a `TimeSlot`.

### 1.4 Aurora non ha una coda, e ha un muro a 180 secondi

`requirements.txt`: Django, DRF, cors-headers, psycopg2, gunicorn, whitenoise,
requests, cryptography, openpyxl, ortools. **Nessun celery, nessun rq, nessun
thread di lavoro.** `docker-compose.prod.yml` ha tre servizi: db, backend,
frontend. La coda di ADR-027 §3 non è una scelta di implementazione da fare:
è **infrastruttura che non esiste**, ed è il pezzo più grosso di tutto questo.

E il muro è scritto in `entrypoint.sh` con il suo perché:
`gunicorn --timeout 180`, «gunicorn UCCIDE il worker che non ha risposto entro
quel tempo». Il commento dichiara che 180 basta a tutto tranne che alle Classi
Prime, e che quel numero e il budget del loro solver **si cambiano insieme**,
con un test che lo verifica.

Le nostre misure contro quel muro:

| | tempo |
|---|---|
| Fermi, `solve` | 1,6 s |
| Alighieri, `solve` senza criteri di qualità | 8,2 s |
| Alighieri, catena intera con gli otto criteri (`--limite 60`) | **378 s** |

⚠ **E i «82 s» che ADR-027 cita erano una catena troncata** — misurati prima
di L14, quando il nono livello su undici esauriva il budget e gli ultimi due
non partivano affatto. Il numero vero è più del doppio del muro, il che
**rafforza** l'argomento dell'ADR invece di indebolirlo: un solve per richiesta
non ci sta, e non ci sta di un fattore due, non di un margine.

### 1.5 ortools è già dentro Aurora, e il commento nomina questo modulo

In `requirements.txt`, sopra `ortools==9.15.6755`:

> *«Il solver delle classi prime. Pesa: con numpy e pandas al seguito sono
> ~200 MB nell'immagine… La dipendenza si ammortizza sul futuro modulo di
> generazione dell'orario, che senza un solver non si fa.»*

La dipendenza più cara di questo pezzo è **già pagata**, e chi l'ha pagata
sapeva per cosa.

### 1.6 Il dominio non sa di stare in un progetto

`domain/` non importa `config/` da nessuna parte: le occorrenze di `settings.`
nel codice sono `InstituteSettings`, cioè un dato, non la configurazione di
Django. Venti migrazioni, nessuna dipendenza da altre app.

⚠ L'unico attrito è il **nome**: l'etichetta dell'app è `domain`, che dentro
Aurora — accanto ad `api` — non dice niente a nessuno. Rinominarla costa una
riscrittura delle venti migrazioni, e va fatta **prima** che esistano dati.

### 1.7 I due banchi di prova non si sommano

| | test | tempo |
|---|---|---|
| Aurora, `manage.py test api` | 1614 | **249 s** |
| noi, giro rapido | 959 | **231 s** |
| noi, i sette file del banco che provano `INFEASIBLE` | 85 | **~21 min** |

Sommarli darebbe una suite da otto minuti buoni prima ancora del banco, e col
banco da mezz'ora. ⚠ Ma non si sommano **se l'app è sua**: il comando che Aurora
documenta è `manage.py test api`, che per costruzione non tocca le altre app
(un'integrazione continua non c'è — non esiste `.github/workflows`). È lo stesso
taglio che già usiamo fra giro rapido e file lenti, ottenuto con un
meccanismo che c'è di suo.

## 2. La topologia: il codice entra in Aurora come app

**Decisione: `domain/` diventa l'app `orario` dentro `Mactywd/aurora`, e ci va
per intero — modelli, solver, analisi, comandi, test, dataset.**

Il motivo è uno solo e non ammette sfumature: **la chiave esterna verso la
`School`.** ADR-027 §3.1 la vuole, e una FK ordinaria si scrive solo fra due
app della stessa installazione. Tutte e tre le alternative la comprano a un
prezzo che non vale la pena pagare.

### 2.1 Alternative considerate

1. **Un pacchetto installabile**, con la scuola presa da una `settings.ORARIO_SCHOOL_MODEL`
   sul modello di `AUTH_USER_MODEL`. Scartata: quel meccanismo funziona perché
   `User` è dichiarato `swappable`, e le migrazioni possono dipendere da un
   modello che non conoscono. `School` non lo è e non ha ragione di diventarlo
   per noi. Senza, le nostre migrazioni **congelano** `to='api.school'`, cioè
   il pacchetto non si sviluppa più da solo — che era tutto il motivo per
   tenerlo separato.
2. **Un pacchetto senza FK**, con un `school_id` intero. Scartata: perde la
   cascata e l'integrità referenziale, cioè proprio le due cose che rendono
   una tenancy verificabile. Cancellare una scuola lascerebbe 34 tabelle di
   orfani, e nessun vincolo del database direbbe niente.
3. **Copia vendorizzata** (subtree, submodule, copia a mano). Scartata: due
   copie dello stesso codice divergono, ed è alla lettera l'accumulo di
   versioni che le convenzioni di questo repository vietano.

⚠ **La conseguenza va guardata in faccia**: questo repository smette di essere
il posto dove il generatore si sviluppa. Ciò che resta qui — il reverse
engineering di EDT, i dataset, gli ADR, il changelog — è la parte che spiega
*perché* il codice è così, e senza il codice accanto si stacca dal suo
oggetto. Quindi **le vanno dietro anche i documenti**: `docs/edt/`, `data/`,
`decisioni.md`, `changelog.md`, `todo.md`. Il trasloco è un pezzo a sé (§5.2),
è un commit che non cambia comportamento, e il criterio di riuscita è che le
due suite restino verdi con gli stessi numeri.

## 3. Cosa fa la `School` alle 34 tabelle

1. **Tredici FK** (§1.1), `on_delete=CASCADE` come tutto il resto di Aurora.
2. **Nove unicità** diventano per scuola (§1.2): gli otto campi `unique=True`
   passano a `UniqueConstraint(school, campo)`, e `QualityCriterion` a
   `(school, kind, population)`.
3. **`InstituteSettings` diventa una riga per scuola** — cioè una FK
   `OneToOne`, non una `ForeignKey`: due righe di impostazioni per la stessa
   scuola sono uno stato che nessun lettore sa risolvere.
4. **Le 21 che ereditano non prendono niente**, e il test che lo difende è
   quello che conta: nessuna delle 34 deve poter essere raggiunta da una
   scuola per due cammini diversi.

## 4. Le quattro collisioni: chi vince

**Vincono le nostre**, per §1.3: sono un soprainsieme, e il verso opposto
perderebbe dati. Concretamente:

- `api.Teacher`, `api.SchoolClass`, `api.Subject` **spariscono**, e i loro 8
  riferimenti passano ai nostri modelli. Le righe esistenti si migrano
  (⚠ `name` → `last_name`, §1.3).
- `api.TimeSlot` diventa `SlotLabel` e `api.DayConfiguration` diventa la
  `TimeGrid`. ⚠ **Ma non sono lo stesso dato con due nomi**: `DayConfiguration`
  ammette un numero di ore **diverso per giorno**, la `TimeGrid` no — ha
  `slots_per_day` unico e i giorni corti si ottengono con le indisponibilità.
  La migrazione deve dire quale delle due semantiche sopravvive, e la risposta
  non è ovvia; è la sola delle quattro che apre una domanda invece di
  chiuderla.
- `ScheduleEntry` **resta dov'è e com'è**: è l'uscita (ADR-027 §3.2), non
  l'anagrafica, e ha già la maschera di validità (emendamento del 2026-09-01).

## 5. L'ordine dei pezzi

**§5.1 — La pubblicazione, e si può fare adesso.** Da `Placement` alla riga
piatta `(docente, giorno, ora, classe, materia, maschera)`. È una funzione
pura, si prova sul banco Alighieri con i dati che ci sono, e **non dipende
dalla topologia**: qui c'è già tutto tranne la scrittura finale, che è un
adattatore di poche righe. La perdita è quella misurata in ADR-027 — 139
chiavi su 142 — e il pezzo la ri-misura invece di fidarsi.

**§5.2 — Il trasloco.** L'app entra in Aurora col nome `orario`, migrazioni
riscritte sotto la nuova etichetta *prima* che esistano dati. Nessun cambio di
comportamento; il criterio è che le due suite restino verdi con gli stessi
numeri.

**§5.3 — La scuola.** Le 13 FK, le 9 unicità, `InstituteSettings` a riga per
scuola, e il test dei due cammini.

**§5.4 — Le collisioni.** Le tre tabelle che spariscono, gli 8 riferimenti che
si spostano, la griglia oraria con la sua domanda aperta.

**§5.5 — Il lavoro.** Coda, stato, polling — e prima di tutto la decisione su
*come*, dato che non c'è niente su cui appoggiarsi (§1.4). È qui che si
risponde a **L14 punto 2**, il budget dei livelli di qualità: davanti a un
lavoro la domanda cambia, ed è per questo che è stata lasciata aperta.

**§5.6 — Le rotte.** `analyze` sincrona, `export_ical` con la griglia mappata,
`extract` come parametro. Il gate del modulo (`modules.py`) e il flag sulla
`School`.

## 6. Cosa questo documento non decide

- **Se il repository `orariogen` si archivia** dopo §5.2, o resta come storia.
  È una decisione di chi lo possiede, non una conseguenza tecnica.
- **Come si fa la coda** — §5.5 dice che va decisa, non quale sia la risposta:
  un processo dedicato nel compose, un thread, un comando che gira a
  intervalli. Vuole le sue misure, come le ha volute tutto il resto.
- **La semantica della griglia** in §4: se sopravvive il giorno a lunghezza
  variabile di Aurora o la griglia rettangolare nostra.
- **La UI, il prezzo, il calendario** — già dichiarati fuori da ADR-027.
