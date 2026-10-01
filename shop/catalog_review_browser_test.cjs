// Disposable test database only. No real staff account or product is modified.
const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const [origin, product] = process.argv.slice(2);
  if (!/^http:\/\/localhost:\d+$/.test(origin)) throw Error('Disposable local test server required');
  const browser = await chromium.launch({headless:true, executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    // Fixture image: avoid depending on an external image server.
    await page.route('https://example.com/**', route => route.fulfill({contentType:'image/svg+xml', body:'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="140"><rect width="120" height="140" fill="#dcefe2"/><text x="12" y="75" fill="#174c37">Test product</text></svg>'}));
    await page.goto(origin + '/crm/login/');
    await page.getByLabel('Username').fill('review-fixture');
    await page.getByLabel('Password').fill('Review-fixture-482!');
    await page.getByRole('button', {name:'Sign in to CRM'}).click();
    await page.waitForURL('**/crm/');
    await page.goto(origin + `/crm/inventory/${product}/review/`);
    for (const width of [320,360,375,390,412,430,768,1440]) {
      await page.setViewportSize({width,height:1000});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Review overflow at ${width}`);
      if (process.env.SURYA_BROWSER_ARTIFACTS && [320,390,1440].includes(width)) {
        fs.mkdirSync(process.env.SURYA_BROWSER_ARTIFACTS, {recursive:true});
        await page.locator('main').screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS, `catalog-review-${width}.png`)});
      }
    }
    await page.locator('#id_decision').selectOption('approved');
    await page.locator('#id_evidence').fill('Fixture supplier price list and dated warehouse stock count.');
    await page.getByRole('button',{name:'Save review decision'}).click();
    await page.getByText('Complete all three checks.',{exact:false}).waitFor();
    for (const name of ['identity','prices','inventory']) await page.locator(`#id_${name}`).check();
    await page.getByRole('button',{name:'Save review decision'}).click();
    await page.getByText('Reviewed',{exact:true}).waitFor();
    await page.locator('#id_decision').selectOption('held');
    await page.locator('#id_evidence').fill('Fixture hold: supplier document requires another verification.');
    await page.getByRole('button',{name:'Save review decision'}).click();
    await page.getByText('Needs review',{exact:true}).waitFor();
    assert.deepEqual(errors, []);
    console.log('Review-only CRM: eight widths, required confirmations, approval and hold passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
