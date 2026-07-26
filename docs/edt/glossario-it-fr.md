# Glossario EDT — italiano ↔ francese ↔ inglese

> Fonte 📦: tabelle di lingua estratte da `EDT Monoposto.dll`. Le etichette sono
> blocchi XML in chiaro (`<chaine numero="…" cle="…">testo</chaine>`), sei lingue
> complete (IT, FR, EN, ES, NL, EU) **allineate per chiave**: la corrispondenza è
> esatta, non euristica. 69 888 stringhe per lingua.

## Perché serve

EDT è software francese tradotto. La traduzione italiana **non è biunivoca**: in
almeno un caso i termini si scambiano di livello, e in un altro una sigla italiana
traduce una parola francese diversa da quella che sembra. Leggere la UI italiana
senza questa tabella porta a modellare la cosa sbagliata.

La lingua **sorgente è il francese**: in caso di dubbio semantico, il francese è
più affidabile dell'italiano.

## ⛔ La trappola: gruppi, parti, suddivisioni

| Francese | **Italiano in UI** | Inglese | Schema di scambio |
|---|---|---|---|
| `partition` | **Suddivisione** | Partition | `@LibellePartition` |
| `partie` | **Gruppo** | Part | `PartieDeClasse` |
| `groupe` | **Raggruppamento** | Group | `Groupe` |
| `dédoublement` | **Sdoppiamento** | Splitting | — |

**"Gruppo" in italiano traduce `partie`, non `groupe`.** Prova, stessa chiave nelle
due lingue:

> IT `EDT crea, al bisogno, i gruppi e i raggruppamenti dello sdoppiamento.`
> FR `EDT va créer, si besoin, les parties et les groupes de dédoublement.`

Vedi [gruppi.md](gruppi.md). Nel nostro codice conviene usare i termini **inglesi**
(`partition` / `part` / `group`), che non sono ambigui.

## Entità e concetti

| Italiano | Francese | Inglese |
|---|---|---|
| Attività | `Cours` | Course |
| Lezione (dentro un'attività complessa) | `Séance` | Class meeting |
| Piano di studi | `MEF` | ETM |
| Materia | `Matière` | Subject |
| Disciplina | `Discipline` | Discipline |
| Fascia oraria | `Séquence` | Sequence |
| Sede | `Site` | Site |
| Docente coordinatore | `Professeur principal` | Homeroom teacher |
| Alunni inseriti | `Effectif` | Population |
| Gruppo di aule | `Groupe de salles` | Room group |

## Tempo e periodicità

| Italiano | Francese | Inglese |
|---|---|---|
| Quindicinale, `Q1` / `Q2` | `Quinzaine`, `Q1` / `Q2` | Fortnight, F1 / F2 |
| Ciclo alternato | `Cycle alterné` | Alternating cycle |
| Intervallo | `Récréation` | Recess |
| Mensa | `Demi-pension` | Half-board |
| Buco | `Trou` | Gap |
| Scarto | `Écart` | Differential |

## Piazzamento

| Italiano | Francese | Inglese |
|---|---|---|
| Piazzamento | `Placement` | Placement |
| Attività scartate | `échecs` | failures |
| Trova una soluzione… | `Lancer le résoluteur pas à pas…` | Launch the step-by-step solver |

## Colonne del docente — le sigle sciolte

| Sigla IT | Esteso IT | Francese |
|---|---|---|
| `Mh/s` | **Monte ore settimanale** | `App.` / `Apport` |
| `Occ.` | Occupazione | `Occupation` |
| `Occ. sett.` | Occupazione settimana tipo | `Occupation semaine type` |
| `Occ. ann.` | Occupazione annuale | `Occupation annuelle` |
| `Occ. prev.` | Occupazione previsionale | `Occupation prévisionnelle` |
| `Occ. simu.` | Occupazione simulata | — |
| `HS prev.` | Ore supplementari previsionali | `HSA prévisionnelles` |
| `D.T.B.` | **Durata tollerata dei buchi** | `Nombre d'Heures de Trous Tolérées` |
| `TOP` | Tasso di occupazione potenziale | `Taux d'occupation potentiel` |

**`Mh/s` non è un massimo**: è il *monte ore contrattuale*, e traduce il francese
`Apport` — la stessa parola che nello schema di scambio è l'elemento
`Professeur/Apport` con le durate in minuti per disciplina. Vedi
[docenti.md](docenti.md).

## ⛔ Una traduzione italiana che dice il **contrario** — 2026-07-26

Non è un'ambiguità: è un errore, e mi aveva indotto una conclusione sbagliata.

| Chiave | IT | FR |
|---|---|---|
| `FicEDT_ResoluteurPasAPas_RS_CheckInit` | `Memorizza le attività che saranno spostate` | **`Réinitialiser la famille des cours déplacés`** |

*Memorizzare* contro *reinizializzare*: significato opposto. La casella compare
anche nella finestra del piazzamento automatico, dove l'avevo documentata come
opzione di tracciabilità — lettura sbagliata, corretta in
[motore-risoluzione.md](motore-risoluzione.md).

**Regola operativa che ne discende: quando IT e FR divergono, vince il francese.**
L'italiano è una traduzione, e in qualche punto sbaglia.

## Falsi amici — 2026-07-26

| IT osservato | Sembra | È in realtà |
|---|---|---|
| **`Interclasse`** (col. `Int.`) | «trasversale alle classi» | **`Récréation`** = l'intervallo/ricreazione |
| **`Aree mobile`** | vincolo o risorsa di spazio | **`Mobile Teachers Webspace`** — il portale mobile di **PRONOTE**, fuori scope |
| **`punti`** / `pesi` (alleggerimenti) | un punteggio del motore | l'unità del **peso didattico**: `points` è tradotto `pesi` |
| **`P.P.`** | «Parte Principale» | `Fractionnable` = **Proprietà di Piazzamento** (fascia fissa/variabile) |

⚠ Su `P.P.` c'è un caso doppio: **non** sono due colonne `P.P.` e `P.F.` — è la
stessa colonna in due lingue (IT/FR `P.P.`, EN `P.F.`). E `Type_Contrainte_RS_LegendePP`
è un `PP` ancora diverso: `Peso didatt.`

⚠ E `intervallo` in italiano traduce **due** parole francesi distinte: `récréation`
(la pausa d'istituto) e `interclasse`. Il francese le separa, l'italiano no.

Nota terminologica utile: l'italiano distingue **frazionare** (spezzare sui
*periodi*) da **sezionare** (spezzare la *durata*, lo spezzamento padre/figlio). Il
francese usa `fractionner` per il primo. Qui, per una volta, l'italiano è più
preciso.

## ⚠ Due ambiguità da tenere a mente

**`Spec.` significa due cose diverse in due griglie diverse.**

| Dove | IT | FR | Significato |
|---|---|---|---|
| Scheda del **piano di studi** | `Spec.` | `Spéc.` | **Specializzazione** (vera; = `Mef/@Specialite` dello schema) |
| Liste **Servizi docenti / Servizi classi** | `Spec.` | `Mod.` | **Modalità di scelta** (`Modalité d'élection`) |

La seconda è quasi certamente una svista del traduttore italiano. Prima di
attribuire un significato a una colonna `Spec.`, guardare **in quale griglia** si
trova.

**`Statuto` idem.** `Chaines_EdT_RS_WinColonStaLong` traduce FR `Statut` → IT
`Statuto` (lo statuto giuridico: titolare/supplente/provvisorio), ma
`WinAffVSProfesseurAffectation` traduce FR `Affectation` → IT `Statuto` in almeno
un'altra griglia, dove significa **assegnazione**. ⚠ Inferenza dal nome della
chiave, da confermare in UI.

## Come interrogare l'estrazione

Le stringhe allineate stanno in un TSV a tre colonne (chiave · IT · FR · EN)
rigenerabile dalla DLL. Il metodo: le tabelle di lingua sono blocchi UTF-8 in
chiaro dentro `EDT Monoposto.dll`, estraibili con una regex su
`<chaine numero="…" cle="…">`.

Conviene **cercare a partire dal francese**, che è la lingua sorgente e non ha le
ambiguità introdotte dalla traduzione.
