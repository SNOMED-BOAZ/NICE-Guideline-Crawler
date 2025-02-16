# 진료지침 데이터 크롤링

> 웹 자체가 사실상 공개 API와 같은 것 같음
> [https://www.nice.org.uk/guidance/published](https://www.nice.org.uk/guidance/published)

## 수집 정보

- title: 가이던스 문서의 제목
- url: 가이던스 문서의 웹페이지 URL
- pdf_url: 가이던스 문서의 PDF URL
- reference: 가이던스 문서의 참조 코드
- published_date: 최초 발행일 (DD MONTH YYYY)
- last_updated: 마지막 업데이트 일자 (DD MONTH YYYY)

## 사용법

### 스크립트 사용

```bash
chmod +x start_crawl.sh

./start_crawl.sh
```

### Docker 사용 (Docker에는 .env가 들어가지 않음. Dockerfile의 환경변수 또는 실행 명령어로 설정.)

1. Docker 이미지 빌드

```bash
# crawler 디렉토리로 이동
cd crawler

# 이미지 빌드
docker build -t guidance-crawler .

# 컨테이너 실행 (현재 디렉토리 기준으로 볼륨 마운트)
docker run -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs guidance-crawler

# 환경 변수 설정과 함께 실행
docker run -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs \
  -e TYPE=Guidance \
  -e PROGRAMME="Clinical guidelines" \
  guidance-crawler
```

### 로컬 실행 (.env는 환경변수보다 우선 적용 됨)

> Python 3.11.7

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env

# 3. 실행
python main.py
```

## 결과물

`output`: 크롤링 결과, `logs`: 로그

- 결과 파일명 형식: `guidance_{type}_{programme}_{from_date}_{to_date}.csv` (설정 안 된 옵션은 포함 X)
- 로그 파일명 형식: `crawl_guidance_YYYYMMDDHHMMSS.log`

## 검색 파라미터

- search_query: 검색어
- from_date: 시작 날짜
- to_date: 종료 날짜
- type: 유형
  - Guidance
  - NICE advice
  - Quality standard
- programme: 프로그램 (type에 따라 자동으로 적절한 필드에 할당)
  - Guidance
    - Antimicrobial prescribing guidelines
    - Cancer service guideline
    - Clinical guidelines
    - COVID-19 rapid guideline
    - Diagnostics guidance
    - Health technology evaluations
    - Highly specialised technologies guidance
    - Interventional procedures guidance
    - Medical technologies guidance
    - Medicines practice guideline
    - NICE guidelines
    - Public health guidelines
    - Safe staffing guideline
    - Social care guidelines
    - Technology appraisal guidance
  - NICE advice
    - Evidence summaries
    - Medtech innovation briefings
- result_per_page: 페이지당 결과 수
