"""Il comando analyze: report in stile EDT, exit code per la CI."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import ResourceUnavailability, SubjectConstraint
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _run(*args):
    out = StringIO()
    call_command("analyze", *args, stdout=out)
    return out.getvalue()


def test_base_pulita():
    mini_school()
    out = _run()
    assert "Nessun problema di capienza" in out
    assert "Verifica terminata: nessuna incoerenza." in out


def test_deficit_di_capienza_stampa_i_quattro_riquadri_e_fallisce():
    env = mini_school()
    for slots in (2, 2, 2, 2, 1, 1):
        make_activity(env["subject"], classes=[env["klass"]], slots=slots)
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"], type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    out = StringIO()
    with pytest.raises(CommandError, match="Rimangono delle incoerenze."):
        call_command("analyze", stdout=out)
    text = out.getvalue()
    assert "I vincoli della classe non permettono il piazzamento" in text
    assert "Durata da piazzare: 10h00" in text
    assert "Durata piazzabile:  9h00" in text
    assert "» 1h00 non potrà essere piazzata" in text
    assert "Rendere i vincoli delle materie meno vincolanti" in text
    assert "1 problemi di capienza" in text          # il riepilogo che EDT non ha


def test_conformita_e_sp_con_schedule():
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]])
    non_piazzata = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=0)          # conflitto
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("analyze", "--schedule", str(env["schedule"].pk), stdout=out)
    text = out.getvalue()
    assert "già occupata in un'attività" in text
    assert "S.P." in text and "Italiano" in text      # la colonna delle non piazzate


def test_la_fase_5_esce_sotto_schedule():
    env = mini_school()
    for day in (1, 2, 3, 4):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    out = StringIO()
    with pytest.raises(CommandError):
        call_command("analyze", "--schedule", str(env["schedule"].pk), stdout=out)
    testo = out.getvalue()
    assert "Insiemi non piazzabili" in testo
    assert "Durata piazzabile" in testo


def test_no_hall_spegne_la_fase_5():
    env = mini_school()
    out = _run("--schedule", str(env["schedule"].pk), "--no-hall")
    assert "Insiemi non piazzabili" not in out


def test_senza_schedule_la_fase_5_si_dichiara_saltata():
    mini_school()
    assert "richiede --schedule" in _run()


def test_la_classifica_dei_vincoli_nomina_il_colpevole_e_le_silenziose():
    """La seconda lacuna di EDT: non «il calcolo è fallito», ma *quale*
    vincolo allentare. Qui c'è una sola risposta possibile — l'unica attività
    non ha nessuna cella, e l'unica causale è l'indisponibilità del docente."""
    env = mini_school(slots=2, days=1)
    make_activity(env["subject"], classes=[env["klass"]], teachers=[env["teacher"]])
    for slot in (0, 1):
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=0, slot=slot, level="hard")

    out = StringIO()
    with pytest.raises(CommandError):
        call_command("analyze", "--schedule", str(env["schedule"].pk), stdout=out)
    testo = out.getvalue()
    assert "Vincoli da allentare" in testo
    assert "1 senza nessuna collocazione ammissibile" in testo
    assert "Rossi Anna ha una indisponibilità" in testo
    assert "Attività che tornerebbero piazzabili: 1" in testo
    # ⚠ La rinuncia va dichiarata dal comando, non solo dal docstring: un
    # vincolo che tace e un vincolo innocuo si leggono uguali.
    assert "Non entrano in classifica" in testo and "max_gap_hours" in testo


def test_no_blame_spegne_la_classifica():
    env = mini_school()
    out = _run("--schedule", str(env["schedule"].pk), "--no-blame")
    assert "Vincoli da allentare" not in out


def test_senza_schedule_la_classifica_si_dichiara_saltata():
    mini_school()
    testo = _run()
    assert "== Vincoli da allentare ==" in testo and "richiede --schedule" in testo
