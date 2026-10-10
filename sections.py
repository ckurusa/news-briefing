"""브리핑 섹션 정의 (한 곳에서 관리). 주제를 추가·삭제하려면 여기만 고친다.

key       : 데이터 키
label     : 화면에 보이는 이름
prefix    : AI에 넘기는 후보 기사 ID 접두어 (섹션마다 달라야 함)
limit     : 브리핑에 실을 기사 수
queries   : 구글뉴스 검색 키워드 (최근 1일)
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    key: str
    label: str
    prefix: str
    limit: int
    queries: tuple[str, ...]


SECTIONS = [
    Section("ai_tech", "AI·테크", "A", 3,
            ("AI 신기능 출시", "생성형 AI 업데이트", "Claude OR ChatGPT OR Gemini", "AI 도구 업무 활용")),
    Section("economy", "경제·시장", "E", 3,
            ("원달러 환율", "기준금리", "코스피 마감", "비트코인 시세")),
    Section("industry", "산업·무역", "I", 2,
            ("철강 가격", "원자재 가격 동향", "해상 운임 물류", "관세 수출 무역")),
    Section("career", "직장인·커리어", "C", 2,
            ("직장인 자기계발", "업무 생산성", "이직 커리어", "직장인 번아웃")),
    Section("health", "건강·생활", "H", 2,
            ("영양제 건강", "수면 건강", "중년 건강 습관", "생활 건강 정보")),
    Section("fun", "오늘의 재미", "F", 2,
            ("이색", "화제", "알고보니", "직장인", "신기한 과학", "반전")),
]
KEYS = [s.key for s in SECTIONS]
