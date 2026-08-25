# Review del Task 10 — `SubjectBuilder`, `SAME_HALF_DAY`, `TWO_DAYS`

Sei il revisore del Task 10. Lavori nel worktree
`.claude/worktrees/modello-hard-completo` e **non ne esci**. Test con
`venv/bin/pytest` dalla radice del worktree.

## Cosa è cambiato

`git status` mostra: `domain/solver/builders/base.py`,
`domain/solver/builders/subject_buckets.py`, `domain/solver/vocabulary.py`,
`tests/solver_harness.py`, `tests/test_solver_registry.py` modificati, più
`tests/test_solver_subject_buckets.py` nuovo. Usa `git diff` per il perimetro
esatto.

## Contesto obbligatorio

- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-10-brief.md` — il
  brief dato all'implementatore. È l'autorità sopra il piano.
- `.superpowers/sdd/2026-08-24-modello-hard-completo/progress.md` — il registro,
  in fondo le Ruling 40, 41, 42 pre-dispatch. Leggi anche le Ruling 13, 16, 20,
  22, 23, 24, 28, 31, 38: sono le lezioni già pagate su questo branch.
- `domain/analysis/checkers/subject_constraints.py` — **il checker è la
  verità**. Ogni affermazione del builder va verificata leggendo lì, non
  fidandosi del docstring del builder.
- ADR-018 in `docs/decisioni.md`.

## Il criterio, prima di tutto

Su questo branch il difetto ricorrente non è il codice sbagliato: è una
**proprietà dichiarata vera che non lo è**, e che si scopre falsa solo
controllandola contro il checker o contro i dati. È successo sei volte. Il tuo
lavoro principale è cercare quella, non refusi.

Corollario: **un test verde non è copertura**. Un caso di banco che passerebbe
anche col builder spento è un difetto, non un successo.

## Due sospetti già aperti dal controller — verificali per primi

### Sospetto 1 — `test_secchi_sul_banco` è un doppione (probabile Important)

`tests/test_solver_witness.py::test_famiglia` parametrizza **già** su
`sorted(DERIVERS, key=str)` × 5 seed: ogni famiglia registrata è quindi già
provata sul banco. `test_secchi_sul_banco` nel file nuovo esegue esattamente
`run_family(tipo, seed)` sugli stessi 5 seed → 10 test duplicati.

È la Ruling 16, già applicata due volte: `tests/test_solver_sites.py` e
`tests/test_solver_max_presence.py` hanno una nota ⚠ in testa al modulo che
spiega perché il test del banco *non* sta lì. Verifica che sia davvero lo stesso
caso, e se sì chiedi la stessa forma (rimozione + nota nel docstring del
modulo). ⚠ `tests/test_solver_time_counting.py` ne ha ancora due: sono residui
anteriori alla Ruling 16, non un precedente da imitare.

### Sospetto 2 — il potere vincolante di `SAME_HALF_DAY` è **1–2/5**

L'implementatore l'ha misurato e riportato onestamente, spiegandolo come
non-determinismo di CP-SAT più assenza di obiettivo. **Non prendere per buona
quella spiegazione senza misurarla**: è esattamente la risposta comoda che la
Ruling 38 ha falsificato al Task 9, dove un potere basso nascondeva un
derivatore strutturalmente vacuo.

Cosa misurare, concretamente:

1. Il potere vincolante di `_derive_same_day` (la famiglia **esistente**, non
   toccata da questo task) sugli stessi seed, con lo stesso metodo — spegnendo
   `SameDayBuilder.post`. È il termine di paragone che manca al rapporto.
2. Ripeti la misura di `SAME_HALF_DAY` abbastanza volte da distinguere varianza
   da segnale (al Task 9 la varianza è risultata **zero** su sei esecuzioni, e
   il "rumore" era un difetto).
3. Decidi fra le due ipotesi, con i numeri in mano:
   - **strutturale**: «al più uno per mezza giornata» è più **debole** di «al
     più uno per giorno» — i secchi sono più fini, quindi una soluzione
     qualsiasi lo soddisfa per caso più spesso. Se è questo, il derivatore è
     corretto e il limite va **scritto** nella sua docstring, non lasciato
     implicito;
   - **difetto**: il derivatore crea righe che, per come è fatta la fixture,
     sono difficili o impossibili da violare. Se è questo, dillo e proponi la
     correzione (per esempio derivare dalle coppie con più occorrenze, o
     ammettere anche A ≠ B).

Non risolvere il sospetto a favore dell'ipotesi comoda solo perché la suite è
verde.

## Il resto del perimetro

**La tabella a quattro rami di `_post_cross`.** È il cuore del task, dettata
nella Ruling 41. Verifica ogni riga contro `_BucketIncompatible.violations` e
`TwoDaysChecker.violations`:

- il ramo `fa=1, fb=0` lascia deliberatamente **libere** le attività libere di
  A. È giusto? (Il checker emette il finding solo `if la and lb`.) E il test che
  lo dimostra distingue davvero questa regola da quella meccanica
  `max(0, 1 - fa - fb)`, o passerebbe anche con quella?
- il ramo `fa=1, fb=1` azzera i letterali liberi. Copre entrambe le materie? E
  il test corrispondente fallirebbe se ne coprisse una sola?
- `TwoDaysBuilder` usa `_post_cross` **anche con A = B**. Verifica sul checker
  che sia corretto (`a_days[d]` contro `b_days[d+1]`) e che `fa`/`fb` siano
  calcolati sui due giorni giusti.

**ADR-018, la regola generale.** Rulings 14, 23, 28: si **clampa**, non si fa
`continue`. Controlla che nessun percorso di `subject_buckets.py` salti un
vincolo che dovrebbe essere postato con un tetto ridotto. E controlla il caso
inverso: che il modello non diventi `INFEASIBLE` per colpa di attività congelate
già in violazione (era il difetto misurato pre-dispatch, Ruling 40 — riproducilo
prima e verifica che ora non si riproduca).

**Il gate di riga in `SubjectBuilder.build`.** È a livello di riga, non di
secchio. Verifica che non nasconda un caso in cui un secchio andrebbe comunque
vincolato, e che `test_il_vincolo_non_si_posta_se_nulla_e_libero` continui a
dipendere da lui e non da un effetto collaterale.

**La deduplicazione.** `posted` usa `coinvolte` come chiave. È sufficiente?
`post()` dipende da `rep` anche attraverso `subject_literals` e
`subject_bucket`: due firme con lo stesso `coinvolte` producono davvero gli
stessi vincoli? (È la stessa domanda che al Task 6 ha prodotto il difetto del
D.T.B.: un insieme di chiavi dichiarato sufficiente e non esserlo.)

**Costo sul modello.** `_post_cross` posta `ha + hb <= 1` per **ogni** secchio,
anche dove nessuna delle due materie ha letterali: due variabili e un constraint
buttati. Quantificalo sul Fermi (`tests/fermi.py`) e sul banco: numero di
variabili e constraint prima/dopo il task. Se è significativo, è una Minor con
un numero attaccato, non un'impressione.

**La regressione.** `tests/test_solver_same_day.py` doveva restare verde **senza
modifiche**: verifica con `git diff` che non sia stato toccato.
`tests/test_solver_registry.py` invece è stato modificato — controlla che la
modifica sia solo l'aggiunta delle due chiavi nuove e non un allentamento del
test.

**Il bug che l'implementatore dichiara di aver corretto** (`residual_cap`
restituisce `(peso, letterale)`, non `(aid, letterale)`, quindi il conteggio
delle attività distinte leggeva il peso): verifica che la correzione sia giusta
*e* che esista un test che fallirebbe se tornasse. Se la copertura passa solo da
un test end-to-end, dillo.

## Cosa consegnare

Un rapporto con i finding classificati **Critical / Important / Minor**, ognuno
con: dove, perché è un difetto (contro quale fonte — checker, ADR, ruling), e
come si riproduce. Se un sospetto si rivela infondato, **dillo esplicitamente
con i numeri che lo escludono**: un sospetto chiuso con una misura vale quanto
un difetto trovato.

In fondo, una sezione **«cosa non ho verificato»**. Non arrotondare.

Non fare commit e non correggere il codice: il tuo compito è il rapporto.
