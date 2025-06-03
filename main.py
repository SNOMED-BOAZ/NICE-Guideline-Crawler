import logging
import os
import datetime
import argparse
from dotenv import load_dotenv
from crawler import GuidanceCrawler
import asyncio
import pandas as pd
from typing import List, Dict, Optional
from type_programme import type_programme
import random

def calculate_date_range(days_ago: int = None) -> tuple:
    """
    날짜 범위를 계산하는 함수
    
    Args:
        days_ago (int, optional): 오늘로부터 며칠 전까지 검색할지 지정
        
    Returns:
        tuple: (시작일, 종료일) 형식의 튜플
    """
    today = datetime.datetime.now()
    if days_ago is not None:
        from_date = (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
    else:
        from_date = "2000-01-01"  # 기본값
    
    to_date = today.strftime("%Y-%m-%d")
    return from_date, to_date

def parse_arguments():
    """
    명령줄 인자를 파싱하는 함수
    
    Returns:
        argparse.Namespace: 파싱된 인자들
    """
    parser = argparse.ArgumentParser(description="NICE 가이드라인 크롤러")
    parser.add_argument("days_ago", nargs="?", type=int, default=None,
                       help="검색 시작일(오늘로부터 며칠 전)")
    return parser.parse_args()

def init_logger():
    """로깅 설정 초기화"""
    logger = logging.getLogger("crawl_guidance")
    
    # logs 디렉토리가 없으면 생성
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # 로그 레벨 설정 (빈 문자열일 경우 INFO 사용)
    log_level = os.getenv("LOG_LEVEL", "").strip()
    if not log_level:
        log_level = "INFO"
        
    logging.basicConfig(
        filename=f'logs/crawl_guidance_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.log',
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔에도 로그 출력을 위한 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        '%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(console_handler)
    
    return logger

def load_config():
    """설정을 로드합니다."""
    load_dotenv(override=True)
    
    # 명령줄 인자 파싱
    args = parse_arguments()
    
    # 날짜 범위 계산
    from_date, to_date = calculate_date_range(args.days_ago)
    
    def get_env_int(key: str, default: int) -> int:
        """정수형 환경 변수를 가져옵니다."""
        value = os.getenv(key, '').strip()
        return int(value) if value else default
    
    # 기본 설정 로드
    config = {
        "max_retries": get_env_int("MAX_RETRIES", 3),
        "max_concurrent": get_env_int("MAX_CONCURRENT", 5),
        "result_per_page": get_env_int("RESULT_PER_PAGE", 9999),
        "search_params": {
            "from_date": from_date,
            "to_date": to_date,
        }
    }
    
    return config

def logging_config(logger: logging.Logger, config: dict) -> None:
    """로깅 설정을 구성하고 설정값을 출력합니다."""
    logger.info("\n============ Configuration ============")
    logger.info("\n[기본 설정]")
    logger.info(f"- 최대 재시도 횟수: {config['max_retries']}")
    logger.info(f"- 동시 요청 수: {config['max_concurrent']}")
    logger.info(f"- 결과 페이지 수: {config['result_per_page']}")
    logger.info("\n[검색 파라미터]")
    search_params = config['search_params']
    logger.info(f"- 검색 시작일: {search_params['from_date']}")
    logger.info(f"- 검색 종료일: {search_params['to_date']}")
    
    logger.info("\n=====================================\n")

def handle_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    URL을 기준으로 중복 데이터를 처리하는 함수
    
    Args:
        df (pd.DataFrame): 원본 데이터프레임
        
    Returns:
        pd.DataFrame: 중복이 처리된 데이터프레임
    """
    # 중복 데이터 확인
    duplicated_urls = df[df.duplicated(subset=['url'], keep=False)]
    logger = logging.getLogger("crawl_guidance")
    logger.info(f"중복된 URL 개수: {len(duplicated_urls['url'].unique())}")
    logger.info(f"중복 포함 전체 레코드 수: {len(duplicated_urls)}")
    
    def combine_values(x):
        # 각 컬럼별로 고유값을 리스트로 변환
        if x.name in ['type', 'guidance_programme', 'advice_programme']:
            # NaN 값 제거 후 고유값 추출
            values = list(x.dropna().unique())
            return values if values else None
        # 나머지 컬럼은 첫번째 값 반환
        return x.iloc[0]
    
    # URL 기준으로 그룹화하여 데이터 병합
    merged_df = df.groupby('url').agg(combine_values).reset_index()
    
    logger.info(f"병합 전 레코드 수: {len(df)}")
    logger.info(f"병합 후 레코드 수: {len(merged_df)}")
    
    return merged_df

def save_results(results: List[Dict], params: Dict, logger: logging.Logger) -> None:
    """크롤링 결과를 CSV 파일로 저장"""
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not results:
        logger.warning("No results to save")
        return
        
    try:
        # 결과를 DataFrame으로 변환
        df = pd.DataFrame(results)
        
        # 중복 데이터 처리
        df = handle_duplicates(df)
        
        # 파일명 생성 (지정된 순서대로)
        parts = ['guidance']
        
        # 날짜 추가
        for key in ['type', 'guidance_programme', 'advice_programme', 'from_date', 'to_date']:
            if params.get(key):
                # 공백을 -로 대체
                value = str(params[key]).replace(' ', '-')
                parts.append(value)
        
        if len(parts) == 1:
            parts.append('all')
            
        filename = '_'.join(parts) + '.csv'
        output_path = os.path.join(output_dir, filename)
        
        # CSV 파일로 저장
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Total {len(results)} guidance records saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error occurred while saving results: {e}")

def _get_random_delay() -> float:
    """0.5초에서 0.8초 사이의 랜덤한 딜레이 시간을 반환"""
    return random.uniform(0.5, 0.8)

async def crawl_by_type_and_programme(logger: logging.Logger, config: dict) -> List[Dict]:
    """
    각 타입과 프로그램별로 크롤링을 수행하는 함수
    
    Args:
        logger: 로깅 객체
        config: 설정 딕셔너리
        
    Returns:
        List[Dict]: 전체 크롤링 결과
    """
    all_results = []
    tasks = []

    # 기본 파라미터에 result_per_page 추가
    base_params = config['search_params'].copy()
    base_params['result_per_page'] = config['result_per_page']

    for type_dict in type_programme['type']:
        for type_name, programmes in type_dict.items():
            params = base_params.copy()  # 기본 파라미터를 복사
            params['type'] = type_name

            if type_name == 'Guidance':
                for programme in programmes:
                    # 각 요청 사이에 랜덤 지연 추가
                    await asyncio.sleep(_get_random_delay())
                    current_params = params.copy()
                    current_params['guidance_programme'] = programme
                    crawler = GuidanceCrawler(
                        logger=logger,
                        max_retries=config['max_retries'],
                        max_concurrent=config['max_concurrent']
                    )
                    tasks.append(crawler.crawl_async(current_params))
                    logger.info(f"크롤링 작업 추가: {type_name} - {programme}")

            elif type_name == 'NICE advice':
                for programme in programmes:
                    # 각 요청 사이에 랜덤 지연 추가
                    await asyncio.sleep(_get_random_delay())
                    current_params = params.copy()
                    current_params['advice_programme'] = programme
                    crawler = GuidanceCrawler(
                        logger=logger,
                        max_retries=config['max_retries'],
                        max_concurrent=config['max_concurrent']
                    )
                    tasks.append(crawler.crawl_async(current_params))
                    logger.info(f"크롤링 작업 추가: {type_name} - {programme}")

            elif type_name == 'Quality standard':
                # 각 요청 사이에 랜덤 지연 추가
                await asyncio.sleep(_get_random_delay())
                current_params = params.copy()
                crawler = GuidanceCrawler(
                    logger=logger,
                    max_retries=config['max_retries'],
                    max_concurrent=config['max_concurrent']
                )
                tasks.append(crawler.crawl_async(current_params))
                logger.info(f"크롤링 작업 추가: {type_name}")

    # 모든 크롤링 작업을 비동기로 실행
    results = await asyncio.gather(*tasks)
    
    # 결과 합치기
    for result in results:
        all_results.extend(result)

    return all_results

async def main():
    """
    메인 실행 함수
    """
    # 초기화
    logger = init_logger()
    config = load_config()
    
    # 로깅 설정
    logging_config(logger, config)
    
    try:
        logger.info("크롤링 시작")
        
        # 크롤링 실행
        results = await crawl_by_type_and_programme(logger, config)
        
        if results:
            # 결과 저장
            save_results(results, config['search_params'], logger)
            logger.info(f"총 {len(results)}개의 문서가 수집되었습니다.")
        else:
            logger.warning("수집된 결과가 없습니다.")
            
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

