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
      ${row('Kosten bis '+(f.observed_until||'zur ersten Ablesung'),money(f.period_cost))}${row('Tatsächlich bezahlte Abschläge',money(f.paid))}${row('Saldo bisher (Kosten − Zahlungen)',money(f.balance))}${row('Monatlicher Abschlag',money(Number(l.monthly_installment)))}${row('Geplante Zahlungen gesamte Periode',money(f.planned))}${row('Kostenprognose gesamte Periode',money(f.forecast_cost))}${row('Prognose Nachzahlung (+) / Guthaben (−)',money(f.forecast_balance))}
      <p class="hint">Prognose anhand des bisherigen Tagesverbrauchs und aktuellen Tarifs, ohne saisonale Anpassung. Geplante Zahlungen sind keine bestätigten Zahlungen.${f.partial_period_estimate?' Verbrauch an einer Periodengrenze ist zeitanteilig geschätzt.':''}</p>
      <p class="hint">${reminder_error?'Erinnerungen gestört: '+esc(reminder_error):''}</p><h3>Geplante Abschlagstermine</h3>${table(['Datum','Betrag','Ursprüngliches Datum'],schedule.map(p=>[p.date,money(Number(p.amount)),p.key]))}<h3>Endabrechnungen</h3>${table(['Tarif','Von','Bis (exklusiv)','Rechnungsbetrag','Nachzahlung (+) / Guthaben (−)'],(l.bills||[]).map(b=>[b.tariff,b.start,b.end,money(Number(b.invoice_total)),money(Number(b.balance))]))}<h3>Tarifhistorie</h3>${table(['Ab','Tarif','Status','EUR/kWh','EUR/Monat'],[...l.tariffs].reverse().map(t=>[t.start,t.name,t.active===false?'Inaktiv':'Aktiv',value(t.price),money(Number(t.monthly_fee))]))}
      <h3>Ablesungen</h3>${table(['Datum','kWh','Art'],[...l.readings].reverse().map(r=>[r.date,value(r.value),r.kind]))}
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
