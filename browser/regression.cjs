const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const fs=require('fs'),assert=require('assert');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,headless:true,args:['--no-sandbox']});try{
const context=await browser.newContext({offline:true,acceptDownloads:true}),page=await context.newPage(),errors=[],requests=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});page.on('dialog',d=>d.accept());
await page.setContent(fs.readFileSync(process.env.SPECCOMPARE_HTML||require('path').join(__dirname,'dist/SpecCompare.html'),'utf8'));await page.waitForFunction(()=>window.SpecCompare);
const analyze=async(name,category)=>page.evaluate(async({name,category})=>{const bytes=Uint8Array.from(atob(name.data),c=>c.charCodeAt(0));return SpecCompare.analyze(new File([bytes],name.name,{type:'application/pdf'}),category);},{name:{name:name.split('/').pop(),data:fs.readFileSync(name).toString('base64')},category});
const pm=process.env.SPECCOMPARE_PM9E1_PDF;if(!pm)throw Error('SPECCOMPARE_PM9E1_PDF is required');
await page.locator('#pdf-input').setInputFiles(pm);await page.locator('#analyze').click();await page.locator('#model-dialog').waitFor({state:'visible',timeout:30000});assert.equal(await page.locator('#model-list input').count(),4);await page.locator('#model-dialog button[value="ok"]').click();await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
const products=await page.evaluate(()=>SpecCompare.getProducts());assert.equal(products.length,4);
for(let i=0;i<4;i++){assert.equal(products[i].values['순차쓰기 속도'].text,['7,000 MB/s','12,500 MB/s','12,500 MB/s','12,600 MB/s'][i]);assert.equal(products[i].values['내구성'].text,['300 TB','600 TB','1,200 TB','2,400 TB'][i]);assert.match(products[i].values['인터페이스'].text,/PCI Express\s*®?\s*Gen\.5 x4/);assert.equal(products[i].values['가격'].text,'확인 필요');}
console.log('PASS real PM9E1 upload, model selector, per-capacity specifications');
let download=page.waitForEvent('download');await page.locator('#save').click();await (await download).saveAs(require('path').join(process.env.SPECCOMPARE_TEST_OUTPUT||__dirname,'PM9E1_Browser_SpecCompare.xlsx'));
await page.getByRole('textbox',{name:'제조사 제품 1',exact:true}).fill('수동 수정');await page.locator('#confirm').click();assert.equal((await page.evaluate(()=>SpecCompare.getProducts()))[0].values['제조사'].status,'확인 완료');
download=page.waitForEvent('download');await page.locator('#save').click();await(await download).saveAs(require('path').join(process.env.SPECCOMPARE_TEST_OUTPUT||__dirname,'edited.xlsx'));console.log('PASS direct edits, confirmation, Excel download');
const extra=JSON.parse(JSON.stringify(products[0]));extra.values['모델명'].text='EXTRA5';await page.evaluate(p=>SpecCompare.loadProducts(p),[...products,extra]);assert.equal(await page.locator('#groups button').count(),2);await page.locator('#groups button').nth(1).click();assert.equal(await page.locator('#comparison tbody input').count(),10);console.log('PASS five-product grouping');
const sample=(process.env.SPECCOMPARE_SAMPLES||require('path').join(__dirname,'samples'))+'/';
const memory=(await analyze(sample+'memory.pdf','MEMORY'))[0];assert.equal(memory.values['용량'].text,'16GB');assert.equal(memory.values['동작속도'].text,'5600 MT/s');
const vga=(await analyze(sample+'vga.pdf','VGA'))[0];assert.equal(vga.values['VRAM 용량'].text,'16GB');assert.equal(vga.values['소비전력'].text,'200 W (TGP)');
const mixed=(await analyze(sample+'mixed.pdf','SSD'))[0];assert.equal(mixed.values['용량'].text,'확인 필요');console.log('PASS memory/VGA samples, repeated Worker use, ambiguous-model rejection');
for(const name of ['scan','locked','bad']){let failed=false;try{await analyze(sample+name+'.pdf','SSD');}catch(e){failed=true;}assert(failed,name+' must reject');}console.log('PASS scan, encrypted and invalid PDF handling');
assert.equal(errors.length,0,errors.join('\n'));assert.equal(requests.length,0,requests.join('\n'));console.log('PASS no page errors; zero external HTTP requests in offline browser');
fs.writeFileSync(require('path').join(process.env.SPECCOMPARE_TEST_OUTPUT||__dirname,'regression-products.json'),JSON.stringify(products,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
