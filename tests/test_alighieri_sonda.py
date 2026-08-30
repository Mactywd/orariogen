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
from domain.solver.registry import BUILDERS, all_builders
from tests import alighieri, fermi, sonda

pytestmark = pytest.mark.django_db


# Ondate 1–5, e con l'ondata 5 l'insieme **è il registro intero**. Le quattro
# voci strutturali vengono dall'anagrafica; le otto famiglie di
# `ResourceTimeConstraint` dall'ondata 3, una riga per famiglia; i tredici
# tipi di `SubjectConstraint` dall'ondata 4, idem; e gli ultimi due
# dall'ondata 5 — le indisponibilità e i tetti di peso didattico.
#
# 🔑 **Il registro intero è il criterio di accettazione della spec (§6), ed è
# raggiunto qui invece che all'ondata 7.** Erano 27 su 27 all'ondata 5; sono 28
# su 28 da L5, che al registro ha aggiunto `structural:alignment`. Non chiude il pezzo: la sonda dice che ogni
# builder *fa qualcosa*, non che ciò che fa morda — quello lo dicono la tacca
# e il testimone puntato, famiglia per famiglia. Ma da adesso in poi il
# cricchetto non deve più salire: deve **restare fermo**, e un'ondata che lo
# facesse scendere sarebbe una regressione.
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
# ⚠ **I due ultimi arrivati non erano dimenticati, erano nominati**:
# `structural:unavailability` (il banco non aveva una riga di indisponibilità)
# e `structural:didactic_weight` (i quattro tetti di `InstituteSettings`
# erano tutti `None`, com'è fedele a EDT — il Fermi li ha ancora così). Sono
# le sei righe e i tre tetti dell'ondata 5.
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
    "structural:unavailability",    # ondata 5: sei righe, tre livelli
    "structural:didactic_weight",   # ondata 5: i tre tetti d'istituto
    "structural:alignment",         # L5: i sedici allineamenti
}


def test_l_alighieri_esercita_i_builder_dichiarati():
    env = alighieri.build()
    assert sonda.attivi(env["schedule"]) == ATTIVI


def test_e_l_insieme_e_il_registro_intero():
    """Il criterio di accettazione di §6, scritto come identità e non come
    numero: se un builder nuovo entrasse nel registro senza una riga che lo
    sveglia, questo test lo direbbe il giorno stesso.

    ⚠ `all_builders()` prima di leggere `BUILDERS`: il registro si popola
    all'import, che è pigro — la stessa trappola documentata in
    `tests/sonda.py`."""
    all_builders()
    assert ATTIVI == set(BUILDERS)


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
