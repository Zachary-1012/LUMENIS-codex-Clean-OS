"""读取公关话术模版docx文件"""
import zipfile
import xml.etree.ElementTree as ET

docx_path = '公关话术模版-舆情信息.docx'

with zipfile.ZipFile(docx_path, 'r') as z:
    with z.open('word/document.xml') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        print("=== 文档段落内容 ===")
        paragraphs = root.findall('.//w:p', ns)
        for i, p in enumerate(paragraphs):
            texts = p.findall('.//w:t', ns)
            content = ''.join([t.text for t in texts if t.text])
            if content.strip():
                print(f"[{i}] {content}")
        
        print("\n=== 表格内容 ===")
        tables = root.findall('.//w:tbl', ns)
        for t_idx, table in enumerate(tables):
            print(f"\n--- 表格 {t_idx+1} ---")
            rows = table.findall('.//w:tr', ns)
            for r_idx, row in enumerate(rows):
                cells = row.findall('.//w:tc', ns)
                cell_texts = []
                for cell in cells:
                    texts = cell.findall('.//w:t', ns)
                    cell_text = ''.join([t.text for t in texts if t.text])
                    cell_texts.append(cell_text.strip())
                print(f"  行{r_idx}: {' | '.join(cell_texts)}")
