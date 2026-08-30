"""L'ondata 4 del banco: l'asse Relazione.

I tredici tipi di `SubjectConstraint` in tredici righe, e le stesse tre
domande dell'ondata 3 — il builder la vede? si vede nell'orario? morde? — ma
con una risposta **diversa** alla terza, e la differenza è il contenuto di
questa ondata.

🔑 **La tacca dell'ondata 3 non si applica qui, e il motivo è strutturale.**
Un vincolo di cardinalità limita una risorsa che ha un carico fisso: si
stringe di un'unità e il conteggio non torna più. Un divieto di relazione no —
una proibizione **non sparpaglia**. Vietare che il greco stia a un giorno di
distanza da sé stesso non impedisce di metterne tre ore nello stesso giorno,
e trentanove fasce libere assorbono quasi ogni altro divieto. Misurato invece
che supposto: vedi `test_la_proibizione_non_sparpaglia_ed_e_una_misura`, dove
la tacca che sembrava aritmetica torna `OPTIMAL`.

🔑 **Al suo posto, il testimone puntato — ed è la mutazione per rimozione che
torna misurabile.** L'ondata 3 ha scartato «togli la riga e l'orario cambia»
perché senza funzione di costo sopra lo scarto ogni orario a zero scarti è
ottimo, e ciò che torna dice quale ottimo ha trovato la ricerca. Ma se con
`pinned` si **impone** la configurazione che la riga vieta, le due esecuzioni
non rispondono più «quale orario», rispondono `INFEASIBLE` e `OPTIMAL`: due
proprietà del modello, in due direzioni. Con la riga l'orario non esiste,
senza la riga esiste — e nessuna delle due frasi dipende dal testimone che il
solver sceglie.

⚠ Il prezzo è che il pin va scelto **minimale**: se la configurazione imposta
fosse illegale anche per un'altra ragione, il ramo «senza la riga» sarebbe
infattibile e il test direbbe soltanto che due attività non ci stanno. È
esattamente ciò che il secondo `assert` di ogni caso controlla, ed è il motivo
per cui i due rami stanno nello stesso test invece che in due."""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.analysis.state import ScheduleState
from domain.models import Activity, Subject, SubjectConstraint
from domain.solver.model import apply, solve
from tests import alighieri

pytestmark = pytest.mark.django_db

MORNING_END = alighieri.MORNING_END_SLOT


def _mezza(day, slot):
    return day * 2 + (0 if slot < MORNING_END else 1)


def _riga(nome):
    """Il queryset della riga di `SUBJECT_CONSTRAINTS` che si chiama `nome`."""
    for n, (kind, ref), a, b, tipo, _param in alighieri.SUBJECT_CONSTRAINTS:
        if n == nome:
            campo = {"c": "school_class__name", "p": "class_part__name",
                     "g": "group__name"}[kind]
            return SubjectConstraint.objects.filter(
                **{campo: ref}, subject_a__code=a, subject_b__code=b, type=tipo)
    raise KeyError(nome)


def _celle(stato, **filtro):
    """`(giorno, fascia, durata)` delle attività piazzate che soddisfano il
    filtro, in ordine."""
    return sorted(
        (stato.placed[a.pk].day, stato.placed[a.pk].start_slot, a.duration_slots)
        for a in Activity.objects.filter(**filtro).distinct()
        if a.pk in stato.placed)


# I testimoni puntati: per ogni riga, la configurazione **minima** che la
# viola. Il valore è una funzione perché gli id esistono solo dopo il build.
#
# ⚠ Ogni pin è a cavallo di fasce diverse e di attività che possono
# legittimamente coesistere: se due di esse confliggessero sull'occupazione, il
# ramo di controllo fallirebbe e il test lo direbbe.
def _pin(nome):
    def cl(classe, materia, durata=1):
        return list(Activity.objects.filter(
            classes__name=classe, subject__code=materia,
            duration_slots=durata).order_by("pk"))

    def parte(nome_parte, materia):
        return list(Activity.objects.filter(
            parts__name=nome_parte, subject__code=materia).order_by("pk"))

    if nome == "same_half_day":        # MAT e FIS nella stessa mattinata
        return {cl("5A", "MAT")[0].pk: (0, 0), cl("5A", "FIS")[0].pk: (0, 2)}
    if nome == "same_day":             # latino e greco lo stesso giorno
        return {cl("4B", "LAT")[0].pk: (0, 0), cl("4B", "GRE")[0].pk: (0, 2)}
    if nome == "two_days":             # due ore di greco a un giorno di distanza
        g = cl("3B", "GRE")
        return {g[0].pk: (0, 0), g[1].pk: (1, 0)}
    if nome == "forbidden_sequence":   # matematica subito dopo le due ore di MOT
        # ⚠ **Martedì e non lunedì, e l'ha imposto l'ondata 5**: la palestra è
        # rossa il lunedì mattina, e su un'aula a candidata unica quella riga
        # toglie la cella *prima* che il modello nasca. Il pin finiva fuori
        # dominio, il primo `assert` restava verde per il motivo sbagliato e il
        # secondo — il ramo di controllo — è diventato rosso. È il ramo di
        # controllo che ha fatto il suo mestiere: senza, l'ondata 5 avrebbe
        # spento un testimone dell'ondata 4 in silenzio.
        return {cl("4A", "MOT", 2)[0].pk: (1, 0), cl("4A", "MAT")[0].pk: (1, 2)}
    if nome == "max_hours_half_day":   # quattro ore di matematica in una mattina
        m = cl("2A", "MAT")
        return {cl("2A", "MAT", 2)[0].pk: (0, 0), m[0].pk: (0, 2), m[1].pk: (0, 3)}
    if nome == "max_hours_day":        # tre ore di italiano in un giorno
        i = cl("3B", "ITA")
        return {i[0].pk: (0, 0), i[1].pk: (0, 2), i[2].pk: (0, 4)}
    if nome == "weekly_order":         # il greco apre la settimana prima del latino
        return {cl("5B", "GRE")[0].pk: (0, 0), cl("5B", "LAT")[0].pk: (0, 1)}
    if nome == "imposed_succession":   # le due sessioni di fisica agli antipodi
        return {cl("3A", "FIS", 2)[0].pk: (0, 0), cl("3A", "FIS")[0].pk: (4, 0)}
    if nome == "half_day_gap":         # due ore di latino nella stessa mezza giornata
        l = cl("1B", "LAT")
        return {l[0].pk: (0, 0), l[1].pk: (0, 2)}
    if nome == "parts_before":         # il gruppo dopo la teoria, dove va prima
        return {cl("3A", "SCI")[0].pk: (0, 1), parte("3A_G1", "SCI")[0].pk: (0, 3)}
    if nome == "parts_after":          # il gruppo prima della teoria, dove va dopo
        return {cl("3A", "SCI")[0].pk: (0, 3), parte("3A_G2", "SCI")[0].pk: (0, 1)}
    if nome == "parts_h":              # parte, classe, parte nella stessa mattina
        return {parte("3A_G1", "SCI")[0].pk: (0, 0), cl("3A", "SCI")[0].pk: (0, 1),
                parte("3A_G2", "SCI")[0].pk: (0, 2)}
    if nome == "parts_ab":             # parte, classe, parte nello stesso giorno
        return {parte("4A_G1", "SCI")[0].pk: (0, 0), cl("4A", "SCI")[0].pk: (0, 1),
                parte("4A_G2", "SCI")[0].pk: (0, 2)}
    raise KeyError(nome)


NOMI = [n for n, *_ in alighieri.SUBJECT_CONSTRAINTS]


def test_le_tredici_righe_ci_sono():
    """Un tipo per riga, e nessun tipo scoperto: sull'asse Relazione il
    portatore è una coppia **(unità, materia)**, non una risorsa, quindi non
    c'è la ragione che all'ondata 3 costringeva due righe sulla stessa
    famiglia."""
    alighieri.build()
    righe = SubjectConstraint.objects.all()
    assert righe.count() == 13
    assert {r.type for r in righe} == set(SubjectConstraint.Type.values)
    # Le unità sono tutte e tre le forme che il modello ammette? No: i
    # raggruppamenti no, ed è un fatto del dataset, non una svista. Nessuna
    # materia dei due raggruppamenti di inglese esiste anche a classe intera,
    # quindi una riga su di loro sarebbe vera per vacuità.
    assert {bool(r.school_class_id) for r in righe} == {True, False}
    assert righe.filter(class_part__isnull=False).count() == 2
    assert righe.filter(group__isnull=False).count() == 0


def test_le_tredici_forme_dichiarate():
    """L'invariante che ogni riga garantisce, letto sull'orario prodotto.

    ⚠ **Questo test non dimostra che le righe mordono**, e la distinzione è il
    contenuto dell'ondata: un divieto è soddisfatto anche separando, e
    separare è quasi sempre possibile. Qui si controlla che l'invariante *ci
    sia*; che non sia soddisfatto per caso lo dice il testimone puntato.

    L'unica riga che si vede **forzare** la forma è lo scarto minimo di mezze
    giornate: cinque ore di latino con passo ≥ 2 stanno in un arco di almeno
    otto mezze giornate su dieci, cioè un'ora al giorno e non di più.

    ⚠ **`workers=1` è stato tolto dall'ondata 5**, che con i tetti di peso
    ha portato lo stesso modello da 7 s a 439 s con un lavoratore solo. Le
    asserzioni qui sotto sono invarianti e non celle, quindi non dipendono da
    quale ottimo torni."""
    env = alighieri.build()
    soluzione = solve(env["schedule"], workers=8)
    assert soluzione.status == "OPTIMAL"
    assert list(soluzione.unplaced) == []
    apply(soluzione, env["schedule"])
    stato = ScheduleState.build(env["schedule"])

    def mezze(**filtro):
        return sorted(_mezza(d, s) for d, s, _ in _celle(stato, **filtro))

    def giorni(**filtro):
        return sorted({d for d, _s, _n in _celle(stato, **filtro)})

    # same_half_day — MAT e FIS di 5A mai nella stessa mezza giornata.
    assert not (set(mezze(classes__name="5A", subject__code="MAT"))
                & set(mezze(classes__name="5A", subject__code="FIS")))

    # same_day — latino e greco di 4B mai lo stesso giorno.
    assert not (set(giorni(classes__name="4B", subject__code="LAT"))
                & set(giorni(classes__name="4B", subject__code="GRE")))

    # two_days — nessuna coppia di giornate di greco a distanza uno.
    greco = giorni(classes__name="3B", subject__code="GRE")
    assert not any(b - a == 1 for a in greco for b in greco)

    # forbidden_sequence — niente matematica attaccata alla fine di MOT.
    mot = _celle(stato, classes__name="4A", subject__code="MOT")
    mat = _celle(stato, classes__name="4A", subject__code="MAT")
    assert not [1 for gd, gs, dur in mot for md, ms, _ in mat
                if md == gd and ms == gs + dur]

    # max_hours_half_day / max_hours_day — i due tetti, per secchio.
    per_mezza, per_giorno = {}, {}
    for d, s, dur in _celle(stato, classes__name="2A", subject__code="MAT"):
        per_mezza[_mezza(d, s)] = per_mezza.get(_mezza(d, s), 0) + dur * 60
    for d, s, dur in _celle(stato, classes__name="3B", subject__code="ITA"):
        per_giorno[d] = per_giorno.get(d, 0) + dur * 60
    assert max(per_mezza.values()) <= 180
    assert max(per_giorno.values()) <= 120

    # weekly_order — la prima ora di latino precede la prima di greco.
    primo_lat = _celle(stato, classes__name="5B", subject__code="LAT")[0][:2]
    primo_gre = _celle(stato, classes__name="5B", subject__code="GRE")[0][:2]
    assert primo_lat < primo_gre

    # imposed_succession — le due sessioni di fisica a non più di una mezza
    # giornata l'una dall'altra.
    fisica = mezze(classes__name="3A", subject__code="FIS")
    assert all(b - a <= 1 for a, b in zip(fisica, fisica[1:]))

    # 🔑 half_day_gap — la sola riga che si vede **forzare** la forma: passo
    # ≥ 2, quindi arco ≥ 8 su dieci mezze giornate disponibili.
    latino = mezze(classes__name="1B", subject__code="LAT")
    assert all(b - a >= 2 for a, b in zip(latino, latino[1:]))
    assert latino[-1] - latino[0] >= 8

    # I quattro PARTS_* — l'ordine fra ore di parte e ore a classe intera,
    # dentro il secchio di ciascuna riga.
    def ordine(secchio, parte, classe, modo):
        entries = ([(secchio(d, s), s, "part") for d, s, _ in parte]
                   + [(secchio(d, s), s, "class") for d, s, _ in classe])
        for chiave in {k for k, _s, _l in entries}:
            dentro = sorted((s, l) for k, s, l in entries if k == chiave)
            etichette = [l for _s, l in dentro]
            if "part" not in etichette or "class" not in etichette:
                continue
            parti = [s for s, l in dentro if l == "part"]
            classi = [s for s, l in dentro if l == "class"]
            if modo == "before":
                assert max(parti) < min(classi), (chiave, dentro)
            elif modo == "after":
                assert min(parti) > max(classi), (chiave, dentro)
            else:
                assert sum(x != y for x, y in zip(etichette, etichette[1:])) <= 1

    sci3 = _celle(stato, classes__name="3A", subject__code="SCI")
    sci4 = _celle(stato, classes__name="4A", subject__code="SCI")
    g1_3 = _celle(stato, parts__name="3A_G1", subject__code="SCI")
    g2_3 = _celle(stato, parts__name="3A_G2", subject__code="SCI")
    per_giornata = (lambda d, _s: d)
    ordine(per_giornata, g1_3, sci3, "before")
    ordine(per_giornata, g2_3, sci3, "after")
    ordine(_mezza, g1_3 + g2_3, sci3, "omogeneo")
    ordine(per_giornata,
           _celle(stato, parts__name="4A_G1", subject__code="SCI")
           + _celle(stato, parts__name="4A_G2", subject__code="SCI"),
           sci4, "omogeneo")

    # E nessuna riga violata: le forme dicono *quale* effetto si vede, il
    # checker dice che non ce n'è nessuno rotto.
    hard = [f for f in check_schedule(env["schedule"]) if f.severity == Severity.HARD]
    assert [f.code for f in hard] == ["room_unassigned"] * 73


@pytest.mark.parametrize("nome", NOMI)
def test_ogni_riga_morde_col_testimone_puntato(nome):
    """🔑 **La mutazione per rimozione, nella forma che si può dimostrare.**

    Si impone con `pinned` la configurazione che la riga vieta. Con la riga il
    modello è `INFEASIBLE`; tolta la riga — e **solo** quella, con lo stesso
    pin — torna `OPTIMAL` a zero scarti. La prima metà dice che la riga
    vincola, la seconda che a vincolare è *lei* e non un conflitto qualunque
    fra le attività che il pin tocca.

    ⚠ Nessuna delle due affermazioni dipende da quale ottimo la ricerca
    sceglie, che è ciò che all'ondata 3 aveva reso la mutazione per rimozione
    non misurabile."""
    env = alighieri.build()
    pin = _pin(nome)
    con = solve(env["schedule"], workers=8, time_limit=60, pinned=pin)
    assert con.status == "INFEASIBLE", con.stats

    assert _riga(nome).delete()[0] == 1
    senza = solve(env["schedule"], workers=8, time_limit=60, pinned=pin)
    assert senza.status == "OPTIMAL", senza.stats
    assert list(senza.unplaced) == []


# Le tacche dell'ondata 3, dove la famiglia ne ammette una: un parametro che
# si stringe di un'unità e un argomento di conteggio che lo giustifica.
#
# ⚠ Sono **tre su tredici**, e non è una lacuna del dataset: sui divieti puri
# non esiste un parametro da stringere, ed è la ragione per cui l'ondata 4
# porta il testimone puntato invece della tacca.
TACCHE = {
    # Il blocco da due ore di matematica non si spezza: 120 minuti in una
    # mezza giornata sola, quindi un tetto a 60 è già rotto dal dato.
    "max_hours_half_day": 60,
    # 🔑 La tacca che attraversa i due assi: quattro ore di italiano a un'ora
    # al giorno vogliono quattro giornate distinte, e GENTI — che il 3B ce
    # l'ha — ne lavora **tre** per la riga `max_presence` dell'ondata 3.
    "max_hours_day": 60,
    # Cinque ore di latino con passo ≥ 3 vogliono un arco di dodici mezze
    # giornate, e la settimana ne ha dieci.
    "half_day_gap": 3,
}


@pytest.mark.parametrize("nome", sorted(TACCHE))
def test_le_tre_tacche_che_esistono(nome):
    env = alighieri.build()
    riga = _riga(nome).get()
    riga.param = TACCHE[nome]
    riga.save()
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=90)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_la_proibizione_non_sparpaglia_ed_e_una_misura():
    """⚠ **Un'attesa smentita, e la sbagliata era l'attesa.**

    Il disegno prevedeva una quarta tacca: spostare la riga `two_days` dal
    greco del 3B (3 ore) al latino (4 ore), perché quattro giornate a due a
    due non adiacenti non stanno in cinque — l'insieme indipendente massimo di
    un cammino di cinque nodi è tre. Il conteggio è giusto e la premessa no:
    **niente obbliga quattro ore della stessa materia a stare su quattro
    giornate distinte.** Il solver le impila, e l'orario esiste.

    È la stessa trappola che rende `same_day_incompatible` fra due materie
    sempre soddisfacibile da solo, ed è il motivo per cui l'asse Relazione
    vuole il testimone puntato invece della tacca. Il test asserisce
    l'`OPTIMAL` perché diventi rosso il giorno in cui il banco si stringe
    abbastanza da forzare lo sparpagliamento.

    ⚠ **E l'ondata 7 non è quel giorno**, misurato: il criterio «stretto ma
    risolvibile» di §4 è verificato togliendo una risorsa, non
    accorciando la griglia — e lo sparpagliamento lo forza la seconda,
    non la prima."""
    env = alighieri.build()
    riga = _riga("two_days").get()
    riga.subject_a = riga.subject_b = Subject.objects.get(code="LAT")
    riga.save()
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=90)
    assert soluzione.status == "OPTIMAL", soluzione.stats
