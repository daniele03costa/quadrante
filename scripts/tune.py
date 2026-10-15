#!/usr/bin/env python3
"""Taratura del modello sui rendimenti reali.

Prova diverse varianti (numero di fasce, regolarizzazione, smussatura, pilastri inclusi) e sceglie
quella con la migliore capacità di prevedere l'extra-rendimento a 3 mesi, misurata:
  - IC: correlazione di rango settimanale tra punteggio ed extra-rendimento futuro (media e stabilità)
  - spread: extra-rendimento medio dei punteggi >= 80 meno quello dei punteggi < 30
  - monotonia della scala di affidabilità
La scelta avviene sul periodo fino a 3 anni fa; gli ultimi 3 anni restano come verifica indipendente.

Uso:
    python scripts/tune.py          # dati reali (usa la cache prezzi di update_data.py)
    python scripts/tune.py --demo   # dati simulati

Scrive scripts/model_config.json (letto da update_data.py) e scripts/tuning_report.json.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import model  # noqa: E402
import update_data as U  # noqa: E402
from universe import market_of  # noqa: E402

HERE = os.path.dirname(__file__)


def evaluate(res, holdout_years=3):
    score, excess = res["score"], res["excess"]
    dates = score.index
    split = dates[-1] - pd.DateOffset(years=holdout_years) - pd.Timedelta(weeks=model.H)
    out = {}
    for name, mask in (("selezione", (dates >= pd.Timestamp(res["first_year"], 1, 1)) & (dates < split)),
                       ("verifica", dates >= split)):
        S, X = score.loc[mask], excess.loc[mask]
        ics = []
        for d in S.index:
            s, x = S.loc[d], X.loc[d]
            ok = s.notna() & x.notna()
            if ok.sum() > 30:
                ics.append(s[ok].rank().corr(x[ok].rank()))
        s_all, x_all = S.values.ravel(), X.values.ravel()
        ok = np.isfinite(s_all) & np.isfinite(x_all)
        s_all, x_all = s_all[ok], x_all[ok]
        top, bot = x_all[s_all >= 80], x_all[s_all < 30]
        buckets = [np.median(x_all[(s_all >= lo) & (s_all < lo + 10)]) for lo in range(0, 100, 10) if ((s_all >= lo) & (s_all < lo + 10)).sum() > 50]
        mono = pd.Series(buckets).rank().corr(pd.Series(range(len(buckets))).rank()) if len(buckets) > 3 else None
        ics = np.array([i for i in ics if np.isfinite(i)])
        out[name] = {
            "ic": round(float(ics.mean()), 4) if len(ics) else None,
            "ic_ir": round(float(ics.mean() / ics.std()), 3) if len(ics) > 2 and ics.std() > 0 else None,
            "spread": round(float(top.mean() - bot.mean()), 4) if len(top) and len(bot) else None,
            "hit80": round(float((top > 0).mean()), 3) if len(top) else None,
            "mono": round(float(mono), 3) if mono is not None else None,
            "weeks": int(len(ics)),
        }
    # affidabilità delle probabilità: la % che batte il mercato per fascia è stabile tra i due periodi?
    def hits(mask):
        S, X = score.loc[mask].values.ravel(), excess.loc[mask].values.ravel()
        ok = np.isfinite(S) & np.isfinite(X)
        S, X = S[ok], X[ok]
        return {lo: float((X[(S >= lo) & (S < lo + 10)] > 0).mean()) for lo in range(0, 100, 10) if ((S >= lo) & (S < lo + 10)).sum() > 100}
    h1 = hits((dates >= pd.Timestamp(res["first_year"], 1, 1)) & (dates < split))
    h2 = hits(dates >= split)
    common = [k for k in h1 if k in h2]
    out["calib_err"] = round(float(np.mean([abs(h1[k] - h2[k]) for k in common])), 4) if common else None
    sc = score.dropna(how="all")
    out["turnover"] = round(float(sc.diff().abs().mean().mean()), 2)
    return out


def objective(m):
    s = m["selezione"]
    if s["ic"] is None:
        return -9
    return s["ic"] + 0.25 * (s["spread"] or 0) - 0.002 * m["turnover"]


def better(new, old, margin=0.002):
    """Accetta una variante solo se migliora in modo netto e non peggiora la verifica indipendente."""
    if new["objective"] < old["objective"] + margin:
        return False
    ni, oi = new["metrics"]["verifica"]["ic"], old["metrics"]["verifica"]["ic"]
    return ni is None or oi is None or ni >= oi - 0.005


def main():
    demo = "--demo" in sys.argv
    U.DEMO = demo
    rows = U.demo_universe(0) if demo else json.load(open(os.path.join(U.DATA, "universe.json")))["rows"]
    tickers = [r["t"] for r in rows]
    info = {r["t"]: (r["type"], r["country"]) for r in rows}
    prices = U.demo_prices(tickers) if demo else U.price_store.load_prices(tickers, os.path.join(U.ROOT, "cache", "prices.parquet"), U.START)
    markets = {t: market_of(*info[t]) for t in prices}
    fg = None if demo else U.fetch_fred("INDPRO")
    fi = None if demo else U.fetch_fred("CPIAUCSL")
    panels = model.build_panels(prices)

    tried = []

    def run(cfg, why):
        t0 = time.time()
        res = model.run_model(prices, markets, fg, fi, cfg=cfg, panels=panels)
        m = evaluate(res)
        rec = {"cfg": cfg, "why": why, "metrics": m, "objective": round(objective(m), 5), "sec": round(time.time() - t0)}
        tried.append(rec)
        print(f"{why:38s} obiettivo {rec['objective']:+.4f}  IC {m['selezione']['ic']}  spread {m['selezione']['spread']}  "
              f"verifica IC {m['verifica']['ic']}  errore prob. {m['calib_err']}  turnover {m['turnover']}  ({rec['sec']}s)")
        return rec

    best = run(dict(model.DEFAULT_CFG), "configurazione iniziale")
    for key, values in (("smooth", [1, 8, 13]), ("nb", [5, 20]), ("lam_frac", [0.0005, 0.01, 0.05])):
        for v in values:
            cfg = {**best["cfg"], key: v}
            r = run(cfg, f"{key} = {v}")
            if better(r, best):
                best = r
    for p in list(best["cfg"]["pillars"]):
        pil = [x for x in best["cfg"]["pillars"] if x != p]
        if len(pil) < 2:
            continue
        r = run({**best["cfg"], "pillars": pil}, f"senza pilastro {p}")
        if better(r, best):
            best = r

    with open(os.path.join(HERE, "model_config.json"), "w") as f:
        json.dump(best["cfg"], f, indent=1)
    with open(os.path.join(HERE, "tuning_report.json"), "w") as f:
        json.dump({"date": pd.Timestamp.now().strftime("%Y-%m-%d"), "demo": demo, "best": best, "tried": tried}, f, indent=1)
    print("\nMigliore:", best["why"], best["cfg"])
    print("Verifica sugli ultimi 3 anni:", best["metrics"]["verifica"])


if __name__ == "__main__":
    main()
