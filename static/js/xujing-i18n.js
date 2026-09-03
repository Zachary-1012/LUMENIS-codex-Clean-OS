/* 序境 · 轻量三语 i18n（中英韩）
 * 设计：渐进增强 —— 不重构现有 DOM/JS，通过 [data-xujing-i18n] 属性 + 字典切换。
 * 默认 zh；localStorage('xujing_lang') 记忆；无侵入、可回滚。
 */
(function () {
  'use strict';
  var LANG_KEY = 'xujing_lang';

  var DICT = {
    zh: {
      'brand.name': '序境',
      'brand.tagline': '芥子纳须弥',
      'brand.en': 'XUJING · Z-BRAND INTELLIGENCE PLATFORM',
      'brand.subtitle': 'CTH-POMS · 实时舆情 · 风险预警 · 智能报告',
      'top.collect': '采集数据',
      'top.zbmp': 'ZBMP工作台',
      'top.import': '导入',
      'top.ai': 'AI分析',
      'top.export': '导出报告',
      'nav.qa': '智能问答',
      'nav.overview': '总览',
      'nav.monitor': '舆情监测',
      'nav.alerts': '风险预警',
      'nav.events': '事件中心',
      'nav.kos': 'KOS传播主体',
      'nav.analysis': '数据分析',
      'nav.reports': '报告中心',
      'qa.placeholder': '你今天想知道什么？',
      'qa.example': '例如 今天太古汇有哪些高风险舆情？',
      'qa.enter': '进入智能问答',
      'qa.highrisk': '今日高风险',
      'qa.latest': '最新事件',
      'qa.daily': '生成日报',
      'status.collecting': '采集状态',
      'status.warning': '风险预警',
      'status.ai': 'AI引擎',
      'status.running': '运行中',
      'status.monitoring': '监测中',
      'status.ready': '就绪',
      'footer.prod': '序境·CTH-POMS生产工区·数据来自本地采集与分析管线',
      'lang.label': '语言'
    },
    en: {
      'brand.name': 'XUJING',
      'brand.tagline': 'Seed within Sumeru',
      'brand.en': 'XUJING · Z-BRAND INTELLIGENCE PLATFORM',
      'brand.subtitle': 'CTH-POMS · Real-time Opinion · Risk Alert · Intelligent Report',
      'top.collect': 'Collect',
      'top.zbmp': 'ZBMP Console',
      'top.import': 'Import',
      'top.ai': 'AI Analysis',
      'top.export': 'Export',
      'nav.qa': 'Ask AI',
      'nav.overview': 'Overview',
      'nav.monitor': 'Monitoring',
      'nav.alerts': 'Risk Alerts',
      'nav.events': 'Event Center',
      'nav.kos': 'KOS Entities',
      'nav.analysis': 'Analytics',
      'nav.reports': 'Reports',
      'qa.placeholder': 'What do you want to know today?',
      'qa.example': 'e.g. What high-risk opinion trends exist for Taikoo Hui today?',
      'qa.enter': 'Ask Now',
      'qa.highrisk': 'Today High Risk',
      'qa.latest': 'Latest Events',
      'qa.daily': 'Daily Report',
      'status.collecting': 'Collecting',
      'status.warning': 'Risk Alert',
      'status.ai': 'AI Engine',
      'status.running': 'Running',
      'status.monitoring': 'Monitoring',
      'status.ready': 'Ready',
      'footer.prod': 'XUJING · CTH-POMS Production · Data from local pipeline',
      'lang.label': 'Language'
    },
    ko: {
      'brand.name': '서경',
      'brand.tagline': '겟자 내 수메루',
      'brand.en': 'XUJING · Z-BRAND INTELLIGENCE PLATFORM',
      'brand.subtitle': 'CTH-POMS · 실시간 여론 · 리스크 알림 · 지능형 리포트',
      'top.collect': '수집',
      'top.zbmp': 'ZBMP 콘솔',
      'top.import': '가져오기',
      'top.ai': 'AI 분석',
      'top.export': '보고서 내보내기',
      'nav.qa': 'AI 질문',
      'nav.overview': '개요',
      'nav.monitor': '여론 모니터링',
      'nav.alerts': '리스크 알림',
      'nav.events': '이벤트 센터',
      'nav.kos': 'KOS 주체',
      'nav.analysis': '데이터 분석',
      'nav.reports': '리포트 센터',
      'qa.placeholder': '오늘 무엇을 알고 싶으신가요?',
      'qa.example': '예: 오늘 타이쿠후이의 고위험 여론은?',
      'qa.enter': '질문하기',
      'qa.highrisk': '오늘 고위험',
      'qa.latest': '최신 이벤트',
      'qa.daily': '일일 보고서',
      'status.collecting': '수집 중',
      'status.warning': '리스크 경고',
      'status.ai': 'AI 엔진',
      'status.running': '실행 중',
      'status.monitoring': '모니터링 중',
      'status.ready': '준비됨',
      'footer.prod': '서경 · CTH-POMS 프로덕션 · 로컬 파이프라인 데이터',
      'lang.label': '언어'
    }
  };

  function detect() {
    var saved = null;
    try { saved = localStorage.getItem(LANG_KEY); } catch (e) {}
    if (saved && DICT[saved]) return saved;
    var nav = (navigator.language || 'zh').toLowerCase();
    if (nav.indexOf('ko') === 0) return 'ko';
    if (nav.indexOf('en') === 0) return 'en';
    return 'zh';
  }

  var current = detect();

  function apply(lang) {
    current = DICT[lang] ? lang : 'zh';
    var dict = DICT[current] || DICT.zh;
    var nodes = document.querySelectorAll('[data-xujing-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-xujing-i18n');
      var text = dict[key];
      if (text !== undefined) nodes[i].textContent = text;
    }
    // 切换控件状态
    var btns = document.querySelectorAll('[data-xujing-lang]');
    for (var j = 0; j < btns.length; j++) {
      if (btns[j].getAttribute('data-xujing-lang') === current) {
        btns[j].classList.add('xujing-lang-active');
      } else {
        btns[j].classList.remove('xujing-lang-active');
      }
    }
    try { localStorage.setItem(LANG_KEY, current); } catch (e) {}
    if (document.documentElement) document.documentElement.setAttribute('lang', current);
    window.dispatchEvent(new CustomEvent('xujing:lang', { detail: { lang: current } }));
  }

  window.xujingSetLang = function (lang) { apply(lang); };
  window.xujingGetLang = function () { return current; };
  window.xujingT = function (key) {
    var dict = DICT[current] || DICT.zh;
    return dict[key] !== undefined ? dict[key] : key;
  };
  // 暴露字典（供报告/工具层复用）
  window.XUJING_I18N = DICT;
  window.XUJING_LANG_KEY = LANG_KEY;

  // 自动应用（DOM 就绪后）
  function init() {
    apply(current);
    // 语言切换控件事件委托
    document.addEventListener('click', function (e) {
      var el = e.target;
      while (el && el !== document) {
        if (el.getAttribute && el.getAttribute('data-xujing-lang')) {
          window.xujingSetLang(el.getAttribute('data-xujing-lang'));
          return;
        }
        el = el.parentNode;
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
