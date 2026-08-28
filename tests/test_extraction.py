"""`Estrai`: la selezione di lavoro come operazione.

Le due proprietà che il pezzo deve tenere, e che nessun'altra parte del
progetto teneva: **appartenenza ≠ occupazione** (i token rispondono a un'altra
domanda) e **un perimetro restringe l'azione, mai il conteggio**."""
import pytest

from domain import extraction as ex
from domain.analysis.state import activity_tokens
from domain.models import (Activity, ClassPart, ClassPartition, Extraction,
                           Group, ResourceUnavailability, Room)
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _con_parti(env, nomi=("A", "B")):
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="Lingue")
    return [ClassPart.objects.create(partition=partizione, name=n) for n in nomi]


# -- appartenenza ------------------------------------------------------------

def test_la_classe_estrae_anche_i_suoi_sdoppiamenti():
    """🔑 La proprietà che vieta di riusare i token.

    `activity_tokens` è asimmetrico apposta: la classe intera occupa le sue
    parti, la parte **non** occupa la classe. È giusto per i conflitti e
    sbagliato per l'appartenenza — leggere i token qui perderebbe proprio gli
    sdoppiamenti, cioè le attività che un vicepreside cerca per prime."""
    env = mini_school()
    parti = _con_parti(env)
    intera = make_activity(env["subject"], classes=[env["klass"]])
    sdoppiata = make_activity(env["subject"], parts=[parti[0]])

    assert ex.per_risorsa([env["klass"].pk]) == {intera.pk, sdoppiata.pk}
    # E la prova che non è un caso: i token, da soli, la seconda la perdono.
    assert env["klass"].pk not in activity_tokens(sdoppiata)[0]


def test_il_raggruppamento_trasversale_risale_a_tutte_le_classi():
    """ADR-013: un raggruppamento attraversa più classi, quindi un'attività di
    raggruppamento appartiene a ognuna di esse."""
    env = mini_school()
    parti = _con_parti(env)
    altra_partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="Altra")
    ClassPart.objects.create(partition=altra_partizione, name="C")
    gruppo = Group.objects.create(name="G")
    gruppo.parts.add(parti[0])
    act = make_activity(env["subject"], groups=[gruppo])

    assert act.pk in ex.per_risorsa([env["klass"].pk])
    assert act.pk in ex.per_risorsa([parti[0].pk])
    assert act.pk not in ex.per_risorsa([parti[1].pk])


def test_tutte_le_aule_dichiarate_non_solo_la_candidata_unica():
    """⚠ Seconda divergenza dai token: quelli prendono l'aula solo quando è
    una sola, perché a due candidate la scelta è della seconda fase. Per
    l'appartenenza sono entrambe: «le attività che possono finire in
    laboratorio» include quelle che potrebbero finire altrove."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    aula = Room.objects.create(name="A1")
    act = make_activity(env["subject"], classes=[env["klass"]],
                        rooms=[lab, aula])

    assert act.pk in ex.per_risorsa([lab.pk])
    assert lab.pk not in activity_tokens(act)[0]


# -- stato e finestra --------------------------------------------------------

def test_gli_stati_leggono_il_piazzamento_e_l_immobilita():
    env = mini_school()
    piazzata = make_activity(env["subject"], classes=[env["klass"]])
    libera = make_activity(env["subject"], classes=[env["klass"]])
    bloccata = make_activity(env["subject"], classes=[env["klass"]],
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], piazzata, 0, 0)

    assert ex.per_stato(env["schedule"], "piazzate") == {piazzata.pk}
    assert ex.per_stato(env["schedule"], "non_piazzate") == {libera.pk, bloccata.pk}
    assert ex.per_stato(env["schedule"], "bloccate") == {bloccata.pk}


def test_la_finestra_si_misura_su_tutte_le_fasce_occupate():
    """⚠ Non sulla sola fascia d'inizio: un blocco da 3 ore avviato in 1 esce
    da una finestra [0, 2], e «interamente» deve dirlo."""
    env = mini_school()
    lungo = make_activity(env["subject"], classes=[env["klass"]], slots=3)
    place(env["schedule"], lungo, 0, 1)

    assert ex.nella_fascia(env["schedule"], 0, 0, 2, interamente=True) == set()
    assert ex.nella_fascia(env["schedule"], 0, 0, 2, interamente=False) == {lungo.pk}
    assert ex.nella_fascia(env["schedule"], 0, 1, 3, interamente=True) == {lungo.pk}


# -- rilevatori --------------------------------------------------------------

def test_il_rilevatore_nomina_chi_viola():
    env = mini_school()
    act = make_activity(env["subject"], classes=[env["klass"]],
                        teachers=[env["teacher"]])
    place(env["schedule"], act, 0, 0)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)

    r = ex.rileva(env["schedule"], "non_rispettano_i_vincoli")
    assert r.activity_ids == {act.pk}
    assert not r.muto


def test_i_vincoli_sulla_risorsa_non_nominano_nessuno_e_si_dichiara():
    """🔑 Il D.T.B. viola la **forma** di una giornata, non una lezione: quale
    delle due ore sarebbe «quella che viola»? Nessuna. Il rilevatore
    restituisce un insieme vuoto e lo **dichiara**, invece di lasciar credere
    che l'orario sia sano."""
    from domain.models import ResourceTimeConstraint

    env = mini_school()
    prima = make_activity(env["subject"], teachers=[env["teacher"]])
    dopo = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], prima, 0, 0)
    place(env["schedule"], dopo, 0, 3)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"],
        type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    r = ex.rileva(env["schedule"], "non_rispettano_i_vincoli")
    assert r.muto
    assert [c for c, _ in r.senza_attivita] == ["max_gap"]


def test_il_rilevatore_delle_aule_e_quello_dei_vincoli_sono_disgiunti():
    """⚠ `room_unassigned` descrive un orario **incompleto**, non illegale — la
    stessa esclusione che `solve` fa già. Chiede l'aula chi ne ha bisogno, e
    fino alla seconda fase nessuno ce l'ha: contarlo fra le violazioni direbbe
    a chi legge che l'orario è sbagliato quando invece non è ancora finito."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    act = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    place(env["schedule"], act, 0, 0)

    assert ex.rileva(env["schedule"], "problemi_di_aule").activity_ids == {act.pk}
    assert ex.rileva(env["schedule"], "non_rispettano_i_vincoli").activity_ids == set()


def test_lo_scostamento_dal_quadro_orario_nomina_le_attivita_che_ci_sono():
    """⚠ E solo quelle: con `got < want` il colpevole è un'attività che **non
    esiste**, e nessuna estrazione può nominarla. Il rilevatore dà le righe da
    cui si corregge il monte ore, non l'elenco completo delle colpevoli —
    perché in quel verso quell'elenco non esiste."""
    env = mini_school()
    act = make_activity(env["subject"], classes=[env["klass"]])
    servizio = env["plan"].services.get(subject=env["subject"])
    servizio.class_minutes += 60      # il piano ne chiede una in più
    servizio.save()

    r = ex.rileva(env["schedule"], "non_conformi_ai_piani_di_studi")
    assert r.activity_ids == {act.pk}


# -- composizione ------------------------------------------------------------

def test_le_quattro_operazioni_insiemistiche():
    assert ex.componi({1, 2}, {2, 3}, "sostituisci") == {2, 3}
    assert ex.componi({1, 2}, {2, 3}, "aggiungi") == {1, 2, 3}
    assert ex.componi({1, 2}, {2, 3}, "togli") == {1}
    assert ex.componi({1, 2}, {2, 3}, "limita") == {2}


def test_l_estrazione_si_salva_e_si_richiama_sovrascrivendo():
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(env["subject"], classes=[env["klass"]])

    ex.salva("biennio", {a.pk, b.pk})
    assert ex.carica("biennio") == {a.pk, b.pk}
    ex.salva("biennio", {a.pk})
    assert ex.carica("biennio") == {a.pk}
    assert Extraction.objects.filter(name="biennio").count() == 1
