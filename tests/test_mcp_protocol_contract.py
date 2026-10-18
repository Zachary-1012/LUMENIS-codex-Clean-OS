"""Self-authored subprocess protocol fixtures: no external MCP execution."""

import json
import sys

import pytest

from mcp_discovery import call_mcp_stdio, discover_mcp_stdio, tool_contract_hash

TOOL = {
    "name": "read_signal",
    "annotations": {"readOnlyHint": True},
    "inputSchema": {
        "type": "object",
        "$defs": {"query": {"type": "string"}},
        "properties": {"query": {"$ref": "#/$defs/query"}},
        "required": ["query"],
        "additionalProperties": False,
    },
    "outputSchema": {
        "type": "object",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    },
}


def server(tmp_path, **options):
    config = {"tool": TOOL, **options}
    path = tmp_path / "server.py"
    path.write_text(
        """import json,sys
config = json.loads(CONFIG)
for line in sys.stdin:
 m=json.loads(line)
 if 'id' not in m: continue
 method=m['method']
 if method=='initialize':
  result={'protocolVersion':config.get('version','2025-11-25'),'capabilities':config.get('caps',{'tools':{}}),'serverInfo':{'name':'local-fixture','version':'1'}}
 elif method=='tools/list':
  if config.get('paginate') and not m.get('params',{}).get('cursor'): result={'tools':[], 'nextCursor':'page2'}
  else: result={'tools':[config['tool']]}
  if config.get('cycle'): result={'tools':[], 'nextCursor':'repeat'}
 elif method=='tools/call':
  result=config.get('result',{'content':[{'type':'text','text':'ok'}],'structuredContent':{'value':42}})
 else: raise RuntimeError('unadvertised method called')
 reply={'jsonrpc':'2.0','id':m['id'],'result':result}
 if config.get('bad_rpc'): reply.pop('jsonrpc')
 if config.get('wrong_id'): reply['id']=True
 if config.get('oversize'): print('x' * 1100000,flush=True); continue
 if config.get('error_and_result'): reply['error']={'code':-32603,'message':'bad'}
 print(json.dumps(reply),flush=True)
""".replace("CONFIG", repr(json.dumps(config))),
        encoding="utf-8",
    )
    return [sys.executable], [str(path)]


def invoke(tmp_path, *, arguments=None, reviewed=True, contracts=None, **options):
    command, args = server(tmp_path, **options)
    return call_mcp_stdio(
        command,
        args,
        tool_name="read_signal",
        arguments={"query": "x"} if arguments is None else arguments,
        allow_process=True,
        allow_tool_call=True,
        human_approved=True,
        permissions_granted=["mcp:tools/call", "read_only"],
        allowed_tools=["read_signal"],
        reviewed_tool_contracts=(
            contracts
            if contracts is not None
            else ({"read_signal": tool_contract_hash(TOOL)} if reviewed else {})
        ),
        timeout=3,
    )


def test_paginated_discovery_and_call(tmp_path):
    command, args = server(tmp_path, paginate=True)
    result = discover_mcp_stdio(command, args, allow_process=True)
    assert result["ok"], result
    assert result["trace"]["request_count"] == 3
    assert result["security"]["tool_calls"] == 0
    assert result["tool_contracts"] == {"read_signal": tool_contract_hash(TOOL)}
    assert result["tools"][0]["inputSchema"] == TOOL["inputSchema"]
    result = invoke(tmp_path, paginate=True)
    assert result["ok"], result
    assert result["result"]["structuredContent"] == {"value": 42}


@pytest.mark.parametrize(
    "options",
    [
        {"version": "2024-11-05"},
        {"bad_rpc": True},
        {"wrong_id": True},
        {"error_and_result": True},
        {"cycle": True},
        {"oversize": True},
    ],
)
def test_protocol_rejected_before_call(tmp_path, options):
    result = invoke(tmp_path, **options)
    assert result["state"] == "PROTOCOL_ERROR", result
    assert result["security"]["tool_calls"] == 0


def test_only_advertised_capabilities_are_requested(tmp_path):
    command, args = server(tmp_path, caps={})
    result = discover_mcp_stdio(command, args, allow_process=True)
    assert result["ok"]
    assert result["trace"]["request_count"] == 1
    assert result["tools"] == []
    assert invoke(tmp_path, caps={})["state"] == "CAPABILITY_UNAVAILABLE"


@pytest.mark.parametrize("arguments", [{}, {"query": 42}, {"query": "x", "extra": True}])
def test_invalid_arguments_never_call(tmp_path, arguments):
    result = invoke(tmp_path, arguments=arguments)
    assert result["state"] == "PROTOCOL_ERROR"
    assert result["security"]["tool_calls"] == 0


def test_missing_review_and_changed_contract(tmp_path):
    assert invoke(tmp_path, reviewed=False)["state"] == "CONTRACT_APPROVAL_REQUIRED"
    assert invoke(tmp_path, contracts={"read_signal": "0" * 64})["state"] == "CONTRACT_CHANGED"


@pytest.mark.parametrize(
    "result",
    [
        {"content": [], "structuredContent": {"value": "wrong"}},
        {"content": []},
        {"content": "wrong"},
        {"content": [], "isError": "false"},
    ],
)
def test_output_rejected(tmp_path, result):
    response = invoke(tmp_path, result=result)
    assert response["state"] == "PROTOCOL_ERROR"
    assert response["security"]["tool_calls"] == 1
    assert response["result"] is None


def test_tool_error_does_not_require_success_output(tmp_path):
    result = invoke(tmp_path, result={"content": [], "isError": True})
    assert result["state"] == "TOOL_ERROR"


@pytest.mark.parametrize("ref", ["https://example.com/schema", "file:///etc/passwd", "/tmp/schema"])
def test_external_schema_refs_rejected_without_retrieval(tmp_path, ref):
    tool = {**TOOL, "inputSchema": {"type": "object", "$ref": ref}}
    result = invoke(tmp_path, tool=tool)
    assert result["state"] == "PROTOCOL_ERROR"
    assert result["security"]["tool_calls"] == 0


def test_reader_rejects_duplicate_keys_and_nonfinite_json(tmp_path):
    for raw in [
        '{"jsonrpc":"2.0","id":1,"id":1,"result":{}}',
        '{"jsonrpc":"2.0","id":1,"result":{"n":NaN}}',
    ]:
        script = tmp_path / "invalid_json.py"
        script.write_text("import sys\nsys.stdin.readline()\nprint(" + repr(raw) + ",flush=True)\n")
        result = discover_mcp_stdio([sys.executable], [str(script)], allow_process=True, timeout=1)
        assert result["state"] == "PROTOCOL_ERROR"


def test_timeout_reaps_unresponsive_process(tmp_path):
    script = tmp_path / "hang.py"
    pidfile = tmp_path / "pid"
    script.write_text(
        "import os,time\nopen("
        + repr(str(pidfile))
        + ',"w").write(str(os.getpid()))\ntime.sleep(30)\n'
    )
    result = discover_mcp_stdio([sys.executable], [str(script)], allow_process=True, timeout=0.2)
    assert result["state"] == "TIMEOUT"
    import os

    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)


def test_registered_runtime_requires_stored_contract_before_process(tmp_path, monkeypatch):
    from tests.test_mcp_skill_runtime import _package

    runtime, package = _package(tmp_path, monkeypatch)
    info = {
        "skill_id": "trendhub-mcp",
        "version": "1.5.2",
        "install_path": str(package),
        "entrypoint": runtime.build_entrypoint(str(package)),
        "tools_json": '["read_signal"]',
        "permissions_granted_json": '["mcp:tools/call","read_only"]',
    }
    monkeypatch.setattr(runtime, "call_mcp_stdio", lambda *a, **k: pytest.fail("must not start"))
    result = runtime.invoke_registered_mcp(
        info, {"tool_name": "read_signal", "arguments": {}, "human_approved": True}
    )
    assert result["state"] == "CONTRACT_APPROVAL_REQUIRED"


def test_runtime_change_invalidates_pin_before_process(tmp_path, monkeypatch):
    from tests.test_mcp_skill_runtime import _package

    runtime, package = _package(tmp_path, monkeypatch)
    info = {
        "skill_id": "trendhub-mcp",
        "version": "1.5.2",
        "active_version": "1.5.2",
        "install_path": str(package),
        "entrypoint": runtime.build_entrypoint(str(package)),
        "tools_json": '["read_signal"]',
        "permissions_granted_json": '["mcp:tools/call","read_only"]',
    }
    compatibility = {
        "mcp_tool_contracts": {"read_signal": tool_contract_hash(TOOL)},
        "mcp_runtime_binding": runtime.runtime_contract_binding(info),
    }
    info["compatibility_json"] = json.dumps(compatibility)
    info["entrypoint"] = {**info["entrypoint"], "args": []}
    monkeypatch.setattr(runtime, "call_mcp_stdio", lambda *a, **k: pytest.fail("must not start"))
    assert (
        runtime.invoke_registered_mcp(
            info, {"tool_name": "read_signal", "arguments": {}, "human_approved": True}
        )["state"]
        == "CONTRACT_CHANGED"
    )


def test_task_required_tool_is_not_falsely_advertised_as_supported(tmp_path):
    result = invoke(tmp_path, tool={**TOOL, "execution": {"taskSupport": "required"}})
    assert result["state"] == "CAPABILITY_UNAVAILABLE"
    assert result["security"]["tool_calls"] == 0
