# Ri-review mirata — Task 11, giro di correzione 1

Lavori nel worktree `.claude/worktrees/modello-hard-completo` e **non ne esci**.
Test con `venv/bin/pytest`. **Non fare commit e non correggere il codice.**

Stato: **340 passed, 4 skipped** (gli stessi quattro skip della baseline).

Non è una review completa: il perimetro è **solo** ciò che il giro di
correzione ha toccato. Il rapporto di review precedente è già stato accettato e
i suoi finding sono chiusi — il tuo compito è verificare che le **correzioni**
non abbiano introdotto un difetto nuovo.

## Contesto

- `.superpowers/sdd/2026-08-24-modello-hard-completo/task-11-fix-brief.md` — i
  sei finding da chiudere.
- `progress.md`, in fondo le **Rulings 63-70**.
- `domain/analysis/checkers/subject_constraints.py` — il checker è la verità.

## Perché questa ri-review esiste

Al Task 10 il giro di correzione fu **esso stesso sbagliato**: la guardia
introdotta per riparare una vacuità si rivelò necessaria-ma-falsa, e lo si
scoprì solo misurando (Rulings 48, 51). Qui il giro 1 introduce **codice
algoritmico nuovo nel banco** (`_massimo_pacchetto`, ricerca esatta con
memoizzazione su bitmask) che **non ha alcun test proprio**, più una
dimostrazione di sussunzione scritta in docstring.

## I quattro punti, in ordine di rischio

### 1. `_massimo_pacchetto` è corretto? (rischio più alto)

Non ha test. È una ricerca esatta su `(indice, maschera di fasce occupate)` che
sceglie per ogni attività una fascia di partenza o la salta. Verifica per
enumerazione forza-bruta indipendente su casi piccoli costruiti a mano —
**scrivi la tua brute force, non riusare la sua ricorsione** — che restituisca
davvero il massimo, in particolare: attività di durata > 1, attività con
`respects_breaks`, mezze giornate di larghezza 1 e 2, insiemi vuoti.

⚠ Controlla anche una cosa che la ricorsione **non** sembra fare: le
collocazioni provengono da `_collocazioni`, che è indipendente dal giorno.
Impacchettare "nello stesso secchio in un giorno qualunque" è corretto solo se
tutte le attività possono stare nello **stesso** giorno. Verifica se questo
introduce un errore, e in quale direzione (generosa o stretta).

### 2. La dimostrazione di sussunzione è vera?

La docstring di `_derive_max_hours_subject` afferma che la guardia di
riempimento **sussume** le due guardie precedenti, con due passaggi:

- «se la capienza supera `param`, il totale della firma la supera per forza,
  perché la capienza è un sottoinsieme del totale»;
- «la capienza non può essere raggiunta da una sola attività, perché ogni
  attività compare già da sola nel proprio secchio nel testimone, quindi il suo
  stesso `param` la domina per costruzione».

Verificali entrambi contro il codice. **E verifica per misura**, non solo per
argomento: ricostruisci le due guardie vecchie e controlla su seed 1-20 che
nessuna riga passi la guardia nuova ma sarebbe stata scartata dalle vecchie. Se
ne trovi una, la sussunzione è falsa e le vecchie non andavano rimosse.

### 3. I due test nuovi discriminano davvero?

`test_max_hours_day_con_a_diverso_da_b_conta_solo_a` e la nuova versione di
`test_forbidden_sequence_con_a_uguale_b`. Riapplica **tu** le due mutazioni che
la review precedente aveva usato (sommare anche B quando A ≠ B; e
`if row.subject_a_id == row.subject_b_id and pb <= pa: continue`) e conferma che
i test falliscano. Poi verifica il caso simmetrico che il fix brief non
chiedeva: la mutazione `pb >= pa` (l'altro verso) fa fallire qualcosa?

Controlla anche che `test_adr018_forbidden_sequence_una_congelata_la_libera_evita`
non sia più byte-identico al gemello, e che eserciti davvero qualcosa che il
gemello non esercita.

### 4. La Minor 2 è chiusa nel modo richiesto?

L'assert su `KIND` doveva diventare **inevitabile**, non da ricordare. Verifica
che sia in `buckets()` e che una sottoclasse di `_Bucketed` senza `KIND` si
rompa davvero — e che `_check_kind` non sia rimasto da nessuna parte.

## Una discrepanza aperta, da chiudere se è cheap

Le due misure indipendenti della violabilità concordano sull'aggregato (20
righe, 4 inviolabili, la guardia ne esclude 2, ne restano 2) ma **discordano su
quale sia il residuo del seed 3**: la review dice classe 2 / materia 3, il giro
di correzione dice classe 1 / materia 3. L'ipotesi più probabile è una
convenzione di indicizzazione diversa fra due sonde usa-e-getta. Se puoi
chiuderla in poco, fallo; altrimenti dillo e lasciala aperta — non è una
decisione che dipende da questo.

## Cosa consegnare

Finding classificati **Critical / Important / Minor**, ognuno con: dove, perché
è un difetto, come si riproduce. Un sospetto chiuso con una misura vale quanto
un difetto trovato: dillo con i numeri.

In fondo, **«cosa non ho verificato»**. Non arrotondare.

Se crei sonde temporanee, rimuovile e conferma con `git status` e `git diff`.
