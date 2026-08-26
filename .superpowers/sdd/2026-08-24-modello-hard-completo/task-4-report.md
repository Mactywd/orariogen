# Task 4: Spostamento dei builder nei file del proprio pattern

## Completamento

Lo spostamento è completo e verificato. Due builder sono stati spostati nei file che seguono il pattern di appartenenza.

## Cosa è stato spostato

### File rinominati (via `git mv`)
- `domain/solver/builders/time_constraints.py` → `domain/solver/builders/time_presence.py`
- `domain/solver/builders/subject_constraints.py` → `domain/solver/builders/subject_buckets.py`

### File modificati
- `domain/solver/builders/__init__.py`: aggiornati gli import dai vecchi nomi ai nuovi
- `domain/solver/builders/time_presence.py`: preposto nuovo docstring di modulo
- `domain/solver/builders/subject_buckets.py`: preposto nuovo docstring di modulo

## Verifica di continuità della logica

Il brief richiede di dimostrare che **la logica non è cambiata**. Analisi del diff:

1. **Spostamento via `git mv`**: preserva la storia git e non cambia alcun byte del codice sorgente dei builder.
2. **Docstring di modulo**: aggiunto sopra il docstring esistente senza toccare la logica sottostante. I docstring descrivono il pattern di **cui il builder fa parte**, non il builder in sé.
3. **Import in `__init__.py`**: cambiamento puramente meccanico da `time_constraints` e `subject_constraints` a `time_presence` e `subject_buckets` — nessuna logica di builder toccata.

**Verifica**: gli unici cambiamenti nel diff dei due builder sono:
- Nome del file (rinomina storica gestita da `git mv`)
- Aggiunta di righe di docstring sopra la riga `"""MAX_GAP_HOURS…` e `"""SAME_DAY_INCOMPATIBLE…`
- Nessun cambiamento al codice Python dei builder stessi

## Test

### Stato pre-spostamento
```
189 passed in 7.89s
```

### Stato post-spostamento
```
189 passed in 7.87s
```

**Risultato**: Numero identico di test verdi. Nessun test aggiunto né rimosso.

### Verifica degli import nei test

Pre-spostamento:
```bash
$ grep -rn "time_constraints\|subject_constraints" tests/ domain/solver/
```

Risultato:
- `tests/test_solver_oracle.py` contiene commenti che menzionano i vecchi nomi di file
- `domain/solver/builders/__init__.py` importa i moduli (ora aggiornato)
- Nessun import diretto nei test stessi

**Conclusione**: I test raggiungono i builder solo attraverso `all_builders()` e il registro, non tramite import diretti. Nessuna modifica ai test è necessaria.

## Chiavi del registro

Le chiavi rimangono invariate:
- `MaxGapBuilder` registrato sotto `T.MAX_GAP_HOURS` (identico)
- `SameDayBuilder` registrato sotto `T.SAME_DAY_INCOMPATIBLE` (identico)

Verificato in `domain/solver/builders/time_presence.py` e `domain/solver/builders/subject_buckets.py` che il decoratore `@register(...)` rimane identico.

## Commit

```
b0df969 refactor(solver): i builder nel file del proprio pattern
```

Messaggio:
```
refactor(solver): i builder nel file del proprio pattern

time_constraints.py -> time_presence.py, subject_constraints.py ->
subject_buckets.py. Le chiavi del registro non cambiano. Prepara le ondate
3-6, dove quei file accolgono altri undici builder.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

## Autorevisione

### Completezza
- [x] File spostati con `git mv`
- [x] Docstring di modulo aggiornati
- [x] Import in `__init__.py` aggiornati
- [x] Nessun import nei test modificato (non necessario)
- [x] Suite eseguita

### Disciplina
- [x] Nessuna logica di builder cambiata
- [x] Nessun nuovo comportamento introdotto
- [x] Semplice riorganizzazione strutturale

### Test
- [x] Suite rimane a 189 test verdi
- [x] Nessun test aggiunto né rimosso

## Dubbi

Nessuno. Lo spostamento è meccanico, i test confermano continuità, e le chiavi del registro rimangono invariate.
