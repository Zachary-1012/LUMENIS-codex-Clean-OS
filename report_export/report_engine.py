# -*- coding: utf-8 -*-
"""v5.6.4 report export engine: DOCX/CSV/XLSX from existing monitor.db.
- 严格按笔记发布日期过滤
- 周报/月报/年报负面笔记必须是二次确认的
- 包含事件分析
"""
import csv, sqlite3
from datetime import datetime, timedelta
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
except ImportError:
    Document=None
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    Workbook=None

BASE=Path(__file__).resolve().parent.parent
DB=BASE/"data"/"monitor.db"
OUT=BASE/"data"/"exports"
NOTE_COLS=["note_id","title","author_nickname","publish_date","url","sentiment","risk_level",
           "risk_score","summary","category","likes","comments","collects","shares","source_platform",
           "negative_confirmed"]
EVENT_COLS=["event_id","title","event_type","risk_level","risk_score","first_seen","last_seen","note_count","summary","status"]

def _conn():
    if not DB.exists(): raise FileNotFoundError(f"未找到数据库: {DB}")
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def _cols(c,t): return {r[1] for r in c.execute(f"PRAGMA table_info({t})")}

def _pick(cols,names):
    return next((x for x in names if x in cols),None)

def _notes(start=None,end=None,kind="daily",only_confirmed_negative=False):
    """获取指定周期内发布的笔记
    kind: daily/weekly/monthly/yearly
    only_confirmed_negative: 只包含二次确认的负面笔记（用于周报/月报/年报）
    """
    c=_conn()
    try:
        cols=_cols(c,"notes")
        if "note_id" not in cols: raise RuntimeError("notes 表缺少 note_id")
        use=[x for x in NOTE_COLS if x in cols]
        # 优先使用publish_date，确保按发布日期过滤
        d=_pick(cols,["publish_date","publish_datetime","published_at"])
        if not d:
            d="publish_date"
        sql="SELECT "+",".join(use)+" FROM notes WHERE 1=1"
        w=[];v=[]
        # 严格按发布日期过滤
        if start: w.append(f"date({d})>=date(?)");v.append(start)
        if end: w.append(f"date({d})<=date(?)");v.append(end)
        # 对于周报/月报/年报，负面笔记必须是二次确认的
        if only_confirmed_negative and "negative_confirmed" in cols:
            w.append("(sentiment!='negative' OR negative_confirmed=1)")
        if w: sql+=" AND "+" AND ".join(w)
        sql+=f" ORDER BY {d} DESC"
        return [dict(x) for x in c.execute(sql,v)]
    finally:c.close()

def _events(start=None,end=None):
    c=_conn()
    try:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone(): return []
        cols=_cols(c,"events"); use=[x for x in EVENT_COLS if x in cols]
        d=_pick(cols,["last_seen","updated_at","created_at","first_seen"])
        if "event_id" not in cols:return []
        sql="SELECT "+",".join(use)+" FROM events WHERE 1=1";w=[];v=[]
        if d and start:w.append(f"date({d})>=date(?)");v.append(start)
        if d and end:w.append(f"date({d})<=date(?)");v.append(end)
        if w:sql+=" AND "+" AND ".join(w)
        if d:sql+=f" ORDER BY {d} DESC"
        return [dict(x) for x in c.execute(sql,v)]
    finally:c.close()

def payload(kind="daily",start=None,end=None):
    today=datetime.now().date()
    if not end:end=str(today)
    if not start:
        days={"daily":0,"weekly":6,"monthly":29,"yearly":364}.get(kind,0)
        start=str(today-timedelta(days=days))
    # 周报/月报/年报只包含二次确认的负面笔记
    only_confirmed = kind in ("weekly","monthly","yearly")
    n=_notes(start,end,kind,only_confirmed_negative=only_confirmed)
    e=_events(start,end)
    def cnt(k,v):return sum(str(x.get(k,"")).lower()==v for x in n)  # 通用兜底保留
    from canonical_metrics import sentiment_count as _scf, risk_count as _rcf  # [Canonical]
    _sc, _rc = _scf(n), _rcf(n)
    # 事件分析（Topic 聚类主题词增强：c-TF-IDF 只读内存，不改 DB）
    event_analysis = []
    evs = e[:5]
    try:
        from scripts.topic_cluster import enrich_events_with_labels
        evs = enrich_events_with_labels(evs, top_k=4)
    except Exception:
        pass
    for ev in evs:  # 最多分析5个事件
        event_analysis.append({
            "title": ev.get("title","未知事件"),
            "type": ev.get("event_type","-"),
            "risk": ev.get("risk_level","-"),
            "notes": ev.get("note_count",0),
            "summary": ev.get("summary","-"),
            "first_seen": ev.get("first_seen","-"),
            "last_seen": ev.get("last_seen","-"),
            "topic": ev.get("topic_label",""),
        })
    # 高风险笔记
    high_risk_notes = [x for x in n if str(x.get("risk_level","")).lower()=="high"]
    # 负面笔记（已二次确认）
    confirmed_negative = [x for x in n if str(x.get("sentiment","")).lower()=="negative" and x.get("negative_confirmed")==1]
    # 圈层研究资产：case_study 按圈层分布 + 创意引擎 16 圈层符号表（报告消费新圈层）
    case_circles = {}
    circle_symbols = {}
    try:
        from scripts.idea_generator import CIRCLE_SYMBOLS
        circle_symbols = {k: v.get("symbols", []) for k, v in CIRCLE_SYMBOLS.items()}
        _cc = _conn(); _cu = _cc.cursor()
        _cu.execute("SELECT tags FROM swire_events WHERE project_key='case_study'")
        for (_t,) in _cu.fetchall():
            for _tag in (str(_t or "").split(",")):
                _tag = _tag.strip()
                if _tag and _tag in circle_symbols:
                    case_circles[_tag] = case_circles.get(_tag, 0) + 1
    except Exception:
        case_circles, circle_symbols = {}, {}
    return {
        "report_type":kind,"period_start":start,"period_end":end,
        "notes":n,"events":e,
        "total_notes":len(n),
        "positive_count":_sc["positive"],
        "neutral_count":_sc["neutral"],
        "negative_count":_sc["negative"],
        "confirmed_negative_count":len(confirmed_negative),
        "high_risk_count":_rc["high"],
        "medium_risk_count":_rc["medium"],
        "low_risk_count":_rc["low"],
        "event_analysis":event_analysis,
        "high_risk_notes":high_risk_notes[:10],
        "case_circles": case_circles,
        "circle_symbols": circle_symbols,
        "only_confirmed_negative":only_confirmed
    }

def _v(x):return "" if x is None else x

def export_csv(p,out):
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=NOTE_COLS,extrasaction="ignore");w.writeheader()
        for n in p["notes"]:w.writerow({k:_v(n.get(k)) for k in NOTE_COLS})

def export_xlsx(p,out):
    if Workbook is None:raise RuntimeError("请安装 openpyxl")
    out.parent.mkdir(parents=True,exist_ok=True)
    wb=Workbook()
    
    # Sheet1: 报告概览
    ws=wb.active;ws.title="报告概览"
    # 标题样式
    title_font=Font(name="微软雅黑",size=16,bold=True,color="FFFFFF")
    header_font=Font(name="微软雅黑",size=11,bold=True,color="FFFFFF")
    normal_font=Font(name="微软雅黑",size=10)
    header_fill=PatternFill(start_color="2563EB",end_color="2563EB",fill_type="solid")
    title_fill=PatternFill(start_color="1E40AF",end_color="1E40AF",fill_type="solid")
    thin_border=Border(
        left=Side(style='thin'),right=Side(style='thin'),
        top=Side(style='thin'),bottom=Side(style='thin')
    )
    
    ws.merge_cells('A1:D1')
    ws['A1']="广州太古汇舆情监测系统 - 舆情报告"
    ws['A1'].font=title_font
    ws['A1'].fill=title_fill
    ws['A1'].alignment=Alignment(horizontal='center',vertical='center')
    ws.row_dimensions[1].height=30
    
    type_names={"daily":"日报","weekly":"周报","monthly":"月报","yearly":"年报"}
    overview_data=[
        ["报告类型",type_names.get(p["report_type"],p["report_type"])],
        ["数据周期",f'{p["period_start"]} 至 {p["period_end"]}'],
        ["生成时间",datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["",""],
        ["核心指标","数值"],
        ["圈层资产",f'{len(p.get("case_circles", {}))} 圈层 / {sum(p.get("case_circles", {}).values())} 案例' ],
        ["监测笔记总数",p["total_notes"]],
        ["正面笔记",p["positive_count"]],
        ["中性笔记",p["neutral_count"]],
        ["负面笔记",p["negative_count"]],
        ["已二次确认负面",p["confirmed_negative_count"]],
        ["高风险笔记",p["high_risk_count"]],
        ["中风险笔记",p["medium_risk_count"]],
        ["低风险笔记",p["low_risk_count"]],
        ["舆情事件数",len(p["events"])],
    ]
    
    for i,row in enumerate(overview_data,start=2):
        for j,val in enumerate(row,start=1):
            cell=ws.cell(row=i,column=j,value=val)
            cell.font=normal_font
            cell.border=thin_border
            if i==6:  # 表头行
                cell.font=header_font
                cell.fill=header_fill
    ws.column_dimensions['A'].width=20
    ws.column_dimensions['B'].width=30
    ws.column_dimensions['C'].width=15
    ws.column_dimensions['D'].width=15
    
    # Sheet2: 事件分析
    if p["event_analysis"]:
        ws2=wb.create_sheet("事件分析")
        event_headers=["事件标题","事件类型","风险等级","主题标签","关联笔记数","首次发现","最后更新","事件摘要"]
        ws2.append(event_headers)
        for cell in ws2[1]:
            cell.font=header_font
            cell.fill=header_fill
            cell.border=thin_border
            cell.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        for ev in p["event_analysis"]:
            ws2.append([
                ev.get("title",""),ev.get("type",""),ev.get("risk",""),ev.get("topic",""),
                ev.get("notes",0),ev.get("first_seen",""),ev.get("last_seen",""),
                ev.get("summary","")
            ])
        for row in ws2.iter_rows(min_row=2):
            for cell in row:
                cell.font=normal_font
                cell.border=thin_border
                cell.alignment=Alignment(vertical='center',wrap_text=True)
        ws2.freeze_panes="A2"
        widths=[30,15,12,18,12,18,18,50]
        for i,w in enumerate(widths,start=1):
            ws2.column_dimensions[get_column_letter(i)].width=w
    
    # Sheet3: 高风险笔记
    if p["high_risk_notes"]:
        ws3=wb.create_sheet("高风险笔记")
        risk_headers=["标题","作者","发布日期","点赞","评论","收藏","分享","风险分","摘要","链接"]
        ws3.append(risk_headers)
        for cell in ws3[1]:
            cell.font=header_font
            cell.fill=PatternFill(start_color="DC2626",end_color="DC2626",fill_type="solid")
            cell.border=thin_border
            cell.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        for n in p["high_risk_notes"]:
            ws3.append([
                n.get("title",""),n.get("author_nickname",""),n.get("publish_date",""),
                n.get("likes",0),n.get("comments",0),n.get("collects",0),n.get("shares",0),
                n.get("risk_score",0),n.get("summary",""),n.get("url","")
            ])
        for row in ws3.iter_rows(min_row=2):
            for cell in row:
                cell.font=normal_font
                cell.border=thin_border
                cell.alignment=Alignment(vertical='center',wrap_text=True)
        ws3.freeze_panes="A2"
        widths=[35,15,12,8,8,8,8,8,40,40]
        for i,w in enumerate(widths,start=1):
            ws3.column_dimensions[get_column_letter(i)].width=w
    
    # Sheet4: 舆情明细
    ws4=wb.create_sheet("舆情明细")
    ws4.append(NOTE_COLS)
    for cell in ws4[1]:
        cell.font=header_font
        cell.fill=header_fill
        cell.border=thin_border
        cell.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
    for n in p["notes"]:
        ws4.append([_v(n.get(k)) for k in NOTE_COLS])
    for row in ws4.iter_rows(min_row=2):
        for cell in row:
            cell.font=normal_font
            cell.border=thin_border
    ws4.freeze_panes="A2"
    for col in ws4.columns:
        ws4.column_dimensions[get_column_letter(col[0].column)].width=min(max(max(len(str(_v(c.value))) for c in col)+2,10),50)
    
    # Sheet5: 事件明细
    ws5=wb.create_sheet("事件明细")
    ws5.append(EVENT_COLS)
    for cell in ws5[1]:
        cell.font=header_font
        cell.fill=header_fill
        cell.border=thin_border
    for x in p["events"]:
        ws5.append([_v(x.get(k)) for k in EVENT_COLS])
    for row in ws5.iter_rows(min_row=2):
        for cell in row:
            cell.font=normal_font
            cell.border=thin_border
    ws5.freeze_panes="A2"
    
    wb.save(out)

def export_docx(p,out):
    if Document is None:raise RuntimeError("请安装 python-docx")
    out.parent.mkdir(parents=True,exist_ok=True)
    d=Document()
    
    type_names={"daily":"日报","weekly":"周报","monthly":"月报","yearly":"年报"}
    report_title=f"广州太古汇舆情{type_names.get(p['report_type'],p['report_type'])}"
    
    # 标题
    title=d.add_heading(report_title,0)
    title.alignment=1  # 居中
    
    # 基本信息
    d.add_paragraph(f"报告周期：{p['period_start']} 至 {p['period_end']}")
    d.add_paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if p.get("only_confirmed_negative"):
        d.add_paragraph("说明：本报告负面笔记均已通过二次确认。")
    
    # 一、数据概览
    d.add_heading("一、数据概览",1)
    table=d.add_table(rows=1,cols=2)
    table.style='Table Grid'
    hdr_cells=table.rows[0].cells
    hdr_cells[0].text='指标'
    hdr_cells[1].text='数值'
    overview_items=[
        ("监测笔记总数",str(p["total_notes"])),
        ("正面笔记",str(p["positive_count"])),
        ("中性笔记",str(p["neutral_count"])),
        ("负面笔记",str(p["negative_count"])),
        ("已二次确认负面",str(p["confirmed_negative_count"])),
        ("高风险笔记",str(p["high_risk_count"])),
        ("中风险笔记",str(p["medium_risk_count"])),
        ("低风险笔记",str(p["low_risk_count"])),
        ("舆情事件数",str(len(p["events"]))),
    ]
    for k,v in overview_items:
        row_cells=table.add_row().cells
        row_cells[0].text=k
        row_cells[1].text=v
    
    # 二、事件分析
    if p["event_analysis"]:
        d.add_heading("二、舆情事件分析",1)
        for i,ev in enumerate(p["event_analysis"],1):
            d.add_heading(f"事件{i}：{ev.get('title','未知')}",2)
            d.add_paragraph(f"事件类型：{ev.get('type','-')}")
            d.add_paragraph(f"风险等级：{ev.get('risk','-')}")
            d.add_paragraph(f"主题标签：{ev.get('topic','-')}")
            d.add_paragraph(f"关联笔记数：{ev.get('notes',0)}")
            d.add_paragraph(f"首次发现：{ev.get('first_seen','-')}")
            d.add_paragraph(f"最后更新：{ev.get('last_seen','-')}")
            d.add_paragraph(f"事件摘要：{ev.get('summary','-')}")
    
    # 三、高风险笔记
    if p["high_risk_notes"]:
        d.add_heading("三、高风险笔记TOP10",1)
        table2=d.add_table(rows=1,cols=5)
        table2.style='Table Grid'
        hdr=table2.rows[0].cells
        hdr[0].text='序号'
        hdr[1].text='标题'
        hdr[2].text='作者'
        hdr[3].text='发布日期'
        hdr[4].text='互动量'
        for i,n in enumerate(p["high_risk_notes"],1):
            row=table2.add_row().cells
            row[0].text=str(i)
            row[1].text=n.get("title","")[:50]
            row[2].text=n.get("author_nickname","")
            row[3].text=n.get("publish_date","")
            engage=int(n.get("likes",0) or 0)+int(n.get("comments",0) or 0)*3
            row[4].text=str(engage)
    
    # 四、舆情明细
    d.add_heading("四、舆情明细",1)
    d.add_paragraph(f"共{p['total_notes']}条笔记，详见附件Excel表格。")
    
    d.save(out)

def export_report(kind="daily",start=None,end=None,formats=("docx","csv","xlsx")):
    p=payload(kind,start,end)
    OUT.mkdir(parents=True,exist_ok=True)
    stamp=f'{p["period_start"]}_{p["period_end"]}'
    r={}
    if "docx" in formats:
        r["docx"]=OUT/f"广州太古汇舆情_{kind}_{stamp}.docx"
        export_docx(p,r["docx"])
    if "csv" in formats:
        r["csv"]=OUT/f"广州太古汇舆情_{kind}_{stamp}.csv"
        export_csv(p,r["csv"])
    if "xlsx" in formats:
        r["xlsx"]=OUT/f"广州太古汇舆情_{kind}_{stamp}.xlsx"
        export_xlsx(p,r["xlsx"])
    return {"payload":p,"files":{k:str(v) for k,v in r.items()}}
