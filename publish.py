"""docs/ 의 공개용 신문을 깃허브(ckurusa/news-briefing)에 커밋·푸시한다 (GitHub Pages로 공개됨).

main.py --publish 로만 실행된다. 원격 주소가 예상과 다르면 아무것도 올리지 않는다.
"""
import os
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
EXPECTED_REMOTE = "https://github.com/ckurusa/news-briefing.git"


def _ckurusa_env() -> dict:
    """gh의 활성 계정이 회사 계정(che-kwan)으로 바뀌어 있어도 ckurusa 토큰으로 푸시하도록 지정."""
    r = subprocess.run(["gh", "auth", "token", "--user", "ckurusa"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError("gh에 ckurusa 계정 로그인이 없습니다 (gh auth login).")
    return {**os.environ, "GH_TOKEN": r.stdout.strip()}


def _git(*args: str, env: dict | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {r.stderr.strip()}")
    return r.stdout.strip()


def wait_until_live(url: str, today: date, timeout: int = 240) -> bool:
    """깃허브 페이지에 오늘자 신문이 반영될 때까지 기다린다 (보통 1~2분)."""
    import time

    import requests

    marker = f"{today:%Y년 %m월 %d일}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, params={"t": int(time.time())}, timeout=15)
            if r.status_code == 200 and marker in r.text:
                return True
        except requests.RequestException:
            pass
        time.sleep(10)
    return False


def publish(today: date) -> None:
    remote = _git("remote", "get-url", "origin")
    if remote.rstrip("/") not in (EXPECTED_REMOTE, EXPECTED_REMOTE.removesuffix(".git")):
        raise RuntimeError(f"원격 저장소가 예상과 다릅니다({remote}). 게시를 중단합니다.")
    _git("add", "docs")
    if not _git("status", "--porcelain", "docs"):
        print("   게시할 변경 없음")
        return
    _git("commit", "-m", f"나믿따 신문 {today:%Y-%m-%d}")
    _git("push", "origin", "HEAD", env=_ckurusa_env())
    print("   깃허브에 게시 완료")
