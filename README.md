# 나믿따 뉴스브리핑

AI·테크, 경제·시장, 재미 기사를 요약해 카카오톡("나에게 보내기")으로 보내고 블로그·유튜브 소재까지 제안하는 개인용 도구. 기획안: `나믿따_뉴스브리핑_기획안.md`

## 설치

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env     # 값 채우기
```

## 실행 (기획안 6장 개발 순서대로)

| 단계 | 명령 | 설명 |
|---|---|---|
| 1 | `python main.py --collect-only` | 수집만 확인 (API 키 불필요) |
| 2 | `python main.py --no-send` | Claude 요약 + 소재 제안을 콘솔 출력 |
| 3 | `python send_kakao.py auth` → `python send_kakao.py test` | 카카오 최초 인증, 테스트 전송 |
| 3 | `python main.py` | 실제 전송 (A안: 섹션별 분할) |

| 4 | `python main.py --publish` | 위 + A4 신문을 깃허브 페이지(`docs/`)에 게시하고 카카오로 링크 전송 |

## 나믿따 신문 (A4 한 장)
- `output/나믿따신문_날짜.html·pdf`: 개인용 (오늘의 소재 박스 포함, PC에만 저장)
- `docs/`: 공개용 (소재 박스 제외). GitHub Pages로 https://ckurusa.github.io/news-briefing/ 에 게시된다. 주소를 아는 누구나 볼 수 있으므로 개인 정보나 키를 넣지 않는다.
- 게시는 `--publish`를 줄 때만 한다. 푸시는 `gh`의 ckurusa 토큰을 명시해 사용한다.
- 카카오 링크 버튼은 앱에 등록한 도메인만 열릴 수 있어, 본문에도 주소를 함께 보낸다.

## 자동 실행 (평일 08:00)
Windows 작업 스케줄러 "나믿따 뉴스브리핑"이 `run_daily.bat`을 실행한다(전송 → 게시 → 신문 페이지 열기). 로그는 `data/run.log`. PC가 켜져 있고 로그인 상태여야 한다. 해제: `Unregister-ScheduledTask -TaskName "나믿따 뉴스브리핑"`.

실행하면 링크 포함 전체본이 `output/briefing_YYYY-MM-DD.md`에 저장되고, 전송 성공 시 `data/history.json`(7일 중복 체크)과 `data/ideas.json`(소재 누적)에 기록된다.

## 설계 메모
- 환율·지수·비트코인 수치는 Yahoo Finance 공개 차트 API 값을 그대로 쓰고(비공식 API라 변경 가능, 환율은 open.er-api.com 보조), AI는 수치를 만들지 않는다.
- 기사는 Claude가 후보 ID로만 선택하고, 링크·언론사는 코드가 원본에서 붙인다 (URL 환각 방지). 원문 복사 없이 한 줄 요약 + 링크.
- 카카오 텍스트는 약 200자 제한이라 섹션별로 나눠 보내며 링크는 md 전체본에만 있다. (B안 전환은 안정화 후)
- 금리는 별도 API 없이 경제 뉴스 기사로 다룬다.
- 요약 규칙은 `prompts/briefing.md`만 고치면 된다. 수집 키워드는 `collect.py` 상단 `QUERIES`.

## 확인 필요
- 카카오 글자 수 제한·토큰 유효기간은 공식 문서로 재확인 (기획안에도 명시된 항목)
- 카카오 앱: 로그인 활성화, `talk_message` 동의항목, 리다이렉트 URI 등록
- 자동 실행(5단계)은 1주일 검증 후 추가 (발송 시간·실행 위치 미정)
