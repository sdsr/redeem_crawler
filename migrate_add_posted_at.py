"""
DB 마이그레이션: source_posted_at 컬럼 추가

기존 redeem_codes 테이블에 원본 게시글 작성일 컬럼을 추가합니다.
"""

import sqlite3
import os

DB_PATH = 'redeem_codes.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"[오류] {DB_PATH} 파일이 없습니다.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 컬럼이 이미 있는지 확인
        cursor.execute("PRAGMA table_info(redeem_codes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'source_posted_at' in columns:
            print("[정보] source_posted_at 컬럼이 이미 존재합니다.")
            return True
        
        # 컬럼 추가
        cursor.execute('ALTER TABLE redeem_codes ADD COLUMN source_posted_at DATETIME')
        conn.commit()
        print("[완료] source_posted_at 컬럼 추가 완료!")
        return True
        
    except Exception as e:
        print(f"[오류] 마이그레이션 실패: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
