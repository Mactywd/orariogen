"""L'ondata 5 del banco: le risorse, il peso didattico e le indisponibilità.

Tre famiglie in un'ondata sola, e stanno insieme per una ragione aritmetica:
sono **tutto ciò che manca** perché la sonda arrivi al registro intero. I due
builder che l'ondata 4 lasciava fuori — `structural:unavailability` e
`structural:didactic_weight` — sono qui, e con loro le due risorse di
piazzamento che nessun dataset aveva mai avuto: un tecnico di laboratorio e
tre carrelli di portatili.

🔑 **Il contratto è misto, e questa è la prima ondata in cui succede.** Le
ondate 3 e 4 hanno ciascuna una forma di verifica; qui servono entrambe, e
quale delle due valga lo decide la natura della riga, non il gusto:

- un'**indisponibilità** è un divieto sul piazzamento → testimone puntato
  (ondata 4): si impone la cella vietata, `INFEASIBLE` con la riga e
  `OPTIMAL` senza;
- lo **spezzone di RICCI** è un conteggio (tre ore in tre fasce) → tacca
  (ondata 3): una fascia rossa in più e il modello non sta in piedi;
- il tetto di peso **settimanale** non ammette né l'uno né l'altra, e il
  perché è la cosa più istruttiva dell'ondata: la somma dei pesi di
  un'unità-studente lungo la settimana **non dipende da dove le attività
  vanno**. Un pin non la può violare. Resta la tacca.

⚠ E i tre livelli di indisponibilità **non** si provano allo stesso modo,
perché non fanno la stessa cosa: la rossa vieta, la gialla vieta *ma* può
essere autorizzata per **tipo** di risorsa, la verde non vieta affatto. Tre
affermazioni diverse, tre test diversi."""

import pytest

from domain.models import (
    Activity, ActivityMaterialRequirement, InstituteSettings, Material,
    Resource, ResourceUnavailability, Room, SchoolClass, StaffMember, Subject,
    Teacher,
)
from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.analysis.state import ScheduleState, site_occupation
from domain.solver.model import apply, solve
from domain.solver.rooms import solve_rooms
from tests import alighieri

pytestmark = pytest.mark.django_db


def _cl(classe, materia, durata=1):
    return list(Activity.objects.filter(classes__name=classe,
                                        subject__code=materia,
                                        duration_slots=durata).order_by("pk"))


def _parte(parte, materia):
    return list(Activity.objects.filter(parts__name=parte,
                                        subject__code=materia).order_by("pk"))


def _gruppo(nome):
    return list(Activity.objects.filter(groups__name=nome).order_by("pk"))


def _righe(nome):
    """Il queryset delle righe di `INDISPONIBILITA` che si chiamano `nome`."""
    for n, kind, ref, livello, celle in alighieri.INDISPONIBILITA:
        if n != nome:
            continue
        modello = {"t": Teacher, "c": SchoolClass, "r": Room}[kind]
        campo = {"t": "abbreviation", "c": "name", "r": "name"}[kind]
        return ResourceUnavailability.objects.filter(
            resource=modello.objects.get(**{campo: ref}), level=livello)
    raise KeyError(nome)


# ---------------------------------------------------------------- l'anagrafica

def test_le_sei_righe_di_indisponibilita_nei_tre_livelli():
    """Tre livelli **e** tre tipi di risorsa, che è il punto: il meccanismo è
    generico sulla risorsa (`docs/edt/vincoli.md`), e un dataset che mettesse
    le indisponibilità solo sui docenti non lo mostrerebbe."""
    alighieri.build()
    righe = ResourceUnavailability.objects.all()
    assert righe.count() == 55           # 37 + 3 + 5 + 3 + 2 + 5
    assert ({r.level for r in righe}
            == set(ResourceUnavailability.Level.values))
    assert {r.resource.kind for r in righe} == {
        Resource.Kind.TEACHER, Resource.Kind.CLASS, Resource.Kind.ROOM}
    # ⚠ Nessuna riga **datata**, e non è una dimenticanza: una sola
    # indisponibilità con `date` valorizzata spacca l'anno in due firme di
    # settimana (`domain/analysis/conformity.week_signatures`), che è materia
    # dell'ondata 6. Qui la tabella è la stessa — indisponibilità e assenze —
    # ma il banco resta a una firma.
    assert not righe.exclude(date=None).exists()


def test_le_due_risorse_che_nessun_dataset_aveva():
    """`Resource` prevede cinque tipi da sempre — è il pannello dell'attività
    di EDT — e il personale e i materiali non ne avevano mai visto uno."""
    env = alighieri.build()
    assert StaffMember.objects.count() == 1
    assert Material.objects.count() == 1
    assert env["tecnico"].role == "Tecnico di laboratorio"
    assert env["carrelli"].simultaneous_capacity == 4

    # Il tecnico: i tre blocchi di fisica del triennio scientifico, le quattro
    # ore di laboratorio a mezza classe e — dall'**ondata 6** — la metà di
    # laboratorio dell'ora quindicinale del 5B.
    col_tecnico = Activity.objects.exclude(staff=None)
    assert col_tecnico.count() == 8
    assert {a.subject.code for a in col_tecnico} == {"FIS", "SCI"}

    # I carrelli: uno ogni dodici alunni, e solo dove si lavora a piccoli
    # gruppi. 🔑 La **quantità** è ciò che rende l'occupazione cumulativa
    # invece che binaria, e nessun altro dato del progetto la esercita.
    richieste = ActivityMaterialRequirement.objects.all()
    assert richieste.count() == 13
    per_unita = {}
    for r in richieste.select_related("activity"):
        gruppi = [g.name for g in r.activity.groups.all()]
        parti = [p.name for p in r.activity.parts.all()]
        per_unita[(gruppi or parti)[0]] = r.quantity
    assert per_unita == {"ING1-BASE": 2, "ING1-AVANZ": 2, "2C_APP": 1,
                         "3A_G1": 2, "3A_G2": 2, "4A_G1": 2, "4A_G2": 2}


def test_i_pesi_e_i_tetti():
    """⚠ In una base reale del prodotto i quattro tetti d'istituto sono a
    «nessuno» e ogni materia pesa 1 — il Fermi è fedele, ed è per questo che
    `structural:didactic_weight` non aveva mai visto un dato."""
    alighieri.build()
    assert {s.code for s in Subject.objects.filter(didactic_weight=2)} == {
        "MAT", "LAT", "GRE"}
    s = InstituteSettings.load()
    assert (s.max_weight_morning, s.max_weight_afternoon, s.max_weight_day) == (
        9, 5, 12)
    # 🔑 Il settimanale d'istituto resta spento: sul 3B lo porta la
    # **classe**, ed è l'unico modo di esercitare il ramo che prevale.
    assert s.max_weight_week is None
    caps = dict(SchoolClass.objects.values_list("name",
                                                "max_weekly_weight_per_student"))
    assert caps.pop("3B") == 40
    assert set(caps.values()) == {None}


# --------------------------------------------------- le indisponibilità, rosse

def test_lo_spezzone_di_ricci_e_al_bordo():
    """La tacca dell'ondata 3, e qui è un conteggio nudo: RICCI ha **tre** ore
    e viene un pomeriggio, cioè tre fasce. Una fascia rossa in più e le tre
    ore non ci stanno.

    ⚠ `allow_unplaced=False` legge `INFEASIBLE` invece di uno scarto: sono la
    stessa cosa detta da due porte diverse."""
    env = alighieri.build()
    ResourceUnavailability.objects.create(
        resource=Teacher.objects.get(abbreviation="RICCI"), day=2, slot=7,
        level=ResourceUnavailability.Level.HARD)
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=90)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


# I testimoni puntati delle rosse e della gialla: (riga, come si costruisce il
# pin). ⚠ Ogni pin è **minimale** — una sola attività nella cella vietata —
# quindi il ramo di controllo non può fallire per un conflitto d'occupazione.
def _pin_indisponibilita(nome):
    if nome == "orientamento":       # la 5A non c'è, il mercoledì pomeriggio
        return {_cl("5A", "ITA")[0].pk: (2, 5)}
    if nome == "palestra":           # la palestra è della scuola media
        return {_cl("1A", "MOT", 2)[0].pk: (0, 0)}
    if nome == "permesso":           # il permesso del venerdì pomeriggio
        return {_cl("5B", "MAT")[0].pk: (4, 5)}
    if nome == "manutenzione":       # il laboratorio della succursale è chiuso
        return {_cl("1C", "FIS")[0].pk: (0, 0)}
    raise KeyError(nome)


@pytest.mark.parametrize("nome", ["orientamento", "palestra"])
def test_le_rosse_mordono_col_testimone_puntato(nome):
    """🔑 Su **due tipi di risorsa diversi**, e con lo stesso identico
    contratto: è ciò che significa «il meccanismo è generico sulla risorsa».

    ⚠ L'indisponibilità è un **pre-filtro del dominio**, non un constraint, e
    si vede: la cella sparisce prima che il modello nasca, quindi il pin
    finisce fuori dominio e il solver lo dichiara — `pin_fuori_dominio`. È una
    differenza di meccanismo che vale la pena tenere sotto asserzione, perché
    un giorno in cui l'indisponibilità diventasse un constraint questo test
    lo direbbe."""
    env = alighieri.build()
    pin = _pin_indisponibilita(nome)
    con = solve(env["schedule"], workers=8, time_limit=60, pinned=pin)
    assert con.status == "INFEASIBLE", con.stats
    assert con.stats["pin_fuori_dominio"] != ()

    quante = next(len(celle) for n, _k, _r, _l, celle
                  in alighieri.INDISPONIBILITA if n == nome)
    assert _righe(nome).delete()[0] == quante
    senza = solve(env["schedule"], workers=8, time_limit=60, pinned=pin)
    assert senza.status == "OPTIMAL", senza.stats
    assert list(senza.unplaced) == []


def test_il_verde_non_vieta_ed_e_un_contro_testimone():
    """La terza affermazione sui tre livelli, e l'unica che si prova al
    contrario: il verde è una **preferenza**, quindi il suo posto è un livello
    di qualità della catena, non un pre-filtro del dominio. Se un giorno
    restringesse, questo test diventerebbe rosso — che è esattamente ciò che
    si vuole, perché sarebbe il solver a farsi più severo di EDT."""
    env = alighieri.build()
    amato = _righe("preferenza")
    assert amato.count() == 5
    pin = {_cl("1A", "ITA")[0].pk: (0, 0)}   # la prima ora, che AMATO evita
    soluzione = solve(env["schedule"], workers=8, time_limit=60, pinned=pin)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert list(soluzione.unplaced) == []


# ---------------------------------------------------- le gialle, e l'override

@pytest.mark.parametrize("nome,tipo,altro", [
    ("permesso", Resource.Kind.TEACHER, Resource.Kind.ROOM),
    ("manutenzione", Resource.Kind.ROOM, Resource.Kind.TEACHER),
])
def test_la_gialla_vieta_finche_non_la_si_autorizza(nome, tipo, altro):
    """🔑 **La misura di A4**: *«Piazza le attività anche sulle fasce con
    indisponibilità opzionali»* è un'opzione di calcolo **per tipo di
    risorsa**, non una quota e non una deroga sulla singola riga. Le due
    parametrizzazioni la provano nei due versi — autorizzare i docenti non
    tocca le aule, e viceversa — che è l'unico modo di distinguere «per
    categoria» da «per riga» con una riga sola per categoria.

    Ed è anche la differenza fra giallo e rosso, tutta intera: senza
    l'autorizzazione i due livelli si comportano allo stesso modo."""
    env = alighieri.build()
    pin = _pin_indisponibilita(nome)
    assert solve(env["schedule"], workers=8, time_limit=60,
                 pinned=pin).status == "INFEASIBLE"
    assert solve(env["schedule"], workers=8, time_limit=60, pinned=pin,
                 ignora_opzionali=(altro,)).status == "INFEASIBLE"
    liberato = solve(env["schedule"], workers=8, time_limit=60, pinned=pin,
                     ignora_opzionali=(tipo,))
    assert liberato.status == "OPTIMAL", liberato.stats
    assert list(liberato.unplaced) == []


# ------------------------------------------------------------ il peso didattico

# I tre tetti che dipendono dal piazzamento, col testimone puntato. Ogni pin
# sfora **un solo** secchio: quello della giornata tiene la mattina a 9 e il
# pomeriggio a 4 apposta, o direbbe `INFEASIBLE` per il tetto sbagliato.
TETTI = {
    # Quattro ore di latino (2 punti l'una) e una di greco in una mattina: 10.
    "morning": (lambda: {**{_cl("3B", "LAT")[i].pk: (0, i) for i in range(4)},
                         _cl("3B", "GRE")[0].pk: (0, 4)}, 10),
    # Due ore di matematica e una di latino in un pomeriggio da tre fasce: 6.
    "afternoon": (lambda: {_cl("3B", "MAT")[0].pk: (0, 5),
                           _cl("3B", "MAT")[1].pk: (0, 6),
                           _cl("3B", "LAT")[0].pk: (0, 7)}, 6),
    # Nove in mattinata (il tetto esatto) più quattro di pomeriggio: 13.
    "day": (lambda: {**{_cl("3B", "LAT")[i].pk: (0, i) for i in range(4)},
                     _cl("3B", "ITA")[0].pk: (0, 4),
                     _cl("3B", "GRE")[0].pk: (0, 5),
                     _cl("3B", "GRE")[1].pk: (0, 6)}, 13),
}


@pytest.mark.parametrize("secchio", sorted(TETTI))
def test_i_tre_tetti_di_peso_mordono(secchio):
    env = alighieri.build()
    costruisci, _peso = TETTI[secchio]
    pin = costruisci()
    con = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert con.status == "INFEASIBLE", con.stats
    # ⚠ E **non** per il pre-filtro: il peso è un constraint, non un dominio
    # ristretto. Se il pin finisse fuori dominio il test direbbe INFEASIBLE
    # per il motivo sbagliato.
    assert con.stats["pin_fuori_dominio"] == ()

    s = InstituteSettings.load()
    setattr(s, f"max_weight_{secchio}", None)
    s.save()
    senza = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert senza.status == "OPTIMAL", senza.stats
    assert list(senza.unplaced) == []


def test_il_tetto_settimanale_non_ha_un_testimone_puntato_e_ha_una_tacca():
    """🔑 **Il tetto inevadibile**, che `CLAUDE.md` porta fra i punti aperti.

    La somma dei pesi di un'unità-studente lungo la settimana non dipende da
    dove le attività vanno: ogni ora pesa ovunque la si metta. Quindi nessun
    pin lo può violare — non esiste una configurazione vietata da imporre — e
    l'unica leva che il modello ha per rispettarlo è **scartare**. Il suo
    contratto è quindi la tacca dell'ondata 3, e a `allow_unplaced=False` la
    tacca parla.

    ⚠ Vale la pena scriverlo perché è la differenza fra un vincolo che
    *forma* l'orario e uno che si limita ad ammetterlo o rifiutarlo, e i due
    non si provano allo stesso modo. 40 è esattamente il peso settimanale
    delle due unità-studente del 3B: 39 di classe più l'ora di IRC o di
    alternativa."""
    env = alighieri.build()
    SchoolClass.objects.filter(name="3B").update(
        max_weekly_weight_per_student=39)
    soluzione = solve(env["schedule"], workers=8, allow_unplaced=False,
                      time_limit=90)
    assert soluzione.status == "INFEASIBLE", soluzione.stats


# --------------------------------------------------- il tecnico e i carrelli

def test_il_tecnico_e_uno_solo():
    """Due laboratori non possono essere simultanei, ed è il vincolo vero
    delle scuole. Nel nostro modello non è una famiglia nuova: il tecnico è
    una **chiave di occupazione** come un docente o un'aula, e questo test
    dice che ci entra davvero.

    ⚠ Il pin sceglie due laboratori che non condividono nient'altro — parti
    diverse, docenti diversi, aule candidate diverse — o il ramo di controllo
    direbbe `INFEASIBLE` per un conflitto che non è il tecnico."""
    env = alighieri.build()
    pin = {_parte("4A_G1", "SCI")[0].pk: (0, 0),
           _cl("5A", "FIS", 2)[0].pk: (0, 0)}
    con = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert con.status == "INFEASIBLE", con.stats

    StaffMember.objects.all().delete()
    senza = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert senza.status == "OPTIMAL", senza.stats
    assert list(senza.unplaced) == []


def test_i_carrelli_sono_una_capienza_cumulativa():
    """🔑 La **quantità** al lavoro: la scuola ha quattro carrelli, i due
    livelli d'inglese ne chiedono due l'uno e un laboratorio a mezza classe
    altri due. Non è l'esclusione mutua di una risorsa singola — i due livelli
    d'inglese nella stessa fascia ci stanno, e ci devono stare (ondata 2) — è
    `2 + 2 + 2 > 4`, cioè il ramo **cumulativo** di `structural:occupation`,
    che nessun dataset aveva mai acceso."""
    env = alighieri.build()
    pin = {_gruppo("ING1-BASE")[0].pk: (0, 2),
           _gruppo("ING1-AVANZ")[0].pk: (0, 2),
           _parte("3A_G1", "SCI")[0].pk: (0, 2)}
    con = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert con.status == "INFEASIBLE", con.stats

    ActivityMaterialRequirement.objects.all().delete()
    senza = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert senza.status == "OPTIMAL", senza.stats
    assert list(senza.unplaced) == []


# ------------------------------------- ⚠ i due difetti che l'ondata ha trovato

def test_il_carrello_non_puo_servire_due_sedi_e_non_e_la_capienza():
    """⚠ **Difetto L6**, e il banco lo ha trovato costruendo la sua unica
    risorsa **senza sede**.

    Tre carrelli sono della scuola, non di un edificio: servono l'inglese alla
    centrale e l'informatica in succursale. Ma `structural:site_transition`
    posta la clausola «due sedi sulla stessa fascia» su **ogni** chiave di
    occupazione, e per il carrello quella clausola è falsa — un insieme di tre
    carrelli non è un corpo solo, e non viaggia.

    Le tre esecuzioni qui sotto sono la dimostrazione che il colpevole è la
    sede e non la capienza:

    1. capienza 3, domanda 2 + 1 = 3: entrerebbe, e invece `INFEASIBLE`;
    2. capienza 9, stessa cella: ancora `INFEASIBLE` — quindi non è capienza;
    3. stessa capienza 3, stessa cella, **stessa sede**: `OPTIMAL` a zero
       scarti.

    ⚠ Non riparato, per la regola della spec (§8: il banco non modifica il
    motore). Il test asserisce il comportamento **corrente**, così diventa
    rosso il giorno in cui si ripara."""
    env = alighieri.build()
    inf = _parte("2C_APP", "INF")[0]
    base = _gruppo("ING1-BASE")[0]
    pin = {base.pk: (2, 5), inf.pk: (2, 5)}   # il pomeriggio in cui RICCI c'è

    assert solve(env["schedule"], workers=8, time_limit=90,
                 pinned=pin).status == "INFEASIBLE"
    env["carrelli"].simultaneous_capacity = 9
    env["carrelli"].save()
    assert solve(env["schedule"], workers=8, time_limit=90,
                 pinned=pin).status == "INFEASIBLE"

    env["carrelli"].simultaneous_capacity = 3
    env["carrelli"].save()
    base.site = inf.site
    base.save()
    stessa = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert stessa.status == "OPTIMAL", stessa.stats
    assert list(stessa.unplaced) == []


def test_adr_019_dentro_una_fascia_non_si_viaggia_e_il_carrello_lo_mostra():
    """🔑 ADR-019 su un dato vero, e il carrello è l'unica risorsa del
    progetto che possa mostrarlo.

    *Dentro una fascia non si viaggia*: una fascia contribuisce l'**insieme**
    delle sedi che la occupano, e due sedi simultanee valgono **zero** cambi.
    A capienza 1 la regola coincide riga per riga con la vecchia, quindi
    serviva una chiave a capienza cumulativa toccata da due sedi — che nessun
    dataset aveva.

    Il test scrive l'orario a mano, perché il solver quella configurazione la
    vieta (vedi il difetto qui sopra): è l'analisi di un orario *già scritto*,
    che è dove ADR-019 vive."""
    env = alighieri.build()
    inf = _parte("2C_APP", "INF")[0]
    base = _gruppo("ING1-BASE")[0]
    for a in (inf, base):
        env["schedule"].placements.create(activity=a, day=0, start_slot=0)
    stato = ScheduleState.build(env["schedule"])

    chiave = env["carrelli"].pk
    sedi = dict(site_occupation(stato, chiave, 0, [0]))
    assert set(sedi[0]) == {inf.site_id, base.site_id}
    # Due sedi in una fascia: nessuna **transizione**, perché non c'è una
    # fascia successiva con un insieme diverso.
    assert not [f for f in check_schedule(env["schedule"])
                if f.code == "max_site_changes"]
    # E invece l'impossibilità c'è, e la nomina l'altro checker.
    trasferte = [f for f in check_schedule(env["schedule"])
                 if f.code == "site_transition" and chiave in f.resources]
    assert trasferte and trasferte[0].severity == Severity.HARD


def test_il_giallo_su_un_aula_a_piu_candidate_costa_una_rinuncia():
    """⚠ **Difetto L6bis**, e nasce da una domanda che l'ondata si è posta
    scegliendo *dove* mettere l'indisponibilità gialla di un'aula.

    Le due fasi leggono il giallo in modo diverso:

    - `structural:room_pool` (fase 1) conta i posti dell'aula come se fosse
      libera — il suo commento lo dichiara, e la ragione è che l'opzionale è
      violabile per definizione;
    - `RoomsContext._filtra` (fase 2) toglie l'aula dalle candidate esattamente
      come per una rossa, se non si autorizza l'override.

    Su un'aula a **candidata unica** non si vede: l'aula è un token, e il
    pre-filtro di `structural:unavailability` — che il giallo lo rispetta —
    toglie la cella prima. Su un'aula a più candidate la fase 1 piazza e la
    fase 2 **rinuncia**, che è esattamente ciò che ADR-021 esiste per non far
    succedere.

    ⚠ Non riparato (§8). Il dataset porta quindi la sua gialla su `LAB-SUCC`,
    a candidata unica, e il difetto vive qui: due attività di fisica delle
    sole `{LAB-FIS, LAB-INF}` imposte sulla fascia gialla, e la fase 2 può
    servirne una sola."""
    env = alighieri.build()
    ResourceUnavailability.objects.create(
        resource=env["rooms"]["LAB-INF"], day=0, slot=0,
        level=ResourceUnavailability.Level.OPTIONAL)
    pin = {_cl("1A", "FIS")[0].pk: (0, 0), _cl("3B", "FIS")[0].pk: (0, 0)}

    fase1 = solve(env["schedule"], workers=8, time_limit=90, pinned=pin)
    assert fase1.status == "OPTIMAL", fase1.stats   # la fase 1 non la vede
    apply(fase1, env["schedule"])

    fase2 = solve_rooms(env["schedule"], workers=8)
    assert len(list(fase2.unassigned)) == 1
    rinuncia = Activity.objects.get(pk=list(fase2.unassigned)[0])
    assert rinuncia.subject.code == "FIS"
    # E l'override della categoria aule la ricompone, che è l'altra metà della
    # prova: la rinuncia viene dal giallo, non da una scarsità vera.
    liberata = solve_rooms(env["schedule"], workers=8,
                           ignora_opzionali=(Resource.Kind.ROOM,))
    assert list(liberata.unassigned) == []
