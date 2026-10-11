const assert=require('node:assert/strict');
const {chromium}=require(process.env.STROMTARIF_PLAYWRIGHT_PATH || 'playwright');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:700,height:1600}});
  await page.setContent('<body><stromtarif-card></stromtarif-card></body>');
  await page.addScriptTag({path:path.join(__dirname,'../custom_components/stromtarif/www/stromtarif-card.js')});
  await page.evaluate(()=>{
   window.exportCalls=0;
   const card=document.querySelector('stromtarif-card');card.setConfig({type:'custom:stromtarif-card'});
   const response={title:'Test',due:'2026-12-01',source_error:null,intervals:[{from:'2026-01-01',to:'2026-04-01',tariff:'A',consumption:600,total_cost:216}],
    ledger:{billing_start:'2026-01-01',billing_end:'2027-01-01',monthly_installment:'100',source:null,tariffs:[{start:'2026-01-01',name:'<img src=x onerror="window.XSS=true">',price:'0.30',monthly_fee:'12'}],readings:[{date:'2026-01-01',value:'1000',kind:'initial'},{date:'2026-04-01',value:'1600',kind:'manual'}],payments:[{date:'2026-01-01',amount:'100'}]},
    finances:{observed_until:'2026-04-01',period_cost:216,paid:100,balance:116,planned:1200,forecast_cost:874,forecast_balance:-326,partial_period_estimate:false}};
   card.hass={callWS:async msg=>msg.type==='stromtarif/list'?[{entry_id:'entry1',title:'Test'}]:msg.type==='stromtarif/export'?(window.exportCalls++,{filename:'stromtarif.csv',csv:'Typ;Datum\nTarif;2026-01-01'}):response};
  });
  await page.getByRole('heading',{name:'DEr Stromtarif',exact:true}).waitFor();
  assert.equal(await page.locator('stromtarif-card').locator('img').count(),0);
  assert.equal(await page.evaluate(()=>window.XSS),undefined);
  assert.match(await page.evaluate(()=>document.querySelector('stromtarif-card').shadowRoot.textContent),/216,00/);
  assert.match(await page.evaluate(()=>document.querySelector('stromtarif-card').shadowRoot.textContent),/600/);
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Historie als CSV herunterladen'}).click();
  assert.equal((await download).suggestedFilename(),'stromtarif.csv');
  assert.equal(await page.evaluate(()=>window.exportCalls),1);
  await page.screenshot({path:'/tmp/stromtarif-card-test.png',fullPage:true});
  console.log('Card rendering, history, escaping and CSV download passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
