/* 统一本地文件导入：点击顶栏"导入"按钮 → 浏览本地 → 上传到 /api/local-import */
(function(){
  'use strict';
  var input = document.getElementById('localImportInput');
  if (!input) return;

  function getAuthHeader() {
    if (window.__Z_AUTH) return { 'Authorization': window.__Z_AUTH };
    return {};
  }

  function showToast(msg, type) {
    var t = document.createElement('div');
    t.style.cssText = 'position:fixed;top:70px;right:20px;z-index:99999;padding:12px 20px;border-radius:10px;font-size:13px;box-shadow:0 4px 20px rgba(0,0,0,.15);max-width:360px;word-break:break-all;';
    t.style.background = type === 'error' ? '#fff0f0' : type === 'success' ? '#f0fff4' : '#f5f5f7';
    t.style.color = type === 'error' ? '#d32f2f' : type === 'success' ? '#2e7d32' : '#1d1d1f';
    t.style.border = '1px solid ' + (type === 'error' ? '#ffcdd2' : type === 'success' ? '#c8e6c9' : '#e0e0e0');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function(){ t.style.opacity='0'; t.style.transition='opacity .3s'; setTimeout(function(){ t.remove(); }, 300); }, 4000);
  }

  input.addEventListener('change', function(e) {
    var files = e.target.files;
    if (!files || files.length === 0) return;

    var fd = new FormData();
    for (var i = 0; i < files.length; i++) {
      fd.append('files', files[i]);
    }

    showToast('正在上传 ' + files.length + ' 个文件...', 'info');

    fetch('/api/local-import', {
      method: 'POST',
      headers: getAuthHeader(),
      body: fd
    })
    .then(function(r){ return r.json(); })
    .then(function(data){
      if (data.ok) {
        var msg = '成功导入 ' + data.imported + '/' + data.total + ' 个文件';
        if (data.results && data.results.length) {
          var failed = data.results.filter(function(r){ return !r.ok; });
          if (failed.length) msg += '，' + failed.length + ' 个失败（格式或大小不支持）';
        }
        showToast(msg, 'success');
      } else {
        showToast('导入失败: ' + (data.error || '未知错误'), 'error');
      }
    })
    .catch(function(err){
      showToast('上传出错: ' + err.message, 'error');
    });

    input.value = '';
  });
})();
