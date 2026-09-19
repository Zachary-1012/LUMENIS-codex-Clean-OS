# -*- coding: utf-8 -*-
"""
豆包大模型API调用模块（字节跳动ARK）
功能：舆情分析、通用聊天、摘要生成、关键词提取、报告生成等
"""
import os
import json
import time
import sqlite3
import logging
from datetime import date
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ark_llm')

# ZBC Phase 7: module status markers
MODULE_STATUS = 'LEGACY'
DEPRECATION_NOTE = 'ARK/doubao channel disabled since 2026-09-02 (AI_PROVIDER=zhipu). Routes migrated to intelligence.py (zhipu GLM). Retained for backward compatibility only.'
AI_PROVIDER_GUARD = True  # PROVIDER_ACTIVE only true when AI_PROVIDER in (ark,doubao,volc,doubao-ark)

# =========配置区========
# 优先从环境变量读取，没有则使用默认值
API_KEY = os.getenv('ARK_API_KEY', '').strip()
API_URL = os.getenv('ARK_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3') + '/chat/completions'
MODEL_NAME = os.getenv('ARK_MODEL', 'doubao-seed-evolving-latest-version')
MAX_DAILY_TOKEN = int(os.getenv('ARK_MAX_DAILY_TOKEN', '190000'))
MAX_RETRIES = int(os.getenv('ARK_MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('ARK_RETRY_DELAY', '2'))
TIMEOUT = int(os.getenv('ARK_TIMEOUT', '60'))

# AI_PROVIDER 主开关守卫：非豆包主力时禁用豆包通道（豆包最小输出硬边界）
AI_PROVIDER = os.getenv('AI_PROVIDER', 'zhipu').strip().lower()
PROVIDER_ACTIVE = AI_PROVIDER in ('ark', 'doubao', 'volc', 'doubao-ark')


# 数据库路径（使用绝对路径）
BASE_DIR = Path(__file__).parent
from lumenis.shared.database import get_repository, main_db_path  # token accounting shares canonical production DB
TOKEN_DB = main_db_path()
# ======================


def load_daily_token():
    """加载今日已使用的token数"""
    try:
        today = date.today().isoformat()
        conn = get_repository().connect()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS token_stat (day TEXT PRIMARY KEY, used INTEGER)''')
        cur.execute("SELECT used FROM token_stat WHERE day=?", (today,))
        row = cur.fetchone()
        conn.close()
        if row:
            return row[0]
        return 0
    except Exception as e:
        logger.error(f"加载token统计失败: {e}")
        return 0


def save_daily_token(total: int):
    """保存今日已使用的token数"""
    try:
        today = date.today().isoformat()
        conn = get_repository().connect()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS token_stat (day TEXT PRIMARY KEY, used INTEGER)''')
        cur.execute('''INSERT OR REPLACE INTO token_stat(day,used) VALUES (?,?)''', (today, total))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"保存token统计失败: {e}")


def check_token_limit():
    """检查是否超过每日token限制"""
    daily_token_used = load_daily_token()
    if daily_token_used >= MAX_DAILY_TOKEN:
        logger.warning(f"今日token已达上限: {daily_token_used}/{MAX_DAILY_TOKEN}")
        return False, daily_token_used
    return True, daily_token_used


def call_ark_api(messages, temperature=0.7, max_tokens=None):
    """
    通用ARK API调用函数
    :param messages: 消息列表 [{"role": "system/user", "content": "..."}]
    :param temperature: 温度参数
    :param max_tokens: 最大生成token数
    :return: 响应内容字符串
    """
    # 安全：无 API_KEY 立即明确报错（调用方可见），禁止发空 Bearer 请求
    if not PROVIDER_ACTIVE:
        raise RuntimeError(
            f"ark_channel_disabled: AI_PROVIDER={AI_PROVIDER} (zhipu 主力模式豆包通道禁用，仅 zhipu/glm 走智谱)")

    if not API_KEY:
        raise RuntimeError("ARK_API_KEY not configured: set in .env (gitignore-protected) and restart")

    # 检查token限制
    ok, daily_token_used = check_token_limit()
    if not ok:
        raise Exception(f"daily_token_limit_exceeded: {daily_token_used}/{MAX_DAILY_TOKEN}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "messages": messages
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    # 重试机制
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            import requests
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
            resp.raise_for_status()
            res_json = resp.json()

            # 记录token使用
            usage = res_json.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens
            daily_token_used += total_tokens
            save_daily_token(daily_token_used)

            content = res_json["choices"][0]["message"]["content"]
            logger.info(f"API调用成功 (尝试{attempt+1}/{MAX_RETRIES}), token: {total_tokens}, 今日累计: {daily_token_used}")
            return content

        except Exception as e:
            last_error = e
            logger.warning(f"API调用失败 (尝试{attempt+1}/{MAX_RETRIES}): {repr(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # 指数退避

    raise Exception(f"API调用失败，已重试{MAX_RETRIES}次: {repr(last_error)}")


def sentiment_analyse(text: str):
    """
    舆情分析
    :param text: 待分析文本
    :return: {"sentiment": -1/0/1, "summary": "...", "keywords": [...]}
    """
    messages = [
        {
            "role": "system",
            "content": "你是专业的舆情分析助手，输出严格JSON格式，只输出json，不要有其他文字。字段：sentiment(-1负面,0中性,1正面),summary(简要总结),keywords(关键词数组)"
        },
        {
            "role": "user",
            "content": text
        }
    ]

    try:
        content = call_ark_api(messages, temperature=0.1)
        # 尝试解析JSON
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except Exception as _e:
                    logger.warning('ark_llm json re-parse failed: %s', _e)
            return {"error": "json_parse_failed", "raw_content": content, "sentiment": None}
    except Exception as e:
        logger.error(f"舆情分析失败: {e}")
        return {"error": str(e), "sentiment": None}


def generate_summary(text: str, max_length=200):
    """
    生成文本摘要
    :param text: 待摘要文本
    :param max_length: 最大长度
    :return: 摘要字符串
    """
    messages = [
        {
            "role": "system",
            "content": f"你是专业的文本摘要助手，请生成简洁准确的摘要，不超过{max_length}字。只输出摘要内容，不要有其他文字。"
        },
        {
            "role": "user",
            "content": text
        }
    ]

    try:
        return call_ark_api(messages, temperature=0.3)
    except Exception as e:
        logger.error(f"摘要生成失败: {e}")
        return f"摘要生成失败: {str(e)}"


def extract_keywords(text: str, num_keywords=10):
    """
    提取关键词
    :param text: 待提取文本
    :param num_keywords: 关键词数量
    :return: 关键词列表
    """
    messages = [
        {
            "role": "system",
            "content": f"你是专业的关键词提取助手，请提取{num_keywords}个最重要的关键词。输出严格JSON格式：{{\"keywords\": [\"关键词1\", \"关键词2\", ...]}}，只输出json。"
        },
        {
            "role": "user",
            "content": text
        }
    ]

    try:
        content = call_ark_api(messages, temperature=0.2)
        try:
            data = json.loads(content)
            return data.get("keywords", [])
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group()).get("keywords", [])
                except:
                    pass
            return []
    except Exception as e:
        logger.error(f"关键词提取失败: {e}")
        return []


def chat(message: str, system_prompt=None, history=None):
    """
    通用聊天接口
    :param message: 用户消息
    :param system_prompt: 系统提示词
    :param history: 历史消息列表
    :return: 回复字符串
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        return call_ark_api(messages, temperature=0.7)
    except Exception as e:
        logger.error(f"聊天失败: {e}")
        return f"抱歉，我遇到了一些问题：{str(e)}"


def generate_report(title: str, data: dict, report_type="daily"):
    """
    生成舆情报告
    :param title: 报告标题
    :param data: 报告数据
    :param report_type: 报告类型 (daily/weekly/monthly)
    :return: 报告内容字符串
    """
    type_names = {
        "daily": "日报",
        "weekly": "周报",
        "monthly": "月报"
    }
    type_name = type_names.get(report_type, "报告")

    system_prompt = f"""你是专业的舆情分析报告撰写专家。
请根据提供的数据撰写一份广州太古汇{type_name}，要求：
1. 结构清晰，包含概述、数据统计、重点事件、风险预警、建议等部分
2. 数据准确，引用提供的数据
3. 语言专业，符合公关行业标准
4. 重点突出负面舆情和风险事件
5. 给出可操作的建议"""

    user_message = f"""报告标题：{title}
报告数据：
{json.dumps(data, ensure_ascii=False, indent=2)}

请撰写完整的{type_name}。"""

    try:
        return chat(user_message, system_prompt=system_prompt)
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        return f"报告生成失败: {str(e)}"


def get_api_status():
    """获取API状态信息"""
    daily_token_used = load_daily_token()
    return {
        "enabled": bool(API_KEY),
        "provider": "ark",
        "model": MODEL_NAME,
        "api_url": API_URL,
        "daily_token_used": daily_token_used,
        "daily_token_limit": MAX_DAILY_TOKEN,
        "remaining_tokens": max(0, MAX_DAILY_TOKEN - daily_token_used),
        "max_retries": MAX_RETRIES,
        "timeout": TIMEOUT
    }


if __name__ == "__main__":
    print("=" * 60)
    print("豆包大模型API测试")
    print("=" * 60)

    # 显示API状态
    status = get_api_status()
    print(f"\nAPI状态:")
    print(f"  模型: {status['model']}")
    print(f"  今日已用token: {status['daily_token_used']}/{status['daily_token_limit']}")
    print(f"  剩余token: {status['remaining_tokens']}")

    # 测试舆情分析
    print("\n" + "=" * 60)
    print("测试1: 舆情分析")
    print("=" * 60)
    test_text = "太古汇这家门店服务很好，环境高级，体验很不错，但是停车场排队时间太长了"
    print(f"输入: {test_text}")
    result = sentiment_analyse(test_text)
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 测试摘要生成
    print("\n" + "=" * 60)
    print("测试2: 摘要生成")
    print("=" * 60)
    long_text = """广州太古汇位于广州市天河区天河路383号，是太古地产在中国大陆地区的第二个投资物业。
项目总楼面面积约13.8万平方米，包括一个高端购物商场、一座甲级办公楼（太古汇一座）、
一座甲级办公楼（太古汇二座）以及一家精品酒店（广州文华东方酒店）。
太古汇商场于2011年9月开业，汇聚了众多国际知名品牌，包括Louis Vuitton、Gucci、
Prada、Chanel、Hermès等奢侈品牌，以及Apple、Nike等潮流品牌。
商场内还有多家高端餐厅和咖啡馆，为顾客提供多元化的餐饮选择。
太古汇的设计理念是"城市中的绿洲"，商场内部采用了大量的自然采光和绿色植物，
营造出舒适宜人的购物环境。商场还经常举办各种文化艺术活动和展览，
为顾客带来丰富的文化体验。"""
    print(f"输入长度: {len(long_text)}字")
    summary = generate_summary(long_text, max_length=100)
    print(f"摘要: {summary}")

    # 测试关键词提取
    print("\n" + "=" * 60)
    print("测试3: 关键词提取")
    print("=" * 60)
    keywords = extract_keywords(long_text, num_keywords=8)
    print(f"关键词: {keywords}")

    # 最终状态
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    final_status = get_api_status()
    print(f"今日已用token: {final_status['daily_token_used']}/{final_status['daily_token_limit']}")
    print(f"剩余token: {final_status['remaining_tokens']}")
