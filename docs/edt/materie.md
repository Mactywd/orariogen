# Entità EDT — Materie

## Cos'è

La singola materia di insegnamento (Italiano, Matematica…). Punta a una
[disciplina](discipline.md).

## Campi osservati nella UI

| Campo | Tipo | Note |
|---|---|---|
| Codice | testo | |
| Nome | testo | |
| Disciplina | FK → Discipline | |
| Al./Rid. | intero | Tooltip letterale: *"Numero ridotto di alunni della materia"*. Default **15**. |

## Il campo `Al./Rid.` — cosa NON è

Il campo `Al./Rid.` **non è un flag** (classe intera vs. ridotta) e **non è un
effettivo** (quanti alunni ci sono davvero). È un **massimo**: il tetto che EDT
verifica contro la capienza dell'aula quando il corso è svolto a effettivo ridotto.

> **Errore commesso e corretto.** All'inizio FIS e SCI erano state impostate a 13
> ("metà di 26 alunni"). Sbagliato: quello è ragionare sull'*effettivo*, non sul
> *massimo*. Un tetto a 13 si romperebbe con una classe da 28 iscritti. Il valore
> corretto è il massimo ammesso, non la metà stimata della classe reale.

## 🔑 La cascata di default

Il default 15 di `Al./Rid.` non è isolato: è un livello di una **catena di
ereditarietà**.

Schermata di configurazione globale di EDT:

> *"Inserite il numero massimo di alunni per struttura che EDT dovrà applicare"*
> - a classe intera: **30** (default)
> - a numero di alunni ridotto: **15** (default)

```
impostazione globale   →   campo Al./Rid. della materia   →   corso concreto
     (30 / 15)                 (override per materia)            (valore effettivo)
```

Ogni livello eredita da quello sopra finché qualcuno non lo sovrascrive. Nel dataset
Fermi tutte le materie hanno `Al./Rid. = 15`, cioè **tutte ereditano** dal default
globale: nessun override deliberato.

## Implicazioni per il nostro modello

- `NULL` significa **"eredita"**. Non materializzare i default nelle righe: se
  `max_alunni` fosse una colonna obbligatoria su ogni corso, avremmo ~288 righe che
  ripetono "30" e nessun modo di distinguere le scelte deliberate dalle inerzie.
  La cascata si risolve a runtime. Vedi [ADR-003](../decisioni.md).
- `Al./Rid.` va modellato come **tetto massimo nullable**, non come flag né come
  effettivo. Vedi [ADR-005](../decisioni.md).
- **Ipotesi da verificare**: quasi tutti i campi di EDT funzionano a cascata.
  Esistono per essere lasciati vuoti. Da confermare su campi diversi da `Al./Rid.`
  (vedi *Aperto* in [CLAUDE.md](../../CLAUDE.md)).

## Dataset di esempio

Materie del Liceo Fermi e monte ore per livello:
[`data/liceo-fermi/materie.md`](../../data/liceo-fermi/materie.md) e
[`data/liceo-fermi/classi.md`](../../data/liceo-fermi/classi.md).
