# tests/test_solver_witness.py
"""Il banco di prova. Il test di copertura e' quello che tiene: registrare un
builder senza il suo derivatore diventa impossibile, invece di dipendere dalla
diligenza di chi lo scrive."""
import pytest

from domain.solver import builders  # noqa: F401 — forza la registrazione
from domain.solver.registry import BUILDERS
from tests.solver_harness import DERIVERS, build_witness, run_family

pytestmark = pytest.mark.django_db

SEEDS = [1, 2, 3, 4, 5]


def test_ogni_builder_ha_un_derivatore():
    mancanti = sorted(str(k) for k in BUILDERS if k not in DERIVERS)
    assert mancanti == [], (
        "questi builder non hanno un banco di prova: " + ", ".join(mancanti))


def test_il_testimone_ha_piu_di_una_firma_di_settimana():
    """Se questa proprieta' si perdesse, ogni test del banco tornerebbe cieco
    sulla dimensione «settimane» — che e' esattamente il modo in cui il
    difetto del D.T.B. e' passato inosservato."""
    w = build_witness(seed=1)
    assert len(w.signatures) >= 2


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("key", sorted(DERIVERS, key=str))
def test_famiglia(key, seed):
    run_family(key, seed)
