import os
import sys
import json
import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
WEB_DIR = os.path.join(BASE_DIR, "web")

CURRICULUM_PATH = os.path.join(DATA_DIR, "curriculum.json")
VIDEOS_PATH = os.path.join(DATA_DIR, "videos_2026.json")
SNAPSHOT_PATH = os.path.join(DATA_DIR, "market_snapshots.json")
SUB_EVENTS_PATH = os.path.join(DATA_DIR, "subscriber_events.json")
QUEUE_STATE_PATH = os.path.join(DATA_DIR, "daily_queue_state.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


LEVEL_SYSTEM = [
    {
        "level": 1,
        "badge": "🌱 Lv.1 주린이 입문자",
        "min_xp": 0,
        "max_xp": 199,
        "summary": "주식·지수·ETF의 기본 개념을 익히고, 올랜도 킴 영상에서 '주장'과 '팩트'를 구분하기 시작하는 단계입니다.",
        "next_goal": "1~2단원 기본 개념 학습 및 초기 레벨 진단 테스트 완료하기"
    },
    {
        "level": 2,
        "badge": "🌿 Lv.2 재무·차트 해독가",
        "min_xp": 200,
        "max_xp": 449,
        "summary": "손익계산서(매출·영업이익·EPS)와 차트의 이동평균선(5·20·60·200일선)을 동시에 읽을 수 있는 단계입니다.",
        "next_goal": "3단원 대차대조표(현금 vs 부채) 마스터 테스트 통과 및 구독자 요청 종목 이벤트 2건 해결"
    },
    {
        "level": 3,
        "badge": "🌳 Lv.3 대차대조표 & 수급 분석가",
        "min_xp": 450,
        "max_xp": 749,
        "summary": "대차대조표(유동비율·순현금·이연수익)로 기업의 생존 체력을 진단하고, 직전 고점 매물대 소화와 기관 수급(13F)을 읽어내는 중급 투자자입니다.",
        "next_goal": "4~5단원 밸류에이션(PEG) 및 매물대 차트 테스트 80점 이상 달성"
    },
    {
        "level": 4,
        "badge": "🦅 Lv.4 실전 밸류 & 시나리오 전략가",
        "min_xp": 750,
        "max_xp": 1099,
        "summary": "Forward PER·PEG로 가격 적정성을 계산하고, 외부 악재 시 '펀더멘털 훼손'과 '일시적 노이즈'를 구분해 지지선 분할 매수를 실행하는 단계입니다.",
        "next_goal": "6단원 통합 실전 분석 마스터 및 오답 리마인드 노트 완전 정복"
    },
    {
        "level": 5,
        "badge": "👑 Lv.5 올랜도 킴 마스터 독립 투자자",
        "min_xp": 1100,
        "max_xp": 99999,
        "summary": "어떤 시황 영상이나 구독자 요청 종목을 보더라도 1차 공시(대차대조표·손익)와 기술적 차트로 교차 검증하여 나만의 기준으로 투자하는 완성형 투자자입니다!",
        "next_goal": "매일 자동 업데이트되는 영상과 내 포트폴리오 종목 점검 루틴 유지"
    }
]


def select_today_study(videos, sub_events, stocks, curriculum):
    """
    신규 영상이 올라왔으면 신규 영상을,
    신규 영상이 없는 날이라도 아직 학습 큐에서 다루지 않은 최근 영상 + 구독자 요청 종목 + 내 보유 종목을
    자동 매칭하여 매일 공부가 끊기지 않도록 구성합니다.
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    state = load_json(QUEUE_STATE_PATH, {
        "last_date": "",
        "completed_video_ids": [],
        "sub_event_idx": 0,
        "my_stock_idx": 0,
        "history": []
    })

    # 오늘 이미 생성된 브리핑이 있으면 그대로 유지하되 최신 데이터 반영
    completed_ids = state.get("completed_video_ids", [])

    # 1. 아직 큐에서 소화하지 않은 가장 최근 영상 선택 (모두 소화했으면 다시 처음부터 심화 순회)
    unseen_videos = [v for v in videos if v["video_id"] not in completed_ids]
    if not unseen_videos:
        completed_ids = []
        unseen_videos = videos

    selected_video = unseen_videos[0]
    is_brand_new = (selected_video.get("published_at") == today_str)

    # 2. 오늘의 구독자 요청 종목 이벤트 선택
    sub_idx = state.get("sub_event_idx", 0) % len(sub_events) if sub_events else 0
    selected_sub_event = sub_events[sub_idx] if sub_events else None

    # 3. 오늘의 내 보유종목 집중 스터디 선택
    my_holdings = [s for s in stocks if s.get("is_my_holding")]
    if not my_holdings:
        my_holdings = stocks
    my_idx = state.get("my_stock_idx", 0) % len(my_holdings)
    selected_my_stock = my_holdings[my_idx]

    # 4. 연결 단원 정보 추출
    unit_num = selected_video.get("related_unit", 1)
    units = curriculum.get("units", [])
    matched_unit = next((u for u in units if u["unit_id"] == unit_num), units[0] if units else {})

    # 날짜가 바뀌었거나 최초 실행이면 큐 포인터 전진 기록
    if state.get("last_date") != today_str:
        if selected_video["video_id"] not in completed_ids:
            completed_ids.append(selected_video["video_id"])
        state["last_date"] = today_str
        state["completed_video_ids"] = completed_ids
        state["sub_event_idx"] = sub_idx + 1
        state["my_stock_idx"] = my_idx + 1
        state["history"].insert(0, {
            "study_date": today_str,
            "video_id": selected_video["video_id"],
            "video_title": selected_video["title"],
            "video_date": selected_video["published_at"],
            "mode": "신규 업로드 영상 실시간 학습" if is_brand_new else "최근 미학습 영상 & 심화 커리큘럼 자동 진행",
            "sub_event_ticker": selected_sub_event["ticker"] if selected_sub_event else "-",
            "my_stock_ticker": selected_my_stock["ticker"]
        })
        state["history"] = state["history"][:30]
        save_json(QUEUE_STATE_PATH, state)

    mode_badge = (
        "🔴 [신규 영상 업로드 반영] 오늘 올라온 최신 영상 기반 학습"
        if is_brand_new
        else "🟢 [스마트 연속 학습 모드] 최근 미학습 영상 × 기본·기술적 개념 × 구독자 요청 종목 집중 학습"
    )

    return {
        "study_date": today_str,
        "mode_badge": mode_badge,
        "video": selected_video,
        "unit_summary": {
            "unit_id": matched_unit.get("unit_id", 1),
            "title": matched_unit.get("title", ""),
            "subtitle": matched_unit.get("subtitle", "")
        },
        "subscriber_event": selected_sub_event,
        "my_stock_spotlight": selected_my_stock,
        "queue_history": state.get("history", [])
    }


def generate_markdown_docs(curriculum, videos, stocks, sub_events, today_briefing):
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. 01_올랜도킴_2026_벤치마킹_프레임워크.md
    bp = curriculum["benchmark_profile"]
    md1 = [
        f"# 🎯 {bp['channel_name']} 2026년 영상 분석 & 벤치마킹 프레임워크\n",
        f"- **채널 링크**: [{bp['channel_name']}]({bp['channel_url']})",
        f"- **핵심 투자 철학**: {bp['core_philosophy']}\n",
        "## 1. 올랜도 킴의 5단계 주식·기업 분석 깔때기 (5-Step Funnel)\n"
    ]
    for p in bp["five_pillars"]:
        md1.append(f"### Step {p['step']}. {p['title']}")
        md1.append(f"- **핵심 요지**: {p['summary']}")
        md1.append(f"- **주요 점검 지표**: `{', '.join(p['key_metrics'])}`\n")

    md1.append("## 2. 2026년 주요 영상별 핵심 분석 아카이브\n")
    md1.append("| 공개일 | 영상 제목 | 분류 | 연결 단원 | 기본적 분석(재무/대차대조표) 핵심 | 기술적 분석(차트) 핵심 |")
    md1.append("|---|---|---|---|---|---|")
    for v in videos:
        md1.append(
            f"| {v['published_at']} | [{v['title']}]({v['youtube_url']}) | {v['category']} | {v['related_unit']}단원 | {v['fundamental_lesson']['concept']} | {v['technical_lesson']['concept']} |"
        )
    with open(os.path.join(DOCS_DIR, "01_올랜도킴_2026_벤치마킹_프레임워크.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md1) + "\n")

    # 2. 02_기본적분석x기술적분석_통합커리큘럼.md
    md2 = [
        "# 📚 기본적 분석(대차대조표·손익) × 기술적 분석(차트) 6단원 통합 커리큘럼\n",
        "> 초보자부터 시작해 5단계 레벨 진단 시스템을 통해 'Lv.5 올랜도 킴 마스터 독립 투자자'로 성장하는 맞춤형 커리큘럼입니다.\n"
    ]
    for u in curriculum["units"]:
        md2.append(f"## {u['title']}")
        md2.append(f"**{u['subtitle']}** (권장 학습 시간: {u['estimated_minutes']}분)\n")
        md2.append("### 🎯 학습 목표")
        for obj in u["learning_objectives"]:
            md2.append(f"- {obj}")
        md2.append(f"\n### {u['fundamental_section']['title']}")
        for c in u["fundamental_section"]["core_concepts"]:
            md2.append(f"- **{c['term']}** (`{c['formula']}`)\n  - {c['explanation']}")
        md2.append(f"\n### {u['technical_section']['title']}")
        for c in u["technical_section"]["core_concepts"]:
            md2.append(f"- **{c['term']}** (`{c['pattern']}`)\n  - {c['explanation']}")
        cs = u["orlando_case_study"]
        md2.append(f"\n### 🎬 올랜도 킴 2026 실제 영상 벤치마킹: 『{cs['video_title']}』 ({cs['video_date']})")
        md2.append(f"- **분석 포인트**: {cs['how_orlando_analyzed']}")
        md2.append(f"- **실전 적용**: {cs['actionable_takeaway']}\n---\n")
    with open(os.path.join(DOCS_DIR, "02_기본적분석x기술적분석_통합커리큘럼.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md2) + "\n")

    # 3. 03_일일_영상분석_및_구독자요청_학습일지.md
    v = today_briefing["video"]
    sub = today_briefing["subscriber_event"]
    my_st = today_briefing["my_stock_spotlight"]
    md3 = [
        f"# 📅 일일 스마트 주식 학습 일지 (최신 업데이트: {today_briefing['study_date']})\n",
        f"**상태**: {today_briefing['mode_badge']}\n",
        f"## 1. 오늘의 메인 영상 분석: 『{v['title']}』 ({v['published_at']})",
        f"- **원본 링크**: {v['youtube_url']} | **연결 단원**: {today_briefing['unit_summary']['title']}",
        f"- **① 매크로/시황**: {v['orlando_five_step']['macro']}",
        f"- **② 스마트 머니/수급**: {v['orlando_five_step']['smart_money']}",
        f"- **③ 기본적 분석(재무/대차대조표)**: {v['orlando_five_step']['fundamental']}",
        f"- **④ 기술적 분석(차트/이평선)**: {v['orlando_five_step']['technical']}",
        f"- **⑤ 대응 원칙**: {v['orlando_five_step']['action_plan']}\n",
        f"### 💡 오늘의 기본적 분석 × 기술적 분석 핵심 레슨",
        f"- **기본적 분석**: **{v['fundamental_lesson']['concept']}** — {v['fundamental_lesson']['detail']}",
        f"- **기술적 분석**: **{v['technical_lesson']['concept']}** — {v['technical_lesson']['detail']}",
        f"- **내 포트폴리오 연결**: {v['my_portfolio_connection']}\n"
    ]
    if sub:
        md3.extend([
            f"## 2. 🎁 오늘의 구독자 요청 종목 이벤트 스터디: {sub['name']} (`{sub['ticker']}`)",
            f"- **구독자 고민**: {sub['subscriber_story']}",
            f"- **올랜도 킴 식 한 줄 진단**: **{sub['orlando_verdict']}**",
            f"- **기본적 분석(대차대조표·손익)**: {sub['fundamental_check']}",
            f"- **기술적 분석(차트·지지/저항)**: {sub['technical_check']}\n"
        ])
    md3.extend([
        f"## 3. 💼 오늘의 내 보유종목 집중 점검: {my_st['name']} (`{my_st['ticker']}`)",
        f"- **내 평단가 / 현재가**: `${my_st.get('my_avg_usd', '-')}` / `${my_st['technical']['current_price']}`",
        f"- **대차대조표 체력 등급**: **{my_st['fundamental']['bs_grade']}** ({my_st['fundamental']['net_cash_status']})",
        f"- **대차대조표 해설**: {my_st['fundamental']['bs_comment']}",
        f"- **차트 기술적 위치**: {my_st['technical']['ma_alignment']} (지지 `${my_st['technical']['support']}` / 저항 `${my_st['technical']['resistance']}` / RSI `{my_st['technical']['rsi']}`)",
        f"- **차트 해설**: {my_st['technical']['tech_comment']}\n"
    ])
    with open(os.path.join(DOCS_DIR, "03_일일_영상분석_및_구독자요청_학습일지.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md3) + "\n")


def build_all():
    curriculum = load_json(CURRICULUM_PATH, {})
    videos = load_json(VIDEOS_PATH, [])
    snap = load_json(SNAPSHOT_PATH, {"updated_at": "", "stocks": []})
    sub_events = load_json(SUB_EVENTS_PATH, [])

    today_briefing = select_today_study(videos, sub_events, snap.get("stocks", []), curriculum)
    generate_markdown_docs(curriculum, videos, snap.get("stocks", []), sub_events, today_briefing)

    bundle = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "level_system": LEVEL_SYSTEM,
        "today_briefing": today_briefing,
        "curriculum": curriculum,
        "videos_2026": videos,
        "market_snapshots": snap,
        "subscriber_events": sub_events
    }

    os.makedirs(WEB_DIR, exist_ok=True)
    data_js_path = os.path.join(WEB_DIR, "data.js")
    data_js_content = "window.STUDY_APP_DATA = " + json.dumps(bundle, ensure_ascii=False, indent=2) + ";\n"
    with open(data_js_path, "w", encoding="utf-8") as f:
        f.write(data_js_content)

    # 아이폰 카톡/파일 전송용 단일 올인원 HTML 파일(CSS + data.js + app.js 내장) 자동 생성
    index_path = os.path.join(WEB_DIR, "index.html")
    css_path = os.path.join(WEB_DIR, "style.css")
    app_js_path = os.path.join(WEB_DIR, "app.js")
    if os.path.exists(index_path) and os.path.exists(css_path) and os.path.exists(app_js_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html_str = f.read()
        with open(css_path, "r", encoding="utf-8") as f:
            css_str = f.read()
        with open(app_js_path, "r", encoding="utf-8") as f:
            js_str = f.read()

        standalone_html = html_str.replace(
            '<link rel="stylesheet" href="style.css" />',
            f"<style>\n{css_str}\n</style>"
        ).replace(
            '<script src="data.js"></script>\n  <script src="app.js"></script>',
            f"<script>\n{data_js_content}\n</script>\n<script>\n{js_str}\n</script>"
        )
        standalone_path = os.path.join(WEB_DIR, "아이폰용_올인원_주식공부앱.html")
        with open(standalone_path, "w", encoding="utf-8") as f:
            f.write(standalone_html)

    print(f"✅ 오늘의 스터디 번들(web/data.js, 아이폰용_올인원_주식공부앱.html) 및 마크다운 학습 노트 3종 생성 완료!")
    print(f"   📌 오늘의 메인 영상: [{today_briefing['video']['published_at']}] {today_briefing['video']['title']}")
    if today_briefing["subscriber_event"]:
        print(f"   🎁 오늘의 구독자 요청 이벤트 종목: {today_briefing['subscriber_event']['name']} ({today_briefing['subscriber_event']['ticker']})")
    print(f"   💼 오늘의 내 보유종목 스포트라이트: {today_briefing['my_stock_spotlight']['name']} ({today_briefing['my_stock_spotlight']['ticker']})")
    return bundle


if __name__ == "__main__":
    build_all()

