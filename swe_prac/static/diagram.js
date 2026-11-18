// Box-and-arrow diagram editor for the high-level design step. Plain SVG, no dependencies.
//
// Model (saved with the session): { nodes: [{id, kind, x, y, w, h, label}], edges: [{id, from, to, label}] }
// Editing: add shapes from the toolbar (or double-click empty canvas), drag to move, drag the dot on
// a selected shape onto another to draw an arrow, double-click a shape or arrow to label it,
// Delete removes the selection.

import { esc } from "./common.js";

const KINDS = {
  client: { name: "Client", w: 120, h: 48 },
  box: { name: "Service", w: 140, h: 56 },
  store: { name: "Database", w: 130, h: 72 },
  queue: { name: "Queue", w: 150, h: 46 },
  note: { name: "Note", w: 170, h: 44 },
};
const CANVAS = { w: 2400, h: 1600 };
const GRID = 10;
const snap = (v) => Math.round(v / GRID) * GRID;

export function normalize(model) {
  const nodes = Array.isArray(model?.nodes) ? model.nodes.filter((n) => n && n.id) : [];
  const ids = new Set(nodes.map((n) => n.id));
  const edges = Array.isArray(model?.edges)
    ? model.edges.filter((e) => e && ids.has(e.from) && ids.has(e.to)) : [];
  return {
    nodes: nodes.map((n) => {
      const kind = KINDS[n.kind] ? n.kind : "box";
      return {
        id: String(n.id), kind, label: String(n.label ?? ""),
        x: Number(n.x) || 0, y: Number(n.y) || 0,
        w: Number(n.w) || KINDS[kind].w, h: Number(n.h) || KINDS[kind].h,
      };
    }),
    edges: edges.map((e) => ({ id: String(e.id), from: String(e.from), to: String(e.to), label: String(e.label ?? "") })),
  };
}

// ---------------------------------------------------------------- drawing
function shape(n) {
  const { x, y, w, h } = n;
  if (n.kind === "store") {
    const ry = 9;
    return `<path class="dg-body" d="M${x} ${y + ry} L${x} ${y + h - ry} A${w / 2} ${ry} 0 0 0 ${x + w} ${y + h - ry} L${x + w} ${y + ry}"/>
      <ellipse class="dg-body" cx="${x + w / 2}" cy="${y + ry}" rx="${w / 2}" ry="${ry}"/>`;
  }
  if (n.kind === "queue") {
    const slots = [0.68, 0.78, 0.88].map((f) => `<line class="dg-slot" x1="${x + w * f}" y1="${y + 6}" x2="${x + w * f}" y2="${y + h - 6}"/>`);
    return `<rect class="dg-body" x="${x}" y="${y}" width="${w}" height="${h}" rx="4"/>${slots.join("")}`;
  }
  const rx = n.kind === "client" ? h / 2 : n.kind === "note" ? 2 : 8;
  return `<rect class="dg-body" x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}"/>`;
}

function label(text, cx, cy, cls = "dg-label") {
  const lines = String(text).split("\n");
  const first = cy - ((lines.length - 1) * 16) / 2;
  return `<text class="${cls}" x="${cx}" y="${first}" text-anchor="middle" dominant-baseline="central">${
    lines.map((line, i) => `<tspan x="${cx}" y="${first + i * 16}">${esc(line)}</tspan>`).join("")}</text>`;
}

// Where the line from n's center towards (tx, ty) leaves n's bounding box.
function boundary(n, tx, ty) {
  const cx = n.x + n.w / 2, cy = n.y + n.h / 2;
  const dx = tx - cx, dy = ty - cy;
  if (!dx && !dy) return [cx, cy];
  const t = Math.min(dx ? (n.w / 2) / Math.abs(dx) : Infinity, dy ? (n.h / 2) / Math.abs(dy) : Infinity);
  return [cx + dx * t, cy + dy * t];
}

function edgeGeometry(e, byId) {
  const a = byId.get(e.from), b = byId.get(e.to);
  const [x1, y1] = boundary(a, b.x + b.w / 2, b.y + b.h / 2);
  const [x2, y2] = boundary(b, a.x + a.w / 2, a.y + a.h / 2);
  return { x1, y1, x2, y2 };
}

function svgBody(model, sel = {}) {
  const byId = new Map(model.nodes.map((n) => [n.id, n]));
  const edges = model.edges.map((e) => {
    const { x1, y1, x2, y2 } = edgeGeometry(e, byId);
    const cls = sel.edge === e.id ? "dg-edge selected" : "dg-edge";
    const text = e.label ? label(e.label, (x1 + x2) / 2, (y1 + y2) / 2, "dg-edge-label") : "";
    return `<g class="${cls}" data-edge="${esc(e.id)}">
      <line class="dg-hit" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>
      <line class="dg-line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" marker-end="url(#dg-arrow)"/>${text}</g>`;
  });
  // Every shape gets an arrow handle; CSS shows it only on the selected shape while editable.
  const nodes = model.nodes.map((n) => {
    const handle = sel.editable
      ? `<circle class="dg-handle" data-handle="${esc(n.id)}" cx="${n.x + n.w}" cy="${n.y + n.h / 2}" r="7"><title>Drag onto another shape to draw an arrow</title></circle>` : "";
    return `<g class="dg-node dg-${n.kind}${sel.node === n.id ? " selected" : ""}" data-node="${esc(n.id)}">
      ${shape(n)}${label(n.label, n.x + n.w / 2, n.y + n.h / 2 + (n.kind === "store" ? 5 : 0))}${handle}</g>`;
  });
  const rubber = sel.rubber
    ? `<line class="dg-line dg-rubber" x1="${sel.rubber.x1}" y1="${sel.rubber.y1}" x2="${sel.rubber.x2}" y2="${sel.rubber.y2}" marker-end="url(#dg-arrow)"/>` : "";
  return `<defs><marker id="dg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" class="dg-arrowhead"/></marker></defs>
    ${edges.join("")}${nodes.join("")}${rubber}`;
}

// A read-only picture of a diagram, cropped to its contents (review page).
export function renderDiagramSvg(raw) {
  const model = normalize(raw);
  if (!model.nodes.length) return "";
  const pad = 24;
  const minX = Math.min(...model.nodes.map((n) => n.x)) - pad;
  const minY = Math.min(...model.nodes.map((n) => n.y)) - pad;
  const maxX = Math.max(...model.nodes.map((n) => n.x + n.w)) + pad;
  const maxY = Math.max(...model.nodes.map((n) => n.y + n.h)) + pad;
  const w = maxX - minX, h = maxY - minY;
  return `<svg class="dg-svg" viewBox="${minX} ${minY} ${w} ${h}" width="${w}" style="max-width:100%;height:auto"
    role="img" aria-label="Your high-level design diagram">${svgBody(model)}</svg>`;
}

// ---------------------------------------------------------------- editor
export function createDiagramEditor(host, initial, { onChange = () => {} } = {}) {
  let model = normalize(initial);
  let readOnly = false;
  const sel = { node: null, edge: null, editable: true, rubber: null };
  let drag = null; // {kind: "move", id, dx, dy, moved} | {kind: "link", from}
  let counter = model.nodes.length + model.edges.length;
  const newId = (prefix) => `${prefix}${Date.now().toString(36)}${(counter++).toString(36)}`;

  host.innerHTML = `<div class="diagram">
    <div class="diagram-toolbar">
      <span class="faint">Add</span>
      ${Object.entries(KINDS).map(([k, v]) => `<button class="small" data-add="${k}">${v.name}</button>`).join("")}
      <button class="small danger" data-delete disabled>Delete</button>
      <span class="diagram-hint">Drag to move · drag the dot onto another shape for an arrow · double-click to label</span>
    </div>
    <div class="diagram-canvas" tabindex="0">
      <svg class="dg-svg" width="${CANVAS.w}" height="${CANVAS.h}" viewBox="0 0 ${CANVAS.w} ${CANVAS.h}"></svg>
      <textarea class="diagram-input hidden" rows="1" spellcheck="false"></textarea>
    </div>
  </div>`;
  const canvas = host.querySelector(".diagram-canvas");
  const svg = host.querySelector("svg");
  const input = host.querySelector(".diagram-input");
  const delBtn = host.querySelector("[data-delete]");

  // A full redraw is only for model changes. Selection just toggles classes: replacing the element
  // under the pointer mid-click would stop the browser from firing click and dblclick.
  const render = () => {
    sel.editable = !readOnly;
    svg.innerHTML = svgBody(model, sel);
    paintSelection();
  };
  function paintSelection() {
    svg.querySelectorAll("[data-node]").forEach((g) => g.classList.toggle("selected", g.dataset.node === sel.node));
    svg.querySelectorAll("[data-edge]").forEach((g) => g.classList.toggle("selected", g.dataset.edge === sel.edge));
    delBtn.disabled = readOnly || !(sel.node || sel.edge);
  }
  const changed = () => { render(); onChange(); };
  const point = (e) => {
    const r = svg.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  const nodeAt = ({ x, y }) => [...model.nodes].reverse().find((n) => x >= n.x && x <= n.x + n.w && y >= n.y && y <= n.y + n.h);
  const edgeAt = ({ x, y }) => {
    const byId = new Map(model.nodes.map((n) => [n.id, n]));
    return model.edges.find((e) => {
      const { x1, y1, x2, y2 } = edgeGeometry(e, byId);
      const len2 = (x2 - x1) ** 2 + (y2 - y1) ** 2 || 1;
      const t = Math.max(0, Math.min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / len2));
      return Math.hypot(x - (x1 + t * (x2 - x1)), y - (y1 + t * (y2 - y1))) <= 6;
    });
  };

  // The first grid slot in view that doesn't overlap an existing shape.
  function freeSpot(k) {
    const x0 = snap(canvas.scrollLeft + 40), y0 = snap(canvas.scrollTop + 40);
    const cols = Math.max(1, Math.floor((canvas.clientWidth - 80) / 190));
    for (let i = 0; i < 300; i++) {
      const x = x0 + (i % cols) * 190, y = y0 + Math.floor(i / cols) * 120;
      const clash = model.nodes.some((n) => x < n.x + n.w + 20 && x + k.w + 20 > n.x && y < n.y + n.h + 20 && y + k.h + 20 > n.y);
      if (!clash) return { x, y };
    }
    return { x: x0, y: y0 };
  }

  function addNode(kind, at) {
    const k = KINDS[kind];
    let x, y;
    if (at) { x = at.x - k.w / 2; y = at.y - k.h / 2; } else ({ x, y } = freeSpot(k));
    const node = { id: newId("n"), kind, x: snap(Math.max(0, x)), y: snap(Math.max(0, y)), w: k.w, h: k.h, label: k.name };
    model.nodes.push(node);
    sel.node = node.id; sel.edge = null;
    changed();
    return node;
  }

  function removeSelected() {
    if (readOnly) return;
    if (sel.node) {
      model.nodes = model.nodes.filter((n) => n.id !== sel.node);
      model.edges = model.edges.filter((e) => e.from !== sel.node && e.to !== sel.node);
    } else if (sel.edge) {
      model.edges = model.edges.filter((e) => e.id !== sel.edge);
    } else return;
    sel.node = sel.edge = null;
    changed();
  }

  function connect(from, to) {
    if (from === to || model.edges.some((e) => e.from === from && e.to === to)) return;
    const edge = { id: newId("e"), from, to, label: "" };
    model.edges.push(edge);
    sel.node = null; sel.edge = edge.id;
    changed();
  }

  // Inline label editing: a textarea laid over the shape (or the arrow's midpoint).
  function editLabel(target) {
    if (readOnly) return;
    let box;
    if (target.type === "node") {
      const n = model.nodes.find((x) => x.id === target.id);
      box = { x: n.x, y: n.y + n.h / 2 - 16, w: n.w, value: n.label };
    } else {
      const e = model.edges.find((x) => x.id === target.id);
      const g = edgeGeometry(e, new Map(model.nodes.map((n) => [n.id, n])));
      box = { x: (g.x1 + g.x2) / 2 - 80, y: (g.y1 + g.y2) / 2 - 16, w: 160, value: e.label };
    }
    Object.assign(input.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${box.w}px` });
    input.value = box.value;
    input.classList.remove("hidden");
    input.focus();
    input.select();
    const finish = (save) => {
      input.onblur = input.onkeydown = null;
      input.classList.add("hidden");
      canvas.focus();
      if (!save) return;
      const list = target.type === "node" ? model.nodes : model.edges;
      const item = list.find((x) => x.id === target.id);
      if (item && item.label !== input.value) { item.label = input.value; changed(); }
    };
    input.onblur = () => finish(true);
    input.onkeydown = (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); finish(true); }
      if (ev.key === "Escape") { ev.preventDefault(); finish(false); }
      ev.stopPropagation();
    };
  }

  svg.addEventListener("pointerdown", (e) => {
    if (readOnly || e.button !== 0) return;
    canvas.focus({ preventScroll: true });
    const p = point(e);
    const handle = e.target.closest("[data-handle]");
    const nodeEl = e.target.closest("[data-node]");
    const edgeEl = e.target.closest("[data-edge]");
    if (handle) {
      drag = { kind: "link", from: handle.dataset.handle };
    } else if (nodeEl) {
      const n = model.nodes.find((x) => x.id === nodeEl.dataset.node);
      sel.node = n.id; sel.edge = null;
      drag = { kind: "move", id: n.id, dx: p.x - n.x, dy: p.y - n.y, moved: false };
    } else if (edgeEl) {
      sel.edge = edgeEl.dataset.edge; sel.node = null;
    } else {
      sel.node = sel.edge = null;
    }
    if (drag) svg.setPointerCapture(e.pointerId);
    paintSelection();
  });

  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const p = point(e);
    if (drag.kind === "move") {
      const n = model.nodes.find((x) => x.id === drag.id);
      const x = snap(Math.max(0, Math.min(CANVAS.w - n.w, p.x - drag.dx)));
      const y = snap(Math.max(0, Math.min(CANVAS.h - n.h, p.y - drag.dy)));
      if (x !== n.x || y !== n.y) { n.x = x; n.y = y; drag.moved = true; render(); }
    } else {
      const from = model.nodes.find((x) => x.id === drag.from);
      const [x1, y1] = boundary(from, p.x, p.y);
      sel.rubber = { x1, y1, x2: p.x, y2: p.y };
      render();
    }
  });

  const endDrag = (e) => {
    if (!drag) return;
    const was = drag;
    drag = null;
    sel.rubber = null;
    if (was.kind === "move") {
      if (was.moved) changed();
    } else {
      const target = nodeAt(point(e));
      if (target) connect(was.from, target.id); else render();
    }
  };
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);

  // By position, not e.target: after a drag the element under the pointer may have been redrawn.
  svg.addEventListener("dblclick", (e) => {
    if (readOnly) return;
    const p = point(e);
    const node = nodeAt(p);
    const edge = node ? null : edgeAt(p);
    if (node) editLabel({ type: "node", id: node.id });
    else if (edge) editLabel({ type: "edge", id: edge.id });
    else editLabel({ type: "node", id: addNode("box", p).id });
  });

  canvas.addEventListener("keydown", (e) => {
    if (e.target !== canvas) return;
    if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); removeSelected(); }
    if (e.key === "Escape") { sel.node = sel.edge = null; paintSelection(); }
    if (e.key === "F2" && sel.node) editLabel({ type: "node", id: sel.node });
  });

  host.querySelectorAll("[data-add]").forEach((b) => {
    b.onclick = () => { if (!readOnly) { addNode(b.dataset.add); canvas.focus({ preventScroll: true }); } };
  });
  delBtn.onclick = removeSelected;

  render();
  return {
    getModel: () => structuredClone(model),
    setReadOnly(value) {
      readOnly = value;
      if (value) { sel.node = sel.edge = null; drag = null; input.classList.add("hidden"); }
      host.querySelector(".diagram").classList.toggle("readonly", value);
      host.querySelectorAll(".diagram-toolbar button").forEach((b) => { b.disabled = value; });
      render();
    },
  };
}
