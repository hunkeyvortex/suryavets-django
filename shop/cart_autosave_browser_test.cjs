const {chromium}=require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
(async()=>{
 const origin=process.argv[2];
 assert(/^http:\/\/localhost:\d+$/.test(origin),'Isolated test server required');
 const browser=await chromium.launch({headless:true,executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/product/autosave-food/');
  await page.locator('.product-form [data-add-to-cart]').click();
  await page.waitForURL('**/cart/');
  await page.locator('[data-step="1"]').waitFor();
  assert.equal(await page.getByRole('button',{name:'Update',exact:true}).isVisible(),false);
  const input=page.locator('.basket-quantity [name="quantity"]');
  const saved=async value=>page.waitForFunction(value=>document.querySelector('.basket-quantity [name="quantity"]').value===String(value) && document.querySelector('.basket-checkout').getAttribute('aria-disabled')==='false',value);
  // Deliberately edit again while the first absolute update is in flight.
  let first=true;
  await page.route('**/cart/update/**',async route=>{
   if(first){first=false;await new Promise(resolve=>setTimeout(resolve,600));}
   await route.continue();
  });
  const sent=page.waitForRequest(r=>r.url().includes('/cart/update/'));
  await page.locator('[data-step="1"]').click();
  await sent;
  assert.equal(await page.locator('.basket-checkout').getAttribute('aria-disabled'),'true');
  await page.locator('[data-step="1"]').click();
  await page.locator('[data-step="1"]').click();
  await saved(4);
  assert.equal(await page.locator('[data-basket-total]').innerText(),'₹410.00');
  assert.equal(await page.locator('.sv-dock-badge').innerText(),'4');
  await page.unroute('**/cart/update/**');
  await input.fill('6');await saved(6);
  assert.equal(await page.locator('[data-basket-total]').innerText(),'₹540.00');
  assert.match(await page.locator('.basket-delivery strong').innerText(),/on us/);
  await page.locator('[data-step="-1"]').click();await saved(5);
  assert.equal(await page.locator('[data-basket-total]').innerText(),'₹500.00');
  await input.fill('99');
  await page.waitForFunction(()=>document.querySelector('[data-basket-status]').textContent.includes('not currently available'));
  await saved(5);
  await input.fill('0');
  assert.equal(await page.locator('.basket-checkout').getAttribute('aria-disabled'),'true');
  await input.fill('3');await saved(3);
  // Do not display a false total after network failure; retry the absolute value.
  await page.route('**/cart/update/**',route=>route.abort('failed'));
  await input.fill('2');
  await page.locator('[data-basket-retry]').waitFor();
  assert.equal(await page.locator('[data-basket-total]').innerText(),'₹320.00');
  assert.equal(await page.locator('.basket-checkout').getAttribute('aria-disabled'),'true');
  await page.unroute('**/cart/update/**');
  await page.locator('[data-basket-retry]').click();await saved(2);
  await page.reload();
  assert.equal(await input.inputValue(),'2');
  assert.equal(await page.locator('[data-basket-total]').innerText(),'₹230.00');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  // The ordinary form remains a working accessibility/network fallback.
  await page.context().close();
  const context=await browser.newContext({javaScriptEnabled:false});
  const nojs=await context.newPage();
  await nojs.goto(origin+'/product/autosave-food/');
  await nojs.locator('.product-form [data-add-to-cart]').click();
  await nojs.waitForURL('**/cart/');
  await nojs.locator('.basket-quantity [name="quantity"]').fill('2');
  await nojs.getByRole('button',{name:'Update',exact:true}).click();
  await nojs.waitForURL('**/cart/');
  assert.equal(await nojs.locator('[data-basket-total]').innerText(),'₹230.00');
  assert.deepEqual(errors,[]);
  console.log('Automatic +/- and typed updates, queued rapid edits, totals/counts/delivery, stock rejection, invalid inputs, network retry, reload persistence and no-JS fallback passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
