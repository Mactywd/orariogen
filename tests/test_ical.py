"""L'export iCal: dove la fascia di calcolo smette di essere l'ora.

L'oracolo di questo pezzo non è il solver ma il **formato**: `_srotola` rifà a
ritroso la piegatura di RFC 5545 e ricostruisce i VEVENT, così un test che
guarda `DTEND` guarda ciò che un telefono leggerebbe e non ciò che il
generatore credeva di scrivere.
"""
import datetime as dt

import pytest

from domain import ical, weeks
from domain.ical import LabelsMancanti, esporta, occorrenze
from domain.models import Activity, Holiday, Room, SlotLabel
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

ORE = [(0, dt.time(8, 0), dt.time(9, 0)),
       (1, dt.time(9, 0), dt.time(10, 0)),
       (2, dt.time(10, 0), dt.time(11, 0)),
       (3, dt.time(11, 0), dt.time(12, 0)),
       (4, dt.time(14, 0), dt.time(15, 0)),   # ⚠ la pausa: 12 → 14
       (5, dt.time(15, 0), dt.time(16, 0))]

QUANDO = dt.datetime(2026, 8, 28, 12, 0, tzinfo=dt.timezone.utc)


def etichette(grid, ore=ORE):
    for slot, inizio, fine in ore:
        SlotLabel.objects.create(grid=grid, slot=slot,
                                 start_time=inizio, end_time=fine)


def _srotola(testo):
    """Il verso opposto della piegatura: una riga che comincia con uno spazio
    è la continuazione della precedente (RFC 5545 §3.1)."""
    righe = []
    for riga in testo.split("\r\n"):
        if riga.startswith(" ") and righe:
            righe[-1] += riga[1:]
        else:
            righe.append(riga)
    return [r for r in righe if r]


def eventi(testo):
    """[{proprietà: valore}] per ogni VEVENT."""
    fuori, corrente = [], None
    for riga in _srotola(testo):
        if riga == "BEGIN:VEVENT":
            corrente = {}
        elif riga == "END:VEVENT":
            fuori.append(corrente)
            corrente = None
        elif corrente is not None:
            nome, _, valore = riga.partition(":")
            corrente[nome] = valore
    return fuori


# --- l'ora ------------------------------------------------------------------

def test_l_etichetta_e_l_ora_e_la_fascia_di_calcolo_non_lo_e():
    """🔑 Il punto del pezzo. La griglia dice 60 minuti — è l'ora di servizio
    del docente — e l'etichetta ne dichiara 55. Un calendario legge la
    seconda: `slot_minutes` non deve comparire nel file."""
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(8, 55))])
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)

    testo, _, _ = esporta(env["schedule"], dtstamp=QUANDO)
    ev = eventi(testo)[0]
    assert env["grid"].slot_minutes == 60
    assert ev["DTSTART"].endswith("T080000")
    assert ev["DTEND"].endswith("T085500")


def test_il_blocco_finisce_quando_finisce_l_ultima_fascia():
    env = mini_school(days=1, slots=6)
    etichette(env["grid"])
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    place(env["schedule"], a, 0, 0)

    ev = eventi(esporta(env["schedule"], dtstamp=QUANDO)[0])
    assert len(ev) == 4      # quattro settimane, un evento ciascuna
    assert ev[0]["DTSTART"].endswith("T080000")
    assert ev[0]["DTEND"].endswith("T100000")


def test_il_blocco_a_cavallo_della_pausa_e_due_eventi():
    """🔑 Un'attività non è sempre **un** evento. Il blocco da due fasce che
    scavalca la linea di mezza giornata dura due ore, non quattro: sommare
    `duration_minutes` all'ora d'inizio darebbe 11:00–13:00, che è un orario
    che non esiste da nessuna parte — né inizio né fine né durata."""
    env = mini_school(days=1, slots=6)
    etichette(env["grid"])
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    place(env["schedule"], a, 0, 3)          # fasce 3 e 4, con la pausa in mezzo

    ev = [e for e in eventi(esporta(env["schedule"], dtstamp=QUANDO)[0])
          if e["DTSTART"].startswith("20260914")]
    assert len(ev) == 2
    assert (ev[0]["DTSTART"][-6:], ev[0]["DTEND"][-6:]) == ("110000", "120000")
    assert (ev[1]["DTSTART"][-6:], ev[1]["DTEND"][-6:]) == ("140000", "150000")
    # E i due tronconi non si contendono l'UID, o il telefono ne terrebbe uno.
    assert ev[0]["UID"] != ev[1]["UID"]


def test_senza_etichetta_si_rifiuta_e_dice_quali_fasce():
    """⚠ Il rifiuto è la funzionalità. Il fallimento alternativo — «comincia
    alle 8» — non fa rumore e mette tutta la scuola all'ora sbagliata."""
    env = mini_school(days=1, slots=3)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    a = make_activity(env["subject"], classes=[env["klass"]], slots=2)
    place(env["schedule"], a, 0, 0)

    with pytest.raises(LabelsMancanti) as manca:
        occorrenze(env["schedule"])
    assert manca.value.args[0] == [1]


# --- il calendario ----------------------------------------------------------

def test_la_maschera_sceglie_le_settimane():
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    a = make_activity(env["subject"], classes=[env["klass"]], mask=0b0101)
    place(env["schedule"], a, 0, 0)

    occs, _ = occorrenze(env["schedule"])
    assert [o.date for o in occs] == [dt.date(2026, 9, 14), dt.date(2026, 9, 28)]


def test_il_festivo_toglie_l_occorrenza_e_non_la_sposta():
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    Holiday.objects.create(school_year=env["year"], date=dt.date(2026, 9, 21))

    occs, saltate = occorrenze(env["schedule"])
    assert dt.date(2026, 9, 21) not in [o.date for o in occs]
    assert len(occs) == 3 and saltate == 1


def test_il_periodo_e_un_confine():
    """ADR-010: si rigenera un orario per periodo, quindi il calendario del
    primo quadrimestre non deve invadere il secondo — anche quando la
    maschera dell'attività è annuale, che è il caso in cui sbagliare è
    silenzioso."""
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)
    periodo = env["period"]
    periodo.end_date = dt.date(2026, 9, 27)
    periodo.save()

    occs, saltate = occorrenze(env["schedule"])
    assert [o.date for o in occs] == [dt.date(2026, 9, 14), dt.date(2026, 9, 21)]
    assert saltate == 2


def test_la_sospesa_non_esce():
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    a = make_activity(env["subject"], classes=[env["klass"]],
                      immobility=Activity.Immobility.SUSPENDED)
    place(env["schedule"], a, 0, 0)

    assert occorrenze(env["schedule"])[0] == []


def test_il_perimetro_restringe_l_uscita():
    """⚠ L'unica sede in cui l'estrazione **restringe ciò che si conta**, e la
    ragione è che qui non si conta niente: pubblicare è agire, e un
    calendario non è una diagnosi."""
    env = mini_school(days=1, slots=2)
    etichette(env["grid"])
    dentro = make_activity(env["subject"], classes=[env["klass"]])
    fuori = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], dentro, 0, 0)
    place(env["schedule"], fuori, 0, 1)

    occs, _ = occorrenze(env["schedule"], selected={dentro.pk})
    assert {o.activity_id for o in occs} == {dentro.pk}


# --- il formato -------------------------------------------------------------

def test_l_uid_e_stabile_fra_due_export():
    """Ripubblicare deve **aggiornare**, non duplicare: un UID che cambia
    riempirebbe l'agenda di un docente di copie a ogni rigenerazione."""
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)

    uno = [e["UID"] for e in eventi(esporta(env["schedule"], dtstamp=QUANDO)[0])]
    due = [e["UID"] for e in eventi(esporta(
        env["schedule"], dtstamp=QUANDO + dt.timedelta(days=1))[0])]
    assert uno == due and len(set(uno)) == len(uno)


def test_le_righe_sono_piegate_a_settantacinque_ottetti():
    """⚠ In **ottetti**, non in caratteri: «à» ne occupa due, e un file che
    pieghi a 75 caratteri produce righe illegali su ogni nome accentato."""
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    env["subject"].name = "Attività integrative di potenziamento " * 3
    env["subject"].save()
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)

    testo, _, _ = esporta(env["schedule"], dtstamp=QUANDO)
    assert all(len(r.encode("utf-8")) <= 75 for r in testo.split("\r\n"))
    # E srotolando si riottiene il titolo intero: la piegatura è reversibile.
    assert eventi(testo)[0]["SUMMARY"].startswith("Attività integrative")
    assert env["subject"].name in eventi(testo)[0]["SUMMARY"]


def test_il_testo_e_sfuggito():
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    env["subject"].name = "Storia; geografia, e altro\\"
    env["subject"].save()
    a = make_activity(env["subject"], classes=[env["klass"]])
    place(env["schedule"], a, 0, 0)

    testo, _, _ = esporta(env["schedule"], dtstamp=QUANDO)
    assert "Storia\\; geografia\\, e altro\\\\" in testo


def test_l_ora_e_fluttuante():
    """Le 08:00 di una scuola sono le 08:00 dell'orologio alla parete. Niente
    `Z`, niente `TZID`, niente `VTIMEZONE`: è anche l'unica forma che
    attraversa il cambio d'ora senza spostare le lezioni per metà anno."""
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    place(env["schedule"],
          make_activity(env["subject"], classes=[env["klass"]]), 0, 0)

    testo, _, _ = esporta(env["schedule"], dtstamp=QUANDO)
    ev = eventi(testo)[0]
    assert not ev["DTSTART"].endswith("Z") and "TZID" not in testo
    assert "VTIMEZONE" not in testo
    assert ev["DTSTAMP"].endswith("Z")     # il DTSTAMP invece è UTC per norma


def test_la_busta_e_completa():
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    place(env["schedule"],
          make_activity(env["subject"], classes=[env["klass"]]), 0, 0)

    testo, _, _ = esporta(env["schedule"], dtstamp=QUANDO, nome="Orario 1A")
    righe = _srotola(testo)
    assert righe[0] == "BEGIN:VCALENDAR" and righe[-1] == "END:VCALENDAR"
    assert f"PRODID:{ical.PRODID}" in righe and "VERSION:2.0" in righe
    assert "X-WR-CALNAME:Orario 1A" in righe
    assert testo.endswith("\r\n")


def test_l_aula_assegnata_diventa_il_luogo():
    env = mini_school(days=1, slots=1)
    etichette(env["grid"], [(0, dt.time(8, 0), dt.time(9, 0))])
    lab = Room.objects.create(name="LAB-INF")
    a = make_activity(env["subject"], classes=[env["klass"]],
                      teachers=[env["teacher"]])
    place(env["schedule"], a, 0, 0, room=lab)

    ev = eventi(esporta(env["schedule"], dtstamp=QUANDO)[0])[0]
    assert ev["LOCATION"] == "LAB-INF"
    assert ev["SUMMARY"] == "Italiano · 1A"
    assert "Rossi Anna" in ev["DESCRIPTION"]


# --- la misura --------------------------------------------------------------

def test_fermi_misurato():
    """Il prezzo della scelta «un VEVENT per occorrenza», misurato invece che
    temuto: 33 settimane × 284 attività, **9372 eventi e 1,8 MiB** in mezzo
    secondo. È molto per un file e niente per un calendario, e il file che
    finisce davvero su un telefono è quello di *un* docente: 693 eventi.

    ⚠ **E il Fermi non esercita lo spezzamento, contro la previsione.** Il suo
    orologio ha la pausa fra le 12 e le 14, ma i blocchi da due fasce sono
    **quattro** su 284 e nessuno è atterrato a cavallo della linea — per caso,
    non per regola: nel modello *niente vieta* a un blocco di scavalcare la
    mezza giornata. Il divieto esiste ed è `Break` + `respects_breaks`
    (`structural:grid`), che questo dataset non usa. Quindi il conto è esatto,
    9372 = 284 × 33, e la metà interessante la misura la seconda parte del
    test — spostando a mano un blocco dove il solver non l'ha messo."""
    import time

    from domain.models import Placement
    from domain.solver.model import apply, solve
    from tests import fermi

    dataset = fermi.build()
    schedule = dataset["schedule"]
    apply(solve(schedule, workers=1), schedule)

    t0 = time.perf_counter()
    testo, eventi_n, saltate = esporta(schedule, dtstamp=QUANDO)
    secondi = time.perf_counter() - t0
    kib = len(testo.encode("utf-8")) / 1024
    print(f"\nFermi iCal: {eventi_n} eventi, {kib:.0f} KiB, {secondi:.2f}s")

    assert eventi_n == 284 * fermi.WEEKS_IN_YEAR
    assert saltate == 0                       # nessun festivo nel dataset
    assert len(eventi(testo)) == eventi_n

    # Un docente solo: 21 ore settimanali per 33 settimane.
    from domain import extraction as ex
    uno = ex.per_risorsa([dataset["teachers"]["D01"].pk])
    _, suoi, _ = esporta(schedule, selected=uno, dtstamp=QUANDO)
    print(f"Fermi iCal, un docente: {suoi} eventi")
    assert suoi == 21 * fermi.WEEKS_IN_YEAR

    # E il blocco a cavallo, che il solver non ha prodotto: un'ora in più di
    # lezione dà **33 eventi in più**, non 33 eventi più lunghi.
    blocco = Placement.objects.filter(schedule=schedule,
                                      activity__duration_slots=2).first()
    blocco.day, blocco.start_slot = blocco.day, 3
    blocco.save()
    _, spezzato, _ = esporta(schedule, dtstamp=QUANDO)
    assert spezzato == eventi_n + fermi.WEEKS_IN_YEAR


# ── La sostituzione oscura l'originale ──────────────────────────────────────


def _sostituzione():
    """L'orario minimo di ADR-014: un'ora annuale e un sostituto sulla
    **stessa** cella con la maschera di una settimana sola. È la forma
    verificata sui 161 record di EDT — stessa classe, stessa aula, cambia il
    docente — e l'originale resta annuale, che è la parte che questo test
    esiste per rendere innocua."""
    env = mini_school()
    etichette(env["grid"])
    annuale = make_activity(env["subject"], teachers=[env["teacher"]],
                            classes=[env["klass"]])
    place(env["schedule"], annuale, day=0, slot=0)
    supplente = _docente_supplente()
    sostituto = make_activity(env["subject"], teachers=[supplente],
                              classes=[env["klass"]],
                              mask=weeks.single_week(2))
    place(env["schedule"], sostituto, day=0, slot=0)
    return env, annuale, sostituto


def _docente_supplente():
    from domain.models import Teacher
    return Teacher.objects.create(name="Supplente", last_name="Supplente",
                                  first_name="Ada")


def _settimane_di(occ, activity):
    return sorted({(o.date - dt.date(2026, 9, 14)).days // 7
                   for o in occ if o.activity_id == activity.pk})


def test_la_sostituzione_oscura_l_originale():
    """Il debito chiuso, **col suo ramo di controllo**: senza la relazione le
    due ore compaiono entrambe nella settimana 2 — che è il difetto — e con la
    relazione l'annuale salta quella settimana e basta quella."""
    env, annuale, sostituto = _sostituzione()

    prima, _ = occorrenze(env["schedule"])
    assert _settimane_di(prima, annuale) == [0, 1, 2, 3]
    assert _settimane_di(prima, sostituto) == [2]

    sostituto.substitutes = annuale
    sostituto.save()
    dopo, _ = occorrenze(env["schedule"])
    assert _settimane_di(dopo, annuale) == [0, 1, 3]
    assert _settimane_di(dopo, sostituto) == [2]


def test_la_soppressione_e_per_settimana_non_per_attivita():
    """⚠ La distinzione che il campo deve reggere: `substitutes` non cancella
    l'originale, gli toglie **le settimane del sostituto**. Due sostituti su
    due settimane diverse ne tolgono due, e ciò che resta è ancora l'ora
    annuale — non un residuo da ricostruire altrove."""
    env, annuale, sostituto = _sostituzione()
    sostituto.substitutes = annuale
    sostituto.save()
    altro = make_activity(env["subject"], teachers=[_docente_supplente()],
                          classes=[env["klass"]], mask=weeks.single_week(0))
    altro.substitutes = annuale
    altro.save()
    place(env["schedule"], altro, day=0, slot=0)

    occ, _ = occorrenze(env["schedule"])
    assert _settimane_di(occ, annuale) == [1, 3]


def test_la_sostituzione_non_e_un_conflitto_di_occupazione():
    """🔑 La ragione per cui il filtro non vive nell'export. Sostituto e
    originale stanno sulla **stessa** cella della stessa classe: senza la
    relazione quella settimana ha due ore dove la classe ne ha una, e
    `check_schedule` lo dice — giustamente, perché è ciò che i dati
    affermavano. Con la relazione il conflitto sparisce perché sparisce il
    fatto, non perché qualcuno lo abbia messo a tacere."""
    from domain.analysis.conformity import check_schedule
    from domain.analysis.findings import Severity
    env, annuale, sostituto = _sostituzione()

    prima = [f for f in check_schedule(env["schedule"])
             if f.severity == Severity.HARD and f.code == "resource_occupied"]
    assert prima, [f.code for f in check_schedule(env["schedule"])]

    sostituto.substitutes = annuale
    sostituto.save()
    dopo = [f for f in check_schedule(env["schedule"])
            if f.severity == Severity.HARD and f.code == "resource_occupied"]
    assert dopo == []


def test_un_sostituto_sospeso_non_sopprime_niente():
    """⚠ La sospensione è l'ora che **non si tiene**: se non si tiene il
    rimpiazzo, quella che si tiene è di nuovo l'originale. Senza questa
    esclusione la settimana 2 resterebbe vuota per entrambi — il peggiore dei
    due esiti, perché toglie un'ora invece di sceglierne una."""
    env, annuale, sostituto = _sostituzione()
    sostituto.substitutes = annuale
    sostituto.immobility = Activity.Immobility.SUSPENDED
    sostituto.save()

    occ, _ = occorrenze(env["schedule"])
    assert _settimane_di(occ, annuale) == [0, 1, 2, 3]
    assert _settimane_di(occ, sostituto) == []
