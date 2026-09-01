/* ============================================================
   ZBIP 多系统启动页共享脚本（独立预览用，当前不接入主系统）
   流程：启动海报(约3.2s/可跳过) → 苹果风居中密码登录 → 占位主界面
   说明：此处仅为前端交互演示，不做真实鉴权；真实鉴权由后端
   Basic Auth / 登录体系负责。未来接入时替换 requestLogin()。
   ============================================================ */
(function () {
  var SPLASH_MS = 3200;
  var stage = document.getElementById('stage');
  var login = document.getElementById('login');
  var after = document.getElementById('after');
  var errEl = document.getElementById('loginErr');
  var pwd = document.getElementById('pwdInput');
  var account = document.getElementById('accountInput');
  var gone = false, timer = null;

  function showLogin() {
    if (gone) return;
    gone = true;
    stage.classList.add('gone');
    setTimeout(function () {
      login.classList.add('show');
      setTimeout(function () { (account || pwd).focus(); }, 350);
    }, 420);
  }

  // 自动弹出 / 点击跳过
  timer = setTimeout(showLogin, SPLASH_MS);
  var skip = document.getElementById('skip');
  if (skip) skip.addEventListener('click', function () { clearTimeout(timer); showLogin(); });
  stage.addEventListener('click', function (e) {
    if (e.target.closest('.skip')) return;
    clearTimeout(timer); showLogin();
  });

  function fail(msg) {
    errEl.textContent = msg;
    pwd.select();
  }

  function requestLogin() {
    // 演示模式：账号非空 + 密码≥4位即进入（真实接入时改为后端鉴权接口）
    var u = (account ? account.value : '').trim();
    var p = pwd.value;
    if (account && !u) return fail('请输入账号');
    if (!p) return fail('请输入密码');
    if (p.length < 4) return fail('密码长度不足');
    errEl.textContent = '';
    login.classList.remove('show');
    after.classList.add('show');
  }

  var btn = document.getElementById('btnLogin');
  if (btn) btn.addEventListener('click', requestLogin);
  [account, pwd].forEach(function (el) {
    if (el) el.addEventListener('keydown', function (e) { if (e.key === 'Enter') requestLogin(); });
  });
})();
