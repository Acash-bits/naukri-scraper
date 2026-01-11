import mysql.connector
import os
from mysql.connector import errorcode
from env import load_dotenv

# 1. Establish connection to the server
# Use your actual MySQL username and password
db_connection = mysql.connector.connect(
  host="localhost",
  user="your_username",
  password="your_password"
)

# 2. Create a cursor object to interact with the server
cursor = db_connection.cursor()

# 3. Execute the SQL command to create the database
# Using 'IF NOT EXISTS' prevents errors if the database already exists
cursor.execute("CREATE DATABASE IF NOT EXISTS my_new_database")

print("Database created successfully.")

# 4. (Optional) Verify by listing all databases
cursor.execute("SHOW DATABASES")
for db in cursor:
    print(db)

# 5. Close the connection
cursor.close()
db_connection.close()
