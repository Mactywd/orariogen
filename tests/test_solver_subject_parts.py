"""I quattro `PARTS_*`: l'ordine fra le ore di parte e le ore a classe intera
(`domain/solver/builders/subject_parts.py`).

⚠ Niente `test_parts_sul_banco` qui (Ruling 16, ottava applicazione):
`tests/solver_harness.py` registra i quattro derivatori sotto
`ST.PARTS_BEFORE_CLASS`, `ST.PARTS_AFTER_CLASS`,
`ST.PARTS_BEFORE_OR_AFTER_CLASS_H` e `ST.PARTS_BEFORE_OR_AFTER_CLASS_AB`, e
`tests/test_solver_witness.py::test_famiglia` gia' parametrizza su
`sorted(DERIVERS) x [1..5]` — i venti casi del banco esistono in automatico
appena i derivatori sono registrati. Scriverli anche qui sarebbe un duplicato
esatto, come gia' per i derivatori dei Task 7-14.

⚠ **Forma avversaria** (Ruling 85), non «risolvi e guarda la soluzione»: ogni
test che afferma la presenza di un vincolo costruisce il modello con
`build_model`, **forza** con `model.Add(ctx.x[...] == 1)` la configurazione
che il checker giudicherebbe violata, e attende `INFEASIBLE`. La forma «lancia
`solve()` e controlla dove sono finite le attivita'» qui non discriminerebbe:
sui due omogenei CP-SAT restituisce da se', deterministicamente, una soluzione
che rispetta la riga — misurato su venti seed del banco, zero soluzioni
violanti col builder **spento**."""
import pytest
from ortools.sat.python import cp_model

from domain.models import (
    ClassPart, ClassPartition, SchoolClass, StudyPlan, SubjectConstraint,
)
from domain.solver.model import build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


def _parti(env, n=1):
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="SDOPP")
    return [ClassPart.objects.create(name=f"1A-g{i}", partition=partizione)
            for i in range(1, n + 1)]


def _riga(env, tipo, **unita):
    return SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"], type=tipo,
        **(unita or {"school_class": env["klass"]}))


def _verdetto(schedule, forzature):
    """Costruisce il modello, forza le celle indicate e restituisce lo stato
    CP-SAT. `forzature`: [(attivita', giorno, fascia), ...]."""
    model, ctx = build_model(schedule)
    for (act, day, slot) in forzature:
        model.Add(ctx.x[(act.id, day, slot)] == 1)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    return solver.Solve(model)


# --- before / after ------------------------------------------------------

def test_before_morde_se_la_parte_segue_la_classe():
    """`PARTS_BEFORE_CLASS`: nel secchio giornata la violazione e'
    `max(fasce di parte) > min(fasce di classe)`. Forzata la classe alla
    fascia 1 e la parte alla 2 nello stesso giorno, il modello dev'essere
    infattibile.

    Verificato per mutazione: con `_PartsOrderBuilder.post` reso no-op questo
    scenario risponde OPTIMAL invece di INFEASIBLE."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_CLASS)
    classe = make_activity(env["subject"], classes=[env["klass"]])
    parte = make_activity(env["subject"], parts=[p1])
    assert _verdetto(env["schedule"],
                     [(classe, 0, 1), (parte, 0, 2)]) == cp_model.INFEASIBLE


def test_before_ammette_la_parte_prima_della_classe():
    """Il complemento del test sopra: un builder che vietasse *tutto*
    supererebbe la prova avversaria (resta INFEASIBLE sempre) e fallirebbe
    qui, dove la configurazione legale dev'essere raggiungibile.

    Il pareggio non e' in discussione per `before`: la disuguaglianza del
    checker e' stretta.

    Difeso da una mutazione mirata (un'assenza non si difende spegnendo il
    builder): scambiando `MODE` fra `PartsBeforeBuilder` e
    `PartsAfterBuilder` questo test diventa rosso."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_CLASS)
    classe = make_activity(env["subject"], classes=[env["klass"]])
    parte = make_activity(env["subject"], parts=[p1])
    assert _verdetto(env["schedule"], [(parte, 0, 1), (classe, 0, 2)]) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_after_morde_se_la_parte_precede_la_classe():
    """`PARTS_AFTER_CLASS`: la violazione e' `min(fasce di parte) <
    max(fasce di classe)`. Speculare al gemello `before`.

    Verificato per mutazione: con `post` no-op risponde OPTIMAL."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_AFTER_CLASS)
    classe = make_activity(env["subject"], classes=[env["klass"]])
    parte = make_activity(env["subject"], parts=[p1])
    assert _verdetto(env["schedule"],
                     [(parte, 0, 1), (classe, 0, 2)]) == cp_model.INFEASIBLE


def test_after_ammette_la_parte_dopo_la_classe():
    """Difeso dalla stessa mutazione mirata del gemello `before`: scambiando
    `MODE` fra i due builder questo test diventa rosso."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_AFTER_CLASS)
    classe = make_activity(env["subject"], classes=[env["klass"]])
    parte = make_activity(env["subject"], parts=[p1])
    assert _verdetto(env["schedule"], [(classe, 0, 1), (parte, 0, 2)]) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE)


# --- omogeneo: «al piu' una transizione», non «tutte le parti prima» -----

def test_omogeneo_vieta_l_interlacciatura():
    """Parte, classe, parte nello stesso secchio: la sequenza di etichette e'
    `P C P`, due transizioni, violazione.

    E' il test che distingue «al piu' una transizione» da «tutte le parti
    prima»: quest'ultima lettura vieterebbe anche `P P C`, che il test
    gemello sotto esibisce come legale.

    Verificato per mutazione: con `post` no-op risponde OPTIMAL."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
    prima = make_activity(env["subject"], parts=[p1])
    classe = make_activity(env["subject"], classes=[env["klass"]])
    dopo = make_activity(env["subject"], parts=[p1])
    assert _verdetto(
        env["schedule"],
        [(prima, 0, 0), (classe, 0, 1), (dopo, 0, 2)]) == cp_model.INFEASIBLE


def test_omogeneo_ammette_le_parti_compatte():
    """Le stesse tre attivita' in ordine `P P C`: una sola transizione,
    legale. Senza questo gemello, un builder che traducesse l'omogeneo come
    «tutte le parti prima **e** compatte in modo piu' stretto del checker»
    passerebbe comunque il test avversario.

    Difeso da una mutazione mirata: togliendo l'`OnlyEnforceIf` alle coppie
    con `sp < sc` — cioe' leggendo l'omogeneo come «le classi prima», un
    vincolo secco invece di un ramo della disgiunzione — questo test diventa
    rosso."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
    prima = make_activity(env["subject"], parts=[p1])
    dopo = make_activity(env["subject"], parts=[p1])
    classe = make_activity(env["subject"], classes=[env["klass"]])
    assert _verdetto(
        env["schedule"],
        [(prima, 0, 0), (dopo, 0, 1), (classe, 0, 2)]) in (
            cp_model.OPTIMAL, cp_model.FEASIBLE)


def test_h_e_ab_hanno_secchi_diversi():
    """⚠ Il test che **separa** i due omogenei. `_H` raggruppa per mezza
    giornata (`PartsHomogeneousHalfChecker` sovrascrive `bucket()` con
    `_half`), `_AB` per giornata: e' l'unica differenza fra i due, e
    invertirla non fa fallire niente di ovvio.

    La direzione discriminante e' una sola. Il secchio mezza giornata e' un
    **sottoinsieme** di quello giornata, e togliere elementi da una sequenza
    non puo' aumentarne le transizioni: quindi «illegale per `_H`» implica
    sempre «illegale per `_AB`». Una configurazione legale per `_AB` e
    illegale per `_H` non esiste, e va cercata la coppia opposta.

    Qui: parte alla fascia 0 e classe alla fascia 1 (mattino, `P C`, una
    transizione), piu' una seconda parte alla fascia 4 (pomeriggio, che da
    solo non ha entrambe le etichette e che il checker salta). Legale per
    `_H`; per `_AB` la giornata intera legge `P C P`, due transizioni.

    Verificato per mutazione: scambiando `KIND` fra
    `PartsHomogeneousHalfBuilder` e `PartsHomogeneousDayBuilder` il test
    diventa rosso sulla prima asserzione (e la seconda cadrebbe subito
    dopo: le due sono l'una il rovescio dell'altra)."""
    env = mini_school()
    assert env["grid"].morning_end_slot == 4      # la fascia 4 e' pomeriggio
    (p1,) = _parti(env)
    riga = _riga(env, T.PARTS_BEFORE_OR_AFTER_CLASS_H)
    mattino = make_activity(env["subject"], parts=[p1])
    classe = make_activity(env["subject"], classes=[env["klass"]])
    pomeriggio = make_activity(env["subject"], parts=[p1])
    celle = [(mattino, 0, 0), (classe, 0, 1), (pomeriggio, 0, 4)]

    assert _verdetto(env["schedule"], celle) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE), "legale sulla mezza giornata"

    riga.type = T.PARTS_BEFORE_OR_AFTER_CLASS_AB
    riga.save()
    assert _verdetto(env["schedule"], celle) == cp_model.INFEASIBLE, (
        "illegale sulla giornata intera")


def test_omogeneo_e_il_pareggio_di_fascia():
    """Il pareggio fra un'occorrenza di parte e una a classe intera **e'**
    realizzabile, e il builder lo tratta come il checker.

    Il brief del task lo dava per impossibile (una lezione a classe intera
    occupa la classe e tutte le sue parti, quindi confliggerebbe). La
    premessa non regge: l'etichetta «classe» si guadagna con una qualunque
    chiave CLASS, non con la classe **della riga**. Qui l'attivita' `esterna`
    ha `classes = [1B]` e `parts = [p1]`: entra nell'unita' della 1A per via
    di `p1`, e' etichettata «classe», e **non** occupa `p2` — quindi puo'
    stare nella stessa fascia di un'attivita' su `p2`.

    Il checker ordina `(fascia, etichetta, id)` e la stringa `"class"`
    precede `"part"`: a parita' di fascia la classe viene **prima**. Da qui
    l'asimmetria dei due rami del builder — «parti prima» chiede `sp < sc`
    (il pareggio lo rompe), «classi prima» chiede `sc <= sp` (il pareggio lo
    rispetta) — e le due asserzioni qui sotto la mettono alla prova nei due
    versi.

    Verificato per mutazione: rendendo simmetrici i due rami (`sp > sc`
    invece di `sp >= sc` per il ramo «parti prima») la prima asserzione
    diventa rossa."""
    env = mini_school()
    p1, p2 = _parti(env, 2)
    altro_piano = StudyPlan.objects.create(code="P2", name="Piano 2", year=1)
    altra = SchoolClass.objects.create(
        name="1B", study_plan=altro_piano, year=1)
    _riga(env, T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
    esterna = make_activity(env["subject"], classes=[altra], parts=[p1])
    su_p2 = make_activity(env["subject"], parts=[p2])
    altra_p2 = make_activity(env["subject"], parts=[p2])

    # P@1, C@2, P@2 -> ordinate: (1,part) (2,class) (2,part) = P C P
    assert _verdetto(env["schedule"], [
        (altra_p2, 0, 1), (esterna, 0, 2), (su_p2, 0, 2)]) == cp_model.INFEASIBLE

    # C@2, P@2, P@3 -> ordinate: (2,class) (2,part) (3,part) = C P P
    assert _verdetto(env["schedule"], [
        (esterna, 0, 2), (su_p2, 0, 2), (altra_p2, 0, 3)]) in (
            cp_model.OPTIMAL, cp_model.FEASIBLE)


# --- ADR-018 -------------------------------------------------------------

def test_adr018_secchio_gia_violato_dalle_congelate():
    """Una parte e una classe **entrambe congelate** in violazione, piu' una
    libera. Il modello **non** dev'essere INFEASIBLE: pretendere che la
    libera ripari un difetto gia' scritto nella baseline e' esattamente cio'
    che ADR-018 vieta.

    Le asserzioni sono **strutturali** (si fissa la libera in una cella e si
    chiede il verdetto), non «risolvi e guarda dove e' finita»:

    1. il modello, da solo, resta risolvibile;
    2. la libera puo' andare in un **altro** giorno;
    3. la libera **non** puo' entrare nel giorno gia' violato. E' il
       trattamento scelto, e non e' zelo: il finding di questo checker porta
       fra le `activities` tutte le occorrenze del secchio, e `activities`
       sta dentro `Finding.key` — una libera in piu' in quel secchio e' un
       finding *nuovo*, non lo stesso della baseline. E' lo stesso
       trattamento del quarto ramo di `post_cross` e del clamp a zero di
       `residual_cap`.

    Verificato per mutazione: rendendo `_viola` sempre falso (cioe'
    togliendo la guardia sul secchio gia' violato) il punto 1 diventa rosso —
    la coppia di congelate finisce sotto una clausola che nessuna delle due
    puo' soddisfare."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_CLASS)
    classe = make_activity(env["subject"], classes=[env["klass"]],
                           immobility="fixed")
    parte = make_activity(env["subject"], parts=[p1], immobility="fixed")
    place(env["schedule"], classe, day=0, slot=1)
    place(env["schedule"], parte, day=0, slot=2)   # gia' violato: 2 > 1
    libera = make_activity(env["subject"], parts=[p1])

    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert _verdetto(env["schedule"], [(libera, 1, 0)]) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert _verdetto(env["schedule"], [(libera, 0, 3)]) == cp_model.INFEASIBLE


def test_adr018_una_sola_congelata_resta_un_divieto():
    """Con **una sola** delle due congelate la clausola resta e forza a zero
    il letterale libero: e' un divieto su una decisione del solver, non una
    riparazione del passato, e ADR-018 lo concede anche quando rende il
    modello INFEASIBLE (stessa proprieta' gia' scritta per
    `ForbiddenSequenceBuilder`).

    Qui la classe e' congelata alla fascia 1 del giorno 0 e il secchio e'
    **pulito** (una sola etichetta fra le congelate): la parte libera puo'
    stare prima di lei, non dopo.

    Verificato per mutazione: con `post` no-op la seconda asserzione risponde
    OPTIMAL invece di INFEASIBLE."""
    env = mini_school()
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_CLASS)
    classe = make_activity(env["subject"], classes=[env["klass"]],
                           immobility="fixed")
    place(env["schedule"], classe, day=0, slot=1)
    parte = make_activity(env["subject"], parts=[p1])

    assert _verdetto(env["schedule"], [(parte, 0, 0)]) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert _verdetto(env["schedule"],
                     [(parte, 0, 2)]) == cp_model.INFEASIBLE


def test_h_morde_dentro_la_stessa_mezza_giornata():
    """⚠ Il test che mancava: fino alla review finale
    `PartsHomogeneousHalfBuilder` non era difeso da **nessun** test.

    Misurato: rendendo `post()` no-op sulla sola sottoclasse `_H`, la suite
    intera restava **424 passed, 15 skipped** — identica alla baseline. Per
    confronto, la stessa mutazione su `_AB` da' 3 rossi, su `PartsBefore` 5,
    su `PartsAfter` 3.

    Era sfuggito perche' tutte le mutazioni fatte finora spegnevano
    `_PartsOrderBuilder.post`, cioe' tutte e quattro le sottoclassi insieme; e
    perche' l'unico test che nomina `_H` — `test_h_e_ab_hanno_secchi_diversi`
    — lo usa nel verso **legale**, cioe' afferma un'assenza. Un'assenza non
    puo' diventare rossa quando il vincolo sparisce.

    Qui `_H` deve **mordere**: parte, classe, parte tutte e tre nel mattino
    del giorno 0. La sequenza di etichette e' `P C P`, due transizioni, e
    «al piu' una transizione» la vieta.

    ⚠ Questo test non separa `_H` da `_AB` — non puo': il secchio mezza
    giornata e' un sottoinsieme di quello giornata, quindi «illegale per `_H`»
    implica sempre «illegale per `_AB`», e una configurazione che li separi
    esiste solo nel verso opposto. La separazione resta compito di
    `test_h_e_ab_hanno_secchi_diversi`; questo test copre l'altra meta', che
    il builder faccia qualcosa."""
    env = mini_school()
    assert env["grid"].morning_end_slot == 4      # 0..3 mattino
    (p1,) = _parti(env)
    _riga(env, T.PARTS_BEFORE_OR_AFTER_CLASS_H)
    prima = make_activity(env["subject"], parts=[p1])
    classe = make_activity(env["subject"], classes=[env["klass"]])
    dopo = make_activity(env["subject"], parts=[p1])

    assert _verdetto(env["schedule"],
                     [(prima, 0, 0), (classe, 0, 1), (dopo, 0, 2)]) == (
        cp_model.INFEASIBLE), "P C P nella stessa mezza giornata: due transizioni"

    assert _verdetto(env["schedule"],
                     [(prima, 0, 0), (dopo, 0, 1), (classe, 0, 2)]) in (
        cp_model.OPTIMAL, cp_model.FEASIBLE), (
        "P P C e' una transizione sola: se anche questo e' INFEASIBLE, "
        "l'INFEASIBLE di sopra non dice niente sul vincolo")
