# Task 10 — lo scheletro di materia, `SAME_HALF_DAY` e `TWO_DAYS`

Sei l'implementatore del Task 10 del piano
`docs/superpowers/plans/2026-08-24-modello-hard-completo.md` (righe 2407–2708).
Lavori nel worktree `.claude/worktrees/modello-hard-completo`. **Non uscire dal
worktree.** Il progetto è italiano nei commenti e nella documentazione, inglese
negli identificatori.

Leggi la sezione del piano. **Ma il piano ha tre difetti già misurati**, elencati
qui sotto: dove questo brief contraddice il piano, **vince il brief**.

## Cosa fa il task

1. `SubjectBuilder` in `domain/solver/builders/base.py` — lo scheletro dei
   vincoli sull'asse Relazione, con ciclo per firma di settimana e
   deduplicazione, gemello di `ResourceBuilder` che è già lì.
2. `vocab.subject_literals(...)` in `domain/solver/vocabulary.py`, estratto da
   `subject_bucket` e usato da entrambi.
3. `domain/solver/builders/subject_buckets.py` riscritto: `SameDayBuilder`
   (esistente) sul nuovo scheletro, più `SameHalfDayBuilder` e `TwoDaysBuilder`.
4. Due derivatori nuovi in `tests/solver_harness.py`.
5. `tests/test_solver_subject_buckets.py`.

Prima di scrivere qualunque riga: **leggi
`domain/analysis/checkers/subject_constraints.py`**, in particolare
`_BucketIncompatible.violations` e `TwoDaysChecker.violations`. La traduzione si
deriva dal checker, non dal ricordo di cosa faccia il vincolo. Su questo branch
la stessa svista è già costata tre volte.

## Difetto 1 del piano — ADR-018 non è trattato (il più importante)

`SameDayBuilder` **oggi** produce `INFEASIBLE` su input sporco. Misurato con due
sonde, entrambe su `mini_school()`:

- due attività **congelate** della stessa materia nello stesso giorno (già in
  violazione) più una libera altrove → `INFEASIBLE`;
- A ≠ B, una congelata per materia nello stesso giorno, più una libera →
  `INFEASIBLE`.

ADR-018 (`docs/decisioni.md`) dice il contrario, testualmente: *«Il solver non è
mai INFEASIBLE per colpa di una violazione preesistente: al più non può
aggiungere nulla lì.»*

La guardia esistente `any(aid in ctx.free for aid, _ in a)` **non è** un
trattamento ADR-018: risponde a «c'è qualcosa da decidere?», non a «di quanto il
passato ha già consumato il tetto?». Il piano la sposta perfino dal livello
**secchio** al livello **riga** (il gate su `coinvolte` in
`SubjectBuilder.build`), il che allarga il difetto.

Il gate di riga **va tenuto** — serve a `test_il_vincolo_non_si_posta_se_nulla_e_libero`
e alla regola dell'implicazione (`residual.any_free`) — ma **non basta**.

### La regola esatta, da implementare così

**Caso A = B** (il dominante nei dati EDT: non due ore della stessa materia
nello stesso giorno). Il caso è **separabile**, quindi `residual_cap` di
`domain/solver/residual.py` è esatto:

- termini: `(1, aid, lit)` per ogni `(aid, lit)` di
  `v.subject_literals(keys, subject_a_id, KIND, bucket, signature=rep)`;
- `free, cap = residual_cap(ctx, termini, 1)`;
- posta `sum(lit for _, lit in free) <= cap`.

Il checker emette `count=len(la)` fra le `quantities`, e le `quantities` sono
dentro `Finding.key` (`domain/analysis/findings.py`): un'aggiunta libera a un
secchio già violato è un finding **nuovo**, non lo stesso di prima. Quindi
`cap = 0` è il valore giusto, non un eccesso di zelo.

Tieni la guardia di ridondanza che il codice ha già, adattata: se `cap >= 1` e
le attività **distinte** fra i termini liberi sono al più una, il vincolo è
implicato da `AddExactlyOne` e non va postato. (Una sola attività può
contribuire più letterali allo stesso secchio, quando ha più celle candidate lì:
è per questo che si contano le attività, non i letterali.)

**Caso A ≠ B**, e **`TWO_DAYS`** che ha la stessa forma su due secchi
consecutivi. Qui il residuo **non** è separabile — sono indicatori derivati — e
la regola meccanica `max(0, 1 - fa - fb)` sarebbe **troppo stretta**. Il checker
emette il finding solo `if la and lb`: più occorrenze di A in un secchio dove B
è assente non creano e non peggiorano nulla.

Siano `fa` e `fb` due costanti note a build time — «una attività **congelata**
di A (risp. B) abita quel secchio» — calcolabili da `subject_literals`
guardando `aid not in ctx.free`. Quattro rami:

| `fa` | `fb` | vincolo da postare |
|---|---|---|
| 0 | 0 | `ha + hb <= 1` |
| 1 | 0 | `hb == 0` — le libere di A restano **libere** |
| 0 | 1 | `ha == 0` |
| 1 | 1 | azzera uno per uno i letterali **liberi** di A e di B in quel secchio |

dove `ha`/`hb` sono `v.subject_bucket(...)`. Nel ramo `fa=0, fb=0` gli
indicatori pieni **coincidono** con quelli sulle sole libere, perché nessuna
congelata contribuisce a quel secchio: puoi usare `subject_bucket` direttamente,
non serve una variante `free_only`.

Il quarto ramo serve perché il secchio è **già** violato e ogni aggiunta libera
ingrossa la tupla `activities`, che sta dentro `Finding.key`.

⚠ Il quarto ramo **può** rendere il modello infattibile se una libera non ha
altro posto dove andare. È **voluto**: è la stessa proprietà di `residual_cap`
clampato a zero, ed è testualmente ciò che ADR-018 concede. Scrivilo nel
docstring così nessuno lo rilitiga.

Per `TWO_DAYS` la tabella è identica con i secchi `("day", d)` per A e
`("day", d+1)` per B. Vale anche con **A = B** (il checker confronta `a_days[d]`
con `b_days[d+1]`, che sono lo stesso insieme letto su giorni diversi): non
trattare `TWO_DAYS` con A = B come il caso `_BucketIncompatible` A = B — sono
due secchi distinti, quindi la tabella a quattro rami è quella giusta.

### I test ADR-018 richiesti (uno per ramo)

Nuovi, in `tests/test_solver_subject_buckets.py` (o in
`tests/test_solver_same_day.py` per quelli su `SAME_DAY`):

1. A = B, due congelate nello stesso giorno + una libera → **non** `INFEASIBLE`,
   e la libera **non** finisce in quel giorno.
2. A = B, una congelata + una libera → la libera evita quel giorno (già coperto
   in parte: verifica e non duplicare).
3. A ≠ B, entrambe congelate nello stesso giorno + una libera di A → **non**
   `INFEASIBLE`, e la libera di A **non** finisce in quel giorno.
4. A ≠ B, solo A congelata, più una libera di A e una libera di B → la libera di
   **B** evita il giorno, la libera di **A** non è vincolata (esibisci una
   soluzione in cui ci sta, o almeno verifica che il modello non la vieti).
   Questo è il ramo che distingue la regola giusta da quella meccanica: senza
   questo test, `max(0, 1 - fa - fb)` passerebbe.

`tests/analysis_helpers.py` ha `place(schedule, activity, day=, slot=)` e
`make_activity(..., immobility="fixed")`: è così che si congela.

## Difetto 2 del piano — i due derivatori sarebbero **skip permanenti**

Entrambi i derivatori del piano finiscono con un `return` nudo dentro il ciclo e
non hanno `return` finale: restituiscono `None`, e `run_family` fa
`if not potere: pytest.skip(...)`. Le due famiglie nuove sarebbero dieci test
**sempre saltati** — verdi in apparenza, zero copertura.

E anche col valore di ritorno corretto restano vacui:

- `_derive_same_half_day` non impone **almeno due occorrenze**. Sotto due, il
  vincolo è soddisfatto per costruzione e non violabile.
- `_derive_two_days` non impone che **entrambe** le materie compaiano davvero
  sulla classe: con `defaultdict(set)`, una materia assente dà `giorni` vuoto,
  `not any(...)` è banalmente vero, e nasce una riga che nessun piazzamento può
  violare.

**Scrivili sulla forma di `_derive_same_day`** (già in `tests/solver_harness.py`,
riga ~433): scorre **tutte** le coppie (classe, materia), accumula invece di
fermarsi alla prima, dichiara le condizioni di vacuità nella docstring, e
`return creata`.

Per `_derive_two_days`, oltre alla guardia «entrambe presenti», considera anche
che serve almeno un giorno con un successore (`days_per_cycle >= 2`).

## Difetto 3 del piano — i numeri di test sono vecchi

Il piano dice «274 passed». La baseline reale del branch è **297 passed,
3 skipped** (`arrival_departure` seed 2 e 4, `structural:site_transition`
seed 3). Riporta i numeri che misuri, non quelli del piano.

## Il potere vincolante va **misurato**, non dichiarato

Alla fine, per ciascuna delle due famiglie nuove: rendi `post` del builder
corrispondente un `return` immediato e rilancia
`test_secchi_sul_banco` sui cinque seed. **I casi devono fallire.** Riporta la
frazione (es. «4/5»). Se una famiglia passa lo stesso con il builder spento, il
derivatore è vacuo e va corretto — è già successo quattro volte su questo
branch. Ripristina il builder prima di committare, e **verifica con `git diff`
che non resti traccia della mutazione**.

Il banco è nondeterministico: `domain/solver/model.py` non fissa `random_seed`
né `num_search_workers`. Un fallimento intermittente è **larghezza vera del
builder**, mai rumore da ignorare.

## Vincoli permanenti del branch

- `domain/analysis/` non deve **mai** importare `ortools`. Il solver sta in
  `domain/solver/`.
- Niente test duplicati con nome `test_*_sul_banco` per la stessa famiglia.
- La semplificazione «tutte le attività co-attive» va **rimossa** dal docstring
  di `subject_buckets.py`, non riadattata: con il ciclo per firma non è più
  vera. Sulla firma unica del Fermi il costo è zero, perché la deduplicazione
  collassa tutto in un vincolo solo.
- `SubjectBuilder.build` deve avere lo stesso `assert self.TYPE is not None` di
  `ResourceBuilder.build`, e per lo stesso motivo (una sottoclasse senza `TYPE`
  sarebbe silenziosamente vacua e nessun test se ne accorgerebbe).
- I test esistenti di `tests/test_solver_same_day.py` devono restare verdi
  **senza modifiche**: il refactor non cambia la semantica del caso pulito.

## Procedura

TDD: prima i test che falliscono, poi il codice. Alla fine
`venv/bin/pytest -q` per intero. Non committare: al commit ci pensa il
controller. Consegna un rapporto che dica, in ordine:

1. cosa hai implementato e dove;
2. la frazione di potere vincolante misurata per ciascuna famiglia nuova;
3. i quattro rami ADR-018 e quale test copre ciascuno;
4. i numeri finali della suite;
5. **cosa non hai fatto o non hai verificato** — esplicitamente, senza
   arrotondare. Su questo branch un rapporto che tace un dubbio costa più di un
   difetto dichiarato.
