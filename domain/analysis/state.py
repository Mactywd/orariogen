"""Lo snapshot in memoria di uno Schedule per una settimana data. Costruito
una volta dal DB, poi interrogato (e mutato dai piazzamenti di prova) dai
checker in millisecondi. Le chiavi di occupazione sono pk di Resource
(con la MTI, Teacher.pk == Resource.pk)."""

from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from domain import weeks
from domain.models import (
    Activity, ClassPart, ClassPartition, Holiday, InstituteSettings, Resource,
    ResourceTimeConstraint, ResourceUnavailability, SchoolClass, Service,
    Subject, SubjectConstraint, TimeGrid,
)

_SEVERITY_ORDER = {"hard": 0, "optional": 1, "preference": 2}


def resource_sort_key(key):
    """Ordina le chiavi di occupazione gestendo miste int/str.
    Necessario da ADR-017: gli atomi sono chiavi stringa ('atom:...') affiancate
    ai pk interi (Resource, SchoolClass, ClassPart). Python 3 non confronta
    direttamente int e str, quindi servono tuple (tipo, valore) per sortare."""
    if isinstance(key, int):
        return (0, key)
    else:
        return (1, key)


def site_occupation(state, key, day, slots):
    """Le sedi che occupano una chiave, fascia per fascia:
    `[(fascia, {sede: frozenset(attività)}), ...]`, solo per le fasce con
    almeno una sede **nota** e in ordine di fascia crescente.

    ⚠ **Dentro una fascia le occupazioni non hanno ordine.** `occupancy` è un
    `defaultdict(list)` e conserva l'ordine in cui `build()` ha visto le
    attività, cioè l'ordine del queryset `Activity` — un fatto del database,
    non dell'orario. I due checker delle sedi leggevano quella lista come una
    **sequenza temporale**, e a capienza cumulativa (`simultaneous_capacity >
    1`, il `Numero di aule` di EDT) due attività di sedi diverse sulla stessa
    fascia facevano dipendere il verdetto dai pk: `[A, B, A]` dava due cambi,
    `[B, A, A]` uno solo. Raggruppare per sede toglie l'ordine di mezzo e
    lascia ai checker una decisione da prendere invece di un accidente da
    subire — vedi i loro docstring, e
    `tests/test_analysis_ordine_inserimento.py`."""
    out = []
    for s in slots:
        by_site = defaultdict(set)
        for aid in state.occupancy[(key, day, s)]:
            site = state.activities[aid].site_id
            if site is not None:
                by_site[site].add(aid)
        if by_site:
            out.append((s, {site: frozenset(aids)
                            for site, aids in by_site.items()}))
    return out


@dataclass(frozen=True)
class AtomMap:
    """ADR-017. Due partizioni della stessa classe sono due modi di dividere
    gli stessi studenti: una parte dell'una e una parte dell'altra hanno
    studenti in comune. Gli atomi sono le celle del prodotto delle partizioni,
    così le parti della stessa partizione restano disgiunte (lo sdoppiamento)
    e quelle di partizioni diverse si intersecano.

    Costruito solo per le classi con almeno due partizioni non vuote: altrove
    le mappe restano vuote e le chiavi di occupazione non cambiano di un bit."""

    part: dict    # ClassPart pk → frozenset di atomi
    klass: dict   # SchoolClass pk → frozenset di atomi
    names: dict   # atomo → nome leggibile, per le causali

    @classmethod
    def build(cls):
        by_class = defaultdict(lambda: defaultdict(list))
        for pk, partition_id, class_id in ClassPart.objects.values_list(
                "pk", "partition_id", "partition__school_class_id"):
            by_class[class_id][partition_id].append(pk)
        class_names = dict(SchoolClass.objects.values_list("pk", "name"))
        part, klass, names = {}, {}, {}
        for class_id, partitions in by_class.items():
            blocks = [sorted(parts) for _, parts in sorted(partitions.items()) if parts]
            if len(blocks) < 2:
                continue
            label = f"{class_names.get(class_id, class_id)} (studenti in comune fra partizioni)"
            keys = []
            for combo in product(*blocks):
                key = "atom:{}:{}".format(class_id, "-".join(str(p) for p in combo))
                keys.append(key)
                names[key] = label
                for part_pk in combo:
                    part.setdefault(part_pk, set()).add(key)
            klass[class_id] = frozenset(keys)
        return cls({p: frozenset(v) for p, v in part.items()}, klass, names)


def activity_tokens(activity, assigned_room_id=None, atoms=None):
    """Chiavi di occupazione e quantità dei materiali di un'attività.
    Regola dei conflitti sulle unità: la classe intera occupa sé stessa, tutte
    le sue parti e tutti i suoi atomi; la parte occupa sé stessa e i propri
    atomi; il raggruppamento occupa le parti membre e i loro atomi. Parti di
    partizioni diverse della stessa classe condividono un atomo, quindi
    confliggono (ADR-017); parti della stessa partizione no."""
    if atoms is None:
        atoms = AtomMap.build()
    keys, materials = set(), {}
    for t in activity.teachers.all():
        keys.add(t.pk)
    for c in activity.classes.all():
        keys.add(c.pk)
        keys.update(ClassPart.objects.filter(
            partition__school_class=c).values_list("pk", flat=True))
        keys |= atoms.klass.get(c.pk, frozenset())
    for p in activity.parts.all():
        keys.add(p.pk)
        keys |= atoms.part.get(p.pk, frozenset())
    for g in activity.groups.all():
        for part_pk in g.parts.values_list("pk", flat=True):
            keys.add(part_pk)
            keys |= atoms.part.get(part_pk, frozenset())
    if assigned_room_id is not None:
        keys.add(assigned_room_id)
    else:
        # ⚠ Solo a **candidata unica**: le aule dichiarate sono l'insieme fra
        # cui la seconda fase sceglie (spec §1). Con due o piu' candidate
        # occuparle tutte inventerebbe conflitti che l'assegnazione
        # risolverebbe da sola; con una sola la scelta e' determinata, quindi
        # occupare non e' una stima, e' esatto.
        rooms = list(activity.rooms.all())
        if len(rooms) == 1:
            keys.add(rooms[0].pk)
    for s in activity.staff.all():
        keys.add(s.pk)
    for req in activity.material_requirements.all():
        keys.add(req.material_id)
        materials[req.material_id] = req.quantity
    return frozenset(keys), materials


def _subject_row_unit_keys(row):
    """L'espansione dell'unità di una riga SubjectConstraint in chiavi di
    occupazione (stessa logica di checkers.subject_constraints._unit_keys,
    ricalcolata una sola volta qui in build() invece che ad ogni check())."""
    if row.school_class_id:
        parts = ClassPart.objects.filter(
            partition__school_class_id=row.school_class_id).values_list("pk", flat=True)
        return frozenset({row.school_class_id, *parts})
    if row.class_part_id:
        return frozenset({row.class_part_id})
    return frozenset(row.group.parts.values_list("pk", flat=True))


@dataclass(frozen=True)
class Placed:
    activity_id: int
    day: int
    start_slot: int
    slots: tuple[int, ...]


class ScheduleState:
    def __init__(self, schedule, grid, week, settings):
        self.schedule = schedule
        self.grid = grid
        self.week = week
        self.settings = settings
        self.activities = {}          # id → Activity (attive nella settimana)
        self.placed = {}              # id → Placed
        self.assigned_room = {}       # id → room_id assegnata (solo se piazzata)
        self.occupancy = defaultdict(list)  # (chiave, giorno, fascia) → [activity_id]
        self.tokens = {}              # id → frozenset di chiavi
        self.material_quantity = {}   # (activity_id, chiave) → quantità
        self.capacity = {}            # chiave → capacità simultanea
        self.kinds = {}               # chiave → Resource.Kind
        self.resource_names = {}      # chiave → nome
        self.unavailability = {}      # (chiave, giorno, fascia) → livello più severo
        self.holidays = set()         # giorni festivi di questa settimana
        self.n_weeks = 1
        # Cache di righe/dati anagrafici che i checker consultavano prima con
        # una query ORM ad ogni check(): caricate una volta qui, in millisecondi
        # (contratto dichiarato in cima a questo modulo).
        self.time_rows = []           # tutte le righe ResourceTimeConstraint
        self.subject_rows = []        # [(riga SubjectConstraint, unit_keys precalcolate)]
        self.part_class = {}          # ClassPart pk → SchoolClass pk (partizione)
        self.class_caps = {}          # SchoolClass pk → max_weekly_weight_per_student
        self.services_by_plan = {}    # StudyPlan pk → {subject_id: class_minutes}
        self.student_units = []       # [(chiave, StudyPlan pk, nome)] — coverage._student_units
        self.break_boundaries = []    # boundary_slot degli intervalli della griglia
        self.subject_names = {}       # Subject pk → nome

    @classmethod
    def build(cls, schedule, week=0):
        grid = TimeGrid.objects.first()
        settings = InstituteSettings.objects.filter(pk=1).first() or InstituteSettings()
        state = cls(schedule, grid, week, settings)

        for r in Resource.objects.values("id", "name", "kind", "simultaneous_capacity"):
            state.resource_names[r["id"]] = r["name"]
            state.kinds[r["id"]] = r["kind"]
            state.capacity[r["id"]] = r["simultaneous_capacity"]

        atoms = AtomMap.build()
        state.resource_names.update(atoms.names)

        placements = {p.activity_id: p for p in schedule.placements.all()}
        acts = (Activity.objects
                .exclude(immobility=Activity.Immobility.SUSPENDED)
                .select_related("subject", "site")
                .prefetch_related("teachers", "classes", "parts", "groups",
                                  "rooms", "staff", "material_requirements"))
        for a in acts:
            if not weeks.week_in_mask(a.week_mask, week):
                continue
            state.activities[a.id] = a
            pl = placements.get(a.id)
            keys, materials = activity_tokens(
                a, assigned_room_id=pl.assigned_room_id if pl else None,
                atoms=atoms)
            state.tokens[a.id] = keys
            for k, q in materials.items():
                state.material_quantity[(a.id, k)] = q
            if pl is not None:
                state.place(a, pl.day, pl.start_slot)
                if pl.assigned_room_id is not None:
                    state.assigned_room[a.id] = pl.assigned_room_id

        year = schedule.period.school_year
        state.n_weeks = ((year.end_date - year.first_week_monday).days // 7) + 1
        for u in ResourceUnavailability.objects.all():
            day = u.day
            if u.date is not None:
                delta = (u.date - year.first_week_monday).days
                if delta // 7 != week:
                    continue
                day = delta % 7
            key = (u.resource_id, day, u.slot)
            current = state.unavailability.get(key)
            if current is None or _SEVERITY_ORDER[u.level] < _SEVERITY_ORDER[current]:
                state.unavailability[key] = u.level
        for h in Holiday.objects.filter(school_year=year):
            delta = (h.date - year.first_week_monday).days
            if delta // 7 == week and 0 <= delta % 7 < grid.days_per_cycle:
                state.holidays.add(delta % 7)

        state.time_rows = list(ResourceTimeConstraint.objects.all())

        subject_rows = (SubjectConstraint.objects
                        .select_related("subject_a", "subject_b", "school_class",
                                        "class_part", "group"))
        state.subject_rows = [(row, _subject_row_unit_keys(row)) for row in subject_rows]

        state.part_class = dict(ClassPart.objects.values_list(
            "pk", "partition__school_class_id"))
        state.class_caps = dict(SchoolClass.objects.values_list(
            "pk", "max_weekly_weight_per_student"))

        state.subject_names = dict(Subject.objects.values_list("id", "name"))
        services = defaultdict(dict)
        for s in Service.objects.all():
            services[s.study_plan_id][s.subject_id] = s.class_minutes
        state.services_by_plan = dict(services)

        for klass in SchoolClass.objects.select_related("study_plan"):
            parts = list(ClassPart.objects.filter(partition__school_class=klass)
                         .select_related("partition__school_class__study_plan", "study_plan"))
            if parts:
                for part in parts:
                    state.student_units.append(
                        (part.pk, part.effective_study_plan.pk, part.name))
            else:
                state.student_units.append((klass.pk, klass.study_plan_id, klass.name))

        state.break_boundaries = [b.boundary_slot for b in grid.breaks.all()]
        return state

    def place(self, activity, day, start_slot):
        slots = tuple(range(start_slot, start_slot + activity.duration_slots))
        self.placed[activity.id] = Placed(activity.id, day, start_slot, slots)
        for key in self.tokens[activity.id]:
            for s in slots:
                self.occupancy[(key, day, s)].append(activity.id)

    def unplace(self, activity_id):
        pl = self.placed.pop(activity_id)
        for key in self.tokens[activity_id]:
            for s in pl.slots:
                cell = self.occupancy[(key, pl.day, s)]
                cell.remove(activity_id)
                if not cell:
                    del self.occupancy[(key, pl.day, s)]

    def resource_days(self, key):
        """giorno → fasce occupate ordinate, per una chiave di occupazione."""
        out = defaultdict(set)
        for (k, day, slot), acts in self.occupancy.items():
            if k == key and acts:
                out[day].add(slot)
        return {d: sorted(s) for d, s in sorted(out.items())}
