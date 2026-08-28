"""L'orario in un file `.ics`, per una risorsa o per tutta la scuola.

⚠ Senza `--out` scrive sullo standard output: un export è una lettura, e non
ha la prudenza che hanno `solve` e `assign_rooms` — non c'è niente da
sovrascrivere."""

from django.core.management.base import BaseCommand, CommandError

from domain import extraction as ex
from domain.ical import LabelsMancanti, esporta
from domain.models import Resource, Schedule, SlotLabel, TimeGrid


class Command(BaseCommand):
    help = "Esporta l'orario di uno schedule in formato iCalendar (.ics)."

    def add_arguments(self, parser):
        parser.add_argument("--schedule", type=int, required=True,
                            help="pk dello schedule da esportare")
        parser.add_argument("--risorsa", type=int, default=None,
                            help="pk della risorsa (docente, classe, parte, "
                                 "aula…): esporta il suo solo orario")
        parser.add_argument("--estrazione", type=str, default=None,
                            help="nome dell'Extraction da esportare")
        parser.add_argument("--out", type=str, default=None,
                            help="file .ics da scrivere (default: stdout)")

    def handle(self, *args, **options):
        schedule = Schedule.objects.get(pk=options["schedule"])
        selected, nome = None, None

        if options["risorsa"] is not None:
            risorsa = Resource.objects.filter(pk=options["risorsa"]).first()
            if risorsa is None:
                raise CommandError(f"risorsa {options['risorsa']} inesistente")
            # 🔑 Riuso di `Estrai`: «le attività di questa risorsa» è già una
            # domanda con una risposta, e ha già i tre versi che ai token non
            # servono (parte → classe, raggruppamento → classi, tutte le aule).
            selected = ex.per_risorsa([risorsa.pk])
            nome = f"Orario — {risorsa.name}"

        if options["estrazione"]:
            estratte = ex.carica(options["estrazione"])
            selected = estratte if selected is None else selected & estratte
            nome = nome or f"Orario — {options['estrazione']}"

        try:
            testo, eventi, saltate = esporta(schedule, selected, nome=nome)
        except LabelsMancanti as manca:
            griglia = TimeGrid.objects.first()
            note = SlotLabel.objects.filter(grid=griglia).count()
            raise CommandError(
                f"Nessuna etichetta oraria per le fasce {sorted(manca.args[0])} "
                f"(la griglia ne ha {note} su {griglia.slots_per_day}). "
                "Un calendario senza orologio non è un calendario, e "
                "indovinare l'ora d'inizio metterebbe in silenzio le lezioni "
                "di tutta la scuola all'ora sbagliata: popola `SlotLabel`.")

        if options["out"]:
            with open(options["out"], "w", encoding="utf-8", newline="") as f:
                f.write(testo)
            self.stdout.write(f"{eventi} eventi in {options['out']} "
                              f"({len(testo.encode('utf-8')) // 1024} KiB)")
            if saltate:
                self.stdout.write(f"{saltate} occorrenze saltate "
                                  f"(festivi o fuori dal periodo).")
        else:
            self.stdout.write(testo, ending="")
