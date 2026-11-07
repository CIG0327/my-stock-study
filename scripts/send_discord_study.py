import os
import sys
import json
import time
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
WEB_DATA_PATH = os.path.join(BASE_DIR, "web", "data.js")


def get_webhook_url():
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip().strip('"').strip("'")
    if url:
        return url
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg.get("discord_webhook_url", "").strip()
    return ""


def load_bundle():
    if not os.path.exists(WEB_DATA_PATH):
        raise FileNotFoundError("web/data.js 파일이 없습니다. 먼저 build_daily_lesson.py를 실행하세요.")
    with open(WEB_DATA_PATH, "r", encoding="utf-8") as f:
        raw = f.read().replace("window.STUDY_APP_DATA =", "").strip()
        if raw.endswith(";"):
            raw = raw[:-1].strip()
        return json.loads(raw)


def format_spoiler_quiz(q_obj, label):
    opts = []
    for idx, opt in enumerate(q_obj["options"]):
        opts.append(f"**{idx + 1}번.** {opt}")
    ans_num = q_obj["answer"] + 1
    ans_text = q_obj["options"][q_obj["answer"]]
    return (
        f"**Q. {q_obj['question']}**\n"
        + "\n".join(opts)
        + f"\n\n👉 **정답 확인 (아래 검은 박스를 터치하세요!)**\n"
        + f"||🎯 **정답: {ans_num}번 ({ans_text})**\n💡 **해설:** {q_obj['explanation']}||"
    )


def send_discord_study(dry_run=False):
    bundle = load_bundle()
    tb = bundle["today_briefing"]
    v = tb["video"]
    sub = tb.get("subscriber_event")
    my_st = tb["my_stock_spotlight"]
    study_date = tb["study_date"]

    # 카드 1: 오늘의 올랜도 킴 영상 벤치마킹 & 기본×기술적 균형 레슨
    embed_lesson = {
        "title": f"🎓 [올랜도 킴 벤치마킹 스터디] {study_date} 오늘의 주식 공부",
        "url": v["youtube_url"],
        "description": (
            f"{tb['mode_badge']}\n"
            f"🎬 **기준 영상:** [{v['title']}]({v['youtube_url']}) (`{v['published_at']}`)\n"
            f"📚 **연결 단원:** `{tb['unit_summary']['title']}`"
        ),
        "color": 0x6366F1,
        "fields": [
            {
                "name": "🧭 올랜도 킴 5단계 분석 핵심 요약",
                "value": (
                    f"• **1) 매크로/시황:** {v['orlando_five_step']['macro']}\n"
                    f"• **2) 스마트머니:** {v['orlando_five_step']['smart_money']}\n"
                    f"• **3) 기본적(재무):** {v['orlando_five_step']['fundamental']}\n"
                    f"• **4) 기술적(차트):** {v['orlando_five_step']['technical']}\n"
                    f"• **5) 대응 원칙:** {v['orlando_five_step']['action_plan']}"
                )[:1020],
                "inline": False
            },
            {
                "name": f"📊 오늘의 기본적 분석 (대차대조표·손익): {v['fundamental_lesson']['concept']}",
                "value": v["fundamental_lesson"]["detail"][:1020],
                "inline": False
            },
            {
                "name": f"📈 오늘의 기술적 분석 (차트·이평선): {v['technical_lesson']['concept']}",
                "value": v["technical_lesson"]["detail"][:1020],
                "inline": False
            }
        ],
        "footer": {
            "text": "Antigravity Stock Academy • 기본적 분석 50% × 기술적 분석 50% 균형 학습"
        }
    }

    # 카드 2: 구독자 요청 종목 이벤트 & 내 보유종목 실전 대조
    fields_card2 = []
    if sub:
        fields_card2.append({
            "name": f"🎁 [구독자 요청 종목 이벤트] {sub['name']} ({sub['ticker']})",
            "value": (
                f"💬 *{sub['subscriber_story']}*\n"
                f"⚡ **올랜도 킴 식 진단:** {sub['orlando_verdict']}\n"
                f"• **재무(대차대조표/손익):** {sub['fundamental_check']}\n"
                f"• **차트(기술적 타점):** {sub['technical_check']}"
            )[:1020],
            "inline": False
        })

    fields_card2.append({
        "name": f"💼 [내 보유종목 실전 대조] {my_st['name']} ({my_st['ticker']})",
        "value": (
            f"• **내 평단가 / 현재가:** `${my_st.get('my_avg_usd', '-')}` / `${my_st['technical']['current_price']}`\n"
            f"• **대차대조표 체력:** **{my_st['fundamental']['bs_grade']}** ({my_st['fundamental']['net_cash_status']})\n"
            f"• **차트 배열 & 지지/저항:** {my_st['technical']['ma_alignment']} | 지지 `${my_st['technical']['support']}` / 저항 `${my_st['technical']['resistance']}` (RSI `{my_st['technical']['rsi']}`)\n"
            f"• **실전 학습 포인트:** {my_st['study_point']}"
        )[:1020],
        "inline": False
    })

    embed_event = {
        "title": "🎁 오늘의 구독자 요청 종목 이벤트 & 💼 내 보유종목 실전 적용",
        "color": 0x10B981,
        "fields": fields_card2
    }

    # 카드 3: 휴대폰 1분 스포일러 퀴즈 브리핑
    quiz_fields = []
    if v.get("daily_quiz"):
        q1 = v["daily_quiz"][0]
        quiz_fields.append({
            "name": "📝 [문제 1] 오늘의 영상 × 재무·차트 실전 퀴즈",
            "value": format_spoiler_quiz(q1, "문제 1")[:1020],
            "inline": False
        })
    if sub and sub.get("quiz"):
        q2 = sub["quiz"]
        quiz_fields.append({
            "name": f"🎁 [문제 2] 구독자 요청 종목({sub['ticker']}) 이벤트 퀴즈 (+50 XP)",
            "value": format_spoiler_quiz(q2, "문제 2")[:1020],
            "inline": False
        })

    embed_quiz = {
        "title": "🧠 출근길 1분 스포일러 퀴즈 & 리마인드 테스트",
        "description": "마음속으로 정답을 고른 뒤 **검은색 가림막(`||...||`)을 손가락으로 터치**해 정답과 해설을 확인하세요! 모바일 웹앱에서 풀면 내 레벨(XP)과 5대 역량 진단 차트에 자동 반영됩니다.",
        "color": 0xF59E0B,
        "fields": quiz_fields,
        "footer": {
            "text": "휴대폰 웹앱에서 단원별 테스트 및 오답 리마인드 노트를 진행하세요!"
        }
    }

    if dry_run:
        print("✓ [Dry-Run] 디스코드 전송 페이로드 생성 및 검증 완료! (총 3개 임베드 카드)")
        return True

    webhook_url = get_webhook_url()
    if not webhook_url:
        print("⚠️ 디스코드 웹훅 URL이 설정되지 않아 콘솔 출력으로 대체합니다.")
        return False

    try:
        for idx, emb in enumerate([embed_lesson, embed_event, embed_quiz], 1):
            r = requests.post(webhook_url, json={"embeds": [emb]}, timeout=8)
            if r.status_code in (200, 204):
                print(f"✓ 디스코드 스터디 카드 [{idx}/3] 전송 성공!")
            else:
                print(f"⚠️ 디스코드 카드 [{idx}/3] 응답 코드: {r.status_code}")
            time.sleep(0.5)
        return True
    except Exception as e:
        print(f"ℹ️ 디스코드 전송 생략 (오프라인/샌드박스 환경): {e}")
        return False


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    send_discord_study(dry_run=is_dry)

