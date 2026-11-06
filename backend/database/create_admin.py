#!/usr/bin/env python3
"""
Secure CLI script to provision the first Admin account.

This script is the ONLY authorized way to create admin accounts.
It is NOT exposed via any API endpoint — server-side access only.

Usage:
    cd C:\ACP_System
    python -m backend.database.create_admin --email admin@acpcare.com --name "Admin Name" --password "SecureAdmin123!"

Requirements:
    - Must be run on the server (not via any public API)
    - Email must be unique in the system
    - Password must be at least 8 characters (stronger requirement for admin)
    - Existing accounts are never modified by this script
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def main():
    parser = argparse.ArgumentParser(
        description='Provision an authorized admin account (server-side only, not a public endpoint).'
    )
    parser.add_argument('--email', required=True, help='Admin email address')
    parser.add_argument('--name', required=True, help='Admin full name')
    parser.add_argument('--password', required=True, help='Admin password (min 8 characters)')
    args = parser.parse_args()

    if len(args.password) < 8:
        print('ERROR: Admin password must be at least 8 characters long.')
        sys.exit(1)

    try:
        from backend.app import create_app
        from backend.extensions import db
        from backend.models.user import User
    except ImportError as e:
        print(f'ERROR: Could not import backend modules: {e}')
        print('Make sure you run this from the C:\\ACP_System directory:')
        print('  python -m backend.database.create_admin --email ... --name ... --password ...')
        sys.exit(1)

    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(email=args.email).first()
        if existing:
            print(f"ERROR: A user with email '{args.email}' already exists (role={existing.role}).")
            sys.exit(1)

        admin = User(
            full_name=args.name,
            email=args.email,
            role='admin',  # Always 'admin' — hardcoded, not from any CLI argument
        )
        admin.set_password(args.password)

        db.session.add(admin)
        db.session.commit()

        print('✓ Admin account provisioned successfully.')
        print(f'  Email : {args.email}')
        print(f'  Name  : {args.name}')
        print(f'  Role  : admin')
        print(f'  ID    : {admin.id}')
        print()
        print('The admin can now sign in at the Admin Portal (/admin-login).')
        print('KEEP THIS PASSWORD SECURE — it was not stored in plain text.')


if __name__ == '__main__':
    main()

