"""Isolated research examples. SYNTHETIC ONLY. Never imports or modifies LUMENIS."""
import hashlib, itertools, json, math, pathlib, platform
ROOT = pathlib.Path(__file__).parent
def wilson(k,n,z=1.959963984540054):
    if n == 0: return None
    p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()
results={'label':'SYNTHETIC_ONLY_NOT_CUSTOMER_RESULTS','python':platform.python_version()}
results['small_sample']={'A':{'negative':8,'classified':10,'ratio':.8,'wilson95':wilson(8,10)},'B':{'negative':60,'classified':100,'ratio':.6,'wilson95':wilson(60,100)},'decision':'Intervals overlap; raw rank does not establish A has higher population negativity.'}
results['unknown_bound']={'negative':20,'classified':50,'unknown':50,'known_only_rate':.4,'whole_observed_set_bounds':[.2,.7],'decision':'Unknown exclusion changes estimand; report unknown fraction, do not show 40% as all-content negativity.'}
results['exposure']={'previous':{'negative':20,'observed':100},'current':{'negative':40,'observed':400},'negative_count_growth':1.0,'observed_rate_change_pp':-10.0,'decision':'Count doubled while within-sample rate halved. Neither is population risk without stable coverage.'}
results['did_confounding']={'treated_pre':100,'treated_post':130,'control_pre':100,'control_post':110,'did':20,'true_treatment_effect_in_constructed_world':0,'unobserved_treated_only_road_reopening':20,'decision':'DiD arithmetic is correct yet causal claim false. Identical pretrends cannot rule out post-treatment confounding.'}
results['spend_proxy']={'impressions':100000,'cpm_bounds':[20,60],'sponsor_probability_bounds':[.3,.7],'derived_currency_bounds':[600,4200],'decision':'A seven-fold interval is a sensitivity scenario, not a calibrated confidence interval. Do not multiply post count by CPM.'}
items=[{'id':'A','cost':60,'audience':set(range(100))},{'id':'B','cost':40,'audience':set(range(80))},{'id':'C','cost':40,'audience':set(range(100,170))}]
options=[]
for n in range(1,4):
    for subset in itertools.combinations(items,n):
        cost=sum(i['cost'] for i in subset)
        if cost<=100: options.append({'ids':[i['id'] for i in subset],'cost':cost,'sum_audience':sum(len(i['audience']) for i in subset),'unique_audience':len(set().union(*(i['audience'] for i in subset)))})
results['creator_overlap']={'options':options,'additive_winner':max(options,key=lambda x:x['sum_audience'])['ids'],'deduplicated_winner':max(options,key=lambda x:x['unique_audience'])['ids'],'decision':'Overlap changes the optimal creator set. If overlap unavailable, do not claim unique reach.'}
series=[100+10*(i%7) for i in range(42)]
tests=list(range(21,42))
mae=lambda lag:sum(abs(series[i]-series[i-lag]) for i in tests)/len(tests)
results['forecast_baseline']={'train_points':21,'rolling_one_step_test_points':21,'last_value_mae':mae(1),'seasonal_naive_mae':mae(7),'decision':'Synthetic perfect weekly repetition favors seasonal naive; no evidence of real forecast gain or interval calibration.'}
results['identity']={'same_name':True,'brand_id':'brand-A','store_id':'store-A-101','filing_entity':'group-X','relationship':'brand operated by group; store belongs to brand','decision':'Relationship edges are not identity equivalence. Never merge these three entities or allocate group expense without disclosure.'}
frozen={'method':'synthetic-analysis@1','inputs':results,'claim_type':'illustrative'}
serialized=canonical(frozen); restored=json.loads(serialized)
assert digest(frozen)==digest(restored)
changed=json.loads(serialized); changed['inputs']['unknown_bound']['unknown']=40
assert digest(changed)!=digest(frozen)
assert wilson(0,0) is None
assert results['creator_overlap']['additive_winner']!=results['creator_overlap']['deduplicated_winner']
results['recovery_checks']={'roundtrip_same_hash':True,'upstream_change_new_hash':True,'zero_denominator_unknown':True,'scope':'Research JSON roundtrip only; not product SavedWork or runtime recovery.'}
(ROOT/'04_synthetic_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
