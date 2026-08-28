"""Il comando `extract`: la selezione che l'utente costruisce e memorizza."""
from io import StringIO

import pytest
from django.core.management import call_command

from domain.models import (Extraction, ResourceTimeConstraint,
                           ResourceUnavailability, Room)
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _run(*args):
    out = StringIO()
    call_command("extract", *args, stdout=out)
    return out.getvalue()


def test_i_criteri_si_intersecano_fra_assi():
    env = mini_school()
    piazzata = make_activity(env["subject"], classes=[env["klass"]],
                             teachers=[env["teacher"]])
    altra_classe = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], piazzata, 0, 0)
    place(env["schedule"], altra_classe, 0, 1)

    testo = _run("--schedule", str(env["schedule"].pk),
                 "--stato", "piazzate",
                 "--risorsa", str(env["klass"].pk))
    assert "Estratte (1" in testo
    assert f"[{piazzata.pk}]" in testo
    assert f"[{altra_classe.pk}]" not in testo


def test_senza_salva_non_scrive_niente():
    env = mini_school()
    make_activity(env["subject"], classes=[env["klass"]])
    testo = _run("--schedule", str(env["schedule"].pk), "--stato", "non_piazzate")
    assert "Niente è stato scritto" in testo
    assert not Extraction.objects.exists()


def test_con_salva_l_estrazione_esiste_e_si_richiama():
    env = mini_school()
    act = make_activity(env["subject"], classes=[env["klass"]])
    _run("--schedule", str(env["schedule"].pk), "--stato", "non_piazzate",
         "--salva", "da-piazzare")

    estrazione = Extraction.objects.get(name="da-piazzare")
    assert list(estrazione.activities.values_list("pk", flat=True)) == [act.pk]
    assert "da-piazzare: 1 attività" in _run("--elenca")


def test_limita_raffina_l_estrazione_precedente():
    """`Limita la ricerca alle attività già estratte`: è ciò che rende la
    selezione componibile invece che un filtro usa-e-getta."""
    env = mini_school()
    lab = Room.objects.create(name="LAB")
    con_lab = make_activity(env["subject"], classes=[env["klass"]], rooms=[lab])
    senza = make_activity(env["subject"], classes=[env["klass"]])

    _run("--risorsa", str(env["klass"].pk), "--salva", "la-1A")
    _run("--base", "la-1A", "--modo", "limita",
         "--risorsa", str(lab.pk), "--salva", "la-1A-in-lab")

    assert set(Extraction.objects.get(name="la-1A")
               .activities.values_list("pk", flat=True)) == {con_lab.pk, senza.pk}
    assert set(Extraction.objects.get(name="la-1A-in-lab")
               .activities.values_list("pk", flat=True)) == {con_lab.pk}


def test_il_rilevatore_dichiara_i_finding_che_non_nominano_nessuno():
    """⚠ Vuoto e sano si leggono uguali se non lo si dice: qui la violazione
    c'è, ed è del D.T.B., che nomina il docente e nessuna lezione."""
    env = mini_school()
    prima = make_activity(env["subject"], teachers=[env["teacher"]])
    dopo = make_activity(env["subject"], teachers=[env["teacher"]])
    place(env["schedule"], prima, 0, 0)
    place(env["schedule"], dopo, 0, 3)
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"],
        type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    testo = _run("--schedule", str(env["schedule"].pk),
                 "--rileva", "non_rispettano_i_vincoli")
    assert "Violazioni che non nominano nessuna attività: 1" in testo
    assert "max_gap" in testo
    assert "**non** perché l'orario sia sano" in testo


def test_il_rilevatore_nomina_le_violazioni_attribuibili():
    env = mini_school()
    act = make_activity(env["subject"], classes=[env["klass"]],
                        teachers=[env["teacher"]])
    place(env["schedule"], act, 0, 0)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)

    testo = _run("--schedule", str(env["schedule"].pk),
                 "--rileva", "non_rispettano_i_vincoli", "--salva", "illegali")
    assert "Attività nominate: 1" in testo
    assert set(Extraction.objects.get(name="illegali")
               .activities.values_list("pk", flat=True)) == {act.pk}
