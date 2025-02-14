# 진료지침 데이터 크롤링

> API 라이센스 제도가 있기는 하지만, 영국 외부에서는 유료이므로 크롤링으로 진행
> 참고:
> [https://www.nice.org.uk/about/what-we-do/nice-syndication-api#available-content](https://www.nice.org.uk/about/what-we-do/nice-syndication-api#available-content)
> [https://www.nice.org.uk/guidance/published](https://www.nice.org.uk/guidance/published)

## 사용법

### Docker 사용 (고정된 설정 사용 시 권장. Docker에는 .env가 들어가지 않음. Dockerfile의 환경변수 또는 실행 명령어로 설정.)

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
  -e MAX_CONCURRENT=5 \
  -e TYPE=Guidance \
  -e GUIDANCE_PROGRAMME="Clinical guidelines" \
  guidance-crawler
```

### 로컬 실행 (.env는 환경변수보다 우선 적용 됨. 설정 바꿔 가며 로컬 테스트 시 권장)

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

- 결과 파일명 형식: `guidance_{type}_{guidance-programme}_{from_date}_{to_date}.csv` (설정 안 된 옵션은 포함 X)
- 로그 파일명 형식: `crawl_guidance_YYYYMMDDHHMMSS.log`

## 검색 파라미터

- search_query: 검색어
- from: 시작 날짜
- to: 종료 날짜
- type: 유형
  - Guidance
  - NICE advice
  - Quality standard
- guidance_programme: 진료지침 프로그램
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
- result_per_page: 페이지당 결과 수
