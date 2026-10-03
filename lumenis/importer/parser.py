"""
文件解析器
支持 PDF / Word(DOCX) / Excel(XLSX) / CSV / TXT
不依赖重型库，优先用标准库+可选依赖
"""
import os
import re
import hashlib
from typing import List, Dict
from ..config import IMPORTER_CONFIG


class ParseResult:
    """解析结果"""
    def __init__(self):
        self.text: str = ""
        self.tables: List[List[List[str]]] = []  # 表格数据
        self.metadata: Dict = {}
        self.paragraphs: List[str] = []
        self.locators: List[Dict] = []


def parse_file(file_path: str) -> ParseResult:
    """
    根据文件扩展名自动选择解析器
    返回 ParseResult
    """
    if not isinstance(file_path, str) or not file_path.strip() or "://" in file_path:
        raise ValueError("LOCAL_DOCUMENT_REQUIRED")
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    if os.path.getsize(file_path) > IMPORTER_CONFIG["max_file_size_mb"] * 1024 * 1024:
        raise ValueError("DOCUMENT_TOO_LARGE")
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        result = parse_pdf(file_path)
    elif ext == ".docx":
        result = parse_word(file_path)
    elif ext == ".doc":
        result = parse_legacy_word(file_path)
    elif ext == ".xlsx":
        result = parse_excel(file_path)
    elif ext == ".xls":
        result = parse_legacy_excel(file_path)
    elif ext == ".csv":
        result = parse_csv(file_path)
    elif ext == ".txt":
        result = parse_txt(file_path)
    elif ext in (".pptx", ".html", ".htm"):
        result = parse_markitdown(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
    digest = hashlib.sha256()
    with open(file_path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    result.metadata.update(source_name=os.path.basename(file_path),
                           source_fingerprint=digest.hexdigest(), network_mode="local_only")
    # Offsets refer to the exact retained parsed text, not guessed PDF pages or
    # source-byte positions. Keep repeated paragraphs independently locatable.
    if not result.locators:
        offset = 0
        for index, line in enumerate(result.text.splitlines(keepends=True), 1):
            text = line.rstrip("\r\n")
            if text.strip():
                result.locators.append({"unit": "parsed_line", "index": index,
                                        "start": offset, "end": offset + len(text)})
            offset += len(line)
    result.metadata["parsed_text_sha256"] = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
    return result


def parse_markitdown(file_path: str) -> ParseResult:
    """Convert one bounded local document through optional MarkItDown.

    MarkItDown is an importer implementation, not a source, Evidence or
    Canonical owner.  It is deliberately lazy and local-only: a missing
    optional dependency is reported honestly and remote URI inputs are never
    handed to a third-party converter.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("文档路径为空")
    local_path = os.path.abspath(file_path)
    if not os.path.isfile(local_path):
        raise FileNotFoundError(local_path)
    if os.path.getsize(local_path) > IMPORTER_CONFIG["max_file_size_mb"] * 1024 * 1024:
        raise ValueError(f"文件超过{IMPORTER_CONFIG['max_file_size_mb']}MB")

    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise ImportError(
            "PPTX/HTML 解析需要可选依赖 markitdown；请按 requirements.txt 安装后重试"
        ) from exc

    result = ParseResult()
    result.metadata.update({
        "format": os.path.splitext(local_path)[1].lstrip(".").lower(),
        "parser": "markitdown",
        "network_mode": "local_only",
        "source_name": os.path.basename(local_path),
    })
    digest = hashlib.sha256()
    with open(local_path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    result.metadata["source_fingerprint"] = digest.hexdigest()

    converter = MarkItDown(enable_plugins=False)
    convert_local = getattr(converter, "convert_local", None)
    converted = convert_local(local_path) if callable(convert_local) else converter.convert(local_path)
    markdown = getattr(converted, "markdown", None)
    if markdown is None:
        markdown = getattr(converted, "text_content", None)
    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError("MarkItDown 未返回可用文本")
    result.text = markdown
    result.paragraphs = [line.strip() for line in markdown.splitlines() if line.strip()]
    version = getattr(__import__("markitdown"), "__version__", None)
    if version is None:
        from importlib.metadata import version as distribution_version
        version = distribution_version("markitdown")
    result.metadata["parser_version"] = str(version)
    return result


def parse_txt(file_path: str) -> ParseResult:
    """纯文本解析"""
    result = ParseResult()
    result.metadata["format"] = "txt"
    with open(file_path, "r", encoding="utf-8-sig") as f:
        result.text = f.read()
    result.paragraphs = [p.strip() for p in result.text.split("\n") if p.strip()]
    return result


def parse_csv(file_path: str) -> ParseResult:
    """CSV解析"""
    import csv
    result = ParseResult()
    result.metadata["format"] = "csv"
    table = []
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            table.append(row)
    result.tables = [table]
    result.text = "\n".join([",".join(row) for row in table])
    result.paragraphs = [",".join(row) for row in table if any(cell.strip() for cell in row)]
    return result


def parse_pdf(file_path: str) -> ParseResult:
    """
    PDF解析
    优先用 pdfplumber，回退到 PyPDF2，都没有则报错提示安装
    """
    result = ParseResult()
    result.metadata["format"] = "pdf"
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            result.metadata["pages"] = len(pdf.pages)
            all_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_text.append(text)
                # 提取表格
                tables = page.extract_tables()
                for t in tables:
                    result.tables.append(t)
            result.text = "\n\n".join(all_text)
            offset = 0
            for index, text in enumerate(all_text, 1):
                result.locators.append({"unit": "pdf_page", "index": index,
                                        "start": offset, "end": offset + len(text)})
                offset += len(text) + 2
            result.paragraphs = [p.strip() for p in result.text.split("\n") if p.strip()]
    except ImportError:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            result.metadata["pages"] = len(reader.pages)
            all_text = []
            for page in reader.pages:
                all_text.append(page.extract_text() or "")
            result.text = "\n\n".join(all_text)
            offset = 0
            for index, text in enumerate(all_text, 1):
                result.locators.append({"unit": "pdf_page", "index": index,
                                        "start": offset, "end": offset + len(text)})
                offset += len(text) + 2
            result.paragraphs = [p.strip() for p in result.text.split("\n") if p.strip()]
        except ImportError:
            raise ImportError("PDF解析需要 pdfplumber 或 PyPDF2，请运行: pip install pdfplumber")
    return result


def parse_word(file_path: str) -> ParseResult:
    """
    Word DOCX 解析
    需要 python-docx
    """
    result = ParseResult()
    result.metadata["format"] = "word"
    try:
        from docx import Document
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        doc = Document(file_path)
        all_text = []
        offset, paragraph_index, table_index = 0, 0, 0
        for element in doc.element.body:
            if element.tag.endswith("}p"):
                paragraph_index += 1
                text = Paragraph(element, doc).text
                if text.strip():
                    if all_text:
                        offset += 2
                    result.locators.append({"unit": "word_paragraph", "index": paragraph_index,
                                            "start": offset, "end": offset + len(text)})
                    all_text.append(text)
                    result.paragraphs.append(text)
                    offset += len(text)
            elif element.tag.endswith("}tbl"):
                table_index += 1
                rows = [[cell.text for cell in row.cells] for row in Table(element, doc).rows]
                result.tables.append(rows)
                for row_index, cells in enumerate(rows, 1):
                    text = " | ".join(cells)
                    if all_text:
                        offset += 2
                    cell_offset = offset
                    for column, cell in enumerate(cells, 1):
                        if cell:
                            result.locators.append({"unit": "word_table_cell", "table": table_index,
                                                    "row": row_index, "column": column,
                                                    "start": cell_offset, "end": cell_offset + len(cell)})
                        cell_offset += len(cell) + 3
                    all_text.append(text)
                    offset += len(text)
        result.text = "\n\n".join(all_text)
    except ImportError:
        raise ImportError("Word解析需要 python-docx，请运行: pip install python-docx")
    return result


def parse_excel(file_path: str) -> ParseResult:
    """
    Excel XLSX 解析
    需要 openpyxl 或 pandas
    """
    result = ParseResult()
    result.metadata["format"] = "excel"
    try:
        import openpyxl
        # Retain formula expressions as source statements. A missing cached
        # calculation is never silently converted to a blank or zero.
        wb = openpyxl.load_workbook(file_path, data_only=False, read_only=True, keep_links=False)
        result.metadata["sheets"] = wb.sheetnames
        all_text = []
        offset = 0
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            table = []
            for row_index, row in enumerate(ws.iter_rows(values_only=True), 1):
                row_data = [str(cell) if cell is not None else "" for cell in row]
                if any(cell.strip() for cell in row_data):
                    table.append(row_data)
                    text = " | ".join(row_data)
                    if all_text:
                        offset += 1
                    cell_offset = offset
                    for column, cell in enumerate(row_data, 1):
                        if cell:
                            result.locators.append({"unit": "spreadsheet_cell", "sheet": sheet_name,
                                                    "row": row_index, "column": column,
                                                    "start": cell_offset, "end": cell_offset + len(cell)})
                        cell_offset += len(cell) + 3
                    all_text.append(text)
                    offset += len(text)
            result.tables.append(table)
        result.text = "\n".join(all_text)
        result.paragraphs = all_text
        wb.close()
    except ImportError:
        try:
            import pandas as pd
            xls = pd.ExcelFile(file_path)
            result.metadata["sheets"] = xls.sheet_names
            all_text = []
            for sheet in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                result.tables.append(df.values.tolist())
                all_text.append(df.to_string())
            result.text = "\n\n".join(all_text)
            result.paragraphs = all_text
        except ImportError:
            raise ImportError("Excel解析需要 openpyxl 或 pandas，请运行: pip install openpyxl")
    return result


def parse_legacy_word(file_path: str) -> ParseResult:
    """Convert binary Word with a private, inert local LibreOffice profile.

    Original bytes remain the canonical Source input. Converted paragraph/cell
    offsets refer to retained text, not original layout/pages. Runtime packaging
    and decoder isolation remain W6 responsibilities for production use.
    """
    import shutil
    import signal
    import subprocess
    import tempfile
    from pathlib import Path
    executable = shutil.which("soffice")
    if executable is None:
        raise ImportError("二进制 DOC 解析需要本地 LibreOffice；不能用 DOCX 解析器替代")
    executable = str(Path(executable).resolve())
    configuration = '''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting">
<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>
<prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop>
</item>
<item oor:path="/org.openoffice.Office.Writer/Content/Update">
<prop oor:name="Link" oor:op="fuse"><value>2</value></prop>
<prop oor:name="Field" oor:op="fuse"><value>false</value></prop>
</item></oor:items>'''
    with tempfile.TemporaryDirectory(prefix="lumenis-doc-decode-") as directory:
        work = Path(directory)
        profile = work / "profile"
        (profile / "user").mkdir(parents=True)
        (profile / "user" / "registrymodifications.xcu").write_text(configuration, encoding="utf-8")
        # The decoder receives only its public runtime configuration, never
        # caller credentials, private environment variables or a user profile.
        environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "TMPDIR": str(work)}
        version = subprocess.run([executable, "-env:UserInstallation=" + profile.as_uri(), "--version"],
                                 capture_output=True, text=True, env=environment, timeout=5, check=False)
        parser_version = version.stdout.strip()[:200] if version.returncode == 0 else "not_reported"
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            process = subprocess.Popen([executable, "-env:UserInstallation=" + profile.as_uri(),
                                        "--headless", "--convert-to", "docx:Office Open XML Text",
                                        "--outdir", str(work), os.path.abspath(file_path)],
                                       stdout=output, stderr=errors, env=environment,
                                       start_new_session=(os.name == "posix"))
            try:
                returncode = process.wait(timeout=30)
            except subprocess.TimeoutExpired as exc:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
                raise ValueError("LEGACY_DOC_CONVERSION_TIMEOUT") from exc
        converted = work / (Path(file_path).stem + ".docx")
        if returncode != 0 or not converted.is_file():
            raise ValueError("LEGACY_DOC_CONVERSION_FAILED")
        if not 0 < converted.stat().st_size <= 8 * 1024 * 1024:
            raise ValueError("LEGACY_DOC_CONVERSION_SIZE_INVALID")
        converted_sha = hashlib.sha256(converted.read_bytes()).hexdigest()
        result = parse_word(str(converted))
    for locator in result.locators:
        locator["unit"] = "converted_" + locator["unit"]
    result.metadata.update(format="doc", parser="libreoffice", parser_version=parser_version,
                           intermediate_docx_sha256=converted_sha,
                           intermediate_state="transient_conversion_not_committed_artifact",
                           conversion_mode="local_doc_to_docx", positions="retained_converted_text",
                           embedded_macros="disabled_by_ephemeral_profile",
                           external_links="updates_disabled_by_ephemeral_profile",
                           active_content="disabled_by_ephemeral_profile")
    return result


def parse_legacy_excel(file_path: str) -> ParseResult:
    """Read binary XLS locally; preserve original bytes and cached-value limits.

    xlrd does not expose formula expressions. Values are statements retained in
    the input workbook, never a claim that a formula was freshly calculated.
    Exact source cell coordinates remain available alongside the raw archive.
    """
    try:
        import xlrd
    except ImportError as exc:
        raise ImportError("XLS解析需要可选依赖 xlrd；不能用 XLSX 解析器替代") from exc
    result = ParseResult()
    workbook = xlrd.open_workbook(file_path, on_demand=True)
    result.metadata.update(format="xls", parser="xlrd", parser_version=xlrd.__version__,
                           sheets=workbook.sheet_names(),
                           calculation_state="retained_cached_values_not_recalculated",
                           formula_expressions="not_exposed_by_xlrd")
    lines, offset = [], 0
    try:
        for sheet_name in workbook.sheet_names():
            sheet = workbook.sheet_by_name(sheet_name)
            table = []
            for row_index in range(sheet.nrows):
                cells = []
                for column in range(sheet.ncols):
                    cell = sheet.cell(row_index, column)
                    if cell.ctype in {xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK}:
                        value = ""
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        value = "True" if cell.value else "False"
                    elif cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate_as_datetime(cell.value, workbook.datemode).isoformat()
                    elif cell.ctype == xlrd.XL_CELL_ERROR:
                        value = xlrd.error_text_from_code.get(cell.value, "#UNKNOWN_ERROR")
                    elif cell.ctype == xlrd.XL_CELL_NUMBER and float(cell.value).is_integer():
                        value = str(int(cell.value))
                    else:
                        value = str(cell.value)
                    cells.append(value)
                if not any(value.strip() for value in cells):
                    continue
                table.append(cells)
                text = " | ".join(cells)
                if lines:
                    offset += 1
                cell_offset = offset
                for column, value in enumerate(cells, 1):
                    if value:
                        result.locators.append({"unit": "spreadsheet_cell", "sheet": sheet_name,
                                                "row": row_index + 1, "column": column,
                                                "start": cell_offset, "end": cell_offset + len(value)})
                    cell_offset += len(value) + 3
                lines.append(text)
                offset += len(text)
            result.tables.append(table)
        result.text = "\n".join(lines)
        result.paragraphs = lines
    finally:
        workbook.release_resources()
    return result


def split_into_chunks(text: str, max_chunk_size: int = 500) -> List[str]:
    """将长文本切分成适合AI分析的块"""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) > max_chunk_size and current:
            chunks.append(current.strip())
            current = p
        else:
            current += "\n" + p
    if current.strip():
        chunks.append(current.strip())
    return chunks
