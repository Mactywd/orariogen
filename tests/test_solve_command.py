"""Il comando `manage.py solve`."""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import Placement, ResourceTimeConstraint
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db


def _esegui(schedule, **kw):
    from io import StringIO
    out = StringIO()
    try:
        call_command("solve", schedule=schedule.pk, lavoratori=1, stdout=out, **kw)
        errore = None
    except CommandError as exc:
        errore = str(exc)
    return out.getvalue(), errore


def test_il_comando_piazza_e_riporta_i_criteri():
    env = mini_school(days=2, slots=2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    testo, errore = _esegui(env["schedule"], applica=True)
    assert errore is None, testo
    assert "Stato: OPTIMAL" in testo
    assert "Criteri, in ordine di priorità" in testo
    assert "minuti_scartati" in testo and "attivita_scartate" in testo
    assert "Calcolo terminato" in testo
    assert Placement.objects.filter(schedule=env["schedule"]).count() == 3


def test_senza_applica_non_scrive_niente():
    """⚠ Un solve sovrascrive l'orario di una scuola: il default non può
    essere scrivere."""
    env = mini_school(days=2, slots=2)
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])

    testo, errore = _esegui(env["schedule"])
    assert errore is None
    assert "Niente è stato scritto" in testo
    assert not Placement.objects.filter(schedule=env["schedule"]).exists()


def test_gli_scarti_sono_nominati_e_il_comando_fallisce():
    """Nella forma di EDT: non «infeasible», ma quali attività restano fuori,
    con materia, classe e docente. Ed exit code ≠ 0, per la CI."""
    env = mini_school(days=1, slots=2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    testo, errore = _esegui(env["schedule"])
    assert "Attività scartate (1, 1h00)" in testo
    assert "Italiano (1h00)" in testo and "1A" in testo
    assert errore is not None and "1 attività non piazzate" in errore


def test_una_violazione_residua_e_dichiarata_dopo_applica():
    """Con un vincolo già violato dal passato, `--applica` scrive comunque e
    **dichiara** cosa resta violato: un orario illegale è uno stato ammesso,
    ed è il comportamento di EDT."""
    from domain.models import Activity

    env = mini_school(days=2, slots=2)
    for slot in (0, 1):
        congelata = make_activity(env["subject"], teachers=[env["teacher"]],
                                  classes=[env["klass"]])
        Activity.objects.filter(pk=congelata.pk).update(
            immobility=Activity.Immobility.FIXED)
        Placement.objects.create(schedule=env["schedule"], activity=congelata,
                                 day=0, start_slot=slot)
    # le due congelate sforano da sole il tetto del giorno 0; la libera trova
    # posto nel giorno 1, quindi si piazza — e la violazione del passato resta
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HOURS,
        params={"day_minutes": 60})

    testo, errore = _esegui(env["schedule"], applica=True)
    assert errore is None, testo
    assert "Violazioni residue" in testo
    assert "massimo di ore nella giornata superato" in testo


def test_il_comando_sul_fermi():
    """La scala vera: 284 attività su una griglia stretta, dal comando.
    ⚠ Come per `test_fermi_intero_misurato`, il Fermi esercita cinque famiglie
    su ventisei — questo test misura il **comando**, non il modello."""
    from tests import fermi

    dataset = fermi.build()
    testo, errore = _esegui(dataset["schedule"], applica=True, limite=120)
    assert errore is None, testo
    assert "Stato: OPTIMAL" in testo
    assert "Attività: 284" in testo
    assert "Attività scartate" not in testo
    assert "Violazioni residue" not in testo
    assert Placement.objects.filter(schedule=dataset["schedule"]).count() == 284
    print("\n" + testo)
