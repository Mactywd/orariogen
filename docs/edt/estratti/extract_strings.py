#!/usr/bin/env python3
"""Ri-estrae le tabelle di lingua IT/FR/EN da EDT Monoposto.dll (sola lettura)."""
import re, html, sys, os

DLL = "/home/mattia/.wine/drive_c/Program Files/Index Education/EDT 2026/Monoposto/EDT Monoposto.dll"
OUT = os.path.dirname(os.path.abspath(__file__))

data = open(DLL, "rb").read()
print(f"letti {len(data)} byte", file=sys.stderr)

# I blocchi <chaines> ... </chaines>
blocks = [(m.start(), m.end()) for m in re.finditer(rb"<chaines[^>]*>", data)]
ends = [m.start() for m in re.finditer(rb"</chaines>", data)]
print(f"aperture={len(blocks)} chiusure={len(ends)}", file=sys.stderr)

RE = re.compile(rb'<chaine numero="(\d+)" cle="([^"]*)">(.*?)</chaine>', re.S)

# marcatori di lingua sulla chiave di riconoscimento
MARK = {
    "EN": b"Operations must be conducted on the database.",
    "ES": b"Unas operaciones deben ser efectuadas en la base de datos.",
    "FR": b"Des op",           # accenti -> prefisso
    "IT": b"\xc3\x88 necessario effettuare alcune operazioni sulla base dati.",
    "NL": b"Er wordt aan de databank gewerkt.",
    "EU": b"Eragiketak datu-basean egin behar dira.",
}

langs = {}
for i, (s, e) in enumerate(blocks):
    end = next((x for x in ends if x > e), len(data))
    chunk = data[e:end]
    if len(chunk) < 100000:
        continue
    head = chunk[:3000]
    lang = None
    for code, mark in MARK.items():
        if mark in head:
            lang = code
            break
    if lang is None or lang in langs:
        continue
    entries = {}
    for m in RE.finditer(chunk):
        num, cle, txt = m.group(1), m.group(2), m.group(3)
        try:
            entries[cle.decode("utf-8")] = html.unescape(txt.decode("utf-8"))
        except UnicodeDecodeError:
            continue
    langs[lang] = entries
    print(f"blocco {i} @{e} -> {lang}: {len(entries)} stringhe", file=sys.stderr)

it, fr, en = langs.get("IT", {}), langs.get("FR", {}), langs.get("EN", {})
with open(os.path.join(OUT, "it_fr_en.tsv"), "w", encoding="utf-8") as f:
    for k in it:
        row = [k, it.get(k, ""), fr.get(k, ""), en.get(k, "")]
        f.write("\t".join(c.replace("\t", " ").replace("\n", "\\n").replace("\r", "") for c in row) + "\n")
print(f"scritte {len(it)} righe in it_fr_en.tsv", file=sys.stderr)
