// Open jobs: no listings yet, just how an employer gets a position posted here.

import { esc, mount, topnav } from "./ui.js";

// The address employers write to. A placeholder until a real contact address is chosen.
export const CONTACT_EMAIL = "TEMP_EMAIL";

export function renderOpenJobs() {
  const mail = esc(CONTACT_EMAIL);
  mount(`${topnav("open")}<main class="page jobs">
    <h1>Open jobs</h1>
    <section class="panel">
      <h2>Hiring software engineers?</h2>
      <p>To post a position here, email <a href="mailto:${mail}?subject=${encodeURIComponent("Job posting")}">${mail}</a>
        with the role, location and a link.</p>
    </section>
  </main>`);
}
