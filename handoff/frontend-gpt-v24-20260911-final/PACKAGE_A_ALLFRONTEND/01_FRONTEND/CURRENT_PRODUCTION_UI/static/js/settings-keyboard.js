/**
 * settings-keyboard.js — 序境 LUMENIS 键盘快捷键管理
 * 对接 keyboard-shortcuts.js 现有机制（Ctrl+/等），设置页化
 * 持久化到 localStorage
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'lumenis-keyboard-shortcuts-v1';

  // 默认快捷键定义（与 keyboard-shortcuts.js 保持一致）
  var DEFAULT_SHORTCUTS = [
    // 全局操作
    { id: 'search', name: '搜索', desc: '聚焦全局搜索框', combo: 'Ctrl+K', category: '全局操作', editable: true },
    { id: 'refresh', name: '刷新当前页', desc: '重新加载当前页面', combo: 'Ctrl+Shift+R', category: '全局操作', editable: true },
    { id: 'ai-assistant', name: 'AI 助手', desc: '唤起/关闭 AI 助手面板', combo: 'Ctrl+J', category: '全局操作', editable: true },
    { id: 'theme-toggle', name: '切换主题', desc: '浅色/深色主题切换', combo: 'Ctrl+T', category: '全局操作', editable: true },
    // 域切换
    { id: 'domain-zbmp', name: '切换序境·品牌市场域', desc: '切换到 ZBMP 序境·品牌市场域', combo: 'Ctrl+1', category: '域切换', editable: true },
    { id: 'domain-cth', name: '切换序境·商业运营域', desc: '切换到 序境·商业运营域', combo: 'Ctrl+2', category: '域切换', editable: true },
    { id: 'domain-system', name: '切换系统域', desc: '切换到 SYSTEM 运行控制域', combo: 'Ctrl+3', category: '域切换', editable: true },
    // 视图与窗口
    { id: 'shortcuts-help', name: '显示快捷键', desc: '打开快捷键帮助面板', combo: 'Ctrl+/', category: '视图与窗口', editable: false },
    { id: 'close-modal', name: '关闭弹窗', desc: '关闭当前打开的弹窗/面板', combo: 'Esc', category: '视图与窗口', editable: false },
    { id: 'back', name: '返回上一页', desc: '浏览器历史后退', combo: 'Alt+Left', category: '视图与窗口', editable: true },
    // 导航（Alt+数字，动态生成）
    { id: 'nav-1', name: '导航项 1', desc: '跳转到当前域第1个导航项', combo: 'Alt+1', category: '导航', editable: true },
    { id: 'nav-2', name: '导航项 2', desc: '跳转到当前域第2个导航项', combo: 'Alt+2', category: '导航', editable: true },
    { id: 'nav-3', name: '导航项 3', desc: '跳转到当前域第3个导航项', combo: 'Alt+3', category: '导航', editable: true },
    { id: 'nav-4', name: '导航项 4', desc: '跳转到当前域第4个导航项', combo: 'Alt+4', category: '导航', editable: true },
    { id: 'nav-5', name: '导航项 5', desc: '跳转到当前域第5个导航项', combo: 'Alt+5', category: '导航', editable: true },
  ];

  function loadShortcuts() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        var custom = JSON.parse(saved);
        // Merge with defaults (custom overrides combo)
        return DEFAULT_SHORTCUTS.map(function (d) {
          var c = custom.find(function (x) { return x.id === d.id; });
          return c ? Object.assign({}, d, { combo: c.combo }) : d;
        });
      }
    } catch (e) { /* fallback to defaults */ }
    return DEFAULT_SHORTCUTS.map(function (d) { return Object.assign({}, d); });
  }

  function saveShortcuts(shortcuts) {
    try {
      var custom = shortcuts.filter(function (s) {
        var def = DEFAULT_SHORTCUTS.find(function (d) { return d.id === s.id; });
        return def && def.combo !== s.combo;
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(custom.map(function (s) {
        return { id: s.id, combo: s.combo };
      })));
      return true;
    } catch (e) { return false; }
  }

  function resetToDefaults() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
    return DEFAULT_SHORTCUTS.map(function (d) { return Object.assign({}, d); });
  }

  // Capture a key combo for editing
  function captureCombo(callback) {
    var handler = function (e) {
      e.preventDefault();
      e.stopPropagation();
      var parts = [];
      if (e.ctrlKey) parts.push('Ctrl');
      if (e.altKey) parts.push('Alt');
      if (e.shiftKey) parts.push('Shift');
      if (e.metaKey) parts.push('Meta');
      var key = e.key;
      if (key === ' ') key = 'Space';
      else if (key.length === 1) key = key.toUpperCase();
      else if (key === 'Escape') {
        // Cancel capture
        document.removeEventListener('keydown', handler, true);
        callback(null);
        return;
      }
      if (!['Control', 'Alt', 'Shift', 'Meta'].includes(key)) {
        parts.push(key);
        document.removeEventListener('keydown', handler, true);
        callback(parts.join('+'));
      }
    };
    document.addEventListener('keydown', handler, true);
  }

  // Check for conflicts
  function findConflict(shortcuts, id, combo) {
    return shortcuts.find(function (s) {
      return s.id !== id && s.combo === combo && combo;
    });
  }

  window.SettingsKeyboard = {
    load: loadShortcuts,
    save: saveShortcuts,
    reset: resetToDefaults,
    capture: captureCombo,
    findConflict: findConflict,
    DEFAULT: DEFAULT_SHORTCUTS
  };

  console.log('[settings-keyboard] 键盘快捷键管理已加载');
})();

