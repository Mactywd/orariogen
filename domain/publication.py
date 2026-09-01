"""La **pubblicazione**: da `Placement` alla griglia piatta di Aurora.

ADR-027 §3.2 — l'uscita del generatore non è un secondo orario accanto a
quello che il motore delle sostituzioni già legge, è **quello**. Una riga di
`ScheduleEntry` dice *chi insegna, quando, a chi*, e questo modulo è la
funzione che la ricava dai piazzamenti.

🔑 **Appiattire perde, e la perdita si nomina invece di evitarla** — è la
scelta di ADR-027, e questo modulo la rende esplicita: `pubblica` restituisce
le righe **e** un `Perdita` che dice, contato, che cosa la griglia non ha
saputo tenere. Un'uscita che perde in silenzio sarebbe la stessa uscita con un
bug in meno da trovare e uno in più da subire.

⚠ **La maschera di settimana non è più una perdita, ed è cambiata da poco.**
Fino a L9 la griglia di Aurora non aveva un asse su cui metterla, e l'ora
quindicinale usciva come un'ora annuale — cioè come una cosa **falsa** una
settimana su due. Ora `ScheduleEntry.iso_week_mask` c'è. Ma i due indici non
sono lo stesso: da noi il bit *w* è la settimana che comincia a
`SchoolYear.first_week_monday + 7w`, in Aurora è la settimana **ISO**. La
conversione sta qui, e sta qui perché noi un anno scolastico ce l'abbiamo e
Aurora no: è l'unico posto del confine dove esiste l'ancora che serve a farla.

🔑 **E il periodo attraversa il confine dentro la maschera.** ADR-010 dice che
un orario si *rigenera* a ogni periodo; Aurora non ha un campo per dire da
quando a quando una riga vale. Ma la maschera è esattamente quel campo, se le
si intersecano le settimane del periodo: due schedule di due quadrimestri
pubblicano su maschere disgiunte e convivono nella stessa tabella, senza che
nessuno debba cancellare il primo per scrivere il secondo.
"""

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field

from domain.models import (Activity, Placement, SchoolYear,
                           effective_week_masks)

#: I giorni che `ScheduleEntry.WEEKDAY_CHOICES` conosce. ⚠ Sono **cinque**:
#: Aurora non ha il sabato, e una scuola che fa sei giorni non è pubblicabile
#: oggi. Non è un dettaglio da aggirare qui — sarebbe una riga di lunedì per
#: una lezione di sabato — quindi le ore del sesto giorno si contano nella
#: perdita e non escono.
GIORNI = ("monday", "tuesday", "wednesday", "thursday", "friday")


@dataclass(frozen=True)
class Riga:
    """Una riga di `ScheduleEntry`, nei termini di Aurora."""
    teacher: str
    weekday: str
    period_number: int
    school_class: str
    subject: str
    iso_week_mask: int

    @property
    def chiave(self):
        """L'unicità di Aurora **meno la maschera**: due righe con questa
        chiave uguale sono la stessa cella dello stesso docente, e vanno
        fuse o dichiarate ambigue."""
        return (self.teacher, self.weekday, self.period_number,
                self.school_class)


@dataclass
class Perdita:
    """Cosa la griglia piatta non tiene, contato invece che previsto.

    ⚠ **Le voci non sono tutte della stessa gravità**, e la distinzione è di
    ADR-027: un raggruppamento trasversale fa dire ad Aurora una cosa **vera e
    incompleta** — «Novelli insegna a 1A» dove insegna a metà di 1A — e il
    supplente serve comunque; un'ora di sabato o un'attività senza docente
    **non escono affatto**. La prima è un'approssimazione con cui Aurora già
    convive, le altre due sono buchi.
    """
    #: attività il cui soggetto è una parte di classe: esce la classe intera
    parti: int = 0
    #: attività su un raggruppamento trasversale: escono le classi che tocca
    gruppi: int = 0
    #: attività senza docente — `ScheduleEntry.teacher` è obbligatoria
    senza_docente: int = 0
    #: piazzamenti oltre il venerdì: Aurora non ha il sabato
    fuori_settimana: int = 0
    #: attività la cui maschera, intersecata col periodo, resta vuota
    fuori_periodo: int = 0
    #: celle in cui lo stesso docente risulta su due materie per la stessa
    #: classe: l'unicità di Aurora non le distingue, e non si inventa quale vince
    celle_ambigue: list = field(default_factory=list)
    #: righe identiche fuse in una sola (due parti, stesso docente e materia)
    fuse: int = 0

    @property
    def vuota(self):
        return not any((self.parti, self.gruppi, self.senza_docente,
                        self.fuori_settimana, self.fuori_periodo,
                        self.celle_ambigue, self.fuse))


def settimane_iso(week_mask, year, period=None):
    """La nostra maschera, tradotta nell'indice che Aurora usa.

    Il bit *w* è la settimana che comincia a `first_week_monday + 7w`; il bit
    che esce è il **numero ISO** di quel lunedì. ⚠ La traduzione non è una
    rinumerazione: due settimane nostre non possono cadere sullo stesso bit
    ISO dentro un anno scolastico, ma un periodo più lungo di 52 settimane sì
    — è il prezzo dichiarato nell'emendamento del 2026-09-01 ad ADR-027, e
    vale qui come là.

    `period` restringe alle settimane in cui quell'orario è in vigore: è così
    che ADR-010 attraversa il confine (vedi il docstring del modulo).
    """
    n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
    fuori = 0
    for w in range(n_weeks):
        if not (week_mask >> w) & 1:
            continue
        lunedi = year.first_week_monday + dt.timedelta(weeks=w)
        if period is not None and not (lunedi <= period.end_date
                                       and lunedi + dt.timedelta(days=4)
                                       >= period.start_date):
            continue
        fuori |= 1 << lunedi.isocalendar()[1]
    return fuori


def _classi_di(act):
    """Le classi che questa attività tocca, con la classe al posto della parte.

    🔑 È qui che si consuma la perdita **vera e incompleta**: una parte diventa
    la sua classe e un raggruppamento diventa le classi delle sue parti, quindi
    Aurora vede una lezione dove ce n'è mezza. Il supplente serve comunque, ed
    è la stessa approssimazione con cui Aurora convive già dandosi classi dal
    nome composto."""
    classi = {c.name for c in act.classes.all()}
    for p in act.parts.all():
        classi.add(p.partition.school_class.name)
    for g in act.groups.all():
        for p in g.parts.all():
            classi.add(p.partition.school_class.name)
    return classi


def pubblica(schedule, selected=None):
    """`(righe, perdita)` — l'orario di `schedule` nella forma di Aurora.

    `selected` è l'estrazione, con la regola di sempre: **restringe ciò su cui
    si agisce**. Qui agire è pubblicare, quindi restringe l'uscita davvero.
    """
    period = schedule.period
    year = period.school_year if period is not None else SchoolYear.objects.first()
    perdita = Perdita()

    piazzamenti = (Placement.objects.filter(schedule=schedule)
                   .exclude(activity__immobility=Activity.Immobility.SUSPENDED)
                   .select_related("activity", "activity__subject")
                   .prefetch_related("activity__teachers", "activity__classes",
                                     "activity__parts__partition__school_class",
                                     "activity__groups__parts__partition__school_class")
                   .order_by("day", "start_slot", "activity_id"))

    # ⚠ La maschera **effettiva** (ADR-014): nella settimana in cui un
    # sostituto rimpiazza questa lezione l'originale non esce, o Aurora
    # vedrebbe due ore dove ce n'è una.
    maschere = effective_week_masks(
        (pl.activity_id, pl.activity.week_mask) for pl in piazzamenti)

    grezze = defaultdict(dict)   # chiave -> {materia: maschera}
    for pl in piazzamenti:
        act = pl.activity
        if selected is not None and act.pk not in selected:
            continue
        if pl.day >= len(GIORNI):
            perdita.fuori_settimana += 1
            continue
        docenti = [t for t in act.teachers.all()]
        if not docenti:
            perdita.senza_docente += 1
            continue
        iso = settimane_iso(maschere[act.pk], year, period)
        if not iso:
            perdita.fuori_periodo += 1
            continue
        if act.parts.all():
            perdita.parti += 1
        if act.groups.all():
            perdita.gruppi += 1
        for t in docenti:
            for c in _classi_di(act):
                for k in range(act.duration_slots):
                    # ⚠ `period_number` di Aurora conta da 1, le nostre fasce da 0.
                    chiave = (t.name, GIORNI[pl.day], pl.start_slot + k + 1, c)
                    per_materia = grezze[chiave]
                    if act.subject.code in per_materia:
                        perdita.fuse += 1
                    per_materia[act.subject.code] = (
                        per_materia.get(act.subject.code, 0) | iso)

    righe = []
    for chiave, per_materia in sorted(
            grezze.items(), key=lambda kv: (GIORNI.index(kv[0][1]), kv[0][2],
                                            kv[0][3], kv[0][0])):
        if len(per_materia) > 1:
            # ⚠ Due materie nella stessa cella per lo stesso docente e la
            # stessa classe: l'unicità di Aurora non porta la materia, quindi
            # le due righe **collidono**. Non si sceglie quale vince — si
            # nomina la cella e non esce nessuna delle due.
            perdita.celle_ambigue.append((chiave, sorted(per_materia)))
            continue
        (materia, iso), = per_materia.items()
        righe.append(Riga(chiave[0], chiave[1], chiave[2], chiave[3],
                          materia, iso))
    return righe, perdita
