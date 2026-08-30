"""L1 — il perimetro su cui si misura il buco è un parametro, non una costante.

In EDT il buco si conta sulla **giornata**, e una casella
`Non conteggiare come buchi le ore libere prima o dopo la linea di fine
mattinata` — **separata per classi e per docenti** — ne toglie la pausa. Fino
al 2026-08-30 ci comportavamo come se fosse spuntata per entrambe le
popolazioni, cioè misuravamo sempre dentro la mezza giornata.

🔑 Le due formulazioni **coincidono**, e non è un'assunzione: con la giornata
come perimetro il buco è `ultima − prima + 1 − conteggio`; spezzarlo alla linea
di fine mattinata toglie esattamente le fasce libere fra l'ultima occupata del
mattino e la prima del pomeriggio, cioè «le ore libere prima o dopo la linea».
`test_la_differenza_e_esattamente_la_corsa_libera_attorno_alla_linea` la misura.
"""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import (
    InstituteSettings, ResourceTimeConstraint, ResourceUnavailability, Teacher,
)
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

T = ResourceTimeConstraint.Type


def _dtb(risorsa, minuti):
    return ResourceTimeConstraint.objects.create(
        resource=risorsa, type=T.MAX_GAP_HOURS, params={"max_gap_minutes": minuti})


def _teach(env, day, slot):
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], a, day=day, slot=slot)
    return a


def _findings(env, code="max_gap"):
    return [f for f in check_schedule(env["schedule"]) if f.code == code]


def _sul_giorno(**kwargs):
    s = InstituteSettings.load()
    for campo, valore in kwargs.items():
        setattr(s, campo, valore)
    s.save()


# --- il default non cambia niente ---------------------------------------

def test_il_default_e_la_mezza_giornata():
    """Lo status quo resta lo status quo: chi non tocca il parametro misura
    come prima, e i due campi nascono a `True`."""
    s = InstituteSettings.load()
    assert s.gaps_split_at_lunch_teachers is True
    assert s.gaps_split_at_lunch_classes is True
    env = mini_school()
    _dtb(env["teacher"], 60)
    _teach(env, day=0, slot=1)
    _teach(env, day=0, slot=5)      # fasce 2,3,4 libere, ma a cavallo del pranzo
    assert _findings(env) == []


# --- il parametro spento sposta il perimetro alla giornata ---------------

def test_sulla_giornata_il_buco_del_pranzo_conta():
    env = mini_school()
    _sul_giorno(gaps_split_at_lunch_teachers=False)
    _dtb(env["teacher"], 60)
    _teach(env, day=0, slot=1)
    _teach(env, day=0, slot=5)
    (f,) = _findings(env)
    assert f.quantities["gap_minutes"] == 180   # fasce 2, 3 e 4


def test_la_differenza_e_esattamente_la_corsa_libera_attorno_alla_linea():
    """La misura che dimostra l'equivalenza con la casella di EDT: giornata
    meno mezza giornata = le fasce libere fra l'ultima del mattino e la prima
    del pomeriggio. Qui: occupate 0, 2 e 5, linea fra 3 e 4.

    Mezza giornata → 60' (la sola fascia 1). Giornata → 180' (1, 3 e 4). La
    differenza sono 3 e 4, che sono *«le ore libere prima o dopo la linea di
    fine mattinata»* alla lettera."""
    env = mini_school()
    _dtb(env["teacher"], 0)
    for fascia in (0, 2, 5):
        _teach(env, 0, fascia)
    (mezza,) = _findings(env)
    _sul_giorno(gaps_split_at_lunch_teachers=False)
    (giorno,) = _findings(env)
    assert mezza.quantities["gap_minutes"] == 60
    assert giorno.quantities["gap_minutes"] == 180
    assert giorno.quantities["gap_minutes"] - mezza.quantities["gap_minutes"] == 120


# --- ed è separato per popolazione --------------------------------------

def test_il_parametro_e_separato_per_popolazione():
    """Spegnerlo per i docenti non tocca le classi: sono due caselle, e in EDT
    la base di esempio le ha davvero diverse (spuntata per i docenti, no per le
    classi)."""
    env = mini_school()
    _sul_giorno(gaps_split_at_lunch_teachers=False)
    _dtb(env["klass"], 60)
    for fascia in (1, 5):
        a = make_activity(env["subject"], classes=[env["klass"]])
        place(env["schedule"], a, day=0, slot=fascia)
    assert _findings(env) == []

    _sul_giorno(gaps_split_at_lunch_classes=False)
    (f,) = _findings(env)
    assert f.resources == (env["klass"].resource_ptr_id,)


# --- il builder legge lo stesso parametro del checker --------------------

def _solo_queste_fasce(risorsa, ammesse, giorni=5, fasce=6):
    for giorno in range(giorni):
        for fascia in range(fasce):
            if (giorno, fascia) not in ammesse:
                ResourceUnavailability.objects.create(
                    resource=risorsa, day=giorno, slot=fascia, level="hard")


def _scena_a_cavallo(env):
    """Fascia 0 fissa, unica altra cella libera la 5: il buco esiste solo se il
    perimetro è la giornata."""
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 5)})
    fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
    place(env["schedule"], fissa, day=0, slot=0)
    make_activity(env["subject"], teachers=[docente])


def test_il_builder_sulla_mezza_giornata_e_fattibile():
    env = mini_school()
    _scena_a_cavallo(env)
    _dtb(env["teacher"], 0)
    assert solve(env["schedule"], allow_unplaced=False).status in ("OPTIMAL", "FEASIBLE")


def test_il_builder_sulla_giornata_vede_lo_stesso_buco_del_checker():
    env = mini_school()
    _scena_a_cavallo(env)
    _sul_giorno(gaps_split_at_lunch_teachers=False)
    _dtb(env["teacher"], 0)
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"


def test_il_clamp_di_adr_018_segue_il_perimetro():
    """Le sole congelate sforano — ma solo sulla giornata. Col perimetro largo
    il tetto va clampato al debito già contratto, e il modello resta fattibile
    invece di pretendere una riparazione impossibile."""
    env = mini_school()
    docente = env["teacher"]
    _solo_queste_fasce(docente, {(0, 0), (0, 5), (1, 0)})
    for giorno, fascia in ((0, 0), (0, 5)):
        fissa = make_activity(env["subject"], teachers=[docente], immobility="fixed")
        place(env["schedule"], fissa, day=giorno, slot=fascia)
    make_activity(env["subject"], teachers=[docente])   # va per forza in (1, 0)
    _sul_giorno(gaps_split_at_lunch_teachers=False)
    _dtb(docente, 0)
    assert solve(env["schedule"], allow_unplaced=False).status in ("OPTIMAL", "FEASIBLE")


# --- e il criterio di qualità pure --------------------------------------

def test_il_criterio_buchi_segue_il_perimetro():
    """`gaps` è la stessa quantità del D.T.B. senza il tetto: se il perimetro
    cambia per il checker deve cambiare anche per il criterio, o i due numeri
    che l'utente legge nello stesso rendiconto non parlerebbero della stessa
    cosa. Si misura sul **massimo** dichiarato, che è il numero di fasce che
    possono stare in mezzo: sulla mezza giornata è strettamente minore."""
    from domain.models import QualityCriterion
    from domain.solver import criteria  # noqa: F401 — registra i criteri
    from domain.solver.model import build_model
    from domain.solver.quality import _CRITERI

    env = mini_school()
    docente = env["teacher"]
    make_activity(env["subject"], teachers=[docente])

    def _massimo(split):
        _sul_giorno(gaps_split_at_lunch_teachers=split)
        model, ctx = build_model(env["schedule"])
        _, tetto = _CRITERI[QualityCriterion.Kind.GAPS](
            ctx, model, [docente.resource_ptr_id])
        return tetto

    assert _massimo(True) < _massimo(False)
