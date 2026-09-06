/**
 * settings-dropdown.js — 序境 LUMENIS 统一下拉浮层组件
 * 形态：白底圆角12px阴影，选项=主文字+灰色说明+选中✓
 * 用法：SettingsDropdown.init(triggerEl, { options, value, onChange })
 * options: [{ value, label, desc }]
 */
(function () {
  'use strict';

  var STYLE_ID = 'settings-dropdown-style';
  var activeDropdown = null;

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      '.sd-trigger{display:inline-flex;align-items:center;gap:8px;padding:7px 12px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;color:#0f172a;cursor:pointer;min-width:140px;justify-content:space-between;transition:border-color .15s,box-shadow .15s}',
      '.sd-trigger:hover{border-color:#0F766E}',
      '.sd-trigger.open{border-color:#0F766E;box-shadow:0 0 0 3px rgba(15,118,110,.12)}',
      '.sd-trigger .sd-label{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.sd-trigger .sd-chevron{width:14px;height:14px;color:#94a3b8;transition:transform .15s;flex-shrink:0}',
      '.sd-trigger.open .sd-chevron{transform:rotate(180deg)}',
      '.sd-overlay{position:fixed;inset:0;z-index:9998;display:none}',
      '.sd-overlay.show{display:block}',
      '.sd-menu{position:fixed;z-index:9999;background:#fff;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.16),0 2px 8px rgba(0,0,0,.08);padding:6px;min-width:200px;max-width:320px;max-height:320px;overflow-y:auto;display:none;animation:sd-in .15s ease}',
      '.sd-menu.show{display:block}',
      '@keyframes sd-in{from{opacity:0;transform:translateY(-4px) scale(.98)}to{opacity:1;transform:none}}',
      '.sd-option{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;cursor:pointer;transition:background .1s}',
      '.sd-option:hover{background:#f1f5f9}',
      '.sd-option.selected{background:#f0fdfa}',
      '.sd-option .sd-opt-text{flex:1;min-width:0}',
      '.sd-option .sd-opt-label{font-size:13px;color:#0f172a;font-weight:500}',
      '.sd-option .sd-opt-desc{font-size:11px;color:#94a3b8;margin-top:1px}',
      '.sd-option .sd-check{width:16px;height:16px;color:#0F766E;flex-shrink:0;display:none}',
      '.sd-option.selected .sd-check{display:block}',
      '.sd-divider{height:1px;background:#f1f5f9;margin:4px 8px}',
      '.sd-disabled{opacity:.4;pointer-events:none}'
    ].join('');
    var st = document.createElement('style');
    st.id = STYLE_ID;
    st.textContent = css;
    document.head.appendChild(st);
  }

  function chevronSvg() {
    return '<svg class="sd-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';
  }

  function checkSvg() {
    return '<svg class="sd-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
  }

  function closeActive() {
    if (activeDropdown) {
      activeDropdown.trigger.classList.remove('open');
      activeDropdown.menu.classList.remove('show');
      activeDropdown.overlay.classList.remove('show');
      activeDropdown = null;
    }
  }

  function openDropdown(trigger, menu, overlay) {
    closeActive();
    var rect = trigger.getBoundingClientRect();
    var menuWidth = Math.max(trigger.offsetWidth, 200);
    menu.style.width = menuWidth + 'px';
    menu.style.left = rect.left + 'px';
    // Position below or above based on space
    var spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow < 200 && rect.top > 200) {
      menu.style.top = 'auto';
      menu.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
    } else {
      menu.style.top = (rect.bottom + 4) + 'px';
      menu.style.bottom = 'auto';
    }
    trigger.classList.add('open');
    menu.classList.add('show');
    overlay.classList.add('show');
    activeDropdown = { trigger: trigger, menu: menu, overlay: overlay };
  }

  /**
   * Initialize a dropdown on a trigger element.
   * @param {HTMLElement} trigger - The element to attach to (will be replaced/upgraded)
   * @param {Object} config - { options, value, onChange, placeholder }
   * @returns {Object} - { setValue, getValue, destroy }
   */
  function init(trigger, config) {
    injectStyle();
    var options = config.options || [];
    var currentValue = config.value != null ? config.value : (options[0] && options[0].value);
    var onChange = config.onChange || function () {};

    // Build trigger
    trigger.classList.add('sd-trigger');
    trigger.innerHTML = '<span class="sd-label"></span>' + chevronSvg();
    var labelEl = trigger.querySelector('.sd-label');

    function findOption(val) {
      return options.find(function (o) { return o.value === val; });
    }

    function renderLabel() {
      var opt = findOption(currentValue);
      labelEl.textContent = opt ? opt.label : (config.placeholder || '请选择');
    }
    renderLabel();

    // Build menu
    var menu = document.createElement('div');
    menu.className = 'sd-menu';
    function renderMenu() {
      menu.innerHTML = options.map(function (o) {
        var selected = o.value === currentValue ? ' selected' : '';
        var disabled = o.disabled ? ' sd-disabled' : '';
        return '<div class="sd-option' + selected + disabled + '" data-value="' + String(o.value) + '">' +
          '<div class="sd-opt-text">' +
            '<div class="sd-opt-label">' + o.label + '</div>' +
            (o.desc ? '<div class="sd-opt-desc">' + o.desc + '</div>' : '') +
          '</div>' + checkSvg() + '</div>';
      }).join('');
      menu.querySelectorAll('.sd-option').forEach(function (el) {
        el.addEventListener('click', function () {
          if (el.classList.contains('sd-disabled')) return;
          var val = el.getAttribute('data-value');
          // Convert back to original type if numeric
          var orig = findOption(val);
          currentValue = orig ? orig.value : val;
          renderLabel();
          renderMenu();
          closeActive();
          onChange(currentValue);
        });
      });
    }
    renderMenu();
    document.body.appendChild(menu);

    // Overlay
    var overlay = document.createElement('div');
    overlay.className = 'sd-overlay';
    overlay.addEventListener('click', closeActive);
    document.body.appendChild(overlay);

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (trigger.classList.contains('open')) {
        closeActive();
      } else {
        renderMenu();
        openDropdown(trigger, menu, overlay);
      }
    });

    return {
      setValue: function (val) { currentValue = val; renderLabel(); renderMenu(); },
      getValue: function () { return currentValue; },
      setOptions: function (opts) { options = opts; renderMenu(); renderLabel(); },
      destroy: function () {
        closeActive();
        trigger.classList.remove('sd-trigger');
        trigger.innerHTML = '';
        menu.remove();
        overlay.remove();
      }
    };
  }

  // Close on escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeActive();
  });

  // Close on scroll (to avoid misalignment)
  document.addEventListener('scroll', function () {
    if (activeDropdown) closeActive();
  }, true);

  window.SettingsDropdown = { init: init, close: closeActive };
  console.log('[settings-dropdown] 统一下拉浮层组件已加载');
})();
