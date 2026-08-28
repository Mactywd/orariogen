"""L'ordinamento dei vincoli per numero di fallimenti causati: il ponte
mancante fra «il calcolo è fallito» e «quale vincolo allento»
(`docs/scope-v1.md`, «Le due lacune di EDT, che sono la nostra occasione»).

EDT dice *che* un'attività non si piazza, e la finestra `Alleggerimenti` dice
*quali* vincoli si possono allentare — ma nessuna delle due dice quale
allentare **per primo**. Qui si conta: ogni cella che il piazzamento di prova
scarta porta con sé le causali che l'hanno scartata, e le causali si ordinano
per quanto costano.

🔑 **L'unità di misura non è la riga di vincolo: è la coppia (causale,
risorsa).** Un `Finding` non porta il pk della riga che l'ha generato, e
`ResourceTimeConstraint` non ha unicità su `(resource, type)` — quindi
risalire alla riga sarebbe una deduzione, non una lettura. La coppia è invece
esattamente ciò che l'utente va a toccare («il D.T.B. del prof. Rossi»), ed è
la stessa chiave grossolana che il progetto usa già per le famiglie
indipendenti dal piazzamento. Dove più righe condividono la coppia, la
classifica le nomina insieme, che è il verdetto corretto: sono
indistinguibili dall'orario.

🔑 **Il numero che conta è `activities_freed`, non `cells_blocked`.** Un
dominio si svuota per **congiunzione** — la cella 1 la esclude un vincolo, la
cella 2 un altro — quindi «questo vincolo esclude 400 celle» non implica che
allentarlo serva a qualcosa. `activities_freed` risponde alla domanda vera:
*se allento questo, quante attività tornano ad avere dove andare?* Sono le
attività a dominio vuoto per cui esiste una cella la cui **unica** causale è
questa. Il resto della riga è pressione, e sta in classifica sotto.

⚠ **Le famiglie non monotone non compaiono, ed è una rinuncia dichiarata.**
Il criterio di `admissible_starts` — «una chiave nuova rispetto alla baseline
significa cella inammissibile» — è falso per i checker con
`PLACEMENT_MONOTONE = False`: là piazzare può *riparare* la violazione o
spostarne l'identità, quindi **ogni** cella produce una chiave nuova.
Contarle le metterebbe in cima a qualunque classifica, su qualunque dataset,
per un artefatto del criterio — cioè manderebbe l'utente a smontare il
vincolo sbagliato, che è l'unico errore che questa funzione non ha il diritto
di fare. Si passa quindi `relaxed=True`, come la fase 5: si perde
**richiamo**, mai precisione. `famiglie_silenziose()` le legge dal registro
invece di elencarle, e il comando le dichiara invece di lasciarle
sottintese — fra loro c'è il D.T.B., che è uno dei vincoli che le scuole
allentano più spesso.
"""

from collections import defaultdict
from dataclasses import dataclass

from domain.analysis import causali
from domain.analysis.conformity import week_signatures
from domain.analysis.domain_size import free_candidates, trial_placements
from domain.analysis.registry import REGISTRY, all_checkers
from domain.analysis.state import ScheduleState, resource_sort_key
from domain.models import TimeGrid


@dataclass(frozen=True)
class ConstraintBlame:
    """Una riga della classifica: la coppia (causale, risorsa) e il suo costo."""

    code: str
    resources: tuple
    statement: str            # la frase italiana, con i nomi delle risorse
    resource_labels: tuple
    activities_freed: int     # attività a dominio vuoto che questo solo vincolo riaprirebbe
    activities_blocked: int   # attività di cui esclude **ogni** cella, da solo
    cells_alone: int          # celle di cui è l'unica causale
    cells_blocked: int        # celle in cui compare, da sola o in compagnia


@dataclass(frozen=True)
class BlameReport:
    rows: tuple
    unplaceable: tuple        # pk delle attività rimaste senza nessuna cella
    considered: int           # attività esaminate


def famiglie_silenziose():
    """Le famiglie che il rilassamento esclude dalla classifica, **lette dal
    registro** invece che elencate: una famiglia marcata non monotona domani
    deve entrare qui senza che nessuno se ne ricordi."""
    all_checkers()  # forza la registrazione
    return tuple(sorted(str(k) for k, cls in REGISTRY.items()
                        if not cls.PLACEMENT_MONOTONE))


def _labels(names, resources):
    """I nomi delle risorse, deduplicati per nome come in `hall._labels` e per
    la stessa ragione: gli atomi di ADR-017 sono chiavi distinte che portano
    tutte il nome della classe."""
    out, visti = [], set()
    for k in sorted(resources, key=resource_sort_key):
        nome = names.get(k, str(k))
        if nome not in visti:
            visti.add(nome)
            out.append(nome)
    return tuple(out)


def _statement(code, labels):
    """La frase della causale con i segnaposto riempiti dai nomi delle risorse.

    ⚠ Per `{resource}` e `{unit}` è esatta. Per `{subject}` — le causali dei
    vincoli di materia — è **più grossolana** della frase originale: quelle
    causali nominano la materia, e la chiave grossolana la materia non ce
    l'ha, quindi al suo posto compare l'unità didattica su cui la riga è
    scritta. È la stessa perdita che la chiave dichiara altrove, non un errore
    di formattazione: la classifica aggrega sulle materie, e una riga che
    nominasse una materia sola mentirebbe sul proprio conteggio."""
    testo = ", ".join(labels) or "—"
    return causali.CAUSALI[code].format(resource=testo, subject=testo, unit=testo)


def rank_constraints(schedule, relaxed=True):
    """La classifica dei vincoli per fallimenti causati.

    ⚠ **Le firme di settimana sono una dimensione, non un dettaglio**, e qui
    non si aggregano sommando: un'attività va collocata in **una** cella
    valida in **tutte** le settimane in cui è attiva, quindi le causali di una
    stessa cella si **uniscono** fra le firme e la cella è ammissibile solo se
    l'unione è vuota. Sommare le firme conterebbe più volte la stessa
    attività; ignorarle nasconderebbe i vincoli che mordono solo in alcune
    settimane. Il costo è lineare nel numero di firme, come per la fase 5.
    """
    if TimeGrid.objects.first() is None:
        return BlameReport((), (), 0)

    blame = defaultdict(frozenset)   # (attività, cella) → causali grossolane
    celle = defaultdict(set)         # attività → celle valutate
    names = {}
    for representative, _weeks in week_signatures(schedule):
        state = ScheduleState.build(schedule, week=representative)
        names.update(state.resource_names)
        for a in free_candidates(state):
            # ⚠ Si tocca `celle` anche a mani vuote: un'attività più lunga
            # della giornata non ha nessuna cella da provare, quindi il ciclo
            # sotto non gira mai. Senza questa riga sparirebbe dal rapporto —
            # cioè l'attività **più** impiazzabile di tutte sarebbe l'unica a
            # non comparire fra le impiazzabili.
            celle.setdefault(a.id, set())
            for day, start, coarse in trial_placements(a, state, relaxed=relaxed):
                blame[(a.id, (day, start))] |= coarse
                celle[a.id].add((day, start))

    conti = defaultdict(lambda: {"cells": 0, "alone": 0,
                                 "blocca": set(), "libera": set()})
    unplaceable = []
    for aid, cells in sorted(celle.items()):
        vuoto = all(blame[(aid, c)] for c in cells)
        if vuoto:
            unplaceable.append(aid)
        ovunque = None
        for c in sorted(cells):
            b = blame[(aid, c)]
            ovunque = b if ovunque is None else (ovunque & b)
            for chiave in b:
                riga = conti[chiave]
                riga["cells"] += 1
                if len(b) == 1:
                    riga["alone"] += 1
                    if vuoto:
                        riga["libera"].add(aid)
        # `ovunque` è vuoto appena una cella è ammissibile: `activities_blocked`
        # conta quindi solo le attività che questa causale, da sola, basta a
        # lasciare senza collocazione.
        for chiave in ovunque or frozenset():
            conti[chiave]["blocca"].add(aid)

    rows = []
    for (code, resources), riga in conti.items():
        labels = _labels(names, resources)
        rows.append(ConstraintBlame(
            code=code, resources=resources,
            statement=_statement(code, labels), resource_labels=labels,
            activities_freed=len(riga["libera"]),
            activities_blocked=len(riga["blocca"]),
            cells_alone=riga["alone"], cells_blocked=riga["cells"],
        ))
    rows.sort(key=_ordine)
    return BlameReport(tuple(rows), tuple(unplaceable), len(celle))


def _ordine(row):
    """Prima ciò su cui si può agire, poi la pressione; l'ultimo criterio è
    l'identità della riga, perché una classifica che cambia ordine a parità di
    numeri non è leggibile due volte."""
    return (-row.activities_freed, -row.activities_blocked,
            -row.cells_alone, -row.cells_blocked,
            row.code, tuple(resource_sort_key(r) for r in row.resources))
