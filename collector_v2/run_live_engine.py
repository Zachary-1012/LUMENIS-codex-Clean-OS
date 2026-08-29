import argparse, json
from .xhs.live_engine import run_live, persist_live

def main():
    p=argparse.ArgumentParser(description='广州太古汇小红书实时数据引擎')
    p.add_argument('--keyword', action='append', required=True)
    p.add_argument('--max-scroll', type=int, default=5)
    p.add_argument('--max-details', type=int, default=20)
    p.add_argument('--max-comment-pages', type=int, default=5)
    p.add_argument('--cdp-url', default='')
    p.add_argument('--no-comments', action='store_true')
    a=p.parse_args()
    # 由现有业务层注入 subject_hit。默认拒绝，避免误把非广州太古汇内容写入数据库。
    try:
        from ai_analyzer import verify_taikoo_location
        def subject_hit(text):
            ok, _reason = verify_taikoo_location(text, '')
            return bool(ok)
    except Exception:
        def subject_hit(_): return False
    all_stats=[]
    for kw in a.keyword:
        data=run_live(kw,max_scroll=a.max_scroll,max_details=a.max_details,max_comment_pages=a.max_comment_pages,comments=not a.no_comments,cdp_url=a.cdp_url or None)
        stats=persist_live(data,subject_hit)
        all_stats.append({'keyword':kw,'collector':data.get('stats',{}),'persist':stats,'verification_required':data.get('verification_required',False)})
    print(json.dumps({'ok':all(not x['verification_required'] for x in all_stats),'results':all_stats},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
