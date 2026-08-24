"""Il registro dei builder: stesse chiavi dei checker, package separato."""
import pytest

from domain.analysis.registry import REGISTRY, all_checkers
from domain.solver.registry import BUILDERS, Builder, all_builders, register


def test_register_mette_la_classe_sotto_ogni_chiave():
    @register("prova:uno", "prova:due")
    class Finto(Builder):
        def build(self, ctx, model):
            return None

    try:
        assert BUILDERS["prova:uno"] is Finto
        assert BUILDERS["prova:due"] is Finto
    finally:
        del BUILDERS["prova:uno"], BUILDERS["prova:due"]


def test_all_builders_istanzia_ogni_classe_una_volta_sola():
    tipi = [type(b) for b in all_builders()]
    assert len(tipi) == len(set(tipi))


def test_i_due_hook_sono_no_op_di_default():
    assert Builder().restrict(None) is None
    assert Builder().build(None, None) is None


def test_le_chiavi_dei_builder_sono_chiavi_del_registro_dei_checker():
    all_checkers()   # forza la registrazione dei checker
    all_builders()   # forza la registrazione dei builder
    assert set(BUILDERS) <= set(REGISTRY)


def test_ogni_builder_implementa_almeno_un_hook():
    all_builders()
    for chiave, cls in BUILDERS.items():
        assert (cls.restrict is not Builder.restrict
                or cls.build is not Builder.build), chiave


def test_i_builder_tradotti_finora():
    """Non piu' i cinque dello spike: il modello completo li accresce task
    dopo task. Qui si fissa lo stato corrente — dopo il Task 7, i sette del
    Task 6 piu' i tre minimi garantiti (MIN_DISTRIBUTION, ARRIVAL_DEPARTURE,
    FREE_GUARANTEED) — cosi' una registrazione dimenticata o una di troppo si
    vede subito, invece di dipendere dalla memoria di chi legge."""
    from domain.models import ResourceTimeConstraint, SubjectConstraint
    all_builders()
    assert set(BUILDERS) == {
        "structural:grid",
        "structural:unavailability",
        "structural:occupation",
        ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        ResourceTimeConstraint.Type.MAX_HOURS,
        ResourceTimeConstraint.Type.MAX_HALF_DAYS,
        ResourceTimeConstraint.Type.MIN_DISTRIBUTION,
        ResourceTimeConstraint.Type.ARRIVAL_DEPARTURE,
        ResourceTimeConstraint.Type.FREE_GUARANTEED,
        SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE,
    }
