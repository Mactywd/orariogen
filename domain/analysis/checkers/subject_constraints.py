"""I tredici tipi di SubjectConstraint (l'asse Relazione): orientati,
A = B come caso dominante. Le attività si attribuiscono alla mezza giornata
della fascia di partenza. Una riga si applica alle attività i cui token
intersecano l'espansione dell'unità della riga."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import ClassPart, Group, SubjectConstraint
from domain.models.resources import Resource

T = SubjectConstraint.Type


def _unit_keys(row):
    if row.school_class_id:
        parts = ClassPart.objects.filter(
            partition__school_class_id=row.school_class_id).values_list("pk", flat=True)
        return frozenset({row.school_class_id, *parts})
    if row.class_part_id:
        return frozenset({row.class_part_id})
    return frozenset(Group.objects.get(pk=row.group_id)
                     .parts.values_list("pk", flat=True))


def _unit_resources(row):
    """I pk di Resource che identificano l'unità nel finding (per i
    raggruppamenti, che non sono Resource, le parti membre)."""
    if row.school_class_id:
        return (row.school_class_id,)
    if row.class_part_id:
        return (row.class_part_id,)
    return tuple(sorted(Group.objects.get(pk=row.group_id)
                        .parts.values_list("pk", flat=True)))


def _placed_of(state, keys, subject_id):
    return sorted(
        (pl for aid, pl in state.placed.items()
         if state.activities[aid].subject_id == subject_id
         and state.tokens[aid] & keys),
        key=lambda p: (p.day, p.start_slot))


def _half(state, day, slot):
    return day * 2 + (0 if slot < state.grid.morning_end_slot else 1)


def _is_class_level(state, aid):
    return any(state.kinds.get(k) == Resource.Kind.CLASS for k in state.tokens[aid])


class _SubjectChecker(Checker):
    TYPE = None
    CODE = None

    def check(self, state, resources=None):
        for row, keys in state.subject_rows:
            if row.type != self.TYPE:
                continue
            if resources is not None and not (keys & resources):
                continue
            a = _placed_of(state, keys, row.subject_a_id)
            b = (a if row.subject_a_id == row.subject_b_id
                 else _placed_of(state, keys, row.subject_b_id))
            yield from self.violations(state, row, a, b)

    def finding(self, state, row, activity_ids, **quantities):
        return Finding(
            self.CODE, causali.message(self.CODE, subject=row.subject_a.name),
            Severity.HARD, resources=_unit_resources(row),
            activities=tuple(sorted(set(activity_ids))), quantities=quantities)


class _BucketIncompatible(_SubjectChecker):
    """Incompatibilità per secchio (mezza giornata o giornata)."""

    def bucket(self, state, pl):
        raise NotImplementedError

    def violations(self, state, row, a, b):
        buckets = defaultdict(lambda: ([], []))
        for pl in a:
            buckets[self.bucket(state, pl)][0].append(pl.activity_id)
        if row.subject_a_id != row.subject_b_id:
            for pl in b:
                buckets[self.bucket(state, pl)][1].append(pl.activity_id)
        for bucket, (la, lb) in sorted(buckets.items()):
            if row.subject_a_id == row.subject_b_id and len(la) > 1:
                yield self.finding(state, row, la, bucket=bucket, count=len(la))
            elif row.subject_a_id != row.subject_b_id and la and lb:
                yield self.finding(state, row, la + lb, bucket=bucket)


@register(T.SAME_HALF_DAY_INCOMPATIBLE)
class SameHalfDayChecker(_BucketIncompatible):
    TYPE, CODE = T.SAME_HALF_DAY_INCOMPATIBLE, "subject_same_half_day"

    def bucket(self, state, pl):
        return _half(state, pl.day, pl.start_slot)


@register(T.SAME_DAY_INCOMPATIBLE)
class SameDayChecker(_BucketIncompatible):
    TYPE, CODE = T.SAME_DAY_INCOMPATIBLE, "subject_same_day"

    def bucket(self, state, pl):
        return pl.day


@register(T.TWO_DAYS_INCOMPATIBLE)
class TwoDaysChecker(_SubjectChecker):
    TYPE, CODE = T.TWO_DAYS_INCOMPATIBLE, "subject_two_days"

    def violations(self, state, row, a, b):
        a_days = defaultdict(list)
        b_days = defaultdict(list)
        for pl in a:
            a_days[pl.day].append(pl.activity_id)
        for pl in b:
            b_days[pl.day].append(pl.activity_id)
        for day in sorted(a_days):
            if b_days.get(day + 1):
                acts = a_days[day] + b_days[day + 1]
                if len(set(acts)) > 1:
                    yield self.finding(state, row, acts, day=day)


@register(T.FORBIDDEN_SEQUENCE)
class ForbiddenSequenceChecker(_SubjectChecker):
    TYPE, CODE = T.FORBIDDEN_SEQUENCE, "subject_forbidden_sequence"

    def violations(self, state, row, a, b):
        for pa in a:
            end = pa.start_slot + state.activities[pa.activity_id].duration_slots
            for pb in b:
                if (pb.activity_id != pa.activity_id
                        and pb.day == pa.day and pb.start_slot == end):
                    yield self.finding(state, row, [pa.activity_id, pb.activity_id],
                                       day=pa.day, slot=pb.start_slot)


class _MaxHours(_SubjectChecker):
    def bucket(self, state, pl):
        raise NotImplementedError

    def violations(self, state, row, a, b):
        minutes = defaultdict(int)
        acts = defaultdict(list)
        for pl in a:
            key = self.bucket(state, pl)
            minutes[key] += state.activities[pl.activity_id].duration_minutes
            acts[key].append(pl.activity_id)
        for key in sorted(minutes):
            if row.param is not None and minutes[key] > row.param:
                yield self.finding(state, row, acts[key], bucket=key,
                                   minutes=minutes[key], max_minutes=row.param)


@register(T.MAX_HOURS_HALF_DAY)
class MaxHoursHalfDayChecker(_MaxHours):
    TYPE, CODE = T.MAX_HOURS_HALF_DAY, "subject_max_hours_half_day"

    def bucket(self, state, pl):
        return _half(state, pl.day, pl.start_slot)


@register(T.MAX_HOURS_DAY)
class MaxHoursDayChecker(_MaxHours):
    TYPE, CODE = T.MAX_HOURS_DAY, "subject_max_hours_day"

    def bucket(self, state, pl):
        return pl.day


@register(T.WEEKLY_ORDER)
class WeeklyOrderChecker(_SubjectChecker):
    TYPE, CODE = T.WEEKLY_ORDER, "subject_weekly_order"

    def violations(self, state, row, a, b):
        if row.subject_a_id == row.subject_b_id or not a or not b:
            return
        first_a = (a[0].day, a[0].start_slot)
        first_b = (b[0].day, b[0].start_slot)
        if first_b < first_a:
            yield self.finding(state, row, [a[0].activity_id, b[0].activity_id])


@register(T.IMPOSED_SUCCESSION)
class ImposedSuccessionChecker(_SubjectChecker):
    TYPE, CODE = T.IMPOSED_SUCCESSION, "subject_imposed_succession"

    def violations(self, state, row, a, b):
        delay = row.param or 1
        if row.subject_a_id == row.subject_b_id:
            halves = [(_half(state, p.day, p.start_slot), p.activity_id) for p in a]
            for (h1, a1), (h2, a2) in zip(halves, halves[1:]):
                if h2 - h1 > delay:
                    yield self.finding(state, row, [a1, a2],
                                       gap=h2 - h1, max_gap=delay)
        else:
            b_halves = [_half(state, p.day, p.start_slot) for p in b]
            for pa in a:
                ha = _half(state, pa.day, pa.start_slot)
                if not any(0 < hb - ha <= delay for hb in b_halves):
                    yield self.finding(state, row, [pa.activity_id], max_gap=delay)


@register(T.HALF_DAY_GAP)
class HalfDayGapChecker(_SubjectChecker):
    """Scarto minimo fra occorrenze. Deliberatamente simmetrico anche con
    A ≠ B: lo scarto è una distanza temporale, e la distanza non ha verso.
    L'orientamento della relazione vale per le righe di dato, non per
    l'effetto di questo tipo."""
    TYPE, CODE = T.HALF_DAY_GAP, "subject_half_day_gap"

    def violations(self, state, row, a, b):
        same = row.subject_a_id == row.subject_b_id
        merged = [(_half(state, p.day, p.start_slot), p.activity_id, "a") for p in a]
        if not same:
            merged += [(_half(state, p.day, p.start_slot), p.activity_id, "b") for p in b]
        merged.sort()
        for (h1, a1, s1), (h2, a2, s2) in zip(merged, merged[1:]):
            crossed = same or s1 != s2
            if crossed and a1 != a2 and h2 - h1 < row.param:
                yield self.finding(state, row, [a1, a2],
                                   gap=h2 - h1, min_gap=row.param)


class _PartsOrder(_SubjectChecker):
    CODE = "subject_parts_order"
    MODE = None  # "before" | "after" | "homogeneous"

    def bucket(self, state, pl):
        return pl.day

    def violations(self, state, row, a, b):
        buckets = defaultdict(list)
        for pl in a:
            label = "class" if _is_class_level(state, pl.activity_id) else "part"
            buckets[self.bucket(state, pl)].append((pl.start_slot, label, pl.activity_id))
        for bucket, entries in sorted(buckets.items()):
            entries.sort()
            labels = [label for _, label, _ in entries]
            if "class" not in labels or "part" not in labels:
                continue
            bad = False
            if self.MODE == "before":
                bad = max(s for s, l, _ in entries if l == "part") > min(
                    s for s, l, _ in entries if l == "class")
            elif self.MODE == "after":
                bad = min(s for s, l, _ in entries if l == "part") < max(
                    s for s, l, _ in entries if l == "class")
            else:  # homogeneous: nessuna interlacciatura
                transitions = sum(x != y for x, y in zip(labels, labels[1:]))
                bad = transitions > 1
            if bad:
                yield self.finding(state, row, [aid for _, _, aid in entries],
                                   bucket=bucket)


@register(T.PARTS_BEFORE_CLASS)
class PartsBeforeChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_BEFORE_CLASS, "before"


@register(T.PARTS_AFTER_CLASS)
class PartsAfterChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_AFTER_CLASS, "after"


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_H)
class PartsHomogeneousHalfChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_BEFORE_OR_AFTER_CLASS_H, "homogeneous"

    def bucket(self, state, pl):
        return _half(state, pl.day, pl.start_slot)


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
class PartsHomogeneousDayChecker(_PartsOrder):
    TYPE, MODE = T.PARTS_BEFORE_OR_AFTER_CLASS_AB, "homogeneous"
