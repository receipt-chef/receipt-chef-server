# 영수증 셰프👨‍🍳🧾 : 장은 네가 봐, 식단은 내가 짜줄게
NIPA-NAVER 플랫폼 Tech 교육 중 진행한 프로젝트입니다.
<br/>

| 개인화된 식단 추천 서비스로 건강한 식습관을 형성하고, 질병과 기호에 맞는 식단, 조리법을 추천합니다.
- 배포 URL : https://prd-web.appspia.kr/
    - Test ID : test@gmail.com
    - Test PW : 0000

<br>

## 프로젝트 소개 📝
**영수증 셰프👨‍🍳🧾**는 사용자가 보유한 식재료를 기반으로 일주일치 식단을 생성하는 웹 서비스입니다. 
<br/>
마트 영수증을 통해 사용 가능한 재료를 분석하여 추가 구매 없이 활용할 수 있는 레시피를 제공함으로써 음식물 낭비를 줄이고, 사용자 맞춤형 식단 추천을 통해 더 건강한 식생활을 돕는 것을 목표로 합니다.


1. **재료 기반 레시피 추천**
   - 마트 영수증에서 재료를 추출.
   - 추가 구매 없이 기존 재료로 활용 가능한 레시피를 제공하여 음식물 낭비를 최소화.

2. **맞춤형 식단 제공**
   - 알레르기, 건강 상태, 비건 여부 등 사용자 식단 선호사항 분석.
   - 사용자 요구에 맞춘 일주일치 식단 제공.

3. **OCR 기반 데이터 추출**
   - **CLOVA OCR**을 사용하여 업로드된 영수증 이미지에서 세부 정보 추출.

4. **AI 기반 식단 계획**
   - **CLOVA X AI**를 활용하여 추출된 데이터를 분석하고 지능형 식단 추천 생성.

<br>

## 개발 환경 📝

- 프론트 : HTML, CSS, JavaScript
- 백엔드 : Flask, MySQL
- 인프라 : Naver Cloud, Object Storage, Naver Cloud Developer Tools
- AI : Clova X, Clova OCR
<br>
<br>

## 서비스 아키텍처 📝
###  🏛 Infra - Naver Cloud
<img src="https://github.com/user-attachments/assets/c9ec06b5-768d-40a5-bee2-5137ec7243bc" width="90%"/>

### 1. Developer Tools
- SourceCommit, SourceBuild, SourceDeploy, SourcePipeline 
- 파이프라인 작성하여 CI/CD로 배포 자동화 구축
<br>

### 2. AI
- 네이버 클라우드의 API Gateway를 사용해 Clova OCR, Clova X 연동
- Object Storage에 저장된 마트 영수증을 Clova OCR로 텍스트 추출
- "OCR 추출 텍스트 + 프롬프트" 로 Clova X 에게 요일별 식단 추천받기
<br>

### 3. 로드밸런서
- web1, web2로 서버 이중화 구성하여 로드밸런서로 부하 분산
- 로드밸런싱 알고리즘 : 라운드 로빈 알고리즘 + sticky session
<br>

### 4. 보안
- 서버를 프라이빗에 구축해 개발자는 SSL VPN을 사용하여 접근
- Security Monitoring (IDS, IPS, Anti-Virus) 사용하여 모니터링

<br>

## 페이지별 기능 📝

### 🎥 메인, 회원가입, 로그인
- 서비스 접속 초기화면입니다.
- 회원가입 시에 유저의 개인 음식 취향 및 질병을 등록합니다. 

<div style="display: flex; justify-content: center; gap: 20px;"><img src="https://github.com/user-attachments/assets/0d66f54f-3e3a-4aef-b52c-1330de1ba886" width="70%"/></div>

### 🎥 영수증 등록
- 마트 영수증 사진을 직접 촬영하거나, 갤러리에서 이미지를 등록합니다.
<div style="display: flex; justify-content: center; gap: 20px;"><img src="https://github.com/user-attachments/assets/81678710-81c1-464a-8ab4-0c232a135c52" width="70%"/></div>

### 🎥 식단 추출
- 개인 맞춤형 일주일 식단을 추천받을 수 있습니다.
<div style="display: flex; justify-content: center; gap: 20px;"><img src="https://github.com/user-attachments/assets/a343deb9-f3d0-4019-8ec6-1acc721efd08" width="70%"/></div>
