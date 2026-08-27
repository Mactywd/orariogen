"""Tetto di ore per materia in un secchio (giornata/mezza giornata), e la
sequenza vietata: `_MaxHoursSubject` (sulla base comune `_Bucketed`,
Ruling 58) e `ForbiddenSequenceBuilder`, entrambi in
`domain/solver/builders/subject_buckets.py`.

⚠ Niente `test_sul_banco` qui (Ruling 16, correzione 3 del brief Task 9, qui
quarta applicazione — Ruling 61): `tests/solver_harness.py` registra
`_derive_max_hours_day`, `_derive_max_hours_half_day` e
`_derive_forbidden_sequence` sotto `T.MAX_HOURS_DAY`, `T.MAX_HOURS_HALF_DAY`
e `T.FORBIDDEN_SEQUENCE`, e `tests/test_solver_witness.py::test_famiglia`
gia' parametrizza su `sorted(DERIVERS) × [1..5]` — i cinque seed di tutte e
tre le famiglie esistono in automatico appena i derivatori sono registrati.
Scriverli anche qui sarebbe un duplicato esatto, come gia' per i derivatori
dei Task 7-10."""
import pytest
from ortools.sat.python import cp_model

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.models import Subject, SubjectConstraint
from domain.solver.model import apply, build_model, solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db
T = SubjectConstraint.Type


def test_max_hours_day_limita_la_materia():
    """Due congelate che riempiono esattamente il tetto in un giorno: la
    terza, libera, non deve aggiungersi a quel giorno. Deterministico (non
    si osserva dove il solver mette le tre attivita' di sua scelta, ma si
    forzano due collocazioni e si verifica l'unica cosa che il vincolo
    vieta) — verificato per mutazione: spegnendo il `post` di
    `MaxHoursDayBuilder` il test fallisce (la libera finisce nel giorno gia'
    pieno, che senza vincolo e' una cella candidata come ogni altra)."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    c = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.MAX_HOURS_DAY, param=120)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.placements[c.id][0] != 0


def test_max_hours_half_day_morde_solo_meta_giornata():
    """Il tetto vale sul secchio **mezza giornata**, non sull'intera
    giornata: due congelate al mattino del giorno 0 (`morning_end_slot = 4`
    in mini_school) gia' al tetto; la libera non deve aggiungersi al
    mattino, ma il pomeriggio dello stesso giorno resta un secchio diverso
    e ammesso — verificato costruendo il modello e forzando la libera li'."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    c = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.MAX_HOURS_HALF_DAY, param=120)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    day, slot = soluzione.placements[c.id]
    assert not (day == 0 and slot < env["grid"].morning_end_slot)

    # Il pomeriggio dello stesso giorno resta ammesso: il vincolo non
    # trabocca sull'intera giornata come farebbe MAX_HOURS_DAY.
    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(c.id, 0, env["grid"].morning_end_slot)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), status


def test_adr018_max_hours_giorno_gia_sopra_il_tetto():
    """ADR-018: due congelate che gia' da sole sforano il tetto (`param =
    60`, due attivita' da 60' = 120' nello stesso giorno: residuo negativo,
    clampato a zero da `residual_cap`). Non deve essere INFEASIBLE, e la
    libera non deve aggiungersi a quel giorno — verificato rileggendo il
    piazzamento col checker: la violazione preesistente delle due congelate
    resta (non e' compito del builder ripararla), ma la libera non ci deve
    comparire dentro."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    c = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.MAX_HOURS_DAY, param=60)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    trovate = [f for f in check_schedule(env["schedule"])
               if f.code == "subject_max_hours_day" and f.severity == Severity.HARD]
    assert trovate   # la violazione preesistente delle due congelate resta
    assert all(c.id not in f.activities for f in trovate)


def test_adr018_max_hours_half_day_gia_sopra_il_tetto():
    """Gemello di `test_adr018_max_hours_giorno_gia_sopra_il_tetto` sul
    secchio **mezza giornata** (Minor 3, review Task 11): stesso `post`,
    ma qui il clamp di `residual_cap` interagisce con `bucket_of` sulla
    fascia di **partenza**, ed e' la famiglia col potere vincolante piu'
    basso — quella che il banco a testimone sorveglia meno.

    ⚠ Le due congelate stanno **entrambe nel mattino**, dove secchio-giorno
    e secchio-mezza-giornata coincidono: con le sole asserzioni sul finding
    questo test sarebbe il gemello DAY con l'enum scambiato, e infatti non
    falliva mutando `KIND` a `"day"` (Minor 2, ri-review Task 11). Il
    secondo blocco separa le due semantiche: il **pomeriggio dello stesso
    giorno** e' un secchio diverso, e la libera ci deve poter entrare —
    cosa che il tetto per giornata vieterebbe."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    c = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    place(env["schedule"], b, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.MAX_HOURS_HALF_DAY, param=60)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    trovate = [f for f in check_schedule(env["schedule"])
               if f.code == "subject_max_hours_half_day"
               and f.severity == Severity.HARD]
    assert trovate   # la violazione preesistente delle due congelate resta
    assert all(c.id not in f.activities for f in trovate)

    # Il pomeriggio dello stesso giorno e' un secchio diverso, e il clamp a
    # zero del mattino non ci arriva: e' cio' che distingue questo vincolo
    # dal gemello per giornata.
    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(c.id, 0, env["grid"].morning_end_slot)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), status


def test_max_hours_day_con_a_diverso_da_b_conta_solo_a():
    """Important 3 (review Task 11): `_MaxHours.violations`
    (domain/analysis/checkers/subject_constraints.py, righe 149-159) itera
    su `a` e non tocca mai `b` — il tetto vale sulla **sola** materia A
    anche quando A != B. Nessun derivatore crea mai questo caso
    (`_derive_max_hours_subject` chiama sempre `subject_a=subject,
    subject_b=subject`), quindi restava scoperto.

    Costruisce un tetto (`param = 100`) che la sola A rispetta ma che
    A + B (60' di una congelata B gia' nel secchio, piu' 60' della libera
    A) sforerebbe: forzando la libera A in quel giorno il modello deve
    restare **fattibile**, perche' il checker somma solo A (60' <= 100).
    Verificato per mutazione: sommando anche B nel `post` — un errore
    semantico reale contro il checker — forzare la libera li' diventa
    INFEASIBLE.

    ⚠ **Il primo blocco da solo non basta**, ed e' l'Important 1 della
    ri-review: e' unilaterale per forma — asserisce che il modello resti
    **fattibile**, e un builder che per le righe A != B non posta nulla e'
    fattibile pure lui. Con `if row.subject_a_id != row.subject_b_id:
    return` in testa a `_MaxHoursSubject.post` l'intero ramo A != B poteva
    sparire senza che la suite se ne accorgesse. Il secondo blocco chiude
    l'altra meta': il tetto sulla **sola A** deve applicarsi comunque."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    b_congelata = make_activity(matematica, classes=[env["klass"]],
                                immobility="fixed")
    a_libera = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], b_congelata, day=0, slot=0)
    riga = SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.MAX_HOURS_DAY, param=100)
    model, ctx = build_model(env["schedule"])
    model.Add(ctx.x[(a_libera.id, 0, 1)] == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), status

    # L'altra meta': il tetto sulla sola A morde comunque. Si aggiunge una
    # **seconda** attivita' di A congelata nello stesso giorno e si stringe
    # il tetto a 60': ora A da sola vale gia' 60', `residual_cap` clampa il
    # residuo a zero, e la libera di A non puo' entrare in quel giorno.
    a_congelata = make_activity(env["subject"], classes=[env["klass"]],
                                immobility="fixed")
    place(env["schedule"], a_congelata, day=0, slot=1)
    riga.param = 60
    riga.save()
    model, ctx = build_model(env["schedule"], allow_unplaced=False)
    model.Add(ctx.x[(a_libera.id, 0, 2)] == 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


def test_forbidden_sequence_vieta_l_adiacenza():
    """B non puo' iniziare esattamente dove A finisce, nello stesso giorno.
    Deterministico: A congelata forza la fascia di fine, e si verifica che
    la libera B non ci parta — verificato per mutazione: spegnendo il
    `post` di `ForbiddenSequenceBuilder` il test fallisce."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(matematica, classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=0)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.FORBIDDEN_SEQUENCE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    day, slot = soluzione.placements[b.id]
    assert not (day == 0 and slot == 1)


def test_forbidden_sequence_con_a_uguale_b():
    """Il checker permette A = B (`ForbiddenSequenceChecker.violations` non
    esclude `subject_a_id == subject_b_id`; la sola guardia e'
    `pb.activity_id != pa.activity_id`), e il builder ha il corrispondente
    `if pb == pa: continue`. Nessun derivatore crea questo caso
    (`_derive_forbidden_sequence` salta con `if a.pk == b.pk: continue`),
    quindi se non lo si testa qui resta scoperto — Minor 4 del Task 10, in
    anticipo.

    Con A = B `subject_activities(A)` e `subject_activities(B)` sono la
    stessa lista: il doppio ciclo del builder produce sia (a, b) sia (b, a)
    come coppie distinte (escluse solo quando coincidono), quindi
    l'adiacenza e' vietata in **entrambi i versi** — verificato qui
    (Important 2, review Task 11) forzando la congelata alla fascia **1**
    (non alla 0, dove il verso «la libera finisce dove la congelata
    comincia» sarebbe impossibile comunque e quindi non osservabile) e
    controllando che entrambe le fasce adiacenti alla congelata siano
    INFEASIBLE per la libera. Verificato per mutazione: con
    `if row.subject_a_id == row.subject_b_id and pb <= pa: continue`
    aggiunto al `post()` del builder (vieta un verso solo, in funzione
    dell'ordine dei `pk` — quale dei due blocchi fallisce dipende da quale
    attivita' e' stata creata per prima), questo test fallisce."""
    env = mini_school()
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=env["subject"],
        school_class=env["klass"], type=T.FORBIDDEN_SEQUENCE)

    # verso «B finisce dove A comincia»: la libera non puo' partire alla
    # fascia 0 (0 + durata 1 = 1, dove la congelata comincia).
    model, ctx = build_model(env["schedule"], allow_unplaced=False)
    model.Add(ctx.x[(b.id, 0, 0)] == 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE

    # verso «B comincia dove A finisce»: la libera non puo' partire alla
    # fascia 2 (la congelata finisce li', 1 + durata 1 = 2).
    model, ctx = build_model(env["schedule"], allow_unplaced=False)
    model.Add(ctx.x[(b.id, 0, 2)] == 1)
    solver = cp_model.CpSolver()
    assert solver.Solve(model) == cp_model.INFEASIBLE


# --- ADR-018, FORBIDDEN_SEQUENCE ------------------------------------------


def test_adr018_forbidden_sequence_entrambe_congelate_nessun_vincolo():
    """Ramo 1 (Ruling 59): con **entrambe** congelate il `continue` e'
    `any_free`, «un fatto, non una decisione» — non il `continue` su un
    tetto che le Rulings 14/23/28 vietano. Verificato non assumendo: le due
    congelate sono piazzate **gia' adiacenti** (violano la sequenza). Se il
    builder postasse comunque la clausola per questa coppia, i due letterali
    sono entrambi forzati a 1 dall'unico `AddExactlyOne` della propria
    attivita' congelata (dominio a una sola cella), e la clausola `not(x_a)
    or not(x_b)` sarebbe in conflitto immediato: il modello sarebbe
    INFEASIBLE. Deve restare FEASIBLE.

    ⚠ Serve una terza attivita' **libera** (di A, mai piazzata vicino a
    nulla) solo per tenere viva la riga: il gate di riga di
    `SubjectBuilder.build` («c'e' qualcosa di libero fra le coinvolte?»)
    salterebbe comunque `post()` se **tutta** la riga fosse congelata, e
    allora il test non eserciterebbe affatto il `continue` per-coppia di
    `ForbiddenSequenceBuilder` che vuole verificare — misurato rimuovendo
    quel `continue`: senza la terza attivita' il test restava verde anche
    senza guardia (il gate di riga la copriva gia'), con la terza attivita'
    diventa INFEASIBLE come previsto, ed e' la prova che la guardia serve
    davvero."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a_fissa = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    b_fissa = make_activity(matematica, classes=[env["klass"]], immobility="fixed")
    make_activity(env["subject"], classes=[env["klass"]])   # a_libera, tiene viva la riga
    place(env["schedule"], a_fissa, day=0, slot=0)
    place(env["schedule"], b_fissa, day=0, slot=1)   # adiacente: viola gia' la sequenza
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.FORBIDDEN_SEQUENCE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats


def test_adr018_forbidden_sequence_una_congelata_la_libera_evita():
    """Ramo 2: con una sola congelata la clausola resta e forza a zero il
    letterale libero corrispondente — qui la libera A ha altrove dove
    andare, quindi il modello resta fattibile ed evita la fascia vietata.

    Verso **B congelata, A libera** (Minor 1, review Task 11): il gemello
    esatto era gia' interamente coperto da `test_forbidden_sequence_vieta_
    l_adiacenza` (A congelata, B libera) — stessi corpi carattere per
    carattere, solo le docstring differivano. Qui si esercita il verso non
    ancora coperto con A != B: la libera A non deve **finire** dove
    comincia la congelata B, cioe' non deve iniziare alla fascia
    immediatamente precedente (la congelata e' alla fascia 1, quindi la
    libera A non deve iniziare alla fascia 0)."""
    env = mini_school()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], classes=[env["klass"]])
    b = make_activity(matematica, classes=[env["klass"]], immobility="fixed")
    place(env["schedule"], b, day=0, slot=1)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.FORBIDDEN_SEQUENCE)
    soluzione = solve(env["schedule"])
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    day, slot = soluzione.placements[a.id]
    assert not (day == 0 and slot == 0)


def test_adr018_forbidden_sequence_una_congelata_forza_infattibile():
    """Ramo 3 (Ruling 59, Minor 5 del Task 10 in anticipo): con una sola
    congelata la clausola forza a zero il letterale libero corrispondente —
    e se quella e' l'**unica** cella rimasta per la libera, il modello
    **deve** essere INFEASIBLE. E' testualmente cio' che ADR-018 concede:
    non garantisce una soluzione, garantisce solo che il passato non
    impedisca di provarci.

    Griglia a un solo giorno, due sole fasce: A congelata alla fascia 0
    occupa la classe li' (structural:occupation vieta la sovrapposizione),
    quindi l'unica fascia libera per B e' la 1 — esattamente quella vietata
    dalla sequenza."""
    env = mini_school()
    env["grid"].days_per_cycle = 1
    env["grid"].slots_per_day = 2
    env["grid"].morning_end_slot = 2
    env["grid"].save()
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    a = make_activity(env["subject"], classes=[env["klass"]], immobility="fixed")
    make_activity(matematica, classes=[env["klass"]])  # b, libera
    place(env["schedule"], a, day=0, slot=0)
    SubjectConstraint.objects.create(
        subject_a=env["subject"], subject_b=matematica,
        school_class=env["klass"], type=T.FORBIDDEN_SEQUENCE)
    soluzione = solve(env["schedule"], allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats
