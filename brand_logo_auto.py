"""
ZBC 品牌Logo自动发现系统 v2.0
研究来源：OpenBrand Asset Extraction、Brand Logo Fetcher
核心逻辑：品牌名 → 域名推断/搜索 → favicon/OG图片/logo提取 → 缓存
新增品牌时系统自动搜集logo，无需手动维护映射。
"""
import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

try:
    import urllib.request
    import urllib.error
except:
    pass

LOGO_CACHE_DIR = Path(__file__).parent / 'data' / 'brand_logos'
LOGO_META_FILE = Path(__file__).parent / 'data' / 'brand_logo_meta.json'

# 常见品牌域名后缀（用于自动推断）
COMMON_TLDS = ['.com', '.cn', '.com.cn', '.co', '.io', '.net', '.org']

# 品牌名→域名常见转换规则
def _brand_to_domain_candidates(brand_en):
    """从品牌英文名生成可能的域名候选。"""
    name = brand_en.strip().lower()
    # 移除特殊字符
    clean = re.sub(r'[^a-z0-9]', '', name)
    # 移除常见后缀词
    clean = re.sub(r'(store|shop|official|boutique|guangzhou|taikoo|hui)$', '', clean)

    candidates = []
    # 直接品牌名
    candidates.append(clean)
    # 品牌名+brand
    candidates.append(clean + 'brand')
    # 品牌名+official
    candidates.append(clean + 'official')
    # 品牌名+cn（中国官网）
    candidates.append(clean + 'cn')
    # 品牌名.com.cn
    candidates.append(clean + '.com.cn')

    # 处理带空格的品牌名（如TOM FORD → tomford, tom-ford）
    if ' ' in name:
        no_space = name.replace(' ', '')
        candidates.append(no_space)
        candidates.append(no_space + 'cn')
        with_dash = name.replace(' ', '-')
        candidates.append(with_dash)

    # 去重
    seen = set()
    unique = []
    for c in candidates:
        if c and c not in seen and len(c) >= 2:
            seen.add(c)
            unique.append(c)
    return unique[:8]  # 最多8个候选


def _try_fetch_favicon(domain, size=128):
    """尝试获取域名favicon。"""
    # 使用Google favicon服务（稳定、高清、无需key）
    url = f'https://www.google.com/s2/favicons?domain={domain}&sz={size}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=8)
        data = resp.read()
        if len(data) > 100:  # 有效图片至少100字节
            return url, data
    except:
        pass
    return None, None


def _discover_domain_for_brand(brand_en):
    """为品牌发现可用域名。"""
    candidates = _brand_to_domain_candidates(brand_en)

    for name in candidates:
        for tld in COMMON_TLDS:
            if name.endswith(tld):
                domain = name
            else:
                domain = name + tld
            # 快速检测域名是否存在（通过favicon服务）
            try:
                url, data = _try_fetch_favicon(domain)
                if data and len(data) > 200:  # 有实质内容
                    return domain, url
            except:
                continue
    return None, None


def auto_discover_logo(brand_en, brand_cn=''):
    """
    自动发现品牌logo。
    流程：品牌名 → 域名候选 → favicon获取 → 缓存
    返回：(logo_url, domain, source)
    """
    # 1. 先查缓存
    meta = _load_meta()
    cache_key = brand_en.upper()
    if cache_key in meta and meta[cache_key].get('logo_url'):
        cached = meta[cache_key]
        # 缓存有效期30天
        if (datetime.now() - datetime.fromisoformat(cached.get('discovered_at', '2020-01-01'))).days < 30:
            return cached['logo_url'], cached.get('domain'), 'cache'

    # 2. 自动发现域名
    domain, favicon_url = _discover_domain_for_brand(brand_en)

    if domain and favicon_url:
        # 3. 缓存logo元数据
        meta[cache_key] = {
            'brand_en': brand_en,
            'brand_cn': brand_cn,
            'domain': domain,
            'logo_url': favicon_url,
            'source': 'auto_discover',
            'discovered_at': datetime.now().isoformat(),
            'confidence': 'medium'
        }
        _save_meta(meta)
        return favicon_url, domain, 'auto_discover'

    # 4. 发现失败，记录为unknown
    meta[cache_key] = {
        'brand_en': brand_en,
        'brand_cn': brand_cn,
        'domain': None,
        'logo_url': None,
        'source': 'not_found',
        'discovered_at': datetime.now().isoformat(),
        'confidence': 'none'
    }
    _save_meta(meta)
    return None, None, 'not_found'


def _load_meta():
    if LOGO_META_FILE.exists():
        try:
            return json.loads(LOGO_META_FILE.read_text(encoding='utf-8'))
        except:
            pass
    return {}


def _save_meta(meta):
    os.makedirs(LOGO_META_FILE.parent, exist_ok=True)
    LOGO_META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


def batch_discover_logos(brands, progress_callback=None):
    """批量发现品牌logo。"""
    results = []
    total = len(brands)
    for i, brand in enumerate(brands):
        brand_en = brand.get('brand_en', '')
        brand_cn = brand.get('brand_cn', '')
        if not brand_en:
            continue
        logo_url, domain, source = auto_discover_logo(brand_en, brand_cn)
        results.append({
            'brand_en': brand_en,
            'brand_cn': brand_cn,
            'logo_url': logo_url,
            'domain': domain,
            'source': source
        })
        if progress_callback:
            progress_callback(i + 1, total, brand_en, source)
    return results


def get_logo_for_brand(brand_en):
    """获取品牌logo（优先缓存，否则自动发现）。"""
    meta = _load_meta()
    cache_key = brand_en.upper()
    if cache_key in meta and meta[cache_key].get('logo_url'):
        return meta[cache_key]['logo_url']
    # 自动发现
    logo_url, _, _ = auto_discover_logo(brand_en)
    return logo_url


def get_discovery_stats():
    """获取logo发现统计。"""
    meta = _load_meta()
    total = len(meta)
    found = sum(1 for v in meta.values() if v.get('logo_url'))
    not_found = total - found
    auto = sum(1 for v in meta.values() if v.get('source') == 'auto_discover')
    return {
        'total': total,
        'found': found,
        'not_found': not_found,
        'auto_discovered': auto,
        'coverage': round(found / total * 100, 1) if total else 0
    }
