// Cloudflare report relay. Written independently from a description of the behaviour (2026-11-06); the design follows Pfadfinder-Adam's campaign editor report relay.

const ID = /^R-\d{8}-[0-9A-F]{6}$/;
const REPLY = '**Reply from the reporter**';
const ZIP_LIMIT = 5_592_424;

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

const error = (status, message) => json({ error: message }, status);
const text = (value, limit) => String(value || '').slice(0, limit)
  .replace(/[<>]/g, '').replace(/@/g, '@\u200b');
const quote = value => value.split('\n').map(line => `> ${line}`).join('\n');
const validZip = value => typeof value === 'string' && value.length <= ZIP_LIMIT
  && value.startsWith('UEsDB') && /^[A-Za-z0-9+/=]+$/.test(value);
const issueNumber = value => Number.isInteger(value) && value > 0;

function attachmentPath(id, suffix = '') {
  const day = `${id.slice(2, 6)}-${id.slice(6, 8)}-${id.slice(8, 10)}`;
  return `reports/${day}/${id}${suffix}.zip`;
}

function github(env) {
  const root = `https://api.github.com/repos/${env.REPORTS_REPO}`;
  const call = async (path, method = 'GET', body) => {
    const response = await globalThis.fetch(path.startsWith('https://') ? path : root + path, {
      method,
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': 'M2-GUI-Kit-report-relay',
        'X-GitHub-Api-Version': '2022-11-28',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
    return response.json();
  };
  return {
    call,
    upload: (path, content) => call(`/contents/${path}`, 'PUT', {
      message: `Store report attachment ${path}`, content,
    }),
    link: path => `https://github.com/${env.REPORTS_REPO}/blob/HEAD/${path}`,
    async find(id, hint) {
      const matches = issue => typeof issue?.title === 'string'
        && issue.title.startsWith(`${id}:`) && issueNumber(issue.number);
      if (issueNumber(hint)) {
        try {
          const issue = await call(`/issues/${hint}`);
          if (matches(issue)) return issue;
        } catch {
          // A failed hint still permits the identifier search.
        }
      }
      const params = new URLSearchParams({
        q: `repo:${env.REPORTS_REPO} is:issue in:title "${id}"`, per_page: '5',
      });
      const result = await call(`https://api.github.com/search/issues?${params}`);
      return (result.items || []).slice(0, 5).find(matches);
    },
  };
}

function displayComment(comment) {
  let value = String(comment.body || '');
  const reporter = value.startsWith(REPLY);
  value = value.replace(/\r/g, '');
  if (reporter) {
    value = value.slice(REPLY.length)
      .replace(/\nFiles: https:\/\/[^\n]+\s*$/, '')
      .replace(/^> ?/gm, '');
  }
  value = value.trim().slice(0, 8000);
  return value ? {
    from: reporter ? 'you' : 'author', text: value, at: comment.created_at || '',
  } : null;
}

async function createReport(body, api) {
  if (!validZip(body.zip)) return error(400, 'A screened ZIP attachment is required.');
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const bytes = crypto.getRandomValues(new Uint8Array(3));
  const random = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('').toUpperCase();
  const id = `R-${date}-${random}`;
  const path = attachmentPath(id);
  const idea = body.kind === 'idea';
  const summary = text(body.message, 80).split(/\r?\n/)[0].trim() || 'No description';
  const sections = [
    idea ? '**The idea**' : '**What happened**',
    quote(text(body.message, 4000)),
    `**Contact**: ${text(body.contact, 200) || 'Not supplied'}`,
  ];
  if (body.info && typeof body.info === 'object' && !Array.isArray(body.info)) {
    const bullets = Object.entries(body.info).slice(0, 12)
      .map(([key, value]) => `- **${text(key, 40)}**: ${text(value, 200)}`);
    if (bullets.length) sections.push(bullets.join('\n'));
  }
  sections.push(`The files: ${api.link(path)}`);
  try {
    await api.upload(path, body.zip);
    const issue = await api.call('/issues', 'POST', {
      title: `${id}: [${idea ? 'Idea' : 'Bug'}] ${summary}`,
      labels: [idea ? 'idea' : 'bug'], body: sections.join('\n\n'),
    });
    return json({ id, issue: issueNumber(issue?.number) ? issue.number : 0 });
  } catch (failure) {
    return error(502, `The report could not be filed. Keep the ZIP for another submission channel. ${failure.message}`);
  }
}

async function answers(body, api) {
  const result = {};
  const reports = Array.isArray(body.reports) ? body.reports.slice(0, 30) : [];
  for (const entry of reports) {
    if (typeof entry?.id !== 'string' || !ID.test(entry.id)) continue;
    try {
      const issue = await api.find(entry.id, entry.issue);
      if (!issue) continue;
      const comments = await api.call(`/issues/${issue.number}/comments?per_page=100`);
      result[entry.id] = {
        issue: issue.number, state: issue.state || '', reason: issue.state_reason || '',
        messages: comments.map(displayComment).filter(Boolean),
      };
    } catch {
      // Each report is independent, so a failed lookup contributes no answer.
    }
  }
  return json({ answers: result });
}

async function reply(body, api) {
  if (typeof body.id !== 'string' || !ID.test(body.id)) return error(400, 'A valid report identifier is required.');
  const message = text(body.message, 4000).trim();
  if (!message) return error(400, 'Reply text is required.');
  if (body.zip != null && !validZip(body.zip)) return error(400, 'The reply ZIP was rejected.');
  try {
    const issue = await api.find(body.id, body.issue);
    if (!issue) return error(404, 'No matching report was found.');
    let comment = `${REPLY}\n\n${quote(message)}`;
    if (body.zip != null) {
      const path = attachmentPath(body.id, `-reply-${Date.now().toString(36)}`);
      await api.upload(path, body.zip);
      comment += `\n\nFiles: ${api.link(path)}`;
    }
    await api.call(`/issues/${issue.number}/comments`, 'POST', { body: comment });
    return json({ ok: true });
  } catch (failure) {
    return error(502, `The reply could not be posted. ${failure.message}`);
  }
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return error(405, 'Use the toolkit to submit requests.');
    if (!env.REPORTS_REPO || !env.GITHUB_TOKEN) return error(503, 'Relay setup is incomplete.');
    if (!(request.headers.get('User-Agent') || '').startsWith('M2-GUI-Kit/')) {
      return error(403, 'Requests must come from the toolkit.');
    }
    if (Number(request.headers.get('Content-Length')) > 5_608_808) return error(413, 'Request too large.');
    const route = new URL(request.url).pathname.replace(/\/+$/, '') || '/';
    const limiter = route === '/answers' ? env.ANSWER_LIMIT : env.REPORT_LIMIT;
    if (limiter) {
      const allowance = await limiter.limit({ key: request.headers.get('CF-Connecting-IP') || 'unknown' });
      if (!allowance.success) return error(429, 'Too many requests. Try again later.');
    }
    let body;
    try { body = await request.json(); }
    catch { return error(400, 'Request body must be JSON.'); }
    const api = github(env);
    if (route === '/answers') return answers(body, api);
    if (route === '/reply') return reply(body, api);
    return createReport(body, api);
  },
};
