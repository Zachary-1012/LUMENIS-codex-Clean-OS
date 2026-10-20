// Independent review prototype. No API, model, production store or permission grant.
export const TOPIC_SIGNALS = Object.freeze([
  ['demand', '需求', .16], ['timeliness', '时效', .12], ['novelty', '新颖', .10],
  ['human_relevance', '人的相关性', .14], ['guest_fit', '嘉宾适配', .12],
  ['evidence', '证据', .10], ['content_yield', '内容产出', .10],
  ['distribution', '分发', .06], ['risk', '风险', -.05], ['cost', '成本', -.05]
].map(([key, label, weight]) => Object.freeze({key, label, weight})));
export const GUEST_GATES = Object.freeze([
  {key: 'public_value', label: '独特体验且有公共价值'},
  {key: 'expression', label: '有表达能力与意愿'},
  {key: 'resonance', label: '能引发共鸣'}
].map(Object.freeze));
export const TOPIC_PLANNING_LIMITS = Object.freeze({history: 32, text: 20000, title: 500, source: 4000, serialized: 4000000});
const keys = TOPIC_SIGNALS.map(x => x.key), gateKeys = GUEST_GATES.map(x => x.key);
const clone = x => structuredClone(x);
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x) && Object.getPrototypeOf(x) === Object.prototype;
function assert(condition, message = 'INVALID_PLANNING_DATA') { if (!condition) throw new Error(message); }
function exactKeys(x, names) { assert(object(x) && Object.keys(x).length === names.length && Object.keys(x).every(k => names.includes(k))); }
function signal(x) { assert(x === null || typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1, 'INVALID_TOPIC_SIGNAL'); return x; }
function signals(input) {
  assert(object(input) && Object.keys(input).every(k => keys.includes(k)), 'INVALID_TOPIC_SIGNALS');
  return Object.fromEntries(keys.map(k => [k, signal(Object.hasOwn(input, k) ? input[k] : null)]));
}
// Round the exact IEEE-754 value to two decimal places, ties-to-even, as Python round(x, 2).
// No epsilon adjustment; do not round signals before calculating the score.
export function roundTopicScore(value) {
  assert(typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100);
  if (value === 0) return 0;
  const bytes = new DataView(new ArrayBuffer(8)); bytes.setFloat64(0, value);
  const bits = bytes.getBigUint64(0), exponent = Number((bits >> 52n) & 2047n);
  const mantissa = (bits & ((1n << 52n) - 1n)) + (exponent ? 1n << 52n : 0n);
  const shift = (exponent || 1) - 1023 - 52;
  let numerator = mantissa * 100n, denominator = 1n;
  if (shift >= 0) numerator <<= BigInt(shift); else denominator <<= BigInt(-shift);
  let quotient = numerator / denominator;
  const remainder = numerator % denominator;
  if (remainder * 2n > denominator || remainder * 2n === denominator && quotient % 2n === 1n) quotient++;
  return Number(quotient) / 100;
}
export function classifyTopic(score, timeliness) {
  if (score === null || timeliness === null) return null;
  assert(typeof score === 'number' && Number.isFinite(score) && score >= 0 && score <= 100, 'INVALID_TOPIC_CLASSIFICATION_INPUT'); signal(timeliness);
  return score < 35 ? 'rejected' : timeliness >= .85 ? 'now' : score >= 75 ? 'soon' : score >= 55 ? 'evergreen' : 'watch';
}
export function evaluateTopic(input = {}) {
  const values = signals(input), missing_signals = keys.filter(k => values[k] === null);
  if (missing_signals.length) return {state: 'input_required', score: null, stage: null, signals: values, missing_signals};
  const positive = TOPIC_SIGNALS.slice(0, 8).reduce((sum, {key, weight}) => sum + weight * values[key], 0);
  const penalty = .05 * values.risk + .05 * values.cost;
  const score = roundTopicScore(100 * Math.max(0, Math.min(1, positive - penalty)));
  return {state: 'scored', score, stage: classifyTopic(score, values.timeliness), signals: values, missing_signals};
}
const draftKeys = ['title', 'originalText', 'editedText', 'sourceRef', 'signals', 'gates'];
function validateDraft(draft) {
  exactKeys(draft, draftKeys);
  for (const key of ['title', 'originalText', 'editedText', 'sourceRef']) {
    const max = key === 'title' ? TOPIC_PLANNING_LIMITS.title : key === 'sourceRef' ? TOPIC_PLANNING_LIMITS.source : TOPIC_PLANNING_LIMITS.text;
    assert(typeof draft[key] === 'string' && draft[key].length <= max, 'TEXT_BUDGET_EXCEEDED');
  }
  exactKeys(draft.signals, keys); signals(draft.signals); exactKeys(draft.gates, gateKeys);
  gateKeys.forEach(k => assert([null, true, false].includes(draft.gates[k])));
}
function validateState(state) {
  exactKeys(state, ['schema', 'revision', 'draft', 'history', 'suggestion']);
  assert(state.schema === 'topic-planning-review-v1' && Number.isSafeInteger(state.revision) && state.revision >= 0);
  validateDraft(state.draft); assert(Array.isArray(state.history) && state.history.length <= TOPIC_PLANNING_LIMITS.history);
  state.history.forEach(d => { validateDraft(d); assert(d.originalText === state.draft.originalText && d.sourceRef === state.draft.sourceRef); });
  if (state.suggestion !== null) {
    const s = state.suggestion;
    exactKeys(s, ['id', 'simulation', 'baseRevision', 'signals', 'rationale', 'status']);
    assert(typeof s.id === 'string' && s.id.length > 0 && s.id.length <= 120 && s.simulation === true && Number.isSafeInteger(s.baseRevision) && s.baseRevision >= 0 && s.baseRevision <= state.revision);
    exactKeys(s.signals, keys); signals(s.signals);
    assert(typeof s.rationale === 'string' && s.rationale.length <= 2000 && ['pending', 'accepted', 'rejected'].includes(s.status));
  }
  return state;
}
export function createTopicPlanning({title = '', originalText = '', sourceRef = '', signals: input = {}} = {}) {
  return validateState({schema: 'topic-planning-review-v1', revision: 0,
    draft: {title, originalText, editedText: originalText, sourceRef, signals: signals(input), gates: Object.fromEntries(gateKeys.map(k => [k, null]))}, history: [], suggestion: null});
}
function signalsPatch(input) { signals(input); return input; }
export function topicPlanningReduce(input, event) {
  validateState(input); assert(object(event) && typeof event.type === 'string', 'INVALID_EVENT');
  const state = clone(input);
  const edit = apply => { state.history.push(clone(state.draft)); if (state.history.length > TOPIC_PLANNING_LIMITS.history) state.history.shift(); apply(); state.revision++; };
  switch (event.type) {
    case 'edit-signal': assert(keys.includes(event.key)); signal(event.value); edit(() => { state.draft.signals[event.key] = event.value; }); break;
    case 'edit-text': assert(['title', 'editedText'].includes(event.key) && typeof event.value === 'string'); edit(() => { state.draft[event.key] = event.value; }); break;
    case 'edit-gate': assert(gateKeys.includes(event.key) && [null, true, false].includes(event.value)); edit(() => { state.draft.gates[event.key] = event.value; }); break;
    case 'undo': if (state.history.length) { state.draft = state.history.pop(); state.revision++; } break;
    case 'suggest':
      assert(event.simulation === true, 'SIMULATION_LABEL_REQUIRED');
      assert(event.baseRevision === state.revision, 'STALE_SUGGESTION');
      assert(typeof event.id === 'string' && event.id.length > 0 && typeof event.rationale === 'string');
      state.suggestion = {id: event.id, simulation: true, baseRevision: event.baseRevision, signals: signals({...state.draft.signals, ...signalsPatch(event.signals)}), rationale: event.rationale, status: 'pending'}; break;
    case 'accept-suggestion':
      assert(state.suggestion?.status === 'pending' && event.id === state.suggestion.id, 'NO_PENDING_SUGGESTION');
      assert(state.suggestion.baseRevision === state.revision, 'STALE_SUGGESTION');
      edit(() => { state.draft.signals = clone(state.suggestion.signals); }); state.suggestion.status = 'accepted'; break;
    case 'reject-suggestion':
      assert(state.suggestion?.status === 'pending' && event.id === state.suggestion.id, 'NO_PENDING_SUGGESTION');
      state.suggestion.status = 'rejected'; break;
    default: throw new Error('UNKNOWN_EVENT');
  }
  return validateState(state);
}
export function compareTopicSuggestion(state) {
  validateState(state); const suggestion = state.suggestion;
  if (!suggestion) return null;
  return {simulation: true, status: suggestion.status, stale: suggestion.baseRevision !== state.revision,
    current: evaluateTopic(state.draft.signals), proposed: evaluateTopic(suggestion.signals),
    changes: keys.filter(k => state.draft.signals[k] !== suggestion.signals[k]).map(key => ({key, before: state.draft.signals[key], after: suggestion.signals[key]}))};
}
export function guestQualification(state) {
  validateState(state); const missing = gateKeys.filter(k => state.draft.gates[k] === null), failed = gateKeys.filter(k => state.draft.gates[k] === false);
  return {qualified: missing.length === 0 && failed.length === 0, missing, failed, authority: 'manual_review_only'};
}
export function canEnterPodcastPath(state, path) {
  validateState(state);
  if (['owned-audio', 'owned-script'].includes(path)) return {allowed: true, reason: 'independent_creation', productionPermission: 'NOT_VERIFIED'};
  assert(path === 'guest-outline', 'UNKNOWN_PATH');
  return {allowed: guestQualification(state).qualified, reason: guestQualification(state).qualified ? 'manual_gates_passed' : 'guest_review_required', productionPermission: 'NOT_VERIFIED'};
}
export function serializeTopicPlanning(state) {
  validateState(state); const serialized = JSON.stringify(state);
  assert(serialized.length <= TOPIC_PLANNING_LIMITS.serialized, 'STORAGE_BUDGET_EXCEEDED'); return serialized;
}
export function reopenTopicPlanning(serialized) {
  assert(typeof serialized === 'string' && serialized.length <= TOPIC_PLANNING_LIMITS.serialized, 'INVALID_SAVED_DATA');
  let state; try { state = JSON.parse(serialized); } catch { throw new Error('INVALID_SAVED_DATA'); }
  return clone(validateState(state));
}
