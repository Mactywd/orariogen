"""Findings: la forma del verdetto. Mai persistiti (principio 2)."""
import re

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity


def _finding(**overrides):
    base = dict(
        code="subject_same_day",
        message="Italiano, troppe attività nella giornata",
        severity=Severity.HARD,
        resources=(3,),
        activities=(7, 9),
        quantities={"day": 2, "count": 2},
    )
    base.update(overrides)
    return Finding(**base)


def test_finding_key_ignora_il_messaggio_e_le_settimane():
    a = _finding()
    b = _finding(message="altro testo", weeks=(0, 1))
    assert a.key == b.key


def test_finding_key_distingue_le_quantita():
    assert _finding().key != _finding(quantities={"day": 3, "count": 2}).key


def test_message_formatta_i_nomi():
    msg = causali.message("unavailability", resource="ROSSI")
    assert msg == "ROSSI ha una indisponibilità"


def test_tutte_le_causali_usano_solo_segnaposto_noti():
    # ⚠ `group` è entrato con ADR-020, ed è un **nome** come gli altri tre:
    # il gruppo di elezione. I numeri restano fuori dalle frasi e stanno in
    # `quantities`, che è ciò che rende il verdetto verificabile.
    ammessi = {"resource", "subject", "unit", "group"}
    for code, template in causali.CAUSALI.items():
        campi = set(re.findall(r"{(\w+)}", template))
        assert campi <= ammessi, f"{code}: segnaposto {campi - ammessi}"
