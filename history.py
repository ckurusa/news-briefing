"""발송 이력 저장과 최근 7일 중복 체크 (data/history.json)."""
import json
import re
from datetime import date, timedelta
from pathlib import Path

HISTORY_PATH = Path(__file__).parent / "data" / "history.json"
IDEAS_PATH = Path(__file__).parent / "data" / "ideas.json"
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


def record(briefing: dict, today: date) -> None:
    items = [it for sec in ("ai_tech", "economy", "fun") for it in briefing[sec]]
    entry = {
        "date": today.isoformat(),
        "links": [it["link"] for it in items],
        "titles": [it["title"] for it in items],
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
