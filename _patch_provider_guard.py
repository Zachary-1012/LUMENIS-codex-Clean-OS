# -*- coding: utf-8 -*-
"""为豆包(ARK)通道加 AI_PROVIDER 守卫：AI_PROVIDER 非豆包时禁用豆包通道（最小输出硬边界）。
备份已存：*.bak-providerguard"""
import io, os

base = r"D:\Taikoo-monitor-new"

def patch(path, old, new, tag):
    p = os.path.join(base, path)
    s = io.open(p, encoding="utf-8").read()
    if tag in s:
        print(f"[SKIP-ALREADY] {path}: {tag}")
        return
    if old not in s:
        print(f"[FAIL-NOTFOUND] {path}: {tag}")
        return
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print(f"[OK] {path}: {tag}")

# ---- 1) ark_llm.py: env 区加 PROVIDER_ACTIVE 判定 ----
old_env = "TIMEOUT = int(os.getenv('ARK_TIMEOUT', '60'))"
new_env = ("TIMEOUT = int(os.getenv('ARK_TIMEOUT', '60'))\n"
           "\n"
           "# AI_PROVIDER 主开关守卫：非豆包主力时禁用豆包通道（豆包最小输出硬边界）\n"
           "AI_PROVIDER = os.getenv('AI_PROVIDER', 'zhipu').strip().lower()\n"
           "PROVIDER_ACTIVE = AI_PROVIDER in ('ark', 'doubao', 'volc', 'doubao-ark')\n")
patch("ark_llm.py", old_env, new_env, "ark_provider_guard_env")

# ---- 2) ark_llm.py: call_ark_api 入口加 PROVIDER_ACTIVE 检查 ----
old_api = '    if not API_KEY:\n        raise RuntimeError("ARK_API_KEY not configured: set in .env (gitignore-protected) and restart")'
new_api = ('    if not PROVIDER_ACTIVE:\n'
           '        raise RuntimeError(\n'
           '            f"ark_channel_disabled: AI_PROVIDER={AI_PROVIDER} (zhipu 主力模式豆包通道禁用，仅 zhipu/glm 走智谱)")\n'
           '\n'
           '    if not API_KEY:\n'
           '        raise RuntimeError("ARK_API_KEY not configured: set in .env (gitignore-protected) and restart")')
patch("ark_llm.py", old_api, new_api, "ark_provider_guard_api")

# ---- 3) ai_learning_engine.py: __init__ 加 AI_PROVIDER 门控 ----
old_init = ("        # 尝试导入ark_llm\n"
            "        try:\n"
            "            import ark_llm\n"
            "            self.ark_llm = ark_llm\n"
            "            self.ai_available = True\n"
            "        except ImportError:\n"
            "            self.ark_llm = None\n"
            "            self.ai_available = False\n"
            "            logger.warning(\"ark_llm模块不可用，全网舆情检索功能受限\")")
new_init = ("        # 尝试导入ark_llm（受 AI_PROVIDER 主开关约束：仅豆包主力模式启用）\n"
            "        self.ai_provider = os.getenv('AI_PROVIDER', 'zhipu').strip().lower()\n"
            "        self.ark_channel_enabled = self.ai_provider in ('ark', 'doubao', 'volc', 'doubao-ark')\n"
            "        try:\n"
            "            import ark_llm\n"
            "            self.ark_llm = ark_llm\n"
            "            self.ai_available = self.ark_channel_enabled\n"
            "            if not self.ark_channel_enabled:\n"
            "                logger.warning(\n"
            "                    f\"豆包通道已禁用：AI_PROVIDER={self.ai_provider}（智谱主力模式，豆包最小输出）\")\n"
            "        except ImportError:\n"
            "            self.ark_llm = None\n"
            "            self.ai_available = False\n"
            "            logger.warning(\"ark_llm模块不可用，全网舆情检索功能受限\")")
patch("ai_learning_engine.py", old_init, new_init, "learning_provider_guard")

print("DONE")
