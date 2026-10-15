/* Quadrante — pagine: Radar, Rotation, Portafogli, News e Macro, Metodo */
(() => {
  "use strict";
  const { $, $$, css, esc, state, pct, pctCls, fmtPrice, fmtDate, labelHtml, scoreHtml, COLS, link, num } = Q;
  const head = (title, sub = "", right = "") => `<div class="page-head"><div><h1>${title}</h1>${sub ? `<p class="muted">${sub}</p>` : ""}</div>${right}</div>`;
  const withAsset = (rows) => rows.map((r) => ({ ...state.byT[r.t], ...r })).filter((r) => r.name);

  // ======================================================================= RADAR
  Q.pages.radar = async (root, params) => {
    const R = await Q.load("radar");
    const mode = params.arg || Q.store.get("radarMode", "stagionalita");
    let market = "";
    root.innerHTML = `${head("Radar", "Finestre stagionali imminenti e segnali della regola 80/60.")}
      <div class="card"><div id="rt"></div><div class="filter-row"><select id="r-mkt" aria-label="Mercato"><option value="">Tutti i mercati</option>${Object.keys(state.dash.markets).map((m) => `<option>${esc(m)}</option>`).join("")}</select><p id="r-desc" class="muted small"></p></div><div id="rbody"></div></div>`;
    const seasonCols = [COLS.star, COLS.name, COLS.market,
      { k: "start", l: "Inizio", sort: (r) => r.startDate }, { k: "end", l: "Fine", nosort: true }, { k: "days", l: "Giorni", cls: "num" }, COLS.score,
      { k: "win", l: "Positivo", cls: "num", html: (r) => `${Math.round(r.win * 100)}%` }, { k: "avg", l: "Rend. medio", cls: "num", html: (r) => `<span class="${pctCls(r.avg)}">${pct(r.avg)}</span>` },
      { k: "worst", l: "Peggiore", cls: "num", html: (r) => `<span class="${pctCls(r.worst)}">${pct(r.worst)}</span>` }, { k: "years", l: "Anni", cls: "num" }];
    const momCols = [COLS.star, COLS.name, COLS.market, { k: "event", l: "Segnale", html: (r) => `<span class="lbl ${r.event === "ENTRATA" ? "b" : "s"}">${r.event}</span>` },
      { k: "date", l: "Settimana", html: (r) => fmtDate(r.date) }, COLS.score, COLS.delta,
      { k: "rs", l: "Storico regola", sort: (r) => r.ruleStats?.n ? r.ruleStats.wins / r.ruleStats.n : null, html: (r) => r.ruleStats?.n ? `${r.ruleStats.wins}/${r.ruleStats.n} in guadagno · media ${pct(r.ruleStats.avg)}` : "–" }, COLS.r1m];
    const DESC = {
      stagionalita: "Strumenti con una finestra stagionale che inizia nei prossimi 14 giorni, positiva almeno 7 anni su 10. Ordinati per punteggio.",
      momentum: "Strumenti entrati (punteggio salito a 80+) o usciti (sceso sotto 60) dalla regola nelle ultime 4 settimane.",
      combo: "Finestra stagionale imminente e regola 80/60 attiva nello stesso momento.",
    };
    const draw = (m) => {
      Q.store.set("radarMode", m);
      $("#r-desc").textContent = DESC[m];
      const f = (rows) => withAsset(rows).filter((r) => !market || r.market === market);
      if (m === "momentum") Q.table($("#rbody"), momCols, f(R.momentum), { sort: { key: "date", asc: false }, page: 20 });
      else Q.table($("#rbody"), seasonCols, f(m === "combo" ? R.combo : R.seasonal), { sort: { key: "score", asc: false }, page: 20 });
      cur = m;
    };
    let cur = mode;
    $("#rt").appendChild(Q.tabs(["stagionalita", "momentum", "combo"], ["Stagionalità", "Regola 80/60", "Regola + stagionalità"], mode, draw));
    $("#r-mkt").addEventListener("change", (e) => { market = e.target.value; draw(cur); });
    draw(mode);
  };

  // ======================================================================= ROTATION
  Q.pages.rotation = async (root, params) => {
    const RO = await Q.load("rotation");
    const keys = Object.keys(RO).filter((k) => RO[k].items.length);
    let key = keys.includes(params.arg) ? params.arg : keys.includes("settori") ? "settori" : keys[0];
    root.innerHTML = `${head("Rotation", "Forza relativa e momentum rispetto al benchmark, stile Relative Rotation Graph. La rotazione tipica gira in senso orario.")}
      <div class="card"><div id="rot-tabs"></div><div class="rot-wrap"><div><svg id="rrg" class="rrg" viewBox="0 0 640 480" role="img" aria-label="Grafico di rotazione relativa"></svg><p class="muted small" id="rot-bench"></p></div><aside><ul class="rot-list" id="rot-list"></ul><div class="quad-count" id="qc"></div></aside></div></div>
      <div class="grid-2"><article class="card"><h2>Sopra il benchmark (3 mesi)</h2><div id="rot-up"></div></article><article class="card"><h2>Sotto il benchmark (3 mesi)</h2><div id="rot-dn"></div></article></div>`;
    const QC = { LEADING: css("--b"), WEAKENING: css("--h"), LAGGING: css("--ss"), IMPROVING: "#6ea8fe" };
    const QIT = { LEADING: "in testa", WEAKENING: "in indebolimento", LAGGING: "in ritardo", IMPROVING: "in miglioramento" };
    let selected = null;
    const draw = (k) => {
      key = k;
      history.replaceState(null, "", `#/rotation/${k}`);
      const set = RO[k], items = set.items.map((p) => ({ ...p, a: state.byT[p.t] })).filter((p) => p.a);
      $("#rot-bench").textContent = set.bench ? `Benchmark: ${state.byT[set.bench]?.name || set.bench}` : "Benchmark: andamento assoluto";
      const xs = items.flatMap((p) => p.path.map((q) => q[0])), ys = items.flatMap((p) => p.path.map((q) => q[1]));
      const span = (v) => Math.max(1.5, ...v.map((x) => Math.abs(x - 100))) * 1.12;
      const sx = span(xs), sy = span(ys), W = 640, H = 480, P = 40;
      const X = (x) => P + ((x - (100 - sx)) / (2 * sx)) * (W - 2 * P), Y = (y) => H - P - ((y - (100 - sy)) / (2 * sy)) * (H - 2 * P);
      let s = `<rect x="${X(100)}" y="${P}" width="${W - P - X(100)}" height="${Y(100) - P}" fill="${QC.LEADING}" opacity=".07"/><rect x="${X(100)}" y="${Y(100)}" width="${W - P - X(100)}" height="${H - P - Y(100)}" fill="${QC.WEAKENING}" opacity=".07"/>
        <rect x="${P}" y="${Y(100)}" width="${X(100) - P}" height="${H - P - Y(100)}" fill="${QC.LAGGING}" opacity=".07"/><rect x="${P}" y="${P}" width="${X(100) - P}" height="${Y(100) - P}" fill="${QC.IMPROVING}" opacity=".07"/>
        <line x1="${X(100)}" y1="${P}" x2="${X(100)}" y2="${H - P}" stroke="${css("--line")}"/><line x1="${P}" y1="${Y(100)}" x2="${W - P}" y2="${Y(100)}" stroke="${css("--line")}"/>
        <text x="${W - P - 4}" y="${P + 14}" text-anchor="end" class="rq" fill="${QC.LEADING}">LEADING</text><text x="${W - P - 4}" y="${H - P - 6}" text-anchor="end" class="rq" fill="${QC.WEAKENING}">WEAKENING</text>
        <text x="${P + 4}" y="${H - P - 6}" class="rq" fill="${QC.LAGGING}">LAGGING</text><text x="${P + 4}" y="${P + 14}" class="rq" fill="${QC.IMPROVING}">IMPROVING</text>
        <text x="${W / 2}" y="${H - 8}" text-anchor="middle" class="rax">Forza relativa →</text><text x="12" y="${H / 2}" text-anchor="middle" class="rax" transform="rotate(-90 12 ${H / 2})">Momentum relativo →</text>`;
      items.forEach((p) => {
        const on = selected === p.t, col = QC[p.quad], pts = p.path.map((q) => `${X(q[0])},${Y(q[1])}`).join(" ");
        const [lx, ly] = p.path[p.path.length - 1];
        s += `<g class="rrg-item${selected && !on ? " dim" : ""}" data-t="${esc(p.t)}"><polyline points="${pts}" fill="none" stroke="${col}" stroke-width="${on ? 2.5 : 1.4}" opacity=".8"/>${p.path.slice(0, -1).map((q) => `<circle cx="${X(q[0])}" cy="${Y(q[1])}" r="2" fill="${col}" opacity=".6"/>`).join("")}
          <circle cx="${X(lx)}" cy="${Y(ly)}" r="${on ? 7 : 5}" fill="${col}" stroke="${css("--bg")}" stroke-width="1.5"><title>${esc(p.a.name)} · ${QIT[p.quad]}</title></circle><text x="${X(lx) + 8}" y="${Y(ly) + 4}" class="rlab">${esc(Q.shortT(p.t))}</text></g>`;
      });
      $("#rrg").innerHTML = s;
      $$("#rrg .rrg-item").forEach((g) => g.addEventListener("click", () => { selected = selected === g.dataset.t ? null : g.dataset.t; draw(key); }));
      $("#rot-list").innerHTML = items.sort((a, b) => (b.score ?? 0) - (a.score ?? 0)).map((p) => `<li class="${selected === p.t ? "active" : ""}" data-t="${esc(p.t)}"><i style="background:${QC[p.quad]}"></i><div><b>${esc(p.a.name)}</b><span class="muted small">${esc(p.t)} · ${QIT[p.quad]} da ${p.weeks} sett.</span></div>${scoreHtml(p.score)}</li>`).join("");
      $$("#rot-list li").forEach((li) => { li.addEventListener("click", () => { selected = selected === li.dataset.t ? null : li.dataset.t; draw(key); }); li.addEventListener("dblclick", () => (location.hash = link(li.dataset.t))); });
      const cnt = {}; items.forEach((p) => (cnt[p.quad] = (cnt[p.quad] || 0) + 1));
      $("#qc").innerHTML = ["LEADING", "WEAKENING", "LAGGING", "IMPROVING"].map((q) => `<div style="border-color:${QC[q]}"><span style="color:${QC[q]}">${q}</span><b>${cnt[q] || 0}</b></div>`).join("");
      const rel = items.filter((p) => p.rel3m != null).sort((a, b) => b.rel3m - a.rel3m);
      const relCols = [{ k: "name", l: "Strumento", sort: (p) => p.a.name, html: (p) => `<a href="${link(p.t)}"><b>${esc(p.a.name)}</b></a>` }, { k: "rel3m", l: "Vs benchmark", cls: "num", html: (p) => `<span class="${pctCls(p.rel3m)}">${(p.rel3m * 100).toFixed(1).replace(".", ",")} pt</span>` }, { k: "quad", l: "Quadrante", html: (p) => `<span style="color:${QC[p.quad]}">${QIT[p.quad]}</span>` }, { k: "score", l: "Punteggio", cls: "num", html: (p) => scoreHtml(p.score) }];
      Q.table($("#rot-up"), relCols, rel.filter((p) => p.rel3m >= 0), { sort: { key: "rel3m", asc: false } });
      Q.table($("#rot-dn"), relCols, rel.filter((p) => p.rel3m < 0), { sort: { key: "rel3m", asc: true } });
    };
    $("#rot-tabs").appendChild(Q.tabs(keys, keys.map((k) => RO[k].title), key, (k) => { selected = null; draw(k); }));
    draw(key);
  };

  // ======================================================================= PORTAFOGLI
  Q.pages.portafogli = async (root, params) => {
    const P = await Q.load("portfolios");
    const mk = Object.keys(P);
    let pfs = Q.store.get("portfolios", [{ name: "Il mio portafoglio", pos: [] }]);
    let cur = Math.min(Q.store.get("pfCur", 0), pfs.length - 1);
    const save = () => { Q.store.set("portfolios", pfs); Q.store.set("pfCur", cur); };
    root.innerHTML = `${head("Portafogli", "I tuoi portafogli (salvati in questo browser) e i portafogli modello del punteggio.")}
      <article class="card"><header class="card-head"><div><h2>I miei portafogli</h2><p class="muted small">Aggiungi posizioni: valore, guadagno e punteggio si aggiornano con i dati del giorno.</p></div><div class="pf-ctrl"><select id="pf-sel" aria-label="Portafoglio"></select><button class="btn ghost" id="pf-new">Nuovo</button><button class="btn ghost" id="pf-ren">Rinomina</button><button class="btn ghost" id="pf-del">Elimina</button></div></header>
        <form class="pf-form" id="pf-form"><input id="pf-t" list="pf-list" placeholder="Ticker (es. ENI.MI)" required aria-label="Ticker"><datalist id="pf-list">${state.assets.map((a) => `<option value="${esc(a.t)}">${esc(a.name)}</option>`).join("")}</datalist>
          <input id="pf-q" type="number" step="any" min="0" placeholder="Quantità" required aria-label="Quantità"><input id="pf-p" type="number" step="any" min="0" placeholder="Prezzo medio di carico" required aria-label="Prezzo medio"><button class="btn" type="submit">Aggiungi</button></form>
        <div class="stat-grid" id="pf-sum"></div><div id="pf-tbl"></div><p class="muted small">Inserisci il prezzo di carico nella valuta dello strumento (i titoli di Londra sono in pence, GBp). Valori e totali sono convertiti in euro al cambio di oggi; il G/P percentuale è nella valuta dello strumento.</p>
        <div class="pf-io"><button class="btn ghost" id="io-exp">Esporta backup</button><label class="btn ghost" for="io-imp">Importa backup</label><input type="file" id="io-imp" accept="application/json,.json" hidden><span class="muted small">Il backup contiene portafogli e watchlist: salvalo e reimportalo su un altro computer o sul telefono.</span></div></article>
      <article class="card"><header class="card-head"><div><h2>Portafogli modello</h2><p class="muted small">Ogni settimana, in pesi uguali: gli strumenti dentro la regola 80/60, i migliori 10% per punteggio e il mercato intero. Backtest fuori campione dal ${state.dash.firstYear}, senza costi.</p></div></header>
        <div id="mp-tabs"></div><div id="mp-chart" class="chart tall"></div><div class="legend small"><span class="lg" style="background:${css("--accent")}"></span>Regola 80/60 <span class="lg" style="background:#5fd18f"></span>Top 10% <span class="lg" style="background:#8b97a8"></span>Mercato</div><div id="mp-stats"></div><h3 class="h3">Posizioni attuali della regola</h3><div id="mp-hold"></div></article>`;
    const add = params.q.get("add");
    if (add) $("#pf-t").value = add, $("#pf-p").value = state.byT[add]?.price ?? "";
    const drawPf = () => {
      $("#pf-sel").innerHTML = pfs.map((p, i) => `<option value="${i}" ${i === cur ? "selected" : ""}>${esc(p.name)}</option>`).join("");
      // valori convertiti in euro al cambio di oggi (carico e prezzo sono nella valuta dello strumento)
      const FX = state.dash.fx || { EUR: 1 };
      const rate = (c) => FX[c || "EUR"] || null;
      const rows = pfs[cur].pos.map((p, i) => {
        const a = state.byT[p.t] || {}, r = rate(a.ccy) || 1;
        const loc = (a.price ?? p.p) * p.q, locCost = p.p * p.q;
        return { ...a, t: p.t, i, q: p.q, p: p.p, val: loc / r, cost: locCost / r, plp: locCost ? loc / locCost - 1 : null, noFx: !rate(a.ccy) };
      });
      const tot = rows.reduce((s, r) => s + r.val, 0), cost = rows.reduce((s, r) => s + r.cost, 0);
      rows.forEach((r) => (r.w = tot ? r.val / tot : 0));
      const wScore = rows.filter((r) => r.score != null).reduce((s, r) => s + r.score * r.w, 0) / (rows.filter((r) => r.score != null).reduce((s, r) => s + r.w, 0) || 1);
      const day = rows.reduce((s, r) => s + (r.r1d != null ? r.val - r.val / (1 + r.r1d) : 0), 0);
      $("#pf-sum").innerHTML = rows.length ? `<div><span>Valore (EUR)</span><b>€ ${num(tot, 2)}</b></div><div><span>Guadagno / perdita</span><b class="${pctCls(tot - cost)}">${num(tot - cost, 2)} (${pct(cost ? tot / cost - 1 : 0)})</b></div><div><span>Oggi</span><b class="${pctCls(day)}">${num(day, 2)}</b></div><div><span>Punteggio medio ponderato</span><b>${Math.round(wScore) || "–"}</b></div><div><span>Posizioni sotto 60</span><b class="${rows.some((r) => r.score != null && r.score < 60) ? "neg" : ""}">${rows.filter((r) => r.score != null && r.score < 60).length}</b></div>` : "";
      Q.table($("#pf-tbl"), [COLS.name, { k: "q", l: "Quantità", cls: "num", html: (r) => num(r.q, 4) }, { k: "p", l: "Carico", cls: "num", html: (r) => fmtPrice(r.p) }, { k: "price", l: "Prezzo", cls: "num", html: (r) => fmtPrice(r.price) }, { k: "ccy", l: "Valuta", html: (r) => esc(r.ccy || "–") + (r.noFx ? ' <span class="neg" title="Cambio non disponibile: valore non convertito">!</span>' : "") },
        { k: "val", l: "Valore €", cls: "num", html: (r) => num(r.val, 2) }, { k: "w", l: "Peso", cls: "num", html: (r) => `${(r.w * 100).toFixed(1).replace(".", ",")}%` }, { k: "plp", l: "G/P", cls: "num", html: (r) => `<span class="${pctCls(r.plp)}">${pct(r.plp)}</span>` }, COLS.r1d, COLS.score, COLS.label,
        { k: "x", l: "", nosort: true, html: (r) => `<button class="link-btn del" data-i="${r.i}" aria-label="Rimuovi">Rimuovi</button>` }], rows, { sort: { key: "val", asc: false }, empty: "Nessuna posizione: aggiungine una con il modulo qui sopra." });
      $$("#pf-tbl .del").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); pfs[cur].pos.splice(+b.dataset.i, 1); save(); drawPf(); }));
    };
    $("#pf-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const t = $("#pf-t").value.trim(), a = state.byT[t] || state.assets.find((x) => x.t.toLowerCase() === t.toLowerCase());
      if (!a) { $("#pf-t").setCustomValidity("Ticker non presente nell'universo monitorato"); $("#pf-t").reportValidity(); return; }
      pfs[cur].pos.push({ t: a.t, q: +$("#pf-q").value, p: +$("#pf-p").value }); save(); e.target.reset(); drawPf();
    });
    $("#pf-t").addEventListener("input", (e) => { e.target.setCustomValidity(""); const a = state.byT[e.target.value.trim()]; if (a && !$("#pf-p").value) $("#pf-p").value = a.price; });
    $("#pf-sel").addEventListener("change", (e) => { cur = +e.target.value; save(); drawPf(); });
    $("#io-exp").addEventListener("click", () => {
      const data = { app: "quadrante", version: 1, date: new Date().toISOString(), portfolios: pfs, watchlist: Q.watchlist(), compare: Q.store.get("compare", []) };
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: "application/json" }));
      const a = Object.assign(document.createElement("a"), { href: url, download: `quadrante-backup-${new Date().toISOString().slice(0, 10)}.json` });
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    $("#io-imp").addEventListener("change", async (e) => {
      const f = e.target.files[0];
      if (!f) return;
      try {
        const d = JSON.parse(await f.text());
        if (d.app !== "quadrante" || !Array.isArray(d.portfolios)) throw new Error("file non riconosciuto");
        const ok = d.portfolios.every((p) => typeof p.name === "string" && Array.isArray(p.pos) && p.pos.every((x) => typeof x.t === "string" && isFinite(x.q) && isFinite(x.p)));
        if (!ok) throw new Error("contenuto non valido");
        if (!confirm(`Sostituire i portafogli e la watchlist di questo browser con quelli del backup del ${fmtDate(d.date)}?`)) return;
        pfs = d.portfolios.length ? d.portfolios : pfs; cur = 0; save();
        Q.store.set("watchlist", (d.watchlist || []).filter((t) => typeof t === "string"));
        if (Array.isArray(d.compare)) Q.store.set("compare", d.compare);
        location.reload();
      } catch (err) { alert("Importazione non riuscita: " + err.message); }
      e.target.value = "";
    });
    $("#pf-new").addEventListener("click", () => { const n = prompt("Nome del nuovo portafoglio", `Portafoglio ${pfs.length + 1}`); if (n) { pfs.push({ name: n, pos: [] }); cur = pfs.length - 1; save(); drawPf(); } });
    $("#pf-ren").addEventListener("click", () => { const n = prompt("Nuovo nome", pfs[cur].name); if (n) { pfs[cur].name = n; save(); drawPf(); } });
    $("#pf-del").addEventListener("click", () => { if (pfs.length > 1 && confirm(`Eliminare "${pfs[cur].name}"?`)) { pfs.splice(cur, 1); cur = 0; save(); drawPf(); } });
    drawPf();

    const drawMp = (g) => {
      const m = P[g];
      Q.disposeCharts();
      const c = Q.chart($("#mp-chart"), { pf: (p) => p.toFixed(2) + "x", chart: { rightPriceScale: { mode: 1, borderColor: css("--line") } } });
      Q.line(c, m.dates, m.curves.mercato, "#8b97a8", { width: 1.5 });
      Q.line(c, m.dates, m.curves.top, "#5fd18f", { width: 1.5 });
      Q.line(c, m.dates, m.curves.regola, css("--accent"), { width: 2 });
      c.timeScale().fitContent();
      const L = { regola: "Regola 80/60", top: `Top 10% (${m.n_top})`, mercato: "Mercato" };
      $("#mp-stats").innerHTML = `<div class="table-wrap"><table class="table"><thead><tr><th>Strategia</th><th class="num">Rend. annuo</th><th class="num">Volatilità</th><th class="num">Max drawdown</th><th class="num">Rend./vol.</th><th class="num">Totale</th></tr></thead><tbody>${Object.entries(m.stats).map(([k, s]) => `<tr><td>${L[k]}</td><td class="num ${pctCls(s.cagr)}">${pct(s.cagr)}</td><td class="num">${pct(s.vol).replace("+", "")}</td><td class="num neg">${pct(s.maxdd)}</td><td class="num">${s.sharpe ?? "–"}</td><td class="num ${pctCls(s.total)}">${pct(s.total, 0)}</td></tr>`).join("")}</tbody></table></div>`;
      Q.table($("#mp-hold"), [COLS.star, COLS.name, COLS.score, { k: "ruleSince", l: "Dentro dal", html: (a) => fmtDate(a.ruleSince) }, { k: "ruleRet", l: "Da allora", cls: "num", html: (a) => `<span class="${pctCls(a.ruleRet)}">${pct(a.ruleRet)}</span>` }, COLS.r1m], m.holdings.map((t) => state.byT[t]).filter(Boolean), { empty: "Nessuno strumento dentro la regola in questo mercato." });
    };
    const g0 = mk.includes(Q.store.get("mpMarket")) ? Q.store.get("mpMarket") : mk[0];
    $("#mp-tabs").appendChild(Q.tabs(mk, mk.map((k) => `${k} (${P[k].held_now})`), g0, (g) => { Q.store.set("mpMarket", g); drawMp(g); }));
    if (g0) drawMp(g0);
  };

  // ======================================================================= NEWS E MACRO
  Q.pages.news = async (root, params) => {
    const N = await Q.load("news");
    const sub = ["earnings", "calendario", "cot"].includes(params.arg) ? params.arg : "earnings";
    const T = { earnings: ["Earnings", "Trimestrali in arrivo (e della settimana scorsa) per i titoli monitorati, con il loro punteggio."], calendario: ["Calendario macro", "Dati economici di questa settimana e della prossima. Orari in ora italiana."], cot: ["Commitment of Traders", "Posizione netta dei grandi speculatori (non-commercial) sui futures, report settimanale CFTC. Indice COT = dove si trova la posizione netta rispetto agli ultimi 3 anni (0 minimo, 100 massimo)."] };
    root.innerHTML = `${head(T[sub][0], T[sub][1])}<div class="card"><div id="nbody"></div></div>`;
    const body = $("#nbody");
    if (sub === "earnings") {
      const rows = withAsset(N.earnings);
      Q.table(body, [{ k: "date", l: "Data", html: (r) => fmtDate(r.date, { weekday: "short", day: "numeric", month: "short" }) }, COLS.star, COLS.name, COLS.market, COLS.sector, COLS.score, COLS.label, COLS.r1m], rows, { sort: { key: "date", asc: true }, page: 25, empty: "Nessuna trimestrale nel periodo." });
    } else if (sub === "calendario") {
      const IMP = { High: "alto", Medium: "medio", Low: "basso", Holiday: "festività" };
      const rows = (N.calendar || []).map((e, i) => ({ ...e, t: "", i }));
      Q.table(body, [{ k: "date", l: "Quando", html: (e) => new Date(e.date).toLocaleString("it-IT", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) }, { k: "country", l: "Valuta" },
        { k: "impact", l: "Impatto", html: (e) => `<span class="imp ${esc(e.impact || "")}">${IMP[e.impact] || esc(e.impact || "")}</span>` }, { k: "title", l: "Evento", html: (e) => esc(e.title) }, { k: "forecast", l: "Previsto", cls: "num" }, { k: "previous", l: "Precedente", cls: "num" }, { k: "actual", l: "Effettivo", cls: "num", html: (e) => esc(e.actual || "") }],
        rows, { sort: { key: "date", asc: true }, empty: "Calendario non disponibile." });
    } else {
      const rows = (N.cot || []).map((c) => ({ ...c, t: "" }));
      body.innerHTML = `<div id="cot-tbl"></div><div class="cot-detail"><h3 class="h3" id="cot-title"></h3><div id="cot-chart" class="chart"></div></div>`;
      const show = (c) => {
        $("#cot-title").textContent = `${c.name} · posizione netta degli speculatori, ultimi 3 anni`;
        Q.disposeCharts();
        const ch = Q.chart($("#cot-chart"), { pf: (p) => num(p, 0) });
        const s = ch.addHistogramSeries({ priceLineVisible: false });
        s.setData(c.hist.map(([d, v]) => ({ time: d, value: v, color: v >= 0 ? css("--pos") : css("--neg") })));
        ch.timeScale().fitContent();
      };
      Q.table($("#cot-tbl"), [{ k: "cat", l: "Categoria" }, { k: "name", l: "Contratto", html: (c) => `<b>${esc(c.name)}</b>` }, { k: "net", l: "Netto speculatori", cls: "num", html: (c) => `<span class="${pctCls(c.net)}">${num(c.net)}</span>` },
        { k: "chg", l: "Variazione sett.", cls: "num", html: (c) => `<span class="${pctCls(c.chg)}">${c.chg > 0 ? "+" : ""}${num(c.chg)}</span>` }, { k: "netPctOi", l: "% open interest", cls: "num", html: (c) => pct(c.netPctOi, 1) },
        { k: "index", l: "Indice COT 3 anni", cls: "num", html: (c) => `<span class="score">${c.index}<span class="score-bar"><i style="width:${c.index}%;background:${c.index >= 80 ? css("--b") : c.index <= 20 ? css("--s") : css("--h")}"></i></span></span>` },
        { k: "spark", l: "Andamento", nosort: true, html: (c) => Q.sparkSvg(c.hist.slice(-52).map((x) => x[1])) }, { k: "date", l: "Report", html: (c) => fmtDate(c.date) }],
        rows, { sort: { key: "cat", asc: true }, onRow: show, empty: "Dati COT non disponibili." });
      if (rows.length) show(rows[0]);
    }
  };

  // ======================================================================= METODO
  Q.pages.metodo = async (root) => {
    const d = state.dash, cal = d.calib || [];
    const max = Math.max(...cal.map((c) => Math.abs(c.median)), 0.001);
    root.innerHTML = `${head("Come funziona il punteggio", "Un modello quantitativo a cinque pilastri, ricostruito da zero e stimato sui dati storici.")}
      <div class="grid-2"><article class="card prose">
        <h2>In breve</h2>
        <ol><li><b>Cinque pilastri</b> misurano ogni strumento ogni settimana. Ognuno diventa un percentile 0–100 dentro il suo mercato (azioni USA, azioni Europa, ETF, indici, cripto, forex, materie prime).</li>
        <li>Per ogni fascia di ogni pilastro il modello stima, dai dati passati, quanto rende in più del proprio mercato nei <b>3 mesi successivi</b>: è il <b>contributo</b>. La stima usa una regressione ridge sui decili ed è rifatta ogni anno usando solo il passato.</li>
        <li>La somma dei contributi è il <b>vantaggio atteso</b>. Il <b>punteggio 1–99</b> è la posizione in classifica di quel vantaggio nel mercato: 93 vuol dire meglio del 93% degli strumenti confrontabili. Per questo non è la media dei pilastri.</li>
        <li><b>Regola operativa:</b> si entra quando il punteggio sale a 80 o più e si esce quando scende sotto 60. Il cuscinetto tra le due soglie evita di entrare e uscire di continuo.</li></ol>
        <h2>I pilastri</h2>
        <ul class="pillar-def">${Q.PILLARS.map((p) => `<li><b>${Q.pillarName(p)}</b> — ${Q.PILLAR_DESC[p]}.</li>`).join("")}</ul>
        <p class="muted small">Tendenza: distanza dalla media a 200 giorni e rendimento 12 mesi meno l'ultimo mese, entrambi divisi per la volatilità. Momentum: rendimenti a 1 e 3 mesi corretti per la volatilità più l'accelerazione (3 mesi contro 6). Stagionalità: rendimento medio dei 3 mesi successivi negli stessi giorni degli ultimi 15 anni. Rischio: volatilità a 3 mesi rispetto alla mediana del mercato. Macro: extra-rendimento medio dello strumento nelle fasi passate con lo stesso regime USA di oggi (${esc(d.usRegime || "–")}), calcolato da produzione industriale e inflazione (FRED).</p>
        <h2>Fasce di posizionamento</h2>
        <p>${["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"].map((l) => labelHtml(l)).join(" ")}</p><p class="muted small">90–99 · 80–89 · 60–79 · 30–59 · 1–29</p>
        <h2>Quanto sono affidabili le probabilità</h2>
        <ul><li><b>Nessun dato futuro.</b> Pilastri, pesi e soglie di taglio degli outlier usano solo informazioni disponibili alla data; i pesi sono ristimati ogni anno sul passato. Su prezzi casuali senza segnale (test di controllo) la scala resta piatta intorno al 50% in ogni fascia.</li>
        <li><b>Intervalli onesti.</b> Le finestre di 3 mesi misurate ogni settimana si sovrappongono: l'intervallo di confidenza usa solo un'osservazione ogni 13 settimane.</li>
        <li><b>Probabilità per mercato.</b> La percentuale mostrata nella scheda viene dalla scala del proprio mercato (azioni USA, ETF…), se ha abbastanza dati.</li>
        <li><b>Esecuzione realistica.</b> Nei backtest si entra ed esce alla chiusura della settimana successiva al segnale.</li>
        <li><b>Distorsione da sopravvivenza.</b> L'universo usa i componenti attuali degli indici: i titoli usciti o falliti in passato mancano, quindi i risultati storici sono probabilmente un po' migliori della realtà.</li>
        <li><b>Futures.</b> Materie prime con contratti continui (=F) hanno salti di rollover che sporcano i rendimenti.</li></ul>
        <h2>Limiti</h2>
        <p>È un modello statistico su prezzi passati: indica quanto uno strumento è stato favorito in situazioni simili, non cosa succederà. I backtest non includono costi, tasse e slittamenti. Gli strumenti con meno di 5 anni di storico hanno pilastri incompleti. Non è consulenza finanziaria.</p>
      </article>
      <article class="card"><h2>Il modello funziona? Verifica fuori campione</h2><p class="muted small">Extra-rendimento mediano a 3 mesi rispetto al proprio mercato per fascia di punteggio, su tutti gli strumenti e le settimane dal ${d.firstYear}. Una scala che sale da sinistra a destra indica che il punteggio ha avuto potere predittivo.</p>
        <div class="calib">${cal.map((c) => `<div class="cb" title="Punteggio ${c.from}–${c.to}: mediana ${pct(c.median)}, batte il mercato ${Math.round(c.hit * 100)}%, ${num(c.n)} casi"><div class="cb-bar"><i class="${c.median >= 0 ? "up" : "dn"}" style="height:${(Math.abs(c.median) / max) * 50}%"></i></div><span>${c.from}</span></div>`).join("")}</div>
        ${d.tuning ? `<h2 style="margin-top:18px">Taratura sui dati reali</h2><p class="muted small">Eseguita il ${fmtDate(d.tuning.date)}${d.tuning.demo ? " su dati simulati" : ""}. Variante scelta: <b>${esc(d.tuning.best)}</b>. IC = correlazione di rango settimanale tra punteggio ed extra-rendimento a 3 mesi; la colonna «verifica» usa gli ultimi 3 anni, esclusi dalla scelta.</p>
          <div class="table-wrap"><table class="table"><thead><tr><th>Variante</th><th class="num">IC</th><th class="num">IC verifica</th><th class="num">Spread 80+ vs &lt;30</th><th class="num">Scarto prob.</th><th class="num">Turnover</th></tr></thead><tbody>${d.tuning.tried.map((t) => `<tr${t.why === d.tuning.best ? ' style="color:var(--accent)"' : ""}><td>${esc(t.why)}</td><td class="num">${t.ic ?? "–"}</td><td class="num">${t.ic_check ?? "–"}</td><td class="num">${pct(t.spread)}</td><td class="num">${t.calib_err == null ? "–" : (t.calib_err * 100).toFixed(1).replace(".", ",") + " pt"}</td><td class="num">${t.turnover}</td></tr>`).join("")}</tbody></table></div>` : `<p class="muted small" style="margin-top:14px">Taratura non ancora eseguita: avvia l'Action «Taratura del modello».</p>`}
        <div class="table-wrap"><table class="table"><thead><tr><th>Fascia</th><th class="num">Mediana 3M</th><th class="num">Batte il mercato</th><th class="num">Intervallo 95%</th><th class="num">Casi</th><th class="num">Indipendenti</th></tr></thead><tbody>${cal.slice().reverse().map((c) => `<tr><td>${c.from}–${c.to}</td><td class="num ${pctCls(c.median)}">${pct(c.median)}</td><td class="num">${Math.round(c.hit * 100)}%</td><td class="num">${c.hit_lo != null ? Math.round(c.hit_lo * 100) + "–" + Math.round(c.hit_hi * 100) + "%" : "–"}</td><td class="num">${num(c.n)}</td><td class="num">${num(c.n_ind)}</td></tr>`).join("")}</tbody></table></div>
      </article></div>`;
  };
})();
