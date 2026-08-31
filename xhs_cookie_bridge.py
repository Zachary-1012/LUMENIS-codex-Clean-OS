"""广州太古汇 v5.3.2：本地 Cookie 小红书数据桥。

职责：
1. 使用本机 Cookie/持久化 Playwright profile 搜索小红书；
2. 只把搜索结果标准化后交给现有 database.insert_note；
3. 继续调用现有 ai_analyzer / reprocess，保持 v5.3.1 业务链；
4. source_id 使用 note_id，xsec_token 原样存入 notes，保证真实详情链接可更新；
5. Cookie 只从本机读取，不进入源码、日志、JSON 数据快照。
"""
from __future__ import annotations
import json, os, subprocess, threading, time
from datetime import datetime
import database as db
import ai_analyzer
import network_adaptive
import cache_manager

ROOT=os.path.dirname(os.path.abspath(__file__))
SEARCH_JS=os.path.join(ROOT,'xhs_cookie_search.js')
COOKIE_FILE=os.path.join(ROOT,'data','private','xhs_cookie_header.txt')
STATS_FILE=os.path.join(ROOT,'data','collector_stats.json')  # 采集计数持久化文件
DEFAULT_KEYWORDS=['广州太古汇','太古汇 15周年','太古汇 周年庆','太古汇 活动','太古汇 展览','太古汇 快闪',
                  '太古汇 新店','太古汇 开业','太古汇 美食','太古汇 探店','太古汇 打卡','太古汇 方所','太古汇 品牌',
                  '太古汇 投诉','太古汇 避雷','太古汇 差评','太古汇 吐槽','太古汇 维权','太古汇 服务','太古汇 停车']

# ========== 账号安全保护机制 ==========
ALLOWED_USER_ID = "61d58d560000000010005a8a"  # 白名单：只有这个账号可以运行爬虫
MAX_DAILY_RUNS = 12  # 每日最大运行次数（保护账号）
MAX_MANUAL_RUNS = 3  # 每日手动触发（一键实时更新）最大次数
MAX_AUTO_RUNS = 9  # 每日自动定时采集最大次数
COOLDOWN_MINUTES = 60  # 连续运行后的冷却时间（分钟）- 调整为1小时
NEW_ACCOUNT_GUARD_RUNS = 3  # 新账号前N次强制极轻量模式
# 采集时长配置（秒）
AUTO_COLLECT_DURATION = 1800  # 自动采集每次30分钟
MANUAL_COLLECT_DURATION = 1200  # 手动采集每次20分钟
NODE_PROCESS_TIMEOUT = 1800  # Node进程超时时间（秒）- 调整为30分钟，给足时间完成
# 自动采集时间分配（9次/天，合理覆盖高峰时段）
AUTO_COLLECT_HOURS = [8, 10, 12, 14, 16, 18, 20, 22, 23]
_daily_runs = []  # 今日运行时间戳列表
_daily_manual_runs = 0  # 今日手动触发次数
_daily_auto_runs = 0  # 今日自动采集次数
_last_run_time = None  # 上次运行时间
_stats_loaded = False  # 是否已加载持久化统计

_lock=threading.Lock()
_tasks={}

def _load_stats_from_db():
    """从数据库统计今天的采集次数（兜底恢复）"""
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        with db.get_db() as conn:
            # 统计今天有多少个不同的采集批次（按collected_at的分钟级分组）
            cur = conn.execute("SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H:%M', collected_at)) FROM notes WHERE date(collected_at)=date('now','localtime')")
            db_batch_count = cur.fetchone()[0] or 0
            # 获取最晚采集时间
            cur2 = conn.execute("SELECT MAX(collected_at) FROM notes WHERE date(collected_at)=date('now','localtime')")
            last_collect = cur2.fetchone()[0]
            if last_collect:
                try:
                    _last_run_time = datetime.strptime(last_collect, '%Y-%m-%d %H:%M:%S').timestamp()
                except Exception:
                    pass
        # 如果数据库有今天的采集记录，且内存计数为0，则从数据库恢复
        if db_batch_count > 0 and len(_daily_runs) == 0:
            # 估算：数据库批次数量作为今日运行次数（上限MAX_DAILY_RUNS）
            estimated_runs = min(db_batch_count, MAX_DAILY_RUNS)
            now = time.time()
            _daily_runs = [now - (estimated_runs - i) * 3600 for i in range(estimated_runs)]
            # 假设大部分是自动采集，手动占少数
            _daily_auto_runs = max(0, estimated_runs - 1)
            _daily_manual_runs = min(1, estimated_runs)
            print(f'[Stats] 从数据库恢复今日采集次数: {estimated_runs}次 (自动{_daily_auto_runs}/手动{_daily_manual_runs})')
    except Exception as e:
        print(f'[Stats] 从数据库恢复计数失败: {e}')

def _load_stats():
    """从持久化文件加载统计数据（优先），失败则从数据库恢复"""
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time, _stats_loaded
    if _stats_loaded:
        return
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('date') == today:
                _daily_runs = data.get('daily_runs', [])
                _daily_manual_runs = data.get('manual_runs', 0)
                _daily_auto_runs = data.get('auto_runs', 0)
                _last_run_time = data.get('last_run_time')
                print(f'[Stats] 从文件恢复今日计数: 总{len(_daily_runs)}/手动{_daily_manual_runs}/自动{_daily_auto_runs}')
                _stats_loaded = True
                return
        # 文件不存在或不是今天的数据，从数据库恢复
        _load_stats_from_db()
        _save_stats()
        _stats_loaded = True
    except Exception as e:
        print(f'[Stats] 加载统计失败: {e}')
        _load_stats_from_db()
        _stats_loaded = True

def _save_stats():
    """保存统计数据到持久化文件"""
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'daily_runs': _daily_runs[-50:],  # 只保留最近50条
            'manual_runs': _daily_manual_runs,
            'auto_runs': _daily_auto_runs,
            'last_run_time': _last_run_time,
            'updated_at': datetime.now().isoformat()
        }
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[Stats] 保存统计失败: {e}')

# 模块加载时自动恢复统计
_load_stats()

def _get_current_user_id():
    """从本地Cookie文件中提取当前登录账号ID"""
    try:
        if os.path.exists(COOKIE_FILE):
            content = open(COOKIE_FILE, encoding='utf-8').read()
            # 提取 x-user-id-pro 的值
            for part in content.split(';'):
                part = part.strip()
                if part.startswith('x-user-id-pro='):
                    return part.split('=', 1)[1].strip()
        if os.getenv('XHS_COOKIE_HEADER'):
            for part in os.getenv('XHS_COOKIE_HEADER', '').split(';'):
                part = part.strip()
                if part.startswith('x-user-id-pro='):
                    return part.split('=', 1)[1].strip()
    except Exception:
        pass
    return None

def verify_account():
    """验证当前登录账号是否在白名单中"""
    current_id = _get_current_user_id()
    if not current_id:
        return False, "无法读取账号ID，请检查Cookie配置"
    if current_id != ALLOWED_USER_ID:
        return False, f"当前账号({current_id[:8]}...)不在白名单中，禁止爬虫。仅允许轻量检索。"
    return True, f"账号验证通过({current_id[:8]}...)"

def check_rate_limit(run_type='manual'):
    """检查频率限制，返回(是否允许, 提示信息)
    run_type: 'manual'（一键实时更新）或 'auto'（定时自动采集）
    """
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    now = time.time()
    today = datetime.now().strftime('%Y-%m-%d')
    # 清理非今日的记录
    _daily_runs = [t for t in _daily_runs if datetime.fromtimestamp(t).strftime('%Y-%m-%d') == today]
    # 检查每日总次数
    if len(_daily_runs) >= MAX_DAILY_RUNS:
        return False, f"今日已运行{len(_daily_runs)}次，达到每日上限({MAX_DAILY_RUNS}次)，请明天再试"
    # 检查手动次数
    if run_type == 'manual' and _daily_manual_runs >= MAX_MANUAL_RUNS:
        return False, f"今日手动触发已达{MAX_MANUAL_RUNS}次上限，剩余{MAX_AUTO_RUNS}次为定时自动采集"
    # 检查自动次数
    if run_type == 'auto' and _daily_auto_runs >= MAX_AUTO_RUNS:
        return False, f"今日自动采集已达{MAX_AUTO_RUNS}次上限"
    # 检查冷却时间
    if _last_run_time and (now - _last_run_time) < COOLDOWN_MINUTES * 60:
        wait_min = int((COOLDOWN_MINUTES * 60 - (now - _last_run_time)) / 60) + 1
        return False, f"距离上次运行不足{COOLDOWN_MINUTES}分钟，请等待{wait_min}分钟后再试（保护账号）"
    return True, "频率检查通过"

def record_run(run_type='manual'):
    """记录一次运行
    run_type: 'manual'（一键实时更新）或 'auto'（定时自动采集）
    """
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    now = time.time()
    _daily_runs.append(now)
    _last_run_time = now
    if run_type == 'manual':
        _daily_manual_runs += 1
    else:
        _daily_auto_runs += 1
    # 持久化保存
    _save_stats()

def get_account_status():
    """获取账号健康状态"""
    current_id = _get_current_user_id()
    today = datetime.now().strftime('%Y-%m-%d')
    today_runs = len([t for t in _daily_runs if datetime.fromtimestamp(t).strftime('%Y-%m-%d') == today])
    in_whitelist = (current_id == ALLOWED_USER_ID) if current_id else False
    cooldown_remaining = 0
    if _last_run_time:
        elapsed = time.time() - _last_run_time
        if elapsed < COOLDOWN_MINUTES * 60:
            cooldown_remaining = int((COOLDOWN_MINUTES * 60 - elapsed) / 60) + 1
    return {
        'current_user_id': current_id[:12] + '...' if current_id else None,
        'in_whitelist': in_whitelist,
        'allowed_user_id': ALLOWED_USER_ID[:12] + '...',
        'today_runs': today_runs,
        'today_manual_runs': _daily_manual_runs,
        'today_auto_runs': _daily_auto_runs,
        'max_daily_runs': MAX_DAILY_RUNS,
        'max_manual_runs': MAX_MANUAL_RUNS,
        'max_auto_runs': MAX_AUTO_RUNS,
        'auto_collect_hours': AUTO_COLLECT_HOURS,
        'cooldown_minutes': COOLDOWN_MINUTES,
        'cooldown_remaining_minutes': cooldown_remaining,
        'new_account_guard_runs': NEW_ACCOUNT_GUARD_RUNS,
        'cookie_configured': cookie_configured(),
        'status': 'ready' if (in_whitelist and cookie_configured() and cooldown_remaining == 0) else 'restricted'
    }

def cookie_configured():
    return bool(os.getenv('XHS_COOKIE_HEADER') or os.getenv('XHS_COOKIES_JSON') or (os.path.exists(COOKIE_FILE) and open(COOKIE_FILE,encoding='utf-8').read().strip()))

def _run_search(keyword,max_scroll=6):
    # 网络自适应：使用当前自适应设置
    adaptive = network_adaptive.get_adaptive_settings()
    effective_scroll = min(max_scroll, adaptive.get('current_scroll_limit', 6))
    delay = adaptive.get('current_delay_seconds', 2)
    
    out=os.path.join(ROOT,'data','private',f'xhs_{int(time.time()*1000)}.json')
    env=os.environ.copy()
    env['XHS_COOKIE_FILE']=COOKIE_FILE
    cmd=['node',SEARCH_JS,'--keyword',keyword,'--output',out,'--max-scroll',str(effective_scroll)]
    try:
        # 使用Popen+轮询，避免Flask线程中subprocess阻塞
        stdout_file = out + '.stdout'
        stderr_file = out + '.stderr'
        with open(stdout_file, 'w', encoding='utf-8') as fout, open(stderr_file, 'w', encoding='utf-8') as ferr:
            p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=fout, stderr=ferr)
        # 轮询等待完成，最多30分钟（给足时间完成采集，不要因为担心时间长而简短过去）
        waited = 0
        while p.poll() is None and waited < NODE_PROCESS_TIMEOUT:
            time.sleep(5)
            waited += 5
            # 每30秒输出一次进度（通过任务状态反馈）
            if waited % 30 == 0:
                print(f"[xhs-bridge] 关键词 '{keyword}' 采集中... 已等待 {waited}秒", flush=True)
        if p.poll() is None:
            p.kill()
            return {'keyword':keyword,'total':0,'notes':[],'state':'NETWORK_ERROR','error':f'Node进程超时（{NODE_PROCESS_TIMEOUT}秒）','risk_detected':False}
        if p.returncode != 0:
            error_msg = ''
            parsed = None
            # Node 崩溃时也可能已写出结构化结果（main catch 会落 NETWORK_ERROR）
            try:
                if os.path.exists(out):
                    with open(out, encoding='utf-8') as f: parsed = json.load(f)
            except Exception:
                parsed = None
            try:
                with open(stderr_file, encoding='utf-8') as f:
                    error_msg = f.read()[-1000:]
            except Exception:
                pass
            # 风控检测
            risk = network_adaptive.detect_risk(error_msg=error_msg)
            if risk['is_risk']:
                network_adaptive.report_collection_result(False, risk_info=risk)
            if parsed:
                parsed.setdefault('error', error_msg); return parsed
            return {'keyword':keyword,'total':0,'notes':[],'state':'NETWORK_ERROR','error':error_msg,'risk_detected':risk['is_risk']}
        with open(out,encoding='utf-8') as f:
            result = json.load(f)
        # 六态兜底：若旧版结果无 state，则按 blocked_reason/数量推导
        if not result.get('state'):
            _br = result.get('blocked_reason','')
            if _br == 'LOGIN_REQUIRED': result['state']='AUTH_FAILED'
            elif _br: result['state']='BLOCKED'
            elif result.get('api_calls',0)>0 and result.get('total',0)==0: result['state']='EMPTY'
            elif result.get('total',0)>0: result['state']='SUCCESS'
            else: result['state']='NETWORK_ERROR'
        # js 已基于 URL 重定向 / error_code / 验证码精确判定 state；
        # bridge 不再用“结果正文词频”覆盖成功态——搜“投诉/避雷”时正文本就含风险词，宽泛匹配会误杀成功采集
        if result.get('state') in (None, '', 'NETWORK_ERROR'):
            risk = network_adaptive.detect_risk(response_text=json.dumps(result, ensure_ascii=False))
            if risk['is_risk']:
                result['state']='BLOCKED'; result['blocked_reason']=risk.get('type','RISK')
        if result.get('state') in ('BLOCKED','AUTH_FAILED','CAPTCHA'):
            network_adaptive.report_collection_result(False, risk_info={'type':result.get('blocked_reason') or result['state'],'is_risk':True})
        return result
    finally:
        try: os.remove(out)
        except OSError: pass
        try: os.remove(out + '.stdout')
        except OSError: pass
        try: os.remove(out + '.stderr')
        except OSError: pass
        # 自适应延迟
        time.sleep(delay)

# ========== 六态状态机：采集日志落库 + 自动熔断 ==========
CIRCUIT_FILE=os.path.join(ROOT,'data','private','xhs_circuit.json')
# 用户级“手动暂停采集”开关（区别于风控熔断：由用户主动设置，手动/自动一律不发起平台请求，直到用户主动恢复）
USER_PAUSE_FILE=os.path.join(ROOT,'data','private','xhs_user_paused.json')

def is_user_paused():
    """返回用户暂停信息 dict；未暂停返回 None。"""
    try:
        if not os.path.exists(USER_PAUSE_FILE): return None
        d=json.load(open(USER_PAUSE_FILE,encoding='utf-8'))
        return d if d.get('paused') else None
    except Exception:
        return None

def set_user_paused(reason='用户手动暂停'):
    try:
        os.makedirs(os.path.dirname(USER_PAUSE_FILE),exist_ok=True)
        with open(USER_PAUSE_FILE,'w',encoding='utf-8') as f:
            json.dump({'paused':True,'reason':reason,'at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')},f,ensure_ascii=False)
        return True
    except Exception:
        return False

def resume_user_paused():
    try:
        if os.path.exists(USER_PAUSE_FILE): os.remove(USER_PAUSE_FILE)
        return True
    except OSError:
        return False
STATE_LABEL={'SUCCESS':'正常','EMPTY':'正常但无数据','BLOCKED':'IP风控拦截','AUTH_FAILED':'登录态失效',
             'CAPTCHA':'需要人机验证','NETWORK_ERROR':'网络异常','PARTIAL_BLOCKED':'部分关键词被拦截'}

def _write_collection_log(keyword,notes_count,state,error_msg=''):
    """每个关键词一条采集日志，state 为六态，绝不把 BLOCKED 写成成功 0 条"""
    try:
        with db.get_db() as conn:
            conn.execute("INSERT INTO collection_logs(keyword,notes_count,status,error_msg,started_at,finished_at) VALUES(?,?,?,?,?,?)",
                         (keyword,notes_count if state in ('SUCCESS','EMPTY') else None,state,error_msg,
                          datetime.now().strftime('%Y-%m-%d %H:%M:%S'),datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
    except Exception as e:
        print('[xhs-bridge] collection_logs写入失败:',e,flush=True)

def _trip_circuit(state,detail,cool_minutes=60):
    """熔断：BLOCKED/AUTH/CAPTCHA 时写入暂停时间，自动调度在此之前跳过（手动/测试模式可强制）"""
    try:
        import json as _json
        until=time.time()+cool_minutes*60
        cur={'state':state,'detail':detail,'tripped_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             'resume_at':datetime.fromtimestamp(until).strftime('%Y-%m-%d %H:%M:%S'),'resume_ts':until}
        with open(CIRCUIT_FILE,'w',encoding='utf-8') as f: _json.dump(cur,f,ensure_ascii=False)
    except Exception:
        pass

def get_circuit_state():
    """供调度器/报告/前端读取当前熔断状态"""
    try:
        if not os.path.exists(CIRCUIT_FILE): return {'open':False,'state':'SUCCESS'}
        d=json.load(open(CIRCUIT_FILE,encoding='utf-8'))
        if d.get('resume_ts',0) <= time.time(): return {'open':False,'state':'SUCCESS'}
        d['open']=True; return d
    except Exception:
        return {'open':False,'state':'SUCCESS'}

def clear_circuit():
    try:
        if os.path.exists(CIRCUIT_FILE): os.remove(CIRCUIT_FILE)
    except OSError: pass

def is_test_mode():
    """测试模式：环境变量 XHS_TEST_MODE=1 时跳过冷却/新账号保护/熔断拦截，端到端测试期使用"""
    return os.environ.get('XHS_TEST_MODE','').strip() in ('1','true','TRUE','yes')

def sync(keywords=None,max_scroll=6):
    if not cookie_configured():
        raise RuntimeError('未配置本机 XHS Cookie。请在 data/private/xhs_cookie_header.txt 配置，或使用已登录的 Playwright profile。')
    keywords=list(dict.fromkeys(keywords or DEFAULT_KEYWORDS))[:32]
    raw={}; results=[]; blocked={}; state_counts={}
    for kw in keywords:
        r=_run_search(kw,max_scroll)
        st=r.get('state') or ('SUCCESS' if r.get('total',0)>0 else 'NETWORK_ERROR')
        state_counts[st]=state_counts.get(st,0)+1
        results.append({'keyword':kw,'fetched':r.get('total',0),'state':st,'error':r.get('error',''),'blocked':r.get('blocked_reason','')})
        _write_collection_log(kw, r.get('total',0), st, (r.get('blocked_reason') or r.get('error_code') or r.get('error') or '')[:200])
        br=r.get('blocked_reason')
        if br: blocked[br]=blocked.get(br,0)+1
        # 仅在真正成功/空结果态收集笔记；被拦截态 notes 必为空，双保险防止把故障当数据
        if st in ('SUCCESS','EMPTY'):
            for n in r.get('notes',[]):
                nid=str(n.get('note_id') or '').strip()
                if nid:
                    n['source_keyword']=kw; raw.setdefault(nid,n)
    # 若多数关键词被风控/登录墙拦截，上报网络自适应并在结果中明确标注（不再伪装成“0 条新笔记”）
    blocked_summary = ''
    if blocked:
        top_block=max(blocked,key=blocked.get)
        label={'IP_RISK_OR_CAPTCHA':'IP存在风险/出现验证码，已被小红书安全拦截','LOGIN_REQUIRED':'登录态失效，需要重新登录','EMPTY_NO_API':'未收到搜索接口响应（可能被风控）'}.get(top_block,top_block)
        blocked_summary=f'{label}（{sum(blocked.values())}/{len(keywords)} 个关键词被拦截）'
        try:
            network_adaptive.report_collection_result(False, risk_info={'type':top_block,'is_risk':True})
        except Exception:
            pass
        results.append({'stage':'blocked','reason':top_block,'detail':blocked_summary})
    inserted=updated=rejected=0
    for n in raw.values():
        ok,reason=ai_analyzer.verify_taikoo_location(n.get('title',''),n.get('content',''))
        n['is_taikoo_verified']=1 if ok else 0; n['verify_reason']=reason; n['source_platform']='xiaohongshu'
        if not ok: rejected+=1; continue
        _,new=db.insert_note(n); inserted+=int(new); updated+=int(not new)
    analyzed=0
    events=[]
    try:
        import reprocess
        # AI分析改为异步后台执行（每条约23秒，避免阻塞主流程）
        # 每次只分析最新的20条，避免处理积压
        with db.get_db() as conn:
            rows=conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND (ai_analyzed_at='' OR ai_analyzed_at IS NULL) ORDER BY id DESC LIMIT 20").fetchall()
        analyzed = len(rows)  # 记录待分析数量，实际分析在后台完成
        
        def _async_analyze_and_events():
            try:
                for row in rows:
                    reprocess.analyze_note_row(row, translate=False)
                # AI分析完成后再执行事件聚合
                reprocess.build_cross_platform_events()
            except Exception as e:
                results.append({'stage':'async_analysis_events','error':str(e)})
        threading.Thread(target=_async_analyze_and_events, daemon=True, name='ai-analysis-events').start()
        results.append({'stage':'ai_analysis','status':'async_started','message':f'AI分析({analyzed}条)+事件聚合已在后台异步执行，不阻塞主流程'})
    except Exception as e:
        results.append({'stage':'post_process','error':str(e)})
    
    # 网络自适应：报告采集结果
    total_new = inserted + updated
    if total_new > 0:
        network_adaptive.report_collection_result(True, notes_count=total_new)
        # 成功采集后创建缓存快照
        try:
            cache_result = cache_manager.create_snapshot()
            results.append({'stage':'cache_snapshot','success':cache_result.get('success',False)})
        except Exception as e:
            results.append({'stage':'cache_snapshot','error':str(e)})
    else:
        network_adaptive.report_collection_result(False, notes_count=0)
    
    # 获取当前网络状态
    net_status = network_adaptive.get_network_status()

    # ===== 任务级六态汇总（关键：被拦截不等于“0 条正常”）=====
    n=len(keywords)
    n_ok=state_counts.get('SUCCESS',0); n_empty=state_counts.get('EMPTY',0)
    n_block=state_counts.get('BLOCKED',0)+state_counts.get('CAPTCHA',0)+state_counts.get('AUTH_FAILED',0)
    n_neterr=state_counts.get('NETWORK_ERROR',0)
    if n_ok==n: task_state='SUCCESS'
    elif (n_ok+n_empty)==n and n_ok==0: task_state='EMPTY'
    elif n_ok>0 and (n_block+n_neterr)>0: task_state='PARTIAL_BLOCKED'
    elif n_block==n: task_state='BLOCKED'
    elif (n_block+n_neterr)==n: task_state='NETWORK_ERROR'
    elif n_ok==0 and n_empty>0: task_state='EMPTY'
    else: task_state='PARTIAL_BLOCKED'
    # 半数以上关键词被拦截/失败：熔断自动调度（测试模式不熔断，便于端到端验证）
    if not is_test_mode() and (n_block+n_neterr) >= max(1, n//2):
        top=blocked_summary or task_state
        _trip_circuit(task_state, top)
    elif task_state=='SUCCESS':
        clear_circuit()

    return {
        'ok':True,
        'task_state':task_state,
        'state_counts':state_counts,
        'keywords':keywords,
        'raw_unique':len(raw),
        'verified':len(raw)-rejected,
        'rejected':rejected,
        'inserted':inserted,
        'updated':updated,
        'analyzed':analyzed,
        'events':len(events),
        'results':results,
        'network_status': net_status,
        'cache_status': cache_manager.get_cache_status(),
        'blocked': blocked_summary,
        'finished_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def _shadow_record_result(task_state, items_found, blocked='', run_type='auto'):
    """v5.8.6 动态调度影子闭环：把本次真实采集状态回写统一规划器。
    仅演进影子状态/写审计，不门控、不影响采集，任何异常 fail-open；AI 不参与此决策。"""
    try:
        from platform_adapters.scheduling import get_planner
        _map = {'EMPTY': 'NO_NEW_DATA', 'PARTIAL_BLOCKED': 'RISK_WARNING', 'SUCCESS': 'SUCCESS'}
        raw = _map.get(task_state, task_state)
        planner = get_planner()
        planner.record_result('xhs', raw, now=datetime.now(),
                              items_found=int(items_found or 0),
                              error_code=str(blocked or '')[:120],
                              trigger_source=f'xhs-{run_type}')
    except Exception as e:
        print('[xhs-bridge] shadow record skipped:', e, flush=True)


def create_task(keywords=None,max_scroll=6,run_type='manual'):
    """创建采集任务
    run_type: 'manual'（一键实时更新）或 'auto'（定时自动采集）
    """
    # 用户主动暂停期间，手动/自动一律不发起平台请求（测试模式旁路），保护账号，直到用户显式恢复
    _paused = is_user_paused()
    if _paused and not is_test_mode():
        raise RuntimeError(f"小红书采集已手动暂停（{_paused.get('reason','')}，{_paused.get('at','')}）。请恢复后再采集。")
    # 账号白名单验证
    account_ok, account_msg = verify_account()
    if not account_ok:
        raise RuntimeError(f'账号验证失败：{account_msg}')
    # 频率限制检查（区分手动/自动）；测试模式旁路，便于端到端连续验证
    if not is_test_mode():
        rate_ok, rate_msg = check_rate_limit(run_type)
        if not rate_ok:
            raise RuntimeError(f'频率限制：{rate_msg}')
    # 自动任务在熔断期直接跳过（手动/测试模式可强制，用于恢复健康检查）
    circ=get_circuit_state()
    if run_type=='auto' and circ.get('open') and not is_test_mode():
        raise RuntimeError(f'采集熔断中（{circ.get("state")}），自动任务暂停至 {circ.get("resume_at")}')
    # 新账号保护：前N次强制极轻量模式（测试模式旁路）
    today = datetime.now().strftime('%Y-%m-%d')
    today_runs = len([t for t in _daily_runs if datetime.fromtimestamp(t).strftime('%Y-%m-%d') == today])
    if today_runs < NEW_ACCOUNT_GUARD_RUNS and not is_test_mode():
        max_scroll = min(max_scroll, 2)
        guard_msg = f'（新账号保护：第{today_runs+1}/{NEW_ACCOUNT_GUARD_RUNS}次，强制极轻量模式max_scroll={max_scroll}）'
    else:
        guard_msg = '（测试模式：已旁路冷却/新账号保护）' if is_test_mode() else ''
    type_label = '手动触发' if run_type == 'manual' else '自动采集'
    if not _lock.acquire(blocking=False): raise RuntimeError('已有小红书 Cookie 同步任务运行中')
    task_id=f"xhs-{datetime.now():%Y%m%d%H%M%S}-{int(time.time()*1000)%1000:03d}"
    _tasks[task_id]={'task_id':task_id,'status':'running','progress':5,'run_type':run_type,'message':f'[{type_label}]正在使用本机登录态检索小红书…{guard_msg}','created_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    def worker():
        try:
            record_run(run_type)  # 记录运行（区分手动/自动）
            _tasks[task_id].update(progress=20,message=f'[{type_label}]搜索广州太古汇关键词…{guard_msg}')
            result=sync(keywords,max_scroll)
            ts=result.get('task_state','SUCCESS')
            if ts in ('BLOCKED','PARTIAL_BLOCKED','NETWORK_ERROR','AUTH_FAILED','CAPTCHA'):
                done_msg=f'[{type_label}]采集未完成（{STATE_LABEL.get(ts,ts)}）：{result.get("blocked") or "多数关键词未取得响应"}。本次不计为0条，自动任务已按策略熔断/降频'
            elif ts=='EMPTY':
                done_msg=f'[{type_label}]采集成功但本批无新笔记（接口正常）'
            else:
                done_msg=f'[{type_label}]小红书同步完成（新增{result.get("inserted",0)}、更新{result.get("updated",0)}）'
            if result.get('blocked') and ts=='SUCCESS':
                done_msg=f'[{type_label}]未采集到新笔记：{result["blocked"]}（已自动降频，建议切换网络或稍后重试）'
            _tasks[task_id].update(status='done',progress=100,message=done_msg,result=result,finished_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            # v5.8.6 真实结果回写动态调度影子（不门控、不影响采集）
            try:
                _shadow_record_result(ts, result.get('inserted',0)+result.get('updated',0),
                                      result.get('blocked') or '', run_type)
            except Exception as _be:
                print('[xhs-bridge] shadow feedback non-blocking:', _be, flush=True)
        except Exception as e:
            _tasks[task_id].update(status='error',progress=100,message=str(e),error=str(e))
        finally: _lock.release()
    threading.Thread(target=worker,daemon=True,name='xhs-cookie-sync').start()
    return task_id

def get_task(task_id): return _tasks.get(task_id)
