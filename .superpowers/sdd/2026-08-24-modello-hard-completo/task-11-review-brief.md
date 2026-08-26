# Review del Task 11 — `MAX_HOURS_DAY`, `MAX_HOURS_HALF_DAY`, `FORBIDDEN_SEQUENCE`

Sei il revisore del Task 11. Lavori nel worktree
`.claude/worktrees/modello-hard-completo` e **non ne esci**. Test con
`venv/bin/pytest` dalla radice del worktree. **Non fare commit e non correggere
il codice**: il tuo compito è il rapporto.

## Cosa è cambiato

`git status`: `domain/solver/builders/subject_buckets.py`,
`tests/solver_harness.py`, `tests/test_solver_registry.py` modificati, più
`tests/test_solver_subject_maxhours.py` nuovo. Usa `git diff` per il perimetro
esatto. Suite attuale: **338 passed, 4 skipped** (baseline 315 + 4, stessi
quattro skip).

## Contesto obbligatorio

- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-11-brief.md` — il
  brief dato all'implementatore. **È l'autorità sopra il piano**, che in tre
  punti è dimostrabilmente sbagliato.
- `.superpowers/sdd/2026-08-24-modello-hard-completo/progress.md`, in fondo le
  **Rulings 54-62** (pre-dispatch, misurate). Leggi anche 13, 16, 20, 22, 23,
  24, 28, 31, 38, 43, 44, 48, 49, 50: sono le lezioni già pagate.
- `domain/analysis/checkers/subject_constraints.py` — **il checker è la
  verità**, in particolare `_MaxHours.violations` (149-159) e
  `ForbiddenSequenceChecker.violations` (135-142).
- ADR-018 in `docs/decisioni.md`.

## Il criterio, prima di tutto

Sette volte su questo branch il difetto non è stato codice sbagliato, ma una
**proprietà dichiarata vera che non lo è**, scoperta falsa solo controllandola
contro il checker o contro i dati. Il tuo lavoro principale è cercare quella.

Corollario: **un test verde non è copertura**. Un caso che passerebbe anche col
builder spento è un difetto, non un successo.

## Tre sospetti già aperti dal controller — verificali per primi

### Sospetto 1 — `MAX_HOURS_HALF_DAY` ha potere vincolante **1/5** (probabile Important)

L'implementatore l'ha misurato e riportato onestamente: spegnendo il `post`,
`MAX_HOURS_DAY` fallisce su 4 seed su 5, `FORBIDDEN_SEQUENCE` su 5 su 5,
`MAX_HOURS_HALF_DAY` su **1 solo** (il seed 5). Ha fatto **una sola misura per
seed** e non ha ripetuto.

È esattamente il punto dove la Ruling 38 (Task 9) e le Rulings 43-44 (Task 10)
hanno già trovato un difetto sotto una spiegazione comoda. **Non accettare la
spiegazione strutturale senza misurarla.**

Cosa fare, concretamente:

1. **Ripeti la misura** abbastanza volte da distinguere varianza da segnale.
   ⚠ CP-SAT è non deterministico qui: `domain/solver/model.py` non fissa né
   `random_seed` né `num_search_workers`. Le Rulings 43-44 stabiliscono la
   regola: un seed **deterministicamente a 0** merita la sonda strutturale, uno
   che **oscilla** no.
2. Se qualche seed è deterministicamente a 0, fai la **sonda di violabilità
   strutturale**: la riga creata per quel seed è violabile *davvero*, contro
   l'orario intero — non solo secondo la condizione necessaria del derivatore?
3. Decidi fra le due ipotesi, **con i numeri in mano**:
   - **strutturale**: «≤ `param` minuti per mezza giornata» è più **debole** di
     «≤ `param` minuti per giornata», perché un secchio più fine partiziona di
     più e lascia passare più piazzamenti (con 3 ore da 60' e `param = 60`: il
     vincolo giornata impone tre giorni distinti, quello mezza giornata solo tre
     mezze giornate, che stanno in due giorni). Se è questo, il derivatore è
     corretto e il limite va **scritto** nella sua docstring, come il Task 10 ha
     fatto per `SAME_HALF_DAY`;
   - **difetto**: la guardia di violabilità (Ruling 55) è troppo generosa e
     lascia passare righe che, dato il resto dell'orario, nessun piazzamento può
     violare. Se è questo, dillo e proponi la correzione.

⚠ Nota che la guardia è **due condizioni necessarie verificate
indipendentemente**: `totale_per_firma > param` su *una* firma, e
`_coppia_violabile` su *una qualsiasi* coppia — che possono essere firme
diverse. Resta necessaria (quindi non perde copertura), ma è più lasca di
quanto sembri. Valuta se è la causa.

### Sospetto 2 — il seed 1 di `MAX_HOURS_DAY` non discrimina, e nessuno sa perché

L'implementatore lo dichiara esplicitamente fra le cose non verificate: la riga
viene creata (potere > 0, altrimenti sarebbe skip), ma la soluzione trovata
**senza** il vincolo lo rispetta comunque. Stessa domanda del Sospetto 1, su un
caso singolo: è varianza di CP-SAT, o quella riga è di fatto inviolabile?

### Sospetto 3 — `test_forbidden_sequence_con_a_uguale_b` dichiara più di quanto verifica

La docstring afferma che con A = B il doppio ciclo del builder produce sia
`(a, b)` sia `(b, a)`, quindi «l'adiacenza è vietata in **entrambi i versi**».
Ma il test asserisce solo `not (day == 0 and slot == 1)` — cioè il verso *A
finisce, B comincia*. Il commento nel corpo ammette che il verso opposto è
«impossibile comunque» in quella fixture.

È una proprietà dichiarata e non difesa: il pattern esatto di questo branch.
Verifica se il verso opposto è testabile (per esempio con la congelata alla
fascia **1** e la libera che non deve andare alla **0**, cioè «la libera
finisce dove la congelata comincia») e se il test attuale passerebbe anche
rimuovendo metà del doppio ciclo del builder. Se sì, è un Important.

## Il resto del perimetro

**I tre derivatori.** Sono la parte che il piano aveva sbagliata. Verifica che
le correzioni siano quelle delle Rulings 55-57 e che siano **necessarie**, non
solo comode:

- `param` per firma di settimana (Ruling 56): controlla che il testimone non
  possa mai violare la riga derivata, e che `param` sia il più stretto che il
  testimone soddisfa;
- le guardie sono condizioni **necessarie** per la violabilità? Una guardia
  troppo stretta costa copertura persa in silenzio, ed è l'errore grave. Una
  troppo generosa costa un caso di banco debole. Verifica in quale direzione
  sbagliano;
- `_adiacenza_raggiungibile`: la docstring dice «nello stesso giorno», ma la
  funzione non guarda mai il giorno (`_collocazioni` restituisce solo fasce).
  Verifica se è solo imprecisione di docstring o se nasconde qualcosa (giorni
  festivi, che il helper dichiara di ignorare).

**ADR-018.** Rulings 14, 23, 28: si **clampa**, non si fa `continue`. Verifica
che il `continue` di `ForbiddenSequenceBuilder` sia davvero il caso `any_free`
(«un fatto, non una decisione») e non un tetto mascherato, e che
`_MaxHoursSubject` non salti mai un vincolo che andrebbe postato con tetto
ridotto. Riproduci il caso inverso: il modello non deve diventare INFEASIBLE
per colpa di congelate già in violazione — **tranne** dove è dichiarato che può
(ramo 3 di FORBIDDEN_SEQUENCE).

**`test_adr018_forbidden_sequence_entrambe_congelate_nessun_vincolo`.**
L'implementatore dichiara di aver trovato e corretto un difetto proprio lì: la
prima versione aveva tutta la riga congelata, quindi il **gate di riga** di
`SubjectBuilder.build` saltava `post()` a monte e il test non esercitava affatto
il `continue` per-coppia. Dice di aver aggiunto una terza attività libera e di
aver verificato per mutazione mirata. **Riverificalo**: rimuovi solo il
`if not any_free(...): continue` e controlla che il test diventi INFEASIBLE.

**Il refactor `_Bucketed`** (Ruling 58). Verifica che `_BucketIncompatible` non
abbia cambiato comportamento (`tests/test_solver_same_day.py` e
`tests/test_solver_subject_buckets.py` devono essere verdi **senza modifiche** —
controlla con `git diff` che non siano stati toccati), e che l'assert su `KIND`
morda ancora: una sottoclasse senza `KIND` deve rompersi, non prendere in
silenzio la semantica "half".

**La deduplicazione per `coinvolte`** (Ruling 60). La docstring di
`_MaxHoursSubject` afferma che con A != B l'effetto è «al più una riga postata
due volte identica, mai una firma saltata». Verificalo sul codice di
`SubjectBuilder.build`, non sulla docstring: è la stessa domanda che al Task 6
ha prodotto il difetto del D.T.B.

**Costo sul modello.** `tests/fermi.py` non crea alcun `SubjectConstraint`,
quindi questi tre builder dovrebbero costare **zero** sul Fermi. Confermalo con
i numeri (variabili/constraint prima e dopo), non per deduzione:
l'implementatore dichiara di non averlo controllato.

**La regressione.** `tests/test_solver_registry.py` è stato modificato:
controlla che sia solo l'aggiunta delle tre chiavi e l'aggiornamento del
docstring, non un allentamento del test.

## Cosa consegnare

Un rapporto con i finding classificati **Critical / Important / Minor**, ognuno
con: dove, perché è un difetto (contro quale fonte — checker, ADR, ruling), e
come si riproduce.

Se un sospetto si rivela infondato, **dillo esplicitamente con i numeri che lo
escludono**: un sospetto chiuso con una misura vale quanto un difetto trovato.

In fondo, una sezione **«cosa non ho verificato»**. Non arrotondare.
