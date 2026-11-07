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
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 950 }, permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await ctx.newPage();
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

  // LeetCode mode: load a problem, add a custom test, judge, then visualise a test case.
  await page.click('[role="radio"]:has-text("LeetCode")');
  await page.fill('input[placeholder^="Problem #"]', '1');
  await page.click('button:has-text("Load")');
  await page.waitForSelector('h3:has-text("1. Two Sum")');
  const solution = 'class Solution:\n    def twoSum(self, nums, target):\n        seen = {}\n' +
    '        for i, x in enumerate(nums):\n            if target - x in seen:\n' +
    '                return [seen[target - x], i]\n            seen[x] = i\n';
  await page.evaluate((c) => navigator.clipboard.writeText(c), solution);
  await page.click('.monaco-editor');
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Control+V');
  await page.click('button:has-text("Add test case")');
  const custom = page.locator('article[aria-label^="Custom test"]').last();
  await custom.locator('textarea').nth(0).fill('[4,5,6,10]');
  await custom.locator('textarea').nth(1).fill('15');
  await custom.locator('textarea').nth(2).fill('[1,3]');
  await page.click('button:has-text("Run all tests")');
  await page.waitForSelector('text=/\\d+ \\/ \\d+ passed/', { timeout: 20000 });
  const summary = await page.locator('text=/\\d+ \\/ \\d+ passed/').first().textContent();
  check(summary?.trim() === '4 / 4 passed', `LeetCode: examples + custom test pass (${summary})`);
  await custom.locator('button:has-text("Visualize")').click();
  await page.waitForSelector('text=Traced from real execution', { timeout: 20000 });
  check(await page.isVisible('code.chip:has-text("nums = [4,5,6,10], target = 15")'), 'LeetCode: custom test drives the dry run');

  check(errors.length === 0, `no console errors (${errors.join(' | ')})`);
  await browser.close();
  if (failures.length) {
    console.error('FAILED:\n- ' + failures.join('\n- '));
    process.exit(1);
  }
})();
