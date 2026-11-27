// The AI skills page: your profile (saved in this browser, and written into the kit you download
// as reference/profile.yaml), one "Before you start" list, then a card per skill with the details
// to fill in and the prompt to copy into your AI agent. The page never runs a skill: the agent
// does, on your computer, with your own browser.

import { GROUPS, FIELDS, initial, missing, profileYaml } from "./profile.js";
import { SKILLS, skill } from "./prompts.js";
import { py } from "./python.js";
import { allMessages, getKV, setKV } from "./store.js";
import { bindCopy, copyBlock, esc, fmtFull, mount, toast, topnav } from "./ui.js";
import { addFile } from "./zip.js";

const SOURCE = "https://github.com/JarLowrey/swe-prac/tree/master/jobs/job-search";
const values = Object.fromEntries(SKILLS.map((s) => [s.id, {}])); // what you typed, kept while the page is open
const link = (href, text) => `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;

const INSTALL_WIN = `Expand-Archive "$HOME\\Downloads\\job-search.zip" "$HOME"
cd "$HOME\\job-search"`;
const INSTALL_UNIX = `unzip ~/Downloads/job-search.zip -d ~
cd ~/job-search`;

// ---------------------------------------------------------------- profile

function profileField(f, p) {
  const id = `pf-${f.key.replace(/\W/g, "-")}`;
  const v = p[f.key] ?? initial(f);
  const attrs = `id="${id}" data-pf="${esc(f.key)}"${f.required ? ' aria-required="true"' : ""}`;
  if (f.kind === "check") {
    return `<label class="check"><input type="checkbox" ${attrs} ${v === true ? "checked" : ""}>${esc(f.label)}</label>`;
  }
  const ph = `placeholder="${esc(f.placeholder ?? "")}"`;
  const control = f.kind === "select"
    ? `<select ${attrs}>${f.options.map(([o, l]) => `<option value="${esc(o)}" ${o === v ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`
    : f.kind === "list" || f.kind === "docs"
      ? `<textarea ${attrs} rows="3" ${ph}>${esc(v)}</textarea>`
      : `<input type="text" ${attrs} value="${esc(v)}" ${ph} autocomplete="${f.auto ?? "off"}"${f.url ? ' spellcheck="false"' : ""}>`;
  return `<label class="field${f.wide ? " wide" : ""}" for="${id}">
    <span>${esc(f.label)}${f.required ? ' <b class="req" aria-hidden="true">*</b>' : ""}</span>${control}
    ${f.hint ? `<small class="dim">${esc(f.hint)}</small>` : ""}</label>`;
}

function profileGroups(p) {
  return GROUPS.map((g) => {
    const grid = `<div class="profile-grid">${g.fields.map((f) => profileField(f, p)).join("")}</div>`;
    return g.collapsed
      ? `<details class="profile-group"><summary>${esc(g.title)} <span class="dim small">${esc(g.note)}</span></summary>${grid}</details>`
      : `<fieldset class="profile-group"><legend>${esc(g.title)}</legend>${grid}</fieldset>`;
  }).join("");
}

const missingNote = (p) => {
  const m = missing(p);
  return m.length ? `Blank, so you'll be asked: ${m.join(", ")}.` : "All required fields are filled in.";
};

function profileSection(p) {
  return `<section class="panel" id="profile">
    <h2>Your profile</h2>
    <p class="dim small">Used to fill in applications. <b class="req">*</b> Required.</p>
    <div class="profile-form">${profileGroups(p)}</div>
    <div class="actions">
      <button class="primary" data-download>Download job-search.zip</button>
      <button data-clear-profile>Clear</button>
    </div>
    <p class="dim small" id="profile-missing">${esc(missingNote(p))}</p>
  </section>`;
}

// Fetch the kit the site built, add your profile to it, and hand it to the browser to save.
async function downloadKit(p, button) {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Building…";
  try {
    const res = await fetch("job-search.zip", { cache: "no-cache" });
    if (!res.ok) throw new Error(`the kit didn't load (HTTP ${res.status})`);
    const zip = addFile(new Uint8Array(await res.arrayBuffer()), "job-search/reference/profile.yaml", profileYaml(p));
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([zip], { type: "application/zip" }));
    a.download = "job-search.zip";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
  } catch (err) {
    toast(`Couldn't build the download: ${err.message}`, "bad");
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
}

function beforeSection() {
  return `<section class="panel">
    <h2>Before you start</h2>
    <ol class="setup-steps">
      <li><strong>Fill in your profile and download the kit.</strong></li>
      <li><strong>Unzip it and start your AI agent there.</strong> Any agent that runs skills (SKILL.md) works.
        <div class="two-col">
          <div><div class="sub-label">Windows (PowerShell)</div>${copyBlock(INSTALL_WIN)}</div>
          <div><div class="sub-label">macOS or Linux</div>${copyBlock(INSTALL_UNIX)}</div>
        </div></li>
      <li><strong>Put your resume and docs in <code>reference/</code>.</strong> The skills use only facts from there:
        <ul class="doc-list">
          <li><strong>Brag doc</strong>: your wins, with numbers.</li>
          <li><strong>Career summary</strong>: each role and its projects.</li>
          <li><strong>Behavioral stories</strong>: situation, action, result.</li>
          <li><strong>Project write-ups</strong>: the problem, your part, the outcome.</li>
        </ul>
        Markdown, PDF, .txt or .docx; see <code>examples/reference/</code>.</li>
      <li><strong>For skills that use Chrome</strong>, connect your agent to Chrome and sign in to LinkedIn and the
        job sites there.</li>
    </ol>
  </section>`;
}

// ---------------------------------------------------------------- skill cards

function field(s, f, apps) {
  const v = values[s.id][f.id] ?? "";
  const id = `${s.id}-${f.id}`;
  if (f.kind === "app") {
    const opts = apps.map((a) => `<option value="${esc(a.key)}" ${values[s.id].app === a.key ? "selected" : ""}>${esc(a.company)} · ${esc(a.position || "position not stated")} · ${esc(a.status)}</option>`);
    return `<label class="field" for="${id}"><span>${esc(f.label)}</span>
      <select id="${id}" data-field="${f.id}" ${apps.length ? "" : "disabled"}>
        <option value="">${apps.length ? "None" : "No applications yet"}</option>${opts.join("")}
      </select></label>`;
  }
  if (f.kind === "select") {
    const cur = v || f.options[0][0];
    return `<label class="field" for="${id}"><span>${esc(f.label)}</span><select id="${id}" data-field="${f.id}">
      ${f.options.map(([o, l]) => `<option value="${esc(o)}" ${o === cur ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`;
  }
  const input = f.kind === "textarea"
    ? `<textarea id="${id}" data-field="${f.id}" rows="4" placeholder="${esc(f.placeholder)}">${esc(v)}</textarea>`
    : `<input id="${id}" data-field="${f.id}" type="text" value="${esc(v)}" placeholder="${esc(f.placeholder)}">`;
  return `<label class="field" for="${id}"><span>${esc(f.label)}</span>${input}</label>`;
}

function promptArea(s) {
  const v = values[s.id];
  const text = s.prompt(v);
  const batch = s.batch?.(v) || "";
  const missingText = { "job-apply": "Add at least one job link.", "job-answers": "Add at least one question.",
    "job-contacts": "Add the company.", "interview-prep": "Pick an application or add the company." }[s.id];
  return `<div class="sub-label">Prompt</div>
    ${text ? copyBlock(text, "prompt") : `<div class="empty-prompt">${esc(missingText)}</div>`}
    ${v.contextNote ? `<p class="dim small">${esc(v.contextNote)}</p>` : ""}
    ${s.after ? `<p class="dim small">${s.after}</p>` : ""}
    ${batch ? `<div class="sub-label">Or run them as a batch, from the job-search folder</div>
      ${copyBlock(batch)}
      <p class="dim small">Each step runs as its own agent. Set <code>JOB_SEARCH_AGENT</code> first (see the kit's README). Re-running skips finished steps.</p>` : ""}`;
}

function card(s, apps) {
  return `<article class="skill-card" id="skill-${s.id}" data-skill="${s.id}">
    <header><h2>${esc(s.title)}</h2>${s.browser ? '<span class="chip">Uses Chrome</span>' : ""}<code class="skill-name">/${s.id}</code></header>
    <p>${esc(s.does)}</p>
    <div class="fields">${s.fields.map((f) => field(s, f, apps)).join("")}</div>
    <div class="prompt-area">${promptArea(s)}</div>
  </article>`;
}

// Picking an application fills the company and role, and adds what the emails say (prep_context).
async function pickApp(key, apps) {
  const v = values["interview-prep"];
  v.app = key;
  const a = apps.find((x) => x.key === key);
  if (!a) {
    Object.assign(v, { context: "", status: "", lastDate: "", contextNote: "" });
    return;
  }
  Object.assign(v, { company: a.company, role: a.position || "", status: a.status, lastDate: fmtFull(a.last_date),
    contextNote: "Reading your emails for this company…" });
  const same = apps.filter((x) => x.company === a.company);
  try {
    v.context = await py("prep_context", { applications: same, messages: await allMessages() });
    v.contextNote = "Adds your latest emails from this company, without addresses. Check it before you paste it.";
  } catch (err) {
    v.context = "";
    v.contextNote = `Couldn't read the emails: ${err.message}`;
  }
}

// focus: a skill id to scroll to. params (from the tracker's and Job finder's links): company, role,
// links (job-apply), and app (an application's key, which interview-prep reads the emails for).
export async function renderSkills(focus, params = new URLSearchParams()) {
  const apps = (await getKV("apps", [])) ?? [];
  const profile = { ...((await getKV("profile", {})) ?? {}) };
  const target = skill(focus);
  if (target) {
    for (const f of ["company", "role", "links"]) {
      if (params.has(f) && target.fields.some((x) => x.id === f)) values[target.id][f] = params.get(f);
    }
    const appKey = params.get("app");
    if (target.id === "interview-prep" && appKey && apps.some((a) => a.key === appKey)) await pickApp(appKey, apps);
  }
  const root = mount(`${topnav("skills")}<main class="page jobs">
    <div class="privacy-banner" role="note">
      <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
      <div><strong>Your profile stays in this browser.</strong> It only goes into the zip you download.</div>
    </div>

    <h1>AI skills</h1>
    <p class="lead">Skills your AI agent runs on your computer. Copy a prompt into it; nothing is submitted or sent for you.</p>
    ${profileSection(profile)}
    ${beforeSection()}
    <div class="skill-list">${SKILLS.map((s) => card(s, apps)).join("")}</div>
    <section class="panel">
      <h2>What the skills never do</h2>
      <ul class="rules">
        <li>Click Submit, or accept terms, privacy policies or attestations.</li>
        <li>Send LinkedIn requests or messages.</li>
        <li>Guess. A question your profile doesn't answer is left blank and listed for you.</li>
        <li>Type answers to questions with anti-AI instructions. They draft those, and you enter them.</li>
        <li>Use facts that aren't in your own docs, or employer-confidential detail.</li>
      </ul>
      <p class="dim small">Your files stay in the job-search folder, out of git. Source: ${link(SOURCE, "jobs/job-search")}.</p>
    </section>
  </main>`);
  bindCopy(root);

  // Profile: saved as you type, a moment after you stop.
  const missingEl = root.querySelector("#profile-missing");
  let timer = null;
  const save = () => setKV("profile", profile).catch((err) => toast(`Couldn't save your profile: ${err.message}`, "bad"));
  const saveSoon = () => { clearTimeout(timer); timer = setTimeout(save, 300); };
  const formEl = root.querySelector(".profile-form");
  formEl.addEventListener("input", (e) => {
    const el = e.target.closest("[data-pf]");
    if (!el) return;
    profile[el.dataset.pf] = el.type === "checkbox" ? el.checked : el.value;
    missingEl.textContent = missingNote(profile);
    saveSoon();
  });
  root.querySelector("[data-download]").onclick = (e) => {
    clearTimeout(timer);
    save();
    downloadKit(profile, e.currentTarget);
  };
  root.querySelector("[data-clear-profile]").onclick = async () => {
    if (!confirm("Clear your profile from this browser?")) return;
    clearTimeout(timer);
    for (const f of FIELDS) delete profile[f.key];
    await setKV("profile", {});
    formEl.innerHTML = profileGroups(profile);
    missingEl.textContent = missingNote(profile);
  };

  // Skill cards
  const refresh = (s) => { root.querySelector(`[data-skill="${s.id}"] .prompt-area`).innerHTML = promptArea(s); };
  root.querySelector(".skill-list").addEventListener("input", (e) => {
    const el = e.target.closest("[data-field]");
    const s = skill(el?.closest("[data-skill]")?.dataset.skill);
    if (!s || el.dataset.field === "app") return; // the application picker is handled on change
    values[s.id][el.dataset.field] = el.value;
    refresh(s);
  });
  root.addEventListener("change", async (e) => {
    const el = e.target.closest('select[data-field="app"]');
    if (!el) return;
    const s = skill("interview-prep");
    const pending = pickApp(el.value, apps);
    refresh(s);
    await pending;
    for (const f of ["company", "role"]) {
      const input = root.querySelector(`#interview-prep-${f}`);
      if (input) input.value = values[s.id][f] ?? "";
    }
    refresh(s);
  });
  if (target) {
    const el = root.querySelector(`#skill-${target.id}`);
    el.classList.add("focus");
    el.scrollIntoView({ block: "start" });
  } else {
    scrollTo(0, 0);
  }
}
