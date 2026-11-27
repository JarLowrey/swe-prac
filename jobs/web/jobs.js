// The Jobs section's router. Routes:
//   #/                     the application tracker
//   #/skills[/<id>][?…]    the Claude skills, optionally scrolled to one and prefilled (company, role, app)
//   #/gmail                Gmail setup, settings and your data

import { renderGmail } from "./setup.js";
import { renderSkills } from "./skills.js";
import { renderTracker, rescan } from "./tracker.js";
import { toast } from "./ui.js";

let leave = null; // cleanup for the page on screen

async function route() {
  const [path, query = ""] = location.hash.replace(/^#/, "").split("?");
  const parts = path.split("/").filter(Boolean);
  const params = new URLSearchParams(query);
  const prev = leave;
  leave = null;
  prev?.();
  try {
    if (parts[0] === "skills") {
      document.title = "Claude skills · Jobs";
      await renderSkills(parts[1], params);
    } else if (parts[0] === "gmail") {
      document.title = "Connect Gmail · Jobs";
      await renderGmail(rescan);
      scrollTo(0, 0);
    } else {
      document.title = "Application tracker · Jobs";
      leave = await renderTracker();
    }
  } catch (err) {
    console.error(err);
    toast(`Something went wrong: ${err.message}`, "bad");
  }
}

addEventListener("hashchange", route);
route();
