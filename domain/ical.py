"""Export iCal: l'orario nel telefono di chi lo vive.

`scope-v1.md` lo mette **dentro** con una frase sola — *«i docenti vogliono il
proprio orario nel telefono»* — ed è l'unica voce di quell'elenco che non
riguarda il calcolo: tutto il resto di questo repository produce un orario, e
questo è il primo pezzo che lo **consegna**. In EDT il canale esiste ed è
esattamente questo (`UtilitaireSco_ExportICal`, e `ImpEDT_ExportICALRencontre`
/ `ImpEDT_ExportICALConseil` per colloqui e consigli), dichiarato dalle
stringhe come *«il canale verso l'esterno / verso il calendario personale»*,
distinto da `Partenaire_Index` che è quello verso gli altri gestionali.

🔑 **E l'export è il punto in cui la fascia di calcolo smette di essere l'ora.**
`tempo-e-calendario.md` distingue per nome due grandezze che tutto il resto del
progetto ha potuto confondere impunemente, perché il motore ne usa una sola: la
**fascia di calcolo** (l'unità del piazzamento e dell'ora di servizio) e
l'**etichetta oraria** (*«ad esempio 55 minuti»*, orari sfalsati). Un calendario
legge la seconda: un evento alle 08:00 che dura 55 minuti è un fatto sul
telefono, mentre «un'ora di servizio» non lo è. Quindi qui `SlotLabel` è
obbligatorio e `slot_minutes` **non compare**.

🔑 **Un'attività non è sempre un evento.** Se l'orologio salta fra due fasce
consecutive — la pausa di mezza giornata è il caso normale, `12:00` che riprende
alle `14:00` — un blocco da due fasce a cavallo della linea non è una lezione di
quattro ore: sono due lezioni. Le fasce si spezzano quindi in **corse contigue**
nel tempo dell'orologio, una per evento. Sommare `duration_minutes` a
`start_time` avrebbe dato la risposta giusta su ogni scuola senza pausa e
sbagliata su tutte le altre, senza mai fallire rumorosamente.

⚠ **Niente `RRULE`, ed è una decisione.** «Ogni lunedì» sarebbe più compatto e
il telefono lo mostrerebbe come ricorrenza, ma la maschera di settimane non è
una ricorrenza: annuale e quadrimestre lo sono, la sostituzione di ADR-014 (un
bit solo) e l'`Amenagement` no, e festivi e confini di periodo andrebbero
elencati in `EXDATE` uno per uno. Si emette quindi un `VEVENT` per occorrenza —
corretto per **qualunque** maschera, e con il prezzo misurato invece che
temuto (vedi `tests/test_ical.py`).

⚠ **Ora locale fluttuante**, senza `TZID` e senza `VTIMEZONE`: le 08:00 di una
scuola sono le 08:00 dell'orologio alla parete, non un istante UTC. È anche
l'unica forma che attraversa il cambio d'ora senza spostare le lezioni di
un'ora per metà anno.

🔑 **E la sostituzione oscura l'originale** (2026-08-31). Per ADR-014 il
sostituto è una riga di `Activity` con un bit solo, quindi compare da sé; ma
l'originale è annuale — 161 su 161 nella base di EDT — e senza la relazione fra
i due continuava a comparire nella stessa settimana, cioè il calendario di una
settimana con sostituzione portava **due** eventi invece di uno.
`Activity.substitutes` è quella relazione (`RELATIONCOURSSUBSTITUT`), e la
*soppressione dell'occorrenza* che ADR-014 chiedeva ne discende invece di
essere una seconda tabella. ⚠ Il filtro non vive qui: `effective_week_masks`
sta sul modello e lo leggono tutti e quattro i lettori di maschere — le firme
di settimana, lo stato, la capienza e questo export — perché l'orario di quella
settimana è uno solo, e un calendario che mostrasse una cosa e i checker
un'altra sarebbe il difetto con un passo in più.
"""

import datetime as dt
from dataclasses import dataclass

from domain import weeks
from domain.models import (
    Activity, Holiday, Placement, SlotLabel, TimeGrid, effective_week_masks,
)

PRODID = "-//orariogen//Orario scolastico//IT"


@dataclass(frozen=True)
class Occorrenza:
    """Una lezione in un giorno preciso: la coppia (attività, data) risolta in
    un intervallo di orologio. `slots` sono le fasce che questo evento copre —
    non necessariamente tutte quelle dell'attività, se l'orologio salta."""

    activity: Activity
    date: dt.date
    start: dt.time
    end: dt.time
    slots: tuple

    @property
    def uid(self):
        """Stabile fra due export dello stesso orario: un calendario che
        riceve due volte lo stesso UID **aggiorna** invece di duplicare, ed è
        la differenza fra ripubblicare e sporcare l'agenda di un docente. La
        fascia entra nell'UID perché un'attività spezzata dà due eventi lo
        stesso giorno."""
        return f"{self.activity_id}-{self.date:%Y%m%d}-{self.slots[0]}@orariogen"

    @property
    def activity_id(self):
        return self.activity.pk


class LabelsMancanti(Exception):
    """Nessun orologio per una fascia usata. Si rifiuta, non si indovina."""


def _labels(grid):
    return {sl.slot: sl for sl in SlotLabel.objects.filter(grid=grid)}


def _corse(labels, start_slot, duration_slots):
    """Le corse **contigue nel tempo dell'orologio** fra le fasce occupate.

    Contigue significa `fine della fascia i == inizio della fascia i+1`: la
    pausa di mezza giornata è precisamente la sua negazione. Restituisce
    `[(fasce, ora d'inizio, ora di fine)]`, dove la fine è quella dichiarata
    dall'**ultima** fascia della corsa e mai `inizio + durata`."""
    usate = range(start_slot, start_slot + duration_slots)
    mancanti = [s for s in usate if s not in labels]
    if mancanti:
        raise LabelsMancanti(mancanti)

    out, corsa = [], [start_slot]
    for s in usate[1:]:
        if labels[s].start_time == labels[s - 1].end_time:
            corsa.append(s)
        else:
            out.append(tuple(corsa))
            corsa = [s]
    out.append(tuple(corsa))
    return [(c, labels[c[0]].start_time, labels[c[-1]].end_time) for c in out]


def occorrenze(schedule, selected=None):
    """Espande i piazzamenti in eventi datati.

    Tre filtri, e sono tre entità distinte del modello: la **maschera** dice in
    quali settimane l'attività esiste, il **periodo** dello schedule dice fin
    dove quell'orario vale (ADR-010: se ne rigenera uno per periodo, e il
    calendario del primo quadrimestre non deve invadere il secondo), i
    **festivi** tolgono le date in cui la scuola è chiusa.

    `selected` è l'estrazione, con la stessa regola di sempre: restringe ciò su
    cui si agisce. Qui «agire» è pubblicare, quindi restringe davvero l'uscita
    — non c'è niente da contare, un calendario non è una diagnosi."""
    grid = TimeGrid.objects.first()
    labels = _labels(grid)
    period = schedule.period
    year = period.school_year
    festivi = set(Holiday.objects.filter(school_year=year)
                  .values_list("date", flat=True))
    n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1

    piazzamenti = (Placement.objects.filter(schedule=schedule)
                   .exclude(activity__immobility=Activity.Immobility.SUSPENDED)
                   .select_related("activity", "activity__subject",
                                   "activity__site", "assigned_room")
                   .prefetch_related("activity__teachers", "activity__classes",
                                     "activity__parts", "activity__groups",
                                     "activity__rooms")
                   .order_by("day", "start_slot", "activity_id"))

    maschere = effective_week_masks(
        (pl.activity_id, pl.activity.week_mask) for pl in piazzamenti)
    out, saltate = [], 0
    for pl in piazzamenti:
        act = pl.activity
        if selected is not None and act.pk not in selected:
            continue
        corse = _corse(labels, pl.start_slot, act.duration_slots)
        for w in range(n_weeks):
            # La maschera **effettiva**: nella settimana in cui un sostituto
            # rimpiazza questa lezione, l'originale non compare.
            if not weeks.week_in_mask(maschere[act.pk], w):
                continue
            data = year.first_week_monday + dt.timedelta(weeks=w, days=pl.day)
            if not (period.start_date <= data <= period.end_date):
                saltate += 1
                continue
            if data in festivi:
                saltate += 1
                continue
            for fasce, inizio, fine in corse:
                out.append(Occorrenza(act, data, inizio, fine, fasce))
    out.sort(key=lambda o: (o.date, o.start, o.activity_id))
    return out, saltate


# --- resa RFC 5545 ---------------------------------------------------------

def _escape(testo):
    """RFC 5545 §3.3.11: nel tipo TEXT si sfuggono backslash, punto e virgola,
    virgola e a capo. ⚠ Il backslash per primo, o si sfuggirebbero due volte
    quelli appena introdotti."""
    return (testo.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _piega(riga):
    """RFC 5545 §3.1: nessuna riga oltre 75 **ottetti**, e la continuazione
    comincia con uno spazio. Si conta in ottetti e non in caratteri perché
    «MATEMATICA» e «Matemàtica» non occupano lo stesso spazio, e si taglia su
    un confine di carattere per non spezzare un UTF-8 a metà."""
    grezza = riga.encode("utf-8")
    if len(grezza) <= 75:
        return [riga]
    fuori, resto = [], riga
    limite = 75
    while len(resto.encode("utf-8")) > limite:
        taglio = limite
        while len(resto[:taglio].encode("utf-8")) > limite:
            taglio -= 1
        fuori.append(resto[:taglio])
        resto = resto[taglio:]
        limite = 74           # la continuazione spende un ottetto per lo spazio
    fuori.append(resto)
    return [fuori[0]] + [" " + p for p in fuori[1:]]


def _unita(act):
    return sorted([c.name for c in act.classes.all()]
                  + [p.name for p in act.parts.all()]
                  + [g.name for g in act.groups.all()])


def _vevent(occ, dtstamp, aula_di):
    act = occ.activity
    unita = _unita(act)
    docenti = sorted(t.name for t in act.teachers.all())
    titolo = act.subject.name
    if unita:
        titolo += " · " + ", ".join(unita)

    descrizione = []
    if docenti:
        descrizione.append("Docenti: " + ", ".join(docenti))
    if unita:
        descrizione.append("Classi: " + ", ".join(unita))

    aula = aula_di.get(act.pk)
    luogo = aula or (act.site.name if act.site_id else "")

    righe = [
        "BEGIN:VEVENT",
        f"UID:{occ.uid}",
        f"DTSTAMP:{dtstamp:%Y%m%dT%H%M%SZ}",
        # Ora locale fluttuante: nessun suffisso Z, nessun TZID.
        f"DTSTART:{occ.date:%Y%m%d}T{occ.start:%H%M%S}",
        f"DTEND:{occ.date:%Y%m%d}T{occ.end:%H%M%S}",
        f"SUMMARY:{_escape(titolo)}",
    ]
    if descrizione:
        righe.append("DESCRIPTION:" + _escape("\n".join(descrizione)))
    if luogo:
        righe.append(f"LOCATION:{_escape(luogo)}")
    righe.append("END:VEVENT")
    return righe


def render(occs, schedule, dtstamp=None, nome=None):
    """Il testo `.ics`, con terminatori CRLF come vuole RFC 5545 §3.1."""
    dtstamp = dtstamp or dt.datetime.now(dt.timezone.utc)
    aula_di = dict(Placement.objects.filter(schedule=schedule)
                   .exclude(assigned_room=None)
                   .values_list("activity_id", "assigned_room__name"))

    righe = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    if nome:
        righe.append(f"X-WR-CALNAME:{_escape(nome)}")
    for occ in occs:
        righe.extend(_vevent(occ, dtstamp, aula_di))
    righe.append("END:VCALENDAR")

    piegate = []
    for r in righe:
        piegate.extend(_piega(r))
    return "\r\n".join(piegate) + "\r\n"


def esporta(schedule, selected=None, dtstamp=None, nome=None):
    """Il percorso completo: `(testo ics, quante occorrenze, quante saltate)`."""
    occs, saltate = occorrenze(schedule, selected)
    return render(occs, schedule, dtstamp=dtstamp, nome=nome), len(occs), saltate
