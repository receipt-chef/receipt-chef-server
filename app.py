from flask import Flask, request, render_template, redirect, url_for
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
    # Fetch receipt image links from the database
    receipt_links = get_receipt_links()  # Returns a list of (receipt_id, receipt_key)
    signed_urls = []
    for receipt_id, receipt_key in receipt_links:
        # Check if receipt_key is a full URL
        if receipt_key.startswith("http"):
            url = receipt_key
        else:
            # Generate a presigned URL for S3 object
            try:
                url = s3.generate_presigned_url('get_object',
                                                Params={'Bucket': BUCKET_NAME, 'Key': receipt_key},
                                                ExpiresIn=3600,
                                                HttpMethod='GET')
            except Exception as e:
                print(f"Error generating presigned URL for {receipt_key}: {e}")
                url = None
        signed_urls.append((receipt_id, url))
    return {'receipt_links': signed_urls}


@app.route('/receipt/<receipt_id>')
def view_receipt(receipt_id):
    try:
        s3_key = f"receipts/{receipt_id}"
        ocr_result = process_image_for_ocr(s3_key)
        extracted_text = display_text_data(ocr_result, receipt_id)
        return render_template('receipt_details.html', receipt_id=receipt_id, ocr_result=extracted_text)
    except Exception as e:
        return render_template('error.html', error=str(e))
    
    

if __name__ == '__main__':
    app.run(debug=True)