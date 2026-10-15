"""Costruisce l'universo esteso (~4.000 strumenti) da fonti pubbliche.

Fonti:
  - Wikipedia: S&P 500/400/600, Nasdaq-100, indici europei (DAX, MDAX, SDAX, FTSE 100/250,
    CAC 40, SBF 120, FTSE MIB, IBEX 35, AEX, AMX, BEL 20, SMI, OMX Stockholm 30, OMX Helsinki 25,
    PSI, ATX, OBX, OMX Copenhagen 25)
  - NASDAQ Trader Symbol Directory: tutti gli ETF quotati negli USA (filtrati poi per liquidità)
  - liste interne di universe.py (indici, forex, materie prime, cripto, temi)

Il risultato è salvato in data/universe.json e ricostruito al massimo una volta a settimana.
Se una fonte non risponde, viene saltata: lo script usa ciò che riesce a ottenere più le liste interne.
"""
import io
import json
import os
import re
import time
import urllib.request

import pandas as pd

VERSION = 3          # aumentalo quando cambiano le fonti: l'universo in cache viene ricostruito
UA = {"User-Agent": "Mozilla/5.0 (Quadrante personal dashboard; contact via GitHub)"}

# (pagina Wikipedia, suffisso Yahoo, paese)
WIKI_INDEXES = [
    ("List_of_S%26P_500_companies", "", "Stati Uniti"),
    ("List_of_S%26P_400_companies", "", "Stati Uniti"),
    ("List_of_S%26P_600_companies", "", "Stati Uniti"),
    ("Nasdaq-100", "", "Stati Uniti"),
    ("DAX", ".DE", "Germania"),
    ("MDAX", ".DE", "Germania"),
    ("SDAX", ".DE", "Germania"),
    ("FTSE_100_Index", ".L", "Regno Unito"),
    ("FTSE_250_Index", ".L", "Regno Unito"),
    ("CAC_40", ".PA", "Francia"),
    ("SBF_120", ".PA", "Francia"),
    ("FTSE_MIB", ".MI", "Italia"),
    ("FTSE_Italia_Mid_Cap", ".MI", "Italia"),
    ("IBEX_35", ".MC", "Spagna"),
    ("AEX_index", ".AS", "Paesi Bassi"),
    ("AMX_index", ".AS", "Paesi Bassi"),
    ("BEL_20", ".BR", "Belgio"),
    ("Swiss_Market_Index", ".SW", "Svizzera"),
    ("OMX_Stockholm_30", ".ST", "Svezia"),
    ("OMX_Helsinki_25", ".HE", "Finlandia"),
    ("OMX_Copenhagen_25", ".CO", "Danimarca"),
    (("PSI_(stock_index)", "PSI-20", "PSI_20"), ".LS", "Portogallo"),
    ("Austrian_Traded_Index", ".VI", "Austria"),
    ("OBX_Index", ".OL", "Norvegia"),
]

# simboli Yahoo (alcune cripto hanno un identificativo numerico per evitare omonimie)
CRYPTO_EXTRA = ["BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "LINK", "AVAX", "TRX", "DOT", "LTC", "BCH",
                "XLM", "ATOM", "NEAR", "ETC", "FIL", "HBAR", "ICP", "APT21794", "ARB11841", "OP", "AAVE", "UNI7083",
                "ALGO", "VET", "SUI20947", "TON11419", "SHIB", "PEPE24478", "INJ", "RENDER", "GRT6719", "XMR", "SAND",
                "MANA", "XTZ"]


def _get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


NORDIC = (".ST", ".CO", ".HE", ".OL")


def _norm_ticker(raw, suffix):
    t = str(raw).strip().upper()
    t = re.sub(r"\[.*?\]", "", t).strip()            # note di Wikipedia
    t = t.split(":")[-1].strip()                    # "XETRA: ADS" -> "ADS"
    if suffix in NORDIC:
        t = re.sub(r"\s+", "-", t)                  # "VOLV B" -> "VOLV-B" (formato Yahoo)
    else:
        t = t.split(" ")[0]
    if not t or t in ("NAN", "—", "-") or len(t) > 14:
        return None
    if suffix == "":
        return t.replace(".", "-")                  # BRK.B -> BRK-B (Yahoo)
    if re.search(r"\.(DE|L|PA|MI|MC|AS|BR|SW|ST|HE|CO|LS|VI|OL)$", t):   # ha già il suffisso di borsa
        return t
    t = t.rstrip(".").replace(".", "-")             # BT.A -> BT-A.L
    return t + suffix


def wiki_constituents(page, suffix, country):
    pages = page if isinstance(page, tuple) else (page,)
    html, err = None, None
    for pg in pages:                                  # alcune pagine cambiano nome: prova le alternative
        try:
            html = _get(f"https://en.wikipedia.org/wiki/{pg}")
            page = pg
            break
        except Exception as e:
            err = e
    if html is None:
        raise err
    tables = pd.read_html(io.StringIO(html))
    best = []
    for df in tables:
        cols = [" ".join(str(x) for x in c) if isinstance(c, tuple) else str(c) for c in df.columns]
        cols = [f"{c}#{i}" if cols.count(c) > 1 else c for i, c in enumerate(cols)]
        df.columns = cols
        tcol = next((c for c in cols if re.search(r"ticker|symbol|epic|code", c, re.I)), None)
        if tcol is not None and len(df) >= 30:
            looks = df[tcol].astype(str).str.strip().str.fullmatch(r"[A-Za-z][A-Za-z0-9.\-: ]{0,14}").mean()
            if looks < 0.6:
                tcol = None                          # l'intestazione inganna: decido guardando i valori
        if tcol is None and len(df) >= 30:
            # nessuna intestazione riconoscibile: cerco la colonna i cui valori sembrano ticker
            best_c, best_f = None, 0.0
            for c in cols:
                v = df[c].astype(str).str.strip()
                f = v.str.fullmatch(r"[A-Z][A-Z0-9.\- ]{0,9}").mean()
                if f > best_f:
                    best_c, best_f = c, f
            tcol = best_c if best_f >= 0.8 else None
        if tcol is None or len(df) < 10:
            continue
        ncol = next((c for c in cols if re.search(r"company|security|name|constituent", c, re.I) and c != tcol), None)
        scol = next((c for c in cols if re.search(r"sector", c, re.I)), None)
        icol = next((c for c in cols if re.search(r"sub-industry|industry", c, re.I) and c != scol), None)
        rows = []
        for _, r in df.iterrows():
            t = _norm_ticker(r[tcol], suffix)
            if not t:
                continue
            rows.append({"t": t, "name": str(r[ncol]).strip() if ncol else t, "type": "Azione", "country": country, "src": page,
                         "sector": str(r[scol]).strip() if scol and pd.notna(r[scol]) else "",
                         "industry": str(r[icol]).strip() if icol and pd.notna(r[icol]) else ""})
        if len(rows) > len(best):
            best = rows
    return best


def nasdaq_etfs():
    out = []
    for fn, sym_col, name_col in (("nasdaqlisted.txt", "Symbol", "Security Name"), ("otherlisted.txt", "ACT Symbol", "Security Name")):
        txt = _get(f"https://www.nasdaqtrader.com/dynamic/SymDir/{fn}")
        df = pd.read_csv(io.StringIO(txt), sep="|")
        df = df[(df.get("ETF") == "Y") & (df.get("Test Issue", "N") == "N")]
        for _, r in df.iterrows():
            s = str(r[sym_col]).strip()
            if s and re.fullmatch(r"[A-Z]{1,5}", s):
                out.append({"t": s, "name": str(r[name_col]).split(" - ")[0].strip()[:60], "type": "ETF", "src": "nasdaqtrader",
                            "country": "Stati Uniti", "sector": "", "industry": ""})
    return out


def liquidity_rank(tickers, keep, chunk=100):
    """Scarica 3 mesi e tiene i 'keep' ticker con controvalore mediano più alto."""
    import yfinance as yf
    dv = {}
    for i in range(0, len(tickers), chunk):
        part = tickers[i:i + chunk]
        try:
            df = yf.download(part, period="3mo", interval="1d", group_by="ticker", auto_adjust=True,
                             threads=True, progress=False)
        except Exception as e:
            print("  liquidità: errore", e)
            continue
        for t in part:
            try:
                sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
                v = (sub["Close"] * sub["Volume"]).dropna()
                if len(v) > 20:
                    dv[t] = float(v.median())
            except Exception:
                pass
        print(f"  liquidità ETF: {min(i + chunk, len(tickers))}/{len(tickers)}")
        time.sleep(1)
    return [t for t, _ in sorted(dv.items(), key=lambda x: -x[1])[:keep]]


def build(path, base_rows, max_age_days=7, etf_keep=1200, force=False, sample=None):
    """base_rows: lista interna [(ticker, nome, tipo, paese)]. Restituisce lista di dict.
    sample: per la prova veloce, prende solo i primi N titoli di ogni fonte."""
    if not force and not sample and path and os.path.exists(path):
        try:
            with open(path) as f:
                cached = json.load(f)
            if (cached.get("v") == VERSION and time.time() - cached.get("ts", 0) < max_age_days * 86400
                    and len(cached.get("rows", [])) > 500):
                print(f"Universo in cache: {len(cached['rows'])} strumenti")
                return cached["rows"]
        except Exception:
            pass
    rows = {r[0]: {"t": r[0], "name": r[1], "type": r[2], "country": r[3], "sector": "", "industry": "", "src": "interno"}
            for r in base_rows}
    for page, suffix, country in WIKI_INDEXES:
        try:
            got = wiki_constituents(page, suffix, country)
            if sample:
                got = got[:sample]
            added = 0
            for r in got:
                if r["t"] not in rows:
                    rows[r["t"]] = r
                    added += 1
                elif r["sector"] and not rows[r["t"]]["sector"]:
                    rows[r["t"]].update(sector=r["sector"], industry=r["industry"])
            print(f"  {page}: {len(got)} titoli (+{added})")
        except Exception as e:
            print(f"  {page}: non disponibile ({e})")
        time.sleep(0.5)
    for c in CRYPTO_EXTRA:
        rows.setdefault(f"{c}-USD", {"t": f"{c}-USD", "name": re.sub(r"\d+$", "", c), "type": "Cripto", "country": "Globale", "sector": "", "industry": "", "src": "cripto"})
    try:
        etfs = [e for e in nasdaq_etfs() if e["t"] not in rows]
        print(f"  ETF USA candidati: {len(etfs)}")
        if sample:
            etfs = etfs[:sample * 4]
        keep = set(liquidity_rank([e["t"] for e in etfs], sample * 2 if sample else etf_keep))
        for e in etfs:
            if e["t"] in keep:
                rows[e["t"]] = e
    except Exception as e:
        print("  elenco ETF NASDAQ non disponibile:", e)
    out = list(rows.values())
    if sample:
        return out
    with open(path, "w") as f:
        json.dump({"v": VERSION, "ts": time.time(), "rows": out}, f)
    print(f"Universo costruito: {len(out)} strumenti")
    return out
