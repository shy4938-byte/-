const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,headless:true,args:['--no-sandbox']});try{
 const context=await browser.newContext({offline:true,acceptDownloads:true}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent(fs.readFileSync(path.join(__dirname,'dist/SpecCompare.html'),'utf8'));
 const a=process.env.SPECCOMPARE_PM9A1_PDF,e=process.env.SPECCOMPARE_PM9E1_PDF;assert(a&&e,'Both PDF environment paths are required');
 const models=await page.evaluate(async({data})=>SpecCompare.analyze(new File([Uint8Array.from(atob(data),c=>c.charCodeAt(0))],'PM9A1.pdf'),'SSD'),{data:fs.readFileSync(a).toString('base64')});
 assert.equal(models.length,4);
 const capacities=['256GB','512GB','1024GB','2048GB'];
 for(let i=0;i<4;i++){
  const v=models[i].values;assert.equal(v['모델명'].text,'Samsung PM9A1 '+capacities[i]);assert.equal(v['용량'].text,capacities[i]);assert.equal(v['인터페이스'].text,'PCI Express Gen4 x4');
  assert.equal(v['순차읽기 속도'].text,['6,400 / 4,900 MB/s (QD32)','6,900 / 6,300 MB/s (QD32)','7,000 / 6,600 MB/s (QD32)','7,000 / 6,600 MB/s (QD32)'][i]);
  assert.equal(v['순차쓰기 속도'].text,['2,700 / 500 MB/s (QD32)','5,000 / 1,050 MB/s (QD32)','5,100 / 1,900 MB/s (QD32)','5,200 / 2,000 MB/s (QD32)'][i]);
  assert.equal(v['랜덤읽기 속도'].text,['500K / 300K IOPS (QD32)','800K / 500K IOPS (QD32)','1,000K / 750K IOPS (QD32)','1,000K / 750K IOPS (QD32)'][i]);
  assert.equal(v['랜덤쓰기 속도'].text,['600K / 150K IOPS (QD32)','800K / 250K IOPS (QD32)','850K / 500K IOPS (QD32)','850K / 500K IOPS (QD32)'][i]);
  assert.equal(v['랜덤읽기 속도 · QD1'].text,'18K IOPS');assert.equal(v['랜덤쓰기 속도 · QD1'].text,'53K IOPS');
  assert.equal(v['내구성'].text,['150 TB','300 TB','600 TB','1200 TB'][i]);assert.equal(v['TBW'].text,v['내구성'].text);assert.equal(v['가격'].text,'확인 필요');assert.equal(v['순차읽기 속도'].page,6);
  assert(v['부품번호'].text.includes('$'));assert(v['순차읽기 속도 · 병기값 설명'].text.includes('TurboWrite 미적용'));
 }
 console.log('PASS PM9A1: four capacities, family/part numbers, Gen4, all performance values, QD1/QD32, TurboWrite note, TBW and missing price');
 await page.locator('#pdf-input').setInputFiles([e,a]);await page.locator('#analyze').click();
 await page.locator('#model-dialog').waitFor({state:'visible'});await page.locator('#model-list').getByText(/Samsung PM9E1/).first().waitFor();
 for(const input of await page.locator('#model-list input').all())await input.uncheck();await page.locator('#model-list input').nth(0).check();await page.locator('#model-dialog button[value="ok"]').click();
 await page.locator('#model-list').getByText(/Samsung PM9A1/).first().waitFor();
 for(const input of await page.locator('#model-list input').all())await input.uncheck();await page.locator('#model-list input').nth(1).check();await page.locator('#model-dialog button[value="ok"]').click();
 await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);const comparison=await page.evaluate(()=>SpecCompare.getProducts());assert.equal(comparison.length,2);assert.equal(comparison[0].values['모델명'].text,'Samsung PM9E1 512GB');assert.equal(comparison[1].values['모델명'].text,'Samsung PM9A1 512GB');
 const download=page.waitForEvent('download');await page.locator('#save').click();await(await download).saveAs(path.join(process.env.SPECCOMPARE_TEST_OUTPUT||__dirname,'PM9E1_PM9A1_512GB.xlsx'));
 assert.equal(errors.length,0,errors.join('\n'));console.log('PASS two-PDF upload, independent model selections, no empty column, Excel download, zero page errors');
}finally{await browser.close();}})().catch(err=>{console.error(err);process.exitCode=1});
