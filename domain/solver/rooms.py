"""L'assegnazione delle aule: la **seconda fase**, un modello a se'.

In EDT non fa parte del piazzamento — ha criteri propri (`TypeChoixOptimSalle`),
un ottimizzatore dedicato (`FicheEdt_OptimiseurSalles`) e una `ripartizione
delle aule` distinta dal calcolo. Assegnare le aule *dopo* aver piazzato e'
quindi una semplificazione validata da un prodotto maturo, non una scorciatoia
(`docs/edt/motore-risoluzione.md`).

I vincoli veri sono tre, piu' la capienza: la finestra `Aule disponibili`
dichiara `Sedi distaccate`, `Indisponibilita' opzionali`, `Indisponibilita'` e
nient'altro. **Capienza in alunni, categoria e tipologie non vincolano.**"""

from collections import defaultdict
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from domain.analysis.conformity import week_signatures
from domain.analysis.state import ScheduleState
from domain.models import Activity, Resource, Room

_IMMOBILE = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


@dataclass
class RoomContext:
    schedule: object
    signatures: list          # [(settimana rappresentante, tutte le settimane)]
    states: dict              # rappresentante → ScheduleState
    requests: dict            # id → Activity: le decisioni della fase
    candidates: dict          # id → set(room_id) sopravvissute ai pre-filtri
    previous: dict            # id → room_id assegnata prima del calcolo
    held: dict                # id → room_id delle **non** decisioni
    ignora_opzionali: frozenset = frozenset()
    y: dict = field(default_factory=dict)         # (id, room_id) → BoolVar
    assigned: dict = field(default_factory=dict)  # id → BoolVar «assegnata»

    @classmethod
    def build(cls, schedule, ignora_opzionali=()):
        signatures = week_signatures(schedule)
        states = {rep: ScheduleState.build(schedule, week=rep)
                  for rep, _ in signatures}
        ignora = frozenset(ignora_opzionali)

        requests, dichiarate, previous, held = {}, {}, {}, {}
        for state in states.values():
            for aid, act in state.activities.items():
                if aid in requests or aid in held or aid not in state.placed:
                    continue
                aula = state.assigned_room.get(aid)
                rooms = {r.pk for r in act.rooms.all()}
                # Il blocco riguarda l'aula che ha, non quella che non ha:
                # un'immobile senza assegnazione resta una decisione.
                if rooms and not (act.immobility in _IMMOBILE and aula is not None):
                    requests[aid] = act
                    dichiarate[aid] = rooms
                    if aula is not None:
                        previous[aid] = aula
                elif aula is not None:
                    held[aid] = aula

        room_sites = dict(Room.objects.values_list("pk", "site_id"))
        candidates = {
            aid: cls._filtra(aid, act, dichiarate[aid], room_sites,
                             states, ignora)
            for aid, act in requests.items()
        }
        return cls(schedule=schedule, signatures=signatures, states=states,
                   requests=requests, candidates=candidates,
                   previous=previous, held=held, ignora_opzionali=ignora)

    @staticmethod
    def _filtra(aid, act, dichiarate, room_sites, states, ignora):
        """Sede e indisponibilita', su **tutta** la durata del piazzamento."""
        gialla_ignorata = Resource.Kind.ROOM in ignora
        ok = set()
        for room_id in dichiarate:
            if act.site_id is not None and room_sites.get(room_id) != act.site_id:
                continue
            libera = True
            for state in states.values():
                collocazione = state.placed.get(aid)
                if collocazione is None:
                    continue
                for slot in collocazione.slots:
                    livello = state.unavailability.get(
                        (room_id, collocazione.day, slot))
                    if livello == "hard" or (livello == "optional"
                                             and not gialla_ignorata):
                        libera = False
                        break
                if not libera:
                    break
            if libera:
                ok.add(room_id)
        return ok

    def frozen_load(self):
        """(rappresentante, room_id, giorno, fascia) → carico non decisionale.
        Sono le attivita' che occupano un'aula senza essere una scelta di questa
        fase: le immobili che tengono la loro, e le assegnazioni a mano su
        attivita' che non dichiarano candidate."""
        load = defaultdict(int)
        for rep, _ in self.signatures:
            state = self.states[rep]
            for aid, room_id in self.held.items():
                collocazione = state.placed.get(aid)
                if collocazione is None:
                    continue
                for slot in collocazione.slots:
                    load[(rep, room_id, collocazione.day, slot)] += 1
        return dict(load)


def build_room_model(schedule, *, allow_unassigned=True, ignora_opzionali=()):
    """`allow_unassigned=False` pretende un'aula per ogni richiesta: e' il modo
    di chiedere «questo vincolo morde?». Con la rinuncia ammessa la risposta a
    un vincolo violato non e' l'infattibilita' ma la **rinuncia**, che e'
    un'altra domanda — la stessa cucitura che `build_model(allow_unplaced=...)`
    ha per lo scarto.

    ⚠ Il modello restituito **non porta obiettivo**: e' lo stesso contratto di
    `build_model` in `domain/solver/model.py`. Chi lo risolve con un
    `CpSolver()` nudo ottiene una soluzione feasible qualunque — «rinuncia a
    tutti» compresa, perche' e' feasible quanto «assegna il possibile» e
    CP-SAT senza obiettivo non preferisce l'una all'altra. La preferenza (e la
    catena a due livelli) e' compito di chi risolve — `solve_rooms` (Task 4)
    per la fase vera, un `model.Maximize(...)` locale per chi vuole solo
    osservare il modello grezzo in un test."""
    ctx = RoomContext.build(schedule, ignora_opzionali=ignora_opzionali)
    model = cp_model.CpModel()
    for aid in sorted(ctx.requests):
        lits = []
        for room_id in sorted(ctx.candidates[aid]):
            var = model.NewBoolVar(f"y_{aid}_{room_id}")
            ctx.y[(aid, room_id)] = var
            lits.append(var)
        if not allow_unassigned:
            # ⚠ Anche con `lits` vuoto: `AddExactlyOne([])` e' gia' INFEASIBLE,
            # che e' precisamente cio' che «nessuna candidata e assegnazione
            # pretesa» deve significare.
            model.AddExactlyOne(lits)
            continue
        assegnata = model.NewBoolVar(f"assegnata_{aid}")
        ctx.assigned[aid] = assegnata
        model.Add(sum(lits) == assegnata)
    _post_capacity(ctx, model)
    return model, ctx


def _post_capacity(ctx, model):
    """La capienza simultanea, per (aula, giorno, fascia, **firma**).

    ⚠ Il tetto e' il **residuo**: `max(0, capienza - carico congelato)`. Le
    immobili che tengono la loro aula consumano senza essere decisioni, e
    pretendere che le libere riparino il loro sovraccarico e' la meta' vietata
    di ADR-018."""
    carico = ctx.frozen_load()
    posted = set()
    for rep, _ in ctx.signatures:
        state = ctx.states[rep]
        per_cella = defaultdict(list)
        for aid in ctx.requests:
            collocazione = state.placed.get(aid)
            if collocazione is None:
                continue          # non attiva in questa firma: non compete
            for room_id in ctx.candidates[aid]:
                for slot in collocazione.slots:
                    per_cella[(room_id, collocazione.day, slot)].append(
                        ctx.y[(aid, room_id)])
        for (room_id, day, slot), lits in sorted(per_cella.items()):
            residuo = max(0, state.capacity.get(room_id, 1)
                          - carico.get((rep, room_id, day, slot), 0))
            if len(lits) <= residuo:
                continue          # non e' una decisione: e' un fatto
            firma = (room_id, day, slot, residuo,
                     tuple(sorted(lit.Index() for lit in lits)))
            if firma in posted:
                continue          # due firme con lo stesso insieme: un vincolo solo
            posted.add(firma)
            model.Add(sum(lits) <= residuo)
