"""Il picco d'occupazione del gruppo di aule, dentro il modello del
piazzamento (ADR-021).

La fase 1 non **assegna** le aule — resta la seconda fase, che e' la forma del
prodotto e di EDT. Le **conta**: che tre attivita' scelgano ognuna fra le
stesse due aule e' un fatto noto prima di piazzare, e ignorarlo lascia alla
fase 2 una sola risposta possibile, la rinuncia, perche' §6 della sua spec
dichiara fuori scope il ritorno indietro.

🔑 **Il vincolo e' sano per costruzione.** Vieta esattamente le configurazioni
che *nessuna* assegnazione d'aula potrebbe servire — il principio dei
cassetti — quindi non toglie mai al piazzamento un orario che la fase 2
saprebbe completare. Non e' un'euristica con un prezzo: e' una condizione
necessaria che prima non veniva posta.

## Quali insiemi si postano

Il tetto vale per un insieme S di aule: le attivita' le cui candidate stanno
**tutte** dentro S non possono superare i posti di S. Gli S che contano sono
le **unioni** degli insiemi di candidate dichiarati — un violatore di Hall
stretto e' sempre di quella forma, perche' restringere S all'unione delle
candidate del gruppo colpevole non perde nessuna attivita' e non guadagna
nessun posto.

⚠ La chiusura per unione e' esponenziale nel numero di insiemi **distinti**,
non nel numero di aule ne' di attivita': una scuola ne ha uno per materia che
chiede un laboratorio, cioe' pochi (sul Fermi: quattro, chiusura quindici).
Oltre `TETTO_POOL` la chiusura si tronca e restano gli insiemi dichiarati, che
sono i violatori piu' probabili — sul Fermi il colpevole misurato,
`{LAB-FIS, LAB-INF}`, e' un insieme dichiarato. La troncatura **non rende il
modello sbagliato**: toglie tetti, quindi ammette di piu', e cio' che passa
lo nomina `structural:room_pool`.

⚠ Gli insiemi di **una sola** aula non si postano: quell'aula e' gia' una
chiave di occupazione (`activity_tokens` la mette fra i token a candidata
unica) e `OccupationBuilder` posta lo stesso tetto. Postarlo due volte
gonfierebbe il modello senza cambiarne le soluzioni."""

from collections import defaultdict

from domain.solver.registry import Builder, register
from domain.solver.residual import residual_cap

TETTO_POOL = 256


def _candidati(ctx):
    """id → insieme di aule fra cui l'attivita' puo' finire.

    Le **dichiarate**, come nel checker: `assigned_room` e' una ripartizione
    rivedibile e la fase 2 la tratta da preferenza. Un'assegnazione senza
    candidate dichiarate e' invece un fatto, e consuma."""
    base = ctx.states[ctx.signatures[0][0]]
    fuori = {}
    for aid, act in ctx.activities.items():
        rooms = {r.pk for r in act.rooms.all()}
        if not rooms:
            assegnata = base.assigned_room.get(aid)
            if assegnata is None:
                continue
            rooms = {assegnata}
        fuori[aid] = frozenset(rooms)
    return fuori


def _pools(dichiarati):
    """La chiusura per unione degli insiemi dichiarati, troncata a
    `TETTO_POOL`. Deterministica: la frontiera si visita ordinata."""
    distinti = sorted(set(dichiarati), key=lambda s: (len(s), sorted(s)))
    pools, frontiera = set(distinti), list(distinti)
    while frontiera and len(pools) < TETTO_POOL:
        nuovi = []
        for a in frontiera:
            for b in distinti:
                u = a | b
                if u not in pools:
                    pools.add(u)
                    nuovi.append(u)
                    if len(pools) >= TETTO_POOL:
                        return sorted(pools, key=lambda s: (len(s), sorted(s)))
        frontiera = sorted(nuovi, key=lambda s: (len(s), sorted(s)))
    return sorted(pools, key=lambda s: (len(s), sorted(s)))


def _chiusa(ctx, state, room_id, day, slot):
    """L'aula e' chiusa in quella cella? Rossa sempre, gialla se nessuno ha
    autorizzato a scavalcarla per la **categoria** di risorsa (A4)."""
    livello = state.unavailability.get((room_id, day, slot))
    if livello == "hard":
        return True
    return (livello == "optional"
            and state.kinds.get(room_id) not in ctx.ignora_opzionali)


@register("structural:room_pool")
class RoomPoolBuilder(Builder):
    def build(self, ctx, model):
        candidati = _candidati(ctx)
        if not candidati:
            return
        pools = [p for p in _pools(candidati.values()) if len(p) > 1]
        if not pools:
            return

        # (giorno, fascia) → [(id, letterale)]: i letterali di avvio che fanno
        # occupare quella cella. Al piu' uno di essi vale 1, quindi la loro
        # somma **e'** l'indicatore «occupa» — la stessa algebra di
        # `SolverContext.index_cells`, qui su una chiave che non e' un token.
        per_cella = defaultdict(list)
        for aid, insieme in candidati.items():
            durata = ctx.activities[aid].duration_slots
            for (day, start) in ctx.cells[aid]:
                lit = ctx.x[(aid, day, start)]
                for slot in range(start, start + durata):
                    per_cella[(day, slot)].append((aid, lit))

        posted = set()
        for rep, _ in ctx.signatures:
            state = ctx.states[rep]
            attive = state.activities
            for (day, slot), voci in sorted(per_cella.items()):
                qui = [(aid, lit) for aid, lit in voci if aid in attive]
                if not qui:
                    continue
                for pool in pools:
                    self._posta(ctx, model, state, posted, pool, day, slot, qui,
                                candidati)

    @staticmethod
    def _posta(ctx, model, state, posted, pool, day, slot, qui, candidati):
        dentro = [(aid, lit) for aid, lit in qui if candidati[aid] <= pool]
        if not dentro:
            return
        ids = {aid for aid, _lit in dentro}
        if not any(aid in ctx.free for aid in ids):
            return          # un fatto, non una decisione
        # 🔑 **Il giallo chiude il posto come il rosso** (L6bis, 2026-08-31).
        # Qui c'era il contrario — «l'opzionale e' violabile per definizione» —
        # e costava una rinuncia: la fase 2 (`RoomsContext._filtra`) l'aula
        # gialla la toglie dalle candidate, quindi contarne i posti qui
        # significava promettere alla fase 2 un'aula che non potra' usare.
        # Stessa regola del checker, cosi' che l'oracolo differenziale
        # confronti due letture identiche.
        #
        # L'autorizzazione a scavalcare il giallo esiste ed e' per **tipo** di
        # risorsa (A4), non per la singola: `ignora_opzionali`, la stessa che
        # legge `UnavailabilityBuilder._ignorata`. Con quella accesa il posto
        # torna a contare, coerentemente con cio' che fara' la fase 2 se la si
        # lancia con lo stesso override.
        capienza = sum(0 if _chiusa(ctx, state, r, day, slot)
                       else state.capacity.get(r, 1)
                       for r in pool)
        if len(ids) <= capienza:
            return          # non potrebbe superarla nemmeno tutte insieme
        firma = (pool, day, slot, frozenset(ids))
        if firma in posted:
            return          # firme di settimana diverse, stesso constraint
        posted.add(firma)
        # ADR-018: il tetto e' il residuo, clampato a zero. Tre congelate su
        # due aule sono un orario illegale che il checker nomina; pretendere
        # dalle libere che lo riparino sarebbe la meta' vietata.
        liberi, residuo = residual_cap(
            ctx, [(1, aid, lit) for aid, lit in dentro], capienza)
        model.Add(sum(lit for _peso, lit in liberi) <= residuo)
