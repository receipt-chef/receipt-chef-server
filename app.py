from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, session
from database import get_receipt_links, register_user, authenticate_user
from ocr import process_image_for_ocr, display_text_data
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from flask import Response
import boto3
import os
from video import video_bp
from meal import save_meal_plan, get_meal_plan
from requests.exceptions import RequestException, ConnectionError, HTTPError, Timeout
import json

app = Flask(__name__)

# .env 파일 로드
load_dotenv()

# 애플리케이션 로거 설정
import logging
from logging.handlers import RotatingFileHandler

# Register the Blueprint for video routes
app.register_blueprint(video_bp, url_prefix='/video')


# 파일 핸들러 (애플리케이션 로그용)
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)
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

app.secret_key = os.getenv("FLASK_SECRET_KEY")

ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
REGION_NAME = os.getenv("REGION_NAME")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION_NAME, endpoint_url=ENDPOINT_URL)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 메인 화면
@app.route('/')
def main():
    return render_template('index.html')

'''
회원 부분
'''
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
            flash("회원가입이 성공적으로 완료되었습니다!!", "success")
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

'''
홈 부분
'''
# 홈 화면
@app.route('/home')
def home():
    return render_template('home.html')

# 영수증 이미지 가져오는 함수
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

'''
카메라 부분
'''
# 이미지 업로드 함수
@app.route('/upload_image', methods=['POST'])
def upload_image():
    member_id = request.form.get('memberId')
    image = request.files.get('image')

    if not member_id or not image:
        app_logger.error("Missing member ID or image in request.")
        return jsonify({'error': 'Missing member ID or image in request'}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"captured_image_{timestamp}.jpg"

    image.save(filename)
    try:
        s3.upload_file(filename, BUCKET_NAME, filename)
        app_logger.info(f"Image uploaded successfully to Object Storage: {filename}")

        image_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': filename},
            ExpiresIn=3600
        )

        if insert_receipt(filename, member_id):
            result = "Image uploaded and receipt info saved"
            app_logger.info(result)
        else:
            result = "Image uploaded but failed to save receipt info"
            app_logger.warning(result)

    except Exception as e:
        app_logger.error(f"Error uploading image: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    return jsonify({'url': image_url, 'result': result})

# 영수증 정보 가져오는 함수
def insert_receipt(receipt_image_url, member_id):
    db_config = {
        'host': os.getenv('DB_HOST'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_NAME')
    }

    connection = None
    try:
        # Establish the database connection
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()

            # Check if member_id exists in MEMBER table
            check_member_query = "SELECT 1 FROM MEMBER WHERE member_no = %s"
            cursor.execute(check_member_query, (member_id,))
            if not cursor.fetchone():
                app_logger.error(f"Member ID {member_id} does not exist in MEMBER table.")
                return False

            # Insert query for the receipt
            insert_query = "INSERT INTO RECEIPT (receipt_file_path, member_no) VALUES (%s, %s)"
            cursor.execute(insert_query, (receipt_image_url, member_id))
            connection.commit()
            
            app_logger.info("Receipt info inserted successfully.")
            return True

    except Error as e:
        app_logger.error(f"Error inserting receipt info: {e}")
        return False

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

'''
식단 부분
'''
# OCR + CLOVA X 진행 함수
@app.route('/process_receipt', methods=['POST'])
def process_receipt():
    image_url = request.json.get('image_url')
    if not image_url:
        return jsonify({'error': 'No image URL provided'}), 400

    try:
        # Step 1: OCR 진행
        app_logger.info(f"Processing image for OCR: {image_url}")
        ocr_result = process_image_for_ocr(image_url)

        if 'error' in ocr_result:
            return jsonify({'error': ocr_result['error']}), 500

        # Step 2: CLOVA X 진행
        meal_plan = display_text_data(ocr_result)

        if not meal_plan:
            return jsonify({'error': 'Meal plan missing in server response.'}), 500

        # Step 3: 최종 응답값 도출
        meal_plan_id = save_meal_plan(meal_plan)

        return jsonify({'meal_plan_id': meal_plan_id})

    except (RequestException, ConnectionError, HTTPError, Timeout) as e:
        app_logger.error(f"Error processing receipt due to connection issue: {e}")
        return jsonify({'error': 'Failed to connect to the service. Please check your network and try again.'}), 500
    except IndexError as e:
        app_logger.error(f"Error processing receipt: {e}")
        return jsonify({'error': 'Unexpected response format from OCR processing.'}), 500
    except Exception as e:
        app_logger.error(f"Error processing receipt: {e}")
        return jsonify({'error': str(e)}), 500

# 식단 화면
@app.route('/meal/<meal_plan_id>', methods=['GET'])
def meal_page(meal_plan_id):
    meal_plan_data = get_meal_plan(meal_plan_id)
    app_logger.info(f"Retrieved meal plan: {meal_plan_data}")

    # meal_plan_data가 문자열일 경우 JSON 파싱
    if isinstance(meal_plan_data, str):
        try:
            meal_plan_data = json.loads(meal_plan_data)
        except json.JSONDecodeError:
            app_logger.error("Failed to decode meal plan JSON.")
            return "Invalid meal plan data", 500

    # message 안의 content 가져오기
    meal_plan_content = meal_plan_data.get('message', {}).get('content', "")
    if not meal_plan_content:
        return "Meal plan content missing in server response.", 404

    return render_template('meal.html', meal_plan=meal_plan_content)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)