"""L'ondata 3 del banco: l'asse Cardinalità.

Le otto famiglie di `ResourceTimeConstraint` in dieci righe, e tre domande
diverse su ciascuna — perché rispondere solo alla prima è come si costruisce
un dataset «completo» che non prova niente:

1. **Il builder la vede?** Lo dice la sonda (`tests/test_alighieri_sonda.py`),
   che passa da 4 builder attivi a 12. È il filtro che prende in un secondo il
   caso «la riga c'è e nessuno la legge».
2. **Si vede nell'orario?** `test_le_otto_forme_dichiarate` guarda la forma che
   ogni riga deve produrre — la prima fascia vuota, i due giorni interi liberi,
   le ore spinte al pomeriggio — invece di fidarsi dell'assenza di finding.
3. **Morde, o è soddisfatta per caso?** `test_ogni_famiglia_e_al_bordo`: una
   tacca più stretta e il dataset diventa INFEASIBLE. È la verifica per
   mutazione della spec §6.4, nella direzione che si può **dimostrare**.

⚠ **La mutazione per rimozione — «togli la riga e l'orario cambia» — è stata
provata e scartata, e vale la pena scrivere perché.** Il modello di fase 1 non
ha una funzione di costo sopra lo scarto: ogni orario a zero scarti è
*ottimo*, quindi il solver ne restituisce uno arbitrario fra milioni. Togliendo
una riga, se l'orario che torna la viola è un fatto sulla **ricerca**, non
sulla riga: misurato, cambiando una sola riga *estranea* alla famiglia il
verdetto si ribaltava per tre famiglie su nove. Congelarlo in un test
fisserebbe un artefatto della ricerca — lo stesso errore che il tie-break di
`_placed_of` ha insegnato a non fare. La direzione dello **stringimento** non
ha questo difetto: `INFEASIBLE` è una proprietà del modello, non del testimone
che torna."""

import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.analysis.state import ScheduleState, site_occupation
from domain.models import ResourceTimeConstraint, SchoolClass, Teacher
from domain.solver.model import apply, solve
from tests import alighieri

pytestmark = pytest.mark.django_db

MATTINA = range(0, 5)


# Le tacche più strette: (famiglia da sostituire, portatore, tipo, params).
# Ogni riga sostituisce la sua omonima di `TIME_CONSTRAINTS` e deve rendere il
# dataset infattibile. Sono argomenti di **conteggio**, non tarature: 5 × 3 h
# per un docente da 10 ore, 5 × 4 h per uno da 21, dodici ore in una giornata
# da otto fasce, venti ore in tre fasce al giorno, dodici ore in un giorno
# solo, ventotto fasce in cinque mezze giornate da cinque.
STRETTE = {
    "min_distribution": ("t", "URBAN", "min_distribution",
                         {"min_days": 5, "min_minutes_per_day": 180}),
    "max_hours": ("t", "RINAL", "max_hours",
                  {"day_minutes": 240, "morning_minutes": 180}),
    "max_presence": ("t", "GENTI", "max_presence",
                     {"days": 1, "max_minutes": 480}),
    "arrival_departure": ("t", "VITAL", "arrival_departure",
                          {"days": 5, "not_before_slot": 5}),
    "free_guaranteed": ("t", "ZANET", "free_guaranteed",
                        {"free_days": 4, "free_half_days": 2}),
    "max_half_days": ("c", "2A", "max_half_days", {"max_half_days": 5}),
    # Il `MG` non ha una tacca: o c'è o non c'è. Si sposta sulla classe, che
    # con 28 fasce non può stare in cinque mezze giornate da cinque.
    "only_half_day": ("c", "2A", "max_half_days", {"only_half_day_per_day": True}),
    "max_site_changes": ("t", "COLOM", "max_site_changes", {"per_day": 0}),
}


def _risorsa(kind, ref):
    return (Teacher.objects.get(abbreviation=ref) if kind == "t"
            else SchoolClass.objects.get(name=ref))


def _sostituisci(famiglia, kind, ref, tipo, params):
    """Toglie la riga di `famiglia` da `TIME_CONSTRAINTS` e ne mette una più
    stretta al suo posto."""
    for nome, k, r, t, _p in alighieri.TIME_CONSTRAINTS:
        if nome == famiglia:
            ResourceTimeConstraint.objects.filter(
                resource=_risorsa(k, r), type=t).delete()
    ResourceTimeConstraint.objects.create(
        resource=_risorsa(kind, ref),
        type=ResourceTimeConstraint.Type(tipo), params=params)


def _giorni(state, kind, ref):
    return state.resource_days(_risorsa(kind, ref).pk)


def test_le_dieci_righe_ci_sono():
    """Otto famiglie, dieci righe: `max_half_days` ne porta due (il `MMG` e il
    `MG`, che in EDT sono la stessa riga con due caselle) e `max_presence`
    anche — il tempo parziale e il cappellano, che è lì per le sedi."""
    alighieri.build()
    righe = ResourceTimeConstraint.objects.all()
    assert righe.count() == 10
    assert {r.type for r in righe} == set(ResourceTimeConstraint.Type.values)


def test_le_otto_forme_dichiarate():
    """L'orario prodotto, letto famiglia per famiglia.

    ⚠ **`workers=1` è stato tolto dall'ondata 5, ed è una misura.** Fino a
    lì questo test cercava con un lavoratore solo per rendere la ricerca
    riproducibile. I tetti di peso didattico per giornata e per mezza giornata
    hanno cambiato il regime: **7 s a otto lavoratori, 439 s a uno**, sullo
    stesso modello. Ciò che questo test asserisce sono comunque **invarianti**
    — nessuna riga guarda una cella particolare — quindi il portafoglio
    parallelo non toglie niente."""
    env = alighieri.build()
    soluzione = solve(env["schedule"], workers=8)
    assert soluzione.status == "OPTIMAL"
    assert list(soluzione.unplaced) == []
    apply(soluzione, env["schedule"])
    stato = ScheduleState.build(env["schedule"])

    # min_distribution — almeno quattro giornate da due ore per N02.
    urbani = _giorni(stato, "t", "URBAN")
    assert sum(1 for fasce in urbani.values() if len(fasce) >= 2) >= 4

    # max_hours — mattina a 3, giornata a 5: almeno sei ore di pomeriggio.
    rinaldi = _giorni(stato, "t", "RINAL")
    assert all(len(f) <= 5 for f in rinaldi.values())
    assert all(len([s for s in f if s in MATTINA]) <= 3 for f in rinaldi.values())
    pomeriggio = sum(len([s for s in f if s not in MATTINA]) for f in rinaldi.values())
    assert pomeriggio >= 6

    # max_presence — tre giornate, quindi due interamente vuote; e presenza
    # (buchi compresi) al più cinque fasce.
    gentili = _giorni(stato, "t", "GENTI")
    assert len(gentili) == 3
    assert all(f[-1] - f[0] + 1 <= 5 for f in gentili.values())

    # arrival_departure — la prima fascia è libera tutti i giorni.
    assert all(0 not in f for f in _giorni(stato, "t", "VITAL").values())

    # free_guaranteed — due giornate intere libere, e almeno due mezze
    # giornate libere **fra quelle lavorate** (un giorno vuoto ne vale zero).
    zanetti = _giorni(stato, "t", "ZANET")
    assert len(zanetti) <= 3
    mezze_libere = sum((not [s for s in f if s in MATTINA])
                       + (not [s for s in f if s not in MATTINA])
                       for f in zanetti.values())
    assert mezze_libere >= 2

    # max_half_days — il MMG della 2A, e il MG di R02.
    seconda = _giorni(stato, "c", "2A")
    assert sum(bool([s for s in f if s in MATTINA])
               + bool([s for s in f if s not in MATTINA])
               for f in seconda.values()) <= 7
    for fasce in _giorni(stato, "t", "DONAT").values():
        assert not ([s for s in fasce if s in MATTINA]
                    and [s for s in fasce if s not in MATTINA])

    # max_site_changes — due giornate sole, e al più un cambio di sede.
    colombo = _giorni(stato, "t", "COLOM")
    assert len(colombo) == 2
    cambi = 0
    for giorno, fasce in colombo.items():
        sedi = [set(per_fascia) for _s, per_fascia
                in site_occupation(stato, _risorsa("t", "COLOM").pk, giorno, fasce)]
        del_giorno = sum(a != b for a, b in zip(sedi, sedi[1:]))
        assert del_giorno <= 1
        cambi += del_giorno
    assert cambi <= 1

    # max_gap_hours — al più un'ora di buco in tutta la settimana.
    buchi = 0
    for fasce in _giorni(stato, "t", "CAVAL").values():
        for meta in ([s for s in fasce if s in MATTINA],
                     [s for s in fasce if s not in MATTINA]):
            if len(meta) >= 2:
                buchi += meta[-1] - meta[0] + 1 - len(meta)
    assert buchi <= 1

    # E nessuna riga violata, che è l'altra metà: le forme qui sopra dicono
    # *quale* effetto si vede, il checker dice che non ce ne sono di rotti.
    hard = [f for f in check_schedule(env["schedule"]) if f.severity == Severity.HARD]
    assert [f.code for f in hard] == ["room_unassigned"] * 73


@pytest.mark.parametrize("famiglia", sorted(STRETTE))
def test_ogni_famiglia_e_al_bordo(famiglia):
    """Una tacca più stretta e il dataset non sta più in piedi.

    🔑 È la verifica per mutazione di §6.4 nella forma dimostrabile: se
    stringere di una tacca rende il modello infattibile, la riga *non* può
    essere soddisfatta per caso — sta esattamente sul bordo di ciò che il
    dataset concede. `allow_unplaced=False` serve a leggere `INFEASIBLE`
    invece di uno scarto: sono la stessa cosa detta da due porte diverse."""
    env = alighieri.build()
    _sostituisci(famiglia, *STRETTE[famiglia])
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=90)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


def test_il_dtb_non_e_al_bordo_ed_e_una_misura():
    """⚠ **La nona famiglia non ci arriva, e non si finge il contrario.**

    Il D.T.B. è l'unica riga dell'ondata 3 che il dataset non porta al bordo:
    non solo `max_gap_minutes = 0` su L03 resta risolvibile, ma lo resta
    **zero buchi per ogni docente e per ogni classe insieme**. La ragione è
    strutturale e si misura: 40 fasce a settimana contro cattedre da 10–21 ore
    e classi da 28–32: la contiguità dentro una mezza giornata è gratis.

    Stringerla vuole una griglia più densa o un carico più alto. La riga
    resta **esercitata** — la sonda la vede, e la forma si legge su L03 — ma
    non è al bordo, e questo test lo tiene scritto invece di lasciarlo intuire
    da un test che manca.

    ⚠ **L'ondata 7 ha misurato il criterio di §4 e questo test resta verde, ed
    è corretto.** «Stretto ma risolvibile» è verificato — togliendo il
    laboratorio unico della succursale il banco scarta 11 attività, togliendo
    un docente le sue — ma sono **due nozioni diverse di stretto**: quella è
    stretta rispetto alle **risorse**, la contiguità che il D.T.B. chiede è
    stretta rispetto alla **densità della griglia**. Quaranta fasce contro
    cattedre da 10–21 ore la rendono gratis, e per negarla servirebbe un altro
    banco. Il «diventerà rosso all'ondata 7» che stava scritto qui era quindi
    sbagliato: l'ondata 7 stringe le risorse, non la griglia."""
    env = alighieri.build()
    for docente in Teacher.objects.all():
        ResourceTimeConstraint.objects.update_or_create(
            resource=docente, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
            defaults={"params": {"max_gap_minutes": 0}})
    for classe in SchoolClass.objects.all():
        ResourceTimeConstraint.objects.create(
            resource=classe, type=ResourceTimeConstraint.Type.MAX_GAP_HOURS,
            params={"max_gap_minutes": 0})

    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=90)
    assert soluzione.status == "OPTIMAL", soluzione.stats
