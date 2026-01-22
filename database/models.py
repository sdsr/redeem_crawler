"""
데이터베이스 모델 정의

SQLAlchemy ORM을 사용하여 리딤코드 데이터를 관리합니다.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Index, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

Base = declarative_base()


class RedeemCode(Base):
    """
    리딤코드 모델
    
    Attributes:
        id: 기본 키 (자동 증가)
        code: 리딤코드 문자열 (유니크)
        game: 게임 종류 (genshin, starrail, zzz)
        source_url: 코드를 발견한 게시글 URL
        source_title: 게시글 제목
        is_valid: 코드 유효 여부 (기본값: True)
        created_at: 생성 시간
        updated_at: 수정 시간
    """
    __tablename__ = "redeem_codes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    game = Column(String(20), nullable=False, index=True)
    source_url = Column(String(500), nullable=True)
    source_title = Column(String(200), nullable=True)
    is_valid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 복합 인덱스: 게임별 코드 조회 최적화
    __table_args__ = (
        Index('ix_game_code', 'game', 'code'),
    )
    
    def __repr__(self):
        return f"<RedeemCode(id={self.id}, code='{self.code}', game='{self.game}')>"
    
    def to_dict(self):
        """모델을 딕셔너리로 변환"""
        return {
            "id": self.id,
            "code": self.code,
            "game": self.game,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScrapedArticle(Base):
    """
    스크래핑한 게시글 기록
    
    이미 방문한 게시글을 기록하여 중복 스크래핑을 방지합니다.
    
    Attributes:
        id: 기본 키
        url: 게시글 URL (유니크)
        game: 게임 종류
        title: 게시글 제목
        codes_found: 발견된 코드 수
        scraped_at: 스크래핑 시간
    """
    __tablename__ = "scraped_articles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False, unique=True, index=True)
    game = Column(String(20), nullable=False, index=True)
    title = Column(String(300), nullable=True)
    codes_found = Column(Integer, default=0)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ScrapedArticle(id={self.id}, game='{self.game}', title='{self.title[:30]}...')>"


class GameSite(Base):
    """
    게임별 스크래핑 사이트 설정
    
    여러 사이트에서 리딤코드를 수집할 수 있도록 사이트 목록을 관리합니다.
    
    Attributes:
        id: 기본 키
        game: 게임 식별자 (genshin, starrail, zzz 등)
        game_name: 게임 이름 (표시용)
        site_name: 사이트 이름 (예: 아카라이브, 루리웹 등)
        search_url: 검색 URL
        is_active: 활성화 여부
        created_at: 생성 시간
    """
    __tablename__ = "game_sites"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game = Column(String(20), nullable=False, index=True)
    game_name = Column(String(50), nullable=False)
    site_name = Column(String(50), nullable=False)
    search_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 게임+사이트 조합은 유니크
    __table_args__ = (
        Index('ix_game_site', 'game', 'site_name', unique=True),
    )
    
    def __repr__(self):
        return f"<GameSite(game='{self.game}', site='{self.site_name}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "game": self.game,
            "game_name": self.game_name,
            "site_name": self.site_name,
            "search_url": self.search_url,
            "is_active": self.is_active,
        }


def get_engine():
    """SQLAlchemy 엔진 생성"""
    return create_engine(DATABASE_URL, echo=False)


def get_session():
    """데이터베이스 세션 생성"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """
    데이터베이스 초기화 (테이블 생성)
    
    Base.metadata.create_all()은 정의된 모든 모델의 테이블을 생성합니다.
    이미 존재하는 테이블은 건너뜁니다 (DROP하지 않음).
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
