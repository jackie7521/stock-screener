"""
隔日沖選股儀表板 (TWSE OpenAPI 版本)
====================================
使用方式：
1. pip install streamlit pandas requests
2. streamlit run stock_screener.py
3. 瀏覽器會自動開啟 http://localhost:8501

資料來源：證交所 (TWSE) + 櫃買中心 (TPEx) 官方 OpenAPI
特色：免註冊、免 token、不會 ban IP
作者：3ZeBra
更新：2026/05/28
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ============================================================
# 頁面設定
# ============================================================
st.set_page_config(
    page_title="隔日沖選股儀表板",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 隔日沖選股儀表板")
st.caption(f"資料更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ============================================================
# 資料抓取
# ============================================================
TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"


@st.cache_data(ttl=3600)
def fetch_twse_data():
    """抓取上市股票資料"""
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(TWSE_URL, headers=headers, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["市場"] = "上市"
    return df


@st.cache_data(ttl=3600)
def fetch_tpex_data():
    """抓取上櫃股票資料"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(TPEX_URL, headers=headers, timeout=30)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        df["市場"] = "上櫃"
        return df
    except Exception as e:
        st.warning(f"⚠️ 上櫃資料抓取失敗（不影響上市資料）：{e}")
        return pd.DataFrame()


def normalize_data(twse_df, tpex_df):
    """將兩個來源的資料統一格式"""
    # TWSE 欄位
    twse_cols = {
        "Code": "股號",
        "Name": "股名",
        "TradeVolume": "成交量",
        "TradeValue": "成交金額",
        "OpeningPrice": "開盤",
        "HighestPrice": "最高",
        "LowestPrice": "最低",
        "ClosingPrice": "收盤",
        "Change": "漲跌",
        "Transaction": "成交筆數",
    }

    twse = twse_df.rename(columns=twse_cols)[list(twse_cols.values()) + ["市場"]]

    # TPEx 欄位（櫃買中心格式不太一樣）
    if not tpex_df.empty:
        # 嘗試不同的可能欄位名稱
        tpex_col_map = {}
        for orig, new in [
            ("SecuritiesCompanyCode", "股號"),
            ("CompanyName", "股名"),
            ("TradingShares", "成交量"),
            ("TransactionAmount", "成交金額"),
            ("Open", "開盤"),
            ("High", "最高"),
            ("Low", "最低"),
            ("Close", "收盤"),
            ("Change", "漲跌"),
            ("TransactionNumber", "成交筆數"),
        ]:
            if orig in tpex_df.columns:
                tpex_col_map[orig] = new

        tpex = tpex_df.rename(columns=tpex_col_map)
        # 只保留有對應的欄位
        keep_cols = [c for c in twse.columns if c in tpex.columns]
        tpex = tpex[keep_cols]
        df = pd.concat([twse, tpex], ignore_index=True)
    else:
        df = twse

    # 轉換數值欄位
    numeric_cols = ["成交量", "成交金額", "開盤", "最高", "最低", "收盤", "漲跌", "成交筆數"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 計算漲幅 %
    # 漲跌 = 今收 - 昨收，所以 昨收 = 今收 - 漲跌
    df["昨收"] = df["收盤"] - df["漲跌"]
    df["漲幅%"] = (df["漲跌"] / df["昨收"] * 100).round(2)

    # 過濾無效資料
    df = df.dropna(subset=["收盤", "成交量", "漲幅%"])
    df = df[df["收盤"] > 0]

    return df


# ============================================================
# 篩選邏輯
# ============================================================
def apply_5_conditions(df, params):
    """套用 5 大條件並評分"""
    # 條件 1：漲幅 ≥ X%
    df["cond_1_rise"] = (df["漲幅%"] >= params["min_rise_pct"]).astype(int)

    # 條件 2：成交量 ≥ X 張（1 張 = 1000 股）
    df["cond_2_volume"] = (df["成交量"] >= params["min_volume"] * 1000).astype(int)

    # 條件 3：成交金額 ≥ X 元（避免雞蛋水餃股）
    df["cond_3_turnover"] = (df["成交金額"] >= params["min_turnover"] * 10000).astype(int)

    # 條件 4：收紅 K（收盤 > 開盤）
    df["cond_4_red_k"] = (df["收盤"] > df["開盤"]).astype(int)

    # 條件 5：股價在合理區間（避免太低或太高）
    df["cond_5_price"] = (
        (df["收盤"] >= params["min_price"]) & (df["收盤"] <= params["max_price"])
    ).astype(int)

    # 總分
    df["score"] = (
        df["cond_1_rise"]
        + df["cond_2_volume"]
        + df["cond_3_turnover"]
        + df["cond_4_red_k"]
        + df["cond_5_price"]
    )

    return df


# ============================================================
# Sidebar - 篩選參數
# ============================================================
st.sidebar.header("⚙️ 篩選條件設定")

min_rise_pct = st.sidebar.slider(
    "最小漲幅 (%)", min_value=1.0, max_value=10.0, value=5.0, step=0.5
)

min_volume = st.sidebar.number_input(
    "最小成交量（張）",
    min_value=100,
    max_value=100000,
    value=1000,
    step=100,
)

min_turnover = st.sidebar.number_input(
    "最小成交金額（萬）",
    min_value=1000,
    max_value=100000,
    value=5000,
    step=1000,
)

min_price = st.sidebar.number_input("最低股價", min_value=1, max_value=1000, value=10)
max_price = st.sidebar.number_input("最高股價", min_value=10, max_value=5000, value=500)

min_score = st.sidebar.slider(
    "最低總分（5 分滿分）", min_value=1, max_value=5, value=4
)

market_filter = st.sidebar.multiselect(
    "市場", options=["上市", "上櫃"], default=["上市", "上櫃"]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 預設條件適合大多數隔日沖情境，可依個人風格調整")
st.sidebar.caption("📡 資料來源：證交所 + 櫃買中心官方 OpenAPI")


# ============================================================
# 主要內容
# ============================================================
try:
    with st.spinner("📊 正在從證交所抓取最新資料..."):
        twse_df = fetch_twse_data()
        tpex_df = fetch_tpex_data()
        df = normalize_data(twse_df, tpex_df)

    # 套用市場篩選
    df = df[df["市場"].isin(market_filter)]

    # 套用條件
    params = {
        "min_rise_pct": min_rise_pct,
        "min_volume": min_volume,
        "min_turnover": min_turnover,
        "min_price": min_price,
        "max_price": max_price,
    }
    scored_df = apply_5_conditions(df, params)

    # 篩出候選股
    candidates = scored_df[scored_df["score"] >= min_score].copy()
    candidates = candidates.sort_values(
        by=["score", "漲幅%", "成交金額"], ascending=[False, False, False]
    )

    # ====== 顯示統計 ======
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 全市場檔數", f"{len(df):,}")
    col2.metric("🎯 通過漲幅", f"{(df['漲幅%'] >= min_rise_pct).sum():,}")
    col3.metric("💰 通過成交金額", f"{(df['成交金額'] >= min_turnover * 10000).sum():,}")
    col4.metric("✅ 候選清單", f"{len(candidates):,}")

    st.markdown("---")

    # ====== 候選清單 ======
    st.subheader("🎯 隔日沖候選清單")

    if len(candidates) == 0:
        st.warning("⚠️ 今日沒有符合條件的標的，可放寬條件再試")
    else:
        display_cols = [
            "股號", "股名", "市場", "收盤", "漲幅%",
            "成交量", "成交金額", "score"
        ]
        display_df = candidates[display_cols].rename(columns={"score": "總分"})

        # 格式化顯示
        display_df["成交量"] = (display_df["成交量"] / 1000).round(0).astype(int).astype(str) + " 張"
        display_df["成交金額"] = (display_df["成交金額"] / 10000).round(0).astype(int).astype(str) + " 萬"

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=600,
        )

        # 下載按鈕
        csv = candidates.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下載候選清單 CSV",
            data=csv,
            file_name=f"候選清單_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    # ====== 操作建議 ======
    st.markdown("---")
    st.subheader("💡 操作建議")
    st.markdown("""
    1. **盤後 (15:30 後)**：執行篩選，挑出總分 4–5 分標的
    2. **隔日盤前**：上大戶投 App 設定智慧單
       - **觸價買單**：跌破當日收盤 -1% 就放棄
       - **母子單**：買進成交後自動掛賣
       - **移動停利**：高點回檔 2% 出場
    3. **隔日 09:00–09:30**：黃金出場窗口，過 10:00 就要警覺
    4. **單筆部位**：不超過總資金 20%，嚴守停損 2-3%
    """)

except Exception as e:
    st.error(f"❌ 資料載入失敗：{e}")
    st.info("""
    可能原因：
    - 證交所 API 暫時無法連線
    - 非交易日（週末或假日）資料未更新
    - 請稍後重試
    """)


# ============================================================
# 頁尾
# ============================================================
st.markdown("---")
st.caption("⚠️ 本工具僅供參考，投資有風險，請自行評估後操作")
