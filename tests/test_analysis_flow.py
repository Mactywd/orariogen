"""Il flusso massimo e il taglio minimo, su grafi minuscoli scritti a mano.
Nessuna nozione di orario qui: se questi test sono verdi e hall.py sbaglia,
l'errore e' nella semantica del dominio, non nell'algoritmo."""

from domain.analysis.flow import INF, MaxFlow


def test_catena_semplice():
    f = MaxFlow(4)
    f.add_edge(0, 1, 3)
    f.add_edge(1, 2, 2)
    f.add_edge(2, 3, 5)
    assert f.max_flow(0, 3) == 2


def test_bipartito_saturo():
    # 2 attivita' da 1 unita', 2 celle da 1: entra tutto.
    f = MaxFlow(6)
    src, snk = 4, 5
    for a in (0, 1):
        f.add_edge(src, a, 1)
        for c in (2, 3):
            f.add_edge(a, c, INF)
    for c in (2, 3):
        f.add_edge(c, snk, 1)
    assert f.max_flow(src, snk) == 2


def test_deficienza_e_lato_sorgente():
    # 3 attivita' da 1 unita', 2 celle da 1: una resta fuori, e il lato
    # sorgente del taglio nomina tutte e tre le attivita' piu' le due celle.
    f = MaxFlow(7)
    src, snk = 5, 6
    for a in (0, 1, 2):
        f.add_edge(src, a, 1)
        for c in (3, 4):
            f.add_edge(a, c, INF)
    for c in (3, 4):
        f.add_edge(c, snk, 1)
    assert f.max_flow(src, snk) == 2
    side = f.source_side(src)
    assert {0, 1, 2, 3, 4} <= side
    assert snk not in side


def test_lato_sorgente_esclude_le_celle_irraggiungibili():
    # L'attivita' 0 e' saturata e non risale; la cella 3 non entra nel taglio.
    f = MaxFlow(6)
    src, snk = 4, 5
    f.add_edge(src, 0, 1)
    f.add_edge(0, 2, INF)
    f.add_edge(src, 1, 2)
    f.add_edge(1, 3, INF)
    f.add_edge(2, snk, 1)
    f.add_edge(3, snk, 1)
    assert f.max_flow(src, snk) == 2
    side = f.source_side(src)
    assert 1 in side and 3 in side   # l'attivita' 1 non entra tutta
    assert 0 not in side             # l'attivita' 0 e' servita
