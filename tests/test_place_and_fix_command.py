"""Il comando `place_and_fix`: il rendiconto che l'utente legge prima di
accettare la mossa, e il rifiuto nominato quando non si puo'."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain.models import Placement, ResourceUnavailability
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _due_in_conflitto(slots=2):
    env = mini_school(days=1, slots=slots)
    occupante = make_activity(env["subject"], classes=[env["klass"]])
    entrante = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], occupante, 0, 0)
    place(env["schedule"], entrante, 0, 1)
    return env, occupante, entrante


def _run(env, act, giorno, fascia, *extra):
    out = StringIO()
    call_command("place_and_fix", "--schedule", str(env["schedule"].pk),
                 "--attivita", str(act.pk), "--giorno", str(giorno),
                 "--fascia", str(fascia), "--lavoratori", "1", *extra,
                 stdout=out)
    return out.getvalue()


def test_il_rendiconto_nomina_chi_si_sposta():
    env, occupante, entrante = _due_in_conflitto()
    testo = _run(env, entrante, 0, 0)
    assert "Attività ricollocate (1)" in testo
    assert "Italiano" in testo and "1A" in testo
    assert "→ giorno 0, fascia 1" in testo


def test_senza_applica_non_scrive_niente():
    """⚠ La stessa cautela di `solve`, e per la stessa ragione: forzare una
    collocazione riscrive l'orario di una scuola."""
    env, occupante, entrante = _due_in_conflitto()
    testo = _run(env, entrante, 0, 0)
    assert "Niente è stato scritto" in testo
    assert Placement.objects.get(activity=entrante).start_slot == 1
    assert Placement.objects.get(activity=occupante).start_slot == 0


def test_con_applica_l_orario_cambia_davvero():
    env, occupante, entrante = _due_in_conflitto()
    _run(env, entrante, 0, 0, "--applica")
    assert Placement.objects.get(activity=entrante).start_slot == 0
    assert Placement.objects.get(activity=occupante).start_slot == 1


def test_il_rifiuto_e_nominato_e_l_exit_code_lo_dice():
    """Non «INFEASIBLE»: la frase del catalogo delle causali, con il nome del
    docente dentro."""
    env = mini_school(days=1, slots=2)
    entrante = make_activity(env["subject"], classes=[env["klass"]],
                             teachers=[env["teacher"]])
    place(env["schedule"], entrante, 0, 1)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=0,
        level=ResourceUnavailability.Level.HARD)

    out = StringIO()
    with pytest.raises(CommandError, match="Collocazione rifiutata."):
        call_command("place_and_fix", "--schedule", str(env["schedule"].pk),
                     "--attivita", str(entrante.pk), "--giorno", "0",
                     "--fascia", "0", "--lavoratori", "1", stdout=out)
    testo = out.getvalue()
    assert "Non si può, e il motivo è questo" in testo
    assert "Rossi Anna ha una indisponibilità" in testo
