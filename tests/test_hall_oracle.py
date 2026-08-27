"""Il criterio di riuscita della fase 5, nelle due direzioni.

Direzione 1 — ogni finding dev'essere confermato dal solver. ⚠ Il criterio e'
cambiato col **pezzo 3**: il modello ha smesso di pretendere il piazzamento
(`AddExactlyOne` e' diventato `somma(celle) == piazzata`), quindi un insieme
deficiente non risponde piu' INFEASIBLE — **rinuncia**. La conferma si chiede
allora a due modelli, e la seconda meta' e' piu' forte di quella di prima:

- `allow_unplaced=False` e' il modello di prima dello scarto, quello che il suo
  docstring chiama «il modo di chiedere: questo vincolo morde?». Deve dare
  INFEASIBLE;
- col modello vero, che lo scarto lo ammette, i **minuti scartati** devono
  essere esattamente quelli che la fase 5 ha dichiarato mancanti. Non solo
  «c'e' una deficienza»: la sua **aritmetica**.

Un violatore inventato diventa un rosso in entrambe.

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
from tests.solver_harness import costruisci_tutte_le_famiglie

pytestmark = pytest.mark.django_db


def test_un_finding_e_confermato_dal_solver():
    env = mini_school()
    for day in (1, 2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1

    assert solve(env["schedule"], time_limit=30,
                 allow_unplaced=False).status == "INFEASIBLE"

    rinuncia = solve(env["schedule"], time_limit=30)
    assert rinuncia.status in ("OPTIMAL", "FEASIBLE")
    assert rinuncia.stats["minuti_scartati"] == (
        findings[0].required_minutes - findings[0].placeable_minutes)


def test_il_solver_conferma_anche_il_confine():
    # Una fascia in piu': la fase 5 tace, e il solver deve piazzare **tutto**.
    # Senza questa meta', il test sopra passerebbe anche con una fase 5 che
    # dichiara infattibile qualunque cosa.
    #
    # ⚠ Col pezzo 3 il vecchio `status in (OPTIMAL, FEASIBLE)` non discrimina
    # piu': lo scarto ammesso rende OPTIMAL anche l'istanza deficiente qui
    # sopra, quindi quell'asserzione da sola era diventata incapace di
    # fallire. Cio' che separa le due istanze non e' lo stato ma la
    # **rinuncia**: 60 minuti la', zero qui.
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

    assert solve(env["schedule"], time_limit=30,
                 allow_unplaced=False).status in ("OPTIMAL", "FEASIBLE")

    pieno = solve(env["schedule"], time_limit=30)
    assert pieno.status in ("OPTIMAL", "FEASIBLE")
    assert pieno.stats["minuti_scartati"] == 0


@pytest.mark.parametrize("seed", list(range(1, 41)))
def test_nessun_finding_su_un_istanza_fattibile_per_costruzione(seed):
    """⚠ Il testimone dev'essere **denso**, non nudo.

    Fino alla review finale questo test girava su `build_witness(seed)`, dove
    `ResourceTimeConstraint.objects.count() == 0`, `SubjectConstraint == 0` e
    `ResourceUnavailability == 0`: le righe le creano i **derivatori**, che
    `build_witness` non chiama. Quaranta semi che esercitavano lo stesso
    sottoinsieme dello spike a cinque vincoli — ed e' per questo che il falso
    positivo di `admissible_starts` sui checker non monotoni (Critical 1) e'
    arrivato indisturbato all'ultima porta.

    `costruisci_tutte_le_famiglie` porta le righe di tutte e ventisei le
    famiglie e **asserisce** che il testimone le soddisfi insieme: il
    testimone resta un testimone, quindi ogni finding qui e' un falso positivo
    dimostrato. Non chiama il solver — alla fase 5 non serve, e pagarlo
    costerebbe due ordini di grandezza."""
    w, _poteri, _codici = costruisci_tutte_le_famiglie(seed)
    findings = analyze_hall(w.schedule)
    assert findings == [], (
        f"falso positivo dimostrato sul seed {seed}: esiste un testimone, "
        f"quindi nessun insieme puo' essere deficiente — "
        f"{[(f.binding_label, f.n_activities) for f in findings]}")
