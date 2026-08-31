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


# --- i due arrivati con O5 (ADR-025) ----------------------------------------

def test_la_distribuzione_settimanale_sparpaglia_la_materia_sui_giorni():
    """Quattro ore della stessa materia in una griglia 4×1: una per giorno, e
    il criterio vale **zero**. È il minimo dichiarato — ogni occorrenza in un
    giorno suo — e qui è raggiungibile perché la griglia lo permette."""
    env = mini_school(days=4, slots=1)
    _n(env, 4)
    _criterio(K.WEEKLY_SPREAD, P.CLASSES)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    assert _livelli(soluzione)["weekly_spread_classes"] == 0, soluzione.stats


def test_e_conta_le_occorrenze_di_troppo_non_le_coppie():
    """⚠ La quantità è `occorrenze − giorni distinti`, e questo test la
    **distingue** dalla lettura letterale di EDT.

    Quattro ore in due giorni da due fasce: due per giorno, per forza. Le
    *coppie* nello stesso giorno sarebbero 2 (una per giorno); le occorrenze di
    troppo sono anch'esse 2. Il caso che separa le due letture è il terzo
    ammucchiamento — tre ore in un giorno valgono 3 coppie e **2** occorrenze
    di troppo — e sta nel test seguente. Qui si fissa il numero facile, perché
    è quello che una regressione romperebbe per primo."""
    env = mini_school(days=2, slots=2)
    _n(env, 4)
    _criterio(K.WEEKLY_SPREAD, P.CLASSES)
    soluzione = solve(env["schedule"], workers=1)
    assert _livelli(soluzione)["weekly_spread_classes"] == 2, soluzione.stats


def test_tre_ore_in_un_giorno_costano_due_e_non_tre():
    """🔑 La differenza fra la nostra quantità e le «coppie» di EDT, misurata.

    Un giorno solo, tre fasce, tre ore della stessa materia: non c'è scelta.
    Le coppie nello stesso giorno sarebbero **3**, le occorrenze di troppo
    **2**. Il numero che il livello riporta è 2, e la scelta è dichiarata in
    `_sparpaglia`: la lettura letterale è quadratica, questa è lineare, e
    nessun orario le scambia di posto — perché fra due orari il verso della
    disuguaglianza è lo stesso."""
    env = mini_school(days=1, slots=3)
    _n(env, 3)
    _criterio(K.WEEKLY_SPREAD, P.CLASSES)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    assert _livelli(soluzione)["weekly_spread_classes"] == 2, soluzione.stats


def test_le_fasce_sparse_sono_la_regolarita_al_contrario():
    """🔑 Lo stesso testimone di `test_la_regolarita_mette_ogni_materia_sempre_
    alla_stessa_ora`, con l'altro criterio: due materie da due ore in una
    griglia 2×2.

    `regularity` sceglie la risposta **regolare** — ogni materia sempre alla
    stessa ora, due fasce distinte in tutto — e vale 2. `slot_spread` sceglie
    la risposta **incrociata**, quattro fasce distinte, e vale 0: nessuna
    occorrenza di troppo. I due orari riempiono la griglia allo stesso modo, e
    la differenza è tutta in quale dei due un criterio preferisce.

    ⚠ È la stessa griglia e sono i due versi opposti: è per questo che il
    testimone è deliberatamente lo stesso, e non uno costruito su misura."""
    from domain.models import Subject

    env = mini_school(days=2, slots=2)
    matematica = Subject.objects.create(code="MAT", name="Matematica",
                                        discipline=env["discipline"])
    _n(env, 2)
    for _ in range(2):
        make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    _criterio(K.SLOT_SPREAD, P.TEACHERS)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    assert _livelli(soluzione)["slot_spread_teachers"] == 0, soluzione.stats


def test_i_due_versi_convivono_su_popolazioni_diverse():
    """🔑 L'asimmetria di EDT, detta nel nostro modello: la classe vuole il
    ritmo, il docente vuole variare.

    Qui le due popolazioni **non competono** — il docente insegna alla sola
    classe — quindi i due criteri chiedono cose incompatibili sullo stesso
    orario e vince il primo della catena. Che è il punto: entrambi hanno un
    valore, e l'ordine dichiarato dai dati decide. `regularity` è il rango 1,
    quindi scende a 2 e `slot_spread` paga."""
    from domain.models import Subject

    env = mini_school(days=2, slots=2)
    matematica = Subject.objects.create(code="MAT", name="Matematica",
                                        discipline=env["discipline"])
    _n(env, 2)
    for _ in range(2):
        make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    _criterio(K.REGULARITY, P.CLASSES, rank=1)
    _criterio(K.SLOT_SPREAD, P.TEACHERS, rank=2)
    livelli_ = _livelli(solve(env["schedule"], workers=1))
    assert livelli_["regularity_classes"] == 2
    assert livelli_["slot_spread_teachers"] == 2


def test_sulla_stessa_popolazione_il_secondo_dei_due_versi_e_inerte():
    """⚠ **La forma «argomento»**: il verdetto è vero per costruzione, non per
    come è andata la ricerca.

    `regularity` minimizza *secchi distinti*; `slot_spread` minimizza
    *occorrenze − secchi distinti*. Sulla stessa popolazione e con le
    occorrenze già fissate dai livelli 1 e 2 della catena, il secondo è una
    funzione affine decrescente del primo: appena il livello di testa fissa il
    proprio ottimo, il secondo **non ha più niente da scegliere** e assume il
    valore complementare.

    Qui: quattro occorrenze, `regularity` scende a 2 (due materie, una fascia
    ciascuna) e `slot_spread` vale per forza `4 − 2 = 2`, cioè il suo
    **peggio** su questa istanza — dove da solo varrebbe 0
    (test precedente). Non c'è un vincolo che vieti la coppia: c'è questo
    numero, che la rende inutile e lo dice."""
    from domain.models import Subject

    env = mini_school(days=2, slots=2)
    matematica = Subject.objects.create(code="MAT", name="Matematica",
                                        discipline=env["discipline"])
    _n(env, 2)
    for _ in range(2):
        make_activity(matematica, teachers=[env["teacher"]],
                      classes=[env["klass"]])
    _criterio(K.REGULARITY, P.CLASSES, rank=1)
    _criterio(K.SLOT_SPREAD, P.CLASSES, rank=2)
    livelli_ = _livelli(solve(env["schedule"], workers=1))
    assert livelli_["regularity_classes"] == 2
    assert livelli_["slot_spread_classes"] == 2


def test_il_criterio_4_non_rende_infattibile_dove_il_divieto_lo_farebbe():
    """🔑 **Il valore di O5 in un test.** Tre ore della stessa materia e due
    soli giorni: due finiranno lo stesso giorno, non c'è alternativa.

    Come **divieto** — `SAME_DAY_INCOMPATIBLE` — l'istanza è infattibile e la
    scuola resta senza orario. Come **criterio** l'orario esiste, il livello
    dichiara `1` e la scuola sa quanto ha pagato. È la differenza fra
    impedire e preferire, ed è la ragione per cui questo criterio è il primo
    dei tre approvati."""
    from domain.models import SubjectConstraint

    env = mini_school(days=2, slots=2)
    _n(env, 3)
    _criterio(K.WEEKLY_SPREAD, P.CLASSES)
    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.stats["scartate"] == 0, soluzione.stats
    assert _livelli(soluzione)["weekly_spread_classes"] == 1, soluzione.stats

    # Lo stesso desiderio come divieto: l'ora di troppo non si piazza più.
    SubjectConstraint.objects.create(
        school_class=env["klass"], subject_a=env["subject"],
        subject_b=env["subject"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    assert solve(env["schedule"], workers=1).stats["scartate"] == 1


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


# --- il budget dei livelli di qualità ---------------------------------------

def test_chi_dimostra_l_ottimo_non_ha_budget():
    """🔑 Il default sta dove un livello **non sa dimostrare l'ottimo**.

    I livelli che contano un **fallimento** chiudono dimostrando l'ottimo,
    perché il loro ottimo è zero e zero è anche il limite inferiore banale: sul
    Fermi 1,7 s e 0,7 s. I criteri di qualità hanno ottimi non nulli con limiti
    inferiori inutili (`free_half_days` 202 con limite 6), quindi non
    concludono mai — e senza budget `manage.py solve` **non torna**: nove
    minuti senza risposta, misurati.

    ⚠ Un budget globale sarebbe stato il rimedio sbagliato: punirebbe proprio i
    livelli che l'ottimo lo dimostrano.

    ⚠ E il criterio non è la famiglia ma la **posizione**: questo testimone non
    ha un orario di partenza, quindi non ha il livello di stabilità — che in
    testa è senza budget e in coda, sotto l'arbitrato, lo prende
    (`test_in_coda_la_stabilita_prende_il_budget_della_qualita`)."""
    from domain.solver.objective import BUDGET_QUALITA

    env = mini_school(days=2, slots=4)
    _n(env, 4)
    QualityCriterion.objects.create(kind=K.GAPS, population=P.ALL, rank=1)
    model, ctx = build_model(env["schedule"])

    budget = {lv.nome: lv.limite for lv in livelli(ctx, model)}
    assert budget["minuti_scartati"] is None
    assert budget["attivita_scartate"] is None
    assert budget["gaps_all"] == BUDGET_QUALITA


def test_il_limite_esplicito_vince_in_entrambi_i_versi():
    """⚠ Anche **allungando**: chi passa un numero sta rispondendo alla domanda
    «quanto tempo mi costa», e non gli si mette davanti un default. Il test
    guarda il parametro che il solver riceve, non il tempo di parete — che
    dipenderebbe dalla macchina."""
    from ortools.sat.python import cp_model

    from domain.solver.objective import Level, solve_chain

    visti = []

    class _SolverCheAnnota:
        def __init__(self):
            self._vero = cp_model.CpSolver()
            self.parameters = self._vero.parameters

        def Solve(self, m):
            visti.append(self.parameters.max_time_in_seconds)
            return self._vero.Solve(m)

        def Value(self, var):
            return self._vero.Value(var)

        def BestObjectiveBound(self):
            return self._vero.BestObjectiveBound()

    def catena(model):
        x = [model.NewBoolVar(f"x{i}") for i in range(3)]
        senza = model.NewIntVar(0, 3, "senza")
        model.Add(senza == sum(x))
        con = model.NewIntVar(0, 3, "con")
        model.Add(con == sum(x))
        return [Level("senza", senza), Level("con", con, 15.0)]

    model = cp_model.CpModel()
    solve_chain(model, catena(model), estrai=lambda s: {},
                solver=_SolverCheAnnota())
    assert visti[0] > 1e8 and visti[1] == 15.0   # il budget proprio, e nessuno

    visti.clear()
    model = cp_model.CpModel()
    solve_chain(model, catena(model), estrai=lambda s: {}, time_limit=99.0,
                solver=_SolverCheAnnota())
    assert visti == [99.0, 99.0], "un limite esplicito vale per tutti i livelli"


def test_fermi_i_criteri_di_qualita_misurati():
    """Il costo dei criteri di qualità sul Fermi, e la diagnosi che lo spiega.

    🔑 **Un livello non è lento perché sia difficile da ottimizzare: è lento
    perché è impossibile da dimostrare.** `gaps` arriva a 0 e chiude in un
    secondo — zero è anche il limite inferiore banale, quindi valore e limite
    si toccano subito. `free_half_days` si ferma a 202 con limite inferiore
    **6**, `regularity` a 236 con **18**: il divario non è un residuo di
    ricerca, è tutto il valore. Da qui il budget dei soli livelli di qualità.

    ⚠ **E i lavoratori pesano più del limite.** A 15 s per livello, misurato:
    con **1** lavoratore `regularity 359`, `free_half_days 243`, `isolated 37`;
    con **4**, `236`, `202` e **0** — l'ottimo, raggiunto in 7 s e non
    dimostrato. `--lavoratori 1` serve alla riproducibilità e si paga.

    ⛔ **E la riparazione ovvia non funziona.** Un limite inferiore
    *implicato* per `free_half_days` — `somma_h attiva(g,h)·len(span_h) >=
    somma_s occupata(g,s)` per chiave e giorno, valido sempre — non chiude il
    divario: **lo peggiora**. Misurato a 15 s: valore da 202 a 209, limite da
    6 a **4**. La presolve di CP-SAT ne deriva già almeno altrettanto, e le
    140 righe in più costano ricerca. Scritta, misurata, buttata — e non
    riprovata, perché romperebbe anche l'invariante «un criterio posta solo
    definizioni», da cui dipende `_valori_di_base`.

    ⚠ Qui si gira con `--limite 3` per non spendere un minuto di suite: i
    numeri sopra vengono dalla misura a 15 s, che è il ginocchio della curva
    (`free_half_days` 202 a 15 s e 199 a 60 s; `regularity` 236 e 226)."""
    import time

    from tests import fermi

    dataset = fermi.build()
    for i, kind in enumerate([K.GAPS, K.ISOLATED, K.FREE_HALF_DAYS,
                              K.REGULARITY, K.PREFERENCES], 1):
        QualityCriterion.objects.create(kind=kind, population=P.ALL, rank=i)

    t0 = time.perf_counter()
    soluzione = solve(dataset["schedule"], time_limit=3)
    secondi = time.perf_counter() - t0
    livelli_ = soluzione.stats["livelli"]
    print(f"\nFermi qualità: {secondi:.1f}s, {len(livelli_)} livelli")
    for lv in livelli_:
        print(f"   {lv['nome']:<22} {lv['valore']:>6}  "
              f"limite {lv['limite']:>4}  divario {lv['divario']:>6}"
              f"  {lv['secondi']}s")

    assert soluzione.status in ("OPTIMAL", "FEASIBLE")
    assert soluzione.unplaced == ()
    nomi = [lv["nome"] for lv in livelli_]
    # ⚠ `preferences` non diventa un livello: il Fermi non ha indisponibilità
    # verdi, quindi il criterio è la costante zero e `livelli_di_qualita` lo
    # salta. Cinque righe, quattro livelli — ed è la regola «un criterio senza
    # niente da misurare non è un livello», non una perdita.
    assert "preferences_all" not in nomi
    # ⚠ I livelli che girano sono un **prefisso** dell'ordine dichiarato, non
    # necessariamente tutti: a 3 s per livello e con la macchina carica un
    # livello di qualità può non restituire alcuna soluzione, e allora la
    # catena si ferma — è il comportamento dichiarato di `solve_chain`, non un
    # difetto. Pretendere la coda esatta rendeva questo test rosso sotto la
    # suite intera e verde da solo, che è il modo peggiore di fallire.
    attesi = ["minuti_scartati", "attivita_scartate", "gaps_all",
              "isolated_all", "free_half_days_all", "regularity_all"]
    assert nomi == attesi[:len(nomi)]

    per_nome = {lv["nome"]: lv for lv in livelli_}
    assert per_nome["gaps_all"]["divario"] == 0, "zero è anche il suo limite"
    dimostrabili_male = [lv for lv in livelli_
                         if lv["nome"] in attesi[3:] and lv["divario"] is not None]
    assert dimostrabili_male, "nessun livello oltre gaps: la misura è vuota"
    assert any(lv["divario"] > 0 for lv in dimostrabili_male), (
        "il divario dei criteri dopo `gaps` è il fenomeno che questo test "
        "misura: se diventasse zero ovunque, il limite inferiore avrebbe "
        "smesso di essere inutile")
