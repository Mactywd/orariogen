"""Copertura del monte ore per (unità-studente × materia): il predicato
anti-inversione STO/SCI. Confronta le attività (piazzate o no) con i servizi
del piano effettivo. È un predicato sui dati, non sull'orario."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ClassPart, SchoolClass, Service, Subject


def _student_units():
    """(chiave Resource, StudyPlan effettivo, nome) per ogni parte, o per la
    classe se non ha partizioni."""
    for klass in SchoolClass.objects.select_related("study_plan"):
        parts = list(ClassPart.objects.filter(partition__school_class=klass)
                     .select_related("partition__school_class__study_plan", "study_plan"))
        if parts:
            for part in parts:
                yield part.pk, part.effective_study_plan, part.name
        else:
            yield klass.pk, klass.study_plan, klass.name


@register("structural:coverage")
class CoverageChecker(Checker):
    def check(self, state, resources=None):
        subject_names = dict(Subject.objects.values_list("id", "name"))
        services = defaultdict(dict)
        for s in Service.objects.all():
            services[s.study_plan_id][s.subject_id] = s.class_minutes
        for key, plan, unit_name in _student_units():
            if resources is not None and key not in resources:
                continue
            expected = services.get(plan.pk, {})
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
                                        subject=subject_names[subject_id]),
                        Severity.HARD, resources=(key,),
                        quantities={"expected_minutes": want, "actual_minutes": got},
                    )
