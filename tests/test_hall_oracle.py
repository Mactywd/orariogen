"""Il criterio di riuscita della fase 5, nelle due direzioni.

Direzione 1 — ogni finding dev'essere confermato: se la fase 5 dichiara un
insieme infattibile, il modello hard sulle stesse attivita' deve rispondere
INFEASIBLE. Un violatore inventato diventa un rosso.

Direzione 2, quella che vale di piu' — le istanze di `solver_harness` sono
**fattibili per costruzione**: hanno un testimone. Quindi la fase 5 su ognuna
di esse deve tacere. Qualunque finding e' un falso positivo *dimostrato*.

⚠ Questo misura la **precisione**, non il **richiamo**: la fase 5 e' incompleta
per costruzione (§3.4 della spec) e non c'e' un numero di richiamo da
promettere."""
import pytest

from domain.analysis.hall import analyze_hall
from domain.models import ResourceUnavailability
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school
from tests.solver_harness import build_witness

pytestmark = pytest.mark.django_db


def test_un_finding_e_confermato_dal_solver():
    env = mini_school()
    for day in (1, 2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert len(analyze_hall(env["schedule"])) == 1
    assert solve(env["schedule"], time_limit=30).status == "INFEASIBLE"


def test_il_solver_conferma_anche_il_confine():
    # Una fascia in piu': la fase 5 tace, e il solver deve trovare una
    # soluzione. Senza questa meta', il test sopra passerebbe anche con una
    # fase 5 che dichiara infattibile qualunque cosa.
    env = mini_school()
    for day in (2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for slot in range(1, 6):
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=1, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []
    assert solve(env["schedule"], time_limit=30).status in ("OPTIMAL", "FEASIBLE")


@pytest.mark.parametrize("seed", list(range(1, 41)))
def test_nessun_finding_su_un_istanza_fattibile_per_costruzione(seed):
    w = build_witness(seed)
    findings = analyze_hall(w.schedule)
    assert findings == [], (
        f"falso positivo dimostrato sul seed {seed}: esiste un testimone, "
        f"quindi nessun insieme puo' essere deficiente — "
        f"{[(f.binding_label, f.n_activities) for f in findings]}")
