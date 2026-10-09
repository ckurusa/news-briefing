"""브리핑을 카카오톡용 짧은 메시지 목록과 전체 md 문서로 변환한다."""
from datetime import date

KAKAO_LIMIT = 200  # 기본 텍스트 템플릿 글자 수 제한 (공식 문서로 재확인 필요)
WEEKDAYS = "월화수목금토일"


def _header(today: date) -> str:
    return f"[나믿따 뉴스브리핑] {today:%m/%d}({WEEKDAYS[today.weekday()]})"


def _article_lines(items: list[dict]) -> list[str]:
    """기사 1건 = 1항목(제목+요약). 메시지가 나뉠 때 항목 중간에서 끊기지 않게 한다."""
    lines = []
    for i, it in enumerate(items, 1):
        line = f"{i}. {it['title']}"
        if it["summary"]:
            line += f"\n  - {it['summary']}"
        lines.append(line)
    return lines


def _pack(lines: list[str], limit: int = KAKAO_LIMIT) -> list[str]:
    """줄 단위로 limit 이하가 되게 묶는다. 한 줄이 limit을 넘으면 잘라낸다."""
    messages, cur = [], ""
    for line in lines:
        if len(line) > limit:
            line = line[: limit - 1] + "…"
        if cur and len(cur) + 1 + len(line) > limit:
            messages.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        messages.append(cur)
    return messages


def to_kakao_messages(briefing: dict, market: list[str], today: date) -> list[str]:
    """A안: 섹션별로 나눠 여러 번 전송."""
    sections = [
        ("■ AI·테크", _article_lines(briefing["ai_tech"])),
        ("■ 경제·시장", market + _article_lines(briefing["economy"])),
        ("■ 오늘의 재미", _article_lines(briefing["fun"])),
        ("■ 오늘의 소재", [f"- \"{i['title']}\"\n  {i['angle']}" for i in briefing["ideas"]]),
    ]
    messages = []
    for n, (title, lines) in enumerate(sections):
        if not lines:
            continue
        head = [_header(today), title] if n == 0 else [title]
        packed = _pack(head + lines)
        messages.extend(packed)
    return messages


def to_markdown(briefing: dict, market: list[str], today: date) -> str:
    """링크 포함 전체 문서 (저장용)."""
    out = [f"# {_header(today)}", ""]

    def articles(title: str, items: list[dict]):
        out.append(f"## {title}")
        for i, it in enumerate(items, 1):
            out.append(f"{i}. [{it['title']}]({it['link']}) ({it['source']})")
            if it["summary"]:
                out.append(f"   - {it['summary']}")
        out.append("")

    articles("AI·테크", briefing["ai_tech"])
    out.append("## 경제·시장")
    out += [f"- {m}" for m in market]
    out.append("")
    for i, it in enumerate(briefing["economy"], 1):
        out.append(f"{i}. [{it['title']}]({it['link']}) ({it['source']})")
        if it["summary"]:
            out.append(f"   - {it['summary']}")
    out.append("")
    articles("오늘의 재미", briefing["fun"])
    out.append("## 오늘의 소재")
    for i in briefing["ideas"]:
        out.append(f"- \"{i['title']}\" — {i['angle']}")
    return "\n".join(out) + "\n"
