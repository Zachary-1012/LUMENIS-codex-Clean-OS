# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,_ROOT); os.chdir(_ROOT)
import ai_analyzer as A

cases = [
    # (标题, 内容, 期望)
    ("太古汇美奈小馆，我求你不要害我", "", "negative"),   # 用户案例
    ("广州太古汇ole员工态度投诉", "服务很差", "negative"),
    ("LV柜姐避雷，姐妹们别来", "", "negative"),
    ("在太古汇餐厅吃拉肚子了，吃出异物", "", "negative"),
    ("劝你别去这家店，踩雷", "", "negative"),
    ("再也不会来太古汇这家了，拉黑", "", "negative"),
    ("这家店不要太好吃，强烈推荐", "", "positive"),   # 正面强调豁免
    ("大小朋友都拒绝不了吧", "很喜欢", "positive"),  # 拒绝不了=正面
    ("方所表示：没有倒闭，择期重开", "", None),  # 澄清非负面(中性可接受)
    ("广州商场厕所都那么豪华 有点离谱哦", "很豪华", None),  # 褒义离谱,不判负即可
    ("也没人和我说在宝格丽能见到明星", "惊喜", None),  # 没人(已移除)不误伤
    ("周末Plog 在广州太古汇玩一天！", "很好逛很开心", "positive"),
    ("拾光五境·礼遇江至 太古汇15周年艺术装置", "精美展览", None),  # 中性/官方活动
    ("太古汇差不多逛完了", "记录日常", None),  # “差不多”不应误判负面
    ("太古汇假期活动预告", "黑色主题装置很好看", None),  # 假期/黑色不误伤
    ("贵州风味美食节进驻太古汇", "", None),  # 贵州不误伤
    ("太古汇今日客流平稳", "品牌正常营业", None),
]
ok=0
for title,content,exp in cases:
    topics=A.extract_topics(title,content)
    s,score,reasons=A.analyze_sentiment(title,content,topics=topics,return_reasons=True)
    rl,rs=A.assess_risk(title,content,42,12)
    mark=""
    if exp is None:
        mark="(参考)"
    elif s==exp:
        mark="✓"; ok+=1
    else:
        mark=f"✗ 期望{exp}"
    print(f'[{s:8} {score:+.2f} 风险{rl}{rs:>3}] {mark} {title[:28]} | 话题{topics[:3]} | {reasons[:3]}')
print(f'\n明确期望命中 {ok}/7')
