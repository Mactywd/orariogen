"""L2 — le due voci che O1 ha lasciato sulla fase 2.

Vengono dalla stessa schermata: la finestra `Ottimizzazione della ripartizione
delle aule`, osservata il 2026-08-30.

1. **La capienza in alunni è un criterio.** `Minimizza il superamento della
   capienza` (`tcosCapacite`) è il terzo dei quattro default. Dice due cose
   insieme: che la capienza **si può** superare — quindi «non è un vincolo»
   resta vero — e che EDT preferisce non farlo. `Room.capacity` esisteva nello
   schema dal primo giorno e non era letto da nessuno.
2. **Il lucchetto sulla singola assegnazione.** `Blocco delle aule nelle
   attività coinvolte` ha una casella **per riga** (43 righe nella finestra
   osservata): è l'immobilità applicata all'**aula** invece che alla
   collocazione. Da noi il blocco dell'aula era un effetto collaterale
   dell'immobilità del piazzamento, che è un'altra cosa.
"""
import pytest

from domain.models import Activity, Placement, Room
from domain.solver.rooms import RoomContext, build_room_model, livelli_aule, solve_rooms
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


# --- 1. il lucchetto sull'aula ------------------------------------------

def test_il_lucchetto_toglie_l_attivita_dalle_decisioni():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    p = place(env["schedule"], a, 0, 0, room=lab)
    Placement.objects.filter(pk=p.pk).update(room_locked=True)
    ctx = RoomContext.build(env["schedule"])
    assert a.id not in ctx.requests
    assert ctx.held == {a.id: lab.pk}


def test_il_lucchetto_senza_aula_non_blocca_niente():
    """Come per l'immobilità: il blocco riguarda l'aula che ha, non quella che
    non ha. Un lucchetto su un'assegnazione inesistente non è un lucchetto."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab])
    p = place(env["schedule"], a, 0, 0)
    Placement.objects.filter(pk=p.pk).update(room_locked=True)
    ctx = RoomContext.build(env["schedule"])
    assert a.id in ctx.requests


def test_il_lucchetto_e_indipendente_dall_immobilita_del_piazzamento():
    """Le due cose si separano in **entrambi** i versi: un'attività mobile può
    avere l'aula bloccata, e un'attività bloccata in griglia può cambiare
    aula. Prima di L2 la seconda era vera e la prima no."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    mobile = make_activity(env["subject"], rooms=[lab])
    p = place(env["schedule"], mobile, 0, 0, room=lab)
    Placement.objects.filter(pk=p.pk).update(room_locked=True)
    fissa = make_activity(env["subject"], rooms=[lab],
                          immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], fissa, 1, 0)
    ctx = RoomContext.build(env["schedule"])
    assert set(ctx.requests) == {fissa.id}
    assert ctx.held == {mobile.id: lab.pk}


def test_il_lucchetto_consuma_capienza():
    """Una bloccata occupa il posto come chiunque altro: chi resta deve
    rinunciare, non prendersi l'aula che è già di un'altra."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")   # capienza simultanea 1
    bloccata = make_activity(env["subject"], rooms=[lab])
    p = place(env["schedule"], bloccata, 0, 0, room=lab)
    Placement.objects.filter(pk=p.pk).update(room_locked=True)
    altra = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], altra, 0, 0)
    sol = solve_rooms(env["schedule"])
    assert sol.unassigned == (altra.id,)


# --- 2. la capienza in alunni come criterio ------------------------------

def _livelli(schedule):
    model, ctx = build_room_model(schedule)
    return [liv.nome for liv in livelli_aule(ctx, model)]


def test_senza_dati_il_livello_non_esiste():
    """Nessuna capienza dichiarata, nessun effettivo: il criterio non ha niente
    da misurare, e un livello che misura la costante zero è un giro di solver
    regalato. Stessa disciplina del vincolo che è un fatto e non si posta."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    assert _livelli(env["schedule"]) == ["minuti_senza_aula", "cambi_aula"]


def test_il_livello_compare_quando_c_e_un_eccedenza_possibile():
    env = mini_school()
    env["klass"].expected_students = 30
    env["klass"].save()
    lab = Room.objects.create(name="LAB", capacity=20)
    a = make_activity(env["subject"], rooms=[lab], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    assert _livelli(env["schedule"])[-1] == "eccedenza_capienza"


def test_fra_due_aule_sceglie_quella_che_sfora_meno():
    """Il criterio, non il vincolo: l'aula piccola resta ammissibile — se fosse
    l'unica verrebbe assegnata — ma fra le due si preferisce la grande."""
    env = mini_school()
    env["klass"].expected_students = 30
    env["klass"].save()
    piccola = Room.objects.create(name="PICCOLA", capacity=20)
    grande = Room.objects.create(name="GRANDE", capacity=28)
    a = make_activity(env["subject"], rooms=[piccola, grande],
                      classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    sol = solve_rooms(env["schedule"])
    assert sol.assignments == {a.id: grande.pk}
    assert sol.stats["eccedenza_capienza"] == 2


def test_l_aula_troppo_piccola_resta_ammissibile():
    """La prova che è un criterio e non un vincolo: con la sola aula piccola
    l'attività la prende, e l'eccedenza si dichiara invece di rifiutare."""
    env = mini_school()
    env["klass"].expected_students = 30
    env["klass"].save()
    piccola = Room.objects.create(name="PICCOLA", capacity=20)
    a = make_activity(env["subject"], rooms=[piccola], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    sol = solve_rooms(env["schedule"])
    assert sol.assignments == {a.id: piccola.pk}
    assert sol.stats["eccedenza_capienza"] == 10


def test_l_effettivo_dell_attivita_somma_le_parti():
    """L'unità non è la classe ma ciò che l'attività porta dentro: due parti di
    partizioni diverse fanno un'aula sola, e l'effettivo è la somma."""
    from domain.models import ClassPart, ClassPartition
    env = mini_school()
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="Lingua")
    a1 = ClassPart.objects.create(partition=partizione, name="ING",
                                  expected_students=12)
    a2 = ClassPart.objects.create(partition=partizione, name="FRA",
                                  expected_students=11)
    lab = Room.objects.create(name="LAB", capacity=20)
    att = make_activity(env["subject"], rooms=[lab], parts=[a1, a2])
    place(env["schedule"], att, 0, 0)
    sol = solve_rooms(env["schedule"])
    assert sol.stats["eccedenza_capienza"] == 3


def test_la_capienza_non_dichiarata_non_sfora_mai():
    """`capacity` a NULL è «non lo so», non «zero»: un'aula senza capienza
    dichiarata non può essere in eccedenza, o ogni base senza quel dato
    vedrebbe un criterio inventato dal nulla."""
    env = mini_school()
    env["klass"].expected_students = 30
    env["klass"].save()
    ignota = Room.objects.create(name="IGNOTA")
    piccola = Room.objects.create(name="PICCOLA", capacity=20)
    a = make_activity(env["subject"], rooms=[ignota, piccola],
                      classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    sol = solve_rooms(env["schedule"])
    assert sol.assignments == {a.id: ignota.pk}
    assert sol.stats["eccedenza_capienza"] == 0


def test_il_criterio_viene_dopo_i_due_livelli_che_gia_c_erano():
    """L'ordine è quello di EDT, che mette la capienza **terza** fra i suoi
    criteri: rinunciare a un'aula costa più che starci stretti."""
    env = mini_school()
    env["klass"].expected_students = 30
    env["klass"].save()
    grande = Room.objects.create(name="GRANDE", capacity=40)
    piccola = Room.objects.create(name="PICCOLA", capacity=1)
    prima = make_activity(env["subject"], rooms=[grande], classes=[env["klass"]])
    place(env["schedule"], prima, 0, 0)
    seconda = make_activity(env["subject"], rooms=[grande, piccola],
                            classes=[env["klass"]])
    place(env["schedule"], seconda, 0, 0)
    sol = solve_rooms(env["schedule"])
    assert sol.unassigned == ()          # meglio strette che senza aula
    assert sol.assignments[seconda.id] == piccola.pk
