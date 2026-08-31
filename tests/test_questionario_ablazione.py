"""L'**ablazione**: `Questione.tocca` è misurato, non dichiarato.

Si tolgono dall'Alighieri le righe di una famiglia e si ripassa la sonda: i
builder che calano sono quelli che quella risposta fa lavorare. È lo stesso
mestiere del cricchetto di `tests/sonda.py`, e nasce dallo stesso inciampo —
un elenco scritto a mano che nessuno rimisura invecchia senza dirlo, e
`CLAUDE.md` ne portava uno per settimane.

⚠ **Calare, non spegnersi.** Il criterio più stretto («il builder diventa
inerte») perderebbe i due casi in cui una famiglia fa lavorare di più un
builder che *resta* attivo: i materiali attraverso le chiavi di occupazione
(ADR-017) e i pesi attraverso i tetti. Sono lo stesso fenomeno dell'ondata 2
del banco, dove partizioni e parti non hanno un builder proprio e si vedono
solo come `structural:occupation` che cresce.

⚠ **E si misura il verso.** Togliere le indisponibilità fa **crescere** il
modello — 13 645 → 13 861 constraint — perché una cella potata non genera
letterali e quindi nemmeno i constraint che li nominerebbero. Potare costa meno
che vincolare, e un criterio che contasse le variazioni in valore assoluto
attribuirebbe alle indisponibilità builder che quelle righe non alimentano.
"""

import pytest
from django.db import transaction

from domain import questionario as Q
from domain.models import (Activity, Break, CompetitionClass, Discipline,
                           Holiday, InstituteSettings, Material, Period,
                           QualityCriterion, RelaxationQuota, Resource,
                           ResourceTimeConstraint, ResourceUnavailability,
                           Room, Site, StaffMember, Subject, SubjectConstraint)
from tests import alighieri, sonda

pytestmark = pytest.mark.django_db


class _Rollback(Exception):
    """Il modo per misurare dieci ablazioni sullo stesso dataset senza
    ricostruirlo dieci volte: ognuna vive dentro un `atomic` che non viene mai
    confermato."""


def _senza(azione, schedule):
    try:
        with transaction.atomic():
            azione()
            raise _Rollback(sonda.misura(schedule))
    except _Rollback as e:
        return e.args[0]


def _via_aule():
    # ⚠ Togliere le aule toglie anche le loro indisponibilità (CASCADE sulla
    # risorsa), ed è giusto che `tocca` lo dica: chi non risponde «quali aule
    # ho» perde tutto ciò che alle aule sta appeso, non solo l'assegnazione.
    for a in Activity.objects.all():
        a.rooms.clear()
    Room.objects.all().delete()


def _via_sedi():
    Resource.objects.update(site=None)
    Activity.objects.update(site=None)
    Site.objects.all().delete()


def _via_discipline():
    # La disciplina non è annullabile (`Subject.discipline` è NOT NULL): il
    # meglio che si può togliere è il *contenuto* della risposta, cioè la
    # distinzione fra discipline e le classi di concorso. È esattamente ciò
    # che `bootstrap.applica` lascia dietro di sé.
    nd = Discipline.objects.create(code="ZZND", name="Da assegnare")
    Subject.objects.update(discipline=nd)
    for d in Discipline.objects.all():
        d.competition_classes.clear()
    Discipline.objects.exclude(pk=nd.pk).delete()
    CompetitionClass.objects.all().delete()


def _via_pesi():
    Subject.objects.update(didactic_weight=1)
    InstituteSettings.objects.update(
        max_weight_morning=None, max_weight_afternoon=None,
        max_weight_day=None, max_weight_week=None)


#: Come si toglie la risposta a una domanda. ⚠ `partizioni` non c'è, e non è
#: una dimenticanza: le cattedre puntano alle parti, quindi cancellarle
#: cancellerebbe metà del dataset e misurerebbe quella. È l'unica voce il cui
#: `tocca` resta dichiarato — ed è `()`, come l'ondata 2 del banco ha già
#: misurato per altra via.
ABLAZIONI = {
    "sedi": _via_sedi,
    "aule": _via_aule,
    "materiali_e_personale": lambda: (Material.objects.all().delete(),
                                      StaffMember.objects.all().delete()),
    "calendario": lambda: (Holiday.objects.all().delete(),
                           Break.objects.all().delete(),
                           Period.objects.all().delete()),
    "indisponibilita": lambda: ResourceUnavailability.objects.all().delete(),
    "vincoli_orari": lambda: ResourceTimeConstraint.objects.all().delete(),
    "vincoli_materia": lambda: SubjectConstraint.objects.all().delete(),
    "peso_didattico": _via_pesi,
    "criteri_di_qualita": lambda: QualityCriterion.objects.all().delete(),
    "quote": lambda: RelaxationQuota.objects.all().delete(),
    "discipline": _via_discipline,
}


def _calati(base, dopo):
    return {str(k) for k in base
            if dopo[k]["celle"] < base[k]["celle"]
            or dopo[k]["constraint"] < base[k]["constraint"]}


def test_ogni_tocca_e_quello_misurato():
    schedule = alighieri.build()["schedule"]
    base = sonda.misura(schedule)
    per_chiave = {q.chiave: q for q in Q.questionario()}
    for chiave, azione in ABLAZIONI.items():
        atteso = set(per_chiave[chiave].tocca)
        assert _calati(base, _senza(azione, schedule)) == atteso, chiave


def test_le_famiglie_ablabili_sono_tutte_tranne_una():
    """Il ramo di controllo dell'elenco: se domani il catalogo cresce di una
    voce senza ablazione, questo test lo dice invece di lasciarla non
    misurata."""
    assert set(ABLAZIONI) | {"partizioni"} == {v["chiave"] for v in Q._CATALOGO}


def test_il_punto_cieco_della_sonda_e_dichiarato():
    """⚠ Quote e criteri di qualità misurano **zero**, e zero lì non vuol dire
    inerte: vivono sopra il modello duro — sono livelli della catena
    lessicografica, costruiti uno alla volta — e `sonda.misura` guarda
    `build_model`. Le due voci lo dichiarano, e sono le sole a poterlo fare."""
    per_chiave = {q.chiave: q for q in Q.questionario()}
    cieche = {k for k, q in per_chiave.items() if q.oltre_il_modello_duro}
    assert cieche == {"quote", "criteri_di_qualita"}
    for k in cieche:
        assert per_chiave[k].tocca == ()


def test_la_disciplina_non_tocca_il_calcolo():
    """La misura che declassa una domanda a `FUORI_CALCOLO`: zero builder, zero
    celle, zero constraint. È l'unica del catalogo, e senza la misura sarebbe
    rimasta nell'elenco del gradino 3 accanto alle altre."""
    schedule = alighieri.build()["schedule"]
    base = sonda.misura(schedule)
    dopo = _senza(_via_discipline, schedule)
    assert dopo == base
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert per_chiave["discipline"].effetto == Q.FUORI_CALCOLO
