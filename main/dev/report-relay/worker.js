// The toolkit's report relay - a Cloudflare Worker (free plan).
//
// The design is the Pfadfinder (Oogway) campaign editor's report relay
// (github.com/MasterOogwayHomebrew/RTW-M2TW-Campaign-Editor, worker/report-relay.js, 0.29.2, GPLv3), credited in
// CREDITS: the same three routes and the same privacy rules, with the toolkit's labels and user agent.
//
// The toolkit (Report a problem / Suggest) POSTs one JSON: {kind, message, contact, info, zip (base64)}. The relay
// checks it (size, a real zip, the rate), commits the zip to a PRIVATE reports repo and opens an issue there,
// labelled `bug` or `idea`, so the author gets a notification with the report's number. The GitHub token is the
// Worker's secret (GITHUB_TOKEN): never in the toolkit, never in this repo. Nothing else is kept: no IP address, no
// cookies.
//
// Settings (Worker > Settings > Variables and Secrets), see README.md beside this file:
//   GITHUB_TOKEN  secret: a fine-grained token for the reports repo only - Contents: read and write,
//                 Issues: read and write
//   REPORTS_REPO  text: owner/name of the private reports repo, like ProJ-Yeet/Medieval2-GUI-Toolkit-Reports
// Optional rate limits (wrangler.toml): REPORT_LIMIT, 3 reports or replies a minute from one address; ANSWER_LIMIT,
// 10 answer checks a minute.
//
// Routes (all POST, JSON, from the toolkit only):
//   /          a new report -> {id, issue}
//   /answers   {reports: [{id, issue?}, ...]} -> {answers: {id: {issue, state, reason, messages: [{from, text, at}]}}}
//              only the comments of the reports whose numbers are given; a number is random and known only to the
//              one who sent it, so nobody reads another's answers. `from` is `author` or `you`.
//   /reply     {id, issue?, message, zip?} -> {ok}: the reporter's answer, a comment on the same issue, with its
//              zip committed beside the report's own

const ZIP_CAP = 4 * 1024 * 1024; // bytes, as report.RELAY_ZIP in the toolkit
const B64_CAP = Math.ceil(ZIP_CAP / 3) * 4 + 16;
const AGENT = "M2-GUI-Kit/";
const REPLY_MARK = "**Reply from the reporter**";
const ID_RE = /^R-\d{8}-[0-9A-F]{6}$/;
const MAX_IDS = 30;

function reply(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function reportId() {
  const d = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const r = crypto.getRandomValues(new Uint8Array(3));
  return "R-" + d + "-" + [...r].map((b) => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}

function clean(text, cap) {
  // plain text for the issue: no html, no mentions that would ping anyone
  return String(text || "")
    .slice(0, cap)
    .replace(/[<>]/g, "")
    .replace(/@/g, "@​");
}

async function github(env, method, path, body, whole) {
  const r = await fetch((whole ? "https://api.github.com" : "https://api.github.com/repos/" + env.REPORTS_REPO) + path, {
    method,
    headers: {
      Authorization: "Bearer " + env.GITHUB_TOKEN,
      Accept: "application/vnd.github+json",
      "User-Agent": "m2-gui-kit-report-relay",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error("GitHub " + r.status);
  return r.json();
}

function goodZip(zip) {
  return typeof zip === "string" && zip.startsWith("UEsDB") && zip.length <= B64_CAP && /^[A-Za-z0-9+/=]+$/.test(zip);
}

function zipPath(id, suffix) {
  const day = id.slice(2, 10);
  return "reports/" + day.slice(0, 4) + "-" + day.slice(4, 6) + "-" + day.slice(6) + "/" + id + (suffix || "") + ".zip";
}

async function limited(env, binding, request) {
  if (!env[binding]) return false;
  const { success } = await env[binding].limit({ key: request.headers.get("CF-Connecting-IP") || "?" });
  return !success;
}

// A report's issue: by the number the toolkit kept, checked against the title so a wrong pair gives nothing, else
// found by the report's number in the titles.
async function findIssue(env, id, issue) {
  if (Number.isInteger(issue) && issue > 0) {
    try {
      const it = await github(env, "GET", "/issues/" + issue);
      if (String(it.title || "").startsWith(id + ":")) return it;
    } catch (e) {
      /* fall through to the search */
    }
  }
  const q = encodeURIComponent("repo:" + env.REPORTS_REPO + ' is:issue in:title "' + id + '"');
  const found = await github(env, "GET", "/search/issues?q=" + q + "&per_page=5", undefined, true);
  return (found.items || []).find((it) => String(it.title || "").startsWith(id + ":")) || null;
}

// A comment as the reporter sees it; their own replies without the mark and the file link.
function asMessage(c) {
  let text = String(c.body || "").replace(/\r/g, "");
  let from = "author";
  if (text.startsWith(REPLY_MARK)) {
    from = "you";
    text = text.slice(REPLY_MARK.length).replace(/\n+Files: https:\/\/\S+\s*$/, "");
    text = text.split("\n").map((l) => l.replace(/^> ?/, "")).join("\n");
  }
  return { from, text: text.trim().slice(0, 8000), at: c.created_at || "" };
}

async function answers(request, env) {
  if (await limited(env, "ANSWER_LIMIT", request)) return reply(429, { error: "too many checks in a minute" });
  let data;
  try {
    data = await request.json();
  } catch (e) {
    return reply(400, { error: "not a list of reports" });
  }
  const asked = (Array.isArray(data.reports) ? data.reports : [])
    .slice(0, MAX_IDS)
    .filter((r) => r && ID_RE.test(String(r.id || "")));
  const out = {};
  for (const r of asked) {
    try {
      const it = await findIssue(env, r.id, r.issue);
      if (!it) continue;
      const comments = await github(env, "GET", "/issues/" + it.number + "/comments?per_page=100");
      out[r.id] = {
        issue: it.number,
        state: it.state,
        reason: it.state_reason || "",
        messages: comments.map(asMessage).filter((m) => m.text),
      };
    } catch (e) {
      /* skipped; the toolkit asks again later */
    }
  }
  return reply(200, { answers: out });
}

async function answerBack(request, env) {
  if (await limited(env, "REPORT_LIMIT", request))
    return reply(429, { error: "too many messages in a minute - wait a little and send again" });
  let data;
  try {
    data = await request.json();
  } catch (e) {
    return reply(400, { error: "not a reply" });
  }
  const id = String(data.id || "");
  if (!ID_RE.test(id)) return reply(400, { error: "no report number" });
  const message = clean(data.message, 4000).trim();
  if (!message) return reply(400, { error: "the reply is empty" });
  if (data.zip !== undefined && data.zip !== null && !goodZip(data.zip))
    return reply(400, { error: "the files are broken or too big" });
  try {
    const it = await findIssue(env, id, data.issue);
    if (!it) return reply(404, { error: "no such report" });
    const lines = [REPLY_MARK, "", message.split("\n").map((l) => "> " + l).join("\n")];
    if (data.zip) {
      const file = zipPath(id, "-reply-" + Date.now().toString(36));
      await github(env, "PUT", "/contents/" + file, { message: "Reply to " + id, content: data.zip });
      lines.push("", "Files: https://github.com/" + env.REPORTS_REPO + "/blob/HEAD/" + file);
    }
    await github(env, "POST", "/issues/" + it.number + "/comments", { body: lines.join("\n") });
  } catch (e) {
    return reply(502, { error: "the reply could not be filed (" + e.message + ")" });
  }
  return reply(200, { ok: true });
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return reply(405, { error: "send a report from the toolkit (Report a problem)" });
    if (!env.GITHUB_TOKEN || !env.REPORTS_REPO) return reply(503, { error: "the relay is not set up yet" });
    if (!(request.headers.get("User-Agent") || "").startsWith(AGENT))
      return reply(403, { error: "reports come from the toolkit only" });
    const size = Number(request.headers.get("Content-Length") || 0);
    if (size > B64_CAP + 16384) return reply(413, { error: "the report is too big" });
    const route = new URL(request.url).pathname.replace(/\/+$/, "");
    if (route === "/answers") return answers(request, env);
    if (route === "/reply") return answerBack(request, env);
    if (await limited(env, "REPORT_LIMIT", request))
      return reply(429, { error: "too many reports in a minute - wait a little and send again" });
    let data;
    try {
      data = await request.json();
    } catch (e) {
      return reply(400, { error: "not a report" });
    }
    const zip = typeof data.zip === "string" ? data.zip : "";
    if (!goodZip(zip)) return reply(400, { error: "the report has no zip, or a broken one" });
    const kind = data.kind === "idea" ? "idea" : "bug";
    const id = reportId();
    const file = zipPath(id);
    const info = data.info && typeof data.info === "object" ? data.info : {};
    const lines = Object.entries(info)
      .slice(0, 12)
      .map(([k, v]) => "- **" + clean(k, 40) + "**: " + clean(v, 200));
    let issue = 0;
    try {
      await github(env, "PUT", "/contents/" + file, { message: "Report " + id, content: zip });
      const made = await github(env, "POST", "/issues", {
        title: id + ": " + (kind === "idea" ? "[Idea] " : "[Bug] ") + (clean(data.message, 80).split("\n")[0] || "(no words)"),
        labels: [kind],
        body: [
          kind === "idea" ? "**The idea**" : "**What happened**",
          "",
          clean(data.message, 4000).split("\n").map((l) => "> " + l).join("\n") || "> (not said)",
          "",
          "**Contact**: " + (clean(data.contact, 200) || "none"),
          "",
          ...lines,
          "",
          "The files: https://github.com/" + env.REPORTS_REPO + "/blob/HEAD/" + file,
        ].join("\n"),
      });
      issue = made.number || 0;
    } catch (e) {
      return reply(502, { error: "the report could not be filed (" + e.message + ") - save the zip and send it on Discord" });
    }
    return reply(200, { id, issue });
  },
};
