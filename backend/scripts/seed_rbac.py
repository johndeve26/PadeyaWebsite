"""Seed default roles and permissions.

Usage:
  cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/seed_rbac.py
"""

from app.core.database import SessionLocal
from app.users.seed import seed_roles_and_permissions


def main() -> None:
    db = SessionLocal()
    try:
        seed_roles_and_permissions(db)
        print("Seeded default roles and permissions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
