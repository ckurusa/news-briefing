"""뉴스(RSS)와 시세(공개 API) 수집.

환율·지수·비트코인 수치는 AI가 아니라 API 값을 그대로 사용한다.
"""
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

from sections import SECTIONS

HEADERS = {"User-Agent": "Mozilla/5.0 (news-briefing personal tool)"}
TIMEOUT = 15

PER_QUERY = 6  # 키워드당 후보 기사 수

# (표시명, Yahoo 심볼, 소수점 자리, 단위)
MARKETS = [
    ("원/달러", "KRW=X", 1, "원"),
    ("코스피", "^KS11", 2, ""),
    ("코스닥", "^KQ11", 2, ""),
    ("S&P500", "^GSPC", 2, ""),
    ("나스닥", "^IXIC", 2, ""),
    ("비트코인", "BTC-USD", 0, "달러"),
]


def fetch_rss(query: str, limit: int = PER_QUERY) -> list[dict]:
    url = (
        "https://news.google.com/rss/search?q="
        + quote(f"{query} when:1d")
        + "&hl=ko&gl=KR&ceid=KR:ko"
    )
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "").strip()
        # 구글뉴스 제목은 "제목 - 언론사" 형식이라 뒤쪽 언론사명을 떼어낸다
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        if title and link:
            items.append({"title": title, "link": link, "source": source})
        if len(items) >= limit:
            break
    return items


def collect_news() -> dict[str, list[dict]]:
    """섹션별 후보 기사 목록(링크 기준 중복 제거)."""
    result: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for sec in SECTIONS:
        section, articles = sec.key, []
        for q in sec.queries:
            try:
                for a in fetch_rss(q):
                    if a["link"] not in seen:
                        seen.add(a["link"])
                        articles.append(a)
            except Exception as e:  # 한 키워드 실패가 전체를 막지 않게
                print(f"[경고] RSS 수집 실패 ({q}): {e}", file=sys.stderr)
        result[section] = articles
    return result


def _yahoo_quote(symbol: str) -> tuple[float, float] | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?interval=1d&range=10d"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    # 종가 목록의 마지막 값이 빠지는 경우가 있어, 현재가는 meta 값을 기준으로 삼는다
    cur = result["meta"]["regularMarketPrice"]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    if not closes:
        return None
    # 마지막 종가가 현재가와 같으면 그 전 종가가, 다르면 마지막 종가가 '전일 종가'
    prev = closes[-2] if abs(closes[-1] - cur) < 1e-6 * abs(cur) and len(closes) >= 2 else closes[-1]
    return cur, prev


def collect_market() -> list[str]:
    """시세 한 줄씩. 실패한 지표는 건너뛴다."""
    lines = []
    for name, symbol, digits, unit in MARKETS:
        try:
            q = _yahoo_quote(symbol)
        except Exception as e:
            print(f"[경고] 시세 수집 실패 ({name}): {e}", file=sys.stderr)
            q = None
        if q is None:
            if symbol == "KRW=X":  # 환율은 보조 API로 한 번 더 시도
                try:
                    r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=TIMEOUT)
                    r.raise_for_status()
                    lines.append(f"{name} {r.json()['rates']['KRW']:,.1f}원")
                except Exception as e:
                    print(f"[경고] 환율 보조 API 실패: {e}", file=sys.stderr)
            continue
        cur, prev = q
        diff = cur - prev
        pct = diff / prev * 100
        arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "-")
        lines.append(f"{name} {cur:,.{digits}f}{unit} ({arrow}{abs(pct):.2f}%)")
    return lines


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for sec, arts in collect_news().items():
        print(f"\n## {sec} ({len(arts)}건)")
        for a in arts[:5]:
            print(f"- {a['title']} ({a['source']})")
    print("\n## 시세")
    print("\n".join(collect_market()))
