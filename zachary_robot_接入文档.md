# Zachary 机器人组件 · 完整接入文档

> CTH-POMS 系统 · 3D交互式机器人助手
> 版本：v1.0 精致版
> 更新日期：2026-08-29

---

## 一、文件清单

| 文件名 | 位置 | 说明 |
|--------|------|------|
| `zachary_robot_widget.html` | 系统根目录 | 独立测试页，双击打开预览效果 |
| `robot_open.png` | `static/img/` | 睁眼表情（0 0 眼 + 微笑），900x900 透明底 |
| `robot_close.png` | `static/img/` | 闭眼微笑表情，900x900 透明底 |

---

## 二、功能特性

- ✅ **造型还原**：黑色球形身体 + 紫色发光猫耳 + 青色光环耳机，100%还原设计稿
- ✅ **底部完整**：完整球形身体，无裁切
- ✅ **表情切换**：睁眼 ↔ 闭眼微笑，淡入淡出过渡，每3.2秒自动切换
- ✅ **呼吸光晕**：机器人背后紫青渐变光晕，随呼吸脉动缩放
- ✅ **玻璃拟态底座**：底部椭圆能量光晕，悬浮感
- ✅ **旋转光环**：外圈细光环 + 青色光点缓慢旋转
- ✅ **星星粒子**：42颗紫色/青色星星环绕，分大小两层，大星星带十字星芒
- ✅ **悬浮动画**：正弦曲线上下浮动 + 轻微缩放，NOMI呼吸感
- ✅ **拖拽交互**：鼠标/触屏拖动，边界限制不会拖出容器
- ✅ **点击跳转**：区分拖拽和点击，点击机器人跳转指定页面
- ✅ **透明背景**：画布透明，直接透出页面原有背景
- ✅ **防CSS污染**：所有样式JS动态生成，不受全局CSS影响
- ✅ **延迟渲染兼容**：轮询等待DOM节点，解决Jinja模板延迟渲染问题
- ✅ **双端兼容**：PC鼠标 / 手机触屏均可

---

## 三、接入步骤

### 第一步：确认图片已就位

检查以下两个文件存在：
```
static/img/robot_open.png
static/img/robot_close.png
```

### 第二步：页面添加挂载节点

在你要显示机器人的页面模板（如 `templates/overview.html`）任意位置添加：
```html
<div id="robotMount"></div>
```

### 第三步：嵌入组件JS

在页面底部（`</body>` 前）复制以下代码：

```html
<script>
const ZacharyRobot = (function() {
  const CONFIG = {
    mountId: "robotMount",
    imgOpen:  "/static/img/robot_open.png",
    imgClose: "/static/img/robot_close.png",
    onClickJumpUrl: "/overview",       // ← 改成你的跳转路由
    robotSize: 220,                     // 机器人显示尺寸(px)
    containerW: 340,                    // 容器宽(px)
    containerH: 380,                    // 容器高(px)
    expressionInterval: 3200,           // 表情切换间隔(ms)
    starCount: 42,                      // 星星数量
    dragBoundaryX: 100,                 // 拖拽X边界(px)
    dragBoundaryY: 110,                 // 拖拽Y边界(px)
    glowPurple: "184,107,255",          // 紫色光晕RGB
    glowCyan: "100,220,255"             // 青色光晕RGB
  };

  let mountEl, wrapEl, robotEl, imgEl, glowEl, baseEl, ringEl, starCanvas, starCtx;
  let stars = [], currentExpression = "open";
  let drag = { active:false, ox:0, oy:0, rx:0, ry:0, moved:false };
  let time = 0, animationId = null, expressionTimer = null;
  let imgOpacity = 1, targetImgOpacity = 1;

  function waitMount(cb) {
    const el = document.getElementById(CONFIG.mountId);
    if (!el) { setTimeout(() => waitMount(cb), 100); return; }
    mountEl = el; cb();
  }

  function buildDom() {
    wrapEl = document.createElement("div");
    wrapEl.style.cssText = `width:${CONFIG.containerW}px;height:${CONFIG.containerH}px;position:relative;margin:0 auto;overflow:hidden;touch-action:none;user-select:none;-webkit-user-select:none;`;

    starCanvas = document.createElement("canvas");
    starCanvas.style.cssText = "position:absolute;inset:0;pointer-events:none;z-index:1;";
    starCanvas.width = CONFIG.containerW; starCanvas.height = CONFIG.containerH;
    starCtx = starCanvas.getContext("2d");

    glowEl = document.createElement("div");
    glowEl.style.cssText = `position:absolute;left:50%;top:44%;width:${CONFIG.robotSize*1.6}px;height:${CONFIG.robotSize*1.6}px;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(${CONFIG.glowPurple},0.25) 0%,rgba(${CONFIG.glowCyan},0.08) 40%,transparent 70%);filter:blur(20px);pointer-events:none;z-index:2;`;

    baseEl = document.createElement("div");
    baseEl.style.cssText = `position:absolute;left:50%;bottom:25px;width:${CONFIG.robotSize*0.9}px;height:18px;transform:translateX(-50%);border-radius:50%;background:radial-gradient(ellipse,rgba(${CONFIG.glowPurple},0.3) 0%,rgba(${CONFIG.glowCyan},0.1) 50%,transparent 70%);filter:blur(6px);pointer-events:none;z-index:2;`;

    ringEl = document.createElement("div");
    ringEl.style.cssText = `position:absolute;left:50%;top:46%;width:${CONFIG.robotSize*1.35}px;height:${CONFIG.robotSize*1.35}px;transform:translate(-50%,-50%);border-radius:50%;border:1px solid rgba(${CONFIG.glowPurple},0.15);pointer-events:none;z-index:2;`;
    const dot = document.createElement("div");
    dot.style.cssText = `position:absolute;top:-2px;left:50%;width:4px;height:4px;border-radius:50%;background:rgba(${CONFIG.glowCyan},0.8);box-shadow:0 0 8px rgba(${CONFIG.glowCyan},0.8);transform:translateX(-50%);`;
    ringEl.appendChild(dot);

    robotEl = document.createElement("div");
    robotEl.style.cssText = `width:${CONFIG.robotSize}px;height:${CONFIG.robotSize}px;position:absolute;left:50%;top:44%;transform:translate(-50%,-50%);cursor:grab;z-index:3;transition:transform 0.15s ease-out;`;

    imgEl = document.createElement("img");
    imgEl.src = CONFIG.imgOpen;
    imgEl.style.cssText = `width:100%;height:100%;object-fit:contain;display:block;pointer-events:none;-webkit-user-drag:none;filter:drop-shadow(0 4px 20px rgba(${CONFIG.glowPurple},0.3)) drop-shadow(0 0 30px rgba(${CONFIG.glowCyan},0.15));transition:opacity 0.4s ease;`;

    [CONFIG.imgOpen, CONFIG.imgClose].forEach(s => { const i=new Image(); i.src=s; });

    robotEl.appendChild(imgEl);
    wrapEl.append(starCanvas, glowEl, baseEl, ringEl, robotEl);
    mountEl.appendChild(wrapEl);

    initStars(); bindEvents(); startExpression(); animate();
    console.log("%c[ZacharyRobot] 组件加载完成 ✨", "color:#b86bff;font-weight:bold;");
  }

  function initStars() {
    stars = [];
    for (let i = 0; i < CONFIG.starCount; i++) {
      const layer = Math.random();
      stars.push({ baseAngle:Math.random()*Math.PI*2, radius:75+Math.random()*85, speed:0.002+Math.random()*0.005, size:layer>0.7?2+Math.random()*1.5:0.8+Math.random()*1.2, phase:Math.random()*Math.PI*2, twinkleSpeed:0.02+Math.random()*0.035, yOffset:(Math.random()-0.5)*70, layer });
    }
  }

  function startExpression() {
    expressionTimer = setInterval(() => {
      targetImgOpacity = 0;
      setTimeout(() => {
        currentExpression = currentExpression==="open"?"close":"open";
        imgEl.src = currentExpression==="open"?CONFIG.imgOpen:CONFIG.imgClose;
        targetImgOpacity = 1;
      }, 350);
    }, CONFIG.expressionInterval);
  }

  function bindEvents() {
    robotEl.addEventListener("pointerdown", e => { drag.active=true;drag.moved=false;drag.ox=e.clientX;drag.oy=e.clientY;robotEl.style.cursor="grabbing";e.preventDefault(); });
    window.addEventListener("pointermove", e => {
      if (!drag.active) return;
      const dx=e.clientX-drag.ox, dy=e.clientY-drag.oy;
      if (Math.abs(dx)>3||Math.abs(dy)>3) drag.moved=true;
      drag.rx+=dx; drag.ry+=dy; drag.ox=e.clientX; drag.oy=e.clientY;
      drag.rx=Math.max(-CONFIG.dragBoundaryX,Math.min(CONFIG.dragBoundaryX,drag.rx));
      drag.ry=Math.max(-CONFIG.dragBoundaryY,Math.min(CONFIG.dragBoundaryY,drag.ry));
    });
    window.addEventListener("pointerup", () => {
      if (drag.active && !drag.moved && CONFIG.onClickJumpUrl) window.location.href = CONFIG.onClickJumpUrl;
      drag.active=false; robotEl.style.cursor="grab";
    });
  }

  function animate() {
    time += 0.016;
    const fy=Math.sin(time*1.2)*5, fx=Math.sin(time*0.8)*1.5, sc=1+Math.sin(time*1.5)*0.008;
    robotEl.style.transform = `translate(calc(-50% + ${drag.rx+fx}px),calc(-50% + ${drag.ry+fy}px)) scale(${sc})`;
    imgOpacity += (targetImgOpacity-imgOpacity)*0.1;
    imgEl.style.opacity = imgOpacity;
    glowEl.style.transform = `translate(-50%,-50%) scale(${1+Math.sin(time*1.8)*0.06})`;
    glowEl.style.opacity = 0.7+Math.sin(time*1.8)*0.3;
    baseEl.style.opacity = 0.6+Math.sin(time*1.8+0.5)*0.4;
    ringEl.style.transform = `translate(-50%,-50%) rotate(${time*20}deg)`;
    ringEl.style.opacity = 0.5+Math.sin(time*1.5)*0.3;

    starCtx.clearRect(0,0,CONFIG.containerW,CONFIG.containerH);
    const cx=CONFIG.containerW/2, cy=CONFIG.containerH*0.44;
    for (let s of stars) {
      s.baseAngle+=s.speed; s.phase+=s.twinkleSpeed;
      const x=cx+Math.cos(s.baseAngle)*s.radius, y=cy+Math.sin(s.baseAngle)*s.radius*0.55+s.yOffset;
      const alpha=0.2+0.8*(0.5+0.5*Math.sin(s.phase)), size=s.size*(0.6+0.4*Math.sin(s.phase));
      if (s.layer>0.6) {
        starCtx.beginPath(); starCtx.arc(x,y,size*3,0,Math.PI*2);
        const g=starCtx.createRadialGradient(x,y,0,x,y,size*3);
        g.addColorStop(0,`rgba(${CONFIG.glowPurple},${alpha*0.3})`); g.addColorStop(1,"transparent");
        starCtx.fillStyle=g; starCtx.fill();
      }
      starCtx.beginPath(); starCtx.arc(x,y,size,0,Math.PI*2);
      starCtx.fillStyle = s.layer>0.7?`rgba(${CONFIG.glowCyan},${alpha})`:`rgba(210,170,255,${alpha})`;
      starCtx.fill();
      if (s.layer>0.75 && alpha>0.5) {
        starCtx.strokeStyle=`rgba(255,255,255,${alpha*0.4})`; starCtx.lineWidth=0.5;
        starCtx.beginPath(); starCtx.moveTo(x-size*2.5,y); starCtx.lineTo(x+size*2.5,y);
        starCtx.moveTo(x,y-size*2.5); starCtx.lineTo(x,y+size*2.5); starCtx.stroke();
      }
    }
    animationId = requestAnimationFrame(animate);
  }

  return {
    init: () => waitMount(buildDom),
    destroy: () => { clearInterval(expressionTimer); cancelAnimationFrame(animationId); if(wrapEl) wrapEl.remove(); }
  };
})();

if (document.readyState==="loading") document.addEventListener("DOMContentLoaded",()=>ZacharyRobot.init());
else ZacharyRobot.init();
</script>
```

---

## 四、配置说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mountId` | string | `"robotMount"` | 挂载节点ID |
| `imgOpen` | string | `/static/img/robot_open.png` | 睁眼表情图片路径 |
| `imgClose` | string | `/static/img/robot_close.png` | 闭眼表情图片路径 |
| `onClickJumpUrl` | string | `"/overview"` | 点击机器人跳转的路由 |
| `robotSize` | number | `220` | 机器人显示尺寸(px)，手机端建议180 |
| `containerW` | number | `340` | 容器宽度，决定拖拽活动范围 |
| `containerH` | number | `380` | 容器高度 |
| `expressionInterval` | number | `3200` | 表情自动切换间隔(ms) |
| `starCount` | number | `42` | 星星粒子数量 |
| `dragBoundaryX` | number | `100` | 横向拖拽边界(px) |
| `dragBoundaryY` | number | `110` | 纵向拖拽边界(px) |
| `glowPurple` | string | `"184,107,255"` | 紫色光晕RGB值 |
| `glowCyan` | string | `"100,220,255"` | 青色光晕RGB值 |

---

## 五、验证方法

1. **独立测试**：双击系统根目录的 `zachary_robot_widget.html`，确认机器人效果正常
2. **系统嵌入测试**：启动系统后访问对应页面，F12打开控制台
3. **成功标志**：控制台输出 `[ZacharyRobot] 组件加载完成 ✨`
4. **功能检查**：
   - 机器人显示完整，底部无裁切
   - 每3秒左右表情自动切换（睁眼↔闭眼）
   - 鼠标拖动机器人，不会拖出容器
   - 点击机器人（不拖动）跳转到配置的页面
   - 周围有紫色星星缓慢环绕闪烁

---

## 六、常见问题排查

### Q1：机器人不显示
- 检查F12控制台是否有报错
- 确认挂载节点 `<div id="robotMount"></div>` 存在
- 确认图片路径正确，可直接访问 `/static/img/robot_open.png`
- 确认容器父元素不是 `display:none`（隐藏请用 `visibility:hidden`）

### Q2：机器人底部被裁切
- 确认使用的是最新的 `robot_open.png` / `robot_close.png`（900x900版本）
- 检查父容器是否有 `overflow:hidden` 且高度不足

### Q3：拖拽不生效
- 确认没有其他元素覆盖在机器人上方（检查z-index）
- 手机端确认父容器没有 `touch-action: none` 冲突

### Q4：点击不跳转
- 检查 `CONFIG.onClickJumpUrl` 路由是否正确
- 确认点击时没有拖动（移动超过3px会被判定为拖拽）

### Q5：全局CSS污染样式
- 本组件所有样式通过JS动态生成，理论上不受全局CSS影响
- 如仍有问题，检查是否有 `* { all: unset }` 之类的全局重置

### Q6：页面切换后机器人还在运行
- 调用 `ZacharyRobot.destroy()` 可销毁组件，清理定时器和动画

---

## 七、技术参数

- **依赖**：无外部依赖，纯原生JS + Canvas + CSS
- **兼容性**：Chrome / Edge / Safari / 移动端浏览器
- **性能**：单canvas动画，requestAnimationFrame驱动，移动端无压力
- **内存**：页面切换时调用destroy()可完全释放

---

## 八、文件位置汇总

```
D:\Taikoo-monitor-new\
├── zachary_robot_widget.html          # 独立测试页
├── zachary_robot_接入文档.md           # 本文档
└── static\
    └── img\
        ├── robot_open.png             # 睁眼表情（278KB）
        └── robot_close.png            # 闭眼表情（387KB）
```

---

*文档结束 · 有问题随时反馈*
