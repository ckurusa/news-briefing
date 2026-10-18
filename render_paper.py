"""브리핑을 A4 1장짜리 신문 레이아웃(HTML, PDF)으로 만든다: "나믿따 신문"."""
import shutil
import subprocess
import sys
from datetime import date
from html import escape
from pathlib import Path

from sections import SECTIONS

WEEKDAYS = "월화수목금토일"

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: #e9e6df; }
body { font-family: 'Noto Serif KR', 'Batang', 'Malgun Gothic', serif; color: #1b1b1b; word-break: keep-all; }
.page { width: 210mm; height: 297mm; margin: 0 auto; padding: 8mm 11mm; background: #fbf9f3;
        display: flex; flex-direction: column; overflow: hidden; }
@media print { html, body { background: none; } .page { margin: 0; } }
a { color: inherit; text-decoration: none; }
.masthead { text-align: center; border-bottom: 3px double #1b1b1b; padding-bottom: 3mm; }
.masthead h1 { font-size: 36pt; letter-spacing: 5px; font-weight: 900; line-height: 1.1; }
.masthead .sub { font-family: 'Malgun Gothic', sans-serif; font-size: 8.5pt; color: #444; margin-top: 1.5mm;
                 display: flex; justify-content: space-between; border-top: 1px solid #1b1b1b; padding-top: 1.5mm; }
.ticker { display: grid; grid-template-columns: repeat(6, 1fr); font-family: 'Malgun Gothic', sans-serif;
          border-bottom: 1px solid #1b1b1b; margin-bottom: 3mm; }
.ticker div { padding: 1.2mm 1mm; text-align: center; border-right: 1px solid #bbb; font-size: 8pt; }
.ticker div:last-child { border-right: none; }
.ticker b { display: block; font-size: 8pt; color: #555; font-weight: 700; }
.ticker span { display: block; font-size: 10pt; font-weight: 700; }
.up { color: #c0392b; } .down { color: #1f5fa8; }
.grid { flex: 1; display: grid; grid-template-columns: 1fr 1fr 1fr; grid-auto-rows: auto;
        column-gap: 5mm; row-gap: 2.5mm; min-height: 0; align-content: start; }
.grid > .c2, .grid > .c3 { border-left: 1px solid #1b1b1b; padding-left: 5mm; }
.grid > .wide { grid-column: 2 / span 2; }
.grid > .wide .item { break-inside: avoid; }
.sec h2 { font-family: 'Malgun Gothic', sans-serif; font-size: 10pt; letter-spacing: 1px; color: #fff;
          background: #1b1b1b; padding: 1mm 2.5mm; margin-bottom: 1.5mm; display: inline-block; }
.headline { grid-column: 1 / span 2; padding-right: 2mm; }
.headline h3 { font-size: 22pt; line-height: 1.25; font-weight: 900; margin-bottom: 2.5mm; }
.headline p { font-size: 10.5pt; line-height: 1.55; }
.fun { grid-column: 3; }
.item { padding: 1.2mm 0; border-bottom: 1px solid #ccc; }
.item:last-child { border-bottom: none; }
.item h4 { font-size: 10pt; line-height: 1.35; font-weight: 800; margin-bottom: 0.8mm; }
.item p { font-size: 8.5pt; line-height: 1.42; color: #333; }
.item .src { font-family: 'Malgun Gothic', sans-serif; font-size: 7.5pt; color: #777; margin-top: 0.8mm; }
.item .src a.orig { color: #1f5fa8; font-weight: 700; margin-left: 1.5mm; }
.fun .item h4 { font-size: 10.5pt; }
.fun .item p { font-size: 8.5pt; }
.ideas { border: 2px solid #1b1b1b; padding: 2.5mm 3mm; background: #f3efe3; }
.ideas ul { list-style: none; }
.ideas li { font-size: 8pt; line-height: 1.4; color: #333; margin-bottom: 1.2mm; }
.ideas li b { display: block; font-size: 9pt; color: #1b1b1b; margin-bottom: 0.4mm; line-height: 1.35; }
.footer { font-family: 'Malgun Gothic', sans-serif; font-size: 7pt; color: #777; margin-top: 3mm;
          border-top: 1px solid #1b1b1b; padding-top: 1.5mm; display: flex; justify-content: space-between; }
/* 휴대폰 화면: A4 고정 폭 대신 세로로 쌓는다 (인쇄에는 적용되지 않음) */
@media screen and (max-width: 700px) {
  .page { width: 100%; height: auto; padding: 5mm 4mm; }
  .masthead h1 { font-size: 30pt; letter-spacing: 3px; }
  .masthead .sub { font-size: 7pt; flex-wrap: wrap; gap: 1mm; justify-content: center; }
  .ticker { grid-template-columns: repeat(3, 1fr); }
  .grid { display: block; }
  .grid > .c2, .grid > .c3 { border-left: none; padding-left: 0; }
  .headline { border-right: none; padding-right: 0; margin-bottom: 4mm; }
  .headline h3 { font-size: 19pt; }
  .item h4 { font-size: 11.5pt; } .item p { font-size: 10pt; }
  .sec { margin-bottom: 4mm; }
  .footer { flex-direction: column; gap: 1mm; }
}
"""


def _item(it: dict) -> str:
    summary = f"<p>{escape(it['summary'])}</p>" if it["summary"] else ""
    return (
        f'<div class="item"><h4><a href="{escape(it["link"])}">{escape(it["title"])}</a></h4>'
        f'{summary}<div class="src">{escape(it["source"])}'
        f'<a class="orig" href="{escape(it["link"])}">원문 보기 ›</a></div></div>'
    )


def _ticker(market: list[str]) -> str:
    cells = []
    for line in market:
        name, _, rest = line.partition(" ")
        value, _, change = rest.partition(" ")  # "6,625.93 (▼2.62%)" → 값 / 등락 두 줄
        cls = "up" if "▲" in rest else ("down" if "▼" in rest else "")
        cells.append(
            f'<div><b>{escape(name)}</b><span class="{cls}">{escape(value)}</span>'
            f'<span class="{cls}" style="font-size:8.5pt">{escape(change)}</span></div>'
        )
    return f'<div class="ticker">{"".join(cells)}</div>'


BASE_URL = "https://ckurusa.github.io/news-briefing/"
OG_HEIGHT = 388  # 794x388 → 제호·시세 띠·헤드라인·재미 단까지, 아래 섹션 제목이 걸리기 전에서 끊는다


def _og_tags(briefing: dict, today: date, image_name: str) -> str:
    """블로그·메신저에 주소를 붙였을 때 신문 미리보기 카드가 나오도록 하는 og 태그."""
    ai = briefing.get("ai_tech", [])
    desc = f"오늘의 헤드라인: {ai[0]['title']}" if ai else "AI · 경제 · 재미를 한 장에"
    title = f"나믿따 신문 {today:%Y년 %m월 %d일} ({WEEKDAYS[today.weekday()]})"
    img = BASE_URL + image_name
    tags = {
        "og:type": "website", "og:site_name": "나믿따 신문", "og:title": title, "og:description": desc,
        "og:url": BASE_URL, "og:image": img, "og:image:width": "1588", "og:image:height": str(OG_HEIGHT * 2),
        "twitter:card": "summary_large_image", "twitter:image": img,
    }
    return "\n".join(f'<meta property="{k}" content="{escape(v)}">' for k, v in tags.items())


def to_html(
    briefing: dict, market: list[str], today: date, include_ideas: bool = True, og_image: str | None = None
) -> str:
    ai = briefing["ai_tech"]
    head = ai[0] if ai else None
    head_html = ""
    if head:
        head_html = (
            f'<div class="sec headline"><h2>TOP · AI·테크</h2>'
            f'<h3><a href="{escape(head["link"])}">{escape(head["title"])}</a></h3>'
            f'<p>{escape(head["summary"])}</p><div class="item"><div class="src">{escape(head["source"])}'
            f'<a class="orig" href="{escape(head["link"])}">원문 보기 ›</a></div></div></div>'
        )
    ideas_li = "".join(
        f"<li><b>“{escape(i['title'])}”</b>{escape(i['angle'])}</li>" for i in briefing["ideas"]
    )
    # 헤드라인·재미 다음 칸들을 3열로 채운다: AI(나머지) 경제 산업 / 커리어 건강 소재
    cells = [("ai_tech", ai[1:])] + [(s.key, briefing.get(s.key, [])) for s in SECTIONS if s.key not in ("ai_tech", "fun")]
    labels = {s.key: s.label for s in SECTIONS}
    boxes = [(k, f'<h2>{labels[k]}</h2>' + "".join(_item(i) for i in items)) for k, items in cells if items]
    if include_ideas:
        boxes.append(("ideas", f'<h2>오늘의 소재</h2><ul>{ideas_li}</ul>'))
    grid_cells = []
    for n, (key, inner) in enumerate(boxes):
        cls = ["sec", ["", "c2", "c3"][n % 3]]
        if key == "ideas":
            cls.append("ideas")
        if not include_ideas and n == len(boxes) - 1 and n % 3 == 1:
            cls += ["wide"]  # 마지막 칸이 둘째 열에서 끝나면 오른쪽 빈칸까지 넓힌다
        grid_cells.append(f'<div class="{" ".join(c for c in cls if c)}">{inner}</div>')
    cells_html = "".join(grid_cells)
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>나믿따 신문 {today:%Y-%m-%d}</title>
{_og_tags(briefing, today, og_image) if og_image else ""}
<style>{CSS}</style></head><body><div class="page">
<div class="masthead"><h1>나믿따 신문</h1>
<div class="sub"><span>AI · 경제 · 재미를 한 장에</span><span>{today:%Y년 %m월 %d일} {WEEKDAYS[today.weekday()]}요일</span><span>나믿따 뉴스브리핑 편집</span></div></div>
{_ticker(market)}
<div class="grid">
{head_html}
<div class="sec fun c3"><h2>오늘의 재미</h2>{"".join(_item(i) for i in briefing.get("fun", []))}</div>
{cells_html}
</div>
<div class="footer"><span>※ 요약은 기사 제목을 바탕으로 AI가 작성했습니다. 소재로 쓰기 전 원문을 확인하세요.</span><span>시세: Yahoo Finance · 기사: Google News</span></div>
</div></body></html>
"""


def _find_browser() -> str | None:
    for name in ("msedge", "chrome"):
        if p := shutil.which(name):
            return p
    for p in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ):
        if Path(p).exists():
            return p
    return None


def capture_png(html_path: Path, png_path: Path, height: int = 1123, width: int = 794) -> bool:
    """HTML을 지정 크기로 캡처한다(고해상도 2배). 브라우저가 없으면 False."""
    browser = _find_browser()
    if not browser:
        return False
    subprocess.run(
        [browser, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
         f"--window-size={width},{height}", f"--screenshot={png_path}", html_path.resolve().as_uri()],
        check=True, capture_output=True, timeout=60,
    )
    return png_path.exists()


def _prune_old_previews(docs_dir: Path, today: date, keep_days: int = 14) -> None:
    for p in docs_dir.glob("paper-*.png"):
        try:
            d = date.fromisoformat(p.stem.removeprefix("paper-"))
        except ValueError:
            continue
        if (today - d).days > keep_days:
            p.unlink(missing_ok=True)


def make_paper(
    briefing: dict, market: list[str], today: date, out_dir: Path, docs_dir: Path | None = None
) -> tuple[Path, Path | None]:
    """개인용(소재 박스 포함) HTML·PDF를 out_dir에 저장한다. (html, pdf 또는 None) 반환.
    docs_dir를 주면 공개용(소재 박스 제외) HTML을 날짜별 파일과 index.html(최신본)로,
    미리보기 카드 이미지(paper-날짜.png)와 함께 저장한다."""
    out_dir.mkdir(exist_ok=True)
    html_path = out_dir / f"나믿따신문_{today:%Y-%m-%d}.html"
    html_path.write_text(to_html(briefing, market, today), encoding="utf-8")
    if docs_dir is not None:
        docs_dir.mkdir(exist_ok=True)
        image_name = f"paper-{today:%Y-%m-%d}.png"  # 날짜가 들어간 이름: 블로그·메신저의 이미지 캐시를 피한다
        public = to_html(briefing, market, today, include_ideas=False, og_image=image_name)
        (docs_dir / f"{today:%Y-%m-%d}.html").write_text(public, encoding="utf-8")
        (docs_dir / "index.html").write_text(public, encoding="utf-8")
        if not capture_png(docs_dir / "index.html", docs_dir / image_name, OG_HEIGHT):
            print("[경고] 신문 미리보기 이미지를 만들지 못했습니다(브라우저 없음).", file=sys.stderr)
        _prune_old_previews(docs_dir, today)
    browser = _find_browser()
    if not browser:
        return html_path, None
    pdf_path = html_path.with_suffix(".pdf")
    subprocess.run(
        [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
        check=True, capture_output=True, timeout=60,
    )
    return html_path, pdf_path
