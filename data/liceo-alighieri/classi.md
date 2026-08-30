# Classi

Dodici classi, tre sezioni, due indirizzi.

| Classe | Indirizzo | Anno | Sede | Alunni previsti | Aula preferenziale |
|---|---|---:|---|---:|---|
| 1A–5A | Scientifico | 1–5 | Centrale | 26 | A101–A105 |
| 1B–5B | Classico | 1–5 | Centrale | 22 | B101–B105 |
| 1C | Scientifico | 1 | Succursale | 24 | C101 |
| 2C | Scientifico | 2 | Succursale | 24 | C102 |

## Perché esiste la sezione C

Per la **sede**. Senza una sezione staccata non ci sono due sedi, e senza due
sedi `structural:site_transition` resta muto — come sul Fermi, che ha zero
righe `Site`. Un biennio in succursale è anche la forma in cui le scuole
italiane le sedi le hanno davvero: le prime e le seconde stanno fuori, il
triennio sta al centro.

⚠ E la C è **piccola apposta**: due classi su dodici. Una succursale che
contenesse metà scuola darebbe due problemi quasi indipendenti; con due classi
le cattedre che attraversano sono poche e nominate ([sedi.md](sedi.md)), che è
la condizione in cui un vincolo di transizione morde su qualcuno invece di
pesare su tutti.

## Dove andrà il raggruppamento trasversale

Su **1A e 1B**, alla centrale: i livelli di inglese delle due prime che si
mescolano, che è il modo in cui le scuole li fanno davvero (ondata 2). È il
caso che *rompe la decomposizione per classe* — la conseguenza dichiarata da
[ADR-013](../../docs/decisioni.md) e che nessun dataset ha mai messo alla
prova.

⚠ **E non attraversa le sedi, deliberatamente.** Un raggruppamento fra 1A e 1C
sarebbe più spettacolare e sarebbe un errore di anagrafica: gli alunni delle
due classi dovrebbero stare nello stesso posto alla stessa ora, in due edifici
diversi. Un banco che chiedesse l'impossibile misurerebbe la propria
incoerenza, non il motore.

## `expected_students`

Dichiarato su tutte e dodici (`N.Alu` di EDT): è il dato con cui lavora
`eccedenza_capienza`, il terzo livello della catena delle aule — **criterio e
non vincolo**, come in EDT. Le aule della sezione B sono da 24 posti per 22
alunni, quelle della A da 28 per 26: margine stretto ma sufficiente, così che
il criterio abbia qualcosa da misurare senza che nulla lo forzi.

⚠ `max_weekly_weight_per_student` resta `NULL` su tutte: lo accende l'ondata 5,
con i tetti d'istituto.
