# /// script
# requires-python = ">=3.10"
# dependencies = ["ortools>=9.10"]
# ///
"""Primo test del solver: orario del Liceo Fermi con OR-Tools CP-SAT.

Modello volutamente minimo (vedi data/liceo-fermi/):
  - ogni ora del quadro orario di ogni classe va piazzata in uno slot;
  - una classe non ha due lezioni nello stesso slot;
  - un docente non è in due classi nello stesso slot.
Nessun altro vincolo (buchi, indisponibilità, aule, blocchi): serve solo a
vedere cosa produce CP-SAT sui dati grezzi.

Uso: uv run scripts/genera_orario.py
"""

from collections import defaultdict

from ortools.sat.python import cp_model

# ---------------------------------------------------------------- griglia
GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven"]
ORE = 6  # 08:00-14:00, moduli da 60'
SLOTS = [(g, h) for g in range(len(GIORNI)) for h in range(ORE)]

# ------------------------------------------------- quadro orario (classi.md)
BIENNIO = {"ITA": 4, "LAT": 3, "ING": 3, "STG": 3, "MAT": 5,
           "FIS": 2, "SCI": 2, "DIS": 2, "MOT": 2, "IRC": 1}   # 27 h
TRIENNIO = {"ITA": 4, "LAT": 3, "ING": 3, "STO": 2, "FIL": 3, "MAT": 4,
            "FIS": 3, "SCI": 3, "DIS": 2, "MOT": 2, "IRC": 1}  # 30 h

CLASSI = ["1A", "2A", "3A", "4A", "5A", "1B", "2B", "3B", "4B", "5B"]
TUTTE = CLASSI


def quadro(classe: str) -> dict[str, int]:
    return BIENNIO if classe[0] in "12" else TRIENNIO


# ------------------------- ripartizione docente -> materia -> classi
# (docenti.md, dopo la ripartizione puntuale: +/- = 0 per tutti)
CATTEDRE = {
    "ROSSI": {"ITA": ["1A", "2A", "3A"], "LAT": ["1A", "2A", "3A"]},
    "BIANC": {"ITA": ["4A", "5A"], "LAT": ["4A", "5A"]},
    "VERDI": {"ITA": ["1B", "2B", "3B"], "LAT": ["1B", "2B", "3B"]},
    "NERI":  {"ITA": ["4B", "5B"], "LAT": ["4B", "5B"]},
    "FERRA": {"ING": ["1A", "2A", "3A", "4A", "5A", "1B"]},
    "RUSSO": {"ING": ["2B", "3B", "4B", "5B"]},
    "CONTI": {"FIL": ["3A", "4A", "5A"], "STO": ["3A", "4A", "5A"], "STG": ["1A"]},
    "MARIN": {"FIL": ["3B", "4B", "5B"], "STO": ["3B", "4B", "5B"], "STG": ["1B"]},
    "GRECO": {"STG": ["2A", "2B"]},
    "COSTA": {"MAT": ["1A", "2A", "3A"], "FIS": ["1A", "2A", "3A"]},
    "GALLO": {"MAT": ["4A", "5A"], "FIS": ["4A", "5A"]},
    "LOMBA": {"MAT": ["1B", "2B", "3B"], "FIS": ["1B", "2B", "3B"]},
    "FONTA": {"MAT": ["4B", "5B"], "FIS": ["4B", "5B"]},
    "RICCI": {"SCI": ["1A", "2A", "3A", "4A", "5A", "1B", "2B"]},
    "ESPOS": {"SCI": ["3B", "4B", "5B"]},
    "BARB":  {"DIS": TUTTE},
    "VILLA": {"MOT": TUTTE},
    "PIANI": {"IRC": TUTTE},
}


def costruisci_attivita() -> list[tuple[str, str, str, int]]:
    """(docente, classe, materia, ore) — l'equivalente delle attività EDT."""
    attivita = []
    for doc, materie in CATTEDRE.items():
        for materia, classi in materie.items():
            for classe in classi:
                attivita.append((doc, classe, materia, quadro(classe)[materia]))
    return attivita


def main() -> None:
    attivita = costruisci_attivita()

    tot = sum(ore for *_, ore in attivita)
    assert tot == 288, f"quadratura rotta: {tot} ore invece di 288"
    for classe in CLASSI:
        ore_cl = sum(o for _, c, _, o in attivita if c == classe)
        assert ore_cl == sum(quadro(classe).values()), f"{classe}: {ore_cl}h"

    model = cp_model.CpModel()

    # x[(doc, classe, materia, slot)] = 1 se quell'ora è piazzata lì
    x = {}
    for doc, classe, materia, _ in attivita:
        for slot in SLOTS:
            x[doc, classe, materia, slot] = model.new_bool_var(
                f"{doc}_{classe}_{materia}_{slot[0]}_{slot[1]}")

    # 1) ogni (classe, materia) riceve esattamente il suo monte ore
    for doc, classe, materia, ore in attivita:
        model.add(sum(x[doc, classe, materia, s] for s in SLOTS) == ore)

    # 2) una classe: al più una lezione per slot
    for classe in CLASSI:
        righe = [(d, c, m) for d, c, m, _ in attivita if c == classe]
        for slot in SLOTS:
            model.add_at_most_one(x[d, c, m, slot] for d, c, m in righe)

    # 3) un docente: al più una classe per slot
    for doc in CATTEDRE:
        righe = [(d, c, m) for d, c, m, _ in attivita if d == doc]
        for slot in SLOTS:
            model.add_at_most_one(x[d, c, m, slot] for d, c, m in righe)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60
    status = solver.solve(model)

    nome_status = solver.status_name(status)
    print(f"Stato: {nome_status}  (wall time {solver.wall_time:.2f}s, "
          f"{len(x)} variabili)")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return

    # orario[classe][slot] = "MAT COSTA", orario_doc[doc][slot] = "3A MAT"
    orario = defaultdict(dict)
    orario_doc = defaultdict(dict)
    for (doc, classe, materia, slot), var in x.items():
        if solver.value(var):
            orario[classe][slot] = f"{materia} {doc}"
            orario_doc[doc][slot] = f"{classe} {materia}"

    def stampa_griglia(titolo: str, celle: dict, largh: int) -> None:
        print(f"\n### {titolo}")
        print("| Ora | " + " | ".join(GIORNI) + " |")
        print("|---|" + "---|" * len(GIORNI))
        for h in range(ORE):
            riga = [f"{8 + h}:00"]
            riga += [celle.get((g, h), "—").ljust(largh) for g in range(len(GIORNI))]
            print("| " + " | ".join(riga) + " |")

    print("\n" + "=" * 60 + "\nORARI PER CLASSE\n" + "=" * 60)
    for classe in CLASSI:
        stampa_griglia(classe, orario[classe], 9)

    print("\n" + "=" * 60 + "\nORARI PER DOCENTE\n" + "=" * 60)
    for doc in CATTEDRE:
        stampa_griglia(doc, orario_doc[doc], 6)

    # sanity check: nessun conflitto docente/classe nella soluzione
    for doc, agenda in orario_doc.items():
        assert len(agenda) == sum(
            o for d, _, _, o in attivita if d == doc), doc
    print("\nQuadratura soluzione: OK (288 ore piazzate, nessun conflitto)")


if __name__ == "__main__":
    main()
