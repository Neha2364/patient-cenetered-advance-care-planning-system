#!/usr/bin/env python3
"""
Secure CLI script to create authorized doctor accounts (server-side only).

Normal doctor creation should happen through the Admin Portal.
This script is kept as a server-side recovery / bootstrap utility.

Usage:
    cd C:\ACP_System
    python -m backend.database.create_doctor --email dr@hospital.com --name "Dr. Name" --password "Pass123!"

Requirements:
    - Must be run on the server (not via any public API)
    - Email must be unique in the system
    - Password must be at least 6 characters
    - Existing accounts are never modified by this script
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    parser = argparse.ArgumentParser(
        description='Create an authorized doctor account (server-side only, not a public endpoint).'
    )
    parser.add_argument('--email', required=True, help="Doctor's email address")
    parser.add_argument('--name', required=True, help="Doctor's full name")
    parser.add_argument('--password', required=True, help='Initial password (min 6 characters)')
    parser.add_argument('--specialization', default=None, help='Medical specialization (optional)')
    parser.add_argument('--hospital', default=None, help='Hospital / institution (optional)')
    parser.add_argument('--mobile', default=None, help='Mobile number (optional)')
    args = parser.parse_args()

    if len(args.password) < 6:
        print('ERROR: Password must be at least 6 characters long.')
        sys.exit(1)

    try:
        from backend.app import create_app
        from backend.extensions import db
        from backend.models.user import User
        from backend.services.admin_service import AdminService
    except ImportError as e:
        print(f'ERROR: Could not import backend modules: {e}')
        sys.exit(1)

    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(email=args.email).first()
        if existing:
            print(f"ERROR: A user with email '{args.email}' already exists (role={existing.role}).")
            sys.exit(1)

        # Use the shared AdminService so logic is not duplicated
        try:
            user, _ = AdminService.create_doctor(
                full_name=args.name,
                email=args.email,
                mobile_number=args.mobile,
                specialization=args.specialization,
                hospital=args.hospital,
                performed_by_id=None,
            )
            # Override the generated password with the one the admin provided
            user.set_password(args.password)
            db.session.commit()
        except ValueError as e:
            print(f'ERROR: {e}')
            sys.exit(1)

        print('✓ Doctor account created successfully.')
        print(f'  Email : {args.email}')
        print(f'  Name  : {args.name}')
        print(f'  Role  : doctor')
        print(f'  ID    : {user.id}')
        print()
        print('The doctor can now sign in at the Doctor Portal (/doctor-login).')


if __name__ == '__main__':
    main()
