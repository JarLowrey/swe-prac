// The file browser of a tech investigation (#/tech/<page>/files/<path>): the finished project as
// a folder tree, and the chosen file in full with line numbers, its colours and links to the
// sections of the guide that explain it. The server lists the files (tech_api.project), so the
// code here is the code in the repo.

import { $app, api, esc, plural, toast, topnav } from "./common.js";

// The Guide | Files tabs under an investigation's title, on both of its pages.
export function projectTabs(slug, project, active) {
  if (!project) return "";
  const tab = (key, href, label) => `<a class="project-tab${key === active ? " active" : ""}" href="${href}"
      ${key === active ? 'aria-current="page"' : ""}>${label}</a>`;
  return `<nav class="project-tabs" aria-label="Investigation">
      ${tab("guide", `#/tech/${esc(slug)}`, "Guide")}
      ${tab("files", filesHref(slug), `Files <span class="faint">${project.files}</span>`)}
    </nav>`;
}

// Each path segment is encoded on its own, so the slashes stay readable in the address bar.
export function filesHref(slug, path = "") {
  const tail = path ? `/${path.split("/").map(encodeURIComponent).join("/")}` : "";
  return `#/tech/${esc(slug)}/files${esc(tail)}`;
}

function decodePath(raw) {
  try {
    return raw ? raw.split("/").map(decodeURIComponent).join("/") : "";
  } catch {
    return raw; // a malformed %-escape: shown as "no such file"
  }
}

// Folders first, then files, each A to Z ignoring case, as editors list them.
const byName = (a, b) => a.localeCompare(b, undefined, { sensitivity: "base" });

function buildTree(files) {
  const root = { dirs: new Map(), files: [] };
  for (const file of files) {
    const parts = file.path.split("/");
    let node = root;
    for (const dir of parts.slice(0, -1)) {
      if (!node.dirs.has(dir)) node.dirs.set(dir, { dirs: new Map(), files: [] });
      node = node.dirs.get(dir);
    }
    node.files.push({ name: parts.at(-1), file });
  }
  return root;
}

function treeHtml(slug, node) {
  const dirs = [...node.dirs.keys()].sort(byName).map((name) => `<li>
      <details open><summary>${esc(name)}</summary>${treeHtml(slug, node.dirs.get(name))}</details>
    </li>`);
  const files = node.files.sort((a, b) => byName(a.name, b.name)).map(({ name, file }) =>
    `<li><a href="${filesHref(slug, file.path)}" data-path="${esc(file.path)}" title="${esc(file.path)}">${esc(name)}</a></li>`);
  return `<ul>${dirs.join("")}${files.join("")}</ul>`;
}

const kb = (bytes) => (bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`);

function viewHtml(slug, folder, file) {
  const parts = file.path.split("/");
  const crumbs = `<span class="faint">${esc(folder)}/</span>${parts.slice(0, -1).map((p) => `${esc(p)}/`).join("")}<strong>${esc(parts.at(-1))}</strong>`;
  const guide = file.sections.length
    ? `<p class="file-guide">Explained in the guide: ${file.sections.map((s) =>
        `<a href="#/tech/${esc(slug)}/${esc(s.id)}">${esc(s.title)}</a>`).join(" · ")}</p>`
    : "";
  if (file.text === null) {
    return `<div class="file-head"><div class="file-path mono">${crumbs}</div><span class="faint">${kb(file.size)}</span></div>
      ${guide}<div class="callout info">${esc(file.note)} Open it in your editor: <span class="mono">tech/${esc(folder)}/${esc(file.path)}</span></div>`;
  }
  // The colorizer (common.js) drops a final newline too, so the numbers match its lines.
  const body = file.text.replace(/\n$/, "");
  const lines = body.split("\n").length;
  const numbers = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
  const code = file.lang ? `<code class="language-${esc(file.lang)}">` : "<code>";
  return `<div class="file-head">
      <div class="file-path mono">${crumbs}</div>
      <span class="faint">${plural(lines, "line")} · ${kb(file.size)}</span>
      <button class="small" data-copy>Copy</button>
    </div>
    ${guide}
    <div class="code-view"><pre class="gutter" aria-hidden="true">${numbers}</pre><pre class="code">${code}${esc(body)}</code></pre></div>`;
}

// The file to open when the address names none: the project's README, else the first file.
function defaultFile(files) {
  return files.find((f) => f.path.toLowerCase() === "readme.md") ?? files[0];
}

export async function renderFiles(slug, rawPath) {
  const project = await api("GET", `/api/tech/pages/${encodeURIComponent(slug)}/files`);
  const byPath = new Map(project.files.map((f) => [f.path, f]));
  const info = { folder: project.folder, files: project.files.length };

  $app.innerHTML = `${topnav("tech")}<main class="page files-page">
    <p class="faint crumbs"><a href="#/tech">← Tech investigations</a></p>
    <h1>${esc(project.title)}</h1>
    ${projectTabs(slug, info, "files")}
    <p class="dim files-lead">The finished project in <span class="mono">tech/${esc(project.folder)}/</span>.
      Its README says how to run it.</p>
    <div class="files-layout">
      <nav class="file-tree" aria-label="Files">${treeHtml(slug, buildTree(project.files))}</nav>
      <section class="file-view" aria-live="polite"></section>
    </div>
  </main>`;

  const main = $app.querySelector(".files-page");
  const tree = main.querySelector(".file-tree");
  const view = main.querySelector(".file-view");
  let current = null;

  const show = (path) => {
    const file = byPath.get(path) ?? (path ? null : defaultFile(project.files));
    current = file;
    tree.querySelectorAll("a[data-path]").forEach((a) => {
      const active = a.dataset.path === file?.path;
      a.classList.toggle("active", active);
      if (active) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    view.innerHTML = file
      ? viewHtml(slug, project.folder, file)
      : `<div class="callout bad">There's no file <span class="mono">${esc(path)}</span> in this project.</div>`;
    // Keep the chosen file visible in a long tree.
    tree.querySelector("a.active")?.scrollIntoView({ block: "nearest" });
  };

  // Opening a file swaps the view in place, so the tree keeps its folders and scroll position;
  // back and forward come through the router as usual.
  tree.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-path]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    history.pushState(null, "", a.getAttribute("href"));
    show(a.dataset.path);
    if (view.getBoundingClientRect().top < 0) view.scrollIntoView({ block: "start" });
  });
  view.addEventListener("click", async (e) => {
    if (!e.target.closest("[data-copy]") || current?.text == null) return;
    try {
      await navigator.clipboard.writeText(current.text);
      toast(`Copied ${current.path.split("/").at(-1)}`, "good");
    } catch {
      toast("Couldn't copy: clipboard blocked", "bad");
    }
  });

  show(decodePath(rawPath));
  window.scrollTo(0, 0);
  return undefined;
}
