// Foundations: the long-form study pages of a track (system design). Each page has a
// table of contents; every section has a route of its own (#/design/learn/<page>/<section>) so
// hints, explanations and other pages can link straight to it.

import { $app, api, esc, topnav, renderMermaid } from "./common.js";

const TRACKS = {
  design: {
    api: "/api/design/foundations", base: "#/design/learn", nav: "design", home: "#/design",
    label: "System design",
  },
};

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

  $app.innerHTML = `${topnav(t.nav)}<main class="page learn-page">
    <div class="learn-layout">
      <aside class="learn-toc">
        <a class="faint" href="${t.base}">${t.label} foundations</a>
        <h4>${esc(page.title)}</h4>
        <ul>${toc}</ul>
      </aside>
      <article class="learn-article">
        <p class="faint crumbs"><a href="${t.home}">← ${t.label}</a> · <a href="${t.base}">Foundations</a></p>
        <h1>${esc(page.title)}</h1>
        <div class="md learn-body">${page.html}</div>
        <div class="learn-pager">${pager(page.prev, "prev")}${pager(page.next, "next")}</div>
      </article>
    </div>
  </main>`;

  const main = $app.querySelector(".learn-page");
  const article = main.querySelector(".learn-article");
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
    if (!href.startsWith(prefix)) return;
    e.preventDefault();
    history.pushState(null, "", href);
    goto(href.slice(prefix.length), true);
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
      <ul class="learn-sections">${p.sections.map((s) =>
        `<li><a href="${t.base}/${esc(p.slug)}/${esc(s.id)}">${esc(s.title)}</a></li>`).join("")}</ul>
    </section>`).join("");
  $app.innerHTML = `${topnav(t.nav)}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="${t.home}">← ${t.label}</a></p>
    <h1>${t.label} foundations</h1>
    <p class="lead">The concepts the questions build on, with diagrams. Read a page end to end, or jump
      to a section from a hint or an explanation.</p>
    ${items || '<p class="dim">No foundations pages yet.</p>'}
  </main>`;
  window.scrollTo(0, 0);
  return undefined;
}
