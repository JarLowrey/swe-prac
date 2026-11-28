// Small helpers shared by the Jobs pages.

const $app = document.getElementById("app");

// Each page renders into a fresh wrapper and binds its listeners there, so they go with it.
export function mount(html) {
  $app.innerHTML = `<div class="view">${html}</div>`;
  return $app.firstElementChild;
}

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Only links that are plainly https:// become hrefs (mail and settings are never markup).
export const safeUrl = (u) => (/^https:\/\/[^\s"'<>]+$/i.test(String(u || "")) ? String(u) : "");

export function toast(message, kind = "") {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

export function topnav(active) {
  const link = (key, href, label) => `<a href="${href}" class="${active === key ? "active" : ""}">${label}</a>`;
  return `<header class="topnav">
    <a class="brand" href="../"><span class="brand-mark">&lt;/&gt;</span>SWE Practice</a>
    <nav>
      ${link("tracker", "#/", "Tracker")}
      ${link("finder", "#/finder", "Job finder")}
      ${link("skills", "#/skills", "AI skills")}
      ${link("gmail", "#/gmail", "Connect Gmail")}
      ${link("open", "#/open", "Open jobs")}
    </nav>
    <span class="nav-spacer"></span>
    <a class="nav-out" href="../practice/">Interview practice →</a>
    <a class="nav-icon" href="https://github.com/JarLowrey/swe-prac" target="_blank" rel="noopener" title="Source on GitHub" aria-label="Source on GitHub"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg></a>
  </header>`;
}

// Copy to the clipboard; if the browser refuses, select the text so Ctrl+C works.
export async function copyText(text, button, selectEl) {
  const label = button.textContent;
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
  } catch {
    if (selectEl) {
      const range = document.createRange();
      range.selectNodeContents(selectEl);
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }
    button.textContent = "Selected: press Ctrl+C";
  }
  setTimeout(() => { button.textContent = label; }, 1800);
}

// A block of text with a Copy button. Bind once per page with bindCopy().
export const copyBlock = (text, cls = "") =>
  `<div class="copy-block ${cls}"><pre>${esc(text)}</pre><button class="small" data-copy>Copy</button></div>`;

export function bindCopy(root) {
  root.addEventListener("click", (e) => {
    const b = e.target.closest("[data-copy]");
    if (!b) return;
    const pre = b.closest(".copy-block").querySelector("pre");
    copyText(pre.textContent, b, pre);
  });
}

// Dates are UTC days (YYYY-MM-DD), as job_tracker.py writes them; shown in the reader's locale.
export function dayOf(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || "");
  return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
}
export const fmtDay = (s) => dayOf(s)?.toLocaleDateString(undefined, { month: "short", day: "numeric" }) ?? "";
export const fmtFull = (s) => dayOf(s)?.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) ?? "";
export function ago(s) {
  const d = dayOf(s);
  if (!d) return "";
  const t = new Date();
  t.setHours(0, 0, 0, 0);
  const n = Math.round((t - d) / 86400000);
  return n <= 0 ? "today" : n === 1 ? "1 day ago" : `${n} days ago`;
}
export const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
