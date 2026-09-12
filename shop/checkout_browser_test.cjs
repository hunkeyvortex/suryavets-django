// Run only against Django's disposable LiveServerTestCase database.
const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const origin = process.argv[2];
  const coupons = process.argv[3] === 'coupons';
  const output = process.env.SURYA_BROWSER_ARTIFACTS;
  if (!/^http:\/\/localhost:\d+$/.test(origin)) throw Error('Expected disposable local test server');
  const browser = await chromium.launch({headless: true, ...(process.env.SURYA_BROWSER_EXECUTABLE ? {executablePath: process.env.SURYA_BROWSER_EXECUTABLE} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 390, height: 844}});
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    if (coupons) {
      await page.goto(origin + '/crm/login/');
      await page.getByLabel('Username').fill('coupon-browser-staff');
      await page.getByLabel('Password').fill('Coupon-browser-fixture-482!');
      await page.getByRole('button', {name: 'Sign in to CRM'}).click();
      await page.waitForURL('**/crm/');
      await page.goto(origin + '/crm/coupons/new/');
      await page.locator('#id_code').fill('browser15');
      await page.locator('#id_name').fill('Browser-only campaign');
      await page.locator('#id_kind').selectOption('percent');
      await page.locator('#id_value').fill('10');
      await page.locator('#id_max_uses').fill('1');
      await page.locator('#id_is_active').check();
      await page.getByRole('button', {name: 'Save coupon'}).click();
      await page.getByText('Coupon saved. Previous orders keep their original discount.').waitFor();
      await page.locator('#id_value').fill('15');
      await page.getByRole('button', {name: 'Save coupon'}).click();
      await page.getByText('Coupon saved. Previous orders keep their original discount.').waitFor();
      for (const width of [390, 1440]) {
        await page.setViewportSize({width, height: 1000});
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        if (output) {
          fs.mkdirSync(output, {recursive: true});
          await page.screenshot({path: path.join(output, `coupon-crm-${width}.png`), fullPage: true});
        }
      }
      await page.getByRole('button', {name: 'Sign out'}).click();
    }
    await page.goto(origin + '/cart/');
    await page.locator('.basket-empty').waitFor();
    if (output) {
      fs.mkdirSync(output, {recursive: true});
      await page.locator('.basket-shell').screenshot({path: path.join(output, 'basket-empty-390.png')});
    }
    await page.goto(origin + '/product/browser-checkout-fixture/', {waitUntil: 'domcontentloaded'});
    await page.locator('.product-form [name="quantity"]').fill('2');
    await page.locator('.product-form [data-add-to-cart]').click();
    await page.locator('.basket-product').waitFor();
    await page.locator('[data-step="1"]').click();
    assert.equal(await page.locator('[data-basket-quantity] [name="quantity"]').inputValue(), '3');
    await page.getByRole('button', {name: 'Update', exact: true}).click();
    await page.waitForURL('**/cart/');
    assert.match(await page.locator('[data-basket-total]').innerText(), /320/);
    await page.locator('[data-step="-1"]').click();
    await page.getByRole('button', {name: 'Update', exact: true}).click();
    await page.waitForURL('**/cart/');
    assert.match(await page.locator('[data-basket-total]').innerText(), /230/);
    for (const width of [320, 360, 375, 390, 412, 430, 768, 1024, 1440]) {
      await page.setViewportSize({width, height: 900});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      const items = await page.locator('.basket-products').boundingBox();
      const summary = await page.locator('.basket-summary').boundingBox();
      if (width < 901) assert(summary.y > items.y + items.height, 'Mobile items must precede the summary');
      if (output && [390, 1440].includes(width)) {
        await page.locator('.basket-shell').screenshot({path: path.join(output, `basket-${width}.png`)});
      }
    }
    await page.getByRole('button', {name: 'Remove Browser checkout fixture', exact: true}).click();
    await page.locator('.basket-empty').waitFor();
    await page.goto(origin + '/product/browser-checkout-fixture/');
    await page.locator('.product-form [name="quantity"]').fill('2');
    await page.locator('.product-form [data-add-to-cart]').click();
    await page.getByRole('link', {name: 'Proceed to checkout'}).click();
    assert(await page.getByRole('radio', {name: 'Cash on Delivery (COD)', exact: false}).isChecked());
    assert(await page.getByRole('radio', {name: 'Online Payment', exact: false}).isDisabled());
    const values = {email:'browser-test@example.com',phone:'9999999999',shipping_name:'Test Buyer',shipping_address_line_1:'1 Test Street',shipping_city:'Mumbai',shipping_state:'Maharashtra',shipping_postal_code:'400001'};
    for (const [name, value] of Object.entries(values)) await page.locator(`[data-checkout-form] [name="${name}"]`).fill(value);
    await page.locator('[name="billing_same_as_shipping"]').check();
    await page.locator('[name="terms"]').check();
    if (coupons) {
      await page.locator('[name="coupon_code"]').fill('browser15');
      await page.getByRole('button', {name: 'Apply', exact: true}).click();
      await page.locator('.coupon-applied').waitFor();
      assert.equal(await page.locator('[name="shipping_name"]').inputValue(), 'Test Buyer');
      assert.match(await page.locator('[data-order-total]').innerText(), /203/);
      await page.getByRole('button', {name: 'Remove coupon'}).click();
      assert.match(await page.locator('[data-order-total]').innerText(), /230/);
      await page.locator('[name="coupon_code"]').fill('BROWSER15');
      await page.getByRole('button', {name: 'Apply', exact: true}).click();
      await page.locator('.coupon-applied').waitFor();
      await page.locator('[name="billing_same_as_shipping"]').uncheck();
      assert(await page.locator('[data-billing-fields]').isVisible());
      await page.locator('[name="billing_same_as_shipping"]').check();
      assert(!(await page.locator('[data-billing-fields]').isVisible()));
    }
    for (const width of (coupons ? [375, 390, 430, 768, 1024, 1440] : [390, 1440])) {
      await page.setViewportSize({width,height:900});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      if (coupons && output && [390, 1440].includes(width)) {
        await page.locator('.skip-link').focus();
        assert.equal(await page.locator('.skip-link').evaluate(el => getComputedStyle(el).clipPath), 'none');
        await page.locator('[name="shipping_name"]').focus();
        if (width === 1440) assert(await page.locator('.checkout-shell').evaluate(el => el.getBoundingClientRect().width >= 1100), 'Desktop checkout should use its full content width');
        await page.locator('.checkout-shell').screenshot({path: path.join(output, `checkout-${width}.png`)});
      }
    }
    const payload = await page.locator('[data-checkout-form]').evaluate(form => Object.fromEntries(new FormData(form)));
    await page.getByRole('button', {name: 'Place order', exact:true}).click();
    await page.waitForURL('**/checkout/confirmation/**');
    const receipt = page.url();
    assert.match(await page.locator('body').innerText(), /Order placed successfully/i);
    for (const width of [320, 360, 375, 390, 412, 430, 768, 1440]) {
      await page.setViewportSize({width, height:900});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      if (output && [390,1440].includes(width)) await page.locator('.receipt-card').screenshot({path:path.join(output, `confirmation-${width}.png`)});
    }
    const duplicate = await page.request.post(origin + '/checkout/', {form: payload, headers: {Referer: origin + '/checkout/'}});
    assert.equal(duplicate.status(), 200); assert.equal(duplicate.url(), receipt);
    const stranger = await browser.newContext();
    assert.equal((await stranger.request.get(receipt)).status(), 404);
    await stranger.close();
    assert.deepEqual(errors, []);
    console.log('Mobile/desktop checkout, CSRF form submit, duplicate POST and private receipt passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
