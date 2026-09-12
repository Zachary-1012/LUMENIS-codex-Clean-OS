/* ============================================================================
 * LUMENIS Experience V2.5 — Lumen Core (the AI Orb, WebGL1, zero dependency)
 * A signature Glyph, not a glowing toy: Point + Axis + two Boundaries +
 * state-density. Inside the sphere, domain-warped turbulence flows like a
 * quiet current ("混沌流转"); there are deliberately NO stars / particles.
 * Monochrome metal: light theme = black-chrome (SH-01 黑银),
 *                   dark theme  = white-silver (AI-01 白银， the inverse).
 * Icy tint appears ONLY while processing — state is legible, never decorative.
 * Contract preserved: window.LumOrb = { mount, mountAll, setStatus };
 * binds to <canvas class="lum-orb" data-status>. Codex drives setStatus().
 * ========================================================================== */
(function (global) {
  'use strict';

  const VERT = [
    'attribute vec2 a_pos;',
    'void main(){ gl_Position = vec4(a_pos,0.0,1.0); }'
  ].join('\n');

  // Ashima/Stefan Gustavson simplex 3D (MIT) — deterministic, no textures.
  const NOISE = `
  vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
  vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
  vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
  vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
  float snoise(vec3 v){
    const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
    vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx);
    vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=1.0-max(g.xyz,l.zxy);
    vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy;
    i=mod289(i);
    vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
    float n_=0.142857142857; vec3 ns=n_*D.wyz-D.xzx;
    vec4 j=p-49.0*floor(p*ns.z*ns.z);
    vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
    vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y);
    vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
    vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0));
    vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
    vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
    vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
    p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
    vec4 m=max(0.5-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m;
    return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
  }
  float fbm(vec3 p){
    float a=0.5; float s=0.0;
    for(int i=0;i<4;i++){ s+=a*snoise(p); p*=2.02; a*=0.5; }
    return s;
  }`;

  const FRAG = `
  precision mediump float;
  uniform vec2 u_res; uniform float u_time; uniform float u_theme; uniform float u_state; uniform float u_reduced;
  ${NOISE}
  void main(){
    vec2 uv=(gl_FragCoord.xy-0.5*u_res)/min(u_res.x,u_res.y);
    float r=0.46;
    float d=length(uv);
    float aa=1.5/min(u_res.x,u_res.y);          // ~1.5px edge AA (WebGL1-safe, no fwidth)
    float mask=1.0-smoothstep(r-aa,r+aa,d);
    if(mask<=0.001){ gl_FragColor=vec4(0.0); return; }
    vec3 N=normalize(vec3(uv, sqrt(max(0.0, r*r-dot(uv,uv)))));
    vec3 V=vec3(0.0,0.0,1.0);
    vec3 L=normalize(vec3(-0.45,0.62,0.72));      // key light, upper-left-front
    float diff=max(dot(N,L),0.0);
    vec3 Rf=reflect(-L,N); float spec=pow(max(dot(Rf,V),0.0),26.0);
    float t=u_reduced>0.5?1.7:u_time;
    float speed = u_state>0.5&&u_state<1.5 ? 1.7 : 0.55;   // processing flows faster
    // domain-warped turbulence streaming along the vertical 序轴 (no stars)
    vec3 q=vec3(N.xy*1.5, N.z*1.5);
    float w=fbm(q + vec3(0.0, t*0.10*speed, t*0.05*speed));
    vec3 pp=q + 0.5*vec3(w, fbm(q+vec3(5.2,1.3,0.0)+t*0.06*speed), fbm(q-vec3(1.7,9.2,3.1)));
    float turb=fbm(pp*1.9 + vec3(0.0,-t*0.14*speed, t*0.04));
    turb=turb*0.5+0.5;
    float filament=pow(turb,2.3);                 // high-contrast flowing streaks
    float fres=pow(1.0-max(dot(N,V),0.0), 2.2);   // metal catch-light rim
    vec3 icyProc=vec3(0.436,0.769,0.949);         // #6FD6F2, state-only
    vec3 col;
    if(u_theme<0.5){
      // black-chrome 黑银: deep ink body, silver filaments + sheen + bright rim
      vec3 ink=vec3(0.055,0.062,0.078);
      vec3 silver=vec3(0.80,0.82,0.86);
      col=mix(ink, silver*0.66, filament*0.66);
      col+=silver*(diff*0.12+spec*0.6);
      col=mix(col,silver,fres*0.92);
      if(u_state>0.5&&u_state<1.5) col=mix(col,icyProc,0.16*filament);
    } else {
      // white-silver 白银 (inverse): luminous silver body, graphite filaments
      vec3 graphite=vec3(0.42,0.45,0.50);
      vec3 white=vec3(0.975,0.98,1.0);
      col=mix(white, graphite, (1.0-filament)*0.40);
      col+=white*(diff*0.10+spec*0.45);
      col=mix(col,white,fres*0.9);
      if(u_state>0.5&&u_state<1.5) col=mix(col,icyProc,0.18*filament);
    }
    gl_FragColor=vec4(col, mask*(0.97+0.03*fres));
  }`;

  function compile(gl, type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.error('[LumOrb] shader compile error:', gl.getShaderInfoLog(s));
    }
    return s;
  }

  function createOrb(canvas) {
    const gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: true, depth: false, preserveDrawingBuffer: true });
    if (!gl) { canvas.style.background = 'radial-gradient(circle at 36% 30%,#3a3d45,#0c0d10 68%)'; return null; }
    const prog = gl.createProgram();
    gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) console.error('[LumOrb] link error:', gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'a_pos');
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const U = {};
    ['u_res', 'u_time', 'u_theme', 'u_state', 'u_reduced'].forEach(n => { U[n] = gl.getUniformLocation(prog, n); });
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    const reduced = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let status = 0, raf = null, start = performance.now(), visible = true;

    function themeValue() {
      const app = document.querySelector('.lum-app');
      return app && app.dataset.theme === 'dark' ? 1 : 0;
    }
    function resize() {
      const dpr = Math.min(global.devicePixelRatio || 1, 2);
      const w = Math.max(2, Math.round(canvas.clientWidth * dpr));
      const h = Math.max(2, Math.round(canvas.clientHeight * dpr));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      gl.viewport(0, 0, canvas.width, canvas.height);
    }
    function frame(now) {
      resize();
      gl.uniform2f(U.u_res, canvas.width, canvas.height);
      gl.uniform1f(U.u_time, (now - start) / 1000);
      gl.uniform1f(U.u_theme, themeValue());
      gl.uniform1f(U.u_state, status);
      gl.uniform1f(U.u_reduced, reduced ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!reduced && visible) raf = global.requestAnimationFrame(frame);
    }
    function run() {
      if (reduced) { resize(); gl.uniform2f(U.u_res, canvas.width, canvas.height);
        gl.uniform1f(U.u_time, 1.7); gl.uniform1f(U.u_theme, themeValue()); gl.uniform1f(U.u_state, status); gl.uniform1f(U.u_reduced, 1);
        gl.drawArrays(gl.TRIANGLES, 0, 3); return; }
      if (raf == null && visible) raf = global.requestAnimationFrame(frame);
    }
    function stop() { if (raf != null) { global.cancelAnimationFrame(raf); raf = null; } }

    if ('ResizeObserver' in global) new ResizeObserver(resize).observe(canvas);
    if ('IntersectionObserver' in global) new IntersectionObserver(es => {
      visible = es[0].isIntersecting; visible ? run() : stop();
    }).observe(canvas);

    const api = {
      canvas,
      // idle 0 · processing 1 · done 2 · error 3
      setStatus(s) {
        status = ({ idle: 0, processing: 1, thinking: 1, running: 1, done: 2, ok: 2, complete: 2, error: 3, fail: 3 }[s] ?? 0);
        canvas.dataset.status = s; if (reduced) run();
      },
      start: run, stop
    };
    const init = (canvas.dataset.status || 'idle');
    api.setStatus(init);
    run();
    return api;
  }

  const instances = [];
  function mount(canvas) {
    if (!canvas || canvas.dataset.lumOrbMounted) return instances.find(i => i.canvas === canvas) || null;
    canvas.dataset.lumOrbMounted = '1';
    const orb = createOrb(canvas);
    if (orb) instances.push(orb);
    return orb;
  }
  function mountAll(root) {
    (root || document).querySelectorAll('canvas.lum-orb').forEach(mount);
  }
  function setStatus(s) { instances.forEach(o => o.setStatus(s)); }

  global.LumOrb = { mount, mountAll, setStatus, _instances: instances };
})(window);
