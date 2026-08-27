# Alleggerimenti a quota e ottimizzazione lessicografica — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dare al solver i due stati che oggi non ha — l'attività **scartata** e
il vincolo **alleggerito a quota** — e la catena lessicografica che li governa,
così che un'istanza sovravincolata produca un orario con scarti nominati invece
di `INFEASIBLE`.

**Architecture:** `AddExactlyOne` diventa `sum(celle) == piazzata[a]`, e lo
scarto entra nel registro dei predicati come tutti gli altri (causale +
checker), perché senza un finding che lo nomini «scarta tutto» è una soluzione
pulita per l'oracolo differenziale. Le quote vivono in `relaxation.py`: un
letterale di violazione per riga alleggeribile, agganciato al **residuo** di
ADR-018 e non al tetto grezzo, con la somma sotto `RelaxationQuota`. La catena
lessicografica sta in `objective.py`: risolvi, fissa, prosegui — mai una somma
pesata.

**Tech Stack:** Python 3, Django (solo ORM e `manage.py`), OR-Tools CP-SAT,
pytest + `pytest-django`. Nessuna nuova dipendenza.

**Spec:** [docs/superpowers/specs/2026-08-26-alleggerimenti-lessicografico-design.md](../specs/2026-08-26-alleggerimenti-lessicografico-design.md)

## Global Constraints

1. **La suite parte da 450 test verdi, 16 skip.** Nessun task la lascia rossa,
   e nessuno *riduce* il numero di test. I due test di §2.1 della spec
   (dominio vuoto) **cambiano significato**: vanno riscritti, mai cancellati.
   In locale si esegue `venv/bin/pytest`; dove il venv non esiste,
   `python3 -m pytest`.
2. **`domain/analysis/` non importa mai `ortools`.** Il checker dello scarto
   sta di là, la macchina degli scarti di qua.
3. **Quote a zero ⇒ il modello di oggi.** Nessun letterale di violazione va
   creato in assenza di una riga `RelaxationQuota`. È un test, non un
   corollario.
4. **Nessuna penalità, mai.** Un letterale di violazione entra in un
   conteggio con un tetto, e al più in un livello lessicografico. Se in un
   diff compare `minimize(w1*a + w2*b)`, il task è respinto.
5. **Il residuo, non il tetto grezzo.** Dove oggi c'è `residual_cap`, domani
   c'è `libere <= residuo + margine·v`. Alleggerire concede un margine *sopra
   lo stato corrente*; pretendere che il passato venga riparato è la metà
   vietata di ADR-018.
6. **Ogni traduzione si deriva leggendo il checker**, non ricordandolo. Vale
   dallo spike, e ha trovato qualcosa ogni volta che è stata applicata.
7. **Il test che dimostra che un vincolo morde forza la violazione e attende
   `INFEASIBLE`.** Mai «risolvi e guarda dove è finita»: è un rilevatore
   debole, misurato 1 su 11 nella spec precedente.

## Task 1 — Lo scarto, con L1 attaccato ✅ (2026-08-26)

⚠ L'obiettivo non è un miglioramento di questo task: è ciò che lo rende un
task. Senza, «scarta tutto» è ammissibile e CP-SAT la restituisce.

- [x] `causali.py`: la causale dello scarto (`activity_unplaced`).
- [x] `domain/analysis/checkers/placement.py`: `structural:placement`, un
      finding `HARD` per ogni attività senza piazzamento.
- [x] `model.py`: `piazzata[aid]`, `sum(lits) == piazzata`, e il ramo del
      dominio vuoto che diventa uno scarto invece di un'infattibilità.
- [x] ~~Il builder registrato sotto `structural:placement`~~ → **no**: la
      traduzione esiste ma non è un builder, perché crea le variabili di
      decisione e deve esistere prima che qualunque builder giri
      (`vocabulary.pos` la legge). Seconda assenza **dichiarata** da un test.
- [x] L1: minimizza le **ore** scartate.
- [x] I due test del dominio vuoto riscritti, più il loro gemello con
      `allow_unplaced=False`.
- [x] Il Fermi resta a **zero scarti** (e i numeri del modello aggiornati:
      8425 variabili, 1083 constraint — +284 `piazzata`, +1 obiettivo).
- [x] Un test che pretende scarti **contati**, non «status diverso da
      INFEASIBLE».
- [x] *(non previsto)* `allow_unplaced=False`: il modello che pretende il
      piazzamento, per i 23 test che dimostrano che un vincolo morde.
- [x] *(non previsto)* Il banco a testimone pretende **zero scarti** in tre
      punti: una soluzione che scarta è pulita per qualunque famiglia, quindi
      senza quell'assert il banco si era indebolito in silenzio.
- [x] *(non previsto)* `presolve_substitution_level = 0` e `workers=1` nel
      banco. Le due misure sono nel changelog.

## Task 2 — La catena ✅ (2026-08-26)

- [x] `objective.py`: livelli, fissaggio del valore ottenuto (`<=`, non `==`),
      limite di tempo **per livello**, `stats` livello per livello.
- [x] L2: numero di attività scartate, come spareggio di L1.
- [x] Test di **monotonia** — ⚠ nella forma che morde: un'istanza dove L1 e L2
      tirano in direzioni **opposte**. Con l'istanza a pareggio scritta per
      prima, togliere il fissaggio lasciava la suite verde.
- [x] *(non previsto)* La cucitura `solver=` iniettabile, e con essa i due rami
      di caduta: un livello che **non conclude** (la catena si ferma ma
      restituisce l'ultimo livello concluso) e uno che **non dimostra**
      l'ottimo (`ottimo=False`, fissaggio all'ultimo valore trovato). Nessuno
      dei due sarebbe stato affermato da un test, e farli scattare con un
      limite di tempo stretto avrebbe prodotto test flaky.
- [x] *(non previsto)* I test delle due esenzioni del banco sporco **cercano**
      il fenomeno su una lista di semi dichiarata invece di appuntarne uno: i
      fenomeni si erano spostati per la terza volta in una sessione, perché
      sono proprietà della soluzione restituita e ogni ondata ne cambia una.

## Task 3a — Il meccanismo delle quote, e due famiglie ✅ (2026-08-26)

- [x] `RelaxationQuota.params` e
      `InstituteSettings.max_relaxed_constraints_per_resource` (migrazione
      additiva `0008`). `ARRIVAL_DEPARTURE` aggiunto a `Family`: in EDT
      `Gestione Entrate / Uscite` è alleggeribile, e mancava.
- [x] `relaxation.py`: lettura delle righe, i due modi (**margine** additivo e
      **deroga** per enforcement), tetti per (famiglia, risorsa) e tetto
      globale per risorsa. Le quote si postano una volta sola in fondo a
      `build_model`: nessun builder le conosce.
- [x] `MAX_HOURS` (margine) e le tre incompatibilità di materia (deroga), in
      **entrambi** i rami `post_separable` e `post_cross` — alleggerirne uno
      solo avrebbe lasciato metà famiglia scoperta.
- [x] «Senza righe, il modello è quello di prima», e «una quota a zero è come
      non averla».
- [x] «La quota morde»: con quota `k`, la violazione `k+1` dà `INFEASIBLE`.
- [x] «Il margine è quello dichiarato»: alleggerire non è un interruttore.
- [x] «Il margine si somma al **residuo**, non al tetto grezzo»: l'incrocio con
      ADR-018, che è il punto in cui questo pezzo poteva sbagliare in silenzio.
- [x] «Un vincolo alleggerito resta una violazione **nominata**»: la quota non
      nasconde il finding, autorizza il solver a produrlo.

## Task 3b — Le famiglie restanti ✅ (2026-08-26)

- [x] `MAX_PRESENCE`, `HALF_DAYS` (tetto **e** «solo mezza giornata», che è
      una deroga), `ARRIVAL_DEPARTURE`, `FREE_GUARANTEED` — ⚠ sono **soglie**:
      il margine si sottrae. E si applica al ramo della **riparazione**, mai
      allo status quo, che non è una soglia da alleggerire ma il divieto di
      peggiorare (ADR-018).
- [x] `SITES` (cambi di sede) e `DIDACTIC_WEIGHT`.
- [x] Le altre righe di materia — ⚠ e sono **famiglie distinte**, come in EDT:
      `SUBJECT_MAX_HOURS` (margine) e `SUBJECT_SEQUENCE` (deroga) accanto a
      `SUBJECT_CONSTRAINT` (le incompatibilità). Migrazione `0009`.
- [x] Un test per famiglia, nella forma «senza quota `INFEASIBLE`, con quota
      `OPTIMAL`». Una sola mutazione — il meccanismo che non concede nulla —
      li fa cadere tutti e quindici.
- [x] ⚠ Dichiarato nel docstring del modello: le famiglie che **non**
      compaiono non sono alleggeribili, ed è la scelta di EDT, non una
      dimenticanza.
- [x] *(non previsto)* Un letterale **per riga**, non per parametro, dove i
      parametri sono due metà dello stesso alleggerimento (presenza, giorni
      liberi, sedi): due quote consumate per una sola concessione sarebbero
      state un errore invisibile.

## Task 4 — Le quote nei pre-filtri

⚠ Il caso storto, e l'unico in cui si sbaglia in silenzio: se il builder pota
**e** riammette, la quota è inerte e nessun test se ne accorge da solo.

- [ ] `UNAVAILABILITY` / `OPTIONAL_UNAVAILABILITY`: con quota > 0 il builder
      non pota, riammette le celle e posta un `v` per cella.
- [ ] Un test che dimostra che la cella riammessa è **usabile** e che il suo
      uso consuma quota.

## Task 5 — L3, e il ramo pigro

- [ ] L3: i `v` consumati **e** i booleani di riparazione dei rami disgiuntivi,
      in due conteggi separati dentro lo stesso livello.
- [ ] Il test che pretende la riparazione dove §9.7 misurava lo scambio di
      soglie di `free_guaranteed` (seme 20 del banco che congela).
- [ ] §9.7 della spec precedente aggiornata: il debito si chiude qui, e si
      scrive **come**.

## Task 6 — L4, la stabilità

- [ ] L4: minimizza le attività che cambiano cella rispetto ai `Placement`
      esistenti.
- [ ] Un test sulla rigenerazione per periodo: due solve di seguito sullo
      stesso schedule non stravolgono l'orario.

## Task 7 — `manage.py solve`

- [ ] Comando in stile `analyze`: scarti nominati, alleggerimenti consumati,
      livello per livello, e i tempi.
- [ ] Un test del comando sul Fermi.
