"""Il **cricchetto** della copertura: quali builder l'Alighieri esercita, oggi.

⚠ L'asserzione è un insieme e non un numero, e va **aggiornata a ogni ondata**
che aggiunge righe. È il punto: la spec (§6.4) fa della sonda il criterio di
accettazione — a ondata 7 l'insieme deve essere il registro intero — e un test
che dice solo `>= 4` lascerebbe passare l'ondata che aggiunge una tabella
senza svegliare il builder che dovrebbe leggerla.

Il confronto col Fermi è la misura che ha aperto il pezzo, e sta qui accanto
perché è ciò che rende il numero leggibile."""

import pytest

from domain.models import ResourceTimeConstraint, SubjectConstraint
from tests import alighieri, fermi, sonda

pytestmark = pytest.mark.django_db


# Ondate 1–4. Le quattro voci strutturali vengono dall'anagrafica; le otto
# famiglie di `ResourceTimeConstraint` dall'ondata 3, una riga per famiglia; i
# tredici tipi di `SubjectConstraint` dall'ondata 4, idem.
#
# ⚠ **L'ondata 2 non ha allargato questo insieme, ed era corretto così.**
# Partizioni, parti e raggruppamenti non hanno un builder proprio: entrano nel
# modello attraverso le **chiavi di occupazione** (ADR-017), cioè facendo
# lavorare di più `structural:occupation` — **1440 → 3440** constraint — e
# attraverso `structural:coverage`, che un builder non ce l'ha per costruzione
# (il solver non crea né distrugge attività). Un cricchetto che contasse i
# constraint invece dell'insieme direbbe «cresciuto» e non direbbe niente di
# vero. L'ondata 3 lo allarga di **otto** e l'ondata 4 di **tredici**, che è
# il salto più grande che una sola ondata possa fare.
#
# ⚠ **I due che mancano sono nominati, non dimenticati**:
# `structural:unavailability` (il banco non ha ancora una riga di
# indisponibilità) e `structural:didactic_weight` (i quattro tetti di
# `InstituteSettings` sono tutti `None`, com'è fedele a EDT). Sono l'ondata 5,
# e 27 su 27 resta il criterio di accettazione dell'ondata 7.
T = ResourceTimeConstraint.Type
S = SubjectConstraint.Type
ATTIVI = {
    "structural:occupation",
    "structural:room_pool",
    "structural:site_transition",   # 🔑 il Fermi ha zero `Site`: qui è muto
    "structural:grid",              # blocchi lunghi + intervallo mensa
    T.MIN_DISTRIBUTION, T.MAX_HOURS, T.MAX_PRESENCE, T.ARRIVAL_DEPARTURE,
    T.FREE_GUARANTEED, T.MAX_HALF_DAYS, T.MAX_SITE_CHANGES, T.MAX_GAP_HOURS,
    S.SAME_HALF_DAY_INCOMPATIBLE, S.SAME_DAY_INCOMPATIBLE,
    S.TWO_DAYS_INCOMPATIBLE, S.FORBIDDEN_SEQUENCE, S.MAX_HOURS_HALF_DAY,
    S.MAX_HOURS_DAY, S.WEEKLY_ORDER, S.IMPOSED_SUCCESSION, S.HALF_DAY_GAP,
    S.PARTS_BEFORE_CLASS, S.PARTS_AFTER_CLASS,
    S.PARTS_BEFORE_OR_AFTER_CLASS_H, S.PARTS_BEFORE_OR_AFTER_CLASS_AB,
}


def test_l_alighieri_esercita_i_builder_dichiarati():
    env = alighieri.build()
    assert sonda.attivi(env["schedule"]) == ATTIVI


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
