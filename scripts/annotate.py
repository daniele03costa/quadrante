"""Pubblica un riepilogo dell'esecuzione come annotazione GitHub (::notice / ::error)."""
import json
import os
import sys


def enc(s):
    return s.replace("%", "%25").replace("\r", "").replace("\n", "%0A")


log = open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines() if os.path.exists(sys.argv[1]) else []
rep_path = sys.argv[2] if len(sys.argv) > 2 else ""
lines = []
if rep_path and os.path.exists(rep_path):
    rep = json.load(open(rep_path))
    lines.append("FONTE | TITOLI | CON PREZZI | ESEMPI SENZA PREZZI")
    for src, e in sorted(rep.items()):
        flag = "OK" if e["con_prezzi"] >= 0.8 * e["titoli"] else "!!"
        lines.append(f"{flag} {src} | {e['titoli']} | {e['con_prezzi']} | {' '.join(e['senza_prezzi'][:6])}")
key = [l for l in log if any(k in l for k in ("Universo", "Prezzi disponibili", "Modello stimato", "Fatto:", "non disponibile",
                                                  "tempo massimo", "senza prezzi", "Archivio", "Storico completo"))]
lines += ["", "RIGHE CHIAVE DEL LOG:"] + key[-40:]
print(f"::notice title=Riepilogo Quadrante::{enc(chr(10).join(lines))[:60000]}")
tb = [i for i, l in enumerate(log) if l.startswith("Traceback")]
if tb:
    print(f"::error title=Errore Python::{enc(chr(10).join(log[tb[-1]:][-40:]))[:60000]}")
