"""Claude API로 섹션별 기사 선별·요약과 소재 제안을 생성한다."""
import os
from pathlib import Path

import anthropic

from sections import KEYS, SECTIONS

PROMPT_PATH = Path(__file__).parent / "prompts" / "briefing.md"
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_CANDIDATES = 15  # 섹션당 AI에 넘기는 후보 수 (토큰 절약)


def _build_user_message(
    news: dict[str, list[dict]], market: list[str], recent: list[str]
) -> tuple[str, dict[str, dict]]:
    index: dict[str, dict] = {}
    parts = ["## 오늘의 시세 (API 값)", "\n".join(market) or "(수집 실패)"]
    if recent:
        parts += ["\n## 최근 7일 이미 보낸 기사 (같은 사건·주제는 다른 언론사 기사라도 고르지 말 것)"]
        parts += [f"- {t}" for t in recent[:80]]
    for sec in SECTIONS:
        articles = news.get(sec.key, [])
        parts.append(f"\n## 후보 기사: {sec.key} ({sec.label}, {sec.limit}건 선택)")
        for i, a in enumerate(articles[:MAX_CANDIDATES], 1):
            aid = f"{sec.prefix}{i}"
            index[aid] = a
            parts.append(f"[{aid}] {a['title']} ({a['source']})")
    return "\n".join(parts), index


_ARTICLE = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": ["id", "title", "summary"],
    },
}
# 텍스트 JSON은 따옴표 등으로 깨질 수 있어, 도구 호출(스키마 강제)로 구조화된 결과를 받는다
BRIEFING_TOOL = {
    "name": "submit_briefing",
    "description": "완성된 뉴스 브리핑을 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            **{k: _ARTICLE for k in KEYS},
            "ideas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "angle": {"type": "string"}},
                    "required": ["title", "angle"],
                },
            },
        },
        "required": [*KEYS, "ideas"],
    },
}


def summarize(news: dict[str, list[dict]], market: list[str], recent: list[str] | None = None) -> dict:
    """반환: {섹션 key: [기사...], ..., "ideas": [...]}  (섹션은 sections.py 참고)
    기사 항목에는 title, summary, source, link(코드가 원본에서 붙임)가 들어간다."""
    user_msg, index = _build_user_message(news, market, recent or [])
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    resp = client.messages.create(
        model=MODEL,
        max_tokens=16000,  # 모델의 사고 과정이 토큰을 쓰므로 여유 있게
        system=PROMPT_PATH.read_text(encoding="utf-8"),
        messages=[{"role": "user", "content": user_msg + "\n\n위 후보로 브리핑을 만들어 submit_briefing 도구를 호출하세요."}],
        tools=[BRIEFING_TOOL],
    )
    # 이 모델은 tool_choice 강제를 지원하지 않아, 프롬프트로 도구 호출을 유도하고 결과를 확인한다
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Claude 응답이 max_tokens에서 잘렸습니다. summarize.py의 max_tokens를 늘리세요.")
    data = next((b.input for b in resp.content if b.type == "tool_use"), None)
    if data is None:
        raise RuntimeError("Claude가 submit_briefing 도구를 호출하지 않았습니다. 다시 실행해 보세요.")

    briefing: dict = {}
    for sec in SECTIONS:
        section, limit = sec.key, sec.limit
        items = []
        for it in data.get(section, []):
            src = index.get(it.get("id"))
            if not src:  # 존재하지 않는 ID(환각)는 버린다
                continue
            items.append({
                "title": it.get("title") or src["title"],
                "orig_title": src["title"],
                "summary": it.get("summary", ""),
                "source": src["source"],
                "link": src["link"],
            })
        briefing[section] = items[:limit]
    briefing["ideas"] = data.get("ideas", [])[:3]
    return briefing
