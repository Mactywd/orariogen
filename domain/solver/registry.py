"""Il registro dei builder CP-SAT. Stesse chiavi del registro dei predicati
(domain/analysis/registry.py): «una riga di dato, due facce». Package
separato perché domain/analysis non dipenda da ortools — la diagnostica
dev'essere usabile senza tirarsi dietro un solver."""


class Builder:
    """Due tempi diversi, entrambi no-op di default. `restrict` pota il
    dominio *prima* che le variabili esistano — è così che griglia e
    indisponibilità non diventano constraint. `build` posta constraint sulle
    variabili già create. Un builder ne implementa almeno uno."""

    def restrict(self, ctx):
        return None

    def build(self, ctx, model):
        return None


BUILDERS = {}


def register(*keys):
    def decorator(cls):
        for key in keys:
            BUILDERS[key] = cls
        return cls
    return decorator


def all_builders():
    from domain.solver import builders  # noqa: F401 — forza la registrazione
    out, seen = [], set()
    for cls in BUILDERS.values():
        if cls not in seen:
            seen.add(cls)
            out.append(cls())
    return out
