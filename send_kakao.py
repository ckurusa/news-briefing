"""카카오톡 "나에게 보내기" 전송과 토큰 관리.

최초 1회:  python send_kakao.py auth   (브라우저 인증 → 토큰을 data/kakao_token.json에 저장)
이후에는 access token 만료 시 refresh token으로 자동 갱신한다.
키·토큰은 .env / data/kakao_token.json에만 보관한다 (둘 다 Git 제외).
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests

TOKEN_PATH = Path(__file__).parent / "data" / "kakao_token.json"
AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TIMEOUT = 15


def _env(name: str, required: bool = True) -> str:
    v = os.getenv(name, "")
    if required and not v:
        raise RuntimeError(f".env에 {name}이(가) 없습니다.")
    return v


def _token_request(data: dict) -> dict:
    data = {**data, "client_id": _env("KAKAO_REST_API_KEY")}
    secret = _env("KAKAO_CLIENT_SECRET", required=False)
    if secret:
        data["client_secret"] = secret
    resp = requests.post(TOKEN_URL, data=data, timeout=TIMEOUT)
    if resp.status_code != 200:
        # 응답에는 토큰이 없으므로 에러 내용만 출력
        raise RuntimeError(f"카카오 토큰 요청 실패 {resp.status_code}: {resp.text}")
    return resp.json()


def _save_token(resp: dict, old: dict | None = None) -> dict:
    now = time.time()
    old = old or {}
    token = {
        "access_token": resp["access_token"],
        "access_expires_at": now + int(resp["expires_in"]),
        # 갱신 응답에는 refresh_token이 만료 임박일 때만 새로 내려온다
        "refresh_token": resp.get("refresh_token", old.get("refresh_token")),
        "refresh_expires_at": (
            now + int(resp["refresh_token_expires_in"])
            if "refresh_token_expires_in" in resp
            else old.get("refresh_expires_at", 0)
        ),
    }
    TOKEN_PATH.parent.mkdir(exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding="utf-8")
    return token


def _refresh(token: dict) -> dict:
    return _save_token(
        _token_request({"grant_type": "refresh_token", "refresh_token": token["refresh_token"]}),
        token,
    )


def _get_access_token(force_refresh: bool = False) -> str:
    if not TOKEN_PATH.exists():
        raise RuntimeError("토큰이 없습니다. 먼저 `python send_kakao.py auth`를 실행하세요.")
    token = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    if force_refresh or token["access_expires_at"] - time.time() < 600:
        if token["refresh_expires_at"] and token["refresh_expires_at"] < time.time():
            raise RuntimeError("refresh token이 만료됐습니다. `python send_kakao.py auth`로 재인증하세요.")
        token = _refresh(token)
    return token["access_token"]


def send_text(text: str, url: str = "https://news.google.com") -> None:
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": url, "mobile_web_url": url},
    }
    for attempt in (0, 1):
        access = _get_access_token(force_refresh=attempt == 1)
        resp = requests.post(
            SEND_URL,
            headers={"Authorization": f"Bearer {access}"},
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=TIMEOUT,
        )
        if resp.status_code == 401 and attempt == 0:  # 토큰 만료 → 갱신 후 1회 재시도
            continue
        if resp.status_code != 200 or resp.json().get("result_code") != 0:
            raise RuntimeError(f"카카오 전송 실패 {resp.status_code}: {resp.text}")
        return


def send_all(messages: list[str], delay: float = 0.5) -> None:
    for i, m in enumerate(messages, 1):
        send_text(m)
        print(f"  전송 {i}/{len(messages)}")
        time.sleep(delay)


CODE_PATH = Path(__file__).parent / "data" / "kakao_code.txt"


def _auth_url() -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": _env("KAKAO_REST_API_KEY"),
        "redirect_uri": _env("KAKAO_REDIRECT_URI"),
        "response_type": "code",
        "scope": "talk_message",
    })


def _exchange(raw: str) -> None:
    code = parse_qs(urlparse(raw).query).get("code", [raw])[0]
    _save_token(_token_request({
        "grant_type": "authorization_code",
        "redirect_uri": _env("KAKAO_REDIRECT_URI"),
        "code": code,
    }))
    print(f"토큰 저장 완료: {TOKEN_PATH}")


def auth_open() -> None:
    """1단계: 인증 주소를 브라우저로 연다. 로그인·동의 후 이동된 주소창의 전체 URL을
    data/kakao_code.txt에 저장한다 (채팅창이 아니라 파일로 전달)."""
    import webbrowser

    CODE_PATH.parent.mkdir(exist_ok=True)
    CODE_PATH.write_text("", encoding="utf-8")
    webbrowser.open(_auth_url())
    print(f"브라우저를 열었습니다. 로그인·동의 후 주소창 전체를 {CODE_PATH}에 붙여넣어 저장하세요.")


def auth_file() -> None:
    """2단계: kakao_code.txt의 코드로 토큰을 발급하고, 코드 파일은 삭제한다."""
    raw = CODE_PATH.read_text(encoding="utf-8").strip() if CODE_PATH.exists() else ""
    if not raw:
        raise RuntimeError(f"{CODE_PATH}가 비어 있습니다. 1단계(auth-open)를 먼저 하세요.")
    try:
        _exchange(raw)
    finally:
        CODE_PATH.unlink(missing_ok=True)  # 인증 코드는 1회용이므로 남기지 않는다


def auth() -> None:
    print("1) 아래 주소를 브라우저에서 열어 로그인·동의하세요.\n")
    print(_auth_url())
    print("\n2) 이동된 주소창의 전체 URL(또는 code 값)을 아래에 붙여넣으세요.")
    print("   (이 코드는 이 터미널에만 입력하고, 채팅창에는 붙여넣지 마세요)")
    _exchange(input("> ").strip())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    from dotenv import load_dotenv

    load_dotenv()
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        auth()
    elif len(sys.argv) > 1 and sys.argv[1] == "auth-open":
        auth_open()
    elif len(sys.argv) > 1 and sys.argv[1] == "auth-file":
        auth_file()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        send_text("[나믿따 뉴스브리핑] 테스트 메시지입니다.")
        print("테스트 전송 완료")
    else:
        print("사용법: python send_kakao.py auth | test")
