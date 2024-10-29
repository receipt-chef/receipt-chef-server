import os
import mysql.connector
from mysql.connector import errorcode
import sys
import signal
import logging

# MySQL 연결 설정
db_config = {
  'host': os.getenv('DB_HOST'),
  'user': os.getenv('DB_USER'),
  'password': os.getenv('DB_PASSWORD'),
  'database': os.getenv('DB_NAME'),
  'unix_socket': None,  # TCP 연결 강제
  'use_pure': True  # 순수 Python 구현 사용
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        print("Connection successful!")
        return conn
    except mysql.connector.Error as err:
        print("Error connecting to MySQL:", err)
        return None
    
def get_receipt_links():
    conn = get_db_connection()
    if conn is None:
        print("Failed to get database connection.")
        return []
    try:
        cursor = conn.cursor()
        query = "SELECT receipt_no, receipt_file_path FROM RECEIPT"
        cursor.execute(query)
        receipt_links = cursor.fetchall()
        print(receipt_links)
        if not receipt_links:
            print("No receipt links found in the database.")
        return [(row[0], row[1]) for row in receipt_links]
    except mysql.connector.Error as err:
        print("Error fetching receipt links", err)
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == '__main__':
    get_db_connection()