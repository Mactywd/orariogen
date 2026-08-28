"""Le famiglie **non monotone**, una per una: il falso positivo che ciascuna
produceva prima del rilassamento, e la prova che il rilassamento non ha spento
la fase 5.

Il criterio della fase 5 e' che un verdetto negativo sia una **dimostrazione**:
ogni approssimazione deve *sovrastimare* la capienza, perche' una che la
sottostima manda l'utente a smontare vincoli sani. `admissible_starts` scarta
una cella quando il piazzamento di prova introduce una `Finding.key` **nuova**
rispetto alla baseline — e per i checker non monotoni quella condizione e'
falsa: la loro violazione si **ripara** piazzando, oppure la loro chiave si
sposta senza che niente peggiori. Ogni cella diventa allora "nuova", il dominio
si svuota, e la fase 5 inventa la deficienza.

⚠ Due forme di dimostrazione, e la differenza non e' cosmetica:

- dove il rilassamento riguarda una violazione **riparabile**, l'orario di
  partenza e' **valido** (`check_schedule` senza HARD) e il solver risponde
  OPTIMAL: il falso positivo e' fuori discussione;
- dove riguarda una violazione **gia' presente e non riparabile** (le
  congelate), l'orario resta invalido per definizione — e la prova e' che il
  **solver** una collocazione la trova lo stesso (ADR-018: vietare un
  peggioramento si', pretendere una riparazione no), mentre la fase 5 dichiara
  che collocazioni non ce ne sono."""
import pytest

from domain.analysis.conformity import check_schedule
from domain.analysis.findings import Severity
from domain.analysis.hall import analyze_hall
from domain.models import (
    Activity, ClassPart, ClassPartition, InstituteSettings,
    ResourceTimeConstraint, ResourceUnavailability, Room, Subject,
    SubjectConstraint,
)
from domain.solver.model import solve
from tests.analysis_helpers import make_activity, mini_school, place

pytestmark = pytest.mark.django_db

RT = ResourceTimeConstraint.Type
ST = SubjectConstraint.Type


def _hard(schedule):
    return [f for f in check_schedule(schedule) if f.severity == Severity.HARD]


def _violazioni(schedule):
    """I finding HARD **meno** l'incompletezza. `structural:placement` (pezzo 3)
    nomina ogni attivita' non piazzata, e in questi test l'attivita' libera e'
    deliberatamente non piazzata: e' la **premessa**, non un esito. Il checker
    lo dichiara di suo — «descrive un orario incompleto, non illegale» — e cio'
    che qui si asserisce e' *quale violazione di vincolo* preesiste."""
    return [f for f in _hard(schedule) if f.code != "activity_unplaced"]


def _blocca(resource, giorni=(), celle=()):
    for day in giorni:
        for slot in range(6):
            ResourceUnavailability.objects.create(
                resource=resource, day=day, slot=slot, level="hard")
    for day, slot in celle:
        ResourceUnavailability.objects.create(
            resource=resource, day=day, slot=slot, level="hard")


def _orario_valido_e_muto(env):
    """La forma della riproduzione: orario valido, solver OPTIMAL, fase 5 zitta."""
    assert _hard(env["schedule"]) == [], "l'orario di partenza dev'essere valido"
    assert solve(env["schedule"], time_limit=30).status in ("OPTIMAL", "FEASIBLE")
    assert analyze_hall(env["schedule"]) == []


def test_min_distribution_non_inventa_una_deficienza():
    # La riproduzione del Critical 1. A stato vuoto `days=0 < min_days=3`: la
    # violazione c'e' gia' nella baseline, e ogni piazzamento la **migliora**
    # cambiandone la chiave. Prima del rilassamento: tre finding
    # «L'attivita' non ha nessuna collocazione ammissibile».
    env = mini_school()
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=RT.MIN_DISTRIBUTION,
        params={"min_days": 3, "min_minutes_per_day": 60})
    for day in range(3):
        a = make_activity(env["subject"], teachers=[env["teacher"]], slots=1)
        place(env["schedule"], a, day=day, slot=0)

    _orario_valido_e_muto(env)


def test_free_guaranteed_non_inventa_una_deficienza():
    # `free_half_days` si conta solo sui giorni **con** attivita': a stato
    # vuoto vale 0, quindi la soglia e' violata al massimo e ogni piazzamento
    # la migliora. Chiave nuova a ogni cella, dominio vuoto.
    env = mini_school()
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=RT.FREE_GUARANTEED,
        params={"free_days": 2, "free_half_days": 3})
    for day in range(3):
        a = make_activity(env["subject"], teachers=[env["teacher"]], slots=1)
        place(env["schedule"], a, day=day, slot=0)

    _orario_valido_e_muto(env)


def test_imposed_succession_non_inventa_una_deficienza():
    # Ramo A != B, quello senza guardia di vacuita': con B assente **ogni**
    # occorrenza di A e' in violazione. Nel loop di prova le sorelle sono tutte
    # spiazzate, quindi piazzare una A da sola produce sempre il finding — e
    # nessuna cella sopravvive.
    env = mini_school()
    altra = Subject.objects.create(code="MAT", name="Matematica",
                                   discipline=env["discipline"])
    SubjectConstraint.objects.create(
        school_class=env["klass"], type=ST.IMPOSED_SUCCESSION,
        subject_a=env["subject"], subject_b=altra, param=1)
    a = make_activity(env["subject"], teachers=[env["teacher"]],
                      classes=[env["klass"]], slots=1)
    b = make_activity(altra, classes=[env["klass"]], slots=1)
    place(env["schedule"], a, day=0, slot=0)     # mezza giornata 0
    place(env["schedule"], b, day=0, slot=4)     # mezza giornata 1: scarto 1

    _orario_valido_e_muto(env)


def test_max_gap_non_inventa_una_deficienza():
    """⚠ Famiglia **non** nell'elenco della review, trovata leggendo il
    checker. Il buco e' `ultima − prima + 1 − conteggio`: piazzare *dentro* un
    buco esistente alza il conteggio senza toccare gli estremi, e il totale
    **cala**. Una riparazione parziale lascia la violazione e ne cambia la
    chiave — cella scartata a torto.

    Serve una **congelata** per vederla, ed e' per questo che il banco a
    testimone non poteva trovarla: li' non si congela niente, e con la sola
    attivita' di prova nessuna mezza giornata arriva a due fasce."""
    env = mini_school()
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=RT.MAX_GAP_HOURS,
        params={"max_gap_minutes": 0})
    _blocca(env["teacher"], giorni=(1, 2, 3, 4), celle=[(0, 4), (0, 5)])
    for slot in (0, 3):
        congelata = make_activity(
            env["subject"], teachers=[env["teacher"]], slots=1,
            immobility=Activity.Immobility.LOCKED_IN_PLACE)
        place(env["schedule"], congelata, day=0, slot=slot)
    make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    # L'orario NON e' valido — le due congelate lasciano un buco di 2h con
    # tetto 0 — e nessuna mossa sulle libere lo ripara. Ma il solver una
    # collocazione la trova (ADR-018), quindi «nessuna collocazione
    # ammissibile» e' un falso positivo dimostrato.
    assert [f.code for f in _violazioni(env["schedule"])] == ["max_gap"]
    assert solve(env["schedule"], time_limit=30).status in ("OPTIMAL", "FEASIBLE")
    assert analyze_hall(env["schedule"]) == []


def test_peso_didattico_non_inventa_una_deficienza():
    """⚠ Famiglia **non** nell'elenco della review. `acts[key]` raccoglie tutte
    le attivita' piazzate dell'unita'-studente, e finisce in `activities` di
    *ogni* finding di peso: un piazzamento di lunedi' cambia la chiave della
    violazione settimanale senza aggiungerle un punto di quanto non pesi
    davvero. Con la baseline gia' oltre il tetto per colpa delle congelate,
    ogni cella risulta nuova."""
    settings = InstituteSettings.load()
    settings.max_weight_week = 2
    settings.save()
    env = mini_school()
    env["subject"].didactic_weight = 3
    env["subject"].save()
    congelata = make_activity(
        env["subject"], classes=[env["klass"]], slots=1,
        immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], congelata, day=0, slot=0)
    make_activity(env["subject"], classes=[env["klass"]], slots=1)

    assert [f.code for f in _violazioni(env["schedule"])] == ["weight_week"]
    assert solve(env["schedule"], time_limit=30).status in ("OPTIMAL", "FEASIBLE")
    assert analyze_hall(env["schedule"]) == []


def test_weekly_order_non_inventa_una_deficienza():
    """⚠ Famiglia **non** nell'elenco della review: **deriva d'identita'**. Il
    finding nomina le due occorrenze *argmin*. Piazzare una A dopo la B ma
    prima della A congelata non ripara niente e non peggiora niente — cambia
    solo *quale* attivita' e' l'argmin, e quindi la chiave."""
    env = mini_school()
    altra = Subject.objects.create(code="MAT", name="Matematica",
                                   discipline=env["discipline"])
    SubjectConstraint.objects.create(
        school_class=env["klass"], type=ST.WEEKLY_ORDER,
        subject_a=env["subject"], subject_b=altra)
    # ⚠ La libera dev'essere costretta **fra** le due congelate: dopo la A
    # congelata l'argmin non si sposta, la chiave non cambia e la cella
    # sopravvive — la prima stesura di questo test aveva la libera libera di
    # andare dopo, e restava verde anche senza il rilassamento (misurato per
    # mutazione).
    _blocca(env["klass"], giorni=(1, 2, 3, 4))
    b = make_activity(altra, classes=[env["klass"]], slots=1,
                      immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], b, day=0, slot=0)
    a_cong = make_activity(env["subject"], classes=[env["klass"]], slots=1,
                           immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], a_cong, day=0, slot=5)
    libera = make_activity(env["subject"], classes=[env["klass"]], slots=1)

    prima = {(f.code, f.resources) for f in _violazioni(env["schedule"])}
    assert prima == {("subject_weekly_order", (env["klass"].pk,))}

    assert analyze_hall(env["schedule"]) == []

    # La collocazione esiste: la libera in fascia 1 e' pur sempre dopo la B, e
    # la violazione resta quella di prima — cambia solo *chi* e' nominato.
    place(env["schedule"], libera, day=0, slot=1)
    assert {(f.code, f.resources) for f in _violazioni(env["schedule"])} == prima


def test_parts_order_non_inventa_una_deficienza():
    """⚠ Famiglia **non** nell'elenco della review (e sono quattro tipi, una
    sola classe base). Il finding nomina `entries`, cioe' *tutte* le attivita'
    del secchio e non quelle che realizzano il disordine: aggiungerne una gia'
    ben ordinata cambia la chiave senza peggiorare niente.

    ⚠ **Qui il solver non e' il metro, ed e' l'unica delle sei dove non lo
    e'.** `_PartsOrderBuilder` tratta ADR-018 azzerando *tutti* i letterali
    liberi di un secchio gia' violato dalle sole congelate — un **divieto**,
    dichiarato nel suo docstring e concesso da ADR-018 anche quando rende il
    modello INFEASIBLE. Misurato: confinando la libera al solo giorno 0,
    `solve` risponde INFEASIBLE. Il metro e' allora il **checker**: esiste un
    piazzamento che non aggiunge nessuna coppia (causale, risorsa) nuova,
    quindi «nessuna collocazione ammissibile» resta una frase falsa.

    Rilassare qui costa **richiamo** e non compra precisione *finche'* il
    builder resta cosi'. Si rilassa lo stesso perche' `PLACEMENT_MONOTONE` e'
    una proprieta' del **checker**: legarla alla scelta ADR-018 di un builder
    metterebbe in `domain/analysis` una dipendenza dal solver — quella che
    tutto il package esiste per non avere — e marcirebbe in silenzio il giorno
    che il builder cambia idea."""
    env = mini_school()
    partizione = ClassPartition.objects.create(
        school_class=env["klass"], name="Lingue")
    parte = ClassPart.objects.create(partition=partizione, name="L1")
    SubjectConstraint.objects.create(
        school_class=env["klass"], type=ST.PARTS_BEFORE_CLASS,
        subject_a=env["subject"], subject_b=env["subject"])
    _blocca(env["klass"], giorni=(1, 2, 3, 4))
    _blocca(parte, giorni=(1, 2, 3, 4))

    di_classe = make_activity(env["subject"], classes=[env["klass"]], slots=1,
                              immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], di_classe, day=0, slot=1)
    di_parte = make_activity(env["subject"], parts=[parte], slots=1,
                             immobility=Activity.Immobility.LOCKED_IN_PLACE)
    place(env["schedule"], di_parte, day=0, slot=3)   # dopo: gia' in violazione
    libera = make_activity(env["subject"], parts=[parte], slots=1)

    prima = {(f.code, f.resources) for f in _violazioni(env["schedule"])}
    assert prima == {("subject_parts_order", (env["klass"].pk,))}

    assert analyze_hall(env["schedule"]) == []

    # E la collocazione esiste davvero: la libera in fascia 0 e' **prima**
    # della classe, cioe' proprio l'ordine che la riga chiede, e non aggiunge
    # nessuna coppia (causale, risorsa) che non ci fosse gia'.
    place(env["schedule"], libera, day=0, slot=0)
    assert {(f.code, f.resources) for f in _violazioni(env["schedule"])} == prima


def test_room_assignment_non_inventa_una_deficienza():
    """La **terza** forma, e va per il verso opposto a tutte le altre: qui
    piazzare non ripara la violazione, la **crea**.

    `structural:room_assignment` nomina le attivita' **piazzate** che chiedono
    un'aula e non ne hanno ancora una. A stato vuoto l'attivita' e' sospesa,
    quindi il finding non c'e'; ogni cella di prova la piazza, e in ogni cella
    il finding compare. Chiave nuova ovunque, dominio vuoto, e la fase 5
    dichiara impiazzabile un'attivita' che il solver colloca senza fatica.

    ⚠ L'orario di partenza non e' **muto** come nelle altre riproduzioni, ed e'
    corretto che non lo sia: `room_unassigned` e' li' per definizione finche' la
    seconda fase non ha girato. Cio' che si asserisce e' che non ci sia nessuna
    violazione di **vincolo**, e che la fase 5 taccia lo stesso."""
    env = mini_school()
    lab = Room.objects.create(name="LAB", simultaneous_capacity=1)
    for day in range(3):
        a = make_activity(env["subject"], teachers=[env["teacher"]],
                          rooms=[lab], slots=1)
        place(env["schedule"], a, day=day, slot=0)

    codici = {f.code for f in _hard(env["schedule"])}
    assert codici == {"room_unassigned"}, codici
    assert solve(env["schedule"], time_limit=30).status in ("OPTIMAL", "FEASIBLE")
    assert analyze_hall(env["schedule"]) == []


def test_il_rilassamento_non_ha_spento_la_fase_5():
    """⚠ La meta' che conta quanto l'altra. Il rilassamento **allarga** i
    domini, e allargarli abbastanza spegnerebbe la fase 5 in silenzio: una
    fase 5 che tace sempre passa quasi tutti i test negativi.

    Qui la deficienza e' vera — sette lezioni da un'ora per un docente libero
    un solo giorno da sei fasce — e c'e' anche una riga **non monotona** sulla
    stessa risorsa. Deve uscire lo stesso."""
    env = mini_school()
    ResourceTimeConstraint.objects.create(
        resource=env["teacher"], type=RT.MIN_DISTRIBUTION,
        params={"min_days": 3, "min_minutes_per_day": 60})
    _blocca(env["teacher"], giorni=(1, 2, 3, 4))
    for _ in range(7):
        make_activity(env["subject"], teachers=[env["teacher"]], slots=1)

    findings = analyze_hall(env["schedule"])

    assert len(findings) == 1
    assert findings[0].n_activities == 7
    assert findings[0].required_minutes == 7 * 60
    assert findings[0].placeable_minutes == 6 * 60
    # ⚠ `allow_unplaced=False` dal pezzo 3: col modello vero un insieme
    # deficiente non e' INFEASIBLE, **rinuncia**. E qui la rinuncia non si puo'
    # misurare, perche' la riga MIN_DISTRIBUTION (min_days 3, docente libero un
    # giorno solo) e' una causa **indipendente e sufficiente** di
    # infattibilita': misurato, il modello con lo scarto risponde INFEASIBLE
    # con zero minuti scartati. Questa meta' quindi **corrobora e non isola** —
    # l'isolamento e' in `test_hall_oracle.py`, dove la sola deficienza di
    # capienza produce esattamente i 60 minuti dichiarati.
    assert solve(env["schedule"], time_limit=30,
                 allow_unplaced=False).status == "INFEASIBLE"
