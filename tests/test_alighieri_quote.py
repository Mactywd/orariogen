"""L'ondata 6 del banco, prima metà: gli alleggerimenti a quota.

Un vincolo alleggerito **non diventa soft**. L'istruzione del prodotto è
letterale — *«Sbloccate i vincoli da alleggerire e selezionateli per
quantificare il margine di manovra concesso al calcolo»* — e nel nostro
modello è un numero massimo di violazioni per (famiglia, risorsa), in due
forme: il **margine**, che allarga il tetto di una quantità dichiarata, e la
**deroga**, che non considera il vincolo per quell'occorrenza.

Tutto questo esiste dal 2026-08-26 e **nessun dataset l'aveva mai eseguito**:
né il Fermi né l'Alighieri fino a qui hanno una riga `RelaxationQuota`.

🔑 **La forma della prova è quella dell'ondata 4, rovesciata.** Là si imponeva
la configurazione vietata e si pretendeva `INFEASIBLE`; qui si mette il
dataset in tensione e si pretende che la quota lo rimetta in piedi — e che
**senza** la quota non ci stia. Due verdetti sul modello, non su quale ottimo
la ricerca abbia scelto.

⚠ **E le quote del dataset non sono consumate dal dataset**, il che sembra una
rinuncia e non lo è. `test_le_otto_forme_dichiarate` (ondata 3) pretende che
l'orario di base non porti **nessun** finding `HARD` oltre alle aule non
assegnate; una quota consumata *è* una violazione nominata, perché la quota
autorizza il solver a produrla e non la nasconde (`relaxation.py`). Una quota
consumata dal dataset spegnerebbe quel test. Quindi le righe stanno nel
dataset perché i builder le leggano — e la misura dice che le leggono: undici
variabili e quattro constraint in più sul modello di base — e la tensione la
mette il testimone.

🔑 **La terza prova è sulla taglia, non sulla presenza**, ed è quella che il
docstring di `RelaxationQuota` chiede per nome: *«"la quota è collegata" passa
anche se il margine vale dieci volte quello dichiarato»*. Sul cappellano il
**numero** conta: dodici ore non stanno in 4 + 4 fasce né in 4 + 7, stanno in
7 + 7. Un supplemento non basta, due sì."""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import (
    RelaxationQuota, ResourceTimeConstraint, ResourceUnavailability, Teacher,
)
from domain.solver.model import apply, solve
from tests import alighieri

pytestmark = pytest.mark.django_db


def _quota(famiglia, abbr):
    return RelaxationQuota.objects.get(
        family=famiglia, resource=Teacher.objects.get(abbreviation=abbr))


def _tensione_donati():
    """R02 viene **due giorni**: dodici ore non stanno in due mezze giornate.

    Con il `MG` — mai mattina *e* pomeriggio nello stesso giorno — due giornate
    danno al più due mattine, cioè dieci fasce per dodici ore. Derogare una
    volta sola apre un pomeriggio: 5 + 5 + 3 = 13, e ci stanno."""
    ResourceTimeConstraint.objects.create(
        resource=Teacher.objects.get(abbreviation="DONAT"),
        type=ResourceTimeConstraint.Type.MAX_PRESENCE, params={"days": 2})


def _tensione_colombo(minuti=240):
    """Il cappellano viene lunedì e martedì, e la presenza scende a **quattro**
    fasce.

    Dodici ore in due giornate da quattro fasce sono otto: non ci stanno. E non
    basta allargarne una sola — 4 + 7 fa undici, e le ore sono dodici. Con due
    supplementi le giornate valgono 7 + 7 = 14, e tredici bastano: dodici ore
    più la fascia libera che il cambio di sede si porta dietro
    (`site_transition_slots`).

    🔑 **Le due giornate si dichiarano col rosso, non col `days`**, e la
    differenza è misurata. Con `max_presence {days: 2}` i tetti giornalieri
    restano postati su tutte e cinque le giornate, e il legame «solo due sono
    attive» passa da booleani che il rilassamento lineare non lega ai minuti:
    il caso di mezzo restava `UNKNOWN` a tre minuti. Con le tre giornate rese
    **indisponibili** il pre-filtro toglie le celle, le giornate diventano due
    davvero e il conto è immediato. È la stessa affermazione detta col
    meccanismo che il modello sa propagare — e che l'ondata 5 ha messo nel
    banco proprio per questo."""
    colombo = Teacher.objects.get(abbreviation="COLOM")
    riga = ResourceTimeConstraint.objects.get(
        resource=colombo, type=ResourceTimeConstraint.Type.MAX_PRESENCE)
    riga.params = {"days": 2, "max_minutes": minuti}
    riga.save()
    for day in (2, 3, 4):
        for slot in range(8):
            ResourceUnavailability.objects.create(
                resource=colombo, day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)


def test_le_due_righe_ci_sono_e_sono_le_due_forme():
    """Due quote, e sono i **due** tipi di riga della finestra
    `Alleggerimenti`: una col margine e una senza.

    ⚠ L'assenza di `margine` non è un campo dimenticato: le famiglie che si
    **derogano** non hanno un supplemento da quantificare — «Non considerare
    le incompatibilità … una sola volta al giorno» ha il *quante volte* e non
    il *quanto*."""
    alighieri.build()
    righe = RelaxationQuota.objects.all()
    assert righe.count() == 2
    deroga = _quota(RelaxationQuota.Family.HALF_DAYS, "DONAT")
    assert deroga.params == {} and deroga.max_violations == 1
    margine = _quota(RelaxationQuota.Family.MAX_PRESENCE, "COLOM")
    assert margine.params == {"margine": 180} and margine.max_violations == 2


def test_il_dataset_non_le_consuma():
    """La base non cambia: nessuna violazione nuova, e le forme dell'ondata 3
    restano quelle.

    🔑 È l'invariante «quote a zero ⇒ il modello di prima» detto dall'altro
    capo: qui le quote **ci sono**, e il modello resta lo stesso perché il
    livello L3 minimizza le quote consumate insieme alle riparazioni mancate.
    Una quota che si consumasse da sola sarebbe un alleggerimento che nessuno
    ha chiesto."""
    env = alighieri.build()
    soluzione = solve(env["schedule"], workers=8)
    assert soluzione.status == "OPTIMAL"
    assert list(soluzione.unplaced) == []
    apply(soluzione, env["schedule"])
    hard = [f for f in check_schedule(env["schedule"])
            if f.severity == Severity.HARD]
    assert [f.code for f in hard] == ["room_unassigned"] * 73


def test_la_deroga_rimette_in_piedi_il_mg_di_donati():
    """La **deroga**: senza, dodici ore in due mattine non ci stanno."""
    env = alighieri.build()
    _tensione_donati()
    _quota(RelaxationQuota.Family.HALF_DAYS, "DONAT").delete()
    senza = solve(env["schedule"], workers=8, allow_unplaced=False,
                  time_limit=120)
    assert senza.status == "INFEASIBLE", senza.stats


def test_e_con_la_deroga_ci_stanno():
    """L'altra metà: con la deroga R02 fa mattina **e** pomeriggio una volta,
    e le dodici ore ci stanno. Le due metà insieme dicono che a rimettere in
    piedi il dataset è **quella riga**, non un caso della ricerca."""
    env = alighieri.build()
    _tensione_donati()
    con = solve(env["schedule"], workers=8, allow_unplaced=False, time_limit=120)
    assert con.status == "OPTIMAL", con.stats


def test_la_deroga_consumata_resta_una_violazione_nominata():
    """🔑 **La quota autorizza, non nasconde.** È il comportamento di EDT, dove
    l'orario risolto conteneva 21 attività su 984 che non rispettavano i
    vincoli e il prodotto continuava a lavorare: `check_schedule` produce il
    finding `HARD` esattamente come se la quota non ci fosse.

    ⚠ Ed è la ragione per cui le due righe del dataset **non** possono essere
    consumate dalla base: l'ondata 3 pretende che l'orario di base non porti
    finding `HARD` oltre alle aule."""
    env = alighieri.build()
    _tensione_donati()
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=120)
    assert soluzione.status == "OPTIMAL"
    apply(soluzione, env["schedule"])
    donati = Teacher.objects.get(abbreviation="DONAT")
    codici = {f.code for f in check_schedule(env["schedule"])
              if f.severity == Severity.HARD and donati.pk in f.resources}
    assert "only_half_day" in codici, codici


@pytest.mark.parametrize("quante,atteso", [(0, "INFEASIBLE"),
                                           (1, "INFEASIBLE"),
                                           (2, "OPTIMAL")])
def test_il_margine_del_cappellano_e_una_questione_di_taglia(quante, atteso):
    """🔑 **Il numero della quota conta, non la sua presenza.**

    Con la presenza a quattro fasce il cappellano non ci sta — otto fasce per
    dodici ore; con **un** supplemento neppure, perché 4 + 7 fa undici; con
    **due** le giornate diventano 7 + 7 = 14, e tredici bastano.

    🔑 E i tre verdetti sono tutti argomenti di **conteggio sulle ore**, non
    sul viaggio — il che è una correzione della prima taratura e vale la pena
    scriverla. Il disegno iniziale metteva il tetto a cinque fasce e faceva
    dire al caso di mezzo *5 + 7 = 12 fasce per dodici ore più la fascia di
    viaggio*: vero, e il solver non ci arrivava in tre minuti (`UNKNOWN`
    due volte, a 180 s e a 120 s). Con quattro fasce e un margine di tre ore
    l'aritmetica sta tutta sulle ore, e i tre casi chiudono in 37 s in tutto.
    ⚠ Un test che misura la potenza del propagatore invece di una proprietà
    del modello è un test che un giorno diventa rosso da solo.

    ⚠ È la mutazione che il docstring di `RelaxationQuota` chiede per nome —
    una quota «collegata» che passasse anche a margine decuplicato non
    proverebbe niente. Qui la riga di mezzo è quella che porta l'informazione:
    è l'unica che distingue «la quota c'è» da «la quota è quella giusta»."""
    env = alighieri.build()
    _tensione_colombo()
    riga = _quota(RelaxationQuota.Family.MAX_PRESENCE, "COLOM")
    if quante == 0:
        riga.delete()
    else:
        riga.max_violations = quante
        riga.save()
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=120)
    assert soluzione.status == atteso, soluzione.stats
