// Independent, pure review logic. Product Learning/Permission/Evidence interfaces are UNBOUND.
// Nothing here authenticates evidence, promotes a product rule, calls AI, or persists externally.
export const RESEARCH_LEVELS = Object.freeze(['fact', 'observation', 'pattern', 'hypothesis', 'validation', 'transfer', 'dont_copy']);
export const RESEARCH_STATUSES = Object.freeze(['observed', 'derived', 'ai_suggested', 'human_verified', 'unverified']);
export const RESEARCH_BINDING = 'UNBOUND';
const clone = x => structuredClone(x);
const assert = (x, message = 'INVALID_RESEARCH_DATA') => { if (!x) throw new Error(message); };
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x) && Object.getPrototypeOf(x) === Object.prototype;
const text = (x, max = 2000) => typeof x === 'string' && x.trim().length > 0 && x.length <= max;
const revision = x => Number.isSafeInteger(x) && x >= 0;
const keys = (x, list) => assert(object(x) && Object.keys(x).length === list.length && Object.keys(x).every(k => list.includes(k)));
const timestamp = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(x) && Number.isFinite(Date.parse(x));
function refs(list) {
  assert(Array.isArray(list) && list.length <= 100);
  list.forEach(r => { keys(r, ['id', 'version']); assert(text(r.id, 200) && text(r.version, 200)); });
  assert(new Set(list.map(r => r.id)).size === list.length, 'DUPLICATE_EVIDENCE_REFERENCE');
}
function finding(f) {
  keys(f, ['id', 'statement', 'level', 'status', 'evidenceRefs']);
  assert(text(f.id, 200) && text(f.statement, 20000) && RESEARCH_LEVELS.includes(f.level) && RESEARCH_STATUSES.includes(f.status)); refs(f.evidenceRefs);
  assert(!(f.level === 'fact' && ['ai_suggested', 'derived', 'unverified'].includes(f.status)), 'FACT_REQUIRES_OWNER_OBSERVATION');
}
function validation(v) {
  keys(v, ['id', 'outcome', 'independenceKey', 'independenceBasis', 'candidateVersion', 'evidenceRefs']);
  assert(text(v.id, 200) && ['pass', 'counterexample', 'inconclusive'].includes(v.outcome));
  assert(v.independenceKey === null || text(v.independenceKey, 200));
  assert(v.independenceBasis === null || text(v.independenceBasis));
  assert(revision(v.candidateVersion)); refs(v.evidenceRefs);
}
function draft(d) {
  keys(d, ['finding', 'candidateVersion', 'validations']); finding(d.finding); assert(revision(d.candidateVersion));
  assert(Array.isArray(d.validations) && d.validations.length <= 100); d.validations.forEach(validation);
  assert(new Set(d.validations.map(v => v.id)).size === d.validations.length, 'DUPLICATE_VALIDATION');
}
function stateCheck(s) {
  keys(s, ['schema', 'revision', 'draft', 'history', 'reader', 'confirmation']);
  assert(s.schema === 'research-learning-review-v1' && revision(s.revision)); draft(s.draft);
  assert(Array.isArray(s.history) && s.history.length <= 32); s.history.forEach(draft);
  keys(s.reader, ['anchor', 'drawerEvidenceId']); assert(text(s.reader.anchor, 200));
  assert(s.reader.drawerEvidenceId === null || text(s.reader.drawerEvidenceId, 200));
  if (s.confirmation !== null) {
    keys(s.confirmation, ['reviewer', 'candidateVersion', 'basis', 'at', 'localOnly']);
    assert(text(s.confirmation.reviewer, 200) && revision(s.confirmation.candidateVersion) && text(s.confirmation.basis, 200000) && timestamp(s.confirmation.at) && s.confirmation.localOnly === true);
  }
  return s;
}
export function createResearchState({id, statement, level = 'hypothesis', status = 'unverified', evidenceRefs = []}) {
  return stateCheck({schema: 'research-learning-review-v1', revision: 0,
    draft: {finding: {id, statement, level, status, evidenceRefs: clone(evidenceRefs)}, candidateVersion: 0, validations: []},
    history: [], reader: {anchor: 'start', drawerEvidenceId: null}, confirmation: null});
}
function contextCheck({now, evidence}) {
  assert(timestamp(now), 'EXPLICIT_TIME_REQUIRED'); assert(Array.isArray(evidence) && evidence.length <= 1000);
  const map = new Map();
  for (const e of evidence) {
    keys(e, ['id', 'version', 'state', 'locator', 'sourceGroup', 'validUntil']);
    assert(text(e.id, 200) && text(e.version, 200) && ['active', 'withdrawn', 'unknown'].includes(e.state));
    assert(e.locator === null || text(e.locator, 4000)); assert(e.sourceGroup === null || text(e.sourceGroup, 200));
    assert(e.validUntil === null || timestamp(e.validUntil)); assert(!map.has(e.id), 'DUPLICATE_EVIDENCE'); map.set(e.id, e);
  }
  return map;
}
function inspectRefs(list, map, now) {
  if (!list.length) return ['EVIDENCE_MISSING'];
  return list.flatMap(ref => {
    const e = map.get(ref.id);
    if (!e) return [`EVIDENCE_MISSING:${ref.id}`];
    if (e.version !== ref.version) return [`EVIDENCE_VERSION_CHANGED:${ref.id}`];
    if (e.state !== 'active') return [`EVIDENCE_${e.state.toUpperCase()}:${ref.id}`];
    if (!e.locator || !e.sourceGroup || e.validUntil === null) return [`EVIDENCE_INCOMPLETE:${ref.id}`];
    if (Date.parse(e.validUntil) <= Date.parse(now)) return [`EVIDENCE_EXPIRED:${ref.id}`];
    return [];
  });
}
export function evaluateLearning(input, context) {
  const s = stateCheck(input), map = contextCheck(context), {now} = context, {finding: f, validations, candidateVersion} = s.draft;
  const reasons = inspectRefs(f.evidenceRefs, map, now);
  const valid = [], invalidValidations = [];
  for (const v of validations) {
    const errors = inspectRefs(v.evidenceRefs, map, now);
    if (v.candidateVersion !== candidateVersion) errors.push('STALE_CANDIDATE_VERSION');
    if (!v.independenceKey || !v.independenceBasis) errors.push('INDEPENDENCE_UNVERIFIED');
    if (errors.length) invalidValidations.push({id: v.id, reasons: errors}); else valid.push(v);
  }
  // Counterexamples remain vetoes even after expiry, edits or undo. Only the product owner
  // can resolve a contradiction; this unbound review module offers no override.
  const contradicted = validations.some(v => v.outcome === 'counterexample');
  const accepted = [], groups = new Set(), independentKeys = new Set();
  for (const v of valid.filter(v => v.outcome === 'pass').sort((a,b) => a.id.localeCompare(b.id))) {
    const sourceGroups = v.evidenceRefs.map(r => map.get(r.id).sourceGroup);
    if (independentKeys.has(v.independenceKey) || sourceGroups.some(g => groups.has(g))) continue;
    accepted.push(v); independentKeys.add(v.independenceKey); sourceGroups.forEach(g => groups.add(g));
  }
  if (contradicted) reasons.push('COUNTEREXAMPLE_VETO');
  if (accepted.length < 2) reasons.push('TWO_INDEPENDENT_VALIDATIONS_REQUIRED');
  if (f.status === 'ai_suggested') reasons.push('AI_SUGGESTION_REQUIRES_OWNER_REVIEW');
  if (f.status === 'unverified') reasons.push('CLAIM_UNVERIFIED');
  if (f.level === 'dont_copy') reasons.push('DONT_COPY_NOT_PROMOTABLE');
  const basis = JSON.stringify({draft: s.draft, evidence: [...map.values()].sort((a,b) => a.id.localeCompare(b.id))});
  const eligible = reasons.length === 0;
  const confirmed = eligible && s.confirmation?.candidateVersion === candidateVersion && s.confirmation?.basis === basis;
  return {binding: RESEARCH_BINDING, localOnly: true, productPromotion: 'UNBOUND', canonicalFact: false,
    status: contradicted ? 'rejected' : confirmed ? 'review_confirmed' : eligible ? 'ready_for_human_review' : 'candidate',
    evidenceLabel: inspectRefs(f.evidenceRefs, map, now).length ? '未核实' : f.status === 'ai_suggested' ? 'AI 建议' : '来源已提供（未核产品准入）',
    eligible, independentValidationCount: accepted.length, reasons, invalidValidations, basis};
}
export function reduceResearch(input, action, context) {
  stateCheck(input); assert(object(action));
  assert(action.expectedRevision === input.revision, 'STALE_RESEARCH_REVISION');
  const s = clone(input), history = () => { s.history.push(clone(s.draft)); if (s.history.length > 32) s.history.shift(); };
  switch (action.type) {
    case 'edit-finding':
      finding(action.finding); assert(action.finding.id === s.draft.finding.id, 'FINDING_ID_IMMUTABLE');
      // This local editor cannot upgrade an origin/status to externally verified fact.
      assert(action.finding.status === s.draft.finding.status, 'OWNER_STATUS_REQUIRED');
      history(); s.draft.finding = clone(action.finding); s.draft.candidateVersion++; s.confirmation = null; break;
    case 'add-validation':
      validation(action.validation); assert(action.validation.candidateVersion === s.draft.candidateVersion, 'STALE_CANDIDATE_VERSION');
      assert(!s.draft.validations.some(v => v.id === action.validation.id), 'DUPLICATE_VALIDATION');
      history(); s.draft.validations.push(clone(action.validation)); s.confirmation = null; break;
    case 'confirm-review': {
      assert(action.humanConfirmed === true && text(action.reviewer, 200), 'HUMAN_CONFIRMATION_REQUIRED');
      const result = evaluateLearning(s, context); assert(result.eligible, 'LEARNING_REVIEW_BLOCKED');
      s.confirmation = {reviewer: action.reviewer, candidateVersion: s.draft.candidateVersion, basis: result.basis, at: context.now, localOnly: true}; break;
    }
    case 'undo': {
      assert(s.history.length, 'NOTHING_TO_UNDO');
      const previous = s.history.pop();
      // Undo only editing. Validation evidence is append-only in the review session.
      s.draft.finding = previous.finding; s.draft.candidateVersion++; s.confirmation = null; break;
    }
    case 'revoke-review': s.confirmation = null; break;
    case 'set-anchor': assert(text(action.anchor, 200)); s.reader.anchor = action.anchor; break;
    case 'open-evidence':
      assert(text(action.evidenceId, 200) && s.draft.finding.evidenceRefs.some(r => r.id === action.evidenceId), 'EVIDENCE_NOT_REFERENCED');
      s.reader.drawerEvidenceId = action.evidenceId; break;
    case 'close-evidence': s.reader.drawerEvidenceId = null; break;
    default: throw new Error('UNKNOWN_RESEARCH_ACTION');
  }
  s.revision++; return stateCheck(s);
}
// Serialization is a local byte deliverable, never a claim of a successful server save.
export function saveResearch(input) { stateCheck(input); return JSON.stringify(input); }
export function reopenResearch(serialized, context) {
  assert(typeof serialized === 'string' && serialized.length <= 4000000, 'INVALID_RESEARCH_SAVE');
  const state = stateCheck(JSON.parse(serialized));
  // Saved review attestations are not trusted across load. A fresh human review is required.
  state.confirmation = null;
  return {state, evaluation: evaluateLearning(state, context)};
}
const scopeKeys = ['platform', 'metric', 'definitionVersion', 'unit', 'denominator', 'population', 'windowStart', 'windowEnd'];
export function compareMetricScopes(a, b) {
  assert(object(a) && object(b));
  const known = x => text(x, 500) && !['unknown', 'unverified', 'not_available', 'not_collected', '—', '-'].includes(x.trim().toLowerCase());
  const missing = scopeKeys.filter(k => !known(a[k]) || !known(b[k]));
  const mismatches = scopeKeys.filter(k => !missing.includes(k) && a[k] !== b[k]);
  return {comparable: !missing.length && !mismatches.length, missing, mismatches, aggregationPerformed: false};
}
