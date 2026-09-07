const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE);
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const origin=process.argv[2];
  if (!/^http:\/\/localhost:\d+$/.test(origin)) throw Error('Disposable server required');
  const browser=await chromium.launch({headless:true, executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const page=await browser.newPage(); const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(origin+'/product/gallery-test-product/');
    for(const width of [320,360,375,390,412,430,768,1024,1440]) {
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1), `Page overflow at ${width}`);
      const button=page.getByRole('button',{name:'View product photo 2'});
      await button.click();
      assert.equal(await page.locator('[data-product-main-image]').getAttribute('alt'),'Test photo 2');
      assert.equal(await button.getAttribute('aria-pressed'),'true');
      assert(await page.locator('[data-product-main-image]').evaluate(image=>image.complete && image.naturalWidth>0));
      assert(await page.getByText('Fixture nutrition text').isVisible());
      const box=await button.boundingBox(); assert(box.width>=44 && box.height>=44);
      await page.getByRole('button',{name:'View product photo 1'}).focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('[data-product-main-image]').getAttribute('alt'),'Test photo 1');
      if(process.env.SURYA_BROWSER_ARTIFACTS && [320,390,1440].includes(width)) {
        fs.mkdirSync(process.env.SURYA_BROWSER_ARTIFACTS,{recursive:true});
        await page.locator('.product-page').screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`product-media-${width}.png`)});
      }
    }
    assert.deepEqual(errors,[]);
    console.log('Gallery image switching, accessible controls and nutrition at nine widths passed.');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
