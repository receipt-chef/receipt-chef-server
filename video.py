# pip install flask opencv-python boto3
import cv2
import boto3
import os
from datetime import datetime
import mysql.connector
import logging
from logging.handlers import RotatingFileHandler
import sys

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 애플리케이션 로거 설정
app_logger = logging.getLogger('app')
# app_logger.setLevel(logging.DEBUG)
app_logger.setLevel(logging.INFO)

# 파일 핸들러 (애플리케이션 로그용)
file_handler = RotatingFileHandler('app.log', maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
app_logger.addHandler(file_handler)

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
app_logger.addHandler(console_handler)

# boto3 및 다른 라이브러리의 로그 레벨 조정
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# 네이버 클라우드 플랫폼 Object Storage 설정
# .env에 api 설정 값, api gateway url 넣으면 됨
CLOVA_API_URL = os.getenv("CLOVA_API_URL")  # 클로바 OCR API URL로 변경
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")  # 클로바 OCR API Key로 변경
ACCESS_KEY = os.getenv('ACCESS_KEY') # 네이버 Obejct Storage Access Key로 변경
SECRET_KEY = os.getenv('SECRET_KEY') # 네이버 Obejct Storage Secret Key로 변경
REGION_NAME = 'kr-standard'
ENDPOINT_URL = 'https://kr.object.ncloudstorage.com'
BUCKET_NAME = os.getenv('BUCKET_NAME') # 네이버 Obejct Storage Secret Key로 변경

# S3 클라이언트 생성
s3 = boto3.client('s3',
                  aws_access_key_id=ACCESS_KEY,
                  aws_secret_access_key=SECRET_KEY,
                  region_name=REGION_NAME,
                  endpoint_url=ENDPOINT_URL)

# MySQL 연결 설정
db_config = {
  'host': os.getenv('DB_HOST'),
  'user': os.getenv('DB_USER'),
  'password': os.getenv('DB_PASSWORD'),
  'database': os.getenv('DB_NAME'),
  'unix_socket': None,  # TCP 연결 강제
  'use_pure': True  # 순수 Python 구현 사용
}

# 카메라 설정
camera = cv2.VideoCapture(0)

def get_db_connection():
  app_logger.info("Attempting to connect to the database")
  app_logger.debug(f"Attempting to connect with: host={db_config['host']}, user={db_config['user']}, database={db_config['database']}")
  try:
      conn = mysql.connector.connect(**db_config)
      app_logger.info("Database connection successful")
      return conn
  except mysql.connector.Error as err:
      app_logger.error(f"Database connection failed: {err}")
      if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
          app_logger.error("Something is wrong with your user name or password")
      elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
          app_logger.error("Database does not exist")
      else:
          app_logger.error(f"Error: {err}")
      raise  # 예외를 다시 발생시켜 상위 레벨에서 처리할 수 있게 함
  except Exception as e:
      app_logger.error(f"Unexpected error in get_db_connection: {e}")
      raise

def create_table_if_not_exists():
  app_logger.info("Attempting to create table if not exists")
  try:
      conn = get_db_connection()
      if conn is None:
          app_logger.error("Failed to create table: Unable to connect to database")
          return False

      cursor = conn.cursor()
      create_table_sql = '''
      CREATE TABLE IF NOT EXISTS mart_receipts (
          receipt_id INT AUTO_INCREMENT PRIMARY KEY,
          receipt_image_url VARCHAR(255) NOT NULL,
          member_id VARCHAR(100) NOT NULL,
          items LONGTEXT
      );
      '''
      cursor.execute(create_table_sql)
      conn.commit()
      app_logger.info("Table created or already exists.")
      return True
  except mysql.connector.Error as err:
      app_logger.error(f"MySQL Error: {err}")
      return False
  except Exception as e:
      app_logger.error(f"Unexpected error in create_table_if_not_exists: {e}")
      return False
  finally:
      if 'cursor' in locals():
          cursor.close()
      if 'conn' in locals() and conn.is_connected():
          conn.close()
          app_logger.info("Database connection closed")

def insert_receipt(receipt_image_url, member_id):
  conn = get_db_connection()
  if conn is None:
      app_logger.error("Failed to insert receipt: Unable to connect to database")
      return False

  try:
      cursor = conn.cursor()
      insert_sql = '''
      INSERT INTO mart_receipts (receipt_image_url, member_id)
      VALUES (%s, %s);
      '''
      cursor.execute(insert_sql, (receipt_image_url, member_id))
      conn.commit()
      app_logger.info("Receipt info inserted successfully.")
      return True
  except mysql.connector.Error as err:
      app_logger.error(f"Error inserting receipt info: {err}")
      return False
  finally:
      if 'cursor' in locals():
          cursor.close()
      conn.close()

def generate_frames():
  while True:
      success, frame = camera.read()
      if not success:
          break
      else:
          ret, buffer = cv2.imencode('.jpg', frame)
          frame = buffer.tobytes()
          yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def capture_and_upload():
  ret, frame = camera.read()
  if not ret:
      app_logger.error("Failed to capture image")
      return None, "Failed to capture image"

  # 이미지 파일 이름 생성 (현재 시간 기준)
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  filename = f"captured_image_{timestamp}.jpg"

  
  # 이미지를 임시 파일로 저장
  cv2.imwrite(filename, frame)

  # Object Storage에 업로드
  try:
      s3.upload_file(filename, BUCKET_NAME, filename)
      app_logger.info(f"Image uploaded successfully: {filename}")
      
      image_url = f"https://{BUCKET_NAME}.{REGION_NAME}.object.ncloudstorage.com/{filename}"
      
      member_id = f"member_{timestamp}"
      
      if insert_receipt(image_url, member_id):
          result = f"Image uploaded and receipt info saved: {filename}"
          app_logger.info(result)
      else:
          result = "Image uploaded but failed to save receipt info"
          app_logger.warning(result)
  except Exception as e:
      app_logger.error(f"Error in capture_and_upload: {str(e)}")
      result = f"Error: {str(e)}"
      image_url = None
  finally:
      if os.path.exists(filename):
          os.remove(filename)
      image_url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': BUCKET_NAME,
                                                'Key': filename},
                                        ExpiresIn=3600)
  
  return image_url, result