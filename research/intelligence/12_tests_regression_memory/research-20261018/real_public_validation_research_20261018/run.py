"""Independent, offline standard-library benchmark. No product imports or training."""
import csv,json,zipfile,hashlib,statistics as st,datetime as dt,xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from collections import Counter,defaultdict
P=Path(__file__).resolve().parent; O=P/'originals'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readcsv(name,delimiter=','):return list(csv.DictReader((O/name).open(newline='',encoding='utf-8-sig'),delimiter=delimiter))
def rate(rows):return sum(r['Revenue']=='TRUE' for r in rows)/len(rows)
def mae(a,b):return st.mean(abs(x-y) for x,y in zip(a,b))
def med(x):return st.median(x)
def wilson(k,n):
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/d;return [c-h,c+h]
results={'scope':'Research only; external real data, not LUMENIS execution or benefit; no model training','inputs':{p.name:sha(p) for p in O.glob('*') if p.suffix in ['.csv','.xlsx','.zip']}}
r=readcsv('online_shoppers_intention.csv'); n=len(r);k=sum(x['Revenue']=='TRUE' for x in r)
monthly={m:{'n':len(v),'positive':sum(x['Revenue']=='TRUE' for x in v),'rate':rate(v)} for m in sorted({x['Month'] for x in r}) if (v:=[x for x in r if x['Month']==m])}
train=[x for x in r if x['Month'] not in ['Oct','Nov','Dec']];test=[x for x in r if x['Month'] in ['Oct','Nov','Dec']];p=rate(train);q=rate(test)
results['shoppers']={'rows':n,'positive':k,'rate':k/n,'wilson95_conditional_on_sample':wilson(k,n),'all_negative_accuracy':1-k/n,'all_negative_recall':0,'all_negative_balanced_accuracy':.5,'empty_cells':sum(v=='' for x in r for v in x.values()),'monthly':monthly,'coarse_month_holdout':{'note':'Month labels only: not an exact chronological/backtest or as-of test','train_n':len(train),'test_n':len(test),'train_rate':p,'test_rate':q,'constant_train_rate_brier':st.mean((p-(x['Revenue']=='TRUE'))**2 for x in test),'all_negative_brier':q},'pagevalue_counterexample':{'positive_pagevalue_count':sum(float(x['PageValues'])>0 for x in r),'note':'Do not assume PageValues known before a target decision; require timestamp and metric provenance, no early prediction claim.'}}
r=readcsv('dataset_Facebook.csv',';');fields=list(r[0]);miss={f:sum(x[f]=='' for x in r) for f in fields};target='Lifetime Post Total Reach';train=[x for x in r if int(x['Post Month'])<=9];test=[x for x in r if int(x['Post Month'])>=10];base=med([int(x[target]) for x in train]); typ={t:med([int(x[target]) for x in train if x['Type']==t]) for t in {x['Type'] for x in train}};y=[int(x[target]) for x in test];a=[base]*len(test);b=[typ.get(x['Type'],base) for x in test]
groups={}
for t in sorted({x['Type'] for x in r}):
 v=[x for x in r if x['Type']==t];rat=[int(x['Total Interactions'])/int(x[target]) for x in v if int(x[target])>0];groups[t]={'n':len(v),'reach_mean':st.mean(int(x[target]) for x in v),'reach_median':med([int(x[target]) for x in v]),'interaction_mean':st.mean(int(x['Total Interactions']) for x in v),'mean_of_post_interaction_reach_ratios':st.mean(rat),'ratio_of_sums':sum(int(x['Total Interactions']) for x in v)/sum(int(x[target]) for x in v)}
results['facebook']={'rows':len(r),'missing_by_field':miss,'metadata_claim_no_missing':True,'observed_missing_cells':sum(miss.values()),'group_descriptions':groups,'coarse_month_holdout':{'train_n':len(train),'test_n':len(test),'global_past_median':base,'type_past_medians':typ,'global_median_MAE':mae(y,a),'type_median_MAE':mae(y,b),'relative_MAE_improvement':1-mae(y,b)/mae(y,a)},'interaction_component_complete_rows':sum(all(x[f]!='' for f in ['comment','like','share']) for x in r),'interaction_sum_mismatches_complete_rows':sum(int(x['Total Interactions'])!=sum(int(x[f]) for f in ['comment','like','share']) for x in r if all(x[f]!='' for f in ['comment','like','share']))}
# XML streaming XLSX, no third-party dependency. Original workbook cached numeric/date values.
z=zipfile.ZipFile(O/'Online Retail.xlsx');ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}';ss=[]
for _,e in ET.iterparse(z.open('xl/sharedStrings.xml'),events=('end',)):
 if e.tag==ns+'si':ss.append(''.join(e.itertext()));e.clear()
def rows():
 for _,e in ET.iterparse(z.open('xl/worksheets/sheet1.xml'),events=('end',)):
  if e.tag==ns+'row':
   d={}
   for c in e.findall(ns+'c'):
    v=c.find(ns+'v');val=v.text if v is not None else '';key=''.join(a for a in c.attrib['r'] if a.isalpha());d[key]=ss[int(val)] if c.attrib.get('t')=='s' and val else val
   yield d;e.clear()
it=rows();head=next(it);counts=Counter();total=Decimal(0);positive=Decimal(0);daily=defaultdict(Decimal);dups=set();duplicate_value=Decimal(0);month=defaultdict(Decimal);date_min=None;date_max=None
for d in it:
 counts['rows']+=1;key=tuple(d.get(c,'') for c in 'ABCDEFGH');q=Decimal(d.get('D','0') or '0');u=Decimal(d.get('F','0') or '0');value=q*u;total+=value
 if key in dups:counts['exact_duplicate_rows_beyond_first']+=1;duplicate_value+=value
 else:dups.add(key)
 counts['missing_customer']+=not bool(d.get('G'));counts['missing_description']+=not bool(d.get('C'));counts['negative_quantity']+=q<0;counts['zero_price']+=u==0;counts['negative_price']+=u<0;counts['cancellation_lines']+=d.get('A','').upper().startswith('C')
 if q>0 and u>0:positive+=value
 date=(dt.datetime(1899,12,30)+dt.timedelta(days=float(d['E']))).date();daily[date]+=value;month[date.strftime('%Y-%m')]+=value;date_min=min(date_min or date,date);date_max=max(date_max or date,date)
# Fixed last complete two calendar months Oct/Nov, preceding recorded calendar days only.
start=dt.date(2011,10,1);end=dt.date(2011,11,30);dates=[start+dt.timedelta(days=i) for i in range((end-start).days+1)];actual=[float(daily[d]) for d in dates];naive=[float(daily[d-dt.timedelta(days=7)]) for d in dates];smooth=[float(sum(daily[d-dt.timedelta(days=7*j)] for j in range(1,5))/4) for d in dates]
with (P/'retail_daily_forecast.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['date','actual_signed_GBP','weekly_naive_GBP','four_prior_same_weekdays_mean_GBP']);w.writerows(zip(map(str,dates),actual,naive,smooth))
with (P/'facebook_holdout_predictions.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['source_csv_row_1_based_header_included','month','type','actual_reach','global_past_median','type_past_median'])
 for i,row in enumerate(r,2):
  if int(row['Post Month'])>=10:w.writerow([i,row['Post Month'],row['Type'],row[target],base,typ.get(row['Type'],base)])
results['retail']={'headers':head,'counts':dict(counts),'date_min':str(date_min),'date_max':str(date_max),'currency':'GBP (sterling)','all_line_signed_value':str(total),'positive_quantity_and_positive_price_value':str(positive),'difference_positive_vs_signed':str(positive-total),'duplicate_line_signed_value':str(duplicate_value),'monthly_signed_value':{k:str(v) for k,v in sorted(month.items())},'forecast':{'window':[str(start),str(end)],'n':len(dates),'zero_days_mean':'No recorded lines, not evidence retailer was closed','weekly_naive_MAE_GBP':mae(actual,naive),'four_prior_same_weekdays_mean_MAE_GBP':mae(actual,smooth),'relative_MAE_improvement':1-mae(actual,smooth)/mae(actual,naive),'raw_signed_value_including_corrections':True}}
sensitivity=[]
for m in range(1,12):
 start_m=dt.date(2011,m,1);next_m=dt.date(2011,m+1,1);ds=[start_m+dt.timedelta(days=i) for i in range((next_m-start_m).days)]
 yy=[float(daily[d]) for d in ds];aa=[float(daily[d-dt.timedelta(days=7)]) for d in ds];bb=[float(sum(daily[d-dt.timedelta(days=7*j)] for j in range(1,5))/4) for d in ds]
 ea,eb=mae(yy,aa),mae(yy,bb);sensitivity.append({'month':str(start_m)[:7],'n':len(ds),'weekly_naive_MAE':ea,'four_week_mean_MAE':eb,'relative_MAE_improvement':1-eb/ea})
results['retail']['all_complete_month_sensitivity']=sensitivity
checks={'shoppers_row_count':results['shoppers']['rows']==12330,'shoppers_labels':k==1908,'facebook_row_count':results['facebook']['rows']==500,'retail_row_count':counts['rows']==541909,'retail_value_reconciliation':positive-total==Decimal(results['retail']['difference_positive_vs_signed']),'facebook_real_missing_counterexample':sum(miss.values())>0,'retail_real_missing_counterexample':counts['missing_customer']>0,'train_test_disjoint_facebook':max(int(x['Post Month']) for x in train)<min(int(x['Post Month']) for x in test)}
results['checks']=checks;results['all_checks_pass']=all(checks.values());(P/'RESULTS.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,sort_keys=True)+'\n');print(json.dumps(results,ensure_ascii=False,indent=2,sort_keys=True));assert all(checks.values())
