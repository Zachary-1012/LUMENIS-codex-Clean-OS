"""Narrow inert-HTML research extractor, not a validating/general XBRL engine."""
from html.parser import HTMLParser
from pathlib import Path
import re,json,hashlib
from decimal import Decimal
ROOT=Path(__file__).resolve().parent
class Facts(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.open=[];self.facts=[];self.text=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('ix:nonfraction','ix:nonnumeric'):self.open.append([tag,dict(attrs),[],self.getpos()])
 def handle_data(self,d):
  self.text.append(d)
  for item in self.open:item[2].append(d)
 def handle_endtag(self,tag):
  if self.open and self.open[-1][0]==tag:
   tag,a,ch,pos=self.open.pop();a.update(raw_display=''.join(ch),source_line=pos[0],source_column=pos[1]);self.facts.append(a)
def clean(t):return re.sub('<[^>]*>','',t)
def load(name):
 raw=(ROOT/'originals'/name).read_text();p=Facts();p.feed(raw);contexts={}
 for id,body in re.findall(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>',raw,re.S):
  contexts[id]={'entity':re.findall(r'<xbrli:identifier[^>]*>(.*?)</xbrli:identifier>',body),'start':re.findall(r'<xbrli:startdate>(.*?)</xbrli:startdate>',body),'end':re.findall(r'<xbrli:enddate>(.*?)</xbrli:enddate>',body),'instant':re.findall(r'<xbrli:instant>(.*?)</xbrli:instant>',body),'dimensions':re.findall(r'<xbrldi:explicitmember dimension="([^"]+)">(.*?)</xbrldi:explicitmember>',body)}
 units=dict(re.findall(r'<xbrli:unit id="([^"]+)">(.*?)</xbrli:unit>',raw,re.S))
 chosen=[]
 for f in p.facts:
  if f.get('name') in ['us-gaap:MarketingAndAdvertisingExpense','us-gaap:PrepaidAdvertising','dei:DocumentPeriodEndDate','dei:AmendmentFlag','dei:EntityRegistrantName','dei:EntityCentralIndexKey','dei:DocumentType']:
   f['context']=contexts.get(f.get('contextref'));f['unit_definition']=clean(units.get(f.get('unitref'),''))
   if 'scale' in f:f['normalized_value']=str(Decimal(f['raw_display'].replace(',',''))*(Decimal(10)**int(f['scale']))*(-1 if f.get('sign')=='-' else 1))
   chosen.append(f)
 return {'filename':name,'sha256':hashlib.sha256((ROOT/'originals'/name).read_bytes()).hexdigest(),'selected_facts':chosen,'contexts':contexts},' '.join(p.text)
a,ta=load('nke-20250531.htm');b,tb=load('nke-20260531.htm');c,tc=load('nke-20250728.htm')
def cons(x,end):return [f for f in x['selected_facts'] if f.get('name')=='us-gaap:MarketingAndAdvertisingExpense' and f['context']['end']==[end] and not f['context']['dimensions']]
checks={
 '2025_consolidated_expense_4689m':all(f['normalized_value']=='4689000000' for f in cons(a,'2025-05-31')) and len(cons(a,'2025-05-31'))==3,
 '2025_repeated_in_2026_same_value':all(f['normalized_value']=='4689000000' for f in cons(b,'2025-05-31')) and bool(cons(b,'2025-05-31')),
 '2026_expense_4754m':all(f['normalized_value']=='4754000000' for f in cons(b,'2026-05-31')) and bool(cons(b,'2026-05-31')),
 'context_id_not_cross_document_key':a['contexts']['c-288']!=b['contexts']['c-288'],
 'fiscal_2025_not_calendar_2025':cons(a,'2025-05-31')[0]['context']['start']==['2024-06-01'],
 'USD_not_millions_unit':cons(a,'2025-05-31')[0]['unit_definition']=='iso4217:USD' and cons(a,'2025-05-31')[0]['scale']=='6',
 'original_obligation_7_9bn':'product purchase obligations of $7.9 billion' in ta,
 'correction_approximately_5bn':'approximately $5 billion' in tc and 'correct an error' in tc,
 'correction_document_8K':any(f.get('name')=='dei:DocumentType' and f['raw_display']=='8-K' for f in c['selected_facts']),
 'correction_not_amendment_flag':any(f.get('name')=='dei:AmendmentFlag' and f['raw_display']=='false' for f in c['selected_facts'])}
# Preserve narrow metadata/facts, not full decoded report or personal identifying boilerplate.
for d in (a,b,c):d.pop('contexts')
(ROOT/'SELECTED_FACTS.json').write_text(json.dumps([a,b,c],ensure_ascii=False,indent=2))
(ROOT/'REPLAY_RESULTS.json').write_text(json.dumps({'checks':checks,'pass':sum(checks.values()),'total':len(checks),'scope':'research fixtures only; product acceptance NOT_RUN'},indent=2))
print(json.dumps(checks,indent=2));assert all(checks.values())
