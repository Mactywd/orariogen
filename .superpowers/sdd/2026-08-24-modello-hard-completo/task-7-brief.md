### Task 7: I tre minimi garantiti

**Files:**
- Modify: `domain/solver/builders/time_counting.py`
- Modify: `tests/solver_harness.py` (tre derivatori)
- Test: `tests/test_solver_time_minimums.py`

**Interfaces:**
- Consumes: `ResourceBuilder`, `ctx.vocab`.
- Produces: `MinDistributionBuilder` (`T.MIN_DISTRIBUTION`),
  `ArrivalDepartureBuilder` (`T.ARRIVAL_DEPARTURE`), `FreeGuaranteedBuilder`
  (`T.FREE_GUARANTEED`).

**⚠ Nessuno dei tre usa `residual_cap`, ed è corretto.** Sono minimi
garantiti: le attività congelate contribuiscono *a favore* dentro le variabili
derivate, e una soglia già soddisfatta dal passato rende il vincolo vacuo, mai
infattibile (spec §3.1). Chiamare `residual_cap` qui sarebbe un difetto.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
# tests/test_solver_time_minimums.py
"""I tre vincoli orari che chiedono un minimo invece di imporre un tetto. Il
test che conta e' quello su FREE_GUARANTEED: il checker conta le mezze
giornate libere **solo sui giorni che hanno attivita'**, e un builder che le
contasse su tutti i giorni accetterebbe orari che il checker boccia."""
import pytest

from domain.models import ResourceTimeConstraint
from domain.solver.model import apply, solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import run_family
from tests.test_solver_oracle import violazioni

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("tipo", [T.MIN_DISTRIBUTION, T.ARRIVAL_DEPARTURE,
                                  T.FREE_GUARANTEED])
def test_minimi_sul_banco(tipo, seed):
    run_family(tipo, seed)


def test_min_distribution_morde():
    """Quattro ore, distribuite su almeno tre giorni."""
    env = mini_school()
    for _ in range(4):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": 60, "min_days": 3})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert len({day for (day, _s) in soluzione.placements.values()}) >= 3


def test_free_guaranteed_non_regala_mezze_giornate_dei_giorni_vuoti():
    """La trappola, dritta. Griglia 5x6 con meta' giornata a 4; una sola
    attivita', quindi quattro giorni su cinque sono **completamente** vuoti.

    Il checker conta le mezze giornate libere solo sui giorni con attivita':
    con una sola attivita' ce n'e' esattamente **una** (l'altra meta' del
    giorno in cui si lavora). Un builder che sommasse su tutti i giorni ne
    conterebbe nove, e dichiarerebbe soddisfatto un vincolo che il checker
    boccia. Chiediamo tre mezze giornate libere: dev'essere INFEASIBLE."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 3})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_free_guaranteed_soddisfacibile_resta_soddisfacibile():
    """Il complemento del test sopra: con una sola mezza giornata richiesta la
    stessa istanza dev'essere fattibile, e pulita per il checker."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.FREE_GUARANTEED,
        params={"free_half_days": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], {"free_guaranteed"}) == set()
```

- [ ] **Step 2: Eseguire e verificare il fallimento**

Run: `venv/bin/pytest tests/test_solver_time_minimums.py -q`
Expected: FAIL — `nessun derivatore` sui test parametrizzati, e i due test
mirati falliscono perché nessun vincolo è ancora postato.

- [ ] **Step 3: Aggiungere i tre builder a `time_counting.py`**

```python
@register(T.MIN_DISTRIBUTION)
class MinDistributionBuilder(ResourceBuilder):
    """MinDistributionChecker conta i giorni in cui la risorsa lavora almeno
    `min_minutes_per_day`, e ne vuole almeno `min_days`."""
    TYPE = T.MIN_DISTRIBUTION

    def post(self, ctx, model, row, rep):
        sm, v, key = ctx.grid.slot_minutes, ctx.vocab, row.resource_id
        soglia = row.params["min_minutes_per_day"]
        qualificati = []
        for day in range(ctx.grid.days_per_cycle):
            occ = [v.occupied(key, day, s, signature=rep)
                   for s in range(ctx.grid.slots_per_day)]
            q = model.NewBoolVar(f"qualifies_{key}_{rep}_{day}")
            model.Add(sm * sum(occ) >= soglia).OnlyEnforceIf(q)
            model.Add(sm * sum(occ) < soglia).OnlyEnforceIf(q.Not())
            qualificati.append(q)
        model.Add(sum(qualificati) >= row.params["min_days"])


@register(T.ARRIVAL_DEPARTURE)
class ArrivalDepartureBuilder(ResourceBuilder):
    """⚠ Non servono variabili di prima/ultima fascia.

    «La prima fascia e' >= not_before» equivale a «nessuna occupazione prima di
    not_before»; «l'ultima e' < not_after» a «nessuna occupazione da not_after
    in poi». E il giorno vuoto risulta conforme gratis, che e' esattamente cio'
    che ArrivalDepartureChecker fa con il suo `compliant += 1`."""
    TYPE = T.ARRIVAL_DEPARTURE

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        not_before = row.params.get("not_before_slot")
        not_after = row.params.get("not_after_slot")
        proibite = [s for s in range(ctx.grid.slots_per_day)
                    if (not_before is not None and s < not_before)
                    or (not_after is not None and s >= not_after)]
        conformi = []
        for day in range(ctx.grid.days_per_cycle):
            viola = model.NewBoolVar(f"ad_viola_{key}_{rep}_{day}")
            lits = [v.occupied(key, day, s, signature=rep) for s in proibite]
            if lits:
                model.AddMaxEquality(viola, lits)
            else:
                model.Add(viola == 0)
            conforme = model.NewBoolVar(f"ad_ok_{key}_{rep}_{day}")
            model.Add(conforme + viola == 1)
            conformi.append(conforme)
        model.Add(sum(conformi) >= row.params["days"])


@register(T.FREE_GUARANTEED)
class FreeGuaranteedBuilder(ResourceBuilder):
    """⚠ La trappola di questa famiglia, e la ragione per cui il termine
    `giorno_attivo` compare nella congiunzione.

    FreeGuaranteedChecker itera `for day, slots in days.items()`, e `days`
    contiene **solo i giorni con attivita'**: un giorno completamente vuoto
    contribuisce **zero** mezze giornate libere, non due. Sommare
    `not half_active` su tutte le mezze giornate ne conterebbe di piu',
    renderebbe `>= soglia` piu' facile, e farebbe accettare orari che il
    checker boccia — la direzione sbagliata."""
    TYPE = T.FREE_GUARANTEED

    def post(self, ctx, model, row, rep):
        v, key = ctx.vocab, row.resource_id
        giorni_liberi, mezze_libere = [], []
        for day in range(ctx.grid.days_per_cycle):
            attivo = v.day_active(key, day, signature=rep)
            libero = model.NewBoolVar(f"freeday_{key}_{rep}_{day}")
            model.Add(libero + attivo == 1)
            giorni_liberi.append(libero)
            for half, span in enumerate(v.halves()):
                if not len(span):
                    continue
                meta = v.half_active(key, day, half, signature=rep)
                libera = model.NewBoolVar(f"freehalf_{key}_{rep}_{day}_{half}")
                # libera  <->  giorno attivo AND mezza giornata scarica
                model.AddBoolAnd([attivo, meta.Not()]).OnlyEnforceIf(libera)
                model.AddBoolOr([attivo.Not(), meta]).OnlyEnforceIf(libera.Not())
                mezze_libere.append(libera)
        minimo_giorni = row.params.get("free_days", 0)
        if minimo_giorni:
            model.Add(sum(giorni_liberi) >= minimo_giorni)
        minimo_mezze = row.params.get("free_half_days", 0)
        if minimo_mezze and mezze_libere:
            model.Add(sum(mezze_libere) >= minimo_mezze)
```

- [ ] **Step 4: Aggiungere i tre derivatori a `tests/solver_harness.py`**

```python
@deriver(RT.MIN_DISTRIBUTION, {"min_distribution"})
def _derive_min_distribution(w):
    """Chiede i giorni effettivamente lavorati nella firma **peggiore**: e' il
    massimo che il testimone garantisce in tutte le settimane."""
    klass = w.rng.choice(w.env["classes"])
    peggiore = min(len(w.resource_days(klass.pk, rep)) for rep, _ in w.signatures)
    ResourceTimeConstraint.objects.create(
        resource=klass, type=RT.MIN_DISTRIBUTION,
        params={"min_minutes_per_day": w.env["grid"].slot_minutes,
                "min_days": peggiore})


@deriver(RT.ARRIVAL_DEPARTURE, {"arrival_departure"})
def _derive_arrival_departure(w):
    """La finestra osservata: la prima fascia usata e l'ultima piu' uno.
    Chiede che **tutti** i giorni siano conformi, e nel testimone lo sono."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    prima, ultima = grid.slots_per_day, 0
    for rep, _ in w.signatures:
        for _day, fasce in w.resource_days(docente.pk, rep).items():
            prima, ultima = min(prima, fasce[0]), max(ultima, fasce[-1])
    if prima > ultima:
        prima, ultima = 0, grid.slots_per_day - 1
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.ARRIVAL_DEPARTURE,
        params={"not_before_slot": prima, "not_after_slot": ultima + 1,
                "days": grid.days_per_cycle})


@deriver(RT.FREE_GUARANTEED, {"free_guaranteed"})
def _derive_free_guaranteed(w):
    """I giorni e le mezze giornate libere osservati nella firma peggiore.
    ⚠ Le mezze giornate si contano **solo sui giorni con attivita'**, come fa
    il checker: derivare altrimenti produrrebbe un testimone che il checker
    stesso boccia, e run_family lo direbbe al punto 1."""
    grid = w.env["grid"]
    docente = w.rng.choice(w.env["teachers"])
    min_giorni, min_mezze = grid.days_per_cycle, grid.days_per_cycle * 2
    for rep, _ in w.signatures:
        giorni = w.resource_days(docente.pk, rep)
        liberi = grid.days_per_cycle - len(giorni)
        mezze = 0
        for _day, fasce in giorni.items():
            mezze += not any(f < grid.morning_end_slot for f in fasce)
            mezze += not any(f >= grid.morning_end_slot for f in fasce)
        min_giorni, min_mezze = min(min_giorni, liberi), min(min_mezze, mezze)
    ResourceTimeConstraint.objects.create(
        resource=docente, type=RT.FREE_GUARANTEED,
        params={"free_days": min_giorni, "free_half_days": min_mezze})
```

- [ ] **Step 5: Eseguire**

Run: `venv/bin/pytest tests/test_solver_time_minimums.py -q`
Expected: PASS (18 test)

Run: `venv/bin/pytest -q`
Expected: **243 passed**

- [ ] **Step 6: Commit**

```bash
git add domain/solver/builders/time_counting.py tests/solver_harness.py tests/test_solver_time_minimums.py
git commit -m "$(cat <<'EOF'
feat(solver): MIN_DISTRIBUTION, ARRIVAL_DEPARTURE, FREE_GUARANTEED

I tre minimi garantiti, che per costruzione non hanno bisogno del residuo
di ADR-018: una soglia gia' soddisfatta dalle congelate e' vacua, mai
infattibile.

FREE_GUARANTEED porta la trappola: il checker conta le mezze giornate
libere solo sui giorni con attivita', quindi un giorno vuoto ne vale zero,
non due. Sommare su tutti i giorni accetterebbe orari illegali. Il test
mirato lo dimostra chiedendo tre mezze giornate su un'istanza che ne ha
una sola.

ARRIVAL_DEPARTURE si semplifica: nessuna variabile di prima/ultima fascia,
solo l'assenza di occupazioni nella zona proibita.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

