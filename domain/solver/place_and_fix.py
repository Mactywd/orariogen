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
from domain.models import Activity
from domain.solver.model import solve

_IMMOBILE = (Activity.Immobility.FIXED, Activity.Immobility.LOCKED_IN_PLACE)


CAUSALI_DI_PREFILTRO = frozenset({
    # ⚠ I soli due builder che implementano `restrict()` sono `GridBuilder` e
    # `UnavailabilityBuilder`. Filtrare su queste causali non è prudenza, è
    # precisione — la lettura di `trial_placements` valuta tutti i checker
    # contro lo stato corrente, e includerebbe l'occupazione da parte di
    # attività che `Piazza e sistema` saprebbe spostare: incolparle sarebbe una
    # diagnosi falsa. `test_solo_due_builder_prefiltrano` tiene ferma la
    # premessa.
    #
    # ⚠ Ma «i pre-filtri sono due» **non** vuol dire «un pin fuori dominio può
    # venire solo di lì», e qui c'era scritto il contrario. Il dominio lo
    # restringe anche `SolverContext.build`, *prima* di qualunque `restrict()`:
    # a un'attività immobile e già piazzata dà un dominio di **cardinalità
    # uno** (la sua collocazione attuale), e lo stesso a tutto ciò che sta
    # fuori dall'estrazione. Sono le tre ragioni di `_fuori_dal_modello`, che
    # vanno riconosciute **prima** di consultare il catalogo delle causali —
    # o si finisce a rispondere «la collocazione non è ammissibile» su una
    # cella perfettamente libera.
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
        obstruction = _perche_no(schedule, activity_id, day, start, solution,
                                 extraction)
    return PlaceAndFix(solution=solution, activity_id=activity_id,
                       cell=(day, start), moved=moved, dropped=dropped,
                       obstruction=obstruction)


def _fuori_dal_modello(schedule, activity_id, extraction):
    """Le tre ragioni per cui il dominio è già un singoletto (o è vuoto)
    **prima** che un pre-filtro tocchi qualcosa, e quindi le tre risposte che
    il catalogo delle causali non può dare.

    🔑 Sono decisioni di `SolverContext.build`, non di un `restrict()`:
    l'immobile piazzata ha per dominio la sua sola collocazione attuale
    (`cells[aid] = {placed[aid]}`, la premessa di ADR-018), l'immobile mai
    piazzata è fuori dal modello del tutto, e ciò che sta fuori
    dall'estrazione è congelato dov'è. In tutti e tre i casi la cella
    richiesta può essere **perfettamente libera** — e infatti di solito lo è.

    ⚠ Senza questa lettura la risposta era «La collocazione non è ammissibile
    per l'attività» su una griglia vuota: non solo inutile, ma falsa, e falsa
    proprio nella direzione che manda l'utente a cercare un vincolo che non
    esiste. Il rimedio è invece sempre lo stesso e non è un vincolo: sbloccare
    l'attività, o allargare l'estrazione."""
    act = Activity.objects.filter(pk=activity_id).first()
    if act is None:
        return "L'attività non esiste."
    if act.immobility == Activity.Immobility.SUSPENDED:
        return ("L'attività è sospesa: non entra nell'orario, e sospesa non "
                "la si può collocare da nessuna parte.")
    if act.immobility in _IMMOBILE:
        piazzata = schedule.placements.filter(activity_id=activity_id).first()
        dove = (f"è bloccata su giorno {piazzata.day}, fascia "
                f"{piazzata.start_slot}" if piazzata is not None
                else "è bloccata e non è mai stata piazzata")
        return (f"L'attività {dove}: il suo blocco la tiene ferma, e nessun "
                "vincolo dell'orario c'entra. Va sbloccata prima di spostarla.")
    if extraction is not None and not extraction.activities.filter(
            pk=activity_id).exists():
        return (f"L'attività non fa parte dell'estrazione "
                f"«{extraction.name}»: fuori dal perimetro resta dov'è, "
                "esattamente come una congelata. Va estratta prima di "
                "spostarla.")
    return None


def _perche_no(schedule, activity_id, day, start, solution, extraction=None):
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
    fuori = _fuori_dal_modello(schedule, activity_id, extraction)
    if fuori is not None:
        return (fuori,)
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
