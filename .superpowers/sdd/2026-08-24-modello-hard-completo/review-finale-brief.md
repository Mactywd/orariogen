# Review finale — branch `modello-hard-completo`

Revisore. Worktree `modello-hard-completo`, HEAD `8cf87b7`. Python:
`venv/bin/pytest`. Suite attuale: **424 passed, 15 skipped**. Docstring e
commenti in italiano senza accenti, identificatori in inglese.
`domain/analysis/` **non si tocca mai** — e' l'autorita' semantica, e ogni
volta che builder e checker divergono **vince il checker**.

Diff: `git diff master...HEAD` — 35 file, ~8600 righe. Diciassette task, dallo
spike a cinque vincoli al modello hard completo: ventisei builder su
ventisette checker.

## 0. Cosa e' gia' noto, e non va ri-trovato

Il registro delle decisioni e' in
`.superpowers/sdd/2026-08-24-modello-hard-completo/progress.md` — **118
rulings**. Leggilo prima: ogni difetto gia' trovato, la decisione presa e il
costo se sbagliata sono li'. Segnalare di nuovo una cosa gia' decisa li' non
aiuta; **contraddire** una decisione con una prova nuova aiuta moltissimo.

I debiti gia' dichiarati (in §9.7 della spec e in «Ancora aperto» di
`CLAUDE.md`) non sono findings:

- il banco **non congela mai nulla**, quindi ADR-018 poggia sui soli test
  scritti a mano;
- `coverage_mismatch` sul testimone, da riparare nella fixture;
- i due tie-break di `domain/analysis` che sono artefatti dell'ordine
  d'inserimento (`MaxSiteChangesChecker`, `_placed_of`);
- la meta' del tetto inevadibile che nessun builder puo' risolvere.

## 1. Cosa cercare, in ordine di valore

Il difetto che questo progetto produce, dodici volte su dodici, ha **una sola
forma**: un documento — piano, spec, docstring, commento — dichiara vera una
proprieta' che si rivela falsa solo controllandola contro il checker o contro
i dati. Mai a colpo d'occhio sul documento. Quindi:

1. **Ogni affermazione di conservativita', esattezza o sufficienza, verificata
   contro il checker.** Ce ne sono in quasi ogni docstring di
   `domain/solver/builders/`. Frasi tipo «e' conservativo», «e' esatto», «la
   direzione dell'errore e' sicura», «questo insieme di chiavi basta»: per
   ognuna, il checker corrispondente dice davvero quella cosa? La domanda che
   ha funzionato meglio finora e' **«conservativo in quale verso?»** — il
   D.T.B. era conservativo nel verso opposto a quello dichiarato.
2. **Test che non difendono nulla.** Criterio (Ruling 89): un test che afferma
   la **presenza** di un vincolo dev'essere rosso quando il `build()`/`post()`
   di quel builder e' reso no-op. Se ne trovi uno che resta verde, e' un test
   che non afferma niente. ⚠ I test di **assenza** non possono essere rossi
   sotto no-op: quelli si difendono con una mutazione mirata, e nel report va
   detto quale.
3. **Vacuita' nei derivatori di `tests/solver_harness.py`.** Sei forme gia'
   censite (occorrenza singola, maschere disgiunte, impossibilita' geometrica,
   materia assente, capienza del secchio, due occorrenze contro una
   transizione). Cercane una settima: una riga creata che **nessun
   piazzamento** puo' violare e' potere vincolante contato e inesistente. Lo
   strumento che funziona e' la sonda esatta — costruire il modello col
   builder spento, aggiungere la clausola che esprime la violazione, e vedere
   se e' soddisfacibile.
4. **ADR-018 nei quattro casi.** Vedi §9.5 della spec. Per ogni builder:
   quando le congelate sono gia' in violazione, il modello resta fattibile? E
   quando resta fattibile, la soluzione introduce un finding con una
   `Finding.key` **nuova**? La chiave include `activities` e `quantities`, non
   solo il codice: e' li' che il Task 12 aveva un buco.
5. **La composizione.** `test_modello_completo` prova i ventisei builder
   insieme su cinque seed. Cinque seed non sono molti: se trovi una coppia di
   builder che possono contraddirsi, dillo con un caso costruito, non con un
   sospetto.

## 2. Cosa **non** cercare

- Stile, naming, formattazione, lunghezza delle docstring.
- Ottimizzazioni di performance: il costo misurato sul Fermi e' irrilevante e
  il modello non e' ancora in produzione.
- I tre pezzi dichiarati fuori scope (aule, alleggerimenti + lessicografico,
  violatore di Hall).
- Proposte di refactoring architetturale.

## 3. Forma del report

Per ogni finding: **file e riga**, la proprieta' dichiarata, la prova che e'
falsa (misurata, non argomentata), e il costo se resta. Ordina per gravita'
reale, non per numero.

⚠ **Distingui «l'ho dimostrato» da «lo sospetto»**, esplicitamente. Un
sospetto etichettato come tale e' utile; un sospetto presentato come prova ha
gia' fatto perdere tempo su questo branch.

Se non trovi nulla di grave, **dillo**: un report che gonfia tre minori per
sembrare produttivo e' peggio di un report corto. Ma prima di dirlo, prova
almeno tre mutazioni per conto tuo — spegnere un builder e contare i rossi e'
la contromisura che ha trovato piu' difetti di qualunque rilettura.

Non committare, non pushare. Report in
`.superpowers/sdd/2026-08-24-modello-hard-completo/review-finale-report.md`.
