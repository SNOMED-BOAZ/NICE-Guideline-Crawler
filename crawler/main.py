import logging
import os
import datetime
from dotenv import load_dotenv
from crawler import GuidanceCrawler
import asyncio
import pandas as pd
from typing import List, Dict, Optional
from type_programme import type_programme

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
    """환경 설정을 로드합니다."""
    load_dotenv(override=True)
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    def get_env_int(key: str, default: int) -> int:
        """정수형 환경 변수를 가져옵니다."""
        value = os.getenv(key, '').strip()
        return int(value) if value else default
    
    def get_env_str(key: str, default: str = None) -> Optional[str]:
        """문자열 환경 변수를 가져옵니다."""
        value = os.getenv(key, '').strip()
        return value if value else default
    
    # 기본 설정 로드
    config = {
        "max_retries": get_env_int("MAX_RETRIES", 3),
        "max_concurrent": get_env_int("MAX_CONCURRENT", 15),
        "search_params": {
            "from_date": get_env_str("FROM_DATE", "2000-01-01"),
            "to_date": get_env_str("TO_DATE", today),
            "type": get_env_str("TYPE", ""),
            "guidance_programme": get_env_str("GUIDANCE_PROGRAMME", ""),
            "advice_programme": get_env_str("ADVICE_PROGRAMME", ""),
            "sort": get_env_str("SORT"),
            "result_per_page": get_env_int("RESULT_PER_PAGE", 9999)
        }
    }
    
    return config

def logging_config(logger: logging.Logger, config: dict) -> None:
    """로깅 설정을 구성하고 설정값을 출력합니다."""
    logger.info("\n============ Configuration ============")
    logger.info("\n[기본 설정]")
    logger.info(f"- 최대 재시도 횟수: {config['max_retries']}")
    logger.info(f"- 동시 요청 수: {config['max_concurrent']}")
    
    logger.info("\n[검색 파라미터]")
    search_params = config['search_params']
    logger.info(f"- 검색 시작일: {search_params['from_date']}")
    logger.info(f"- 검색 종료일: {search_params['to_date']}")
    logger.info(f"- Type: {search_params['type'] or ''}")
    logger.info(f"- Guidance Programme: {search_params['guidance_programme'] or ''}")
    logger.info(f"- Advice Programme: {search_params['advice_programme'] or ''}")
    
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

    # 각 타입에 대해 반복
    for type_dict in type_programme['type']:
        for type_name, programmes in type_dict.items():
            # 기본 파라미터 설정
            base_params = config['search_params'].copy()
            base_params['type'] = type_name

            if type_name == 'Guidance':
                # Guidance 타입의 각 프로그램에 대해 크롤링
                for programme in programmes:
                    params = base_params.copy()
                    params['guidance_programme'] = programme
                    crawler = GuidanceCrawler(
                        logger=logger,
                        max_retries=config['max_retries'],
                        max_concurrent=config['max_concurrent']
                    )
                    tasks.append(crawler.crawl_async(params))
                    logger.info(f"크롤링 작업 추가: {type_name} - {programme}")

            elif type_name == 'NICE advice':
                # NICE advice 타입의 각 프로그램에 대해 크롤링
                for programme in programmes:
                    params = base_params.copy()
                    params['advice_programme'] = programme
                    crawler = GuidanceCrawler(
                        logger=logger,
                        max_retries=config['max_retries'],
                        max_concurrent=config['max_concurrent']
                    )
                    tasks.append(crawler.crawl_async(params))
                    logger.info(f"크롤링 작업 추가: {type_name} - {programme}")

            elif type_name == 'Quality standard':
                # Quality standard는 프로그램이 없으므로 바로 크롤링
                params = base_params.copy()
                crawler = GuidanceCrawler(
                    logger=logger,
                    max_retries=config['max_retries'],
                    max_concurrent=config['max_concurrent']
                )
                tasks.append(crawler.crawl_async(params))
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

