Steps to reset migrations (if no data is present):

1. Drop your current database schema (or the entire database).
2. Delete or move aside the "migrations" folder.
3. Recreate the migration repository:
   - Run: flask db init
   - Run: flask db migrate -m "Initial migration"
   - Run: flask db upgrade
4. Your database is now synced with your models.
