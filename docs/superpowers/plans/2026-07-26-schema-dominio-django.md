# Schema Django del modello di dominio v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tradurre in schema Django il design approvato di
[docs/modello-dominio.md](../../modello-dominio.md), con il dataset Fermi
(`data/liceo-fermi/`) interamente rappresentato come primo test.

**Architecture:** Progetto Django minimale (`config/` + app `domain/`), modelli
divisi per area (risorse, curriculum, classi, docenti, tempo, attività, vincoli),
risorsa generica via multi-table inheritance, SQLite per i test. Nessuna view,
nessuna URL: solo modelli + test.

**Tech Stack:** Python 3.11+, Django 5.1+ (serve `CheckConstraint(condition=…)`),
pytest + pytest-django, SQLite.

**Scope:** SOLO il sottosistema 1 (schema + rappresentazione Fermi). I predicati /
analisi di capienza e il modello CP-SAT sono piani successivi, su questo schema.

## Global Constraints

- Identificatori in **inglese**; sui gruppi SOLO `partition` / `part` / `group`
  (mai tradurre dall'italiano di EDT: «gruppo» IT = `part`, [gruppi.md](../../edt/gruppi.md)).
- Durate sempre in **minuti** nei campi DB (mai float di ore).
- Cascata di default = campo **nullable** + property `effective_*` (`NULL` = eredita).
  Solo dove il design la dichiara: `Subject.max_reduced_students`,
  `Teacher.weekly_minutes`, `ClassPart.study_plan`.
- I calcolati **non si memorizzano** (ADR-007): niente colonne per totali/derivati.
- **Nessun vincolo di integrità** che leghi piazzamenti a vincoli o monte ore:
  l'orario invalido è uno stato ammesso (principio 3 del design).
- Ogni task termina con `pytest` verde e un commit. Messaggi di commit in
  italiano, prefisso `feat(domain):`.

---

### Task 1: Scaffolding del progetto Django

**Files:**
- Create: `manage.py`, `config/__init__.py`, `config/settings.py`
- Create: `domain/__init__.py`, `domain/apps.py`, `domain/models/__init__.py`, `domain/migrations/__init__.py`
- Create: `pytest.ini`, `tests/__init__.py`, `tests/test_scaffolding.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: —
- Produces: progetto importabile (`config.settings`, app `domain`), suite pytest
  funzionante con accesso al DB (`@pytest.mark.django_db`).

- [ ] **Step 1: Aggiorna requirements.txt**

Contenuto finale (ortools c'era già, per il prototipo parcheggiato):

```
ortools
Django>=5.1,<6
pytest
pytest-django
```

Poi: `pip install -r requirements.txt`

- [ ] **Step 2: Scrivi i file di progetto**

`config/settings.py`:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-only-not-a-secret"
DEBUG = True
INSTALLED_APPS = ["domain"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

`config/__init__.py`: vuoto.

`manage.py`:

```python
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
```

`domain/__init__.py`: vuoto. `domain/migrations/__init__.py`: vuoto.
`domain/models/__init__.py`: vuoto (per ora).

`domain/apps.py`:

```python
from django.apps import AppConfig


class DomainConfig(AppConfig):
    name = "domain"
```

`pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
```

`tests/__init__.py`: vuoto.

- [ ] **Step 3: Scrivi il test di fumo**

`tests/test_scaffolding.py`:

```python
import pytest
from django.db import connection


@pytest.mark.django_db
def test_database_available():
    assert connection.vendor == "sqlite"
```

- [ ] **Step 4: Esegui e verifica che passi**

Run: `pytest tests/test_scaffolding.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt manage.py config domain pytest.ini tests
git commit -m "feat(domain): scaffolding Django del modulo dominio"
```

---

### Task 2: Istituto, sedi e la risorsa generica

**Files:**
- Create: `domain/models/institute.py`, `domain/models/resources.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_resources.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: `Site(name)`, `InstituteSettings.load()` (singleton con
  `default_teacher_weekly_minutes`, `default_max_reduced_students`,
  `site_transition_slots`, `max_weight_morning/afternoon/day/week` tutti
  nullable), `Resource` (base MTI: `kind`, `name`, `site`,
  `simultaneous_capacity` default 1, `Resource.Kind` TextChoices),
  `Room(Resource)` con `capacity` nullable, `Material(Resource)`,
  `StaffMember(Resource)` con `role`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_resources.py`:

```python
import pytest

from domain.models import InstituteSettings, Material, Resource, Room, Site, StaffMember


@pytest.mark.django_db
def test_institute_settings_is_singleton():
    a = InstituteSettings.load()
    b = InstituteSettings.load()
    assert a.pk == b.pk == 1


@pytest.mark.django_db
def test_room_is_a_resource_with_default_capacity_one():
    room = Room.objects.create(name="LAB-FIS", capacity=30)
    base = Resource.objects.get(pk=room.pk)
    assert base.kind == Resource.Kind.ROOM
    assert base.simultaneous_capacity == 1


@pytest.mark.django_db
def test_gym_can_host_two_classes():
    gym = Room.objects.create(name="PALESTRA", capacity=60, simultaneous_capacity=2)
    assert Resource.objects.get(pk=gym.pk).simultaneous_capacity == 2


@pytest.mark.django_db
def test_material_and_staff_are_resources():
    cart = Material.objects.create(name="PC portatile", simultaneous_capacity=12)
    aide = StaffMember.objects.create(name="Guglielmi Marco", role="educatore")
    assert Resource.objects.get(pk=cart.pk).kind == Resource.Kind.MATERIAL
    assert Resource.objects.get(pk=aide.pk).kind == Resource.Kind.STAFF


@pytest.mark.django_db
def test_resource_can_have_a_site():
    site = Site.objects.create(name="Succursale")
    room = Room.objects.create(name="S101", site=site)
    assert room.site.name == "Succursale"
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL con `ImportError` (i modelli non esistono).

- [ ] **Step 3: Implementa i modelli**

`domain/models/institute.py`:

```python
from django.db import models


class Site(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class InstituteSettings(models.Model):
    """Singleton. I default d'istituto della cascata dichiarata (ADR-003) e i
    parametri unici (transizione di sede, tetti di peso didattico)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    default_teacher_weekly_minutes = models.PositiveIntegerField(null=True, blank=True)
    default_max_reduced_students = models.PositiveSmallIntegerField(null=True, blank=True)
    site_transition_slots = models.PositiveSmallIntegerField(default=1)
    max_weight_morning = models.PositiveSmallIntegerField(null=True, blank=True)
    max_weight_afternoon = models.PositiveSmallIntegerField(null=True, blank=True)
    max_weight_day = models.PositiveSmallIntegerField(null=True, blank=True)
    max_weight_week = models.PositiveSmallIntegerField(null=True, blank=True)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

`domain/models/resources.py`:

```python
from django.db import models

from .institute import Site


class Resource(models.Model):
    """Base comune delle risorse di piazzamento (multi-table inheritance).
    Disponibilità, vincoli orari e capacità puntano qui, mai al tipo concreto."""

    class Kind(models.TextChoices):
        TEACHER = "teacher"
        CLASS = "class"
        CLASS_PART = "class_part"
        ROOM = "room"
        STAFF = "staff"
        MATERIAL = "material"

    KIND = None  # ogni sottoclasse lo fissa

    kind = models.CharField(max_length=16, choices=Kind.choices, editable=False)
    name = models.CharField(max_length=100)
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)
    simultaneous_capacity = models.PositiveSmallIntegerField(default=1)

    def save(self, *args, **kwargs):
        if self.KIND is not None:
            self.kind = self.KIND
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Room(Resource):
    KIND = Resource.Kind.ROOM
    capacity = models.PositiveSmallIntegerField(null=True, blank=True)  # descrittiva


class Material(Resource):
    KIND = Resource.Kind.MATERIAL


class StaffMember(Resource):
    KIND = Resource.Kind.STAFF
    role = models.CharField(max_length=50, blank=True)
```

`domain/models/__init__.py`:

```python
from .institute import InstituteSettings, Site
from .resources import Material, Resource, Room, StaffMember

__all__ = [
    "InstituteSettings", "Site",
    "Material", "Resource", "Room", "StaffMember",
]
```

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_resources.py -v`
Expected: migrazione `0001_initial` creata, 5 passed.

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_resources.py
git commit -m "feat(domain): sedi, impostazioni d'istituto e risorsa generica"
```

---

### Task 3: La catena del curriculum

**Files:**
- Create: `domain/models/curriculum.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_curriculum.py`

**Interfaces:**
- Consumes: `InstituteSettings.load()` (Task 2).
- Produces: `Discipline(code, name)` con M2M `competition_classes`,
  `CompetitionClass(code, name)`, `Subject(code, name, discipline,
  max_reduced_students, didactic_weight)` con property
  `effective_max_reduced_students`, `StudyPlan(code, name, year)`,
  `Service(study_plan, subject, class_minutes, reduced_minutes, split_minutes)`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_curriculum.py`:

```python
import pytest

from domain.models import (
    CompetitionClass, Discipline, InstituteSettings, Service, StudyPlan, Subject,
)


@pytest.fixture
def lettere(db):
    return Discipline.objects.create(code="LET", name="Lettere")


@pytest.mark.django_db
def test_discipline_maps_to_competition_classes(lettere):
    a011 = CompetitionClass.objects.create(code="A011")
    a013 = CompetitionClass.objects.create(code="A013")
    lettere.competition_classes.add(a011, a013)
    assert lettere.competition_classes.count() == 2


@pytest.mark.django_db
def test_subject_max_reduced_students_inherits_from_institute(lettere):
    settings = InstituteSettings.load()
    settings.default_max_reduced_students = 15
    settings.save()
    ita = Subject.objects.create(code="ITA", name="Italiano", discipline=lettere)
    assert ita.max_reduced_students is None          # NULL = eredita
    assert ita.effective_max_reduced_students == 15  # risolto a runtime


@pytest.mark.django_db
def test_subject_didactic_weight_defaults_to_one(lettere):
    ita = Subject.objects.create(code="ITA", name="Italiano", discipline=lettere)
    assert ita.didactic_weight == 1


@pytest.mark.django_db
def test_service_carries_three_durations(lettere):
    plan = StudyPlan.objects.create(code="SCI1", name="Liceo Scientifico - 1 anno", year=1)
    ing = Subject.objects.create(code="ING", name="Inglese", discipline=lettere)
    svc = Service.objects.create(
        study_plan=plan, subject=ing,
        class_minutes=120, reduced_minutes=None, split_minutes=60,
    )
    assert (svc.class_minutes, svc.reduced_minutes, svc.split_minutes) == (120, None, 60)
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_curriculum.py -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementa i modelli**

`domain/models/curriculum.py`:

```python
from django.db import models

from .institute import InstituteSettings


class CompetitionClass(models.Model):
    """Classe di concorso ministeriale (A011, A027…). Nostra estensione, non
    campo EDT (ADR-002)."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100, blank=True)


class Discipline(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    competition_classes = models.ManyToManyField(CompetitionClass, blank=True)


class Subject(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    discipline = models.ForeignKey(Discipline, on_delete=models.PROTECT)
    max_reduced_students = models.PositiveSmallIntegerField(null=True, blank=True)
    didactic_weight = models.PositiveSmallIntegerField(default=1)

    @property
    def effective_max_reduced_students(self):
        if self.max_reduced_students is not None:
            return self.max_reduced_students
        return InstituteSettings.load().default_max_reduced_students


class StudyPlan(models.Model):
    """Indirizzo × anno (la chiave Formation+Specialite dello XSD)."""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField()


class Service(models.Model):
    """Riga del quadro orario del piano. Monte ore tripartito, in minuti."""

    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name="services")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    class_minutes = models.PositiveIntegerField()
    reduced_minutes = models.PositiveIntegerField(null=True, blank=True)
    split_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["study_plan", "subject"], name="uniq_service_plan_subject"),
        ]
```

Aggiungi a `domain/models/__init__.py` gli import e le voci `__all__`:
`CompetitionClass, Discipline, Service, StudyPlan, Subject`.

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_curriculum.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_curriculum.py
git commit -m "feat(domain): discipline, classi di concorso, materie, piani e servizi"
```

---

### Task 4: Classi, partizioni, parti e raggruppamenti

**Files:**
- Create: `domain/models/classes.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_classes.py`

**Interfaces:**
- Consumes: `Resource`, `Room` (Task 2); `StudyPlan` (Task 3).
- Produces: `SchoolClass(Resource)` con `study_plan`, `year`, `preferred_room`,
  `max_weekly_weight_per_student`; `ClassPartition(school_class, name)`;
  `ClassPart(Resource)` con `partition`, `study_plan` nullable e property
  `effective_study_plan`; `Group(name)` con M2M `parts`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_classes.py`:

```python
import pytest

from domain.models import (
    ClassPart, ClassPartition, Group, Resource, Room, SchoolClass, StudyPlan,
)


@pytest.fixture
def plan(db):
    return StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)


@pytest.mark.django_db
def test_class_is_a_resource_with_plan_and_preferred_room(plan):
    room = Room.objects.create(name="A101", capacity=30)
    c = SchoolClass.objects.create(name="1A", study_plan=plan, year=1, preferred_room=room)
    assert Resource.objects.get(pk=c.pk).kind == Resource.Kind.CLASS
    assert c.preferred_room == room


@pytest.mark.django_db
def test_part_inherits_study_plan_from_class(plan):
    c = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    partition = ClassPartition.objects.create(school_class=c, name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=partition)
    assert rel.study_plan is None                 # NULL = eredita
    assert rel.effective_study_plan == plan       # condizione 3 di ADR-015


@pytest.mark.django_db
def test_articulated_class_part_carries_its_own_plan(plan):
    other = StudyPlan.objects.create(code="ELE3", name="Elettronica 3", year=3)
    c = SchoolClass.objects.create(name="3A", study_plan=plan, year=3)
    partition = ClassPartition.objects.create(school_class=c, name="Articolazione")
    part_b = ClassPart.objects.create(name="3A_ELE", partition=partition, study_plan=other)
    assert part_b.effective_study_plan == other


@pytest.mark.django_db
def test_group_crosses_classes_through_parts(plan):
    a = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    b = SchoolClass.objects.create(name="1B", study_plan=plan, year=1)
    pa = ClassPartition.objects.create(school_class=a, name="Lingua")
    pb = ClassPartition.objects.create(school_class=b, name="Lingua")
    part_a = ClassPart.objects.create(name="1A_FRA", partition=pa)
    part_b = ClassPart.objects.create(name="1B_FRA", partition=pb)
    g = Group.objects.create(name="FRANCESE 1A-1B")
    g.parts.add(part_a, part_b)
    classes = {p.partition.school_class.name for p in g.parts.all()}
    assert classes == {"1A", "1B"}
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_classes.py -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementa i modelli**

`domain/models/classes.py`:

```python
from django.db import models

from .curriculum import StudyPlan
from .resources import Resource, Room


class SchoolClass(Resource):
    KIND = Resource.Kind.CLASS
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.PROTECT, related_name="classes")
    year = models.PositiveSmallIntegerField()
    preferred_room = models.ForeignKey(
        Room, null=True, blank=True, on_delete=models.SET_NULL, related_name="preferred_by"
    )
    max_weekly_weight_per_student = models.PositiveSmallIntegerField(null=True, blank=True)


class ClassPartition(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="partitions")
    name = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school_class", "name"], name="uniq_partition_per_class"),
        ]


class ClassPart(Resource):
    KIND = Resource.Kind.CLASS_PART
    partition = models.ForeignKey(ClassPartition, on_delete=models.CASCADE, related_name="parts")
    study_plan = models.ForeignKey(
        StudyPlan, null=True, blank=True, on_delete=models.PROTECT, related_name="parts"
    )

    @property
    def effective_study_plan(self):
        return self.study_plan or self.partition.school_class.study_plan


class Group(models.Model):
    """Raggruppamento trasversale (FR groupe): M2M di parti, attraversa più
    classi. Derivato dall'allineamento, non anagrafica a monte."""

    name = models.CharField(max_length=100, unique=True)
    parts = models.ManyToManyField(ClassPart, related_name="groups")
```

Aggiungi a `domain/models/__init__.py`:
`ClassPart, ClassPartition, Group, SchoolClass`.

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_classes.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_classes.py
git commit -m "feat(domain): classi, partizioni, parti e raggruppamenti trasversali"
```

---

### Task 5: Docenti e cattedre

**Files:**
- Create: `domain/models/teachers.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_teachers.py`

**Interfaces:**
- Consumes: `Resource`, `InstituteSettings` (Task 2); `Subject` (Task 3);
  `SchoolClass`, `ClassPart`, `Group` (Task 4).
- Produces: `Teacher(Resource)` con `last_name`, `first_name`, `abbreviation`,
  `status`, `weekly_minutes` nullable + `effective_weekly_minutes`,
  `max_overtime_minutes`, `preferred_subject`, M2M `teachable_subjects`;
  `TeachingAssignment(teacher, subject, school_class|class_part|group,
  weekly_minutes)` con CheckConstraint «esattamente una unità».

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_teachers.py`:

```python
import pytest
from django.db import IntegrityError

from domain.models import (
    Discipline, InstituteSettings, SchoolClass, StudyPlan, Subject, Teacher,
    TeachingAssignment,
)


@pytest.fixture
def subject(db):
    let = Discipline.objects.create(code="LET", name="Lettere")
    return Subject.objects.create(code="ITA", name="Italiano", discipline=let)


@pytest.fixture
def school_class(db):
    plan = StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)
    return SchoolClass.objects.create(name="1A", study_plan=plan, year=1)


@pytest.mark.django_db
def test_capability_is_separate_from_assignment(subject, school_class):
    t = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")
    t.teachable_subjects.add(subject)          # capacità (ADR-006)
    assert TeachingAssignment.objects.count() == 0  # nessuna cattedra implicita


@pytest.mark.django_db
def test_weekly_minutes_inherits_global_default(subject):
    settings = InstituteSettings.load()
    settings.default_teacher_weekly_minutes = 18 * 60
    settings.save()
    t = Teacher.objects.create(name="Bianchi Marco", last_name="Bianchi", first_name="Marco")
    assert t.weekly_minutes is None
    assert t.effective_weekly_minutes == 18 * 60


@pytest.mark.django_db
def test_assignment_points_to_exactly_one_unit(subject, school_class):
    t = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")
    TeachingAssignment.objects.create(
        teacher=t, subject=subject, school_class=school_class, weekly_minutes=240
    )
    with pytest.raises(IntegrityError):
        TeachingAssignment.objects.create(teacher=t, subject=subject, weekly_minutes=240)
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_teachers.py -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementa i modelli**

`domain/models/teachers.py`:

```python
from django.db import models

from .classes import ClassPart, Group, SchoolClass
from .curriculum import Subject
from .institute import InstituteSettings
from .resources import Resource

_EXACTLY_ONE_UNIT = (
    models.Q(school_class__isnull=False, class_part__isnull=True, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=False, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=True, group__isnull=False)
)


class Teacher(Resource):
    KIND = Resource.Kind.TEACHER
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=10, blank=True)
    status = models.CharField(max_length=30, blank=True)  # pura anagrafica
    weekly_minutes = models.PositiveIntegerField(null=True, blank=True)  # Mh/s; NULL = default globale
    max_overtime_minutes = models.PositiveIntegerField(null=True, blank=True)  # HSMax
    preferred_subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.SET_NULL, related_name="preferred_by"
    )
    teachable_subjects = models.ManyToManyField(Subject, related_name="teachable_by", blank=True)

    @property
    def effective_weekly_minutes(self):
        if self.weekly_minutes is not None:
            return self.weekly_minutes
        return InstituteSettings.load().default_teacher_weekly_minutes


class TeachingAssignment(models.Model):
    """La cattedra: docente × materia × unità × ore. L'unità è classe, parte o
    raggruppamento — mai solo la classe intera."""

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="assignments")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.CASCADE)
    class_part = models.ForeignKey(ClassPart, null=True, blank=True, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    weekly_minutes = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=_EXACTLY_ONE_UNIT, name="assignment_exactly_one_unit"),
        ]

    @property
    def unit(self):
        return self.school_class or self.class_part or self.group
```

Aggiungi a `domain/models/__init__.py`: `Teacher, TeachingAssignment`.

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_teachers.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_teachers.py
git commit -m "feat(domain): docenti (capacita' separata dalla cattedra) e assegnazioni"
```

---

### Task 6: Il tempo — griglia, calendario, periodi, maschere

**Files:**
- Create: `domain/models/time.py`, `domain/weeks.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_time.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: `TimeGrid(days_per_cycle, slots_per_day, slot_minutes,
  morning_end_slot)` con metodo `half_day(slot) -> "morning"|"afternoon"`;
  `Break(grid, boundary_slot)` con metodo `straddles(start_slot, duration_slots)
  -> bool`; `SchoolYear(start_date, end_date, first_week_monday)`;
  `Holiday(school_year, date)`; `Period(school_year, name, start_date,
  end_date)`; `Schedule(period, label)`. Modulo `domain/weeks.py`:
  `full_mask(n_weeks) -> int`, `single_week(index) -> int`,
  `week_in_mask(mask, index) -> bool`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_time.py`:

```python
import datetime

import pytest

from domain import weeks
from domain.models import Break, Period, Schedule, SchoolYear, TimeGrid


@pytest.mark.django_db
def test_half_day_derives_from_morning_end_line():
    grid = TimeGrid.objects.create(days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4)
    assert grid.half_day(0) == "morning"
    assert grid.half_day(3) == "morning"
    assert grid.half_day(4) == "afternoon"


@pytest.mark.django_db
def test_break_is_a_separator_not_a_slot():
    grid = TimeGrid.objects.create(days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4)
    brk = Break.objects.create(grid=grid, boundary_slot=2)  # fra il rango 1 e il 2
    assert brk.straddles(start_slot=1, duration_slots=2) is True   # blocco 1-2 a cavallo
    assert brk.straddles(start_slot=2, duration_slots=2) is False  # blocco 2-3 dopo
    assert brk.straddles(start_slot=0, duration_slots=2) is False  # blocco 0-1 prima


def test_week_masks():
    assert weeks.full_mask(33) == (1 << 33) - 1
    assert weeks.single_week(0) == 1
    assert weeks.week_in_mask(weeks.single_week(12), 12) is True
    assert weeks.week_in_mask(weeks.single_week(12), 11) is False


@pytest.mark.django_db
def test_schedule_belongs_to_a_period():
    year = SchoolYear.objects.create(
        start_date=datetime.date(2026, 9, 14),
        end_date=datetime.date(2027, 6, 8),
        first_week_monday=datetime.date(2026, 9, 14),
    )
    q1 = Period.objects.create(
        school_year=year, name="Primo quadrimestre",
        start_date=datetime.date(2026, 9, 14), end_date=datetime.date(2027, 1, 31),
    )
    sched = Schedule.objects.create(period=q1, label="bozza 1")
    assert sched.period.school_year == year
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_time.py -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementa**

`domain/weeks.py`:

```python
"""Maschere di settimane a bit: il bit i è la settimana i dell'anno scolastico
(settimana 0 = quella di first_week_monday). Annuale = tutti i bit; la
sostituzione/eccezione = un bit solo (ADR-014)."""


def full_mask(n_weeks: int) -> int:
    return (1 << n_weeks) - 1


def single_week(index: int) -> int:
    return 1 << index


def week_in_mask(mask: int, index: int) -> bool:
    return bool((mask >> index) & 1)
```

`domain/models/time.py`:

```python
from django.db import models


class TimeGrid(models.Model):
    """Griglia parametrica: giorni per ciclo × fasce. In v1 ciclo = settimana,
    ma i due concetti restano campi separati. Niente suddivisioni sub-orarie."""

    days_per_cycle = models.PositiveSmallIntegerField(default=5)
    slots_per_day = models.PositiveSmallIntegerField(default=6)
    slot_minutes = models.PositiveSmallIntegerField(default=60)
    morning_end_slot = models.PositiveSmallIntegerField()  # primo slot del pomeriggio

    def half_day(self, slot: int) -> str:
        return "morning" if slot < self.morning_end_slot else "afternoon"


class Break(models.Model):
    """Intervallo: separatore fra due ranghi, non consuma slot. La linea sta
    prima di boundary_slot."""

    grid = models.ForeignKey(TimeGrid, on_delete=models.CASCADE, related_name="breaks")
    boundary_slot = models.PositiveSmallIntegerField()

    def straddles(self, start_slot: int, duration_slots: int) -> bool:
        return start_slot < self.boundary_slot < start_slot + duration_slots


class SchoolYear(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    first_week_monday = models.DateField()  # ancora del ciclo al calendario reale


class Holiday(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()


class Period(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, related_name="periods")
    name = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()


class Schedule(models.Model):
    """Una versione d'orario per un periodo (ADR-010: si rigenera a ogni
    periodo). I piazzamenti appartengono a uno Schedule."""

    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name="schedules")
    label = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Aggiungi a `domain/models/__init__.py`:
`Break, Holiday, Period, Schedule, SchoolYear, TimeGrid`.

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_time.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_time.py
git commit -m "feat(domain): griglia oraria, calendario, periodi e maschere di settimane"
```

---

### Task 7: L'attività e il piazzamento

**Files:**
- Create: `domain/models/activities.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_activities.py`

**Interfaces:**
- Consumes: `Subject` (Task 3); `SchoolClass`, `ClassPart`, `Group` (Task 4);
  `Teacher` (Task 5); `Room`, `StaffMember`, `Material`, `Site` (Task 2);
  `Schedule` (Task 6); `domain/weeks.py`.
- Produces: `Activity` (campi sotto), `ActivityMaterialRequirement(activity,
  material, quantity)`, `Placement(schedule, activity, day, start_slot,
  assigned_room)` con UniqueConstraint su `(schedule, activity)`.
  `Activity.Immobility` TextChoices: `NONE, FIXED, LOCKED_IN_PLACE,
  NOT_SUSPENDABLE, SUSPENDED`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_activities.py`:

```python
import datetime

import pytest

from domain import weeks
from domain.models import (
    Activity, ActivityMaterialRequirement, Discipline, Material, Period, Placement,
    Schedule, SchoolClass, SchoolYear, StudyPlan, Subject, Teacher,
)


@pytest.fixture
def subject(db):
    let = Discipline.objects.create(code="LET", name="Lettere")
    return Subject.objects.create(code="ITA", name="Italiano", discipline=let)


@pytest.fixture
def school_class(db):
    plan = StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)
    return SchoolClass.objects.create(name="1A", study_plan=plan, year=1)


@pytest.mark.django_db
def test_subject_is_the_only_required_reference(subject):
    a = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60, week_mask=weeks.full_mask(33)
    )
    assert a.teachers.count() == 0  # un'attività senza docente è legale (XSD)
    assert a.immobility == Activity.Immobility.NONE


@pytest.mark.django_db
def test_substitution_is_a_single_bit_activity(subject, school_class):
    original = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60, week_mask=weeks.full_mask(33)
    )
    sub = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60,
        week_mask=weeks.single_week(12), parent=original,
    )
    assert bin(sub.week_mask).count("1") == 1  # ADR-014: un bit solo
    assert sub.parent == original


@pytest.mark.django_db
def test_activity_requires_materials_with_quantity(subject):
    a = Activity.objects.create(
        subject=subject, duration_slots=1, duration_minutes=60, week_mask=1
    )
    laptops = Material.objects.create(name="PC portatile", simultaneous_capacity=12)
    ActivityMaterialRequirement.objects.create(activity=a, material=laptops, quantity=5)
    assert a.material_requirements.get().quantity == 5


@pytest.mark.django_db
def test_placement_is_separate_and_unique_per_schedule(subject):
    a = Activity.objects.create(
        subject=subject, duration_slots=2, duration_minutes=120, week_mask=1
    )
    year = SchoolYear.objects.create(
        start_date=datetime.date(2026, 9, 14), end_date=datetime.date(2027, 6, 8),
        first_week_monday=datetime.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="Q1",
        start_date=datetime.date(2026, 9, 14), end_date=datetime.date(2027, 1, 31),
    )
    sched = Schedule.objects.create(period=period)
    Placement.objects.create(schedule=sched, activity=a, day=0, start_slot=2)
    assert Placement.objects.count() == 1
    import django.db.utils
    with pytest.raises(django.db.utils.IntegrityError):
        Placement.objects.create(schedule=sched, activity=a, day=1, start_slot=0)
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_activities.py -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementa i modelli**

`domain/models/activities.py`:

```python
from django.db import models

from .classes import ClassPart, Group, SchoolClass
from .curriculum import Subject
from .institute import Site
from .resources import Material, Room, StaffMember
from .teachers import Teacher
from .time import Schedule


class Activity(models.Model):
    """L'unità di piazzamento (ADR-014): una sola entità con maschera
    temporale. La sostituzione è la stessa riga con un bit solo."""

    class Immobility(models.TextChoices):
        NONE = "none"
        FIXED = "fixed"
        LOCKED_IN_PLACE = "locked_in_place"
        NOT_SUSPENDABLE = "not_suspendable"
        SUSPENDED = "suspended"

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)  # unico obbligatorio
    teachers = models.ManyToManyField(Teacher, blank=True, related_name="activities")
    classes = models.ManyToManyField(SchoolClass, blank=True, related_name="activities")
    parts = models.ManyToManyField(ClassPart, blank=True, related_name="activities")
    groups = models.ManyToManyField(Group, blank=True, related_name="activities")
    rooms = models.ManyToManyField(Room, blank=True, related_name="activities")  # eccezione dichiarata
    staff = models.ManyToManyField(StaffMember, blank=True, related_name="activities")
    materials = models.ManyToManyField(
        Material, blank=True, through="ActivityMaterialRequirement", related_name="activities"
    )
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT)

    duration_slots = models.PositiveSmallIntegerField()
    duration_minutes = models.PositiveIntegerField()
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )  # spezzamento padre/figlio (TypeParenteCours)
    alignment_ident = models.CharField(max_length=50, blank=True)  # stesso ident = attività complessa
    week_mask = models.PositiveBigIntegerField()

    respects_breaks = models.BooleanField(default=False)
    priority = models.BooleanField(default=False)
    immobility = models.CharField(max_length=20, choices=Immobility.choices, default=Immobility.NONE)


class ActivityMaterialRequirement(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="material_requirements")
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)


class Placement(models.Model):
    """Il piazzamento è output, mai sull'attività. assigned_room è l'esito
    della seconda fase (assegnazione aule), distinto dalle aule dichiarate."""

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="placements")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="placements")
    day = models.PositiveSmallIntegerField()
    start_slot = models.PositiveSmallIntegerField()
    assigned_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["schedule", "activity"], name="uniq_placement_per_schedule"),
        ]
```

Aggiungi a `domain/models/__init__.py`:
`Activity, ActivityMaterialRequirement, Placement`.

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_activities.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_activities.py
git commit -m "feat(domain): attivita' con maschera temporale e piazzamento separato"
```

---

### Task 8: I vincoli come dati

**Files:**
- Create: `domain/models/constraints.py`
- Modify: `domain/models/__init__.py`
- Test: `tests/test_constraints.py`

**Interfaces:**
- Consumes: `Resource` (Task 2); `Subject` (Task 3); `SchoolClass`, `ClassPart`,
  `Group` (Task 4); `Activity` (Task 7).
- Produces: `ResourceUnavailability(resource, day, slot, level, date)` con
  `Level` TextChoices `HARD/OPTIONAL/PREFERENCE`; `ResourceTimeConstraint(
  resource, type, params)` con `Type` TextChoices (8 valori sotto);
  `SubjectConstraint(school_class|class_part|group, subject_a, subject_b, type,
  param)` con `Type` TextChoices (13 valori dell'enum interno EDT);
  `RelaxationQuota(family, resource, max_violations)`;
  `Extraction(name)` con M2M `activities`.

- [ ] **Step 1: Scrivi i test che falliscono**

`tests/test_constraints.py`:

```python
import datetime

import pytest

from domain.models import (
    Discipline, Extraction, RelaxationQuota, ResourceTimeConstraint,
    ResourceUnavailability, SchoolClass, StudyPlan, Subject, SubjectConstraint, Teacher,
)


@pytest.fixture
def teacher(db):
    return Teacher.objects.create(name="Russo Elena", last_name="Russo", first_name="Elena")


@pytest.fixture
def school_class(db):
    plan = StudyPlan.objects.create(code="SCI1", name="Scientifico 1", year=1)
    return SchoolClass.objects.create(name="1A", study_plan=plan, year=1)


@pytest.fixture
def arte(db):
    art = Discipline.objects.create(code="ART", name="Arte")
    return Subject.objects.create(code="DIS", name="Disegno", discipline=art)


@pytest.mark.django_db
def test_unavailability_and_absence_share_one_table(teacher):
    recurring = ResourceUnavailability.objects.create(
        resource=teacher, day=1, slot=3, level=ResourceUnavailability.Level.HARD
    )
    dated = ResourceUnavailability.objects.create(
        resource=teacher, day=1, slot=3,
        level=ResourceUnavailability.Level.HARD, date=datetime.date(2027, 3, 12),
    )
    assert recurring.date is None   # NULL = ricorrente, ogni settimana
    assert dated.date is not None   # valorizzata = assenza puntuale


@pytest.mark.django_db
def test_time_constraint_serves_teachers_and_classes(teacher, school_class):
    ResourceTimeConstraint.objects.create(
        resource=teacher, type=ResourceTimeConstraint.Type.MAX_HOURS, params={"day_minutes": 360}
    )
    ResourceTimeConstraint.objects.create(
        resource=school_class, type=ResourceTimeConstraint.Type.MAX_HALF_DAYS,
        params={"max_half_days": 9},
    )  # MMG della classe = stesso vincolo del docente
    assert ResourceTimeConstraint.objects.count() == 2


@pytest.mark.django_db
def test_subject_constraint_is_directed_and_self_pairs_allowed(school_class, arte):
    c = SubjectConstraint.objects.create(
        school_class=school_class, subject_a=arte, subject_b=arte,
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE,
    )  # il caso dominante: la materia con sé stessa
    assert c.subject_a == c.subject_b


@pytest.mark.django_db
def test_relaxation_is_a_quota_not_a_penalty(teacher):
    q = RelaxationQuota.objects.create(
        family=RelaxationQuota.Family.MAX_HOURS, resource=teacher, max_violations=2
    )
    assert q.max_violations == 2


@pytest.mark.django_db
def test_extraction_is_a_named_persistent_selection(arte):
    from domain.models import Activity
    a = Activity.objects.create(subject=arte, duration_slots=1, duration_minutes=60, week_mask=1)
    ext = Extraction.objects.create(name="biennio")
    ext.activities.add(a)
    assert ext.activities.count() == 1
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_constraints.py -v`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementa i modelli**

`domain/models/constraints.py`:

```python
from django.db import models

from .activities import Activity
from .classes import ClassPart, Group, SchoolClass
from .curriculum import Subject
from .resources import Resource

_EXACTLY_ONE_UNIT = (
    models.Q(school_class__isnull=False, class_part__isnull=True, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=False, group__isnull=True)
    | models.Q(school_class__isnull=True, class_part__isnull=True, group__isnull=False)
)


class ResourceUnavailability(models.Model):
    """Rosso/giallo/verde, generico sulla risorsa. date NULL = ricorrente;
    valorizzata = assenza puntuale: indisponibilità e assenze, una tabella."""

    class Level(models.TextChoices):
        HARD = "hard"            # rosso
        OPTIONAL = "optional"    # giallo: violabile solo con override globale
        PREFERENCE = "preference"  # verde

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="unavailabilities")
    day = models.PositiveSmallIntegerField()
    slot = models.PositiveSmallIntegerField()
    level = models.CharField(max_length=10, choices=Level.choices)
    date = models.DateField(null=True, blank=True)


class ResourceTimeConstraint(models.Model):
    """L'asse Cardinalità: i sette gruppi del pannello docente + la soglia
    buchi, sulla risorsa generica (stessa tabella per docenti e classi).
    Chiavi attese in params, per type:
      MIN_DISTRIBUTION:   {"min_days": int, "min_minutes_per_day": int}
      MAX_HOURS:          {"day_minutes": int?, "morning_minutes": int?, "afternoon_minutes": int?}
      MAX_PRESENCE:       {"days": int, "max_minutes": int}
      ARRIVAL_DEPARTURE:  {"days": int, "not_before_slot": int?, "not_after_slot": int?}
      FREE_GUARANTEED:    {"free_days": int, "free_half_days": int}
      MAX_HALF_DAYS:      {"max_half_days": int?, "only_half_day_per_day": bool?}
      MAX_SITE_CHANGES:   {"per_day": int?, "per_week": int?}
      MAX_GAP_HOURS:      {"max_gap_minutes": int}   # D.T.B.
    """

    class Type(models.TextChoices):
        MIN_DISTRIBUTION = "min_distribution"
        MAX_HOURS = "max_hours"
        MAX_PRESENCE = "max_presence"
        ARRIVAL_DEPARTURE = "arrival_departure"
        FREE_GUARANTEED = "free_guaranteed"
        MAX_HALF_DAYS = "max_half_days"
        MAX_SITE_CHANGES = "max_site_changes"
        MAX_GAP_HOURS = "max_gap_hours"

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="time_constraints")
    type = models.CharField(max_length=20, choices=Type.choices)
    params = models.JSONField(default=dict)


class SubjectConstraint(models.Model):
    """L'asse Relazione: orientato (A→B ≠ B→A), con A = B come caso dominante.
    L'enum ricalca TypeIncompatibiliteMatiereClasse di EDT (13 valori);
    l'orizzonte settimana/ciclo e il ritardo delle concatenazioni stanno in
    param (mezze giornate, o minuti per i MAX_HOURS_*)."""

    class Type(models.TextChoices):
        SAME_HALF_DAY_INCOMPATIBLE = "same_half_day_incompatible"
        SAME_DAY_INCOMPATIBLE = "same_day_incompatible"
        TWO_DAYS_INCOMPATIBLE = "two_days_incompatible"
        FORBIDDEN_SEQUENCE = "forbidden_sequence"
        MAX_HOURS_HALF_DAY = "max_hours_half_day"
        MAX_HOURS_DAY = "max_hours_day"
        WEEKLY_ORDER = "weekly_order"
        IMPOSED_SUCCESSION = "imposed_succession"
        HALF_DAY_GAP = "half_day_gap"
        PARTS_BEFORE_CLASS = "parts_before_class"
        PARTS_AFTER_CLASS = "parts_after_class"
        PARTS_BEFORE_OR_AFTER_CLASS_H = "parts_before_or_after_class_h"
        PARTS_BEFORE_OR_AFTER_CLASS_AB = "parts_before_or_after_class_ab"

    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.CASCADE)
    class_part = models.ForeignKey(ClassPart, null=True, blank=True, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.CASCADE)
    subject_a = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="constraints_as_a")
    subject_b = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="constraints_as_b")
    type = models.CharField(max_length=40, choices=Type.choices)
    param = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=_EXACTLY_ONE_UNIT, name="subject_constraint_one_unit"),
        ]


class RelaxationQuota(models.Model):
    """Alleggerimento a quota, mai a penalità: numero massimo di violazioni,
    per famiglia e opzionalmente per risorsa. Modello lessicografico."""

    class Family(models.TextChoices):
        MAX_PRESENCE = "max_presence"
        FREE_GUARANTEED = "free_guaranteed"
        HALF_DAYS = "half_days"
        SUBJECT_CONSTRAINT = "subject_constraint"
        SITES = "sites"
        BREAKS = "breaks"
        OPTIONAL_UNAVAILABILITY = "optional_unavailability"
        UNAVAILABILITY = "unavailability"
        MAX_HOURS = "max_hours"
        DIDACTIC_WEIGHT = "didactic_weight"

    family = models.CharField(max_length=30, choices=Family.choices)
    resource = models.ForeignKey(
        Resource, null=True, blank=True, on_delete=models.CASCADE, related_name="relaxation_quotas"
    )
    max_violations = models.PositiveSmallIntegerField()


class Extraction(models.Model):
    """La selezione di lavoro persistente e nominata: il motore opera
    esclusivamente su di essa."""

    name = models.CharField(max_length=100, unique=True)
    activities = models.ManyToManyField(Activity, related_name="extractions", blank=True)
```

Aggiungi a `domain/models/__init__.py`:
`Extraction, RelaxationQuota, ResourceTimeConstraint, ResourceUnavailability, SubjectConstraint`.

- [ ] **Step 4: Migrazioni e test verdi**

Run: `python manage.py makemigrations domain && pytest tests/test_constraints.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add domain tests/test_constraints.py
git commit -m "feat(domain): i vincoli come dati sui quattro assi, quote ed estrazioni"
```

---

### Task 9: Il dataset Fermi come fixture

**Files:**
- Create: `tests/fermi.py`
- Test: `tests/test_fermi_representation.py`

**Interfaces:**
- Consumes: tutti i modelli dei task 2–8.
- Produces: `tests/fermi.py` con `build() -> dict` che popola il DB con
  l'intero dataset e restituisce `{"grid": TimeGrid, "plans": {code: StudyPlan},
  "classes": {name: SchoolClass}, "teachers": {tid: Teacher},
  "subjects": {code: Subject}}`.

La fonte è `data/liceo-fermi/*.md`; qui è trascritta in letterali Python (la
trascrizione È il test di rappresentazione — non si parsano i markdown).
Regole di derivazione, tutte dal dataset:

- ore per (materia, classe) = quadro orario per regime (biennio anni 1–2,
  triennio 3–5), colonna in `classi.md`;
- spezzamento in attività: MAT al biennio = blocchi `[2, 1, 1, 1]`
  (i quattro blocchi da 2h di `attivita.md`), tutto il resto blocchi da `[1] × ore`;
- aula preferenziale: `1A→A101 … 5A→A105`, `1B→B101 … 5B→B105` (mappatura
  nostra, coerente col vincolo "sezione A/B" di `aule.md`);
- `Al./Rid.` delle materie: NULL ovunque + default d'istituto 15 (tutte
  ereditano, `materie.md`);
- Mh/s: esplicito per docente (colonna Ore).

- [ ] **Step 1: Scrivi il test che fallisce**

`tests/test_fermi_representation.py`:

```python
import pytest

from domain.models import (
    Activity, Discipline, Room, SchoolClass, Service, StudyPlan, Subject, Teacher,
    TeachingAssignment,
)
from tests import fermi


@pytest.fixture
def dataset(db):
    return fermi.build()


def test_entity_counts(dataset):
    assert Discipline.objects.count() == 8
    assert Subject.objects.count() == 12
    assert StudyPlan.objects.count() == 5
    assert Service.objects.count() == 2 * 10 + 3 * 11  # biennio 10 materie, triennio 11
    assert SchoolClass.objects.count() == 10
    assert Teacher.objects.count() == 18
    assert Room.objects.count() == 16


def test_284_activities_for_288_hours(dataset):
    assert Activity.objects.count() == 284
    total = sum(Activity.objects.values_list("duration_minutes", flat=True))
    assert total == 288 * 60


def test_every_teacher_balances_to_zero(dataset):
    for teacher in Teacher.objects.all():
        assigned = sum(
            a.weekly_minutes for a in TeachingAssignment.objects.filter(teacher=teacher)
        )
        assert assigned == teacher.effective_weekly_minutes, teacher.name


def test_coverage_per_plan_and_subject_not_just_totals(dataset):
    """La lezione di vincoli-attesi.md: STO/SCI invertite tornavano nei totali.
    Si controlla per (classe, materia), contro il servizio del piano."""
    for school_class in SchoolClass.objects.all():
        for service in school_class.study_plan.services.all():
            placed = sum(
                a.duration_minutes
                for a in Activity.objects.filter(classes=school_class, subject=service.subject)
            )
            assert placed == service.class_minutes, (school_class.name, service.subject.code)


def test_gym_hosts_two_classes_lab_inf_is_smaller(dataset):
    assert Room.objects.get(name="PALESTRA").simultaneous_capacity == 2
    assert Room.objects.get(name="LAB-INF").capacity == 25
```

- [ ] **Step 2: Esegui e verifica che fallisca**

Run: `pytest tests/test_fermi_representation.py -v`
Expected: FAIL con `ImportError: cannot import name 'fermi'`.

- [ ] **Step 3: Scrivi la fixture**

`tests/fermi.py`:

```python
"""Il dataset del Liceo Fermi (data/liceo-fermi/*.md) trascritto in letterali
Python. La trascrizione è essa stessa il test: se lo schema non riesce a
rappresentare una riga, il build fallisce."""

from domain import weeks
from domain.models import (
    Activity, CompetitionClass, Discipline, InstituteSettings, Room, SchoolClass,
    Service, StudyPlan, Subject, Teacher, TeachingAssignment, TimeGrid,
)

WEEKS_IN_YEAR = 33  # periodicità S (33/33) osservata in EDT

DISCIPLINES = {  # codice: (nome, [classi di concorso])
    "LET": ("Lettere", ["A011", "A013"]),
    "STF": ("Storia e Filosofia", ["A019"]),
    "LIN": ("Lingue straniere", ["AB24"]),
    "MAF": ("Matematica e Fisica", ["A027"]),
    "SCN": ("Scienze", ["A050"]),
    "ART": ("Discipline artistiche", ["A017"]),
    "MOT": ("Scienze motorie", ["A048"]),
    "REL": ("Religione", ["IRC"]),
}

SUBJECTS = {  # codice: (nome, disciplina)
    "ITA": ("Italiano", "LET"), "LAT": ("Latino", "LET"),
    "STG": ("Storia e Geografia", "LET"),
    "STO": ("Storia", "STF"), "FIL": ("Filosofia", "STF"),
    "ING": ("Inglese", "LIN"),
    "MAT": ("Matematica", "MAF"), "FIS": ("Fisica", "MAF"),
    "SCI": ("Scienze naturali", "SCN"), "DIS": ("Disegno e Storia dell'Arte", "ART"),
    "MOT": ("Scienze motorie", "MOT"), "IRC": ("Religione cattolica", "REL"),
}

CURRICULUM = {  # materia: (ore biennio, ore triennio); None = non presente
    "ITA": (4, 4), "LAT": (3, 3), "ING": (3, 3), "STG": (3, None),
    "STO": (None, 2), "FIL": (None, 3), "MAT": (5, 4), "FIS": (2, 3),
    "SCI": (2, 3), "DIS": (2, 2), "MOT": (2, 2), "IRC": (1, 1),
}

CLASSES = [f"{y}{s}" for s in "AB" for y in range(1, 6)]  # 1A..5A, 1B..5B

ROOMS = (
    [(f"A10{i}", 30, 1) for i in range(1, 6)]
    + [(f"B10{i}", 30, 1) for i in range(1, 6)]
    + [("LAB-FIS", 30, 1), ("LAB-SCI", 30, 1), ("LAB-INF", 25, 1),
       ("AUL-DIS", 30, 1), ("PALESTRA", 60, 2), ("AULA-MAGNA", 100, 1)]
)

ALL = CLASSES
TEACHERS = [  # (id, nome, abbr, [(materia, [classi])], ore Mh/s, materia preferenziale)
    ("D01", "Rossi Anna", "ROSSI", [("ITA", ["1A", "2A", "3A"]), ("LAT", ["1A", "2A", "3A"])], 21, "ITA"),
    ("D02", "Bianchi Marco", "BIANC", [("ITA", ["4A", "5A"]), ("LAT", ["4A", "5A"])], 14, "ITA"),
    ("D03", "Verdi Chiara", "VERDI", [("ITA", ["1B", "2B", "3B"]), ("LAT", ["1B", "2B", "3B"])], 21, "ITA"),
    ("D04", "Neri Paolo", "NERI", [("ITA", ["4B", "5B"]), ("LAT", ["4B", "5B"])], 14, "ITA"),
    ("D05", "Ferrari Giulia", "FERRA", [("ING", ["1A", "2A", "3A", "4A", "5A", "1B"])], 18, "ING"),
    ("D06", "Russo Elena", "RUSSO", [("ING", ["2B", "3B", "4B", "5B"])], 12, "ING"),
    ("D07", "Conti Luca", "CONTI", [("FIL", ["3A", "4A", "5A"]), ("STO", ["3A", "4A", "5A"]), ("STG", ["1A"])], 18, "FIL"),
    ("D08", "Marino Sara", "MARIN", [("FIL", ["3B", "4B", "5B"]), ("STO", ["3B", "4B", "5B"]), ("STG", ["1B"])], 18, "FIL"),
    ("D09", "Greco Ilaria", "GRECO", [("STG", ["2A", "2B"])], 6, "STG"),
    ("D10", "Costa Davide", "COSTA", [("MAT", ["1A", "2A", "3A"]), ("FIS", ["1A", "2A", "3A"])], 21, "MAT"),
    ("D11", "Gallo Francesca", "GALLO", [("MAT", ["4A", "5A"]), ("FIS", ["4A", "5A"])], 14, "MAT"),
    ("D12", "Lombardi Andrea", "LOMBA", [("MAT", ["1B", "2B", "3B"]), ("FIS", ["1B", "2B", "3B"])], 21, "MAT"),
    ("D13", "Fontana Silvia", "FONTA", [("MAT", ["4B", "5B"]), ("FIS", ["4B", "5B"])], 14, "MAT"),
    ("D14", "Ricci Matteo", "RICCI", [("SCI", ["1A", "2A", "3A", "4A", "5A", "1B", "2B"])], 17, "SCI"),
    ("D15", "Esposito Laura", "ESPOS", [("SCI", ["3B", "4B", "5B"])], 9, "SCI"),
    ("D16", "Barbieri Giorgio", "BARB", [("DIS", ALL)], 20, "DIS"),
    ("D17", "Villa Roberto", "VILLA", [("MOT", ALL)], 20, "MOT"),
    ("D18", "Piani Stefano", "PIANI", [("IRC", ALL)], 10, "IRC"),
]


def _year(class_name):
    return int(class_name[0])


def _hours(subject_code, class_name):
    biennio, triennio = CURRICULUM[subject_code]
    return biennio if _year(class_name) <= 2 else triennio


def _blocks(subject_code, class_name):
    hours = _hours(subject_code, class_name)
    if subject_code == "MAT" and _year(class_name) <= 2:
        return [2, 1, 1, 1]  # i quattro blocchi da 2h di attivita.md
    return [1] * hours


def build():
    settings = InstituteSettings.load()
    settings.default_max_reduced_students = 15
    settings.save()

    grid = TimeGrid.objects.create(
        days_per_cycle=5, slots_per_day=6, slot_minutes=60, morning_end_slot=4
    )

    disciplines, subjects = {}, {}
    for code, (name, ccs) in DISCIPLINES.items():
        d = Discipline.objects.create(code=code, name=name)
        for cc in ccs:
            obj, _ = CompetitionClass.objects.get_or_create(code=cc)
            d.competition_classes.add(obj)
        disciplines[code] = d
    for code, (name, disc) in SUBJECTS.items():
        subjects[code] = Subject.objects.create(code=code, name=name, discipline=disciplines[disc])

    plans = {}
    for year in range(1, 6):
        plan = StudyPlan.objects.create(
            code=f"SCI{year}", name=f"Liceo Scientifico - {year} anno", year=year
        )
        col = 0 if year <= 2 else 1
        for subject_code, hours_pair in CURRICULUM.items():
            hours = hours_pair[col]
            if hours is not None:
                Service.objects.create(
                    study_plan=plan, subject=subjects[subject_code], class_minutes=hours * 60
                )
        plans[plan.code] = plan

    rooms = {
        name: Room.objects.create(name=name, capacity=cap, simultaneous_capacity=simult)
        for name, cap, simult in ROOMS
    }

    classes = {}
    for name in CLASSES:
        classes[name] = SchoolClass.objects.create(
            name=name, study_plan=plans[f"SCI{_year(name)}"], year=_year(name),
            preferred_room=rooms[f"{name[1]}10{name[0]}"],  # 1A→A101 … 5B→B105
        )

    teachers = {}
    year_mask = weeks.full_mask(WEEKS_IN_YEAR)
    for tid, full_name, abbr, assignments, hours, preferred in TEACHERS:
        last, first = full_name.split(" ", 1)
        t = Teacher.objects.create(
            name=full_name, last_name=last, first_name=first, abbreviation=abbr,
            weekly_minutes=hours * 60, preferred_subject=subjects[preferred],
        )
        for subject_code, class_names in assignments:
            t.teachable_subjects.add(subjects[subject_code])
            for class_name in class_names:
                TeachingAssignment.objects.create(
                    teacher=t, subject=subjects[subject_code],
                    school_class=classes[class_name],
                    weekly_minutes=_hours(subject_code, class_name) * 60,
                )
                for block in _blocks(subject_code, class_name):
                    activity = Activity.objects.create(
                        subject=subjects[subject_code],
                        duration_slots=block, duration_minutes=block * 60,
                        week_mask=year_mask,
                    )
                    activity.teachers.add(t)
                    activity.classes.add(classes[class_name])
        teachers[tid] = t

    return {
        "grid": grid, "plans": plans, "classes": classes,
        "teachers": teachers, "subjects": subjects,
    }
```

- [ ] **Step 4: Esegui e verifica che passi**

Run: `pytest tests/test_fermi_representation.py -v`
Expected: PASS (5 passed). Se `test_every_teacher_balances_to_zero` o
`test_coverage_per_plan_and_subject_not_just_totals` falliscono, l'errore è
nella trascrizione (o nello schema): NON aggiustare le asserzioni — i numeri
attesi (288h, +/-=0 per 18 docenti) sono quadrature verificate in EDT.

- [ ] **Step 5: Commit**

```bash
git add tests/fermi.py tests/test_fermi_representation.py
git commit -m "test(domain): il dataset Fermi interamente rappresentato nello schema"
```

---

### Task 10: I casi che il Fermi non ha

**Files:**
- Test: `tests/test_beyond_fermi.py`

**Interfaces:**
- Consumes: tutti i modelli; `tests/fermi.py` (`build()`, `WEEKS_IN_YEAR`).
- Produces: solo test — la prova che lo schema regge i casi della base di
  esempio EDT assenti dal Fermi.

- [ ] **Step 1: Scrivi i test**

`tests/test_beyond_fermi.py`:

```python
import pytest

from domain import weeks
from domain.models import (
    Activity, ClassPart, ClassPartition, Group, InstituteSettings, Site,
)
from tests import fermi


@pytest.fixture
def dataset(db):
    return fermi.build()


def _irc_partition(dataset, class_name):
    c = dataset["classes"][class_name]
    partition = ClassPartition.objects.create(school_class=c, name="IRC")
    rel = ClassPart.objects.create(name=f"{class_name}_REL", partition=partition)
    alt = ClassPart.objects.create(name=f"{class_name}_ALT", partition=partition)
    return rel, alt


@pytest.mark.django_db
def test_irc_and_alternative_are_two_parts(dataset):
    rel, alt = _irc_partition(dataset, "1A")
    assert rel.partition == alt.partition          # stessa partizione
    assert rel.effective_study_plan == alt.effective_study_plan  # entrambe ereditano


@pytest.mark.django_db
def test_transversal_group_and_its_activity(dataset):
    rel_a, _ = _irc_partition(dataset, "2A")
    rel_b, _ = _irc_partition(dataset, "2B")
    g = Group.objects.create(name="ALTERNATIVA 2A-2B")
    g.parts.add(rel_a, rel_b)
    a = Activity.objects.create(
        subject=dataset["subjects"]["IRC"], duration_slots=1, duration_minutes=60,
        week_mask=weeks.full_mask(fermi.WEEKS_IN_YEAR), alignment_ident="ALT-2AB",
    )
    a.groups.add(g)
    involved = {p.partition.school_class.name for p in a.groups.get().parts.all()}
    assert involved == {"2A", "2B"}  # l'attività accoppia due classi


@pytest.mark.django_db
def test_sites_with_transition_parameter(dataset):
    branch = Site.objects.create(name="Succursale")
    settings = InstituteSettings.load()
    settings.site_transition_slots = 1
    settings.save()
    a = Activity.objects.create(
        subject=dataset["subjects"]["MOT"], duration_slots=1, duration_minutes=60,
        week_mask=1, site=branch,
    )
    assert a.site == branch
    assert InstituteSettings.load().site_transition_slots == 1


@pytest.mark.django_db
def test_substitution_reuses_a_fermi_activity(dataset):
    original = Activity.objects.filter(classes=dataset["classes"]["1A"]).first()
    substitute = dataset["teachers"]["D02"]
    sub = Activity.objects.create(
        subject=original.subject, duration_slots=original.duration_slots,
        duration_minutes=original.duration_minutes,
        week_mask=weeks.single_week(12), parent=original,
    )
    sub.teachers.add(substitute)
    sub.classes.set(original.classes.all())
    assert bin(sub.week_mask).count("1") == 1
    assert list(sub.classes.all()) == list(original.classes.all())
```

- [ ] **Step 2: Esegui e verifica che passi**

Run: `pytest tests/test_beyond_fermi.py -v`
Expected: PASS (4 passed) — questi test non richiedono nuovo codice: se
falliscono, lo schema ha un buco e va corretto il modello, non il test.

- [ ] **Step 3: Suite completa**

Run: `pytest -v`
Expected: tutti i test dei task 1–10 verdi.

- [ ] **Step 4: Commit**

```bash
git add tests/test_beyond_fermi.py
git commit -m "test(domain): parti IRC/ALT, raggruppamenti trasversali, sedi e sostituzioni"
```

---

### Task 11: Chiusura — documentazione dello stato

**Files:**
- Modify: `CLAUDE.md` (struttura + stato + changelog)

- [ ] **Step 1: Aggiorna CLAUDE.md**

Nella sezione «Struttura dei documenti» aggiungi, dopo `scripts/`:

```
config/                progetto Django minimale (solo settings, niente view)
domain/                l'app Django del modello di dominio v1
tests/                 la suite; tests/fermi.py è il dataset Fermi come fixture
```

Nello stato del progetto, sostituisci la frase sul prossimo passo con: lo schema
è implementato e il dataset Fermi è interamente rappresentato (X test verdi —
usare il numero reale); i piani successivi sono predicati/analisi di capienza e
modello CP-SAT. Aggiungi una voce di changelog datata con: schema Django
implementato per TDD dal design di `docs/modello-dominio.md`, dataset Fermi come
primo test di rappresentazione (284 attività / 288h, 18 docenti a quadratura
zero, copertura per (classe, materia)), più i casi oltre-Fermi.

- [ ] **Step 2: Verifica finale e commit**

Run: `pytest` (tutta la suite verde) poi:

```bash
git add CLAUDE.md
git commit -m "docs: schema del dominio implementato, stato e changelog"
```

---

## Fuori da questo piano

- **Predicati e analisi di capienza** (piano 2): le due nature del vincolo,
  le causali nominate, il controllo di conformità, l'analisi pre-calcolo.
- **Modello CP-SAT** (piano 3): variabili a intervallo, `NoOverlap`/`cumulative`,
  alleggerimenti a quota, criterio «mantieni le collocazioni precedenti».
- Import dei dati (via d'ingresso ancora da scegliere, vedi design).
