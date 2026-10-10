"""발송 이력 저장과 최근 7일 중복 체크 (data/history.json)."""
import json
import re
from datetime import date, timedelta
from pathlib import Path

from sections import KEYS

HISTORY_PATH = Path(__file__).parent / "data" / "history.json"
SEND_LOG_PATH = Path(__file__).parent / "data" / "send_log.jsonl"
IDEAS_PATH =Path(__file__).parent / "data" / "ideas.json"
KEEP_DAYS = 7


def _norm(title: str) -> str:
    return re.sub(r"[\W_]+", "", title).lower()


def load() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def _recent(today: date) -> list[dict]:
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    return [h for h in load() if h["date"] >= cutoff]


def filter_duplicates(news: dict[str, list[dict]], today: date) -> dict[str, list[dict]]:
    """최근 7일에 보낸 기사(링크 또는 정규화한 제목이 같은 것)를 후보에서 뺀다."""
    recent = _recent(today)
    links = {l for h in recent for l in h["links"]}
    titles = {_norm(t) for h in recent for t in h["titles"]}
    return {
        sec: [a for a in arts if a["link"] not in links and _norm(a["title"]) not in titles]
        for sec, arts in news.items()
    }


def log_send(status: str, sent: int, total: int, paper: bool, articles: int = 0, error: str = "") -> None:
    """발송 기록을 data/send_log.jsonl에 한 줄씩 누적한다 (같은 날 재전송도 각각 남는다)."""
    from datetime import datetime

    row = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "status": status,  # success | failed
        "messages_sent": sent,
        "messages_total": total,
        "paper_link_sent": paper,
        "articles": articles,
        "error": error[:300],
    }
    SEND_LOG_PATH.parent.mkdir(exist_ok=True)
    with SEND_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def recent_titles(today: date) -> list[str]:
    """최근 7일에 보낸 기사 제목(같은 사건을 다른 언론사 기사로 또 보내지 않도록 AI에 알려 준다)."""
    return [t for h in _recent(today) for t in h["titles"]]


def record(briefing: dict, today: date) -> None:
    items = [it for sec in KEYS for it in briefing.get(sec, [])]
    entry = {
        "date": today.isoformat(),
        "links": [it["link"] for it in items],
        # 요약용 제목과 원문 제목을 둘 다 남긴다
        "titles": [t for it in items for t in {it["title"], it.get("orig_title", it["title"])}],
        "ideas": [i["title"] for i in briefing["ideas"]],  # 소재 누적
    }
    history = [h for h in _recent(today) if h["date"] != entry["date"]] + [entry]
    HISTORY_PATH.parent.mkdir(exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    # 소재 제안은 7일 보관과 별개로 계속 누적 (2단계 검증 때 활용)
    ideas = json.loads(IDEAS_PATH.read_text(encoding="utf-8")) if IDEAS_PATH.exists() else []
    ideas = [x for x in ideas if x["date"] != entry["date"]]
    ideas += [{"date": entry["date"], **i} for i in briefing["ideas"]]
    IDEAS_PATH.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")
