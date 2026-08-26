### Task 3: ADR-018 — l'helper del residuo e l'oracolo differenziale

**Files:**
- Create: `domain/solver/residual.py`
- Modify: `tests/test_solver_oracle.py` (l'oracolo diventa differenziale)
- Test: `tests/test_solver_residual.py`

**Interfaces:**
- Consumes: `SolverContext.free` (l'insieme degli id muovibili).
- Produces:
  - `split(ctx, terms) -> (list[(peso, letterale)], int)` — `terms` è un
    iterabile di `(peso, id_attività, letterale)`
  - `residual_cap(ctx, terms, cap) -> (list[(peso, letterale)], int)`
  - `residual_floor(ctx, terms, floor) -> (list[(peso, letterale)], int)`
  - `any_free(ctx, activity_ids) -> bool`
  - in `tests/test_solver_oracle.py`: `violazioni(schedule) -> set` (era una
    lista) e `nuove(schedule, prima) -> set`

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_residual.py
"""ADR-018: i letterali delle attivita' congelate sono costanti note a build
time, quindi ogni espressione lineare si spezza in «parte costante + parte
libera». Sui tetti il residuo puo' essere negativo e va clampato a zero; sui
minimi garantiti no."""
import pytest

from domain.solver.residual import any_free, residual_cap, residual_floor, split

pytestmark = pytest.mark.django_db


class _Ctx:
    def __init__(self, free):
        self.free = set(free)


def test_split_separa_libere_e_congelate():
    ctx = _Ctx({1, 2})
    termini = [(60, 1, "x1"), (60, 2, "x2"), (60, 3, "x3"), (30, 4, "x4")]
    liberi, congelate = split(ctx, termini)
    assert liberi == [(60, "x1"), (60, "x2")]
    assert congelate == 90


def test_residual_cap_sottrae_il_consumo_delle_congelate():
    ctx = _Ctx({1})
    liberi, tetto = residual_cap(ctx, [(60, 1, "x1"), (60, 2, "x2")], 180)
    assert liberi == [(60, "x1")]
    assert tetto == 120


def test_residual_cap_clampa_a_zero_invece_di_andare_negativo():
    """Il caso di ADR-018: le congelate hanno gia' sforato. Il vincolo resta
    postabile e le libere non possono aggiungere nulla, ma il modello non
    diventa infattibile per colpa di una violazione preesistente."""
    ctx = _Ctx({1})
    liberi, tetto = residual_cap(ctx, [(60, 1, "x1"), (300, 2, "x2")], 180)
    assert liberi == [(60, "x1")]
    assert tetto == 0


def test_residual_floor_non_clampa():
    """Su un minimo garantito il residuo negativo e' corretto e va lasciato
    passare: significa che le congelate gia' bastano e il vincolo e' vacuo.
    Clamparlo a zero non cambierebbe nulla qui, ma clamparlo *dal basso* a un
    valore positivo imporrebbe alle libere un dovere gia' assolto."""
    ctx = _Ctx({1})
    liberi, soglia = residual_floor(ctx, [(1, 1, "x1"), (1, 2, "x2"), (1, 3, "x3")], 2)
    assert liberi == [(1, "x1")]
    assert soglia == 0
    _, soglia_vacua = residual_floor(ctx, [(1, 2, "x2"), (1, 3, "x3")], 1)
    assert soglia_vacua == -1


def test_any_free_e_la_regola_dell_implicazione():
    ctx = _Ctx({7})
    assert any_free(ctx, [7, 8]) is True
    assert any_free(ctx, [8, 9]) is False
    assert any_free(ctx, []) is False
```

- [ ] **Step 2: Eseguire i test e verificare che falliscano**

Run: `venv/bin/pytest tests/test_solver_residual.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'domain.solver.residual'`

- [ ] **Step 3: Scrivere `domain/solver/residual.py`**

```python
"""ADR-018 — l'input sporco non blocca il solver.

Un'attivita' congelata ha ctx.cells[aid] di cardinalita' uno e riceve comunque
AddExactlyOne: il suo letterale vale 1, ed e' noto al momento della
costruzione. Quindi ogni espressione lineare del modello si spezza
**esattamente** in «parte costante + parte libera», e da li' discendono due
casi soli.

Sui **tetti**: `costante + libere <= tetto` equivale a
`libere <= tetto - costante`, e quel residuo puo' essere negativo — e' il caso
in cui le congelate sono gia' in violazione. ADR-018 impone di clamparlo a
zero invece di lasciare il modello infattibile per colpa del passato.

Sui **minimi garantiti**: `costante + libere >= soglia` equivale a
`libere >= soglia - costante`, che non e' mai infattibile per colpa del
passato — se le congelate gia' bastano, il requisito e' vacuo. Nessun clamp."""


def split(ctx, terms):
    """terms: iterabile di (peso, id attivita', letterale).
    → (termini liberi come (peso, letterale), consumo delle congelate)."""
    free, frozen = [], 0
    for weight, aid, lit in terms:
        if aid in ctx.free:
            free.append((weight, lit))
        else:
            frozen += weight
    return free, frozen


def residual_cap(ctx, terms, cap):
    """Per un vincolo «<= cap». Il tetto residuo e' clampato a zero."""
    free, frozen = split(ctx, terms)
    return free, max(0, cap - frozen)


def residual_floor(ctx, terms, floor):
    """Per un vincolo «>= floor». Nessun clamp: una soglia residua <= 0
    significa che le congelate gia' bastano, ed e' corretto che il vincolo
    risulti vacuo."""
    free, frozen = split(ctx, terms)
    return free, floor - frozen


def any_free(ctx, activity_ids):
    """La regola dell'implicazione: un vincolo i cui letterali vengono tutti da
    attivita' congelate non si posta — e' un fatto, non una decisione."""
    return any(aid in ctx.free for aid in activity_ids)
```

- [ ] **Step 4: Rendere differenziale l'oracolo dei test**

In `tests/test_solver_oracle.py`, sostituire `violazioni` con:

```python
def violazioni(schedule, codici=CODICI):
    """L'insieme delle chiavi dei finding HARD nelle famiglie modellate.
    Un insieme, non una lista: il criterio di riuscita e' il **contenimento**
    (ADR-018), non l'uguaglianza."""
    return {f.key for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codici}


def nuove(schedule, prima, codici=CODICI):
    """I finding HARD comparsi **dopo** il solve. Il solver puo' anche
    riparare una violazione preesistente spostando un'attivita' libera: quello
    e' un successo, non una discrepanza, ed e' per questo che il criterio e'
    il contenimento e non l'uguaglianza."""
    return violazioni(schedule, codici) - prima
```

Poi sostituire ovunque `assert violazioni(...) == []` con
`assert violazioni(...) == set()`. Sono sei occorrenze, tutte su istanze che
partono pulite, quindi il valore atteso non cambia — cambia solo il tipo.

⚠ Non aggiungere ancora un test che parte da un input sporco: nessun builder
usa `residual_cap` finché non arriva l'ondata 3. Il primo test end-to-end di
ADR-018 nasce nel Task 6.

- [ ] **Step 5: Eseguire tutto**

Run: `venv/bin/pytest tests/test_solver_residual.py -v`
Expected: PASS (5 test)

Run: `venv/bin/pytest -q`
Expected: **186 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/residual.py tests/test_solver_residual.py tests/test_solver_oracle.py
git commit -m "$(cat <<'EOF'
feat(solver): ADR-018, il residuo e l'oracolo differenziale

residual_cap clampa a zero il tetto residuo, residual_floor non clampa
perche' su un minimo garantito il passato non puo' rendere infattibile
nulla. L'oracolo dei test passa da lista a insieme: il criterio e' il
contenimento dei finding, non l'uguaglianza, perche' il solver puo' anche
riparare una violazione preesistente.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

