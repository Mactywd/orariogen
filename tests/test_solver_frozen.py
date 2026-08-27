# tests/test_solver_frozen.py
"""Il banco che **congela**.

⚠ Fino al 2026-08-26 nessun test del banco congelava niente (Ruling 20, §9.7
della spec: «il buco strutturale piu' grande che resta»). Ogni attivita' del
testimone era libera, quindi in ogni modello costruito dal banco `ctx.free`
conteneva tutto: `split()` restituiva sempre `frozen = 0`, `any_free` sempre
`True`, `frozen_occupies` sempre `False`, `residual_cap` non clampava mai, e i
rami disgiuntivi di ADR-018 non venivano mai imboccati. La copertura di
ADR-018 — cinque casi, due dei quali trovati falsificando la spec il giorno
dopo averla scritta — poggiava interamente sui test scritti a mano.

`test_modello_sporco` e' il banco di ADR-018 vero: le congelate sono **gia' in
violazione**, e la domanda e' se il solver le accetta come stato di partenza
invece di pretendere che le libere le riparino. La prova che morde e' la
**prima**, non la seconda: si forza ogni libera nella cella del testimone e si
attende che il modello non risponda `INFEASIBLE` — la forma della casa
(forzare e attendere uno stato), non «risolvi e guarda dove e' finita».

⚠ **C'era un secondo banco, e la mutazione l'ha bocciato.**
`run_family_congelata` congelava una parte del testimone **dov'e'**, famiglia
per famiglia, su una baseline che restava pulita: 78 test, 28 secondi — i due
terzi del tempo aggiunto. Su **sette** mutazioni (`residual_cap` senza clamp,
`split` che conta le congelate come libere, `frozen_occupies` sempre falso,
`any_free` sempre vero, `_sede_congelata` sempre falso,
`_status_quo_rappresentabile` sempre vero, congelate con dominio pieno) non e'
diventato rosso **una sola volta**, mentre questo file le ha colte su **sei**
delle sette — i due test qui sotto su quattro e due rispettivamente, e zero per
entrambi sul clamp di `residual_cap`, che resta difeso dai soli test scritti a
mano. Un test che non diventa rosso quando il codice che afferma sparisce non
sta affermando niente: rimosso. La misura e' il motivo, ed e' nel ledger — non
ricostruirlo senza prima trovargli una mutazione che lo faccia cadere.

Cosa ha trovato, la prima volta che e' stato acceso (seme 38):
`SiteTransitionBuilder` postava una clausola gia' insoddisfacibile per colpa
delle sole congelate. Il commento di modulo di
`domain/solver/builders/time_sites.py` — e il docstring di
`tests/test_solver_sites.py::test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca`
— dichiaravano entrambi che quel builder «ha gia' ADR-018 nella forma della
regola dell'implicazione». Non ce l'aveva: `any_free` guarda chi **tocca** le
due fasce, non chi **realizza** la coppia di sedi vietata. Il caso ridotto
alla forma minima sta in `test_solver_sites.py`."""
import pytest

from domain.solver import builders  # noqa: F401 — forza la registrazione
from tests.solver_harness import run_modello_sporco

pytestmark = pytest.mark.django_db

# I semi del banco sporco. Scelti su una passata di 40: **36 su 40** producono
# una costruzione utilizzabile (saltano 13, 14, 17 e 28, dove le violazioni
# create dal ripack implicano quasi tutte le attivita' e restano meno di tre
# libere), e la dirt copre in tutto **26 causali distinte**. Questi dieci sono
# scelti per coprire fenomeni diversi, non a caso:
#
#   1   subject_parts_order fra le causali sporcate
#   5   subject_weekly_order — una delle tre famiglie a ramo disgiuntivo
#   6   fa scattare l'esenzione «deriva d'identita'»
#   9   free_guaranteed e max_gap insieme
#  16   arrival_departure, e deriva d'identita'
#  20   deriva d'identita' su subject_imposed_succession (fino all'ondata 5
#       faceva scattare anche l'esenzione del ramo pigro, che non esiste piu')
#  27   la dirt piu' larga misurata: undici causali su un solo testimone
#  30   il rapporto piu' estremo, 29 congelate contro 3 libere
#  36   min_distribution e site_transition insieme
#  38   ⚠ il seme che ha trovato il difetto di SiteTransitionBuilder
#
# Su questi dieci la costruzione **non puo' saltare**: `run_modello_sporco`
# deve restituire qualcosa, e l'assert lo pretende. Se un giorno la fixture o
# i derivatori cambiano al punto da non produrre piu' sporco su questi semi, il
# banco diventa rosso invece di svuotarsi in silenzio.
SEMI_SPORCHI = [1, 5, 6, 9, 16, 20, 27, 30, 36, 38]


@pytest.mark.parametrize("seed", SEMI_SPORCHI)
def test_modello_sporco(seed):
    esito = run_modello_sporco(seed)
    assert esito is not None, (
        f"il seme {seed} non produce piu' una costruzione sporca "
        f"utilizzabile: rimisurare e riscegliere i semi, non cancellare il "
        f"caso")
    _w, congelate, libere, esiti = esito
    assert len(esiti["dirt"]) >= 2, (
        f"il seme {seed} sporca una sola causale ({esiti['dirt']}): la "
        f"costruzione si sta svuotando")
    print(f"\nsporco, seed {seed}: {len(congelate)} congelate in violazione / "
          f"{len(libere)} libere, dirt={esiti['dirt']}, "
          f"deriva={esiti['deriva']}, "
          f"{esiti['soluzione'].status}")


class _Rollback(Exception):
    """Uscita da `transaction.atomic` che annulla la fixture: serve a provare
    piu' semi dentro un test solo, perche' ricostruire la scuola due volte
    nella stessa transazione violerebbe l'unicita' delle anagrafiche."""


def _cerca(fenomeno, semi):
    """Il primo seme di `semi` che esercita `fenomeno`, o None.

    ⚠ Perche' una **ricerca** e non un seme appuntato: i due fenomeni sono
    proprieta' della **soluzione restituita**, non dell'istanza. Cambia
    l'obiettivo — e questo pezzo ne aggiunge uno per ondata — e il solver
    sceglie un altro ottimo, altrettanto valido, in cui il fenomeno non
    compare. Appuntando un seme il test va rimisurato a ogni ondata (misurato:
    tre volte in una sessione, spostandosi fra 7, 11, 16, 20 e 24); cercando
    su una lista dichiarata, il test afferma la cosa che conta davvero —
    **l'esenzione e' esercitata da qualcosa**.

    Resta un test che puo' fallire, ed e' voluto: se nessuno dei semi esercita
    piu' l'esenzione, quell'esenzione non e' piu' affermata da niente e va
    rimisurata o rimossa."""
    from django.db import transaction
    for seme in semi:
        esito = None
        try:
            with transaction.atomic():
                esito = run_modello_sporco(seme)
                raise _Rollback
        except _Rollback:
            pass
        if esito is not None and esito[3][fenomeno]:
            return seme, esito[3]
    return None


# I semi su cui cercare. Ristretti apposta: la ricerca costa un solve per seme,
# e questi sono quelli che hanno esercitato l'uno o l'altro fenomeno in almeno
# una delle configurazioni provate.
SEMI_FENOMENI = [12, 16, 20, 24, 35, 7, 11]


# ⚠ **L'esenzione del ramo pigro non esiste piu'** (ondata 5): L3 minimizza le
# riparazioni mancate, e su 60 semi il fenomeno non compare piu' — prima era ai
# semi 20, 35, 41, 45 e 52. Il test che la esercitava e' stato tolto insieme a
# lei: un'esenzione che non scatta mai non e' un'esenzione.


def test_l_esenzione_della_deriva_d_identita_e_esercitata():
    """L'altra esenzione: stessa causale, stessa risorsa, stesse quantita',
    **altra** coppia nominata in `activities`. Il finding cambia identita'
    senza che la violazione cambi, perche' piazzare una libera accanto a una
    congelata cambia *quale* coppia e' l'argmin."""
    trovato = _cerca("deriva", SEMI_FENOMENI)
    assert trovato is not None, (
        f"nessuna deriva d'identita' su {SEMI_FENOMENI}: l'esenzione "
        f"`_grossa` non e' piu' esercitata da nessun test — rimisurare i "
        f"semi, non togliere il test")
    seme, esiti = trovato
    print(f"\nderiva d'identita' al seme {seme}: {len(esiti['deriva'])} occorrenze")
