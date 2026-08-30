"""L'ondata 6 del banco, terza parte: i criteri di qualità.

`QualityCriterion` è vuota su entrambi i dataset da quando esiste. Il Fermi non
ne ha (ed è fedele: in EDT l'`Ottimizzazione degli orari` ha tre slot su cinque
e nella base di esempio due restano a `Nessuno`), l'Alighieri non ne aveva, e
il difetto del budget in coda — trovato il 2026-08-30 — è emerso solo
seminandone cinque a mano. Qui la gerarchia è **un dato del banco**.

⚠ **E `build()` non la installa.** Non è pigrizia: sei livelli portano un
`solve` da 9 a **82 secondi**, e ogni test dell'Alighieri li pagherebbe. È
anche la forma giusta, perché in EDT l'ottimizzazione è un comando a sé che si
lancia su un orario che già c'è — `Ottimizza gli orari dei docenti` non è una
fase del calcolo. Chi vuole la qualità la chiede.

🔑 **E qui si chiude un anello aperto dall'ondata 5.** Il pennello verde di
AMATO — la sola indisponibilità che non vieta niente — là si provava *al
contrario*, mostrando che l'orario esiste lo stesso. Qui si prova che **conta**:
`preferences_all` scende a zero e lo dimostra. Un pre-filtro che non filtra e
un criterio che non conta si somigliano molto, e sono cose diverse."""

import pytest

from domain.models import Activity, QualityCriterion, Teacher
from domain.solver.model import apply, solve
from domain.solver.quality import Arbitrato
from tests import alighieri

pytestmark = pytest.mark.django_db


def _esiti(soluzione):
    return {l["nome"]: l for l in soluzione.stats["livelli"]}


def test_la_gerarchia_e_completa_e_ordinata_dai_dati():
    """Sei righe, **cinque generi** — cioè la tabella intera — e le due
    popolazioni. Un genere che non compare è un criterio *ignorato*, e la
    tabella vuota dà la catena senza qualità: è la UI di EDT, «Criteri
    considerati / ignorati», detta in una tabella."""
    alighieri.build(qualita=True)
    righe = list(QualityCriterion.objects.all())
    assert len(righe) == 6
    assert {r.kind for r in righe} == set(QualityCriterion.Kind.values)
    assert [r.rank for r in righe] == [1, 2, 3, 4, 5, 6]
    # ⚠ L'equilibrio didattico solo sulle classi: l'asimmetria è del prodotto.
    regolarita = QualityCriterion.objects.get(kind="regularity")
    assert regolarita.population == QualityCriterion.Population.CLASSES


def test_la_catena_arriva_in_fondo_e_dichiara_cosa_ha_dimostrato():
    """La catena completa sul banco: quattro livelli di fallimento più sei di
    qualità, nell'ordine dichiarato dai dati.

    🔑 **E il rendiconto porta il divario**, che è ciò che distingue «zero» da
    «zero non dimostrato». La lezione del Fermi si ripete a scala maggiore: un
    livello di qualità non è lento perché difficile da ottimizzare, è lento
    perché **impossibile da dimostrare**. `gaps` chiude a zero in pochi
    secondi perché zero è anche il suo limite inferiore banale; `isolated`,
    `free_half_days` e `regularity` esauriscono il budget con un divario
    aperto.

    ⚠ Lo stato della catena è quello del **suo ultimo livello**, quindi un
    `FEASIBLE` qui non è un fallimento: dice che l'ultimo livello non ha
    dimostrato il proprio ottimo. Ciò che deve restare vero è che nessuna
    attività è scartata — la qualità cede a tutto il resto, e non si compra
    con uno scarto."""
    env = alighieri.build(qualita=True)
    soluzione = solve(env["schedule"], workers=8)
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.stats["scartate"] == 0
    esiti = _esiti(soluzione)
    assert list(esiti) == [
        "minuti_scartati", "attivita_scartate", "violazioni_nuove",
        "gaps_teachers", "gaps_classes", "isolated_all",
        "free_half_days_teachers", "regularity_classes", "preferences_all",
    ]
    # I buchi arrivano a zero **e lo dimostrano**, per entrambe le popolazioni.
    for nome in ("gaps_teachers", "gaps_classes"):
        assert esiti[nome]["valore"] == 0 and esiti[nome]["ottimo"], esiti[nome]
    # E almeno un livello chiude col divario aperto. ⚠ Si asserisce
    # l'**esistenza** e non quali: misurati, sono `isolated_all` (71),
    # `free_half_days_teachers` (143, limite inferiore 19) e
    # `regularity_classes` (936, limite inferiore 101), ma quali esattamente
    # dipende da quanto la ricerca arriva a dimostrare dentro il budget, e
    # fissarlo sarebbe fissare un fatto sulla ricerca.
    assert any(l["divario"] > 0 for l in soluzione.stats["livelli"])


def test_il_verde_conta_e_lo_dimostra():
    """🔑 L'anello dell'ondata 5, chiuso dall'altro capo.

    La riga `preferenza` mette AMATO in verde sulla prima fascia di tutti i
    giorni. L'ondata 5 ha provato che **non vieta**: l'orario esiste lo stesso.
    Qui si prova che **conta**: il criterio scende a zero e lo dimostra, cioè
    nessuna delle sue ore finisce sulla prima fascia. Nessuna garanzia — in
    EDT è l'undicesimo e ultimo criterio, e cede a tutto — ma su questo banco
    la si può soddisfare, e la si soddisfa.

    ⚠ **Il criterio è solo, e non è una comodità.** Con la gerarchia intera il
    valore osservato è stato 0 in una misura e **1** in un'altra, e la ragione
    non è il verde: i tre livelli sopra di lui esauriscono il budget senza
    dimostrare il proprio ottimo, quindi vengono fissati al valore che la
    ricerca *ha trovato*, che cambia da esecuzione a esecuzione — e con esso
    cambia la regione in cui il verde deve stare. Asserire zero là dentro
    sarebbe fissare un fatto sulla **ricerca**; da solo, lo zero è una
    proprietà del **modello**. È la stessa lezione della mutazione per
    rimozione dell'ondata 3."""
    env = alighieri.build()
    QualityCriterion.objects.create(
        kind=QualityCriterion.Kind.PREFERENCES,
        population=QualityCriterion.Population.ALL, rank=1)
    soluzione = solve(env["schedule"], workers=8)
    esiti = _esiti(soluzione)
    assert esiti["preferences_all"]["valore"] == 0
    assert esiti["preferences_all"]["ottimo"]
    apply(soluzione, env["schedule"])
    amato = Teacher.objects.get(abbreviation="AMATO")
    prime = [p for p in env["schedule"].placements.all()
             if p.start_slot == 0 and amato in p.activity.teachers.all()]
    assert prime == []


def test_l_arbitrato_sacrifica_una_popolazione_e_dichiara_quanto():
    """La separazione per popolazione, su un orario che **già c'è** — che è
    l'unico modo in cui EDT la esegue.

    Prima il calcolo senza qualità (nove secondi), poi la scuola chiede di
    ottimizzare i **docenti**: i criteri delle classi smettono di essere
    livelli e diventano tetti di non-regressione `valore <= base + tolleranza`,
    dove la base è il valore che quel criterio ha sull'orario di partenza. E
    la **stabilità** scivola in coda a fare da spareggio, che è la ragione per
    cui i criteri di qualità erano inerti su ogni orario già scritto finché
    l'arbitrato non è esistito.

    ⚠ Ed è anche il posto in cui si vede il difetto corretto il 2026-08-30: in
    coda, `spostamenti` prende `BUDGET_QUALITA` come gli altri. Senza,
    `solve --popolazione` sul Fermi veniva ucciso a dodici minuti."""
    env = alighieri.build()
    primo = solve(env["schedule"], workers=8)
    assert primo.status == "OPTIMAL"
    apply(primo, env["schedule"])

    alighieri.criteri_di_qualita()
    soluzione = solve(env["schedule"], workers=8,
                      arbitrato=Arbitrato(popolazione="teachers", tolleranza=5))
    assert soluzione.status in ("OPTIMAL", "FEASIBLE"), soluzione.stats
    assert soluzione.stats["scartate"] == 0

    esiti = _esiti(soluzione)
    # I criteri della popolazione sacrificata non sono livelli...
    assert "gaps_classes" not in esiti and "regularity_classes" not in esiti
    # ...sono tetti, e ognuno dichiara la base da cui non deve peggiorare.
    tetti = {a["nome"]: a for a in soluzione.stats["arbitraggi"]}
    assert set(tetti) == {"gaps_classes", "regularity_classes"}
    for a in tetti.values():
        assert a["tetto"] == a["base"] + 5
    # E la stabilità è l'ultimo livello, non il primo.
    assert list(esiti)[-1] == "spostamenti"
    assert esiti["spostamenti"]["valore"] <= Activity.objects.count()
