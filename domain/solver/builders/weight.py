"""Il peso didattico (ADR-011): `Totale = Peso x Durata`, contato per **unita'
studente** e non per classe — il caso _REL/_ALT verificato sui dati.

Tre dettagli, tutti presi da `domain/analysis/checkers/weight.py`, che e'
l'autorita':

- il peso di un'attivita' e' `subject.didactic_weight * duration_slots`, una
  **costante nota a build time**: nessuna variabile intera, solo coefficienti
  su letterali booleani;
- le unita' su cui pesa sono le **parti** presenti nei token, oppure la classe
  se la classe non ha partizioni (`_student_keys`). ⚠ **Non** tutti i token:
  docenti, aule e materiali non c'entrano, e un builder che sommasse su tutti
  vincolerebbe cose che il checker non guarda;
- il tetto **settimanale della classe** prevale su quello d'istituto
  (`class_caps[part_class[key]]`), e si ricade su `settings.max_weight_week`
  solo quando e' `None`. ⚠ Ogni tetto `None` e' **spento**, non zero.

⚠ **In una base reale del prodotto i quattro tetti d'istituto sono tutti a
«nessuno»** (osservato in EDT, changelog del 2026-07-26 sera): questo builder
di norma **non posta nulla**. Il silenzio e' il comportamento corretto, non un
difetto da cercare quando il conteggio dei constraint non cambia.

**Il verso delle firme di settimana.** Qui si aggrega su una risorsa lungo la
settimana, quindi il ciclo per firma c'e'; ma la direzione dell'errore e'
l'opposto di quella del D.T.B. Questo e' un **tetto**: piu' letterali nella
somma significano un vincolo piu' stretto, mai piu' lasco, quindi fondere le
settimane sarebbe **conservativo** (si perderebbe qualche soluzione legale,
mai se ne ammetterebbero di illegali) — come in
`domain/analysis/checkers/subject_constraints.py`, e al contrario di
`MaxGapBuilder`, dove il buco e' `ultima - prima + 1 - conteggio` e un
letterale di un'altra settimana **allarga**. Il ciclo per firma resta perche'
e' piu' preciso ed e' la regola della casa (vedi `builders/base.py`), non
perche' senza sarebbe sbagliato.

**ADR-018, e ⚠ i due secchi non si comportano allo stesso modo.** La somma e'
separabile — ogni letterale porta i propri punti di peso — quindi il residuo
si ottiene sottraendo il consumo delle congelate. Ma il clamp a zero e'
sufficiente solo per i secchi **evadibili**:

- **giornata e mezza giornata sono evadibili**: un'attivita' libera che non
  entra nel secchio saturo va altrove, e il residuo a zero lo rende
  *inagibile*. Vietare un peggioramento, che ADR-018 concede — anche quando
  per una libera senza alternative il divieto produce INFEASIBLE (Ruling 80,
  stessa proprieta' di `ForbiddenSequenceBuilder`);
- **la settimana e' inevadibile**: il secchio contiene *tutte* le celle
  candidate di ogni attivita' dell'unita', quindi `AddExactlyOne` rende la
  somma dei letterali liberi una **costante**. Il vincolo e' vero sempre o
  falso sempre, e con il residuo clampato a zero sarebbe falso sempre: non
  un divieto, ma la pretesa che il passato venga riparato — il caso che
  ADR-018 esclude. Misurato: due congelate da 2 punti con tetto settimanale
  3 piu' una libera davano INFEASIBLE. Percio' il tetto settimanale **non si
  posta** quando le congelate da sole lo sforano gia'.

⚠ Quando invece a sforare e' il totale (congelate **piu'** libere, o nessuna
congelata affatto) il vincolo si posta e il modello e' INFEASIBLE: li' il
passato non e' il colpevole, l'istanza semplicemente non ha soluzione, e
tacere restituirebbe un orario che `check_schedule` boccia.

⚠ **Un limite che nessun builder puo' togliere**, dichiarato: nel caso saltato
qui sopra la soluzione restituita porta comunque il finding `weight_week`, e
la sua `Finding.key` **non** e' quella di prima — `activities` cresce delle
libere e `quantities["weight"]` cambia. Per un vincolo indipendente dal
piazzamento non esiste alternativa: le libere vanno collocate, e ovunque
vadano pesano. L'oracolo differenziale a tutto campo lo incontrera'; e' fra i
punti aperti in `CLAUDE.md`.
"""

from collections import defaultdict

from domain.analysis.state import resource_sort_key
from domain.models import RelaxationQuota
from domain.models.resources import Resource
from domain.solver.registry import Builder, register
from domain.solver.residual import split


def _student_keys(kinds, tokens):
    """Le unita'-studente di un'attivita', con la stessa regola di
    `domain/analysis/checkers/weight.py::_student_keys`: le parti nei token,
    o la classe se la classe non ha partizioni."""
    parts = [k for k in tokens if kinds.get(k) == Resource.Kind.CLASS_PART]
    if parts:
        return sorted(parts, key=resource_sort_key)
    return sorted((k for k in tokens if kinds.get(k) == Resource.Kind.CLASS),
                  key=resource_sort_key)


@register("structural:didactic_weight")
class DidacticWeightBuilder(Builder):
    def build(self, ctx, model):
        v = ctx.vocab
        posted = set()
        for rep, _ in ctx.signatures:
            state = ctx.states[rep]
            s = state.settings
            per_day, per_half, per_week = (defaultdict(list), defaultdict(list),
                                           defaultdict(list))
            for aid in sorted(ctx.activities):
                if aid not in state.activities:
                    continue
                act = ctx.activities[aid]
                peso = act.subject.didactic_weight * act.duration_slots
                keys = _student_keys(state.kinds, ctx.tokens[aid])
                if not keys:
                    continue   # nessuna unita'-studente: il checker la ignora
                for (day, slot) in sorted(ctx.cells[aid]):
                    # ⚠ la fascia di **partenza** decide giorno e meta'
                    # giornata, esattamente come il checker che legge
                    # `pl.start_slot`: un'attivita' a cavallo del mezzogiorno
                    # pesa tutta sulla meta' in cui comincia.
                    lit = ctx.x[(aid, day, slot)]
                    meta = v.half_of(slot)
                    for key in keys:
                        # La stessa attivita' mette **piu' letterali** nello
                        # stesso secchio, uno per cella candidata li' dentro.
                        # E' corretto: `somma(celle) == piazzata` limita a 1 la
                        # somma dei suoi letterali, quindi il peso entra nella
                        # somma **al piu'** una volta — zero se l'attivita' e'
                        # scartata (stessa osservazione di `post_separable`).
                        per_day[(key, day)].append((peso, aid, lit))
                        per_half[(key, day, meta)].append((peso, aid, lit))
                        per_week[key].append((peso, aid, lit))

            def posta(bucket, terms, cap, evadibile=True):
                if cap is None:
                    return   # tetto spento, non tetto a zero
                firma = (bucket, frozenset(aid for _p, aid, _l in terms), cap)
                if firma in posted:
                    return   # firme di settimana diverse, stesso constraint
                posted.add(firma)
                liberi, consumo = split(ctx, terms)
                if not liberi:
                    return
                if not evadibile and consumo > cap:
                    # ⚠ ADR-018 sul secchio settimanale sforato **dalle sole
                    # congelate**. L'argomento originale era che la somma dei
                    # letterali liberi fosse una costante — ogni libera pesa
                    # ovunque vada — e che il clamp a zero rendesse quindi il
                    # secchio contraddittorio invece che inagibile. ⚠ Quella
                    # costante era `AddExactlyOne`: dal 2026-08-26 il
                    # piazzamento non e' piu' obbligatorio e la somma torna a
                    # dipendere dalle decisioni. Il clamp non e' piu'
                    # contraddittorio, ma preteso ora significa **scartare** le
                    # libere per espiare il peso del passato — un peggioramento
                    # imposto al presente da uno stato che non ha scelto, che
                    # e' la stessa cosa che ADR-018 esclude. Si salta.
                    return
                margine = ctx.relax.margine(
                    model, RelaxationQuota.Family.DIDACTIC_WEIGHT,
                    bucket[1], f"{bucket}")
                model.Add(sum(p * lit for p, lit in liberi)
                          <= max(0, cap - consumo) + margine)

            def ordina(secchi):
                # ordine deterministico su chiavi miste int/str (ADR-017: gli
                # atomi sono stringhe — qui non compaiono, perche' non sono
                # ne' CLASS ne' CLASS_PART, ma la funzione resta quella)
                return sorted(secchi, key=lambda b: (resource_sort_key(b[0]),
                                                     b[1:]))

            for (key, day) in ordina(per_day):
                posta(("day", key, day), per_day[(key, day)], s.max_weight_day)
            for (key, day, meta) in ordina(per_half):
                cap = s.max_weight_morning if meta == 0 else s.max_weight_afternoon
                posta(("half", key, day, meta), per_half[(key, day, meta)], cap)
            for key in sorted(per_week, key=resource_sort_key):
                # ⚠ il tetto della classe prevale su quello d'istituto, e si
                # trova passando dalla parte alla sua classe (`part_class`).
                cap = state.class_caps.get(state.part_class.get(key, key))
                if cap is None:
                    cap = s.max_weight_week
                posta(("week", key), per_week[key], cap, evadibile=False)
