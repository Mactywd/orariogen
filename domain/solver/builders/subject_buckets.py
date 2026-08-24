"""I vincoli di materia che si esprimono come cardinalita' su un **secchio**
(giornata o mezza giornata). L'attivita' si attribuisce al secchio della sua
fascia di **partenza**.

SAME_DAY_INCOMPATIBLE — l'incompatibilità nella giornata.

Con A = B (il caso dominante osservato nei dati reali di EDT: non due ore
della stessa materia nello stesso giorno) è «al più un'occorrenza per unità e
giorno». Con A ≠ B è «le due materie non coesistono nella giornata».
L'attività si attribuisce al giorno della sua fascia di partenza, come nel
checker.

Semplificazione dichiarata: questo builder non distingue le firme di settimana
e tratta tutte le attività come co-attive. È conservativo — può vincolare di
più, mai di meno."""

from domain.models import SubjectConstraint
from domain.solver.registry import Builder, register

T = SubjectConstraint.Type


@register(T.SAME_DAY_INCOMPATIBLE)
class SameDayBuilder(Builder):
    def build(self, ctx, model):
        for row, keys in ctx.subject_rows:
            if row.type != T.SAME_DAY_INCOMPATIBLE:
                continue
            for day in range(ctx.grid.days_per_cycle):
                a = self._literals(ctx, keys, row.subject_a_id, day)
                if row.subject_a_id == row.subject_b_id:
                    if (len({aid for aid, _ in a}) > 1
                            and any(aid in ctx.free for aid, _ in a)):
                        model.Add(sum(lit for _, lit in a) <= 1)
                    continue
                b = self._literals(ctx, keys, row.subject_b_id, day)
                if not a or not b:
                    continue
                if not any(aid in ctx.free for aid, _ in a + b):
                    continue
                ha_a = model.NewBoolVar(f"ha_{row.subject_a_id}_{row.pk}_{day}")
                model.AddMaxEquality(ha_a, [lit for _, lit in a])
                ha_b = model.NewBoolVar(f"ha_{row.subject_b_id}_{row.pk}_{day}")
                model.AddMaxEquality(ha_b, [lit for _, lit in b])
                model.Add(ha_a + ha_b <= 1)

    @staticmethod
    def _literals(ctx, keys, subject_id, day):
        out = []
        for aid, act in ctx.activities.items():
            if act.subject_id != subject_id or not (ctx.tokens[aid] & keys):
                continue
            for (d, s) in sorted(ctx.cells[aid]):
                if d == day:
                    out.append((aid, ctx.x[(aid, d, s)]))
        return out
