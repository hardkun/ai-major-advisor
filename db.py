"""SQLite 数据库连接与初始化。"""

import sqlite3
from collections.abc import Generator
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "advisor.db"


def create_connection() -> sqlite3.Connection:
    """创建数据库连接，并让查询结果可以像字典一样读取。"""
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI 依赖：每个请求使用一个数据库连接。"""
    connection = create_connection()
    try:
        yield connection
    finally:
        connection.close()


def column_exists(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    """检查 SQLite 表中是否已经存在指定字段。"""
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def init_db() -> None:
    """创建项目所需的数据表，并执行轻量字段迁移。"""
    connection = create_connection()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                province TEXT,
                city TEXT,
                level TEXT,
                tags TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS majors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                direction_tags TEXT,
                description TEXT,
                career_paths TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_type TEXT,
                url TEXT,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_name TEXT NOT NULL,
                data_year INTEGER,
                province TEXT,
                source_id INTEGER,
                row_count INTEGER DEFAULT 0,
                remark TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES data_sources (id)
            );

            CREATE TABLE IF NOT EXISTS admissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                major_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                province TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                batch TEXT,
                min_score INTEGER,
                min_rank INTEGER,
                plan_count INTEGER,
                tuition TEXT,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (school_id) REFERENCES schools (id),
                FOREIGN KEY (major_id) REFERENCES majors (id)
            );

            CREATE INDEX IF NOT EXISTS idx_admissions_school_id
                ON admissions (school_id);
            CREATE INDEX IF NOT EXISTS idx_admissions_major_id
                ON admissions (major_id);
            CREATE INDEX IF NOT EXISTS idx_admissions_year_province
                ON admissions (year, province);

            CREATE TABLE IF NOT EXISTS recommendation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                province TEXT NOT NULL,
                score INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                subject_type TEXT NOT NULL,
                target_direction TEXT NOT NULL,
                use_ai INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id INTEGER NOT NULL,
                free_result_json TEXT NOT NULL,
                paid_result_json TEXT NOT NULL,
                is_paid INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (log_id) REFERENCES recommendation_logs (id)
            );

            CREATE INDEX IF NOT EXISTS idx_reports_log_id
                ON reports (log_id);

            CREATE TABLE IF NOT EXISTS raw_data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_type TEXT,
                url TEXT,
                parser_type TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                description TEXT,
                school_name TEXT,
                discovery_score INTEGER DEFAULT 0,
                discovery_mode TEXT,
                is_demo INTEGER DEFAULT 0,
                is_candidate INTEGER DEFAULT 0,
                candidate_status TEXT,
                official_check_status TEXT,
                official_check_message TEXT,
                official_score INTEGER DEFAULT 0,
                candidate_reject_reason TEXT,
                reference_only INTEGER DEFAULT 0,
                field_mapping_json TEXT,
                parser_config_json TEXT,
                parent_source_id INTEGER,
                file_type TEXT,
                local_file_path TEXT,
                file_size INTEGER,
                file_download_status TEXT,
                file_download_message TEXT,
                last_check_status TEXT,
                last_check_message TEXT,
                last_content_type TEXT,
                last_detected_type TEXT,
                last_table_count INTEGER DEFAULT 0,
                last_file_links_json TEXT,
                last_checked_at TEXT,
                collect_diagnosis_status TEXT,
                collect_diagnosis_message TEXT,
                last_preview_json TEXT,
                last_preview_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_admission_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_source_id INTEGER,
                school_name TEXT,
                school_code TEXT,
                school_province TEXT,
                city TEXT,
                school_level TEXT,
                school_tags TEXT,
                major_name TEXT,
                major_code TEXT,
                major_category TEXT,
                direction_tags TEXT,
                major_description TEXT,
                career_paths TEXT,
                admission_year INTEGER,
                admission_province TEXT,
                subject_type TEXT,
                batch TEXT,
                major_group_code TEXT,
                elective_requirement TEXT,
                min_score INTEGER,
                min_rank INTEGER,
                plan_count INTEGER,
                tuition TEXT,
                campus TEXT,
                source_name TEXT,
                source_url TEXT,
                raw_text TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                is_duplicate INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (raw_source_id) REFERENCES raw_data_sources (id)
            );

            CREATE INDEX IF NOT EXISTS idx_raw_admission_records_status
                ON raw_admission_records (status);
            CREATE INDEX IF NOT EXISTS idx_raw_admission_records_raw_source_id
                ON raw_admission_records (raw_source_id);

            CREATE TABLE IF NOT EXISTS collector_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_source_id INTEGER,
                source_name TEXT,
                parser_type TEXT,
                status TEXT NOT NULL,
                inserted_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                message TEXT,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (raw_source_id) REFERENCES raw_data_sources (id)
            );

            CREATE INDEX IF NOT EXISTS idx_collector_runs_raw_source_id
                ON collector_runs (raw_source_id);
            CREATE INDEX IF NOT EXISTS idx_collector_runs_created_at
                ON collector_runs (created_at);

            CREATE TABLE IF NOT EXISTS source_discovery_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_name TEXT,
                admission_site TEXT,
                query TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                discovered_url TEXT,
                discovered_admission_site TEXT,
                discovered_score_url TEXT,
                detected_type TEXT,
                score INTEGER DEFAULT 0,
                search_candidates_json TEXT,
                discovery_mode TEXT,
                message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_source_discovery_tasks_status
                ON source_discovery_tasks (status);
            CREATE INDEX IF NOT EXISTS idx_source_discovery_tasks_school_name
                ON source_discovery_tasks (school_name);

            CREATE TABLE IF NOT EXISTS data_coverage_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT,
                province TEXT,
                year INTEGER,
                total_schools INTEGER,
                schools_with_sources INTEGER,
                sources_detected INTEGER,
                sources_collected INTEGER,
                raw_records_count INTEGER,
                verified_records_count INTEGER,
                ai_major_records_count INTEGER,
                missing_schools_json TEXT,
                failed_sources_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_data_coverage_reports_created_at
                ON data_coverage_reports (created_at);

            CREATE TABLE IF NOT EXISTS gap_diagnosis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                province TEXT,
                year INTEGER,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_gap_diagnosis_reports_created_at
                ON gap_diagnosis_reports (created_at);
            """
        )

        admission_columns = [
            ("school_code", "TEXT"),
            ("major_group_code", "TEXT"),
            ("major_code", "TEXT"),
            ("elective_requirement", "TEXT"),
            ("campus", "TEXT"),
            ("source_id", "INTEGER"),
            ("import_batch_id", "INTEGER"),
            ("is_verified", "INTEGER NOT NULL DEFAULT 0"),
            ("remark", "TEXT"),
        ]
        for column_name, column_definition in admission_columns:
            if not column_exists(connection, "admissions", column_name):
                connection.execute(
                    f"ALTER TABLE admissions ADD COLUMN "
                    f"{column_name} {column_definition}"
                )

        raw_data_source_columns = [
            ("school_name", "TEXT"),
            ("discovery_score", "INTEGER DEFAULT 0"),
            ("discovery_mode", "TEXT"),
            ("is_demo", "INTEGER DEFAULT 0"),
            ("is_candidate", "INTEGER DEFAULT 0"),
            ("candidate_status", "TEXT"),
            ("official_check_status", "TEXT"),
            ("official_check_message", "TEXT"),
            ("official_score", "INTEGER DEFAULT 0"),
            ("candidate_reject_reason", "TEXT"),
            ("reference_only", "INTEGER DEFAULT 0"),
            ("field_mapping_json", "TEXT"),
            ("parser_config_json", "TEXT"),
            ("parent_source_id", "INTEGER"),
            ("file_type", "TEXT"),
            ("local_file_path", "TEXT"),
            ("file_size", "INTEGER"),
            ("file_download_status", "TEXT"),
            ("file_download_message", "TEXT"),
            ("last_check_status", "TEXT"),
            ("last_check_message", "TEXT"),
            ("last_content_type", "TEXT"),
            ("last_detected_type", "TEXT"),
            ("last_table_count", "INTEGER DEFAULT 0"),
            ("last_file_links_json", "TEXT"),
            ("last_checked_at", "TEXT"),
            ("collect_diagnosis_status", "TEXT"),
            ("collect_diagnosis_message", "TEXT"),
            ("last_preview_json", "TEXT"),
            ("last_preview_at", "TEXT"),
        ]
        for column_name, column_definition in raw_data_source_columns:
            if not column_exists(connection, "raw_data_sources", column_name):
                connection.execute(
                    f"ALTER TABLE raw_data_sources ADD COLUMN "
                    f"{column_name} {column_definition}"
                )

        source_discovery_task_columns = [
            ("discovered_admission_site", "TEXT"),
            ("discovered_score_url", "TEXT"),
            ("search_candidates_json", "TEXT"),
            ("discovery_mode", "TEXT"),
        ]
        for column_name, column_definition in source_discovery_task_columns:
            if not column_exists(connection, "source_discovery_tasks", column_name):
                connection.execute(
                    f"ALTER TABLE source_discovery_tasks ADD COLUMN "
                    f"{column_name} {column_definition}"
                )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_admissions_source_id
            ON admissions (source_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_admissions_import_batch_id
            ON admissions (import_batch_id)
            """
        )
        connection.commit()
    finally:
        connection.close()


def check_db_status() -> dict[str, str]:
    """执行一条简单查询，确认数据库可连接。"""
    connection = create_connection()
    try:
        connection.execute("SELECT 1").fetchone()
        return {"status": "ok", "database": str(DATABASE_PATH)}
    finally:
        connection.close()
