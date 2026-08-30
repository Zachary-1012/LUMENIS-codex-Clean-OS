/* ============================================================
 * Zachary PNG 形象层 v5.8.2
 * 只负责“外观”：设计稿 robot_open/close.png 双表情定时淡入淡出。
 * 拖拽 / 点击开聊天 / 系统知识问答 仍由 zachary_robot_enhanced.js 负责，本脚本不拦截任何指针事件。
 * ============================================================ */
(function () {
  'use strict';
  var OPEN = '/static/img/robot_open.png?v=5.8.8';
  var CLOSE = '/static/img/robot_close.png?v=5.8.8';
  var INTERVAL = 3200;   // 表情切换间隔
  var FADE = 320;        // 淡入淡出时长(ms)
  var timer = null, current = 'open', img = null;

  // 预加载，避免切换瞬间闪白
  try { var p1 = new Image(); p1.src = OPEN; var p2 = new Image(); p2.src = CLOSE; } catch (e) {}

  function bind() {
    img = document.getElementById('zacharyPngFace');
    if (!img) { setTimeout(bind, 120); return; }
    // 暴露给聊天模块：说话时闭眼微笑、说完睁眼
    window.ZacharyPNG = {
      setExpression: function (name) {
        if (!img) return;
        current = (name === 'close' || name === 'speaking') ? 'close' : 'open';
        swap(current, true);
      },
      get current() { return current; }
    };
    timer = setInterval(function () {
      current = current === 'open' ? 'close' : 'open';
      swap(current, false);
    }, INTERVAL);
    console.log('%c[ZacharyRobot] PNG形象组件加载完成 ✨', 'color:#b86bff;font-weight:bold;');
  }

  function swap(which, instant) {
    if (!img) return;
    var target = which === 'close' ? CLOSE : OPEN;
    if (img.getAttribute('src') === target) return;
    img.style.opacity = '0';
    setTimeout(function () {
      img.src = target;
      img.style.opacity = '1';
    }, instant ? 0 : FADE);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
  window.addEventListener('beforeunload', function () { if (timer) clearInterval(timer); });
})();
