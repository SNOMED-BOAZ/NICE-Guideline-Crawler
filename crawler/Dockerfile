# 베이스 이미지로 Python 3.11 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 Python 패키지 설치를 위한 파일 복사
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY *.py ./

# 필요한 디렉토리 생성
RUN mkdir -p output logs

# 환경 변수 설정
ENV MAX_RETRIES="5"
ENV MAX_CONCURRENT="15"
ENV LOG_LEVEL="INFO"
ENV FROM_DATE="2000-01-01"
ENV TO_DATE=""
ENV TYPE=""
ENV PROGRAMME=""
ENV RESULT_PER_PAGE="9999"
ENV SEARCH_QUERY=""

# 볼륨 설정
VOLUME ["/app/output", "/app/logs"]

# 실행 명령
CMD ["python", "main.py"]