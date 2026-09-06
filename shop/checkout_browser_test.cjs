// Run only against Django's disposable LiveServerTestCase database.
const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const origin = process.argv[2];
  if (!/^http:\/\/localhost:\d+$/.test(origin)) throw Error('Expected disposable local test server');
  const browser = await chromium.launch({headless: true, ...(process.env.SURYA_BROWSER_EXECUTABLE ? {executablePath: process.env.SURYA_BROWSER_EXECUTABLE} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/product/browser-checkout-fixture/', {waitUntil: 'domcontentloaded'});
    await page.locator('.product-form [name="quantity"]').fill('2');
    await page.locator('.product-form button[type="submit"]').click();
    await page.getByRole('link', {name: 'Proceed to checkout'}).click();
    const values = {email:'browser-test@example.com',phone:'9999999999',shipping_name:'Test Buyer',shipping_address_line_1:'1 Test Street',shipping_city:'Mumbai',shipping_state:'Maharashtra',shipping_postal_code:'400001'};
    for (const [name, value] of Object.entries(values)) await page.locator(`[data-checkout-form] [name="${name}"]`).fill(value);
    await page.locator('[name="billing_same_as_shipping"]').check();
    await page.locator('[name="terms"]').check();
    for (const width of [390, 1440]) {
      await page.setViewportSize({width,height:900});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    const payload = await page.locator('[data-checkout-form]').evaluate(form => Object.fromEntries(new FormData(form)));
    await page.getByRole('button', {name: 'Place order', exact:true}).click();
    await page.waitForURL('**/checkout/confirmation/**');
    const receipt = page.url();
    assert.match(await page.locator('body').innerText(), /Order Placed Successfully/);
    const duplicate = await page.request.post(origin + '/checkout/', {form: payload, headers: {Referer: origin + '/checkout/'}});
    assert.equal(duplicate.status(), 200); assert.equal(duplicate.url(), receipt);
    const stranger = await browser.newContext();
    assert.equal((await stranger.request.get(receipt)).status(), 404);
    await stranger.close();
    assert.deepEqual(errors, []);
    console.log('Mobile/desktop checkout, CSRF form submit, duplicate POST and private receipt passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
