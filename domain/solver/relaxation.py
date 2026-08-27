"""Gli alleggerimenti a quota: un vincolo rilassabile **non diventa soft**.

Istruzione letterale del prodotto: *«Sbloccate i vincoli da alleggerire e
selezionateli per quantificare il margine di manovra concesso al calcolo»*.
Non esiste «spegni il vincolo»: resta hard, con un numero massimo di violazioni
attribuito per famiglia e per risorsa. Nel modello CP-SAT questo si esprime con
**variabili di violazione vincolate in somma**, mai con penalità
nell'obiettivo — e la differenza è sostanziale, non estetica.

Due forme, perché le righe della finestra `Alleggerimenti` sono di due tipi:

- il **margine**, dove il vincolo si allarga di una quantità dichiarata
  («Autorizza un supplemento di 1 ora, una volta per settimana e per
  docente») → `expr <= tetto + margine · v`;
- la **deroga**, dove il vincolo semplicemente non si considera per
  quell'occorrenza («Non considerare le incompatibilità … una sola volta al
  giorno») → la clausola si posta sotto `OnlyEnforceIf(v.Not())`.

In entrambe, `v` è un letterale di violazione che **consuma quota**: la somma
dei `v` di una (famiglia, risorsa) sta sotto `max_violations`, e la somma di
tutti i `v` di una risorsa sotto il tetto globale d'istituto.

⚠ Un vincolo alleggerito resta una **violazione nominata**: `check_schedule`
continua a produrre il suo finding `HARD`. È il comportamento di EDT, dove
l'orario risolto conteneva 21 attività su 984 che non rispettavano i vincoli e
il prodotto continuava a lavorare. La quota non nasconde la violazione:
autorizza il solver a produrla, e in numero limitato.

⚠ Senza righe `RelaxationQuota` questo modulo non crea **niente**: nessun
letterale, nessun constraint. È la proprietà «quote a zero ⇒ il modello di
prima», ed è un test, non un corollario."""

from collections import defaultdict

from domain.models import InstituteSettings, RelaxationQuota


class Relaxation:
    def __init__(self, quote, tetto_globale):
        self._quote = quote                  # (famiglia, risorsa|None) → riga
        self._tetto_globale = tetto_globale
        self._letterali = defaultdict(list)  # (famiglia, risorsa) → [BoolVar]

    @classmethod
    def build(cls):
        quote = {}
        for riga in RelaxationQuota.objects.all():
            quote[(riga.family, riga.resource_id)] = riga
        settings = InstituteSettings.objects.filter(pk=1).first()
        tetto = settings.max_relaxed_constraints_per_resource if settings else None
        return cls(quote, tetto)

    def _riga(self, famiglia, risorsa):
        """La riga più specifica: quella della risorsa, altrimenti la generica.
        Una quota a zero equivale a non averla — è il modo di scrivere «questo
        vincolo non si alleggerisce» senza cancellare la riga."""
        riga = self._quote.get((famiglia, risorsa)) or self._quote.get((famiglia, None))
        if riga is None or not riga.max_violations:
            return None
        return riga

    def deroga(self, model, famiglia, risorsa, tag):
        """Il letterale di violazione di **una** occorrenza del vincolo, o
        `None` se quella famiglia non è alleggerita su quella risorsa. Il
        chiamante posta il proprio vincolo sotto `OnlyEnforceIf(v.Not())`."""
        if self._riga(famiglia, risorsa) is None:
            return None
        var = model.NewBoolVar(f"deroga_{famiglia}_{risorsa}_{tag}")
        self._letterali[(famiglia, risorsa)].append(var)
        return var

    def margine(self, model, famiglia, risorsa, tag):
        """Il termine da **sommare** al tetto (o da sottrarre alla soglia) per
        una occorrenza: `margine · v`, oppure `0` se non c'è quota. Restituisce
        un intero quando non c'è nulla da aggiungere, così il chiamante scrive
        sempre `expr <= tetto + termine` senza rami."""
        riga = self._riga(famiglia, risorsa)
        if riga is None:
            return 0
        quanto = int(riga.params.get("margine", 0))
        if quanto <= 0:
            # ⚠ Una riga senza margine dichiarato **non** si trasforma in
            # deroga implicita: sarebbe un vincolo spento per distrazione, che
            # è esattamente ciò che EDT non fa mai.
            return 0
        var = model.NewBoolVar(f"margine_{famiglia}_{risorsa}_{tag}")
        self._letterali[(famiglia, risorsa)].append(var)
        return quanto * var

    def post_caps(self, model):
        """Le quote, postate una volta sola alla fine: nessun builder le
        conosce, ognuno chiede solo il proprio letterale."""
        per_risorsa = defaultdict(list)
        for (famiglia, risorsa), letterali in sorted(
                self._letterali.items(), key=lambda kv: (str(kv[0][0]), kv[0][1] or 0)):
            riga = self._riga(famiglia, risorsa)
            model.Add(sum(letterali) <= riga.max_violations)
            per_risorsa[risorsa].extend(letterali)
        if self._tetto_globale is None:
            return
        for risorsa, letterali in sorted(per_risorsa.items(), key=lambda kv: kv[0] or 0):
            model.Add(sum(letterali) <= self._tetto_globale)
