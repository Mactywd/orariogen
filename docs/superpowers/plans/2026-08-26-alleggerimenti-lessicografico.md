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

## Task 1 — Lo scarto, con L1 attaccato

⚠ L'obiettivo non è un miglioramento di questo task: è ciò che lo rende un
task. Senza, «scarta tutto» è ammissibile e CP-SAT la restituisce.

- [ ] `causali.py`: la causale dello scarto.
- [ ] `domain/analysis/checkers/placement.py`: `structural:placement`, un
      finding `HARD` per ogni attività senza piazzamento.
- [ ] `model.py`: `piazzata[aid]`, `sum(lits) == piazzata`, e il ramo del
      dominio vuoto che diventa uno scarto invece di un'infattibilità.
- [ ] Il builder registrato sotto `structural:placement`, così che il registro
      resti in parità e `test_solver_registry_completo` continui a dichiarare
      **un solo** checker senza builder.
- [ ] L1: minimizza le **ore** scartate.
- [ ] I due test di §2.1 riscritti: dimostrano lo stesso dominio vuoto,
      pretendendo lo scarto nominato.
- [ ] Un test che pretende che il Fermi resti a **zero scarti**.
- [ ] Un test che pretende che un'istanza infattibile dia scarti **contati**,
      non solo «status diverso da INFEASIBLE».

## Task 2 — La catena

- [ ] `objective.py`: livelli, fissaggio del valore ottenuto, limite di tempo
      **per livello**, `stats` livello per livello.
- [ ] L2: numero di attività scartate, come spareggio di L1.
- [ ] Test di **monotonia**: L2 non peggiora L1. È la proprietà che regge anche
      quando un livello scade in tempo.

## Task 3 — Le quote, sulle famiglie a clausola

- [ ] `RelaxationQuota.params` e `InstituteSettings.max_relaxed_constraints_per_resource`
      (+ migrazioni additive). `ARRIVAL_DEPARTURE` aggiunto a `Family`, o
      escluso con una ragione scritta.
- [ ] `relaxation.py`: lettura delle righe, creazione dei `v`, tetti per
      (famiglia, risorsa) e tetto globale per risorsa.
- [ ] Le famiglie della tabella §3.3 che sono clausole, una per una, agganciate
      al residuo.
- [ ] Il test «quote a zero = modello di oggi» (Global Constraint 3).
- [ ] Il test «la quota morde»: con quota `k`, forzare `k+1` violazioni dà
      `INFEASIBLE`.

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
