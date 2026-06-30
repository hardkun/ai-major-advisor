"""采集器通用工具函数。"""

import json
import sqlite3


RAW_RECORD_FIELDS = [
    "raw_source_id",
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
    "status",
]


INTEGER_FIELDS = {
    "admission_year",
    "min_score",
    "min_rank",
    "plan_count",
}


def safe_int(value):
    """安全转换整数；空值或转换失败时返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def normalize_text(value):
    """清理文本；None 和空字符串都返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_field_mapping(source: dict) -> dict:
    """从 raw_data_sources.field_mapping_json 中读取字段映射配置。"""
    mapping_json = source.get("field_mapping_json")
    if not mapping_json:
        return {}

    try:
        mapping = json.loads(mapping_json)
    except (TypeError, json.JSONDecodeError):
        return {}

    if not isinstance(mapping, dict):
        return {}
    return mapping


def load_parser_config(source: dict) -> dict:
    """从 raw_data_sources.parser_config_json 中读取解析配置。"""
    parser_config_json = source.get("parser_config_json")
    if not parser_config_json:
        return {}

    try:
        config = json.loads(parser_config_json)
    except (TypeError, json.JSONDecodeError):
        return {}

    if not isinstance(config, dict):
        return {}
    return config


def apply_field_mapping(row: dict, mapping: dict) -> dict:
    """将原始表头数据转换为系统字段格式。

    mapping 示例：
    {
        "院校名称": "school_name",
        "专业名称": "major_name",
        "最低分": "min_score"
    }

    未配置映射的字段会保留原字段，方便调试。
    """
    if not mapping:
        return dict(row)

    mapped_row = {}
    for key, value in row.items():
        target_key = mapping.get(key, key)
        mapped_row[target_key] = value
    return mapped_row


def apply_default_values(data: dict, default_values: dict) -> dict:
    """当 data 某字段为空时，用 default_values 中的默认值补齐。"""
    if not default_values:
        return data

    updated = dict(data)
    for key, value in default_values.items():
        current_value = updated.get(key)
        if current_value is None or str(current_value).strip() == "":
            updated[key] = value
    return updated


def _prepare_value(field_name: str, data: dict):
    if field_name in INTEGER_FIELDS:
        return safe_int(data.get(field_name))
    return normalize_text(data.get(field_name))


def _raw_record_exists(conn: sqlite3.Connection, data: dict) -> bool:
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
            data.get("admission_year"),
            data.get("admission_province"),
            data.get("subject_type"),
            data.get("major_group_code"),
            data.get("major_code"),
            data.get("min_score"),
            data.get("min_rank"),
        ),
    ).fetchone()
    return row is not None


def create_raw_record_from_dict(
    conn: sqlite3.Connection,
    raw_source_id: int,
    data: dict,
) -> int | None:
    """将解析结果写入 raw_admission_records。

    如果按核心字段判断已经存在相同记录，则跳过并返回 None。
    """
    prepared = {
        field: _prepare_value(field, data)
        for field in RAW_RECORD_FIELDS
        if field not in {"raw_source_id", "status"}
    }
    prepared["raw_source_id"] = raw_source_id
    prepared["status"] = "pending"

    if _raw_record_exists(conn, prepared):
        return None

    columns = ", ".join(RAW_RECORD_FIELDS)
    placeholders = ", ".join(["?"] * len(RAW_RECORD_FIELDS))
    values = [prepared.get(field) for field in RAW_RECORD_FIELDS]

    cursor = conn.execute(
        f"""
        INSERT INTO raw_admission_records ({columns})
        VALUES ({placeholders})
        """,
        values,
    )
    return cursor.lastrowid


def mark_duplicate_records(conn: sqlite3.Connection) -> None:
    """标记 raw_admission_records 中的疑似重复数据。"""
    conn.execute("UPDATE raw_admission_records SET is_duplicate = 0")
    conn.execute(
        """
        UPDATE raw_admission_records
        SET is_duplicate = 1
        WHERE EXISTS (
            SELECT 1
            FROM raw_admission_records AS other
            WHERE other.id != raw_admission_records.id
              AND COALESCE(other.school_name, '') =
                  COALESCE(raw_admission_records.school_name, '')
              AND COALESCE(other.major_name, '') =
                  COALESCE(raw_admission_records.major_name, '')
              AND COALESCE(other.admission_year, -1) =
                  COALESCE(raw_admission_records.admission_year, -1)
              AND COALESCE(other.admission_province, '') =
                  COALESCE(raw_admission_records.admission_province, '')
              AND COALESCE(other.subject_type, '') =
                  COALESCE(raw_admission_records.subject_type, '')
              AND COALESCE(other.major_group_code, '') =
                  COALESCE(raw_admission_records.major_group_code, '')
              AND COALESCE(other.major_code, '') =
                  COALESCE(raw_admission_records.major_code, '')
        )
        """
    )
