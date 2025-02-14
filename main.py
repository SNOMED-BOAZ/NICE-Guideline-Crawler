import logging
from crawler import GuidanceCrawler
import random
import datetime
import os
from dotenv import load_dotenv
from typing import Dict, Any

def init_logger():
    """로깅 설정 초기화"""
    logger = logging.getLogger("crawl_guidance")
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logger

def load_config() -> Dict[str, Any]:
    """
    config 설정
    우선순위: .env > 환경변수 > 기본값
    """
    # 기본값 설정
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # .env 있는 경우 로드
    load_dotenv(override=True)  # 환경변수보다 .env가 우선

    config = {
        "max_retries": int(os.getenv("MAX_RETRIES", 3)),
        "search_params": {
            "from": os.getenv("FROM_DATE", "2000-01-01"),
            "to": os.getenv("TO_DATE", today),
            "type": os.getenv("TYPE", None),
            "guidance_programme": os.getenv("GUIDANCE_PROGRAMME", None),
            "sort": os.getenv("SORT", None),
            "result_per_page": int(os.getenv("RESULT_PER_PAGE", 9999)),  # 웹사이트에서 All 선택시 9999로 지정됨
            "page": os.getenv("PAGE", None)
        }
    }

    # None 문자열을 실제 None으로 변환
    for key in config["search_params"]:
        if config["search_params"][key] == "None":
            config["search_params"][key] = None

    return config

def main():
    # 로거 설정
    logger = init_logger()
    logger.info("Starting guidance crawler")

    # 설정 로드
    config = load_config()
    
    # 설정값 예쁘게 출력
    logger.info("\n============ Loaded configuration ============")
    logger.info("\n[기본 설정]")
    logger.info(f"- 최대 재시도 횟수: {config['max_retries']}")
    
    logger.info("\n[검색 파라미터]")
    search_params = config['search_params']
    logger.info(f"- 검색 시작일: {search_params['from']}")
    logger.info(f"- 검색 종료일: {search_params['to']}")
    logger.info(f"- Type: {search_params['type'] or '전체'}")
    logger.info(f"- Guidance Programme: {search_params['guidance_programme'] or '전체'}")
    logger.info(f"- 정렬 기준: {search_params['sort'] or '기본'}")
    logger.info(f"- 페이지당 결과 수: {search_params['result_per_page']}")
    logger.info(f"- 페이지 번호: {search_params['page'] or '1'}")
    logger.info("\n===========================================\n")
    
    # 크롤러 초기화 및 실행
    crawler = GuidanceCrawler(logger=logger, max_retries=config["max_retries"])
    
    output_file = crawler.crawl_and_save(config["search_params"])
    
    if not output_file:
        logger.warning("No results were saved")

if __name__ == "__main__":
    main()

