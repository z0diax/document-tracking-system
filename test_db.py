from your_app import db  # Adjust the import according to your project structure
result = db.session.execute("SELECT 1").scalar()
if result == 1:
    print("Python MySQL connection test successful.")
else:
    print("Python MySQL connection test failed.")
