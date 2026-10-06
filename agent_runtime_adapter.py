# -*- coding: utf-8 -*-
"""LUMENIS compatibility adapter for the canonical shared-intelligence repository.

Cross-repository runtime dependency is optional and fail-closed. The external
repository may supply Shared Intelligence Assets but never owns or overwrites
LUMENIS Production Truth, Permission, Evidence or product runtime.
"""
import json
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional


def _osai_root() -> Optional[str]:
    """发现 OSAI 仓库根目录（复用 skill adapter 的发现逻辑，禁止硬编码个人路径）。"""
    env = os.environ.get("OSAI_REPO_ROOT")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    for rp in (os.path.join(here, "repo_registry.json"),
               os.path.join(here, "config", "repo_registry.json"),
               os.path.expanduser("~/.lumenis/repo_registry.json")):
        if os.path.isfile(rp):
            try:
                with open(rp, "r", encoding="utf-8") as fh:
                    reg = json.load(fh)
                for repo in reg.get("repositories", []):
                    if (repo.get("role") == "intelligence_core"
                            or repo.get("name", "").lower() in ("osai", "zachary-os-ai")):
                        p = repo.get("root_path", "")
                        if p and os.path.isdir(p):
                            return p
            except (json.JSONDecodeError, OSError):
                continue
    parent = os.path.dirname(here)
    for base in (parent, os.path.expanduser("~")):
        try:
            for entry in os.listdir(base):
                full = os.path.join(base, entry)
                if os.path.isdir(full) and entry.lower() in ("zachary-os-ai", "zachary os ai", "osai"):
                    return full
        except OSError:
            pass
    return None


def _python_executable() -> str:
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

# ZBC Lifecycle Contract V1.0 (bypass-mode)
try:
    from lifecycle_mixin import LifecycleMixin as _LifecycleMixin
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _LifecycleMixin = None
    _LIFECYCLE_AVAILABLE = False


class AgentRuntimeAdapter:
    """ZBC → OSAI Agent Identity / Delegation / OBO / JIT 跨仓适配器。

    所有方法 fail-close：OSAI 不可用 → {connected: False, status: "UNAVAILABLE"}。
    不造假身份、不伪造委托、不默认 ALLOW。
    """

    def __init__(self, osai_root: Optional[str] = None, timeout: int = 15):
        self._osai_root = osai_root or _osai_root()
        self._timeout = timeout
        self._last_error: Optional[str] = None
        self._audit_log: List[Dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return self._osai_root is not None

    def _run_osai(self, script: str, timeout: Optional[float] = None,
                  argv: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """通过 subprocess 调用 OSAI Python，返回 JSON。fail-close。"""
        if not self._osai_root:
            self._last_error = "OSAI_REPO_NOT_FOUND"
            return None
        try:
            cmd = [_python_executable(), "-c", script]
            if argv:
                cmd.extend(argv)
            result = subprocess.run(
                cmd, cwd=self._osai_root, capture_output=True, text=True,
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

    def _audit(self, action: str, target: str, result: str, reason: str = "") -> Dict[str, Any]:
        record = {
            "audit_id": f"audit_{uuid.uuid4().hex[:10]}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "action": action, "target": target,
            "result": result, "reason": reason,
        }
        self._audit_log.append(record)
        return record

    # ============ Agent Identity ============

    _IDENTITY_SCRIPT = (
        "import json,sys; sys.path.insert(0,'.'); "
        "from osai_engine.agent_identity import get_identity_registry; "
        "reg=get_identity_registry(); "
        "args=json.loads(sys.argv[1]); "
        "ident=reg.create_identity("
        "identity_type=args['identity_type'],name=args['name'],"
        "parent_identity=args.get('parent_identity',''),"
        "permissions=args.get('permissions',[]),"
        "scope=args.get('scope','default'),intent=args.get('intent','')); "
        "print(json.dumps({'identity': ident.to_dict(),"
        "'chain': [i.to_dict() for i in reg.get_chain(ident.identity_id)]},ensure_ascii=False))"
    )

    def create_agent_identity(self, name: str, permissions: List[str] = None,
                               parent_identity: str = "", scope: str = "default",
                               intent: str = "") -> Dict[str, Any]:
        """创建 Agent Identity（User → Agent 身份链分离）。

        返回 {connected, status, identity, chain}。
        OSAI 不可用 → UNAVAILABLE（不造假身份）。
        """
        payload = json.dumps({
            "identity_type": "agent", "name": name,
            "parent_identity": parent_identity,
            "permissions": permissions or ["READ", "AUDIT", "ANALYZE"],
            "scope": scope, "intent": intent,
        }, ensure_ascii=False)
        data = self._run_osai(self._IDENTITY_SCRIPT, argv=[payload])
        if data is None:
            self._audit("create_agent_identity", name, "UNAVAILABLE", self._last_error)
            return {"connected": False, "status": "UNAVAILABLE", "error": self._last_error}
        self._audit("create_agent_identity", name, "CREATED",
                    data["identity"]["identity_id"])
        return {"connected": True, "status": "CREATED",
                "identity": data["identity"], "identity_chain": data["chain"]}

    # ============ Delegation / OBO ============

    _DELEGATE_SCRIPT = (
        "import json,sys; sys.path.insert(0,'.'); "
        "from osai_engine.agent_identity import get_identity_registry; "
        "from osai_engine.obo_jit import DelegationManager; "
        "reg=get_identity_registry(); dm=DelegationManager(reg); "
        "args=json.loads(sys.argv[1]); "
        "ctx=dm.delegate("
        "delegator_id=args['delegator_id'],delegate_id=args['delegate_id'],"
        "permissions=args.get('permissions',[]),scope=args.get('scope','default'),"
        "intent=args.get('intent',''),task_id=args.get('task_id','')); "
        "print(json.dumps({'delegation': ctx.to_dict()},ensure_ascii=False))"
    )

    def delegate(self, delegator_id: str, delegate_id: str,
                 permissions: List[str], scope: str = "default",
                 intent: str = "", task_id: str = "") -> Dict[str, Any]:
        """创建 OBO 委托（用户授权 Agent 执行，不是 Agent 冒充用户）。

        fail-close：OSAI 不可用 → UNAVAILABLE，不默认允许委托。
        """
        payload = json.dumps({
            "delegator_id": delegator_id, "delegate_id": delegate_id,
            "permissions": permissions, "scope": scope,
            "intent": intent, "task_id": task_id,
        }, ensure_ascii=False)
        data = self._run_osai(self._DELEGATE_SCRIPT, argv=[payload])
        if data is None:
            self._audit("delegate", f"{delegator_id}->{delegate_id}", "UNAVAILABLE", self._last_error)
            return {"connected": False, "status": "UNAVAILABLE", "error": self._last_error}
        self._audit("delegate", f"{delegator_id}->{delegate_id}", "GRANTED",
                    data["delegation"]["delegation_id"])
        return {"connected": True, "status": "DELEGATED",
                "delegation": data["delegation"]}

    # ============ JIT Elevation ============

    _JIT_SCRIPT = (
        "import json,sys; sys.path.insert(0,'.'); "
        "from osai_engine.agent_identity import get_identity_registry; "
        "from osai_engine.obo_jit import DelegationManager; "
        "reg=get_identity_registry(); dm=DelegationManager(reg); "
        "args=json.loads(sys.argv[1]); "
        "ctx=dm.jit_elevate(args['delegation_id'],args.get('additional_permissions',[]),"
        "duration_seconds=args.get('duration_seconds',300.0)); "
        "print(json.dumps({'delegation': ctx.to_dict() if ctx else None},ensure_ascii=False))"
    )

    def jit_elevate(self, delegation_id: str, additional_permissions: List[str],
                     duration_seconds: float = 300.0) -> Dict[str, Any]:
        """JIT 临时权限提升（有时效、可撤销、不永久授权）。

        fail-close：委托不存在或已过期 → DENIED，不默认提升。
        """
        payload = json.dumps({
            "delegation_id": delegation_id,
            "additional_permissions": additional_permissions,
            "duration_seconds": duration_seconds,
        }, ensure_ascii=False)
        data = self._run_osai(self._JIT_SCRIPT, argv=[payload])
        if data is None:
            self._audit("jit_elevate", delegation_id, "UNAVAILABLE", self._last_error)
            return {"connected": False, "status": "UNAVAILABLE", "error": self._last_error}
        if data.get("delegation") is None:
            self._audit("jit_elevate", delegation_id, "DENIED", "delegation not found or expired")
            return {"connected": True, "status": "DENIED",
                    "error": "delegation not found or expired"}
        self._audit("jit_elevate", delegation_id, "ELEVATED",
                    f"perms={additional_permissions}, duration={duration_seconds}s")
        return {"connected": True, "status": "ELEVATED",
                "delegation": data["delegation"]}

    # ============ Check Delegation ============

    _CHECK_SCRIPT = (
        "import json,sys; sys.path.insert(0,'.'); "
        "from osai_engine.agent_identity import get_identity_registry; "
        "from osai_engine.obo_jit import DelegationManager; "
        "reg=get_identity_registry(); dm=DelegationManager(reg); "
        "args=json.loads(sys.argv[1]); "
        "result=dm.check_delegation(args['delegation_id'],args['permission']); "
        "print(json.dumps(result,ensure_ascii=False))"
    )

    def check_delegation(self, delegation_id: str, permission: str) -> Dict[str, Any]:
        """检查委托是否允许某操作（OBO 授权验证）。

        fail-close：任何异常 → DENIED。
        """
        payload = json.dumps({"delegation_id": delegation_id, "permission": permission},
                             ensure_ascii=False)
        data = self._run_osai(self._CHECK_SCRIPT, argv=[payload])
        if data is None:
            self._audit("check_delegation", delegation_id, "UNAVAILABLE", self._last_error)
            return {"connected": False, "status": "UNAVAILABLE", "allowed": False,
                    "error": self._last_error}
        result = data.get("allowed", False)
        self._audit("check_delegation", delegation_id,
                    "ALLOW" if result else "DENY",
                    data.get("reason", ""))
        return {"connected": True, "status": "CHECKED", **data}

    # ============ Status / Snapshot ============

    def status(self) -> Dict[str, Any]:
        """适配器状态快照。"""
        return {
            "connected": self.available,
            "osai_root": self._osai_root,
            "last_error": self._last_error,
            "audit_count": len(self._audit_log),
            "capabilities": ["agent_identity", "delegation_obo", "jit_elevation",
                              "delegation_check"],
            "design": "subprocess bridge, fail-close, no runtime hard-coupling",
        }


# ============ 进程级单例 ============

_adapter: Optional[AgentRuntimeAdapter] = None


def get_agent_adapter() -> AgentRuntimeAdapter:
    global _adapter
    if _adapter is None:
        _adapter = AgentRuntimeAdapter()
    return _adapter


if __name__ == "__main__":
    adapter = get_agent_adapter()
    print(json.dumps(adapter.status(), ensure_ascii=False, indent=2))
