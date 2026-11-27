// The Claude Code skills the Skills page hands off to: what each does, what it needs before you
// start, the details you type in, and the prompt built from them. No page code here, so the
// Node tests can check the prompts. The skills themselves are in jobs/job-search/.claude/skills/.

// Things a skill needs, shown as its "Before you start" list. Each is [title, detail].
export const NEEDS = {
  code: ["Claude Code, signed in with your Claude account",
    "In a terminal, the desktop app or the VS Code extension. Install it from code.claude.com, then run /login."],
  kit: ["The job-search skills",
    "Download job-search.zip below and unzip it so you have a job-search folder in your home folder. Start Claude Code in that folder."],
  profile: ["Your profile and resume",
    "reference/profile.yaml filled in (copy it from examples/reference/), and your resume PDF in reference/."],
  material: ["Material to draw answers from",
    "A brag doc, behavioral stories and project write-ups in reference/. The skill only uses facts written there."],
  chrome: ["Claude in Chrome, connected to Claude Code",
    "Install the Claude in Chrome extension (version 1.0.36 or later) in Chrome or Edge and sign in to it. In Claude Code, run /chrome and turn on “Enabled by default”, or start it with claude --chrome. It needs a Pro, Max, Team or Enterprise plan, and doesn't work when Claude Code is signed in with an API key."],
  sites: ["Signed in to the job sites in that browser",
    "Claude fills forms in your own Chrome, so sign in to sites that need an account (Workday, iCIMS and the like) first, or when it asks. Approve each site when Claude in Chrome asks."],
  linkedin: ["Signed in to LinkedIn in that browser",
    "Searches use your own LinkedIn account, lightly (about 6 to 8 page loads per company)."],
  drive: ["Optional: Google Drive connected in Claude",
    "Only if your profile links reference docs in Google Drive."],
  docs: ["Optional: Claude Docs",
    "With it the guide is a doc you can share; without it, the skill writes a markdown file in your job-search folder."],
};

const lines = (text) => String(text || "").split(/\r?\n/).map((s) => s.trim()).filter(Boolean);

export const SKILLS = [
  {
    id: "job-apply",
    title: "Fill in applications",
    does: "Give it job links. For each one it reads the posting, checks the location against yours, opens the application in your Chrome and fills it from your profile: contact details, work authorization, self-ID answers and your resume. It drafts the written answers, finds people to contact, logs the application, and stops before Submit so you can review it.",
    needs: ["code", "kit", "profile", "material", "chrome", "sites"],
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
      return links.length > 1 ? `python .claude/skills/job-apply/scripts/apply.py run ${links.join(" ")}` : "";
    },
  },
  {
    id: "job-answers",
    title: "Draft written answers",
    does: "Drafts answers to an application's free-text questions and cover letters in your voice, from your resume and the material in your reference folder. It only uses facts you've written down, leaves [ADD: …] placeholders for anything it doesn't know, and keeps to each question's length limit.",
    needs: ["code", "kit", "profile", "material", "drive"],
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
    does: "Finds a recruiter, an engineer and, if it can, the hiring manager at the company on LinkedIn, and drafts a short connection note and a follow-up for each. It never sends a request or a message: you do the outreach.",
    needs: ["code", "kit", "profile", "chrome", "linkedin"],
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
    does: "Researches how the company interviews for your role (the loop, behavioral, coding and system design rounds) with four research agents searching the web, then writes a sourced study guide that maps likely behavioral questions onto your stories and links the practice section's foundations pages. Pick an application from your tracker to include what your emails say about the process.",
    needs: ["code", "kit", "material", "docs"],
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
