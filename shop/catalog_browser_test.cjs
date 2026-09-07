// Runs only against a disposable Django test database, never the user's inventory.
const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const [origin, product] = process.argv.slice(2);
  if (!/^http:\/\/localhost:\d+$/.test(origin)) throw Error('Disposable test server required');
  const output = process.env.SURYA_BROWSER_ARTIFACTS;
  const browser = await chromium.launch({headless: true, executablePath: process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/crm/login/');
    await page.getByLabel('Username').fill('catalog-fixture');
    await page.getByLabel('Password').fill('Catalog-fixture-482!');
    await page.getByRole('button', {name: 'Sign in to CRM'}).click();
    await page.waitForURL('**/crm/');
    for (const route of ['/crm/inventory/', `/crm/inventory/${product}/edit/`]) {
      await page.goto(origin + route);
      for (const width of [375,390,430,768,1024,1440]) {
        await page.setViewportSize({width, height:1000});
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} overflow at ${width}`);
        if (output && [390,1440].includes(width)) {
          fs.mkdirSync(output, {recursive: true});
          await page.locator('main').screenshot({path:path.join(output, `catalog-${route.endsWith('/edit/') ? 'editor' : 'inventory'}-${width}.png`)});
        }
      }
    }
    await page.getByRole('link', {name:'Edit pack', exact:true}).click();
    await page.getByLabel('Selling pack price (₹)').fill('349');
    await page.getByRole('button', {name:'Save pack', exact:true}).click();
    await page.getByText('Pack details saved. Stock and past orders are unchanged.').waitFor();
    await page.goto(origin + '/crm/inventory/');
    await page.getByRole('link', {name:'Add product', exact:false}).click();
    await page.locator('#id_name').fill('New daily supplement');
    await page.getByLabel('URL handle').fill('browser-catalog-new');
    await page.getByLabel('Primary category').selectOption({label:'Dog'});
    await page.locator('#id_base_price').fill('250');
    await page.locator('#id_selling_price').fill('200');
    await page.getByRole('button', {name:'Create product', exact:true}).click();
    await page.getByText('Product created. Use Adjust stock to record its opening quantity before selling.').waitFor();
    const editor = page.url();
    await page.getByRole('link', {name:'Archive from store', exact:true}).click();
    await page.getByLabel('Reason').fill('Browser fixture archive');
    await page.getByRole('button', {name:'Confirm archive'}).click();
    await page.goto(editor);
    await page.getByRole('link', {name:'Restore to store'}).click();
    await page.getByLabel('Reason').fill('Browser fixture restore');
    await page.getByRole('button', {name:'Confirm restore'}).click();
    await page.getByText('Restored product. Order history and stock records are preserved.').waitFor();
    assert.deepEqual(errors, []);
    console.log('Catalog: six widths, create, variant pricing, archive and restore passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
