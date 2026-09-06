/* ============================================================================
   LUMENIS Internal Browser — Frontend Controller
   对标 Safari/Chrome，全部在平台内完成，不跳系统外部浏览器。
   后端：browser_surface.py + browser_surface_api.py + internal_browser.py
   ============================================================================ */
(function (global) {
  'use strict';

  // ===== Config =====
  var CONFIG = {
    cdpPort: 9222,              // 默认 CDP 端口（采集主号）
    screenshotQuality: 60,      // 截图质量
    screenshotInterval: 3000,   // 截图轮询间隔（ms）
    tabRefreshInterval: 5000,   // Tab 列表刷新间隔
  };

  // ===== State =====
  var state = {
    tabs: [],
    activeTabId: null,
    currentUrl: '',
    currentTitle: '',
    navMode: 'strict',
    isLoading: false,
    screenshotTimer: null,
    tabTimer: null,
    pendingUrl: null,           // 等待确认的 URL
    pendingTargetId: null,      // 等待确认的 target_id
    sidebarOpen: true,
    activePanel: 'bookmarks',
    bookmarks: [],
    history: [],
    browserOnline: false,
  };

  // ===== DOM Helpers =====
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }
  function icon(name, size) {
    return typeof licon === 'function' ? licon(name, size || 16) : '';
  }
  function renderIconsIn(container) {
    if (!container || typeof licon !== 'function') return;
    container.querySelectorAll('[data-icon]').forEach(function (el) {
      var name = el.getAttribute('data-icon');
      var sz = parseInt(el.getAttribute('data-icon-size') || '16', 10);
      el.innerHTML = licon(name, sz);
    });
  }

  // ===== API Helpers =====
  function api(url, options) {
    var opts = options || {};
    opts.headers = opts.headers || {};
    opts.headers['Content-Type'] = 'application/json';
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(url, opts).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok && !d) throw new Error('HTTP ' + r.status);
        return d;
      });
    });
  }

  function apiGet(url) { return api(url); }
  function apiPost(url, body) { return api(url, { method: 'POST', body: body }); }

  // ===== URL Helpers =====
  function normalizeUrl(input) {
    var s = (input || '').trim();
    if (!s) return '';
    // 如果已经是完整 URL
    if (/^https?:\/\//i.test(s)) return s;
    // 如果看起来像域名（含点且不含空格）
    if (/^[a-zA-Z0-9][a-zA-Z0-9-]*(\.[a-zA-Z0-9-]+)+(\/.*)?$/.test(s)) {
      return 'https://' + s;
    }
    // 否则作为搜索
    return 'https://www.bing.com/search?q=' + encodeURIComponent(s);
  }

  function getHost(url) {
    try { return new URL(url).hostname.toLowerCase(); } catch (e) { return ''; }
  }

  function isInternalHost(host) {
    return host === '127.0.0.1' || host === 'localhost' || host === '::1' ||
           host.endsWith('.localhost');
  }

  function isPlatformDomain(host) {
    var platforms = ['xiaohongshu.com', 'rednote.com', 'weibo.com', 'bilibili.com',
                     'zhihu.com', 'douyin.com'];
    return platforms.some(function (p) { return host === p || host.endsWith('.' + p); });
  }

  function detectPlatform(url) {
    var host = getHost(url);
    if (host.indexOf('xiaohongshu') >= 0 || host.indexOf('rednote') >= 0) return '小红书';
    if (host.indexOf('weibo') >= 0) return '微博';
    if (host.indexOf('bilibili') >= 0) return 'B站';
    if (host.indexOf('zhihu') >= 0) return '知乎';
    if (host.indexOf('douyin') >= 0) return '抖音';
    if (isInternalHost(host)) return '系统内部';
    return '外部网站';
  }

  // ===== Security Indicator =====
  function updateSecurityIndicator(evaluation) {
    var indicator = $('security-indicator');
    var label = $('security-label');
    if (!indicator || !label) return;

    indicator.className = 'browser-security-indicator';
    var status = evaluation ? evaluation.status : 'unknown';
    var host = evaluation ? evaluation.host : getHost(state.currentUrl);

    if (status === 'allowed' && isInternalHost(host)) {
      indicator.classList.add('is-secure');
      indicator.innerHTML = icon('lock', 16) + '<span class="browser-security-label">内部安全</span>';
    } else if (status === 'allowed' && isPlatformDomain(host)) {
      indicator.classList.add('is-secure');
      indicator.innerHTML = icon('lock', 16) + '<span class="browser-security-label">平台域</span>';
    } else if (status === 'need_confirmation') {
      indicator.classList.add('is-warning');
      indicator.innerHTML = icon('alertTriangle', 16) + '<span class="browser-security-label">需确认</span>';
    } else if (status === 'blocked') {
      indicator.classList.add('is-danger');
      indicator.innerHTML = icon('alertTriangle', 16) + '<span class="browser-security-label">已拦截</span>';
    } else {
      indicator.classList.add('is-unknown');
      indicator.innerHTML = icon('globe', 16) + '<span class="browser-security-label">未知</span>';
    }
  }

  // ===== Tab Management =====
  function loadTabs() {
    apiGet('/api/browser-surface/tabs?port=' + CONFIG.cdpPort)
      .then(function (d) {
        if (d.ok && d.tabs) {
          state.tabs = d.tabs;
          renderTabs();
          updateCollectStatus();
        }
      })
      .catch(function () { /* 静默失败，下次轮询重试 */ });
  }

  function renderTabs() {
    var list = $('browser-tab-list');
    if (!list) return;
    var html = state.tabs.map(function (tab) {
      var isActive = tab.target_id === state.activeTabId;
      var title = tab.title || tab.url || '新标签页';
      var favicon = isPlatformDomain(getHost(tab.url)) ? icon('globe', 14) : icon('globe', 14);
      return '<div class="browser-tab' + (isActive ? ' is-active' : '') + '" '
        + 'data-id="' + esc(tab.target_id) + '" onclick="BrowserApp.switchTab(\'' + esc(tab.target_id) + '\')">'
        + '<div class="browser-tab__favicon">' + favicon + '</div>'
        + '<div class="browser-tab__title">' + esc(title) + '</div>'
        + '<div class="browser-tab__close" onclick="event.stopPropagation();BrowserApp.closeTab(\'' + esc(tab.target_id) + '\')">'
        + icon('close', 12) + '</div>'
        + '</div>';
    }).join('');
    list.innerHTML = html;
    renderIconsIn(list);
  }

  function switchTab(targetId) {
    state.activeTabId = targetId;
    apiPost('/api/browser-surface/tab/activate', { target_id: targetId, port: CONFIG.cdpPort })
      .then(function () {
        renderTabs();
        refreshScreenshot();
        updateAddressFromTab();
      })
      .catch(function (e) { console.warn('switchTab failed:', e); });
  }

  function closeTab(targetId) {
    apiPost('/api/browser-surface/tab/close', { target_id: targetId, port: CONFIG.cdpPort })
      .then(function () {
        if (state.activeTabId === targetId) {
          state.activeTabId = null;
        }
        loadTabs();
        setTimeout(function () {
          if (!state.activeTabId && state.tabs.length > 0) {
            switchTab(state.tabs[0].target_id);
          } else if (state.tabs.length === 0) {
            showPlaceholder();
          }
        }, 300);
      })
      .catch(function (e) { console.warn('closeTab failed:', e); });
  }

  function newTab() {
    var url = 'https://www.xiaohongshu.com';
    apiPost('/api/browser-surface/tab/new', { url: url, port: CONFIG.cdpPort })
      .then(function (d) {
        if (d.ok && d.tab) {
          state.activeTabId = d.tab.target_id;
          loadTabs();
          setTimeout(function () {
            refreshScreenshot();
            updateAddressFromTab();
          }, 500);
        } else {
          console.warn('newTab failed:', d.error);
        }
      })
      .catch(function (e) { console.warn('newTab failed:', e); });
  }

  function updateAddressFromTab() {
    var tab = state.tabs.find(function (t) { return t.target_id === state.activeTabId; });
    if (tab) {
      state.currentUrl = tab.url || '';
      state.currentTitle = tab.title || '';
      $('address-input').value = tab.url || '';
      evaluateUrl(tab.url || '');
    }
  }

  // ===== Navigation =====
  function navigateTo(url, confirmed) {
    var targetUrl = normalizeUrl(url);
    if (!targetUrl) return;

    state.isLoading = true;
    setLoadingUI(true);

    var body = { url: targetUrl, port: CONFIG.cdpPort };
    if (confirmed) body.confirmed = true;
    if (state.activeTabId) body.target_id = state.activeTabId;

    // 使用 internal-browser navigate（支持 confirmed 参数）
    apiPost('/api/internal-browser/navigate', body)
      .then(function (d) {
        state.isLoading = false;
        setLoadingUI(false);

        if (d.status === 'need_confirmation') {
          // 弹出确认弹窗
          state.pendingUrl = targetUrl;
          state.pendingTargetId = state.activeTabId;
          showConfirmModal(targetUrl);
          return;
        }
        if (d.status === 'blocked') {
          showBlockedPage(targetUrl, d.gate ? d.gate.reason : d.error || '访问被拦截');
          return;
        }
        if (d.ok || d.status === 'navigated') {
          state.currentUrl = targetUrl;
          $('address-input').value = targetUrl;
          evaluateUrl(targetUrl);
          recordHistory(targetUrl);
          hideBlockedPage();
          setTimeout(function () {
            refreshScreenshot();
            loadTabs();
          }, 800);
        } else {
          console.warn('navigate failed:', d.error);
        }
      })
      .catch(function (e) {
        state.isLoading = false;
        setLoadingUI(false);
        console.warn('navigate error:', e);
      });
  }

  function evaluateUrl(url) {
    if (!url) return;
    apiGet('/api/browser-surface/policy?url=' + encodeURIComponent(url))
      .then(function (d) {
        if (d.evaluation) {
          updateSecurityIndicator(d.evaluation);
          state.navMode = d.nav_mode || state.navMode;
        }
      })
      .catch(function () { /* 静默 */ });
  }

  function goBack() {
    // 使用 CDP history back
    apiPost('/api/internal-browser/history', { action: 'back', account: '' })
      .then(function () {
        setTimeout(function () {
          refreshScreenshot();
          loadTabs();
          updateAddressFromTab();
        }, 500);
      })
      .catch(function (e) { console.warn('goBack failed:', e); });
  }

  function goForward() {
    apiPost('/api/internal-browser/history', { action: 'forward', account: '' })
      .then(function () {
        setTimeout(function () {
          refreshScreenshot();
          loadTabs();
          updateAddressFromTab();
        }, 500);
      })
      .catch(function (e) { console.warn('goForward failed:', e); });
  }

  function refresh() {
    var body = { port: CONFIG.cdpPort };
    if (state.activeTabId) body.target_id = state.activeTabId;
    apiPost('/api/internal-browser/refresh', body)
      .then(function () {
        state.isLoading = true;
        setLoadingUI(true);
        setTimeout(function () {
          refreshScreenshot();
          loadTabs();
          state.isLoading = false;
          setLoadingUI(false);
        }, 1000);
      })
      .catch(function (e) { console.warn('refresh failed:', e); });
  }

  function stopLoading() {
    state.isLoading = false;
    setLoadingUI(false);
  }

  function setLoadingUI(loading) {
    var refreshBtn = $('btn-refresh');
    var stopBtn = $('btn-stop');
    if (refreshBtn) refreshBtn.style.display = loading ? 'none' : '';
    if (stopBtn) stopBtn.style.display = loading ? '' : 'none';
    if (loading && refreshBtn) refreshBtn.classList.add('is-loading');
    else if (refreshBtn) refreshBtn.classList.remove('is-loading');
  }

  // ===== Screenshot =====
  function refreshScreenshot() {
    var wrap = $('viewport-img-wrap');
    var placeholder = $('viewport-placeholder');
    if (!wrap) return;

    var url = '/api/browser-surface/screenshot?port=' + CONFIG.cdpPort + '&quality=' + CONFIG.screenshotQuality;
    if (state.activeTabId) url += '&target_id=' + encodeURIComponent(state.activeTabId);

    apiGet(url)
      .then(function (d) {
        if (d.ok && d.image_base64) {
          state.browserOnline = true;
          updateStatusBar(true);
          if (placeholder) placeholder.style.display = 'none';
          wrap.innerHTML = '<img class="browser-viewport__img" src="data:image/jpeg;base64,'
            + d.image_base64 + '" alt="浏览器画面" onclick="BrowserApp.onScreenshotClick(event)">';
          if (d.url) {
            state.currentUrl = d.url;
            $('address-input').value = d.url;
            evaluateUrl(d.url);
          }
          if (d.title) state.currentTitle = d.title;
          $('status-url').textContent = d.url || state.currentUrl || '—';
        } else {
          state.browserOnline = false;
          updateStatusBar(false);
          showPlaceholder(d.error || '截图失败');
        }
      })
      .catch(function (e) {
        state.browserOnline = false;
        updateStatusBar(false);
        showPlaceholder('连接失败: ' + e.message);
      });
  }

  function onScreenshotClick(e) {
    // 点击截图区域不做任何写操作（只读保护）
    // 未来可扩展为坐标映射点击，但当前保持只读
  }

  function showPlaceholder(msg) {
    var wrap = $('viewport-img-wrap');
    var placeholder = $('viewport-placeholder');
    if (wrap) {
      wrap.innerHTML = '<div class="browser-viewport__placeholder" id="viewport-placeholder">'
        + '<div class="browser-viewport__placeholder-icon">' + icon('globe', 32) + '</div>'
        + '<div class="browser-viewport__placeholder-text">' + (msg || '系统内置浏览器') + '</div>'
        + '<div class="browser-viewport__placeholder-sub">在地址栏输入 URL 开始浏览 · 所有操作在平台内完成</div>'
        + '</div>';
      renderIconsIn(wrap);
    }
  }

  // ===== Blocked Page =====
  function showBlockedPage(url, reason) {
    var blocked = $('browser-blocked');
    $('blocked-url').textContent = url;
    $('blocked-reason').textContent = reason || '该地址被安全策略拦截';
    if (blocked) blocked.style.display = 'flex';
    updateSecurityIndicator({ status: 'blocked', host: getHost(url) });
  }

  function hideBlockedPage() {
    var blocked = $('browser-blocked');
    if (blocked) blocked.style.display = 'none';
  }

  // ===== Confirmation Modal =====
  function showConfirmModal(url) {
    $('confirm-url').textContent = url;
    var modal = $('confirm-modal');
    if (modal) modal.classList.add('is-visible');
  }

  function hideConfirmModal() {
    var modal = $('confirm-modal');
    if (modal) modal.classList.remove('is-visible');
  }

  function confirmNavigate() {
    var url = state.pendingUrl;
    hideConfirmModal();
    if (url) {
      navigateTo(url, true);
    }
    state.pendingUrl = null;
  }

  function cancelNavigate() {
    hideConfirmModal();
    state.pendingUrl = null;
  }

  // ===== Sidebar =====
  function toggleSidebar() {
    state.sidebarOpen = !state.sidebarOpen;
    var sidebar = $('browser-sidebar');
    var btn = $('btn-sidebar');
    if (sidebar) sidebar.classList.toggle('is-collapsed', !state.sidebarOpen);
    if (btn) btn.classList.toggle('is-active', state.sidebarOpen);
  }

  function switchPanel(name) {
    state.activePanel = name;
    document.querySelectorAll('.browser-sidebar__tab').forEach(function (t) {
      t.classList.toggle('is-active', t.getAttribute('data-panel') === name);
    });
    document.querySelectorAll('.browser-panel').forEach(function (p) {
      p.style.display = p.id === 'panel-' + name ? '' : 'none';
    });
    if (name === 'bookmarks') loadBookmarks();
    if (name === 'history') loadHistory();
    if (name === 'collect') updateCollectStatus();
  }

  // ===== Bookmarks =====
  function loadBookmarks() {
    apiGet('/api/browser-surface/bookmarks')
      .then(function (d) {
        state.bookmarks = d.bookmarks || [];
        renderBookmarks();
      })
      .catch(function (e) { console.warn('loadBookmarks failed:', e); });
  }

  function renderBookmarks() {
    var list = $('bookmarks-list');
    if (!list) return;
    if (state.bookmarks.length === 0) {
      list.innerHTML = '<div class="browser-empty">' + icon('bookmark', 28)
        + '<div class="browser-empty__text">暂无书签</div></div>';
      renderIconsIn(list);
      return;
    }
    var html = state.bookmarks.map(function (b) {
      return '<div class="browser-list-item" onclick="BrowserApp.navigateTo(\'' + esc(b.url) + '\')">'
        + '<div class="browser-list-item__icon">' + icon('globe', 14) + '</div>'
        + '<div class="browser-list-item__body">'
        + '<div class="browser-list-item__title">' + esc(b.title || b.url) + '</div>'
        + '<div class="browser-list-item__url">' + esc(b.url) + '</div>'
        + '<div class="browser-list-item__meta">' + esc(b.added_at || '') + '</div>'
        + '</div>'
        + '<div class="browser-list-item__remove" onclick="event.stopPropagation();BrowserApp.removeBookmark(\'' + esc(b.url) + '\')">'
        + icon('close', 12) + '</div>'
        + '</div>';
    }).join('');
    list.innerHTML = html;
    renderIconsIn(list);
  }

  function toggleBookmark() {
    var url = state.currentUrl;
    if (!url) return;
    // 检查是否已存在
    var exists = state.bookmarks.some(function (b) { return b.url === url; });
    if (exists) {
      removeBookmark(url);
    } else {
      apiPost('/api/browser-surface/bookmarks', { title: state.currentTitle || url, url: url })
        .then(function () { loadBookmarks(); })
        .catch(function (e) { console.warn('addBookmark failed:', e); });
    }
  }

  function removeBookmark(url) {
    apiPost('/api/browser-surface/bookmark/remove', { url: url })
      .then(function () { loadBookmarks(); })
      .catch(function (e) { console.warn('removeBookmark failed:', e); });
  }

  function refreshBookmarks() { loadBookmarks(); }

  // ===== History =====
  function loadHistory() {
    apiGet('/api/browser-surface/history?limit=50')
      .then(function (d) {
        state.history = d.history || [];
        renderHistory();
      })
      .catch(function (e) { console.warn('loadHistory failed:', e); });
  }

  function renderHistory() {
    var list = $('history-list');
    if (!list) return;
    if (state.history.length === 0) {
      list.innerHTML = '<div class="browser-empty">' + icon('history', 28)
        + '<div class="browser-empty__text">暂无浏览历史</div></div>';
      renderIconsIn(list);
      return;
    }
    var html = state.history.map(function (h) {
      return '<div class="browser-list-item" onclick="BrowserApp.navigateTo(\'' + esc(h.url) + '\')">'
        + '<div class="browser-list-item__icon">' + icon('globe', 14) + '</div>'
        + '<div class="browser-list-item__body">'
        + '<div class="browser-list-item__title">' + esc(h.title || h.url) + '</div>'
        + '<div class="browser-list-item__url">' + esc(h.url) + '</div>'
        + '<div class="browser-list-item__meta">' + esc(h.visited_at || '') + '</div>'
        + '</div></div>';
    }).join('');
    list.innerHTML = html;
    renderIconsIn(list);
  }

  function recordHistory(url) {
    if (!url) return;
    apiPost('/api/browser-surface/history', { title: state.currentTitle || url, url: url })
      .catch(function () { /* 静默 */ });
  }

  function clearHistory() {
    apiPost('/api/browser-surface/history/clear', {})
      .then(function () { loadHistory(); })
      .catch(function (e) { console.warn('clearHistory failed:', e); });
  }

  // ===== Collect Status =====
  function updateCollectStatus() {
    $('cs-platform').textContent = detectPlatform(state.currentUrl);
    $('cs-port').textContent = CONFIG.cdpPort;
    $('cs-page').textContent = state.currentTitle || state.currentUrl || '—';
    $('cs-tabs').textContent = state.tabs.length;

    // 检测浏览器在线状态
    apiGet('/api/browser-surface/tabs?port=' + CONFIG.cdpPort)
      .then(function (d) {
        var online = d.ok && d.tabs && d.tabs.length > 0;
        var el = $('cs-online');
        el.textContent = online ? '在线' : '离线';
        el.className = 'browser-collect-status__value ' + (online ? 'is-online' : 'is-offline');
      })
      .catch(function () {
        $('cs-online').textContent = '离线';
        $('cs-online').className = 'browser-collect-status__value is-offline';
      });

    // 导航模式
    apiGet('/api/browser-surface/policy')
      .then(function (d) {
        $('cs-navmode').textContent = d.nav_mode || 'strict';
      })
      .catch(function () { $('cs-navmode').textContent = 'strict'; });
  }

  function checkCollectStatus() {
    updateCollectStatus();
    refreshScreenshot();
  }

  // ===== Status Bar =====
  function updateStatusBar(online) {
    var dot = $('status-dot');
    var text = $('status-text');
    if (dot) dot.className = 'browser-statusbar__dot ' + (online ? 'is-online' : 'is-offline');
    if (text) text.textContent = online ? '已连接' : '未连接';
  }

  function updateTime() {
    var el = $('status-time');
    if (el) el.textContent = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  }

  // ===== Polling =====
  function startPolling() {
    stopPolling();
    state.screenshotTimer = setInterval(refreshScreenshot, CONFIG.screenshotInterval);
    state.tabTimer = setInterval(loadTabs, CONFIG.tabRefreshInterval);
  }

  function stopPolling() {
    if (state.screenshotTimer) clearInterval(state.screenshotTimer);
    if (state.tabTimer) clearInterval(state.tabTimer);
    state.screenshotTimer = null;
    state.tabTimer = null;
  }

  // ===== Init =====
  function init() {
    // 地址栏回车导航
    var addrInput = $('address-input');
    if (addrInput) {
      addrInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          navigateTo(addrInput.value);
        }
      });
      addrInput.addEventListener('focus', function () { this.select(); });
    }

    // 初始加载
    loadTabs();
    loadBookmarks();
    refreshScreenshot();
    updateCollectStatus();
    updateTime();
    setInterval(updateTime, 1000);

    // 启动轮询
    startPolling();

    // 页面可见性变化时暂停/恢复轮询
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopPolling();
      else {
        refreshScreenshot();
        loadTabs();
        startPolling();
      }
    });

    console.log('[LUMENIS Browser] Initialized, port=' + CONFIG.cdpPort);
  }

  // ===== Public API =====
  var BrowserApp = {
    init: init,
    navigateTo: navigateTo,
    goBack: goBack,
    goForward: goForward,
    refresh: refresh,
    stopLoading: stopLoading,
    newTab: newTab,
    closeTab: closeTab,
    switchTab: switchTab,
    toggleSidebar: toggleSidebar,
    switchPanel: switchPanel,
    toggleBookmark: toggleBookmark,
    removeBookmark: removeBookmark,
    refreshBookmarks: refreshBookmarks,
    clearHistory: clearHistory,
    confirmNavigate: confirmNavigate,
    cancelNavigate: cancelNavigate,
    checkCollectStatus: checkCollectStatus,
    onScreenshotClick: onScreenshotClick,
  };

  global.BrowserApp = BrowserApp;

  // Auto-init
  if (document.readyState !== 'loading') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }

})(window);
