from flask import Flask, request, render_template, redirect, url_for, jsonify
import boto3
import os
import uuid
from database import get_receipt_links
from ocr import process_image_for_ocr, display_text_data


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
    
    

if __name__ == '__main__':
    app.run(debug=True)