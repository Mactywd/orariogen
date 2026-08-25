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
    dopo task. Qui si fissa lo stato corrente — dopo il Task 9, i sette del
    Task 6, i tre minimi garantiti del Task 7 (MIN_DISTRIBUTION,
    ARRIVAL_DEPARTURE, FREE_GUARANTEED), MAX_PRESENCE del Task 8, le due
    sedi del Task 9 (MAX_SITE_CHANGES, structural:site_transition), i due
    secchi di materia del Task 10 (SAME_HALF_DAY_INCOMPATIBLE,
    TWO_DAYS_INCOMPATIBLE, sullo scheletro SubjectBuilder), i tre del
    Task 11 (MAX_HOURS_DAY, MAX_HOURS_HALF_DAY sulla base comune
    `_Bucketed`, e FORBIDDEN_SEQUENCE), WEEKLY_ORDER del Task 12, primo
    della famiglia d'ordine, IMPOSED_SUCCESSION del Task 13, secondo della
    stessa famiglia, HALF_DAY_GAP del Task 14, terzo, e i quattro `PARTS_*`
    del Task 15b (l'ordine fra ore di parte e ore a classe intera, sullo
    scheletro comune `_PartsOrderBuilder`) e `structural:didactic_weight` del
    Task 16, l'ultimo — cosi' una registrazione dimenticata o una di troppo si
    vede subito, invece di dipendere dalla memoria di chi legge.

    Con il Task 16 il registro e' **completo**: ventisei chiavi su
    ventisette, e la ventisettesima (`structural:coverage`) non ne ha una per
    costruzione — e' `PLACEMENT_INDEPENDENT`, il solver non crea ne'
    distrugge attivita'."""
    from domain.models import ResourceTimeConstraint, SubjectConstraint
    all_builders()
    assert set(BUILDERS) == {
        "structural:grid",
        "structural:unavailability",
        "structural:occupation",
        "structural:site_transition",
        "structural:didactic_weight",
        ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        ResourceTimeConstraint.Type.MAX_HOURS,
        ResourceTimeConstraint.Type.MAX_HALF_DAYS,
        ResourceTimeConstraint.Type.MIN_DISTRIBUTION,
        ResourceTimeConstraint.Type.ARRIVAL_DEPARTURE,
        ResourceTimeConstraint.Type.FREE_GUARANTEED,
        ResourceTimeConstraint.Type.MAX_PRESENCE,
        ResourceTimeConstraint.Type.MAX_SITE_CHANGES,
        SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE,
        SubjectConstraint.Type.SAME_HALF_DAY_INCOMPATIBLE,
        SubjectConstraint.Type.TWO_DAYS_INCOMPATIBLE,
        SubjectConstraint.Type.MAX_HOURS_DAY,
        SubjectConstraint.Type.MAX_HOURS_HALF_DAY,
        SubjectConstraint.Type.FORBIDDEN_SEQUENCE,
        SubjectConstraint.Type.WEEKLY_ORDER,
        SubjectConstraint.Type.IMPOSED_SUCCESSION,
        SubjectConstraint.Type.HALF_DAY_GAP,
        SubjectConstraint.Type.PARTS_BEFORE_CLASS,
        SubjectConstraint.Type.PARTS_AFTER_CLASS,
        SubjectConstraint.Type.PARTS_BEFORE_OR_AFTER_CLASS_H,
        SubjectConstraint.Type.PARTS_BEFORE_OR_AFTER_CLASS_AB,
    }
