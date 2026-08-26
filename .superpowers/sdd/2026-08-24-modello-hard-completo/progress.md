# SDD ledger — plan: docs/superpowers/plans/2026-08-24-modello-hard-completo.md

Spec: docs/superpowers/specs/2026-08-24-modello-hard-completo-design.md (letta)
Worktree: .claude/worktrees/modello-hard-completo, branch worktree-modello-hard-completo
Base: 9d5680d (EnterWorktree era partito da 1d079dc, indietro di 5 commit —
stesso inciampo dei piani 1, 2 e 3; allineato con `git reset --hard master`)
venv: symlink a /home/mattia/coding/scuola/orariogen/venv (il worktree non ne ha uno)
Baseline: 173 test verdi, misurati con `venv/bin/pytest` nel worktree

## Pre-flight scan

### Coppie di task che condividono file o interfacce

| task A | task B | file / interfaccia | esito |
|---|---|---|---|
| 1 | 2, 10 | `domain/solver/vocabulary.py` | T1 crea, T2 aggiunge materia/posizione/sede, T10 aggiunge `subject_literals`. Progressione additiva, nessuna riscrittura |
| 1 | 4 | `builders/time_constraints.py` | T1 lo modifica (usa `covered`), T4 lo cancella spostando `MaxGapBuilder` in `time_presence.py`. Ordine coerente: il lavoro di T1 sopravvive nel file nuovo |
| 4 | 6, 8 | `builders/time_presence.py` | T4 crea, T6 riscrive `MaxGapBuilder` su `ResourceBuilder`, T8 aggiunge `MaxPresenceBuilder`. Coerente |
| 4 | 10, 11 | `builders/subject_buckets.py` | T4 crea, T10 aggiunge lo scheletro + 2 builder e riscrive `SameDayBuilder`, T11 aggiunge 3 builder. Coerente |
| 6 | 10 | `builders/base.py` | T6 crea con `ResourceBuilder`, T10 aggiunge `SubjectBuilder`. Due classi indipendenti, nessuna collisione |
| 6 | 7 | `builders/time_counting.py` | T6 crea (2 tetti), T7 aggiunge (3 minimi). Additivo |
| 3 | 6 | `domain/solver/residual.py` | T3 crea, T6 aggiunge `frozen_occupies`. Additivo |
| 12 | 13, 14 | `builders/subject_order.py` | T12 crea, T13 e T14 aggiungono un builder ciascuno. Additivo |
| 4, 9, 12, 15, 16 | fra loro | `builders/__init__.py` | ogni task riscrive gli import per intero. Rischio noto (identico ai piani 1-3): un task che dimentica un import spegne builder gia' registrati. Mitigazione: il test di copertura del registro (T5) e' in suite da T5 in poi e fallisce se un builder sparisce |
| 3 | 17 | `tests/test_solver_oracle.py` | T3 rende l'oracolo differenziale (`violazioni` -> set, nuova `nuove`), T17 aggiunge il Fermi con tutti i vincoli usando quelle funzioni. Coerente |
| 5 | 6..16 | `tests/solver_harness.py` | T5 crea `build_witness`/`DERIVERS`/`run_family`, gli undici task successivi aggiungono derivatori. Additivo **tranne** T9 (aggiunge le sedi alla scuola del testimone) e T15 (aggiunge le partizioni): entrambi cambiano la forma dell'orario testimone sotto i derivatori gia' scritti. Vedi Ruling 2 |
| 2 | 12, 13, 15 | `vocab.subject_activities` | il blocco «Produces» di T2 **non lo elenca**, ma il codice dello Step di T2 (piano riga 506) lo definisce e la prosa di T2 lo nomina. Omissione di documentazione, non di sostanza. Vedi Ruling 3 |
| 1 | — | `SolverContext.occupied` | T1 dichiara di rimuoverlo, ma **`tests/test_solver_context.py:72-73` lo usa** e non compare nella lista Files di T1. Vedi Ruling 1 |
| 4 | — | `tests/test_solver_max_gap.py`, `test_solver_same_day.py` | verificato: importano `domain.solver.model.solve`, **non** i moduli dei builder. Lo spostamento di T4 non li tocca. Nessuna modifica necessaria |

### Coerenza interna di ogni task

| task | verificato | esito |
|---|---|---|
| 1-17 | ogni task ha blocchi **Files**, **Interfaces**, Step numerati con codice completo | presenti in tutti e diciassette |
| tutti | i builder registrati contro i derivatori attesi | 23 `@register` nel piano + 3 preesistenti = 26; 26 `@deriver`. Corrispondenza uno a uno (riverificato in worktree) |
| tutti | segnaposto / TODO / `...` lasciati nel codice del piano | nessuno |
| 5 | il test di copertura del registro esiste prima dei builder che deve sorvegliare | si', T5 precede l'ondata 3 |
| 7 | dichiara di **non** usare `residual_cap` | coerente con la spec §3.1 (minimi, non tetti). Non e' una svista |

## Rulings pre-flight

Ruling 1: T1 deve anche aggiornare `tests/test_solver_context.py` — la coppia
di righe che chiama `ctx.occupied(model, ...)` va spostata/riscritta su
`vocab.occupied` (senza `model`), non cancellata. — Motivo: rimuovere
`SolverContext.occupied` senza toccare il suo unico test lascia la suite rossa,
e cancellare il test violerebbe il vincolo globale 2 (nessun task riduce il
numero di test). — Costo se sbagliato: nullo; e' la manutenzione minima di un
test esistente.

Ruling 2: T9 e T15 devono eseguire la **suite intera**, non solo il proprio
file di test, e il loro brief lo dice esplicitamente. — Motivo: sono i due soli
task che cambiano la scuola del testimone (sedi, partizioni) sotto derivatori
gia' scritti; un derivatore che smette di valere si vede solo lanciando tutto.
— Costo se sbagliato: nullo, e' solo tempo di CPU. Il vincolo globale 2 lo
impone gia' a tutti, qui e' un promemoria mirato.

Ruling 3: nessuna azione sull'omissione di `subject_activities` dal blocco
«Produces» di T2. — Motivo: il codice dello Step lo definisce e il brief lo
contiene per intero; correggere il piano a meta' esecuzione costerebbe piu' di
quanto vale. Annotato qui perche' un reviewer di T12 potrebbe segnalarlo come
interfaccia non dichiarata. — Costo se sbagliato: un giro di review su un
falso positivo.

## Task log

Task 1: implementato (commit 6e5050d, 177 test). Review: spec ✅, 1 Important
(il default `signature=None` non e' piu' documentato in nessuna delle quattro
primitive — il diff ha cancellato l'unico punto del codice che ne diceva la
semantica), 6 Minor.

Task 1: minor (deferred): `half_of` e' codice morto finche' un builder non lo
usa (plan-mandated, sta nel brief; il Task 2 introduce `bucket_of`, che e' il
consumatore naturale).
Task 1: minor (deferred): i nomi CP-SAT di `covered` non distinguono gli span
(usano solo `span[0]`) — leggibilita' di `model.Proto()`, non correttezza.
Task 1: minor (deferred): ramo irraggiungibile `span[0] if span else 'x'`.
Task 1: minor (deferred): `covered` restituisce il dizionario memoizzato per
riferimento; un chiamante che lo muta corrompe la cache.
Task 1: minor (deferred): il report parafrasa un output di grep invece di
incollarlo. Il revisore ha verificato che l'affermazione e' vera.

Ruling 4: la voce ⚠️ del revisore su `span`/MAX_PRESENCE non e' una lacuna. Il
Task 8 la copre esplicitamente («`span` e' la giornata intera»), ed e' per
costruzione non verificabile finche' quel consumatore non esiste. — Costo se
sbagliato: nullo, il Task 8 la verifica comunque.

Ruling 5: la seconda voce ⚠️ del revisore **e' una lacuna vera del piano**.
`MaxGapBuilder` posta contro `row.params["max_gap_minutes"]` grezzo, e nessun
task lo dota della regola ADR-018 — verificato leggendo lo Step 4 del Task 6
(piano riga ~1450), che lo riscrive sullo scheletro lasciando il tetto crudo.
Se le sole attivita' congelate sforano gia' il budget settimanale dei buchi, il
modello diventa INFEASIBLE per colpa del passato: esattamente cio' che ADR-018
vieta. Decisione: la correzione appartiene al **Task 6**, non al Task 1, e
viene portata nel suo dispatch come requisito aggiuntivo — `MaxGapBuilder.post`
salta il vincolo per quella firma quando la somma dei buchi indotti dalle sole
congelate supera gia' `max_gap_minutes`, con lo stesso commento ADR-018 di
`MaxPresenceBuilder`. Il guardiano sta a livello di settimana, non di mezza
giornata, perche' il D.T.B. e' un budget settimanale confrontato una volta
sola. — Costo se sbagliato: il modello resta piu' largo del checker su input
gia' sporco, cosa che l'oracolo **differenziale** tollera per definizione
(nessun finding *nuovo*); su input pulito non cambia nulla, perche' senza
congelate il guardiano non scatta mai.

Ruling 6: al giro di correzione del Task 1 aggiungo un requisito che il
revisore aveva classificato Minor — un test che eserciti davvero `signature=`
su `day_active`/`half_active`, piu' il caso positivo di `half_active`. —
Motivo: il contratto che l'osservazione Important chiede di scrivere nei
docstring e' esattamente l'asse su cui questo repository ha gia' sbagliato tre
volte, e un contratto affermato solo in prosa non e' un contratto. — Costo se
sbagliato: qualche minuto e due test in piu' su una fondazione che ne regge
sedici task.

Task 1: fix round 1/5 (3 addressed, 0 open; commits 6e5050d..e4b6f9f)
Task 1: complete (commits 9d5680d..e4b6f9f, review clean, 179 test verdi)

Task 2: complete (commits e4b6f9f..ccfd78b, review clean, 183 test verdi)
Task 2: minor (deferred): nessun test esercita `signature` su `subject_bucket`
e `site_occupied` (il revisore ha verificato per lettura che il filtro e'
corretto e simmetrico a quello del Task 1). Omissione del brief, non
dell'implementatore.
Task 2: minor (deferred): `subject_activities` non ha un test dedicato.
Task 2: minor (deferred): il report dell'implementatore sbaglia due numeri
auto-riferiti (righe aggiunte, «sei metodi privati» che sono cinque pubblici).

Ruling 7: la voce ⚠️ del revisore sul conteggio dei test non e' una lacuna. Il
brief del Task 2 elenca quattro funzioni di test nello Step 1 ma piu' avanti ne
dichiara «due» — incoerenza del piano; l'aritmetica reale (179 + 4 = 183)
quadra col diff. — Costo se sbagliato: nullo, il numero e' verificabile a ogni
esecuzione.

Task 3: implementato (commit 316f38c, 188 test). Review: spec ✅ sul cuore
ADR-018 (nessun clamp sui minimi, partizione esaustiva e disgiunta,
`test_oracolo_puo_fallire` conserva il potere discriminante), 1 Important:
`nuove()` eredita da `Finding.key` la fusione fra firme di settimana e puo'
tacere su una violazione nuova introdotta in una firma diversa.
Task 3: minor (deferred): `split` e' cieco alla firma — una riga di docstring
che dica «`terms` deve arrivare gia' filtrato alla firma» starebbe dove verra'
letta dai quattordici task successivi.
Task 3: minor (deferred): `codici` di `nuove()` puo' divergere da quello con
cui e' stato calcolato `prima` (accoppiamento non dichiarato).
Task 3: minor (deferred): `pytestmark = django_db` in `test_solver_residual.py`
paga una transazione per test senza toccare l'ORM (plan-mandated).
Task 3: minor (deferred): due casi limite scoperti in `test_solver_residual.py`
— `split(ctx, [])` e il caso «tutti liberi».

Ruling 8: l'osservazione Important sull'oracolo differenziale e' accolta, e la
correzione e' quella proposta dal revisore — espandere per settimana
(`{(f.key, w) for f in ... for w in f.weeks}`) invece di collassare. — Motivo:
`Finding.key` esclude `weeks` **per costruzione** (serve al dedup fra firme in
`check_schedule`), quindi due firme che producono la stessa violazione sulla
stessa risorsa collidono; su `max_gap` la chiave non contiene nemmeno le
attivita', solo risorsa e due numeri. E' la stessa dimensione da cui e' gia'
passato il difetto del 2026-08-24, stavolta travestita da oracolo. — Costo se
sbagliato: l'oracolo diventa piu' severo del necessario e potrebbe segnalare
come «nuova» una violazione preesistente **migrata** in un'altra settimana; ma
quella e' davvero nuova in quella settimana, quindi il verso dell'errore e'
quello sicuro.

Ruling 9: al giro di correzione aggiungo un requisito classificato Minor dal
revisore — un test che fissi la semantica di `nuove()`. — Motivo: e' l'unica
funzione introdotta qui su cui i quattordici task successivi appoggiano il
criterio di riuscita, non e' esercitata da nessun test, e questo giro **ne
cambia la semantica**. Cambiare il comportamento di una funzione non testata
senza aggiungerne uno lascia la correzione stessa non verificata. — Costo se
sbagliato: tre righe di test in piu'.

Task 3: fix round 1/5 (2 addressed, 0 open; commits 316f38c..16108cc)
Task 3: complete (commits ccfd78b..16108cc, review clean, 189 test verdi)
Task 3: minor (deferred): l'espansione per settimana produce un falso «nuovo»
quando una violazione preesistente **migra** da una firma all'altra (il solver
chiude il buco nella settimana 0 e ne apre uno identico nella settimana 1).
Verso gia' giudicato sicuro (Ruling 8), ma non documentato: ne' la docstring di
`nuove()` ne' un commento lo dicono. Da portare nel dispatch del Task 6, che e'
il primo consumatore di `nuove()`.

Task 4: complete (commits 16108cc..b0df969, review clean, 189 test invariati)

Ruling 10: il brief del Task 5 definisce un proprio `_hard(schedule, codes)`
che colassa per chiave (`{f.key for f in ...}`), cioe' la forma che il giro di
correzione del Task 3 ha appena dichiarato insufficiente per `violazioni()`.
**Qui e' corretta**: `run_family` confronta con l'insieme **vuoto** in
entrambi i punti (`prima == set()`, `dopo == set()`), e per una tale
asserzione assoluta l'espansione per settimana non aggiunge nulla — se una
violazione esiste in una settimana qualsiasi, la chiave compare comunque.
Resta pero' un helper quasi-omonimo con semantica diversa da quella
appena corretta, a due file di distanza. Decisione: si tiene la forma del
brief, **con una riga di commento** che dica perche' qui puo' collassare le
settimane e `violazioni()` no. — Costo se sbagliato: un commento in piu'; il
rischio che evita e' che qualcuno copi `_hard` in un contesto differenziale,
che e' esattamente l'errore appena corretto.

Task 5: implementato (commit 4f56aab, 216 test). Review: spec ❌, 3 Important.
(1) la famiglia `structural:grid` e' **integralmente vacua** — la fixture non
crea ne' `Holiday` ne' `Break`, e tutte le attivita' hanno `duration_slots=1`,
quindi svuotare `GridBuilder.restrict` lascerebbe tutti e cinque i semi verdi;
due dei tre codici dichiarati non possono fisicamente essere emessi.
(2) la derivazione vacua e' indistinguibile da un successo, e la spiegazione
del report sui «2 semi su 5» non regge: `_derive_same_day` accetta anche una
coppia con **una sola** attivita', che crea una riga impossibile da violare.
(3) la fixture costruisce `Service` incoerenti (le due classi condividono lo
`StudyPlan`, quindi i `class_minutes` si sommano).
Task 5: minor (deferred): `MASKS` non puo' produrre piu' di **due** firme di
settimana; la molteplicita' e' asserita solo per `seed=1`; import a meta' file;
il docstring di `_derive_max_gap` sopravvaluta la forza del test («stretto» per
una sola firma); commento di `_hard` con referente ambiguo; il controllo di
copertura e' unidirezionale (un derivatore orfano non viene segnalato);
`Deriver.fn: object` e' un'annotazione che non annota.
Task 5: minor (deferred): identificatori in italiano nel banco (`celle`,
`ordine`, `fasce`...) contro il vincolo globale 3 — plan-mandated, e' il testo
del brief. Da valutare alla review finale: correggerli **ora** significherebbe
riscrivere il brief di dodici task che ci si appoggeranno.

Ruling 11: accolte tutte e tre le Important. La (3) merita una parola: il
revisore la motiva con un builder futuro per `structural:coverage`, che **non
esiste in questo piano** (la spec §4.4 dichiara che quella famiglia non ha
builder perche' il checker e' `PLACEMENT_INDEPENDENT`). Il rischio prospettico
quindi non si materializza qui. La correggo lo stesso perche' e' un difetto
della fixture in se', costa poco, e adesso e' il momento piu' economico —
nessun builder ci si appoggia ancora. — Costo se sbagliato: il testimone
cambia forma prima che dodici task lo usino, il che e' il verso giusto in cui
sbagliare.

Ruling 12: la Minor su `MASKS` (mai piu' di due firme) resta differita.
— Motivo: due firme **bastano** a esercitare la dimensione — e' esattamente
quello che fa il test multi-firma dell'oracolo, che ha scoperto il difetto del
2026-08-24. Una terza firma aggiungerebbe copertura marginale a un giro di
correzione gia' carico di tre osservazioni che toccano la fixture. — Costo se
sbagliato: una dimensione esercitata al minimo sindacale invece che
abbondantemente.

Task 5: fix round 1/5 (3 addressed, 0 open; commits 4f56aab..9da64e3)
Task 5: complete (commits b0df969..9da64e3, review clean, 216 test verdi)
Task 5: minor (deferred): resta un `coverage_mismatch` nel testimone (maschere
di settimana parziali contro `Service.class_minutes` a somma piena su tutte le
settimane). Non tocca nessuna delle famiglie tracciate e `structural:coverage`
non ha builder in questo piano; diventera' rilevante solo se un giorno ne
avra' uno.

Ruling 13 (scoperta della ri-review, non un'osservazione): **CP-SAT gira non
deterministico in questo repository** — `domain/solver/model.py` non fissa ne'
`random_seed` ne' `num_search_workers` (default 0 = auto-parallelo su 12
core), quindi lo stesso modello puo' restituire soluzioni diverse fra
esecuzioni. E' cio' che spiega il «4/5» della prova di falsificabilita': il
seme che sopravvive **cambia** a ogni esecuzione, cosa che una vacuita'
strutturale non farebbe. Decisione: non lo si fissa adesso. — Motivo: toccare
`model.py` non appartiene a nessun task del piano, e per il banco la non
determinismo e' un'arma a doppio taglio utile (esplora soluzioni diverse a
ogni esecuzione, quindi scopre le larghezze che un solver deterministico
mancherebbe sempre). Il punto 2 di `run_family` (INFEASIBLE) resta comunque
deterministico. — Conseguenza operativa, da ricordare per i dodici task
successivi: **un fallimento intermittente del banco non e' rumore da
rilanciare, e' una larghezza vera del builder colta in una soluzione diversa.**
Da portare alla review finale di branch come decisione da confermare.

Task 6: implementato (commit d410745, 243 test), DONE_WITH_CONCERNS. Review:
spec ✅ sulle tre traduzioni (verificate riga per riga contro
`time_constraints.py`) e sul guardiano D.T.B. **a livello di settimana**; 2
Important, entrambe da una riga.

Ruling 14: **la mia Ruling 5 era giusta nel problema e sbagliata nel rimedio.**
Avevo ordinato che `MaxGapBuilder` **saltasse** il vincolo quando le sole
congelate sforano il budget. Il revisore ha mostrato che saltare spegne il
D.T.B. per **l'intera settimana**, cioe' anche sui giorni che le congelate non
toccano: le libere possono allora aggiungere buchi illimitati, e un `max_gap`
che passa da `gap_minutes=60` a `300` e' una **chiave diversa** (le
`quantities` stanno in `Finding.key`), quindi `nuove()` la conterebbe come
nuova e il criterio differenziale cadrebbe comunque. La forma corretta e'
**clampare**: `<= max(cap, buchi_congelati)`, che e' l'analogo esatto di
`max(0, cap - congelate)` di `residual_cap` — concede al modello il debito gia'
contratto e nulla di piu'. Adottata. — Costo se sbagliato: nessuno rispetto al
salto, che era strettamente peggiore.

Ruling 15: promuovo a requisito del giro di correzione la Minor sul disarmo
della rete di sicurezza del registro (`assert self.TYPE is not None` in testa a
`ResourceBuilder.build`). — Motivo: da questo task in poi **ogni** sottoclasse
supera `test_ogni_builder_implementa_almeno_un_hook` per eredita', anche se
dimentica `TYPE` o `post`; e un builder con `TYPE = None` non fa match con
nessuna riga ed e' silenziosamente vacuo. Sei builder ereditano questo
scheletro nei tre task successivi: e' il momento in cui la riga costa meno. —
Costo se sbagliato: una riga di assert.

Ruling 16 (azione del controller, non dell'implementatore): i blocchi
`test_*_sul_banco` che i brief dei task 7-16 fanno scrivere sono **duplicati**
di `test_famiglia`, gia' parametrizzato su `sorted(DERIVERS) x [1..5]` in
`tests/test_solver_witness.py`: registrare un derivatore genera il test da
solo. I dieci gia' scritti restano (toglierli ridurrebbe il conteggio, contro
il vincolo globale 2), ma **dai task 7 in poi non se ne aggiungono altri**, e
lo diro' in ogni dispatch. — Motivo: sono i test piu' lenti della suite e ai
task 7-9 diventerebbero trenta esecuzioni duplicate. — Costo se sbagliato:
nulla, la copertura e' identica; cambia solo chi genera i casi.

Task 6: minor (deferred): tre espressioni inline della stessa regola di clamp
ADR-018 (`residual_cap`, `MaxHalfDaysBuilder`, `MaxGapBuilder`) — un
`residual_const(cap, consumo)` le terrebbe in un posto solo.
Task 6: minor (deferred): `_frozen_gap_minutes` e' la **terza** copia della
formula del buco, dopo il checker e il derivatore. Attraversa tre strati che
non devono dipendersi, quindi e' accettabile, ma e' la formula che questo
progetto ha gia' sbagliato una volta: un commento incrociato costerebbe una
riga.
Task 6: minor (deferred): `_derive_max_half_days` crea la riga di vincolo anche
quando ritorna 0.

Task 6: fix round 1/5 (3 addressed, 0 open; commits d410745..28c90ef)
Task 6: complete (commits 9da64e3..28c90ef, review clean, 244 test verdi)

Task 7: implementato (commit 8193f82, 262 test + 2 skip). Review: spec ❌,
2 Important, **entrambe dimostrate con istanze minime riprodotte dal revisore**.

Ruling 17: **la spec sbaglia, ed e' la quarta volta della stessa famiglia.** La
spec §3.1 e il brief del Task 7 dichiarano che un minimo garantito «non e' mai
infattibile per colpa del passato», e su quella base era stato **vietato**
qualunque residuo. E' vero solo per la meta' additiva del ragionamento: le
congelate contribuiscono a favore *dentro* `occupied`, ma su `ARRIVAL_DEPARTURE`
e `FREE_GUARANTEED` possono anche **consumare** la quantita' contata — una
congelata in una fascia proibita forza `conforme = 0` per quel giorno, una
congelata in un giorno forza `libero = 0`, e nessuno dei due si recupera
muovendo le libere. Il revisore l'ha riprodotto: `INFEASIBLE` in entrambi i
casi, e ha fatto la **controprova** che `MIN_DISTRIBUTION` invece regge davvero
(`OPTIMAL`), quindi l'asimmetria e' reale e non generale. Decisione: si corregge
**qui**, con il residuo *per forzatura* (contare con `frozen_occupies` i giorni
gia' persi e abbassare la soglia a cio' che resta ottenibile), non con
`residual_cap` e non con un clamp a zero. — Motivo: lasciarlo alla spec del
modello completo significherebbe tenere in repo due builder che smettono di
piazzare su input sporco, cioe' proprio cio' che ADR-018 dichiara inaccettabile.
— Costo se sbagliato: un vincolo piu' lasco del checker su input gia' sporco,
che l'oracolo differenziale tollera per definizione.
Conseguenza: **il Task 17 deve correggere il testo della spec §3.1**, che oggi
afferma come impossibile un comportamento riprodotto in due righe. Annotato qui
perche' il Task 17 e' quello che tocca la spec.

Ruling 18: promuovo a requisito del giro di correzione la Minor sul test
mancante per la **prima** trappola (giorno vuoto = conforme su
`ARRIVAL_DEPARTURE`). — Motivo: entrambi i test mirati esistenti riempiono tutti
e cinque i giorni, quindi un builder che trattasse il giorno vuoto come
violazione li supererebbe entrambi; e la correzione della Ruling 17 tocca
esattamente quella logica. — Costo se sbagliato: un test in piu'.

Task 7: minor (deferred): la coppia `if lits: AddMaxEquality else: Add(var==0)`
e' il **quarto** punto del repo in cui la stessa guardia e' riscritta a mano —
una primitiva `occupied_any(key, day, slots, signature)` servirebbe anche a
`MAX_PRESENCE` (Task 8) e ai vincoli di sede (Task 9).
Task 7: minor (deferred): i riferimenti di riga del report al checker sono
sfalsati di 2-7 righe (il codice citato e' verbatim corretto, la numerazione no).
Task 7: minor (deferred): `residual_floor` resta senza un solo chiamante anche
dopo il task interamente dedicato ai minimi. Da decidere alla review finale se
e' destinato a un builder futuro o se e' un helper morto.
Task 7: minor (deferred): la riga di riepilogo pytest incollata nel report ha
separatori di larghezza non standard — probabile ritocco a mano del riepilogo.

Task 7: INTERROTTO A META'. Su richiesta esplicita dell'utente ho committato le
modifiche in volo dell'implementatore come `24a544d` («wip(solver): istantanea
del giro di correzione del Task 7, non verificata»), e ho pushato il branch su
origin. Subito dopo **l'utente ha fermato l'implementatore**, che stava per
lanciare la suite intera. Stato reale: le due correzioni Important sembrano
scritte (74 righe in `time_counting.py`, 151 in `test_solver_time_minimums.py`)
ma **nessuna suite e' stata lanciata su quel contenuto**, non c'e' rapporto di
correzione nel file di report, e la ri-review del giro non e' mai partita.
Per riprendere: lanciare `venv/bin/pytest`, e se verde generare
`review-8193f82..<head>.diff` e dispiegare la ri-review sulle due osservazioni
Important del Task 7. Se rossa, il giro 2 riparte da li'.

Task 7: fix round 1/5 (3 addressed, 2 nuove aperte; commits 8193f82..24a544d).
Suite misurata dal controller su 24a544d: 267 passed, 2 skipped.
Le tre osservazioni originali sono chiuse, ma il diff ne introduce due:
(a) il bound di `free_half_days` e' **sovrastimato** (`2*giorni - mezze_perse`),
mentre una giornata puo' contribuire al massimo **una** mezza libera — con due
congelate sulle due meta' dello stesso giorno il modello e' ancora INFEASIBLE
per colpa del solo passato, e con soglia 4 la stessa istanza e' OPTIMAL;
(b) la docstring di `MinDistributionBuilder` dichiara un'immunita' al passato
falsificabile in tre righe (il codice invece e' giusto e non va toccato).

Ruling 19: **(a) e' colpa mia.** Nel messaggio del giro 1 avevo dettato la forma
del residuo ripetendo la proposta del revisore precedente
(`min(soglia, ottenibili)` con `ottenibili = 2*giorni - perse`), senza verificare
che il massimo raggiungibile per `free_half_days` non e' due per giorno ma
**uno**: `libera = attivo AND NOT meta`, quindi un giorno attivo ha per forza
una meta' occupata e un giorno inattivo ne da' zero. Il bound corretto e'
`min(minimo_mezze, giorni - giorni_interamente_persi)`. — Costo se sbagliato:
il vincolo diventa piu' lasco del checker su input sporco, che l'oracolo
differenziale tollera.

Ruling 20 (scoperta fuori ambito, non un'osservazione): **il banco a testimone
non congela mai nulla** — `run_family` cancella tutti i `Placement` e risolve da
zero — quindi ADR-018 non e' esercitato da nessuna delle famiglie sul banco, per
costruzione. E' la ragione per cui ogni difetto di residuo di questo piano e'
emerso solo dai test mirati o dalle sonde dei revisori, mai dal banco. Decisione:
**non** si estende il banco adesso. — Motivo: significherebbe riaprire il Task 5
a meta' ondata dei builder e cambiare la forma del testimone sotto sette
derivatori gia' scritti; e i test mirati per ADR-018 esistono, famiglia per
famiglia. — Costo se sbagliato: il residuo resta coperto da test scritti a mano
invece che generati, quindi da una copertura che vale quanto l'immaginazione di
chi li scrive. **Da portare alla review finale di branch come lacuna strutturale
dichiarata**, e da valutare come primo candidato per il piano successivo.

Task 7: fix round 2/5 (commit 7e88822, 269 passed + 2 skipped). Chiuso dal
controller: il secondo implementatore aveva scritto entrambe le correzioni nel
working tree ed e' stato fermato prima della suite e prima dei test. Ho
verificato il suo lavoro, aggiunto i due test mirati mancanti, eseguito le
prove RED (giro 2: vecchio bound `2*giorni` -> INFEASIBLE sulla sonda; giro 1:
`if not len(span): continue` -> INFEASIBLE sul pomeriggio vuoto), e ricostruito
il rapporto dei due giri in `task-7-report.md` con la nota di provenienza in
testa. La correzione di Important 1 e' quella dettata dalla Ruling 19:
`giorni_interamente_persi` invece di `mezze_perse`, soglia
`min(minimo, days_per_cycle - giorni_interamente_persi)`. Important 2 tocca la
sola docstring: il codice di `MinDistributionBuilder` non e' stato modificato.
Ri-review mirata sulle due osservazioni dispiegata su 24a544d..7e88822.

Ruling 21: il rapporto di un task passato di mano piu' volte va marcato come
**ricostruito**, con l'indicazione di chi ha scritto cosa, invece di essere
riscritto in prima persona come se un solo autore avesse fatto tutto. — Motivo:
il Task 7 ha attraversato due implementatori interrotti e il controller; un
rapporto in prima persona avrebbe attribuito a un autore inesistente prove che
nessuno di loro ha eseguito, e il revisore non avrebbe saputo dove guardare per
le incoerenze fra codice e commenti — che e' esattamente il difetto tipico di
un file scritto a piu' mani (Important 2 del giro 1 era proprio quello).
— Costo se sbagliato: nullo, e' solo una nota di provenienza in piu'.

Task 7: ri-review giro 2 — **entrambe le Important chiuse, nessun giro 3**.
Rapporto in `task-7-rereview-giro2.md`. Il revisore non si e' fermato alla
prova RED: ha ricostruito la tabella caso-per-caso del contributo del checker
contro quello del modello per ogni forma di giornata (vuota / una meta' / due
meta' / meta' congelata / meta' strutturalmente vuota) e dimostrato che
`sum(mezze_libere)` **coincide** con `free_halves` del checker — quindi il
bound e' esatto, non solo meno sbagliato, e sulle istanze soddisfacibili la
traduzione e' esatta. `MinDistributionBuilder.post` verificato identico a
`24a544d` per **confronto di AST** (docstring escluse), non a occhio.
Fuzz di 40 istanze **con congelate** su FREE_GUARANTEED (40/40 verdi, 24/40
rosse a builder disabilitato: discrimina) e altrettante su ARRIVAL_DEPARTURE.
Nessuna intermittenza in 6 rilanci. Suite: 269 passed, 2 skipped.

Task 7: **complete** (commit 7e88822).

Task 7: minor (deferred): il clamp scatta anche su input **pulito** quando il
parametro e' irraggiungibile (`free_half_days=6` su 5 giorni -> OPTIMAL con
soluzione bocciata dal checker). Nessuna soluzione legale persa — il vincolo e'
insoddisfacibile comunque — ma i tre rami si comportano in **tre modi diversi**
sul parametro impossibile. E' validazione dei `params`, non traduzione.
Task 7: minor (deferred): deriva fra commento e codice in
`tests/solver_harness.py` (`_derive_free_guaranteed` cita una guardia caduta in
`24a544d`). Preesistente, fuori dal diff.

Ruling 22 (correzione di una mia Ruling, la terza): la Ruling 19 chiude con
«il vincolo diventa piu' lasco del checker su input sporco, che l'oracolo
differenziale tollera». **Non e' letteralmente vero**, e il revisore l'ha
dimostrato: `Finding.key` include le `quantities`, quindi appena il solver
*migliora* una quantita' (es. `free_half_days` da 0 a 2) la chiave cambia e
`nuove()` la conta come violazione **nuova**. L'oracolo differenziale tollera
il finding che resta identico, non quello che migliora. Oggi non morde perche'
`free_guaranteed` non e' fra i `CODICI` dell'oracolo. — Decisione: **non** si
tocca `nuove()` adesso; si porta al **Task 17**, che allarga l'insieme dei
codici ed e' il punto in cui il difetto diventerebbe reale. — Costo se
sbagliato: il Task 17 apre con un falso positivo dell'oracolo e va corretto
li'. Annotato anche perche' e' la seconda volta su questo piano che una mia
Ruling dichiara una proprieta' vera «per costruzione» che non regge alla
verifica (la prima e' la Ruling 19 stessa, corretta dalla 19).

Ruling 23 (pre-dispatch del Task 8): **il piano sbaglia ADR-018 su
MAX_PRESENCE, ed e' la Ruling 14 daccapo.** Il codice del Task 8 (piano riga
~2020) fa `continue` sul giorno in cui le sole congelate hanno gia' sforato il
tetto di presenza, col commento «le libere non possono ridurre una presenza,
quindi il vincolo e' perso comunque». La premessa e' vera — `_presence_minutes`
e' `ultima - prima + 1` ed e' monotona non decrescente — ma la conclusione no:
saltare il vincolo lascia le libere **allargare** quella giornata. Con
congelate alle fasce 0-2 (presenza 180) e tetto 120, saltando il vincolo una
libera puo' andare alla fascia 5 e portare la presenza a 360. E il finding
`max_presence` porta `minutes=presence` fra le `quantities`, che entrano in
`Finding.key`: la violazione **peggiorata e' una violazione nuova** per
l'oracolo differenziale (vedi Ruling 22). Quindi il `continue` non e' solo piu'
largo del necessario, **rompe il criterio di riuscita**. Decisione: il Task 8
deve **clampare**, non saltare — `cap_effettivo = max(cap, presenza_congelate)`
per quel giorno, esattamente la forma di `MaxGapBuilder`. Nel caso pulito
`presenza_congelate <= cap` e non cambia nulla. — Costo se sbagliato: nessuno
che io veda; il clamp e' sempre almeno stretto quanto il `continue`.

Ruling 24 (pre-dispatch del Task 8): il derivatore `_derive_max_presence` del
piano **non ha `return`** (quindi `None`, e la convenzione di `run_family` sul
potere vincolante non scatta) e **non ha guardia di vacuita'**. Va allineato
agli altri nove del file: `return 0` quando il vincolo derivato non vieta
nulla — cioe' quando `picco` copre gia' la giornata intera **e** `giorni`
copre gia' `days_per_cycle` — e `return 1` altrimenti. — Motivo: senza, due
dei cinque casi parametrizzati sarebbero verdi senza aver testato niente, lo
stesso difetto che la review del Task 5 ha gia' dovuto correggere tre volte.
— Costo se sbagliato: un derivatore che si dichiara vacuo troppo spesso, cioe'
qualche `pytest.skip` in piu'.

Ruling 25 (pre-dispatch del Task 8): il ramo `days` che scrive
`max(0, max_days - consumo)` a mano **non viola** il vincolo globale «nessun
builder calcola a mano un residuo». `residual_cap` lavora su termini
`(peso, id, letterale)` per attivita', mentre qui i termini sono **variabili
derivate** (`day_active`): e' il caso esplicitamente previsto dalla docstring
di `frozen_occupies`, e i Task 6 e 7 fanno gia' cosi'. Annotato perche' un
revisore potrebbe segnalarlo come violazione. — Costo se sbagliato: un giro di
review su un falso positivo.

Task 8: implementato (commit 04c793f, pushato, 279 passed + 2 skipped, +10 sulla
baseline: 5 test mirati + 5 casi della famiglia sul banco). Le tre Ruling del
dispatch risultano applicate: clamp `max(cap, _frozen_presence_minutes(...))`
invece del `continue` del piano (23), derivatore con `return 0/1` e guardia di
vacuita' (24), `max(0, max_days - consumo)` lasciato a mano (25). Nessun
`test_max_presence_sul_banco` (16). Due deviazioni dichiarate
dall'implementatore, entrambe da verificare in review:
(a) ha modificato `tests/test_solver_registry.py`, non elencato nei Files del
piano, per aggiungere la chiave nuova — stessa mossa del Task 7;
(b) ⚠ ha **riscritto** `test_max_presence_giorni_morde` del piano perche' «non
mordeva contro la fixture, CP-SAT compatta di default», sostituendolo con uno
scenario che forza la capienza e asserisce `INFEASIBLE`. Un test riscritto
perche' non falliva e' il posto piu' probabile in cui si nasconde un test
vacuo, e `INFEASIBLE` e' un'asserzione debole (la soddisfa anche un modello
rotto in tutt'altro modo). Portato alla review come punto di attenzione
esplicito.
Review dispiegata su 7e88822..04c793f.

Task 8: review — **nessuna Important, tre Minor**. Il revisore ha verificato per
mutazione lo `span` (a mezza giornata cadono 2 test mirati in 10/10 esecuzioni
piu' `test_famiglia[max_presence-5]`), ha dimostrato che il `continue` del piano
rompe davvero l'oracolo differenziale (`minutes` da 180 a 240 -> chiave diversa
-> finding nuovo; col clamp `PRIMA == DOPO`), e ha confermato che l'INFEASIBLE
del ramo `days` e' per la ragione giusta (senza la riga OPTIMAL, con tetto 3
OPTIMAL e pulito, col ramo disabilitato il test cade 5/5). Guardia di vacuita'
del derivatore misurata in **entrambe** le direzioni: 2 zeri su 40 seed, e
potere reale 2/5 seed contro 1/5 di max_hours e max_half_days. Suite stabile su
quattro esecuzioni.

Ruling 26: le Minor 1 e 2 si chiudono **subito**, non si rimandano. — Motivo:
la Minor 1 e' una docstring che **afferma il falso** (che le fasce 3 e 4 a
cavallo del pranzo siano vietate; non lo sono, e il checker e' d'accordo), ed e'
esattamente la forma di difetto che il Task 7 ha gia' pagato con un giro di
correzione — su questo piano un commento falso e' costato piu' di un bug. La
Minor 2 e' codice **portante e scoperto** (il clamp ADR-018 del ramo `days`:
mutandolo, la suite intera resta verde), e la Ruling 20 ha gia' dichiarato che
la copertura ADR-018 di questo piano vale quanto l'immaginazione di chi scrive i
test a mano — lasciarne uno scoperto quando la sonda e' gia' verificata sarebbe
sprecare l'unica rete che abbiamo. La Minor 3 non si "corregge": il test resta,
ma la docstring ora dichiara che documenta invece di verificare. — Costo se
sbagliato: un commit di soli test in piu' nella storia del branch.

Task 8: **complete** (commit 04c793f + 6a6d9b0, pushati). Suite 282 passed,
2 skipped. Entrambi i test nuovi verificati RED contro la mutazione
corrispondente; il builder non e' stato toccato dal commit delle Minor.

Ruling 27 (pre-dispatch del Task 9): **il piano rende `MaxSiteChangesBuilder`
piu' LARGO del checker, non piu' stretto — e dichiara l'opposto.** Il piano
apre il Task 9 con «Il conservativo numero due»: i checker guardano le coppie
consecutive, il builder tutte le coppie, quindi «piu' stretto, mai piu' largo».
Per `SiteTransitionBuilder` e' vero. Per `MaxSiteChangesBuilder` **e' falso**, e
la ragione sta in cosa significa «consecutive».

`_site_sequence` (`domain/analysis/checkers/time_constraints.py:153`) scorre le
fasce occupate e appende **solo** le attivita' con sede nota (`if site is not
None`). Quindi «consecutive» vuol dire consecutive nella **sottosequenza delle
occupazioni con sede**, non «senza niente in mezzo»: un'attivita' **senza sede**
interposta non spezza l'adiacenza.

Il `_coppie_di_sede` del piano invece pretende `occupied(m).Not()` per ogni `m`
fra `s` e `t` — cioe' **tutto vuoto in mezzo**. Con Centrale alla fascia 0, una
attivita' senza sede alla fascia 1 e Succursale alla fascia 2: il checker vede
`[Centrale, Succursale]` e conta **un cambio**; il builder non trova la coppia
(la fascia 1 non e' vuota), non forza `c`, e **non conta niente**. Under-count
-> il solver accetta un orario che il checker boccia -> finding `HARD` **nuovo**
-> criterio di riuscita rotto.

Non e' teorico su questo banco: `_make_activities` del Task 9 da' una sede a
**meta'** delle attivita', quindi le attivita' senza sede interposte ci sono per
costruzione.

Correzione richiesta: la condizione «in mezzo» dev'essere **«nessuna occupazione
con sede in mezzo»**, non «nessuna occupazione». Con quella, la coppia `(s, t)`
con `sa != sb` diventa **esattamente** l'adiacenza nella sottosequenza del
checker. — Costo se sbagliato: un vincolo che conta qualche cambio di troppo,
cioe' piu' stretto — la direzione che il piano credeva di avere gia'.

Ruling 28 (pre-dispatch del Task 9): **ADR-018 e' interamente assente da
`MaxSiteChangesBuilder`** — la quarta volta su questo piano. `sum(cambi) <=
per_giorno` e `sum(tutti) <= per_settimana` sono postati sul parametro grezzo:
se le sole congelate producono gia' piu' cambi del tetto, il modello e'
INFEASIBLE per colpa del passato. I `cambi` sono variabili derivate, non termini
separabili, quindi vale lo stesso schema di `MaxGapBuilder` e
`MaxPresenceBuilder`: un `_frozen_site_changes` che calcola i cambi indotti
dalle sole congelate a build time, e un clamp `max(tetto, cambi_congelati)`.
⚠ `SiteTransitionBuilder` invece ADR-018 ce l'ha gia', nella forma della regola
dell'implicazione (`if not any(aid in ctx.free ...)`): quello non va toccato.
— Costo se sbagliato: nessuno; nel caso pulito il clamp coincide col tetto.

Ruling 29 (pre-dispatch del Task 9): valgono anche qui la Ruling 16 (niente
`test_sedi_sul_banco`: `test_famiglia` lo copre gia') e la Ruling 24 (i due
derivatori del piano non hanno `return` ne' guardia di vacuita'). ⚠ Per
`_derive_site_transition` la vacuita' e' netta e va dichiarata: quando `minimo`
resta `None` il derivatore scrive `site_transition_slots = 0`, e con `needed = 0`
il builder esce subito (`if not needed: return`) — famiglia completamente vacua,
quindi `return 0`.

Ruling 30 (pre-dispatch del Task 9): il Task 9 e' **il piu' rischioso del
piano** perche' cambia la forma della scuola testimone sotto sette derivatori
gia' scritti (Ruling 2). In piu' l'`rng.random() < 0.5` di `_make_activities`
**consuma numeri casuali**, quindi sposta l'intero flusso: ogni derivatore
esistente vedra' un testimone diverso a parita' di seed, e l'insieme dei
`pytest.skip` per vacuita' cambiera'. Non e' un difetto — e' atteso — ma il
brief deve dirlo, o l'implementatore lo scambiera' per una regressione. Cio' che
**non** deve cambiare e' il verde della suite. — Costo se sbagliato: qualche
minuto perso a inseguire uno skip che si e' spostato.

Task 9: implementato (commit 4035980). Le quattro correzioni del brief risultano
applicate. ⚠ Il difetto della Ruling 27 e' stato **riprodotto prima di essere
corretto**, come richiesto: con la formulazione del piano il solver rispondeva
OPTIMAL su sede A / senza sede / sede B con `per_day=0`, e `check_schedule`
bocciava con un `max_site_changes` che il solver non aveva mai visto — il
criterio di riuscita rotto, dimostrato invece che argomentato. Due scoperte
collaterali riportate dall'implementatore e da portare alla review:
(a) il caso «due sedi diverse sulla stessa fascia» e' **raggiungibile** con
`simultaneous_capacity > 1`, documentato ma non risolto (come da istruzioni);
(b) la guardia `any_free` di `SiteTransitionBuilder` e' piu' grossolana di
quanto dichiari — verifica la raggiungibilita' del dominio, non chi causa
davvero il conflitto — e puo' scattare su conflitti fra sole congelate.

Ruling 31: **il flusso casuale delle sedi va separato da quello principale, e
non e' una rifinitura.** L'implementatore ha assegnato le sedi con
`rng.random()` dentro il ciclo di `_make_activities`, cioe' pescando dal flusso
condiviso: ogni estrazione successiva si sposta, `_try_place` compreso, e a
parita' di seed **tutti** gli undici derivatori preesistenti vedono un testimone
diverso. La Ruling 30 lo aveva previsto e dichiarato «atteso, non una
regressione» — **era una lettura sbagliata**, ed e' la quarta volta su questo
piano che una mia Ruling dichiara innocuo qualcosa che non lo e'. Non e' un
difetto di correttezza (il testimone resta valido) ma di **potere**: cinque
coppie famiglia/seed che prima vincolavano sono diventate vacue. Misurato:
flusso condiviso `283 passed, 16 skipped`, flusso separato
(`random.Random(f"sedi-{seed}")`) `290 passed, 9 skipped`, con le famiglie
preesistenti riportate **esattamente** al loro insieme di skip di prima del
Task 9. Corretto dal controller nel commit 31ff9de. — Costo se sbagliato:
nullo; il testimone e' valido con entrambi i flussi, cambia solo quanto vincola.

Ruling 32: **`structural:site_transition` e' vacuo 4 volte su 5, e non si
chiude qui.** Il derivatore prende il **minimo** della distanza su tutte le
coppie di sedi diverse che condividono una risorsa; un minimo su molte
estrazioni casuali e' quasi sempre zero, e con `site_transition_slots = 0` il
builder esce subito. E' una debolezza della **formula del piano**, non del
flusso casuale (il flusso separato l'ha migliorata solo da 5/5 a 4/5). Un
builder strutturale nuovo con copertura di banco quasi nulla e' una lacuna
vera. — Decisione: portarla alla review del Task 9 come punto esplicito, e
farla decidere li' sulla base di una misura, invece di dettare io una formula
alternativa a colpo d'occhio — e' esattamente il modo in cui su questo piano ho
gia' sbagliato tre volte. — Costo se sbagliato: la famiglia resta coperta dai
soli test mirati, cioe' dalla stessa lacuna strutturale gia' dichiarata dalla
Ruling 20.

Task 9: review — **due Important**, piu' la raccomandazione misurata sulla
vacuita'. Le quattro correzioni del brief sono applicate e corrette: il difetto
della Ruling 27 riprodotto (formulazione del piano -> OPTIMAL + finding HARD
nuovo; corretta -> INFEASIBLE), entrambe le prove RED di ADR-018 riprodotte, e
il test che distingue clamp da salto morde davvero. Il commit 31ff9de del
controller e' confermato dall'aritmetica: 284 -> 299 test, delta esattamente i
15 nuovi, nessun test preesistente ha cambiato stato. Oltre al richiesto, il
revisore ha fatto il confronto **esaustivo** checker/builder su tutte le
configurazioni di una giornata: a capienza 1 la traduzione non e' conservativa,
e' **esatta** — zero scarto in entrambe le direzioni, per entrambi i builder.
Meglio di quanto il piano prometteva.

Ruling 33: **la scoperta (a) e' reale, piu' grave di come l'aveva riportata
l'implementatore, e si chiude solo a meta'.** Sotto capienza cumulativa (aula
con `Qta' > 1`, feature EDT documentata) due attivita' di sedi diverse possono
occupare la **stessa** fascia della stessa chiave: per il checker e' un cambio,
per la costruzione a coppie `s < t` non esiste. Rompe l'oracolo davvero (solver
OPTIMAL, checker HARD nuovo, zero finding di occupazione), e il buco e' anche in
`SiteTransitionBuilder`, che il rapporto dava per sano. Decisione, in due parti:
(1) per `site_transition` **si ripara subito** — basta una clausola `s == t`,
esatta e a costo trascurabile;
(2) per `max_site_changes` **non si ripara nel builder**, e nemmeno adesso.
`state.occupancy` e' una `list` e `_site_sequence` la scorre in ordine, quindi
sotto capienza cumulativa il conteggio dei cambi dipende dall'**ordine di
inserimento** — un artefatto del checker, non una semantica. Tradurre un
artefatto sarebbe peggio che lasciare lo scarto. Va prima deciso in
`domain/analysis` cosa significhi «cambio di sede» quando due sedi coesistono
nella stessa fascia; finche' non lo e', il builder lo dichiara nel docstring.
— Aggiunto all'elenco «Ancora aperto» del progetto. — Costo se sbagliato: lo
scarto resta su istanze con `simultaneous_capacity > 1`, che nel Fermi non
esistono (le aule non sono mai state inserite).

Ruling 34: **si adotta la raccomandazione misurata del revisore sui due
derivatori: costruire lo scenario invece di subirlo.** Il revisore ha misurato
il **potere vincolante reale** (builder reso no-op -> il caso deve fallire), che
e' la domanda giusta: la vacuita' da sola non basta, un caso non vacuo puo'
comunque non mordere. In albero: `structural:site_transition` morde **1/15**,
`T.MAX_SITE_CHANGES` **0/15** — cioe' la famiglia dei cambi di sede non testava
**niente**. Con le formulazioni proposte: **12/15** entrambe (`denso` = sede a
tutte le attivita' piu' riparazione a `needed=1`; `segregato` = sedi assegnate
per giornata, da cui `per_day = per_week = 0`). Due delle tre alternative che
avevo elencato nel brief sono **dimostrabilmente chiuse**: derivare su una
coppia sola non si puo' perche' `site_transition_slots` e' un'impostazione
d'istituto, globale — il `needed` derivabile *e'* il minimo; e ridurre la
densita' peggiora, perche' meno coppie significa piu' spesso zero coppie. Costo
0,05-0,41 s per seed, e non tocca `_make_activities`, quindi nessun altro
derivatore vede un testimone diverso. — Costo se sbagliato: il banco esercita
uno scenario piu' artificiale del testimone casuale; ma un testimone che non
morde mai non e' meno artificiale, e' solo inutile.

Ruling 35: **Important 2 del revisore va corretta: `_derive_site_transition`
ignora `duration_slots`.** Misura la distanza fra fasce d'**inizio**, il checker
fra fasce **occupate**: deriva un `needed` che il testimone stesso viola.
`run_family("structural:site_transition", 15)` fallisce col codice in albero,
senza alcuna mutazione — latente sui seed 1-5, scatta appena si allarga il
range, cosa che l'implementatore stesso ha fatto per misurare. ⚠
`_derive_max_site_changes` non ne soffre, ed e' istruttivo perche': il
**conteggio** dei cambi e' invariante alle ripetizioni di sede, la **distanza**
no. — Costo se sbagliato: nullo, e' un difetto dimostrato con un test che
fallisce.

Ruling 36: la scoperta (b) — la guardia `any_free` di `SiteTransitionBuilder`
piu' grossolana di quanto dichiari — resta **Minor e non si chiude qui**. Il
revisore ha portato la contro-sonda decisiva: `structural:occupation`, builder
**preesistente** e mai contestato, si comporta in modo identico. Non e' una
regressione del Task 9 ma la domanda gia' aperta in CLAUDE.md sul trattamento
delle congelate in violazione. — Costo se sbagliato: nullo finche' nessuno
congela attivita' gia' in conflitto di sede.

Task 9: fix round 1/5 (commit 43c37ad, pushato). Suite da 290 passed / 9 skipped
a **297 passed / 3 skipped** — gli skip residui sono `arrival_departure` 2 e 4
(preesistenti, invariati dal Task 5) piu' `structural:site_transition` seed 3.
Le quattro cose del giro risultano fatte: `_distanza_sedi` sulle fasce occupate
(Ruling 35), clausola `s == t` sul solo `SiteTransitionBuilder` con
`MaxSiteChangesBuilder` dichiaratamente non toccato (Ruling 33), derivatori
riscritti da osservativi a **costruttivi** (Ruling 34), filtro `_sedi_raggiungibili`.
Due cose dichiarate onestamente dall'implementatore e portate alla ri-review:
(a) il potere vincolante di `max_site_changes` si ferma a **10/15** contro i
12/15 misurati dalla review, con un'ipotesi sul perche' — non ha spacciato per
raggiunto un numero che non aveva;
(b) il filtro delle clausole ha effetto **nullo** sul Fermi (constraint identici
con e senza, a 2 e a 4 sedi), tenuto perche' innocuo. Un filtro che non filtra o
e' inutile o non filtra cio' che crede: da stabilire in ri-review.
Ri-review mirata dispiegata su 31ff9de..43c37ad.

Ruling 37: il metodo «potere vincolante» della Ruling 34 e' **esso stesso
rumoroso**, e va misurato piu' volte prima di concludere. Il mutante (builder
reso no-op) viene risolto da un solver non deterministico, quindi lo stesso seed
puo' fallire o no fra un'esecuzione e l'altra — l'implementatore ha visto
`site_transition` oscillare fra 12/15 e 14/15 su sei esecuzioni. Non invalida la
misura (1/15 -> 12/15 e' un salto ben oltre l'oscillazione), ma **il divario
10-contro-12 su `max_site_changes` non e' concludente da una sola esecuzione**,
ed e' esattamente il tipo di numero che si e' tentati di leggere come una
differenza reale. — Costo se sbagliato: si insegue un divario che era rumore,
oppure si archivia come rumore un derivatore piu' debole del necessario.

Task 9: ri-review giro 1 — **una Important, tre Minor**, nessun giro 2 pieno.
Chiuse: `_distanza_sedi` (riprodotta su 30 seed: col codice pre-correzione
falliscono il **15 e il 20** — il 20 la review non l'aveva visto — e col codice
in albero 57 passed su 30 seed x 2 famiglie); la clausola `s == t`, con
l'argomento dell'implementatore **verificato vero** leggendo il checker
(`gap_slots = -1 < needed` per ogni `needed >= 0`, quindi postarla anche a
`needed = 0` e' esatto, non piu' stretto); e la nota del docstring su
`MaxSiteChangesBuilder`, **dimostrata** invertendo l'ordine di creazione di due
attivita' compresenti — `changes=2` con finding HARD contro `changes=1` senza.

Ruling 38: **il divario 10-contro-12 non era rumore, e sotto c'era un difetto
vero.** Il revisore ha rimisurato con varianza zero su sei esecuzioni (10/15
esatto), quindi la Ruling 37 e' stata applicata e ha dato la risposta opposta a
quella comoda: non rumore. La causa: `_derive_max_site_changes` alternava le
sedi su `day % len(sites)`, la **parita' del numero di giorno**, quindi un
docente che lavora solo in giorni di pari parita' riceveva **una sola sede** e
`per_day = per_week = 0` diventava inviolabile — un verde che non puo' fallire.
Era il seed 1, dentro il banco (`giorni {0: 3, 2: 2}`, entrambi al sito 0).
**Quarta occorrenza dello stesso pattern** (Ruling 16, 24, 31): un caso di
banco che sembra coprire e non copre. Corretto dal controller in 81cb620
alternando sui giorni **realmente usati**, con la seconda condizione di vacuita'
aggiunta alla docstring (ne dichiarava una sola, definendola l'unica possibile).
Potere rimisurato: **11-12/15** su cinque esecuzioni. ⚠ Il seed 1 continua a
passare, ma per un'altra ragione — con due sedi il vincolo e' violabile e il
solver semplicemente non lo viola. E' la differenza fra un difetto e il limite
del metodo, e va detta: il banco a testimone non puo' costringere il mutante a
sbagliare. — Costo se sbagliato: nullo, la correzione e' misurata.

Ruling 39: **«effetto nullo» del filtro era una misura giusta generalizzata
troppo.** Il revisore ha strumentato: **8277 chiamate su 18308 filtrano
davvero**. I numeri del rapporto (5604 / 21830) si riproducono esattamente, ma
valgono per il solo scenario **saturo**; con le sedi correlate alle classi — il
caso reale dei plessi — il filtro taglia **-26%** a 2 sedi e **-37%** a 4, e sul
banco fino al **-63%**. Non e' codice morto. — Decisione: il filtro resta, e la
sua docstring va corretta perche' oggi dichiara un'inefficacia che non ha.
Annotato come Minor da chiudere al Task 17, insieme alla Minor 3 (il filtro non
e' applicato alle fasce **intermedie** di `_coppie_di_sede`, dove sta il grosso
delle variabili sprecate a molte sedi). — Costo se sbagliato: una docstring che
sconsiglia un'ottimizzazione utile.

Task 9: **complete** (commit 4035980, 31ff9de, 463f418, 43c37ad, 81cb620 —
tutti pushati). Suite 297 passed, 3 skipped.

## Task 10 — rulings pre-dispatch

Ruling 40: **`SameDayBuilder` viola ADR-018 gia' oggi, e il piano del Task 10
conserva il difetto invece di correggerlo.** Misurato con due sonde
(`tests/test_probe_tmp.py`, rimossa): (a) due congelate della **stessa**
materia nello stesso giorno piu' una libera altrove -> `INFEASIBLE`; (b) A != B
entrambe congelate nello stesso giorno piu' una libera -> `INFEASIBLE`. In
entrambi i casi ADR-018 dice il contrario: «Il solver non e' mai INFEASIBLE per
colpa di una violazione preesistente: al piu' non puo' aggiungere nulla li'».
La guardia esistente `any(aid in ctx.free for aid, _ in a)` **non e'** un
trattamento ADR-018: dice «c'e' qualcosa da decidere», non «di quanto il passato
ha gia' consumato il tetto» — sono due domande diverse, e la prima non implica
la seconda. Il piano la sposta perfino dal livello **secchio** al livello
**riga** (`coinvolte` in `SubjectBuilder.build`), quindi allarga il difetto: una
riga con una sola libera qualsiasi fa postare il vincolo su **tutti** i secchi,
compresi quelli abitati solo da congelate. — Decisione: il Task 10 riscrive
questo builder, quindi e' il momento di correggerlo; il brief porta la regola
esatta (Ruling 41) e un test per ramo. — Costo se sbagliato: il solver si
rifiuta di lavorare su un orario che l'utente ha sporcato a mano, cioe' il caso
d'uso che ADR-018 esiste per servire.

Ruling 41: **la regola esatta, derivata leggendo il checker, non il piano.**
Per **A = B** il caso e' separabile e `residual_cap` e' esatto: tetto 1, ogni
congelata nel secchio ne consuma uno, `cap = max(0, 1 - congelate)`, vincolo
sui soli letterali liberi. Il checker emette `count=len(la)` fra le
`quantities`, quindi anche una sola aggiunta libera a un secchio gia' violato e'
un finding **nuovo** per `Finding.key`: `cap = 0` e' il valore giusto, non un
eccesso di zelo.
Per **A != B** (e per `TWO_DAYS`, che ha la stessa forma su due secchi
consecutivi) il residuo **non** e' separabile — sono indicatori derivati — e la
regola meccanica `max(0, 1 - fa - fb)` sarebbe **troppo stretta**. Il checker
emette il finding solo `if la and lb`: piu' A in un secchio dove B e' assente
non crea e non peggiora nulla. Quattro rami, con `fa`/`fb` = «una congelata di
A/B abita il secchio», noti a build time:
  - `fa=0, fb=0` -> `ha + hb <= 1` (gli indicatori pieni **coincidono** con
    quelli sulle sole libere, perche' nessuna congelata contribuisce);
  - `fa=1, fb=0` -> `hb == 0` (e le libere di A restano **libere**: senza B non
    c'e' finding);
  - `fa=0, fb=1` -> `ha == 0`;
  - `fa=1, fb=1` -> il secchio e' **gia' violato**, e ogni aggiunta libera
    ingrossa la tupla `activities` che sta dentro `Finding.key`: si azzerano i
    letterali **liberi** di A e di B in quel secchio, uno per uno.
⚠ Il quarto ramo puo' rendere il modello infattibile se una libera non ha altro
posto dove andare — ed e' **voluto**: e' la stessa proprieta' di
`residual_cap` clampato a zero, ed e' testualmente cio' che ADR-018 concede
(«al piu' non puo' aggiungere nulla li'»). Da non rilitigare in review. —
Costo se sbagliato: l'oracolo differenziale del Task 17 fallisce su input
sporco, cioe' esattamente dove ADR-018 e' stato scritto per reggere.

Ruling 42: **i due derivatori del piano sarebbero saltati sempre, e comunque
vacui.** Entrambi terminano con un `return` nudo dentro il ciclo e nessun
`return` finale: restituiscono `None`, e `run_family` fa `if not potere:
pytest.skip(...)`. Le due famiglie nuove sarebbero quindi **skip permanenti** —
dieci test verdi in apparenza, zero copertura reale. E anche col valore di
ritorno corretto restano vacui: `_derive_same_half_day` non impone **almeno due
occorrenze** (sotto due il vincolo e' soddisfatto per costruzione e non
violabile — e' la terza forma di vacuita' gia' scovata in review per
`_derive_same_day`, che infatti la guarda con `sum(...) < 2`), e
`_derive_two_days` non impone che **entrambe** le materie compaiano davvero
sulla classe: con `defaultdict(set)`, una materia assente da' `giorni` vuoto,
`not any(...)` e' banalmente vero, e nasce una riga che nessun piazzamento puo'
violare. **Quinta occorrenza del pattern** (Ruling 16, 24, 31, 38). —
Decisione: i due derivatori si scrivono sulla forma di `_derive_same_day`
(scorrere tutte le coppie, accumulare, `return creata`), con la vacuita'
dichiarata nella docstring e **verificata nelle due direzioni** — il potere
vincolante va misurato spegnendo il builder. — Costo se sbagliato: due famiglie
di banco che sembrano coprire due vincoli nuovi e non coprono nulla.

## Task 10 — rulings post-review (giro 1)

Ruling 43: **il metodo del potere vincolante da' qui una risposta diversa dal
Task 9, e va misurato caso per caso.** Sei esecuzioni x cinque seed per
famiglia: `SAME_DAY` (esistente, collaudata) **20/30**, `SAME_HALF_DAY`
**8/30**, `TWO_DAYS` **30/30**. Il seed 1 oscilla **2/6 per entrambe** le
famiglie di secchio: il non determinismo di CP-SAT e' quindi **reale**, al
contrario del Task 9 dove la varianza era zero e il "rumore" era un difetto. Ma
i seed 2, 3 e 4 sono **0/6 deterministici**, e li' il rumore non spiega niente.
— Decisione: la Ruling 37 non si chiude una volta per tutte. La domanda
«varianza o segnale?» si risponde solo separando i seed **deterministicamente
0** dagli oscillanti, e sui primi si passa alla sonda di violabilita'
strutturale (esiste *una* soluzione che violi la riga?), che e' una misura
esatta e non statistica. — Costo se sbagliato: si archivia come rumore un
derivatore vacuo, che e' esattamente il fallimento del Task 9.

Ruling 44: **il calibro del banco, scritto una volta per tutte.** `SAME_DAY` e'
in produzione da cinque task, ha guardie di vacuita' gia' corrette in review, e
arriva a **20/30**. Quindi **5/5 non e' la norma e non e' l'obiettivo**: il
banco a testimone misura quanto spesso il builder e' *necessario* perche' il
solver non sbagli, non se il derivatore e' vacuo. Le due domande sono diverse e
richiedono strumenti diversi — la seconda si risponde con la sonda di
violabilita', non contando i verdi. — Decisione: un potere basso non e' di per
se' un difetto; e' un **innesco d'indagine**. Da non trasformare in una soglia
numerica da inseguire. — Costo se sbagliato: si riscrivono derivatori sani per
inseguire un numero, o si archiviano derivatori malati perche' il numero
sembrava normale.

Ruling 45: **sesta occorrenza del pattern, e stavolta la vacuita' viene dalla
geometria, non dal conteggio.** Al seed 2 `_derive_same_half_day` crea una riga
**matematicamente impossibile da violare**: la mezza giornata e' larga 2 fasce,
e fra le attivita' della coppia (classe, materia) ce n'e' una di durata 2 con
`respects_breaks`, che riempie da sola l'intera mezza giornata — la seconda non
puo' mai raggiungerla, `len(la) > 1` e' irraggiungibile e `SameHalfDayChecker`
non emette nulla. Il derivatore restituisce comunque `1`, quindi `run_family`
non salta e il caso e' un verde che non puo' fallire. Le due condizioni di
vacuita' dichiarate nella docstring («sotto due occorrenze totali», «nessuna
coppia qualifica») non coprono questa: e' la terza forma, e nasce dalla
**larghezza del secchio contro le durate**, dimensione che nessun derivatore
aveva ancora dovuto guardare. — Decisione: terza guardia — le due attivita' piu'
corte della coppia devono starci in **qualche** mezza giornata
(`min + seconda_minima <= max(morning_end_slot, slots_per_day -
morning_end_slot)`). E' una condizione **necessaria**, non esatta (non modella
l'allineamento agli intervalli), quindi la correzione va **verificata**: il seed
2 deve passare a skip. La stessa guardia va aggiunta a `_derive_same_day`, dove
la vacuita' e' latente ma oggi non morde (5/5 righe violabili) — due righe
adesso contro una regressione silenziosa dopo. — Costo se sbagliato: una
famiglia nuova che sembra coprire e non copre, per la sesta volta.

Ruling 46: **il gate di riga non e' piu' portante, e la docstring non deve
suggerire il contrario.** Rimosso il gate di `SubjectBuilder.build`, la suite
resta **interamente verde**: `test_il_vincolo_non_si_posta_se_nulla_e_libero`
ora passa per il `if not free: return` di `_post_separable`, non per il gate.
Il gate e' semanticamente neutro (con tutto congelato ogni ramo e' gia' un
no-op, verificato ramo per ramo) e resta come ottimizzazione. — Decisione:
si tiene, ma la docstring dice **cos'e'** — un'ottimizzazione, non l'invariante
che difende ADR-018 — perche' su questo branch le proprieta' dichiarate e non
vere sono il difetto ricorrente, e questa lo diventerebbe. — Costo se
sbagliato: il prossimo che tocca il gate crede di poterlo rimuovere senza
conseguenze, o crede che protegga qualcosa che non protegge.

Ruling 47: **l'oracolo differenziale non vede nessuna delle famiglie dei Task
6-10.** `CODICI` in `tests/test_solver_oracle.py` non e' mai stato esteso: la
copertura di tutti i vincoli tradotti dopo lo spike passa **solo** dal
`_hard(schedule, d.codes)` di `run_family`, che confronta con l'insieme vuoto e
non e' differenziale. Nessuno dei Task 7, 8, 9 l'ha esteso, quindi non e' un
difetto del Task 10. — Decisione: rimane al **Task 17**, insieme alla Ruling 22
(le `quantities` dentro `Finding.key` rendono «peggiorato» e «migliorato»
entrambi finding *nuovi*), che diventa reale proprio quando `CODICI` si allarga.
Annotato qui perche' e' cresciuto di cinque famiglie da quando fu aperto. —
Costo se sbagliato: si arriva al Task 17 credendo che l'oracolo abbia gia'
sorvegliato dieci vincoli, quando ne sorveglia cinque.

## Task 10 — rulings post-ri-review (giro 2)

Ruling 48: **settima occorrenza, e stavolta la proprieta' falsa e' nella
*correzione* del giro 1.** La terza guardia di vacuita' si dichiara «condizione
**necessaria**, non esatta». Non lo e'. Il secchio si attribuisce alla fascia di
**partenza** — lo dice il docstring di `subject_buckets.py` stesso — quindi
un'attivita' puo' *partire* nell'ultima fascia della mattina e *sconfinare* nel
pomeriggio restando attribuita alla mattina: la somma delle due durate non e'
limitata dalla larghezza della mezza giornata. Controesempio eseguito con
`check_schedule` (S=4, m=2, intervallo a 1; corta alla fascia 0, lunga da 2 alla
fascia 1): finding `subject_same_half_day` **unico HARD**, riga violabile, e la
guardia la butta via. Costo oggi zero (sui seed 1-5 nessuna riga violabile viene
esclusa), costo su 250 seed: **22 righe escluse, di cui 13 violabili**. Stesso
profilo della Ruling 35: latente sui cinque seed, scatta appena qualcuno allarga
il range. — Decisione: formula corretta, con `m = morning_end_slot`,
`S = slots_per_day` e le due durate piu' corte `d1 <= d2`:
`(d1 <= m - 1 and d1 + d2 <= S) or (d1 + d2 <= S - m)` — sconfinamento dalla
mattina, oppure entrambe dentro il pomeriggio. Sul secchio **giornata** la
formula in albero (`somma <= slots_per_day`) **e' gia' corretta** e non si
tocca: entrambe le attivita' partono e finiscono dentro la stessa giornata.
Verificato che `_derive_same_day` ha comportamento **identico** prima e dopo su
250 seed — la guardia "day" non esclude mai nulla, quindi il derivatore
collaudato non e' a rischio. ⚠ **Anche la Ruling 45 va corretta**: il seed 2 e'
davvero inviolabile (enumerazione esaustiva), ma **non** perche' «la durata 2
riempie da sola la mezza giornata» — potrebbe partire alla fascia 1 e stare in
mattina con una durata 1 alla fascia 0. A bloccarla e' l'**intervallo** a 2
combinato con `respects_breaks`. La guardia da' il verdetto giusto al seed 2 per
**coincidenza**. — Costo se sbagliato: copertura persa in silenzio, cioe' lo
stesso difetto che la guardia esisteva per correggere, al contrario.

Ruling 49: **quarta forma di vacuita': le maschere di settimana disgiunte.**
`_derive_same_day` e `_derive_same_half_day` contano le occorrenze **senza
filtrare per firma**. Due attivita' con maschere `(0,)` e `(1,2)` non compaiono
mai nello stesso `ScheduleState`, quindi `len(la) > 1` e' irraggiungibile e la
riga e' inviolabile pur superando tutte e tre le guardie. Misurato: **assente
sui seed 1-5**, presente dal seed 8 (e poi 14, 25, 28, 29, 32, 37, 43, 51, 57,
58, 59, 65, 69, 78, 85, 94 su cento). E' **preesistente** in `_derive_same_day`
dal Task 5, ma il derivatore nuovo l'ha ereditata e le docstring elencano le
forme di vacuita' come se fossero tutte. — Decisione: si corregge adesso, nello
stesso giro, perche' e' esattamente la specie di difetto che questo branch
produce — un'enumerazione dichiarata completa e non completa. La condizione
diventa: esiste **una firma** in cui almeno due attivita' della coppia sono
co-attive (il vincolo di validita' del testimone resta sull'**unione**, che e'
piu' forte e quindi sicuro). Da verificare che i seed 1-5 non cambino
comportamento — e' la lezione del Task 9. — Costo se sbagliato: righe verdi che
non possono fallire, per la quarta forma.

Ruling 50: **i numeri misurati dentro le docstring vanno rimisurati nello
stesso giro che cambia cio' che misurano, o tolti.** Il giro 1 ha scritto in
docstring `8/30` e `20/30` (potere vincolante) e `-16,1%` (constraint
risparmiati); la ri-review ha rimisurato `-16,7%`, e ha notato che togliere il
seed 2 dalla famiglia **cambia il denominatore** di `8/30` senza che nessuno
l'abbia ricontato. Un numero in docstring non e' un commento: e' una misura
datata, e invecchia in silenzio. Ha anche un secondo difetto scoperto qui: il
guadagno della guardia `if not la or not lb` e' sul banco **tutto** di
`TWO_DAYS` — le righe A = B passano da `_post_separable`, che la guardia non
attraversa — e la docstring non lo diceva. — Decisione: chi cambia il codice
rimisura, oppure sostituisce il numero con la proprieta' qualitativa. — Costo
se sbagliato: la documentazione del repo diventa una raccolta di misure di
versioni che non esistono piu'.

## Task 10 — giro 2, applicato dal controller

Ruling 51: **la formula chiusa e' stata provata due volte e scartata due
volte; la guardia giusta e' un'enumerazione.** Prima versione (giro 1): «somma
delle due durate piu' corte <= larghezza del secchio» — **non necessaria**, e
escludeva righe violabili (Ruling 48). Seconda versione (dettata dalla
ri-review): corretta per lo sconfinamento, quindi necessaria, ma **troppo
generosa** — non modella l'intervallo, e riammetteva il seed 2, dove la riga e'
inviolabile per via di un `Break` con `respects_breaks`. Verificato eseguendo:
con la sola formula corretta la suite tornava a **316 passed, 3 skipped**, cioe'
il seed 2 ridiventava un verde che non puo' fallire. — Decisione: `_ci_stanno`
enumera le coppie di fasce di partenza (al piu' 36 combinazioni) applicando le
stesse regole di `_try_place` — dentro la giornata, niente scavalcamento
dell'intervallo per chi lo rispetta, niente sovrapposizione. E' **necessaria per
costruzione**, non per misura: se le due attivita' non coesistono nemmeno da
sole, a maggior ragione non coesistono col resto dell'orario addosso. Resta non
sufficiente (ignora le altre attivita', le indisponibilita', i festivi), ed e'
la direzione giusta in cui sbagliare. — Costo se sbagliato: la terza volta sullo
stesso punto.

Ruling 52: **e la guardia corretta scopre che anche `_derive_same_day` creava
righe inviolabili, dal Task 5.** Misurato su 120 seed: sul secchio **giornata**
l'enumerazione esclude **76 righe su 258** (29%), tutte per allineamento
all'intervallo — piu' altre 24 per maschere di settimana disgiunte
(Ruling 49). La ri-review aveva concluso che «la guardia "day" non esclude mai
nulla su 250 seed»: era vero **della vecchia formula**, che non guardava gli
intervalli, non della condizione corretta. Sul secchio mezza giornata:
82 escluse dalla geometria e 26 dalle settimane su 375. — Verificato che il
potere vincolante di `SAME_DAY` non cambia: **18/30 e 20/30** su due
esecuzioni, contro 20/30 misurato prima del giro 2 — dentro la varianza gia'
nota (il seed 1 oscilla). E non **puo'** cambiare, per argomento e non per
misura: togliere una riga che nessun piazzamento puo' violare non toglie alcun
finding, perche' quella riga non ne produceva. — Decisione: si tiene, ed e' un
miglioramento di onesta' del banco: `creata` smette di contare righe che non
provano niente. — Costo se sbagliato: nullo sul verde, ma il numero di righe
create non e' piu' confrontabile con quello dei task precedenti.

Ruling 53: **i tre numeri in docstring del giro 1, rimossi o rimisurati**
(applicazione della Ruling 50). `8/30` e `20/30` (potere vincolante) tolti dalla
docstring di `_derive_same_half_day` e lasciati solo qui nel registro: dopo
questo giro sarebbero comunque sbagliati, perche' il seed 2 ora salta e il
denominatore e' cambiato (**7/30 e 9/30 su due esecuzioni, con 6 skip
onesti**). `-16,1%` sostituito dall'ordine di grandezza piu' la nota — mai
scritta prima — che sul banco il risparmio e' **tutto di TWO_DAYS**, perche' le
righe A = B passano da `_post_separable`, che la guardia non attraversa.
Corretta anche la frase «**non** un'ottimizzazione, e' esatta»: e'
un'ottimizzazione la cui *giustificazione* e' l'esattezza. — Costo se
sbagliato: cosmetico, ma e' la classe di difetto che questo branch produce.

Task 10: **complete** — 315 passed, 4 skipped. Skip: `arrival_departure` 2 e 4,
`structural:site_transition` 3 (preesistenti), `same_half_day_incompatible` 2
(nuovo, onesto).

## Task 11 — decisioni pre-dispatch

Ruling 54: **i tre derivatori del piano sono vacui tutti e tre sullo stesso
seed 2, e la vacuita' e' misurata prima del dispatch.** Sonde temporanee su 60
seed, poi rimosse. `_derive_max_hours_subject` come scritto nel piano produce
una riga **inviolabile** su **19/60** seed (secchio giornata) e **17/60**
(mezza giornata); `_derive_forbidden_sequence` su **10/60**. Il seed 2 e' fra i
vacui in tutti e tre i casi, e i seed del banco sono 1-5: senza correzione,
**tre dei quindici casi** del Task 11 sarebbero verdi incapaci di fallire. —
Decisione: le guardie sono obbligatorie nel brief, non un miglioramento
facoltativo. — Costo se sbagliato: la stessa patologia del branch, ottava
occorrenza, con la differenza che stavolta era misurabile prima di scriverla.

Ruling 55: **`param = max(per_secchio)` e' vacuo ogni volta che il testimone
concentra tutto in un secchio solo.** La condizione di violabilita' e' che
*esista* un piazzamento con un secchio sopra il tetto; se il totale della coppia
(classe, materia) **per firma di settimana** non supera `param`, nessun
piazzamento lo puo' superare — e con una sola attivita' questo e' automatico
(`param` = la sua stessa durata). Due forme distinte, entrambe osservate: seed 2
con `n=1`, seed 9 e 10 con `n=2/3` ma `totale == param`. — Decisione: la
guardia e' `totale_per_firma > param` **piu'** la condizione geometrica gia'
esistente (`_ci_stanno`: almeno due attivita' co-attive devono poter partire
nello stesso secchio — se nessuna coppia ci sta, il massimo raggiungibile e' la
durata piu' lunga, che `param` domina per costruzione). — Costo se sbagliato:
una famiglia intera di verdi che non provano nulla.

Ruling 56: **il `param` va calcolato per firma di settimana, non sull'unione.**
Il piano somma i minuti per secchio su tutti i piazzamenti, ignorando le
maschere; ma `_try_place` **permette** a due attivita' di settimane disgiunte di
condividere la cella, e il checker valuta uno `ScheduleState` per firma. Il
`param` dell'unione e' quindi >= di ogni somma per firma: il testimone lo
soddisfa (nessun falso rosso), ma il vincolo nasce piu' largo del necessario. —
Decisione: `param` = massimo, sulle firme, della somma massima per secchio
**dentro quella firma**. — Verificato: con questa correzione piu' la scansione
di tutte le coppie (classe, materia) invece del `return` alla prima, i seed
vacui passano da 19/60 e 17/60 a **0/60**, con 2-6 righe vincolanti per seed. —
Costo se sbagliato: potere vincolante regalato via, in silenzio.

Ruling 57: **la vacuita' di `FORBIDDEN_SEQUENCE` al seed 2 e' la forma piu'
cruda: `|A| = 0`.** La materia scelta come antecedente **non ha alcuna
attivita'** in quella classe, quindi `_placed_of` restituisce la lista vuota e
`ForbiddenSequenceChecker.violations` non entra mai nel ciclo. Il piano non
controlla la presenza: itera su `w.env["subjects"]` e prende la prima coppia
`(a, b)` mai adiacente nel testimone — e «mai adiacente» e' banalmente vero per
una materia assente. — Decisione: tre guardie, tutte necessarie — presenza di
**entrambe** le materie nella classe; **co-attivita'** in qualche firma; e
l'adiacenza dev'essere **geometricamente raggiungibile** (esiste `sa` ammessa
per un'attivita' di A tale che `sa + durata` sia ammessa per una di B, con le
stesse regole di `_collocazioni`). Piu' l'accumulo su tutte le coppie invece del
`return` alla prima. — Verificato: da 10/60 seed vacui a **0/60**, 5-9 righe per
seed. — Costo se sbagliato: come sopra.

Ruling 58: **`_MaxHoursSubject` duplica `buckets()` e perde l'assert su
`KIND`** — cioe' reintroduce esattamente la Minor 2 chiusa nel giro 1 del Task
10, in una classe nuova. `vocab.bucket_of` tratta **ogni** `kind != "day"` come
mezza giornata, quindi una sottoclasse che dimentichi `KIND` prende
silenziosamente la semantica sbagliata invece di rompersi. — Decisione:
estrarre `_Bucketed(SubjectBuilder)` con `KIND`, `buckets()` e l'assert, e farne
ereditare **sia** `_BucketIncompatible` (esistente) **sia** `_MaxHoursSubject`
(nuovo). Non due copie. — Costo se sbagliato: la stessa svista viaggia avanti di
task in task, un `KIND` per volta.

Ruling 59: **il `continue` di `ForbiddenSequenceBuilder` e' legittimo e non
viola le Rulings 14/23/28.** Quelle vietano il `continue` su un **tetto**, dove
saltare significa perdere il clamp a zero. Qui il vincolo e' una clausola fra
due letterali: se **entrambi** vengono da attivita' congelate non c'e' nulla da
decidere — e' `any_free`, «un fatto, non una decisione». Con **uno solo**
congelato la clausola resta e forza a zero il letterale libero, che e'
precisamente il comportamento voluto. — ⚠ Come il quarto ramo di `_post_cross`,
**puo' rendere il modello INFEASIBLE** se la libera non ha altro posto dove
andare: e' cio' che ADR-018 concede testualmente, e per il precedente del Task
10 (Minor 5) va **esibito da un test**, non solo dichiarato in docstring. —
Costo se sbagliato: una proprieta' dichiarata e non difesa, di nuovo.

Ruling 60: **la deduplicazione per `coinvolte` regge anche per queste tre
famiglie, e il motivo va scritto una volta sola.** `SubjectBuilder.build`
dedupla sull'unione delle attivita' di A e B per la firma; `post()` dipende
dalla firma solo attraverso `subject_literals`/`subject_activities`, che
filtrano sullo stesso insieme `active`. L'insieme A si ricava da `coinvolte` in
modo deterministico (la materia di un'attivita' e' fissa), quindi due firme con
lo stesso `coinvolte` producono gli stessi vincoli. ⚠ Per `MAX_HOURS` con
A != B il gate e `coinvolte` guardano **anche** B, che al vincolo non serve (il
checker somma solo A): l'effetto e' al piu' una riga postata due volte in modo
identico, mai una saltata. Non e' un difetto — ma va detto, perche' e' la stessa
domanda che al Task 6 aveva prodotto il difetto del D.T.B. — Costo se
sbagliato: si "ottimizza" il gate e si perde una firma.

Ruling 61: **Ruling 16, quarta applicazione.** Il piano prescrive
`test_sul_banco` con `@parametrize(seed, [1..5]) × @parametrize(tipo, [i tre
tipi])`: quindici casi che `test_solver_witness.py::test_famiglia` genera gia'
registrando i derivatori. Non si scrive, e in testa al modulo va la nota ⚠ nella
forma di `tests/test_solver_sites.py`. — Costo se sbagliato: quindici test
duplicati, ~4 s di suite.

Ruling 62: **i numeri attesi del piano sono stantii** (`291 passed`, `17
test`). La linea di base e' **315 passed, 4 skipped**, e ai quattro skip
esistenti se ne aggiungeranno solo quelli onesti che le guardie nuove
produrranno — che dalle sonde dovrebbero essere **zero** sui seed 1-5. — Costo
se sbagliato: si insegue un numero inventato invece di spiegare gli scostamenti.

## Task 11 — review, giro 1

Ruling 63: **la dimensione della Ruling 45 non era stata riportata sul tetto di
ore, e il seed 2 di `max_hours_half_day` e' un verde che non puo' fallire.** Le
due guardie della Ruling 55 sono entrambe **necessarie** (verificato dal
revisore riga per riga), ma sono verificate **indipendentemente** e nessuna
delle due guarda **quanto ci sta davvero in un secchio** — la larghezza del
secchio contro le durate, cioe' esattamente cio' che la Ruling 45 aveva gia'
dovuto scoprire per `SAME_HALF_DAY`. Misura del revisore con sonda esatta
(modello col `post` della famiglia spento piu' la clausola «esiste una firma e
un secchio con minuti > param»; `INFEASIBLE` = riga inviolabile): su 20 righe
create sui seed 1-5, **4 inviolabili**, e le **due** del seed 2 sono fra
queste — quindi `potere = 2`, `run_family` non salta, e il caso passa comunque.
Sul secchio giornata: 18 righe, **0 inviolabili**. — Decisione: guardia di
**riempimento per firma**, misurata dal revisore fuori dal codice: per ogni
firma, il massimo di minuti che possono *partire* nello stesso secchio senza
sovrapporsi (enumerazione sulle collocazioni, come `_ci_stanno`), e la riga si
crea solo se qualche firma supera `param`. Esclude **2 righe inviolabili su 4**,
**0 righe violabili su 16**, ed e' un **no-op completo** sul secchio giornata —
lo stesso profilo della guardia della Ruling 48. — Costo se sbagliato: la
quarta occorrenza della stessa forma, gia' pagata tre volte.

Ruling 64: **e la guardia di riempimento non basta: un derivatore non puo'
sapere il resto del modello.** Le altre due righe inviolabili (seed 2 cl2/mat2,
seed 3 **cl1/mat3** — ⚠ *corretto dalla ri-review*: qui c'era scritto
`cl2/mat3`, che e' la riga che la guardia **esclude**, non il residuo; la
convenzione di indicizzazione era la stessa, il numero era semplicemente
sbagliato) lo sono per `structural:site_transition` — le due attivita' che
sommerebbero abbastanza minuti hanno **sedi diverse** e non possono stare in
fasce adiacenti. Verificato dal revisore spegnendo i builder di sede: la stessa
riga torna `OPTIMAL`. Quindi anche con la Ruling 63 applicata, il seed 2 di
`max_hours_half_day` crea ancora una riga inviolabile e il caso di banco resta
un verde incapace di fallire. — Decisione: **si applica la Ruling 63 e si
dichiara il residuo**, invece di inseguirlo. Le guardie dei derivatori sono
condizioni necessarie calcolate sulla **sola geometria**: non vedono le altre
risorse, le indisponibilita', le sedi. Una riga che le supera puo' comunque
essere inviolabile per via del resto del modello, e stabilirlo richiede di
**chiedere al solver**. — Costo se sbagliato: si continua a credere che il banco
sia esatto quando e' solo necessario.

Ruling 65: **la sonda esatta di violabilita' e' la proposta di metodo piu'
importante uscita finora, e va valutata al Task 17 — non adottata qui.** Il
revisore osserva che e' la **quarta volta** (Rulings 45, 48, 51, 63) che una
guardia in forma chiusa o euristica si rivela necessaria-ma-insufficiente, e che
farne il criterio di `potere` (contare le righe **dimostrabilmente** violabili
invece di quelle create) renderebbe il banco esatto per tutte le famiglie e
avrebbe intercettato da solo le prime tre. — Decisione: **non adottarla al Task
11**. Il motivo non e' il costo di esecuzione (un `Solve` in piu' per riga su
modelli piccoli) ma la **forma**: la sonda richiede di riesprimere in CP-SAT la
condizione di violazione di ogni famiglia, cioe' di **reimplementare nel banco
la cosa che il banco verifica**. Come diagnostico una tantum e' eccellente ed e'
cosi' che il revisore l'ha usata; come machinery permanente introduce una
seconda implementazione di diciotto vincoli, che e' esattamente la struttura che
questo progetto evita altrove (una primitiva per concetto, `vocabulary.py`). Da
riprendere al Task 17 con questa obiezione sul tavolo. — Costo se sbagliato: si
rimanda un miglioramento reale di sei task.

Ruling 66: **due proprieta' dichiarate in docstring, zero test che le
difendono — e la mutazione lo dimostra su tutta la suite.** (a) `A = B` su
`FORBIDDEN_SEQUENCE`: la docstring afferma che il doppio ciclo vieta l'adiacenza
«in **entrambi** i versi». Il revisore ha verificato che la **proprieta' e'
vera** (congelata alla fascia 1: la libera non puo' ne' alla 0 ne' alla 2,
entrambe `INFEASIBLE`) e che **nessun test la difende**: mutando il `post` a
vietare un verso solo con A = B, la suite resta **338 passed, 4 skipped**. (b)
`MAX_HOURS` con `A != B`: la docstring afferma — correttamente contro il checker
— che si somma la **sola** materia A. Non esiste in tutto il repo una riga
`MAX_HOURS_*` con A != B: mutando il `post` a sommare anche B quando le materie
differiscono, la suite resta **338 passed, 4 skipped**. — Decisione: entrambe
richiedono il proprio test. E' la Minor 5 del Task 10 («una proprieta' scritta
per non essere rilitigata deve avere il suo test») applicata due volte, di cui
una — la (b) — su una famiglia che il brief **non** nominava: il ragionamento e'
stato applicato dove era scritto e non dove serviva. — Costo se sbagliato: due
docstring che affermano cio' che il codice potrebbe smettere di fare.

Ruling 67: **l'assert su `KIND` e' tornato opt-in, cioe' la Ruling 58 e' stata
soddisfatta a meta'.** L'estrazione chiedeva che una sottoclasse smemorata si
**rompesse** invece di prendere in silenzio la semantica "half". Ora l'assert e'
in `_check_kind()`, **un metodo che ogni `post` deve ricordarsi di chiamare**:
una futura sottoclasse di `_Bucketed` che scrive il proprio `post` senza
chiamarlo e' di nuovo nella condizione che la Ruling voleva chiudere. —
Decisione: spostare l'assert dentro `buckets()`, che ogni `post` **deve**
chiamare per funzionare: li' e' inevitabile invece che da ricordare. — Costo se
sbagliato: una rete di sicurezza che protegge solo chi si ricorda di usarla.

Ruling 68: **due test byte-identici.** `test_forbidden_sequence_vieta_l_adiacenza`
e `test_adr018_forbidden_sequence_una_congelata_la_libera_evita` hanno corpi
identici carattere per carattere (verificato programmaticamente dal revisore):
stesse attivita', stesso piazzamento, stessa riga, stesse asserzioni — solo le
docstring differiscono. Il "ramo 2" di ADR-018 **e' gia'** il primo test. —
Decisione: differenziare il secondo mettendo **B congelata e A libera**, verso
non ancora esercitato con A != B, invece di fonderli. — Costo se sbagliato: due
test che si contano come due e valgono uno.

Ruling 69: **quattro sospetti chiusi con misure, e vanno registrati come chiusi.**
(a) Il seed 1 di `MAX_HOURS_DAY` **e' varianza**: 2/6 su sei esecuzioni, e la
sonda esatta dice che tutte e 4 le sue righe sono violabili. (b) `seed 3` e
`seed 4` di `max_hours_half_day` sono 0/6 **deterministici ma non difettosi**:
le righe sono violabili (4/4 e 1/3), il solver semplicemente non le viola — e'
il limite del banco a testimone dichiarato dalla Ruling 44, da non trasformare
in una soglia da inseguire. (c) La Ruling 56 **tiene numericamente**: su tutte
le coppie × 5 seed × 2 secchi il testimone non viola mai la riga derivata, ed
esiste sempre un secchio esattamente uguale a `param` — cioe' `param` e' il piu'
stretto che il testimone soddisfa. (d) **Costo zero sul Fermi, misurato**: i tre
`post` non vengono mai chiamati (`tests/fermi.py` crea 0 righe
`SubjectConstraint`), e il modello resta a **8140 variabili / 1082 constraint**,
identico alla misura dello spike pubblicata in CLAUDE.md. — Costo se sbagliato:
si rimisura cio' che era gia' misurato.

Ruling 70: **il nome del modulo non si cambia.** `subject_buckets.py` ora
contiene anche `FORBIDDEN_SEQUENCE`, che i secchi non li usa; la docstring lo
dichiara in chiaro invece di nasconderlo, ed e' la scelta giusta. Rinominare il
modulo a meta' branch e' churn che sporca il diff di sei task senza cambiare
nulla. — Decisione: si tiene, con la dichiarazione. — Costo se sbagliato:
cosmetico.

## Task 11 — ri-review del giro 1, e giro 2 applicato dal controller

Ruling 71: **il codice algoritmico nuovo nel banco e' corretto, verificato per
forza bruta indipendente.** `_massimo_pacchetto` (ricerca esatta con
memoizzazione su bitmask) confrontato con un'enumerazione scritta da zero
(`itertools.product`, controllo a intervalli, nessuna ricorsione): **14 casi a
mano** (insieme vuoto, `starts` vuoto, durata > 1, `starts` bucati come li
produce `respects_breaks`, secchi larghi 1 e 2, due trappole golose speculari) e
**34 000 casi casuali**, **zero divergenze**. — E l'obiezione che avevo sollevato
sull'indipendenza dal giorno **non morde**: variante *day-aware* confrontata su
226 coppie, **0 capienze diverse e 0 verdetti diversi**, e il motivo e'
strutturale — l'unico filtro dipendente dal giorno e' il **singolo** giorno
festivo, e `days_per_cycle >= 3`, quindi un giorno comune esiste sempre. Se mai
sbagliasse, sbaglierebbe **generoso**. — Costo se sbagliato: una guardia che
scarta righe buone senza che nulla lo segnali.

Ruling 72: **la sussunzione della Ruling 63 e' vera, per argomento e per
misura.** I due passaggi tengono contro il codice (la capienza somma un
sottoinsieme del totale; `param >= ` la durata di ogni singola attivita' perche'
ognuna contribuisce da sola l'intera durata al proprio secchio nel testimone —
**premessa misurata: 226/226 righe, zero eccezioni**). Ricostruite le due
guardie vecchie e confrontate su seed 1-20 × 2 secchi: **0 controesempi**. Righe
create: `day` 83 contro 83 (**no-op completo**, come previsto), `half` 84 contro
87. — Piu' una prova che la misura non dava: `_capienza_secchio` e' un limite
superiore **vero** sulla somma di secchio del checker, quindi la guardia **non
puo'** escludere una riga violabile. Le due guardie vecchie erano rimovibili. —
E la sonda esatta riproduce **esattamente** i numeri della Ruling 63: 18 righe
create e **2** inviolabili su mezza giornata (da 20 e 4), 18 e **0** su giornata;
entrambe le residue tornano violabili spegnendo i builder di sede, cioe' la
diagnosi della Ruling 64 confermata sui numeri. Potere vincolante su seed 1-20:
`day` invariato 20 su 20, `half` ridotto di 1 su tre seed, **mai a zero**. —
Costo se sbagliato: si rimuovono guardie che servivano.

Ruling 73: **il test su A != B difendeva meta' della proprieta'.** La docstring
di `_MaxHoursSubject` afferma due cose: (a) B **non** si somma quando A != B, e
(b) il tetto sulla **sola A** si applica comunque. Il test copriva solo (a), ed
era unilaterale **per forma** — asserisce che il modello resti *fattibile*, e un
builder che per le righe A != B non posta nulla e' fattibile pure lui. Misurato:
con `if row.subject_a_id != row.subject_b_id: return` in testa a `post()`
l'intero ramo A != B spariva e la suite restava **340 passed, 4 skipped**. — ⚠ Il
fix brief chiedeva letteralmente «un tetto che il totale della **sola** A
sfora», cioe' proprio il blocco mancante: l'implementatore ha scelto la
costruzione complementare, che e' quella giusta per (a), e non ha aggiunto
l'altra. E' la Ruling 66 chiusa a meta'. — Decisione: aggiunto il secondo blocco
(seconda congelata di A, tetto stretto a 60', libera forzata nello stesso
giorno → `INFEASIBLE`). **Verificato per mutazione**: con quel `return` il test
ora fallisce alla riga del secondo blocco. — Costo se sbagliato: un ramo intero
del builder cancellabile senza che nulla protesti.

Ruling 74: **«generosa, mai stretta» aveva due precondizioni non scritte, ed
erano proprieta' del testimone, non del dominio.** `_massimo_pacchetto` vieta la
sovrapposizione, ed e' un limite superiore vero solo finche' (1) la capienza
simultanea vale 1 — il default di `Resource.simultaneous_capacity`, che
l'harness non tocca mai, ma `OccupationBuilder` supporta la capienza cumulativa
ed e' feature EDT documentata; e (2) la classe non ha **partizioni** — il
checker prende `keys = {classe, *tutte le sue parti}`, e due attivita' su parti
diverse (sdoppiamento, `_REL`/`_ALT`) sono legittimamente simultanee e cadono
**entrambe** nella stessa somma di secchio. In entrambi i casi il massimo reale
supera la capienza calcolata, la guardia diventa **stretta**, e scarta righe
violabili — esattamente il modo di sbagliare che quella frase dichiarava di
evitare. — Non morde oggi (misurato: capienza 1 ovunque, zero partizioni). —
Decisione: **asserite**, non solo scritte. Due `assert` in testa a
`_capienza_secchio` su `Resource.objects.filter(simultaneous_capacity__gt=1)` e
`ClassPart.objects.exists()`, cosi' chi arricchisce il testimone se ne accorge
invece di perdere copertura in silenzio. — Costo se sbagliato: la quarta volta
che una precondizione taciuta diventa falsa senza che nessuno se ne accorga.

Ruling 75: **il gemello ADR-018 di mezza giornata era il gemello DAY con l'enum
scambiato.** Le due congelate stavano entrambe nel mattino, dove secchio-giorno
e secchio-mezza-giornata **coincidono**, e le asserzioni non distinguevano le due
semantiche: misurato con `MaxHoursHalfDayBuilder.KIND = "day"`, il test restava
verde. — Decisione: aggiunto il blocco che le separa — il **pomeriggio dello
stesso giorno** e' un secchio diverso e la libera ci deve poter entrare, cosa che
il tetto per giornata vieterebbe. **Verificato per mutazione**: con `KIND =
"day"` ora falliscono **due** test invece di uno. — Costo se sbagliato: un test
che si conta come copertura di una semantica e copre l'altra.

Ruling 76: **l'assert su `KIND` saltava le righe con `param` nullo.**
`post()` faceva `if row.param is None: return` **prima** di `buckets()`, dove
vive l'assert: «inevitabile invece che da ricordare» (Ruling 67) era vero a meno
di quel `return`. — Decisione: `buckets()` chiamato per primo, il risultato
tenuto in una variabile. ⚠ Resta un assert di **runtime, per riga**: un builder
che nessuna riga viva raggiunge non lo esegue mai. `__init_subclass__` sarebbe
incondizionato — annotato, non fatto, non era chiesto. — Costo se sbagliato:
cosmetico oggi, ma e' la terza volta che questa rete di sicurezza si scopre
piu' larga di quanto dichiarava.

Ruling 77: **la Ruling 64 nominava la riga sbagliata, e la discrepanza fra le
due sonde e' chiusa.** Non era una convenzione di indicizzazione diversa (sul
seed 2 le due fonti concordano, `1B/MAT` = cl2/mat2): il numero era proprio
sbagliato. Elenco nominale del seed 3, secchio mezza giornata — `1A/ITA`
(`param=60`) creata e violabile; `1A/STO` (`param=120`) creata e **inviolabile**
per le sedi; `1B/STO` (`param=180`) **esclusa** dalla guardia. Cioe' `cl2/mat3`
e' la riga che la guardia rimuove, e il residuo e' `cl1/mat3` — quello che
diceva il giro di correzione. La Ruling 64 e' stata **corretta in loco**. La
docstring del derivatore non nomina righe e resta corretta. — Costo se
sbagliato: un numero sbagliato nel registro che sopravvive alle sonde che
l'hanno prodotto.

Task 11: **complete** — 340 passed, 4 skipped. Skip: i quattro preesistenti,
nessuno nuovo.

## Task 12 — WEEKLY_ORDER (rulings pre-dispatch)

Ruling 78: **il derivatore del piano non salta: fallisce.** Misurato prima di
scrivere il brief, 60 seed, sonda usa-e-getta. Non produce mai zero righe
(`righe=1` su 60/60), ma su **19 seed su 60 il testimone stesso viola la riga
appena derivata** — cioe' `run_family` passo 1, che e' un fallimento duro, non
uno skip. E il **seed 1 e' fra questi**: la famiglia sarebbe rossa al primo
test del banco. Causa: `prime[s] = min(...)` calcolato sull'**unione delle
settimane**, mentre il checker valuta uno `ScheduleState` per firma. Con A
prima di B nell'unione ma B prima di A dentro una singola firma, la riga nasce
gia' violata. — Decisione: derivare la condizione **per firma**, non
sull'unione. Quarta occorrenza della Ruling 56 (le firme contano quando si
*deriva* un parametro, non solo quando si posta). ⚠ Nota di contrasto: per
SAME_DAY, SAME_HALF_DAY e TWO_DAYS la derivazione sull'unione **e' corretta**,
perche' sono vincoli di «non accade mai» e un sottoinsieme dei piazzamenti puo'
solo averne di meno; qui e' un `min`, e il minimo di un sottoinsieme e' **piu'
grande**, quindi la relazione si ribalta. — Costo se sbagliato: una famiglia
rossa al primo colpo, o peggio, aggiustata rilassando il test invece del
derivatore.

Ruling 79: **il derivatore riscritto, misurato in tutte e tre le direzioni.**
Per ogni classe e ogni coppia **ordinata** di materie distinte: (i) in ogni
firma in cui entrambe hanno almeno un'attivita' attiva, il testimone deve gia'
avere `first_a <= first_b` — se una sola firma lo smentisce, la coppia si
scarta; (ii) violabilita' **geometrica** in almeno una firma, con la guardia
generosa `min(prima ammissibile di B) < min(ultima ammissibile di A)` sulle
celle che `_try_place`/`GridBuilder` ammettono (giorno festivo e intervalli
inclusi); (iii) accumulo su tutte le coppie, niente `return` alla prima.
Misurato: **0/60 vacuo**, **0/60 testimone violato**, da 1 a 6 righe per seed
(il massimo strutturale e' 12: due classi per sei coppie ordinate). Potere
vincolante col builder assente — che qui e' letteralmente il caso «builder reso
no-op», perche' senza registrazione la riga non posta nulla — **19/20 seed**,
e **4/5 dentro il banco**. — Costo se sbagliato: gli stessi 19 seed rossi di
sopra.

Ruling 80: **ADR-018 su una variabile derivata che non e' un tetto, e il
principio che unifica i precedenti.** `residual_cap` clampa a zero e il quarto
ramo di `_post_cross` azzera i letterali liberi: entrambi **possono** rendere
il modello infattibile, e la docstring lo dichiara voluto. Qui invece il
vincolo del piano (`prima_a <= prima_b`, secco) sarebbe infattibile per un
motivo diverso: con le congelate gia' in violazione (`FB < FA`) chiederebbe
alle libere di **riparare il passato**, non di non peggiorarlo. La distinzione,
che vale per tutta la famiglia d'ordine: **INFEASIBLE che nasce dal divieto di
peggiorare e' ammesso; INFEASIBLE che nasce dalla pretesa di riparare non lo
e'.** Letta cosi', il clamp a zero di `residual_cap` *e'* «non peggiorare» —
non chiede mai alle libere di rientrare sotto il tetto. — Decisione: quando
`FA` e `FB` sono entrambi finiti e `FB < FA`, il ramo diventa una **disgiunzione
reificata**: o `prima_a <= prima_b` (riparazione, ammessa ma non imposta), o
`prima_a >= FA` **e** `prima_b >= FB` (status quo: nessuna libera davanti alle
colpevoli, quindi `Finding.key` resta **identico** alla baseline, che e'
esattamente l'argomento gia' scritto in `_post_separable`). Piu' debole di
entrambi i rami presi da soli, e non vieta il miglioramento. — Costo se
sbagliato: la modalita' di fallimento piu' segnalata di questo branch, un
solver che rifiuta di lavorare su un orario sporco.

Ruling 81: **WEEKLY_ORDER e' la famiglia dove la sonda esatta di violabilita'
del revisore (Ruling 65) costa quasi nulla**, e va portata al Task 17 come dato
e non come opinione: la condizione di violazione e' letteralmente
`prima_b < prima_a`, una clausola sulle **stesse due variabili che il builder
gia' costruisce** — nessuna seconda implementazione da scrivere. E' l'estremo
favorevole dello spettro; l'obiezione della Ruling 65 (riesprimere in CP-SAT la
condizione di violazione di diciotto famiglie) resta valida sulle altre. Il
seed 5, deterministicamente non mordente su quattro esecuzioni consecutive,
sarebbe il primo caso da chiarire con quella sonda: oggi non si sa se le sue 4
righe siano inviolabili davvero o solo fortunate. — Costo se sbagliato: si
decide al Task 17 su un'impressione invece che su un caso misurato.

## Task 12 — rulings del giro di review

Ruling 82: **la nona occorrenza, e stavolta falsifica una decisione del
registro.** La Ruling 80 giustificava il ramo status-quo con «`Finding.key`
resta identico alla baseline». **Falso.** `Finding.key` include `activities`,
cioe' l'**identita'** delle due attivita' argmin; `prima_a >= FA` fissa il
**valore** del minimo, non chi lo realizza. Con due attivita' della stessa
materia su **parti diverse della stessa partizione** (sdoppiamento, ADR-013,
in scope v1) il pareggio esatto su `FA` e' ammissibile — parti della stessa
partizione non condividono atomi, quindi non confliggono — e `_placed_of`
scioglie la parita' con `sorted` stabile, cioe' con l'ordine di inserimento
del queryset. Riprodotto dal revisore e **riprodotto di nuovo da me con una
sonda indipendente**: baseline `(2,3)`, dopo `(1,3)`, modello `OPTIMAL`. Un
finding `HARD` **nuovo** sotto il differenziale di ADR-018: esattamente il
fallimento che il criterio di riuscita dello spike dichiara inaccettabile. —
Decisione: nel ramo status-quo si vieta anche il **pareggio**, per attivita'
libera (`pos >= FA + 1`, `pos >= FB + 1`), cosi' «l'argmin resta la congelata
colpevole» e' vero **per costruzione** invece che sperato; `prima_a >= FA`
diventa implicato e si toglie, per non mascherare le mutazioni. Costo
consapevole: si vietano anche i pareggi innocui, ma quali siano dipende
dall'ordine dei pk — non e' una semantica su cui vincolare. — Costo se
sbagliato: la modalita' di fallimento che lo spike esiste per escludere,
dentro il ramo che esisteva per evitarla.

Ruling 83: **la causa a monte sta nel checker, e va registrata, non
aggirata in silenzio.** `_placed_of` ordina per `(day, start_slot)` con
`sorted` stabile: a parita' di collocazione, **l'identita' di `a[0]` dipende
dall'ordine del queryset**, e con lei `Finding.key`. E' la stessa forma gia'
registrata in CLAUDE.md per `MaxSiteChangesChecker` (`state.occupancy` e'
una `list`, il conteggio dipende dall'ordine d'inserimento): un artefatto
implementativo che diventa semantica. — Decisione: la Ruling 82 vincola di
piu' per non dipenderne, e la questione va nell'elenco «Ancora aperto» di
CLAUDE.md accanto a quella delle sedi, da decidere in `domain/analysis`.
Tradurre un artefatto sarebbe peggio che stringere. — Costo se sbagliato: due
famiglie che dipendono da un ordine di inserimento senza che nessuno lo sappia.

Ruling 84: **la spiegazione del seed 5 era falsa, e la Ruling 81 si chiude
con un dato.** La docstring attribuiva il seed non mordente alla generosita'
della guardia geometrica. Misurato dal revisore con la sonda esatta di
violabilita' (builder spento, `Add(prima_b < prima_a)` sulle stesse variabili,
risolvi): **tutte e quattro** le righe del seed 5 rispondono `OPTIMAL`, cioe'
sono realmente violabili. La guardia non ha creato nessuna riga vacua. Il seed
non morde perche' il **banco** accetta «una soluzione qualunque», e CP-SAT ne
restituisce una che le rispetta per conto suo. — Decisione: riscrivere il
capoverso con la causa vera. — Costo se sbagliato: una docstring che
sopravvive ai Task 13-17 e indirizza verso la correzione sbagliata (stringere
una guardia che non c'entra).

Ruling 85: **la forma avversaria diventa la regola per i vincoli d'ordine.**
Il test «il vincolo morde» scritto come «risolvi e asserisci sulla soluzione»
e' una lotteria: `test_weekly_order_impone_la_prima_occorrenza` restava verde
col `post()` reso no-op, in modo **deterministico** (8/8), perche' la fixture
crea A prima di B e CP-SAT piazza in ordine di creazione. La forma
**avversaria** — costruisci il modello, forza la violazione sulle stesse
variabili che il builder costruisce, attendi `INFEASIBLE` — morde **5/5** seed
del banco, seed 5 incluso, contro 4/5. — Decisione: adottata qui e **nei brief
dei Task 13-17**, che riguardano altri sei vincoli d'ordine. ⚠ Si tiene anche
una versione «risolvi e asserisci», ma con l'**orientamento invertito**
rispetto all'ordine di creazione della fixture: copre l'altro modo di
sbagliare, un builder che vieta tutto. Obiettivo dichiarato: **6/6 rossi**
sotto `post()` no-op, contro 3/6 di oggi. — Costo se sbagliato: sei famiglie
con il test-vetrina che non testa niente.

Ruling 86: **la Ruling 65 va decisa per famiglia, non in blocco.** Il revisore
ha usato la sonda esatta di violabilita' due volte in questa review (per il
seed 5 e per misurare la forma avversaria), e le e' costata **cinque righe di
CP-SAT**: per i vincoli d'ordine la condizione di violazione *e'* una clausola
sulle variabili che il builder gia' costruisce. L'obiezione della Ruling 65 —
«una seconda implementazione di diciotto famiglie dentro il banco» — resta
valida dove la violazione va riespressa, ma **non qui**. — Decisione: al Task
17 la domanda non e' «adottarla o no» ma «per quali famiglie il costo e'
zero»; i vincoli d'ordine sono il primo gruppo dove lo e'. — Costo se
sbagliato: si butta via una sonda che ha gia' trovato due cose che nient'altro
aveva trovato.

Ruling 87: **`prima_b >= FB` era vera e indifesa** — rimossa, la suite intera
resta verde (351 passed). L'altra meta' (`prima_a >= FA`) era difesa,
verificato per contro-mutazione. Il test del ramo disgiuntivo non conteneva
**nessuna attivita' libera di B**: esercitava meta' congiunzione. Terza
occorrenza della Ruling 66 su questo branch. — Decisione: il test guadagna una
libera di B, verificata per mutazione. — Costo se sbagliato: meta' di un
vincolo che si puo' cancellare senza che nulla protesti.

Ruling 88: **la precondizione taciuta del filtro sull'unita', e la sua
direzione.** Il derivatore filtra su `klass.pk in w.tokens[aid]`, il checker
espande a `{class_id, *parts}`. Con una `ClassPart` in gioco un'attivita'
legata alla sola parte sfugge al derivatore e non al checker. Direzione:
generosa su A (innocua), **stretta su B** (scarta righe violabili — il modo di
sbagliare che la docstring dichiara di evitare), e sul passo 1 del banco
produrrebbe una riga **nata gia' violata**, cioe' la modalita' della Ruling
78. Oggi non morde: zero `ClassPart` nel banco. — Decisione: `assert`, come
gia' in `_capienza_secchio` (Ruling 74). ⚠ Pattern **preesistente**, condiviso
coi derivatori dei Task 10-11 (sei occorrenze): la generalizzazione e'
materiale del Task 17, nominata e rimandata. — Costo se sbagliato: la quinta
precondizione taciuta che diventa falsa senza che nessuno se ne accorga.

Ruling 89: **il bersaglio «6/6 rossi sotto no-op» del fix brief era mal
posto, e l'implementatore ha avuto ragione a non raggiungerlo.** Due dei
test — la guardia `A = B` e la materia assente — asseriscono che il builder
**non posta nulla**: un `post()` reso no-op li soddisfa per definizione, e
nessuna riformulazione puo' cambiarlo. Difendere l'assenza di un vincolo
richiede la mutazione **mirata** (togliere quella guardia), non la mutazione
globale. Misurato dopo la correzione: **7/9 rossi** sotto no-op, i due verdi
sono esattamente quelli, ciascuno difeso dalla propria mutazione mirata. —
Decisione: nei brief dei Task 13-17 il criterio si formula «ogni test che
afferma la **presenza** di un vincolo dev'essere rosso sotto no-op», non
«tutti». — Costo se sbagliato: un bersaglio numerico che spinge a
riformulare test corretti per inseguire una cifra.

Task 12: **completo** — 354 passed, 4 skipped. Commit `84a2aca`, pushato.
Skip: i quattro preesistenti, nessuno nuovo. Critical chiuso e verificato con
sonda indipendente (pareggio -> INFEASIBLE, cella dopo FA -> OPTIMAL: non e'
stato stretto fino all'inutilita').

## Task 13 — IMPOSED_SUCCESSION (rulings pre-dispatch)

Ruling 90: **i checker della famiglia di materia non hanno le stesse uscite
anticipate, e darlo per scontato costa.** `WeeklyOrderChecker` esce con
`if ... or not a or not b: return`. `ImposedSuccessionChecker` **non ha
nessuna guardia**: con `b` vuoto, `b_halves` e' vuoto, `any(...)` e' sempre
falso, e **ogni** occorrenza di A diventa una violazione. Trovato misurando:
la mia prima stesura del derivatore A != B saltava le firme dove B e' assente
(`if not aa or not bb: continue`) — la regola giusta per WEEKLY_ORDER — e
produceva 12 testimoni violati su 40. Con la guardia corretta («se in una
firma A c'e' e B no, la riga **non e' derivabile**»): 0/40. — Decisione: ogni
task d'ordine legge il **proprio** checker riga per riga, e la lista delle
uscite anticipate va nel brief per esteso; nessuna analogia con la famiglia
gia' tradotta. — Costo se sbagliato: righe nate gia' violate, cioe' la
modalita' della Ruling 78, in una forma che il seed 1 non intercetta.

Ruling 91: **il derivatore del piano lascia meta' builder senza banco.**
Crea solo righe con A = B, mentre `ImposedSuccessionBuilder` ha **due
semantiche in una riga** (A = B: gli scarti fra occorrenze consecutive;
A != B: dopo ogni A serve una B entro `delay`). Il ramo incrociato non
sarebbe stato esercitato da nessun seed. In piu' i difetti gia' visti:
`return` alla prima coppia, derivazione sull'unione delle settimane, nessuna
guardia di violabilita'. — Decisione: **un solo derivatore** che crea
entrambe le forme e le accumula. Misurato su 40 seed: **0 vacui**, **0
testimoni violati**, 4-12 righe per seed, **entrambe le forme presenti su
tutti e cinque i seed del banco** (same 3-6, cross 1-3), potere vincolante
**39/40**. — Costo se sbagliato: meta' di un builder che nessun seed tocca,
con il conteggio delle righe a dire il contrario.

Ruling 92: **ADR-018 su una clausola che *esige* invece di vietare** — la
generalizzazione della Ruling 80 alla forma clausale. Una clausola resta
posta finche' almeno un suo letterale rappresenta una **decisione**; diventa
una pretesa di riparazione quando tutti i letterali negativi sono gia'
falsificati dalle congelate e l'unica via d'uscita e' muovere le libere.
Concretamente: A = B, si salta la coppia `(u, w)` se una congelata di A
occupa `u`, una occupa `w`, e **nessuna** congelata sta in mezzo — e' una
violazione della baseline, e chiedere a una libera di infilarcisi sarebbe
riparare. A != B, il trigger non e' l'indicatore aggregato `sa[u]` ma il
**singolo letterale**: si posta la clausola solo per le occorrenze di A
**libere**, perche' il finding e' per occorrenza (`[pa.activity_id]`) e
quello di una congelata senza B in finestra e' della baseline. ⚠ Saltare la
clausola *intera* sarebbe sbagliato: una **libera** di A nella stessa mezza
giornata produrrebbe un finding **nuovo**, con il proprio id. — Costo se
sbagliato: o un solver che rifiuta un orario sporco, o uno che ne peggiora
uno.

Ruling 93: **l'implementatore del Task 13 si e' fermato a meta' (builder e
derivatore fatti, test no) per un'interruzione di processo, e i test li ho
scritti io.** Nessuna anomalia di merito: builder e derivatore corrispondono
al brief, e il banco era gia' verde (359 passed) senza nessuno skip nuovo. —
Decisione: finire in loco invece di ripartire, e verificare **cinque**
mutazioni invece delle tre canoniche, visto che nessun altro rivedra' questi
test prima della review finale. — Esiti: `post()` no-op -> 3 rossi (i tre che
affermano una **presenza**); salto ADR-018 rimosso -> `adr018_same`; termine
`+ [sa[m]]` rimosso -> `same_con_una_in_mezzo` e `adr018_same`; «salta la
clausola intera quando una congelata occupa il secchio» -> `adr018_cross`;
finestra off-by-one -> `cross_con_la_b_in_finestra` e `adr018_cross`. Ognuno
dei sei test nuovi cade sotto almeno una mutazione.

Ruling 94: **la prima stesura del test ADR-018 A = B era di nuovo la lotteria
della Ruling 85, e l'ho corretta prima di committare.** Asseriva «risolvi, poi
guarda che la libera non sia finita nelle mezze 1-3»: dove il solver la metta
di suo non e' una proprieta' del builder. Riscritta in forma **strutturale**:
si fissa la libera **fuori** dall'intervallo fra le due congelate (mezza 5) e
si chiede che il modello resti fattibile — la negazione diretta della pretesa
di riparazione. Con il salto rimosso il test diventa rosso in modo
deterministico. — Costo se sbagliato: la stessa forma che il Task 12 aveva
gia' pagato, ripetuta dentro il task che l'aveva scoperta.

Task 13: **completo** — 365 passed, 4 skipped. Skip: i quattro preesistenti.

## Task 14 — HALF_DAY_GAP (rulings pre-dispatch)

Ruling 95: **«il conservativo dimostrato» non e' conservativo: e' esatto.** Il
piano intitola cosi' il Task 14 e ne fa il caso vetrina della
sovra-approssimazione deliberata (spec §4.2): il checker vincola le coppie
**consecutive** incrociate, il builder **tutte** quelle incrociate, e la tesi
e' che il secondo sia piu' stretto. Le due regole sono invece **equivalenti**.
Dimostrazione: se esiste una coppia incrociata a distanza `< param`, ne esiste
una **adiacente** altrettanto corta — si prende quella con meno elementi in
mezzo; se qualcosa c'e' in mezzo, quel qualcosa ha sorgente `a` o `b`, quindi
forma con uno dei due estremi una coppia **incrociata** con distanza non
maggiore e meno elementi in mezzo, contro la minimalita'. Verificato su
**200 000** casi sintetici casuali (liste `(mezza, id, sorgente)` di 2-6
elementi, `param` 1-4, entrambe le modalita'): **zero divergenze** fra il
verdetto del checker e quello «tutte le coppie». — Decisione: il builder
resta com'e' (corretto in entrambe le letture), ma la docstring dichiara
l'**equivalenza** con la dimostrazione, non una direzione conservativa; e
cade la motivazione dell'istruzione «deriva contro la regola del builder»,
che si tiene lo stesso come rete se la dimostrazione fosse sbagliata. ⚠ Da
correggere anche in spec §4.2 al Task 17. — Costo se sbagliato: un caso
vetrina che insegna una tecnica su un esempio che non la esercita.

Ruling 96: **il builder si scrive riusando `_post_separable` e `_post_cross`,
e cosi' eredita ADR-018 invece di riscriverlo.** Il builder del piano posta a
mano `a_u + a_w <= 1` su indicatori derivati (`subject_bucket`) — cioe'
esattamente la forma per cui esiste la tabella a quattro rami di
`_post_cross` — e **non ha alcun trattamento ADR-018**: con due congelate
nelle due mezze giornate il modello diventerebbe INFEASIBLE per colpa del
passato. Ogni coppia di questo vincolo e' pero' gia' uno dei due casi noti:
stessa materia e **stesso** secchio -> `_post_separable`; stessa materia e
secchi **diversi**, o materie diverse -> `_post_cross` (che il Task 10 usa
gia' su due secchi distinti per TWO_DAYS). — Decisione: il builder diventa un
ciclo sulle coppie che delega ai due helper, e i due helper perdono
l'underscore (`post_separable`, `post_cross`) perche' non sono piu' privati
di un modulo. — Costo se sbagliato: una terza copia della stessa tabella a
quattro rami, da tenere allineata a mano.

Ruling 97: **misure del derivatore** (40 seed, per firma, entrambe le forme,
accumulato, guardia `param >= n`): **0 testimoni violati**, 0-13 righe,
**seed 33 vacuo** (fuori dal banco), potere vincolante **36/40** e **4/5 nel
banco** — il seed 2 non morde, in modo **deterministico** su tre esecuzioni.
In linea con le altre famiglie (10/15, 12-14/15). — Decisione: si accetta, e
il peso della dimostrazione lo porta il test avversario scritto a mano
(Ruling 85), non il banco.

Ruling 98: **il potere vincolante del Task 14 rimisurato da me: 4/5 nel banco,
non 3/5.** Il report dell'implementatore riportava «35/39, 3/5 nel banco» con
uno scarto attribuito al rumore di CP-SAT. Rimisurato con il derivatore
**registrato** e il builder spento per `monkeypatch` (la forma piu' pulita:
nessuna modifica al sorgente, nessuna riscrittura del derivatore nella sonda):
**36-37/40** su due esecuzioni, e i non mordenti sono sempre gli stessi
quattro — seed 2, 21, 33 (vacuo, 0 righe), 37. Nel banco morde **4/5**, e il
seed 2 e' l'unico fuori, deterministicamente. Riproduce esattamente la misura
pre-dispatch. — Decisione: vale la misura fatta col derivatore vero; una
sonda che ne riscrive una copia misura la copia. — Costo se sbagliato: un
numero peggiore del reale che spinge a «riparare» un derivatore sano.

Task 14: **completo** — 375 passed, 4 skipped. Mutazioni ricontrollate da me:
`post()` no-op -> 3 rossi (i tre che affermano una presenza); seconda
`post_cross` rimossa -> il test sui due versi, e solo quello.

## Task 15 — i quattro PARTS_* (rulings pre-dispatch)

Ruling 99: **l'arricchimento della scuola del banco previsto dal Task 15 rompe
34 test, misurato prima di dispatchare.** Aggiunta una `ClassPartition` con due
parti su `classes[0]` e due attivita' di parte, come da piano: `34 failed, 342
passed, 3 skipped`. I fallimenti sono di **due specie**, e la differenza e' la
dimostrazione che le asserzioni della Ruling 88 servivano:

- le famiglie con l'assert (WEEKLY_ORDER, IMPOSED_SUCCESSION, HALF_DAY_GAP,
  MAX_HOURS_*) falliscono dicendo *cosa* e' rotto: «_derive_weekly_order filtra
  su klass.pk: con le parti, le occorrenze legate alla sola parte sfuggono al
  derivatore e non al checker»;
- le famiglie **senza** assert (SAME_DAY, SAME_HALF_DAY, TWO_DAYS — il pattern
  preesistente dei Task 10) falliscono con «il testimone stesso viola
  two_days_incompatible (seed 1): [...]», lasciando a chi legge il compito di
  scoprire perche'.

— Decisione: la generalizzazione del filtro `klass.pk` all'espansione
`{class_id, *parts}` **non e' materiale del Task 17**, come dicevo nella Ruling
88: cade dentro il Task 15, ed e' il suo prerequisito. Il task si spezza in due
dispacci — **15a** l'arricchimento e la generalizzazione, con la suite riportata
a verde e nessuno skip nuovo; **15b** i quattro builder. — Costo se sbagliato:
un dispaccio solo che tocca sette derivatori, quattro builder nuovi e la
fixture condivisa, con 34 test rossi come punto di partenza.

Ruling 100: **`_capienza_secchio` diventa *stretta* con le parti, e stretta e'
la direzione vietata.** La sua ricerca esatta di impacchettamento presuppone
che due attivita' non possano partire nella stessa fascia (precondizione
asserita al Task 11, Ruling 74). Con le parti la presupposizione cade: due
attivita' su **parti diverse della stessa partizione** non condividono atomi e
possono coesistere, quindi la capienza reale del secchio e' **maggiore** di
quella calcolata, e la guardia scarta righe **violabili**. — Decisione: si
rilassa in modo dichiaratamente generoso, `max_pacchetto(attivita' di classe) +
somma sui gruppi di parte di max_pacchetto(quel gruppo)`: ignora i conflitti
classe-contro-parte, quindi e' `>=` della capienza vera per costruzione, e resta
molto piu' fine della somma nuda dei minuti. ⚠ Il costo e' qualche riga
inviolabile che rientra nel banco — la direzione accettabile, quella che costa
un caso debole invece di copertura persa in silenzio. — Costo se sbagliato: la
guardia che il giro di correzione del Task 11 aveva costruito apposta per non
sbagliare in questa direzione, che ci ricasca appena la fixture cambia.

Ruling 101: **il testimone del banco non e' mai stato un orario valido, e la
premessa del passo 2 di `run_family` era falsa dal Task 5.** Trovato
misurando il testimone contro **tutti** i checker invece che contro le sole
causali della famiglia — cosa che nessun test faceva. Su `HEAD` prima del
Task 15a: `coverage_mismatch` su 5 seed su 5, `site_transition` su 4 su 5.
Il secondo e' quello che morde: `InstituteSettings.site_transition_slots` ha
default **1** sul modello e `_make_activities` assegna una sede a meta' delle
attivita' **a caso**, quindi il testimone viola un vincolo il cui builder e'
registrato e attivo in **ogni** `solve()`. Cioe' il testimone non e' un punto
ammissibile del modello completo, e la frase che `run_family` stampa
(«c'era un testimone, quindi INFEASIBLE e' un fallimento duro») non regge per
nessuna famiglia diversa da `structural:site_transition` — che infatti si
ripara la fixture da sola prima di derivare. Non ha mai prodotto un rosso, ma
avrebbe mandato qualcuno a cercare un difetto in un builder sano. — Decisione:
`_school` fissa `site_transition_slots = 0` (nessun vincolo di partenza) e
`_derive_site_transition` alza la soglia per conto proprio, come gia' faceva.
Verificato: dopo la correzione il testimone non produce piu' nessun
`site_transition`. — Costo se sbagliato: la decima occorrenza del difetto
ricorrente, e la prima annidata nel **banco** invece che in un builder.

Ruling 102: **`coverage_mismatch` sul testimone resta, ed e' innocuo per
costruzione — ma va scritto, non lasciato scoprire.** I `Service` della
fixture sono per (piano, materia), mentre `student_units` attribuisce il
monte ore alle **parti** quando la classe ne ha; con l'arricchimento del
Task 15a i conteggi salgono (4-7 -> 5-13 findings per seed). Non tocca la
premessa del passo 2: `structural:coverage` e' l'unico checker **senza
builder**, deliberatamente (e' `PLACEMENT_INDEPENDENT`), quindi non entra mai
nel modello. — Decisione: scritto nel docstring di `tests/solver_harness.py`
insieme al limite esatto di «orario valido», e portato al Task 17 come
prerequisito di qualunque oracolo differenziale a tutto campo sul banco. Si
riparerebbe **nella fixture**, non in `domain/analysis/`. — Costo se
sbagliato: un oracolo futuro che parte gia' sporco e che qualcuno prova a
sistemare dalla parte sbagliata.

Task 15a: **completo** — 379 passed, 6 skipped. Gli skip passano da 4 a 6 e
sono tutti misurati: `site_transition` 3 sparito, `arrival_departure` 3 e 5
(era 2 e 4 — solo rimescolamento, e' una famiglia di risorsa),
`same_day` 3 e `two_days` 5 **causati davvero dalle parti** (l'occorrenza di
parte rende la riga non derivabile, e giustamente), `same_day` 5 causato dal
rimescolamento su griglia densa, non dalle parti. ⚠ Il brief diceva sei
occorrenze di `klass.pk in w.tokens[aid]`: a HEAD ne erano **nove** su sette
derivatori, e l'implementatore ha seguito il codice invece del brief.

## Task 15b — i quattro PARTS_* (rulings)

Ruling 103: **l'implementatore ha smentito il mio brief su due punti, e ha
ragione su entrambi.** Prima volta su questo branch che la regola «se il brief
contraddice il codice, vince il codice» produce una correzione di merito
invece di un dettaglio.
(a) **Il pareggio di fascia parte/classe e' realizzabile.** Il brief lo dava
per impossibile «perche' un'attivita' di classe occupa la classe e tutte le
sue parti». Ma `_is_class_level` etichetta «classe» in base a **una qualunque**
chiave di `Kind.CLASS` nei token, non a quella della riga: un'attivita' con
`classes=[X]` e `parts=[p di Y]` e' etichettata classe pur non occupando Y.
L'esattezza si ricava invece dal **criterio d'ordinamento** del checker
(`"class" < "part"`), che rende i due rami asimmetrici — `sp >= sc` smentisce
«parti prima», `sp < sc` smentisce «classi prima» — e quindi **complementari**,
senza nessuna assunzione sull'occupazione. Verificato leggendo: la
partizione delle coppie e' esatta e copre il pareggio.
(b) **Il trattamento ADR-018 che avevo chiesto ammetterebbe finding nuovi, e
peggio, lascerebbe passare piazzamenti illegali.** Il finding di `_PartsOrder`
porta fra le `activities` **tutte** le occorrenze del secchio, quindi il
livello giusto e' il **secchio** (azzeramento dei letterali liberi quando le
sole congelate lo violano gia' — il quarto ramo di `post_cross`), non la
coppia. E nel ramo omogeneo le coppie tutte-congelate **vanno postate**: sono
cio' che ancora il booleano `prima_le_parti` al verso gia' scelto dal passato.
Saltarle, come chiedeva il brief, lascerebbe il booleano libero e permetterebbe
a una libera di stare dalla parte sbagliata. ⚠ E non puo' rendere infattibile:
si posta solo quando le congelate da sole sono legali, quindi almeno un ramo
sopravvive per costruzione. — Costo se sbagliato: un brief che, applicato alla
lettera, avrebbe prodotto il difetto che voleva evitare.

Ruling 104: **il banco e' quasi cieco su queste quattro famiglie, e le righe
sono comunque violabili.** Misurato: righe create su 20 seed 29/23/30/38, **0
testimoni violati**; ma «morde col builder spento» solo 3/12, 3/9, 0/12, 0/15,
e sui cinque seed del banco **1 rosso su 11** non saltati (9 skip nuovi).
Seconda sonda, che forza la violazione invece di risolvere e guardare:
**118 righe su 120** danno INFEASIBLE col builder acceso e FEASIBLE con quello
spento. Cioe' le righe sono violabili quasi sempre, ed e' la **forma** del
banco a non farle mordere — la stessa causa gia' misurata per WEEKLY_ORDER al
seed 5 (Ruling 84), qui in scala molto piu' grande. — Decisione: si accetta,
il peso lo portano i dieci test avversari scritti a mano (7 rossi su 10 sotto
`post()` no-op, verificato da me). Ed e' **la prova piu' forte finora** a
favore della sonda esatta di violabilita' come criterio permanente: da
portare al Task 17 con questi numeri (Rulings 65, 86). — Costo se sbagliato:
quattro famiglie il cui banco passa quasi sempre per il motivo sbagliato.

Ruling 105: **vacuita' trovata misurando, non ragionando**: per i due modi
omogenei **due** occorrenze non possono mai produrre piu' di una transizione,
quindi ogni riga su un secchio con due sole occorrenze e' matematicamente
inviolabile (al seed 2, `_H` ne creava due). Aggiunta la guardia «tre
occorrenze co-attive e secchio largo almeno tre fasce». Sesta forma di
vacuita' censita. — Costo se sbagliato: righe che il conteggio del potere
vincolante conta e che nessun piazzamento puo' violare.

Task 15b: **completo** — 400 passed, 15 skipped. Mutazioni ricontrollate da
me: `post()` no-op -> **7 rossi su 10**; `KIND` scambiato fra i due omogenei
-> **solo** `test_h_e_ab_hanno_secchi_diversi`, cioe' il test scritto apposta
per separarli esiste e morde.


## Task 16 — `structural:didactic_weight`

Ruling 106: **il derivatore del piano non restituiva niente** — terza
occorrenza esatta dello stesso difetto (Task 15, Task 16, e il Task 12 in
forma diversa). `run_family` avrebbe saltato la famiglia su **ogni** seed, con
cinque test verdi per non aver fatto nulla. Intercettato prima del dispatch,
nel brief. — Decisione: la misura pre-dispatch del derivatore del piano resta
il passo piu' redditizio dell'intero ciclo, e va scritta nella retrospettiva
del Task 17. — Costo se sbagliato: una famiglia intera coperta solo in
apparenza.

Ruling 107: **secondo difetto del derivatore del piano, meno visibile**:
sommava su **tutti i token**, quindi il tetto derivato poteva venire da un
docente — una chiave che il checker non guarda. Un tetto sopra il massimo che
un'unita'-studente possa mai raggiungere e' **inviolabile**, e il banco lo
conterebbe come successo. Corretto sommando sulle stesse unita' del checker
(`_student_keys`), per firma, con guardia di violabilita'. — Misurato da me
(Ruling 98, `monkeypatch` sul builder **registrato**, derivatore non
riscritto): 25 seed, **0 vacui, 0 testimoni violati, 13/25 mordono** a builder
spento, media 2,6 tetti accesi su 3. L'implementatore riportava 14/25: la
differenza e' la stocasticita' di CP-SAT multi-thread, non un disaccordo. —
Costo se sbagliato: la famiglia passa per il motivo sbagliato.

Ruling 108: **la guardia di violabilita' della mezza giornata non era un
maggiorante**, e a scoprirlo e' stata la misura dell'implementatore, non la
rilettura: il checker attribuisce il peso alla meta' in cui l'attivita'
**comincia**, quindi una che comincia nell'ultima fascia del mattino pesa sul
mattino occupando il pomeriggio. Osservato 8 contro un «limite» di 6.
Direzione innocua (si perde potere, non si guadagna un falso successo) ma
reale: i seed vacui erano cinque, sono zero. — Costo se sbagliato: potere
vincolante buttato via in silenzio.

Ruling 109 (**la piu' importante del task**): **ADR-018 non e' applicabile a
un vincolo indipendente dal piazzamento, e `residual_cap` da solo lo
nascondeva.** La docstring consegnata dichiarava: «la somma e' separabile,
quindi il trattamento e' `residual_cap`; un secchio gia' oltre il tetto per
colpa del passato non rende infattibile il modello». Vero per giornata e mezza
giornata — **falso per la settimana**. Il secchio settimanale contiene *tutte*
le celle candidate di ogni attivita' dell'unita', quindi `AddExactlyOne` rende
la somma dei letterali liberi una **costante**: col residuo clampato a zero il
vincolo diventa `costante positiva <= 0`, falso comunque vada il piazzamento.
Non «inagibile»: **contraddittorio**. Non vietare un peggioramento, ma
pretendere che il passato venga riparato — il caso che la Ruling 80 esclude.
Misurato con una sonda: due congelate da 2 punti, tetto settimanale 3, una
libera -> **INFEASIBLE**. — Decisione: si distingue il secchio **evadibile**
dall'**inevadibile** (`posta(..., evadibile=False)`), e il tetto settimanale
non si posta quando a sforarlo sono le congelate da sole. ⚠ Continua a
postarsi quando il colpevole e' il **totale** (congelate piu' libere, o nessuna
congelata): li' il passato non c'entra, l'istanza non ha soluzione, e tacere
restituirebbe un orario che `check_schedule` boccia. Due test tengono ferme le
due meta', e sono separati per mutazione: la vecchia forma (clamp sempre)
rende rosso **solo** il primo, «salta sempre l'inevadibile» rende rossi i
quattro test settimanali compreso il secondo. — Costo se sbagliato: un orario
con un passato illegale rende il solver inutilizzabile, cioe' esattamente cio'
che ADR-018 esiste per impedire.

Ruling 110: **e una meta' del problema non e' risolvibile da nessun builder**,
dichiarata invece che nascosta. Anche saltando il vincolo, la soluzione
restituita porta comunque il finding `weight_week`, e la sua `Finding.key` non
e' quella di prima: `activities` cresce delle libere e `quantities["weight"]`
cambia. Le libere vanno collocate, e ovunque vadano pesano. — Decisione:
**l'oracolo differenziale a tutto campo va formulato su una chiave piu'
grossolana** (causale + risorsa) per le famiglie placement-invariant, oppure
quelle famiglie vanno dove EDT le mette davvero: nell'analisi di **capienza**,
che si esegue prima del calcolo e non dentro. Aggiunto a «Ancora aperto» in
`CLAUDE.md` e alla lista del Task 17. — Costo se sbagliato: l'oracolo finale
fallisce su un caso per cui non esiste correzione, e si cerca il difetto nel
builder.

Ruling 111: **il tetto settimanale non e' derivabile da un testimone, per la
stessa ragione strutturale** — e questa volta il limite e' stato dimostrato,
non ipotizzato: con tutte le attivita' piazzate il peso settimanale e'
identico in ogni soluzione, quindi qualunque tetto soddisfatto dal testimone
e' soddisfatto sempre. Confermato sui numeri (il tetto settimanale del piano
non e' mai violato su nessuno dei 25 seed, nemmeno a builder spento). Le due
semantiche settimanali — istituto e classe, con la precedenza della classe e
il passaggio da `part_class` — sono coperte da **quattro** test scritti a
mano. — Costo se sbagliato: si insegue potere vincolante dove non ce n'e'.

Ruling 112: **mutazioni ricontrollate da me, e una discrepanza col report**:
`build()` no-op -> **10 rossi su 13** (i sette di presenza piu' i seed 3, 4, 5
del banco), non 8 come riportato; verso mattina/pomeriggio invertito -> 5;
`class_caps` ignorato -> 2; `part_class` saltato -> 1; `None` come 0 ->
13/13; somma su tutti i token -> 2; residuo senza clamp -> 1. La differenza
sul no-op e' la stocasticita' del solver, gia' dichiarata dall'implementatore.
Tutte le mutazioni previste sono catturate. — Costo se sbagliato: si crede
coperto cio' che non lo e'.

Task 16: **completo** — 415 passed, 15 skipped (413 consegnati + i due test
del secchio inevadibile). Il registro dei builder e' chiuso: **26 chiavi su
27**, e la ventisettesima (`structural:coverage`) non ne ha una per
costruzione.


## Task 17 — la misura e la chiusura

Ruling 113 (**la scoperta del task**): **il Fermi non misura il modello
completo, misura il dataset.** Il piano (§5.6, Step 4-5) dava per scontato che
il Fermi fosse la prova del modello completo, e prevedeva perfino la diagnosi
in caso di INFEASIBLE. Misurato: **8140 variabili e 1082 constraint, identici
byte per byte a quelli dello spike a cinque vincoli** del 2026-08-09, stesso
0,56s. Causa: il dataset ha **zero** righe `ResourceTimeConstraint`, **zero**
`SubjectConstraint` e i quattro tetti di peso a `None` — 21 builder su 26 non
postano nulla. — Decisione: il test resta (porta la **scala**: 284 attivita'
contro le 14-32 del banco) ma con due assert che dichiarano il limite, e la
misura del modello si sposta su `test_modello_completo`. — Costo se sbagliato:
si chiude il piano credendo di aver misurato ventisei famiglie quando se ne
sono misurate cinque. Il piu' puro «successo travestito» dell'intero branch, e
sarebbe finito nel changelog come risultato.

Ruling 114: **nessun test provava i ventisei builder insieme.** `test_famiglia`
prova ventisei modelli da una famiglia ciascuno; l'oracolo del Fermi non ha
righe. Due traduzioni corrette separatamente possono contraddirsi una volta
postate insieme, e niente lo avrebbe visto. — Decisione: aggiunto
`test_modello_completo` (5 seed): tutte le famiglie attive insieme sullo stesso
testimone. 22-23 famiglie con righe su 26, 48-73 righe, OPTIMAL ovunque,
oracolo pulito. Il testimone regge la congiunzione **per costruzione**, quindi
INFEASIBLE resta un fallimento duro. — Costo se sbagliato: un'incompatibilita'
fra builder si scopre in produzione.

Ruling 115: **i derivatori non sono componibili in ordine qualunque**, trovato
componendoli. Due formulazioni dense (Ruling 34) **riparano** il testimone:
`_derive_site_transition` riassegna le sedi (che `max_site_changes` conta) e
`_sintonizza_parti` riassegna la materia (su cui ogni `SubjectConstraint` e'
ancorata). In ordine alfabetico: INFEASIBLE su 2 seed su 3, con il testimone
sporco su `subject_half_day_gap`, `subject_imposed_succession`,
`subject_max_hours_day/half_day` e `max_site_changes`. ⚠ **Entrambe le
docstring dichiaravano esplicitamente di non disturbare nessuno** — vero per il
testimone in se' (griglia e occupazione non cambiano), falso per le righe gia'
derivate da altri. Dodicesima occorrenza del pattern. — Decisione: non e' un
difetto ma una **precedenza** (`MUTANTI`: chi ripara va per primo), e le due
docstring sono corrette con la misura. — Costo se sbagliato: il test del
modello completo sarebbe nato rosso e si sarebbe cercato il difetto nei
builder.

Ruling 116: **il test di completezza del registro del piano dipendeva
dall'ordine di raccolta di pytest.** Legge `REGISTRY` e `BUILDERS` direttamente,
ma i due registri si popolano per **import**: fuori da una suite che abbia gia'
caricato `domain.analysis.checkers`, `REGISTRY` e' vuoto. — Decisione: il test
passa da `all_checkers()`/`all_builders()`, che l'import lo fanno loro, e fissa
i due numeri (27 e 26) invece del solo insieme vuoto. — Costo se sbagliato: un
test verde il cui verdetto dipende da chi gira prima.

Ruling 117: **la sonda esatta di violabilita', decisa** (chiude Rulings 65, 86,
104). **Adottata come forma dei test scritti a mano** — ed e' gia' la regola
della casa dalla Ruling 85 — **e non come criterio di `potere` del banco**.
Le due ragioni sono opposte a quelle attese: (a) come criterio non servirebbe,
perche' i numeri dicono che le righe **hanno gia'** potere (118/120 violabili
sui PARTS_*) ed e' il **passo 3** del banco a non saperlo sfruttare (1 rosso su
11); (b) come machinery permanente resta l'obiezione della Ruling 65 —
reimplementare in CP-SAT la condizione di violazione di ventisei famiglie
dentro il banco che le verifica. — Conseguenza dichiarata: **il passo 3 di
`run_family` e' un rilevatore debole** e va detto; il peso della copertura lo
portano i passi 1 e 2 piu' i test avversari. — Costo se sbagliato: si continua
a credere che «qualunque soluzione dev'essere pulita» sia una rete fitta.

Ruling 118: **il bilancio dei conservativi era sbagliato in entrambi i versi.**
La spec §4.5 prevedeva «diciannove esatti su ventuno, il conservativo serve due
volte». A consuntivo: `HALF_DAY_GAP` e' **esatto** (Ruling 95, dimostrato e
verificato su 200 000 casi), il D.T.B. era conservativo **nel verso sbagliato**
(corretto il 2026-08-24, prima del piano), e resta conservativo il solo
`structural:site_transition`. **Venticinque esatti su ventisei.** — Decisione:
corretto in §9.4 della spec, lasciando la previsione scritta com'era. — Costo
se sbagliato: si eredita una stima della precisione del modello piu' pessimista
del vero, e si cercano margini dove non ce ne sono.

Task 17: **completo** — 424 passed, 15 skipped. Commit 7712a6f (la misura) e il
commit della documentazione. Il piano `modello-hard-completo` e' chiuso:
diciassette task su diciassette.


## Review finale — rulings sui findings chiusi da me

Ruling 119: **`PartsHomogeneousHalfBuilder` non era difeso da nessun test, e
la mutazione che avrebbe dovuto accorgersene non poteva.** Verificato di
persona: aggiungendo un `post()` no-op alla **sola** sottoclasse `_H`, la
suite intera resta **424 passed, 15 skipped** — identica alla baseline. Le
altre tre danno 5, 3 e 3 rossi. La causa e' metodologica: le Rulings 104 e 112
mutavano `_PartsOrderBuilder.post`, cioe' **tutte e quattro le sottoclassi
insieme**, e l'unico test che nomina `_H`
(`test_h_e_ab_hanno_secchi_diversi`) lo usa nel verso **legale**, cioe'
afferma un'assenza — che per costruzione non puo' diventare rossa. —
Decisione: aggiunto `test_h_morde_dentro_la_stessa_mezza_giornata`, e la
mutazione per sottoclasse ora da' 1 rosso. ⚠ **Corollario da portarsi
dietro**: quando un builder ha sottoclassi, la mutazione va fatta **per
sottoclasse**, non sulla base — altrimenti misura la base. — Costo se
sbagliato: un builder cancellabile senza che nulla protesti, e `_H`/`_AB`
differiscono per un solo attributo.

Ruling 120: **settima forma di vacuita', e la giustificazione scritta era
falsa.** `_derive_max_gap` dichiarava «crea sempre una riga: anche a budget
zero e' un vincolo vero, perche' qualunque buco lo violerebbe». Il buco e'
`ultima - prima + 1 - conteggio`: serve una mezza giornata larga **almeno
tre**, e la fixture pesca `(slots_per_day, morning_end_slot) = (4, 2)`, dove
entrambe le meta' sono larghe due. Misurato dalla review con la sonda esatta:
**8 righe inviolabili su 40 seed**, e il **seed 2 e' fra i cinque del banco**.
— Decisione: guardia con un **maggiorante geometrico** (in una meta' larga
`W` il buco massimo e' `W - 2`); si scartano solo righe dimostrabilmente
inviolabili. Effetto: `test_famiglia[max_gap_hours-2]` ora **salta**
onestamente invece di passare senza provare niente — **uno skip in piu', 15 ->
16**, misurato e non nascosto. ⚠ Resta fuori il seed 1 (violabile
geometricamente, inviolabile per il resto del modello): e' il limite gia'
dichiarato dalla Ruling 64. — Costo se sbagliato: un caso su cinque del banco
di una famiglia su cui questo progetto ha gia' sbagliato due volte.

Ruling 121: **i quattro `parts_*` si invalidavano a vicenda, e `MUTANTI` non
poteva proteggerli.** La precedenza introdotta al Task 17 protegge le *altre*
famiglie dai mutanti; ma tutti e quattro i `parts_*` chiamano
`_sintonizza_parti`, che riassegna la **stessa** materia della **stessa**
attivita' di parte, quindi il secondo ri-sintonizza sotto le righe del primo.
Misurato dalla review: l'assegnazione cambia in 22 seed su 40, e il testimone
viola una riga gia' derivata in **6 su 40** — esattamente i sei rossi di
`run_tutte_le_famiglie` sui seed 6-45. — Decisione: **non** riordinare (non
esiste un ordine che funzioni) ma dare a `_sintonizza_parti` un guardiano,
`_sintonia_compatibile`, che accetta una riassegnazione solo se (a) il
testimone resta pulito su tutte le causali e (b) le righe `PARTS_*` gia'
create restano **ammissibili**, non solo non violate. La (b) chiude anche il
**sospetto non quantificato** della review — una riassegnazione puo' togliere
a un secchio una delle due etichette, rendendo vacua una riga gia' contata nel
`potere` — per costruzione invece che per misura. Misurato dopo: **40 seed su
40 puliti** (prima 34/40). Le righe scendono a 36-76 da 48-73: il minimo cala
perche' i numeri di prima **includevano** righe diventate vacue. Corretto
anche il messaggio d'errore del passo 1, che mandava a riordinare i mutanti —
il rimedio sbagliato. — Costo se sbagliato: la misura di punta del Task 17
rossa su un seed su sette, e un potere vincolante sovrastimato.

Ruling 122: **quarta forma di vacuita' (Ruling 49) mai applicata a
`_derive_two_days`** — l'unico derivatore di materia rimasto scoperto. Con
maschere di settimana disgiunte le due materie non compaiono mai nello stesso
`ScheduleState` e `TwoDaysChecker` non puo' emettere nulla. Misurato dalla
review: 3 seed su 60 (6, 22, 59), **nessuno fra i cinque del banco** — stesso
profilo latente delle Rulings 35 e 48. — Decisione: guardia `_coattive`,
scritta a parte perche' ⚠ `_coppia_violabile` **non** si puo' riusare: quello
richiede anche lo **stesso secchio** (`_ci_stanno`), mentre
`TWO_DAYS_INCOMPATIBLE` vuole l'opposto — A in un giorno e B in quello dopo.
Nessuno skip in piu' sui cinque seed del banco. — Costo se sbagliato: potere
vincolante sovrastimato in un seed su venti.

Ruling 123 (**metodo**): **la review finale valeva il suo costo, e le due
misure che hanno trovato tutto sono le stesse due di sempre.** I sei findings
vengono da: la **mutazione per singola classe** (Finding 3), la **sonda esatta
di violabilita'** (Finding 4), e l'**allargamento dei seed** da 5 a 40
(Findings 5 e 6, piu' i due ADR-018). Nessuno da una rilettura. ⚠ E il
risultato piu' importante e' **positivo**: su seed 6-25 per tutte e ventisei
le famiglie, e su seed 6-45 per la composizione, **zero** builder piu' larghi
del checker e **zero** piu' stretti del testimone. I difetti trovati stanno
tutti su input **sporco** (ADR-018), copertura di test e vacuita' del banco —
non nella traduzione dei vincoli. — Costo se sbagliato: si generalizza «la
review ha trovato sei cose» in «il modello e' fragile», che i numeri smentiscono.

## Coda — il banco che congela (2026-08-26 sera)

Fuori dai diciassette task: chiude il debito §9.7 «il banco non congela mai
nulla» (Ruling 20).

Ruling 124: **come si costruisce un input sporco senza perdere la premessa.**
Il banco ha bisogno di congelate **già in violazione**, ma anche della
garanzia che rimettere le libere dove stavano non aggiunga niente — altrimenti
`INFEASIBLE` non è più diagnosticabile (ADR-018 ne ammette metà). — Decisione:
ripack in **celle libere da conflitti di occupazione** (così il resto
dell'orario resta dov'è), poi congelare **chi è implicato** nelle violazioni
prodotte. L'attribuzione ha due forme e vanno usate dove servono: le attività
che il finding **nomina**, e — solo per i findings che non ne nominano nessuna
— tutte quelle che toccano la **risorsa**. ⚠ Gli otto vincoli orari sulla
risorsa (`_finding` in `time_constraints.py`) e `sites.py` non portano **mai**
`activities`. — Costo se sbagliato: misurato. Estendendo per risorsa **ovunque**
si congela l'intera classe a ogni violazione di materia (`_unit_resources`
restituisce le chiavi dell'unità), i semi utilizzabili scendono da 36/40 a
24/40 e il caso misto congelata/libera **dentro la riga violata** — il cuore di
ADR-018 — non viene mai esercitato.

Ruling 125: **la prova che morde è il forzare, non l'oracolo.** Su un input
sporco «risolvi e guarda» soffre lo stesso difetto misurato nella §9.6: CP-SAT
non cerca la soluzione cattiva. — Decisione: `build_model` + `model.Add(x[a, d,
s] == 1)` su ogni libera alla cella del testimone, e si attende che non sia
`INFEASIBLE`. Quell'assegnazione produce esattamente la baseline, quindi
rifiutarla è *pretendere una riparazione*. — Costo se sbagliato: è la prova che
ha trovato il difetto del Ruling 126; l'oracolo differenziale, da solo, non
l'avrebbe visto (il seme 38 dà `OPTIMAL` e zero nuove appena il difetto è
corretto).

Ruling 126: **`SiteTransitionBuilder` non aveva il guardiano ADR-018 che due
commenti gli attribuivano.** `any_free` guarda chi **tocca** le due fasce, non
chi **realizza** la coppia di sedi vietata: con due congelate di sede diversa a
distanza insufficiente — già una violazione per il checker — basta una libera
qualunque che tocchi una delle due fasce perché la clausola venga postata, e
quella clausola ha **entrambi** i letterali forzati a 1 dalle congelate.
`INFEASIBLE` per colpa del solo passato. Il commento di modulo di
`time_sites.py` («ha già ADR-018 nella forma della regola dell'implicazione:
non toccato») e il docstring di
`test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca` dichiaravano
entrambi il contrario. — Decisione: `_sede_congelata`, che salta la clausola
quando **entrambe** le sedi sono forzate da congelate, e che rispecchia
**letteralmente** la selezione dei letterali di `Vocabulary.site_occupied` —
stessa lettura di `by_cell`, stesso filtro su `site_id`, stesso filtro di
firma. Con una sola sede forzata la clausola resta ed è un divieto, che ADR-018
concede (caso 3). — Costo se sbagliato: un solve incrementale su una scuola con
più sedi risponde `INFEASIBLE` ogni volta che l'orario di partenza porta un
cambio di sede troppo stretto, cioè proprio nel caso d'uso per cui ADR-018
esiste. Mutazione: `_sede_congelata → False` fa due rossi,
`test_modello_sporco[38]` e il test ridotto.

Ruling 127 (**metodo**): **la mutazione ha bocciato metà del banco appena
scritto.** Il banco nasceva con due parti; la seconda,
`test_famiglia_con_congelate`, congelava una parte del testimone dov'è,
famiglia per famiglia, su baseline pulita: 78 test, 28 secondi, i due terzi del
tempo aggiunto. Misurato su **sette** mutazioni (`residual_cap` senza clamp,
`split` che conta le congelate come libere, `frozen_occupies` sempre falso,
`any_free` sempre vero, `_sede_congelata` sempre falso,
`_status_quo_rappresentabile` sempre vero, congelate con dominio pieno):
**zero rossi**, mentre il banco sporco le coglie su sei delle sette (4, 8, 2,
1, 1, 1 rossi; zero entrambi sul clamp di `residual_cap`, difeso dai soli test
scritti a mano). — Decisione: rimosso. — Costo se sbagliato: 28 secondi di
suite per un test che non afferma niente, e la falsa sicurezza di «il banco
copre anche il caso pulito con congelate». ⚠ Ricostruirlo solo dopo avergli
trovato una mutazione che lo faccia cadere.

Ruling 128: **la deriva d'identità, e perché l'oracolo del banco sporco ha una
chiave grossolana.** §9.5 attribuiva la crescita della `Finding.key` alle sole
famiglie indipendenti dal piazzamento. ⚠ **È più largo**: riguarda ogni
famiglia il cui finding nomina in `activities` la **coppia argmin** o la coppia
consecutiva invece del secchio intero. Misurato: `subject_imposed_succession`
al seme 20 passa da `(5, 7)` a `(4, 5)` sulla risorsa 1 con `gap 3 / max_gap
2` **identici**, perché una libera piazzata accanto a una congelata cambia
*quale* coppia è consecutiva. Sullo stesso seme il ramo pigro si vede come uno
**scambio**: `free_guaranteed` da `free_days 4 / free_half_days 1` a
`free_days 1 / free_half_days 4` — ripara una soglia e rompe l'altra,
scavalcando il booleano unico che esiste apposta per impedirlo. È
la stessa causa a monte del tie-break di `_placed_of` già in «Ancora aperto».
— Decisione: due esenzioni **dichiarate** in `_classifica_nuove`, non
implicite: la deriva d'identità (stessa causale, risorsa e quantità) e il ramo
pigro di §9.7 (peggioramento su una (causale, risorsa) **già** violata, e solo
per le tre famiglie a ramo disgiuntivo). Un test apposta pretende che entrambe
scattino sul seme 20. — Costo se sbagliato: un'esenzione larga renderebbe
l'oracolo cieco proprio dove serve; un'esenzione mai esercitata sarebbe codice
che nessun test afferma — la stessa forma del Ruling 127.

Ruling 129: **il docstring del banco falsificato entro l'ora.**
`run_family_congelata` dichiarava «la baseline resta pulita»: cancellando i
piazzamenti delle libere, le famiglie che contano una quantità *presente* —
successione imposta, minimi, distribuzione — sono violate proprio **perché
manca qualcosa**. Misurato: `imposed_succession` al seme 3, finding `(2,)
max_gap 2` già prima del solve. — Decisione: criterio di **contenimento**, non
`== set()`. — Costo se sbagliato: il banco rosso su una violazione che ADR-018
concede esplicitamente, cioè il contrario di quel che deve misurare. ⚠ §9.8 su
un documento vecchio di un'ora, scritto da chi stava già cercando quel pattern.

Ruling 130 (**osservazione, non risolta**): **`residual_floor` non è chiamato
da nessun builder** — solo dal proprio test. I «minimi» di §3.1 non sono mai
stati trattati per sottrazione di termini: i cinque casi di ADR-018 usano
`frozen_occupies` o la disgiunzione reificata. — Decisione: lasciato dov'è (è
il gemello documentale di `residual_cap`, non codice morto per distrazione) e
annotato. — Costo se sbagliato: si crede che esista un trattamento dei minimi
per sottrazione, e lo si riusa dove serve invece il residuo per forzatura.
