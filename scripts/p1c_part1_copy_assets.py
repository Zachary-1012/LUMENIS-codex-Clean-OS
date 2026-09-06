#!/usr/bin/env python3
"""P1-C Part 1: Create 13-dir structure + copy research assets + generate _index.md"""
import os, shutil, json, hashlib
from datetime import datetime

PROJECT = r'D:\Taikoo-monitor-new'
LIB = os.path.join(PROJECT, 'intelligence_library')
OSAI = r'D:\Zachary OS AI'
ADRH = r'D:\AI-Development-Research-Hub'
SICI = r'D:\SICI-Core'

# 13 directories (exact names from user spec)
DIRS = [
    '00_总览',
    '01_ZBC专项研究',
    '02_ZBMP研究',
    '03_CTH研究',
    '04_OSAI核心技术',
    '05_Runtime',
    '06_Security',
    '07_Data-Evidence-Evaluation',
    '08_UI-UX',
    '09_Research-Hub',
    '10_工程审计方法',
    '11_前沿研究',
    '12_研究到ZBC落地索引',
    '_index',
]

def safe_makedirs(path):
    os.makedirs(path, exist_ok=True)

def copy_dir(src, dst, prefix=None):
    """Copy directory contents, return list of copied file paths"""
    copied = []
    if not os.path.exists(src):
        return copied
    safe_makedirs(dst)
    for root, dirs, files in os.walk(src):
        # skip hidden/cache dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'node_modules']
        rel = os.path.relpath(root, src)
        if prefix:
            dst_root = os.path.join(dst, prefix, rel) if rel != '.' else os.path.join(dst, prefix)
        else:
            dst_root = os.path.join(dst, rel) if rel != '.' else dst
        safe_makedirs(dst_root)
        for f in files:
            if f.startswith('.') or f.endswith('.pyc'):
                continue
            src_f = os.path.join(root, f)
            dst_f = os.path.join(dst_root, f)
            try:
                shutil.copy2(src_f, dst_f)
                copied.append(dst_f)
            except Exception as e:
                print(f"  COPY FAIL: {src_f} -> {e}")
    return copied

def copy_file(src, dst_dir, new_name=None):
    """Copy single file"""
    if not os.path.exists(src):
        return None
    safe_makedirs(dst_dir)
    name = new_name or os.path.basename(src)
    dst = os.path.join(dst_dir, name)
    try:
        shutil.copy2(src, dst)
        return dst
    except Exception as e:
        print(f"  COPY FAIL: {src} -> {e}")
        return None

def gen_index(dir_path, dir_name, copied_files):
    """Generate _index.md for a directory"""
    idx_path = os.path.join(dir_path, '_index.md')
    lines = [
        f'# {dir_name} - 资产索引',
        f'',
        f'> 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'> 文件数: {len(copied_files)}',
        f'',
        f'## 文件清单',
        f'',
    ]
    # Group by subdirectory
    groups = {}
    for f in copied_files:
        rel = os.path.relpath(f, dir_path)
        parts = rel.split(os.sep)
        if len(parts) > 1:
            sub = parts[0]
        else:
            sub = '(根目录)'
        groups.setdefault(sub, []).append(rel)
    
    for sub in sorted(groups.keys()):
        lines.append(f'### {sub}')
        lines.append('')
        for f in sorted(groups[sub]):
            size = os.path.getsize(os.path.join(dir_path, f)) if os.path.exists(os.path.join(dir_path, f)) else 0
            lines.append(f'- `{f}` ({size} bytes)')
        lines.append('')
    
    with open(idx_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return idx_path

# ============================================================
# STEP 1: Create directories
# ============================================================
print("=== STEP 1: Creating 13 directories ===")
for d in DIRS:
    safe_makedirs(os.path.join(LIB, d))
    print(f"  OK: {d}")

# Track all copied files per directory
all_copied = {d: [] for d in DIRS}

# ============================================================
# STEP 2: Copy OSAI research assets
# ============================================================
print("\n=== STEP 2: Copying OSAI assets ===")

# 03-RESEARCH/LANGUAGE-BRAND-LIFE -> 04_OSAI核心技术/语言品牌生命
src = os.path.join(OSAI, '03-RESEARCH')
if os.path.exists(src):
    # Copy all of 03-RESEARCH (includes P0-AGENT-ORG, LANGUAGE-BRAND-LIFE, etc.)
    # P0-AGENT-ORG -> 11_前沿研究/AgentOrg
    ag_src = os.path.join(src, 'P0-AGENT-ORG')
    if os.path.exists(ag_src):
        files = copy_dir(ag_src, os.path.join(LIB, '11_前沿研究', 'AgentOrg'))
        all_copied['11_前沿研究'].extend(files)
        print(f"  03-RESEARCH/P0-AGENT-ORG -> 11_前沿研究/AgentOrg: {len(files)} files")
    # Other 03-RESEARCH content -> 09_Research-Hub
    for item in os.listdir(src):
        item_path = os.path.join(src, item)
        if item == 'P0-AGENT-ORG':
            continue
        if os.path.isdir(item_path):
            files = copy_dir(item_path, os.path.join(LIB, '09_Research-Hub', '03-RESEARCH', item))
            all_copied['09_Research-Hub'].extend(files)
            print(f"  03-RESEARCH/{item} -> 09_Research-Hub: {len(files)} files")
        elif os.path.isfile(item_path):
            f = copy_file(item_path, os.path.join(LIB, '09_Research-Hub', '03-RESEARCH'))
            if f: all_copied['09_Research-Hub'].append(f)

# learning-feed/brand-marketing-knowledge-* -> 02_ZBMP研究/品牌营销知识
# learning-feed/KOS-* -> 02_ZBMP研究/KOS研究
lf = os.path.join(OSAI, 'learning-feed')
if os.path.exists(lf):
    for item in os.listdir(lf):
        item_path = os.path.join(lf, item)
        if not os.path.isfile(item_path):
            # copy subdirs to 09_Research-Hub/learning-feed
            files = copy_dir(item_path, os.path.join(LIB, '09_Research-Hub', 'learning-feed', item))
            all_copied['09_Research-Hub'].extend(files)
            continue
        name_lower = item.lower()
        if 'brand-marketing' in name_lower or 'brand_marketing' in name_lower:
            f = copy_file(item_path, os.path.join(LIB, '02_ZBMP研究', '品牌营销知识'))
            if f: all_copied['02_ZBMP研究'].append(f)
        elif 'kos' in name_lower:
            f = copy_file(item_path, os.path.join(LIB, '02_ZBMP研究', 'KOS研究'))
            if f: all_copied['02_ZBMP研究'].append(f)
        elif 'cth' in name_lower or 'poms' in name_lower or 'opinion' in name_lower:
            f = copy_file(item_path, os.path.join(LIB, '03_CTH研究', '学习资料'))
            if f: all_copied['03_CTH研究'].append(f)
        else:
            f = copy_file(item_path, os.path.join(LIB, '09_Research-Hub', 'learning-feed'))
            if f: all_copied['09_Research-Hub'].append(f)
    print(f"  learning-feed processed")

# ai-os-research/* -> 09_Research-Hub/AI操作系统研究
src = os.path.join(OSAI, 'ai-os-research')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '09_Research-Hub', 'AI操作系统研究'))
    all_copied['09_Research-Hub'].extend(files)
    print(f"  ai-os-research -> 09_Research-Hub: {len(files)} files")

# research-inbox/* -> 09_Research-Hub/研究收件箱
src = os.path.join(OSAI, 'research-inbox')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '09_Research-Hub', '研究收件箱'))
    all_copied['09_Research-Hub'].extend(files)
    print(f"  research-inbox -> 09_Research-Hub: {len(files)} files")

# 序境/00-GOVERNANCE -> 10_工程审计方法/治理
# 序境/01-PRODUCT -> 01_ZBC专项研究/产品研究
# 序境/08-AUDIT -> 10_工程审计方法
xj = os.path.join(OSAI, '序境')
if os.path.exists(xj):
    for item in os.listdir(xj):
        item_path = os.path.join(xj, item)
        if not os.path.isdir(item_path):
            continue
        if 'GOVERNANCE' in item.upper() or '00' in item:
            files = copy_dir(item_path, os.path.join(LIB, '10_工程审计方法', '治理', item))
            all_copied['10_工程审计方法'].extend(files)
            print(f"  序境/{item} -> 10_工程审计方法/治理: {len(files)} files")
        elif 'PRODUCT' in item.upper() or '01' in item:
            files = copy_dir(item_path, os.path.join(LIB, '01_ZBC专项研究', '产品研究', item))
            all_copied['01_ZBC专项研究'].extend(files)
            print(f"  序境/{item} -> 01_ZBC专项研究/产品研究: {len(files)} files")
        elif 'AUDIT' in item.upper() or '08' in item:
            files = copy_dir(item_path, os.path.join(LIB, '10_工程审计方法', '审计', item))
            all_copied['10_工程审计方法'].extend(files)
            print(f"  序境/{item} -> 10_工程审计方法/审计: {len(files)} files")
        else:
            files = copy_dir(item_path, os.path.join(LIB, '01_ZBC专项研究', '序境', item))
            all_copied['01_ZBC专项研究'].extend(files)
            print(f"  序境/{item} -> 01_ZBC专项研究: {len(files)} files")

# research/podcast-module -> 02_ZBMP研究/播客研究
src = os.path.join(OSAI, 'research')
if os.path.exists(src):
    for item in os.listdir(src):
        item_path = os.path.join(src, item)
        if 'podcast' in item.lower():
            files = copy_dir(item_path, os.path.join(LIB, '02_ZBMP研究', '播客研究', item)) if os.path.isdir(item_path) else [copy_file(item_path, os.path.join(LIB, '02_ZBMP研究', '播客研究'))]
            all_copied['02_ZBMP研究'].extend([f for f in files if f])
            print(f"  research/{item} -> 02_ZBMP研究/播客研究")
        else:
            if os.path.isdir(item_path):
                files = copy_dir(item_path, os.path.join(LIB, '09_Research-Hub', 'research', item))
            else:
                files = [copy_file(item_path, os.path.join(LIB, '09_Research-Hub', 'research'))]
            all_copied['09_Research-Hub'].extend([f for f in files if f])

# baseline/ -> 10_工程审计方法/基线
src = os.path.join(OSAI, 'baseline')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '10_工程审计方法', '基线'))
    all_copied['10_工程审计方法'].extend(files)
    print(f"  baseline -> 10_工程审计方法/基线: {len(files)} files")

# reconciliation/ -> 10_工程审计方法/对账
src = os.path.join(OSAI, 'reconciliation')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '10_工程审计方法', '对账'))
    all_copied['10_工程审计方法'].extend(files)
    print(f"  reconciliation -> 10_工程审计方法/对账: {len(files)} files")

# 01-22 matrix files (root level .md) -> 10_工程审计方法/工程矩阵
for i in range(1, 23):
    prefix = f'{i:02d}_'
    for f in os.listdir(OSAI):
        if f.startswith(prefix) and f.endswith('.md'):
            copied = copy_file(os.path.join(OSAI, f), os.path.join(LIB, '10_工程审计方法', '工程矩阵'))
            if copied: all_copied['10_工程审计方法'].append(copied)
print("  01-22 matrix files -> 10_工程审计方法/工程矩阵")

# contracts/ -> 10_工程审计方法/合约
src = os.path.join(OSAI, 'contracts')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '10_工程审计方法', '合约'))
    all_copied['10_工程审计方法'].extend(files)
    print(f"  contracts -> 10_工程审计方法/合约: {len(files)} files")

# docs/ -> split by content
src = os.path.join(OSAI, 'docs')
if os.path.exists(src):
    for item in os.listdir(src):
        item_path = os.path.join(src, item)
        name_lower = item.lower()
        if os.path.isdir(item_path):
            if 'ui' in name_lower:
                files = copy_dir(item_path, os.path.join(LIB, '08_UI-UX', item))
                all_copied['08_UI-UX'].extend(files)
            elif 'audit' in name_lower:
                files = copy_dir(item_path, os.path.join(LIB, '10_工程审计方法', item))
                all_copied['10_工程审计方法'].extend(files)
            elif 'research' in name_lower:
                files = copy_dir(item_path, os.path.join(LIB, '09_Research-Hub', item))
                all_copied['09_Research-Hub'].extend(files)
            elif 'architecture' in name_lower:
                files = copy_dir(item_path, os.path.join(LIB, '05_Runtime', item))
                all_copied['05_Runtime'].extend(files)
            elif 'kos' in name_lower or 'data' in name_lower or 'content' in name_lower:
                files = copy_dir(item_path, os.path.join(LIB, '02_ZBMP研究', item))
                all_copied['02_ZBMP研究'].extend(files)
            else:
                files = copy_dir(item_path, os.path.join(LIB, '09_Research-Hub', 'docs', item))
                all_copied['09_Research-Hub'].extend(files)
        else:
            # single files in docs/
            if 'ui' in name_lower or 'ux' in name_lower:
                f = copy_file(item_path, os.path.join(LIB, '08_UI-UX'))
                if f: all_copied['08_UI-UX'].append(f)
            elif 'audit' in name_lower:
                f = copy_file(item_path, os.path.join(LIB, '10_工程审计方法'))
                if f: all_copied['10_工程审计方法'].append(f)
            elif 'zbc' in name_lower or 'opinion' in name_lower:
                f = copy_file(item_path, os.path.join(LIB, '01_ZBC专项研究'))
                if f: all_copied['01_ZBC专项研究'].append(f)
            else:
                f = copy_file(item_path, os.path.join(LIB, '09_Research-Hub', 'docs'))
                if f: all_copied['09_Research-Hub'].append(f)
    print(f"  docs/ processed")

# evidence/ -> 07_Data-Evidence-Evaluation/证据
src = os.path.join(OSAI, 'evidence')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '07_Data-Evidence-Evaluation', '证据'))
    all_copied['07_Data-Evidence-Evaluation'].extend(files)
    print(f"  evidence -> 07_Data-Evidence-Evaluation: {len(files)} files")

# tests/ -> 07_Data-Evidence-Evaluation/测试证据 (research reference, not runtime)
src = os.path.join(OSAI, 'tests')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '07_Data-Evidence-Evaluation', 'OSAI测试证据'))
    all_copied['07_Data-Evidence-Evaluation'].extend(files)
    print(f"  tests -> 07_Data-Evidence-Evaluation: {len(files)} files")

# skills/ -> 04_OSAI核心技术/Skill体系
src = os.path.join(OSAI, 'skills')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '04_OSAI核心技术', 'Skill体系'))
    all_copied['04_OSAI核心技术'].extend(files)
    print(f"  skills -> 04_OSAI核心技术: {len(files)} files")

# P0-resident-xhs-runtime/ -> 03_CTH研究/XHS运行时
src = os.path.join(OSAI, 'P0-resident-xhs-runtime')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '03_CTH研究', 'XHS运行时'))
    all_copied['03_CTH研究'].extend(files)
    print(f"  P0-resident-xhs-runtime -> 03_CTH研究: {len(files)} files")

# P0-TRINITY/ -> 01_ZBC专项研究
src = os.path.join(OSAI, 'P0-TRINITY')
if os.path.exists(src):
    files = copy_dir(src, os.path.join(LIB, '01_ZBC专项研究', 'P0-TRINITY'))
    all_copied['01_ZBC专项研究'].extend(files)
    print(f"  P0-TRINITY -> 01_ZBC专项研究: {len(files)} files")

# osai_engine/ - copy .md research docs only (NOT .py code - OSAI not runtime dep)
src = os.path.join(OSAI, 'osai_engine')
if os.path.exists(src):
    md_count = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if f.endswith('.md') or f.endswith('.txt') or f.endswith('.json'):
                rel = os.path.relpath(root, src)
                dst = os.path.join(LIB, '04_OSAI核心技术', '引擎研究文档', rel) if rel != '.' else os.path.join(LIB, '04_OSAI核心技术', '引擎研究文档')
                copied = copy_file(os.path.join(root, f), dst)
                if copied:
                    all_copied['04_OSAI核心技术'].append(copied)
                    md_count += 1
    print(f"  osai_engine .md/.json -> 04_OSAI核心技术/引擎研究文档: {md_count} files")

# Root-level key .md files
root_md_map = {
    'README.md': '00_总览',
    'README-main-latest.md': '00_总览',
    'ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1.md': '01_ZBC专项研究',
    'CHANGELOG.md': '10_工程审计方法',
    'DESIGN_PHILOSOPHY_SEED_MUSTERY_TAIJI_V1.md': '08_UI-UX',
    'LOCAL_AI_CONTINUOUS_RUNTIME_P0.md': '05_Runtime',
    'AUDIT_EXECUTION_HANDOFF_20260902.md': '10_工程审计方法',
    'AUDIT_HANDOFF_20260902_UNIFIED_RESOURCE.md': '10_工程审计方法',
    'WORK_LOG_20260902_RESOURCE_EVOLUTION.md': '10_工程审计方法',
    'UI_DELETE_MANIFEST.md': '08_UI-UX',
}
for fname, target in root_md_map.items():
    src = os.path.join(OSAI, fname)
    if os.path.exists(src):
        f = copy_file(src, os.path.join(LIB, target))
        if f: all_copied[target].append(f)
print("  OSAI root-level key files copied")

# components/ - extract ADRH, SICI, DCC research docs
comp = os.path.join(OSAI, 'components')
if os.path.exists(comp):
    for item in os.listdir(comp):
        item_path = os.path.join(comp, item)
        if not os.path.isdir(item_path):
            continue
        name_lower = item.lower()
        if 'ai-development-research' in name_lower or 'adrh' in name_lower:
            # This is embedded ADRH - copy research docs
            for sub in ['research', 'cases', 'docs', 'protocols', 'design-system', 'architecture']:
                sub_path = os.path.join(item_path, sub)
                if os.path.exists(sub_path):
                    if sub == 'cases':
                        files = copy_dir(sub_path, os.path.join(LIB, '07_Data-Evidence-Evaluation', '工程案例', sub))
                        all_copied['07_Data-Evidence-Evaluation'].extend(files)
                    elif sub == 'design-system':
                        files = copy_dir(sub_path, os.path.join(LIB, '08_UI-UX', sub))
                        all_copied['08_UI-UX'].extend(files)
                    else:
                        files = copy_dir(sub_path, os.path.join(LIB, '09_Research-Hub', 'ADRH', sub))
                        all_copied['09_Research-Hub'].extend(files)
            print(f"  components/{item} (ADRH) processed")
        elif 'sici' in name_lower:
            # Embedded SICI - copy docs
            docs_path = os.path.join(item_path, 'docs')
            if os.path.exists(docs_path):
                files = copy_dir(docs_path, os.path.join(LIB, '09_Research-Hub', 'SICI研究'))
                all_copied['09_Research-Hub'].extend(files)
                print(f"  components/{item} (SICI) -> 09_Research-Hub/SICI研究: {len(files)} files")
        elif 'development-command' in name_lower or 'dcc' in name_lower:
            # DCC - copy research docs only
            docs_path = os.path.join(item_path, 'docs')
            if os.path.exists(docs_path):
                files = copy_dir(docs_path, os.path.join(LIB, '09_Research-Hub', 'DCC研究'))
                all_copied['09_Research-Hub'].extend(files)
                print(f"  components/{item} (DCC) -> 09_Research-Hub/DCC研究: {len(files)} files")
        else:
            # Other components - copy .md docs
            for root, dirs, files in os.walk(item_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'node_modules']
                for f in files:
                    if f.endswith('.md'):
                        rel = os.path.relpath(root, item_path)
                        dst = os.path.join(LIB, '09_Research-Hub', 'components', item, rel) if rel != '.' else os.path.join(LIB, '09_Research-Hub', 'components', item)
                        copied = copy_file(os.path.join(root, f), dst)
                        if copied: all_copied['09_Research-Hub'].append(copied)

# ============================================================
# STEP 3: Copy ADRH (D:\AI-Development-Research-Hub)
# ============================================================
print("\n=== STEP 3: Copying ADRH assets ===")
if os.path.exists(ADRH):
    # cases/ -> 07_Data-Evidence-Evaluation/工程案例
    src = os.path.join(ADRH, 'cases')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '07_Data-Evidence-Evaluation', '工程案例'))
        all_copied['07_Data-Evidence-Evaluation'].extend(files)
        print(f"  cases -> 07: {len(files)} files")
    
    # research/ -> 09_Research-Hub/工程研究
    src = os.path.join(ADRH, 'research')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '09_Research-Hub', '工程研究'))
        all_copied['09_Research-Hub'].extend(files)
        print(f"  research -> 09: {len(files)} files")
    
    # data/evidence -> 07_Data-Evidence-Evaluation/证据
    src = os.path.join(ADRH, 'data', 'evidence')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '07_Data-Evidence-Evaluation', 'ADRH证据'))
        all_copied['07_Data-Evidence-Evaluation'].extend(files)
        print(f"  data/evidence -> 07: {len(files)} files")
    
    # data/experiments -> 09_Research-Hub/实验
    src = os.path.join(ADRH, 'data', 'experiments')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '09_Research-Hub', '实验'))
        all_copied['09_Research-Hub'].extend(files)
        print(f"  data/experiments -> 09: {len(files)} files")
    
    # data/shadow -> 09_Research-Hub/影子学习
    src = os.path.join(ADRH, 'data', 'shadow')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '09_Research-Hub', '影子学习'))
        all_copied['09_Research-Hub'].extend(files)
        print(f"  data/shadow -> 09: {len(files)} files")
    
    # data/learning, data/research -> 09
    for sub in ['learning', 'research']:
        src = os.path.join(ADRH, 'data', sub)
        if os.path.exists(src):
            files = copy_dir(src, os.path.join(LIB, '09_Research-Hub', 'data', sub))
            all_copied['09_Research-Hub'].extend(files)
    
    # design-system/ -> 08_UI-UX
    src = os.path.join(ADRH, 'design-system')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '08_UI-UX', 'ADRH设计系统'))
        all_copied['08_UI-UX'].extend(files)
        print(f"  design-system -> 08: {len(files)} files")
    
    # architecture/ -> 05_Runtime
    src = os.path.join(ADRH, 'architecture')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '05_Runtime', 'ADRH架构'))
        all_copied['05_Runtime'].extend(files)
        print(f"  architecture -> 05: {len(files)} files")
    
    # docs/ -> 09 or 10 based on content
    src = os.path.join(ADRH, 'docs')
    if os.path.exists(src):
        for item in os.listdir(src):
            item_path = os.path.join(src, item)
            if os.path.isdir(item_path):
                files = copy_dir(item_path, os.path.join(LIB, '09_Research-Hub', 'ADRH-docs', item))
                all_copied['09_Research-Hub'].extend(files)
            else:
                name_lower = item.lower()
                if 'protocol' in name_lower or 'audit' in name_lower:
                    f = copy_file(item_path, os.path.join(LIB, '10_工程审计方法', 'ADRH'))
                    if f: all_copied['10_工程审计方法'].append(f)
                else:
                    f = copy_file(item_path, os.path.join(LIB, '09_Research-Hub', 'ADRH-docs'))
                    if f: all_copied['09_Research-Hub'].append(f)
    
    # protocols/ -> 10_工程审计方法
    src = os.path.join(ADRH, 'protocols')
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '10_工程审计方法', 'ADRH协议'))
        all_copied['10_工程审计方法'].extend(files)
        print(f"  protocols -> 10: {len(files)} files")
    
    # Root .md files (protocols, registry, baseline) -> 07 or 10
    for f in os.listdir(ADRH):
        if f.endswith('.md'):
            name_lower = f.lower()
            if 'protocol' in name_lower or 'registry' in name_lower or 'baseline' in name_lower or 'schema' in name_lower:
                copied = copy_file(os.path.join(ADRH, f), os.path.join(LIB, '10_工程审计方法', 'ADRH'))
                if copied: all_copied['10_工程审计方法'].append(copied)
            else:
                copied = copy_file(os.path.join(ADRH, f), os.path.join(LIB, '09_Research-Hub', 'ADRH'))
                if copied: all_copied['09_Research-Hub'].append(copied)
    print("  ADRH root files processed")

# ============================================================
# STEP 4: Copy SICI-Core docs
# ============================================================
print("\n=== STEP 4: Copying SICI-Core docs ===")
sici_docs = os.path.join(SICI, 'docs')
if os.path.exists(sici_docs):
    files = copy_dir(sici_docs, os.path.join(LIB, '09_Research-Hub', 'SICI研究'))
    all_copied['09_Research-Hub'].extend(files)
    print(f"  SICI docs -> 09_Research-Hub/SICI研究: {len(files)} files")

# ============================================================
# STEP 5: Copy ZBC internal governance docs
# ============================================================
print("\n=== STEP 5: Copying ZBC governance docs ===")
gov_dirs = ['00-GOVERNANCE', '02-ARCHITECTURE', 'contracts', 'core']
for gd in gov_dirs:
    src = os.path.join(PROJECT, gd)
    if os.path.exists(src):
        files = copy_dir(src, os.path.join(LIB, '10_工程审计方法', '治理架构', gd))
        all_copied['10_工程审计方法'].extend(files)
        print(f"  {gd} -> 10_工程审计方法/治理架构: {len(files)} files")

# ============================================================
# STEP 6: Copy audit/ research docs
# ============================================================
print("\n=== STEP 6: Copying audit/ docs ===")
audit_dir = os.path.join(PROJECT, 'audit')
if os.path.exists(audit_dir):
    for f in os.listdir(audit_dir):
        fpath = os.path.join(audit_dir, f)
        if not os.path.isfile(fpath):
            continue
        name_lower = f.lower()
        # Design docs -> 08_UI-UX
        if 'design_system' in name_lower or 'page_level_design' in name_lower or f == 'ZBC_Design_System_V1.1.html':
            copied = copy_file(fpath, os.path.join(LIB, '08_UI-UX'))
            if copied: all_copied['08_UI-UX'].append(copied)
        # Feature map/gap -> 01_ZBC专项研究
        elif 'feature_map' in name_lower or 'feature_gap' in name_lower:
            copied = copy_file(fpath, os.path.join(LIB, '01_ZBC专项研究'))
            if copied: all_copied['01_ZBC专项研究'].append(copied)
        # Intelligence library architecture -> 00_总览
        elif 'intelligence_library' in name_lower:
            copied = copy_file(fpath, os.path.join(LIB, '00_总览'))
            if copied: all_copied['00_总览'].append(copied)
        # THREE_REPO_FEEDING_RULE -> 00_总览
        elif 'three_repo' in name_lower or 'feeding_rule' in name_lower:
            copied = copy_file(fpath, os.path.join(LIB, '00_总览'))
            if copied: all_copied['00_总览'].append(copied)
        # docx outline -> 00_总览
        elif f.endswith('.docx'):
            copied = copy_file(fpath, os.path.join(LIB, '00_总览'))
            if copied: all_copied['00_总览'].append(copied)
        # Other audit reports -> 10_工程审计方法
        elif f.endswith('.md') or f.endswith('.json'):
            copied = copy_file(fpath, os.path.join(LIB, '10_工程审计方法', 'ZBC审计'))
            if copied: all_copied['10_工程审计方法'].append(copied)
    print("  audit/ files processed")

# ============================================================
# STEP 7: Generate _index.md for each directory
# ============================================================
print("\n=== STEP 7: Generating _index.md ===")
total = 0
for d in DIRS:
    dir_path = os.path.join(LIB, d)
    files = all_copied[d]
    # Also count any files that might have been copied directly
    all_files = []
    for root, dirs, filenames in os.walk(dir_path):
        for f in filenames:
            if f != '_index.md':
                all_files.append(os.path.join(root, f))
    gen_index(dir_path, d, all_files)
    total += len(all_files)
    print(f"  {d}: {len(all_files)} files -> _index.md")

print(f"\n=== TOTAL COPIED: {total} files ===")
print("=== Part 1 COMPLETE ===")
