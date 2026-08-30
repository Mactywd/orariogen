"""Il criterio di riuscita: solve → apply → check_schedule → zero HARD nelle
famiglie modellate. Il registro dei predicati e' l'oracolo del solver: le due
facce sono state scritte dai lati opposti dello stesso dato.

Dal Task 17 le famiglie sono **ventisei**, non le cinque dello spike: vedi
`CODICI` qui sotto e la guardia che gli impedisce di invecchiare."""
import datetime as dt

import pytest

from domain import weeks
from domain.analysis.conformity import check_schedule, week_signatures
from domain.analysis.findings import Severity
from domain.models import (
    Activity, Break, ClassPart, ClassPartition, Discipline, Extraction, Period,
    Placement, ResourceTimeConstraint, ResourceUnavailability, Schedule,
    SchoolClass, SchoolYear, StudyPlan, Subject, SubjectConstraint, Teacher,
    TimeGrid,
)
from domain.solver.model import apply, solve
from tests import fermi
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

# Le causali di **tutte** le ventisei famiglie modellate. Fino al Task 16
# questo insieme elencava le sole cinque dello spike, e l'oracolo del Fermi
# era percio' cieco su ventuno famiglie su ventisei: un `check_schedule` che
# gira su tutto ma di cui si guardava un ventesimo.
CODICI = {
    # strutturali
    "resource_occupied", "resource_occupied_locked", "resource_peak",
    "unavailability",
    "slot_out_of_grid", "break_straddled", "holiday",
    "site_transition",
    # l'allineamento (L5, ADR-022): il solver sceglie la cella, quindi due
    # allineate che finiscono in celle diverse sono un finding **nuovo** che
    # questo oracolo deve vedere.
    "alignment_split",
    # il picco del **gruppo di aule** (ADR-021): la fase 1 le conta, quindi
    # e' questo oracolo a sorvegliarlo — non quello della seconda fase, che
    # sorveglia invece *quale* aula viene assegnata (`room_unassigned`).
    "room_group_peak",
    "weight_day", "weight_morning", "weight_afternoon", "weight_week",
    # orari sulla risorsa
    "min_distribution", "max_hours_day", "max_hours_morning",
    "max_hours_afternoon", "max_presence", "max_presence_days",
    "arrival_departure", "free_guaranteed", "max_half_days", "only_half_day",
    "max_site_changes", "max_gap",
    # di materia
    "subject_same_half_day", "subject_same_day", "subject_two_days",
    "subject_forbidden_sequence", "subject_max_hours_half_day",
    "subject_max_hours_day", "subject_weekly_order",
    "subject_imposed_succession", "subject_half_day_gap",
    "subject_parts_order",
    # lo scarto: il solver lo decide, quindi l'oracolo lo sorveglia. Un
    # piazzamento che c'era nella baseline e che il solve ha rinunciato a
    # tenere e' un finding **nuovo**, e va visto.
    "activity_unplaced",
}

# La legalita' di cio' che **e' piazzato**, separata dalla completezza
# dell'orario. Un'attivita' fuori dall'estrazione, o che il solver ha
# rinunciato a piazzare, non e' un'illegalita': e' un buco. I test che
# pretendono un orario *legale* usano questo insieme; il confronto
# differenziale di `nuove()` resta su CODICI, dove uno scarto **nuovo** —
# qualcosa che era piazzato e non lo e' piu' — deve vedersi.
LEGALITA = CODICI - {"activity_unplaced"}

# Le causali del catalogo che restano **deliberatamente** fuori.
FUORI = {
    # nessun builder: PLACEMENT_INDEPENDENT, il solver non crea ne' distrugge
    # attivita' (vedi tests/test_solver_registry_completo.py). Le altre due
    # sono lo stesso checker (ADR-020): l'elezione e il piano ambiguo sono
    # predicati sui **dati** — il monte ore e chi lo deve — e nessuna
    # collocazione li cambia.
    "coverage_mismatch", "election_mismatch", "ambiguous_study_plan",
    # non sono HARD: violazioni() le filtrerebbe comunque per severita', ma
    # elencarle qui rende la scelta leggibile invece che implicita
    "unavailability_optional", "preference",
    # l'assegnazione delle aule e' una **seconda fase**, un modello separato
    # che gira sui piazzamenti gia' scritti (`domain/solver/rooms.py`).
    # `solve()` qui e' il primo modello, che non tocca mai `assigned_room`:
    # non e' questo oracolo a doverlo vedere, ed e' l'oracolo della seconda
    # fase (`tests/test_rooms_oracle.py`) a sorvegliarlo.
    "room_unassigned",
}


def test_codici_copre_tutto_il_catalogo():
    """La guardia contro la deriva: una causale nuova in
    `domain/analysis/causali.py` deve finire in CODICI oppure in FUORI, per
    decisione esplicita. Senza questo test l'insieme invecchia in silenzio —
    ed e' esattamente quello che gli e' successo per ventuno famiglie."""
    from domain.analysis import causali
    assert set(causali.CAUSALI) == CODICI | FUORI


# 🔑 Le famiglie che nominano il **secchio** invece del violatore, e per cui
# quindi la `Finding.key` cambia per il solo fatto che una libera e' stata
# piazzata. Sono esattamente i checker `PLACEMENT_MONOTONE = False` di
# `domain/analysis`, meno due esclusi con la loro ragione (vedi sotto), e
# `test_le_famiglie_grossolane_seguono_il_registro` tiene ferma la
# corrispondenza — una famiglia marcata non monotona domani deve passare di
# qui invece di rendere l'oracolo rosso senza spiegazione.
NON_MONOTONE = {
    "structural:didactic_weight": ("weight_day", "weight_morning",
                                   "weight_afternoon", "weight_week"),
    "free_guaranteed": ("free_guaranteed",),
    "max_gap_hours": ("max_gap",),
    "min_distribution": ("min_distribution",),
    "imposed_succession": ("subject_imposed_succession",),
    "weekly_order": ("subject_weekly_order",),
    "parts_after_class": ("subject_parts_order",),
    "parts_before_class": ("subject_parts_order",),
    "parts_before_or_after_class_ab": ("subject_parts_order",),
    "parts_before_or_after_class_h": ("subject_parts_order",),
    # ⚠ Esclusi apposta, entrambi non monotoni e nessuno dei due «a secchio»:
    # `structural:placement` nomina **una** attivita', e uno scarto nuovo e'
    # precisamente cio' che questo oracolo esiste per vedere — sgrossarlo lo
    # renderebbe cieco sull'unica cosa che il solver decide da se';
    # `structural:room_assignment` sta in FUORI, e' la seconda fase.
    "structural:placement": (),
    "structural:room_assignment": (),
}
CAUSALI_GROSSOLANE = {c for codes in NON_MONOTONE.values() for c in codes}


def test_le_famiglie_grossolane_seguono_il_registro():
    """La guardia contro la deriva, nella forma di `test_codici_copre_tutto_il
    _catalogo`: se un checker viene marcato non monotono, deve comparire qui
    con le sue causali — o con la tupla vuota e il perche'."""
    from domain.analysis.registry import REGISTRY, all_checkers

    all_checkers()
    non_monotoni = {str(k) for k, cls in REGISTRY.items()
                    if not cls.PLACEMENT_MONOTONE}
    assert non_monotoni == set(NON_MONOTONE)


def _grossolana(chiave_settimana):
    """(causale, risorse, settimana): la chiave **senza** l'identita' delle
    attivita' e senza le quantita'."""
    chiave, week = chiave_settimana
    return (chiave.code, chiave.resources, week)


def violazioni(schedule, codici=CODICI):
    """L'insieme delle (chiave, settimana) dei finding HARD nelle famiglie
    modellate. Un insieme, non una lista: il criterio di riuscita e' il
    **contenimento** (ADR-018), non l'uguaglianza.

    Espanso per settimana invece di lasciare la sola chiave: `Finding.key`
    esclude deliberatamente `weeks` (e' pensata per il dedup fra firme dentro
    check_schedule), quindi una violazione identica per codice/risorse/
    attivita'/quantita' ma comparsa su una firma diversa da quella di
    partenza si fonderebbe nello stesso finding e sparirebbe dal calcolo
    differenziale di `nuove()`. Espandere per settimana la rende visibile."""
    return {(f.key, w) for f in check_schedule(schedule)
            if f.severity == Severity.HARD and f.code in codici
            for w in f.weeks}


def nuove(schedule, prima, codici=CODICI):
    """I finding HARD comparsi **dopo** il solve. Il solver puo' anche
    riparare una violazione preesistente spostando un'attivita' libera: quello
    e' un successo, non una discrepanza, ed e' per questo che il criterio e'
    il contenimento e non l'uguaglianza.

    🔑 **E su una famiglia «a secchio» gia' violata, la chiave si sgrossa.** Il
    debito §9.5 del modello hard, ora chiuso da una misura invece che previsto:
    con due congelate oltre il tetto settimanale di peso didattico e una libera
    da piazzare, la libera **va collocata e ovunque vada pesa**, quindi il
    finding `weight_week` torna con `activities (1,2) → (1,2,3)` e `weight
    6 → 9`. `Finding.key` diversa, violazione la stessa: l'oracolo dichiarava
    rotto un solve che non aveva fatto niente di male. Il builder non puo'
    rimediare — il tetto e' inevadibile per costruzione — quindi la
    riparazione sta qui.

    ⚠ **L'esenzione e' stretta, e va detto quanto.** Vale solo se la coppia
    (causale, risorsa, settimana) era **gia'** violata nella baseline: una
    risorsa pulita resta protetta dalla chiave intera. Cio' che si perde e' il
    **peggioramento** di una violazione che c'era gia' — su `max_gap`, per
    esempio, una libera piazzata in mezzo alla giornata di un docente gia'
    fuori budget non fa scattare nulla. E' il prezzo di ADR-018 sulle famiglie
    che nominano il secchio invece del violatore, ed e' un prezzo dichiarato:
    l'alternativa sarebbe confrontare la *quantita'* violata famiglia per
    famiglia, cioe' riscrivere fuori dai checker la nozione di «quale numero e'
    quello cattivo» — il difetto che questo progetto ha gia' intercettato due
    volte."""
    dopo = violazioni(schedule, codici)
    gia_rotte = {_grossolana(k) for k in prima}
    return {k for k in dopo - prima
            if not (k[0][0] in CAUSALI_GROSSOLANE
                    and _grossolana(k) in gia_rotte)}


def _scuola_media():
    """Tre classi, tre docenti, tutte e cinque le famiglie attive. Dimensionata
    con margine: se risulta infattibile, il bug e' nella traduzione, non
    nell'istanza."""
    env = mini_school()
    Break.objects.create(grid=env["grid"], boundary_slot=4)
    italiano = env["subject"]
    matematica = Subject.objects.create(
        code="MAT", name="Matematica", discipline=env["discipline"])
    storia = Subject.objects.create(
        code="STO", name="Storia", discipline=env["discipline"])

    classi = [env["klass"]]
    for nome in ("1B", "1C"):
        classi.append(SchoolClass.objects.create(
            name=nome, study_plan=env["plan"], year=1))

    docenti = {"ITA": env["teacher"]}
    for codice, cognome, nome in (("MAT", "Bruni", "Ivo"), ("STO", "Sala", "Rita")):
        docenti[codice] = Teacher.objects.create(
            name=f"{cognome} {nome}", last_name=cognome, first_name=nome)

    # due partizioni su 1A: gli atomi di ADR-017 entrano nel modello
    irc = ClassPartition.objects.create(school_class=env["klass"], name="IRC")
    rel = ClassPart.objects.create(name="1A_REL", partition=irc)
    ClassPart.objects.create(name="1A_ALT", partition=irc)
    lingua = ClassPartition.objects.create(school_class=env["klass"], name="LINGUA")
    ing = ClassPart.objects.create(name="1A_ING", partition=lingua)
    ClassPart.objects.create(name="1A_TED", partition=lingua)

    ita_activities = []
    for classe in classi:
        for codice, materia in (("ITA", italiano), ("MAT", matematica), ("STO", storia)):
            for _ in range(2):
                att = make_activity(materia, teachers=[docenti[codice]], classes=[classe])
                if codice == "ITA":
                    ita_activities.append(att)
    make_activity(matematica, teachers=[docenti["MAT"]], classes=[classi[1]],
                  slots=2, respects_breaks=True)
    make_activity(italiano, parts=[rel])
    make_activity(italiano, parts=[ing])

    for fascia in range(6):
        ResourceUnavailability.objects.create(
            resource=docenti["STO"], day=4, slot=fascia, level="hard")
    for fascia in (1, 2):
        ResourceUnavailability.objects.create(
            resource=docenti["ITA"], day=0, slot=fascia, level="hard")
    ResourceTimeConstraint.objects.create(
        resource=docenti["ITA"], type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 240})
    SubjectConstraint.objects.create(
        subject_a=italiano, subject_b=italiano, school_class=env["klass"],
        type=SubjectConstraint.Type.SAME_DAY_INCOMPATIBLE)
    env["docenti"] = docenti
    env["ita_activities"] = ita_activities
    return env


def test_oracolo_sulla_scuola_media():
    env = _scuola_media()
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], LEGALITA) == set()


def test_oracolo_sul_fermi_per_una_classe():
    """Le attivita' di 2A libere, tutto il resto fuori dal modello. 2A e' la
    classe che passa dal docente D09, indisponibile tre giorni su cinque."""
    dataset = fermi.build()
    classe = dataset["classes"]["2A"]
    estrazione = Extraction.objects.create(name="2A")
    estrazione.activities.set(classe.activities.all())
    soluzione = solve(dataset["schedule"], extraction=estrazione, time_limit=60)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert len(soluzione.placements) == classe.activities.count()
    apply(soluzione, dataset["schedule"])
    assert violazioni(dataset["schedule"], LEGALITA) == set()


def test_oracolo_puo_fallire():
    """L'oracolo deve poter fallire, non solo passare sempre. Senza questo
    test, un oracolo diventato vacuo — per esempio perche' l'insieme CODICI
    perde un codice, o un checker smette di essere registrato — passerebbe
    silenziosamente per sempre: gli altri test dell'oracolo continuerebbero a
    dare 'violazioni() == set()' anche se non stessero piu' verificando niente.
    Qui corrompiamo deliberatamente due Placement dopo un solve+apply andato a
    buon fine, e verifichiamo che violazioni() veda ciascuna corruzione con il
    codice atteso, in due famiglie diverse: occupazione (due attivita' dello
    stesso docente sulla stessa cella) e indisponibilita' (un'attivita'
    spostata su una fascia rossa)."""
    env = _scuola_media()
    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], LEGALITA) == set()

    ita = env["ita_activities"]  # [1A×2, 1B×2, 1C×2], stesso docente per tutte
    docente_ita = env["docenti"]["ITA"]

    # Famiglia "occupazione": due attivita' dello stesso docente (classi
    # diverse, 1A e 1B) forzate sulla stessa cella.
    p_a = Placement.objects.get(schedule=env["schedule"], activity=ita[0])
    p_b = Placement.objects.get(schedule=env["schedule"], activity=ita[2])
    giorno_orig, fascia_orig = p_b.day, p_b.start_slot
    p_b.day, p_b.start_slot = p_a.day, p_a.start_slot
    p_b.save()
    codici = {codice for (codice, *_), _settimana in violazioni(env["schedule"], LEGALITA)}
    assert "resource_occupied" in codici

    # Ripristino: la corruzione precedente non deve contaminare la successiva.
    p_b.day, p_b.start_slot = giorno_orig, fascia_orig
    p_b.save()
    assert violazioni(env["schedule"], LEGALITA) == set()

    # Famiglia "indisponibilita'": un'attivita' del docente ITA spostata sulla
    # fascia (giorno=0, fascia=1), dichiarata indisponibile hard per lui.
    assert ResourceUnavailability.objects.filter(
        resource=docente_ita, day=0, slot=1, level="hard").exists()
    p_a.day, p_a.start_slot = 0, 1
    p_a.save()
    codici = {codice for (codice, *_), _settimana in violazioni(env["schedule"], LEGALITA)}
    assert "unavailability" in codici


def _scuola_multi_firma():
    """Due settimane con firme diverse, per disciplinare la dimensione che il
    Fermi non esercita (una sola firma, tutto annuale). Un docente con
    D.T.B. = 0 sulla classe; due attivita' della prima settimana forzate da
    indisponibilita' **datate** su (giorno 0, fascia 0) e (giorno 0, fascia
    2); una terza attivita', libera, attiva solo nella seconda settimana.

    Per settimana l'istanza e' infattibile: il buco alla fascia 1 non e'
    colmabile da nessuna attivita' attiva in quella settimana (la terza
    attivita' non c'e' ancora). Un builder che trattasse tutte le attivita'
    come co-attive vedrebbe invece la terza attivita' come disponibile a
    riempire il buco, e dichiarerebbe OPTIMAL una soluzione che
    check_schedule rifiuta per la prima settimana — esattamente il difetto
    dimostrato in time_constraints.py."""
    grid = TimeGrid.objects.create(
        days_per_cycle=1, slots_per_day=3, slot_minutes=60, morning_end_slot=3)
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 9, 27),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1", start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    t1 = Teacher.objects.create(name="Uno Aldo", last_name="Uno", first_name="Aldo")
    t2 = Teacher.objects.create(name="Due Bice", last_name="Due", first_name="Bice")
    t3 = Teacher.objects.create(name="Tre Ciro", last_name="Tre", first_name="Ciro")

    prima_settimana = weeks.single_week(0)
    seconda_settimana = weeks.single_week(1)
    make_activity(subject, teachers=[t1], classes=[klass], mask=prima_settimana)
    make_activity(subject, teachers=[t2], classes=[klass], mask=prima_settimana)
    make_activity(subject, teachers=[t3], classes=[klass], mask=seconda_settimana)

    lunedi_prima_settimana = year.first_week_monday
    for fascia in (1, 2):
        ResourceUnavailability.objects.create(
            resource=t1, day=0, slot=fascia, level="hard", date=lunedi_prima_settimana)
    for fascia in (0, 1):
        ResourceUnavailability.objects.create(
            resource=t2, day=0, slot=fascia, level="hard", date=lunedi_prima_settimana)

    ResourceTimeConstraint.objects.create(
        resource=klass, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    return {"schedule": schedule}


def test_oracolo_su_istanza_multi_firma():
    """Il dataset Fermi ha un'unica firma di settimana (tutto annuale): questo
    test e' l'unico a esercitare davvero la dimensione «settimane». L'istanza
    e' costruita apposta per essere infattibile **per settimana** (il buco
    alla fascia 1 della prima settimana non e' colmabile da nessuna attivita'
    attiva in quella settimana): un builder corretto deve dichiararlo, non
    nasconderlo dietro un OPTIMAL che check_schedule rifiuterebbe.

    Prima della correzione, trattare tutte le attivita' come co-attive faceva
    apparire colmabile il buco con l'attivita' della seconda settimana: il
    solver rispondeva OPTIMAL, e check_schedule bocciava il piazzamento con
    un HARD max_gap — il fallimento che questo test scopre."""
    env = _scuola_multi_firma()
    # `allow_unplaced=False`: la domanda qui e' «il buco e' colmabile?», e con
    # lo scarto ammesso la risposta sarebbe «no, e allora rinuncio», che e'
    # un'altra domanda. Il modello che pretende il piazzamento e' quello in cui
    # l'infattibilita' e' la risposta.
    soluzione = solve(env["schedule"], time_limit=30, allow_unplaced=False)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def _scuola_multi_firma_fattibile():
    """Due firme di settimana, e un'istanza che ha una soluzione **solo** se il
    modello le distingue. Griglia 2 giorni x 4 fasce, anno di due settimane.

    Il giorno 0 porta la dimensione D.T.B.: la classe non tollera buchi. Nella
    settimana 0 ci sono A2 — inchiodata alla fascia 0 dalle indisponibilita'
    del suo docente — e A1, libera; nella settimana 1 c'e' la sola A3,
    inchiodata alla fascia 3. Prese insieme, le tre occuperebbero {0, 3} piu'
    una fascia: un buco incolmabile su quattro fasce. Prese per firma, la
    settimana 0 chiude il buco mettendo A1 alla fascia 1, e la settimana 1 ha
    una fascia sola, che un buco non ce l'ha.

    Il giorno 1 porta la dimensione occupazione: A5 (settimana 0) e A6
    (settimana 1) condividono docente e classe e hanno entrambe una sola
    collocazione ammissibile, la stessa. Co-attive sarebbero un conflitto; non
    lo sono mai.

    Un modello che trattasse tutte le attivita' come co-attive risponderebbe
    quindi INFEASIBLE a un'istanza che una soluzione ce l'ha."""
    grid = TimeGrid.objects.create(
        days_per_cycle=2, slots_per_day=4, slot_minutes=60, morning_end_slot=4)
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 9, 27),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1", start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)

    docenti = {}
    for sigla, cognome, nome in (("T1", "Uno", "Aldo"), ("T2", "Due", "Bice"),
                                 ("T3", "Tre", "Ciro"), ("T5", "Cinque", "Ebe")):
        docenti[sigla] = Teacher.objects.create(
            name=f"{cognome} {nome}", last_name=cognome, first_name=nome)

    def solo_su(docente, cella):
        """Indisponibilita' ovunque tranne una cella: l'attivita' di quel
        docente ha un dominio di cardinalita' uno. **Ricorrenti**, non datate,
        cosi' le firme di settimana restano due e a distinguerle e' soltanto
        la maschera delle attivita'."""
        for d in range(grid.days_per_cycle):
            for s in range(grid.slots_per_day):
                if (d, s) != cella:
                    ResourceUnavailability.objects.create(
                        resource=docente, day=d, slot=s, level="hard")

    solo_su(docenti["T2"], (0, 0))
    solo_su(docenti["T3"], (0, 3))
    solo_su(docenti["T5"], (1, 0))

    prima, seconda = weeks.single_week(0), weeks.single_week(1)
    attivita = {
        "A1": make_activity(subject, teachers=[docenti["T1"]], classes=[klass], mask=prima),
        "A2": make_activity(subject, teachers=[docenti["T2"]], classes=[klass], mask=prima),
        "A3": make_activity(subject, teachers=[docenti["T3"]], classes=[klass], mask=seconda),
        "A5": make_activity(subject, teachers=[docenti["T5"]], classes=[klass], mask=prima),
        "A6": make_activity(subject, teachers=[docenti["T5"]], classes=[klass], mask=seconda),
    }

    ResourceTimeConstraint.objects.create(
        resource=klass, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    return {"schedule": schedule, "attivita": attivita}


def test_oracolo_su_istanza_multi_firma_fattibile():
    """L'altra meta' della dimensione «settimane»: non l'istanza infattibile
    che il solver deve rifiutare, ma una **fattibile** portata per intero lungo
    la catena solve -> apply -> check_schedule -> violazioni() == set().

    E' il caso che il criterio di riuscita dello spike descrive davvero, e che
    prima di questo test nessun banco di prova copriva: la scuola giocattolo,
    il Fermi per una classe e il Fermi intero hanno tutti **una sola** firma di
    settimana, perche' al Fermi ogni attivita' e' annuale. Da li' e' passato il
    difetto del D.T.B. trovato il 2026-08-24."""
    env = _scuola_multi_firma_fattibile()
    # se la fixture smettesse di avere due firme il test diventerebbe vacuo
    assert len(week_signatures(env["schedule"])) == 2

    soluzione = solve(env["schedule"], time_limit=30)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert len(soluzione.placements) == len(env["attivita"])
    apply(soluzione, env["schedule"])
    assert violazioni(env["schedule"], LEGALITA) == set()

    # la prova diretta che le due firme non sono state fuse: due attivita' di
    # settimane diverse condividono docente, classe e collocazione
    celle = {
        nome: (p.day, p.start_slot)
        for nome, att in env["attivita"].items()
        for p in [Placement.objects.get(schedule=env["schedule"], activity=att)]
    }
    assert celle["A5"] == (1, 0)
    assert celle["A6"] == (1, 0)
    # e A1 ha dovuto chiudere il buco della settimana 0, non aprirne uno
    assert celle["A1"] in {(0, 1), (1, 1)}


def _due_settimane_stessa_violazione():
    """Fissa la semantica di nuove() sul caso della review: una violazione
    max_gap identica per codice/risorsa/quantita' su due settimane diverse.
    Non passa dal solver — e' costruita a mano con Placement diretti, perche'
    qui l'oggetto sotto esame e' l'helper del test, non il solver.

    Griglia 1 giorno x 3 fasce, MAX_GAP_HOURS = 0 sulla classe (qualunque
    buco e' una violazione). Settimana 0: due attivita' piazzate a fascia 0 e
    2, buco alla fascia 1 → un finding max_gap su 'klass', quantities
    {gap_minutes: 60, max_gap_minutes: 0}. Settimana 1: due attivita' attive
    ma non ancora piazzate → nessuna occupazione, nessun buco, nessuna
    violazione — finche' il chiamante non le piazza con lo stesso schema.

    MaxGapChecker (domain/analysis/checkers/time_constraints.py) costruisce
    il finding senza 'activities' nella chiave (solo resources e quantities):
    piazzando A3/A4 con lo stesso buco, il finding della settimana 1 ha
    esattamente la stessa Finding.key di quello della settimana 0, e
    check_schedule li fonde in un solo oggetto con weeks=(0, 1)."""
    grid = TimeGrid.objects.create(
        days_per_cycle=1, slots_per_day=3, slot_minutes=60, morning_end_slot=3)
    year = SchoolYear.objects.create(
        start_date=dt.date(2026, 9, 14), end_date=dt.date(2026, 9, 27),
        first_week_monday=dt.date(2026, 9, 14),
    )
    period = Period.objects.create(
        school_year=year, name="P1", start_date=year.start_date, end_date=year.end_date)
    schedule = Schedule.objects.create(period=period)
    disc = Discipline.objects.create(code="LET", name="Lettere")
    subject = Subject.objects.create(code="ITA", name="Italiano", discipline=disc)
    plan = StudyPlan.objects.create(code="P1", name="Piano", year=1)
    klass = SchoolClass.objects.create(name="1A", study_plan=plan, year=1)
    teacher = Teacher.objects.create(name="Rossi Anna", last_name="Rossi", first_name="Anna")

    prima_settimana, seconda_settimana = weeks.single_week(0), weeks.single_week(1)
    a1 = make_activity(subject, teachers=[teacher], classes=[klass], mask=prima_settimana)
    a2 = make_activity(subject, teachers=[teacher], classes=[klass], mask=prima_settimana)
    a3 = make_activity(subject, teachers=[teacher], classes=[klass], mask=seconda_settimana)
    a4 = make_activity(subject, teachers=[teacher], classes=[klass], mask=seconda_settimana)

    ResourceTimeConstraint.objects.create(
        resource=klass, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})

    place(schedule, a1, day=0, slot=0)
    place(schedule, a2, day=0, slot=2)

    return {"schedule": schedule, "a3": a3, "a4": a4}


def test_nuove_vede_una_violazione_ripetuta_su_unaltra_settimana():
    """L'osservazione Important della review del Task 3: violazioni() riduce
    ogni finding alla sua Finding.key, che esclude 'weeks' per costruzione
    (e' pensata per il dedup fra firme dentro check_schedule). Senza
    l'espansione per settimana, una violazione preesistente in una firma e
    una identica — stesso codice/risorse/quantities — comparsa su un'altra
    firma si fondono in un solo finding con weeks allargato: la chiave era
    gia' in 'prima', quindi nuove() la perderebbe.

    Qui costruiamo esattamente quel caso: 'prima' cattura la violazione della
    settimana 0; poi piazziamo lo stesso schema di buco sulla settimana 1
    (stessa Finding.key, weeks diverso). Se nuove() operasse sulla sola
    chiave, il risultato sarebbe l'insieme vuoto — il finding "nuovo" e'
    identico a quello gia' visto. Con l'espansione per (chiave, settimana),
    nuove() deve vedere la settimana 1 come genuinamente nuova."""
    env = _due_settimane_stessa_violazione()
    schedule = env["schedule"]

    prima = violazioni(schedule, LEGALITA)
    assert len(prima) == 1
    (chiave, settimana), = prima
    assert chiave[0] == "max_gap"
    assert settimana == 0

    # stesso schema di buco, sulla settimana 1: stessa Finding.key di prima
    place(schedule, env["a3"], day=0, slot=0)
    place(schedule, env["a4"], day=0, slot=2)

    dopo = violazioni(schedule, LEGALITA)
    assert dopo == prima | {(chiave, 1)}

    trovate = nuove(schedule, prima, LEGALITA)
    assert trovate == {(chiave, 1)}


def test_fermi_intero_misurato():
    """Il Fermi ha le classi del triennio a 30 ore su una griglia di 30 fasce:
    non e' noto se sia fattibile. Qualunque cosa il solver restituisca, deve
    essere corretta — e le misure vanno riportate.

    ⚠⚠ **E qui la misura dice meno di quanto sembri, misurato al Task 17.** Il
    dataset Fermi ha **zero** righe `ResourceTimeConstraint`, **zero**
    `SubjectConstraint` e i quattro tetti di peso a `None`: delle ventisei
    famiglie modellate ne esercita **cinque** — griglia, indisponibilita' (42
    righe), occupazione, sedi e D.T.B. — e ventuno builder su ventisei non
    postano nulla. Il numero lo dimostrava: **8140 variabili e 1082
    constraint, identici a quelli dello spike a cinque vincoli** del
    2026-08-09, e lo stesso 0,56s.

    ⚠ Dal 2026-08-26 i numeri sono **8426 e 1086**, e la differenza e' tutta
    la macchina dello scarto e della catena, contata. Variabili: +284 booleani
    `piazzata` (uno per attivita' libera), +1 per i minuti scartati e +1 per il
    numero di attivita' scartate — i due livelli. Constraint: i 284
    `AddExactlyOne` diventano 284 `somma(celle) == piazzata` (netto zero), piu'
    le due uguaglianze dei livelli e i **due fissaggi** che la catena aggiunge
    percorrendola (`minuti <= v1`, `numero <= v2`). Il resto del modello e'
    identico a prima, ed e' la forma in cui «le quote a zero danno il modello
    di oggi» si vede su un dataset vero.

    Quindi «OPTIMAL sul Fermi col modello completo» **non e' una misura del
    modello completo**: e' una misura del dataset. La misura del modello sta
    in `tests/test_solver_witness.py::test_modello_completo`, dove ogni
    famiglia porta le proprie righe.

    Questo test resta per l'altra meta' — la scala. 284 attivita' su una
    griglia stretta sono il volume vero; il banco a testimone ne ha 14-32."""
    dataset = fermi.build()
    assert ResourceTimeConstraint.objects.count() == 0
    assert SubjectConstraint.objects.count() == 0
    soluzione = solve(dataset["schedule"], time_limit=120)
    print("\nFermi intero:", soluzione.status, soluzione.stats)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN")
    if soluzione.status in ("OPTIMAL", "FEASIBLE"):
        assert soluzione.placements
        # Il Fermi si piazza per intero: nessuna rinuncia. Se un giorno
        # comparisse uno scarto qui, sarebbe la notizia — non un dettaglio.
        assert soluzione.stats["scartate"] == 0, soluzione.stats
        assert soluzione.stats["variabili"] == 8426
        # ⚠ 1086 → 1116 da quando il Fermi chiede le aule. I +30 sono
        # l'occupazione di `PALESTRA` sulle 30 celle della griglia: MOT e' la
        # sola materia a **candidata unica**, e a candidata unica l'aula entra
        # gia' nei token del piazzamento (`_activity_tokens`), quindi diventa
        # una risorsa come il docente e la classe.
        #
        # ⚠ 1116 → 1536 con ADR-021, ed e' il prezzo di far **contare** le
        # aule alla fase 1. I +420 sono i tetti di `structural:room_pool`: i
        # quattro insiemi di candidate dichiarati dal dataset generano una
        # chiusura per unione di quindici, di cui quattordici con piu' di
        # un'aula (i singoletti non si postano — sono gia' occupazione), su 30
        # celle. Non tutti mordono, e quelli che non potrebbero mordere
        # nemmeno con tutte le attivita' insieme il builder li salta.
        assert soluzione.stats["constraint"] == 1536
        # i due livelli hanno concluso, e con l'ottimo dimostrato
        assert [l["nome"] for l in soluzione.stats["livelli"]] == [
            "minuti_scartati", "attivita_scartate"]
        assert all(l["ottimo"] and l["valore"] == 0
                   for l in soluzione.stats["livelli"])
        apply(soluzione, dataset["schedule"])
        assert violazioni(dataset["schedule"], LEGALITA) == set()


def test_il_tetto_inevadibile_non_e_una_violazione_nuova():
    """🔑 §9.5 del modello hard, chiuso da una misura invece che previsto.

    Due congelate gia' oltre il tetto settimanale di peso didattico, e una
    libera. Il `DidacticWeightBuilder` non posta il tetto — a sforarlo sono le
    congelate da sole, e pretenderne la riparazione e' la meta' vietata di
    ADR-018 — quindi la libera si piazza, e **ovunque si piazzi pesa**.
    Misurato: `activities (1, 2) → (1, 2, 3)`, `weight 6 → 9`, quattro
    settimane. `Finding.key` diversa in tutte e quattro, violazione la stessa.

    Senza la chiave grossolana l'oracolo dichiara rotto un solve impeccabile;
    con essa tace, perche' la coppia (causale, risorsa, settimana) era gia'
    rotta prima. ⚠ E una risorsa **pulita** resta protetta dalla chiave
    intera: lo prova la seconda meta' del test."""
    env = mini_school(days=2, slots=3)
    env["subject"].didactic_weight = 3
    env["subject"].save()
    env["klass"].max_weekly_weight_per_student = 3
    env["klass"].save()
    for day, slot in ((0, 0), (0, 1)):
        congelata = make_activity(
            env["subject"], classes=[env["klass"]],
            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], congelata, day, slot)
    make_activity(env["subject"], classes=[env["klass"]])

    prima = violazioni(env["schedule"])
    assert {k[0][0] for k in prima} == {"weight_week", "activity_unplaced"}

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.status == "OPTIMAL"
    apply(soluzione, env["schedule"])

    # La chiave intera vede quattro violazioni nuove; la grossolana nessuna.
    assert violazioni(env["schedule"]) - prima
    assert nuove(env["schedule"], prima) == set()


def test_la_chiave_grossolana_non_perdona_una_risorsa_pulita():
    """⚠ L'esenzione vale **solo** dove la coppia (causale, risorsa, settimana)
    era gia' rotta: altrimenti sarebbe un'amnistia per **famiglia**, cioe' un
    oracolo cieco su dieci causali su ventisei.

    Si asserisce la regola di `nuove()` invece di farla scattare da un solve, e
    non e' una scorciatoia: su `weight_week` una violazione nuova su una
    risorsa pulita **non e' costruibile**, perche' il builder il tetto lo posta
    esattamente quando le congelate non lo sforano — e allora il solver lo
    rispetta. La proprieta' da tenere ferma e' quindi quella dell'oracolo, e va
    interrogata dove vive."""
    env = mini_school(days=2, slots=3)
    env["subject"].didactic_weight = 3
    env["subject"].save()
    altra = SchoolClass.objects.create(name="1B", study_plan=env["plan"], year=1)
    for klass in (env["klass"], altra):
        klass.max_weekly_weight_per_student = 3
        klass.save()
        for day, slot in ((0, 0), (0, 1)):
            act = make_activity(env["subject"], classes=[klass],
                                immobility=Activity.Immobility.LOCKED_IN_PLACE)
            place(env["schedule"], act, day, slot)

    tutte = violazioni(env["schedule"])
    pesi = {k for k in tutte if k[0][0] == "weight_week"}
    assert len({k[0][1] for k in pesi}) == 2, "le due classi violano entrambe"

    # `prima` conosce una sola delle due risorse: l'altra e' pulita, e la sua
    # violazione dev'essere **nuova** anche se la famiglia e' grossolana.
    risorsa_nota = sorted({k[0][1] for k in pesi})[0]
    prima = {k for k in tutte
             if k[0][0] != "weight_week" or k[0][1] == risorsa_nota}
    residue = nuove(env["schedule"], prima)
    assert residue
    assert {k[0][0] for k in residue} == {"weight_week"}
    assert {k[0][1] for k in residue} == {sorted({k[0][1] for k in pesi})[1]}


def test_uno_scarto_nuovo_si_vede_anche_se_la_risorsa_era_gia_scoperta():
    """⚠ `activity_unplaced` è escluso dalle famiglie grossolane, e il perché
    va **asserito**, non solo scritto: sgrossarlo renderebbe l'oracolo cieco
    sull'unica cosa che il solver decide da sé.

    Le sue `resources` sono i token dell'attività, quindi due attività della
    stessa classe condividono la chiave grossolana. Qui la baseline ha già una
    non piazzata di quella classe, e il solve — che preferisce scartare
    un'ora invece di due (L1) — ne butta fuori un'**altra**: stessa causale,
    stesse risorse, stessa settimana. Con la chiave grossolana lo scarto nuovo
    sparirebbe dentro quello vecchio.

    ⚠ Trovato per mutazione: coprire `activity_unplaced` lasciava la suite
    verde in tutti e undici i test."""
    env = mini_school(days=1, slots=2)
    lunga = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    corta = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], corta, 0, 0)

    prima = violazioni(env["schedule"])
    assert {k[0][0] for k in prima} == {"activity_unplaced"}
    assert {k[0][2] for k in prima} == {(lunga.pk,)}

    soluzione = solve(env["schedule"], workers=1)
    assert soluzione.unplaced == (corta.pk,), (
        "L1 conta le ore: scartare la corta costa 60', la lunga 120'")
    apply(soluzione, env["schedule"])

    residue = nuove(env["schedule"], prima)
    assert {k[0][2] for k in residue} == {(corta.pk,)}
