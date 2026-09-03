import urllib.request
import json
import base64

auth = base64.b64encode(b'Zachary:Zachary01').decode()
headers = {'Authorization': f'Basic {auth}'}

print("=== 检查warning模块具体状态 ===")
req = urllib.request.Request('http://127.0.0.1:8200/api/system/health/detailed', headers=headers)
data = json.loads(urllib.request.urlopen(req, timeout=10).read())
modules = data.get('modules', {})
for name, mod in modules.items():
    status = mod.get('status', 'unknown')
    if status in ['warning', 'error']:
        detail = mod.get('detail', mod.get('message', ''))
        print(f"  {name}: status={status}, detail={detail}")

print("\n=== 检查所有模块状态 ===")
for name, mod in modules.items():
    status = mod.get('status', 'unknown')
    icon = '🟢' if status == 'ok' else '🟡' if status == 'warning' else '🔴'
    print(f"  {icon} {name}: {status}")

print("\n=== 检查自适应引擎 ===")
req = urllib.request.Request('http://127.0.0.1:8200/api/adaptive/status', headers=headers)
data = json.loads(urllib.request.urlopen(req, timeout=10).read())
print(f"  当前策略: {data.get('current_strategy')}")
print(f"  风险等级: {data.get('risk_level')}")
print(f"  请求间隔: {data.get('current_request_delay')}s")

print("\n=== 检查采集器状态 ===")
req = urllib.request.Request('http://127.0.0.1:8200/api/collector/status', headers=headers)
data = json.loads(urllib.request.urlopen(req, timeout=10).read())
print(f"  CDP状态: {data.get('cdp_status')}")
print(f"  今日采集: {data.get('today_collections')}")
print(f"  采集器状态: {data.get('collector_status')}")

print("\n检查完成！")
