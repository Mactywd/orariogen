# Task 16 — `structural:didactic_weight`

Implementatore. Worktree `modello-hard-completo`, HEAD `e83c104`. Python:
`venv/bin/pytest`. Baseline: **400 passed, 15 skipped**. Docstring e commenti
in italiano senza accenti, identificatori in inglese. `domain/analysis/` **non
si tocca mai**.

E' l'**ultimo builder**: con questo il registro passa da 26 chiavi su 27, e la
ventisettesima (`structural:coverage`) non ne ha una per costruzione.

Piano: sezione **Task 16** (riga 3715). ⚠ Il suo derivatore ha **lo stesso
difetto fatale** di quello del Task 15 — non restituisce niente — piu' un
problema di potere vincolante. Vedi §3.

## 0. Leggi prima

1. `domain/analysis/checkers/weight.py` — **l'autorita'**, per intero. E'
   corto: leggilo tutto, in particolare `_student_keys` e la precedenza del
   tetto settimanale.
2. `domain/analysis/state.py` — `ScheduleState.settings`, `class_caps`,
   `part_class`, `kinds`.
3. `domain/solver/residual.py` — `residual_cap`.
4. `domain/solver/builders/occupation.py` — un builder **strutturale** (non
   `ResourceBuilder` ne' `SubjectBuilder`) che cicla sulle firme e deduplica:
   e' il tuo modello di struttura.
5. `domain/solver/vocabulary.py` — `half_of`.

Tre dettagli del checker che vanno riprodotti **esattamente**:

- il peso di un'attivita' e' `subject.didactic_weight * duration_slots`, una
  **costante nota a build time**;
- le unita' su cui pesa sono le **parti** nei token, **oppure** la classe se
  la classe non ha partizioni (`_student_keys`). ⚠ **Non** tutti i token: i
  docenti non c'entrano. Un builder che sommasse su tutti i token
  vincolerebbe cose che il checker non guarda;
- il tetto **settimanale della classe** prevale su quello d'istituto:
  `class_caps.get(part_class.get(key, key))`, e si ricade su
  `settings.max_weight_week` solo se e' `None`. ⚠ **Ogni tetto `None` e'
  spento, non zero.**

## 1. Il builder

`domain/solver/builders/weight.py`, registrato su
`"structural:didactic_weight"` e aggiunto a `builders/__init__.py`.

Il codice del piano (Step 3) e' sostanzialmente **giusto**: cicla sulle firme,
raccoglie i termini `(peso, id, letterale)` per i tre secchi (giornata, mezza
giornata, settimana) e li chiude con `residual_cap`, che e' il trattamento
ADR-018 corretto perche' la somma e' **separabile** (ogni letterale pesa i
propri minuti). Prendilo come base.

Cose da verificare tu, non da dare per buone:

- **`v.half_of(slot)` restituisce 0/1**, e il piano confronta `meta == 0` per
  scegliere fra `max_weight_morning` e `max_weight_afternoon`. Controlla che
  il verso sia quello giusto contro il checker (`start_slot <
  morning_end_slot` = mattina).
- **Un'attivita' contribuisce piu' letterali allo stesso secchio** (una per
  cella candidata li' dentro). Va bene — `AddExactlyOne` limita la sua somma a
  1, quindi il peso entra una volta sola — ma **scrivilo**, e' la stessa
  osservazione che `post_separable` fa per il proprio caso.
- **La deduplicazione**: il piano usa `(bucket, frozenset(id), cap)`. Firme
  diverse con lo stesso insieme di attivita' attive producono lo stesso
  vincolo, come gia' per `OccupationBuilder`.
- **Con tutti i tetti a `None` il builder non posta nulla.** E' il caso
  normale in una base reale del prodotto (i quattro tetti d'istituto sono
  tutti a «nessuno»): dichiaralo in docstring, cosi' il silenzio non sembra un
  difetto.

## 2. ⚠ Le firme contano anche qui, ma non nel verso solito

Questo e' un **tetto**: piu' letterali significano una somma piu' vincolata,
mai il contrario. Quindi fondere le settimane sarebbe conservativo (si perde
qualche soluzione, mai se ne ammettono di illegali) — l'opposto del D.T.B.,
dove fondere allargava. Il ciclo per firma resta comunque, perche' e' piu'
preciso e perche' e' la regola della casa. **Scrivi la direzione** in
docstring: e' esattamente la distinzione che il changelog del 2026-08-24
registra fra `MaxGapBuilder` e `subject_constraints.py`, ed e' stata sbagliata
una volta.

## 3. Il derivatore — due difetti da correggere

⚠⚠ **Difetto fatale**: `_derive_weight` nel piano **non restituisce niente**.
`run_family` fa `if not potere: pytest.skip(...)`, quindi la famiglia
salterebbe **sempre**, su ogni seed. E' lo stesso difetto del Task 15, ed e'
la forma piu' pura del «successo travestito».

⚠ **Secondo difetto, meno visibile**: il piano somma su **tutti i token** e
si giustifica dicendo che una sovrastima produce tetti piu' larghi, quindi il
testimone li soddisfa comunque. Vero — ma un tetto piu' largo del massimo
reale e' **inviolabile**: se il massimo su tutte le chiavi viene da un docente
(che il checker non guarda), il tetto puo' risultare molto sopra qualunque
valore che un'unita'-studente potra' mai raggiungere, e nessun piazzamento
potra' violarlo. Il banco lo conterebbe come successo.

Riscrivilo:

- somma **sulle stesse unita' del checker** (`_student_keys`), non su tutti i
  token: cosi' i tetti sono stretti e violabili;
- **per firma**: il checker valuta uno `ScheduleState` per firma, quindi il
  tetto dev'essere il **massimo fra le firme** del massimo per secchio, non il
  massimo sull'unione (che sarebbe piu' largo e quindi piu' debole);
- **guardia di violabilita'**: un tetto che nessun piazzamento puo' superare
  e' vacuo. Almeno: niente tetto se il valore derivato e' `0`, e niente tetto
  se e' `>=` del peso **totale** che quella unita' puo' accumulare in quel
  secchio (per la settimana: il peso totale di tutte le sue attivita');
- **restituisci un intero**: quanti tetti hai davvero acceso.

**Esercita anche il tetto di classe**: il ramo `class_caps` prevale su quello
d'istituto ed e' l'unico pezzo di semantica che i tetti globali non toccano.
Se riesci a farlo dal derivatore senza rendere il banco fragile, fallo;
altrimenti basta un test scritto a mano — ma **deve esistere**, e la mutazione
che lo difende e' «ignora `class_caps` e usa sempre `settings.max_weight_week`».

Misura tu, prima di dichiarare fatto: su almeno 20 seed, quanti tetti accendi,
quanti testimoni violi (**deve essere zero**) e su quanti seed **morde** col
builder spento. Spegnilo con
`monkeypatch.setattr(DidacticWeightBuilder, "build", lambda *a, **k: None)` in
una sonda usa-e-getta: non toccare il sorgente e non riscrivere il derivatore
dentro la sonda (Ruling 98). I numeri vanno nel **report** (Ruling 50).

## 4. I test — `tests/test_solver_weight.py`

Niente `test_peso_sul_banco`: `test_solver_witness.py::test_famiglia` lo
genera gia' (Ruling 16, nona applicazione). Copia in testa al modulo la nota ⚠
degli altri file di test del solver.

**Forma obbligatoria (Ruling 85)**: il test che dimostra che il vincolo morde
si scrive con `build_model` + `model.Add(ctx.x[...] == 1)` **forzando la
violazione** e attendendo `INFEASIBLE`. ⚠ Il test del piano
(`test_il_tetto_giornaliero_distribuisce_il_carico`) e' nella forma «risolvi e
guarda la soluzione» che su questo branch e' gia' stata misurata inutile: non
copiarlo.

Servono almeno:

1. **Il tetto giornaliero morde**: tre attivita' di peso 2 forzate nello
   stesso giorno con `max_weight_day = 4` → INFEASIBLE; due sole → FEASIBLE.
2. **Mattina e pomeriggio sono secchi distinti**, e non invertiti: una
   configurazione legale per il mattino e illegale per il pomeriggio (o
   viceversa). **Verifica per mutazione** scambiando i due tetti.
3. **Il tetto settimanale**, e il **tetto di classe che prevale** su quello
   d'istituto.
4. **Le unita'-studente non sono tutti i token**: due classi diverse con lo
   stesso docente; il peso non deve sommarsi sul docente. Senza questo test,
   un builder che sommasse su tutti i token passerebbe.
5. **I tetti spenti non postano nulla**: il test del piano
   (`test_i_tetti_spenti_non_postano_nulla`) va bene — e' un test di
   **assenza**, quindi non puo' essere rosso sotto `build()` no-op: difendilo
   con la mutazione mirata «tratta `None` come 0».
6. **ADR-018**: un secchio gia' oltre il tetto per via delle congelate, piu'
   una libera. Il modello **non** dev'essere INFEASIBLE (`residual_cap` clampa
   a zero), e la libera non deve poter entrare in quel secchio. Asserzione
   **strutturale**, non «risolvi e guarda».

**Criterio di mutazione (Ruling 89)**: ogni test che afferma la **presenza**
di un vincolo dev'essere rosso con `build()` reso no-op; quelli che affermano
un'**assenza** vanno difesi da una mutazione mirata. Nel report elenca ogni
mutazione con l'esito.

## 5. Chiusura

- `venv/bin/pytest -q`: **400 + i tuoi**, e **15 skipped**. ⚠ Uno skip in piu'
  va misurato e riportato, non nascosto.
- Aggiorna `tests/test_solver_registry.py` con la chiave nuova e la docstring.
- **Non committare, non pushare.** Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/task-16-report.md`.
- Se il brief contraddice il codice, **vince il codice**: segnalalo. E' gia'
  successo due volte su questo branch, ed entrambe le volte aveva ragione chi
  ha guardato il codice.
