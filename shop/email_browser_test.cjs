const {chromium}=require(process.env.SURYA_PLAYWRIGHT_MODULE);
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
  const emails=JSON.parse(fs.readFileSync(0,'utf8'));
  const browser=await chromium.launch({headless:true,executablePath:process.env.SURYA_BROWSER_EXECUTABLE});
  try {
    const page=await browser.newPage();
    for(let index=0;index<emails.length;index++) {
      for(const width of [320,390,600]) {
        await page.setViewportSize({width,height:900});
        await page.setContent(emails[index]);
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        assert((await page.locator('body').innerText()).includes('5 KG'));
        if(process.env.SURYA_BROWSER_ARTIFACTS && width===390)
          await page.screenshot({path:path.join(process.env.SURYA_BROWSER_ARTIFACTS,`order-email-${index}-390.png`),fullPage:true});
      }
    }
    console.log('Both HTML email templates render without overflow at 320, 390 and 600px.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
