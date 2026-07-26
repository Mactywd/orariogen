"""Maschere di settimane a bit: il bit i è la settimana i dell'anno scolastico
(settimana 0 = quella di first_week_monday). Annuale = tutti i bit; la
sostituzione/eccezione = un bit solo (ADR-014)."""


def full_mask(n_weeks: int) -> int:
    return (1 << n_weeks) - 1


def single_week(index: int) -> int:
    return 1 << index


def week_in_mask(mask: int, index: int) -> bool:
    return bool((mask >> index) & 1)
