# -*- coding: utf-8 -*-


"""LUMENIS Shared Reporting KOS HTML Report Engine（动态 HTML 报告引擎）





核心交付格式：单文件 HTML，CSS/JS 内嵌，无外部依赖，浏览器直接打开。


PC/移动端自适应，支持动态筛选/Hover/Tooltip/排序/搜索/Tab切换。


数据来自真实数据库（kos_profiles/notes/note_comments/events），不造Demo数据。


"""


from __future__ import annotations


import sqlite3, os, json, io, math


from datetime import datetime


from pathlib import Path


from typing import Optional





PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = os.environ.get("ZBC_DB_PATH", str(PROJECT_ROOT / "data" / "monitor.db"))


REPORT_DIR = str(PROJECT_ROOT / "data" / "reports")


os.makedirs(REPORT_DIR, exist_ok=True)








def _get_conn() -> sqlite3.Connection:


    conn = sqlite3.connect(DB_PATH, timeout=10)


    conn.row_factory = sqlite3.Row


    return conn








def _collect_data(brand_name: str = "广州太古汇") -> dict:


    """从真实数据库收集报告数据。"""


    conn = _get_conn()


    cur = conn.cursor()


    # KOS 总览


    total = cur.execute("SELECT COUNT(*) FROM kos_profiles").fetchone()[0]


    tiers = {r["kos_tier"]: r["cnt"] for r in cur.execute("SELECT kos_tier, COUNT(*) as cnt FROM kos_profiles GROUP BY kos_tier")}


    lifecycle = {r["lifecycle_stage"]: r["cnt"] for r in cur.execute("SELECT lifecycle_stage, COUNT(*) as cnt FROM kos_profiles GROUP BY lifecycle_stage")}


    potential = cur.execute("SELECT COUNT(*) FROM kos_profiles WHERE is_potential=1").fetchone()[0]


    risk = cur.execute("SELECT COUNT(*) FROM kos_profiles WHERE is_risk=1").fetchone()[0]


    # TOP KOS


    top_kos = [dict(r) for r in cur.execute("SELECT author_nickname, kos_tier, kos_score, note_count, total_engagement, total_likes, total_comments, subject_type, lifecycle_stage, is_potential, is_risk FROM kos_profiles ORDER BY kos_score DESC LIMIT 30")]


    # 潜力 KOS


    potential_kos = [dict(r) for r in cur.execute("SELECT author_nickname, kos_score, note_count, avg_engagement, total_engagement FROM kos_profiles WHERE is_potential=1 ORDER BY avg_engagement DESC LIMIT 15")]


    # 风险 KOS


    risk_kos = [dict(r) for r in cur.execute("SELECT author_nickname, kos_score, note_count, negative_count, risk_count FROM kos_profiles WHERE is_risk=1 ORDER BY risk_count DESC LIMIT 15")]


    # TOP 内容


    top_notes = [dict(r) for r in cur.execute("SELECT title, author_nickname, likes, comments, collects, shares, publish_datetime, sentiment, url FROM notes WHERE title IS NOT NULL AND title != '' ORDER BY likes DESC LIMIT 20")]


    # 评论统计


    comment_total = cur.execute("SELECT COUNT(*) FROM note_comments").fetchone()[0]


    comment_by_sentiment = {}  # note_comments 表无 sentiment 列，评论分类由前端规则引擎处理


    # 事件


    events = [dict(r) for r in cur.execute("SELECT title, risk_level, mention_count, first_seen, status FROM events ORDER BY mention_count DESC LIMIT 10")]


    # 投流候选（从 notes 计算）


    ad_candidates = []


    for r in cur.execute("SELECT note_id, title, author_nickname, likes, comments, collects, shares, content_quality_score, sentiment, risk_level FROM notes WHERE sentiment != 'negative' AND (risk_level IS NULL OR risk_level NOT IN ('high','medium')) ORDER BY likes DESC LIMIT 15"):


        d = dict(r)


        eng = (d.get("likes") or 0) + (d.get("comments") or 0)*2 + (d.get("collects") or 0)*1.5 + (d.get("shares") or 0)*2


        nat = min(math.log10(eng+1)*12, 40) if eng > 0 else 0


        iq = min(((d.get("comments") or 0)+(d.get("collects") or 0))/max(d.get("likes") or 1, 1)*30, 30)


        qs = min((d.get("content_quality_score") or 0)*20, 20)


        score = max(0, min(100, round(nat+iq+qs, 1)))


        rec = "推荐投流" if score >= 70 else "建议观察" if score >= 40 else "不建议投流"


        ad_candidates.append({"title": (d.get("title") or "")[:50], "author": d.get("author_nickname"), "engagement": eng, "score": score, "recommendation": rec})


    ad_candidates.sort(key=lambda x: x["score"], reverse=True)


    conn.close()


    return {


        "brand_name": brand_name,


        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),


        "overview": {"total": total, "by_tier": tiers, "by_lifecycle": lifecycle, "potential": potential, "risk": risk},


        "top_kos": top_kos, "potential_kos": potential_kos, "risk_kos": risk_kos,


        "top_notes": top_notes, "comment_total": comment_total, "comment_by_sentiment": comment_by_sentiment,


        "events": events, "ad_candidates": ad_candidates,


    }








def _render_html(data: dict) -> str:


    """渲染动态 HTML 报告（单文件，CSS/JS 内嵌，无外部依赖）。"""


    d = json.dumps(data, ensure_ascii=False, default=str)


    tier_colors = {"S": "#e74c3c", "A": "#f39c12", "B": "#3498db", "C": "#95a5a6"}


    return f"""<!DOCTYPE html>


<html lang="zh-CN">


<head>


<meta charset="UTF-8">


<meta name="viewport" content="width=device-width, initial-scale=1.0">


<title>{data['brand_name']} KOS Intelligence Report</title>


<style>


*{{margin:0;padding:0;box-sizing:border-box}}


body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:#f7f7f5;color:#171717;line-height:1.6}}


.container{{max-width:1200px;margin:0 auto;padding:20px}}


.header{{background:linear-gradient(135deg,#171717 0%,#2d2d2d 100%);color:#fff;padding:40px 30px;border-radius:16px;margin-bottom:24px}}


.header h1{{font-size:28px;font-weight:700;margin-bottom:8px}}


.header .meta{{font-size:13px;opacity:.7}}


.header .brand-tag{{display:inline-block;background:rgba(255,255,255,.15);padding:4px 12px;border-radius:20px;font-size:12px;margin-top:12px}}


.tabs{{display:flex;gap:4px;margin-bottom:20px;flex-wrap:wrap;background:#fff;padding:6px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}


.tab{{padding:10px 18px;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;transition:all .2s;border:none;background:transparent;color:#666}}


.tab:hover{{background:#f0f0f0}}


.tab.active{{background:#171717;color:#fff}}


.panel{{display:none;animation:fadeIn .3s}}


.panel.active{{display:block}}


@keyframes fadeIn{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}


.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}}


.card{{background:#fff;padding:20px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}


.card .label{{font-size:12px;color:#888;margin-bottom:6px}}


.card .value{{font-size:28px;font-weight:700}}


.card .sub{{font-size:11px;color:#aaa;margin-top:4px}}


.section{{background:#fff;padding:24px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:20px}}


.section h2{{font-size:18px;font-weight:600;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #eee}}


.donut-container{{display:flex;align-items:center;gap:30px;flex-wrap:wrap}}


.donut{{width:160px;height:160px;border-radius:50%;position:relative;flex-shrink:0}}


.donut-center{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}}


.donut-center .num{{font-size:24px;font-weight:700}}


.donut-center .lbl{{font-size:11px;color:#888}}


.legend{{display:flex;flex-direction:column;gap:8px}}


.legend-item{{display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer}}


.legend-dot{{width:12px;height:12px;border-radius:3px;flex-shrink:0}}


.rank-list{{display:flex;flex-direction:column;gap:8px}}


.rank-item{{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:8px;transition:background .15s;cursor:pointer}}


.rank-item:hover{{background:#f8f8f8}}


.rank-num{{width:24px;height:24px;border-radius:50%;background:#f0f0f0;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0}}


.rank-num.top{{background:#171717;color:#fff}}


.rank-name{{flex:1;font-size:14px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}


.rank-bar{{width:120px;height:8px;background:#f0f0f0;border-radius:4px;overflow:hidden;flex-shrink:0}}


.rank-bar-fill{{height:100%;border-radius:4px;transition:width .5s}}


.rank-score{{font-size:13px;font-weight:600;width:40px;text-align:right;flex-shrink:0}}


.rank-tier{{font-size:10px;padding:2px 6px;border-radius:4px;color:#fff;font-weight:600;flex-shrink:0}}


table{{width:100%;border-collapse:collapse;font-size:13px}}


th{{text-align:left;padding:10px 8px;border-bottom:2px solid #eee;font-weight:600;color:#666;cursor:pointer;user-select:none;white-space:nowrap}}


th:hover{{color:#171717}}


td{{padding:10px 8px;border-bottom:1px solid #f5f5f5}}


tr:hover{{background:#fafafa}}


.search-box{{width:100%;padding:10px 14px;border:1px solid #ddd;border-radius:8px;font-size:14px;margin-bottom:16px;outline:none;transition:border .2s}}


.search-box:focus{{border-color:#171717}}


.filter-row{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}


.filter-btn{{padding:6px 14px;border:1px solid #ddd;border-radius:20px;background:#fff;font-size:12px;cursor:pointer;transition:all .15s}}


.filter-btn:hover{{border-color:#171717}}


.filter-btn.active{{background:#171717;color:#fff;border-color:#171717}}


.tooltip{{position:fixed;background:#171717;color:#fff;padding:8px 12px;border-radius:6px;font-size:12px;pointer-events:none;z-index:9999;display:none;max-width:300px}}


.bar-chart{{display:flex;flex-direction:column;gap:6px}}


.bar-row{{display:flex;align-items:center;gap:10px}}


.bar-label{{width:80px;font-size:12px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}


.bar-track{{flex:1;height:20px;background:#f5f5f5;border-radius:4px;overflow:hidden;position:relative}}


.bar-fill{{height:100%;border-radius:4px;transition:width .6s;display:flex;align-items:center;padding-left:6px;font-size:10px;color:#fff;font-weight:600}}


.insight-box{{background:#f8f8f8;border-left:3px solid #171717;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:12px;font-size:13px}}


.insight-box .tag{{display:inline-block;background:#171717;color:#fff;padding:2px 8px;border-radius:4px;font-size:10px;margin-right:8px}}


.footer{{text-align:center;padding:20px;color:#aaa;font-size:11px}}


@media(max-width:768px){{


.container{{padding:12px}}


.header{{padding:24px 18px}}


.header h1{{font-size:20px}}


.cards{{grid-template-columns:repeat(2,1fr)}}


.rank-bar{{width:60px}}


.donut-container{{justify-content:center}}


table{{font-size:11px}}


th,td{{padding:6px 4px}}


}}


</style>


</head>


<body>


<div class="container">


<div class="header">


<h1>{data['brand_name']} · KOS Intelligence</h1>


<div class="meta">传播主体智能报告 · 生成于 {data['generated_at']}</div>


<div class="brand-tag">LUMENIS KOS Reporting · 数据来源：真实采集数据库</div>


</div>


<div class="tabs" id="tabs">


<button class="tab active" data-panel="overview">KOS总览</button>


<button class="tab" data-panel="top">TOP KOS</button>


<button class="tab" data-panel="potential">潜力/风险</button>


<button class="tab" data-panel="content">TOP内容</button>


<button class="tab" data-panel="comments">评论洞察</button>


<button class="tab" data-panel="ad">投流建议</button>


<button class="tab" data-panel="events">事件关系</button>


<button class="tab" data-panel="insights">AI洞察</button>


</div>


<div id="panels"></div>


<div class="footer">序境 · KOS Intelligence Report · 数据可追溯至原始笔记与 Evidence</div>


</div>


<div class="tooltip" id="tooltip"></div>


<script>


const DATA = {d};


const TIER_COLORS = {json.dumps(tier_colors)};


const $ = s => document.querySelector(s);


const $$ = s => document.querySelectorAll(s);





// Tab 切换


$$('.tab').forEach(tab => {{


  tab.addEventListener('click', () => {{


    $$('.tab').forEach(t => t.classList.remove('active'));


    $$('.panel').forEach(p => p.classList.remove('active'));


    tab.classList.add('active');


    document.getElementById('panel-' + tab.dataset.panel).classList.add('active');


  }});


}});





// Tooltip


const tooltip = $('#tooltip');


document.addEventListener('mouseover', e => {{


  const t = e.target.closest('[data-tip]');


  if (t) {{ tooltip.textContent = t.dataset.tip; tooltip.style.display = 'block'; }}


}});


document.addEventListener('mousemove', e => {{


  if (tooltip.style.display === 'block') {{


    tooltip.style.left = (e.clientX + 12) + 'px';


    tooltip.style.top = (e.clientY + 12) + 'px';


  }}


}});


document.addEventListener('mouseout', e => {{


  if (e.target.closest('[data-tip]')) tooltip.style.display = 'none';


}});





// 渲染面板


function render() {{


  const o = DATA.overview;


  const panels = $('#panels');


  let html = '';





  // 总览


  html += `<div class="panel active" id="panel-overview">


    <div class="cards">


      <div class="card"><div class="label">KOS 总数</div><div class="value">${{o.total}}</div><div class="sub">传播主体</div></div>


      <div class="card"><div class="label">S级核心</div><div class="value" style="color:#e74c3c">${{o.by_tier['S']||0}}</div><div class="sub">优先合作</div></div>


      <div class="card"><div class="label">A级重点</div><div class="value" style="color:#f39c12">${{o.by_tier['A']||0}}</div><div class="sub">重点培养</div></div>


      <div class="card"><div class="label">潜力KOS</div><div class="value" style="color:#3498db">${{o.potential}}</div><div class="sub">高互动低篇数</div></div>


      <div class="card"><div class="label">风险KOS</div><div class="value" style="color:#e67e22">${{o.risk}}</div><div class="sub">负面/风险占比高</div></div>


    </div>


    <div class="section"><h2>KOS 分层分布</h2>


      <div class="donut-container">


        <div class="donut" id="donut-tier"></div>


        <div class="legend" id="legend-tier"></div>


      </div>


    </div>


    <div class="section"><h2>生命周期分布</h2>


      <div class="bar-chart" id="bar-lifecycle"></div>


    </div>


  </div>`;





  // 环形图


  const tiers = ['S','A','B','C'];


  const total = o.total || 1;


  let grad = 'conic-gradient(';


  let acc = 0;


  tiers.forEach((t,i) => {{


    const v = o.by_tier[t] || 0;


    const pct = v/total*100;


    grad += `${{TIER_COLORS[t]}} ${{acc}}% ${{acc+pct}}%`;


    if (i < tiers.length-1) grad += ', ';


    acc += pct;


  }});


  grad += ')';


  setTimeout(() => {{


    const donut = document.getElementById('donut-tier');


    if (donut) {{ donut.style.background = grad; donut.innerHTML = `<div class="donut-center"><div class="num">${{o.total}}</div><div class="lbl">KOS 总数</div></div>`; }}


    const legend = document.getElementById('legend-tier');


    if (legend) {{


      legend.innerHTML = tiers.map(t => `<div class="legend-item"><div class="legend-dot" style="background:${{TIER_COLORS[t]}}"></div>${{t}}级 · ${{o.by_tier[t]||0}}人 (${{((o.by_tier[t]||0)/total*100).toFixed(1)}}%)</div>`).join('');


    }}


  }}, 50);





  // 生命周期柱状


  setTimeout(() => {{


    const bl = document.getElementById('bar-lifecycle');


    if (bl) {{


      const lc = o.by_lifecycle || {{}};


      const max = Math.max(...Object.values(lc), 1);


      bl.innerHTML = Object.entries(lc).sort((a,b)=>b[1]-a[1]).map(([k,v]) =>


        `<div class="bar-row"><div class="bar-label">${{k}}</div><div class="bar-track"><div class="bar-fill" style="width:${{v/max*100}}%;background:#171717">${{v}}</div></div></div>`


      ).join('');


    }}


  }}, 50);





  // TOP KOS


  html += `<div class="panel" id="panel-top">


    <div class="section"><h2>TOP KOS 排名（按综合评分）</h2>


      <input class="search-box" id="search-top" placeholder="搜索 KOS 名称...">


      <div class="filter-row" id="filter-top">


        <button class="filter-btn active" data-tier="">全部</button>


        <button class="filter-btn" data-tier="S">S级</button>


        <button class="filter-btn" data-tier="A">A级</button>


        <button class="filter-btn" data-tier="B">B级</button>


        <button class="filter-btn" data-tier="C">C级</button>


      </div>


      <div class="rank-list" id="rank-top"></div>


    </div>


  </div>`;





  // 潜力/风险


  html += `<div class="panel" id="panel-potential">


    <div class="section"><h2>潜力 KOS（低篇数高互动，值得培养）</h2>


      <div class="rank-list" id="rank-potential"></div>


    </div>


    <div class="section"><h2>风险 KOS（负面/风险占比高，需关注）</h2>


      <div class="rank-list" id="rank-risk"></div>


    </div>


  </div>`;





  // TOP内容


  html += `<div class="panel" id="panel-content">


    <div class="section"><h2>TOP 内容（按点赞排序）</h2>


      <div style="overflow-x:auto"><table id="table-notes">


        <thead><tr><th data-sort="title">标题</th><th data-sort="author_nickname">作者</th><th data-sort="likes">点赞</th><th data-sort="comments">评论</th><th data-sort="collects">收藏</th><th data-sort="sentiment">情感</th></tr></thead>


        <tbody></tbody>


      </table></div>


    </div>


  </div>`;





  // 评论洞察


  html += `<div class="panel" id="panel-comments">


    <div class="cards">


      <div class="card"><div class="label">评论总数</div><div class="value">${{DATA.comment_total}}</div></div>


    </div>


    <div class="section"><h2>评论情感分布</h2>


      <div class="bar-chart" id="bar-comments"></div>


    </div>


    <div class="section"><h2>评论分类洞察（规则引擎）</h2>


      <div class="insight-box"><span class="tag">NO_REPLY</span>高风险投诉、法律/安全问题、明显争议——禁止 AI 自动回复，转人工处理</div>


      <div class="insight-box"><span class="tag">购买意向</span>含"怎么买/多少钱/链接/购买"关键词——建议优先回复，引导转化</div>


      <div class="insight-box"><span class="tag">活动咨询</span>含"活动/时间/地点/报名"关键词——建议回复活动信息</div>


    </div>


  </div>`;





  // 投流建议


  html += `<div class="panel" id="panel-ad">


    <div class="section"><h2>投流候选评分（自然表现 × 互动质量 × 内容质量）</h2>


      <div style="overflow-x:auto"><table id="table-ad">


        <thead><tr><th>标题</th><th>作者</th><th>互动量</th><th>投流评分</th><th>建议</th></tr></thead>


        <tbody></tbody>


      </table></div>


      <div class="insight-box" style="margin-top:16px"><span class="tag">注意</span>无真实投流成本和转化数据，不生成虚假 ROI。评分仅基于自然表现，投流决策需结合实际投放数据。</div>


    </div>


  </div>`;





  // 事件关系


  html += `<div class="panel" id="panel-events">


    <div class="section"><h2>关联事件（按提及量排序）</h2>


      <div style="overflow-x:auto"><table id="table-events">


        <thead><tr><th>事件</th><th>风险等级</th><th>提及量</th><th>首次发现</th><th>状态</th></tr></thead>


        <tbody></tbody>


      </table></div>


    </div>


  </div>`;





  // AI洞察


  const sCount = o.by_tier['S']||0, aCount = o.by_tier['A']||0;


  html += `<div class="panel" id="panel-insights">


    <div class="section"><h2>AI 运营洞察</h2>


      <div class="insight-box"><span class="tag">核心</span>当前 S 级 ${{sCount}} 人 + A 级 ${{aCount}} 人，建议优先建立深度合作关系，形成品牌核心传播矩阵。</div>


      <div class="insight-box"><span class="tag">潜力</span>发现 ${{o.potential}} 位潜力 KOS（低篇数高互动），建议通过活动邀请激活，培养为长期合作对象。</div>


      <div class="insight-box"><span class="tag">风险</span>${{o.risk}} 位风险 KOS 需持续监测，高风险内容不建议自动回复，转人工评估。</div>


      <div class="insight-box"><span class="tag">投流</span>投流候选基于自然表现评分，建议优先对"推荐投流"内容进行小预算测试，验证转化后再放大。</div>


      <div class="insight-box"><span class="tag">评论</span>评论回复需分级：购买意向/活动咨询优先回复，高风险投诉 NO_REPLY 转人工，普通互动可批量处理。</div>


    </div>


    <div class="section"><h2>Evidence 可追溯</h2>


      <div class="insight-box">本报告所有数据来自真实采集数据库（notes/kos_profiles/note_comments/events），每个 KOS 可追溯至原始笔记，每个结论可关联 Evidence 记录。无 Demo 数据，无 AI 虚构。</div>


    </div>


  </div>`;





  panels.innerHTML = html;





  // 渲染 TOP KOS


  function renderTop(filter='', search='') {{


    let list = DATA.top_kos.filter(k => (!filter || k.kos_tier === filter) && (!search || (k.author_nickname||'').toLowerCase().includes(search.toLowerCase())));


    const max = Math.max(...list.map(k=>k.kos_score), 1);


    document.getElementById('rank-top').innerHTML = list.slice(0,30).map((k,i) =>


      `<div class="rank-item" data-tip="${{k.author_nickname}} | 笔记${{k.note_count}}篇 | 互动${{k.total_engagement}} | 赞${{k.total_likes}} 评${{k.total_comments}} | ${{k.subject_type||'unknown'}} | ${{k.lifecycle_stage}}">


        <div class="rank-num ${{i<3?'top':''}}">${{i+1}}</div>


        <div class="rank-name">${{k.author_nickname||'unknown'}}</div>


        <div class="rank-tier" style="background:${{TIER_COLORS[k.kos_tier]||'#999'}}">${{k.kos_tier}}</div>


        <div class="rank-bar"><div class="rank-bar-fill" style="width:${{k.kos_score/max*100}}%;background:${{TIER_COLORS[k.kos_tier]||'#999'}}"></div></div>


        <div class="rank-score">${{k.kos_score.toFixed(1)}}</div>


      </div>`


    ).join('');


  }}


  renderTop();


  document.getElementById('search-top').addEventListener('input', e => renderTop(document.querySelector('#filter-top .filter-btn.active').dataset.tier, e.target.value));


  document.querySelectorAll('#filter-top .filter-btn').forEach(b => b.addEventListener('click', () => {{


    document.querySelectorAll('#filter-top .filter-btn').forEach(x=>x.classList.remove('active'));


    b.classList.add('active');


    renderTop(b.dataset.tier, document.getElementById('search-top').value);


  }}));





  // 潜力 KOS


  const pm = Math.max(...DATA.potential_kos.map(k=>k.avg_engagement||0),1);


  document.getElementById('rank-potential').innerHTML = DATA.potential_kos.slice(0,15).map((k,i) =>


    `<div class="rank-item"><div class="rank-num">${{i+1}}</div><div class="rank-name">${{k.author_nickname||'unknown'}}</div><div class="rank-bar"><div class="rank-bar-fill" style="width:${{(k.avg_engagement||0)/pm*100}}%;background:#3498db"></div></div><div class="rank-score">${{(k.avg_engagement||0).toFixed(0)}}</div></div>`


  ).join('');





  // 风险 KOS


  const rm = Math.max(...DATA.risk_kos.map(k=>(k.risk_count||0)+(k.negative_count||0)),1);


  document.getElementById('rank-risk').innerHTML = DATA.risk_kos.slice(0,15).map((k,i) =>


    `<div class="rank-item"><div class="rank-num">${{i+1}}</div><div class="rank-name">${{k.author_nickname||'unknown'}}</div><div class="rank-bar"><div class="rank-bar-fill" style="width:${{((k.risk_count||0)+(k.negative_count||0))/rm*100}}%;background:#e67e22"></div></div><div class="rank-score">${{(k.risk_count||0)+(k.negative_count||0)}}</div></div>`


  ).join('');





  // TOP内容表格


  const ntb = document.querySelector('#table-notes tbody');


  ntb.innerHTML = DATA.top_notes.map(n => `<tr><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{(n.title||'').replace(/"/g,'&quot;')}}">${{n.title||''}}</td><td>${{n.author_nickname||''}}</td><td>${{n.likes||0}}</td><td>${{n.comments||0}}</td><td>${{n.collects||0}}</td><td>${{n.sentiment||''}}</td></tr>`).join('');





  // 评论情感柱状


  setTimeout(() => {{


    const bc = document.getElementById('bar-comments');


    if (bc && DATA.comment_by_sentiment) {{


      const cs = DATA.comment_by_sentiment;


      const mx = Math.max(...Object.values(cs),1);


      bc.innerHTML = Object.entries(cs).sort((a,b)=>b[1]-a[1]).map(([k,v]) =>


        `<div class="bar-row"><div class="bar-label">${{k}}</div><div class="bar-track"><div class="bar-fill" style="width:${{v/mx*100}}%;background:#171717">${{v}}</div></div></div>`


      ).join('');


    }}


  }},50);





  // 投流表格


  document.querySelector('#table-ad tbody').innerHTML = DATA.ad_candidates.map(a =>


    `<tr><td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{a.title}}</td><td>${{a.author||''}}</td><td>${{a.engagement}}</td><td><strong>${{a.score}}</strong></td><td><span style="color:${{a.recommendation==='推荐投流'?'#27ae60':a.recommendation==='建议观察'?'#f39c12':'#999'}}">${{a.recommendation}}</span></td></tr>`


  ).join('');





  // 事件表格


  document.querySelector('#table-events tbody').innerHTML = (DATA.events||[]).map(e =>


    `<tr><td>${{e.title||''}}</td><td>${{e.risk_level||''}}</td><td>${{e.mention_count||0}}</td><td>${{(e.first_seen||'').slice(0,10)}}</td><td>${{e.status||''}}</td></tr>`


  ).join('');


}}


render();


</script>


</body>


</html>"""








def _render_channel_roi(ch: dict) -> str:
    """多渠道 ROI 对比卡片（KM-06）：各渠道 CPL/CPC/预算/vs 基准。静态 HTML，无 JS 依赖。"""
    channels = ch.get("channels", []) if isinstance(ch, dict) else []
    if not channels:
        return '<section class="card" style="padding:20px;margin-bottom:20px;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)"><h3 style="margin:0 0 8px">多渠道 ROI 对比</h3><p style="color:#999;font-size:13px;margin:0">暂无数据（请在 KOS 后台回填 Boosting/WeCom/进线数据）</p></section>'
    rows = ""
    for c in channels:
        cpl = c.get("cpl")
        ref = c.get("reference_cpl")
        if cpl is not None and ref:
            pct = c.get("vs_reference_pct")
            color = "#27ae60" if pct is not None and pct < 0 else "#f39c12"
            ref_txt = '<span style="color:%s">%s%% vs 基准 %s</span>' % (color, pct, ref)
        else:
            ref_txt = '<span style="color:#999">待回填</span>'
        rows += ('<tr><td style="padding:10px 12px;border-bottom:1px solid #f0f0f0"><strong>%s</strong></td>'
                 '<td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">%s</td>'
                 '<td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">%s</td>'
                 '<td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">%s</td>'
                 '<td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">%s</td>'
                 '<td style="padding:10px 12px;border-bottom:1px solid #f0f0f0">%s</td></tr>') % (
            c.get("label", c.get("name", "")),
            c.get("budget", 0), c.get("inquiry", 0), c.get("wecom", 0),
            cpl if cpl is not None else "--", ref_txt)
    return ('<section class="card" style="padding:20px;margin-bottom:20px;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)">'
            '<h3 style="margin:0 0 12px">多渠道 ROI 对比（KM-06）</h3>'
            '<table style="width:100%;border-collapse:collapse;font-size:13px">'
            '<thead><tr style="color:#999;text-align:left"><th style="padding:8px 12px;border-bottom:2px solid #f0f0f0">渠道</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #f0f0f0">预算(¥)</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #f0f0f0">进线</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #f0f0f0">WeCom</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #f0f0f0">CPL</th>'
            '<th style="padding:8px 12px;border-bottom:2px solid #f0f0f0">vs 基准</th></tr></thead>'
            '<tbody>' + rows + '</tbody></table></section>')


def generate_report(brand_name: str = "广州太古汇", output_path: Optional[str] = None) -> dict:


    """生成 KOS 动态 HTML 报告。"""


    data = _collect_data(brand_name)


    html = _render_html(data)

    import kos_metrics

    data["channel_roi"] = kos_metrics.channel_roi()

    html = html.replace("</body>", _render_channel_roi(data["channel_roi"]) + "</body>", 1)


    if not output_path:


        safe_brand = brand_name.replace("/", "_").replace(" ", "_")


        output_path = os.path.join(REPORT_DIR, f"KOS_Report_{safe_brand}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")


    with io.open(output_path, "w", encoding="utf-8") as f:


        f.write(html)


    return {"ok": True, "path": output_path, "brand": brand_name,


            "kos_total": data["overview"]["total"], "file_size": len(html.encode("utf-8")),


            "generated_at": data["generated_at"]}








__all__ = ["generate_report", "REPORT_DIR"]
