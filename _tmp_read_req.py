"""临时：读取 WPS 云盘需求 docx 并输出到 txt"""
import zipfile, xml.etree.ElementTree as ET, os

candidates = [
    r'D:\wps云空间\WPS Cloud\WPSDrive\280397037\WPS云盘\gpt研发，tare代码运行测试.docx',
    r'D:\WPS云盘\gpt研发，tare代码运行测试.docx',
    r'D:\wps云盘\gpt研发，tare代码运行测试.docx',
]

# 全盘搜索
search_roots = [r'D:\wps云空间', r'D:\WPS云盘', r'D:\wps云盘', r'D:']

def find_docx():
    for p in candidates:
        if os.path.exists(p):
            return p
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                if 'gpt' in f.lower() and 'trae' in f.lower() and f.endswith('.docx'):
                    return os.path.join(dirpath, f)
                if 'gpt' in f.lower() and '代码运行测试' in f and f.endswith('.docx'):
                    return os.path.join(dirpath, f)
    return None

docx_path = find_docx()
out_lines = []
if not docx_path:
    out_lines.append('[ERROR] 未找到需求文档，请确认路径正确')
    # 列出所有找到的 docx
    for root in [r'D:\wps云空间', r'D:\WPS云盘', r'D:\wps云盘']:
        if os.path.isdir(root):
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    if f.endswith('.docx'):
                        out_lines.append(f'  [FOUND] {os.path.join(dirpath, f)}')
else:
    out_lines.append(f'[OK] 找到文档: {docx_path}')
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(docx_path, 'r') as z:
        with z.open('word/document.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            out_lines.append('\n=== 文档段落内容 ===')
            paragraphs = root.findall('.//w:p', ns)
            for i, p in enumerate(paragraphs):
                texts = p.findall('.//w:t', ns)
                content = ''.join([t.text for t in texts if t.text])
                if content.strip():
                    out_lines.append(f'[{i}] {content}')
            out_lines.append('\n=== 表格内容 ===')
            tables = root.findall('.//w:tbl', ns)
            for t_idx, table in enumerate(tables):
                out_lines.append(f'\n--- 表格 {t_idx+1} ---')
                rows = table.findall('.//w:tr', ns)
                for r_idx, row in enumerate(rows):
                    cells = row.findall('.//w:tc', ns)
                    cell_texts = []
                    for cell in cells:
                        texts = cell.findall('.//w:t', ns)
                        cell_text = ''.join([t.text for t in texts if t.text])
                        cell_texts.append(cell_text.strip())
                    out_lines.append(f'  行{r_idx}: {" | ".join(cell_texts)}')

output = '\n'.join(out_lines)
print(output)
with open(r'd:\Taikoo-monitor-new\_tmp_requirements_output.txt', 'w', encoding='utf-8') as f:
    f.write(output)
print(f'\n[DONE] 已保存到 _tmp_requirements_output.txt')
