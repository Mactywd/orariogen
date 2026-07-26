# Estratti grezzi dagli artefatti di EDT

> ⚠ **Questo non è documentazione.** È il materiale di lavoro da cui è stata
> ricavata la documentazione in `docs/edt/`. Non è curato, non segue le
> convenzioni del progetto, e in alcuni punti è più verboso o più incerto di
> quanto sia finito nei documenti entità.
>
> **La fonte autorevole per il progetto resta `docs/edt/`.** Questi file servono
> a: (a) non dover rifare l'estrazione, (b) verificare un'affermazione risalendo
> alla prova, (c) recuperare dettagli che non è valso la pena curare subito.

Fonte 📦 — vedi [ADR-009](../../decisioni.md) per la gerarchia di autorevolezza.
Estratti il 2026-07-26 da EDT Monoposto 2026.1.3 installato sotto Wine.

## Contenuto

| File | Cosa contiene | Documento curato corrispondente |
|---|---|---|
| `xsd-partenaire-index-v46.md` | Dump strutturato dello schema XSD ufficiale: elementi, attributi, tipi, cardinalità, annotazioni dell'autore | [`schema-scambio.md`](../schema-scambio.md) |
| `sidi-quadri-licei.md` | I 61 quadri materie ministeriali per indirizzo di liceo × anno, con codici SIDI | [`nomenclatura-sidi.md`](../nomenclatura-sidi.md) |
| `catalogo-tipi-interni.md` | Catalogo del modello dati interno: 1039 classi persistenti, 227 tabelle di relazione, 2565 enumerazioni, raggruppate per dominio | [`motore-risoluzione.md`](../motore-risoluzione.md), vari |
| `stringhe-localizzazione.md` | Etichette di interfaccia IT/FR/EN allineate per chiave, per tema (vincoli, aule, gruppi, servizi, docente) | [`glossario-it-fr.md`](../glossario-it-fr.md), [`vincoli.md`](../vincoli.md) |
| `formato-edt-analisi.md` | Reverse engineering del formato binario `.edt`: contenitore, tabelle, record `COURS`, codifica della collocazione | [`formato-file.md`](../formato-file.md) |
| `motore-diagnostica.md` | Il catalogo delle causali di mancato piazzamento, il risolutore automatico e quello passo-passo, la modalità diagnostica | [`diagnostica.md`](../diagnostica.md), [`motore-risoluzione.md`](../motore-risoluzione.md) |
| `modello-del-tempo.md` | Griglia oraria, suddivisioni sub-orarie, intervalli, mezza giornata, mensa, calendario, periodi, periodicità, sedi | [`tempo-e-calendario.md`](../tempo-e-calendario.md) |
| `risorse-e-colonne.md` | Personale, materiali, incarichi; le ~590 colonne visualizzabili sulle risorse | [`risorse.md`](../risorse.md) |
| `moduli-adiacenti.md` | Sostituzioni, colloqui, consigli di classe, `Estrai`, import/export; confine EDT ↔ PRONOTE | [`moduli-e-scope.md`](../moduli-e-scope.md) |
| `inventario-vincoli.md` · `inventario-struttura.md` · `inventario-risorse-motore.md` | **L'inventario piatto delle funzionalità** censite dalla documentazione: 308 voci con costo, dipendenze e valore percepito. ⚠ Non sono estratti da EDT ma **dai nostri documenti**: sono il materiale grezzo della decisione di scope | [`scope-v1.md`](../../scope-v1.md) |
| `cascata-default.md` | Quanto è estesa l'ereditarietà dei default: il marcatore `(Gr.)`, il vocabolario, il caso `Mh/s` | [ADR-003](../../decisioni.md), [`docenti.md`](../docenti.md), [`aule.md`](../aule.md) |
| `vincoli-aperti.md` | `Fractionnable`/`P.P.`, `Cours isolés`, `Interclasse`, scala e default del peso didattico | [`vincoli.md`](../vincoli.md), [`moduli-e-scope.md`](../moduli-e-scope.md) |
| `motore-punti-aperti.md` | I «punti» degli alleggerimenti; `Amenagement` ≡ sostituzione sul modello dati; aree mobile, intervalli, spostamento fra sedi | [`formato-file.md`](../formato-file.md), [`motore-risoluzione.md`](../motore-risoluzione.md), [`tempo-e-calendario.md`](../tempo-e-calendario.md) |
| `parse_xsd.py` | Lo script che produce il dump dello schema | — |
| `extract_strings.py` | Lo script che riproduce `it_fr_en.tsv` dalle tabelle di lingua della DLL | — |

## Come rigenerare

Lo script degli XSD:

```bash
python3 docs/edt/estratti/parse_xsd.py \
  ~/.wine/drive_c/"Program Files"/"Index Education"/"EDT 2026"/Monoposto/Schema/Partenaire_Index.xsd
```

Per gli altri, il metodo è descritto dentro ciascun file (sezione *Metodo* o
*Come rifare l'estrazione*). In sintesi:

- **Stringhe di interfaccia**: sono blocchi XML UTF-8 in chiaro dentro
  `EDT Monoposto.dll`, nella forma `<chaine numero="…" cle="…">testo</chaine>`,
  sei lingue allineate per chiave.
- **Tipi interni**: RTTI Delphi in `EDT Monoposto.exe`. Attenzione: i nomi sono
  shortstring (byte di lunghezza + caratteri), quindi un `grep` ingenuo produce
  ~100 varianti fasulle — filtrare sulle occorrenze dove il byte precedente è la
  lunghezza del nome.
- **Formato `.edt`**: contenitore Delphi non compresso, header XML in chiaro a
  `0x4B0`, magic di sezione `AB CD EF FF`, tabelle auto-descrittive.

## Nota

Tutte le estrazioni sono state fatte in **sola lettura**. Nessun file
dell'installazione di EDT né delle basi dati è stato modificato.
