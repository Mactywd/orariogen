# tests/test_solver_witness.py
"""Il banco di prova. Il test di copertura e' quello che tiene: registrare un
builder senza il suo derivatore diventa impossibile, invece di dipendere dalla
diligenza di chi lo scrive."""
import pytest

from domain.solver import builders  # noqa: F401 — forza la registrazione
from domain.solver.registry import BUILDERS
from tests.solver_harness import (
    DERIVERS, build_witness, run_family, run_tutte_le_famiglie,
)

pytestmark = pytest.mark.django_db

SEEDS = [1, 2, 3, 4, 5]


def test_ogni_builder_ha_un_derivatore():
    mancanti = sorted(str(k) for k in BUILDERS if k not in DERIVERS)
    assert mancanti == [], (
        "questi builder non hanno un banco di prova: " + ", ".join(mancanti))


def test_il_testimone_ha_piu_di_una_firma_di_settimana():
    """Se questa proprieta' si perdesse, ogni test del banco tornerebbe cieco
    sulla dimensione «settimane» — che e' esattamente il modo in cui il
    difetto del D.T.B. e' passato inosservato."""
    w = build_witness(seed=1)
    assert len(w.signatures) >= 2


@pytest.mark.parametrize("seed", SEEDS)
def test_le_parti_entrano_nel_testimone(seed):
    """Le parti di classe non sono solo *create* dalla fixture: hanno
    attivita' proprie, con token che contengono la parte e **non** la classe.
    E' la forma che il filtro sul solo `klass.pk` perdeva — la generalizzazione
    dei derivatori (`_chiavi_unita`) non avrebbe nulla da generalizzare se
    questa proprieta' si perdesse."""
    w = build_witness(seed)
    parti = {p.pk for p in w.env["parts"]}
    classi = {k.pk for k in w.env["classes"]}
    solo_parte = [aid for aid in w.placement
                  if (w.tokens[aid] & parti) and not (w.tokens[aid] & classi)]
    assert len(solo_parte) == len(w.env["parts"]) == 2
    # e sono davvero su parti diverse: una per parte, non due sulla stessa
    assert {frozenset(w.tokens[aid] & parti) for aid in solo_parte} == {
        frozenset({p.pk}) for p in w.env["parts"]}


# Nessuno dei cinque seed del banco esibisce due attivita' di parti diverse
# nella **stessa** cella: misurato 0/5 (e 4/80 sui primi ottanta semi — 22,
# 28, 31, 53). Non e' un fallimento, e' la frequenza del fenomeno: le
# attivita' di parte sono due, e le celle libere per loro sono molte. Il
# seme qui sotto e' il primo che lo esibisce, e serve a tenere la proprieta'
# di ADR-017 sotto test invece che sotto statistica.
SEME_STESSA_CELLA = 22


def test_due_parti_della_stessa_partizione_condividono_una_cella():
    """La proprieta' di ADR-017 che nessun banco di prova esercitava: due
    parti della **stessa** partizione sono disgiunte, quindi le loro attivita'
    non condividono nessuna chiave di occupazione e possono partire nella
    stessa cella, nella stessa settimana. Il testimone lo esibisce, quindi
    ogni derivatore che ragiona su «quante ne stanno» o su «sono simultanee»
    e' costretto a reggerlo."""
    w = build_witness(SEME_STESSA_CELLA)
    parti = {p.pk for p in w.env["parts"]}
    classi = {k.pk for k in w.env["classes"]}
    solo_parte = [aid for aid in w.placement
                  if (w.tokens[aid] & parti) and not (w.tokens[aid] & classi)]
    a, b = solo_parte
    assert w.placement[a] == w.placement[b], (
        "il seme di riferimento non esibisce piu' due attivita' di parte "
        "nella stessa cella: rimisurare e sceglierne un altro")
    assert not (w.tokens[a] & w.tokens[b]), (
        "condividono una chiave di occupazione: allora non sono simultanee "
        "per ADR-017, sono un conflitto che _try_place non avrebbe dovuto "
        "produrre")
    assert set(w.weeks_of[a]) & set(w.weeks_of[b]), (
        "stessa cella ma settimane disgiunte: non e' simultaneita', e' solo "
        "riuso della cella in settimane diverse")


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("key", sorted(DERIVERS, key=str))
def test_famiglia(key, seed):
    run_family(key, seed)


@pytest.mark.parametrize("seed", SEEDS)
def test_modello_completo(seed):
    """⚠ Il test che mancava: **tutte le famiglie insieme**, non una per volta.

    `test_famiglia` prova ventisei modelli da una famiglia ciascuno. Nessuno di
    quei test — e nemmeno l'oracolo del Fermi, che di righe di vincolo non ne
    ha nessuna — verifica che i ventisei builder convivano: che due traduzioni
    corrette separatamente non si contraddicano una volta postate insieme.

    Il testimone regge la congiunzione per costruzione, perche' ogni riga e'
    derivata dal fatto che *lui* la soddisfa. Quindi INFEASIBLE qui e' un
    fallimento duro come in `run_family`, e vale su tutte e ventisei le
    famiglie in un colpo solo.

    ⚠ L'ordine dei derivatori conta: vedi `MUTANTI` in `solver_harness`. Se
    qualcuno lo rompe, l'assert sul testimone sporco lo dice per nome."""
    w, soluzione, poteri = run_tutte_le_famiglie(seed)
    vive = [k for k, v in poteri.items() if v]
    assert len(vive) >= 20, (
        f"solo {len(vive)} famiglie portano righe al seed {seed}: la misura "
        f"del modello completo si sta svuotando")
    print(f"\nmodello completo, seed {seed}: {len(vive)}/26 famiglie, "
          f"{sum(poteri.values())} righe, {soluzione.status} "
          f"{soluzione.stats}")
