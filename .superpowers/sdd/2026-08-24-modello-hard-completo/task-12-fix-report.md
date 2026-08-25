# Task 12 — report del giro di correzione

Worktree `modello-hard-completo`. Suite finale: **354 passed, 4 skipped**
(`venv/bin/pytest -q`, sia con `-p no:randomly` sia senza) — 351 della
baseline + 3 test nuovi (`test_weekly_order_impone_la_prima_occorrenza_
orientamento_invertito`, `test_adr018_ramo_disgiuntivo_vieta_la_libera_di_b_
sotto_lo_status_quo`, `test_adr018_ramo_disgiuntivo_vieta_anche_il_
pareggio`), 0 skip nuovi. Nessun commit, nessun push. `domain/analysis/` non
toccato (`grep -rn ortools domain/analysis/` → nessun risultato).

File modificati:
- `domain/solver/builders/subject_order.py` — il Critical, Minor 2, docstring
  riscritte (spiegazione del ramo disgiuntivo, Minor 1).
- `tests/solver_harness.py` — Important 2 (docstring seed 5), Important 4
  (assert), Minor 3 (`_pos_bounds` docstring).
- `tests/test_solver_subject_order.py` — Important 1, Important 3, il test
  che difende il Critical.
- `CLAUDE.md` — punto 1: nuova voce «Ancora aperto» sul tie-break di
  `_placed_of`.

---

## 1. Critical — il pareggio che cambia l'argmin

Applicata la correzione minima del brief: nel ramo disgiuntivo, il divieto
e' ora **per attivita' libera** (`v.pos(aid) >= FA + 1` / `v.pos(bid) >= FB +
1`), non piu' sul solo minimo aggregato (`prima_a >= FA` / `prima_b >= FB`).
`prima_a >= FA` diventa implicato e non si posta piu' come vincolo a se'
(era diventato ridondante, e tenerlo avrebbe mascherato le mutazioni).

Docstring riscritta: la frase «`Finding.key` resta identico alla baseline»
e' ora giustificata dal divieto per attivita' (vero per costruzione), non
piu' da `prima_a >= FA` (falso sotto pareggio). Il costo consapevole del
divieto piu' ampio (si vietano anche i pareggi che non avrebbero cambiato
l'argmin) e' dichiarato, con rimando alla voce nuova di CLAUDE.md.

**Test**: `test_adr018_ramo_disgiuntivo_vieta_anche_il_pareggio` — la sonda
della review (ClassPartition + due ClassPart sulla stessa classe, libera di
A su una parte, congelata di A sull'altra, congelata di B prima di tutte;
forza la libera nella cella della congelata di A). Attende INFEASIBLE.

**Mutazione**: ripristinato `model.Add(prima_a >= FA).OnlyEnforceIf(...)` +
`model.Add(prima_b >= FB).OnlyEnforceIf(...)` al posto dei due cicli per
attivita'. Risultato: **1 failed, 8 passed** —
`test_adr018_ramo_disgiuntivo_vieta_anche_il_pareggio` rosso (OPTIMAL invece
di INFEASIBLE), tutti gli altri verdi. Nessun altro test cattura questa
mutazione: e' isolata correttamente sul test che la difende.

## 2. Important 1 — `prima_b >= FB` indifeso

Aggiunto un gemello di `test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo`:
`test_adr018_ramo_disgiuntivo_vieta_la_libera_di_b_sotto_lo_status_quo`. A
differenza dell'originale, qui A non ha **nessuna** libera (solo
`a_frozen`): il ramo `riparato` resta bloccato per costruzione (`prima_a` e'
fissa a `FA`, non puo' scendere sotto la posizione forzata di `b_free`), cosi'
la prova isola il congiunto su B senza la via di fuga della riparazione che
avrebbe permesso ad `a_free` di soddisfare la parte "riparato" del modello.
`b_frozen` piazzata a pos 2 (non pos 0, per avere spazio sotto cui forzare
`b_free`); forza `b_free` a pos 0 e attende INFEASIBLE.

Ho anche aggiornato l'assert dell'originale
`test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo` da `>= (2, 0)` a
`> (2, 0)`, perche' dopo la correzione del Critical il vincolo reale e'
`pos >= FA + 1`, non piu' `pos >= FA`: l'assert precedente era ancora vero
ma piu' debole di quanto il builder garantisce ora.

**Mutazione**: rimosso il ciclo `for bid in b: ...` (mantenuto quello su
`a`). Risultato: **1 failed, 8 passed** — solo
`test_adr018_ramo_disgiuntivo_vieta_la_libera_di_b_sotto_lo_status_quo`
rosso (OPTIMAL invece di INFEASIBLE); `test_adr018_ramo_disgiuntivo_vieta_
anche_il_pareggio` resta verde (esercita solo il lato A), confermando che le
due proprieta' sono difese da test distinti e indipendenti.

## 3. Important 2 — la docstring del seed 5 diceva il falso

Riscritto il capoverso in `_derive_weekly_order` (`tests/solver_harness.py`):
non piu' «la guardia geometrica vede solo la geometria della coppia» come
causa del non-mordere, ma la causa vera — il banco chiede «risolvi col
builder acceso e guarda se la soluzione e' pulita», e CP-SAT restituisce da
solo una soluzione che rispetta le quattro righe del seed 5 (tutte
**davvero violabili**, non vacue). La proprieta' di generosita' della
guardia geometrica resta enunciata, ma separata e non piu' spacciata per
causa del seed 5. Nessun numero misurato riportato in docstring (Ruling 50);
il seed e' nominato come identificatore del caso, non come statistica.

Nessun test dedicato richiesto dal brief per questo punto (e' una
correzione di prosa); la proprieta' "il seed 5 morde nella forma
avversaria" e' comunque coperta indirettamente: `test_famiglia`
(`tests/test_solver_witness.py`) esercita tutti i cinque seed della
famiglia con `run_family`, che ora userebbe la forma "risolvi e guarda"
descritta correttamente.

## 4. Important 3 — il test «mordente» non mordeva

`test_weekly_order_impone_la_prima_occorrenza` riscritto in forma
**avversaria**: costruisce il modello, forza esplicitamente due attivita' di
A a posizioni tarde (12, 18) e due di B a posizioni presto (0, 1) — la
violazione diretta della riga — e attende INFEASIBLE. Aggiunto anche
`test_weekly_order_impone_la_prima_occorrenza_orientamento_invertito`, forma
«risolvi e asserisci» ma con l'orientamento invertito rispetto all'ordine
di creazione della fixture (richiede Matematica, creata per seconda, prima
di Italiano, creata per prima): copre il modo di sbagliare complementare,
un builder che vieta *tutto* incondizionatamente (INFEASIBLE sempre)
supererebbe la prova avversaria ma fallirebbe qui, perche' qui serve che un
piazzamento legale esista davvero.

**Mutazione** (`post()` reso completamente no-op, `return` come prima
istruzione): sui 9 test del file, **7 falliscono, 2 passano**:

```
FAILED test_weekly_order_impone_la_prima_occorrenza
FAILED test_weekly_order_impone_la_prima_occorrenza_orientamento_invertito
FAILED test_weekly_order_posta_per_firma_di_settimana
FAILED test_adr018_ramo_secco_vieta_la_libera_dopo_la_congelata
FAILED test_adr018_ramo_disgiuntivo_mantiene_lo_status_quo
FAILED test_adr018_ramo_disgiuntivo_vieta_la_libera_di_b_sotto_lo_status_quo
FAILED test_adr018_ramo_disgiuntivo_vieta_anche_il_pareggio
7 failed, 2 passed
```

I due che restano verdi sono `test_weekly_order_con_a_uguale_b_non_vincola_
nulla` e `test_weekly_order_materia_assente_non_crea_vincoli`: sono test di
**guardia** (verificano che una condizione interna a `post()` — A=B, materia
assente — faccia uscire senza postare nulla), non test di "il vincolo
morde". Con `post()` interamente disattivato dal `return` iniziale, il
comportamento osservabile per quei due scenari e' identico a quello con la
guardia intatta (in entrambi i casi non si posta nulla), quindi
legittimamente non possono distinguere questa mutazione — non e' la
mutazione che li riguarda (le loro mutazioni sono "rimuovi solo la propria
guardia", gia' verificate nei rispettivi docstring).

Contando solo sui **sei** test originali della baseline pre-Task-12-fix (gli
stessi sei nominati dalla review): `impone_la_prima_occorrenza` (ora rosso,
prima verde), `con_a_uguale_b` (verde, guardia — invariato), `materia_
assente` (verde, guardia — invariato), `posta_per_firma` (rosso, invariato),
`ramo_secco` (rosso, invariato), `ramo_disgiuntivo_mantiene_lo_status_quo`
(rosso, invariato) → **4/6 rossi**, non 6/6. Non ho raggiunto 6/6: i due
verdi restanti sono per costruzione guard-test che questa specifica
mutazione (disattivazione totale di `post()`) non puo' far cadere senza
farli smettere di testare cio' che dichiarano di testare (la guardia
specifica, non il "mordere" del vincolo). Includendo i tre test nuovi
aggiunti in questo giro, il totale sale a **7/9** rossi sotto la stessa
mutazione — un miglioramento netto rispetto ai 3/6 originali, ma il
sotto-insieme "guardia" resta strutturalmente non discriminante per questa
mutazione, ed e' corretto che lo sia.

## 5. Important 4 — precondizione taciuta del derivatore

Aggiunto in testa al corpo di `_derive_weekly_order` (dopo il docstring,
prima del primo uso di `w.env`):

```python
assert not ClassPart.objects.exists(), (
    "_derive_weekly_order filtra su klass.pk: con le parti, le "
    "occorrenze legate alla sola parte sfuggono al derivatore e non "
    "al checker")
```

sullo stesso modello di `_capienza_secchio` (`tests/solver_harness.py:720`).
Nessuna generalizzazione agli altri derivatori (materiale del Task 17, come
da brief). Non ho scritto un test dedicato: come per `_capienza_secchio`
(che ha lo stesso pattern e nessun test lo difende), l'assert e' una rete di
sicurezza contro un testimone futuro, non una proprieta' oggi osservabile —
`ClassPart.objects.exists()` e' sempre `False` nell'harness corrente
(`grep -n "ClassPart\|parts=" tests/solver_harness.py` → solo l'import e i
due assert). La suite completa (354 passed, 4 skipped) conferma che
l'assert non spara su nessun seed/famiglia esistente.

## 6. I tre Minor

- **Minor 1**: riscritto il capoverso `FA is None or FB is None` nel
  docstring del builder con il testo corretto: `FA`/`FB` contano solo le
  congelate (quelle che il solver non puo' toccare), "a"/"b" del builder
  (tutte le attivita' della materia in firma) sono gia' garantiti non vuoti
  dalla guardia sopra ma possono non contenere congelate; e se una delle due
  manca, qualunque INFEASIBLE che segua e' un divieto di peggiorare anche
  quando la baseline del checker non e' pulita per via di una libera gia'
  piazzata (non piu' la frase falsa «solo se la materia fosse del tutto
  assente»).
- **Minor 2**: `NewIntVar(0, days*slots, ...)` → `days*slots - 1`, su
  entrambe le variabili (`prima_a`, `prima_b`). Verificato che la suite
  resta verde (il vincolo di dominio non era mai stringente, essendo fissato
  da `AddMinEquality`): 354 passed dopo la modifica.
- **Minor 3**: aggiunta la subordinata a `_pos_bounds` in
  `tests/solver_harness.py` — la struttura a prodotto vale «finche' nessun
  pre-filtro taglia per coppia (giorno, fascia)», nominando
  `UnavailabilityBuilder.restrict` come il pre-filtro che romperebbe
  l'invariante, e notando che la decomposizione resterebbe comunque un
  rilassamento (dalla parte generosa) se accadesse.

Nessuno dei tre Minor richiede un test di mutazione dedicato (nessuna
proprieta' comportamentale nuova dichiarata: Minor 1 e 3 sono correzioni di
prosa, Minor 2 e' un bound mai stringente — confermato dalla suite verde
prima e dopo).

---

## Tabella delle mutazioni provate

| # | Mutazione | Test che cade | Esito |
|---|---|---|---|
| 1 | Ramo disgiuntivo: `prima_a >= FA` / `prima_b >= FB` al posto dei due cicli per attivita' | `test_adr018_ramo_disgiuntivo_vieta_anche_il_pareggio` | **Rosso** (OPTIMAL invece di INFEASIBLE); 1 failed, 8 passed — isolato |
| 2 | Rimosso `for bid in b: ...` (tenuto `for aid in a: ...`) | `test_adr018_ramo_disgiuntivo_vieta_la_libera_di_b_sotto_lo_status_quo` | **Rosso**; 1 failed, 8 passed — isolato, `..._pareggio` resta verde |
| 3 | `post()` interamente no-op (`return` come prima riga) | 7 dei 9 test del file | **7 failed, 2 passed** — i 2 verdi sono guard-test che questa mutazione non puo' discriminare per costruzione |

Tutte le mutazioni sono state applicate e verificate dal vivo (non solo
ragionate), e ripristinate subito dopo da una copia di riserva
(`/tmp/.../scratchpad/subject_order.py.orig`); il file finale sul disco e'
quello con la correzione, verificato con `git diff` e con la suite completa
verde.

## Verifica finale

```
$ venv/bin/pytest -q
354 passed, 4 skipped
$ venv/bin/pytest -q -p no:randomly
354 passed, 4 skipped
$ grep -rn ortools domain/analysis/
(nessun risultato)
$ git status --porcelain
 M CLAUDE.md
 M domain/solver/builders/__init__.py
 M tests/solver_harness.py
 M tests/test_solver_registry.py
?? domain/solver/builders/subject_order.py
?? tests/test_solver_subject_order.py
```

Nessun commit, nessun push, come richiesto.
