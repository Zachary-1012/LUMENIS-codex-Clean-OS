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
    opts.credentials = 'include';
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
    }
    var doFetch = function() { return fetch(url, opts); };
    if (window.LUMENIS && window.LUMENIS.Auth && typeof window.LUMENIS.Auth.getHeader === 'function') {
      return window.LUMENIS.Auth.getHeader().then(function(h) {
        if (h) { opts.headers['Authorization'] = h; window.__Z_AUTH = h; }
        return doFetch();
      }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok && !d) throw new Error('HTTP ' + r.status);
        return d;
      });
      });
    } else {
      return doFetch().then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok && !d) throw new Error('HTTP ' + r.status);
        return d;
      });
      });
    }
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

/* ============================================================================
   ZBC AI Browser Runtime — Frontend Controller
   调用链：AI Agent → Browser Skill → Permission Gate → Browser Runtime
          → Observe → Reason → Plan → Action → Verify → Evidence → Trace
   每个 Action 必须经过 Verification 闭环，禁止 AI 说"点击成功"就认定成功。
   ============================================================================ */
(function (global) {
  'use strict';

  // ===== State =====
  var aiState = {
    sessionId: null,
    sessionStatus: null,
    currentUrl: '',
    currentTitle: '',
    riskLevel: 'medium',
    circuitBreaker: 'closed',
    pendingApproval: null,
    evidenceCache: [],
  };

  // ===== DOM Helpers =====
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  // ===== API Helpers =====
  function api(url, options) {
    var opts = options || {};
    opts.headers = opts.headers || {};
    opts.headers['Content-Type'] = 'application/json';
    opts.credentials = 'include';
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
    }
    var doFetch = function() { return fetch(url, opts); };
    if (window.LUMENIS && window.LUMENIS.Auth && typeof window.LUMENIS.Auth.getHeader === 'function') {
      return window.LUMENIS.Auth.getHeader().then(function(h) {
        if (h) { opts.headers['Authorization'] = h; window.__Z_AUTH = h; }
        return doFetch();
      }).then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok && !d) throw new Error('HTTP ' + r.status);
        return d;
      });
      });
    } else {
      return doFetch().then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok && !d) throw new Error('HTTP ' + r.status);
        return d;
      });
      });
    }
  }
  function apiPost(url, body) { return api(url, { method: 'POST', body: body }); }
  function apiGet(url) { return api(url); }

  // ===== Session Management =====
  function createSession() {
    setActionResult('正在创建 AI Browser Session...', 'info');
    apiPost('/api/browser/sessions', {
      cdp_port: 9222,
      headless: true,
      auto_start: true,
      idle_timeout: 600,
      max_lifetime: 3600,
    }).then(function (resp) {
      if (resp.ok) {
        aiState.sessionId = resp.session_id;
        aiState.sessionStatus = resp.status;
        updateStatusUI();
        setActionResult(
          'Session 创建成功: ' + resp.session_id +
          (resp.started ? ' (浏览器已启动)' : ' (启动失败: ' + (resp.start_error || 'unknown') + ')'),
          'success'
        );
      } else {
        setActionResult('Session 创建失败: ' + resp.error, 'error');
      }
    }).catch(function (e) {
      setActionResult('Session 创建异常: ' + e.message, 'error');
    });
  }

  function stopSession() {
    if (!aiState.sessionId) {
      setActionResult('没有活跃 Session', 'warn');
      return;
    }
    apiPost('/api/browser/sessions/' + aiState.sessionId + '/stop', {}).then(function (resp) {
      setActionResult('Session 已关闭: ' + aiState.sessionId, 'info');
      aiState.sessionId = null;
      aiState.sessionStatus = 'closed';
      updateStatusUI();
    }).catch(function (e) {
      setActionResult('关闭异常: ' + e.message, 'error');
    });
  }

  function refreshStatus() {
    if (!aiState.sessionId) return;
    apiGet('/api/browser/sessions/' + aiState.sessionId).then(function (resp) {
      if (resp.ok) {
        aiState.sessionStatus = resp.status;
        aiState.currentUrl = resp.current_url || '';
        aiState.currentTitle = resp.current_title || '';
        aiState.circuitBreaker = (resp.circuit_breaker && resp.circuit_breaker.open) ? 'OPEN' : 'closed';
        updateStatusUI();
      }
    }).catch(function () {});
  }

  function updateStatusUI() {
    if ($('ai-session-id')) $('ai-session-id').textContent = aiState.sessionId || '未创建';
    if ($('ai-session-status')) {
      var el = $('ai-session-status');
      el.textContent = aiState.sessionStatus || '—';
      el.style.color = aiState.sessionStatus === 'running' ? '#059669' :
                       aiState.sessionStatus === 'need_verify' ? '#D97706' :
                       aiState.sessionStatus === 'error' ? '#DC2626' : '#6B7280';
    }
    if ($('ai-current-url')) $('ai-current-url').textContent = aiState.currentUrl || '—';
    if ($('ai-risk-level')) $('ai-risk-level').textContent = aiState.riskLevel;
    if ($('ai-circuit-breaker')) {
      var cb = $('ai-circuit-breaker');
      cb.textContent = aiState.circuitBreaker;
      cb.style.color = aiState.circuitBreaker === 'OPEN' ? '#DC2626' : '#059669';
    }
  }

  // ===== Observe =====
  function observe() {
    if (!requireSession()) return;
    setActionResult('正在观察页面...', 'info');
    apiPost('/api/browser/sessions/' + aiState.sessionId + '/observe', {
      include_dom: true,
      include_accessibility: false,
      max_text_length: 1500,
      screenshot: false,
    }).then(function (resp) {
      if (resp.ok && resp.state) {
        var s = resp.state;
        aiState.currentUrl = s.url || '';
        aiState.currentTitle = s.title || '';
        updateStatusUI();

        var html = '<div style="margin-bottom:6px;"><strong>URL:</strong> ' + esc(s.url) + '</div>';
        html += '<div style="margin-bottom:6px;"><strong>Title:</strong> ' + esc(s.title) + '</div>';
        html += '<div style="margin-bottom:6px;"><strong>元素数:</strong> ' + (s.element_count || 0) + '</div>';
        html += '<div style="margin-bottom:6px;"><strong>State Hash:</strong> ' + esc(resp.state_hash || '') + '</div>';
        if (s.body_text) {
          html += '<div style="margin-top:6px;padding-top:6px;border-top:1px solid #E5E7EB;"><strong>页面文本（脱敏）:</strong><br>' + esc(s.body_text.substring(0, 800)) + '</div>';
        }
        if (s.console_errors && s.console_errors.length > 0) {
          html += '<div style="margin-top:6px;color:#DC2626;"><strong>控制台错误 (' + s.console_errors.length + '):</strong><br>' + esc(s.console_errors.slice(0, 3).join('; ')) + '</div>';
        }
        $('ai-observe-content').innerHTML = html;

        // Injection warning
        if (resp.injection_scan && resp.injection_scan.detected) {
          $('ai-injection-warning').style.display = 'block';
          $('ai-injection-warning').textContent = '⚠ 检测到 Prompt Injection 模式: ' +
            (resp.injection_scan.patterns || []).join(', ') + '。网页内容已标记为不可信，不会改变Agent权限。';
        } else {
          $('ai-injection-warning').style.display = 'none';
        }

        setActionResult('观察完成', 'success');
      } else {
        setActionResult('观察失败: ' + (resp.error || 'unknown'), 'error');
      }
    }).catch(function (e) {
      setActionResult('观察异常: ' + e.message, 'error');
    });
  }

  // ===== Action Execution =====
  function executeAction() {
    if (!requireSession()) return;

    var actionType = $('ai-action-type').value;
    var selector = $('ai-action-selector').value.trim();
    var value = $('ai-action-value').value.trim();
    var expectedStr = $('ai-action-expected').value.trim();

    // Parse expected state
    var expected = null;
    if (expectedStr) {
      expected = {};
      expectedStr.split(',').forEach(function (pair) {
        var kv = pair.split('=');
        if (kv.length === 2) {
          expected[kv[0].trim()] = kv[1].trim();
        }
      });
    }

    var body = {
      action: actionType,
      selector: selector,
      value: value,
      text: value,
      url: actionType === 'navigate' ? value : '',
      expected: expected,
      risk_level: 'medium',
    };

    setActionResult('正在执行 Action: ' + actionType + '...', 'info');

    apiPost('/api/browser/sessions/' + aiState.sessionId + '/action', body).then(function (resp) {
      handleActionResult(resp);
    }).catch(function (e) {
      setActionResult('Action 执行异常: ' + e.message, 'error');
    });
  }

  function handleActionResult(resp) {
    var html = '';
    var status = 'info';

    if (resp.ok || resp.success) {
      status = 'success';
      html = '<div style="color:#059669;font-weight:600;margin-bottom:6px;">✓ Action 执行成功</div>';
    } else if (resp.needs_human_approval || resp.human_escalation_required) {
      status = 'warn';
      html = '<div style="color:#D97706;font-weight:600;margin-bottom:6px;">⚠ 需要人工审批</div>';
      html += '<div>' + esc(resp.escalation_reason || resp.error || '') + '</div>';
      showApprovalModal(resp);
    } else {
      status = 'error';
      html = '<div style="color:#DC2626;font-weight:600;margin-bottom:6px;">✗ Action 执行失败</div>';
      html += '<div>' + esc(resp.error || 'unknown error') + '</div>';
    }

    // Verification result
    if (resp.verification) {
      var v = resp.verification;
      html += '<div style="margin-top:8px;padding-top:8px;border-top:1px solid #E5E7EB;">';
      html += '<div style="font-weight:600;margin-bottom:4px;">Verification: ' +
        (v.passed ? '<span style="color:#059669;">PASS</span>' : '<span style="color:#DC2626;">FAIL</span>') + '</div>';
      if (v.differences && v.differences.length > 0) {
        html += '<div style="color:#DC2626;">差异:</div><ul style="margin:4px 0;padding-left:16px;">';
        v.differences.forEach(function (d) {
          html += '<li>' + esc(d) + '</li>';
        });
        html += '</ul>';
      }
      if (v.actual) {
        html += '<div style="margin-top:4px;"><strong>Actual:</strong> URL=' + esc(v.actual.url || '') + '</div>';
      }
      html += '</div>';
    }

    // Recovery attempts
    if (resp.recovery_attempts && resp.recovery_attempts.length > 0) {
      html += '<div style="margin-top:8px;padding-top:8px;border-top:1px solid #E5E7EB;">';
      html += '<div style="font-weight:600;margin-bottom:4px;">Recovery 尝试 (' + resp.recovery_attempts.length + '):</div>';
      resp.recovery_attempts.forEach(function (r) {
        html += '<div>• ' + esc(r.strategy) + ': ' + (r.success ? '<span style="color:#059669;">成功</span>' : '<span style="color:#DC2626;">失败</span>') + '</div>';
      });
      html += '</div>';
    }

    // Evidence ID
    if (resp.evidence_id && resp.evidence_id > 0) {
      html += '<div style="margin-top:6px;font-size:10px;color:#9CA3AF;">Evidence ID: ' + resp.evidence_id + '</div>';
    }

    setActionResult(html, status);
    refreshStatus();
    refreshEvidence();
  }

  // ===== Human Approval Modal =====
  function showApprovalModal(resp) {
    aiState.pendingApproval = resp;
    $('ai-approval-action').textContent = resp.action || 'unknown';
    $('ai-approval-target').textContent = (resp.after_state && resp.after_state.url) || resp.target || '—';
    $('ai-approval-expected').textContent = resp.verification ? JSON.stringify(resp.verification.expected || {}).substring(0, 100) : '—';
    $('ai-approval-risk').textContent = 'HIGH - ' + (resp.escalation_reason || '需要人工确认');
    $('ai-approval-reason').textContent = resp.escalation_reason || 'AI Browser Runtime 请求人工确认。';
    $('ai-approval-modal').style.display = 'flex';
  }

  function approveAction() {
    if (!aiState.pendingApproval || !aiState.sessionId) {
      $('ai-approval-modal').style.display = 'none';
      return;
    }
    var pending = aiState.pendingApproval;
    apiPost('/api/browser/sessions/' + aiState.sessionId + '/human-approval', {
      approved: true,
      action: pending.action,
      selector: pending.selector || '',
      value: pending.value || '',
      reason: 'human approved',
    }).then(function (resp) {
      $('ai-approval-modal').style.display = 'none';
      aiState.pendingApproval = null;
      handleActionResult(resp);
    }).catch(function (e) {
      $('ai-approval-modal').style.display = 'none';
      setActionResult('审批执行异常: ' + e.message, 'error');
    });
  }

  function rejectAction() {
    if (aiState.sessionId) {
      apiPost('/api/browser/sessions/' + aiState.sessionId + '/human-approval', {
        approved: false,
      }).catch(function () {});
    }
    $('ai-approval-modal').style.display = 'none';
    aiState.pendingApproval = null;
    setActionResult('操作已被人工拒绝', 'warn');
  }

  // ===== Evidence Timeline =====
  function refreshEvidence() {
    if (!aiState.sessionId) return;
    apiGet('/api/browser/sessions/' + aiState.sessionId + '/evidence?limit=20').then(function (resp) {
      if (resp.ok && resp.records && resp.records.length > 0) {
        var html = '';
        resp.records.forEach(function (r) {
          var color = r.result === 'PASS' ? '#059669' :
                      r.result === 'FAIL' ? '#DC2626' :
                      r.result === 'RETRY' ? '#D97706' : '#7C3AED';
          html += '<div style="padding:4px 0;border-bottom:1px solid #F3F4F6;">';
          html += '<div style="display:flex;justify-content:space-between;">';
          html += '<span style="font-weight:500;">' + esc(r.action) + '</span>';
          html += '<span style="color:' + color + ';font-weight:600;">' + esc(r.result) + '</span>';
          html += '</div>';
          html += '<div style="font-size:10px;color:#9CA3AF;">' + esc(r.timestamp || '') +
            (r.retry_count > 0 ? ' · retries=' + r.retry_count : '') + '</div>';
          if (r.error) {
            html += '<div style="font-size:10px;color:#DC2626;margin-top:2px;">' + esc(r.error.substring(0, 100)) + '</div>';
          }
          html += '</div>';
        });
        $('ai-evidence-timeline').innerHTML = html;
        if (resp.stats) {
          aiState.riskLevel = resp.stats.pass_rate && parseInt(resp.stats.pass_rate) < 50 ? 'high' : 'medium';
          updateStatusUI();
        }
      } else {
        $('ai-evidence-timeline').innerHTML = '<div style="color:#9CA3AF;">暂无 Evidence 记录</div>';
      }
    }).catch(function () {});
  }

  // ===== Utilities =====
  function requireSession() {
    if (!aiState.sessionId) {
      setActionResult('请先创建 AI Browser Session', 'warn');
      return false;
    }
    return true;
  }

  function setActionResult(html, type) {
    var el = $('ai-action-result');
    if (!el) return;
    var colors = {
      success: '#059669',
      error: '#DC2626',
      warn: '#D97706',
      info: '#7C3AED',
    };
    var color = colors[type] || '#6B7280';
    if (type === 'info' || type === 'success' || type === 'error' || type === 'warn') {
      el.innerHTML = '<div style="color:' + color + ';">' + html + '</div>';
    } else {
      el.innerHTML = html;
    }
  }

  // ===== Auto-refresh =====
  var aiRefreshTimer = null;
  function startAutoRefresh() {
    if (aiRefreshTimer) return;
    aiRefreshTimer = setInterval(function () {
      if (aiState.sessionId) {
        refreshStatus();
      }
    }, 10000);
  }

  // ===== Public API =====
  var AIBrowser = {
    createSession: createSession,
    stopSession: stopSession,
    refreshStatus: refreshStatus,
    observe: observe,
    executeAction: executeAction,
    approveAction: approveAction,
    rejectAction: rejectAction,
    refreshEvidence: refreshEvidence,
    getState: function () { return aiState; },
  };

  global.AIBrowser = AIBrowser;

  // Auto-init when panel opened
  if (document.readyState !== 'loading') {
    startAutoRefresh();
  } else {
    document.addEventListener('DOMContentLoaded', startAutoRefresh);
  }

})(window);
