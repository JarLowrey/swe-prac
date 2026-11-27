// The profile form on the AI skills page, and the reference/profile.yaml it writes into the
// downloaded kit. No page code here, so the Node tests can check the YAML. The keys and allowed
// values follow job-search/profile.schema.json; anything required and left blank is written as
// TODO, which the skills ask you for before they fill a form.

const YES_NO = [["", "Choose…"], ["true", "Yes"], ["false", "No"]];
const ASK = [["", "Ask me each time"], ["true", "Yes"], ["false", "No"]];
const DECLINE = ["decline", "Decline"];

// Each field: key (a dotted path into the YAML), label, and kind: text (the default), select, list
// (one item per line), check, or docs (Drive links). options are [value, label]; the first is the default.
export const GROUPS = [
  { title: "You", fields: [
    { key: "identity.first_name", label: "First name", required: true, auto: "given-name" },
    { key: "identity.last_name", label: "Last name", required: true, auto: "family-name" },
    { key: "identity.preferred_name", label: "Preferred name", hint: "If not your first name" },
    { key: "identity.pronouns", label: "Pronouns", kind: "select",
      options: [["", "Leave blank"], ["he/him", "he/him"], ["she/her", "she/her"], ["they/them", "they/them"], ["other", "Other"]] },
    { key: "identity.email", label: "Email", required: true, auto: "email" },
    { key: "identity.phone", label: "Phone", required: true, auto: "tel-national", hint: "Without the country code" },
    { key: "identity.linkedin_url", label: "LinkedIn", url: true, placeholder: "https://www.linkedin.com/in/…" },
    { key: "identity.github_url", label: "GitHub", url: true, placeholder: "https://github.com/…" },
    { key: "identity.portfolio_url", label: "Website", url: true, auto: "url" },
    { key: "identity.languages", label: "Languages", placeholder: "English (fluent), Spanish (conversational)" },
  ] },
  { title: "Location", fields: [
    { key: "location.city", label: "City", required: true, auto: "address-level2" },
    { key: "location.state", label: "State", required: true, auto: "address-level1" },
    { key: "location.zip", label: "ZIP", auto: "postal-code" },
    { key: "location.country", label: "Country", required: true, auto: "country-name", placeholder: "United States" },
    { key: "location.street_address", label: "Street address", auto: "street-address", hint: "Only for forms that require it" },
    { key: "location.acceptable_locations", label: "Where you'd work", kind: "list", required: true, wide: true,
      placeholder: "Denver area, onsite or hybrid\nRemote within the US", hint: "One per line. Jobs anywhere else are skipped." },
    { key: "location.open_to_relocation", label: "Open to relocating", kind: "check" },
  ] },
  { title: "Work authorization", fields: [
    { key: "work_authorization.citizenship", label: "Citizenship", kind: "select", required: true,
      options: [["", "Choose…"], ["us_citizen", "US citizen"], ["us_permanent_resident", "US permanent resident"],
        ["work_visa", "Work visa (H-1B, L-1, TN, OPT…)"], ["other", "Other"]] },
    { key: "work_authorization.authorized_to_work_in_us", label: "Authorized to work in the US?", kind: "select", required: true, options: YES_NO },
    { key: "work_authorization.requires_sponsorship_now", label: "Need sponsorship now?", kind: "select", required: true, options: YES_NO },
    { key: "work_authorization.requires_sponsorship_future", label: "Need sponsorship later?", kind: "select", required: true, options: YES_NO },
    { key: "work_authorization.security_clearance", label: "Security clearance", kind: "select",
      options: [["none", "None"], ["public_trust", "Public trust"], ["confidential", "Confidential"], ["secret", "Secret"],
        ["top_secret", "Top secret"], ["top_secret_sci", "Top secret / SCI"]] },
    { key: "work_authorization.willing_to_obtain_clearance", label: "Willing to get a clearance?", kind: "select", required: true, options: YES_NO },
    { key: "military.military_spouse", label: "Military spouse?", kind: "select", options: ASK },
    { key: "military.national_guard_or_reserves", label: "National Guard or Reserves?", kind: "select", options: ASK },
    { key: "consents.sms_contact", label: "OK to be texted about applications?", kind: "select", options: ASK },
    { key: "consents.ai_application_review", label: "OK for AI tools to review applications?", kind: "select", options: ASK },
  ] },
  { title: "Voluntary self-ID", note: "All default to Decline.", collapsed: true, fields: [
    { key: "eeo.gender", label: "Gender", kind: "select",
      options: [DECLINE, ["man", "Man"], ["woman", "Woman"], ["non_binary", "Non-binary"], ["other", "Other"]] },
    { key: "eeo.hispanic_or_latino", label: "Hispanic or Latino", kind: "select",
      options: [DECLINE, ["hispanic_or_latino", "Yes"], ["not_hispanic_or_latino", "No"]] },
    { key: "eeo.race", label: "Race", kind: "select",
      options: [DECLINE, ["american_indian_or_alaska_native", "American Indian or Alaska Native"], ["asian", "Asian"],
        ["black_or_african_american", "Black or African American"],
        ["native_hawaiian_or_pacific_islander", "Native Hawaiian or Pacific Islander"], ["white", "White"],
        ["two_or_more", "Two or more races"]] },
    { key: "eeo.veteran_status", label: "Veteran status", kind: "select",
      options: [DECLINE, ["not_a_protected_veteran", "Not a protected veteran"], ["protected_veteran", "Protected veteran"]] },
    { key: "eeo.disability_status", label: "Disability", kind: "select",
      options: [DECLINE, ["no_disability", "No disability"], ["has_disability", "Has a disability"]] },
    { key: "eeo.sexual_orientation", label: "Sexual orientation", kind: "select",
      options: [DECLINE, ["heterosexual", "Heterosexual"], ["gay_or_lesbian", "Gay or lesbian"], ["bisexual", "Bisexual"],
        ["pansexual", "Pansexual"], ["asexual", "Asexual"], ["queer", "Queer"], ["other", "Other"]] },
    { key: "eeo.transgender", label: "Transgender", kind: "select",
      options: [DECLINE, ["transgender", "Yes"], ["not_transgender", "No"]] },
    { key: "eeo.lgbtqia", label: "LGBTQIA+", kind: "select", options: [DECLINE, ["lgbtqia", "Yes"], ["not_lgbtqia", "No"]] },
    { key: "eeo.other_self_id_questions", label: "Any other self-ID question", kind: "select",
      options: [DECLINE, ["ask", "Leave blank and ask me"]] },
  ] },
  { title: "Roles and resume", fields: [
    { key: "preferences.target_roles", label: "Roles you're applying for", required: true, wide: true,
      placeholder: "Senior or staff backend engineer", hint: "Postings clearly below this are flagged." },
    { key: "preferences.salary_expectation", label: "Salary expectation", placeholder: "Blank: ask me for each job" },
    { key: "preferences.earliest_start", label: "Earliest start", placeholder: "Two weeks after an offer" },
    { key: "preferences.heard_about_default", label: "How you heard about the job", placeholder: "Company careers page" },
    { key: "resume.file", label: "Resume file name", required: true, placeholder: "Your_Name_Resume.pdf",
      hint: "Put it in reference/. Employers see this name." },
    { key: "resume.google_doc_url", label: "Resume as a Google Doc", url: true, placeholder: "https://docs.google.com/…" },
  ] },
  { title: "Extras", fields: [
    { key: "reference_docs", label: "Google Drive docs to draft from", kind: "docs", wide: true,
      placeholder: "https://docs.google.com/document/d/…  On-call redesign: proposal and results",
      hint: "One per line: the link, then what it covers. Your agent needs Google Drive access." },
    { key: "contacts.shared_background", label: "Groups you're part of", kind: "list", wide: true,
      placeholder: "Denver Go meetup (co-organizer)", hint: "One per line. Used to find contacts." },
  ] },
];

export const FIELDS = GROUPS.flatMap((g) => g.fields);
const BY_KEY = Object.fromEntries(FIELDS.map((f) => [f.key, f]));

const text = (p, key) => String(p?.[key] ?? "").trim();
const lines = (s) => String(s ?? "").split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
// A select's value if it's one of its options, else its default.
function choice(p, key) {
  const f = BY_KEY[key];
  const v = text(p, key);
  return f.options.some(([o]) => o === v) ? v : f.options[0][0];
}
const filled = (p, f) => (f.kind === "list" ? lines(p?.[f.key]).length > 0 : f.kind === "check" ? true
  : f.kind === "select" ? choice(p, f.key) !== "" : text(p, f.key) !== "");

// The value a field starts with on the form.
export const initial = (f) => (f.kind === "check" ? false : f.kind === "select" ? f.options[0][0] : "");

// The labels of required fields still blank. The download works anyway; the skills ask for these.
export const missing = (p) => FIELDS.filter((f) => f.required && !filled(p, f)).map((f) => f.label);

// "a/b\c.pdf" -> "c.pdf"
const baseName = (s) => s.split(/[\\/]/).pop();
const withScheme = (u) => (!u || /^https?:\/\//i.test(u) ? u : `https://${u}`);

// One Drive doc per line: the link, then what it covers ("link - notes", "link: notes" also work).
export function parseDocs(s) {
  return lines(s).map((line) => {
    const [url, ...rest] = line.split(/\s+/);
    const useFor = rest.join(" ").replace(/^[-–—:|]+\s*/, "");
    return { url: withScheme(url.replace(/[:,;]+$/, "")), useFor: useFor || "Reference material" };
  }).filter((d) => /^https?:\/\/\S+\.\S+/.test(d.url));
}

const q = (s) => JSON.stringify(s); // a JSON string is a valid YAML double-quoted string

export function profileYaml(p = {}) {
  const str = (key) => {
    const f = BY_KEY[key];
    const v = f.url ? withScheme(text(p, key)) : text(p, key);
    return q(v || (f.required ? "TODO" : ""));
  };
  const pick = (key) => choice(p, key) || (BY_KEY[key].required ? "TODO" : '""');
  const list = (key, required) => {
    const items = lines(p[key]);
    if (!items.length && required) items.push("TODO");
    return items.length ? items.map((x) => `\n    - ${q(x)}`).join("") : " []";
  };
  // Optional yes/no answers: left out when blank, which means ask each time.
  const optional = (keys) => keys.filter((k) => choice(p, k)).map((k) => `  ${k.split(".")[1]}: ${choice(p, k)}`);
  const section = (name, rows) => (rows.length ? [`${name}:`, ...rows, ""] : []);
  const resume = baseName(text(p, "resume.file"));
  const pronouns = choice(p, "identity.pronouns");
  const docs = parseDocs(p.reference_docs);

  return [
    "# Job application profile, made on the AI skills page. The job-search skills read it",
    "# from reference/profile.yaml. Edit it freely: profile.schema.json lists the allowed values,",
    "# and the skills ask you for anything still marked TODO.",
    "",
    "identity:",
    ...["first_name", "last_name", "preferred_name"].map((k) => `  ${k}: ${str(`identity.${k}`)}`),
    `  pronouns: ${pronouns ? pronouns : '""'}`,
    ...["email", "phone", "linkedin_url", "github_url", "portfolio_url", "languages"].map((k) => `  ${k}: ${str(`identity.${k}`)}`),
    "",
    "location:",
    ...["city", "state", "zip", "country", "street_address"].map((k) => `  ${k}: ${str(`location.${k}`)}`),
    `  open_to_relocation: ${p["location.open_to_relocation"] === true}`,
    `  acceptable_locations:${list("location.acceptable_locations", true)}`,
    "",
    "work_authorization:",
    ...["citizenship", "authorized_to_work_in_us", "requires_sponsorship_now", "requires_sponsorship_future",
      "security_clearance", "willing_to_obtain_clearance"].map((k) => `  ${k}: ${pick(`work_authorization.${k}`)}`),
    "",
    "# Voluntary self-ID. decline is always a valid answer.",
    "eeo:",
    `  gender: ${pick("eeo.gender")}`,
    `  pronouns: ${pronouns || "decline"}`,
    ...["hispanic_or_latino", "race", "veteran_status", "disability_status", "sexual_orientation", "transgender",
      "lgbtqia", "other_self_id_questions"].map((k) => `  ${k}: ${pick(`eeo.${k}`)}`),
    "",
    ...section("military", optional(["military.military_spouse", "military.national_guard_or_reserves"])),
    ...section("consents", optional(["consents.sms_contact", "consents.ai_application_review"])),
    "# Blank: taken from your resume. Fill one in to override it.",
    "background:",
    '  current_title: ""',
    '  current_employer: ""',
    '  years_of_experience: ""',
    "  education: []",
    "",
    "preferences:",
    `  target_roles: ${str("preferences.target_roles")}`,
    `  salary_expectation: ${q(text(p, "preferences.salary_expectation") || "ask-per-job")}`,
    `  earliest_start: ${str("preferences.earliest_start")}`,
    `  heard_about_default: ${str("preferences.heard_about_default")}`,
    "",
    "resume:",
    `  path: ${q(resume ? `reference/${resume}` : "TODO")}`,
    `  google_doc_url: ${str("resume.google_doc_url")}`,
    "",
    '# Every other file in this folder is read when drafting answers.',
    'reference_folder: "reference"',
    "",
    `reference_docs:${docs.length ? docs.map((d) => `\n  - url: ${q(d.url)}\n    use_for: ${q(d.useFor)}`).join("") : " []"}`,
    "",
    "contacts:",
    "  count: 3",
    `  shared_background:${list("contacts.shared_background", false)}`,
    "",
  ].join("\n");
}
