"""L'ondata 7 del banco: **i comandi**.

Le sei ondate precedenti provano proprietà del **modello** — la tacca, il
testimone puntato, la tensione con la quota. Questa prova una proprietà del
**dataset**, ed è la domanda di §7 della spec: *i comandi hanno qualcosa di
vero da dire su questa scuola?* Un comando diagnostico che gira e risponde
«niente da segnalare» è verde e non prova niente; è lo stesso rischio di §6,
alla scala del prodotto invece che a quella del builder.

🔑 **Il metro è sempre il Fermi**, e la ragione è quella di §1: il Fermi non è
stato progettato per superare i nostri test, quindi ciò che *non* riesce a far
dire a un comando misura una lacuna vera del dataset — non un difetto del
comando. La classifica dei vincoli ne è l'esempio letterale: sul Fermi sono
**tre indisponibilità**, che è la frase con cui §7 dichiara insufficiente quel
risultato.

In coda ci sono due cose che i comandi non misurano ma l'ondata sì: il criterio
**«stretto ma risolvibile»** di §4 — l'ultimo della spec rimasto senza verdetto
— e il difetto che misurarlo ha trovato, **L8**.

⚠ **Due strumenti di questo file non sono modifiche al motore** e vanno
riconosciuti come tali: `pinned=` è un parametro pubblico di `solve` — lo
stesso dell'ondata 4 — e la rimozione di un builder dal registro avviene
avvolgendo `all_builders`, come fa `tests/sonda.py`. Nessun `if` di test entra
in `domain/`.
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from domain import extraction as ex
from domain.analysis.blame import famiglie_silenziose, rank_constraints
from domain.analysis.conformity import check_schedule
from domain.analysis.hall import analyze_hall
from domain.models import (
    Activity, Extraction, Placement, QualityCriterion,
    ResourceTimeConstraint, ResourceUnavailability, Room, SchoolClass,
    Teacher,
)
from domain.solver import model as M
from domain.solver.model import apply, solve
from domain.solver.place_and_fix import place_and_fix
from domain.solver.quality import Arbitrato
from domain.solver.rooms import solve_rooms
from tests import alighieri, fermi

pytestmark = pytest.mark.django_db

K = QualityCriterion.Kind
P = QualityCriterion.Population

#: Le nove coppie (classe, materia) che la variante **satura** libera. Sono
#: scelte fra le unità che portano una riga dell'asse Relazione (ondata 4) e
#: una dell'asse Cardinalità (ondata 3): liberare *una* occorrenza per coppia
#: lascia le sorelle congelate, ed è ciò che fa scattare le famiglie
#: relazionali — un vincolo fra due ore non ha soggetto se sono libere
#: entrambe.
SATURE = [("5A", "FIS"), ("4B", "GRE"), ("3B", "GRE"), ("4A", "MAT"),
          ("2A", "MAT"), ("3B", "ITA"), ("5B", "GRE"), ("3A", "FIS"),
          ("1B", "LAT")]


def _orario_pieno(qualita=False):
    """Il banco calcolato e scritto: il punto di partenza di ogni comando.

    ⚠ Nessun comando diagnostico dice niente di interessante su un orario
    vuoto, e non è un dettaglio di comodo: `free_candidates` **spiazza tutte
    le candidate** prima di calcolare i domini, quindi su un orario dove
    nessuna attività è congelata la pressione reciproca non esiste e la
    classifica vede solo le famiglie *unarie*. Misurato: 3 causali sul dataset
    a riposo contro 15 sulla variante satura."""
    env = alighieri.build(qualita=qualita)
    soluzione = solve(env["schedule"], workers=8)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    apply(soluzione, env["schedule"])
    return env


def _satura(env):
    """Congela tutto tranne nove occorrenze, e le spiazza.

    È la situazione in cui EDT si trova quando l'utente chiede *«quale vincolo
    allento?»*: un orario quasi fatto e poche attività che non trovano posto.
    """
    liberi = []
    for classe, materia in SATURE:
        liberi += list(Activity.objects
                       .filter(classes__name=classe, subject__code=materia)
                       .order_by("pk").values_list("pk", flat=True))[:1]
    Activity.objects.exclude(pk__in=liberi).update(
        immobility=Activity.Immobility.FIXED)
    Placement.objects.filter(schedule=env["schedule"],
                             activity_id__in=liberi).delete()
    return liberi


def _senza_pool(fn):
    """Esegue `fn` con `structural:room_pool` tolto dal registro.

    ⚠ Non è una modifica al motore: è lo stesso avvolgimento di
    `tests/sonda.py`, e serve a misurare **cosa cambia** ADR-021 su questo
    dataset. Senza un modo di spegnerlo, «il gruppo di aule risolve la
    contesa» resterebbe un'affermazione senza controprova."""
    originale = M.all_builders
    M.all_builders = lambda: [b for b in originale()
                              if type(b).__name__ != "RoomPoolBuilder"]
    try:
        return fn()
    finally:
        M.all_builders = originale


# --------------------------------------------------------------------------
# 1. `analyze` — la classifica deve ordinare famiglie **diverse**
# --------------------------------------------------------------------------

def test_la_classifica_ordina_famiglie_diverse():
    """§7: *«una classifica di blame che ordina famiglie diverse, non tre
    indisponibilità»*.

    🔑 **E la differenza col Fermi non è di quantità, è di natura.** Là le
    uniche righe che escludono celle sono le indisponibilità dei docenti,
    perché non c'è nient'altro da ordinare: zero `ResourceTimeConstraint`,
    zero `SubjectConstraint`. Qui la prima riga della classifica è un vincolo
    di **materia**, e sotto ci sono l'occupazione, i tetti orari, il cambio di
    sede e l'intervallo."""
    env = _orario_pieno()
    _satura(env)
    report = rank_constraints(env["schedule"])
    codici = {r.code for r in report.rows}
    assert len(codici) >= 10, sorted(codici)
    # Le tre famiglie che il Fermi ha, più almeno una per asse del banco.
    assert {"resource_occupied_locked", "unavailability"} <= codici
    assert any(c.startswith("subject_") for c in codici), sorted(codici)
    assert {"max_presence", "max_half_days"} & codici, sorted(codici)
    # ⚠ La prima riga **non** è un'indisponibilità: è ciò che §7 chiede.
    assert report.rows[0].code != "unavailability"
    assert report.considered == len(SATURE)


def test_e_sul_fermi_sono_tre_indisponibilita():
    """La misura di §7, verificata invece che citata.

    ⚠ Questo test non chiede al Fermi di migliorare — è una trascrizione, e
    non si tocca per far passare niente. Fissa il numero perché la frase «tre
    indisponibilità» resti una misura."""
    env = fermi.build()
    report = rank_constraints(env["schedule"])
    assert {r.code for r in report.rows} == {"unavailability"}
    assert len(report.rows) == 3


def test_il_comando_analyze_stampa_la_classifica_e_dichiara_le_silenziose():
    """Il comando, non la funzione: è il rendiconto che un vicepreside legge.

    🔑 **La riga sulle famiglie silenziose è la parte che vale.** Una
    classifica che tacesse sul D.T.B. — uno dei vincoli che le scuole
    allentano più spesso — sembrerebbe dire «il D.T.B. non c'entra». Il
    comando dichiara invece *perché* non entra in classifica, che è
    l'informazione onesta."""
    env = _orario_pieno()
    _satura(env)
    out = StringIO()
    with pytest.raises(CommandError):        # 73 aule da assegnare: incoerenze
        call_command("analyze", "--schedule", str(env["schedule"].pk),
                     "--no-hall", stdout=out)
    testo = out.getvalue()
    assert "== Vincoli da allentare (per fallimenti causati) ==" in testo
    assert f"{len(SATURE)} attività esaminate" in testo
    assert "Attività che tornerebbero piazzabili:" in testo
    assert "Non entrano in classifica, per costruzione:" in testo
    assert "max_gap_hours" in testo          # il D.T.B., nominato
    assert "max_gap_hours" in famiglie_silenziose()


# --------------------------------------------------------------------------
# 2. `analyze` — un deficit di Hall **vero**
# --------------------------------------------------------------------------

def test_a_riposo_nessun_insieme_e_deficiente():
    """⚠ **È un atteso, non un contorno.** Un banco che desse un deficit di
    Hall a riposo sarebbe rotto, non teso: la fase 5 dimostra
    l'*impossibilità*, e un dataset che il solver risolve non può contenerne
    una."""
    env = alighieri.build()
    assert analyze_hall(env["schedule"]) == []


def test_il_laboratorio_unico_della_succursale_produce_un_deficit_vero():
    """Il portatore è dichiarato da `aule.md` fin dall'ondata 1: la succursale
    ha **un** laboratorio e nessun ripiego, e undici ore la settimana se lo
    contendono. Ridotto al solo mercoledì, il teorema di Hall in forma
    deficitaria lo nomina.

    ⚠ **Il deficit non è «undici ore meno otto celle»**, ed è la prima attesa
    di quest'ondata a essere smentita. Il certificato di Hall è un **insieme**
    minimale, non un totale: la riduzione si ferma su nove attività la cui
    finestra comune vale otto ore, e dichiara 9h00 contro 8h00. Un totale
    direbbe un numero più grande su un insieme più grande, e sarebbe un
    consiglio peggiore — l'utente deve sapere *quali* attività non stanno."""
    env = alighieri.build()
    lab = Room.objects.get(name="LAB-SUCC")
    assert Activity.objects.filter(rooms=lab).count() == 11
    for day in (0, 1, 3, 4):
        for slot in range(8):
            ResourceUnavailability.objects.create(
                resource=lab, day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)

    trovati = analyze_hall(env["schedule"])
    assert len(trovati) == 1
    f = trovati[0]
    assert f.binding_label == "LAB-SUCC"
    assert "LAB-SUCC" in f.resource_labels
    assert f.required_minutes > f.placeable_minutes
    assert f.n_activities == len(f.activities)


# --------------------------------------------------------------------------
# 3. `Estrai` — almeno un'attività per ciascuno dei sei rilevatori
# --------------------------------------------------------------------------

def _guasta(env):
    """I cinque guasti, uno per rilevatore. Il sesto non si inietta.

    ⚠ Si scrivono uno per uno perché **nessun orario sano li produce
    insieme**, ed è il punto: i rilevatori di EDT servono a trovare ciò che
    una mano umana ha rotto, non ciò che il solver produce."""
    s = env["schedule"]
    lunga = Activity.objects.filter(duration_slots=2,
                                    respects_breaks=True).first()
    Placement.objects.filter(schedule=s, activity=lunga).update(day=0,
                                                               start_slot=4)
    altra = (Activity.objects.filter(duration_slots=2)
             .exclude(pk=lunga.pk).first())
    Placement.objects.filter(schedule=s, activity=altra).update(day=1,
                                                                start_slot=7)
    # Due sedi in fasce adiacenti: il trasferimento non ci sta.
    nomade = Teacher.objects.get(abbreviation="NOVEL")
    suoi = list(Activity.objects.filter(teachers=nomade).order_by("pk"))
    centrale = [a for a in suoi if a.site and a.site.name == "Centrale"][0]
    succursale = [a for a in suoi if a.site and a.site.name == "Succursale"][0]
    Placement.objects.filter(schedule=s, activity=centrale).update(
        day=3, start_slot=2)
    Placement.objects.filter(schedule=s, activity=succursale).update(
        day=3, start_slot=3)
    # Un'ora che sparisce: il monte ore del piano non torna più.
    persa = Activity.objects.filter(subject__code="ITA").order_by("pk").last()
    Placement.objects.filter(schedule=s, activity=persa).delete()
    persa.delete()


def test_i_sei_rilevatori_hanno_tutti_qualcosa_da_dire():
    """§7: *«almeno un'attività per ciascuno dei sei rilevatori»*.

    🔑 **Il primo è il più interessante e non si inietta**: un orario appena
    calcolato è *sempre* «con problemi di aule», perché le aule le assegna la
    seconda fase. Non è un guasto — è la forma a due fasi del prodotto, che il
    rilevatore vede correttamente."""
    env = _orario_pieno()
    prima = ex.rileva(env["schedule"], "problemi_di_aule")
    assert len(prima.activity_ids) == 73

    _guasta(env)
    findings = check_schedule(env["schedule"])
    trovate = {nome: ex.rileva(env["schedule"], nome, findings)
               for nome in ex.RILEVATORI}
    assert set(trovate) == set(ex.RILEVATORI) and len(trovate) == 6
    for nome, r in trovate.items():
        assert r.activity_ids, nome
        assert not r.muto, nome


def test_il_comando_extract_salva_l_estrazione_dei_guasti():
    """`Estrai` è un'**operazione**, non un filtro di vista: il comando scrive
    una `Extraction` che gli altri comandi poi onorano."""
    env = _orario_pieno()
    _guasta(env)
    out = StringIO()
    call_command("extract", "--schedule", str(env["schedule"].pk),
                 "--rileva", "fuori_griglia", "a_cavallo_dell_intervallo",
                 "problemi_di_sede", "--salva", "guasti", stdout=out)
    testo = out.getvalue()
    assert "guasti" in testo
    assert Extraction.objects.get(name="guasti").activities.count() >= 3


# --------------------------------------------------------------------------
# 4. `place_and_fix` — un'imposizione che costa **più di una**
# --------------------------------------------------------------------------

def _testimone_a_due_sfratti(schedule):
    """Una cella dove due attività **diverse** confliggono con la stessa terza:
    una per la classe, una per il docente.

    🔑 **È un argomento, non una misura fortunata.** Imporre A lì obbliga
    *entrambe* a lasciare la cella — nessun'altra collocazione le salva —
    quindi `len(moved) >= 2` è vero per costruzione e non dipende da quale
    ottimo la ricerca abbia trovato. È la stessa cura dell'ondata 3, dove il
    verdetto misurabile è quello che il modello dimostra."""
    per_cella = {}
    for p in schedule.placements.all():
        per_cella.setdefault((p.day, p.start_slot), []).append(p.activity_id)
    tutte = {a.pk: a for a in Activity.objects.prefetch_related(
        "classes", "teachers", "parts")}

    def classi(a):
        return ({c.pk for c in a.classes.all()}
                | {p.partition.school_class_id for p in a.parts.all()})

    for a in Activity.objects.filter(duration_slots=1).order_by("pk"):
        sue_classi = classi(a)
        suoi_docenti = {t.pk for t in a.teachers.all()}
        for cella, presenti in sorted(per_cella.items()):
            if a.pk in presenti:
                continue
            per_classe = [i for i in presenti if classi(tutte[i]) & sue_classi]
            per_docente = [
                i for i in presenti
                if {t.pk for t in tutte[i].teachers.all()} & suoi_docenti
                and i not in per_classe]
            if per_classe and per_docente:
                return a, cella, per_classe[0], per_docente[0]
    raise AssertionError("il banco non offre una cella a due sfratti")


def test_un_imposizione_che_costa_piu_di_una_attivita():
    """§7: *«un'imposizione che costa più di una attività spostata: sul Fermi
    ne costa una, che non mette alla prova niente»*.

    Il minimo di `moved` è lessicografico **dopo** lo scarto: il modello
    preferisce spostare che buttare fuori, e infatti `dropped` resta vuoto."""
    env = _orario_pieno()
    attivita, cella, per_classe, per_docente = _testimone_a_due_sfratti(
        env["schedule"])
    esito = place_and_fix(env["schedule"], attivita.pk, cella[0], cella[1],
                          workers=8, time_limit=120)
    assert esito.ok, esito.obstruction
    assert esito.dropped == ()
    assert len(esito.moved) >= 2, esito.moved
    # I due sfrattati sono proprio quelli: è l'argomento, non la statistica.
    assert per_classe in esito.moved and per_docente in esito.moved


def test_il_comando_place_and_fix_nomina_i_ricollocati():
    env = _orario_pieno()
    attivita, cella, _classe, _docente = _testimone_a_due_sfratti(
        env["schedule"])
    out = StringIO()
    call_command("place_and_fix", "--schedule", str(env["schedule"].pk),
                 "--attivita", str(attivita.pk), "--giorno", str(cella[0]),
                 "--fascia", str(cella[1]), "--lavoratori", "8",
                 "--limite", "120", stdout=out)
    testo = out.getvalue()
    assert "Attività ricollocate (" in testo
    assert "Attività ricollocate (1)" not in testo   # più di una: è il punto
    assert "Niente è stato scritto" in testo


# --------------------------------------------------------------------------
# 5. `solve --popolazione` — il tetto che **morde**
# --------------------------------------------------------------------------

def test_il_tetto_di_non_regressione_e_una_questione_di_taglia():
    """§7: *«un arbitrato in cui il tetto di non-regressione morde davvero,
    cioè in cui alzare la tolleranza cambia il risultato»*.

    ⚠ **Sul dataset a riposo non morde, ed è la seconda attesa smentita di
    quest'ondata.** Misurato su sei configurazioni: qualunque sia la
    popolazione sacrificata e qualunque la tolleranza, i buchi della
    popolazione ottimizzata scendono a **zero** e lo dimostrano. Il banco ha
    quaranta fasce per ventinove ore di lezione: le due popolazioni non
    competono. La smentita è del **dataset**, non del meccanismo — e la
    risposta è quella dell'ondata 6: si mette il dataset in **tensione**.

    La tensione ha tre pezzi, e ognuno serve:

    1. si porta la base a **zero** — un arbitrato che ottimizza le classi,
       cioè il primo dei due comandi di EDT. Senza, la base è il valore di un
       orario mai ottimizzato (misurato: 7500 minuti) e un tetto lassù non
       vincola niente;
    2. si rende la classe 1A **indisponibile** alla seconda fascia del lunedì,
       *prima* di quel calcolo — così l'orario di partenza è legale e la base
       resta calcolabile. ⚠ Invertire i due passi dà `base: None`, che è il
       modo corretto in cui `_valori_di_base` dice «l'orario di partenza non
       è rappresentabile in questo modello»;
    3. si **puntano** due ore di italiano della 1A ai due lati del buco. Il
       pin è dell'ondata 4, e qui fa lo stesso mestiere: impone la
       configurazione e chiede al modello un verdetto.

    🔑 **E i tre verdetti sono i tre dell'ondata 6.** Il buco vale 60 minuti
    per **tre** chiavi — la classe e le sue due parti, IRC e alternativa —
    quindi 180. Con tolleranza 0 il tetto è impossibile; con 60 **anche**, ed
    è la riga che porta l'informazione; con 180 ci sta. Una tolleranza
    dichiarata «più di zero» non basta: deve essere quella giusta."""
    env = _orario_pieno()
    ResourceUnavailability.objects.create(
        resource=SchoolClass.objects.get(name="1A"), day=0, slot=1,
        level=ResourceUnavailability.Level.HARD)

    QualityCriterion.objects.create(kind=K.GAPS, population=P.CLASSES, rank=1)
    primo = solve(env["schedule"], workers=8,
                  arbitrato=Arbitrato(popolazione="classes", tolleranza=0))
    livelli = {l["nome"]: l for l in primo.stats["livelli"]}
    assert livelli["gaps_classes"]["valore"] == 0
    assert livelli["gaps_classes"]["ottimo"]
    apply(primo, env["schedule"])

    due_ore = list(Activity.objects
                   .filter(classes__name="1A", subject__code="ITA",
                           duration_slots=1).order_by("pk"))[:2]
    pin = {due_ore[0].pk: (0, 0), due_ore[1].pk: (0, 2)}
    QualityCriterion.objects.create(kind=K.GAPS, population=P.TEACHERS, rank=2)
    QualityCriterion.objects.filter(population=P.CLASSES).update(rank=3)

    esiti = {}
    for tolleranza in (0, 60, 180):
        soluzione = solve(env["schedule"], workers=8, pinned=pin,
                          arbitrato=Arbitrato(popolazione="teachers",
                                                tolleranza=tolleranza))
        tetti = {a["nome"]: a for a in soluzione.stats["arbitraggi"]}
        assert tetti["gaps_classes"]["base"] == 0
        assert tetti["gaps_classes"]["tetto"] == tolleranza
        esiti[tolleranza] = soluzione.status

    assert esiti == {0: "INFEASIBLE", 60: "INFEASIBLE", 180: "FEASIBLE"}


def test_il_comando_solve_dichiara_base_e_tetto():
    """Il rendiconto dell'arbitrato, dal comando: chi è stato sacrificato, da
    quale base e fino a quale tetto."""
    env = _orario_pieno()
    QualityCriterion.objects.create(kind=K.GAPS, population=P.TEACHERS, rank=1)
    QualityCriterion.objects.create(kind=K.GAPS, population=P.CLASSES, rank=2)
    out = StringIO()
    call_command("solve", "--schedule", str(env["schedule"].pk),
                 "--popolazione", "teachers", "--tolleranza", "60",
                 "--lavoratori", "8", stdout=out)
    testo = out.getvalue()
    assert "gaps_classes" in testo
    assert "gaps_teachers" in testo


# --------------------------------------------------------------------------
# 6-7. `assign_rooms` — la contesa, e la rinuncia
# --------------------------------------------------------------------------

def _tre_fisiche_indipendenti():
    """Tre ore di fisica della centrale su classi e docenti tutti diversi.

    Le loro candidate sono **le stesse due aule** (`LAB-FIS`, `LAB-INF`):
    l'unione è un gruppo da due posti, e tre attività non ci stanno. Classi e
    docenti diversi perché il divieto che si vuole misurare sia quello del
    gruppo di aule e non l'occupazione."""
    scelte, classi, docenti = [], set(), set()
    for a in Activity.objects.filter(subject__code="FIS", duration_slots=1,
                                     site__name="Centrale").order_by("pk"):
        sue = {c.pk for c in a.classes.all()}
        suoi = {t.pk for t in a.teachers.all()}
        if sue & classi or suoi & docenti:
            continue
        scelte.append(a)
        classi |= sue
        docenti |= suoi
        if len(scelte) == 3:
            return scelte
    raise AssertionError("servono tre ore di fisica indipendenti")


def test_la_contesa_che_il_gruppo_di_aule_risolve():
    """§7: *«una contesa che il gruppo di aule di ADR-021 risolve»*.

    🔑 **La prova è il testimone puntato dell'ondata 4, applicato a una
    risorsa che la fase 1 non assegna.** Si impone la configurazione che il
    principio dei cassetti vieta — tre attività, due aule — e si chiedono due
    verdetti: `INFEASIBLE` col builder, `OPTIMAL` senza. Il secondo ramo non è
    decorativo: senza, un `INFEASIBLE` dovuto a qualunque altra ragione
    sembrerebbe una prova.

    ⚠ E il ramo «senza» dice anche **cosa costa non contarle**: la fase 1
    accetta l'orario, la fase 2 lo eredita, e l'unica risposta che le resta è
    la rinuncia — la stessa misura del Fermi (8 rinunce su 92) alla scala di
    questo banco. ⚠ **Quante** non si asserisce: senza il tetto la fase 1 è
    libera di portare altre attività su quella cella, e il numero è una
    proprietà dell'ottimo che la ricerca ha scelto (misurato: 1 e 2 in due
    esecuzioni). Che ce ne sia almeno una, e che sia una delle puntate, è
    invece una proprietà del modello."""
    env = alighieri.build()
    pin = {a.pk: (1, 3) for a in _tre_fisiche_indipendenti()}

    con = solve(env["schedule"], workers=8, pinned=pin, time_limit=120)
    assert con.status == "INFEASIBLE", con.stats

    senza = _senza_pool(lambda: solve(env["schedule"], workers=8, pinned=pin,
                                      time_limit=120))
    assert senza.status == "OPTIMAL", senza.stats
    assert senza.stats["scartate"] == 0
    apply(senza, env["schedule"])
    aule = solve_rooms(env["schedule"], workers=8)
    assert aule.status == "OPTIMAL"
    assert aule.unassigned, "senza il gruppo di aule la contesa deve costare"
    assert set(aule.unassigned) & set(pin), aule.unassigned


def test_la_rinuncia_inevitabile_e_la_fase_1_che_tace():
    """§7: *«una rinuncia inevitabile quando la si stringe»*.

    Un'attività **immobile** in una cella dove entrambe le sue candidate sono
    rosse: nessuna assegnazione esiste, e la seconda fase rinuncia invece di
    dichiararsi infattibile — che è lo stato ammesso di cui `rooms.py` dice
    *«la rinuncia è la risposta, non l'infattibilità»*.

    🔑 **La seconda metà è il contenuto vero**: la fase 1 fa esattamente le due
    cose giuste, e sono opposte. Sulle attività **libere** il gruppo di aule
    conta zero posti in quella cella e le manda altrove — senza il ricalcolo
    le rinunce sono **due** (misurato), perché un'altra ora di laboratorio
    stava lì. Sull'**immobile** tace: `RoomPoolBuilder` esce quando nessuna
    delle attività in causa è libera — *«un fatto, non una decisione»* — e la
    configurazione resta illegale perché nessun piazzamento la può
    riparare."""
    env = _orario_pieno()
    attivita = (Activity.objects
                .filter(subject__code="FIS", duration_slots=1,
                        site__name="Centrale").order_by("pk").first())
    dove = Placement.objects.get(schedule=env["schedule"], activity=attivita)
    attivita.immobility = Activity.Immobility.FIXED
    attivita.save()
    for nome in ("LAB-FIS", "LAB-INF"):
        ResourceUnavailability.objects.create(
            resource=Room.objects.get(name=nome), day=dove.day,
            slot=dove.start_slot, level=ResourceUnavailability.Level.HARD)

    di_nuovo = solve(env["schedule"], workers=8)
    assert di_nuovo.status == "OPTIMAL", di_nuovo.stats
    assert di_nuovo.stats["scartate"] == 0
    apply(di_nuovo, env["schedule"])

    out = StringIO()
    atteso = "1 richieste d'aula senza risposta"
    with pytest.raises(CommandError, match=atteso):
        call_command("assign_rooms", "--schedule", str(env["schedule"].pk),
                     "--lavoratori", "8", stdout=out)
    testo = out.getvalue()
    assert "== Richieste senza aula (1, 1h00) ==" in testo
    assert "chiedeva: LAB-FIS, LAB-INF" in testo

    aule = solve_rooms(env["schedule"], workers=8)
    assert aule.unassigned == (attivita.pk,)
    assert aule.stats["assegnate"] == 72


# --------------------------------------------------------------------------
# 8. Il criterio di §4: «stretto ma risolvibile», sul dataset intero
# --------------------------------------------------------------------------

def _spegni(risorsa):
    """Toglie una risorsa senza cancellarla: rossa su tutta la griglia.

    ⚠ Cancellarla non si può — un'attività senza docente o senza aula
    candidata non è la stessa scuola con una risorsa in meno, è una scuola
    diversa. Il rosso su tutte le quaranta celle è la traduzione fedele di
    *«togliendo un solo docente»*."""
    for day in range(5):
        for slot in range(8):
            ResourceUnavailability.objects.create(
                resource=risorsa, day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)


def test_stretto_ma_risolvibile_e_verificato_sul_dataset_intero():
    """Il criterio di §4 della spec, l'ultimo rimasto: *«la fase 1 chiude
    `OPTIMAL` con zero scarti, ma togliendo una sola aula o un solo docente
    comincia a scartare»*. Le ondate 3-6 lo verificavano **famiglia per
    famiglia**; qui si verifica sul dataset intero, che è ciò che tre file del
    banco rimandavano a quest'ondata.

    ⚠ **«Una» aula, non «qualunque»**: togliere l'aula magna, che nessuno usa,
    non scarta niente e non deve. Il criterio dice che il banco ha un punto in
    cui è teso, e i punti si misurano: `LAB-SUCC` (il laboratorio unico della
    succursale) costa **11** scarti, cioè esattamente le attività che lo
    chiedono; i docenti campionati ne costano 3, 12 e 20 — le loro ore.

    🔑 **E il criterio è soddisfatto senza portare al bordo il D.T.B.**, che è
    la cosa da capire: sono **due nozioni diverse di «stretto»**. Questa è
    stretta rispetto alle **risorse** — togline una e qualcosa cade. La
    contiguità che il D.T.B. chiede è stretta rispetto alla **densità della
    griglia**: 40 fasce contro cattedre da 10–21 ore la rendono gratis, e per
    negarla servirebbe una griglia più corta, cioè un altro banco. I due test
    che asseriscono l'`OPTIMAL` — il D.T.B. dell'ondata 3 e la tacca dei
    divieti dell'ondata 4 — restano quindi verdi, e la frase «diventerà rosso
    all'ondata 7» che li accompagnava era sbagliata: l'ondata 7 stringe le
    risorse, non la griglia."""
    env = alighieri.build()
    intatto = solve(env["schedule"], workers=8)
    assert intatto.status == "OPTIMAL"
    assert intatto.stats["scartate"] == 0

    lab = Room.objects.get(name="LAB-SUCC")
    quante = Activity.objects.filter(rooms=lab).count()
    _spegni(lab)
    senza_lab = solve(env["schedule"], workers=8, time_limit=90)
    assert senza_lab.status == "OPTIMAL", senza_lab.stats
    assert senza_lab.stats["scartate"] == quante == 11


def test_e_lo_stesso_per_un_docente():
    env = alighieri.build()
    ricci = Teacher.objects.get(abbreviation="RICCI")
    sue = Activity.objects.filter(teachers=ricci).count()
    _spegni(ricci)
    soluzione = solve(env["schedule"], workers=8, time_limit=90)
    assert soluzione.status == "OPTIMAL", soluzione.stats
    assert soluzione.stats["scartate"] == sue == 3


def test_l8_lo_scarto_non_e_una_via_d_uscita_universale():
    """🔑 **Il difetto che l'ondata 7 ha trovato, misurando il bordo.**

    Spegnendo la **palestra** il modello non scarta: risponde `INFEASIBLE`,
    che è ciò che `allow_unplaced=True` dovrebbe rendere impossibile — lo
    scarto esiste proprio perché un'attività che non ci sta non blocchi il
    calcolo.

    La causa è **una sola riga**, isolata togliendone dieci una per volta:
    `free_guaranteed` su P01 Zanetti, il docente di scienze motorie. Con la
    palestra spenta gli restano le sole ore della succursale, e il solver ne
    piazza **una**, su **un** giorno. La riga chiede due giornate libere — che
    ci sono — e **due mezze giornate libere**, che non ci sono: una mezza
    giornata libera conta solo su un giorno **lavorato**
    (`libera = attivo AND NOT meta`), perché è così che la conta
    `FreeGuaranteedChecker`, e un giorno interamente vuoto contribuisce zero.
    Con un giorno lavorato il massimo è **uno**.

    🔑 **È l'immagine speculare della trappola che il builder documenta**, e
    non è un errore del builder: contare le mezze libere su tutti i giorni
    accetterebbe orari che il checker boccia — la direzione sbagliata. Il
    fatto nuovo è la **conseguenza**: una famiglia che conta una quantità *sui
    giorni in cui si lavora* può diventare insoddisfacibile **perché si lavora
    meno**, e lì lo scarto non è una via d'uscita. Un prodotto che risponde
    `INFEASIBLE` invece di «queste dieci attività non si piazzano» dà
    all'utente la diagnosi peggiore delle due.

    Non riparato (spec §8), fissato qui col suo **ramo di controllo**: tolta
    quella riga, lo stesso dataset scarta e chiude `OPTIMAL`."""
    env = alighieri.build()
    _spegni(Room.objects.get(name="PALESTRA"))
    soluzione = solve(env["schedule"], workers=8, time_limit=90)
    assert soluzione.status == "INFEASIBLE", soluzione.stats

    ResourceTimeConstraint.objects.filter(
        type=ResourceTimeConstraint.Type.FREE_GUARANTEED).delete()
    controllo = solve(env["schedule"], workers=8, time_limit=90)
    assert controllo.status == "OPTIMAL", controllo.stats
    assert controllo.stats["scartate"] > 0
