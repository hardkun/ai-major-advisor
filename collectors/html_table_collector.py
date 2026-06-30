"""HTML table 数据采集器。

支持：
- rowspan / colspan 表格展开
- field_mapping_json 字段映射
- parser_config_json 中的 table_index / header_row_index / skip_rows
- auto_detect_header / header_keywords / header_min_match_count
- header_row_indexes 多行表头合成
- manual_headers 手工指定表头
- transform_type=wide_subject_scores 宽表拆成物理类/历史类标准记录
- fill_down_fields 向下填充
- major_filter_keywords 专业关键词过滤
- auto_direction_tags 自动方向标签
- preview 模式：只解析和预估，不写入 raw_admission_records

正式采集结果只写入 raw_admission_records，默认 status=pending；
人工核验通过后，才会进入正式 admissions 表。
"""

import re
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from collectors.common import (
    apply_default_values,
    apply_field_mapping,
    create_raw_record_from_dict,
    load_field_mapping,
    load_parser_config,
    mark_duplicate_records,
)
from db import create_connection


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
)

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


DEFAULT_HEADER_MAPPING = {
    "学校": "school_name",
    "院校": "school_name",
    "院校名称": "school_name",
    "学校名称": "school_name",
    "院校代码": "school_code",
    "学校代码": "school_code",
    "所在省份": "school_province",
    "院校省份": "school_province",
    "城市": "city",
    "院校层次": "school_level",
    "院校标签": "school_tags",
    "专业": "major_name",
    "专业名称": "major_name",
    "录取专业": "major_name",
    "专业代码": "major_code",
    "专业类别": "major_category",
    "方向标签": "direction_tags",
    "专业方向": "direction_tags",
    "专业描述": "major_description",
    "就业方向": "career_paths",
    "年份": "admission_year",
    "年度": "admission_year",
    "省份": "admission_province",
    "省市名称": "admission_province",
    "招生省份": "admission_province",
    "科类": "subject_type",
    "首选科目": "subject_type",
    "批次": "batch",
    "录取批次": "batch",
    "专业组": "major_group_code",
    "院校专业组": "major_group_code",
    "专业组代码": "major_group_code",
    "选科": "elective_requirement",
    "选科要求": "elective_requirement",
    "最高分": "max_score",
    "平均分": "avg_score",
    "最低分": "min_score",
    "最低位次": "min_rank",
    "位次": "min_rank",
    "计划数": "plan_count",
    "招生人数": "plan_count",
    "录取人数": "plan_count",
    "学费": "tuition",
    "校区": "campus",
    "数据来源": "source_name",
    "来源链接": "source_url",
    "原始文本": "raw_text",
}


SYSTEM_FIELDS = [
    "school_name",
    "school_code",
    "school_province",
    "city",
    "school_level",
    "school_tags",
    "major_name",
    "major_code",
    "major_category",
    "direction_tags",
    "major_description",
    "career_paths",
    "admission_year",
    "admission_province",
    "subject_type",
    "batch",
    "major_group_code",
    "elective_requirement",
    "min_score",
    "min_rank",
    "plan_count",
    "tuition",
    "campus",
    "source_name",
    "source_url",
    "raw_text",
]


def _download_html(url: str) -> str:
    request = Request(url, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=20) as response:
        content = response.read()
        charset = response.headers.get_content_charset()

    for encoding in [charset, "utf-8", "utf-8-sig", "gb18030", "gbk"]:
        if not encoding:
            continue
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def clean_cell_text(value) -> str:
    """清洗单元格文本：去首尾空白，合并换行/制表符/连续空白，去掉 NBSP。"""
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _cell_text(cell) -> str:
    return clean_cell_text(cell.get_text(" ", strip=True))


def normalize_header(text: str) -> str:
    """归一化表头：去掉所有空白字符，包括空格、换行、制表符和 NBSP。"""
    if text is None:
        return ""
    return re.sub(r"[\s\xa0]+", "", str(text))


def _normalize_mapping_keys(mapping: dict) -> dict:
    return {normalize_header(str(key)): value for key, value in mapping.items()}


def _build_raw_text(row_values: list[str]) -> str:
    return " | ".join(value for value in row_values if value)


def _safe_int_config(config: dict, key: str, default: int) -> int:
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(value, 0)


def _safe_list_config(config: dict, key: str) -> list[str]:
    value = config.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _safe_int_list_config(config: dict, key: str) -> list[int]:
    value = config.get(key, [])
    if not isinstance(value, list):
        return []

    result = []
    for item in value:
        try:
            parsed = int(item)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            result.append(parsed)
    return result


def _is_empty(value) -> bool:
    return value is None or str(value).strip() == ""


def _to_int(value) -> int | None:
    if _is_empty(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _result(source: dict, table_index: int, preview: bool, message: str = "") -> dict:
    return {
        "source_id": source["id"],
        "source_name": source.get("name"),
        "parser_type": source.get("parser_type"),
        "preview": preview,
        "table_index": table_index,
        "header_row_index": None,
        "auto_detected_header_row_index": None,
        "detected_headers": [],
        "sample_rows": [],
        "total_data_rows": 0,
        "would_insert_count": 0,
        "inserted_count": 0,
        "skipped_count": 0,
        "duplicate_skipped_count": 0,
        "filter_skipped_count": 0,
        "empty_major_skipped_count": 0,
        "empty_row_skipped_count": 0,
        "error_count": 0,
        "message": message,
    }


def _parse_int_attr(value, default: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def parse_table_with_spans(table) -> list[list[str]]:
    """解析带 rowspan / colspan 的 HTML table，返回完整二维 grid。"""
    grid: list[list[str]] = []
    rowspan_values: dict[int, dict] = {}

    for tr in table.find_all("tr"):
        row: list[str] = []
        column_index = 0
        cells = tr.find_all(["td", "th"], recursive=False)
        if not cells:
            cells = tr.find_all(["td", "th"])

        def consume_rowspan_cells() -> None:
            nonlocal column_index
            while column_index in rowspan_values:
                item = rowspan_values[column_index]
                row.append(item["text"])
                item["rows_left"] -= 1
                if item["rows_left"] <= 0:
                    del rowspan_values[column_index]
                column_index += 1

        consume_rowspan_cells()
        for cell in cells:
            consume_rowspan_cells()

            text = _cell_text(cell)
            rowspan = _parse_int_attr(cell.get("rowspan", 1))
            colspan = _parse_int_attr(cell.get("colspan", 1))

            for _ in range(colspan):
                row.append(text)
                if rowspan > 1:
                    rowspan_values[column_index] = {
                        "text": text,
                        "rows_left": rowspan - 1,
                    }
                column_index += 1

        consume_rowspan_cells()
        if row:
            grid.append(row)

    return grid


def detect_header_row(
    grid: list[list[str]],
    header_keywords: list[str],
    min_match_count: int = 3,
) -> int | None:
    """根据关键词自动识别表头行。"""
    normalized_keywords = [
        normalize_header(keyword)
        for keyword in header_keywords
        if normalize_header(keyword)
    ]
    if not normalized_keywords:
        return None

    for index, row in enumerate(grid):
        normalized_cells = [normalize_header(cell) for cell in row]
        matched_keywords = set()
        for keyword in normalized_keywords:
            if any(keyword == cell or keyword in cell for cell in normalized_cells):
                matched_keywords.add(keyword)
        if len(matched_keywords) >= min_match_count:
            return index
    return None


def _auto_direction_tags(major_name: str | None) -> str | None:
    if not major_name:
        return None

    rules = [
        ("人工智能", "AI算法,大模型应用,Agent,计算机视觉"),
        ("计算机", "AI算法,大模型应用,Agent"),
        ("软件工程", "大模型应用,Agent,AI应用开发"),
        ("软件", "大模型应用,Agent,AI应用开发"),
        ("数据科学", "AI算法,数据智能,大模型应用"),
        ("大数据", "AI算法,数据智能,大模型应用"),
        ("智能科学", "AI算法,计算机视觉,智能系统"),
        ("网络工程", "AI安全,网络安全,AI应用开发"),
        ("信息安全", "AI安全,网络安全,AI应用开发"),
        ("网络空间安全", "AI安全,网络安全,AI应用开发"),
        ("电子信息", "边缘AI,计算机视觉,智能硬件"),
        ("电气工程", "智能制造,工业AI,自动化控制"),
        ("通信工程", "边缘AI,计算机视觉,智能硬件"),
        ("通信", "边缘AI,计算机视觉,智能硬件"),
        ("自动化", "机器人,智能制造,自动化控制,工业AI"),
        ("机器人工程", "机器人,智能制造,自动化控制"),
        ("机械电子", "智能制造,机器人,工业AI"),
        ("测控", "智能制造,机器人,工业AI"),
        ("微电子", "AI芯片,智能硬件,边缘AI"),
        ("集成电路", "AI芯片,智能硬件,边缘AI"),
        ("物联网", "边缘AI,智能硬件,AI应用开发"),
    ]

    for keyword, tags in rules:
        if keyword in major_name:
            return tags
    return None


def _major_matches_keywords(major_name: str | None, keywords: list[str]) -> bool:
    if not keywords:
        return True
    if not major_name:
        return False
    return any(keyword in major_name for keyword in keywords)


def _apply_fill_down(data: dict, fill_down_fields: list[str], last_values: dict) -> dict:
    updated = dict(data)
    for field in fill_down_fields:
        if _is_empty(updated.get(field)) and not _is_empty(last_values.get(field)):
            updated[field] = last_values[field]
        elif not _is_empty(updated.get(field)):
            last_values[field] = updated[field]
    return updated


def _raw_record_exists(conn, data: dict) -> bool:
    admission_year = _to_int(data.get("admission_year"))
    min_score = _to_int(data.get("min_score"))
    min_rank = _to_int(data.get("min_rank"))

    row = conn.execute(
        """
        SELECT id FROM raw_admission_records
        WHERE COALESCE(school_name, '') = COALESCE(?, '')
          AND COALESCE(major_name, '') = COALESCE(?, '')
          AND COALESCE(admission_year, -1) = COALESCE(?, -1)
          AND COALESCE(admission_province, '') = COALESCE(?, '')
          AND COALESCE(subject_type, '') = COALESCE(?, '')
          AND COALESCE(major_group_code, '') = COALESCE(?, '')
          AND COALESCE(major_code, '') = COALESCE(?, '')
          AND COALESCE(min_score, -1) = COALESCE(?, -1)
          AND COALESCE(min_rank, -1) = COALESCE(?, -1)
        LIMIT 1
        """,
        (
            data.get("school_name"),
            data.get("major_name"),
            admission_year,
            data.get("admission_province"),
            data.get("subject_type"),
            data.get("major_group_code"),
            data.get("major_code"),
            min_score,
            min_rank,
        ),
    ).fetchone()
    return row is not None


def _make_sample(
    raw_cells: list[str],
    mapped_data: dict,
    should_insert: bool,
    skip_reason: str,
    wide_mapped_data: dict | None = None,
    expanded_records: list[dict] | None = None,
) -> dict:
    sample = {
        "raw_cells": raw_cells,
        "mapped_data": mapped_data,
        "major_name": mapped_data.get("major_name"),
        "should_insert": should_insert,
        "skip_reason": skip_reason,
    }
    if wide_mapped_data is not None:
        sample["wide_mapped_data"] = wide_mapped_data
    if expanded_records is not None:
        sample["expanded_records"] = expanded_records
    return sample


def _append_sample(result: dict, sample: dict) -> None:
    if len(result["sample_rows"]) < 5:
        result["sample_rows"].append(sample)


def _build_message(result: dict) -> str:
    mode = "预览完成" if result.get("preview") else "采集完成"
    return (
        f"{mode}：table_index={result['table_index']}，"
        f"header_row_index={result['header_row_index']}，"
        f"auto_detected_header_row_index={result['auto_detected_header_row_index']}，"
        f"detected_headers={result['detected_headers']}，"
        f"total_data_rows={result['total_data_rows']}，"
        f"would_insert_count={result['would_insert_count']}，"
        f"inserted_count={result['inserted_count']}，"
        f"duplicate_skipped_count={result['duplicate_skipped_count']}，"
        f"filter_skipped_count={result['filter_skipped_count']}，"
        f"empty_major_skipped_count={result['empty_major_skipped_count']}，"
        f"empty_row_skipped_count={result['empty_row_skipped_count']}，"
        f"error_count={result['error_count']}"
    )


def _row_to_raw_mapping(raw_cells: list[str], headers: list[str]) -> dict:
    raw_row = {}
    for index, value in enumerate(raw_cells):
        if index >= len(headers):
            continue
        header = headers[index]
        if not header:
            continue
        raw_row[header] = value
    return raw_row


def _prepare_row_data(
    raw_cells: list[str],
    headers: list[str],
    mapping: dict,
    fill_down_fields: list[str],
    last_fill_down_values: dict,
    default_values: dict,
    auto_direction_tags: bool,
    source: dict,
) -> dict:
    raw_row = _row_to_raw_mapping(raw_cells, headers)
    mapped_row = apply_field_mapping(raw_row, mapping)
    data = {field: mapped_row.get(field) for field in SYSTEM_FIELDS}
    data = _apply_fill_down(
        data=data,
        fill_down_fields=fill_down_fields,
        last_values=last_fill_down_values,
    )
    return _finalize_record_data(
        data=data,
        default_values=default_values,
        auto_direction_tags=auto_direction_tags,
        source=source,
        raw_cells=raw_cells,
    )


def _finalize_record_data(
    data: dict,
    default_values: dict,
    auto_direction_tags: bool,
    source: dict,
    raw_cells: list[str],
) -> dict:
    data = apply_default_values(data, default_values)
    if auto_direction_tags and _is_empty(data.get("direction_tags")):
        data["direction_tags"] = _auto_direction_tags(data.get("major_name"))

    data["source_name"] = (
        data.get("source_name")
        or default_values.get("source_name")
        or source.get("name")
    )
    data["source_url"] = (
        data.get("source_url")
        or default_values.get("source_url")
        or source.get("url")
    )
    data["raw_text"] = data.get("raw_text") or _build_raw_text(raw_cells)
    return data


def _normalize_header_list(headers: list[str]) -> list[str]:
    return [normalize_header(header) for header in headers]


def _combine_header_parts(parts: list[str]) -> str:
    clean_parts = [normalize_header(part) for part in parts if normalize_header(part)]
    if not clean_parts:
        return ""
    unique_parts = []
    for part in clean_parts:
        if part not in unique_parts:
            unique_parts.append(part)

    if len(unique_parts) == 2:
        first, second = unique_parts
        if first == second:
            return first
        if first == "录取人数" and second in {"物理", "历史", "物理类", "历史类"}:
            return f"{second.replace('类', '')}录取人数"
        if first in {"物理", "历史", "物理类", "历史类"}:
            return f"{first.replace('类', '')}{second}"
    return "".join(unique_parts)


def _build_headers_from_config(grid: list[list[str]], config: dict, fallback_index: int) -> tuple[list[str], int]:
    manual_headers = config.get("manual_headers")
    if isinstance(manual_headers, list) and manual_headers:
        return _normalize_header_list([str(header) for header in manual_headers]), fallback_index

    header_row_indexes = _safe_int_list_config(config, "header_row_indexes")
    if header_row_indexes:
        max_columns = max(
            (len(grid[index]) for index in header_row_indexes if index < len(grid)),
            default=0,
        )
        headers = []
        for column_index in range(max_columns):
            parts = []
            for row_index in header_row_indexes:
                if row_index < len(grid) and column_index < len(grid[row_index]):
                    parts.append(grid[row_index][column_index])
            headers.append(_combine_header_parts(parts))
        return headers, max(header_row_indexes)

    return _normalize_header_list(grid[fallback_index]), fallback_index


def _get_wide_value(wide_mapped_data: dict, header_name: str | None):
    if header_name is None:
        return None
    return wide_mapped_data.get(normalize_header(header_name))


def _build_wide_records(
    wide_mapped_data: dict,
    wide_config: dict,
    raw_cells: list[str],
) -> list[dict]:
    base_fields = wide_config.get("base_fields", {})
    subjects = wide_config.get("subjects", [])
    if not isinstance(base_fields, dict) or not isinstance(subjects, list):
        return []

    base_data = {}
    for target_field, source_header in base_fields.items():
        base_data[target_field] = _get_wide_value(wide_mapped_data, source_header)

    records = []
    for subject_config in subjects:
        if not isinstance(subject_config, dict):
            continue

        record = dict(base_data)
        for target_field, source_header in subject_config.items():
            if target_field == "subject_type":
                record[target_field] = source_header
            else:
                record[target_field] = _get_wide_value(wide_mapped_data, source_header)
        record["raw_text"] = _build_raw_text(raw_cells)
        records.append(record)
    return records


def _evaluate_and_maybe_insert_record(
    conn,
    result: dict,
    data: dict,
    raw_cells: list[str],
    major_filter_keywords: list[str],
    preview: bool,
    source_id: int,
) -> tuple[bool, str]:
    if major_filter_keywords and _is_empty(data.get("major_name")):
        result["empty_major_skipped_count"] += 1
        result["skipped_count"] += 1
        return False, "empty_major_name"

    if not _major_matches_keywords(data.get("major_name"), major_filter_keywords):
        result["filter_skipped_count"] += 1
        result["skipped_count"] += 1
        return False, "major_filter_not_matched"

    if _raw_record_exists(conn, data):
        result["duplicate_skipped_count"] += 1
        result["skipped_count"] += 1
        return False, "duplicate"

    result["would_insert_count"] += 1
    if preview:
        return True, "would_insert"

    record_id = create_raw_record_from_dict(
        conn=conn,
        raw_source_id=source_id,
        data=data,
    )
    if record_id is None:
        result["duplicate_skipped_count"] += 1
        result["skipped_count"] += 1
        return False, "duplicate"

    result["inserted_count"] += 1
    return True, "would_insert"


def _process_normal_row(
    conn,
    result: dict,
    source: dict,
    raw_cells: list[str],
    headers: list[str],
    mapping: dict,
    fill_down_fields: list[str],
    last_fill_down_values: dict,
    default_values: dict,
    auto_direction_tags: bool,
    major_filter_keywords: list[str],
    preview: bool,
) -> None:
    data = _prepare_row_data(
        raw_cells=raw_cells,
        headers=headers,
        mapping=mapping,
        fill_down_fields=fill_down_fields,
        last_fill_down_values=last_fill_down_values,
        default_values=default_values,
        auto_direction_tags=auto_direction_tags,
        source=source,
    )
    should_insert, skip_reason = _evaluate_and_maybe_insert_record(
        conn=conn,
        result=result,
        data=data,
        raw_cells=raw_cells,
        major_filter_keywords=major_filter_keywords,
        preview=preview,
        source_id=source["id"],
    )
    _append_sample(
        result,
        _make_sample(raw_cells, data, should_insert, skip_reason),
    )


def _process_wide_row(
    conn,
    result: dict,
    source: dict,
    raw_cells: list[str],
    headers: list[str],
    default_values: dict,
    auto_direction_tags: bool,
    major_filter_keywords: list[str],
    preview: bool,
    wide_config: dict,
) -> None:
    wide_mapped_data = _row_to_raw_mapping(raw_cells, headers)
    expanded_records = []
    candidate_records = _build_wide_records(
        wide_mapped_data=wide_mapped_data,
        wide_config=wide_config,
        raw_cells=raw_cells,
    )

    skip_if_plan_count_zero = bool(wide_config.get("skip_if_plan_count_zero", False))
    skip_if_min_score_empty = bool(wide_config.get("skip_if_min_score_empty", False))

    for record in candidate_records:
        data = {field: record.get(field) for field in SYSTEM_FIELDS}
        data = _finalize_record_data(
            data=data,
            default_values=default_values,
            auto_direction_tags=auto_direction_tags,
            source=source,
            raw_cells=raw_cells,
        )

        should_insert = False
        skip_reason = ""

        if skip_if_plan_count_zero and _to_int(data.get("plan_count")) == 0:
            result["skipped_count"] += 1
            skip_reason = "plan_count_zero"
        elif skip_if_min_score_empty and _is_empty(data.get("min_score")):
            result["skipped_count"] += 1
            skip_reason = "min_score_empty"
        else:
            should_insert, skip_reason = _evaluate_and_maybe_insert_record(
                conn=conn,
                result=result,
                data=data,
                raw_cells=raw_cells,
                major_filter_keywords=major_filter_keywords,
                preview=preview,
                source_id=source["id"],
            )

        expanded_records.append(
            {
                "mapped_data": data,
                "major_name": data.get("major_name"),
                "subject_type": data.get("subject_type"),
                "should_insert": should_insert,
                "skip_reason": skip_reason,
            }
        )

    any_insert = any(record["should_insert"] for record in expanded_records)
    first_reason = ""
    if not any_insert and expanded_records:
        first_reason = expanded_records[0].get("skip_reason", "")

    _append_sample(
        result,
        _make_sample(
            raw_cells=raw_cells,
            mapped_data=expanded_records[0]["mapped_data"] if expanded_records else {},
            should_insert=any_insert,
            skip_reason=first_reason,
            wide_mapped_data=wide_mapped_data,
            expanded_records=expanded_records,
        ),
    )


def parse_html_table_source(source: dict, preview: bool = False) -> dict:
    """解析 HTML table 数据源。

    preview=True 时只解析和统计，不写入 raw_admission_records，也不生成 collector_runs。
    preview=False 时正常写入 raw_admission_records。
    """
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

    custom_mapping = load_field_mapping(source)
    mapping = _normalize_mapping_keys(custom_mapping or DEFAULT_HEADER_MAPPING)

    html = _download_html(source["url"])
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        result["error_count"] = 1
        result["message"] = "页面中未找到 table"
        return result

    if table_index >= len(tables):
        result["error_count"] = 1
        result["message"] = (
            f"table_index={table_index} 超出范围，页面仅有 {len(tables)} 个 table"
        )
        return result

    grid = parse_table_with_spans(tables[table_index])
    if not grid:
        result["error_count"] = 1
        result["message"] = "选中的 table 中没有可解析行"
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
        result["message"] = (
            f"header_row_index={header_row_index} 超出范围，"
            f"选中的 table 仅有 {len(grid)} 行"
        )
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
        result["message"] = "表头行为空，无法解析字段"
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
                _append_sample(
                    result,
                    _make_sample(raw_cells, {}, False, "empty_row"),
                )
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
                _append_sample(
                    result,
                    _make_sample(raw_cells, {}, False, f"error: {exc}"),
                )

        if not preview:
            mark_duplicate_records(conn)
            conn.commit()
    finally:
        conn.close()

    if preview:
        result["inserted_count"] = 0

    result["message"] = _build_message(result)
    return result


def collect_html_table_source(source: dict) -> dict:
    """正式采集一个 HTML table 来源，并写入 raw_admission_records。"""
    return parse_html_table_source(source, preview=False)
