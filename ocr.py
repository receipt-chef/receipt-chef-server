import os
import json
import time
import uuid
import requests
from io import BytesIO
from dotenv import load_dotenv
from io import BytesIO
from clovax import completion_executor


# 환경 변수 로드
load_dotenv()
CLOVA_API_URL = os.getenv("CLOVA_API_URL")
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")

# CLOVA OCR 이용 함수
def process_image_for_ocr(image_url):
    print(f"Image URL: {image_url}")
    try:
        print("OCR 처리 시작 중...")

        # 프리사인드 URL에서 이미지 가져오기
        response = requests.get(image_url)
        if response.status_code != 200:
            print(f"URL에서 이미지 가져오기 실패. 상태 코드: {response.status_code}")
            return {'error': 'OCR용 이미지 가져오기 실패', 'details': response.text}

        image_bytes = BytesIO(response.content)
        print("URL에서 이미지 바이트 성공적으로 읽음.")
        

        # OCR API 요청 헤더 설정
        headers = {
            "X-OCR-SECRET": CLOVA_API_KEY
        }
        
        # OCR API 요청 메타데이터 설정
        ocr_data = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "lang": "ko",
            "images": [{"format": "jpg", "name": "sample.jpg"}]  # 이미지 형식에 맞게 format 설정
        }

        # multipart/form-data 형식으로 이미지 및 메타데이터 전송
        files = {
            'file': ('sample.jpg', image_bytes, 'application/octet-stream'),  # 이미지 파일
            'message': (None, json.dumps(ocr_data), 'application/json')       # 메타데이터 JSON
        }

        # OCR API에 이미지와 메타데이터 전송
        ocr_response = requests.post(
            CLOVA_API_URL,
            headers=headers,
            files=files
        )

        print(f"서버에 {image_url} 요청 했습니다")
        print(f"OCR 요청 상태 코드: {ocr_response.status_code}")
        
        if ocr_response.status_code == 200:
            print("OCR 처리 성공.")
            return ocr_response.json()
        else:
            print("OCR 처리 실패.")
            print(f"응답 세부사항: {ocr_response.text}")
            return {'error': 'OCR 처리 실패', 'details': ocr_response.text}

    except Exception as e:
        print(f"process_image_for_ocr 함수 오류: {e}")
        return {'error': str(e)}


# OCR로 추출한 데이터에서 구매 품목만 파싱하여 출력하는 함수
def display_text_data(ocr_data):
    text_data = ""
    for field in ocr_data.get('images', [])[0].get('fields', []):
        if field.get('inferConfidence', 0) > 0.9:
            text_line = field.get('inferText', '').strip()
            if text_line and not any(char.isdigit() for char in text_line):
                text_data += f"{text_line}\n"

    if text_data:
        print("OCR TEXT DATA")
        print(text_data)
        
        prompt = f"{text_data}\n 이 항목들을 보고 요일별로 저녁 식단과 조리방법을 구체적으로 작성해서 알려줘"
        clova_x_response = completion_executor.execute(prompt)
        return clova_x_response
    else:
        return "유의미한 구매 품목을 찾을 수 없습니다."