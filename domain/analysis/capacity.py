"""L'aritmetica di capienza (fase 4 di EDT, diagnostica.md): per (unità,
materia), quante ore entrano al massimo contro quante ne servono. L'ottimo è
esatto su un RILASSAMENTO del problema vero: un verdetto negativo è una
dimostrazione di infattibilità, mai una stima. Il caso collettivo su risorse
incrociate (violatore di Hall, fase 5) è fuori scope → piano CP-SAT."""

import itertools
from dataclasses import dataclass
from functools import lru_cache

from domain import weeks
from domain.models import (
    Activity, ClassPart, Group, ResourceTimeConstraint, ResourceUnavailability,
    SchoolClass, SchoolYear, SubjectConstraint, TimeGrid,
)
from domain.analysis.state import activity_tokens, AtomMap

T = SubjectConstraint.Type
RT = ResourceTimeConstraint.Type

_REMEDY = {
    "subject_rows": "Rendere i vincoli delle materie meno vincolanti",
    "unit_unavailability": "Diminuire le indisponibilità delle risorse",
    "teacher_unavailability": "Diminuire le indisponibilità delle risorse",
    "teacher_free_days": "Diminuire i giorni e 1/2 giornate libere",
    "resource_max_hours": "Rendere i massimi orari meno vincolanti",
}
_TEACHER_FAMILIES = {"teacher_unavailability", "teacher_free_days"}


@dataclass(frozen=True)
class CapacityFinding:
    statement: str
    unit_label: str
    subject_label: str
    teacher_label: str | None
    n_activities: int
    required_minutes: int
    placeable_minutes: int
    culprits: tuple[str, ...]
    remedies: tuple[str, ...]
    activities: tuple[int, ...]


def _units():
    for klass in SchoolClass.objects.all():
        parts = frozenset(ClassPart.objects.filter(
            partition__school_class=klass).values_list("pk", flat=True))
        yield klass.name, frozenset({klass.pk}) | parts, frozenset({klass.pk})
    for part in ClassPart.objects.all():
        yield part.name, frozenset({part.pk}), frozenset({part.pk})
    for group in Group.objects.all():
        parts = frozenset(group.parts.values_list("pk", flat=True))
        yield group.name, parts, parts


def _week_groups(acts):
    """Gruppi di attività per firma di settimana: la capienza deve reggere in
    ogni settimana; per il Fermi (tutto annuale) la firma è una."""
    year = SchoolYear.objects.first()
    if year is None:
        return [acts]
    n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
    groups = {}
    for w in range(n_weeks):
        sig = frozenset(a.id for a in acts if weeks.week_in_mask(a.week_mask, w))
        if sig and sig not in groups:
            groups[sig] = [a for a in acts if a.id in sig]
    return list(groups.values()) or [acts]


def _max_assign(durations, day_caps):
    """Ottimo esatto: massimo dei minuti assegnabili. durations decrescenti;
    day_caps: tuple di (giorno, minuti residui, conteggio residuo, adiacenza
    vietata?)."""
    durations = tuple(sorted(durations, reverse=True))

    @lru_cache(maxsize=None)
    def best(idx, caps):
        if idx == len(durations):
            return 0
        duration = durations[idx]
        top = best(idx + 1, caps)  # l'attività resta fuori
        for i, (day, minutes, count, forbid) in enumerate(caps):
            if minutes >= duration and count > 0:
                updated = list(caps)
                updated[i] = (day, minutes - duration, count - 1, forbid)
                if forbid:
                    updated = [(d, 0, 0, f) if abs(d - day) == 1 else (d, m, c, f)
                               for d, m, c, f in updated]
                top = max(top, duration + best(idx + 1, tuple(updated)))
        return top

    return best(0, day_caps)


def _placeable(grid, group, unit_ids, teacher_ids, subject_id, unit_keys,
               disabled):
    sm, n_days = grid.slot_minutes, grid.days_per_cycle
    unavailable = {d: set() for d in range(n_days)}
    families = []
    if "unit_unavailability" not in disabled:
        families.append(("unit_unavailability", unit_ids))
    if teacher_ids and "teacher_unavailability" not in disabled:
        families.append(("teacher_unavailability", teacher_ids))
    for _, ids in families:
        rows = ResourceUnavailability.objects.filter(
            resource_id__in=ids, level="hard", date=None)
        for u in rows:
            if u.day < n_days:
                unavailable[u.day].add(u.slot)
    available = {d: [s for s in range(grid.slots_per_day)
                     if s not in unavailable[d]] for d in range(n_days)}

    same_day = same_half = two_days = False
    max_day = max_half = None
    if "subject_rows" not in disabled:
        for row in _subject_rows(subject_id, unit_keys):
            if row.type == T.SAME_DAY_INCOMPATIBLE:
                same_day = True
            elif row.type == T.SAME_HALF_DAY_INCOMPATIBLE:
                same_half = True
            elif row.type == T.TWO_DAYS_INCOMPATIBLE:
                two_days = True
            elif row.type == T.MAX_HOURS_DAY and row.param is not None:
                max_day = row.param if max_day is None else min(max_day, row.param)
            elif row.type == T.MAX_HOURS_HALF_DAY and row.param is not None:
                max_half = row.param if max_half is None else min(max_half, row.param)

    resource_day_cap = None
    if "resource_max_hours" not in disabled:
        rows = ResourceTimeConstraint.objects.filter(
            type=RT.MAX_HOURS, resource_id__in=unit_ids | teacher_ids)
        for r in rows:
            cap = r.params.get("day_minutes")
            if cap is not None:
                resource_day_cap = (cap if resource_day_cap is None
                                    else min(resource_day_cap, cap))

    day_caps = []
    for d in range(n_days):
        slots = available[d]
        morning = [s for s in slots if s < grid.morning_end_slot]
        afternoon = [s for s in slots if s >= grid.morning_end_slot]
        cap = len(slots) * sm
        if max_half is not None:
            cap = min(cap, min(len(morning) * sm, max_half)
                      + min(len(afternoon) * sm, max_half))
        if max_day is not None:
            cap = min(cap, max_day)
        if resource_day_cap is not None:
            cap = min(cap, resource_day_cap)
        count = 1 if same_day else (2 if same_half else max(len(slots), 1))
        day_caps.append((d, cap, count, two_days))

    free_days = 0
    if teacher_ids and "teacher_free_days" not in disabled:
        rows = ResourceTimeConstraint.objects.filter(
            type=RT.FREE_GUARANTEED, resource_id__in=teacher_ids)
        for r in rows:
            free_days = max(free_days, r.params.get("free_days", 0))

    durations = [a.duration_minutes for a in group]
    kept = max(0, n_days - free_days)
    best = 0
    for combo in itertools.combinations(range(n_days), kept):
        caps = tuple(day_caps[d] for d in combo)
        best = max(best, _max_assign(durations, caps))
    return best


def _subject_rows(subject_id, unit_keys):
    from domain.analysis.checkers.subject_constraints import _unit_keys
    rows = SubjectConstraint.objects.filter(
        subject_a_id=subject_id, subject_b_id=subject_id)
    return [row for row in rows if _unit_keys(row) & unit_keys]


def _culprit_labels(family, subject, teacher_name, rows):
    if family == "subject_rows":
        return [f"Vincolo materia: {subject.name}/{subject.name} — "
                f"{row.get_type_display()}" for row in rows]
    if family == "teacher_free_days":
        return [f"Giorni e 1/2 giornate libere di {teacher_name}"]
    if family == "teacher_unavailability":
        return [f"Indisponibilità di {teacher_name}"]
    if family == "unit_unavailability":
        return ["Indisponibilità dell'unità"]
    return ["Massimi orari della risorsa"]


def analyze_capacity():
    grid = TimeGrid.objects.first()
    if grid is None:
        return []
    acts = list(Activity.objects
                .exclude(immobility=Activity.Immobility.SUSPENDED)
                .select_related("subject")
                .prefetch_related("teachers", "classes", "parts", "groups",
                                  "rooms", "staff", "material_requirements"))
    atoms = AtomMap.build()
    tokens = {a.id: activity_tokens(a, atoms=atoms)[0] for a in acts}
    teacher_sets = {a.id: frozenset(t.pk for t in a.teachers.all()) for a in acts}
    teacher_names = {t.pk: t.name
                     for a in acts for t in a.teachers.all()}
    findings, seen = [], set()
    for week_acts in _week_groups(acts):
        for unit_label, unit_keys, unit_ids in _units():
            by_subject = {}
            for a in week_acts:
                if tokens[a.id] & unit_keys:
                    by_subject.setdefault(a.subject_id, []).append(a)
            for subject_id, group in by_subject.items():
                dedup = (frozenset(a.id for a in group), subject_id)
                if dedup in seen:
                    continue
                seen.add(dedup)
                common = frozenset.intersection(
                    *(teacher_sets[a.id] for a in group))
                required = sum(a.duration_minutes for a in group)
                args = (grid, group, unit_ids, common, subject_id, unit_keys)
                placeable = _placeable(*args, disabled=frozenset())
                if placeable >= required:
                    continue
                subject = group[0].subject
                teacher_name = (teacher_names[next(iter(common))]
                                if len(common) == 1 else None)
                culprits, remedies = [], {"Diminuire la durata delle attività"}
                guilty_families = set()
                for family in _REMEDY:
                    if _placeable(*args, disabled=frozenset({family})) >= required:
                        guilty_families.add(family)
                        rows = (_subject_rows(subject_id, unit_keys)
                                if family == "subject_rows" else ())
                        culprits += _culprit_labels(family, subject,
                                                    teacher_name, rows)
                        remedies.add(_REMEDY[family])
                if not culprits:
                    culprits = ["Vincoli combinati: nessuna famiglia da sola "
                                "ripristina la capienza"]
                crossed = guilty_families & _TEACHER_FAMILIES
                unit_side = guilty_families - _TEACHER_FAMILIES
                if crossed and unit_side:
                    statement = ("I vincoli incrociati della classe e del docente "
                                 "non permettono il piazzamento di tutte le attività.")
                elif crossed:
                    statement = ("I vincoli del docente non permettono il "
                                 "piazzamento di tutte le attività.")
                else:
                    statement = ("I vincoli della classe non permettono il "
                                 "piazzamento di tutte le attività.")
                findings.append(CapacityFinding(
                    statement=statement, unit_label=unit_label,
                    subject_label=subject.name, teacher_label=teacher_name,
                    n_activities=len(group), required_minutes=required,
                    placeable_minutes=placeable,
                    culprits=tuple(culprits), remedies=tuple(sorted(remedies)),
                    activities=tuple(sorted(a.id for a in group)),
                ))
    return findings
