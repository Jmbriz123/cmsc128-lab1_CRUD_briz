"""Add sample personal tasks to accounts that were registered through the UI.

Usage (inside the backend container):
    python -m app.seed_tasks first@example.com second@example.com

The seeder never creates accounts, and it skips titles an account already
has, so running it twice does not duplicate tasks.
"""
import sys
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Todo, User

SAMPLE_TASKS = [
    {"title": "Review lecture notes", "priority": "medium", "tag": "study", "days": 1},
    {"title": "Finish lab report", "priority": "high", "tag": "cmsc128", "days": 2},
    {"title": "Read assigned chapter", "priority": "low", "tag": "reading", "days": 4},
    {"title": "Prepare defense talking points", "priority": "high", "tag": "cmsc128", "days": 3},
]


class UnknownAccount(Exception):
    pass


def seed_tasks(db: Session, email: str) -> int:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise UnknownAccount(email)
    existing = set(db.scalars(select(Todo.title).where(Todo.user_id == user.id, Todo.list_id.is_(None))))
    now = datetime.utcnow()
    added = [
        Todo(user_id=user.id, title=task["title"], priority=task["priority"], tag=task["tag"],
             due_date=now + timedelta(days=task["days"]))
        for task in SAMPLE_TASKS if task["title"] not in existing
    ]
    db.add_all(added)
    db.commit()
    return len(added)


def main(emails: list[str]) -> int:
    if not emails:
        print(__doc__)
        return 2
    with SessionLocal() as db:
        for email in emails:
            try:
                print(f"{email}: added {seed_tasks(db, email)} task(s)")
            except UnknownAccount:
                print(f"{email}: no such account; register it through the app first")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
