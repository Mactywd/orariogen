"""I criteri di qualità (`domain/solver/quality.py`, `criteria.py`).

I quattro livelli storici della catena misurano un **fallimento**; questi
misurano com'è fatto l'orario, e stanno sotto tutti e quattro. Due proprietà
li governano, e sono le due che qui si provano famiglia per famiglia:

- un criterio **migliora la propria quantità** — misurata sul valore del
  livello, mai su «guarda dove è finita l'attività»;
- un criterio **non restringe**: non cambia ciò che il modello ammette, solo
  ciò che preferisce.
"""
import pytest

from domain.analysis.conformity import check_schedule
from domain.models import (QualityCriterion, ResourceTimeConstraint,
                           ResourceUnavailability)
from domain.solver.model import apply, build_model, solve
from domain.solver.objective import livelli
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db
K = QualityCriterion.Kind
P = QualityCriterion.Population


def _dimensioni_nude(env):
    """Il modello **senza** la catena: la sola `build_model`."""
    model, _ = build_model(env["schedule"])
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return len(proto.variables), len(proto.constraints)


def _dimensioni(env):
    """⚠ **Costruisce anche la catena**, non solo il modello. I livelli di
    qualità nascono dentro `livelli()`, che `build_model` non chiama: misurare
    il solo modello darebbe due numeri identici con e senza righe, cioè
    un'asserzione incapace di fallire. Colta misurando il Fermi, dove le
    dimensioni non si muovevano di un bit con cinque criteri accesi."""
    model, ctx = build_model(env["schedule"])
    livelli(ctx, model)
    proto = model.proto if hasattr(model, "proto") else model.Proto()
    return len(proto.variables), len(proto.constraints)


def _livelli(soluzione):
    return {e["nome"]: e["valore"] for e in soluzione.stats["livelli"]}


def _n(env, n, **kw):
    return [make_activity(env["subject"], teachers=[env["teacher"]],
                          classes=[env["klass"]], **kw) for _ in range(n)]


def test_la_tabella_vuota_da_la_catena_di_prima():
    """La proprietà conservativa per costruzione, e un test invece di un
    corollario: senza righe `QualityCriterion` non nasce **nessuna** variabile
    e **nessun** livello in più."""
    env = mini_school(days=2, slots=4)
    _n(env, 4)

    # solo L1 e L2: senza quote non c'è L3, e senza un orario precedente da
    # conservare non c'è L4
    nomi = [e["nome"] for e in solve(env["schedule"], workers=1).stats["livelli"]]
    assert nomi == ["minuti_scartati", "attivita_scartate"], nomi

    # ⚠ Il confronto è contro il modello **nudo**, non contro sé stesso. La
    # prima versione di questo test misurava due volte lo stesso stato — non
    # esisteva riga da aggiungere in mezzo — e nessuna variabile di troppo
    # poteva farlo fallire.
    nude, con_catena = _dimensioni_nude(env), _dimensioni(env)
    assert (con_catena[0] - nude[0], con_catena[1] - nude[1]) == (2, 2), (
        "le sole due variabili di L1 e L2 con le loro uguaglianze: "
        f"nude={nude} con_catena={con_catena}")


def test_un_criterio_non_ancora_tradotto_e_un_criterio_ignorato():
    """L'enum è il vocabolario del prodotto e può correre avanti alle
    traduzioni. Una riga che nessun criterio legge non fa fallire il solve: è
    un criterio **ignorato**, che è precisamente ciò che la lista «Criteri
    ignorati» di EDT esprime."""
    env = mini_school(days=2, slots=4)
    _n(env, 4)
    prima = _dimensioni(env)
    QualityCriterion.objects.create(kind="criterio_inventato", rank=1)
    assert _dimensioni(env) == prima, "una riga ignorata non costa nulla"
    assert solve(env["schedule"], workers=1).status == "OPTIMAL"


# --- `preferences`: il pennello verde ---------------------------------------

def _verde(risorsa, day, slot):
    return ResourceUnavailability.objects.create(
        resource=risorsa, day=day, slot=slot,
        level=ResourceUnavailability.Level.PREFERENCE)


def _criterio(kind, popolazione=P.ALL, rank=1):
    return QualityCriterion.objects.create(kind=kind, population=popolazione,
                                           rank=rank)


def test_le_preferenze_contano_tutta_la_durata_non_la_fascia_di_partenza():
    """Due attività da due fasce riempiono la giornata: quella di destra copre
    per forza la fascia 3, che è verde. La fascia di **partenza** però è la 2,
    che verde non è — contare solo quella darebbe zero.

    È lo stesso motivo per cui il pre-filtro guarda tutta la durata: un
    criterio che leggesse `start_slot` misurerebbe un orario diverso da quello
    che il checker giudica."""
    env = mini_school(days=1, slots=4)
    _n(env, 2, slots=2)
    _verde(env["teacher"], 0, 3)
    _criterio(K.PREFERENCES)
    livelli = _livelli(solve(env["schedule"], workers=1))
    assert livelli["preferences_all"] == 1, livelli


def test_le_preferenze_contano_per_chiave_e_per_fascia():
    """La stessa fascia sgradita a **due** risorse costa due: è il conteggio
    che il checker già produce (un finding per chiave, con `slots` dentro), non
    «una attività mal piazzata». E la popolazione lo filtra: con `TEACHERS` la
    classe smette di contare."""
    env = mini_school(days=1, slots=4)
    _n(env, 2, slots=2)
    _verde(env["teacher"], 0, 3)
    _verde(env["klass"], 0, 3)

    criterio = _criterio(K.PREFERENCES)
    assert _livelli(solve(env["schedule"], workers=1))["preferences_all"] == 2

    criterio.population = P.TEACHERS
    criterio.save()
    livelli = _livelli(solve(env["schedule"], workers=1))
    assert livelli["preferences_teachers"] == 1, livelli


def test_le_preferenze_cedono_quando_si_puo_evitarle():
    """Il verso opposto, che senza sarebbe un test di sola aritmetica: dove
    esiste una collocazione che non calpesta niente, il livello la trova e
    vale zero."""
    env = mini_school(days=1, slots=4)
    _n(env, 2)          # due ore singole in quattro fasce: c'è spazio
    _verde(env["teacher"], 0, 0)
    _criterio(K.PREFERENCES)
    assert _livelli(solve(env["schedule"], workers=1))["preferences_all"] == 0


def test_un_criterio_di_qualita_non_restringe():
    """L'invariante del pezzo: un criterio cambia ciò che il modello
    **preferisce**, mai ciò che ammette. L'istanza qui è satura — le due ore
    stanno solo nelle due fasce, entrambe sgradite — e deve restare `OPTIMAL`
    con il criterio acceso."""
    env = mini_school(days=1, slots=2)
    _n(env, 2)
    _verde(env["teacher"], 0, 0)
    _verde(env["teacher"], 0, 1)
    assert solve(env["schedule"], workers=1).status == "OPTIMAL"
    _criterio(K.PREFERENCES)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert _livelli(soluzione)["preferences_all"] == 2
    assert soluzione.stats["scartate"] == 0, "la qualità non scarta"


# --- `free_half_days` e `isolated`: le mezze giornate -----------------------

def test_le_mezze_giornate_libere_si_contano_a_mezze_non_a_giornate():
    """Tre ore stanno tutte nella mattina (quattro fasce): una mezza giornata
    occupata. La quinta ora non ci sta più e ne apre una seconda — **nello
    stesso giorno**, che è ciò che distingue questo criterio da un conteggio di
    giornate: là il valore resterebbe 1."""
    env = mini_school(days=1, slots=6)     # mattina 0-3, pomeriggio 4-5
    _n(env, 3)
    _criterio(K.FREE_HALF_DAYS, P.TEACHERS)
    livelli = _livelli(solve(env["schedule"], workers=1))
    assert livelli["free_half_days_teachers"] == 1, livelli

    _n(env, 2)                             # cinque ore: la mattina non basta
    livelli = _livelli(solve(env["schedule"], workers=1))
    assert livelli["free_half_days_teachers"] == 2, livelli


def test_un_attivita_lunga_due_fasce_non_e_isolata():
    """La definizione del prodotto ha **due** condizioni — sola nella mezza
    giornata *e* di durata inferiore a due fasce — e collassano in «la mezza ha
    esattamente una fascia occupata». Un blocco da due ore da solo occupa due
    fasce: non è isolato, e un conteggio per *attività* direbbe 1."""
    env = mini_school(days=1, slots=6)
    _n(env, 1, slots=2)
    _criterio(K.ISOLATED, P.TEACHERS)
    assert _livelli(solve(env["schedule"], workers=1))["isolated_teachers"] == 0


def test_un_ora_sola_in_una_mezza_giornata_e_isolata():
    env = mini_school(days=1, slots=6)
    _n(env, 1)
    _criterio(K.ISOLATED, P.TEACHERS)
    assert _livelli(solve(env["schedule"], workers=1))["isolated_teachers"] == 1


def test_due_ore_nella_stessa_mezza_giornata_non_sono_isolate():
    """L'altro verso della stessa collasso: due ore singole possono stare
    insieme, e allora nessuna delle due è isolata. Un conteggio per attività
    ne troverebbe due."""
    env = mini_school(days=2, slots=6)
    _n(env, 2)
    _criterio(K.ISOLATED, P.TEACHERS)
    assert _livelli(solve(env["schedule"], workers=1))["isolated_teachers"] == 0


def test_la_classe_e_il_docente_contano_ciascuno_per_conto_proprio():
    """⚠ Con `ALL` una sola ora isolata vale **due**, e non è un doppio
    conteggio per distrazione: il contatore `A.iso.` di EDT è dichiarato «per
    docente/classe/**gruppo**». La stessa ora è isolata per il docente e per la
    classe, e sono due fatti distinti su due risorse distinte."""
    env = mini_school(days=1, slots=6)
    _n(env, 1)
    _criterio(K.ISOLATED, P.ALL)
    assert _livelli(solve(env["schedule"], workers=1))["isolated_all"] == 2


# --- `gaps`: la durata totale dei buchi -------------------------------------

def test_il_criterio_dei_buchi_accosta_le_ore():
    """Due ore in quattro fasce: il criterio le mette adiacenti. Senza, `0` e
    `3` sarebbero una risposta ottima quanto le altre — e costerebbero due
    fasce di buco."""
    env = mini_school(days=1, slots=4)     # una sola mezza giornata
    _n(env, 2)
    _criterio(K.GAPS, P.TEACHERS)
    assert _livelli(solve(env["schedule"], workers=1))["gaps_teachers"] == 0


def test_il_buco_e_lo_stesso_numero_che_conta_il_checker():
    """🔑 Il test che tiene ferma la regola della casa: la definizione si
    **legge** dal checker, non si riscrive. Qui il livello e `MaxGapChecker`
    guardano lo stesso orario e devono dire lo stesso numero — una divergenza
    di uno renderebbe il criterio la misura di qualcos'altro.

    L'istanza è costretta: la fascia 1 è indisponibile al docente, e tre ore
    devono occupare 0, 2 e 3. Il buco è la fascia 1, che il checker conta
    perché legge i piazzamenti e delle indisponibilità non sa nulla."""
    env = mini_school(days=1, slots=4)
    _n(env, 3)
    ResourceUnavailability.objects.create(
        resource=env["teacher"], day=0, slot=1,
        level=ResourceUnavailability.Level.HARD)
    _criterio(K.GAPS, P.TEACHERS)
    soluzione = solve(env["schedule"], workers=1)
    assert _livelli(soluzione)["gaps_teachers"] == 60, soluzione.stats

    apply(soluzione, env["schedule"])
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"],
        type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})
    buchi = [f for f in check_schedule(env["schedule"]) if f.code == "max_gap"]
    assert len(buchi) == 1, buchi
    assert buchi[0].quantities["gap_minutes"] == 60


def test_i_buchi_non_attraversano_la_mezza_giornata():
    """L'ultima ora della mattina e la prima del pomeriggio non fanno buco fra
    loro: il checker somma **per mezza giornata**, e la pausa di mezzogiorno
    non è tempo perso. Qui le due ore sono costrette una per metà, e il
    criterio deve dire zero."""
    env = mini_school(days=1, slots=6)     # mattina 0-3, pomeriggio 4-5
    _n(env, 2)
    for slot in (0, 1, 2, 5):              # restano libere la 3 e la 4
        ResourceUnavailability.objects.create(
            resource=env["teacher"], day=0, slot=slot,
            level=ResourceUnavailability.Level.HARD)
    _criterio(K.GAPS, P.TEACHERS)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    assert _livelli(soluzione)["gaps_teachers"] == 0


# --- `regularity`: la materia sempre alla stessa ora ------------------------

def test_la_regolarita_mette_ogni_materia_sempre_alla_stessa_ora():
    """Due materie da due ore in una griglia 2×2. La risposta regolare mette
    ITALIANO sempre alla prima ora e MATEMATICA sempre alla seconda: due fasce
    distinte in tutto, una per materia. La risposta incrociata ne userebbe
    quattro, e riempirebbe la griglia esattamente allo stesso modo — è la
    differenza che questo criterio esiste per vedere."""
    from domain.models import Subject

    env = mini_school(days=2, slots=2)
    matematica = Subject.objects.create(code="MAT", name="Matematica",
                                        discipline=env["discipline"])
    _n(env, 2)
    for _ in range(2):
        make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    _criterio(K.REGULARITY, P.CLASSES)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    assert _livelli(soluzione)["regularity_classes"] == 2, soluzione.stats


def test_la_regolarita_non_scende_mai_sotto_una_fascia_per_materia():
    """Il minimo per coppia (unità, materia) è **uno**: la materia sta da
    qualche parte. Il valore assoluto del livello conta quindi meno della sua
    differenza fra due orari, ed è bene che sia scritto."""
    env = mini_school(days=2, slots=2)
    _n(env, 2)
    _criterio(K.REGULARITY, P.CLASSES)
    assert _livelli(solve(env["schedule"], workers=1))["regularity_classes"] == 1


# --- l'ordine ---------------------------------------------------------------

def test_l_ordine_dei_criteri_decide_chi_cede():
    """⚠ L'istanza è scelta perché i due criteri **tirino in direzioni
    opposte**, e non è un dettaglio: su un pareggio i due ordini darebbero la
    stessa risposta e il test resterebbe verde con la gerarchia rotta. È
    l'errore già commesso e corretto sull'ondata 2 del pezzo precedente.

    Due ore della stessa materia in una griglia 2×2. Metterle nello stesso
    giorno occupa **una** mezza giornata sola ma le mette a ore diverse;
    metterle alla stessa ora di due giorni diversi è regolare ma occupa due
    mezze giornate. Non esiste l'orario che accontenta entrambi, quindi chi ha
    `rank` più basso vince — ed è tutto ciò che «lessicografico» significa."""
    env = mini_school(days=2, slots=2)
    _n(env, 2)
    regolarita = _criterio(K.REGULARITY, P.CLASSES, rank=1)
    libere = _criterio(K.FREE_HALF_DAYS, P.CLASSES, rank=2)

    livelli = _livelli(solve(env["schedule"], workers=1))
    assert (livelli["regularity_classes"],
            livelli["free_half_days_classes"]) == (1, 2), livelli

    regolarita.rank, libere.rank = 2, 1
    regolarita.save()
    libere.save()
    livelli = _livelli(solve(env["schedule"], workers=1))
    assert (livelli["regularity_classes"],
            livelli["free_half_days_classes"]) == (2, 1), livelli
