"""Transizione fra sedi: fra due attività consecutive su sedi diverse servono
site_transition_slots fasce libere (regola semplice di ADR-015 §3)."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.analysis.state import resource_sort_key


@register("structural:site_transition")
class SiteTransitionChecker(Checker):
    def check(self, state, resources=None):
        needed = state.settings.site_transition_slots
        keys = sorted({k for (k, _, _) in state.occupancy}, key=resource_sort_key)
        for key in keys:
            if resources is not None and key not in resources:
                continue
            for day, slots in state.resource_days(key).items():
                sequence = []  # (fascia, sede, attività) per fasce con sede nota
                for s in slots:
                    for aid in state.occupancy[(key, day, s)]:
                        site = state.activities[aid].site_id
                        if site is not None:
                            sequence.append((s, site, aid))
                for (s1, site1, a1), (s2, site2, a2) in zip(sequence, sequence[1:]):
                    if site1 != site2 and s2 - s1 - 1 < needed:
                        yield Finding(
                            "site_transition", causali.message("site_transition"),
                            Severity.HARD, resources=(key,),
                            activities=tuple(sorted({a1, a2})),
                            quantities={"day": day, "gap_slots": s2 - s1 - 1,
                                        "needed_slots": needed},
                        )
