"""Il **questionario d'ingresso** (ADR-028, gradino 3).

Ogni regola si prova col suo **ramo di controllo**, perché «la domanda è
sparita dall'elenco» è soddisfatto anche da un elenco che si svuota da solo —
che è precisamente il difetto che `SetupQuestion` esiste per non avere.
"""

import pytest

from domain import questionario as Q
from domain.bootstrap import Lezione, applica, ricava
from domain.models import (Discipline, SetupQuestion, Subject, Teacher)
from tests import alighieri, fermi

pytestmark = pytest.mark.django_db


# --- Il catalogo --------------------------------------------------------------

def test_il_catalogo_e_coerente():
    chiavi = [v["chiave"] for v in Q._CATALOGO]
    assert len(chiavi) == len(set(chiavi))
    assert set(chiavi) == {q.chiave for q in Q.questionario()}
    for v in Q._CATALOGO:
        assert v["effetto"] in (Q.MUTO, Q.ASSENTE, Q.FUORI_CALCOLO)
        for d in v.get("dipende_da", ()):
            assert d in chiavi


def test_l_ordine_rispetta_le_dipendenze():
    viste = set()
    for q in Q.questionario():
        assert set(q.dipende_da) <= viste, f"{q.chiave} prima di {q.dipende_da}"
        viste.add(q.chiave)


def test_la_dipendenza_batte_la_gravita():
    """La decisione dichiarata in testa al modulo, come misura.

    `indisponibilita` è `MUTO` e `aule` è solo `ASSENTE`, eppure le aule
    vengono prima: non si può dire *quando un'aula è occupata* prima di dire
    *quali aule ci sono*."""
    ordine = [q.chiave for q in Q.questionario()]
    assert Q.MUTO != Q.ASSENTE
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert per_chiave["indisponibilita"].effetto == Q.MUTO
    assert per_chiave["aule"].effetto == Q.ASSENTE
    assert ordine.index("aule") < ordine.index("indisponibilita")


def test_a_parita_di_possibilita_ordina_la_gravita():
    """Il ramo di controllo del precedente: dove la dipendenza non parla, a
    decidere è l'effetto. Fra le domande **senza** dipendenze l'ordine è
    muto → assente → fuori calcolo."""
    libere = [q for q in Q.questionario() if not q.dipende_da]
    gravita = [Q._GRAVITA[q.effetto] for q in libere]
    assert gravita == sorted(gravita)
    assert len(set(gravita)) > 1  # o l'asserzione sopra non direbbe niente


# --- Il silenzio non è una risposta -------------------------------------------

def test_su_un_database_vuoto_sono_tutte_aperte():
    tutte = Q.questionario()
    assert len(tutte) == 12
    assert all(q.aperta for q in tutte)
    assert sum(1 for q in tutte if q.effetto == Q.MUTO) == 6


def test_le_righe_non_chiudono_una_domanda():
    """🔑 La regola del modulo. L'Alighieri ha righe in **undici** famiglie su
    dodici, e resta un questionario **tutto aperto**: nessuno ha chiuso niente.

    Il ramo di controllo è la riga dopo: chiudere una domanda la chiude — cioè
    l'elenco *può* svuotarsi, quando qualcuno lo svuota."""
    alighieri.build()
    con_righe = {q.chiave for q in Q.questionario() if q.righe}
    assert len(con_righe) == 11
    assert "criteri_di_qualita" not in con_righe  # `build()` non li installa
    assert all(q.aperta for q in Q.questionario())

    Q.chiudi("indisponibilita", "55 righe, viste dalla vicepreside")
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert per_chiave["indisponibilita"].chiusa
    assert per_chiave["indisponibilita"].righe == 55
    assert not per_chiave["vincoli_orari"].chiusa


def test_una_domanda_senza_righe_si_chiude_lo_stesso():
    """🔑 Il caso per cui la tabella esiste: la risposta era *«niente»*.

    Senza questo il dialogo non terminerebbe — una scuola davvero senza vincoli
    di materia resterebbe incompleta per sempre."""
    aperta = {q.chiave for q in Q.aperte()}
    assert "vincoli_materia" in aperta

    Q.chiudi("vincoli_materia", "la scuola non ne ha")
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert per_chiave["vincoli_materia"].righe == 0
    assert per_chiave["vincoli_materia"].chiusa
    # Il controllo: un'altra famiglia ugualmente vuota resta aperta, quindi a
    # chiudere è stata la chiusura e non il vuoto.
    assert per_chiave["vincoli_orari"].righe == 0
    assert per_chiave["vincoli_orari"].aperta


def test_chiudere_due_volte_non_duplica_e_aggiorna_la_nota():
    Q.chiudi("aule", "prima nota")
    Q.chiudi("aule", "seconda nota")
    assert SetupQuestion.objects.filter(key="aule").count() == 1
    assert SetupQuestion.objects.get(key="aule").note == "seconda nota"


def test_una_domanda_che_non_esiste_e_un_errore():
    with pytest.raises(ValueError):
        Q.chiudi("colore_delle_tende")


def test_una_chiusura_orfana_si_fa_sentire():
    """Se il catalogo perde una voce, le chiusure che la nominavano non vanno
    ignorate in silenzio: sono uno stato che non significa più niente."""
    SetupQuestion.objects.create(key="una_domanda_di_ieri")
    with pytest.raises(ValueError):
        Q.questionario()


# --- Il perimetro è lo stato di adesso ----------------------------------------

def test_il_perimetro_si_rilegge_ogni_volta():
    prima = {q.chiave: q.perimetro for q in Q.questionario()}
    assert ("docenti", 0) in prima["indisponibilita"]
    Teacher.objects.create(name="ROSSI", last_name="Rossi", first_name="A")
    dopo = {q.chiave: q.perimetro for q in Q.questionario()}
    assert ("docenti", 1) in dopo["indisponibilita"]


def test_un_inventario_dichiara_di_non_avere_perimetro():
    """Aule, sedi e materiali non si ricavano da nessun dato che abbiamo: il
    perimetro vuoto è un'informazione, non un buco."""
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert per_chiave["aule"].perimetro == ()
    assert per_chiave["sedi"].perimetro == ()
    assert per_chiave["materiali_e_personale"].perimetro == ()
    # Il controllo: chi un perimetro ce l'ha lo dice.
    assert per_chiave["peso_didattico"].perimetro == (
        ("materie", 0), ("tetti d'istituto", 4))


# --- Il giro dal gradino 1 al gradino 3 ---------------------------------------

def _griglia_minima():
    return [Lezione("ROSSI", 0, 0, "1A", "MAT"),
            Lezione("ROSSI", 0, 1, "1A", "MAT"),
            Lezione("BIANCHI", 1, 0, "1A", "ITA")]


def test_dopo_ricava_il_questionario_dice_cosa_manca():
    """🔑 Il gradino 1 scrive, il gradino 3 elenca ciò che il gradino 1 **non
    poteva** scrivere: undici famiglie su dodici restano senza una riga."""
    applica(ricava(_griglia_minima()))
    per_chiave = {q.chiave: q for q in Q.questionario()}
    con_righe = {k for k, q in per_chiave.items() if q.righe}
    assert con_righe == {"discipline"}   # la sola, ed è la segnaposto
    assert per_chiave["indisponibilita"].perimetro == (
        ("docenti", 2), ("classi", 1), ("aule", 0))
    assert ("materie", 2) in per_chiave["peso_didattico"].perimetro


def test_la_disciplina_segnaposto_si_riconosce():
    """`applica` inventa una disciplina perché il campo non è annullabile. Il
    questionario la vede per quello che è, e smette di vederla quando qualcuno
    risponde davvero."""
    applica(ricava(_griglia_minima()))
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert ("materie ancora su una disciplina segnaposto", 2) in per_chiave["discipline"].perimetro

    vera = Discipline.objects.create(code="A026", name="Matematica")
    Subject.objects.update(discipline=vera)
    per_chiave = {q.chiave: q for q in Q.questionario()}
    assert ("materie ancora su una disciplina segnaposto", 0) in per_chiave["discipline"].perimetro


# --- Il confronto fra i due dataset -------------------------------------------

def test_il_fermi_ha_risposto_a_un_terzo_delle_domande():
    """⚠ La misura che dice quanto è grande il gradino 3, e viene dal dataset
    che **non** è stato costruito per superare i nostri test.

    Il Fermi è l'unica cosa che abbiamo di osservato: una scuola inserita in
    EDT campo per campo. Delle dodici famiglie ne porta **quattro**. È la
    stessa forma della misura che aprì L4 — tre builder su ventotto — vista
    dalla parte di chi deve chiedere invece che da quella di chi calcola."""
    fermi.build()
    con_righe = {q.chiave for q in Q.questionario() if q.righe}
    assert con_righe == {"aule", "indisponibilita", "discipline", "calendario"}
    mute_vuote = {q.chiave for q in Q.questionario()
                  if q.effetto == Q.MUTO and not q.righe}
    assert mute_vuote == {"sedi", "partizioni", "vincoli_orari", "vincoli_materia"}


def test_una_chiusura_si_puo_annullare():
    """Una chiusura senza ritorno sarebbe una trappola: chi chiude per sbaglio
    non avrebbe modo di dirlo."""
    Q.chiudi("sedi")
    assert {q.chiave for q in Q.aperte()}.isdisjoint({"sedi"})
    assert Q.riapri("sedi") is True
    assert "sedi" in {q.chiave for q in Q.aperte()}
    # Il controllo: riaprire ciò che non era chiuso lo dice invece di tacere.
    assert Q.riapri("sedi") is False


def test_il_segnaposto_e_quello_che_bootstrap_scrive():
    """Le due costanti devono coincidere, e coincidono perché sono una sola."""
    from domain.bootstrap import DISCIPLINA_DA_ASSEGNARE
    assert Q.SEGNAPOSTO == (DISCIPLINA_DA_ASSEGNARE[0],)


# --- Il comando ---------------------------------------------------------------

def test_il_comando_elenca_le_aperte_e_dichiara_la_regola():
    import io
    from django.core.management import call_command
    out = io.StringIO()
    call_command("questionario", stdout=out)
    testo = out.getvalue()
    assert "12 domande aperte su 12" in testo
    assert "6 delle quali muta il calcolo" in testo
    assert "MUTO" in testo and "FUORI CALCOLO" in testo
    assert "Le righe non chiudono una domanda" in testo
    # Il perimetro non ricavabile si dichiara invece di stampare zero.
    assert "non si ricava — è un inventario" in testo


def test_il_comando_chiude_e_riapre():
    import io
    from django.core.management import call_command
    call_command("questionario", "--chiudi", "quote", "--nota", "niente",
                 stdout=io.StringIO())
    out = io.StringIO()
    call_command("questionario", stdout=out)
    assert "11 domande aperte su 12" in out.getvalue()
    assert "(1 già chiuse" in out.getvalue()

    call_command("questionario", "--riapri", "quote", stdout=io.StringIO())
    out = io.StringIO()
    call_command("questionario", stdout=out)
    assert "12 domande aperte su 12" in out.getvalue()


def test_il_comando_rifiuta_le_chiavi_che_non_esistono():
    import io
    from django.core.management import CommandError, call_command
    with pytest.raises(CommandError):
        call_command("questionario", "--chiudi", "colore_delle_tende",
                     stdout=io.StringIO())
    with pytest.raises(CommandError):
        call_command("questionario", "--riapri", "aule", stdout=io.StringIO())


def test_il_peso_didattico_ha_due_meta():
    """I pesi delle materie **e** i tetti d'istituto. Contarne una sola direbbe
    «nessuna riga» a una scuola che ha messo i tetti e lasciato i pesi al
    default — che è il caso più comune, perché il peso di default è 1."""
    from domain.models import InstituteSettings
    assert {q.chiave: q for q in Q.questionario()}["peso_didattico"].righe == 0
    s = InstituteSettings.load()
    s.max_weight_day = 12
    s.save()
    assert {q.chiave: q for q in Q.questionario()}["peso_didattico"].righe == 1
