# Entità EDT — Discipline

## Cos'è

Raggruppamento delle materie affini (es. Matematica e Fisica → una disciplina
`MAF`). In EDT è una **tabella, non un enum**: ogni scuola la personalizza.

## Campi osservati nella UI

| Campo | Tipo | Note |
|---|---|---|
| Codice | testo | |
| Nome | testo | |

## 🔑 Il `Codice` della disciplina porta la classe di concorso

Osservato il 2026-07-26 nella base di esempio fornita con EDT. La colonna
`Disciplina` dell'elenco docenti mostra **codice + nome**, e i codici sono
**classi di concorso italiane reali**:

| Codice | Nome della disciplina |
|---|---|
| `A-01` | ARTE E IMMAGINE |
| `A-22` | LETTERE |
| `A-25` | LING. STRANIERE |
| `A-28` | MATE-SCIENZE |
| `A-30` | MUSICA |
| `A-49` | *(presente nei dati)* |
| `A-60` | TECNOLOGIA |
| `REL` | RELIGIONE |
| `SOST` | SOSTEGNO |

Sono le classi di concorso della scuola secondaria di I grado (D.P.R. 19/2016):
la base demo italiana di EDT è una scuola media, e chi l'ha costruita ha usato il
campo `Codice` **esattamente** per la classe di concorso.

⚠ **Ma EDT non le fornisce.** Verificato: i codici compaiono **solo come dato**
dentro `Esempio.edt`, non nei binari dell'installazione né in `TabellaSIDI.xml`
(che infatti non contiene classi di concorso, vedi
[nomenclatura-sidi.md](nomenclatura-sidi.md)). Non c'è nessuna tabella
ministeriale delle classi di concorso incorporata nel prodotto, nessuna
validazione, nessun campo dedicato.

**Conclusione precisa:** la classe di concorso non è un campo EDT, ma il campo
`Codice` della disciplina è il **posto dove EDT Italia si aspetta che la si
metta**. Non è né "campo nativo" né "pura estensione nostra": è una convenzione
d'uso, documentata dalla base di riferimento del produttore.

Questo raffina [ADR-002](../decisioni.md) senza ribaltarlo.

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
- Aggiungiamo la **mappatura disciplina → classe di concorso** (A-22, A-28…),
  che serve al SaaS sostituzioni: la normativa ragiona per classe di concorso, non
  per materia. Vedi [ADR-002](../decisioni.md).
- **Dove metterla.** La base di riferimento di EDT Italia la mette nel `Codice`
  della disciplina, uno-a-uno. Per una scuola media funziona; per un liceo no —
  Lettere copre A-11/A-12/A-13 a seconda di ordine e indirizzo. Quindi:
  manteniamo la relazione **molti-a-molti** come tabella a sé, e trattiamo il
  `Codice` come il campo da cui **importare** quando è valorizzato. Vedi il
  dataset in
  [`data/liceo-fermi/discipline.md`](../../data/liceo-fermi/discipline.md).
- **Non aspettarsi validazione da EDT.** Il prodotto non incorpora la tabella
  ministeriale delle classi di concorso: se la vogliamo verificata, la tabella la
  dobbiamo portare noi.

## Dataset di esempio

Le discipline concrete del Liceo Fermi (con la mappatura classe di concorso) sono in
[`data/liceo-fermi/discipline.md`](../../data/liceo-fermi/discipline.md).
