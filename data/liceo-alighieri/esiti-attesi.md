# Esiti attesi

🔑 **Questo file si scrive prima di eseguire.** Il rischio di un banco è
preciso e fatale: lo si aggiusta finché è verde, e a quel punto non prova più
niente. Il Fermi si difende con `vincoli-attesi.md`, dove i conflitti sono
scritti *prima* di lanciare il solver; l'Alighieri eredita la disciplina,
rinforzata da quattro regole (spec §6):

1. L'esito si scrive **prima** della prima esecuzione, dal disegno.
2. Ogni riga di vincolo dichiara la famiglia che deve far scattare.
3. Se l'osservato smentisce l'atteso, si scrive **quale delle due** era
   sbagliata — e se era l'attesa, si dice perché. Non si riscrive l'attesa in
   silenzio.
4. **Verifica per mutazione**: togliere la riga di una famiglia deve cambiare
   l'orario. Una famiglia la cui rimozione non cambia niente non è esercitata,
   è solo *presente* — ed è il modo in cui un dataset «completo» può essere
   vuoto.

⚠ Il punto 4 è il vero contratto. Senza, «l'Alighieri copre tutte le famiglie»
significa solo «l'Alighieri ha righe in tutte le tabelle».

E ha una forma economica e automatica che sta a monte della mutazione: la
**sonda** ([`tests/sonda.py`](../../tests/sonda.py)), che avvolge `restrict` e
`build` di ogni builder e conta celle tolte e constraint postati. Non
sostituisce la mutazione — un builder può postare un vincolo vacuo — ma prende
in un secondo il caso «la riga c'è e il builder non la vede», che sul Fermi
vale ventiquattro builder su ventisette.

---

## Ondata 1 — l'anagrafica

Qui l'atteso è **aritmetico**: quadri orari, cattedre e attività devono dire lo
stesso numero. Le cinque quantità qui sotto sono state derivate dal disegno
prima di scrivere il codice che le costruisce, e confermate al primo giro.

| Grandezza | Atteso | Osservato |
|---|---:|---|
| Ore-classe | 345 | ✅ |
| Attività | 323 | ✅ |
| Righe di servizio | 107 | ✅ |
| Assegnazioni docente × classe | 127 | ✅ |
| Cattedre a `+/- = 0` | 21 su 21 | ✅ |

E l'atteso sul **motore**:

| | Atteso | Osservato |
|---|---|---|
| `analyze_capacity` | nessun verdetto negativo | ✅ |
| `check_schedule` su orario vuoto | solo `activity_unplaced`, 323 volte | ✅ |
| Fase 1 | `OPTIMAL`, zero scarti | ✅ 2,5 s, 13 583 var, 5 493 constraint |
| Fase 2 | 66 richieste su 66, zero rinunce | ✅ 0,2 s |
| Sonda | 4 builder su 27 | ✅ occupation, room_pool, site_transition, grid |

⚠ **Un atteso che l'ondata 1 non pretende.** La spec (§4) chiede un dataset
*stretto*: `OPTIMAL` con zero scarti, ma una sola aula o un solo docente in
meno e comincia a scartare. Senza una riga di vincolo la tensione non c'è, e
fingere il contrario sarebbe il primo modo di aggiustare il banco. Il criterio
si verifica all'ondata 7, quando le famiglie ci sono tutte.

## Ondate 2–7

Da scrivere prima di ciascuna, nell'ordine della spec §9: sdoppiamenti, asse
Cardinalità, asse Relazione, sedi e peso didattico, quote e criteri di qualità,
criterio di accettazione.
