import argparse, json
from .xhs.live_engine import run_live, persist_live

def main():
    p=argparse.ArgumentParser(description='广州太古汇小红书实时数据引擎')
    p.add_argument('--keyword', action='append', required=True)
    p.add_argument('--max-scroll', type=int, default=5)
    p.add_argument('--max-details', type=int, default=20)
    p.add_argument('--max-comment-pages', type=int, default=5)
    p.add_argument('--cdp-url', default='')
    p.add_argument('--account', default='XHS_RETINAUT')
    p.add_argument('--no-comments', action='store_true')
    p.add_argument('--domain-id', required=True)
    p.add_argument('--product-id', required=True)
    focus=p.add_mutually_exclusive_group(required=True)
    focus.add_argument('--subject-id')
    focus.add_argument('--brand-focus-id')
    p.add_argument('--brand-key', required=True)
    a=p.parse_args()
    from .xhs.live_engine import resolve_live_scope
    try:
        domain_id, product_id, subject_id, brand_focus_id, _ = resolve_live_scope(
            domain_id=a.domain_id, product_id=a.product_id,
            subject_id=a.subject_id, brand_focus_id=a.brand_focus_id,
        )
    except ValueError as exc:
        print(json.dumps({'ok':False,'status':'scope_unavailable','error':str(exc)},ensure_ascii=False))
        return 2
    # P0-02: explicit profile drives filtering; an ambient Subject/environment
    # value may not silently choose the collection vocabulary.
    try:
        from subject_rules import subject_hit_for_brand
        def subject_hit(text):
            return subject_hit_for_brand(title=text, brand_key=a.brand_key)
    except Exception:
        def subject_hit(_): return False
    all_stats=[]
    for kw in a.keyword:
        data=run_live(kw,max_scroll=a.max_scroll,max_details=a.max_details,max_comment_pages=a.max_comment_pages,comments=not a.no_comments,cdp_url=a.cdp_url or None,account=a.account)
        stats=persist_live(data,subject_hit,domain_id=domain_id,product_id=product_id,
                           subject_id=subject_id,brand_focus_id=brand_focus_id)
        all_stats.append({'keyword':kw,'collector':data.get('stats',{}),'persist':stats,'verification_required':data.get('verification_required',False)})
    print(json.dumps({'ok':all(not x['verification_required'] for x in all_stats),'results':all_stats},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
