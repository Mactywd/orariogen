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
