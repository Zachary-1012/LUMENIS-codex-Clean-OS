# -*- coding: utf-8 -*-
"""采集运维控制面：Kill Switch + Dry-run（研究自 baldur System-Control，落地 ZBC）。

范式对齐（baldur docs/concepts/oss/system-control.md）：
  1. Kill Switch：全局 enabled/disabled；翻转必须带 reason（可问责）；持久化，重启保持
     disabled（不静默重新启用自动化）；读失败 fail-safe 为 enabled（不误禁用）。
  2. Dry-run：观察/演练模式，正常评估所有决策但抑制实际动作，记录 would-have；
     离开 dry-run 需显式 confirm（不会意外退出观察模式）。
  3. 审计：每次翻转记录 who/why/when，事件时间线完整。

用法（程序化检查，供 collector 等调用）：
  from collector_guard.runtime_switch import get_switch
  if get_switch().is_enabled() and not get_switch().is_dry_run():   # 才真正行动
      ...
"""
import datetime
import io
import json
import os
import threading

from core.repository_registry import get_data_dir

STATE_PATH = os.path.join(get_data_dir(), "runtime-switch.json")
AUDIT_PATH = os.path.join(get_data_dir(), "runtime-switch-audit.jsonl")


class RuntimeSwitch:
    """采集运维总开关：enabled/disabled × dry_run on/off。持久化 + 审计 + fail-safe。"""

    def __init__(self, state_path=None, audit_path=None):
        self.state_path = state_path or STATE_PATH
        self.audit_path = audit_path or AUDIT_PATH
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)

    # ---- 状态读写 ----
    def _load(self):
        try:
            with io.open(self.state_path, encoding="utf-8") as f:
                j = json.load(f)
            return {"enabled": bool(j.get("enabled", True)),
                    "dry_run": bool(j.get("dry_run", False))}
        except Exception:
            # fail-safe：读不到状态按 enabled + live（不误禁用，不静默进入观察模式）
            return {"enabled": True, "dry_run": False}

    def _save(self, state):
        with self._lock, io.open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)

    def _audit(self, action, reason, actor):
        rec = {
            "ts": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "action": action, "reason": reason or "", "actor": actor or "unknown",
        }
        with self._lock, io.open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---- 程序化检查 ----
    def is_enabled(self):
        return self._load()["enabled"]

    def is_dry_run(self):
        return self._load()["dry_run"]

    def status(self):
        st = self._load()
        st["state"] = "DISABLED" if not st["enabled"] else ("DRY_RUN" if st["dry_run"] else "ENABLED")
        return st

    # ---- 控制 ----
    def set_enabled(self, enabled, *, reason=None, actor=None, confirm=False):
        """Kill Switch：disable 必须带 reason；enable 需 confirm（对齐 baldur 可问责）。"""
        if enabled:
            if not confirm:
                return {"ok": False, "error": "重新启用需显式 confirm=True"}
            self._save({"enabled": True, "dry_run": self._load()["dry_run"]})
            self._audit("enable", reason, actor)
        else:
            if not reason:
                return {"ok": False, "error": "禁用必须提供 reason（可问责）"}
            self._save({"enabled": False, "dry_run": self._load()["dry_run"]})
            self._audit("disable", reason, actor)
        return {"ok": True, **self.status()}

    def set_dry_run(self, on, *, confirm=False):
        """Dry-run：开启无需确认；关闭（回到 LIVE）需 confirm，避免意外退出观察模式。"""
        if not on and not confirm:
            return {"ok": False, "error": "退出 dry-run 需显式 confirm=True（防止意外上线）"}
        st = self._load()
        st["dry_run"] = bool(on)
        self._save(st)
        self._audit("dry_run_on" if on else "dry_run_off", "dry-run 切换", "operator")
        return {"ok": True, **self.status()}

    def audit_trail(self, limit=20):
        if not os.path.exists(self.audit_path):
            return []
        out = []
        with io.open(self.audit_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out[-limit:]


_default = None


def get_switch():
    global _default
    if _default is None:
        _default = RuntimeSwitch()
    return _default
