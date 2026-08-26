"""ADR-018 — l'input sporco non blocca il solver.

Un'attivita' congelata ha ctx.cells[aid] di cardinalita' uno e riceve comunque
AddExactlyOne: il suo letterale vale 1, ed e' noto al momento della
costruzione. Quindi ogni espressione lineare del modello si spezza
**esattamente** in «parte costante + parte libera», e da li' discendono due
casi soli.

Sui **tetti**: `costante + libere <= tetto` equivale a
`libere <= tetto - costante`, e quel residuo puo' essere negativo — e' il caso
in cui le congelate sono gia' in violazione. ADR-018 impone di clamparlo a
zero invece di lasciare il modello infattibile per colpa del passato.

Sui **minimi garantiti**: `costante + libere >= soglia` equivale a
`libere >= soglia - costante`, che non e' mai infattibile per colpa del
passato — se le congelate gia' bastano, il requisito e' vacuo. Nessun clamp."""


def split(ctx, terms):
    """terms: iterabile di (peso, id attivita', letterale).
    → (termini liberi come (peso, letterale), consumo delle congelate)."""
    free, frozen = [], 0
    for weight, aid, lit in terms:
        if aid in ctx.free:
            free.append((weight, lit))
        else:
            frozen += weight
    return free, frozen


def residual_cap(ctx, terms, cap):
    """Per un vincolo «<= cap». Il tetto residuo e' clampato a zero."""
    free, frozen = split(ctx, terms)
    return free, max(0, cap - frozen)


def residual_floor(ctx, terms, floor):
    """Per un vincolo «>= floor». Nessun clamp: una soglia residua <= 0
    significa che le congelate gia' bastano, ed e' corretto che il vincolo
    risulti vacuo."""
    free, frozen = split(ctx, terms)
    return free, floor - frozen


def any_free(ctx, activity_ids):
    """La regola dell'implicazione: un vincolo i cui letterali vengono tutti da
    attivita' congelate non si posta — e' un fatto, non una decisione."""
    return any(aid in ctx.free for aid in activity_ids)


def frozen_occupies(ctx, key, day, slots, rep=None):
    """Un'attivita' **congelata** occupa quella chiave in una di quelle fasce?

    Serve alle cardinalita' su **variabili derivate** (day_active,
    half_active), dove il contributo delle congelate non e' separabile come
    termine: se una congelata forza la variabile a 1, quella variabile e' una
    costante e va nel consumo; se nessuna la tocca, dipende solo da letterali
    liberi e resta un termine della somma."""
    active = None if rep is None else ctx.states[rep].activities
    for slot in slots:
        for aid, _lit in ctx.by_cell.get((key, day, slot), ()):
            if aid not in ctx.free and (active is None or aid in active):
                return True
    return False
