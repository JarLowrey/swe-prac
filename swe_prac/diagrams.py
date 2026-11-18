"""Data-structure diagrams for the study pages: small fenced blocks rendered to inline SVG.

Markdown like

    ```array
    values: 2 7 11 15
    pointers: lo=0 hi=3
    ```

becomes an <svg class="ds"> styled by styles.css (.ds-*), so it matches the app and works on the
static site without JavaScript. Flowcharts and sequence diagrams use ```mermaid blocks instead,
rendered in the browser. The block syntax is documented in docs/writing-content.md.

Every block is a list of `key: value` lines. Several frames (before/after, step 1/step 2) can be
drawn in one block by separating them with a line containing only `---`.
"""

from __future__ import annotations

import html
import math
import re

KINDS = ("array", "tree", "linkedlist", "grid", "intervals", "ring")
_BLOCK = re.compile(
    r'<pre><code class="language-(' + "|".join(KINDS) + r')">(.*?)</code></pre>', re.S
)

CHAR_W = 8.2  # monospace 13px, roughly
FONT_H = 13


class DiagramError(ValueError):
    pass


# -- parsing -----------------------------------------------------------------------------
def _frames(text: str) -> list[list[str]]:
    frames, cur = [], []
    for raw in text.strip("\n").splitlines():
        if raw.strip() == "---":
            frames.append(cur)
            cur = []
        else:
            cur.append(raw.rstrip())
    frames.append(cur)
    return [f for f in frames if any(line.strip() for line in f)]


# The keys each kind of block reads. Every kind also takes `caption`; a grid's other lines are
# its rows. (An intervals block is free-form: one `name: [a,b] ...` row per line.)
_KEYS = {
    "array": {"values", "pointers", "highlight", "dim", "label", "indices", "direction"},
    "linkedlist": {"values", "pointers", "highlight", "dim", "label", "cycle", "null"},
    "tree": {"values", "highlight", "dim"},
    "grid": {"highlight", "dim", "path", "rowlabels", "collabels"},
    "ring": {"nodes", "keys", "highlight"},
}


def _fields(lines: list[str], kind: str) -> dict[str, str | list[str]]:
    """`key: value` lines into a dict; a grid's lines without a key go to "rows". An unknown key
    is an error, so a misspelt one (`hightlight:`) doesn't vanish or become a grid row."""
    known = _KEYS[kind] | {"caption"}
    out: dict = {}
    for line in lines:
        if not line.strip():
            continue
        m = re.match(r"^\s*([a-z][a-z-]*)\s*:\s?(.*)$", line)
        if m and m.group(1) in known:
            out[m.group(1)] = m.group(2).strip()
        elif m:
            keys = ", ".join(sorted(known))
            raise DiagramError(f"{kind} has no key {m.group(1)!r}; its keys are {keys}")
        elif kind == "grid":
            out.setdefault("rows", []).append(line.strip())
        else:
            raise DiagramError(f"expected `key: value`, got {line.strip()!r}")
    return out


def _tokens(value: str) -> list[str]:
    """Space-separated tokens; "quoted strings" may contain spaces; _ is an empty cell."""
    toks = [a or b for a, b in re.findall(r'"([^"]*)"|(\S+)', value or "")]
    return ["" if t == "_" else t for t in toks]


def _indices(value: str, n: int) -> set[int]:
    """`0 2 4..6` -> {0, 2, 4, 5, 6}; negative indices count from the end."""
    out = set()
    for tok in _tokens(value):
        m = re.fullmatch(r"(-?\d+)\.\.(-?\d+)", tok)
        if m:
            a, b = (int(x) % n if n else 0 for x in m.groups())
            out.update(range(min(a, b), max(a, b) + 1))
        elif re.fullmatch(r"-?\d+", tok):
            out.add(int(tok) % n if n else 0)
        else:
            raise DiagramError(f"not an index or range: {tok!r}")
    return out


def _pointers(value: str, n: int) -> dict[int, list[str]]:
    """`lo=0 hi=-1` -> {0: ["lo"], n-1: ["hi"]}."""
    out: dict[int, list[str]] = {}
    for tok in _tokens(value):
        m = re.fullmatch(r"([^=]+)=(-?\d+)", tok)
        if not m:
            raise DiagramError(f"pointer must be name=index, got {tok!r}")
        idx = int(m.group(2))
        if not -n <= idx <= n:  # n itself is allowed: a pointer just past the end
            raise DiagramError(f"pointer {tok!r} is outside -{n}..{n}")
        out.setdefault(idx % n if idx < 0 else idx, []).append(m.group(1))
    return out


# -- svg helpers -------------------------------------------------------------------------
def _esc(text) -> str:
    return html.escape(str(text), quote=True)


def _text(x, y, s, cls, anchor="middle", extra=""):
    return (
        f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'dominant-baseline="central"{extra}>{_esc(s)}</text>'
    )


def _svg(width: float, height: float, body: list[str], kind: str) -> str:
    w, h = math.ceil(width), math.ceil(height)
    return (
        f'<svg class="ds ds-kind-{kind}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" xmlns="http://www.w3.org/2000/svg"><defs>{_MARKERS}</defs>'
        + "".join(body)
        + "</svg>"
    )


# One arrowhead per colour: markers can't inherit the line's colour everywhere yet.
_MARKERS = "".join(
    f'<marker id="ds-arrow{suffix}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
    f'markerHeight="7" orient="auto-start-reverse"><path class="ds-arrowhead{suffix}" '
    'd="M0 0 L10 5 L0 10 z"/></marker>'
    for suffix in ("", "-ptr", "-path")
)


def _text_w(s: str) -> float:
    return len(str(s)) * CHAR_W


def _label_w(label: str) -> float:
    """Width of the label column left of an array or list (0 without a label)."""
    return _text_w(label) + 14 if label else 0


def _val_cls(dimmed: bool) -> str:
    return "ds-val dim" if dimmed else "ds-val"


def _caption(body: list[str], y: float, width: float, caption: str) -> float:
    """Draw a caption line centred at y; returns the height used."""
    if not caption:
        return 0
    body.append(_text(width / 2, y + 10, caption, "ds-cap"))
    return 24


# -- array -------------------------------------------------------------------------------
def _array_frame(f: dict, y0: float, label_col: float = 0) -> tuple[list[str], float, float]:
    values = _tokens(f.get("values", ""))
    if not values:
        raise DiagramError("array needs `values:`")
    n = len(values)
    hl = _indices(f.get("highlight", ""), n)
    dim = _indices(f.get("dim", ""), n)
    ptrs = _pointers(f.get("pointers", ""), n)
    show_idx = f.get("indices", "true").lower() != "false"
    vertical = f.get("direction", "").lower() == "vertical"
    label = f.get("label", "")
    cell_w = max(40, max(_text_w(v) for v in values) + 18)
    cell_h = 38
    body: list[str] = []
    label_w = max(label_col, _label_w(label))

    if vertical:  # a stack: index 0 at the bottom, the top of the stack drawn first
        ptr_w = max((_text_w(" ".join(p)) for p in ptrs.values()), default=0)
        x0 = 8 + label_w
        top = y0 + 6
        for k in range(n):
            i = n - 1 - k
            y = top + k * cell_h
            cls = "ds-cell" + (" hl" if i in hl else "") + (" dim" if i in dim else "")
            body.append(
                f'<rect class="{cls}" x="{x0:.1f}" y="{y:.1f}" width="{cell_w:.1f}" '
                f'height="{cell_h}" rx="3"/>'
            )
            body.append(_text(x0 + cell_w / 2, y + cell_h / 2, values[i], _val_cls(i in dim)))
            if i in ptrs:
                px = x0 + cell_w + 10
                body.append(
                    f'<line class="ds-ptr-line" x1="{px + 26:.1f}" y1="{y + cell_h / 2:.1f}" '
                    f'x2="{px + 2:.1f}" y2="{y + cell_h / 2:.1f}" marker-end="url(#ds-arrow-ptr)"/>'
                )
                body.append(_text(px + 32, y + cell_h / 2, " ".join(ptrs[i]), "ds-ptr", "start"))
        if label:
            body.append(_text(8, top + n * cell_h / 2, label, "ds-label", "start"))
        width = x0 + cell_w + (ptr_w + 50 if ptrs else 8)
        return body, width, n * cell_h + 14

    ptr_rows = max((len(p) for p in ptrs.values()), default=0)
    top = y0 + (ptr_rows * 16 + 22 if ptrs else 4)
    x0 = 8 + label_w
    for i, v in enumerate(values):
        x = x0 + i * cell_w
        cls = "ds-cell" + (" hl" if i in hl else "") + (" dim" if i in dim else "")
        body.append(
            f'<rect class="{cls}" x="{x:.1f}" y="{top:.1f}" width="{cell_w:.1f}" '
            f'height="{cell_h}" rx="3"/>'
        )
        body.append(_text(x + cell_w / 2, top + cell_h / 2, v, _val_cls(i in dim)))
        if show_idx:
            body.append(_text(x + cell_w / 2, top + cell_h + 11, i, "ds-idx"))
    for i, names in ptrs.items():
        cx = x0 + i * cell_w + cell_w / 2
        for k, name in enumerate(names):
            body.append(_text(cx, top - 22 - (len(names) - 1 - k) * 16, name, "ds-ptr"))
        body.append(
            f'<line class="ds-ptr-line" x1="{cx:.1f}" y1="{top - 14:.1f}" x2="{cx:.1f}" '
            f'y2="{top - 2:.1f}" marker-end="url(#ds-arrow-ptr)"/>'
        )
    if label:
        body.append(_text(8, top + cell_h / 2, label, "ds-label", "start"))
    width = x0 + n * cell_w + 8
    if n in ptrs:  # a pointer one past the end
        width += cell_w
    height = top - y0 + cell_h + (22 if show_idx else 8)
    return body, width, height


# -- tree --------------------------------------------------------------------------------
def _parse_tree(values: list[str]):
    """Level-order values (null or - for missing) into nested [value, left, right] lists."""
    if not values or values[0] in ("null", "-", "None"):
        return None
    root = [values[0], None, None]
    queue, i = [root], 1
    while queue and i < len(values):
        node = queue.pop(0)
        for side in (1, 2):
            if i < len(values) and values[i] not in ("null", "-", "None"):
                child = [values[i], None, None]
                node[side] = child
                queue.append(child)
            i += 1
    return root


def _tree_frame(f: dict, y0: float) -> tuple[list[str], float, float]:
    root = _parse_tree(_tokens(f.get("values", "")))
    hl = set(_tokens(f.get("highlight", "")))
    dim = set(_tokens(f.get("dim", "")))
    r = max(17, max((_text_w(v) for v in _tokens(f.get("values", ""))), default=0) / 2 + 7)
    gap_x, gap_y = 2 * r + 12, 62
    placed = []  # (x_index, depth, value, parent_ref)
    order = [0]

    def walk(node, depth, parent):
        if node is None:
            return
        walk(node[1], depth + 1, node)
        node.append((order[0], depth))
        order[0] += 1
        placed.append(node)
        walk(node[2], depth + 1, node)

    walk(root, 0, None)
    body: list[str] = []
    if not placed:
        body.append(_text(40, y0 + 20, "(empty tree)", "ds-cap"))
        return body, 120, 44

    def pos(node):
        xi, d = node[3]
        return 10 + r + xi * gap_x, y0 + 10 + r + d * gap_y

    for node in placed:
        x1, y1 = pos(node)
        for child in (node[1], node[2]):
            if child is None:
                continue
            x2, y2 = pos(child)
            dx, dy = x2 - x1, y2 - y1
            dist = math.hypot(dx, dy)
            ux, uy = dx / dist, dy / dist
            body.append(
                f'<line class="ds-edge" x1="{x1 + ux * r:.1f}" y1="{y1 + uy * r:.1f}" '
                f'x2="{x2 - ux * r:.1f}" y2="{y2 - uy * r:.1f}"/>'
            )
    for node in placed:
        x, y = pos(node)
        cls = "ds-node" + (" hl" if node[0] in hl else "") + (" dim" if node[0] in dim else "")
        body.append(f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>')
        body.append(_text(x, y, node[0], _val_cls(node[0] in dim)))
    depth = max(n[3][1] for n in placed)
    width = 20 + 2 * r + (len(placed) - 1) * gap_x
    return body, width, 20 + 2 * r + depth * gap_y


# -- linked list -------------------------------------------------------------------------
def _list_frame(f: dict, y0: float, label_col: float = 0) -> tuple[list[str], float, float]:
    values = _tokens(f.get("values", ""))
    n = len(values)
    hl = _indices(f.get("highlight", ""), n) if n else set()
    dim = _indices(f.get("dim", ""), n) if n else set()
    ptrs = _pointers(f.get("pointers", ""), n)
    cycle = f.get("cycle", "").strip()
    show_null = f.get("null", "true").lower() != "false" and not cycle
    label = f.get("label", "")
    box_w = max(44, max((_text_w(v) for v in values), default=0) + 20)
    box_h, gap = 36, 34
    ptr_rows = max((len(p) for p in ptrs.values()), default=0)
    top = y0 + (ptr_rows * 16 + 22 if ptrs else 4)
    x0 = 8 + max(label_col, _label_w(label))
    body: list[str] = []
    for i, v in enumerate(values):
        x = x0 + i * (box_w + gap)
        cls = "ds-cell" + (" hl" if i in hl else "") + (" dim" if i in dim else "")
        body.append(
            f'<rect class="{cls}" x="{x:.1f}" y="{top:.1f}" width="{box_w:.1f}" '
            f'height="{box_h}" rx="5"/>'
        )
        body.append(_text(x + box_w / 2, top + box_h / 2, v, _val_cls(i in dim)))
        if i < n - 1 or show_null:
            body.append(
                f'<line class="ds-edge" x1="{x + box_w:.1f}" y1="{top + box_h / 2:.1f}" '
                f'x2="{x + box_w + gap - 2:.1f}" y2="{top + box_h / 2:.1f}" '
                'marker-end="url(#ds-arrow)"/>'
            )
    end_x = x0 + n * (box_w + gap)
    if show_null:
        body.append(_text(end_x + 14, top + box_h / 2, "None", "ds-null", "start"))
    extra_h = 0
    if cycle and n:
        j = int(cycle) % n
        xa = x0 + (n - 1) * (box_w + gap) + box_w / 2
        xb = x0 + j * (box_w + gap) + box_w / 2
        yb = top + box_h
        body.append(
            f'<path class="ds-edge" d="M{xa:.1f} {yb:.1f} C{xa:.1f} {yb + 40:.1f} '
            f'{xb:.1f} {yb + 40:.1f} {xb:.1f} {yb + 3:.1f}" fill="none" '
            'marker-end="url(#ds-arrow)"/>'
        )
        extra_h = 40
    for i, names in ptrs.items():
        cx = x0 + i * (box_w + gap) + box_w / 2
        for k, name in enumerate(names):
            body.append(_text(cx, top - 22 - (len(names) - 1 - k) * 16, name, "ds-ptr"))
        body.append(
            f'<line class="ds-ptr-line" x1="{cx:.1f}" y1="{top - 14:.1f}" x2="{cx:.1f}" '
            f'y2="{top - 2:.1f}" marker-end="url(#ds-arrow-ptr)"/>'
        )
    if label:
        body.append(_text(8, top + box_h / 2, label, "ds-label", "start"))
    width = end_x + (60 if show_null else 8)
    return body, width, top - y0 + box_h + 12 + extra_h


# -- grid --------------------------------------------------------------------------------
def _cells(value: str) -> list[tuple[int, int]]:
    out = []
    for tok in _tokens(value):
        m = re.fullmatch(r"(\d+),(\d+)", tok)
        if not m:
            raise DiagramError(f"cell must be row,col, got {tok!r}")
        out.append((int(m.group(1)), int(m.group(2))))
    return out


def _grid_frame(f: dict, y0: float) -> tuple[list[str], float, float]:
    rows = [_tokens(line) for line in f.get("rows", [])]
    if not rows:
        raise DiagramError("grid needs at least one row of values")
    ncol = max(len(r) for r in rows)
    rowlabels = _tokens(f.get("rowlabels", ""))
    collabels = _tokens(f.get("collabels", ""))
    hl = set(_cells(f.get("highlight", "")))
    dim = set(_cells(f.get("dim", "")))
    path = _cells(f.get("path", ""))
    flat = [v for r in rows for v in r]
    cell = max(34, max((_text_w(v) for v in flat), default=0) + 16)
    lab_w = max((_text_w(v) for v in rowlabels), default=0) + (14 if rowlabels else 0)
    x0, top = 8 + lab_w, y0 + (22 if collabels else 4)
    body: list[str] = []
    texts: list[str] = []
    for c, lab in enumerate(collabels[:ncol]):
        body.append(_text(x0 + c * cell + cell / 2, top - 11, lab, "ds-idx"))
    for r, row in enumerate(rows):
        if r < len(rowlabels):
            body.append(_text(x0 - 8, top + r * cell + cell / 2, rowlabels[r], "ds-idx", "end"))
        for c in range(ncol):
            v = row[c] if c < len(row) else ""
            cls = "ds-cell" + (" hl" if (r, c) in hl else "") + (" dim" if (r, c) in dim else "")
            x, y = x0 + c * cell, top + r * cell
            body.append(
                f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" '
                f'height="{cell:.1f}"/>'
            )
            texts.append(_text(x + cell / 2, y + cell / 2, v, _val_cls((r, c) in dim)))
    if len(path) > 1:
        pts = " ".join(
            f"{x0 + c * cell + cell / 2:.1f},{top + r * cell + cell / 2:.1f}" for r, c in path
        )
        body.append(f'<polyline class="ds-path" points="{pts}" marker-end="url(#ds-arrow-path)"/>')
    body += texts  # values above the path
    return body, x0 + ncol * cell + 8, top - y0 + len(rows) * cell + 8


# -- intervals ---------------------------------------------------------------------------
def _intervals_frame(lines: list[str], y0: float) -> tuple[list[str], float, float]:
    rows: list[tuple[str, list[tuple[float, float]]]] = []
    caption = ""
    for line in lines:
        if not line.strip():
            continue
        m = re.match(r"^\s*([^:]+?)\s*:\s*(.*)$", line)
        name, rest = (m.group(1), m.group(2)) if m else ("", line)
        if name == "caption":
            caption = rest
            continue
        spans = [
            (float(a), float(b))
            for a, b in re.findall(r"\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", rest)
        ]
        if not spans:
            raise DiagramError(f"intervals row needs [start,end] pairs: {line.strip()!r}")
        rows.append((name, spans))
    if not rows:
        raise DiagramError("intervals needs at least one row")
    lo = min(a for _, sp in rows for a, _ in sp)
    hi = max(b for _, sp in rows for _, b in sp)
    if hi == lo:
        hi = lo + 1
    lab_w = max(_text_w(n) for n, _ in rows) + 16
    scale_w = max(360.0, min(640.0, (hi - lo) * 36))
    x0 = 10 + lab_w

    def X(v):
        return x0 + (v - lo) / (hi - lo) * scale_w

    body: list[str] = []
    lane_h, row_gap = 28, 10
    y = y0 + 8
    for k, (name, spans) in enumerate(rows):
        # Spans that overlap or touch go to separate lanes so none hides another.
        lanes: list[float] = []  # end of the last span in each lane
        placed = []
        for a, b in spans:
            lane = next((i for i, end in enumerate(lanes) if end < a), None)
            if lane is None:
                lanes.append(b)
                lane = len(lanes) - 1
            else:
                lanes[lane] = b
            placed.append((a, b, lane))
        body.append(_text(x0 - 10, y + 11, name, "ds-label", "end"))
        hot = " hl" if k == len(rows) - 1 and len(rows) > 1 else ""
        for a, b, lane in placed:
            yy = y + lane * lane_h
            body.append(
                f'<rect class="ds-bar{hot}" x="{X(a):.1f}" y="{yy:.1f}" '
                f'width="{max(3.0, X(b) - X(a)):.1f}" height="22" rx="4"/>'
            )
            label = f"[{_num(a)},{_num(b)}]"
            if X(b) - X(a) >= _text_w(label) + 6:
                body.append(_text((X(a) + X(b)) / 2, yy + 11, label, "ds-bar-text"))
            else:
                body.append(_text(X(b) + 5, yy + 11, label, "ds-bar-text", "start"))
        y += len(lanes) * lane_h + row_gap
    axis_y = y
    body.append(
        f'<line class="ds-axis" x1="{x0:.1f}" y1="{axis_y:.1f}" x2="{x0 + scale_w:.1f}" '
        f'y2="{axis_y:.1f}"/>'
    )
    step = _nice_step(hi - lo)
    t = math.ceil(lo / step) * step
    while t <= hi + 1e-9:
        body.append(
            f'<line class="ds-axis" x1="{X(t):.1f}" y1="{axis_y:.1f}" x2="{X(t):.1f}" '
            f'y2="{axis_y + 5:.1f}"/>'
        )
        body.append(_text(X(t), axis_y + 15, _num(t), "ds-idx"))
        t += step
    height = axis_y - y0 + 26
    width = x0 + scale_w + 16
    height += _caption(body, y0 + height, width, caption)
    return body, width, height


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _nice_step(span: float) -> float:
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if span / step <= 16:
            return step
    return 10 ** math.ceil(math.log10(span / 10))


# -- consistent-hashing ring -------------------------------------------------------------
def _ring_frame(f: dict, y0: float) -> tuple[list[str], float, float]:
    def items(value):
        out = []
        for tok in _tokens(value):
            m = re.fullmatch(r"(.+)@(-?\d+(?:\.\d+)?)", tok)
            if not m:
                raise DiagramError(f"ring items are name@degrees, got {tok!r}")
            out.append((m.group(1), float(m.group(2)) % 360))
        return out

    nodes = items(f.get("nodes", ""))
    keys = items(f.get("keys", ""))
    if not nodes:
        raise DiagramError("ring needs `nodes:`")
    hl = set(_tokens(f.get("highlight", "")))
    R, cx = 110, 190
    cy = y0 + 150

    def pt(deg, rad=R):
        a = math.radians(deg)
        return cx + rad * math.sin(a), cy - rad * math.cos(a)

    body = [f'<circle class="ds-ring" cx="{cx}" cy="{cy:.1f}" r="{R}"/>']
    ordered = sorted(nodes, key=lambda n: n[1])
    for name, deg in keys:
        owner = next((n for n in ordered if n[1] >= deg), ordered[0])
        sweep = (owner[1] - deg) % 360
        x1, y1 = pt(deg)
        x2, y2 = pt(owner[1])
        large = 1 if sweep > 180 else 0
        if sweep > 0:
            body.append(
                f'<path class="ds-ring-walk" d="M{x1:.1f} {y1:.1f} A{R} {R} 0 {large} 1 '
                f'{x2:.1f} {y2:.1f}"/>'
            )
        kx, ky = pt(deg)
        body.append(
            f'<rect class="ds-key" x="{kx - 5:.1f}" y="{ky - 5:.1f}" '
            'width="10" height="10" rx="2"/>'
        )
        lx, ly = pt(deg, R - 26)
        body.append(_text(lx, ly, name, "ds-idx"))
    for name, deg in nodes:
        x, y = pt(deg)
        cls = "ds-node" + (" hl" if name in hl else "")
        body.append(f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="15"/>')
        body.append(_text(x, y, name, "ds-val"))
    return body, 380, 300


# -- entry points ------------------------------------------------------------------------
def render(kind: str, text: str) -> str:
    """One fenced block (unescaped text) to an SVG string. Raises DiagramError on bad input."""
    if kind not in KINDS:
        raise DiagramError(f"unknown diagram kind {kind!r}")
    body: list[str] = []
    width, y = 0.0, 0.0
    frames = _frames(text)
    if not frames:
        raise DiagramError(f"empty {kind} block")
    fields = [None if kind == "intervals" else _fields(lines, kind) for lines in frames]
    # The frames of a block share one label column, so a frame without a label lines up with
    # the labelled ones.
    label_col = max((_label_w(f.get("label", "")) for f in fields if f), default=0)
    for k, (lines, f) in enumerate(zip(frames, fields, strict=True)):
        if k:
            y += 10
            sep_y = y - 5
            body.append(
                f'<line class="ds-sep" x1="8" y1="{sep_y:.1f}" x2="2000" y2="{sep_y:.1f}"/>'
            )
        if kind == "intervals":
            part, w, h = _intervals_frame(lines, y)
            caption = ""
        elif kind in ("array", "linkedlist"):
            draw = _array_frame if kind == "array" else _list_frame
            part, w, h = draw(f, y, label_col)
            caption = f.get("caption", "")
        else:
            draw = {"tree": _tree_frame, "grid": _grid_frame, "ring": _ring_frame}[kind]
            part, w, h = draw(f, y)
            caption = f.get("caption", "")
        body += part
        width = max(width, w)
        y += h
        if caption:
            y += _caption(body, y, max(w, _text_w(caption) + 20), caption) or 0
            width = max(width, _text_w(caption) + 20)
    return _svg(width, y + 4, body, kind)


def render_blocks(html_text: str) -> str:
    """Replace the data-structure code blocks in rendered markdown with SVG figures."""

    def repl(m):
        kind, raw = m.group(1), html.unescape(m.group(2))
        try:
            svg = render(kind, raw)
        except (DiagramError, ValueError, IndexError) as exc:
            return (
                f'<div class="diagram-error"><strong>Diagram error ({_esc(kind)}):</strong> '
                f"{_esc(exc)}<pre>{_esc(raw)}</pre></div>"
            )
        return f'<figure class="ds-figure">{svg}</figure>'

    return _BLOCK.sub(repl, html_text)
