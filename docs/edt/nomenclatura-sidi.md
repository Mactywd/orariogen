# Entità EDT — La nomenclatura ministeriale SIDI

> Fonte 📦: `TabellaSIDI.xml` (217 KB) dentro l'installazione di EDT 2026
> Monoposto. È la localizzazione italiana di EDT: le tabelle del **SIDI**
> (Sistema Informativo dell'Istruzione, MIM) incorporate nel prodotto.

## Cos'è

EDT è software francese, ma la versione italiana porta con sé le nomenclature
ministeriali italiane, così che i codici esportati verso il SIDI siano quelli
attesi. Per noi è un dizionario di riferimento già pronto e allineato alla
normativa.

Quattro tabelle:

| Tabella | Righe | Contenuto |
|---|---|---|
| `FILIERES` | 179 | Indirizzi di studio |
| `MATIERES` | 267 | Materie |
| `EXPORTMATIERES` | 292 | Mappa (indirizzo × anno) → elenco materie |
| `MENTIONS` | 190 | Esiti di scrutinio |

## Indirizzi (`FILIERE`)

```xml
<FILIERE CodeSIDI="LI02" Classification="PR"
         Libelle="SCIENTIFICO"
         GenreEtab="SCUOLA SECONDARIA DI II GRADO"/>
```

Il codice ha un prefisso di famiglia: `LI` licei (16 voci), `IP` istituti
professionali, `IT` istituti tecnici. I 16 licei:

| Codice | Indirizzo |
|---|---|
| `LI00` | Artistico nuovo ordinamento — biennio comune |
| `LI01` | Classico |
| `LI02` | Scientifico |
| `LI03` | Scientifico — opzione scienze applicate |
| `LI15` | Scientifico — sezione a indirizzo sportivo |
| `LI04` | Linguistico |
| `LI11` | Scienze umane |
| `LI12` | Scienze umane — opz. economico sociale |
| `LI13` | Musicale e coreutico — sez. musicale |
| `LI14` | Musicale e coreutico — sezione coreutica |
| `LI05` | Architettura e ambiente |
| `LI06` | Arti figurative |
| `LI07`–`LI10` | (altre articolazioni artistiche) |

## Materie (`MATIERE`)

```xml
<MATIERE CodeSIDI="0011" Libelle="LINGUA E LETTERATURA ITALIANA"
         GenreEtab="SCUOLA SECONDARIA DI II GRADO"/>
```

Codice a 4 cifre. I codici `0xxx` sono le materie curricolari ordinarie; alcuni
codici alti sono trasversali e ricorrono in ogni indirizzo:

| Codice | Materia |
|---|---|
| `5555` | Scienze motorie e sportive |
| `6666` | Religione cattolica / attività alternativa |
| `7777` | Disciplina autonomia |
| `9999` | Comportamento |

Il `6666` è notevole: nella nomenclatura ufficiale **IRC e attività alternativa
sono un unico codice materia**, non due. Va tenuto presente per il punto aperto
"IRC vs. attività alternativa" ([vincoli.md](vincoli.md)) — a livello
ministeriale non c'è distinzione, quindi lo sdoppiamento è un fatto
organizzativo interno, non una distinzione di materia.

## Quadro orario ministeriale (`EXPORT`)

L'elemento `EXPORT` lega indirizzo e anno all'elenco delle materie previste:

```xml
<EXPORT Filiere="LI02" Niveau="1">
  <MATIERE CodeSIDI="0011"/>   <!-- Italiano -->
  <MATIERE CodeSIDI="0015"/>   <!-- Latino -->
  …
</EXPORT>
```

292 combinazioni in tutto, di cui **61 riguardano i licei**. È il quadro orario
ufficiale — quali materie in quale indirizzo e in quale anno — già in forma
tabellare.

Esempio, Scientifico primo anno (`LI02` / `Niveau=1`), 12 materie:

`0011` Italiano · `0015` Latino · `0025` Lingua e cultura straniera ·
`0039` Storia e geografia · `0042` Matematica con informatica ·
`0047` Fisica · `0048` Scienze naturali · `0054` Disegno e storia dell'arte ·
`5555` Scienze motorie · `6666` Religione/alternativa · `7777` Disciplina
autonomia · `9999` Comportamento

L'estrazione completa dei 61 quadri liceali è riproducibile con lo script in
[Come rigenerare](#come-rigenerare).

## Cosa NON c'è: le classi di concorso

⚠ **La tabella non contiene le classi di concorso** (A011, A027…). Il campo
`MATIERE.CodeSIDI` è il codice *materia*, non il codice della classe di
concorso, e non esiste una tabella che le leghi.

Questo **conferma** [ADR-002](../decisioni.md) nella sua premessa: la mappatura
disciplina → classe di concorso resta **nostra estensione**, perché EDT non la
porta nemmeno nella sua localizzazione italiana. Non è una lacuna della nostra
analisi: non c'è proprio.

## Implicazioni per il nostro schema

1. **Adottare `CodeSIDI` come codice esterno** di materie e indirizzi: dà
   interoperabilità col SIDI gratis, ed è il codice che le scuole già usano.
2. **Il quadro orario ministeriale è un seed**, non un vincolo: `EXPORT` dice
   *quali* materie, mai *quante ore*. Il monte ore resta sul piano di studi
   (vedi `Mef` in [schema-scambio.md](schema-scambio.md)).
3. `6666` unico per IRC e alternativa: la distinzione va modellata come
   organizzazione (gruppi), non come materie diverse.
4. Utile come **validazione** del dataset Fermi: le materie dei nostri 5 piani
   dovrebbero essere un sottoinsieme di quelle previste per il rispettivo
   `(Filiere, Niveau)`.

## Come rigenerare

```bash
python3 - <<'PY'
import xml.etree.ElementTree as ET
p = "~/.wine/drive_c/Program Files/Index Education/EDT 2026/Monoposto/TabellaSIDI.xml"
import os; r = ET.parse(os.path.expanduser(p)).getroot()
names = {m.get('CodeSIDI'): m.get('Libelle') for m in r.findall('./MATIERES/MATIERE')}
fil   = {f.get('CodeSIDI'): f.get('Libelle') for f in r.findall('.//FILIERE')}
for e in r.findall('.//EXPORT'):
    f = e.get('Filiere')
    if not f.startswith('LI'):
        continue
    print(f"\n## {f} anno {e.get('Niveau')} — {fil.get(f)}")
    for m in e:
        print(f"  {m.get('CodeSIDI')} {names.get(m.get('CodeSIDI'), '?')}")
PY
```
