#!/usr/bin/env python3
"""Estrae la struttura di un XSD Partenaire_Index in forma leggibile."""
import sys
import xml.etree.ElementTree as ET

XS = "{http://www.w3.org/2001/XMLSchema}"


def doc_of(node):
    ann = node.find(f"{XS}annotation/{XS}documentation")
    if ann is not None and ann.text:
        return " ".join(ann.text.split())
    return ""


def walk(node, path, out, depth=0):
    """Percorre gli xs:element annidati."""
    for el in node.findall(f".//{XS}element"):
        pass  # gestito ricorsivamente sotto

    # elementi figli diretti (dentro sequence/choice/all o complexType)
    for el in direct_elements(node):
        name = el.get("name") or el.get("ref", "?")
        minocc = el.get("minOccurs", "1")
        maxocc = el.get("maxOccurs", "1")
        card = f"{minocc}..{maxocc}"
        p = f"{path}/{name}"
        attrs = []
        ct = el.find(f"{XS}complexType")
        target = ct if ct is not None else el
        for at in target.findall(f"{XS}attribute"):
            attrs.append(
                {
                    "name": at.get("name"),
                    "type": at.get("type", ""),
                    "use": at.get("use", "optional"),
                    "doc": doc_of(at),
                }
            )
        out.append(
            {
                "path": p,
                "depth": depth,
                "card": card,
                "doc": doc_of(el),
                "attrs": attrs,
            }
        )
        if ct is not None:
            walk(ct, p, out, depth + 1)


def direct_elements(node):
    """xs:element figli diretti, attraversando sequence/choice/all."""
    res = []
    for child in node:
        tag = child.tag
        if tag == f"{XS}element":
            res.append(child)
        elif tag in (f"{XS}sequence", f"{XS}choice", f"{XS}all", f"{XS}complexType"):
            res.extend(direct_elements(child))
    return res


def main(path):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = root.get("targetNamespace", "")

    print(f"# {path.split('/')[-1]}")
    print(f"namespace: {ns}\n")

    # simpleType con enumerazioni
    print("## Tipi semplici ed enumerazioni\n")
    for st in root.findall(f"{XS}simpleType"):
        name = st.get("name")
        restr = st.find(f"{XS}restriction")
        base = restr.get("base") if restr is not None else "?"
        enums = [e.get("value") for e in st.findall(f".//{XS}enumeration")]
        d = doc_of(st)
        line = f"- **{name}** (base `{base}`)"
        if enums:
            line += " = " + " | ".join(f"`{v}`" for v in enums)
        if d:
            line += f"\n  - {d}"
        print(line)
    print()

    # struttura elementi
    print("## Struttura\n")
    out = []
    for el in root.findall(f"{XS}element"):
        name = el.get("name")
        attrs = []
        ct = el.find(f"{XS}complexType")
        target = ct if ct is not None else el
        for at in target.findall(f"{XS}attribute"):
            attrs.append(
                {
                    "name": at.get("name"),
                    "type": at.get("type", ""),
                    "use": at.get("use", "optional"),
                    "doc": doc_of(at),
                }
            )
        out.append({"path": name, "depth": 0, "card": "1..1", "doc": doc_of(el), "attrs": attrs})
        if ct is not None:
            walk(ct, name, out, 1)

    for item in out:
        ind = "  " * item["depth"]
        print(f"{ind}- `{item['path'].split('/')[-1]}` [{item['card']}]", end="")
        if item["doc"]:
            print(f" — {item['doc']}", end="")
        print()
        for a in item["attrs"]:
            req = "**req**" if a["use"] == "required" else "opt"
            t = a["type"].replace("tns:", "").replace("xs:", "")
            line = f"{ind}    · @{a['name']} `{t}` {req}"
            if a["doc"]:
                line += f" — {a['doc']}"
            print(line)


if __name__ == "__main__":
    main(sys.argv[1])
