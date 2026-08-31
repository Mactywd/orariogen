"""`Ricava`: legge una griglia oraria già letta e propone piani e cattedre.

⚠ **Non è un lettore di file d'orario, ed è una scelta.** ADR-028 esclude di
scriverne un secondo: quello di Aurora è a grammatica chiusa, con descrittori,
giudice e verdetto, e attorno gli è cresciuta una proprietà che non si butta —
ogni scuola che importa un formato nuovo lascia dietro di sé un test. Qui entra
la griglia **già letta**, nella forma in cui Aurora la consegnerebbe: le righe
di `ScheduleEntry`.

Di suo il comando **non scrive**: stampa la proposta e ciò che di essa non è
affidabile. Serve `--applica` per scrivere, ed è la disciplina del giudice —
`analyze` propone, l'utente vede, `import` scrive.
"""

import json

from django.core.management.base import BaseCommand, CommandError

from domain.bootstrap import Lezione, applica, ricava

#: I nomi accettati per ogni ruolo. Sono cinque come i ruoli del descrittore di
#: Aurora, e la materia è l'unico non obbligatorio — là e qui.
CAMPI = {
    "teacher": ("teacher", "docente"),
    "day": ("day", "weekday", "giorno"),
    "slot": ("slot", "period", "period_number", "ora", "fascia"),
    "school_class": ("school_class", "class", "class_name", "classe"),
    "subject": ("subject", "materia"),
}

GIORNI = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
          "saturday": 5, "sunday": 6}


def _campo(riga, ruolo):
    for nome in CAMPI[ruolo]:
        if nome in riga:
            return riga[nome]
    return None


def _lezione(riga, n):
    valori = {r: _campo(riga, r) for r in CAMPI}
    for ruolo in ("teacher", "day", "slot", "school_class"):
        if valori[ruolo] is None:
            raise CommandError(
                f"riga {n}: manca il ruolo «{ruolo}». I quattro obbligatori sono "
                f"docente, giorno, fascia e classe; la materia no.")
    giorno = valori["day"]
    if isinstance(giorno, str):
        # I giorni di Aurora sono nomi inglesi; la fascia è **0-based** da noi,
        # e chi manda `period_number` di solito conta da 1. Non lo si indovina:
        # si accettano i nomi e si lascia il numero com'è.
        if giorno.lower() not in GIORNI:
            raise CommandError(f"riga {n}: giorno «{giorno}» non riconosciuto")
        giorno = GIORNI[giorno.lower()]
    return Lezione(teacher=str(valori["teacher"]), day=int(giorno),
                   slot=int(valori["slot"]),
                   school_class=str(valori["school_class"]),
                   subject=None if valori["subject"] is None else str(valori["subject"]))


class Command(BaseCommand):
    help = ("Ricava piani di studi e cattedre da una griglia oraria già letta "
            "(JSON nella forma di ScheduleEntry)")

    def add_arguments(self, parser):
        parser.add_argument("griglia", type=str,
                            help="file JSON: un elenco di righe (docente, giorno, "
                                 "fascia, classe, materia)")
        parser.add_argument("--applica", action="store_true",
                            help="scrive la proposta invece di solo mostrarla")
        parser.add_argument("--replace", action="store_true",
                            help="con --applica: svuota prima di scrivere")
        parser.add_argument("--slot-minutes", type=int, default=60)
        parser.add_argument("--morning-end-slot", type=int, default=None,
                            help="la prima fascia del pomeriggio. Senza, la "
                                 "giornata è tutta mattina — e la linea è il "
                                 "perimetro del buco e della mezza giornata libera")

    def handle(self, *args, **options):
        try:
            dati = json.loads(open(options["griglia"], encoding="utf-8").read())
        except OSError as e:
            raise CommandError(f"non riesco a leggere la griglia: {e}")
        if not isinstance(dati, list):
            raise CommandError("il file deve contenere un elenco di righe")
        proposta = ricava(_lezione(r, n) for n, r in enumerate(dati, 1))
        self._referto(proposta)
        if options["applica"]:
            applica(proposta, slot_minutes=options["slot_minutes"],
                    morning_end_slot=options["morning_end_slot"],
                    replace=options["replace"])
            self.stdout.write(self.style.SUCCESS("\nScritto."))
        else:
            self.stdout.write("\nNiente è stato scritto. Usa --applica.")

    def _referto(self, p):
        w = self.stdout.write
        w(self.style.MIGRATE_HEADING("Ciò che la griglia dice"))
        w(f"  {len(p.teachers)} docenti · {len(p.classes)} classi · "
          f"{len(p.subjects)} materie · griglia {p.days} × {p.slots_per_day}")
        w(f"  {len(p.assignments)} cattedre")

        if p.splits:
            w(self.style.MIGRATE_HEADING("\nSdoppiamenti visti"))
            w("  Due lezioni nella stessa fascia: l'ora vale **una** per l'alunno.")
            for s in p.splits:
                celle = ", ".join(f"g{g}f{f}" for g, f in s.cells)
                w(f"  {s.school_class} / {s.subject or '—'}: "
                  f"{s.streams} contemporanee su {celle}")

        if p.groupings:
            w(self.style.MIGRATE_HEADING("\nRaggruppamenti trasversali visti"))
            w("  Un docente in più classi nella stessa fascia. ⚠ Non si "
              "distingue da una classe dal nome composto: lo scioglie chi guarda.")
            for r in p.groupings:
                w(f"  {r.teacher} / {r.subject or '—'}: {', '.join(r.classes)}")

        w(self.style.MIGRATE_HEADING("\nCiò che la griglia NON dice"))
        w("  Un quadro orario ricavato può essere gonfiato, e la griglia non lo "
          "dice. Va guardato prima di fidarsene:")
        for nome, spiegazione in p.cecita:
            w(f"  · {nome}: {spiegazione}")
        w(self.style.WARNING(
            "\n  Non si ricavano: le partizioni (chi sta in quale metà è "
            "anagrafica di alunni), le attività (nascono dalla ripartizione) e "
            "il calendario (sono date)."))
