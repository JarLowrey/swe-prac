// The skills the AI skills page hands off to: what each does, the details you type in, and the
// prompt built from them. No page code here, so the Node tests can check the prompts.
// The skills themselves are in jobs/job-search/skills/. browser: it drives your Chrome.

const lines = (text) => String(text || "").split(/\r?\n/).map((s) => s.trim()).filter(Boolean);

export const SKILLS = [
  {
    id: "job-find",
    title: "Find open positions",
    does: "Searches LinkedIn and Indeed in Chrome for recent postings that fit your profile, and saves them to postings.json. Read-only: it never applies or messages anyone.",
    after: 'Then import <code>postings.json</code> on <a href="#/finder">Job finder</a> to chart it.',
    browser: true,
    fields: [
      { id: "keywords", label: "Keywords (optional)", kind: "text", placeholder: "Default: your target roles" },
      { id: "locations", label: "Locations, one per line (optional)", kind: "textarea", placeholder: "Default: where you'd work\nDenver, CO\nRemote" },
      { id: "days", label: "Posted within", kind: "select", options: [["1", "The last day"], ["3", "3 days"], ["7", "A week"], ["14", "2 weeks"]] },
      { id: "sources", label: "Sites", kind: "select", options: [["both", "LinkedIn and Indeed"], ["linkedin", "LinkedIn only"], ["indeed", "Indeed only"]] },
    ],
    // Everything is optional: the skill falls back to the profile's roles and locations, the last day, both sites.
    prompt: (v) => {
      const extra = [];
      if (v.keywords?.trim()) extra.push(`Keywords: ${v.keywords.trim()}`);
      const locs = lines(v.locations);
      if (locs.length) extra.push(`Locations: ${locs.join("; ")}`);
      if (v.days && v.days !== "1") extra.push(`Posted within: ${v.days} days`);
      if (v.sources === "linkedin" || v.sources === "indeed") extra.push(`Sites: ${v.sources === "linkedin" ? "LinkedIn" : "Indeed"} only`);
      return ["/job-find", ...extra].join("\n");
    },
  },
  {
    id: "job-apply",
    title: "Fill in applications",
    does: "Checks each posting's location, fills in the application in Chrome from your profile, drafts written answers and finds contacts. Stops before Submit.",
    browser: true,
    fields: [
      { id: "links", label: "Job links, one per line", kind: "textarea", placeholder: "https://job-boards.greenhouse.io/…\nhttps://jobs.lever.co/…" },
    ],
    prompt: (v) => {
      const links = lines(v.links);
      return links.length ? `/job-apply ${links.join("\n")}` : "";
    },
    // Several links: the script runs each step as its own agent and checks what it left behind.
    batch: (v) => {
      const links = lines(v.links);
      return links.length > 1 ? `python skills/job-apply/scripts/apply.py run ${links.join(" ")}` : "";
    },
  },
  {
    id: "job-answers",
    title: "Draft written answers",
    does: "Drafts answers and cover letters in your voice from your reference docs. Marks gaps with [ADD: …].",
    fields: [
      { id: "company", label: "Company", kind: "text", placeholder: "Northwind" },
      { id: "role", label: "Role", kind: "text", placeholder: "Senior Backend Engineer" },
      { id: "link", label: "Posting link (optional)", kind: "text", placeholder: "https://…" },
      { id: "questions", label: "Questions, one per line, with any length limit", kind: "textarea",
        placeholder: "Why do you want to work here? (1000 characters)\nTell us about a project you're proud of." },
    ],
    prompt: (v) => {
      const qs = lines(v.questions);
      if (!qs.length) return "";
      const at = [v.role?.trim() && `the ${v.role.trim()} role`, v.company?.trim() && `at ${v.company.trim()}`]
        .filter(Boolean).join(" ");
      const head = [`/job-answers Draft answers to these application questions${at ? ` for ${at}` : ""}.`];
      if (v.link?.trim()) head.push(`Posting: ${v.link.trim()}`);
      return [...head, "", ...qs.map((q, i) => `${i + 1}. ${q}`)].join("\n");
    },
  },
  {
    id: "job-contacts",
    title: "Find people to contact",
    does: "Finds a recruiter, an engineer and the likely hiring manager on LinkedIn, and drafts a note to each. Sends nothing.",
    browser: true,
    fields: [
      { id: "company", label: "Company", kind: "text", placeholder: "Northwind" },
      { id: "role", label: "Role", kind: "text", placeholder: "Senior Backend Engineer" },
      { id: "team", label: "Team or tech area (optional)", kind: "text", placeholder: "Payments platform" },
      { id: "link", label: "Posting link (optional)", kind: "text", placeholder: "https://…" },
    ],
    prompt: (v) => {
      if (!v.company?.trim()) return "";
      const about = v.role?.trim() ? ` about the ${v.role.trim()} role` : "";
      return [`/job-contacts Find people to contact at ${v.company.trim()}${about}.`,
        v.team?.trim() ? `Team: ${v.team.trim()}` : "", v.link?.trim() ? `Posting: ${v.link.trim()}` : ""]
        .filter(Boolean).join("\n");
    },
  },
  {
    id: "interview-prep",
    title: "Research the interview loop",
    does: "Researches the company's interview loop and writes a study guide that maps likely questions to your stories.",
    fields: [
      { id: "app", label: "Application from your tracker (optional)", kind: "app" },
      { id: "company", label: "Company", kind: "text", placeholder: "Northwind" },
      { id: "role", label: "Role", kind: "text", placeholder: "Senior Backend Engineer" },
    ],
    prompt: (v) => {
      if (!v.company?.trim()) return "";
      const head = [`/interview-prep ${v.company.trim()}`, "", `Role: ${v.role?.trim() || "not stated"}`];
      if (v.status) head.push(`Status: ${v.status}${v.lastDate ? ` (latest email ${v.lastDate})` : ""}`);
      if (v.context) {
        head.push("", "What my email says about this application is below, for context. Keep names, email text, "
          + "links and ids out of any web search.", "", v.context);
      }
      return head.join("\n");
    },
  },
];

export const skill = (id) => SKILLS.find((s) => s.id === id);
