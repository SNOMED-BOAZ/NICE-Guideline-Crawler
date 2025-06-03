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
ENV RESULT_PER_PAGE="9999"

# 볼륨 설정
VOLUME ["/app/output", "/app/logs"]

# ENTRYPOINT와 CMD 설정
# ENTRYPOINT는 항상 실행되는 명령이고, CMD는 기본 인자로 사용됨
ENTRYPOINT ["python", "main.py"]
# CMD는 기본값으로 빈 배열을 제공하여 인자가 없을 때 그냥 main.py가 실행되도록 함
CMD []