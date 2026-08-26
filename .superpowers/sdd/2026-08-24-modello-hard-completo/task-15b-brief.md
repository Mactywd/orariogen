# Task 15b — i quattro `PARTS_*`

Implementatore. Worktree `modello-hard-completo`, HEAD `3eda06b`. Python:
`venv/bin/pytest`. Baseline: **379 passed, 6 skipped**. Docstring e commenti
in italiano senza accenti, identificatori in inglese. `domain/analysis/` **non
si tocca mai**.

Il Task 15a ha gia' fatto entrare le parti nel banco (`w.env["parts"]`,
un'attivita' per parte, e l'helper `_chiavi_unita`). Qui restano i quattro
builder.

Piano: sezione **Task 15** (riga 3400), Step 2, 4, 5 — **salta lo Step 1**,
gia' fatto. ⚠ Il derivatore del piano ha un difetto che lo rende **sempre
vacuo**: vedi §3.

## 0. Leggi prima

1. `domain/analysis/checkers/subject_constraints.py`: `_PartsOrder` e le sue
   quattro sottoclassi (righe 230-283), `_is_class_level`, `_half`.
   **E' l'autorita'.**
2. `domain/solver/builders/subject_order.py` e `subject_buckets.py` — lo stile
   dei builder di materia e i trattamenti ADR-018 gia' adottati.
3. `domain/solver/residual.py` — `any_free`.
4. `tests/solver_harness.py` — `_chiavi_unita`, e i derivatori d'ordine gia'
   scritti (`_derive_weekly_order`, `_derive_imposed_succession`,
   `_derive_half_day_gap`) come modello di stile.

Due trappole che il piano segnala e che confermo leggendo il codice:

- **⚠ Il secchio dei due omogenei e' diverso.** `_PartsOrder.bucket` torna
  `pl.day`; `PartsHomogeneousHalfChecker` lo **sovrascrive** con la mezza
  giornata. Quindi `_H` = **mezza giornata**, `_AB` = **giornata**. E' l'unica
  differenza fra i due, e invertirla non fa fallire niente di ovvio: scrivi un
  test che la distingue (vedi §4).
- **⚠ `_PartsOrder.violations` usa solo `a`**, mai `b`. La materia B non entra.

## 1. Le tre semantiche, e perche' la traduzione e' **esatta**

Il checker raggruppa per secchio, ordina per `(fascia, etichetta, id)`, salta
i secchi che non hanno **entrambe** le etichette, e poi:

| MODE | violazione |
|---|---|
| `before` | `max(fasce di parte) > min(fasce di classe)` |
| `after` | `min(fasce di parte) < max(fasce di classe)` |
| `homogeneous` | piu' di **una** transizione nella sequenza di etichette |

La traduzione del piano — clausole a coppie `AddBoolOr([xp.Not(), xc.Not()])`
sulle celle dello stesso secchio — e' **esatta**, non conservativa, e nella
docstring va detto con la dimostrazione:

- `before`: vietare ogni coppia con `sp > sc` equivale a «ogni fascia di parte
  `<=` ogni fascia di classe», che equivale a `max_parte <= min_classe`.
- `after`: simmetrico.
- `homogeneous`: «al piu' una transizione» nella sequenza ordinata significa
  che le etichette sono `P…PC…C` **oppure** `C…CP…P`, cioe' tutte le parti
  prima di tutte le classi **oppure** il contrario — esattamente la
  disgiunzione che il booleano `prima_le_parti` per secchio esprime.
  ⚠ Il pareggio di fascia fra una parte e una classe **non e' realizzabile**:
  un'attivita' di classe occupa la classe e tutte le sue parti, quindi
  confliggerebbe sull'occupazione. Dillo, e' cio' che rende l'equivalenza
  esatta invece che quasi.

## 2. ADR-018 — il piano non ne ha, e serve

Le clausole `AddBoolOr([xp.Not(), xc.Not()])` sono la stessa forma di
`ForbiddenSequenceBuilder` (subject_buckets.py). Vale la Ruling 59: **una
clausola i cui letterali vengono tutti da attivita' congelate non si posta —
e' un fatto, non una decisione**. Usa `any_free(ctx, (id_parte, id_classe))`
prima di postare, e riprendi la formula «un fatto, non una decisione» nel
commento.

⚠ Per il modo **omogeneo** non basta: li' la clausola e' sotto
`OnlyEnforceIf`, quindi una coppia di congelate gia' in violazione
falsificherebbe **un ramo** del booleano; se entrambi i rami vengono
falsificati da coppie congelate, il modello diventa INFEASIBLE per colpa del
passato. Saltare le coppie tutte-congelate risolve anche questo, e va
spiegato: il booleano resta libero, e i piazzamenti liberi si dispongono
attorno.

⚠ Con **una sola** delle due congelate la clausola resta e forza a zero il
letterale libero: e' un **divieto**, che ADR-018 concede anche quando rende il
modello INFEASIBLE (stessa proprieta' gia' scritta per
`ForbiddenSequenceBuilder`).

Dove metterlo: nuovo file `domain/solver/builders/subject_parts.py`, aggiunto
all'import di `domain/solver/builders/__init__.py`.

## 3. I derivatori — quello del piano e' **sempre vacuo**

⚠⚠ `_derive_parts` nel piano **non restituisce niente**. `run_family` fa
`potere = d.fn(w)` e poi `if not potere: pytest.skip(...)`: con `None` tutte
e quattro le famiglie salterebbero **sempre**, su ogni seed, e i venti test
del banco passerebbero come skip. Sarebbe la forma piu' pura del «successo
travestito» che la convenzione sul potere vincolante esiste per impedire.

Riscrivilo:

- una funzione comune parametrica su `(tipo, kind)`, con `kind` = `"day"` per
  `PARTS_BEFORE_CLASS`, `PARTS_AFTER_CLASS`, `PARTS_BEFORE_OR_AFTER_CLASS_AB`
  e `"half"` per `PARTS_BEFORE_OR_AFTER_CLASS_H`;
- filtro sull'unita' con `_chiavi_unita(w, klass)`, non su `klass.pk`;
- **per firma di settimana**: un secchio si valuta con le sole attivita'
  attive in quella firma, perche' e' cosi' che il checker lo vede. Una riga si
  crea solo se il testimone la soddisfa in **ogni** firma;
- **guardia di violabilita'**: serve almeno un secchio, in almeno una firma,
  che contenga **entrambe** le etichette — altrimenti il checker salta ogni
  secchio e la riga e' inviolabile. Senza questa guardia si creano righe che
  nessun piazzamento puo' violare, e il banco le conta come successi;
- **accumula** su tutte le classi e le materie (non solo `classes[0]`, non
  solo la prima materia buona), e **restituisci il conteggio**.

Misura tu, prima di dichiarare fatto: per ognuna delle quattro famiglie, su
almeno 20 seed, quante righe crea, quanti testimoni viola (**deve essere
zero**) e su quanti seed **morde** col builder spento. Il modo pulito di
spegnere il builder e' `monkeypatch.setattr(<Builder>, "post", lambda *a,
**k: None)` in una sonda usa-e-getta: non toccare il sorgente e non
riscrivere il derivatore dentro la sonda — una sonda che ne riscrive una
copia misura la copia (Ruling 98). I numeri vanno nel **report**, non nelle
docstring (Ruling 50).

## 4. I test — `tests/test_solver_subject_parts.py`

Niente `test_parts_sul_banco`: `test_solver_witness.py::test_famiglia` li
genera gia' (Ruling 16, ottava applicazione). Copia in testa al modulo la nota
⚠ che sta negli altri file di test del solver.

**Forma obbligatoria (Ruling 85)**: il test che dimostra che il vincolo morde
si scrive con `build_model` + `model.Add(ctx.x[...] == 1)` **forzando la
violazione** e attendendo `INFEASIBLE`. Mai «risolvi e guarda la soluzione»:
i test di questo task nel piano sono scritti proprio cosi', e per giunta con
un `if gg == gi:` che li rende vacui quando il solver mette le due attivita'
in giorni diversi. Non copiarli.

Servono almeno:

1. `before` morde: parte **dopo** classe nello stesso giorno → INFEASIBLE.
2. `before` legale: parte prima → FEASIBLE.
3. `after` morde, e legale (specularmente).
4. **omogeneo, l'interlacciatura**: parte, classe, parte nello stesso secchio
   → INFEASIBLE; e le stesse tre in ordine `P P C` → FEASIBLE. E' il test che
   distingue «al piu' una transizione» da «tutte le parti prima».
5. **⚠ `_H` contro `_AB`, il test che li separa**: una configurazione legale
   per la giornata e illegale per la mezza giornata (o viceversa), verificata
   in **entrambi** i tipi. Se scambiando `KIND` fra i due builder nessun test
   diventa rosso, il test non c'e'. **Verificalo per mutazione**: scambia i
   due `KIND` e mostra quale test cade.
6. **ADR-018**: una parte e una classe **entrambe congelate** in violazione,
   piu' una libera. Il modello **non** dev'essere INFEASIBLE. Asserzione
   **strutturale** (fissa la libera in una cella legale e chiedi FEASIBLE),
   non «risolvi e guarda dove e' finita».

**Criterio di mutazione (Ruling 89)**: ogni test che afferma la **presenza**
di un vincolo dev'essere rosso con `post()` reso no-op; quelli che affermano
un'**assenza** vanno difesi da una mutazione mirata. Nel report elenca ogni
mutazione con l'esito.

## 5. Chiusura

- `venv/bin/pytest -q`: **379 + i tuoi**, e **6 skipped**. ⚠ Uno skip in piu'
  significa che un derivatore e' vacuo su un seed del banco: misuralo e
  riportalo, non aggiustare il test.
- Aggiungi le quattro chiavi a `tests/test_solver_registry.py` e aggiorna la
  docstring.
- **Non committare, non pushare.** Report in
  `.superpowers/sdd/2026-08-24-modello-hard-completo/task-15b-report.md`.
- Se il brief contraddice il codice, **vince il codice**: segnalalo (nel
  Task 15a il brief diceva sei occorrenze di un pattern e ne erano nove).
