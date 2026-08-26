# Task 15b — i quattro `PARTS_*` — report

Worktree `modello-hard-completo`, HEAD `3eda06b`. **Nessun commit, nessun
push.** Suite: **400 passed, 15 skipped** (baseline 379 / 6).

File toccati:

| file | cosa |
|---|---|
| `domain/solver/builders/subject_parts.py` | **nuovo** — `_PartsOrderBuilder` e i quattro builder |
| `domain/solver/builders/__init__.py` | import del nuovo modulo |
| `tests/solver_harness.py` | il derivatore comune e le quattro registrazioni |
| `tests/test_solver_subject_parts.py` | **nuovo** — 10 test dedicati |
| `tests/test_solver_registry.py` | le quattro chiavi nuove + docstring |

---

## 1. Due punti in cui il brief non regge, e cosa ho fatto invece

### 1.1 Il pareggio di fascia parte/classe **e' realizzabile**

Il brief chiedeva di dichiarare che `sp == sc` non e' realizzabile — «un'attivita'
di classe occupa la classe e tutte le sue parti, quindi confliggerebbe
sull'occupazione» — e di farne la ragione dell'esattezza del ramo omogeneo.

**La premessa e' falsa.** `_is_class_level` (subject_constraints.py, riga 51)
etichetta «classe» un'attivita' che abbia **una qualunque** chiave di tipo
`Resource.Kind.CLASS`, non la classe *della riga*. Bastano due forme, nessuna
delle due esotica per questo dominio:

- un'attivita' con `classes = [X]` e `parts = [p]`, con `p` di un'altra classe
  `Y`: entra nell'unita' di `Y` etichettata «classe» e occupa `p`, ma **non**
  le altre parti di `Y`;
- una riga su un **raggruppamento** trasversale (ADR-013), dove le parti membre
  stanno in classi diverse: la lezione a classe intera di una di quelle classi
  non occupa le parti delle altre.

In entrambi i casi una «classe» e una «parte» dell'unita' possono stare nella
stessa fascia.

**Cosa ho fatto**: l'esattezza non poggia piu' su quell'assunzione, ma sul
**criterio d'ordinamento del checker stesso**. `entries.sort()` ordina tuple
`(fascia, etichetta, id)` e `"class" < "part"`, quindi a parita' di fascia la
classe viene prima. Da qui i due rami hanno strettezza diversa:

    parti-prima   ⟺  per ogni coppia   sp <  sc     (il pareggio lo rompe)
    classi-prima  ⟺  per ogni coppia   sc <= sp     (il pareggio lo rispetta)

Le due condizioni sono **complementari** (`sp >= sc` contro `sp < sc`): ogni
coppia di celle finisce in esattamente un ramo, e la traduzione coincide col
checker anche sui pareggi, senza assumere niente sull'occupazione. Verificato
sui tre casi che discriminano — `{C@2,P@2}` legale, `{P@1,C@2,P@2}` illegale,
`{P@1,C@2}` legale — ed esibito da
`test_omogeneo_e_il_pareggio_di_fascia`, che **costruisce** un pareggio reale
(attivita' con `classes=[1B]` e `parts=[p1 di 1A]`, contro un'attivita' su
`p2`) e lo mette alla prova nei due versi.

Per **before**/**after** il pareggio non e' mai in discussione: le due
disuguaglianze del checker sono gia' strette, e le coppie in pareggio non si
vietano in nessuno dei due modi.

### 1.2 Il trattamento ADR-018 del brief ammetterebbe finding `HARD` **nuovi**

Il brief chiedeva `any_free(ctx, (id_parte, id_classe))` **per coppia**, piu'
il salto delle coppie tutte-congelate nel ramo omogeneo. Leggendo il checker e
`Finding.key` non regge, in due direzioni opposte:

**(a) Per `before`/`after` la guardia sarebbe codice morto, e comunque non
basterebbe.** Il finding di `_PartsOrder` porta fra le `activities`
**tutte** le occorrenze del secchio (`[aid for _, _, aid in entries]`), e
`activities` sta dentro `Finding.key`. In un secchio **gia' violato dalle sole
congelate**, qualunque aggiunta libera produce un finding con una tupla
diversa, cioe' un finding **nuovo** — non lo stesso della baseline. Saltare
solo le coppie tutte-congelate lascerebbe entrare la libera, e l'oracolo
differenziale di ADR-018 la boccerebbe. E' esattamente la situazione del
quarto ramo di `post_cross` e del clamp a zero di `residual_cap`.

**(b) Per l'omogeneo saltare le coppie tutte-congelate sarebbe attivamente
sbagliato.** Quelle clausole sono cio' che **ancora** il booleano al verso che
il passato ha gia' scelto. Congelate `P@1` e `C@2` (secchio pulito, parti
prima); una libera di classe a `C@0` darebbe `C,P,C`, due transizioni,
violazione **nuova**. Senza la clausola sulla coppia tutta-congelata
`(P@1, C@2)` il ramo «classi prima» resterebbe soddisfacibile e il solver
potrebbe sceglierlo, ammettendo quel piazzamento.

**Cosa ho fatto** — il trattamento sta **sul secchio**, non sulla coppia:

- **secchio gia' violato dalle sole congelate** (`_viola` sul sottoinsieme
  congelato, mirror del checker) → si azzerano uno per uno i letterali
  **liberi** del secchio, parti e classi insieme, e non si posta alcun vincolo
  d'ordine. Divieto, non riparazione: puo' rendere il modello INFEASIBLE, ed e'
  cio' che ADR-018 concede;
- **secchio pulito dalle congelate** → si posta la traduzione per intero,
  **comprese** le coppie tutte-congelate. Non c'e' rischio di INFEASIBLE «per
  colpa del passato»: se le congelate del secchio sono pulite la loro sequenza
  ha al piu' una transizione, quindi e' `P…PC…C` o `C…CP…P`, e **almeno uno**
  dei due rami e' soddisfatto da tutte le coppie tutte-congelate. Il booleano
  resta scegliibile.

Conseguenza: `any_free` non compare in questo builder, e il perche' e' scritto
nel docstring — per `before`/`after` sarebbe **dimostrabilmente morto** (se le
congelate del secchio sono pulite, per `before` vale `max(parti congelate) <=
min(classi congelate)`, quindi nessuna coppia tutta-congelata soddisfa mai
`sp > sc` e nessuna clausola tutta-congelata viene mai generata), per
l'omogeneo sarebbe dannoso.

Con **una sola** congelata la clausola resta e forza a zero il letterale
libero: divieto, concesso da ADR-018 anche quando rende il modello INFEASIBLE
(`test_adr018_una_sola_congelata_resta_un_divieto`).

### 1.3 Il difetto del derivatore del piano: confermato

`_derive_parts` del piano non restituisce niente. `run_family` fa
`potere = d.fn(w)` e poi `if not potere: pytest.skip(...)`: con `None` tutte e
quattro le famiglie sarebbero saltate su ogni seed. Riscritto per intero.

---

## 2. Il derivatore, e i numeri

Struttura finale (`tests/solver_harness.py`):

- `_etichetta_parts`, `_secchi_parts`, `_parts_viola` — mirror del checker
  scritto **per conto proprio**, non importato dal builder: un derivatore che
  chiedesse al builder «e' violato?» direbbe si' e no esattamente quando lo
  dice lui;
- `_riga_parts_ammissibile` — le due condizioni (il testimone la soddisfa in
  **ogni** firma; la riga e' **violabile**);
- `_unita_parts` — due forme di unita': la **classe** (`_chiavi_unita`) e la
  singola **parte** (`class_part`, che porta anche quel ramo di `_unit_keys`
  dentro il banco per la prima volta);
- `_sintonizza_parti` — la formulazione «densa» (§2.3);
- `_derive_parts(w, tipo, kind)`, con `kind = "day"` per `PARTS_BEFORE_CLASS`,
  `PARTS_AFTER_CLASS`, `PARTS_BEFORE_OR_AFTER_CLASS_AB` e `"half"` per
  `PARTS_BEFORE_OR_AFTER_CLASS_H`.

### 2.1 Una vacuita' in piu' trovata misurando: l'omogeneo sotto tre occorrenze

«Piu' di una transizione» su **due** occorrenze e' aritmeticamente impossibile.
La sola guardia «il secchio ha entrambe le etichette» crea quindi righe
inviolabili quando nel secchio non ci stanno tre occorrenze. E ci stanno
davvero poche: dentro un'unita' due occorrenze non possono condividere la
fascia (una lezione a classe intera occupa la classe e tutte le sue parti; due
lezioni a classe intera occupano la classe), quindi il numero di occorrenze di
un secchio e' limitato dalla sua **larghezza**. Nel banco la mezza giornata
puo' essere larga due fasce.

Misurato: al seed 2 la famiglia `_H` creava **2 righe** che nessun piazzamento
poteva violare (la sonda di violabilita' non trovava alcuna configurazione
violante). Aggiunte al guardiano le due condizioni: almeno **tre** attivita'
co-attive in quella firma e un secchio largo almeno **tre** fasce
(`_larghezza_secchio`). Dopo la correzione quelle due righe non si creano piu'.

### 2.2 Potere vincolante — le tre versioni, misurate su 20 seed

Righe create, per famiglia, e seed su 20 in cui la derivazione non e' vacua:

| versione | `BEFORE` | `AFTER` | `_H` | `_AB` |
|---|---|---|---|---|
| v1 — solo unita' classe | 5 righe / 5 seed | 2 / 2 | 8 / 8 | 8 / 8 |
| v2 — + unita' parte | 12 / 7 | 5 / 3 | 16 / 8 | 18 / 8 |
| v3 — + guardia «tre occorrenze» | 12 / 7 | 5 / 3 | 14 / 7 | 18 / 9 |
| **v4 — + formulazione «densa»** | **29 / 12** | **23 / 9** | **30 / 12** | **38 / 15** |

**Testimoni violati: 0 su tutte le righe di tutte le versioni** (il passo 1 di
`run_family` non ha mai avuto niente da dire). **Findings col builder acceso:
0**, sempre.

### 2.3 La formulazione «densa» (Ruling 34), e perche' serviva

Osservando soltanto, questa famiglia e' quasi sempre vacua e **non per colpa
del derivatore**: `_make_activities` crea **una** attivita' per parte e le
pesca la materia a caso fra tre, quindi che l'attivita' di parte e una lezione
a classe intera della **stessa** materia finiscano nello stesso secchio del
testimone e' raro. Misurato in v3: **15 dei 20 casi del banco** (4 famiglie x
5 seed) saltavano per derivazione vacua.

Stessa via gia' presa da `_derive_site_transition`: il derivatore **costruisce**
lo scenario. `_sintonizza_parti` prova a riassegnare la **materia**
dell'attivita' di ogni parte e tiene la prima assegnazione che rende
ammissibile la riga sull'unita' di quella parte; se nessuna funziona rimette
l'originale, e il monte ore del `Service` segue la materia. Non tocca
`_make_activities` (cambierebbe il testimone di tutte le altre famiglie a
parita' di seed), non sposta nessun piazzamento e non cambia nessuna chiave di
occupazione — la materia non entra ne' nella griglia ne' nell'occupazione,
quindi il testimone resta valido esattamente com'era.

Effetto sul banco (seed 1-5): **da 15 skip a 9**.

### 2.4 Gli skip: 15 in totale, 9 nuovi — misurati, non aggiustati

Baseline confermata invariata: `arrival_departure` x2, `same_day` x2,
`same_half_day` x1, `two_days` x1 = **6**. Nuovi: `parts_after_class` seed
2, 3, 4; `parts_before_class` seed 1, 5; `parts_before_or_after_class_ab` seed
2; `parts_before_or_after_class_h` seed 2, 4, 5 = **9**.

Causa residua, misurata: dove `_sintonizza_parti` non trova nessuna materia
che funzioni, l'attivita' di parte e' piazzata **tardi** nella giornata,
e per `before` ogni materia con una lezione a classe intera prima di lei nello
stesso secchio smentisce la riga. Riparabile solo **spostando** il piazzamento
dell'attivita' di parte — cioe' toccando il testimone dove sta l'occupazione,
non solo l'anagrafica. Non l'ho fatto: e' un cambiamento di natura diversa e va
deciso, non improvvisato.

### 2.5 Il banco morde poco — e la sonda dice **perche'**

Col builder spento (`monkeypatch.setattr(_PartsOrderBuilder, "post", lambda
*a, **k: None)` in una sonda usa-e-getta, mai nel sorgente), sui 20 seed:

| famiglia | seed che mordono / seed con righe |
|---|---|
| `PARTS_BEFORE_CLASS` | 3 / 12 |
| `PARTS_AFTER_CLASS` | 3 / 9 |
| `PARTS_BEFORE_OR_AFTER_CLASS_H` | **0** / 12 |
| `PARTS_BEFORE_OR_AFTER_CLASS_AB` | **0** / 15 |

Sui 5 seed del banco: **1 caso rosso su 11** non saltati (tre esecuzioni:
`parts_after_class-5` una volta, `parts_before_class-4` due — CP-SAT non e'
deterministico fra esecuzioni).

⚠ **Non significa che le righe siano vacue.** Seconda sonda usa-e-getta: per
ogni riga creata si cerca (fino a 40 candidate) una configurazione che il
checker giudicherebbe violata, si verifica col builder **spento** che sia
raggiungibile, e si rifa' il modello col builder **acceso** forzando le stesse
celle. Risultato su 20 seed, v4:

| famiglia | righe con violazione raggiungibile e **bloccata** dal builder | inconcludenti |
|---|---|---|
| `PARTS_BEFORE_CLASS` | 29 / 29 | 0 |
| `PARTS_AFTER_CLASS` | 23 / 23 | 0 |
| `PARTS_BEFORE_OR_AFTER_CLASS_H` | 28 / 30 | 2 |
| `PARTS_BEFORE_OR_AFTER_CLASS_AB` | 38 / 38 | 0 |

**118 righe su 120**: forzando la violazione il modello col builder acceso e'
INFEASIBLE e quello col builder spento no. Le 2 inconcludenti (`_H`, seed 3)
sono righe per cui nessuna delle prime 40 configurazioni candidate e'
raggiungibile — altri vincoli del modello le bloccano prima; non e' una
prova che la riga sia vacua, ne' il contrario.

Conclusione onesta: **il banco a testimone e' debole su questa famiglia**, per
la stessa ragione gia' scritta per `WEEKLY_ORDER` al seed 5 — `run_family`
chiede solo «risolvi col builder acceso e guarda se la soluzione e' pulita», e
CP-SAT restituisce da se' una soluzione che rispetta la riga. Il peso della
prova sta sui dieci test avversari (Ruling 85), non sul banco.

---

## 3. I test dedicati — `tests/test_solver_subject_parts.py`

Nessun `test_parts_sul_banco` (Ruling 16, ottava applicazione). Tutti in forma
avversaria: `build_model` + `model.Add(ctx.x[...] == 1)` che **forza** la
violazione, e verdetto atteso `INFEASIBLE`.

1. `test_before_morde_se_la_parte_segue_la_classe`
2. `test_before_ammette_la_parte_prima_della_classe`
3. `test_after_morde_se_la_parte_precede_la_classe`
4. `test_after_ammette_la_parte_dopo_la_classe`
5. `test_omogeneo_vieta_l_interlacciatura` — `P C P`, due transizioni
6. `test_omogeneo_ammette_le_parti_compatte` — `P P C`, una transizione: e' la
   coppia 5+6 che distingue «al piu' una transizione» da «tutte le parti prima»
7. `test_h_e_ab_hanno_secchi_diversi`
8. `test_omogeneo_e_il_pareggio_di_fascia`
9. `test_adr018_secchio_gia_violato_dalle_congelate`
10. `test_adr018_una_sola_congelata_resta_un_divieto`

### 3.1 `_H` contro `_AB`: la direzione discriminante e' **una sola**

Il secchio mezza giornata e' un **sottoinsieme** di quello giornata, e togliere
elementi da una sequenza non puo' aumentarne le transizioni: quindi «illegale
per `_H`» implica sempre «illegale per `_AB`». **Una configurazione legale per
`_AB` e illegale per `_H` non esiste**, e il test va costruito nel verso
opposto: parte@0 e classe@1 (mattino, `P C`, legale per `_H`), piu' una
seconda parte@4 (pomeriggio, secchio con una sola etichetta, che il checker
salta). Sulla giornata intera la sequenza e' `P C P`: illegale per `_AB`.

### 3.2 Verifica per mutazione (Ruling 89)

Sei mutazioni, applicate al sorgente in una copia usa-e-getta e poi
ripristinate.

| mutazione | test che cadono |
|---|---|
| **M1** `post()` reso no-op | `before_morde`, `after_morde`, `omogeneo_vieta_l_interlacciatura`, `h_e_ab`, `pareggio`, `adr018_secchio_gia_violato`, `adr018_una_sola_congelata` — **7 su 10** |
| **M2** `MODE` scambiato fra `PartsBeforeBuilder` e `PartsAfterBuilder` | `before_morde`, `before_ammette`, `after_morde`, `after_ammette`, `adr018_secchio_gia_violato`, `adr018_una_sola_congelata` |
| **M3** `KIND` scambiato fra i due omogenei | `h_e_ab` — **e solo lui**: e' il test che li separa |
| **M4** `_viola` sempre falso (via la guardia ADR-018 sul secchio) | `adr018_secchio_gia_violato` |
| **M5** rami simmetrici (`sp > sc` invece di `sp >= sc`) | `pareggio` |
| **M6** «classi prima» come vincolo secco (niente `OnlyEnforceIf` sulle coppie `sp < sc`) | `omogeneo_ammette_le_parti_compatte`, `h_e_ab` |

Ogni test che afferma una **presenza** cade sotto M1. I quattro che affermano
un'**assenza** sono difesi da mutazioni mirate: `before_ammette` e
`after_ammette` da M2, `omogeneo_ammette_le_parti_compatte` da M6,
`adr018_secchio_gia_violato` (punto 1: il modello resta risolvibile) da M4.

⚠ Una mutazione che avevo previsto **non** funzionava: «postare ogni coppia
sotto `prima_le_parti.Not()`» lascia `omogeneo_ammette_le_parti_compatte`
verde, perche' in `P P C` tutte le coppie hanno gia' `sp < sc` e stavano gia'
in quel ramo. Misurata, scartata, sostituita con M6 e il docstring corretto di
conseguenza — non lasciato scritto un rosso che non c'era.

---

## 4. Cosa resta fuori, dichiarato

- **Il banco morde poco** sui due omogenei (0/12 e 0/15 seed): documentato
  sopra con la sonda che dimostra che le righe **sono** violabili e **sono**
  bloccate. Se un giro futuro volesse un banco che morde, la via e' arricchire
  `_make_activities` (piu' di un'attivita' per parte, o una per (parte,
  materia)) — cioe' toccare la fixture, non il derivatore.
- **Il tie-break di `_placed_of`** (voce aperta in CLAUDE.md dal Task 12) non
  tocca questa famiglia: `_PartsOrder` non usa `a[0]`, e il suo finding porta
  **tutte** le attivita' del secchio, non due argmin.
- **`row.subject_b` non entra**, in nessuno dei quattro tipi, nemmeno con
  A != B: `_PartsOrder.violations` usa solo `a`. Il gate di
  `SubjectBuilder.build` guarda l'unione di A e B (Ruling 60), quindi al piu'
  una riga si posta due volte identica — mai una firma si salta. Stessa nota
  gia' scritta per `_MaxHoursSubject`.
