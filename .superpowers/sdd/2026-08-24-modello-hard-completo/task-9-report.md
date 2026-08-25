# Task 9 — Le sedi: `MAX_SITE_CHANGES` e `structural:site_transition` — report

## Cosa ho implementato

`domain/solver/builders/time_sites.py` (nuovo): `MaxSiteChangesBuilder`
(`T.MAX_SITE_CHANGES`, eredita `ResourceBuilder`) e `SiteTransitionBuilder`
(`"structural:site_transition"`, eredita `Builder`, strutturale come
`OccupationBuilder`). Registrato in `domain/solver/builders/__init__.py`.

`tests/solver_harness.py`: sedi aggiunte a `_school` (`env["sites"]`, due
sedi sempre create), assegnazione di sede al 50% in `_make_activities`, due
derivatori (`_derive_max_site_changes`, `_derive_site_transition`).

`tests/test_solver_sites.py` (nuovo): sei test mirati.

`tests/test_solver_registry.py::test_i_builder_tradotti_finora` aggiornato
con le due nuove chiavi (conseguenza necessaria, come nei Task 7/8).

## Le quattro correzioni del brief

### Correzione 1 (Ruling 27) — il conservativo che non c'era

Letti i checker (`_site_sequence` in `time_constraints.py`, e
`SiteTransitionChecker` in `sites.py`): entrambi ragionano su coppie
**consecutive nella sottosequenza delle occupazioni con sede nota** — un'attività
senza sede interposta non spezza l'adiacenza, perché non entra nella sequenza.

**Riproduzione del difetto, con la formulazione originale del piano** (copia
letterale dello Step 3, "tutto vuoto in mezzo"), PRIMA di correggere: istanza
a tre fasce su un solo giorno, sede A / senza sede / sede B, `per_day = 0`.
Output verbatim:

```
STATUS: OPTIMAL {'attivita': 3, 'libere': 3, 'variabili': 22, 'constraint': 23, 'secondi': 0.022}
PIAZZAMENTI: {1: (0, 0), 2: (0, 1), 3: (0, 2)} act_a= 1 act_none= 2 act_b= 3
FINDING HARD max_site_changes (checker sulla soluzione del solver): [Finding(code='max_site_changes', message='Numero di cambi di sede superiore al limite fissato', severity=<Severity.HARD: 'hard'>, resources=(1,), activities=(), quantities={'day': 0, 'changes': 1, 'max_changes': 0}, weeks=(0, 1, 2, 3))]
```

Il solver (col builder del piano) trova `OPTIMAL` piazzando esattamente
[A, senza sede, B] — l'unico arrangiamento che non innesca nessuna delle sue
coppie, perché lo slot centrale è occupato (dalla senza-sede) e quindi
`occupied(1).Not()` è falso, mentre le coppie adiacenti (0,1) e (1,2)
richiedono un'attività *con* la sede sbagliata al bordo, cosa che qui non
succede. Il checker, rileggendo la stessa soluzione, trova un `max_site_changes`
`HARD` che il solver non aveva visto: il criterio di riuscita (oracolo
differenziale) rotto, esattamente come previsto dal brief.

**Correzione**: la condizione "in mezzo" è diventata "nessuna sede **nota**
in mezzo" (`site_occupied(..., site).Not()` per ogni sede, non
`occupied(...).Not()`). Con questa condizione la coppia `(s, t)` con
`sa != sb` è *esattamente* l'adiacenza nella sottosequenza dei checker.

**Verifica di direzione**: `tests/test_solver_sites.py::test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo`
riprende la stessa istanza contro il builder corretto e assert-a `INFEASIBLE`
(è l'unica istanza possibile su quella griglia e viola sempre il tetto — non
esiste un modo di piazzare le tre attività senza produrre un cambio). Passa;
`test_site_transition_impone_le_fasce_libere` e `test_max_site_changes_limita_i_cambi`
verificano su istanze pulite che il builder non sia diventato più largo altrove
(entrambe passano, la suite intera resta verde a 283/16 — vedi sotto).

**Il secondo caso (stessa fascia, sedi diverse) — verificato e non risolto.**
Costruita un'istanza con una classe a `simultaneous_capacity = 2` (il campo
esiste sulla `Resource` base, quindi è raggiungibile anche per una classe,
anche se il caso d'uso tipico è aule/materiali), due attività di sede diversa
su docenti diversi piazzate sulla stessa fascia:

```
OCCUPATION FINDINGS: []
MAX_SITE_CHANGES FINDINGS: [Finding(code='max_site_changes', ..., quantities={'day': 0, 'changes': 1, 'max_changes': 0}, ...)]
```

Zero finding di `structural:occupation` (la capienza cumulativa lo ammette),
un `max_site_changes` `HARD` dal checker — e nessuna coppia `s < t` del
builder può esprimerlo, perché non esiste `s == t`. **È raggiungibile.** Non
l'ho risolto (il brief lo vieta esplicitamente come iniziativa): documentato
nel docstring di `time_sites.py` come osservazione per il controller.

### Correzione 2 (Ruling 28) — ADR-018 in `MaxSiteChangesBuilder`

I "cambi" sono variabili derivate (letterali `c` da `AddBoolOr`), non termini
separabili: stesso schema di `MaxGapBuilder`/`MaxPresenceBuilder`. Aggiunto
`_frozen_site_changes(ctx, key, day, rep, sedi)` — la sequenza di sede delle
sole attività congelate su quella chiave/giorno/firma, stesso schema di
`_frozen_gap_minutes`/`_frozen_presence_minutes` — e il tetto è **clampato**:
`max(per_giorno, consumo_giorno)` per giorno, `max(per_settimana, consumo_settimana)`
per la somma settimanale. Non un salto (`continue`): il docstring di
`MaxPresenceBuilder` spiega perché saltare lascerebbe le libere peggiorare
oltre il debito già contratto, e `changes` è fra le `quantities` del
`Finding.key` — una violazione peggiorata è una violazione *nuova* per
l'oracolo differenziale.

`SiteTransitionBuilder` non toccato: ha già ADR-018 nella forma della regola
dell'implicazione (uso `any_free(ctx, tocca)` invece di reinventarla a mano).

**Due test, come richiesto.** Entrambi verificati RED sotto mutazione
deliberata (non solo GREEN col codice corretto):

1. `test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca` — due
   congelate adiacenti A/B (cambio già presente, debito = 1), tetto
   dichiarato zero. Mutando via il clamp (uso diretto di `per_giorno`/
   `per_settimana` grezzi, come nello Step 3 del piano) il test va RED:
   `AssertionError: 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')` — le sole
   congelate bloccano il solver, esattamente ciò che ADR-018 vieta.

2. `test_adr018_clamp_impedisce_alla_libera_di_aggiungere_un_cambio` — la
   controprova che conta: stesso passato (debito = 1), libera con una
   **terza** sede C e **costretta** sul giorno 0 (indisponibile ovunque
   altro, via `ResourceUnavailability`). ⚠ La prima stesura di questo test
   lasciava la libera scegliere fra tutti i giorni e assert-ava `giorno != 0`:
   passava col clamp corretto, ma **passava anche con un salto mutato
   apposta** (`continue` quando le congelate sforano) — CP-SAT, senza un
   obiettivo che preferisca il giorno 0, trovava comunque una soluzione su
   un altro giorno per conto suo, e l'asserzione non discriminava nulla
   (verificato: la mutazione lasciava la suite verde). Corretto costringendo
   la libera sul giorno 0, cosa che trasforma la domanda in
   INFEASIBLE-contro-FEASIBLE: col clamp, INFEASIBLE (nessun modo di
   piazzare la libera sul giorno 0 senza sforare); con la mutazione
   "salto invece di clamp" applicata di nuovo, RED:
   `AssertionError: 'OPTIMAL' == 'INFEASIBLE'` — la libera resta
   indisturbata sul giorno 0, peggiorando la situazione.

**Scoperta collaterale, non in scope per questo task.** Scrivendo questi due
test ho trovato che il primo tentativo (senza `site_transition_slots = 0`
esplicito) andava INFEASIBLE per un motivo estraneo: `InstituteSettings`
non viene creato da `mini_school()`, quindi `ScheduleState.build` cade sul
default di modello `site_transition_slots = 1`, e `SiteTransitionBuilder` —
il builder che il brief mi vieta di toccare — risultava **attivo** sulle
due congelate. La sua guardia ADR-018 (`any_free(ctx, tocca)`) controlla se
*qualche* attività libera **potrebbe raggiungere** una delle due celle
(dominio, non occupazione reale), non se le attività effettivamente in
conflitto sono libere: dato che nella fixture c'è sempre un'attività libera
il cui dominio copre l'intera griglia (quindi anche quelle due celle), la
guardia risultava vera anche quando il conflitto reale era **interamente
fra due congelate**, e il vincolo veniva postato comunque — infattibile per
colpa del passato, lo stesso pattern ADR-018 che questo task corregge per
`MaxSiteChangesBuilder`. Non l'ho toccato (il brief lo vieta esplicitamente
per questo builder); ho isolato i miei test con `site_transition_slots = 0`
esplicito e segnalo la scoperta qui per il controller — è verosimilmente la
stessa domanda aperta di CLAUDE.md ("come si comporta un builder quando un
constraint mescola attività congelate già in violazione e attività
libere?"), mai esercitata finora perché il banco di prova (`solver_harness.py`)
non congela mai nulla.

### Correzione 3 (Ruling 29) — niente `test_sedi_sul_banco`, derivatori a `return 0`/`1`

Non scritto `test_sedi_sul_banco`: nota in testa a `tests/test_solver_sites.py`,
stessa forma dei Task 7/8. I due derivatori restituiscono `0`/`1` con
docstring che spiega la vacuità:

- `_derive_max_site_changes`: vacuo se il docente scelto ha meno di due sedi
  distinte fra le proprie attività (nessun cambio è strutturalmente
  possibile per lui, qualunque arrangiamento scelga il solver).
- `_derive_site_transition`: vacuo se `needed` risulta zero — sia perché
  nessuna coppia di attività con sedi diverse e chiave condivisa esiste nel
  testimone (`minimo is None`), sia perché la coppia più vicina trovata ha
  già distanza zero (`minimo == 0`, clampato). In entrambi i casi il builder
  esce subito (`if not needed: return`).

**Misura empirica sui cinque seed** (seed 1–5, replicando esattamente la
logica dei due derivatori):

```
max_site_changes:             [(1, 0), (2, 0), (3, 0), (4, 0), (5, 1)]
structural:site_transition:   [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]
```

`max_site_changes` è vacuo 4/5 (non vacuo solo al seed 5).
`structural:site_transition` è vacuo **5/5**. Ho esteso la misura ai seed
6–10 per capire se fosse un caso limite del range richiesto:

```
seed=1  n_con_sede=5  pairs_found=6  minimo=0     (vacuo)
seed=2  n_con_sede=2  pairs_found=0  minimo=None  (vacuo)
seed=3  n_con_sede=4  pairs_found=0  minimo=None  (vacuo)
seed=4  n_con_sede=10 pairs_found=20 minimo=0     (vacuo)
seed=5  n_con_sede=19 pairs_found=10 minimo=0     (vacuo)
seed=6  n_con_sede=11 pairs_found=6  minimo=0     (vacuo)
seed=7  n_con_sede=5  pairs_found=4  minimo=1     (NON vacuo)
seed=8  n_con_sede=12 pairs_found=14 minimo=0     (vacuo)
seed=9  n_con_sede=8  pairs_found=2  minimo=0     (vacuo)
seed=10 n_con_sede=7  pairs_found=0  minimo=None  (vacuo)
```

9/10 vacuo. **Questa è "troppo spesso vacuo"**, nel senso che il brief avverte.
La causa non è un difetto del mio codice: è intrinseca alla formula del piano
stesso (`_derive_site_transition` prende il **minimo** su *tutte* le coppie di
attività con sedi diverse che condividono una chiave e cadono nello stesso
giorno — quando `pairs_found` è anche solo moderato, per un argomento da
"paradosso del compleanno" il minimo cade quasi sempre su distanza zero,
perché `_try_place` piazza le attività a caso senza mai cercare di
distanziare quelle con sede diversa). Non ho ridisegnato il derivatore di mia
iniziativa (fuori dal perimetro delle quattro correzioni, e il brief chiede
di seguire esattamente questa formula per Ruling 29): la famiglia
`structural:site_transition` **è comunque testata**, ma dai test mirati
(`test_site_transition_impone_le_fasce_libere` in `tests/test_solver_sites.py`,
verificato mordere sotto mutazione — vedi sotto), non dal banco di prova a
testimone. Segnalo la vacuità sistematica come osservazione per il
controller: se si vuole rafforzare la copertura del testimone su questa
famiglia, la formula di derivazione va ripensata (es. scegliere
esplicitamente la coppia più vicina fra quelle a distanza > 0, invece del
minimo assoluto), ma è una decisione di progetto che non mi competeva
prendere qui.

### Correzione 4 (Ruling 30/2) — la scuola del testimone cambia forma

Sedi aggiunte a `_school`/`_make_activities`. `rng.random() < 0.5` sposta il
flusso casuale per **tutti** gli undici derivatori esistenti, come previsto.

**Suite intera, prima/dopo:**

- **Prima** (baseline, verificata con `git stash`): `282 passed, 2 skipped`
  a livello di suite; nel solo `tests/test_solver_witness.py`:
  `55 passed, 2 skipped` (11 famiglie × 5 semi + 2 test fissi = 57), skip su
  `arrival_departure-2`, `arrival_departure-4`.
- **Dopo**: `283 passed, 16 skipped` a livello di suite (+1 collected non
  vuoto: `test_i_builder_tradotti_finora` continua a passare, aggiornato);
  nel solo `test_solver_witness.py`: `52 passed, 15 skipped` (13 famiglie ×
  5 + 2 = 67). Skip completi:

  ```
  arrival_departure-2, arrival_departure-3, arrival_departure-4  (era 2/5, ora 3/5)
  max_half_days-3                                                (nuovo skip)
  max_presence-3                                                 (nuovo skip)
  same_day_incompatible-5                                        (nuovo skip)
  max_site_changes-1, -2, -3, -4                                 (famiglia nuova, 4/5 vacui)
  structural:site_transition-1, -2, -3, -4, -5                   (famiglia nuova, 5/5 vacui)
  ```

  Nessuna famiglia preesistente **fallisce**: solo alcuni seed che prima
  producevano una derivazione non vacua ora la producono vacua (per lo
  spostamento del flusso rng), esattamente il comportamento atteso e non una
  regressione. Nessun test è diventato rosso.

**Registrato anche un effetto non previsto dal brief**: aggiungere le due
chiavi nuove ha reso `tests/test_solver_registry.py::test_i_builder_tradotti_finora`
rosso (fissa l'insieme esatto delle chiavi registrate) — aggiornato con le
due nuove chiavi, stessa manutenzione già fatta nei Task 7/8 per il decimo/
undicesimo builder.

**Uno skip in più fuori da `test_solver_witness.py`**: il totale suite (16
skip) non è tutto nel banco a testimone — `tests/test_solver_time_counting.py`
richiama `run_family` direttamente (una duplicazione di copertura risalente
al Task 6/7, prima che si stabilisse la convenzione "niente `test_X_sul_banco`")
per `MAX_HOURS` e `MAX_HALF_DAYS` sugli stessi cinque seed. Lo spostamento
del flusso rng fa scattare lo stesso skip che in `test_solver_witness.py` si
vede su `max_half_days-3`: `MAX_HALF_DAYS: derivazione vacua per il seed 3`.
Non è una famiglia nuova né un difetto — è lo stesso effetto della
Correzione 4 (rng spostato) che si manifesta in un secondo punto della
suite. 13 skip nuovi in `test_solver_witness.py` (15 − 2 baseline) + 1 skip
nuovo in `test_solver_time_counting.py` = 14 skip in più a livello di suite
(16 − 2), che torna esattamente col delta osservato.

**Suite lanciata più volte** (CP-SAT non deterministico): 4 run completi
della suite intera, tutti `283 passed, 16 skipped`; 5 run di
`tests/test_solver_sites.py tests/test_solver_witness.py`, tutti
`57 passed, 15 skipped`. Nessuna intermittenza osservata.

## Le prove RED verbatim

**Correzione 1** (formulazione originale del piano contro
`test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo`):

```
FAILED tests/test_solver_sites.py::test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo
AssertionError: {'attivita': 3, 'libere': 3, 'variabili': 22, 'constraint': 23, ...}
assert 'OPTIMAL' == 'INFEASIBLE'
```

**Correzione 2, test 1** (clamp rimosso, uso diretto di `per_giorno`/`per_settimana`):

```
FAILED tests/test_solver_sites.py::test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca
AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 242, 'constraint': 222, ...}
assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
```

**Correzione 2, test 2** (clamp → salto):

```
FAILED tests/test_solver_sites.py::test_adr018_clamp_impedisce_alla_libera_di_aggiungere_un_cambio
AssertionError: {'attivita': 3, 'libere': 1, 'variabili': 548, 'constraint': 551, ...}
assert 'OPTIMAL' == 'INFEASIBLE'
```

**`test_site_transition_impone_le_fasce_libere`** (SiteTransitionBuilder
disattivato, `build()` reso no-op), rilanciato 5 volte per escludere rumore:

```
FAILED tests/test_solver_sites.py::test_site_transition_impone_le_fasce_libere
AssertionError: assert (1 - 1) >= 2
 +  where 1 = abs((5 - 4))
```

(fallito in tutti i 5 run — non intermittente).

**`test_max_site_changes_limita_i_cambi`** — verificato che **non morde**
(`MaxSiteChangesBuilder.post` disattivato del tutto): `1 passed`. Documentato
nel suo docstring, appaiato a `test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo`
che invece morde.

Dopo ogni mutazione, `domain/solver/builders/time_sites.py` è stato
ripristinato bit-per-bit (diff vuoto) prima di procedere.

## Numero di variabili e constraint

Misurato su un testimone non banale (seed 5 del banco: 30 attività, griglia
5 giorni × 6 fasce, 19 attività con sede su 2 sedi):

| Configurazione | variabili | constraint |
|---|---|---|
| Baseline (nessun vincolo di sede, `site_transition_slots=0`, nessuna riga `MAX_SITE_CHANGES`) | 778 | 348 |
| `structural:site_transition` da solo, al **default di campo** `needed=1` (nessuna riga esplicita) | 1426 | 1536 |
| `MAX_SITE_CHANGES` da solo (`site_transition_slots=0`) | 1198 | 780 |
| Entrambi, coi valori derivati dal testimone (per questo seed `site_transition` risulta vacuo, `needed=0`) | 1198 | 780 |

`SiteTransitionBuilder` al suo caso più caro (`needed=1`, l'intera griglia
in gioco) quasi **quadruplica** i constraint rispetto alla baseline
(348 → 1536): è la costruzione più cara vista finora nello spike, confermando
l'avvertenza del brief — cicla su tutte le chiavi × giorni × coppie di fasce
× coppie di sedi. `MAX_SITE_CHANGES` da solo aggiunge 420 variabili e 432
constraint su questa istanza (cicla su tutte le coppie `(s,t)` × sedi² ×
giorni, senza il filtro `t - s - 1 >= needed` che invece limita
`SiteTransitionBuilder` alle coppie vicine). È un'informazione utile per il
Task 17 (il Fermi intero): con più di due sedi il costo di
`SiteTransitionBuilder` cresce come il quadrato del numero di sedi, e quello
di `MAX_SITE_CHANGES` altrettanto.

## Deviazioni dal piano

1. **Correzione 1** applicata: `_coppie_di_sede` richiede "nessuna sede nota
   in mezzo" invece di "tutto vuoto in mezzo".
2. **Correzione 2** applicata: `MaxSiteChangesBuilder` clampa il tetto sul
   debito delle sole congelate (`_frozen_site_changes`), non lo posta grezzo.
3. **Correzione 3** applicata: niente `test_sedi_sul_banco`; i due derivatori
   restituiscono `0`/`1`.
4. Il test `test_site_transition_impone_le_fasce_libere` e
   `test_max_site_changes_limita_i_cambi` sono rimasti come nel piano
   (spostati da un ipotetico `test_sedi_sul_banco` a `test_solver_sites.py`,
   dato che quel file non va scritto — erano già lì nel piano originale come
   parte dello stesso file).
5. **Aggiunto** un test non previsto dal piano,
   `test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo`,
   per difendere concretamente la Correzione 1 (richiesto dal brief: "avere
   il test che la difende").
6. **Aggiunti** due test ADR-018 non previsti dal piano (il piano non
   modellava ADR-018 affatto su questo builder), richiesti dalla Correzione 2.
7. **Scartato** un tentativo di test oracolo-level per la Correzione 1 (vedi
   commento in `test_solver_sites.py`): non discriminava il difetto, perché
   con più di un giorno disponibile il solver aggira l'adiacenza separando
   le attività di giornata, sia col builder giusto sia con quello sbagliato.
8. **`tests/test_solver_registry.py`** aggiornato (non elencato fra i file
   da toccare nel brief, ma conseguenza necessaria — stessa nota già fatta
   nei report dei Task 7/8).
9. In `SiteTransitionBuilder` ho sostituito il controllo scritto a mano
   `if not any(aid in ctx.free for aid in tocca): continue` con la primitiva
   già esistente `any_free(ctx, tocca)` da `domain.solver.residual` — stessa
   semantica, ma evita di reinventare a mano la regola dell'implicazione già
   incapsulata altrove (coerente col vincolo globale 5 del brief).

## Numero di variabili e constraint — riepilogo finale

Vedi tabella sopra. Riga di riepilogo della suite, verbatim (ultimo run):

```
283 passed, 16 skipped in 23.82s
```

## Dubbi che restano

1. **La scoperta collaterale su `SiteTransitionBuilder`** (Correzione 2): la
   sua guardia ADR-018 controlla il dominio ("qualche attività libera
   potrebbe raggiungere una di queste due celle"), non l'occupazione reale
   ("le attività che *causano* il conflitto sono libere"). In una fixture
   dove esiste sempre un'attività libera dal dominio pieno sulla stessa
   chiave, questo basta a far posare il vincolo anche quando il conflitto è
   interamente fra congelate — lo stesso pattern ADR-018 di cui questo task
   si occupa per `MaxSiteChangesBuilder`, ma non risolto perché il brief mi
   vieta esplicitamente di toccare quel builder. Segnalo per il controller.
2. **Il secondo caso della Correzione 1** (due attività di sede diversa sulla
   stessa fascia, capienza cumulativa > 1): raggiungibile ma non risolto,
   come richiesto. Se `MAX_SITE_CHANGES` viene mai usato su una risorsa a
   capienza cumulativa (fuori dal caso d'uso tipico docente/classe), il
   builder sotto-conta.
3. **La vacuità sistematica di `structural:site_transition`** sul banco di
   prova (9/10 seed): la famiglia resta testata (dai test mirati, verificati
   mordere sotto mutazione), ma il banco a testimone non la esercita quasi
   mai. Segnalata come osservazione, non risolta di iniziativa.
4. Non ho verificato il comportamento con **più di due sedi** (il banco ne
   crea sempre esattamente due): la stima di costo quadratico nel numero di
   sedi per il Task 17 è un'estrapolazione dalla struttura del ciclo
   (`sedi × sedi`), non una misura diretta.

---

## Giro di correzione 1

Baseline verificata prima di cominciare (`venv/bin/pytest -q`):

```
290 passed, 9 skipped in 25.32s
```

Albero pulito (`git status`) prima di ogni sonda; tutti gli script di misura
sono stati eseguiti fuori dal repo (scratchpad) o come file di test rimossi
subito dopo l'uso — nessuno resta nell'albero finale.

### 1. Riproduzione di Important 2 (prima di correggere)

`_derive_site_transition` misura la distanza fra le fasce **d'inizio**
(`abs(slot2 - slot) - 1`); il checker (`_site_sequence`) misura la distanza
fra le fasce **occupate**. Riprodotto con un file di test temporaneo che
chiama `run_family("structural:site_transition", seed)` per `seed` da 1 a
15, **codice in albero, nessuna mutazione**:

```
seed = 15

    @pytest.mark.parametrize("seed", range(1, 16))
    def test_repro(seed):
>       run_family("structural:site_transition", seed)

tests/test_zzz_repro_important2.py:10:
...
        prima = _hard(w.schedule, d.codes)
>       assert prima == set(), (
               ^^^^^^^^^^^^^^
            f"il testimone stesso viola {key} (seed {seed}): {sorted(prima)}")
E       AssertionError: il testimone stesso viola structural:site_transition (seed 15): [('site_transition', (1,), (1, 5), (('day', 2), ('gap_slots', 0), ('needed_slots', 1)))]

tests/solver_harness.py:290: AssertionError
=========================== short test summary info ============================
FAILED tests/test_zzz_repro_important2.py::test_repro[15] - AssertionError: i...
1 failed, 2 passed, 12 skipped in 2.04s
```

Esattamente il difetto descritto dalla review: l'attività 1 (durata 2, sede
1) copre le fasce 1 e 2; la vecchia formula calcola `3 - 1 - 1 = 1` sulle
fasce d'inizio e dichiara `needed = 1` sicuro, ma il checker vede la
sequenza `…sede1@2, sede2@3…` con `gap_slots = 0` — il testimone che il
derivatore ha appena costruito **viola se stesso**. Il file di test
temporaneo è stato rimosso subito dopo la riproduzione.

### 2. Cosa ho cambiato, e perché

**a) `tests/solver_harness.py` — `_distanza_sedi` (Important 2).** Nuova
funzione che calcola la distanza sulle fasce occupate, non sulle fasce
d'inizio: se `aid` precede `altro`, `slot2 - slot - duration_slots(aid)`;
altrimenti il simmetrico. Usata sia nel nuovo `_derive_site_transition` sia
nel suo helper `_coppie_sedi_vicine`.

**b) `domain/solver/builders/time_sites.py` — `SiteTransitionBuilder`
ripara la fascia condivisa (Important 1, Ruling 33).** Aggiunta una
famiglia di clausole `s == t`: per ogni `(chiave, giorno, fascia)` e ogni
coppia di sedi distinte che tocca davvero quella cella, `site_occupied(...,
s, sa).Not() OR site_occupied(..., s, sb).Not()`. Postata **prima** e
**indipendentemente** dal controllo `if not needed`, perché il checker vede
sempre `gap_slots = -1 < needed` per qualunque `needed >= 0`, anche zero.
`MaxSiteChangesBuilder` **non è stato toccato** per lo stesso difetto:
`_site_sequence` scorre `state.occupancy` (una `list`) in ordine di
inserimento, quindi sotto capienza cumulativa il *conteggio* dei cambi
dipende dall'ordine — un artefatto del checker, non una semantica ben
definita. Tradurlo nel builder significherebbe replicare l'artefatto.
Documentato per esteso nel docstring del modulo (già annotato anche in
CLAUDE.md, elenco "Ancora aperto", da prima di questo giro).

**c) `domain/solver/builders/time_sites.py` — `_sedi_raggiungibili` (Minor
2).** Filtro che restituisce, per una cella, solo le sedi di cui esiste
davvero un'attività il cui dominio la tocca (lettura di `ctx.by_cell`),
usato al posto della lista completa delle sedi nei cicli `sa`/`sb` di
entrambi i builder. Implementato perché a costo zero in leggibilità — ma
**misurato a effetto nullo sul Fermi** (vedi §5 sotto): non è stato
scartato, perché resta corretto e innocuo, solo la sua utilità pratica non è
quella che la review ipotizzava.

**d) `tests/solver_harness.py` — `_derive_max_site_changes` («segregato»,
Ruling 34) e `_derive_site_transition` («denso», Ruling 34).** Riscritti da
osservativi a costruttivi, seguendo la raccomandazione della review (§3):
il derivatore costruisce lo scenario invece di sperare che l'osservazione
casuale ne produca uno interessante. Nessuno dei due tocca
`_make_activities`: entrambi sovrascrivono le sedi **dopo** che il
testimone è già completo, sul proprio `Witness` — nessun altro derivatore
ne risente, perché ogni `run_family` costruisce il proprio testimone da
zero. Dettagli nei docstring aggiornati (vedi diff).

**e) `tests/test_solver_sites.py` — nuovo test.**
`test_site_transition_due_sedi_sulla_stessa_fascia_a_capienza_cumulativa`:
un'aula a `simultaneous_capacity = 2`, due attività di classi (e docenti)
diversi, griglia 1×1, sedi diverse, `site_transition_slots = 1`. Prima
della riparazione: `OPTIMAL` con un finding `site_transition` `HARD` mai
visto dal solver. Dopo: `INFEASIBLE` (è l'unica cella disponibile e la
clausola la vieta).

### 3. Prove RED, verbatim

**Il probe di Important 1 prima della riparazione** (stessa istanza del
test, builder pre-fix, script temporaneo fuori dal repo):

```
STATUS: OPTIMAL {'attivita': 2, 'libere': 2, 'variabili': 2, 'constraint': 2, 'secondi': 0.024}
PLACEMENTS: {1: (0, 0), 2: (0, 0)}
FINDINGS: [Finding(code='site_transition', message='Tempo insufficiente per il trasferimento di sede', severity=<Severity.HARD: 'hard'>, resources=(3,), activities=(1, 2), quantities={'day': 0, 'gap_slots': -1, 'needed_slots': 1}, weeks=(0, 1, 2, 3))]
```

Dopo la riparazione, stessa istanza:

```
STATUS: INFEASIBLE {'attivita': 2, 'libere': 2, 'variabili': 4, 'constraint': 6, 'secondi': 0.016}
PLACEMENTS: {}
```

**Il test nuovo, mutato per verificare che morda davvero** (rimossa solo
la clausola `s == t`, lasciando intatto il resto del builder):

```
    make_activity(env["subject"], teachers=[altro_docente],
                  classes=[altra_classe], rooms=[aula], site=b_site)

    soluzione = solve(env["schedule"], time_limit=30)
>   assert soluzione.status == "INFEASIBLE", soluzione.stats
E   AssertionError: {'attivita': 2, 'libere': 2, 'variabili': 2, 'constraint': 2, ...}
E   assert 'OPTIMAL' == 'INFEASIBLE'
E
E     - INFEASIBLE
E     + OPTIMAL
1 failed in 0.62s
```

Builder ripristinato bit-per-bit dopo la mutazione (diff verificato
identico all'originale prima di rilanciare la suite).

**Important 2, dopo la correzione**: `run_family` per tutti i seed 1-15,
codice in albero:

```
..s............                                                          [100%]
14 passed, 1 skipped in 4.35s
```

Nessun fallimento "il testimone stesso viola": la correzione chiude il
landmine.

### 4. Misura del potere vincolante reale (prima/dopo)

Stesso metodo della review: builder reso no-op (`return` in testa a
`build`/`post`), 15 seed, si conta MORDE (fallisce) / SKIP (derivazione
vacua) / verde-ma-inerte (passa nonostante il builder spento).

**`structural:site_transition`** (mutato: `SiteTransitionBuilder.build`
sostituito con un `return` secco):

| | MORDE | SKIP | verde-ma-inerte |
|---|---|---|---|
| **prima** (formulazione osservativa, `piano`) — dalla review | 1/15 | 13 | 1 |
| **dopo** (formulazione «denso», qui) — 6 esecuzioni consecutive | 12, 13, 14, 14, 14, 13 su 15 | 1 (sempre seed 3) | 0-2 |

Output verbatim di un'esecuzione (12/15):

```
SKIPPED [1] tests/solver_harness.py:283: structural:site_transition: derivazione vacua per il seed 3, nessuna condizione da violare in questo testimone
12 failed, 2 passed, 1 skipped, 15 deselected in 4.20s
```

**`T.MAX_SITE_CHANGES`** (mutato: `MaxSiteChangesBuilder.post` sostituito
con un `return` secco):

| | MORDE | SKIP | verde-ma-inerte |
|---|---|---|---|
| **prima** (formulazione osservativa, `piano`) — dalla review | 0/15 | 10 | 5 |
| **dopo** (formulazione «segregato», qui) — 4 esecuzioni consecutive | 10/15, stabile | 0 | 5 |

Output verbatim:

```
10 failed, 5 passed, 15 deselected in 4.49s
```

Ripetuto altre tre volte: identico (`10 failed, 5 passed`) tutte e tre le
volte — nessuna oscillazione osservata per questa famiglia, a differenza di
`structural:site_transition` che oscilla di 1-2 casi da un run all'altro
(CP-SAT non fissa il seed).

**Onestà sul numero**: la review aveva misurato 12/15 per «segregato» sulla
propria formulazione di riferimento (descritta, non fornita come codice).
La mia implementazione sceglie il docente **per numero totale di
attività**, non specificamente per predisposizione a produrre sedi
multiple, e si ferma a 10/15 stabile invece di 12/15. Resta comunque un
miglioramento netto e verificato rispetto allo 0/15 in albero — l'obiettivo
del giro (*"se non ottieni almeno un miglioramento netto ... dillo con i
numeri"*) è soddisfatto, ma non ho eguagliato esattamente il numero della
review. Non ho investigato oltre per restare dentro lo scopo del giro
(sostituire i derivatori, non ottimizzarli al massimo).

Builder ripristinati bit-per-bit dopo ogni misura (`diff` contro la copia
salvata, identico) prima di procedere.

### 5. Il costo — misura aggiuntiva sul Fermi (Minor 2)

Non richiesta esplicitamente per il giro, ma necessaria per giudicare se il
filtro (punto 4 del compito) vale la pena. Fermi intero, solo
`structural:site_transition` attivo (nessuna riga `MAX_SITE_CHANGES`),
`site_transition_slots = 1`:

| scenario | variabili | constraint | esito |
|---|---|---|---|
| 2 sedi, 100% attività, **builder pre-Task-9-giro-1** (baseline, per confronto) | 9736 | 4008 | UNKNOWN a 60s (timeout, non regressione mia — stesso timeout col codice in albero pre-fix) |
| 2 sedi, 100% attività, **con la riparazione** | 9736 | 5604 | UNKNOWN a 60s |
| 2 sedi, 50% attività, con la riparazione, **con** `_sedi_raggiungibili` | 9736 | 5604 | OPTIMAL, 0.88s |
| 2 sedi, 50% attività, con la riparazione, **senza** il filtro (mutato) | 9736 | 5604 | OPTIMAL, 0.85s |
| 4 sedi, 100% attività, con la riparazione, **con** il filtro | 11332 | 21830 | UNKNOWN a 15s |
| 4 sedi, 100% attività, con la riparazione, **senza** il filtro (mutato) | 11332 | 21830 | UNKNOWN a 15s |

**Il filtro (Minor 2) è corretto ma misurato a effetto nullo sul Fermi**: a
2 e a 4 sedi, con e senza `_sedi_raggiungibili`, il conteggio dei constraint
è **identico**. La ragione è strutturale: sul Fermi, senza indisponibilità
o restrizioni di griglia aggiuntive sulle chiavi usate in questa misura,
`ctx.by_cell` per ogni chiave contiene già rappresentanti di quasi tutte le
sedi in quasi ogni cella — non c'è nulla da filtrare. L'ho lasciato nel
codice comunque (punto 4 del compito: "fallo se è a costo zero in
leggibilità"; lo è, e non ha controindicazioni), ma il beneficio pratico
resta da dimostrare su dati con domini davvero ristretti per sede
(indisponibilità, griglia, congelate) — non il caso qui.

**La riparazione dell'Important 1 aumenta il costo strutturalmente**, e
questo è indipendente dal filtro: la clausola `s == t` è una famiglia
intera di vincoli in più (una per chiave × giorno × fascia × coppia di
sedi), non un'ottimizzazione. Il baseline pre-riparazione andava da 4008 a
12254 constraint (2→4 sedi, dati della review); con la riparazione va da
5604 a 21830 — più caro, come atteso da un builder più corretto ma con più
da dire. Il caso "tutto acceso" (con anche `MAX_SITE_CHANGES`) misurato
dall'implementatore/review era diverso da questi scenari isolati e
risolveva in <1s: non l'ho rimisurato in questo giro, perché il tempo del
Task 17 dipenderà anche da quante chiavi hanno davvero attività a più
sedi, che qui è sintetico e non rappresentativo del Fermi reale (dove le
aule non sono mai state inserite — `NBSALLES = 0`, nota già in CLAUDE.md).

### 6. Prima/dopo di passed/skipped

```
prima (baseline dichiarata e riverificata):  290 passed,  9 skipped
dopo (questo giro, 7+ esecuzioni consecutive): 297 passed, 3 skipped
```

Delta: +7 passed (6 seed che erano skip nelle due famiglie ora mordono/sono
verdi, +1 test nuovo), skip -6 (dei 9 skip originali, i 2 di
`arrival_departure` sono invariati — non toccati da questo giro — e dei 7
appartenenti alle due famiglie sedi ne restano 1, seed 3 di
`structural:site_transition`).

Skip finali, verbatim (`venv/bin/pytest -q -rs`):

```
SKIPPED arrival_departure: derivazione vacua per il seed 2
SKIPPED arrival_departure: derivazione vacua per il seed 4
SKIPPED structural:site_transition: derivazione vacua per il seed 3
```

`max_site_changes` non ha più skip su nessuno dei cinque seed del banco:
tutti e cinque ora derivano una riga non vacua con la formulazione
«segregato». `structural:site_transition` scende da 4 skip su 5 a 1 su 5.

Suite completa lanciata **7 volte consecutive** dopo tutte le modifiche:
sempre `297 passed, 3 skipped`, nessuna intermittenza. `tests/test_solver_
witness.py` e `tests/test_solver_sites.py` lanciati separatamente più
volte con lo stesso esito stabile.

### 7. Deviazioni dal compito

Nessuna deviazione sostanziale. Un chiarimento: il compito non specificava
se la clausola `s == t` dovesse essere postata anche a `needed = 0` (la
sonda della review usava `needed = 1`). L'ho resa **indipendente da
`needed`**, perché il checker (`SiteTransitionChecker`) non esenta mai il
caso `gap_slots = -1` — anche a soglia zero è sempre `< 0`. Verificato che
non introduce regressioni (suite verde, test mirati verdi) e che è più
fedele al checker (esatto anche in quel caso limite) invece di lasciare un
buco residuo identico a quello appena chiuso, solo spostato a `needed = 0`.

### 8. Dubbi che restano

1. **Il numero 10/15 contro il 12/15 della review per «segregato»**: non ho
   investigato la differenza (probabilmente la scelta del docente — "più
   attività" invece di un criterio più mirato alla varietà di sedi). Non
   blocca il giro (miglioramento netto verificato), ma lascia margine.
2. **Il costo di `SiteTransitionBuilder` dopo la riparazione è più alto**,
   non più basso: la clausola `s == t` è correttezza, non ottimizzazione, e
   il filtro (Minor 2) non compensa sul Fermi. Il Task 17 dovrà misurare il
   costo reale con dati che abbiano davvero domini ristretti per sede,
   perché lo scenario sintetico usato qui (nessuna indisponibilità, nessuna
   restrizione di griglia oltre quelle base) non è rappresentativo.
3. **`MaxSiteChangesBuilder` resta con lo scarto della fascia condivisa**,
   deliberatamente, in attesa di una decisione in `domain/analysis` su cosa
   significhi «cambio di sede» quando due sedi coesistono nella stessa
   fascia (voce già in CLAUDE.md, "Ancora aperto").
4. **Minor 1** (la guardia `any_free` più grossolana del dovuto) resta
   aperta come deciso dalla Ruling 36: non è stata toccata in questo giro.
