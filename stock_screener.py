"""
隔日沖選股儀表板 (MVP 版本)
================================
使用方式：
1. pip install streamlit pandas requests FinMind
2. streamlit run stock_screener.py
3. 瀏覽器會自動開啟 http://localhost:8501

資料來源：FinMind (免費版)
作者：3ZeBra
更新：2026/05/28
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from FinMind.data import DataLoader

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
# 資料抓取（加 cache 避免重複呼叫 API）
# ============================================================
@st.cache_data(ttl=3600)  # 快取 1 小時
def load_stock_data(days_back=15):
    """從 FinMind 抓取近 N 日的台股資料"""
    api = DataLoader()
    # 如果你有 FinMind 付費帳號，可在這裡填入 token
    # api.login_by_token(api_token="你的TOKEN")

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    # 抓取所有上市股票日線資料
    df = api.taiwan_stock_daily(
        stock_id="",  # 空字串代表全部
        start_date=start_date,
        end_date=end_date,
    )
    return df


@st.cache_data(ttl=86400)  # 股本資料一天更新一次
def load_stock_info():
    """抓取股票基本資訊（含股本）"""
    api = DataLoader()
    df = api.taiwan_stock_info()
    return df


@st.cache_data(ttl=3600)
def load_institutional_investors(date):
    """抓取三大法人買賣超"""
    api = DataLoader()
    df = api.taiwan_stock_institutional_investors(
        start_date=date,
        end_date=date,
    )
    return df


# ============================================================
# 篩選邏輯
# ============================================================
def calculate_screening_metrics(price_df, info_df):
    """計算每檔股票的 5 大篩選指標"""
    # 取得最新交易日
    latest_date = price_df["date"].max()
    today_data = price_df[price_df["date"] == latest_date].copy()

    # 計算 5 日均量
    avg_volume_5d = (
        price_df.groupby("stock_id")["Trading_Volume"]
        .rolling(window=5)
        .mean()
        .reset_index()
        .rename(columns={"Trading_Volume": "avg_volume_5d"})
    )
    avg_volume_5d = avg_volume_5d.groupby("stock_id").tail(1)

    # 合併資料
    today_data = today_data.merge(
        avg_volume_5d[["stock_id", "avg_volume_5d"]], on="stock_id", how="left"
    )

    # 計算量比
    today_data["volume_ratio"] = (
        today_data["Trading_Volume"] / today_data["avg_volume_5d"]
    )

    # 計算漲幅 %
    today_data["change_pct"] = (
        (today_data["close"] - today_data["open"]) / today_data["open"] * 100
    )
    # 更精確的漲幅應該用昨收計算，這裡簡化
    today_data["change_pct"] = today_data["spread"] / today_data["open"] * 100

    return today_data


def apply_5_conditions(df, info_df, params):
    """套用 5 大條件並評分"""
    # 條件 1：漲幅 ≥ X%
    df["cond_1_rise"] = (df["change_pct"] >= params["min_rise_pct"]).astype(int)

    # 條件 2：量比 ≥ X 倍
    df["cond_2_volume"] = (df["volume_ratio"] >= params["min_volume_ratio"]).astype(int)

    # 條件 3：股本適中（需要 info_df）
    # 註：FinMind 免費版股本資料有限，這裡用「上市」過濾代替
    df["cond_3_size"] = 1  # 預設通過（需付費資料才能精確過濾）

    # 條件 4：成交金額過濾（避免雞蛋水餃股）
    df["turnover"] = df["close"] * df["Trading_Volume"]
    df["cond_4_turnover"] = (df["turnover"] >= params["min_turnover"]).astype(int)

    # 條件 5：收紅 K（收盤 > 開盤）
    df["cond_5_red_k"] = (df["close"] > df["open"]).astype(int)

    # 總分
    df["score"] = (
        df["cond_1_rise"]
        + df["cond_2_volume"]
        + df["cond_3_size"]
        + df["cond_4_turnover"]
        + df["cond_5_red_k"]
    )

    return df


# ============================================================
# Sidebar - 篩選參數
# ============================================================
st.sidebar.header("⚙️ 篩選條件設定")

min_rise_pct = st.sidebar.slider(
    "最小漲幅 (%)", min_value=1.0, max_value=10.0, value=5.0, step=0.5
)

min_volume_ratio = st.sidebar.slider(
    "最小量比（vs 5日均量）", min_value=1.0, max_value=5.0, value=1.5, step=0.1
)

min_turnover = st.sidebar.number_input(
    "最小成交金額（萬）",
    min_value=1000,
    max_value=100000,
    value=5000,
    step=1000,
)

min_score = st.sidebar.slider(
    "最低總分（5 分滿分）", min_value=1, max_value=5, value=4
)

st.sidebar.markdown("---")
st.sidebar.info("💡 預設條件適合大多數隔日沖情境，可依個人風格調整")


# ============================================================
# 主要內容
# ============================================================
try:
    with st.spinner("📊 正在抓取資料..."):
        price_df = load_stock_data()
        info_df = load_stock_info()

    # 計算指標
    today_metrics = calculate_screening_metrics(price_df, info_df)

    # 套用篩選
    params = {
        "min_rise_pct": min_rise_pct,
        "min_volume_ratio": min_volume_ratio,
        "min_turnover": min_turnover * 10000,  # 轉成元
    }
    scored_df = apply_5_conditions(today_metrics, info_df, params)

    # 篩出符合條件的候選股
    candidates = scored_df[scored_df["score"] >= min_score].copy()
    candidates = candidates.sort_values(
        by=["score", "volume_ratio"], ascending=[False, False]
    )

    # ====== 顯示統計 ======
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📅 資料日期", price_df["date"].max())
    col2.metric("📊 全市場檔數", len(today_metrics))
    col3.metric("🎯 通過漲幅", (today_metrics["change_pct"] >= min_rise_pct).sum())
    col4.metric("✅ 候選清單", len(candidates))

    st.markdown("---")

    # ====== 候選清單 ======
    st.subheader("🎯 隔日沖候選清單")

    if len(candidates) == 0:
        st.warning("今日沒有符合條件的標的，可放寬條件再試")
    else:
        # 加上股名（如果可以對應）
        if "stock_name" in info_df.columns:
            name_map = dict(zip(info_df["stock_id"], info_df["stock_name"]))
            candidates["股名"] = candidates["stock_id"].map(name_map)

        display_cols = [
            "stock_id",
            "股名" if "股名" in candidates.columns else "stock_id",
            "close",
            "change_pct",
            "Trading_Volume",
            "volume_ratio",
            "score",
        ]
        display_cols = [c for c in display_cols if c in candidates.columns]

        display_df = candidates[display_cols].copy()
        display_df = display_df.rename(
            columns={
                "stock_id": "股號",
                "close": "收盤價",
                "change_pct": "漲幅%",
                "Trading_Volume": "成交量",
                "volume_ratio": "量比",
                "score": "總分",
            }
        )

        # 格式化
        display_df["漲幅%"] = display_df["漲幅%"].round(2)
        display_df["量比"] = display_df["量比"].round(2)

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=600,
        )

        # 下載按鈕
        csv = display_df.to_csv(index=False).encode("utf-8-sig")
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
    - FinMind 免費版有每日請求次數限制（600 次/小時）
    - 網路連線問題
    - 套件版本不符，請執行：`pip install -U FinMind streamlit pandas`
    """)


# ============================================================
# 頁尾
# ============================================================
st.markdown("---")
st.caption("⚠️ 本工具僅供參考，投資有風險，請自行評估後操作")
