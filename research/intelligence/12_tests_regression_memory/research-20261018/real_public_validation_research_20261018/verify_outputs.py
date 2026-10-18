import csv,json,hashlib,math
from pathlib import Path
p=Path(__file__).resolve().parent;r=json.loads((p/'RESULTS.json').read_text());checks={}
for name,sha in r['inputs'].items():checks['sha_'+name]=hashlib.sha256((p/'originals'/name).read_bytes()).hexdigest()==sha
for filename,actual,preds,obj,keys in [('retail_daily_forecast.csv','actual_signed_GBP',['weekly_naive_GBP','four_prior_same_weekdays_mean_GBP'],r['retail']['forecast'],['weekly_naive_MAE_GBP','four_prior_same_weekdays_mean_MAE_GBP']),('facebook_holdout_predictions.csv','actual_reach',['global_past_median','type_past_median'],r['facebook']['coarse_month_holdout'],['global_median_MAE','type_median_MAE'])]:
 rows=list(csv.DictReader((p/filename).open()))
 for pred,key in zip(preds,keys):checks[filename+':'+key]=math.isclose(sum(abs(float(x[actual])-float(x[pred])) for x in rows)/len(rows),obj[key],rel_tol=1e-12)
checks['negative_months_retained']=sum(x['relative_MAE_improvement']<0 for x in r['retail']['all_complete_month_sensitivity'])==3
checks['complete_months_retained']=len(r['retail']['all_complete_month_sensitivity'])==11
checks['no_training_claim']=r['scope'].endswith('no model training')
out={'verification':'Independent recomputation from exported per-row forecasts and hash readback, not independent external review','checks':checks,'all_pass':all(checks.values())};(p/'VALIDATION_RECEIPT.json').write_text(json.dumps(out,indent=2));print(out);assert all(checks.values())
