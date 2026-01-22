"""
리딤코드 추출 유틸리티

정규표현식을 사용하여 텍스트에서 리딤코드를 추출합니다.
"""

import re
from typing import List, Set


class CodeExtractor:
    """
    텍스트에서 리딤코드를 추출하는 클래스
    
    정규표현식 패턴 매칭을 사용하여 리딤코드 형식의 문자열을 찾습니다.
    
    원신/스타레일/젠존제 리딤코드 특징:
    - 대문자 영문자와 숫자로 구성
    - 길이는 보통 8-16자
    - 예: GENSHINGIFT, VTPU3CQWYCSD, STARRAILGIFT
    """
    
    # 일반적인 리딤코드 패턴
    # \b: 단어 경계 (word boundary)
    # [A-Z0-9]: 대문자 또는 숫자
    # {8,16}: 8자 이상 16자 이하
    DEFAULT_PATTERN = r'\b[A-Z0-9]{8,16}\b'
    
    # 제외할 일반적인 단어들 (리딤코드가 아닌 것들)
    COMMON_EXCLUSIONS = {
        # 일반적인 약어 및 기술 용어
        'HTTPS', 'HTTP', 'HTML', 'CSS', 'JSON', 'XML', 'JAVASCRIPT',
        'YOUTUBE', 'TWITTER', 'FACEBOOK', 'INSTAGRAM', 'DISCORD',
        'GOOGLE', 'CHROME', 'FIREFOX', 'SAFARI', 'WINDOWS', 'ANDROID',
        # 게임 관련 일반 단어
        'GENSHIN', 'IMPACT', 'STARRAIL', 'HONKAI', 'MIHOYO', 'HOYOVERSE',
        'ZENLESS', 'ZONEZERO', 'TEYVAT', 'FONTAINE', 'SUMERU', 'INAZUMA',
        # 일반적인 영어 단어
        'SPREADSHEETS', 'SPREADSHEET', 'DOWNLOAD', 'UPLOADED', 'COMMUNITY',
        'OFFICIAL', 'INFORMATION', 'REDEEM', 'REDEMPTION', 'PRIMOGEMS',
        'CHARACTER', 'CHARACTERS', 'CONSTELLATION', 'CONSTELLATIONS',
        'ANNIVERSARY', 'LIVESTREAM', 'BROADCAST', 'MAINTENANCE',
        'INTERTWINED', 'ACQUAINT', 'STARDUST', 'STARGLITTER',
        'ADVENTURE', 'TRAVELERS', 'TRAVELER', 'BLESSING', 'WELKIN',
        'GENESIS', 'CRYSTALS', 'RESIN', 'FRAGILE', 'ORIGINAL',
        'ARTIFACT', 'ARTIFACTS', 'WEAPON', 'WEAPONS', 'DOMAIN',
        'COMMISSION', 'COMMISSIONS', 'REPUTATION', 'EXPLORATION',
        'ABYSS', 'SPIRAL', 'FLOOR', 'CHAMBER', 'VERSION', 'UPDATE',
        'PREMIUM', 'SUBSCRIPTION', 'PURCHASE', 'PAYMENT', 'REWARD',
    }
    
    def __init__(self, patterns: List[str] = None, exclusions: Set[str] = None):
        """
        Args:
            patterns: 사용할 정규표현식 패턴 리스트
            exclusions: 제외할 단어 집합
        """
        self.patterns = patterns or [self.DEFAULT_PATTERN]
        self.exclusions = exclusions or self.COMMON_EXCLUSIONS
        
        # 정규표현식 컴파일 (성능 최적화)
        # re.compile()은 패턴을 미리 컴파일하여 반복 사용 시 성능 향상
        self.compiled_patterns = [re.compile(p) for p in self.patterns]
    
    # URL에서 코드를 추출하는 패턴
    # 호요버스 리딤 URL 예시:
    # - https://genshin.hoyoverse.com/ko/gift?code=GENSHINQUIZ2026
    # - https://hsr.hoyoverse.com/gift?code=XXXXX
    # - https://zenless.hoyoverse.com/redemption?code=XXXXX
    URL_CODE_PATTERN = re.compile(r'[?&]code=([A-Za-z0-9]+)', re.IGNORECASE)
    
    def extract_from_url(self, text: str) -> List[str]:
        """
        텍스트에서 URL의 code 파라미터를 추출합니다.
        
        Args:
            text: URL이 포함된 텍스트
            
        Returns:
            URL에서 발견된 리딤코드 리스트
            
        예시:
            "https://genshin.hoyoverse.com/ko/gift?code=GENSHINQUIZ2026"
            -> ["GENSHINQUIZ2026"]
        """
        if not text:
            return []
        
        matches = self.URL_CODE_PATTERN.findall(text)
        # 대문자로 변환하여 반환
        return [code.upper() for code in matches]
    
    def extract(self, text: str) -> List[str]:
        """
        텍스트에서 리딤코드를 추출합니다.
        
        Args:
            text: 리딤코드를 찾을 텍스트
            
        Returns:
            발견된 리딤코드 리스트 (중복 제거됨)
            
        사용된 문법:
        - set(): 중복 제거를 위한 집합 자료형
        - findall(): 패턴에 매칭되는 모든 문자열 반환
        """
        if not text:
            return []
        
        # 대문자로 변환하여 검색 (리딤코드는 대소문자 구분 없이 입력 가능)
        text_upper = text.upper()
        
        found_codes: Set[str] = set()
        
        # 1. URL에서 코드 추출 (우선순위 높음 - 검증 없이 추가)
        url_codes = self.extract_from_url(text)
        found_codes.update(url_codes)
        
        # 2. 일반 패턴으로 코드 추출
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text_upper)
            found_codes.update(matches)
        
        # 제외 목록에 있는 단어 필터링
        # URL에서 추출된 코드는 이미 검증됐으므로 유지
        filtered_codes = [
            code for code in found_codes 
            if code in url_codes or (code not in self.exclusions and self._is_valid_code(code))
        ]
        
        return sorted(filtered_codes)  # 정렬하여 반환
    
    def _is_valid_code(self, code: str) -> bool:
        """
        리딤코드 유효성 검사
        
        Args:
            code: 검사할 코드
            
        Returns:
            유효한 리딤코드 여부
            
        검사 조건:
        1. 숫자만 있으면 안 됨 (일반 숫자와 구분)
        2. 영문자만 있고 일반 단어 패턴이면 제외
        3. 최소 하나의 숫자와 영문자가 섞여 있어야 함 (더 엄격하게)
        4. X가 3개 이상 연속이면 제외 (마스킹된 값)
        
        원신 리딤코드 예시:
        - GENSHINGIFT (영문자만, 특별 이벤트용)
        - VTPU3CQWYCSD (영문자+숫자 혼합, 일반적)
        - 3TPUKSV8C5X9 (숫자로 시작)
        """
        # 숫자만 있는 경우 제외
        if code.isdigit():
            return False
        
        # 너무 짧은 경우 제외 (리딤코드는 보통 12자)
        if len(code) < 10:
            return False
        
        # X가 4개 이상 연속이면 제외 (마스킹된 전화번호, 계좌번호 등)
        # 예: 130XXXXXXX, 010-XXXX-XXXX
        if 'XXXX' in code:
            return False
        
        # 영문자와 숫자가 적절히 섞여 있는지 확인
        has_letter = any(c.isalpha() for c in code)
        has_digit = any(c.isdigit() for c in code)
        
        # 영문자+숫자 조합이 가장 일반적인 리딤코드 형식
        if has_letter and has_digit:
            return True
        
        # 영문자만 있는 경우: 특별 이벤트 코드일 수 있음
        # 하지만 일반 영어 단어와 구분하기 어려우므로 
        # 특별히 알려진 패턴만 허용 (예: GENSHINGIFT 형태)
        if has_letter and not has_digit:
            # 영문자만 있는 코드는 매우 드물고
            # 대부분 일반 단어이므로 기본적으로 제외
            # 단, 특별히 "GIFT", "CODE", "REWARD" 등이 포함된 경우 허용
            special_keywords = ['GIFT', 'CODE', 'REWARD', 'FREE', 'BONUS']
            for keyword in special_keywords:
                if keyword in code and code != keyword:
                    return True
            return False
        
        return False
    
    def extract_from_html(self, html_text: str) -> List[str]:
        """
        HTML에서 리딤코드를 추출합니다.
        
        HTML 태그를 제거하고 순수 텍스트에서 코드를 찾습니다.
        
        Args:
            html_text: HTML 문자열
            
        Returns:
            발견된 리딤코드 리스트
        """
        # 간단한 HTML 태그 제거
        # re.sub(pattern, replacement, string)
        clean_text = re.sub(r'<[^>]+>', ' ', html_text)
        return self.extract(clean_text)
