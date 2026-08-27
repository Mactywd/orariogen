"""I criteri di qualità: i livelli della catena che parlano di **come** è
l'orario, non di quanto è fallito.

I quattro livelli di `objective.py` misurano tutti un fallimento — ore
scartate, attività scartate, violazioni nuove, spostamenti. Un orario che
piazza tutto senza violare nulla è indistinguibile, per quella catena, da un
altro che fa lo stesso lasciando a un docente quattro buchi al giorno. Questi
livelli li distinguono, e stanno **sotto** i quattro: la qualità cede a tutto
il resto, come già la stabilità.

🔑 **La proprietà che rende il pezzo economico**: quasi tutte queste quantità
sono già calcolate da un checker di `domain/analysis`, dove servono a essere
confrontate con un tetto. Qui la stessa quantità si **minimizza**. Dove il
checker esiste, la definizione si legge da lì e non si riscrive — la stessa
regola che vale per `B` nei rami disgiuntivi di ADR-018, e per la stessa
ragione: una divergenza di uno renderebbe il livello la misura di
qualcos'altro.

⚠ **Un criterio non cambia ciò che il modello ammette.** Posta variabili e
uguaglianze di definizione, mai un vincolo che escluda una soluzione. Ne
discende che ADR-018 non ha niente da dire su questa famiglia — ed è la prima
di cui è vero: le congelate contribuiscono termini costanti a una somma da
minimizzare, e non esiste il «pretendere una riparazione» perché non esiste
alcuna pretesa.

⚠ **Le firme di settimana: un'approssimazione dichiarata.** Queste quantità si
calcolano sull'**unione** delle settimane (`signature` omessa). Il precedente
di `MaxGapBuilder` — che trattava tutte le attività come co-attive dichiarandolo
conservativo, e non lo era — **non si applica**, e la ragione è il ruolo, non
una svista ripetuta: là l'errore stava in un vincolo hard, e un vincolo hard
sbagliato ammette orari che il checker boccia. Qui la quantità entra solo in un
`Minimize`. Un obiettivo approssimato **ordina male** orari tutti legali; non ne
ammette uno illegale. Il costo dell'alternativa è la ragione della scelta: le
firme sono una dimensione moltiplicativa (~0,3 s per firma, misurato sulla fase
5) e un anno reale ne ha 35-40."""

from domain.models import QualityCriterion, Resource

_CRITERI = {}

_POPOLAZIONI = {
    QualityCriterion.Population.TEACHERS: {Resource.Kind.TEACHER},
    QualityCriterion.Population.CLASSES: {Resource.Kind.CLASS,
                                          Resource.Kind.CLASS_PART},
}


def register(kind):
    """Un criterio è una funzione `(ctx, model, chiavi) -> (espressione, max)`.
    Restituisce l'espressione da minimizzare e il suo estremo superiore, che
    serve a dichiarare il dominio dell'`IntVar` del livello."""
    def deco(fn):
        _CRITERI[kind] = fn
        return fn
    return deco


def chiavi_di(ctx, popolazione):
    """Le chiavi di risorsa su cui il criterio conta.

    ⚠ Gli **atomi** di ADR-017 restano fuori. Non compaiono in `state.kinds`
    perché non sono risorse: sono celle del prodotto delle partizioni, cioè una
    congiunzione sintetica. Contarne i buchi significherebbe contare i buchi di
    nessuno — e comunque li conta già la parte da cui l'atomo nasce.

    ⚠ Le chiavi di **parte di classe** contano invece per conto proprio accanto
    a quelle di classe, e non è un doppio conteggio per distrazione: il
    contatore `A.iso.` di EDT è dichiarato «per docente/classe/**gruppo**»."""
    kinds = ctx.states[ctx.signatures[0][0]].kinds
    ammessi = _POPOLAZIONI.get(popolazione)
    viste = {key for aid in ctx.activities for key in ctx.tokens[aid]}
    return sorted(
        (k for k in viste
         if k in kinds and (ammessi is None or kinds[k] in ammessi)),
        key=str)


def livelli_di_qualita(ctx, model):
    """I livelli di qualità, nell'ordine dichiarato dalle righe.

    Tabella vuota ⇒ lista vuota ⇒ la catena di prima di questo pezzo, senza
    una variabile in più. È la proprietà conservativa per costruzione, e come
    per le quote è un test e non un corollario."""
    from domain.solver import criteria  # noqa: F401 — forza la registrazione

    livelli = []
    for riga in QualityCriterion.objects.all():   # Meta.ordering: rank, kind
        costruisci = _CRITERI.get(riga.kind)
        if costruisci is None:
            # Un criterio dichiarato nell'enum ma non ancora tradotto. Si
            # salta invece di fallire: l'enum è il vocabolario del prodotto,
            # e una riga che nessun builder legge è un criterio *ignorato* —
            # esattamente ciò che la lista «Criteri ignorati» di EDT esprime.
            continue
        espressione, massimo = costruisci(ctx, model, chiavi_di(ctx, riga.population))
        if massimo <= 0:
            continue   # niente da misurare su queste chiavi: nessun livello
        var = model.NewIntVar(0, massimo, f"qualita_{riga.kind}_{riga.population}")
        model.Add(var == espressione)
        livelli.append((f"{riga.kind}_{riga.population}", var))
    return livelli
