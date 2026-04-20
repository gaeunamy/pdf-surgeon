# 1. 가볍고 빠른 파이썬 3.11 버전 사용
FROM python:3.11-slim

# 2. 작업할 폴더를 /app으로 지정
WORKDIR /app

# 3. 라이브러리 목록표를 먼저 복사하고 설치 (이렇게 해야 도커가 빠름)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 우리 프로젝트의 모든 코드와 폰트(.env 포함)를 복사
COPY . .

# 5. FastAPI(8000번)와 Streamlit(8501번)이 사용할 포트 구멍 뚫어주기
EXPOSE 8000 8501

# 6. 도커를 실행할 때 기본으로 켤 명령어 (FastAPI 서버 가동)
CMD uvicorn app.api:app --host 0.0.0.0 --port 8000 & streamlit run app/ui.py --server.port 8501 --server.address 0.0.0.0