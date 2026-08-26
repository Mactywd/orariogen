# Task 9 — Le sedi: `MAX_SITE_CHANGES` e `structural:site_transition` — brief

Implementi il **Task 9** del piano
`docs/superpowers/plans/2026-08-24-modello-hard-completo.md` (righe 2099–2406).
Leggi quella sezione per intero prima di cominciare. Il codice degli Step è
completo, **ma questo task è quello in cui il piano sbaglia di più**: sotto
trovi quattro correzioni obbligatorie, già decise dal controller. Applicale.

Lavora in `/home/mattia/coding/scuola/orariogen/.claude/worktrees/modello-hard-completo`
(worktree git, branch `worktree-modello-hard-completo`). Il venv è
`venv/bin/python` e `venv/bin/pytest`. Non uscire dal worktree.

## Contesto

`orariogen` è un generatore di orari scolastici. `domain/analysis/` contiene i
**checker**, che sono **l'autorità** su cosa significhi ogni vincolo.
`domain/solver/` li traduce in CP-SAT. Il criterio di riuscita è un **oracolo
differenziale**: una soluzione del solver, riscritta nei `Placement` e riletta
da `check_schedule`, non deve produrre alcun finding `HARD` **nuovo**.

Otto task sono chiusi. Le astrazioni che ti servono esistono già:
`domain/solver/vocabulary.py` (per te: `site_occupied(key, day, slot, site_id,
signature=None)` e `occupied`), `domain/solver/residual.py` (ADR-018:
`frozen_occupies`, `any_free`), `domain/solver/builders/base.py`
(`ResourceBuilder`, che fa già il ciclo sulle firme di settimana e la
deduplicazione). Guarda `domain/solver/builders/time_presence.py` come modello:
è il file più curato del pacchetto, e contiene i due precedenti diretti delle
correzioni che devi fare.

## Correzione 1 — ⚠ il piano dichiara un conservativo che non ha (Ruling 27)

**Leggi prima i due checker**, non fidarti di questo brief:
`domain/analysis/checkers/sites.py` e la funzione `_site_sequence` +
`MaxSiteChangesChecker` in `domain/analysis/checkers/time_constraints.py`
(intorno alla riga 153).

Il piano apre il Task 9 con «Il conservativo numero due»: i checker guardano le
coppie **consecutive**, il builder guarda **tutte** le coppie, quindi «più
stretto, mai più largo». Per `SiteTransitionBuilder` è vero. Per
`MaxSiteChangesBuilder` **è falso**, e la ragione sta in cosa significa
«consecutive».

`_site_sequence` scorre le fasce occupate e appende **solo** le attività con
sede nota (`if site is not None`). Quindi «consecutive» vuol dire consecutive
nella **sottosequenza delle occupazioni con sede** — un'attività **senza sede**
interposta **non spezza l'adiacenza**.

Il `_coppie_di_sede` del piano invece pretende `occupied(m).Not()` per ogni `m`
fra `s` e `t`, cioè **tutto vuoto in mezzo**. Con Centrale alla fascia 0,
un'attività senza sede alla fascia 1 e Succursale alla fascia 2: il checker vede
`[Centrale, Succursale]` e conta **un cambio**; il builder non trova la coppia,
non forza il letterale, e **non conta niente**. È un *under-count*: il solver
accetta un orario che il checker boccia, cioè un finding `HARD` **nuovo**, cioè
il criterio di riuscita rotto. E non è teorico su questo banco — il Task 9 dà
una sede a **metà** delle attività, quindi le senza-sede interposte ci sono per
costruzione.

**Cosa devi fare, in quest'ordine:**

1. **Prima riproduci il difetto** con la formulazione del piano: costruisci
   l'istanza a tre fasce (sede A / senza sede / sede B), applica la soluzione e
   fai vedere con `check_schedule` che nasce un finding `max_site_changes` che
   il solver non ha visto. Incolla l'output nel report. Serve a due cose: sapere
   che la correzione è necessaria, e avere il test che la difende.
2. **Poi correggi**: la condizione «in mezzo» dev'essere **«nessuna occupazione
   con sede in mezzo»**, non «nessuna occupazione». Con quella, la coppia
   `(s, t)` con `sa != sb` diventa *esattamente* l'adiacenza nella
   sottosequenza del checker.
3. **Poi verifica la direzione** su istanze pulite: il builder non deve essere
   diventato più largo da nessun'altra parte.

⚠ Un secondo caso, che devi **verificare e documentare** (non necessariamente
risolvere): il checker appende una voce per **ogni** attività che occupa una
fascia, quindi due attività con sedi diverse sulla **stessa** fascia della
stessa chiave contano come un cambio. La costruzione a coppie `s < t` non può
esprimerlo. Guarda se è raggiungibile (di norma sarebbe già una violazione di
`structural:occupation`, ma le chiavi con capienza cumulativa potrebbero
ammetterlo) e scrivi nel report cosa hai trovato: se è irraggiungibile, dillo e
documentalo nel docstring; se è raggiungibile, è un'osservazione da portare al
controller, non da risolvere di tua iniziativa.

## Correzione 2 — ADR-018 manca del tutto in `MaxSiteChangesBuilder` (Ruling 28)

Il builder del piano posta `sum(cambi) <= per_giorno` e
`sum(tutti) <= per_settimana` sul **parametro grezzo**. Se le sole attività
congelate producono già più cambi del tetto, il modello diventa `INFEASIBLE`
per colpa del passato — esattamente ciò che ADR-018 vieta.

I `cambi` sono **variabili derivate**, non termini separabili, quindi non è un
caso di `residual_cap`: vale lo stesso schema di `MaxGapBuilder` e
`MaxPresenceBuilder` nello stesso pacchetto — un helper `_frozen_site_changes`
che calcola a build time i cambi indotti dalle **sole** congelate (celle fisse,
`ctx.by_cell` filtrato su `aid not in ctx.free` e, se `rep` non è `None`,
`aid in ctx.states[rep].activities`), e un **clamp** `max(tetto, cambi_congelati)`.

⚠ **Clamp, non salto.** Su questo piano il `continue` è stato provato due volte
ed è stato sbagliato entrambe (review Task 6 Important 2, e Ruling 23 sul Task
8): saltare il vincolo lascia le libere **peggiorare** la situazione, e poiché i
finding portano le quantità (`changes`) fra le `quantities` di `Finding.key`,
una violazione peggiorata è una violazione **nuova** per l'oracolo differenziale.
Leggi il docstring di `MaxPresenceBuilder`, che spiega l'argomento per esteso.

Servono **due test**: uno che dimostri che le congelate sole non bloccano il
solver, e uno che dimostri che il clamp **non è un salto** (una libera non può
peggiorare oltre il debito già contratto). Il secondo è quello che conta.

⚠ `SiteTransitionBuilder` invece ADR-018 ce l'ha già, nella forma della regola
dell'implicazione (`if not any(aid in ctx.free for aid in tocca): continue`):
**non toccarlo**.

## Correzione 3 — niente `test_sedi_sul_banco`, e i derivatori dichiarino la vacuità (Ruling 29)

- **Non scrivere `test_sedi_sul_banco`** (Ruling 16): `test_famiglia` in
  `tests/test_solver_witness.py` è già parametrizzato su
  `sorted(DERIVERS) × [1..5]`, e i casi delle due famiglie esistono in
  automatico appena registri i derivatori. Metti in testa al modulo di test la
  nota che lo dice, come fanno i file dei Task 7 e 8.
- **I due derivatori devono `return 0` / `return 1`** con una docstring che dice
  quando sono vacui e perché — leggi gli altri undici in
  `tests/solver_harness.py` e segui la loro convenzione. ⚠ Per
  `_derive_site_transition` la vacuità è netta: quando `minimo` resta `None` il
  derivatore scrive `site_transition_slots = 0`, e con `needed = 0` il builder
  esce subito (`if not needed: return`) — famiglia completamente vacua, quindi
  `return 0`.
- ⚠ Misura **empiricamente** quanto spesso ciascun derivatore si dichiara vacuo
  sui cinque seed, e scrivilo nel report. Troppo spesso vacuo = famiglia che non
  testa niente; mai vacuo quando dovrebbe = casi verdi che non hanno testato
  nulla. Entrambi i difetti sono già costati giri di correzione su questo piano.

## Correzione 4 — la scuola del testimone cambia sotto tutti gli altri (Ruling 30 / Ruling 2)

Questo è **il task più rischioso del piano**: aggiungi le sedi a `_school` e
l'assegnazione di sede in `_make_activities`, cioè cambi la forma del testimone
sotto **undici derivatori già scritti**.

⚠ In più, `rng.random() < 0.5` **consuma numeri casuali**, quindi sposta l'intero
flusso del generatore: ogni derivatore esistente vedrà un testimone diverso a
parità di seed, e **l'insieme dei `pytest.skip` per vacuità cambierà**. Non è una
regressione, è atteso. Ciò che **non** deve cambiare è il verde della suite.

Quindi: lancia la **suite intera**, non solo i tuoi file, e lanciala **più
volte**. Se qualcosa diventa rosso, non è un caso: è un derivatore che sotto la
nuova forma del testimone non vale più, e va capito prima di proseguire.

Se ti trovi a dover cambiare il numero di skip, riportalo nel report con il
prima e il dopo.

## Vincoli globali del piano

1. I test si lanciano con `venv/bin/pytest`.
2. La suite non deve **mai** diventare rossa né **rimpicciolire**. Baseline
   attuale: **282 passed, 2 skipped** — verificala tu prima di cominciare. Il
   numero atteso scritto nel piano (262) è stantìo.
3. Commenti e docstring in **italiano**, identificatori in **inglese**. I nomi
   di variabile locale in italiano sono la convenzione già stabilita in questi
   file: seguila.
4. `domain/analysis/` non deve **mai** importare `ortools`.
5. Nessun builder reinventa una primitiva del vocabolario né calcola a mano un
   residuo separabile. (Il clamp su variabili derivate **non** ricade in questo
   divieto: è il caso previsto dal docstring di `frozen_occupies`.)
6. Ogni traduzione va derivata **leggendo il checker**. Su questo piano quattro
   difetti veri sono nati esattamente dal non farlo, e uno di essi è la
   Correzione 1 qui sopra.
7. `AddMaxEquality`/`AddMinEquality` con una lista vuota non è valido.
8. Le chiavi del registro non cambiano mai.
9. **Un solo commit** per il task, con il trailer
   `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## ⚠ Due avvertenze operative

**CP-SAT qui è non deterministico**: `domain/solver/model.py` non fissa né
`random_seed` né `num_search_workers`. Se un test fallisce a intermittenza **non
è rumore, è un builder troppo lasco** — è una Ruling già presa su questo piano,
dopo che un'intermittenza scambiata per rumore si è rivelata un difetto vero.
Rilancia i file mirati e `tests/test_solver_witness.py` almeno cinque volte.

**Attenzione al costo del modello**: `MaxSiteChangesBuilder` cicla su tutte le
coppie `(s, t)` × sedi² × giorni, e `SiteTransitionBuilder` su tutte le chiavi ×
giorni × coppie. È la costruzione più cara introdotta finora. Misura il numero di
variabili e constraint su un'istanza non banale e riportalo nel report: se
esplode, è un'informazione che serve al Task 17, che misura il Fermi intero.

## Metodo

Segui gli Step nell'ordine: prima i test che falliscono, poi la verifica che
falliscano **per la ragione giusta**, poi i builder, poi i derivatori, poi la
suite intera, poi il commit.

Per ogni test che scrivi, **fallo fallire deliberatamente** (mutando il builder o
rimettendo il difetto) e verifica che il fallimento sia quello atteso. Un test
che passerebbe anche col builder assente non dimostra niente: se ne scrivi uno
così, dillo nel report e appaialo a una controprova che invece morde.

Su questo piano vale una regola: **riproduci, non argomentare**. I difetti veri
sono sempre stati dimostrati con un'istanza sonda che gira, e le obiezioni solo
argomentate si sono rivelate false almeno tre volte.

## Cosa consegnare

Un rapporto in `.superpowers/sdd/2026-08-24-modello-hard-completo/task-9-report.md`
con: cosa hai implementato; **la riproduzione del difetto della Correzione 1**
con l'output incollato; le deviazioni dal piano e il loro perché; le prove RED
**verbatim** (incolla l'output di pytest, non parafrasarlo); la misura di
vacuità dei due derivatori sui cinque seed; il numero di variabili e constraint;
il prima/dopo degli skip della suite; la riga di riepilogo finale, verbatim; e i
dubbi che ti restano. Riporta l'essenziale anche nella risposta finale.
