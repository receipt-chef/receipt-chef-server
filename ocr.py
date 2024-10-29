import os
import json
import requests
import boto3
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

CLOVA_API_URL = os.getenv("CLOVA_API_URL")
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY") 
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
REGION_NAME = os.getenv("REGION_NAME")
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION_NAME, endpoint_url=ENDPOINT_URL)

def process_image_for_ocr(image_key):
    try:
        s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=image_key)
        image_bytes = BytesIO(s3_object['Body'].read())

        headers = {
            'X-OCR-SECRET': CLOVA_API_KEY,
            'Content-Type': 'application/octet-stream'
        }
        response = requests.post(CLOVA_API_URL, headers=headers, data=image_bytes)

        if response.status_code == 200:
            return response.json()
        else:
            return {'error': 'Failed to process OCR', 'details': response.text}

    except Exception as e:
        return {'error': str(e)}

def display_text_data(ocr_data, image_file):
    try:
        # 이미지의 의미있는 텍스트 필드를 HTML로 반환
        text_data = ocr_data.get('images', [])[0].get('fields', [])
        result_text = ""
        for field in text_data:
            if field.get('inferConfidence', 0) > 0.9:  # 신뢰도가 높은 텍스트만 추출
                result_text += f"{field['inferText']}\n"
        if result_text:
            return result_text
        else:
            return f"{image_file}에서 유의미한 텍스트를 찾을 수 없습니다."
    except (KeyError, IndexError):
        return f"{image_file}에서 텍스트를 찾을 수 없습니다."