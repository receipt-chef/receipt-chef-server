from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, session
from database import get_receipt_links, register_user, authenticate_user
from ocr import process_image_for_ocr, display_text_data
from video import generate_frames, capture_and_upload
from dotenv import load_dotenv
from flask import Response
import boto3
import os

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

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
REGION_NAME = os.getenv("REGION_NAME")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION_NAME, endpoint_url=ENDPOINT_URL)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 업로드 폴더가 없으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def main():
    return render_template('index.html')

# 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        app.logger.info("Received form data: %s", request.form)

        member_nm = request.form.get('member_nm')
        member_email = request.form.get('member_email')
        member_pw = request.form.get('member_pw')
        member_gender = request.form.get('member_gender')
        member_age = int(request.form.get('member_age'))
        prefer_food_cnt = request.form.get('prefer_food_cnt')
        avoid_food_cnt = request.form.get('avoid_food_cnt')
        disease_yn = request.form.get('disease_yn')
        disease_cnt = request.form.get('disease_cnt')

        success, error = register_user(
            member_nm, member_email, member_pw, member_gender,
            member_age, prefer_food_cnt, avoid_food_cnt, disease_yn, disease_cnt
        )
        if success:
            flash("회원가입이 성공적으로 완료되었습니다!", "success")
            return redirect(url_for('login'))
        else:
            app.logger.error("Registration error: %s", error)
            flash(f"오류 발생: {error}", "danger")
    
    return render_template('signup.html')

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        authenticated, member_or_error = authenticate_user(username, password)
        if authenticated:
            session['user_id'] = member_or_error['member_no']
            return jsonify({"success": True, "userId": member_or_error['member_no']})
        else:
            return jsonify({"success": False, "error": "로그인 실패: 아이디 또는 비밀번호를 확인하세요."})
    
    return render_template('login.html')

# 홈 화면
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/get_receipts', methods=['GET'])
def get_receipts():
    user_id = request.args.get('userId')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    receipt_links = get_receipt_links(user_id)
    signed_urls = []
    for receipt_id, receipt_key in receipt_links:
        try:
            if receipt_key.startswith("https://"):
                receipt_key = receipt_key.split(BUCKET_NAME + "/")[-1]
            
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
        # Process image using Clova OCR to extract text data
        ocr_result = process_image_for_ocr(image_url)
        # Generate meal plan by sending OCR text to Clova X
        meal_plan = display_text_data(ocr_result)

        # Log and display the response for debugging
        print("Clova X Meal Plan Response:", meal_plan)

        return jsonify({'meal_plan': meal_plan})
    except Exception as e:
        app_logger.error(f"Error in process_receipt: {e}")
        return jsonify({'error': str(e)}), 500

# 사진 촬영
@app.route('/video')
def video():
  app_logger.info("Index page accessed")
  return render_template('video.html')

@app.route('/video_feed')
def video_feed():
  app_logger.info("Video feed accessed")
  return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
# def capture():
#   app_logger.info("Capture route accessed")
#   try:
#       url, result = capture_and_upload()
#       return jsonify({'url': url, 'result': result})
#   except Exception as e:
#       app_logger.error(f"Error in capture route: {str(e)}")
#       return jsonify({'error': str(e)}), 500
def capture():
    app_logger.info("Capture route accessed")
    try:
        image_data = request.json['image']  # 클라이언트로부터 base64 인코딩된 이미지 데이터를 받습니다.
        member_id = request.json['memberId']
        url, result = capture_and_upload(image_data, member_id)
        return jsonify({'url': url, 'result': result})
    except Exception as e:
        app_logger.error(f"Error in capture route: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)