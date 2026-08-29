"""Copertura del monte ore per (unità-studente × materia): il predicato
anti-inversione STO/SCI. Confronta le attività (piazzate o no) con i servizi
del piano effettivo. È un predicato sui dati, non sull'orario.

🔑 **L'unità-studente è l'atomo** (ADR-020), cioè la combinazione di parti in
cui sta un alunno — una per partizione. Non la parte: un'attività sulla parte
`Y` non porta la chiave della parte `X`, quindi misurando per parte le ore
ricevute attraverso l'**altra** partizione sparirebbero. Con meno di due
partizioni l'atomo *è* la parte, e la chiave non cambia.

🔑 **E il piano è un catalogo, non un curriculum.** Contiene le righe che la
classe riceve, comprese quelle che nessun alunno deve tutte: IRC e attività
alternativa. Le righe in **alternativa** si dichiarano
(`Service.election_group`) e di ognuna l'alunno ne segue **una** — quale, lo
dice l'orario; che debba esserne una, lo dice il dato. Senza il dato restano
due scostamenti su ogni classe italiana, ed è il comportamento giusto: non è
deducibile da nessuna proprietà dell'orario.

🔑 **Ma è un predicato su una settimana**, e non è la stessa cosa. Il monte ore
di un `Service` è **settimanale**, e `check_schedule` valuta ogni checker una
volta per firma di settimana su `state.activities`, che la maschera filtra:
un'ora di Q1 conta nelle settimane di Q1 e non nelle altre. È la lettura
giusta, e l'alternativa apparentemente più naturale — sommare le durate di
tutte le attività, la maschera ignorata — è **sbagliata sul caso più comune
della scuola italiana**: una coppia Q1/Q2 della stessa materia darebbe 120
minuti contro i 60 del piano, cioè segnalerebbe come scostamento il
quadrimestre. Misurato, e tenuto fermo da
`test_le_ore_di_quadrimestre_non_raddoppiano`.

⚠ La conseguenza è che due firme possono dare due verdetti diversi sulla
**stessa** coppia (unità, materia), con `Finding.key` distinte perché le
quantità differiscono. Non è una contraddizione: sono due settimane diverse, e
una materia che sparisce in Q2 *è* uno scostamento in Q2. Ma un dataset le cui
maschere non compongono un monte ore costante — per esempio maschere casuali —
produce `coverage_mismatch` ovunque, ed è una proprietà di quel dataset e non
del checker."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:coverage")
class CoverageChecker(Checker):
    # I finding dipendono solo da attività e servizi anagrafici, mai da come
    # le attività sono piazzate: residual_domain può escluderlo dal loop di
    # prova (vedi domain_size.py).
    PLACEMENT_INDEPENDENT = True

    def check(self, state, resources=None):
        for key, plan_id, unit_name in state.student_units:
            if resources is not None and key not in resources:
                continue
            if key in state.unit_plan_conflict:
                yield Finding(
                    "ambiguous_study_plan",
                    causali.message("ambiguous_study_plan", unit=unit_name),
                    Severity.HARD, resources=(key,),
                    quantities={"plans": state.unit_plan_conflict[key]},
                )
                continue
            expected = state.services_by_plan.get(plan_id, {})
            actual = defaultdict(int)
            colpevoli = defaultdict(list)
            for aid, act in state.activities.items():
                if key in state.tokens[aid]:
                    actual[act.subject_id] += act.duration_minutes
                    colpevoli[act.subject_id].append(aid)
            # ADR-020: le righe in alternativa non si misurano una per una —
            # l'alunno ne segue **una**, e le altre non gli sono dovute.
            gruppi = state.election_groups.get(plan_id, {})
            elettive = {s for subs in gruppi.values() for s in subs}
            for label, subs in sorted(gruppi.items()):
                seguite = [s for s in subs if actual.get(s, 0)]
                if len(seguite) != 1:
                    yield Finding(
                        "election_mismatch",
                        causali.message("election_mismatch", unit=unit_name,
                                        group=label),
                        Severity.HARD, resources=(key,),
                        activities=tuple(sorted(
                            aid for s in seguite for aid in colpevoli[s])),
                        quantities={"followed": len(seguite),
                                    "alternatives": len(subs)},
                        # ⚠ Il gruppo è un campo e non solo una frase: due
                        # gruppi insoddisfatti sulla stessa unità sarebbero
                        # altrimenti lo stesso verdetto (vedi `Finding.key`).
                        group=label,
                    )
                else:
                    # Seguita una sola: resta da misurarne il monte ore, ed è
                    # la misura ordinaria sulla materia che l'alunno fa.
                    elettive.discard(seguite[0])
            for subject_id in sorted(expected.keys() | actual.keys()):
                if subject_id in elettive:
                    continue
                want, got = expected.get(subject_id, 0), actual.get(subject_id, 0)
                if want != got:
                    # ⚠ Le attività nominate sono quelle che **ci sono**, e con
                    # `got < want` sono per definizione troppo poche: il
                    # colpevole è un'attività che non esiste, e nessuna
                    # estrazione può nominarla. Nominare quelle presenti resta
                    # il verdetto utile — sono le righe da cui si corregge il
                    # monte ore — ma non è l'elenco completo delle colpevoli,
                    # perché quell'elenco in un verso non esiste.
                    yield Finding(
                        "coverage_mismatch",
                        causali.message("coverage_mismatch", unit=unit_name,
                                        subject=state.subject_names[subject_id]),
                        Severity.HARD, resources=(key,),
                        activities=tuple(sorted(colpevoli.get(subject_id, ()))),
                        quantities={"expected_minutes": want, "actual_minutes": got},
                        # ⚠ La materia sta nella frase, e la frase è fuori da
                        # `Finding.key` per scelta: senza questo campo due
                        # materie mancanti alla stessa unità per lo stesso
                        # numero di minuti sarebbero **lo stesso finding**, e
                        # la diagnosi ne nominerebbe una sola.
                        subject=subject_id,
                    )
