# Entità EDT — Vincoli

> Indisponibilità e vincoli orari docente: semantica dalla guida **confermata in
> UI** (2026-07-15). Restano da osservare i vincoli di materie, classi e aule.

## Ambito

Come EDT permette di dichiarare i vincoli che il motore di generazione deve
rispettare. Distinto dai **conflitti attesi del dataset Fermi** (quelli sono il
banco di prova del solver e stanno in
[`data/liceo-fermi/vincoli-attesi.md`](../../data/liceo-fermi/vincoli-attesi.md)).

## Indisponibilità e preferenze docente (guida + UI osservata 2026-07-15)

Si inseriscono in **Orario > Docenti > Indisponibilità e vincoli**, "dipingendo"
la griglia oraria con tre pennelli (frequenza *Settimanale* oppure *Settimane
Q1/Q2* — radio osservati in UI). Griglia osservata: lun–ven × 08h–18h (= i 50
slot del tasso `TOP`, vedi [docenti.md](docenti.md)), con una linea magenta alle
12h (⚠ probabile confine mattino/pomeriggio o fascia mensa):

| Pennello | Nome | Semantica per il piazzamento automatico |
|---|---|---|
| **Rosso** | Indisponibilità | **Mai violata.** Per i casi imperativi (giorno libero richiesto, servizio in altro istituto). |
| **Giallo** | Indisponibilità opzionale | Rispettata come una rossa, ma l'utente può **autorizzare EDT a ignorarle** per risolvere le attività scartate. Attenzione: l'esclusione è **globale** (tutte le gialle di tutti i docenti insieme) → la guida avverte di **non** usare il giallo per impegni improrogabili (part-time, completamento di servizio altrove). |
| **Verde** | Preferenza | Fascia in cui il docente *vorrebbe* lezione. EDT cerca di tenerne conto, **nessuna garanzia**. |

In più esistono i **vincoli orari** numerici, separati dalla griglia (la guida
li consiglia al posto di riempire la griglia di gialli). Catalogo osservato nel
pannello destro della stessa vista (2026-07-15; alcune etichette troncate a
destra dello schermo, ⚠ da completare):

| Vincolo | Parametri osservati |
|---|---|
| Distribuzione oraria `D` | Minimo `N` giorni a settimana con un minimo di `X` ⚠ |
| Massimo di ore di attività `M` | per Giornata / Mattino / Pomeriggio (default "Niente") |
| Massimo di ore di presenza `P` | `N` giorni alla settimana, presenza massima di ⚠ |
| Gestione Entrate / Uscite `E` | `N` giorni alla settimana "non iniziare prima delle…" + `N` giorni "non finire oltre le…" (le "entrate posticipate" della guida) |
| Giorni e ½ giornate libere `G` | Assegna `N` giornate libere + `N` ⚠ (cfr. FAQ "due mezze giornate libere") |
| Massimo di mezze giornate di lavoro | Mattino / Pomeriggio (default "Niente") + checkbox "Lavorare solo mezza giornata al giorno" |
| Preferenze di ottimizzazione | "Numero di ore di buco tollerate": **default `2`** (⚠ probabile sorgente della colonna `D.T.B.` = `2h00` dell'elenco docenti) |

Le lettere (`D`, `M`, `P`, `E`, `G`) sono i badge con cui EDT etichetta i
vincoli. Nota per il modello: **presenza ≠ attività** (la presenza include i
buchi) — EDT le vincola separatamente.

**Implicazione per il dataset Fermi:** gli spezzoni D06, D09, D15 (completamento
su altra scuola) vanno espressi col **rosso**, non col giallo.

**Implicazione per il nostro modello:** tre livelli di durezza (hard /
soft-trattata-come-hard-salvo-override-globale / desiderata) più vincoli di
conteggio (cardinalità per settimana), non solo maschere sulla griglia.

## Blocchi di ore consecutive — risolto

Non sono un vincolo separato: sono la **durata dell'attività**, fissata nello
spezzamento del servizio (doppio clic su `Nr attività` → numero/durata/frequenza
dei blocchi → Trasforma). Pista confermata dalla guida 📖 — la finestra parla
esplicitamente di "numero di blocchi". Vedi [attivita.md](attivita.md).

## Da osservare

Questa lista è il **cancello del solver**: finché non è chiusa, il prototipo resta
fermo (vedi [ADR-008](../decisioni.md)). Non vogliamo scoprire un tipo di vincolo
nuovo a modello già scritto.

- [ ] Completare le **etichette troncate** dei vincoli orari (pannello destro) e
      il nome del terzo pennello (⚠ presumibilmente "Preferenze", verde).
- [ ] **Vincoli di risorsa** (aula/laboratorio a occupazione limitata) — come si
      dichiara "1 classe alla volta" o "max 2 in parallelo". Vedi [aule.md](aule.md).
- [ ] **IRC vs. attività alternativa** — pista dalla guida 📖: **attività
      complessa / compresenza** (gruppi creati automaticamente da EDT, vedi
      [gruppi.md](gruppi.md)).
- [ ] Indisponibilità e vincoli di **classi** e **aule** (la guida ha schede
      analoghe a quelle dei docenti).

## Implicazioni (preliminari) per il nostro modello

Da definire una volta osservata la UI dei vincoli. Presumibilmente:

- vincoli di **disponibilità** per docente (e forse per aula/classe);
- vincoli di **contiguità/blocco** sulle ore di un corso;
- vincoli di **capacità simultanea** sulle risorse condivise.
