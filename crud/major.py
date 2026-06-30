import sqlite3

from schemas.major import MajorCreate


def create_major(db: sqlite3.Connection, major: MajorCreate) -> dict:
    cursor = db.execute(
        """
        INSERT INTO majors
            (name, category, direction_tags, description, career_paths)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            major.name,
            major.category,
            major.direction_tags,
            major.description,
            major.career_paths,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM majors WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def get_major(db: sqlite3.Connection, major_id: int) -> dict | None:
    row = db.execute("SELECT * FROM majors WHERE id = ?", (major_id,)).fetchone()
    return dict(row) if row else None


def list_majors(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute("SELECT * FROM majors ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]
