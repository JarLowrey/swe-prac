// The whiteboard of a system design session: text, boxes, circles and diamonds with text inside
// them, and lines and arrows that connect them (or start and end anywhere). Plain SVG, no
// dependencies; the model, sizes and geometry are in board-model.js.
//
// Mouse: double-click empty space to type, or add a shape from the toolbar. Pick Line or Arrow,
// then drag from one item to another; an end dropped on empty space stays where it is. Drag to
// move (a shape carries whatever sits inside it); drag a selected line's end dot to reconnect
// it. Drag one of the dots on a selected shape onto another item to point at it. Drag the corner
// square to resize. Drag across empty space to select an area, Shift-click to add to the
// selection. Space+drag or middle-drag pans, Ctrl+wheel zooms.
// Keys: Enter or F2 edits the text (Esc finishes), Delete removes, L and A pick Line and Arrow,
// Ctrl+Z / Ctrl+Y undo and redo, Ctrl+D duplicates, Ctrl+C / Ctrl+V copy and paste, Ctrl+A
// selects all, arrow keys nudge.

import { esc } from "./common.js";
import {
  CANVAS, GRID, KINDS, LINE, MAX_EDGES, MAX_NODES, boardBounds, boundary, bounds, center, contents,
  edgeGeometry, fitNode, framedIds, isEmpty, isHeading, labelBand, lines, makesTextAt, normalize,
  paintOrder, shown, snap,
} from "./board-model.js";

const FONT = '"Segoe UI", system-ui, -apple-system, Roboto, sans-serif';
const FONT_PX = 14;
const ZOOM = { min: 0.25, max: 2, step: 1.2 };
const TOOLS = { line: { name: "Line", key: "l", ends: "none" }, arrow: { name: "Arrow", key: "a", ends: "end" } };
let clipboard = null; // copied items, shared by every board on the page

// Toolbar icons, 18×14, drawn with the same outlines as the board.
const ICONS = {
  text: '<text x="9" y="11.5" text-anchor="middle" font-size="12" font-weight="700" fill="currentColor" stroke="none">T</text>',
  box: '<rect x="1.5" y="2.5" width="15" height="9" rx="2"/>',
  circle: '<circle cx="9" cy="7" r="5.5"/>',
  diamond: '<path d="M9 1.2l6.5 5.8L9 12.8 2.5 7z"/>',
  line: '<path d="M2.5 11.5L15.5 2.5"/>',
  arrow: '<path d="M2.5 11.5L15.5 2.5M10 2.8l5.5-.3-.3 5.5"/>',
};
const icon = (kind) => `<svg class="wb-icon" viewBox="0 0 18 14" width="18" height="14" aria-hidden="true">${ICONS[kind]}</svg>`;

// ---------------------------------------------------------------- drawing
function shapeSvg(n) {
  const { x, y, w, h } = n;
  const cx = x + w / 2;
  switch (n.kind) {
    case "text":
      return `<rect class="wb-hit" x="${x - 4}" y="${y - 4}" width="${w + 8}" height="${h + 8}" rx="4"/>`;
    case "circle":
      return `<ellipse class="wb-body" cx="${cx}" cy="${y + h / 2}" rx="${w / 2}" ry="${h / 2}"/>`;
    case "diamond":
      return `<path class="wb-body" d="M${cx} ${y} L${x + w} ${y + h / 2} L${cx} ${y + h} L${x} ${y + h / 2} Z"/>`;
    default:
      return `<rect class="wb-body" x="${x}" y="${y}" width="${w}" height="${h}" rx="8"/>`;
  }
}

// One <tspan> per line, each centered on its own line box; "# " lines are headings.
function tspans(rows, x, firstY, boldFirst = false) {
  return rows.map((line, i) => {
    const bold = isHeading(line) || (boldFirst && i === 0);
    return `<tspan x="${x}" y="${firstY + i * LINE}"${bold ? ' class="wb-strong"' : ""}>${esc(shown(line)) || " "}</tspan>`;
  }).join("");
}

function labelSvg(n, framed = false) {
  if (!n.label && n.kind !== "text") return "";
  const rows = lines(n.label);
  const text = (x, y, anchor, boldFirst) => `<text class="wb-label" text-anchor="${anchor}" dominant-baseline="central">${tspans(rows, x, y, boldFirst)}</text>`;
  if (n.kind === "text") return text(n.x + 5, n.y + 4 + LINE / 2, "start");
  if (framed) return text(n.x + n.w / 2, labelBand(n, true)[0] + LINE / 2, "middle", true);
  return text(n.x + n.w / 2, n.y + n.h / 2 - ((rows.length - 1) * LINE) / 2, "middle");
}

const nodeSvg = (n, framed) => `<g class="wb-node wb-${n.kind}${framed ? " framed" : ""}" data-node="${esc(n.id)}">${shapeSvg(n)}${labelSvg(n, framed)}</g>`;

const markers = (ends) => `${ends === "both" ? ' marker-start="url(#wb-arrow)"' : ""}${ends === "none" ? "" : ' marker-end="url(#wb-arrow)"'}`;

function edgeSvg(e, byId) {
  const { x1, y1, x2, y2 } = edgeGeometry(e, byId);
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const rows = lines(e.label);
  const label = e.label
    ? `<text class="wb-edge-label" text-anchor="middle" dominant-baseline="central">${tspans(rows, mx, my - ((rows.length - 1) * LINE) / 2)}</text>` : "";
  return `<g class="wb-edge${e.dash ? " dashed" : ""}" data-edge="${esc(e.id)}">
    <line class="wb-edge-hit" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>
    <line class="wb-line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"${markers(e.ends)}/>${label}</g>`;
}

const DEFS = `<defs><marker id="wb-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8"
    orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" class="wb-arrowhead"/></marker></defs>`;

// Shapes (largest first), then lines and arrows, then free text on top. A box holding other
// items shows its label at the top, like a frame.
function bodySvg(model) {
  const byId = new Map(model.nodes.map((n) => [n.id, n]));
  const order = paintOrder(model.nodes);
  const framed = framedIds(model.nodes);
  return order.filter((n) => n.kind !== "text").map((n) => nodeSvg(n, framed.has(n.id))).join("")
    + model.edges.map((e) => edgeSvg(e, byId)).join("")
    + order.filter((n) => n.kind === "text").map((n) => nodeSvg(n, false)).join("");
}

// A read-only picture of a board, cropped to what's on it (review page). Old diagrams work too.
export function renderBoardSvg(raw) {
  const model = normalize(raw);
  if (isEmpty(model)) return "";
  const b = boardBounds(model, 28);
  return `<svg class="wb-svg wb-static" viewBox="${b.x} ${b.y} ${b.w} ${b.h}" width="${b.w}"
    style="max-width:100%;height:auto" role="img" aria-label="Your whiteboard">${DEFS}${bodySvg(model)}</svg>`;
}

function canvasMeasure() {
  const ctx = document.createElement("canvas").getContext("2d");
  const cache = new Map();
  return (text, bold = false) => {
    const key = `${bold ? 1 : 0}${text}`;
    if (!cache.has(key)) {
      ctx.font = `${bold ? "600 " : ""}${FONT_PX}px ${FONT}`;
      cache.set(key, ctx.measureText(text).width);
    }
    return cache.get(key);
  };
}

// One end of a line: {id} attached to a node, or {x, y} loose.
const END_KEYS = { from: ["x1", "y1"], to: ["x2", "y2"] };
function setEnd(e, which, end) {
  const [kx, ky] = END_KEYS[which];
  if (end.id != null) {
    e[which] = end.id;
    delete e[kx];
    delete e[ky];
  } else {
    e[which] = null;
    e[kx] = end.x;
    e[ky] = end.y;
  }
}

// ---------------------------------------------------------------- editor
export function createWhiteboard(host, initial, { onChange = () => {} } = {}) {
  let model = normalize(initial);
  let readOnly = false;
  let zoom = 1;
  let tool = null; // "line" or "arrow" while drawing one
  const sel = { nodes: new Set(), edges: new Set() };
  let drag = null;
  let spaceDown = false;
  let editing = null; // the open label editor's finish()
  const undo = [], redo = [];
  let counter = 0;
  const newId = (prefix) => `${prefix}${Date.now().toString(36)}${(counter++).toString(36)}`;
  const measure = canvasMeasure();
  // Text takes its size from this browser's font, which can differ from where it was saved.
  for (const n of model.nodes) if (n.kind === "text") fitNode(n, measure);

  const shapeButtons = Object.entries(KINDS).map(([k, v]) =>
    `<button class="small wb-add" data-add="${k}" title="Add ${v.name.toLowerCase()}">${icon(k)}<span>${v.name}</span></button>`).join("");
  const toolButtons = Object.entries(TOOLS).map(([k, v]) =>
    `<button class="small wb-add" data-tool="${k}" title="Draw ${v.name.toLowerCase()}s: drag from one item to another (${v.key.toUpperCase()})">${icon(k)}<span>${v.name}</span></button>`).join("");
  host.innerHTML = `<div class="wb">
    <div class="wb-toolbar">
      <div class="wb-group">${shapeButtons}</div>
      <div class="wb-group">${toolButtons}</div>
      <div class="wb-group" data-edge-tools>
        <button class="small" data-ends="end" title="Arrow at the end (select a line first)" disabled>→</button>
        <button class="small" data-ends="both" title="Arrows at both ends (select a line first)" disabled>↔</button>
        <button class="small" data-ends="none" title="Plain line (select a line first)" disabled>—</button>
        <button class="small" data-dash title="Dashed (select a line first)" disabled>┄ Dashed</button>
      </div>
      <div class="wb-group">
        <button class="small danger" data-delete title="Delete (Del)" disabled>Delete</button>
        <button class="small" data-undo title="Undo (Ctrl+Z)" disabled>↶</button>
        <button class="small" data-redo title="Redo (Ctrl+Y)" disabled>↷</button>
      </div>
      <div class="wb-group">
        <button class="small" data-zoom="out" title="Zoom out">−</button>
        <button class="small ghost wb-zoom" data-zoom="reset" title="Back to 100%">100%</button>
        <button class="small" data-zoom="in" title="Zoom in">+</button>
        <button class="small" data-fit title="Fit everything in view">Fit</button>
      </div>
    </div>
    <div class="wb-canvas" tabindex="0">
      <svg class="wb-svg" xmlns="http://www.w3.org/2000/svg">${DEFS}<g data-layer="body"></g><g data-layer="overlay"></g></svg>
      <textarea class="wb-input hidden" spellcheck="false"></textarea>
    </div>
    <div class="wb-hint" data-hint></div>
  </div>`;
  const q = (s) => host.querySelector(s);
  const root = q(".wb");
  const canvas = q(".wb-canvas");
  const svg = q(".wb-svg");
  const bodyLayer = q('[data-layer="body"]');
  const overlay = q('[data-layer="overlay"]');
  const input = q(".wb-input");

  // ----- history
  const snapshot = () => JSON.stringify(model);
  function commit(before) {
    undo.push(before);
    if (undo.length > 200) undo.shift();
    redo.length = 0;
  }
  function restore(json) {
    model = normalize(JSON.parse(json));
    const nodeIds = new Set(model.nodes.map((n) => n.id));
    const edgeIds = new Set(model.edges.map((e) => e.id));
    sel.nodes = new Set([...sel.nodes].filter((id) => nodeIds.has(id)));
    sel.edges = new Set([...sel.edges].filter((id) => edgeIds.has(id)));
    changed();
  }
  const doUndo = () => { if (undo.length) { redo.push(snapshot()); restore(undo.pop()); } };
  const doRedo = () => { if (redo.length) { undo.push(snapshot()); restore(redo.pop()); } };

  // ----- rendering. The body is redrawn when the model changes; selection only redraws the
  // overlay, so the element under the pointer survives a click (or dblclick would never fire).
  const nodeById = (id) => model.nodes.find((n) => n.id === id);
  const edgeById = (id) => model.edges.find((e) => e.id === id);
  const byId = () => new Map(model.nodes.map((n) => [n.id, n]));
  const clearSel = () => { sel.nodes = new Set(); sel.edges = new Set(); };
  const only = (set) => (set.size === 1 ? [...set][0] : null);

  function sizeSvg() {
    svg.setAttribute("width", CANVAS.w * zoom);
    svg.setAttribute("height", CANVAS.h * zoom);
    svg.setAttribute("viewBox", `0 0 ${CANVAS.w} ${CANVAS.h}`);
    svg.style.backgroundSize = `${20 * zoom}px ${20 * zoom}px`;
    q(".wb-zoom").textContent = `${Math.round(zoom * 100)}%`;
  }
  function renderBody() { bodyLayer.innerHTML = bodySvg(model); }
  const targetBox = (id) => {
    const t = nodeById(id);
    return t ? `<rect class="wb-target" x="${t.x - 6}" y="${t.y - 6}" width="${t.w + 12}" height="${t.h + 12}" rx="6"/>` : "";
  };
  function renderOverlay() {
    const parts = [];
    for (const id of sel.nodes) {
      const n = nodeById(id);
      if (n) parts.push(`<rect class="wb-sel" x="${n.x - 5}" y="${n.y - 5}" width="${n.w + 10}" height="${n.h + 10}" rx="5"/>`);
    }
    const oneNode = !sel.edges.size && !readOnly && !editing && !tool ? nodeById(only(sel.nodes)) : null;
    if (oneNode) {
      const { x, y, w, h } = oneNode;
      const pad = oneNode.kind === "text" ? 5 : 0;
      for (const [cx, cy] of [[x + w / 2, y - pad], [x + w + pad, y + h / 2], [x + w / 2, y + h + pad], [x - pad, y + h / 2]]) {
        parts.push(`<circle class="wb-dot" data-link="${esc(oneNode.id)}" cx="${cx}" cy="${cy}" r="6"><title>Drag onto another item to draw an arrow</title></circle>`);
      }
      if (oneNode.kind !== "text") {
        parts.push(`<rect class="wb-resize" data-resize="${esc(oneNode.id)}" x="${x + w - 5}" y="${y + h - 5}" width="10" height="10" rx="2"><title>Drag to resize</title></rect>`);
      }
    }
    const oneEdge = !sel.nodes.size && !readOnly && !editing && !tool ? edgeById(only(sel.edges)) : null;
    if (oneEdge && drag?.kind !== "end") {
      const g = edgeGeometry(oneEdge, byId());
      for (const [which, cx, cy] of [["from", g.x1, g.y1], ["to", g.x2, g.y2]]) {
        parts.push(`<circle class="wb-end" data-line-end="${which}" cx="${cx}" cy="${cy}" r="6"><title>Drag to move or reconnect this end</title></circle>`);
      }
    }
    if ((drag?.kind === "link" || drag?.kind === "draw") && drag.line) {
      if (drag.target) parts.push(targetBox(drag.target));
      if (drag.kind === "draw" && drag.from) parts.push(targetBox(drag.from));
      const { x1, y1, x2, y2 } = drag.line;
      parts.push(`<line class="wb-line wb-rubber" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"${markers(drag.ends)}/>`);
    }
    if (drag?.kind === "end" && drag.target) parts.push(targetBox(drag.target));
    if (drag?.kind === "marquee" && drag.box) {
      const b = drag.box;
      parts.push(`<rect class="wb-marquee" x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}"/>`);
    }
    overlay.innerHTML = parts.join("");
    bodyLayer.querySelectorAll("[data-edge]").forEach((g) => g.classList.toggle("selected", sel.edges.has(g.dataset.edge)));
    renderToolbar();
  }
  function renderToolbar() {
    const edges = [...sel.edges].map(edgeById).filter(Boolean);
    // Always shown, so the toolbar never changes height as the selection changes.
    host.querySelectorAll("[data-ends]").forEach((b) => {
      b.disabled = readOnly || !edges.length;
      b.classList.toggle("on", edges.length > 0 && edges.every((e) => e.ends === b.dataset.ends));
    });
    q("[data-dash]").disabled = readOnly || !edges.length;
    q("[data-dash]").classList.toggle("on", edges.length > 0 && edges.every((e) => e.dash));
    host.querySelectorAll("[data-tool]").forEach((b) => b.classList.toggle("on", b.dataset.tool === tool));
    root.classList.toggle("drawing", Boolean(tool));
    q("[data-hint]").textContent = tool
      ? `Drag from one item to another, or anywhere, to draw ${tool === "arrow" ? "an arrow" : "a line"} · Esc stops`
      : "Double-click to type, Esc to finish · Line and Arrow connect items · Ctrl+wheel zooms";
    q("[data-delete]").disabled = readOnly || !(sel.nodes.size || sel.edges.size);
    q("[data-undo]").disabled = readOnly || !undo.length;
    q("[data-redo]").disabled = readOnly || !redo.length;
  }
  const render = () => { renderBody(); renderOverlay(); };
  const changed = () => { render(); onChange(); };

  // ----- positions
  const point = (e) => {
    const r = svg.getBoundingClientRect();
    return { x: (e.clientX - r.left) / zoom, y: (e.clientY - r.top) / zoom };
  };
  const snapPoint = (p) => ({ x: Math.max(0, Math.min(CANVAS.w, snap(p.x))), y: Math.max(0, Math.min(CANVAS.h, snap(p.y))) });
  const hits = (n, { x, y }) => {
    const pad = n.kind === "text" ? 4 : 0;
    return x >= n.x - pad && x <= n.x + n.w + pad && y >= n.y - pad && y <= n.y + n.h + pad;
  };
  const nodeAt = (p, except = null) => [...paintOrder(model.nodes)].reverse().find((n) => n.id !== except && hits(n, p)) ?? null;
  const edgeAt = ({ x, y }) => {
    const nodes = byId();
    return [...model.edges].reverse().find((e) => {
      const { x1, y1, x2, y2 } = edgeGeometry(e, nodes);
      const len2 = (x2 - x1) ** 2 + (y2 - y1) ** 2 || 1;
      const t = Math.max(0, Math.min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / len2));
      return Math.hypot(x - (x1 + t * (x2 - x1)), y - (y1 + t * (y2 - y1))) <= 7;
    }) ?? null;
  };
  const view = () => ({
    x: canvas.scrollLeft / zoom, y: canvas.scrollTop / zoom,
    w: canvas.clientWidth / zoom, h: canvas.clientHeight / zoom,
  });

  // The first grid slot in view that doesn't overlap anything.
  function freeSpot(w, h) {
    const v = view();
    const x0 = snap(v.x + 40), y0 = snap(v.y + 40);
    const stepX = Math.max(w, 140) + 40, stepY = Math.max(h, 50) + 40;
    const cols = Math.max(1, Math.floor((v.w - 80) / stepX));
    for (let i = 0; i < 400; i++) {
      const x = x0 + (i % cols) * stepX, y = y0 + Math.floor(i / cols) * stepY;
      const clash = model.nodes.some((n) => x < n.x + n.w + 20 && x + w + 20 > n.x && y < n.y + n.h + 20 && y + h + 20 > n.y);
      if (!clash && x + w <= CANVAS.w && y + h <= CANVAS.h) return { x, y };
    }
    return { x: x0, y: y0 };
  }

  const clampNode = (n) => {
    n.x = Math.max(0, Math.min(CANVAS.w - n.w, n.x));
    n.y = Math.max(0, Math.min(CANVAS.h - n.h, n.y));
  };

  function setTool(value) {
    if (readOnly) return;
    finishEditing();
    tool = value && tool !== value ? value : null;
    if (tool) clearSel();
    renderOverlay();
    canvas.focus({ preventScroll: true });
  }

  function addNode(kind, { at = null, label = "", edit: openEditor = true } = {}) {
    if (readOnly) return null;
    if (model.nodes.length >= MAX_NODES) return null;
    finishEditing();
    tool = null;
    const before = snapshot();
    const node = fitNode({ id: newId("n"), kind, x: 0, y: 0, w: KINDS[kind].w, h: KINDS[kind].h, label }, measure);
    const spot = at ? { x: at.x - (kind === "text" ? 5 : node.w / 2), y: at.y - (kind === "text" ? LINE / 2 + 4 : node.h / 2) } : freeSpot(node.w, node.h);
    node.x = snap(spot.x);
    node.y = snap(spot.y);
    clampNode(node);
    model.nodes.push(node);
    sel.nodes = new Set([node.id]);
    sel.edges = new Set();
    if (openEditor) {
      render();
      edit({ type: "node", id: node.id, before, created: true });
    } else {
      commit(before);
      changed();
    }
    return node;
  }

  // a, b: {id} or {x, y}. The new line or arrow becomes the selection.
  function addEdge(a, b, ends) {
    if (a.id != null && a.id === b.id) return;
    const twin = a.id != null && b.id != null && model.edges.find((e) => e.from === a.id && e.to === b.id);
    if (twin) { clearSel(); sel.edges.add(twin.id); renderOverlay(); return; }
    if (model.edges.length >= MAX_EDGES) return;
    const before = snapshot();
    const edge = { id: newId("e"), from: null, to: null, label: "", ends, dash: false };
    setEnd(edge, "from", a);
    setEnd(edge, "to", b);
    model.edges.push(edge);
    clearSel();
    sel.edges.add(edge.id);
    commit(before);
    changed();
  }

  function removeSelected() {
    if (readOnly || !(sel.nodes.size || sel.edges.size)) return;
    const before = snapshot();
    model.nodes = model.nodes.filter((n) => !sel.nodes.has(n.id));
    model.edges = model.edges.filter((e) => !sel.edges.has(e.id) && !sel.nodes.has(e.from) && !sel.nodes.has(e.to));
    clearSel();
    commit(before);
    changed();
  }

  function setEdgeStyle(change) {
    const edges = [...sel.edges].map(edgeById).filter(Boolean);
    if (!edges.length || readOnly) return;
    const before = snapshot();
    for (const e of edges) Object.assign(e, typeof change === "function" ? change(e) : change);
    commit(before);
    changed();
  }

  // What Ctrl+C takes: the selected items and the lines between selected nodes. A line end on a
  // node that isn't taken comes along loose, where it was drawn.
  const selectedItems = () => {
    const nodes = model.nodes.filter((n) => sel.nodes.has(n.id));
    const geometry = byId();
    const edges = model.edges.filter((e) => sel.edges.has(e.id) || (sel.nodes.has(e.from) && sel.nodes.has(e.to))).map((e) => {
      const copy = structuredClone(e);
      const g = edgeGeometry(e, geometry);
      if (e.from != null && !sel.nodes.has(e.from)) setEnd(copy, "from", { x: g.x1, y: g.y1 });
      if (e.to != null && !sel.nodes.has(e.to)) setEnd(copy, "to", { x: g.x2, y: g.y2 });
      return copy;
    });
    return structuredClone({ nodes, edges });
  };
  // Copies of items, shifted, as the new selection.
  function pasteItems(items, dx, dy) {
    if (readOnly || !(items?.nodes.length || items?.edges.length)) return;
    const before = snapshot();
    const ids = new Map();
    const nodes = items.nodes.slice(0, MAX_NODES - model.nodes.length).map((n) => {
      const copy = { ...n, id: newId("n"), x: n.x + dx, y: n.y + dy };
      clampNode(copy);
      ids.set(n.id, copy.id);
      return copy;
    });
    const end = (e, which) => {
      const [kx, ky] = END_KEYS[which];
      return e[which] != null ? (ids.has(e[which]) ? { id: ids.get(e[which]) } : null) : snapPoint({ x: e[kx] + dx, y: e[ky] + dy });
    };
    const edges = [];
    for (const e of items.edges.slice(0, MAX_EDGES - model.edges.length)) {
      const a = end(e, "from"), b = end(e, "to");
      if (!a || !b) continue;
      const copy = { ...e, id: newId("e") };
      setEnd(copy, "from", a);
      setEnd(copy, "to", b);
      edges.push(copy);
    }
    model.nodes.push(...nodes);
    model.edges.push(...edges);
    sel.nodes = new Set(nodes.map((n) => n.id));
    sel.edges = new Set(edges.map((e) => e.id));
    commit(before);
    changed();
  }

  // The selection plus everything inside a selected shape.
  function movingNodes() {
    const picked = model.nodes.filter((n) => sel.nodes.has(n.id));
    const set = new Set(picked);
    for (const n of picked) for (const c of contents(n, model.nodes)) set.add(c);
    return [...set];
  }
  // The loose ends of the selected lines: [edge, xKey, yKey, x, y].
  function movingEnds() {
    const out = [];
    for (const id of sel.edges) {
      const e = edgeById(id);
      if (!e) continue;
      for (const which of ["from", "to"]) {
        const [kx, ky] = END_KEYS[which];
        if (e[which] == null) out.push([e, kx, ky, e[kx], e[ky]]);
      }
    }
    return out;
  }
  function nudge(dx, dy) {
    if (readOnly || !(sel.nodes.size || sel.edges.size)) return;
    const before = snapshot();
    for (const n of movingNodes()) { n.x += dx; n.y += dy; clampNode(n); }
    for (const [e, kx, ky] of movingEnds()) {
      e[kx] = Math.max(0, Math.min(CANVAS.w, e[kx] + dx));
      e[ky] = Math.max(0, Math.min(CANVAS.h, e[ky] + dy));
    }
    commit(before);
    changed();
  }

  // ----- label editing: a textarea laid over the item, sized to its text as you type
  function placeInput(target) {
    const z = zoom;
    const rows = Math.max(1, input.value.split("\n").length);
    const longest = Math.max(0, ...input.value.split("\n").map((l) => measure(l)));
    Object.assign(input.style, {
      fontSize: `${FONT_PX * z}px`, lineHeight: `${LINE * z}px`, padding: `${4 * z}px ${5 * z}px`,
    });
    let box;
    if (target.type === "edge") {
      const g = edgeGeometry(edgeById(target.id), byId());
      const w = Math.max(160, longest + 30);
      box = { x: (g.x1 + g.x2) / 2 - w / 2, y: (g.y1 + g.y2) / 2 - (rows * LINE) / 2 - 5, w, align: "center" };
    } else {
      const n = nodeById(target.id);
      if (n.kind === "text") {
        box = { x: n.x, y: n.y, w: Math.max(180, longest + 40), align: "left" };
      } else if (framedIds(model.nodes).has(n.id)) {
        const w = Math.max(n.w, 160, longest + 30);
        box = { x: n.x + n.w / 2 - w / 2, y: labelBand(n, true)[0] - 5, w, align: "center" };
      } else {
        const w = Math.max(n.w, 160, longest + 30);
        const c = center(n);
        box = { x: c.x - w / 2, y: c.y - (rows * LINE) / 2 - 5, w, align: "center" };
      }
    }
    Object.assign(input.style, {
      left: `${box.x * z}px`, top: `${box.y * z}px`, width: `${box.w * z}px`,
      height: `${(rows * LINE + 10) * z}px`, textAlign: box.align,
    });
  }

  // target: {type: "node"|"edge", id, before?, created?}. A new text item left empty is dropped.
  // In a node, Enter starts a new line and Esc (or Ctrl+Enter, or clicking away) finishes; a
  // line's label finishes on Enter.
  function edit(target) {
    if (readOnly) return;
    finishEditing();
    const item = target.type === "node" ? nodeById(target.id) : edgeById(target.id);
    if (!item) return;
    const before = target.before ?? snapshot();
    const multiline = target.type === "node";
    input.value = item.label;
    input.classList.remove("hidden");
    placeInput(target);
    input.focus({ preventScroll: true });
    input.select();
    const finish = () => {
      if (editing !== finish) return;
      editing = null;
      input.oninput = input.onkeydown = input.onblur = null;
      input.classList.add("hidden");
      const value = input.value.replace(/\s+$/, "");
      if (target.type === "node" && item.kind === "text" && !value.trim()) {
        model.nodes = model.nodes.filter((n) => n.id !== item.id);
        model.edges = model.edges.filter((e) => e.from !== item.id && e.to !== item.id);
        sel.nodes.delete(item.id);
        if (target.created) { render(); } else { commit(before); changed(); }
      } else if (value !== item.label || target.created) {
        item.label = value;
        if (target.type === "node") { fitNode(item, measure); clampNode(item); }
        commit(before);
        changed();
      } else {
        renderOverlay();
      }
      canvas.focus({ preventScroll: true });
    };
    editing = finish;
    input.oninput = () => placeInput(target);
    input.onblur = finish;
    input.onkeydown = (ev) => {
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") return; // the page saves
      ev.stopPropagation();
      const done = ev.key === "Escape" || (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey))
        || (ev.key === "Enter" && !ev.shiftKey && !multiline);
      if (done) { ev.preventDefault(); finish(); }
    };
    renderOverlay();
  }
  function finishEditing() { if (editing) editing(); }

  // ----- zoom and pan
  function setZoom(value, anchor) {
    finishEditing();
    const z = Math.max(ZOOM.min, Math.min(ZOOM.max, Math.round(value * 100) / 100));
    const r = canvas.getBoundingClientRect();
    const ax = anchor ? anchor.clientX - r.left : canvas.clientWidth / 2;
    const ay = anchor ? anchor.clientY - r.top : canvas.clientHeight / 2;
    const px = (canvas.scrollLeft + ax) / zoom, py = (canvas.scrollTop + ay) / zoom;
    zoom = z;
    sizeSvg();
    canvas.scrollLeft = px * zoom - ax;
    canvas.scrollTop = py * zoom - ay;
  }
  function fit() {
    const b = boardBounds(model, 40);
    if (!b) { setZoom(1); canvas.scrollTo(0, 0); return; }
    setZoom(Math.min(1.5, canvas.clientWidth / b.w, canvas.clientHeight / b.h));
    canvas.scrollLeft = b.x * zoom - Math.max(0, (canvas.clientWidth - b.w * zoom) / 2);
    canvas.scrollTop = b.y * zoom - Math.max(0, (canvas.clientHeight - b.h * zoom) / 2);
  }

  // The rubber line while drawing: from a node's outline (or a point) to the pointer, or to the
  // outline of the node under it.
  function rubber(fromId, start, p, targetId) {
    const a = fromId ? nodeById(fromId) : null, b = targetId ? nodeById(targetId) : null;
    const pa = a ? center(a) : start, pb = b ? center(b) : p;
    const [x1, y1] = a ? boundary(a, pb.x, pb.y) : [pa.x, pa.y];
    const [x2, y2] = b ? boundary(b, pa.x, pa.y) : [pb.x, pb.y];
    return { x1, y1, x2, y2 };
  }

  // ----- pointer
  svg.addEventListener("pointerdown", (e) => {
    if (e.button === 1 || (e.button === 0 && spaceDown)) {
      e.preventDefault();
      drag = { kind: "pan", sx: e.clientX, sy: e.clientY, left: canvas.scrollLeft, top: canvas.scrollTop };
      root.classList.add("panning");
      svg.setPointerCapture(e.pointerId);
      return;
    }
    if (readOnly || e.button !== 0) return;
    finishEditing();
    canvas.focus({ preventScroll: true });
    const p = point(e);
    if (tool) {
      const from = nodeAt(p);
      drag = { kind: "draw", ends: TOOLS[tool].ends, from: from?.id ?? null, start: snapPoint(p), p, target: null, line: null };
      svg.setPointerCapture(e.pointerId);
      renderOverlay();
      return;
    }
    const endEl = e.target.closest("[data-line-end]");
    const link = e.target.closest("[data-link]");
    const resize = e.target.closest("[data-resize]");
    const edgeEl = endEl || link || resize ? null : e.target.closest("[data-edge]");
    const node = endEl || link || resize || edgeEl ? null : nodeAt(p);
    if (endEl) {
      drag = { kind: "end", id: only(sel.edges), which: endEl.dataset.lineEnd, before: snapshot(), target: null, moved: false };
    } else if (link) {
      drag = { kind: "link", from: link.dataset.link, start: p, ends: "end", line: null, target: null };
    } else if (resize) {
      const n = nodeById(resize.dataset.resize);
      drag = { kind: "resize", id: n.id, before: snapshot(), start: p, w: n.w, h: n.h, min: fitNode({ ...n, w: 0, h: 0 }, measure), moved: false };
    } else if (node || edgeEl) {
      const [set, id] = node ? [sel.nodes, node.id] : [sel.edges, edgeEl.dataset.edge];
      if (e.shiftKey) {
        if (set.has(id)) set.delete(id); else set.add(id);
      } else {
        if (!set.has(id)) { clearSel(); (node ? sel.nodes : sel.edges).add(id); }
        const items = movingNodes();
        drag = {
          kind: "move", click: { node: Boolean(node), id }, before: snapshot(), start: p, moved: false,
          items: items.map((n) => [n, n.x, n.y]), ends: movingEnds(),
        };
      }
    } else {
      if (!e.shiftKey) clearSel();
      drag = { kind: "marquee", start: p, box: null };
    }
    if (drag) svg.setPointerCapture(e.pointerId);
    renderOverlay();
  });

  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    if (drag.kind === "pan") {
      canvas.scrollLeft = drag.left - (e.clientX - drag.sx);
      canvas.scrollTop = drag.top - (e.clientY - drag.sy);
      return;
    }
    const p = point(e);
    if (drag.kind === "move") {
      const boxes = [
        ...drag.items.map(([n, x, y]) => ({ x, y, w: n.w, h: n.h })),
        ...drag.ends.map(([, , , x, y]) => ({ x, y, w: 0, h: 0 })),
      ];
      const b = bounds(boxes);
      if (!b) return;
      const dx = Math.max(-b.x, Math.min(CANVAS.w - b.x - b.w, snap(p.x - drag.start.x)));
      const dy = Math.max(-b.y, Math.min(CANVAS.h - b.y - b.h, snap(p.y - drag.start.y)));
      if (dx || dy || drag.moved) {
        for (const [n, x, y] of drag.items) { n.x = x + dx; n.y = y + dy; }
        for (const [edge, kx, ky, x, y] of drag.ends) { edge[kx] = x + dx; edge[ky] = y + dy; }
        drag.moved = true;
        render();
      }
    } else if (drag.kind === "resize") {
      const n = nodeById(drag.id);
      const w = Math.max(drag.min.w, Math.min(CANVAS.w - n.x, snap(drag.w + p.x - drag.start.x)));
      const h = Math.max(drag.min.h, Math.min(CANVAS.h - n.y, snap(drag.h + p.y - drag.start.y)));
      if (w !== n.w || h !== n.h) { n.w = w; n.h = h; drag.moved = true; render(); }
    } else if (drag.kind === "link" || drag.kind === "draw") {
      const over = nodeAt(p, drag.from);
      drag.p = p;
      drag.target = over?.id ?? null;
      drag.line = rubber(drag.from, drag.start, p, drag.target);
      renderOverlay();
    } else if (drag.kind === "end") {
      const edge = edgeById(drag.id);
      if (!edge) return;
      const other = drag.which === "from" ? edge.to : edge.from;
      drag.target = nodeAt(p, other)?.id ?? null;
      setEnd(edge, drag.which, snapPoint(p));
      drag.moved = true;
      render();
    } else if (drag.kind === "marquee") {
      const s = drag.start;
      drag.box = { x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) };
      renderOverlay();
    }
  });

  const endDrag = (e) => {
    if (!drag) return;
    const was = drag;
    drag = null;
    root.classList.remove("panning");
    if (was.kind === "move" || was.kind === "resize") {
      if (was.moved) {
        commit(was.before);
        changed();
      } else if (was.kind === "move" && sel.nodes.size + sel.edges.size > 1) {
        clearSel(); // a click (no drag) on one of several picks just that one
        (was.click.node ? sel.nodes : sel.edges).add(was.click.id);
        renderOverlay();
      }
    } else if (was.kind === "link" || was.kind === "draw") {
      const p = point(e);
      const target = nodeAt(p, was.from);
      const from = was.from ? { id: was.from } : was.start;
      const far = Math.hypot(p.x - was.start.x, p.y - was.start.y) > (was.kind === "link" ? 30 : 8);
      if (target) addEdge(from, { id: target.id }, was.ends);
      else if (far && !(was.from && hits(nodeById(was.from), p))) addEdge(from, snapPoint(p), was.ends);
      else { renderOverlay(); return; }
      if (was.kind === "draw") { tool = null; renderOverlay(); }
    } else if (was.kind === "end") {
      const edge = edgeById(was.id);
      if (was.moved && edge) {
        if (was.target) setEnd(edge, was.which, { id: was.target });
        commit(was.before);
        changed();
      } else {
        renderOverlay();
      }
    } else if (was.kind === "marquee") {
      const b = was.box;
      if (b && (b.w > 3 || b.h > 3)) {
        const within = (x, y) => x >= b.x && y >= b.y && x <= b.x + b.w && y <= b.y + b.h;
        for (const n of model.nodes) if (within(n.x, n.y) && within(n.x + n.w, n.y + n.h)) sel.nodes.add(n.id);
        const nodes = byId();
        for (const edge of model.edges) {
          const g = edgeGeometry(edge, nodes);
          if (within(g.x1, g.y1) && within(g.x2, g.y2)) sel.edges.add(edge.id);
        }
      }
      renderOverlay();
    }
  };
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);

  // By position, not e.target: after a drag the element under the pointer may have been redrawn.
  svg.addEventListener("dblclick", (e) => {
    if (readOnly || tool) return;
    const p = point(e);
    const node = nodeAt(p);
    const edge = node ? null : edgeAt(p);
    if (node && makesTextAt(node, p, framedIds(model.nodes).has(node.id))) addNode("text", { at: p });
    else if (node) edit({ type: "node", id: node.id });
    else if (edge) { clearSel(); sel.edges.add(edge.id); edit({ type: "edge", id: edge.id }); }
    else addNode("text", { at: p });
  });

  canvas.addEventListener("wheel", (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    setZoom(zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1), e);
  }, { passive: false });

  // ----- keys (only while the board itself has focus)
  canvas.addEventListener("keydown", (e) => {
    if (e.target !== canvas) return;
    const mod = e.ctrlKey || e.metaKey;
    const key = e.key.toLowerCase();
    if (e.key === " ") { spaceDown = true; root.classList.add("can-pan"); e.preventDefault(); return; }
    if (readOnly) return;
    if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); removeSelected(); }
    else if (e.key === "Escape") { tool = null; clearSel(); renderOverlay(); }
    else if ((e.key === "Enter" || e.key === "F2") && !mod) {
      e.preventDefault();
      if (sel.nodes.size === 1 && !sel.edges.size) edit({ type: "node", id: only(sel.nodes) });
      else if (sel.edges.size === 1 && !sel.nodes.size) edit({ type: "edge", id: only(sel.edges) });
    } else if (!mod && !e.altKey && Object.values(TOOLS).some((t) => t.key === key)) {
      e.preventDefault();
      setTool(Object.keys(TOOLS).find((k) => TOOLS[k].key === key));
    } else if (mod && key === "z") { e.preventDefault(); if (e.shiftKey) doRedo(); else doUndo(); }
    else if (mod && key === "y") { e.preventDefault(); doRedo(); }
    else if (mod && key === "a") {
      e.preventDefault();
      sel.nodes = new Set(model.nodes.map((n) => n.id));
      sel.edges = new Set(model.edges.map((x) => x.id));
      renderOverlay();
    } else if (mod && key === "d") { e.preventDefault(); pasteItems(selectedItems(), 2 * GRID, 2 * GRID); }
    else if (mod && key === "c") { if (sel.nodes.size || sel.edges.size) { clipboard = selectedItems(); e.preventDefault(); } }
    else if (mod && key === "v") { if (clipboard) { e.preventDefault(); pasteItems(clipboard, 3 * GRID, 3 * GRID); clipboard = selectedItems(); } }
    else if (e.key.startsWith("Arrow") && (sel.nodes.size || sel.edges.size)) {
      e.preventDefault();
      const step = e.shiftKey ? 5 * GRID : GRID;
      nudge({ ArrowLeft: -step, ArrowRight: step }[e.key] ?? 0, { ArrowUp: -step, ArrowDown: step }[e.key] ?? 0);
    }
  });
  const keyup = (e) => { if (e.key === " ") { spaceDown = false; root.classList.remove("can-pan"); } };
  window.addEventListener("keyup", keyup);
  window.addEventListener("blur", keyup);

  // ----- toolbar
  host.querySelectorAll("[data-add]").forEach((b) => { b.onclick = () => addNode(b.dataset.add); });
  host.querySelectorAll("[data-tool]").forEach((b) => { b.onclick = () => setTool(b.dataset.tool); });
  host.querySelectorAll("[data-ends]").forEach((b) => { b.onclick = () => setEdgeStyle({ ends: b.dataset.ends }); });
  q("[data-dash]").onclick = () => {
    const all = [...sel.edges].map(edgeById).filter(Boolean).every((x) => x.dash);
    setEdgeStyle({ dash: !all });
  };
  q("[data-delete]").onclick = removeSelected;
  q("[data-undo]").onclick = doUndo;
  q("[data-redo]").onclick = doRedo;
  host.querySelectorAll("[data-zoom]").forEach((b) => {
    b.onclick = () => setZoom(b.dataset.zoom === "in" ? zoom * ZOOM.step : b.dataset.zoom === "out" ? zoom / ZOOM.step : 1);
  });
  q("[data-fit]").onclick = fit;
  // Keep the toolbar's buttons from stealing focus from the board.
  q(".wb-toolbar").addEventListener("pointerdown", (e) => { if (e.target.closest("button")) e.preventDefault(); });

  sizeSvg();
  render();
  // Start where the work is.
  const start = boardBounds(model, 40);
  if (start) requestAnimationFrame(() => { canvas.scrollLeft = Math.max(0, start.x) * zoom; canvas.scrollTop = Math.max(0, start.y) * zoom; });

  return {
    getModel: () => { finishEditing(); return structuredClone(model); },
    focus: () => canvas.focus({ preventScroll: true }),
    setReadOnly(value) {
      readOnly = value;
      if (value) { finishEditing(); clearSel(); drag = null; tool = null; }
      root.classList.toggle("readonly", value);
      host.querySelectorAll(".wb-toolbar button").forEach((btn) => {
        if (!btn.dataset.zoom && !("fit" in btn.dataset)) btn.disabled = value;
      });
      renderOverlay();
    },
    dispose() {
      window.removeEventListener("keyup", keyup);
      window.removeEventListener("blur", keyup);
    },
  };
}
