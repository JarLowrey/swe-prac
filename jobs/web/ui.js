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
