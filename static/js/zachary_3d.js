/* ============================================================
 * Zachary 3D 机器人形象（Three.js）
 * 设计：透明画布无背景 · 荧光白主体 · 荧光竹绿自发光 · 紫色星星粒子
 *       4 套表情自动切换 · 缓慢自转
 * 交互：本模块只负责“渲染”，不拦截指针事件；
 *       拖拽（含视口边界）与点击开聊天仍由 zachary_robot_enhanced.js 负责，
 *       从而避免 3D DragControls 与 DOM 拖拽冲突，保证稳定不崩。
 * 容错：CDN 未加载到 THREE 时自动回退到原 CSS 形象，绝不阻断系统。
 * ============================================================ */
(function () {
    'use strict';

    var R3D = {
        robotColor: 0xf8fff8,   // 荧光白主体
        glowGreen: 0x5fd8ff,    // 荧光浅蓝（辉光/耳朵/屏幕表情统一）
        starPurple: 0xb86bff,   // 紫色星星
        inited: false,
        animId: null
    };
    window.Zachary3D = R3D;

    var expressions = [
        { eyes: [[-0.30, 0.15], [0.30, 0.15]], mouth: [0, -0.12] },
        { eyes: [[-0.30, 0.18], [0.30, 0.18]], mouth: [0, -0.16] },
        { eyes: [[-0.28, 0.12], [0.32, 0.12]], mouth: [0, -0.08] },
        { eyes: [[-0.32, 0.16], [0.28, 0.16]], mouth: [0, -0.14] }
    ];

    function build() {
        if (R3D.inited) return;
        // THREE 未就绪（CDN 失败）：保留 CSS 形象，安全回退
        if (typeof THREE === 'undefined') { console.warn('[Zachary3D] THREE 未加载，保留CSS形象'); return; }

        var robot = document.querySelector('.zachary-robot');
        if (!robot) return;
        if (robot.querySelector('#zachary3dWrap')) { R3D.inited = true; return; }

        // 尺寸：优先 .zachary-robot，其次外层浮动容器
        var sizeW = robot.clientWidth || robot.offsetWidth || (robot.parentElement && robot.parentElement.offsetWidth) || 76;
        var sizeH = robot.clientHeight || robot.offsetHeight || (robot.parentElement && robot.parentElement.offsetHeight) || 76;
        if (sizeW < 20) sizeW = 76;
        if (sizeH < 20) sizeH = 76;

        // 透明画布层，不拦截指针
        var wrap = document.createElement('div');
        wrap.id = 'zachary3dWrap';
        wrap.style.cssText = 'position:absolute;inset:0;z-index:3;pointer-events:none;';
        var canvas = document.createElement('canvas');
        canvas.id = 'zachary3dCanvas';
        canvas.style.cssText = 'width:100%;height:100%;display:block;';
        wrap.appendChild(canvas);
        robot.appendChild(wrap);

        // 隐藏 CSS 黑色球体脸（保留耳朵/帽子/耳麦/光环等荧光装饰）
        var cssBody = robot.querySelector('.zachary-body');
        if (cssBody) cssBody.style.visibility = 'hidden';

        var scene = new THREE.Scene();
        var camera = new THREE.PerspectiveCamera(45, sizeW / sizeH, 0.1, 1000);
        camera.position.z = 4.0;

        var renderer;
        try {
            renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        } catch (e) {
            // 浏览器不支持 WebGL，回退
            wrap.remove();
            if (cssBody) cssBody.style.visibility = '';
            console.warn('[Zachary3D] WebGL 不可用，保留CSS形象');
            return;
        }
        renderer.setClearColor(0x000000, 0); // 透明背景
        renderer.setSize(sizeW, sizeH, false);
        try { renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); } catch (e) {}

        // 灯光
        scene.add(new THREE.AmbientLight(0xffffff, 0.55));
        var pGreen = new THREE.PointLight(R3D.glowGreen, 1.25, 8); pGreen.position.set(0, 1.2, 2); scene.add(pGreen);
        var pPurple = new THREE.PointLight(R3D.starPurple, 0.7, 6); pPurple.position.set(-1.5, 0.5, 1); scene.add(pPurple);

        var group = new THREE.Group();
        scene.add(group);

        // 头部球体（荧光白 + 浅蓝微弱自发光）
        var head = new THREE.Mesh(
            new THREE.SphereGeometry(1, 48, 48),
            new THREE.MeshStandardMaterial({
                color: R3D.robotColor,
                emissive: R3D.glowGreen,
                emissiveIntensity: 0.30,
                metalness: 0.2,
                roughness: 0.18
            })
        );
        group.add(head);

        // Nomi 风格液晶面部屏：横椭圆（非正圆、带横切面感），深色微内凹
        var screen = new THREE.Mesh(
            new THREE.CircleGeometry(0.66, 56),
            new THREE.MeshBasicMaterial({ color: 0x06121e })
        );
        screen.position.set(0, -0.02, 0.93);
        screen.scale.set(1.12, 0.86, 1);
        group.add(screen);

        // 面部：2 眼 1 嘴（荧光浅蓝发光点，落在液晶屏上）
        var eyeGeo = new THREE.SphereGeometry(0.072, 20, 20);
        var mouthGeo = new THREE.SphereGeometry(0.055, 20, 20);
        var faceMat = new THREE.MeshBasicMaterial({ color: 0xc6f2ff });
        var eyeL = new THREE.Mesh(eyeGeo, faceMat);
        var eyeR = new THREE.Mesh(eyeGeo, faceMat);
        var mouth = new THREE.Mesh(mouthGeo, faceMat);
        group.add(eyeL); group.add(eyeR); group.add(mouth);
        var expIndex = 0;
        function applyExpression(i) {
            var e = expressions[i];
            eyeL.position.set(e.eyes[0][0], e.eyes[0][1] - 0.02, 0.98);
            eyeR.position.set(e.eyes[1][0], e.eyes[1][1] - 0.02, 0.98);
            mouth.position.set(e.mouth[0], e.mouth[1] - 0.02, 0.98);
        }
        applyExpression(0);
        setInterval(function () {
            expIndex = (expIndex + 1) % expressions.length;
            applyExpression(expIndex);
        }, 3000);

        // 紫色星星粒子环绕
        var count = 42;
        var geo = new THREE.BufferGeometry();
        var pos = new Float32Array(count * 3);
        for (var i = 0; i < count; i++) {
            var theta = Math.random() * Math.PI * 2;
            var r = 1.7 + Math.random() * 0.7;
            pos[i * 3] = Math.cos(theta) * r;
            pos[i * 3 + 1] = (Math.random() - 0.5) * 1.6;
            pos[i * 3 + 2] = Math.sin(theta) * r;
        }
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        var stars = new THREE.Points(geo, new THREE.PointsMaterial({
            color: R3D.starPurple, size: 0.085, transparent: true, opacity: 0.85,
            blending: THREE.AdditiveBlending, depthWrite: false
        }));
        group.add(stars);

        // 对外：可被现有表情系统联动
        R3D.setExpression = applyExpression;

        function resize() {
            var w = robot.clientWidth || sizeW, h = robot.clientHeight || sizeH;
            if (w < 20) w = sizeW; if (h < 20) h = sizeH;
            camera.aspect = w / h; camera.updateProjectionMatrix();
            renderer.setSize(w, h, false);
        }
        window.addEventListener('resize', resize);

        function animate() {
            R3D.animId = requestAnimationFrame(animate);
            group.rotation.y += 0.004;
            stars.rotation.y += 0.008;
            stars.rotation.x += 0.002;
            renderer.render(scene, camera);
        }
        animate();
        R3D.inited = true;
        R3D.destroy = function () {
            if (R3D.animId) cancelAnimationFrame(R3D.animId);
            wrap.remove(); R3D.inited = false;
            if (cssBody) cssBody.style.visibility = '';
        };
        console.log('[Zachary3D] 3D 形象已挂载');
    }

    function boot() { build(); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
    // 兜底：增强脚本异步复用/调整 DOM 后再确保一次
    setTimeout(boot, 600);
    setTimeout(boot, 1600);
})();
