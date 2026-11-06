// Offline contract checks for the independently written report relay.
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { readFile } from 'node:fs/promises';

// An explicit source import avoids looking for package scope above this tree.
const source = await readFile(new URL('./worker.js', import.meta.url), 'utf8');
const { default: worker } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

const env = { REPORTS_REPO: 'example/private-reports', GITHUB_TOKEN: 'test-secret' };
const root = 'https://api.github.com/repos/example/private-reports';
const id = 'R-20261106-ABC123';
const marker = '**Reply from the reporter**';
const zip = 'UEsDB'; // Encoded-text screening deliberately accepts this short string.
const cap = 5_592_424;
const NativeDate = Date;
const now = NativeDate.parse('2026-11-06T23:59:58Z');
const originalFetch = globalThis.fetch;
const cryptoDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
let checks = 0;
let calls;
let pending;
let mockFailure;

function step(path, method = 'GET', response = {}, status = 200, inspect) {
  return { path, method, response, status, inspect };
}
function search(report = id, items = []) {
  return step(url => {
    assert.equal(url.origin + url.pathname, 'https://api.github.com/search/issues');
    assert.deepEqual([...url.searchParams], [
      ['q', `repo:${env.REPORTS_REPO} is:issue in:title "${report}"`], ['per_page', '5'],
    ]);
  }, 'GET', { items });
}
const issue = (report = id, number = 7, extra = {}) => ({
  number, title: `${report}: [Bug] report`, state: 'closed', ...extra,
});
const hint = (report = id, number = 7, extra = {}) => step(`/issues/${number}`, 'GET', issue(report, number, extra));
const comments = (number = 7, values = []) => step(`/issues/${number}/comments?per_page=100`, 'GET', values);

function mock(sequence = []) {
  calls = [];
  pending = [...sequence];
  mockFailure = undefined;
  globalThis.fetch = async (input, options = {}) => {
    const url = new URL(input);
    const body = options.body === undefined ? undefined : JSON.parse(options.body);
    calls.push({ url, method: options.method, body });
    const expected = pending.shift();
    try {
    assert.ok(expected, `Unexpected GitHub call: ${options.method} ${url}`);
    if (typeof expected.path === 'function') expected.path(url);
    else assert.equal(url.href, root + expected.path);
    assert.equal(options.method, expected.method);
    const headers = new Headers(options.headers);
    assert.equal(headers.get('authorization'), 'Bearer test-secret');
    assert.equal(headers.get('accept'), 'application/vnd.github+json');
    assert.match(headers.get('user-agent'), /relay/i);
    assert.equal(headers.get('x-github-api-version'), '2022-11-28');
    if (expected.method === 'GET') assert.equal(body, undefined);
    expected.inspect?.(body, url);
    } catch (failure) {
      mockFailure = failure;
      throw failure;
    }
    if (expected.response instanceof Error) throw expected.response;
    if (expected.response === 'invalid JSON') return new Response('not JSON');
    return new Response(JSON.stringify(expected.response), { status: expected.status });
  };
}

async function request(path = '/', body = {}, options = {}) {
  const headers = { 'User-Agent': 'M2-GUI-Kit/test', ...options.headers };
  for (const [key, value] of Object.entries(headers)) if (value === null) delete headers[key];
  const method = options.method || 'POST';
  const req = new Request(`https://relay.test${path}`, {
    method, headers,
    ...(['GET', 'HEAD'].includes(method) ? {} : { body: options.raw ?? JSON.stringify(body) }),
  });
  return worker.fetch(req, { ...env, ...options.env });
}
async function expectResponse(path, body, status = 200, expected, options) {
  const response = await request(path, body, options);
  if (mockFailure) throw mockFailure;
  assert.equal(response.status, status);
  assert.equal(response.headers.get('content-type'), 'application/json');
  assert.equal(response.headers.get('set-cookie'), null);
  const value = await response.json();
  if (status !== 200) {
    assert.deepEqual(Object.keys(value), ['error']);
    assert.equal(typeof value.error, 'string');
    assert.ok(value.error.length);
  }
  if (expected !== undefined) assert.deepEqual(value, expected);
  assert.equal(pending.length, 0, 'All expected GitHub calls must occur');
  return value;
}
async function test(name, run) {
  mock();
  await run();
  if (mockFailure) throw mockFailure;
  assert.equal(pending.length, 0);
  checks++;
  console.log(`ok ${checks} - ${name}`);
}
const sanitize = (value, length) => String(value || '').slice(0, length).replace(/[<>]/g, '').replace(/@/g, '@\u200b');
const quoted = value => value.split('\n').map(line => `> ${line}`).join('\n');
const initialPath = `reports/2026-11-06/R-20261106-1234AB.zip`;
const fileUrl = path => `https://github.com/${env.REPORTS_REPO}/blob/HEAD/${path}`;
function upload(path, content = zip, response = {}) {
  return step(`/contents/${path}`, 'PUT', response, 200, body => {
    assert.deepEqual(Object.keys(body).sort(), ['content', 'message']);
    assert.equal(body.content, content);
    assert.equal(typeof body.message, 'string');
    assert.ok(body.message.length);
  });
}
function filing(payload, response = { number: 7 }) {
  return [upload(initialPath, payload.zip), step('/issues', 'POST', response, 200, body => {
    const idea = payload.kind === 'idea';
    const metadata = payload.info && typeof payload.info === 'object' && !Array.isArray(payload.info)
      ? Object.entries(payload.info).slice(0, 12).map(([key, value]) => `- **${sanitize(key, 40)}**: ${sanitize(value, 200)}`).join('\n') : '';
    assert.deepEqual(body, {
      title: `R-20261106-1234AB: [${idea ? 'Idea' : 'Bug'}] ${sanitize(payload.message, 80).split(/\r?\n/)[0].trim() || 'No description'}`,
      labels: [idea ? 'idea' : 'bug'],
      body: [idea ? '**The idea**' : '**What happened**', quoted(sanitize(payload.message, 4000)),
        `**Contact**: ${sanitize(payload.contact, 200) || 'Not supplied'}`, ...(metadata ? [metadata] : []),
        `The files: ${fileUrl(initialPath)}`].join('\n\n'),
    });
    assert.ok(!JSON.stringify(body).includes('test-secret'));
    assert.ok(!JSON.stringify(body).includes('192.0.2.1'));
  })];
}

try {
  globalThis.Date = class extends NativeDate {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  };
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: {
    getRandomValues(array) {
      assert.equal(array.byteLength, 3);
      return array.set([0x12, 0x34, 0xab]), array;
    }, subtle: webcrypto.subtle,
  } });

  await test('method rejection precedes all other validation', async () => {
    for (const method of ['GET', 'HEAD', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']) {
      await expectResponse('/answers', {}, 405, undefined, {
        method, env: { REPORTS_REPO: '' }, headers: { 'User-Agent': null, 'Content-Length': '99999999' },
      });
    }
  });
  await test('configuration precedes agent and size validation', async () => {
    for (const key of ['REPORTS_REPO', 'GITHUB_TOKEN']) for (const value of ['', undefined]) {
      await expectResponse('/', {}, 503, undefined, {
        env: { [key]: value }, headers: { 'User-Agent': null, 'Content-Length': '99999999' },
      });
    }
  });
  await test('case-sensitive toolkit prefix precedes size validation', async () => {
    for (const agent of [null, '', 'm2-gui-kit/test', 'prefix M2-GUI-Kit/test', 'M2-GUI-Kit']) {
      await expectResponse('/', {}, 403, undefined, { headers: { 'User-Agent': agent, 'Content-Length': '99999999' } });
    }
  });
  await test('declared body size, inclusive boundary, absent and unusable headers', async () => {
    await expectResponse('/answers', {}, 413, undefined, { headers: { 'Content-Length': '5608809' } });
    for (const size of ['5608808', null, 'unusable']) {
      await expectResponse('/answers', {}, 200, { answers: {} }, { headers: { 'Content-Length': size } });
    }
    await expectResponse('/answers', {}, 200, { answers: {} }, { raw: JSON.stringify({ ignored: 'x'.repeat(5_608_809) }) });
  });
  await test('optional rate bindings use separate scopes and shared address fallback', async () => {
    const keys = [];
    const reportLimit = { limit: async value => { keys.push(['report', value]); return { success: false }; } };
    const answerLimit = { limit: async value => { keys.push(['answer', value]); return { success: false }; } };
    for (const path of ['/', '/reply/', '/unknown', '/answers/']) {
      await expectResponse(path, {}, 429, undefined, { raw: '{', env: { REPORT_LIMIT: reportLimit, ANSWER_LIMIT: answerLimit } });
    }
    await expectResponse('/reply', {}, 429, undefined, {
      env: { REPORT_LIMIT: reportLimit }, headers: { 'CF-Connecting-IP': '192.0.2.1' },
    });
    assert.deepEqual(keys.map(([scope]) => scope), ['report', 'report', 'report', 'answer', 'report']);
    const fallback = keys[0][1].key;
    assert.equal(typeof fallback, 'string');
    for (const [, value] of keys.slice(0, 4)) assert.deepEqual(value, { key: fallback });
    assert.deepEqual(keys[4][1], { key: '192.0.2.1' });
    await expectResponse('/answers', {}, 200, { answers: {} }, { env: { ANSWER_LIMIT: { limit: async () => ({ success: true }) } } });
  });
  await test('malformed JSON returns 400 on every route and can consume rate allowance', async () => {
    let count = 0;
    const binding = { limit: async () => { count++; return { success: true }; } };
    for (const path of ['/', '/answers', '/reply']) {
      await expectResponse(path, {}, 400, undefined, { raw: '{', env: { REPORT_LIMIT: binding, ANSWER_LIMIT: binding } });
    }
    assert.equal(count, 3);
  });
  await test('uncontracted null bodies and limiter failures can reject', async () => {
    for (const path of ['/', '/answers', '/reply']) await assert.rejects(request(path, null), TypeError);
    await assert.rejects(request('/', {}, { env: { REPORT_LIMIT: { limit: async () => { throw new Error('binding failed'); } } } }), /binding failed/);
  });
  await test('invalid report ZIP variants', async () => {
    for (const value of [undefined, null, '', 42, {}, 'UEsDA', 'UEsDB_', 'UEsDB\n', 'UEsDBé', 'UEsDB' + 'A'.repeat(cap - 4)]) {
      await expectResponse('/', { zip: value }, 400);
    }
  });
  await test('report routes, trailing slashes, queries, and category selection', async () => {
    for (const [path, kind] of [['/', 'bug'], ['////', 'idea'], ['/other?route=answers', 'Idea'], ['/?route=reply', null]]) {
      const payload = { zip, kind, message: '<hello> @all\n**Markdown**', contact: 'a@b', info: { version: '1', mods: 'one, two' } };
      mock(filing(payload));
      await expectResponse(path, payload, 200, { id: 'R-20261106-1234AB', issue: 7 }, { headers: { 'Content-Type': 'text/plain', 'CF-Connecting-IP': '192.0.2.1' } });
    }
  });
  await test('empty reports and nonobject metadata, usable issue-number fallback', async () => {
    for (const info of [undefined, null, false, 'text', 4, []]) {
      const payload = { zip, info, message: false, contact: 0 };
      mock(filing(payload, {}));
      await expectResponse('/', payload, 200, { id: 'R-20261106-1234AB', issue: 0 });
    }
    for (const number of [null, '7', 0, -1, 2.5]) {
      mock(filing({ zip }, { number }));
      await expectResponse('/', { zip }, 200, { id: 'R-20261106-1234AB', issue: 0 });
    }
  });
  await test('report limits use UTF-16 before sanitizing, with ordered metadata capped at twelve', async () => {
    const info = Object.fromEntries(Array.from({ length: 14 }, (_, i) => [`${i}<@${'k'.repeat(50)}`, `${i}>@${'😀'.repeat(150)}`]));
    const payload = { zip, message: '<@' + '😀'.repeat(2100), contact: '<@' + 'c'.repeat(250), info };
    mock(filing(payload));
    await expectResponse('/', payload, 200, { id: 'R-20261106-1234AB', issue: 7 });
    for (const message of [123, true, { example: true }, ['a', 'b']]) {
      mock(filing({ zip, message }));
      await expectResponse('/', { zip, message });
    }
  });
  await test('ZIP exact maximum and permissive padding forwarded unchanged', async () => {
    for (const value of ['UEsDB=+/===', 'UEsDB' + 'A'.repeat(cap - 5)]) {
      mock(filing({ zip: value }));
      await expectResponse('/', { zip: value });
    }
  });
  await test('upload and issue HTTP, network, and JSON failures return filing guidance without rollback', async () => {
    for (const stage of ['upload', 'issue']) for (const failure of ['http', 'network', 'json']) {
      const bad = step(stage === 'upload' ? `/contents/${initialPath}` : '/issues', stage === 'upload' ? 'PUT' : 'POST',
        failure === 'network' ? new Error('offline') : failure === 'json' ? 'invalid JSON' : {}, failure === 'http' ? 403 : 200);
      mock(stage === 'upload' ? [bad] : [upload(initialPath), bad]);
      const result = await expectResponse('/', { zip }, 502);
      assert.match(result.error, /could not be filed/i);
      assert.match(result.error, /keep.*ZIP.*another submission channel/i);
      assert.equal(calls.length, stage === 'upload' ? 1 : 2);
    }
  });
  await test('answers accepts missing or non-array reports and ignores invalid entries', async () => {
    for (const body of [{}, { reports: null }, { reports: {} }, { reports: 'x' }, { reports: [null, {}, false, '', { issue: 7 },
      ...['R-20261106-abc123', 'R-2026116-ABC123', id + 'x', 'x' + id, 7].map(value => ({ id: value }))] }]) {
      await expectResponse('/answers/?route=reply', body, 200, { answers: {} });
    }
  });
  await test('hint resolution and comment display preserve order and classification', async () => {
    const values = [
      { body: ' \r\nMaintainer @user <tag>\r\n ', created_at: '2026-11-06T00:00:00Z' },
      { body: marker + '\r\n\r\n> First\r\n> > nested\r\n\r\nFiles: https://github.com/example/file.zip\r\n' },
      { body: marker + '\n\n> keep\n> Files: https://example.com/user-text' },
      { body: marker + '\n\n> ' }, { body: ' \r\n' }, {},
      { body: ' ' + marker + '\n> author because marker is not first' },
      { body: '😀'.repeat(5000) },
    ];
    mock([hint(id, 7, { state_reason: 'completed', body: 'not a comment' }), comments(7, values)]);
    await expectResponse('/answers/', { reports: [{ id, issue: 7 }] }, 200, { answers: { [id]: {
      issue: 7, state: 'closed', reason: 'completed', messages: [
        { from: 'author', text: 'Maintainer @user <tag>', at: '2026-11-06T00:00:00Z' },
        { from: 'you', text: 'First\n> nested', at: '' },
        { from: 'you', text: 'keep\nFiles: https://example.com/user-text', at: '' },
        { from: 'author', text: marker + '\n> author because marker is not first', at: '' },
        { from: 'author', text: '😀'.repeat(4000), at: '' },
      ],
    } } });
  });
  await test('unusable hints bypass direct lookup, exact search matching and impossible date allowed', async () => {
    const strange = 'R-99999999-FFFFFF';
    for (const hintValue of [undefined, '7', 0, -1, 1.5, true]) {
      mock([search(strange, [issue(strange + 'X', 1), { ...issue(strange, 2), title: `prefix ${strange}:` }, issue(strange, 8)]), comments(8)]);
      await expectResponse('/answers', { reports: [{ id: strange, issue: hintValue }] }, 200, {
        answers: { [strange]: { issue: 8, state: 'closed', reason: '', messages: [] } },
      });
    }
  });
  await test('unavailable or mismatched hints fall back to identifier search', async () => {
    for (const first of [hint('R-20261106-000000'), step('/issues/7', 'GET', {}, 404), step('/issues/7', 'GET', new Error('network')), step('/issues/7', 'GET', 'invalid JSON')]) {
      mock([first, search(id, [issue()]), comments()]);
      await expectResponse('/answers', { reports: [{ id, issue: 7 }] }, 200, {
        answers: { [id]: { issue: 7, state: 'closed', reason: '', messages: [] } },
      });
    }
  });
  await test('search considers no more than five candidates and requires exact identifier colon', async () => {
    const wrong = ['x' + id + ':', id + 'X:', id, id.toLowerCase() + ':', id + ' :'];
    mock([search(id, [...wrong.map((title, i) => ({ title, number: i + 1 })), issue()])]);
    await expectResponse('/answers', { reports: [{ id }] }, 200, { answers: {} });
  });
  await test('answer lookup and comments failures omit only affected reports', async () => {
    const other = 'R-20261106-000001';
    for (const failure of ['http', 'network', 'json', 'absent', 'comments']) {
      let steps;
      if (failure === 'comments') steps = [hint(), step('/issues/7/comments?per_page=100', 'GET', {}, 500)];
      else if (failure === 'absent') steps = [search()];
      else {
        const bad = search();
        bad.status = failure === 'http' ? 500 : 200;
        bad.response = failure === 'network' ? new Error('offline') : failure === 'json' ? 'invalid JSON' : {};
        steps = [bad];
      }
      mock([...steps, hint(other, 8), comments(8)]);
      await expectResponse('/answers', { reports: [{ id, ...(failure === 'comments' ? { issue: 7 } : {}) }, { id: other, issue: 8 }] }, 200, {
        answers: { [other]: { issue: 8, state: 'closed', reason: '', messages: [] } },
      });
    }
    for (const response of [new Error('offline'), 'invalid JSON']) {
      mock([hint(), step('/issues/7/comments?per_page=100', 'GET', response)]);
      await expectResponse('/answers', { reports: [{ id, issue: 7 }] }, 200, { answers: {} });
    }
  });
  await test('only first thirty entries eligible, duplicates occupy one response key', async () => {
    mock();
    await expectResponse('/answers', { reports: [...Array(30).fill(null), { id, issue: 7 }] }, 200, { answers: {} });
    mock([hint(), comments(), hint(), comments()]);
    await expectResponse('/answers', { reports: [{ id, issue: 7 }, { id, issue: 7 }] }, 200, {
      answers: { [id]: { issue: 7, state: 'closed', reason: '', messages: [] } },
    });
  });
  await test('reply validation covers invalid id, empty sanitized text, and rejected attachments', async () => {
    for (const value of [undefined, null, '', 7, 'R-20261106-abc123', id + 'x']) {
      await expectResponse('/reply', { id: value, message: 'hello' }, 400);
    }
    for (const message of [undefined, null, '', false, 0, ' \r\n ', '<>']) {
      await expectResponse('/reply', { id, message }, 400);
    }
    for (const value of ['', false, 3, {}, 'not a zip', 'UEsDB_', 'UEsDB\n', 'UEsDB' + 'A'.repeat(cap - 4)]) {
      await expectResponse('/reply', { id, message: 'hi', zip: value }, 400);
    }
  });
  await test('reply without attachment or with null posts to closed issue without reopening', async () => {
    for (const attachment of [{}, { zip: null }]) {
      mock([hint(), step('/issues/7/comments', 'POST', {}, 200, body => {
        assert.deepEqual(body, { body: marker + '\n\n> hello @\u200buser\n> **bold**' });
      })]);
      await expectResponse('/reply/?route=answers', { id, issue: 7, message: '  <hello> @user\n**bold**  ', ...attachment }, 200, { ok: true });
    }
  });
  await test('reply with ZIP uses original identifier date and base36 current milliseconds', async () => {
    const old = 'R-20200102-000ABC';
    const path = `reports/2020-01-02/${old}-reply-${now.toString(36)}.zip`;
    const message = '<@' + '😀'.repeat(2200);
    mock([search(old, [issue(old, 9)]), upload(path), step('/issues/9/comments', 'POST', {}, 200, body => {
      assert.deepEqual(body, { body: `${marker}\n\n${quoted(sanitize(message, 4000).trim())}\n\nFiles: ${fileUrl(path)}` });
    })]);
    await expectResponse('/reply', { id: old, issue: '9', message, zip }, 200, { ok: true });
  });
  await test('reply accepts ordinary value stringification', async () => {
    mock([hint(), step('/issues/7/comments', 'POST', {}, 200, body => assert.deepEqual(body, { body: marker + '\n\n> 123' }))]);
    await expectResponse('/reply', { id, issue: 7, message: 123 }, 200, { ok: true });
  });
  await test('reply missing match is 404, including hint mismatch fallback', async () => {
    mock([hint('R-20261106-000000'), search()]);
    await expectResponse('/reply', { id, issue: 7, message: 'hi' }, 404);
  });
  await test('reply lookup, upload and comment failures return 502 without rollback', async () => {
    const path = `reports/2026-11-06/${id}-reply-${now.toString(36)}.zip`;
    for (const stage of ['search', 'upload', 'comment']) for (const failure of ['http', 'network', 'json']) {
      const response = failure === 'network' ? new Error('offline') : failure === 'json' ? 'invalid JSON' : {};
      const status = failure === 'http' ? 500 : 200;
      let sequence;
      if (stage === 'search') {
        const bad = search(); bad.response = response; bad.status = status; sequence = [bad];
      } else if (stage === 'upload') sequence = [hint(), step(`/contents/${path}`, 'PUT', response, status)];
      else sequence = [hint(), upload(path), step('/issues/7/comments', 'POST', response, status)];
      mock(sequence);
      await expectResponse('/reply', { id, ...(stage === 'search' ? {} : { issue: 7 }), message: 'hi', zip }, 502);
      assert.equal(calls.length, stage === 'search' ? 1 : stage === 'upload' ? 2 : 3);
    }
  });
  console.log(`Passed ${checks} contract groups. All GitHub calls were mocked.`);
} finally {
  globalThis.fetch = originalFetch;
  globalThis.Date = NativeDate;
  if (cryptoDescriptor) Object.defineProperty(globalThis, 'crypto', cryptoDescriptor);
  else delete globalThis.crypto;
}
