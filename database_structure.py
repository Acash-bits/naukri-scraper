import mysql.connector
import os
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

# 1. Establish connection to the server
# Use your actual MySQL username and password
# Database Configuration
DB_CONFIG = {
    'host': os.getenv('HOST'),
    'user': os.getenv('USER'),
    'password': os.getenv('PASS'),
    'database': os.getenv('DATABASE')
}

def init_db_mysql():
    '''Checks connection and ensures the table exists'''
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist so the rest of the script doesn't crash
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs_postings (
                Job_id INT primary key auto_increment,
                Company_Name VARCHAR(512),
                Time_Category VARCHAR(90),
                Posting_Time VARCHAR(20),
                Job_Title VARCHAR(512),
                Category VARCHAR(100),
                Experience VARCHAR(20),
                Location VARCHAR(100),
                Salary VARCHAR(512),
                Page_Number INT,
                LINK VARCHAR(768) unique not null ,
                Scraped_Time TIMESTAMP default CURRENT_TIMESTAMP()
            )
        """)
        print("✅ Connection established and Table is ready!")
    except Error as e:
        print(f'❌ Connection failed: {e}')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
