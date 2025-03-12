import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
import time
from urllib.parse import urljoin
import pandas as pd
import random
import aiohttp
import asyncio
from tqdm import tqdm
from tqdm.asyncio import tqdm as tqdm_asyncio
import json
import os

class GuidanceCrawler:
    """진료지침 정보를 크롤링하는 클래스"""
    
    def __init__(self, logger=None, max_retries: int = 3, max_concurrent: int = 2):
        """
        Constructor
        
        Args:
            max_retries (int): 재시도 최대 횟수
            max_concurrent (int): 동시 요청 최대 수
        """
        self.base_url = 'https://www.nice.org.uk/guidance/published'
        self.max_retries = max_retries
        self.max_concurrent = max_concurrent
        self.logger = logger if logger else logging.getLogger("crawl_guidance.crawler")
        
        # URL 파라미터 포맷 정의
        self.search_params_format = {
            'search_query': 'q',
            'from_date': 'from',
            'to_date': 'to',
            'type': 'ndt',
            'guidance_programme': 'ngt',  # Guidance 타입일 때 사용
            'advice_programme': 'nat',    # NICE advice 타입일 때 사용
            'sort': 's',
            'result_per_page': 'ps',
            'page': 'pa'
        }
        
        # 검색 파라미터 초기화
        self.search_params = {
            'search_query': None,
            'from_date': None,
            'to_date': None,
            'type': None,
            'guidance_programme': None,
            'advice_programme': None,
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

    def get_url(self) -> str:
        """
        self.search_params에서 None이 아니고 빈 문자열이 아닌 값들을 URL 파라미터로 변환하여 base_url에 추가하는 함수
        
        Returns:
            str: 파라미터가 포함된 최종 URL
        """
        # None이 아니고 빈 문자열이 아닌 파라미터만 필터링
        valid_params = {
            self.search_params_format[key]: value 
            for key, value in self.search_params.items()
            if value is not None and value != "" and key in self.search_params_format
        }
        
        if not valid_params:
            return self.base_url
            
        # URL 생성
        url = self.base_url + '?'
        url += '&'.join([f"{key}={value}" for key, value in valid_params.items()])
        
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
        key_order = ['search_query', 'from_date', 'to_date', 'type', 'guidance_programme', 'advice_programme']
        
        # None이 아닌 값만 포함하여 파일명 생성
        parts = ['guidance']
        for key in key_order:
            if params.get(key):
                parts.append(str(params[key]))
        
        # 최소한 하나의 파라미터가 있어야 함
        if len(parts) == 1:
            parts.append('all')
            
        return '_'.join(parts) + '.csv'

    def crawl(self, params: Dict) -> List[Dict]:
        """
        NICE 웹사이트에서 진료지침 정보를 크롤링하는 함수
        
        Args:
            params (Dict): 검색 파라미터 딕셔너리
                - search_query (str, optional): 검색어
                - from_date (str, optional): 시작 날짜 (YYYY-MM-DD)
                - to_date (str, optional): 종료 날짜 (YYYY-MM-DD)
                - type (str, optional): 유형 (Guidance, NICE advice, Quality standard)
                - guidance_programme (str, optional): Guidance 타입일 때 사용
                - advice_programme (str, optional): NICE advice 타입일 때 사용
                - sort (str, optional): 정렬 방식 (Title, Date)
                - result_per_page (int, optional): 페이지당 결과 수
                - page (int, optional): 페이지 번호
            
        Returns:
            List[Dict]: 크롤링된 결과 리스트
        """
        # 데이터 크롤링
        results = self._get_list_of_guidance(params)
        
        if not results:
            self.logger.warning("No results found")
            return []
            
        return results

    def save_to_csv(self, results: List[Dict], params: Dict) -> str:
        """
        크롤링된 결과를 CSV 파일로 저장하는 함수
        
        Args:
            results (List[Dict]): 크롤링된 결과 리스트
            params (Dict): 검색 파라미터 딕셔너리
            
        Returns:
            str: 저장된 파일 경로
        """
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
        
    def save_guideline_contents_json(self, contents: Dict, filename: str):
        """
        가이던스 콘텐츠를 JSON 파일로 저장하는 함수
        
        Args:
            contents (Dict): 가이던스 콘텐츠 딕셔너리
            filename (str): 저장할 파일명
        """
        path = "output/contents"
        if not os.path.exists(path):
            os.makedirs(path)
        filepath = f"{path}/{filename}.json"
        
        # 줄바꿈 문자를 공백으로 대체하는 함수
        def replace_newlines(obj):
            if isinstance(obj, dict):
                return {k: replace_newlines(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_newlines(item) for item in obj]
            elif isinstance(obj, str):
                # 연속된 줄바꿈은 하나의 공백으로 대체
                return ' '.join(obj.split())
            else:
                return obj
        
        # 줄바꿈 문자를 공백으로 대체한 콘텐츠 생성
        processed_contents = replace_newlines(contents)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(processed_contents, f, ensure_ascii=False, indent=4)
            self.logger.info(f"Guideline contents saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save guideline contents: {str(e)}")
    
    async def get_contents_in_detail_page(self, session: aiohttp.ClientSession, result: Dict) -> List[Dict]:
        """
        가이던스 상세 페이지에서 텍스트 콘텐츠를 파싱하는 함수
        
        Args:
            session (aiohttp.ClientSession): 비동기 HTTP 세션
            result (Dict): 크롤링된 결과 딕셔너리
        """
        try:
            reference = result['reference']
            url = result['url']
            self.logger.debug(f"Fetching detail page: {url}")
            
            # 타임아웃 설정 추가
            timeout = aiohttp.ClientTimeout(total=30)  # 30초 타임아웃
            
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    self.logger.warning(f"Failed to fetch detail page {url}. Status: {response.status}")
                    result['contents'] = None
                    return result
                
                try:
                    # response.text() 대신 content.read() 사용하되 예외 처리 추가
                    content = await response.content.read()
                    html = content.decode('utf-8')
                    soup = BeautifulSoup(html, 'html.parser')
                except Exception as e:
                    self.logger.error(f"Error reading content from {url}: {e}")
                    result['contents'] = None
                    return result
                
                # 챕터 목록을 저장할 리스트
                chapters = []
                
                # Case 1: stacked-nav 클래스를 가진 nav 태그 검색
                nav_chapters = soup.find('nav', {'class': 'stacked-nav', 'aria-label': 'Chapters'})
                if nav_chapters:
                    ul = nav_chapters.find('ul', {'class': 'stacked-nav__list'})
                    if ul:
                        items = ul.find_all('li', {'class': 'stacked-nav__list-item'})
                        for item in items:
                            link = item.find('a')
                            span = item.find('span', {'class': 'stacked-nav__content-wrapper'})
                            if link and span:
                                chapter_url = urljoin(url, link.get('href'))
                                chapters.append({
                                    'title': span.get_text(strip=True),  # 제목은 공백 제거
                                    'url': chapter_url
                                })
                
                # Case 2: overview-menu와 guidance-menu div 태그 검색
                if not chapters:
                    overview_menu = soup.find('div', {'id': 'overview-menu'})
                    if overview_menu:
                        overview_link = overview_menu.find('a')
                        if overview_link:
                            chapters.append({
                                "title": overview_link.get_text(strip=True),  # 제목은 공백 제거
                                "url": urljoin(url, overview_link.get('href'))
                            })
                    
                    guidance_menu = soup.find('div', {'id': 'guidance-menu'})
                    if guidance_menu:
                        nav_list = guidance_menu.find('ul', {'class': 'nav nav-list', 'id': 'Guidance-Menu'})
                        if nav_list:
                            items = nav_list.find_all('li')
                            for item in items:
                                link = item.find('a')
                                if link:
                                    chapter_url = urljoin(url, link.get('href'))
                                    chapters.append({
                                        "title": link.get_text(strip=True),  # 제목은 공백 제거
                                        "url": chapter_url
                                    })
                
                # 각 챕터의 내용 수집
                chapter_contents = {}
                chapter_contents['title'] = result['title']
                chapter_contents['reference'] = reference
                chapter_contents['url'] = url
                chapter_contents['contents'] = {}
                for chapter in chapters:
                    try:
                        # 재시도 로직 추가
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                async with session.get(chapter['url'], timeout=timeout) as chapter_response:
                                    if chapter_response.status == 200:
                                        # 컨텐츠 읽기 시도
                                        try:
                                            chapter_content = await chapter_response.content.read()
                                            chapter_html = chapter_content.decode('utf-8')
                                            chapter_soup = BeautifulSoup(chapter_html, 'html.parser')
                                            
                                            # 섹션 내용 찾기 - article 태그 내부의 모든 콘텐츠
                                            article = chapter_soup.find('article')
                                            if article:
                                                # 모든 헤더와 단락을 순서대로 수집
                                                content_elements = []
                                                for element in article.find_all(['h2', 'h3', 'h4', 'p']):
                                                    # 헤더인 경우 구분을 위해 앞뒤로 ### 추가
                                                    if element.name.startswith('h'):
                                                        content_elements.append(f"### {element.get_text(strip=True)} ###")
                                                    else:
                                                        # 단락은 공백으로 정리하여 텍스트 추출
                                                        text = ' '.join(element.get_text().split())
                                                        content_elements.append(text)
                                                
                                                # 공백으로 구분하여 하나의 문자열로 결합
                                                content = ' '.join(content_elements)
                                                
                                                chapter_contents['contents'][chapter['title']] = content
                                                # 성공적으로 처리되면 재시도 루프 종료
                                                break
                                            else:
                                                # js-in-page-nav-target 내의 chapter div 찾기
                                                nav_target = chapter_soup.find('div', {'class': 'js-in-page-nav-target'})
                                                if nav_target:
                                                    chapter_div = nav_target.find('div', {'class': 'chapter'})
                                                    if chapter_div:
                                                        # chapter div 내의 모든 텍스트 수집
                                                        content_elements = []
                                                        for element in chapter_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'li']):
                                                            if element.name.startswith('h'):
                                                                content_elements.append(f"### {element.get_text(strip=True)} ###")
                                                            else:
                                                                # 단락과 리스트 아이템은 공백으로 정리
                                                                text = ' '.join(element.get_text().split())
                                                                content_elements.append(text)
                                                        
                                                        content = ' '.join(content_elements)
                                                        chapter_contents['contents'][chapter['title']] = content
                                                        # 성공적으로 처리되면 재시도 루프 종료
                                                        break
                                                else:
                                                    # article 태그가 없는 경우 section-summary도 확인
                                                    section = chapter_soup.find('div', {'class': 'section-summary web-viewer-content'})
                                                    if section:
                                                        # 공백으로 정리하여 텍스트 추출
                                                        text = ' '.join(section.get_text().split())
                                                        chapter_contents['contents'][chapter['title']] = text
                                                        # 성공적으로 처리되면 재시도 루프 종료
                                                        break
                                                    else:
                                                        self.logger.warning(f"No content found in chapter: {chapter['url']}")
                                                        # 콘텐츠를 찾지 못했지만 오류는 아니므로 재시도 루프 종료
                                                        break
                                        except Exception as e:
                                            self.logger.warning(f"Error reading chapter content (attempt {retry+1}/{max_retries}): {e}")
                                            if retry == max_retries - 1:  # 마지막 시도였다면
                                                raise  # 예외를 다시 발생시켜 외부 예외 처리로 넘김
                                            # 재시도 전 잠시 대기
                                            await asyncio.sleep(1)
                                    else:
                                        self.logger.warning(f"Failed to fetch chapter page {chapter['url']}. Status: {chapter_response.status}")
                                        if retry == max_retries - 1:  # 마지막 시도였다면
                                            break  # 더 이상 재시도하지 않음
                                        # 재시도 전 잠시 대기
                                        await asyncio.sleep(1)
                            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                                self.logger.warning(f"Network error (attempt {retry+1}/{max_retries}): {e}")
                                if retry == max_retries - 1:  # 마지막 시도였다면
                                    raise  # 예외를 다시 발생시켜 외부 예외 처리로 넘김
                                # 재시도 전 잠시 대기
                                await asyncio.sleep(1)
                    except Exception as e:
                        self.logger.error(f"Error occurred while fetching chapter {chapter['url']}: {e}")
                        # 이 챕터에 대한 처리는 실패했지만 다른 챕터는 계속 처리
                        continue
                
                # 결과 저장
                self.save_guideline_contents_json(chapter_contents, result['reference'])
                result['contents'] = chapter_contents
                return result
                
        except Exception as e:
            self.logger.error(f"Error occurred while getting contents in detail page: {e}")
            result['contents'] = None
            return result

    async def crawl_all_pages(self) -> List[Dict]:
        """모든 문서를 크롤링"""
        try:
            # 현재 설정된 검색 파라미터 가져오기
            current_type = self.search_params.get('type', '')
            current_guidance_programme = self.search_params.get('guidance_programme', '')
            current_advice_programme = self.search_params.get('advice_programme', '')
            
            # 현재 크롤링 중인 프로그램 정보 로깅
            programme_info = f"Type: {current_type}"
            if current_guidance_programme:
                programme_info += f", Guidance Programme: {current_guidance_programme}"
            if current_advice_programme:
                programme_info += f", Advice Programme: {current_advice_programme}"
            self.logger.info(f"Crawling documents for {programme_info}")
            
            async with aiohttp.ClientSession() as session:
                url = self.get_url()
                async with session.get(url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    
                    rows = soup.select('table tbody tr')
                    self.logger.info(f"Found {len(rows)} guidance documents for {programme_info}")
                    
                    # tqdm을 사용하여 진행 상황 표시 (프로그램 정보 포함)
                    for row in tqdm(rows, desc=f"문서 정보 수집 ({programme_info})"):
                        cols = row.select('td')
                        if len(cols) >= 4:
                            title = cols[0].select_one('a')
                            if title:
                                guidance_url = urljoin(self.base_url, title['href'])
                                results.append({
                                    'title': title.text.strip(),
                                    'url': guidance_url,
                                    'contents': None,  # 상세 페이지에서 파싱된 텍스트 콘텐츠 TODO:
                                    'reference': cols[1].text.strip(),
                                    'published_date': cols[2].text.strip(),
                                    'last_updated': cols[3].text.strip(),
                                    'type': current_type,
                                    'guidance_programme': current_guidance_programme,
                                    'advice_programme': current_advice_programme
                                })
                    
                    if results:
                        self.logger.info(f"Fetching Detail Page for {len(results)} documents ({programme_info})...")
                        
                        # 세마포어를 사용하여 동시 요청 수 제한
                        semaphore = asyncio.Semaphore(self.max_concurrent)
                        
                        async def fetch_with_semaphore(result):
                            async with semaphore:
                                return await self.get_contents_in_detail_page(session, result)
                        
                        tasks = [fetch_with_semaphore(result) for result in results]
                        # tqdm_asyncio를 사용하여 비동기 진행 상황 표시
                        updated_results = await tqdm_asyncio.gather(*tasks, desc=f"Content 수집 ({programme_info})")
                        return updated_results
                    
                    
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error occurred while crawling: {e}")
            return []

    async def crawl_async(self, params: Dict) -> List[Dict]:
        """비동기적으로 크롤링하고 결과를 반환"""
        # 검색 파라미터 업데이트
        self.set_request_params(params)
        
        # 크롤링 실행
        results = await self.crawl_all_pages()
        
        if not results:
            self.logger.warning("No results crawled")
            return []
            
        self.logger.info(f"Total {len(results)} guidance records crawled")
        return results

    # TODO:
    async def crawl_contents_in_detail_page(self, url: str) -> List[Dict]:
        """
        가이던스 상세 페이지에서 텍스트 콘텐츠를 크롤링하는 함수
        
        Args:
            url (str): 가이던스 상세 페이지의 URL
        """
        return 0