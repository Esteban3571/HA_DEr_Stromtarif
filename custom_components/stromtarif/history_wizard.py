"""Staged historical ledger: incomplete drafts, diagnostics and explicit adoption."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from . import model as m

FIELDS = ('readings','tariffs','meters','bills','billing_start','billing_end','billing_cutoff')

def fingerprint(data):
    return hashlib.sha256(json.dumps({k:data.get(k) for k in FIELDS},sort_keys=True).encode()).hexdigest()

def inclusive(when):
    return (date.fromisoformat(when)-timedelta(days=1)).isoformat() if when else ''

def seed(data):
    return {'base':fingerprint(data),'allow_estimates':False,
        'readings':deepcopy(data['readings']),
        'tariffs':[{'name':t['name'],'start':t['start'],'until':inclusive(t.get('end')),'price':t.get('price'),'monthly_fee':t.get('monthly_fee')} for t in data['tariffs']],
        'bills':[dict(deepcopy(b),until=inclusive(b['end'])) for b in data['bills']],
        'billing_start':data['billing_start'],'billing_until':inclusive(data['billing_end'])}

def save(data, draft):
    if not isinstance(draft,dict) or not isinstance(draft.get('allow_estimates'),bool):
        raise ValueError('invalid_input')
    if any(not isinstance(draft.get(k),list) or len(draft[k])>2000 or any(not isinstance(r,dict) for r in draft[k]) for k in ('readings','tariffs','bills')):
        raise ValueError('invalid_input')
    if draft.get('base') != (data.get('history_draft') or seed(data))['base']:
        raise ValueError('invalid_input')
    if len(json.dumps(draft))>1000000:
        raise ValueError('invalid_input')
    data['history_draft']=deepcopy(draft)

def preview(data, today):
    draft=data.get('history_draft') or seed(data)
    issues=[];timeline=[];candidate=deepcopy(data)
    def issue(level,text,section='',index=None):issues.append({'level':level,'text':text,'section':section,'index':index})
    def when(value,label,section,index,future=False):
        try:
            parsed=date.fromisoformat(str(value))
            if not future and parsed>today:raise ValueError()
            return parsed.isoformat()
        except (ValueError,TypeError):issue('error',label+': Datum fehlt, ist ungültig oder liegt in der Zukunft.',section,index);return None
    def amount(value,label,section,index):
        if value in ('',None):return None
        try:return m.number(value)
        except ValueError:issue('error',label+': Betrag muss eine endliche, nicht negative Zahl sein.',section,index);return None
    if draft['base'] != fingerprint(data):issue('error','Die aktive Historie wurde seit Beginn des Entwurfs geändert. Neuen Entwurf aus dem aktuellen Stand beginnen; es wird nichts überschrieben.')
    readings=[];meters=[];ids={}
    for i,row in enumerate(draft['readings']):
        day=when(row.get('date'),'Ablesung', 'readings',i);value=amount(row.get('value'),'Zählerstand','readings',i)
        number=str(row.get('meter_number') or '').strip()
        if not number:issue('warning','Ablesung '+str(i+1)+': Zählernummer noch nicht hinterlegt.','readings',i)
        if number not in ids:
            ids[number]='meter_'+str(len(ids)+1);meters.append({'id':ids[number],'number':number})
        if value is None:issue('error','Ablesung '+str(i+1)+': Zählerstand fehlt. Der Entwurf kann trotzdem gespeichert werden.','readings',i)
        if day and value is not None:readings.append({'date':day,'value':value,'meter_id':ids[number],'meter_number':number,'kind':'manual','estimated':bool(row.get('estimated',False))})
    readings.sort(key=lambda r:r['date'])
    for i,r in enumerate(readings):
        if not i:r['kind']='initial';continue
        before=readings[i-1]
        if r['meter_id']!=before['meter_id']:
            if r['date']!=before['date']:issue('error',f"Zählerwechsel zwischen {before['meter_number']} ({before['date']}) und {r['meter_number']} ({r['date']}): End- und Anfangsstand am gleichen Datum ergänzen.")
            else:before['kind']='meter_end';r['kind']='meter_start'
        elif r['date']<=before['date']:issue('error',f"Zähler {r['meter_number']}: mehrere Stände am {r['date']}; einen Eintrag korrigieren oder entfernen.")
        elif Decimal(r['value'])<Decimal(before['value']):issue('error',f"Stand {r['value']} am {r['date']} liegt unter {before['value']} vom {before['date']}. Zählernummer oder Stand prüfen.")
    if not readings:issue('error','Mindestens eine vollständige Ablesung ist nötig.')
    tariffs=[]
    for i,row in enumerate(draft['tariffs']):
        start=when(row.get('start'),'Tarifbeginn','tariffs',i)
        until=when(row.get('until'),'Tarifende','tariffs',i) if row.get('until') else None
        end=(date.fromisoformat(until)+timedelta(days=1)).isoformat() if until else None
        name=str(row.get('name') or '').strip()
        if not name:issue('error','Tarif '+str(i+1)+': Namen ergänzen.','tariffs',i)
        if start and end and end<=start:issue('error',f"{name}: Ende einschließlich {until} liegt vor Beginn {start}.",'tariffs',i)
        price=amount(row.get('price'),'Arbeitspreis','tariffs',i);monthly=amount(row.get('monthly_fee'),'Grundgebühr','tariffs',i)
        if price is None or monthly is None:issue('warning',f"{name or 'Tarif'}: Preis oder Grundgebühr unbekannt; betroffene Kosten sind nicht berechenbar.",'tariffs',i)
        if start:tariffs.append({'name':name,'start':start,'end':end,'price':price,'monthly_fee':monthly,'index':i})
    tariffs.sort(key=lambda t:t['start'])
    if not tariffs:issue('error','Mindestens einen Tarif oder einen ausdrücklich unbekannten Zeitraum anlegen.')
    expanded=[]
    if readings and tariffs and tariffs[0]['start']>readings[0]['date']:
        expanded.append({'name':'Unbekannter Zeitraum','start':readings[0]['date'],'end':tariffs[0]['start'],'price':None,'monthly_fee':None,'unknown':True})
        issue('warning',f"Vor dem ersten Tarif: {readings[0]['date']} bis {inclusive(tariffs[0]['start'])} ohne bekannte Tarifdaten.")
    for i,t in enumerate(tariffs):
        expanded.append(t)
        if i+1<len(tariffs):
            nxt=tariffs[i+1]
            if t['end'] is None:
                issue('error',f"{t['name']}: offenes Ende vor {nxt['name']}. Vorgeschlagenes Ende einschließlich: {inclusive(nxt['start'])}.",'tariffs',t['index'])
            elif t['end']>nxt['start']:
                days=(date.fromisoformat(t['end'])-date.fromisoformat(nxt['start'])).days
                issue('error',f"{t['name']} überschneidet {nxt['name']} um {days} Tage. Ende einschließlich {inclusive(nxt['start'])} oder nächsten Beginn {t['end']} wählen.",'tariffs',t['index'])
            elif t['end']<nxt['start']:
                expanded.append({'name':'Unbekannter Zeitraum','start':t['end'],'end':nxt['start'],'price':None,'monthly_fee':None,'unknown':True})
                issue('warning',f"Lücke {t['end']} bis {inclusive(nxt['start'])}: als unbekannter Tarif übernommen, Kosten nicht berechenbar.")
    if readings and expanded and expanded[-1]['end'] and expanded[-1]['end']<readings[-1]['date']:
        expanded.append({'name':'Unbekannter Zeitraum','start':expanded[-1]['end'],'end':readings[-1]['date'],'price':None,'monthly_fee':None,'unknown':True})
        issue('warning','Nach dem letzten bekannten Tarif wird der erfasste Zeitraum als unbekannt übernommen.')
    def boundary(day):
        matches=[r for r in readings if r['date']==day]
        if matches:return matches[-1]
        for before,after in zip(readings,readings[1:]):
            if before['date']<day<after['date'] and before['meter_id']==after['meter_id']:
                if not draft['allow_estimates']:
                    issue('error',f"Grenzstand am {day} fehlt. Nachbarn: {before['value']} am {before['date']} und {after['value']} am {after['date']} ({before['meter_number']}). Stand ergänzen oder Schätzung ausdrücklich einschalten.");return None
                fraction=Decimal((date.fromisoformat(day)-date.fromisoformat(before['date'])).days)/Decimal((date.fromisoformat(after['date'])-date.fromisoformat(before['date'])).days)
                row=dict(before,date=day,value=str(Decimal(before['value'])+(Decimal(after['value'])-Decimal(before['value']))*fraction),kind='estimated',estimated=True)
                readings.append(row);readings.sort(key=lambda r:r['date']);issue('warning',f"Grenzstand am {day}: {row['value']} kWh zeitanteilig geschätzt ({row['meter_number']}).")
                return row
        issue('error',f"Grenzstand am {day} fehlt; kein passendes Ablesepaar vorhanden. Keine Hochrechnung außerhalb bekannter Stände.");return None
    built=[]
    for t in expanded:
        begin=boundary(t['start']) if readings else None
        finish=boundary(t['end']) if t['end'] and readings else None
        timeline.append({'name':t['name'],'start':t['start'],'until':inclusive(t['end']),'unknown':t.get('unknown',False),'cost_known':t['price'] is not None and t['monthly_fee'] is not None})
        if not begin or t['end'] and not finish:continue
        row={k:v for k,v in t.items() if k not in ('index','end')}
        row.update(reading=begin['value'],meter_id=begin['meter_id'],active=t['end'] is None)
        if finish:row.update(end=t['end'],end_reading=finish['value'],end_meter_id=finish['meter_id'])
        built.append(row)
    bills=[]
    for i,row in enumerate(draft['bills']):
        start=when(row.get('start'),'Rechnungsbeginn','bills',i);until=when(row.get('until'),'Rechnungsende','bills',i)
        total=amount(row.get('invoice_total'),'Rechnungsbetrag','bills',i)
        try:balance=str(Decimal(str(row.get('balance'))));assert Decimal(balance).is_finite()
        except (ValueError,AssertionError,m.InvalidOperation):balance=None
        if total is None or balance is None:issue('error','Rechnung '+str(i+1)+': Betrag oder ausgewiesener Saldo fehlt. Entwurf kann gespeichert werden.','bills',i)
        if start and until:
            end=(date.fromisoformat(until)+timedelta(days=1)).isoformat()
            if end<=start:issue('error','Rechnungsende liegt vor dem Beginn.','bills',i)
            if any(start<b['end'] and end>b['start'] for b in bills):issue('error','Rechnung '+str(i+1)+' überschneidet eine andere Rechnung.','bills',i)
            if total is not None and balance is not None:bills.append({'kind':'period','tariff':str(row.get('tariff') or 'Lieferantenrechnung'),'start':start,'end':end,'reading':row.get('reading',''),'invoice_total':total,'balance':balance})
    billing_start=when(draft.get('billing_start'),'Aktuelle Periode: Beginn','period',None)
    billing_until=when(draft.get('billing_until'),'Aktuelle Periode: Ende','period',None,future=True)
    if billing_start and billing_until:
        billing_end=(date.fromisoformat(billing_until)+timedelta(days=1)).isoformat()
        if billing_end<=billing_start or readings and billing_start<readings[0]['date']:issue('error','Aktuelle Rechnungsperiode: Ende muss nach Beginn und Beginn ab erster Ablesung liegen.','period')
        candidate.update(billing_start=billing_start,billing_end=billing_end,billing_cutoff=billing_end[5:])
    candidate.update(readings=readings,tariffs=built,meters=meters,bills=bills)
    if not any(i['level']=='error' for i in issues):
        try:m.validate_history(candidate,today)
        except (ValueError,KeyError,IndexError) as err:issue('error','Historie noch nicht übernehmbar: '+str(err))
    errors=[i for i in issues if i['level']=='error']
    return {'issues':issues,'timeline':timeline,'can_apply':not errors,
        'summary':m.totals(candidate) if not errors else None,
        'counts':{'readings':len(readings),'tariffs':len(built),'bills':len(bills)},'_candidate':candidate}

def adopt(data,today):
    result=preview(data,today)
    if not result['can_apply']:raise ValueError('history_invalid')
    data['history_backup']={k:deepcopy(data[k]) for k in FIELDS}
    for k in FIELDS:data[k]=deepcopy(result['_candidate'][k])
    data.update(source=None,notified_due=None,notified_billing_end=None)
    data.pop('history_draft',None)

def restore(data):
    backup=data.get('history_backup')
    if not backup:raise ValueError('invalid_input')
    for k in FIELDS:data[k]=deepcopy(backup[k])
    data.update(source=None,notified_due=None,notified_billing_end=None)
    data.pop('history_backup',None);data.pop('history_draft',None)
