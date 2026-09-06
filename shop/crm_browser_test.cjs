const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE);
const [base, product, order] = process.argv.slice(2);
const output = process.env.SURYA_BROWSER_ARTIFACTS;

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    if (output) fs.mkdirSync(output, {recursive: true});
    for (const route of ['/login/', '/register/']) {
      for (const width of [375, 390, 430, 768, 1024, 1440]) {
        await page.setViewportSize({width, height: 1000});
        const response = await page.goto(base + route, {waitUntil: 'networkidle'});
        assert.equal(response.status(), 200);
        assert(await page.locator('.auth-shell').isVisible());
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} overflows at ${width}`);
        if (output && [390, 1440].includes(width)) {
          await page.locator('.auth-shell').screenshot({path: path.join(output, `${route.split('/')[1]}-${width}.png`)});
        }
      }
    }
    await page.goto(base + '/register/');
    await page.getByLabel('Username', {exact: true}).fill('browser-parent');
    await page.getByLabel('Email', {exact: true}).fill('browser-parent@example.com');
    await page.getByLabel('Password', {exact: true}).fill('Care-browser-fixture-482!');
    await page.getByLabel('Password confirmation', {exact: true}).fill('Care-browser-fixture-482!');
    await page.getByRole('button', {name: 'Show password', exact: true}).click();
    assert.equal(await page.locator('#id_password1').getAttribute('type'), 'text');
    await page.getByRole('button', {name: 'Hide password', exact: true}).click();
    await page.getByRole('button', {name: 'Create my account'}).click();
    await page.waitForURL('**/account/');
    await page.getByRole('button', {name: 'Log out'}).click();
    await page.goto(base + '/crm/login/');
    await page.getByLabel('Username').fill('crm-fixture');
    await page.getByLabel('Password').fill('CRM-browser-fixture-482!');
    await page.getByRole('button', {name: 'Sign in to CRM'}).click();
    await page.waitForURL('**/crm/');
    for (const width of [375, 390, 430, 768, 1024, 1440]) {
      await page.setViewportSize({width, height: 1000});
      for (const route of ['/crm/', '/crm/orders/', '/crm/customers/', '/crm/inventory/', '/crm/reports/', `/crm/orders/${order}/`, `/crm/inventory/${product}/`]) {
        const response = await page.goto(base + route);
        assert.equal(response.status(), 200, route);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${route} overflows at ${width}`);
        if (output && route === '/crm/' && [390, 1440].includes(width)) {
          await page.screenshot({path: path.join(output, `crm-${width}.png`), fullPage: true});
        }
      }
    }
    await page.goto(`${base}/crm/inventory/${product}/`);
    await page.getByLabel('Quantity change').fill('3');
    await page.getByLabel('Reason').fill('Browser fixture supplier delivery');
    await page.getByRole('button', {name: 'Record adjustment'}).click();
    await page.getByText('Stock adjustment saved with an audit record.').waitFor();
    await page.goto(`${base}/crm/orders/${order}/`);
    await page.getByLabel('Internal note').fill('Browser fixture internal note');
    await page.getByRole('button', {name: 'Add internal note'}).click();
    await page.getByLabel('Next status').selectOption('cancelled');
    await page.getByLabel('Reason').fill('Browser fixture cancellation');
    await page.getByRole('button', {name: 'Save status'}).click();
    await page.getByText('Order status saved. Payment status was not changed.').waitFor();
    assert.equal(await page.getByRole('button', {name: 'Save status'}).count(), 0);
    assert.deepEqual(errors, []);
    console.log('Account signup/password toggle, CRM operations, and six responsive widths passed.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
