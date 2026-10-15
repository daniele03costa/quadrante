/* Quadrante — pagine: Dashboard, Classifica, Mappa, Confronta, Paesi, Temi, Scheda strumento */
(() => {
  "use strict";
  const { $, $$, css, esc, state, pct, pctCls, fmtPrice, fmtDate, labelHtml, scoreHtml, ring, cols, COLS, link } = Q;
  const REGIME_COLOR = { ESPANSIONE: "--g-espansione", REFLAZIONE: "--g-reflazione", STAGFLAZIONE: "--g-stagflazione", DEFLAZIONE: "--g-deflazione" };
  const MARKETS = () => Object.keys(state.dash.markets).filter((m) => state.dash.markets[m] > 0);

  const head = (title, sub = "", right = "") => `<div class="page-head"><div><h1>${title}</h1>${sub ? `<p class="muted">${sub}</p>` : ""}</div>${right}</div>`;

  // ======================================================================= DASHBOARD
  Q.pages.dashboard = async (root) => {
    const d = state.dash;
    root.innerHTML = `
      ${head("Panoramica macro e mercati", `Aggiornato il ${fmtDate(d.updated, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })}`)}
      <div class="grid-3">
        <article class="card"><header class="card-head"><h2>Regime economico</h2><button class="link-btn" data-toggle="i-reg">Metodo</button></header>
          <div class="regime-wrap"><svg id="quadrant" class="quadrant" viewBox="0 0 220 220" role="img" aria-label="Mappa crescita e inflazione"></svg><ul id="regime-list" class="regime-list"></ul></div>
          <div id="i-reg" class="info" hidden>Per ogni paese: accelerazione di produzione industriale e inflazione (FRED) combinata con segnali di mercato. Ne escono le probabilità dei quattro regimi: Espansione (crescita ↑ inflazione ↓), Reflazione (↑ ↑), Stagflazione (↓ ↑), Deflazione (↓ ↓).<div id="regime-sources" class="sources"></div></div>
        </article>
        <article class="card"><header class="card-head"><h2>Sentiment quantitativo</h2><button class="link-btn" data-toggle="i-sent">Metodo</button></header>
          <div id="sent-gauge" class="gauge"></div><div id="sent-bars" class="stack-bars"></div>
          <div id="i-sent" class="info" hidden>Le barre contano gli strumenti per fascia di punteggio (vendita &lt;60, neutrale 60–79, acquisto ≥80). Dato che il punteggio è una classifica, questa distribuzione resta per costruzione vicina a 60/20/20: per questo la lancetta mostra invece l'<b>ampiezza</b>, cioè la quota di strumenti sopra la media mobile a 200 giorni, che misura davvero il clima del mercato.</div>
        </article>
        <article class="card"><header class="card-head"><h2>Risk on / Risk off</h2><button class="link-btn" data-toggle="i-risk">Metodo</button></header>
          <div id="risk-gauge" class="gauge"></div><div id="risk-bars" class="stack-bars"></div>
          <div id="i-risk" class="info" hidden>Punteggio medio degli asset di rischio (azionario USA, small cap, emergenti, high yield, rame, Bitcoin, alto beta) contro i difensivi (Treasury, oro, utility, beni di prima necessità, bassa volatilità, dollaro). L'allocazione indicativa ne deriva in modo meccanico.</div>
        </article>
      </div>
      <section class="grid-2-wide">
        <article class="card"><header class="card-head"><div><h2>Proposte del giorno</h2><p class="muted small">Gli strumenti con il vantaggio atteso più alto.</p></div>
          <div class="carousel-ctrl"><button class="icon-btn" id="pk-prev" aria-label="Precedente">‹</button><span id="pk-pos" class="mono small"></span><button class="icon-btn" id="pk-next" aria-label="Successiva">›</button></div></header>
          <div class="pick"><div class="pick-main"><div class="pick-title"><span id="pk-badge" class="ticker-badge"></span><div><h3 id="pk-name"></h3><span id="pk-meta" class="muted small"></span></div></div><div id="pk-chart" class="chart"></div></div>
          <aside class="pick-side"><div id="pk-ring"></div><div id="pk-label"></div><div id="pk-pillars" class="full"></div><a class="btn" id="pk-open">Apri scheda</a></aside></div>
        </article>
        <article class="card"><header class="card-head"><div><h2>La tua watchlist</h2><p class="muted small">Salvata in questo browser.</p></div></header><div id="wl"></div></article>
      </section>
      <section class="section"><div class="section-head"><h2 class="h1">Panoramica mercati</h2><p class="muted">Punteggio e performance per area, asset class, fattori e settori.</p></div><div id="panels" class="panels"></div></section>`;

    $$("[data-toggle]", root).forEach((b) => b.addEventListener("click", () => { const el = $("#" + b.dataset.toggle); el.hidden = !el.hidden; }));
    renderRegime(d.macro);
    const s = d.sentiment;
    Q.gauge($("#sent-gauge"), s.breadth, `${s.label} ${s.pct}%`, `ampiezza ${s.breadth}% sopra la media a 200 giorni · ${s.n} strumenti`);
    Q.stackBars($("#sent-bars"), [["Vendita", s.sell, css("--s")], ["Neutrale", s.hold, css("--h")], ["Acquisto", s.buy, css("--b")]]);
    const r = d.risk;
    Q.gauge($("#risk-gauge"), r.gauge, r.label, `rischio ${r.score_on} contro difensivi ${r.score_off}`);
    Q.stackBars($("#risk-bars"), [["Asset di rischio", r.risk, css("--b")], ["Difensivi", r.defensive, css("--g-deflazione")], ["Liquidità", r.cash, css("--muted")]]);

    // proposte
    const picks = d.picks.map((t) => state.byT[t]).filter(Boolean);
    let i = 0;
    const show = async () => {
      const a = picks[i];
      if (!a) return;
      $("#pk-pos").textContent = `${i + 1} / ${picks.length}`;
      $("#pk-badge").textContent = Q.shortT(a.t);
      $("#pk-name").textContent = a.name;
      $("#pk-meta").textContent = `${a.t} · ${a.market} · ${fmtPrice(a.price)} · 1M ${pct(a.r1m)}`;
      $("#pk-ring").innerHTML = ring(a.score, 120);
      $("#pk-label").innerHTML = labelHtml(a.label);
      $("#pk-pillars").innerHTML = Q.pillarBars(a);
      $("#pk-open").href = link(a.t);
      const el = $("#pk-chart");
      el.innerHTML = "";
      try {
        const h = await Q.loadHist(a);
        Q.disposeCharts();
        const c = Q.chart(el), from = Math.max(0, h.d.length - 130), bb = Q.bollinger(h.c), tm = h.d.slice(from);
        Q.line(c, tm, bb.up.slice(from), "rgba(244,183,64,.7)", { dashed: true });
        Q.line(c, tm, bb.lo.slice(from), "rgba(244,183,64,.7)", { dashed: true });
        Q.line(c, tm, bb.mid.slice(from), "rgba(139,151,168,.6)");
        Q.candles(c, h, from);
        c.timeScale().fitContent();
      } catch (e) { el.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
    };
    $("#pk-prev").onclick = () => { i = (i - 1 + picks.length) % picks.length; show(); };
    $("#pk-next").onclick = () => { i = (i + 1) % picks.length; show(); };
    show();

    const drawWl = () => {
      const items = Q.watchlist().map((t) => state.byT[t]).filter(Boolean);
      const el = $("#wl");
      if (!el) return;
      if (!items.length) { el.innerHTML = `<div class="empty"><strong>Nessun titolo in watchlist</strong>Usa la ricerca in alto o la stella ☆ nelle tabelle.</div>`; return; }
      Q.table(el, cols("star", "name", "r1d", "score"), items);
    };
    drawWl();
    document.addEventListener("watchlist", drawWl);

    // pannelli mercati
    const wrap = $("#panels");
    d.panels.forEach((keys, pi) => {
      keys = keys.filter((k) => d.groups[k]?.items.length);
      if (!keys.length) return;
      const card = document.createElement("div");
      card.className = "card";
      const saved = Q.store.get("tab" + pi, keys[0]);
      const active = keys.includes(saved) ? saved : keys[0];
      const body = document.createElement("div");
      const draw = (k) => { Q.store.set("tab" + pi, k); Q.table(body, cols("star", "name", "label", "score", "r1d", "r1w", "r1m", "momAvg", "spark"), d.groups[k].items.map((t) => state.byT[t])); };
      card.append(Q.tabs(keys, keys.map((k) => d.groups[k].label), active, draw), body);
      wrap.appendChild(card);
      draw(active);
    });
  };

  function renderRegime(m) {
    const svg = $("#quadrant"), S = 220, pad = 18, mid = S / 2, scale = (S / 2 - pad) / 3;
    let html = `
      <rect x="${pad}" y="${pad}" width="${mid - pad}" height="${mid - pad}" fill="${css("--g-stagflazione")}" opacity=".08"/>
      <rect x="${mid}" y="${pad}" width="${mid - pad}" height="${mid - pad}" fill="${css("--g-reflazione")}" opacity=".08"/>
      <rect x="${pad}" y="${mid}" width="${mid - pad}" height="${mid - pad}" fill="${css("--g-deflazione")}" opacity=".08"/>
      <rect x="${mid}" y="${mid}" width="${mid - pad}" height="${mid - pad}" fill="${css("--g-espansione")}" opacity=".08"/>
      <line x1="${pad}" y1="${mid}" x2="${S - pad}" y2="${mid}" stroke="${css("--line")}"/><line x1="${mid}" y1="${pad}" x2="${mid}" y2="${S - pad}" stroke="${css("--line")}"/>
      <text class="q-label" x="${pad + 4}" y="${pad + 11}" style="fill:${css("--g-stagflazione")}">STAGFLAZ.</text>
      <text class="q-label" x="${S - pad - 4}" y="${pad + 11}" text-anchor="end" style="fill:${css("--g-reflazione")}">REFLAZ.</text>
      <text class="q-label" x="${pad + 4}" y="${S - pad - 5}" style="fill:${css("--g-deflazione")}">DEFLAZ.</text>
      <text class="q-label" x="${S - pad - 4}" y="${S - pad - 5}" text-anchor="end" style="fill:${css("--g-espansione")}">ESPANS.</text>
      <text class="q-label" x="${S - 4}" y="${mid - 4}" text-anchor="end">crescita →</text><text class="q-label" x="${mid + 4}" y="${pad - 6}">↑ inflazione</text>`;
    m.forEach((c) => {
      const x = mid + Math.max(-3, Math.min(3, c.growth_z)) * scale, y = mid - Math.max(-3, Math.min(3, c.inflation_z)) * scale;
      html += `<g data-id="${c.id}" class="dot-g"><circle class="dot" cx="${x}" cy="${y}" r="4.5" fill="${css(REGIME_COLOR[c.regime])}" stroke="${css("--bg")}" stroke-width="1.5"><title>${esc(c.name)}: ${c.regime} ${c.prob}%</title></circle><text class="dot-label" x="${x + 7}" y="${y + 3}">${esc(c.name)}</text></g>`;
    });
    svg.innerHTML = html;
    $("#regime-list").innerHTML = m.map((c) => `<li data-id="${c.id}" tabindex="0"><span class="country">${c.flag} ${esc(c.name)}</span><span class="regime-tag" style="color:${css(REGIME_COLOR[c.regime])}">${c.regime}<span class="pct">${c.prob}%</span></span></li>`).join("");
    const select = (id) => {
      const c = m.find((x) => x.id === id);
      $$("#regime-list li").forEach((li) => li.classList.toggle("active", li.dataset.id === id));
      $$("#quadrant .dot-g").forEach((g) => { const on = g.dataset.id === id; $(".dot", g).setAttribute("r", on ? 7 : 4.5); $(".dot-label", g).style.display = on ? "" : "none"; if (on) g.parentNode.appendChild(g); });
      $("#regime-sources").innerHTML = `<b>${esc(c.name)}</b> — ${Object.entries(c.probs).map(([k, v]) => `${k.toLowerCase()} ${v}%`).join(" · ")}<br>crescita: ${esc(c.sources.crescita)}<br>inflazione: ${esc(c.sources.inflazione)}`;
    };
    $$("#regime-list li, #quadrant .dot-g").forEach((el) => { el.addEventListener("click", () => select(el.dataset.id)); el.addEventListener("keydown", (e) => e.key === "Enter" && select(el.dataset.id)); });
    select(m[0].id);
  }

  // ======================================================================= CLASSIFICA (screener)
  Q.pages.classifica = async (root) => {
    const f = { market: new Set(), type: new Set(), country: new Set(), label: new Set(), capClass: new Set() };
    let text = "", sector = "", onlyRule = false;
    root.innerHTML = `${head("Classifica", "Tutti gli strumenti monitorati, ordinati per punteggio dentro il proprio mercato.")}
      <div class="card"><div class="filters" id="filters"></div>
      <div class="filter-row"><input id="f-text" type="search" placeholder="Filtra per nome o ticker" aria-label="Filtra per nome o ticker"><select id="f-sector" aria-label="Settore"><option value="">Tutti i settori</option></select>
      <label class="check"><input type="checkbox" id="f-rule"> Solo dentro la regola 80/60</label><button class="link-btn" id="f-reset">Ripristina filtri</button></div>
      <p id="f-count" class="muted small"></p><div id="tbl"></div></div>`;
    const A = state.assets;
    const count = (k) => { const m = {}; A.forEach((a) => a[k] && (m[a[k]] = (m[a[k]] || 0) + 1)); return Object.entries(m).sort((a, b) => b[1] - a[1]).map(([x]) => x); };
    const groups = [["market", "Mercato", count("market")], ["type", "Tipo", ["Azione", "ETF", "Indice", "Cripto", "Forex", "Materia prima"]], ["country", "Paese", count("country").slice(0, 14)],
      ["label", "Posizionamento", ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]], ["capClass", "Capitalizzazione", ["Mega", "Large", "Mid", "Small"]]];
    const drawFilters = () => {
      $("#filters").innerHTML = groups.map(([k, t, vals]) => `<div class="f-group"><h4>${t}</h4><div class="chips">${vals.map((v) => `<button class="chip" data-k="${k}" data-v="${esc(v)}" aria-pressed="${f[k].has(v)}">${esc(v)}</button>`).join("")}</div></div>`).join("");
      $$("#filters .chip").forEach((c) => c.addEventListener("click", () => { const s = f[c.dataset.k]; s.has(c.dataset.v) ? s.delete(c.dataset.v) : s.add(c.dataset.v); c.setAttribute("aria-pressed", s.has(c.dataset.v)); apply(); }));
    };
    $("#f-sector").innerHTML += count("sector").sort().map((s) => `<option>${esc(s)}</option>`).join("");
    const tbl = Q.table($("#tbl"), [COLS.star, COLS.rank, COLS.name, COLS.market, COLS.label, COLS.score, COLS.delta, COLS.r1d, COLS.r1m, COLS.ytd, COLS.sector], [], { page: 20 });
    const apply = () => {
      const q = text.toLowerCase();
      const items = A.filter((a) => Object.entries(f).every(([k, s]) => !s.size || s.has(a[k])) && (!sector || a.sector === sector) && (!onlyRule || a.inRule) && (!q || a.name.toLowerCase().includes(q) || a.t.toLowerCase().includes(q)));
      $("#f-count").textContent = `${items.length} risultati`;
      tbl.update(items);
    };
    $("#f-text").addEventListener("input", (e) => { text = e.target.value.trim(); apply(); });
    $("#f-sector").addEventListener("change", (e) => { sector = e.target.value; apply(); });
    $("#f-rule").addEventListener("change", (e) => { onlyRule = e.target.checked; apply(); });
    $("#f-reset").addEventListener("click", () => { Object.values(f).forEach((s) => s.clear()); text = sector = ""; onlyRule = false; $("#f-text").value = ""; $("#f-sector").value = ""; $("#f-rule").checked = false; drawFilters(); apply(); });
    drawFilters(); apply();
  };

  // ======================================================================= MAPPA DEI PUNTEGGI
  Q.pages.mappa = async (root) => {
    const mk = MARKETS();
    let market = Q.store.get("mapMarket", "Azioni USA");
    if (!mk.includes(market)) market = mk[0];
    root.innerHTML = `${head("Mappa dei punteggi", "Ogni riquadro è uno strumento: colore = punteggio, area = capitalizzazione (o uguale per ETF e indici).")}
      <div class="card"><div id="mtabs"></div><div class="legend-scale"><span>STRONG SELL</span><i style="background:${css("--ss")}"></i><i style="background:${css("--s")}"></i><i style="background:${css("--h")}"></i><i style="background:${css("--b")}"></i><i style="background:${css("--sb")}"></i><span>STRONG BUY</span></div><div id="tmap" class="treemap"></div></div>`;
    const tm = $("#tmap");
    const draw = (m) => {
      market = m; Q.store.set("mapMarket", m);
      const items = state.assets.filter((a) => a.market === m && a.score != null);
      const groupKey = (a) => a.sector || a.theme || a.country || a.type;
      const groups = {};
      items.forEach((a) => (groups[groupKey(a)] ||= []).push(a));
      const W = tm.clientWidth || 1000, H = Math.round(Math.max(420, Math.min(760, W * 0.62)) * (items.length > 400 ? 1.7 : 1));
      tm.style.height = H + "px";
      const size = (a) => (m.startsWith("Azioni") ? Math.sqrt(a.cap || 5e9) : 1);
      const blocks = Q.squarify(Object.entries(groups).map(([k, arr]) => ({ k, arr, v: arr.reduce((s, a) => s + size(a), 0) })), 0, 0, W, H);
      tm.innerHTML = blocks.map((b) => {
        const tiles = Q.squarify(b.arr.map((a) => ({ a, v: size(a) })), 0, 18, b.w, Math.max(1, b.h - 18));
        const avg = Math.round(b.arr.reduce((s, a) => s + a.score, 0) / b.arr.length);
        return `<div class="tm-block" style="left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px"><div class="tm-title" title="${esc(b.k)}">${esc(b.k)} <span>· ${avg}</span></div>${tiles.map((t) =>
          `<a class="tm-tile" href="${link(t.a.t)}" style="left:${t.x}px;top:${t.y}px;width:${t.w}px;height:${t.h}px;background:${Q.scoreColor(t.a.score)}" title="${esc(t.a.name)} · ${t.a.score} · 1G ${pct(t.a.r1d)}">${t.w > 42 && t.h > 24 ? `<b>${esc(Q.shortT(t.a.t))}</b>${t.h > 38 ? `<span>${t.a.score}</span>` : ""}` : ""}</a>`).join("")}</div>`;
      }).join("");
    };
    $("#mtabs").appendChild(Q.tabs(mk, mk, market, draw));
    draw(market);
  };

  // ======================================================================= CONFRONTA
  Q.pages.confronta = async (root, params) => {
    let sel = (params.q.get("t") || Q.store.get("compare", ["^GSPC", "^NDX"]).join(",")).split(",").filter((t) => state.byT[t]).slice(0, 4);
    root.innerHTML = `${head("Confronta", "Fino a quattro strumenti sulle stesse righe: andamento, punteggio e pilastri.")}
      <div class="card"><div class="cmp-pick" id="cmp-pick"></div><div class="grid-2"><div><h3 class="h3">Andamento a 1 anno (base 100)</h3><div id="cmp-chart" class="chart"></div></div><div><h3 class="h3">Punteggio settimanale</h3><div id="cmp-score" class="chart"></div></div></div><div id="cmp-table"></div></div>`;
    const COLORS = [css("--accent"), "#6ea8fe", "#c084fc", "#5fd18f"];
    const draw = async () => {
      Q.store.set("compare", sel);
      history.replaceState(null, "", `#/confronta?t=${sel.map(encodeURIComponent).join(",")}`);
      $("#cmp-pick").innerHTML = sel.map((t, i) => `<span class="cmp-chip" style="border-color:${COLORS[i]}"><i style="background:${COLORS[i]}"></i>${esc(state.byT[t].name)} <button data-t="${esc(t)}" aria-label="Rimuovi">✕</button></span>`).join("") +
        (sel.length < 4 ? `<span class="cmp-add"><input id="cmp-in" placeholder="Aggiungi strumento…" list="cmp-list" aria-label="Aggiungi strumento"><datalist id="cmp-list">${state.assets.map((a) => `<option value="${esc(a.t)}">${esc(a.name)}</option>`).join("")}</datalist></span>` : "");
      $$("#cmp-pick button").forEach((b) => b.addEventListener("click", () => { sel = sel.filter((x) => x !== b.dataset.t); draw(); }));
      const inp = $("#cmp-in");
      if (inp) inp.addEventListener("change", () => { const v = inp.value.trim(); const a = state.byT[v] || state.assets.find((x) => x.name.toLowerCase() === v.toLowerCase()); if (a && !sel.includes(a.t)) { sel.push(a.t); draw(); } });
      Q.disposeCharts();
      const hs = await Promise.all(sel.map((t) => Q.loadHist(state.byT[t]).catch(() => null)));
      const c1 = Q.chart($("#cmp-chart"), { pf: (p) => p.toFixed(0) }), c2 = Q.chart($("#cmp-score"), { pf: (p) => p.toFixed(0) });
      hs.forEach((h, i) => {
        if (!h) return;
        const base = h.c.find((x) => x != null);
        Q.line(c1, h.d, h.c.map((x) => (x == null ? null : (x / base) * 100)), COLORS[i], { width: 2 });
        if (h.score) { const n = h.score.d.length, from = Math.max(0, n - 104); Q.line(c2, h.score.d.slice(from), h.score.v.slice(from), COLORS[i], { width: 2 }); }
      });
      c1.timeScale().fitContent(); c2.timeScale().fitContent();
      const A = sel.map((t) => state.byT[t]);
      const rows = [["Punteggio", (a) => scoreHtml(a.score)], ["Posizionamento", (a) => labelHtml(a.label)], ["Classifica", (a) => a.rank ? `${a.rank}° di ${a.of} · ${esc(a.market)}` : "–"],
        ...Q.PILLARS.map((p) => [Q.pillarName(p), (a) => a.pillars ? `${a.pillars[p] ?? "–"} <span class="muted small">${a.contrib ? pct(a.contrib[p]) : ""}</span>` : "–"]),
        ["Extra-rendimento atteso 3M", (a) => `<span class="${pctCls(a.exp3m)}">${pct(a.exp3m)}</span>`], ["Probabilità di battere il mercato", (a) => a.hit3m ? `${Math.round(a.hit3m * 100)}%` : "–"],
        ["1 mese", (a) => `<span class="${pctCls(a.r1m)}">${pct(a.r1m)}</span>`], ["3 mesi", (a) => `<span class="${pctCls(a.r3m)}">${pct(a.r3m)}</span>`], ["Da inizio anno", (a) => `<span class="${pctCls(a.ytd)}">${pct(a.ytd)}</span>`], ["1 anno", (a) => `<span class="${pctCls(a.r1y)}">${pct(a.r1y)}</span>`],
        ["Regola 80/60", (a) => a.inRule ? `<span class="pos">dentro dal ${fmtDate(a.ruleSince)}</span>` : "fuori"]];
      $("#cmp-table").innerHTML = `<div class="table-wrap"><table class="table cmp"><thead><tr><th></th>${A.map((a, i) => `<th><a href="${link(a.t)}" style="color:${COLORS[i]}">${esc(a.name)}</a></th>`).join("")}</tr></thead><tbody>${rows.map(([l, fn]) => `<tr><td class="muted">${l}</td>${A.map((a) => `<td>${fn(a)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    };
    draw();
  };

  // ======================================================================= PAESI
  Q.pages.paesi = async (root) => {
    const d = state.dash, keys = ["usa", "europa", "asia", "emergenti", "sviluppati"];
    root.innerHTML = `${head("Indici globali", "Andamento e punteggio dei mercati azionari per regione.")}<div class="regime-strip" id="rs"></div><div class="card"><div id="ptabs"></div><div id="pbody"></div></div>`;
    $("#rs").innerHTML = d.macro.map((c) => `<div class="rs-item"><span>${c.flag} ${esc(c.name)}</span><b style="color:${css(REGIME_COLOR[c.regime])}">${c.regime.toLowerCase()} ${c.prob}%</b></div>`).join("");
    const draw = (k) => {
      const ks = k === "all" ? keys : [k];
      $("#pbody").innerHTML = ks.map((g) => `<h3 class="h3 region">${esc(d.groups[g].label)} <span class="muted small">${d.groups[g].items.length} indici</span></h3><div data-g="${g}"></div>`).join("");
      ks.forEach((g) => Q.table($(`[data-g="${g}"]`), cols("star", "name", "country", "score", "label", "r1d", "r1w", "r1m", "momAvg", "ytd", "spark"), d.groups[g].items.map((t) => state.byT[t])));
    };
    $("#ptabs").appendChild(Q.tabs(["all", ...keys], ["Tutte", ...keys.map((k) => d.groups[k].label)], "all", draw));
    draw("all");
  };

  // ======================================================================= TEMI
  Q.pages.temi = async (root) => {
    const themes = state.dash.themes.map((t) => {
      const it = t.items.map((x) => state.byT[x]).filter(Boolean);
      const avg = (k) => { const v = it.map((a) => a[k]).filter((x) => x != null); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; };
      return { ...t, it, score: avg("score") == null ? null : Math.round(avg("score")), r1m: avg("r1m"), r3m: avg("r3m"), ytd: avg("ytd") };
    }).sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
    root.innerHTML = `${head("Temi di investimento", "ETF tematici raggruppati: punteggio medio e andamento.")}<input id="tq" class="input" type="search" placeholder="Cerca tema…" aria-label="Cerca tema"><div class="theme-grid" id="tg"></div>`;
    const draw = (q = "") => {
      $("#tg").innerHTML = themes.filter((t) => !q || t.name.toLowerCase().includes(q)).map((t) => `<article class="card theme">
        <header class="card-head"><h2>${esc(t.name)}</h2>${scoreHtml(t.score)}</header>
        <div class="theme-perf"><div><span>1 mese</span><b class="${pctCls(t.r1m)}">${pct(t.r1m)}</b></div><div><span>3 mesi</span><b class="${pctCls(t.r3m)}">${pct(t.r3m)}</b></div><div><span>Da inizio anno</span><b class="${pctCls(t.ytd)}">${pct(t.ytd)}</b></div></div>
        <ul class="mini-list">${t.it.map((a) => `<li><a href="${link(a.t)}"><span><b>${esc(a.t)}</b> ${esc(a.name)}</span>${labelHtml(a.label)}</a></li>`).join("")}</ul></article>`).join("");
    };
    $("#tq").addEventListener("input", (e) => draw(e.target.value.trim().toLowerCase()));
    draw();
  };

  // ======================================================================= SCHEDA STRUMENTO
  Q.pages.titolo = async (root, params) => {
    const a = state.byT[params.arg];
    if (!a) { root.innerHTML = `<div class="card empty"><strong>Strumento non trovato</strong>${esc(params.arg)}</div>`; return; }
    const h = await Q.loadHist(a).catch(() => null);
    const d = state.dash, calib = d.calib || [];
    const contrib = a.contrib || {};
    const ranked = Q.PILLARS.filter((p) => contrib[p] != null).sort((x, y) => contrib[y] - contrib[x]);
    const strong = ranked[0], weak = ranked[ranked.length - 1];
    const st = h?.stats || {};
    const peers = state.assets.filter((x) => x.market === a.market && x.sector && x.sector === a.sector && x.score != null).sort((x, y) => (x.secRank || 0) - (y.secRank || 0));
    const bucket = calib.find((c) => a.score != null && c.from <= a.score && a.score <= c.to);
    root.innerHTML = `
      <div class="sec-head card">
        <div class="pick-title"><span class="ticker-badge">${esc(Q.shortT(a.t))}</span><div><h1>${esc(a.name)}</h1><span class="muted small">${[a.t, a.type, a.market, a.country, a.sector, a.industry].filter(Boolean).map(esc).join(" · ")}</span></div></div>
        <div class="sec-price"><b class="mono">${fmtPrice(a.price)} <small class="muted">${esc(a.ccy || "")}</small></b>${a.stale ? `<span class="lbl na">FERMO DAL ${esc(fmtDate(a.date).toUpperCase())}</span>` : ""}<span class="${pctCls(a.r1d)}">${pct(a.r1d)}</span><span class="muted small">${fmtDate(a.date)}</span></div>
        <div class="sec-actions">${Q.starHtml(a.t)}<a class="btn ghost" href="#/confronta?t=${encodeURIComponent(a.t)}">Confronta</a><button class="btn ghost" id="add-pf">Aggiungi al portafoglio</button></div>
      </div>
      <div class="sec-grid">
        <article class="card sec-score"><div class="ring-wrap">${ring(a.score, 140)}</div>${labelHtml(a.label)}
          <p class="muted small center">${a.rank ? `${a.rank}° di ${a.of} nel mercato ${esc(a.market)}${a.secRank ? ` · ${a.secRank}° di ${a.secOf} in ${esc(a.sector)}` : ""}` : ""}</p>
          ${strong ? `<div class="sw"><h4>Punto di forza</h4><p>${Q.pillarName(strong)} a ${a.pillars[strong]} su 100 · contributo ${pct(contrib[strong])}</p></div>` : ""}
          ${weak && weak !== strong ? `<div class="sw warn"><h4>Punto di attenzione</h4><p>${Q.pillarName(weak)} a ${a.pillars[weak]} su 100 · contributo ${pct(contrib[weak])}</p></div>` : ""}
          ${st.n ? `<div class="sw"><h4>Regola 80/60</h4><p>${a.inRule ? `Dentro dal ${fmtDate(a.ruleSince)} (${pct(a.ruleRet)})` : "Fuori"} · ${st.wins}/${st.n} operazioni in guadagno${st.payoff ? ` · guadagni/perdite ${String(st.payoff).replace(".", ",")}` : ""}</p></div>` : ""}
        </article>
        <article class="card"><header class="card-head"><div><h2>Pilastri del punteggio</h2><p class="muted small">Valore 0–100 nel proprio mercato e contributo all'extra-rendimento atteso a 3 mesi.</p></div></header>
          ${a.pillars ? `<ul class="pillar-list">${Q.PILLARS.map((p) => `<li><div><b>${Q.pillarName(p)}</b><span class="muted small">${Q.PILLAR_DESC[p]}</span></div><div class="pv"><span class="mono">${a.pillars[p] ?? "–"}</span><span class="bar"><i style="width:${a.pillars[p] ?? 0}%;background:${Q.scoreColor(a.pillars[p])}"></i></span><span class="muted small">primo ${a.pillars[p] == null ? "–" : Math.max(1, 100 - a.pillars[p])}%</span><span class="mono ${pctCls(contrib[p])}">${pct(contrib[p])}</span></div></li>`).join("")}</ul>
          <div class="edge-box"><div><span>Vantaggio atteso (somma dei contributi)</span><b class="${pctCls(a.edge)}">${pct(a.edge)}</b></div><div><span>Chi sta nella fascia ${bucket ? `${bucket.from}–${bucket.to}` : ""} ha reso, in mediana, a 3 mesi</span><b class="${pctCls(a.exp3m)}">${pct(a.exp3m)}</b></div><div><span>e ha battuto il mercato</span><b>${a.hit3m ? Math.round(a.hit3m * 100) + "% delle volte" : "–"}</b>${a.hitLo != null ? `<span class="ci">intervallo 95%: ${Math.round(a.hitLo * 100)}–${Math.round(a.hitHi * 100)}% · ${a.nInd} osservazioni indipendenti</span>` : ""}</div></div>
          <p class="muted small">Il punteggio non è la media dei pilastri: è la posizione in classifica del vantaggio atteso dentro il mercato ${esc(a.market)}. Statistiche fuori campione dal ${d.firstYear}, ${bucket ? Q.num(bucket.n) + " casi" : ""}.</p>` : `<p class="muted">Storico insufficiente per calcolare i pilastri.</p>`}
        </article>
      </div>
      <article class="card"><header class="card-head"><div><h2>Prezzo</h2><p class="muted small">Candele giornaliere, media a 50 (giallo) e 200 giorni (blu).</p></div></header><div id="c-price" class="chart tall"></div>
        <div class="returns">${[["1 giorno", "r1d"], ["1 settimana", "r1w"], ["1 mese", "r1m"], ["3 mesi", "r3m"], ["6 mesi", "r6m"], ["Da inizio anno", "ytd"], ["1 anno", "r1y"]].map(([l, k]) => `<div><span>${l}</span><b class="${pctCls(a[k])}">${pct(a[k])}</b></div>`).join("")}<div><span>Volatilità annua</span><b>${h ? pct(h.vol, 1).replace("+", "") : "–"}</b></div></div></article>
      ${h?.score ? `<div class="grid-2"><article class="card"><header class="card-head"><div><h2>Storico del punteggio</h2><p class="muted small">Soglie operative: entrata a 80, uscita sotto 60.</p></div></header><div id="c-score" class="chart"></div></article>
        <article class="card"><header class="card-head"><div><h2>I cinque pilastri nel tempo</h2><p class="muted small">Ultimi due anni.</p></div></header><div id="c-pil" class="chart"></div><div class="legend small" id="pil-leg"></div></article></div>` : ""}
      ${st.n ? `<article class="card"><header class="card-head"><div><h2>Evidenza storica della regola 80/60</h2><p class="muted small">Backtest fuori campione dal ${d.firstYear}, confronto con ${esc(h.bench)} negli stessi periodi. Pochi casi su un singolo titolo raccontano, ma non dimostrano.</p></div></header>
        <div class="stat-grid"><div><span>Operazioni concluse</span><b>${st.n}</b></div><div><span>In guadagno</span><b>${st.wins} su ${st.n}</b></div><div><span>Esito medio</span><b class="${pctCls(st.avg)}">${pct(st.avg)}</b></div><div><span>Benchmark medio</span><b class="${pctCls(st.avg_bench)}">${pct(st.avg_bench)}</b></div><div><span>Vincita media / perdita media</span><b>${pct(st.avg_win)} / ${pct(st.avg_loss)}</b></div><div><span>Durata mediana</span><b>${st.median_weeks} sett.</b></div><div><span>Migliore / peggiore</span><b>${pct(st.best)} / ${pct(st.worst)}</b></div><div><span>Battuto il benchmark</span><b>${st.beat} su ${st.n}</b></div></div>
        <details><summary>Elenco operazioni</summary><div id="trades"></div></details></article>` : ""}
      <div class="grid-2">
        <article class="card"><header class="card-head"><div><h2>Stagionalità mensile</h2><p class="muted small">${h?.seasonality ? `Rendimento medio per mese su ${h.seasonality.years} anni.` : "Storico insufficiente."}</p></div></header><div id="seas"></div>
          ${h?.window ? `<div class="sw"><h4>Finestra stagionale imminente</h4><p>Dal ${h.window.start} al ${h.window.end} (${h.window.days} giorni): positiva ${Math.round(h.window.win * 100)}% delle volte su ${h.window.years} anni, media ${pct(h.window.avg)}.</p></div>` : ""}</article>
        <article class="card"><header class="card-head"><div><h2>Concorrenti nel settore</h2><p class="muted small">${a.sector ? esc(a.sector) + " · " + esc(a.market) : "Nessun settore assegnato"}</p></div></header><div id="peers"></div></article>
      </div>`;

    $(".sec-actions .star", root).addEventListener("click", () => Q.toggleWatch(a.t));
    $("#add-pf").addEventListener("click", () => { location.hash = `#/portafogli?add=${encodeURIComponent(a.t)}`; });
    if (peers.length) Q.table($("#peers"), [COLS.name, COLS.score, COLS.r1m, COLS.ytd], peers.slice(0, 12)); else $("#peers").innerHTML = `<p class="muted">–</p>`;
    if (!h) return;
    Q.disposeCharts();
    const cp = Q.chart($("#c-price"));
    Q.candles(cp, h);
    Q.line(cp, h.d, h.sma50, css("--accent"));
    Q.line(cp, h.d, h.sma200, "#6ea8fe");
    cp.timeScale().fitContent();
    if (h.score) {
      const cs = Q.chart($("#c-score"), { pf: (p) => p.toFixed(0) });
      const n = h.score.d.length, from = Math.max(0, n - 260);
      const s = Q.line(cs, h.score.d.slice(from), h.score.v.slice(from), css("--accent"), { width: 2, title: "Punteggio" });
      s.createPriceLine({ price: 80, color: css("--b"), lineStyle: 2, lineWidth: 1, axisLabelVisible: true, title: "entrata" });
      s.createPriceLine({ price: 60, color: css("--s"), lineStyle: 2, lineWidth: 1, axisLabelVisible: true, title: "uscita" });
      cs.timeScale().fitContent();
      const PC = { macro: "#6ea8fe", trend: css("--accent"), momentum: "#5fd18f", season: "#c084fc", risk: "#f08a4b" };
      const cpl = Q.chart($("#c-pil"), { pf: (p) => p.toFixed(0) });
      Q.PILLARS.forEach((p) => Q.line(cpl, h.pillarsHist.d, h.pillarsHist[p], PC[p], { width: 1.5 }));
      cpl.timeScale().fitContent();
      $("#pil-leg").innerHTML = Q.PILLARS.map((p) => `<span class="lg" style="background:${PC[p]}"></span>${Q.pillarName(p)}`).join(" ");
    }
    if (h.trades?.length) {
      const tr = h.trades.slice().reverse();
      Q.table($("#trades"), [{ k: "in", l: "Entrata", html: (t) => fmtDate(t.in) }, { k: "out", l: "Uscita", html: (t) => t.open ? `<span class="muted">in corso</span>` : fmtDate(t.out) }, { k: "weeks", l: "Settimane", cls: "num" },
        { k: "ret", l: "Esito", cls: "num", html: (t) => `<span class="${pctCls(t.ret)}">${pct(t.ret)}</span>` }, { k: "bench", l: "Benchmark", cls: "num", html: (t) => `<span class="${pctCls(t.bench)}">${pct(t.bench)}</span>` }], tr, { sort: { key: "in", asc: false } });
    }
    if (h.seasonality) {
      const ms = h.seasonality.months, max = Math.max(...ms.map((m) => Math.abs(m.avg || 0)), 0.001), cur = new Date().getMonth() + 1;
      const MN = ["G", "F", "M", "A", "M", "G", "L", "A", "S", "O", "N", "D"];
      $("#seas").innerHTML = `<div class="seas">${ms.map((m) => `<div class="sm${m.m === cur ? " cur" : ""}" title="${MN[m.m - 1]}: media ${pct(m.avg)}, positivo ${Math.round((m.win || 0) * 100)}% su ${m.n} anni"><div class="sm-bar"><i class="${(m.avg || 0) >= 0 ? "up" : "dn"}" style="height:${(Math.abs(m.avg || 0) / max) * 50}%"></i></div><span>${MN[m.m - 1]}</span><small>${Math.round((m.win || 0) * 100)}%</small></div>`).join("")}</div>`;
    }
  };
})();
