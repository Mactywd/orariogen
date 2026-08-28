"""L'analisi dei vincoli da riga di comando, nel formato di EDT:
enunciato → dettaglio con l'aritmetica → soluzione → azioni. In coda il
riepilogo navigabile che a EDT manca (diagnostica.md). Exit code ≠ 0 se
restano incoerenze: usabile in CI."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.blame import famiglie_silenziose, rank_constraints
from domain.analysis.capacity import analyze_capacity
from domain.analysis.conformity import check_schedule
from domain.analysis.domain_size import residual_domain
from domain.analysis.findings import Severity
from domain.analysis.hall import analyze_hall
from domain.analysis.state import ScheduleState
from domain.extraction import carica
from domain.models import Schedule


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


class Command(BaseCommand):
    help = "Analisi dei vincoli: capienza sui dati e conformità di uno schedule"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int,
                            help="pk dello Schedule di cui verificare la conformità")
        parser.add_argument("--no-hall", action="store_true",
                            help="salta la fase 5 (insiemi non piazzabili)")
        parser.add_argument("--no-blame", action="store_true",
                            help="salta la classifica dei vincoli da allentare")
        parser.add_argument("--blame-top", type=int, default=10,
                            help="quante righe di classifica mostrare (default 10)")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction: restringe S.P., fase 5 "
                                 "e classifica alle attività estratte")

    def handle(self, *args, **options):
        # ⚠ L'estrazione restringe ciò su cui si **agisce**, mai ciò che si
        # **conta**: le tre fasi che rispondono a «cosa mi resta da piazzare»
        # (S.P., insiemi non piazzabili, vincoli da allentare) guardano solo le
        # estratte, mentre l'elenco di conformità resta intero. Un perimetro di
        # lavoro non è la pretesa che il resto sia legale, e filtrare anche le
        # violazioni nasconderebbe proprio quelle che l'estrazione dovrà
        # scavalcare.
        selected = carica(options["estrazione"]) if options["estrazione"] else None
        capacity = analyze_capacity()
        self.stdout.write("== Analisi di capienza ==")
        if not capacity:
            self.stdout.write("Nessun problema di capienza.")
        for i, f in enumerate(capacity, 1):
            self.stdout.write(f"\n[{i}] {f.statement}")
            header = f"    Unità: {f.unit_label}   Materia: {f.subject_label}"
            if f.teacher_label:
                header += f"   Docente: {f.teacher_label}"
            self.stdout.write(header)
            self.stdout.write(f"    Numero di attività: {f.n_activities}")
            self.stdout.write(f"    Durata da piazzare: {_hm(f.required_minutes)}")
            self.stdout.write(f"    Durata piazzabile:  {_hm(f.placeable_minutes)}")
            gap = f.required_minutes - f.placeable_minutes
            self.stdout.write(f"    » {_hm(gap)} non potrà essere piazzata")
            self.stdout.write("    Soluzione:")
            for culprit in f.culprits:
                self.stdout.write(f"      - {culprit}")
            self.stdout.write("    Azioni:")
            for remedy in f.remedies:
                self.stdout.write(f"      - {remedy}")

        hard = 0
        hall = []
        if options["schedule"]:
            schedule = Schedule.objects.get(pk=options["schedule"])
            findings = check_schedule(schedule)
            self.stdout.write(f"\n== Conformità (schedule {schedule.pk}) ==")
            if not findings:
                self.stdout.write("Nessuna violazione.")
            for f in findings:
                hard += f.severity == Severity.HARD
                details = ", ".join(f"{k}={v}" for k, v in sorted(f.quantities.items()))
                self.stdout.write(f"  [{f.severity}] {f.message}  ({details})")
            if selected is not None:
                self.stdout.write(
                    f"\n(perimetro: estrazione «{options['estrazione']}», "
                    f"{len(selected)} attività)")
            state = ScheduleState.build(schedule)
            unplaced = [a for aid, a in sorted(state.activities.items())
                        if aid not in state.placed
                        and (selected is None or aid in selected)]
            if unplaced:
                self.stdout.write("\n== S.P. delle attività non piazzate (crescente) ==")
                sized = sorted(((residual_domain(a, state), a) for a in unplaced),
                               key=lambda pair: pair[0].placements)
                for size, act in sized:
                    self.stdout.write(
                        f"  S.P. {size.placements:3d}  Nr G. {size.days}  "
                        f"{act.subject.name} ({_hm(act.duration_minutes)})")

            if not options["no_hall"]:
                hall = analyze_hall(schedule, selected)
                self.stdout.write("\n== Insiemi non piazzabili (fase 5) ==")
                if not hall:
                    self.stdout.write("Nessun insieme deficiente.")
                for i, f in enumerate(hall, 1):
                    self.stdout.write(f"\n[{i}] {f.statement}")
                    self.stdout.write(
                        "    " + ", ".join(f.resource_labels))
                    self.stdout.write(f"    Risorsa satura: {f.binding_label}")
                    self.stdout.write(f"    Numero di attività: {f.n_activities}")
                    self.stdout.write(
                        f"    Durata da piazzare: {_hm(f.required_minutes)}")
                    self.stdout.write(
                        f"    Durata piazzabile:  {_hm(f.placeable_minutes)}")
                    gap = f.required_minutes - f.placeable_minutes
                    self.stdout.write(f"    » {_hm(gap)} non potrà essere piazzata")
                    self.stdout.write("    Azioni:")
                    for remedy in f.remedies:
                        self.stdout.write(f"      - {remedy}")

            if not options["no_blame"]:
                self._blame(schedule, options["blame_top"], selected)
        elif not options["no_hall"]:
            self.stdout.write(
                "\n== Insiemi non piazzabili (fase 5) ==\n"
                "Saltata: richiede --schedule (legge lo stato, non solo l'anagrafica).")

        if not options["schedule"] and not options["no_blame"]:
            self.stdout.write(
                "\n== Vincoli da allentare ==\n"
                "Saltata: richiede --schedule (legge lo stato, non solo l'anagrafica).")

        self.stdout.write("\n== Riepilogo ==")
        self.stdout.write(f"  {len(capacity)} problemi di capienza, "
                          f"{len(hall)} insiemi non piazzabili, "
                          f"{hard} violazioni hard.")
        if capacity or hall or hard:
            raise CommandError("Rimangono delle incoerenze.")
        self.stdout.write("Verifica terminata: nessuna incoerenza.")

    def _blame(self, schedule, top, selected=None):
        """La classifica dei vincoli per fallimenti causati — la seconda delle
        due lacune di EDT che scope-v1 dichiara nostra occasione: il prodotto
        elenca cosa si può alleggerire, ma non quale alleggerimento serva.

        ⚠ Non contribuisce all'exit code, ed è deliberato: la classifica è un
        consiglio su un orario che può essere sanissimo — ordina la pressione
        anche quando tutto si piazza — mentre l'exit code dice «ci sono
        incoerenze». Confonderli renderebbe rosso ogni orario stretto."""
        report = rank_constraints(schedule, selected=selected)
        self.stdout.write("\n== Vincoli da allentare (per fallimenti causati) ==")
        self.stdout.write(
            f"  {report.considered} attività esaminate, "
            f"{len(report.unplaceable)} senza nessuna collocazione ammissibile.")
        if not report.rows:
            self.stdout.write("  Nessun vincolo esclude collocazioni.")
        for i, r in enumerate(report.rows[:top], 1):
            self.stdout.write(f"\n  [{i}] {r.statement}")
            self.stdout.write(
                f"      Attività che tornerebbero piazzabili: {r.activities_freed}"
                f"   bloccate da questo solo vincolo: {r.activities_blocked}")
            self.stdout.write(
                f"      Celle escluse: {r.cells_blocked}"
                f" (di cui {r.cells_alone} da questo solo vincolo)")
        if len(report.rows) > top:
            self.stdout.write(f"\n  … e altre {len(report.rows) - top} righe "
                              f"(--blame-top per vederne di più).")
        self.stdout.write(
            "\n  Non entrano in classifica, per costruzione: "
            + ", ".join(famiglie_silenziose()) + "."
            "\n  Sono le famiglie in cui piazzare può *riparare* la violazione: "
            "contarle\n  le metterebbe in cima sempre, per un artefatto del "
            "criterio (blame.py).")
