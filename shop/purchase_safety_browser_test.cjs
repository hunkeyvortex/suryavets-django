const {chromium}=require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const origin=process.argv[2], fixture=JSON.parse(process.argv[3]);
 assert(/^http:\/\/localhost:\d+$/.test(origin),'Isolated test server required');
 const browser=await chromium.launch({headless:true,executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
 try {
  for(const width of [1440,375,390,430]) {
   const context=await browser.newContext({viewport:{width,height:900}});
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   const fits=async()=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No horizontal overflow at '+width);
   await page.goto(origin+'/product/safety-mixed/');
   assert(await page.locator(`.buying-form input[name="variant_id"][value="${fixture.bad}"]`).isDisabled());
   assert(await page.locator(`.buying-form input[name="variant_id"][value="${fixture.good}"]`).isChecked());
   assert.equal(await page.locator('[data-product-price]').innerText(),'₹180.00');
   assert(!(await page.locator('.buying-form').innerText()).includes('100%'));
   await fits();
   if(process.env.SURYA_BROWSER_ARTIFACTS)await page.screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`safety-mixed-${width}.png`),fullPage:true});
   await page.locator('.buying-form [data-add-to-cart]').click();await page.waitForURL('**/cart/');
   assert((await page.locator('.basket-variant').innerText()).includes('1 KG'));await fits();
   await page.locator('.basket-checkout').click();await page.waitForURL('**/checkout/');
   assert(await page.locator('[name="checkout_token"]').count());await fits();
   await page.goto(origin+'/product/safety-unavailable/');
   assert(await page.locator('.buying-form [data-add-to-cart]').isDisabled());
   assert.equal(await page.locator('[data-product-price]').innerText(),'Currently unavailable');await fits();
   await page.goto(origin+'/categories/');
   const card=page.locator('[data-product-card]').filter({hasText:'Safety unavailable family'});
   assert((await card.innerText()).includes('Currently unavailable'));
   assert(!(await card.innerText()).includes('₹0.00'));await fits();
   const blocked=await browser.newContext({viewport:{width,height:900}});
   await blocked.addCookies([{name:fixture.cookieName,value:fixture.cookie,url:origin}]);
   const blockedPage=await blocked.newPage();await blockedPage.goto(origin+'/cart/');
   assert((await blockedPage.locator('body').innerText()).includes('Price unavailable'));
   assert.equal(await blockedPage.locator('.basket-checkout').getAttribute('aria-disabled'),'true');
   // Deliberately dispatch a click on the disabled link to test its guard.
   await blockedPage.locator('.basket-checkout').dispatchEvent('click');assert(blockedPage.url().endsWith('/cart/'));
   await blockedPage.goto(origin+'/checkout/');
   assert.equal(await blockedPage.locator('[name="checkout_token"]').count(),0);
   assert((await blockedPage.locator('body').innerText()).includes('needs attention'));
   if(process.env.SURYA_BROWSER_ARTIFACTS)await blockedPage.screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`safety-blocked-cart-${width}.png`),fullPage:true});
   assert.equal(errors.length,0,errors.join('\n'));
   await blocked.close();await context.close();
  }
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
