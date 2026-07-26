# Entità EDT — Docenti e cattedre

## Cos'è

Il docente: la sua **anagrafica**, la sua **capacità** (cosa può insegnare) e la sua
**cattedra** (cosa insegna davvero quest'anno — l'insieme delle assegnazioni
materia × classi × ore). EDT tiene queste tre cose distinte, e la distinzione conta.

## Campi osservati nella UI

| Campo | Tipo | Note |
|---|---|---|
| Titolo | enum/testo | Onorifico (Prof., Prof.ssa…). Nessun tooltip. |
| Cognome | testo | |
| Nome | testo | |
| G. Mensa | insieme di giorni | Tooltip: *"Per definire i giorni che richiedono la gestione della mensa per risorsa tra i giorni in cui è attiva (lunedì, martedì, mercoledì, giovedì, venerdì)"*. Giorni in cui il docente ha il turno mensa. Default osservato: **"Tutti"**. |
| Abbr. | testo (≤ 5 car.) | Tooltip: *"Nome abbreviato, 5 caratteri massimo"*. Sigla per la griglia stampata. |
| Mh/s | durata (`h:mm`) | **Input.** Tooltip: *"Monte ore settimanale, numero ore dovute dal docente, ore extra comprese"*. Ore dovute = ordinarie + extra. Le durate in EDT sono ore:minuti (`20h00`), non interi. |
| Occ. prev. | durata | **Calcolato.** Tooltip: *"Occupazione previsionale, in funzione dei docenti desiderati"*. Osservato `0h00` finché non esiste la ripartizione dei servizi. |
| HS Prev. | durata | **Calcolato.** Tooltip: *"Ore supplementari previsionali calcolate in base ai docenti desiderati nella ripartizione dei servizi"*. Osservato `0h00` idem. |
| +/- | durata | **Calcolato.** Tooltip: *"Ore residue rispetto al monte ore definito, monte ore settimanale − occ. previsionale"*. Formula esplicita: `Mh/s − Occ. prev.`. Osservato = `Mh/s` intero prima della ripartizione; deve scendere a **0** a cattedre assegnate. |
| Extra | durata | **Calcolato** (confermato: mostra `0h00` senza input). Tooltip: *"Totale delle ore extra"*. |
| Disciplina | FK → Discipline | **Singola.** Tooltip: *"Disciplina del docente"*. |
| Statuto | enum | Nessun tooltip. Valori osservati: **Titolare** (default), **Supplente**, **Provvisorio**. |
| HSMax | durata | Tooltip: *"Ore supplementari"*. Tetto delle ore supplementari (overtime). Default osservato: **`1h00`** — probabile altro livello di cascata. |
| Materia preferenziale | FK → Materie | **Singola.** Tooltip: *"Materia preferenziale al docente"*. Se si imposta una materia non insegnabile, EDT **la aggiunge da sé** alle insegnabili (vedi sotto). |
| Materie insegnabili | M2M → Materie | **Lista.** Tooltip: *"Elenco delle materie insegnabili"*. |
| Incarichi | M2M → Incarichi | Dropdown "gestire incarichi": gli incarichi sono una **tabella a sé** (vedi sotto), assegnabile al docente. |

## 🔑 Tre nozioni di "materia" sul docente

EDT non mette una sola relazione docente↔materia: ne mette (almeno) tre, più la
cattedra. Confonderle collasserebbe informazione che serve al SaaS sostituzioni.

| Nozione | Campo EDT | Cardinalità | Significato |
|---|---|---|---|
| **Identità** | Disciplina | 1 | Il raggruppamento del docente (le materie puntano a una disciplina — vedi [discipline.md](discipline.md)). |
| **Capacità** | Materie insegnabili | N | Cosa il docente **può** insegnare (abilitazione). |
| **Preferenza** | Materia preferenziale | 1 | Tra le insegnabili, quella da **preferire** in assegnazione (hint per l'auto-assegnazione di EDT). |
| **Assegnazione** | *(la cattedra)* | N | Cosa insegna **davvero** quest'anno (materia × classe/gruppo × ore). |

La **capacità è più ampia dell'assegnazione**: D01 può essere abilitato a ITA e LAT
(materie insegnabili) ma quest'anno insegnare solo ITA (cattedra). È esattamente la
capacità — non l'assegnazione — a decidere **chi può sostituire chi**. Questo aggancia
direttamente il SaaS sostituzioni: eleggibilità = materie insegnabili incrociate con la
classe di concorso (via disciplina). Vedi [ADR-002](../decisioni.md) e
[ADR-006](../decisioni.md).

## Campi calcolati (previsionali) — non si memorizzano

`Occ. prev.`, `HS Prev.`, `+/-` ed `Extra` **non sono input**: sono la
*dashboard di bilanciamento carichi* che EDT calcola in fase di pianificazione
(«ripartizione dei servizi», «docenti desiderati»).

```
Mh/s (input, ore dovute)  −  Occ. prev. (calcolato)  =  +/-  (ore residue)
```

Sono derivate dall'assegnazione e dal monte ore. Memorizzarle significherebbe tenere in
tabella un valore che cambia a ogni modifica della cattedra e può divergere dalla
realtà. Si **ricalcolano a runtime**, come output del solver/report, non come colonne.
Stesso spirito di [ADR-003](../decisioni.md); registrato come [ADR-007](../decisioni.md).

## Monte ore, statuto, ore supplementari

- **Mh/s** è il monte ore *dovuto* (ordinarie + extra). Per una cattedra piena standard
  vale **18**.
- **HSMax** è il tetto delle ore supplementari; **HS Prev.** è l'overtime *proiettato*.
  Alimentano i vincoli di carico del solver, non l'anagrafica pura.
### 🔑 Chiuso: `Mh/s` ha un default, ma non viene dallo Statuto (2026-07-26)

L'ipotesi era che lo **Statuto** guidasse il default di `Mh/s`, come livello
intermedio di una cascata a tre livelli. **Sbagliata a metà.**

**Il default esiste**, ed è **globale**:

> `FicheEDT_ParametresBase_OptionsRessources_RS_Apport`
> FR: **«Apport par défaut pour les professeurs»**

⚠ Ma **la traduzione italiana perde il «par défaut»** — rende soltanto *«Monte ore
settimanale dei docenti»* — per cui **in UI italiana non si vede che è un default**.
È lo stesso genere di perdita segnalato in [glossario-it-fr.md](glossario-it-fr.md):
sulla semantica dei default va interrogato il francese.

**Lo Statuto però non c'entra.** Battute una trentina di chiavi `Statut`: nessuna
lo lega a un monte ore. Lo statuto è anagrafica (titolare / supplente /
provvisorio), e la stessa parola serve altrove per lo stato del motivo d'assenza e
per il coordinatore.

**Quindi la catena è a due livelli — globale → docente — non a tre.**

⚠ Residuo, una sola schermata: verificare se la tabella degli statuti abbia una
colonna di monte ore. Le stringhe dicono di no.

## Il docente nello schema di scambio 📦

Lo schema ufficiale ([schema-scambio.md](schema-scambio.md)) dichiara:

```
Professeur
├── @Nom, @Prenom, @Abreviation, @DateNaissance
├── @Statut                                    ← esiste come campo di scambio
├── Civilite  (0..1)
├── Apport    (0..N)   "Liste des apports en minutes pour chaque discipline"
│   ├── @DureeMinutes
│   └── Discipline (0..1)
├── AHE       (0..N)   @Ident + @DureeMinutes
└── Salle     (0..1)   "Salle de préférence"
```

Tre riscontri e un'assenza:

- **`Statut` è un campo di scambio di prima classe**, non un attributo interno.
  Rafforza l'ipotesi che sia un livello di cascata, ma ⚠ **non la conferma**: lo
  schema lo dichiara come stringa libera senza legarlo ad alcun monte ore.
- **`Salle de préférence`** conferma per via indipendente la distinzione
  preferenza vs. assegnazione già stabilita per le materie: EDT applica lo stesso
  pattern all'aula.
- **`Apport` quantifica la capacità**: non solo *quali* discipline, ma *quanti
  minuti* per disciplina. È una precisazione di [ADR-006](../decisioni.md), che
  finora trattava la capacità come relazione booleana.
- **`Apport` *è* `Mh/s`** — confermato 📦. Non c'è un campo separato per il monte
  ore perché `Apport` è il monte ore: le tabelle di lingua danno
  `UtilitairesEdt_ColonnesRessources_RS_App*` → IT corto **`Mh/s`**, IT esteso
  **`Monte ore settimanale`**, FR corto `App.`, FR esteso **`Apport`**. La stessa
  parola è tradotta `Monte ore` anche nella vista *Consumo per disciplina*.

  Due conseguenze:

  1. **`Mh/s` non è un massimo**, malgrado la sigla lo suggerisca: è il monte ore
     *contrattuale dovuto*. Coerente col tooltip già osservato ("ore dovute dal
     docente"), ma ora è certo.
  2. Nel formato di scambio il monte ore è **scomposto per disciplina** (un
     `Apport` per disciplina, in minuti). `Mh/s` in UI ne è la somma. Il nostro
     modello dovrebbe tenere la scomposizione, non solo il totale — è la stessa
     informazione che serve a `Occ. prev.` per disciplina.

⚠ **Ambiguità su `Statuto`.** La chiave `Chaines_EdT_RS_WinColonStaLong` traduce
FR `Statut` → IT `Statuto` (lo statuto giuridico: titolare/supplente/provvisorio,
quello della tabella qui sopra). Ma `WinAffVSProfesseurAffectation` traduce FR
`Affectation` → IT `Statuto` in un'altra griglia, dove significa
**assegnazione**. Due colonne italiane con lo stesso nome e significati diversi:
verificare sempre in quale vista si è. Vedi
[glossario-it-fr.md](glossario-it-fr.md).

## La cattedra

La cattedra associa a un docente una o più **materie**, le **classi** su cui le insegna
e le **ore settimanali** risultanti (è il volto concreto dell'*assegnazione* della
tabella sopra).

- Una cattedra completa vale **18 ore** settimanali. Chi sta sotto ha uno **spezzone**
  (cattedra completata su un'altra scuola).
- Nel dataset Fermi le 18 cattedre sommano **288 ore**, coerenti con il monte ore-classe
  totale (quadratura verificata — vedi
  [`data/liceo-fermi/classi.md`](../../data/liceo-fermi/classi.md)).

## Spezzoni → vincoli di indisponibilità

D06 (12 h), D09 (6 h) e D15 (9 h) hanno spezzoni sotto le 18 ore. È realistico e utile:
un docente in servizio anche su un'altra scuola porta **giorni di indisponibilità** su
questa. Come EDT esprime concretamente l'indisponibilità è ancora da osservare — vedi
[vincoli.md](vincoli.md).

## G. Mensa

Insieme di giorni (lun–ven) in cui il docente ha il turno mensa: un attributo per
risorsa, di giorno, non di ora. Probabile **fuori scope v1** (non è un vincolo d'orario
in senso stretto), ma va registrato perché è un dato per-docente che EDT modella
esplicitamente. Da riprendere in [vincoli.md](vincoli.md) se rientra in scope.

## Implicazioni per il nostro modello

- **Docente (anagrafica):** titolo, cognome, nome, abbr., statuto, disciplina, `Mh/s`,
  `HSMax`, materia preferenziale.
- **Capacità:** M2M `docente ↔ materia` (materie insegnabili). È la relazione che
  determina l'eleggibilità alle sostituzioni — **da tenere separata** dalla cattedra.
  Vedi [ADR-006](../decisioni.md).
- **Cattedra/assegnazione:** docente × materia × classe/**gruppo** × ore, una riga per
  assegnazione; punta potenzialmente a un [gruppo](gruppi.md), non solo alla classe
  intera.
- **Campi previsionali** (`Occ. prev.`, `HS Prev.`, `+/-`, `Extra`): non memorizzare,
  ricalcolare. Vedi [ADR-007](../decisioni.md).
- **`Statuto`:** ~~probabile sorgente di default per `Mh/s`~~ → **no**, chiuso: il
  default di `Mh/s` è **globale**, lo statuto è pura anagrafica (vedi sopra).
- **`G. Mensa`:** insieme di giorni per docente; probabile fuori scope v1.

## Osservazioni dall'inserimento (2026-07-09)

Screenshot della tabella docenti compilata (18 righe):

- **Le durate sono ore:minuti** (`20h00`), non interi → nel nostro schema le ore vanno
  in **minuti** (o `DurationField`), non `IntegerField`.
- **Extra è derivato**: mostra `0h00` senza alcun input (punto chiuso).
- **Default osservati**: `Statuto = Titolare`, `G. Mensa = Tutti`, `HSMax = 1h00`.
  Nessuno è stato digitato → coerenti con la cascata [ADR-003](../decisioni.md).
- **Occ. prev. / HS prev. a `0h00`** e `+/- = Mh/s` intero: i previsionali restano a
  zero finché non esiste la ripartizione dei servizi. La quadratura (`+/- → 0`) si
  verifica dopo l'assegnazione delle cattedre.
- **Titolo** lasciato vuoto senza obiezioni: campo facoltativo.
- **Statuto**: enum a tre valori — **Titolare / Supplente / Provvisorio**. È lo stato
  contrattuale, non il monte ore.
- **Preferenziale ⊆ insegnabili per auto-correzione, non per vincolo**: impostando come
  preferenziale una materia fuori dalle insegnabili, EDT **la aggiunge da sé** alla
  lista invece di rifiutare. L'invariante è mantenuto, ma riparando l'input.

## L'elenco Docenti in ambiente Orario (osservato 2026-07-15)

Dopo la creazione delle attività, l'elenco docenti di **Orario** mostra colonne
in parte diverse da quello di Preparazione (⚠ = ipotesi da confermare):

| Colonna | Valore osservato | Note |
|---|---|---|
| Mh/s | come in Preparazione | |
| Mh/a | `0h00` | ⚠ monte ore annuale |
| Occ. | = `Mh/s` | occupazione dalle attività create (non più "previsionale") |
| MG lav. / G lav. | `0` | ⚠ mezze giornate / giorni lavorati — a zero finché non c'è piazzamento |
| D.T.B. | `2h00` per tutti | ⚠ durata totale dei buchi tollerata — combacia col default "ore di buco tollerate = 2" dei vincoli ([vincoli.md](vincoli.md)); candidato **cascata** |
| Occ. eff. | = `Occ.` | ⚠ occupazione effettiva (post-piazzamento?) |
| Extra | `0h00` | come in Preparazione |
| TOP | % | **tasso di occupazione** = `Occ. / 50h` (griglia lun–ven × 08–18): verificato su tutti i 18 (Villa 20h → 40%, Greco 6h → 12%, Ricci 17h → 34%…) |

## Incarichi — tabella a sé

"Gestire incarichi" apre la creazione di nuovi incarichi. Campi osservati:

| Campo | Tipo | Note |
|---|---|---|
| Codice | testo | |
| Nome corto | testo | |
| Nome lungo | testo | |
| Impegno | enum + durata | Opzioni: **non definito**, **definito** (con campo per inserire la durata), **tutto l'anno**. |

Quindi l'incarico è un'**entità catalogabile** (come le discipline: tabella, non enum)
con una durata d'impegno, assegnata poi al docente. Semantica plausibile: ruoli
aggiuntivi (coordinatore, collaboratore del DS, referente…) che consumano ore. **Da
osservare**: se l'impegno "definito" sottrae ore alla disponibilità del solver o è solo
anagrafico.

## Aperto / da osservare

- Se lo **Statuto** guida default di altri campi (cascata) o è solo anagrafico.
- Se l'**impegno** di un incarico incide sul calcolo ore (`Occ. prev.`/`Extra`) o è
  solo descrittivo.
- ~~Verificare che `+/-` scenda a **0** su tutti i docenti alla ripartizione
  puntuale per classe~~ → **verificato (2026-07-15)**: dopo la ripartizione
  puntuale (allineamenti cancellati, un docente per classe, supplementari a
  zero) tutti i 18 docenti mostrano `Occ. prev.` = `Mh/s` e `+/- = 0h00`.
  (In fase previsionale non poteva: `Occ. prev.` conta le ore del bisogno una
  volta sola, non per classe — vedi [attivita.md](attivita.md).)

## Dataset di esempio

Le 18 cattedre del Liceo Fermi:
[`data/liceo-fermi/docenti.md`](../../data/liceo-fermi/docenti.md).
