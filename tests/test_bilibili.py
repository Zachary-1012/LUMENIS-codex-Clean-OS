"""测试B站搜索功能"""
from bilibili_login_manager import get_bilibili_manager
import json

manager = get_bilibili_manager()

print('=== B站登录状态 ===')
status = manager.check_login_status()
print(json.dumps(status, ensure_ascii=False, indent=2))

if status['logged_in']:
    print()
    print('=== 测试搜索广州太古汇 ===')
    result = manager.search_videos('广州太古汇')
    if result['ok']:
        print(f'找到 {result["total"]} 个视频')
        for i, video in enumerate(result['videos'][:5]):
            print(f'{i+1}. {video["title"]} - {video["author"]} - 播放:{video["play"]}')
    else:
        print(f'搜索失败: {result.get("error")}')
        print(f'错误码: {result.get("code")}')
