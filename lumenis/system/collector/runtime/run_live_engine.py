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
    a=p.parse_args()
    # P0-02 收敛：统一委托 subject_rules 权威主体口径（排除词一票否决+正向词命中），
    # 不再用 AI verify 替代，避免口径分叉；导入失败时默认拒绝，避免误写入（对账 GAP-P0-02）。
    try:
        from subject_rules import subject_hit_text
        def subject_hit(text):
            return subject_hit_text(text)
    except Exception:
        def subject_hit(_): return False
    all_stats=[]
    for kw in a.keyword:
        data=run_live(kw,max_scroll=a.max_scroll,max_details=a.max_details,max_comment_pages=a.max_comment_pages,comments=not a.no_comments,cdp_url=a.cdp_url or None,account=a.account)
        stats=persist_live(data,subject_hit)
        all_stats.append({'keyword':kw,'collector':data.get('stats',{}),'persist':stats,'verification_required':data.get('verification_required',False)})
    print(json.dumps({'ok':all(not x['verification_required'] for x in all_stats),'results':all_stats},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
