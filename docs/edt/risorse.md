# EDT — Le risorse di piazzamento

> Fonte 📦: etichette di interfaccia dai binari (69 888 stringhe IT/FR/EN).
> ⚠ Binario condiviso con PRONOTE: qui compare solo ciò che è riconducibile al
> piazzamento. Nessuna di queste schede è stata osservata in UI.

## 🔑 Le risorse sono cinque, sullo stesso piano

Prova diretta: il pannello di **verifica della coerenza della base**, che gira prima
del piazzamento, ha una fase per risorsa — e sono esattamente cinque:

| Fase | IT |
|---|---|
| `EtapeOccupationDesClasses` | Controllo dell'occupazione delle **classi** |
| `EtapeOccupationDesProfesseurs` | Controllo dell'occupazione dei **docenti** |
| `EtapeOccupationDesSalles` | Controllo dell'occupazione delle **aule** |
| `EtapeOccupationDesPersonnels` | Controllo dell'occupazione del **personale** |
| `EtapeOccupationDesMateriels` | Controllo dell'occupazione dei **materiali** |

Ognuna con lo stesso testo: *"EDT verifica che tutte le attività possano essere
piazzate tenendo conto delle indisponibilità e dei vincoli di [risorsa]"*.

Conferma indipendente dalla finestra del risolutore, dove l'opzione «piazza anche
sulle indisponibilità opzionali» si declina **sulle stesse cinque**: `dei docenti`,
`delle classi`, `delle aule`, `dei materiali`, `del personale`.

**Non c'è nessuna fase per alunni o responsabili.** Non sono risorse del piazzamento
orario.

Avevamo documentato a fondo tre risorse su cinque. Le due mancanti sono qui.

---

## Il personale

### È una risorsa piazzabile, non un'anagrafica

Ha lo stesso identico corredo delle altre risorse:

- `Il personale ha una indisponibilità` / `...un'indisponibilità opzionale`
- `Il personale è già occupato in un'attività`
- le varianti `CoursPrioritaire` / `NonPrioritaire`
- `Autorizza al personale l'inserimento di indisponibilità` — può dichiararsele da
  sé, come i docenti

### Ha attività proprie

Prova diretta, dal messaggio di conferma:

> *"Volete anche aggiornare le **attività di accompagnamento** del personale
> interessato dalle vostre modifiche?"*

E, ancora più netto, sul legame incarico → attività:

> *"Quando si rimuove un incarico dai docenti/personale, lo si rimuove anche dalle
> loro **attività**"*

Gli incarichi generano quindi **attività schedulate**, non solo righe contabili.

### I ruoli

`Type_GenreFonctionPersonnel`: **Educatore** (FR *Accompagnant*), Amministrativo,
Segreteria (Direzione / Vita Scolastica), Sorveglianza, Gestione, Medico,
Doposcuola, Psicologo, Sociale, Tutor, Admin Comune, Comune.

**Per noi.** Il ruolo che conta è l'**Educatore/Accompagnante**: nella scuola
italiana è l'assistente all'autonomia e comunicazione, che affianca un alunno con
disabilità e il cui orario **deve** stare in griglia insieme a quello della classe.
È un caso d'uso reale e frequente, non un'esoticità francese.

⚠ La gran parte delle stringhe `ScoGlossairePersonnel` (chat, SMS, sanzioni,
webspace) è di **PRONOTE**. Solo accompagnamento, indisponibilità e partecipazione
ai consigli sono attribuibili a EDT.

---

## I materiali

### Modellati come le aule

Stessa finestra (`Aule e materiali`), vista `Orario` propria, stesso meccanismo di
indisponibilità hard/opzionale.

Colonne: `Nome`, **`Quantità`** (`Nb. occurrences`), `Gestori` (docente o personale
responsabile, destinatario delle email), `Informazioni libere`, `Picco
d'occupazione`, `Prenotabile da` (docenti/personale, per settimana o per **ciclo**),
`Limite di prenotazione` (giorni di preavviso).

⚠ A differenza delle aule, **nessuna categoria né tipologia**.

### 🔑 La quantità è un vincolo hard, non una prenotazione informativa

Prova diretta — il sistema **impedisce** di ridurre la quantità sotto l'uso
simultaneo già piazzato:

> *"Il materiale %s non può essere modificato poiché %d quantità di questo materiale
> sono utilizzate **simultaneamente**"*

E l'attività può chiederne più di uno:

> *"Per il materiale, quantità da inserire nelle attività / quantità disponibile"*

Cioè: *«questa lezione richiede 5 portatili»*, verificato contro il totale
disponibile.

**Per noi.** È lo **stesso identico meccanismo** della capacità simultanea dell'aula
(il campo `Qtà`, vedi [aule.md](aule.md)): una risorsa con capacità intera > 1,
consumata da N attività contemporanee. Modellandolo una volta sola come *risorsa
cumulativa*, aule e materiali diventano lo stesso caso — e in CP-SAT è letteralmente
un vincolo `cumulative`. Vale la pena unificarli nello schema invece di scrivere due
tabelle simili.

---

## Gli incarichi del docente

### 🔑 Chiuso: sì, incidono sul monte ore

Era una domanda aperta dal 2026-07-09. La formula è scritta in chiaro nel prodotto:

> **`Ore supplementari = Durata/Coeff. + Extra − Monte ore`**
> (FR: *Heures supplémentaires = Durée/Pond. + ARE − Heures étab.*)

e in variante estesa:

> **`(H.att + H.pond + ACP + CC) − Monte ore`**
> (FR: *(H.enseignées + H.pond + ACP + CSD) − Apport*)

| Termine | Cos'è | Effetto |
|---|---|---|
| **Monte ore** (`Apport`) | il monte ore contrattuale, già in [docenti.md](docenti.md) | base |
| **ARE / Extra (Ist.)** | *"Attività extra Insegnamento a carico dell'istituto"* | **somma** |
| **ACP** | Attività complementari personali | **somma** |
| **ARA / Extra (Uff. scol.)** | esonero a livello di Ufficio Scolastico | **sottrae** |
| **CC / CSD** | Controllo del servizio | aggiustamento |

Conferma incrociata: *"Ore dovute all'istituto: Monte ore − Extra − CC"*.

### L'IMP invece no — ed è francese

L'**IMP** (*Indemnité pour Mission Particulière*) è un **compenso monetario
annuale**, tracciato a parte (`Indennità per missione particolare (IMP) - pagamento
annuale`), con la sua contabilità `Dotazione IMP − Bisogni IMP = Scarto`. **Non entra
nella formula oraria.**

E la sua origine è dichiarata: il codice incarichi serve per *"les missions réalisées
dans le cadre du **PACTE enseignant**"* — riforma francese del 2023.

**Conclusione: distinguere due cose.** Gli incarichi che **occupano ore in griglia**
(accompagnamento, attività complementari) ci servono. La contabilità
indennità/dotazione (IMP, HSA, TRMD) è un impianto **normativo francese** ed è
**fuori scope** — vedi sotto.

---

## 🔑 Chiuso: TRCD/TRMD è fuori scope

Era aperto dal 2026-07-09 («lo scioglimento della sigla non esiste in nessuna delle
sei lingue»). Ora è chiaro **cosa fa**, il che basta a decidere.

`TRMD` è una vista di **pianificazione di bilancio**, non di orario. Confronta:

| Colonna | Significato |
|---|---|
| `Dotazione` | le ore che il ministero assegna alla scuola |
| `Bisogni` | le ore che servono, dai servizi previsionali |
| `Scarto` | Dotazione − Bisogni |

su quattro righe: `Globale`, `Ore posto`, `HSA` (ore supplementari annuali), `IMP`.
E segnala il *"Superamento dei plafond regolamentari (D. 2014-940 et 941)"* — due
decreti **francesi**.

`TRCD` è solo la resa italiana della sigla; la sostanza non è stata tradotta perché
non c'è nulla da tradurre: **non esiste un equivalente italiano** di questo
meccanismo (in Italia l'organico e il FIS seguono logiche diverse).

**Decisione: fuori scope, dichiarato.** Non è una funzionalità di generazione
dell'orario ed è legata a normativa estera.

---

## Alunni e responsabili — fuori dal piazzamento

Non compaiono in nessuna fase di verifica della coerenza. Entrano in gioco solo in:

- l'**alunno dissociato** (*élève détaché*), meccanismo della formazione classi con
  anagrafica nominativa — già dichiarata fuori scope ([classi.md](classi.md));
- i **colloqui e consigli di classe**, che sono un altro problema di scheduling
  ([moduli-e-scope.md](moduli-e-scope.md)).

---

## Colonne mai viste che rivelano attributi del modello

Dalla famiglia `UtilitairesEdt_ColonnesRessources` (591 stringhe). Selezione di ciò
che **non** avevamo documentato e che riguarda il piazzamento:

⚠ Due sigle che a prima vista sembravano nuove **non lo sono**: `Mp` è il badge
**P** (`Massimo di ore di presenza`) e `PLG` è il badge **G**
(`Giorni e ½ giornate libere`), entrambi già osservati nel pannello vincoli del
docente ([vincoli.md](vincoli.md)). Sono i nomi delle colonne corrispondenti, non
vincoli ulteriori.

| Colonna | Cosa suggerisce | Priorità |
|---|---|---|
| **`ProfHeuresP1/P2/P3`** — Priorità 1/2/3 | un sistema di priorità **numerato** sul docente. ⚠ Molto probabilmente sono le **priorità di sostituzione** (`Priorità 1/2/3` per docente × fascia, vedi [moduli-e-scope.md](moduli-e-scope.md)), non un parametro del piazzamento — da confermare | media |
| ~~**`Fractionnable`** (P.P. / P.F.)~~ | **chiuso**: è `P.P.` = *Proprietà di Piazzamento* = `Fascia fissa`/`variabile`; `P.F.` è la stessa colonna in inglese. Non un vincolo nuovo → [moduli-e-scope.md](moduli-e-scope.md) | — |
| ~~**`Cours isolés`**~~ | **chiuso**: criterio di ottimizzazione + contatore, **mai un vincolo** → [vincoli.md](vincoli.md) | — |
| ~~**`Interclasse`**~~ | **chiuso**: falso amico, significa *intervallo/ricreazione*; vincolo hard a tre entità → [vincoli.md](vincoli.md) | — |
| **`Retard de service`** — Permessi / arretrato di servizio | debito/credito ore da recuperare | bassa |
| `Salle NbProf` / `NomsProfs` | quanti e quali docenti usano un'aula | bassa — utile per **inferire** l'aula di fatto dedicata a una disciplina, senza dichiararla |
| `Rempliss. Max/Min/Moy` | riempimento dell'aula | bassa — probabilmente solo diagnostico |
| `Prof NatureSupport` / `ModAffectation` / `Code/Echelon/DateGrade` | stato giuridico e carriera, terminologia HR francese | **fuori scope** |

## 🔑 Le cinque risorse, viste sui dati (2026-07-26)

Le cinque risorse erano state ricostruite dalle stringhe **senza vederle mai usate**.
Il pannello di riepilogo di una selezione di 27 attività le ha mostrate tutte,
contate:

```
Materie 10   ·   Docenti 10   ·   Classi 1 (1 A/R: 27)
Raggruppamenti 0   ·   Gruppi 0   ·   Alunni dissociati 0
Aule 1        LAB. LINGUISTICO  1
Personale 1   Guglielmi Marco   3
Materiali 3   PC portatile      4
```

**Personale e materiali non sono teoria**: in una base reale esistono e sono
agganciati alle attività. Lo stesso riquadro riappare nel risolutore passo-passo,
dove le risorse **in conflitto diventano rosse** — quindi il conteggio per risorsa è
una struttura ricorrente del prodotto, non una vista isolata.

### 🔑 L'aula è l'eccezione, non un attributo di ogni lezione

Su 27 attività di una classe intera, **una sola ha un'aula** (il laboratorio
linguistico). Nella base di esempio le aule si assegnano solo dove servono davvero —
laboratorio, palestra — e tutto il resto vive implicitamente nell'aula della classe
(`Aula preferenziale`, vedi [aule.md](aule.md)).

Indicazione forte per il modello: **l'aula è un'eccezione dichiarata**, non una
colonna obbligatoria dell'attività. Un modello che pretende un'aula per ogni lezione
si crea da solo un problema di assegnazione che la scuola non ha.

## Cosa resta da verificare in UI

1. **Esiste una scheda `Personale` separata** da quella docente, con lo stesso
   pannello a tre pennelli? (base demo, modulo `Personale`)
2. **Attività di accompagnamento**: nella base demo ci sono educatori con attività
   in griglia? Conferma che l'Educatore genera vere lezioni.
3. **Materiali**: la finestra `Aule e materiali`, e se possibile la prova pratica —
   materiale con quantità 2 su 3 attività simultanee: il piazzamento lo rifiuta?
4. **`ProfHeuresP1/P2/P3`**: esiste un pannello «Priorità» sulla scheda docente, ed
   è quello delle sostituzioni o del piazzamento?
5. ~~`Fractionnable` / `Cours isolés` / `Interclasse`~~ — **chiusi il 2026-07-26**,
   vedi la tabella sopra. Nessuno dei tre era un vincolo non censito.
6. Che in EDT Italia le voci **IMP / PACTE / TRMD** siano assenti o disattivate —
   chiuderebbe formalmente il punto.
