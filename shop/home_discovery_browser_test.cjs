const {chromium} = require(process.env.SURYA_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
(async()=>{
 const browser = await chromium.launch({headless:true,executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
 const page = await browser.newPage({reducedMotion:'reduce'});
 await page.route('**/*', route => route.request().url().startsWith(process.argv[2]+'/') ? route.continue() : route.abort());
 await page.route('https://example.com/pack.jpg', route=>route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="240"><rect width="200" height="240" fill="#eef7ef"/><rect x="50" y="30" width="100" height="170" rx="12" fill="#008d51"/><text x="100" y="115" text-anchor="middle" fill="white">TEST PACK</text></svg>'}));
 const errors=[]; page.on('pageerror', error=>errors.push(error.message));
 const origin=process.argv[2];
 const dir=process.env.SURYA_BROWSER_ARTIFACTS || path.join(__dirname,'..','tmp','home-discovery');
 fs.mkdirSync(dir,{recursive:true});
 for (const width of [320,360,375,390,412,430,768,1024,1440]) {
  await page.setViewportSize({width,height:900});
  await page.goto(origin+'/',{waitUntil:'domcontentloaded'});
  await page.waitForSelector('[data-hero-dots] button');
  assert.equal(await page.locator('.sv-home').count(),1);
  const layout=await page.evaluate(()=>{
   const trust=document.querySelector('.trust-strip__grid');
   return {width:innerWidth,scroll:document.documentElement.scrollWidth,
     columns:getComputedStyle(document.querySelector('.sv-home-food-grid')).gridTemplateColumns.split(' ').length,
     trustYs:[...trust.children].map(e=>Math.round(e.getBoundingClientRect().top)),
     trustFits:trust.scrollWidth<=trust.clientWidth+1};
  });
  assert.ok(layout.scroll<=width,`Page overflow at ${width}`);
  assert.equal(await page.locator('#best-sellers [data-product-card]').count(),8);
  await page.locator('#best-sellers [data-product-next]').click();
  assert.ok(await page.locator('#best-sellers [data-product-track]').evaluate(e=>e.scrollLeft>=0));
  assert.equal(new Set(layout.trustYs).size,1,`Trust boxes must remain one fixed row at ${width}`);
  assert.ok(layout.trustFits);
  assert.equal(layout.columns,width<=760?2:4);
  const sizeCard=page.locator('[data-home-panel="dog"] [data-product-card]').first();
  await sizeCard.locator('.sv-card__choose-size').click();
  assert.equal(await sizeCard.locator('dialog').evaluate(e=>e.open),true);
  assert.ok(await sizeCard.locator('dialog').evaluate(e=>e.scrollWidth<=e.clientWidth+1),`Picker overflow ${width}`);
  if([390,430,1440].includes(width)) await page.screenshot({path:path.join(dir,`size-picker-${width}.png`)});
  await page.keyboard.press('Escape');
  await page.waitForFunction(()=>![...document.querySelectorAll('.sv-size-dialog')].some(e=>e.open));
  assert.equal(await sizeCard.locator('.sv-card__choose-size').evaluate(e=>e===document.activeElement),true);
  await page.locator('[data-home-tab="cat"]').click();
  assert.equal(await page.locator('[data-home-panel="cat"]').isVisible(),true);
  assert.equal(await page.locator('[data-home-panel="dog"]').isVisible(),false);
  await page.keyboard.press('ArrowLeft');
  assert.equal(await page.locator('[data-home-tab="dog"]').getAttribute('aria-selected'),'true');
  if(width<=760){
   const opener=page.locator('[data-category-sheet-open]');
   await opener.click();
   assert.equal(await page.locator('#sv-category-sheet').evaluate(e=>e.open),true);
   await page.keyboard.press('Escape');
   await page.waitForFunction(()=>!document.querySelector('#sv-category-sheet').open && document.querySelector('[data-category-sheet-open]').getAttribute('aria-expanded')==='false');
   assert.equal(await opener.getAttribute('aria-expanded'),'false');
   assert.equal(await opener.evaluate(e=>e===document.activeElement),true);
   await opener.click();
   await page.getByRole('button',{name:'Close categories',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('#sv-category-sheet').open);
   await page.locator('[data-menu-toggle]').click();
   assert.equal(await page.locator('#mobile-navigation').evaluate(e=>e.open),true);
   await page.getByRole('button',{name:'Close navigation',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('#mobile-navigation').open);
  } else assert.equal(await page.locator('.sv-mobile-dock').isVisible(),false);
  // Motion preference must prevent autoplay; explicit controls still work.
  assert.equal(await page.locator('[data-hero-pause]').getAttribute('aria-pressed'),'true');
  await page.locator('[data-hero-dots] button').nth(1).click();
  assert.equal(await page.locator('.home-hero__slide').nth(1).getAttribute('aria-hidden'),'false');
  if([390,430,1440].includes(width)){
   await page.evaluate(()=>scrollTo(0,0));
   await page.screenshot({path:path.join(dir,`homepage-${width}.png`),fullPage:true});
   await page.locator('[data-home-tabs]').screenshot({path:path.join(dir,`homepage-food-${width}.png`)});
  }
  console.log(`Homepage ${width}px: layout, tabs, navigation and slider PASS`);
 }
 // Use only isolated test fixtures for a purchase-flow assertion.
 await page.goto(origin+'/',{waitUntil:'domcontentloaded'});
 const card=page.locator('[data-home-panel="dog"] [data-product-card]').first();
 await card.locator('[data-card-image]').evaluate(e=>e.dispatchEvent(new Event('error')));
 assert.equal(await card.locator('[data-card-photo-missing]').isVisible(),true);
 await card.locator('.sv-card__choose-size').click();
 assert.equal(await card.locator('dialog').evaluate(e=>e.open),true);
 await card.locator('input[name="variant_id"]').nth(1).check();
 assert.match(await card.locator('[data-card-price]').innerText(),/180/);
 await Promise.all([page.waitForURL('**/cart/'),card.locator('[data-card-add]').click()]);
 assert.match(await page.locator('main').innerText(),/6 KG/);
 assert.deepEqual(errors,[]);
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
