import { VERSION as PARAMETER_VERSION, parameters, spring } from './physics.mjs';

/** Standalone review component. CSS px, seconds, px/s, and relative mass, never kg.
 * Parameter ranges are owned by physics.mjs: mass .2–6, stiffness 20–600,
 * damping 1–80. No second spring implementation or business-state mutation.
 */
export const DRAWER_VERSION = 'review-physical-drawer/1.0.0';
export const DRAWER_MAX_STEP = .1;
const finite = (value, fallback = 0) => Number.isFinite(value) ? value : fallback;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

/** Input is measured layout geometry, before the drawer's transform, in CSS px.
 * At x=0 the panel is open. At x=closed its left edge is at the stage's edge.
 * Opening overshoot may use only real spare space to the left, at most 18px.
 */
export function drawerGeometry(measurement = {}) {
  const stageWidth = Math.max(0, finite(measurement.stageWidth));
  const stageHeight = Math.max(0, finite(measurement.stageHeight));
  const panelWidth = Math.max(0, finite(measurement.panelWidth));
  const panelHeight = Math.max(0, finite(measurement.panelHeight));
  const panelLeft = finite(measurement.panelLeft);
  const valid = stageWidth > 0 && stageHeight > 0 && panelWidth > 0 &&
    panelHeight > 0 && panelWidth <= stageWidth && panelHeight <= stageHeight &&
    panelLeft >= 0 && panelLeft + panelWidth <= stageWidth + .5;
  return {
    stageWidth, stageHeight, panelWidth, panelHeight, panelLeft, valid,
    open: 0, closed: valid ? stageWidth - panelLeft : 0,
    min: valid ? -Math.min(18, panelLeft) : 0,
    max: valid ? stageWidth - panelLeft : 0,
  };
}

export function initialPhysicalDrawer({ geometry = {}, permission = true, parameters: input = {} } = {}) {
  const g = drawerGeometry(geometry);
  return {
    componentVersion: DRAWER_VERSION, parameterVersion: PARAMETER_VERSION,
    geometry: g, parameters: parameters(input), permission: !!permission,
    source: null, intent: 'closed', phase: g.valid ? 'closed' : 'unavailable',
    x: g.closed, v: 0, target: g.closed, elapsed: 0, epoch: 0,
  };
}

function targetFor(state, geometry = state.geometry) {
  return state.intent === 'open' && state.permission ? geometry.open : geometry.closed;
}

function landed(state) {
  const target = targetFor(state);
  return {
    ...state, x: target, v: 0, target,
    phase: state.geometry.valid ? state.intent : 'unavailable',
    source: state.intent === 'closed' || !state.permission ? null : state.source,
  };
}

function phaseFor(state) {
  if (!state.geometry.valid) return 'unavailable';
  if (state.x === state.target && state.v === 0) return state.intent;
  return state.intent === 'open' ? 'opening' : 'closing';
}

/** Pure transition function. An action changes the target, never resets active
 * x/v. Only safety/lifecycle boundaries, reduced motion, and legal bounds snap.
 * The epoch makes callbacks queued before a target/lifecycle change harmless.
 */
export function physicalDrawerReduce(state, event = {}) {
  if (state.phase === 'disposed') return state;
  if (event.type === 'step') {
    if (event.epoch !== undefined && event.epoch !== state.epoch) return state;
    if (!state.geometry.valid || !['opening', 'closing'].includes(state.phase)) return state;
    const p = parameters(event.parameters || state.parameters);
    if (event.reduce) return landed({ ...state, parameters: p, epoch: state.epoch + 1 });
    const dt = clamp(finite(event.dt), 0, DRAWER_MAX_STEP);
    if (!dt) return state;
    const next = spring({ x: state.x, v: state.v }, state.target, dt, p);
    const x = clamp(finite(next.x, state.target), state.geometry.min, state.geometry.max);
    let v = finite(next.v);
    if ((x === state.geometry.min && v < 0) || (x === state.geometry.max && v > 0)) v = 0;
    let result = { ...state, x, v, parameters: p, elapsed: state.elapsed + dt };
    result.phase = phaseFor(result);
    if (result.phase === 'closed') result.source = null;
    return result;
  }

  if (!['open', 'close', 'geometry', 'revoke', 'restore-permission', 'reduce', 'suspend', 'dispose'].includes(event.type)) return state;
  let next = { ...state, epoch: state.epoch + 1, parameters: parameters(event.parameters || state.parameters) };
  if (event.type === 'dispose') return { ...landed({ ...next, intent: 'closed', source: null }), phase: 'disposed' };
  if (event.type === 'revoke') return landed({ ...next, permission: false, intent: 'closed', source: null });
  if (event.type === 'restore-permission') return landed({ ...next, permission: true, intent: 'closed', source: null });
  if (event.type === 'reduce' || event.type === 'suspend') return landed(next);
  if (event.type === 'geometry') {
    const g = drawerGeometry(event.geometry);
    next.geometry = g;
    next.target = targetFor(next, g);
    if (!g.valid || !state.geometry.valid || state.phase === 'closed' || state.phase === 'open' || event.reduce) return landed(next);
    next.x = clamp(state.x, g.min, g.max);
    if ((next.x === g.min && next.v < 0) || (next.x === g.max && next.v > 0)) next.v = 0;
    next.phase = phaseFor(next);
    if (next.phase === 'closed') next.source = null;
    return next;
  }
  if (event.type === 'open') {
    if (!state.permission) return landed({ ...next, intent: 'closed', source: null });
    const source = event.source || state.source;
    if (!source || typeof source.id !== 'string') return state;
    // Copy only read-only display fields. The reducer has no write/save/publish action.
    next.source = Object.fromEntries(['id', 'title', 'body', 'provenance'].map(key => [key, String(source[key] || '')]));
    next.intent = 'open';
  } else if (event.type === 'close') next.intent = 'closed';
  next.target = targetFor(next);
  if (event.reduce || !next.geometry.valid) return landed(next);
  next.phase = phaseFor(next);
  if (next.phase === 'closed') next.source = null;
  return next;
}

/** Trace excludes source text and the editable page. Parameters are the values
 * used by the most recent real simulation step, not labels or duration tokens.
 */
export function drawerSample(state, time = state.elapsed) {
  const { mass, stiffness, damping } = state.parameters;
  return {
    componentVersion: DRAWER_VERSION, parameterVersion: PARAMETER_VERSION,
    unit: 'CSS px / seconds / px per second / relative mass',
    t: finite(time, state.elapsed), simulationTime: state.elapsed,
    x: state.x, v: state.v, target: state.target, phase: state.phase,
    epoch: state.epoch, permission: state.permission,
    parameters: { mass, stiffness, damping }, geometry: { ...state.geometry },
  };
}
