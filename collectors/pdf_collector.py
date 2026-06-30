"""PDF 附件采集器。

第一版只处理文本型 PDF：
- 优先使用 pdfplumber 的 extract_tables()
- 如果没有标准表格，则使用 extract_text() 做弱结构化兜底
- 采集结果只写入 raw_admission_records，默认 status=pending
"""

import re
from pathlib import Path

from collectors.common import load_field_mapping, load_parser_config, mark_duplicate_records
from collectors.file_download import download_file
from collectors.html_table_collector import (
    DEFAULT_HEADER_MAPPING,
    _append_sample,
    _build_headers_from_config,
    _build_message,
    _make_sample,
    _normalize_mapping_keys,
    _process_normal_row,
    _process_wide_row,
    _result,
    _safe_int_config,
    _safe_int_list_config,
    _safe_list_config,
    clean_cell_text,
    detect_header_row,
)
from db import create_connection


def _update_download_status(source_id: int, download_result: dict) -> None:
    conn = create_connection()
    try:
        conn.execute(
            """
            UPDATE raw_data_sources
            SET local_file_path = ?,
                file_size = ?,
                file_download_status = ?,
                file_download_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                download_result.get("local_file_path"),
                download_result.get("file_size"),
                download_result.get("status"),
                download_result.get("message"),
                source_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def parse_pdf_text_lines_to_rows(text: str) -> list[list[str]]:
    """将 PDF 文本行弱结构化为二维 rows。

    这是兜底方案，只保留疑似招生录取相关文本行，并按连续空白切分。
    图片扫描 PDF 不在第一版支持范围内。
    """
    rows: list[list[str]] = []
    keywords = ["专业", "最低分", "位次", "录取分数"]

    for line in (text or "").splitlines():
        line = clean_cell_text(line)
        if not line:
            continue
        if not any(keyword in line for keyword in keywords):
            continue

        if "\t" in line or re.search(r"\s{2,}", line):
            cells = [clean_cell_text(item) for item in re.split(r"\t+|\s{2,}", line)]
        else:
            cells = [line]

        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)

    return rows


def _safe_page_indexes(config: dict, total_pages: int) -> list[int]:
    page_indexes = _safe_int_list_config(config, "page_indexes")
    if not page_indexes:
        return list(range(total_pages))
    return [index for index in page_indexes if 0 <= index < total_pages]


def _normalize_pdf_table(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table or []:
        cells = [clean_cell_text(cell) for cell in (row or [])]
        if any(cells):
            rows.append(cells)
    return rows


def _extract_pdf_rows(local_file_path: str, config: dict) -> tuple[list[list[str]], bool, str]:
    try:
        import pdfplumber
    except ImportError as exc:
        return [], False, f"缺少依赖 pdfplumber，请先安装：pip install pdfplumber。错误：{exc}"

    all_tables: list[list[list[str]]] = []
    text_chunks: list[str] = []

    with pdfplumber.open(local_file_path) as pdf:
        page_indexes = _safe_page_indexes(config, len(pdf.pages))
        for page_index in page_indexes:
            page = pdf.pages[page_index]

            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []

            for table in tables:
                normalized_table = _normalize_pdf_table(table)
                if normalized_table:
                    all_tables.append(normalized_table)

            if not all_tables:
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text:
                    text_chunks.append(text)

    if all_tables:
        configured_table_index = config.get("table_index")
        if configured_table_index is not None:
            table_index = _safe_int_config(config, "table_index", 0)
            if table_index >= len(all_tables):
                return [], False, f"table_index={table_index} 超出范围，PDF 仅提取到 {len(all_tables)} 个表格"
            return all_tables[table_index], False, f"已从 PDF 提取标准表格，table_index={table_index}"

        merged_rows: list[list[str]] = []
        for table in all_tables:
            merged_rows.extend(table)
        return merged_rows, False, f"已从 PDF 提取标准表格，共 {len(all_tables)} 个表格"

    weak_rows = parse_pdf_text_lines_to_rows("\n".join(text_chunks))
    if weak_rows:
        return weak_rows, True, "未提取到标准表格，已使用文本行弱解析，需人工核验"

    return [], False, "PDF 未提取到标准表格或可用文本行；如果是图片扫描 PDF，当前版本暂不支持 OCR"


def _parse_pdf_grid(
    source: dict,
    grid: list[list[str]],
    preview: bool,
    weak_parse: bool,
    extract_message: str,
    file_path: str,
) -> dict:
    config = load_parser_config(source)
    table_index = _safe_int_config(config, "table_index", 0)
    fallback_header_row_index = _safe_int_config(config, "header_row_index", 0)
    skip_rows = _safe_int_config(config, "skip_rows", 0)
    fill_down_fields = _safe_list_config(config, "fill_down_fields")
    major_filter_keywords = _safe_list_config(config, "major_filter_keywords")
    header_keywords = _safe_list_config(config, "header_keywords")
    header_min_match_count = _safe_int_config(config, "header_min_match_count", 3)
    auto_detect_header = bool(config.get("auto_detect_header", False))
    auto_direction_tags = bool(config.get("auto_direction_tags", False))
    transform_type = config.get("transform_type")
    wide_subject_config = config.get("wide_subject_config", {})
    if not isinstance(wide_subject_config, dict):
        wide_subject_config = {}
    default_values = config.get("default_values", {})
    if not isinstance(default_values, dict):
        default_values = {}

    result = _result(source=source, table_index=table_index, preview=preview)
    result["parser_type"] = "pdf"
    result["file_path"] = file_path
    result["weak_parse"] = weak_parse

    custom_mapping = load_field_mapping(source)
    mapping = _normalize_mapping_keys(custom_mapping or DEFAULT_HEADER_MAPPING)

    if not grid:
        result["error_count"] = 1
        result["message"] = extract_message or "PDF 中没有可解析行"
        return result

    auto_detected_header_row_index = None
    header_row_index = fallback_header_row_index
    if auto_detect_header:
        auto_detected_header_row_index = detect_header_row(
            grid=grid,
            header_keywords=header_keywords,
            min_match_count=header_min_match_count,
        )
        if auto_detected_header_row_index is not None:
            header_row_index = auto_detected_header_row_index

    if header_row_index >= len(grid):
        result["error_count"] = 1
        result["message"] = f"header_row_index={header_row_index} 超出范围，PDF rows 仅有 {len(grid)} 行"
        return result

    headers, effective_header_row_index = _build_headers_from_config(
        grid=grid,
        config=config,
        fallback_index=header_row_index,
    )
    header_row_index = effective_header_row_index
    result["header_row_index"] = header_row_index
    result["auto_detected_header_row_index"] = auto_detected_header_row_index
    result["detected_headers"] = headers
    if not headers:
        result["error_count"] = 1
        result["message"] = "PDF 表头为空，无法解析字段"
        return result

    header_row_indexes = _safe_int_list_config(config, "header_row_indexes")
    if header_row_indexes:
        data_start_index = max(header_row_indexes) + 1 + skip_rows
    else:
        data_start_index = header_row_index + 1 + skip_rows

    data_rows = grid[data_start_index:]
    result["total_data_rows"] = len(data_rows)
    last_fill_down_values: dict = {}

    conn = create_connection()
    try:
        for raw_cells in data_rows:
            if not any(clean_cell_text(cell) for cell in raw_cells):
                result["empty_row_skipped_count"] += 1
                result["skipped_count"] += 1
                _append_sample(result, _make_sample(raw_cells, {}, False, "empty_row"))
                continue

            try:
                if transform_type == "wide_subject_scores":
                    _process_wide_row(
                        conn=conn,
                        result=result,
                        source=source,
                        raw_cells=raw_cells,
                        headers=headers,
                        default_values=default_values,
                        auto_direction_tags=auto_direction_tags,
                        major_filter_keywords=major_filter_keywords,
                        preview=preview,
                        wide_config=wide_subject_config,
                    )
                else:
                    _process_normal_row(
                        conn=conn,
                        result=result,
                        source=source,
                        raw_cells=raw_cells,
                        headers=headers,
                        mapping=mapping,
                        fill_down_fields=fill_down_fields,
                        last_fill_down_values=last_fill_down_values,
                        default_values=default_values,
                        auto_direction_tags=auto_direction_tags,
                        major_filter_keywords=major_filter_keywords,
                        preview=preview,
                    )
            except Exception as exc:
                result["error_count"] += 1
                _append_sample(result, _make_sample(raw_cells, {}, False, f"error: {exc}"))

        if not preview:
            mark_duplicate_records(conn)
            conn.commit()
    finally:
        conn.close()

    if preview:
        result["inserted_count"] = 0

    result["message"] = f"{extract_message}；{_build_message(result)}"
    return result


def collect_pdf_source(source: dict, preview: bool = False) -> dict:
    """预览或采集 PDF 数据源。"""
    download_result = download_file(source["url"])
    _update_download_status(source["id"], download_result)

    if download_result.get("status") != "success":
        result = _result(source=source, table_index=0, preview=preview, message=download_result.get("message"))
        result["parser_type"] = "pdf"
        result["file_path"] = download_result.get("local_file_path")
        result["error_count"] = 1
        return result

    local_file_path = download_result["local_file_path"]
    if Path(local_file_path).suffix.lower() != ".pdf":
        result = _result(
            source=source,
            table_index=0,
            preview=preview,
            message=f"不支持的 PDF 数据源文件类型：{Path(local_file_path).suffix}",
        )
        result["parser_type"] = "pdf"
        result["file_path"] = local_file_path
        result["error_count"] = 1
        return result

    config = load_parser_config(source)
    grid, weak_parse, extract_message = _extract_pdf_rows(local_file_path, config)
    return _parse_pdf_grid(
        source=source,
        grid=grid,
        preview=preview,
        weak_parse=weak_parse,
        extract_message=extract_message,
        file_path=local_file_path,
    )
