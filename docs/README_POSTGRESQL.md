# PostgreSQL Setup Instructions

1. **Install PostgreSQL**  
   Download and install PostgreSQL from the official website and ensure the server is running.

2. **Create a Database**  
   Open your terminal or pgAdmin and create a new database. For example, to create a database named `db_name`:
   ```
   psql -U your_username
   CREATE DATABASE db_name;
   \q
   ```
3. **Import the Schema**  
   Run the provided schema file to create all required tables:
   ```
   psql -U your_username -d db_name -f /c:/Users/User/projects/document-tracking-system/db_schema.sql
   ```
   Replace `your_username` and `db_name` with your actual PostgreSQL username and database name.

4. **Update Application Configuration**  
   In `config.py`, ensure `SQLALCHEMY_DATABASE_URI` is set with the correct username, password, host, port, and database name:
   ```
   SQLALCHEMY_DATABASE_URI = "postgresql://username:password@localhost:5432/db_name"
   ```
   
5. **Verify the Tables**  
   Connect to your database and run:
   ```
   \dt
   ```
   Confirm that tables like "user", document, activity_log, and notification are listed.

6. **Restart Your Application**  
   Your app should now connect to PostgreSQL and use the newly created schema.
