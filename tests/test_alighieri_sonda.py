"""Il **cricchetto** della copertura: quali builder l'Alighieri esercita, oggi.

⚠ L'asserzione è un insieme e non un numero, e va **aggiornata a ogni ondata**
che aggiunge righe. È il punto: la spec (§6.4) fa della sonda il criterio di
accettazione — a ondata 7 l'insieme deve essere il registro intero — e un test
che dice solo `>= 4` lascerebbe passare l'ondata che aggiunge una tabella
senza svegliare il builder che dovrebbe leggerla.

Il confronto col Fermi è la misura che ha aperto il pezzo, e sta qui accanto
perché è ciò che rende il numero leggibile."""

import pytest

from tests import alighieri, fermi, sonda

pytestmark = pytest.mark.django_db


# Ondata 1 — l'anagrafica. Nessuna tabella di vincoli è ancora popolata:
# ciò che lavora è tutto **strutturale**, e sono le sedi e la griglia a essere
# nuove rispetto al Fermi.
ATTIVI_ONDATA_1 = {
    "structural:occupation",
    "structural:room_pool",
    "structural:site_transition",   # 🔑 il Fermi ha zero `Site`: qui è muto
    "structural:grid",              # blocchi lunghi + intervallo mensa
}


def test_l_alighieri_esercita_i_builder_dichiarati():
    env = alighieri.build()
    assert sonda.attivi(env["schedule"]) == ATTIVI_ONDATA_1


def test_il_fermi_ne_esercita_tre_ed_e_la_misura_che_apre_il_pezzo():
    """⚠ Questo test non chiede al Fermi di migliorare: il Fermi è una
    trascrizione e non si tocca per far passare niente. Fissa la misura del
    2026-08-30, così che la riga di `CLAUDE.md` che la riporta non torni a
    essere un elenco."""
    env = fermi.build()
    assert sonda.attivi(env["schedule"]) == {
        "structural:occupation",
        "structural:room_pool",
        "structural:unavailability",
    }
