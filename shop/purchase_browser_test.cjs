const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const origin = process.argv[2];
  assert(/^http:\/\/localhost:\d+$/.test(origin), 'Disposable server only');
  const browser = await chromium.launch({headless:true, executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const page = await browser.newPage({viewport:{width:390,height:900}});
    const errors=[]; page.on('pageerror', e=>errors.push(e.message));
    const signature = crypto.createHmac('sha256','fixture-secret').update('order_browser|pay_browser').digest('hex');
    // This is a test double, not evidence of a real Razorpay payment.
    await page.route('https://checkout.razorpay.com/v1/checkout.js', route=>route.fulfill({contentType:'application/javascript',body:`window.Razorpay=class {constructor(options){this.options=options;} on(){} open(){this.options.handler({razorpay_order_id:'order_browser',razorpay_payment_id:'pay_browser',razorpay_signature:'${signature}'});}};`}));
    await page.goto(origin+'/login/');
    await page.locator('.auth-form').getByLabel('Email address',{exact:true}).fill('flow@example.com');
    await page.getByLabel('Password',{exact:true}).fill('Flow-fixture-921!');
    await page.getByRole('button',{name:'Sign in',exact:true}).click();
    await page.waitForURL('**/account/');
    await page.goto(origin+'/product/complete-flow-fixture/');
    await page.locator('input[data-name="5 KG"]').check();
    await page.locator('[data-add-to-cart]').click();
    await page.waitForURL('**/cart/');
    assert.equal(await page.locator('.basket-variant').innerText(),'5 KG');
    assert((await page.locator('.basket-unit').innerText()).includes('2,950.00'));
    for (const width of [320,360,375,390,412,430,768,1440]) {
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
    await page.getByRole('link',{name:'Proceed to checkout'}).click();
    const fields={email:'flow@example.com',phone:'9999999999',shipping_name:'Flow Test',shipping_address_line_1:'1 Fixture Road',shipping_city:'Mumbai',shipping_state:'Maharashtra',shipping_postal_code:'400001'};
    for(const [key,value] of Object.entries(fields)) await page.locator(`[data-checkout-form] [name="${key}"]`).fill(value);
    await page.getByRole('radio',{name:'Online Payment',exact:false}).check();
    await page.locator('[name="billing_same_as_shipping"]').check();
    await page.locator('[name="terms"]').check();
    await page.getByRole('button',{name:'Place order',exact:true}).click();
    await page.waitForURL('**/checkout/payment/**');
    assert(!(await page.locator('.receipt-card').innerText()).includes('Payment confirmed.'));
    await page.getByRole('button',{name:'Prepare test payment',exact:true}).click();
    await page.getByRole('button',{name:'Open Razorpay test payment',exact:true}).click();
    await page.waitForURL('**/checkout/confirmation/**');
    assert((await page.locator('.receipt-card').innerText()).includes('Payment confirmed.'));
    const receipt=page.url(), orderId=receipt.split('/').filter(Boolean).at(-1);
    for (const width of [320,360,375,390,412,430,768,1440]) {
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      if(process.env.SURYA_BROWSER_ARTIFACTS && [390,1440].includes(width)) {
        fs.mkdirSync(process.env.SURYA_BROWSER_ARTIFACTS,{recursive:true});
        await page.locator('.receipt-card').screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`paid-confirmation-${width}.png`)});
      }
    }
    await page.reload();
    await page.getByRole('link',{name:'Track your order',exact:true}).click();
    assert(page.url().endsWith('#tracking'));
    assert((await page.locator('.customer-main').innerText()).includes('5 KG'));
    const staff=await browser.newPage();
    await staff.goto(origin+'/crm/login/');
    await staff.getByLabel('Username').fill('flow-staff');
    await staff.getByLabel('Password').fill('Flow-fixture-921!');
    await staff.getByRole('button',{name:'Sign in to CRM'}).click();
    await staff.waitForURL('**/crm/');
    const response=await staff.goto(origin+`/crm/orders/${orderId}/`);
    assert.equal(response.status(),200);
    assert((await staff.locator('body').innerText()).includes('5 KG'));
    assert.deepEqual(errors,[]);
    console.log('Simulated verified payment → receipt → My Account → CRM; mobile overflow checks passed.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
