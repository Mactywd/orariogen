"""Il verdetto dell'analisi: dataclass mai persistite (principio 2 del design).
Ogni finding porta la causale, la frase italiana già formattata e le quantità
— il verdetto è un numero verificabile, non un aggettivo."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping


class Severity(StrEnum):
    HARD = "hard"            # rosso
    OPTIONAL = "optional"    # giallo: violabile solo con override globale
    PREFERENCE = "preference"  # verde


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: Severity
    resources: tuple[int, ...] = ()    # pk delle Resource coinvolte
    activities: tuple[int, ...] = ()   # pk delle Activity coinvolte
    quantities: Mapping[str, int] = field(default_factory=dict)
    weeks: tuple[int, ...] = ()        # settimane in cui la violazione vale

    @property
    def key(self):
        """Identità per il dedup fra firme di settimana: messaggio e settimane
        esclusi apposta."""
        return (self.code, self.resources, self.activities,
                tuple(sorted(self.quantities.items())))
