"""Il contesto della seconda fase: chi chiede un'aula, e quali restano."""
import datetime as dt

import pytest

from domain.models import Activity, Resource, ResourceUnavailability, Room, Site
from domain.solver.rooms import RoomContext
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def test_chiede_un_aula_solo_chi_e_piazzato_e_dichiara_candidate():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    chiede = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], chiede, 0, 0)
    make_activity(env["subject"], rooms=[lab])          # non piazzata
    senza = make_activity(env["subject"])               # non chiede aule
    place(env["schedule"], senza, 1, 0)
    ctx = RoomContext.build(env["schedule"])
    assert set(ctx.requests) == {chiede.id}


def test_l_immobile_con_la_sua_aula_non_e_una_decisione():
    """Bloccare una lezione in EDT significa non toccarla: tiene l'aula che ha,
    e quell'aula consuma capienza senza essere una scelta."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], a, 0, 0, room=lab)
    ctx = RoomContext.build(env["schedule"])
    assert a.id not in ctx.requests
    assert ctx.held == {a.id: lab.pk}


def test_l_immobile_senza_aula_resta_una_decisione():
    """Il blocco riguarda l'aula che ha, non quella che non ha (spec §2.4):
    un laboratorio fissato a mano in griglia dev'essere assegnabile."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    a = make_activity(env["subject"], rooms=[lab],
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert a.id in ctx.requests


def test_l_aula_di_un_altra_sede_esce_dalle_candidate():
    env = mini_school()
    principale = Site.objects.create(name="Principale")
    succursale = Site.objects.create(name="Succursale")
    qui = Room.objects.create(name="LAB QUI", site=principale)
    la = Room.objects.create(name="LAB LA", site=succursale)
    a = make_activity(env["subject"], rooms=[qui, la], site=principale)
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == {qui.pk}


def test_senza_sede_sull_attivita_non_si_filtra_per_sede():
    """La sede e' dichiarata sull'attivita' ed e' da li' che la legge
    `SiteTransitionChecker`: dedurla dall'aula creerebbe due sorgenti di
    verita' per la stessa cosa."""
    env = mini_school()
    succursale = Site.objects.create(name="Succursale")
    la = Room.objects.create(name="LAB LA", site=succursale)
    a = make_activity(env["subject"], rooms=[la])
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == {la.pk}


def test_l_aula_indisponibile_esce_dalle_candidate():
    env = mini_school()
    libero = Room.objects.create(name="LAB LIBERO")
    occupato = Room.objects.create(name="LAB CHIUSO")
    ResourceUnavailability.objects.create(
        resource=occupato, day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[libero, occupato])
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == {libero.pk}


def test_l_indisponibilita_sulla_seconda_fascia_di_un_blocco_conta():
    """Il pre-filtro guarda **tutta** la durata: e' l'errore che
    `UnavailabilityBuilder` dichiara di aver gia' commesso una volta."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=1, level=ResourceUnavailability.Level.HARD)
    a = make_activity(env["subject"], rooms=[lab], slots=2)
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.candidates[a.id] == set()


def test_la_gialla_si_rispetta_come_la_rossa():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.OPTIONAL)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    assert RoomContext.build(env["schedule"]).candidates[a.id] == set()


def test_l_override_delle_gialle_e_per_tipo_di_risorsa():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.OPTIONAL)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    ctx = RoomContext.build(env["schedule"],
                            ignora_opzionali=(Resource.Kind.ROOM,))
    assert ctx.candidates[a.id] == {lab.pk}


def test_il_verde_non_restringe():
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    ResourceUnavailability.objects.create(
        resource=lab, day=0, slot=0,
        level=ResourceUnavailability.Level.PREFERENCE)
    a = make_activity(env["subject"], rooms=[lab])
    place(env["schedule"], a, 0, 0)
    assert RoomContext.build(env["schedule"]).candidates[a.id] == {lab.pk}


def test_l_aula_di_prima_e_registrata_per_la_stabilita():
    env = mini_school()
    p1 = Room.objects.create(name="PAL 1")
    p2 = Room.objects.create(name="PAL 2")
    a = make_activity(env["subject"], rooms=[p1, p2])
    place(env["schedule"], a, 0, 0, room=p2)
    ctx = RoomContext.build(env["schedule"])
    assert ctx.previous == {a.id: p2.pk}
