# -*- coding: utf-8 -*-
"""44-screen registry metadata: id, domain, trilingual title, icon, nav group."""

# id: (domain, group, icon, zh, en, ko, dock)
SCREENS = [
 # ---- Account & Entry (4) ----
 ("ACC-01","ACCOUNT","acc","user","领域登录入口","Domain-first Sign-in","도메인 로그인",False),
 ("ACC-02","ACCOUNT","acc","target","主体选择与领域视角","Subject & Domain Lens Entry","주체 및 도메인 선택",False),
 ("ACC-03","ACCOUNT","acc","home","全局工作空间启动","Global Workspace Launch","워크스페이스 시작",True),
 ("ACC-04","ACCOUNT","acc","security","账号恢复与权限守卫","Account Recovery & Auth Guard","계정 복구 및 인증 가드",False),
 # ---- CTH (10) ----
 ("CTH-01","CTH","cth","compass","商业运营总览","Commerce Operations Overview","커머스 운영 개요",True),
 ("CTH-02","CTH","cth","layers","主体档案 / 业务单元 / 品牌业态","Subject Profile · Units · Brands","주체 프로필·사업단위·브랜드",False),
 ("CTH-03","CTH","cth","runtime","实时监测","Real-time Monitoring","실시간 모니터링",False),
 ("CTH-04","CTH","cth","event","事件与事件关系","Events & Event Graph","이벤트 및 이벤트 관계",False),
 ("CTH-05","CTH","cth","calendar","舆情日历","Sentiment Calendar","감성 캘린더",False),
 ("CTH-06","CTH","cth","message","负面与用户/评论反馈","Negative & Feedback","부정 및 사용자 피드백",False),
 ("CTH-07","CTH","cth","trend","趋势分析","Trend Analysis","추세 분석",False),
 ("CTH-08","CTH","cth","case","案例库 / 案例分析 / 知识库","Cases · Analysis · Knowledge","케이스·분석·지식베이스",False),
 ("CTH-09","CTH","cth","risk","风险中心与决策看板","Risk Center & Decision Board","리스크 센터·의사결정",False),
 ("CTH-10","CTH","cth","report","报告 / 周报 / 证据","Reports · Weekly · Evidence","리포트·주보·증거",False),
 # ---- BMP (11) ----
 ("BMP-01","BMP","bmp","compass","品牌市场总览","Brand & Market Overview","브랜드&마켓 개요",True),
 ("BMP-02","BMP","bmp","campaign","品牌中心 / 多品牌与竞品","Brand Center · Competitors","브랜드 센터·경쟁사",False),
 ("BMP-03","BMP","bmp","research","市场情报","Market Intelligence","마켓 인텔리전스",False),
 ("BMP-04","BMP","bmp","trend","传播分析","Communication Analysis","커뮤니케이션 분석",False),
 ("BMP-05","BMP","bmp","creators","创作者 KOS/KOL/KOC/UGC","Creators KOS/KOL/KOC/UGC","크리에이터 KOS/KOL/KOC",False),
 ("BMP-06","BMP","bmp","content","内容中心","Content Center","콘텐츠 센터",False),
 ("BMP-07","BMP","bmp","campaign","话题活动","Topic Campaign","토픽 캠페인",False),
 ("BMP-08","BMP","bmp","podcast","播客工作室","Podcast Studio","팟캐스트 스튜디오",False),
 ("BMP-09","BMP","bmp","evaluation","品牌报告与评估","Brand Reports & Evaluation","브랜드 리포트·평가",False),
 ("BMP-10","BMP","bmp","risk","品牌风险与事件","Brand Risk & Events","브랜드 리스크·이벤트",False),
 ("BMP-11","BMP","bmp","target","对标与竞品分析","Benchmark & Competition","벤치마크·경쟁 분석",False),
 # ---- AI (5) ----
 ("AI-01","AI","ai","orb","AI 意图入口 / Composer","AI Composer · Intent Home","AI 컴포저·의도 홈",True),
 ("AI-02","AI","ai","layers","能力→任务工作台","Capability→Task Workspace","역량→작업 워크스페이스",False),
 ("AI-03","AI","ai","link","证据锚定分析线程","Evidence-grounded Thread","증거 기반 분석 스레드",False),
 ("AI-04","AI","ai","skill","Agent / 技能中心","Agent / Skill Hub","에이전트·스킬 허브",False),
 ("AI-05","AI","ai","ops","AI Gateway 与 Provider","AI Gateway & Providers","AI 게이트웨이·프로바이더",False),
 # ---- System (8) ----
 ("SYS-01","SYSTEM","system","runtime","运行时健康","Runtime Health","런타임 헬스",False),
 ("SYS-02","SYSTEM","system","collector","采集器状态","Collector Status","수집기 상태",False),
 ("SYS-03","SYSTEM","system","database","数据库与事实链","Database & Truth Chain","데이터베이스·진실 체인",False),
 ("SYS-04","SYSTEM","system","security","安全与权限","Security & Permission","보안·권한",False),
 ("SYS-05","SYSTEM","system","settings","设置 / 外观 / 语言","Settings · Appearance · Language","설정·외관·언어",False),
 ("SYS-06","SYSTEM","system","browser","内部浏览器","Internal Browser","내부 브라우저",False),
 ("SYS-07","SYSTEM","system","evaluation","验收评估","Evaluation / Acceptance","평가·어셉턴스",False),
 ("SYS-08","SYSTEM","system","ops","可观测 / 日志","Observability & Logs","옵저버빌리티·로그",False),
 # ---- Shared (6) ----
 ("SH-01","SHARED","shared","content","内容创作工作室","Content Creation Studio","콘텐츠 제작 스튜디오",False),
 ("SH-02","SHARED","shared","link","证据库","Evidence Library","증거 라이브러리",False),
 ("SH-03","SHARED","shared","database","Canonical 数据 / 指标浏览器","Canonical Data & Metric Explorer","캐노니컬 데이터·지표",False),
 ("SH-04","SHARED","shared","download","报告导出中心","Report Export Center","리포트 내보내기",False),
 ("SH-05","SHARED","shared","evaluation","学习与评估资产","Learning & Evaluation Assets","학습·평가 자산",False),
 ("SH-06","SHARED","shared","bell","通知 / 任务中心","Notification & Task Center","알림·작업 센터",False),
]

SCREEN_IDS=[s[0] for s in SCREENS]
assert len(SCREENS)==44, len(SCREENS)
assert len(set(SCREEN_IDS))==44

# Navigation groups (order). group key -> labelKey, item ids in order
NAV = [
 ("navgroup.cth",[s[0] for s in SCREENS if s[1]=="CTH"]),
 ("navgroup.bmp",[s[0] for s in SCREENS if s[1]=="BMP"]),
 ("navgroup.ai",[s[0] for s in SCREENS if s[1]=="AI"]),
 ("navgroup.shared",[s[0] for s in SCREENS if s[1]=="SHARED"]),
 ("navgroup.system",[s[0] for s in SCREENS if s[1]=="SYSTEM"]),
]
ACCOUNT_IDS=[s[0] for s in SCREENS if s[1]=="ACCOUNT"]
META={s[0]:{"domain":s[1],"group":s[2],"icon":s[3],"zh":s[4],"en":s[5],"ko":s[6],"dock":s[7]} for s in SCREENS}
