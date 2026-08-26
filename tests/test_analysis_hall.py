"""La fase 5: il sottoinsieme infattibile. Meta' dei casi sono negativi, e
contano di piu' — il difetto temuto e' il falso positivo, che manda l'utente a
smontare vincoli sani."""
import pytest

from domain.analysis.capacity import analyze_capacity
from domain.analysis.hall import STATEMENT_SINGOLA, analyze_hall
from domain.models import (
    Activity, ActivityMaterialRequirement, Material, ResourceUnavailability, Teacher,
)
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _blocca(resource, giorni=(), celle=()):
    """Indisponibilita' hard: giornate intere e/o singole (giorno, fascia)."""
    for day in giorni:
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=resource, day=day, slot=slot, level="hard")
    for day, slot in celle:
        ResourceUnavailability.objects.create(
            resource=resource, day=day, slot=slot, level="hard")


def test_sette_lezioni_in_sei_fasce():
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))       # resta il solo giorno 0
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])

    assert len(findings) == 1
    f = findings[0]
    assert f.n_activities == 7
    assert f.required_minutes == 7 * 60
    assert f.placeable_minutes == 6 * 60
    assert env["teacher"].name in f.resource_labels


def test_sette_lezioni_in_sette_fasce_non_e_un_problema():
    env = mini_school()
    _blocca(env["teacher"], giorni=(2, 3, 4),
            celle=[(1, s) for s in range(1, 6)])       # giorno 0 intero + (1,0)
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []


def test_l_impronta_e_fatta_di_fasce_occupate_non_di_avvii():
    # Due blocchi da 3 ore in un giorno da 6 fasce: entrano (0-2 e 3-5).
    # Contando gli avvii invece delle fasce occupate l'impronta sarebbe di 4
    # celle e uscirebbe un falso positivo.
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=3)

    assert analyze_hall(env["schedule"]) == []


def test_l_immobile_consuma_capienza():
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(3, 6)])       # restano (0,0) (0,1) (0,2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    assert analyze_hall(env["schedule"]) == []         # 3 attivita', 3 fasce

    bloccata = make_activity(
        env["subject"], teachers=[env["teacher"]], slots=1,
        immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], bloccata, day=0, slot=0)

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    assert findings[0].n_activities == 3               # l'immobile non e' colpevole
    assert findings[0].placeable_minutes == 2 * 60


def test_le_sorelle_gia_piazzate_non_si_tolgono_il_dominio():
    # Trappola §4.1: se si spiazza solo l'attivita' in prova, il blocco B
    # copre entrambe le fasce ammesse ad A, il dominio di A risulta vuoto e
    # esce un falso positivo. Spiazzando tutte le candidate, entra tutto.
    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(4, 6)])       # docente: (0,0)..(0,3)
    _blocca(env["klass"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(2, 6)])       # classe:  (0,0) (0,1)

    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=1)
    b = make_activity(env["subject"], teachers=[env["teacher"]], slots=2)
    place(env["schedule"], b, day=0, slot=0)           # copre (0,0) e (0,1)
    place(env["schedule"], a, day=0, slot=2)           # fuori dalla finestra di classe

    assert analyze_hall(env["schedule"]) == []


def test_l_incrociata_la_classe_satura_i_docenti_restringono():
    # Il caso che la fase 4 non puo' vedere: sette docenti diversi, ciascuno
    # libero solo il giorno 0, tutti sulla stessa classe. Nessun docente e'
    # sopra capienza (una lezione a testa, sei fasce disponibili) e la classe
    # non ha un solo vincolo — ma le sette lezioni si contendono le sei fasce
    # del giorno 0. La risorsa satura e' la classe; a restringere sono i
    # docenti. `analyze_capacity` tace, perche' bucketizza per (unita', materia)
    # e l'insieme di docenti comune alle sette attivita' e' vuoto.
    env = mini_school()
    for i in range(7):
        docente = Teacher.objects.create(
            name=f"Docente {i}", last_name=f"Cognome{i}", first_name=f"Nome{i}")
        _blocca(docente, giorni=(1, 2, 3, 4))
        make_activity(env["subject"], teachers=[docente],
                      classes=[env["klass"]], slots=1)

    assert analyze_capacity() == []                     # la fase 4 non lo vede

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    f = findings[0]
    assert f.n_activities == 7
    assert f.required_minutes == 7 * 60
    assert f.placeable_minutes == 6 * 60
    assert f.binding_label == env["klass"].name         # satura la classe, non un docente


def test_la_capienza_cumulativa_si_pesa_per_quantita():
    # Carrello da 6 posti: un'immobile ne occupa 3, e due attivita' libere
    # ne vogliono 2 ciascuna sull'unica fascia che i loro docenti concedono.
    # Presa una per volta ognuna entra (3 + 2 = 5 <= 6), quindi
    # `admissible_starts` non le scarta: e' l'insieme a non entrare, 3 + 2 + 2
    # = 7 > 6. Contando le attivita' invece delle quantita' il residuo
    # risulterebbe 5 e la diagnosi si perderebbe.
    env = mini_school()
    carrello = Material.objects.create(name="Carrello tablet",
                                       simultaneous_capacity=6)

    immobile = make_activity(env["subject"], slots=1,
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    ActivityMaterialRequirement.objects.create(
        activity=immobile, material=carrello, quantity=3)
    place(env["schedule"], immobile, day=0, slot=0)

    for i in range(2):
        docente = Teacher.objects.create(
            name=f"Docente carrello {i}", last_name=f"Cog{i}", first_name=f"Nom{i}")
        _blocca(docente, giorni=(1, 2, 3, 4),
                celle=[(0, s) for s in range(1, 6)])   # resta la sola (0,0)
        libera = make_activity(env["subject"], teachers=[docente], slots=1)
        ActivityMaterialRequirement.objects.create(
            activity=libera, material=carrello, quantity=2)

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    assert findings[0].n_activities == 2
    assert findings[0].binding_label == "Carrello tablet"


def test_le_settimane_disgiunte_non_competono():
    # Trappola §2: unendo le firme le due attivita' si contendono l'unica
    # fascia e esce un falso positivo. Per firma, ognuna entra da sola.
    from domain import weeks

    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(1, 6)])       # resta la sola (0,0)
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1,
                  mask=weeks.single_week(0))
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1,
                  mask=weeks.single_week(1))

    assert analyze_hall(env["schedule"]) == []


def test_una_deficienza_in_una_sola_settimana_esce_lo_stesso():
    # Deficienza nella settimana 1, non nella 0: con la deficienza nella prima
    # firma il test resterebbe verde anche ignorando il rappresentante del ciclo.
    from domain import weeks

    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4),
            celle=[(0, s) for s in range(1, 6)])
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1,
                      mask=weeks.single_week(1))

    findings = analyze_hall(env["schedule"])
    assert len(findings) == 1
    assert findings[0].n_activities == 2


def test_lo_stesso_insieme_in_due_firme_e_un_problema_solo():
    # Due firme distinte per una sola indisponibilita' DATATA su un docente
    # estraneo, che non tocca ne' le attivita' ne' i loro domini: l'insieme
    # colpevole e' identico nelle due firme. Con `seen` condiviso esce un
    # finding solo; ricreandolo per firma l'utente vedrebbe due volte lo
    # stesso problema.
    import datetime as dt

    env = mini_school()
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))       # resta il solo giorno 0
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    estraneo = Teacher.objects.create(
        name="Estraneo", last_name="Estraneo", first_name="E")
    ResourceUnavailability.objects.create(
        resource=estraneo, day=0, slot=0, level="hard",
        date=dt.date(2026, 9, 21))                     # settimana 1

    assert len(analyze_hall(env["schedule"])) == 1
