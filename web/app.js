"use strict";
// Bazaar dashboard: vanilla JS, hand-built SVG, no CDN, works offline.

const S = { meta: null, summary: null, rep: null, sweep: null, tab: "market", auctions: null, auctionFilter: { system: "bazaar", category: "" }, selAuction: null, busy: false };
const $ = (q, el = document) => el.querySelector(q);
const $$ = (q, el = document) => [...el.querySelectorAll(q)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => Math.round(n).toLocaleString("en-US");
const money = (n) => "$" + fmt(n);
const pct = (x) => (x == null ? "–" : `${(x * 100).toFixed(1)}%`);
const PAL = ["#3987e5", "#2fb344", "#fab219", "#a78bfa", "#ec6aa3", "#35c4c4", "#e0733b", "#9ad04b", "#f05d5d", "#6a9ef0"];
const agentColor = (name, names) => PAL[(names || (S.meta ? S.meta.roster.map((r) => r.name) : [])).indexOf(name) % PAL.length] || "#8f8e86";

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body));
  return body;
}
const post = (p, d) => api(p, { method: "POST", body: d === undefined ? undefined : JSON.stringify(d) });
function toast(msg, bad = false) {
  const t = $("#toast"); t.textContent = msg; t.className = "toast" + (bad ? " bad" : "");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add("hidden"), 4500);
}

// ------------------------------------------------------------------ boot
async function loadAll() {
  [S.meta, S.summary, S.rep] = await Promise.all([api("/api/meta"), api("/api/summary"), api("/api/reputation")]);
  $("#wschip").textContent = `seed ${S.meta.seed} · ${S.meta.n_tasks} tasks · ${S.meta.roster.length} agents`;
}
async function boot() {
  try { await loadAll(); } catch (e) { toast(e.message, true); }
  $$("#tabs button").forEach((b) => b.addEventListener("click", () => { S.tab = b.dataset.tab; renderTab(); }));
  renderTab();
}
function renderTab() {
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === S.tab));
  ({ market: viewMarket, agents: viewAgents, auctions: viewAuctions, compare: viewCompare, how: viewHow })[S.tab]();
}
const view = () => $("#view");
const tile = (v, l) => `<div class="tile"><div class="v">${v}</div><div class="l">${l}</div></div>`;

// ------------------------------------------------------------------ MARKET
function viewMarket() {
  const b = S.summary.bazaar, c = S.summary.crew;
  const names = S.meta.roster.map((r) => r.name);
  const winners = Object.entries(b.win_count).sort((x, y) => y[1] - x[1]);
  const maxWin = Math.max(1, ...winners.map((w) => w[1]));
  view().innerHTML = `
    <p class="lede">Every task is a Contract-Net auction: agents bid price, ETA and confidence; the auctioneer scores each bid against that agent's track record <em>in that category</em> and awards the highest score.
      Run it again with a new seed or different weights and the market replays the same mechanism on a fresh task stream.</p>
    <div class="panel"><div class="controls" style="grid-template-columns:repeat(4,minmax(120px,1fr)) auto">
      <label>Seed<input type="number" id="seed" value="${S.meta.seed}"></label>
      <label>Tasks<select id="ntasks">${S.meta.presets.map((p) => `<option ${p === S.meta.n_tasks ? "selected" : ""}>${p}</option>`).join("")}</select></label>
      <label>Price weight<input type="number" id="wp" step="0.05" min="0" max="1" value="${S.meta.weights[0]}"></label>
      <label>Confidence weight<input type="number" id="wc" step="0.05" min="0" max="1" value="${S.meta.weights[2]}"></label>
      <button class="primary" id="go">Run</button></div>
      <p class="small muted" style="margin-top:6px">ETA weight is whatever is left over after price and confidence. Weights are re-normalised to sum to 1.</p></div>
    <div class="tiles">${tile(pct(b.success_rate), "bazaar success rate")}${tile(money(b.total_cost), "bazaar total spend")}${tile(b.n_awarded, "tasks awarded")}
      ${tile(Object.keys(b.win_count).length, "agents that won at least one auction")}</div>
    <div class="split"><div class="panel"><h2>Who won the work</h2>${winners.map(([n, w]) => `<div class="repgrid"><span>${esc(n)}</span><div class="repbar"><i style="width:${(w / maxWin) * 100}%;background:${agentColor(n, names)}"></i></div><span class="num">${w}</span></div>`).join("")}</div>
    <div class="panel"><h2>Success rate over time (rolling, window ${b.rolling.length ? b.rolling[b.rolling.length - 1].window : 20})</h2>${rollingChart(b.rolling, c.rolling)}
      <p class="small muted"><i style="color:#7fe07f">■</i> bazaar &nbsp; <i style="color:#ff9b9b">■</i> fixed crew (same tasks)</p></div></div>
    <div class="panel"><h2>Success by category</h2><table><tr><th>category</th><th class="num">tasks</th><th class="num">bazaar</th><th class="num">crew</th></tr>
      ${S.meta.categories.map((cat) => { const bc = b.category_success[cat], cc = c.category_success[cat]; return `<tr><td>${esc(cat)}</td><td class="num">${bc ? bc.total : 0}</td>
        <td class="num">${bc ? pct(bc.rate) : "–"}</td><td class="num">${cc ? pct(cc.rate) : "–"}</td></tr>`; }).join("")}</table></div>`;
  $("#go").addEventListener("click", async () => {
    const wp = +$("#wp").value, wc = +$("#wc").value, we = Math.max(0, 1 - wp - wc);
    try { toast("Running…"); await post("/api/run", { seed: +$("#seed").value, n_tasks: +$("#ntasks").value, weights: [wp, we, wc] }); await loadAll(); renderTab(); }
    catch (e) { toast(e.message, true); }
  });
}
function rollingChart(a, b2) {
  const W = 620, H = 170, L = 34, R = 10, T = 8, B = 20;
  const n = Math.max(a.length, b2.length, 1);
  const x = (i) => L + (i / Math.max(n - 1, 1)) * (W - L - R), y = (v) => T + (1 - v) * (H - T - B);
  const grid = [0, 0.5, 1].map((v) => `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="#2e2e2b"/><text x="${L - 4}" y="${y(v) + 3}" fill="#8f8e86" font-size="9" text-anchor="end">${Math.round(v * 100)}%</text>`).join("");
  const line = (arr, color) => `<polyline fill="none" stroke="${color}" stroke-width="2" points="${arr.map((p, i) => `${x(i)},${y(p.success_rate)}`).join(" ")}"/>`;
  return `<svg viewBox="0 0 ${W} ${H}" style="max-width:100%">${grid}${line(a, "#7fe07f")}${line(b2, "#ff9b9b")}</svg>`;
}

// ------------------------------------------------------------------ AGENTS
function viewAgents() {
  const names = S.meta.roster.map((r) => r.name);
  view().innerHTML = `<p class="lede">Each agent's real skill per category is private — only the auctioneer's reputation tracker (a Beta distribution per agent per category) learns it, one outcome at a time. Hover a skill chip to compare it with what the agent tends to claim.</p>
    <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(360px,1fr))">${S.meta.roster.map((a) => agentCard(a, names)).join("")}</div>`;
}
function agentCard(a, names) {
  const rep = S.rep[a.name];
  const flags = [];
  if (a.honesty > 1.15) flags.push('<span class="flagd">overclaims confidence</span>');
  else if (a.honesty < 0.95) flags.push('<span class="flagc">underclaims (cautious)</span>');
  if (a.bids_outside_skill) flags.push('<span class="flagd">bids outside its skill</span>');
  const skills = Object.entries(a.skill).sort((x, y) => y[1] - x[1]);
  return `<div class="agentcard" style="border-left-color:${agentColor(a.name, names)}"><div class="nm"><span>${esc(a.name)}${flags.join("")}</span><span class="small muted">$${a.price_rate}/pt · ${a.speed}d/pt</span></div>
    <div class="skillbar">${skills.map(([c, v]) => `<span class="skillchip" title="real skill in ${esc(c)}: ${v.toFixed(2)}">${esc(c)} ${v.toFixed(2)}</span>`).join("")}</div>
    <h3 style="margin-top:8px">Reputation by category</h3>
    ${Object.entries(rep).filter(([, r]) => r.observations > 0).sort((x, y) => y[1].observations - x[1].observations).map(([cat, r]) =>
      `<div class="repgrid"><span>${esc(cat)}</span><div class="repbar"><i style="width:${r.mean * 100}%;background:${r.mean > 0.6 ? "#2fb344" : r.mean > 0.4 ? "#fab219" : "#d03b3b"}"></i></div><span class="num small">${pct(r.mean)}</span></div>
       <div class="small muted" style="margin:-2px 0 4px 70px">${r.observations} task${r.observations === 1 ? "" : "s"}</div>`).join("") || '<p class="small muted">No track record yet in this run.</p>'}</div>`;
}

// ------------------------------------------------------------------ AUCTION LOG
async function viewAuctions() {
  view().innerHTML = `<p class="lede">Every auction, in order. Click one to see every bid and why the winner won.</p>
    <div class="controls" style="grid-template-columns:160px 200px auto"><label>System<select id="sys"><option value="bazaar" ${S.auctionFilter.system === "bazaar" ? "selected" : ""}>Bazaar (market)</option><option value="crew" ${S.auctionFilter.system === "crew" ? "selected" : ""}>Fixed crew</option></select></label>
      <label>Category<select id="cat"><option value="">all</option>${S.meta.categories.map((c) => `<option ${c === S.auctionFilter.category ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label><div></div></div>
    <div class="split"><div class="panel scroll" style="max-height:560px;padding:0" id="alist"></div><div class="panel detail" id="adetail"><span class="muted">Click an auction.</span></div></div>`;
  $("#sys").addEventListener("change", (e) => { S.auctionFilter.system = e.target.value; loadAuctions(); });
  $("#cat").addEventListener("change", (e) => { S.auctionFilter.category = e.target.value; loadAuctions(); });
  await loadAuctions();
}
async function loadAuctions() {
  const q = new URLSearchParams({ system: S.auctionFilter.system, limit: "300" });
  if (S.auctionFilter.category) q.set("category", S.auctionFilter.category);
  S.auctions = await api("/api/auctions?" + q.toString());
  renderAuctionList();
}
function renderAuctionList() {
  const el = $("#alist");
  if (!el) return;
  const items = S.auctions.items;
  el.innerHTML = `<div class="alog-row" style="font-weight:600;color:var(--text-muted)"><span>#</span><span>category</span><span>cplx</span><span>winner</span><span>note</span></div>
    ${items.map((r, i) => `<div class="alog-row${S.selAuction === i ? " sel" : ""}" data-i="${i}"><span class="mono">${r.task.id}</span><span>${esc(r.task.category)}</span><span class="num">${r.task.complexity.toFixed(1)}</span>
      <span>${r.winner ? esc(r.winner) : "–"}</span><span class="small ${r.outcome ? (r.outcome.success ? "ok" : "no") : "muted"}">${r.outcome ? (r.outcome.success ? "delivered" : "failed") : r.note}</span></div>`).join("") || '<div class="muted" style="padding:14px">no auctions</div>'}`;
  $$(".alog-row[data-i]", el).forEach((row) => row.addEventListener("click", () => { S.selAuction = +row.dataset.i; renderAuctionList(); renderAuctionDetail(); }));
  if (S.selAuction != null && S.selAuction < items.length) renderAuctionDetail(); else $("#adetail").innerHTML = '<span class="muted">Click an auction.</span>';
}
function renderAuctionDetail() {
  const r = S.auctions.items[S.selAuction], el = $("#adetail");
  if (!r || !el) return;
  const names = S.meta.roster.map((x) => x.name);
  const rows = r.bids.length ? r.bids.map((b) => `<tr class="${b.agent === r.winner ? "sel" : ""}"><td>${esc(b.agent)}${b.agent === r.winner ? ' <span class="winmark">★</span>' : ""}</td>
      <td class="num">${money(b.price)}</td><td class="num">${b.eta.toFixed(1)}d</td><td class="num">${pct(b.confidence)}</td><td class="num">${r.scores[b.agent] != null ? r.scores[b.agent].toFixed(3) : "–"}</td></tr>`).join("")
    : `<tr><td colspan="5" class="muted">${esc(r.note)}: no bidding in the fixed crew — ${esc(r.winner)} always does ${esc(r.task.category)} work.</td></tr>`;
  el.innerHTML = `<h2>Task #${r.task.id} · ${esc(r.task.category)}</h2><p class="small muted">complexity ${r.task.complexity.toFixed(1)} of 10 · tick ${r.task.tick}</p>
    <table class="bidtable"><tr><th>agent</th><th class="num">price</th><th class="num">eta</th><th class="num">confidence</th><th class="num">score</th></tr>${rows}</table>
    ${r.outcome ? `<h3 style="margin-top:12px">Outcome</h3><p>${r.outcome.success ? '<span class="ok">Delivered.</span>' : '<span class="no">Failed.</span>'} Real success chance for ${esc(r.outcome.agent)} on this task was ${pct(r.outcome.true_probability)} — never shown to the auctioneer, only used to roll the dice.</p>` : ""}`;
}

// ------------------------------------------------------------------ COMPARE
function viewCompare() {
  view().innerHTML = `<p class="lede">The same task stream, run twice: once through the Bazaar market, once through a fixed-role crew — one agent hired per category at an "interview" where nobody's reputation is known yet, kept forever after regardless of how it performs. This is the gap a market with memory buys you.</p>
    <div class="panel" id="onerun"></div>
    <div class="panel"><h2>Across many seeds</h2><div style="display:flex;gap:8px;align-items:center;margin-bottom:8px"><label class="small">seeds <input type="number" id="nseeds" value="40" min="5" max="200" style="width:70px"></label>
      <button class="primary" id="swgo">Run sweep</button></div><div id="sw" class="muted small">click "Run sweep", or wait for the background one to finish</div></div>`;
  renderOneRun();
  $("#swgo").addEventListener("click", async () => {
    try { toast("Running the sweep… this can take a few seconds"); const r = await post("/api/sweep?" + new URLSearchParams({ n_seeds: $("#nseeds").value })); S.sweep = r; renderSweep(); }
    catch (e) { toast(e.message, true); }
  });
  pollSweep();
}
function renderOneRun() {
  const b = S.summary.bazaar, c = S.summary.crew;
  const hires = S.summary.hires.map((h) => `<span class="skillchip">${esc(h.category)} → ${esc(h.agent)}</span>`).join(" ");
  $("#onerun").innerHTML = `<h2>This run (seed ${S.summary.seed}, ${S.summary.n_tasks} tasks)</h2>
    <div class="vsline"><div class="vscol bazaar"><div class="big">${pct(b.success_rate)}</div><div class="lbl">bazaar success</div></div>
      <div class="vscol crew"><div class="big">${pct(c.success_rate)}</div><div class="lbl">fixed-crew success</div></div>
      <div class="vscol"><div class="big">${money(b.total_cost)}</div><div class="lbl">bazaar spend</div></div>
      <div class="vscol"><div class="big">${money(c.total_cost)}</div><div class="lbl">crew spend</div></div></div>
    <p class="small muted">The crew's one-time hires: ${hires}</p>`;
}
async function pollSweep() {
  const r = await api("/api/sweep");
  if (r.result) { S.sweep = r.result; renderSweep(); return; }
  const el = $("#sw");
  if (el) el.textContent = "running in the background…";
  if (S.tab === "compare") setTimeout(pollSweep, 1500);
}
function renderSweep() {
  const el = $("#sw"), s = S.sweep;
  if (!el || !s) return;
  const fh = s.flex_hired_for_data, d = s.data_rate_when_flex_hired, f = s.flex_win_share_in_data, bc = s.bazaar_beats_crew;
  el.innerHTML = `<div class="tiles">${tile(`${bc.seeds}/${bc.of}`, "seeds where bazaar beats the fixed crew")}${tile(`+${pct(bc.mean_diff)}`, "mean success-rate gap")}
      ${tile(pct(s.bazaar_success.mean), `bazaar success (min ${pct(s.bazaar_success.min)}, max ${pct(s.bazaar_success.max)})`)}
      ${tile(pct(s.crew_success.mean), `crew success (min ${pct(s.crew_success.min)}, max ${pct(s.crew_success.max)})`)}</div>
    <p>Flex (the agent that overclaims confidence) was hired for <b>data</b> by the fixed crew's one-time interview in <b>${fh.seeds} of ${fh.of}</b> seeds. When that happened:</p>
    <div class="vsline"><div class="vscol crew"><div class="big">${d.crew ? pct(d.crew.mean) : "–"}</div><div class="lbl">crew success on data tasks</div></div>
      <div class="vscol bazaar"><div class="big">${d.bazaar ? pct(d.bazaar.mean) : "–"}</div><div class="lbl">bazaar success on the same tasks</div></div></div>
    <p class="small muted">In the market, Flex's share of the "data" auctions it enters falls from ${pct(f.phase1_mean)} in the first third of a run to ${pct(f.phase3_mean)} in the last third, as its reputation catches up with it:
      average cost across these runs was ${money(s.bazaar_cost.mean)} for the market against ${money(s.crew_cost.mean)} for the crew — the market is not free, it is a better trade.</p>`;
}

// ------------------------------------------------------------------ HOW
function viewHow() {
  view().innerHTML = `<div class="prose panel">
    <h3>1. Contract-Net, one auction per task</h3><p>A task (a category and a complexity) is broadcast. Every agent whose true skill in that category clears its own participation bar — or, for an agent that <code>bids_outside_skill</code>, every agent regardless — submits a <b>bid</b>: a price, an ETA and a claimed confidence.
      The claim is computed from the agent's skill and a per-agent <code>honesty</code> factor; an honest agent's confidence tracks its skill, an overclaiming one inflates confidence most exactly where its skill is weakest.</p>
    <h3>2. The auctioneer scores, never the agent's word for it</h3><p>Price and ETA are scored relative to the field in that one auction (cheapest/fastest wins the price/eta share); confidence is multiplied by the bidder's <b>reputation</b> in that category — a Beta distribution built only from outcomes, never from what anyone claims about themselves.
      The highest score wins. Weights (price / ETA / confidence) are 15% / 10% / 75% by default — confidence and track record matter far more than being cheap.</p>
    <h3>3. Execution and the lesson it teaches</h3><p>What actually happens is a function of the winner's <i>real</i> skill and the task's complexity, never of the bid. A success or a failure updates that agent's reputation for that category, which changes the next auction's scoring — this is the whole feedback loop; nothing else does the "routing around".</p>
    <h3>4. The comparison: a fixed-role crew</h3><p>The usual alternative (how CrewAI- or AutoGen-style tooling is normally set up) hires one agent per category, once, at an interview where nobody has a track record yet — and never revisits the decision. Both systems get the identical task stream and the identical outcome draws, so the only thing that differs is whether reputation ever gets to act.</p>
    <h3>Honest limits</h3><ul><li>Ten agents and eight categories are hand-designed so the story is legible, including the specific rivalry between Bolt (genuinely skilled) and Flex (overclaiming) in "data" — this is a demonstration scenario, not a claim about real contractor markets.</li>
      <li>"Reputation routes around dishonesty" held in 39 of 40 tested seeds, by 17.8 points of success rate on average — not every seed, and the market spends a bit more on average doing it (see Compare).</li>
      <li>The scoring weights were chosen so Flex can win early (when nobody has a track record) and lose later; a different weighting could blunt or sharpen the effect, and nothing here searches for the "best" market design.</li></ul></div>`;
}

boot();
