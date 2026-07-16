# Entità EDT — Gruppi

> **Stub.** Sappiamo che i gruppi esistono e perché servono; la loro modellazione
> concreta in EDT è ancora **da osservare**.

## Cos'è

Un **gruppo** è un sottoinsieme di alunni trattato come unità di orario distinta
dalla classe intera. Serve a rappresentare:

- **sdoppiamenti** (la classe si divide, es. su una lingua a effettivo ridotto);
- **corsi a effettivo ridotto** in generale;
- verosimilmente la divisione **IRC vs. attività alternativa** (da confermare).

## Perché è un'entità distinta dalla classe

L'ipotesi "una classe = un blocco monolitico" è falsa. Il campo
[`Al./Rid.`](materie.md) (numero ridotto di alunni della materia) **non ha dove
appoggiarsi** se il gruppo non esiste: si applica a un gruppo, non alla classe
intera. Vedi [ADR-004](../decisioni.md).

## Dalla guida ufficiale 📖 (2026-07-15, UI da osservare)

La guida (scheda *"Perché in genere non è necessario creare i gruppi e i
raggruppamenti?"*) ribalta l'aspettativa: gruppi e raggruppamenti **non si
creano a mano**. Quando si crea un'**attività complessa** (più lezioni
collegate/allineate), EDT genera automaticamente i raggruppamenti, le
suddivisioni e i gruppi necessari; crearli prima produce solo ridondanza.

Definizioni dalla guida:

- **Attività semplice**: attività indipendente, un docente + una classe intera.
- **Attività complessa**: più lezioni collegate fra loro (per sovrapposizione o
  successione); il collegamento si decide nel "dettaglio" dell'attività.
  Consiglio della guida: al piazzamento automatico, prima le complesse (più
  vincolate), poi le semplici.
- Un'**attività** in generale raggruppa tutte le risorse impegnate nella stessa
  fascia oraria (più docenti, più classi, più aule).

Conseguenza per il modello: il gruppo in EDT è un **derivato dell'attività
complessa**, non un'anagrafica compilata a monte. Lo sdoppiamento si esprime
creando le lezioni allineate, e i gruppi ne discendono.

## Da verificare

- [ ] Come EDT modella concretamente i gruppi/sdoppiamenti. Esperimento previsto:
      creare un corso ING a effettivo ridotto con **due gruppi paralleli** e
      osservare come vengono rappresentati (entità propria? attributo del corso?
      legame classe↔gruppo↔docente↔aula?).
- [ ] Gestione IRC vs. attività alternativa come caso particolare di gruppo.
- [ ] Decisione di scope: **supportare gli sdoppiamenti in v1** o dichiararli fuori
      scope. Vedi *Aperto* in [CLAUDE.md](../../CLAUDE.md).

## Implicazioni (preliminari) per il nostro modello

- Prevedere un'entità `group` collegata alla classe (uno-a-molti), a cui agganciare
  assegnazioni docente, aula e il massimo alunni.
- Le assegnazioni docente ([docenti.md](docenti.md)) devono poter puntare a un
  gruppo, non solo a una classe intera.
