"""L'allineamento: 📦 *«tous les cours ayant le même Ident d'alignement seront
regroupés au sein d'un même cours complexe»* — l'annotazione dello XSD
`Partenaire_Index` su `Alignement` (docs/edt/schema-scambio.md).

L'allineamento **genera l'attività complessa**: le attività che condividono
l'ident non sono due che si somigliano, sono **una** collocazione. È la
condizione perché gli sdoppiamenti — voce ✅ di scope v1 (ADR-013) — producano
orari usabili: senza, metà classe resta a scuola in un'ora in cui non ha
lezione, e l'orario consegnato è sbagliato pur essendo, per tutti gli altri
vincoli, impeccabile.

🔑 **Il verdetto si dà sulle coppie, non sul gruppo.** Nominare il gruppo
intero (`activities` = tutti i membri piazzati) sarebbe più leggibile e
romperebbe la monotonia: piazzare un terzo membro *sulla cella giusta*
allargherebbe `activities`, cambierebbe la `Finding.key` e
`admissible_starts` leggerebbe la cella corretta come inammissibile. Una
voce per **coppia in disaccordo** invece è monotona per costruzione — su un
gruppo concorde una collocazione nuova che concorda non produce nulla, una
che diverge produce esattamente le coppie che ha appena creato — ed è la
proprietà su cui poggia il dominio residuo.

⚠ **Il gruppo incompleto non è una violazione**: un membro piazzato e uno no
è un orario *parziale*, non un orario sbagliato, e chiamarlo violazione
renderebbe rossa ogni costruzione incrementale alla prima attività. Che il
gruppo si piazzi tutto o niente è invece una proprietà del **modello**
(`AlignmentBuilder`), dove c'è la decisione da vincolare; qui c'è un orario,
e ciò che manca lo nomina già `structural:coverage`."""

from collections import defaultdict
from itertools import combinations

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:alignment")
class AlignmentChecker(Checker):
    def check(self, state, resources=None):
        gruppi = defaultdict(list)
        for aid, pl in state.placed.items():
            ident = state.activities[aid].alignment_ident
            if ident:
                gruppi[ident].append(aid)
        for ident, membri in sorted(gruppi.items()):
            for a, b in combinations(sorted(membri), 2):
                pa, pb = state.placed[a], state.placed[b]
                if (pa.day, pa.start_slot) == (pb.day, pb.start_slot):
                    continue
                if resources is not None and not (
                        (state.tokens[a] | state.tokens[b]) & resources):
                    continue
                yield Finding(
                    "alignment_split",
                    causali.message("alignment_split"),
                    Severity.HARD, activities=(a, b),
                    quantities={"day": pa.day, "slot": pa.start_slot,
                                "altro_giorno": pb.day,
                                "altra_fascia": pb.start_slot},
                    group=ident,
                )
