/* ============================================================================
 * LUMENIS Experience V2 — MotionSequence runtime (self-built, no Anime.js)
 * Labels: press · recede · morph · content · settle
 * CAPABILITY -> TASK timeline: T+0 / +80 / +140 / +260 / +340 / +420 / +480
 * Rules (Supplement V2.1 sec10):
 *   - stagger at most 5 groups (0/40/80/120/160ms); long lists enter as one.
 *   - every sequence is interruptible and cancels cleanly.
 *   - prefers-reduced-motion -> jump to final state instantly, no fake motion.
 *   - every played motion must carry a semantic_reason (no decoration-only anim).
 *   - never animate a "thinking" loop to imply work that is not happening.
 * Exposes window.LumMotion
 * ========================================================================== */
(function (global) {
  'use strict';
  const reduce = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

  // CAPABILITY -> TASK choreography (ms). Anchors are semantic, not decorative.
  const TASK_MORPH_TIMELINE = {
    t0_recognize: 0, t80_capability_recede: 80, t140_surface_morph: 140,
    t260_context_resolve: 260, t340_content_in: 340, t420_evidence_settle: 420, t480_idle: 480
  };

  const cssVar = (el, name) => getComputedStyle(el).getPropertyValue(name).trim();
  const dur = (el, token) => {
    const v = cssVar(el || document.documentElement, token);
    return v ? parseFloat(v) : undefined;
  };

  /** Cancel all WAAPI animations on an element (interruptibility). */
  function interrupt(el) {
    if (el && el.getAnimations) el.getAnimations().forEach(a => a.cancel());
  }

  /** Play a single WAAPI effect with semantic reason + reduced-motion bypass. */
  function play(el, keyframes, opts = {}) {
    if (!el) return null;
    if (!opts.semantic_reason) {
      // Hard rule: motion without a semantic reason is rejected in dev.
      console.warn('[LumMotion] motion rejected: missing semantic_reason', el);
      return null;
    }
    if (reduce.matches) { // jump to end state
      const last = keyframes[keyframes.length - 1];
      Object.assign(el.style, last);
      if (opts.onfinish) opts.onfinish();
      return null;
    }
    interrupt(el);
    const anim = el.animate(keyframes, Object.assign({
      duration: dur(el, '--lum-dur-base') || 320,
      easing: cssVar(el, '--lum-ease-standard') || 'cubic-bezier(.2,.7,.2,1)',
      fill: 'both'
    }, opts.waapi || {}));
    if (opts.onfinish) anim.onfinish = opts.onfinish;
    return anim;
  }

  /** press / recede micro-interaction on pointer activation. */
  function press(el) {
    return play(el, [{ transform: 'scale(1)' }, { transform: 'scale(.96)' }, { transform: 'scale(1)' }],
      { duration: 180, semantic_reason: 'acknowledge_user_press', waapi: { easing: 'ease-out' } });
  }
  function recede(el, on) {
    el.classList.toggle('lum-is-receded', !!on);
  }

  /** morph: old content exits, new enters (used by CAPABILITY->TASK & tab switch). */
  function morph(outEl, inEl, opts = {}) {
    if (outEl) play(outEl, [{ opacity: 1, transform: 'none', filter: 'blur(0)' },
      { opacity: 0, transform: 'translateY(-6px) scale(.99)', filter: 'blur(2px)' }],
      { duration: 220, semantic_reason: 'old_capability_recede_before_task_morph', waapi: { fill: 'forwards' } });
    return play(inEl, [
      { opacity: 0, transform: 'translateY(10px) scale(.99)', filter: 'blur(3px)' },
      { opacity: 1, transform: 'none', filter: 'blur(0)' }],
      { duration: 520, delay: reduce.matches ? 0 : 140, easing: 'cubic-bezier(.2,0,0,1)',
        semantic_reason: opts.reason || 'surface_morph_to_new_task_context' });
  }

  /** content entrance for a block; supports settle label. */
  function contentIn(el, label = 'content', delay = 0) {
    const map = {
      content: [['lum-fade-up', 320]],
      settle: [['lum-settle', 480]],
      scale: [['lum-scale-in', 320]]
    };
    el.classList.remove('lum-anim-fade-up', 'lum-settle', 'lum-anim-scale-in');
    void el.offsetWidth; // restart
    if (reduce.matches) { el.style.opacity = 1; el.style.transform = 'none'; return; }
    const [cls, d] = map[label] || map.content;
    el.classList.add(label === 'settle' ? 'lum-settle' : cls);
    el.style.animationDelay = delay + 'ms';
  }

  /** Stagger children, capped at 5 delay groups (nth-child n+5 share 160ms via CSS). */
  function stagger(container, { reason = 'grouped_content_entrance', label = 'content' } = {}) {
    if (!container) return;
    const kids = Array.from(container.children);
    if (reduce.matches) { kids.forEach(k => { k.style.opacity = 1; k.style.transform = 'none'; }); return; }
    container.classList.add('lum-stagger');
    kids.forEach((k, i) => { const g = Math.min(i, 4); k.style.animationDelay = (g * 40) + 'ms'; contentIn(k, label); });
  }

  /** Full CAPABILITY -> TASK choreography against named stage elements. */
  function taskMorph(stages, opts = {}) {
    // stages: {capability, surface, context, content, evidence}
    const T = TASK_MORPH_TIMELINE;
    if (stages.capability) play(stages.capability, [{ opacity: 1 }, { opacity: .42, transform: 'scale(.985)' }],
      { duration: 140, delay: T.t80_capability_recede, fill: 'both', semantic_reason: 'capability_recede' });
    if (stages.surface) morph(stages.outSurface, stages.surface, { reason: 'capability_to_task_surface_morph' });
    if (stages.context) contentIn(stages.context, 'content', reduce.matches ? 0 : T.t260_context_resolve - T.t140_surface_morph);
    if (stages.content) contentIn(stages.content, 'content', reduce.matches ? 0 : T.t340_content_in - T.t140_surface_morph);
    if (stages.evidence) contentIn(stages.evidence, 'settle', reduce.matches ? 0 : T.t420_evidence_settle - T.t140_surface_morph);
  }

  /** Count-up for metrics (sets final instantly under reduced-motion). */
  function countUp(el, to, { duration = 700, decimals = 0, prefix = '', suffix = '' } = {}) {
    const start = parseFloat(el.dataset.from || '0') || 0;
    const fmt = n => prefix + n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix;
    if (reduce.matches || !global.requestAnimationFrame) { el.textContent = fmt(to); return; }
    const t0 = performance.now();
    function tick(t) {
      const p = Math.min(1, (t - t0) / duration);
      const e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(start + (to - start) * e);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /** Reveal-on-scroll using IntersectionObserver (long lists enter as one block). */
  function observeReveal(root = document) {
    const els = root.querySelectorAll('[data-reveal]');
    if (!('IntersectionObserver' in global) || reduce.matches) { els.forEach(e => e.classList.add('is-in')); return; }
    const io = new IntersectionObserver((entries) => {
      entries.forEach(en => { if (en.isIntersecting) { contentIn(en.target, en.target.dataset.reveal || 'content'); io.unobserve(en.target); } });
    }, { threshold: .08 });
    els.forEach(e => io.observe(e));
  }

  global.LumMotion = { play, press, recede, morph, contentIn, stagger, taskMorph, countUp, observeReveal, interrupt, TASK_MORPH_TIMELINE, reduce };
})(window);
