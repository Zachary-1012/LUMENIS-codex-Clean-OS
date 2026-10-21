from pathlib import Path
import re,json,hashlib,collections
out=Path('product_task_register_v2_20261017')
root=Path('recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main')
source_names=['00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md','00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md','00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md']
titles={int(n):t for n,t in re.findall(r'(?m)^(\d+)\. (.+)$',(out/'USER_REPORT.txt').read_text())}
# Explicit original-ID classification; multi-category coverage is intentional, never a replacement for original text.
groups={
1:'7 37 49.0 59 93',
2:'4 18 19 20 24 26 27 29 30 34 38 40 42 43 44 46 52 53 54 55 57 61 62 63 64 65 66 67 69 71 75 85 86 87 89 111 113 117 118 119 127 129 132 134 136 137 138 176 177',
3:'143 144 145 146 147 148 149 150 151 152 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169',
4:'15 17 21 23 31 36 39 50 56 83 84 108 109 115 130 181 185 186 187',
5:'10 11 78 91 92 110 125 136 170',
6:'42 54 65 69 85 86 102 105 114 120 124 126 128 135 139 166 167 176 177 178 179 189',
7:'2 8 9 51 68 88 94 95 123 133 140 178 179 180',
8:'1 32 51 82 115 133 188',
9:'33 61 63 76 77 80 81 97 98 99 100 101 102 103 104 105 106 114 120 121 122 134 136 138 170 171 172 173 182',
10:'12 13 23 28 55 64 79 107 124 128 173 174 183 184',
11:'14 16 116 142',
12:'5 14 15 16 22 24 36 45 58 116 141 142',
13:'',
14:'49.0 49.1 49.2 49.3 49.4 49.5 49.6 49.7 60 72 131',
15:'25 131',16:'11',
17:'3 4 6 16 25 26 27 35 37 41 43 44 45 46 58 60 70 71 73 75 87 89 90 96 125 129 132 175',
18:'19 20 25 35 47 48 66 67 70 73 90 112',19:''}
gmap=collections.defaultdict(list)
for group,ids in groups.items():
 for n in ids.split():gmap['G'+n].append(group)
evid=[
('EV-STABLE','lumenis_working_20261017/runtime_validation/unified-learning-joint-evidence-freeze-1409/REPORT.md',3,19,[2,4,5,10,17,18],'47c719612ef7ab91bbb0c96bbf7ad15dca8c0c3a2c7a555303dbf5bf3b6e49ae','1248测试；8应用进程57请求；HPR冷开；Learning gain=0/NOT_ELIGIBLE；Experience原11失败另列'),
('EV-EXP','lumenis_working_20261017/runtime_validation/experience-owner-repair-1409/HANDOFF.md',1,60,[2,17],'ecdd528e8206b935f6fe6fdb11e7c5a94c9de853babb1c88dcdb6bccd1caa234','独立候选284测试=278通过6失败；未整合/部署；不是全Experience通过'),
('EV-CREATION','creation_multiplatform_20261017/IMPLEMENTATION_REPORT.md',1,67,[9,17],'CHANGE_MANIFEST.json固定6文件','182通过+真实隔离HTTP保存重开分析；不等原创意/语言/平台传播质量已验'),
('EV-MATH','mathematical_models_research_20261017/REPORT.md',1,122,[3],'独立研究及G165候选','九family/26稿保留OPEN；G165独立71通过；工程样本非实际ROI'),
('EV-MATH-DEPS','mathematical_models_research_20261017/dependency_plan/REPORT.md',1,29,[3,17],'独立math_validation_venv','42通过，含2项OR-Tools/BERTopic实计算；共享环境未改'),
('EV-MATH-JOINT','mathematical_models_research_20261017/combined_compatibility/REPORT.md',1,None,[3,17],'050abc169026dc5d54782bc745d461a0fbf6cecbe22055e4bc837843547995e3','1319组合、两MMM及HPR base/small冷开通过；新增真实ONNX Owner探针1次/0网络、原0次观测失败保留；源码及共享freeze无漂移。独立组合未采用到共享环境/未部署，不等全产品兼容'),
('EV-BROWSER','lumenis_working_20261017/runtime_validation/browser-addon-evidence/HANDOFF.md',1,44,[7,8,17],'独立6文件候选','61定向通过；扩展6原基线失败；Source准入/AI实际工具/真实浏览器/媒体及四端OPEN'),
('EV-BROWSER-REVIEW','product_task_register_v2_20261017/evidence/browser_capture_review/REVIEW.md',1,None,[8,17],'原Browser6文件候选独立只读审查；证据复制hash一致','61定向重跑通过不关闭独立发现：脱敏/可伪造引用/排队超时/human lease重试/过期receipt回读。均隔离合成测试，无真实凭据事故；所有问题未闭'),
('EV-UX','recovery_inspection_20261017/review-code-freeze-20261017T1437Z/README.md',1,44,[11,12,17],'1437Z冻结；194文件hash','446 Node/最小DOM通过、44示例入口；40–68未恢复；视觉PENDING/后端UNBOUND'),
('EV-INTERP','interpretability_trace_20261017/README.md',1,32,[16],'独立小网络CPU实验','首个16参数实验10测试；另一个8单元训练实验600步、1/8解释阈值通过/7未解释；这份研究报告不含后续PhaseA接线验收'),
('EV-INTERP-A','lumenis_working_20261017/runtime_validation/interpretability-phase-a-1433/INTEGRATION_REPORT.md',1,None,[16,17],'独立5文件PhaseA候选；稳定47c基底','26新增通过；扩展157通过6基线失败；真实Task/Evidence/3指标原子回滚与分进程冷开；未整合/部署，非真实大模型解释'),
('EV-EVO','evoontology_research_20261017/REPORT.md',1,None,[15],'独立研究','研究与离线实验，不是正式产品集成'),
('EV-MEDIA','media_validation_20261017/actual-asr/REPORT.md',1,None,[4,10],'独立ASR真实调用','第三方Whisper证据，不等自研模型或全语言质量验收')]
evidence=[]
for eid,path,ls,le,gs,version,claim in evid:
 p=Path(path);txt=p.read_text();n=len(txt.splitlines())
 evidence.append(dict(evidence_id=eid,path=path,line_start=ls,line_end=min(le or n,n),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),groups=gs,version=version,scope_and_limit=claim,closure_effect='RELATED_PROGRESS_ONLY_NOT_REQUIREMENT_ACCEPTANCE'))

def progress(gs):return [e['evidence_id'] for e in evidence if set(gs)&set(e['groups'])]
def base(id,kind,src,start,end,text,section,gs):
 return dict(id=id,record_type=kind,source_path=src,line_start=start,line_end=end,section=section,original_text=text,report_groups=gs,report_group_titles=[titles[x] for x in gs],verification_status='NOT_VERIFIED',progress_evidence=progress(gs),progress_evidence_scope='相关模块限定版本证据；未完成本条逐验收点映射，不构成本条已通过。',unclosed='保留原文全部适用要求；需对应源码、实际接线、正常任务成果、保存修订重开恢复及适用表面证据。历史状态仅作来源，不自动继承为今日状态。')
rows=[];sources=[];g_ids=[];coverage=[]
plan_section_routes={0:[1,17],1:[1,2,4,8],2:[12,17],3:[2,6,8,9,10,12],4:[11,12],5:[1,2],6:[2,17],7:[1],8:[1],9:[1,17],10:[4,17],11:[1,4,6,8],12:[3,4],13:[3],14:[10],15:[5,9,10],16:[4],17:[4,15,17],18:[11,12],19:[3,6,9,10],20:[11,12,14],21:[6,12,14],22:[1,2,12,17]}
for si,src in enumerate(source_names):
 p=root/src;lines=p.read_text().splitlines();section='前言';section_num=0;seen=[];pending=[]
 sources.append({'path':src,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'line_count':len(lines),'source_role':['完整产品规划及原G要求','唯一完整产品草图','既有Owner与R/J/U要求'][si]})
 for ln,line in enumerate(lines,1):
  if not line.strip():continue
  seen.append(ln)
  if line.startswith('#'):
   section=line.lstrip('# ').strip();m=re.match(r'(\d+)\.',section)
   if m:section_num=int(m[1])
  m=re.match(r'^\|\s*(G\d+(?:\.\d+)?)\s*\|',line) if si==0 else None
  if m:
   ident=m[1];assert ident in gmap,ident
   gs=gmap[ident];record=base(ident,'ORIGINAL_G_REQUIREMENT',src,ln,ln,line,section,gs)
   record['routing_basis']='原G条目标题及完整要求人工分组；多个大项共同覆盖，不转移Owner'
   record['original_columns']=[x.strip() for x in line.strip('|').split('|')]
   rows.append(record);g_ids.append(ident);continue
  # Every nonblank source line is retained: headers/separators are explicitly not additional requirements.
  structural=line.startswith('#') or bool(re.match(r'^\|[\s:|\-]+\|$',line))
  if si==0:gs=plan_section_routes.get(section_num,[1,17])
  elif si==1:
   if section_num==2:gs=[12]
   elif section_num==3:gs=[2,9,10,12]
   elif any(x in section for x in ['CTH-','BMP-']):gs=[2,12]
   elif any(x in section for x in ['SH-']):gs=[2,6,9,10,12]
   elif 'AI-' in section:gs=[4,5,12]
   elif 'SYS-06' in section or '浏览器' in section:gs=[8,12]
   elif section_num==1:gs=[11,12]
   else:gs=[2,12,17]
  else:gs=[1,2,17]
  ident=f'{["PLAN","SKETCH","OWNER"][si]}-L{ln:04d}'
  record=base(ident,'SOURCE_STRUCTURE' if structural else 'RETAINED_SOURCE_CLAUSE',src,ln,ln,line,section,gs)
  record['routing_basis']='按来源章节归入范围；不是逐义务验收映射。原文与既有Owner优先，全部行保留以防关键词筛选遗漏。'
  # Preserve exact R/J/U named rows with repeat occurrence distinguishable.
  rid=re.match(r'^\|\s*((?:R|U)\d{2}|J\d+)\s*\|',line)
  if rid:record['original_requirement_id']=rid[1];record['record_type']='RETAINED_RJU_ROW'
  rows.append(record)
 coverage.append(dict(source_path=src,nonblank_source_lines=len(seen),retained_lines=len(seen),missing_nonblank_lines=[],coverage_ratio=1.0))
# New requirements kept separately, source is latest user request as quoted by parent, not falsely attributed to main.
new=[(8,'新增浏览器全维度用户/AI双入口','用户与AI同一受控能力，全部所需内容/结构/媒体维度，真实任务掌握能力；不是同handler即完成。'),(9,'原原创意完整保留并新增常规稿','原创策略/表达/多模态/探索式创作独立验收；常规稿模板快路新增，不替代原要求。'),(11,'200+交互与44非上限','至少200有用交互；44示例/屏不是上限；参数物理真正参与计算。'),(14,'全部SaaS/社媒及REA研究','原全部对标目标与新增REA等深入研究适配并实测，不能只做最近熟悉目标。'),(15,'Claude全例/EvoOntology/Obelisk','全部原开源适配任务累加，按现有Owner逐项研究实现验证。'),(16,'模型可解释性','Nick/Goodfire研究及独立反例/保留/干预/保存重载，验证后再接产品。'),(18,'全日志备份','代码、数据/实际模型、实验/测试/失败/开发日志、恢复点完整关联保存和Drive备份，不只成功摘要。'),(1,'三条总线与并行','升级优化补充、按完整规划开发闭环、整体交付是概括；详细范围保留，按依赖/版本/修改面/阶段冻结/同版集成有章法并行。'),(18,'逐项标准研究报告','每一样研究独立编号：问题、原始来源/版本、方法、源码/实验、结论限制、序境适配、实现验证、未完下一步；关联代码/测试/开发日志及Drive备份。')]
for i,(g,title,body) in enumerate(new,1):
 r=base(f'ADD-{i:03d}','ADDITIVE_USER_REQUIREMENT','2026-10-17用户本轮要求（由主对话转达，非仓库原文）',None,None,body,title,[g]);r['routing_basis']='最新用户要求只追加，不覆盖原G/R/J/U';rows.append(r)
ledger={'title':'LUMENIS V2完整产品要求对照账（只读审计交付，不是新增产品治理/派工）','as_of_utc':'2026-10-17T14:49:00Z','main_commit':'4dab98ed6357133da9307de846180ed4f7bba5f5','scope_note':'三个指定主源全文非空行覆盖；不是声明仓库全部被引用文件/每个来源附件已逐页读完。行数不等要求数。原G已195唯一逐条保留；所有状态保守NOT_VERIFIED，相关测试不自动关闭任何整条要求。','report_groups':titles,'sources':sources,'evidence':evidence,'rows':rows}
(out/'REQUIREMENTS_LEDGER.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2))
check={'original_g_rows':len(g_ids),'unique_g_ids':len(set(g_ids)),'expected_original_g_rows':195,'matches_195':len(g_ids)==len(set(g_ids))==195,'decimal_g_ids':sorted([x for x in g_ids if '.' in x]),'absent_integer_ids_in_original':['G49','G74'],'invented_ids':[],'duplicate_g_ids':[x for x,n in collections.Counter(g_ids).items() if n>1],'g_ids_missing_report_group':[r['id'] for r in rows if r['record_type']=='ORIGINAL_G_REQUIREMENT' and not r['report_groups']],'source_coverage':coverage,'rju_ids_retained':sorted(set(r['original_requirement_id'] for r in rows if 'original_requirement_id' in r)),'rju_expected_missing':sorted({*[f'R{i:02d}' for i in range(1,16)],*[f'J{i}' for i in range(1,9)],*[f'U{i:02d}' for i in range(1,26)]}-{r['original_requirement_id'] for r in rows if 'original_requirement_id' in r}),'total_records_including_structure':len(rows),'record_types':dict(collections.Counter(r['record_type'] for r in rows)),'acceptance_status_counts':dict(collections.Counter(r['verification_status'] for r in rows)),'coverage_boundary':'文本保全验证，不是逐义务源码/运行验收完成；全部引用原文件/附件未在此账穷尽展开，保留原文引用及定位，后续仍须追踪。','missing_evidence_files':[e['path'] for e in evidence if not Path(e['path']).exists()]}
assert check['matches_195'] and not check['rju_expected_missing']
(out/'COVERAGE_CHECK.json').write_text(json.dumps(check,ensure_ascii=False,indent=2))
(out/'G_EXTRACTION_CHECK.json').write_text(json.dumps({k:v for k,v in check.items() if 'g_' in k or k in ['matches_195','decimal_g_ids','absent_integer_ids_in_original','invented_ids']},ensure_ascii=False,indent=2))
md=['# V2 整个产品要求、进度与未闭合总账','',ledger['scope_note'],'','## 固定19项完整审核稿','',(out/'USER_REPORT.txt').read_text(),'','## 版本隔离与进度证据','']
for e in evidence:md+=['### '+e['evidence_id'],f"- 证据：{e['path']}:{e['line_start']}–{e['line_end']}",'- 版本：'+e['version'],'- 范围：'+e['scope_and_limit'],'- 本证据仅支持限定进度，不自动关闭下述任何整条要求。','']
md+=['## 原195条要求逐项原文账','原文编号与顺序保留；未验不等于未实现，NOT_VERIFIED明确表示本条完整验收尚未建立。','']
for r in rows:
 if r['record_type']!='ORIGINAL_G_REQUIREMENT':continue
 md+=['### '+r['id'],r['original_text'],f"- 来源：{r['source_path']}:{r['line_start']}",'- 对应固定大项：'+','.join(str(x) for x in r['report_groups']),'- 进度证据（仅关联范围）：'+(','.join(r['progress_evidence']) or '尚无本轮精确证据'),'- 本条完整状态：NOT_VERIFIED','- 未闭合：'+r['unclosed'],'']
md+=['## 非G原文覆盖与R/J/U保留','三个主源的全部非空行（包括章节、表行、正文与结构）都保存在REQUIREMENTS_LEDGER.json；不是只摘关键词或熟悉模块。每行有原文、来源、行号、分组、相关证据与未闭合状态。R/J/U原标签保留，多次出现不改号。所有引用合同仍有效，未逐项展开的被引文件不能被本文件缩减。','']
for s in sources:md.append(f"- {s['path']}：{s['line_count']}行；SHA256 {s['sha256']}")
md+=['','文本覆盖校验见COVERAGE_CHECK.json。此处百分比仅是指定来源文本保全率，不是产品进度或验收通过率。']
(out/'MASTER_REGISTER.md').write_text('\n'.join(md))
print(json.dumps(check,ensure_ascii=False,indent=2))
