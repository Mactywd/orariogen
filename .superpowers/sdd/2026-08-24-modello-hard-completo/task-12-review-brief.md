# Review del Task 12 — `WEEKLY_ORDER`

Sei il revisore. Repo: worktree `modello-hard-completo`, HEAD `9e8471a`, il
lavoro da rivedere e' **non committato** (`git status` lo mostra).
Python: `venv/bin/pytest`. Suite attuale: **351 passed, 4 skipped** (baseline
prima del task: 340 passed, 4 skipped — nessuno skip nuovo).

Materiale:
- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-brief.md` — il
  brief dato all'implementatore;
- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-report.md` — il
  suo report;
- `.superpowers/sdd/2026-08-24-modello-hard-completo/progress.md` — il
  registro delle decisioni (81 rulings; le 78-81 sono di questo task).

Diff da rivedere: `domain/solver/builders/subject_order.py` (nuovo),
`tests/test_solver_subject_order.py` (nuovo), piu' le modifiche a
`tests/solver_harness.py`, `domain/solver/builders/__init__.py`,
`tests/test_solver_registry.py`.

L'autorita' su cosa il vincolo **significa** e'
`domain/analysis/checkers/subject_constraints.py` (`WeeklyOrderChecker`,
`_SubjectChecker.check`, `_placed_of`). Non il brief, non il piano, non i
docstring del builder: il checker.

---

## Il difetto ricorrente di questo branch

Otto volte su questo branch il piano (o una docstring, o un test) ha
**dichiarato vera una proprieta'** — una direzione conservativa, un insieme di
chiavi sufficiente, una precondizione, una guardia necessaria — che si e'
rivelata falsa solo controllandola contro il checker o contro i dati, mai a
colpo d'occhio. E una variante piu' sottile: **una proprieta' vera che nessun
test difende**, dimostrabile mutando il builder e guardando la suite restare
verde.

Il tuo compito principale e' cercare la nona. Non ti fidare di nessuna frase
che dica «conservativo», «necessario», «per costruzione», «basta questo»:
**verificale**, con una sonda o con una mutazione.

---

## Cose gia' misurate — non rifarle, ma puoi contestarle

Mutazioni che ho gia' verificato io dopo la consegna (tutte applicate,
eseguite, e ripristinate):

| mutazione | esito |
|---|---|
| togliere `signature=rep` dalle due `subject_activities` | rosso `test_weekly_order_posta_per_firma_di_settimana` |
| sostituire i due rami ADR-018 con `model.Add(prima_a <= prima_b)` secco | rosso `test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo` |
| togliere la guardia `A = B` | rosso `test_weekly_order_con_a_uguale_b_non_vincola_nulla` |
| `post()` reso **no-op completo** | rossi 3 test su 6 |

Misure del derivatore, fatte **prima** di scrivere il brief (60 seed): il
derivatore del piano produceva 60/60 righe ma **19/60 con il testimone che
viola la riga appena creata**, seed 1 incluso. Quello consegnato: **0/60
vacuo, 0/60 testimoni violati, 1-6 righe per seed**; potere vincolante col
builder assente **19/20 seed**, **4/5 nel banco** (seed 5 deterministicamente
non mordente su quattro esecuzioni).

## Un difetto che ho gia' trovato — verificalo e dimmi quanto e' grave

Nella mutazione «`post()` no-op» **tre** test su sei restano verdi, e fra
questi c'e' `test_weekly_order_impone_la_prima_occorrenza` — cioe' proprio il
test la cui unica ragione d'essere e' mostrare che il vincolo **morde**. Con
il builder che non posta nulla, la soluzione soddisfa comunque
`prima(a) <= prima(b)`, per fortuna e in modo deterministico.

Voglio da te: (a) conferma indipendente; (b) se e' rimediabile, la forma
minima di test che morde davvero (e la sua verifica per mutazione); (c) se
**non** e' rimediabile mantenendo la forma «assert su una soluzione», dillo e
motiva — con una raccomandazione su quale forma usare al posto suo per i sei
vincoli d'ordine che restano (Task 13-17).

---

## Punti specifici da attaccare

1. **La disgiunzione reificata di ADR-018.** Il builder afferma che
   `prima_a >= FA` equivale a `prima_a == FA` perche' «una congelata di A sta
   gia' in FA e `prima_a` e' un minimo sull'intero gruppo». Verificalo. Poi
   verifica l'affermazione piu' forte: che nel ramo status-quo `Finding.key`
   resti **identico** alla baseline. Costruisci il caso se serve — in
   particolare, `Finding.key` include cosa, esattamente? Leggi
   `domain/analysis/findings.py`, non dedurlo.
2. **La disgiunzione e' la forma piu' debole corretta?** Il brief lo afferma.
   Esiste un piazzamento che la disgiunzione vieta e che *non* produce alcun
   finding nuovo? Se si', il builder e' piu' stretto della spec, ed e' un
   Important.
3. **Il ramo `FA is None or FB is None`.** Il docstring lo giustifica con un
   ragionamento sulla baseline che a me suona confuso (il paragrafo «Include
   il caso in cui una delle due materie non ha alcuna congelata…»). Controlla
   se il ragionamento e' corretto **e** se e' scritto in modo che regga alla
   rilettura fra sei mesi. Caso concreto da provare: `FA` finito, `FB` None,
   con una libera di B che non ha nessuna cella dopo `FA`. Il modello diventa
   INFEASIBLE? E se si', e' «divieto di peggiorare» (ammesso) o «pretesa di
   riparare» (vietato)?
4. **La guardia di violabilita' del derivatore** (`floor_b < ceil_a`
   su `_pos_bounds`). E' dichiarata «necessaria, non sufficiente», cioe'
   generosa. **Cerca le precondizioni taciute**: sotto quali condizioni
   diventerebbe **stretta** (scartando righe violabili)? Nel Task 11 la stessa
   frase nascondeva due precondizioni (capienza simultanea 1, nessuna
   `ClassPart`), poi asserite invece che sperate. Vale lo stesso qui? E
   `_pos_bounds` decompone il min/max del prodotto cartesiano giorni x fasce:
   quella decomposizione e' sempre lecita, o solo perche' il dominio e'
   davvero un prodotto?
5. **`klass.pk in w.tokens[aid]` contro `_unit_keys(row)`.** Il checker
   espande l'unita' della riga a `{class_id, *parts}`; il derivatore filtra
   sul solo `klass.pk`. Coincidono solo se il testimone non ha `ClassPart`.
   E' una precondizione taciuta (come nel Task 11)? ⚠ E' un pattern
   **preesistente**, condiviso con i derivatori dei Task 10-11: se e' un
   problema, dimmi se va corretto qui o registrato per il Task 17.
6. **`vocab.pos` al primo uso in produzione.** Finora lo toccava solo
   `tests/test_solver_vocabulary.py`. La sua memoizzazione e' **per attivita'**
   e non per firma: e' corretto, o e' la stessa forma del difetto D.T.B. del
   2026-08-24? E il limite superiore `days_per_cycle * slots_per_day` passato
   a `NewIntVar` e' coerente col dominio reale di `pos`?
7. **Il test sulle firme** (`test_weekly_order_posta_per_firma_di_settimana`)
   e' costruito a mano con `model.Add(ctx.x[...] == 1)`. Verifica che stia
   testando cio' che dichiara e non un artefatto: le posizioni citate nei
   commenti (pos 0, pos 12) corrispondono alla griglia che `mini_school`
   costruisce davvero?
8. **Potere vincolante**: rimisuralo per conto tuo, con la tua metodologia.
   Se ottieni numeri diversi dai miei, i tuoi vincono se sai dire perche'.
   ⚠ CP-SAT e' non deterministico qui (`domain/solver/model.py` non fissa
   `random_seed` ne' `num_search_workers`): distingui un seed
   **deterministicamente** a zero da uno che oscilla.
9. Qualunque **proprieta' dichiarata in docstring senza un test che la
   difenda**. Provale per mutazione.

---

## Cosa NON e' in scope

- I ventidue vincoli non ancora tradotti, e i Task 13-17.
- Le questioni gia' aperte nel registro e rinviate al Task 17 (Rulings 17, 20,
  22, 39, 47, 65) — se ne incontri una, **nominala e vai oltre**, non
  risolverla qui.
- Riscrivere `domain/analysis/`. Quel package non deve mai importare
  `ortools`: se pensi che il checker sia sbagliato, **dillo**, non correggerlo.

## Come consegnare

Scrivi il report in
`.superpowers/sdd/2026-08-24-modello-hard-completo/task-12-review.md`,
classificando ogni rilievo come **Critical / Important / Minor**, ciascuno con:
il fatto misurato (comando e output, non impressione), perche' e' un problema,
e la correzione minima. Se una cosa ti sembra sbagliata ma la misura ti
smentisce, **scrivi anche quella**: sapere cosa e' stato controllato e trovato
sano vale quanto un rilievo.

**Non fare commit, non fare push, e non correggere il codice**: il giro di
correzione e' separato. L'unica eccezione sono sonde usa-e-getta, che devi
cancellare prima di consegnare.
