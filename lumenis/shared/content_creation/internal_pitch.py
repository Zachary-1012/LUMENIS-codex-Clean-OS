"""Bind existing Word/ShotPlan, TaskEngine and SavedWork owners for internal work.

No schema creation, alternate store, external publishing or model route.
Permission is always resolved by the existing owner from the live request.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from urllib.parse import urlsplit
import re
import unicodedata
import tempfile
from functools import lru_cache
from pathlib import Path

from ai_task_engine import TaskEngine
from lumenis.shared.content_creation.contracts import AudiovisualPlan, Shot, ShotPlan, resolve_creation_upstream
from lumenis.shared.database import get_repository
from lumenis.shared.reporting import saved_work as work
from lumenis.system.security.permission import OperationType

CONTRACT = {"id": "lumenis.internal-pitch", "version": "1",
            "required_payload_paths": ["manuscript", "shot_plan", "truth_state"]}
MANUSCRIPT_PROFILE = "manuscript-only/v2"
MANUSCRIPT_CONTRACT = {"id": "lumenis.internal-pitch", "version": "2",
                       "required_payload_paths": ["manuscript", "input_manifest", "truth_state"]}
SOURCE_PROFILE = "source-bound/v3"
SOURCE_CONTRACT = {"id": "lumenis.internal-pitch", "version": "3",
                   "required_payload_paths": ["manuscript", "upstream_binding", "truth_state"]}
AUTHORING_PROFILE = "authored-manuscript/v4"
AUTHORING_CONTRACT = {"id": "lumenis.internal-pitch", "version": "4",
                      "required_payload_paths": ["manuscript", "truth_state"]}
AV_PLAN_PROFILE = "audiovisual-planning/v5"
AV_PLAN_CONTRACT = {"id": "lumenis.internal-pitch", "version": "5",
                    "required_payload_paths": ["manuscript", "audiovisual_plan", "truth_state"]}
OWNED_PROFILE = "owned-creation/v6"
MANUSCRIPT_LANGUAGES = frozenset({'zh','en','ko','ja','fr','de','es','pt','ru','ar','hi','id'})
INPUT_MANIFEST_SCHEMA = "lumenis.internal-pitch-input-manifest/v1"
_SCOPE = ("domain_id", "subject_id", "brand_focus_id", "global_scope")


def _document_basename(value):
    # Equivalent bounded display-name handling to Importer path.name, without
    # opening a file or importing an admission owner. Preserve Unicode exactly.
    if not isinstance(value, str) or not 5 < len(value) <= 185:
        return False
    if (value != value.strip() or any(char in '<>:"/\\|?*' for char in value)
            or any(unicodedata.category(char).startswith("C") for char in value)
            or not value.lower().endswith(".docx")):
        return False
    stem = value[:-5]
    if not stem or stem.endswith((" ", ".")) or stem.split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *{f"COM{number}" for number in range(1, 10)},
        *{f"LPT{number}" for number in range(1, 10)},
    }:
        return False
    return True


def _input_manifest(manifest):
    """Retain operator declarations/full text, never ingest or authorize sources.

    Original binary size/hash declarations are not verified file receipts.
    W5's existing Importer retains/admit originals; all formal refs stay NULL.
    """
    if (not isinstance(manifest, dict) or set(manifest) != {"schema", "state", "materials"}
            or manifest["schema"] != INPUT_MANIFEST_SCHEMA or manifest["state"] != "NOT_INGESTED"
            or not isinstance(manifest["materials"], list) or not 1 <= len(manifest["materials"]) <= 16):
        raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
    fields = {"material_id", "role", "filename", "size_bytes", "sha256", "text", "text_sha256",
              "source_url", "published_at", "captured_at", "source_ref", "evidence_ref", "source_use_ref"}
    seen = set()
    for material in manifest["materials"]:
        has_origin = isinstance(material, dict) and "source_origin" in material
        if (not isinstance(material, dict) or set(material) != fields | ({"source_origin"} if has_origin else set())
                or not isinstance(material["material_id"], str)
                or re.fullmatch(r"[A-Za-z0-9_-]{1,80}", material["material_id"]) is None
                or material["material_id"] in seen
                or not isinstance(material["role"], str) or material["role"] not in {"brief", "application_form", "reference"}
                or not _document_basename(material["filename"])
                or type(material["size_bytes"]) is not int or not 0 < material["size_bytes"] <= 8 * 1024 * 1024
                or not isinstance(material["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", material["sha256"]) is None
                or not isinstance(material["text"], str) or not material["text"].strip()
                or len(material["text"].encode("utf-8")) > 512 * 1024
                or material["text_sha256"] != hashlib.sha256(material["text"].encode("utf-8")).hexdigest()):
            raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
        if any(material[key] is not None for key in ("source_ref", "evidence_ref", "source_use_ref")):
            raise ValueError("INTERNAL_PITCH_SOURCE_BINDING_REQUIRED")
        url = material["source_url"]
        if url is None:
            # This is an unverified declaration of the existing Importer's
            # approved-file origin shape, not a new upload or approval receipt.
            origin = material.get("source_origin")
            valid_url = (isinstance(origin, dict) and set(origin) == {"kind", "ref"}
                         and origin["kind"] == "approved-file" and isinstance(origin["ref"], str)
                         and re.fullmatch(r"[A-Za-z0-9_-]{8,128}", origin["ref"]) is not None)
        else:
            try:
                parts = urlsplit(url) if isinstance(url, str) else None
                valid_url = (not has_origin and parts is not None and parts.scheme == "https"
                             and parts.hostname and not parts.username and not parts.password)
            except ValueError:
                valid_url = False
        if not valid_url:
            raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
        for key in ("published_at", "captured_at"):
            stamp = material[key]
            if stamp is None:
                continue
            try:
                parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")) if isinstance(stamp, str) else None
                valid_stamp = parsed is not None and parsed.utcoffset() is not None
            except (ValueError, OverflowError):
                valid_stamp = False
            if not valid_stamp:
                raise ValueError("INTERNAL_PITCH_INPUT_MANIFEST_INVALID")
        seen.add(material["material_id"])
    return manifest


def _contract(value):
    # Absence of profile identifies exact historical v1 input. Never add new
    # keys to old task hashes or reinterpret a committed ShotPlan work.
    if "profile" not in value:
        return CONTRACT
    if value["profile"] == OWNED_PROFILE:
        result = value.get("result_contract")
        if result not in (CONTRACT, MANUSCRIPT_CONTRACT, SOURCE_CONTRACT, AUTHORING_CONTRACT, AV_PLAN_CONTRACT):
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        return result
    if value["profile"] == AV_PLAN_PROFILE:
        if (any(key in value for key in ("input_manifest", "upstream_binding", "upstream_ref"))
                or "shot_plan" not in value):
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        plan = AudiovisualPlan.from_dict(value["shot_plan"]).to_dict()
        for output in plan["outputs"]:
            media_plan = output["plan"]
            if media_plan is None:
                continue
            if output["medium"] == "video":
                unbound = (media_plan["brief_ref"] or media_plan["evidence_refs"]
                           or any(shot["evidence_refs"] for shot in media_plan["shots"]))
            else:
                unbound = any(segment["evidence_refs"] for segment in media_plan["segments"])
            if unbound:
                raise ValueError("INTERNAL_PITCH_SOURCE_BINDING_REQUIRED")
        return AV_PLAN_CONTRACT
    if value["profile"] == AUTHORING_PROFILE:
        if any(key in value for key in ("shot_plan", "input_manifest", "upstream_binding", "upstream_ref")):
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        return AUTHORING_CONTRACT
    if value["profile"] == SOURCE_PROFILE:
        if "shot_plan" in value or "input_manifest" in value or not isinstance(value.get("upstream_binding"), dict):
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        return SOURCE_CONTRACT
    if value["profile"] != MANUSCRIPT_PROFILE or "shot_plan" in value:
        raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
    _input_manifest(value["input_manifest"])
    return MANUSCRIPT_CONTRACT


@lru_cache(maxsize=1)
def engine():
    return TaskEngine(auto_init_db=False)


def _context(actor, scope, action, *, connection=None):
    # Reuse the SavedWork owner for either an explicit domain or actor-owned
    # Shared workspace. A selector never replaces the live Permission grant.
    options = {"connection": connection} if connection is not None else {}
    return work.authorize_saved_work(actor, scope, action=action, **options)


def _permission(actor, scope, resource, *, connection=None):
    _context(actor, scope, "write", connection=connection)
    options = {"connection": connection} if connection is not None else {}
    return work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource, **options)


def _check_upstream(value, *, actor, scope, connection=None):
    if value.get("profile") == OWNED_PROFILE or _contract(value) != SOURCE_CONTRACT:
        return None
    sealed = value["upstream_binding"]
    current = resolve_creation_upstream(sealed["reference"], actor=actor, scope=scope, connection=connection)
    if work._digest(current) != work._digest(sealed):
        raise ValueError("INTERNAL_PITCH_UPSTREAM_CHANGED")
    return current


def _check_saved_upstream(payload, *, actor, scope, connection=None):
    sealed = payload.get('upstream_binding')
    if sealed is None:
        return None
    current = resolve_creation_upstream(sealed['reference'], actor=actor, scope=scope, connection=connection)
    if work._digest(current) != work._digest(sealed):
        raise ValueError('INTERNAL_PITCH_UPSTREAM_CHANGED')
    return current


def _revision_sections(document):
    """Positional identities are always bound to the exact immutable parent."""
    return [{"section_id": "section-" + work._digest({"work_id": document["work_id"], "index": index})[:24],
             "heading": section["heading"], "body": section["body"]}
            for index, section in enumerate(document["payload"]["manuscript"]["sections"])]


def generation_parent(value, *, actor, scope, latest=True, connection=None):
    """Read the real producing Task and parent; a client manuscript is not a parent."""
    from contextlib import nullcontext
    identity = (value.get("work_id"), value.get("previous_artifact_id"), value.get("expected_draft_digest"))
    selected = value["generation"]["selected_section_ids"]
    if not any(item is not None for item in identity):
        if selected:
            raise ValueError("CREATION_REVISION_PARENT_REQUIRED")
        return None
    if any(item is None for item in identity) or not selected:
        raise ValueError("CREATION_REVISION_SELECTION_REQUIRED")
    context = _context(actor, scope, "read", connection=connection)
    reader = nullcontext(connection) if connection is not None else get_repository().connection(read_only=True, wal=False)
    with reader as con:
        parent = work._read(con, value["previous_artifact_id"], context, actor)
        document = parent["document"]
        if (document["work_id"] != value["work_id"] or document["draft_digest"] != value["expected_draft_digest"]
                or document["kind"] != "report" or "manuscript" not in document["payload"]
                or len(document.get("attachments", [])) != 1):
            raise ValueError("CREATION_PARENT_INVALID")
        producer = engine().get_pitch_task(document["task_id"], owner_context=context, connection=con)
        if (producer["status"] != "succeeded" or producer["result"]["artifact_id"] != parent["artifact"]["artifact_id"]
                or producer["result"]["sha256"] != parent["artifact"]["sha256"]
                or _contract(producer["context"]["input"]) != document["contract"]):
            raise ValueError("CREATION_PARENT_PRODUCER_INVALID")
        _check_upstream(producer["context"]["input"], actor=actor, scope=scope, connection=con)
        _check_saved_upstream(document['payload'], actor=actor, scope=scope, connection=con)
        if latest and work._versions(con, document["work_id"], context, actor)[-1]["artifact"]["artifact_id"] != parent["artifact"]["artifact_id"]:
            raise ValueError("WORK_REVISION_CONFLICT")
        sections = _revision_sections(document)
        if set(selected) - {item["section_id"] for item in sections}:
            raise ValueError("CREATION_SECTION_NOT_IN_PARENT")
        if value['generation']['brief']['language'] != document['payload']['manuscript']['language']:
            raise ValueError('CREATION_REVISION_LANGUAGE_CHANGED')
        original = work._read_attachment(con, document["attachments"][0], context, document["work_id"], actor=actor)
        from lumenis.importer.office_package import OfficePackage
        package = OfficePackage(original, filename="document.docx", media_type=document["attachments"][0]["media_type"])
        refs = {item["evidence_id"] for item in document["citations"]}
        bindings = document["payload"].get("creation", {}).get("source_bindings", [])
        refs.update(item["evidence_id"] for item in bindings if type(item.get('evidence_id')) is int)
        artifacts = [{'artifact_id':item['source_artifact_ref'],'sha256':item['source_artifact_sha256']}
                     for item in bindings if item.get('source_kind') == 'private_saved_source']
        return {"artifact_id":parent["artifact"]["artifact_id"], "sha256":parent["artifact"]["sha256"],
                "work_id":document["work_id"], "draft_digest":document["draft_digest"], "contract":document["contract"],
                "manuscript":document["payload"]["manuscript"], "sections":sections,
                "attachment":document["attachments"][0], "office_package_sha256":package.sha256,
                "source_evidence_refs":sorted(refs), 'source_artifacts':artifacts}


def _prepare_owned_pitch(*, manuscript, request_id, actor, scope, context, generation, citations,
                         work_id, previous_artifact_id, expected_draft_digest, shot_plan, input_manifest, upstream_ref):
    from content_generation import normalize_creation_options, _creation_sources, _creation_private_sources
    if manuscript is not None or citations not in (None, []) or any(item is not None for item in (shot_plan, input_manifest, upstream_ref)):
        raise ValueError("CREATION_AI_INPUT_MUST_BE_BRIEF")
    value = {"profile":OWNED_PROFILE,"manuscript":None,"generation":normalize_creation_options(generation),
             "citations":[],"work_id":work_id,"previous_artifact_id":previous_artifact_id,
             "expected_draft_digest":expected_draft_digest}
    parent = generation_parent(value, actor=actor, scope=scope, latest=False)
    value["result_contract"] = parent["contract"] if parent else AUTHORING_CONTRACT
    value["title"] = parent["manuscript"]["title"] if parent else value["generation"]["brief"]["title"]
    def validate_inputs():
        current = generation_parent(value, actor=actor, scope=scope, latest=False)
        refs = sorted(set(value["generation"]["source_evidence_refs"]) | set(current["source_evidence_refs"] if current else []))
        _creation_sources(refs, actor=actor, scope=scope)
        artifacts = list(value['generation']['source_artifacts']) + (current['source_artifacts'] if current else [])
        _creation_private_sources(list({item['artifact_id']:item for item in artifacts}.values()), actor=actor, scope=scope)
    validate_inputs()
    value = json.loads(work._json(value))
    work._safe_payload(value)
    task_context = {"schema":"lumenis.internal-pitch-task/v1", "owner_context":context,
                    "request_id":request_id,"input_hash":work._digest(value),"input":value}
    resource = "internal-pitch-prepare:v1:" + work._digest(task_context)
    _permission(actor, scope, resource)
    with work.staging_write(resource):
        def before_commit():
            _permission(actor, scope, resource)
            validate_inputs()
        task = engine().create_pitch_task(task_context, before_commit=before_commit)
    return read_internal_pitch(task["task_id"], actor=actor, scope=scope)


def prepare_internal_pitch(*, manuscript, request_id, actor, scope, shot_plan=None,
                           citations=None, work_id=None, previous_artifact_id=None,
                           expected_draft_digest=None, profile=None, input_manifest=None, upstream_ref=None, generation=None):
    """Seal an existing contract or an independently authored manuscript."""
    context = _context(actor, scope, "write")
    if profile == OWNED_PROFILE:
        return _prepare_owned_pitch(manuscript=manuscript, request_id=request_id, actor=actor, scope=scope,
            context=context, generation=generation, citations=citations, work_id=work_id,
            previous_artifact_id=previous_artifact_id, expected_draft_digest=expected_draft_digest,
            shot_plan=shot_plan, input_manifest=input_manifest, upstream_ref=upstream_ref)
    if generation is not None:
        raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
    value = {"manuscript": manuscript, "citations": citations if citations is not None else [], "work_id": work_id,
             "previous_artifact_id": previous_artifact_id, "expected_draft_digest": expected_draft_digest}
    if profile == SOURCE_PROFILE and shot_plan is None and input_manifest is None:
        if work._shared_context(context):
            raise ValueError("INTERNAL_PITCH_SOURCE_SCOPE_REQUIRED")
        binding = resolve_creation_upstream(upstream_ref, actor=actor, scope=scope)
        inherited = binding["document"].get("citations", [])
        merged = inherited + value["citations"]
        value["citations"] = list({work._digest(item): item for item in merged}.values())
        value.update(profile=profile, upstream_binding=binding)
    elif profile is None:
        if input_manifest is not None or upstream_ref is not None:
            raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
        value["shot_plan"] = shot_plan
    elif profile == MANUSCRIPT_PROFILE and shot_plan is None and upstream_ref is None:
        value.update(profile=profile, input_manifest=input_manifest)
    elif (profile == AUTHORING_PROFILE and shot_plan is None
          and input_manifest is None and upstream_ref is None):
        value["profile"] = profile
    elif profile == AV_PLAN_PROFILE and input_manifest is None and upstream_ref is None:
        value.update(profile=profile, shot_plan=AudiovisualPlan.from_dict(shot_plan).to_dict())
    else:
        raise ValueError("INTERNAL_PITCH_PROFILE_INVALID")
    value = json.loads(work._json(value))
    work._safe_payload(value)
    manuscript = value["manuscript"]
    if (not isinstance(manuscript, dict) or set(manuscript) != {"title", "summary", "sections", "language", "authorship"}
            or not isinstance(manuscript["title"], str) or not 0 < len(manuscript["title"].strip()) <= 300
            or not isinstance(manuscript["summary"], str) or not manuscript["summary"].strip()
            or not isinstance(manuscript["language"], str) or manuscript["language"] not in MANUSCRIPT_LANGUAGES
            or not isinstance(manuscript["authorship"], str) or manuscript["authorship"] not in {"assisted", "user_supplied"}
            or not isinstance(manuscript["sections"], list) or not 1 <= len(manuscript["sections"]) <= 64):
        raise ValueError("INTERNAL_PITCH_MANUSCRIPT_INVALID")
    for section in manuscript["sections"]:
        if (not isinstance(section, dict) or set(section) != {"heading", "body"}
                or any(not isinstance(section[k], str) or not section[k].strip() for k in ("heading", "body"))):
            raise ValueError("INTERNAL_PITCH_MANUSCRIPT_INVALID")
    if not isinstance(value["citations"], list):
        raise ValueError("INTERNAL_PITCH_CITATIONS_INVALID")
    if _contract(value) == SOURCE_CONTRACT:
        _check_upstream(value, actor=actor, scope=scope)
    elif _contract(value) == MANUSCRIPT_CONTRACT:
        _input_manifest(value["input_manifest"])
    elif _contract(value) in (AUTHORING_CONTRACT, AV_PLAN_CONTRACT):
        pass
    else:
        shot = value["shot_plan"]
        if (not isinstance(shot, dict) or set(shot) != {"shots", "brief_ref", "evidence_refs"}
                or not isinstance(shot["shots"], list) or not 1 <= len(shot["shots"]) <= 128
                or any(not isinstance(s, dict) for s in shot["shots"])
                or not isinstance(value["citations"], list)):
            raise ValueError("INTERNAL_PITCH_SHOT_PLAN_INVALID")
        # Current W4 input refs are empty. The actual canonical source-use reader
        # must bind nonempty refs; a local work locator never substitutes for one.
        if shot["brief_ref"] != "" or shot["evidence_refs"] or any(s.get("evidence_refs") for s in shot["shots"]):
            raise ValueError("INTERNAL_PITCH_SOURCE_BINDING_REQUIRED")
        try:
            plan = ShotPlan(tuple(Shot(**s) for s in shot["shots"]))
            plan.validate()
        except (TypeError, ValueError) as exc:
            raise ValueError("INTERNAL_PITCH_SHOT_PLAN_INVALID") from exc
        if plan.to_dict() != shot:
            raise ValueError("INTERNAL_PITCH_SHOT_PLAN_INVALID")
    value["title"] = manuscript["title"]
    task_context = {"schema": "lumenis.internal-pitch-task/v1", "owner_context": context,
                    "request_id": request_id, "input_hash": work._digest(value), "input": value}
    resource = "internal-pitch-prepare:v1:" + work._digest(task_context)
    _permission(actor, scope, resource)
    with work.staging_write(resource):
        def before_prepare_commit():
            _permission(actor, scope, resource)
            _check_upstream(value, actor=actor, scope=scope)
        task = engine().create_pitch_task(task_context, before_commit=before_prepare_commit)
    return read_internal_pitch(task["task_id"], actor=actor, scope=scope)


def _manuscript_markdown(manuscript):
    return manuscript['title'] + '\n\n' + manuscript['summary'] + '\n\n' + '\n\n'.join(
        '## ' + item['heading'] + '\n\n' + item['body'] for item in manuscript['sections'])


def _assemble_creation(generated, *, task_id, actor, scope):
    output, material = generated['output'], generated['material']
    selected, parent = material['selected_section_ids'], material['parent']
    identities = [item['section_id'] for item in output['sections']]
    if len(set(identities)) != len(identities) or selected and set(identities) != set(selected):
        raise ValueError('CREATION_OUTPUT_SECTION_SCOPE_INVALID')
    replacements, changes = {}, []
    if parent:
        if material['brief']['language'] != parent['manuscript']['language']:
            raise ValueError('CREATION_REVISION_LANGUAGE_CHANGED')
        manuscript = json.loads(work._json(parent['manuscript']))
        by_id = {item['section_id']:item for item in output['sections']}
        for index, original in enumerate(parent['sections']):
            if original['section_id'] not in selected:
                continue
            item = by_id[original['section_id']]
            replacement = {key:item[key] for key in ('heading','body')}
            replacements[index] = replacement
            changes.append({'section_id':original['section_id'],'reason':item['reason'],
                'before_sha256':work._digest(manuscript['sections'][index]),'after_sha256':work._digest(replacement)})
            manuscript['sections'][index] = replacement
    else:
        manuscript = {'title':output['title'], 'summary':output['summary'], 'language':material['brief']['language'],
                      'authorship':'assisted','sections':[{key:item[key] for key in ('heading','body')} for item in output['sections']]}
        task = engine().get_pitch_task(task_id, owner_context=_context(actor, scope, 'write'))
        assigned_work = 'WORK-' + work._digest({'context':task['context']['owner_context'],
                                               'request_id':task['context']['request_id']})[:24]
        identities = _revision_sections({'work_id':assigned_work,'payload':{'manuscript':manuscript}})
        changes = [{'section_id':identity['section_id'],'reason':item['reason'],'before_sha256':None,
                    'after_sha256':work._digest({key:item[key] for key in ('heading','body')})}
                   for identity,item in zip(identities,output['sections'])]
    manuscript['authorship'] = 'assisted'
    if not 0 < len(manuscript['title'].strip()) <= 300:
        raise ValueError('CREATION_OUTPUT_TITLE_INVALID')
    citations, private_quotes = [], []
    for quote in output['source_quotes']:
        index, start, end = quote['source_index'], quote['start'], quote['end']
        if not 0 <= index < len(material['sources']) or not 0 <= start < end <= len(material['sources'][index]['text']):
            raise ValueError('CREATION_OUTPUT_QUOTE_UNGROUNDED')
        source = material['sources'][index]
        if source.get('source_kind') == 'private_saved_source':
            private_quotes.append({'source_artifact_ref':source['source_artifact_ref'],
                'source_artifact_sha256':source['source_artifact_sha256'],'start':start,'end':end,
                'quote':source['text'][start:end],'allowed_use':'private_custody_and_analysis','fact_verification':'NOT_VERIFIED'})
        else:
            citations.append({'evidence_id':source['evidence_id'],'start':start,'end':end,'quote':source['text'][start:end]})
    payload, office_receipt, original = {}, None, None
    if parent:
        context = _context(actor, scope, 'read')
        with get_repository().connection(read_only=True, wal=False) as con:
            prior = work._read(con, parent['artifact_id'], context, actor)
            payload = json.loads(work._json(prior['document']['payload']))
            old_markdown, new_markdown = prior['document']['markdown'], _manuscript_markdown(manuscript)
            from difflib import SequenceMatcher
            blocks = SequenceMatcher(None, old_markdown, new_markdown).get_matching_blocks()
            for inherited in prior['document']['citations']:
                inherited = json.loads(work._json(inherited))
                if 'claim_links' in inherited:
                    retained = []
                    for link in inherited['claim_links']:
                        for block in blocks:
                            if block.a <= link['start'] < link['end'] <= block.a + block.size:
                                retained.append({**link,'start':block.b+link['start']-block.a,'end':block.b+link['end']-block.a})
                                break
                    # A changed claim is no longer asserted to have the old link.
                    inherited['claim_links'] = retained
                citations.append(inherited)
            original = work._read_attachment(con, parent['attachment'], context, parent['work_id'], actor=actor)
        from lumenis.importer.office_package import OfficePackage
        from scripts.pitch_export import _manuscript_document
        notice = _manuscript_document(manuscript).paragraphs[2].text
        result = OfficePackage(original, filename='document.docx', media_type=parent['attachment']['media_type']).revise_word_manuscript(
            parent['manuscript'], replacements, expected_package_sha256=parent['office_package_sha256'], authorship_notice=notice)
        original, office_receipt = result['content'], result['receipt']
    citations = list({work._digest(item):item for item in citations}.values())
    bindings = [{key:value for key,value in source.items() if key != 'text'} for source in material['sources']]
    payload.update(manuscript=manuscript, truth_state={
        'source_admission':'VERIFIED_SOURCE_USE' if bindings else 'USER_BRIEF_ONLY',
        'citation_admission':'SIGNED_CITATIONS_BOUND' if citations else 'NO_SIGNED_QUOTE',
        'external_fact_verification':'SOURCE_CLAIMS_NOT_INDEPENDENTLY_VERIFIED',
        'owned_model_execution':'COMPLETED','professional_quality':'NOT_EVALUATED',
        'external_effect':'NOT_PERFORMED','business_outcome':'NOT_OBSERVED'},
        creation={'schema':'lumenis.owned-creation/v1','operation':'revise_selected_sections' if parent else 'create',
            'brief':material['brief'],'source_bindings':bindings,
            'input_revision_sha256':generated['request'].input_revision_sha256,
            'source_binding_sha256':generated['request'].source_binding_sha256,
            'model_output_sha256':generated['output_sha256'],'provenance':generated['provenance'],
            'source_quotes':citations,'private_source_quotes':private_quotes,'changes':changes,'limitations':output['limitations'],
            'parent':{key:parent[key] for key in ('artifact_id','sha256','draft_digest','work_id','office_package_sha256')} if parent else None,
            'office_edit_receipt':office_receipt,'execution_evidence':{'source':'shared_content',
                'feature_id':'CONTENT_CREATION_EXECUTION','asset_id':task_id}})
    return payload, citations, original


def inspect_saved_pitch(committed, *, actor, scope, connection=None):
    """Reopen needs read/source rights and a real signed execution, never AI_CALL."""
    from contextlib import nullcontext
    from content_generation import validate_creation_material_sources
    from lumenis.shared.evidence import store
    document = committed['document']
    if not isinstance(document.get('task_id'), str) or not document['task_id'].startswith('task-pitch-'):
        return {}
    context = _context(actor, scope, 'read', connection=connection)
    task = engine().get_pitch_task(document['task_id'], owner_context=context, connection=connection)
    if task['status'] != 'succeeded' or task['result']['artifact_id'] != committed['artifact']['artifact_id']:
        raise ValueError('INTERNAL_PITCH_RECEIPT_INTEGRITY_FAILED')
    result = {'revision_sections':_revision_sections(document)}
    upstream = _check_saved_upstream(document['payload'], actor=actor, scope=scope, connection=connection)
    if upstream is not None:
        result['research_return_ref'] = upstream['return_ref']
    if task['context']['input'].get('profile') != OWNED_PROFILE:
        return result
    creation = document['payload'].get('creation')
    if not isinstance(creation, dict) or creation.get('schema') != 'lumenis.owned-creation/v1':
        raise ValueError('CREATION_EXECUTION_INTEGRITY_FAILED')
    reader = nullcontext(connection) if connection is not None else get_repository().connection(read_only=True, wal=False)
    with reader as con:
        validate_creation_material_sources(creation['source_bindings'], actor=actor, scope=scope, connection=con)
        cursor = con.execute('SELECT * FROM app_evidence_records WHERE source=? AND feature_id=? AND asset_id=?',
            ('shared_content','CONTENT_CREATION_EXECUTION',document['task_id']))
        rows = [dict(zip((item[0] for item in cursor.description), row)) for row in cursor.fetchall()]
        if len(rows) != 1 or not store.verify_evidence_record_integrity(rows[0]):
            raise ValueError('CREATION_EXECUTION_EVIDENCE_INVALID')
        evidence = rows[0]
        if (evidence['provider'] != 'content_generation' or evidence['version'] != 'content-creation-source-use/v1'
                or evidence['result'] != 'GENERATED_DERIVED_NOT_PROFESSIONALLY_ACCEPTED' or evidence['status'] != 'derived'
                or json.loads(evidence['inputs_json']) != {'context':context,'input_revision_sha256':creation['input_revision_sha256']}
                or json.loads(evidence['outputs_json']) != {'artifact_id':committed['artifact']['artifact_id'],
                    'artifact_sha256':committed['artifact']['sha256'],'output_sha256':creation['model_output_sha256'],
                    'provenance':creation['provenance']}):
            raise ValueError('CREATION_EXECUTION_EVIDENCE_INVALID')
        result['creation_evidence'] = {'evidence_id':evidence['id'],'integrity_digest':evidence['integrity_digest']}
    return result


def run_internal_pitch(task_id, *, actor, scope):
    """Actually produce Word, then atomically commit the work and Task result."""
    context = _context(actor, scope, "write")
    task = engine().get_pitch_task(task_id, owner_context=context)
    if task["status"] == "succeeded":
        return read_internal_pitch(task_id, actor=actor, scope=scope)
    resource = "internal-pitch-run:v1:" + work._digest({"task_id": task_id, "input_hash": task["context"]["input_hash"]})
    _permission(actor, scope, resource)
    _check_upstream(task["context"]["input"], actor=actor, scope=scope)
    with work.staging_write(resource):
        if task["status"] in {"running", "cancel_requested"}:
            engine().reconcile_pitch_worker(task_id, owner_context=context,
                                            before_commit=lambda: _permission(actor, scope, resource))
        task = engine().claim_pitch_task(task_id, owner_context=context,
                                         before_commit=lambda: _permission(actor, scope, resource))
    worker, value = task["parameters"], task["context"]["input"]

    def check_continue():
        if _context(actor, scope, "write") != context:
            raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
        _permission(actor, scope, resource)
        engine().require_pitch_worker(task_id, owner_context=context, worker=worker)

    try:
        check_continue()
        generated, generated_payload, generated_citations, preserved_office = None, None, None, None
        if value.get('profile') == OWNED_PROFILE:
            from content_generation import generate_pitch_content
            generated = generate_pitch_content(task_id, actor=actor, scope=scope, check_continue=check_continue)
            generated_payload, generated_citations, preserved_office = _assemble_creation(generated, task_id=task_id, actor=actor, scope=scope)
            value = {**value,'manuscript':generated_payload['manuscript'],'citations':generated_citations,
                     'title':generated_payload['manuscript']['title']}
        from scripts.pitch_export import export_pitch_docx
        from lumenis.shared.reporting.artifact import verify_artifact_file
        with tempfile.TemporaryDirectory(prefix="lumenis-internal-pitch-") as temporary:
            output = Path(temporary) / "document.docx"
            export_options = {}
            if generated is None and _contract(value) == AV_PLAN_CONTRACT:
                export_options["audiovisual_plan"] = AudiovisualPlan.from_dict(value["shot_plan"]).snapshot()
            if preserved_office is not None:
                output.write_bytes(preserved_office)
                result_path = output
            else:
                result_path = Path(export_pitch_docx({}, str(output), manuscript=value["manuscript"],
                                                     check_continue=check_continue, **export_options))
            if result_path.resolve() != output.resolve() or not verify_artifact_file(str(output))["valid"]:
                raise ValueError("INTERNAL_PITCH_OUTPUT_INVALID")
            raw = output.read_bytes()
            check_continue()

        if generated is None and _contract(value) == CONTRACT:
            payload = {"manuscript": value["manuscript"], "shot_plan": value["shot_plan"],
                       "truth_state": {"source_admission": "PENDING" if not value["citations"] else "SIGNED_CITATIONS_BOUND",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED", "shot_timing": "PLANNED"}}
        contract = _contract(value)
        if generated is None and contract == SOURCE_CONTRACT:
            _check_upstream(value, actor=actor, scope=scope)
            payload = {"manuscript": value["manuscript"], "upstream_binding": value["upstream_binding"],
                       "truth_state": {"source_admission": "UPSTREAM_READER_BOUND",
                                       "citation_admission": "SIGNED_CITATIONS_BOUND" if value["citations"] else "NO_SIGNED_QUOTE",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED"}}
        if generated is None and contract == MANUSCRIPT_CONTRACT:
            payload = {"manuscript": value["manuscript"], "input_manifest": value["input_manifest"],
                       "truth_state": {"source_admission": "PENDING", "input_materials": "OPERATOR_DECLARED_NOT_INGESTED",
                                       "citation_admission": "SIGNED_CITATIONS_BOUND" if value["citations"] else "PENDING",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED"}}
        if generated is None and contract == AUTHORING_CONTRACT:
            payload = {"manuscript": value["manuscript"],
                       "truth_state": {"source_admission": "USER_AUTHORED_CONTENT" if value["manuscript"]["authorship"] == "user_supplied" else "ASSISTED_DERIVED_CONTENT",
                                       "citation_admission": "SIGNED_CITATIONS_BOUND" if value["citations"] else "NO_SIGNED_QUOTE",
                                       "external_fact_verification": "NOT_INFERRED_FROM_AUTHORSHIP",
                                       "owned_model_execution": "NOT_RUN", "external_effect": "NOT_PERFORMED",
                                       "business_outcome": "NOT_OBSERVED"}}
        if generated is None and contract == AV_PLAN_CONTRACT:
            payload = {"manuscript": value["manuscript"],
                       "audiovisual_plan": AudiovisualPlan.from_dict(value["shot_plan"]).snapshot(),
                       "truth_state": {"source_admission": "DECLARED_NOT_ADMITTED",
                                       "method_source": "RESEARCH_REFERENCE_NOT_MATERIAL_LICENSE",
                                       "citation_admission": "SIGNED_CITATIONS_BOUND" if value["citations"] else "NO_SIGNED_QUOTE",
                                       "media_execution": "NOT_EXECUTED", "owned_model_execution": "NOT_RUN",
                                       "external_effect": "NOT_PERFORMED", "business_outcome": "NOT_OBSERVED"}}
        if generated is not None:
            payload = generated_payload
        markdown = _manuscript_markdown(value['manuscript'])

        def before_commit(con, artifact, document):
            check = _context(actor, scope, "write", connection=con)
            if check != context:
                raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
            _permission(actor, scope, resource, connection=con)
            _check_upstream(value, actor=actor, scope=scope, connection=con)
            if generated is not None:
                # SavedWork already compared the latest parent in this same
                # transaction; its newly staged child is now visible here.
                generation_parent(task['context']['input'], actor=actor, scope=scope, latest=False, connection=con)
                from content_generation import record_pitch_creation
                record_pitch_creation(con, generated=generated, artifact=artifact, document=document, actor=actor, scope=scope)
            engine().commit_pitch_task(task_id, owner_context=context, worker=worker,
                                       connection=con, artifact=artifact, document=document)

        work.save_work(title=value["title"], markdown=markdown, kind="report", payload=payload,
                       citations=value["citations"], request_id=task["context"]["request_id"], actor=actor, scope=scope,
                       work_id=value["work_id"], previous_artifact_id=value["previous_artifact_id"],
                       expected_draft_digest=value["expected_draft_digest"], contract=contract, task_id=task_id,
                       before_commit=before_commit, attachments=[{"name": "document.docx", "content": raw,
                           "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}])
    except BaseException as exc:
        code = str(exc)
        if re.fullmatch(r"[A-Z_0-9]{1,100}", code) is None:
            code = "INTERNAL_PITCH_EXECUTION_FAILED"
        engine().fail_pitch_task(task_id, owner_context=context, worker=worker, error=code)
        raise
    return read_internal_pitch(task_id, actor=actor, scope=scope)


def read_internal_pitch(task_id, *, actor, scope):
    """Reconcile lost acknowledgement through actual committed owner bytes."""
    context = _context(actor, scope, "read")
    task = engine().get_pitch_task(task_id, owner_context=context)
    result = {"task_id": task_id, "state": task["status"], "error": task["error"],
              "action_receipt": None, "work": None, "scope": work._client_scope(context)}
    if task["status"] == "succeeded":
        upstream = _check_upstream(task["context"]["input"], actor=actor, scope=scope)
        stored = task["result"]
        committed = work.reopen_work(stored["artifact_id"], actor=actor, scope=scope)
        if (committed["artifact"]["sha256"] != stored["sha256"] or committed["artifact"]["size_bytes"] != stored["size_bytes"]
                or committed["document"]["task_id"] != task_id or committed["document"]["version"] != stored["version"]
                or committed["document"]["work_id"] != stored["work_id"]
                or committed["document"]["parent_artifact_id"] != stored["parent_artifact_id"]
                or committed["document"]["parent_sha256"] != stored["parent_sha256"]
                or committed["document"]["contract"] != _contract(task["context"]["input"])
                or len(committed["document"].get("attachments", [])) != 1):
            raise ValueError("INTERNAL_PITCH_RECEIPT_INTEGRITY_FAILED")
        if upstream is not None:
            if committed["document"]["payload"].get("upstream_binding") != upstream:
                raise ValueError("INTERNAL_PITCH_UPSTREAM_INTEGRITY_FAILED")
            result["research_return_ref"] = upstream["return_ref"]
        if task['context']['input'].get('profile') == AV_PLAN_PROFILE:
            expected = AudiovisualPlan.from_dict(task["context"]["input"]["shot_plan"])
            if not expected.matches_snapshot(committed["document"]["payload"].get("audiovisual_plan")):
                raise ValueError("INTERNAL_PITCH_AV_PLAN_INTEGRITY_FAILED")
        result["work"] = committed
        if task['context']['input'].get('profile') in {AUTHORING_PROFILE, OWNED_PROFILE}:
            for field in ('revision_sections','creation_evidence','research_return_ref'):
                if field in committed:
                    result[field] = committed[field]
        result["action_receipt"] = {"owner": "Shared ContentCreation/TaskEngine/SavedWork",
                                    "task_id": task_id, **stored, "scope": result["scope"],
                                    "output": committed["document"]["attachments"][0]}
    if _context(actor, scope, "read") != context:
        raise PermissionError("INTERNAL_PITCH_TASK_SCOPE_DENIED")
    return result


def cancel_internal_pitch(task_id, *, actor, scope):
    context = _context(actor, scope, "write")
    resource = "internal-pitch-cancel:v1:" + work._digest({"context": context, "task_id": task_id})
    _permission(actor, scope, resource)
    with work.staging_write(resource):
        task = engine().cancel_pitch_task(task_id, owner_context=context,
                                         before_commit=lambda: _permission(actor, scope, resource))
    result = read_internal_pitch(task_id, actor=actor, scope=scope)
    result["cancellation"] = "ALREADY_COMMITTED" if task["status"] == "succeeded" else task["status"].upper()
    return result


def download_internal_pitch(task_id, *, actor, scope):
    result = read_internal_pitch(task_id, actor=actor, scope=scope)
    if result["work"] is None:
        raise ValueError("INTERNAL_PITCH_OUTPUT_NOT_COMMITTED")
    binding = result["action_receipt"]["output"]
    resource = "internal-pitch-export:v1:" + work._digest(binding)
    work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource)
    context = _context(actor, scope, "read")
    with get_repository().connection(read_only=True, wal=False) as con:
        raw = work._read_attachment(con, binding, context, result["action_receipt"]["work_id"], actor=actor)
    read_internal_pitch(task_id, actor=actor, scope=scope)
    work._check_effect(actor, scope, OperationType.DATA_EXPORT, resource)
    return {"content": raw, "filename": binding["name"], "media_type": binding["media_type"],
            "sha256": binding["sha256"], "action_receipt": result["action_receipt"]}
