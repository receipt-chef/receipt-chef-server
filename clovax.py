import requests
import os
from dotenv import load_dotenv
import uuid
import time
import json

load_dotenv()

class CompletionExecutor:
    def __init__(self):
        self._host = os.getenv("CLOVA_X_HOST")
        self._api_key = os.getenv("CLOVA_X_API_KEY")
        self._api_key_primary_val = os.getenv("CLOVA_X_API_KEY_PRIMARY_VAL")
        self._request_id = str(uuid.uuid4())

        if not self._host:
            raise ValueError("CLOVA_X_HOST is not set. Check your environment variables.")
        print(f"Clova X Host URL: {self._host}")

    def execute(self, text_data):
        print("CLOVA X 에게 보내는 데이터", text_data)
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        request_data = {
            'messages': [{"role": "system", "content": "당신은 영수증을 분석하는 AI 어시스턴트입니다. 영수증 데이터를 보고 일주일치 식단을 만들어주세요."}, 
                         {"role": "user", "content": text_data}],
            "topP" : 0.8,
            "topK" : 5,
            "maxTokens" : 1024,
            "temperature" : 0.5,
            "repeatPenalty" : 5.0,
            "stopBefore" : [ ],
            "includeAiFilters" : True,
            "seed" : 0
        }

        response = requests.post(
            f"{self._host}/testapp/v1/chat-completions/HCX-003",
            headers=headers,
            json=request_data,
            stream=True
        )

        lines = list(response.iter_lines())
        processed_text = None

        for i in range(len(lines) - 1, 0, -1):
            line = lines[i].decode("utf-8")
            if 'data:' in line and 'event:result' in lines[i - 1].decode("utf-8"):
                data_start = line.find("data:") + 5
                processed_text = line[data_start:].strip()
                break

        print("최종 추출된 데이터:", processed_text)
        return processed_text

completion_executor = CompletionExecutor()
