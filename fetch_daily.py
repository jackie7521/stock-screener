"""
每日盤後抓資料程式
==================
由 GitHub Actions 每日 15:30 (TPE) 自動執行。
抓取台股全市場資料，寫入 Google Sheet。

環境變數：
    GOOGLE_CREDENTIALS  - Service Account JSON 字串
    SHEET_ID            - Google Sheet ID

資料來源：
    - TWSE OpenAPI (上市)
    - TPEx OpenAPI (上櫃)
"""

import os
import json
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# 設定
# ============================================================
TPE = timezone(timedelta(hours=8))
TODAY = datetime.now(TPE).strftime("%Y-%m-%d")
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 30

# TWSE / TPEx OpenAPI 端點
URLS = {
    "twse_daily": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
    "tpex_daily": "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
    "twse_t86":   "https://openapi.twse.com.tw/v1/fund/T86",
    "tpex_t86":   "https://www.tpex.org.tw/openapi/v1/tpex_3insti_summary_daily",
    "market_idx": "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK",
    "sector_idx": "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX",
    "warn_attn":  "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
}

GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ============================================================
# Google Sheet 連線
# ============================================================
def get_gsheet():
    """連線 Google Sheet。"""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    sheet_id = os.environ.get("SHEET_ID")
    if not creds_json or not sheet_id:
        sys.exit("❌ 缺少環境變數 GOOGLE_CREDENTIALS 或 SHEET_ID")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=GSHEETS_SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)


def get_or_create_ws(spreadsheet, title, headers):
    """取得或新建工作表，並確保表頭存在。"""
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws


def append_dedup(ws, df, key_cols):
    """append DataFrame 到工作表，以 key_cols 去重（避免同日重跑時重複）。"""
    if df.empty:
        print(f"  ⚠️ {ws.title}: 無資料可寫入")
        return

    existing = pd.DataFrame(ws.get_all_records())
    if not existing.empty:
        # 將 key 欄轉成 str 比對
        new_keys = df[key_cols].astype(str).agg("|".join, axis=1)
        old_keys = existing[key_cols].astype(str).agg("|".join, axis=1)
        df = df[~new_keys.isin(old_keys.values)]
        if df.empty:
            print(f"  ⚠️ {ws.title}: 今日資料已存在，略過")
            return

    # 確保欄位順序與工作表一致
    cols = ws.row_values(1)
    df = df.reindex(columns=cols).fillna("")
    ws.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    print(f"  ✅ {ws.title}: 寫入 {len(df)} 筆")


def overwrite(ws, df):
    """完全覆寫工作表內容（保留表頭）。"""
    cols = ws.row_values(1)
    df = df.reindex(columns=cols).fillna("")
    ws.clear()
    ws.append_row(cols)
    if not df.empty:
        ws.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    print(f"  ✅ {ws.title}: 覆寫 {len(df)} 筆")


# ============================================================
# 資料抓取
# ============================================================
def fetch_json(url, name):
    """通用 JSON 抓取（含錯誤處理）。"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️ 抓取 {name} 失敗：{e}")
        return None


def fetch_daily_quotes():
    """抓上市 + 上櫃每日 K。"""
    rows = []

    # 上市
    twse = fetch_json(URLS["twse_daily"], "TWSE 日 K")
    if twse:
        for r in twse:
            rows.append({
                "日期": TODAY,
                "股號": r.get("Code", ""),
                "股名": r.get("Name", ""),
                "市場": "ETF" if str(r.get("Code", "")).startswith("0") else "上市",
                "開盤": r.get("OpeningPrice", ""),
                "最高": r.get("HighestPrice", ""),
                "最低": r.get("LowestPrice", ""),
                "收盤": r.get("ClosingPrice", ""),
                "漲跌": r.get("Change", ""),
                "成交量": r.get("TradeVolume", ""),
                "成交金額": r.get("TradeValue", ""),
                "成交筆數": r.get("Transaction", ""),
            })

    # 上櫃
    tpex = fetch_json(URLS["tpex_daily"], "TPEx 日 K")
    if tpex:
        for r in tpex:
            code = r.get("SecuritiesCompanyCode", "") or r.get("Code", "")
            rows.append({
                "日期": TODAY,
                "股號": code,
                "股名": r.get("CompanyName", "") or r.get("Name", ""),
                "市場": "ETF" if str(code).startswith("0") else "上櫃",
                "開盤": r.get("Open", "") or r.get("OpeningPrice", ""),
                "最高": r.get("High", "") or r.get("HighestPrice", ""),
                "最低": r.get("Low", "") or r.get("LowestPrice", ""),
                "收盤": r.get("Close", "") or r.get("ClosingPrice", ""),
                "漲跌": r.get("Change", ""),
                "成交量": r.get("TradingShares", "") or r.get("TradeVolume", ""),
                "成交金額": r.get("TransactionAmount", "") or r.get("TradeValue", ""),
                "成交筆數": r.get("TransactionNumber", "") or r.get("Transaction", ""),
            })

    return pd.DataFrame(rows)


def fetch_institutional():
    """抓三大法人買賣超（上市 + 上櫃）。"""
    rows = []

    # 上市
    twse = fetch_json(URLS["twse_t86"], "TWSE 三大法人")
    if twse:
        for r in twse:
            rows.append({
                "日期": TODAY,
                "股號": r.get("Code", ""),
                "外資買賣超": r.get("ForeignInvestorsBuyAndSellAmount", "")
                              or r.get("ForeignNetBuySell", "")
                              or "0",
                "投信買賣超": r.get("InvestmentTrustBuyAndSellAmount", "")
                              or r.get("TrustNetBuySell", "")
                              or "0",
                "自營商買賣超": r.get("DealerBuyAndSellAmount", "")
                                or r.get("DealerNetBuySell", "")
                                or "0",
                "三大法人合計": r.get("NetBuyAndSell", "")
                                or r.get("TotalNetBuySell", "")
                                or "0",
            })

    # 上櫃
    tpex = fetch_json(URLS["tpex_t86"], "TPEx 三大法人")
    if tpex:
        for r in tpex:
            rows.append({
                "日期": TODAY,
                "股號": r.get("SecuritiesCompanyCode", "") or r.get("Code", ""),
                "外資買賣超": r.get("ForeignInvestorsBuyAndSellAmount", "0"),
                "投信買賣超": r.get("InvestmentTrustBuyAndSellAmount", "0"),
                "自營商買賣超": r.get("DealerBuyAndSellAmount", "0"),
                "三大法人合計": r.get("NetBuyAndSell", "0"),
            })

    return pd.DataFrame(rows)


def fetch_market_index():
    """抓加權指數（單日）。"""
    data = fetch_json(URLS["market_idx"], "加權指數")
    if not data:
        return pd.DataFrame()

    # FMTQIK 回傳的是「市場成交資訊」歷史，找最近一筆
    df = pd.DataFrame(data)
    if df.empty:
        return df

    # 欄位：Date, TradeVolume, TradeValue, Transaction, TAIEX, Change
    df = df.tail(1).copy()
    df["日期"] = TODAY
    out = df[["日期"]].copy()
    out["加權指數"] = df.get("TAIEX", "")
    out["漲跌"] = df.get("Change", "")
    out["成交金額"] = df.get("TradeValue", "")
    out["成交量"] = df.get("TradeVolume", "")
    return out


def fetch_sector_index():
    """抓各類股指數。"""
    data = fetch_json(URLS["sector_idx"], "類股指數")
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    if df.empty:
        return df

    rows = []
    for _, r in df.iterrows():
        name = r.get("Name", "") or r.get("IndexName", "")
        if not name:
            continue
        rows.append({
            "日期": TODAY,
            "類股名稱": name,
            "收盤": r.get("ClosingIndex", "") or r.get("Index", ""),
            "漲跌": r.get("Change", ""),
            "漲跌幅%": r.get("ChangePercent", ""),
        })
    return pd.DataFrame(rows)


def fetch_warning_stocks():
    """抓注意股 / 處置股 / 警示股。"""
    rows = []
    data = fetch_json(URLS["warn_attn"], "注意股")
    if data:
        for r in data:
            rows.append({
                "日期": TODAY,
                "股號": r.get("Code", "") or r.get("SecuritiesCompanyCode", ""),
                "股名": r.get("Name", "") or r.get("CompanyName", ""),
                "類型": "注意股",
                "備註": str(r),
            })
    return pd.DataFrame(rows)


# ============================================================
# Sheet 表頭定義
# ============================================================
HEADERS_MAP = {
    "daily_quotes": ["日期", "股號", "股名", "市場", "開盤", "最高", "最低",
                     "收盤", "漲跌", "成交量", "成交金額", "成交筆數"],
    "institutional": ["日期", "股號", "外資買賣超", "投信買賣超",
                      "自營商買賣超", "三大法人合計"],
    "market_index": ["日期", "加權指數", "漲跌", "成交金額", "成交量"],
    "sector_index": ["日期", "類股名稱", "收盤", "漲跌", "漲跌幅%"],
    "warning_stocks": ["日期", "股號", "股名", "類型", "備註"],
}


# ============================================================
# 主流程
# ============================================================
def main():
    print(f"📅 開始執行：{TODAY}")
    ss = get_gsheet()

    # 1. 每日 K
    print("📊 抓取每日 K...")
    df = fetch_daily_quotes()
    ws = get_or_create_ws(ss, "daily_quotes", HEADERS_MAP["daily_quotes"])
    append_dedup(ws, df, key_cols=["日期", "股號"])

    # 2. 三大法人
    print("💰 抓取三大法人...")
    df = fetch_institutional()
    ws = get_or_create_ws(ss, "institutional", HEADERS_MAP["institutional"])
    append_dedup(ws, df, key_cols=["日期", "股號"])

    # 3. 大盤指數
    print("📈 抓取加權指數...")
    df = fetch_market_index()
    ws = get_or_create_ws(ss, "market_index", HEADERS_MAP["market_index"])
    append_dedup(ws, df, key_cols=["日期"])

    # 4. 類股指數
    print("🏭 抓取類股指數...")
    df = fetch_sector_index()
    ws = get_or_create_ws(ss, "sector_index", HEADERS_MAP["sector_index"])
    append_dedup(ws, df, key_cols=["日期", "類股名稱"])

    # 5. 警示股（覆寫）
    print("⚠️ 抓取注意股 / 處置股...")
    df = fetch_warning_stocks()
    ws = get_or_create_ws(ss, "warning_stocks", HEADERS_MAP["warning_stocks"])
    overwrite(ws, df)

    print("✅ 全部完成")


if __name__ == "__main__":
    main()
