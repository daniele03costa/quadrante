#!/usr/bin/env python3
"""Aggiorna tutti i dati di Quadrante.

Uso:
    python scripts/update_data.py          # dati reali (Yahoo Finance, FRED, CFTC, ForexFactory)
    python scripts/update_data.py --demo   # dati simulati, per provare il sito senza internet

Scrive in data/:
    assets.json       tutti gli strumenti: punteggio, pilastri, performance
    dashboard.json    regime macro, sentiment, risk on/off, gruppi, proposte, temi, affidabilità
    radar.json        finestre stagionali imminenti, ingressi/uscite della regola 80/60
    rotation.json     rotazione relativa (RRG) per indici, settori, fattori, commodity, cripto, forex, temi
    portfolios.json   portafogli modello (regola 80/60 e top 10%) contro il mercato
    news.json         calendario earnings, calendario macro, Commitment of Traders
    hist/<id>.json    scheda strumento: OHLC 1 anno, storico punteggio, pilastri, operazioni, stagionalità
    meta.json         cache settore / capitalizzazione / data trimestrale
"""
import io
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import extras  # noqa: E402
import model  # noqa: E402
import price_store  # noqa: E402
import universe_builder  # noqa: E402
from universe import (BENCH, GROUPS, MACRO_COUNTRIES, PANELS, RISK_OFF, RISK_ON, SECTOR_IT,  # noqa: E402
                      THEMES, all_assets, market_of, rotation_sets, theme_of)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
HIST = os.path.join(DATA, "hist")
DEMO = "--demo" in sys.argv or "--demo-full" in sys.argv
SMOKE = "--smoke" in sys.argv          # prova veloce: pochi titoli per fonte, 12 anni di storico
START = "2014-01-01" if SMOKE else "2004-01-01"
STALE_DAYS = 10                        # strumenti senza nuove quotazioni da più giorni = "fermi"

# Valuta e cambi (1 EUR = x valuta) per i portafogli
FX_TICKERS = {"USD": "EURUSD=X", "GBP": "EURGBP=X", "CHF": "EURCHF=X", "JPY": "EURJPY=X",
              "SEK": "EURSEK=X", "DKK": "EURDKK=X", "NOK": "EURNOK=X"}
SUFFIX_CCY = {".L": "GBp", ".MI": "EUR", ".DE": "EUR", ".PA": "EUR", ".AS": "EUR", ".MC": "EUR", ".BR": "EUR",
              ".HE": "EUR", ".LS": "EUR", ".VI": "EUR", ".SW": "CHF", ".ST": "SEK", ".CO": "DKK", ".OL": "NOK",
              ".SS": "CNY", ".HK": "HKD", ".T": "JPY"}
COUNTRY_CCY = {"Stati Uniti": "USD", "Eurozona": "EUR", "Germania": "EUR", "Francia": "EUR", "Italia": "EUR",
               "Spagna": "EUR", "Paesi Bassi": "EUR", "Regno Unito": "GBP", "Svizzera": "CHF", "Giappone": "JPY",
               "Hong Kong": "HKD", "Cina": "CNY", "Corea del Sud": "KRW", "Taiwan": "TWD", "India": "INR",
               "Brasile": "BRL", "Messico": "MXN", "Argentina": "ARS", "Canada": "CAD", "Australia": "AUD"}


def currency_of(t, typ, country, meta_ccy=None):
    if meta_ccy:
        return meta_ccy
    if t.endswith("=X"):
        return t[3:6] if len(t) >= 8 else "USD"
    if t.endswith("-USD") or t.endswith("=F"):
        return "USD"
    for suf, c in SUFFIX_CCY.items():
        if t.endswith(suf):
            return c
    if typ == "Indice":
        return COUNTRY_CCY.get(country, "USD")
    return "USD"


# ==========================================================================
# Utilità
# ==========================================================================
def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def safe_id(ticker):
    return re.sub(r"[^A-Za-z0-9]", "_", ticker)


def r4(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, 4) if math.isfinite(x) else None


def price_at(close, days):
    target = close.index[-1] - pd.Timedelta(days=days)
    past = close[close.index <= target]
    return float(past.iloc[-1]) if len(past) else None


def ret(close, days):
    p0 = price_at(close, days)
    return None if not p0 else float(close.iloc[-1]) / p0 - 1


def ytd(close):
    last = close.index[-1]
    prev = close[close.index < pd.Timestamp(year=last.year, month=1, day=1)]
    return None if prev.empty else float(close.iloc[-1]) / float(prev.iloc[-1]) - 1


def dump(name, obj, pretty=False):
    with open(os.path.join(DATA, name), "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1 if pretty else None,
                  separators=None if pretty else (",", ":"))


# ==========================================================================
# Download
# ==========================================================================
def demo_prices(tickers):
    """Random walk con regimi di trend persistenti (solo per provare il sito offline)."""
    rng = np.random.default_rng(42)
    idx = pd.bdate_range(start=START, end=pd.Timestamp(datetime.now().date()))
    n = len(idx)
    common = rng.normal(0.0002, 0.009, n)
    out = {}
    for t in tickers:
        vol = rng.uniform(0.006, 0.025)
        beta = rng.uniform(0.2, 1.3)
        drift = np.repeat(rng.normal(0.0002, 0.0012, n // 120 + 1), 120)[:n]
        seas = 0.0008 * np.sin(2 * np.pi * (idx.dayofyear.values / 365.25) + rng.uniform(0, 6.28))
        if "--null" in sys.argv:                 # test di controllo: nessun segnale prevedibile
            drift, seas = 0.0002, 0.0
        r = beta * common + drift + seas + rng.normal(0, vol, n)
        start = rng.integers(0, n // 3) if rng.random() < 0.15 else 0
        c = 100 * np.exp(np.cumsum(r))
        o = c * (1 + rng.normal(0, vol / 3, n))
        h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 2, n)))
        lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 2, n)))
        out[t] = pd.DataFrame({"Open": o, "High": h, "Low": lo, "Close": c}, index=idx).iloc[start:]
    return out


_FRED_CACHE = {}
_FRED_DOWN = False


def fetch_fred(series_id):
    """Serie FRED (CSV pubblico, senza chiave). Risultati in memoria per non riscaricarli;
    se FRED non risponde, smette di provarci per il resto dell'esecuzione (si usano i segnali di mercato)."""
    global _FRED_DOWN
    if DEMO or _FRED_DOWN:
        return None
    if series_id in _FRED_CACHE:
        return _FRED_CACHE[series_id]
    import urllib.request
    s = None
    try:
        req = urllib.request.Request(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
                                     headers=extras.UA)
        with urllib.request.urlopen(req, timeout=45) as resp:
            df = pd.read_csv(io.StringIO(resp.read().decode()))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        s = df.dropna().set_index("date")["value"]
        s = s if len(s) > 30 else None
    except Exception as e:
        print(f"  FRED {series_id} non disponibile: {e}")
        if "timed out" in str(e) or "timeout" in str(e).lower():
            _FRED_DOWN = True
            print("  FRED non risponde: per questa esecuzione uso solo i segnali di mercato")
    _FRED_CACHE[series_id] = s
    return s


def load_meta(universe, wiki):
    """Settore/industria (S&P 500 da Wikipedia, resto da Yahoo), capitalizzazione e data trimestrale.
    Cache di 14 giorni; al massimo 400 richieste a Yahoo per esecuzione (la cache si riempie in pochi giorni)."""
    path = os.path.join(DATA, "meta.json")
    meta = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    stocks = [t for t, _, typ, _ in universe if typ == "Azione"]
    if DEMO:
        rng = np.random.default_rng(7)
        secs = list(dict.fromkeys(SECTOR_IT.values()))
        today = pd.Timestamp(datetime.now().date())
        for t in stocks:
            if t not in meta:
                meta[t] = {"sector": str(rng.choice(secs)), "industry": "", "cap": float(rng.lognormal(24.3, 1.3)),
                           "earnings": (today + pd.Timedelta(days=int(rng.integers(-5, 80)))).strftime("%Y-%m-%d"),
                           "ts": 0}
        return meta
    import yfinance as yf
    now = time.time()
    todo = sorted(stocks, key=lambda t: meta.get(t, {}).get("ts", 0))
    todo = [t for t in todo if now - meta.get(t, {}).get("ts", 0) > 14 * 86400][:30 if SMOKE else 400]
    for t in todo:
        m = meta.get(t, {})
        try:
            tk = yf.Ticker(t)
            info = tk.info or {}
            m["sector"] = SECTOR_IT.get(wiki.get(t, (None,))[0] or info.get("sector") or "", info.get("sector") or "")
            m["industry"] = (wiki.get(t, (None, None))[1] or info.get("industry") or "")
            m["cap"] = info.get("marketCap")
            m["currency"] = info.get("currency")
            try:
                cal = tk.calendar or {}
                ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
                if ed:
                    m["earnings"] = pd.Timestamp(ed[0]).strftime("%Y-%m-%d")
            except Exception:
                pass
            m["ts"] = now
            meta[t] = m
        except Exception as e:
            print("  meta non disponibile per", t, e)
        time.sleep(0.3)
    for t, (sec, ind) in wiki.items():          # settori S&P 500 sempre aggiornati
        meta.setdefault(t, {"ts": 0})
        meta[t]["sector"] = SECTOR_IT.get(sec, sec)
        meta[t]["industry"] = ind
    with open(path, "w") as f:
        json.dump(meta, f)
    return meta


def _tuning_summary():
    p = os.path.join(os.path.dirname(__file__), "tuning_report.json")
    if not os.path.exists(p):
        return None
    r = json.load(open(p))
    return {"date": r["date"], "demo": r.get("demo"), "best": r["best"]["why"], "metrics": r["best"]["metrics"],
            "tried": [{"why": t["why"], "objective": t["objective"], "ic": t["metrics"]["selezione"]["ic"],
                       "ic_check": t["metrics"]["verifica"]["ic"], "spread": t["metrics"]["selezione"]["spread"],
                       "turnover": t["metrics"]["turnover"], "calib_err": t["metrics"].get("calib_err")} for t in r["tried"]]}


def sources_report(rows, prices):
    """Riepilogo per fonte: quanti titoli trovati e quanti con prezzi. Utile soprattutto nella prova veloce."""
    rep = {}
    for r in rows:
        src = r.get("src", "interno")
        e = rep.setdefault(src, {"titoli": 0, "con_prezzi": 0, "senza_prezzi": []})
        e["titoli"] += 1
        if r["t"] in prices:
            e["con_prezzi"] += 1
        elif len(e["senza_prezzi"]) < 12:
            e["senza_prezzi"].append(r["t"])
    print("\nFONTE                               TITOLI  CON PREZZI  ESEMPI SENZA PREZZI")
    for src, e in sorted(rep.items()):
        flag = "OK " if e["con_prezzi"] >= 0.8 * e["titoli"] else "!! "
        print(f"{flag}{src[:32]:32s} {e['titoli']:6d}  {e['con_prezzi']:10d}  {' '.join(e['senza_prezzi'][:6])}")
    print()
    dump("sources_report.json", rep, pretty=True)
    return rep


def demo_universe(n_extra=None):
    """Universo dimostrativo della stessa taglia di quello reale (per i test di velocità)."""
    if n_extra is None:
        n_extra = 3300 if "--demo-full" in sys.argv else 0
    base = [{"t": t, "name": n, "type": typ, "country": c, "sector": "", "industry": ""} for t, n, typ, c in all_assets()]
    countries = ["Stati Uniti"] * 5 + ["Germania", "Regno Unito", "Francia", "Italia", "Spagna"]
    for i in range(n_extra):
        typ = "ETF" if i % 3 == 0 else "Azione"
        base.append({"t": f"DEMO{i:04d}", "name": f"Demo {'Fund' if typ == 'ETF' else 'Corp'} {i}", "type": typ,
                     "country": "Stati Uniti" if typ == "ETF" else countries[i % len(countries)], "sector": "", "industry": ""})
    return base


def cap_class(cap):
    if not cap:
        return ""
    return "Mega" if cap >= 200e9 else "Large" if cap >= 10e9 else "Mid" if cap >= 2e9 else "Small"


# ==========================================================================
# Indicatori della dashboard
# ==========================================================================
def build_macro(prices):
    """Regime corrente per paese: accelerazione di produzione industriale e inflazione (FRED)
    combinata con segnali di mercato."""
    def macro_z(series):
        s = series.dropna()
        if len(s) < 40 or (pd.Timestamp.now() - s.index[-1]).days > 270:
            return None
        per_year = 4 if pd.Series(s.index).diff().dt.days.median() > 60 else 12
        yoy = s / s.shift(per_year) - 1
        acc = (yoy - yoy.shift(per_year // 2)).dropna().iloc[-10 * per_year:]
        if len(acc) < 12 or acc.std() == 0:
            return None
        return float(np.clip(acc.iloc[-1] / acc.std(), -3, 3)), s.index[-1].strftime("%Y-%m")

    def market_t(ticker, w=(91, 182)):
        df = prices.get(ticker)
        if df is None or len(df) < 260:
            return None
        c = df["Close"]
        vol = float(np.log(c).diff().iloc[-126:].std() * math.sqrt(252))
        ts = []
        for d in w:
            p0 = price_at(c, d)
            if p0 and vol > 0:
                ts.append(math.log(float(c.iloc[-1]) / p0) / (vol * math.sqrt(d / 365)))
        return float(np.clip(np.mean(ts), -3, 3)) if ts else None

    infl_parts = [x for x in [market_t("DBC")] if x is not None]
    if "TIP" in prices and "IEF" in prices:
        ratio = (prices["TIP"]["Close"] / prices["IEF"]["Close"]).dropna()
        if len(ratio) > 260:
            prices_ratio = {"_r": pd.DataFrame({"Close": ratio})}
            prices.update(prices_ratio)
            x = market_t("_r")
            prices.pop("_r")
            if x is not None:
                infl_parts.append(x)
    infl_mkt = float(np.mean(infl_parts)) if infl_parts else 0.0

    out, fred_cache = [], {}
    for c in MACRO_COUNTRIES:
        g_mkt = market_t(c["market"]) or 0.0
        g_macro = i_macro = g_src = i_src = None
        for key, lst in (("g", c["growth"]), ("i", c["inflation"])):
            for sid in lst:
                s = fred_cache.setdefault(sid, fetch_fred(sid))
                r = macro_z(s) if s is not None else None
                if r:
                    if key == "g":
                        g_macro, g_src = r[0], f"{sid} ({r[1]})"
                    else:
                        i_macro, i_src = r[0], f"{sid} ({r[1]})"
                    break
        zg = 0.6 * g_macro + 0.4 * g_mkt if g_macro is not None else g_mkt
        zi = 0.6 * i_macro + 0.4 * infl_mkt if i_macro is not None else infl_mkt
        pg, pi = sigmoid(1.3 * zg), sigmoid(1.3 * zi)
        probs = {"ESPANSIONE": pg * (1 - pi), "REFLAZIONE": pg * pi,
                 "STAGFLAZIONE": (1 - pg) * pi, "DEFLAZIONE": (1 - pg) * (1 - pi)}
        dom = max(probs, key=probs.get)
        out.append({"id": c["id"], "name": c["name"], "flag": c["flag"], "regime": dom,
                    "prob": round(probs[dom] * 100), "probs": {k: round(v * 100) for k, v in probs.items()},
                    "growth_z": round(zg, 2), "inflation_z": round(zi, 2),
                    "sources": {"crescita": g_src or f"mercato ({c['market']})",
                                "inflazione": i_src or "mercato (materie prime, TIPS/Treasury)"}})
    return out, fred_cache


def build_sentiment(assets):
    pool = [a for a in assets if a["score"] is not None]
    n = len(pool) or 1
    sell = sum(a["score"] < 60 for a in pool) / n
    buy = sum(a["score"] >= 80 for a in pool) / n
    hold = 1 - sell - buy
    groups = {"SELL": sell, "HOLD": hold, "BUY": buy}
    dom = max(groups, key=groups.get)
    # ampiezza: quota sopra la media a 200 giorni (misura assoluta, non vincolata dal ranking)
    breadth = [a["above200"] for a in pool if a.get("above200") is not None]
    br = float(np.mean(breadth)) if breadth else 0.5
    edge_pos = [a["edge"] > 0 for a in pool if a.get("edge") is not None]
    return {"label": dom, "pct": round(groups[dom] * 100), "gauge": round(br * 100),
            "sell": round(sell * 100), "hold": round(hold * 100), "buy": round(buy * 100),
            "n": len(pool), "breadth": round(br * 100),
            "edgePos": round(float(np.mean(edge_pos)) * 100) if edge_pos else None}


def build_risk(by_t):
    on = [by_t[t]["score"] for t in RISK_ON if t in by_t and by_t[t]["score"] is not None]
    off = [by_t[t]["score"] for t in RISK_OFF if t in by_t and by_t[t]["score"] is not None]
    s_on = float(np.mean(on)) if on else 50
    s_off = float(np.mean(off)) if off else 50
    gauge = float(np.clip(50 + (s_on - s_off) * 0.9, 0, 100))
    label = ("EXTREME RISK ON" if gauge >= 70 else "RISK ON" if gauge >= 56 else "NEUTRAL" if gauge > 44
             else "RISK OFF" if gauge > 30 else "EXTREME RISK OFF")
    risk = round(gauge * 0.8 + 10)
    rest = 100 - risk
    cash = round(rest * float(np.clip(1 - s_off / 100, 0.15, 0.85)))
    return {"label": label, "gauge": round(gauge), "risk": risk, "defensive": rest - cash, "cash": cash,
            "score_on": round(s_on), "score_off": round(s_off)}


# ==========================================================================
# Main
# ==========================================================================
def main():
    os.makedirs(HIST, exist_ok=True)
    if DEMO:
        rows = demo_universe()
    elif SMOKE:
        rows = universe_builder.build(None, all_assets(), sample=6)
    else:
        rows = universe_builder.build(os.path.join(DATA, "universe.json"), all_assets())
    have = {r["t"] for r in rows}
    for c, fx in FX_TICKERS.items():                     # cambi necessari ai portafogli
        if fx not in have:
            rows.append({"t": fx, "name": f"EUR/{c}", "type": "Forex", "country": "Globale", "sector": "", "industry": "", "src": "cambi"})
    universe = [(r["t"], r["name"], r["type"], r["country"]) for r in rows]
    wiki = {r["t"]: (r["sector"], r["industry"]) for r in rows if r.get("sector")}
    info = {t: (n, typ, c) for t, n, typ, c in universe}
    themes = theme_of()
    tickers = [u[0] for u in universe]
    mode = "DEMO" if DEMO else "PROVA VELOCE" if SMOKE else "reale"
    print(f"Universo: {len(tickers)} strumenti — modalità {mode}")
    cache_file = os.path.join(ROOT, "cache", "smoke.parquet" if SMOKE else "prices.parquet")
    prices = demo_prices(tickers) if DEMO else price_store.load_prices(tickers, cache_file, START)
    print(f"Prezzi disponibili per {len(prices)} strumenti")
    sources_report(rows, prices)
    meta = load_meta(universe, wiki)

    # ---------------- modello a 5 pilastri
    markets = {t: market_of(info[t][1], info[t][2]) for t in prices}
    _, fred = build_macro(dict(prices))
    cfg_path = os.path.join(os.path.dirname(__file__), "model_config.json")
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else None
    res = model.run_model(prices, markets, fred.get("INDPRO"), fred.get("CPIAUCSL"), cfg=cfg)
    W, score, edge = res["W"], res["score"], res["edge"]
    print(f"Modello stimato. Punteggi fuori campione dal {res['first_year']}.")

    calib = res["calib"]

    def calib_for(s, market=None):
        table = res["calib_mkt"].get(market) or calib
        for c in table:
            if c["from"] <= s <= c["to"]:
                return c
        return None

    bench_w = {g: (W[b] if b and b in W else None) for g, b in BENCH.items()}
    pct_last = {p: res["pct"][p].iloc[-1] for p in model.PILLARS}
    beta = res["beta_live"]
    B_last = res["B_last"]
    col_pos = {t: i for i, t in enumerate(W.columns)}

    last_global = max(df.index[-1] for df in prices.values())
    fx = {"EUR": 1.0}
    for c, tk in FX_TICKERS.items():
        if tk in prices:
            fx[c] = float(prices[tk]["Close"].iloc[-1])
    if "GBP" in fx:
        fx["GBp"] = fx["GBP"] * 100                      # pence

    assets, radar_mom = [], []
    for t in prices:
        name, typ, country = info[t]
        df = prices[t]
        close = df["Close"]
        if len(close) < 60:
            continue
        mkt = markets[t]
        s_series = score[t] if t in score else pd.Series(dtype=float)
        s_now = s_series.iloc[-1] if len(s_series) else np.nan
        s_now = None if pd.isna(s_now) else int(s_now)
        stale = (last_global - close.index[-1]).days > STALE_DAYS
        if stale:
            s_now = None                                  # quotazione ferma: niente punteggio né segnali
        m = meta.get(t, {})
        last = float(close.iloc[-1])
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan
        r_m = [ret(close, d) for d in (30, 91, 182, 365)]
        r_m = [x for x in r_m if x is not None]
        j = col_pos.get(t)
        pillars = contrib = None
        if s_now is not None and j is not None:
            pillars = {p: (None if pd.isna(pct_last[p].get(t)) else round(float(pct_last[p][t]) * 100))
                       for p in model.PILLARS}
            contrib = {p: round(float(beta[k][B_last[j, k]]), 5) for k, p in enumerate(model.PILLARS)}
        e_now = edge[t].iloc[-1] if t in edge else np.nan
        cal = calib_for(s_now, mkt) if s_now is not None else None
        s4 = s_series.iloc[-5] if len(s_series) > 5 else np.nan
        a = {
            "t": t, "id": safe_id(t), "name": name, "type": typ, "country": country, "market": mkt,
            "sector": m.get("sector") or "", "industry": m.get("industry") or "", "theme": themes.get(t, ""),
            "cap": m.get("cap"), "capClass": cap_class(m.get("cap")), "earnings": m.get("earnings"),
            "price": r4(last), "date": close.index[-1].strftime("%Y-%m-%d"),
            "r1d": r4(close.iloc[-1] / close.iloc[-2] - 1), "r1w": r4(ret(close, 7)), "r1m": r4(ret(close, 30)),
            "r3m": r4(ret(close, 91)), "r6m": r4(ret(close, 182)), "r1y": r4(ret(close, 365)),
            "ytd": r4(ytd(close)), "momAvg": r4(np.mean(r_m)) if r_m else None,
            "above200": None if pd.isna(sma200) else bool(last > sma200),
            "score": s_now, "label": "FERMO" if stale else model.label_for(s_now) if s_now is not None else "N/D",
            "stale": stale or None, "ccy": currency_of(t, typ, country, m.get("currency")),
            "delta4w": None if s_now is None or pd.isna(s4) else int(s_now - s4),
            "edge": r4(e_now), "pillars": pillars, "contrib": contrib,
            "exp3m": cal["median"] if cal else None, "hit3m": cal["hit"] if cal else None,
            "hitLo": cal.get("hit_lo") if cal else None, "hitHi": cal.get("hit_hi") if cal else None,
            "nInd": cal.get("n_ind") if cal else None,
            "spark": [r4(v) for v in close.iloc[-64:].values[::4]],
        }
        assets.append(a)

    # classifiche nel mercato e nel settore
    for g in set(a["market"] for a in assets):
        pool = sorted([a for a in assets if a["market"] == g and a["score"] is not None],
                      key=lambda a: (a["edge"] or -9), reverse=True)
        for i, a in enumerate(pool):
            a["rank"], a["of"] = i + 1, len(pool)
        for sec in set(a["sector"] for a in pool if a["sector"]):
            sp = [a for a in pool if a["sector"] == sec]
            for i, a in enumerate(sp):
                a["secRank"], a["secOf"] = i + 1, len(sp)

    # ---------------- schede strumento (hist/) + regola 80/60
    by_t = {a["t"]: a for a in assets}
    for a in assets:
        t = a["t"]
        df = prices[t]
        close = df["Close"]
        h = df[df.index > df.index[-1] - pd.Timedelta(days=380)]
        sma50 = close.rolling(50).mean().reindex(h.index)
        sma200 = close.rolling(200).mean().reindex(h.index)
        rec = {"t": t, "d": [d.strftime("%Y-%m-%d") for d in h.index],
               "o": [r4(v) for v in h["Open"]], "h": [r4(v) for v in h["High"]],
               "l": [r4(v) for v in h["Low"]], "c": [r4(v) for v in h["Close"]],
               "sma50": [r4(v) for v in sma50], "sma200": [r4(v) for v in sma200]}
        vol = float(np.log(close).diff().iloc[-126:].std() * math.sqrt(252))
        rec["vol"] = round(vol, 4)
        if a["score"] is not None:
            s = score[t].dropna()
            s = s[s.index >= pd.Timestamp(res["first_year"], 1, 1)]
            bench = bench_w.get(a["market"])
            trades, state = model.trades_for(s, W[t].reindex(s.index), None if bench is None else bench.reindex(s.index))
            a["inRule"] = bool(state.iloc[-1]) if len(state) else False
            if trades and trades[-1]["open"]:
                a["ruleSince"] = trades[-1]["in"]
                a["ruleRet"] = trades[-1]["ret"]
            # ingressi/uscite recenti per il Radar
            if len(state) > 4:
                changed = state.iloc[-5:].astype(int).diff().fillna(0)
                if (changed > 0).any():
                    radar_mom.append({"t": t, "event": "ENTRATA", "date": changed[changed > 0].index[-1].strftime("%Y-%m-%d")})
                elif (changed < 0).any():
                    radar_mom.append({"t": t, "event": "USCITA", "date": changed[changed < 0].index[-1].strftime("%Y-%m-%d")})
            rec["score"] = {"d": [d.strftime("%Y-%m-%d") for d in s.index[-520:]], "v": [int(v) for v in s.values[-520:]]}
            ph = {p: res["pct"][p][t].iloc[-104:] for p in model.PILLARS}
            rec["pillarsHist"] = {"d": [d.strftime("%Y-%m-%d") for d in W.index[-104:]],
                                  **{p: [None if pd.isna(v) else round(float(v) * 100) for v in ph[p].values] for p in model.PILLARS}}
            rec["trades"] = trades
            rec["stats"] = model.trade_stats(trades)
            rec["bench"] = BENCH.get(a["market"]) or "media del mercato"
            a["ruleStats"] = {k: rec["stats"].get(k) for k in ("n", "wins", "avg", "payoff")}
        rec["seasonality"] = extras.monthly_seasonality(close)
        win = extras.seasonal_window(close)
        rec["window"] = win
        a["window"] = win
        with open(os.path.join(HIST, a["id"] + ".json"), "w") as f:
            json.dump(rec, f, separators=(",", ":"))

    # ---------------- radar
    radar = {"seasonal": [{"t": a["t"], **a["window"]} for a in assets if a.get("window") and not a.get("stale")],
             "momentum": [r for r in radar_mom if r["t"] in by_t]}
    radar["seasonal"].sort(key=lambda r: -(by_t[r["t"]]["score"] or 0))
    radar["combo"] = [r for r in radar["seasonal"] if by_t[r["t"]].get("inRule")]
    for a in assets:
        a.pop("window", None)

    # ---------------- rotation
    rotation = {}
    for key, (title, tks, bench) in rotation_sets().items():
        pts = extras.rrg(W, tks, bench)
        for p in pts:
            p["score"] = by_t.get(p["t"], {}).get("score")
        rotation[key] = {"title": title, "bench": bench, "items": pts}

    # ---------------- portafogli modello
    portfolios = model.model_portfolios(res, res["first_year"])

    # ---------------- news e macro
    today = pd.Timestamp(datetime.now().date())
    earnings = sorted([{"t": a["t"], "date": a["earnings"]} for a in assets
                       if a.get("earnings") and today - pd.Timedelta(days=7) <= pd.Timestamp(a["earnings"]) <= today + pd.Timedelta(days=45)],
                      key=lambda e: e["date"])
    news = {"earnings": earnings, "calendar": extras.fetch_macro_calendar(DEMO), "cot": extras.fetch_cot(DEMO)}

    # ---------------- dashboard
    macro, _ = build_macro(dict(prices))
    groups = {k: {"label": lbl, "items": [i[0] for i in items if i[0] in by_t]} for k, (lbl, items) in GROUPS.items()}
    picks = sorted([a for a in assets if a["score"] and a["type"] in ("Azione", "ETF", "Indice", "Cripto")],
                   key=lambda a: (a["edge"] or -9), reverse=True)
    reg_now = res["regime"].dropna()
    dashboard = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "demo": DEMO, "macro": macro, "sentiment": build_sentiment(assets), "risk": build_risk(by_t),
        "groups": groups, "panels": PANELS, "picks": [a["t"] for a in picks[:10]],
        "themes": [{"name": k, "items": [t for t, _ in v if t in by_t]} for k, v in THEMES.items()],
        "calib": calib, "calibMkt": res["calib_mkt"], "firstYear": res["first_year"], "fx": fx,
        "stale": sum(1 for a in assets if a.get("stale")),
        "usRegime": ["ESPANSIONE", "REFLAZIONE", "STAGFLAZIONE", "DEFLAZIONE"][int(reg_now.iloc[-1])] if len(reg_now) else None,
        "pillarNames": model.PILLAR_NAMES,
        "markets": {g: len([a for a in assets if a["market"] == g and a["score"] is not None]) for g in BENCH},
        "bench": BENCH,
        "model": res["cfg"],
        "tuning": _tuning_summary(),
    }
    dump("assets.json", assets)
    dump("dashboard.json", dashboard, pretty=True)
    dump("radar.json", radar)
    dump("rotation.json", rotation)
    dump("portfolios.json", portfolios)
    dump("news.json", news)
    keep = {a["id"] + ".json" for a in assets}
    for fn in os.listdir(HIST):
        if fn not in keep:
            os.remove(os.path.join(HIST, fn))
    print(f"Fatto: {len(assets)} strumenti, {sum(a['score'] is not None for a in assets)} con punteggio.")


if __name__ == "__main__":
    main()
