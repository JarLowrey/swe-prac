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
  const root = mount(`${topnav("gmail")}<main class="page jobs">
    <h1>Connect Gmail</h1>
    <p class="lead">The tracker reads your job mail straight from Gmail into this browser. There's no server in
      between: Google gives this page a read-only token, the page downloads the messages and sorts them with Python
      running in the page, and everything stays in this browser. To make that possible, you create your own Google
      sign-in client once (about 10 minutes) and paste its ID here.</p>

    <section class="panel">
      <h2>1. Create a Google Cloud project with the Gmail API</h2>
      <ol class="setup-steps">
        <li>Open the <a href="https://console.cloud.google.com/projectcreate" target="_blank" rel="noopener">Google Cloud console</a>
          and create a project. Any name works, such as "Job tracker". It's free.</li>
        <li>Enable the <a href="https://console.cloud.google.com/apis/library/gmail.googleapis.com" target="_blank" rel="noopener">Gmail API</a>
          for that project (APIs &amp; Services &gt; Library &gt; Gmail API &gt; Enable).</li>
      </ol>
      <h2>2. Set up sign-in</h2>
      <ol class="setup-steps">
        <li>Open <a href="https://console.cloud.google.com/auth/overview" target="_blank" rel="noopener">Google Auth Platform</a>
          and click Get started. Give the app a name, pick your address as the support email, choose
          <strong>External</strong> as the audience, add a contact email, agree to the policy and click Create.</li>
        <li>Under <strong>Audience &gt; Test users</strong>, add the Gmail address you'll connect. Leave the app in
          <strong>Testing</strong>: only the test users you list can use it, which is what you want.</li>
        <li>Under <strong>Data Access &gt; Add or remove scopes</strong>, add
          <code>https://www.googleapis.com/auth/gmail.readonly</code> and save.</li>
        <li>Under <strong>Clients &gt; Create client</strong>, choose <strong>Web application</strong>. Under
          <strong>Authorized JavaScript origins</strong>, add this site's address, then Create:
          ${copyBlock(origin)}
          No redirect URI is needed. There's no client secret to keep either: a web client's ID isn't secret.</li>
      </ol>
      <h2>3. Paste the client ID</h2>
      <div class="inline-form">
        <input id="client-id" type="text" spellcheck="false" placeholder="1234567890-abc123.apps.googleusercontent.com" value="${esc(s.clientId)}">
        <button class="primary" data-save-client>Save</button>
        <span id="client-state" class="dim small">${s.clientId ? "Saved. Connect from the Tracker page." : ""}</span>
      </div>
      <div class="callout info small">
        <strong>What to expect when you connect.</strong> Google says it "hasn't verified this app": that's expected
        for an app in testing, and the app is yours. Choose Continue and allow <em>Read your email</em>. Access is
        read-only (this page can't send, delete or label anything) and lasts an hour; while the app is in testing,
        Google asks you to allow it again every 7 days. You can remove access at any time in your
        <a href="https://myaccount.google.com/connections" target="_blank" rel="noopener">Google account</a>.
      </div>
    </section>

    <section class="panel">
      <h2>What the tracker downloads</h2>
      <div class="settings-grid">
        <label class="field"><span>Mail since</span><input type="date" id="since" value="${esc(s.since)}"></label>
        <label class="field"><span>Up to (optional, not included)</span><input type="date" id="before" value="${esc(s.before)}"></label>
        <label class="field wide"><span>Search words (optional)</span>
          <input type="text" id="terms" placeholder="Leave empty for the default job words (application, interview, offer, …)" value="${esc(s.terms)}">
          <small class="dim">Gmail search syntax, such as <code>interview OR "next steps"</code>.</small></label>
        <label class="check wide"><input type="checkbox" id="everything" ${s.everything ? "checked" : ""}>
          Download all mail in the date range, not just mail with job words (slower: about 100 messages a minute)</label>
        <label class="field"><span>Assessment and interview services</span>
          <textarea id="vendors" rows="4" placeholder="assessments.example.com">${esc(s.vendorDomains.join("\n"))}</textarea>
          <small class="dim">Domains of services that email you on employers' behalf, one per line. If one shows up as a
            company in the tracker, add it here. Its name also marks its emails as assessments.</small></label>
        <label class="field"><span>Senders to ignore</span>
          <textarea id="ignore" rows="4" placeholder="newsletters.example.com&#10;someone@example.org">${esc(s.ignoreSenders.join("\n"))}</textarea>
          <small class="dim">A domain, or a single address, per line. Their mail is never treated as an application.</small></label>
      </div>
      <div class="actions"><button class="primary" data-save-settings>Save settings</button>
        <span class="dim small">Saving sorts the mail you already have again. New dates apply at the next sync.</span></div>
    </section>

    <section class="panel">
      <h2>Your data in this browser</h2>
      <p>${plural(mail, "email")} and ${plural(apps.length, "application")} are stored in this browser only
        (IndexedDB, for this site). Clearing the site's data in the browser deletes them.</p>
      <div class="actions">
        <button data-export>Export</button>
        <label class="button-like">Import<input type="file" id="import" accept=".json,application/json" hidden></label>
        <button class="danger" data-delete>Delete everything</button>
      </div>
      <p class="dim small">Export saves your mail, settings and the statuses you set to a JSON file: a backup, or a way to
        move to another browser. It contains the full text of your job emails, so keep it private. Import accepts
        that file (or any JSON with a <code>messages</code> list of the same records) and merges it with what's here.</p>
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
    $("#client-state").textContent = id ? "Saved. Connect from the Tracker page." : "Removed.";
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
    if (!confirm("Delete your downloaded mail, the applications, your settings and the statuses you set, from this browser?")) return;
    await clearAll();
    toast("Deleted.", "good");
    renderGmail(rescan);
  };
}
