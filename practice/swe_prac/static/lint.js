// Lint and Format with ruff, compiled to WebAssembly (vendor/ruff), on the page itself: a check
// of a solution takes a few milliseconds. The settings come from swe_prac/user_ruff.toml and
// user_ruff_algo.toml, merged into data.json by tools/build_static.py.
//
// lint() answers in the shape the pages show: {issues: [{code, message, row, col, end_row,
// end_col, fixable}], error}, with 1-based rows and columns (UTF-16, as the editor counts).
import init, { PositionEncoding, Workspace } from "./vendor/ruff/ruff_wasm.js";

let loading = null;
const workspaces = new Map(); // settings JSON -> Workspace

// Load the WebAssembly module (about 10 MB the first time, then from the browser's cache).
// `source` is for Node, which passes the module's bytes.
export function warmUp(source) {
  loading ??= init({ module_or_path: source ?? new URL("./vendor/ruff/ruff_wasm_bg.wasm", import.meta.url) });
  loading.catch(() => { loading = null; });
  return loading;
}

async function workspace(settings) {
  await warmUp();
  const key = JSON.stringify(settings);
  if (!workspaces.has(key)) workspaces.set(key, new Workspace(settings, PositionEncoding.Utf16));
  return workspaces.get(key);
}

export async function lint(code, settings) {
  const ws = await workspace(settings);
  const issues = ws.check(code).map((d) => ({
    code: d.code ?? "syntax",
    message: d.message,
    row: d.start_location.row,
    col: d.start_location.column,
    end_row: d.end_location.row,
    end_col: d.end_location.column,
    fixable: d.fix != null,
  }));
  issues.sort((a, b) => a.row - b.row || a.col - b.col);
  return { issues, error: null };
}

// {code} with the file formatted, or {code: null, error} when it can't be parsed.
export async function format(code, settings) {
  const ws = await workspace(settings);
  try {
    return { code: ws.format(code), error: null };
  } catch (err) {
    return { code: null, error: String(err?.message ?? err) };
  }
}
