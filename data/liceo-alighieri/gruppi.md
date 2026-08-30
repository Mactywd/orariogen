# Gruppi — le quattro forme di sdoppiamento

> 🔑 **E dall'ondata 6 ce n'è una quinta, che non è uno sdoppiamento**: l'ora
> **quindicinale** del 5B, due attività a maschere complementari. È l'unica
> forma che **non costa un'ora** al docente — in ogni settimana ne è attiva
> una sola — e la differenza fra *sdoppiare* e *alternare* è tutta nella
> maschera. Vedi [quindicinale-e-quote.md](quindicinale-e-quote.md).

🔑 Sono la voce ✅ di scope v1 ([ADR-013](../../docs/decisioni.md)) che **nessun
dataset rappresentava**: sul Fermi `ClassPartition`, `ClassPart` e `Group` sono
tre tabelle vuote, e i loro test girano su fixture sintetiche da poche righe.
Qui stanno dentro una scuola intera, insieme, e ognuna ha una forma diversa —
il che è il punto: quattro righe della stessa forma proverebbero una cosa sola.

⚠ **Attenzione all'inversione terminologica IT↔FR**: `classe → suddivisione →
gruppo`, con il `raggruppamento` trasversale a più classi. Vedi
[glossario-it-fr.md](../../docs/edt/glossario-it-fr.md).

| Forma | Dove | Partizione | Parti |
|---|---|---|---|
| IRC / alternativa | tutte e 12 | `RELIGIONE` | `_REL`, `_ALT` |
| Classe articolata | 2C | `ARTICOLAZIONE` | `2C_ORD`, `2C_APP` |
| Effettivo ridotto | 3A **e 4A** | `LABSCI` ×2 | `3A_G1`/`3A_G2`, `4A_G1`/`4A_G2` |
| Raggruppamento trasversale | 1A + 1B | `INGLESE` ×2 | `ING1-BASE`, `ING1-AVANZ` |

Totale: **17 partizioni, 34 parti, 2 raggruppamenti**.

⚠ **Il secondo laboratorio è dell'ondata 4, e la ragione non è di
anagrafica.** I quattro tipi `PARTS_*` dell'asse Relazione vogliono quattro
portatori che non si implichino a vicenda, e con una sola classe sdoppiata non
esistono: un ordine per giornata su un'unità rende veri per costruzione gli
omogenei su ogni sua sotto-unità. Vedi [relazioni.md](relazioni.md).

## 1. IRC e attività alternativa — su tutte e dodici

`docs/edt/gruppi.md` lo documenta e i dati lo confermano: **due parti della
stessa classe** (`_REL` / `_ALT`), non due gruppi e non una compresenza.

🔑 **E il piano deve dichiararlo.** Le due righe di servizio portano
`election_group = "RELIGIONE"` ([ADR-020](../../docs/decisioni.md)): di quelle
due un alunno ne segue **una**. Senza il dato la copertura darebbe due
scostamenti su ogni classe italiana, ed è il comportamento giusto — che
l'alunno ne segua una non è deducibile da nessuna proprietà dell'orario.

⚠ **Conseguenza sui totali**: il piano somma 28 ore dove l'alunno ne fa 27. Il
piano è un **catalogo**, non un curriculum, e questa è la riga del dataset che
lo dimostra.

L'alternativa la insegna **R02** (12 ore), su una materia la cui disciplina non
ha alcuna classe di concorso — che è la verità: l'alternativa la copre chi ha
ore disponibili.

## 2. La classe articolata 2C — la condizione 3 di ADR-015

Metà classe prosegue lo scientifico ordinario, metà segue **Scienze
Applicate**: niente latino, tre ore di informatica al suo posto. È il caso
reale delle scuole piccole, ed è la condizione che
[`scope-v1.md`](../../docs/scope-v1.md) dichiarava *«da verificare presto, non
a modello finito»*.

- `2C_ORD` **eredita** il piano della classe (`study_plan = NULL`, ADR-003);
- `2C_APP` porta un piano **proprio**, `SAP2`.

Le ore comuni — italiano, inglese, storia e geografia, matematica, fisica,
scienze, disegno, motorie — sono dichiarate in **entrambi** i piani, perché
sono ore che entrambe le popolazioni ricevono. Ed è necessario: la copertura
misura per **atomo**, e un atomo che riceve una materia assente dal proprio
piano è uno scostamento.

Informatica la insegna **I01**, tre ore. ⚠ È uno **spezzone**, ed è ciò che
un'articolata produce davvero in una scuola piccola.

## 3. Lo sdoppiamento a effettivo ridotto — 3A e 4A

Tre ore di scienze: **due a classe intera, una a metà classe** in laboratorio.
Due volte, in 3A (ondata 2) e in 4A (ondata 4), con la stessa forma.

🔑 **E il docente quell'ora la fa due volte.** N01 passa da 17 a 19 ore mentre
i quadri orari di 3A e 4A non cambiano di un minuto: è il costo dello sdoppiamento,
ed è il motivo per cui il monte ore di un docente **non si legge dal quadro
orario**. È anche ciò che dà un senso ad `Al./Rid.` — i due gruppi da 13 stanno
sotto il tetto d'istituto di 15, che le materie ereditano (ADR-003).

⚠ **`Sdop.` (`Service.split_minutes`) resta invece `NULL`**, e non per
dimenticanza: la semantica del monte ore tripartito è
[O3](../../docs/todo.md), un esperimento ancora da fare in EDT. Riempirlo qui
sarebbe inventare un campo, che è ciò che la convenzione della casa vieta —
lo sdoppiamento è nelle attività e nelle parti, dove è osservato.

## 4. Il raggruppamento trasversale — 1A + 1B

I livelli di inglese delle due prime che si mescolano: `ING1-BASE` prende
`1A_ING_B` e `1B_ING_B`, `ING1-AVANZ` gli altri due. Tre ore ciascuno, E01 sul
base ed E02 sull'avanzato.

🔑 **È il caso che rompe la decomposizione per classe** — la conseguenza che
ADR-013 dichiara e che nessun dataset aveva mai messo alla prova. Un'ora del
livello base occupa alunni di 1A *e* di 1B: le due classi non si possono più
risolvere separatamente.

⚠ **Non attraversa le sedi, deliberatamente.** Un raggruppamento fra 1A e 1C
chiederebbe agli stessi alunni di stare in due edifici alla stessa ora. Un
banco che chiede l'impossibile misura la propria incoerenza, non il motore.

⚠ **E la contabilità della cattedra ci sta stretta.** `TeachingAssignment` ha
una FK alla **classe**, quindi le tre ore di E01 sul livello base sono
registrate su 1A e quelle di E02 su 1B, mentre entrambi insegnano ad alunni
delle due. Il monte ore quadra e l'orario è corretto; è la riga di bilancio a
essere una finzione. Non è un difetto trovato dall'orario — è una forma che il
nostro modello non ha, e va scritta perché non venga scoperta come sorpresa.

## 🔑 L'allineamento: il difetto dell'ondata 2, chiuso il 2026-08-31

📦 Lo XSD `Partenaire_Index` dichiara che **l'allineamento genera l'attività
complessa**: in EDT le attività allineate sono **una** collocazione. Da noi
`Activity.alignment_ident` è stato per mesi un campo che **nessun builder e
nessun checker leggeva**, e la misura sul solve completo era impietosa: dei 16
allineamenti dichiarati, **14 uscivano senza una sola coincidenza** — i due
livelli d'inglese su sei celle diverse, il latino e l'informatica della 2C mai
in parallelo, cioè metà classe a scuola in un'ora in cui non ha lezione.

È **L5**, ed è chiuso: `structural:alignment` è il ventottesimo builder, e il
checker gemello nomina la coppia in disaccordo (`alignment_split`). Il gruppo
si piazza **tutto sulla stessa cella o niente**, che è ciò che «una sola
attività complessa» significa; se il dominio comune è vuoto il gruppo si
scarta, e non rende infattibile il modello.

### ⚠ E leggendo il campo si è visto che il dataset diceva due cose false

Nessuna delle due era una svista di battitura: erano due letture sbagliate
della stessa riga dello XSD, invisibili finché nessuno la leggeva.

1. **Sdoppiare non è allineare.** L'ondata 2 aveva scritto `3A-LABSCI` sulle
   due metà del laboratorio. Ma le due metà hanno lo **stesso docente** e non
   sono mai simultanee — il docente quell'ora la fa **due volte**, ed è il
   costo dello sdoppiamento. Allinearle è insoddisfacibile per costruzione.
   È lo stesso argomento con cui l'ondata 6 aveva rifiutato di allineare
   l'ora quindicinale: *alternare non è allineare*. Le due righe ora hanno
   l'allineamento vuoto.
2. **Un ident per attività complessa, non per coppia di servizi.** 📦 *«il
   convient de définir autant d'alignements que de cours complexes
   souhaités»*: tre ore di latino parallele a tre di informatica sono **tre**
   attività complesse, non una da sei ore. Con un ident solo il modello le
   fondeva tutte e sei sulla stessa fascia, e ne scartava quattro. Ora la
   tabella dichiara l'ident della **famiglia** e il fixture lo numera per ora
   (`2C-ART-1`, `-2`, `-3`).

Dopo le due correzioni: **36 attività allineate, 18 ident**, e il solve chiude
`OPTIMAL` a zero scarti con **18 gruppi su 18 coincidenti**.

### ⚠ E ha fatto emergere una terza incoerenza, che era del dato e non del codice

L'articolata dichiara latino e informatica *nelle stesse tre ore*. Onorato
l'allineamento, quelle tre ore sono le tre di RICCI — lo spezzone di
informatica, tre ore in un pomeriggio solo — e tre ore di latino nello stesso
pomeriggio pesano **6** contro il tetto di **5** del peso didattico. Tre
affermazioni del banco, ciascuna deliberata, erano insieme impossibili.

Lo spezzone di RICCI è ora su **due** pomeriggi — due fasce il mercoledì e una
il venerdì. Il bordo non si è mosso: tre fasce libere per tre ore, e una fascia
rossa in più e l'orario non esiste (la tacca dell'ondata 3 si è spostata da
`(2, 7)` a `(4, 7)`).
