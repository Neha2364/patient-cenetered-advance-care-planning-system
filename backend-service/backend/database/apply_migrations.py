#!/usr/bin/env python3
"""
Database Migration Runner for ACP Care.
Safely applies pending SQL schema migrations to the configured PostgreSQL / Supabase database.

Usage:
    cd C:\ACP_System
    python -m backend.database.apply_migrations
"""

import os
import sys
from sqlalchemy import text, inspect

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_migrations():
    from backend.app import create_app
    from backend.extensions import db

    app = create_app()
    with app.app_context():
        print("Connected to database:", app.config.get("SQLALCHEMY_DATABASE_URI", "").split("@")[-1])

        inspector = inspect(db.engine)
        existing_cols = [c["name"] for c in inspector.get_columns("users")]
        print(f"Current columns in 'users' table: {existing_cols}")

        if "must_change_password" not in existing_cols:
            print("Applying migration: Adding 'must_change_password' to 'users' table...")
            db.session.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;")
            )
            db.session.commit()
            print("Successfully added 'must_change_password' column to 'users' table.")
        else:
            print("Column 'must_change_password' already exists in 'users' table.")

        # Re-verify
        inspector = inspect(db.engine)
        updated_cols = [c["name"] for c in inspector.get_columns("users")]
        print(f"Verified columns in 'users' table: {updated_cols}")

        # Check existing user count and their must_change_password values
        result = db.session.execute(
            text("SELECT id, email, role, must_change_password FROM users LIMIT 10;")
        ).fetchall()
        print(f"\nSample users from database ({len(result)} records):")
        for r in result:
            print(f"  ID: {r[0]} | Email: {r[1]} | Role: {r[2]} | must_change_password: {r[3]}")

        print("\nMigration completed successfully.")

if __name__ == "__main__":
    run_migrations()

