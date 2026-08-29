"""Il picco d'occupazione del **gruppo di aule**: la domanda che la fase 1 non
sapeva porsi.

La causale è di EDT alla lettera — *«il gruppo di aule ha raggiunto il suo
picco d'occupazione»*, famiglia `AffSco_UtilDiagnostic`, che è la diagnostica
del **piazzamento** e non dell'assegnazione. Cioè: in EDT le aule si contano
già mentre si piazza, e si *scelgono* dopo.

⚠ Non è il conteggio di una singola aula (quello è `structural:occupation`):
è il teorema di Hall su un insieme. Tre attività che chiedono ciascuna «LAB-FIS
oppure LAB-INF» non violano nessuna capienza singola, e tuttavia non stanno in
due aule."""
import pytest

from domain.analysis.checkers.room_pool import RoomPoolChecker
from domain.analysis.state import ScheduleState
from domain.models import Resource, ResourceUnavailability, Room
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _findings(env, resources=None):
    state = ScheduleState.build(env["schedule"])
    return list(RoomPoolChecker().check(state, resources=resources))


def _aula(nome, simultanee=1):
    return Room.objects.create(name=nome, simultaneous_capacity=simultanee)


def test_due_richieste_e_due_aule_non_sono_un_picco():
    env = mini_school()
    r1, r2 = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[r1, r2])
        place(env["schedule"], a, 0, 0)
    assert _findings(env) == []


def test_tre_richieste_sullo_stesso_pool_da_due():
    """Nessuna capienza singola è superata — l'aula non è «occupata», il
    *gruppo* ha raggiunto il picco."""
    env = mini_school()
    r1, r2 = _aula("LAB-FIS"), _aula("LAB-INF")
    ids = []
    for _ in range(3):
        a = make_activity(env["subject"], rooms=[r1, r2])
        place(env["schedule"], a, 0, 0)
        ids.append(a.id)
    (f,) = _findings(env)
    assert f.code == "room_group_peak"
    assert f.resources == (r1.pk, r2.pk)
    assert f.activities == tuple(sorted(ids))
    assert f.quantities["load"] == 3
    assert f.quantities["capacity"] == 2
    assert f.quantities["day"] == 0 and f.quantities["slot"] == 0
    assert "picco d'occupazione" in f.message


def test_il_violatore_e_il_sottoinsieme_non_l_unione():
    """La forma misurata sul Fermi: sull'**unione** la capienza basta, e il
    deficit vive dentro. Nominare l'unione manderebbe a smontare l'aula
    sbagliata."""
    env = mini_school()
    fis, inf, sci = _aula("LAB-FIS"), _aula("LAB-INF"), _aula("LAB-SCI")
    stretti = []
    for _ in range(3):
        a = make_activity(env["subject"], rooms=[fis, inf])
        place(env["schedule"], a, 0, 0)
        stretti.append(a.id)
    largo = make_activity(env["subject"], rooms=[inf, sci])
    place(env["schedule"], largo, 0, 0)
    (f,) = _findings(env)
    assert f.resources == (fis.pk, inf.pk)          # non sci
    assert f.activities == tuple(sorted(stretti))   # non largo
    assert (f.quantities["load"], f.quantities["capacity"]) == (3, 2)


def test_a_candidata_unica_non_duplica_l_occupazione():
    """Con una sola candidata la scelta è determinata, l'aula è già una chiave
    di occupazione e `structural:occupation` la nomina. Dirlo due volte
    manderebbe l'utente a cercare due problemi dove ce n'è uno."""
    env = mini_school()
    r1 = _aula("LAB-FIS")
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[r1])
        place(env["schedule"], a, 0, 0)
    assert _findings(env) == []


def test_la_candidata_unica_consuma_comunque_la_capienza():
    """Non nominarla non vuol dire non contarla: l'attività bloccata su
    LAB-FIS toglie quella capienza a chi sceglie fra le due."""
    env = mini_school()
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    sola = make_activity(env["subject"], rooms=[fis])
    place(env["schedule"], sola, 0, 0)
    scelgono = []
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[fis, inf])
        place(env["schedule"], a, 0, 0)
        scelgono.append(a.id)
    (f,) = _findings(env)
    assert f.resources == (fis.pk, inf.pk)
    assert f.activities == tuple(sorted([sola.id, *scelgono]))
    assert (f.quantities["load"], f.quantities["capacity"]) == (3, 2)


def test_la_capienza_simultanea_conta():
    env = mini_school()
    palestra, campo = _aula("PALESTRA", simultanee=2), _aula("CAMPO")
    for _ in range(3):
        a = make_activity(env["subject"], rooms=[palestra, campo])
        place(env["schedule"], a, 0, 0)
    assert _findings(env) == []          # 2 + 1 = 3 posti per 3 richieste


def test_celle_diverse_non_competono():
    env = mini_school()
    r1, r2 = _aula("LAB-FIS"), _aula("LAB-INF")
    for slot in range(3):
        a = make_activity(env["subject"], rooms=[r1, r2])
        place(env["schedule"], a, 0, slot)
    assert _findings(env) == []


def test_il_blocco_lungo_occupa_tutte_le_sue_fasce():
    """Un laboratorio da 3 ore compete su tre celle, non sul suo avvio."""
    env = mini_school()
    r1, r2 = _aula("LAB-FIS"), _aula("LAB-INF")
    lungo = make_activity(env["subject"], rooms=[r1, r2], slots=3)
    place(env["schedule"], lungo, 0, 0)
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[r1, r2])
        place(env["schedule"], a, 0, 2)
    (f,) = _findings(env)
    assert f.quantities["slot"] == 2
    assert lungo.id in f.activities


def test_l_aula_indisponibile_non_offre_posti():
    """Un'indisponibilità **rossa** toglie l'aula dal pool: due richieste su
    due aule di cui una chiusa non stanno."""
    env = mini_school()
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    ResourceUnavailability.objects.create(
        resource=Resource.objects.get(pk=inf.pk), day=0, slot=0, level="hard")
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[fis, inf])
        place(env["schedule"], a, 0, 0)
    (f,) = _findings(env)
    assert (f.quantities["load"], f.quantities["capacity"]) == (2, 1)


def test_l_indisponibilita_gialla_non_toglie_posti():
    """Opzionale vuol dire violabile: contarla come chiusa produrrebbe un
    finding `HARD` per un ostacolo che non è duro."""
    env = mini_school()
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    ResourceUnavailability.objects.create(
        resource=Resource.objects.get(pk=inf.pk), day=0, slot=0, level="optional")
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[fis, inf])
        place(env["schedule"], a, 0, 0)
    assert _findings(env) == []


def test_il_filtro_sulle_risorse_non_perde_il_finding():
    """`resources` è un'ottimizzazione: se il pool tocca una risorsa chiesta,
    il finding esce **intero**."""
    env = mini_school()
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(3):
        a = make_activity(env["subject"], rooms=[fis, inf])
        place(env["schedule"], a, 0, 0)
    (f,) = _findings(env, resources={inf.pk})
    assert f.resources == (fis.pk, inf.pk)
    assert _findings(env, resources={_aula("ALTRA").pk}) == []


def test_l_attivita_non_piazzata_non_compete():
    env = mini_school()
    r1, r2 = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[r1, r2])
        place(env["schedule"], a, 0, 0)
    make_activity(env["subject"], rooms=[r1, r2])     # mai piazzata
    assert _findings(env) == []


# --- l'integrazione con il dominio residuo ------------------------------
#
# ⚠ Il filtro `resources` di `trial_placements` sono le **chiavi di
# occupazione** dell'attività, e un'aula con due candidate non è una chiave
# (`activity_tokens` la mette fra i token solo a candidata unica). Senza
# allargarlo alle candidate dichiarate, S.P., il violatore di Hall e la
# classifica dei vincoli restano ciechi a questa famiglia: il checker gira e
# scarta ogni pool, perché nessuno tocca le risorse chieste.

def test_il_dominio_residuo_vede_il_picco_del_gruppo():
    from domain.analysis.domain_size import admissible_starts

    env = mini_school(days=1, slots=2)
    fis, inf = _aula("LAB-FIS"), _aula("LAB-INF")
    for _ in range(2):
        a = make_activity(env["subject"], rooms=[fis, inf])
        place(env["schedule"], a, 0, 0)
    libera = make_activity(env["subject"], rooms=[fis, inf])
    state = ScheduleState.build(env["schedule"])
    assert admissible_starts(libera, state, relaxed=True) == [(0, 1)]
