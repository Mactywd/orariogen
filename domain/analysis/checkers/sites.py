"""Transizione fra sedi: fra due attività consecutive su sedi diverse servono
site_transition_slots fasce libere (regola semplice di ADR-015 §3)."""

from itertools import product

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register
from domain.analysis.state import resource_sort_key, site_occupation


def _carico(state, key, attivita):
    """Quanti membri della chiave impegna quel gruppo di attività — la stessa
    lettura di `OccupationChecker`, che è ciò che rende confrontabili le due
    quantità: `material_quantity` dove c'è, 1 altrove."""
    return sum(state.material_quantity.get((aid, key), 1) for aid in attivita)


@register("structural:site_transition")
class SiteTransitionChecker(Checker):
    """🔑 **Essere in due sedi insieme è impossibile, e resta una violazione.**
    A differenza di `MAX_SITE_CHANGES`, che conta i viaggi e quindi non ne
    vede nessuno dentro una fascia, qui la domanda è se il tragitto ci sta:
    due sedi sulla stessa fascia danno `gap_slots = -1`, minore di
    **qualunque** soglia, anche zero. È la semantica che
    `SiteTransitionBuilder` traduce già con una clausola dedicata, e resta.

    ⚠ Ciò che cambia è **come** si trovano le coppie. Appiattire
    `state.occupancy` in una sequenza le faceva dipendere dall'ordine
    d'inserimento: a capienza cumulativa, con `[A@0, B@0, A@1]` le coppie
    adiacenti sono `(A,B)` e `(B,A)` — due violazioni — mentre con `[B@0,
    A@0, A@1]` sono `(B,A)` e `(A,A)`, e la seconda sparisce. Lo stesso
    orario, due verdetti, a decidere i pk. Ora le coppie si enumerano dagli
    **insiemi** di `site_occupation`: tutte quelle interne a una fascia, e
    tutte quelle incrociate fra due fasce consecutive della sottosequenza.
    A capienza 1 ogni insieme è un singoletto e l'enumerazione è riga per
    riga la vecchia; dove differisce restituisce sempre il caso peggiore che
    l'ordine poteva produrre — cioè si allinea a `SiteTransitionBuilder`, che
    quelle coppie le postava già tutte.

    🔑 **Un insieme non viaggia** (L6, 2026-08-31). Il tragitto lo fa un
    **corpo**, e una chiave a capienza cumulativa non è un corpo: quattro
    carrelli di portatili sono della scuola, non di un edificio, e servono
    l'inglese alla centrale mentre l'informatica è in succursale senza che
    nessuno si sposti. Fino a qui la domanda era «due sedi si toccano?»; ora è
    quella giusta — «**ci stanno**?»: il carico della sede *sa* alla fascia *s*
    più quello della sede *sb* alla fascia *t* deve stare dentro la capienza,
    perché i membri impegnati di qua non possono essere gli stessi di là.

    🔑 **A capienza 1 la regola coincide riga per riga con la vecchia**, e non
    è un'approssimazione: ogni gruppo pesa almeno 1, quindi la somma è almeno
    2 e la capienza è 1 — la coppia è **sempre** una violazione, com'era. La
    generalizzazione non tocca dunque nessuna chiave di docente, classe o
    parte; tocca l'aula col `Numero di aule` di EDT e il materiale con
    quantità, che sono esattamente le due risorse per cui la vecchia regola
    diceva una cosa falsa.

    ⚠ **Resta una condizione a coppie**, non su tutta la finestra: due gruppi
    per volta, come prima. La forma esatta chiederebbe che l'intera domanda
    dentro una finestra di trasferimento stia nella capienza; quella a coppie
    è più larga, e più larga è il verso in cui un checker non inventa
    violazioni. Dove la capienza è 1 — cioè ovunque salvo le due risorse
    dette — le due formulazioni coincidono."""

    def check(self, state, resources=None):
        needed = state.settings.site_transition_slots
        keys = sorted({k for (k, _, _) in state.occupancy}, key=resource_sort_key)
        for key in keys:
            if resources is not None and key not in resources:
                continue
            cap = state.capacity.get(key, 1)
            for day, slots in state.resource_days(key).items():
                occ = site_occupation(state, key, day, slots)
                coppie = []  # (fasce di scarto, attività di qua, attività di là)
                for _, per_site in occ:               # dentro la fascia
                    sedi = sorted(per_site)
                    coppie += [(-1, per_site[sedi[i]], per_site[sedi[j]])
                               for i in range(len(sedi))
                               for j in range(i + 1, len(sedi))]
                for (s1, primo), (s2, secondo) in zip(occ, occ[1:]):
                    coppie += [(s2 - s1 - 1, primo[site1], secondo[site2])
                               for site1 in sorted(primo)
                               for site2 in sorted(secondo)
                               if site1 != site2]
                for gap, di_qua, di_la in coppie:
                    if gap >= needed:
                        continue
                    if (_carico(state, key, di_qua)
                            + _carico(state, key, di_la)) <= cap:
                        continue   # un insieme non viaggia: ci stanno tutti
                    for a1, a2 in product(sorted(di_qua), sorted(di_la)):
                        yield Finding(
                            "site_transition",
                            causali.message("site_transition"),
                            Severity.HARD, resources=(key,),
                            activities=tuple(sorted({a1, a2})),
                            quantities={"day": day, "gap_slots": gap,
                                        "needed_slots": needed},
                        )
