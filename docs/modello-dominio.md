# Modello di dominio — v1

> **Stato: design approvato il 2026-07-26** (sezione per sezione, in sessione).
> Traduce in schema lo scope di v1 ([scope-v1.md](scope-v1.md), [ADR-015](decisioni.md))
> e il reverse engineering di EDT (`docs/edt/`). La costruzione è sbloccata da
> [ADR-016](decisioni.md). Il codice Django arriva in una fase successiva, su
> questo design.

## Impostazione

**Autonomo dal SaaS, convergenza dopo.** Il generatore nasce come modulo con
schema proprio: nessuna tabella del SaaS sostituzioni in produzione viene toccata.
Ma due entità sono disegnate *per* la convergenza, e vanno tenute d'occhio a ogni
modifica: l'**attività con maschera temporale** ([ADR-014](decisioni.md)) e la
**disponibilità con data opzionale** (vedi sotto), che sono esattamente le
strutture che il modulo sostituzioni condividerà quando i due sistemi
convergeranno.

**Terminologia.** Prosa in italiano, identificatori in inglese — e sui gruppi si
usano **solo** i termini inglesi non ambigui `partition` / `part` / `group`,
perché l'italiano di EDT inverte i livelli («gruppo» traduce `partie`, non
`groupe` — [gruppi.md](edt/gruppi.md)).

**Quattro principi trasversali**, tutti ereditati dall'analisi:

1. **La cascata di default è dichiarata, non un meccanismo generale**
   ([ADR-003](decisioni.md)): dove un campo eredita, è nullable con `NULL` =
   «eredita», e il documento lo dice campo per campo. Ovunque altrove si
   materializza.
2. **I calcolati non si memorizzano** ([ADR-007](decisioni.md)): previsionali,
   `S.P.`/dominio residuo, totali di peso — tutti derivati a runtime.
3. **Un orario invalido è uno stato ammesso**: nessun vincolo di integrità sul DB
   lega piazzamenti e vincoli. La validità è un **predicato interrogabile**, non
   un invariante — è la scelta di progetto di EDT verificata sui dati (21/984
   attività illegali in una base risolta, [diagnostica.md](edt/diagnostica.md)).
4. **Ogni vincolo esiste due volte**: come constraint del solver e come predicato
   valutabile su un orario dato, generati dalla **stessa riga di dato**. È ciò che
   rende possibili, senza solver, l'analisi di capienza e il controllo di
   conformità.

## Le tre condizioni di ADR-015, sciolte

Le tre condizioni che tenevano in piedi le decisioni di scope trovano qui la loro
forma. Se una di queste soluzioni cade, va riaperta la decisione corrispondente.

**1. «L'insieme minimo da spostare» (per `Piazza e sistema`).** Il piazzamento è
dato di prima classe, **separato dall'attività**: una tabella `placement`, mai un
campo `slot` sull'attività. E lo slot occupato non è un booleano: l'attività porta
un **livello di immobilità** a quattro valori (vedi *Attività*), perché
«occupata-spostabile vs occupata-bloccata» è il perno di ogni riparazione
([diagnostica.md](edt/diagnostica.md)). Con questo, «cosa devo spostare perché A
stia qui?» è una query sul modello; il motore che la risponde arriverà dopo, ma i
dati ci sono — ed è ciò che tiene riapribile l'esclusione del risolutore
passo-passo.

**2. L'analisi di capienza è un componente a sé.** Garantita dal principio 4:
i vincoli sono righe interrogabili, l'analisi legge le stesse tabelle del solver
senza passare dal solver. Nessuna struttura dati è privata del motore.

**3. La parte porta un piano di studi proprio.** Il quadro orario resta agganciato
al piano ([piani-di-studi.md](edt/piani-di-studi.md)), ma l'aggancio sta
sull'**unità didattica**: `class` ha la sua FK a `study_plan`; `class_part` ha una
FK a `study_plan` **nullable**, `NULL` = eredita dalla classe (cascata dichiarata,
principio 1). La classe articolata: parte A → piano Manutenzione, parte B → piano
Elettronica, ore comuni sulla classe intera. La condizione regge senza entità
dedicata, come richiesto da [ADR-015](decisioni.md) §4.

## Le risorse

**Una tabella base, cinque tipi più le parti.** `resource` (id, tipo, nome,
`site` FK, `simultaneous_capacity` int default 1) con le tabelle di dettaglio in
uno-a-uno: `teacher`, `class`, `class_part`, `room`, `staff_member`, `material`.
Sono le cinque risorse di piazzamento di EDT ([risorse.md](edt/risorse.md)) più la
parte di classe, che in EDT è risorsa di prima classe anch'essa
(`TypeGenreRessource`). Tutto ciò che è generico — disponibilità, vincoli orari,
occupazione — punta a `resource`, mai al tipo concreto: è ciò che rende «personale
e materiali dentro come forma» gratuito ([ADR-015](decisioni.md) §5) e un sesto
tipo aggiungibile senza riscrivere.

**Una sola tabella di disponibilità.**

```
resource_unavailability(resource, slot, level, date?)
```

con tre livelli — `hard` (rosso), `optional` (giallo: violabile solo con
l'override **globale**, mai selettivo), `preference` (verde) — e **data
opzionale**: `NULL` = ricorrente ogni settimana, valorizzata = assenza puntuale.
Indisponibilità e assenze sono la stessa tabella, com'è in EDT
([vincoli.md](edt/vincoli.md)); è l'entità di convergenza col SaaS.

**Capacità cumulativa, una volta sola.** `simultaneous_capacity` sta sulla risorsa
base: l'aula con `Qtà = 2` e il carrello di portatili sono lo stesso caso
([aule.md](edt/aule.md), [risorse.md](edt/risorse.md)). Le attività chiedono
materiali **con quantità** (M2M con campo `quantity`). In CP-SAT: un solo vincolo
`cumulative`.

**Per tipo:**

- `teacher`: anagrafica (titolo, cognome, nome, abbr., statuto), `Mh/s` nullable
  con default **globale** d'istituto (cascata dichiarata), `HSMax`, materia
  preferenziale. **Capacità ≠ assegnazione** ([ADR-006](decisioni.md)): M2M
  `teacher ↔ subject` (materie insegnabili) separata dalla cattedra. Previsionali
  mai memorizzati ([ADR-007](decisioni.md)).
- `room`: `capacity` (capienza, **descrittiva** — non è un vincolo,
  [aule.md](edt/aule.md)). **Niente tipologie in v1**: in EDT sono tag puramente
  descrittivi. Niente gerarchia padre/figlio in v1. L'**aula preferenziale sta
  sulla classe**, e l'aula sull'attività è un'eccezione dichiarata.
- `site`: tabella propria; la sede sta su risorsa e attività. **Un solo parametro
  d'istituto** `site_transition_slots` (N slot liberi per cambiare plesso) — la
  regola di transizione semplice di [ADR-015](decisioni.md) §3. Matrice orientata
  dei tempi, massimi di cambi e «solo negli intervalli» restano fuori v1.
- `staff_member`, `material`: solo la forma — anagrafica minima, disponibilità e
  capacità dalla base. Dati opzionali, mai richiesti per usare il prodotto.

## Il tempo e il calendario

**La griglia.** `time_grid`: `days_per_cycle` × `slots_per_day`, etichette orarie
per slot (inizio/fine) e durate in **minuti** — la fascia di calcolo è distinta
dall'etichetta visualizzata, come in EDT
([tempo-e-calendario.md](edt/tempo-e-calendario.md)). In v1 il ciclo coincide con
la settimana, ma i due concetti restano campi separati (costo zero, riscrittura
evitata). **Niente suddivisioni sub-orarie** (sconsigliate dal produttore stesso):
ore da 50′ = griglia da 50′.

**Due confini sulla griglia:**

- la **linea di fine mattinata** (in numero di fasce), da cui deriva la **mezza
  giornata** — l'unità di misura di un'intera famiglia di vincoli, concetto di
  prima classe del modello;
- gli **intervalli** come separatori fra ranghi (non consumano slot —
  [tempo-e-calendario.md](edt/tempo-e-calendario.md)), col flag `respects_breaks`
  sull'attività: un blocco da 2h che li rispetta non può stare a cavallo.

Niente mensa in v1 (fuori scope dichiarato, [scope-v1.md](scope-v1.md)).

**Calendario.** `school_year` (data inizio, data fine, primo giorno della
settimana 1 — l'ancora del ciclo al calendario reale) + giorni festivi.

**Periodi e versioni d'orario.** `period` partiziona l'anno scolastico. Per
[ADR-010](decisioni.md) non c'è collocazione per periodo sull'attività: l'orario
si **rigenera** a ogni periodo. La forma che lo consente è `schedule` — una
versione d'orario, riferita a un periodo — a cui appartengono i piazzamenti. Due
conseguenze già a verbale: il criterio «mantieni il più possibile le collocazioni
precedenti» è un input del solver che legge lo `schedule` del periodo prima; e lo
`schedule` è anche ciò che permette lo stato «orario invalido ammesso» (principio
3) senza vincoli di integrità.

**Periodicità = maschera di settimane.** L'attività porta una **maschera a bit
sulle settimane di calendario** ([ADR-014](decisioni.md)): annuale = tutti i bit,
`Q1`/`Q2` = metà alterne, sostituzione/eccezione = **un bit solo**. Un solo
meccanismo, nessuna entità «eccezione» separata. (La nomenclatura resta `Q1`/`Q2`,
mai «settimana A/B» — terminologia non del prodotto.)

## La struttura didattica

**La catena anagrafica.**

- `discipline`: tabella ([ADR-001](decisioni.md)), con la mappatura **M2M alle
  classi di concorso** in tabella a sé — nostra estensione, marcata come tale
  ([ADR-002](decisioni.md)); il `Codice` EDT è il campo da cui importare quando
  valorizzato.
- `subject`: FK a `discipline`; `Al./Rid.` come **tetto massimo nullable** in
  cascata ([ADR-005](decisioni.md)); **peso didattico** int default 1
  ([ADR-011](decisioni.md)).
- `study_plan`: indirizzo × anno (`track`, `year` — la chiave
  `Formation + Specialite` dello XSD, [schema-scambio.md](edt/schema-scambio.md)).
- `service`: riga piano × materia col monte ore **tripartito** — `class_hours` /
  `reduced_hours` / `split_hours` (classe intera / ridotto / sdoppiato), i tre
  attributi dello XSD. Con gli sdoppiamenti in v1 ([ADR-013](decisioni.md))
  servono davvero, e sono tre campi durata, non struttura. Il `Coeff.`
  (`Pondération`, 60/60) resta **fuori**: semantica mai chiarita
  ([piani-di-studi.md](edt/piani-di-studi.md)), si aggiunge quando la si capisce.
  Dal 2026-08-28 porta anche `election_group` ([ADR-020](decisioni.md)): le
  righe che lo condividono sono **alternative**, e l'alunno ne segue una. È la
  forma minima del `MS` di EDT, che il piano sia un **catalogo** e non un
  curriculum.

**Classe, parti, raggruppamenti — l'unità didattica.**

```
class ──> class_partition ──> class_part ──compone──> group (trasversale)
  │FK study_plan                 │FK study_plan nullable (NULL = eredita)
```

- `class`: FK `study_plan`, anno, **aula preferenziale** (FK nullable a `room`).
- `class_partition` (classe, nome) → `class_part` (partizione, nome, FK
  `study_plan` nullable — la condizione 3). IRC/alternativa è una partizione
  binaria `_REL`/`_ALT` come un'altra: gratis ([gruppi.md](edt/gruppi.md)).
- `group` (raggruppamento trasversale): M2M di parti, attraversa più classi.
  **Derivato dall'allineamento**, non anagrafica compilata a monte: materializzato
  nello schema, ma creato dal meccanismo di allineamento
  ([gruppi.md](edt/gruppi.md), [ADR-013](decisioni.md)).
- L'**unità didattica** — ciò su cui si scrive un'attività o un vincolo — è
  classe, parte o raggruppamento. Ogni relazione che l'analisi diceva «sulla
  classe» è sull'unità.

**La cattedra** (assegnazione): docente × materia × **unità** × ore, una riga per
assegnazione — mai solo la classe intera ([docenti.md](edt/docenti.md)).

## L'attività e il piazzamento

**Una sola entità** ([ADR-014](decisioni.md)). `activity`:

| Aspetto | Forma |
|---|---|
| Materia | FK a `subject` — **l'unico riferimento obbligatorio**, come nello XSD |
| Docenti | 0..N — la compresenza è il formato base, non un caso speciale |
| Unità didattiche | 0..N (classi, parti, raggruppamenti) |
| Aule dichiarate | 0..N — **eccezione dichiarata**, non colonna obbligatoria |
| Personale | 0..N |
| Materiali | 0..N **con quantità** |
| Sede | 0..1 |
| Durata | in **fasce** (il blocco da 2h è un'attività di durata 2: un intervallo, non celle) e in minuti |
| Spezzamento | **FK ricorsiva padre/figlio** (`TypeParenteCours`, [attivita.md](edt/attivita.md)) |
| Allineamento | ident condiviso → attività complessa (genera i raggruppamenti) |
| Maschera temporale | bit sulle settimane di calendario (vedi *Tempo*) |
| Flag | `respects_breaks`, priorità |
| Immobilità | enum a 4 valori: `fixed` / `locked_in_place` / `not_suspendable` / `suspended` |

Fuori v1, dichiarati: sezionamento (`S`/`SQ`/`SC`/`SP`) e alternanza docenti
(`A`/`AQ`/`AC`) ([scope-v1.md](scope-v1.md) §A), fascia variabile
([ADR-010](decisioni.md)), vincoli fra attività ([ADR-015](decisioni.md) §6).

**Il piazzamento è output, mai sull'attività.**

```
placement(schedule, activity, day, start_slot, assigned_room?)
```

Una riga per attività piazzata, dentro la versione d'orario del periodo.
`assigned_room` è l'esito della **seconda fase** (l'assegnazione aule è un
problema separato, validato da EDT — [scope-v1.md](scope-v1.md) §C), distinta
dalle aule *dichiarate* sull'attività. La copertura del monte ore
(Σ durate attività = ore del servizio) è un **predicato di controllo**, non un
vincolo di integrità (principio 3) — e si misura sull'**atomo**, cioè sul
curriculum di un alunno, non sulla parte ([ADR-020](decisioni.md)).

## I vincoli

Quattro assi, quattro forme — tenuti separati perché EDT li tiene separati
([vincoli.md](edt/vincoli.md)):

| Asse | Forma nel modello |
|---|---|
| Disponibilità | `resource_unavailability` (vedi *Risorse*) |
| Capacità | `simultaneous_capacity` sulla risorsa |
| Cardinalità | `resource_time_constraint` (sotto) |
| Relazione | `subject_constraint` (sotto) |

**Cardinalità.** `resource_time_constraint`, polimorfica sulla risorsa, copre i
sette gruppi osservati sul docente: distribuzione minima (min N giorni con min X
ore), max ore (giornata/mattino/pomeriggio), max presenza, entrate/uscite,
giornate e mezze giornate libere garantite, max mezze giornate di lavoro, max
cambi di sede — più la soglia buchi `D.T.B.`. **La stessa tabella serve docenti e
classi**: `MMG`/`MG` sulla classe sono gli stessi vincoli del docente, confermato
in UI ([classi.md](edt/classi.md)). Valori nullable = default d'istituto (cascata
dichiarata). Nota già a verbale: **presenza ≠ attività** (la presenza include i
buchi) — due conteggi distinti.

**Relazione.** `subject_constraint(unit, subject_a, subject_b, type, param)`:

- **orientata** — `A→B` e `B→A` sono righe distinte, com'è nei dati;
- **`A = B` è il caso dominante** — 15 righe su 19 nella base reale sono la
  materia con sé stessa: il vincolo serve prima di tutto a distribuire nel tempo
  le ore di una materia;
- `type` è un enum sui **13 tipi censiti** ([vincoli.md](edt/vincoli.md)),
  inclusi i quattro `Parties…Classe` (ordine fra ore in gruppo e ore a classe
  intera), che servono perché gli sdoppiamenti sono in v1;
- la granularità dei parametri è la **mezza giornata**, dal modello del tempo.

Il solver li implementerà per gradi — priorità dichiarata: `Incompatibilità 1g`
della materia con sé stessa, poi `Max ore 1g`, poi la sequenza vietata
([scope-v1.md](scope-v1.md) Parte II) — ma lo **schema li rappresenta tutti da
subito**: sono righe con parametri, non struttura.

**Peso didattico** ([ADR-011](decisioni.md)). Peso sulla materia (default **1**,
non 0), tetto per classe (massimo settimanale **per alunno**) e tetti d'istituto
(mattino / pomeriggio / giornata / settimana) in cascata. Il totale si calcola
**per parte, non per classe** — il conteggio `_REL`/`_ALT` verificato sui dati
([vincoli.md](edt/vincoli.md)): senza le parti sarebbe sbagliato.

**Ogni vincolo, due nature e un'etichetta** (principio 4). Ogni tipo di vincolo
nel registro porta: il constraint CP-SAT, il **predicato** valutabile su un orario
dato, e una **causale nominata** — il catalogo di ~170 frasi di EDT
([diagnostica.md](edt/diagnostica.md)) è riusabile quasi così com'è. Sulle stesse
tabelle vivono così, senza solver: il controllo di conformità dell'orario
esistente, l'analisi di capienza pre-calcolo (condizione 2), la diagnostica del
solver. Il dominio residuo (`S.P.`) si **calcola, non si memorizza**
([ADR-007](decisioni.md)).

**Alleggerimenti a quota, mai pesi.** In EDT non esiste una funzione di costo
numerica ([motore-risoluzione.md](edt/motore-risoluzione.md)): il modello è
**lessicografico**. Il rilassamento è

```
relaxation_quota(constraint_family, resource?, max_violations)
```

— variabili di violazione vincolate in somma, non penalità nell'obiettivo.
L'opzionalità del giallo resta un override **globale**, com'è nel prodotto.

**`Estrai`.** Selezione di lavoro persistente e nominata:
`extraction(name, M2M activity)`. È la voce con più dipendenze in entrata
dell'inventario, e il motore opererà **esclusivamente** su di essa
([scope-v1.md](scope-v1.md) §E); come dato costa una tabella.

## Cosa il modello non rappresenta

Già deciso altrove, qui solo richiamato: vincoli fra attività
([ADR-015](decisioni.md) §6) · fascia variabile ([ADR-010](decisioni.md)) ·
sezionamento e alternanza · multi-istituto e formazione classi · mensa ·
ciclo ≠ settimana e suddivisioni sub-orarie · massimi a quattro modalità ·
prenotazioni · contabilità del personale (IMP/TRMD) · import `Partenaire_Index`
([ADR-012](decisioni.md)) · colloqui e consigli.

## Aperto

- **La via d'ingresso dei dati anagrafici** (formato nostro, CSV o aggancio al
  SaaS): da scegliere al momento dell'import, non condiziona questo schema.
- **La configurazione della griglia oraria non è mai stata osservata in UI**: il
  modello del tempo poggia sullo XSD (fonte di livello 1, [ADR-009](decisioni.md))
  ed è marcato da confermare appena possibile.
- La **verifica sul dataset Fermi**: quando lo schema diventa codice, il primo
  test è rappresentare l'intero dataset (`data/liceo-fermi/`) più i casi che il
  Fermi non ha (parti, raggruppamenti, sedi) presi dalla base di esempio.
