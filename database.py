import os
import mysql.connector
from mysql.connector import errorcode
import sys
import signal
import logging
import bcrypt

from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()

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

def register_user(member_nm, member_email, member_pw, member_gender, member_age, prefer_food_cnt, avoid_food_cnt, disease_yn, disease_cnt):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor()
        hashed_password = bcrypt.hashpw(member_pw.encode('utf-8'), bcrypt.gensalt())
        
        query = """
            INSERT INTO MEMBER 
            (member_nm, member_email, member_gender, member_age, member_pw, prefer_food_cnt, avoid_food_cnt, disease_yn, disease_cnt) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (member_nm, member_email, member_gender, member_age, hashed_password, prefer_food_cnt, avoid_food_cnt, disease_yn, disease_cnt))
        conn.commit()
        return True, None
    except mysql.connector.Error as err:
        return False, str(err)
    finally:
        cursor.close()
        conn.close()

def authenticate_user(username, password):
    conn = get_db_connection()
    if conn is None:
        return False, "Database connection failed"
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT member_no, member_pw FROM MEMBER WHERE member_email = %s", (username,))
        member = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if member and bcrypt.checkpw(password.encode('utf-8'), member['member_pw'].encode('utf-8')):
            return True, member
        else:
            return False, "Invalid username or password"
    except mysql.connector.Error as err:
        return False, str(err)

def get_receipt_links(member_no):
    conn = get_db_connection()
    if conn is None:
        print("Failed to get database connection.")
        return []
    try:
        cursor = conn.cursor()
        query = "SELECT receipt_no, receipt_file_path FROM RECEIPT WHERE member_no = %s"
        cursor.execute(query, (member_no,))
        receipt_links = cursor.fetchall()
        if not receipt_links:
            print("No receipt links found in the database for this user.")
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