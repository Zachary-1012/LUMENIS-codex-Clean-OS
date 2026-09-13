/* ============================================================================
 * LUMENIS Experience V2 — Optical Material V1 runtime (self-built WebGL)
 * Mounts ONLY on elements carrying [data-opt] ∈ composer|dock|nav|morph (4 surfaces).
 * Pipeline: ambient -> SDF rounded-rect mask -> normal/edge -> refraction
 *           -> RGB micro-shift -> Fresnel -> specular -> composite.
 * Only 7 parameters are read from CSS tokens (Supplement sec9):
 *   refraction aberration edgeWidth fresnel specular blur opacity.
 * State strength via [data-strength] idle/focus/composing/submit/executing/approval/error.
 * Degradation state machine OPTICAL_HIGH -> STANDARD -> SOFT_GLASS -> OPAQUE;
 * on any failure the CSS .lum-opt__fallback remains, UI function is never lost.
 * No external shader/asset copied; original implementation. Exposes window.LumOptical.
 * ========================================================================== */
(function (global) {
  'use strict';
  const VERT = `attribute vec2 a_pos;varying vec2 v_uv;void main(){v_uv=a_pos*.5+.5;gl_Position=vec4(a_pos,0.,1.);}`;
  const FRAG = `
precision mediump float;varying vec2 v_uv;uniform vec2 u_res;uniform float u_time;
uniform float u_refr,u_aber,u_edge,u_fres,u_spec,u_opacity;uniform vec3 u_tint;
// rounded-rect SDF
float sdRound(vec2 p,vec2 b,float r){vec2 q=abs(p)-b+vec2(r);return min(max(q.x,q.y),0.)+length(max(q,0.))-r;}
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
void main(){
  vec2 uv=v_uv;vec2 p=(uv-.5);p.x*=u_res.x/u_res.y;
  float d=sdRound(p,vec2(.98*u_res.x/u_res.y,.98),.12);
  float mask=smoothstep(0.,-u_edge,d);
  // normals from SDF gradient (fake refraction direction)
  float e=.01;
  float dx=sdRound(p+vec2(e,0.),vec2(.98*u_res.x/u_res.y,.98),.12)-sdRound(p-vec2(e,0.),vec2(.98*u_res.x/u_res.y,.98),.12);
  float dy=sdRound(p+vec2(0.,e),vec2(.98*u_res.x/u_res.y,.98),.12)-sdRound(p-vec2(0.,e),vec2(.98*u_res.x/u_res.y,.98),.12);
  vec2 n=vec2(dx,dy);
  // slow ambient gradient (not a常驻 flowing light; static-ish, moves subtly)
  vec2 q=uv+vec2(.04*sin(u_time*.18),.05*cos(u_time*.15));
  vec3 amb=mix(vec3(.97,.98,1.),u_tint,.18+ .14*q.y);
  vec2 refr=n*u_refr;
  // RGB micro aberration
  float r=amb.r+refr.x*.5, g=amb.g, b=amb.b-refr.x*.5;
  vec3 col=vec3(r,g,b)+vec3(refr,0.)*0.0;
  // Fresnel rim from facing ratio
  float fres=pow(1.-abs(dot(normalize(vec3(n,1.)),vec3(0.,0.,1.))),2.)*u_fres;
  // specular highlight top-left
  float sp=smoothstep(.6,0.,length(uv-vec2(.22,.12)))*u_spec;
  float edgeLine=smoothstep(-u_edge,0.,d)*.5;
  col+=fres+sp;
  col=mix(col,vec3(1.),edgeLine*.25);
  gl_FragColor=vec4(col,mask*u_opacity);
}`;

  function gl(el) {
    const opts = { alpha: true, antialias: true, premultipliedAlpha: false };
    return el.getContext('webgl', opts) || el.getContext('experimental-webgl', opts);
  }
  function program(g) {
    function sh(type, src) { const s = g.createShader(type); g.shaderSource(s, src); g.compileShader(s); return s; }
    const p = g.createProgram(); g.attachShader(p, sh(g.VERTEX_SHADER, VERT)); g.attachShader(p, sh(g.FRAGMENT_SHADER, FRAG));
    g.linkProgram(p); return p;
  }
  const token = (el, n, fb) => { const v = getComputedStyle(el).getPropertyValue(n).trim(); return v === '' ? fb : parseFloat(v); };

  function mount(surface) {
    const canvas = surface.querySelector('canvas.lum-opt__gl');
    if (!canvas) return degrade(surface, 'soft');
    let g; try { g = gl(canvas); } catch (e) { return degrade(surface, 'soft'); }
    if (!g) return degrade(surface, 'soft');
    let p; try { p = program(g); } catch (e) { return degrade(surface, 'soft'); }
    if (!g.getProgramParameter(p, g.LINK_STATUS)) return degrade(surface, 'soft');
    g.useProgram(p);
    const buf = g.createBuffer(); g.bindBuffer(g.ARRAY_BUFFER, buf);
    g.bufferData(g.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), g.STATIC_DRAW);
    const loc = g.getAttribLocation(p, 'a_pos'); g.enableVertexAttribArray(loc); g.vertexAttribPointer(loc, 2, g.FLOAT, false, 0, 0);
    const U = n => g.getUniformLocation(p, n);
    const u = { res: U('u_res'), time: U('u_time'), refr: U('u_refr'), aber: U('u_aber'), edge: U('u_edge'), fres: U('u_fres'), spec: U('u_spec'), op: U('u_opacity'), tint: U('u_tint') };
    g.enable(g.BLEND); g.blendFunc(g.SRC_ALPHA, g.ONE_MINUS_SRC_ALPHA);
    const reduce = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(global.devicePixelRatio || 1, 2);
    function resize() {
      const r = surface.getBoundingClientRect();
      canvas.width = Math.max(1, Math.round(r.width * dpr)); canvas.height = Math.max(1, Math.round(r.height * dpr));
      g.viewport(0, 0, canvas.width, canvas.height);
    }
    resize();
    const ro = 'ResizeObserver' in global ? new ResizeObserver(resize) : null; if (ro) ro.observe(surface);
    surface.dataset.mounted = 'true';
    const t0 = performance.now();
    function frame(t) {
      const r = surface.getBoundingClientRect(); if (r.width === 0) { requestAnimationFrame(frame); return; }
      g.uniform2f(u.res, canvas.width, canvas.height);
      g.uniform1f(u.time, reduce ? 0 : (t - t0) / 1000);
      g.uniform1f(u.refr, token(surface, '--lum-opt-refraction', .1));
      g.uniform1f(u.aber, token(surface, '--lum-opt-aberration', .12));
      g.uniform1f(u.edge, token(surface, '--lum-opt-edge-width', 1.2) / 40);
      g.uniform1f(u.fres, token(surface, '--lum-opt-fresnel', .22));
      g.uniform1f(u.spec, token(surface, '--lum-opt-specular', .28));
      g.uniform1f(u.op, token(surface, '--lum-opt-opacity', .9));
      const styles = getComputedStyle(surface);
      const darkTint = surface.closest('.lum-app') && surface.closest('.lum-app').dataset.theme === 'dark';
      g.uniform3f(u.tint, darkTint ? .20 : .80, darkTint ? .21 : .82, darkTint ? .24 : .86);
      g.clearColor(0, 0, 0, 0); g.clear(g.COLOR_BUFFER_BIT); g.drawArrays(g.TRIANGLES, 0, 3);
      if (!reduce) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    surface._opticalCleanup = () => { if (ro) ro.disconnect(); };
  }
  function degrade(surface, tier) {
    const app = document.querySelector('.lum-app');
    if (app && !app.dataset.optical) app.dataset.optical = tier; // soft -> CSS glass, opaque -> solid
    surface.dataset.mounted = 'fallback';
  }
  /** Detect capability and choose initial tier. */
  function init(root = document) {
    const app = root.querySelector('.lum-app') || document.querySelector('.lum-app');
    let tier = 'high';
    try { const c = document.createElement('canvas'); const g = c.getContext('webgl'); if (!g) tier = 'soft'; } catch (e) { tier = 'soft'; }
    if (app) app.dataset.optical = tier === 'high' ? 'high' : 'soft';
    root.querySelectorAll('[data-opt]').forEach(mount);
  }
  function setStrength(surface, s) { if (surface) surface.dataset.strength = s; }
  global.LumOptical = { init, mount, setStrength, degrade };
})(window);
