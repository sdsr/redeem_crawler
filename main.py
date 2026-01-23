"""
리딤코드 스크래퍼 메인 실행 파일

사용법:
    python main.py                      # 모든 게임 스크래핑
    python main.py --game genshin       # 원신만 스크래핑
    python main.py --list               # 저장된 코드 목록
    python main.py --sites              # 등록된 사이트 목록 (sites.json)
    python main.py --force              # 이미 스크래핑한 URL도 다시 처리

사이트 설정:
    sites.json 파일을 직접 편집하여 사이트를 추가/수정/삭제할 수 있습니다.
"""

import argparse
import sys

sys.path.insert(0, '.')

from site_manager import SiteManager, SiteConfig
from scrapers.arca_scraper import ArcaScraper
from scrapers.youtube_scraper import YoutubeScraper
from services.code_service import CodeService, ArticleService


def scrape_site(site: SiteConfig, max_pages: int = 1, max_articles: int = 10,
                skip_scraped: bool = True, progress: str = "") -> dict:
    """
    단일 사이트 스크래핑
    
    Args:
        site: 사이트 설정
        max_pages: 최대 페이지 수 (아카라이브용)
        max_articles: 최대 게시글 수
        skip_scraped: 이미 방문한 URL 건너뛰기
        progress: 진행 상황 문자열 (예: "[1/5]")
        
    Returns:
        결과 딕셔너리
    """
    print(f"\n{'='*60}")
    print(f"{progress} [{site.game_name}] {site.site_name} 스크래핑 시작")
    print(f"    URL: {site.url[:60]}...")
    print(f"{'='*60}")
    
    service = CodeService()
    codes_to_save = []
    
    try:
        if site.site_type == "arca":
            # 아카라이브 스크래퍼
            scraper = ArcaScraper(site.game, search_url=site.url, skip_scraped=skip_scraped)
            try:
                articles = scraper.scrape_articles(
                    max_pages=max_pages,
                    max_articles=max_articles
                )
                
                for article in articles:
                    for code in article.codes:
                        codes_to_save.append({
                            "code": code,
                            "game": site.game,
                            "source_url": article.url,
                            "source_title": article.title,
                            "source_posted_at": article.posted_at  # 작성일 추가
                        })
            finally:
                scraper.close()
                
        elif site.site_type == "youtube":
            # 유튜브 스크래퍼 (멀티 게임 지원)
            game_tags = site.game_tags if site.is_multi_game else None
            scraper = YoutubeScraper(
                game=site.game,
                channel_url=site.url,
                skip_scraped=skip_scraped,
                game_tags=game_tags
            )
            try:
                results = scraper.scrape_posts(max_posts=max_articles)
                
                # GameCodeResult 리스트 처리
                for result in results:
                    for code in result.codes:
                        codes_to_save.append({
                            "code": code,
                            "game": result.game,  # 태그에서 파싱된 게임
                            "source_url": result.source_url,
                            "source_title": result.source_title
                        })
            finally:
                scraper.close()
        else:
            print(f"[오류] 지원하지 않는 사이트 유형: {site.site_type}")
            return {"saved": 0, "duplicates": 0, "errors": 1}
        
        if not codes_to_save:
            print(f"\n[완료] {site.game_name} - 새로운 리딤코드 없음")
            return {"saved": 0, "duplicates": 0}
        
        # 배치 저장
        results = service.save_codes_batch(codes_to_save)
        
        # 결과 출력
        print(f"\n[완료] {site.game_name} 스크래핑 결과:")
        if results["saved"] > 0:
            print(f"  + 새 코드 {results['saved']}개 저장:")
            for code in results["saved_codes"]:
                print(f"    - {code}")
        if results["duplicates"] > 0:
            print(f"  - 중복 코드 {results['duplicates']}개 스킵")
        
        return results
        
    except Exception as e:
        print(f"[오류] 스크래핑 실패: {e}")
        return {"saved": 0, "duplicates": 0, "errors": 1}


def scrape_all(max_pages: int = 1, max_articles: int = 20,
               skip_scraped: bool = True, game_filter: str = None):
    """
    모든 (또는 특정 게임) 사이트 스크래핑
    """
    manager = SiteManager()
    code_service = CodeService()
    
    # 사이트 목록 가져오기
    if game_filter:
        # 특정 게임 사이트 + 멀티 게임 사이트 (유튜브 등)
        sites = manager.get_sites_by_game(game_filter)
        # 멀티 게임 사이트도 추가 (해당 게임 태그가 있는 경우)
        multi_sites = [s for s in manager.get_enabled_sites() 
                       if s.is_multi_game and game_filter in s.game_tags.values()]
        sites.extend(multi_sites)
        
        if not sites:
            print(f"[오류] '{game_filter}' 게임이 등록되지 않았습니다.")
            print_available_games(manager)
            return
    else:
        sites = manager.get_enabled_sites()
    
    if not sites:
        print("[오류] 활성화된 사이트가 없습니다.")
        print("       sites.json 파일을 확인하세요.")
        return
    
    total_results = {
        "saved": 0,
        "duplicates": 0,
        "saved_codes": [],
        "duplicate_codes": []
    }
    
    total_sites = len(sites)
    print(f"\n{'#'*60}")
    print(f"# 스크래핑 시작: 총 {total_sites}개 사이트")
    print(f"{'#'*60}")
    
    for idx, site in enumerate(sites, 1):
        progress = f"[{idx}/{total_sites}]"
        results = scrape_site(
            site=site,
            max_pages=max_pages,
            max_articles=max_articles,
            skip_scraped=skip_scraped,
            progress=progress
        )
        
        total_results["saved"] += results.get("saved", 0)
        total_results["duplicates"] += results.get("duplicates", 0)
        total_results["saved_codes"].extend(results.get("saved_codes", []))
        total_results["duplicate_codes"].extend(results.get("duplicate_codes", []))
    
    # 최종 결과
    print(f"\n{'='*60}")
    print("[전체 결과]")
    print(f"{'='*60}")
    print(f"  - 새로 저장된 코드: {total_results['saved']}개")
    print(f"  - 중복 코드 (스킵): {total_results['duplicates']}개")
    
    # DB 통계
    stats = code_service.get_stats()
    print(f"\n[DB 통계]")
    print(f"  - 전체 코드: {stats['total_codes']}개")
    if stats['by_game']:
        print("  - 게임별:")
        for game, count in stats['by_game'].items():
            print(f"    - {game}: {count}개")


def print_available_games(manager: SiteManager):
    """사용 가능한 게임 목록 출력"""
    games = manager.get_all_games()
    if games:
        print("\n사용 가능한 게임:")
        for game, game_name in games:
            print(f"  - {game}: {game_name}")


def list_codes(game: str = None):
    """저장된 리딤코드 목록 출력"""
    service = CodeService()
    manager = SiteManager()
    
    if game:
        codes = service.get_codes_by_game(game)
        sites = manager.get_sites_by_game(game)
        game_name = sites[0].game_name if sites else game
        print(f"\n[{game_name}] 저장된 리딤코드 ({len(codes)}개)")
    else:
        codes = service.get_all_codes()
        print(f"\n[전체] 저장된 리딤코드 ({len(codes)}개)")
    
    print("="*60)
    
    if not codes:
        print("저장된 코드가 없습니다.")
        return
    
    current_game = None
    for code in codes:
        if code.game != current_game:
            current_game = code.game
            print(f"\n--- {current_game} ---")
        
        status = "[유효]" if code.is_valid else "[만료]"
        print(f"{status} {code.code}")
        if code.source_title:
            print(f"       출처: {code.source_title[:50]}...")


def list_sites():
    """등록된 사이트 목록 출력 (sites.json)"""
    manager = SiteManager()
    sites = manager.get_all_sites()
    
    print(f"\n[sites.json] 등록된 사이트 ({len(sites)}개)")
    print("="*60)
    
    if not sites:
        print("등록된 사이트가 없습니다.")
        print("sites.json 파일을 생성하세요.")
        return
    
    current_game = None
    for site in sites:
        if site.game != current_game:
            current_game = site.game
            print(f"\n[{site.game_name}] ({site.game})")
        
        status = "ON " if site.enabled else "OFF"
        type_label = f"[{site.site_type.upper()}]"
        print(f"  [{status}] {type_label} {site.site_name}")
        print(f"        {site.url[:55]}...")
    
    print(f"\n[설정 파일] sites.json을 직접 편집하여 사이트를 관리하세요.")


def show_stats():
    """통계 출력"""
    code_service = CodeService()
    article_service = ArticleService()
    manager = SiteManager()
    
    stats = code_service.get_stats()
    scraped_count = article_service.get_scraped_count()
    sites = manager.get_all_sites()
    enabled_sites = manager.get_enabled_sites()
    
    print(f"\n[통계]")
    print("="*60)
    print(f"  - 등록된 사이트: {len(sites)}개 (활성: {len(enabled_sites)}개)")
    print(f"  - 스크래핑한 게시글: {scraped_count}개")
    print(f"  - 수집된 리딤코드: {stats['total_codes']}개")
    print(f"    - 유효: {stats['valid_codes']}개")
    print(f"    - 만료: {stats['invalid_codes']}개")
    
    if stats['by_game']:
        print("\n  [게임별 코드 수]")
        for game, count in stats['by_game'].items():
            print(f"    - {game}: {count}개")


def main():
    """CLI 진입점"""
    print("[INFO] main.py 시작")
    sys.stdout.flush()
    parser = argparse.ArgumentParser(
        description="리딤코드 스크래퍼 - 원신/스타레일/젠존제 등",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py                      # 모든 게임 스크래핑
  python main.py --game genshin       # 원신만 스크래핑
  python main.py --pages 2            # 2페이지까지 스크래핑
  python main.py --force              # 이미 방문한 URL도 다시 처리
  python main.py --list               # 저장된 코드 목록
  python main.py --sites              # sites.json 사이트 목록
  python main.py --stats              # 통계 보기

사이트 관리:
  sites.json 파일을 직접 편집하여 사이트 추가/수정/삭제
  site_type: "arca" (아카라이브), "youtube" (유튜브 커뮤니티)
        """
    )
    
    parser.add_argument(
        '--game', '-g',
        type=str,
        default=None,
        help='특정 게임만 스크래핑 (예: genshin, starrail, zzz)'
    )
    
    parser.add_argument(
        '--pages', '-p',
        type=int,
        default=1,
        help='스크래핑할 페이지 수 (기본값: 1)'
    )
    
    parser.add_argument(
        '--articles', '-a',
        type=int,
        default=20,
        help='처리할 최대 게시글 수 (기본값: 20)'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='이미 스크래핑한 URL도 다시 처리'
    )
    
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='저장된 코드 목록 출력'
    )
    
    parser.add_argument(
        '--sites', '-s',
        action='store_true',
        help='sites.json 사이트 목록 출력'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='통계 보기'
    )
    
    parser.add_argument(
        '--scrape',
        action='store_true',
        help='스크래핑 실행 (웹 API용, 기본 동작과 동일)'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_codes(args.game)
    elif args.sites:
        list_sites()
    elif args.stats:
        show_stats()
    elif args.scrape or not any([args.list, args.sites, args.stats]):
        # --scrape 또는 다른 옵션이 없을 때 스크래핑 실행
        scrape_all(
            max_pages=args.pages,
            max_articles=args.articles,
            skip_scraped=not args.force,
            game_filter=args.game
        )


if __name__ == "__main__":
    main()
