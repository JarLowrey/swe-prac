// The whiteboard's data and geometry, with no DOM: whiteboard.js draws and edits it, the review
// page shows it, interviewer.js describes it to the AI, and tests/js/ checks it in Node.
//
// Model (saved with the session):
//   { nodes: [{id, kind, x, y, w, h, label}],
//     edges: [{id, from, to, x1, y1, x2, y2, label, ends, dash}] }
// A node is free text or a shape (box, circle, diamond) with text inside it. An edge is a line or
// an arrow. Each of its two ends is either attached to a node (from/to is the node's id) or loose
// at a point (from/to is null and x1,y1 / x2,y2 hold the point). ends is "end" (→), "both" (↔)
// or "none" (a plain line).
// Boards saved before the shapes were cut to four (entity, client, user, database, cache, queue,
// cloud, note) and the older diagram model still load: every old shape opens as a box, a cloud
// as a circle.

export const KINDS = {
  text: { name: "Text", w: 0, h: 0 },
  box: { name: "Box", w: 140, h: 60 },
  circle: { name: "Circle", w: 100, h: 100 },
  diamond: { name: "Diamond", w: 140, h: 90 },
};
const OLD_KINDS = { cloud: "circle" }; // anything else unknown opens as a box
export const EDGE_ENDS = ["end", "both", "none"];
export const CANVAS = { w: 4000, h: 3000 };
export const GRID = 10;
export const LINE = 18; // line height of every label
export const MAX_NODES = 600;
export const MAX_EDGES = 1200;
export const snap = (v) => Math.round(v / GRID) * GRID;

// ---------------------------------------------------------------- text sizes
// A label's lines; a "# " line is a heading (bold, drawn without the marker).
export const lines = (text) => String(text ?? "").split("\n");
export const isHeading = (line) => line.startsWith("# ");
export const shown = (line) => (isHeading(line) ? line.slice(2) : line);

// Width in pixels of one line at the label font. The page passes a canvas-based measure; this
// estimate is for Node (tests) and keeps sizes close enough to place things.
export function estimateWidth(line, bold = false) {
  let w = 0;
  for (const ch of line) w += /[ilj.,'|!:;]/.test(ch) ? 3.8 : /[mwMW@]/.test(ch) ? 11 : /[A-Z0-9]/.test(ch) ? 8.6 : 7.2;
  return w * (bold ? 1.06 : 1);
}

function widest(text, measure) {
  return Math.max(0, ...lines(text).map((l) => measure(shown(l), isHeading(l))));
}

// The smallest size that shows a node's whole label. Text is sized to its label; shapes only grow.
export function fitSize(node, measure = estimateWidth) {
  const n = lines(node.label).length;
  if (node.kind === "text") {
    return { w: Math.max(24, Math.ceil(widest(node.label, measure) + 10)), h: n * LINE + 8 };
  }
  // Round shapes need room around the text to keep it inside the outline.
  const roomy = { circle: 1.45, diamond: 1.8 }[node.kind] ?? 1;
  return {
    w: Math.ceil(widest(node.label, measure) * roomy + 24),
    h: Math.ceil(n * LINE * roomy + 16),
  };
}

// Grow (never shrink) a shape so its label fits; text always takes its fitted size.
export function fitNode(node, measure = estimateWidth) {
  const fit = fitSize(node, measure);
  if (node.kind === "text") {
    node.w = fit.w;
    node.h = fit.h;
  } else {
    node.w = Math.max(node.w, snap(fit.w + GRID / 2));
    node.h = Math.max(node.h, snap(fit.h + GRID / 2));
  }
  return node;
}

// ---------------------------------------------------------------- loading
const isNum = (v) => typeof v === "number" && Number.isFinite(v);

export function normalize(model) {
  const nodes = (Array.isArray(model?.nodes) ? model.nodes.filter((n) => n && n.id != null).slice(0, MAX_NODES) : [])
    .map((n) => {
      const kind = KINDS[n.kind] ? n.kind : OLD_KINDS[n.kind] ?? "box";
      return {
        id: String(n.id), kind, label: String(n.label ?? ""),
        x: Number(n.x) || 0, y: Number(n.y) || 0,
        w: Number(n.w) || KINDS[kind].w || 24, h: Number(n.h) || KINDS[kind].h || LINE + 8,
      };
    });
  const ids = new Set(nodes.map((n) => n.id));
  // One end: attached to a node that exists, or loose at a point; null when it's neither.
  const end = (id, x, y) => (id != null && ids.has(String(id)) ? { id: String(id) }
    : id == null && isNum(x) && isNum(y) ? { x, y } : null);
  const edges = [];
  for (const e of Array.isArray(model?.edges) ? model.edges : []) {
    if (!e || edges.length >= MAX_EDGES) continue;
    const a = end(e.from, e.x1, e.y1), b = end(e.to, e.x2, e.y2);
    if (!a || !b) continue;
    if (a.id && a.id === b.id) continue; // a node pointing at itself
    if (!a.id && !b.id && Math.hypot(a.x - b.x, a.y - b.y) < 4) continue; // a dot, not a line
    edges.push({
      id: String(e.id ?? `${e.from ?? "p"}-${e.to ?? "p"}-${edges.length}`),
      from: a.id ?? null, to: b.id ?? null,
      ...(a.id ? {} : { x1: a.x, y1: a.y }), ...(b.id ? {} : { x2: b.x, y2: b.y }),
      label: String(e.label ?? ""),
      ends: EDGE_ENDS.includes(e.ends) ? e.ends : "end",
      dash: Boolean(e.dash),
    });
  }
  return { nodes, edges };
}

export const isEmpty = (model) => !model?.nodes?.length && !model?.edges?.length;

// ---------------------------------------------------------------- geometry
export const area = (n) => n.w * n.h;
export const center = (n) => ({ x: n.x + n.w / 2, y: n.y + n.h / 2 });
export const inside = (inner, outer, slack = 2) => inner.x >= outer.x - slack && inner.y >= outer.y - slack
  && inner.x + inner.w <= outer.x + outer.w + slack && inner.y + inner.h <= outer.y + outer.h + slack;

// Where the line from n's center towards (tx, ty) crosses n's outline.
export function boundary(n, tx, ty) {
  const { x: cx, y: cy } = center(n);
  const dx = tx - cx, dy = ty - cy;
  if (!dx && !dy) return [cx, cy];
  const rx = n.w / 2 + (n.kind === "text" ? 4 : 0), ry = n.h / 2 + (n.kind === "text" ? 4 : 0);
  let t;
  if (n.kind === "circle") {
    t = 1 / Math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2);
  } else if (n.kind === "diamond") {
    t = 1 / (Math.abs(dx) / rx + Math.abs(dy) / ry);
  } else {
    t = Math.min(dx ? rx / Math.abs(dx) : Infinity, dy ? ry / Math.abs(dy) : Infinity);
  }
  return [cx + dx * t, cy + dy * t];
}

// The two drawn ends of an edge: on the attached nodes' outlines, or at its loose points.
export function edgeGeometry(e, byId) {
  const a = e.from != null ? byId.get(e.from) : null;
  const b = e.to != null ? byId.get(e.to) : null;
  const pa = a ? center(a) : { x: e.x1, y: e.y1 };
  const pb = b ? center(b) : { x: e.x2, y: e.y2 };
  const [x1, y1] = a ? boundary(a, pb.x, pb.y) : [pa.x, pa.y];
  const [x2, y2] = b ? boundary(b, pa.x, pa.y) : [pb.x, pb.y];
  return { x1, y1, x2, y2 };
}

// Drawing order: bigger shapes first, so whatever sits on top of a box stays visible; free text
// last. Hit testing walks it backwards.
export function paintOrder(nodes) {
  return nodes.map((n, i) => [n, i]).sort(([a, i], [b, j]) => {
    const ta = a.kind === "text", tb = b.kind === "text";
    if (ta !== tb) return ta ? 1 : -1;
    return area(b) - area(a) || i - j;
  }).map(([n]) => n);
}

// The smallest shape that holds n entirely (text never holds anything), or null.
export function containerOf(n, nodes) {
  let best = null;
  for (const c of nodes) {
    if (c === n || c.kind === "text" || area(c) <= area(n) || !inside(n, c)) continue;
    if (!best || area(c) < area(best)) best = c;
  }
  return best;
}

// Everything inside n, at any depth: these move with it.
export function contents(n, nodes) {
  return n.kind === "text" ? [] : nodes.filter((c) => c !== n && area(c) < area(n) && inside(c, n));
}

// Boxes that hold other items act as frames: their label moves to the top.
export function framedIds(nodes) {
  const ids = new Set();
  for (const n of nodes) {
    if (n.kind === "box" && nodes.some((c) => c !== n && area(c) < area(n) && inside(c, n))) ids.add(n.id);
  }
  return ids;
}

// The label's vertical band [top, bottom] inside a shape (framed: at the top).
export function labelBand(n, framed = false) {
  const h = lines(n.label).length * LINE;
  const top = framed ? n.y + 8 : n.y + n.h / 2 - h / 2;
  return [top, top + h];
}

// Does a double-click at p inside shape n start new text there (rather than edit n's label)?
// Only in a shape with room for at least three more lines, and away from its label.
export function makesTextAt(n, p, framed = false) {
  if (n.kind === "text" || n.h < (lines(n.label).length + 3) * LINE + 16) return false;
  const [top, bottom] = labelBand(n, framed);
  return p.y < top - 8 || p.y > bottom + 8;
}

// The rectangle around a list of {x, y, w, h}, or null for none.
export function bounds(boxes, pad = 0) {
  if (!boxes.length) return null;
  const x = Math.min(...boxes.map((n) => n.x)) - pad;
  const y = Math.min(...boxes.map((n) => n.y)) - pad;
  const x2 = Math.max(...boxes.map((n) => n.x + n.w)) + pad;
  const y2 = Math.max(...boxes.map((n) => n.y + n.h)) + pad;
  return { x, y, w: x2 - x, h: y2 - y };
}

// Everything drawn: the nodes and the loose ends of lines.
export function boardBounds(model, pad = 0) {
  const boxes = [...model.nodes];
  for (const e of model.edges) {
    if (e.from == null) boxes.push({ x: e.x1, y: e.y1, w: 0, h: 0 });
    if (e.to == null) boxes.push({ x: e.x2, y: e.y2, w: 0, h: 0 });
  }
  return bounds(boxes, pad);
}

// ---------------------------------------------------------------- the board as text
// What the AI interviewer reads: each shape and text block, nested under the shape it sits in,
// top to bottom, then every line and arrow.
const ARROW = { end: "→", both: "↔", none: "—" };

function quoted(label) {
  const text = lines(label).map(shown).join(" / ").trim();
  return text ? `"${text.length > 60 ? `${text.slice(0, 57)}…` : text}"` : "(no label)";
}

export function boardText(raw) {
  const model = normalize(raw);
  if (isEmpty(model)) return "(The board is empty.)";
  const parent = new Map(model.nodes.map((n) => [n.id, containerOf(n, model.nodes)?.id ?? null]));
  const byTopLeft = (a, b) => a.y - b.y || a.x - b.x;
  const children = (id) => model.nodes.filter((n) => parent.get(n.id) === id).sort(byTopLeft);
  const out = [];
  const walk = (id, depth) => {
    for (const n of children(id)) {
      const pad = "  ".repeat(depth);
      const [first, ...rest] = lines(n.label).map(shown);
      out.push(`${pad}- ${KINDS[n.kind].name}: ${first || "(no label)"}`);
      for (const line of rest) out.push(`${pad}    ${line}`);
      walk(n.id, depth + 1);
    }
  };
  walk(null, 0);
  if (model.edges.length) {
    const byId = new Map(model.nodes.map((n) => [n.id, n]));
    const name = (id) => (id == null ? "(loose end)" : `${KINDS[byId.get(id).kind].name} ${quoted(byId.get(id).label)}`);
    if (out.length) out.push("");
    out.push("Lines and arrows:");
    for (const e of model.edges) {
      out.push(`- ${name(e.from)} ${ARROW[e.ends]} ${name(e.to)}${e.label ? `: ${lines(e.label).join(" ")}` : ""}${e.dash ? " (dashed)" : ""}`);
    }
  }
  return out.join("\n");
}
