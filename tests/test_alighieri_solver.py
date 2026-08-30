"""L'Alighieri visto dal motore, all'ondata 1.

⚠ **Non è ancora il criterio di accettazione della spec.** Quello (§4) chiede
un dataset *stretto*: `OPTIMAL` con zero scarti, ma una sola aula o un solo
docente in meno e comincia a scartare. All'ondata 1 non c'è ancora una riga di
vincolo, quindi la tensione non c'è: qui si fissa che l'anagrafica **regge**
— capienza pulita, due fasi verdi, nessun finding che non sia lo stato di
partenza — e la tensione arriva con le famiglie."""

import pytest

from domain.analysis.capacity import analyze_capacity
from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Activity
from domain.solver.model import apply, solve
from domain.solver.rooms import apply_rooms, solve_rooms
from tests import alighieri

pytestmark = pytest.mark.django_db


def test_capienza_pulita():
    """Un banco che non passa l'analisi preventiva misura sé stesso, non il
    motore."""
    alighieri.build()
    assert analyze_capacity() == []


def test_su_schedule_vuoto_solo_attivita_non_piazzate():
    env = alighieri.build()
    findings = check_schedule(env["schedule"])
    assert {f.code for f in findings} == {"activity_unplaced"}
    assert len(findings) == Activity.objects.count() == 323


def test_le_due_fasi_chiudono_pulite():
    """🔑 La fase 2 senza rinunce **non è gratuita**: lo è diventata il
    2026-08-29, quando la fase 1 ha cominciato a contare le aule (ADR-021).
    Qui le sessantasei richieste d'aula si dividono fra due sedi, e la
    succursale non ha un `LAB-INF` su cui ripiegare."""
    env = alighieri.build()

    fase1 = solve(env["schedule"], workers=8)
    assert fase1.status == "OPTIMAL"
    assert fase1.unplaced == () or list(fase1.unplaced) == []
    apply(fase1, env["schedule"])

    richieste = Activity.objects.exclude(rooms=None).count()
    assert richieste == 66
    fase2 = solve_rooms(env["schedule"], workers=8)
    assert fase2.status == "OPTIMAL"
    assert len(fase2.assignments) == richieste
    assert list(fase2.unassigned) == []
    apply_rooms(fase2, env["schedule"])

    hard = [f for f in check_schedule(env["schedule"])
            if f.severity == Severity.HARD]
    assert hard == [], [f.message for f in hard[:5]]
