"""L'ondata 6 del banco, seconda metà: l'ora quindicinale e le firme di
settimana.

Il dataset ha avuto **una firma sola** per cinque ondate: ogni maschera era
l'anno intero, `week_signatures` restituiva una riga e metà del motore non
aveva mai avuto un dato su cui mostrarsi. L'ondata 6 mette la seconda ora di
scienze del 5B a settimane alterne — una in laboratorio col tecnico, una di
teoria in aula — e da lì escono tre cose diverse:

- 🔑 **una forma di erogazione che non costa un'ora.** Lo sdoppiamento delle
  ondate 2 e 4 fa ripetere l'ora al docente; la quindicinale no, perché in
  ogni settimana ne è attiva esattamente una. Due attività, un'ora.
- 🔑 **la sola cosa che l'occupazione sa fare e nessuno le aveva chiesto.**
  È l'unico builder che distingue le firme, e le due metà — che stanno sulla
  stessa classe, quindi condividono la chiave — possono stare **nella stessa
  cella**. È poi come una scuola scrive davvero un'ora quindicinale: «scienze
  al martedì alla terza», e cambia solo cosa ci si fa.
- ⚠ **un debito che diventa un test**: i criteri di qualità le firme non le
  distinguono, e con due firme le due letture della stessa quantità divergono.
  Vedi `test_l7_...` in coda, e `docs/todo.md`."""

import pytest

from domain import weeks
from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.models import (
    Activity, Placement, QualityCriterion, ResourceTimeConstraint,
    SchoolClass, Teacher,
)
from domain.solver.context import SolverContext
from domain.solver.model import solve
from domain.solver import criteria  # noqa: F401 — registra i criteri
from domain.solver.quality import _valori_di_base
from tests import alighieri

pytestmark = pytest.mark.django_db


def _quindicinali():
    """Le due metà, nell'ordine (laboratorio, teoria) — cioè per maschera.

    ⚠ Si riconoscono dalla **maschera**, non da un allineamento: allinearle
    direbbe che sono simultanee, e non lo sono mai."""
    intero = weeks.full_mask(alighieri.WEEKS_IN_YEAR)
    righe = list(Activity.objects.filter(classes__name="5B",
                                         subject__code="SCI")
                 .exclude(week_mask=intero).order_by("pk"))
    assert len(righe) == 2, righe
    return sorted(righe, key=lambda a: not weeks.week_in_mask(a.week_mask, 0))


def _settimanale():
    """L'ora di scienze del 5B che c'è **tutte** le settimane."""
    righe = list(Activity.objects.filter(
        classes__name="5B", subject__code="SCI",
        week_mask=weeks.full_mask(alighieri.WEEKS_IN_YEAR)))
    assert len(righe) == 1, righe
    return righe[0]


def test_le_due_firme_di_settimana(db):
    """Due firme, 17 e 16 settimane, e le maschere sono **complementari**.

    ⚠ 17 e 16 su 33, non 16,5: un anno con un numero dispari di settimane dà a
    una delle due metà una volta in più. È un fatto del calendario, non un
    difetto — e va scritto, perché è il genere di asimmetria che dopo si
    scambia per un errore."""
    env = alighieri.build()
    firme = week_signatures(env["schedule"])
    assert sorted(len(w) for _r, w in firme) == [16, 17]

    lab, teoria = _quindicinali()
    intero = weeks.full_mask(alighieri.WEEKS_IN_YEAR)
    assert lab.week_mask & teoria.week_mask == 0
    assert lab.week_mask | teoria.week_mask == intero
    # E le altre 341 sono tutte annuali: la seconda firma la porta una riga
    # sola, ed è la riga che l'ondata 6 ha aggiunto apposta.
    assert Activity.objects.exclude(week_mask=intero).count() == 2


def test_la_quindicinale_e_la_sola_forma_che_non_costa_un_ora(db):
    """🔑 **Due attività, un'ora.**

    Il confronto è con lo sdoppiamento dell'ondata 2: là il docente ripete
    l'ora per la seconda metà classe, e le ore della cattedra salgono (N01 da
    17 a 19). Qui no — le due metà non coesistono mai, quindi la cattedra e il
    monte ore dell'alunno restano quelli di prima. È la differenza fra
    *sdoppiare* e *alternare*, e nel nostro modello è tutta nella maschera."""
    alighieri.build()
    urbani = Teacher.objects.get(abbreviation="URBAN")
    assert urbani.effective_weekly_minutes == 10 * 60
    riga = urbani.assignments.get(school_class__name="5B")
    assert riga.weekly_minutes == 2 * 60

    per_settimana = {
        sum(a.duration_minutes
            for a in Activity.objects.filter(classes__name="5B",
                                             subject__code="SCI")
            if weeks.week_in_mask(a.week_mask, w))
        for w in range(alighieri.WEEKS_IN_YEAR)
    }
    assert per_settimana == {2 * 60}


def test_solo_la_meta_di_laboratorio_chiede_il_laboratorio_e_il_tecnico(db):
    """L'ora di teoria non prenota niente, ed è ciò che rende la quindicinale
    una *scelta* invece di una scrittura diversa della stessa ora: il
    laboratorio conteso lo si spende una settimana su due.

    ⚠ Le richieste d'aula del dataset restano **73**, non 74: un'attività in
    più che non chiede aula non è una richiesta in più."""
    env = alighieri.build()
    lab, teoria = _quindicinali()
    assert {r.name for r in lab.rooms.all()} == {"LAB-SCI", "LAB-INF"}
    assert list(teoria.rooms.all()) == []
    assert [s.name for s in lab.staff.all()] == [alighieri.TECNICO[0]]
    assert list(teoria.staff.all()) == []
    assert Activity.objects.filter(staff__isnull=False).distinct().count() == 8
    assert Activity.objects.filter(rooms__isnull=False).distinct().count() == 73


def test_le_due_meta_possono_stare_nella_stessa_cella(db):
    """🔑 **Il testimone puntato dell'occupazione per firma.**

    Le due metà stanno sulla stessa classe, quindi condividono la chiave di
    occupazione: se il modello contasse le attività ignorando le settimane,
    imporle sulla stessa cella sarebbe `INFEASIBLE`. È `OPTIMAL`, e l'unica
    ragione è che le maschere non si intersecano — la proprietà che
    `OccupationBuilder` dichiara nel suo docstring (*«è l'unico builder che
    distingue le firme di settimana»*) e che nessun dataset gli aveva mai
    chiesto di esercitare."""
    env = alighieri.build()
    lab, teoria = _quindicinali()
    soluzione = solve(env["schedule"], workers=8, time_limit=120,
                      pinned={lab.pk: (1, 2), teoria.pk: (1, 2)})
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["pin_fuori_dominio"] == ()


def test_e_col_ora_settimanale_no(db):
    """Il ramo di controllo: la stessa cella con l'ora **settimanale** non si
    può, e il divieto è l'occupazione della classe.

    ⚠ Senza questo ramo il test qui sopra resterebbe verde anche se
    l'occupazione della classe non fosse postata affatto."""
    env = alighieri.build()
    lab, _teoria = _quindicinali()
    soluzione = solve(env["schedule"], workers=8, time_limit=120,
                      allow_unplaced=False,
                      pinned={lab.pk: (1, 2), _settimanale().pk: (1, 2)})
    assert soluzione.status == "INFEASIBLE", soluzione.stats


# ---------------------------------------------------------------------------
# L7 — il debito che l'ondata 6 rende misurabile
# ---------------------------------------------------------------------------

def _testimone_dei_buchi(env):
    """Il 5B al lunedì: settimanale, laboratorio, teoria, settimanale sulle
    prime quattro fasce — con le due metà in **fasce diverse**.

    | Settimana | Fasce occupate | Buchi |
    |---|---|---|
    | pari | 0, 1, 3 | 1 (la fascia 2) |
    | dispari | 0, 2, 3 | 1 (la fascia 1) |
    | unione | 0, 1, 2, 3 | **0** |

    Tutte le attività diventano immobili: quelle mai piazzate escono dal
    contesto del solver (`SolverContext.build`), e restano solo le quattro che
    interessano — così `_valori_di_base` ha un orario di partenza completo e
    il criterio si calcola su di esso."""
    Activity.objects.update(immobility=Activity.Immobility.FIXED)
    lab, teoria = _quindicinali()
    italiano = list(Activity.objects.filter(classes__name="5B",
                                            subject__code="ITA")
                    .order_by("pk"))[:2]
    for attivita, slot in ((italiano[0], 0), (lab, 1), (teoria, 2),
                           (italiano[1], 3)):
        Placement.objects.create(schedule=env["schedule"], activity=attivita,
                                 day=0, start_slot=slot)
    ResourceTimeConstraint.objects.create(
        resource=SchoolClass.objects.get(name="5B"),
        type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})


def test_l7_il_criterio_i_buchi_li_conta_ed_e_il_contro_testimone(db):
    """Il ramo di controllo, e senza di esso il test qui sotto varrebbe zero.

    Stesso orario, ma con la metà di teoria **non piazzata**: l'unione diventa
    0-1-3 e il buco della fascia 2 c'è anche lì. Il criterio dice **180**, e
    questo prova che i minuti mancanti nell'altro testimone sono la firma di
    settimana, non un criterio spento o una chiave che non c'è.

    ⚠ 180 e non 60 perché le chiavi sono **tre**: la classe 5B e le sue due
    parti IRC/alternativa, che `chiavi_di` conta per conto proprio — *«il
    contatore `A.iso.` di EDT è dichiarato per docente/classe/gruppo»*. Un
    buco nell'ora di un'unità-studente è un buco per ognuna delle unità che
    stanno in quell'ora."""
    env = alighieri.build()
    _testimone_dei_buchi(env)
    _, teoria = _quindicinali()
    env["schedule"].placements.filter(activity=teoria).delete()
    ctx = SolverContext.build(env["schedule"])
    riga = QualityCriterion(kind=QualityCriterion.Kind.GAPS,
                            population=QualityCriterion.Population.CLASSES,
                            rank=1)
    assert _valori_di_base(ctx, [riga]) == {"gaps_classes": 180}


def test_l7_il_checker_vede_il_buco_in_ogni_settimana(db):
    """La verità: **ogni** settimana dell'anno ha un'ora di buco per il 5B.

    `check_schedule` valuta ogni firma per conto suo, quindi il buco della
    settimana pari e quello della dispari danno lo stesso finding, con le
    stesse quantità, e le settimane si fondono: trentatré su trentatré."""
    env = alighieri.build()
    _testimone_dei_buchi(env)
    buchi = [f for f in check_schedule(env["schedule"])
             if f.code == "max_gap" and f.severity == Severity.HARD]
    assert len(buchi) == 1, buchi
    assert buchi[0].quantities["gap_minutes"] == 60
    assert len(buchi[0].weeks) == alighieri.WEEKS_IN_YEAR


def test_l7_il_criterio_gaps_dice_zero_ed_e_il_difetto(db):
    """⚠ **L7: i criteri di qualità ignorano le firme di settimana.**

    Sullo stesso orario, la stessa quantità — «la durata totale dei buchi»,
    che il criterio calcola *senza tetto* e il D.T.B. *col tetto*, e che il
    docstring di `criteria.buchi` dichiara letteralmente essere la stessa —
    vale **60 minuti in ogni settimana** per il checker e **zero** per il
    criterio. Il criterio somma le occupazioni sull'**unione** delle
    settimane, e nell'unione le fasce 0-1-2-3 sono contigue.

    🔑 E non è un difetto nuovo: è **lo stesso** che `MaxGapBuilder` aveva
    fino al 2026-08-24, descritto per esteso nel docstring di
    `Vocabulary.covered` — *«un'occupazione che cade dentro il buco ma viene
    da un'altra firma alza il conteggio senza spostare prima/ultima occupata,
    e chiude nel modello unione un buco che, settimana per settimana, resta
    aperto»*. Il builder passa `signature`; i criteri no.

    ⚠ `quality.py` lo dichiara come approssimazione, con l'argomento che un
    obiettivo approssimato *ordina male orari tutti legali* e non ne ammette
    uno illegale. L'argomento regge; ciò che non reggeva era «nessuno dei due
    dataset lo esercita», e da oggi non è più vero. Il debito è **L7** in
    `docs/todo.md`, non riparato qui (spec §8): questo test diventerà rosso il
    giorno in cui si chiude, ed è il modo giusto di chiuderlo."""
    env = alighieri.build()
    _testimone_dei_buchi(env)
    ctx = SolverContext.build(env["schedule"])
    assert set(ctx.activities) == {p.activity_id for p in
                                   env["schedule"].placements.all()}
    riga = QualityCriterion(kind=QualityCriterion.Kind.GAPS,
                            population=QualityCriterion.Population.CLASSES,
                            rank=1)
    valori = _valori_di_base(ctx, [riga])
    assert valori == {"gaps_classes": 0}   # la verità è 180, ogni settimana
