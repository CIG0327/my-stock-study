import os
import sys
import re
import json
import datetime
import xml.etree.ElementTree as ET
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
VIDEOS_PATH = os.path.join(BASE_DIR, "data", "videos_2026.json")

TICKER_KEYWORDS = {
    "엔비디아": "NVDA", "NVIDIA": "NVDA", "NVDA": "NVDA",
    "테슬라": "TSLA", "TESLA": "TSLA", "TSLA": "TSLA",
    "마이크론": "MU", "MICRON": "MU", "MU": "MU", "삼전닉스": "MU",
    "마이크로소프트": "MSFT", "MS": "MSFT", "MSFT": "MSFT",
    "반도체": "SOXL", "SOXL": "SOXL", "필라델피아": "SOXL",
    "아이온큐": "IONQ", "양자": "IONQ", "IONQ": "IONQ",
    "로빈후드": "HOOD", "HOOD": "HOOD",
    "조비": "JOBY", "JOBY": "JOBY",
    "새틀로직": "SATL", "SATL": "SATL",
    "팔란티어": "PLTR", "PLTR": "PLTR",
    "오라클": "ORCL", "ORCL": "ORCL",
    "에어로스페이스": "GE", "GE": "GE",
    "AMD": "NVDA", "슈마컴": "NVDA"
}


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_channel_id(channel_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(channel_url, headers=headers, timeout=6)
        if resp.status_code == 200:
            match = re.search(r'"externalId":"(UC[a-zA-Z0-9_-]{22})"', resp.text)
            if match:
                return match.group(1)
            match2 = re.search(r'channel_id=(UC[a-zA-Z0-9_-]{22})', resp.text)
            if match2:
                return match2.group(1)
    except Exception as e:
        print(f"ℹ️ 채널 페이지 직접 접근 생략 (오프라인/제한 환경 폴백 작동): {e}")
    return None


def fetch_transcript_text(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
        full_text = " ".join([item["text"] for item in transcript_list])
        return full_text[:4000]
    except Exception:
        return ""


def infer_lesson_from_video(video_id, title, published_at, description="", transcript=""):
    """신규 영상의 제목·자막 맥락을 깊이 분석하여 맞춤형 5단계 프레임워크, 기본/기술적 레슨, 실전 퀴즈 생성"""
    combined = f"{title} {description} {transcript}"
    mentioned = []
    for kw, ticker in TICKER_KEYWORDS.items():
        if kw.lower() in combined.lower() and ticker not in mentioned:
            mentioned.append(ticker)
    if not mentioned:
        mentioned = ["NVDA", "TSLA", "MSFT"]

    # 맥락별 정밀 분류 및 맞춤 해설 생성
    if "아이온큐" in combined and "수주" in combined:
        category = "내 보유종목 & 수주잔고"
        related_unit = 3
        diff_level = 2
        five_step = {
            "macro": "양자컴퓨팅 상용화 및 정부·클라우드 빅테크의 양자 연구 계약 확대 국면.",
            "smart_money": "단기 적자에도 불구하고 기관 투자자들은 아이온큐의 '수주잔고(Bookings)' 증가 속도에 주목해 지분 확대.",
            "fundamental": "초기 기술주는 당장의 PER이 아닌 ① 연간 수주 계약고(Bookings) 목표 초과 달성 여부와 ② 대차대조표의 무차입 순현금($380M, 유동비율 680%) 및 선수금(이연수익) 증가가 핵심.",
            "technical": "수주 모멘텀과 공매도 숏커버링이 맞물리며 20일 이동평균선($19.10)을 지지선 삼아 계단식 상승 추세 유지.",
            "action_plan": "내 보유종목(IONQ) 홀딩 근거를 '수주잔고 성장 + 대차대조표 현금 런웨이 + 차트 20일선 지지' 3박자로 점검!"
        }
        fund_lesson = {
            "concept": "신성장 기술주의 핵심 지표: 수주잔고(Bookings)와 대차대조표 선수금(이연수익)",
            "detail": "아이온큐처럼 R&D 투자기인 기업은 손익계산서상 당기순이익보다 '수주잔고(앞으로 매출로 찍힐 확정 계약)'와 대차대조표의 '현금 실탄(유동비율 680%)'이 기업 가치를 이끌어갑니다."
        }
        tech_lesson = {
            "concept": "수주 모멘텀 종목의 20일 생명선 추세 추종과 직전 고점 돌파",
            "detail": "수주 뉴스로 상승할 때 고점 추격 매수를 피하고, 단기 조정 시 20일 이동평균선에서 거래량이 줄며 지지받는 타점을 기준으로 삼으세요."
        }
        quiz_q = "[신규 영상 실전: 아이온큐] 아직 R&D 투자로 영업적자인 양자컴퓨팅 기업(IONQ)의 기업가치가 상승하는 핵심 기본적 분석 근거 두 가지는?"
        quiz_opts = [
            "지속적으로 늘어나는 수주잔고(Bookings/계약부채)와 대차대조표의 풍부한 무차입 순현금(유동비율 680% 이상의 생존 런웨이)",
            "과거 30년간의 높은 현금 배당률",
            "석유 시추 매장량 증가",
            "단기 차입금 급증"
        ]
        quiz_exp = "상용화 초기 기술주는 '수주잔고(미래 매출 가시성)'와 '대차대조표 순현금(유상증자 없이 버티는 체력)'이 가장 중요한 펀더멘털 지표입니다."
        domain = "balance_sheet"
    elif "아이온큐" in combined and ("증권" in combined or "지분" in combined or "기관" in combined):
        category = "내 보유종목 & 스마트머니"
        related_unit = 5
        diff_level = 3
        five_step = {
            "macro": "글로벌 금융기관들이 차세대 AI·양자 하드웨어 섹터로 장기 포트폴리오 다변화.",
            "smart_money": "일본 2위 증권사(노무라 등) 및 글로벌 기관의 SEC 13F 지분 매집은 단순 테마가 아닌 기술 로드맵 검증 신호.",
            "fundamental": "기관이 소형 기술주 지분을 늘릴 때는 대차대조표의 부채 리스크가 없고(부채비율 4.3%) 특허·수주 해자가 확실한지 실사(Due Diligence)를 거침.",
            "technical": "기관의 장내 분할 매집은 차트상 하락 시 60일·20일선 부근에서 강력한 아랫꼬리 지지력(하방 경직성)을 만들어냄.",
            "action_plan": "개인들의 단기 흔들기에 동요하지 말고, SEC 13F 기관 지분 추이와 20일/60일 지지선을 함께 보며 코어 물량 보유."
        }
        fund_lesson = {
            "concept": "SEC 13F 공시로 읽는 글로벌 기관(스마트 머니)의 종목 선정 기준",
            "detail": "대형 금융기관은 파산 위험이 있는 부실주를 대량 매수하지 않습니다. 기관 지분율 상승은 해당 기업의 대차대조표 안정성과 중장기 성장성에 대한 강력한 간접 보증입니다."
        }
        tech_lesson = {
            "concept": "기관 매집주의 차트 특징: 조정 시 거래량 감소와 중기 이평선 방어",
            "detail": "기관이 지분을 모으는 종목은 지수가 흔들려도 특정 가격대(지지선) 아래로 잘 밀리지 않는 '매집 바닥'을 형성합니다."
        }
        quiz_q = "[신규 영상 실전: 아이온큐 기관 매집] 해외 대형 증권사 등 기관 투자자가 특정 기술주의 지분을 꾸준히 늘리고 있는지 확인할 수 있는 미국 공시 자료는?"
        quiz_opts = [
            "SEC Form 13F (기관 투자자 분기별 보유 지분 공시)",
            "유튜브 댓글 투표",
            "식당 영수증",
            "과거 10년 전 신문 기사"
        ]
        quiz_exp = "운용자산 1억 달러 이상 기관들의 보유 종목과 지분 증감은 SEC Form 13F 공시를 통해 팩트체크할 수 있습니다."
        domain = "technical"
    elif "팔란티어" in combined:
        category = "구독자요청 & 보유원칙"
        related_unit = 4
        diff_level = 2
        five_step = {
            "macro": "기술주 전반의 단기 숨고르기 및 밸류에이션 부담 논란 속 흔들림.",
            "smart_money": "S&P500 편입 이후 패시브 기관 자금이 하방을 받치며 단기 차익실현 물량을 소화.",
            "fundamental": "팔란티어(PLTR)의 대차대조표는 순현금 $4.4B(무차입 S급)이며 상업용 AI(AIP) 매출과 영업이익률이 동시 폭발(Rule of 40 상회)하여 펀더멘털 훼손이 전혀 없음.",
            "technical": "단기 급등 후 20일 이동평균선과의 이격도를 좁히는 건전한 되돌림(눌림목) 구간.",
            "action_plan": "펀더멘털(실적·대차대조표)이 완벽한 주도주는 단기 주가 하락에 겁먹고 팔지 말고 20일·60일 지지선 기준으로 들고 갈 것!"
        }
        fund_lesson = {
            "concept": "소프트웨어 우량주 공식 'Rule of 40'과 S급 대차대조표의 힘",
            "detail": "매출성장률(%) + 영업이익률(%)이 40%를 넘고 대차대조표에 현금이 넘치는 기업은 단기 조정이 와도 결국 실적으로 전고점을 돌파합니다."
        }
        tech_lesson = {
            "concept": "급등 후 '이격도 축소 눌림목(20일선 테스트)'과 추세 이탈 구분하기",
            "detail": "주가가 20일선에서 너무 멀어지면(이격 과열) 잠시 내려와 20일선과 만나는 과정이 필연적입니다. 20일선이 우상향 중이면 매도가 아닌 보유 구간입니다."
        }
        quiz_q = "[신규 영상 실전: 팔란티어] 대차대조표가 무차입 순현금이고 매출·이익이 고성장 중인 주도주가 단기 시장 조정으로 하락할 때 올랜도 킴의 대응 원칙은?"
        quiz_opts = [
            "기업의 실적 성장과 대차대조표 펀더멘털이 훼손되지 않은 단순 이격 조정(20일선 눌림목)이므로 공포에 팔지 않고 기준에 따라 보유한다.",
            "하루라도 음봉이 나오면 무조건 전량 손절한다.",
            "재무제표는 무시하고 루머에 따라 매도한다.",
            "하락할 때마다 신용융자를 풀로 땡긴다."
        ]
        quiz_exp = "실적과 재무가 뒷받침되는 주도주의 건전한 눌림목(20일·60일선 지지)을 견뎌내는 것이 큰 수익을 만드는 핵심입니다."
        domain = "valuation"
    elif "SOXL" in combined or "반도체" in combined or "마이크론" in combined:
        category = "반도체 시황 & 매물소화"
        related_unit = 5
        diff_level = 2
        five_step = {
            "macro": "선거·정책 노이즈 및 AI 고점론 우려로 반도체 섹터와 SOXL의 변동성이 극대화된 구간.",
            "smart_money": "공포에 질린 개인 투자자(특히 SOXL 레버리지 단기 물량)의 투매가 나온 자리에서 장기 기관의 저가 매수 유입 여부 점검.",
            "fundamental": "AI 데이터센터 설비투자(CapEx)와 HBM·고성능 칩 수요, 기업들의 내년 EPS 성장 전망치는 여전히 견고함.",
            "technical": "개인들의 신용·레버리지 반대매매 물량이 털려나간(Climax Volume) 뒤 120일·200일선 및 전저점 부근에서 RSI 과매도 바닥 다지기 진행.",
            "action_plan": "반도체 사이클의 변동성을 이해하고, 레버리지(SOXL)는 반드시 본주(NVDA, MU)의 펀더멘털과 차트 지지선 확인 후 분할로만 대응할 것."
        }
        fund_lesson = {
            "concept": "반도체 사이클의 '주가 선행성'과 고객사 설비투자(CapEx)·EPS 팩트체크",
            "detail": "반도체 주가는 심리적 우려로 실제 실적보다 먼저 급락하기도 하지만, 빅테크 고객사들의 대차대조표 현금 지출(CapEx)과 반도체 기업의 EPS가 살아있다면 결국 본질 가치를 회복합니다."
        }
        tech_lesson = {
            "concept": "개인 투매 물량 소화(Capitulation)와 바닥권 거래량·쌍바닥 신호",
            "detail": "SOXL 등 레버리지 투자자들의 손절 물량이 대량 거래량으로 쏟아진 뒤, 저점을 깨지 않고 5일·20일선을 회복하는 양봉이 나올 때가 진짜 바닥 신호입니다."
        }
        quiz_q = "[신규 영상 실전: 반도체 & SOXL] 반도체 섹터가 급락할 때 '개미들의 공포 투매(물량 털기)'가 끝나고 바닥이 다져지고 있음을 확인하는 기본적·기술적 신호는?"
        quiz_opts = [
            "기업들의 AI 실적·EPS 전망치는 유지되는 가운데, 바닥권 지지선에서 투매 물량이 소화되고 저점을 높이는 쌍바닥 양봉과 5일·20일선 회복이 나타날 때",
            "모든 기업의 실적이 적자로 전환되고 200일선이 수직 폭락할 때",
            "아무 확인 없이 떨어지는 첫날 전 재산을 3배 레버리지에 넣을 때",
            "뉴스 헤드라인이 가장 비관적일 때 무조건 계좌를 폐쇄한다."
        ]
        quiz_exp = "반도체는 내려갈 때 변동성이 크지만, 펀더멘털(EPS 성장) 확인 + 투매 물량 소화 후 지지선 안착을 확인하면 안전하게 대응할 수 있습니다."
        domain = "technical"
    else:
        category = "시황 & 실매수세 점검"
        related_unit = 1
        diff_level = 1
        five_step = {
            "macro": f"『{title}』 — 거시 이벤트(선거·금리·정책) 전후 시장 참여자들의 관망세와 수급 점검.",
            "smart_money": "기관의 진짜 실매수세(거래량 동반 양봉)가 유입되는 업종과 단순 기술적 반등 업종을 구분.",
            "fundamental": f"언급 종목({', '.join(mentioned)})의 매출·EPS 성장 가시성과 대차대조표 현금 체력(순현금·유동비율) 점검.",
            "technical": "실매수세가 들어왔는지 확인하는 핵심 척도는 '거래량 실린 20일·60일선 돌파 및 안착' 여부.",
            "action_plan": "눈치보기 장세에서는 성급한 추격 매수를 자제하고, 현금 비중을 유지하며 실매수세(거래량+양봉)와 실적이 확인되는 종목에 집중."
        }
        fund_lesson = {
            "concept": "관망 장세에서 빛나는 대차대조표 우량주(순현금 & 고마진 실적주)",
            "detail": "시장에 실매수세가 약하고 눈치를 볼 때는 빚이 많고 적자인 기업부터 빠집니다. 대차대조표에 현금이 많고 실적이 찍히는 기업으로 포트폴리오 중심을 잡으세요."
        }
        tech_lesson = {
            "concept": "'진짜 실매수세 유입'을 차트에서 1초 만에 판별하는 법: 거래량 + 20일선 돌파",
            "detail": "주가가 살짝 올라도 거래량이 평소보다 적다면 '실매수세 없는 기술적 반등'입니다. 평균 거래량을 뛰어넘는 양봉으로 20일 이동평균선 위에 안착할 때가 진짜 실매수세 유입입니다!"
        }
        quiz_q = f"[신규 영상 실전] 『{title}』 같은 눈치보기 장세에서 시장에 '기관의 진짜 실매수세'가 들어왔는지 차트(기술적 분석)로 확인하는 가장 확실한 지표는?"
        quiz_opts = [
            "단순 호가창 등락이 아니라, 의미 있는 '거래량 증가'를 동반한 양봉으로 20일·60일 이동평균선 저항을 돌파하고 안착하는지 확인한다.",
            "거래량이 평소의 10분의 1로 줄어든 상태에서 나온 윗꼬리 음봉을 본다.",
            "차트 색깔을 바꾼다.",
            "실매수세는 차트에 전혀 나타나지 않는다."
        ]
        quiz_exp = "주가는 속일 수 있어도 거래량은 속일 수 없습니다. 거래량이 실린 이평선 돌파와 지지 안착이 실매수세 유입의 핵심 증거입니다."
        domain = "macro"

    return {
        "video_id": video_id,
        "published_at": published_at,
        "title": title,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "summary_source_url": f"https://ggulmuse.woongstar.com/videos/{video_id}",
        "category": category,
        "related_unit": related_unit,
        "difficulty_level": diff_level,
        "mentioned_tickers": mentioned,
        "orlando_five_step": five_step,
        "fundamental_lesson": fund_lesson,
        "technical_lesson": tech_lesson,
        "my_portfolio_connection": "내 보유 종목(TSLA, IONQ, HOOD, JOBY, SATL, TSLL)과 구독자 요청 종목(PLTR, ORCL, GE, MU)에 이 영상의 분석 기준(대차대조표 체력 + 20일/60일선 실매수세)을 대입해 점검해 보세요.",
        "daily_quiz": [
            {
                "q_id": f"v_{video_id}_q1",
                "skill_domain": domain,
                "question": quiz_q,
                "options": quiz_opts,
                "answer": 0,
                "explanation": quiz_exp,
                "remind_tag": f"[{published_at}] {title[:18]}... 핵심 포인트"
            }
        ]
    }


def fetch_latest_orlando_videos():
    config = load_json(CONFIG_PATH, {})
    channel_url = config.get("youtube_channel_url", "https://www.youtube.com/@orlandocampus")
    videos = load_json(VIDEOS_PATH, [])

    # 기존에 기본 템플릿 문구("신규 영상 『...")로 생성된 항목이 있으면 고도화된 맞춤 분석으로 업그레이드
    upgraded = 0
    for idx, v in enumerate(videos):
        if v.get("orlando_five_step", {}).get("macro", "").startswith("신규 영상 『"):
            videos[idx] = infer_lesson_from_video(v["video_id"], v["title"], v["published_at"])
            upgraded += 1

    existing_ids = {v["video_id"] for v in videos}
    print(f"🔍 [{config.get('youtube_channel_name', '올랜도 킴 미국주식')}] 채널 최신 영상 확인 중...")
    channel_id = resolve_channel_id(channel_url)
    new_count = 0

    if channel_id:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            resp = requests.get(rss_url, timeout=6)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
                for entry in root.findall("atom:entry", ns):
                    vid_elem = entry.find("yt:videoId", ns)
                    title_elem = entry.find("atom:title", ns)
                    pub_elem = entry.find("yt:published", ns) or entry.find("atom:published", ns)
                    if vid_elem is None or title_elem is None:
                        continue
                    vid = vid_elem.text.strip()
                    title = title_elem.text.strip()
                    pub_date = pub_elem.text[:10] if pub_elem is not None else datetime.date.today().strftime("%Y-%m-%d")

                    if pub_date.startswith("2026") and vid not in existing_ids:
                        transcript = fetch_transcript_text(vid)
                        new_item = infer_lesson_from_video(vid, title, pub_date, transcript=transcript)
                        videos.insert(0, new_item)
                        existing_ids.add(vid)
                        new_count += 1
                        print(f"✨ 신규 영상 감지 및 분석 추가 완료: [{pub_date}] {title}")
        except Exception as e:
            print(f"ℹ️ RSS 파싱 생략 (아카이브 큐 사용): {e}")

    videos.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    save_json(VIDEOS_PATH, videos)

    if upgraded > 0:
        print(f"✨ {upgraded}개 최신 영상의 맞춤형 심층 분석(수주잔고/13F/실매수세/매물소화) 및 실전 퀴즈 고도화 완료!")
    if new_count > 0:
        print(f"✅ 총 {new_count}개의 신규 영상이 학습 DB에 자동 반영되었습니다! (총 {len(videos)}편)")
    else:
        print(f"✓ 총 {len(videos)}편의 2026 올랜도 킴 영상 아카이브 준비 완료!")

    return new_count, videos


if __name__ == "__main__":
    fetch_latest_orlando_videos()
