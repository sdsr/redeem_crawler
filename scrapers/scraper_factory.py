"""
스크래퍼 팩토리

사이트 유형에 따라 적절한 스크래퍼를 생성합니다.

팩토리 패턴 (Factory Pattern):
- 객체 생성 로직을 캡슐화
- 클라이언트 코드가 구체적인 클래스를 알 필요 없음
- 새로운 스크래퍼 추가 시 팩토리만 수정하면 됨
"""

from typing import Optional, Union
from .arca_scraper import ArcaScraper
from .youtube_scraper import YoutubeScraper


class ScraperFactory:
    """
    스크래퍼 팩토리 클래스
    
    사용법:
        scraper = ScraperFactory.create("arca", "genshin", url, skip_scraped=True)
        scraper = ScraperFactory.create("youtube", "genshin", url)
    """
    
    # 지원하는 사이트 유형
    SUPPORTED_TYPES = ["arca", "youtube"]
    
    @staticmethod
    def create(site_type: str, game: str, url: str, 
               skip_scraped: bool = True) -> Optional[Union[ArcaScraper, YoutubeScraper]]:
        """
        사이트 유형에 맞는 스크래퍼 생성
        
        Args:
            site_type: 사이트 유형 (arca, youtube)
            game: 게임 식별자
            url: 스크래핑 URL
            skip_scraped: 이미 방문한 URL 건너뛰기
            
        Returns:
            스크래퍼 인스턴스 또는 None
        """
        site_type = site_type.lower()
        
        if site_type == "arca":
            return ArcaScraper(game, search_url=url, skip_scraped=skip_scraped)
        
        elif site_type == "youtube":
            return YoutubeScraper(game, channel_url=url, skip_scraped=skip_scraped)
        
        else:
            print(f"[오류] 지원하지 않는 사이트 유형: {site_type}")
            print(f"       지원 유형: {ScraperFactory.SUPPORTED_TYPES}")
            return None
    
    @staticmethod
    def get_supported_types() -> list:
        """지원하는 사이트 유형 목록"""
        return ScraperFactory.SUPPORTED_TYPES
