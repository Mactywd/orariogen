# Task 10 — giro di correzione 1

La review ha dato **DONE_WITH_CONCERNS**: nessun Critical, la traduzione è
corretta, la Ruling 40 è stata riprodotta e la sua correzione verificata. Restano
tre Important e cinque Minor, **tutti da chiudere in questo giro**. Non sono
rimandabili: tre di loro sono affermazioni scritte nel codice che nessun test
difende, ed è il difetto ricorrente di questo branch.

Lavori nel worktree `.claude/worktrees/modello-hard-completo` e **non ne esci**.
Test con `venv/bin/pytest` dalla radice. Stato di partenza: **323 passed,
3 skipped**, cinque file modificati più `tests/test_solver_subject_buckets.py`
non tracciato. Non fare commit.

Prima di toccare qualsiasi cosa leggi
`.superpowers/sdd/2026-08-24-modello-hard-completo/task-10-brief.md` (il brief
originale, con la tabella a quattro rami) e il fondo di `progress.md`
(Rulings 40-47).

## Important 1 — i dieci test di banco sono duplicati

`tests/test_solver_witness.py::test_famiglia` parametrizza già su
`sorted(DERIVERS, key=str) × [1..5]`: registrare i due derivatori genera **già**
i dieci casi. `test_secchi_sul_banco` li rifà. Prova aritmetica della review:
297 → 323 = +26 = 16 test scritti nel file + 10 generati da `test_famiglia`.
Costo 2,96 s su 31 s di suite.

Rimuovi il blocco (e l'import di `run_family` se resta inutilizzato) e metti in
testa al docstring del modulo la stessa nota ⚠ che hanno già
`tests/test_solver_sites.py` e `tests/test_solver_max_presence.py` — copiane la
forma, non inventarne una nuova.

⚠ `tests/test_solver_time_counting.py` ne ha ancora due: sono residui anteriori
alla Ruling 16, **non un precedente da imitare**. Non toccarli in questo giro.

## Important 2 — `_derive_same_half_day` crea una riga inviolabile al seed 2

Al seed 2 la griglia ha mezze giornate larghe **2 fasce**, e fra le attività
della coppia (classe, materia) ce n'è una di durata 2 con `respects_breaks`, che
riempie da sola l'intera mezza giornata: la seconda non può mai raggiungerla,
`len(la) > 1` è irraggiungibile, e `SameHalfDayChecker` non può emettere nulla.
Il derivatore restituisce comunque `1`, quindi `run_family` **non salta** e il
caso è un verde che non può fallire.

È la terza forma di vacuità, e nasce da una dimensione che nessun derivatore
aveva ancora dovuto guardare: **la larghezza del secchio contro le durate**.

Aggiungi la terza guardia: le due attività **più corte** della coppia devono
starci in *qualche* mezza giornata, cioè

```
min(durate) + seconda_minima(durate) <= max(morning_end_slot,
                                            slots_per_day - morning_end_slot)
```

Aggiungi **la guardia analoga anche a `_derive_same_day`** (secchio = giornata,
larghezza `slots_per_day`): lì la vacuità è latente ma oggi non morde (la review
ha misurato 5/5 righe violabili su tutti i seed), e due righe adesso valgono più
di una regressione silenziosa dopo.

Nella docstring di `_derive_same_half_day` scrivi **anche** il limite
strutturale, che oggi è implicito: il secchio mezza giornata è due volte più
fine di quello giornata, quindi una soluzione qualsiasi lo soddisfa per caso più
spesso, e il potere vincolante è strutturalmente più basso — 8/30 misurato
contro 20/30 della famiglia esistente `SAME_DAY`.

⚠ La guardia è una condizione **necessaria, non esatta**: non modella
l'allineamento agli intervalli. Dichiaralo, e **verifica** che funzioni: dopo la
correzione il seed 2 di `SAME_HALF_DAY` deve **saltare** (skip onesto), non
passare. Riporta il nuovo conteggio di skip.

## Important 3 — il quarto ramo è coperto solo per la materia A

`_post_cross`, ramo `fa=1, fb=1`, azzera i letterali liberi di A **e** di B.
Mutante di prova della review: togliendo il ciclo su `lb`, **l'intera suite
resta verde**. `test_adr018_a_diverso_b_entrambe_congelate_piu_libera_di_a`
mette una libera di A soltanto.

Aggiungi la copertura del lato B: una libera di **B** accanto alle due congelate
(nello stesso test o in uno simmetrico). Poi **verifica per mutazione** che il
test nuovo fallisca togliendo il ciclo su `lb`, e riporta l'esito. Ripristina il
codice e controlla con `git diff` che non resti traccia della mutazione.

## Minor 1 — la guardia caduta `if not la or not lb`

Il vecchio `SameDayBuilder` aveva `if not a or not b: continue`; `_post_cross`
non ce l'ha più. È **semanticamente esatta** — il checker emette solo
`if la and lb`, e con un lato vuoto tutti e quattro i rami sono vacui — e vale,
misurata sul banco, fino a **−12,3% variabili / −16,1% constraint** (seed 1: 46
chiamate su 48 hanno almeno un lato vuoto). Sul Fermi vale zero, perché
`tests/fermi.py` non crea alcun `SubjectConstraint`.

Rimettila, con il motivo per cui è esatta (non «è un'ottimizzazione», ma «il
checker non può emettere nulla con un lato vuoto, quindi ogni ramo è vacuo»).

## Minor 2 — `KIND` senza assert

`_BucketIncompatible` ha l'assert su `TYPE` ma non su `KIND`, e
`vocabulary.bucket_of` tratta **ogni** `kind != "day"` come mezza giornata: una
sottoclasse che dimentichi `KIND` prende silenziosamente la semantica mezza
giornata invece di rompersi. Stesso argomento dell'assert su `TYPE`, un livello
più sotto. Aggiungi `assert self.KIND in ("day", "half")`.

## Minor 3 — la docstring del gate di riga promette più di quanto mantiene

Rimosso il gate di `SubjectBuilder.build`, la suite resta **interamente verde**:
`test_il_vincolo_non_si_posta_se_nulla_e_libero` passa oggi per il
`if not free: return` di `_post_separable`, non per il gate. Il gate è
semanticamente neutro e si tiene, ma la docstring deve dire **cos'è** — un
short-circuit, non l'invariante che difende ADR-018.

## Minor 4 — `TwoDaysBuilder` con A = B non è coperto

`_derive_two_days` fa `if a.pk == b.pk: continue`, e nessun test mirato crea una
riga con A = B. Il path funziona (la review l'ha verificato a mano: due congelate
ai giorni 0 e 1 più una libera → OPTIMAL, la libera va al giorno 4), ma la
docstring di `TwoDaysBuilder` fa un'affermazione **specifica** su quel caso e
nulla la difende. Scrivi il test.

## Minor 5 — la conseguenza dichiarata del quarto ramo non è esercitata

Il docstring di `_post_cross` avverte in ⚠ che il quarto ramo **può rendere il
modello infattibile** se una libera non ha altro posto dove andare, e dichiara
che è voluto (è ciò che ADR-018 concede testualmente). Nessun test esibisce
quell'`INFEASIBLE`. Una proprietà scritta per non essere rilitigata deve avere il
suo test: costruiscilo.

## Alla fine

`venv/bin/pytest -q` per intero. Attesi: 323 − 10 (duplicati) = **313**, meno
quelli che passano a skip per Important 2, più quelli che aggiungi. **Riporta i
numeri che misuri**, e spiega ogni scostamento dal conto.

Rapporto in cinque punti:

1. cosa hai cambiato, finding per finding;
2. le **verifiche per mutazione** che hai fatto e il loro esito (Important 3 in
   particolare: il test nuovo fallisce davvero senza il ciclo su `lb`?);
3. il nuovo conteggio di skip e quali seed saltano, con il motivo;
4. i numeri finali della suite;
5. **cosa non hai fatto o non hai verificato**, senza arrotondare.
