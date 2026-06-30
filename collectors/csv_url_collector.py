"""CSV URL 数据采集器。"""

import csv
import io
from urllib.request import urlopen

from collectors.common import (
    apply_field_mapping,
    create_raw_record_from_dict,
    load_field_mapping,
    mark_duplicate_records,
)
from db import create_connection


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


def _decode_content(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("utf-8-sig")


def _download_csv(url: str) -> str:
    with urlopen(url, timeout=20) as response:
        content = response.read()
    return _decode_content(content)


def _build_raw_text(row: dict) -> str:
    parts = []
    for key, value in row.items():
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    return "；".join(parts)


def collect_csv_url_source(source: dict) -> dict:
    """采集一个 CSV URL 来源，并写入 raw_admission_records。"""
    result = {
        "source_id": source["id"],
        "parser_type": source.get("parser_type"),
        "inserted_count": 0,
        "skipped_count": 0,
        "error_count": 0,
    }

    mapping = load_field_mapping(source)
    text = _download_csv(source["url"])
    reader = csv.DictReader(io.StringIO(text))

    conn = create_connection()
    try:
        for raw_row in reader:
            try:
                mapped_row = apply_field_mapping(raw_row, mapping)
                data = {field: mapped_row.get(field) for field in SYSTEM_FIELDS}
                data["source_name"] = (
                    mapped_row.get("source_name")
                    or raw_row.get("source_name")
                    or source.get("name")
                )
                data["source_url"] = (
                    mapped_row.get("source_url")
                    or raw_row.get("source_url")
                    or source.get("url")
                )
                data["raw_text"] = (
                    mapped_row.get("raw_text")
                    or raw_row.get("raw_text")
                    or _build_raw_text(raw_row)
                )

                record_id = create_raw_record_from_dict(
                    conn=conn,
                    raw_source_id=source["id"],
                    data=data,
                )
                if record_id is None:
                    result["skipped_count"] += 1
                else:
                    result["inserted_count"] += 1
            except Exception:
                result["error_count"] += 1

        mark_duplicate_records(conn)
        conn.commit()
    finally:
        conn.close()

    return result
