"""
每週抓公司基本資料程式
======================
由 GitHub Actions 每週日 02:00 (TPE) 自動執行。
抓取上市櫃公司基本資料（股本、產業別），覆寫到 Google Sheet 的 stock_info 工作表。

環境變數：
    GOOGLE_CREDENTIALS
    SHEET_ID
"""

import os
import json
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials


TPE = timezone(timedelta(hours=8))
TODAY = datetime.now(TPE).strftime("%Y-%m-%d")
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 60

URLS = {
    "twse_info": "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
    "tpex_info": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
}

GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

INFO_HEADERS = ["更新日期", "股號", "股名", "市場", "產業別", "實收資本額", "股本(億)"]


def get_gsheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    sheet_id = os.environ.get("SHEET_ID")
    if not creds_json or not sheet_id:
        sys.exit("❌ 缺少環境變數 GOOGLE_CREDENTIALS 或 SHEET_ID")
    creds = Credentials.from_service_account_info(json.loads(creds_json),
                                                   scopes=GSHEETS_SCOPES)
    return gspread.authorize(creds).open_by_key(sheet_id)


def fetch_json(url, name):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠️ 抓取 {name} 失敗：{e}")
        return None


def parse_capital(val):
    """將實收資本額字串轉成數字。"""
    if not val:
        return 0
    try:
        return int(str(val).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return 0


def fetch_company_info():
    """抓上市 + 上櫃公司基本資料。"""
    rows = []

    # 上市
    twse = fetch_json(URLS["twse_info"], "TWSE 公司基本資料")
    if twse:
        for r in twse:
            cap = parse_capital(r.get("實收資本額(元)", "") or r.get("PaidInCapital", ""))
            rows.append({
                "更新日期": TODAY,
                "股號": r.get("公司代號", "") or r.get("Code", ""),
                "股名": r.get("公司簡稱", "") or r.get("Name", ""),
                "市場": "上市",
                "產業別": r.get("產業別", "") or r.get("Industry", ""),
                "實收資本額": cap,
                "股本(億)": round(cap / 1e8, 2) if cap else 0,
            })

    # 上櫃
    tpex = fetch_json(URLS["tpex_info"], "TPEx 公司基本資料")
    if tpex:
        for r in tpex:
            cap = parse_capital(r.get("實收資本額(元)", "") or r.get("PaidInCapital", ""))
            rows.append({
                "更新日期": TODAY,
                "股號": r.get("公司代號", "") or r.get("SecuritiesCompanyCode", ""),
                "股名": r.get("公司簡稱", "") or r.get("CompanyName", ""),
                "市場": "上櫃",
                "產業別": r.get("產業別", "") or r.get("Industry", ""),
                "實收資本額": cap,
                "股本(億)": round(cap / 1e8, 2) if cap else 0,
            })

    return pd.DataFrame(rows)


def main():
    print(f"📅 開始抓取公司基本資料：{TODAY}")
    ss = get_gsheet()

    df = fetch_company_info()
    print(f"  共 {len(df)} 筆")

    try:
        ws = ss.worksheet("stock_info")
        first_row = ws.row_values(1)
        if first_row != INFO_HEADERS:
            ws.update(range_name="A1", values=[INFO_HEADERS])
            print("  ℹ️ stock_info: 表頭已寫入 A1")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet("stock_info", rows=3000, cols=len(INFO_HEADERS))
        ws.update(range_name="A1", values=[INFO_HEADERS])

    cols = ws.row_values(1) or INFO_HEADERS
    df = df.reindex(columns=cols).fillna("")
    ws.clear()
    ws.append_row(cols)
    if not df.empty:
        ws.append_rows(df.astype(str).values.tolist(), value_input_option="USER_ENTERED")
    print(f"  ✅ stock_info 覆寫 {len(df)} 筆")


if __name__ == "__main__":
    main()
