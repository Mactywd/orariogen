"""La pubblicazione: da `Placement` alla griglia piatta di Aurora (ADR-027 §3.2).

🔑 **Ogni perdita ha il suo ramo di controllo.** «La parte esce come la classe»
è soddisfatto anche da una pubblicazione che non esce affatto, quindi accanto
a ogni caso che perde ne sta uno che non perde, sullo stesso banco.
"""
import datetime as dt

import pytest

from domain.models import ClassPart, ClassPartition, Group, SchoolClass, Subject, Teacher
from domain.publication import GIORNI, pubblica, settimane_iso
from tests.analysis_helpers import FULL, make_activity, mini_school, place

pytestmark = pytest.mark.django_db

#: Le quattro settimane di `mini_school`, nell'indice di Aurora.
ISO = {0: 38, 1: 39, 2: 40, 3: 41}


def _bit(*settimane):
    m = 0
    for w in settimane:
        m |= 1 << ISO[w]
    return m


def _parti(klass, nomi=("A", "B")):
    p = ClassPartition.objects.create(school_class=klass, name="Lingue")
    return [ClassPart.objects.create(name=f"{klass.name}-{n}", partition=p)
            for n in nomi]


# --- la forma della riga ----------------------------------------------------

def test_una_lezione_diventa_una_riga():
    s = mini_school()
    a = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], a, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert len(righe) == 1
    r = righe[0]
    assert (r.teacher, r.weekday, r.school_class, r.subject) == (
        "Rossi Anna", "monday", "1A", "ITA")
    # ⚠ Aurora conta le ore da 1, noi le fasce da 0.
    assert r.period_number == 1
    assert perdita.vuota


def test_un_attivita_di_due_ore_diventa_due_righe_consecutive():
    """La durata è un campo da noi e non esiste in Aurora: si srotola."""
    s = mini_school()
    a = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]],
                      slots=2)
    place(s["schedule"], a, day=1, slot=2)

    righe, perdita = pubblica(s["schedule"])

    assert [r.period_number for r in righe] == [3, 4]
    assert {r.weekday for r in righe} == {"tuesday"}
    assert perdita.vuota


# --- le perdite, e i loro rami di controllo ---------------------------------

def test_la_parte_di_classe_esce_come_la_sua_classe():
    s = mini_school()
    a, b = _parti(s["klass"])
    att = make_activity(s["subject"], teachers=[s["teacher"]], parts=[a])
    place(s["schedule"], att, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    # Vera e incompleta: Aurora vede «1A», dove è mezza 1A. Il supplente serve
    # comunque, ed è l'approssimazione che ADR-027 accetta **nominandola**.
    assert [r.school_class for r in righe] == ["1A"]
    assert perdita.parti == 1


def test_il_ramo_di_controllo_una_classe_intera_non_perde_niente():
    s = mini_school()
    att = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], att, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert [r.school_class for r in righe] == ["1A"]
    assert perdita.parti == 0 and perdita.vuota


def test_il_raggruppamento_esce_come_tutte_le_classi_che_tocca():
    """Il caso che una griglia piatta non ha modo di rappresentare: un docente
    su mezza 1A e mezza 1B nella stessa ora."""
    s = mini_school()
    altra = SchoolClass.objects.create(name="1B", study_plan=s["plan"], year=1)
    (a1, _), (b1, _) = _parti(s["klass"]), _parti(altra)
    g = Group.objects.create(name="Inglese avanzato")
    g.parts.add(a1, b1)
    att = make_activity(s["subject"], teachers=[s["teacher"]], groups=[g])
    place(s["schedule"], att, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert sorted(r.school_class for r in righe) == ["1A", "1B"]
    assert perdita.gruppi == 1


def test_il_sabato_non_esce_e_si_conta():
    """⚠ `ScheduleEntry.WEEKDAY_CHOICES` ha cinque giorni. Una scuola che fa
    sei giorni oggi non è pubblicabile, e il modo giusto di dirlo non è
    scrivere il sabato di lunedì."""
    s = mini_school(days=6)
    att = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], att, day=5, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert righe == []
    assert perdita.fuori_settimana == 1
    assert len(GIORNI) == 5


def test_il_ramo_di_controllo_il_venerdi_esce():
    s = mini_school(days=6)
    att = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], att, day=4, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert [r.weekday for r in righe] == ["friday"]
    assert perdita.fuori_settimana == 0


def test_l_attivita_senza_docente_non_esce_e_si_conta():
    """`ScheduleEntry.teacher` è obbligatoria: una riga senza docente non
    esiste, e l'ora sparisce dall'orario della classe."""
    s = mini_school()
    att = make_activity(s["subject"], classes=[s["klass"]])
    place(s["schedule"], att, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert righe == []
    assert perdita.senza_docente == 1


def test_due_materie_nella_stessa_cella_sono_una_cella_ambigua():
    """⚠ L'unicità di Aurora è `(docente, giorno, ora, classe, maschera)`: non
    porta la materia. Due parti della stessa classe, stesso docente, materie
    diverse, stessa ora — legittimo da noi, **inscrivibile** là. Non si sceglie
    quale vince: non esce nessuna delle due e la cella si nomina."""
    s = mini_school()
    a, b = _parti(s["klass"])
    altra = Subject.objects.create(code="STO", name="Storia",
                                   discipline=s["discipline"])
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       parts=[a]), day=0, slot=0)
    place(s["schedule"], make_activity(altra, teachers=[s["teacher"]],
                                       parts=[b]), day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert righe == []
    assert len(perdita.celle_ambigue) == 1
    chiave, materie = perdita.celle_ambigue[0]
    assert chiave == ("Rossi Anna", "monday", 1, "1A")
    assert materie == ["ITA", "STO"]


def test_il_ramo_di_controllo_la_stessa_materia_si_fonde_in_una_riga():
    """Due parti, stesso docente, **stessa** materia: là è una riga sola, e
    fonderle è giusto — Aurora leggerebbe due volte la stessa lezione."""
    s = mini_school()
    a, b = _parti(s["klass"])
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       parts=[a]), day=0, slot=0)
    place(s["schedule"], make_activity(s["subject"], teachers=[s["teacher"]],
                                       parts=[b]), day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert len(righe) == 1
    assert perdita.celle_ambigue == []
    assert perdita.fuse == 1


# --- la maschera: l'asse che fino a L9 non c'era ----------------------------

def test_la_maschera_annuale_copre_tutte_le_settimane_dell_anno():
    s = mini_school()
    att = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], att, day=0, slot=0)

    righe, _ = pubblica(s["schedule"])

    assert righe[0].iso_week_mask == _bit(0, 1, 2, 3)


def test_l_ora_quindicinale_esce_come_due_maschere_disgiunte():
    """🔑 Il caso per cui L9 ha aggiunto il campo. Senza, le due mezze ore
    uscivano annuali tutt'e due, e in ogni settimana una delle due era
    **falsa**: il motore avrebbe cercato un supplente per un'ora che non si
    teneva."""
    s = mini_school()
    pari = make_activity(s["subject"], teachers=[s["teacher"]],
                         classes=[s["klass"]], mask=0b0101)
    dispari = make_activity(s["subject"], teachers=[s["teacher"]],
                            classes=[s["klass"]], mask=0b1010)
    place(s["schedule"], pari, day=0, slot=0)
    place(s["schedule"], dispari, day=0, slot=1)

    righe, perdita = pubblica(s["schedule"])

    per_ora = {r.period_number: r.iso_week_mask for r in righe}
    assert per_ora[1] == _bit(0, 2)
    assert per_ora[2] == _bit(1, 3)
    # Disgiunte: nessuna settimana le vede tutt'e due.
    assert per_ora[1] & per_ora[2] == 0
    assert perdita.vuota


def test_il_sostituto_oscura_l_originale():
    """ADR-014: la maschera **effettiva**. Se l'originale uscisse intero,
    Aurora vedrebbe due lezioni nella settimana sostituita."""
    s = mini_school()
    altro = Teacher.objects.create(name="Bianchi Ugo", last_name="Bianchi",
                                   first_name="Ugo")
    originale = make_activity(s["subject"], teachers=[s["teacher"]],
                              classes=[s["klass"]])
    place(s["schedule"], originale, day=0, slot=0)
    supplenza = make_activity(s["subject"], teachers=[altro],
                              classes=[s["klass"]], mask=1 << 2)
    supplenza.substitutes = originale
    supplenza.save()
    place(s["schedule"], supplenza, day=0, slot=0)

    righe, _ = pubblica(s["schedule"])

    per_docente = {r.teacher: r.iso_week_mask for r in righe}
    assert per_docente["Rossi Anna"] == _bit(0, 1, 3)
    assert per_docente["Bianchi Ugo"] == _bit(2)
    assert per_docente["Rossi Anna"] & per_docente["Bianchi Ugo"] == 0


def test_il_periodo_entra_nella_maschera():
    """🔑 ADR-010 attraversa il confine **dentro la maschera**: Aurora non ha
    un campo «da quando a quando», ma le settimane bastano. Due quadrimestri
    convivono nella stessa tabella invece di cancellarsi a vicenda."""
    s = mini_school()
    p = s["period"]
    p.start_date = dt.date(2026, 9, 28)     # le sole settimane 2 e 3
    p.save()
    att = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], att, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert righe[0].iso_week_mask == _bit(2, 3)
    assert perdita.fuori_periodo == 0


def test_l_attivita_tutta_fuori_dal_periodo_non_esce_e_si_conta():
    s = mini_school()
    p = s["period"]
    p.start_date = dt.date(2026, 9, 28)
    p.save()
    att = make_activity(s["subject"], teachers=[s["teacher"]],
                        classes=[s["klass"]], mask=0b0001)   # solo la settimana 0
    place(s["schedule"], att, day=0, slot=0)

    righe, perdita = pubblica(s["schedule"])

    assert righe == []
    assert perdita.fuori_periodo == 1


def test_la_conversione_dell_indice_non_e_una_rinumerazione():
    """La settimana 0 non diventa il bit 0: diventa il bit **38**, che è il
    numero ISO del suo lunedì. È tutta la differenza fra un indice che ha
    bisogno di un'ancora e uno che si legge da sé."""
    s = mini_school()
    assert settimane_iso(0b0001, s["year"]) == 1 << 38
    assert settimane_iso(FULL, s["year"]) == _bit(0, 1, 2, 3)
    assert settimane_iso(0, s["year"]) == 0


# --- l'estrazione -----------------------------------------------------------

def test_l_estrazione_restringe_l_uscita():
    """La regola di sempre: un'estrazione restringe ciò su cui si **agisce**.
    Qui agire è pubblicare, quindi restringe davvero — un calendario non è una
    diagnosi."""
    s = mini_school()
    dentro = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    fuori = make_activity(s["subject"], teachers=[s["teacher"]], classes=[s["klass"]])
    place(s["schedule"], dentro, day=0, slot=0)
    place(s["schedule"], fuori, day=1, slot=0)

    righe, _ = pubblica(s["schedule"], selected={dentro.pk})

    assert [r.weekday for r in righe] == ["monday"]


# --- il banco: la misura che ADR-027 dichiara, rifatta ----------------------

@pytest.mark.django_db
def test_banco_la_griglia_piatta_porta_tutte_le_cattedre():
    """🔑 **La perdita di ADR-027 non è più tre chiavi su 142.**

    Quell'ADR misurava l'appiattimento quando `ScheduleEntry` non aveva un asse
    delle settimane: tre chiavi non tornavano — due il raggruppamento
    trasversale, una l'ora quindicinale. Con il campo di validità (L9) e con il
    gruppo che esce come le classi che tocca, la griglia porta **142 chiavi su
    142, ore comprese**, purché la maschera si legga.

    ⚠ **E l'oracolo dichiara il proprio limite.** Le cattedre di riferimento
    sono appiattite *nello stesso modo* — la parte diventa la sua classe, il
    gruppo le classi delle sue parti — quindi questo confronto **non può
    vedere** la perdita del gruppo: la vede identica da tutt'e due i lati. È
    esattamente per questo che `Perdita` la conta a parte invece di dedurla da
    un confronto.

    I numeri sono stabili su cinque ottimi distinti a otto lavoratori.
    """
    import collections

    from tests import alighieri
    from tests.test_bootstrap import _cattedre_vere
    from domain.solver.model import apply, solve

    env = alighieri.build()
    r = solve(env["schedule"], workers=8, time_limit=180, allow_unplaced=False)
    assert r.status == "OPTIMAL", r.stats
    apply(r, env["schedule"])

    righe, perdita = pubblica(env["schedule"])
    assert len(righe) == 369

    vere = _cattedre_vere()
    chiavi = {(x.teacher, x.school_class, x.subject) for x in righe}
    assert chiavi == set(vere)
    assert len(chiavi) == 142

    # Contate **cieche alla maschera**, le ore sbagliano su una chiave sola: la
    # griglia mostra tre ore di scienze in 5B dove la settimana ne porta due.
    cieche = collections.Counter(
        (x.teacher, x.school_class, x.subject) for x in righe)
    storte = {k for k in chiavi if cieche[k] != vere[k]}
    assert storte == {("Urbani Chiara", "5B", "SCI")}

    # Contate **dentro una settimana**, non ne sbaglia nessuna. È tutto il
    # lavoro che fa il campo di validità.
    for iso in (38, 39):
        dentro = collections.Counter(
            (x.teacher, x.school_class, x.subject) for x in righe
            if (x.iso_week_mask >> iso) & 1)
        assert not {k for k in chiavi if dentro[k] != vere[k]}, iso

    # E la perdita che resta non è una chiave: è **cosa una chiave significa**.
    assert (perdita.parti, perdita.gruppi) == (34, 6)
    assert perdita.senza_docente == 0 and perdita.fuori_settimana == 0
    assert perdita.fuori_periodo == 0
    assert perdita.celle_ambigue == [] and perdita.fuse == 0


@pytest.mark.django_db
def test_banco_l_ora_quindicinale_esce_come_due_meta_complementari():
    """Il ramo di controllo della misura qui sopra: che le due righe **siano**
    complementari, e non solo che il conteggio settimanale torni. Un conteggio
    torna anche con due maschere sbagliate della taglia giusta."""
    from tests import alighieri
    from domain.solver.model import apply, solve

    env = alighieri.build()
    r = solve(env["schedule"], workers=8, time_limit=180, allow_unplaced=False)
    apply(r, env["schedule"])
    righe, _ = pubblica(env["schedule"])

    annuale = max(r_.iso_week_mask for r_ in righe)
    meta = [r_ for r_ in righe if r_.iso_week_mask != annuale]

    assert len(meta) == 2
    assert {(m.school_class, m.subject) for m in meta} == {("5B", "SCI")}
    assert meta[0].iso_week_mask & meta[1].iso_week_mask == 0
    assert meta[0].iso_week_mask | meta[1].iso_week_mask == annuale
