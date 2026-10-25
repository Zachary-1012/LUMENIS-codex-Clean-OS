# -*- coding: utf-8 -*-
"""AI Hub 路由：状态 / 对话 / 任意模块分析 / 学习记录 / 影子队列。"""
from flask import Blueprint, request, jsonify
from ..auth import require_auth, get_current_user, log_audit
from . import service, shadow

ai_bp = Blueprint("v4_ai", __name__)


@ai_bp.route("/ai/status", methods=["GET"])
@require_auth
def ai_status():
    return jsonify({"success": True, "ai": service.status()})


@ai_bp.route("/ai/settings", methods=["GET", "POST"])
@require_auth
def ai_settings():
    # Authenticated App entry delegates to the one settings/Gateway owner.
    # It does not require a server-wide Basic-auth credential to set user choice.
    from settings_module import user_ai_settings
    return user_ai_settings()


@ai_bp.route("/ai/chat", methods=["POST"])
@require_auth
def ai_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        result = service.invalid_chat_input("JSON_OBJECT_REQUIRED")
        result.pop("ok", None)
        return jsonify({"success": False, **result}), 503 if result["status"] == "UNAVAILABLE" else 400
    q = data.get("message") or data.get("question") or ""
    # Ordinary chat must not depend on selecting a business report scope.
    # A reports:read scope alone is not a SourceUse grant for sending business
    # records to a model. Until a typed Gateway operation supplies and validates
    # that SourceUse contract, the service receives no business retrieval scope.
    result = service.chat(q, history=data.get("history"), scope=data.get("scope", "all"),
                          source_scope=None, external_approval=data.get("external_approval"))
    success = result.pop("ok", False)
    status = result.get("status")
    http_status = 200 if success else (409 if status == "APPROVAL_REQUIRED" else 400 if status == "INVALID_INPUT" else 503 if status == "UNAVAILABLE" else 502)
    return jsonify({"success": success, **result}), http_status


@ai_bp.route("/ai/analyze", methods=["POST"])
@require_auth
def ai_analyze():
    data = request.get_json() or {}
    result = service.analyze_module(data.get("module", ""), data.get("text", ""), data.get("meta"))
    success = result.pop("ok", False)
    status = result.get("status")
    http_status = 200 if success else (400 if status == "INVALID_INPUT" else 503 if status == "UNAVAILABLE" else 502)
    return jsonify({"success": success, **result}), http_status


@ai_bp.route("/ai/learn", methods=["GET"])
@require_auth
def ai_learn():
    return jsonify({"success": True, **service.learning_stats(limit=int(request.args.get("limit", 50)))})


@ai_bp.route("/ai/shadow", methods=["GET", "POST"])
@require_auth
def ai_shadow():
    if request.method == "POST":
        data = request.get_json() or {}
        r = shadow.add_suggestion(
            data.get("module", ""), data.get("title", ""), data.get("payload"),
            rationale=data.get("rationale"), kind=data.get("kind", "suggestion"))
        if r.get("ok"):
            log_audit("ai_shadow_add", "ai", r.get("id"), f"AI建议入影子队列: {data.get('title','')[:40]}")
        return jsonify(r)
    status = request.args.get("status", "pending")
    return jsonify({"success": True, "stats": shadow.stats(),
                    "items": shadow.list_suggestions(status, int(request.args.get("limit", 100)))})


@ai_bp.route("/ai/shadow/<sid>/decide", methods=["POST"])
@require_auth
def ai_shadow_decide(sid):
    user = get_current_user() or {}
    role = user.get("role", "user")
    if role not in ("owner", "admin"):
        return jsonify({"success": False, "error": "仅主账号/管理员可审核 AI 建议"}), 403
    data = request.get_json() or {}
    r = shadow.decide(sid, data.get("decision", ""), user.get("username", ""), data.get("note", ""))
    if r.get("ok"):
        log_audit("ai_shadow_decide", "ai", sid, f"AI建议决策={data.get('decision')}")
    return jsonify(r)


@ai_bp.route("/ai/shadow/stats", methods=["GET"])
@require_auth
def ai_shadow_stats():
    return jsonify({"success": True, "stats": shadow.stats()})


# Persistent conversation routes live in the existing AI Hub, not a second chat service.
def _conversation_response(call):
    try:
        return jsonify({'ok': True, **call()})
    except PermissionError as exc:
        return jsonify({'ok': False, 'code': str(exc)}), 403
    except TypeError:
        return jsonify({'ok': False, 'code': 'CONVERSATION_FIELDS_INVALID'}), 400
    except ValueError as exc:
        return jsonify({'ok': False, 'code': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'ok': False, 'code': str(exc)}), 409
    except Exception:
        return jsonify({'ok': False, 'code': 'CONVERSATION_STORAGE_UNAVAILABLE'}), 503


def _conversation_body(allowed):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise ValueError('CONVERSATION_FIELDS_INVALID')
    return data


@ai_bp.route('/ai/workspace-draft', methods=['GET', 'PUT'])
def ai_workspace_draft():
    from . import conversations as owner
    def call():
        writing = request.method == 'PUT'
        actor = owner.current_actor('write' if writing else 'read')
        if not writing:
            return owner.workspace_draft(actor, scope_key=request.args.get('scope_key'))
        data = _conversation_body({'scope_key', 'text', 'expected_revision'})
        if set(data) != {'scope_key', 'text', 'expected_revision'} or data['text'] is None:
            raise ValueError('WORKSPACE_DRAFT_INVALID')
        return owner.workspace_draft(actor, **data)
    return _conversation_response(call)


@ai_bp.route('/ai/conversations', methods=['GET', 'POST'])
def ai_conversations_list_create():
    from . import conversations as owner
    def call():
        actor = owner.current_actor('read' if request.method == 'GET' else 'write')
        if request.method == 'GET':
            return owner.list_conversations(actor, limit=int(request.args.get('limit',30)), offset=int(request.args.get('offset',0)))
        data = _conversation_body({'title'})
        return {'conversation': owner.create_conversation(actor, title=data.get('title',''))}
    return _conversation_response(call)


@ai_bp.route('/ai/conversations/<conversation_id>', methods=['GET', 'PATCH'])
def ai_conversation_read_update(conversation_id):
    from . import conversations as owner
    def call():
        actor = owner.current_actor('read' if request.method == 'GET' else 'write')
        if request.method == 'GET':
            return {'conversation': owner.read_conversation(actor, conversation_id,
                after_sequence=int(request.args.get('after_sequence',0)), limit=int(request.args.get('limit',30)))}
        data = _conversation_body({'title','state','expected_revision'})
        return {'conversation': owner.update_conversation(actor, conversation_id, **data)}
    return _conversation_response(call)


@ai_bp.route('/ai/conversations/<conversation_id>/turns', methods=['POST'])
def ai_conversation_append(conversation_id):
    from . import conversations as owner
    def call():
        data = _conversation_body({'text','idempotency_key','expected_revision'})
        return owner.append_user_turn(owner.current_actor('write'), conversation_id, **data)
    return _conversation_response(call)


@ai_bp.route('/ai/conversations/<conversation_id>/context', methods=['GET', 'PUT'])
def ai_conversation_context(conversation_id):
    from . import conversations as owner
    def call():
        actor = owner.current_actor('read' if request.method == 'GET' else 'write')
        if request.method == 'GET':
            if (set(request.args) - {'query', 'limit', 'offset', 'snapshot', 'source_reference'}
                    or any(len(request.args.getlist(key)) != 1 for key in request.args)
                    or 'source_reference' in request.args and len(request.args) != 1
                    or set(request.args) - {'source_reference'} and 'query' not in request.args):
                raise ValueError('CONVERSATION_CONTEXT_SEARCH_INVALID')
            options = {}
            if 'query' in request.args:
                numbers = [request.args.get('limit', '30'), request.args.get('offset', '0')]
                if any(not value.isascii() or not value.isdecimal() for value in numbers):
                    raise ValueError('MEMORY_SEARCH_INVALID')
                options = {'query': request.args['query'], 'limit': int(numbers[0]), 'offset': int(numbers[1]),
                           'expected_snapshot': request.args.get('snapshot')}
            if 'source_reference' in request.args:
                import json
                if len(request.args['source_reference']) > 4096:
                    raise ValueError('MEMORY_REFERENCE_INVALID')
                options['source_reference'] = json.loads(request.args['source_reference'])
                if type(options['source_reference']) is not dict:
                    raise ValueError('MEMORY_REFERENCE_INVALID')
            return owner.read_context(actor, conversation_id, **options)
        data = _conversation_body({'value', 'idempotency_key', 'expected_revision', 'source_references'})
        if 'source_references' in data and type(data['source_references']) is not list:
            raise ValueError('CONVERSATION_SOURCE_REFERENCES_INVALID')
        return owner.update_context(actor, conversation_id, **data)
    return _conversation_response(call)


@ai_bp.route('/ai/conversations/<conversation_id>/tasks', methods=['POST'])
def ai_conversation_attach_task(conversation_id):
    from . import conversations as owner
    def call():
        data = _conversation_body({'task_id','idempotency_key','expected_revision'})
        return owner.attach_task(owner.current_actor('write'), conversation_id, **data)
    return _conversation_response(call)


@ai_bp.route('/ai/conversations/<conversation_id>/turns/<turn_id>/respond', methods=['POST'])
def ai_conversation_respond(conversation_id, turn_id):
    from . import conversations as owner
    def call():
        data = _conversation_body({'operation','idempotency_key','expected_revision','retry_confirmed','confirmed','external_approval'})
        actor = owner.current_actor('write')
        operation = data.pop('operation', 'respond')
        if operation == 'interrupt':
            if set(data) - {'expected_revision','confirmed'}:
                raise ValueError('CONVERSATION_FIELDS_INVALID')
            return owner.interrupt_response(actor, conversation_id, turn_id, **data)
        if operation != 'respond' or 'confirmed' in data:
            raise ValueError('CONVERSATION_OPERATION_INVALID')
        return owner.respond(actor, conversation_id, turn_id, **data)
    return _conversation_response(call)


def authorize_conversation_root_request():
    """Exact full-app perimeter delegation; Owner rechecks every DB operation."""
    from . import conversations as owner
    entries = {
        'v4.v4_ai.ai_workspace_draft': ('/v4/ai/workspace-draft', {'GET','PUT'}),
        'v4.v4_ai.ai_conversations_list_create': ('/v4/ai/conversations', {'GET','POST'}),
        'v4.v4_ai.ai_conversation_read_update': ('/v4/ai/conversations/<conversation_id>', {'GET','PATCH'}),
        'v4.v4_ai.ai_conversation_append': ('/v4/ai/conversations/<conversation_id>/turns', {'POST'}),
        'v4.v4_ai.ai_conversation_context': ('/v4/ai/conversations/<conversation_id>/context', {'GET','PUT'}),
        'v4.v4_ai.ai_conversation_attach_task': ('/v4/ai/conversations/<conversation_id>/tasks', {'POST'}),
        'v4.v4_ai.ai_conversation_respond': ('/v4/ai/conversations/<conversation_id>/turns/<turn_id>/respond', {'POST'}),
    }
    entry = entries.get(request.endpoint)
    if not entry or request.url_rule is None or request.url_rule.rule != entry[0] or request.method not in entry[1]:
        return False
    con = None
    try:
        action = 'read' if request.method == 'GET' else 'write'
        actor = owner.current_actor(action)
        con = owner._connect()
        identifier = (request.view_args or {}).get('conversation_id')
        if identifier:
            owner._authorize(con, identifier, actor, action)
        else:
            owner._identity(actor, action, con)
        return True
    except Exception:
        return False
    finally:
        if con is not None:
            con.close()
