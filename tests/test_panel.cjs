const assert=require('node:assert/strict');
const {chromium}=require(process.env.STROMTARIF_PLAYWRIGHT_PATH || 'playwright');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1200}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<body style="margin:0"><stromtarif-panel></stromtarif-panel></body>');
  await page.addScriptTag({path:path.join(__dirname,'../custom_components/stromtarif/www/stromtarif-panel.js')});
  await page.evaluate(()=>{
   const panel=document.querySelector('stromtarif-panel');window.writes=[];window.periodRequests=[];
   const history={title:'Haushalt',due:'2026-12-01',source_error:null,reminder_error:null,intervals:[],totals:{},
    ledger:{revision:3,show_panel:false,interval:90,billing_start:'2026-01-01',billing_end:'2027-01-01',monthly_installment:'90',payment_day:1,schedule_mode:'monthly',source:null,reminders:{calendar:null,todo:null,readings:true,payments:true},
     tariffs:[{start:'2026-01-01',name:'<img src=x onerror="window.XSS=true">',reading:'1000',price:'0.30',monthly_fee:'12',active:true}],readings:[{date:'2026-01-01',value:'1000',kind:'initial'},{date:'2026-02-01',value:'1200',kind:'manual'},{date:'2026-04-01',value:'1600',kind:'manual'}],payments:[{date:'2026-01-02',amount:'90'}],bills:[]},
    tariff_summaries:[{index:0,name:'<img src=x onerror="window.XSS=true">',start:'2026-01-01',end:'2026-04-01',consumption:600,cost:216,effective_price:.36}],schedule:[{key:'2026-02-01',date:'2026-02-17',amount:'83'}],finances:{period_cost:216,paid:90,planned:1080,forecast_balance:-206}};
   history.ledger.meters=[{id:'meter_1',number:'OLD-123'}];history.ledger.readings.forEach(r=>Object.assign(r,{meter_id:'meter_1',meter_number:'OLD-123'}));
   panel.hass={config:{time_zone:'Europe/Berlin'},states:{'calendar.tarife':{entity_id:'calendar.tarife',state:'off',attributes:{friendly_name:'Tarifkalender',supported_features:7}},'calendar.readonly':{entity_id:'calendar.readonly',state:'off',attributes:{friendly_name:'Nur lesen',supported_features:0}}},callWS:async msg=>{
    if(msg.type==='stromtarif/list')return [{entry_id:'entry1',title:'Haushalt'}];
    if(msg.type==='stromtarif/history')return structuredClone(history);
    if(msg.type==='stromtarif/periods'){window.periodRequests.push(msg);return [{label:msg.unit==='month'?'2026-02':msg.unit==='quarter'?'2026 Q1':'2026',start:'2026-02-01',end:'2026-03-01',consumption:190,cost:70,effective_price:70/190,estimated:true,partial:msg.unit==='year'}];}
    if(msg.type==='stromtarif/history_preview')return {can_apply:false,issues:[{level:'error',text:'Grenzstand fehlt. Nachbarn: 1000 am 2026-01-01 und 1600 am 2026-04-01.'}],timeline:[],counts:{readings:3,tariffs:1,bills:0}};
    if(msg.type==='stromtarif/export')return {filename:'stromtarif.csv',csv:'Typ;Datum\nAblesung;2026-02-01'};
    if(msg.type==='stromtarif/update'){
     window.writes.push(msg);if(window.rejectWrite)throw new Error('Der Zählerstand darf nicht sinken.');
     history.ledger.revision++;
     if(msg.operation==='history_start')history.ledger.history_draft={base:'test',allow_estimates:false,readings:structuredClone(history.ledger.readings),tariffs:history.ledger.tariffs.map(t=>({...t,until:''})),bills:[],billing_start:history.ledger.billing_start,billing_until:'2026-12-31'};
     if(msg.operation==='history_save')history.ledger.history_draft=structuredClone(msg.values.draft);
     if(msg.operation==='reading_edit')history.ledger.readings[msg.values.index]={...history.ledger.readings[msg.values.index],date:msg.values.date,value:String(msg.values.reading)};
     if(msg.operation==='payment_settle'){const row=history.schedule.find(p=>p.key===msg.values.key);row.paid=true;history.ledger.payments.push({date:row.date,amount:row.amount,schedule_key:row.key});}
     if(msg.operation==='panel')history.ledger.show_panel=msg.values.show_panel;
     return {revision:history.ledger.revision};
    }
   }};
  });
  await page.getByRole('heading',{name:'Strompreis je Tarif'}).waitFor();
  assert.equal(await page.locator('stromtarif-panel').locator('img').count(),0);assert.equal(await page.evaluate(()=>window.XSS),undefined);
  assert.match(await page.evaluate(()=>document.querySelector('stromtarif-panel').shadowRoot.textContent),/36 ct\/kWh/);
  await page.getByLabel('Zeiteinheit').selectOption('quarter');await page.getByText('2026 Q1',{exact:true}).first().waitFor();
  await page.getByLabel('Zeiteinheit').selectOption('year');assert.equal(await page.evaluate(()=>window.periodRequests.at(-1).unit),'year');
  await page.getByLabel('Tarif',{exact:true}).selectOption('0');assert.equal(await page.evaluate(()=>window.periodRequests.at(-1).tariff_index),0);
  await page.getByRole('button',{name:'Ablesungen',exact:true}).click();
  assert.equal(await page.getByRole('row').filter({has:page.getByRole('button',{name:'Bearbeiten',exact:true})}).count(),3);
  await page.getByRole('row').filter({hasText:'2026-02-01'}).getByRole('button',{name:'Bearbeiten',exact:true}).click();
  await page.getByLabel('Zählerstand (kWh)',{exact:true}).fill('1300');await page.getByLabel('Ablesedatum',{exact:true}).fill('2026-02-10');
  await page.getByRole('button',{name:'Speichern',exact:true}).click();await page.getByText('2026-02-10',{exact:true}).waitFor();
  assert.deepEqual(await page.evaluate(()=>window.writes[0]),{type:'stromtarif/update',entry_id:'entry1',revision:3,operation:'reading_edit',values:{index:1,date:'2026-02-10',reading:1300}});
  await page.getByRole('row').filter({hasText:'2026-02-10'}).getByRole('button',{name:'Bearbeiten',exact:true}).click();
  await page.evaluate(()=>window.rejectWrite=true);await page.getByLabel('Zählerstand (kWh)',{exact:true}).fill('900');await page.getByRole('button',{name:'Speichern',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'Der Zählerstand darf nicht sinken.'}).waitFor();assert.equal(await page.getByLabel('Zählerstand (kWh)',{exact:true}).inputValue(),'900');
  await page.getByRole('button',{name:'Abbrechen',exact:true}).click();await page.evaluate(()=>window.rejectWrite=false);
  await page.getByRole('button',{name:'Nummer hinterlegen / korrigieren',exact:true}).click();await page.getByLabel('Zählernummer',{exact:true}).fill('OLD-CORRECTED');await page.getByRole('button',{name:'Speichern',exact:true}).click();
  await page.getByRole('button',{name:'Zähler wechseln',exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.writes.at(-1).values.meter_id),'meter_1');
  await page.getByRole('button',{name:'Zähler wechseln',exact:true}).click();await page.getByLabel('Neue Zählernummer',{exact:true}).fill('NEW-456');await page.getByLabel('Wechseldatum',{exact:true}).fill('2026-05-01');await page.getByLabel('Endstand des bisherigen Zählers (kWh)',{exact:true}).fill('1700');await page.getByLabel('Anfangsstand des neuen Zählers (kWh)',{exact:true}).fill('5');
  await page.getByRole('button',{name:'Speichern',exact:true}).click();await page.getByRole('button',{name:'Zähler wechseln',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.writes.at(-1).operation),'meter_replace');assert.equal(await page.evaluate(()=>window.writes.at(-1).values.new_reading),5);
  await page.getByRole('button',{name:'Einstellungen',exact:true}).click();
  await page.getByRole('button',{name:'Seitenleiste ein-/ausblenden'}).click();await page.getByLabel('DEr Stromtarif für dieses Tarifbuch in der Seitenleiste anzeigen').check();await page.getByRole('button',{name:'Speichern',exact:true}).click();
  await page.getByText('Eingeblendet',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Kalender und To-do-Liste ändern'}).click();assert.equal(await page.getByLabel('Kalender',{exact:true}).locator('option').count(),2);await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
  await page.getByRole('button',{name:'Tarife',exact:true}).click();await page.getByRole('button',{name:'Bearbeiten',exact:true}).click();await page.getByLabel('Tarifname',{exact:true}).fill('B');await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
  await page.getByRole('button',{name:'Abrechnung & Zahlungen',exact:true}).click();await page.getByRole('button',{name:'Ändern / entfernen'}).click();assert.equal(await page.getByLabel('Gewünschtes Zahlungsdatum').inputValue(),'2026-02-17');await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
  await page.getByRole('button',{name:'Ändern / entfernen'}).click();await page.getByLabel('Am Fälligkeitstag automatisch als bezahlt verbuchen').check();await page.getByRole('button',{name:'Speichern',exact:true}).click();
  await page.getByRole('button',{name:'Als bezahlt markieren',exact:true}).waitFor();assert.equal(await page.evaluate(()=>window.writes.at(-1).values.auto_pay),true);
  await page.getByRole('button',{name:'Als bezahlt markieren',exact:true}).click();await page.getByText('Bezahlt',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.writes.at(-1).operation),'payment_settle');assert.equal(await page.getByRole('button',{name:'Als bezahlt markieren',exact:true}).count(),0);
  await page.getByRole('row').filter({hasText:'2026-02-17'}).filter({has:page.getByRole('button',{name:'Bearbeiten',exact:true})}).getByRole('button',{name:'Bearbeiten',exact:true}).click();
  assert.equal(await page.getByLabel('Tatsächlich bezahlter Betrag (EUR)').inputValue(),'83');await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
  await page.getByRole('button',{name:'Periodenabrechnung erfassen',exact:true}).click();
  assert.equal(await page.getByLabel('Stichtag / Ende (exklusiv)').inputValue(),'2027-01-01');
  await page.getByLabel('Rechnungsbetrag (EUR)',{exact:true}).fill('1080');await page.getByLabel('Ausgewiesener Saldo (EUR)',{exact:true}).fill('25');
  await page.getByLabel('Stichtag / Ende (exklusiv)').fill('2026-10-01');await page.getByLabel('Nächste Rechnungsperiode zum jährlichen Stichtag beginnen').uncheck();
  await page.getByRole('button',{name:'Speichern',exact:true}).click();await page.getByRole('button',{name:'Periodenabrechnung erfassen',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.writes.at(-1).operation),'bill_add');assert.equal(await page.evaluate(()=>window.writes.at(-1).values.invoice_total),1080);assert.equal(await page.evaluate(()=>window.writes.at(-1).values.advance),false);
  await page.getByRole('button',{name:'Abschlag ab Datum ändern',exact:true}).click();
  await page.getByLabel('Gültig ab',{exact:true}).fill('2027-01-01');await page.getByLabel('Neuer monatlicher Abschlag (EUR)',{exact:true}).fill('115');
  await page.getByRole('button',{name:'Speichern',exact:true}).click();await page.getByRole('button',{name:'Abschlag ab Datum ändern',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.writes.at(-1).operation),'installment_change');assert.deepEqual(await page.evaluate(()=>window.writes.at(-1).values),{date:'2027-01-01',amount:115});
  await page.getByRole('button',{name:'Abrechnung und Zahlungsplan ändern',exact:true}).click();assert.equal(await page.getByLabel('Abschlag gültig ab',{exact:true}).count(),1);await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
  await page.getByRole('button',{name:'Tarife',exact:true}).click();
  await page.getByRole('button',{name:'Neuen Tarif anlegen',exact:true}).click();
  assert.equal(await page.getByLabel('Rechnungsbetrag (EUR)',{exact:true}).count(),0);
  await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
  await page.getByRole('button',{name:'Historische Daten',exact:true}).click();
  await page.getByRole('button',{name:'Entwurf beginnen',exact:true}).click();
  await page.getByRole('button',{name:'Speichern',exact:true}).click();
  await page.getByRole('button',{name:'2 · Tarife',exact:true}).click();
  await page.getByRole('button',{name:'Tarif zum Entwurf hinzufügen',exact:true}).click();
  assert.equal(await page.getByLabel('Rechnungsbetrag (EUR)',{exact:true}).count(),0);
  await page.getByLabel('Tarifname',{exact:true}).fill('Alter Tarif');
  await page.getByRole('button',{name:'Speichern',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.writes.at(-1).operation),'history_save');
  assert.equal(await page.evaluate(()=>window.writes.at(-1).values.draft.tariffs.at(-1).name),'Alter Tarif');
  await page.getByRole('button',{name:'3 · Rechnungen',exact:true}).click();
  await page.getByRole('button',{name:'Rechnung zum Entwurf hinzufügen',exact:true}).click();
  await page.getByLabel('Saldo: Nachzahlung (+), Guthaben (−)',{exact:true}).fill('-25');
  await page.getByRole('button',{name:'Speichern',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.writes.at(-1).values.draft.bills[0].balance),-25);
  await page.getByRole('button',{name:'4 · Prüfen und übernehmen',exact:true}).click();
  assert.equal(await page.getByRole('button',{name:'Geprüfte Historie übernehmen',exact:true}).count(),0);
  await page.getByText('Übernahme gesperrt, solange Fehler offen sind. Entwurf bleibt erhalten.',{exact:true}).waitFor();
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Historie als CSV herunterladen'}).click();assert.equal((await download).suggestedFilename(),'stromtarif.csv');
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Ablesungen',exact:true}).click();
  assert.ok(await page.evaluate(()=>document.querySelector('stromtarif-panel').shadowRoot.querySelector('.scroll').scrollWidth > document.querySelector('stromtarif-panel').shadowRoot.querySelector('.scroll').clientWidth));
  assert.deepEqual(errors,[]);
  await page.setViewportSize({width:1280,height:1200});await page.getByRole('button',{name:'Übersicht',exact:true}).click();
  await page.screenshot({path:'/tmp/stromtarif-panel-test.png',fullPage:true});
  console.log('Panel: periods, tariff price, row editing, validation errors, sidebar option, entity filters, CSV, escaping and mobile layout passed');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
