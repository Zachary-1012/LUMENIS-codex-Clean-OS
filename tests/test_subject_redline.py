# -*- coding: utf-8 -*-
"""主体红线专项断言：确认广州太古汇主体口径未被弱化（每次回归必跑）。"""
import io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subject_rules as sr

n_pass = 0
def check(name, cond):
    global n_pass
    assert cond, 'FAIL: ' + name
    n_pass += 1
    print('PASS', name)

check('主体词表非空且含核心词', len(sr.SUBJECT_WORDS) >= 15 and '广州太古汇' in sr.SUBJECT_WORDS and '太古汇' in sr.SUBJECT_WORDS)
check('排除词表非空且含外地太古汇', len(sr.SUBJECT_EXCLUDE_WORDS) >= 15 and '上海太古汇' in sr.SUBJECT_EXCLUDE_WORDS and '三里屯太古汇' in sr.SUBJECT_EXCLUDE_WORDS)
check('正例-15周年活动命中', sr.subject_hit(title='广州太古汇15周年庆典活动') is True)
check('正例-新店打卡命中', sr.subject_hit(body='太古汇新店开业探店') is True)
check('负例-无关内容不命中', sr.subject_hit(title='今天天气不错去公园散步') is False)
check('排除-上海太古汇一票否决', sr.subject_hit(title='上海太古汇逛街攻略') is False)
check('排除-三里屯一票否决', sr.subject_hit(title='三里屯太古汇美食') is False)
check('排除优先于正向(同时含两地)', sr.subject_hit(title='广州太古汇和上海太古汇对比') is False)
check('note字典接口一致', sr.subject_hit_note({'title':'太古汇停车场收费','body':''}) is True)
sql, values = sr._subject_sql_and_values('n')
check('SQL含正向与AND NOT', ' OR ' in sql and 'AND NOT' in sql and 'n.title' in sql)
check('SQL参数数=字段×(正向+排除)', len(values) == len(sr.SUBJECT_FIELDS)*(len(sr.SUBJECT_WORDS)+len(sr.SUBJECT_EXCLUDE_WORDS)))
check('SQL参数全部小写like', all(v.startswith('%') and v == v.lower() for v in values))
# —— V1.0 基线补齐：其他城市太古汇 / 品牌词无主体 / 五字段组合（只加断言，不改生产逻辑）——
for city in ['成都远洋太古汇逛街', '北京太古汇打卡', '深圳太古汇攻略', '香港太古汇', '兴业太古汇']:
    check('排除-其他城市:' + city, sr.subject_hit(title=city) is False)
check('品牌词无主体不命中', sr.subject_hit(title='lululemon 秋季新品上新', body='瑜伽裤测评') is False)
check('正文命中title无关', sr.subject_hit(title='周末随手拍', body='去了广州太古汇看展') is True)
check('matched_keywords命中', sr.subject_hit(matched_keywords='太古汇15周年') is True)
check('source_keyword命中', sr.subject_hit(source_keyword='广州太古汇') is True)
check('content字段命中', sr.subject_hit(content='太古汇停车场指引') is True)
check('title正向body外地仍否决', sr.subject_hit(title='广州太古汇', body='不如上海太古汇') is False)
check('空内容返回False', sr.subject_hit() is False)
print(f'\n主体红线断言: {n_pass} 项全部通过 SUBJECT_REDLINE_OK')
