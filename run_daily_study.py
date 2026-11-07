import os
import sys
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")


def run_step(script_name, desc, extra_args=None):
    print("\n============================================================")
    print(f"▶ {desc} ({script_name})")
    print("============================================================")
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, script_name)]
    if extra_args:
        cmd.extend(extra_args)
    res = subprocess.run(cmd, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"❌ {script_name} 실행 중 오류 발생 (코드: {res.returncode})")
        return False
    return True


def main():
    print("🚀 [주식공부하기(Anitigravity)] 올랜도 킴 벤치마킹 & 일일 스마트 학습 파이프라인 시작")
    extra = ["--dry-run"] if "--dry-run" in sys.argv else []

    # 1. 유튜브 @orlandocampus 신규 영상 확인 및 아카이브 동기화
    if not run_step("fetch_youtube.py", "1단계: 올랜도 킴(@orlandocampus) 신규 영상 감지 및 자막/프레임워크 추출"):
        sys.exit(1)

    # 2. 언급 종목 + 구독자 요청 종목 + 내 보유 종목의 기본적(대차대조표)·기술적(차트) 지표 업데이트
    if not run_step("analyze_stock_data.py", "2단계: 기본적 분석(대차대조표·손익) × 기술적 분석(차트·이평선) 데이터 갱신"):
        sys.exit(1)

    # 3. 오늘의 스마트 레슨(신규 영상 or 미학습 최근 영상 + 구독자 요청 이벤트 + 내 종목) 및 web/data.js 빌드
    if not run_step("build_daily_lesson.py", "3단계: 오늘의 맞춤 학습 카드 & 1분 퀴즈 & 모바일 웹앱(data.js) 생성"):
        sys.exit(1)

    # 4. 휴대폰 디스코드로 오늘의 학습 & 스포일러 퀴즈 브리핑 전송
    if not run_step("send_discord_study.py", "4단계: 휴대폰 디스코드 일일 학습 & 1분 스포일러 퀴즈 알림 전송", extra):
        sys.exit(1)

    print("\n🎉 오늘의 주식 학습 업데이트가 완료되었습니다! 휴대폰(디스코드 및 모바일 웹앱 web/index.html)에서 학습을 시작하세요.")


if __name__ == "__main__":
    main()

