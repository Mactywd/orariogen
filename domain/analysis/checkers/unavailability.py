"""I tre pennelli rosso/giallo/verde, generici sulla risorsa."""

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register

_CODE = {"hard": "unavailability", "optional": "unavailability_optional",
         "preference": "preference"}
_SEV = {"hard": Severity.HARD, "optional": Severity.OPTIONAL,
        "preference": Severity.PREFERENCE}
_ORDER = ["hard", "optional", "preference"]


@register("structural:unavailability")
class UnavailabilityChecker(Checker):
    def check(self, state, resources=None):
        for aid, pl in sorted(state.placed.items()):
            for key in sorted(state.tokens[aid]):
                if resources is not None and key not in resources:
                    continue
                hit = [state.unavailability[(key, pl.day, s)]
                       for s in pl.slots if (key, pl.day, s) in state.unavailability]
                if not hit:
                    continue
                level = min(hit, key=_ORDER.index)
                name = state.resource_names.get(key, str(key))
                yield Finding(
                    _CODE[level], causali.message(_CODE[level], resource=name),
                    _SEV[level], resources=(key,), activities=(aid,),
                    quantities={"day": pl.day, "slots": len(hit)},
                )
