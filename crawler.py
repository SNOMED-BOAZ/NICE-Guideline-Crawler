import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import urljoin
import pandas as pd
import random

class GuidanceCrawler:
    """진료지침 정보를 크롤링하는 클래스"""
    
    def __init__(self, logger=None, max_retries: int = 3):
        """
        Constructor
        
        Args:
            max_retries (int): 재시도 최대 횟수
        """
        self.base_url = 'https://www.nice.org.uk/guidance/published'
        self.max_retries = max_retries
        self.logger = logger if logger else logging.getLogger("crawl_guidance.crawler")
        
        # URL 파라미터 포맷 정의
        self.search_params_format = {
            'search_query': 'q',
            'from': 'from', 
            'to': 'to',
            'type': 'ndt',
            'guidance_programme': 'ngt',
            'sort': 's',
            'result_per_page': 'ps',
            'page': 'pa'
        }
        
        # 검색 파라미터 초기화
        self.search_params = {
            'search_query': None,
            'from': None,
            'to': None, 
            'type': None,
            'guidance_programme': None,
            'sort': None,
            'result_per_page': None,
            'page': None
        }

    def set_request_params(self, params: Dict):
        """
        url에 요청 파라미터 추가하는 함수
        params dict에서 None이 아닌 값만 실제 검색 파라미터에 포함
        
        Args:
            params (dict): 검색 파라미터 딕셔너리
        """
        # 입력된 파라미터 중 None이 아닌 값만 search_params에 업데이트
        valid_params = {k: v for k, v in params.items() if v is not None}
        self.search_params.update(valid_params)
        if valid_params:
            self.logger.info("Set Request Params: " + ", ".join([f"{k}={v}" for k,v in valid_params.items()]))
        else:
            self.logger.info("No request parameters provided")

    def get_url(self) -> str:
        """
        self.search_params에서 None이 아닌 값들을 URL 파라미터로 변환하여 base_url에 추가하는 함수
        
        Returns:
            str: 파라미터가 포함된 최종 URL
        """
        # None이 아닌 파라미터만 필터링
        valid_params = {k: v for k, v in self.search_params.items() if v is not None}
        
        if not valid_params:
            return self.base_url
            
        # URL 생성
        url = self.base_url
        
        # 첫 번째 파라미터는 '?'로 시작
        first = True
        for param_name, param_value in valid_params.items():
            # search_params_format에서 실제 URL 파라미터 키 가져오기
            param_key = self.search_params_format[param_name]
            
            if first:
                url += f'?{param_key}={param_value}'
                first = False
            else:
                url += f'&{param_key}={param_value}'
                
        return url

    def _get_random_delay(self) -> float:
        """
        0.7초에서 1.2초 사이의 랜덤한 딜레이 시간을 반환하는 함수
        
        Returns:
            float: 랜덤 딜레이 시간 (초)
        """
        delay = random.uniform(0.7, 1.2)
        self.logger.debug(f"Generated random delay: {delay:.2f} seconds")
        return delay

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        URL로 요청을 보내고 응답을 반환
        
        Args:
            url (str): 요청을 보낼 URL
            
        Returns:
            Optional[requests.Response]: 성공시 Response 객체, 실패시 None
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                # 매 요청마다 랜덤한 딜레이 적용
                delay = self._get_random_delay()
                time.sleep(delay)
                return response
            except requests.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self._get_random_delay())  # 실패시에도 랜덤 딜레이 사용
                continue
        return None

    def _parse_row(self, row) -> Optional[Dict]:
        """
        테이블 행 파싱
        
        Args:
            row: BeautifulSoup row 객체
            
        Returns:
            Optional[Dict]: 파싱된 데이터 또는 None
        """
        try:
            cols = row.find_all('td')
            if len(cols) < 4:
                self.logger.warning(f"Row has insufficient columns (expected 4, got {len(cols)})")
                return None

            link = cols[0].find('a')
            if not link:
                self.logger.warning("Link not found")
                return None

            return {
                'url': urljoin(self.base_url, link.get('href', '')),
                'title': link.text.strip(),
                'technology_type': cols[1].text.strip(),
                'decision_date': cols[3].find('time').get('datetime', '')[:10] if cols[3].find('time') else ''
            }
        except Exception as e:
            self.logger.error(f"Error occurred while parsing row: {str(e)}")
            return None

    def _get_list_of_guidance(self, params: Dict) -> List[Dict]:
        """
        NICE 웹사이트에서 조건에 해당하는 진료지침 목록을 가져오는 내부 함수
        
        Args:
            params (Dict): 검색 파라미터 딕셔너리
            
        Returns:
            List[Dict]: 크롤링된 가이던스 정보 리스트
        """
        self.set_request_params(params)

        url = self.get_url()
        guidance_list = []
        
        try:
            response = self._make_request(url)
            if not response:
                self.logger.error(f"Page request failed")
                return guidance_list

            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select('#results > tbody > tr')
            
            if not rows:
                self.logger.warning(f"No data found")
                return guidance_list

            for row in rows:
                guidance_info = self._parse_row(row)
                if guidance_info:
                    guidance_list.append(guidance_info)
                time.sleep(self._get_random_delay())  # 요청 간 딜레이

        except Exception as e:
            self.logger.error(f"Unexpected error occurred while crawling: {str(e)}")
        
        self.logger.info(f"Found {len(guidance_list)} guidance items")
        return guidance_list

    def _generate_filename(self, params: Dict) -> str:
        """
        검색 파라미터를 기반으로 파일명 생성
        
        Args:
            params (Dict): 검색 파라미터
            
        Returns:
            str: 생성된 파일명
        """
        # 파일명에 포함될 키 순서
        key_order = ['search_query', 'from', 'to', 'type', 'guidance_programme']
        
        # None이 아닌 값만 포함하여 파일명 생성
        parts = ['guidance']
        for key in key_order:
            if params.get(key):
                parts.append(str(params[key]))
        
        # 최소한 하나의 파라미터가 있어야 함
        if len(parts) == 1:
            parts.append('all')
            
        return '_'.join(parts) + '.csv'

    def crawl_and_save(self, params: Dict) -> str:
        """
        NICE 웹사이트에서 진료지침 정보를 크롤링하고 CSV 파일로 저장하는 함수
        
        Args:
            params (Dict): 검색 파라미터 딕셔너리
                - search_query (str, optional): 검색어
                - from_date (str, optional): 시작 날짜 (YYYY-MM-DD)
                - to_date (str, optional): 종료 날짜 (YYYY-MM-DD)
                - type (str, optional): 유형 (Guidance, NICE advice, Quality standard)
                - guidance_programme (str, optional): 진료지침 프로그램 (guide.md 참고)
                - sort (str, optional): 정렬 방식 (Title, Date)
                - result_per_page (int, optional): 페이지당 결과 수
                - page (int, optional): 페이지 번호
            
        Returns:
            str: 저장된 파일 경로
            
        Example:
            >>> params = {
            ...     "search_query": "diabetes",
            ...     "from_date": "2023-01-01",
            ...     "type": "Guidance"
            ... }
            >>> crawler.crawl_and_save(params)
            'guidance_diabetes_2023-01-01_Guidance.csv'
        """
        # 데이터 크롤링
        results = self._get_list_of_guidance(params)
        
        if not results:
            self.logger.warning("No results to save")
            return ""
            
        # 결과를 DataFrame으로 변환
        df = pd.DataFrame(results)
        
        # 파일명 생성
        filename = self._generate_filename(params)
        
        # CSV 파일로 저장
        try:
            df.to_csv(filename, index=False, encoding='utf-8')
            self.logger.info(f"Results saved to {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
            return ""

# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("crawl_guidance.crawler")
    
    # 크롤러 초기화
    crawler = GuidanceCrawler(logger)
    
    # 검색 조건을 적용하여 크롤링 실행
    params = {
        "search_query": None,
        "from_date": None,
        "to_date": None,
        "type": None,
        "guidance_programme": None,
        "sort": None,
        "result_per_page": 30,
        "page": 1
    }
    
    output_file = crawler.crawl_and_save(params)
    if output_file:
        print(f"결과가 {output_file}에 저장되었습니다.")