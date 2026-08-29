"""Il picco d'occupazione del **gruppo di aule**: n attivita' che scelgono
dentro lo stesso insieme di aule, e nell'insieme non ci stanno.

🔑 **Perche' non e' `structural:occupation`.** Quel checker conta una chiave
alla volta, e una chiave d'aula esiste solo quando la scelta e' determinata —
aula assegnata, oppure candidata unica (`activity_tokens`). Tre attivita' che
chiedono ciascuna «LAB-FIS *oppure* LAB-INF» non superano nessuna capienza
singola: nessuna delle due aule e' occupata da nessuno, perche' nessuna delle
tre ha ancora scelto. E tuttavia in due aule non stanno. La violazione non e'
di una risorsa, e' di un **insieme**.

🔑 **Perche' e' una causale del piazzamento e non dell'assegnazione.** La
frase e' di EDT alla lettera — *«il gruppo di aule ha raggiunto il suo picco
d'occupazione»* — e sta in `AffSco_UtilDiagnostic`, la famiglia che spiega
**perche' un'attivita' non si piazza** (`docs/edt/diagnostica.md`). Lo
conferma la finestra del risolutore passo-passo, dove l'attivita' porta il
conto di tutte e cinque le risorse (`Aule 0`) e le risorse in conflitto
diventano rosse, aule comprese (`docs/edt/motore-risoluzione.md`). In EDT le
aule si **contano** mentre si piazza; l'ottimizzatore dedicato sceglie *quale*
aula fra le ammissibili, che e' un'altra domanda. Vedi ADR-021.

## Il metodo: Hall, non il totale

Sull'**unione** delle candidate la capienza quasi sempre basta — misurato sul
Fermi: su nessuna delle 26 celle contese l'unione era in deficit, e le rinunce
c'erano lo stesso. Il deficit vive in un **sottoinsieme**: e' il teorema di
Hall, e il modo di trovarlo e' quello che `domain/analysis/hall.py` usa gia'
per le fasce — flusso massimo, e il lato sorgente del taglio minimo *e'*
l'insieme colpevole.

Rete, per ogni cella: sorgente → attivita' (capienza 1) → aule candidate
(capienza infinita) → pozzo (capienza simultanea dell'aula). Il flusso massimo
e' il numero di richieste servibili; cio' che avanza e' il deficit.

⚠ **L'insieme nominato e' l'unione delle candidate del gruppo colpevole**, non
il lato sorgente grezzo del taglio: i due contengono le stesse attivita', ma
il taglio puo' portarsi dietro aule che nessuno di quel gruppo chiede, e
mandare a smontare l'aula sbagliata e' il difetto peggiore di una
diagnostica."""

from collections import defaultdict

from domain.analysis import causali
from domain.analysis.findings import Finding, Severity
from domain.analysis.flow import INF, MaxFlow
from domain.analysis.registry import Checker, register
from domain.analysis.state import resource_sort_key

CODE = "room_group_peak"


def _candidates(state, aid, act):
    """Le aule fra cui l'attivita' puo' finire, come le vede la seconda fase.

    ⚠ Le **dichiarate**, non l'assegnata: `Placement.assigned_room` e' una
    ripartizione rivedibile, non un fatto — `solve_rooms` la tratta come
    preferenza (livello `cambi_aula`) e non come vincolo. Contarla come fissa
    inventerebbe deficit che la fase 2 scioglie da sola.

    Un'assegnazione **senza** candidate dichiarate e' invece un fatto: nessuna
    fase la rivede, quindi quell'aula e' consumata."""
    rooms = {r.pk for r in act.rooms.all()}
    if rooms:
        return rooms
    assegnata = state.assigned_room.get(aid)
    return {assegnata} if assegnata is not None else set()


def _capacity(state, room_id, day, slot):
    """⚠ Solo il rosso azzera il posto. Un'indisponibilita' **opzionale** e'
    violabile per definizione — l'opzione di calcolo di EDT la scavalca per
    categoria di risorsa — e contarla come chiusa produrrebbe un finding
    `HARD` per un ostacolo che duro non e'."""
    if state.unavailability.get((room_id, day, slot)) == "hard":
        return 0
    return state.capacity.get(room_id, 1)


@register("structural:room_pool")
class RoomPoolChecker(Checker):
    # Monotono: una richiesta in piu' su una cella non puo' che aggiungere
    # domanda a quella cella. Nessun piazzamento *ripara* un deficit di Hall,
    # e l'identita' del finding si sposta solo allargando il gruppo colpevole
    # — cioe' aggravando, che e' precisamente cio' che la monotonia ammette.
    PLACEMENT_MONOTONE = True

    def check(self, state, resources=None):
        per_cella = defaultdict(list)
        for aid, act in state.activities.items():
            collocazione = state.placed.get(aid)
            if collocazione is None:
                continue
            candidate = _candidates(state, aid, act)
            if not candidate:
                continue
            for slot in collocazione.slots:
                per_cella[(collocazione.day, slot)].append((aid, candidate))

        for (day, slot), voci in sorted(per_cella.items()):
            yield from self._cella(state, day, slot, voci, resources)

    def _cella(self, state, day, slot, voci, resources):
        """⚠ Il flusso si calcola **sempre**, anche dove la capienza totale
        basterebbe: e' precisamente il caso in cui il deficit si nasconde in
        un sottoinsieme, ed e' il caso misurato sul Fermi. Una guardia sul
        totale sarebbe la stessa scorciatoia che rende `structural:occupation`
        cieco a questa famiglia. Le reti sono minuscole — una cella, poche
        richieste — e il costo non si vede."""
        voci = sorted(voci)
        aule = sorted({r for _aid, cand in voci for r in cand})
        capienze = {r: _capacity(state, r, day, slot) for r in aule}

        indice_att = {aid: i for i, (aid, _c) in enumerate(voci)}
        indice_aula = {r: len(voci) + i for i, r in enumerate(aule)}
        sorgente, pozzo = len(voci) + len(aule), len(voci) + len(aule) + 1
        rete = MaxFlow(pozzo + 1)
        for aid, candidate in voci:
            rete.add_edge(sorgente, indice_att[aid], 1)
            for r in sorted(candidate):
                rete.add_edge(indice_att[aid], indice_aula[r], INF)
        for r in aule:
            rete.add_edge(indice_aula[r], pozzo, capienze[r])
        if rete.max_flow(sorgente, pozzo) == len(voci):
            return

        lato = rete.source_side(sorgente)
        colpevoli = [(aid, cand) for aid, cand in voci
                     if indice_att[aid] in lato]
        pool = sorted({r for _aid, cand in colpevoli for r in cand})
        dentro = sorted(aid for aid, cand in voci if set(cand) <= set(pool))
        capienza = sum(capienze[r] for r in pool)
        if len(dentro) <= capienza:
            return
        if all(len(cand) == 1 for aid, cand in voci if aid in dentro):
            # Tutte a candidata unica: e' il sovraccarico di **una** aula, che
            # e' una chiave di occupazione e che `structural:occupation` gia'
            # nomina. Dirlo due volte manda a cercare due problemi dove ce
            # n'e' uno.
            return
        if resources is not None and not (set(pool) & set(resources)):
            return
        etichetta = ", ".join(state.resource_names.get(r, str(r)) for r in pool)
        yield Finding(
            CODE, causali.message(CODE, resource=etichetta), Severity.HARD,
            resources=tuple(sorted(pool, key=resource_sort_key)),
            activities=tuple(dentro),
            quantities={"day": day, "slot": slot,
                        "load": len(dentro), "capacity": capienza},
        )
