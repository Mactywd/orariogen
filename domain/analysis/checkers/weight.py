"""Il peso didattico (ADR-011): Totale = Peso × Durata (in ore), conteggiato
per parte, non per classe (il caso _REL/_ALT verificato sui dati). Tetti
d'istituto per mattina/pomeriggio/giornata/settimana; il tetto settimanale
per alunno della classe prevale su quello d'istituto. Tetti NULL = spenti."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ClassPart, SchoolClass
from domain.models.resources import Resource


def _student_keys(state, activity_id):
    """Le unità-studente su cui pesa un'attività: le parti nei token, o la
    classe stessa se la classe non ha partizioni."""
    tokens = state.tokens[activity_id]
    parts = [k for k in tokens if state.kinds.get(k) == Resource.Kind.CLASS_PART]
    if parts:
        return parts
    return [k for k in tokens if state.kinds.get(k) == Resource.Kind.CLASS]


@register("structural:didactic_weight")
class DidacticWeightChecker(Checker):
    def check(self, state, resources=None):
        s = state.settings
        per_day, per_half, per_week = (defaultdict(int), defaultdict(int),
                                       defaultdict(int))
        acts = defaultdict(set)
        for aid, pl in state.placed.items():
            act = state.activities[aid]
            weight = act.subject.didactic_weight * act.duration_slots
            half = "morning" if pl.start_slot < state.grid.morning_end_slot else "afternoon"
            for key in _student_keys(state, aid):
                per_day[(key, pl.day)] += weight
                per_half[(key, pl.day, half)] += weight
                per_week[key] += weight
                acts[key].add(aid)

        def emit(code, key, weight, cap, **extra):
            name = state.resource_names.get(key, str(key))
            return Finding(code, causali.message(code), Severity.HARD,
                           resources=(key,), activities=tuple(sorted(acts[key])),
                           quantities={"weight": weight, "max_weight": cap, **extra})

        for (key, day), weight in sorted(per_day.items()):
            if resources is not None and key not in resources:
                continue
            if s.max_weight_day is not None and weight > s.max_weight_day:
                yield emit("weight_day", key, weight, s.max_weight_day, day=day)
        half_caps = {"morning": s.max_weight_morning, "afternoon": s.max_weight_afternoon}
        for (key, day, half), weight in sorted(per_half.items()):
            if resources is not None and key not in resources:
                continue
            cap = half_caps[half]
            if cap is not None and weight > cap:
                code = "weight_morning" if half == "morning" else "weight_afternoon"
                yield emit(code, key, weight, cap, day=day)

        part_class = dict(ClassPart.objects.values_list(
            "pk", "partition__school_class_id"))
        class_caps = dict(SchoolClass.objects.values_list(
            "pk", "max_weekly_weight_per_student"))
        for key, weight in sorted(per_week.items()):
            if resources is not None and key not in resources:
                continue
            cap = class_caps.get(part_class.get(key, key))
            if cap is None:
                cap = s.max_weight_week
            if cap is not None and weight > cap:
                yield emit("weight_week", key, weight, cap)
