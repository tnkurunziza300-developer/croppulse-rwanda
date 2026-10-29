"""Controlled first-administrator provisioning for a locally operated API database."""
import argparse
from sqlalchemy import func, select

from .db import get_session_factory
from .models import AdminAuditEvent, Farmer, utcnow


def promote_first_admin(email: str):
    expected = email.strip().lower()
    confirmation = input(f"Type the account email to confirm first-admin provisioning ({expected}): ").strip().lower()
    if confirmation != expected:
        raise SystemExit("Confirmation did not match; no changes were made.")
    with get_session_factory()() as db:
        if db.scalar(select(func.count()).select_from(Farmer).where(Farmer.role == "admin")):
            raise SystemExit("An administrator already exists. Use the authenticated admin account workflow instead.")
        farmer = db.scalar(select(Farmer).where(func.lower(Farmer.email) == expected))
        if farmer is None or farmer.status != "active":
            raise SystemExit("An existing active farmer account is required. No changes were made.")
        farmer.role = "admin"
        db.add(AdminAuditEvent(actor_id=None, target_farmer_id=farmer.id,
                               action="first_admin_provisioned", target_type="farmer",
                               target_id=farmer.id,
                               reason="First administrator provisioned by local database operator.",
                               result="success", created_at=utcnow()))
        db.commit()
        print(f"Administrator role granted to {farmer.email} ({farmer.id}).")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    promote = subparsers.add_parser("promote-first-admin")
    promote.add_argument("email")
    args = parser.parse_args()
    if args.command == "promote-first-admin":
        promote_first_admin(args.email)


if __name__ == "__main__":
    main()
