"""Copertura del monte ore per (unità-studente × materia): il predicato
anti-inversione STO/SCI. Confronta le attività (piazzate o no) con i servizi
del piano effettivo. È un predicato sui dati, non sull'orario."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:coverage")
class CoverageChecker(Checker):
    # I finding dipendono solo da attività e servizi anagrafici, mai da come
    # le attività sono piazzate: residual_domain può escluderlo dal loop di
    # prova (vedi domain_size.py).
    PLACEMENT_INDEPENDENT = True

    def check(self, state, resources=None):
        for key, plan_id, unit_name in state.student_units:
            if resources is not None and key not in resources:
                continue
            expected = state.services_by_plan.get(plan_id, {})
            actual = defaultdict(int)
            for aid, act in state.activities.items():
                if key in state.tokens[aid]:
                    actual[act.subject_id] += act.duration_minutes
            for subject_id in sorted(expected.keys() | actual.keys()):
                want, got = expected.get(subject_id, 0), actual.get(subject_id, 0)
                if want != got:
                    yield Finding(
                        "coverage_mismatch",
                        causali.message("coverage_mismatch", unit=unit_name,
                                        subject=state.subject_names[subject_id]),
                        Severity.HARD, resources=(key,),
                        quantities={"expected_minutes": want, "actual_minutes": got},
                    )
