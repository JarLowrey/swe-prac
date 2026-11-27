// Connect Gmail: the one-time Google Cloud setup (each visitor makes their own OAuth client, so
// nobody's mail passes through anyone else's app), the client ID box, the tracker's settings, and
// your data in this browser (export, import, delete).

import { prepare } from "./gmail.js";
import { clearAll, countMessages, exportAll, getKV, importAll, setKV } from "./store.js";
import { bindCopy, copyBlock, esc, isoDay, mount, plural, toast, topnav } from "./ui.js";

export const defaultSince = () => { const d = new Date(); d.setMonth(d.getMonth() - 3); return isoDay(d); };
const CLIENT_ID = /^[\w-]+\.apps\.googleusercontent\.com$/;
const listOf = (text) => String(text || "").split(/[\s,]+/).map((s) => s.trim().toLowerCase()).filter(Boolean);

export async function loadSettings() {
  return { since: defaultSince(), before: "", terms: "", everything: false, vendorDomains: [], ignoreSenders: [],
    clientId: "", ...((await getKV("settings", {})) ?? {}) };
}

export async function renderGmail(rescan) {
  const s = await loadSettings();
  const [mail, apps] = [await countMessages(), (await getKV("apps", [])) ?? []];
  const origin = location.origin;
  const link = (href, text) => `<a href="${href}" target="_blank" rel="noopener">${text}</a>`;
  const root = mount(`${topnav("gmail")}<main class="page jobs">
    <div class="privacy-banner" role="note">
      <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
      <div><strong>Your data stays in this browser.</strong> Mail goes straight from Gmail to this page and nowhere else.</div>
    </div>

    <h1>Connect Gmail</h1>
    <p class="lead">One-time setup, about 10 minutes: make your own Google sign-in client, then paste its ID here.</p>

    <section class="panel">
      <h2>1. Google Cloud project</h2>
      <ol class="setup-steps">
        <li>${link("https://console.cloud.google.com/projectcreate", "Create a project")} (free, any name).</li>
        <li>${link("https://console.cloud.google.com/apis/library/gmail.googleapis.com", "Enable the Gmail API")}.</li>
      </ol>
      <h2>2. Sign-in client</h2>
      <ol class="setup-steps">
        <li>${link("https://console.cloud.google.com/auth/overview", "Google Auth Platform")} &gt; Get started:
          audience <strong>External</strong>, fill in the required fields.</li>
        <li><strong>Audience &gt; Test users</strong>: add your Gmail address. Leave the app in Testing.</li>
        <li><strong>Data Access</strong>: add the scope <code>https://www.googleapis.com/auth/gmail.readonly</code>.</li>
        <li><strong>Clients &gt; Create client &gt; Web application</strong>, with this
          <strong>Authorized JavaScript origin</strong>: ${copyBlock(origin)}</li>
      </ol>
      <h2>3. Client ID</h2>
      <div class="inline-form">
        <input id="client-id" type="text" spellcheck="false" placeholder="1234567890-abc123.apps.googleusercontent.com" value="${esc(s.clientId)}" aria-label="Client ID">
        <button class="primary" data-save-client>Save</button>
        <span id="client-state" class="dim small">${s.clientId ? "Saved. Connect from the Tracker." : ""}</span>
      </div>
      <p class="dim small">Google will call the app unverified: it's yours, so choose Continue. Access is read-only and
        lasts 7 days. ${link("https://myaccount.google.com/connections", "Revoke it any time")}.</p>
    </section>

    <section class="panel">
      <h2>What to download</h2>
      <p class="dim small">The first sync runs at about 100 emails a minute. Later ones fetch only new mail.</p>
      <div class="settings-grid">
        <label class="field"><span>Since</span><input type="date" id="since" value="${esc(s.since)}"></label>
        <label class="field"><span>Before (optional)</span><input type="date" id="before" value="${esc(s.before)}"></label>
        <label class="field wide"><span>Search words (optional, Gmail syntax)</span>
          <input type="text" id="terms" placeholder="Default: application, interview, offer, …" value="${esc(s.terms)}"></label>
        <label class="check wide"><input type="checkbox" id="everything" ${s.everything ? "checked" : ""}>
          All mail in the range, not just job mail (slower)</label>
        <label class="field"><span>Assessment services (optional)</span>
          <textarea id="vendors" rows="3" placeholder="assessments.example.com">${esc(s.vendorDomains.join("\n"))}</textarea>
          <small class="dim">Domains that email for employers, one per line.</small></label>
        <label class="field"><span>Ignore senders (optional)</span>
          <textarea id="ignore" rows="3" placeholder="newsletters.example.com&#10;someone@example.org">${esc(s.ignoreSenders.join("\n"))}</textarea>
          <small class="dim">Domains or addresses, one per line.</small></label>
      </div>
      <div class="actions"><button class="primary" data-save-settings>Save settings</button></div>
    </section>

    <section class="panel">
      <h2>Your data</h2>
      <p>${plural(mail, "email")} and ${plural(apps.length, "application")} in this browser.</p>
      <div class="actions">
        <button data-export>Export</button>
        <label class="button-like">Import<input type="file" id="import" accept=".json,application/json" hidden></label>
        <button class="danger" data-delete>Delete everything</button>
      </div>
      <p class="dim small">Exports include your full emails and your profile: keep them private.</p>
    </section>
  </main>`);
  bindCopy(root);
  const $ = (sel) => root.querySelector(sel);

  $("[data-save-client]").onclick = async () => {
    const id = $("#client-id").value.trim();
    if (id && !CLIENT_ID.test(id)) {
      $("#client-state").textContent = "That doesn't look like a client ID: it ends in .apps.googleusercontent.com.";
      return;
    }
    await setKV("settings", { ...(await loadSettings()), clientId: id });
    $("#client-state").textContent = id ? "Saved. Connect from the Tracker." : "Removed.";
    if (id) prepare(id).catch((err) => { $("#client-state").textContent = err.message; });
  };

  $("[data-save-settings]").onclick = async () => {
    const since = $("#since").value;
    const before = $("#before").value;
    if (!since) return toast("Pick the first day to download mail from.", "bad");
    if (before && before <= since) return toast("The end date has to be after the start date.", "bad");
    await setKV("settings", { ...(await loadSettings()), since, before, terms: $("#terms").value.trim(),
      everything: $("#everything").checked, vendorDomains: listOf($("#vendors").value), ignoreSenders: listOf($("#ignore").value) });
    try {
      if (mail) await rescan();
      toast("Settings saved.", "good");
    } catch (err) {
      toast(`Saved, but sorting the mail failed: ${err.message}`, "bad");
    }
  };

  $("[data-export]").onclick = async () => {
    const data = await exportAll();
    const blob = new Blob([JSON.stringify(data)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `job-tracker-${isoDay(new Date())}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
  };

  $("#import").onchange = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try {
      const added = await importAll(JSON.parse(await file.text()));
      await rescan();
      toast(`Imported: ${plural(added, "new email")}.`, "good");
      renderGmail(rescan);
    } catch (err) {
      toast(err instanceof SyntaxError ? "That file isn't JSON." : err.message, "bad");
    }
  };

  $("[data-delete]").onclick = async () => {
    if (!confirm("Delete all your mail, applications, settings, profile and postings from this browser?")) return;
    await clearAll();
    toast("Deleted.", "good");
    renderGmail(rescan);
  };
}
