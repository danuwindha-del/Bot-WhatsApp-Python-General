const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const artifacts=process.env.DAFFO_SCREENSHOTS||path.resolve('.artifacts');
fs.mkdirSync(artifacts,{recursive:true});
(async()=>{
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
try{
const page=await browser.newPage({viewport:{width:1440,height:1060},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
await page.goto('http://127.0.0.1:8765');await page.fill('#username','admin');await page.fill('#password','Ui-test-only-password');await page.click('#loginForm button');await page.waitForSelector('#dashboard:not([hidden])');
await page.screenshot({path:path.join(artifacts,'dashboard-desktop.png'),fullPage:true});
await page.click('[data-tab="training"]');await page.fill('#profileObjective','Membantu pelanggan toko dengan jawaban yang jelas.');await page.click('#trainingProfileForm button');await page.waitForFunction(()=>document.querySelector('#trainingSummary').textContent.includes('revisi 1'));
await page.fill('#documentTitle','Pengiriman & pengembalian');await page.fill('#documentTags','pengiriman, toko, FAQ');await page.fill('#documentContent','Pengiriman pesanan gratis dalam 3 hari kerja. Pengembalian produk diterima dalam 7 hari dengan bukti pembelian.');await page.click('#documentForm button.primary');await page.waitForSelector('#documentList .entryCard');
await page.fill('#exampleQuestion','Kapan pesanan saya sampai?');await page.fill('#exampleAnswer','Pesananmu akan sampai dalam 3 hari kerja, dengan ongkir gratis.');await page.click('#exampleForm button.primary');await page.waitForSelector('#exampleList .entryCard');
await page.fill('#trainingPrompt','Berapa lama pengiriman pesanan?');await page.click('#trainingPreview');await page.waitForSelector('#trainingSources .sourceCard');assert.match(await page.textContent('#trainingSources'),/3 hari/);
await page.fill('#evaluationQuestion','Berapa lama pengiriman?');await page.fill('#evaluationExpected','gratis, 3 hari');await page.click('#evaluationForm button');await page.waitForSelector('#evaluationList .entryCard');await page.click('#runEvaluation');await page.waitForFunction(()=>document.querySelector('#evaluationResults').textContent.includes('1/1'));
await page.fill('#publishLabel','Layanan pelanggan v1');await page.click('#trainingPublish');await page.waitForSelector('#versionList .entryCard');assert.match(await page.textContent('#trainingState'),/aktif/);
await page.click('#documentList button');await page.fill('#documentContent','Pengiriman pesanan gratis dalam 5 hari kerja. Pengembalian produk diterima dalam 7 hari.');await page.click('#documentForm button.primary');await page.waitForFunction(()=>document.querySelector('#documentList').textContent.includes('5 hari'));
await page.fill('#publishLabel','Layanan pelanggan v2');await page.click('#trainingPublish');await page.waitForFunction(()=>document.querySelectorAll('#versionList .entryCard').length===2);await page.click('#versionList button');await page.waitForFunction(()=>document.querySelectorAll('#versionList button').length===1&&document.querySelector('#versionList .entryCard:last-child').textContent.includes('Aktif'));
await page.selectOption('#previewMode','active');await page.click('#trainingPreview');await page.waitForFunction(()=>document.querySelector('#trainingSources').textContent.includes('3 hari'));assert.match(await page.textContent('#trainingSources'),/3 hari/);
await page.screenshot({path:path.join(artifacts,'training-desktop.png'),fullPage:true});
await page.reload();await page.waitForSelector('#dashboard:not([hidden])');await page.click('[data-tab="training"]');assert.match(await page.textContent('#documentList'),/5 hari/);
const dataset=await page.evaluate(async()=>await(await fetch('/api/training/export')).json());assert.equal(dataset.documents.length,1);
await page.setInputFiles('#trainingImport',{name:'training.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(dataset))});await page.waitForFunction(()=>document.querySelector('#notice').textContent==='Dataset diimpor ke draft');
await page.click('[data-tab="vision"]');await page.setInputFiles('#visionFile',{name:'sample.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=','base64')});await page.waitForSelector('#visionPreviewWrap:not([hidden])');await page.click('#visionAnalyze');await page.waitForFunction(()=>document.querySelector('#visionResult').textContent.includes('API key'));
await page.screenshot({path:path.join(artifacts,'vision-desktop.png'),fullPage:true});
await page.click('#themeToggle');assert(await page.locator('body').evaluate(e=>e.classList.contains('dark')));await page.screenshot({path:path.join(artifacts,'vision-dark.png'),fullPage:true});await page.click('#themeToggle');
await page.setViewportSize({width:390,height:844});await page.click('[data-tab="training"]');await page.screenshot({path:path.join(artifacts,'training-mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Mobile page must not overflow horizontally');
await page.click('[data-tab="vision"]');await page.screenshot({path:path.join(artifacts,'vision-mobile.png'),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
assert.deepEqual(errors,[]);console.log(JSON.stringify({result:'PASS',checks:['login','profile','knowledge CRUD','examples','retrieval preview','evaluation','publication','rollback','persistence after reload','dataset import/export','image selection','missing-provider-key error','theme toggle','mobile layout'],screenshots:6,errors}));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
