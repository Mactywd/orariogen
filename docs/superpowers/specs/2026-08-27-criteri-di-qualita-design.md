# I criteri di qualità — design

> Stato: **approvato in sessione** (2026-08-27). Le tre decisioni di scope sono
> state chiuse prima di scrivere: tutti e quattro i criteri di EDT più il
> verde; l'ordine è **dato**, non codice; la catena resta **unica** e la
> separazione per popolazione è dichiarata fuori.

## 0. Il pezzo che è

La catena lessicografica di `domain/solver/objective.py` ha quattro livelli, e
tutti e quattro parlano di **fallimento**: ore scartate, attività scartate,
violazioni nuove, spostamenti. Nessuno parla di **qualità**. Un orario che
piazza tutto senza violare nulla è oggi indistinguibile da un altro che fa lo
stesso lasciando a un docente quattro buchi al giorno.

Questo pezzo aggiunge i livelli che li distinguono.

## 1. ⚠ In EDT i meccanismi sono **due**, e confonderli sarebbe l'errore di
   partenza

`docs/edt/motore-risoluzione.md` li documenta separatamente, e hanno forma
diversa:

| | `Ordinamento dei criteri` | `Ottimizzazione degli orari` |
|---|---|---|
| dove | `Parametri → Piazzamento` | `Parametri → Piazzamento → Ottimizzazione` |
| forma | **undici** criteri, due liste (considerati / ignorati), riordinabili | **tre** slot ordinati, **per popolazione**, su cinque valori |
| quando | durante il piazzamento | in una fase **separata**, dopo |
| popolazione | nessuna | docenti **oppure** classi, mai insieme |

I cinque valori della seconda sono `Nessuno`, `Durata totale dei buchi`
(`tcoTrous`), `1/2 giornate libere` (`tcoDJLibres`), `Attività isolate`
(`tcoIsoles`), `Equilibrio didattico` (`tcoMemesHoraires`). Gli undici della
prima includono in **ultima** posizione `Rispetta le preferenze`, che è il
pennello verde.

**Quello che implementiamo qui** sono i quattro valori dell'ottimizzazione più
il verde, come livelli della catena unica. La distinzione fra le due liste
resta vera in EDT e va conservata nella documentazione; il nostro modello ha
un solo meccanismo perché ha una sola catena.

## 2. I cinque criteri, con la definizione esatta

🔑 **La proprietà che rende questo pezzo economico**: quasi tutte queste
quantità sono **già calcolate** da un checker di `domain/analysis`, dove
servono a essere confrontate con un tetto. Qui la stessa quantità si
**minimizza** invece di raffrontarla. Dove esiste il checker, la definizione si
legge da lì e non si riscrive — è la stessa regola che vale per `B` nei rami
disgiuntivi di ADR-018, e per la stessa ragione: una divergenza di uno renderebbe
il livello una misura di qualcos'altro.

### 2.1 `gaps` — Durata totale dei buchi (`tcoTrous`)

Definizione, letta da `MaxGapChecker.violations`: per ogni mezza giornata con
almeno due fasce occupate, `ultima − prima + 1 − conteggio`, in minuti, sommato
su tutte le mezze giornate. È il **D.T.B.** senza il tetto.

Encoding. La forma `ultima − prima` chiederebbe due `IntVar` per mezza
giornata; si evita con l'equivalenza puntuale: una fascia è **di buco** quando
è libera e ha almeno un'occupazione **prima** e almeno una **dopo**, dentro la
stessa mezza giornata.

```
prima[k,d,s] = OR( occ[k,d,t] per t < s nella stessa mezza )
dopo [k,d,s] = OR( occ[k,d,t] per t > s nella stessa mezza )
buco [k,d,s] ⟺ prima ∧ dopo ∧ ¬occ
gaps = slot_minutes · Σ buco
```

La somma dei `buco` di una mezza giornata è esattamente
`ultima − prima + 1 − conteggio`: le fasce fra la prima e l'ultima occupata
sono `ultima − prima + 1`, di cui `conteggio` occupate.

### 2.2 `isolated` — Attività isolate (`tcoIsoles`)

Definizione letterale del prodotto (`docs/edt/vincoli.md`): *«attività isolata
in una mezza giornata **e** di durata inferiore a due fasce orarie»*.

🔑 Le due condizioni collassano in una sola: **la mezza giornata ha esattamente
una fascia occupata**. Sola e lunga due dà conteggio 2; due attività da una
fascia danno conteggio 2 e nessuna delle due è isolata. Non serve guardare la
durata né l'identità dell'attività.

```
isolata[k,d,h] ⟺ Σ occ[k,d,s per s nella mezza] == 1
isolated = Σ isolata
```

### 2.3 `free_half_days` — 1/2 giornate libere (`tcoDJLibres`)

Massimizzare le mezze giornate libere è minimizzare quelle occupate, e
`Vocabulary.half_active` esiste già.

```
free_half_days = Σ half_active[k,d,h]
```

⚠ **Non** è la quantità di `FreeGuaranteedChecker`, e la divergenza è
deliberata: quel checker conta le mezze libere **solo sui giorni che lavorano**,
perché il vincolo garantisce tempo libero *dentro* la settimana lavorativa. Il
criterio invece ordina orari fra loro, e un giorno intero libero è il caso
migliore, non un caso da non contare.

### 2.4 `regularity` — Equilibrio didattico (`tcoMemesHoraires`)

⚠ La traduzione italiana è fuorviante e il documento lo dice già: l'enum è
`tcoMemesHoraires`, *stessi orari*, e il senso francese (`Régularité des cours`)
è che **la stessa materia ricada sempre nella stessa fascia**, non l'equilibrio
del carico.

```
usa[k,m,s] = OR( x[a,d,s] per ogni attività a di materia m sulla chiave k,
                 per ogni giorno d )
regularity = Σ usa[k,m,s]
```

Minimizzare il numero di **fasce distinte** usate da una coppia (unità, materia)
spinge le occorrenze sulla stessa fascia. Il minimo è 1 per coppia: una materia
sempre alla terza ora.

### 2.5 `preferences` — Rispetta le preferenze (il verde)

Il pre-filtro delle indisponibilità restringe il rosso e il giallo e lascia
passare il verde, con il rimando esplicito a questo pezzo nel proprio docstring.
Qui il verde diventa il termine più economico dei cinque: una somma di
letterali che esistono già.

```
preferences = Σ x[a,d,s]  per le celle in cui una fascia coperta
                          dall'attività cade su un'indisponibilità di livello
                          `preference` per una delle sue chiavi
```

⚠ La copertura è su **tutta la durata** dell'attività, non sulla sola fascia di
partenza: è lo stesso motivo per cui il pre-filtro guarda `range(slot, slot +
duration_slots)`, e il checker itera `pl.slots`.

## 3. L'ordine è un dato

EDT lascia alla scuola l'ordine, e il documento ne fa una lezione di prodotto:
*«"Criteri considerati / ignorati" è una UI onesta: dichiara che
l'ottimizzazione è una scelta editoriale della scuola, non una verità»*. Un
ordine cablato direbbe il contrario.

```python
class QualityCriterion(models.Model):
    kind       # gaps | isolated | free_half_days | regularity | preferences
    population # teachers | classes | all
    rank       # l'ordine lessicografico, crescente
```

- **Tabella vuota ⇒ la catena di oggi, byte per byte.** È la stessa proprietà
  conservativa delle quote («senza righe non nasce niente»), ed è un test, non
  un corollario.
- `population` non è speculativa in vista dello split: la tabella dei criteri di
  calcolo di EDT dà `Gestione dei buchi` come dichiarata *«separatamente per i
  docenti e per le classi»*. È un filtro sulle chiavi, e ha significato oggi.
- ⚠ Le chiavi di **parte di classe** contano per conto proprio accanto a quelle
  di classe, e non è un doppio conteggio per distrazione: il contatore `A.iso.`
  di EDT è dichiarato «per docente/classe/**gruppo**».

## 4. ⚠ Le firme di settimana: un'approssimazione **dichiarata**

Tutte queste quantità si calcolano sull'**unione** delle settimane, cioè con
`signature` omessa.

Questo progetto ha già sbagliato una volta esattamente qui: `MaxGapBuilder`
trattava tutte le attività come co-attive dichiarandolo conservativo, e non lo
era — vincolava **di meno**, ammettendo orari illegali. La ragione per cui il
precedente **non si applica** è la differenza di ruolo, non una svista ripetuta:
là l'errore stava in un vincolo **hard**, e un vincolo hard sbagliato ammette
orari che il checker boccia. Qui la quantità non entra in nessun vincolo di
ammissibilità: entra in un `Minimize`. Un obiettivo approssimato **ordina male**
orari tutti legali; non ne ammette uno illegale.

Il costo dell'alternativa è la ragione della scelta: le firme sono una
dimensione moltiplicativa (misurata sulla fase 5: ~0,3 s per firma), e un anno
reale ne ha 35-40. Cinque livelli × 40 firme sarebbe il conto sbagliato da
pagare per ordinare meglio orari già tutti validi.

## 5. Dove si innestano, e l'invariante che non devono rompere

I criteri sono livelli **dopo** i quattro esistenti: la qualità cede a tutto.
Un orario più bello che scarta un'ora in più è peggiore, ed è la stessa
asimmetria già scritta per L4.

🔑 **L'invariante**: un criterio di qualità non cambia **ciò che il modello
ammette**, solo ciò che preferisce. Posta variabili e uguaglianze di
definizione, mai un vincolo che escluda una soluzione. Ne discende un test
diretto: l'insieme delle soluzioni ammissibili con e senza le righe è lo
stesso, e in particolare nessuna istanza passa da `OPTIMAL` a `INFEASIBLE`.

⚠ Ne discende anche che ADR-018 **non ha niente da dire qui**, e va detto
perché è la prima famiglia di cui è vero: le congelate contribuiscono termini
costanti a una somma da minimizzare. Non esiste il «pretendere una riparazione»,
perché non esiste alcuna pretesa.

## 6. Il criterio di riuscita

1. **Tabella vuota ⇒ nessun livello nuovo, nessuna variabile nuova.**
2. **Ogni criterio migliora la propria quantità**: su un'istanza costruita
   perché due orari ottimi si distinguano solo per quel criterio, il livello
   sceglie quello giusto. Nella forma della casa: si misura il **valore del
   livello**, non «guarda dove è finita l'attività».
3. **L'ordine conta**: due criteri che tirano in direzioni opposte danno
   risposte diverse a `rank` invertito. ⚠ Un'istanza a pareggio non
   dimostrerebbe nulla — è l'errore già commesso e corretto sull'ondata 2.
4. **Nessun criterio restringe**: per ciascuno, un'istanza che senza righe è
   `OPTIMAL` resta `OPTIMAL` con la riga.
5. **Mutazione**: spegnere un criterio rende rosso il test di quel criterio e
   nessun altro.

## 7. Le ondate

1. Il modello `QualityCriterion` + migrazione + la lettura nella catena, con
   **zero** criteri implementati: la tabella vuota è già un test.
2. `preferences` — il più economico, e prova la cucitura da un capo all'altro.
3. `free_half_days` e `isolated`, che vivono entrambi sulle mezze giornate.
4. `gaps`, con la macchina `prima`/`dopo`.
5. `regularity`.
6. `manage.py solve` che riporta i livelli di qualità, e `CLAUDE.md`.

## 7-bis. Il costo, misurato

⚠ **Il numero che conta è arrivato a consuntivo, e cambia una raccomandazione
operativa.** Fermi, 284 attività, cinque criteri accesi:

| | senza criteri | cinque criteri, `--limite 15` |
|---|---|---|
| totale | **1,05 s** | **39,5 s** |
| `gaps_teachers` | — | 0, ottimo, 0,97 s |
| `isolated_teachers` | — | 0, ottimo, 6,70 s |
| `regularity_classes` | — | 247, **non dimostrato**, 15 s |
| `free_half_days_teachers` | — | 117, **non dimostrato**, 15 s |

**Senza limite di tempo il calcolo non è tornato in nove minuti.** I due
livelli cari sono quelli che aprono più simmetrie: la regolarità mette in gioco
ogni coppia (unità, materia) × fascia, le mezze giornate ogni (chiave, giorno,
metà). La catena resta corretta — un livello che scade fissa l'ultimo valore
trovato invece dell'ottimo, quindi diventa meno ambiziosa, mai sbagliata — ma
il limite per livello smette di essere una precauzione e diventa parte
dell'uso normale. È dichiarato nel docstring di `manage.py solve`.

⚠ E come sempre sul Fermi, **questa è una misura del costo e mai della
copertura**: il dataset non ha righe `QualityCriterion` di suo, e i criteri qui
sopra sono stati creati apposta per misurare.

## 8. Fuori scope, dichiarato

- **La separazione per popolazione** e la **perdita di qualità tollerata**.
  EDT ottimizza docenti *oppure* classi e dichiara quanto è disposto a
  peggiorare l'altra. Il meccanismo di fissaggio della catena è già la metà del
  lavoro (`<= valore` diventa `<= valore + tolleranza`), ma la scelta di *quale*
  popolazione ottimizzare è un parametro di lancio, non una politica: va
  progettata con il comando, non con l'obiettivo.
- **I sei criteri di piazzamento** che non hanno un valore corrispondente
  nell'ottimizzazione (allineamento, turni di mensa, buchi quindicinali,
  distanza fra occorrenze della stessa materia…).
- **Le quattro modalità dei massimi orari** (per settimana / per ciclo / media
  su 2 settimane con scarto). Restano il debito dichiarato in
  `motore-risoluzione.md`, e riguardano i vincoli hard, non questi livelli.

## 9. Esito — a consuntivo

Sei ondate su sei. Cinque criteri, diciassette test, **nove mutazioni con nove
esiti distinti**.

⚠ **Due difetti trovati nei test, non nel codice, e sono la stessa forma.**
`_dimensioni` costruiva il solo `build_model`, ma i livelli di qualità nascono
dentro `livelli()`: con e senza righe dava lo stesso numero, cioè
un'asserzione incapace di fallire. Corretto — e la correzione ha scoperto il
secondo: il test misurava **due volte lo stesso stato**, perché per la
proprietà «tabella vuota» non c'è nessuna riga da aggiungere in mezzo. Il
confronto è ora contro il modello **nudo**, e la differenza attesa è esatta (le
due variabili di L1 e L2 con le loro uguaglianze). Solo così la mutazione «una
variabile di troppo a tabella vuota» diventa rossa.

Il primo dei due l'ha trovato la misura sul Fermi, non una rilettura: le
dimensioni non si muovevano di un bit con cinque criteri accesi.
