"""Il registro dei checker: la struttura in cui «ogni vincolo esiste due
volte» (principio 4). Ogni tipo di vincolo dello schema ha una voce; il
piano CP-SAT aggancerà il builder alla stessa voce."""


class Checker:
    """`check()` produce i findings sullo stato. `resources`, se dato, è un
    filtro di ottimizzazione: il checker può saltare il lavoro sulle risorse
    fuori dall'insieme, ma i findings che le toccano devono restare completi."""

    # True per i checker i cui finding non dipendono dal piazzamento (solo dai
    # dati anagrafici): residual_domain può escluderli dal loop di prova, il
    # delta rispetto alla baseline è comunque sempre vuoto.
    PLACEMENT_INDEPENDENT = False

    # True per i checker **monotoni**: piazzare un'attività in più non può che
    # *aggiungere* o *aggravare* violazioni, mai ripararne una né spostarne
    # l'identità senza aggravarla. È la proprietà su cui poggia il criterio di
    # `admissible_starts` («una chiave nuova rispetto alla baseline significa
    # che la cella è inammissibile»): se non vale, una cella che *migliora* la
    # situazione produce comunque una chiave nuova e viene scartata a torto.
    # Default True; le famiglie che non lo sono lo dichiarano False e portano
    # nel proprio docstring il perché. Vedi domain/analysis/domain_size.py.
    PLACEMENT_MONOTONE = True

    def check(self, state, resources=None):
        raise NotImplementedError


REGISTRY = {}


def register(*keys):
    def decorator(cls):
        for key in keys:
            REGISTRY[key] = cls
        return cls
    return decorator


def all_checkers():
    from domain.analysis import checkers  # noqa: F401 — forza la registrazione
    out, seen = [], set()
    for cls in REGISTRY.values():
        if cls not in seen:
            seen.add(cls)
            out.append(cls())
    return out
