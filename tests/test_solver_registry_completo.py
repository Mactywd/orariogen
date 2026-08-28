"""Il registro dei builder a modello completo: fissa due numeri e
un'**assenza deliberata**, cosi' che un builder aggiunto o perso si veda.

⚠ I due registri si popolano per **import**, non per scoperta: leggere
`REGISTRY` e `BUILDERS` senza importare prima `domain.analysis.checkers` e
`domain.solver.builders` restituisce cio' che altri moduli hanno gia' caricato
— quindi il verdetto dipenderebbe dall'ordine di raccolta di pytest e non dal
codice. Qui si passa apposta da `all_checkers()` e `all_builders()`, che
l'import lo fanno loro."""
import pytest

from domain.analysis.registry import REGISTRY as CHECKERS, all_checkers
from domain.solver.registry import BUILDERS, all_builders

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _registri_popolati():
    all_checkers()
    all_builders()


def test_ogni_builder_ha_un_checker_con_la_stessa_chiave():
    """«Una riga di dato, due facce»: le chiavi dei builder sono un
    sottoinsieme di quelle dei checker, mai un insieme diverso. Un builder
    orfano vorrebbe dire un vincolo che il solver impone e che l'analisi non
    sa verificare — cioe' un pezzo di modello fuori dalla portata
    dell'oracolo."""
    orfani = sorted(str(k) for k in BUILDERS if k not in CHECKERS)
    assert orfani == []


def test_structural_coverage_non_ha_un_builder_ed_e_voluto():
    """`CoverageChecker` e' `PLACEMENT_INDEPENDENT`: confronta le attivita'
    con i servizi anagrafici e non guarda mai i piazzamenti. Il solver non
    crea ne' distrugge attivita', quindi non c'e' nulla da vincolare.

    Questo test esiste perche' l'assenza sia **dichiarata** invece di
    sembrare una dimenticanza: chi aggiungesse un builder per questa chiave
    dovrebbe prima cancellare questo test, e leggerne il perche'."""
    assert "structural:coverage" in CHECKERS
    assert "structural:coverage" not in BUILDERS


def test_structural_placement_non_ha_un_builder_ed_e_voluto():
    """`PlacementChecker` nomina le attivita' scartate. La sua traduzione
    esiste — e' `somma(celle) == piazzata` — ma **non e' un builder**: crea le
    variabili di decisione stesse, quindi deve stare in `build_model`, dove
    nascono le `x`, e deve esistere **prima** che qualunque builder giri
    (`vocabulary.pos` la legge). Un builder che la postasse dopo arriverebbe
    tardi per costruzione.

    Come per `structural:coverage`, l'assenza e' dichiarata qui perche' non
    sembri una dimenticanza."""
    assert "structural:placement" in CHECKERS
    assert "structural:placement" not in BUILDERS


def test_structural_room_assignment_non_ha_un_builder_ed_e_voluto():
    """`RoomAssignmentChecker` ha una traduzione, ma vive in un **altro
    modello**: la seconda fase (`domain/solver/rooms.py`), che gira sui
    piazzamenti gia' scritti. I builder di questo registro postano sul modello
    del **piazzamento**, dove l'aula non e' ancora una decisione.

    Come per `structural:coverage` e `structural:placement`, l'assenza e'
    dichiarata qui perche' non sembri una dimenticanza."""
    assert "structural:room_assignment" in CHECKERS
    assert "structural:room_assignment" not in BUILDERS


def test_il_registro_dei_builder_e_completo():
    """Ventisei chiavi su ventinove. I numeri sono scritti qui apposta: se
    un checker nuovo entra in `domain/analysis` senza il builder
    corrispondente, questo test lo dice per nome."""
    senza_builder = {"structural:coverage", "structural:placement",
                     "structural:room_assignment"}
    mancanti = sorted(str(k) for k in CHECKERS
                      if k not in BUILDERS and k not in senza_builder)
    assert mancanti == []
    assert len(CHECKERS) == 29
    assert len(BUILDERS) == 26
