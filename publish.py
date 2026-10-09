"""docs/ 의 공개용 신문을 깃허브(ckurusa/news-briefing)에 커밋·푸시한다 (GitHub Pages로 공개됨).

main.py --publish 로만 실행된다. 원격 주소가 예상과 다르면 아무것도 올리지 않는다.
"""
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
EXPECTED_REMOTE = "https://github.com/ckurusa/news-briefing.git"


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {r.stderr.strip()}")
    return r.stdout.strip()


def publish(today: date) -> None:
    remote = _git("remote", "get-url", "origin")
    if remote.rstrip("/") not in (EXPECTED_REMOTE, EXPECTED_REMOTE.removesuffix(".git")):
        raise RuntimeError(f"원격 저장소가 예상과 다릅니다({remote}). 게시를 중단합니다.")
    _git("add", "docs")
    if not _git("status", "--porcelain", "docs"):
        print("   게시할 변경 없음")
        return
    _git("commit", "-m", f"나믿따 신문 {today:%Y-%m-%d}")
    _git("push", "origin", "HEAD")
    print("   깃허브에 게시 완료")
