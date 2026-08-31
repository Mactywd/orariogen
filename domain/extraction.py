"""`Estrai`: la selezione di lavoro come **operazione**, non come filtro di
vista.

`scope-v1.md` la chiama *«la voce con più dipendenze in entrata di tutto
l'inventario»*, ed è la risposta a *«rigenera solo il biennio»*, *«ripiazza solo
quelle tre»*. La tabella esisteva dal giorno dello schema e il solver la
onorava già (`SolverContext.build`, dove ciò che è fuori dall'estrazione è
**congelato** e non cancellato); ciò che mancava è tutto il resto —
**niente la popolava**, e le due fasi diagnostiche la ignoravano.

🔑 **La regola che tiene insieme il pezzo: un'estrazione restringe ciò su cui
si *agisce*, mai ciò che si *conta*.** Fuori dall'estrazione le attività
restano dove sono e continuano a occupare le loro risorse: è la ragione per cui
`SolverContext` le congela invece di escluderle, ed è la stessa ragione per cui
qui `ScheduleState` si costruisce sempre intero. Filtrare lo stato sarebbe
silenziosamente sbagliato — l'occupazione risulterebbe più bassa del vero e il
motore piazzerebbe sopra a lezioni che esistono.

⚠ **I token dicono chi confligge, non chi appartiene, e i due verbi non
coincidono.** `activity_tokens` è deliberatamente asimmetrico: un'attività a
classe intera occupa la classe *e tutte le sue parti* (quindi confligge con
loro), ma un'attività di parte **non** occupa la classe. Estrarre «le attività
della 2A» leggendo i token restituirebbe le ore a classe intera e perderebbe
gli sdoppiamenti — cioè proprio quelle che un vicepreside vuole vedere. Da qui
`_appartenenze`, che percorre anche il verso che ai token non serve: parte →
classe, raggruppamento → classi dei membri, e **tutte** le aule dichiarate (i
token ne prendono una sola, e solo a candidata unica).

⚠ **I rilevatori nominano chi i finding nominano, e non tutti nominano
qualcuno.** Gli otto vincoli orari sulla risorsa (D.T.B., giorni liberi,
massimi…) producono finding che nominano la **risorsa** e nessuna attività, ed
è corretto: un buco tollerato è una proprietà della *giornata* di un docente,
non di una delle sue cinque lezioni — quale sarebbe «quella che viola»? Nessuna,
è la forma a violare. Il rilevatore restituisce quindi ciò che c'è, e
**dichiara** a parte i finding rimasti senza nome, con la stessa regola di
`blame.famiglie_silenziose()`: un vincolo che tace e un vincolo innocuo non
devono leggersi uguali.
"""

from collections import defaultdict
from dataclasses import dataclass

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (Activity, ClassPart, Extraction, Group, Placement)

#: I due codici che descrivono un orario **incompleto**, non illegale: la stessa
#: esclusione che `manage.py solve` fa già sulle «violazioni residue». Le aule
#: le assegna la seconda fase, e un'attività non piazzata non viola niente.
INCOMPLETO = ("activity_unplaced", "room_unassigned")

#: I rilevatori di problemi di EDT che il nostro modello sa davvero rispondere.
#: `None` = «tutti i vincoli», cioè ogni finding HARD tranne i due qui sopra.
#: ⚠ Le voci del menu di EDT sono dodici; qui ce ne sono sei, e le assenti sono
#: assenti per una ragione dichiarata, mai per dimenticanza: `attività non
#: costanti durante l'anno`, `sezionate asincrone` e `spostate` riguardano la
#: fascia variabile e il sezionamento, fuori scope (ADR-010); `raggruppamenti ad
#: alunni variabili` è la formazione classi, che non abbiamo; `complesse` e `di
#: compresenza` sono filtri di forma, non problemi.
RILEVATORI = {
    "non_rispettano_i_vincoli": None,
    "problemi_di_aule": ("room_unassigned",),
    "problemi_di_sede": ("site_transition",),
    "a_cavallo_dell_intervallo": ("break_straddled",),
    "fuori_griglia": ("slot_out_of_grid", "holiday"),
    "non_conformi_ai_piani_di_studi": ("coverage_mismatch", "election_mismatch",
                                       "ambiguous_study_plan"),
}

#: Gli stati di EDT che il nostro modello ha. ⚠ `Scartate` e `In attesa` sono
#: sfumature di «non piazzata» che il modello non distingue, e `Variabili` è la
#: fascia variabile, fuori scope: non si inventano.
STATI = ("piazzate", "non_piazzate", "bloccate", "fisse", "mobili", "sospese")

_IMMOBILITA = {
    "bloccate": (Activity.Immobility.LOCKED_IN_PLACE,),
    "fisse": (Activity.Immobility.FIXED,),
    "sospese": (Activity.Immobility.SUSPENDED,),
    "mobili": (Activity.Immobility.NONE, Activity.Immobility.NOT_SUSPENDABLE),
}

MODI = ("sostituisci", "aggiungi", "togli", "limita")


@dataclass(frozen=True)
class Rilevamento:
    """L'esito di un rilevatore: chi ha trovato, e cosa non ha saputo nominare."""

    nome: str
    activity_ids: frozenset
    senza_attivita: tuple   # [(codice, frase)] dei finding che non nominano nessuno

    @property
    def muto(self):
        """Vero quando ci sono violazioni ma nessuna è attribuibile a
        un'attività: l'estrazione è vuota e **non** perché l'orario è sano."""
        return not self.activity_ids and bool(self.senza_attivita)


def _appartenenze():
    """`Activity pk → chiavi di risorsa a cui appartiene`.

    Non è `state.tokens`: vedi il ⚠ in testa al modulo. Qui si risale anche
    parte → classe e raggruppamento → classi, e si prendono **tutte** le aule
    dichiarate invece della sola candidata unica."""
    # ⚠ Le stesse due mappe stanno in `AtomMap` (ADR-031), e qui **non** si
    # riusano: `AtomMap.build` calcola anche il prodotto delle partizioni, che
    # a `Estrai` non serve. È una duplicazione dichiarata, non una svista — e
    # il giorno in cui serve anche l'atomo, la riga giusta è togliere queste.
    parts_of_class = defaultdict(set)
    class_of_part = {}
    for part_pk, class_pk in ClassPart.objects.values_list(
            "pk", "partition__school_class_id"):
        parts_of_class[class_pk].add(part_pk)
        class_of_part[part_pk] = class_pk
    parts_of_group = defaultdict(set)
    for group_pk, part_pk in Group.parts.through.objects.values_list(
            "group_id", "classpart_id"):
        parts_of_group[group_pk].add(part_pk)

    out = {}
    acts = Activity.objects.prefetch_related(
        "teachers", "classes", "parts", "groups", "rooms", "staff",
        "material_requirements")
    for a in acts:
        keys = {t.pk for t in a.teachers.all()}
        keys |= {r.pk for r in a.rooms.all()}
        keys |= {s.pk for s in a.staff.all()}
        keys |= {req.material_id for req in a.material_requirements.all()}
        for c in a.classes.all():
            keys.add(c.pk)
            keys |= parts_of_class[c.pk]
        for p in a.parts.all():
            keys.add(p.pk)
            keys.add(class_of_part[p.pk])
        for g in a.groups.all():
            for part_pk in parts_of_group[g.pk]:
                keys.add(part_pk)
                keys.add(class_of_part[part_pk])
        out[a.pk] = frozenset(keys)
    return out


def per_risorsa(resource_ids):
    """Le attività che coinvolgono **almeno una** delle risorse date."""
    voluti = set(resource_ids)
    return frozenset(aid for aid, keys in _appartenenze().items()
                     if keys & voluti)


def per_materia(subject_ids):
    return frozenset(Activity.objects.filter(subject_id__in=list(subject_ids))
                     .values_list("pk", flat=True))


def per_stato(schedule, stato):
    if stato not in STATI:
        raise ValueError(f"stato sconosciuto: {stato}")
    if stato in ("piazzate", "non_piazzate"):
        piazzate = set(Placement.objects.filter(schedule=schedule)
                       .values_list("activity_id", flat=True))
        if stato == "piazzate":
            return frozenset(piazzate)
        return frozenset(Activity.objects.exclude(pk__in=piazzate)
                         .values_list("pk", flat=True))
    return frozenset(
        Activity.objects.filter(immobility__in=_IMMOBILITA[stato])
        .values_list("pk", flat=True))


def nella_fascia(schedule, giorno, dalla, alla, interamente=True):
    """Le attività piazzate che cadono nella finestra `[dalla, alla]` del
    giorno — `interamente` come in EDT, che distingue *«interamente nella
    fascia»* da *«parzialmente nella fascia»*.

    ⚠ La finestra è inclusiva su entrambi gli estremi, e un'attività lunga si
    misura su **tutte** le fasce che occupa, non sulla sola fascia d'inizio."""
    out = set()
    for pl in (Placement.objects.filter(schedule=schedule, day=giorno)
               .select_related("activity")):
        occupate = range(pl.start_slot,
                         pl.start_slot + pl.activity.duration_slots)
        dentro = [s for s in occupate if dalla <= s <= alla]
        if not dentro:
            continue
        if interamente and len(dentro) != len(occupate):
            continue
        out.add(pl.activity_id)
    return frozenset(out)


def rileva(schedule, nome, findings=None):
    """Un rilevatore di problemi. `findings` si passa dall'esterno quando se ne
    lancia più d'uno: `check_schedule` è la parte cara, e va pagata una volta."""
    if nome not in RILEVATORI:
        raise ValueError(f"rilevatore sconosciuto: {nome}")
    codici = RILEVATORI[nome]
    if findings is None:
        findings = check_schedule(schedule)

    ids, muti = set(), []
    for f in findings:
        if f.severity != Severity.HARD:
            continue
        if codici is None:
            if f.code in INCOMPLETO:
                continue
        elif f.code not in codici:
            continue
        if f.activities:
            ids.update(f.activities)
        else:
            muti.append((f.code, f.message))
    return Rilevamento(nome, frozenset(ids), tuple(muti))


def componi(base, nuovi, modo):
    """Le quattro operazioni insiemistiche del menu `Estrai`.

    `limita` è la casella *«Limita la ricerca alle attività già estratte»*, che
    è ciò che rende l'estrazione **componibile**: si raffina progressivamente
    un insieme, come una query incrementale con stato."""
    base, nuovi = frozenset(base), frozenset(nuovi)
    if modo == "sostituisci":
        return nuovi
    if modo == "aggiungi":
        return base | nuovi
    if modo == "togli":
        return base - nuovi
    if modo == "limita":
        return base & nuovi
    raise ValueError(f"modo sconosciuto: {modo}")


def salva(nome, activity_ids):
    """Memorizza l'estrazione sotto un nome, sovrascrivendo l'omonima.

    È `Memorizza le attività estratte` di EDT: la selezione è nominabile e
    richiamabile, cioè una struttura dati di prima classe e non uno stato di
    interfaccia."""
    estrazione, _ = Extraction.objects.get_or_create(name=nome)
    estrazione.activities.set(sorted(activity_ids))
    return estrazione


def carica(nome):
    estrazione = Extraction.objects.get(name=nome)
    return frozenset(estrazione.activities.values_list("id", flat=True))
