"""L'attività complessa: le attività con lo stesso `alignment_ident` sono
**una** collocazione (📦 XSD `Partenaire_Index`, annotazione su `Alignement`).

Il checker gemello (`domain/analysis/checkers/alignment.py`) giudica un orario
scritto e nomina le coppie in disaccordo. Qui c'è la decisione, e la decisione
è una sola per gruppo: **tutto il gruppo sulla stessa cella, o niente**.

## Perché tutto-o-niente, e non «la stessa cella se entrambe piazzate»

Perché è ciò che dice lo XSD: le attività *seront regroupés au sein d'un même
cours complexe*. Un'attività complessa si piazza o si scarta come un corpo
solo. La forma debole — «la stessa cella **se** entrambe piazzate» — sarebbe
soddisfatta anche da un gruppo in cui una metà è piazzata e l'altra scartata,
che è la stessa mezza classe abbandonata a scuola da cui nasce il debito, solo
con un nome diverso.

## Le tre situazioni, e perché nessuna produce un `INFEASIBLE` del passato

Il gruppo si legge una volta sola, non per firma di settimana: la cella è la
stessa in tutte le settimane, e l'uguaglianza fra letterali di cella non ha
firma. (Allineare due attività che non coesistono mai è una scelta del dato —
`tests/alighieri.py` lo dichiara e non lo fa — e questo builder la onora
comunque: l'attività complessa è un oggetto dell'anagrafica, non una
proprietà della settimana.)

1. **Nessun membro libero** → non si posta nulla: è un fatto, non una
   decisione (la regola dell'implicazione).
2. **I membri congelati non concordano** → il gruppo è **già** rotto, e il
   checker lo dice. Pretendere dai liberi che lo ricompongano è la metà
   vietata di ADR-018: non si posta nulla.
3. **I congelati concordano su una cella** (o non ce ne sono) → quella cella
   è l'àncora e il dominio comune si riduce a lei; senza congelati il dominio
   comune è l'**intersezione** dei domini dei liberi.

Quando il dominio comune è **vuoto** i liberi restano senza celle: il gruppo
si **scarta** invece di rendere infattibile il modello — che è la risposta
giusta e la stessa di EDT, dove l'attività complessa che non ci sta resta fra
le non piazzate. Con `allow_unplaced=False` diventa `INFEASIBLE`, ed è
corretto: quella è la domanda «questo vincolo morde?».

⚠ **Non è alleggeribile.** EDT non elenca l'allineamento fra le famiglie che
il piazzamento può allentare, e non potrebbe: alleggerirlo vorrebbe dire
scomporre l'attività complessa, cioè cambiare l'anagrafica e non un vincolo.
È strutturale come l'occupazione, e per la stessa ragione.

⚠ **Le durate diverse dentro lo stesso ident non sono vietate qui.** Lo XSD
dà all'attività complessa una durata sola, quindi il caso non dovrebbe
esistere; se esiste nel dato, l'intersezione dei domini fa già la cosa giusta
(la più lunga restringe l'inizio comune) e nessuno inventa un divieto che
l'anagrafica non dichiara."""

from collections import defaultdict

from domain.solver.registry import Builder, register


def _gruppi(ctx):
    """ident → [id], solo i gruppi con più di un membro nel modello."""
    per_ident = defaultdict(list)
    for aid, act in ctx.activities.items():
        if act.alignment_ident:
            per_ident[act.alignment_ident].append(aid)
    return {ident: sorted(membri)
            for ident, membri in sorted(per_ident.items()) if len(membri) > 1}


@register("structural:alignment")
class AlignmentBuilder(Builder):
    def build(self, ctx, model):
        for _ident, membri in _gruppi(ctx).items():
            liberi = [aid for aid in membri if aid in ctx.free]
            if not liberi:
                continue                      # un fatto, non una decisione
            ancore = {next(iter(ctx.cells[aid]))
                      for aid in membri if aid not in ctx.free}
            if len(ancore) > 1:
                continue                      # già rotto: ADR-018
            comune = set(ctx.cells[liberi[0]])
            for aid in liberi[1:]:
                comune &= ctx.cells[aid]
            if ancore:
                comune &= ancore
            for aid in liberi:
                for cella in sorted(ctx.cells[aid] - comune):
                    model.Add(ctx.x[(aid, *cella)] == 0)
            if ancore and comune:
                cella = next(iter(comune))
                for aid in liberi:
                    model.Add(ctx.x[(aid, *cella)] == 1)
                continue
            riferimento = liberi[0]
            for aid in liberi[1:]:
                for cella in sorted(comune):
                    model.Add(ctx.x[(aid, *cella)]
                              == ctx.x[(riferimento, *cella)])
