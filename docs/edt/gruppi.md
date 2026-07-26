# Entità EDT — Gruppi

> Struttura ricavata dallo schema di scambio e dai dati (📦), con **conferma in
> UI** il 2026-07-26: il pannello di composizione dell'attività elenca
> `Raggruppamenti` e `Gruppi` come **due righe distinte**, allo stesso livello di
> `Classi`, `Personale`, `Aule` e `Materiali`. I due livelli esistono davvero e
> non sono sinonimi — il che regge l'intera sezione sull'inversione
> terminologica qui sotto.

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

## ⛔ Prima di tutto: l'inversione terminologica IT ↔ FR 📦

**La terminologia italiana di EDT non ricalca quella francese, e i termini si
scambiano di livello.** Estratto dalle tabelle di lingua del prodotto (69 888
stringhe italiane allineate per chiave alle francesi):

| Francese (lingua sorgente) | **Italiano in UI** | Inglese | Elemento nello schema 📦 |
|---|---|---|---|
| `partition` | **Suddivisione** | Partition | `@LibellePartition` |
| `partie` | **Gruppo** | Part | `PartieDeClasse` |
| `groupe` | **Raggruppamento** | Group | `Groupe` |
| `dédoublement` | **Sdoppiamento** | Splitting | — |

Prova letterale, dalla stessa chiave nelle due lingue:

> IT `EDT crea, al bisogno, i gruppi e i raggruppamenti dello sdoppiamento.`
> FR `EDT va créer, si besoin, les parties et les groupes de dédoublement.`

Cioè: **"gruppo" in italiano traduce `partie`, non `groupe`.** Quello che la
guida francese e lo schema XSD chiamano `Groupe` in UI italiana si chiama
**raggruppamento**.

**Conseguenza per questo documento e per il nostro modello.** Il "gruppo" di cui
parla questo file — e [ADR-004](../decisioni.md) — è concettualmente la
**parte di classe** (`PartieDeClasse`), non il `Groupe` dello schema. Sono due
livelli diversi e il nostro schema deve tenerli separati con nomi inequivocabili.
Dato che il codice va in inglese (convenzione di progetto), la via d'uscita è
usare i termini **inglesi**, che non sono ambigui: `partition` / `part` / `group`.

Vedi il [glossario IT ↔ FR](glossario-it-fr.md) per il resto delle
corrispondenze.

## La struttura, dallo schema di scambio 📦

Lo schema ufficiale ([schema-scambio.md](schema-scambio.md)) dichiara il
meccanismo, che è **a due stadi** (nomi dello schema, francesi):

```
Classe ──partiziona──> PartieDeClasse ──compone──> Groupe
                       @Nom                        @Nom
                       @LibellePartition           Classe          (0..N) + @LibellePartition
                                                   PartieDeClasse  (0..N)
```

1. Una **classe si partiziona**: nasce una *partizione* nominata
   (`@LibellePartition`) le cui componenti sono le **parti di classe**
   (`PartieDeClasse`).
2. Un **gruppo si compone** di parti. E `Groupe/Classe` ha cardinalità **`0..N`**,
   con l'annotazione *"Libelle de la partition de la classe à l'origine du
   groupe"*.

**Il gruppo può quindi attraversare più classi.** Questo smentisce l'ipotesi
"gruppo uno-a-molti con la classe" che stava qui sotto: la relazione è
molti-a-molti, mediata dalle parti. È il caso reale delle lingue o delle
opzionali su classi parallele.

Terzo pezzo, che chiude la catena descritta dalla guida 📖: lo schema dichiara
testualmente che l'**allineamento** genera l'attività complessa —

> *«tous les cours ayant le même Ident d'alignement seront regroupés au sein d'un
> même cours complexe»*

quindi *allineamento → attività complessa → gruppi*. La guida diceva il vero.

## Lo sdoppiamento in concreto 📦

Le suddivisioni hanno **nomi predefiniti** cablati nel prodotto (chiavi
`ParametresSco_Ressources_RS_Nommage*`):

| Chiave interna | IT | FR |
|---|---|---|
| `NommagePartitionDedoublement` | `Sdoppiamento` | `Dédoublement` |
| `NommagePartitionArbitraire` | `Suddivisione` | `Partition` |
| `NommagePartitionGarconsFilles` | `Maschio/Femmina` | `Fille/Garçon` |
| `NommagePartition1TiersDeuxTiers` | `UnTerzoDueTerzi` | `UnTiersDeuxTiers` |
| `NommagePartie1Tiers` / `…2Tiers` | `1Terzo` / `2Terzi` | `1Tiers` / `2Tiers` |
| `NommagePartieGarcon` / `…Fille` | `Maschi` / `Femmine` | `Garçons` / `Filles` |

⚠ Correzione rispetto a una lettura affrettata di queste stringhe: **non sono
un'enumerazione di "modalità di sdoppiamento"**. Sono etichette di *default*
scritte come dato. L'enumerazione vera nel motore è
`TypeNomPartiePredefini = partieFille, partieGarcon, partie1Tiers, partie2Tiers`
— cioè riguarda le **parti**, non le suddivisioni.

I tipi di sdoppiamento offerti in UI sono: *prima metà*, *seconda metà*, *un
terzo*, *due terzi*, *maschi*, *femmine*. Il riempimento avviene per criterio
`Alfabetico` o `Maschio/Femmina`.

**Regola strutturale, letterale dal prodotto:**

> `- per le ore in sdoppiamento, il numero di raggruppamenti per classe è sempre
> uguale a 2.`

Lo sdoppiamento produce **sempre esattamente 2 raggruppamenti** per classe. Non è
un parametro libero. Per dividere in tre si usa la suddivisione
`UnTerzoDueTerzi`, che è un'altra cosa.

## Da verificare

- [x] ~~La partizione ha un'anagrafica propria?~~ → **sì**: nel motore
      `TypeGenreRessource` elenca `Partition` e `PartieDivision` fra le **risorse
      di prima classe**, allo stesso livello di Classe e Aula. Nello schema di
      scambio è degradata a stringa (`@LibellePartition`), ma internamente è
      un'entità. Il nostro modello segua l'interno, non lo scambio.
- [ ] Come si crea concretamente un gruppo trasversale a due classi.
- [x] ~~Gestione IRC vs. attività alternativa~~ → **risolto sui dati**, vedi
      sotto.
- [ ] Decisione di scope: **supportare gli sdoppiamenti in v1** o dichiararli fuori
      scope. Vedi *Aperto* in [CLAUDE.md](../../CLAUDE.md).

## 🔑 IRC vs. attività alternativa — risolto sui dati 📦

La base di esempio fornita con EDT contiene 187 parti di classe. **Solo 8 hanno
un nome**, e sono quattro coppie:

```
1C_REL   / 1C_ALT
1F_REL   / 1F_ALT
1 A/R_REL / 1 A/R_ALT
1 B/R_REL / 1 B/R_ALT
```

`_REL` = religione, `_ALT` = alternativa. Le altre ~179 parti sono anonime e non
compaiono in nessun corso.

**EDT modella IRC e attività alternativa come due parti della stessa classe che
condividono lo stesso ident di ripartizione** — non come un gruppo, non come
compresenza, non come materie diverse. La pista della guida 📖 ("attività
complessa / compresenza") era **sbagliata** per questo caso.

Coerente con la nomenclatura ministeriale, dove IRC e alternativa condividono un
solo codice materia (`6666`, vedi
[nomenclatura-sidi.md](nomenclatura-sidi.md)): la distinzione è **organizzativa**,
ed è esattamente lì che EDT la mette — nella partizione della classe.

**Per il nostro modello** è la notizia migliore possibile: IRC non è un caso
speciale. È una suddivisione binaria della classe come un'altra, e se supportiamo
le partizioni lo otteniamo gratis.

## La differenza fra parte e raggruppamento, sui dati 📦

Nella base di esempio ci sono 3 raggruppamenti, con nomi leggibili:

```
FRANCESE 1AA-1BA      SPAGNOLO 1AA-1BA      ALTERNATIVA 1H-2D
```

I nomi dicono tutto: **attraversano più classi**. Le parti invece portano nel
proprio record l'ident di *una sola* classe. È la differenza strutturale, e
conferma sui dati quanto lo schema di scambio dichiara con la cardinalità
`Groupe/Classe 0..N`.

Nota di scala: i 3 raggruppamenti sono usati in **5 corsi** su 984, le parti in
16. Sono strumenti di nicchia anche in una base realistica — utile per calibrare
lo scope di v1.

## Implicazioni per il nostro modello

- Tre entità, non una: `class_partition` (la partizione), `class_part` (la parte)
  e `group` (l'insieme di parti). Il gruppo si lega alle classi **attraverso** le
  parti, in molti-a-molti.
- Le assegnazioni docente ([docenti.md](docenti.md)) devono poter puntare a un
  gruppo o a una parte, non solo a una classe intera.
- Il gruppo è **derivato**: nasce dall'attività complessa (allineamento), non da
  un'anagrafica compilata a monte. Nel nostro schema può restare un'entità
  materializzata, ma la sua *creazione* va guidata dall'allineamento, non lasciata
  all'utente — altrimenti si ricade nella ridondanza che la guida sconsiglia.
