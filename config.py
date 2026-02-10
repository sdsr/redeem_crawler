"""
리딤코드 스크래퍼 설정 파일
"""

# 데이터베이스 설정
DATABASE_URL = "sqlite:///redeem_codes.db"

# 아카라이브 URL 설정
ARCA_BASE_URL = "https://arca.live"

# 게임별 게시판 및 검색 URL
GAME_CONFIGS = {
    "genshin": {
        "name": "원신",
        "board_url": "https://arca.live/b/genshin",
        "search_url": "https://arca.live/b/genshin?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4",
        # 리딤코드 패턴: 대문자+숫자, 8-16자 (원신 리딤코드 형식)
        "code_patterns": [
            r'\b[A-Z0-9]{8,16}\b',  # 기본 패턴
        ],
        # 제외할 패턴 (너무 일반적인 단어들)
        "exclude_patterns": [
            r'^[A-Z]{1,3}$',  # 1-3글자 대문자만
            r'^[0-9]+$',  # 숫자만
            r'^HTTP[S]?$',
            r'^URL$',
            r'^API$',
        ]
    },
    "starrail": {
        "name": "붕괴: 스타레일",
        "board_url": "https://arca.live/b/starrail",
        "search_url": "https://arca.live/b/starrail?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4",
        "code_patterns": [
            r'\b[A-Z0-9]{8,16}\b',
        ],
        "exclude_patterns": []
    },
    "zzz": {
        "name": "젠레스 존 제로",
        "board_url": "https://arca.live/b/zenlesszonezero",
        "search_url": "https://arca.live/b/zenlesszonezero?category=%F0%9F%92%A1%EC%A0%95%EB%B3%B4&target=all&keyword=%EB%A6%AC%EB%94%A4",
        "code_patterns": [
            r'\b[A-Z0-9]{8,16}\b',
        ],
        "exclude_patterns": []
    }
}

# HTTP 요청 설정
# 아카라이브는 봇 차단이 있으므로 실제 브라우저와 유사하게 설정
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# 요청 간 대기 시간 (초)
REQUEST_DELAY = 1.0

# 스크래핑 날짜 필터 (일)
# 이 기간보다 오래된 게시글은 스크래핑하지 않음
MAX_AGE_DAYS = 90
