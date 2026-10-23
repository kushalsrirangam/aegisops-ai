"""Create local users after migrations: python -m app.core.users_cli create-user."""

import argparse
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from app.core.auth import ROLES, create_user
from app.core.db import SessionLocal
from app.core.login_throttle import reset_password, unlock_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local AegisOps users")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user")
    create.add_argument("--email", required=True)
    create.add_argument("--role", choices=sorted(ROLES), default="admin")
    reset = commands.add_parser("reset-password")
    reset.add_argument("--email", required=True)
    unlock = commands.add_parser("unlock-user")
    unlock.add_argument("--email", required=True)
    args = parser.parse_args()
    if args.command != "unlock-user":
        password = getpass("Password (12+ characters): ")
        confirm = getpass("Confirm password: ")
        if password != confirm:
            parser.error("Passwords did not match")
    try:
        with SessionLocal() as db:
            if args.command == "create-user":
                user = create_user(db, args.email, password, args.role)
                message = f"Created {user.role} account {user.email}"
            elif args.command == "reset-password":
                user = reset_password(db, args.email, password)
                message = f"Reset password and revoked sessions for {user.email}"
            else:
                user = unlock_user(db, args.email)
                message = f"Cleared account lock for {user.email}"
    except (ValueError, IntegrityError) as exc:
        parser.error(str(exc))
    print(message)


if __name__ == "__main__":
    main()
