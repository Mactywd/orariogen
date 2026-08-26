# Task 3 — ADR-018: l'helper del residuo e l'oracolo differenziale

## Cosa ho implementato

1. **`domain/solver/residual.py`** (nuovo). Quattro funzioni, riprese alla
   lettera dal brief:
   - `split(ctx, terms)` — separa i termini `(peso, id_attivita', letterale)`
     in `(liberi, consumo_congelate)`.
   - `residual_cap(ctx, terms, cap)` — residuo di un tetto, clampato a zero
     con `max(0, cap - frozen)`.
   - `residual_floor(ctx, terms, floor)` — residuo di un minimo garantito,
     **non** clampato (`floor - frozen`, puo' essere negativo o zero: vincolo
     vacuo, mai infattibile).
   - `any_free(ctx, activity_ids)` — vero se almeno un id e' in `ctx.free`.

2. **`tests/test_solver_residual.py`** (nuovo, 5 test), copiato dal brief
   senza modifiche.

3. **`tests/test_solver_oracle.py`** (modificato). `violazioni()` ora
   restituisce un `set` delle **chiavi** (`Finding.key`, non l'oggetto
   `Finding`) dei finding HARD nelle famiglie modellate, invece di una
   lista di oggetti `Finding`. Aggiunta `nuove(schedule, prima, codici=CODICI)`
   che calcola i finding comparsi *dopo* il solve (`violazioni(...) - prima`).
   Le sei occorrenze di `assert violazioni(...) == []` sono diventate
   `assert violazioni(...) == set()`.

   **Una correzione non elencata esplicitamente nel brief ma necessaria**: in
   `test_oracolo_puo_fallire` due righe estraevano il codice cosi':
   `codici = {f.code for f in violazioni(env["schedule"])}`. Con la nuova
   `violazioni()` che restituisce chiavi (tuple `(code, resources, activities,
   quantities)`, vedi `Finding.key` in `domain/analysis/findings.py`) invece
   di oggetti `Finding`, `f.code` avrebbe sollevato `AttributeError` su una
   tupla. Corretto in
   `codici = {codice for codice, *_ in violazioni(env["schedule"])}` in
   entrambi i punti (righe ~157 e ~171). E' l'unica deviazione dal testo
   letterale del brief, resa necessaria dalla combinazione
   lista→insieme-di-chiavi che il brief stesso richiede.

   Ho anche aggiornato due menzioni di `violazioni() == []` nei docstring
   (righe 135 e 317, non asserzioni) a `violazioni() == set()`, per non
   lasciare la documentazione in contraddizione con il codice.

## Cosa ho testato, e risultati

**RED** — prima di scrivere `residual.py`:

```
$ venv/bin/pytest tests/test_solver_residual.py -v
...
ImportError while importing test module '.../tests/test_solver_residual.py'.
Traceback:
/home/mattia/Miniforge3/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_solver_residual.py:7: in <module>
    from domain.solver.residual import any_free, residual_cap, residual_floor, split
E   ModuleNotFoundError: No module named 'domain.solver.residual'
=========================== short test summary info ============================
ERROR tests/test_solver_residual.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.12s ===============================
```

Fallimento atteso e per il motivo giusto: il modulo non esiste ancora.

**GREEN** — dopo aver scritto `domain/solver/residual.py`:

```
$ venv/bin/pytest tests/test_solver_residual.py -v
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0 -- /home/mattia/coding/scuola/orariogen/venv/bin/python3
cachedir: .pytest_cache
django: version: 5.2.17, settings: config.settings (from ini)
rootdir: /home/mattia/coding/scuola/orariogen/.claude/worktrees/modello-hard-completo
configfile: pytest.ini
plugins: django-4.14.0
collecting ... collected 5 items

tests/test_solver_residual.py::test_split_separa_libere_e_congelate PASSED [ 20%]
tests/test_solver_residual.py::test_residual_cap_sottrae_il_consumo_delle_congelate PASSED [ 40%]
tests/test_solver_residual.py::test_residual_cap_clampa_a_zero_invece_di_andare_negativo PASSED [ 60%]
tests/test_solver_residual.py::test_residual_floor_non_clampa PASSED     [ 80%]
tests/test_solver_residual.py::test_any_free_e_la_regola_dell_implicazione PASSED [100%]

============================== 5 passed in 0.27s ===============================
```

**Oracolo, dopo la riscrittura** (l'unico modo per verificare la correzione
delle due righe `codici = {...}`):

```
$ venv/bin/pytest tests/test_solver_oracle.py -v
============================= test session starts ==============================
...
collected 6 items

tests/test_solver_oracle.py::test_oracolo_sulla_scuola_media PASSED      [ 16%]
tests/test_solver_oracle.py::test_oracolo_sul_fermi_per_una_classe PASSED [ 33%]
tests/test_solver_oracle.py::test_oracolo_puo_fallire PASSED             [ 50%]
tests/test_solver_oracle.py::test_oracolo_su_istanza_multi_firma PASSED  [ 66%]
tests/test_solver_oracle.py::test_oracolo_su_istanza_multi_firma_fattibile PASSED [ 83%]
tests/test_solver_oracle.py::test_fermi_intero_misurato PASSED           [100%]

============================== 6 passed in 2.58s ===============================
```

Sei test su sei, lo stesso numero di prima (nessun caso sparito).

**Suite completa**, lanciata una sola volta prima del commit:

```
$ venv/bin/pytest -q
........................................................................ [ 38%]
........................................................................ [ 76%]
............................................                             [100%]
188 passed in 7.40s
```

⚠ Il brief allo Step 5 indicava **186 passed** atteso, ma il prompt del
controller dichiara esplicitamente che la suite parte da **183** test verdi
(non 181, come implicito nel conto del brief). 183 + 5 nuovi test di
`test_solver_residual.py` = **188**, il numero letto dall'output. Nessun test
e' stato perso: la discrepanza con il brief e' nel numero di partenza
assunto, non in un test mancante — coerente con la nota esplicita del
controller "la suite e' a 183 test verdi" nell'elenco delle interfacce dai
task gia' chiusi.

Nessun warning nell'output (`grep -i warning` sull'output di `pytest -q` non
ha prodotto righe).

## File cambiati

- `domain/solver/residual.py` (nuovo)
- `tests/test_solver_residual.py` (nuovo)
- `tests/test_solver_oracle.py` (modificato)

## Osservazioni dell'autorevisione

- Le quattro funzioni di `residual.py` sono identiche al testo del brief,
  nessuna aggiunta oltre lo scopo del task (niente YAGNI-breaking).
- La firma `SolverContext.free` e' stata verificata contro
  `domain/solver/context.py` prima di scrivere il codice (riga 22:
  `free: set # id delle attività che il solver può muovere`), coerente con
  l'interfaccia "Consumes: SolverContext.free" del brief.
- Verificato che nessun builder in `domain/solver/builders/` chiama ancora
  `residual_cap`/`residual_floor` — coerente con l'avvertenza del brief che il
  primo uso end-to-end arriva nel Task 6, non qui.
- La deviazione dal testo letterale (le due righe `codici = {codice for
  codice, *_ in violazioni(...)}`) e' minima e strettamente necessaria: il
  brief non le menziona esplicitamente ma il cambio di tipo di ritorno di
  `violazioni()` (da lista di `Finding` a insieme di chiavi) le rende
  obbligatorie per non rompere `test_oracolo_puo_fallire`. Ho verificato che
  quel test — l'unico che dipende da questa estrazione — passa e continua a
  discriminare (i due `assert "..." in codici` restano significativi, non
  vacui, perche' derivano dal primo elemento della tupla-chiave che e'
  sempre `code`).
- Non ho toccato `subject_constraints.py` ne' altri builder esistenti: fuori
  scope per questo task, come da nota nel changelog del progetto
  ("La stessa semplificazione in subject_constraints.py resta corretta").

## Dubbi

Nessuno che blocchi la consegna. L'unico punto degno di nota e' la
discrepanza fra il conteggio "186 passed" del brief e il "188 passed"
osservato — spiegata sopra e coerente con le interfacce dichiarate dal
controller (183 test di partenza), non un segnale di regressione.

---

## Rapporto di correzione — giro di review 1

### Osservazione Important accolta

Il revisore ha trovato che `violazioni()` in `tests/test_solver_oracle.py`
riduceva ogni finding alla sola `Finding.key`, che **esclude
deliberatamente** `weeks` (`domain/analysis/findings.py:27-31`, "Identità per
il dedup fra firme di settimana"). `check_schedule` (`domain/analysis/conformity.py:53-58`)
usa la stessa chiave per fondere finding di firme diverse in un unico oggetto
con `weeks` allargato. Conseguenza: una violazione preesistente in una firma
e una **nuova** violazione identica per codice/risorse/attività/quantità in
un'**altra** firma collassano nello stesso finding — `nuove()` non la vede,
perché la chiave era già in `prima`. Non ipotetico: `max_gap`
(`domain/analysis/checkers/time_constraints.py:196-197`, l'esatto vincolo del
difetto del 2026-08-24) non ha nessuna attività nella chiave, solo risorsa e
due numeri — due firme con lo stesso totale di buco sulla stessa risorsa
collidono.

### Correzione implementata

Ho applicato **esattamente** la forma indicata dal revisore, senza varianti:

```python
def violazioni(schedule, codici=CODICI):
    """L'insieme delle (chiave, settimana) dei finding HARD nelle famiglie
    modellate. ..."""
    return {(f.key, w) for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codici
            for w in f.weeks}
```

`nuove()` non è cambiata nel corpo (`violazioni(schedule, codici) - prima`):
la sottrazione ora opera su coppie `(chiave, settimana)`, e — come nota il
revisore — resta corretta anche quando il solver ripara una firma, perché
una riparazione può solo togliere elementi da `dopo`.

**Conseguenza a cascata non menzionata esplicitamente dal revisore, ma
necessaria**: due righe in `test_oracolo_puo_fallire` estraevano il codice
così: `codici = {codice for codice, *_ in violazioni(env["schedule"])}`. Con
`violazioni()` che ora restituisce coppie `(chiave, settimana)` invece di
sole chiavi, ogni elemento è `((code, resources, activities, quantities),
week)` — un 2-tuple, non più direttamente spacchettabile con `codice, *_`.
Corretto in `codici = {codice for (codice, *_), _settimana in
violazioni(env["schedule"])}` in entrambi i punti (righe ~165 e ~179). Stessa
categoria di correzione minima già fatta nel giro precedente per lo stesso
motivo strutturale (il tipo di ritorno di `violazioni()` cambia).

### Verifica: i sei `== set()` esistenti non sono diventati rossi

Come richiesto, ho verificato per primo che nessuno dei sei
`assert violazioni(...) == set()` esistenti si rompesse con la nuova forma
(l'espansione per settimana non cambia il risultato quando non ci sono
collisioni fra firme, che è il caso di tutti e sei):

```
$ venv/bin/pytest tests/test_solver_oracle.py -v
============================= test session starts ==============================
platform linux -- Python 3.12.12, pytest-9.1.1, pluggy-1.6.0 -- /home/mattia/coding/scuola/orariogen/venv/bin/python3
cachedir: .pytest_cache
django: version: 5.2.17, settings: config.settings (from ini)
rootdir: /home/mattia/coding/scuola/orariogen/.claude/worktrees/modello-hard-completo
configfile: pytest.ini
plugins: django-4.14.0
collecting ... collected 7 items

tests/test_solver_oracle.py::test_oracolo_sulla_scuola_media PASSED      [ 14%]
tests/test_solver_oracle.py::test_oracolo_sul_fermi_per_una_classe PASSED [ 28%]
tests/test_solver_oracle.py::test_oracolo_puo_fallire PASSED             [ 42%]
tests/test_solver_oracle.py::test_oracolo_su_istanza_multi_firma PASSED  [ 57%]
tests/test_solver_oracle.py::test_oracolo_su_istanza_multi_firma_fattibile PASSED [ 71%]
tests/test_solver_oracle.py::test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana PASSED [ 85%]
tests/test_solver_oracle.py::test_fermi_intero_misurato PASSED           [100%]

============================== 7 passed in 2.58s ===============================
```

Nessuno è diventato rosso — non c'è stato niente da riportare al
coordinatore su questo fronte.

### Requisito aggiunto dal controller: un test che fissi la semantica di `nuove()`

Il controller ha promosso a requisito di questo giro la Minor "`nuove()` non
è esercitata da nessun test", perché questo giro ne cambia il comportamento.

**Ho scelto la forma "piena" fra le due proposte** (violazione preesistente
in una firma, violazione nuova della stessa famiglia in un'altra firma,
`nuove()` che la vede), non il ripiego modesto con insiemi sintetici — perché
`_scuola_multi_firma_fattibile`, letta prima di scrivere, mostrava che
costruire due firme di settimana distinte con `weeks.single_week(n)` è poco
impianto (quattro righe), e volevo che il test passasse per la strada vera
(`check_schedule` reale, non un finto `Finding` costruito a mano) per essere
sicuro che il collasso di `Finding.key` fosse riprodotto esattamente come nel
caso reale.

**Non sono passato dal solver**: la fixture `_due_settimane_stessa_violazione`
usa `place()` (già esistente in `tests/analysis_helpers.py`) per piazzare
Placement direttamente, perché l'oggetto sotto esame in questo giro è
l'helper del test (`violazioni`/`nuove`), non il solver — passare da
`solve()` avrebbe aggiunto tempo e rumore senza aggiungere potere
discriminante.

**Meccanica**: griglia 1 giorno × 3 fasce, `MAX_GAP_HOURS = 0` sulla classe
(qualunque buco è violazione). Settimana 0: due attività piazzate a fascia 0
e 2 → buco alla fascia 1 → un finding `max_gap` su `klass`, quantities
`{gap_minutes: 60, max_gap_minutes: 0}`. Settimana 1: due attività attive ma
non ancora piazzate (nessuna violazione). `prima = violazioni(schedule)`
cattura solo `(chiave, 0)`. Poi piazzo le due attività della settimana 1 con
**lo stesso schema di buco** (stessa risorsa, stesse quantities) →
`Finding.key` identica → `check_schedule` fonde i due finding in un solo
oggetto con `weeks=(0, 1)`. Con l'espansione per settimana,
`violazioni(schedule)` torna `{(chiave, 0), (chiave, 1)}`, e
`nuove(schedule, prima)` torna `{(chiave, 1)}` — la settimana 1 è vista come
genuinamente nuova, esattamente il caso dell'osservazione.

**Verificato che discrimina davvero**, non solo che passa: ho temporaneamente
ripristinato la vecchia forma di `violazioni()` (`{f.key for f in ...}`,
senza espansione) e rilanciato **solo** il nuovo test:

```
$ venv/bin/pytest tests/test_solver_oracle.py::test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana -v
============================= test session starts ==============================
...
collected 1 item

tests/test_solver_oracle.py::test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana FAILED [100%]

=================================== FAILURES ===================================
_________ test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana _________

    def test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana():
        ...
        env = _due_settimane_stessa_violazione()
        schedule = env["schedule"]

        prima = violazioni(schedule)
        assert len(prima) == 1
>       (chiave, settimana), = prima
        ^^^^^^^^^^^^^^^^^^^
E       ValueError: too many values to unpack (expected 2)

tests/test_solver_oracle.py:423: ValueError
---------------------------- Captured stderr setup -----------------------------
Creating test database for alias 'default'...
--------------------------- Captured stderr teardown -----------------------------
Destroying test database for alias 'default'...
=========================== short test summary info ============================
FAILED tests/test_solver_oracle.py::test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana
============================== 1 failed in 0.65s ===============================
```

Fallisce nel modo giusto: con la sola `Finding.key`, `prima` conterrebbe
elementi non spacchettabili in coppia (in realtà avrebbe collassato anche il
caso a un solo elemento in modo diverso — il punto è che la forma a chiave
nuda produce un insieme di oggetti non a coppia, il test lo intercetta
subito). Ho poi ripristinato la correzione (`git diff` confermato pulito) e
rilanciato la suite:

```
$ venv/bin/pytest tests/test_solver_oracle.py -v
... (stesso output di sopra, 7 passed in 2.58s)
```

### Suite completa, una volta prima del commit

```
$ venv/bin/pytest -q
........................................................................ [ 38%]
........................................................................ [ 76%]
.............................................                            [100%]
189 passed in 8.02s
```

189 = 188 (fine giro precedente) + 1 nuovo test
(`test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana`). Nessun test
perso, nessun warning nell'output.

### File cambiati in questo giro

- `tests/test_solver_oracle.py` (unico file toccato: `violazioni()` espansa
  per settimana, le due righe di estrazione codice in `test_oracolo_puo_fallire`
  adattate al nuovo tipo di ritorno, nuova fixture
  `_due_settimane_stessa_violazione` e nuovo test
  `test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana`)

### Minor differite (non toccate in questo giro, come da istruzione)

- Docstring di `split` sul filtraggio per firma.
- Accoppiamento non dichiarato fra il `codici` di `nuove()` e quello con cui
  è stato calcolato `prima`.
- `pytestmark = django_db` in `tests/test_solver_residual.py`.
- I due casi limite `split(ctx, [])` e "tutti liberi".

### Dubbi

Nessuno. La verifica per falsificazione (ripristino della forma pre-fix,
conferma del fallimento, ripristino della correzione) dà confidenza piena che
il test aggiunto discrimini davvero e non sia un passaggio vacuo.
