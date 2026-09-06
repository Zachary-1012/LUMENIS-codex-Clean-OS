#!/usr/bin/env python3
"""P1-C Part 2: Generate ASSETS_INDEX.json + create intelligence_assets table + import data"""
import os, json, sqlite3, re
from datetime import datetime

PROJECT = r'D:\Taikoo-monitor-new'
LIB = os.path.join(PROJECT, 'intelligence_library')
DB_PATH = os.path.join(PROJECT, 'data', 'monitor.db')

# 13 sub-library names
SUB_LIBS = [
    '00_总览', '01_ZBC专项研究', '02_ZBMP研究', '03_CTH研究',
    '04_OSAI核心技术', '05_Runtime', '06_Security', '07_Data-Evidence-Evaluation',
    '08_UI-UX', '09_Research-Hub', '10_工程审计方法', '11_前沿研究',
    '12_研究到ZBC落地索引',
]

def infer_source_origin(rel_path, sub_lib):
    """Infer source origin from path"""
    p = rel_path.lower()
    if '治理架构' in rel_path or sub_lib == '10_工程审计方法' and ('治理' in rel_path or 'ZBC审计' in rel_path):
        return 'ZBC-internal'
    if 'adrh' in p or 'ai-development-research' in p or '工程研究' in rel_path or '工程案例' in rel_path:
        return 'ADRH'
    if 'sici' in p:
        return 'SICI'
    if 'dcc' in p or 'development-command' in p:
        return 'DCC'
    if 'zbc审计' in p or '治理架构' in p:
        return 'Governance'
    # Default: OSAI for most content in research/osai/core dirs
    if sub_lib in ['04_OSAI核心技术', '05_Runtime', '11_前沿研究']:
        return 'OSAI'
    if any(k in p for k in ['osai', '序境', 'learning-feed', 'research-inbox', 'ai-os-research', 'baseline', 'reconciliation', '工程矩阵', '合约', '对账', '证据', '测试证据', 'skill体系', '引擎研究']):
        return 'OSAI'
    return 'OSAI'

def infer_product(rel_path, sub_lib, filename):
    """Infer product: ZBC / GGI / SHARED"""
    p = (rel_path + filename).lower()
    # GGI-specific
    if any(k in p for k in ['ggi', 'global-growth', 'global_growth', '全球增长']):
        return 'GGI'
    # ZBC-specific
    if any(k in p for k in ['zbc', '序境', 'zbmp', 'cth', '太古汇', '舆情', 'xhs', '小红书', 'kos', '品牌营销', '播客', '双域', 'dual_domain', 'dual-domain']):
        return 'ZBC'
    if sub_lib in ['01_ZBC专项研究', '02_ZBMP研究', '03_CTH研究']:
        return 'ZBC'
    if sub_lib == '08_UI-UX' and any(k in p for k in ['zbc', 'design_system', 'page_level']):
        return 'ZBC'
    if sub_lib == '10_工程审计方法' and ('治理架构' in rel_path or 'ZBC审计' in rel_path):
        return 'ZBC'
    # Default SHARED for OSAI core, research hub, runtime, security, data-evidence
    return 'SHARED'

def infer_domain(rel_path, sub_lib, filename):
    """Infer ZBC internal domain: ZBMP / CTH / SYSTEM / SHARED"""
    p = (rel_path + filename).lower()
    if sub_lib == '02_ZBMP研究' or any(k in p for k in ['zbmp', '品牌', 'brand', 'marketing', 'kos', 'kol', 'koc', '播客', 'podcast', '创意', 'creative']):
        return 'ZBMP'
    if sub_lib == '03_CTH研究' or any(k in p for k in ['cth', '太古汇', '舆情', 'opinion', 'poms', 'xhs', '小红书', 'topic', '话题', '事件', 'event']):
        return 'CTH'
    if sub_lib in ['05_Runtime', '06_Security'] or any(k in p for k in ['runtime', 'security', 'permission', 'identity', 'guardian', 'preflight', '系统', 'system']):
        return 'SYSTEM'
    return 'SHARED'

def infer_evidence_level(rel_path, sub_lib, filename):
    """Infer evidence level E0-E4"""
    p = (rel_path + filename).lower()
    # E4: tested/audited/verified
    if any(k in p for k in ['audit', '验证', 'verified', 'test', '测试证据', '对账', 'reconciliation', '矩阵', 'matrix', 'baseline', '基线']):
        return 'E4'
    # E3: authoritative original research
    if sub_lib in ['04_OSAI核心技术', '09_Research-Hub', '11_前沿研究']:
        return 'E3'
    if any(k in p for k in ['research', '研究', '合约', 'contract', 'governance', '治理']):
        return 'E3'
    # E2: multi-source consistent
    if any(k in p for k in ['case', '案例', 'evidence', '证据']):
        return 'E2'
    # Default E3 for research documents
    return 'E3'

def infer_knowledge_status(rel_path, sub_lib, filename):
    """Infer knowledge status"""
    p = (rel_path + filename).lower()
    if any(k in p for k in ['audit', '验证', 'verified', 'test', '对账', 'reconciliation', '矩阵', 'baseline', '基线', 'registry', '注册']):
        return 'VERIFIED'
    if any(k in p for k in ['contract', '合约', 'governance', '治理', 'rule', '规则', 'policy', '策略']):
        return 'FACT'
    if any(k in p for k in ['proposal', '建议', 'recommendation', 'roadmap', '路线图', 'plan', '计划']):
        return 'RECOMMENDATION'
    if any(k in p for k in ['concept', '概念', 'philosophy', '哲学', 'vision', '愿景', '2030', '前沿', 'frontier']):
        return 'CONCEPT'
    if any(k in p for k in ['research', '研究', 'exploration', '探索', 'inbox', '收件箱']):
        return 'PENDING'
    if any(k in p for k in ['legacy', 'archive', '归档', 'old', '历史']):
        return 'LEGACY'
    return 'PENDING'

def infer_landing_status(rel_path, sub_lib, filename):
    """Infer five-state landing status"""
    p = (rel_path + filename).lower()
    # 已落地: already in production
    if any(k in p for k in ['design_system', 'design-system', 'page_level', '双域', 'dual_domain', 'risk_engine', '风险引擎', '治理架构']):
        return '已落地'
    # 已实现待验证
    if any(k in p for k in ['audit', '验证', 'verified', 'test', '对账', 'preflight', 'guardian']):
        return '已实现待验证'
    # 可直接复用
    if any(k in p for k in ['case', '案例', 'template', '模板', '话术', 'contract', '合约', 'protocol', '协议']):
        return '可直接复用'
    # 建议转化
    if sub_lib in ['04_OSAI核心技术', '05_Runtime', '06_Security', '09_Research-Hub', '11_前沿研究']:
        if any(k in p for k in ['research', '研究', '架构', 'architecture', 'runtime', 'security', 'permission', 'agent', 'skill', 'browser', 'ai']):
            return '建议转化'
    # 仅研究不应转化
    if any(k in p for k in ['philosophy', '哲学', 'vision', '愿景', '2030', 'naming', '命名', 'paper', '论文', 'radar', '雷达', '前沿', 'frontier', 'concept']):
        return '仅研究不应转化'
    if sub_lib == '11_前沿研究':
        return '仅研究不应转化'
    # Default
    return '建议转化'

def infer_tags(rel_path, sub_lib, filename):
    """Infer tags from path and filename"""
    tags = []
    p = (rel_path + filename).lower()
    tag_map = {
        'zbc': 'ZBC', '序境': 'ZBC', 'zbmp': 'ZBMP', 'cth': 'CTH',
        '太古汇': 'CTH', '舆情': '舆情', 'xhs': 'XHS', '小红书': 'XHS',
        'kos': 'KOS', 'kol': 'KOL', 'koc': 'KOC', 'brand': '品牌',
        '品牌': '品牌', 'marketing': '营销', 'runtime': 'Runtime',
        'security': '安全', '安全': '安全', 'permission': '权限',
        'agent': 'Agent', 'skill': 'Skill', 'ai': 'AI',
        'browser': '浏览器', 'evidence': '证据', '证据': '证据',
        'evaluation': '评估', 'audit': '审计', '审计': '审计',
        'research': '研究', '研究': '研究', 'ui': 'UI/UX',
        'ux': 'UI/UX', 'design': '设计', '设计': '设计',
        'contract': '合约', '合约': '合约', 'governance': '治理',
        '治理': '治理', 'architecture': '架构', '架构': '架构',
        'learning': '学习', '学习': '学习', 'memory': '记忆',
        'osai': 'OSAI', 'sici': 'SICI', 'adrh': 'ADRH',
        'dcc': 'DCC', 'podcast': '播客', '播客': '播客',
        'topic': '话题监控', 'risk': '风险', '风险': '风险',
        'dual': '双域', '双域': '双域', 'cookie': 'Cookie',
        'collector': '采集', '采集': '采集', 'report': '报告',
        '报告': '报告', 'case': '案例', '案例': '案例',
        'shadow': '影子学习', 'frontier': '前沿', '前沿': '前沿',
        'identity': '身份', 'delegation': '委托', 'firewall': '防火墙',
        'gateway': '网关', 'llm': 'LLM', 'model': '模型',
        'test': '测试', '测试': '测试', 'verification': '验证',
        '验证': '验证', 'reconciliation': '对账', 'baseline': '基线',
        '矩阵': '工程矩阵', 'registry': '注册表', 'protocol': '协议',
        '协议': '协议', 'policy': '策略', '策略': '策略',
    }
    for key, tag in tag_map.items():
        if key in p and tag not in tags:
            tags.append(tag)
    if not tags:
        tags.append(sub_lib.split('_', 1)[-1] if '_' in sub_lib else sub_lib)
    return tags[:8]  # limit to 8 tags

def infer_summary(filename, rel_path, sub_lib):
    """Generate one-line summary from filename"""
    name = os.path.splitext(filename)[0]
    # Clean up filename
    name = re.sub(r'[_\-]+', ' ', name)
    name = re.sub(r'\d{4,}', '', name)  # remove long numbers
    name = name.strip()
    if len(name) > 80:
        name = name[:77] + '...'
    source = infer_source_origin(rel_path, sub_lib)
    return f'[{source}] {name}'

def scan_library():
    """Scan all files in intelligence_library and generate metadata"""
    assets = []
    asset_counter = 1
    
    for sub_lib in SUB_LIBS:
        dir_path = os.path.join(LIB, sub_lib)
        if not os.path.exists(dir_path):
            continue
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in sorted(files):
                if f == '_index.md':
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, LIB)
                lib_rel = os.path.relpath(full_path, dir_path)
                
                asset_id = f'AST-{asset_counter:04d}'
                asset_counter += 1
                
                product = infer_product(rel_path, sub_lib, f)
                domain = infer_domain(rel_path, sub_lib, f) if product == 'ZBC' else ''
                
                asset = {
                    'asset_id': asset_id,
                    'title': os.path.splitext(f)[0],
                    'sub_library': sub_lib,
                    'source_origin': infer_source_origin(rel_path, sub_lib),
                    'source_path': '',  # will be inferred
                    'library_path': rel_path.replace('\\', '/'),
                    'product': product,
                    'domain': domain,
                    'evidence_level': infer_evidence_level(rel_path, sub_lib, f),
                    'knowledge_status': infer_knowledge_status(rel_path, sub_lib, f),
                    'tags': infer_tags(rel_path, sub_lib, f),
                    'summary': infer_summary(f, rel_path, sub_lib),
                    'landing_status': infer_landing_status(rel_path, sub_lib, f),
                    'admission_status': 'CANDIDATE',  # default for research assets
                    'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                    'updated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                }
                assets.append(asset)
    
    return assets

def write_assets_index(assets):
    """Write ASSETS_INDEX.json"""
    idx_path = os.path.join(LIB, '00_总览', 'ASSETS_INDEX.json')
    data = {
        'metadata': {
            'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'total_assets': len(assets),
            'version': '1.0',
            'description': 'ZBC/LUMENIS Unified Intelligence Library - Asset Index',
            'product_fields': 'product (ZBC/GGI/SHARED) + domain (ZBMP/CTH/SYSTEM/SHARED for ZBC only)',
            'osai_boundary': 'OSAI=Intelligence Core, NOT a ZBC runtime dependency. Admission chain required.',
        },
        'assets': assets,
    }
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"ASSETS_INDEX.json written: {len(assets)} assets -> {idx_path}")
    return idx_path

def create_db_table():
    """Create intelligence_assets table (idempotent)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing tables count
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Existing tables: {len(tables)}")
    
    # Create intelligence_assets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intelligence_assets (
            asset_id TEXT PRIMARY KEY,
            title TEXT,
            sub_library TEXT,
            source_origin TEXT,
            source_path TEXT,
            library_path TEXT,
            product TEXT,
            domain TEXT,
            evidence_level TEXT,
            knowledge_status TEXT,
            tags TEXT,
            summary TEXT,
            landing_status TEXT,
            admission_status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    
    # Verify table created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='intelligence_assets'")
    result = cursor.fetchone()
    print(f"intelligence_assets table created: {result is not None}")
    
    # Count tables after
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_after = cursor.fetchall()
    print(f"Tables after migration: {len(tables_after)}")
    
    conn.close()
    return len(tables_after)

def import_to_db(assets):
    """Import assets into intelligence_assets table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data (idempotent)
    cursor.execute("DELETE FROM intelligence_assets")
    
    inserted = 0
    for a in assets:
        cursor.execute('''
            INSERT OR REPLACE INTO intelligence_assets 
            (asset_id, title, sub_library, source_origin, source_path, library_path,
             product, domain, evidence_level, knowledge_status, tags, summary,
             landing_status, admission_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            a['asset_id'], a['title'], a['sub_library'], a['source_origin'],
            a['source_path'], a['library_path'], a['product'], a['domain'],
            a['evidence_level'], a['knowledge_status'],
            json.dumps(a['tags'], ensure_ascii=False), a['summary'],
            a['landing_status'], a['admission_status'],
            a['created_at'], a['updated_at'],
        ))
        inserted += 1
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM intelligence_assets")
    count = cursor.fetchone()[0]
    print(f"Imported {inserted} assets, DB count: {count}")
    
    # Print stats
    print("\n=== Product distribution ===")
    cursor.execute("SELECT product, COUNT(*) FROM intelligence_assets GROUP BY product")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\n=== Sub-library distribution ===")
    cursor.execute("SELECT sub_library, COUNT(*) FROM intelligence_assets GROUP BY sub_library ORDER BY sub_library")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\n=== Landing status distribution ===")
    cursor.execute("SELECT landing_status, COUNT(*) FROM intelligence_assets GROUP BY landing_status")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\n=== Evidence level distribution ===")
    cursor.execute("SELECT evidence_level, COUNT(*) FROM intelligence_assets GROUP BY evidence_level")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()
    return count

def write_migration_script():
    """Write a standalone migration script for record"""
    mig_path = os.path.join(PROJECT, 'migrations', 'create_intelligence_assets_table.py')
    os.makedirs(os.path.dirname(mig_path), exist_ok=True)
    content = '''#!/usr/bin/env python3
"""Migration: Create intelligence_assets table for Unified Intelligence Library.
Idempotent - safe to run multiple times.
Does NOT modify or drop any existing tables.
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'monitor.db')

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_assets (
            asset_id TEXT PRIMARY KEY,
            title TEXT,
            sub_library TEXT,
            source_origin TEXT,
            source_path TEXT,
            library_path TEXT,
            product TEXT,
            domain TEXT,
            evidence_level TEXT,
            knowledge_status TEXT,
            tags TEXT,
            summary TEXT,
            landing_status TEXT,
            admission_status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM intelligence_assets")
    print(f"intelligence_assets table ready. Current records: {cursor.fetchone()[0]}")
    conn.close()

if __name__ == '__main__':
    upgrade()
'''
    with open(mig_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Migration script written: {mig_path}")

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=== P1-C Part 2: Metadata Index + DB Table ===")
    
    # Step 1: Scan library
    print("\n--- Scanning intelligence_library ---")
    assets = scan_library()
    print(f"Total assets scanned: {len(assets)}")
    
    # Step 2: Write ASSETS_INDEX.json
    print("\n--- Writing ASSETS_INDEX.json ---")
    write_assets_index(assets)
    
    # Step 3: Write migration script
    print("\n--- Writing migration script ---")
    write_migration_script()
    
    # Step 4: Create DB table
    print("\n--- Creating intelligence_assets table ---")
    tables_after = create_db_table()
    
    # Step 5: Import data
    print("\n--- Importing assets to DB ---")
    count = import_to_db(assets)
    
    print(f"\n=== Part 2 COMPLETE: {count} assets in DB, {tables_after} total tables ===")
