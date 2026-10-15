/* Quadrante — funzioni comuni (dati, formattazione, componenti, grafici) */
window.Q = (() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ------------------------------------------------------------ dati
  const cache = {};
  async function load(name) {
    if (!cache[name]) cache[name] = fetch(`data/${name}.json`, { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(`data/${name}.json non trovato`); return r.json(); });
    return cache[name];
  }
  const state = { assets: [], byT: {}, dash: null };
  async function boot() {
    const [d, a] = await Promise.all([load("dashboard"), load("assets")]);
    state.dash = d; state.assets = a;
    a.forEach((x) => (state.byT[x.t] = x));
  }
  const hist = {};
  async function loadHist(a) {
    if (!hist[a.id]) hist[a.id] = fetch(`data/hist/${a.id}.json`, { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error("storico non disponibile"); return r.json(); });
    return hist[a.id];
  }

  // ------------------------------------------------------------ storage locale
  const store = {
    get(k, d) { try { const v = localStorage.getItem("quadrante." + k); return v ? JSON.parse(v) : d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem("quadrante." + k, JSON.stringify(v)); } catch { /* non disponibile */ } },
  };
  let watch = store.get("watchlist", []);
  const isWatched = (t) => watch.includes(t);
  function toggleWatch(t) {
    watch = isWatched(t) ? watch.filter((x) => x !== t) : [...watch, t];
    store.set("watchlist", watch);
    $$(`.star[data-t="${CSS.escape(t)}"]`).forEach((b) => { b.classList.toggle("on", isWatched(t)); b.textContent = isWatched(t) ? "★" : "☆"; });
    document.dispatchEvent(new CustomEvent("watchlist"));
  }
  const watchlist = () => watch.slice();

  // ------------------------------------------------------------ formattazione
  const LABEL_CLASS = { "STRONG BUY": "sb", BUY: "b", HOLD: "h", SELL: "s", "STRONG SELL": "ss" };
  const scoreColor = (s) => s == null ? css("--muted") : s >= 90 ? css("--sb") : s >= 80 ? css("--b") : s >= 60 ? css("--h") : s >= 30 ? css("--s") : css("--ss");
  const pct = (v, d = 2) => v == null ? "–" : `${v > 0 ? "+" : ""}${(v * 100).toFixed(d).replace(".", ",")}%`;
  const pctCls = (v) => v == null ? "" : v >= 0 ? "pos" : "neg";
  const num = (v, d = 0) => v == null ? "–" : Number(v).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d });
  const fmtPrice = (p) => p == null ? "–" : p >= 1000 ? num(p, 0) : num(p, p < 10 ? 4 : 2);
  const fmtDate = (d, opt = { day: "numeric", month: "short", year: "numeric" }) => d ? new Date(d).toLocaleDateString("it-IT", opt) : "–";
  const shortT = (t) => t.replace(/^\^/, "").replace(/\.(MI|DE|PA|AS|MC|BR|HE|SS)$/, "").replace(/=X$|=F$|-USD$/, "").slice(0, 6);
  const labelHtml = (l) => `<span class="lbl ${LABEL_CLASS[l] || "na"}">${esc(l || "N/D")}</span>`;
  const scoreHtml = (s) => s == null ? `<span class="muted">–</span>` : `<span class="score">${s}<span class="score-bar"><i style="width:${s}%;background:${scoreColor(s)}"></i></span></span>`;
  const starHtml = (t) => `<button class="star${isWatched(t) ? " on" : ""}" data-t="${esc(t)}" title="Watchlist" aria-label="Watchlist">${isWatched(t) ? "★" : "☆"}</button>`;
  const link = (t) => `#/titolo/${encodeURIComponent(t)}`;
  const nameCell = (a) => `<a href="${link(a.t)}"><b>${esc(a.name)}</b><span>${esc(a.t)}</span></a>`;
  const PILLAR_DESC = {
    macro: "Rendimento storico dello strumento nel regime economico attuale",
    trend: "Direzione e forza del trend di lungo periodo",
    momentum: "Accelerazione recente del prezzo, corretta per la volatilità",
    season: "Comportamento storico nei prossimi tre mesi dell'anno",
    risk: "Volatilità rispetto al proprio mercato (alto = più tranquillo)",
  };
  const PILLARS = ["macro", "trend", "momentum", "season", "risk"];
  const pillarName = (p) => (state.dash?.pillarNames || {})[p] || p;

  function sparkSvg(vals, w = 90, h = 26) {
    const v = (vals || []).filter((x) => x != null);
    if (v.length < 2) return "";
    const min = Math.min(...v), max = Math.max(...v);
    const pts = v.map((y, i) => `${(i / (v.length - 1)) * w},${h - 2 - ((y - min) / (max - min || 1)) * (h - 4)}`).join(" ");
    const col = v[v.length - 1] >= v[0] ? css("--pos") : css("--neg");
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>`;
  }

  // ------------------------------------------------------------ componenti
  function gauge(el, value, label, sub, colors = [css("--ss"), css("--s"), css("--h"), css("--b"), css("--sb")]) {
    const cx = 120, cy = 116, r = 92, seg = colors.length;
    const pt = (a, rr = r) => [cx + rr * Math.cos(Math.PI * (1 - a)), cy - rr * Math.sin(Math.PI * (1 - a))];
    const active = Math.min(seg - 1, Math.floor((value / 100) * seg));
    let arcs = "";
    for (let i = 0; i < seg; i++) {
      const [x0, y0] = pt(i / seg + 0.006), [x1, y1] = pt((i + 1) / seg - 0.006);
      arcs += `<path d="M${x0},${y0} A${r},${r} 0 0 1 ${x1},${y1}" stroke="${colors[i]}" stroke-width="14" fill="none" opacity="${i === active ? 1 : 0.28}"/>`;
    }
    const [nx, ny] = pt(value / 100, r - 26);
    el.innerHTML = `<svg viewBox="0 0 240 132" role="img" aria-label="${esc(label)}: ${value} su 100">${arcs}
      <line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" stroke="${css("--text")}" stroke-width="3" stroke-linecap="round"/>
      <circle cx="${cx}" cy="${cy}" r="6" fill="${css("--text")}"/>
      <text x="22" y="130" fill="${css("--muted")}" font-size="10" text-anchor="middle">0</text>
      <text x="218" y="130" fill="${css("--muted")}" font-size="10" text-anchor="middle">100</text></svg>
      <div class="g-label">${esc(label)}</div><div class="g-sub">${esc(sub)}</div>`;
  }
  function stackBars(el, rows) {
    el.innerHTML = rows.map(([name, v, col]) => `<div class="sb-row"><span>${esc(name)}</span><div class="sb-track"><div class="sb-fill" style="width:${Math.max(0, v)}%;background:${col}"></div></div><span class="v">${v}%</span></div>`).join("");
  }
  function ring(score, size = 130) {
    if (score == null) return `<div class="empty">Punteggio non disponibile</div>`;
    const r = 54, c = 2 * Math.PI * r, col = scoreColor(score);
    return `<svg viewBox="0 0 130 130" width="${size}" height="${size}" role="img" aria-label="Punteggio ${score} su 100">
      <circle cx="65" cy="65" r="${r}" stroke="${css("--line")}" stroke-width="10" fill="none"/>
      <circle cx="65" cy="65" r="${r}" stroke="${col}" stroke-width="10" fill="none" stroke-linecap="round" stroke-dasharray="${(score / 100) * c} ${c}" transform="rotate(-90 65 65)"/>
      <text x="65" y="70" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="34" font-weight="600" fill="${css("--text")}">${score}</text>
      <text x="65" y="90" text-anchor="middle" font-size="10" fill="${css("--muted")}">/ 100</text></svg>`;
  }
  function pillarBars(a) {
    if (!a.pillars) return `<p class="muted small">Storico insufficiente per i pilastri.</p>`;
    return `<ul class="comp-list">${PILLARS.map((p) => `<li><span>${pillarName(p)}</span><span class="v">${a.pillars[p] ?? "–"}</span><span class="track"><i style="width:${a.pillars[p] ?? 0}%;background:${scoreColor(a.pillars[p])}"></i></span></li>`).join("")}</ul>`;
  }
  function tabs(keys, labels, active, onChange) {
    const el = document.createElement("div");
    el.className = "tabs"; el.setAttribute("role", "tablist");
    el.innerHTML = keys.map((k, i) => `<button class="tab" role="tab" data-k="${esc(k)}" aria-selected="${k === active}">${esc(labels[i])}</button>`).join("");
    $$(".tab", el).forEach((b) => b.addEventListener("click", () => { $$(".tab", el).forEach((x) => x.setAttribute("aria-selected", x === b)); onChange(b.dataset.k); }));
    return el;
  }

  /** Tabella ordinabile. cols: [{k, l, cls, html(a), sort(a)}]. */
  function table(container, cols, items, { sort = { key: "score", asc: false }, page = 0, onRow, empty = "Nessun risultato." } = {}) {
    let st = { ...sort }, pg = 1;
    container.innerHTML = `<div class="table-wrap"><table class="table"><thead><tr>${cols.map((c) => `<th data-k="${c.k}" class="${c.cls || ""}${c.nosort ? " nosort" : ""}">${c.l}</th>`).join("")}</tr></thead><tbody></tbody></table></div>${page ? `<div class="pager"></div>` : ""}`;
    const draw = () => {
      const col = cols.find((c) => c.k === st.key);
      const val = (a) => col?.sort ? col.sort(a) : a[st.key];
      const rows = [...items].sort((x, y) => {
        const a = val(x), b = val(y);
        if (a == null) return 1; if (b == null) return -1;
        const r = typeof a === "string" ? a.localeCompare(b, "it") : a - b;
        return st.asc ? r : -r;
      });
      const pages = page ? Math.max(1, Math.ceil(rows.length / page)) : 1;
      pg = Math.min(pg, pages);
      const view = page ? rows.slice((pg - 1) * page, pg * page) : rows;
      $$("th", container).forEach((th) => { th.classList.toggle("sorted", th.dataset.k === st.key); th.classList.toggle("asc", st.asc); });
      $("tbody", container).innerHTML = view.map((a, i) => `<tr data-t="${esc(a.t || "")}" data-i="${i}">${cols.map((c) => `<td class="${c.cls || ""}">${c.html ? c.html(a) : esc(a[c.k])}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${cols.length}" class="empty">${empty}</td></tr>`;
      $$("tbody tr[data-t]", container).forEach((tr) => tr.addEventListener("click", (e) => {
        const star = e.target.closest(".star");
        if (star) { e.preventDefault(); e.stopPropagation(); toggleWatch(star.dataset.t); return; }
        if (e.target.closest("a,button,input,select")) return;
        if (onRow) onRow(view[+tr.dataset.i]); else if (tr.dataset.t) location.hash = link(tr.dataset.t);
      }));
      if (page) pager($(".pager", container), pg, pages, (p) => { pg = p; draw(); });
    };
    $$("th", container).forEach((th) => th.addEventListener("click", () => {
      if (th.classList.contains("nosort")) return;
      const k = th.dataset.k;
      st = { key: k, asc: st.key === k ? !st.asc : ["name", "country", "type", "sector", "market"].includes(k) };
      draw();
    }));
    draw();
    return { update(newItems) { items = newItems; pg = 1; draw(); } };
  }
  function pager(el, cur, pages, go) {
    const nums = new Set([1, pages, cur - 1, cur, cur + 1].filter((p) => p >= 1 && p <= pages));
    let html = `<button data-p="${cur - 1}" ${cur === 1 ? "disabled" : ""} aria-label="Pagina precedente">‹</button>`, prev = 0;
    [...nums].sort((a, b) => a - b).forEach((p) => { if (p - prev > 1) html += `<button disabled>…</button>`; html += `<button data-p="${p}" aria-current="${p === cur}">${p}</button>`; prev = p; });
    html += `<button data-p="${cur + 1}" ${cur === pages ? "disabled" : ""} aria-label="Pagina successiva">›</button>`;
    el.innerHTML = html;
    $$("button[data-p]", el).forEach((b) => b.addEventListener("click", () => go(+b.dataset.p)));
  }

  // Colonne standard per le tabelle di mercato
  const COLS = {
    star: { k: "star", l: "", nosort: true, html: (a) => starHtml(a.t) },
    name: { k: "name", l: "Strumento", cls: "name", html: nameCell },
    label: { k: "label", l: "Posizionamento", sort: (a) => a.score, html: (a) => labelHtml(a.label) },
    score: { k: "score", l: "Punteggio", cls: "num", html: (a) => scoreHtml(a.score) },
    rank: { k: "rank", l: "#", cls: "num", html: (a) => a.rank ? `${a.rank}<span class="muted small">/${a.of}</span>` : "–" },
    r1d: { k: "r1d", l: "1G", cls: "num", html: (a) => `<span class="${pctCls(a.r1d)}">${pct(a.r1d)}</span>` },
    r1w: { k: "r1w", l: "1S", cls: "num", html: (a) => `<span class="${pctCls(a.r1w)}">${pct(a.r1w)}</span>` },
    r1m: { k: "r1m", l: "1M", cls: "num", html: (a) => `<span class="${pctCls(a.r1m)}">${pct(a.r1m)}</span>` },
    r3m: { k: "r3m", l: "3M", cls: "num", html: (a) => `<span class="${pctCls(a.r3m)}">${pct(a.r3m)}</span>` },
    ytd: { k: "ytd", l: "YTD", cls: "num", html: (a) => `<span class="${pctCls(a.ytd)}">${pct(a.ytd)}</span>` },
    r1y: { k: "r1y", l: "1A", cls: "num", html: (a) => `<span class="${pctCls(a.r1y)}">${pct(a.r1y)}</span>` },
    momAvg: { k: "momAvg", l: "Momentum medio", cls: "num", html: (a) => `<span class="${pctCls(a.momAvg)}">${pct(a.momAvg)}</span>` },
    spark: { k: "spark", l: "3 mesi", nosort: true, html: (a) => sparkSvg(a.spark) },
    delta: { k: "delta4w", l: "Δ 4 sett.", cls: "num", html: (a) => a.delta4w == null ? "–" : `<span class="${a.delta4w >= 0 ? "pos" : "neg"}">${a.delta4w > 0 ? "+" : ""}${a.delta4w}</span>` },
    type: { k: "type", l: "Tipo" },
    country: { k: "country", l: "Paese" },
    market: { k: "market", l: "Mercato" },
    sector: { k: "sector", l: "Settore", cls: "sector", html: (a) => esc(a.sector || a.theme || "–") },
  };
  const cols = (...ks) => ks.map((k) => COLS[k]);

  // ------------------------------------------------------------ grafici (Lightweight Charts)
  const charts = new Set();
  function chart(el, opts = {}) {
    const c = LightweightCharts.createChart(el, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: css("--muted"), fontFamily: css("--font") },
      grid: { vertLines: { color: "#151515" }, horzLines: { color: "#151515" } },
      rightPriceScale: { borderColor: css("--line") },
      timeScale: { borderColor: css("--line") },
      crosshair: { mode: 0 },
      localization: { locale: "it-IT", priceFormatter: opts.pf || ((p) => fmtPrice(p)), dateFormat: "dd MMM yy" },
      ...opts.chart,
    });
    charts.add(c);
    return c;
  }
  function disposeCharts() { charts.forEach((c) => { try { c.remove(); } catch { /* già rimosso */ } }); charts.clear(); }
  function candles(c, h, from = 0) {
    const s = c.addCandlestickSeries({ upColor: css("--pos"), downColor: css("--neg"), borderVisible: false, wickUpColor: css("--pos"), wickDownColor: css("--neg") });
    s.setData(h.d.slice(from).map((d, i) => ({ time: d, open: h.o[i + from], high: h.h[i + from], low: h.l[i + from], close: h.c[i + from] })).filter((x) => x.close != null && x.open != null));
    return s;
  }
  function line(c, times, vals, color, { dashed = false, width = 1.5, title = "" } = {}) {
    const s = c.addLineSeries({ color, lineWidth: width, lineStyle: dashed ? 2 : 0, priceLineVisible: false, lastValueVisible: !!title, crosshairMarkerVisible: !!title, title });
    s.setData(times.map((t, i) => ({ time: t, value: vals[i] })).filter((x) => x.value != null));
    return s;
  }
  function bollinger(c, n = 20, k = 2) {
    const mid = [], up = [], lo = [];
    for (let i = 0; i < c.length; i++) {
      if (i < n - 1) { mid.push(null); up.push(null); lo.push(null); continue; }
      const w = c.slice(i - n + 1, i + 1), m = w.reduce((a, b) => a + b, 0) / n;
      const sd = Math.sqrt(w.reduce((a, b) => a + (b - m) ** 2, 0) / n);
      mid.push(m); up.push(m + k * sd); lo.push(m - k * sd);
    }
    return { mid, up, lo };
  }

  // Treemap "squarified"
  function squarify(items, x, y, w, h) {
    const out = [], total = items.reduce((s, i) => s + i.v, 0);
    if (!total) return out;
    const scale = (w * h) / total;
    let rest = items.map((i) => ({ ...i, _a: i.v * scale })).sort((p, q) => q._a - p._a);
    const sum = (row) => row.reduce((t, r) => t + r._a, 0);
    const worst = (row, side) => { const s = sum(row), mx = Math.max(...row.map((r) => r._a)), mn = Math.min(...row.map((r) => r._a)); return Math.max((side * side * mx) / (s * s), (s * s) / (side * side * mn)); };
    while (rest.length) {
      const side = Math.min(w, h);
      let row = [rest[0]], k = 1;
      while (k < rest.length && worst([...row, rest[k]], side) <= worst(row, side)) { row.push(rest[k]); k++; }
      rest = rest.slice(k);
      const s = sum(row);
      if (w >= h) { const cw = s / h; let cy = y; row.forEach((r) => { const rh = r._a / cw; out.push({ ...r, x, y: cy, w: cw, h: rh }); cy += rh; }); x += cw; w -= cw; }
      else { const ch = s / w; let cx = x; row.forEach((r) => { const rw = r._a / ch; out.push({ ...r, x: cx, y, w: rw, h: ch }); cx += rw; }); y += ch; h -= ch; }
    }
    return out;
  }

  return { $, $$, css, esc, load, boot, state, loadHist, store, isWatched, toggleWatch, watchlist, scoreColor, pct, pctCls, num, fmtPrice, fmtDate, shortT, labelHtml, scoreHtml, starHtml, link, nameCell, sparkSvg, gauge, stackBars, ring, pillarBars, tabs, table, pager, COLS, cols, chart, disposeCharts, candles, line, bollinger, squarify, PILLARS, PILLAR_DESC, pillarName, pages: {} };
})();
