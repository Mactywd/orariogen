"""La quadratura del carico (L10): il dichiarato contro l'erogato.

⚠ **Qui sta la prova, non sul banco.** Sull'Alighieri le cattedre si *derivano*
da `EROGAZIONI`, cioè dalla stessa tabella che genera le attività, quindi là
`structural:workload` non può fallire: quel dataset è il **controllo su scala**
— 23 docenti, 144 cattedre, zero scostamenti — e la prova è il testimone
puntato, scritto discorde apposta, con il suo ramo di controllo accanto."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.registry import REGISTRY
from domain.models import (
    ClassPart, ClassPartition, Group, SchoolClass, Subject, TeachingAssignment,
)
from tests import alighieri, fermi
from tests.analysis_helpers import FULL, make_activity, mini_school, place

pytestmark = pytest.mark.django_db


def _quadratura(schedule):
    return [f for f in check_schedule(schedule) if f.code == "workload_mismatch"]


def _parti(klass, *nomi, partizione="P"):
    partition = ClassPartition.objects.create(school_class=klass, name=partizione)
    return [ClassPart.objects.create(name=n, partition=partition) for n in nomi]


# --------------------------------------------------------------------------
# il testimone puntato: due dichiarazioni discordi, e il ramo che le accorda


def test_la_cattedra_che_dice_meno_di_quel_che_si_insegna():
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=120,
    )
    (f,) = _quadratura(env["schedule"])
    assert f.quantities == {"declared_minutes": 120, "actual_minutes": 60}
    assert "Rossi Anna" in f.message and "1A" in f.message


def test_il_ramo_di_controllo_la_cattedra_che_quadra():
    """Senza questo ramo «il difetto non c'è più» sarebbe soddisfatto anche da
    un checker che non guarda niente."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=60,
    )
    assert _quadratura(env["schedule"]) == []


# --------------------------------------------------------------------------
# il docente non dichiarato tace — e non perché il checker sia spento


def test_un_docente_senza_cattedre_non_e_sbilanciato():
    """È *non dichiarato*, che è una condizione diversa e precedente. Senza
    questa regola ogni frammento di test con un'attività e nessuna cattedra
    direbbe «manca un'ora» dove manca l'anagrafica."""
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    assert TeachingAssignment.objects.count() == 0
    assert _quadratura(env["schedule"]) == []


def test_ma_basta_una_cattedra_perche_tutte_le_sue_ore_si_contino():
    """Il controllo del precedente: lo stesso docente, la stessa attività non
    dichiarata, più **una** riga altrove. Ora il silenzio finisce."""
    env = mini_school()
    altra = SchoolClass.objects.create(name="1B", study_plan=env["plan"], year=1)
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=altra, weekly_minutes=60,
    )
    scarti = {f.quantities["declared_minutes"]: f.quantities["actual_minutes"]
              for f in _quadratura(env["schedule"])}
    assert scarti == {0: 60, 60: 0}   # l'ora erogata a 1A, quella dichiarata su 1B


# --------------------------------------------------------------------------
# la forma: una classe non è la sua parte, e un raggruppamento non è una classe


def test_la_cattedra_sulla_classe_non_copre_l_ora_sulla_parte():
    env = mini_school()
    (ord_,) = _parti(env["klass"], "1A_ORD")
    make_activity(env["subject"], teachers=[env["teacher"]], parts=[ord_])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=60,
    )
    unita = {f.message.split(" su ")[1].split(":")[0] for f in _quadratura(env["schedule"])}
    assert unita == {"1A", "1A_ORD"}


def test_e_il_ramo_di_controllo_la_cattedra_sulla_parte():
    env = mini_school()
    (ord_,) = _parti(env["klass"], "1A_ORD")
    make_activity(env["subject"], teachers=[env["teacher"]], parts=[ord_])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        class_part=ord_, weekly_minutes=60,
    )
    assert _quadratura(env["schedule"]) == []


def test_il_raggruppamento_trasversale_e_il_caso_che_decide():
    """NOVEL non insegna «l'inglese della 1A»: insegna a metà 1A più metà 1B.
    Dichiararlo sulla classe fa quadrare i totali — due errori si annullano —
    e manda il supplente nella classe sbagliata, senza nominare l'altra."""
    env = mini_school()
    altra = SchoolClass.objects.create(name="1B", study_plan=env["plan"], year=1)
    (a1,) = _parti(env["klass"], "1A_ING_B")
    (b1,) = _parti(altra, "1B_ING_B")
    gruppo = Group.objects.create(name="ING1-BASE")
    gruppo.parts.add(a1, b1)
    make_activity(env["subject"], teachers=[env["teacher"]], groups=[gruppo])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=60,
    )
    unita = {f.message.split(" su ")[1].split(":")[0] for f in _quadratura(env["schedule"])}
    assert unita == {"1A", "ING1-BASE"}


def test_e_il_ramo_di_controllo_la_cattedra_sul_raggruppamento():
    env = mini_school()
    altra = SchoolClass.objects.create(name="1B", study_plan=env["plan"], year=1)
    (a1,) = _parti(env["klass"], "1A_ING_B")
    (b1,) = _parti(altra, "1B_ING_B")
    gruppo = Group.objects.create(name="ING1-BASE")
    gruppo.parts.add(a1, b1)
    make_activity(env["subject"], teachers=[env["teacher"]], groups=[gruppo])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        group=gruppo, weekly_minutes=60,
    )
    assert _quadratura(env["schedule"]) == []


# --------------------------------------------------------------------------
# la settimana: il quindicinale non costa un'ora


def test_l_ora_quindicinale_non_raddoppia():
    """La quinta forma di erogazione — due metà a maschere complementari — è la
    sola che *non costa un'ora*. Letta per firma di settimana quadra; sommando
    le durate darebbe il doppio, ed è la stessa trappola che `CoverageChecker`
    documenta per i quadrimestri."""
    env = mini_school()
    pari = sum(1 << w for w in range(0, 4, 2))
    dispari = sum(1 << w for w in range(1, 4, 2))
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], mask=pari)
    b = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], mask=dispari)
    # ⚠ La trappola, detta come numero: sommare le durate dà 120.
    assert a.duration_minutes + b.duration_minutes == 120
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=60,
    )
    assert _quadratura(env["schedule"]) == []


def test_e_il_ramo_di_controllo_due_ore_piene_costano_due_ore():
    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]], mask=FULL)
    make_activity(env["subject"], teachers=[env["teacher"]],
                  classes=[env["klass"]], mask=FULL)
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=60,
    )
    (f,) = _quadratura(env["schedule"])
    assert f.quantities == {"declared_minutes": 60, "actual_minutes": 120}


# --------------------------------------------------------------------------
# l'identità del verdetto


def test_dodici_unita_identiche_non_collassano_in_un_finding():
    """Il cappellano: dodici classi, stessa causale, stesso docente, stessa
    materia, `60 → 0` su ognuna. Senza l'unità fra le risorse sarebbero **un**
    finding, e quale delle dodici sopravvivesse dipenderebbe dall'ordine di
    iterazione. È il difetto che `Finding.key` documenta su `coverage_mismatch`."""
    env = mini_school()
    for n in range(12):
        klass = (env["klass"] if n == 0
                 else SchoolClass.objects.create(
                     name=f"C{n}", study_plan=env["plan"], year=1))
        TeachingAssignment.objects.create(
            teacher=env["teacher"], subject=env["subject"],
            school_class=klass, weekly_minutes=60,
        )
    findings = _quadratura(env["schedule"])
    assert len(findings) == 12
    assert len({f.key for f in findings}) == 12


def test_due_materie_sulla_stessa_unita_non_collassano():
    env = mini_school()
    altra = Subject.objects.create(code="STO", name="Storia",
                                   discipline=env["discipline"])
    for materia in (env["subject"], altra):
        TeachingAssignment.objects.create(
            teacher=env["teacher"], subject=materia,
            school_class=env["klass"], weekly_minutes=60,
        )
    assert len({f.key for f in _quadratura(env["schedule"])}) == 2


# --------------------------------------------------------------------------
# la natura del checker


def test_e_indipendente_dal_piazzamento():
    """Nessuna collocazione crea o ripara uno scostamento: il carico è la somma
    delle durate. È la ragione per cui non ha un builder."""
    env = mini_school()
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=120,
    )
    prima = {f.key for f in _quadratura(env["schedule"])}
    place(env["schedule"], a, day=0, slot=0)
    assert {f.key for f in _quadratura(env["schedule"])} == prima
    assert REGISTRY["structural:workload"].PLACEMENT_INDEPENDENT


def test_il_checker_e_nel_registro_e_non_ha_builder():
    from domain.solver.registry import BUILDERS, all_builders
    all_builders()
    assert "structural:workload" in REGISTRY
    assert "structural:workload" not in BUILDERS


# --------------------------------------------------------------------------
# il controllo su scala: le due scuole quadrano


def test_l_alighieri_quadra():
    env = alighieri.build()
    assert _quadratura(env["schedule"]) == []
    assert TeachingAssignment.objects.filter(class_part__isnull=False).count() == 30
    assert TeachingAssignment.objects.filter(group__isnull=False).count() == 2


def test_il_comando_analyze_lo_dice_e_fallisce():
    """La quadratura è **HARD**, quindi `analyze` esce con codice ≠ 0: una
    cattedra che non torna è un dato da correggere *prima* di calcolare, non un
    difetto dell'orario. ⚠ Su nessuna delle due scuole vere la quadratura
    contribuisce a quel conteggio — lo dicono i due test in coda — che è la
    ragione per cui questa severità non cambia nulla in CI."""
    from io import StringIO
    from django.core.management import call_command
    from django.core.management.base import CommandError

    env = mini_school()
    make_activity(env["subject"], teachers=[env["teacher"]], classes=[env["klass"]])
    TeachingAssignment.objects.create(
        teacher=env["teacher"], subject=env["subject"],
        school_class=env["klass"], weekly_minutes=120,
    )
    # ⚠ `--schedule`: senza, `analyze` legge la sola anagrafica e i finding
    # non si valutano affatto. La quadratura è un predicato sui dati, ma il
    # comando la raggiunge per la via dello stato come tutte le altre.
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("analyze", "--schedule", str(env["schedule"].pk), stdout=out)
    testo = out.getvalue()
    assert "ore dichiarate dalla cattedra diverse da quelle erogate" in testo
    assert "declared_minutes=120" in testo and "actual_minutes=60" in testo


def test_il_fermi_quadra():
    """⚠ E quadrava già: il Fermi non ha partizioni, quindi non aveva modo di
    sbagliare forma. È la stessa ragione per cui non aveva trovato L4."""
    env = fermi.build()
    assert _quadratura(env["schedule"]) == []
