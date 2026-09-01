# orariogen — traslocato dentro Aurora

**Il generatore di orari scolastici non si sviluppa più qui.** Dal 2026-09-01
vive dentro **`Mactywd/aurora`**, il gestionale di sostituzioni per cui era
stato pensato, come app Django `orario`.

| cosa | dove, adesso |
|---|---|
| il codice (modelli, analisi, solver, comandi) | `backend/orario/` |
| i test e i due banchi (Fermi, Alighieri) | `backend/orario/tests/` |
| i documenti: EDT, ADR, todo, changelog, dataset | `docs/orario/` |
| lo stato corrente e le convenzioni | `backend/orario/CLAUDE.md` |

## Perché

Due decisioni, tutt'e due in `docs/orario/decisioni.md` di Aurora.

**ADR-027** (2026-08-31) decide che il generatore è un **modulo di Aurora**: i
dati d'ingresso sono dati di Aurora, il calcolo è un lavoro e non una
richiesta, e l'uscita è la `ScheduleEntry` che il motore delle sostituzioni già
legge — non un secondo orario accanto.

**ADR-032** (2026-09-01) decide che allora il codice ci **entra**, invece di
restare un pacchetto installabile. Il motivo è uno solo e non ammette
sfumature: ADR-027 vuole una chiave esterna verso la `School`, e una FK
ordinaria si scrive solo fra due app della stessa installazione. Un pacchetto
la comprerebbe con una `settings.ORARIO_SCHOOL_MODEL` sul modello di
`AUTH_USER_MODEL`, che però funziona perché `User` è dichiarato `swappable`:
senza, le migrazioni congelano `to='api.school'` e il pacchetto smette di
svilupparsi da solo — cioè perde l'unico motivo per cui lo si teneva separato.

E i **documenti sono andati dietro al codice** per la stessa ragione per cui il
codice è andato dentro Aurora: sono la parte che spiega *perché* è così. Un
reverse engineering di EDT separato dal generatore che ne discende è un
archivio, non una documentazione.

## Cosa resta qui

La **storia**: ogni commit fino al trasloco, che è dove sta il racconto di come
il modello di dominio, il solver e i due banchi sono stati costruiti. E
`.superpowers/sdd/`, gli artefatti di lavoro dei pezzi finiti, che Aurora non
traccia.

⚠ **Non si sviluppa più su questo repository.** Due copie dello stesso codice
divergono, ed è alla lettera l'accumulo di versioni che le convenzioni di
questo progetto hanno sempre vietato.
