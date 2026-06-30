"""将模拟院校、专业和录取数据批量导入 SQLite。"""

import csv
from pathlib import Path

from db import create_connection, init_db
from utils.subject_type import normalize_subject_type


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "seed_admissions.csv"


def parse_int(value: str, field_name: str, row_number: int) -> int | None:
    """将 CSV 整数字段转换为 int，空字符串转换为 None。"""
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ValueError(f"第 {row_number} 行的 {field_name} 不是有效整数") from exc


def import_seed_data() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"找不到种子数据文件：{CSV_PATH}")

    init_db()
    db = create_connection()

    new_schools = 0
    new_majors = 0
    new_admissions = 0
    skipped_admissions = 0

    try:
        with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)

            for row_number, row in enumerate(reader, start=2):
                school_name = row["school_name"].strip()
                major_name = row["major_name"].strip()
                year = parse_int(row["year"], "year", row_number)
                min_score = parse_int(row["min_score"], "min_score", row_number)
                min_rank = parse_int(row["min_rank"], "min_rank", row_number)
                plan_count = parse_int(row["plan_count"], "plan_count", row_number)

                school = db.execute(
                    "SELECT id FROM schools WHERE name = ?",
                    (school_name,),
                ).fetchone()
                if school is None:
                    cursor = db.execute(
                        """
                        INSERT INTO schools (name, province, city, level, tags)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            school_name,
                            row["school_province"].strip() or None,
                            row["city"].strip() or None,
                            row["school_level"].strip() or None,
                            row["school_tags"].strip() or None,
                        ),
                    )
                    school_id = int(cursor.lastrowid)
                    new_schools += 1
                else:
                    school_id = int(school["id"])

                major = db.execute(
                    "SELECT id FROM majors WHERE name = ?",
                    (major_name,),
                ).fetchone()
                if major is None:
                    cursor = db.execute(
                        """
                        INSERT INTO majors
                            (name, category, direction_tags, description, career_paths)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            major_name,
                            row["major_category"].strip() or None,
                            row["direction_tags"].strip() or None,
                            row["major_description"].strip() or None,
                            row["career_paths"].strip() or None,
                        ),
                    )
                    major_id = int(cursor.lastrowid)
                    new_majors += 1
                else:
                    major_id = int(major["id"])

                admission_province = row["admission_province"].strip()
                subject_type = normalize_subject_type(row["subject_type"].strip())
                duplicate = db.execute(
                    """
                    SELECT id FROM admissions
                    WHERE school_id = ?
                      AND major_id = ?
                      AND year = ?
                      AND province = ?
                      AND subject_type = ?
                    """,
                    (
                        school_id,
                        major_id,
                        year,
                        admission_province,
                        subject_type,
                    ),
                ).fetchone()

                if duplicate is not None:
                    skipped_admissions += 1
                    continue

                db.execute(
                    """
                    INSERT INTO admissions
                        (school_id, major_id, year, province, subject_type,
                         batch, min_score, min_rank, plan_count, tuition, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        school_id,
                        major_id,
                        year,
                        admission_province,
                        subject_type,
                        row["batch"].strip() or None,
                        min_score,
                        min_rank,
                        plan_count,
                        row["tuition"].strip() or None,
                        row["source"].strip() or None,
                    ),
                )
                new_admissions += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"新增学校数量：{new_schools}")
    print(f"新增专业数量：{new_majors}")
    print(f"新增录取数据数量：{new_admissions}")
    print(f"跳过重复数据数量：{skipped_admissions}")


if __name__ == "__main__":
    import_seed_data()
