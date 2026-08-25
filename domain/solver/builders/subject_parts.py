"""I quattro `PARTS_*`: l'ordine, dentro uno stesso secchio, fra le ore di
**parte** e le ore a **classe intera** della stessa materia.

Autorita': `_PartsOrder` e le sue quattro sottoclassi in
`domain/analysis/checkers/subject_constraints.py` (righe 230-283). Il checker
raggruppa per secchio, ordina le occorrenze piazzate per
`(fascia, etichetta, id)`, salta i secchi che non contengono **entrambe** le
etichette, e poi:

    if self.MODE == "before":
        bad = max(s for s, l, _ in entries if l == "part") > min(
            s for s, l, _ in entries if l == "class")
    elif self.MODE == "after":
        bad = min(s for s, l, _ in entries if l == "part") < max(
            s for s, l, _ in entries if l == "class")
    else:  # homogeneous: nessuna interlacciatura
        transitions = sum(x != y for x, y in zip(labels, labels[1:]))
        bad = transitions > 1

⚠ **Il secchio dei due omogenei non e' lo stesso.** `_PartsOrder.bucket`
torna `pl.day`, ma `PartsHomogeneousHalfChecker` lo **sovrascrive** con
`_half`. Quindi `_H` = mezza giornata e `_AB` = giornata: e' l'unica
differenza fra i due, ed e' silenziosa se la si inverte.

⚠ **`_PartsOrder.violations` usa solo `a`**, mai `b`. La materia B non entra
in nessuno dei quattro tipi, nemmeno quando la riga ha A != B. Vale qui la
stessa nota di `_MaxHoursSubject` (subject_buckets.py): il gate di
`SubjectBuilder.build` e la deduplicazione per `coinvolte` guardano l'unione
di A e B (Ruling 60), quindi al piu' una riga si posta due volte identica,
mai una firma si salta.

## L'etichetta e' una proprieta' dell'attivita', non del piazzamento

`_is_class_level` guarda se **qualcuna** delle chiavi di occupazione
dell'attivita' e' una Resource di tipo CLASS. Non dipende dalla cella, quindi
si calcola una volta a build time.

## La traduzione e' **esatta**, e la dimostrazione sta nelle coppie

Per un secchio fissato, sia `P` l'insieme delle celle candidate delle
attivita' di parte e `C` quello delle celle candidate delle attivita' di
classe (della materia A, sull'unita' della riga, attive in questa firma).

- **before**: la violazione e' `max(fasce di parte) > min(fasce di classe)`,
  cioe' «esiste una coppia con `sp > sc`». Vietare **ogni** coppia con
  `sp > sc` (`AddBoolOr([xp.Not(), xc.Not()])`) equivale quindi esattamente
  alla negazione della violazione. Non e' conservativo: e' un se-e-solo-se.
- **after**: simmetrico, la violazione e' «esiste una coppia con `sp < sc`».
- **homogeneous**: «al piu' una transizione» nella sequenza ordinata delle
  etichette significa che la sequenza e' `P…PC…C` **oppure** `C…CP…P` —
  cioe' tutte le parti prima di tutte le classi, oppure il contrario. E'
  la disgiunzione che il booleano `prima_le_parti` per secchio esprime: le
  coppie che smentiscono il primo ramo vanno sotto `OnlyEnforceIf(b)`,
  quelle che smentiscono il secondo sotto `OnlyEnforceIf(b.Not())`.

⚠ **Il pareggio di fascia fra una parte e una classe, e perche' qui non serve
assumerlo impossibile.** Il brief di questo task dava per non realizzabile il
caso `sp == sc` (un'attivita' a classe intera occupa la classe **e tutte le
sue parti**, quindi confliggerebbe sull'occupazione con un'attivita' di
parte), e ne faceva la ragione dell'esattezza del ramo omogeneo. La premessa
pero' **non regge in generale**: l'etichetta «classe» si guadagna con una
qualunque chiave CLASS, non con la classe *della riga*. Un'attivita' con
`classes = [X]` e `parts = [p]` con `p` di un'altra classe entra
nell'unita' di `p` etichettata «classe» senza occupare le altre parti di
quella classe; lo stesso vale per una riga su un **raggruppamento**
trasversale, dove le parti membre appartengono a classi diverse (ADR-013).
In quei casi il pareggio e' realizzabile.

Non serve assumerlo, perche' l'esattezza si ottiene dal **criterio di
ordinamento del checker stesso**: `entries.sort()` ordina tuple
`(fascia, etichetta, id)` e la stringa `"class"` precede `"part"`. Quindi a
parita' di fascia la classe viene **prima**, e i due rami hanno strettezze
diverse:

    parti-prima  ⟺  per ogni coppia:  sp <  sc   (il pareggio rompe il ramo)
    classi-prima ⟺  per ogni coppia:  sc <= sp   (il pareggio lo rispetta)

Con questa asimmetria i due insiemi di coppie sono **complementari** (`sp >=
sc` contro `sp < sc`): ogni coppia finisce in esattamente un ramo, e la
traduzione coincide col checker anche sui pareggi. Verificato sui tre casi
che discriminano: `{C@2, P@2}` legale (sequenza `C,P`, una transizione);
`{P@1, C@2, P@2}` illegale (sequenza `P,C,P`, due transizioni); `{P@1, C@2}`
legale.

Per **before** e **after** il pareggio non e' mai in discussione: le due
disuguaglianze del checker sono gia' strette, e le coppie in pareggio non
vanno vietate in nessuno dei due modi.

## ADR-018 — l'input sporco non blocca il solver

Il trattamento sta **sul secchio**, non sulla coppia, e per la stessa
ragione per cui ci sta nel resto della famiglia di materia: il finding di
questo checker porta fra le `activities` **tutte** le occorrenze del secchio
(`[aid for _, _, aid in entries]`), e `activities` sta dentro
`Finding.key`. Quindi in un secchio **gia' violato dalle sole congelate**
qualunque aggiunta libera produce un finding *nuovo* — non lo stesso gia'
scritto nella baseline. E' identico al quarto ramo di `post_cross` e al
clamp a zero di `residual_cap` (subject_buckets.py, residual.py), e si
risolve allo stesso modo:

- **secchio gia' violato dalle sole congelate** → si azzerano uno per uno i
  letterali **liberi** di quel secchio (parti e classi insieme: entrambe le
  etichette entrano nella tupla del finding) e non si posta nessun vincolo
  d'ordine. ⚠ Puo' rendere il modello INFEASIBLE se una libera non ha
  altrove dove andare: e' un **divieto**, ed e' testualmente cio' che
  ADR-018 concede.
- **secchio pulito dalle congelate** → si posta la traduzione per intero,
  **comprese le coppie in cui entrambe le attivita' sono congelate**.

Quel «comprese» e' il punto delicato, e va contro il trattamento che il
brief proponeva (saltare le coppie tutte-congelate con `any_free`):

- per **before**/**after** saltarle sarebbe innocuo ma **morto**: se le
  congelate del secchio sono pulite, allora per before `max(fasce di parte
  congelate) <= min(fasce di classe congelate)`, quindi *nessuna* coppia
  tutta-congelata soddisfa la condizione `sp > sc` e nessuna clausola
  tutta-congelata verrebbe mai generata. La guardia non scatterebbe mai;
  postarla sarebbe codice che non difende niente.
- per **homogeneous** saltarle sarebbe **sbagliato**. Le clausole
  tutte-congelate sono cio' che **ancora** il booleano al verso che il
  passato ha gia' scelto. Esempio: congelate `P@1` e `C@2` (parti prima),
  secchio pulito; una libera di classe a `C@0` creerebbe la sequenza
  `C,P,C`, due transizioni, violazione **nuova**. Se la coppia
  tutta-congelata `(P@1, C@2)` non fosse postata, il ramo «classi prima»
  resterebbe soddisfacibile e il solver potrebbe sceglierlo, ammettendo
  quel piazzamento. Postandola, quella coppia (`sp=1 < sc=2`) forza
  `prima_le_parti = 1` e il ramo sbagliato cade.

E non c'e' rischio di INFEASIBLE «per colpa del passato» nel ramo omogeneo:
se le congelate del secchio sono pulite, la loro sequenza ha al piu' una
transizione, quindi e' `P…PC…C` o `C…CP…P` e **almeno uno dei due rami e'
soddisfatto da tutte le coppie tutte-congelate**. Il booleano resta
scegliibile; i piazzamenti liberi si dispongono attorno.

⚠ Con **una sola** delle due congelate la clausola resta e forza a zero il
letterale libero: e' di nuovo un divieto, concesso da ADR-018 anche quando
rende il modello INFEASIBLE (stessa proprieta' gia' scritta per
`ForbiddenSequenceBuilder`).
"""

from collections import defaultdict

from domain.models import Resource, SubjectConstraint
from domain.solver.builders.base import SubjectBuilder
from domain.solver.registry import register

T = SubjectConstraint.Type

PARTE, CLASSE = 1, 0   # l'ordinamento del checker: "class" < "part"


def _viola(mode, voci):
    """Mirror di `_PartsOrder.violations` su un solo secchio.

    `voci`: iterabile di `(fascia, etichetta)` con `etichetta` in
    {`CLASSE`, `PARTE`}. La codifica numerica 0/1 riproduce l'ordinamento
    del checker, che ordina la stringa `"class"` prima di `"part"`."""
    voci = sorted(voci)
    parti = [s for s, lab in voci if lab == PARTE]
    classi = [s for s, lab in voci if lab == CLASSE]
    if not parti or not classi:
        return False          # il checker salta i secchi senza entrambe
    if mode == "before":
        return max(parti) > min(classi)
    if mode == "after":
        return min(parti) < max(classi)
    etichette = [lab for _, lab in voci]
    return sum(x != y for x, y in zip(etichette, etichette[1:])) > 1


class _PartsOrderBuilder(SubjectBuilder):
    """Lo scheletro comune ai quattro: cambiano solo `TYPE`, `KIND` e `MODE`.

    L'assert su `KIND` sta all'ingresso di `post()`, l'unico punto che tutte
    e quattro le sottoclassi attraversano (stesso motivo per cui in
    `_Bucketed` sta dentro `buckets()`, Ruling 67): `vocab.bucket_of` tratta
    **ogni** `kind != "day"` come mezza giornata, quindi una sottoclasse che
    dimenticasse `KIND` prenderebbe silenziosamente la semantica "half"
    invece di rompersi. Stessa rete per `MODE`, dove l'errore sarebbe ancora
    piu' muto: `_viola` cadrebbe nel ramo `else`, cioe' nell'omogeneo."""

    KIND = None   # "day" | "half"
    MODE = None   # "before" | "after" | "homogeneous"

    def post(self, ctx, model, row, keys, rep):
        assert self.KIND in ("day", "half"), type(self).__name__
        assert self.MODE in ("before", "after", "homogeneous"), type(self).__name__
        v = ctx.vocab
        kinds = ctx.states[rep].kinds
        aids = v.subject_activities(keys, row.subject_a_id, signature=rep)
        if not aids:
            return
        etichetta = {
            aid: (CLASSE if any(kinds.get(k) == Resource.Kind.CLASS
                                for k in ctx.tokens[aid]) else PARTE)
            for aid in aids
        }
        # secchio → {CLASSE: [...], PARTE: [...]} di (id attivita', fascia,
        # letterale). Si passa dalle celle e non da `vocab.subject_literals`
        # perche' qui serve la **fascia** di ogni letterale, che l'indice
        # memoizzato non restituisce; l'insieme delle attivita' resta pero'
        # quello di `subject_activities`, cioe' la stessa regola di
        # appartenenza che `subject_literals` usa al suo interno.
        secchi = defaultdict(lambda: {CLASSE: [], PARTE: []})
        for aid in aids:
            lato = etichetta[aid]
            for (day, slot) in sorted(ctx.cells[aid]):
                bucket = v.bucket_of(self.KIND, day, slot)
                secchi[bucket][lato].append((aid, slot, ctx.x[(aid, day, slot)]))

        for bucket in sorted(secchi):
            parti = secchi[bucket][PARTE]
            classi = secchi[bucket][CLASSE]
            if not parti or not classi:
                # Nessun piazzamento puo' dare a questo secchio entrambe le
                # etichette, quindi il checker lo salterebbe sempre: tutti i
                # vincoli sarebbero vacui. Stessa giustificazione — esattezza,
                # non risparmio — della guardia `if not la or not lb` di
                # `post_cross`.
                continue
            congelate = [(slot, lato)
                         for lato, voci in ((PARTE, parti), (CLASSE, classi))
                         for aid, slot, _ in voci if aid not in ctx.free]
            if _viola(self.MODE, congelate):
                # ADR-018: il secchio e' gia' violato dalle sole congelate.
                # Ogni aggiunta libera allunga la tupla `activities` del
                # finding, cioe' e' un finding *nuovo*: si vieta il secchio
                # alle libere invece di pretendere che riparino il passato.
                for aid, _slot, lit in parti + classi:
                    if aid in ctx.free:
                        model.Add(lit == 0)
                continue
            self._posta(model, row, rep, bucket, parti, classi)

    def _posta(self, model, row, rep, bucket, parti, classi):
        omogeneo = self.MODE == "homogeneous"
        prima_le_parti = (
            model.NewBoolVar(f"partsorder_{row.pk}_{rep}_{bucket}")
            if omogeneo else None)
        for _pid, sp, xp in parti:
            for _cid, sc, xc in classi:
                if omogeneo:
                    # I due rami sono complementari: `sp >= sc` smentisce
                    # «parti prima» (che a parita' di fascia e' rotto, perche'
                    # il checker ordina la classe per prima), `sp < sc`
                    # smentisce «classi prima». Ogni coppia finisce in
                    # esattamente uno dei due.
                    ramo = (prima_le_parti if sp >= sc
                            else prima_le_parti.Not())
                    model.AddBoolOr([xp.Not(), xc.Not()]).OnlyEnforceIf(ramo)
                    continue
                vietata = sp > sc if self.MODE == "before" else sp < sc
                if vietata:
                    model.AddBoolOr([xp.Not(), xc.Not()])


@register(T.PARTS_BEFORE_CLASS)
class PartsBeforeBuilder(_PartsOrderBuilder):
    TYPE, KIND, MODE = T.PARTS_BEFORE_CLASS, "day", "before"


@register(T.PARTS_AFTER_CLASS)
class PartsAfterBuilder(_PartsOrderBuilder):
    TYPE, KIND, MODE = T.PARTS_AFTER_CLASS, "day", "after"


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_H)
class PartsHomogeneousHalfBuilder(_PartsOrderBuilder):
    """⚠ `_H` e' la **mezza giornata**: `PartsHomogeneousHalfChecker`
    sovrascrive `bucket()` con `_half`, mentre la base torna `pl.day`."""
    TYPE, KIND, MODE = T.PARTS_BEFORE_OR_AFTER_CLASS_H, "half", "homogeneous"


@register(T.PARTS_BEFORE_OR_AFTER_CLASS_AB)
class PartsHomogeneousDayBuilder(_PartsOrderBuilder):
    """⚠ `_AB` e' la **giornata**: eredita il `bucket()` della base."""
    TYPE, KIND, MODE = T.PARTS_BEFORE_OR_AFTER_CLASS_AB, "day", "homogeneous"
