#!/usr/bin/env python3
"""Render the JSON written by `multiplex_demo.py --json` as an HTML timeline.

Each demo becomes two panels (HTTP/1.1, HTTP/2) on a shared time axis. Every
transfer is a bar split into its phases as curl measured them: TCP connect,
TLS handshake, waiting for the first byte, body transfer. Bars are grouped
into lanes by TCP connection, so connection reuse and the number of sockets
are visible directly.

Usage: python experiments/multiplex_viz.py [captures/multiplex_run.json] [out.html]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = r"""<title>HTTP Multiplexing Timeline</title>
<style>
  /* Layout: one column of demo sections; each demo is a two-panel grid (HTTP/1.1 | HTTP/2)
     on a shared time axis, lanes grouped by TCP connection. */
  :root {
    --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --axis: #c3c2b7; --lane: rgba(11,11,11,0.035); --ring: rgba(11,11,11,0.10);
    --p1: #86b6ef; --p2: #5598e7; --p3: #2a78d6; --p4: #184f95;   /* ordinal blue: connect, tls, wait, body */
    --tip-bg: #ffffff;
    --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --lane: rgba(255,255,255,0.04); --ring: rgba(255,255,255,0.10);
    --p1: #9ec5f4; --p2: #6da7ec; --p3: #3987e5; --p4: #1c5cab; --tip-bg: #242423; color-scheme: dark; } }
  :root[data-theme="dark"] {
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --lane: rgba(255,255,255,0.04); --ring: rgba(255,255,255,0.10);
    --p1: #9ec5f4; --p2: #6da7ec; --p3: #3987e5; --p4: #1c5cab; --tip-bg: #242423; color-scheme: dark; }

  body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.5 var(--sans); }
  .wrap { max-width: 1100px; margin: 0 auto; padding-block: 32px 56px; padding-inline: 16px; }
  h1 { font-size: 1.6rem; line-height: 1.2; margin: 0 0 6px; letter-spacing: -0.01em; text-wrap: balance; }
  h2 { font-size: 1.1rem; margin: 0 0 4px; text-wrap: balance; }
  h3 { font-size: 0.8rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink-2); margin: 0; }
  p { max-width: 68ch; margin: 0; }
  .lede { color: var(--ink-2); }
  .meta { color: var(--muted); font-size: 0.8rem; font-family: var(--mono); margin-top: 8px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 20px 0 4px; font-size: 0.85rem; color: var(--ink-2); align-items: center; }
  .legend span { display: inline-flex; align-items: center; gap: 7px; }
  .sw { width: 14px; height: 14px; border-radius: 3px; box-shadow: inset 0 0 0 1px var(--ring); }
  .demo { margin-top: 36px; }
  .demo .what { color: var(--ink-2); margin: 4px 0 12px; }
  .panels { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 760px) { .panels { grid-template-columns: 1fr; } }
  .panel { background: var(--surface); border-radius: 8px; box-shadow: inset 0 0 0 1px var(--ring); padding: 14px 14px 10px; min-width: 0; }
  .panel header { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 8px; }
  .stat { font-family: var(--mono); font-size: 0.78rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }
  .stat b { color: var(--ink); font-weight: 600; }
  svg { display: block; width: 100%; height: auto; overflow: visible; }
  .tick text, .lane-label { font-family: var(--sans); font-size: 11px; fill: var(--muted); }
  .tick line { stroke: var(--grid); stroke-width: 1; shape-rendering: crispEdges; }
  .axis { stroke: var(--axis); stroke-width: 1; shape-rendering: crispEdges; }
  .lane-bg { fill: var(--lane); }
  .bar-label { font-size: 11px; fill: var(--ink-2); font-family: var(--mono); }
  .hit { fill: transparent; cursor: default; outline: none; }
  .hit:focus-visible + .focus-ring { stroke: var(--ink); stroke-width: 2; fill: none; }
  .focus-ring { stroke: none; fill: none; pointer-events: none; }
  .tip { position: fixed; z-index: 10; pointer-events: none; background: var(--tip-bg); color: var(--ink);
         box-shadow: 0 0 0 1px var(--ring), 0 6px 20px rgba(0,0,0,0.18); border-radius: 6px; padding: 8px 10px;
         font-size: 12px; line-height: 1.45; font-variant-numeric: tabular-nums; max-width: 260px; }
  .tip b { font-weight: 600; }
  .tip .row { display: flex; justify-content: space-between; gap: 14px; }
  .tip .row i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
  details { margin-top: 10px; font-size: 0.85rem; }
  summary { cursor: pointer; color: var(--ink-2); }
  summary:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; border-radius: 3px; }
  .tablewrap { overflow-x: auto; margin-top: 6px; }
  table { border-collapse: collapse; font-size: 0.8rem; font-variant-numeric: tabular-nums; min-width: 560px; }
  th, td { text-align: right; padding: 4px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
  th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
  th { color: var(--ink-2); font-weight: 600; }
  .takeaways { margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--grid); }
  .takeaways ul { margin: 8px 0 0; padding-left: 20px; }
  .takeaways li { margin: 4px 0; max-width: 68ch; }
  @media (prefers-reduced-motion: no-preference) { .tip { transition: opacity 80ms; } }
</style>

<div class="wrap">
  <h1>HTTP Multiplexing Timeline</h1>
  <p class="lede">Each bar is one HTTP transfer, placed where it actually happened in time and split into the phases curl measured. Bars are grouped into lanes by TCP connection. HTTP/1.1 and HTTP/2 share a time axis in every demo, so the shape of the difference is the point.</p>
  <p class="meta" id="meta"></p>
  <div class="legend" id="legend" aria-label="Phases of a transfer"></div>
  <div id="demos"></div>
  <section class="takeaways">
    <h2>How to read it</h2>
    <ul>
      <li><b>A.</b> HTTP/1.1 needs one lane per concurrent request and pays a TCP connect and TLS handshake in each. HTTP/2 runs every request in one lane and pays the handshake once.</li>
      <li><b>B.</b> Browsers allow about six HTTP/1.1 connections per host. With eight requests, two must wait for a lane to free up, and when they do, that lane is reused (no connect or TLS segment on the second bar). On HTTP/2, all eight start together in the one lane.</li>
      <li><b>C.</b> On a single HTTP/1.1 connection, the fast request cannot start until the slow response has finished: head-of-line blocking. On HTTP/2 the fast stream completes while the slow one is still open.</li>
      <li>Every Server-Sent Events stream is a response that stays open. On HTTP/1.1 it holds a lane for its whole life; on HTTP/2 it is just one more stream.</li>
    </ul>
  </section>
</div>
<div class="tip" id="tip" hidden></div>

<script>
const DATA = __DATA__;
const PHASES = [
  { key: "connect", name: "TCP connect",        v: "--p1" },
  { key: "tls",     name: "TLS handshake",      v: "--p2" },
  { key: "wait",    name: "Waiting for first byte", v: "--p3" },
  { key: "body",    name: "Body transfer",      v: "--p4" },
];
const PROTO = { "http1.1": "HTTP/1.1", "http2": "HTTP/2" };
const NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}, parent) => {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.appendChild(n);
  return n;
};
const fmt = (s) => (s >= 1 ? s.toFixed(2) + " s" : Math.round(s * 1000) + " ms");

// phases as [start, end] offsets within a transfer
function phases(t) {
  const c = t.connect, a = Math.max(t.appconnect, c), w = Math.max(t.starttransfer, a), e = Math.max(t.total, w);
  return [[0, c], [c, a], [a, w], [w, e]];
}

function renderMeta() {
  document.getElementById("meta").textContent =
    `run ${DATA.generated}  ·  ${DATA.host}  ·  ${DATA.curl}`;
  const lg = document.getElementById("legend");
  for (const p of PHASES) {
    const s = document.createElement("span");
    const sw = document.createElement("i"); sw.className = "sw"; sw.style.background = `var(${p.v})`;
    s.appendChild(sw); s.appendChild(document.createTextNode(p.name)); lg.appendChild(s);
  }
}

function niceStep(domain) {
  for (const s of [0.05, 0.1, 0.25, 0.5, 1, 2]) if (domain / s <= 8) return s;
  return 5;
}

function renderPanel(run, domain, container) {
  const panel = document.createElement("div"); panel.className = "panel";
  const head = document.createElement("header");
  const h3 = document.createElement("h3"); h3.textContent = PROTO[run.proto] || run.proto;
  if (run.parallel_max) h3.textContent += ` · at most ${run.parallel_max} at once`;
  const stat = document.createElement("span"); stat.className = "stat";
  const strong = document.createElement("b"); strong.textContent = `${run.connections} TCP connection${run.connections === 1 ? "" : "s"}`;
  stat.appendChild(strong);
  stat.appendChild(document.createTextNode(`  ·  wall ${run.wall.toFixed(2)} s` +
    (run.stream_ids.length ? `  ·  streams ${run.stream_ids.join(", ")}` : "")));
  head.appendChild(h3); head.appendChild(stat); panel.appendChild(head);

  // lanes: group by connection id, order by first start
  const lanes = new Map();
  for (const t of [...run.transfers].sort((a, b) => a.start - b.start)) {
    if (!lanes.has(t.conn_id)) lanes.set(t.conn_id, []);
    lanes.get(t.conn_id).push(t);
  }
  const W = 640, L = 62, R = 14, TOP = 8, ROW = 20, LANEPAD = 6, AXIS_H = 26, BAR = 14;
  let rows = 0; for (const v of lanes.values()) rows += v.length;
  const H = TOP + rows * ROW + lanes.size * LANEPAD + AXIS_H;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": `${PROTO[run.proto]} timeline, ${run.transfers.length} transfers on ${run.connections} connections` });
  const x = (s) => L + (s / domain) * (W - L - R);
  const plotBottom = H - AXIS_H;

  // grid + ticks
  const step = niceStep(domain);
  for (let v = 0; v <= domain + 1e-9; v += step) {
    const g = el("g", { class: "tick" }, svg);
    el("line", { x1: x(v), x2: x(v), y1: TOP, y2: plotBottom }, g);
    const tx = el("text", { x: x(v), y: plotBottom + 16, "text-anchor": v === 0 ? "start" : "middle" }, g);
    tx.textContent = (step < 1 ? v.toFixed(2).replace(/0+$/, "").replace(/\.$/, "") : v) + " s";
  }
  el("line", { class: "axis", x1: L, x2: W - R, y1: plotBottom, y2: plotBottom }, svg);

  let y = TOP, laneIdx = 0;
  for (const [cid, list] of lanes) {
    const laneH = list.length * ROW + LANEPAD;
    if (laneIdx % 2 === 1) el("rect", { class: "lane-bg", x: L, y: y - LANEPAD / 2, width: W - L - R, height: laneH }, svg);
    const lab = el("text", { class: "lane-label", x: L - 8, y: y + ROW / 2 + 4, "text-anchor": "end" }, svg);
    lab.textContent = `conn ${cid}`;
    for (const t of list) {
      const by = y + (ROW - BAR) / 2;
      const segs = phases(t);
      segs.forEach(([a, b], i) => {
        let x0 = x(t.start + a), x1 = x(t.start + b);
        if (x1 - x0 < 0.5) return;
        if (i < 3 && x1 - x0 > 4) x1 -= 2;                 // 2px surface gap between phases
        const w = Math.max(x1 - x0, 1);
        const r = el("rect", { x: x0, y: by, width: w, height: BAR, rx: 2, fill: `var(${PHASES[i].v})` }, svg);
      });
      const endX = x(t.end);
      const label = el("text", { class: "bar-label", x: endX + 6, y: by + BAR - 3 }, svg);
      label.textContent = t.url;
      // hit target bigger than the mark
      const hit = el("rect", { class: "hit", x: x(t.start) - 4, y: by - 3, width: Math.max(x(t.end) - x(t.start), 2) + 8, height: BAR + 6, tabindex: 0 }, svg);
      el("rect", { class: "focus-ring", x: x(t.start) - 2, y: by - 2, width: Math.max(x(t.end) - x(t.start), 2) + 4, height: BAR + 4, rx: 3 }, svg);
      attachTip(hit, t, cid, run);
      y += ROW;
    }
    y += LANEPAD; laneIdx++;
  }
  panel.appendChild(svg);
  container.appendChild(panel);
}

const tip = document.getElementById("tip");
function attachTip(node, t, cid, run) {
  const show = (ev) => {
    tip.replaceChildren();
    const title = document.createElement("div");
    const b = document.createElement("b"); b.textContent = `${t.url}  ·  ${PROTO[run.proto]}`;
    title.appendChild(b); tip.appendChild(title);
    const sub = document.createElement("div"); sub.style.color = "var(--ink-2)";
    sub.textContent = `connection ${cid}  ·  ${fmt(t.start)} → ${fmt(t.end)}`;
    tip.appendChild(sub);
    phases(t).forEach(([a, bnd], i) => {
      const row = document.createElement("div"); row.className = "row";
      const l = document.createElement("span");
      const sw = document.createElement("i"); sw.style.background = `var(${PHASES[i].v})`;
      l.appendChild(sw); l.appendChild(document.createTextNode(PHASES[i].name));
      const v = document.createElement("b"); v.textContent = bnd - a < 0.0005 ? "reused" : fmt(bnd - a);
      if (i > 1 && bnd - a < 0.0005) v.textContent = "0 ms";
      row.appendChild(l); row.appendChild(v); tip.appendChild(row);
    });
    tip.hidden = false; move(ev);
  };
  const move = (ev) => {
    const r = node.getBoundingClientRect();
    const px = ev && ev.clientX != null ? ev.clientX : r.left + r.width / 2;
    const py = ev && ev.clientY != null ? ev.clientY : r.top;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    let left = px + 14, top = py - th - 10;
    if (left + tw > window.innerWidth - 8) left = px - tw - 14;
    if (top < 8) top = py + 18;
    tip.style.left = left + "px"; tip.style.top = top + "px";
  };
  const hide = () => { tip.hidden = true; };
  node.addEventListener("pointerenter", show);
  node.addEventListener("pointermove", move);
  node.addEventListener("pointerleave", hide);
  node.addEventListener("focus", show);
  node.addEventListener("blur", hide);
}

function renderTable(runs, container) {
  const d = document.createElement("details");
  const s = document.createElement("summary"); s.textContent = "Table view"; d.appendChild(s);
  const wrap = document.createElement("div"); wrap.className = "tablewrap";
  const tb = document.createElement("table");
  const thead = tb.createTHead().insertRow();
  for (const h of ["Protocol", "URL", "Conn", "Start", "End", "Connect", "TLS", "Wait", "Body"]) {
    const th = document.createElement("th"); th.textContent = h; thead.appendChild(th);
  }
  const body = tb.createTBody();
  for (const run of runs) for (const t of [...run.transfers].sort((a, b) => a.start - b.start)) {
    const r = body.insertRow();
    const ph = phases(t).map(([a, b]) => b - a);
    for (const v of [PROTO[run.proto], t.url, String(t.conn_id), fmt(t.start), fmt(t.end), ...ph.map(fmt)]) {
      r.insertCell().textContent = v;
    }
  }
  wrap.appendChild(tb); d.appendChild(wrap); container.appendChild(d);
}

const WHAT = {
  A: "Count the lanes. Then look at the left end of each bar for the two handshake segments.",
  B: "Six lanes fill, two requests wait. Find the lane that gets a second bar, and notice it has no handshake segments.",
  C: "The fast request is the short bar. See where it sits relative to the slow one.",
};

function render() {
  renderMeta();
  const root = document.getElementById("demos");
  const byDemo = new Map();
  for (const r of DATA.runs) { if (!byDemo.has(r.demo)) byDemo.set(r.demo, []); byDemo.get(r.demo).push(r); }
  for (const [demo, runs] of byDemo) {
    const sec = document.createElement("section"); sec.className = "demo";
    const h2 = document.createElement("h2"); h2.textContent = `${demo}. ${DATA.titles[demo] || ""}`; sec.appendChild(h2);
    const what = document.createElement("p"); what.className = "what"; what.textContent = WHAT[demo] || ""; sec.appendChild(what);
    const panels = document.createElement("div"); panels.className = "panels";
    const maxWall = Math.max(...runs.map(r => r.wall));
    const step = niceStep(maxWall);
    const domain = Math.ceil(maxWall / step) * step;
    for (const r of runs) renderPanel(r, domain, panels);
    sec.appendChild(panels);
    renderTable(runs, sec);
    root.appendChild(sec);
  }
}
render();
</script>
"""


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "captures" / "multiplex_run.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    data = json.loads(src.read_text())
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    out.write_text(html)
    print(f"wrote {out} ({len(html) // 1024} KB) from {src}")


if __name__ == "__main__":
    main()
