"""
資料載入模組
============
從公開 Google Sheet 以 CSV export 方式載入資料（不需 auth）。
被 stock_screener.py 用 @st.cache_data 快取。

設定方式（在 Streamlit Cloud Secrets 或 .streamlit/secrets.toml 設定）：
    SHEET_ID = "你的 Google Sheet ID"
    SHEET_GIDS = { daily_quotes = "0", institutional = "...", ... }
"""

import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


# ============================================================
# Google Sheet 設定（從 Secrets 讀取）
# ============================================================
def _get_sheet_id():
    """從 Streamlit Secrets 讀 Sheet ID。"""
    try:
        return st.secrets["SHEET_ID"]
    except (KeyError, FileNotFoundError):
        return None


def _get_sheet_gids():
    """從 Streamlit Secrets 讀各工作表 gid。"""
    try:
        return dict(st.secrets["SHEET_GIDS"])
    except (KeyError, FileNotFoundError):
        return {}


def _csv_url(sheet_id, gid):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


# ============================================================
# 通用載入函式
# ============================================================
def _load_sheet(name, dtype=None):
    """載入指定工作表為 DataFrame。"""
    sheet_id = _get_sheet_id()
    gids = _get_sheet_gids()
    if not sheet_id or name not in gids:
        st.warning(f"⚠️ Secrets 未設定 SHEET_ID 或 SHEET_GIDS.{name}")
        return pd.DataFrame()

    url = _csv_url(sheet_id, gids[name])
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        r.encoding = "utf-8"  # 強制用 UTF-8 解碼（Google Sheets CSV 一律是 UTF-8）
        df = pd.read_csv(io.StringIO(r.text), dtype=dtype)
        return df
    except Exception as e:
        st.error(f"❌ 載入 {name} 失敗：{e}")
        return pd.DataFrame()


# ============================================================
# 各資料表的載入器（含快取）
# ============================================================
@st.cache_data(ttl=3600)
def load_daily_quotes():
    """日 K 資料（含歷史）。"""
    df = _load_sheet("daily_quotes", dtype={"股號": str})
    if df.empty:
        return df

    # 防禦性檢查：必要欄位是否存在（避免表頭錯位）
    required = ["日期", "股號", "收盤", "開盤", "漲跌"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"❌ daily_quotes 缺少欄位 {missing}。請清空 Sheet 後重跑 Daily Fetch。")
        st.caption(f"目前 CSV 欄位：{list(df.columns)}")
        return pd.DataFrame()

    # 型別轉換
    num_cols = ["開盤", "最高", "最低", "收盤", "漲跌",
                "成交量", "成交金額", "成交筆數"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")

    # 衍生欄位
    df["昨收"] = df["收盤"] - df["漲跌"]
    df["漲幅%"] = (df["漲跌"] / df["昨收"] * 100).round(2)
    df["紅K"] = df["收盤"] > df["開盤"]

    # 上影線比例（用 float('nan') 避免 pd.NA 把 dtype 升級成 object）
    if "最高" in df.columns and "最低" in df.columns:
        rng = (df["最高"] - df["最低"]).replace(0, float("nan"))
        upper_shadow = df["最高"] - df[["開盤", "收盤"]].max(axis=1)
        df["上影線比例"] = (upper_shadow / rng).round(3)
    else:
        df["上影線比例"] = float("nan")

    df = df.dropna(subset=["收盤"])
    df = df[df["收盤"] > 0]

    return df


@st.cache_data(ttl=3600)
def load_institutional():
    """三大法人買賣超。"""
    df = _load_sheet("institutional", dtype={"股號": str})
    if df.empty:
        return df
    for c in ["外資買賣超", "投信買賣超", "自營商買賣超", "三大法人合計"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_market_index():
    """加權指數歷史。"""
    df = _load_sheet("market_index")
    if df.empty:
        return df
    for c in ["加權指數", "漲跌", "成交金額", "成交量"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.sort_values("日期")

    # 衍生
    df["昨收"] = df["加權指數"] - df["漲跌"]
    df["漲幅%"] = (df["漲跌"] / df["昨收"] * 100).round(2)
    df["MA5"] = df["加權指數"].rolling(5).mean()
    df["MA10"] = df["加權指數"].rolling(10).mean()
    df["MA20"] = df["加權指數"].rolling(20).mean()

    return df


@st.cache_data(ttl=3600)
def load_sector_index():
    """類股指數歷史。"""
    df = _load_sheet("sector_index")
    if df.empty:
        return df
    for c in ["收盤", "漲跌", "漲跌幅%"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    return df


@st.cache_data(ttl=3600 * 24)
def load_stock_info():
    """公司基本資料（股本、產業別），每日刷新一次。"""
    df = _load_sheet("stock_info", dtype={"股號": str})
    if df.empty:
        return df
    for c in ["實收資本額", "股本(億)"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=3600)
def load_warning_stocks():
    """注意股 / 處置股清單。"""
    df = _load_sheet("warning_stocks", dtype={"股號": str})
    return df


# ============================================================
# 組合資料：取最新交易日的全市場 + 衍生指標
# ============================================================
@st.cache_data(ttl=3600)
def build_latest_snapshot():
    """組合最新一日的完整快照（含歷史衍生欄位）。"""
    quotes = load_daily_quotes()
    info = load_stock_info()
    insti = load_institutional()
    warnings = load_warning_stocks()

    if quotes.empty:
        return pd.DataFrame(), None

    latest_date = quotes["日期"].max()
    today = quotes[quotes["日期"] == latest_date].copy()

    # 合併基本資料（股本、產業別）
    if not info.empty:
        today = today.merge(
            info[["股號", "產業別", "股本(億)"]],
            on="股號", how="left"
        )

    # 合併今日法人
    if not insti.empty:
        insti_today = insti[insti["日期"] == latest_date]
        today = today.merge(
            insti_today[["股號", "外資買賣超", "投信買賣超",
                         "自營商買賣超", "三大法人合計"]],
            on="股號", how="left"
        )

    # 標註警示股
    if not warnings.empty:
        warn_set = set(warnings["股號"].astype(str).unique())
        today["注意股"] = today["股號"].astype(str).isin(warn_set)
    else:
        today["注意股"] = False

    # ===== 歷史衍生 =====
    today = _add_historical_features(today, quotes, latest_date)

    return today, latest_date


def _add_historical_features(today, quotes, latest_date):
    """加上需要歷史的衍生欄位：量比、連漲天數、連板天數、突破前高。"""
    # 為了效率，只在每檔股票的歷史內計算
    quotes = quotes.sort_values(["股號", "日期"])
    grp = quotes.groupby("股號")

    # 5 日均量
    quotes["MA5_量"] = grp["成交量"].transform(lambda s: s.rolling(5).mean().shift(1))
    # 量比
    quotes["量比"] = (quotes["成交量"] / quotes["MA5_量"]).round(2)

    # 連漲天數（含今日）
    rising = quotes["收盤"] > quotes.groupby("股號")["收盤"].shift(1)
    quotes["連漲"] = rising.groupby(quotes["股號"]).cumsum() - \
                     rising.groupby(quotes["股號"]).cumsum().where(~rising).ffill().fillna(0)

    # 連板天數（漲幅 ≥ 9%）
    limit_up = quotes["漲幅%"] >= 9.0
    quotes["連板"] = limit_up.groupby(quotes["股號"]).cumsum() - \
                     limit_up.groupby(quotes["股號"]).cumsum().where(~limit_up).ffill().fillna(0)

    # 20 日最高（不含今日）
    quotes["20日最高"] = grp["最高"].transform(lambda s: s.rolling(20).max().shift(1))
    quotes["突破前高"] = quotes["收盤"] > quotes["20日最高"]

    # 取今日這一列
    latest = quotes[quotes["日期"] == latest_date][
        ["股號", "量比", "連漲", "連板", "20日最高", "突破前高"]
    ]

    today = today.merge(latest, on="股號", how="left")
    return today
