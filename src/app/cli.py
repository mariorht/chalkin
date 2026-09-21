"""
Management CLI for Chalkin.

Usage (from the src/ directory, or with src/ on PYTHONPATH):

    python -m app.cli make_admin tu@email.com
    python -m app.cli revoke_admin tu@email.com
    python -m app.cli list_admins

Inside Docker:

    docker-compose exec app python -m app.cli make_admin tu@email.com
"""
import argparse
import sys
from pathlib import Path

# Allow running as `python src/app/cli.py ...` from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import SessionLocal
from app.models.user import User


def _find_user(db, email: str):
    return db.query(User).filter(User.email == email).first()


def make_admin(email: str, value: bool = True) -> int:
    db = SessionLocal()
    try:
        user = _find_user(db, email)
        if not user:
            print(f"No user found with email: {email}")
            return 1

        user.is_admin = value
        db.commit()
        state = "granted" if value else "revoked"
        print(f"Admin privileges {state} for {user.username} <{user.email}> (id={user.id})")
        return 0
    finally:
        db.close()


def list_admins() -> int:
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.is_admin == True).all()  # noqa: E712
        if not admins:
            print("No admins configured.")
            return 0
        for user in admins:
            print(f"- {user.username} <{user.email}> (id={user.id})")
        return 0
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Chalkin management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_make = sub.add_parser("make_admin", help="Grant admin privileges to a user")
    p_make.add_argument("email", help="User email")

    p_revoke = sub.add_parser("revoke_admin", help="Revoke admin privileges")
    p_revoke.add_argument("email", help="User email")

    sub.add_parser("list_admins", help="List all admins")

    args = parser.parse_args()

    if args.command == "make_admin":
        return make_admin(args.email, True)
    if args.command == "revoke_admin":
        return make_admin(args.email, False)
    if args.command == "list_admins":
        return list_admins()

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
