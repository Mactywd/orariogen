"""I tredici tipi di SubjectConstraint (l'asse Relazione): orientati,
A = B come caso dominante. Le attività si attribuiscono alla mezza giornata
della fascia di partenza. Una riga si applica alle attività i cui token
intersecano l'espansione dell'unità della riga."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.models import SubjectConstraint
from domain.models.resources import Resource

T = SubjectConstraint.Type

# ⚠ Nessuna query in questo file, ed è una regola e non un caso: l'espansione
# dell'unità di una riga sta in `state.subject_rows` e
# `state.subject_row_resources`, calcolate al caricamento. Le due copie che
# stavano qui la ricalcolavano **a ogni finding**.


def _placed_of(state, keys, subject_id):
    """Le occorrenze piazzate della materia dentro l'unità della riga, in
    ordine di collocazione.

    ⚠ **Il pareggio va rotto da qualcosa di dichiarato.** L'ordine è
    `(giorno, fascia)` e `sorted` è **stabile**: a parità esatta restava
    davanti l'occorrenza che il queryset aveva restituito per prima, cioè un
    fatto del database. Non è un caso di scuola — due occorrenze della stessa
    materia su parti diverse della **stessa** partizione (uno sdoppiamento)
    condividono legittimamente una cella, e le famiglie d'ordine
    (`WEEKLY_ORDER`, `IMPOSED_SUCCESSION`) **nominano** l'argmin: il valore
    aggregato restava identico e cambiava *chi* veniva incolpato, cioè la
    `Finding.key`.

    Si rompe con l'identità dell'attività. È arbitraria — fra due occorrenze
    davvero intercambiabili nessuna proprietà dell'orario le distingue — ma è
    **stabile e riproducibile**, che è precisamente ciò che l'ordine di un
    queryset senza `order_by` non promette.

    ⚠ L'alternativa considerata era nominarle **tutte** invece di sceglierne
    una: sarebbe una funzione della sola forma dell'orario, e per
    `WEEKLY_ORDER` funzionerebbe. Scartata perché non generalizza alle
    famiglie a **coppie consecutive** (`IMPOSED_SUCCESSION` con A = B), dove
    non esiste un «insieme in pareggio» da nominare: là il pareggio sposta la
    coppia, non allarga un secchio. Una regola sola per tutti i lettori di
    questa funzione vale più di due contratti di finding diversi."""
    return sorted(
        (pl for aid, pl in state.placed.items()
         if state.activities[aid].subject_id == subject_id
         and state.tokens[aid] & keys),
        key=lambda p: (p.day, p.start_slot, p.activity_id))


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
            Severity.HARD, resources=state.subject_row_resources[row.pk],
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
    """⚠ Non monotono per **deriva d'identità**: il finding nomina `a[0]` e
    `b[0]`, cioè le due occorrenze *argmin*, non il secchio intero. Piazzare
    un'occorrenza di A più presto può ripararlo del tutto, oppure — se non
    basta a scavalcare B — lasciare la violazione identica cambiando *quale*
    attività è l'argmin: chiave nuova senza nessun peggioramento. È la stessa
    causa a monte del tie-break di `_placed_of` già dichiarata in CLAUDE.md.
    Vedi `admissible_starts`."""
    TYPE, CODE = T.WEEKLY_ORDER, "subject_weekly_order"
    PLACEMENT_MONOTONE = False

    def violations(self, state, row, a, b):
        if row.subject_a_id == row.subject_b_id or not a or not b:
            return
        first_a = (a[0].day, a[0].start_slot)
        first_b = (b[0].day, b[0].start_slot)
        if first_b < first_a:
            yield self.finding(state, row, [a[0].activity_id, b[0].activity_id])


@register(T.IMPOSED_SUCCESSION)
class ImposedSuccessionChecker(_SubjectChecker):
    """⚠ Non monotono in **entrambi** i rami. Con A = B la violazione è su una
    coppia consecutiva, e infilare un'occorrenza *dentro* lo scarto lo spezza
    in due: riparazione. Con A ≠ B non c'è la guardia di vacuità che
    `WeeklyOrder` ha, quindi con B assente **ogni** occorrenza di A è in
    violazione — e piazzare una B le ripara tutte insieme. Vedi
    `admissible_starts`."""
    TYPE, CODE = T.IMPOSED_SUCCESSION, "subject_imposed_succession"
    PLACEMENT_MONOTONE = False

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
    """⚠ Non monotono per **deriva d'identità**, e vale per tutte e quattro le
    sottoclassi. Il finding nomina `entries` — *tutte* le attività del secchio,
    non quelle che realizzano il disordine — quindi aggiungere al secchio
    un'occorrenza già ben ordinata cambia la chiave senza peggiorare niente.
    Vedi `admissible_starts`."""

    CODE = "subject_parts_order"
    MODE = None  # "before" | "after" | "homogeneous"
    PLACEMENT_MONOTONE = False

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
