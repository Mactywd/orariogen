"""Le sedi: `MAX_SITE_CHANGES` (cambi contati per giornata e per settimana) e
`structural:site_transition` (fasce libere richieste fra due lezioni su sedi
diverse).

⚠ Niente `test_sedi_sul_banco` qui (Ruling 16, correzione 3 del brief Task 9):
`tests/solver_harness.py` registra `_derive_max_site_changes` sotto
`T.MAX_SITE_CHANGES` e `_derive_site_transition` sotto
`"structural:site_transition"`, e `tests/test_solver_witness.py::test_famiglia`
gia' parametrizza su `sorted(DERIVERS) × [1..5]` — i cinque seed di entrambe
le famiglie esistono in automatico appena i derivatori sono registrati.
Scriverli anche qui sarebbe un duplicato esatto, come gia' per i derivatori
dei Task 7 e 8.

⚠ Il primo test qui sotto e' quello che difende la Correzione 1 (Ruling 27):
la formulazione originale del piano ('tutto vuoto in mezzo' invece di
'nessuna sede nota in mezzo') non vedeva nessun cambio in questa istanza —
vedi `domain/solver/builders/time_sites.py` per la spiegazione e il report
del Task 9 per la riproduzione verbatim del difetto prima della correzione."""
import pytest

from domain.models import (
    Activity, InstituteSettings, Placement, ResourceTimeConstraint, Site,
)
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school

pytestmark = pytest.mark.django_db
T = ResourceTimeConstraint.Type


def test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo():
    """La riproduzione della Correzione 1, ora contro il builder corretto.
    Sede A alla fascia 0, un'attivita' senza sede alla fascia 1, sede B alla
    fascia 2 — un solo giorno nella griglia, cosi' non c'e' altrove dove
    andare. Con `per_day = 0` il checker vede sempre la sequenza [A, B] (la
    senza-sede non entra nella sottosequenza) e boccia sempre, qualunque sia
    l'ordine scelto per le tre attivita': i due soli siti presenti compaiono
    sempre in un ordine, mai uguali.

    Col builder sbagliato del piano ('tutto vuoto in mezzo') il solver
    trovava sempre `OPTIMAL` piazzando esattamente [A, senza sede, B], perche'
    era l'unico arrangiamento che non innescava nessuna delle sue coppie —
    e la soluzione, riletta dal checker, falliva. Col builder corretto
    ('nessuna sede nota in mezzo') quell'arrangiamento e' proprio quello
    vietato: il modello deve risultare INFEASIBLE, perche' e' l'unica
    istanza possibile su questa griglia e viola sempre il tetto.

    ⚠ `site_transition_slots` a zero: isola MAX_SITE_CHANGES da
    `structural:site_transition`, che con tre attivita' tutte adiacenti su
    un'unica giornata avrebbe anche lui qualcosa da dire (a default 1) — non
    e' quello sotto esame qui."""
    env = mini_school()
    env["grid"].days_per_cycle = 1
    env["grid"].slots_per_day = 3
    env["grid"].morning_end_slot = 3
    env["grid"].save()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})

    a_site = Site.objects.create(name="A")
    b_site = Site.objects.create(name="B")
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]], site=a_site)
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]])
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]], site=b_site)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_SITE_CHANGES, params={"per_day": 0})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_max_site_changes_limita_i_cambi():
    """Tre attivita' alternate fra due sedi, un solo cambio al giorno
    consentito: il solver deve raggrupparle per sede.

    ⚠ Verificato che **non discrimina**: passa anche con
    `MaxSiteChangesBuilder.post` disattivato del tutto, perche' senza alcun
    vincolo tre attivita' libere trovano comunque posto da qualche parte —
    e' un test di consistenza (il builder non deve rendere infattibile
    un'istanza risolvibile), non una controprova. Quella che morde e'
    `test_max_site_changes_intercetta_il_cambio_con_una_senza_sede_in_mezzo`
    in cima al file."""
    env = mini_school()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    for sede in (centrale, succursale, centrale):
        make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=sede)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_SITE_CHANGES, params={"per_day": 1})
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats


def test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca():
    """ADR-018 (correzione 2 del brief, Ruling 28), primo test: le sole
    congelate non devono bloccare il solver. Due congelate adiacenti di sede
    diversa (A poi B) sullo stesso giorno: un cambio gia' presente nel
    passato, tetto giornaliero dichiarato **zero**. Senza il clamp, il
    letterale di quella coppia e' forzato vero dalle sole congelate e il
    vincolo grezzo `sum(cambi) <= 0` sarebbe insoddisfacibile a prescindere
    da qualunque attivita' libera — infattibile per colpa del passato, cio'
    che ADR-018 vieta. Col clamp (`max(0, consumo_congelate) = 1`) il modello
    resta risolvibile e l'attivita' libera trova comunque posto.

    ⚠ `site_transition_slots` a zero: e' un test isolato su MAX_SITE_CHANGES,
    non su `structural:site_transition` (quello ha gia' un guardiano ADR-018
    proprio, non toccato da questo task — vedi il report per la scoperta
    fatta scrivendo questo test)."""
    env = mini_school()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    a_site = Site.objects.create(name="A")
    b_site = Site.objects.create(name="B")
    frozen_a = make_activity(env["subject"], teachers=[env["teacher"]],
                             classes=[env["klass"]], site=a_site,
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    frozen_b = make_activity(env["subject"], teachers=[env["teacher"]],
                             classes=[env["klass"]], site=b_site,
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    Placement.objects.create(schedule=env["schedule"], activity=frozen_a,
                             day=0, start_slot=0)
    Placement.objects.create(schedule=env["schedule"], activity=frozen_b,
                             day=0, start_slot=1)
    libera = make_activity(env["subject"], teachers=[env["teacher"]],
                           classes=[env["klass"]])
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_SITE_CHANGES, params={"per_day": 0})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert libera.id in soluzione.placements


def test_adr018_clamp_impedisce_alla_libera_di_aggiungere_un_cambio():
    """La controprova che distingue clamp da salto (correzione 2 del brief,
    Ruling 28) — quella che conta davvero. Stesso passato del test sopra (A
    poi B, adiacenti, giorno 0, debito gia' contratto = 1 cambio), ma la
    libera ha una **terza** sede (C), diversa da entrambe, ed e' **costretta**
    sul giorno 0 (indisponibile ovunque altro): qualunque fascia del giorno 0
    le venga assegnata, la sua sede nota si affianca alla sottosequenza
    [A, B] gia' presente e produce **almeno un altro** cambio (nessuna sede
    fra lei e il blocco A/B: le fasce di mezzo, se ce ne sono, sono vuote di
    sede) — il totale del giorno salirebbe a due, oltre il debito gia'
    contratto (uno). Col clamp questo e' vietato ovunque sul giorno 0, e
    siccome non ha altrove dove andare il modello dev'essere INFEASIBLE.

    ⚠ **Perche' costretta, non lasciata libera fra i giorni.** La prima
    stesura di questo test lasciava la libera scegliere fra tutti i giorni e
    si limitava ad asserire `giorno != 0`: passava col clamp, ma passava
    *anche* con un salto (`continue` quando le congelate gia' sforano)
    mutato apposta — CP-SAT, senza un obiettivo che preferisca il giorno 0,
    trovava comunque una soluzione su un altro giorno per conto suo, e
    l'asserzione non discriminava nulla (verificato: la mutazione lasciava la
    suite verde). Costringendo la libera sul giorno 0 la domanda diventa
    INFEASIBLE-contro-FEASIBLE, che il salto rovescia davvero: senza il
    vincolo del giorno 0 (saltato perche' le congelate lo sforano gia' da
    sole) la libera puo' restarci indisturbata, e il modello torna FEASIBLE —
    proprio il difetto gia' corretto due volte su questo piano (review Task 6
    Important 2, Ruling 23 sul Task 8) e vietato da ADR-018.

    ⚠ `site_transition_slots` a zero, stesso motivo del test sopra: isola
    MAX_SITE_CHANGES da `structural:site_transition`."""
    env = mini_school()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 0})
    a_site = Site.objects.create(name="A")
    b_site = Site.objects.create(name="B")
    c_site = Site.objects.create(name="C")
    frozen_a = make_activity(env["subject"], teachers=[env["teacher"]],
                             classes=[env["klass"]], site=a_site,
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    frozen_b = make_activity(env["subject"], teachers=[env["teacher"]],
                             classes=[env["klass"]], site=b_site,
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    Placement.objects.create(schedule=env["schedule"], activity=frozen_a,
                             day=0, start_slot=0)
    Placement.objects.create(schedule=env["schedule"], activity=frozen_b,
                             day=0, start_slot=1)
    from domain.models import ResourceUnavailability
    for day in range(1, 5):
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=env["teacher"], day=day, slot=slot, level="hard")
    make_activity(env["subject"], teachers=[env["teacher"]],
                 classes=[env["klass"]], site=c_site)
    ResourceTimeConstraint.objects.create(
        resource=env["klass"], type=T.MAX_SITE_CHANGES, params={"per_day": 0})

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_site_transition_impone_le_fasce_libere():
    """Due attivita' della stessa classe su sedi diverse, con due fasce di
    trasferimento richieste: non possono stare a meno di tre fasce di
    distanza nello stesso giorno."""
    env = mini_school()
    InstituteSettings.objects.update_or_create(
        pk=1, defaults={"site_transition_slots": 2})
    centrale = Site.objects.create(name="Centrale")
    succursale = Site.objects.create(name="Succursale")
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=centrale)
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], site=succursale)
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    (ga, sa), (gb, sb) = soluzione.placements[a.id], soluzione.placements[b.id]
    if ga == gb:
        assert abs(sa - sb) - 1 >= 2


# ⚠ Un tentativo di test in piu' e' stato scartato qui, non aggiunto: una
# variante dell'istanza sopra con **due** giorni invece di uno (cosi' il
# solver trova sempre una soluzione, per un test in stile oracolo con
# apply()+check_schedule()). Verificato che **non discrimina** il difetto
# della Correzione 1: con due giorni a disposizione, il solver evita
# l'adiacenza A/B semplicemente separandole di giornata, sia col builder
# corretto sia con quello sbagliato — il difetto vive tutto **dentro** la
# stessa giornata (l'iterazione e' per-day), quindi appena il solver ha una
# via di fuga fra giorni diversi il test passa comunque, senza dire nulla sul
# builder. Confermato mutando davvero il builder alla formulazione sbagliata
# e rilanciando: verde in entrambi i casi (vedi il report del Task 9). La
# dimostrazione che *invece* morde e' `test_max_site_changes_intercetta_il_
# cambio_con_una_senza_sede_in_mezzo` sopra: la stessa istanza ristretta a un
# solo giorno, dove non c'e' via di fuga, e l'asserzione e' INFEASIBLE.
