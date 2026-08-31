# Entità EDT — Piani di studi

## Cos'è

Il **piano di studi** è il curriculum/indirizzo (es. Liceo Scientifico ordinario):
il livello di raggruppamento *sopra* le classi. È il posto naturale dove agganciare
il quadro orario (monte ore per materia) e i default d'effettivo.

## Campi osservati nella UI

| Campo | Tipo | Note |
|---|---|---|
| Nome | testo (≤ 40 car.) | **Obbligatorio.** La denominazione estesa. |
| Piano di studi | testo (≤ 6 car.) | **Obbligatorio.** La **sigla** del piano (è questo il codice corto, non "Nome" — invertito rispetto al pattern Codice/Nome di discipline e materie). |
| Alunni inseriti | numero | **Calcolato** (confermato: `0` su tutti i piani appena creati, senza input). Conteggio degli alunni collegati al piano. |
| Livello | enum | Obbligatorio. Valori osservati: **primo, secondo, terzo, quarto, quinto** = l'**anno di corso**. Quindi un piano di studi = indirizzo × anno (es. "Scientifico, terzo anno"), non l'indirizzo intero. |
| Al./Cl. | numero | Tooltip: *"numero alunni atteso per classe per il piano di studio"*. **Default d'effettivo per le classi del piano** → altro livello della cascata (piano → classe), come `Al./Rid.` per le materie ([ADR-003](../decisioni.md)). |
| Spec. | ? | "Specializzazione". Semantica da osservare. |

## Implicazioni per il nostro modello

- Entità `study_plan` sopra la classe: le classi puntano al piano; il quadro orario
  (materia × ore settimanali) appartiene al piano, non alla singola classe.
- `Al./Cl.` = default nullable d'effettivo atteso, ereditato dalle classi
  (cascata, `NULL` = eredita).
- Il piano è **indirizzo × anno** (Livello = primo…quinto): la granularità giusta
  per il quadro orario, che al Fermi cambia fra biennio e triennio
  ([classi.md](classi.md)). Nel nostro schema: `study_plan(track, year)` con il
  quadro orario appeso al piano.

## I servizi — il quadro orario del piano

Selezionando un piano si apre il pannello **"Servizi"** (`<Piano> – Servizi`): qui
si risponde alla domanda "dove sta il quadro orario". Un **servizio** è una riga
materia × ore appartenente al piano di studi. Colonne osservate (tooltip letterali,
valori dalla compilazione di SCI1, 2026-07-09):

| Colonna | Tooltip / semantica | Osservato su SCI1 |
|---|---|---|
| A | *"Stato di attivazione del servizio"* | pallino verde (attivo). Il flag "Visualizza i servizi inattivi" filtra i disattivati. |
| Materia (Nome, Codice) | FK → Materie | |
| Disciplina | derivata dalla materia (mostrata `Nome (COD)`) | non si inserisce |
| Alu. | *"Numero di alunni del piano di studi che segue la materia"* | `-` finché non ci sono alunni (coerente con "Alunni inseriti" calcolato) |
| Coeff. | *"Coefficiente del servizio"* | default **`60/60`** — peso della durata (minuti conteggiati / minuti reali?), da approfondire |
| MS | *"Modalità di scelta del servizio"* | vuoto — probabile rilevante per materie opzionali/a scelta |
| Istituto: H/Classe | **ore settimanali per classe** — il monte ore del quadro orario | input (`4h00`…) |
| Istituto: Ridotto | *"Durata con alunni ridotti"* | vuoto |
| Istituto: Sdop. | *"Durata con alunni sdoppiati"* | vuoto — **quota ore in sdoppiamento**: i gruppi si dichiarano qui ([gruppi.md](gruppi.md)) |
| Istituto: Alu./… | *"Numero di alunni ridotto del servizio"* | **`15` su tutte le righe, mai digitato** → è l'`Al./Rid.` delle materie che **eredita in cascata** fin dentro il servizio ([ADR-003](../decisioni.md)) |
| Istituto: H/Al. | *"Durata per alunno"* | = H/Classe quando non c'è sdoppiamento. 🔑 **La quantità dell'alunno è una colonna distinta da quella della classe**, ed è la distinzione che mancava al nostro `Service`: la copertura confrontava un atteso per-alunno contro `class_minutes` ([ADR-020](../decisioni.md)) |

#### 👁 La stessa griglia sulla base del produttore (2026-08-29)

Riletta sulla base demo, che è una **secondaria di primo grado italiana** — quattro
piani `1° / 2° / 3° TEMPO NORMALE` e `3° TEMPO PROLUNGATO`, materie e classi di
concorso italiane (`A-60`, `A-49`, `A-30`, `A-28`, `A-22`, `A-25`, `A-01`, `REL`),
`30h00` di totale sul primo. Ogni colonna coincide con la tabella qui sopra,
inclusi il `Coeff. 60/60` e l'`Alu./… 15` mai digitato: la cascata di
[ADR-003](../decisioni.md) si comporta identica su due basi diverse.

🔑 **E `MS` è vuota anche lì — sulla riga `RELIGIONE` compresa.** Il piano porta
`RELIGIONE / REL / RELIGIONE (REL) / Alu. 390 / H/Classe 1h00 / H/Al. 1h00`: un
servizio ordinario dovuto da **tutti** i 390 alunni del piano, senza alcuna
alternativa dichiarata e senza modalità di scelta. Anche `Ridotto` e `Sdop.` sono
vuote su tutte le righe.

Due conseguenze, e la seconda pesa:

- **O3 non è osservabile, solo sperimentabile**: nessuna delle due basi che
  abbiamo compila `Ridotto`/`Sdop.`, quindi «come nascono i gruppi» si vede solo
  compilandole.
- **EDT ha il campo, non il dato.** La colonna `MS` esiste e il tooltip la
  conferma (*«Modalità di scelta del servizio»*), ma la base di riferimento del
  produttore **non modella affatto** l'alternativa a IRC. Vedi l'emendamento ad
  [ADR-020](../decisioni.md).

Il monte ore è quindi **tripartito per servizio**: `H/Classe` (classe intera) +
`Ridotto` (effettivo ridotto) + `Sdop.` (sdoppiata in gruppi). "Totale delle ore di
servizio" somma la colonna: per il Fermi **27h00 al biennio (verificato su SCI1)**,
30 atteso al triennio.

> **Tripartizione confermata 📦.** Lo schema di scambio ufficiale dichiara
> esattamente tre durate per la coppia (piano, materia):
> `Mef/Matiere/@DureeMinutesClasse`, `@DureeMinutesReduite`,
> `@DureeMinutesDedoublee`. Le colonne `H/Classe`, `Ridotto` e `Sdop.` sono la resa
> in UI di questi tre attributi — l'inferenza fatta qui il 2026-07-09
> era corretta. Vedi [schema-scambio.md](schema-scambio.md).
>
> Lo schema conferma anche la **chiave del piano**: `Mef` è identificato da
> `Formation` + `Specialite` ("*Formation+Specialite constituent la clé unique*"),
> cioè indirizzo × anno, come dedotto dal campo Livello.

> ⚠ **Attenzione, `Spec.` è ambiguo** 📦. Esistono **due** colonne italiane
> abbreviate `Spec.`, con origini diverse:
>
> | Dove | IT | FR | Significato |
> |---|---|---|---|
> | Scheda del **piano di studi** | `Spec.` | `Spéc.` | **Specializzazione** — quella vera, = `Mef/@Specialite` |
> | Liste **Servizi docenti / Servizi classi** | `Spec.` | `Mod.` | **Modalità di scelta** (`Modalité d'élection`) |
>
> La seconda è quasi certamente una svista del traduttore italiano. Il `Spec.`
> della tabella qui sopra — che è sulla scheda del piano — è la
> **specializzazione**. Ma prima di attribuire un significato a una colonna
> `Spec.` incontrata altrove, guardare in quale griglia si trova. Vedi
> [glossario-it-fr.md](glossario-it-fr.md).

## Le colonne dei servizi — sciolte 📦

| Colonna | Esteso IT | FR |
|---|---|---|
| `A` | Stato di attivazione | — |
| `Coeff.` | Coefficiente | `Pondération` |
| `MS` | **Modalità di scelta** | `Modalité d'élection` — otto codici più il vuoto, § qui sotto |
| `Ridotto` | Durata con alunni ridotti | — |
| `Sdop.` | Durata con alunni sdoppiati | — |

### 👁 `MS` — gli otto codici, con la loro semantica

Tendina aperta in UI il 2026-08-29, e le etichette complete dalla famiglia
`Type_ModaliteDElection` (📦). ⚠ **Sono otto più il vuoto, non sette**, e la voce
che mancava è quella che conta.

| Codice | IT | Spiegazione (IT) | FR |
|---|---|---|---|
| *(vuoto)* | `Senza specifica` | — | `Aucune modalité` |
| **`S`** | `Senza` | **Percorso curricolare** | **`Tronc commun`** |
| `O` | `Obbligatoria` | Opzione obbligatoria | `Option obligatoire` |
| `F` | `Facoltativa` | Opzione facoltativa | `Option facultative` |
| `N` | `Normale` | Opzione neutra (`O` o `F`) | `Option neutre` |
| `X` | `Extra` | Opzione facoltativa in forma di aiuto personalizzato | `Option facultative à caractère d'aide personnalisée` |
| `L` | `Locale` | Insegnamento locale | `Ajout académique au programme` |
| `R` | `Religiosa` | **Insegnamento religioso** | `Enseignement religieux` |
| `D` | `DNL` | Disciplina Non Linguistica | `Discipline Non Linguistique` |

🔑 **L'asse di `MS` è *«tronco comune oppure opzione»*.** `S` non è «senza
valore» — è `Tronc commun`, cioè la riga che **tutti** seguono; tutte le altre
sono forme di opzione, con `R` a nominare il caso religioso. È esattamente il
dato che [ADR-020](../decisioni.md) cercava… su **un** asse solo.

⚠ Perché `MS` **non** dice quali opzioni siano alternative *fra loro*. Sa
distinguere «dovuta da tutti» da «opzione», non «di queste tre se ne segue una».
Il nostro `Service.election_group` risponde alla seconda domanda e tace sulla
prima: i due meccanismi sono **complementari**, non uno la traduzione dell'altro.

✅ **E dal 2026-08-31 abbiamo anche il primo asse** ([ADR-026](../decisioni.md)):
`Service.elective`, un booleano — `S` da una parte, gli altri sette codici
dall'altra. Non è l'enumerazione: è la **partizione** che l'enumerazione
descrive, che è tutto ciò di cui il predicato di copertura ha bisogno e tutto
ciò che si può copiare onestamente da un campo di cui nessun comportamento è
mai stato osservato. Con esso un'opzione **fuori** da ogni gruppo — un corso
che si sceglie o no — smette di far risultare debitore chi non l'ha scelta:
*zero o tutta*.

⚠ Due correzioni a quanto era scritto qui: `L` è **`Locale`** e non
«Accademica» — il francese `académique` è l'aggettivo di *académie*, la
circoscrizione scolastica, quindi `Ajout académique au programme` è
un'**aggiunta locale al programma** e non qualcosa di accademico. Falso amico,
→ [glossario-it-fr.md](glossario-it-fr.md). E il codice `S` mancava del tutto.

`Coeff.` = FR `Pondération`, che nello schema di scambio è l'elemento
`Cours/Ponderation`: è quindi la stessa quantità che scende in cascata fino
all'attività ([attivita.md](attivita.md)).

Il motore conosce **quattro** durate per il servizio previsionale, non tre:
`ColDureeEleve`, `ColDureeClasseEntiere`, `ColDureeReduite`, `ColDureeDedoublee` —
che corrispondono esattamente alle colonne `H/Al.`, `H/Classe`, `Ridotto`,
`Sdop.` osservate in UI. L'enumerazione `TypeGenreDureePrev` ne distingue tre
(`gdpClasse`, `gdpDedoublee`, `gdpReduite`): `H/Al.` è derivata, non un genere a
sé. Coerente con lo schema di scambio, che ne esporta tre.

## Aperto / da osservare

- Semantica fine di **Coeff.**: quando si usa un valore ≠ `60/60`? (è la
  `Pondération` del formato di scambio).
- ~~I sette codici di **MS**~~ — **chiuso il 2026-08-31**, e la risposta è che
  l'enumerazione **non si copia**. I nomi si conoscono (📦, vedi la tabella qui
  sopra), il comportamento no, e non è osservabile: la colonna è vuota su ogni
  riga di entrambe le basi. Ciò che si copia è la **partizione** — tronco
  comune contro opzione — e sta in `Service.elective`
  ([ADR-026](../decisioni.md)). L'esperimento residuo (compilare `MS = R` e
  guardare se il piazzamento cambia) resta possibile ma è sceso di priorità: un
  campo che il produttore non compila nemmeno nella propria base difficilmente
  muove il motore.
- Cosa comporta un servizio **inattivo**.
- Compilare **Ridotto/Sdop.** su un servizio (es. ING) per osservare come nascono i
  gruppi → [gruppi.md](gruppi.md).
