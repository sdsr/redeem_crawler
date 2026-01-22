"""
유튜브 커뮤니티 포스트 스크래퍼 (Playwright 버전)

Playwright를 사용하여 JavaScript 렌더링 후 포스트를 가져옵니다.
[원신], [스타레일] 같은 태그로 게임을 구분합니다.
"""

import re
import time
from typing import List, Dict
from dataclasses import dataclass, field

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from utils.code_extractor import CodeExtractor
from services.code_service import ArticleService


@dataclass 
class GameCodeResult:
    """게임별 코드 결과"""
    game: str
    codes: List[str] = field(default_factory=list)
    source_url: str = ""
    source_title: str = ""


class YoutubeScraper:
    """
    유튜브 커뮤니티 포스트 스크래퍼 (Playwright 기반)
    
    특징:
    - Playwright로 실제 브라우저 렌더링
    - [원신], [스타레일] 같은 태그로 게임 구분
    - 여러 게임의 코드를 한번에 수집
    """
    
    DEFAULT_CODE_PATTERNS = [r'\b[A-Z0-9]{8,16}\b']
    
    # 기본 게임 태그 매핑
    DEFAULT_GAME_TAGS = {
        "[원신]": "genshin",
        "[스타레일]": "starrail", 
        "[붕스]": "starrail",
        "[젠레스]": "zzz",
        "[젠존제]": "zzz",
        "[붕괴3rd]": "honkai3rd",
        "[붕삼]": "honkai3rd",
        "[명조]": "wuwa",
        "[블아]": "bluearchive",
        "[블루아카이브]": "bluearchive",
        "[소전2]": "gfl2",
        "[소녀전선2]": "gfl2",
        "[니케]": "nikke",
        "[트릭컬]": "trikkal",
        "[명방]": "arknights",
        "[명일방주]": "arknights",
        "[림버스]": "limbus",
    }
    
    def __init__(self, game: str, channel_url: str, skip_scraped: bool = True,
                 game_tags: Dict[str, str] = None, headless: bool = True):
        """
        Args:
            game: 게임 식별자 (또는 "_multi")
            channel_url: 유튜브 채널 URL
            skip_scraped: 이미 스크래핑한 URL 건너뛰기
            game_tags: 게임 태그 매핑 (None이면 기본값 사용)
            headless: 브라우저 숨김 모드
        """
        self.game = game
        self.channel_url = channel_url
        self.skip_scraped = skip_scraped
        self.headless = headless
        
        # 게임 태그 매핑 설정
        self.game_tags = game_tags or self.DEFAULT_GAME_TAGS
        
        # URL을 커뮤니티 탭으로 변환
        if '/posts' in channel_url:
            self.channel_url = channel_url.replace('/posts', '/community')
        elif '/community' not in channel_url:
            self.channel_url = channel_url.rstrip('/') + '/community'
        
        self.extractor = CodeExtractor(patterns=self.DEFAULT_CODE_PATTERNS)
        self.article_service = ArticleService()
        
        self.playwright = None
        self.browser = None
        self.page = None
        
        print(f"[정보] YouTube 스크래퍼 초기화 (Playwright)")
        print(f"       게임 태그: {list(self.game_tags.keys())[:5]}...")
    
    def _init_browser(self):
        """Playwright 브라우저 초기화"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        
        # 한국어 설정
        self.page.set_extra_http_headers({
            "Accept-Language": "ko-KR,ko;q=0.9"
        })
    
    def _get_posts_content(self) -> List[str]:
        """
        커뮤니티 페이지에서 포스트 내용 추출
        
        Returns:
            포스트 텍스트 리스트
        """
        try:
            print(f"[접근] {self.channel_url}")
            self.page.goto(self.channel_url, wait_until="networkidle", timeout=30000)
            
            # 쿠키 동의 팝업 처리 (있으면)
            try:
                self.page.click('button:has-text("동의")', timeout=3000)
            except:
                pass
            
            # 포스트 로드 대기
            time.sleep(2)
            
            # 스크롤하여 더 많은 포스트 로드
            for _ in range(3):
                self.page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1)
            
            # 포스트 내용 추출
            # 유튜브 커뮤니티 포스트는 yt-formatted-string 또는 #content-text에 있음
            posts = []
            
            # 포스트 컨테이너 찾기
            post_elements = self.page.query_selector_all('ytd-backstage-post-thread-renderer')
            print(f"[정보] {len(post_elements)}개 포스트 요소 발견")
            
            for post_el in post_elements:
                try:
                    # 포스트 내용 텍스트 추출
                    content_el = post_el.query_selector('#content-text')
                    if content_el:
                        text = content_el.inner_text()
                        if text.strip():
                            posts.append(text.strip())
                except Exception as e:
                    continue
            
            return posts
            
        except PlaywrightTimeout:
            print("[오류] 페이지 로드 타임아웃")
            return []
        except Exception as e:
            print(f"[오류] 포스트 추출 실패: {e}")
            return []
    
    def _parse_game_codes(self, content: str) -> List[GameCodeResult]:
        """
        포스트 내용에서 게임별 코드 추출
        """
        results = []
        
        # 각 게임 태그별로 처리
        for tag, game_id in self.game_tags.items():
            if tag not in content:
                continue
            
            # 태그 뒤의 텍스트에서 코드 추출
            tag_patterns = '|'.join(re.escape(t) for t in self.game_tags.keys())
            pattern = re.escape(tag) + r'(.*?)(?=' + tag_patterns + r'|$)'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                section_text = match.group(1)
                codes = self.extractor.extract(section_text)
                
                if codes:
                    results.append(GameCodeResult(
                        game=game_id,
                        codes=codes,
                        source_url=self.channel_url,
                        source_title=f"YouTube: {content[:40]}..."
                    ))
        
        # 태그가 없는 경우 전체에서 추출
        if not results and self.game != "_multi":
            codes = self.extractor.extract(content)
            if codes:
                results.append(GameCodeResult(
                    game=self.game,
                    codes=codes,
                    source_url=self.channel_url,
                    source_title=f"YouTube: {content[:40]}..."
                ))
        
        return results
    
    def scrape_posts(self, max_posts: int = 10) -> List[GameCodeResult]:
        """
        커뮤니티 포스트에서 게임별 리딤코드 추출
        """
        self._init_browser()
        
        try:
            posts = self._get_posts_content()
            print(f"[정보] {len(posts)}개 포스트 텍스트 추출됨")
            
            all_results = []
            processed = 0
            
            for content in posts:
                if processed >= max_posts:
                    break
                
                # 게임별 코드 추출
                game_results = self._parse_game_codes(content)
                
                for result in game_results:
                    all_results.append(result)
                    print(f"[발견] [{result.game}] 리딤코드 {len(result.codes)}개: {result.codes}")
                
                # 스크래핑 기록
                if game_results:
                    total_codes = sum(len(r.codes) for r in game_results)
                    self.article_service.mark_scraped(
                        url=f"{self.channel_url}#{processed}",
                        game="_multi",
                        title=f"YouTube: {content[:50]}...",
                        codes_found=total_codes
                    )
                
                processed += 1
            
            return all_results
            
        finally:
            self.close()
    
    def close(self):
        """브라우저 종료"""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("[정보] YouTube 스크래퍼 종료")
