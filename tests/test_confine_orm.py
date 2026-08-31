"""Il confine dell'ORM: dove il dominio può interrogare il database, e dove no.

**Perché esiste questo file.** ADR-031. Il progetto non ha un pacchetto senza
Django come `api/intake/` di Classi Prime, e ha deciso di non averlo: il nucleo
del calcolo era **già** senza query prima di questo file — tutti e ventotto i
builder e tredici file di checker su quattordici, e il quattordicesimo è stato
chiuso insieme a questo test — e ce l'ha per via del *pezzo di dati* che si passa
(`ScheduleState`, `SolverContext`), non per via di una riga di import. Ma una
proprietà che nessuno asserisce non è una proprietà: è una coincidenza che dura
finché qualcuno non scrive la riga sbagliata.

E la misura dice che succede. Al 2026-08-31, mattina, i siti di query fuori da
`domain/models/` erano **77** e la spec del confine li contò uno per uno. La sera
dello stesso giorno erano **116**, cresciuti di metà in una giornata di lavoro
ordinario — L12 (`bootstrap.py`) e L13 (`questionario.py`) — e **nessuno se ne era
accorto**, perché non c'era niente che guardasse.

**Le due asserzioni non sono la stessa cosa, ed è apposta.**

1. `test_il_nucleo_non_interroga` è una **regola**: builder e checker stanno a
   zero. Non un inventario da aggiornare — un numero che deve restare zero.
2. `test_l_inventario_del_confine` è un **cricchetto**, nella forma di
   `tests/sonda.py`: l'insieme dei punti di contatto, asserito come *insieme* e
   non come numero, perché da qui non deve più salire ma restare fermo. Un sito
   nuovo rompe il test e chiede di essere dichiarato con il suo ruolo; un sito
   tolto lo rompe ugualmente, ed è giusto — un inventario che si aggiorna da solo
   verso il basso smette di dire quanto è costato arrivarci.

⚠ **Il test non sa se il ruolo dichiarato è vero.** Sa che il punto è dichiarato.
La differenza fra un caricatore e una query dentro un ciclo la vede solo chi
legge il codice — ed è precisamente la differenza che L11 ha misurato: `_placeable`
interrogava a ogni chiamata, e `analyze_capacity()` costava **1206** query dove
ora ne costa 20.
"""

import ast
import io
import os

# I quattro ruoli. «Caricatore» non vuol dire *può interrogare*: vuol dire
# **interroga una volta, prima del calcolo, e il calcolo lavora sul risultato**.
CARICATORE = "caricatore"   # legge una volta in un'istantanea
INGRESSO = "ingresso"       # la via d'ingresso dei dati (ADR-028)
COMANDO = "comando"         # riga di comando; diventerà una rotta (ADR-027)
USCITA = "uscita"           # scrive o rende il risultato

CONFINE = {
    ("domain/analysis/blame.py", "rank_constraints"): CARICATORE,
    ("domain/analysis/capacity.py", "_leggi"): CARICATORE,
    ("domain/analysis/capacity.py", "_week_groups"): CARICATORE,
    ("domain/analysis/capacity.py", "analyze_capacity"): CARICATORE,
    ("domain/analysis/conformity.py", "week_signatures"): CARICATORE,
    ("domain/analysis/hall.py", "analyze_hall"): CARICATORE,
    ("domain/analysis/state.py", "AtomMap.build"): CARICATORE,
    ("domain/analysis/state.py", "ScheduleState.build"): CARICATORE,
    ("domain/bootstrap.py", "applica"): INGRESSO,
    ("domain/extraction.py", "_appartenenze"): CARICATORE,
    ("domain/extraction.py", "carica"): CARICATORE,
    ("domain/extraction.py", "nella_fascia"): CARICATORE,
    ("domain/extraction.py", "per_materia"): CARICATORE,
    ("domain/extraction.py", "per_stato"): CARICATORE,
    ("domain/extraction.py", "salva"): USCITA,
    ("domain/ical.py", "_labels"): CARICATORE,
    ("domain/ical.py", "occorrenze"): CARICATORE,
    ("domain/ical.py", "render"): CARICATORE,
    ("domain/management/commands/analyze.py", "Command.handle"): COMANDO,
    ("domain/management/commands/assign_rooms.py", "Command.handle"): COMANDO,
    ("domain/management/commands/export_ical.py", "Command.handle"): COMANDO,
    ("domain/management/commands/extract.py", "Command._elenca"): COMANDO,
    ("domain/management/commands/extract.py", "Command._stampa"): COMANDO,
    ("domain/management/commands/extract.py", "Command.handle"): COMANDO,
    ("domain/management/commands/place_and_fix.py", "Command.handle"): COMANDO,
    ("domain/management/commands/solve.py", "Command.handle"): COMANDO,
    # ⚠ `<modulo>`: le lambda del catalogo delle domande, valutate al momento
    # della domanda e non all'import. È l'unico contatto a livello di modulo.
    ("domain/questionario.py", "<modulo>"): INGRESSO,
    ("domain/questionario.py", "_giorni"): INGRESSO,
    ("domain/questionario.py", "_segnaposto"): INGRESSO,
    ("domain/questionario.py", "_tetti_messi"): INGRESSO,
    ("domain/questionario.py", "chiudi"): INGRESSO,
    ("domain/questionario.py", "questionario"): INGRESSO,
    ("domain/questionario.py", "riapri"): INGRESSO,
    ("domain/solver/model.py", "apply"): USCITA,
    ("domain/solver/place_and_fix.py", "_fuori_dal_modello"): CARICATORE,
    ("domain/solver/quality.py", "livelli_di_qualita"): CARICATORE,
    ("domain/solver/relaxation.py", "Relaxation.build"): CARICATORE,
    ("domain/solver/rooms.py", "RoomContext.build"): CARICATORE,
    ("domain/solver/rooms.py", "apply_rooms"): USCITA,
}

# Il nucleo del calcolo: qui la regola è **zero**, non un elenco.
NUCLEO = ("domain/solver/builders/", "domain/analysis/checkers/")


def _siti():
    """Ogni `.objects` fuori da `domain/models/`, con la funzione che lo
    contiene. L'AST e non `grep`: una riga può portarne due (le lambda del
    questionario ne portano davvero due), e una query spezzata su più righe
    ne porta una sola."""
    fuori = []
    for root, _dirs, files in os.walk("domain"):
        if "/models" in root or "migrations" in root or "__pycache__" in root:
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            percorso = os.path.join(root, f)
            albero = ast.parse(io.open(percorso, encoding="utf-8").read())
            proprietario = {}

            def visita(nodo, prefisso):
                for figlio in ast.iter_child_nodes(nodo):
                    if isinstance(figlio, ast.ClassDef):
                        visita(figlio, figlio.name + ".")
                    elif isinstance(figlio, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nome = prefisso + figlio.name
                        for sotto in ast.walk(figlio):
                            if hasattr(sotto, "lineno"):
                                proprietario.setdefault(sotto.lineno, nome)
                        visita(figlio, nome + ".")
                    else:
                        visita(figlio, prefisso)

            visita(albero, "")
            for nodo in ast.walk(albero):
                if isinstance(nodo, ast.Attribute) and nodo.attr == "objects":
                    fuori.append((percorso,
                                  proprietario.get(nodo.lineno, "<modulo>")))
    return fuori


def test_il_nucleo_non_interroga():
    """I ventotto builder e i checker lavorano su `SolverContext` e
    `ScheduleState`, mai sul database. È la purezza che Classi Prime compra con
    un confine di pacchetto, ottenuta per un'altra strada — e questa riga è ciò
    che la rende una regola invece di un'abitudine."""
    colpevoli = sorted({(p, f) for p, f in _siti() if p.startswith(NUCLEO)})
    assert colpevoli == [], (
        "Un builder o un checker interroga il database. Il dato che serve va "
        "caricato una volta nel contesto o nello stato, non chiesto durante il "
        "calcolo: qui stavano le tre copie dell'espansione dell'unità che L11 "
        f"ha unificato in `state.subject_row_unit_keys`. Trovati: {colpevoli}")


def test_l_inventario_del_confine():
    """Il cricchetto. Un sito nuovo va **dichiarato**, con il suo ruolo."""
    visti = {(p, f) for p, f in _siti()}
    dichiarati = set(CONFINE)
    nuovi = sorted(visti - dichiarati)
    spariti = sorted(dichiarati - visti)
    assert not nuovi, (
        "Punti di contatto con l'ORM non dichiarati. Se è un caricatore, "
        "aggiungilo a CONFINE con il suo ruolo; se è una query dentro un ciclo "
        f"del calcolo, spostala al caricamento. Nuovi: {nuovi}")
    assert not spariti, (
        "Punti dichiarati che non esistono più: bene, ma vanno tolti da "
        f"CONFINE, o l'inventario smette di dire il vero. Spariti: {spariti}")


def test_l_espansione_dell_unita_e_una_sola():
    """L10 aveva trovato una tabella che poteva dire il falso; qui c'era una
    **frase** scritta tre volte — in `state`, nel checker, e per riflesso in
    `capacity`, che importava il privato del checker. Tre implementazioni della
    stessa regola sono tre occasioni di divergere."""
    testo = io.open("domain/analysis/checkers/subject_constraints.py",
                    encoding="utf-8").read()
    assert "_unit_keys" not in testo and "_unit_resources" not in testo
    testo_capacity = io.open("domain/analysis/capacity.py", encoding="utf-8").read()
    assert "from domain.analysis.checkers" not in testo_capacity, (
        "`capacity` importava un helper privato di un checker: è la stessa "
        "duplicazione, presa dall'altro capo.")
