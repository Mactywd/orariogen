# Changelog

Il racconto datato di come le cose sono state fatte, e **perché**: le misure,
le previsioni smentite, le semplificazioni che si sono rivelate false. Si
legge dal fondo per la storia, dall'alto per lo stato.

⚠ **Questo file non si legge tutto.** Viveva dentro `CLAUDE.md`, dove valeva
l'81% di un file caricato in ogni sessione — 165 KB di racconto davanti a 39 KB
di istruzioni. Sta qui perché lo si apra quando serve: `CLAUDE.md` porta lo
stato corrente, `docs/todo.md` le cose da fare, e questo file il perché di
quelle già fatte.

> **Come si scrive una voce.** Data, titolo, e poi cosa è cambiato *e cosa ha
> smentito*: le misure con i numeri veri, le proprietà dichiarate che si sono
> rivelate false, le decisioni scartate col motivo. Una voce che dice solo cosa
> è stato aggiunto la dice il diff.

- **2026-08-31 (sera) — O5: due criteri di piazzamento su dieci, e il costo che
  hanno reso visibile** —
  [ADR-025](decisioni.md). O5 era l'ultima decisione di prodotto che avesse
  materiale pronto: [criteri-di-piazzamento.md](criteri-di-piazzamento.md)
  prendeva i dieci criteri di `Ordinamento dei criteri` uno per uno con una
  raccomandazione, e mancava solo la firma. È **due sì e otto no**.

  🔑 **La decisione non è quali due: è che cambiano meccanismo.** In EDT quegli
  undici governano un'**euristica di ricerca** — l'ordine in cui il motore
  prova le collocazioni — e in CP-SAT quell'oggetto non esiste. Tradurne uno
  significa spostarlo nell'**altro riquadro**, `Ottimizzazione degli orari`,
  dove diventa un livello lessicografico. Non è la stessa cosa, e la direzione
  è quella prudente: un criterio non posta vincoli di ammissibilità, quindi non
  può rendere infattibile ciò che un'euristica al più rallentava.

  **I due che entrano.** Il **4**, `Distribuisci nella settimana le attività
  della stessa materia` → `WEEKLY_SPREAD` sulle classi: è l'unico che dice una
  cosa che oggi sapevamo esprimere **solo come divieto**, e un divieto rende
  infattibile dove un criterio peggiora e basta — un test lo misura, stessa
  istanza, `1` col criterio contro **un'attività scartata** col divieto.
  L'**8**, `Evita le attività della stessa materia nella stessa ora` →
  `SLOT_SPREAD` sui **docenti**: è `regularity` col segno opposto, e la sua
  assenza era un'asimmetria involontaria dove EDT ne ha una voluta — per la
  classe la ripetizione è una routine, per il docente è una condanna.

  ⚠ **Una delle otto righe rosse ha cambiato motivo mentre la si leggeva.** Il
  **5**, `Riduci i buchi quindicinali`, era «fuori *per ora*, ma è l'unico no
  che nasconde un difetto»: i criteri di qualità ignoravano le firme di
  settimana. **L7 quel difetto l'ha pagato** la mattina stessa, quindi il 5 è
  passato a **già dentro** senza che nessuno lo traducesse. Il **6** è
  l'unico no che costa qualcosa: `gaps` con l'unità cambiata — buchi invece di
  minuti — costa mezz'ora e resta fuori perché due criteri quasi identici nella
  stessa lista sono una UI peggiore, non migliore.

  🔑 **Un dividendo non previsto: tre criteri, una funzione.** Scrivendoli si è
  visto che il 4, l'8 e `regularity` contano tutti *quanti secchi distinti* usa
  la stessa materia per la stessa unità, e cambiano solo il **secchio** (la
  fascia o il giorno) e il **segno** (pochi o molti). `_secchi` è quindi una
  funzione sola e `regularity` è stato riscritto su di essa **senza che nessuno
  dei suoi numeri si muovesse**. ⚠ La quantità è `occorrenze − secchi
  distinti`, non «coppie nello stesso secchio»: lineare invece che quadratica,
  tre ore in un giorno costano 2 invece di 3, e un test fissa proprio quel
  numero perché è dove le due letture divergono.

  ⚠ **E `REGULARITY` con `SLOT_SPREAD` sulla stessa popolazione è inerte.** Non
  c'è un vincolo che lo vieti — sarebbe una proibizione su una configurazione
  che non fa danno, solo nulla — e un test lo **misura**: il primo fissa i
  secchi distinti al proprio ottimo, il secondo assume il valore complementare
  e non sceglie più niente.

  🔑 **Il difetto che i due criteri hanno trovato, ed è il pezzo che vale più
  della decisione.** Aggiungendo `weekly_spread` come **sesto** livello, il
  **primo** — `minuti_scartati`, che di quel criterio non sa nulla — passava da
  9,2 s a **33,6 s**; con due criteri nuovi a **71 s**, e la catena che in sei
  arrivava in fondo in 98 s moriva al quarto livello. La causa: il modello si
  costruiva **intero** prima che la catena partisse, quindi ogni livello pagava
  le migliaia di variabili derivate dei criteri **sotto** di lui. Ora ogni
  criterio si costruisce **immediatamente prima del proprio livello**
  (`Level.costruisci`), il che è lecito perché la catena è un `Solve` per
  livello sullo stesso modello e quel modello già muta fra l'uno e l'altro. Il
  primo livello del banco è sceso a **2,6 s** — cioè meno di prima di O5, coi
  soli sei criteri storici.

  ⚠ **Il rovescio: l'arbitrato non può rimandare niente.** I tetti di
  non-regressione **restringono**, quindi vanno costruiti prima del primo
  `Solve`. Con tre criteri sacrificati invece di due il modello cresce di ~5000
  variabili in testa e `gaps_teachers` non produce alcuna soluzione nei suoi
  15 s — misurato a tolleranza **5, 60 e 180**, cioè non è la strettezza del
  tetto, è il peso. Il test dell'arbitrato misura quindi il **meccanismo** sui
  sei storici, e la misura degli otto sta scritta accanto invece che nascosta.

  ⚠ **E con otto criteri la catena del banco non arriva più in fondo**: il nono
  livello non conclude e i due dopo di lui non compaiono. Non è la quantità dei
  due criteri nuovi a essere dura — da soli chiudono senza fatica,
  `weekly_spread` 220 e `slot_spread` 120 con limite inferiore 51 — è la loro
  **posizione**: ogni livello è più duro del precedente perché quelli sopra
  sono fissati al valore che la ricerca *ha trovato*, non a un ottimo
  dimostrato. Il test asserisce ora un **prefisso**, e che i sei storici
  arrivino tutti in fondo.

  Il banco porta le due righe nuove (`weekly_spread` classi, `slot_spread`
  docenti): il cricchetto della qualità è `{r.kind} == set(Kind.values)`, cioè
  la tabella intera, e ha morso appena l'enum è cresciuta — che è il suo
  mestiere. **960 test verdi**, 17 skip.

- **2026-08-31 — I cinque difetti del banco, chiusi: e tre di essi erano del dato** —
  Il banco L4 ha prodotto cinque difetti e non ne ha riparato nessuno: la spec
  (§8) vietava di modificare il motore mentre lo si misurava, e ognuno è
  rimasto fissato da un test che asseriva il comportamento **sbagliato**.
  Questa voce chiude il conto. Nessun difetto è stato «sistemato»: ognuno aveva
  una **decisione** aperta scritta nel todo, e la parte che vale è quale
  decisione è stata presa e contro cosa.

  🔑 **L5 — l'allineamento genera l'attività complessa**
  ([ADR-022](decisioni.md)), ed è il
  ventottesimo builder (`structural:alignment`) e il trentunesimo checker
  (`alignment_split`). Le due decisioni aperte: **hard e non alleggeribile**
  (alleggerire un allineamento vorrebbe dire scomporre l'attività complessa,
  cioè cambiare l'anagrafica — non un vincolo), e **tutto il gruppo sulla
  stessa cella o niente**, perché la forma debole «la stessa cella *se*
  entrambe piazzate» è soddisfatta anche dal gruppo mezzo scartato, che è la
  mezza classe abbandonata a scuola con un altro nome. Dominio comune vuoto ⇒
  il gruppo si scarta, mai `INFEASIBLE`.

  🔑 **E leggere un campo che nessuno leggeva ha corretto il *dataset*, in
  quattro punti.** È la scoperta della giornata, e va detta per prima perché è il
  genere di cosa per cui il banco esiste: una dichiarazione che nessuno legge
  può dire il falso per mesi. (1) *Sdoppiare non è allineare*: le due metà del
  laboratorio avevano lo stesso ident, ma hanno lo **stesso docente** e non
  sono mai simultanee — è insoddisfacibile per costruzione, ed è lo stesso
  argomento con cui l'ondata 6 aveva rifiutato di allineare l'ora
  quindicinale. (2) 📦 *«autant d'alignements que de cours complexes
  souhaités»*: tre ore parallele sono **tre** attività complesse, non una da
  sei ore — con un ident solo il modello fondeva sei attività su una fascia e
  ne scartava quattro. (3) L'articolata *«nelle stesse tre ore»*, lo spezzone
  di RICCI concentrato in un pomeriggio e il tetto di peso d'indirizzo erano
  **insieme impossibili**: tre ore di latino (peso 2) in un pomeriggio pesano
  6 contro un tetto di 5. Isolato spegnendo i builder uno per uno —
  `DidacticWeightBuilder` era l'unico che, tolto, rendeva il pin fattibile.
  Lo spezzone è ora su **due** pomeriggi, e il bordo non si è mosso: tre fasce
  libere per tre ore (la tacca dell'ondata 3 si sposta da `(2, 7)` a
  `(4, 7)`). (4) E il `MG` è passato da R02 Donati a **P02 Bruni**: onorato
  l'allineamento, l'orario dell'insegnante di alternativa *è* quello del
  cappellano, che viene due giorni — dodici ore in due giornate con una sola
  mezza giornata ciascuna fanno al più dieci. La riga su Donati aveva smesso
  di essere un vincolo su di lei per diventarne uno sul cappellano, cioè aveva
  perso il **soggetto**; la deroga l'ha seguita, e la sua tensione è diventata
  un **pin** invece di una riga di presenza (su Bruni una riga di presenza
  fallirebbe per la palestra, che è una sola — misurato: `INFEASIBLE` anche
  con la deroga, cioè il testimone sbagliato). Misure: **16 → 18 ident, 40 →
  36 attività allineate, 18 gruppi coincidenti su 18**, `OPTIMAL` a zero
  scarti.

  🔑 **L6 — un insieme non viaggia, e la decisione è stata *cambiare la
  domanda*** ([ADR-023](decisioni.md)). Il todo chiedeva quale criterio
  dicesse «questa chiave viaggia»,
  col candidato `simultaneous_capacity > 1` e la sua obiezione (l'aula col
  `Numero di aule` di EDT, che invece un luogo ce l'ha). La domanda non ha
  risposta perché è la domanda sbagliata: quella giusta non è «due sedi si
  toccano?» ma «**ci stanno?**». Il vincolo è ora un tetto di capienza,
  `carico(sa, s) + carico(sb, t) <= posti`, nel builder e nel checker con la
  stessa disuguaglianza. A capienza 1 — ogni docente, classe, parte, atomo —
  coincide **riga per riga** con la clausola booleana di prima (due carichi
  valgono almeno due, un posto non li regge), quindi l'obiezione dell'aula
  cade da sé: cambiano solo le due risorse per cui la vecchia regola diceva il
  falso. Misura sul banco: era `INFEASIBLE` a capienza 4 con domanda 3 e
  `INFEASIBLE` anche a capienza **9**; ora `OPTIMAL` a 4, `OPTIMAL` a 3 (il
  bordo esatto), `INFEASIBLE` a 2.

  ⚠ **Una conseguenza non prevista, e un errore che il banco che congela ha
  trovato.** La conseguenza: il ramo `s == t` — la riparazione «Important 1 /
  Ruling 33» — è ora **implicato da `structural:occupation`** (il carico di un
  sottoinsieme di una cella non può superare la capienza se il totale non la
  supera); resta postato perché ogni builder deve essere corretto da solo, ma
  non vieta più niente di nuovo.

  L'errore: la prima stesura **tolse** la guardia `_sede_congelata` scrivendo
  che `residual_cap` la conteneva. È falso, e `tests/test_solver_frozen.py`
  l'ha detto sui semi 6 e 9 — `INFEASIBLE` sulla prova A, cioè il modello che
  rifiuta l'orario che gli è stato dato. Col residuo clampato a zero ogni
  **libera** viene cacciata dalle celle in cui la coppia è già rotta, comprese
  quelle in cui già stava: la metà vietata di ADR-018, precisa.
  🔑 E la differenza con `structural:occupation`, che invece clampa e fa bene,
  è la **forma del finding**: là la causale nomina *tutte* le attività della
  cella, quindi una libera che si aggiunge cambia la chiave ed è un finding
  nuovo; qui nomina una **coppia**, e la coppia (libera, congelata) esisteva
  già nella baseline. La guardia resta, generalizzata: il tetto non si posta
  quando le sole congelate lo hanno già superato.

  🔑 **L6bis — il giallo lo conta anche la fase 1** (emendamento ad
  [ADR-021](decisioni.md)), e la decisione si prende
  guardando **chi paga**. L'argomento che teneva `structural:room_pool` com'era
  — *«l'opzionale è violabile per definizione, contarlo come chiuso
  produrrebbe un finding HARD per un ostacolo che duro non è»* — si rovescia:
  l'ostacolo è duro *finché non lo si autorizza*, ed è la frase letterale
  della documentazione. La fase 2 lo toglie dalle candidate; contarne i posti
  in fase 1 significava promettere un'aula che nessuno avrebbe potuto usare.
  Il builder legge l'autorizzazione (`ignora_opzionali`, per **categoria** di
  risorsa — A4), il checker no e non può: legge un orario, non i parametri di
  un calcolo. È la stessa asimmetria che `structural:unavailability` ha da
  sempre. Misura: il pin che prima era `OPTIMAL` in fase 1 e una rinuncia in
  fase 2 è ora `INFEASIBLE` **prima**, e con l'override torna `OPTIMAL` in
  entrambe.

  🔑 **L7 — i criteri di qualità contano per firma, e il livello è la
  settimana peggiore** ([ADR-024](decisioni.md)). La decisione qui era
  l'**aggregazione**, e le tre
  candidate danno tre numeri diversi sullo stesso testimone: somma delle firme
  360, somma pesata per settimane 5940, massimo **180**. Vince il massimo per
  la regola della casa — *dove il checker esiste, la definizione si legge da
  lì*: 180 è il numero che `check_schedule` conta. La somma direbbe 360 e
  farebbe dipendere il valore da quante firme ha il dataset; la pesata è la
  quantità annuale, vera ma di un'altra unità — e `Arbitrato.tolleranza` è un
  numero che l'utente scrive nell'unità del criterio. ⚠ Il prezzo, dichiarato:
  sul massimo, migliorare una firma che non è la peggiore non muove il
  livello. ⚠ E il costo moltiplicativo che il todo temeva **non si paga**: le
  firme si deduplicano come in `ResourceBuilder`, e su un dataset a firma
  unica non cambia nessun numero — i venti test di `test_solver_qualita.py`
  sono passati senza toccarne uno.

  🔑 **L8 — la soglia è quella raggiungibile.** Delle due strade aperte nel
  todo è stata presa la prima: `free_half_days >= min(richieste, giorni
  lavorati)`, nel checker e nel builder insieme (`AddMinEquality`, una
  definizione e non un vincolo). Non è un'attenuazione: è la garanzia detta
  senza la parte che nessun orario potrebbe onorare, perché una mezza giornata
  libera conta solo su un giorno lavorato e un giorno lavorato ne offre al più
  una. La seconda strada — contare diversamente — resta esclusa per la ragione
  di sempre: accetterebbe orari che il checker boccia. ⚠ E `free_days` **non**
  prende lo stesso trattamento, ed è la metà che spiega la prima: lavorare
  meno *aumenta* i giorni liberi, quindi quel minimo non è mai reso
  irraggiungibile dallo scarto.

  ⚠ **Ogni test capovolto porta il suo ramo di controllo**, perché «il difetto
  non c'è più» da solo è soddisfatto anche da un vincolo spento: la capienza
  dei carrelli scende 4 → 3 → 2 (tacca), la fase 1 sul giallo si rimette in
  piedi con l'override, il criterio dei buchi distingue le due firme quando si
  toglie il laboratorio (360 contro 180), e L8 pretende che i due rami — con
  la riga `free_guaranteed` e senza — diano lo **stesso** numero di scarti.

  ⚠ **E quattro test che non parlavano dei difetti sono cambiati lo stesso**,
  perché erano scritti sopra la semantica sbagliata: i due di
  `test_solver_sites.py` sul ramo `s == t` (costruiti su un'aula a due posti
  *senza sede*, dove la vecchia regola vietava ciò che ora è lecito — quello
  di ADR-018 ha ora **tre** congelate invece di due, perché con due il passato
  non sarebbe più in violazione e il test non misurerebbe niente) e i due di
  `test_analysis_ordine_inserimento.py`, dove l'indipendenza dall'ordine si
  misura ora su un carico che sfora davvero (`1 + 2 > 2`).

- **2026-08-30 (notte) — L'Alighieri, ondata 7: i comandi, e due attese smentite di natura diversa** —
  L'ultima ondata non aggiunge una riga al dataset. Aggiunge la domanda che sta
  a valle di tutte le altre, §7 della spec: **i cinque comandi diagnostici
  hanno qualcosa di vero da dire su questa scuola?** Un comando che gira, non
  va in errore e risponde *«niente da segnalare»* è verde e non prova niente —
  è il rischio di §6 alla scala del prodotto invece che a quella del builder.
  Dettaglio in
  [`data/liceo-alighieri/comandi.md`](../data/liceo-alighieri/comandi.md);
  **sedici test** in `tests/test_alighieri_comandi.py`, e la suite passa da 930
  a **946 verdi**. **Il pezzo L4 è chiuso.**

  🔑 **Il criterio di accettazione era già raggiunto, e il lavoro dell'ondata 7
  è che resti fermo.** La sonda dice **27 su 27** dall'ondata 5, asserita come
  **insieme** e non come numero: un builder che smettesse di lavorare mentre un
  altro comincia passerebbe un `>= 27` e non passa un `==`.

  **Cosa dicono i comandi.** La classifica dei vincoli ordina **quindici**
  famiglie in 63 righe, e la prima è un vincolo di **materia**; sul Fermi sono
  tre righe e **una** causale, `{"unavailability"}` — cioè *letteralmente* le
  «tre indisponibilità» che §7 dichiara insufficienti. La fase 5 nomina **un**
  insieme deficiente quando si stringe il laboratorio unico della succursale.
  Tutti e **sei** i rilevatori di `Estrai` trovano almeno un'attività, e
  nessuno è muto. `place_and_fix` costa **tre** attività spostate contro l'una
  del Fermi. `assign_rooms` è `INFEASIBLE` in fase 1 col gruppo di aule, e
  rinuncia senza.

  ⚠ **Prima attesa smentita, e la sbagliata era l'attesa.** Sul dataset **a
  riposo** la classifica dà **tre** causali, non le cinque previste:
  `unavailability`, `arrival_departure`, `break_straddled` — cioè le sole
  famiglie **unarie**. 🔑 La ragione sta in `blame.py`: `free_candidates`
  **spiazza tutte le candidate** prima di calcolare i domini, quindi su un
  orario dove niente è congelato l'occupazione non occupa e un vincolo *fra due
  ore* non ha soggetto se sono libere entrambe. Ed è coerente col mestiere
  dello strumento — *«il calcolo è fallito, cosa allento?»* è una domanda che
  si pone su un orario **quasi fatto**. Sulla variante satura (tutto congelato
  tranne nove occorrenze) sono quindici.

  ⚠ **Seconda attesa smentita, e la sbagliata era il dataset: il tetto di
  non-regressione non morde.** Sei configurazioni misurate — le due
  popolazioni, tolleranze da 0 a 6000, e la base portata a zero da una prima
  ottimizzazione — e in **tutte** i buchi della popolazione ottimizzata
  scendono a zero e lo **dimostrano**. Non c'è competizione: quaranta fasce per
  ventinove ore di lezione lasciano a docenti e classi abbastanza spazio da non
  togliersi niente. ⚠ E la strada del criterio *non dimostrato* è stata provata
  e scartata: sacrificando `free_half_days_teachers` i valori sono usciti
  121 / 122 / 124 al crescere della tolleranza — nella direzione **sbagliata**,
  con un divario di oltre cento. È l'ondata 6 che si paga due volte.

  🔑 **La risposta è la terza forma di verifica, quella dell'ondata 6: si mette
  il dataset in tensione.** Tre pezzi, ognuno necessario: la base si porta a
  zero con un primo arbitrato sulle classi (che è letteralmente il primo dei
  due comandi di EDT); la classe 1A si rende indisponibile a metà mattina
  **prima** di quel calcolo, così l'orario di partenza resta legale — ⚠
  invertire i due passi dà `base: None`, che è il modo corretto in cui
  `_valori_di_base` dice *«l'orario di partenza non è rappresentabile in questo
  modello»*; e due ore di italiano si **puntano** ai lati del buco. I tre
  verdetti tornano quelli delle quote: `INFEASIBLE` a tolleranza 0,
  `INFEASIBLE` a 60 — **la riga che porta l'informazione** — e `FEASIBLE` a
  180. Il buco vale 60 minuti per **tre chiavi**, la classe e le sue due parti:
  la stessa aritmetica di L7.

  🔑 **E due contratti si sono dovuti riscrivere come argomenti invece che come
  misure.** La prima stesura li faceva passare misurando l'ottimo che la
  ricerca aveva scelto: otto imposizioni sulla succursale costavano 2
  spostamenti ogni volta, e un calcolo libero senza il gruppo di aule dava una
  rinuncia in una esecuzione e due nell'altra. Riscritti: `place_and_fix` cerca
  una cella dove due attività **diverse** confliggono con la terza — una per la
  classe, una per il docente — così «almeno due si spostano» è vero per
  costruzione e nessun ottimo lo può evitare; e il gruppo di aule si prova col
  **testimone puntato** dell'ondata 4, tre ore di fisica sulle stesse due aule
  candidate imposte sulla stessa cella, con `INFEASIBLE` col builder e
  `OPTIMAL` senza. È la lezione dell'ondata 3, applicata ai comandi.

  🔑 **Il deficit di Hall non è «undici ore meno otto celle».** Il comando
  dichiara **9h00 contro 8h00 su nove attività**: il certificato è un
  **insieme deficiente minimale**, non un totale. Ed è il verdetto più utile
  dei due — *«mancano tre ore»* non dice dove guardare, *«queste nove hanno in
  comune otto ore di finestra»* nomina il gruppo da spezzare.

  ✅ **E il criterio di §4 della spec è verificato sul dataset intero** —
  l'ultimo rimasto senza verdetto, e tre file del banco lo rimandavano qui.
  Spento `LAB-SUCC` il banco scarta **11** attività, cioè quelle che lo
  chiedono; spento un docente, le sue ore (3, 12, 20 sui tre campionati);
  l'aula magna, che nessuno usa, non costa niente. ⚠ **«Una» aula, non
  «qualunque»**: il criterio dice che il banco ha un punto in cui è teso, e i
  punti si misurano.
  🔑 **Ma «stretto» ha due nozioni, e la spec ne dichiarava una sola.** Questa
  è stretta rispetto alle **risorse** — togline una e qualcosa cade; la
  contiguità che il D.T.B. chiede è stretta rispetto alla **densità della
  griglia**, e con quaranta fasce contro cattedre da 10–21 ore resta gratis.
  I due test che asseriscono l'`OPTIMAL` — il D.T.B. dell'ondata 3 e la tacca
  dei divieti della 4 — restano verdi **e restano giusti**, e il «diventerà
  rosso all'ondata 7» che li accompagnava era sbagliato: corretto nei tre
  file dove stava scritto.

  🔑 **E misurando quel bordo il banco ha trovato il suo quinto difetto, L8:
  lo scarto non è una via d'uscita universale.** Spegnendo la palestra il
  modello non scarta, risponde `INFEASIBLE` — che è ciò che
  `allow_unplaced=True` dovrebbe rendere impossibile. La causa è **una sola
  riga**, isolata togliendone dieci una per volta: `free_guaranteed` su P01
  Zanetti, il docente di scienze motorie. Con la palestra spenta gli restano
  le sole ore della succursale, e il solver ne piazza **una**, su **un**
  giorno: la riga chiede due giornate libere — che ci sono — e due **mezze**
  giornate libere, che non ci sono, perché una mezza giornata libera conta
  solo su un giorno **lavorato** (`libera = attivo AND NOT meta`, com'è nel
  checker) e con un giorno lavorato il massimo è uno.
  🔑 È l'immagine speculare della trappola che `FreeGuaranteedBuilder`
  documenta, e non è un errore del builder: contare le mezze libere su tutti i
  giorni accetterebbe orari che il checker boccia. Il fatto nuovo è la
  **conseguenza** — una famiglia che conta una quantità *sui giorni in cui si
  lavora* può diventare insoddisfacibile **perché si lavora meno**. ⚠ E il
  costo è di prodotto: chi ha spento una palestra legge `INFEASIBLE` invece di
  «queste dieci attività non si piazzano», cioè la diagnosi peggiore delle
  due. Non riparato (§8), fissato col suo ramo di controllo, aperto come
  **L8**.

  ⚠ **E la rinuncia inevitabile mostra la fase 1 che fa due cose opposte,
  entrambe corrette.** Sulle attività **libere** il gruppo di aule conta zero
  posti nella cella dalle candidate rosse e le manda altrove — senza il
  ricalcolo le rinunce sono due, perché un'altra ora di laboratorio stava lì.
  Sull'**immobile** tace, perché `RoomPoolBuilder` esce quando nessuna delle
  attività in causa è libera: *«un fatto, non una decisione»*.

- **2026-08-30 (notte) — L'Alighieri, ondata 6: l'ora quindicinale, le due forme dell'alleggerimento, e un debito che diventa una misura** —
  Tre cose che nessun dataset aveva mai messo in moto: la **seconda firma di
  settimana**, le **quote di alleggerimento** nelle due forme e la **gerarchia
  completa** dei criteri di qualità. Modello di fase 1 a **15 330 variabili e
  13 817 constraint**, `OPTIMAL` a zero scarti in ~9 s; fase 2 ancora **73 su
  73**; sonda **ferma a 27 su 27**, che da qui è il comportamento giusto.
  Dettaglio in
  [`data/liceo-alighieri/quindicinale-e-quote.md`](../data/liceo-alighieri/quindicinale-e-quote.md).

  🔑 **La quindicinale è la quinta forma di erogazione, e la sola che non costa
  un'ora.** La seconda ora di scienze del 5B è a settimane alterne — una in
  laboratorio col tecnico, una di teoria in aula — cioè due attività con
  maschere complementari. In ogni settimana ne è attiva esattamente una, quindi
  la cattedra di N02 resta a 10 ore e l'alunno ne riceve 2: lo sdoppiamento
  delle ondate 2 e 4 fa **ripetere** l'ora al docente, questa no. *Sdoppiare* e
  *alternare* sono due cose diverse, e la differenza è tutta nella maschera.
  ⚠ E l'allineamento resta **vuoto**: 📦 lo XSD dichiara che l'allineamento
  genera *una* collocazione, e le due metà non sono simultanee mai. Allinearle
  direbbe il contrario di ciò che sono.

  🔑 **Ed è il primo dataset a chiedere all'occupazione ciò che sa fare.**
  `OccupationBuilder` è l'unico builder che distingue le firme di settimana — lo
  dichiara nel suo docstring dal giorno in cui è stato scritto — e nessuno
  gliel'aveva mai chiesto. Le due metà stanno sulla stessa classe, quindi
  condividono la chiave di occupazione: **possono stare nella stessa cella**, e
  solo perché le maschere non si intersecano. Testimone puntato, con il suo
  ramo di controllo: `OPTIMAL` con le due metà sulla stessa cella,
  `INFEASIBLE` con una metà e l'ora settimanale. Ed è poi come una scuola
  scrive davvero un'ora quindicinale — «scienze al martedì alla terza» — e
  cambia solo cosa ci si fa dentro.

  ⚠ **Un'attesa smentita, e la sbagliata era l'attesa.** Scritta prima:
  *«variabili e constraint circa il doppio, il vocabolario è per firma»*.
  Misurato: **+86 variabili e +1562 constraint**, cioè +0,6 % e +12,7 %. 🔑 Una
  seconda firma **non raddoppia il modello: costa quanto le attività che la
  distinguono** — le variabili derivate nascono solo dove un builder posta
  qualcosa, e `OccupationBuilder` deduplica i constraint identici fra firme. ⚠ E
  non contraddice la nota di `quality.py` che chiama le firme *«una dimensione
  moltiplicativa (~0,3 s per firma)»*: quella misura è sulla **fase 5**, dove
  ogni checker gira una volta per firma. Là è moltiplicativo davvero; nel solver
  no. La decomposizione è misurata riga per riga: ondata 5 15 233 / 12 251, con
  le sole quote 15 244 / 12 255, con la sola quindicinale 15 319 / 13 813.

  🔑 **Le quote hanno una forma di verifica propria**, la terza del banco
  accanto alla tacca dell'ondata 3 e al testimone puntato dell'ondata 4: si
  mette il dataset **in tensione** e si pretende che la quota lo rimetta in
  piedi, che senza la quota non ci stia, e che con una quota **troppo piccola**
  nemmeno. La riga di mezzo è quella che porta l'informazione — è l'unica che
  distingue «la quota c'è» da «la quota è quella giusta», ed è la mutazione che
  il docstring di `RelaxationQuota` chiede per nome (*«"la quota è collegata"
  passa anche se il margine vale dieci volte quello dichiarato»*). Sul
  cappellano: quota 0 → `INFEASIBLE` (4 + 4 fasce), quota 1 → `INFEASIBLE`
  (4 + 7 = 11 per dodici ore), quota 2 → `OPTIMAL` (7 + 7 = 14, e ne servono
  tredici col viaggio).

  ⚠ **E le quote del dataset non sono consumate dal dataset**, che sembra una
  rinuncia e non lo è: una quota consumata **è** una violazione nominata — la
  quota autorizza il solver a produrla e non la nasconde — e l'ondata 3
  pretende che l'orario di base non porti nessun finding `HARD` oltre alle aule.
  Le righe stanno nel dataset perché i builder le leggano su dati veri (**+11
  variabili, +4 constraint**: la misura dice che le leggono), e i due portatori
  sono scelti perché **non sono bordi** di nessuna ondata precedente —
  allentare un bordo dell'ondata 3 spegnerebbe la sua tacca.

  ⚠ **Un test che misurava il propagatore invece del modello.** La prima
  taratura del margine metteva la presenza a cinque fasce e faceva dimostrare
  al caso di mezzo *5 + 7 = 12 fasce per dodici ore più la fascia di viaggio*:
  vero, e il solver non ci arrivava — `UNKNOWN` a 180 s, e di nuovo a 120 s. Il
  legame «solo due giornate sono attive» passa da booleani che il rilassamento
  lineare non lega ai minuti. Due correzioni: le due giornate si dichiarano col
  **rosso** (il pre-filtro toglie le celle, e le giornate diventano due
  *davvero*) invece che col `days`, e l'aritmetica si sposta tutta sulle ore. I
  tre casi chiudono in 37 s. 🔑 **Un test che misura la potenza del propagatore
  invece di una proprietà del modello è un test che un giorno diventa rosso da
  solo.**

  🔑 **E il verde dell'ondata 5 chiude il suo anello.** La riga `preferenza`
  mette AMATO in verde sulla prima fascia di tutti i giorni: l'ondata 5 ha
  provato che **non vieta** — l'orario esiste lo stesso — e qui si prova che
  **conta**: col solo criterio delle preferenze installato, `preferences_all`
  scende a zero e lo dimostra, cioè nessuna ora di AMATO finisce alla prima
  fascia. Un pre-filtro che non filtra e un criterio che non conta si
  somigliano molto, e sono cose diverse.

  ⚠ **E il «da solo» è una seconda attesa smentita.** Il test nasceva sulla
  gerarchia intera, e la prima misura dava zero; la seconda ha dato **1**. Non
  è il verde a essere incerto: i tre livelli sopra di lui esauriscono il budget
  senza dimostrare il proprio ottimo, quindi vengono fissati al valore che la
  ricerca *ha trovato*, che cambia da esecuzione a esecuzione — e con esso
  cambia la regione in cui il verde deve stare. 🔑 **Un livello sotto un
  livello non dimostrato eredita l'indeterminatezza di quello**, ed è una
  proprietà della catena lessicografica che nessuna misura aveva ancora
  esposto. Per la stessa ragione il rendiconto della catena asserisce che
  **almeno un** livello chiude col divario aperto, non quali.

  ⚠ **La qualità costa, e `build()` non la installa.** Sei livelli portano un
  `solve` sul banco da 9 a **82 secondi**, e ogni test dell'Alighieri li
  pagherebbe. È anche la forma giusta: in EDT l'ottimizzazione è un comando a
  sé che si lancia su un orario che già c'è — `Ottimizza gli orari dei docenti`
  non è una fase del calcolo. La catena dice quale ottimo ha dimostrato:
  `gaps_teachers` e `gaps_classes` a **0** provati, `preferences_all` a 0
  provato, e `isolated_all` 71, `free_half_days_teachers` 143,
  `regularity_classes` 936 col divario aperto. La lezione del Fermi si ripete a
  scala maggiore: un livello di qualità non è lento perché difficile da
  ottimizzare, è lento perché **impossibile da dimostrare**.

  ⚠ **E il difetto nuovo, L7: i criteri di qualità ignorano le firme di
  settimana.** È il debito che L3 aveva aperto **il giorno prima** come
  sospetto — *«nessuna delle due basi lo esercita»* — e la seconda metà non è
  più vera. Testimone aritmetico: il 5B al lunedì, italiano alla prima e alla
  quarta fascia, la metà di laboratorio alla seconda e quella di teoria alla
  terza. Settimana pari 0-1-3, buco alla 2; settimana dispari 0-2-3, buco alla
  1; **unione** 0-1-2-3, nessun buco. Sullo stesso orario la stessa quantità
  vale 60 minuti in *ogni* settimana dell'anno per `check_schedule` e **zero**
  per il criterio `gaps`. 🔑 E non è un difetto nuovo: è **lo stesso** che
  `MaxGapBuilder` aveva fino al 2026-08-24, descritto per esteso nel docstring
  di `Vocabulary.covered`. Il builder passa `signature`; i criteri no. Non
  riparato (spec §8): è **L7** in `docs/todo.md`, fissato da un test col suo
  ramo di controllo — con la metà di teoria non piazzata l'unione ha davvero il
  buco e il criterio dice 180.

  Suite: **930 verdi, 17 skip, 945 s** (ondata 5: 910 / 546 s). ⚠ I quattro
  minuti in più non sono la seconda firma — il modello cresce dello 0,6 % —
  ma i solve che le due nuove prove **devono** fare: sei verdetti
  `INFEASIBLE`/`OPTIMAL` sulle quote e due catene di qualità intere.

- **2026-08-30 (notte) — L'Alighieri, ondata 5: le risorse che mancavano, e i due modi di provare una riga** —
  Le **sei righe di indisponibilità** nei tre livelli, i **tetti di peso
  didattico**, il **tecnico di laboratorio** e i **quattro carrelli di
  portatili**. La sonda dei builder arriva a **27 su 27**: il registro intero,
  cioè il criterio di accettazione della spec (§6), raggiunto all'ondata 5
  invece che alla 7. Due fasi ancora `OPTIMAL` a zero scarti — **15 233
  variabili, 12 251 constraint**, **73 aule su 73**, ~7 s. Dettaglio in
  [`data/liceo-alighieri/risorse.md`](../data/liceo-alighieri/risorse.md).

  ⚠ **Le variabili scendono, ed è la prima volta.** L'indisponibilità è un
  **pre-filtro del dominio**, non un constraint: 55 righe tolgono celle, e con
  esse i letterali di avvio che ci vivevano (15 545 → 15 233). I constraint
  salgono comunque, per i tetti di peso. È una differenza di meccanismo che i
  test asseriscono per nome — un pin dentro una cella indisponibile finisce
  **fuori dominio** (`pin_fuori_dominio`), mentre un pin che sfora un tetto di
  peso no.

  🔑 **Il contratto dell'ondata è misto, per la prima volta, e quale prova
  valga lo decide la natura della riga.** Le indisponibilità e i tetti per
  giornata e mezza giornata *formano* l'orario: vietano configurazioni, quindi
  si provano col **testimone puntato** dell'ondata 4. Lo spezzone di RICCI —
  tre ore in tre fasce — è un conteggio, quindi ammette la **tacca**
  dell'ondata 3. E il tetto **settimanale** non ammette né l'uno né l'altra:
  la somma dei pesi di un'unità-studente lungo la settimana non dipende da dove
  le attività vanno, quindi nessun pin la può violare — è *il tetto
  inevadibile* che `CLAUDE.md` porta fra i punti aperti, e resta la sola tacca
  (40 regge, 39 è `INFEASIBLE`). Vale la pena averlo scritto: è la differenza
  fra un vincolo che **forma** l'orario e uno che si limita ad ammetterlo o
  rifiutarlo.

  🔑 **E i tre livelli di indisponibilità non fanno la stessa cosa, il che è
  tre affermazioni e non una.** La rossa vieta (testimone puntato, su una
  **classe** e su un'**aula**: è ciò che significa «generico sulla risorsa»).
  La gialla vieta finché non la si autorizza — e l'autorizzazione è **per tipo
  di risorsa**, mai per la singola riga (A4): misurato nei due versi, con una
  gialla su un docente e una su un'aula, autorizzando l'una categoria e
  vedendo l'altra restare `INFEASIBLE`. La verde non vieta affatto
  (contro-testimone: si impone la cella preferita libera e si pretende
  `OPTIMAL`; se un giorno restringesse quel test diventerebbe rosso, ed è il
  verso giusto — sarebbe il solver a farsi più severo di EDT).

  ⚠ **Un'attesa smentita, e stavolta la sbagliata era il dataset.** Il disegno
  dava **tre** carrelli, così che i due livelli d'inglese (due l'uno) non
  potessero stare nella stessa fascia: il testimone sarebbe stato pulito e il
  dataset rotto, perché stare nella stessa fascia è *il senso* di un
  raggruppamento trasversale — gli stessi alunni si dividono per livello nella
  stessa ora. Lo ha detto per primo un test dell'ondata 2, diventando rosso.
  Correzione: **quattro** carrelli, e il carrello anche sulle quattro ore di
  laboratorio a mezza classe; il testimone diventa a tre attività,
  `2 + 2 + 2 > 4`. 🔑 La regola generale, che vale per le ondate 6 e 7:
  **un'ondata che rompe una forma dell'ondata precedente per accendere un
  builder sta misurando sé stessa.**

  ⚠ **E una misura che ha cambiato due test delle ondate precedenti.** I tetti
  di peso per giornata e mezza giornata sono ~510 constraint da migliaia di
  letterali l'uno, e sono il primo vincolo del banco a cambiare il **regime di
  ricerca**: stesso modello, **439 s** con un lavoratore contro **7 s** con
  otto (senza i tetti: 7 s in entrambi i casi). I due test che cercavano con
  `workers=1` per riproducibilità sono passati a `workers=8` — le loro
  asserzioni sono invarianti e non celle, quindi non dipendono da quale ottimo
  torni.

  🔑 **Due difetti nuovi, e nessuno dei due riparato** (spec §8: il banco non
  modifica il motore; si dichiarano e si fissano con un test che asserisce il
  comportamento corrente).

  **L6 — una risorsa senza sede non può servire due sedi, e non è la
  capienza.** Quattro carrelli sono della scuola, non di un edificio: servono
  l'inglese alla centrale e l'informatica in succursale. Ma
  `SiteTransitionBuilder` posta la clausola «due sedi sulla stessa fascia» su
  **ogni** chiave di occupazione, e pretende in più `site_transition_slots`
  fasce libere fra due sedi diverse — cioè un tempo di viaggio da una risorsa
  che non viaggia. La dimostrazione che il colpevole è la sede sta in tre
  esecuzioni: `INFEASIBLE` a capienza 4 con domanda 3; `INFEASIBLE` ancora a
  capienza **9**, quindi non è capienza; `OPTIMAL` a zero scarti appena le due
  attività dichiarano la **stessa** sede.
  🔑 E lo stesso carrello è **l'unica risorsa del progetto che possa mostrare
  [ADR-019](decisioni.md)** — *dentro una fascia non si viaggia*: a capienza 1
  la regola coincide riga per riga con la vecchia, quindi serviva una chiave a
  capienza cumulativa toccata da due sedi, che nessun dataset aveva. Misurata
  su un orario scritto a mano, perché il solver quella configurazione la
  vieta: `MaxSiteChangesChecker` conta **zero cambi**, e
  `SiteTransitionChecker` nomina comunque l'impossibilità. Due domande diverse,
  due risposte diverse — che è esattamente ciò che l'ADR decide.

  Suite: **910 verdi**, 17 skip, **545 s** (era 891 / 345 s — i diciannove
  test nuovi sono quasi tutti due solve dell'Alighieri l'uno, che è il prezzo
  del testimone puntato).

  🔑 **E il ramo di controllo dell'ondata 4 ha fatto il suo mestiere.** La riga
  `palestra` (rossa il lunedì mattina) ha reso indisponibile la cella su cui il
  testimone puntato di `forbidden_sequence` metteva le due ore di scienze
  motorie della 4A. Da quel momento il primo `assert` di quel testimone restava
  verde **per il motivo sbagliato** — `INFEASIBLE` per il pre-filtro invece che
  per la riga osservata — e il secondo, il ramo «senza la riga», è diventato
  rosso. È il caso per cui la spec ha reso obbligatorio quel ramo: senza, un
  testimone si sarebbe svuotato in silenzio. Il pin si è spostato al martedì.

  **L6bis — il giallo su un'aula a più candidate costa una rinuncia.** Trovato
  *scegliendo dove* mettere l'indisponibilità gialla di un'aula. Lo stesso
  giallo ha **tre** letture nel codice: il checker lo classifica
  `Severity.OPTIONAL`, il pre-filtro di `structural:unavailability` lo rispetta
  come una rossa, e `structural:room_pool` lo ignora contando i posti
  dell'aula come se fosse libera. Due su tre sono d'accordo; la terza paga. Su
  un'aula a **candidata unica** non si vede — il pre-filtro toglie la cella
  prima; su un'aula a più candidate la fase 1 piazza e la fase 2 **rinuncia**,
  cioè esattamente ciò che [ADR-021](decisioni.md) esiste per non far
  succedere. ⚠ È il motivo per cui la gialla del dataset sta su `LAB-SUCC` e
  non su `LAB-INF`: **un banco che porta un difetto noto smette di misurare le
  regressioni** — la rinuncia comparirebbe e sparirebbe a seconda di quale
  ottimo la fase 1 restituisce, e nessuno saprebbe più leggere il numero.

- **2026-08-30 (notte) — L'Alighieri, ondata 4: l'asse Relazione, e la rimozione che torna misurabile se la si punta** —
  I **tredici tipi** di `SubjectConstraint` in tredici righe, e la sonda dei
  builder passa da **12 a 25 su 27**. Due fasi ancora `OPTIMAL` a zero scarti —
  **15 545 variabili, 11 783 constraint** (ondata 3: 15 372 / 8 758), **73 aule
  su 73**. Dettaglio riga per riga in
  [`data/liceo-alighieri/relazioni.md`](../data/liceo-alighieri/relazioni.md).
  I due builder che restano sono nominati e non dimenticati:
  `structural:unavailability` — il banco non ha ancora una riga di
  indisponibilità — e `structural:didactic_weight`, i cui quattro tetti sono
  `None` com'è fedele a EDT. Sono l'ondata 5.

  🔑 **La tacca dell'ondata 3 non si applica qui, e la ragione è che una
  proibizione non sparpaglia.** Un tetto su una risorsa dal carico fisso si
  rompe stringendolo di un'unità; un divieto di relazione no. Il disegno
  prevedeva una quarta tacca — spostare `two_days_incompatible` dal greco del
  3B (3 ore) al latino (4 ore), perché quattro giornate a due a due non
  adiacenti non stanno in cinque — e l'aritmetica era giusta. **La premessa
  no**: niente obbliga quattro ore della stessa materia a stare su quattro
  giornate distinte. Misurato: `OPTIMAL`. È la stessa trappola che rende
  `same_day_incompatible` fra due materie sempre soddisfacibile da solo, e nel
  solve libero si vede — le tre ore di greco del 3B finiscono **tutte lo
  stesso venerdì**, legalmente. Un test asserisce quell'`OPTIMAL` perché
  diventi rosso all'ondata 7.

  🔑 **Al suo posto il testimone puntato — ed è la regola 4 che torna
  misurabile, un'ondata dopo essere stata dichiarata inutilizzabile.** L'ondata
  3 aveva scartato *«togli la riga e l'orario deve cambiare»* perché senza
  funzione di costo sopra lo scarto ogni orario a zero scarti è ottimo, e ciò
  che torna dice quale ottimo ha trovato la ricerca. Vero **finché il solver è
  libero**: imponendo con `pinned` la configurazione che la riga vieta, le due
  esecuzioni non rispondono più «quale orario» ma `INFEASIBLE` con la riga e
  `OPTIMAL` a zero scarti senza. Due proprietà del **modello**, in due
  direzioni, nessuna dipendente dal testimone. **13 su 13**, in entrambe le
  direzioni. Il secondo ramo non è un lusso: senza, un pin illegale per
  un'altra ragione qualunque direbbe `INFEASIBLE` e non proverebbe niente.

  🔑 **E una delle tre tacche superstiti attraversa i due assi.** Dove il tipo
  ha un parametro la tacca resta il modo più economico di dirlo, e sono tre su
  tredici: il tetto di 60′ per mezza giornata sulla matematica di 2A (il blocco
  da due ore non si spezza), lo scarto minimo a 3 mezze giornate sul latino di
  1B (cinque ore vogliono un arco di dodici, la settimana ne ha dieci), e —
  quella che conta — il tetto di 60′ al giorno sull'italiano del 3B, che
  diventa impossibile perché **GENTI lavora tre giornate** per una riga
  `max_presence` scritta all'ondata 3, su una risorsa e non su una materia. È
  l'argomento di §1.1 della spec — *una scuola combina i vincoli come li
  combina una scuola* — misurato invece che dichiarato.

  ⚠ **Il dataset è cresciuto, ed è la mossa del cappellano.** I quattro tipi
  `PARTS_*` vogliono quattro portatori che **non si implichino**: un ordine per
  giornata su un'unità rende veri per costruzione gli omogenei su ogni
  sotto-unità e dentro ogni mezza giornata, quindi con la sola 3A sdoppiata due
  dei quattro sarebbero stati *presenti e implicati* — il difetto che la regola
  4 esiste per non avere. Da qui un secondo laboratorio a mezza classe in
  **4A**: +1 partizione, +2 parti, +2 attività, N01 da 18 a 19 ore, quadratura
  `+/- = 0` intatta su tutte e ventitré le cattedre. E la forma che ne esce è
  quella che una scuola scriverebbe: in 3A le due metà **ruotano attorno
  all'ora di teoria**, in 4A vale solo la regola debole.

  ⚠ **Una riga del dataset che nessuna riga di vincolo può avere**: nessun tipo
  sta su un **raggruppamento**, e non è una svista. I due raggruppamenti di
  inglese portano una materia che a classe intera non esiste in nessuna delle
  due classi che attraversano, quindi una riga su di loro sarebbe vera per
  vacuità. Il campo `group` resta esercitato dal solo `structural:occupation`;
  le due righe su **parte** coprono l'altra forma.

- **2026-08-30 (notte) — L'Alighieri, ondata 3: l'asse Cardinalità, e la regola della mutazione che si è rotta in mano** —
  Otto famiglie di `ResourceTimeConstraint` in **dieci righe**, e la sonda dei
  builder passa da **4 a 12 su 27**: il salto più grande che una singola ondata
  possa fare, perché è l'unico asse in cui una riga per famiglia sveglia un
  builder per famiglia. Due fasi ancora `OPTIMAL` a zero scarti — **15 372
  variabili, 8 758 constraint** contro 14 372 / 7 704 senza le righe, 71 aule
  su 71. Dettaglio riga per riga in
  [`data/liceo-alighieri/vincoli.md`](../data/liceo-alighieri/vincoli.md).

  🔑 **Ogni riga è scelta al bordo, e questo è il contenuto del pezzo.** Il
  pericolo di un banco non è dimenticare una famiglia — quello lo prende la
  sonda in un secondo — è metterci una riga così larga che l'orario la
  soddisfa da solo. Perciò per otto righe su nove **una tacca più stretta
  rende il dataset `INFEASIBLE`**, e ogni tacca è un argomento di conteggio,
  non una taratura trovata provando: `min_days 5` da tre ore per un docente da
  dieci; `day_minutes 240` per uno da ventuno; dodici ore in una giornata da
  otto fasce; venti ore in tre fasce al giorno; ventotto fasce in cinque mezze
  giornate da cinque.

  ⚠ **La regola 4 della spec è stata implementata, misurata e sostituita.**
  Diceva: *togliere la riga di una famiglia deve cambiare l'orario*. Non è
  misurabile. Il modello di fase 1 non ha una funzione di costo sopra lo
  scarto, quindi **ogni orario a zero scarti è ottimo** e il solver ne
  restituisce uno arbitrario fra milioni: se quello che torna dopo la rimozione
  viola la riga tolta, è un fatto sulla *ricerca*, non sulla riga. La misura è
  netta — cambiando una sola riga **estranea** alla famiglia osservata il
  verdetto si è ribaltato per **tre famiglie su nove**, e a otto lavoratori la
  stessa identica configurazione dava «viola» e «non viola» a esecuzioni
  diverse. Congelarlo in un test avrebbe fissato un artefatto della ricerca,
  che è l'errore che il tie-break di `_placed_of` ha già insegnato a non fare.
  Al suo posto lo **stringimento**, che dimostra la stessa cosa in modo più
  forte: `INFEASIBLE` è una proprietà del modello, e una riga che non sopporta
  una tacca in più non può essere soddisfatta per caso.

  🔑 **Il cappellano, cioè come si dà un soggetto a `max_site_changes`.**
  Misurato: `per_day 0, per_week 0` su R01 — che insegna religione in tutte e
  dodici le classi, quindi in entrambe le sedi — era `OPTIMAL`. Con cinque
  giornate a disposizione può dedicarne una intera alla succursale e non
  spostarsi mai: il vincolo c'era e non vincolava niente. La riga che gli dà un
  soggetto è `max_presence days 2` — l'insegnante di religione che viene due
  giorni — e con due sole giornate le dieci ore della centrale non stanno in
  una: il cambio diventa **inevitabile**, e limitarlo a uno diventa una scelta.
  È il caso vero delle scuole con una sede staccata, e va scritto perché la
  strada facile era lasciare la riga larga e dichiarare la famiglia coperta.

  ⚠ **Il D.T.B. non arriva al bordo, ed è dichiarato invece che aggiustato.**
  Non solo `max_gap_minutes = 0` su L03 resta risolvibile: lo resta **zero
  buchi per ogni docente e per ogni classe insieme**. La ragione si conta — 40
  fasce a settimana contro cattedre da 10–21 ore e classi da 28–32 fasce: la
  contiguità dentro una mezza giornata è gratis. Stringerla vuole una griglia
  più densa, cioè il criterio di accettazione dell'ondata 7, non una taratura
  di questa riga. Un test asserisce l'`OPTIMAL`, così diventerà rosso il giorno
  in cui il banco si stringe — che è quando vogliamo saperlo.

  ⚠ **E un fatto reso visibile, non introdotto**: a orario vuoto l'Alighieri
  non produce più solo `activity_unplaced`. Due delle otto famiglie sono
  *deficienze* — `min_distribution` e `free_guaranteed`, i due checker
  `PLACEMENT_MONOTONE = False` fra le righe del dataset — e valgono zero quando
  non c'è niente di piazzato: per loro **piazzare ripara**. Tre test dell'ondata
  2 lo hanno scoperto rompendosi, e la riparazione non è stata allentare
  l'asserzione ma prendere la **linea di partenza** prima di piazzare e
  confrontarsi con quella, sulla chiave grossolana `(causale, risorsa)` — la
  stessa scelta dell'oracolo differenziale di ADR-018.

- **2026-08-30 (notte) — L'Alighieri, ondata 2: gli sdoppiamenti, e il primo difetto che il banco produce** —
  La voce ✅ di scope v1 ([ADR-013](decisioni.md)) che **nessun dataset
  rappresentava**: `ClassPartition`, `ClassPart` e `Group` erano tre tabelle
  vuote, provate solo da fixture sintetiche da poche righe. Ora stanno dentro
  una scuola intera, **insieme**, e in quattro forme deliberatamente diverse —
  quattro righe della stessa forma proverebbero una cosa sola.

  **16 partizioni, 32 parti, 2 raggruppamenti.** IRC/alternativa su tutte e
  dodici le classi (due parti della stessa classe, con `election_group` a
  dichiarare l'alternativa, ADR-020); la **2C articolata** con una parte su un
  piano proprio, `SAP2` Scienze Applicate — la condizione 3 di ADR-015, provata
  finora solo su fixture; uno **sdoppiamento a effettivo ridotto** in 3A; il
  **raggruppamento trasversale** dei livelli di inglese su 1A e 1B, che è il
  caso che *rompe la decomposizione per classe*.

  🔑 **E ha reso visibile una distinzione che il Fermi non poteva fare
  vedere: 345 ore-alunno contro 361 erogate.** Lo scarto è tutto negli
  sdoppiamenti — dodici ore di alternativa, tre di informatica, e l'ora di
  laboratorio di 3A insegnata **due volte**, che è il costo dello sdoppiamento e
  il motivo per cui `Mh/s` di N01 vale 18 mentre il curriculum ne dice 17.
  Confonderli è il modo in cui un monte ore torna e una cattedra no. Con essi il
  piano diventa quello che ADR-020 dice che è: un **catalogo** che somma 28 dove
  l'alunno fa 27.

  ⚠ **La sonda non si è mossa, e va detto perché.** Restano 4 builder su 27:
  partizioni, parti e raggruppamenti **non hanno un builder proprio**, entrano
  dalle chiavi di occupazione (ADR-017 — `structural:occupation` da 1440 a
  **3440** constraint) e da `structural:coverage`, che per costruzione un
  builder non ce l'ha. Un cricchetto che contasse i constraint avrebbe detto
  «cresciuto» senza dire niente di vero, ed è la ragione per cui l'asserzione è
  un **insieme**.

  🔑 **Il difetto trovato — L5, e il banco ha fatto il suo mestiere al secondo
  colpo.** 📦 Lo XSD dichiara che *l'allineamento genera l'attività complessa*:
  in EDT le attività allineate sono **una** collocazione. Da noi
  `Activity.alignment_ident` esiste dal giorno dello schema e **nessun builder e
  nessun checker lo legge**. Misurato: dei **15** allineamenti dichiarati dal
  dataset, **13 escono dal solve senza una sola coincidenza** — i due livelli di
  inglese sparsi su sei celle, il latino e l'informatica della 2C mai in
  parallelo. Nessun finding, nessun vincolo violato: l'orario è impeccabile per
  i nostri predicati e **sbagliato per una scuola**, perché metà classe resta a
  scuola in un'ora in cui non ha lezione.
  ⚠ Non riparato qui — la spec §8 dice *nessuna modifica al motore*, e un
  dataset che si aggiusta per far passare un test non prova più niente. Il
  comportamento sbagliato è **fissato da un test** che diventerà rosso quando il
  debito si chiude.

  ⚠ E una seconda cosa che il modello non ha, scritta prima che sorprenda
  qualcuno: `TeachingAssignment` ha una FK alla **classe**, quindi le ore di E01
  sul livello base sono registrate su 1A mentre insegna ad alunni di 1A e 1B. Il
  monte ore quadra e l'orario è corretto; è la riga di bilancio a mentire.

  Misure: **340 attività / 361 ore**, modello a 14 370 variabili e 7 700
  constraint, fase 1 `OPTIMAL` a zero scarti in ~3,6 s, fase 2 **71 su 71**
  senza rinunce, `check_schedule` su orario vuoto con solo `activity_unplaced` —
  cioè copertura, alternativa e piano dell'articolata tutti puliti al primo
  giro.

- **2026-08-30 (notte) — L'Alighieri, ondata 1: l'anagrafica, e la sonda che diventa un cricchetto** —
  Il primo dei sette pezzi della spec approvata. `data/liceo-alighieri/` (sette
  file di markdown) e `tests/alighieri.py`: **12 classi** su due indirizzi
  (A scientifico, B classico, C biennio scientifico in succursale) e **due sedi**,
  **21 cattedre** tutte a `+/- = 0`, **345 ore-classe**, **323 attività**,
  griglia **5 × 8** con la pausa mensa fra la quinta e la sesta fascia.

  🔑 **Le otto fasce e le due sedi non sono dimensionamento, sono le due cose
  che il Fermi non può misurare.** `max_hours` con tetto mattutino diverso da
  quello giornaliero, `max_half_days` e le mezze giornate libere non hanno
  soggetto su una griglia senza pomeriggio; e `structural:site_transition`
  legge `Activity.site`, di cui il Fermi ha **zero** righe. Con l'ondata 1 quel
  builder posta **1330** constraint, e `structural:grid` toglie **110** celle —
  i 22 blocchi lunghi che non attraversano la mensa.

  **La sonda è diventata un test** (`tests/sonda.py`,
  `tests/test_alighieri_sonda.py`), ed è la parte che conta più dei dati:
  l'asserzione è l'**insieme** dei builder attivi, non un numero, perché
  `>= n` lascerebbe passare l'ondata che aggiunge una tabella senza svegliare
  il builder che dovrebbe leggerla. Oggi **4 su 27** — occupation, room_pool,
  site_transition, grid — contro i **3** del Fermi, che un secondo test fissa
  accanto perché quella riga di `CLAUDE.md` non torni a essere un elenco.
  ⚠ E scrivendola si è ripreso l'inciampo della prima stesura: `all_builders()`
  importa i builder **pigramente**, quindi leggere `BUILDERS` prima di
  chiamarlo dà un registro vuoto — il primo test a girare falliva e il secondo
  passava. È il motivo per cui la sonda è un modulo con un import esplicito e
  non uno script.

  Misure: modello di fase 1 a **13 583 variabili e 5 493 constraint**, fase 1
  `OPTIMAL` con **zero scarti** in ~2,5 s, fase 2 **66 richieste su 66** senza
  rinunce in ~0,2 s, `analyze_capacity` pulita.

  ⚠ **Ciò che l'ondata 1 dichiara di non avere.** Il criterio di §4 — *stretto
  ma risolvibile*, cioè `OPTIMAL` a zero scarti ma con gli scarti che compaiono
  togliendo una sola aula o un solo docente — **non è verificato, e non lo
  sarà** finché non ci sono righe di vincolo: senza, la tensione non c'è, e
  affermarla sarebbe il primo modo di aggiustare il banco. Sta scritto in
  `esiti-attesi.md` come atteso dell'ondata 7, non come esito di questa.

  ⚠ E `structural:unavailability` — l'unico dei tre builder attivi del Fermi
  che l'Alighieri **non** esercita — resta inerte: le indisponibilità sono
  righe di vincolo, e arrivano con l'asse Cardinalità.

- **2026-08-30 (tarda sera) — La spec dell'Alighieri: il Fermi misura il dataset, non il modello** —
  Conseguenza diretta della prova del prodotto qui sopra, e con due misure che
  hanno smentito quello che il progetto credeva di sé.

  🔑 **La prima: tre builder su ventisette, non sei famiglie.** `CLAUDE.md`
  elencava le famiglie esercitate dal Fermi — *«griglia, indisponibilità,
  occupazione, sedi, D.T.B. e `room_pool`»* — ma era un elenco, non una misura.
  Avvolgendo `restrict` e `build` di ogni builder durante `build_model`:
  `structural:occupation` posta **948** constraint, `structural:room_pool`
  **420**, `structural:unavailability` toglie **360** celle, e **gli altri
  ventiquattro non fanno assolutamente nulla**. Tre dei sei elencati non
  reggono la verifica: `site_transition` non ha `Site` da leggere,
  `max_gap_hours` legge righe `ResourceTimeConstraint` che non esistono, e
  `structural:grid` è un no-op perché il Fermi non ha né festività né
  intervalli e ogni durata sta nella giornata. La riga in `CLAUDE.md` è stata
  corretta.

  ⚠ Ed è la misura che diventa il **criterio di accettazione** dell'Alighieri,
  scritta come test e non eseguita una volta a mano: zero builder inerti. Senza
  quel test, il primo builder aggiunto dopo tornerebbe silenziosamente inerte —
  che è esattamente com'è nata questa situazione.

  **La seconda: tredici tabelle su trentatré sono vuote.** Non solo
  `ResourceTimeConstraint` e `SubjectConstraint` — che era già scritto — ma
  anche `ClassPartition`, `ClassPart` e `Group`.

  ⚠ **Quelle tre sono voci ✅ dello scope v1.** Sdoppiamenti e raggruppamenti
  trasversali sono decisi *dentro* v1 da ADR-013, hanno i loro test su fixture
  sintetiche, e **nessun dataset li rappresenta**. È il buco più grave
  dell'elenco, perché non è una famiglia rara: è una forma che quasi ogni liceo
  italiano ha.

  🔑 **La decisione della spec è che l'Alighieri sta accanto al Fermi, non al
  suo posto.** Il Fermi è la trascrizione di una scuola realmente inserita in
  EDT, e il suo docstring dichiara che *«la trascrizione è essa stessa il
  test»*. Quel test funziona **solo perché nessuno ha progettato il Fermi per
  superarlo**: arricchirlo finché esercita ventisette builder distruggerebbe la
  proprietà che lo rende utile. Da quel momento «lo schema rappresenta il
  Fermi» non direbbe più niente sul mondo.

  E l'Alighieri è di natura diversa — righe costruite per far scattare un
  checker, non osservate — quindi il suo README apre dichiarandolo un **banco**.
  La convenzione «ciò che è nostra estensione va segnalato come tale» vale
  anche per i dataset.

  ⚠ **La regola che lo tiene onesto è la verifica per mutazione**, ed è il vero
  contratto della spec: togliere la riga di una famiglia **deve** cambiare
  l'orario. Senza, «l'Alighieri copre tutte le famiglie» significa soltanto
  «l'Alighieri ha righe in tutte le tabelle» — ed è il modo in cui un dataset
  completo può essere vuoto. Il rischio gemello è dichiarato: un dataset lo si
  aggiusta finché è verde, e a quel punto non prova più niente; per questo gli
  esiti attesi si scrivono **prima** della prima esecuzione.

  Cosa aggiunge rispetto a `test_modello_completo`, che le famiglie le accende
  già tutte insieme: la **scala** (il difetto del budget è comparso solo a 284
  attività, e nessun test lo vedeva), la **coerenza** (il banco combina per
  seme, una scuola combina come una scuola), e **i comandi** — sul Fermi la
  classifica di blame ordina tre indisponibilità e nient'altro: non è una
  classifica, è un elenco.

  Ordine rispetto a D2, dichiarato: prima l'Alighieri. D2 porterà una seconda
  scuola *vera*, che varrà di più, ma dipende da dati che non abbiamo — e
  l'Alighieri riduce il rischio di D2, invece di scoprire insieme che i dati
  sono difficili e che il motore non li regge.

  Sette ondate, con gli sdoppiamenti in seconda posizione — prima dei vincoli,
  perché le quattro famiglie `parts_*` senza partizioni non hanno soggetto.

- **2026-08-30 (tarda sera) — Il budget appartiene alla posizione: `solve --popolazione` non tornava** —
  Trovato non da un test ma **provando il prodotto**: database vuoto, `migrate`,
  il Fermi caricato, e poi tutti i comandi uno per uno dalla riga di comando.
  La catena breve regge benissimo — `solve` `OPTIMAL` 284/284 in 1,2 s,
  `assign_rooms` 92 su 92 in 0,2 s, `analyze` dopo di loro con **zero
  finding**, `export_ical` 9405 eventi in 0,7 s, `place_and_fix` due attività
  ricollocate in 8,2 s. Poi il caso che il Fermi non prova mai da solo.

  ⚠ **Il Fermi non ha righe `QualityCriterion`**, quindi dalla riga di comando
  la qualità non era mai stata esercitata: il prodotto consegnava un orario
  *legale*, mai *ottimizzato*. Seminandone cinque, `solve` regge (4,2 s), ma
  `solve --popolazione teachers --tolleranza 50` **non torna**: ucciso dopo
  dodici minuti. Con `--limite 15` chiude in 52 s.

  🔑 **La causa è che `BUDGET_QUALITA` era stato appeso alla famiglia invece
  che alla posizione.** La diagnosi che l'aveva prodotto era precisa — un
  livello è lento non perché difficile da ottimizzare ma perché *impossibile
  da dimostrare* — e la stabilità sembrava esente perché in testa arriva a
  zero, che è anche il suo limite inferiore banale. Ma con l'arbitrato la
  stabilità **scivola in coda**, e lì il suo ottimo non è più zero: i criteri
  sopra di lei hanno già spostato l'orario. Diventa indimostrabile esattamente
  come loro, e `Level("spostamenti", spostate)` la costruiva con
  `limite=None`, cioè `1e9` secondi. È lo stesso difetto di allora, ricomparso
  **al posto lasciato libero**: la coda era la qualità, ora è la stabilità.

  La prova non è un argomento ma il numero che il comando stampa da sé:
  `spostamenti 219 (ottimo non dimostrato, non sotto 8)`. Un livello che a 15 s
  dichiara un divario di 211 non stava chiudendo.

  Corretto in `livelli()`: sotto arbitrato la stabilità entra in coda con
  `replace(stabilita, limite=BUDGET_QUALITA)`. Il comando ora torna in **49 s**,
  e la qualità finalmente lavora — `gaps_teachers` da 1260 a **0**,
  `isolated_all` da 50 a **5**, `free_half_days_teachers` da 132 a 108, al
  prezzo di 169 spostamenti su 284.

  ⚠ **Un test è stato rinominato perché il suo nome era diventato falso**:
  `test_solo_i_livelli_di_qualita_hanno_un_budget` →
  `test_chi_dimostra_l_ottimo_non_ha_budget`. Non è cosmesi — il nome vecchio
  affermava proprio la generalizzazione sbagliata, e sarebbe stato l'argomento
  con cui rifiutare questa correzione.

  ⚠ **Sedici skip su diciassette non sono un debito**: vengono tutti da
  `solver_harness.py:384` e dicono la stessa cosa, «derivazione vacua per il
  seed N». Nove famiglie, mai la stessa su tutti e cinque i seed: nessuna
  famiglia è saltata per intero, ogni skip è un seed che non produce il caso.

- **2026-08-30 (sera) — L1, L2, L3: la sezione `Lavoro` nasce e si chiude lo stesso giorno** —
  Tre voci che non aspettavano nessuno, prese in ordine di valore.

  **L1 — il perimetro del buco è un parametro.** Era un debito con la misura
  già scritta: per EDT il buco si conta sulla **giornata**, e una casella `Non
  conteggiare come buchi le ore libere prima o dopo la linea di fine mattinata`
  — separata per classi e per docenti — ne toglie la pausa. Noi misuravamo
  sempre dentro la mezza giornata, cioè come se fosse spuntata per tutti.

  🔑 **Le due formulazioni sono la stessa cosa, e non era un'assunzione.** Sulla
  giornata il buco è `ultima − prima + 1 − conteggio`; spezzarlo alla linea
  toglie esattamente le fasce libere fra l'ultima occupata del mattino e la
  prima del pomeriggio — cioè, alla lettera, «le ore libere prima o dopo la
  linea». La misura sta in `test_la_differenza_e_esattamente_la_corsa_libera_attorno_alla_linea`:
  occupate 0, 2 e 5 con la linea fra 3 e 4 danno 60′ sulla mezza giornata e 180′
  sulla giornata, e i 120′ di differenza **sono** le fasce 3 e 4. Senza questa
  identità il parametro sarebbe stato un'approssimazione della casella di EDT;
  con essa è la casella.

  I posti che leggono il parametro sono **tre**, non due come diceva il debito:
  `MaxGapChecker`, il builder del D.T.B. — dove il clamp di ADR-018 va calcolato
  sullo stesso perimetro, o il tetto concederebbe un debito che non esiste — e
  il criterio di qualità `gaps`. ⚠ I primi due e il terzo **devono** leggere lo
  stesso campo: sono la stessa quantità, uno col tetto e uno senza, e nello
  stesso rendiconto.

  ⚠ **Il default resta lo status quo** (mezza giornata per entrambe le
  popolazioni), e non è il default di EDT — la sua base di esempio ha la casella
  spuntata per i docenti e **non** per le classi. Deliberato: la scelta cambia
  la quantità di un vincolo **hard**, quindi è della scuola e non nostra. Il
  Fermi misura identico a prima, ed è la prova che il parametro non ha cambiato
  niente a chi non lo tocca.

  **L2 — le due voci che O1 aveva lasciato sulla fase 2.** La prima: `Minimizza
  il superamento della capienza` è il terzo dei quattro default
  dell'ottimizzatore aule, quindi la capienza in alunni **non è un vincolo ma
  non è nemmeno inerte** — e `Room.capacity` esisteva dal primo giorno letto da
  nessuno. Ora è il **terzo livello** della catena della fase 2, dopo i minuti
  senza aula e i cambi, come in EDT sta dopo il cammino e l'aula preferenziale:
  stare stretti costa meno che restare senza aula, e il test lo tiene fermo.

  🔑 **L'eccedenza è una costante, non una variabile.** Effettivo e capienza
  sono due numeri anagrafici, quindi il livello è una somma di costanti per
  letterale — nessuna variabile in più per coppia. E il livello **non si posta**
  quando nessuna coppia può sforare: senza effettivi o senza capienze
  misurerebbe la costante zero, e un livello della catena è un giro di solver.

  ⚠ Ha richiesto un dato che non avevamo: `expected_students` su classe e
  parte, che è `N.Alu` di EDT — il numero di alunni **previsto**, quello con cui
  la catena previsionale lavora anche senza anagrafica nominativa. `NULL` è «non
  lo so», mai zero, e **basta un'unità senza il numero perché il totale sia
  ignoto**: sommare le sole dichiarate darebbe un numero più piccolo del vero, e
  un'eccedenza sparirebbe in silenzio.

  La seconda: il **lucchetto sulla singola assegnazione d'aula**
  (`Placement.room_locked`), che in EDT è la casella per riga di `Blocco delle
  aule nelle attività coinvolte`. Da noi il blocco dell'aula era un effetto
  collaterale dell'immobilità della **collocazione**, che è un'altra cosa: ora
  sono due lucchetti e si separano nei due versi — un'attività mobile può avere
  l'aula bloccata, e una bloccata in griglia può cambiare aula.

  **L3 — il materiale per decidere O5**, in
  [criteri-di-piazzamento.md](criteri-di-piazzamento.md): i dieci criteri di
  piazzamento non tradotti, uno per uno, con cosa fanno in EDT, cosa già abbiamo
  che li tocca, il costo e la raccomandazione. Esito **sette no e tre forse**, e
  la ragione dei no è una sola: i due meccanismi sono diversi. `Ordinamento dei
  criteri` governa un'**euristica di ricerca** — quale cella provare — che in
  CP-SAT non esiste, perché la ricerca la governa il solver; ciò che possiamo
  dichiarare è un obiettivo, cioè l'altro riquadro. Le voci utili di quella
  lista erano già state prese, da quello giusto.

  ⚠ **E una prima stesura diceva una cosa più forte del vero.** Aveva marcato il
  criterio 8 (`Evita le attività della stessa materia nella stessa ora`) come
  «da verificare prima», sospettando che il nostro `regularity` premiasse per i
  docenti ciò che EDT evita. Verificato: `QualityCriterion.population` fa già
  esattamente quel filtro, la riga di regolarità si dichiara `CLASSES` come in
  EDT, e non c'è nessun difetto — c'è un'**assenza**, che per i docenti non
  abbiamo niente che spinga *via* dalla stessa ora. Corretto da ⚠ a 🟡 prima di
  scriverlo, che è il motivo per cui una raccomandazione va verificata contro il
  codice e non contro il ricordo del codice.

  🔑 **E L3 ha trovato un debito che nessuno cercava**, dal criterio 5 (`Riduci
  i buchi quindicinali`): i nostri **criteri di qualità ignorano le firme di
  settimana**. Contano su una settimana sola, mentre i vincoli le distinguono
  già — `MaxGapBuilder` posta un budget per firma. Su una scuola con attività
  quindicinali il numero che il rendiconto stampa non è quello di nessuna
  settimana reale. Che EDT abbia un criterio apposta vuol dire che il fenomeno
  lo conosce. Aperto come debito: nessuna delle due basi lo esercita.

  Suite: 833 test verdi, 17 skip. Il Fermi non cambia di un numero — i due default di
  L1 sono lo status quo, e L2 non ha né effettivi né capienze da leggere.

- **2026-08-30 (notte) — O1 chiusa: il criterio dominante è quanto camminano le persone** —
  Lanciata la ripartizione su `PALESTRE` e aperto l'ottimizzatore. I quattro
  criteri che il produttore ci trova dentro:

  | | Default | Enum |
  |---|---|---|
  | 1. | `Limita gli spostamenti tra attività consecutive` | `tcosChangements` |
  | 2. | `Favorisci l'utilizzo delle aule preferenziali` | `tcosSallePref` |
  | 3. | `Minimizza il superamento della capienza` | `tcosCapacite` |
  | 4. | `Nessuno` | `tcosAucun` |

  Il quinto (`tcosChangementsConfort`, gli spostamenti fra attività **non**
  consecutive) resta fuori, coerentemente con l'avvertenza che è lento.

  🔑 **Il criterio dominante non è «quale aula è più adatta»: è «quanto
  camminano le persone».** Il cammino primo, l'aula preferenziale seconda, la
  capienza terza. Quarta conferma indipendente che `tcosChangements` è una
  distanza fisica e non una differenza fra due ripartizioni — il che lascia in
  piedi la conclusione del 2026-08-29: il secondo livello della nostra fase 2
  (la stabilità) **non è nessuno dei cinque criteri di EDT**, è nostro.

  ⚠ **E la capienza torna, ma come criterio.** `Minimizza il superamento della
  capienza` dice due cose insieme: che la capienza in alunni **si può superare**
  — quindi «non è un vincolo» resta vero — e che EDT **preferisce non farlo**.
  Non era inerte come sembrava. `Room.capacity` esiste nel nostro schema,
  dichiarato descrittivo, e non è letto da nessuno.

  Altre tre cose dalla stessa finestra:

  - `Ottimizza per` è una **tendina** `Classi`/`Docenti` (nella ripartizione la
    stessa scelta è un radio), e sotto c'è la lista dei **prioritari** — 22
    classi o 4 docenti sulla demo, `0` selezionati. 🔑 **La priorità è una
    selezione, non un peso**: il nostro `Arbitrato` dichiara invece una
    tolleranza numerica di peggioramento. Il nostro è più fine, il loro sa dire
    una cosa che il nostro non sa — *queste* classi prima delle altre;
  - `Blocco delle aule nelle attività coinvolte` è la tabella delle assegnazioni
    rimescolabili (43 righe sulla demo) con un **lucchetto per riga**: è
    `immobility` applicato all'**aula** invece che alla collocazione, e non ce
    l'abbiamo;
  - le colonne della tabella si **scambiano** con la popolazione scelta —
    `Classe | Aula | …` diventa `Docente | Aula | …`.

  🔑 **E la ripartizione, misurata, giustifica la separazione in due fasi.**
  Prima: `Palestra 1` e `Palestra 2` entrambe a `0h00`. Dopo `Assegna le aule
  alle attività`: **29h00 e 19h00**, somma 48h00 = l'`Occ.` del gruppo. Cioè la
  ripartizione da sola trova *una* assegnazione valida e **non la bilancia**;
  bilanciarla è il lavoro dell'ottimizzatore. La separazione non è formale.

  Con questa, **O1 è chiusa** e resta una sola osservazione aperta in tutto il
  todo — il `Ciclo personalizzato`.

- **2026-08-30 (sera) — `Picco d'occ.` è la colonna che ADR-021 calcola** — Quattro
  schermate della vista `Orario → Aule` e della finestra `Gestione del gruppo di
  aule`, cercando i default dell'ottimizzatore (O1). L'ottimizzatore non si è
  ancora aperto, ma per strada è uscita la conferma più diretta che avessimo di
  ADR-021, e sta in una colonna che guardavamo da luglio senza capirla.

  🔑 **`LAB.MUSICA`: `Qtà = 2`, `Assegnate = 0`, `Picco d'occ. = 2`.** EDT
  conosce il picco d'occupazione di un gruppo di aule a cui non è stata assegnata
  **nessuna** aula. Quindi quel numero è calcolato **sul piazzamento** e non
  sull'assegnazione — è il `load` di `structural:room_pool`, esposto in una
  colonna dell'elenco. Il giorno prima ADR-021 si era deciso su tre indizi
  indiretti (la causale nella diagnostica del piazzamento, le cinque risorse del
  pannello, il `Qtà`); questo è il numero stesso.

  ⚠ **E costringe a rileggere `Qtà`.** `aule.md` concludeva dal 2026-07-26 che
  `Qtà` non è il conteggio dei figli, perché `PALESTRA succ` ha `Qtà = 2` e
  nessuna sotto-aula. Il fatto regge, l'interpretazione no: `Assegnate = 0` è
  scritto in **arancione**, cioè per EDT quel record è **incompleto**, non
  normale. La lettura che tiene entrambe le osservazioni è quella del titolo
  della finestra — *«2 aule massimo»*, `Assegnate al gruppo: 2/2`: `Qtà` è la
  capienza simultanea *e quindi* quante aule il gruppo dovrebbe contenere,
  `Assegnate` quante ne contiene, e la differenza è uno stato ammesso ma
  segnalato che blocca l'ottimizzatore. Per il nostro modello non cambia niente
  (`simultaneous_capacity` resta `Qtà`); cambia la frase con cui lo si spiega.

  **La finestra `Gestione del gruppo di aule`**, mai vista prima, porta altre
  quattro cose:

  - ☐ `Considera solo le attività estratte` — il **perimetro dell'estrazione
    dentro la ripartizione delle aule**, cioè il nostro `assign_rooms
    --estrazione`, che avevamo dedotto dalla regola generale e non osservato qui;
  - un radio `Limita gli spostamenti dei docenti` / `delle classi`: la
    **separazione per popolazione** esiste già nella *ripartizione*, non solo
    nell'ottimizzatore, e senza tolleranza dichiarata. E `spostamenti` è di nuovo
    il **cammino fisico**, terza conferma indipendente della correzione di
    `tcosChangements` del 2026-08-29. La nostra seconda fase non ha nessuno dei
    due criteri: voce in meno, dichiarata;
  - 🔑 **le fasi di EDT sulle aule sono due, in due riquadri distinti**:
    `Assegnazione delle aule` e `Ottimizzazione dell'assegnazione`, con
    l'ottimizzatore che rifiuta finché la prima non è finita
    (*«Ottimizzazione impossibile — solamente i gruppi di aule interamente
    assegnati possono essere ottimizzati»*). La nostra `solve_rooms` le fa
    **insieme**, in una catena a due livelli: differenza di forma, da sapere;
  - i tre pallini `Totalmente libere` / `Parzialmente libere` / `Non disponibili`
    sono gli undici `TypeIncompatibiliteSalle` (📦) collassati in tre secchi, e i
    gruppi compaiono in grassetto **e rossi** — cioè `isGroupeDansGroupe`: un
    gruppo non entra in un gruppo.

  ⚠ **La ripartizione è massiva e distruttiva**, e lo dichiara: *«Certe modifiche
  dell'orario per settimana saranno cancellate. Confermate l'assegnazione di
  tutte le attività del gruppo di aule PALESTRE?»*. Cancella cioè proprio le
  righe con maschera a una settimana che [ADR-014](decisioni.md) usa per
  sostituzioni e aggiustamenti. Il nostro `apply_rooms` scrive `assigned_room` e
  basta: qui siamo più conservativi di EDT, ed è la scelta giusta.

  ⚠ Aperta una minuzia sulla colonna **`TOP`**: su quattro righe su cinque torna
  `Occ. / (Qtà × 50h)` sulla griglia `5 × 10` della demo (1%, 26%, 35%, 48%), ma
  `LAB.ARTISTICA` fa 21h → **72%** dove la formula darebbe 42%. L'ipotesi è che
  il denominatore sia il tempo **disponibile** invece che quello totale
  (21/29 ≈ 72%), cioè che le indisponibilità escano dal conto — **[INFERENZA]**,
  si conferma con un tooltip.

- **2026-08-30 — Tre schermate del passo 3, e un pulsante che mentiva sull'unità** —
  Chiuso il primo dei due residui di O2. Il pulsante `Inserisci / cancella una
  fascia oraria` del pannello `Parametri → Istituto → Orari` era rimasto aperto
  come «operazione posizionale, differenza non osservata». La finestra lo
  spiega, e non è quello che il nome lascia credere:

  - 🔑 **l'unità non è la fascia, è la durata.** Il campo si chiama `Durata di`,
    non «numero di fasce», e la nota in corsivo dice perché: *«Qualunque sia la
    durata aggiunta o rimossa, EDT visualizzerà sempre un numero intero di
    lezioni»*. Si inserisce **tempo**; il numero di lezioni è ciò che EDT ne
    deriva. Il nome del comando mente sull'unità;
  - 🔑 **e l'operazione riallinea, dichiarandolo**: *«Le attività, gli intervalli
    e i limiti della mezza-giornata collocati dopo … verranno scalati di: …»*.
    Sì, si inserisce in mezzo; sì, i ranghi successivi slittano; e le tre cose
    che slittano sono nominate una per una.

  Quindi le due strade non erano due modi di fare la stessa cosa: la finestra di
  conversione della griglia aggiunge o toglie **fasce** a un'**estremità**,
  questa aggiunge o toglie **durata** in una **posizione qualsiasi** e scala ciò
  che segue. Una **converte** la griglia, l'altra **manutiene** un orario
  esistente — ed è per questo che stanno in due pannelli diversi. ⚠ Per noi
  resta fuori scope, ma la mappa è uno-a-uno con tre campi che abbiamo già
  (`Placement.start_slot`, il `boundary_slot` degli intervalli, il limite di
  mezza giornata della griglia): se un giorno si farà, è una **migrazione di
  dati**, non un cambio di configurazione.

  Due cose in più dallo stesso pannello, entrambe conferme e una utile:

  - la radio `Definizione delle etichette relative a: Orari | Fasce orarie`
    **commuta il pannello**, non lo filtra: in modo `Fasce orarie` il riquadro
    `Creazione automatica degli orari` sparisce del tutto e restano i ranghi
    `1…10`. 🔑 Le etichette ordinali **non si generano** — *sono* i ranghi — e
    l'unica operazione è rinominarle. Il generatore esiste solo per l'orologio:
    è la distinzione fra le due nozioni di «ora» che l'export iCal aveva
    incontrato dal lato del codice, qui come due pulsanti radio;
  - l'orologio conferma i ranghi per la **terza** via indipendente. Con
    `08:00 + 60 + 0`, la pausa di mezza giornata (`14:00–15:00`) è il rango 7 di
    10 — cioè **6 + 1 + 3** letto sull'orologio invece che sui conteggi — e i
    due intervalli (`09:50–10:00`, `11:50–12:00`) sono le code dei ranghi **2** e
    **4**, che sono i ranghi di `RECREATION` nel binario e i salti `2` e `2`
    della colonna in UI.

  ⚠ Aperta una minuzia: `Intervallo del pomeriggio` sta alle **11:50**, cioè
  *prima* della pausa delle 14:00 e quindi nella mezza giornata del mattino. O i
  nomi sono posizionali, o l'ingranaggio ⚙ porta una configurazione per mezza
  giornata che non abbiamo aperto. Non dedurne niente prima di guardare: è lo
  stesso genere di dettaglio che aveva fatto leggere il rango vuoto 6 come «la
  mensa».

  📖 **E trovato dove sta `Assegna le aule alle attività`**, che era il
  prerequisito bloccante di O1: non è una voce di menu ma un **pulsante dentro
  una finestra** — `Orario → Aule → Gestione del gruppo di aule`, si seleziona
  un gruppo, si preme il pulsante. Ne discende perché il menu `Elabora`,
  trascritto per intero il 2026-07-26, non nomina mai le aule: l'assegnazione
  non passa di lì. `Gestione del gruppo di aule` era già fra le stringhe
  estratte e non era stata collegata al comando. La guida elenca anche tre
  precondizioni, e la terza conferma alla lettera l'ordine delle due fasi:
  *«gli orari chiusi con tutte le attività piazzate»*.

- **2026-08-29 (sera) — D3: la fase 1 impara a contare le aule, e la risposta era già nel repo** —
  D3 chiedeva se accettare le rinunce della seconda fase come conseguenza
  dichiarata o insegnare al piazzamento a contare le aule. La domanda sembrava
  una preferenza di prodotto; era un'**osservazione mal letta**, e le tre fonti
  stavano già nei documenti:

  - la causale *«il gruppo di aule ha raggiunto il suo picco d'occupazione»*
    sta in `AffSco_UtilDiagnostic` — la diagnostica del **piazzamento**, cioè
    l'elenco delle ragioni per cui un'attività non si piazza;
  - nel risolutore passo-passo il pannello dell'attività conta **tutte e
    cinque** le risorse (`Aule 0`) e le risorse in conflitto diventano rosse,
    aule comprese;
  - il `Qtà` dell'aula è una capacità simultanea, con le colonne calcolate
    `Assegnate` / `Picco d'occ.`.

  🔑 **La frase falsa era una sola**, e questo repo l'aveva scritta in tre
  posti: *«non è un difetto del modello, è la conseguenza dichiarata di
  assegnare le aule dopo»*. Assegnarle dopo **non obbliga a contarle dopo**. In
  EDT l'ottimizzatore dedicato sceglie *quale* aula fra le ammissibili — i suoi
  cinque criteri sono tutti criteri di scelta, nessuno conta i posti, perché
  quel conto è già stato fatto.

  **La misura che ha deciso, prima di scrivere una riga di modello.** Sul Fermi
  con le aule: 92 richieste, 84 assegnate, **8 rinunce**, e i numeri di prima
  dicevano solo «39 celle contese». Contate a mano le celle in deficit, il
  risultato è netto in due modi:

  - su **nessuna** delle 26 celle contese l'unione delle candidate era in
    deficit. Un tetto sul totale non avrebbe morso: il deficit vive in un
    **sottoinsieme**, cioè è Hall e non un totale;
  - il deficit di Hall sommato su tutte le celle faceva **8**, che è
    esattamente il numero di rinunce, e stava tutto su un insieme solo —
    `{LAB-FIS, LAB-INF}`, ripetuto su sette celle. La fase 2 rinuncia una volta
    per ogni unità di deficit che la fase 1 le lascia, perché non ha altra
    mossa.

  Da qui `structural:room_pool`, trentesimo checker e ventisettesimo builder
  ([ADR-021](decisioni.md)). Il checker trova l'insieme colpevole col
  macchinario che il violatore di Hall usava già (`domain/analysis/flow.py`:
  flusso massimo, e il lato sorgente del taglio minimo *è* l'insieme
  deficitario) e nomina l'**unione delle candidate del gruppo colpevole**, non
  il taglio grezzo — i due contengono le stesse attività, ma il taglio si porta
  dietro aule che nessuno di quel gruppo chiede, e mandare a smontare l'aula
  sbagliata è il difetto peggiore di una diagnostica. Il builder posta i tetti
  sulla chiusura per unione degli insiemi dichiarati, troncata a 256.

  **Il vincolo è sano per costruzione**, e vale la pena dirlo perché è ciò che
  lo distingue da un'euristica: vieta esattamente le configurazioni che
  *nessuna* assegnazione potrebbe servire — il principio dei cassetti — quindi
  non toglie mai al piazzamento un orario che la fase 2 saprebbe completare.
  Non può creare scarti nuovi, può solo spostare un problema da «rinuncia
  d'aula» a «collocazione diversa».

  **Risultato, misurato:** 92 richieste su 92 assegnate, **zero rinunce**, zero
  deficit residuo, e la fase 1 continua a piazzare tutte e 284 le attività
  senza scarti. Prezzo: **1116 → 1536 constraint** (+420: quattordici pool con
  più di un'aula su 30 celle) e 1,07 → 1,27 s.

  ⚠ **Un difetto trovato integrando, non prevedendo — e non era del pezzo
  nuovo.** Il filtro `resources` di `trial_placements` sono le **chiavi di
  occupazione** dell'attività, e un'aula con due candidate non è una chiave:
  `activity_tokens` la mette fra i token solo a candidata unica, perché con due
  la scelta è della seconda fase. S.P., il violatore di Hall e la classifica
  dei vincoli erano quindi ciechi all'intera famiglia nuova — il checker girava
  e scartava ogni pool, perché nessuno toccava le risorse chieste. Si vedeva
  solo guardando un `S.P. = 2` che avrebbe dovuto essere 1. Il filtro ora
  comprende le candidate dichiarate; allargarlo è sempre sano, perché è
  un'ottimizzazione e un'ottimizzazione più larga costa, non sbaglia.

  ⚠ **Il banco a testimone ha un derivatore in più, e un seed vacuo
  dichiarato.** Il testimone non ha aule: il derivatore ne crea
  **esattamente** quante ne serve il picco di simultaneità misurato sul
  piazzamento, così il vincolo è soddisfatto e stretto. A picco uno il gruppo
  avrebbe una sola aula, cioè una chiave di occupazione, e starebbe misurando
  un'altra famiglia: quel caso è una derivazione vacua, e `run_family` lo
  salta invece di spacciarlo per verde. Misurato: 4 seed su 5 lo esercitano,
  il seed 2 no.

  **814 test verdi**, 17 skip (uno nuovo, quello lì sopra).

- **2026-08-29 — La griglia oraria, finalmente guardata (e un confronto che non cercavo)** — L'osservazione di
  EDT era dichiarata conclusa da ADR-016, ma **O2 era rimasta aperta apposta**:
  la configurazione della griglia era l'unica parte del modello del tempo nota
  per sola via documentale, ed è quella su cui poggia tutto il resto. Riaperta
  perché la licenza di prova fa scadere le basi dopo due settimane e la base
  del produttore — `Monoposto/Esempio.edt`, 40 classi, 3 sedi, 984 corsi tutti
  piazzati — si può ricopiare sul Desktop all'infinito.

  Osservata `File → Strumenti → Cambia i parametri della griglia oraria`. Tre
  cose che le stringhe non dicevano:

  - 🔑 **Il numero di fasce è in sola lettura.** Non si scrive «10»: si
    `Aggiungi`/`Togli` *N* fasce **all'inizio** o **alla fine** della giornata,
    due righe gemelle. «Passare da 10 a 8 fasce» non è una domanda ben posta:
    manca *da quale capo*, e il perché è l'allineamento — il rango di una fascia
    cambia solo se se ne aggiunge una *prima*. ⚠ La prima stesura di questa
    voce concludeva «la griglia si modifica ai bordi, **mai** al centro»: la
    seconda schermata l'ha smentita nel giro di un turno, perché il pannello
    `Orari` porta un `Inserisci / cancella una fascia oraria` che è
    posizionale. Restano vere le due righe gemelle; falsa la generalizzazione.
  - I **giorni lavorativi** sono una **maschera** di sette caselle, non un
    conteggio, e il **primo giorno della settimana** è un campo a sé. Sulla demo:
    Lun–Ven bianchi, Sab e Dom grigi, primo giorno lunedì.
  - La **suddivisione** è un radio a **sei valori** — 2, 3, 4, 6, 12, `Nessuno` —
    quindi `NombrePlacesParSequence` non è un intero libero. Default `Nessuno`.

  Due cose promosse da [INFERENZA] a osservazione: la frase *«La durata della
  fascia oraria serve per il calcolo dei servizi dei docenti»* è stampata dentro
  la finestra, e la demo è `5 × 10 × 1` a 60 minuti — il che **chiude per
  osservazione** la codifica `place = giorno × 10 + rango` dedotta dal formato
  binario, perché il 10 è letto nel campo che lo imposta.

  Nello stesso giro, `Parametri della base dati → Istituto → Orari`, che è una
  procedura in tre passi (`Mezza giornata`, `Intervalli`, `Orari / Fasce
  orarie`). Il passo 1:

  - 🔑 **La pausa di mezza giornata non è un confine: è un blocco di fasce.**
    `mattina 6 + pausa 1 + pomeriggio 3 = 10`, che è il `NombreSequencesParJour`
    della griglia. Le righe si chiamano `M1…M6`, poi una **senza nome** fra due
    linee verdi, poi `P1…P3`. La fascia di pausa **esiste** e non è piazzabile.
    Il documento diceva che la linea si definisce in numero di fasce e non in
    orario: vero, ma diceva anche che le due modalità erano `Giornata continua`
    e *«Giornata con una pausa delimitata da un'ora di fine mattinata»* — la
    seconda in UI si chiama `2 mezze giornate separate da una pausa` e non
    chiede **nessun** orario, solo tre conteggi. Corretto.
  - ☑ *«Dopo la pausa della mezza giornata, riprendi all'inizio dell'ora
    successiva»* è **la stessa discontinuità** che l'export iCal già gestisce
    spezzando un'attività in corse contigue. Lì era dedotta dalle `SlotLabel`;
    qui è una casella.
  - ⚠ **Una maschera che non abbiamo**: una casella per giorno, *«I giorni
    spuntati saranno ignorati durante il calcolo delle giornate libere»*. Non è
    la maschera dei giorni lavorativi — il giorno resta e ci si lavora, ma non
    conta come libero. `FreeGuaranteedChecker`/`Builder` contano su tutti i
    `days_per_cycle`. Nuovo debito dichiarato.

  I passi 2 e 3, che hanno chiuso O2:

  - 🔑 **L'intervallo è un confine, e la conferma è su una trasformazione.** Il
    pannello elenca due intervalli con la colonna `Nr. fasce orarie dopo
    l'ultimo intervallo` = **2** e **2**; la tabella `RECREATION` del binario
    porta i ranghi **2** e **4**. La UI mostra il salto, il file il cumulato: le
    due letture combaciano su una regola, non su un numero, che è una verifica
    molto più forte di una coincidenza. E sulla griglia le linee gialle stanno
    **fra** due righe, mentre la pausa di mezza giornata è una riga intera — la
    differenza fra un confine e una `Place`, nella stessa immagine.
  - Due cose che le stringhe non davano: gli intervalli hanno un **orario
    proprio** (09:50–10:00 e 11:50–12:00, dieci minuti ritagliati *prima* del
    confine, che non allungano la giornata), e una colonna **`Classi`** — un
    intervallo può non valere per tutte.
  - Corretta un'attribuzione del 2026-07-26: il rango vuoto **6** era stato
    letto come «la mensa». È la **fascia di pausa della mezza giornata**; la
    mensa è ciò che ci si svolge dentro, e sulla demo non ha turni attivi.
  - 🔑 Il passo 3 è il **generatore delle `SlotLabel`**: `Primo orario sulla
    griglia` 08:00, `Durata reale delle fasce orarie` 60, `Durata tra le fasce
    orarie` 0. La *durata reale* è un campo **diverso** da quello della finestra
    di conversione, che è la durata della fascia di **calcolo** — le due nozioni
    di «ora» sono letteralmente due caselle in due finestre. E `Durata tra le
    fasce orarie` permette etichette con un **buco** che il modello di calcolo
    non conosce: l'export iCal fa bene a leggere le etichette invece di
    `slot_minutes`, perché lì le due grandezze divergono per costruzione.

  E la scheda `Mensa`, che era in bilico come «fuori scope da dichiarare»:
  l'osservazione lo **rafforza**. Non è un'ora bloccata — è una finestra oraria
  con maschera per giorno propria, divisa in **turni**, ciascuno destinato a
  classi (con un `N. Max.`) o docenti, con `Equilibra automaticamente` e
  `Statistiche di ripartizione`. È un terzo problema di assegnazione con
  capienze, della stessa forma delle aule. Entrarci costerebbe un modello a sé.

  Una quinta schermata, `Parametri → Piazzamento`, ha invece prodotto **zero
  informazioni nuove** — ed è un risultato, non uno spreco. Ogni valore
  coincide con quanto documentato il 2026-07-26 dalla stessa base: le due
  caselle dei buchi, il raggruppamento all'inizio della giornata, i due massimi
  quindicinali su «rispetta il massimo in ciascuna settimana», i primi otto
  degli undici criteri nell'ordine. Una fonte che si rilegge a un mese di
  distanza e dà la stessa cosa è una fonte replicabile.

  Ha però prodotto un **confronto**, che lo screenshot da solo non conteneva:
  per EDT il buco si misura sulla **giornata**, e la casella `Non conteggiare
  come buchi le ore libere prima o dopo la linea di fine mattinata` ne toglie la
  pausa — **separatamente per classi e per docenti**, e sulla base è spuntata
  per i docenti e non per le classi. Da noi `MaxGapChecker` e il criterio
  `buchi` misurano sempre e solo **dentro la mezza giornata**: ci comportiamo
  come se la casella fosse spuntata per tutti, quindi giusti sui docenti e
  sbagliati sulle classi. Nuovo debito, non toccato subito perché cambierebbe la
  quantità di un vincolo hard (il D.T.B.) oltre a un livello della catena.

  E **O5 è stata riclassificata da osservazione a decisione**: la lista degli
  undici criteri era già scritta da luglio, quindi non manca uno screenshot —
  mancano dieci decisioni dentro/fuori. Tre le decide già la struttura (la
  mensa è fuori scope; due criteri valgono solo con la suddivisione sub-oraria,
  che è a `Nessuno`).

  E la tabella delle stringhe, rigenerata dal binario per dare all'utente i nomi
  esatti delle voci di menu invece di fargliele cercare, ha pagato un dividendo
  che nessuno cercava: la finestra `FicheEdt_OptimiseurSalles`. Le sue etichette
  mappano **uno a uno** sui cinque `TypeChoixOptimSalle`, e **smentiscono la
  lettura che avevamo dato al primo**. `tcosChangements` non è «minimizzare i
  cambi rispetto alla ripartizione precedente»: l'etichetta dice `Limita gli
  spostamenti tra attività consecutive` — è il **cammino** di una classe fra
  un'ora e la successiva, e `tcosChangementsConfort` è lo stesso fra attività
  **non** consecutive. Sono distanze fisiche, non differenze fra ripartizioni.

  🔑 Conseguenza diretta sul codice già scritto: il **secondo livello della
  nostra seconda fase** — «i cambi rispetto alla ripartizione precedente» — **non
  è nessuno dei cinque criteri di EDT**. È nostro, ed è la stabilità, l'analogo
  per le aule di L4. Non è sbagliato, ma va dichiarato come voce in più invece
  che passare per traduzione di `tcosChangements`, che è quel che
  [aule.md](edt/aule.md) faceva.

  La stessa finestra dichiara **quattro** caselle numerate di criterio (una
  catena lessicografica a quattro livelli, la stessa forma della nostra) e un
  `Ottimizza per` **Classi/Docenti** con liste di prioritari — la separazione per
  popolazione vale anche nella fase aule. Di O1 resta solo *quali siano i
  quattro default*.

  Infine la griglia dei **servizi** di un piano di studi, sulla stessa base. Ogni
  colonna coincide con quanto scritto il 2026-07-09 dal Fermi — `Coeff. 60/60`,
  `Alu./… 15` mai digitato, `H/Al.` = `H/Classe`: la cascata di ADR-003 si
  comporta identica su due basi diverse, il che è la sua prima verifica fuori
  dai nostri dati. La base del produttore è per inciso una **secondaria di primo
  grado italiana** (`1°/2°/3° TEMPO NORMALE`, `3° TEMPO PROLUNGATO`, classi di
  concorso `A-60 A-49 A-30 A-28 A-22 A-25 A-01 REL`, 30h00), non francese.

  🔑 **E `MS` è vuota anche lì, sulla riga `RELIGIONE` compresa** — che è un
  servizio ordinario del piano, `Alu. 390`, `H/Classe 1h00`, `H/Al. 1h00`,
  dovuto da tutti. Il che obbliga a **emendare ADR-020**: il Motivo diceva che
  il dato mancante «è un dato che EDT ha già», e l'affermazione dimostrata è più
  debole — EDT ha la **colonna** dove il dato starebbe e non la riempie nemmeno
  nella propria base di riferimento. La decisione non cambia e semmai si
  rafforza (se il produttore non distingue IRC da alternativa, **nessun import**
  poteva darcelo — che era l'argomento contro l'alternativa 2), ma
  `Service.election_group` va dichiarato per quello che è: **nostra estensione**,
  non traduzione di `MS`.

  E poi la tendina di `MS`, che era l'ultima richiesta della serie e che avevo
  presentato come *«la meno utile»*. Sbagliato: 🔑 **i codici sono otto più il
  vuoto, non sette, e quello che mancava è quello che conta.** `S = Senza` non
  è «nessun valore» — è **`Tronc commun`**, il *percorso curricolare*, la riga
  che tutti seguono; `O F N X L R D` sono tutte forme di **opzione**. Il vuoto è
  una nona voce a sé (`Senza specifica` / `Aucune modalité`).

  Il che chiarisce, e ridimensiona, l'emendamento scritto un'ora prima:
  `MS` **è** l'asse *«dovuta da tutti oppure opzione»*, ma non dice **quali
  opzioni siano alternative fra loro**, che è la sola cosa che
  `Service.election_group` dice. Non sono due risposte alla stessa domanda: sono
  due domande. ⚠ E ne esce un caso che il nostro modello non copre — una riga
  marcata opzione ma fuori da ogni gruppo di elezione verrebbe ancora contata
  come dovuta da tutti, lo stesso falso positivo di ADR-020 su un altro ingresso.
  Resta una decisione e non un difetto, perché nessun dato lo esercita.

  ⚠ E un falso amico corretto: `L` è **`Locale`**, non «Accademica» come era
  scritto dal 2026-07-26. Il francese `académique` è l'aggettivo di *académie*,
  la circoscrizione scolastica: `Ajout académique au programme` è
  un'**aggiunta locale al programma**. Aggiunto alla tabella dei falsi amici
  insieme a `S`.

  Stessa griglia, seconda conseguenza: `Ridotto` e `Sdop.` sono vuote su tutte
  le righe di entrambe le basi. **O3 non è osservabile, solo sperimentabile**, e
  con D1 sciolta non sblocca più niente — la domanda residua è se tenere
  `reduced_minutes`/`split_minutes` o toglierli.

  ⚠ E una assenza, che vale quanto una presenza: **il ciclo pluri-settimanale
  non c'è**. La finestra mostra i sette giorni della settimana e nient'altro,
  mentre lo XSD ammette `NombreJoursParCycle > 7` e le stringhe hanno un
  `Ciclo personalizzato`. Vive dunque nel solo wizard di creazione — da
  confermare. O2 resta aperta per questo e per la linea di mezza giornata.

- **2026-08-28 (sera) — D1: la copertura era per classe e si spacciava per
  alunno** — ⛔ La sola voce marcata *blocca l'import* è sciolta
  ([ADR-020](decisioni.md)), e la prima cosa che l'analisi ha trovato è che
  **il nome della voce nominava metà del problema**. La voce diceva «l'unità è
  la parte dove dovrebbe essere l'atomo»; il caso misurato — IRC e attività
  alternativa — è una classe con **una sola partizione**, dove l'atomo *è* la
  parte. Portare l'unità sull'atomo su quel caso non cambia un bit.

  Erano **due difetti**, e le tre strade elencate nel todo li confondevano in
  uno:

  - **il lato osservato** — con due partizioni, un'attività sulla parte `Y`
    non porta la chiave della parte `X`: l'alunno che sta in `X∩Y` vede
    sparire le ore ricevute attraverso l'altra divisione. Misurato su una
    classe sdoppiata due volte: **quattro** scostamenti inesistenti, del tipo
    `1A_L1, Laboratorio: atteso 60, osservato 0`. Si chiude portando l'unità
    sull'**atomo** — e senza un dato nuovo, perché `activity_tokens` gli atomi
    li marca già per l'occupazione;
  - **il lato atteso** — il piano è un **catalogo**, non un curriculum:
    contiene REL e ALT perché la classe le riceve entrambe, ma nessun alunno
    le deve entrambe. **Due** scostamenti su ogni classe italiana, con una
    sola partizione. Nessuna proprietà dell'orario dice che sono in
    alternativa: è un **dato**, e mancava.

  🔑 **E il dato mancante ce l'aveva EDT**, in due colonne che avevamo
  documentato senza collegarle. Le durate del servizio sono **quattro**, non
  tre: `H/Classe` (*Durée en classe*) e `H/Al.` (*Durée par élève*) sono
  quantità distinte — noi confrontavamo un atteso per-alunno contro
  `class_minutes`. E `MS` (*Modalità di scelta*, `Modalité d'élection`) porta
  sette codici, fra cui **`R` Religioso**: EDT marca la riga elettiva sulla
  riga stessa. `Service.election_group` è la forma minima di quel meccanismo —
  un'etichetta, non l'enum, perché `MS` viene dalle stringhe (📦) e non è mai
  stata osservata in UI (ora **O6** in [todo.md](todo.md)).

  **Il prezzo per la scuola** è ciò che decideva fra le strade, e non è
  un'opinione: un `StudyPlan` per combinazione — misurato, funziona — costa
  **quattro piani** per una 3A articolata con IRC; l'etichetta ne costa **una
  riga**. ⚠ E il colpo di grazia alla prima è che quel documento **non
  esiste**: nessun quadro orario ministeriale descrive «il curriculum
  dell'alunno che fa religione e francese», quindi nessun import — e nessun
  agente che legge un PDF, che è la via d'ingresso decisa per Aurora — potrebbe
  alimentarlo.

  Due guardie del progetto hanno fatto il loro mestiere invece di essere
  aggirate: `test_codici_copre_tutto_il_catalogo` ha preteso che le due causali
  nuove fossero classificate per decisione esplicita (`FUORI`, stessa ragione
  di `coverage_mismatch`: `PLACEMENT_INDEPENDENT`), e
  `test_tutte_le_causali_usano_solo_segnaposto_noti` ha rifiutato la frase che
  ci infilava il **numero** — i numeri stanno in `quantities`, ed è ciò che
  rende il verdetto verificabile. La frase ha perso il conteggio, `group` è
  entrato nel vocabolario dei segnaposto **e** in `Finding.key`: due gruppi
  insoddisfatti sulla stessa unità sarebbero altrimenti collassati in un
  verdetto solo — la stessa forma già misurata su `subject`.

  ⚠ **Ciò che resta fuori, dichiarato**: se due parti della stessa
  combinazione portano piani diversi, l'unità **non si misura** e si nomina
  l'errore (`ambiguous_study_plan`). Fondere i due piani sarebbe inventare il
  campo che ADR-017 ha rifiutato, e sceglierne uno in silenzio sarebbe peggio.

  Sette test nuovi in `tests/test_copertura_per_alunno.py`, uno in
  `tests/test_extraction.py`; il test che teneva fermo il limite resta, con il
  nome e la ragione corretti — è ora il caso in cui il dato **non** è
  dichiarato, e i due scostamenti sono il comportamento giusto.

- **2026-08-28 (la review della seconda fase, e il file che si leggeva da solo)**
  — Cinque difetti applicati, ciascuno riprodotto prima di essere corretto e
  ciascuno verificato per mutazione: nessuno era visibile rileggendo il codice,
  e tre stavano in commenti che dichiaravano vera una proprietà falsa. È il
  pattern di questo progetto, di nuovo.

  ⛔ **Il residuo di ADR-018 sulle sedi si misurava nell'unità sbagliata, e il
  passato tornava a rendere infattibile il presente.** La correzione del
  2026-08-28 mattina aveva allineato `_frozen_site_changes` al **checker** —
  che conta transizioni fra *insiemi* di sedi — mentre il tetto che quel
  numero clampa è una somma dei letterali del **builder**, che ne crea uno per
  ogni coppia **ordinata** di sedi diverse fra due fasce adiacenti. A capienza
  cumulativa le due grandezze divergono: `{A,B}` alla fascia 0 e `{C}` alla
  fascia 1 valgono **1** cambio per il checker e **due** letterali per il
  builder, quindi `max(per_day, consumo)` non clampava abbastanza. Misurato:
  `check_schedule` non ha **niente** da ridire su quell'orario e `solve()`
  risponde `INFEASIBLE` — esattamente la metà vietata del criterio.
  🔑 La regola che ne esce, e che vale per ogni residuo futuro: **il consumo
  delle congelate si conta nell'unità del vincolo che lo riceve, non in quella
  del checker che lo ispira.** A capienza 1 i due conteggi coincidono riga per
  riga, ed è per questo che nessuna istanza esistente si è mossa.

  ⚠ **E [ADR-019](decisioni.md) prescriveva la regola sbagliata**, perché è
  da lì che il conteggio a insiemi era venuto: le sue *Conseguenze* dicevano
  che «il residuo di ADR-018 va calcolato con **la stessa** regola» del
  checker. Corretto in loco più un emendamento datato, nella forma di ADR-003:
  lasciarlo com'era avrebbe mandato chi cerca il perché di una decisione a
  leggere prescritta proprio la regola che questo giro ha misurato come causa
  di un `INFEASIBLE` per colpa del solo passato — «niente accumulo di
  versioni» dentro il file delle decisioni. ⚠ L'emendamento dichiara anche ciò
  che **non** riabilita: appiattire `by_cell` resta l'errore che ADR-019 aveva
  corretto, perché conta anche le coppie *dentro* una fascia e in un ordine
  deciso dal queryset.

  ⛔ **La seconda fase rubava l'aula a chi stava fuori dal perimetro.**
  `activity_tokens` mette l'aula fra le chiavi di occupazione anche **senza
  assegnazione**, quando le candidate dichiarate sono una sola — regola scritta
  lo stesso giorno, in `state.py`. `RoomContext.build` leggeva invece il solo
  `assigned_room`, quindi quell'occupazione non entrava in `frozen_load` e
  `_post_capacity` la regalava agli estratti. Misurato: zero conflitti
  d'occupazione prima di `assign_rooms --estrazione`, un `resource_occupied`
  sull'aula dopo — creato dalla fase stessa. ⚠ Si vede **solo** con
  un'estrazione: senza, ogni piazzata che dichiara aule è una richiesta, e il
  modello la conosce. Una proprietà del percorso senza perimetro scambiata per
  una proprietà del codice.

  ⛔ **`Piazza e sistema` rispondeva «la collocazione non è ammissibile» su una
  cella vuota.** Il commento di `CAUSALI_DI_PREFILTRO` diceva che un pin fuori
  dominio «può venire **solo**» dai due builder che pre-filtrano. Falso: il
  dominio lo restringe anche `SolverContext.build`, *prima* di qualunque
  `restrict()` — un'immobile già piazzata ha dominio di cardinalità **uno**, e
  altrettanto ciò che sta fuori dall'estrazione. Il salto logico è «i
  pre-filtri sono due» ⇒ «le cause sono due», ed è tenuto in piedi da un test
  che verifica la prima. Ora `_fuori_dal_modello` riconosce le tre ragioni
  (bloccata, sospesa, fuori perimetro) **prima** di consultare il catalogo, e
  nomina il rimedio, che non è mai allentare un vincolo: è sbloccare, o
  allargare l'estrazione.

  ⛔ **S.P. valeva zero per ogni attività con una sola aula candidata.**
  `structural:room_assignment`, nato non monotono e rilassato in `hall.py` e in
  `blame.py`, restava dentro il loop di `residual_domain`, che passava
  `relaxed=False`. Il suo finding esiste solo per le **piazzate**, quindi ogni
  cella di prova produce una chiave nuova: misurato, `6 → 0` su una griglia
  interamente libera. ⚠ E l'argomento che teneva quel default — *«per l'utente
  un dominio più stretto è informazione, non un bug»* — è stato **falsificato
  invece che riscritto**: zero non è una stima prudente, è la frase «nessuna
  collocazione ammissibile», che `manage.py analyze` stampa **per prima**
  perché ordina in senso crescente. Il Fermi ha esattamente quella forma
  (`SPECIAL_ROOMS["MOT"] = ("PALESTRA",)`). Le tre letture di
  `trial_placements` hanno ora la stessa regola.
  ⚠ Il caso morde a candidata **unica** e non a due, ed è controintuitivo:
  `_hard_keys` filtra sulle risorse dell'attività, e con due candidate l'aula
  non è nei token, quindi il finding non passa neppure il filtro.

  ⚠ **E `manage.py analyze` falliva in CI su un orario impeccabile.** Contava
  `room_unassigned` fra le violazioni hard, cioè dichiarava incoerente ogni
  orario appena uscito da `solve` e non ancora passato per `assign_rooms` —
  mentre `solve` e `assign_rooms` quel codice lo escludono già, con la ragione
  scritta: descrive un orario **incompleto**, non illegale. Delle tre, `analyze`
  era l'unica a decidere un exit code. Il finding resta stampato: si dichiara,
  non si conta.

  🔑 **E il changelog è uscito da `CLAUDE.md`.** Valeva **165 KB su 204** —
  l'81% di un file che entra nel contesto di *ogni* sessione, decine di
  migliaia di token di racconto letti prima di qualunque domanda; e
  `AGENTS.md`, che dal 2026-08-27 è un symlink allo stesso file, lo fa pagare
  due volte a chi legge entrambi. Sta ora in `docs/changelog.md`, integro riga
  per riga. `CLAUDE.md` scende a **40 KB** e guadagna la regola che gli
  mancava: porta **lo stato**, non la storia — una voce nuova va nel
  changelog, e qui si *sostituisce* la riga diventata falsa.

  **Sette test nuovi, sette mutazioni, sette esiti distinti.** Suite: **779
  test verdi**, 16 skip.

- **2026-08-28 (la classe articolata, e l'unità del monte ore)** — **L'ultima
  delle «tre condizioni da non perdere» di ADR-015 ancora non verificata è
  stata verificata, e regge a metà.** `scope-v1.md` copre la classe articolata
  — la 3A con 12 alunni di Manutenzione e 10 di Elettronica — senza entità
  dedicata: *«la parte A segue un piano, la parte B un altro, le ore comuni si
  insegnano a classe intera»*, con la condizione scritta accanto, *«da
  verificare presto, non a modello finito»*. Non era mai stata esercitata:
  `test_classes.py` asserisce che una parte **può** portare un piano proprio,
  che è la metà anagrafica, e nient'altro.

  🔑 **La prima metà tiene, ed è misurata invece che dichiarata.** La copertura
  legge davvero il piano della parte; le due articolazioni **stanno nella
  stessa fascia** — che è ciò che la scorciatoia compra, perché parti della
  stessa partizione sono insiemi disgiunti di alunni — e l'ora comune a classe
  intera **occupa** entrambe le parti, quindi nessuno fa laboratorio mentre la
  sua classe fa italiano. La decisione 4 di ADR-015 non decade.
  **Tre mutazioni, tre esiti distinti**: la parte che perde il piano proprio
  uccide un test solo, la classe intera che smette di occupare le sue parti ne
  uccide quattro su cinque, la parte che occupa anche la classe uccide solo
  quello del parallelismo.

  ⛔ **La seconda metà no, e non riguarda solo la classe articolata.**
  `structural:coverage` misura ogni **parte** contro il piano **intero** della
  parte: è una lettura *per alunno*, ed è quella giusta. Ma un alunno non sta
  in una parte, sta in una **combinazione** di parti — una per partizione — e
  quella combinazione è l'**atomo** di ADR-017, che il modello costruisce già
  per l'occupazione e non per il curriculum. Con una sola partizione parte e
  atomo coincidono; con due, o con una sola le cui parti ricevono materie
  diverse — **IRC e alternativa, cioè ogni classe italiana** — la copertura
  dichiara che chi fa religione deve l'ora di alternativa, e viceversa.
  Misurato: due scostamenti inesistenti sulla classe più ordinaria che ci sia,
  quattro su una 3A articolata con IRC.
  ⚠ **Non l'aveva visto nessuno perché il Fermi non ha nessuna partizione**, e
  `test_beyond_fermi.py` le costruisce senza mai chiamare `check_schedule` — la
  forma di sempre, una proprietà del dataset scambiata per una proprietà del
  codice. La scappatoia esiste ed è misurata (un `StudyPlan` gemello per
  combinazione: funziona, e costa quattro piani per una classe), ma sceglierla
  è **una decisione di modello**, non una correzione: cambia i dati che una
  scuola deve inserire. Le tre strade sono in `scope-v1.md`, e la terza — il
  monte ore **tripartito** del servizio, che è la risposta di EDT alla stessa
  domanda — poggia su due campi (`reduced_minutes`, `split_minutes`) che sono
  nello schema dal primo giorno, **letti da nessuno**, e la cui semantica non è
  mai stata osservata in UI.

  🔑 **E la mutazione ha trovato un difetto vero, in un punto che nessuno
  guardava: `Finding.key` perdeva la materia.** Mutando i token della classe
  intera, due scostamenti diversi si presentavano come **uno**: la chiave
  esclude il messaggio per scelta, e per `coverage_mismatch` la materia vive
  solo lì — quindi un'unità a cui mancano due materie per lo stesso numero di
  minuti (`atteso 60 / osservato 0` su ciascuna, il caso normale) produceva un
  finding solo, e *quale* delle due venisse nominata dipendeva dall'ordine di
  iterazione. In uno strumento il cui valore è nominare la causa, questo è il
  difetto peggiore della famiglia. Corretto con il campo `subject`, e
  `subject_constraints` **non** ne ha bisogno: là la frase porta `subject_a`,
  uguale per tutte le righe che potrebbero collidere.

  ⚠ **E il campo in più ha rotto i due lettori che spacchettavano la chiave per
  posizione** — l'oracolo differenziale e il banco, insieme, con quindici test
  rossi. `Finding.key` è ora una **tupla nominata**: un campo in più diventa
  additivo invece di essere una trappola per chi lo aggiunge. La regola resta
  scritta dove serve: **tutto ciò che distingue due verdetti dev'essere un
  campo**, perché il messaggio è fuori dalla chiave.

  ⚠ Nello stesso giro, `test_fermi_i_criteri_di_qualita_misurati` — scritto il
  giorno prima — si è rivelato **sensibile al carico**: verde da solo, rosso
  nella suite intera, perché a 3 s per livello un criterio di qualità può non
  restituire alcuna soluzione e la catena si ferma, che è il comportamento
  dichiarato di `solve_chain`. Pretendeva la coda esatta dei livelli; ora
  pretende che i livelli girati siano un **prefisso** dell'ordine dichiarato e
  che almeno uno dei criteri dopo `gaps` abbia divario positivo — il fenomeno
  che il test misura, senza dipendere da quale livello faccia in tempo.

  **Quattro mutazioni in tutto, quattro esiti distinti.** **772 test verdi**,
  16 skip. Il Fermi è invariato per costruzione: non ha partizioni.

- **2026-08-28 (il costo dei criteri di qualità)** — **Il numero che questo
  file dichiarava da un giorno era misurato male, e la diagnosi che ne
  discendeva era l'opposto di quella giusta.** La nota di stato diceva «cinque
  criteri senza limite non tornano in nove minuti, con `--limite 15` chiudono
  in 39,5 s lasciando due livelli su sei con l'ottimo non dimostrato», e da lì
  il docstring di `manage.py solve` concludeva che *«`--limite` non è
  opzionale»*. Entrambe le frasi vengono da una misura a **un lavoratore**, che
  non è come il comando gira.

  🔑 **Il fenomeno vero: un livello non è lento perché sia difficile da
  ottimizzare, è lento perché è impossibile da dimostrare.** `gaps` arriva a 0
  e chiude in un secondo, e la ragione non è che sia un criterio facile — è che
  **zero è anche il suo limite inferiore banale**, quindi valore e limite si
  toccano subito. `free_half_days` si ferma a 202 con limite inferiore **6**,
  `regularity` a 236 con **18**: il divario non è un residuo di ricerca, è
  tutto il valore. Il tempo se ne va in una dimostrazione che non arriverà.

  🔑 **E i livelli che contano un fallimento non hanno il problema**, per la
  stessa ragione e al contrario: scarti, violazioni nuove e spostamenti hanno
  ottimo zero, cioè il limite banale, e sul Fermi chiudono in 1,7 s e 0,7 s.
  Da qui il **budget dei soli livelli di qualità** (`BUDGET_QUALITA`, 15 s dal
  ginocchio della curva: `free_half_days` 202 a 15 s e 199 a 60 s). ⚠ Un
  comando la cui configurazione predefinita non termina è un difetto, e un
  budget globale sarebbe stato il rimedio sbagliato — punirebbe proprio i
  livelli che l'ottimo lo dimostrano. `--limite` sovrascrive in **entrambi** i
  versi, anche allungando.

  🔑 **Il rendiconto porta il divario, e CP-SAT quel numero ce l'aveva già.**
  «Ottimo non dimostrato» da solo non distingue chi ha finito da chi non ha
  cominciato: `isolated 0` con limite 0 è *l'ottimo*, e mandare a alzare
  `--limite` è un consiglio a vuoto; `regularity 236` con limite 18 è un'altra
  cosa. `BestObjectiveBound` costava zero e lo buttavamo via.

  ⚠ **E i lavoratori pesano più del limite.** A 15 s per livello, misurato: con
  **1** lavoratore `regularity 359`, `free_half_days 243`, `isolated 37`; con
  **4**, `236`, `202` e **0** — l'ottimo, raggiunto in 7 s e non dimostrato.
  Il tracciato dell'incumbent lo spiega: a un lavoratore `isolated` resta
  fermo a 37 dal secondo 1 al secondo 36 e poi **crolla a 0** entro il 50°.
  ⛔ Da cui una contromisura che sembrava ovvia e sarebbe stata esattamente
  sbagliata: un limite «fermati dopo N secondi senza miglioramenti» avrebbe
  tagliato al quinto secondo e fissato 37 invece di 0. Il plateau non era il
  fondo. `manage.py solve` dichiara ora quanti lavoratori ha usato, perché un
  numero di qualità senza quel dato non è confrontabile con nessun altro.

  ⛔ **E la riparazione modellistica ovvia peggiora le cose.** Un limite
  inferiore *implicato* per `free_half_days` — `somma_h attiva(g,h)·len(span_h)
  >= somma_s occupata(g,s)` per chiave e giorno, valido sempre — non chiude il
  divario: misurato a 15 s, il valore passa da 202 a **209** e il limite da 6 a
  **4**. La presolve di CP-SAT ne deriva già almeno altrettanto, e le 140 righe
  in più costano ricerca. Scritta, misurata, buttata — e non riprovata, perché
  romperebbe anche l'invariante «un criterio posta **solo definizioni**», da
  cui dipende `_valori_di_base` dell'arbitrato.

  **Sei mutazioni, sei esiti distinti**, e il fenomeno entra nella suite invece
  di restare in una sessione: `test_fermi_i_criteri_di_qualita_misurati` gira a
  `--limite 3` (14 s) e pretende che `gaps` abbia divario zero e `regularity`
  no — se il limite inferiore smettesse di essere inutile, quel test
  diventerebbe rosso e la decisione si riprenderebbe guardando quel rosso.
  **766 test verdi**, 16 skip.

- **2026-08-28 (l'orario nel telefono)** — **Il primo pezzo che consegna
  invece di calcolare.** `domain/ical.py` più `manage.py export_ical`: è
  l'unica voce ✅ di `scope-v1.md` che non riguarda il motore, e la sua riga là
  era una frase sola — *«i docenti vogliono il proprio orario nel telefono»*.
  In EDT il canale esiste ed è dichiarato per quello che è
  (`UtilitaireSco_ExportICal`, `ImpEDT_ExportICALRencontre`,
  `ImpEDT_ExportICALConseil`): il verso **esterno**, distinto da
  `Partenaire_Index` che è il verso verso gli altri gestionali.

  🔑 **Ed è il punto in cui la fascia di calcolo smette di essere l'ora.**
  `tempo-e-calendario.md` distingue per nome due grandezze che tutto il resto
  del progetto ha potuto confondere impunemente, perché il motore ne usa una
  sola: la **fascia di calcolo** (l'unità del piazzamento *e* dell'ora di
  servizio del docente) e l'**etichetta oraria** (*«ad esempio 55 minuti»*,
  orari sfalsati). Un calendario legge la seconda. Da qui `SlotLabel`
  (migrazione `0011`), che non è un campo nostro: è il `Place` dello XSD
  `Partenaire_Index` V4.6 (📦, livello 1) con i suoi `@LibelleHeureDebut` e
  `@LibelleHeureFin` — cioè l'orologio sta **per fascia**, non sulla griglia,
  ed è per questo che gli orari sfalsati sono rappresentabili. Nel file
  `slot_minutes` non compare.

  ⚠ **E senza etichette si rifiuta.** È la funzionalità, non una mancanza: il
  fallimento alternativo — «si comincia alle 8» — non fa rumore e mette le
  lezioni di tutta la scuola all'ora sbagliata. Il rifiuto nomina le fasce
  scoperte.

  🔑 **Un'attività non è sempre *un* evento.** Se l'orologio salta fra due
  fasce consecutive — la pausa di mezza giornata è il caso normale, le 12 che
  riprendono alle 14 — un blocco da due fasce a cavallo della linea non è una
  lezione di quattro ore: sono due lezioni. Le fasce si spezzano quindi in
  **corse contigue** nel tempo dell'orologio. Sommare `duration_minutes`
  all'ora d'inizio avrebbe dato la risposta giusta su ogni scuola senza pausa
  e sbagliata su tutte le altre, senza mai fallire rumorosamente.

  ⚠ **E il Fermi non lo esercita, contro la previsione scritta nel test.** Il
  suo orologio ha la pausa, ma i blocchi da due fasce sono **quattro** su 284 e
  nessuno è atterrato a cavallo — per caso, non per regola: nel modello
  *niente vieta* a un blocco di scavalcare la mezza giornata. Il divieto
  esiste ed è `Break` + `respects_breaks` (`structural:grid`), che questo
  dataset non usa. Il conto è quindi esatto — **9372 = 284 × 33** — e la metà
  interessante la misura il test spostando a mano un blocco dove il solver non
  l'ha messo: **33 eventi in più**, non 33 eventi più lunghi.

  ⚠ **Niente `RRULE`, ed è una decisione.** «Ogni lunedì» sarebbe più compatto,
  ma la maschera di settimane **non è una ricorrenza**: annuale e quadrimestre
  lo sono, la sostituzione di ADR-014 (un bit solo) e l'`Amenagement` no, e
  festivi e confini di periodo andrebbero elencati in `EXDATE` uno per uno. Un
  `VEVENT` per occorrenza è corretto per **qualunque** maschera, e il prezzo è
  misurato invece che temuto: 1,8 MiB per la scuola intera, **0,6 s**, e il
  file che finisce davvero su un telefono è quello di un docente — **693
  eventi**, 21 ore per 33 settimane.

  ⚠ **Ora locale fluttuante**, senza `TZID` e senza `VTIMEZONE`: le 08:00 di
  una scuola sono le 08:00 dell'orologio alla parete, ed è l'unica forma che
  attraversa il cambio d'ora senza spostare le lezioni per metà anno.

  🔑 **`Estrai` guadagna un dipendente, e con una deroga alla sua regola.**
  `--risorsa` è `per_risorsa`, che ha già i tre versi che ai token non servono
  (parte → classe, raggruppamento → classi, tutte le aule). Ma il perimetro
  qui **restringe davvero l'uscita**, cioè l'unico posto in cui un'estrazione
  tocca ciò che si «conta» — e la ragione è che qui non si conta niente:
  pubblicare è agire, e un calendario non è una diagnosi.

  ⚠ Fuori, dichiarato: la **sostituzione non oscura l'originale**. Per ADR-014
  il sostituto è una riga di `Activity` con un bit solo e compare da sé, ma
  l'originale è annuale e continua a comparire nella stessa settimana — il
  modello non ha la relazione fra i due (`RELATIONCOURSSUBSTITUT` di EDT).

  Le etichette del Fermi sono **nostra scelta di dimensionamento**, come le
  aule: `tempo-e-calendario.md` dichiara che la configurazione oraria di EDT
  non è mai stata osservata in UI. **Quindici mutazioni, quindici esiti
  distinti** — e l'oracolo del pezzo non è il solver ma il **formato**:
  `_srotola` rifà a ritroso la piegatura di RFC 5545, così un test che guarda
  `DTEND` guarda ciò che un telefono leggerebbe. **761 test verdi**, 16 skip.

- **2026-08-28 (i debiti del banco)** — **Tre debiti dichiarati, e due erano
  dichiarati male.** Il piano del modello hard ne aveva lasciati tre in
  eredità; questa passata li ha misurati uno per uno invece di ripararli sulla
  fiducia, e due si sono rivelati diversi da come erano scritti.

  ⛔ **`coverage_mismatch` sul testimone non veniva da dove il banco diceva.**
  L'intestazione di `tests/solver_harness.py` attribuiva il fenomeno ai
  `Service` per (piano, materia) contro `student_units` che attribuisce il
  monte ore alle **parti**. Vero — ed è stato corretto, ogni parte ha ora il
  suo piano di studi — ma **misurato**, spiega un ottavo del fenomeno: su
  dieci semi i finding passano da 122 a 111. Il resto lo fanno le **maschere
  di settimana**, e si vede su `1B`, che di parti non ne ha nessuna e sporca
  ogni seme lo stesso. Il monte ore di un `Service` è settimanale e
  `check_schedule` valuta ogni firma separatamente: un dataset a maschere
  casuali non ha nessun monte ore costante da settimana a settimana.

  🔑 **E la riparazione ovvia è quella sbagliata.** Sommare le durate a
  maschera ignorata — la «vista annuale» — rende il testimone pulito su tutti
  e venti i semi provati, e **raddoppia una coppia Q1/Q2**: 120 minuti contro
  i 60 del piano, cioè segnala come scostamento il quadrimestre, che è la
  forma più comune della scuola italiana. Scritta, misurata, buttata. ⚠ E
  mentre era in piedi la suite era **verde in tutti e 733 i test**: niente
  proteggeva la lettura per settimana. Ora la protegge
  `test_le_ore_di_quadrimestre_non_raddoppiano`, e la semantica è scritta nel
  docstring del checker invece di essere implicita nel modo in cui
  `check_schedule` lo chiama.

  ⚠ **Il debito non era comunque bloccante, ed era la parte peggiore
  dell'errore.** Si diceva «da riparare nella fixture prima di qualunque
  oracolo differenziale a tutto campo». Falso: `coverage_mismatch` è
  `PLACEMENT_INDEPENDENT`, quindi è identico prima e dopo il solve e la
  differenza è vuota per costruzione. Ciò che andava formulato con cura non
  era la fixture ma la **chiave**.

  🔑 **Ed è il secondo debito, ora chiuso: la chiave grossolana di §9.5.**
  L'oracolo confronta su `Finding.key`, che include attività e quantità. Per
  le famiglie che nominano il **secchio** invece del violatore quella chiave
  cambia per il solo fatto che una libera è stata piazzata — misurato con due
  congelate oltre il tetto settimanale di peso didattico e una libera:
  `activities (1,2) → (1,2,3)`, `weight 6 → 9`, quattro settimane, e l'oracolo
  dichiarava rotto un solve impeccabile. Il builder non può rimediare (il
  tetto è inevadibile per costruzione), quindi la riparazione sta
  nell'oracolo: `nuove()` confronta su `(causale, risorsa, settimana)` per
  quelle famiglie, **lette dal registro** (`PLACEMENT_MONOTONE = False`) e non
  elencate a mano, con un test che tiene ferma la corrispondenza.

  ⚠ **L'esenzione è stretta due volte, e la seconda l'ha imposta la
  mutazione.** Vale solo dove la coppia (causale, risorsa, settimana) era
  **già** rotta nella baseline — altrimenti sarebbe un'amnistia per famiglia,
  cioè un oracolo cieco su dieci causali su ventisei. E `activity_unplaced`
  ne resta **fuori**, perché le sue `resources` sono i token dell'attività:
  due attività della stessa classe condividono la chiave grossolana, e uno
  scarto nuovo sparirebbe dentro uno vecchio — cioè l'oracolo diventerebbe
  cieco sull'unica cosa che il solver decide da sé. ⚠ Quell'esclusione era
  **dichiarata e non asserita**: coprirla lasciava verdi tutti e undici i
  test. Ora c'è il caso che la uccide — L1 preferisce scartare un'ora invece
  di due, quindi il solve butta fuori un'attività *diversa* da quella già
  fuori, sulla stessa classe. **Quattro mutazioni, quattro esiti distinti.**

  ⚠ Il prezzo della chiave grossolana è dichiarato: si perde il
  **peggioramento** di una violazione già presente — su `max_gap`, una libera
  piazzata dentro un buco già fuori budget non fa scattare nulla.
  L'alternativa sarebbe confrontare la quantità violata famiglia per famiglia,
  cioè riscrivere fuori dai checker la nozione di «quale numero è quello
  cattivo»: il difetto che questo progetto ha già intercettato due volte.

  🔑 **Terzo debito: `residual_floor` non era codice morto per distrazione, era
  una simmetria che non esiste.** L'intestazione di `domain/solver/residual.py`
  presentava due casi — tetti clampati, minimi no — e il secondo aveva una
  funzione che nessun builder ha mai chiamato, con l'unico riferimento nel suo
  stesso test. La ragione, che il codice già sapeva altrove: **nessun minimo di
  questo modello è additivo**. `MIN_DISTRIBUTION`, `FREE_GUARANTEED` e
  `ARRIVAL_DEPARTURE` contano giorni e mezze giornate, dove una congelata non
  consuma una quota ma toglie gradi di libertà, e la sottrazione non è
  definita: tutti e tre usano `frozen_occupies` o la disgiunzione reificata.
  Rimossa, con l'assenza tenuta ferma da un test perché rimetterla sia una
  decisione. Se un minimo davvero additivo comparirà, è una riga.

  ⚠ **E il gemello di `residual_floor` stava nel banco.** `_causale_risorsa`
  calcolava esattamente la chiave grossolana che l'oracolo ha appena adottato,
  e **nessuno la chiamava**. Prima di cablarla, la misura: strumentando
  `_classifica_nuove` per contare quante violazioni salverebbe, sui dieci semi
  appuntati della suite il conto è **zero**. Non si aggiunge un'esenzione che
  non scatta — è la regola con cui il ramo pigro era stato tolto nell'ondata 5
  — quindi l'helper è rimosso e la misura sta nel docstring. Se un giorno
  scatterà, il banco diventerà rosso e la decisione si prenderà guardando quel
  rosso.

  **738 test verdi**, 16 skip. Il testimone del banco resta sporco su
  `coverage_mismatch`, ora per la ragione giusta e con la riparazione
  quantificata: comprendere le maschere in coppie complementari, cioè
  riscrivere `_make_activities` e spostare il testimone di ogni famiglia e
  ogni seme appuntato. Non fatto, e dichiarato: non serve a niente che sia
  fatto.

- **2026-08-28 (estrai)** — **La voce con più dipendenze in entrata
  dell'inventario esisteva come tabella e non come funzione.** `Extraction` era
  nello schema dal primo giorno e `SolverContext.build` la onorava già, ma
  **niente la popolava**, e `analyze` e `assign_rooms` la ignoravano — cioè la
  risposta a *«rigenera solo il biennio»* era scritta a metà, e la metà
  mancante era tutta quella che l'utente tocca. `domain/extraction.py` più
  `manage.py extract`, e il perimetro sulle due fasi diagnostiche.

  🔑 **La regola che tiene insieme il pezzo: un'estrazione restringe ciò su cui
  si *agisce*, mai ciò che si *conta*.** Fuori dal perimetro le attività
  restano dove sono e continuano a occupare le loro risorse — è la ragione per
  cui il solver le **congela** invece di escluderle, ed è la stessa ragione per
  cui `ScheduleState` si costruisce sempre intero. Filtrare lo stato sarebbe
  stato il difetto silenzioso di questo pezzo: l'occupazione risulterebbe più
  bassa del vero e il motore piazzerebbe sopra a lezioni che esistono, mentre
  ogni test di «l'estrazione restringe» resterebbe verde, perché restringere
  lo farebbe comunque. Nell'analisi il perimetro entra come una **immobilità di
  esecuzione** (`free_candidates(state, selected)`), che è letteralmente la
  semantica che il solver già aveva.

  🔑 **I token dicono chi confligge, non chi appartiene, e i due verbi non
  coincidono.** `activity_tokens` è asimmetrico apposta: la classe intera
  occupa **tutte** le sue parti, la parte **non** occupa la classe. Estrarre
  «le attività della 2A» leggendo i token darebbe le ore a classe intera e
  perderebbe gli sdoppiamenti — cioè proprio quelle che si cercano per prime.
  Da qui `_appartenenze`, che percorre i tre versi che ai token non servono:
  parte → classe, raggruppamento → classi dei membri (ADR-013: non esiste «la»
  classe di un raggruppamento, ci sono tutte), e **tutte** le aule dichiarate
  invece della sola candidata unica. Tre mutazioni, tre rossi distinti: era la
  scorciatoia disponibile, ed è quella sbagliata.

  ⚠ **I rilevatori nominano chi i finding nominano, e un'intera famiglia non
  nomina nessuno.** Gli otto vincoli orari sulla risorsa — D.T.B., giorni
  liberi, massimi — producono finding che nominano la **risorsa** e zero
  attività, ed è corretto: un buco tollerato è una proprietà della *giornata*
  di un docente, non di una delle sue cinque lezioni. `Estrai le attività che
  non rispettano i vincoli` preso alla lettera restituirebbe quindi un insieme
  vuoto su una scuola che viola il D.T.B. ovunque. Il rilevatore **dichiara** i
  finding rimasti senza nome, con la stessa regola di `famiglie_silenziose()`:
  un vincolo che tace e un vincolo innocuo non devono leggersi uguali, e
  `Rilevamento.muto` distingue «vuoto perché sano» da «vuoto perché nessuno era
  attribuibile».

  ⚠ **E `coverage_mismatch` non nominava nessuno affatto**: il checker più
  vecchio del registro confrontava monte ore e servizi senza mai popolare
  `activities`, quindi `Estrai le attività non conformi ai piani di studi`
  sarebbe stato muto per costruzione. Ora nomina le attività che **ci sono** —
  ed è metà del verdetto, dichiarata come tale: con `got < want` il colpevole è
  un'attività che **non esiste**, e nessuna estrazione può nominarla.

  ⛔ **La misura ha smentito la previsione, di un fattore sei.** Restringere
  alla 1A doveva costare un undicesimo (26 attività su 284) e costa il **62%**:
  `0,263s` contro `0,422s`. La decomposizione dice perché — `~0,25s` di
  `ScheduleState.build`, che il perimetro non tocca perché lo stato si
  costruisce sempre intero, più `~0,6ms` per attività esaminata. Il perimetro
  taglia il 90% della parte **variabile** e il 38% del totale. 🔑 Il che vale
  più del numero: sul Fermi la classifica dei vincoli è **dominata dalla
  costruzione dello stato**, non dal conteggio delle attività — ed è la
  conferma dal verso opposto che «restringe l'azione, mai il conteggio» non è
  solo una regola di correttezza, è anche il modello di costo. La frase è stata
  riscritta nel test invece che nel changelog.

  ⚠ **Un test non poteva fallire, e l'ha detto la mutazione.**
  `apply_rooms_non_tocca_chi_sta_fuori` era verde sotto tutte e undici le
  mutazioni: chi stava fuori teneva la sua aula anche **senza** perimetro,
  perché nessuno gliela contendeva. Riscritto su un'istanza dove il perimetro è
  l'unica cosa che la salva — l'aula è diventata indisponibile dopo
  l'assegnazione a mano, quindi come *richiesta* rinuncerebbe, e `apply_rooms`
  cancella l'aula di chi rinuncia — e ora una dodicesima mutazione lo uccide.
  **Quattordici mutazioni, quattordici esiti distinti.**

  ⚠ **E una nota di metodo, pagata:** lo script di mutazione ripristinava con
  `git checkout -- domain/`, che su un pezzo con file **non tracciati** e
  modifiche **non committate** fa il contrario di ciò che serve — lascia il file
  nuovo mutato e butta via il lavoro degli altri. Da qui in avanti le mutazioni
  si ripristinano da una **copia**, mai dall'indice.

  I numeri sul Fermi, `--estrazione biennio` (104 attività su 284): `solve`
  passa da **8426 a 3243 variabili** e da 1086 a 800 constraint, 0,53 s;
  `assign_rooms` da 92 a **32 richieste d'aula**, 90 variabili contro 258.
  Nessuna attività fuori dal biennio si muove, che è garantito per costruzione
  — il loro dominio è un singoletto. **733 test verdi**, 16 skip.

  Restano fuori, dichiarati: sei delle dodici voci del menu `Estrai` di EDT,
  ognuna per una ragione scritta accanto al registro — `non costanti durante
  l'anno`, `sezionate asincrone` e `spostate` riguardano la fascia variabile e
  il sezionamento (ADR-010, fuori scope); `raggruppamenti ad alunni variabili` è
  la formazione classi, che non abbiamo; `complesse` e `di compresenza` sono
  filtri di forma, non problemi. E gli stati `Scartate` e `In attesa`, che sono
  sfumature di «non piazzata» che il modello non distingue.

- **2026-08-28 (piazza e sistema)** — **L'ultima voce strutturale ✅ di
  scope-v1 rimasta assente è dentro**, e con lei la **condizione 1** delle tre
  «da non perdere» di ADR-015: *«qual è l'insieme minimo di attività da
  spostare perché A stia qui?»*. È lo stesso motore del risolutore passo-passo
  escluso da v1, e averlo tiene quella porta aperta invece di richiederne la
  riscrittura. `domain/solver/place_and_fix.py` più `manage.py place_and_fix`.

  🔑 **Il pezzo costa poco perché la catena lessicografica lo era già.**
  Imporre una cella è un vincolo hard — `pinned` su `build_model` —; «disturbare
  il meno possibile» è **L4**, la stabilità, scritta per ADR-010 e per il
  secondo quadrimestre da non stravolgere. L'ordine della catena era già
  quello giusto e non si tocca: **non scartare** viene prima di **non
  spostare**, perché ricollocare è meno grave che buttare fuori. Il minimo di
  `moved` è quindi lessicografico *dopo* L1-L3, ed è la nozione corretta, non
  un'approssimazione. Un test lo prova invece di dichiararlo.

  🔑 **E la diagnosi del «perché no» è la `blame` scritta poche ore prima.**
  Quando la cella non è nel dominio dell'attività, `trial_placements` sa già
  *quali* causali la escludono: il rifiuto è una frase del catalogo con dentro
  il nome del docente, non un `INFEASIBLE`. Le due risposte restano
  **distinte**, ed è il punto: «la cella è vietata all'attività dai suoi
  stessi vincoli» (nessuno spostamento aiuterebbe — una dimostrazione) e
  «l'orario non si ricompone attorno» (la cella andrebbe bene, ma chi c'è non
  ha dove andare — il caso in cui servirebbe il risolutore passo-passo).

  ⚠ **La diagnosi va filtrata alle sole causali dei pre-filtri, o incolpa chi
  si potrebbe spostare.** `trial_placements` valuta tutti i checker contro lo
  stato corrente, quindi sulla cella contesa vede anche l'occupazione da parte
  di chi ci sta — che è precisamente ciò che `Piazza e sistema` sposterebbe.
  I builder che implementano `restrict()` sono **due**, griglia e
  indisponibilità, e un test lo tiene fermo: se ne comparisse un terzo, la
  diagnosi diventerebbe muta sul suo caso.

  ⚠ **`moved` da solo mentirebbe, e serve `dropped`.** Un'attività che era
  piazzata e che il modello ha dovuto **scartare** non si è spostata: ha perso
  il posto. «Zero spostamenti» su un orario che ha perso un'ora sarebbe il
  rendiconto peggiore possibile. Il buco l'ha trovato la mutazione: nessuno
  dei test iniziali forzava uno scarto, quindi `dropped` era affermato solo da
  un `== ()` che una costante vuota soddisfa.

  ⚠ **Resta fuori, dichiarata: «Ignora i vincoli dell'attività selezionata».**
  In EDT è una casella; da noi non è separabile per attività, perché i vincoli
  di A non sono *di* A — una riga di materia sulla classe lega A alle sue
  sorelle, e spegnerli vorrebbe dire attraversare ventisei builder. Una
  versione parziale (riaprire i soli pre-filtri) lascerebbe forzare oltre
  un'indisponibilità rossa ma non oltre un'incompatibilità di materia: un
  modello mentale incoerente, peggiore dell'assenza.

  **Otto mutazioni, otto esiti distinti**, e l'oracolo del file è verificato a
  parte — spegnendo `OccupationBuilder` diventa rosso, quindi può fallire.

  🔑 **La misura, e stavolta il Fermi la può dare.** Su un orario **pieno**
  (284 attività piazzate, zero scarti) forzare una lezione dove ne sta
  un'altra della stessa classe costa **uno** spostamento: l'insieme minimo è
  uno scambio. ⚠ Il costo è ~4 s contro il secondo scarso del `solve` che ha
  generato l'orario, e la differenza è **L4**, che prima non aveva niente da
  conservare e ora confronta 284 collocazioni — è il prezzo di disturbare
  poco, non un difetto. Come sempre sul Fermi la copertura resta fuori: senza
  righe di vincolo la ricomposizione incontra la sola occupazione.
  **707 test verdi**, 16 skip.

- **2026-08-28 (quale vincolo allento)** — **La seconda delle due lacune di
  EDT è colmata: `domain/analysis/blame.py`.** `scope-v1.md` le chiama «la
  nostra occasione» — il riepilogo navigabile (già in `analyze`) e
  **l'ordinamento dei vincoli per numero di fallimenti causati**, «il ponte
  mancante fra *il calcolo è fallito* e *quale vincolo allento*». EDT elenca
  cosa si **può** alleggerire e non dice mai cosa **serve** alleggerire.

  🔑 **Il pezzo è economico perché il numero esisteva già e veniva buttato
  via.** `admissible_starts` prova ogni cella e calcola l'insieme delle
  violazioni nuove — cioè *perché* quella cella è esclusa — e poi ne guardava
  solo se fosse vuoto. Ora c'è `trial_placements`, che restituisce le causali
  cella per cella; `admissible_starts` ne è il filtro, e la classifica le
  legge. **Zero giri di checker in più.**

  🔑 **L'unità di misura non è la riga di vincolo, ed è una decisione.** Un
  `Finding` non porta il pk della riga che l'ha generato, e
  `ResourceTimeConstraint` non ha unicità su `(resource, type)`: risalire alla
  riga sarebbe una deduzione. La classifica è quindi sulla coppia **(causale,
  risorsa)** — la stessa chiave grossolana che il progetto usa già altrove, ed
  esattamente ciò che l'utente va a toccare («il D.T.B. del prof. Rossi»).
  Dove due righe condividono la coppia sono indistinguibili dall'orario, e
  nominarle insieme è il verdetto corretto.

  🔑 **Il numero che conta è `activities_freed`, non le celle escluse.** Un
  dominio si svuota per **congiunzione** — la cella 1 la esclude un vincolo,
  la cella 2 un altro — quindi «questo vincolo esclude quattrocento celle» non
  implica che allentarlo serva. `activities_freed` conta le attività a dominio
  vuoto per cui esiste una cella la cui **unica** causale è questa: *se
  allento questo, quante attività tornano ad avere dove andare?* Ordinare per
  pressione metterebbe in cima, su ogni scuola vera, l'indisponibilità più
  larga — che è quasi sempre quella che non si può togliere. Un test tiene
  fermo l'ordine: sedici celle escluse senza chiudere una porta stanno sotto a
  cinque che ne chiudono una.

  ⚠ **Le famiglie non monotone non compaiono, ed è una rinuncia dichiarata dal
  comando, non solo dal docstring.** Il criterio «chiave nuova ⇒ cella
  esclusa» è falso per i checker `PLACEMENT_MONOTONE = False` — là piazzare
  può *riparare* — quindi ogni cella produrrebbe una chiave nuova e quelle
  famiglie starebbero in cima a **qualunque** classifica su **qualunque**
  dataset, per un artefatto del criterio. Si passa `relaxed=True` come la fase
  5: si perde **richiamo**, mai precisione. Fra le silenziose c'è il D.T.B.,
  che è uno dei vincoli che le scuole allentano più spesso, e per questo
  `famiglie_silenziose()` le legge **dal registro** invece di elencarle, e
  `analyze` le stampa: un vincolo che tace e un vincolo innocuo si leggono
  uguali.

  ⚠ **Le firme di settimana si uniscono, non si sommano.** Un'attività va
  collocata in **una** cella valida in **tutte** le settimane in cui è attiva:
  le causali di una stessa cella si uniscono fra le firme, e la cella è
  ammissibile solo se l'unione è vuota. Sommare le firme raddoppierebbe ogni
  numero dove le firme sono trentacinque.

  ⚠ **E la mutazione ha trovato un test vacuo, nella forma di sempre.** Sei
  mutazioni, e la terza — spegnere il rilassamento — **non rendeva rosso
  niente**: le due attività che dovevano creare il buco del D.T.B. erano
  *mobili*, quindi `free_candidates` le spiazzava e il buco spariva prima di
  essere misurato. È la trappola §4.1 del violatore di Hall, questa volta
  dentro il caso di prova. Congelate: sei mutazioni, **sei esiti distinti** —
  cinque con un rosso solo, e spegnere il rilassamento ne fa due, perché
  trascina anche la misura sul Fermi.

  Nello stesso giro `_split` esce da `hall.py` e diventa
  `domain_size.free_candidates`: i due lettori di `trial_placements` hanno
  bisogno della **stessa** preparazione dello stato, e la §4.1 è precisamente
  il tipo di precauzione che si perde in una copia.

  Fermi: **0,25 s** su 284 attività, tre righe — le tre giornate intere di
  `vincoli-attesi.md` — zero impiazzabili, zero liberabili. ⚠ Come sempre su
  questo dataset la misura è del **costo**, mai della **copertura**: senza
  righe di vincolo le uniche causali possibili sono le indisponibilità. E il
  costo è lineare nelle firme, quindi il numero da portarsi dietro è «~0,25 s
  per firma», non un assoluto. **693 test verdi**, 16 skip.

- **2026-08-28 (l'ordine d'inserimento)** — **Due artefatti dichiarati erano
  tre, e il terzo rompeva l'oracolo.** I due punti aperti da luglio —
  «cosa significa cambio di sede quando due sedi coesistono nella stessa
  fascia» e «il tie-break di `_placed_of`» — erano la stessa forma: un
  `Finding` la cui identità dipendeva dall'**ordine d'inserimento** invece che
  dall'orario. `ScheduleState.occupancy` è un `defaultdict(list)` e
  `state.placed` un `dict`: entrambi conservano l'ordine del queryset
  `Activity`, che è un fatto del database e non un fatto dell'orario.
  Le due decisioni sono in [ADR-019](decisioni.md).

  🔑 **La decisione sulle sedi: dentro una fascia non si viaggia.** Una fascia
  contribuisce l'**insieme** delle sue sedi, e un cambio è una transizione fra
  due fasce consecutive i cui insiemi differiscono — sedi diverse simultanee
  valgono **zero** cambi. L'argomento che la sceglie fra le due candidate:
  essere in due posti insieme è *impossibile*, e
  `structural:site_transition` continua a dirlo (`gap_slots = -1`, minore di
  qualunque soglia), ma non è un **viaggio**. Le due domande sono diverse —
  «è fisicamente possibile?» contro «quante volte si è spostato?» — e ognuna
  tiene la sua risposta. A capienza 1, cioè ovunque salvo l'aula col `Numero
  di aule` di EDT, la nuova regola coincide riga per riga con la vecchia.

  ⚠ **E gli artefatti erano tre: `SiteTransitionChecker` aveva lo stesso, e
  non era in nessun elenco.** Anche lui appiattiva `occupancy` in una
  sequenza: con `[A@0, B@0, A@1]` le coppie adiacenti sono `(A,B)` e `(B,A)`
  — due violazioni — mentre con `[B@0, A@0, A@1]` sono `(B,A)` e `(A,A)`, e la
  seconda sparisce. Lo stesso orario, due verdetti. Ora le coppie si enumerano
  dagli insiemi, e il checker si **allinea al proprio builder**, che quelle
  coppie le postava già tutte.

  ⛔ **Il quarto sito dell'artefatto era nel solver, e non era cosmetico.**
  `_frozen_site_changes` calcola il residuo di ADR-018 — quanti cambi le sole
  congelate hanno già contratto, cioè il pavimento sotto cui il tetto non
  scende — e lo calcolava **appiattendo** `by_cell`. Due congelate di sede
  diversa sulla stessa fascia gli valevano un cambio che per il checker non
  esiste: il tetto clampato saliva da `max(0, 0)` a `max(0, 1)` e il solver si
  ritrovava in tasca un cambio che il checker non gli perdona. **Misurato**:
  baseline pulita, `solve` risponde `OPTIMAL`, e la soluzione applicata porta
  un `max_site_changes` `HARD` **nuovo** — l'oracolo differenziale rotto.
  Non l'ha trovato una rilettura: l'ha trovato l'obbligo di far contare al
  builder come conta il checker, una volta che il checker aveva finalmente una
  regola da seguire.

  🔑 **Il tie-break si rompe con l'identità dell'attività**, `(day,
  start_slot, activity_id)`. È arbitraria — fra due occorrenze davvero
  intercambiabili nessuna proprietà dell'orario le distingue — ma **stabile e
  riproducibile**, che è precisamente ciò che l'ordine di un queryset senza
  `order_by` non promette. ⚠ L'alternativa di nominarle **tutte** è stata
  considerata e scartata, non dimenticata: sarebbe funzione della sola forma
  dell'orario e per `WEEKLY_ORDER` funzionerebbe, ma non generalizza alle
  famiglie a coppie consecutive (`IMPOSED_SUCCESSION` con A = B), dove il
  pareggio sposta la coppia invece di allargare un secchio. Una regola sola
  per tutti i lettori di `_placed_of` vale più di due contratti di finding.
  ⚠ La **deriva d'identità sotto piazzamento** resta, e resta giusta: è
  `PLACEMENT_MONOTONE = False`, una proprietà del checker, non un artefatto.

  ⚠ **Nessuno dei quattro tocca il Fermi**, che non ha né sedi né righe
  d'ordine con pareggi: sono difetti che solo un test costruito apposta poteva
  esibire — la forma di sempre, una proprietà del dataset scambiata per una
  proprietà del codice. `tests/test_analysis_ordine_inserimento.py` costruisce
  lo stesso orario due volte e pretende la stessa risposta; **quattro
  mutazioni, quattro rossi distinti**, uno per correzione e nessuno per caso.

  🔑 **E che nessun test esistente si sia mosso è la misura, non un sollievo.**
  Suite da 674 a **680 verdi** — i sei nuovi e nient'altro — e il Fermi
  invariato byte per byte (8426 variabili, 1116 constraint). È la prova che
  «a capienza 1 la nuova regola coincide riga per riga con la vecchia» è un
  fatto e non una speranza: se avesse cambiato qualcosa altrove, 674 test
  l'avrebbero detto.

- **2026-08-28 (assegnazione delle aule)** — **L'ultimo pezzo dichiarato fuori
  è dentro, e non è un vincolo in più: è una seconda fase.**
  `domain/solver/rooms.py` più `manage.py assign_rooms`, sei task
  ([spec](superpowers/specs/2026-08-27-assegnazione-aule-design.md),
  [piano](superpowers/plans/2026-08-27-assegnazione-aule.md)). Assegnare
  le aule *dopo* aver piazzato non è una scorciatoia: è la forma del prodotto,
  che ha per le aule criteri propri (`TypeChoixOptimSalle`), un ottimizzatore
  dedicato (`FicheEdt_OptimiseurSalles`) e una `ripartizione delle aule`
  distinta dal calcolo.

  🔑 **I vincoli veri sono tre più la capienza, ed è meno di quanto sembri.**
  La finestra `Aule disponibili` dichiara `Sedi distaccate`, `Indisponibilità
  opzionali`, `Indisponibilità` e nient'altro: **capienza in alunni, categoria
  e tipologie non vincolano** — verificato in UI il 2026-07-26, e la tentazione
  di aggiungerle era esattamente ciò che il piano vietava. Sopra ci sono due
  livelli, nella forma della catena della prima fase: L1 i **minuti** senza
  aula (un laboratorio da 3h che resta fuori fa più danno di uno da 1h), L2 i
  cambi rispetto alla ripartizione precedente — che è il criterio che EDT
  dichiara alla lettera, *«se possibile mantenendo le assegnazioni della
  precedente ripartizione»*. L'ordine è provato da un test: conservare l'aula
  di prima non vale una rinuncia.

  ⚠ **E la seconda fase ha un prezzo, che il Fermi ha misurato invece di
  prevederlo.** Il piazzamento è cieco alle aule con più di una candidata, e
  §6 dichiara fuori scope il ritorno indietro: la fase 1 può accatastare su una
  cella più richieste di quante aule esistano, e la fase 2 non ha altra
  risposta che **rinunciare**. Sul Fermi: 92 richieste, **84 assegnate, 8
  rinunce**, 39 celle contese, fino a 5 richieste su una cella; 258 variabili,
  135 constraint, 0,44 s. Non è un difetto del modello — è la conseguenza
  dichiarata di assegnare le aule dopo — ma è la prima volta che il progetto
  porta un numero invece di un «si potrebbe».

  🔑 **Il dataset è stato scelto contro la propria comodità, ed è il punto del
  pezzo.** Il Fermi non ha aule (`NBSALLES = 0`), quindi il Task 6 le inventa;
  la versione ovvia — una materia, una sua aula — dà `OPTIMAL` con zero
  rinunce e sembra un successo. **Non lo è**: a candidata unica l'aula entra
  già nei token del piazzamento (`_activity_tokens`), quindi zero celle
  contese, la capienza non morde mai, e la seconda fase si limita a confermare
  una scelta già fatta — una misura su un problema **senza gradi di libertà**,
  cioè il verde incapace di fallire che questo repository ha già pagato otto
  volte. Da qui `LAB-INF` **condiviso** fra FIS, SCI e DIS: è l'unica riga che
  mette in concorrenza materie e docenti diversi, e le 8 rinunce sono il prezzo
  di avere un dataset che può dire di no.

  ⚠ **E l'arricchimento ha trovato un difetto vero, in codice scritto il giorno
  prima.** `structural:room_assignment` nomina le attività **piazzate** che
  chiedono un'aula senza averla: in `admissible_starts` la baseline è lo stato
  con l'attività sospesa, dove il finding non c'è, quindi ogni cella di prova
  lo fa comparire e il dominio si svuota **ovunque**. Misurato: **92 falsi
  positivi** sul Fermi con le aule — uno per ogni attività che ne chiede una —
  mentre `solve` risponde `OPTIMAL` con zero scarti. È il difetto che la fase 5
  non ha il diritto di produrre, mandare l'utente a smontare vincoli sani, già
  pagato nella review del violatore di Hall; qui in una forma **nuova**: non
  monotono **per il verso opposto**. Nelle sei famiglie note piazzare *ripara*
  la violazione, qui piazzare la **crea**, perché la richiesta d'aula la
  soddisfa la seconda fase e non il piazzamento. Marcato
  `PLACEMENT_MONOTONE = False`; la mutazione rende rossi due test indipendenti.
  ⚠ **Nessuna review l'avrebbe trovato**: il Fermi senza aule non ha
  un'attività che ne chieda una, quindi il checker girava a vuoto sull'unico
  dataset di scala. È la forma di sempre — una proprietà del dataset scambiata
  per una proprietà del codice — e stavolta a ventiquattr'ore di distanza.

  Nello stesso giro `manage.py solve` smette di elencare `room_unassigned` fra
  le «violazioni residue», per la ragione con cui già escludeva
  `activity_unplaced`: descrive un orario **incompleto**, non illegale.

  Il banco a testimone della fase (`tests/rooms_harness.py`) genera **prima**
  un'assegnazione valida e solo dopo chiede di ricostruirla; con la capienza
  spenta **9 test su 20** diventano rossi, quindi il banco esercita davvero ciò
  che sorveglia. Suite: **674 test verdi**, 16 skip.

  Restano fuori, dichiarati: `TypeIncompatibiliteSalle` (11 valori) e
  `TypeChoixOptimSalle`, di cui conosciamo il nome e non i valori — la nostra
  fase sceglie una candidata qualunque fra quelle legali, con la sola
  preferenza per la ripartizione precedente.

- **2026-08-27 (separazione per popolazione)** — **EDT non cerca mai un ottimo
  congiunto, e adesso nemmeno noi.** I comandi del prodotto sono due —
  `Ottimizza gli orari dei docenti` / `... delle classi`, `TypeTypeOptim =
  ttoProfs, ttoClasses` — e chi lancia dichiara **quanto è disposto a
  peggiorare l'altra popolazione**. `Arbitrato(popolazione, tolleranza)`
  ([spec](superpowers/specs/2026-08-27-separazione-popolazione-design.md)):
  i criteri della popolazione sacrificata escono dalla catena e diventano
  `valore <= base + tolleranza`, un vincolo hard di non-regressione — mai un
  peso in una somma, che è la frase con cui `motore-risoluzione.md` descrive il
  meccanismo.

  🔑 **Non basta riordinare i `rank`**, ed è il punto del pezzo. Con i soli
  `rank` i criteri dell'altra popolazione restano **livelli**: si ottimizzano
  comunque, e costano. L'arbitrato li declassa a tetti. Misurato in A/B sul
  Fermi: la stessa riga come tetto costa i suoi ~640 variabili di definizione e
  **zero** tempo di ricerca (31,6 s); come livello si prende una fetta intera
  del limite e chiude senza dimostrare l'ottimo (41,9 s). Il risparmio è
  limitato dal `--limite`, e senza limite non è limitato da niente.

  🔑 **La base non è una seconda definizione del criterio: è la stessa
  funzione.** Un criterio posta **solo definizioni** — l'invariante scritto in
  testa a `quality.py` quando il pezzo precedente è nato — quindi lo si può
  valutare su un orario *dato* chiamandolo con i letterali di cella sostituiti
  dalle costanti `0`/`1` di quell'orario: ogni booleano derivato è determinato
  per propagazione, e un `Solve` istantaneo restituisce il numero.
  L'alternativa era riscrivere i cinque criteri in Python su `ScheduleState`,
  cioè il difetto che questo progetto ha già intercettato due volte. Un test
  tiene ferme le due strade: la base dev'essere il numero che il **livello** dà
  sullo stesso orario.

  ⚠ **E il pezzo ha trovato che i criteri di qualità non funzionavano su
  nessun orario già scritto.** L'arbitrato ha bisogno di un orario di partenza,
  e un orario di partenza mette in catena **L4**: la stabilità arriva a zero
  conservando tutto, il suo fissaggio inchioda ogni cella, e da lì in giù ogni
  livello di qualità è **inerte**. Sul Fermi con l'orario già scritto la catena
  unica riporta `gaps_teachers 420`, `isolated_teachers 20`,
  `regularity_classes 265` **in 0,06 s per livello** — non sono risultati, sono
  i valori dell'orario che c'era, misurati e non migliorati. Un livello che
  chiude in sessanta millisecondi su 284 attività non sta ottimizzando niente.
  ⚠ Il difetto **non è di questo pezzo**: c'era dal giorno in cui i criteri
  sono nati, e non si vedeva perché **il Fermi non ha piazzamenti di suo**,
  quindi la misura che li aveva dichiarati funzionanti girava dove L4 non
  esiste. È la forma di sempre — una proprietà del dataset scambiata per una
  proprietà del codice — stavolta a ventiquattr'ore di distanza.
  **La correzione è d'ordine, e la decisione viene da EDT**: là i comandi sono
  due e il conflitto non si pone, perché `Ottimizza` rimescola un orario che
  c'è già e rimescolare *è* lo scopo. Qui il comando è uno, quindi la corsa
  deve dichiararsi: senza arbitrato vince la stabilità (ADR-010, il secondo
  quadrimestre da non stravolgere), con l'arbitrato la stabilità scivola in
  coda e diventa lo **spareggio**. Sul Fermi i buchi dei docenti passano da 420
  a **0**, e il prezzo è dichiarato: **231 attività spostate su 284**.

  ⚠ **L'istanza dei test è stata costruita dopo aver misurato che le ovvie non
  funzionano.** Due docenti per due classi su una griglia 2×2 sembra la
  tensione canonica e **non lo è**: due classi diverse possono occupare la
  stessa cella, quindi comprimere i docenti comprime anche le classi e i due
  ottimi coincidono — tolleranza 0 e tolleranza 2 davano la stessa risposta,
  cioè un test incapace di distinguere. La tensione vera è fra `regularity` (la
  materia sempre alla stessa fascia, quindi su giorni diversi) e
  `free_half_days` (tutto lo stesso giorno, quindi su fasce diverse): l'una a 1
  costringe l'altra a 2.

  **Nove mutazioni, nove esiti distinti.** ⚠ E due sono servite dove una
  sembrava bastare: sfasare il **tetto** non tocca il test che confronta la
  base col livello, perché quel test guarda la base. Ci vuole la mutazione
  sulla **fonte** per farlo diventare rosso.

  ⚠ Sul Fermi il tetto **non morde** — buchi e ore isolate arrivano a zero
  comunque — quindi tolleranza 0 e 10 danno lo stesso orario. Come sempre su
  questo dataset la misura è del **costo**, mai della **copertura**.

  Dichiarato fuori, e come decisione: il valore **raggiunto** dal criterio
  sacrificato. Il rendiconto dice base e tetto, non dove si è atterrati;
  leggerlo vorrebbe `solve_chain` che restituisce il solver, o una seconda
  valutazione con le righe ripescate e riappaiate per nome — parecchia coppia
  incidentale per un numero solo. **612 test verdi**, 16 skip.

- **2026-08-27 (criteri di qualità)** — **La catena impara a distinguere due
  orari legali.** Sei ondate
  ([spec](superpowers/specs/2026-08-27-criteri-di-qualita-design.md)). I
  quattro livelli esistenti misurano tutti un **fallimento** — ore scartate,
  attività scartate, violazioni nuove, spostamenti — quindi un orario che
  piazza tutto senza violare nulla era indistinguibile da un altro che fa lo
  stesso lasciando a un docente quattro buchi al giorno. Ora ci sono i livelli
  che li separano: `domain/solver/quality.py` (il registro) e `criteria.py` (le
  cinque traduzioni).

  ⚠ **In EDT i meccanismi sono due, e confonderli era l'errore di partenza.**
  `Ordinamento dei criteri` è la lista degli **undici** criteri di
  *piazzamento*, riordinabile fra «considerati» e «ignorati»; `Ottimizzazione
  degli orari` è una fase **separata**, con **tre** slot ordinati **per
  popolazione** su cinque valori. Implementati i quattro valori
  dell'ottimizzazione — buchi, attività isolate, mezze giornate libere,
  equilibrio didattico — più `Rispetta le preferenze`, che in EDT è
  l'undicesimo e **ultimo** criterio di piazzamento, ed è il pennello verde che
  il pre-filtro lasciava passare rimandando qui per nome.

  🔑 **Il pezzo è economico perché le quantità esistono già.** Quasi tutte sono
  calcolate da un checker di `domain/analysis`, dove servono a essere
  confrontate con un tetto: qui la stessa quantità si **minimizza**. I buchi
  sono la formula di `MaxGapChecker` senza il D.T.B., e un test lo tiene fermo
  facendo guardare **lo stesso orario** al livello e al checker — devono dire
  lo stesso numero, o il criterio misura qualcos'altro.

  🔑 **E una definizione di EDT collassa.** *«Attività isolata in una mezza
  giornata **e** di durata inferiore a due fasce orarie»* sono due condizioni
  che diventano una: **la mezza giornata ha esattamente una fascia occupata**.
  Sola e lunga due dà 2; due ore singole danno 2 e nessuna è isolata. Non serve
  guardare né la durata né l'identità dell'attività.

  ⚠ **La traduzione italiana di un criterio dice un'altra cosa**, ed era già
  scritto nei documenti: `Equilibrio didattico` traduce `Régularité des cours`,
  ma l'enum è `tcoMemesHoraires` — *stessi orari*. Il senso è che la materia
  ricada sempre nella stessa fascia, non l'equilibrio del carico. Tradurre
  l'etichetta alla lettera avrebbe prodotto un criterio diverso da quello del
  prodotto.

  **L'ordine è un dato, non codice** (`QualityCriterion`, migrazione `0010`),
  perché è il punto dichiarato del meccanismo: *«"Criteri considerati /
  ignorati" è una UI onesta»*. Tabella vuota ⇒ la catena di prima, e un
  criterio dell'enum che nessuna traduzione legge è un criterio **ignorato**,
  non un errore.

  ⚠ **Il costo cambia una raccomandazione operativa.** Fermi, cinque criteri:
  **senza limite di tempo il calcolo non è tornato in nove minuti**; con
  `--limite 15` finisce in **39,5 s**, e due livelli su sei chiudono con
  l'ottimo **non dimostrato** — `regularity` e `free_half_days`, i due che
  aprono più simmetrie. La catena resta corretta (un livello che scade fissa
  l'ultimo valore trovato), ma il limite per livello smette di essere una
  precauzione. Dichiarato nel docstring di `manage.py solve`.

  ⚠ **Due difetti trovati nei test, non nel codice, e sono la stessa forma —
  il primo l'ha trovato la misura sul Fermi, non una rilettura.** Le dimensioni
  del modello non si muovevano di un bit con cinque criteri accesi, perché
  `_dimensioni` costruiva la sola `build_model` mentre i livelli di qualità
  nascono dentro `livelli()`: un'asserzione **incapace di fallire**. E
  correggendola è emerso il secondo: il test misurava **due volte lo stesso
  stato**, perché per la proprietà «tabella vuota» non esiste una riga da
  aggiungere in mezzo. Ora il confronto è contro il modello **nudo** con una
  differenza attesa esatta, ed è l'unica forma in cui la mutazione «una
  variabile di troppo» diventa rossa.

  ⚠ **Una previsione sbagliata, corretta dai numeri e non dal ragionamento**:
  un'ora isolata con `population=ALL` vale **due**, non una — è isolata per il
  docente e per la classe. Non è un doppio conteggio per distrazione: il
  contatore `A.iso.` di EDT è dichiarato «per docente/classe/**gruppo**». Due
  test attendevano 1 e sono stati corretti, non il codice.

  **Nove mutazioni, nove esiti distinti**: ciascun criterio spento rende rossi
  i suoi test e nessun altro; «nessun livello di qualità» ne rende rossi
  quindici su diciassette e lascia verdi esattamente i due conservativi, che
  devono sopravvivergli. Suite: **599 test verdi**, 16 skip.

  Resta fuori, dichiarato: la **separazione per popolazione** e la **perdita di
  qualità tollerata** — EDT ottimizza docenti *oppure* classi e dichiara quanto
  è disposto a peggiorare l'altra. Il fissaggio della catena è già metà del
  lavoro (`<= valore` diventa `<= valore + tolleranza`), ma *quale* popolazione
  ottimizzare è un parametro di lancio: va progettato col comando, non con
  l'obiettivo.

- **2026-08-27 (audit delle quote)** — **Dodici call site di alleggerimento,
  misurati uno per uno: nessun difetto di comportamento, due di
  documentazione.** È il seguito diretto della review. Là erano emersi un
  errore di unità (`MAX_PRESENCE`) e un'attribuzione decisa dall'ordine dei pk
  (`risorsa_di`), entrambi su call site che nessun test sapeva distinguere da
  quelli sani; gli altri dieci erano stati controllati **per lettura**, non per
  misura. Ora lo sono.

  🔑 **Il risultato positivo va detto per primo: ogni margine è la grandezza
  che dichiara, e ogni granularità è quella della riga di EDT.** Sonda su tutte
  le famiglie prima di scrivere un solo assert: il tetto delle mezze giornate
  concede mezze giornate, quello del peso concede pesi, quello delle sedi
  concede cambi, quello delle materie minuti — e nessuno concede il decuplo.

  ⚠ **Ma i test che c'erano non potevano dirlo.** La forma `_senza_poi_con` —
  «senza quota INFEASIBLE, con quota OPTIMAL» — prova che la quota è
  **collegata**, mai *quanto* concede né *quante volte*: un margine
  moltiplicato per mille e un letterale issato fuori dal ciclo la passano
  entrambi indisturbati. È precisamente la vacuità che aveva lasciato passare
  l'errore di unità di `MAX_PRESENCE`. **Undici test nuovi** la chiudono, uno
  per la grandezza e uno per la granularità, famiglia per famiglia.

  **Undici mutazioni, undici esiti distinti, esattamente un rosso ciascuna** —
  il margine di una famiglia decuplicato, oppure un letterale solo per
  (famiglia, risorsa) al posto del tag. Nessun test passa per caso, nessuno è
  ridondante con un altro.

  ⚠ **I due difetti sono nella documentazione, e sono la forma di sempre.** La
  tabella delle unità di `RelaxationQuota` **non nominava `ARRIVAL_DEPARTURE`**,
  che è una famiglia a margine con un suo test dal giorno in cui è nata; e dava
  `FREE_GUARANTEED` in *mezze giornate* mentre lo stesso numero si sottrae 1:1
  anche dalla soglia dei **giorni** — misurato: con `free_days = 2` un margine
  di 1 lascia la soglia a 1, non a 0.

  ⚠ E quella divergenza **resta, dichiarata invece che corretta**. Non è il
  gemello dell'errore di `MAX_PRESENCE`: là un margine in minuti finiva su un
  tetto in giorni e lo **spegneva**; qui le due soglie contano cose disgiunte
  (un giorno del tutto libero contribuisce zero mezze giornate libere, perché
  il checker le conta solo sui giorni che lavorano), quindi non esiste una
  conversione da applicare, e una riga che non alleggerisse `free_days`
  resterebbe inerte proprio sul vincolo che le scuole scrivono più spesso. La
  tabella porta ora anche la **granularità** accanto all'unità, che è la metà
  che non era scritta da nessuna parte.

  ⚠ **E una sonda ha misurato sé stessa invece del codice**, che vale
  registrare: tre attività su sedi A/B/A dovevano costare due cambi, e il
  modello rispondeva `OPTIMAL` con margine 1. Non era il builder — il solver
  **riordina**, e A/A/B costa un cambio solo. Con tre sedi distinte l'ordine
  non aiuta più e la misura torna quella voluta. Un caso di prova che il solver
  può aggirare non misura il vincolo: misura l'istanza.

  Nessun builder toccato, quindi il Fermi è invariato per costruzione (8426
  variabili, 1086 constraint, tenuti fermi dalla suite). **582 test verdi**, 16
  skip.

- **2026-08-27 (review)** — **La review del pezzo 3, applicata: un errore di
  unità che spegneva un vincolo, e un'attribuzione decisa dall'ordine dei pk.**
  Sei rilievi su alleggerimenti e catena lessicografica, tutti chiusi. Il
  risultato positivo va detto per primo: **nessun builder più largo del
  checker**, nessuna traduzione sbagliata. I difetti stanno nelle unità di
  misura, nell'attribuzione delle quote e nella forma delle API.

  🔑 **Il margine di `MAX_PRESENCE` è in *ore*, e veniva sommato anche al tetto
  dei *giorni*.** Con «margine 60» un tetto di «al massimo 1 giornata» diventava
  61: il vincolo si spegneva, in silenzio. La fonte lo dice per nome
  (`docs/edt/estratti/motore-punti-aperti.md`: *«MaxPresentielProf … | ore»*),
  e il tetto dei giorni non è alleggeribile con quella grandezza.
  ⚠ **Il test che c'era non poteva vederlo**: `mini_school(days=1)` contro un
  tetto `days: 5` rende quel ramo irraggiungibile. È la forma consueta di
  vacuità di questo progetto — un verde incapace di fallire — stavolta su una
  famiglia scritta il giorno prima.

  ⚠ **E lo stesso margine si consumava una volta per l'intera settimana.** Un
  letterale solo per riga, issato fuori dal ciclo sui giorni, significa «due
  giorni sforati al prezzo di una quota», mentre la riga di EDT dice «una volta
  per settimana e per docente» — cioè conta le **volte**. Ora è per giorno, come
  in `MAX_HOURS`, che quotava la stessa frase in modo opposto.
  ⚠ `SITES` **resta com'era**, ed è una divergenza ora **dichiarata** invece che
  accidentale: in francese quella riga dice *par semaine*, quindi un'allowance
  settimanale e un letterale per riga sono difendibili.

  ⚠ **La quota di una riga di materia si deduceva col minimo delle chiavi**, e
  dava tre risposte diverse: la classe (per un accidente di chiavi esterne —
  `ClassPartition` punta alla `SchoolClass`, quindi la classe prende il
  `Resource.pk` più basso), la **parte** su una riga di parte, e una parte
  **qualunque** su una riga di raggruppamento. Un raggruppamento è trasversale
  (ADR-013): non esiste «la» sua classe, e attribuirgli la quota di un membro a
  caso è un'attribuzione decisa dall'ordine di creazione delle righe.
  `risorsa_di(row)` ora **legge** il campo che il `CheckConstraint` obbliga la
  riga ad avere, e sul raggruppamento dà `None`, cioè la quota generica.

  🔑 **`deroga()` restituiva `letterale | None`, e la prova che l'astrazione
  mancava era già nel codice**: quattro call site ripetevano lo stesso
  null-check, e il quinto (`post_cross`) si era scritto una chiusura locale per
  non ripeterlo altre cinque volte. Quando un call site cresce un involucro
  attorno a un helper, l'involucro appartiene all'helper. Ora restituisce sempre
  un oggetto con `.applica(vincolo)`, e senza quota è l'oggetto nullo — la
  stessa forma per cui `margine()` restituisce l'intero `0`.

  Più tre pulizie: `AddExactlyOne([])` è **già** INFEASIBLE (verificato), quindi
  il ramo `dominio_vuoto` e il suo booleano contraddittorio spariscono;
  l'uscita anticipata di `livelli()` **dichiara** di confondere due condizioni
  («niente di libero» e `allow_unplaced=False`) e la conseguenza in quella
  modalità — quote non minimizzate, rami di ADR-018 di nuovo alla pari, con
  l'oracolo di Hall fra i chiamanti; e la guardia di `qualcuna_piazzata` porta
  gli id nel nome invece di un `hash(aids) & 0xffff`, che troncato a sedici bit
  collideva.

  **Tre test nuovi, tre mutazioni, tre esiti distinti** — nessuno passa per
  caso. Suite: **571 test verdi**, 16 skip. Fermi invariato (8426 variabili,
  1086 constraint): il dataset non ha righe `RelaxationQuota`, quindi nessuno
  di questi letterali nasce lì — che è, di nuovo, la ragione per cui il Fermi
  misura il costo e mai la copertura.

  **Igiene**, dai residui di una sessione lavorata senza worktree: `AGENTS.md`
  era una copia di `CLAUDE.md` ferma al 2026-07-26 — 615 righe contro 1922,
  senza solver, analisi, Hall e pezzo 3 — cioè il peggior tipo di documento
  invecchiato, autorevole e caricato in automatico. Verificato che non portasse
  nulla di suo, è diventata un **symlink**. E `.claude/` entra nel `.gitignore`:
  ci viveva un worktree registrato di 6,4 MB dentro il repository.

- **2026-08-27** — **Il merge delle due linee, e il criterio dell'oracolo di
  Hall che il pezzo 3 aveva reso vuoto.** `master` e `origin/master` erano
  divergenti — diciannove commit locali del violatore di Hall contro undici del
  pezzo 3, entrambi partiti dal merge della PR #1. Un solo conflitto testuale
  (questo file); tutto il codice si è fuso da solo. **Ma le due linee si
  contraddicevano nel merito**, e la suite l'ha detto: **cinque rossi**.

  🔑 **Il pezzo 3 ha tolto da sotto i piedi alla fase 5 la sua unica prova.**
  Il modello ha smesso di pretendere il piazzamento, quindi un insieme
  deficiente non risponde più `INFEASIBLE`: **rinuncia**. La direzione 1
  dell'oracolo — «se la fase 5 dichiara un insieme infattibile, il solver deve
  rispondere INFEASIBLE» — chiedeva al solver una risposta che il solver non dà
  più. Riscritta su **due** modelli: `allow_unplaced=False`, che è il modello di
  prima dello scarto e che il suo stesso docstring chiama «il modo di chiedere:
  questo vincolo morde?», deve dare `INFEASIBLE`; e col modello vero i **minuti
  scartati** devono essere **esattamente** quelli che la fase 5 ha dichiarato
  mancanti. La seconda metà è più forte di ciò che c'era prima: non conferma
  che una deficienza esista, ne conferma l'**aritmetica**. Misurato sull'istanza
  dell'oracolo: deficit dichiarato `420 − 360 = 60`, minuti scartati **60**.
  ⚠ E la prova che non è un'asserzione di comodo è una **mutazione che il
  vecchio criterio non avrebbe colto**: sbagliando di una fascia la capienza in
  `hall.py` (`capacity - 1`), il test diventa rosso — mentre l'`INFEASIBLE` di
  prima sarebbe passato indisturbato.

  ⚠ **E il test che *non* era rosso era il peggiore dei due.**
  `test_il_solver_conferma_anche_il_confine` continuava a passare: asserisce
  `OPTIMAL`, e col pezzo 3 `OPTIMAL` è la risposta anche all'istanza
  deficiente. La coppia era stata scritta perché la seconda metà impedisse a
  una fase 5 «tutto infattibile» di passare la prima — e aveva smesso di poter
  fallire in entrambe le direzioni. **L'ottava forma di vacuità di questo
  progetto**, e la prima arrivata non da una svista ma da un merge: nessuno dei
  due lati era sbagliato *da solo*. Ciò che separa le due istanze non è più lo
  stato ma la rinuncia — **60 minuti là, zero qui** — ed è così che il confine
  è riscritto.

  ⚠ **La terza prova per `INFEASIBLE` passava per la ragione sbagliata.** In
  `test_il_rilassamento_non_ha_spento_la_fase_5` la riga `MIN_DISTRIBUTION`
  (min_days 3, docente libero un giorno solo) è una causa **indipendente e
  sufficiente** di infattibilità: misurato, col modello che ammette lo scarto
  la risposta è `INFEASIBLE` con **zero** minuti scartati, cioè l'infattibilità
  non viene dalla capienza che il test crede di misurare. Passata a
  `allow_unplaced=False` e **dichiarata**: quella metà *corrobora e non isola*,
  l'isolamento è nell'oracolo.

  🔑 **Un difetto di prestazione trovato per lettura, non cercato.** Il checker
  nuovo del pezzo 3 (`structural:placement`) ereditava
  `PLACEMENT_MONOTONE = True`, ma piazzare **ripara** la sua violazione — che è
  la definizione stessa di non monotono scritta in `domain/analysis/domain_size.py`.
  Sotto il criterio `chiavi_nuove = dopo − baseline` un checker che sa solo
  *togliere* chiavi non ne produce mai di nuove, quindi la marcatura **non
  cambia il verdetto di nessuna cella**: cambia il **costo**. Senza,
  `admissible_starts` scorreva tutte le attività non piazzate per ogni cella di
  prova, e la fase 5 sul Fermi era passata da **0,326 s a 1,887 s** — una
  regressione di 5,8× che nessun test misurava, perché la soglia era `< 5.0`.
  Marcato non monotono: **0,326 s**, il numero che il changelog dichiarava.

  I quattro test di monotonia asserivano liste esatte di causali HARD, ora
  sporcate da `activity_unplaced`: l'attività libera lì è deliberatamente non
  piazzata, cioè la **premessa** e non un esito. Aggiunto `_violazioni()`, che
  toglie l'incompletezza e lascia le violazioni di vincolo — il checker stesso
  dichiara di descrivere «un orario incompleto, non illegale».

  Suite dopo il merge: **568 test verdi**, 16 skip in ~100 s.

- **2026-08-26 (notte, hall)** — **Il violatore di Hall: la fase 5,
  implementata senza solver.** Sette task sul branch `hall-violator`, sopra
  [`docs/superpowers/specs/2026-08-26-violatore-di-hall-design.md`](superpowers/specs/2026-08-26-violatore-di-hall-design.md).
  `domain/analysis/hall.py` risponde alla domanda che la fase 4 non sa porre:
  non «questo vincolo impedisce il piazzamento», ma «questo *insieme* di
  attività non entra nella finestra di disponibilità comune delle sue risorse,
  anche se nessuna presa da sola è impossibile». Il metodo è il **teorema di
  Hall in forma deficitaria**: flusso massimo su una rete (attività → celle →
  risorsa `r`) per ogni (risorsa, firma di settimana) in `domain/analysis/flow.py`
  (nuovo, generico, senza semantica di orario — la stessa separazione che
  `domain/solver` ha fra `model.py` e i builder), e il **taglio minimo è
  l'insieme colpevole**. Una passata di riduzione greedy (`_reduce`) lo tiene
  **irriducibile** invece che massimale: senza, sul Fermi un finding
  nominerebbe centinaia di attività, una diagnosi che nessuno legge. Esposto
  in `manage.py analyze` come fase 5, dopo la fase 4, col flag `--no-hall` per
  spegnerla e la dichiarazione esplicita quando la salta (richiede
  `--schedule`, a differenza della fase 4 che lavora sull'anagrafica grezza).

  🔑 **Prima volta su questo progetto: due trappole scritte in spec *prima* di
  implementarle, non scoperte dopo.** Il pattern ricorrente qui — il
  changelog arriva a contarlo alla «tredicesima volta» entro il
  2026-08-26 (sera), sempre nella stessa forma — è che un documento dichiara
  vera una proprietà che si rivela falsa solo controllandola contro il
  checker o i dati. Questa volta la spec (§2, §4.1) ha **previsto** due falsi
  positivi specifici e ha chiesto un test dedicato per ciascuno, prima che il
  codice esistesse. Tengono entrambi.
  **§2 — le firme di settimana.** Due attività di settimane disgiunte non
  competono per la stessa cella; trattarle come concorrenti produrrebbe
  deficienze fantasma — il difetto peggiore possibile per una fase che dice
  «impossibile» e manda l'utente a smontare vincoli sani. `analyze_hall` riusa
  `week_signatures` di `conformity.py` (non `_week_groups` di `capacity.py`:
  la prima include le indisponibilità datate ed è la stessa firma su cui posta
  il modello CP-SAT), e `test_le_settimane_disgiunte_non_competono` lo tiene
  fermo.
  **§4.1 — lo spiazzamento.** Le attività candidate già piazzate (le
  «sorelle») vanno **tutte** spiazzate prima di calcolare i domini: se restano
  piazzate si tolgono il dominio a vicenda, la capienza calcolata scende sotto
  il vero e produce falsi positivi — un difetto che nessun caso positivo
  avrebbe rivelato. `_split` lo fa, e
  `test_le_sorelle_gia_piazzate_non_si_tolgono_il_dominio` lo dimostra.

  **Quattro scoperte durante l'esecuzione, non previste dalla spec.**
  `MaxFlow.max_flow` sollevava un loop infinito quando sorgente e pozzo
  coincidono (misurato: `exit 124`); irraggiungibile dalla rete di Hall così
  com'è costruita, ma un hang è il modo peggiore di fallire in uno strumento
  da riga di comando — ora solleva `ValueError`.
  `_cell_capacity` pesa le **quantità** dei materiali cumulativi, come
  `OccupationChecker.check` (`checkers/occupation.py` riga 25): contare le
  attività invece delle quantità avrebbe sovrastimato la capienza residua ogni
  volta che un'immobile già piazzata ne occupa più di una.
  I due test del Task 4 non dimostravano davvero il ciclo sulle firme — tre
  mutazioni realistiche passavano indisturbate, incluso il codice pre-task —
  corretti spostando la deficienza alla settimana 1 e aggiungendo un test
  portante sulla condivisione di `seen`.
  E un test del Task 3 non testava ciò che il suo nome diceva
  (`test_l_insieme_nominato_e_irriducibile` non esercitava `_reduce`, perché
  in quello scenario il taglio minimo restituisce già l'insieme irriducibile):
  rinominato `test_il_taglio_minimo_esclude_le_attivita_estranee`, e aggiunto
  `test_la_riduzione_toglie_la_terza_di_tre_sulla_stessa_cella`, costruito
  apposta perché il taglio minimo sia strettamente più largo dell'irriducibile.

  ⚠ **L'oracolo misura la precisione, mai il richiamo — per costruzione, non
  per pigrizia.** `tests/test_hall_oracle.py` verifica due direzioni: ogni
  finding dev'essere confermato dal solver (`INFEASIBLE`), e su istanze
  fattibili per costruzione (i testimoni di `solver_harness`) la fase 5 deve
  tacere — parametrizzata su **quaranta semi** (`range(1, 41)`), non i cinque
  del piano originale: **misurato**, 42 test in 6,4 s. Il richiamo — trovare
  *tutti* i sottoinsiemi infattibili — non si promette da nessuna parte:
  enumerare tutti i sottoinsiemi di risorse è esponenziale, ed è la ragione
  per cui l'alternativa è stata scartata già in §1.2 della spec. Il risultato:
  **zero finding sui 40 semi, nella suite** — non una misura di review
  rimasta fuori dal repository. E la qualificazione che conta quanto il
  numero resta: i testimoni di `build_witness` non aggiungono mai
  indisponibilità e lasciano circa metà griglia libera, quindi i 40 semi
  misurano **l'assenza di rumore su istanze lasche**, non la tenuta sul
  confine di Hall. Quel confine lo dimostrano solo i due casi scritti a mano
  (`test_un_finding_e_confermato_dal_solver`,
  `test_il_solver_conferma_anche_il_confine`).

  ⚠ **La proiezione di costo della spec era sbagliata di un ordine di
  grandezza, ed è stata corretta invece del changelog.** §4.2 stimava ~3,5 s
  sul Fermi intero, estrapolati linearmente dalla colonna S.P. di 26 attività
  (~12 ms/attività). Misurato (`test_fermi_intero_misurato` in
  `tests/test_analysis_hall.py`): **~0,4 s** su 284 attività — l'estrapolazione
  ignorava che i domini si calcolano una volta per attività dentro un solo
  `ScheduleState` condiviso fra tutte le risorse, non ricalcolati risorsa per
  risorsa. Come per il modello CP-SAT hard, sul Fermi questo misura il
  **costo**, mai la **copertura**: il dataset non ha righe di vincolo, quindi
  zero finding è l'esito atteso, non un risultato.

  Suite dopo i sette task: **516 test verdi**, 16 skip (i 35 in più sono i
  seed 6-40 dell'oracolo, appena portati nella suite). Corretto anche il
  **436** dichiarato nella nota di stato più sopra: era la misura di prima dei
  due commit di review della PR #1 (`modello-hard-completo`), non il numero
  corrente neppure a inizio di questo lavoro. E i **tre pezzi dichiarati
  fuori** nella nota di stato diventano **due**: resta l'assegnazione delle
  aule e gli alleggerimenti a quota con l'ottimizzazione lessicografica.

  ---

  ⛔ **E poi la review finale ha trovato un falso positivo dimostrato — il
  difetto che questa stessa voce si congratulava di aver prevenuto.** Tre righe
  di riproduzione: `mini_school()`, una riga `MIN_DISTRIBUTION`
  (`min_days = 3`) su un docente, tre attività da un'ora sui giorni 0, 1 e 2.
  `check_schedule` non emette **nessun** finding HARD, `solve` risponde
  `OPTIMAL` — e `analyze_hall` restituisce **tre** finding «L'attività non ha
  nessuna collocazione ammissibile». Cioè esattamente ciò che la fase 5 non ha
  il diritto di fare: mandare l'utente a smontare vincoli sani.

  🔑 **La causa sta nel punto che la spec dichiarava sano per definizione.**
  §4 diceva: *«Resta sano perché la condizione di `residual_domain` è
  precisamente l'ammissibilità»*. Non lo è. La condizione di
  `admissible_starts` è «la `Finding.key` è **cambiata** rispetto alla
  baseline», e `Finding.key` include le `quantities`. Per un checker la cui
  violazione è una **deficienza** — `MIN_DISTRIBUTION` esiste già a stato
  vuoto, con `days = 0` — ogni piazzamento *migliora* il conteggio e con esso
  cambia la chiave: chiave nuova a ogni cella, dominio vuoto, deficienza
  inventata. E §4.1 — la trappola che la spec aveva **previsto**, giustamente —
  è ciò che *crea* la condizione, perché spiazzando tutte le candidate insieme
  rende la baseline lo stato in cui i minimi sono massimamente violati. La
  precauzione giusta ha esposto il difetto sbagliato.

  ⚠ **Né le sette review per-task né l'oracolo a quaranta semi potevano
  vederlo, e il perché è il difetto vero.** `build_witness(seed)` lascia
  `ResourceTimeConstraint.objects.count() == 0`, `SubjectConstraint == 0`,
  `ResourceUnavailability == 0`: le righe di vincolo le creano i
  **derivatori**, che `build_witness` non chiama. I quaranta semi dell'oracolo
  esercitavano quindi lo stesso sottoinsieme dello spike a cinque vincoli — ed
  è **letteralmente** la frase che questo file porta già sul Fermi («non misura
  il modello completo: misura il dataset. Ha zero righe
  `ResourceTimeConstraint`, zero `SubjectConstraint`»), non applicata al banco
  nuovo. Un numero grande di semi ha fatto da anestetico: quaranta ripetizioni
  della stessa misura povera sembrano una copertura.
  **Corretto** estraendo da `run_tutte_le_famiglie` la metà che **non chiama il
  solver** — `costruisci_tutte_le_famiglie(seed)`, che deriva le righe di tutte
  e ventisei le famiglie e **asserisce** che il testimone le soddisfi insieme.
  Su quei testimoni densi la fase 5 era rossa **40 semi su 40** — da **1 a 29**
  falsi positivi per seme, **14,1 di media**; e l'oracolo resta a **~26 s** per
  i quaranta semi,
  perché alla fase 5 il solver non serve e non lo si paga.

  **La correzione**: `Checker.PLACEMENT_MONOTONE`, dichiarato nella stessa
  forma di `PLACEMENT_INDEPENDENT` — default `True`, `False` sulle famiglie in
  cui piazzare può *riparare* una violazione oppure spostare l'identità del
  finding senza aggravarlo. `admissible_starts(..., relaxed=False)`; con
  `relaxed=True` esclude i non monotoni, e `hall.py` passa `relaxed=True`.
  ⚠ Il default resta `relaxed=False`, quindi **S.P. non cambia di un bit** e
  nessun test esistente si muove: `S.P.` è una stima di difficoltà in una
  colonna ordinabile, e un dominio più stretto è per l'utente informazione, non
  un bug — la fase 5 è l'opposto, il suo verdetto negativo è una dimostrazione.
  Rilassare fa perdere **richiamo**, mai precisione: domini più larghi
  significano più capienza, quindi meno deficienze trovate. È il verso giusto
  in cui sbagliare.

  🔑 **E l'elenco della review era corretto ma non esaustivo, in entrambe le
  direzioni.** La review dava quattro famiglie, misurate su dieci semi.
  Rileggendo i checker uno per uno ne escono **sei**: le tre confermate
  (`MIN_DISTRIBUTION`, `FREE_GUARANTEED`, `IMPOSED_SUCCESSION` in **entrambi**
  i rami) più `MAX_GAP_HOURS` — il buco è `ultima − prima + 1 − conteggio`,
  quindi piazzare *dentro* un buco lo **riduce** — e tre casi di **deriva
  d'identità**: `WEEKLY_ORDER` (il finding nomina l'argmin), i quattro
  `PARTS_*` (nomina l'intero secchio) e `structural:didactic_weight` (nomina
  tutte le attività dell'unità, quindi un piazzamento di lunedì rikeya la
  violazione di venerdì). ⚠ Le ultime quattro **la misura non le vede**: hanno
  bisogno di un'attività **congelata** per manifestarsi, e il banco a testimone
  non congela niente — lo stesso buco che il 2026-08-26 (sera) aveva già
  costretto a costruire il banco che congela per il solver. La stessa cecità,
  su un banco diverso, sei giorni dopo.
  ⚠ E in senso opposto: `ARRIVAL_DEPARTURE`, la quarta dell'elenco, **non lo
  è**. La prova è per lettura del checker: `compliant` è **non crescente** sotto piazzamento, per due
  ragioni indipendenti: una giornata **vuota** contribuisce 1 e piazzandoci
  può solo restare 1 o passare a 0; una giornata **già occupata** ha `slots[0]`
  che può solo calare e `slots[-1]` che può solo crescere, quindi le due
  condizioni `>= not_before` e `< not_after` possono solo passare da vero a
  falso. Nessuna riparazione è possibile, e ogni cambio di chiave è un
  peggioramento causato dalla prova.
  Resta monotona, e la divergenza è dichiarata invece che appianata.
  ⛔ **E la misura che avevo messo a sostegno era vacua** — «marcandola non
  monotona, zero semi su quaranta cambiano esito» **non poteva dare altro
  risultato**: marcare una famiglia non monotona *allarga* i domini, e
  l'oracolo attende zero finding, quindi quel verde era incapace di fallire in
  entrambe le direzioni (42 passed con e senza). È la settima forma di vacuità
  di questo progetto, dentro la voce che si congratula di averle imparate a
  riconoscere — scritta qui invece che tolta in silenzio.
  ⚠ La misura **simmetrica** invece dice qualcosa: rimettere `MaxGapChecker` a
  monotono lascia anch'esso 42 passed, e lì il verde *poteva* fallire (marcarlo
  restringe i domini). Quel dato non è vacuo: è la misura di una **cecità del
  banco**, non di una proprietà del checker.
  ⚠ Su `WEEKLY_ORDER` e sui quattro `PARTS_*` il rilassamento costa richiamo e
  **oggi non compra precisione**: i loro builder trattano ADR-018 vietando ai
  liberi il secchio già sporco, quindi rispondono `INFEASIBLE` esattamente dove
  il dominio non rilassato si svuotava — misurato, ed è il motivo per cui i due
  test corrispondenti hanno il **checker** come metro e non il solver. Si
  rilassano lo stesso, perché `PLACEMENT_MONOTONE` è una proprietà del
  *checker*: legarla alla scelta di un builder metterebbe in `domain/analysis`
  una dipendenza dal solver — quella che il package esiste per non avere.

  **Ogni marcatura è verificata per mutazione**: rimettendo `True` su una sola
  famiglia, il test di *quella* famiglia diventa rosso e nessun altro (sette
  mutazioni, sette esiti distinti). E il banco morde anche nel verso opposto,
  che con una correzione fatta *restringendo ciò che si scarta* è il rischio
  vero: `analyze_hall` sostituita da `return []` incondizionato lascia **12
  test rossi** fra i quattro file della fase 5.

  ⚠ **Il costo è lineare nel numero di firme, e il numero dichiarato veniva
  dall'unico dataset che ne ha una sola.** Il Fermi ha **una** firma di
  settimana, quindi «~0,4 s, è anzi la più veloce delle famiglie di analisi»
  era una conclusione generale tratta dalla dimensione che il dataset non
  esercita — mentre §2 della spec chiama le firme *«una dimensione, non un
  dettaglio»*. Misurato aggiungendo indisponibilità **datate** (il meccanismo
  reale: le assenze): 1 firma 0,34 s · 3 firme 0,99 s · 6 firme 1,88 s ·
  11 firme 3,25 s · 21 firme 5,98 s — circa **0,3 s per firma**. Un anno reale
  ha 35-40 settimane, quindi nel caso limite **~10-13 s** sul Fermi. Resta
  accettabile per una fase diagnostica lanciata a mano, e `--no-hall` esiste
  apposta; ma va letto come «0,3 s per firma», non come un numero assoluto.
  Spec e nota di stato corrette in loco.

  **Chiusi nello stesso giro** i minori della review: il caveat degli archi a
  ∞ nel docstring di `_deficient_set` (§3.2 lo imponeva testualmente);
  `_labels` che deduplica per nome — senza, gli atomi di ADR-017 ripetevano il
  nome della classe una volta per atomo più una per `ClassPart`, e su una
  scuola vera la frase diventava illeggibile, che è l'UX del finding, cioè il
  punto del pezzo; i due `assert` mancanti (`findings == []` sul Fermi,
  `activities` sulla riduzione). E la decisione **dichiarata** sui due
  guardiani che si potevano togliere lasciando la suite verde: `required <=
  capacity` e il clamp `max(0, base - used)` sono **entrambi irraggiungibili
  per costruzione** — il primo perché con gli archi centrali a ∞ il lato
  sorgente del taglio minimo soddisfa sempre la disuguaglianza e `_reduce` la
  preserva; il secondo perché ogni cella che arriva a `_cell_capacity` è
  passata per `admissible_starts`, dove `structural:occupation` (monotono,
  quindi presente anche col rilassamento) scarta le celle sature. **Restano
  entrambi**, col perché nel docstring: il primo è la §3.3 della spec, cioè un
  argomento sui grafi residui trasformato in postcondizione controllata; il
  secondo è l'ultima porta prima di Dinic, dove una capacità negativa non
  fallirebbe — produrrebbe un certificato che non torna, in silenzio.

  **Suite a fine lavoro**: `venv/bin/pytest -q` → **525 test verdi**, 16 skip
  in ~85 s.

- **2026-08-26 (notte, pezzo 3 — ondata 7)** — **`manage.py solve`, e il pezzo
  3 è chiuso.** Il comando nella forma di `analyze`: stato, dimensioni del
  modello, i **criteri in ordine di priorità** con valore, se l'ottimo è
  dimostrato e quanto è costato, e gli scarti **nominati** uno per uno con
  materia, classe e docente — non «infeasible», ma *chi* è rimasto fuori.
  ⚠ Non scrive niente senza `--applica`: un solve sovrascrive l'orario di una
  scuola, e il default non può essere scrivere. Exit code ≠ 0 se resta qualcosa
  di scartato, come `analyze`; e dopo `--applica` le **violazioni residue** si
  dichiarano, perché un orario illegale è uno stato ammesso.

  🔑 **E il comando ha trovato un difetto della catena.** Sul Fermi L2 costava
  **4,07 s** contro gli 0,47 s di L1 — per riscoprire lo stesso orario da zero.
  Ogni livello ripartiva senza sapere nulla del precedente. Con la soluzione
  del livello concluso passata come **suggerimento**: 0,27 s, e il totale del
  comando da 4,9 s a **1,2 s**. ⚠ `AddHint` accumula, quindi `ClearHints`
  prima — senza, a quattro livelli il proto porta quattro copie dei
  suggerimenti; un test lo tiene fermo contandoli.

  **Il pezzo 3 è completo**: sette ondate su sette. Suite: **493 test verdi**,
  16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 6)** — **L4: la stabilità fra
  periodi.** L'ultimo livello minimizza le attività che cambiano cella rispetto
  ai `Placement` esistenti. È la conseguenza di [ADR-010](decisioni.md)
  rimasta scoperta da luglio — rigenerando l'orario a ogni periodo serve un
  criterio «mantieni il più possibile le collocazioni precedenti», o il secondo
  quadrimestre viene stravolto per tutti — ed è anche ciò che EDT minimizza nel
  risolutore passo-passo. Come previsto da D4, è costato un `minimize`, non
  un'architettura.

  ⚠ **Ultimo, e l'ordine è provato da un test**: conservare una collocazione
  non vale uno scarto. ⚠ E il primo test scritto per quella proprietà **non
  discriminava** — due ore accatastate nella stessa cella danno un movimento in
  entrambi gli ordini, perché anche scartare un'attività già piazzata conta
  come spostamento. Riscritto su un'istanza dove i due ordini danno risposte
  diverse: con L1 prima si piazzano entrambe e la vecchia si sposta; con L4
  prima la vecchia resta e la nuova viene scartata.

  Suite: **486 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 5)** — 🔑 **L3, e il debito di §9.7
  chiuso da una misura.** Il terzo livello della catena conta le **violazioni
  nuove** che il modello si concede: le quote consumate e le riparazioni
  mancate dei rami disgiuntivi di ADR-018. Due conteggi distinti sommati in un
  livello solo — un conteggio, non una somma pesata — e restano separati dove
  conta: una riparazione mancata **non consuma quota**, perché non è un
  alleggerimento.

  **Il debito era testuale**: «il modello non ha funzione di costo, quindi
  `riparato` e `riparato.Not()` sono alla pari e CP-SAT non ha motivo di
  preferire la riparazione». Adesso ne ha uno. Non cambia cosa il modello
  ammette — cambia cosa preferisce — ed era la quarta strada, quella senza
  rischio semantico, delle tre che §9.7 elencava senza adottarne nessuna.

  ⚠ **E la prova non è un argomento, è una misura**: dopo L3 il ramo pigro non
  compare più su **60 semi** del banco che congela, dove prima c'era ai semi
  20, 35, 41, 45 e 52. Quindi **l'esenzione che lo perdonava è stata rimossa**
  da `_classifica_nuove`, insieme al test che la esercitava — un'esenzione che
  non scatta mai non è un'esenzione, è codice che nessun test afferma. Il banco
  è ora **più severo di prima**: se il fenomeno tornasse diventerebbe rosso
  invece di perdonarlo in silenzio, e rimetterlo sarebbe una decisione da
  prendere guardando la misura.

  ⚠ **Il primo test scritto per L3 non discriminava**, ed è la solita forma:
  provava che il solver *ripara*, ma senza L3 il solver può riparare **per
  caso** — misurato, restava verde con la mutazione. Sostituito da due test sul
  valore del livello: la riparazione mancata contata quando riparare è
  impossibile (una griglia di due giorni con `min_days=3`), e la quota non
  consumata quando non serve. Tre mutazioni, tre rossi, ciascuno sul test
  giusto.

  Suite: **484 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 4)** — **I pre-filtri, e il task che
  aveva la premessa sbagliata.** L'ondata era scritta come «le quote nei
  pre-filtri». Controllando i documenti **prima** di scrivere il codice, la
  premessa è caduta: in EDT l'indisponibilità **rossa non si alleggerisce
  mai**, e la **gialla si rispetta come la rossa** — l'utente può autorizzare
  il motore a ignorarla, ma con un'**opzione di calcolo per categoria di
  risorsa** («Piazza le attività anche sulle fasce con indisponibilità
  opzionali», declinata sulle cinque risorse), mai selettiva sulla singola.
  Non è una quota. È §9.8 di nuovo, stavolta su un piano scritto poche ore
  prima.

  ⚠ **E la verifica ha trovato un difetto vero: il solver era più permissivo
  di EDT su una famiglia intera.** Il pre-filtro ignorava il giallo del tutto —
  si comportava come se l'override fosse sempre acceso — e **il test che
  c'era affermava il comportamento sbagliato**, chiamandosi
  `test_giallo_e_verde_non_restringono`. Ora il giallo restringe come il
  rosso, l'override è il parametro `ignora_opzionali` per `Resource.Kind`, e
  il verde resta fuori: è una preferenza, e il suo posto è un livello di
  qualità della catena, non un pre-filtro.

  ⚠ **Due famiglie dell'enum non sono quote**, e ora è dichiarato invece che
  implicito: `UNAVAILABILITY` e `OPTIONAL_UNAVAILABILITY` restano nello schema
  approvato ma nessun builder le consulta. Un test lo tiene fermo — con una
  quota da cinque violazioni sull'indisponibilità rossa, il modello resta
  `INFEASIBLE` — così che chi volesse renderle quote debba prima cancellarlo e
  leggerne il perché.

  Suite: **483 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 3b)** — **Tutte le famiglie
  alleggeribili.** Agganciate le restanti: presenza massima, massimo di mezze
  giornate (tetto **e** «solo mezza giornata al giorno», che è una deroga),
  entrate/uscite, giorni e mezze giornate libere, cambi di sede, peso
  didattico, massimo di ore di una materia e sequenze indesiderate.

  ⚠ **Sulle soglie il margine si sottrae, e va al ramo giusto.** «Togli se
  necessario … mezze giornate libere per settimana» abbassa la soglia; ma nel
  ramo disgiuntivo di ADR-018 si applica **solo** alla riparazione, mai allo
  status quo — quello non è una soglia da alleggerire, è il divieto di
  peggiorare rispetto alla baseline, e alleggerirlo autorizzerebbe un
  peggioramento del passato, che è un'altra cosa da quella che la finestra di
  EDT concede.

  ⚠ **Un letterale per riga, non per parametro.** Presenza (minuti + giorni),
  giorni liberi (giorni + mezze), sedi (per giorno + per settimana): sono due
  parametri dello stesso alleggerimento, e due quote consumate per una sola
  concessione sarebbero state un errore che nessun test avrebbe visto.

  ⚠ **Le righe di materia sono tre famiglie, non una.** La finestra di EDT le
  tiene distinte — `Incompatibilità materie`, `Massimo di ore delle materie`,
  `Sequenze indesiderate di materie` — con quote separate, e il nostro enum ne
  aveva una sola: aggiunte `SUBJECT_MAX_HOURS` e `SUBJECT_SEQUENCE`
  (migrazione `0009`). Condividere una quota fra un margine e una deroga
  sarebbe stata una deviazione silenziosa dal prodotto.

  🔑 **E l'ondata 1 ha reso falso un argomento scritto in `weight.py`.** Il
  salto sul secchio settimanale inevadibile era giustificato dal fatto che «la
  somma dei letterali liberi è una costante» — vero solo con `AddExactlyOne`.
  Ora non lo è più: il clamp non sarebbe *contraddittorio*, sarebbe la pretesa
  che il presente **scarti** per espiare il peso del passato. La conclusione
  regge, l'argomento no, e il commento è stato riscritto invece di lasciarlo
  invecchiare. Stessa sorte per il commento di `post_separable` e per quello
  del peso, che citavano `AddExactlyOne` per una proprietà che oggi discende
  da `piazzata`.

  **Quindici test su diciassette cadono** con una sola mutazione — il
  meccanismo che non concede niente — e i due che restano verdi sono quelli
  che devono restarlo: «senza righe il modello è quello di prima» e «una quota
  a zero è come non averla». Suite: **481 test verdi**, 16 skip.

- **2026-08-26 (notte, pezzo 3 — ondata 3a)** — **Le quote: un vincolo
  rilassabile non diventa soft.** `domain/solver/relaxation.py`, il meccanismo
  e due famiglie. Istruzione letterale del prodotto: *«Sbloccate i vincoli da
  alleggerire e selezionateli per quantificare il margine di manovra concesso
  al calcolo»* — non esiste «spegni il vincolo», resta hard con un numero
  massimo di violazioni attribuito per famiglia e per risorsa.

  **Due forme, perché le righe della finestra `Alleggerimenti` sono di due
  tipi**: il **margine**, dove il vincolo si allarga di una quantità dichiarata
  (`expr <= tetto + margine·v`), e la **deroga**, dove semplicemente non si
  considera per quell'occorrenza (`OnlyEnforceIf(v.Not())`). Agganciate
  `MAX_HOURS` (margine) e le tre incompatibilità di materia (deroga), queste
  ultime in **entrambi** i rami `post_separable` e `post_cross`: alleggerirne
  uno solo avrebbe lasciato metà famiglia scoperta senza che un test se ne
  accorgesse.

  ⚠ **Lo schema è cresciuto di due campi, ed era un buco di modellazione già
  segnalato dalla spec**: `RelaxationQuota.params` (il *quanto*, che mancava
  accanto al *quante volte*) e `InstituteSettings.max_relaxed_constraints_per_resource`
  (il tetto globale «numero massimo di vincoli da alleggerire per risorsa»).
  Più `ARRIVAL_DEPARTURE` fra le famiglie: in EDT `Gestione Entrate / Uscite`
  è alleggeribile e non c'era. Migrazione additiva, nessun dato da riscrivere.

  🔑 **Un vincolo alleggerito resta una violazione nominata.** `check_schedule`
  continua a produrre il suo finding `HARD`, ed è il comportamento di EDT —
  l'orario risolto della base di esempio conteneva 21 attività su 984 che non
  rispettavano i vincoli, e il prodotto continuava a lavorare. La quota non
  nasconde la violazione: autorizza il solver a produrla, in numero limitato.
  Un test lo tiene fermo, contando i finding dopo il solve.

  ⚠ **Il margine si somma al *residuo*, non al tetto grezzo**, ed è il punto in
  cui questo pezzo poteva sbagliare in silenzio: alleggerire concede spazio
  **sopra lo stato corrente**, mai la pretesa che il passato venga riparato
  (ADR-018). Misurato per mutazione — con `cap + margine` al posto di
  `residuo + margine` due libere entrano dove ne entra una sola, e il test
  diventa rosso.

  **Sette mutazioni, sette rossi**: quota non postata, tetto globale non
  postato, margine decuplicato, quota a zero trattata come quota, deroga
  sempre assente, deroga tolta da `post_cross`, margine sul tetto grezzo.
  Suite: **472 test verdi**, 16 skip.

  Restano le famiglie dell'ondata 3b — presenza, mezze giornate, giorni
  liberi, entrate/uscite, sedi, peso didattico e le altre righe di materia —
  e le quote nei pre-filtri (ondata 4), che è il caso storto.

- **2026-08-26 (notte, pezzo 3 — ondata 2)** — **La catena lessicografica.**
  `domain/solver/objective.py`: risolvi per il criterio 1, **fissa** quel
  valore, passa al 2 — mai una somma pesata. Due livelli, L1 le ore scartate e
  L2 il loro numero come spareggio (D1), il fissaggio a `<=` e non `==`, il
  limite di tempo **per livello** (una catena di quattro livelli con
  `time_limit=60` può spendere quattro minuti: va detto, non scoperto), e gli
  `stats` che riportano ogni livello con nome, valore, **se l'ottimo è stato
  dimostrato** e quanto è costato.

  🔑 **La strategia a due passate di EDT è questa catena, non due esecuzioni.**
  «Il piazzamento rispetta tutti i vincoli; se restano attività scartate,
  potete alleggerire» è «L3 dopo L1»: si consuma un alleggerimento solo quando
  riduce gli scarti, perché a scarti pari il livello dopo preferisce zero
  violazioni.

  ⚠ **E la mutazione ha bocciato il test del meccanismo centrale.** Il primo
  test di monotonia usava un'istanza a **pareggio** — un blocco da 2h contro
  due ore singole — dove L1 e L2 indicano la stessa risposta: togliere
  `model.Add(level.var <= valore)`, cioè il fissaggio, lasciava la suite
  **verde**. Riscritto su un'istanza in cui i due livelli tirano in direzioni
  **opposte** (quattro fasce, un blocco da 3h più tre ore singole: L1 vuole
  fuori due ore in due attività, L2 vorrebbe fuori tre ore in una sola), dove
  la mutazione diventa rossa.

  ⚠ **Due rami che nessun test poteva affermare**, e la cucitura che li rende
  affermabili: un livello che **non conclude** (la catena si ferma, ma
  restituisce la fotografia dell'ultimo livello concluso invece di buttare via
  il lavoro) e uno che **non dimostra** l'ottimo. Farli scattare con un limite
  di tempo stretto sarebbe stato un test flaky su una macchina più lenta: da
  qui `solve_chain(solver=...)`, con due solver finti di sei righe. Entrambe le
  mutazioni corrispondenti diventano rosse.

  ⚠ **I due fenomeni del banco sporco si sono spostati per la terza volta**, ed
  era prevedibile: sono proprietà della **soluzione restituita**, e ogni ondata
  cambia l'obiettivo. Invece di ri-appuntare un seme, i due test ora
  **cercano** il fenomeno su una lista dichiarata — provando più semi dentro
  lo stesso test con un `transaction.atomic` annullato, perché ricostruire la
  scuola due volte nella stessa transazione violerebbe l'unicità delle
  anagrafiche. Il test afferma così la cosa che conta — *l'esenzione è
  esercitata da qualcosa* — invece di una coincidenza fra un seme e una
  configurazione del solver.

  ⚠ **Un difetto introdotto e colto dai test dell'ondata 1**: `unplaced`
  calcolato solo `if placements` faceva sparire lo scarto proprio nell'istanza
  in cui l'unica attività è impiazzabile — la distinzione è fra «nessuna
  soluzione» e «una soluzione senza piazzamenti», e va fatta sul `None`.

  **I numeri.** Fermi: `OPTIMAL`, zero scarti, due livelli conclusi e
  dimostrati, **8426 variabili e 1086 constraint** — +1 variabile per L2, +2
  constraint per le uguaglianze dei livelli e +2 per i fissaggi che la catena
  aggiunge percorrendola. Suite: **464 test verdi**, 16 skip, **92 s** contro i
  74,8 di ieri: è il costo di due solve per istanza invece di uno, ed è la
  ragione per cui il limite di tempo è per livello.

- **2026-08-26 (notte, pezzo 3)** — **Il modello smette di pretendere il
  piazzamento.** Comincia il **pezzo 3** — alleggerimenti a quota e
  ottimizzazione lessicografica — con la spec
  ([design](superpowers/specs/2026-08-26-alleggerimenti-lessicografico-design.md))
  e le sue quattro decisioni chiuse in sessione: **L1 conta le ore** (il numero
  di attività è lo spareggio), lo scarto è **`HARD`**, il ramo pigro di §9.7 si
  chiude dentro **L3**, la stabilità fra periodi è **L4** di questa catena. Poi
  la prima delle sette ondate: `AddExactlyOne` diventa
  `somma(celle) == piazzata`, e ciò che non ci sta resta **scartato** invece di
  rendere infattibile tutto l'orario.

  ⚠ **Lo scarto va nominato, o l'oracolo diventa vacuo** — previsto scrivendo
  la spec, non scoperto dopo. In `domain/analysis` non esisteva alcuna causale
  sul non-piazzamento e nessun checker guardava le attività prive di
  `Placement` (l'occupazione si costruisce **dai** piazzamenti): appena cade
  `AddExactlyOne`, «scarta tutto» è una soluzione con zero occupazioni, zero
  findings, verde. Da qui `structural:placement`. **Il registro ha ora 28
  checker e 26 builder**, e la seconda assenza è dichiarata da un test come la
  prima: la traduzione dello scarto esiste — è `somma(celle) == piazzata` — ma
  non è un builder, perché crea le **variabili di decisione** e deve esistere
  prima che qualunque builder giri (`vocabulary.pos` la legge).

  🔑 **Il «tetto inevadibile» di §9.5 era inevadibile per colpa di
  `AddExactlyOne`.** L'argomento diceva che le libere «vanno collocate, e
  ovunque vadano pesano»: vero solo finché il piazzamento è obbligatorio. Con
  `somma(celle) == piazzata` la somma dei letterali liberi torna a dipendere
  dalle decisioni, e il tetto settimanale del peso didattico torna evadibile
  **nel modo in cui lo evade EDT: scartando**. La chiave grossolana per le
  famiglie indipendenti dal piazzamento diventa una scelta invece di un
  obbligo. ⚠ Resta la metà delle congelate, che è un fatto e non una decisione.

  ⚠ **E la regola della casa cambia forma.** «Forza la violazione e attendi
  `INFEASIBLE`» smette di funzionare: con lo scarto ammesso la risposta a una
  violazione forzata non è l'infattibilità ma la **rinuncia** — misurato,
  `OPTIMAL` con esattamente uno scarto in 23 test su 27 rossi. Da qui
  `build_model(allow_unplaced=False)`, che è il modello di prima e resta il
  modo di chiedere «questo vincolo morde?». I 23 test lo usano; la domanda che
  ponevano è intatta.

  ⚠ **Il banco a testimone si era indebolito in silenzio**, ed è la forma
  vecchia del difetto nuovo: cancella i piazzamenti, risolve e controlla che la
  soluzione sia pulita per la famiglia — ma **una soluzione che scarta è pulita
  per qualunque famiglia**, perché un'attività non piazzata non viola niente.
  Il testimone esiste, quindi l'ottimo è zero scarti: preteso in tre punti
  (`run_family`, `run_tutte_le_famiglie`, prova B del banco che congela).

  🔑 **La presolve espandeva l'obiettivo, e il banco ci passava dentro senza
  accorgersene.** Quattro test del testimone erano passati da ~0,5 s a **60 s
  esatti** — il limite di tempo — restando verdi. Il log lo dice per nome:
  *«objective: expanded via tight equality»*, 36 volte su un testimone da 32
  attività. I 32 booleani `piazzata` spariscono dall'obiettivo e al loro posto
  entrano **723 letterali di cella**; il dominio iniziale passa da `[0, 660]` a
  `[-35460, 2040]`. Il solver trova `best:0` in un decimo di secondo e poi
  spende un minuto a dimostrare che non esiste un ottimo negativo — vero per
  costruzione, ma non più per lui. Con `presolve_substitution_level = 0`:
  **`OPTIMAL` in 0,09 s**. ⚠ Il dominio dichiarato di un `IntVar` da solo
  **non basta** (misurato: bound −720, tempo pieno), e nemmeno `AddHint` sui
  `piazzata` (nessun guadagno: rimosso, perché un meccanismo che nessuna misura
  giustifica è peso morto).

  ⚠ **I due fenomeni del banco sporco dipendono da *quale* ottimo torna, e
  CP-SAT in parallelo non è riproducibile.** La deriva d'identità e il ramo
  pigro si sono spostati di seme due volte in una sessione — una per
  l'obiettivo, una per la presolve — e la prima volta erano **verdi da soli e
  rossi nella suite intera**. Non era il seme: con più lavoratori CP-SAT
  restituisce l'ottimo che il primo thread trova. Da qui `workers=1` nella
  prova B (e il parametro su `solve()`); rimisurati due volte di fila con lo
  stesso esito, il ramo pigro sta al **20** (e al 35, 41, 45, 52), la deriva
  d'identità all'**11**, unica su sessanta semi.

  ⚠ **Due mutazioni hanno bocciato metà del lavoro nuovo, di nuovo.** Il test
  su `apply()` che cancella il piazzamento di ciò che è stato scartato
  **restava verde** con la cancellazione rimossa: l'attività scartata non aveva
  una riga da cancellare. E i due guardiani di `pos` — la sentinella «oltre la
  griglia» e la guardia del builder d'ordine — erano coperti da **un solo**
  test che nessuna delle due mutazioni faceva diventare rosso, perché in
  quell'istanza ciascun meccanismo bastava da solo. Separati in due test, uno
  per meccanismo, ciascuno ucciso dalla propria mutazione.

  **I numeri.** Fermi: `OPTIMAL`, **zero scarti**, 0,74 s, **8425 variabili e
  1083 constraint** — la differenza dai vecchi 8140/1082 è tutta la macchina
  dello scarto, contata: +284 booleani `piazzata`, +1 per i minuti scartati, e
  sui constraint il solo +1 dell'obiettivo (i 284 `AddExactlyOne` sono
  diventati 284 uguaglianze). Suite: **458 test verdi**, 16 skip, e il tempo
  totale è **quello di prima** (74,8 s contro 74,6 s) — che è il vero verdetto
  sulla riparazione della presolve.

- **2026-08-26 (notte)** — **La review della PR #1, e il gemello del difetto
  nella famiglia che il banco non poteva vedere.** Quattro rilievi sistemati
  sopra il banco che congela.
  🔑 **`OccupationBuilder` aveva lo stesso difetto di `SiteTransitionBuilder`,
  ed è la conferma che «tocca» contro «realizza» è un pattern, non un
  incidente.** Il gate `any_free` guarda chi tocca la cella, non chi ne
  realizza la saturazione: due congelate in conflitto su una cella che una
  libera può toccare producevano `costante + libere <= capienza` con la sola
  costante oltre il tetto — `INFEASIBLE` per colpa del solo passato, con il
  checker che quello stato lo prevede e lo nomina (`resource_occupied_locked`,
  HARD). Corretto con `residual_cap`, come tutti gli altri tetti. ⚠ **Il banco
  che congela non poteva trovarlo**: `sporca()` ripacka solo in celle libere da
  conflitti di occupazione e lo asserisce, quindi la famiglia esclusa per
  costruzione dal banco è proprio quella in cui il difetto è sopravvissuto. La
  chiusura di Ruling 20 resta valida, ma **non è totale**: un banco ha sempre
  una cecità, e va detto dove.
  ⚠ **Metà del guardiano nuovo non era asserita da niente.** Misurato:
  rimuovendo il solo `continue` del ramo `s == t` di `SiteTransitionBuilder` e
  lasciando l'altro, la suite intera restava verde. Aggiunto il test del ramo
  (`test_adr018_site_transition_due_sedi_gia_sulla_stessa_fascia_non_blocca`),
  che è raggiungibile solo a capienza simultanea > 1. Entrambi i test nuovi
  sono **verificati per mutazione**: senza la correzione diventano rossi.
  ⚠ **Le due prove del banco passavano su `UNKNOWN`.** `!= INFEASIBLE` non è
  `in (OPTIMAL, FEASIBLE)`: al timeout la prova A passava senza soluzione, e la
  prova B pure — con i piazzamenti vuoti `apply()` è un no-op dichiarato e
  l'oracolo differenziale confrontava la baseline pre-solve con sé stessa.
  Verde per non aver misurato niente, cioè il criterio con cui questa stessa
  sessione aveva bocciato `test_famiglia_con_congelate`. Corretto in entrambe.
  Corretta infine una contraddizione interna: «Ancora aperto» dava
  `free_guaranteed` in peggioramento da 2 mezze giornate a 1, mentre la misura
  (spec §9.7) è uno **scambio** — `free_days 4 / free_half_days 1` →
  `free_days 1 / free_half_days 4`. **450 test verdi**, 16 skip.

- **2026-08-26 (sera)** — **Il banco congela, e il primo builder a cadere è
  quello che si dichiarava già a posto.** Chiude il debito che §9.7 chiamava
  «il buco strutturale più grande che resta» (Ruling 20): fino a qui **nessun
  test del banco congelava niente**, quindi in ogni modello che il banco
  costruiva `ctx.free` conteneva tutto — `split()` con `frozen = 0` sempre,
  `any_free` sempre vero, `frozen_occupies` sempre falso, `residual_cap` che
  non clampava mai, i rami disgiuntivi mai imboccati. Tutta la copertura di
  ADR-018 poggiava sui test scritti a mano.

  **La costruzione.** Si genera il testimone pulito, si derivano le righe di
  **tutte** e ventisei le famiglie, poi si **ripacka**: alcune attività si
  spostano in celle libere da conflitti di occupazione — «libere da conflitti»
  non è cosmetico, è ciò che lascia il resto dell'orario dov'è. Chi risulta
  **implicato** nelle violazioni così create viene congelato; gli altri restano
  liberi e i loro piazzamenti si cancellano. Il risultato è letteralmente la
  premessa di ADR-018: congelate **già in violazione**, libere da piazzare.

  🔑 **La prova che morde è la prima, non l'oracolo.** Si **forza** ogni libera
  nella cella dove il testimone la teneva e si attende che il modello non
  risponda `INFEASIBLE`. Quell'assegnazione non aggiunge niente — per
  costruzione, perché la baseline è calcolata su di essa e ogni attività
  implicata è congelata — quindi rifiutarla è *pretendere una riparazione*, la
  metà vietata del criterio di ADR-018. È la forma della casa (forzare e
  attendere uno stato), applicata a un modello intero invece che a una riga.

  ⚠ **`SiteTransitionBuilder` non aveva il guardiano ADR-018 che due commenti
  gli attribuivano.** Trovato al seme 38, ridotto alla forma minima in
  `tests/test_solver_sites.py`. `any_free` guarda chi **tocca** le due fasce,
  non chi **realizza** la coppia di sedi vietata: due congelate di sede diversa
  a distanza insufficiente sono già una violazione, ma basta una qualunque
  libera che tocchi una delle due fasce perché la clausola venga postata — e
  quella clausola ha **entrambi** i letterali forzati a 1 dalle congelate.
  `INFEASIBLE` per colpa del solo passato. Il commento di
  `builders/time_sites.py` diceva «ha già ADR-018 nella forma della regola
  dell'implicazione (`any_free`): non toccato», e il docstring di
  `test_adr018_cambio_gia_prodotto_dalle_congelate_non_blocca` lo ripeteva.
  **Il pattern di questo progetto per la tredicesima volta**, e stavolta l'ha
  trovato una misura, non una rilettura. Corretto con `_sede_congelata`, che
  rispecchia **letteralmente** la selezione dei letterali di
  `Vocabulary.site_occupied` — leggere il codice invece del proprio ricordo è
  la stessa regola che vale per `B` nei rami disgiuntivi.

  🔑 **E la mutazione ha bocciato metà del lavoro.** Il banco nasceva con
  **due** parti: oltre a quella sporca, un `test_famiglia_con_congelate` che
  congelava una parte del testimone dov'è, famiglia per famiglia, su baseline
  pulita — 78 test, 28 secondi, i due terzi del tempo aggiunto. Su **sette**
  mutazioni della macchina ADR-018 non è diventato rosso **una sola volta**,
  mentre il banco sporco le ha colte su **sei** delle sette (`split` 4 rossi,
  congelate a dominio pieno 8, `any_free` 2, `_sede_congelata` 1,
  `_status_quo_rappresentabile` 1, `frozen_occupies` 1 — e **zero** entrambi
  sul clamp di `residual_cap`, che resta difeso dai soli test scritti a mano).
  Rimosso: un test che non diventa rosso quando il codice che afferma sparisce
  non sta affermando niente. ⚠ Il banco **non sostituisce** i test a mano —
  aggiunge la sola cosa che nessuno di loro sapeva fare, trovare un difetto che
  nessuno cercava.

  **Due esenzioni dichiarate, entrambe misurate, entrambe esercitate da un test
  apposta.** ⚠ La prima estende §9.5 oltre le famiglie indipendenti dal
  piazzamento: la **deriva d'identità**. Diverse famiglie non nominano in
  `activities` il secchio intero ma la **coppia argmin** o la coppia
  consecutiva — chi viola, non chi partecipa; piazzare una libera accanto a una
  congelata cambia allora *quale* coppia è l'argmin senza cambiare la
  violazione. Misurato al seme 20: `subject_imposed_succession` sulla risorsa 1
  passa da `(5, 7)` a `(4, 5)` con `gap 3 / max_gap 2` **identici**. È la stessa causa a monte del
  tie-break di `_placed_of` già in «Ancora aperto».
  La seconda è il **ramo pigro** di §9.7, per la prima volta misurato invece
  che dichiarato — e con una forma più precisa di quella descritta lì: è uno
  **scambio**, non un peggioramento secco. Al seme 20 `free_guaranteed` passa
  da `free_days 4 / free_half_days 1` a `free_days 1 / free_half_days 4`:
  ripara la soglia delle mezze (min 3) e rompe quella dei giorni (min 2), che
  era soddisfatta. Le due soglie stanno sotto **lo stesso** booleano proprio
  per impedirlo (correzione del 2026-08-26 mattina), ma con le libere non
  ancora piazzate lo status quo non è rappresentabile, il ramo scende a `>= 0`
  e scavalca il booleano. Perdita di qualità, non di correttezza:
  l'esenzione è stretta apposta — una violazione su una risorsa **pulita**
  resta rossa anche per quelle tre famiglie.

  ⚠ **E un docstring del banco è stato falsificato entro l'ora.**
  `run_family_congelata` dichiarava «la baseline resta pulita»: falso.
  Cancellando i piazzamenti delle libere, le famiglie che contano una quantità
  *presente* — successione imposta, minimi, distribuzione — sono violate
  proprio **perché manca qualcosa** (misurato: `imposed_succession` al seme 3,
  finding `(2,) max_gap 2` già prima del solve). Il criterio giusto è il
  **contenimento** rispetto alla baseline pre-solve, non `== set()`.

  **Osservazione a margine, non risolta**: `residual_floor` non è chiamato da
  **nessun** builder — solo dal proprio test. I minimi di §3.1 non sono mai
  stati trattati per sottrazione di termini: i cinque casi di ADR-018 usano
  `frozen_occupies` o la disgiunzione reificata. È il gemello documentale di
  `residual_cap`, non codice morto per distrazione, ma va detto.

  **I numeri.** Su 40 semi, **36** producono una costruzione sporca
  utilizzabile (saltano 13, 14, 17 e 28: le violazioni implicano quasi tutto e
  restano meno di tre libere) e la dirt copre **26 causali distinte**. Dieci
  semi entrano nella suite, scelti per fenomeni diversi e non a caso; su quelli
  la costruzione **non può saltare**, così che una decadenza diventi rossa
  invece di svuotarsi in silenzio. Suite: **448 test verdi**, 16 skip.

- **2026-08-26** — **La review finale, e due builder che rifiutavano il
  presente.** Sei findings su tutte e ventisei le famiglie, con i seed allargati
  da 5 a 40. ⚠ **Il risultato più importante è positivo e va detto per primo**:
  **zero** builder più larghi del checker e **zero** più stretti del testimone.
  I difetti stanno su input **sporco** (ADR-018), copertura di test e vacuità
  del banco — non nella traduzione dei vincoli.

  **I due gravi erano lo stesso errore in due forme.**
  `MinDistributionBuilder` postava la soglia **grezza** pur avendo il
  controesempio scritto nella propria docstring: due congelate sullo stesso
  giorno, una libera, `min_days=3` → `INFEASIBLE` **anche forzando lo status
  quo**, cioè rifiutando un piazzamento che non introduce niente di nuovo.
  Spegnendo il solo builder, `OPTIMAL`. `FreeGuaranteedBuilder` clampava le due
  soglie **una per volta**, ma i due conteggi si escludono a vicenda —
  `libera = attivo AND NOT meta` conta una mezza solo se il giorno lavora,
  quindi un giorno che la soglia dei *giorni* obbliga a lasciare vuoto
  contribuisce **zero** mezze — e la congiunzione era irraggiungibile mentre
  ciascuna soglia da sola no. Entrambi passano alla **disgiunzione reificata**
  già in uso su `WeeklyOrderBuilder`, con le due soglie sotto **lo stesso**
  booleano. `B` si legge **chiamando il checker** di `domain/analysis`, mai
  riscrivendone la condizione: una divergenza di uno renderebbe il residuo
  peggiore del difetto. Misurato: status quo rifiutato 45/45 → **0** e 43/45 →
  **0**, `solve()` `INFEASIBLE` 33/45 e 16/45 → **0**, coppie (causale,
  risorsa) nuove **0** prima e dopo.
  ⚠ **ADR-018 ha quindi cinque casi, non quattro**, e la §9.5 della spec —
  scritta il giorno prima — **dichiarava vere due cose false**: che
  `FREE_GUARANTEED` fosse risolto dal residuo per forzatura e che
  `MIN_DISTRIBUTION` «reggesse davvero». Nessuna delle due si vedeva
  rileggendo il documento. È il pattern di questo progetto per l'ennesima
  volta, stavolta su un documento scritto da meno di ventiquattr'ore.

  🔑 **E la mutazione che avrebbe dovuto accorgersene non poteva.**
  `PartsHomogeneousHalfBuilder` non era difeso da **nessun** test: un `post()`
  no-op sulla sola sottoclasse `_H` lasciava la suite identica alla baseline,
  mentre le altre tre danno 5, 3 e 3 rossi. Tutte le mutazioni fatte fino a lì
  spegnevano `_PartsOrderBuilder.post`, cioè **tutte e quattro le sottoclassi
  insieme**: misuravano la base, non le foglie. **Corollario da portarsi
  dietro: quando un builder ha sottoclassi, la mutazione va fatta per
  sottoclasse.** Lo stesso corollario ha poi trovato un secondo buco —
  `_giorni_garantiti` sostituito da `resource_days` lasciava la suite verde,
  cioè il codice faceva una distinzione che nessun test affermava.

  **Settima forma di vacuità.** `_derive_max_gap` dichiarava «anche a budget
  zero è un vincolo vero»: falso, il buco è `ultima − prima + 1 − conteggio`,
  quindi serve una mezza giornata larga **almeno tre**, e la fixture pesca
  anche `(4, 2)` dove entrambe le metà sono larghe due. Otto righe inviolabili
  su 40 seed, e il **seed 2 era fra i cinque del banco** — un verde incapace di
  fallire. Ora salta onestamente: **uno skip in più, 15 → 16**, che è il numero
  giusto. E `_derive_two_days` era l'unico derivatore di materia senza la
  guardia di co-attività per firma; ⚠ `_coppia_violabile` **non** si può
  riusare, perché richiede lo **stesso** secchio mentre `TWO_DAYS` vuole
  l'opposto.

  **I quattro `parts_*` si invalidavano a vicenda**, e la precedenza fra
  derivatori introdotta al Task 17 non poteva proteggerli: tutti e quattro
  risintonizzano la **stessa** materia della **stessa** attività di parte, e
  non esiste un ordine che funzioni. Serviva un guardiano, non un riordino.
  Con `_sintonia_compatibile` la composizione passa da 34/40 a **40/40**
  puliti; le righe scendono da 48-73 a **36-76**, e il minimo cala perché i
  numeri di prima **includevano righe diventate vacue** — il sospetto che la
  review aveva segnalato senza quantificare era fondato.

  ⚠ **Debito nuovo, dichiarato e non risolto: il ramo status quo è pigro.**
  Senza funzione di costo i due rami sono alla pari, e nel solve incrementale
  con le libere non ancora piazzate la baseline è quasi sempre già violata
  perché **nulla è piazzato**: `B` vale quanto qualificano le sole congelate e
  il ramo diventa **vacuo**, cioè la riga smette di vincolare. Misurato. È
  perdita di qualità, non di correttezza, e va decisa sulla **famiglia** dei
  rami disgiuntivi — vedi «Ancora aperto» e §9.7 della spec.

  Suite: **436 test verdi**, 16 skip.

- **2026-08-25** — **Il modello hard completo: ventisei builder su
  ventisette.** Diciassette task sul branch `modello-hard-completo`, ciascuno
  scritto da un sottoagente su un brief e verificato per mutazione. Il registro
  dei builder è chiuso: la ventisettesima chiave (`structural:coverage`) non ha
  un builder **per costruzione** — è `PLACEMENT_INDEPENDENT`, confronta attività
  e servizi anagrafici e non guarda mai i piazzamenti, e il solver non crea né
  distrugge attività. L'assenza è **dichiarata da un test**
  (`tests/test_solver_registry_completo.py`), così che chi volesse aggiungerla
  debba prima cancellare il test e leggerne il perché. **436 test verdi**, 16
  skip tutti misurati e attribuiti.

  **Il vocabolario, e perché esiste.** I checker ragionano su quantità che i
  piazzamenti non contengono: «il docente lavora quel giorno», «quella mezza
  giornata è occupata», «la posizione della prima occorrenza di questa
  materia». Tradurle una per builder avrebbe prodotto ventisei definizioni
  incoerenti della stessa cosa. `domain/solver/vocabulary.py` le costruisce una
  volta sola — `occupied`, `day_active`, `half_active`, `pos` — memoizzate per
  chiave, e ⚠ **parametriche sulla firma di settimana**, che è la dimensione su
  cui questo progetto ha già sbagliato una volta.

  **ADR-018 nelle sue forme, che non erano due.** La spec ne prevedeva due —
  tetti (si clampa il residuo a zero) e minimi (nessun clamp, non sono mai
  infattibili per colpa del passato). Ne sono servite **quattro**.
  ⚠ I minimi **non** sono sempre innocui: su `ARRIVAL_DEPARTURE` e
  `FREE_GUARANTEED` una congelata in una fascia proibita **consuma** la
  quantità contata, e nessuna mossa sulle libere la recupera — corretto col
  residuo *per forzatura* (`frozen_occupies`), mentre `MIN_DISTRIBUTION` regge
  davvero, quindi l'asimmetria è reale e non generale.
  ⚠ E il caso che nessuno aveva previsto: il **tetto inevadibile**. Il secchio
  settimanale del peso didattico contiene *tutte* le celle candidate di ogni
  attività dell'unità, quindi `AddExactlyOne` rende la somma dei letterali
  liberi una **costante**: col residuo clampato a zero il vincolo diventa
  `costante positiva ≤ 0`, falso comunque vada il piazzamento. Non «inagibile»:
  **contraddittorio**. Il clamp, che altrove è il trattamento giusto, produce
  qui esattamente ciò che ADR-018 vieta — misurato, `INFEASIBLE` con due
  congelate e una libera. Il criterio che unifica i quattro casi è più preciso
  di «tetto o minimo»: **`INFEASIBLE` che nasce dal vietare un peggioramento è
  ammesso, `INFEASIBLE` che nasce dal pretendere una riparazione no.**

  **Il generatore a testimone.** Il banco genera **prima** un orario valido a
  caso, **poi** le righe di vincolo che quell'orario soddisfa, e solo allora
  chiede al solver di ricostruirlo da zero. Rende impossibile un oracolo vacuo:
  un builder che postasse `1 == 0` non trova il testimone, uno che non postasse
  nulla lascia passare un orario che il checker boccia. Ogni derivatore
  restituisce il proprio **potere vincolante** (quante righe ha creato), e zero
  fa saltare il seed invece di spacciarlo per un successo.

  **Le trappole trovate leggendo i checker invece di ricordarli.**
  `FREE_GUARANTEED` conta le mezze giornate libere **solo sui giorni con
  attività**, non su tutti; `MAX_PRESENCE` usa la **giornata intera** dove il
  D.T.B. usa la mezza; `_PartsOrder` bucketizza per giorno, ma
  `PartsHomogeneousHalfChecker` **sovrascrive** il bucket con la mezza giornata,
  e invertire le due cose non fa fallire niente di ovvio; `ImposedSuccession`
  non ha la guardia di vacuità che `WeeklyOrder` ha, quindi con B assente
  **ogni** occorrenza di A è in violazione. Nessuna di queste era nel piano.

  **I due conservativi previsti erano uno.** ⚠ `HALF_DAY_GAP` era il caso
  vetrina della sovra-approssimazione deliberata: si è rivelato **esatto**. Le
  due regole — coppie consecutive nel checker, tutte le coppie incrociate nel
  builder — sono equivalenti (dimostrato, e verificato su 200 000 casi sintetici
  con zero divergenze). Resta conservativo il solo `structural:site_transition`.
  A consuntivo: **venticinque builder esatti su ventisei**.

  **⚠ E la misura sul Fermi dice meno di quanto sembri.** `OPTIMAL` in ~0,56 s,
  284 attività, 8140 variabili, 1082 constraint — **gli stessi numeri, byte per
  byte, dello spike a cinque vincoli del 2026-08-09**. La ragione è che il
  dataset Fermi ha **zero** righe `ResourceTimeConstraint`, **zero**
  `SubjectConstraint` e i quattro tetti di peso a `None`: delle ventisei
  famiglie ne esercita cinque, e ventuno builder non postano nulla. «OPTIMAL sul
  Fermi col modello completo» è una frase vera e priva di contenuto, ed è ora
  scritta così nel test, con due assert che la tengono ferma.
  La misura vera è `test_modello_completo`, aggiunto qui: tutte le famiglie
  attive **insieme** sullo stesso testimone — 22–23 famiglie con righe su 26,
  48–73 righe, `OPTIMAL` su tutti e cinque i seed, oracolo pulito. Non esisteva:
  il banco provava ventisei modelli da una famiglia ciascuno, e due traduzioni
  corrette separatamente possono contraddirsi una volta postate insieme.

  **Comporre ha trovato una precedenza che nessuno aveva visto.** ⚠ I derivatori
  **non sono componibili in ordine qualunque**: due sono in formulazione densa e
  non osservano il testimone, lo **riparano**. `_derive_site_transition`
  riassegna le sedi — che sono ciò che `max_site_changes` conta;
  `_sintonizza_parti` riassegna la materia — che è ciò su cui ogni riga
  `SubjectConstraint` è ancorata. In ordine alfabetico la composizione risponde
  `INFEASIBLE` su 2 seed su 3. Entrambe le docstring dichiaravano di non
  disturbare nessuno: vero per il testimone *in sé*, falso per le righe già
  derivate da altri. Corrette, e la precedenza è ora esplicita.

  **L'oracolo differenziale era rimasto alle cinque famiglie dello spike** per
  dieci task: `CODICI` non era mai stato esteso, quindi copriva un ventesimo di
  ciò che sorvegliava di nome. Ora copre le ventisei, con una guardia che gli
  impedisce di reinvecchiare — una causale nuova deve finire in `CODICI` oppure
  in `FUORI`, per decisione esplicita.

  **Il passo «risolvi e guarda» è un rilevatore debole, misurato.** Sulle quattro
  famiglie `PARTS_*` le righe derivate sono violabili **118 volte su 120** —
  forzando la violazione: `INFEASIBLE` col builder acceso, `FEASIBLE` con quello
  spento — eppure il banco, che risolve e guarda, coglie un builder rotto **1
  volta su 11**. CP-SAT non cerca la soluzione cattiva e quasi mai la trova per
  caso. Da qui la regola della casa: **il test che dimostra che un vincolo morde
  forza la violazione e attende `INFEASIBLE`**, mai «risolvi e controlla dove è
  finita». La sonda esatta di violabilità è adottata in questa forma, e
  **non** come criterio del banco: farne il criterio richiederebbe di
  reimplementare in CP-SAT la condizione di violazione di tutte e ventisei le
  famiglie, dentro il banco che le verifica.

  **Il pattern, contato.** «Questa semplificazione è conservativa» era già stata
  asserita e falsificata tre volte prima di questo piano. Il piano l'ha ripetuta
  (`HALF_DAY_GAP`), e ne ha aggiunte altre: derivatori senza `return` (**tre
  volte** — avrebbero reso una famiglia intera verde per non aver fatto nulla),
  docstring che dichiarano di non disturbare nessuno, `residual_cap` dichiarato
  sufficiente per ogni tetto. Sempre la stessa forma: **il documento dichiara
  vera una proprietà che si rivela falsa solo controllandola contro il checker o
  contro i dati, mai a colpo d'occhio sul documento.** Le due contromisure che
  hanno funzionato sono misurare il derivatore del piano **prima** di scrivere
  il builder, e la mutazione — spegnere il builder e contare i rossi, perché un
  test che non diventa rosso quando il codice che afferma sparisce non sta
  affermando niente.

  **Debiti dichiarati**, tutti in «Ancora aperto» o nella §9 della spec: il
  banco **non congela mai nulla**, quindi la copertura di ADR-018 poggia
  interamente sui test scritti a mano; `coverage_mismatch` sul testimone, da
  riparare nella fixture prima di qualunque oracolo differenziale a tutto campo;
  i due tie-break di `domain/analysis` che sono artefatti dell'ordine
  d'inserimento; e ⚠ **una metà del tetto inevadibile che nessun builder può
  risolvere** — la `Finding.key` cresce comunque delle attività libere, quindi
  per le famiglie indipendenti dal piazzamento l'oracolo differenziale andrà
  formulato su una chiave più grossolana, o quelle famiglie andranno dove EDT le
  mette davvero: nell'analisi di capienza, che si esegue *prima* del calcolo.

- **2026-08-24** — **La review finale falsifica l'oracolo, e lo ripara.**
  L'oracolo dichiarato "tenuto" il 2026-08-09 aveva un limite non notato:
  scuola giocattolo, Fermi per una classe e Fermi intero condividono tutti
  **un'unica firma di settimana** (tutte le attività sono annuali), quindi la
  dimensione «settimane» di `domain/analysis/conformity.week_signatures` non
  era mai stata esercitata. La review finale l'ha trovato lì: `MaxGapBuilder`
  (il D.T.B.) dichiarava **conservativo** trattare tutte le attività come
  co-attive, ignorando le firme. **Non lo è.** Il buco è
  `ultima − prima + 1 − conteggio`: un'occupazione che cade *dentro* il buco
  ma viene da un'attività di un'**altra** firma alza il conteggio senza
  toccare `prima` né `ultima` — riempie il buco nel modello unione, mentre
  nelle settimane reali quel buco resta scoperto. Trattare tutto come
  co-attivo vincola quindi **di meno**, non di più: l'opposto di quanto
  dichiarato. Dimostrato con un'istanza a due firme costruita apposta
  (indisponibilità **datate**, non ricorrenti, su un docente con D.T.B. = 0):
  il solver rispondeva `OPTIMAL` piazzando una terza attività a riempire un
  buco che, settimana per settimana, nessuna attività attiva poteva colmare —
  e `check_schedule` bocciava il piazzamento con un `max_gap` `HARD`.
  Esattamente il fallimento che il criterio di riuscita dello spike dichiara
  inaccettabile.
  **Corretto**: `MaxGapBuilder` ora posta un budget **per firma di
  settimana** — un `model.Add(...)` per ogni `(rep, _)` di `ctx.signatures`,
  con i letterali `occ` filtrati alle sole attività attive in quella firma
  (`SolverContext.occupied` guadagna un parametro `signature` opzionale,
  memoizzato per `(firma, chiave, giorno, fascia)`; senza firma si comporta
  come prima). Firme diverse con lo stesso insieme di attività attive
  producono lo stesso vincolo: deduplicate con `posted`, come già fa
  `OccupationBuilder`. Nuovo test in `tests/test_solver_oracle.py` —
  `test_oracolo_su_istanza_multi_firma` — che nessuno dei banchi di prova
  esistenti poteva scrivere, perché il Fermi non ha la varietà di firme per
  farlo scattare.
  ⚠ **La stessa semplificazione in `subject_constraints.py` resta corretta**,
  e non è stata toccata: lì più letterali significano una somma più
  vincolata, mai il contrario — il caso pessimo è perdere qualche soluzione,
  mai accettarne di illegali.
  **Non è un errore di chi ha implementato: è il piano, la terza volta.** La
  semplificazione era scritta nei vincoli globali del piano con quella
  giustificazione. Sullo stesso branch: prima il D.T.B. tradotto come soglia
  per singolo buco invece che come budget settimanale (intercettato in fase
  di design, prima del commit); poi il modello dei token che non sapeva
  distinguere parti della stessa partizione da parti di partizioni diverse
  (ADR-017); ora questo. Tre volte lo stesso pattern: il piano dichiara una
  proprietà — soglia singola, insieme di chiavi sufficiente, semplificazione
  conservativa — che si rivela falsa solo quando la si controlla contro il
  checker o contro i dati, mai a colpo d'occhio sul piano stesso.
  **Rifiniture minori nello stesso giro**: `EMPTY_ATOMS` (dead code, zero
  riferimenti) rimosso da `domain/analysis/state.py`; in
  `subject_constraints.py` il ramo `A = B` ora conta attività distinte, non
  letterali, prima di postare il vincolo ridondante; `apply()` documenta di
  non fare nulla su `placements` vuoto; `test_fermi_intero_misurato` non può
  più spegnersi in silenzio se lo stato è feasible ma `placements` è vuoto;
  aggiunto un test di `AtomMap` con tre partizioni sulla stessa classe.
  **Chiusa la lacuna che restava**: il test multi-firma aggiunto qui sopra
  dimostra la correzione con un `INFEASIBLE`, ma nessun banco di prova
  portava una soluzione multi-firma **fattibile** lungo l'intera catena
  `solve → apply → check_schedule → violazioni() == []` — cioè il caso che il
  criterio di riuscita dello spike descrive davvero. Aggiunto
  `test_oracolo_su_istanza_multi_firma_fattibile`: due giorni per quattro
  fasce, due settimane, cinque attività. Il giorno 0 porta la dimensione
  D.T.B. (un buco che si chiude per firma e non si chiude nell'unione), il
  giorno 1 quella dell'occupazione (due attività di settimane diverse con
  docente, classe e unica collocazione ammissibile in comune: co-attive
  sarebbero un conflitto, e non lo sono mai). **Verificato che discrimina**,
  non solo che passa: rompendo `OccupationBuilder` (tutte le attività
  co-attive) e, separatamente, `MaxGapBuilder` (letterali `occ` senza firma),
  il test risponde `INFEASIBLE` in entrambi i casi. Suite completa a **173
  test verdi**.

  **Questione aperta, non risolta qui**: cosa fare quando un constraint
  mescola attività congelate già in violazione e attività libere nello stesso
  vincolo — va deciso nella spec del modello completo, prima degli altri
  ventidue builder. Aggiunta all'elenco **«Ancora aperto»**.

- **2026-08-09** — **Lo spike CP-SAT, e ADR-017 chiuso.** `domain/solver/`,
  package separato da `domain/analysis/` perché quest'ultimo resti senza
  `ortools`. Cinque vincoli tradotti, scelti per attraversare i **tre pattern
  di traduzione** dal predicato al modello CP-SAT: **pre-filtro strutturale**
  (`structural:grid`, `structural:unavailability` — le celle inammissibili non
  diventano nemmeno variabili), **cardinalità sulla risorsa**
  (`structural:occupation` come conflitto e capienza cumulativa,
  `MAX_GAP_HOURS`) e **relazione fra materie** (`SAME_DAY_INCOMPATIBLE`). I
  builder sono registrati sotto le **stesse chiavi** dei checker di
  `domain/analysis`.
  **ADR-017 chiuso.** Il problema che lo teneva aperto: un insieme di token
  non sa dire «parti della stessa partizione sono disgiunte, parti di
  partizioni diverse si sovrappongono» sulla stessa coppia di oggetti — sono
  due affermazioni opposte sulla stessa relazione. Gli **atomi** (`AtomMap` in
  `domain/analysis/state.py`), le celle del prodotto delle partizioni, la
  esprimono senza toccare l'architettura a intersezione di insiemi: aggiunti
  per tutte e tre le vie con cui una parte entra nelle chiavi (parte diretta,
  via raggruppamento, via espansione della classe intera), e **solo** per le
  classi con almeno due partizioni — altrove nulla cambia. Nessun campo nuovo,
  nessuna migrazione.
  **La correzione sul `D.T.B.`** Il vincolo era stato tradotto come soglia per
  **singolo** buco. Non lo è: il checker somma i minuti di buco su **tutte le
  mezze giornate della settimana** e confronta una volta sola — è un budget
  settimanale, dove due buchi da un'ora sforano un budget di un'ora e mezza.
  L'errore è stato intercettato in fase di design, rileggendo il checker
  invece del proprio ricordo di cosa facesse: è esattamente il tipo di svista
  che l'oracolo esiste per intercettare.
  **L'oracolo tiene.** Il criterio di riuscita è uno solo: una soluzione del
  solver, riscritta nei `Placement` e riletta da `check_schedule`, non produce
  alcun finding `HARD` nelle cinque famiglie modellate. Ha tenuto al primo
  colpo — sulla scuola giocattolo, sul Fermi ristretto a una classe e sul
  Fermi intero. E che potesse fallire è stato **verificato**: corrompendo
  deliberatamente i piazzamenti, tutte le famiglie provate hanno prodotto il
  finding atteso (`test_oracolo_puo_fallire` in
  `tests/test_solver_oracle.py` — un test della suite, non un esperimento una
  tantum: la prova resta nel repo, non solo nella sessione di review).
  ⚠ **Falsificato il 2026-08-24**: nessuno di quei tre banchi di prova
  esercita più di una firma di settimana, e proprio lì si annidava il
  difetto. Vedi la voce corrispondente più sopra.
  **Le misure sul Fermi intero**: 284 attività (288h00), **tutte libere**
  (nessuna congelata dai pre-filtri strutturali), **8140 variabili**, **1082
  constraint**, `OPTIMAL` in **meno di un secondo** (~0,55s). ⚠ Come già una
  volta con `scripts/genera_orario.py`, quel risultato **non dice nulla**
  sulla risolvibilità dell'istanza reale: è la risposta a un problema con
  **cinque vincoli su ventisette**, non ai ventisette.
  **Cosa resta fuori**, esplicitamente: gli altri ventidue vincoli del
  registro, gli alleggerimenti a quota, l'ottimizzazione lessicografica,
  l'assegnazione delle aule, il violatore di Hall, un comando `manage.py
  solve`.

- **2026-07-26 (notte, analisi)** — **L'analisi dei vincoli, implementata:
  `domain/analysis/`.** Chiude il piano 2 (dodici task) sopra lo schema
  approvato: un package di predicati con causali nominate, sul modello
  dell'`Analisi dei vincoli` di EDT osservata dal vivo.
  **Il registro.** Findings e catalogo causali (`findings.py`, `causali.py`);
  `ScheduleState` che materializza una settimana (occupazione, indisponibilità,
  monte ore) **una volta sola per verifica** — i checker leggono lo stato, non
  fanno query dentro `check()` (`perf(analysis)`, commit `066efc8`); un
  registro con **copertura completa verificata da test**: gli **otto** vincoli
  orari sulla risorsa, i **tredici** di materia, e **sei** checker strutturali
  (griglia, sedi, occupazione/indisponibilità, copertura, peso). Sopra il
  registro: la conformità di una settimana contro tutti i checker in un colpo
  solo.
  **Il dominio residuo.** `S.P.`/`Nr G.` di EDT riprodotto come **piazzamento di
  prova**: quante fasce restano legali per un'attività contro lo stato
  corrente. Misurato sul Fermi: la colonna S.P. di un'intera classe (26
  attività) in **~0.3s**.
  **La capienza esatta.** L'algoritmo `Dotazione − Bisogni` di EDT, con
  **colpevoli per sottrazione** (non solo il verdetto, ma quali attività
  restano fuori e perché); le **due diagnosi osservate in EDT riprodotte sui
  numeri**: il caso semplice (`600` richiesti, `540` piazzabili) e
  l'incrociata classe+docente (`360`/`300`).
  **Il comando.** `manage.py analyze`: report in stile EDT (`Enunciato del
  problema` → `Dettaglio` → `Soluzione`) più un riepilogo finale.
  **Il Fermi, arricchito.** Aggiunte le indisponibilità attese di
  `vincoli-attesi.md` (D06/D09/D15, giornate intere), e un test che inverte
  deliberatamente STO/SCI in tre servizi: la copertura per (classe, materia)
  lo rileva anche se i **totali quadrano lo stesso** — il bug reale del
  2026-07-09 diventa un test di non regressione.
  **Le code del piano 1, chiuse.** `tests/test_constraint_negatives.py`: i sei
  test negativi rimandati (cattedra a due/zero unità, vincolo di materia a due
  unità, partizione duplicata, quota senza risorsa, `Break.straddles` con
  durata 1) confermano che i `CheckConstraint` **mordono davvero**. Corretto
  anche un refuso in `modello-dominio.md` (**12 tipi censiti** → **13**: l'enum
  implementato dei vincoli di materia ne ha 13) e annotato in `institute.py` il
  percorso di sola lettura di `domain/analysis` (`filter(pk=1).first()`, non
  `load()`, per non scrivere alla prima analisi). **116 test verdi** a suite
  completa (`venv/bin/pytest`). Prossimo passo: **il piano 3**, il modello
  CP-SAT sul registro.

- **2026-07-26 (notte, seguito)** — **Lo schema del dominio, implementato.** Per
  TDD dal design approvato in [docs/modello-dominio.md](modello-dominio.md):
  progetto Django minimale `config/`, app `domain/` (modelli su istituto, risorse,
  curriculum, classi, docenti, tempo, attività, vincoli, più `domain/weeks.py`) e
  la suite in `tests/` — **39 test, tutti verdi**. `tests/fermi.py` è il dataset
  Fermi come fixture: primo test di rappresentazione, con la quadratura verificata
  sui dati reali (284 attività / 288h, 18 docenti a quadratura zero, copertura per
  ogni coppia (classe, materia)). Aggiunti anche i casi **oltre-Fermi** che il
  dataset da solo non esercita: parti IRC/ALT, raggruppamenti trasversali (2A-2B),
  sedi, sostituzione come maschera a un bit. I piani successivi: predicati e
  analisi di capienza, poi il modello CP-SAT.

- **2026-07-26 (notte)** — **Cambio di fase: da analisi a progettazione.**
  [ADR-016](decisioni.md) chiude formalmente la condizione di ADR-008:
  l'osservazione di EDT è conclusa, si progetta. Scritto e approvato (sezione per
  sezione, in sessione) il **design del modello di dominio v1**
  ([docs/modello-dominio.md](modello-dominio.md)). Le scelte portanti:
  modello **autonomo dal SaaS** con due entità di convergenza (attività con
  maschera temporale, disponibilità con data opzionale); le **tre condizioni di
  ADR-015 sciolte in forma** — piazzamento come entità separata con quattro
  livelli di immobilità, vincoli come righe di dato interrogabili (ogni vincolo =
  constraint CP-SAT + predicato + causale nominata), parte di classe con FK
  nullable al piano di studi (`NULL` = eredita); risorsa **generica** a sei tipi
  (le cinque di EDT + la parte) con una sola tabella di disponibilità a tre
  livelli e data opzionale, e capacità cumulativa unica per aule e materiali;
  griglia parametrica con **mezza giornata** e intervalli-separatori;
  rigenerazione per periodo tramite l'entità `schedule`; attività con la sola
  materia obbligatoria e maschera di settimane a bit; vincoli sui quattro assi con
  la relazione **orientata** e `A = B` come caso dominante; alleggerimenti **a
  quota**, modello lessicografico, niente funzione di costo. Prossimo passo: il
  piano di implementazione (schema Django + dataset Fermi come primo test di
  rappresentazione).

- **2026-07-26 (sera)** — **Il motore visto girare, e la scoperta che tocca il
  SaaS.** Ultima passata su EDT: chiusi tutti i punti aperti tranne due, e
  l'osservazione del prodotto si può considerare **conclusa**.
  **1) Il motore all'opera.** Esperimento sulla base di esempio: sospese le **27
  attività di una classe intera** da un orario per il resto pieno — l'istanza
  difficile, non quella facile — e rilanciato il calcolo. **27/27, zero scarti, in
  ~10–15 secondi**; una singola attività, ~2 s. Le **quattro fasi sono dichiarate
  mentre girano** (`Fase calcolo (n / 4)` più percentuale interna), la prima passata
  piazza circa metà e si ferma, il grosso lo fa la seconda; `Lancia il calcolo`
  diventa **`Interrompi`** e ciò che è già piazzato resta.
  **2) 🔑 EDT espone la dimensione del dominio.** Le colonne `S.P.` e `Nr G.` — che
  a orario pieno valgono quasi sempre `1` — si accendono appena si sospende
  qualcosa. Tooltip letterale: *«numero di **fasce orarie possibili** per il
  piazzamento dell'attività **nel rispetto di tutti i vincoli**»*. È il dominio
  residuo della variabile, **ricalcolato contro lo stato corrente** (sospendendo una
  lezione salgono i vicini, richiudendo il buco riscendono), messo in una colonna
  ordinabile. Sui dati: l'ora singola a 21 collocazioni, il blocco da 3h00 a 6, la
  religione in compresenza a 4, le ore `Q1`/`Q2` a 34 perché vivono in due
  quadrimestri. **Per noi è gratis** — il solver quel numero lo calcola comunque — e
  ordinando per `S.P.` crescente si ottiene *prima* del calcolo la lista di cosa sta
  per diventare impiazzabile.
  **3) 🔑 Il risolutore passo-passo, end-to-end.** Tre pannelli affiancati: la
  scheda dell'attività (con il conto di **tutte e cinque** le risorse), la griglia
  annotata astratta, e **l'orario reale del docente** accanto — la mappa delle
  decisioni vicino al contesto che le rende comprensibili. Cliccando una cella
  grigia, il costo è dichiarato **per nome**: non «3 conflitti» ma le tre lezioni con
  giorno, ora, materia, docente e classe — e fra queste la MATEMATICA di un altro
  docente, perché il conflitto passa dalla **classe**, non dal docente. Intanto **le
  risorse in conflitto diventano rosse** nel pannello di sinistra: la finestra dice
  anche *su quale* delle cinque si sta consumando. Premuto `Piazza`, le tre scacciate
  diventano una **coda di lavoro con cursore** e tutta la finestra si riconfigura
  attorno alla prima (cambia perfino l'orario mostrato a destra), con `[1° step]`,
  `Indietro` e commit finale `Conferma tutti gli step`. La scoperta non è
  l'algoritmo — quello si sapeva — ma che **è esibibile**: una ricerca a catena si
  mostra a un umano un nodo per volta, perché a ogni nodo il costo è espresso in
  entità che l'utente conosce.
  **4) 🔑🔑 `Amenagement` e sostituzione sono la stessa cosa.** Il byte a offset 8
  di `COURS` è la **natura** dell'attività: 0 = annuale (1001), 1 = **consigli di
  classe** (62, e `NBCONSEILS = 62`), 2 = **141** che è esattamente
  `NBAMENAGEMENTS`, 4 = 20. Le 141 sono le attività con **un solo bit** nella
  maschera settimane. Quindi l'`Amenagement` **non è una tabella**: è una riga di
  `COURS` con la maschera ridotta. E i 161 record di `RELATIONCOURSSUBSTITUT` lo
  confermano: i sostituti sono **esattamente** le nature 2+4, gli originali
  **161/161 annuali**, e **159/161 cambiano solo il docente** a parità di classe
  (161/161) e aula (161/161). **Sostituire un docente e spostare un'ora per una
  settimana sono lo stesso atto sul modello dati** → [ADR-014](decisioni.md).
  Riguarda direttamente il **SaaS di sostituzioni già in produzione**: adottando
  questo modello i due sistemi condividono l'entità invece di scambiarsi dati.
  ⚠ Trappola evitata: le quattro tabelle `*AMENAGEMENT*` sono di **PRONOTE** (PDP/PEI)
  e tutte a zero record.
  **5) I «punti» non erano un punteggio.** Chiuso da due ricerche indipendenti e
  convergenti: sono i suffissi singolare/plurale di uno spinner, e la traduzione IT
  di `points` è **`pesi`** — punti di *peso didattico*. Cade l'ultima riserva: **in
  EDT non esiste alcuna funzione di costo numerica.** Il nostro modello dev'essere
  lessicografico.
  **6) Peso didattico, i numeri veri.** Osservato in UI: default **`1`** (non 0),
  `Totale = Peso × Durata`, e **quattro** tetti d'istituto — mattino, pomeriggio,
  giornata, settimana — **tutti a `nessuno`**. ⚠ Cioè in una base completa, risolta
  e messa a punto a mano, la funzione **è spenta**: ridimensiona
  [ADR-011](decisioni.md), che l'ha messa in v1. 🔑 E un dettaglio non cercato:
  il totale di classe (33) è **1 in meno** della somma delle materie (34), e la
  differenza è `ALTERNATIVA` — **il peso si misura per alunno, non per classe**, il
  che conferma sui dati il modello `_REL`/`_ALT` di `gruppi.md`.
  **7) Tre colonne che sembravano vincoli e non lo erano.** `P.P.` = *Proprietà di
  Piazzamento* (⚠ e `P.F.` non è una seconda colonna: è la stessa in inglese) =
  fascia fissa/variabile, già fuori scope; `Cours isolés` = **criterio di
  ottimizzazione**, con definizione operativa esatta e prova negativa solida (non
  compare in nessuna causale di diagnostica); `Interclasse` = **falso amico**,
  significa *intervallo*, ed è un vincolo hard a tre entità. Chiusi anche:
  l'**intervallo è un separatore, non una `Place`** (prova: i ranghi 2 e 4 sono fra
  i più occupati), lo **spostamento fra sedi è per coppia orientata**, e `Aree
  mobile` è il portale mobile di PRONOTE.
  **⛔ Una traduzione italiana dice il contrario.** `Memorizza le attività che
  saranno spostate` in francese è `Réinitialiser la famille des cours déplacés`.
  Avevo documentato la casella come opzione di tracciabilità: **sbagliato**,
  corretto. Nuova regola operativa: **quando IT e FR divergono, vince il francese**.
  → `docs/edt/glossario-it-fr.md`

- **2026-07-26** — **Il motore, il tempo e le risorse mancanti.** Fino a qui
  avevamo documentato bene **cosa EDT sa rappresentare** (dati e vincoli) e quasi
  nulla di **cosa EDT sa fare**. Questa passata colma il buco, rileggendo le 69 888
  stringhe di interfaccia per finestra invece che per parola chiave. Quattro
  documenti nuovi e una riscrittura.
  **1) Il motore visto dall'utente** (`motore-risoluzione.md`, riscritto). La
  generazione non è un bottone: il menu `Elabora` ha **cinque comandi di
  risoluzione**, usati in sequenza. Fra questi due mai immaginati: il **risolutore
  passo-passo**, che è una **ricerca a catena di espulsioni** (*"Trova una soluzione
  al massimo in %d step"*) con la griglia annotata slot per slot — *"in bianco, le
  collocazioni senza attività che creano problemi; in grigio, quelle che comportano
  lo spostamento di almeno un'altra attività"*, più il costo in vincoli e
  spostamenti; e **`Piazza e sistema`**, che impone una collocazione occupata e
  ripara il resto, con l'opzione *"Ignora i vincoli dell'attività selezionata"*.
  Trovata anche la **funzione obiettivo esposta**: i `Criteri di calcolo` sono una
  lista che l'utente sposta fra *considerati* e *ignorati*, e i massimi orari hanno
  **quattro modalità** (per settimana / per ciclo / media su 2 settimane con scarto
  massimo / media su 2 cicli). L'ottimizzazione ha **tre criteri ordinati** più una
  **`perdita di qualità tollerata`** per l'altra popolazione: il compromesso è
  sempre una **quota**, mai un peso. ⚠ Due correzioni al «tutto hard di default»:
  `Durata se possibile`, `Frequenza se possibile` e `Periodi se possibile` sono
  degradabilità dichiarate **sull'attività**.
  **2) La diagnostica** (`diagnostica.md`, nuovo). ~170 causali **nominate**: non
  «infeasible», ma *"La classe è già occupata in un'attività bloccata"*. Il perno è
  la distinzione **occupata-spostabile / occupata-bloccata**, che è ciò che rende
  possibile il risolutore a catena. Scoperto un attributo mai visto: le attività
  hanno una **priorità** (`Rendi prioritarie le attività`), distinta dal blocco.
  **Poi verificato in UI, e ha smentito una conclusione:** EDT **sì** che
  diagnostica e suggerisce, nell'`Analisi dei vincoli` (vedi sotto).
  **3) Il modello del tempo** (`tempo-e-calendario.md`, nuovo). Lo XSD conferma
  formalmente `place = giorno × 10 + rango`
  (`NombreJoursParCycle × NombreSequencesParJour × NombrePlacesParSequence`). Ma la
  scoperta strutturale è **`Fascia fissa` vs `Fascia variabile`**: *"EDT può
  modificare la collocazione dell'attività a seconda dei periodi"* — cioè una
  lezione non ha *una* collocazione, ne ha **una per periodo**. Inoltre gli
  **`Amenagement`** (eccezioni su una singola settimana) sono un **layer separato**
  sovrapposto all'orario annuale, e non sono un caso limite: 141 su 984 attività
  nella base demo. ⚠ Le settimane «A/B» **non esistono col quel nome**: il prodotto
  usa `Q1`/`Q2`, e trimestri e quadrimestri sono codificati con lo stesso
  meccanismo numeratore/denominatore.
  **4) Le risorse** (`risorse.md`, nuovo). La verifica di coerenza pre-piazzamento
  elenca **cinque risorse sullo stesso piano**: classi, docenti, aule, **personale**,
  **materiali** — le ultime due mai documentate. Il materiale ha una **quantità che
  è un vincolo hard** (*"%d quantità di questo materiale sono utilizzate
  simultaneamente"*), cioè lo stesso meccanismo della capacità simultanea dell'aula:
  **una risorsa cumulativa sola**, non due tabelle.
  **5) I moduli** (`moduli-e-scope.md`, nuovo). Delimitato il confine EDT ↔ PRONOTE
  (nuova convenzione, sopra). Le **sostituzioni non hanno un solver**: filtro
  multi-criterio + workflow, assegnazione manuale — quindi non c'è tecnologia da
  recuperare per il SaaS del committente, solo criteri (due buoni: «chi ha già un
  buco lì», «chi è stato liberato da un'assenza di classe»). Colloqui e consigli
  invece hanno un motore vero, e i consigli usano **lo stesso schema a tre stadi**
  dell'orario: è un **pattern architetturale del prodotto**, non una scelta
  specifica. E `Estrai` non è un filtro di vista ma una **selezione persistente e
  componibile** su cui piazzamento e ottimizzazione operano *esclusivamente*.
  **Un vincolo mai censito:** il **peso didattico** delle materie, con tetti per
  mattina/pomeriggio/giornata/settimana/ciclo, diagnostica e alleggerimento propri
  (`vincoli.md`). È il vincolo di carico cognitivo — facile da implementare, alto
  valore percepito, e nessuno lo fa.
  **Quattro punti aperti chiusi:** il vincolo normativo italiano **non esiste**
  (terza ricerca, negativa: nessuna delle 69 888 etichette nomina l'Italia in senso
  normativo); **TRCD/TRMD** è contabilità di bilancio su decreti francesi → fuori
  scope; gli **incarichi incidono** sul monte ore, con formula letterale, ma l'IMP
  no; i quattro valori **`Parties…Classe`** confermati da una seconda fonte.
  **Verificato subito in UI:** il **solver funziona anche senza registrazione** —
  tutte le voci di `Elabora` sono attive (la clausola francese di primo avvio non si
  applica a questa build). E il menu ha una **quarta sezione mai prevista**,
  `Analisi → Lancia l'analisi dei vincoli`: si analizza *prima* di calcolare.
  Le quattro sezioni sono **analizza → piazza → risolvi gli scarti → ottimizza**.
  🔑 **L'analisi dei vincoli è la funzione più preziosa trovata finora**, e ha
  **smentito** la conclusione «EDT non suggerisce quale vincolo allentare»: quella
  vale per il pannello `Alleggerimenti`, non per l'analisi. Cinque fasi
  selezionabili, di cui la quinta è `Controllo dell'insieme di attività non
  piazzabili` — la ricerca di **sottoinsiemi infattibili**, cioè un violatore di
  Hall, non il caso banale della singola attività bloccata. E una diagnosi reale
  osservata è strutturata in quattro riquadri: `Enunciato del problema` in italiano
  corrente, `Azioni che permettono di risolvere il problema`, `Dettaglio` con
  **l'aritmetica esplicita** (*"Classe 1B, LETTERE, 6 attività, durata da piazzare
  10h00, durata piazzabile 9h00 » 1h00 non potrà essere piazzata"*) e `Soluzione`
  con **la riga di vincolo colpevole mostrata in loco** (LETTERE incompatibile con
  sé stessa nella giornata). Più il pulsante `Estrai le materie, le risorse
  coinvolte e le attività`, che riversa la diagnosi nella selezione di lavoro.
  Osservate **tre forme di diagnosi** di natura crescente: un vincolo su una
  risorsa; **vincoli incrociati** di classe *e* docente, dove il riquadro
  `Soluzione` mostra affiancati due vincoli di famiglie diverse (incompatibilità
  di materia **e** giornate libere del docente) che sono innocui separatamente e
  fatali insieme; e infine la fase 5, che ha trovato un **violatore di Hall** vero —
  *11 docenti + 1 classe + 1 aula* nominati insieme, 25 attività, 33h di domanda
  contro 32h di *finestra di disponibilità comune*. Il riquadro `Soluzione` è
  **operativo**: tendine e griglia delle indisponibilità modificabili sul posto,
  poi `Rilancia la verifica` — si diagnostica e si ripara senza cambiare finestra.
  È la differenza fra `INFEASIBLE` e un prodotto: **da progettare come componente a
  sé**, perché è un conteggio di capienza, non richiede il solver.
  🔑 **E l'analisi è esatta, verificato.** Una base con 984/984 attività piazzate
  dichiarava comunque incoerenze; `Estrai → Attività che non rispettano i vincoli`
  ha restituito **21 attività su 984 (38h00)**, fra cui **entrambe** le diagnosi
  (EPICURO/LETTERE su 1B, DI MILETO/MATEMATICA su 1E). Quindi l'orario contiene
  davvero lezioni illegali piazzate a mano: **un orario valido non è un invariante**
  in EDT, la violazione è uno stato ammesso e interrogabile. Scelta di progetto da
  imitare. Quel comando apre prima una finestra `Criteri di estrazione` con le
  **dieci famiglie violabili** (dove ci sono `Mensa` e `Intervallo` — conferma che
  sono hard — ma ⚠ **mancano `Massimo di ore` e `Peso didattico`**, da chiarire).
  ⚠ Debolezza annotata: la chiusura (`Verifica terminata / Rimangono delle
  incoerenze`) **non riepiloga nulla** — chi ha scorso dieci problemi non può
  rivederli. → `docs/edt/diagnostica.md`, `docs/edt/vincoli.md`

- **2026-07-26** — **Verifica in UI sulla base di esempio del prodotto.** Copiata
  la base demo di EDT (completa e risolta: 18 aule, 187 parti, 3 raggruppamenti,
  984 attività piazzate) in `~/Desktop/EDT_COMPLETE/` e aperta in EDT per
  osservare ciò che nella base del Fermi non è osservabile. Ha **confermato**
  gran parte del lavoro sugli artefatti — le due griglie di vincoli mai viste
  esistono e i conteggi coincidono (11 tipi attività↔attività) — e ha
  **smentito due conclusioni**.
  **1) L'occupazione simultanea dell'aula non è il gruppo di aule.** È il campo
  `Numero di aule` (colonna `Qtà`), scalare e modificabile: `PALESTRE succ` ha
  `Qtà = 2` e **zero** sotto-aule. Le sotto-aule servono a nominare gli spazi, e
  portano una cascata di default (suffisso `(Gr.)`). Le stringhe descrivevano il
  caso tipico, non il modello — motivo per cui [ADR-009](decisioni.md) le
  mette in fondo alla gerarchia.
  **2) La `Tipologia` dell'aula non è il "tipo d'aula".** È un tag di dotazione a
  due livelli definito dall'utente (`Attrezzature → PC docente, Videoproiettore`),
  usato solo per raggruppare la lista. **Capienza, categoria e tipologia non sono
  vincoli**: la finestra `Aule disponibili` dichiara tre soli vincoli
  (`Sedi distaccate`, `Indisponibilità opzionali`, `Indisponibilità`). Il legame
  didattica↔aula esiste ma passa dalla **classe** (`Aula preferenziale`), non
  dalla materia — la relazione materia → tipo d'aula è **nostra estensione**.
  **Confermato in UI**, con testo letterale: i tre pennelli
  (`Indisponibilità` / `Indisponibilità opzionali` / `Preferenze`); i vincoli fra
  attività **nascono opzionali** (casella spuntata di default) e l'alleggerimento
  avviene *"durante il piazzamento delle attività scartate"* — cioè la strategia
  a due passate dedotta dal motore, scritta in una finestra; `Raggruppamenti` e
  `Gruppi` come righe distinte nella composizione dell'attività, che regge
  l'inversione terminologica IT↔FR.
  **Dai dati reali** della griglia dei vincoli di materia (19 righe su `2 A/R`):
  il caso d'uso dominante è la **materia con sé stessa** (non due ore di ARTE
  nello stesso giorno), non la relazione fra materie diverse — e la relazione è
  **orientata**, `A→B` e `B→A` sono record distinti.
  **Limite aggirato:** la tabella `SALLE` è cifrata nel file, ma le 18 aule sono
  perfettamente leggibili aprendo la base in EDT.
  **L'aiuto contestuale del prodotto** (pulsante `?` del pannello dei vincoli) ha
  chiuso le ultime due colonne oscure con sette casi d'uso: `Attività in gruppo`
  = ordine fra ore in gruppo e ore a classe intera — cioè i quattro valori
  `Parties…Classe` che erano aperti dal 26 luglio mattina — e `Conc. Imp.` =
  concatenazione imposta con ritardo massimo. Spiegata anche la discrepanza fra
  le 10 colonne della griglia e i 12 tipi delle stringhe: alcuni "tipi" sono
  **valori di parametro** della stessa colonna, non vincoli distinti.
  ⚠ Nota di metodo: **l'aiuto è in inglese anche nella build italiana**, quindi
  non è una fonte per la terminologia IT.
  **Le classi di concorso ci sono, ma come dato.** Nella base di riferimento
  italiana le discipline hanno per `Codice` le classi di concorso reali (`A-01`,
  `A-22`, `A-25`, `A-28`, `A-30`, `A-49`, `A-60`, `REL`, `SOST`): non è un campo
  dedicato, ma è **il posto dove EDT Italia si aspetta che la si metta**.
  Verificato però che il prodotto **non incorpora la tabella ministeriale** — i
  codici stanno solo nei dati della demo, non nei binari né in `TabellaSIDI.xml`.
  [ADR-002](decisioni.md) aggiornato di conseguenza: resta valido (relazione
  molti-a-molti in una tabella a sé), ma la nota "è nostra estensione" era troppo
  netta.
  **Il vincolo normativo italiano non si trova in UI**: battuti il pannello
  vincoli del docente (sette gruppi, tutti generici) e l'intero menu `Parametri`
  (28 voci). Probabile codice morto.

- **2026-07-26** — **Reverse engineering degli artefatti dell'installazione.**
  EDT gira sotto Wine su questa macchina: l'installazione e le basi dati sono
  leggibili come file. Da lì sono usciti quattro filoni, ora documentati, e una
  nuova convenzione di fonte (**📦**, [ADR-009](decisioni.md)).
  **1) Lo schema XSD ufficiale** `Partenaire_Index` V4.6 (`docs/edt/schema-scambio.md`):
  è un formato di *input* — trasporta anagrafica, struttura e attività da piazzare,
  **nessun vincolo e nessun piazzamento**. Ha chiuso da solo tre domande aperte:
  l'**allineamento genera l'attività complessa** (dichiarato testualmente), il
  monte ore per (piano, materia) è **tripartito** (classe intera / ridotta /
  sdoppiata — l'inferenza del 2026-07-09 era corretta), e la griglia oraria è a
  due livelli (sequenza → posizione) su un **ciclo** che può eccedere la settimana.
  **2) Le tabelle di lingua** del prodotto (`docs/edt/glossario-it-fr.md`): 69 888
  stringhe italiane allineate per chiave a francese e inglese. Hanno sciolto le
  **etichette troncate dei vincoli orari**, il nome del terzo pennello
  (**`Preferenze`**), `D.T.B.` (*Durata tollerata dei buchi*), `Mh/s` (= FR
  `Apport`, il monte ore contrattuale) e le colonne dei servizi. Hanno rivelato
  un'**inversione terminologica IT↔FR** che invalidava un'ipotesi di modello:
  «gruppo» in italiano traduce `partie`, non `groupe`.
  **3) Il modello interno e il motore** (`docs/edt/motore-risoluzione.md`):
  il piazzamento è una **pipeline a 7 fasi** con ottimizzazione separata, si
  ottimizza per docenti **o** per classi mai insieme, e i vincoli sono **tutti
  hard** con rilassamento esplicito **a quota** (non penalità). Sono emersi i
  vincoli di **materia** (12 tipi) e **attività↔attività** (11 tipi), mai
  osservati. Segnalato `TContrainteItalieProfReglementaire`: unico vincolo
  normativo italiano cablato nel motore, da indagare.
  **4) Le basi dati** (`docs/edt/formato-file.md`): il `.edt` è un contenitore
  Delphi non compresso con 744 tabelle auto-descrittive. Decodificata la
  collocazione (`place = giorno × 10 + rango`, validata contro `NBCOURSPLACES`).
  Due risultati sui dati: **IRC e attività alternativa sono due parti della stessa
  classe** (`_REL`/`_ALT`), non gruppi né compresenza — la pista della guida 📖 era
  sbagliata; e **indisponibilità e assenze condividono una sola tabella**,
  distinte dalla presenza della data.
  **Anomalia trovata e da sanare:** la base del Fermi dichiara `NBSALLES = 0` —
  **le aule non sono mai state inserite in EDT**, quindi `docs/edt/aule.md` e
  `data/liceo-fermi/aule.md` sono progetto, non osservazione. Marcato nei file.
  **Limite dichiarato:** la tabella `SALLE` del `.edt` è cifrata (con sei tabelle
  di dati personali), quindi i dati delle aule restano illeggibili.
  Materiale grezzo in `docs/edt/estratti/`.

- **2026-07-26** — Messi a indice tre elementi presenti nel repo ma mai
  documentati: il **prototipo solver** CP-SAT (`scripts/genera_orario.py`,
  `results.md`, commit `0ac80ac`), gli screenshot in `preparazione/` e
  `requirements.txt`. Deciso che il **prototipo resta parcheggiato** finché il
  reverse engineering di EDT non è completo: prima tutti i vincoli, poi il modello
  ([ADR-008](decisioni.md)). Corretta una voce "Aperto" stantia: le
  indisponibilità docente risultavano da osservare, ma `docs/edt/vincoli.md` le dà
  confermate in UI dal 2026-07-15; l'elenco dei vincoli ancora da osservare
  (classi, aule, risorse, materie) è ora esplicito.
- **2026-07-15** — L'utente ha fornito la **guida online ufficiale** di EDT; nuova
  convenzione "due fonti, marcate" (📖 = solo guida, da confermare in UI).
  Osservate in UI le viste 3 e 4 di Preparazione delle attività (**Assegnazione
  dei docenti ai servizi** e **Ripartizione dei docenti per classe**); dalla guida
  risolti: la **ripartizione puntuale** docente→classe avviene nella vista 3, da
  cui **"Crea le attività"** genera le attività e reindirizza a Orario (Preparazione
  non si usa più fino all'anno dopo); i **blocchi** sono la durata dell'attività;
  le **indisponibilità docente** sono rosso/giallo/verde + vincoli orari;
  **gruppi/raggruppamenti** creati automaticamente dalle attività complesse;
  `Nr. doc. suppl.` chiude il punto "docenti supplementari". La **Formazione
  classi** riguarda gli alunni nominativi → si salta senza anagrafica alunni.
  Eseguita la **ripartizione puntuale** sul Fermi (allineamenti cancellati per
  lavorare per classe, un titolare per cella, supplementari a zero): **tutti i
  18 docenti quadrano a `+/- = 0h00`** — verifica in sospeso chiusa.
  (`docs/edt/attivita.md`, `vincoli.md`, `gruppi.md`, `docenti.md`)
- **2026-07-15** — Anomalia su `Occ. prev.` (Conti/Marino a 21h, Ricci/Esposito a
  23h contro gli 8h/5h/3h attesi) risolta **reinserendo il dataset su base EDT
  vuota**: tutti i 18 valori ora coincidono con la regola documentata ("ore del
  bisogno una volta sola"). Era stato corrotto del vecchio file (plausibile residuo
  dell'inversione STO/SCI), non un errore di semantica. Lezione: dopo correzioni al
  quadro orario, cancellare e rifare l'allineamento (`docs/edt/attivita.md`).
- **2026-07-09** — Documentata la catena previsionale **piani di studi → classi
  previsionali → bisogni** (`docs/edt/piani-di-studi.md`, `classi.md`,
  `bisogni-previsionali.md`; dataset in `data/liceo-fermi/piani-di-studi.md`).
  Scoperte: il quadro orario vive sui **servizi del piano** e cascata sulle classi;
  il **bisogno** è calcolato da `ore × classi necessarie` (dagli effettivi
  previsti); il Totale dei bisogni del Fermi dà **288h00**, quadratura verificata
  da EDT.
- **2026-07-09** — Documentata la scheda **Docente** di EDT campo per campo
  (`docs/edt/docenti.md`). Due scoperte: EDT separa **capacità** (materie insegnabili),
  **preferenza** (materia preferenziale) e **assegnazione** (cattedra), e quattro campi
  (`Occ. prev.`, `HS Prev.`, `+/-`, `Extra`) sono **calcolati, non inseriti**. Nuovi
  ADR-006 (capacità ≠ assegnazione) e ADR-007 (i campi previsionali non si memorizzano).
- **2026-07-09** — Migrazione su Claude Code. Il documento di partenza
  `docs/edt/_stato-attuale.md` è stato decomposto nella struttura definitiva:
  entità in `docs/edt/`, decisioni in `docs/decisioni.md`, dataset in
  `data/liceo-fermi/`. Chiarita una distinzione: nella tabella Discipline il campo
  "Classe di concorso" è nostra mappatura, non un campo EDT osservato. Il documento
  di partenza è stato rimosso a decomposizione completata (contenuto interamente
  ridistribuito).
