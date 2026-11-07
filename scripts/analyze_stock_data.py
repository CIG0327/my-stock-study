import os
import sys
import re
import json
import datetime
import numpy as np
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(BASE_DIR, "data", "market_snapshots.json")
MY_STOCK_MD_PATH = os.path.join(os.path.dirname(BASE_DIR), "MyStockManagement", "종목.md")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sync_my_holdings_from_md(stocks):
    """MyStockManagement/종목.md의 보유종목 평단가 및 수량을 자동 연동"""
    if not os.path.exists(MY_STOCK_MD_PATH):
        return
    try:
        with open(MY_STOCK_MD_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        parsed = {}
        for line in lines:
            line = line.strip()
            if line.startswith("-"):
                parts = [p.strip() for p in line[1:].split(",")]
                # 형식: - 종목명, 평단(원), 평단(달러), 수량, ID, 티커
                if len(parts) >= 6:
                    ticker = parts[-1].upper()
                    try:
                        avg_usd = float(parts[3].replace(",", ""))
                        shares = int(float(parts[4].replace(",", "")))
                        parsed[ticker] = (avg_usd, shares)
                    except Exception:
                        pass
        for st in stocks:
            tk = st["ticker"]
            if tk in parsed:
                st["is_my_holding"] = True
                st["my_avg_usd"] = round(parsed[tk][0], 2)
                st["my_shares"] = parsed[tk][1]
    except Exception as e:
        print(f"ℹ️ 종목.md 동기화 참고: {e}")


def compute_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 55.0
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 70.0
    rs = up / down
    rsi = 100.0 - 100.0 / (1.0 + rs)
    for delta in deltas[period:]:
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 100
        rsi = 100.0 - 100.0 / (1.0 + rs)
    return round(float(rsi), 1)


def try_update_live_chart(stock):
    """Yahoo Finance v8 chart API를 통해 최신 캔들/이평선/RSI 갱신 시도"""
    ticker = stock["ticker"]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code != 200:
            return False
        res = r.json()["chart"]["result"][0]
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
        if len(closes) < 30:
            return False

        tech = stock["technical"]
        curr = round(float(closes[-1]), 2)
        ma5 = round(float(np.mean(closes[-5:])), 2)
        ma20 = round(float(np.mean(closes[-20:])), 2)
        ma60 = round(float(np.mean(closes[-60:])), 2) if len(closes) >= 60 else ma20
        ma200 = round(float(np.mean(closes[-200:])), 2) if len(closes) >= 200 else ma60

        tech["current_price"] = curr
        tech["ma5"] = ma5
        tech["ma20"] = ma20
        tech["ma60"] = ma60
        tech["ma200"] = ma200
        tech["rsi"] = compute_rsi(closes)
        tech["price_history"] = [round(float(x), 2) for x in closes[-20:]]
        tech["support"] = round(float(min(closes[-20:])), 2)
        tech["resistance"] = round(float(max(closes[-60:])), 2)

        if curr >= ma5 >= ma20 >= ma60:
            tech["ma_alignment"] = "강한 정배열 우상향 (현재가 > 5일 > 20일 > 60일)"
        elif curr >= ma20:
            tech["ma_alignment"] = "20일 생명선 위 단기 우상향 유지"
        elif curr >= ma60:
            tech["ma_alignment"] = "20일선 조정 후 60일 중기 수급선 지지 테스트"
        else:
            tech["ma_alignment"] = "중단기 이평선 하회 — 바닥 다지기 및 20일선 탈환 확인 필요"
        return True
    except Exception:
        return False


def update_market_snapshots():
    snap = load_json(SNAPSHOT_PATH, {"updated_at": "", "stocks": []})
    stocks = snap.get("stocks", [])
    sync_my_holdings_from_md(stocks)

    print("📊 [기본적 분석 × 기술적 분석] 9대 핵심 종목(올랜도킴 빈출 + 내 보유종목) 데이터 점검 중...")
    live_updated = 0
    for st in stocks:
        if try_update_live_chart(st):
            live_updated += 1

    snap["updated_at"] = datetime.date.today().strftime("%Y-%m-%d")
    save_json(SNAPSHOT_PATH, snap)
    print(f"✅ 총 {len(stocks)}개 종목 대차대조표·손익 및 기술적 차트 스냅샷 준비 완료! (실시간 시세 갱신: {live_updated}종목)")
    return snap


if __name__ == "__main__":
    update_market_snapshots()
