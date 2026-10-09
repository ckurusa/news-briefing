"""나믿따 뉴스브리핑 전체 실행.

python main.py                # 수집 → 요약 → 카카오 전송 → 이력 저장
python main.py --publish      # 위 + 공개용 신문을 깃허브 페이지에 게시하고 카카오로 링크 전송
python main.py --no-send      # 전송·이력 저장 없이 콘솔 출력만 (테스트)
python main.py --collect-only # 수집 결과만 확인 (Claude API 호출 없음)
"""
import argparse
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

import history
from collect import collect_market, collect_news
from render import to_kakao_messages, to_markdown
from render_paper import make_paper

OUTPUT_DIR = Path(__file__).parent / "output"
DOCS_DIR = Path(__file__).parent / "docs"  # GitHub Pages 공개용 (소재 박스 제외)
PAGES_URL = "https://ckurusa.github.io/news-briefing/"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--no-send", action="store_true", help="카카오 전송과 이력 저장을 건너뜀")
    p.add_argument("--publish", action="store_true", help="공개용 신문을 깃허브 페이지에 게시하고 카카오에 링크 전송")
    p.add_argument("--collect-only", action="store_true", help="수집만 하고 종료")
    args = p.parse_args()
    today = date.today()

    print("1) 수집 중...")
    news = history.filter_duplicates(collect_news(), today)
    market = collect_market()
    for sec, arts in news.items():
        print(f"   {sec}: 후보 {len(arts)}건")
    print("   시세:", " / ".join(market) or "수집 실패")
    if args.collect_only:
        return 0
    if not any(news.values()):
        print("후보 기사가 없습니다. 네트워크/키워드를 확인하세요.", file=sys.stderr)
        return 1

    print("2) 요약·소재 제안 생성 중...")
    from summarize import summarize  # collect-only에서는 anthropic 불필요

    briefing = summarize(news, market)
    messages = to_kakao_messages(briefing, market, today)
    OUTPUT_DIR.mkdir(exist_ok=True)
    md_path = OUTPUT_DIR / f"briefing_{today:%Y-%m-%d}.md"
    md_path.write_text(to_markdown(briefing, market, today), encoding="utf-8")
    print(f"   전체본(링크 포함) 저장: {md_path}")
    paper_url = None
    try:
        _, pdf_path = make_paper(briefing, market, today, OUTPUT_DIR, DOCS_DIR if args.publish else None)
        print(f"   나믿따 신문(A4) 저장: {pdf_path or '(PDF 생성 불가, HTML만 저장)'}")
        if args.publish and not args.no_send:
            from publish import publish, wait_until_live

            publish(today)
            paper_url = PAGES_URL
            if not wait_until_live(PAGES_URL, today):
                print("[경고] 신문 페이지 반영 확인 시간 초과 (링크는 그대로 보냅니다)", file=sys.stderr)
    except Exception as e:  # 신문 생성·게시 실패가 카카오 전송을 막지 않게
        print(f"[경고] 신문 생성/게시 실패: {e}", file=sys.stderr)

    print(f"\n--- 카카오 메시지 {len(messages)}건 ---")
    for i, m in enumerate(messages, 1):
        print(f"[{i}] ({len(m)}자)\n{m}\n")

    if args.no_send:
        print("--no-send: 전송하지 않았습니다.")
        return 0

    print("3) 카카오톡 전송 중...")
    from send_kakao import send_all, send_text

    send_all(messages)
    if paper_url:
        # 카카오는 앱에 등록되지 않은 도메인의 링크 버튼을 열지 못할 수 있어, 본문에도 주소를 함께 넣는다
        send_text(f"📰 나믿따 신문 (A4 한 장)\n{paper_url}", url=paper_url)
    history.record(briefing, today)  # 전송 성공 후에만 이력 저장
    print("완료.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)
