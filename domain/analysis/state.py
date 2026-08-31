"""Lo snapshot in memoria di uno Schedule per una settimana data. Costruito
una volta dal DB, poi interrogato (e mutato dai piazzamenti di prova) dai
checker in millisecondi. Le chiavi di occupazione sono pk di Resource
(con la MTI, Teacher.pk == Resource.pk)."""

from collections import defaultdict
from dataclasses import dataclass
from itertools import product

from domain import weeks
from domain.models import (
    Activity, ClassPart, ClassPartition, Group, Holiday, InstituteSettings,
    Resource, ResourceTimeConstraint, ResourceUnavailability, SchoolClass,
    Service, Subject, SubjectConstraint, TeachingAssignment, TimeGrid,
    effective_week_masks,
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
    le mappe restano vuote e le chiavi di occupazione non cambiano di un bit.

    ⚠ **Le due mappe piatte non sono atomi**, e stanno qui per una ragione
    misurata. `parts_of_class` (tutte le classi, non solo quelle a due
    partizioni) e `parts_of_group` sono *come un'unità si espande in parti*:
    `activity_tokens` le chiedeva al database una volta per ogni classe e per
    ogni raggruppamento di **ogni** attività. La riga che produce la prima è
    **la stessa** che gli atomi leggono già e buttavano via — misurato sul
    banco: 668 delle 718 query di `check_schedule`, il 93 %."""

    part: dict    # ClassPart pk → frozenset di atomi
    klass: dict   # SchoolClass pk → frozenset di atomi
    names: dict   # atomo → nome leggibile, per le causali
    parts_of: dict  # atomo → tupla delle parti che lo compongono (ADR-020)
    parts_of_class: dict  # SchoolClass pk → frozenset delle sue ClassPart
    parts_of_group: dict  # Group pk → frozenset delle ClassPart membre

    @classmethod
    def build(cls):
        by_class = defaultdict(lambda: defaultdict(list))
        for pk, partition_id, class_id in ClassPart.objects.values_list(
                "pk", "partition_id", "partition__school_class_id"):
            by_class[class_id][partition_id].append(pk)
        class_names = dict(SchoolClass.objects.values_list("pk", "name"))
        part, klass, names, parts_of = {}, {}, {}, {}
        parts_of_class = {c: frozenset(pk for blocco in ps.values() for pk in blocco)
                          for c, ps in by_class.items()}
        parts_of_group = defaultdict(set)
        for group_id, part_id in Group.parts.through.objects.values_list(
                "group_id", "classpart_id"):
            parts_of_group[group_id].add(part_id)
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
                parts_of[key] = combo
                for part_pk in combo:
                    part.setdefault(part_pk, set()).add(key)
            klass[class_id] = frozenset(keys)
        return cls({p: frozenset(v) for p, v in part.items()}, klass, names,
                   parts_of, parts_of_class,
                   {g: frozenset(v) for g, v in parts_of_group.items()})


def _unit_ref(unit):
    """L'unità di piazzamento come chiave stabile: `"class:12"`, `"part:5"`,
    `"group:2"`. ⚠ Non è una chiave di occupazione — quelle appiattiscono
    (ADR-017) e due unità diverse possono condividerle. Qui serve il
    contrario: distinguere la classe intera dalla sua parte, perché una
    cattedra dichiarata sull'una e un'ora erogata all'altra sono **due cose
    diverse**, ed è esattamente lo scarto che L10 ha trovato."""
    if isinstance(unit, ClassPart):
        return f"part:{unit.pk}"
    if isinstance(unit, Group):
        return f"group:{unit.pk}"
    return f"class:{unit.pk}"


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
        keys |= atoms.parts_of_class.get(c.pk, frozenset())
        keys |= atoms.klass.get(c.pk, frozenset())
    for p in activity.parts.all():
        keys.add(p.pk)
        keys |= atoms.part.get(p.pk, frozenset())
    for g in activity.groups.all():
        for part_pk in atoms.parts_of_group.get(g.pk, frozenset()):
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


def subject_row_unit_keys(row, atoms):
    """L'espansione dell'unità di una riga `SubjectConstraint` in chiavi di
    occupazione.

    ⚠ **Questa è l'unica.** Ne esistevano tre copie — qui, in
    `checkers.subject_constraints._unit_keys` e per riflesso in
    `capacity._subject_rows`, che importava il privato del checker — e le due
    di là interrogavano il database *a ogni chiamata* invece che una volta al
    caricamento. Tre implementazioni della stessa frase sono tre occasioni di
    divergere; ora la frase sta scritta una volta e legge la mappa."""
    if row.school_class_id:
        return frozenset({row.school_class_id,
                          *atoms.parts_of_class.get(row.school_class_id, ())})
    if row.class_part_id:
        return frozenset({row.class_part_id})
    return atoms.parts_of_group.get(row.group_id, frozenset())


def subject_row_resources(row, atoms):
    """I pk di `Resource` che identificano l'unità della riga nel finding. Per
    i raggruppamenti — che non sono `Resource` — le parti membre."""
    if row.school_class_id:
        return (row.school_class_id,)
    if row.class_part_id:
        return (row.class_part_id,)
    return tuple(sorted(atoms.parts_of_group.get(row.group_id, ())))


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
        self.room_locked = set()      # id con il lucchetto sull'aula (L2)
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
        self.subject_row_resources = {}  # SubjectConstraint pk → risorse dell'unità
        self.part_class = {}          # ClassPart pk → SchoolClass pk (partizione)
        self.class_caps = {}          # SchoolClass pk → max_weekly_weight_per_student
        self.services_by_plan = {}    # StudyPlan pk → {subject_id: class_minutes}
        self.election_groups = {}     # StudyPlan pk → {etichetta: (subject_id, …)} (ADR-020)
        self.elective_services = {}   # StudyPlan pk → {subject_id} opzioni fuori gruppo (ADR-026)
        self.student_units = []       # [(chiave, StudyPlan pk, nome)] — coverage._student_units
        self.unit_plan_conflict = {}  # chiave → quanti piani diversi la dichiarano (ADR-020)
        self.break_boundaries = []    # boundary_slot degli intervalli della griglia
        self.subject_names = {}       # Subject pk → nome
        self.declared_load = {}       # (Teacher pk, Subject pk, unità) → minuti (L10)
        self.activity_units = {}      # Activity pk → tupla delle unità **dichiarate**
        self.unit_names = {}          # unità → nome leggibile, per le causali

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
        maschere = effective_week_masks(
            (a.id, a.week_mask) for a in acts)
        for a in acts:
            # ⚠ La maschera **effettiva**: nella settimana in cui un sostituto
            # rimpiazza questa attività, l'attività non si tiene. Senza,
            # l'occupazione conterebbe due ore dove la classe ne ha una.
            if not weeks.week_in_mask(maschere[a.id], week):
                continue
            state.activities[a.id] = a
            pl = placements.get(a.id)
            keys, materials = activity_tokens(
                a, assigned_room_id=pl.assigned_room_id if pl else None,
                atoms=atoms)
            state.tokens[a.id] = keys
            # ⚠ Le unità **dichiarate**, non i token: `activity_tokens`
            # appiattisce apposta — la classe occupa anche le sue parti, e il
            # raggruppamento occupa le parti membre senza lasciare traccia di
            # sé. È la lettura giusta per i conflitti e quella sbagliata per
            # la quadratura, che deve sapere *a chi* l'ora è erogata (L10).
            unita = (*a.classes.all(), *a.parts.all(), *a.groups.all())
            state.activity_units[a.id] = tuple(sorted(_unit_ref(u) for u in unita))
            for u in unita:
                state.unit_names[_unit_ref(u)] = u.name
            for k, q in materials.items():
                state.material_quantity[(a.id, k)] = q
            if pl is not None:
                state.place(a, pl.day, pl.start_slot)
                if pl.assigned_room_id is not None:
                    state.assigned_room[a.id] = pl.assigned_room_id
                if pl.room_locked:
                    state.room_locked.add(a.id)

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
        state.subject_rows = [(row, subject_row_unit_keys(row, atoms))
                              for row in subject_rows]
        state.subject_row_resources = {
            row.pk: subject_row_resources(row, atoms) for row, _ in state.subject_rows}

        state.part_class = dict(ClassPart.objects.values_list(
            "pk", "partition__school_class_id"))
        state.class_caps = dict(SchoolClass.objects.values_list(
            "pk", "max_weekly_weight_per_student"))

        state.subject_names = dict(Subject.objects.values_list("id", "name"))
        for ta in TeachingAssignment.objects.select_related(
                "school_class", "class_part", "group"):
            unita = ta.unit
            ref = _unit_ref(unita)
            state.unit_names[ref] = unita.name
            chiave = (ta.teacher_id, ta.subject_id, ref)
            state.declared_load[chiave] = state.declared_load.get(chiave, 0) + ta.weekly_minutes
        services = defaultdict(dict)
        elezioni = defaultdict(lambda: defaultdict(list))
        opzioni = defaultdict(set)
        for s in Service.objects.all():
            services[s.study_plan_id][s.subject_id] = s.class_minutes
            if s.election_group:
                elezioni[s.study_plan_id][s.election_group].append(s.subject_id)
            elif s.elective:
                # ADR-026: opzione **fuori** da ogni gruppo. Il gruppo ha la
                # precedenza perché dice di più — «esattamente una» invece di
                # «non a tutti» — e le due marcature sulla stessa riga non
                # sono un conflitto: la seconda è implicata dalla prima.
                # ⚠ L'`elif` è ridondante *per costruzione* e non per caso:
                # una riga in gruppo o è la seguita (e allora ha ore, quindi
                # il salto non scatterebbe) o è già esclusa dal conteggio.
                # Resta perché dice quale dei due assi vince, che è ciò che
                # un lettore verrà qui a cercare.
                opzioni[s.study_plan_id].add(s.subject_id)
        state.services_by_plan = dict(services)
        state.elective_services = dict(opzioni)
        state.election_groups = {plan: {label: tuple(sorted(subs))
                                        for label, subs in gruppi.items()}
                                 for plan, gruppi in elezioni.items()}

        # ⚠ Una query, non una per classe: la riga di prima chiedeva le parti
        # dentro il ciclo, e la copertura è già la fase più costosa.
        parti_per_classe = defaultdict(list)
        for parte in ClassPart.objects.select_related(
                "partition__school_class__study_plan", "study_plan"):
            parti_per_classe[parte.partition.school_class_id].append(parte)
        for klass in SchoolClass.objects.select_related("study_plan"):
            parts = parti_per_classe.get(klass.pk, [])
            if not parts:
                state.student_units.append((klass.pk, klass.study_plan_id, klass.name))
                continue
            by_pk = {p.pk: p for p in parts}
            # ADR-020: l'unità della copertura è l'**atomo**, cioè la
            # combinazione di parti in cui sta un alunno — una per partizione.
            # Con meno di due partizioni l'atomo *è* la parte, e AtomMap non ne
            # costruisce: la chiave resta la parte, come prima.
            combinazioni = [(key, atoms.parts_of[key])
                            for key in sorted(atoms.klass.get(klass.pk, ()))]
            if not combinazioni:
                combinazioni = [(p.pk, (p.pk,)) for p in parts]
            for key, combo in combinazioni:
                membri = [by_pk[pk] for pk in combo]
                propri = {p.study_plan_id for p in membri if p.study_plan_id}
                if len(propri) > 1:
                    # ⚠ Non si fonde e non si sceglie: si nomina l'errore.
                    state.unit_plan_conflict[key] = len(propri)
                plan_id = propri.pop() if len(propri) == 1 else klass.study_plan_id
                nome = (membri[0].name if len(membri) == 1
                        else "{} [{}]".format(klass.name,
                                              " · ".join(p.name for p in membri)))
                state.student_units.append((key, plan_id, nome))

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
