"""Create local users after migrations: python -m app.core.users_cli create-user."""

import argparse
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from app.core.auth import ROLES, create_user
from app.core.db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local AegisOps users")
    parser.add_argument("command", choices=["create-user"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=sorted(ROLES), default="admin")
    args = parser.parse_args()
    password = getpass("Password (12+ characters): ")
    confirm = getpass("Confirm password: ")
    if password != confirm:
        parser.error("Passwords did not match")
    try:
        with SessionLocal() as db:
            user = create_user(db, args.email, password, args.role)
    except (ValueError, IntegrityError) as exc:
        parser.error(str(exc))
    print(f"Created {user.role} account {user.email}")


if __name__ == "__main__":
    main()
