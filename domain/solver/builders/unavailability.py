"""Indisponibilita' rossa **e gialla**: pre-filtro del dominio, su **tutta**
la durata dell'attivita'. Il checker itera su tutte le fasce del piazzamento,
quindi un filtro che guardasse solo la cella di partenza lascerebbe passare
un'attivita' di durata >= 2 con la coda sull'indisponibilita'.

⚠ **Il giallo si rispetta come il rosso**, ed e' una correzione del
2026-08-26: fino a lì questo builder lo ignorava del tutto, cioe' si comportava
come se l'override fosse sempre acceso. La documentazione dice il contrario —
*«Indisponibilita' opzionali (giallo): rispettata come una rossa, ma l'utente
puo' autorizzare il motore a ignorarle per risolvere le attivita' scartate»*
(`docs/edt/estratti/inventario-vincoli.md`, A2). Il solver era quindi **piu'
permissivo di EDT** su una famiglia intera.

L'autorizzazione esiste, ed e' un'**opzione di calcolo per tipo di risorsa**,
non una quota: *«Piazza le attivita' anche sulle fasce con indisponibilita'
opzionali»*, declinata sulle cinque risorse (L7). Non e' selettiva sul singolo
docente: si attiva per tutta la categoria (A4). Da qui il parametro
`ignora_opzionali` di `build_model`, che porta i `Resource.Kind` da ignorare.

Il verde non restringe nulla: e' una preferenza, e il suo posto e' un livello
di qualita' della catena lessicografica, non un pre-filtro."""

from collections import defaultdict

from domain.solver.registry import Builder, register


@register("structural:unavailability")
class UnavailabilityBuilder(Builder):
    @staticmethod
    def _ignorata(ctx, stato, key):
        """L'override delle gialle: per **tipo** di risorsa, mai per la singola
        (A4). Una chiave-atomo (ADR-017) non ha un tipo proprio: eredita quello
        della parte di classe da cui nasce, e in `kinds` non compare — nel
        dubbio si **rispetta** l'indisponibilita', che e' il default di EDT."""
        return stato.kinds.get(key) in ctx.ignora_opzionali
    def restrict(self, ctx):
        blocked = {}
        for rep, _ in ctx.signatures:
            stato = ctx.states[rep]
            per_key = defaultdict(set)
            for (key, day, slot), level in stato.unavailability.items():
                if level == "hard":
                    per_key[key].add((day, slot))
                elif level == "optional" and not self._ignorata(ctx, stato, key):
                    per_key[key].add((day, slot))
            blocked[rep] = per_key

        for aid in ctx.free:
            act = ctx.activities[aid]
            forbidden = set()
            for rep, _ in ctx.signatures:
                if aid not in ctx.states[rep].activities:
                    continue
                per_key = blocked[rep]
                for key in ctx.tokens[aid]:
                    forbidden |= per_key.get(key, set())
            if not forbidden:
                continue
            ctx.cells[aid] = {
                (day, slot) for (day, slot) in ctx.cells[aid]
                if not any((day, s) in forbidden
                           for s in range(slot, slot + act.duration_slots))
            }
