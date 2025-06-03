# 진료지침 데이터 크롤링

> 웹 자체가 사실상 공개 API와 같은 것 같음
> [https://www.nice.org.uk/guidance/published](https://www.nice.org.uk/guidance/published)

## 수집 정보

- title: 가이던스 문서의 제목
- url: 가이던스 문서의 웹페이지 URL
- contents: 가이던스 문서의 텍스트 콘텐츠  (json array 형식, [{title: str, url: str, content: str}, ...])
- type: 가이던스 문서의 유형 (여러 개 지닌 문서들이 있어 배열로 저장)
- guidance_programme: Guidance 프로그램 (여러 개 지닌 문서들이 있어 배열로 저장)
- advice_programme: NICE advice 프로그램 (여러 개 지닌 문서들이 있어 배열로 저장)
- reference: 가이던스 문서의 참조 코드
- published_date: 최초 발행일 (DD MONTH YYYY)
- last_updated: 마지막 업데이트 일자 (DD MONTH YYYY)

## 사용법

### Docker

```bash
docker build -t crawler .

# 30일 전까지의 문서 수집 (숫자 변경 가능)
docker run -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs crawler 30

# 전체 문서 수집
docker run -v $(pwd)/output:/app/output -v $(pwd)/logs:/app/logs crawler
```

### Python 실행

```bash
# 30일 전까지의 문서 수집 (숫자 변경 가능)
python main.py 30

# 전체 문서 수집
python main.py
```

### 로컬 실행을 위한 환경 설정

> Python 3.11.7

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 환경 변수 설정 (선택사항)
cp .env.example .env
```

## 결과물

`output`: 크롤링 결과, `logs`: 로그

- 결과 파일명 형식: `guidance_{type}_{programme}_{from_date}_{to_date}.csv` (설정 안 된 옵션은 포함 X)
- 로그 파일명 형식: `crawl_guidance_YYYYMMDDHHMMSS.log`
