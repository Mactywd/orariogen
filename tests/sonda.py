"""La **sonda**: quali builder fanno davvero qualcosa su un dataset.

🔑 Nasce da una misura che ha corretto ciò che il progetto credeva di sé.
`CLAUDE.md` dichiarava che il Fermi esercita «sei famiglie: griglia,
indisponibilità, occupazione, sedi, D.T.B. e `room_pool`». Era un elenco, non
una misura: avvolgendo `restrict` e `build` di ogni builder durante
`build_model` i builder che toccano qualcosa sono **tre** — `occupation`,
`room_pool`, `unavailability` — e gli altri ventiquattro non fanno nulla.

⚠ **E per questo la sonda è un test e non uno script.** Il caso che prende è
«la riga c'è e il builder non la vede»: un dataset può avere righe in tutte le
tabelle e restare vuoto per il modello. Eseguita a mano una volta, il primo
builder aggiunto dopo tornerebbe silenziosamente inerte — che è esattamente
com'è nata quella riga sbagliata.

Non sostituisce la verifica per mutazione (un builder può postare un vincolo
vacuo): la **precede**, perché costa un secondo."""

import domain.solver.builders  # noqa: F401 — il registro è vuoto senza
from domain.solver import model as M
from domain.solver.registry import BUILDERS

# ⚠ L'import qui sopra non è cosmetico. `all_builders()` importa i builder
# **pigramente**, quindi leggere `BUILDERS` prima di chiamarlo dà un registro
# vuoto: la sonda contava zero e il primo test a girare falliva mentre il
# secondo passava. Lo stesso inciampo della prima stesura della sonda, il
# 2026-08-30, e il motivo per cui questo modulo esiste invece di uno script.


def _nome(builder):
    for chiave, cls in BUILDERS.items():
        if type(builder) is cls:
            return chiave
    raise AssertionError(f"builder non registrato: {type(builder)}")


class _Spia:
    """Avvolge un builder e conta ciò che toglie e ciò che posta.

    Le due fasi sono **entrambe** lavoro, e contarne una sola sottostima: un
    pre-filtro del dominio (`GridBuilder`, `UnavailabilityBuilder`) non posta
    nemmeno un constraint e toglie centinaia di celle."""

    def __init__(self, builder, conteggi):
        self._b, self._c = builder, conteggi[_nome(builder)]

    def restrict(self, ctx):
        prima = sum(len(v) for v in ctx.cells.values())
        esito = self._b.restrict(ctx)
        self._c["celle"] += prima - sum(len(v) for v in ctx.cells.values())
        return esito

    def build(self, ctx, model):
        prima = len(model.Proto().constraints)
        esito = self._b.build(ctx, model)
        self._c["constraint"] += len(model.Proto().constraints) - prima
        return esito


def misura(schedule, **kwargs):
    """`{chiave: {"celle": n, "constraint": n}}` per ogni builder del registro,
    misurato su una costruzione vera del modello di `schedule`."""
    conteggi = {chiave: {"celle": 0, "constraint": 0} for chiave in BUILDERS}
    originale = M.all_builders
    M.all_builders = lambda: [_Spia(b, conteggi) for b in originale()]
    try:
        M.build_model(schedule, **kwargs)
    finally:
        M.all_builders = originale
    return conteggi


def attivi(schedule, **kwargs):
    """Le sole chiavi che hanno fatto qualcosa. È l'insieme su cui si scrive
    l'asserzione: `== {…}` e non `>= n`, perché un builder che smette di
    lavorare va visto anche quando un altro comincia."""
    return {chiave for chiave, c in misura(schedule, **kwargs).items()
            if c["celle"] or c["constraint"]}
