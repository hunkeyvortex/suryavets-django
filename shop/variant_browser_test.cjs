const {chromium}=require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
  const origin=process.argv[2];
  assert(/^http:\/\/localhost:\d+$/.test(origin),'Disposable test server required');
  const browser=await chromium.launch({headless:true,executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    for(const width of [320,360,375,390,412,430,768,1024,1440]) {
      const context=await browser.newContext({viewport:{width,height:900}});
      const page=await context.newPage(), errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(origin+'/categories/');
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Card grid overflow ${width}`);
      const inlineCard = page.locator('[data-product-card]');
      await inlineCard.locator('input[data-name="5 kg"]').check();
      assert.equal(await inlineCard.locator('[data-card-price]').innerText(),'₹2,950.00');
      assert.equal(await inlineCard.locator('[data-card-regular]').innerText(),'₹3,500.00');
      assert.equal(await inlineCard.locator('[data-card-saving]').innerText(),'You save ₹550.00');
      assert.equal(await inlineCard.locator('[data-card-image]').getAttribute('alt'),'5 kg test fixture');
      assert(await inlineCard.locator('input[data-name="10 kg"]').isDisabled());
      assert.equal(await inlineCard.locator('[data-card-step]').count(),0);
      assert.equal(await inlineCard.locator('[name="quantity"]').getAttribute('type'),'hidden');
      assert.equal(await inlineCard.locator('[name="quantity"]').inputValue(),'1');
      if(process.env.SURYA_BROWSER_ARTIFACTS && [320,390,1440].includes(width)) {
        fs.mkdirSync(process.env.SURYA_BROWSER_ARTIFACTS,{recursive:true});
        await page.locator('.catalog-product-grid').screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`variant-cards-${width}.png`)});
      }
      await inlineCard.getByRole('button',{name:'Add to Cart',exact:true}).click();
      await page.waitForURL('**/cart/');
      await page.goto(origin+'/cart/');
      assert((await page.locator('body').innerText()).includes('5 kg'));
      assert.equal(await page.locator('.basket-quantity input[name="quantity"]').inputValue(),'1');
      await page.locator('.basket-quantity input[name="quantity"]').fill('2');
      await page.getByRole('button',{name:'Update',exact:true}).click();
      await page.waitForURL('**/cart/');
      assert((await page.locator('body').innerText()).includes('5,900.00'));
      await page.getByRole('button',{name:/^Remove /}).click();
      await page.goto(origin+'/categories/');
      await page.getByRole('link',{name:'View product',exact:true}).click();
      const overflow=async()=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Overflow ${width}: ${page.url()}`);
      await overflow();
      const small=page.locator('input[data-name="1.5 kg"]'), large=page.locator('input[data-name="5 kg"]');
      await small.check();
      assert.equal(await page.locator('[data-product-price]').innerText(),'₹1,050.00');
      await large.check();
      assert.equal(await page.locator('[data-product-price]').innerText(),'₹2,950.00');
      assert.equal(await page.locator('[data-product-compare]').innerText(),'₹3,500.00');
      assert.equal(await page.locator('[data-product-discount]').innerText(),'15% OFF');
      assert.equal(await page.locator('[data-product-saving]').innerText(),'You save ₹550.00 on MRP');
      assert.equal(await page.locator('[data-product-unit]').innerText(),'₹590.00/kg');
      assert.equal(await page.locator('[data-product-main-image]').getAttribute('alt'),'5 kg test fixture');
      assert(await page.locator('[data-product-main-image]').evaluate(img=>img.complete&&img.naturalWidth>0));
      assert(await page.locator('.buying-option').filter({has:large}).getByText('Best value',{exact:true}).isVisible());
      assert(!(await page.locator('input[data-name="10 kg"]').isEnabled()));
      for(const label of await page.locator('.buying-option').all()){ const box=await label.boundingBox();assert(box.width>=44&&box.height>=44); }
      await page.getByRole('button',{name:'Increase quantity',exact:true}).click();
      assert.equal(await page.locator('#quantity').inputValue(),'2');
      if(process.env.SURYA_BROWSER_ARTIFACTS && [320,390,1440].includes(width)){
        fs.mkdirSync(process.env.SURYA_BROWSER_ARTIFACTS,{recursive:true});
        await page.locator('.product-view').screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`variant-buying-${width}.png`)});
      }
      await page.getByRole('button',{name:'Add to Cart',exact:true}).click();
      await page.waitForURL('**/cart/'); await overflow();
      assert.equal(await page.locator('.basket-variant').innerText(),'5 kg');
      await page.locator('.basket-quantity input[name="quantity"]').fill('3');
      await page.getByRole('button',{name:'Update',exact:true}).click();
      await page.waitForURL('**/cart/');
      assert.equal(await page.locator('.basket-quantity input[name="quantity"]').inputValue(),'3');
      assert.equal(await page.locator('.basket-line-total > strong').innerText(),'₹8,850.00');
      await page.goto(origin+'/product/variant-test-food/'); await small.check();
      await page.getByRole('button',{name:'Add to Cart',exact:true}).click(); await page.waitForURL('**/cart/');
      assert.equal(await page.locator('.basket-variant').count(),2);
      assert.deepEqual((await page.locator('.basket-variant').allTextContents()).sort(),['1.5 kg','5 kg']);
      await page.goto(origin+'/product/variant-test-food/');
      await large.focus(); await page.keyboard.press('Space');
      assert(await large.isChecked());
      await page.getByRole('button',{name:'Buy now',exact:true}).click(); await page.waitForURL('**/checkout/');
      await overflow(); assert.deepEqual(errors,[]);
      await context.close();
    }
    console.log('Nine widths: pack choice, exact prices, MRP, savings, images, stock, quantity, separate cart sizes, Buy now and no overflow passed.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
