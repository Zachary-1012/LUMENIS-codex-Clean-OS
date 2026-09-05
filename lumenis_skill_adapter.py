"""LUMENIS Cross-Core Skill Adapter — ZBC 消费 OSAI Canonical Skill Registry。

ZBC 不再维护独立 Skill Truth。所有 Skill 数据通过本 Adapter 从 OSAI
Canonical Registry 获取。OSAI 不可用时返回 PARTIALLY_CONNECTED，
不造假数据、不固定返回 SYNCED。

调用链：
  ZBC API → CrossCoreSkillAdapter → subprocess → OSAI canonical_skill_registry
  → JSON → ZBC Response

权限：只读，不修改 OSAI 任何状态。
"""
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


# OSAI 仓库路径（通过环境变量或默认相对路径发现，不硬编码个人路径）
def _osai_root() -> Optional[str]:
    """发现 OSAI 仓库根目录。优先环境变量，其次常见位置。"""
    env = os.environ.get("OSAI_REPO_ROOT")
    if env and os.path.isdir(env):
        return env
    # 常见兄弟目录
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(here), "Zachary-OS-AI"),
        os.path.join(os.path.dirname(here), "Zachary OS AI"),
        r"D:\Zachary OS AI",
        os.path.expanduser("~/Zachary-OS-AI"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def _python_executable() -> str:
    """获取可用的 Python 解释器。"""
    # 优先使用 ZBC .venv
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


class CrossCoreSkillAdapter:
    """ZBC → OSAI Canonical Registry 跨仓适配器。

    所有方法都是只读的，不修改 OSAI 状态。
    OSAI 不可用时明确返回 PARTIALLY_CONNECTED / UNAVAILABLE。
    """

    def __init__(self, osai_root: Optional[str] = None, timeout: int = 10):
        self._osai_root = osai_root or _osai_root()
        self._timeout = timeout
        self._last_error: Optional[str] = None
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 30.0  # 30 秒缓存

    @property
    def available(self) -> bool:
        return self._osai_root is not None

    def _run_osai(self, script: str, timeout: Optional[float] = None,
                  argv: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """通过 subprocess 调用 OSAI Python 执行脚本，返回 JSON。

        timeout: 本次独立超时（秒）；argv: 透传命令行参数（sys.argv[1:]）。
        """
        if not self._osai_root:
            self._last_error = "OSAI_REPO_NOT_FOUND"
            return None
        try:
            cmd = [_python_executable(), "-c", script]
            if argv:
                cmd.extend(argv)
            result = subprocess.run(
                cmd,
                cwd=self._osai_root,
                capture_output=True,
                text=True,
                timeout=timeout if timeout is not None else self._timeout,
                env={**os.environ, "PYTHONPATH": self._osai_root},
            )
            if result.returncode != 0:
                self._last_error = f"OSAI_EXIT_{result.returncode}: {result.stderr[:300]}"
                return None
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            self._last_error = "OSAI_TIMEOUT"
            return None
        except (json.JSONDecodeError, Exception) as e:
            self._last_error = f"OSAI_ERROR: {type(e).__name__}: {str(e)[:200]}"
            return None

    def get_registry_snapshot(self, force_refresh: bool = False) -> Dict[str, Any]:
        """获取 OSAI Canonical Registry 完整快照。

        Returns:
            dict: {
                "connected": bool,
                "status": "CONNECTED" | "PARTIALLY_CONNECTED" | "UNAVAILABLE",
                "source": "OSAI_CANONICAL_REGISTRY" | "FALLBACK_NONE",
                "data": {...} | None,
                "error": str | None,
            }
        """
        now = time.time()
        if not force_refresh and self._cache and (now - self._cache_ts) < self._cache_ttl:
            return self._cache

        script = (
            "import json, sys; sys.path.insert(0, '.'); "
            "from osai_engine.canonical_skill_registry import canonical_snapshot; "
            "print(json.dumps(canonical_snapshot(), ensure_ascii=False))"
        )
        data = self._run_osai(script)

        if data is None:
            result = {
                "connected": False,
                "status": "UNAVAILABLE",
                "source": "FALLBACK_NONE",
                "data": None,
                "error": self._last_error,
                "skills": [],
                "total": 0,
                "implemented_count": 0,
            }
        else:
            result = {
                "connected": True,
                "status": "CONNECTED",
                "source": "OSAI_CANONICAL_REGISTRY",
                "data": data,
                "error": None,
                "skills": data.get("skills", []),
                "total": data.get("total", 0),
                "implemented_count": data.get("implemented_count", 0),
                "partial_count": data.get("partial_count", 0),
                "planned_count": data.get("planned_count", 0),
            }
        self._cache = result
        self._cache_ts = now
        return result

    def get_skill(self, skill_id: str) -> Dict[str, Any]:
        """获取单个 Skill 定义。"""
        snap = self.get_registry_snapshot()
        if not snap["connected"]:
            return {"found": False, "status": "UNAVAILABLE", "error": snap["error"]}
        for s in snap["skills"]:
            if s["id"] == skill_id:
                return {"found": True, "status": s["status"], "skill": s}
        return {"found": False, "status": "UNKNOWN", "error": f"skill {skill_id} not found"}

    def check_sync_status(self) -> Dict[str, Any]:
        """真实检查 GitHub → Manifest → Registry 同步状态。

        不固定返回 SYNCED。实际检查：
        1. OSAI Canonical Registry 是否可用
        2. Manifest 文件是否存在
        3. 是否有版本冲突
        """
        snap = self.get_registry_snapshot(force_refresh=True)
        if not snap["connected"]:
            return {
                "sync_status": "UNAVAILABLE",
                "synced_count": 0,
                "conflict_count": 0,
                "error": snap["error"],
                "detail": "OSAI Canonical Registry unavailable, cannot verify sync",
            }

        # 检查 Manifest 目录
        manifest_dir = os.path.join(self._osai_root or "", "skills", "manifests")
        manifest_files = []
        if os.path.isdir(manifest_dir):
            manifest_files = [f for f in os.listdir(manifest_dir) if f.endswith(".json")]

        # 检查已实现 Skill 与 Manifest 的对应
        implemented = [s for s in snap["skills"] if s["status"] == "IMPLEMENTED"]
        implemented_ids = {s["id"] for s in implemented}
        manifest_ids = {os.path.splitext(f)[0].upper() for f in manifest_files}

        # 冲突检测：已实现但无 Manifest，或有 Manifest 但未实现
        missing_manifest = implemented_ids - manifest_ids
        unimplemented_manifest = manifest_ids - implemented_ids

        has_conflict = len(missing_manifest) > 0 or len(unimplemented_manifest) > 0

        return {
            "sync_status": "CONFLICT" if has_conflict else "SYNCED",
            "synced_count": len(implemented_ids & manifest_ids),
            "conflict_count": len(missing_manifest) + len(unimplemented_manifest),
            "missing_manifest": sorted(missing_manifest),
            "unimplemented_manifest": sorted(unimplemented_manifest),
            "manifest_files": len(manifest_files),
            "implemented_count": len(implemented),
            "error": None,
        }

    # OSAI SkillInvoker runner：参数经 argv(JSON) 传入，避免转义
    _INVOKE_RUNNER = (
        "import json,sys; sys.path.insert(0,'.'); "
        "from osai_engine.skill_invocation import SkillInvoker; "
        "args=json.loads(sys.argv[1]); "
        "r=SkillInvoker().invoke(args['task'],args['skill_id'],"
        "workspace=args.get('workspace','intelligence'),"
        "skill_version=args.get('skill_version','0.1.0'),"
        "user_permissions=args.get('user_permissions')); "
        "print(json.dumps(r,ensure_ascii=False,default=str))"
    )

    def invoke_skill(self, task: str, skill_id: str, workspace: str = "intelligence",
                     skill_version: str = "0.1.0",
                     user_permissions: Optional[List[str]] = None,
                     timeout: float = 90.0) -> Dict[str, Any]:
        """真实执行：ZBC → subprocess → OSAI SkillInvoker。

        走 OSAI 完整链 Permission(fail-close) → Context → Engine → Provider →
        EvidenceChain(落盘) → Evaluation。返回统一映射，绝不伪造 COMPLETED：
          - connected=False: OSAI 不可用/超时（调用方据此保留 ACCEPTED 兜底）
          - OSAI status SUCCESS/FAILED/BLOCKED 原样透传 + evidence/evaluation
        """
        if user_permissions is None:
            # 最小权限：只读/分析/测试/验证，不含 COMMIT/PUSH/HUMAN_APPROVAL
            user_permissions = ["READ", "AUDIT", "ANALYZE", "RESEARCH",
                                "PLAN", "PATCH_PREVIEW", "TEST", "VERIFY"]
        payload = json.dumps({
            "task": task, "skill_id": skill_id, "workspace": workspace,
            "skill_version": skill_version, "user_permissions": user_permissions,
        }, ensure_ascii=False)
        data = self._run_osai(self._INVOKE_RUNNER, timeout=timeout, argv=[payload])
        if data is None:
            return {"connected": False, "status": "UNAVAILABLE",
                    "error": self._last_error, "osai": None}
        return {"connected": True, "status": "CONNECTED",
                "error": None, "osai": data}



# 进程级单例
_adapter: Optional[CrossCoreSkillAdapter] = None


def get_skill_adapter() -> CrossCoreSkillAdapter:
    global _adapter
    if _adapter is None:
        _adapter = CrossCoreSkillAdapter()
    return _adapter


if __name__ == "__main__":
    adapter = get_skill_adapter()
    print("OSAI root:", adapter._osai_root)
    print("Available:", adapter.available)
    snap = adapter.get_registry_snapshot()
    print(json.dumps({
        "status": snap["status"],
        "total": snap.get("total", 0),
        "implemented": snap.get("implemented_count", 0),
        "error": snap.get("error"),
    }, ensure_ascii=False, indent=2))
    sync = adapter.check_sync_status()
    print("Sync:", json.dumps(sync, ensure_ascii=False, indent=2))
