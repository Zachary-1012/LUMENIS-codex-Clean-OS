#!/usr/bin/env python3
"""兼容旧命令的本地 Pipeline。真实数据优先；不再依赖不存在的评论脚本或静态事件库。"""
import os, sys
from datetime import datetime
import database as db
import collector
import ai_analyzer

def run(keywords=None,max_scroll=4):
    keywords=keywords or collector.MONITOR_KEYWORDS
    notes,results=collector.collect_all(keywords,max_scroll)
    verified=inserted=0
    for n in notes:
        ok,reason=ai_analyzer.verify_taikoo_location(n.get('title',''),n.get('content',''))
        if not ok: continue
        n['is_taikoo_verified']=1;n['verify_reason']=reason
        _,new=db.insert_note(n); inserted+=int(new); verified+=1
        db.update_note_analysis(n['note_id'],ai_analyzer.analyze_note(n,provider='rule'))
    for r in results: db.log_collection(r['keyword'],r.get('count',0),'error' if r.get('error') else 'success',r.get('error',''))
    print(f'[Pipeline] 原始 {len(notes)}，验证通过 {verified}，新增 {inserted}')
    return verified

def main():
    print('='*60); print('广州太古汇本地舆情 Pipeline'); print(datetime.now().strftime('%Y-%m-%d %H:%M:%S')); print('='*60)
    run()
    print('提示：旧版“全网事件反哺/评论采集”脚本已不再作为默认链路，避免把静态事件配置当作实时事实。')

if __name__=='__main__': main()
