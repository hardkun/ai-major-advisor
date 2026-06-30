import sqlite3

from schemas.school import SchoolCreate


def create_school(db: sqlite3.Connection, school: SchoolCreate) -> dict:
    cursor = db.execute(
        """
        INSERT INTO schools (name, province, city, level, tags)
        VALUES (?, ?, ?, ?, ?)
        """,
        (school.name, school.province, school.city, school.level, school.tags),
    )
    db.commit()
    row = db.execute("SELECT * FROM schools WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def get_school(db: sqlite3.Connection, school_id: int) -> dict | None:
    row = db.execute("SELECT * FROM schools WHERE id = ?", (school_id,)).fetchone()
    return dict(row) if row else None


def list_schools(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT * FROM schools ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]
