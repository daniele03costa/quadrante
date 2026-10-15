"""Quadrante Score — modello quantitativo a 5 pilastri.

Ricostruisce l'impostazione descritta pubblicamente dallo Smart Quant di Quantaste
(con calcoli e pesi propri, appresi dai dati):

  1. Cinque pilastri per ogni strumento, ogni settimana:
       Macro        rendimento storico dello strumento nel regime economico attuale
       Tendenza     direzione e forza del trend di lungo periodo
       Momentum     accelerazione recente del prezzo
       Stagionalità comportamento storico nei prossimi 3 mesi dell'anno
       Rischio      volatilità rispetto al proprio mercato
     Ogni pilastro diventa un percentile (0-100) dentro il proprio mercato.
  2. Obiettivo: extra-rendimento a 3 mesi (13 settimane) rispetto alla mediana del mercato.
  3. Contributi: regressione ridge sui decili dei 5 pilastri, stimata walk-forward
     (ogni anno si usa solo il passato) -> contributo in % di extra-rendimento atteso.
  4. Vantaggio atteso = somma dei contributi.
     Punteggio 1-99 = posizione in classifica del vantaggio dentro il mercato.
  5. Regola operativa: dentro quando il punteggio sale a 80+, fuori sotto 60.
"""
import math

import numpy as np
import pandas as pd

H = 13                      # orizzonte in settimane (~3 mesi)
PILLARS = ["macro", "trend", "momentum", "season", "risk"]
PILLAR_NAMES = {"macro": "Macro", "trend": "Tendenza", "momentum": "Momentum",
                "season": "Stagionalità", "risk": "Rischio"}
NB = 10                     # decili
DEFAULT_CFG = {"nb": 10, "lam_frac": 0.002, "smooth": 4, "pillars": ["macro", "trend", "momentum", "season", "risk"]}
ENTRY, EXIT = 80, 60


def label_for(score):
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "N/D"
    if score >= 90:
        return "STRONG BUY"
    if score >= 80:
        return "BUY"
    if score >= 60:
        return "HOLD"
    if score >= 30:
        return "SELL"
    return "STRONG SELL"


# --------------------------------------------------------------------------
# Pannelli di prezzo
# --------------------------------------------------------------------------
def build_panels(prices):
    close = pd.DataFrame({t: df["Close"] for t, df in prices.items()}).sort_index()
    close = close[~close.index.duplicated()].ffill(limit=5)
    W = close.resample("W-FRI").last()
    W = W.iloc[:-1] if len(W) > 1 and W.index[-1] > close.index[-1] + pd.Timedelta(days=6) else W
    lr = np.log(close).diff()
    vol = (lr.rolling(63, min_periods=40).std() * math.sqrt(252)).resample("W-FRI").last().reindex(W.index)
    sma200 = close.rolling(200, min_periods=180).mean().resample("W-FRI").last().reindex(W.index)
    return close, W, vol, sma200


def group_median(df, groups):
    out = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for g, cols in groups.items():
        cols = [c for c in cols if c in df.columns]
        if cols:
            med = df[cols].median(axis=1)
            for c in cols:
                out[c] = med
    return out


def group_rank(df, groups):
    out = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for g, cols in groups.items():
        cols = [c for c in cols if c in df.columns]
        if cols:
            out[cols] = df[cols].rank(axis=1, pct=True)
    return out


# --------------------------------------------------------------------------
# Regime macro storico (USA) per il pilastro Macro
# --------------------------------------------------------------------------
def regime_history(index, fred_growth=None, fred_infl=None, W=None):
    """Regime settimanale 0..3: 0 Espansione, 1 Reflazione, 2 Stagflazione, 3 Deflazione.
    Dati FRED pubblicati con ~1 mese di ritardo: li sposto avanti di 2 mesi.
    Senza FRED uso proxy di mercato (S&P 500 e paniere materie prime)."""
    def accel(s):
        s = s.dropna()
        per_year = 4 if pd.Series(s.index).diff().dt.days.median() > 60 else 12
        yoy = s / s.shift(per_year) - 1
        a = yoy - yoy.shift(per_year // 2)
        a.index = a.index + pd.DateOffset(months=2)
        return a

    g = i = None
    if fred_growth is not None and fred_infl is not None:
        g = accel(fred_growth).reindex(index, method="ffill")
        i = accel(fred_infl).reindex(index, method="ffill")
    if g is None or g.notna().sum() < 52 * 5:
        lw = np.log(W)
        g = (lw["^GSPC"] - lw["^GSPC"].shift(26)) if "^GSPC" in W else pd.Series(0.0, index=index)
        i = (lw["DBC"] - lw["DBC"].shift(26)) if "DBC" in W else pd.Series(0.0, index=index)
    reg = pd.Series(np.nan, index=index)
    gu, iu = g > 0, i > 0
    reg[gu & ~iu] = 0
    reg[gu & iu] = 1
    reg[~gu & iu] = 2
    reg[~gu & ~iu] = 3
    reg[g.isna() | i.isna()] = np.nan
    return reg


# --------------------------------------------------------------------------
# Pilastri grezzi
# --------------------------------------------------------------------------
def raw_pillars(W, vol, sma200, groups, regime):
    lw = np.log(W)
    v = vol.where(vol > 0)

    def t(k):
        return (lw - lw.shift(k)) / (v * math.sqrt(k / 52))

    trend = 0.5 * (np.log(W / sma200) / v) + 0.5 * ((lw.shift(4) - lw.shift(52)) / (v * math.sqrt(48 / 52)))
    momentum = (t(4) + t(13) + (t(13) - t(26))) / 3
    risk = -(v / group_median(v, groups))

    fwd = lw.shift(-H) - lw                                  # rendimento futuro 13 settimane
    excess = fwd - group_median(fwd, groups)                 # obiettivo: batte il suo mercato?

    seas_vals, seas_cnt = 0, 0
    for y in range(1, 16):
        past = fwd.shift(52 * y)
        seas_vals = seas_vals + past.fillna(0)
        seas_cnt = seas_cnt + past.notna()
    season = (seas_vals / seas_cnt.replace(0, np.nan)).where(seas_cnt >= 3)

    known = excess.shift(H)                                  # extra-rendimento ormai noto
    reg_then = regime.shift(H)
    macro = pd.DataFrame(np.nan, index=W.index, columns=W.columns)
    shape = known.shape
    for k in range(4):
        m = np.broadcast_to((reg_then == k).values[:, None], shape)
        vals = known.where(m & known.notna().values)
        s = vals.fillna(0).cumsum()
        c = vals.notna().cumsum()
        mean_k = (s / c.replace(0, np.nan)).where(c >= 8)
        now = np.broadcast_to((regime == k).values[:, None], shape)
        macro = macro.where(~now, mean_k)
    return {"macro": macro, "trend": trend, "momentum": momentum, "season": season, "risk": risk}, excess, fwd


# --------------------------------------------------------------------------
# Stima dei contributi (ridge su decili) e punteggio
# --------------------------------------------------------------------------
def to_buckets(pct, nb=NB):
    b = np.floor(pct.values * nb)
    b = np.where(np.isnan(b), nb // 2, np.clip(b, 0, nb - 1))
    return b.astype(np.int16)


def fit_contrib(B, y, lam_frac=0.002, nb=NB):
    """B: (n,5) indici di fascia, y: extra-rendimento. Restituisce beta (5, nb) centrato."""
    NB = nb
    B = B.astype(np.int64)
    n = len(y)
    P = len(PILLARS)
    idx = B + np.arange(P) * NB
    K = P * NB
    XtX = np.zeros(K * K)
    for a in range(P):
        for b in range(P):
            XtX += np.bincount(idx[:, a] * K + idx[:, b], minlength=K * K)
    XtX = XtX.reshape(K, K)
    Xty = np.zeros(K)
    for a in range(P):
        Xty += np.bincount(idx[:, a], weights=y, minlength=K)
    lam = max(1.0, lam_frac * n)
    beta = np.linalg.solve(XtX + lam * np.eye(K), Xty).reshape(P, NB)
    counts = np.array([np.bincount(B[:, a], minlength=NB) for a in range(P)], dtype=float)
    beta -= (beta * counts).sum(1, keepdims=True) / np.maximum(counts.sum(1, keepdims=True), 1)
    return beta


def run_model(prices, groups_of, fred_growth=None, fred_infl=None, min_years=5, cfg=None, panels=None):
    """groups_of: {ticker: nome mercato}. cfg: parametri (vedi DEFAULT_CFG).
    panels: pannelli già calcolati (per i test ripetuti di tune.py)."""
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    nb, lam, smooth = cfg["nb"], cfg["lam_frac"], cfg["smooth"]
    close, W, vol, sma200 = panels or build_panels(prices)
    groups = {}
    for t, g in groups_of.items():
        if t in W.columns:
            groups.setdefault(g, []).append(t)
    regime = regime_history(W.index, fred_growth, fred_infl, W)
    raw, excess, fwd = raw_pillars(W, vol, sma200, groups, regime)
    pct = {p: group_rank(raw[p], groups) for p in PILLARS}

    dates, tick = W.index, W.columns
    alive = W.notna() & vol.notna()
    B = np.stack([to_buckets(pct[p], nb) if p in cfg["pillars"] else np.full(W.shape, nb // 2, dtype=np.int16)
                  for p in PILLARS], axis=-1)                              # (T, N, 5); pilastri esclusi = neutri
    Y = excess.values
    trainable = alive.values & np.isfinite(Y)

    def clipped(mask):
        """Extra-rendimenti di addestramento, tagliati all'1°/99° percentile calcolato SOLO su di essi."""
        y = Y[mask]
        lo, hi = np.percentile(y, [1, 99])
        return np.clip(y, lo, hi)

    edge = np.full((len(dates), len(tick)), np.nan)
    years = sorted(set(dates.year))
    first_year = years[0] + min_years
    betas = {}
    for yr in years:
        if yr < first_year:
            continue
        start = pd.Timestamp(yr, 1, 1)
        cutoff = start - pd.Timedelta(weeks=H)
        rows = (dates <= cutoff)
        m = trainable & rows[:, None]
        if m.sum() < 2000:
            continue
        beta = fit_contrib(B[m], clipped(m), lam, nb)
        betas[yr] = beta
        seg = (dates >= start) & (dates < pd.Timestamp(yr + 1, 1, 1))
        Bs = B[seg]
        edge[seg] = sum(beta[p][Bs[..., p]] for p in range(len(PILLARS)))

    # fit "live" con tutti i dati noti oggi, per l'ultima settimana
    m_all = trainable & (dates <= dates[-1] - pd.Timedelta(weeks=H))[:, None]
    beta_live = fit_contrib(B[m_all], clipped(m_all), lam, nb) if m_all.sum() >= 2000 else np.zeros((len(PILLARS), nb))
    edge[-1] = sum(beta_live[p][B[-1][..., p]] for p in range(len(PILLARS)))

    # media mobile esponenziale di 4 settimane: riduce i cambi di classifica dovuti al rumore
    edge_df = pd.DataFrame(edge, index=dates, columns=tick).ewm(span=max(1, smooth), min_periods=1).mean().where(alive & pd.DataFrame(np.isfinite(edge), index=dates, columns=tick))
    score_df = (group_rank(edge_df, groups) * 100).round().clip(1, 99).where(edge_df.notna())

    # tabella di affidabilità: fascia di punteggio -> extra-rendimento a 3 mesi (fuori campione)
    oos_rows = dates >= pd.Timestamp(first_year, 1, 1)
    calib = calibration(score_df.values, Y, oos_rows)
    calib_mkt = {}
    for g, cols in groups.items():
        j = [tick.get_loc(c) for c in cols]
        if len(j) >= 20:
            calib_mkt[g] = calibration(score_df.values[:, j], Y[:, j], oos_rows)

    return {
        "close": close, "W": W, "vol": vol, "regime": regime, "raw": raw, "pct": pct,
        "edge": edge_df, "score": score_df, "groups": groups, "beta_live": beta_live,
        "B_last": B[-1], "calib": calib, "calib_mkt": calib_mkt, "first_year": first_year, "excess": excess, "cfg": cfg,
        "panels": (close, W, vol, sma200),
    }


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def calibration(S, Y, rows, width=5):
    """Per fascia di punteggio: mediana/media dell'extra-rendimento a 3 mesi e frequenza con cui batte il mercato.
    Le finestre di 13 settimane si sovrappongono: l'intervallo di confidenza (95%, Wilson) è calcolato
    solo su osservazioni indipendenti, una ogni 13 settimane (n_ind), per non sopravvalutare la precisione."""
    out = []
    idx = np.where(rows)[0]
    ind = idx[::H]                                         # date non sovrapposte
    sc, ex = S[idx], Y[idx]
    sci, exi = S[ind], Y[ind]
    for lo_b in range(1, 100, width):
        hi_b = min(lo_b + width - 1, 99)
        mm = (sc >= lo_b) & (sc <= hi_b) & np.isfinite(ex)
        mi = (sci >= lo_b) & (sci <= hi_b) & np.isfinite(exi)
        if mm.sum() > 30 and mi.sum() > 5:
            k = int((exi[mi] > 0).sum())
            lo_ci, hi_ci = wilson(k, int(mi.sum()))
            out.append({"from": lo_b, "to": hi_b, "n": int(mm.sum()), "n_ind": int(mi.sum()),
                        "median": round(float(np.median(ex[mm])), 5), "mean": round(float(np.mean(ex[mm])), 5),
                        "hit": round(float((ex[mm] > 0).mean()), 4), "hit_lo": lo_ci, "hit_hi": hi_ci})
    return out


# --------------------------------------------------------------------------
# Regola 80/60: operazioni per strumento e portafogli modello
# --------------------------------------------------------------------------
def rule_state(score):
    """Serie booleana 'dentro la regola' (entra a 80+, esce sotto 60)."""
    inside, out = False, []
    for s in score.values:
        if np.isnan(s):
            out.append(inside)
            continue
        if not inside and s >= ENTRY:
            inside = True
        elif inside and s < EXIT:
            inside = False
        out.append(inside)
    return pd.Series(out, index=score.index)


def trades_for(score, price, bench):
    st = rule_state(score)
    trades, entry = [], None
    idx = score.index
    last = len(st) - 1
    for k in range(1, len(st)):
        # il segnale nasce dalla chiusura della settimana k: si esegue alla chiusura della settimana dopo
        if st.iloc[k] and not st.iloc[k - 1] and k < last:
            entry = k + 1
        elif not st.iloc[k] and st.iloc[k - 1] and entry is not None:
            trades.append(_trade(idx, entry, min(k + 1, last), price, bench, k + 1 > last))
            entry = None
    if entry is not None:
        trades.append(_trade(idx, entry, len(st) - 1, price, bench, True))
    return trades, st


def _trade(idx, a, b, price, bench, open_):
    p0, p1 = price.iloc[a], price.iloc[b]
    r = float(p1 / p0 - 1) if p0 and np.isfinite(p0) and np.isfinite(p1) else None
    rb = None
    if bench is not None:
        b0, b1 = bench.iloc[a], bench.iloc[b]
        if np.isfinite(b0) and np.isfinite(b1) and b0:
            rb = float(b1 / b0 - 1)
    return {"in": idx[a].strftime("%Y-%m-%d"), "out": idx[b].strftime("%Y-%m-%d"),
            "weeks": int(b - a), "ret": None if r is None else round(r, 4),
            "bench": None if rb is None else round(rb, 4), "open": open_}


def trade_stats(trades):
    closed = [t for t in trades if not t["open"] and t["ret"] is not None]
    if not closed:
        return {"n": 0}
    rets = np.array([t["ret"] for t in closed])
    wins, losses = rets[rets > 0], rets[rets <= 0]
    beat = [t for t in closed if t["bench"] is not None and t["ret"] > t["bench"]]
    return {
        "n": len(closed), "wins": int((rets > 0).sum()), "avg": round(float(rets.mean()), 4),
        "avg_bench": round(float(np.mean([t["bench"] for t in closed if t["bench"] is not None])), 4)
        if any(t["bench"] is not None for t in closed) else None,
        "best": round(float(rets.max()), 4), "worst": round(float(rets.min()), 4),
        "avg_win": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loss": round(float(losses.mean()), 4) if len(losses) else None,
        "payoff": round(float(wins.mean() / -losses.mean()), 2) if len(wins) and len(losses) and losses.mean() < 0 else None,
        "median_weeks": int(np.median([t["weeks"] for t in closed])),
        "beat": len(beat),
        "cum": round(float(np.prod(1 + rets) - 1), 4),
        "cum_bench": round(float(np.prod([1 + t["bench"] for t in closed if t["bench"] is not None]) - 1), 4)
        if any(t["bench"] is not None for t in closed) else None,
    }


def model_portfolios(res, start_year):
    """Per ogni mercato: portafoglio equipesato degli strumenti 'dentro la regola' contro il mercato."""
    W, score = res["W"], res["score"]
    ret = W.pct_change(fill_method=None).shift(-1)                # rendimento della settimana successiva
    out = {}
    states = {t: rule_state(score[t]) for t in score.columns}
    # posizioni decise alla chiusura della settimana t-1, rendimento da t a t+1 (nessun uso della stessa chiusura)
    S = pd.DataFrame(states).reindex(index=W.index).fillna(False).astype(bool).shift(1, fill_value=False)
    score = score.shift(1)
    for g, cols in res["groups"].items():
        cols = [c for c in cols if c in W.columns]
        if len(cols) < 5:
            continue
        sel = (W.index >= pd.Timestamp(start_year, 1, 1))
        r = ret.loc[sel, cols]
        bench = r.mean(axis=1)
        rule = r.where(S.loc[sel, cols]).mean(axis=1).fillna(0)
        n_top = max(3, len(cols) // 10)
        ranks = score.loc[sel, cols].rank(axis=1, ascending=False)
        top = r.where(ranks <= n_top).mean(axis=1).fillna(0)
        held = S.loc[sel, cols].sum(axis=1)
        series = pd.DataFrame({"regola": rule, "top": top, "mercato": bench.fillna(0)}).iloc[:-1]
        eq = (1 + series).cumprod()
        out[g] = {
            "dates": [d.strftime("%Y-%m-%d") for d in eq.index],
            "curves": {k: [round(float(x), 4) for x in eq[k].values] for k in eq.columns},
            "stats": {k: perf_stats(series[k]) for k in series.columns},
            "n_top": n_top, "held_now": int(held.iloc[-1]),
            "holdings": [c for c in cols if S[c].iloc[-1]],
        }
    return out


def perf_stats(r):
    r = r.dropna()
    if len(r) < 10:
        return {}
    eq = (1 + r).cumprod()
    years = len(r) / 52
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    vol = r.std() * math.sqrt(52)
    dd = (eq / eq.cummax() - 1).min()
    return {"cagr": round(float(cagr), 4), "vol": round(float(vol), 4), "maxdd": round(float(dd), 4),
            "sharpe": round(float(cagr / vol), 2) if vol > 0 else None, "total": round(float(eq.iloc[-1] - 1), 4)}
