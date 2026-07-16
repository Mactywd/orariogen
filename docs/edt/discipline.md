# Entità EDT — Discipline

## Cos'è

Raggruppamento delle materie affini (es. Matematica e Fisica → una disciplina
`MAF`). In EDT è una **tabella, non un enum**: ogni scuola la personalizza.

## Campi osservati nella UI

| Campo | Tipo | Note |
|---|---|---|
| Codice | testo | |
| Nome | testo | |

> Non abbiamo (ancora) visto in EDT un campo "classe di concorso" sulla
> disciplina. Il mapping alle classi di concorso è **nostra estensione** (vedi
> sotto), non un campo EDT osservato. Da confermare se EDT lo esponga.

## Semantica dedotta

- Le materie puntano alla disciplina con una FK (una disciplina raggruppa più
  materie).
- Il raggruppamento è editoriale/organizzativo della scuola, quindi va trattato
  come dato, non come costante di dominio.

## ⚠️ Collisione di codici materia/disciplina

`MOT` esiste sia come **codice materia** (Scienze motorie) sia come **codice
disciplina** (Scienze motorie). In EDT non è un problema: sono tabelle distinte con
spazi di codici separati.

Implicazione: se il nostro schema prevedesse uno spazio di codici **unico** per
materie e discipline, servirebbe un prefisso di disambiguazione (`M-MOT` per la
materia, `D-MOT` per la disciplina). Meglio evitare uno spazio unico e mantenere,
come EDT, tabelle separate.

## Implicazioni per il nostro modello

- `discipline` è una **tabella** con FK in arrivo da `materie`, non un enum.
  Vedi [ADR-001](../decisioni.md).
- Aggiungiamo la **mappatura disciplina → classe di concorso** (A011, A027…). Non è
  un campo EDT: è ciò che serve al SaaS sostituzioni, la cui normativa ragiona per
  classe di concorso e non per materia. Vedi [ADR-002](../decisioni.md).
- La relazione disciplina ↔ classe di concorso può essere molti-a-molti (es. Lettere
  copre A011/A013), quindi non è un semplice campo scalare — vedi il dataset in
  [`data/liceo-fermi/discipline.md`](../../data/liceo-fermi/discipline.md).

## Dataset di esempio

Le discipline concrete del Liceo Fermi (con la mappatura classe di concorso) sono in
[`data/liceo-fermi/discipline.md`](../../data/liceo-fermi/discipline.md).
