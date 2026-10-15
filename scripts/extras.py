"""Calcoli accessori: stagionalità, finestre del Radar, rotazione relativa (RRG),
Commitment of Traders, calendari earnings e macro."""
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

UA = {"User-Agent": "Mozilla/5.0 (Quadrante personal dashboard)"}


def http_json(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# --------------------------------------------------------------------------
# Stagionalità mensile
# --------------------------------------------------------------------------
def monthly_seasonality(close):
    m = close.resample("ME").last()
    r = m.pct_change(fill_method=None).dropna()
    if len(r) < 24:
        return None
    out = []
    for mo in range(1, 13):
        x = r[r.index.month == mo]
        out.append({"m": mo, "avg": round(float(x.mean()), 4) if len(x) else None,
                    "win": round(float((x > 0).mean()), 3) if len(x) else None, "n": int(len(x))})
    return {"months": out, "years": int(len(r) / 12)}


# --------------------------------------------------------------------------
# Radar: finestre stagionali imminenti
# --------------------------------------------------------------------------
def seasonal_window(close, today=None, lookahead=14, durations=(30, 45, 60), min_years=5):
    """Miglior finestra che inizia nei prossimi 'lookahead' giorni, sugli anni passati."""
    s = close.dropna()
    if len(s) < 260 * min_years:
        return None
    today = today or s.index[-1]
    idx = s.index.values
    vals = s.values
    best = None
    for off in range(0, lookahead + 1):
        start0 = today + pd.Timedelta(days=off)
        for d in durations:
            rets = []
            for y in range(1, 21):
                st = start0 - pd.DateOffset(years=y)
                en = st + pd.Timedelta(days=d)
                if st < s.index[0] or en > s.index[-1]:
                    continue
                i0 = np.searchsorted(idx, np.datetime64(st), side="right") - 1
                i1 = np.searchsorted(idx, np.datetime64(en), side="right") - 1
                if i0 < 0 or i1 <= i0:
                    continue
                rets.append(vals[i1] / vals[i0] - 1)
            if len(rets) < min_years:
                continue
            rets = np.array(rets)
            win, avg = float((rets > 0).mean()), float(rets.mean())
            key = win * 2 + avg * 10
            if win >= 0.7 and avg > 0 and (best is None or key > best["_k"]):
                best = {"_k": key, "start": start0.strftime("%d-%m"), "end": (start0 + pd.Timedelta(days=d)).strftime("%d-%m"),
                        "startDate": start0.strftime("%Y-%m-%d"), "days": d, "win": round(win, 3),
                        "avg": round(avg, 4), "years": int(len(rets)),
                        "worst": round(float(rets.min()), 4), "best": round(float(rets.max()), 4)}
    if best:
        best.pop("_k")
    return best


# --------------------------------------------------------------------------
# Rotazione relativa (stile Relative Rotation Graph)
# --------------------------------------------------------------------------
def rrg(W, tickers, bench, tail=8):
    out = []
    b = W[bench] if bench and bench in W else None
    for t in tickers:
        if t not in W or t == bench:
            continue
        p = W[t]
        rs = p / b if b is not None else p
        rs = rs.dropna()
        if len(rs) < 40:
            continue
        x = (100 * rs / rs.rolling(13).mean()).ewm(span=3).mean()
        y = (100 * x / x.shift(4)).ewm(span=3).mean()
        df = pd.DataFrame({"x": x, "y": y}).dropna().iloc[-(tail + 6):]
        if len(df) < tail:
            continue
        q = df.apply(lambda r: quadrant(r.x, r.y), axis=1)
        cur = q.iloc[-1]
        weeks_in = int((q[::-1] != cur).values.argmax()) if (q != cur).any() else len(q)
        lw = np.log(p.dropna())
        rel = None
        if len(lw) > 13:
            r_a = lw.iloc[-1] - lw.iloc[-14]
            r_b = (math.log(b.dropna().iloc[-1] / b.dropna().iloc[-14]) if b is not None else 0)
            rel = round(float((math.exp(r_a) - 1) - (math.exp(r_b) - 1)), 4)
        out.append({
            "t": t, "quad": cur, "weeks": weeks_in, "rel3m": rel,
            "path": [[round(float(a), 2), round(float(c), 2)] for a, c in df[["x", "y"]].values[-tail:]],
            "dates": [d.strftime("%Y-%m-%d") for d in df.index[-tail:]],
        })
    return out


def quadrant(x, y):
    if x >= 100 and y >= 100:
        return "LEADING"
    if x >= 100:
        return "WEAKENING"
    if y < 100:
        return "LAGGING"
    return "IMPROVING"


# --------------------------------------------------------------------------
# Commitment of Traders (CFTC, report Legacy futures-only, API pubblica)
# --------------------------------------------------------------------------
COT_CONTRACTS = [
    ("088691", "Oro", "Metalli"), ("084691", "Argento", "Metalli"), ("085692", "Rame", "Metalli"),
    ("067651", "Petrolio WTI", "Energia"), ("023651", "Gas naturale", "Energia"),
    ("002602", "Mais", "Agricoli"), ("001602", "Grano", "Agricoli"), ("005602", "Soia", "Agricoli"),
    ("13874A", "S&P 500 E-mini", "Indici"), ("209742", "Nasdaq 100 E-mini", "Indici"),
    ("239742", "Russell 2000 E-mini", "Indici"), ("1170E1", "VIX", "Indici"),
    ("099741", "Euro", "Valute"), ("097741", "Yen giapponese", "Valute"), ("096742", "Sterlina", "Valute"),
    ("092741", "Franco svizzero", "Valute"), ("090741", "Dollaro canadese", "Valute"),
    ("232741", "Dollaro australiano", "Valute"), ("098662", "Dollar Index", "Valute"),
    ("043602", "Treasury 10 anni", "Tassi"), ("020601", "Treasury Bond", "Tassi"),
    ("133741", "Bitcoin (CME)", "Cripto"),
]


def fetch_cot(demo=False):
    if demo:
        return demo_cot()
    codes = ",".join(f"'{c}'" for c, _, _ in COT_CONTRACTS)
    since = (datetime.utcnow() - timedelta(days=3 * 365 + 30)).strftime("%Y-%m-%d")
    params = {
        "$select": "report_date_as_yyyy_mm_dd,cftc_contract_market_code,open_interest_all,"
                   "noncomm_positions_long_all,noncomm_positions_short_all,"
                   "comm_positions_long_all,comm_positions_short_all",
        "$where": f"cftc_contract_market_code in({codes}) AND report_date_as_yyyy_mm_dd >= '{since}'",
        "$limit": "50000",
    }
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json?" + urllib.parse.urlencode(params)
    try:
        rows = http_json(url, timeout=60)
    except Exception as e:
        print("  COT non disponibile:", e)
        return []
    df = pd.DataFrame(rows)
    if df.empty:
        return []
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    for c in ["open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all",
              "comm_positions_long_all", "comm_positions_short_all"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = []
    for code, name, cat in COT_CONTRACTS:
        d = df[df["cftc_contract_market_code"] == code].sort_values("date").drop_duplicates("date")
        if len(d) < 20:
            continue
        net = d["noncomm_positions_long_all"] - d["noncomm_positions_short_all"]
        comm = d["comm_positions_long_all"] - d["comm_positions_short_all"]
        out.append(cot_record(name, cat, d["date"], net, comm, d["open_interest_all"]))
    return out


def cot_record(name, cat, dates, net, comm, oi):
    net, comm, oi = list(net), list(comm), list(oi)
    lo, hi = min(net), max(net)
    idx = (net[-1] - lo) / (hi - lo) * 100 if hi > lo else 50
    return {
        "name": name, "cat": cat, "date": pd.Timestamp(list(dates)[-1]).strftime("%Y-%m-%d"),
        "net": int(net[-1]), "chg": int(net[-1] - net[-2]), "comm": int(comm[-1]), "oi": int(oi[-1]),
        "netPctOi": round(net[-1] / oi[-1], 4) if oi[-1] else None, "index": round(idx),
        "hist": [[pd.Timestamp(d).strftime("%Y-%m-%d"), int(n)] for d, n in zip(list(dates)[-156:], net[-156:])],
    }


def demo_cot():
    rng = np.random.default_rng(3)
    dates = pd.date_range(end=datetime.utcnow(), periods=156, freq="W-TUE")
    out = []
    for _, name, cat in COT_CONTRACTS:
        net = np.cumsum(rng.normal(0, 5000, len(dates))) + rng.normal(0, 40000)
        comm = -net * rng.uniform(0.7, 1.1)
        oi = np.abs(net).max() * rng.uniform(3, 8) + np.zeros(len(dates))
        out.append(cot_record(name, cat, dates, np.round(net), np.round(comm), np.round(oi)))
    return out


# --------------------------------------------------------------------------
# Calendario macro (feed settimanale pubblico di ForexFactory)
# --------------------------------------------------------------------------
def fetch_macro_calendar(demo=False):
    if demo:
        base = datetime.utcnow().replace(hour=12, minute=30, second=0, microsecond=0)
        ev = [("USD", "CPI m/m", "High"), ("EUR", "Fiducia ZEW", "Medium"), ("USD", "Richieste sussidi", "Medium"),
              ("GBP", "PIL m/m", "High"), ("JPY", "Bilancia commerciale", "Low"), ("USD", "Vendite al dettaglio", "High"),
              ("CNY", "PIL a/a", "High"), ("EUR", "Decisione tassi BCE", "High"), ("CAD", "CPI m/m", "High")]
        return [{"date": (base + timedelta(hours=7 * i)).strftime("%Y-%m-%dT%H:%M:%SZ"), "country": c, "title": t,
                 "impact": imp, "forecast": "0.3%", "previous": "0.2%"} for i, (c, t, imp) in enumerate(ev)]
    out = []
    for feed in ("ff_calendar_thisweek", "ff_calendar_nextweek"):
        try:
            for e in http_json(f"https://nfs.faireconomy.media/{feed}.json"):
                out.append({k: e.get(k) for k in ("date", "country", "title", "impact", "forecast", "previous", "actual")})
        except Exception as ex:
            print("  calendario macro non disponibile:", feed, ex)
    return out
