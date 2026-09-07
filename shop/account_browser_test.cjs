const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const [origin, order] = process.argv.slice(2);
  assert(/^http:\/\/localhost:\d+$/.test(origin), 'Disposable test server required');
  const browser = await chromium.launch({headless: true, executablePath: process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const buyerContext = await browser.newContext();
    const buyer = await buyerContext.newPage();
    await buyer.goto(origin + '/login/');
    await buyer.locator('.auth-form').getByLabel('Email address', {exact:true}).fill('account-browser@example.com');
    await buyer.getByLabel('Password', {exact:true}).fill('Account-fixture-921!');
    await buyer.getByRole('button', {name:'Sign in', exact:true}).click();
    await buyer.waitForURL('**/account/');
    for (const width of [320,360,375,390,412,430,768,1024,1440]) {
      await buyer.setViewportSize({width, height:900});
      for (const route of ['/account/', '/account/orders/', `/account/orders/${order}/`, '/account/pets/', '/account/wishlist/', '/account/addresses/', '/account/profile/', '/account/security/', '/account/support/']) {
        const response = await buyer.goto(origin + route);
        assert.equal(response.status(), 200, route);
        assert.equal(await buyer.locator('.customer-nav').count(), 0);
        assert.equal(await buyer.getByRole('link', {name:'Back to My Account', exact:true}).count(), route === '/account/' ? 0 : 1);
        assert(await buyer.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Account overflow ${width}: ${route}`);
        if (process.env.SURYA_BROWSER_ARTIFACTS && [320,390,1440].includes(width) && [ '/account/', `/account/orders/${order}/` ].includes(route)) {
          fs.mkdirSync(process.env.SURYA_BROWSER_ARTIFACTS, {recursive:true});
          await buyer.locator('.customer-area').screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS, `account-${route === '/account/' ? 'dashboard' : 'order'}-${width}.png`)});
        }
      }
    }
    const staffContext = await browser.newContext();
    const staff = await staffContext.newPage();
    await staff.goto(origin + '/crm/login/');
    await staff.getByLabel('Username').fill('account-staff');
    await staff.getByLabel('Password').fill('Account-fixture-921!');
    await staff.getByRole('button', {name:'Sign in to CRM'}).click();
    await staff.waitForURL('**/crm/');
    for (const width of [320,360,375,390,412,430,1440]) {
      await staff.setViewportSize({width,height:900});
      for (const route of ['/crm/orders/', `/crm/orders/${order}/`, '/crm/support/']) {
        const response = await staff.goto(origin + route);
        assert.equal(response.status(),200);
        assert(await staff.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `CRM overflow ${width}: ${route}`);
      }
    }
    await staff.goto(`${origin}/crm/orders/${order}/`);
    await staff.getByLabel('Next status').selectOption('confirmed');
    await staff.locator('textarea[name="reason"]').fill('PRIVATE staff verification');
    await staff.locator('textarea[name="customer_note"]').fill('We have confirmed your order.');
    await staff.getByRole('button', {name:'Save status',exact:true}).click();
    await buyer.goto(`${origin}/account/orders/${order}/`);
    await buyer.getByText('We have confirmed your order.',{exact:true}).waitFor();
    assert(!(await buyer.locator('body').innerText()).includes('PRIVATE staff verification'));
    await buyer.getByRole('button',{name:'Buy again',exact:true}).click();
    await buyer.waitForURL('**/cart/');
    assert((await buyer.locator('body').innerText()).includes('5 KG'));
    console.log('Nine account widths, seven CRM widths, shared staff-to-customer tracking and exact-pack reorder passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
