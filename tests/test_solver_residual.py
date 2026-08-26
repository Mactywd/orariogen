"""ADR-018: i letterali delle attivita' congelate sono costanti note a build
time, quindi ogni espressione lineare si spezza in «parte costante + parte
libera». Sui tetti il residuo puo' essere negativo e va clampato a zero; sui
minimi garantiti no."""
import pytest

from domain.solver.residual import (any_free, frozen_occupies, residual_cap,
                                    residual_floor, split)

pytestmark = pytest.mark.django_db


class _Ctx:
    def __init__(self, free, by_cell=None, states=None):
        self.free = set(free)
        self.by_cell = by_cell or {}
        self.states = states or {}


class _State:
    def __init__(self, activities):
        self.activities = activities


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


def test_frozen_occupies_vero_se_una_congelata_tocca_la_cella():
    """Una variabile derivata (half_active, day_active) che una congelata
    forza a 1 e' essa stessa una costante — e' il caso positivo."""
    ctx = _Ctx(free={2}, by_cell={("k", 0, 1): [(1, "x1")]})
    assert frozen_occupies(ctx, "k", 0, [0, 1, 2]) is True


def test_frozen_occupies_falso_se_solo_libere_toccano_la_cella():
    """Nessuna congelata: la variabile dipende solo da letterali liberi e
    resta un termine della somma, non un consumo."""
    ctx = _Ctx(free={2}, by_cell={("k", 0, 1): [(2, "x2")]})
    assert frozen_occupies(ctx, "k", 0, [0, 1, 2]) is False


def test_frozen_occupies_falso_se_la_cella_e_vuota():
    ctx = _Ctx(free=set(), by_cell={})
    assert frozen_occupies(ctx, "k", 0, [0, 1, 2]) is False


def test_frozen_occupies_rispetta_la_firma():
    """Con `rep` dato, una congelata di un'altra firma non conta: la
    congelata deve essere attiva nella firma richiesta, come fa
    ScheduleState.build(schedule, week=rep) per il checker."""
    ctx = _Ctx(free=set(), by_cell={("k", 0, 1): [(1, "x1")]},
              states={"rep": _State(activities={2: object()})})
    assert frozen_occupies(ctx, "k", 0, [1], rep="rep") is False
    ctx.states["rep"].activities[1] = object()
    assert frozen_occupies(ctx, "k", 0, [1], rep="rep") is True
