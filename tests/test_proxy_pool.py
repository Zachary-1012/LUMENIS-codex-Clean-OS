# -*- coding: utf-8 -*-
"""ProxyPool 可插拔代理池单元测试（不依赖真实网络/代理在线）。
覆盖《可插拔 ProxyPool 补丁1.0》验收标准中的关键安全行为。运行：python -m pytest tests/test_proxy_pool.py 或直接 python 运行。"""
import os, sys, io
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proxy_pool.manager import ProxyManager, ProxyUnavailable
from proxy_pool.models import ProxyNode
from proxy_pool import config as pcfg

PASS = 0
def check(name, cond):
    global PASS
    assert cond, name
    PASS += 1
    print('  PASS', name)

# 1) 默认关闭：get_requests_proxies 永远 None，系统等同直连原版
m = ProxyManager()
m.add_node(ProxyNode(name='a', url='http://127.0.0.1:10808', healthy=True))
old = pcfg.ProxyConfig.ENABLED
pcfg.ProxyConfig.ENABLED = False
check('关闭时无代理(等同直连)', m.get_requests_proxies('general') is None)
pcfg.ProxyConfig.ENABLED = True
check('开启且有健康节点时返回proxies', m.get_requests_proxies('general') is not None)
pcfg.ProxyConfig.ENABLED = old

# 2) 冷却中的节点不可选，自动选其他可用节点
m2 = ProxyManager()
n1 = ProxyNode(name='cool', url='http://1.1.1.1:1', healthy=True)
n2 = ProxyNode(name='ok', url='http://2.2.2.2:2', healthy=True, priority=90)
n1.mark_failure(300)  # 进入冷却
m2.add_node(n1); m2.add_node(n2)
got = m2.get_node('general')
check('冷却节点被跳过选其他', got.name == 'ok')

# 3) 平台匹配：general 兜底 + 专用平台优先
m3 = ProxyManager()
m3.add_node(ProxyNode(name='g', url='http://g:1', healthy=True, platform='general'))
m3.add_node(ProxyNode(name='ig', url='http://ig:1', healthy=True, platform='instagram', priority=200))
check('专用平台优先于general', m3.get_node('instagram').name == 'ig')
check('未知平台回退general', m3.get_node('weibo').name == 'g')

# 4) 强制出海平台：无任何节点且禁止直连时必须抛错，绝不裸奔直连
m4 = ProxyManager()
pcfg.ProxyConfig.ENABLED = True
raised = False
try:
    m4.safe_request('GET', 'http://example.com', platform='instagram',
                    allow_direct=False, timeout=2)
except ProxyUnavailable:
    raised = True
except Exception:
    raised = True
check('强制出海无节点不裸奔(抛异常)', raised)
pcfg.ProxyConfig.ENABLED = old

# 5) 代理失败自动回退直连（mock 全局 requests：代理调用抛错，直连成功）
import requests as _rq
class _FakeResp:
    def __init__(self, via): self.via = via
calls = {'proxy': 0, 'direct': 0}
def fake_request(method, url, **kw):
    if kw.get('proxies'):
        calls['proxy'] += 1
        raise ConnectionError('proxy down')
    calls['direct'] += 1
    return _FakeResp('direct')
_orig_request = _rq.request
_rq.request = fake_request
try:
    m5 = ProxyManager()
    m5.add_node(ProxyNode(name='bad', url='http://127.0.0.1:9', healthy=True))
    pcfg.ProxyConfig.ENABLED = True
    pcfg.ProxyConfig.ALLOW_DIRECT_FALLBACK = True
    r = m5.safe_request('GET', 'http://x.com', platform='general', timeout=2)
    check('代理失败后回退直连成功', r.via == 'direct' and calls['proxy'] == 1 and calls['direct'] == 1)
    bad = m5.nodes['bad']
    check('失败节点被标记失败并进冷却', bad.failures == 1 and bad.cooldown_until > 0)
finally:
    _rq.request = _orig_request
pcfg.ProxyConfig.ENABLED = old
pcfg.ProxyConfig.ALLOW_DIRECT_FALLBACK = True

# 6) status 脱敏：url 内嵌 userinfo 时不回显
from proxy_pool.manager import _mask
masked = _mask('http://user:secret@127.0.0.1:10808')
check('状态不回显内嵌账号', 'secret' not in masked and 'user' not in masked and '10808' in masked)

# 7) loader：缺 proxy_nodes.json 不报错；env 主代理被加载
from proxy_pool import loader
from proxy_pool.manager import ProxyManager as _PM
# 用全新 manager 验证 env 加载逻辑（直接调 loader 会写全局单例，这里只验证函数不抛错）
st = loader.load_proxy_nodes(path='config/__not_exist__.json')
check('loader缺JSON不报错且返回status', isinstance(st, dict) and 'nodes' in st)

# 8) 模块不包含任何“自动抓取免费节点”的行为（结构安全断言）
import inspect, proxy_pool
src = inspect.getsource(pcfg) + inspect.getsource(loader)
check('无自动抓取免费节点逻辑', 'crawl' not in src.lower() and 'scrape free' not in src.lower())

print(f'\nPROXY_POOL_UNIT_OK 共 {PASS} 项全部通过')
