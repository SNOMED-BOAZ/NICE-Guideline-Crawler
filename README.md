# 진료지침 데이터 크롤링

> API 라이센스 제도가 있기는 하지만, 영국 외부에서는 유료이므로 크롤링으로 진행
> 참고:
> [https://www.nice.org.uk/about/what-we-do/nice-syndication-api#available-content](https://www.nice.org.uk/about/what-we-do/nice-syndication-api#available-content)
> [https://www.nice.org.uk/guidance/published](https://www.nice.org.uk/guidance/published)

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
- sort: 정렬 방식 [Title, Date]
- result_per_page: 페이지당 결과 수
- page: 페이지 번호
