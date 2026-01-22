"""
사이트 목록 관리자

sites.json 파일을 읽고 관리합니다.
"""

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass


SITES_FILE = "sites.json"


@dataclass
class SiteConfig:
    """
    사이트 설정 데이터 클래스
    
    Attributes:
        game: 게임 식별자 (genshin, starrail, _multi 등)
        game_name: 게임 이름 (표시용)
        site_type: 사이트 유형 (arca, youtube, custom)
        site_name: 사이트 이름
        url: 스크래핑 URL
        enabled: 활성화 여부
        options: 추가 옵션 (게임 태그 파싱 등)
    """
    game: str
    game_name: str
    site_type: str
    site_name: str
    url: str
    enabled: bool = True
    options: Dict = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}
    
    def to_dict(self) -> dict:
        result = {
            "game": self.game,
            "game_name": self.game_name,
            "site_type": self.site_type,
            "site_name": self.site_name,
            "url": self.url,
            "enabled": self.enabled
        }
        if self.options:
            result["options"] = self.options
        return result
    
    @property
    def is_multi_game(self) -> bool:
        """여러 게임 코드가 섞인 사이트인지"""
        return self.game == "_multi" or self.options.get("parse_game_tags", False)
    
    @property
    def game_tags(self) -> Dict[str, str]:
        """게임 태그 -> 게임ID 매핑"""
        return self.options.get("game_tags", {})


class SiteManager:
    """
    sites.json 파일 기반 사이트 관리자
    
    사용법:
        manager = SiteManager()
        sites = manager.get_enabled_sites()
        sites = manager.get_sites_by_game("genshin")
    """
    
    # 기본 키워드 (sites.json에 keywords가 없을 때 사용)
    DEFAULT_KEYWORDS = [
        "리딤", "쿠폰", "코드", "기프트", "보상",
        "redeem", "coupon", "code", "gift", "reward"
    ]
    
    def __init__(self, sites_file: str = SITES_FILE):
        self.sites_file = sites_file
        self._sites: List[SiteConfig] = []
        self._keywords: List[str] = []
        self._load()
    
    def _load(self):
        """JSON 파일에서 사이트 목록 로드"""
        if not os.path.exists(self.sites_file):
            print(f"[경고] {self.sites_file} 파일이 없습니다. 빈 목록으로 시작합니다.")
            self._sites = []
            self._keywords = self.DEFAULT_KEYWORDS
            return
        
        try:
            with open(self.sites_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 키워드 로드
            self._keywords = data.get("keywords", self.DEFAULT_KEYWORDS)
            
            self._sites = []
            for site_data in data.get("sites", []):
                site = SiteConfig(
                    game=site_data.get("game", ""),
                    game_name=site_data.get("game_name", ""),
                    site_type=site_data.get("site_type", "arca"),
                    site_name=site_data.get("site_name", ""),
                    url=site_data.get("url", ""),
                    enabled=site_data.get("enabled", True),
                    options=site_data.get("options", {})
                )
                self._sites.append(site)
            
            print(f"[정보] {len(self._sites)}개 사이트 설정 로드됨")
            print(f"[정보] 키워드 필터: {self._keywords}")
            
        except json.JSONDecodeError as e:
            print(f"[오류] JSON 파싱 실패: {e}")
            self._sites = []
            self._keywords = self.DEFAULT_KEYWORDS
    
    def _save(self):
        """사이트 목록을 JSON 파일에 저장"""
        data = {
            "sites": [site.to_dict() for site in self._sites],
            "_comment": {
                "site_type": "arca(아카라이브), youtube(유튜브 커뮤니티), custom(기타)",
                "enabled": "false로 설정하면 스크래핑 제외"
            }
        }
        
        with open(self.sites_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[정보] {self.sites_file} 저장됨")
    
    def get_all_sites(self) -> List[SiteConfig]:
        """모든 사이트 반환"""
        return self._sites
    
    def get_enabled_sites(self) -> List[SiteConfig]:
        """활성화된 사이트만 반환"""
        return [s for s in self._sites if s.enabled]
    
    def get_sites_by_game(self, game: str) -> List[SiteConfig]:
        """특정 게임의 사이트만 반환"""
        return [s for s in self._sites if s.game == game and s.enabled]
    
    def get_sites_by_type(self, site_type: str) -> List[SiteConfig]:
        """특정 유형의 사이트만 반환"""
        return [s for s in self._sites if s.site_type == site_type and s.enabled]
    
    def get_all_games(self) -> List[tuple]:
        """등록된 게임 목록 반환 (game, game_name) 튜플"""
        games = {}
        for site in self._sites:
            if site.game not in games:
                games[site.game] = site.game_name
        return list(games.items())
    
    def add_site(self, game: str, game_name: str, site_type: str, 
                 site_name: str, url: str) -> bool:
        """새 사이트 추가"""
        # 중복 체크
        for site in self._sites:
            if site.game == game and site.site_name == site_name:
                print(f"[경고] 이미 존재하는 사이트: [{game}] {site_name}")
                return False
        
        new_site = SiteConfig(
            game=game,
            game_name=game_name,
            site_type=site_type,
            site_name=site_name,
            url=url,
            enabled=True
        )
        self._sites.append(new_site)
        self._save()
        return True
    
    def remove_site(self, game: str, site_name: str) -> bool:
        """사이트 삭제"""
        for i, site in enumerate(self._sites):
            if site.game == game and site.site_name == site_name:
                del self._sites[i]
                self._save()
                return True
        return False
    
    def toggle_site(self, game: str, site_name: str) -> Optional[bool]:
        """사이트 활성화/비활성화 토글, 새 상태 반환"""
        for site in self._sites:
            if site.game == game and site.site_name == site_name:
                site.enabled = not site.enabled
                self._save()
                return site.enabled
        return None
    
    def update_url(self, game: str, site_name: str, new_url: str) -> bool:
        """사이트 URL 업데이트"""
        for site in self._sites:
            if site.game == game and site.site_name == site_name:
                site.url = new_url
                self._save()
                return True
        return False
    
    def reload(self):
        """파일에서 다시 로드"""
        self._load()
    
    def get_keywords(self) -> List[str]:
        """키워드 목록 반환"""
        return self._keywords
    
    def has_keyword(self, text: str) -> bool:
        """
        텍스트에 키워드가 포함되어 있는지 확인
        
        Args:
            text: 검사할 텍스트 (제목 또는 본문)
            
        Returns:
            키워드가 하나라도 포함되어 있으면 True
            
        사용된 문법:
        - any(): 하나라도 True면 True 반환 (short-circuit evaluation)
        - lower(): 대소문자 무시하여 비교
        """
        if not text:
            return False
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self._keywords)
