// Long-form study pages: the foundations of a track (system design, algorithms) and the tech
// investigations. Each page has a table of contents; every section has a route of its own
// (#/design/learn/<page>/<section>, #/tech/<page>/<section>) so hints, explanations and other
// pages can link straight to it.

import { $app, api, esc, plural, topnav, renderMermaid } from "./common.js";
import { filesHref, projectTabs } from "./files.js";

const FOUNDATIONS_LEAD = "The concepts the questions build on, with diagrams.";

// base: the index of the pages. home: the track's own page; the tech pages have no other, so
// their index is their home and links back from it go to the site's home page.
const TRACKS = {
  design: {
    api: "/api/design/foundations", base: "#/design/learn", nav: "design", home: "#/design",
    label: "System design", index: "System design foundations", lead: FOUNDATIONS_LEAD,
  },
  algo: {
    api: "/api/algo/foundations", base: "#/algo/learn", nav: "algo", home: "#/algo",
    label: "Algorithms", index: "Algorithms foundations", lead: FOUNDATIONS_LEAD,
  },
  tech: {
    api: "/api/tech/pages", base: "#/tech", nav: "tech", home: "#/tech",
    label: "Tech investigations", index: "Tech investigations",
    lead: `One technology per guide, built around a small, complete project: the files, the choices
      behind them, and the interview questions they prepare you for.`,
  },
};

// The tech card on the home page.
export async function techTrackCard() {
  let pages = [];
  try {
    ({ pages } = await api("GET", TRACKS.tech.api));
  } catch { /* no pages: the card still links to the empty index */ }
  const titles = pages.map((p) => esc(p.title)).join(" · ");
  return `<a class="track-card" href="#/tech">
    <div class="track-head"><span class="track-mark tech">&#9881;</span><h2>Tech investigations</h2></div>
    <p>Deep dives into one technology at a time, each around a small project you can run.</p>
    <ul class="track-facts"><li>${plural(pages.length, "investigation")}</li><li>runnable code</li><li>untimed</li></ul>
    <div class="track-foot"><span class="faint">${titles || "None yet"}</span><span class="track-cta">Open →</span></div>
  </a>`;
}

// The "Foundations" block on a track's home page: one card per page.
export async function foundationsSection(track, intro) {
  const t = TRACKS[track];
  let pages = [];
  try {
    ({ pages } = await api("GET", t.api));
  } catch { return ""; }
  if (!pages.length) return "";
  const cards = pages.map((p, i) => `<a class="learn-card" href="${t.base}/${esc(p.slug)}">
      <span class="num">${i + 1}</span>
      <h3>${esc(p.title)}</h3>
      <p>${esc(p.summary)}</p>
      <span class="faint">${p.sections.length} sections</span>
    </a>`).join("");
  return `<h2 class="section-title">Foundations</h2>
    <p class="dim" style="margin:-4px 0 12px">${intro}</p>
    <div class="learn-grid">${cards}</div>`;
}

export async function renderLearn(track, slug, section) {
  const t = TRACKS[track];
  if (!slug) return renderIndex(t);
  const page = await api("GET", `${t.api}/${encodeURIComponent(slug)}`);
  const link = (id, title) => `<a href="${t.base}/${esc(page.slug)}/${esc(id)}" data-sec="${esc(id)}">${esc(title)}</a>`;
  const toc = page.toc.map((s) => `<li>${link(s.id, s.title)}${s.children.length
    ? `<ul>${s.children.map((c) => `<li>${link(c.id, c.title)}</li>`).join("")}</ul>` : ""}</li>`).join("");
  const pager = (p, dir) => (p ? `<a class="learn-nav ${dir}" href="${t.base}/${esc(p.slug)}">
      <span class="faint">${dir === "prev" ? "← Previous" : "Next →"}</span>${esc(p.title)}</a>` : "<span></span>");
  const crumbs = t.home === t.base
    ? `<a href="${t.base}">← ${t.index}</a>`
    : `<a href="${t.home}">← ${t.label}</a> · <a href="${t.base}">Foundations</a>`;

  $app.innerHTML = `${topnav(t.nav)}<main class="page learn-page">
    <div class="learn-layout">
      <aside class="learn-toc">
        <a class="faint" href="${t.base}">${t.index}</a>
        <h4>${esc(page.title)}</h4>
        <ul>${toc}</ul>
      </aside>
      <article class="learn-article">
        <p class="faint crumbs">${crumbs}</p>
        <h1>${esc(page.title)}</h1>
        ${projectTabs(page.slug, page.project, "guide")}
        <div class="md learn-body">${page.html}</div>
        <div class="learn-pager">${pager(page.prev, "prev")}${pager(page.next, "next")}</div>
      </article>
    </div>
  </main>`;

  const main = $app.querySelector(".learn-page");
  const article = main.querySelector(".learn-article");
  // A tech page's code captions (its ```include blocks) open the file in the file browser.
  if (page.project) {
    const folder = `${page.project.folder}/`;
    article.querySelectorAll(".code-file").forEach((el) => {
      const name = el.textContent;
      if (!name.startsWith(folder)) return;
      el.innerHTML = `<a href="${filesHref(page.slug, name.slice(folder.length))}"
        title="Open in the file browser">${esc(name)}</a>`;
    });
  }
  const sidebar = main.querySelector(".learn-toc");
  const tocLinks = [...sidebar.querySelectorAll("[data-sec]")];
  const mark = (id) => {
    tocLinks.forEach((a) => a.classList.toggle("active", a.dataset.sec === id));
    // On wide screens the sidebar scrolls on its own: keep the highlighted entry in view.
    const current = tocLinks.find((a) => a.dataset.sec === id);
    if (!current) return;
    const box = sidebar.getBoundingClientRect();
    const r = current.getBoundingClientRect();
    if (r.top < box.top || r.bottom > box.bottom) sidebar.scrollTop += r.top - box.top - box.height / 3;
  };
  const goto = (id, smooth) => {
    const el = id && document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
    mark(id);
  };

  // Links to a section of this page scroll instead of re-rendering it.
  const prefix = `${t.base}/${page.slug}/`;
  main.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    const href = a?.getAttribute("href") ?? "";
    const id = href.slice(prefix.length);
    if (!href.startsWith(prefix) || id === "files" || id.startsWith("files/")) return;
    e.preventDefault();
    history.pushState(null, "", href);
    goto(id, true);
  });

  // Highlight the section being read.
  const heads = [...article.querySelectorAll(".learn-body h2[id], .learn-body h3[id]")];
  const spy = new IntersectionObserver((entries) => {
    const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (visible.length) mark(visible[0].target.id);
  }, { rootMargin: "-70px 0px -70% 0px" });
  heads.forEach((h) => spy.observe(h));

  if (section) {
    requestAnimationFrame(() => goto(section, false));
    // Diagrams above the section change the layout as they draw; land on the section again.
    renderMermaid(article).then(() => goto(section, false));
  } else {
    window.scrollTo(0, 0);
  }
  return () => spy.disconnect();
}

async function renderIndex(t) {
  const { pages } = await api("GET", t.api);
  const items = pages.map((p, i) => `<section class="learn-index-item">
      <h2><span class="num">${i + 1}</span><a href="${t.base}/${esc(p.slug)}">${esc(p.title)}</a></h2>
      <p class="dim">${esc(p.summary)}</p>
      ${p.project ? `<p class="learn-files"><a href="${filesHref(p.slug)}">Browse the finished code</a>
        <span class="faint">· ${plural(p.project.files, "file")} in tech/${esc(p.project.folder)}/</span></p>` : ""}
      <ul class="learn-sections">${p.sections.map((s) =>
        `<li><a href="${t.base}/${esc(p.slug)}/${esc(s.id)}">${esc(s.title)}</a></li>`).join("")}</ul>
    </section>`).join("");
  const [backHref, backLabel] = t.home === t.base ? ["#/", "Home"] : [t.home, t.label];
  $app.innerHTML = `${topnav(t.nav)}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="${backHref}">← ${backLabel}</a></p>
    <h1>${t.index}</h1>
    <p class="lead">${t.lead}</p>
    ${items || '<p class="dim">No pages yet.</p>'}
  </main>`;
  window.scrollTo(0, 0);
  return undefined;
}
