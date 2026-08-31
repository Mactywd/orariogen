"""Il calcolo dell'orario da riga di comando, nella forma in cui EDT lo
racconta: le fasi dichiarate mentre girano, gli scarti **nominati** uno per
uno, e cosa è costato ogni criterio.

⚠ Non scrive niente senza `--applica`. Un solve sovrascrive l'orario di una
scuola, e un comando che lo facesse di default sarebbe un modo di perdere il
lavoro di qualcun altro premendo invio. Senza il flag il comando dice cosa
farebbe; con il flag scrive i piazzamenti e **cancella** quelli delle attività
che ha deciso di scartare.

⚠ **I criteri di qualità hanno un budget proprio**, e da qui in poi `--limite`
è un'opzione e non un obbligo: senza, ogni livello di qualità ha
`BUDGET_QUALITA` secondi e i livelli che dimostrano l'ottimo non hanno limite.
Prima il default era «nessun limite ovunque», e sul Fermi con cinque criteri
il comando **non tornava in nove minuti** — una configurazione predefinita che
non termina.

🔑 **E il motivo per cui certi livelli non concludono non è che siano difficili
da ottimizzare: è che sono impossibili da dimostrare.** Misurato sul Fermi:
`gaps` arriva a 0 e lo dimostra in un secondo, perché zero è anche il limite
inferiore banale; `free_half_days` si ferma a 202 con un limite inferiore di
**6** e `regularity` a 236 con **18**. Il divario non è un residuo di ricerca:
è tutto il valore. Il comando lo stampa, perché «ottimo non dimostrato» da solo
non distingue chi ha finito da chi non ha cominciato — e quando valore e limite
coincidono lo dice, così nessuno alza `--limite` per niente.

⚠ **E i lavoratori contano più del limite.** A 15 s per livello, un solo
lavoratore dà `regularity 359` dove quattro danno **236**: `--lavoratori 1`
serve alla riproducibilità e si paga in qualità. Il comando dichiara quanti ne
ha usati, perché un numero di qualità senza quel dato non è confrontabile.

`--popolazione` è la separazione di EDT, che **non cerca mai un ottimo
congiunto**: si ottimizza una popolazione, e `--tolleranza` dichiara di quanto
si accetta che l'altra peggiori rispetto all'orario che c'è. Senza il flag la
catena è unica su tutte le righe — che serve a costruire un orario da zero,
dove non c'è ancora niente da peggiorare.

Exit code ≠ 0 se qualcosa resta scartato: usabile in CI come `analyze`."""

from django.core.management.base import BaseCommand, CommandError

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (Activity, Extraction, QualityCriterion, Resource,
                           Schedule)
from domain.solver.model import apply, solve
from domain.solver.quality import Arbitrato


def _hm(minutes):
    return f"{minutes // 60}h{minutes % 60:02d}"


def _esito(livello):
    """La riga di un livello. Estratta perché sia verificabile senza costruire
    un'istanza che produca *deterministicamente* un divario: farla scattare con
    un solve vero vorrebbe dire dipendere dalla velocità della macchina."""
    valore, divario = livello["valore"], livello["divario"]
    if valore is None:
        return "non concluso"
    if livello["ottimo"]:
        return str(valore)
    if divario == 0:
        # 🔑 Valore e limite inferiore coincidono ma il solver non ha chiuso la
        # dimostrazione: è l'ottimo, e leggerlo come «forse c'è di meglio»
        # manda ad alzare il limite di tempo per niente.
        return f"{valore} (è l'ottimo, non dimostrato)"
    return f"{valore} (ottimo non dimostrato, non sotto {livello['limite']})"


class Command(BaseCommand):
    help = "Calcola l'orario: piazza ciò che ci sta, nomina ciò che scarta"

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True,
                            help="pk dello Schedule da calcolare")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction su cui lavorare "
                                 "(il motore opera esclusivamente su di essa)")
        parser.add_argument("--limite", type=float, default=None,
                            help="limite di tempo in secondi, **per livello** "
                                 "della catena lessicografica")
        parser.add_argument("--lavoratori", type=int, default=None,
                            help="thread di ricerca; 1 rende il calcolo "
                                 "riproducibile")
        parser.add_argument("--ignora-opzionali", nargs="*", default=(),
                            choices=[k for k in Resource.Kind.values],
                            help="categorie di risorsa per cui le "
                                 "indisponibilità gialle non si rispettano")
        parser.add_argument("--popolazione", type=str, default=None,
                            choices=[QualityCriterion.Population.TEACHERS,
                                     QualityCriterion.Population.CLASSES],
                            help="quale popolazione ottimizzare; l'altra non "
                                 "si ottimizza, si impedisce solo che peggiori")
        parser.add_argument("--tolleranza", type=int, default=0,
                            help="perdita di qualità tollerata sulla "
                                 "popolazione non ottimizzata, per criterio e "
                                 "nell'unità del criterio")
        parser.add_argument("--applica", action="store_true",
                            help="scrive i piazzamenti (senza, non tocca nulla)")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        estrazione = None
        if options["estrazione"]:
            estrazione = Extraction.objects.get(name=options["estrazione"])

        arbitrato = None
        if options["popolazione"]:
            arbitrato = Arbitrato(options["popolazione"], options["tolleranza"])

        soluzione = solve(schedule, extraction=estrazione,
                          time_limit=options["limite"],
                          workers=options["lavoratori"],
                          ignora_opzionali=options["ignora_opzionali"],
                          arbitrato=arbitrato)
        stats = soluzione.stats

        self.stdout.write(f"== Calcolo (schedule {schedule.pk}) ==")
        self.stdout.write(f"  Stato: {soluzione.status}")
        self.stdout.write(f"  Attività: {stats['attivita']} "
                          f"({stats['libere']} libere)")
        self.stdout.write(f"  Modello: {stats['variabili']} variabili, "
                          f"{stats['constraint']} constraint")
        # ⚠ I lavoratori si dichiarano perché **cambiano il risultato**, non
        # solo il tempo: misurato sul Fermi a 15 s per livello, un solo
        # lavoratore dà `regularity 359` dove quattro danno 236, e
        # `free_half_days 243` contro 202. Un numero di qualità senza il
        # numero di lavoratori non è confrontabile con nessun altro.
        self.stdout.write(f"  Tempo totale: {stats['secondi']}s "
                          f"({stats['lavoratori'] or 'tutti i core'} in ricerca)")

        if stats["livelli"]:
            self.stdout.write("\n== Criteri, in ordine di priorità ==")
            for i, livello in enumerate(stats["livelli"], 1):
                self.stdout.write(f"  [{i}] {livello['nome']}: {_esito(livello)}"
                                  f"   {livello['secondi']}s")

        if arbitrato is not None:
            self.stdout.write("\n== Arbitrato fra popolazioni ==")
            self.stdout.write(f"  Si ottimizza: {arbitrato.popolazione}")
            self.stdout.write(f"  Perdita tollerata per {arbitrato.sacrificata}: "
                              f"{arbitrato.tolleranza} (per criterio)")
            if not stats["arbitraggi"]:
                self.stdout.write("  Nessun criterio dichiarato su quella "
                                  "popolazione: niente da preservare.")
            for a in stats["arbitraggi"]:
                if a["base"] is None:
                    # ⚠ Dichiarato, mai silenzioso: un tetto non posto cambia
                    # il risultato, e chi legge deve sapere perché manca.
                    self.stdout.write(
                        f"  {a['nome']}: nessun tetto — l'orario di partenza "
                        "non è completo, o una vecchia collocazione non è più "
                        "ammissibile.")
                else:
                    # Dove è atterrato, non solo entro cosa doveva restare: il
                    # margine è ciò che dice se la tolleranza dichiarata è
                    # servita o è rimasta inutilizzata.
                    if a["valore"] is None:
                        dove = "non raggiunto (nessun livello concluso)"
                    elif a["valore"] > a["base"]:
                        dove = (f"atterrato a {a['valore']} "
                                f"(+{a['valore'] - a['base']} sulla base, "
                                f"{a['tetto'] - a['valore']} di margine)")
                    else:
                        dove = (f"atterrato a {a['valore']} "
                                f"({a['base'] - a['valore']} meglio della base)")
                    self.stdout.write(f"  {a['nome']}: base {a['base']}, "
                                      f"tetto {a['tetto']}, {dove}")

        if soluzione.status not in ("OPTIMAL", "FEASIBLE"):
            colpa = ("a bloccare è un vincolo sulle attività congelate o sui "
                     "dati.")
            if any(a["tetto"] is not None for a in stats["arbitraggi"]):
                colpa = ("a bloccare può essere un vincolo sui dati oppure un "
                         "tetto di non-regressione qui sopra: alzare "
                         "`--tolleranza` è la mossa che lo scioglie.")
            raise CommandError(
                "Nessuna soluzione: il modello è infattibile anche ammettendo "
                f"gli scarti. È una diagnosi da `manage.py analyze`, non da qui: {colpa}")

        if soluzione.unplaced:
            self.stdout.write(f"\n== Attività scartate ({len(soluzione.unplaced)}, "
                              f"{_hm(stats['minuti_scartati'])}) ==")
            # ⚠ Si nominano dalle **attività**, non da `check_schedule`: prima
            # di `apply` gli scarti che il solver ha deciso non sono ancora nel
            # database, e il checker racconterebbe l'orario di ieri.
            for act in Activity.objects.filter(
                    pk__in=soluzione.unplaced).select_related("subject"):
                classi = ", ".join(sorted(c.name for c in act.classes.all()))
                docenti = ", ".join(sorted(t.name for t in act.teachers.all()))
                self.stdout.write(f"  {act.subject.name} ({_hm(act.duration_minutes)})"
                                  f"   classi: {classi or '—'}"
                                  f"   docenti: {docenti or '—'}")

        if not options["applica"]:
            self.stdout.write("\nNiente è stato scritto: rilancia con "
                              "`--applica` per salvare i piazzamenti.")
        else:
            apply(soluzione, schedule)
            # ⚠ `room_unassigned` si esclude per la stessa ragione di
            # `activity_unplaced`: descrive un orario **incompleto**, non
            # illegale. Le aule le assegna la seconda fase (`assign_rooms`), e
            # dopo il solo piazzamento ogni attivita' che ne chiede una e'
            # ancora senza — elencarle qui come «violazioni residue» direbbe a
            # chi lancia il comando che l'orario e' sbagliato quando invece non
            # e' ancora finito.
            hard = [f for f in check_schedule(schedule)
                    if f.severity == Severity.HARD
                    and f.code not in ("activity_unplaced", "room_unassigned")]
            self.stdout.write("\nPiazzamenti scritti.")
            if hard:
                self.stdout.write("\n== Violazioni residue ==")
                for f in hard:
                    self.stdout.write(f"  [{f.severity}] {f.message}")
                self.stdout.write(
                    "  (una violazione qui è un alleggerimento consumato o una "
                    "riga già violata dalle attività congelate: `analyze` le "
                    "spiega una per una)")

        if soluzione.unplaced:
            raise CommandError(
                f"{len(soluzione.unplaced)} attività non piazzate "
                f"({_hm(stats['minuti_scartati'])}).")
        self.stdout.write("\nCalcolo terminato: tutte le attività sono piazzate.")
