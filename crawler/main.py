import logging
import os
import datetime
from dotenv import load_dotenv
from crawler import GuidanceCrawler
import asyncio
import pandas as pd
from typing import List, Dict, Optional

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
    
    return {
        "max_retries": get_env_int("MAX_RETRIES", 3),
        "max_concurrent": get_env_int("MAX_CONCURRENT", 5),
        "search_params": {
            "from_date": get_env_str("FROM_DATE", "2000-01-01"),
            "to_date": get_env_str("TO_DATE", today),
            "type": get_env_str("TYPE"),
            "guidance_programme": get_env_str("GUIDANCE_PROGRAMME"),
            "sort": get_env_str("SORT"),
            "result_per_page": get_env_int("RESULT_PER_PAGE", 15)
        }
    }

def save_results(results: List[Dict], params: Dict, logger: logging.Logger) -> None:
    """크롤링 결과를 CSV 파일로 저장합니다."""

    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not results:
        logger.warning("No results to save")
        return
        
    try:
        # 결과를 DataFrame으로 변환
        df = pd.DataFrame(results)
        
        # 파일명 생성 (지정된 순서대로)
        parts = ['guidance']
        for key in ['type', 'guidance_programme', 'from_date', 'to_date']:
            if params.get(key):
                parts.append(str(params[key]).replace(' ', '-'))
        
        if len(parts) == 1:
            parts.append('all')
            
        filename = '_'.join(parts) + '.csv'
        output_path = os.path.join(output_dir, filename)
        
        # CSV 파일로 저장
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Total {len(results)} guidance records saved to {output_path}")
        
    except Exception as e:
        logger.error(f"Error occurred while saving results: {e}")

async def main():
    # 초기화
    logger = init_logger()
    config = load_config()
    
    # 설정값 출력
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
    logger.info(f"- 페이지당 결과 수: {search_params['result_per_page']}")
    logger.info("\n=====================================\n")
    
    # 크롤러 생성
    crawler = GuidanceCrawler(
        logger=logger,
        max_retries=config["max_retries"],
        max_concurrent=config["max_concurrent"]
    )
    
    try:
        # 크롤링 실행
        results = await crawler.crawl_and_save_async(config["search_params"])
        
        # 결과 저장
        save_results(results, config["search_params"], logger)
        
    except Exception as e:
        logger.error(f"Error occurred while crawling: {e}")

if __name__ == "__main__":
    asyncio.run(main())

