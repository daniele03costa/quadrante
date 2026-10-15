/* Quadrante — router, ricerca, navigazione */
(() => {
  "use strict";
  const { $, $$, esc, state } = Q;
  const view = $("#view");

  function parse() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, qs = ""] = raw.split("?");
    const [page = "", ...rest] = path.split("/");
    return { page: page || "dashboard", arg: rest.length ? decodeURIComponent(rest.join("/")) : "", q: new URLSearchParams(qs) };
  }

  let seq = 0;
  async function route() {
    const p = parse(), my = ++seq;
    const fn = Q.pages[p.page] || Q.pages.dashboard;
    $$(".nav a[data-route], .nav .dd-btn").forEach((el) => el.classList.toggle("active", (el.dataset.route || "").split(" ").includes(p.page === "dashboard" ? "" : p.page)));
    $("#nav").classList.remove("open");
    Q.disposeCharts();
    try {
      // il contenitore è già nel documento: grafici e mappa conoscono subito la loro larghezza
      const root = document.createElement("div");
      root.className = "page";
      root.innerHTML = `<div class="loading">Caricamento…</div>`;
      view.replaceChildren(root);
      await fn(root, p);
    } catch (e) {
      console.error(e);
      if (my === seq) view.innerHTML = `<div class="card empty"><strong>Qualcosa non ha funzionato</strong>${esc(e.message)}</div>`;
    }
    if (!p.q.has("keep")) window.scrollTo({ top: 0 });
  }

  function initSearch() {
    const input = $("#search"), list = $("#search-results");
    let idx = -1, res = [];
    const close = () => { list.classList.remove("open"); idx = -1; };
    const draw = () => {
      list.innerHTML = res.map((a, i) => `<li role="option" data-t="${esc(a.t)}" class="${i === idx ? "active" : ""}"><span><b>${esc(a.name)}</b> <span class="muted small">${esc(a.t)} · ${esc(a.market)}</span></span>${Q.labelHtml(a.label)}</li>`).join("");
      list.classList.toggle("open", res.length > 0);
      $$("li", list).forEach((li) => li.addEventListener("mousedown", (e) => { e.preventDefault(); pick(li.dataset.t); }));
    };
    const pick = (t) => { close(); input.value = ""; input.blur(); location.hash = Q.link(t); };
    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      res = q ? state.assets.filter((a) => a.t.toLowerCase().includes(q) || a.name.toLowerCase().includes(q))
        .sort((a, b) => (b.t.toLowerCase().startsWith(q) - a.t.toLowerCase().startsWith(q)) || (b.score ?? 0) - (a.score ?? 0)).slice(0, 8) : [];
      idx = -1; draw();
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") { idx = Math.min(res.length - 1, idx + 1); draw(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { idx = Math.max(0, idx - 1); draw(); e.preventDefault(); }
      else if (e.key === "Enter" && res.length) pick(res[Math.max(0, idx)].t);
      else if (e.key === "Escape") close();
    });
    input.addEventListener("blur", close);
  }

  function initTape() {
    const T = ["^GSPC", "^NDX", "^DJI", "^RUT", "^STOXX50E", "FTSEMIB.MI", "^GDAXI", "^FTSE", "^N225", "^HSI", "EURUSD=X", "USDJPY=X", "DX-Y.NYB", "GC=F", "CL=F", "HG=F", "BTC-USD", "ETH-USD", "TLT"];
    const items = T.map((t) => state.byT[t]).filter(Boolean);
    if (!items.length) return;
    const html = items.map((a) => `<a href="${Q.link(a.t)}"><b>${esc(Q.shortT(a.t))}</b>${Q.fmtPrice(a.price)} <span class="${Q.pctCls(a.r1d)}">${Q.pct(a.r1d)}</span></a>`).join("");
    $("#tape").innerHTML = `<div class="tape-inner">${html}${html}</div>`;
  }
  function initClock() {
    const tick = () => {
      const now = new Date();
      const f = (tz) => now.toLocaleTimeString("it-IT", { timeZone: tz, hour: "2-digit", minute: "2-digit" });
      $("#clock").innerHTML = `MIL <b>${f("Europe/Rome")}</b> · NY <b>${f("America/New_York")}</b> · TOK <b>${f("Asia/Tokyo")}</b>`;
    };
    tick(); setInterval(tick, 30000);
  }
  function initKeys() {
    // tasti 1–9 come scorciatoie di sezione, "/" per la ricerca (non mentre si scrive in un campo)
    const go = { 1: "#/", 2: "#/portafogli", 3: "#/radar", 4: "#/classifica", 5: "#/rotation", 6: "#/paesi", 7: "#/temi", 8: "#/news/earnings", 9: "#/metodo" };
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("input,textarea,select") || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "/") { e.preventDefault(); $("#search").focus(); }
      else if (go[e.key]) location.hash = go[e.key];
    });
  }

  async function init() {
    $("#menu-btn").addEventListener("click", () => { const n = $("#nav"); n.classList.toggle("open"); $("#menu-btn").setAttribute("aria-expanded", n.classList.contains("open")); });
    $$(".dd-btn").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); const dd = b.parentNode; const was = dd.classList.contains("open"); $$(".dd").forEach((x) => x.classList.remove("open")); dd.classList.toggle("open", !was); }));
    document.addEventListener("click", () => $$(".dd").forEach((x) => x.classList.remove("open")));
    $$(".dd-menu a").forEach((a) => a.addEventListener("click", () => $$(".dd").forEach((x) => x.classList.remove("open"))));
    try {
      await Q.boot();
    } catch (e) {
      view.innerHTML = `<div class="card empty"><strong>Dati non trovati</strong>Avvia la GitHub Action “Aggiorna dati e pubblica” oppure, in locale, <code>python scripts/update_data.py --demo</code>.</div>`;
      return;
    }
    $("#demo-banner").hidden = !state.dash.demo;
    $("#updated").textContent = `Dati aggiornati il ${Q.fmtDate(state.dash.updated, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })}.`;
    initSearch();
    initTape();
    initClock();
    initKeys();
    window.addEventListener("hashchange", route);
    route();
  }
  init();
})();
