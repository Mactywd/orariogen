# Task 15a — le parti entrano nel banco

Implementatore. Worktree `modello-hard-completo`, HEAD `41ae062`. Python:
`venv/bin/pytest`. Baseline: **375 passed, 4 skipped**. Docstring e commenti
in italiano senza accenti, identificatori in inglese. `domain/analysis/` **non
si tocca mai** (non deve importare `ortools`).

Questo e' il **prerequisito** del Task 15, separato apposta: non scrivi nessun
builder nuovo. Il tuo unico compito e' far entrare le **parti di classe** nella
scuola del banco di prova e rimettere in piedi tutto quello che si rompe.

## Il punto di partenza, gia' misurato

Ho applicato l'arricchimento previsto dal piano (Task 15, Step 1) e misurato:
**34 failed, 342 passed, 3 skipped**. Non e' una sorpresa da diagnosticare —
e' il tuo punto di partenza noto. I fallimenti sono di due specie:

```
E  AssertionError: _derive_weekly_order filtra su klass.pk: con le parti, le
   occorrenze legate alla sola parte sfuggono al derivatore e non al checker

E  AssertionError: il testimone stesso viola two_days_incompatible (seed 1):
   [('subject_two_days', (1,), (2, 14), (('day', 0),)), ...]
```

La prima specie viene dalle famiglie che hanno un `assert` di precondizione
(WEEKLY_ORDER, IMPOSED_SUCCESSION, HALF_DAY_GAP, MAX_HOURS_DAY/HALF_DAY); la
seconda dalle famiglie che non ce l'hanno (SAME_DAY, SAME_HALF_DAY,
TWO_DAYS). **Sono lo stesso difetto**: il derivatore filtra le attivita' con
`klass.pk in w.tokens[aid]`, il checker espande l'unita' a
`{class_id, *parts}` (`_unit_keys`, in
`domain/analysis/checkers/subject_constraints.py`).

## 0. Leggi prima

1. `domain/analysis/checkers/subject_constraints.py`: `_unit_keys`,
   `_placed_of`, `_is_class_level`.
2. `domain/analysis/state.py`: `activity_tokens` e `AtomMap` — in particolare
   la regola «parti di partizioni diverse della stessa classe condividono un
   atomo e confliggono; parti della **stessa** partizione no» (ADR-017).
3. `tests/solver_harness.py` per intero: `_school`, `_make_activities`,
   `_try_place`, e **tutti** i punti che fanno `klass.pk in w.tokens[aid]`
   (`grep -n "klass.pk in w.tokens"` → sei occorrenze) piu' `_capienza_secchio`.

## 1. L'arricchimento

In `_school`, dopo le sedi:

```python
partizione = ClassPartition.objects.create(
    school_class=classes[0], name="LINGUA")
parts = [ClassPart.objects.create(name=nm, partition=partizione)
         for nm in ("1A_ING", "1A_TED")]
```

e `"parts": parts` nel dizionario restituito.

In `_make_activities`, in coda, un'attivita' per parte (durata 1, maschera
casuale come le altre, un docente a caso, il `Service` sincronizzato sul
`effective_study_plan` della parte). Il codice esatto sta nel piano, Step 1
del Task 15.

⚠ Se qualche seed diventasse infattibile, `build_witness` lo dice con un
messaggio esplicito; in quel caso riduci le attivita' per classe da
`capienza // 2` a `capienza // 3` e **dillo nel report**.

## 2. La generalizzazione — il vero lavoro

Aggiungi al modulo un helper unico, e usalo **ovunque**:

```python
def _chiavi_unita(w, klass):
    """L'espansione dell'unita' «classe» come la fa il checker
    (`_unit_keys`, domain/analysis/checkers/subject_constraints.py): la
    classe **piu' tutte le sue parti**. Filtrare sul solo `klass.pk`
    perderebbe le attivita' legate alla sola parte, che il checker invece
    vede — e una riga derivata senza vederle nasce gia' violata."""
```

Sostituisci tutte e sei le occorrenze di `klass.pk in w.tokens[aid]` con
l'intersezione contro questo insieme, e **togli i quattro
`assert not ClassPart.objects.exists()`**: hanno fatto il loro lavoro,
adesso la condizione che asserivano e' falsa per costruzione.

⚠ Non fermarti al filtro. Con le parti in gioco cambia anche **cosa puo'
coesistere**: due attivita' su parti diverse della stessa partizione possono
partire nella stessa fascia. Ripercorri ogni derivatore che ragiona su
«quante ne stanno» o su «sono simultanee» e verifica che regga; in
particolare i derivatori dei secchi (SAME_DAY, SAME_HALF_DAY) contano
occorrenze per secchio, e ora un secchio puo' averne due nella stessa fascia.

## 3. `_capienza_secchio` — diventa **stretta**, ed e' la direzione vietata

La sua ricerca esatta di impacchettamento presuppone che due attivita' non
possano partire nella stessa fascia; l'ho fatta asserire al Task 11 proprio
perche' era una precondizione taciuta. Adesso e' falsa: la capienza reale del
secchio e' **maggiore** di quella calcolata, quindi la guardia scarta righe
**violabili** — il modo di sbagliare che la sua docstring dichiara di evitare.

Rilassala in modo dichiaratamente generoso:

```
capienza = max_pacchetto(attivita' di livello classe)
         + somma, su ogni parte, di max_pacchetto(attivita' di quella parte)
```

Ignora i conflitti classe-contro-parte, quindi e' `>=` della capienza vera
**per costruzione** — e resta molto piu' fine della somma nuda dei minuti.
Riscrivi la docstring: la precondizione «nessuna `ClassPart`» sparisce, quella
su `simultaneous_capacity == 1` **resta** e resta asserita.

⚠ Il costo e' qualche riga inviolabile che rientra nel banco. E' la direzione
accettabile: un caso di banco debole, non copertura persa in silenzio.
Dichiaralo.

## 4. Il criterio di riuscita

`venv/bin/pytest -q` → **375 passed** (o piu', se qualcosa si sdoppia) e
**4 skipped**.

⚠ **Uno skip in piu' non e' un successo.** Significa che un derivatore e'
diventato vacuo su un seed del banco per via della fixture piu' ricca. Se
succede: **non aggiustare il test**, misura *quale* famiglia e *quale* seed,
e riportalo. Uno skip nuovo giustificato e dichiarato e' un esito accettabile;
uno skip nuovo non notato no.

Allo stesso modo, se un test resta rosso e pensi che la causa sia il checker e
non il derivatore, **dillo nel report**: non toccare `domain/analysis/`.

## 5. Verifica che l'arricchimento serva davvero

Non basta che la suite torni verde: serve la prova che le parti siano
**davvero entrate** nel banco. Aggiungi un test in `tests/test_solver_witness.py`
(o dove ti sembra piu' naturale) che, costruito il testimone, verifichi che:

- esistono attivita' i cui token contengono una parte e **non** la classe;
- esiste almeno un seed in cui due attivita' di **parti diverse della stessa
  partizione** condividono la stessa cella — la proprieta' di ADR-017 che
  prima nessun banco esercitava.

Se la seconda non e' vera per nessuno dei cinque seed del banco, **dillo**:
significa che l'arricchimento e' entrato ma non morde, ed e' un'informazione,
non un fallimento.

## 6. Chiusura

- **Non committare, non pushare.** Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/task-15a-report.md`, con:
  la lista dei punti generalizzati, cosa hai cambiato in `_capienza_secchio` e
  perche' resta generoso, l'esito del punto 5, e ogni skip o rosso residuo.
- Se il brief contraddice il codice, **vince il codice**: segnalalo.
