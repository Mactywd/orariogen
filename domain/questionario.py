"""Il **questionario d'ingresso**: cosa resta da chiedere, e in che ordine.

È il **gradino 3** di ADR-028. I primi due leggono l'orario dell'anno scorso —
`bootstrap.ricava` ne cava docenti, classi, materie, fasce, cattedre e i
sospetti di sdoppiamento. Questo modulo prende ciò che resta e lo rende una
**conversazione finita**: nominabile, contabile, e che a un certo punto
finisce.

🔑 **Un questionario non è l'elenco delle tabelle vuote, e la differenza è la
ragione per cui esiste `SetupQuestion`.** Una scuola senza vincoli di materia e
una scuola a cui nessuno li ha ancora chiesti hanno le stesse zero righe. Se
«aperta» volesse dire «vuota», il dialogo non potrebbe terminare: ogni famiglia
legittimamente vuota resterebbe aperta per sempre, e un questionario che non
finisce nessuno lo compila. Una domanda si chiude perché qualcuno la chiude.

🔑 **I tre effetti sono la stessa disciplina di `CECITA`**: si dichiara *in che
modo* si è ciechi, non solo che lo si è. `MUTO` è la categoria che conta —
senza risposta il calcolo produce un orario **sbagliato e nessuno lo dice**:
piazza un docente quando non c'è, lo manda fra due sedi in fasce consecutive,
occupa un giorno di vacanza. `ASSENTE` è il caso onesto: un pezzo dichiarato
non si fa, e si vede (senza aule `assign_rooms` rinuncia, e lo scrive).
`FUORI_CALCOLO` è la domanda che non tocca il solve — si fa lo stesso, ma per
il gestionale.

🔑 **L'ordine lo decide la dipendenza, non l'effetto.** `indisponibilita` è
`MUTO` e `aule` è solo `ASSENTE`, eppure le aule vengono prima: non si può dire
*quando un'aula è occupata* prima di dire *quali aule ci sono*. La gravità
ordina ciò che è ugualmente possibile; la possibilità viene prima della
gravità.

⚠ **`tocca` è misurato, non dichiarato.** Sono i builder che quella risposta fa
lavorare, e li tiene fermi un test di **ablazione** sull'Alighieri
(`tests/test_questionario_ablazione.py`): si tolgono le righe della famiglia e
si ripassa la sonda. È lo stesso mestiere del cricchetto di `tests/sonda.py`,
e nasce dallo stesso inciampo — un elenco scritto a mano che nessuno rimisura
invecchia senza dirlo.

⚠ **E la sonda ha un punto cieco dichiarato**: misura `build_model`, cioè il
modello **duro**. Le quote di alleggerimento e i criteri di qualità vivono
*sopra* di esso — sono livelli della catena lessicografica, costruiti uno alla
volta — quindi l'ablazione le misura a zero, e zero lì non vuol dire *inerte*.
Le due voci portano `oltre_il_modello_duro`, e il test asserisce lo zero
insieme al motivo.

⚠ **Una domanda che si chiude presto perde il suo perimetro.** Il perimetro si
calcola sullo stato di adesso: chiudere `indisponibilita` prima di aver
inserito le aule chiude una domanda che allora riguardava soltanto docenti e
classi. È il prezzo dell'ordine per dipendenza, ed è scritto qui perché sia una
scelta e non una sorpresa.
"""

from dataclasses import dataclass

from domain.bootstrap import DISCIPLINA_DA_ASSEGNARE
from domain.models import (Break, ClassPartition, Discipline, Holiday,
                           InstituteSettings, Material, Period,
                           QualityCriterion, RelaxationQuota,
                           ResourceTimeConstraint, ResourceUnavailability,
                           Room, SchoolClass, Service, SetupQuestion, Site,
                           StaffMember, Subject, SubjectConstraint, Teacher,
                           TimeGrid)

#: I tre modi di essere senza risposta. Non è una scala di importanza: è la
#: differenza fra un errore che tace e un pezzo che manca.
MUTO = "muto"
ASSENTE = "assente"
FUORI_CALCOLO = "fuori_calcolo"

_GRAVITA = {MUTO: 0, ASSENTE: 1, FUORI_CALCOLO: 2}


@dataclass(frozen=True)
class Questione:
    """Una domanda da fare alla scuola, con il suo prezzo e il suo effetto."""

    chiave: str
    domanda: str
    effetto: str
    senza: str
    #: I builder che questa risposta fa lavorare — **misurati** per ablazione.
    tocca: tuple = ()
    #: Le domande che vanno fatte prima, perché questa parla dei loro oggetti.
    dipende_da: tuple = ()
    #: La sonda non arriva: la risposta vive sopra il modello duro.
    oltre_il_modello_duro: bool = False
    #: `((descrizione, quanti), …)` — su cosa spazia la risposta, contato
    #: sullo stato di adesso. Vuoto = non si ricava da nessun dato che abbiamo:
    #: è un inventario, e va chiesto e basta.
    perimetro: tuple = ()
    righe: int = 0
    chiusa: bool = False

    @property
    def aperta(self):
        """⚠ Le righe **non** chiudono da sole, ed è il punto del modulo. Ma
        righe senza chiusura sono comunque una risposta cominciata, e il
        comando le distingue."""
        return not self.chiusa


#: Il catalogo. L'ordine in cui si legge lo decide `_ordina`, non questa lista.
#: `perimetro` e `righe` sono funzioni perché si rileggono ogni volta: un
#: questionario è una fotografia dello stato, non un documento.
_CATALOGO = (
    dict(
        chiave="sedi",
        domanda="La scuola ha più di una sede? Quali, e quante fasce serve per "
                "spostarsi fra due di esse?",
        effetto=MUTO,
        senza="il calcolo manda lo stesso docente da una sede all'altra in due "
              "fasce consecutive, e nessuno lo dice: senza sedi non c'è "
              "distanza da violare.",
        tocca=("max_site_changes", "structural:site_transition"),
        perimetro=lambda: (),
        righe=lambda: Site.objects.count(),
    ),
    dict(
        chiave="aule",
        domanda="Quali aule ci sono, di che capienza, e quali attività le "
                "richiedono?",
        effetto=ASSENTE,
        senza="la fase 2 non ha niente da assegnare e **rinuncia dichiarandolo**: "
              "l'orario esce senza aule, non sbagliato.",
        tocca=("structural:occupation", "structural:room_pool",
               "structural:unavailability"),
        dipende_da=("sedi",),
        perimetro=lambda: (),
        righe=lambda: Room.objects.count(),
    ),
    dict(
        chiave="materiali_e_personale",
        domanda="Ci sono carrelli, laboratori mobili o personale tecnico che "
                "un'attività deve avere per potersi tenere?",
        effetto=ASSENTE,
        senza="due attività che si contendono l'unico carrello finiscono nella "
              "stessa fascia. È **assente** e non **muto** solo perché la "
              "risorsa non esiste: non c'è niente che il calcolo stia "
              "ignorando.",
        tocca=("structural:occupation", "structural:site_transition"),
        dipende_da=("sedi",),
        perimetro=lambda: (),
        righe=lambda: Material.objects.count() + StaffMember.objects.count(),
    ),
    dict(
        chiave="partizioni",
        domanda="Nelle classi che si sdoppiano, chi sta in quale metà?",
        effetto=MUTO,
        senza="il quadro orario della classe sdoppiata resta **gonfiato** — le "
              "ore delle due metà si sommano invece di sovrapporsi — e un "
              "quadro gonfiato produce un `INFEASIBLE` che non nomina nessuno.",
        # Le partizioni non hanno un builder proprio: entrano dalle chiavi di
        # occupazione (ADR-017). ⚠ E non sono ablabili come le altre — le
        # cattedre puntano alle parti — quindi qui `tocca` è **dichiarato**, e
        # il test lo dice invece di misurarlo come gli altri.
        # ⚠ Quella ragione era scritta in anticipo: fino ad ADR-030 **nessuna**
        # cattedra puntava a una parte, ed erano le sole attività a scenderci.
        # Da allora sono 30 su 144, e la riga qui sopra è diventata vera.
        tocca=(),
        # ⚠ Il perimetro sono le classi, e non i **sospetti**, che sarebbero la
        # risposta utile: `ricava` li trova (la stessa classe due volte nella
        # stessa fascia) e `manage.py bootstrap` li stampa, ma `applica` non li
        # scrive — una partizione senza gli alunni dentro non è una riga che si
        # possa mettere. Chi vuole l'elenco rilegge la griglia. È una cucitura
        # dichiarata, non una dimenticanza.
        perimetro=lambda: (("classi", SchoolClass.objects.count()),),
        righe=lambda: ClassPartition.objects.count(),
    ),
    dict(
        chiave="calendario",
        domanda="Quali sono le festività, gli intervalli e i periodi "
                "dell'anno?",
        effetto=MUTO,
        senza="la griglia conta giorni in cui la scuola è chiusa, e ci piazza "
              "lezioni.",
        tocca=("structural:grid",),
        # ⚠ Il perimetro è quello degli **intervalli** — una riga per fascia del
        # ciclo, al più. Festività e periodi sono date, e da nessun dato che
        # abbiamo si ricava quante siano.
        perimetro=lambda: (("giorni del ciclo", _giorni()),),
        righe=lambda: (Holiday.objects.count() + Break.objects.count()
                       + Period.objects.count()),
    ),
    dict(
        chiave="indisponibilita",
        domanda="Quando ogni docente, classe e aula **non** è disponibile — "
                "rosso, giallo o verde?",
        effetto=MUTO,
        senza="il calcolo piazza un docente in una fascia in cui non c'è. È il "
              "caso peggiore del questionario: l'orario è formalmente valido e "
              "praticamente inservibile.",
        tocca=("structural:unavailability",),
        dipende_da=("aule",),
        perimetro=lambda: (("docenti", Teacher.objects.count()),
                           ("classi", SchoolClass.objects.count()),
                           ("aule", Room.objects.count())),
        righe=lambda: ResourceUnavailability.objects.count(),
    ),
    dict(
        chiave="vincoli_orari",
        domanda="Per ogni docente e ogni classe: massimo di ore, di presenza, "
                "di mezze giornate, giorni liberi garantiti, entrate e uscite, "
                "distribuzione minima, buchi tollerati, cambi di sede.",
        effetto=MUTO,
        senza="le regole contrattuali e didattiche non esistono per il "
              "calcolo, che le viola tutte senza saperlo.",
        tocca=("arrival_departure", "free_guaranteed", "max_gap_hours",
               "max_half_days", "max_hours", "max_presence",
               "max_site_changes", "min_distribution"),
        dipende_da=("sedi",),
        perimetro=lambda: (("docenti", Teacher.objects.count()),
                           ("classi", SchoolClass.objects.count()),
                           ("famiglie", len(ResourceTimeConstraint.Type.choices))),
        righe=lambda: ResourceTimeConstraint.objects.count(),
    ),
    dict(
        chiave="vincoli_materia",
        domanda="Quali materie non stanno bene insieme, in che ordine vanno, e "
                "quante ore al giorno se ne possono fare?",
        effetto=MUTO,
        senza="l'orario mette quattro ore di matematica di fila, o "
              "l'educazione fisica prima del pranzo, e li considera corretti.",
        tocca=("forbidden_sequence", "half_day_gap", "imposed_succession",
               "max_hours_day", "max_hours_half_day", "parts_after_class",
               "parts_before_class", "parts_before_or_after_class_ab",
               "parts_before_or_after_class_h", "same_day_incompatible",
               "same_half_day_incompatible", "two_days_incompatible",
               "weekly_order"),
        perimetro=lambda: (("righe di quadro orario", Service.objects.count()),
                           ("tipi", len(SubjectConstraint.Type.choices))),
        righe=lambda: SubjectConstraint.objects.count(),
    ),
    dict(
        chiave="peso_didattico",
        domanda="Quanto pesa ogni materia, e qual è il tetto per mattina, "
                "pomeriggio, giornata e settimana?",
        effetto=ASSENTE,
        senza="nessun tetto esiste, quindi nessuno si viola. Il peso di "
              "default è 1 e i quattro tetti sono `nessuno`, che è anche il "
              "default d'istituto di EDT.",
        tocca=("structural:didactic_weight",),
        perimetro=lambda: (("materie", Subject.objects.count()),
                           ("tetti d'istituto", len(_TETTI))),
        # ⚠ La risposta ha **due metà** — i pesi delle materie e i tetti
        # d'istituto — e contarne una sola direbbe «nessuna riga» a una scuola
        # che ha messo i tetti e lasciato i pesi al default.
        righe=lambda: (Subject.objects.exclude(didactic_weight=1).count()
                       + _tetti_messi()),
    ),
    dict(
        chiave="criteri_di_qualita",
        domanda="Cosa conta di più in un orario buono, e in che ordine — e per "
                "quale popolazione, docenti o classi?",
        effetto=ASSENTE,
        senza="la catena si ferma al modello duro: l'orario è **ammissibile** e "
              "non **ottimizzato**, che è lo stato in cui EDT lascia un orario "
              "appena piazzato.",
        oltre_il_modello_duro=True,
        perimetro=lambda: (("criteri disponibili", len(QualityCriterion.Kind.choices)),),
        righe=lambda: QualityCriterion.objects.count(),
    ),
    dict(
        chiave="quote",
        domanda="Quali vincoli si possono alleggerire se l'orario non si chiude, "
                "di quanto e quante volte?",
        effetto=ASSENTE,
        senza="un orario che non si chiude resta con delle attività "
              "**scartate** invece che con un vincolo allentato, e le scartate "
              "il modello le nomina.",
        oltre_il_modello_duro=True,
        dipende_da=("vincoli_orari", "vincoli_materia"),
        # ⚠ Meno due: `UNAVAILABILITY` e `OPTIONAL_UNAVAILABILITY` stanno
        # nell'enum ma non sono quote (il rosso non si alleggerisce mai, il
        # giallo si ignora con un'opzione di calcolo). Contarle qui darebbe
        # alla scuola due domande che nessun builder legge.
        perimetro=lambda: (("famiglie alleggeribili",
                            len(RelaxationQuota.Family.choices) - 2),),
        righe=lambda: RelaxationQuota.objects.count(),
    ),
    dict(
        chiave="discipline",
        domanda="A quale disciplina e a quale classe di concorso appartiene "
                "ogni materia?",
        effetto=FUORI_CALCOLO,
        senza="il calcolo è **identico** — misurato: zero builder, zero celle, "
              "zero constraint. Ma il gestionale ragiona per classe di concorso "
              "quando cerca un supplente (ADR-001, ADR-002), e senza non sa a "
              "chi chiedere.",
        perimetro=lambda: (("materie", Subject.objects.count()),
                           ("materie ancora su una disciplina segnaposto",
                            _segnaposto()),),
        righe=lambda: Discipline.objects.count(),
    ),
)

#: Il codice che `bootstrap.applica` inventa quando l'orario non dice a quale
#: disciplina appartiene una materia — cioè sempre. Si legge da lì e non si
#: ricopia: due costanti che devono coincidere prima o poi non coincidono.
SEGNAPOSTO = (DISCIPLINA_DA_ASSEGNARE[0],)


#: I quattro tetti di peso didattico d'istituto (la finestra `Pesi` di EDT).
_TETTI = ("max_weight_morning", "max_weight_afternoon", "max_weight_day",
          "max_weight_week")


def _tetti_messi():
    riga = InstituteSettings.objects.filter(pk=1).first()
    if riga is None:
        return 0
    return sum(1 for c in _TETTI if getattr(riga, c) is not None)


def _segnaposto():
    return Subject.objects.filter(discipline__code__in=SEGNAPOSTO).count()


def _giorni():
    griglia = TimeGrid.objects.first()
    return griglia.days_per_cycle if griglia else 0


def _ordina(voci):
    """Topologico sulle dipendenze, gravità come spareggio.

    ⚠ Il verso è quello dichiarato in testa al modulo: la **possibilità** viene
    prima della gravità, perché una domanda sugli oggetti di un'altra non si sa
    nemmeno formulare finché quella non ha risposta."""
    chiavi = {v["chiave"] for v in voci}
    ignote = {d for v in voci for d in v.get("dipende_da", ())} - chiavi
    if ignote:
        raise ValueError(f"dipendenze da domande che non esistono: {sorted(ignote)}")
    fatte, out = set(), []
    rimaste = list(voci)
    while rimaste:
        pronte = [v for v in rimaste
                  if all(d in fatte for d in v.get("dipende_da", ()))]
        if not pronte:
            raise ValueError(f"ciclo fra {[v['chiave'] for v in rimaste]}")
        pronte.sort(key=lambda v: (_GRAVITA[v["effetto"]], v["chiave"]))
        scelta = pronte[0]
        out.append(scelta)
        fatte.add(scelta["chiave"])
        rimaste = [v for v in rimaste if v["chiave"] != scelta["chiave"]]
    return out


def questionario():
    """Tutte le domande, nell'ordine in cui vanno fatte, con lo stato di
    adesso. È una fotografia: nulla è memorizzato tranne le chiusure."""
    chiuse = set(SetupQuestion.objects.values_list("key", flat=True))
    fuori = chiuse - {v["chiave"] for v in _CATALOGO}
    if fuori:
        raise ValueError(f"chiusure per domande che non esistono: {sorted(fuori)}")
    out = []
    for voce in _ordina(list(_CATALOGO)):
        v = dict(voce)
        out.append(Questione(
            chiave=v["chiave"], domanda=v["domanda"], effetto=v["effetto"],
            senza=v["senza"], tocca=tuple(v.get("tocca", ())),
            dipende_da=tuple(v.get("dipende_da", ())),
            oltre_il_modello_duro=v.get("oltre_il_modello_duro", False),
            perimetro=tuple(v["perimetro"]()), righe=v["righe"](),
            chiusa=v["chiave"] in chiuse,
        ))
    return tuple(out)


def aperte():
    """Le sole domande ancora da fare."""
    return tuple(q for q in questionario() if q.aperta)


def chiudi(chiave, note=""):
    """Chiude una domanda: qualcuno l'ha posta e ha ricevuto una risposta —
    **anche se la risposta era «niente»**, che è tutto il motivo per cui questa
    funzione esiste."""
    if chiave not in {v["chiave"] for v in _CATALOGO}:
        raise ValueError(f"domanda sconosciuta: {chiave}")
    riga, creata = SetupQuestion.objects.get_or_create(
        key=chiave, defaults={"note": note})
    if not creata and note:
        riga.note = note
        riga.save(update_fields=["note"])
    return riga


def riapri(chiave):
    """Riapre una domanda chiusa. Esiste perché una chiusura senza ritorno
    sarebbe una trappola: chi chiude per sbaglio non avrebbe nessun modo di
    dirlo, e il questionario porterebbe per sempre una risposta che non c'è
    stata. Restituisce se c'era qualcosa da riaprire."""
    return bool(SetupQuestion.objects.filter(key=chiave).delete()[0])
