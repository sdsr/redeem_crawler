"""
리딤코드 웹 뷰어

Flask 기반 웹 애플리케이션으로 저장된 리딤코드를 확인합니다.
"""

from flask import Flask, render_template, jsonify, request, session
from database import get_session, RedeemCode
from sqlalchemy import func
from datetime import datetime, date, timedelta
import threading
import subprocess
import sys
import os
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 세션용 시크릿 키

# 관리자 비밀번호 (원하는 값으로 변경하세요)
ADMIN_PASSWORD = "admin1234"

# 스크래핑 상태 관리
scrape_state = {
    'is_running': False,
    'last_run': None,
    'last_result': None,
    'cooldown_minutes': 3  # 쿨타임 3분
}
scrape_lock = threading.Lock()


def get_all_codes():
    """DB에서 모든 코드 조회 (삭제되지 않은 것만)"""
    session = get_session()
    today = date.today()
    
    try:
        # is_deleted=False인 코드만 조회 (Soft Delete 적용)
        codes = session.query(RedeemCode).filter(
            RedeemCode.is_deleted == False
        ).order_by(
            RedeemCode.game,
            RedeemCode.created_at.desc()
        ).all()
        
        result = []
        for code in codes:
            # 오늘 추가된 코드인지 확인
            is_new = False
            if code.created_at:
                is_new = code.created_at.date() == today
            
            result.append({
                'id': code.id,
                'code': code.code,
                'game': code.game,
                'source_title': code.source_title or '',
                'source_url': code.source_url or '',
                'is_valid': code.is_valid,
                'is_new': is_new,
                'created_at': code.created_at.strftime('%Y-%m-%d %H:%M') if code.created_at else ''
            })
        return result
    finally:
        session.close()


def get_today_count():
    """오늘 추가된 코드 수 (삭제되지 않은 것만)"""
    session = get_session()
    today = date.today()
    try:
        count = session.query(func.count(RedeemCode.id)).filter(
            func.date(RedeemCode.created_at) == today,
            RedeemCode.is_deleted == False
        ).scalar()
        return count or 0
    finally:
        session.close()


def get_stats():
    """통계 정보 조회 (삭제되지 않은 것만)"""
    session = get_session()
    try:
        total = session.query(func.count(RedeemCode.id)).filter(
            RedeemCode.is_deleted == False
        ).scalar()
        
        # 게임별 통계 (삭제되지 않은 것만)
        game_stats = session.query(
            RedeemCode.game,
            func.count(RedeemCode.id)
        ).filter(
            RedeemCode.is_deleted == False
        ).group_by(RedeemCode.game).all()
        
        return {
            'total': total,
            'by_game': {game: count for game, count in game_stats}
        }
    finally:
        session.close()


def run_scraper():
    """백그라운드에서 스크래퍼 실행"""
    global scrape_state
    
    print("\n" + "="*50)
    print("[스크래핑 시작]")
    print("="*50)
    
    try:
        # main.py --scrape 실행 (실시간 출력)
        process = subprocess.Popen(
            [sys.executable, 'main.py', '--scrape'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            bufsize=1,  # 라인 버퍼링
            encoding='utf-8',
            errors='replace'
        )
        
        output_lines = []
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(line, end='')  # 실시간 콘솔 출력
                    output_lines.append(line)
            process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            process.kill()
            with scrape_lock:
                scrape_state['last_result'] = {
                    'success': False,
                    'output': ''.join(output_lines[-50:]),
                    'error': '스크래핑 시간 초과 (5분)'
                }
            return
        
        with scrape_lock:
            scrape_state['last_result'] = {
                'success': process.returncode == 0,
                'output': ''.join(output_lines[-50:]),  # 마지막 50줄
                'error': '' if process.returncode == 0 else f'Exit code: {process.returncode}'
            }
            
        print("\n" + "="*50)
        print(f"[스크래핑 완료] 결과: {'성공' if process.returncode == 0 else '실패'}")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n[스크래핑 오류] {e}\n")
        with scrape_lock:
            scrape_state['last_result'] = {
                'success': False,
                'output': '',
                'error': str(e)
            }
    finally:
        with scrape_lock:
            scrape_state['is_running'] = False


# 게임 정보 (표시 이름, 색상, 로컬 아이콘)
# 아이콘은 static/icons/ 폴더에 저장됨 (나무위키에서 다운로드)
GAME_INFO = {
    'genshin': {
        'name': '원신',
        'color': '#FFB13B',
        'gradient': 'linear-gradient(135deg, #FFB13B 0%, #FF6B35 100%)',
        'icon': '/static/icons/genshin.webp',
        'redeem_url': 'https://genshin.hoyoverse.com/ko/gift?code='
    },
    'starrail': {
        'name': '스타레일',
        'color': '#9B8AFF',
        'gradient': 'linear-gradient(135deg, #9B8AFF 0%, #6366F1 100%)',
        'icon': '/static/icons/starrail.webp',
        'redeem_url': 'https://hsr.hoyoverse.com/gift?code='
    },
    'zzz': {
        'name': '젠레스 존 제로',
        'color': '#FF4757',
        'gradient': 'linear-gradient(135deg, #FF4757 0%, #C44569 100%)',
        'icon': '/static/icons/zzz.webp',
        'redeem_url': 'https://zenless.hoyoverse.com/redemption?code='
    },
    'honkai3rd': {
        'name': '붕괴3rd',
        'color': '#00D9FF',
        'gradient': 'linear-gradient(135deg, #00D9FF 0%, #0099CC 100%)',
        'icon': '/static/icons/honkai3rd.webp',
        'redeem_url': ''
    },
    'wuwa': {
        'name': '명조',
        'color': '#7ED321',
        'gradient': 'linear-gradient(135deg, #7ED321 0%, #4A9F2E 100%)',
        'icon': '/static/icons/wuwa.webp',
        'redeem_url': ''
    },
    'bluearchive': {
        'name': '블루 아카이브',
        'color': '#00BFFF',
        'gradient': 'linear-gradient(135deg, #00BFFF 0%, #1E90FF 100%)',
        'icon': '/static/icons/bluearchive.webp',
        'redeem_url': ''
    },
    'nikke': {
        'name': '니케',
        'color': '#FF69B4',
        'gradient': 'linear-gradient(135deg, #FF69B4 0%, #DB7093 100%)',
        'icon': '/static/icons/nikke.webp',
        'redeem_url': ''
    },
    'gfl2': {
        'name': '소녀전선2',
        'color': '#E74C3C',
        'gradient': 'linear-gradient(135deg, #E74C3C 0%, #C0392B 100%)',
        'icon': '/static/icons/gfl2.webp',
        'redeem_url': ''
    },
    'trikkal': {
        'name': '트릭컬',
        'color': '#9B59B6',
        'gradient': 'linear-gradient(135deg, #9B59B6 0%, #8E44AD 100%)',
        'icon': '/static/icons/trikkal.webp',
        'redeem_url': ''
    },
    'arknights': {
        'name': '명일방주',
        'color': '#1ABC9C',
        'gradient': 'linear-gradient(135deg, #1ABC9C 0%, #16A085 100%)',
        'icon': '/static/icons/arknights.webp',
        'redeem_url': ''
    },
    'endfield': {
        'name': '엔드필드',
        'color': '#3498DB',
        'gradient': 'linear-gradient(135deg, #3498DB 0%, #2980B9 100%)',
        'icon': '/static/icons/endfield.webp',
        'redeem_url': ''
    }
}


def check_admin():
    """관리자 모드 확인"""
    # URL 파라미터로 관리자 모드 활성화
    if request.args.get('admin') == ADMIN_PASSWORD:
        session['is_admin'] = True
    # 로그아웃
    if request.args.get('logout') == '1':
        session.pop('is_admin', None)
    return session.get('is_admin', False)


@app.route('/')
def index():
    """메인 페이지"""
    is_admin = check_admin()
    
    codes = get_all_codes()
    stats = get_stats()
    today_count = get_today_count()
    
    # 게임별로 그룹화
    codes_by_game = {}
    for code in codes:
        game = code['game']
        if game not in codes_by_game:
            codes_by_game[game] = []
        codes_by_game[game].append(code)
    
    # 스크래핑 상태
    with scrape_lock:
        scrape_info = {
            'is_running': scrape_state['is_running'],
            'last_run': scrape_state['last_run'].isoformat() if scrape_state['last_run'] else None,
            'cooldown_minutes': scrape_state['cooldown_minutes']
        }
    
    return render_template('index.html', 
                         codes_by_game=codes_by_game,
                         stats=stats,
                         game_info=GAME_INFO,
                         today_count=today_count,
                         scrape_info=scrape_info,
                         is_admin=is_admin,
                         now=datetime.now)


@app.route('/api/codes')
def api_codes():
    """API: 코드 목록"""
    codes = get_all_codes()
    return jsonify(codes)


@app.route('/api/stats')
def api_stats():
    """API: 통계"""
    stats = get_stats()
    return jsonify(stats)


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API: 스크래핑 시작"""
    global scrape_state
    
    with scrape_lock:
        # 이미 실행 중인지 확인
        if scrape_state['is_running']:
            return jsonify({
                'success': False,
                'message': '스크래핑이 이미 진행 중입니다.',
                'is_running': True
            })
        
        # 쿨타임 확인
        if scrape_state['last_run']:
            elapsed = datetime.now() - scrape_state['last_run']
            cooldown = timedelta(minutes=scrape_state['cooldown_minutes'])
            if elapsed < cooldown:
                remaining = cooldown - elapsed
                remaining_seconds = int(remaining.total_seconds())
                return jsonify({
                    'success': False,
                    'message': f'쿨타임 중입니다. {remaining_seconds}초 후에 다시 시도하세요.',
                    'remaining_seconds': remaining_seconds,
                    'is_running': False
                })
        
        # 스크래핑 시작
        scrape_state['is_running'] = True
        scrape_state['last_run'] = datetime.now()
        scrape_state['last_result'] = None
    
    # 백그라운드에서 실행
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': '스크래핑을 시작했습니다.',
        'is_running': True
    })


@app.route('/api/scrape/status')
def api_scrape_status():
    """API: 스크래핑 상태 확인"""
    with scrape_lock:
        # 남은 쿨타임 계산
        remaining_seconds = 0
        if scrape_state['last_run'] and not scrape_state['is_running']:
            elapsed = datetime.now() - scrape_state['last_run']
            cooldown = timedelta(minutes=scrape_state['cooldown_minutes'])
            if elapsed < cooldown:
                remaining_seconds = int((cooldown - elapsed).total_seconds())
        
        return jsonify({
            'is_running': scrape_state['is_running'],
            'last_run': scrape_state['last_run'].strftime('%Y-%m-%d %H:%M:%S') if scrape_state['last_run'] else None,
            'remaining_seconds': remaining_seconds,
            'last_result': scrape_state['last_result']
        })


@app.route('/api/scrape/ack', methods=['POST'])
def api_scrape_ack():
    """API: 스크래핑 결과 확인 완료 (결과 리셋)
    
    클라이언트에서 결과를 확인한 후 호출하여 중복 새로고침 방지
    """
    global scrape_state
    with scrape_lock:
        scrape_state['last_result'] = None
    return jsonify({'success': True})


@app.route('/api/codes/delete/<int:code_id>', methods=['DELETE'])
def api_delete_code(code_id):
    """API: 리딤코드 삭제 (관리자 전용, Soft Delete)
    
    Soft Delete: 실제로 DB에서 삭제하지 않고 is_deleted=True로 표시
    이렇게 하면 다음 스크래핑에서 같은 코드를 다시 가져오지 않음
    """
    # 관리자 권한 확인
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    db_session = get_session()
    try:
        code = db_session.query(RedeemCode).filter_by(id=code_id).first()
        if not code:
            return jsonify({'success': False, 'message': '코드를 찾을 수 없습니다.'}), 404
        
        deleted_code = code.code
        # Soft Delete: is_deleted=True로 표시 (실제 삭제 아님)
        code.is_deleted = True
        db_session.commit()
        
        return jsonify({
            'success': True,
            'message': f'"{deleted_code}" 삭제됨',
            'deleted_id': code_id
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db_session.close()


@app.route('/api/codes/refresh')
def api_refresh_codes():
    """API: 코드 목록 새로고침 (AJAX용)"""
    codes = get_all_codes()
    stats = get_stats()
    today_count = get_today_count()
    
    # 게임별로 그룹화
    codes_by_game = {}
    for code in codes:
        game = code['game']
        if game not in codes_by_game:
            codes_by_game[game] = []
        codes_by_game[game].append(code)
    
    return jsonify({
        'codes_by_game': codes_by_game,
        'stats': stats,
        'today_count': today_count
    })


if __name__ == '__main__':
    print("=" * 50)
    print("  리딤코드 뷰어 시작")
    print("  http://localhost:5000 에서 확인하세요")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
