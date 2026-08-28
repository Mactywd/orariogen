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


def test_il_comando_arbitra_fra_le_popolazioni():
    """`--popolazione` e `--tolleranza`: la separazione di EDT da riga di
    comando. Il rendiconto dichiara base e tetto, perché un tetto che non si
    vede è un risultato che l'utente non sa spiegarsi."""
    from domain.models import QualityCriterion
    P = QualityCriterion.Population

    env = mini_school(days=2, slots=2)
    a1 = make_activity(env["subject"], teachers=[env["teacher"]],
                       classes=[env["klass"]])
    a2 = make_activity(env["subject"], teachers=[env["teacher"]],
                       classes=[env["klass"]])
    Placement.objects.create(schedule=env["schedule"], activity=a1, day=0, start_slot=0)
    Placement.objects.create(schedule=env["schedule"], activity=a2, day=1, start_slot=0)
    QualityCriterion.objects.create(kind=QualityCriterion.Kind.FREE_HALF_DAYS,
                                    population=P.TEACHERS, rank=1)
    QualityCriterion.objects.create(kind=QualityCriterion.Kind.REGULARITY,
                                    population=P.CLASSES, rank=2)

    testo, errore = _esegui(env["schedule"], popolazione=P.TEACHERS, tolleranza=0)
    assert errore is None, testo
    assert "Arbitrato fra popolazioni" in testo
    assert "Si ottimizza: teachers" in testo
    assert "Perdita tollerata per classes: 0" in testo
    assert "regularity_classes: base 1, tetto 1" in testo
    # il criterio sacrificato non compare fra i livelli della catena
    criteri = testo.split("Criteri, in ordine di priorità")[1].split("Arbitrato")[0]
    assert "free_half_days_teachers" in criteri
    assert "regularity_classes" not in criteri


def test_il_comando_dichiara_quando_non_c_e_una_base():
    """Un tetto non posto cambia il risultato: si dichiara, mai in silenzio."""
    from domain.models import QualityCriterion
    P = QualityCriterion.Population

    env = mini_school(days=2, slots=2)
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    QualityCriterion.objects.create(kind=QualityCriterion.Kind.REGULARITY,
                                    population=P.CLASSES, rank=1)

    testo, errore = _esegui(env["schedule"], popolazione=P.TEACHERS)
    assert errore is None, testo
    assert "nessun tetto" in testo
    assert "non è completo" in testo


def test_il_rendiconto_distingue_l_ottimo_non_dimostrato_dal_divario():
    """🔑 «Ottimo non dimostrato» da solo non è un'informazione: non distingue
    chi ha finito da chi non ha cominciato. Con il limite inferiore le due
    frasi diventano diverse, e quella a divario zero **toglie** il consiglio di
    alzare `--limite` invece di darlo a vuoto.

    I quattro casi vengono dalla misura sul Fermi: `gaps` dimostra 0;
    `isolated` **arriva** a 0 e non lo dimostra; `regularity` si ferma a 236
    con limite inferiore 18; un livello scaduto senza soluzione non conclude."""
    from domain.management.commands.solve import _esito
    from domain.solver.objective import Esito

    def riga(**kw):
        return _esito(Esito(**kw).as_dict())

    assert riga(nome="gaps_all", valore=0, ottimo=True,
                secondi=1.0, limite=0) == "0"
    assert riga(nome="isolated_all", valore=0, ottimo=False,
                secondi=15.0, limite=0) == "0 (è l'ottimo, non dimostrato)"
    assert riga(nome="regularity_all", valore=236, ottimo=False,
                secondi=15.0, limite=18) == (
        "236 (ottimo non dimostrato, non sotto 18)")
    assert riga(nome="x", valore=None, ottimo=False,
                secondi=15.0, limite=None) == "non concluso"


def test_i_lavoratori_si_dichiarano():
    """⚠ Cambiano il **risultato**, non solo il tempo: a 15 s per livello un
    lavoratore dà `regularity 359` dove quattro danno 236. Un numero di qualità
    senza il numero di lavoratori non è confrontabile con nessun altro."""
    env = mini_school(days=2, slots=2)
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    testo, _ = _esegui(env["schedule"])
    assert "(1 in ricerca)" in testo
