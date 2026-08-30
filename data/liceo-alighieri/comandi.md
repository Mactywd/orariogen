# I comandi, su questo banco

Ondata 7. Le sei ondate precedenti riguardano il **modello**: una riga di
vincolo c'è, un builder la legge, e stringerla di una tacca rende il calcolo
impossibile. Questa riguarda il **prodotto**: i cinque comandi diagnostici
hanno qualcosa di vero da dire su questa scuola? In coda ci sono due cose che
i comandi non misurano ma l'ondata sì — il criterio **«stretto ma
risolvibile»** di §4, l'ultimo della spec rimasto senza verdetto, e il difetto
che misurarlo ha trovato.

🔑 **È una domanda diversa, e ha un modo diverso di fallire.** Un comando che
gira, non va in errore e risponde *«niente da segnalare»* è verde e non prova
niente. È lo stesso rischio del §6 della spec — *un dataset lo si aggiusta
finché è verde* — alla scala del prodotto invece che a quella del builder.

⚠ **Il metro resta il Fermi.** Non perché sia più povero, ma perché non è
stato progettato per superare i nostri test: ciò che *non* riesce a far dire a
un comando misura una lacuna vera del dataset, non un difetto del comando.

---

## 1. `analyze` — la classifica dei vincoli da allentare

La domanda è quella che EDT non sa rispondere: il prodotto elenca *cosa* si può
alleggerire, ma non *quale* alleggerimento serva.

| | Fermi | Alighieri a riposo | Alighieri saturo |
|---|---:|---:|---:|
| righe di classifica | 3 | 5 | **63** |
| causali distinte | **1** | 3 | **15** |
| prima riga | `unavailability` | `unavailability` | **`subject_half_day_gap`** |

Il Fermi dà `{"unavailability"}` in tre righe, su tre docenti: cioè
**letteralmente** le *«tre indisponibilità»* che la spec dichiara
insufficienti. Non è un difetto del comando — zero `ResourceTimeConstraint` e
zero `SubjectConstraint` non danno niente da ordinare.

### 🔑 La misura che conta è su un orario **quasi fatto**

A riposo l'Alighieri ne dà tre, non le cinque attese, e la ragione sta in
`domain/analysis/blame.py`: `free_candidates` **spiazza tutte le candidate**
prima di calcolare i domini. Su un orario in cui niente è congelato
l'occupazione non occupa, e un vincolo *fra due ore* non ha soggetto se sono
libere entrambe — restano solo le famiglie **unarie**.

Ed è coerente col mestiere dello strumento: *«il calcolo è fallito, cosa
allento?»* è una domanda che si pone su un orario quasi fatto. La **variante
satura** è quella situazione — tutto congelato tranne nove occorrenze, una per
unità che porta una riga dei due assi — e lì le famiglie sono quindici:
l'occupazione delle risorse bloccate, cinque tetti orari del docente e della
classe, l'intervallo, l'indisponibilità, il **picco del gruppo di aule**, e
sei dei tredici tipi di vincolo di materia.

### Le famiglie che non entrano in classifica

Il comando le **dichiara**, ed è la riga che vale: dodici famiglie non
monotone, `max_gap_hours` fra loro. Una classifica che tacesse sul D.T.B. —
uno dei vincoli che le scuole allentano più spesso — sembrerebbe dire «il
D.T.B. non c'entra», che è il consiglio sbagliato dato in silenzio.

## 2. `analyze` — il violatore di Hall

| | esito |
|---|---|
| dataset base | **nessun** insieme deficiente |
| `LAB-SUCC` ridotto al solo mercoledì | **1** insieme, risorsa satura `LAB-SUCC` |

La prima riga è un atteso e non un contorno: la fase 5 dimostra
l'*impossibilità*, e un dataset che il solver risolve non può contenerne una.
Un banco che desse un deficit a riposo sarebbe **rotto**, non teso.

Il portatore era dichiarato dall'ondata 1: la succursale ha **un** laboratorio
e nessun ripiego, e undici ore la settimana se lo contendono
([aule.md](aule.md)).

### ⚠ Il deficit non è «undici meno otto»

Il comando dichiara **9h00 contro 8h00** su **nove** attività, non tre ore su
undici. Il certificato di Hall è un **insieme deficiente minimale**: la
riduzione toglie dal gruppo ogni attività che potrebbe stare altrove, e resta
il sottoinsieme che dimostra l'impossibilità.

🔑 Ed è il verdetto più utile dei due. *«Mancano tre ore»* non dice dove
guardare; *«queste nove hanno in comune otto ore di finestra»* nomina il gruppo
da spezzare.

## 3. `Estrai` — i sei rilevatori

Cinque guasti si iniettano, il sesto è naturale.

| Rilevatore | attività trovate |
|---|---:|
| `problemi_di_aule` | **73** |
| `non_rispettano_i_vincoli` | 36 |
| `non_conformi_ai_piani_di_studi` | 3 |
| `problemi_di_sede` | 2 |
| `a_cavallo_dell_intervallo` | 1 |
| `fuori_griglia` | 1 |

🔑 **Il primo è il più interessante, e non si inietta.** Un orario appena
calcolato è *sempre* «con problemi di aule», perché le aule le assegna la
seconda fase. Non è un guasto: è la forma a due fasi del prodotto, che il
rilevatore vede correttamente.

⚠ E nessuno dei sei è **muto** — cioè in nessuno la violazione esiste senza
un'attività da nominare. È il caso che `Rilevamento.muto` esiste per
distinguere, e su questo orario non si presenta.

## 4. `place_and_fix` — quanto costa imporre una collocazione

Sul Fermi un'imposizione costa **una** attività spostata, e con una sola il
minimo lessicografico di `moved` non è messo alla prova. Qui ne costa **tre**,
zero scartate.

🔑 **E il testimone è un argomento, non una misura fortunata.** Si cerca una
cella dove due attività *diverse* confliggono con la terza — una per la classe,
una per il docente — e allora «almeno due si spostano» è vero per costruzione:
entrambe devono sgomberare, e nessun ottimo può evitarlo. Il numero **tre** è
invece ciò che la ricerca ha trovato, e non si asserisce.

⚠ La prima esplorazione impose otto attività della succursale su celle
occupate e ottenne 2 ogni volta: incoraggiante, e non una prova — la cella
bersaglio veniva da un calcolo precedente e sarebbe cambiata alla successiva.

## 5. `solve --popolazione` — il tetto di non-regressione

### ⚠ Sul dataset a riposo **non morde**, e la sbagliata era l'attesa

Sei configurazioni misurate: le due popolazioni, tolleranze da 0 a 6000, e la
base portata a zero da una prima ottimizzazione. In **tutte** i buchi della
popolazione ottimizzata scendono a zero e lo dimostrano.

| popolazione ottimizzata | base del sacrificato | esito |
|---|---:|---|
| docenti | `gaps_classes` 7500 | `gaps_teachers` **0**, dimostrato |
| classi | `gaps_teachers` 4380 | `gaps_classes` **0**, dimostrato |
| docenti, dopo aver azzerato le classi | `gaps_classes` **0** | `gaps_teachers` **0**, dimostrato |

Il tetto non morde perché **non c'è competizione**: quaranta fasce per
ventinove ore lasciano a ciascuna popolazione abbastanza spazio da non togliere
niente all'altra. La smentita è del **dataset**, non del meccanismo.

⚠ E la strada del criterio *non dimostrato* è stata provata e scartata:
sacrificando `free_half_days_teachers` i valori sono usciti 121 / 122 / 124 al
crescere della tolleranza — cioè nella direzione **sbagliata**, con un divario
di oltre cento. È l'ondata 6 che si paga due volte: la differenza fra due
esecuzioni di un livello che non dimostra il proprio ottimo non dice niente sul
modello.

### 🔑 La risposta è mettere il dataset in tensione

La terza forma di verifica, dall'ondata 6. Tre pezzi, ognuno necessario:

1. la base si porta a **zero** con un primo arbitrato sulle classi — che è
   letteralmente il primo dei due comandi di EDT;
2. la classe 1A si rende **indisponibile** alla seconda fascia del lunedì
   *prima* di quel calcolo, così l'orario di partenza resta legale. ⚠
   Invertire i due passi dà `base: None`, ed è il modo corretto in cui
   `_valori_di_base` dice *«l'orario di partenza non è rappresentabile in
   questo modello»*;
3. si **puntano** due ore di italiano ai due lati del buco, con lo stesso
   `pinned` dell'ondata 4.

| tolleranza | tetto | esito |
|---:|---:|---|
| 0 | 0 | `INFEASIBLE` |
| 60 | 60 | `INFEASIBLE` — **la riga che porta l'informazione** |
| 180 | 180 | `FEASIBLE` |

Il buco vale 60 minuti per **tre chiavi** — la classe e le sue due parti, IRC e
alternativa — quindi 180. È la stessa aritmetica del difetto **L7**, e la
stessa forma della quota dell'ondata 6: una tolleranza «più di zero» non basta,
deve essere **quella giusta**.

## 6. `assign_rooms` — la contesa, e la rinuncia

### La contesa che il gruppo di aule risolve

Il testimone è **puntato**, come nell'ondata 4: tre ore di fisica su classi e
docenti tutti diversi, imposte sulla stessa cella. Le loro candidate sono le
stesse due aule, quindi il principio dei cassetti dice che non ci stanno.

| | con `structural:room_pool` | senza |
|---|---|---|
| fase 1 | **`INFEASIBLE`** | `OPTIMAL`, zero scarti |
| fase 2 | — | ≥ 1 rinuncia, fra le tre puntate |

⚠ Il ramo «senza» non è decorativo: senza di lui, un `INFEASIBLE` dovuto a
qualunque altra ragione sembrerebbe una prova. E dice anche **cosa costa non
contarle**: la fase 1 accetta l'orario, la fase 2 lo eredita, e l'unica
risposta che le resta è la rinuncia — la stessa misura del Fermi, 8 su 92,
alla scala di questo banco.

⚠ Su un calcolo **libero** senza il builder le rinunce misurate sono state 1 e
poi 2: è una proprietà dell'ottimo che la ricerca ha scelto, non del modello, e
per questo non si asserisce.

### La rinuncia inevitabile

Un'attività **immobile** in una cella dove entrambe le sue candidate sono
rosse: nessuna assegnazione esiste, e la seconda fase **rinuncia** invece di
dichiararsi infattibile — 72 su 73, `1h00` senza aula, e il comando nomina
l'attività, la classe, il docente, quando e cosa chiedeva.

🔑 **E la fase 1 fa due cose opposte, entrambe corrette.** Sulle attività
**libere** il gruppo di aule conta zero posti in quella cella e le manda
altrove: senza il ricalcolo le rinunce sono due, perché un'altra ora di
laboratorio stava lì. Sull'**immobile** tace, perché `RoomPoolBuilder` esce
quando nessuna delle attività in causa è libera — *«un fatto, non una
decisione»* — e la configurazione resta illegale perché nessun piazzamento la
può riparare.

---

## 7. E il criterio di §4, che i comandi non misurano ma l'ondata sì

*«La fase 1 chiude `OPTIMAL` con zero scarti, ma togliendo una sola aula o un
solo docente comincia a scartare.»* È l'ultimo criterio della spec rimasto
senza verdetto, e tre file del banco lo rimandavano a quest'ondata.

| risorsa spenta | scarti |
|---|---:|
| `LAB-SUCC`, il laboratorio unico della succursale | **11** — cioè le attività che lo chiedono |
| `VITAL` (20 h) | 20 |
| `COLOM` (12 h) | 12 |
| `RICCI` (lo spezzone, 3 h) | 3 |
| `LAB-INF`, `AUL-DIS`, `A101`, `AULA-MAGNA` | 0 |

⚠ **«Una» aula, non «qualunque»**: l'aula magna non la usa nessuno, e toglierla
non deve costare niente. Il criterio dice che il banco ha un punto in cui è
teso, e i punti si misurano.

### 🔑 Due nozioni diverse di «stretto», e la spec ne dichiarava una sola

Il criterio è soddisfatto **senza** portare al bordo né il D.T.B. (ondata 3) né
la tacca dei divieti di relazione (ondata 4), e i due test che asseriscono
l'`OPTIMAL` restano verdi. Non è una contraddizione:

- **stretto rispetto alle risorse** — togline una e qualcosa cade. È il
  criterio di §4, ed è verificato;
- **stretto rispetto alla densità della griglia** — la contiguità costa. Con
  quaranta fasce contro cattedre da 10–21 ore è gratis, e per negarla
  servirebbe una griglia più corta, cioè un altro banco.

La frase «diventerà rosso all'ondata 7» che accompagnava quei due test era
quindi sbagliata: l'ondata 7 stringe le **risorse**, non la griglia. Corretta
dove stava scritta.

## 8. ⚠ Misurando il bordo il banco ha trovato **L8**

Spegnendo la **palestra** il modello non scarta: risponde `INFEASIBLE`, che è
ciò che `allow_unplaced=True` dovrebbe rendere impossibile — lo scarto esiste
proprio perché un'attività che non ci sta non blocchi il calcolo.

| | esito |
|---|---|
| palestra spenta | **`INFEASIBLE`**, zero scarti |
| la stessa, tolta la riga `free_guaranteed` | `OPTIMAL`, **10** scarti |

La causa è **una sola riga**, isolata togliendone dieci una per volta:
`free_guaranteed` su P01 Zanetti, il docente di scienze motorie. Con la
palestra spenta gli restano le sole ore della succursale, e il solver ne piazza
**una**, su **un** giorno. La riga chiede due giornate libere — che ci sono — e
due **mezze** giornate libere, che non ci sono: una mezza giornata libera conta
solo su un giorno **lavorato** (`libera = attivo AND NOT meta`), perché è così
che la conta `FreeGuaranteedChecker`, e un giorno interamente vuoto contribuisce
zero. Con un giorno lavorato il massimo è uno.

🔑 **È l'immagine speculare della trappola che il builder documenta**, e non è
un errore del builder: contare le mezze libere su tutti i giorni accetterebbe
orari che il checker boccia, cioè la direzione sbagliata. Il fatto nuovo è la
**conseguenza**: una famiglia che conta una quantità *sui giorni in cui si
lavora* può diventare insoddisfacibile **perché si lavora meno**, e lì lo
scarto non è una via d'uscita. Un prodotto che risponde `INFEASIBLE` invece di
«queste dieci attività non si piazzano» dà all'utente la diagnosi peggiore
delle due.

---

## Cosa non è misurato qui

`export_ical` non compare in §7 e non ha una domanda diagnostica: consegna
l'orario, non lo giudica. La sua misura sta nel changelog del 2026-08-28.
