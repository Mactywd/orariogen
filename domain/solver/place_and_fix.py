"""`Piazza e sistema`: *«sposta l'attività in una posizione già occupata; se
ciò comporta lo spostamento di altre attività, queste verranno automaticamente
ricollocate»* — la voce che `scope-v1.md` dichiara ✅ dentro perché è «il modo
più economico di dare all'utente il potere di forzare».

🔑 **E porta con sé la condizione 1 delle tre da non perdere**: *«qual è
l'insieme minimo di attività da spostare perché A stia qui?»*. È lo stesso
motore del risolutore passo-passo escluso da v1, e averlo tiene quella porta
aperta. La risposta è `PlaceAndFix.moved`.

🔑 **Il pezzo costa poco perché la catena lessicografica lo era già.** Imporre
una cella è un vincolo hard; «disturbare il meno possibile» è **L4**, la
stabilità, che minimizza le attività che cambiano cella rispetto ai
`Placement` esistenti — scritta per ADR-010 e per il secondo quadrimestre da
non stravolgere, ed è esattamente ciò che serve qui. L'ordine della catena è
già quello giusto e non si tocca: **non scartare** viene prima di **non
spostare**, perché ricollocare un'attività è meno grave che buttarla fuori.
Il minimo di `moved` è quindi lessicografico *dopo* L1-L3, non assoluto — ed è
la nozione corretta, non un'approssimazione.

⚠ **Resta fuori, dichiarato: l'opzione «Ignora i vincoli dell'attività
selezionata».** In EDT è una casella; da noi non è separabile per attività,
perché i vincoli di A non sono *di* A — una riga di materia sulla classe lega
A alle sue sorelle, e «spegnere i vincoli di A» vorrebbe dire attraversare
ventisei builder per togliere i letterali di una sola attività. Un'attuazione
parziale — per esempio la sola riapertura dei pre-filtri — lascerebbe forzare
oltre un'indisponibilità rossa ma non oltre un'incompatibilità di materia:
un modello mentale incoerente, peggiore dell'assenza. Senza la casella, una
collocazione impossibile riceve una **diagnosi nominata**, che è comunque la
risposta che l'utente deve leggere.
"""

from dataclasses import dataclass

from domain.analysis.domain_size import trial_placements
from domain.analysis.state import ScheduleState, resource_sort_key
from domain.analysis import causali
from domain.solver.model import solve


CAUSALI_DI_PREFILTRO = frozenset({
    # ⚠ I soli due builder che implementano `restrict()` sono `GridBuilder` e
    # `UnavailabilityBuilder`: un pin fuori dominio può venire **solo** di lì.
    # Filtrare su queste causali non è prudenza, è precisione — la lettura di
    # `trial_placements` valuta tutti i checker contro lo stato corrente, e
    # includerebbe l'occupazione da parte di attività che `Piazza e sistema`
    # saprebbe spostare: incolparle sarebbe una diagnosi falsa.
    # `test_solo_due_builder_prefiltrano` tiene ferma la premessa.
    "slot_out_of_grid", "break_straddled", "holiday",
    "unavailability", "unavailability_optional",
})


@dataclass(frozen=True)
class PlaceAndFix:
    solution: object      # la Solution del solver, per `apply`
    activity_id: int
    cell: tuple
    moved: tuple          # id delle attività ricollocate, **esclusa** la forzata
    dropped: tuple        # id delle attività che erano piazzate e ora sono scartate
    obstruction: tuple    # le frasi del perché no, vuote se si è potuto

    @property
    def ok(self):
        return self.solution.status in ("OPTIMAL", "FEASIBLE")


def place_and_fix(schedule, activity_id, day, start, *, extraction=None,
                  time_limit=None, workers=None, ignora_opzionali=()):
    """Impone `activity_id` sulla cella `(day, start)` e ricolloca il resto.

    ⚠ `moved` **esclude la forzata**, che si è spostata per definizione: il
    numero che interessa all'utente è il danno collaterale, e contarci dentro
    la mossa che ha chiesto lui renderebbe «zero spostamenti» irraggiungibile
    proprio nel caso migliore.

    ⚠ E `dropped` esiste perché `moved` da solo mentirebbe: un'attività che
    era piazzata e che il modello ha dovuto **scartare** non compare fra le
    ricollocate, e «zero spostamenti» su un orario che ha perso tre ore
    sarebbe il rendiconto peggiore possibile."""
    solution = solve(schedule, extraction=extraction, time_limit=time_limit,
                     workers=workers, ignora_opzionali=ignora_opzionali,
                     pinned={activity_id: (day, start)})
    prima = {p.activity_id: (p.day, p.start_slot)
             for p in schedule.placements.all()}
    moved = dropped = obstruction = ()
    if solution.status in ("OPTIMAL", "FEASIBLE"):
        moved = tuple(sorted(
            aid for aid, cella in solution.placements.items()
            if aid != activity_id
            and aid in prima and prima[aid] != cella))
        dropped = tuple(sorted(aid for aid in solution.unplaced if aid in prima))
    else:
        obstruction = _perche_no(schedule, activity_id, day, start, solution)
    return PlaceAndFix(solution=solution, activity_id=activity_id,
                       cell=(day, start), moved=moved, dropped=dropped,
                       obstruction=obstruction)


def _perche_no(schedule, activity_id, day, start, solution):
    """La diagnosi nominata, e sono **due domande diverse**.

    Se il pin è finito fuori dominio (`pin_fuori_dominio`), la cella è
    inammissibile per l'attività **da sola**, cioè per i suoi vincoli
    strutturali: nessuno spostamento altrui potrebbe aiutare, ed è una
    dimostrazione. Le causali le dà `trial_placements` di `domain/analysis`,
    che per ogni cella già calcola *perché* è esclusa — la stessa lettura su
    cui poggia la classifica dei vincoli da allentare.

    ⚠ Se invece la cella è nel dominio e il modello è comunque infattibile, la
    causa **non** è in quella lettura: `trial_placements` risponde a «cosa si
    romperebbe se nessun altro si muovesse», mentre qui gli altri si sono
    potuti muovere e non è bastato. Attribuirle la colpa sarebbe una diagnosi
    inventata, quindi qui si dichiara ciò che si sa e non di più — il caso in
    cui `Piazza e sistema` va sostituito dal risolutore passo-passo, che v1
    non ha."""
    if not solution.stats.get("pin_fuori_dominio"):
        return ("La collocazione è ammissibile per l'attività, ma "
                "l'orario non si ricompone attorno: le altre attività non "
                "hanno dove andare.",)
    state = ScheduleState.build(schedule)
    activity = state.activities.get(activity_id)
    if activity is None:
        return ("L'attività non fa parte di questo orario.",)
    for d, s, coarse in trial_placements(activity, state, relaxed=True):
        if (d, s) != (day, start):
            continue
        frasi = tuple(sorted(
            causali.CAUSALI[code].format(resource=_nomi(state, resources),
                                         subject=_nomi(state, resources),
                                         unit=_nomi(state, resources))
            for code, resources in coarse if code in CAUSALI_DI_PREFILTRO))
        return frasi or ("La collocazione non è ammissibile per l'attività.",)
    return ("La collocazione esce dalla griglia oraria dell'attività.",)


def _nomi(state, resources):
    out, visti = [], set()
    for k in sorted(resources, key=resource_sort_key):
        nome = state.resource_names.get(k, str(k))
        if nome not in visti:
            visti.add(nome)
            out.append(nome)
    return ", ".join(out) or "—"
