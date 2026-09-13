// ZBC Browser Panel — 右侧AI浏览器面板控制
// 三栏布局：拖拽延展 + 折叠/展开 + iframe嵌入
(function() {
  'use strict';

  const STORAGE_KEY = 'zbc_browser_panel_width';
  const DEFAULT_WIDTH = 420;
  const MIN_WIDTH = 280;
  const MAX_WIDTH = 800;

  const panel = document.getElementById('zbc-browser-panel');
  const resizer = document.getElementById('zbc-resizer');
  const iframe = document.getElementById('browser-panel-iframe');
  const placeholder = document.getElementById('browser-panel-placeholder');
  const launcher = document.getElementById('zbc-browser-launcher');

  let isDragging = false;
  let startX = 0;
  let startWidth = 0;

  // 恢复保存的宽度
  function restoreWidth() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && !isNaN(parseInt(saved))) {
      const w = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, parseInt(saved)));
      if (panel) panel.style.width = w + 'px';
    }
  }

  // 拖拽逻辑
  if (resizer) {
    resizer.addEventListener('mousedown', function(e) {
      isDragging = true;
      startX = e.clientX;
      startWidth = panel ? panel.offsetWidth : DEFAULT_WIDTH;
      document.body.classList.add('is-resizing');
      resizer.classList.add('is-dragging');
      e.preventDefault();
    });
  }

  document.addEventListener('mousemove', function(e) {
    if (!isDragging || !panel) return;
    const delta = startX - e.clientX; // 向右拖=缩小面板
    const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidth + delta));
    panel.style.width = newWidth + 'px';
  });

  document.addEventListener('mouseup', function() {
    if (isDragging) {
      isDragging = false;
      document.body.classList.remove('is-resizing');
      if (resizer) resizer.classList.remove('is-dragging');
      if (panel) localStorage.setItem(STORAGE_KEY, panel.offsetWidth);
    }
  });

  // 浏览器面板API
  window.BrowserPanel = {
    launch: function() {
      if (!iframe || !placeholder) return;
      placeholder.style.display = 'none';
      iframe.style.display = 'block';
      iframe.src = '/lumenis/system/browser';
      this._updateStatus(true);
    },
    reload: function() {
      if (iframe && iframe.src !== 'about:blank') {
        iframe.src = iframe.src;
      }
    },
    collapse: function() {
      if (panel) {
        panel.classList.add('is-collapsed');
        panel.style.width = '0';
      }
      if (resizer) resizer.style.display = 'none';
      if (launcher) launcher.style.display = 'block';
      localStorage.setItem('zbc_browser_panel_collapsed', '1');
    },
    expand: function() {
      if (panel) {
        panel.classList.remove('is-collapsed');
        restoreWidth();
      }
      if (resizer) resizer.style.display = '';
      if (launcher) launcher.style.display = 'none';
      localStorage.setItem('zbc_browser_panel_collapsed', '0');
    },
    toggle: function() {
      if (panel && panel.classList.contains('is-collapsed')) {
        this.expand();
      } else {
        this.collapse();
      }
    },
    toggleFullscreen: function() {
      if (!panel) return;
      if (panel.dataset.fullscreen === '1') {
        panel.style.width = '';
        panel.style.position = '';
        panel.style.zIndex = '';
        panel.dataset.fullscreen = '0';
        if (resizer) resizer.style.display = '';
      } else {
        panel.style.width = '80vw';
        panel.style.position = 'fixed';
        panel.style.right = '0';
        panel.style.top = '0';
        panel.style.bottom = '0';
        panel.style.zIndex = '9999';
        panel.dataset.fullscreen = '1';
        if (resizer) resizer.style.display = 'none';
      }
    },
    navigate: function(url) {
      if (iframe) {
        if (placeholder) placeholder.style.display = 'none';
        iframe.style.display = 'block';
        iframe.src = url;
      }
    },
    _updateStatus: function(active) {
      const dot = document.getElementById('browser-panel-dot');
      if (dot) {
        dot.className = 'status-dot ' + (active ? 'active' : '');
      }
    }
  };

  // 初始化：恢复折叠状态
  document.addEventListener('DOMContentLoaded', function() {
    restoreWidth();
    const collapsed = localStorage.getItem('zbc_browser_panel_collapsed') === '1';
    if (collapsed) {
      window.BrowserPanel.collapse();
    }
  });

  // 键盘快捷键：Ctrl+B 切换浏览器面板
  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault();
      window.BrowserPanel.toggle();
    }
  });

  console.log('[BrowserPanel] 三栏布局右侧浏览器面板已就绪 (Ctrl+B 切换)');
})();
