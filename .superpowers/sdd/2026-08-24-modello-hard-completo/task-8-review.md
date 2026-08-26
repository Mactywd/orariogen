# Task 8 — `MAX_PRESENCE` — review

Diff rivisto: `review-7e88822..04c793f.diff` (un solo commit, `04c793f`, con il
trailer richiesto). Worktree pulito prima e dopo la review (`git status` vuoto).

## Conformità al piano e al brief

Tutto ciò che il brief chiedeva è stato fatto, e le tre correzioni al piano sono
applicate esattamente come decise.

| Requisito | Esito |
|---|---|
| `span` = giornata intera (`range(grid.slots_per_day)`), non `v.halves()` | ✅ e **verificato per mutazione** |
| Ruling 23 — clamp `max(cap, presenza_congelate)`, non `continue` | ✅ e **verificato che il `continue` rompe davvero l'oracolo differenziale** |
| Ruling 16 — niente `test_max_presence_sul_banco` | ✅ assente; i 5 casi `test_famiglia[max_presence-1..5]` esistono e girano |
| Ruling 24 — derivatore con `return 0/1` e docstring sulla vacuità | ✅ e **misurato in entrambe le direzioni** |
| Ruling 25 — `max(0, max_days - consumo)` a mano | ✅ non segnalato, come da istruzione |
| `tests/test_solver_registry.py` — solo la chiave nuova | ✅ (chiave + docstring); il test **morde** ancora |
| Commenti/docstring in italiano, identificatori in inglese | ✅ |
| `domain/analysis/` non importa `ortools` | ✅ (`grep -rn ortools domain/analysis/` → nessuno) |
| Nessuna primitiva del vocabolario reinventata | ✅ (`covered`, `day_active`, `frozen_occupies` usate; `_frozen_presence_minutes` è un calcolo a build time, gemello di `_frozen_gap_minutes`) |
| Suite non rossa né rimpicciolita (269+2 → 279+2) | ✅ |

Il rapporto dell'implementatore è **fedele**: ho riprodotto tutte e tre le prove
RED che dichiara e tutte e tre si comportano come scritto. La deviazione
dichiarata su `tests/test_solver_registry.py` è necessaria e minima; la
riscrittura di `test_max_presence_giorni_morde` è giustificata e il nuovo test è
genuino (vedi sotto).

## Verifiche eseguite

### 1. Lo `span` — il test discrimina

Mutato il builder sostituendo `range(grid.slots_per_day)` con `v.halves()`
(ciclo sulle due mezze giornate, stesso `cap_effettivo`). **10 esecuzioni su
10**, sempre lo stesso esito — nessuna intermittenza:

```
2 failed, 3 passed in 0.70s   (× 10)
FAILED tests/test_solver_max_presence.py::test_la_presenza_include_i_buchi_e_attraversa_il_pranzo
FAILED tests/test_solver_max_presence.py::test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata
E           assert (((5 - 0) + 1) * 60) <= 120
```

e sul banco a testimone: `FAILED tests/test_solver_witness.py::test_famiglia[max_presence-5]`.

Lo `span` della giornata intera è quindi quello giusto e il test lo dimostra.

### 2. Il clamp (Ruling 23) — presente, corretto, e distinto dal `continue`

**(a) Il `continue` rompe davvero l'oracolo differenziale.** Non l'ho solo
argomentato: rimesso `if _frozen_presence_minutes(...) > cap: continue` e fatto
girare una sonda differenziale (congelate 0-1-2, tetto 120, una libera):

```
PRIMA: [('max_presence', (1,), (), (('day', 0), ('max_minutes', 120), ('minutes', 180)))]
DOPO : [('max_presence', (1,), (), (('day', 0), ('max_minutes', 120), ('minutes', 240)))]
PLACEMENTS: {1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (0, 3)}
AssertionError: [('max_presence', (1,), (), (('day', 0), ('max_minutes', 120), ('minutes', 240)))]
```

`minutes` passa da 180 a 240: chiave diversa, **finding nuovo**. L'argomento del
brief è confermato sui dati.

**(b) Col clamp consegnato lo stesso scenario è pulito** (`dopo - prima == set()`),
e il test `test_adr018_clamp_impedisce_alla_libera_di_peggiorare_la_giornata`
fallisce col `continue` in **5 esecuzioni su 5** (`assert 3 <= 2`).

**(c) Il clamp è conservativo rispetto al checker su input pulito.** Sonde
costruite apposta, tutte verdi con `check_schedule` a zero finding `HARD`:

- attività da due fasce + una da una fascia, tetto 180 e `days: 1` → `{1: (0,3), 2: (0,2)}`, checker `[]`;
- congelata di un **altro docente** sulla stessa classe (la presenza è della *chiave*, non del docente) alla fascia 5, tetto 120 → libera alla 4, checker `[]`;
- congelata **multi-fascia** (3-4) + congelata (0), presenza congelate 300', tetto 120 → `PRIMA` e `DOPO` identici (`minutes: 300`), la libera resta dentro `[0,4]`.

Il clamp è sempre `>= cap`, quindi non può rendere il modello più infattibile
del vincolo pulito: nessun rischio ADR-018 introdotto dalla forma scelta.

### 3. Il ramo `days` — l'`INFEASIBLE` è per la ragione giusta

Il punto su cui il brief chiedeva la massima attenzione. Tre controlli:

- **Senza la riga `MAX_PRESENCE`**, lo stesso scenario è risolvibile:
  `SENZA VINCOLO: OPTIMAL {1: (1, 0), 2: (0, 0), 3: (2, 0)}`. Quindi
  l'`INFEASIBLE` non viene dalle indisponibilità né da altro.
- **Caso di controllo vicino**, tetto `days: 3` invece di 2: `OPTIMAL`, e
  `check_schedule` non trova nulla (`[]`). Il modello non è rotto in generale.
- **Il ramo è esercitato**: disabilitandolo (`if False and max_days is not None`)
  `test_max_presence_giorni_morde` fallisce in **5 esecuzioni su 5**
  (`assert 'OPTIMAL' == 'INFEASIBLE'`), e sul banco cade anche
  `test_famiglia[max_presence-5]`.

Il test riscritto è quindi genuino, non un `INFEASIBLE` di comodo.

### 4. Il derivatore (Ruling 24) — misurato in entrambe le direzioni

**Guardia troppo larga? No.** Eseguito `_derive_max_presence` su **40 seed**:
ritorna `0` solo **2 volte su 40** (seed 7 e 31), e in entrambi i casi per la
ragione legittima `giorni == 0` (il docente sorteggiato non compare in nessuna
attività). La seconda guardia (picco a giornata piena **e** giorni a ciclo
pieno) **non è mai scattata** in 40 seed — è difensiva, non un interruttore
generale. Nota di contorno che conferma che l'`and` è la congiunzione giusta:
seed 4 produce `{'max_minutes': 360, 'days': 2}` su griglia 3×6 (ramo minuti
vacuo, ramo giorni vincolante) e seed 30 `{'max_minutes': 240, 'days': 5}` su
5×6 (il contrario). Con un `or` entrambi sarebbero stati buttati via.

**Guardia troppo stretta?** Ho misurato il *potere vincolante reale*: per ogni
famiglia ho rimosso il builder da `BUILDERS` e contato su quanti dei 5 seed
`run_family` se ne accorge. `max_presence` morde su **2 seed su 5** (2 e 5).
Non è un'anomalia — è al di sopra della media del banco:

| famiglia | seed che mordono (su 5) |
|---|---|
| `max_hours` | 1 |
| `max_half_days` | 1 |
| `max_gap_hours` | 2 |
| `free_guaranteed` | 2 |
| `min_distribution` | 2 |
| `same_day_incompatible` | 2 |
| **`max_presence`** | **2** |
| `structural:unavailability` | 3 |

Quindi la guardia è allineata alla convenzione stabilita (vacuità
*strutturale*, non «il builder è catturabile»), e non introduce un
peggioramento. Il residuo di verdi non-probanti è una proprietà del banco, non
di questo task.

### 5. `tests/test_solver_registry.py` — modifica minima, e morde

Il diff aggiunge **solo** `ResourceTimeConstraint.Type.MAX_PRESENCE`
all'insieme atteso (più l'aggiornamento della docstring). Provato a togliere la
registrazione `@register(T.MAX_PRESENCE)`:

```
FAILED tests/test_solver_registry.py::test_i_builder_tradotti_finora - assert...
1 failed, 6 passed in 0.61s
```

Il test di copertura continua a mordere.

### 6. Ruling 16 — i cinque casi esistono

Nessun `test_max_presence_sul_banco` nel file (verificato), e la nota in testa
al modulo lo dichiara. I cinque casi della famiglia esistono e girano:

```
tests/test_solver_witness.py::test_famiglia[max_presence-1..5] PASSED
5 passed, 52 deselected
```

Nessuno dei cinque è saltato per vacuità.

### 7. Non determinismo

`tests/test_solver_max_presence.py + test_solver_witness.py + test_solver_registry.py`
lanciati **6 volte di seguito**: `66 passed, 2 skipped` tutte e sei. Suite intera
lanciata **4 volte**: identica. I 2 skip sono quelli preesistenti della baseline
(`arrival_departure`, seed 2 e 4), invariati.

## Osservazioni

Nessuna **Important**. Tre **Minor**, tutte su test/documentazione, nessuna sul
comportamento del builder.

### Minor 1 — la docstring di `test_la_presenza_include_i_buchi_e_attraversa_il_pranzo` afferma il falso, e il test non esercita la dimensione che il suo nome promette

La docstring (ereditata **verbatim dal piano**) dice che il solver «non può
metterle […] né alle fasce 3 e 4 (presenza due ore ma **a cavallo del
pranzo**)». È falso: con `morning_end_slot = 4`, le fasce 3 e 4 danno
`4 - 3 + 1 = 2` fasce = 120', che il tetto di 120' **ammette**. Il checker è
d'accordo.

Sonda (docente indisponibile ovunque tranne le fasce 3 e 4 del giorno 0, due
attività, tetto 120):

```
3&4 con tetto 120: OPTIMAL {1: (0, 4), 2: (0, 3)}   checker: []
```

Conseguenza pratica: ciò che il test cattura sotto mutazione non è il pranzo ma
lo `span` in generale — l'asserzione che salta è
`assert (((5 - 0) + 1) * 60) <= 120`, cioè le fasce **0 e 5**. La dimensione
«a cavallo del pranzo» resta non esercitata.

**Caso di controllo che invece la esercita davvero** (già scritto e verificato):
stesse due attività forzate alle fasce 3 e 4, tetto **60'**. Il checker misura
120' e boccia; uno `span` per mezza giornata misurerebbe 60' + 60' e
accetterebbe.

```
# builder consegnato
3&4 con tetto 60: INFEASIBLE {}
# builder mutato a v.halves()
3&4 con tetto 60: OPTIMAL {1: (0, 4), 2: (0, 3)}
# caso di controllo vicino: una sola attività, stesso tetto 60'
una sola, tetto 60: OPTIMAL {1: (0, 4)}
```

Il builder è **corretto** su questa dimensione: manca solo il test che la
dichiara. Rimedio: correggere la frase falsa della docstring e aggiungere il
caso a tetto 60' qui sopra.

### Minor 2 — il clamp `max(0, …)` del ramo `days` è portante ma non è coperto da nessun test

Nessuno dei cinque test mirati mette attività congelate **e** una riga con
`days`, quindi il caso `consumo > max_days` non è mai costruito. Sostituendo
`max(0, max_days - consumo)` con `max_days - consumo` la suite intera resta
verde:

```
$ venv/bin/pytest -q          # con la mutazione, senza la mia sonda
279 passed, 2 skipped
```

mentre la sonda (tre congelate su tre giorni distinti, `days: 2`, una libera)
mostra il difetto:

```
AssertionError: {'attivita': 4, 'libere': 1, 'variabili': 47, 'constraint': 25, ...}
assert 'INFEASIBLE' in ('OPTIMAL', 'FEASIBLE')
```

cioè esattamente l'«infattibile per colpa del passato» che ADR-018 vieta. Con
il codice consegnato la stessa istanza è `OPTIMAL` e l'oracolo differenziale è
pulito (`PRIMA` e `DOPO` entrambi
`[('max_presence_days', (1,), (), (('days', 3), ('max_days', 2)))]`).

Il codice è giusto; manca la rete. Un test di tre righe sul modello della sonda
chiude il buco.

### Minor 3 — `test_il_vincolo_non_si_posta_se_nulla_e_libero` è vacuo

Passa anche disattivando la rete di sicurezza che dice di provare. Sonda:
commentata la guardia `if not any(aid in ctx.free for aid in touching): continue`
in `domain/solver/builders/base.py`:

```
$ venv/bin/pytest tests/test_solver_max_presence.py::test_il_vincolo_non_si_posta_se_nulla_e_libero -q
1 passed in 0.56s
```

Motivo: anche postando il vincolo, `cap_effettivo` si clampa alla presenza delle
congelate e il ramo `days` forza a zero solo giornate che nessuna attività
libera può toccare — il modello resta risolvibile in entrambi i casi. È
documentazione, non verifica. Caso di controllo che invece morde: la stessa
mutazione della rete di sicurezza è catturata da altri test della suite (che
infatti la review del Task 6 aveva imposto). Rimedio possibile: o rinominarlo
per quello che è, o costruire un'istanza in cui postare il vincolo cambi
davvero l'esito.

## Esito della suite (verbatim)

Baseline dichiarata dal brief, 269 passed / 2 skipped. Dopo il Task 8, working
tree pulito, quattro esecuzioni:

```
279 passed, 2 skipped in 23.08s
279 passed, 2 skipped in 23.60s
279 passed, 2 skipped in 23.18s
279 passed, 2 skipped in 22.86s
```

File mirati + banco + registro, sei esecuzioni consecutive:

```
66 passed, 2 skipped in 13.08s
66 passed, 2 skipped in 12.89s
66 passed, 2 skipped in 12.79s
66 passed, 2 skipped in 12.83s
66 passed, 2 skipped in 12.84s
66 passed, 2 skipped in 12.89s
```

I due skip:

```
SKIPPED [1] tests/solver_harness.py:271: arrival_departure: derivazione vacua per il seed 2, ...
SKIPPED [1] tests/solver_harness.py:271: arrival_departure: derivazione vacua per il seed 4, ...
```

## Verdetto

**Il Task 8 si può chiudere.** Il builder è corretto su tutte le dimensioni che
ho saputo sondare — `span` sulla giornata intera (incluso il caso specifico del
pranzo, che il codice tratta bene anche se il test non lo esercita), clamp
ADR-018 su entrambi i rami, firme di settimana gestite dalla classe base,
attività multi-fascia, oracolo differenziale pulito su input sporco. Le tre
Ruling del brief sono applicate come decise, il registro e il banco sono a
posto, la suite è stabile e non è rimpicciolita.

Le tre osservazioni sono **Minor** e non richiedono un giro di correzione prima
della chiusura: nessuna riguarda il comportamento del codice consegnato, tutte
riguardano la forza probante di test già verdi. Se il controller preferisce
chiuderle subito, la più utile è la **Minor 2** (il clamp del ramo `days` non ha
rete), seguita dalla **Minor 1** (frase falsa nella docstring, più il test a
tetto 60' che è già scritto e verificato qui sopra). Entrambe sono lavoro da
pochi minuti e possono anche essere accodate al prossimo task.
