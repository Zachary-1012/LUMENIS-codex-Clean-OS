/* ============================================================================
   LUMENIS · LumOrb — the AI sphere ("混沌/星云" internal flow).
   Self-contained vanilla canvas, zero dependencies.
   - Nebula wisps drift on slow orbital paths INSIDE a clipped sphere, looping.
   - Colour follows data-status: idle(silver) / processing(icy) / success /
     warning / danger. Theme follows closest .lum-app[data-theme]:
       light = BLACK-SILVER sphere (silver wisps on black-chrome)
       dark  = WHITE-SILVER sphere (shadow wisps on silver)  — the inverse.
   - prefers-reduced-motion renders a single composed frame (no rAF loop).
   ========================================================================== */
(function (global) {
  'use strict';
  const STATUS = {
    idle:       { light: [216, 222, 232], dark: [58, 62, 72],  speed: 1 },
    processing: { light: [126, 224, 255], dark: [40, 96, 120], speed: 1.9 },
    success:    { light: [110, 214, 168], dark: [40, 104, 78], speed: 1.2 },
    warning:    { light: [240, 186, 96],  dark: [120, 86, 34], speed: 1.3 },
    danger:     { light: [255, 128, 138], dark: [128, 48, 56], speed: 1.4 }
  };
  const WISPS = [
    { orbit: .28, rad: .62, phase: 0.0,  spin: .19, bob: 1.7, alpha: .50 },
    { orbit: .42, rad: .50, phase: 2.1,  spin: -.15, bob: 1.3, alpha: .42 },
    { orbit: .20, rad: .44, phase: 4.0,  spin: .26, bob: 2.1, alpha: .46 },
    { orbit: .50, rad: .38, phase: 1.05, spin: -.21, bob: 1.1, alpha: .36 },
    { orbit: .34, rad: .56, phase: 5.2,  spin: .13, bob: 1.9, alpha: .40 },
    { orbit: .12, rad: .34, phase: 3.3,  spin: -.30, bob: 2.4, alpha: .30 }
  ];
  const registry = new Set();
  let rafOn = false;

  function themeOf(canvas) {
    const app = canvas.closest('.lum-app');
    return app && app.dataset.theme === 'dark' ? 'dark' : 'light';
  }

  function drawFrame(canvas, t) {
    const ctx = canvas.__orb; if (!ctx) return;
    const dpr = canvas.__dpr || 1;
    const W = canvas.width / dpr, H = canvas.height / dpr;
    const cx = W / 2, cy = H / 2, R = Math.min(W, H) / 2;
    const status = STATUS[canvas.dataset.status] || STATUS.idle;
    const dark = themeOf(canvas) === 'dark';
    const sp = status.speed;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, R - .5, 0, Math.PI * 2); ctx.clip();

    // base sphere — black-chrome (light) / silver (dark)
    const base = ctx.createRadialGradient(cx - R * .32, cy - R * .36, R * .1, cx, cy, R);
    if (dark) { base.addColorStop(0, '#ffffff'); base.addColorStop(.55, '#d9dce2'); base.addColorStop(1, '#9ea4af'); }
    else      { base.addColorStop(0, '#33363d'); base.addColorStop(.55, '#16181d'); base.addColorStop(1, '#040508'); }
    ctx.fillStyle = base; ctx.fillRect(0, 0, W, H);

    // swirling nebula wisps
    // soft inner nebula core so the sphere reads as a contained cloud, not flat fill
    const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * .92);
    if (dark) { core.addColorStop(0, 'rgba(120,124,134,.20)'); core.addColorStop(1, 'rgba(120,124,134,0)'); }
    else      { core.addColorStop(0, 'rgba(190,198,214,.22)'); core.addColorStop(1, 'rgba(190,198,214,0)'); }
    ctx.fillStyle = core; ctx.beginPath(); ctx.arc(cx, cy, R * .92, 0, Math.PI * 2); ctx.fill();

    ctx.globalCompositeOperation = dark ? 'multiply' : 'lighter';
    const tint = dark ? status.dark : status.light;
    for (let i = 0; i < WISPS.length; i++) {
      const w = WISPS[i];
      const a = t * .00032 * w.spin * sp + w.phase;
      const wob = Math.sin(t * .0006 * w.bob + w.phase) * .10;
      const ox = Math.cos(a) * R * (w.orbit + wob);
      const oy = Math.sin(a * 1.18) * R * (w.orbit * .8 + wob);
      const rr = R * w.rad * (1 + .12 * Math.sin(t * .0008 * w.bob + i));
      const g = ctx.createRadialGradient(cx + ox, cy + oy, 0, cx + ox, cy + oy, rr);
      const al = Math.min(.85, w.alpha * (dark ? .55 : 1.35));
      g.addColorStop(0, `rgba(${tint[0]},${tint[1]},${tint[2]},${al})`);
      g.addColorStop(1, `rgba(${tint[0]},${tint[1]},${tint[2]},0)`);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(cx + ox, cy + oy, rr, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';

    // slow rotating inner turbulence band (the "flow")
    ctx.save();
    ctx.translate(cx, cy); ctx.rotate(t * .00018 * sp);
    const band = ctx.createLinearGradient(-R, 0, R, 0);
    if (dark) { band.addColorStop(0, 'rgba(255,255,255,0)'); band.addColorStop(.5, 'rgba(255,255,255,.20)'); band.addColorStop(1, 'rgba(255,255,255,0)'); }
    else      { band.addColorStop(0, 'rgba(255,255,255,0)'); band.addColorStop(.5, 'rgba(255,255,255,.10)'); band.addColorStop(1, 'rgba(255,255,255,0)'); }
    ctx.fillStyle = band; ctx.fillRect(-R, -R * .16, R * 2, R * .32);
    ctx.restore();

    // metallic specular catch-light (upper-left)
    const spec = ctx.createRadialGradient(cx - R * .38, cy - R * .42, 0, cx - R * .38, cy - R * .42, R * .85);
    spec.addColorStop(0, dark ? 'rgba(255,255,255,.85)' : 'rgba(255,255,255,.30)');
    spec.addColorStop(.4, 'rgba(255,255,255,0)');
    ctx.fillStyle = spec; ctx.fillRect(0, 0, W, H);
    // lower bounce shadow
    const sh = ctx.createRadialGradient(cx + R * .3, cy + R * .5, 0, cx + R * .3, cy + R * .5, R * .8);
    sh.addColorStop(0, dark ? 'rgba(20,22,28,.28)' : 'rgba(0,0,0,.55)'); sh.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = sh; ctx.fillRect(0, 0, W, H);
    ctx.restore();

    // metal rim
    ctx.beginPath(); ctx.arc(cx, cy, R - 1, 0, Math.PI * 2);
    ctx.lineWidth = 1;
    ctx.strokeStyle = dark ? 'rgba(255,255,255,.7)' : 'rgba(255,255,255,.22)';
    ctx.stroke();
  }

  function mount(canvas) {
    if (!canvas || canvas.__orb) return;
    const dpr = Math.min(global.devicePixelRatio || 1, 2.5);
    const size = () => {
      const s = Math.max(canvas.clientWidth || 48, canvas.clientHeight || 48);
      canvas.width = Math.round(s * dpr); canvas.height = Math.round(s * dpr);
    };
    size();
    canvas.__dpr = dpr;
    canvas.__orb = canvas.getContext('2d');
    canvas.__ro = new ResizeObserver(size); canvas.__ro.observe(canvas);
    const reduced = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) { drawFrame(canvas, 1400); return; }
    registry.add(canvas);
    start();
  }
  function setStatus(canvas, status) { if (canvas) canvas.dataset.status = STATUS[status] ? status : 'idle'; }

  let last = 0;
  function tick(ts) {
    if (!registry.size) { rafOn = false; return; }
    registry.forEach(c => { if (c.isConnected) drawFrame(c, ts); else registry.delete(c); });
    last = ts;
    global.requestAnimationFrame(tick);
  }
  function start() { if (!rafOn) { rafOn = true; global.requestAnimationFrame(tick); } }

  function mountAll(root) { (root || document).querySelectorAll('canvas.lum-orb').forEach(mount); }

  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', () => { if (!document.hidden) start(); });
  }
  global.LumOrb = { mount, mountAll, setStatus };
})(window);
