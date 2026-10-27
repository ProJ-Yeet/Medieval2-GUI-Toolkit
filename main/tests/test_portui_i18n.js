// Count-aware nouns in the shared Traits/Ancillaries import summary.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const en = JSON.parse(fs.readFileSync(path.join(root, 'web/i18n/en.json'), 'utf8'));
const summaryId = 'portui.n_nouns_in_source_already_exist_in_dest';

for (const lang of ['en', 'zh-Hans', 'ru']) {
  const cat = lang === 'en' ? {} : JSON.parse(fs.readFileSync(path.join(root,
    `dev/i18n/${lang}.json`), 'utf8'));
  const context = vm.createContext({
    window: {I18N_BOOT: {lang, en, cat}},
    document: {documentElement: {}, querySelectorAll: () => []},
    console,
    esc: String,
    state: {mods: [{name: 'Source'}, {name: 'Dest'}]},
    summaryId,
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'web/js/i18n.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(root, 'web/js/portui.js'), 'utf8'), context);
  vm.runInContext(`
    const originalTtN = ttN;
    const stopAfterSummary = {};
    ttN = function(id, n, params) {
      const text = originalTtN(id, n, params);
      if (id === summaryId) {
        globalThis.summary = {text, params};
        throw stopAfterSummary;
      }
      return text;
    };
  `, context);
  for (const kind of ['traits', 'ancillaries']) {
    for (const count of [0, 1, 2, 5, 21, 22]) {
      context.testKind = kind;
      context.testCount = count;
      vm.runInContext(`
        portState = {kind: testKind, source: 'Source', dest: 'Dest', sel: new Set(),
          ov: {count: testCount, source: 'Source', dest: 'Dest', already: 0, records: []}};
        globalThis.expectedNoun = portNoun(testKind, testCount);
        try { portRender(); } catch (err) { if (err !== stopAfterSummary) throw err; }
      `, context);
      assert.strictEqual(context.summary.params.noun, context.expectedNoun,
        `${lang}/${kind}/${count}: noun must use the actual count`);
      assert(!/\{\w+\}/.test(context.summary.text), `${lang}/${kind}/${count}: unfilled placeholder`);
      if (lang === 'en') {
        assert(context.summary.text.includes(count === 1 ?
          (kind === 'traits' ? ' trait in ' : ' ancillary in ') :
          (kind === 'traits' ? ' traits in ' : ' ancillaries in ')));
      }
    }
  }
}
console.log('36 import summaries passed in English, Simplified Chinese and Russian');
