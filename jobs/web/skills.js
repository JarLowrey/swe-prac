// The Claude skills page: how to install the job-search skills once, then one card per skill with
// what it does, what it needs before you start, the details to fill in and the prompt to copy into
// Claude Code. The page never runs a skill itself: Claude Code does, on your computer, with your
// Claude plan and your own browser.

import { NEEDS, SKILLS, skill } from "./prompts.js";
import { py } from "./python.js";
import { allMessages, getKV } from "./store.js";
import { bindCopy, copyBlock, esc, fmtFull, mount, topnav } from "./ui.js";

const SOURCE = "https://github.com/JarLowrey/swe-prac/tree/master/jobs/job-search";
const values = Object.fromEntries(SKILLS.map((s) => [s.id, {}])); // what you typed, kept while the page is open

const INSTALL_WIN = `Expand-Archive "$HOME\\Downloads\\job-search.zip" "$HOME"
cd "$HOME\\job-search"
mkdir reference; copy examples\\reference\\profile.yaml reference\\
claude`;
const INSTALL_UNIX = `unzip ~/Downloads/job-search.zip -d ~
cd ~/job-search
mkdir -p reference && cp examples/reference/profile.yaml reference/
claude`;

function setupSection() {
  return `<section class="panel">
    <h2>Before the first one: install the skills</h2>
    <ol class="setup-steps">
      <li><strong>Install Claude Code</strong> and sign in (<code>/login</code>) with your Claude account. See
        <a href="https://code.claude.com/docs/en/overview" target="_blank" rel="noopener">code.claude.com</a>.</li>
      <li><strong>Download <a href="job-search.zip" download>job-search.zip</a></strong>: the skills, a profile template,
        and fake examples of every file they read and write. Unzip it into your home folder, copy the profile template,
        and start Claude Code there (the skills load from the folder):
        <div class="two-col">
          <div><div class="sub-label">Windows (PowerShell)</div>${copyBlock(INSTALL_WIN)}</div>
          <div><div class="sub-label">macOS or Linux</div>${copyBlock(INSTALL_UNIX)}</div>
        </div></li>
      <li><strong>Fill in <code>reference/profile.yaml</code></strong>: who you are, the locations you'd work in,
        your target roles, work authorization and the voluntary self-ID answers (<code>decline</code> is always fine).
        Put your resume PDF in <code>reference/</code>, with a brag doc, stories and project write-ups to draft answers
        from. The skills won't fill a form while the profile still has the example's values.</li>
      <li><strong>For the skills that use a browser</strong> (filling applications, finding contacts), connect Claude in
        Chrome: <span class="dim">${esc(NEEDS.chrome[1])}</span></li>
    </ol>
    <p class="dim small">Everything personal stays in your job-search folder (<code>reference/</code>,
      <code>applications/</code> and <code>tracker.csv</code>), which the kit's .gitignore keeps out of git. To use the
      skills from any folder, the kit's README shows how to link them into <code>~/.claude/skills</code>.
      Source: <a href="${SOURCE}" target="_blank" rel="noopener">jobs/job-search</a>.</p>
  </section>`;
}

function field(s, f, apps) {
  const v = values[s.id][f.id] ?? "";
  const id = `${s.id}-${f.id}`;
  if (f.kind === "app") {
    const opts = apps.map((a) => `<option value="${esc(a.key)}" ${values[s.id].app === a.key ? "selected" : ""}>${esc(a.company)} · ${esc(a.position || "position not stated")} · ${esc(a.status)}</option>`);
    return `<label class="field" for="${id}"><span>${esc(f.label)}</span>
      <select id="${id}" data-field="${f.id}" ${apps.length ? "" : "disabled"}>
        <option value="">${apps.length ? "None: type the company below" : "No applications yet (see Tracker)"}</option>${opts.join("")}
      </select></label>`;
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
  const missing = { "job-apply": "Add at least one job link.", "job-answers": "Add at least one question.",
    "job-contacts": "Add the company.", "interview-prep": "Pick an application or add the company." }[s.id];
  return `<div class="sub-label">Prompt for Claude Code</div>
    ${text ? copyBlock(text, "prompt") : `<div class="empty-prompt">${esc(missing)}</div>`}
    ${v.contextNote ? `<p class="dim small">${esc(v.contextNote)}</p>` : ""}
    ${batch ? `<div class="sub-label">Several links? Run them as a batch from the job-search folder instead</div>
      ${copyBlock(batch)}
      <p class="dim small">The script runs each step (read, fill, contacts, log) as its own short agent, one at a time
        because they share your Chrome, and checks the file each step leaves before moving on. Re-running skips what's done.</p>` : ""}`;
}

function card(s, apps) {
  return `<article class="skill-card" id="skill-${s.id}" data-skill="${s.id}">
    <header><h2>${esc(s.title)}</h2><code class="skill-name">/${s.id}</code></header>
    <p>${esc(s.does)}</p>
    <div class="sub-label">Before you start</div>
    <ul class="needs">${s.needs.map((k) => `<li><strong>${esc(NEEDS[k][0])}</strong><span>${esc(NEEDS[k][1])}</span></li>`).join("")}</ul>
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
    v.contextNote = "Includes the applications and the newest emails at this company, with sender addresses removed. Read it before you paste it.";
  } catch (err) {
    v.context = "";
    v.contextNote = `Couldn't read the emails: ${err.message}`;
  }
}

// focus: a skill id to scroll to. params (from the tracker's links): company, role, and app (an
// application's key, which interview-prep reads the emails for).
export async function renderSkills(focus, params = new URLSearchParams()) {
  const apps = (await getKV("apps", [])) ?? [];
  const target = skill(focus);
  if (target) {
    for (const f of ["company", "role"]) {
      if (params.has(f) && target.fields.some((x) => x.id === f)) values[target.id][f] = params.get(f);
    }
    const appKey = params.get("app");
    if (target.id === "interview-prep" && appKey && apps.some((a) => a.key === appKey)) await pickApp(appKey, apps);
  }
  const root = mount(`${topnav("skills")}<main class="page jobs">
    <h1>Claude skills for the job search</h1>
    <p class="lead">Four Claude Code skills that do the busywork of applying. This page doesn't run them: fill in the
      details, copy the prompt and paste it into Claude Code, which runs the skill on your computer, with your Claude
      plan and, for forms and LinkedIn, your own Chrome. Nothing is submitted or sent for you.</p>
    ${setupSection()}
    <div class="skill-list">${SKILLS.map((s) => card(s, apps)).join("")}</div>
    <section class="panel">
      <h2>Ground rules the skills follow</h2>
      <ul class="rules">
        <li>They never click the final Submit button, and never tick terms, privacy-policy or attestation boxes. You do those.</li>
        <li>They never send LinkedIn requests or messages.</li>
        <li>When your profile or resume doesn't answer a question, they leave it blank and list it for you instead of guessing.</li>
        <li>Questions with an anti-AI instruction ("start your answer with the word kiwi") get a draft, but you type those in yourself.</li>
        <li>Written answers use only facts from your own material, and keep employer-confidential detail out.</li>
      </ul>
    </section>
  </main>`);
  bindCopy(root);

  const refresh = (s) => { root.querySelector(`[data-skill="${s.id}"] .prompt-area`).innerHTML = promptArea(s); };
  root.addEventListener("input", (e) => {
    const el = e.target.closest("[data-field]");
    const s = skill(el?.closest("[data-skill]")?.dataset.skill);
    if (!s || el.tagName === "SELECT") return;
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
