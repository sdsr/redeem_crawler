"""
아카라이브 스크래퍼 (cloudscraper 버전)

cloudscraper는 CloudFlare의 JavaScript Challenge를 우회하는
requests 호환 라이브러리입니다.
"""

import time
from datetime import datetime, timedelta
import cloudscraper
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple
from dataclasses import dataclass

from config import REQUEST_HEADERS, REQUEST_DELAY, ARCA_BASE_URL
from utils.code_extractor import CodeExtractor
from services.code_service import ArticleService
from site_manager import SiteManager


@dataclass
class ArticleInfo:
    """
    게시글 정보를 담는 데이터 클래스
    """
    url: str
    title: str
    codes: List[str] = None
    posted_at: datetime = None  # 게시글 작성일
    
    def __post_init__(self):
        if self.codes is None:
            self.codes = []


class ArcaScraper:
    """
    아카라이브 게시판 스크래퍼 (cloudscraper 기반)
    
    특징:
    - CloudFlare 우회
    - 이미 스크래핑한 URL 건너뛰기
    - DB 기반 사이트 설정 사용
    """
    
    # 기본 코드 패턴 (게임 공통)
    DEFAULT_CODE_PATTERNS = [r'\b[A-Z0-9]{8,16}\b']
    
    def __init__(self, game: str, search_url: str = None, skip_scraped: bool = True):
        """
        Args:
            game: 게임 식별자
            search_url: 검색 URL (없으면 기본값 사용)
            skip_scraped: 이미 스크래핑한 URL 건너뛰기 여부
        """
        self.game = game
        self.search_url = search_url
        self.skip_scraped = skip_scraped
        
        # cloudscraper 세션 생성
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.scraper.headers.update(REQUEST_HEADERS)
        
        # 코드 추출기 초기화
        self.extractor = CodeExtractor(patterns=self.DEFAULT_CODE_PATTERNS)
        
        # 게시글 서비스 (URL 중복 체크용)
        self.article_service = ArticleService()
        
        # 사이트 관리자 (키워드 필터용)
        self.site_manager = SiteManager()
        
        print(f"[정보] CloudScraper 초기화 완료 (게임: {game})")
        print(f"[정보] 키워드 필터 활성화: {self.site_manager.get_keywords()}")
    
    def _request(self, url: str) -> Optional[BeautifulSoup]:
        """URL에 GET 요청을 보내고 BeautifulSoup 객체를 반환"""
        try:
            time.sleep(REQUEST_DELAY)
            response = self.scraper.get(url, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'lxml')
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            print(f"[오류] CloudFlare Challenge 실패: {url}")
            return None
        except Exception as e:
            print(f"[오류] 요청 실패: {url}")
            print(f"       원인: {e}")
            return None
    
    def _parse_time_element(self, time_elem) -> Optional[datetime]:
        """<time> 태그에서 datetime을 파싱"""
        if not time_elem or not time_elem.get('datetime'):
            return None
        try:
            dt_str = time_elem.get('datetime')
            if dt_str.endswith('Z'):
                dt_str = dt_str[:-1]
            if '.' in dt_str:
                dt_str = dt_str.split('.')[0]
            return datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            return None
    
    def get_article_list(self, page: int = 1, max_age_days: int = 30) -> List[Tuple[str, str]]:
        """게시판 목록에서 게시글 정보를 가져옴 (날짜 필터 포함)
        
        Args:
            page: 페이지 번호
            max_age_days: 최대 게시글 나이 (일). 이보다 오래된 글은 건너뜀. 기본값 30일.
        """
        if not self.search_url:
            print("[오류] 검색 URL이 설정되지 않았습니다.")
            return [], False
        
        url = self.search_url
        if page > 1:
            url += f"&p={page}"
        
        print(f"[정보] 게시글 목록 조회: 페이지 {page}")
        print(f"[접근] {url}")
        
        soup = self._request(url)
        if not soup:
            return [], False
        
        articles = []
        skipped_old = 0
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        found_old_article = False
        article_links = soup.select('a.vrow.column')
        
        for link in article_links:
            href = link.get('href', '')
            
            if href.startswith('/'):
                full_url = ARCA_BASE_URL + href
            else:
                full_url = href
            
            # 제목 추출
            title_elem = link.select_one('.col-title')
            title = title_elem.get_text(strip=True) if title_elem else "제목 없음"
            
            # 날짜 필터: 목록의 <time> 태그에서 작성일 확인
            time_elem = link.select_one('time')
            article_date = self._parse_time_element(time_elem)
            
            if article_date and article_date < cutoff_date:
                skipped_old += 1
                found_old_article = True
                continue
            
            # 게시글 URL인지 확인
            if '/b/' in href and href.count('/') >= 3:
                # 이미 스크래핑한 URL인지 확인
                if self.skip_scraped and self.article_service.is_scraped(full_url):
                    continue
                articles.append((full_url, title))
        
        if skipped_old > 0:
            print(f"[정보] {skipped_old}개 게시글 건너뜀 (작성일 {max_age_days}일 초과)")
        print(f"[정보] {len(articles)}개 새 게시글 발견")
        return articles, found_old_article
    
    def get_article_content(self, url: str, include_comments: bool = True) -> Tuple[Optional[str], Optional[datetime]]:
        """
        게시글 본문 내용과 작성일을 가져옴
        
        Args:
            url: 게시글 URL
            include_comments: 댓글도 포함할지 여부 (기본값: True)
            
        Returns:
            (본문 텍스트, 작성일) 튜플
        """
        soup = self._request(url)
        if not soup:
            return None, None
        
        all_text = []
        posted_at = None
        
        # 작성일 추출: <span class="head">작성일</span> 또는 <span class="head">Uploaded date</span>
        # (아카라이브는 언어 설정에 따라 한글/영어로 표시됨)
        date_head = soup.find('span', class_='head', string='작성일')
        if not date_head:
            date_head = soup.find('span', class_='head', string='Uploaded date')
        
        if date_head:
            time_elem = date_head.find_next('time')
            if time_elem and time_elem.get('datetime'):
                try:
                    # ISO 형식: 2026-01-03T14:25:41.000Z
                    dt_str = time_elem.get('datetime')
                    # .000Z 부분 처리
                    if dt_str.endswith('Z'):
                        dt_str = dt_str[:-1]  # Z 제거
                    if '.' in dt_str:
                        dt_str = dt_str.split('.')[0]  # 밀리초 제거
                    posted_at = datetime.fromisoformat(dt_str)
                except (ValueError, TypeError) as e:
                    print(f"[경고] 작성일 파싱 실패: {e}")
        
        # 1. 본문 추출
        content_elem = soup.select_one('.article-content')
        if content_elem:
            # href 속성에서 URL도 추출 (링크에 코드가 포함된 경우)
            # 예: https://genshin.hoyoverse.com/ko/gift?code=GENSHINQUIZ2026
            for link in content_elem.select('a[href]'):
                href = link.get('href', '')
                if 'code=' in href:
                    all_text.append(href)
            
            all_text.append(content_elem.get_text(separator=' ', strip=True))
        
        # 2. 댓글 추출 (옵션)
        if include_comments:
            # 아카라이브 댓글 선택자
            comment_elems = soup.select('.comment-content')
            for comment in comment_elems:
                # 댓글 내 링크도 확인
                for link in comment.select('a[href]'):
                    href = link.get('href', '')
                    if 'code=' in href:
                        all_text.append(href)
                
                comment_text = comment.get_text(separator=' ', strip=True)
                if comment_text:
                    all_text.append(comment_text)
        
        content = ' '.join(all_text) if all_text else None
        return content, posted_at
    
    def scrape_articles(self, max_pages: int = 1, max_articles: int = 10, max_age_days: int = 30) -> List[ArticleInfo]:
        """
        게시글을 스크래핑하고 리딤코드를 추출
        
        Args:
            max_pages: 스크래핑할 최대 페이지 수
            max_articles: 처리할 최대 게시글 수
            max_age_days: 최대 게시글 나이 (일). 기본값 30일.
            
        Returns:
            ArticleInfo 리스트 (리딤코드가 발견된 게시글만)
        """
        all_articles = []
        articles_processed = 0
        skipped_count = 0
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        for page in range(1, max_pages + 1):
            if articles_processed >= max_articles:
                break
            
            article_list, found_old = self.get_article_list(page, max_age_days=max_age_days)
            
            if not article_list:
                print(f"[정보] 페이지 {page}에서 새 게시글 없음")
                if found_old:
                    print(f"[정보] 오래된 글이 발견되어 이후 페이지 탐색 중단")
                    break
                continue
            
            # 오래된 글이 목록에 나타났으면 이 페이지만 처리하고 중단
            stop_after_this_page = found_old
            
            for url, title in article_list:
                if articles_processed >= max_articles:
                    break
                
                print(f"[처리] {title[:40]}...")
                
                # 키워드 필터링: 제목에 키워드가 있는지 먼저 확인
                title_has_keyword = self.site_manager.has_keyword(title)
                
                # 본문과 작성일 추출
                content, posted_at = self.get_article_content(url)
                
                # 상세 페이지의 작성일로 한번 더 날짜 필터 확인
                if posted_at and posted_at < cutoff_date:
                    print(f"[건너뛰기] 오래된 글: {title[:30]}... (작성일: {posted_at.strftime('%Y-%m-%d')})")
                    self.article_service.mark_scraped(
                        url=url, game=self.game, title=title, codes_found=0
                    )
                    articles_processed += 1
                    continue
                
                # 제목에 키워드가 없으면 본문에서도 확인
                if not title_has_keyword:
                    content_has_keyword = self.site_manager.has_keyword(content) if content else False
                    
                    if not content_has_keyword:
                        print(f"[건너뛰기] 키워드 없음: {title[:30]}...")
                        # 스크래핑 기록은 저장 (다시 처리하지 않도록)
                        self.article_service.mark_scraped(
                            url=url,
                            game=self.game,
                            title=title,
                            codes_found=0
                        )
                        articles_processed += 1
                        continue
                
                # 제목에서 코드 추출
                codes_from_title = self.extractor.extract(title)
                
                # 본문에서 코드 추출
                codes_from_content = self.extractor.extract(content) if content else []
                
                # 중복 제거하여 합치기
                all_codes = list(set(codes_from_title + codes_from_content))
                
                # 스크래핑 기록 저장
                self.article_service.mark_scraped(
                    url=url,
                    game=self.game,
                    title=title,
                    codes_found=len(all_codes)
                )
                
                if all_codes:
                    article = ArticleInfo(
                        url=url,
                        title=title,
                        codes=all_codes,
                        posted_at=posted_at  # 작성일 추가
                    )
                    all_articles.append(article)
                    print(f"[발견] 리딤코드 {len(all_codes)}개: {all_codes}")
                    if posted_at:
                        print(f"       작성일: {posted_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                articles_processed += 1
            
            # 오래된 글이 목록에 있었으면 다음 페이지는 더 오래된 글뿐이므로 중단
            if stop_after_this_page:
                print(f"[정보] 오래된 글이 발견되어 이후 페이지 탐색 중단")
                break
        
        return all_articles
    
    def close(self):
        """세션 종료"""
        self.scraper.close()
        print("[정보] 세션 종료")
