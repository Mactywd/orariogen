"""La **quadratura**: il carico dichiarato dalle cattedre contro quello
erogato dalle attività. È il `+/- = 0` che EDT mostra nella Preparazione, ed è
un predicato sui dati — non sull'orario.

🔑 **Nasce da una misura, non da un'idea** (L10): fino al 2026-08-31 nessuno
leggeva `TeachingAssignment`. Cancellare tutte e 140 le cattedre dell'Alighieri
lasciava il modello duro **identico** — stesse variabili, stessi constraint.
Una tabella che il calcolo non legge non è per questo inerte: è una tabella che
può dire il falso senza che niente lo dica.

🔑 **E diceva il falso.** Il banco dichiarava 140 cattedre tutte su classe
intera mentre 40 attività scendevano a parti e gruppi, e il caso che decide è
il raggruppamento trasversale: NOVEL figurava su `ING 1A`, ORLAN su `ING 1B`,
mentre in verità ognuno dei due insegna a **metà 1A più metà 1B**. I totali
quadravano perché **due errori si annullavano**. La forma piatta non è una
verità più grossolana: su un raggruppamento è una verità falsa, e per il
gestionale delle sostituzioni (ADR-027) è quella che manda il supplente nella
classe sbagliata — anzi, che non nomina nemmeno l'altra.

🔑 **Perciò l'unità è quella dichiarata, non i token.** `activity_tokens`
appiattisce apposta (ADR-017): la classe occupa anche le sue parti e il
raggruppamento occupa le parti membre senza lasciare traccia di sé. È la
lettura giusta per i conflitti e quella cieca per la quadratura, che deve
sapere *a chi* l'ora è erogata. Da qui `state.activity_units`.

🔑 **E si legge per firma di settimana**, che è gratis perché `check_schedule`
già valuta ogni checker una volta per firma su `state.activities`, filtrate
dalla maschera. Non è un dettaglio: misurata **fuori** dalla firma, l'ora
quindicinale del 5B — la sola forma di erogazione che *non costa un'ora* —
risultava costarne una intera (120 dichiarati contro 180 erogati), perché le
due metà complementari venivano sommate. Per firma quadra esatto, 600 contro
600. È lo stesso fenomeno che `CoverageChecker` documenta per i quadrimestri,
e la stessa risposta.

⚠ **Si misura un docente le cui cattedre sono state dichiarate, e solo
quello.** Un docente senza nemmeno una riga non è sbilanciato: è *non
dichiarato*, che è una condizione diversa e precedente — la si nomina nel
questionario d'ingresso, non qui. Senza questa regola ogni frammento di test
con un'attività e nessuna cattedra produrrebbe uno scostamento, e la causale
direbbe «manca un'ora» dove manca invece l'anagrafica. È la stessa costruzione
per cui `CoverageChecker` tace su una classe senza piano di studi.

⚠ **Un'ora senza unità non si conta, ed è un buco dichiarato.** Nel modello
solo `subject` è obbligatorio su un'attività, quindi un'ora può esistere senza
classe, parte né raggruppamento: qui non contribuisce a nessuna chiave, e le
sue ore restano invisibili alla quadratura. Contarle vorrebbe dire inventare
una chiave «nessuna unità» che nessuna cattedra potrà mai pareggiare — un
finding che nessuno può chiudere. ⚠ E nessun rilevatore di `Estrai` la nomina:
i sei sono quelli che EDT ha, e inventarne un settimo sarebbe inventare una
feature. È un buco vero, e resta scritto qui perché non sembri un caso.

⚠ **Non è un vincolo del piazzamento e non ne avrà un builder.** Nessuna
collocazione crea o ripara uno scostamento: il carico è la somma delle durate,
e quella non dipende da dove le ore stanno. `PLACEMENT_INDEPENDENT` lo dichiara
— terzo caso dopo `structural:coverage` e insieme allo scarto, e per la stessa
ragione strutturale."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.registry import Checker, register


@register("structural:workload")
class WorkloadChecker(Checker):
    PLACEMENT_INDEPENDENT = True

    def check(self, state, resources=None):
        dichiaranti = {t for t, _s, _u in state.declared_load}
        if not dichiaranti:
            return

        erogato = defaultdict(int)
        colpevoli = defaultdict(list)
        for aid, act in state.activities.items():
            # ⚠ `.all()` e non `.values_list()`: il secondo scavalca la cache
            # di `prefetch_related` e rifarebbe una query per attività — 343
            # sul banco, per un dato già in memoria.
            for teacher in act.teachers.all():
                tid = teacher.pk
                if tid not in dichiaranti:
                    continue
                for ref in state.activity_units.get(aid, ()):
                    erogato[(tid, act.subject_id, ref)] += act.duration_minutes
                    colpevoli[(tid, act.subject_id, ref)].append(aid)

        for chiave in sorted(set(state.declared_load) | set(erogato)):
            tid, subject_id, ref = chiave
            if resources is not None and tid not in resources:
                continue
            atteso = state.declared_load.get(chiave, 0)
            visto = erogato.get(chiave, 0)
            if atteso == visto:
                continue
            yield Finding(
                "workload_mismatch",
                causali.message(
                    "workload_mismatch",
                    teacher=state.resource_names.get(tid, tid),
                    subject=state.subject_names.get(subject_id, subject_id),
                    unit=state.unit_names.get(ref, ref),
                ),
                Severity.HARD,
                # ⚠ L'unità sta **fra le risorse** e non solo nella frase.
                # Senza, le dodici righe di IRC di uno stesso cappellano —
                # stessa causale, stesso docente, stessa materia, stessi
                # `60 → 0` — sarebbero **un** finding solo, e quale delle
                # dodici sopravvivesse dipenderebbe dall'ordine di
                # iterazione. È il difetto che `Finding.key` documenta su
                # `coverage_mismatch`, nella stessa forma.
                resources=(tid, ref),
                activities=tuple(sorted(colpevoli.get(chiave, ()))),
                quantities={"declared_minutes": atteso, "actual_minutes": visto},
                subject=subject_id,
            )
