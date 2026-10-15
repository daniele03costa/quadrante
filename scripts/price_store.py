"""Archivio prezzi incrementale (cache/prices.parquet).

- Prima esecuzione: scarica tutto lo storico dal 2004, salvando l'archivio ogni ~500 ticker:
  se Yahoo blocca o l'Action va in timeout, l'esecuzione successiva riparte da dove si era fermata.
- Tempo massimo di download per esecuzione: MAX_DOWNLOAD_MIN (variabile d'ambiente, default 100 minuti).
  Quello che manca viene completato all'esecuzione successiva; nel frattempo il sito usa ciò che c'è.
- Esecuzioni successive: scarica solo gli ultimi 15 giorni e li accoda. Se un prezzo già salvato non
  coincide più (dividendi/split ricalcolano lo storico 'adjusted'), riscarica quel ticker per intero.
- Ogni giorno riscarica per intero 1/7 dei ticker a rotazione, così in una settimana l'archivio è ripulito.
"""
import os
import time
import zlib
from datetime import datetime

import numpy as np
import pandas as pd

COLS = ["Open", "High", "Low", "Close"]


def _download(tickers, start=None, period=None, chunk=50, pause=1.5, on_progress=None, deadline=None):
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), chunk):
        if deadline and time.time() > deadline:
            print(f"  tempo massimo raggiunto: {len(tickers) - i} ticker rimandati alla prossima esecuzione")
            break
        part = tickers[i:i + chunk]
        df = None
        for attempt in range(4):
            try:
                kw = {"start": start} if start else {"period": period}
                df = yf.download(part, interval="1d", group_by="ticker", auto_adjust=True,
                                 threads=True, progress=False, **kw)
                break
            except Exception as e:
                print("  download fallito, riprovo:", e)
                time.sleep(15 * (attempt + 1))
        if df is not None and not df.empty:
            for t in part:
                try:
                    sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
                    sub = sub[COLS].dropna(subset=["Close"])
                    sub = sub[sub["Close"] > 0]
                    if len(sub):
                        sub.index = pd.to_datetime(sub.index).tz_localize(None).normalize()
                        out[t] = sub[~sub.index.duplicated()].astype("float32")
                except Exception:
                    pass
        if (i // chunk) % 10 == 0:
            print(f"  prezzi: {min(i + chunk, len(tickers))}/{len(tickers)} ({len(out)} validi)")
        if on_progress and (i // chunk) % 10 == 9:
            on_progress(out)
        time.sleep(pause)
    return out


def _save(stored, path):
    frames = []
    for t, df in stored.items():
        f = df.astype("float32").copy()
        f["t"] = t
        frames.append(f.reset_index(names="date"))
    long = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "t", *COLS])
    tmp = path + ".tmp"
    long.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _rotation_day(t):
    return zlib.crc32(t.encode()) % 7


def load_prices(tickers, cache_path, start="2004-01-01", min_rows=260):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    deadline = time.time() + float(os.environ.get("MAX_DOWNLOAD_MIN", "100")) * 60
    stored = {}
    if os.path.exists(cache_path):
        try:
            long = pd.read_parquet(cache_path)
            for t, g in long.groupby("t"):
                stored[t] = g.set_index("date")[COLS].sort_index()
            print(f"Archivio prezzi: {len(stored)} ticker in cache")
        except Exception as e:
            print("  archivio illeggibile, riparto da zero:", e)
    today = datetime.utcnow().weekday()
    new = [t for t in tickers if t not in stored]
    old = [t for t in tickers if t in stored]
    refetch = list(new) + [t for t in old if _rotation_day(t) == today]
    rest = [t for t in old if _rotation_day(t) != today]
    if rest:
        recent = _download(rest, period="15d", chunk=100, deadline=deadline)
        for t in rest:
            r = recent.get(t)
            s = stored[t]
            if r is None or r.empty:
                continue
            common = r.index.intersection(s.index)
            if len(common) and np.nanmax(np.abs(r.loc[common, "Close"].values / s.loc[common, "Close"].values - 1)) > 0.003:
                refetch.append(t)                       # storico ricalcolato: riscarico tutto
            else:
                stored[t] = pd.concat([s[s.index < r.index[0]], r]).sort_index()
    if refetch:
        # prima i ticker mai scaricati, poi quelli da ripulire
        print(f"Storico completo da scaricare: {len(refetch)} ticker ({len(new)} nuovi)")

        def checkpoint(partial):
            stored.update(partial)
            _save(stored, cache_path)
            print(f"  archivio salvato ({len(stored)} ticker)")

        stored.update(_download(refetch, start=start, on_progress=checkpoint, deadline=deadline))
    _save({t: stored[t] for t in tickers if t in stored}, cache_path)
    missing = [t for t in tickers if t not in stored]
    if missing:
        print(f"  {len(missing)} ticker senza prezzi (es. {', '.join(missing[:10])})")
    prices = {t: stored[t] for t in tickers if t in stored and len(stored[t]) >= min_rows}
    return {t: df.astype("float64") for t, df in prices.items()}
