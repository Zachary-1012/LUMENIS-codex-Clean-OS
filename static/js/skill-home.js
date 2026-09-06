/**
 * skill-home.js — 主界面 Skill 轻量入口
 * 只显示已启用的常用 Skill 横排小图标（4-6个），点击跳转 Skill 商店
 */
(function () {
  'use strict';
  const COLORS = {ai_analyzer:'#0F766E',risk_engine:'#cf222e',report_generator:'#8250df',kos_engine:'#bf8700',collector_xhs:'#ff2442',collector_weibo:'#e6162d',collector_bilibili:'#0969da',brand_analysis:'#8250df',internal_browser:'#0969da',data_visualization:'#1a7f37',intelligence_library:'#8250df',alert_engine:'#bc4c00'};
  const ICONS = {ai_analyzer:'🧠',risk_engine:'⚠️',report_generator:'📄',kos_engine:'👥',collector_xhs:'📕',collector_weibo:'🔴',collector_bilibili:'📺',brand_analysis:'📊',internal_browser:'🌐',data_visualization:'📈',intelligence_library:'📚',alert_engine:'🔔'};
  const DEFAULT = '#656d76';

  async function load() {
    const strip = document.getElementById('chSkillStrip');
    const icons = document.getElementById('chSkillIcons');
    if (!strip || !icons) return;
    try {
      const resp = await fetch('/api/system/account/skills/status', {credentials:'include'});
      const data = await resp.json();
      const enabled = (data.skills||[]).filter(s => s.status==='enabled');
      if (!enabled.length) { strip.style.display='none'; return; }
      strip.style.display='flex';
      icons.innerHTML = enabled.slice(0,6).map(s => {
        const c = COLORS[s.skill_id]||DEFAULT, i = ICONS[s.skill_id]||'⚡';
        return `<div class="ch-skill-mini" title="${s.name}" style="background:${c}">${i}</div>`;
      }).join('');
      icons.querySelectorAll('.ch-skill-mini').forEach(el => el.addEventListener('click', () => { window.location.href='/system/skills'; }));
    } catch(e) { strip.style.display='none'; }
  }
  document.addEventListener('DOMContentLoaded', load);
})();
