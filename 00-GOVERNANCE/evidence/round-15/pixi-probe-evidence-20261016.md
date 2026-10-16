# PixiJS 8.22.0 isolated probe: source and historical observations

Research documentation only. This preserves the complete source and observation receipt of the previously run small IAB probe; publication does not rerun it or establish product, native, performance or reference-calibration acceptance. The screenshot was not persisted.

The rules-only publication gate permits documentation, not executable/JSON evidence paths. Both complete originals are therefore documented below as fenced source, without changing the validator or adding a product route/dependency. Extract each fenced body as UTF-8/LF with one final newline, using its original basename; verify the SHA-256 below. The HTML only imports the fixed public PixiJS module. Running it is a separate explicit local operation, served on 127.0.0.1, outside product navigation.

<a id="probe-source"></a>

## pixi-8.22.0-probe.html

Extracted-body SHA-256: `7b7368f93cb2cc3df2539d26fb22172cd394d4c08bb87a0e5e63d5b94897ace8`. Original mixed-line-ending digest remains in plan section20.2. HTML line endings and excess final empty lines alone were normalized; JavaScript and observed values were unchanged.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PixiJS 8.22.0 isolated render probe</title>
  <style>
    :root { color-scheme: light; font: 16px/1.5 system-ui, sans-serif; }
    body { max-width: 760px; margin: 2rem auto; padding: 0 1rem; color: #15202b; background: #f5f7fa; }
    main { background: white; border: 1px solid #d7dfe8; border-radius: 12px; padding: 1.25rem; }
    #canvas-host { min-height: 180px; display: grid; place-items: center; background: #eef3f8; border-radius: 8px; }
    #status { white-space: pre-wrap; background: #111827; color: #e5e7eb; padding: .75rem; border-radius: 8px; }
    .note { color: #485564; }
    button { padding: .5rem .75rem; }
  </style>
</head>
<body>
  <main>
    <h1>Isolated PixiJS 8.22.0 render probe</h1>
    <p class="note">Static technical probe only. It is not LUMENIS UI or a design direction.</p>
    <section id="scene" aria-label="Canvas render test">
      <div id="canvas-host" aria-hidden="true"></div>
      <p id="semantic-equivalent">Accessible equivalent: a blue rectangle with an orange circle overlapping its right edge. No interaction or business meaning is encoded in the canvas.</p>
    </section>
    <button id="destroy" type="button" disabled>Destroy renderer</button>
    <h2>Probe log</h2>
    <pre id="status" role="status" aria-live="polite">Starting import…</pre>
  </main>
  <script type="module">
    const statusNode = document.querySelector('#status');
    const host = document.querySelector('#canvas-host');
    const destroyButton = document.querySelector('#destroy');
    let app;

    const log = (message) => {
      statusNode.textContent += '\n' + message;
    };

    try {
      const { Application, Graphics } = await import('https://cdn.jsdelivr.net/npm/pixi.js@8.22.0/dist/pixi.min.mjs');
      log('Imported pixi.js 8.22.0.');
      app = new Application();
      log('Created Application; awaiting app.init().');
      await app.init({ width: 640, height: 240, autoStart: false, backgroundAlpha: 0, autoDensity: true, resolution: window.devicePixelRatio });
      app.canvas.setAttribute('aria-hidden', 'true');
      app.canvas.dataset.probeCanvas = 'true';
      host.appendChild(app.canvas);
      log('Initialized renderer: ' + app.renderer.constructor.name + '.');
      log('Canvas size: ' + app.canvas.width + 'x' + app.canvas.height + ' backing pixels; client size: ' + app.canvas.clientWidth + 'x' + app.canvas.clientHeight + '.');
      log('Backend flags: gl=' + Boolean(app.renderer.gl) + ', gpu=' + Boolean(app.renderer.gpu) + ', device=' + Boolean(app.renderer.device) + '.');
      log('DPR=' + window.devicePixelRatio + '; canvas resolution=' + (app.canvas.width / app.canvas.clientWidth) + 'x scale ratio.');

      const graphic = new Graphics()
        .rect(64, 48, 280, 144)
        .fill({ color: 0x2463eb })
        .circle(344, 120, 64)
        .fill({ color: 0xf28c28 });
      app.stage.addChild(graphic);
      app.renderer.render(app.stage);
      log('Added one Graphics object (rect + circle); called renderer.render(stage).');
      log('RESULT=RENDERED');
      destroyButton.disabled = false;
      destroyButton.addEventListener('click', () => {
        app.destroy({ removeView: true }, { children: true });
        app = undefined;
        log('Called app.destroy({ removeView: true }, { children: true });');
        log('Canvas remaining in host: ' + host.querySelectorAll('canvas').length + '.');
        log('Accessible equivalent remains: ' + Boolean(document.querySelector('#semantic-equivalent')) + '.');
        log('RESULT=DESTROYED');
        destroyButton.disabled = true;
      }, { once: true });
    } catch (error) {
      log('RESULT=NOT_RUN');
      log('ERROR=' + (error?.stack || error?.message || String(error)));
    }
  </script>
</body>
</html>
```

<a id="observation-receipt"></a>

## pixi-probe-result-20261016.json

Extracted-body SHA-256: `91354c52287d3ea3b22f40c02b37329e32ac16eb4580cc1c206f7ea2a14596bc`. Original mixed-line-ending digest remains in plan section20.2. HTML line endings and excess final empty lines alone were normalized; JavaScript and observed values were unchanged.

```json
{
  "probe": "pixi.js isolated static render probe",
  "library": "pixi.js",
  "version": "8.22.0",
  "source": "https://github.com/pixijs/pixijs/tree/v8.22.0",
  "page": "pixi-8.22.0-probe.html",
  "origin": "http://127.0.0.1:8765/pixi-8.22.0-probe.html",
  "run_date": "2026-10-16",
  "isolated_from_product_source": true,
  "init_options": {
    "width": 640,
    "height": 240,
    "autoStart": false,
    "backgroundAlpha": 0,
    "autoDensity": true,
    "resolution": 1.25
  },
  "observed_runtime": {
    "browser_surface": "Codex in-app browser, new isolated tab",
    "device_pixel_ratio": 1.25,
    "renderer_constructor_name": "H0 (minified; not used as backend proof)",
    "renderer_gl_present": true,
    "renderer_gpu_present": false,
    "renderer_device_present": false,
    "inferred_backend": "WebGL",
    "canvas_css_size_px": [640, 240],
    "canvas_backing_size_px": [800, 300],
    "canvas_to_css_scale_ratio": 1.25,
    "render_call": "app.renderer.render(app.stage)",
    "result": "RENDERED"
  },
  "scene": "One static Graphics object: blue rectangle and overlapping orange circle. The canvas is aria-hidden; an adjacent DOM paragraph describes the equivalent.",
  "dispose": {
    "call": "app.destroy({ removeView: true }, { children: true })",
    "canvas_count_after_destroy": 0,
    "semantic_dom_remained": true,
    "result": "DESTROYED"
  },
  "logs": [
    "Imported pixi.js 8.22.0.",
    "Created Application; awaiting app.init().",
    "Initialized renderer: H0.",
    "Canvas size: 800x300 backing pixels; client size: 640x240.",
    "Backend flags: gl=true, gpu=false, device=false.",
    "DPR=1.25; canvas resolution=1.25x scale ratio.",
    "Added one Graphics object (rect + circle); called renderer.render(stage).",
    "RESULT=RENDERED",
    "Called app.destroy({ removeView: true }, { children: true });",
    "Canvas remaining in host: 0.",
    "Accessible equivalent remains: true.",
    "RESULT=DESTROYED"
  ],
  "console_warn_or_error_entries": 0,
  "screenshot": "Captured in the isolated browser tool output; repeatable HTML probe retained locally, screenshot was not persisted as a file.",
  "limits": [
    "One browser, one small static scene, one render and one teardown only.",
    "No FPS/frame-time, startup latency, memory, GPU/battery, long-run, target-device or Flutter/Astro product benchmark.",
    "No LUMENIS source, app/, website/, production runtime, database, credentials, accounts, paid resources or external messages were used.",
    "The CDN import fetched public pixi.js v8.22.0 source; no user data was sent."
  ]
}
```
