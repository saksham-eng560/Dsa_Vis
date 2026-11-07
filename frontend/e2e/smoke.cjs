/**
 * Browser smoke test (Playwright). Requires the backend on :8000 and `npm run dev`.
 *   BASE_URL=http://localhost:5173 node e2e/smoke.cjs
 * Exits non-zero on any failed check or console error.
 */
const { chromium } = require('playwright');

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173';
const PRESETS = ['bubble', 'binary-search', 'bfs', 'reverse-list', 'bst', 'stack', 'two-sum', 'lcs', 'fib-memo', 'js-quick', 'cpp-dfs'];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  const errors = [];
  const failures = [];
  const check = (ok, msg) => (ok ? console.log(`✓ ${msg}`) : failures.push(msg));
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));

  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  check(await page.isVisible('text=See how your code thinks.'), 'welcome screen renders');

  for (const id of PRESETS) {
    await page.selectOption('select[aria-label="Load an example"]', id);
    await page.click('button:has-text("Analyze")');
    await page.waitForFunction(() => !document.querySelector('button.btn-glow')?.textContent?.includes('Analyzing'), null, { timeout: 30000 });
    for (const tab of ['Flowchart', 'Dry Run', 'Complexity', 'Explain']) {
      await page.click(`[role="tab"]:has-text("${tab}")`);
      await page.waitForTimeout(250);
    }
    check((await page.locator('section[aria-label="Analysis results"] [role="alert"]').count()) === 0, `${id}: analysed without errors`);
  }

  await page.selectOption('select[aria-label="Load an example"]', 'bubble');
  await page.click('button:has-text("Analyze")');
  await page.waitForFunction(() => !document.querySelector('button.btn-glow')?.textContent?.includes('Analyzing'));
  await page.click('[role="tab"]:has-text("Dry Run")');
  await page.locator('.monaco-editor .line-numbers', { hasText: /^7$/ }).first().click();
  await page.locator('input[type=range][aria-valuetext$="x"]').fill('5');
  await page.click('button[aria-label="Play"]');
  await page.waitForTimeout(4000);
  const narration = await page.locator('div[aria-live="polite"].glass-inset').first().textContent();
  check(narration?.startsWith('Line 7'), 'playback pauses at breakpoint on line 7');

  check(errors.length === 0, `no console errors (${errors.join(' | ')})`);
  await browser.close();
  if (failures.length) {
    console.error('FAILED:\n- ' + failures.join('\n- '));
    process.exit(1);
  }
})();
