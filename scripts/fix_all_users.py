from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sys
import os

# Add parent directory to path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User

app = create_app()

# Run this script to fix all users in the database
with app.app_context():
    # First check the database structure
    try:
        result = db.session.execute("DESCRIBE user").fetchall()
        print("Database structure for user table:")
        for row in result:
            print(row)
            
        # Now directly update all users with SQL for absolute certainty
        db.session.execute("UPDATE user SET status = 'Pending' WHERE status != 'Active' AND is_admin = 0")
        db.session.execute("UPDATE user SET status = 'Active' WHERE is_admin = 1")
        db.session.commit()
        
        # Verify the updates
        print("\nUser status after updates:")
        users = User.query.all()
        for user in users:
            print(f"User ID: {user.id}, Username: {user.username}, Status: {user.status}, Admin: {user.is_admin}")
        
        print("\nFix completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
