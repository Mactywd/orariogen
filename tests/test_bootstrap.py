"""`Ricava`: la derivazione da una griglia piatta (ADR-028, gradino 1).

I test sintetici provano **un meccanismo per volta**, ognuno col suo ramo di
controllo — perché «il rilevatore ha trovato lo sdoppiamento» è soddisfatto
anche da un rilevatore che dice sempre di sì. Il giro sul banco prova i numeri
che l'ADR dichiara.
"""

import pytest

from domain.bootstrap import Lezione, applica, ricava


def _g(*righe):
    return [Lezione(*r) for r in righe]


# --- Ciò che si legge ---------------------------------------------------------

def test_una_griglia_semplice_si_legge_tutta():
    p = ricava(_g(("ROSSI", 0, 0, "1A", "MAT"),
                  ("ROSSI", 0, 1, "1A", "MAT"),
                  ("BIANCHI", 1, 0, "1A", "ITA")))
    assert p.teachers == ("BIANCHI", "ROSSI")
    assert p.classes == ("1A",)
    assert p.subjects == ("ITA", "MAT")
    assert (p.days, p.slots_per_day) == (2, 2)
    assert p.assignments == {("ROSSI", "1A", "MAT"): 2, ("BIANCHI", "1A", "ITA"): 1}
    assert p.curriculum == {"1A": {"MAT": 2, "ITA": 1}}
    assert p.splits == () and p.groupings == ()


def test_una_lezione_senza_materia_conta_per_il_docente_e_non_per_il_quadro():
    """La materia è l'unico dei cinque ruoli che il descrittore di Aurora non
    pretende. Chi non la dichiara dice che qualcuno insegna, non cosa."""
    p = ricava(_g(("ROSSI", 0, 0, "1A", None), ("ROSSI", 0, 1, "1A", "MAT")))
    assert p.assignments[("ROSSI", "1A", None)] == 1
    assert p.curriculum == {"1A": {"MAT": 1}}   # la cella senza materia non c'è
    assert p.subjects == ("MAT",)


# --- Lo sdoppiamento, e il suo ramo di controllo ------------------------------

def test_due_lezioni_nella_stessa_cella_sono_uno_sdoppiamento():
    p = ricava(_g(("ROSSI", 0, 0, "1A", "ING"),
                  ("BIANCHI", 0, 0, "1A", "ING")))
    assert len(p.splits) == 1
    s = p.splits[0]
    assert (s.school_class, s.subject, s.streams) == ("1A", "ING", 2)
    assert s.cells == ((0, 0),)
    # 🔑 E il quadro conta **una** ora, non due: l'alunno ne frequenta una.
    assert p.curriculum == {"1A": {"ING": 1}}
    # Le cattedre invece ne contano una per ciascuno: il servizio è di entrambi.
    assert p.assignments == {("ROSSI", "1A", "ING"): 1, ("BIANCHI", "1A", "ING"): 1}
    assert p.uncertain_classes == ("1A",)


def test_le_stesse_due_lezioni_in_celle_diverse_non_lo_sono():
    """Il ramo di controllo. Senza collisione non c'è niente da vedere, e il
    quadro dice **due** ore — che è la risposta giusta se davvero sono due, e
    quella sbagliata se è un turno di laboratorio. È la cecità dichiarata."""
    p = ricava(_g(("ROSSI", 0, 0, "1A", "ING"),
                  ("BIANCHI", 0, 1, "1A", "ING")))
    assert p.splits == ()
    assert p.curriculum == {"1A": {"ING": 2}}
    assert p.uncertain_classes == ()


def test_il_turno_di_laboratorio_non_si_vede_ed_e_dichiarato():
    """Le due metà con lo **stesso** docente non possono essere simultanee, e
    quindi non collidono. Sono le due mancate del banco, e la ragione per cui
    `CECITA` esiste."""
    p = ricava(_g(("TOSI", 0, 0, "3A", "SCI"), ("TOSI", 0, 1, "3A", "SCI")))
    assert p.splits == ()
    assert p.curriculum == {"3A": {"SCI": 2}}
    assert "turno_di_laboratorio" in dict(p.cecita)


def test_l_unita_della_cattedra_non_si_legge_ed_e_dichiarata():
    """La quarta cecità (ADR-030). La griglia dice *chi insegna dove*, non *a
    quanti*: due docenti nella stessa cella della stessa classe sono un
    sospetto di sdoppiamento — `groupings` lo raccoglie — ma un sospetto non è
    una parte, e le cattedre restano a classe intera.

    ⚠ Il ramo di controllo è che la cattedra c'è comunque, e giusta nelle ore:
    la cecità è sull'**unità**, non sul carico."""
    p = ricava(_g(("ROSSI", 0, 0, "1A", "ING"), ("ROSSI", 0, 1, "1A", "ING")))
    assert p.assignments == {("ROSSI", "1A", "ING"): 2}
    assert "unita_della_cattedra" in dict(p.cecita)
    assert len(p.cecita) == 4


# --- Il raggruppamento trasversale, e il suo ramo di controllo -----------------

def test_un_docente_in_due_classi_nella_stessa_cella_e_un_raggruppamento():
    p = ricava(_g(("ROSSI", 0, 0, "1A", "ING"),
                  ("ROSSI", 0, 0, "1B", "ING")))
    assert len(p.groupings) == 1
    r = p.groupings[0]
    assert (r.teacher, r.subject, r.classes) == ("ROSSI", "ING", ("1A", "1B"))
    # ⚠ E non è uno sdoppiamento: nessuna delle due classi ha due lezioni.
    assert p.splits == ()
    # Due cattedre, una per classe: è così che la griglia lo registra.
    assert p.assignments == {("ROSSI", "1A", "ING"): 1, ("ROSSI", "1B", "ING"): 1}


def test_lo_stesso_docente_in_due_classi_in_celle_diverse_no():
    p = ricava(_g(("ROSSI", 0, 0, "1A", "ING"),
                  ("ROSSI", 0, 1, "1B", "ING")))
    assert p.groupings == ()


# --- `applica` ----------------------------------------------------------------

@pytest.mark.django_db
def test_applica_scrive_anagrafica_piani_e_cattedre():
    from domain.models import (SchoolClass, Service, StudyPlan, Subject,
                               Teacher, TeachingAssignment, TimeGrid)
    p = ricava(_g(("ROSSI", 0, 0, "1A", "MAT"),
                  ("ROSSI", 0, 1, "1A", "MAT"),
                  ("BIANCHI", 1, 0, "1A", "ITA")))
    applica(p)
    assert Teacher.objects.count() == 2
    assert Subject.objects.count() == 2
    assert SchoolClass.objects.get().name == "1A"
    assert SchoolClass.objects.get().year == 1        # dedotto dal nome
    griglia = TimeGrid.objects.get()
    assert (griglia.days_per_cycle, griglia.slots_per_day) == (2, 2)
    # ⚠ Senza linea dichiarata la giornata è tutta mattina.
    assert griglia.morning_end_slot == 2
    assert {(s.subject.code, s.class_minutes) for s in Service.objects.all()} == {
        ("MAT", 120), ("ITA", 60)}
    assert {(t.teacher.name, t.weekly_minutes) for t in TeachingAssignment.objects.all()} == {
        ("ROSSI", 120), ("BIANCHI", 60)}
    assert StudyPlan.objects.count() == 1


@pytest.mark.django_db
def test_due_classi_con_lo_stesso_quadro_restano_due_piani():
    """Il ramo che tiene ferma la scelta: raggruppare per profilo sembra
    economico ed è una perdita — sull'Alighieri i profili distinti sono **9
    contro 11 piani**. Fondere è una decisione della scuola, e da un piano per
    classe la si può sempre prendere; dal contrario non si torna indietro."""
    from domain.models import StudyPlan
    p = ricava(_g(("ROSSI", 0, 0, "1A", "MAT"), ("ROSSI", 0, 1, "1B", "MAT")))
    applica(p)
    assert StudyPlan.objects.count() == 2


@pytest.mark.django_db
def test_applica_rifiuta_un_database_gia_popolato():
    p = ricava(_g(("ROSSI", 0, 0, "1A", "MAT")))
    applica(p)
    with pytest.raises(ValueError, match="non è vuoto"):
        applica(p)
    applica(p, replace=True)          # il ramo di controllo: chiedendolo, si può
    from domain.models import Teacher
    assert Teacher.objects.count() == 1


@pytest.mark.django_db
def test_la_disciplina_e_l_unico_dato_inventato():
    """`Subject.discipline` è obbligatoria e la griglia non ne parla. Il codice
    è visibile apposta: assegnarla è un lavoro umano (ADR-001)."""
    from domain.models import Discipline, Subject
    applica(ricava(_g(("ROSSI", 0, 0, "1A", "MAT"))))
    assert Discipline.objects.get().code == "ND"
    assert Subject.objects.get().discipline.code == "ND"


# --- Il giro sul banco: i numeri che ADR-028 dichiara -------------------------

def _griglia_da(placements):
    """L'orario risolto, appiattito nella forma di `ScheduleEntry`.

    È la **pubblicazione** di ADR-027 §3.2 in miniatura: una parte di classe
    diventa la sua classe, un raggruppamento diventa le classi delle sue parti,
    e la maschera di settimana sparisce — perché la griglia di Aurora non ha un
    asse su cui metterla.
    """
    from domain.models import Activity
    righe = []
    for a in Activity.objects.prefetch_related(
            "teachers", "classes", "parts__partition__school_class",
            "groups__parts__partition__school_class"):
        if a.pk not in placements:
            continue
        giorno, inizio = placements[a.pk]
        classi = {c.name for c in a.classes.all()}
        for p in a.parts.all():
            classi.add(p.partition.school_class.name)
        for g in a.groups.all():
            for p in g.parts.all():
                classi.add(p.partition.school_class.name)
        for t in a.teachers.all():
            for c in classi:
                for k in range(a.duration_slots):
                    righe.append(Lezione(t.name, giorno, inizio + k, c, a.subject.code))
    return righe


def _verita_sdoppiamenti():
    from domain.models import Activity
    vere = set()
    for a in Activity.objects.prefetch_related(
            "parts__partition__school_class", "groups__parts__partition__school_class"):
        for p in a.parts.all():
            vere.add((p.partition.school_class.name, a.subject.code))
        for g in a.groups.all():
            for p in g.parts.all():
                vere.add((p.partition.school_class.name, a.subject.code))
    return vere


def _quadri_veri():
    from domain.models import SchoolClass, Service
    return {c.name: {s.subject.code: s.class_minutes // 60
                     for s in Service.objects.filter(study_plan=c.study_plan)
                     .select_related("subject")}
            for c in SchoolClass.objects.select_related("study_plan")}


def _cattedre_vere():
    """Le cattedre appiattite sulla stessa chiave: la parte diventa la sua
    classe, il gruppo le classi delle sue parti."""
    from collections import defaultdict
    from domain.models import TeachingAssignment
    vere = defaultdict(int)
    for ta in (TeachingAssignment.objects
               .select_related("teacher", "subject", "school_class",
                               "class_part__partition__school_class")
               .prefetch_related("group__parts__partition__school_class")):
        classi = set()
        if ta.school_class_id:
            classi.add(ta.school_class.name)
        if ta.class_part_id:
            classi.add(ta.class_part.partition.school_class.name)
        if ta.group_id:
            for p in ta.group.parts.all():
                classi.add(p.partition.school_class.name)
        for c in classi:
            vere[(ta.teacher.name, c, ta.subject.code)] += ta.weekly_minutes // 60
    return dict(vere)


@pytest.mark.django_db
def test_banco_le_cattedre_si_leggono_i_quadri_no():
    """🔑 Il numero su cui poggia ADR-028, in tutt'e due i versi.

    Le cattedre tornano quasi tutte perché la griglia le contiene davvero. I
    quadri no, e i quattro che restano storti sono **quattro meccanismi
    diversi**, tutti fuori dalla portata di una griglia settimanale.

    ⚠ I numeri sono stabili perché lo sono **per costruzione, non per
    fortuna**: le due metà di uno sdoppiamento sono allineate (L5), quindi
    sempre simultanee, e il turno di laboratorio ha un docente solo, quindi
    non lo è mai. Misurato su cinque ottimi distinti a otto lavoratori.
    """
    from tests import alighieri
    from domain.solver.model import solve
    env = alighieri.build()
    r = solve(env["schedule"], workers=8, time_limit=180, allow_unplaced=False)
    assert r.status == "OPTIMAL", r.stats

    p = ricava(_griglia_da(r.placements))

    # --- Le cattedre: si leggono.
    vere = _cattedre_vere()
    chiavi = set(p.assignments) | set(vere)
    identiche = {k for k in chiavi if p.assignments.get(k, 0) == vere.get(k, 0)}
    assert len(chiavi) == 142
    # 🔑 **141 e non 139 da ADR-030**: le due che tornavano storte erano il
    # raggruppamento trasversale, dove la cattedra diceva «NOVEL fa l'inglese
    # della 1A» mentre la griglia mostrava metà 1A e metà 1B. `ricava`, che
    # legge l'orario vero, aveva **ragione**; era la dichiarazione a sbagliare.
    # ⚠ E l'unica che resta storta è ora esattamente la cecità dichiarata del
    # gradino 1: l'ora quindicinale del 5B, tre ore nella griglia piatta dove
    # la settimana ne porta due. Una griglia settimanale non ha modo di
    # vederlo.
    assert len(identiche) == 141

    # --- I quadri: si indovinano, e contare le celle è ciò che li porta a 8.
    quadri = _quadri_veri()
    esatti = {c for c in p.classes if p.curriculum.get(c, {}) == quadri[c]}
    assert len(esatti) == 8, sorted(set(p.classes) - esatti)
    # I quattro storti, uno per meccanismo: turno di laboratorio (3A, 4A),
    # ora quindicinale (5B), classe articolata (2C).
    assert set(p.classes) - esatti == {"3A", "4A", "5B", "2C"}


@pytest.mark.django_db
def test_banco_il_rilevatore_e_sicuro_ma_non_completo():
    from tests import alighieri
    from domain.solver.model import solve
    env = alighieri.build()
    r = solve(env["schedule"], workers=8, time_limit=180, allow_unplaced=False)
    p = ricava(_griglia_da(r.placements))

    trovate = {(s.school_class, s.subject) for s in p.splits}
    vere = _verita_sdoppiamenti()
    assert len(trovate & vere) == 28
    assert trovate - vere == set()                       # sicuro
    assert vere - trovate == {("3A", "SCI"), ("4A", "SCI")}   # non completo
    # I due raggruppamenti trasversali del banco, trovati come tali.
    assert len(p.groupings) == 2


@pytest.mark.django_db
def test_fermi_il_ramo_di_controllo_del_rilevatore():
    """Senza il Fermi il rilevatore non è misurato: sul banco **ogni** classe è
    sdoppiata, quindi «12 su 12» lo prenderebbe anche un rilevatore che dice
    sempre di sì. Qui le partizioni sono zero, e i sospetti devono essere zero."""
    from tests import fermi
    from domain.models import ClassPartition
    from domain.solver.model import solve
    env = fermi.build()
    assert ClassPartition.objects.count() == 0
    r = solve(env["schedule"], workers=8, time_limit=180, allow_unplaced=False)
    p = ricava(_griglia_da(r.placements))
    assert p.splits == ()
    assert p.groupings == ()
    # E i quadri del Fermi tornano **tutti**, perché non c'è niente da perdere.
    quadri = _quadri_veri()
    assert all(p.curriculum.get(c, {}) == quadri[c] for c in p.classes)


# --- Il comando ---------------------------------------------------------------

def _scrivi(tmp_path, righe):
    import json
    f = tmp_path / "griglia.json"
    f.write_text(json.dumps(righe), encoding="utf-8")
    return str(f)


@pytest.mark.django_db
def test_comando_di_suo_non_scrive(tmp_path):
    """La disciplina del giudice: si guarda prima di scrivere."""
    import io
    from django.core.management import call_command
    from domain.models import Teacher
    out = io.StringIO()
    call_command("bootstrap", _scrivi(tmp_path, [
        {"teacher": "ROSSI", "day": 0, "slot": 0, "class": "1A", "subject": "MAT"}]),
        stdout=out)
    assert Teacher.objects.count() == 0
    assert "Niente è stato scritto" in out.getvalue()


@pytest.mark.django_db
def test_comando_applica_e_nomina_la_cecita(tmp_path):
    import io
    from django.core.management import call_command
    from domain.models import Teacher
    out = io.StringIO()
    call_command("bootstrap", _scrivi(tmp_path, [
        {"docente": "ROSSI", "giorno": "monday", "ora": 0, "classe": "1A", "materia": "ING"},
        {"docente": "BIANCHI", "giorno": "monday", "ora": 0, "classe": "1A", "materia": "ING"}]),
        "--applica", stdout=out)
    testo = out.getvalue()
    assert Teacher.objects.count() == 2
    # I nomi italiani dei ruoli e i giorni inglesi di Aurora, tutti e due accettati.
    assert "Sdoppiamenti visti" in testo
    assert "turno_di_laboratorio" in testo   # la cecità si stampa sempre
    assert "Scritto." in testo


@pytest.mark.django_db
def test_comando_rifiuta_una_riga_senza_i_quattro_ruoli(tmp_path):
    from django.core.management import call_command
    from django.core.management.base import CommandError
    with pytest.raises(CommandError, match="manca il ruolo"):
        call_command("bootstrap", _scrivi(tmp_path, [
            {"teacher": "ROSSI", "day": 0, "slot": 0}]))


def test_la_compresenza_da_lo_stesso_numero_con_un_altro_nome():
    """🔑 Due docenti in una cella sono due mezze classi **oppure** una
    compresenza, e la griglia non lo dice. Ma il quadro non se ne accorge: in
    tutt'e due i casi l'alunno fa un'ora. L'incertezza è sull'etichetta."""
    p = ricava(_g(("ROSSI", 0, 0, "1A", "FIS"), ("VERDI", 0, 0, "1A", "FIS")))
    assert p.curriculum == {"1A": {"FIS": 1}}
    assert p.assignments == {("ROSSI", "1A", "FIS"): 1, ("VERDI", "1A", "FIS"): 1}


@pytest.mark.django_db
def test_applica_rifiuta_una_proposta_vuota():
    with pytest.raises(ValueError, match="vuota"):
        applica(ricava([]))


def test_una_riga_ripetuta_non_diventa_uno_sdoppiamento():
    """⚠ Il caso che romperebbe la proprietà su cui poggia il rilevatore. Due
    righe identiche dicono la stessa cosa due volte — un file vero lo fa — e
    senza fonderle regalerebbero un'ora alla cattedra **e** un falso allarme."""
    p = ricava(_g(("ROSSI", 0, 0, "1A", "MAT"), ("ROSSI", 0, 0, "1A", "MAT")))
    assert p.splits == ()
    assert p.assignments == {("ROSSI", "1A", "MAT"): 1}
    assert p.curriculum == {"1A": {"MAT": 1}}


def test_ma_due_docenti_diversi_nella_stessa_cella_restano_due():
    """Il ramo di controllo della fusione: si fondono le righe **identiche**,
    non le lezioni simultanee."""
    p = ricava(_g(("ROSSI", 0, 0, "1A", "MAT"), ("VERDI", 0, 0, "1A", "MAT")))
    assert len(p.splits) == 1
    assert len(p.assignments) == 2
