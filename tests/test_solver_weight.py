"""Il peso didattico: il vincolo di carico cognitivo
(`domain/solver/builders/weight.py`). In una base reale del prodotto i quattro
tetti d'istituto sono tutti a «nessuno», quindi questo builder di norma non
posta nulla — i test qui sotto li accendono apposta.

⚠ Niente `test_peso_sul_banco` qui (Ruling 16, ennesima applicazione):
`tests/solver_harness.py` registra `_derive_weight` sotto
`"structural:didactic_weight"`, e `tests/test_solver_witness.py::test_famiglia`
gia' parametrizza su `sorted(DERIVERS) x [1..5]` — i cinque seed della
famiglia esistono in automatico appena il derivatore e' registrato. Scriverli
anche qui sarebbe un duplicato esatto, come per i derivatori dei Task 7-15.

⚠ La forma dei test che affermano la **presenza** del vincolo e' quella
avversaria (Ruling 85): `build_model` + `model.Add(x[...] == 1)` che **forza**
la violazione, e si attende INFEASIBLE. La forma «risolvi e guarda la
soluzione» su questo branch e' gia' stata misurata inutile — passava anche col
builder reso no-op, perche' CP-SAT distribuisce comunque.

⚠ Il tetto **settimanale** (istituto e classe) e' un caso a parte: il peso
settimanale di un'unita' non dipende dal piazzamento, perche' `AddExactlyOne`
obbliga a piazzare tutte le attivita'. Quindi il suo vincolo e' vero sempre o
falso sempre, e la forma avversaria e' semplicemente «il modello e'
INFEASIBLE». E' anche il motivo per cui il banco a testimone non puo'
esercitarlo: vedi la docstring di `_derive_weight`.

⚠ **E per la stessa ragione ADR-018 li' non si tratta col clamp**: un secchio
inevadibile con residuo zero non e' inagibile, e' contraddittorio. I due test
in fondo al modulo tengono ferme le due meta' — le congelate da sole non
devono bloccare il modello, ma il tetto dev'essere ancora capace di mordere
quando il colpevole non e' il passato."""
import pytest
from ortools.sat.python import cp_model

from domain.models import (
    Activity, ClassPart, ClassPartition, InstituteSettings, SchoolClass,
    StudyPlan,
)
from domain.solver.model import build_model
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _status(model):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    return solver.Solve(model)


def _feasible(model):
    return _status(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def _infeasible(model):
    return _status(model) == cp_model.INFEASIBLE


def _pesa(env, quanto):
    env["subject"].didactic_weight = quanto
    env["subject"].save()


def _constraints(model):
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return len(proto.constraints)


def test_il_tetto_giornaliero_morde():
    """Tre attivita' di peso 2 forzate nello stesso giorno con
    `max_weight_day = 4`: 6 > 4, il modello dev'essere INFEASIBLE. Due sole
    forzate (la terza libera di andare altrove) devono invece stare in piedi —
    altrimenti l'INFEASIBLE non direbbe nulla sul tetto.

    Verificato per mutazione: con `DidacticWeightBuilder.build` reso no-op il
    primo modello risponde FEASIBLE."""
    env = mini_school()
    _pesa(env, 2)
    atti = [make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]]) for _ in range(3)]
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": 4})

    model, ctx = build_model(env["schedule"])
    for i, a in enumerate(atti):
        model.Add(ctx.x[(a.id, 0, i)] == 1)
    assert _infeasible(model)

    model2, ctx2 = build_model(env["schedule"])
    for i, a in enumerate(atti[:2]):
        model2.Add(ctx2.x[(a.id, 0, i)] == 1)
    assert _feasible(model2)


def test_mattina_e_pomeriggio_sono_secchi_distinti_e_non_invertiti():
    """`mini_school` ha `morning_end_slot = 4` su 6 fasce: 0-3 mattina, 4-5
    pomeriggio. Con `max_weight_morning = 4` e `max_weight_afternoon = 2`, due
    attivita' di peso 2 stanno nel mattino (4 <= 4) e non nel pomeriggio
    (4 > 2). Il tetto giornaliero resta spento, cosi' l'unica cosa che
    discrimina fra i due casi e' la meta' giornata.

    Le due direzioni sono asserite insieme apposta: scambiando i due tetti nel
    builder (`meta == 0` → pomeriggio) il primo caso diventa INFEASIBLE e il
    secondo FEASIBLE, quindi la mutazione «verso invertito» e' catturata.
    Verificato per mutazione, in entrambe le forme (no-op e verso
    invertito)."""
    env = mini_school()
    _pesa(env, 2)
    a, b = [make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]]) for _ in range(2)]
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_morning": 4, "max_weight_afternoon": 2})

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 1)] == 1)
    assert _feasible(model), "due pesi da 2 stanno in un mattino da 4"

    model2, ctx2 = build_model(env["schedule"])
    model2.Add(ctx2.x[(a.id, 0, 4)] == 1)
    model2.Add(ctx2.x[(b.id, 0, 5)] == 1)
    assert _infeasible(model2), "due pesi da 2 non stanno in un pomeriggio da 2"


def test_il_tetto_settimanale_di_istituto_morde():
    """Il peso settimanale non dipende dal piazzamento: tre attivita' di peso
    2 fanno 6 comunque le si disponga. Col tetto a 6 il modello sta in piedi,
    col tetto a 5 e' INFEASIBLE senza bisogno di forzare nulla.

    Verificato per mutazione: con `build` no-op il secondo modello risponde
    FEASIBLE."""
    env = mini_school()
    _pesa(env, 2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 6})
    assert _feasible(build_model(env["schedule"])[0])

    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 5})
    assert _infeasible(build_model(env["schedule"], allow_unplaced=False)[0])


def test_il_tetto_della_classe_prevale_su_quello_di_istituto():
    """Le due direzioni, perche' «prevale» significa entrambe:

    - classe **piu' stretta** dell'istituto (4 contro 6) → INFEASIBLE;
    - classe **piu' larga** dell'istituto (6 contro 4) → FEASIBLE.

    Verificato per mutazione: con la mutazione mirata «ignora `class_caps` e
    usa sempre `settings.max_weight_week`» i due esiti si invertono
    esattamente, quindi il ramo `class_caps` e' davvero quello che decide.
    Con `build` no-op il primo modello risponde FEASIBLE."""
    env = mini_school()
    _pesa(env, 2)
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 6})

    SchoolClass.objects.filter(pk=env["klass"].pk).update(
        max_weekly_weight_per_student=4)
    assert _infeasible(build_model(env["schedule"], allow_unplaced=False)[0])

    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 4})
    SchoolClass.objects.filter(pk=env["klass"].pk).update(
        max_weekly_weight_per_student=6)
    assert _feasible(build_model(env["schedule"])[0])


def test_il_tetto_della_classe_si_trova_passando_dalla_parte():
    """Quando la classe ha una partizione, il peso non sta piu' sulla classe:
    sta sulle **parti** (`_student_keys`). Il tetto settimanale della classe
    va quindi ritrovato risalendo `part_class[parte] → classe`.

    Due attivita' a classe intera di peso 2 pesano 4 su **ciascuna** delle due
    parti; col tetto di classe a 3 il modello dev'essere INFEASIBLE.

    Verificato per mutazione: togliendo il passaggio da `part_class`
    (`state.class_caps.get(key)`) il tetto non si trova piu' e il modello
    risponde FEASIBLE — ed e' anche il motivo per cui questo test esiste
    accanto al precedente, che sul `part_class` identita' non direbbe
    nulla."""
    env = mini_school()
    _pesa(env, 2)
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="LINGUA")
    for nome in ("1A_ING", "1A_TED"):
        ClassPart.objects.create(name=nome, partition=partizione)
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SchoolClass.objects.filter(pk=env["klass"].pk).update(
        max_weekly_weight_per_student=3)

    assert _infeasible(build_model(env["schedule"], allow_unplaced=False)[0])

    SchoolClass.objects.filter(pk=env["klass"].pk).update(
        max_weekly_weight_per_student=4)
    assert _feasible(build_model(env["schedule"])[0])


def test_le_unita_studente_non_sono_tutti_i_token():
    """Due classi diverse, **lo stesso docente**, un'attivita' di peso 2 per
    classe, `max_weight_day = 3`. Le due attivita' forzate nello stesso giorno
    devono stare in piedi: ciascuna classe porta 2 <= 3, e il docente — che il
    checker non guarda — non deve accumulare 4.

    E' un test di **assenza** (il vincolo che non c'e'), quindi non puo'
    essere rosso sotto `build()` no-op: lo difende la mutazione mirata
    «somma su tutti i token invece che su `_student_keys`», con cui il modello
    diventa INFEASIBLE. Senza questo test un builder che sommasse su tutti i
    token passerebbe l'intera suite."""
    env = mini_school()
    _pesa(env, 2)
    altro_piano = StudyPlan.objects.create(code="P2", name="Piano 2", year=1)
    altra = SchoolClass.objects.create(name="1B", study_plan=altro_piano, year=1)
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[altra])
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": 3})

    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a.id, 0, 0)] == 1)
    model.Add(ctx.x[(b.id, 0, 1)] == 1)
    assert _feasible(model), "il peso non deve sommarsi sul docente"


def test_i_tetti_spenti_non_postano_nulla():
    """Tutti i tetti a `None`: il modello dev'essere identico a quello senza
    questo builder. Si verifica sul conteggio dei constraint.

    E' un test di **assenza**: lo difende la mutazione mirata «tratta `None`
    come 0» in `posta`, con cui il conteggio a tetti spenti sale e
    l'uguaglianza cade."""
    env = mini_school()
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": None, "max_weight_morning": None,
                        "max_weight_afternoon": None, "max_weight_week": None})
    senza_peso = _constraints(build_model(env["schedule"])[0])

    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": 99})
    assert _constraints(build_model(env["schedule"])[0]) > senza_peso


def test_adr_018_un_secchio_gia_oltre_il_tetto_non_blocca_il_modello():
    """Due attivita' **congelate** di peso 2 nel giorno 0 con
    `max_weight_day = 3`: il secchio e' gia' a 4, oltre il tetto, per colpa
    del passato. ADR-018 impone che il modello resti fattibile — `residual_cap`
    clampa il residuo a zero — e che il secchio diventi inagibile per la
    libera.

    L'asserzione e' **strutturale**, non «risolvi e guarda»: si forza la
    libera in ciascuna delle sei fasce del giorno 0 e si attende INFEASIBLE
    ogni volta, mentre il modello non forzato sta in piedi.

    Verificato per mutazione: con `build` no-op tutte le forzature diventano
    FEASIBLE. Con `residual_cap` sostituito dalla sottrazione secca (nessun
    clamp: residuo -1) il modello **non forzato** diventa INFEASIBLE, che e'
    esattamente cio' che ADR-018 vieta."""
    env = mini_school()
    _pesa(env, 2)
    congelate = [
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]],
                      immobility=Activity.Immobility.FIXED)
        for _ in range(2)]
    for i, a in enumerate(congelate):
        place(env["schedule"], a, 0, i)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": 3})

    assert _feasible(build_model(env["schedule"])[0]), (
        "ADR-018: un secchio gia' in violazione non rende infattibile il "
        "modello")
    for slot in range(2, env["grid"].slots_per_day):
        model, ctx = build_model(env["schedule"])
        model.Add(ctx.x[(libera.id, 0, slot)] == 1)
        assert _infeasible(model), f"la libera non deve entrare in (0, {slot})"


def _tre_attivita_da_due(env, congelate):
    """`congelate` attivita' fissate nel giorno 0, le restanti libere: in tutto
    tre da 2 punti sulla stessa classe."""
    _pesa(env, 2)
    atti = []
    for i in range(3):
        fissa = i < congelate
        a = make_activity(
            env["subject"], teachers=[env["teacher"]], classes=[env["klass"]],
            immobility=(Activity.Immobility.FIXED if fissa
                        else Activity.Immobility.NONE))
        if fissa:
            place(env["schedule"], a, 0, i)
        atti.append(a)
    return atti


def test_adr_018_il_tetto_settimanale_gia_sforato_dal_passato_non_blocca():
    """⚠ Il caso che `residual_cap` da solo **non** copre, e che il secchio
    giornaliero non fa vedere.

    Il secchio settimanale e' **inevadibile**: contiene tutte le celle
    candidate di ogni attivita' dell'unita', quindi `AddExactlyOne` rende la
    somma dei letterali liberi una costante. Con il residuo clampato a zero il
    vincolo sarebbe `costante positiva <= 0`, cioe' falso comunque vada il
    piazzamento: pretendere che il passato venga riparato, non vietare un
    peggioramento. ADR-018 lo esclude.

    Due congelate da 2 punti (totale 4) contro un tetto settimanale di 3, piu'
    una libera: il modello dev'essere **fattibile**. Misurato prima della
    correzione: INFEASIBLE.

    Il test gemello qui sotto tiene ferma l'altra meta': saltare il vincolo
    quando a sforare e' il **totale** sarebbe spegnerlo."""
    env = mini_school()
    _tre_attivita_da_due(env, congelate=2)
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 3})

    assert _feasible(build_model(env["schedule"])[0]), (
        "ADR-018: le congelate da sole sforano il tetto settimanale, e il "
        "modello non deve diventare infattibile per colpa del passato")


def test_il_tetto_settimanale_morde_quando_il_colpevole_non_e_il_passato():
    """Le stesse tre attivita' da 2 punti e lo stesso tetto 3, ma **nessuna
    congelata**: qui il passato non c'entra, l'istanza non ha soluzione e
    INFEASIBLE e' la risposta onesta. Tacere restituirebbe un orario che
    `check_schedule` boccia con un `weight_week`.

    E' la meta' che impedisce alla correzione del test precedente di degenerare
    in «il tetto settimanale non si posta mai»: verificato per mutazione —
    saltando sempre il secchio inevadibile, questo test diventa rosso."""
    env = mini_school()
    _tre_attivita_da_due(env, congelate=0)
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 3})

    assert _infeasible(build_model(env["schedule"], allow_unplaced=False)[0])

    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_week": 6})
    assert _feasible(build_model(env["schedule"], allow_unplaced=False)[0]), (
        "col tetto a 6 le tre attivita' ci stanno: l'INFEASIBLE di sopra "
        "dev'essere il tetto, non altro")
