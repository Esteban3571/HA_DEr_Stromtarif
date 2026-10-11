/* DEr Stromtarif dashboard card; data stays in authenticated HA WebSocket. */
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
class StromtarifCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._busy=false; this._selected=null; }
  setConfig(config) { this._config=config; this._selected=config.entry_id || null; this._last=0; }
  set hass(hass) { this._hass=hass; if (this.isConnected && !this._busy && Date.now()-(this._last||0)>30000) this.refresh(); }
  connectedCallback() { this._timer=setInterval(()=>this.refresh(),30000); if(this._hass)this.refresh(); }
  disconnectedCallback() { clearInterval(this._timer); }
  getCardSize() { return 8; }
  async refresh() {
    if(!this._hass||this._busy||!this.isConnected)return;
    this._busy=true;
    try {
      const entries=await this._hass.callWS({type:'stromtarif/list'});
      if(!this._selected && entries.length)this._selected=entries[0].entry_id;
      if(!entries.length)throw new Error('Kein Tarifbuch geladen. Integration zuerst einrichten.');
      this._entries=entries;
      this._data=await this._hass.callWS({type:'stromtarif/history',entry_id:this._selected});
      this._last=Date.now(); this.render();
    } catch(error) { this.shadowRoot.innerHTML=`<ha-card><div style="padding:20px">${esc(error.message||error)}<p>Diese Karte benötigt ein Administratorkonto.</p><button id="retry">Erneut laden</button></div></ha-card>`;this.shadowRoot.querySelector('#retry').onclick=()=>this.refresh(); }
    finally {this._busy=false;}
  }
  async exportCSV() {
    const button=this.shadowRoot.querySelector('#export');button.disabled=true;
    try {
      const result=await this._hass.callWS({type:'stromtarif/export',entry_id:this._selected});
      const url=URL.createObjectURL(new Blob(['\ufeff'+result.csv],{type:'text/csv;charset=utf-8'}));
      const link=document.createElement('a');link.href=url;link.download=result.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    } catch(error) {this.shadowRoot.querySelector('#status').textContent='Export fehlgeschlagen: '+(error.message||error);}
    finally {button.disabled=false;}
  }
  render() {
    const {ledger:l,finances:f,intervals,due,source_error,schedule=[],reminder_error,tariff_summaries=[]}=this._data;
    const money=v=>v===null?'Noch keine Prognose':new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR'}).format(v);
    const value=v=>new Intl.NumberFormat('de-DE',{maximumFractionDigits:4}).format(Number(v));
    const t=l.tariffs[l.tariffs.length-1],last=l.readings[l.readings.length-1];
    const row=(a,b)=>`<div class="row"><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`;
    const table=(headers,rows)=>`<div class="scroll"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
    this.shadowRoot.innerHTML=`<style>:host{display:block}ha-card{padding:20px}h2{margin:0 0 16px;color:#f57c00}h3{margin-top:24px}.row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid var(--divider-color,#ddd)}.row strong{text-align:right;min-width:0;overflow-wrap:anywhere}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--divider-color,#ddd)}button,select{padding:10px;border-radius:8px;background:var(--card-background-color,white);color:var(--primary-text-color,#222);border:1px solid var(--divider-color,#aaa)}button{cursor:pointer}.hint{color:var(--secondary-text-color,#666);font-size:13px}</style><ha-card>
      <h2>DEr Stromtarif</h2><select id="entry">${this._entries.map(e=>`<option value="${esc(e.entry_id)}" ${e.entry_id===this._selected?'selected':''}>${esc(e.title)}</option>`).join('')}</select>
      ${row('Aktueller Tarif',t.name)}${row('Tarifstatus',t.active===false?'Inaktiv':'Aktiv')}${row('Arbeitspreis',value(t.price)+' EUR/kWh')}${tariff_summaries.length?row('Effektiver Strompreis inkl. Grundgebühr',tariff_summaries.at(-1).effective_price==null?'Noch kein Verbrauch':value(tariff_summaries.at(-1).effective_price*100)+' ct/kWh'):''}${row('Grundgebühr',money(Number(t.monthly_fee))+' / Monat')}${row('Letzte Ablesung',last.date+' · '+value(last.value)+' kWh')}${row('Nächste Ablesung',t.active===false?'Keine Erinnerung':due)}
      <p class="hint">${esc(l.source?'Automatischer Sensor: '+l.source.entity_id:'Manuelle Ablesung')}${source_error?' · Störung: '+esc(source_error):''}</p>
      <h3>Abrechnung ${esc(l.billing_start)} – ${esc(l.billing_end)}</h3>
      ${row('Kosten bis '+(f.observed_until||'zur ersten Ablesung'),money(f.period_cost))}${row('Tatsächlich bezahlte Abschläge',money(f.paid))}${row('Saldo bisher (Kosten − Zahlungen)',money(f.balance))}${row('Monatlicher Abschlag',money(Number(this._data.current_installment ?? l.monthly_installment)))}${row('Geplante Zahlungen gesamte Periode',money(f.planned))}${row('Kostenprognose gesamte Periode',money(f.forecast_cost))}${row('Prognose Nachzahlung (+) / Guthaben (−)',money(f.forecast_balance))}
      <p class="hint">Prognose anhand des bisherigen Tagesverbrauchs und aktuellen Tarifs, ohne saisonale Anpassung. Geplante Zahlungen sind keine bestätigten Zahlungen.${f.partial_period_estimate?' Verbrauch an einer Periodengrenze ist zeitanteilig geschätzt.':''}</p>
      <p class="hint">${reminder_error?'Erinnerungen gestört: '+esc(reminder_error):''}</p><h3>Geplante Abschlagstermine</h3>${table(['Datum','Betrag','Ursprüngliches Datum'],schedule.map(p=>[p.date,money(Number(p.amount)),p.key]))}<h3>Rechnungen</h3>${table(['Art','Tarif','Von','Bis (exklusiv)','Rechnungsbetrag','Nachzahlung (+) / Guthaben (−)'],(l.bills||[]).map(b=>[b.kind==='period'?'Periodenabrechnung':'Endabrechnung',b.tariff,b.start,b.end,money(Number(b.invoice_total)),money(Number(b.balance))]))}<h3>Tarifhistorie</h3>${table(['Ab','Tarif','Status','EUR/kWh','EUR/Monat'],[...l.tariffs].reverse().map(t=>[t.start,t.name,t.active===false?'Inaktiv':'Aktiv',value(t.price),money(Number(t.monthly_fee))]))}
      <h3>Ablesungen</h3>${table(['Datum','Zählernummer','kWh','Art'],[...l.readings].reverse().map(r=>[r.date,r.meter_number||'Nicht hinterlegt',value(r.value),r.kind]))}
      <h3>Verbrauch und Kosten je Ablesezeitraum</h3>${table(['Von','Bis','Tarif','kWh','Kosten'],[...intervals].reverse().map(i=>[i.from,i.to,i.tariff,value(i.consumption),money(i.total_cost)]))}
      <h3>Zahlungen</h3>${table(['Datum','Betrag'],[...l.payments].reverse().map(p=>[p.date,money(Number(p.amount))]))}
      <p><a href="/stromtarif?entry_id=${encodeURIComponent(this._selected)}">Verwaltung öffnen</a></p><p><button id="export">Historie als CSV herunterladen</button> <button id="refresh">Aktualisieren</button></p><p id="status" class="hint">Änderungen: Einstellungen → Geräte & Dienste → DEr Stromtarif → Konfigurieren.</p>
    </ha-card>`;
    this.shadowRoot.querySelector('#entry').onchange=e=>{this._selected=e.target.value;this.refresh();};
    this.shadowRoot.querySelector('#export').onclick=()=>this.exportCSV();this.shadowRoot.querySelector('#refresh').onclick=()=>this.refresh();
  }
}
customElements.define('stromtarif-card',StromtarifCard);
window.customCards=window.customCards||[];
window.customCards.push({type:'stromtarif-card',name:'DEr Stromtarif',description:'Tarife, Ablesungen, Abschläge, Prognose und CSV-Export'});

/* Compact reading input; shares the authenticated, revision-protected ledger API. */
class StromtarifReadingCard extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._busy=false;this._draft={};}
  setConfig(config){this._config=config;this._selected=config.entry_id||null;this._data=null;this._draft={};if(this._hass&&this.isConnected)this.refresh();}
  set hass(value){this._hass=value;if(this.isConnected&&!this._data&&!this._busy)this.refresh();}
  connectedCallback(){if(this._hass&&!this._data)this.refresh();}
  getCardSize(){return 4;}
  today(){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:this._hass?.config?.time_zone||'Europe/Berlin',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());return ['year','month','day'].map(k=>parts.find(p=>p.type===k).value).join('-');}
  async refresh(){
    if(!this._hass||this._busy)return;this._busy=true;this.controls(true);
    try{
      this._entries=await this._hass.callWS({type:'stromtarif/list'});
      if(!this._selected)this._selected=this._entries[0]?.entry_id;
      if(!this._entries.some(e=>e.entry_id===this._selected))throw new Error('Tarifbuch nicht verfügbar. Auswahl bzw. entry_id prüfen.');
      this._data=await this._hass.callWS({type:'stromtarif/history',entry_id:this._selected});this.render();
    }catch(error){this._notice=error.message||String(error);if(this._data)this.message();else{this.shadowRoot.innerHTML='<ha-card style="padding:20px"><h2>Zählerstand erfassen</h2><p role="alert"></p><p>Diese Karte benötigt ein Administratorkonto.</p><button>Erneut laden</button></ha-card>';this.shadowRoot.querySelector('[role=alert]').textContent=this._notice;this.shadowRoot.querySelector('button').onclick=()=>this.refresh();}}
    finally{this._busy=false;this.controls(false);}
  }
  controls(disabled){this.shadowRoot.querySelectorAll('button,input,select').forEach(e=>e.disabled=disabled);const save=this.shadowRoot.querySelector('#save-reading');if(save&&this._data?.ledger.tariffs.at(-1).active===false)save.disabled=true;}
  message(){const e=this.shadowRoot.querySelector('#reading-message');if(e)e.textContent=this._notice||'';}
  render(){
    const l=this._data.ledger,last=l.readings.at(-1),inactive=l.tariffs.at(-1).active===false;
    this.shadowRoot.innerHTML=`<style>:host{display:block}ha-card{padding:20px}h2{margin:0 0 16px;color:#f57c00}label{display:grid;gap:6px;margin:14px 0}input,select,button{box-sizing:border-box;max-width:100%;font:inherit;padding:10px;border-radius:8px;border:1px solid var(--divider-color,#aaa);color:var(--primary-text-color,#222);background:var(--card-background-color,white)}input,select{width:100%}button{cursor:pointer}.primary{background:#ef7800;color:white}button:disabled{opacity:.5;cursor:default}.hint{color:var(--secondary-text-color,#666);overflow-wrap:anywhere}footer{display:flex;gap:10px;flex-wrap:wrap}</style><ha-card><h2>${esc(this._config?.title||'Zählerstand erfassen')}</h2>
      <label>Tarifbuch<select id="reading-entry" aria-label="Tarifbuch">${this._entries.map(e=>`<option value="${esc(e.entry_id)}" ${e.entry_id===this._selected?'selected':''}>${esc(e.title)}</option>`).join('')}</select></label>
      <p class="hint">Zählernummer: <strong>${esc(last.meter_number||'Noch nicht hinterlegt')}</strong><br>Letzter Stand: ${esc(last.value)} kWh am ${esc(last.date)}</p>
      ${inactive?'<p>Tarif ist inaktiv. Im Verwaltungs-Panel prüfen.</p>':''}
      <form id="reading-form"><label>Ablesedatum<input aria-label="Ablesedatum" id="reading-date" type="date" required max="${this.today()}" value="${esc(this._draft.date||this.today())}"></label><label>Zählerstand (kWh)<input aria-label="Zählerstand (kWh)" id="reading-value" type="number" min="0" step="any" required placeholder="Aktuellen Stand eingeben" value="${esc(this._draft.value??'')}"></label><footer><button class="primary" id="save-reading" type="submit">Zählerstand speichern</button><button id="reload-reading" type="button">Aktualisieren</button></footer></form>
      <p id="reading-message" role="status" aria-live="polite"></p><p class="hint">Am Datum der letzten normalen Ablesung wird deren Stand korrigiert. Zählerwechsel und Grenzstände im Verwaltungs-Panel bearbeiten.</p><a href="/stromtarif?entry_id=${encodeURIComponent(this._selected)}">Verwaltung öffnen</a></ha-card>`;
    this.message();
    for(const [id,key] of [['reading-date','date'],['reading-value','value']])this.shadowRoot.querySelector('#'+id).oninput=e=>this._draft[key]=e.target.value;
    this.shadowRoot.querySelector('#reading-entry').onchange=async e=>{this._selected=e.target.value;this._draft={};this._data=null;this._notice='';await this.refresh();};
    this.shadowRoot.querySelector('#reload-reading').onclick=()=>this.refresh();
    this.shadowRoot.querySelector('#reading-form').onsubmit=e=>{e.preventDefault();this.saveReading();};this.controls(this._busy);
  }
  async saveReading(){
    if(this._busy||!this._data)return;const l=this._data.ledger,last=l.readings.at(-1);
    if(l.tariffs.at(-1).active===false)return;
    const date=this.shadowRoot.querySelector('#reading-date').value,reading=this.shadowRoot.querySelector('#reading-value').value;
    this._draft={date,value:reading};
    if(!date||reading===''||!Number.isFinite(Number(reading))||Number(reading)<0){this._notice='Bitte Datum und einen gültigen Zählerstand eingeben.';this.message();return;}
    if(date===last.date&&!['manual','automatic'].includes(last.kind)){this._notice='Anfangs- und Grenzstände bitte im Verwaltungs-Panel korrigieren.';this.message();return;}
    const values={date,reading},operation=date===last.date?'reading_edit':'reading_add';if(operation==='reading_edit')values.index=l.readings.length-1;
    this._busy=true;this.controls(true);
    try{await this._hass.callWS({type:'stromtarif/update',entry_id:this._selected,revision:l.revision,operation,values});this._draft={};this._notice='Zählerstand gespeichert.';this._busy=false;await this.refresh();}
    catch(error){this._notice=error.message||String(error);this.message();}
    finally{this._busy=false;this.controls(false);}
  }
}
customElements.define('stromtarif-reading-card',StromtarifReadingCard);
window.customCards.push({type:'stromtarif-reading-card',name:'DEr Stromtarif – Zählerstand erfassen',description:'Aktuellen Zählerstand mit Datum direkt im Dashboard speichern'});
