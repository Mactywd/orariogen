# Task 11 — giro di correzione 1

La review non ha trovato nessun Critical: la traduzione è corretta contro il
checker, le tre correzioni pre-dispatch hanno tenuto, e **sette sospetti sono
stati chiusi con misure** (fra cui il costo zero sul Fermi e la tenuta numerica
del `param` per firma). Restano **tre Important** e **tre Minor**, tutti da
chiudere in questo giro.

Lavori nel worktree `.claude/worktrees/modello-hard-completo` e **non ne esci**.
Test con `venv/bin/pytest` dalla radice. Stato di partenza: **338 passed,
4 skipped**, tre file modificati più `tests/test_solver_subject_maxhours.py` non
tracciato. **Non fare commit.**

Prima di toccare qualsiasi cosa leggi
`.superpowers/sdd/2026-08-24-modello-hard-completo/task-11-brief.md` (il brief
originale) e il fondo di `progress.md`, **Rulings 63-70**: sono le decisioni già
prese su questi finding, con le misure.

## Important 1 — la guardia di violabilità non guarda la capienza del secchio

**Il difetto.** Le due guardie della Ruling 55 sono entrambe *necessarie*, ma
sono verificate **indipendentemente** e nessuna guarda **quanto ci sta davvero
in un secchio** — la larghezza del secchio contro le durate. È la dimensione che
la Ruling 45 aveva già dovuto scoprire per `SAME_HALF_DAY` e che non è stata
riportata sul tetto di ore.

**La misura** (sonda esatta del revisore: modello col `post` della famiglia
spento più la clausola «esiste una firma e un secchio con minuti > `param`»;
`INFEASIBLE` = riga inviolabile). Sui seed 1-5: `max_hours_half_day` crea 20
righe, **4 inviolabili**; `max_hours_day` ne crea 18, **0 inviolabili**. Le
**due** righe del seed 2 sono fra le inviolabili — quindi `potere = 2`,
`run_family` non salta, e `test_famiglia[max_hours_half_day-2]` è un verde che
non può fallire.

**La correzione: guardia di riempimento per firma.** Per ogni firma di
settimana, calcola il massimo di minuti che possono **partire** nello stesso
secchio in un giorno qualunque **senza sovrapporsi**, enumerando le
collocazioni con `_collocazioni` (stessa forma di `_ci_stanno`: enumerazione
esaustiva, non formula chiusa — la formula chiusa su questo branch è stata
provata e scartata **due volte**, Ruling 51). La riga si crea solo se **qualche
firma** supera `param`.

È una condizione necessaria (limite superiore esatto della somma di secchio,
ignorando le altre risorse) e **subsume entrambe le guardie attuali**: valuta se
tenerle comunque per chiarezza o se sostituirle, e **dichiara quale scelta hai
fatto e perché**.

Misurata dal revisore fuori dal codice, sui seed 1-5: esclude **2 righe
inviolabili su 4**, **0 righe violabili su 16**, ed è un **no-op completo sul
secchio giornata**. ⚠ Quei numeri vengono da una sonda esterna, non da una
versione modificata del derivatore: **rimisurali** dopo averla implementata, e
verifica che il potere vincolante dei seed che oggi funzionano non peggiori.

**⚠ E dichiara il residuo (Ruling 64).** Anche con questa guardia il seed 2
crea ancora **una** riga inviolabile, e resta un verde che non può fallire. Non
è un difetto della guardia: quella riga è inviolabile per
`structural:site_transition` — le due attività che sommerebbero abbastanza
minuti hanno **sedi diverse**. Un derivatore calcola condizioni necessarie sulla
**sola geometria** e non vede le altre risorse; stabilire la violabilità esatta
richiede di chiedere al solver, ed è una decisione rimandata al Task 17
(Ruling 65). **Scrivi questo limite nella docstring del derivatore**, in modo
che chi legge il numero non lo scambi per una garanzia.

## Important 2 — «entrambi i versi» dichiarato, nessuno dei due difeso

`test_forbidden_sequence_con_a_uguale_b` afferma in docstring che con A = B il
doppio ciclo vieta l'adiacenza «in **entrambi** i versi». Il revisore ha
verificato che **la proprietà è vera** (congelata alla fascia 1: la libera non
può andare né alla 0 né alla 2, entrambe `INFEASIBLE`) e che **nessun test la
difende**: mutando il `post` a vietare un verso solo con A = B —
`if row.subject_a_id == row.subject_b_id and pb <= pa: continue` — la suite
resta **338 passed, 4 skipped**.

Correzione: metti la congelata alla fascia **1** invece che alla 0, così il
verso inverso («la libera finisce dove la congelata comincia») diventa
osservabile, e verifica entrambi. Poi **verifica per mutazione** che il test
nuovo fallisca con quella mutazione, ripristina, e conferma con `git diff` che
non resti traccia. Riporta l'esito.

Togli anche dal corpo del test il commento che afferma il contrario di quello
che fa (*«fascia -1, impossibile comunque … è verificato qui per completezza»*).

## Important 3 — `MAX_HOURS` con A ≠ B non è coperto da nulla

La docstring di `_MaxHoursSubject` afferma — **correttamente** contro il checker
(`_MaxHours.violations` itera su `a` e non tocca mai `b`) — che si somma la
**sola** materia A anche quando A ≠ B. È l'affermazione portante di quel
builder, ed è l'unica cosa che il piano segnalava con un ⚠.

Non esiste in tutto il repo una riga `MAX_HOURS_*` con A ≠ B: il derivatore crea
sempre `subject_a=subject, subject_b=subject`, e tutti e tre i test mirati usano
A = B. Misura del revisore: mutando il `post` a sommare **anche** B quando le
materie differiscono — un errore semantico reale contro il checker — la suite
resta **338 passed, 4 skipped**.

Scrivi il test: due materie distinte, un tetto che il totale della **sola** A
sfora e che A+B sforerebbe di più, così il test distingue le due semantiche.
Verifica per mutazione.

## Minor 1 — due test byte-identici

`test_forbidden_sequence_vieta_l_adiacenza` e
`test_adr018_forbidden_sequence_una_congelata_la_libera_evita` hanno corpi
identici **carattere per carattere**: stesse attività, stesso piazzamento,
stessa riga, stesse asserzioni. Solo le docstring differiscono, e il "ramo 2" di
ADR-018 è già interamente il primo test.

Correzione (Ruling 68): **differenzia il secondo** mettendo **B congelata e A
libera** — verso non ancora esercitato con A ≠ B — invece di fonderli.

## Minor 2 — l'assert su `KIND` è tornato opt-in

La Ruling 58 chiedeva l'estrazione perché una sottoclasse che dimentichi `KIND`
si **rompesse** invece di prendere in silenzio la semantica "half". Ora l'assert
è in `_check_kind()`, **un metodo che ogni `post` deve ricordarsi di chiamare**:
una futura sottoclasse di `_Bucketed` col proprio `post` che non lo chiama è di
nuovo nella condizione che la Ruling voleva chiudere.

Correzione: sposta l'assert dentro `buckets()`, che ogni `post` di `_Bucketed`
**deve** chiamare per funzionare — lì è inevitabile invece che da ricordare.
Togli `_check_kind()` e le sue chiamate.

## Minor 3 — `MAX_HOURS_HALF_DAY` non ha un test ADR-018

`test_adr018_max_hours_giorno_gia_sopra_il_tetto` copre solo `MAX_HOURS_DAY`. Il
`post` è lo stesso codice, quindi il rischio è basso — ma il secchio mezza
giornata è dove il clamp interagisce con `bucket_of` sulla fascia di partenza,
ed è la famiglia col potere vincolante più basso, cioè quella che il banco
sorveglia meno. Scrivi il gemello.

## Cosa NON fare

- **Non rinominare `subject_buckets.py`** (Ruling 70): la docstring dichiara già
  in chiaro che il modulo ospita anche un vincolo che i secchi non li usa, ed è
  la scelta giusta. Rinominare a metà branch è churn su sei task.
- **Non adottare la sonda esatta di violabilità come criterio di `potere`**
  (Ruling 65): è la proposta di metodo più importante uscita finora, ma è una
  decisione del Task 17 — richiede di riesprimere in CP-SAT la condizione di
  violazione di **ogni** famiglia, cioè una seconda implementazione di diciotto
  vincoli dentro il banco.
- Non toccare `tests/test_solver_same_day.py`, `tests/test_solver_subject_buckets.py`,
  `tests/test_solver_time_counting.py`, né i file di altri task.

## Alla fine

`venv/bin/pytest -q -rs` per intero. **Riporta i numeri che misuri** e spiega
ogni scostamento. Se compaiono skip nuovi, dì quale seed salta e **perché quella
riga è davvero inviolabile**.

Rapporto in cinque punti:

1. cosa hai cambiato, finding per finding;
2. le **verifiche per mutazione**, con l'esito di ciascuna — in particolare:
   l'Important 2 e l'Important 3 falliscono davvero con le mutazioni che la
   review ha usato?
3. la rimisura della guardia di riempimento: quante righe esclude, quante di
   quelle erano violabili, e il potere vincolante prima e dopo;
4. skip finali e numeri della suite;
5. **cosa non hai fatto o non hai verificato**, senza arrotondare.
