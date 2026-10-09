"""
广州太古汇官方信息采集器 v1.0
合理合规采集官网公开信息、微博官方账号内容
用于辅助舆情系统，丰富官方动态数据源
"""
import requests
import json
import re
import os
import time
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 官方信息源配置
OFFICIAL_SOURCES = {
    'taikoo_official': {
        'name': '广州太古汇官网',
        'base_url': 'https://www.taikoohui.com',
        'type': 'website',
        'enabled': True,
    },
    'weibo_official': {
        'name': '广州太古汇官方微博',
        'weibo_id': '太古汇TaiKooHui-广州',
        'weibo_uid': '',  # 需通过搜索获取
        'type': 'weibo',
        'enabled': True,
    },
    'wechat_service': {
        'name': '广州太古汇服务号',
        'wechat_id': 'TaikooHui-Guangzhou',
        'type': 'wechat',
        'enabled': False,  # 微信公众号需特殊处理，默认关闭
    },
    'wechat_subscribe': {
        'name': '广州太古汇订阅号',
        'wechat_id': 'TaikooHui-GZ',
        'type': 'wechat',
        'enabled': False,
    },
}


class OfficialInfoScraper:
    """官方信息采集器"""

    def __init__(self, db=None):
        self.db = db
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data_dir.mkdir(exist_ok=True)

    def fetch_taikoo_website(self, max_pages=3):
        """采集广州太古汇官网活动信息（精准版）
        只采集活动页面，移除页脚导航，精准提取活动卡片
        """
        results = []
        # 只采集活动页面，排除首页和购物页（页脚链接多）
        activity_url = 'https://www.taikoohui.com/zh-cn/activity/'

        try:
            print(f'[官网] 采集活动页: {activity_url}')
            resp = self.session.get(activity_url, timeout=15, allow_redirects=True)
            if resp.status_code != 200:
                print(f'[官网] 状态码 {resp.status_code}')
                return results

            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 移除页脚、导航、弹窗等无关区域
            for tag in soup.find_all(['footer', 'nav', 'header']):
                tag.decompose()
            for selector in ['.footer', '.nav', '.header', '.modal', '.popup', '.cookie', '.subscribe']:
                for tag in soup.select(selector):
                    tag.decompose()

            # 过滤关键词：排除页脚、导航等无关内容
            exclude_keywords = ['私隐', '免责', '备案', '政策', '条款', '扫码', '关注', 'copyright',
                              'footer', 'nav', 'header', '订阅', '邮件', '联系我们', '关于我们',
                              '商场开放时间', '停车场', '交通指南', '会员', '积分', '数字化']
            # 活动相关关键词（白名单）
            include_keywords = ['活动', '展览', '快闪', '限时', '节日', '周年', '庆典', '演出',
                              '艺术', '音乐', '市集', '派对', '体验', '首发', '新品', '优惠',
                              '促销', '折扣', '会员日', '主题', '展', '秀', '季', '节']

            # 方法1：提取包含图片和链接的活动卡片
            # 找所有包含img的div/article
            cards = soup.find_all(['div', 'article', 'li'], recursive=True)
            for card in cards:
                try:
                    # 必须包含图片和链接
                    img = card.find('img', src=True)
                    link = card.find('a', href=True)
                    if not img or not link:
                        continue

                    # 提取标题
                    title = ''
                    title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'span', 'div', 'p'],
                                           class_=re.compile(r'(title|name|heading|text|label)', re.I))
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    if not title:
                        # 从链接文本提取
                        title = link.get_text(strip=True)
                    if not title:
                        # 从img alt提取
                        title = img.get('alt', '')

                    if not title or len(title) < 4 or len(title) > 100:
                        continue

                    # 过滤无关内容
                    if any(kw in title for kw in exclude_keywords):
                        continue

                    # 白名单过滤：标题必须包含活动相关关键词，或者链接包含activity
                    href = link['href']
                    has_activity_keyword = any(kw in title for kw in include_keywords)
                    has_activity_link = 'activity' in href.lower() or 'event' in href.lower() or 'promo' in href.lower()
                    if not has_activity_keyword and not has_activity_link:
                        continue

                    # 完整链接
                    if href and not href.startswith('http'):
                        href = 'https://www.taikoohui.com' + href

                    # 图片URL
                    img_src = img.get('src', '')
                    if img_src and not img_src.startswith('http'):
                        img_src = 'https://www.taikoohui.com' + img_src

                    # 描述
                    desc = ''
                    desc_elem = card.find(['p', 'div', 'span'], class_=re.compile(r'(desc|summary|excerpt|content|text|sub)', re.I))
                    if desc_elem:
                        desc = desc_elem.get_text(strip=True)[:200]

                    # 日期
                    date = ''
                    date_elem = card.find(['span', 'time', 'div', 'p'], class_=re.compile(r'(date|time|meta|period|date)', re.I))
                    if date_elem:
                        date = date_elem.get_text(strip=True)

                    # 去重
                    if any(r['url'] == href for r in results):
                        continue

                    results.append({
                        'source': 'taikoo_official',
                        'source_name': '广州太古汇官网',
                        'title': title[:100],
                        'url': href,
                        'publish_date': date,
                        'description': desc,
                        'content': desc,
                        'image': img_src,
                        'category': 'official_activity',
                        'collected_at': datetime.now().isoformat(),
                    })
                except Exception as e:
                    continue

            print(f'[官网] 活动卡片提取: {len(results)} 条')

            # 方法2：如果活动卡片提取不到，从页面所有链接中精准提取活动链接
            if len(results) < 3:
                print('[官网] 活动卡片不足，从链接中补充提取...')
                all_links = soup.find_all('a', href=True)
                for a in all_links:
                    try:
                        text = a.get_text(strip=True)
                        href = a['href']
                        if not text or len(text) < 6 or len(text) > 80:
                            continue
                        if any(kw in text for kw in exclude_keywords):
                            continue
                        # 必须是活动相关链接或包含活动关键词
                        is_activity_link = 'activity' in href.lower() or 'event' in href.lower() or 'promo' in href.lower()
                        has_activity_kw = any(kw in text for kw in include_keywords)
                        if not is_activity_link and not has_activity_kw:
                            continue
                        if any(r['title'] == text for r in results):
                            continue
                        full_link = href if href.startswith('http') else 'https://www.taikoohui.com' + href
                        results.append({
                            'source': 'taikoo_official',
                            'source_name': '广州太古汇官网',
                            'title': text[:100],
                            'url': full_link,
                            'publish_date': '',
                            'description': '',
                            'content': '',
                            'image': '',
                            'category': 'official_activity',
                            'collected_at': datetime.now().isoformat(),
                        })
                    except:
                        continue

            print(f'[官网] 最终提取: {len(results)} 条活动')

        except Exception as e:
            print(f'[官网] 采集失败: {e}')

        return results

    def fetch_weibo_official(self, max_posts=20):
        """采集广州太古汇官方微博内容
        优先使用Playwright登录态采集，备用已知微博ID
        """
        results = []

        # 方式1：尝试通过Playwright采集（复用rednote登录态）
        try:
            print('[微博] 尝试Playwright登录态采集...')
            playwright_results = self._fetch_weibo_via_playwright(max_posts)
            if playwright_results:
                results.extend(playwright_results)
                print(f'[微博] Playwright采集到 {len(results)} 条')
                return results
        except Exception as e:
            print(f'[微博] Playwright采集失败: {e}')

        # 方式2：通过微博搜索API（可能需要登录）
        try:
            print('[微博] 尝试搜索API采集...')
            search_url = 'https://m.weibo.cn/api/container/getIndex'
            params = {
                'containerid': '100103type=1&q=太古汇TaiKooHui-广州',
                'page_type': 'searchall',
            }
            resp = self.session.get(search_url, params=params, timeout=15)
            if resp.status_code == 200 and resp.text.strip().startswith('{'):
                data = resp.json()
                cards = data.get('data', {}).get('cards', [])
                for card in cards[:5]:
                    card_group = card.get('card_group', [])
                    for item in card_group:
                        if item.get('card_type') == 9 and 'user' in item:
                            user = item['user']
                            if '太古汇' in user.get('screen_name', '') or 'taikoo' in user.get('screen_name', '').lower():
                                weibo_uid = user.get('id', '')
                                print(f'[微博] 找到官方账号: {user["screen_name"]} (UID: {weibo_uid})')
                                if weibo_uid:
                                    posts = self._fetch_weibo_user_timeline(weibo_uid, max_posts)
                                    results.extend(posts)
                                break
        except Exception as e:
            print(f'[微博] 搜索API失败: {e}')

        # 方式3：已知微博ID备用
        if not results:
            print('[微博] 使用已知微博ID备用采集...')
            known_weibo_ids = [
                '5333596663453399',  # 七夕花厨
                '5332177308619118',  # 布契拉提
                '5312215777020182',  # 父亲节DAYBYDAY
                '5277426546640341',  # CPB肌肤之钥
                '5250247452002662',  # FILA
            ]
            for wid in known_weibo_ids:
                try:
                    post = self._fetch_weibo_single(wid)
                    if post and post.get('title'):
                        results.append(post)
                except:
                    pass

        return results

    def _fetch_weibo_via_playwright(self, max_posts=20):
        """Fetch public Weibo pages in an anonymous headless context only."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print('[微博] Playwright未安装，跳过')
            return []

        results = []
        browser = None
        context = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled'],
                )
                context = browser.new_context()
                page = context.new_page()
                page.goto('https://weibo.com/u/1878001152', wait_until='domcontentloaded', timeout=30000)
                page.wait_for_timeout(3000)

                posts = page.query_selector_all('article[class*="Feed_body"]')
                if not posts:
                    posts = page.query_selector_all('div[class*="card-wrap"]')

                for post in posts[:max_posts]:
                    try:
                        text_elem = post.query_selector('div[class*="txt"]')
                        body = text_elem.inner_text() if text_elem else ''
                        if not body or len(body) < 10:
                            continue
                        link_elem = post.query_selector('a[href*="/detail/"]')
                        link = link_elem.get_attribute('href') if link_elem else ''
                        if link and not link.startswith('http'):
                            link = 'https://weibo.com' + link
                        time_elem = post.query_selector('a[class*="time"]')
                        publish_date = time_elem.inner_text() if time_elem else ''
                        results.append({
                            'source': 'weibo_official',
                            'source_name': '广州太古汇官方微博',
                            'title': body[:100],
                            'url': link,
                            'publish_date': publish_date,
                            'description': body[:300],
                            'content': body,
                            'category': 'official_weibo',
                            'collected_at': datetime.now().isoformat(),
                        })
                    except Exception:
                        continue
                print(f'[微博] Playwright采集到 {len(results)} 条')
        except Exception as e:
            print(f'[微博] Playwright采集异常: {e}')
        finally:
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass
            try:
                if browser is not None:
                    browser.close()
            except Exception:
                pass
        return results

    def _fetch_weibo_user_timeline(self, uid, max_posts=20):
        """获取微博用户时间线"""
        results = []
        url = 'https://m.weibo.cn/api/container/getIndex'
        params = {
            'type': 'uid',
            'value': uid,
            'containerid': f'107603{uid}',
        }

        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                cards = data.get('data', {}).get('cards', [])
                for card in cards[:max_posts]:
                    if card.get('card_type') == 9:
                        mblog = card.get('mblog', {})
                        results.append({
                            'source': 'weibo_official',
                            'source_name': '广州太古汇官方微博',
                            'title': mblog.get('text', '')[:100],
                            'url': f'https://m.weibo.cn/detail/{mblog.get("id", "")}',
                            'publish_date': mblog.get('created_at', ''),
                            'description': mblog.get('text', '')[:300],
                            'content': mblog.get('text', ''),
                            'category': 'official_weibo',
                            'likes': mblog.get('attitudes_count', 0),
                            'comments': mblog.get('comments_count', 0),
                            'reposts': mblog.get('reposts_count', 0),
                            'collected_at': datetime.now().isoformat(),
                        })
                print(f'[微博] 采集到 {len(results)} 条微博')
        except Exception as e:
            print(f'[微博] 时间线采集失败: {e}')

        return results

    def _fetch_weibo_single(self, weibo_id):
        """获取单条微博详情"""
        url = f'https://m.weibo.cn/detail/{weibo_id}'
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                # 从页面提取微博内容
                match = re.search(r'"text":"(.*?)"', resp.text)
                text = match.group(1) if match else ''
                text = re.sub(r'<[^>]+>', '', text)
                return {
                    'source': 'weibo_official',
                    'source_name': '广州太古汇官方微博',
                    'title': text[:100],
                    'url': url,
                    'publish_date': '',
                    'description': text[:300],
                    'content': text,
                    'category': 'official_weibo',
                    'collected_at': datetime.now().isoformat(),
                }
        except Exception as e:
            print(f'[微博] 单条采集失败 {weibo_id}: {e}')
        return None

    def fetch_brand_websites(self, max_brands=20):
        """场内品牌官网批量采集（底层库版）
        直接从 data/brand_websites.json 读取品牌官网URL，合规采集品牌信息
        不用每次爬取太古汇官网表格，简单明了
        """
        results = []
        brand_websites_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'brand_websites.json')

        # 加载品牌官网URL库（底层逻辑用，不在前端展示）
        brand_websites = {}
        if os.path.exists(brand_websites_file):
            try:
                with open(brand_websites_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    brand_websites = data.get('brands', {})
                print(f'[品牌官网] 加载底层URL库，共{len(brand_websites)}个品牌')
            except Exception as e:
                print(f'[品牌官网] 加载URL库失败: {e}')

        if not brand_websites:
            print('[品牌官网] URL库为空')
            return results

        # 直接从URL库采集品牌信息
        collected = 0
        for brand_name, info in list(brand_websites.items())[:max_brands]:
            if collected >= max_brands:
                break
            try:
                website = info.get('website', '')
                brand_cn = info.get('brand_cn', brand_name)
                category = info.get('category', '')

                if not website:
                    continue

                print(f'[品牌官网] 采集: {brand_cn} ({website[:50]})')

                # 采集品牌官网首页信息
                try:
                    resp = self.session.get(website, timeout=10, allow_redirects=True)
                    if resp.status_code == 200:
                        resp.encoding = 'utf-8'
                        soup = BeautifulSoup(resp.text, 'html.parser')

                        # 提取页面标题
                        title = ''
                        title_elem = soup.find('title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)

                        # 提取meta描述
                        desc = ''
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc:
                            desc = meta_desc.get('content', '')[:300]
                        if not desc:
                            meta_og = soup.find('meta', attrs={'property': 'og:description'})
                            if meta_og:
                                desc = meta_og.get('content', '')[:300]

                        results.append({
                            'source': 'brand_official',
                            'source_name': f'{brand_cn}官网',
                            'title': title or brand_cn,
                            'url': website,
                            'brand_name': brand_cn,
                            'brand_category': category,
                            'official_site': website,
                            'description': desc,
                            'content': desc,
                            'category': 'brand_info',
                            'collected_at': datetime.now().isoformat(),
                        })
                        collected += 1
                        print(f'[品牌官网]   成功: {brand_cn}')
                except Exception as e:
                    print(f'[品牌官网]   采集失败 {brand_cn}: {e}')
                    # 即使采集失败，也记录品牌基本信息
                    results.append({
                        'source': 'brand_official',
                        'source_name': f'{brand_cn}官网',
                        'title': brand_cn,
                        'url': website,
                        'brand_name': brand_cn,
                        'brand_category': category,
                        'official_site': website,
                        'description': '',
                        'content': '',
                        'category': 'brand_info',
                        'collected_at': datetime.now().isoformat(),
                    })
                    collected += 1

                time.sleep(0.3)  # 礼貌延迟
            except Exception as e:
                print(f'[品牌官网] 处理失败 {brand_name}: {e}')
                continue

        print(f'[品牌官网] 采集完成: {len(results)}个品牌信息')
        return results

    def collect_all(self, sources=None):
        """采集所有启用的官方信息源"""
        if sources is None:
            sources = [k for k, v in OFFICIAL_SOURCES.items() if v.get('enabled')]

        all_results = []
        for source_key in sources:
            config = OFFICIAL_SOURCES.get(source_key, {})
            if not config.get('enabled'):
                continue

            print(f'\n=== 采集: {config["name"]} ===')
            try:
                if source_key == 'taikoo_official':
                    results = self.fetch_taikoo_website()
                elif source_key == 'weibo_official':
                    results = self.fetch_weibo_official()
                elif source_key == 'brand_official':
                    results = self.fetch_brand_websites(max_brands=10)
                else:
                    results = []
                all_results.extend(results)
                print(f'=== {config["name"]} 采集完成: {len(results)} 条 ===')
            except Exception as e:
                print(f'=== {config["name"]} 采集失败: {e} ===')

        # 保存到文件
        output_file = self.data_dir / 'official_info.json'
        existing = []
        if output_file.exists():
            try:
                existing = json.loads(output_file.read_text(encoding='utf-8'))
            except:
                existing = []

        # 去重
        existing_urls = {item.get('url', '') for item in existing if item.get('url')}
        new_items = [item for item in all_results if item.get('url', '') not in existing_urls]
        existing.extend(new_items)

        output_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'\n=== 官方信息采集完成 ===')
        print(f'新增: {len(new_items)} 条')
        print(f'总计: {len(existing)} 条')
        print(f'保存至: {output_file}')

        return all_results


def run_collection():
    """运行官方信息采集"""
    scraper = OfficialInfoScraper()
    results = scraper.collect_all()
    return results


if __name__ == '__main__':
    run_collection()
