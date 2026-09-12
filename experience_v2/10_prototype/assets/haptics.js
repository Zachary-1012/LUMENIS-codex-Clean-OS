/* ============================================================================
 * LUMENIS V2.5 — Haptics / tactile layer (embodied-ready)
 * Every interactive surface gets a physical, channeled response.
 *
 *  Web today  : navigator.vibrate() where supported (Android/Chrome mobile),
 *               always paired with CSS :active press (see components/shell).
 *  Hardware   : every impact also dispatches CustomEvent('lum:haptic') so a
 *               future native shell / embodied device (wearable, controller,
 *               tactile surface) can bind a real actuator without touching UI.
 *  Safety     : respects prefers-reduced-motion + user master switch; never
 *               throws; absence of an actuator is a silent no-op.
 *
 *  Channels are semantic, not device-specific — Codex binds actuators later.
 * ========================================================================== */
(function (global) {
  'use strict';
  const reduce = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const STORE = 'lum-haptics';
  // ms patterns for Vibration API; iOS Safari = no-op by design.
  const PATTERNS = {
    tick: 8,
    press: 12,
    select: [10, 24, 10],
    toggle: 9,
    nav: 14,
    confirm: [12, 30, 12],
    success: [14, 36, 26],
    warning: [20, 40, 20, 40, 20],
    error: [44],
    'ai-step': 8,
    evidence: 10,
    heavy: 30
  };
  // Brand motion verbs (Motion System V2.5) -> physical channels. Designers and
  // Codex call the verb; the actuator mapping stays semantic and device-agnostic.
  const VERB = {
    touch: 'press',      // Touch : contact confirmed
    open: 'confirm',     // Open  : a stratum/realm opens
    trace: 'evidence',   // Trace : travelling along an evidence path
    shift: 'select',     // Shift : focus/tab/view change
    settle: 'tick',      // Settle: value/element lands (soft, near-silent)
    return: 'nav'        // Return: back to subject / origin
  };
  let enabled = true;
  try { enabled = localStorage.getItem(STORE) !== 'off'; } catch (e) {}
  if (reduce) enabled = false;

  function vibrate(p) {
    try { if (enabled && navigator.vibrate) navigator.vibrate(p); } catch (e) {}
  }

  function impact(channel, payload) {
    let ch = PATTERNS[channel] ? channel : (VERB[channel] || 'press');
    vibrate(PATTERNS[ch]);
    // hardware / embodied bridge — a native shell listens and drives actuators.
    global.dispatchEvent(new CustomEvent('lum:haptic', {
      detail: Object.assign({ channel: ch, at: Date.now() }, payload || {}), bubbles: true
    }));
  }

  function setEnabled(v) {
    enabled = !!v;
    try { localStorage.setItem(STORE, enabled ? 'on' : 'off'); } catch (e) {}
  }

  // ---- automatic wiring (delegation, pointer-first) ----
  const SELECTOR = 'button,a.lum-nav-item,.lum-press,.lum-chip,.lum-action-item,.lum-dock__item,.lum-list-item,[role="button"],.lum-tabs button,.lum-segmented button';
  function bind(root) {
    const scope = root || document;
    scope.addEventListener('pointerdown', (e) => {
      const el = e.target.closest && e.target.closest(SELECTOR);
      if (!el) return;
      if (el.matches('[aria-disabled="true"],[disabled]')) return;
      let ch = 'press';
      const risk = el.dataset.risk || (el.closest('[data-risk]') || {}).dataset && el.closest('[data-risk]').dataset.risk;
      if (el.classList.contains('lum-nav-item') || el.classList.contains('lum-dock__item')) ch = 'nav';
      else if (el.classList.contains('lum-segmented') || el.closest('.lum-segmented')) ch = 'select';
      else if (risk === 'high' || el.classList.contains('lum-btn-effect-risk')) ch = 'warning';
      impact(ch, { source: 'pointerdown', target: el.className });
    }, { passive: true });
    // semantic outcomes from existing UI events
    scope.addEventListener('lum:toast', (e) => {
      const tone = e.detail && e.detail.tone;
      if (tone === 'success') impact('success');
      else if (tone === 'error' || tone === 'danger') impact('error');
      else if (tone === 'warning') impact('warning');
    });
    scope.addEventListener('lum:ai-step', () => impact('ai-step'));
  }

  global.LumHaptics = { impact, bind, setEnabled,
    get enabled() { return enabled; }, CHANNELS: Object.keys(PATTERNS),
    VERBS: Object.keys(VERB) };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => bind(), { once: true });
  else bind();
})(window);
