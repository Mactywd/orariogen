"""check_schedule: valuta ogni firma di settimana distinta una volta sola e
fonde i findings identici annotando le settimane."""

from dataclasses import replace

from domain import weeks
from domain.analysis.findings import Severity
from domain.analysis.registry import all_checkers
from domain.analysis.state import ScheduleState, resource_sort_key
from domain.models import (Activity, Holiday, ResourceUnavailability,
                           effective_week_masks)

_RANK = {Severity.HARD: 0, Severity.OPTIONAL: 1, Severity.PREFERENCE: 2}


def _finding_sort_key(f):
    """Chiave di ordinamento per i findings che gestisce risorse miste int/str.
    Applica resource_sort_key elemento per elemento sulla tupla resources."""
    return (_RANK[f.severity], f.code, tuple(resource_sort_key(r) for r in f.resources), f.activities)


def week_signatures(schedule):
    """[(settimana rappresentante, tutte le settimane con la stessa firma)].
    La firma include attività attive, indisponibilità datate e festivi."""
    year = schedule.period.school_year
    n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
    # ⚠ Maschera **effettiva**: l'originale non si tiene nelle settimane in cui
    # un sostituto lo rimpiazza (ADR-014), e la firma deve dirlo — o due
    # settimane che differiscono per una sostituzione risulterebbero uguali.
    masks = list(effective_week_masks(
        Activity.objects
        .exclude(immobility=Activity.Immobility.SUSPENDED)
        .values_list("id", "week_mask")).items())
    dated = list(ResourceUnavailability.objects
                 .exclude(date=None).values_list("id", "date"))
    holidays = list(Holiday.objects.filter(school_year=year)
                    .values_list("id", "date"))

    def week_of(date):
        return (date - year.first_week_monday).days // 7

    signatures = {}
    for w in range(n_weeks):
        sig = (
            frozenset(i for i, m in masks if weeks.week_in_mask(m, w)),
            frozenset(i for i, d in dated if week_of(d) == w),
            frozenset(i for i, d in holidays if week_of(d) == w),
        )
        signatures.setdefault(sig, []).append(w)
    return [(ws[0], tuple(ws)) for ws in signatures.values()]


def check_schedule(schedule):
    merged = {}
    for representative, wks in week_signatures(schedule):
        state = ScheduleState.build(schedule, week=representative)
        for checker in all_checkers():
            for f in checker.check(state):
                if f.key in merged:
                    combined = tuple(sorted(set(merged[f.key].weeks) | set(wks)))
                    merged[f.key] = replace(merged[f.key], weeks=combined)
                else:
                    merged[f.key] = replace(f, weeks=wks)
    return sorted(merged.values(), key=_finding_sort_key)
