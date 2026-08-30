# -*- coding: utf-8 -*-
"""读取V3.0文档完整内容"""
import docx

path = r'D:\wps云空间\WPS Cloud\WPSDrive\280397037\WPS云盘\Z-Brand-Core_全局代码级基线_V3.0_豆包执行版.docx'
doc = docx.Document(path)

print(f'段落数: {len(doc.paragraphs)}')
print(f'表格数: {len(doc.tables)}')
print('='*70)

for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if not text:
        continue
    style = para.style.name if para.style else ''
    if 'Heading' in style or '标题' in style:
        print(f'\n## [{style}] {text}')
    else:
        print(text)
