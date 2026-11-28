// Connect Gmail: the one-time Google Cloud setup (each visitor makes their own OAuth client, so
// nobody's mail passes through anyone else's app), the client ID box, the tracker's settings, and
// your data in this browser (export, import, delete).

import { prepare, SCOPE } from "./gmail.js";
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
        <li>${link("https://console.cloud.google.com/projectcreate", "Create a project")}: any name, then <strong>Create</strong>.</li>
        <li>Check that it's selected in the project picker at the top. The links below open the selected project.</li>
        <li>${link("https://console.cloud.google.com/apis/library/gmail.googleapis.com", "Gmail API")} &gt; <strong>Enable</strong>.</li>
      </ol>
      <h2>2. Consent screen</h2>
      <ol class="setup-steps">
        <li>${link("https://console.cloud.google.com/auth/overview", "Google Auth Platform")} &gt; <strong>Get started</strong>.</li>
        <li><strong>App information</strong>: any app name, your email as the support email. Next.</li>
        <li><strong>Audience</strong>: External. Next.</li>
        <li><strong>Contact information</strong>: your email. Next.</li>
        <li><strong>Finish</strong>: agree to the policy, Continue, then <strong>Create</strong>.</li>
        <li>${link("https://console.cloud.google.com/auth/audience", "Audience")} &gt; <strong>Test users</strong> &gt;
          <strong>Add users</strong>: your Gmail address, then Save. Leave the app in Testing.</li>
        <li>${link("https://console.cloud.google.com/auth/scopes", "Data Access")} &gt; <strong>Add or remove scopes</strong>.
          Paste this under <strong>Manually add scopes</strong>: ${copyBlock(SCOPE)}
          Add to table, Update, then <strong>Save</strong> at the bottom of the page.</li>
      </ol>
      <h2>3. Sign-in client</h2>
      <ol class="setup-steps">
        <li>${link("https://console.cloud.google.com/auth/clients/create", "Create client")}: application type
          <strong>Web application</strong>, any name.</li>
        <li><strong>Authorized JavaScript origins</strong> &gt; Add URI: ${copyBlock(origin)} Leave redirect URIs empty.</li>
        <li><strong>Create</strong>, then copy the <strong>Client ID</strong> from the dialog. It's also listed under
          ${link("https://console.cloud.google.com/auth/clients", "Clients")}.</li>
      </ol>
      <h2>4. Client ID</h2>
      <div class="inline-form">
        <input id="client-id" type="text" spellcheck="false" placeholder="1234567890-abc123.apps.googleusercontent.com" value="${esc(s.clientId)}" aria-label="Client ID">
        <button class="primary" data-save-client>Save</button>
        <span id="client-state" class="dim small">${s.clientId ? "Saved. Connect from the Tracker." : ""}</span>
      </div>
      <p class="dim small">A new client can take a few minutes, sometimes hours, to start working. If Google shows an
        origin error, wait and try again.</p>
      <h2>5. Connect</h2>
      <ol class="setup-steps">
        <li>On the <a href="#/">Tracker</a>, choose <strong>Connect Gmail and sync</strong>.</li>
        <li>Pick your account. Google says the app is unverified: it's yours, so choose <strong>Continue</strong>.</li>
        <li>Tick <strong>View your email messages and settings</strong>, then Continue.</li>
      </ol>
      <p class="dim small">Access is read-only and lasts 7 days, then you connect again.
        ${link("https://myaccount.google.com/connections", "Revoke it any time")}.</p>
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
