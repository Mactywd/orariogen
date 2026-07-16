# Entità EDT — Aule

## Cos'è

Gli spazi fisici in cui si svolgono i corsi: aule ordinarie, laboratori, palestra,
aula magna.

## Campi osservati nella UI

> Da completare campo per campo sulla scheda "Aula" di EDT. Attributi emersi
> dall'inserimento:

| Attributo | Note |
|---|---|
| Tipo | aula ordinaria, laboratorio, palestra, aula magna |
| Capienza | numero massimo di alunni |
| Vincolo di occupazione | quante classi contemporaneamente (1 alla volta; max 2 in parallelo; nessun limite) |

## Semantica dedotta

- La **capienza** è il tetto di alunni dello spazio; va confrontata col massimo di
  alunni del corso (vedi il campo [`Al./Rid.`](materie.md) e la cascata di default).
- Il **vincolo di occupazione** è distinto dalla capienza: la palestra ha capienza
  60 ma regge **2 classi in parallelo**; i laboratori ospitano **1 classe alla
  volta**. È un vincolo di risorsa condivisa per il solver.
- Alcuni corsi **richiedono un tipo d'aula specifico**: FIS/SCI vanno prenotati in
  laboratorio, DIS in aula disegno, MOT in palestra. Questo lega materia → tipo aula.

## Risorsa contesa (nota per il solver)

La palestra regge 2 classi, ma il docente di MOT (D17) è **uno solo**: di fatto la
palestra è mono-classe finché c'è un solo docente. Idem per l'aula disegno con D16.
La capienza dell'aula non è il collo di bottiglia: lo è il docente. Vedi
[`data/liceo-fermi/vincoli-attesi.md`](../../data/liceo-fermi/vincoli-attesi.md).

## Implicazioni per il nostro modello

- L'aula ha `tipo`, `capienza` e un vincolo di **occupazione simultanea** (quante
  classi in parallelo).
- Serve una relazione **materia → tipo d'aula richiesto** (o corso → aula ammessa)
  per instradare i corsi verso gli spazi giusti.

## Dataset di esempio

Le aule del Liceo Fermi:
[`data/liceo-fermi/aule.md`](../../data/liceo-fermi/aule.md).
