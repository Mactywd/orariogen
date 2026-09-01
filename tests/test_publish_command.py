"""Il comando `publish`: la griglia piatta, e la perdita detta a voce.

⚠ **Non scrive niente**, e i test lo tengono fermo: la destinazione — la
`ScheduleEntry` di Aurora — non esiste ancora in questo modello (ADR-032). Ciò
che il comando fa è **mostrare** cosa uscirà, che è il modo di guardare la
pubblicazione prima di poterla eseguire.
"""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import ClassPart, ClassPartition, Subject
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _run(*args):
    out = StringIO()
    call_command("publish", *args, stdout=out)
    return out.getvalue()


def test_un_orario_che_passa_intero_lo_dice():
    s = mini_school()
    a = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], a, day=0, slot=0)

    out = _run("--schedule", str(s["schedule"].pk))

    assert "Righe: 1" in out
    assert "Docenti: 1 · Classi: 1" in out
    assert "l'orario passa il confine intero" in out


def test_la_perdita_separa_le_due_nature():
    """🔑 Un'unità incompleta e un'ora che non esce non sono la stessa cosa, e
    il comando non le mette nello stesso elenco: la prima è
    un'approssimazione con cui Aurora convive, la seconda è un buco."""
    s = mini_school(days=6)
    part = ClassPart.objects.create(
        name="1A-A",
        partition=ClassPartition.objects.create(school_class=s["klass"],
                                                name="Lingue"))
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       parts=[part]), day=0, slot=0)
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       classes=[s["klass"]]), day=5, slot=0)

    out = _run("--schedule", str(s["schedule"].pk))

    assert "Vero ma incompleto" in out
    assert "1 attività su una parte di classe" in out
    assert "Non esce affatto:" in out
    assert "1 piazzamenti oltre il venerdì" in out


def test_la_cella_ambigua_si_nomina_per_esteso():
    s = mini_school()
    p = ClassPartition.objects.create(school_class=s["klass"], name="Lingue")
    a = ClassPart.objects.create(name="1A-A", partition=p)
    b = ClassPart.objects.create(name="1A-B", partition=p)
    altra = Subject.objects.create(code="STO", name="Storia",
                                   discipline=s["discipline"])
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       parts=[a]), day=0, slot=0)
    place(s["schedule"], make_activity(altra, teachers=[s["teacher"]],
                                       parts=[b]), day=0, slot=0)

    out = _run("--schedule", str(s["schedule"].pk))

    assert "Celle ambigue: 1" in out
    assert "Rossi Anna · monday ora 1 · 1A: ITA / STO" in out


def test_le_righe_si_stampano_solo_se_chieste():
    s = mini_school()
    a = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], a, day=0, slot=0)

    assert "Rossi Anna\tmonday\t1\t1A\tITA" not in _run(
        "--schedule", str(s["schedule"].pk))
    assert "Rossi Anna\tmonday\t1\t1A\tITA" in _run(
        "--schedule", str(s["schedule"].pk), "--righe")


def test_una_risorsa_inesistente_e_un_errore_non_un_orario_vuoto():
    s = mini_school()
    with pytest.raises(CommandError):
        _run("--schedule", str(s["schedule"].pk), "--risorsa", "99999")


def test_il_perimetro_restringe_l_uscita():
    """La regola di `Estrai`: restringe ciò su cui si **agisce**. Qui agire è
    pubblicare, quindi l'uscita si accorcia davvero."""
    from domain.models import Teacher
    s = mini_school()
    altro = Teacher.objects.create(name="Bianchi Ugo", last_name="Bianchi",
                                   first_name="Ugo")
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       classes=[s["klass"]]), day=0, slot=0)
    place(s["schedule"], make_activity(s["subject"], teachers=[altro],
                                       classes=[s["klass"]]), day=1, slot=0)

    intero = _run("--schedule", str(s["schedule"].pk))
    ristretto = _run("--schedule", str(s["schedule"].pk),
                     "--risorsa", str(altro.pk), "--righe")

    assert "Righe: 2" in intero
    assert "Righe: 1" in ristretto
    assert "Bianchi Ugo" in ristretto and "Rossi Anna" not in ristretto
