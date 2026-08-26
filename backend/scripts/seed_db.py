"""Create the tables and upsert the 10 catalog courses. Idempotent — run it as often as you like.

    python scripts/seed_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, SQLModel                      # noqa: E402

from app.db import engine                                   # noqa: E402
from app.models import Course                               # noqa: E402
from seed.courses import CATALOG                            # noqa: E402


def seed() -> tuple[int, int]:
    SQLModel.metadata.create_all(engine)
    inserted = updated = 0
    with Session(engine) as session:
        for row in CATALOG:
            course = session.get(Course, row["id"])
            if course is None:
                session.add(Course(**row))
                inserted += 1
            elif (course.code, course.name, course.curriculum_text) != (
                row["code"], row["name"], row["curriculum_text"],
            ):
                course.code, course.name = row["code"], row["name"]
                course.curriculum_text = row["curriculum_text"]
                updated += 1
        session.commit()
    return inserted, updated


if __name__ == "__main__":
    ins, upd = seed()
    print(f"catalog: {ins} inserted, {upd} updated, {len(CATALOG) - ins - upd} unchanged")
