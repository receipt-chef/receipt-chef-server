from flask import Flask, request, render_template, redirect, url_for, jsonify
import boto3
import os
import uuid
from database import get_receipt_links
from ocr import process_image_for_ocr, display_text_data
from video import generate_frames, capture_and_upload

from dotenv import load_dotenv
from flask import Response
# .env 파일 로드
load_dotenv()

# 애플리케이션 로거 설정
import logging
from logging.handlers import RotatingFileHandler

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

app = Flask(__name__)

ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
REGION_NAME = os.getenv("REGION_NAME")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")
CLOVA_OCR_SECRET_KEY = os.getenv("CLOVA_OCR_SECRET_KEY")
CLOVA_OCR_API_URL = os.getenv("CLOVA_OCR_API_URL")

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION_NAME, endpoint_url=ENDPOINT_URL)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 업로드 폴더가 없으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/get_receipts', methods=['GET'])
def get_receipts():
    receipt_links = get_receipt_links()
    signed_urls = []
    for receipt_id, receipt_key in receipt_links:
        try:
            # Ensure receipt_key does not contain additional prefixes
            if receipt_key.startswith("https://"):
                receipt_key = receipt_key.split(BUCKET_NAME + "/")[-1]
            
            # Generate the presigned URL
            url = s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': receipt_key},
                ExpiresIn=3600,
                HttpMethod='GET'
            )
            signed_urls.append({'receipt_id': receipt_id, 'url': url})
            print(f"signed_urls URL for {signed_urls}")
        except Exception as e:
            print(f"Error generating presigned URL for {receipt_key}: {e}")
    return jsonify({'receipt_links': signed_urls})

@app.route('/process_receipt', methods=['POST'])
def process_receipt():
    image_url = request.json.get('image_url')
    if not image_url:
        return jsonify({'error': 'No image URL provided'}), 400

    try:
        ocr_result = process_image_for_ocr(image_url)
        extracted_text = display_text_data(ocr_result, image_url)
        return jsonify({'receipt_text': extracted_text})
    except Exception as e:
        print(f"Error in process_receipt: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/video')
def video():
  app_logger.info("Index page accessed")
  return render_template('video.html')

@app.route('/video_feed')
def video_feed():
  app_logger.info("Video feed accessed")
  return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
  app_logger.info("Capture route accessed")
  try:
      url, result = capture_and_upload()
      return jsonify({'url': url, 'result': result})
  except Exception as e:
      app_logger.error(f"Error in capture route: {str(e)}")
      return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)