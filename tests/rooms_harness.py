"""Il banco a testimone della ripartizione: si genera **prima**
un'assegnazione valida a caso, e solo dopo si chiede alla fase di ricostruirla.

Rende impossibile l'oracolo vacuo: una fase che non postasse nulla lascerebbe
passare un'assegnazione che il checker boccia, una che postasse `1 == 0` non
troverebbe il testimone.

⚠ Il generatore **dichiara il proprio potere vincolante**: se le aule generate
non stringono (capienza totale molto maggiore della domanda per cella), il seme
salta invece di spacciarsi per un successo verde."""

import random

import pytest

from domain.models import ResourceUnavailability, Room
from tests.analysis_helpers import make_activity, mini_school, place


def costruisci_testimone_aule(seed, n_attivita=12):
    rnd = random.Random(seed)
    env = mini_school(days=3, slots=4)
    aule = [Room.objects.create(name=f"AULA {i}",
                                simultaneous_capacity=rnd.choice([1, 1, 2]))
            for i in range(3)]

    atteso, per_cella = {}, {}
    for _ in range(n_attivita):
        day, slot = rnd.randrange(3), rnd.randrange(4)
        candidate = rnd.sample(aule, rnd.choice([1, 2, 3]))
        # Sceglie l'aula del testimone fra le candidate che hanno ancora posto:
        # e' l'assegnazione valida che la fase dovra' ritrovare.
        libere = [r for r in candidate
                  if per_cella.get((r.pk, day, slot), 0) < r.simultaneous_capacity]
        if not libere:
            continue
        scelta = rnd.choice(libere)
        act = make_activity(env["subject"], rooms=candidate)
        place(env["schedule"], act, day, slot)
        per_cella[(scelta.pk, day, slot)] = per_cella.get(
            (scelta.pk, day, slot), 0) + 1
        atteso[act.id] = scelta.pk

    # Indisponibilita' che il testimone rispetta: aggiungono potere vincolante
    # senza invalidarlo. ⚠ Si escludono le celle che il testimone occupa, o
    # l'assegnazione attesa diventerebbe illegale e il banco misurerebbe un
    # testimone che non esiste.
    occupate = set(per_cella)
    for aula in aule:
        for _ in range(2):
            day, slot = rnd.randrange(3), rnd.randrange(4)
            if (aula.pk, day, slot) in occupate:
                continue
            ResourceUnavailability.objects.create(
                resource=aula, day=day, slot=slot,
                level=ResourceUnavailability.Level.HARD)

    capienze = {r.pk: r.simultaneous_capacity for r in aule}
    stretto = sum(1 for (room_id, _, _), carico in per_cella.items()
                  if carico >= capienze[room_id])
    if len(atteso) < 6 or stretto == 0:
        pytest.skip(f"seed {seed}: il testimone non stringe "
                    f"({len(atteso)} attività, {stretto} celle sature)")
    return {"schedule": env["schedule"], "atteso": atteso, "aule": aule}
