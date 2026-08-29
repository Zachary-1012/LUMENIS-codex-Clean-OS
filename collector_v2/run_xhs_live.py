import argparse,json,os
from collector_v2.xhs.collector import XHSCollector
from collector_v2.pipeline.normalize import normalize_note
from collector_v2.pipeline.deduplicate import deduplicate
def main():
    p=argparse.ArgumentParser();p.add_argument("--keyword",action="append",required=True);p.add_argument("--max-scroll",type=int,default=5);p.add_argument("--out",default="data/collector_v2_latest.json");a=p.parse_args()
    c=XHSCollector(config={"search_script":"xhs_search_v2.js"},use_browser=True); alln=[]; results=[]
    for kw in a.keyword:
        ns=c.search(kw,a.max_scroll);alln.extend(normalize_note(n) for n in ns);results.append({"keyword":kw,"count":len(ns)})
    alln=deduplicate(alln);os.makedirs(os.path.dirname(a.out) or ".",exist_ok=True)
    json.dump({"ok":True,"total":len(alln),"results":results,"notes":alln},open(a.out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(json.dumps({"ok":True,"total":len(alln),"results":results},ensure_ascii=False))
if __name__=="__main__": main()
