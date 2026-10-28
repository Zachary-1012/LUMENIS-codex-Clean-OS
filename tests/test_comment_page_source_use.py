"""Original comment-page SourceUse: isolated real owners, synthetic acquisition."""
import sqlite3

import pytest

from tests.test_collector_comment_pages import comments_case, collect
from tests.test_collector_transaction_truth import collector_case


DECLARATION = {'rights': 'public-reference-only',
               'statement': 'Use these exact observed comments for internal reference; no publication or training.'}


def page_request(case, monkeypatch):
    result = collect(case, monkeypatch)
    from lumenis.system.collector.adapters.secondary_collection import read_comment_page_original
    from lumenis.shared.database import get_repository
    con = get_repository().connect()
    original = read_comment_page_original(result['page_ref'], actor=case['actor'], scope=case['scope'], connection=con)
    request = dict(scope=case['scope'], source_evidence_ref=result['page_ref'], source_fingerprint=original['sha256'],
        body_sha256=original['document']['body_sha256'], source_version='collector-native-comments/2', connection=con)
    return result, original, request, con


def grant(case, request, purpose):
    prepared = case['gate'].prepare_comment_page_use(case['actor'], **request, purpose=purpose, rights_declaration=DECLARATION)
    assert prepared.allowed is False and prepared.requires_approval
    assert prepared.reason == 'COMMENT_PAGE_PREPARED_NOT_AUTHORIZED', prepared.to_dict()
    assert 'comment-page:' in prepared.resource
    token = case['gate'].grant_approval(prepared.operation_type, resource=prepared.resource, granted_by='isolated exact comment-use fixture')
    return prepared, token


def test_original_page_exact_purpose_grants_survive_reopen_without_borrowing_parent(comments_case, monkeypatch):
    case = comments_case
    result, original, request, con = page_request(case, monkeypatch)
    try:
        gate = case['gate']
        # The original import/parent grants and broad operation grants do not
        # authorize this page's expression or either downstream purpose.
        gate.grant_approval('collector_source_read', resource=None, granted_by='isolated broad fixture')
        denied = gate.check_comment_page_use(case['actor'], **request, purpose='research_reference')
        assert not denied.allowed
        prepared, token = grant(case, request, 'research_reference')
        admitted = gate.check_comment_page_use(case['actor'], **request, purpose='research_reference')
        assert admitted.allowed and admitted.audit_id and admitted.resource == prepared.resource
        assert not gate.check_comment_page_use(case['actor'], **request, purpose='quote_reference').allowed
        quoted, quote_token = grant(case, request, 'quote_reference')
        assert quoted.resource != prepared.resource
        assert gate.check_comment_page_use(case['actor'], **request, purpose='quote_reference').allowed
        gate.revoke_approval(token)
        assert not gate.check_comment_page_use(case['actor'], **request, purpose='research_reference').allowed
        assert gate.check_comment_page_use(case['actor'], **request, purpose='quote_reference').allowed
        assert original['document']['rights']['status'] == 'UNREVIEWED'
        assert original['document']['rights']['allowed_uses'] == []
    finally:
        con.close()


def test_page_grant_cannot_follow_next_page_or_mutated_input(comments_case, monkeypatch):
    case = comments_case
    first, original, request, con = page_request(case, monkeypatch)
    try:
        grant(case, request, 'quote_reference')
        second = collect(case, monkeypatch, continuation=first['continuation'])
        from lumenis.system.collector.adapters.secondary_collection import read_comment_page_original
        next_page = read_comment_page_original(second['page_ref'], actor=case['actor'], scope=case['scope'], connection=con)
        changed = {**request, 'source_evidence_ref': second['page_ref'], 'source_fingerprint': next_page['sha256'],
                   'body_sha256': next_page['document']['body_sha256']}
        assert not case['gate'].check_comment_page_use(case['actor'], **changed, purpose='quote_reference').allowed
        for fields in ({'source_fingerprint': '0' * 64}, {'body_sha256': '0' * 64}, {'source_version': 'collector-native-comments/1'}):
            assert not case['gate'].check_comment_page_use(case['actor'], **{**request, **fields}, purpose='quote_reference').allowed
        assert case['gate'].check_comment_page_use(case['actor'], **request, purpose='quote_reference').allowed
        assert not case['gate'].check_comment_page_use(case['actor'], **request, purpose='model_training').allowed
        assert not case['gate'].check_comment_page_use(case['actor'], **request, purpose='external_publish').allowed
    finally:
        con.close()


def test_current_scope_and_in_call_token_revocation_win_over_prior_read(comments_case, monkeypatch):
    case = comments_case
    result, original, request, con = page_request(case, monkeypatch)
    try:
        prepared, token = grant(case, request, 'research_reference')
        original_audit = case['gate']._write_audit
        def revoke_during_audit(**kwargs):
            audit_id = original_audit(**kwargs)
            if kwargs.get('permission_required') == 'comment_page_exact_research_reference' and kwargs.get('result') == 'allowed':
                case['gate'].revoke_approval(token)
            return audit_id
        monkeypatch.setattr(case['gate'], '_write_audit', revoke_during_audit)
        denied = case['gate'].check_comment_page_use(case['actor'], **request, purpose='research_reference')
        assert not denied.allowed and denied.reason == 'COMMENT_PAGE_APPROVAL_OR_SOURCE_CHANGED'
        monkeypatch.setattr(case['gate'], '_write_audit', original_audit)
        grant(case, request, 'research_reference')
        with sqlite3.connect(case['db_path']) as db:
            db.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id=?", (case['scope']['subject_id'],))
        assert not case['gate'].check_comment_page_use(case['actor'], **request, purpose='research_reference').allowed
    finally:
        con.close()


def test_commit_lease_uses_original_approval_lock_through_consumer_commit(comments_case, monkeypatch):
    import threading
    case = comments_case
    result, original, request, con = page_request(case, monkeypatch)
    try:
        prepared, token = grant(case, request, 'quote_reference')
        con.execute('BEGIN IMMEDIATE')
        entered, revoked = threading.Event(), threading.Event()
        def revoke():
            entered.set()
            case['gate'].revoke_approval(token)
            revoked.set()
        thread = threading.Thread(target=revoke)
        with case['gate'].comment_page_use_commit_lease(case['actor'], **request, purpose='quote_reference') as decision:
            assert decision.allowed and decision.resource == prepared.resource
            thread.start()
            assert entered.wait(1)
            assert not revoked.wait(.05)
            con.commit()
        thread.join(timeout=2)
        assert revoked.is_set() and not thread.is_alive()
        assert not case['gate'].check_comment_page_use(case['actor'], **request, purpose='quote_reference').allowed
        with pytest.raises(PermissionError, match='COMMENT_PAGE_COMMIT_TRANSACTION_REQUIRED'):
            with case['gate'].comment_page_use_commit_lease(case['actor'], **request, purpose='quote_reference'):
                pytest.fail('lease without consumer transaction')
    finally:
        con.close()


def test_batch_commit_checks_each_purpose_before_one_non_reentrant_lock(comments_case, monkeypatch):
    case = comments_case
    result, original, request, con = page_request(case, monkeypatch)
    try:
        _, research_token = grant(case, request, 'research_reference')
        _, quote_token = grant(case, request, 'quote_reference')
        uses = [{**{key: value for key, value in request.items() if key != 'connection'}, 'purpose': purpose}
                for purpose in ('research_reference', 'quote_reference')]
        con.execute('BEGIN IMMEDIATE')
        with case['gate'].comment_page_uses_commit_lease(case['actor'], uses=uses, connection=con) as decisions:
            assert len(decisions) == 2 and all(decision.allowed for decision in decisions)
            assert decisions[0].resource != decisions[1].resource
            con.commit()
        case['gate'].revoke_approval(quote_token)
        con.execute('BEGIN IMMEDIATE')
        with pytest.raises(PermissionError, match='COMMENT_PAGE_COMMIT_USE_DENIED'):
            with case['gate'].comment_page_uses_commit_lease(case['actor'], uses=uses, connection=con):
                pytest.fail('revoked quote purpose reached commit')
        con.rollback()
    finally:
        con.close()


def test_original_storage_recovery_admits_same_signed_page_without_refetch(comments_case, monkeypatch):
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.database import get_repository
    case = comments_case
    original_stage = saved_work._stage_bytes
    def fail(*args, **kwargs):
        raise OSError('isolated original file failure')
    monkeypatch.setattr(saved_work, '_stage_bytes', fail)
    page = collect(case, monkeypatch)
    assert page['original_source']['status'] == 'UNAVAILABLE'
    con = get_repository().connect()
    try:
        request = dict(scope=case['scope'], source_evidence_ref=page['page_ref'],
            source_fingerprint=page['original_source']['source_fingerprint'],
            body_sha256=page['original_source']['body_sha256'],
            source_version='collector-native-comments/2', connection=con)
        blocked = case['gate'].prepare_comment_page_use(case['actor'], **request,
            purpose='research_reference', rights_declaration=DECLARATION)
        assert not blocked.allowed and blocked.reason != 'COMMENT_PAGE_PREPARED_NOT_AUTHORIZED'
        monkeypatch.setattr(saved_work, '_stage_bytes', original_stage)
        recovered = case['entry'].recover_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])
        assert recovered['sha256'] == request['source_fingerprint'] and recovered['evidence_rewritten'] is False
        assert len(case['calls']) == 1 and recovered['network_attempted'] is False
        prepared, token = grant(case, request, 'research_reference')
        assert case['gate'].check_comment_page_use(case['actor'], **request, purpose='research_reference').allowed
        replay = case['entry'].recover_comment_page_original(page['page_ref'], actor=case['actor'], scope=case['scope'])
        assert replay['replayed'] and replay['sha256'] == request['source_fingerprint']
        assert case['gate'].check_comment_page_use(case['actor'], **request, purpose='research_reference').resource == prepared.resource
    finally:
        con.close()


def test_revoke_withdraws_all_own_declarations_even_after_source_read_is_withdrawn(comments_case, monkeypatch):
    case = comments_case
    page, original, request, con = page_request(case, monkeypatch)
    try:
        prepared, first = grant(case, request, 'research_reference')
        declaration = {'rights': 'owner-approved', 'statement': 'Separate exact page research review, without publication or training.'}
        other = case['gate'].prepare_comment_page_use(case['actor'], **request, purpose='research_reference', rights_declaration=declaration)
        assert other.reason == 'COMMENT_PAGE_PREPARED_NOT_AUTHORIZED' and other.resource != prepared.resource
        second = case['gate'].grant_approval(other.operation_type, resource=other.resource, granted_by='isolated purpose review')
        grant(case, request, 'quote_reference')
        denied = case['gate'].revoke_comment_page_use({'id': 999}, **request, purpose='research_reference')
        assert not denied.allowed
        revoked = case['gate'].revoke_comment_page_use(case['actor'], **request, purpose='research_reference')
        assert revoked.allowed and revoked.reason == 'COMMENT_PAGE_USE_REVOKED_NO_READ_GRANTED'
        assert not case['gate']._approval_token_is_valid(first, prepared.operation_type, prepared.resource)
        assert not case['gate']._approval_token_is_valid(second, other.operation_type, other.resource)
        assert not case['gate'].check_comment_page_use(case['actor'], **request, purpose='research_reference').allowed
        assert case['gate'].check_comment_page_use(case['actor'], **request, purpose='quote_reference').allowed
        with sqlite3.connect(case['db_path']) as db:
            db.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id=?", (case['scope']['subject_id'],))
        # Withdrawal needs only the authenticated grant owner and immutable page
        # binding; it must not require reading a now unavailable source body.
        final = case['gate'].revoke_comment_page_use(case['actor'], **request, purpose='quote_reference')
        assert final.allowed and final.audit_id
    finally:
        con.close()
