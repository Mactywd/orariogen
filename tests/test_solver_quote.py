"""Gli alleggerimenti a quota (`domain/solver/relaxation.py`).

Un vincolo rilassabile non diventa soft: resta hard con un numero massimo di
violazioni attribuito. Qui si prova che la quota **concede** (senza, il modello
non ci sta) e che **morde** (con quota `k`, la violazione `k+1` è vietata) —
nella forma della casa: si forza la violazione e si attende `INFEASIBLE`.

⚠ Tutti i test usano `allow_unplaced=False`. Con lo scarto ammesso la risposta
a un vincolo che non ci sta non è l'infattibilità ma la rinuncia, e la domanda
«questo alleggerimento serve a qualcosa?» diventa invisibile."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import (InstituteSettings, RelaxationQuota,
                           ResourceTimeConstraint, SubjectConstraint)
from domain.solver.model import apply, build_model, solve
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db
F = RelaxationQuota.Family


def _tre_ore_con_tetto_di_due(env):
    """Un solo giorno, tre ore per la stessa classe e un tetto giornaliero di
    due: senza alleggerimento non ci stanno."""
    for _ in range(3):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HOURS,
        params={"day_minutes": 120})


def _dimensioni(env):
    model, _ = build_model(env["schedule"], allow_unplaced=False)
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return len(proto.variables), len(proto.constraints)


def test_senza_righe_il_modello_e_quello_di_prima():
    """La proprietà che rende questo pezzo conservativo per costruzione, e che
    è un test invece di un corollario: senza righe `RelaxationQuota` non nasce
    **nessun** letterale di violazione e **nessuna** somma."""
    env = mini_school(days=1)
    _tre_ore_con_tetto_di_due(env)
    prima = _dimensioni(env)

    RelaxationQuota.objects.create(family=F.MAX_HOURS, resource=env["klass"],
                                   max_violations=1, params={"margine": 60})
    dopo = _dimensioni(env)
    assert dopo[0] == prima[0] + 1, "un letterale di violazione, e uno solo"
    assert dopo[1] == prima[1] + 1, "e la somma che gli mette il tetto"


def test_una_quota_a_zero_e_come_non_averla():
    """Il modo di scrivere «questo vincolo non si alleggerisce» senza
    cancellare la riga."""
    env = mini_school(days=1)
    _tre_ore_con_tetto_di_due(env)
    prima = _dimensioni(env)

    RelaxationQuota.objects.create(family=F.MAX_HOURS, resource=env["klass"],
                                   max_violations=0, params={"margine": 60})
    assert _dimensioni(env) == prima
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"


def test_la_quota_concede_e_il_margine_e_quello_dichiarato():
    """Con un supplemento di un'ora le tre ore ci stanno; con la stessa quota
    ma quattro ore da piazzare, no. Il margine è una quantità dichiarata, non
    un interruttore: alleggerire non spegne il vincolo."""
    env = mini_school(days=1)
    _tre_ore_con_tetto_di_due(env)
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"

    RelaxationQuota.objects.create(family=F.MAX_HOURS, resource=env["klass"],
                                   max_violations=1, params={"margine": 60})
    assert solve(env["schedule"], allow_unplaced=False,
                 workers=1).status == "OPTIMAL"

    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])   # la quarta ora
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE", (
        "il margine di un'ora ne ha concesse due: l'alleggerimento è "
        "diventato un interruttore")


def test_la_quota_morde_sul_numero_di_violazioni():
    """Due giornate che sforano, quota **una**: la seconda violazione è
    vietata. È la forma della casa — si forza la violazione e si attende
    `INFEASIBLE` — applicata alla quota invece che al vincolo."""
    env = mini_school(days=2)
    for _ in range(6):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HOURS,
        params={"day_minutes": 120})
    # sei ore, due giorni, tetto due ore al giorno: servono due supplementi
    RelaxationQuota.objects.create(family=F.MAX_HOURS, resource=env["klass"],
                                   max_violations=1, params={"margine": 60})
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"

    RelaxationQuota.objects.filter(family=F.MAX_HOURS).update(max_violations=2)
    assert solve(env["schedule"], allow_unplaced=False,
                 workers=1).status == "OPTIMAL"


def test_la_deroga_di_materia_lascia_una_violazione_nominata():
    """L'altra forma: «Non considerare le incompatibilità … una sola volta al
    giorno». Qui il vincolo non si allarga, non si considera.

    ⚠ E la violazione **resta nominata**: `check_schedule` produce il finding
    `HARD` della famiglia derogata, esattamente uno. È il comportamento di EDT
    — l'orario risolto della base di esempio conteneva 21 attività su 984 che
    non rispettavano i vincoli — e la ragione per cui la quota non è un modo
    di nascondere la violazione, ma di autorizzarla in numero limitato."""
    env = mini_school(days=1, slots=2)
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"

    RelaxationQuota.objects.create(family=F.SUBJECT_CONSTRAINT,
                                   resource=env["klass"], max_violations=1)
    soluzione = solve(env["schedule"], allow_unplaced=False, workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    apply(soluzione, env["schedule"])
    codici = [f.code for f in check_schedule(env["schedule"])]
    assert codici == ["subject_same_day"], codici


def test_il_tetto_globale_per_risorsa_morde():
    """«Numero massimo di vincoli da alleggerire per risorsa»: due famiglie
    alleggerite sulla stessa classe, una violazione ciascuna concessa dalle
    quote di famiglia, ma il tetto d'istituto ne ammette **una sola** in
    tutto."""
    env = mini_school(days=1, slots=2)
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HOURS,
        params={"day_minutes": 60})
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    RelaxationQuota.objects.create(family=F.MAX_HOURS, resource=env["klass"],
                                   max_violations=1, params={"margine": 60})
    RelaxationQuota.objects.create(family=F.SUBJECT_CONSTRAINT,
                                   resource=env["klass"], max_violations=1)
    assert solve(env["schedule"], allow_unplaced=False,
                 workers=1).status == "OPTIMAL"

    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_relaxed_constraints_per_resource": 1})
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"


def test_il_margine_si_somma_al_residuo_non_al_tetto_grezzo():
    """L'incrocio fra le quote e ADR-018, che è il punto in cui questo pezzo
    poteva sbagliare in silenzio.

    Due congelate hanno già sforato da sole il tetto di un'ora: il residuo è
    zero, clampato. Il supplemento di un'ora si somma **a quello** — concede
    spazio sopra lo stato corrente — e non al tetto grezzo, che vorrebbe dire
    concedere due ore e cioè far pagare al presente il conto del passato al
    contrario.

    Quattro fasce in un giorno solo, due libere da piazzare: col residuo ne
    entra **una**, e il modello che pretende il piazzamento risponde
    `INFEASIBLE`. Verificato per mutazione: sommando il margine a `cap` invece
    che a `residuo`, entrambe entrano e la risposta diventa `OPTIMAL`."""
    from domain.models import Activity, Placement

    env = mini_school(days=1, slots=4)
    for slot in (0, 1):
        congelata = make_activity(env["subject"], teachers=[env["teacher"]],
                                  classes=[env["klass"]])
        Activity.objects.filter(pk=congelata.pk).update(
            immobility=Activity.Immobility.FIXED)
        Placement.objects.create(schedule=env["schedule"], activity=congelata,
                                 day=0, start_slot=slot)
    for _ in range(2):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])

    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HOURS,
        params={"day_minutes": 60})
    RelaxationQuota.objects.create(family=F.MAX_HOURS, resource=env["klass"],
                                   max_violations=1, params={"margine": 60})

    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"


def test_la_deroga_vale_anche_fra_materie_diverse():
    """`post_separable` (A = B) e `post_cross` (A ≠ B) sono due rami dello
    stesso vincolo: alleggerirne uno solo avrebbe lasciato metà famiglia
    scoperta, e nessun test se ne sarebbe accorto.

    Verificato per mutazione: togliendo la deroga da `post_cross` questo test
    resta `INFEASIBLE`."""
    from domain.models import Subject

    env = mini_school(days=1, slots=2)
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    make_activity(matematica, teachers=[env["teacher"]], classes=[env["klass"]])
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"

    RelaxationQuota.objects.create(family=F.SUBJECT_CONSTRAINT,
                                   resource=env["klass"], max_violations=1)
    assert solve(env["schedule"], allow_unplaced=False,
                 workers=1).status == "OPTIMAL"


# --- una famiglia per volta, nella forma «senza quota INFEASIBLE, con quota
#     OPTIMAL». ⚠ Ciascuna è verificata anche nel verso opposto: la quota da
#     sola non basta se il builder non la usa, e infatti spegnendo il margine
#     nel builder corrispondente il secondo assert torna INFEASIBLE.

def _n_attivita(env, n, **kw):
    return [make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]], **kw) for _ in range(n)]


def _senza_poi_con(env, famiglia, params=None, **quota):
    """Il ritornello: prima si prova che il vincolo non ci sta, poi che la
    quota lo concede. Fallire il primo assert vorrebbe dire un'istanza che non
    esercitava niente."""
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"
    RelaxationQuota.objects.create(family=famiglia, resource=env["klass"],
                                   max_violations=1, params=params or {},
                                   **quota)
    soluzione = solve(env["schedule"], allow_unplaced=False, workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats


def test_quota_su_max_presence():
    env = mini_school(days=1, slots=4)
    _n_attivita(env, 2)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_PRESENCE,
        params={"days": 5, "max_minutes": 60})
    _senza_poi_con(env, F.MAX_PRESENCE, {"margine": 60})


def test_quota_sul_massimo_di_mezze_giornate():
    env = mini_school(days=1, slots=6)   # mattina 0-3, pomeriggio 4-5
    _n_attivita(env, 5)                  # non stanno in una mezza giornata sola
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HALF_DAYS,
        params={"max_half_days": 1})
    _senza_poi_con(env, F.HALF_DAYS, {"margine": 1})


def test_quota_sul_lavorare_una_sola_mezza_giornata():
    """L'altra metà della stessa famiglia, che è una **deroga** e non un
    margine: «lavorare solo mezza giornata al giorno» o si considera o no."""
    env = mini_school(days=1, slots=6)
    _n_attivita(env, 5)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=ResourceTimeConstraint.Type.MAX_HALF_DAYS,
        params={"only_half_day_per_day": True})
    _senza_poi_con(env, F.HALF_DAYS)


def test_quota_su_entrate_e_uscite():
    env = mini_school(days=2, slots=4)
    _n_attivita(env, 7)   # sei celle senza la prima fascia: una deve sforare
    ResourceTimeConstraint.objects.create(
        resource=env["klass"],
        type=ResourceTimeConstraint.Type.ARRIVAL_DEPARTURE,
        params={"days": 2, "not_before_slot": 1})
    _senza_poi_con(env, F.ARRIVAL_DEPARTURE, {"margine": 1})


def test_quota_sui_giorni_liberi_garantiti():
    env = mini_school(days=2, slots=2)
    _n_attivita(env, 4)   # tutte le celle: nessun giorno resta libero
    ResourceTimeConstraint.objects.create(
        resource=env["klass"],
        type=ResourceTimeConstraint.Type.FREE_GUARANTEED,
        params={"free_days": 1})
    _senza_poi_con(env, F.FREE_GUARANTEED, {"margine": 1})


def test_quota_sui_cambi_di_sede():
    from domain.models import Site

    env = mini_school(days=1, slots=2)
    a_site = Site.objects.create(name="A")
    b_site = Site.objects.create(name="B")
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]], site=a_site)
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]], site=b_site)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"],
        type=ResourceTimeConstraint.Type.MAX_SITE_CHANGES,
        params={"per_day": 0})
    _senza_poi_con(env, F.SITES, {"margine": 1})


def test_quota_sul_peso_didattico():
    env = mini_school(days=1, slots=2)
    _n_attivita(env, 2)
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"max_weight_day": 1})
    _senza_poi_con(env, F.DIDACTIC_WEIGHT, {"margine": 1})


def test_quota_sul_massimo_di_ore_di_una_materia():
    env = mini_school(days=1, slots=2)
    _n_attivita(env, 2)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"],
        type=SubjectConstraint.Type.MAX_HOURS_DAY, param=60)
    _senza_poi_con(env, F.SUBJECT_MAX_HOURS, {"margine": 60})


def test_quota_sulle_sequenze_indesiderate():
    from domain.models import Subject

    env = mini_school(days=1, slots=2)
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    make_activity(matematica, teachers=[env["teacher"]], classes=[env["klass"]])
    for a, b in ((env["subject"], matematica), (matematica, env["subject"])):
        SubjectConstraint.objects.create(
            subject_a=a, subject_b=b, school_class=env["klass"],
            type=SubjectConstraint.Type.FORBIDDEN_SEQUENCE)
    # entrambi gli ordini vietati: due ore in due fasce non hanno scampo.
    # ⚠ Due deroghe, non una: il divieto è postato per **coppia di celle**, e
    # in due fasce le coppie possibili sono due (A→B e B→A).
    assert solve(env["schedule"], allow_unplaced=False).status == "INFEASIBLE"
    RelaxationQuota.objects.create(family=F.SUBJECT_SEQUENCE,
                                   resource=env["klass"], max_violations=1)
    soluzione = solve(env["schedule"], allow_unplaced=False, workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
