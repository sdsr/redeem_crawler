"""
리딤코드 서비스

리딤코드의 저장, 조회, 중복 검증 등의 비즈니스 로직을 처리합니다.
"""

from typing import List, Optional, Tuple
from sqlalchemy.exc import IntegrityError

from database.models import RedeemCode, ScrapedArticle, GameSite, get_session, init_db


class CodeService:
    """
    리딤코드 CRUD 서비스
    """
    
    def __init__(self):
        """데이터베이스 초기화"""
        init_db()
    
    def code_exists(self, code: str) -> bool:
        """코드가 이미 데이터베이스에 존재하는지 확인"""
        session = get_session()
        try:
            exists = session.query(RedeemCode).filter_by(code=code).first() is not None
            return exists
        finally:
            session.close()
    
    def save_code(self, code: str, game: str, source_url: str = None, 
                  source_title: str = None) -> Tuple[bool, str]:
        """리딤코드를 데이터베이스에 저장"""
        if self.code_exists(code):
            return (False, f"이미 존재하는 코드: {code}")
        
        session = get_session()
        try:
            new_code = RedeemCode(
                code=code,
                game=game,
                source_url=source_url,
                source_title=source_title
            )
            session.add(new_code)
            session.commit()
            return (True, f"새 코드 저장됨: {code}")
            
        except IntegrityError:
            session.rollback()
            return (False, f"중복 코드 (동시성): {code}")
        except Exception as e:
            session.rollback()
            return (False, f"저장 실패: {e}")
        finally:
            session.close()
    
    def save_codes_batch(self, codes: List[dict]) -> dict:
        """여러 코드를 일괄 저장"""
        results = {
            "saved": 0,
            "duplicates": 0,
            "errors": 0,
            "saved_codes": [],
            "duplicate_codes": []
        }
        
        for code_info in codes:
            success, message = self.save_code(
                code=code_info["code"],
                game=code_info["game"],
                source_url=code_info.get("source_url"),
                source_title=code_info.get("source_title")
            )
            
            if success:
                results["saved"] += 1
                results["saved_codes"].append(code_info["code"])
            elif "이미 존재" in message or "중복" in message:
                results["duplicates"] += 1
                results["duplicate_codes"].append(code_info["code"])
            else:
                results["errors"] += 1
        
        return results
    
    def get_codes_by_game(self, game: str, valid_only: bool = True) -> List[RedeemCode]:
        """게임별 리딤코드 목록을 조회"""
        session = get_session()
        try:
            query = session.query(RedeemCode).filter_by(game=game)
            if valid_only:
                query = query.filter_by(is_valid=True)
            codes = query.order_by(RedeemCode.created_at.desc()).all()
            return codes
        finally:
            session.close()
    
    def get_all_codes(self) -> List[RedeemCode]:
        """모든 리딤코드를 조회"""
        session = get_session()
        try:
            codes = session.query(RedeemCode).order_by(
                RedeemCode.game, 
                RedeemCode.created_at.desc()
            ).all()
            return codes
        finally:
            session.close()
    
    def mark_invalid(self, code: str) -> bool:
        """코드를 무효 상태로 변경"""
        session = get_session()
        try:
            code_obj = session.query(RedeemCode).filter_by(code=code).first()
            if code_obj:
                code_obj.is_valid = False
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def get_stats(self) -> dict:
        """데이터베이스 통계를 반환"""
        session = get_session()
        try:
            total = session.query(RedeemCode).count()
            valid = session.query(RedeemCode).filter_by(is_valid=True).count()
            
            from sqlalchemy import func
            game_stats = session.query(
                RedeemCode.game,
                func.count(RedeemCode.id)
            ).group_by(RedeemCode.game).all()
            
            return {
                "total_codes": total,
                "valid_codes": valid,
                "invalid_codes": total - valid,
                "by_game": {game: count for game, count in game_stats}
            }
        finally:
            session.close()


class ArticleService:
    """
    스크래핑한 게시글 관리 서비스
    
    이미 방문한 URL을 기록하여 중복 스크래핑을 방지합니다.
    """
    
    def __init__(self):
        init_db()
    
    def is_scraped(self, url: str) -> bool:
        """URL이 이미 스크래핑되었는지 확인"""
        session = get_session()
        try:
            # URL에서 쿼리 파라미터 제거하여 기본 URL만 비교
            base_url = url.split('?')[0]
            exists = session.query(ScrapedArticle).filter(
                ScrapedArticle.url.like(f"{base_url}%")
            ).first() is not None
            return exists
        finally:
            session.close()
    
    def mark_scraped(self, url: str, game: str, title: str = None, codes_found: int = 0) -> bool:
        """URL을 스크래핑 완료로 기록"""
        session = get_session()
        try:
            article = ScrapedArticle(
                url=url,
                game=game,
                title=title,
                codes_found=codes_found
            )
            session.add(article)
            session.commit()
            return True
        except IntegrityError:
            session.rollback()
            return False  # 이미 존재
        finally:
            session.close()
    
    def get_scraped_count(self, game: str = None) -> int:
        """스크래핑한 게시글 수 조회"""
        session = get_session()
        try:
            query = session.query(ScrapedArticle)
            if game:
                query = query.filter_by(game=game)
            return query.count()
        finally:
            session.close()
    
    def get_recent_scraped(self, game: str = None, limit: int = 10) -> List[ScrapedArticle]:
        """최근 스크래핑한 게시글 목록"""
        session = get_session()
        try:
            query = session.query(ScrapedArticle)
            if game:
                query = query.filter_by(game=game)
            return query.order_by(ScrapedArticle.scraped_at.desc()).limit(limit).all()
        finally:
            session.close()


class SiteService:
    """
    게임별 스크래핑 사이트 관리 서비스
    """
    
    # 기본 사이트 설정 (초기화용)
    DEFAULT_SITES = [
        {
            "game": "genshin",
            "game_name": "원신",
            "site_name": "아카라이브",
            "search_url": "https://arca.live/b/genshin?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4"
        },
        {
            "game": "starrail",
            "game_name": "붕괴: 스타레일",
            "site_name": "아카라이브",
            "search_url": "https://arca.live/b/starrail?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4"
        },
        {
            "game": "zzz",
            "game_name": "젠레스 존 제로",
            "site_name": "아카라이브",
            "search_url": "https://arca.live/b/zenlesszonezero?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4"
        },
        {
            "game": "honkai3rd",
            "game_name": "붕괴3rd",
            "site_name": "아카라이브",
            "search_url": "https://arca.live/b/honkai3rd?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4"
        },
        {
            "game": "wuwa",
            "game_name": "명조: 워더링 웨이브",
            "site_name": "아카라이브",
            "search_url": "https://arca.live/b/wutheringwaves?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4"
        },
    ]
    
    def __init__(self):
        init_db()
        self._init_default_sites()
    
    def _init_default_sites(self):
        """기본 사이트 설정 초기화"""
        session = get_session()
        try:
            # 사이트가 없으면 기본값 추가
            if session.query(GameSite).count() == 0:
                for site_config in self.DEFAULT_SITES:
                    site = GameSite(**site_config)
                    session.add(site)
                session.commit()
        except:
            session.rollback()
        finally:
            session.close()
    
    def get_all_sites(self, active_only: bool = True) -> List[GameSite]:
        """모든 사이트 목록 조회"""
        session = get_session()
        try:
            query = session.query(GameSite)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.order_by(GameSite.game, GameSite.site_name).all()
        finally:
            session.close()
    
    def get_sites_by_game(self, game: str, active_only: bool = True) -> List[GameSite]:
        """게임별 사이트 목록 조회"""
        session = get_session()
        try:
            query = session.query(GameSite).filter_by(game=game)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()
        finally:
            session.close()
    
    def get_all_games(self) -> List[str]:
        """등록된 모든 게임 목록"""
        session = get_session()
        try:
            games = session.query(GameSite.game, GameSite.game_name).distinct().all()
            return games
        finally:
            session.close()
    
    def add_site(self, game: str, game_name: str, site_name: str, search_url: str) -> Tuple[bool, str]:
        """새 사이트 추가"""
        session = get_session()
        try:
            site = GameSite(
                game=game,
                game_name=game_name,
                site_name=site_name,
                search_url=search_url
            )
            session.add(site)
            session.commit()
            return (True, f"사이트 추가됨: [{game_name}] {site_name}")
        except IntegrityError:
            session.rollback()
            return (False, f"이미 존재하는 사이트: [{game}] {site_name}")
        finally:
            session.close()
    
    def remove_site(self, game: str, site_name: str) -> bool:
        """사이트 삭제"""
        session = get_session()
        try:
            site = session.query(GameSite).filter_by(game=game, site_name=site_name).first()
            if site:
                session.delete(site)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def toggle_site(self, game: str, site_name: str) -> Tuple[bool, bool]:
        """사이트 활성화/비활성화 토글"""
        session = get_session()
        try:
            site = session.query(GameSite).filter_by(game=game, site_name=site_name).first()
            if site:
                site.is_active = not site.is_active
                session.commit()
                return (True, site.is_active)
            return (False, False)
        finally:
            session.close()
    
    def update_url(self, game: str, site_name: str, new_url: str) -> bool:
        """사이트 URL 업데이트"""
        session = get_session()
        try:
            site = session.query(GameSite).filter_by(game=game, site_name=site_name).first()
            if site:
                site.search_url = new_url
                session.commit()
                return True
            return False
        finally:
            session.close()
