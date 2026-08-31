"""Il **questionario d'ingresso**: cosa resta da chiedere alla scuola.

Il gradino 3 di ADR-028. I primi due leggono l'orario dell'anno scorso; questo
elenca il terzo che in nessun orario sta — aule, indisponibilità, vincoli — e
per ognuno dice **cosa succede se non si risponde**.

`--chiudi <chiave>` chiude una domanda, ed è l'unica cosa che il comando
scrive. Serve anche — e soprattutto — quando la risposta è *«niente»*: senza,
una scuola che davvero non ha vincoli di materia resterebbe incompleta per
sempre.
"""

from django.core.management.base import BaseCommand, CommandError

from domain import questionario as Q

_ETICHETTA = {
    Q.MUTO: "MUTO — senza risposta il calcolo sbaglia, e nessuno lo dice",
    Q.ASSENTE: "ASSENTE — senza risposta un pezzo non si fa, e si vede",
    Q.FUORI_CALCOLO: "FUORI CALCOLO — non tocca il calcolo, serve al gestionale",
}


class Command(BaseCommand):
    help = "Cosa resta da chiedere alla scuola perché il calcolo sia completo."

    def add_arguments(self, parser):
        parser.add_argument("--chiudi", metavar="CHIAVE",
                            help="segna la domanda come posta e con risposta "
                                 "(anche se la risposta è «niente»)")
        parser.add_argument("--riapri", metavar="CHIAVE",
                            help="annulla una chiusura data per sbaglio")
        parser.add_argument("--nota", default="",
                            help="chi ha risposto, o cosa ha risposto")
        parser.add_argument("--tutte", action="store_true",
                            help="mostra anche le domande già chiuse")

    def handle(self, *args, **opzioni):
        if opzioni["chiudi"] and opzioni["riapri"]:
            raise CommandError("--chiudi e --riapri insieme non vogliono dire niente")
        if opzioni["riapri"]:
            if not Q.riapri(opzioni["riapri"]):
                raise CommandError(f"non era chiusa: {opzioni['riapri']}")
            self.stdout.write(self.style.SUCCESS(f"Riaperta: {opzioni['riapri']}"))
            return
        if opzioni["chiudi"]:
            try:
                Q.chiudi(opzioni["chiudi"], opzioni["nota"])
            except ValueError as e:
                raise CommandError(str(e))
            self.stdout.write(self.style.SUCCESS(
                f"Chiusa: {opzioni['chiudi']}"))
            return

        tutte = Q.questionario()
        mostrate = tutte if opzioni["tutte"] else [q for q in tutte if q.aperta]
        aperte = [q for q in tutte if q.aperta]
        muti = [q for q in aperte if q.effetto == Q.MUTO]

        self.stdout.write(
            f"\n{len(aperte)} domande aperte su {len(tutte)}"
            f" — {len(muti)} delle quali muta il calcolo se resta senza risposta\n")

        effetto = None
        for q in mostrate:
            if q.effetto != effetto:
                effetto = q.effetto
                self.stdout.write(f"\n  {_ETICHETTA[effetto]}")
            stato = "chiusa" if q.chiusa else "aperta"
            righe = f"{q.righe} righe" if q.righe else "nessuna riga"
            self.stdout.write(f"\n  [{stato}] {q.chiave}  ({righe})")
            self.stdout.write(f"      {q.domanda}")
            self.stdout.write(f"      senza: {q.senza}")
            if q.perimetro:
                p = ", ".join(f"{n} {d}" for d, n in q.perimetro)
                self.stdout.write(f"      perimetro: {p}")
            else:
                self.stdout.write("      perimetro: non si ricava — è un inventario")
            if q.dipende_da:
                self.stdout.write(f"      dopo: {', '.join(q.dipende_da)}")
            if q.oltre_il_modello_duro:
                self.stdout.write(
                    "      ⚠ vive sopra il modello duro: l'ablazione la misura a "
                    "zero, e zero lì non vuol dire inerte")
            elif q.tocca:
                self.stdout.write(f"      accende: {', '.join(q.tocca)}")

        if not opzioni["tutte"] and len(mostrate) < len(tutte):
            self.stdout.write(
                f"\n  ({len(tutte) - len(mostrate)} già chiuse — `--tutte` per vederle)")
        self.stdout.write(
            "\n⚠ Le righe non chiudono una domanda: la chiude `--chiudi`. Una "
            "famiglia\n  vuota e una famiglia mai chiesta hanno le stesse zero "
            "righe.\n")
