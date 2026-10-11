const assert=require('node:assert/strict');
const {chromium}=require(process.env.STROMTARIF_PLAYWRIGHT_PATH||'playwright');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<stromtarif-reading-card></stromtarif-reading-card>');
  await page.addScriptTag({path:path.join(__dirname,'../custom_components/stromtarif/www/stromtarif-card.js')});
  await page.evaluate(()=>{
   window.writes=[];window.reject=false;
   const card=document.querySelector('stromtarif-reading-card');card.setConfig({type:'custom:stromtarif-reading-card'});
   window.historyData={ledger:{revision:8,tariffs:[{active:true}],readings:[{date:'2026-01-01',value:'1000',kind:'initial',meter_number:'<img src=x onerror="window.XSS=true">',meter_id:'meter_1'}]}};
   card.hass={config:{time_zone:'Europe/Berlin'},callWS:async m=>{
    if(m.type==='stromtarif/list')return [{entry_id:'first',title:'Haushalt'},{entry_id:'second',title:'Garage'}];
    if(m.type==='stromtarif/history')return structuredClone(window.historyData);
    if(m.type==='stromtarif/update'){window.writes.push(m);if(window.reject)throw new Error('Die Daten wurden inzwischen geändert. Bitte neu laden.');
     window.historyData.ledger.revision++;const row={date:m.values.date,value:m.values.reading,kind:'manual',meter_number:'OLD-123',meter_id:'meter_1'};
     if(m.operation==='reading_add')window.historyData.ledger.readings.push(row);else window.historyData.ledger.readings[m.values.index]=row;
     return {revision:window.historyData.ledger.revision};}
   }};
  });
  await page.getByRole('button',{name:'Zählerstand speichern'}).waitFor();
  assert.equal(await page.locator('stromtarif-reading-card').locator('img').count(),0);assert.equal(await page.evaluate(()=>window.XSS),undefined);
  await page.getByLabel('Ablesedatum').fill('2026-02-01');await page.getByLabel('Zählerstand (kWh)').fill('1234.5678');
  await page.getByRole('button',{name:'Zählerstand speichern'}).click();await page.getByRole('status').filter({hasText:'Zählerstand gespeichert.'}).waitFor();
  assert.deepEqual(await page.evaluate(()=>window.writes[0]),{type:'stromtarif/update',entry_id:'first',revision:8,operation:'reading_add',values:{date:'2026-02-01',reading:'1234.5678'}});
  assert.equal(await page.getByLabel('Zählerstand (kWh)').inputValue(),'');
  await page.getByLabel('Ablesedatum').fill('2026-02-01');await page.getByLabel('Zählerstand (kWh)').fill('1240');await page.getByRole('button',{name:'Zählerstand speichern'}).click();
  await page.waitForFunction(()=>window.writes.length===2);assert.equal(await page.evaluate(()=>window.writes[1].operation),'reading_edit');assert.equal(await page.evaluate(()=>window.writes[1].values.index),1);
  await page.getByRole('button',{name:'Zählerstand speichern',disabled:false}).waitFor();await page.getByLabel('Ablesedatum').fill('2026-03-01');await page.getByLabel('Zählerstand (kWh)').fill('1400');
  await page.evaluate(()=>window.reject=true);await page.getByRole('button',{name:'Zählerstand speichern'}).click();await page.getByRole('status').filter({hasText:'Die Daten wurden inzwischen geändert.'}).waitFor();
  assert.equal(await page.getByLabel('Zählerstand (kWh)').inputValue(),'1400');await page.getByRole('button',{name:'Aktualisieren',exact:true}).click();assert.equal(await page.getByLabel('Zählerstand (kWh)').inputValue(),'1400');
  await page.getByLabel('Tarifbuch').selectOption('second');await page.getByLabel('Zählerstand (kWh)').waitFor();assert.equal(await page.getByLabel('Zählerstand (kWh)').inputValue(),'');
  await page.evaluate(()=>{window.historyData.ledger.tariffs[0].active=false;});await page.getByRole('button',{name:'Aktualisieren',exact:true}).click();await page.getByText('Tarif ist inaktiv. Im Verwaltungs-Panel prüfen.').waitFor();assert.equal(await page.getByRole('button',{name:'Zählerstand speichern'}).isDisabled(),true);
  assert.deepEqual(errors,[]);console.log('Reading card: input, meter number, add/edit, decimal precision, revision errors, draft preservation, selection, inactive tariff and escaping passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
