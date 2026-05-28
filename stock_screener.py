"""
隔日沖選股儀表板（v2 - Google Sheet 版）
========================================
資料流：
    GitHub Actions -> TWSE/TPEx API -> Google Sheet -> 本程式（讀 Sheet）

本程式不直接呼叫 API，每次開頁瞬間載入。
歷史資料逐日累積，量比 / 連漲天數 / 突破前高等指標自動算出。

作者：3ZeBra
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from data_loader import (
    build_latest_snapshot,
    load_market_index,
    load_sector_index,
)
from filters import (
    score_candidates, apply_traps,
    quick_near_limit_up, quick_locked_limit_up,
    is_market_strong_day, is_market_above_ma5,
    top_sectors, cond_in_top_sectors,
)


# ============================================================
# 頁面設定
# ============================================================
st.set_page_config(
    page_title="隔日沖選股儀表板",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 隔日沖選股儀表板")
st.caption(f"頁面載入時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ============================================================
# 載入資料
# ============================================================
with st.spinner("📊 從 Google Sheet 載入資料..."):
    df, latest_date = build_latest_snapshot()
    market_df = load_market_index()
    sector_df = load_sector_index()

if df.empty:
    st.error("❌ 沒有資料。請確認 Google Sheet 已建立且 Secrets 已設定。")
    st.info("""
    **可能原因：**
    - Streamlit Secrets 未設定 SHEET_ID 或 SHEET_GIDS
    - Google Sheet 尚未公開（需要「知道連結的所有人皆可檢視」）
    - GitHub Actions 還沒跑過第一次（明天 15:30 後再來看）
    """)
    st.stop()

st.success(f"📅 最新資料日期：**{latest_date.strftime('%Y-%m-%d')}**　全市場 {len(df):,} 檔")


# ============================================================
# Sidebar - 篩選條件
# ============================================================
st.sidebar.header("⚙️ 篩選條件")

# ===== 一鍵快速篩 =====
st.sidebar.subheader("🔥 一鍵快速篩選")

if "quick_mode" not in st.session_state:
    st.session_state.quick_mode = None

col_q1, col_q2 = st.sidebar.columns(2)
if col_q1.button("🔥 接近漲停", use_container_width=True):
    st.session_state.quick_mode = "near"
if col_q2.button("🔒 鎖死漲停", use_container_width=True):
    st.session_state.quick_mode = "locked"
if st.sidebar.button("↩️ 重設為自訂", use_container_width=True):
    st.session_state.quick_mode = None

st.sidebar.markdown("---")

# ===== 必要條件 =====
with st.sidebar.expander("📌 必要條件", expanded=True):
    min_rise_pct = st.slider("最小漲幅 (%)", 1.0, 10.0, 5.0, 0.5)
    min_volume = st.number_input("最小成交量（張）", 100, 100000, 1000, 100)
    min_turnover = st.number_input("最小成交金額（萬）", 1000, 100000, 5000, 1000)
    min_price = st.number_input("最低股價", 1, 1000, 10)
    max_price = st.number_input("最高股價", 10, 5000, 500)

# ===== 加分條件 =====
with st.sidebar.expander("✨ 加分條件", expanded=False):
    st.caption("加分條件每項計 0.5 分，必要條件每項 1 分")
    min_capital_yi = st.number_input("最小股本（億）", 1, 1000, 5)
    max_capital_yi = st.number_input("最大股本（億）", 5, 5000, 50)
    min_vol_ratio = st.number_input("量比 ≥", 0.0, 10.0, 1.5, 0.1,
                                     help="當日量 vs 5 日均量。需歷史資料")
    min_foreign_lots = st.number_input("外資買超 ≥（張）", 0, 100000, 500, 100)
    min_trust_lots = st.number_input("投信買超 ≥（張）", 0, 100000, 200, 100)

# ===== 地雷排除 =====
with st.sidebar.expander("🚫 地雷排除", expanded=True):
    trap_long_shadow = st.checkbox("上影線過長（>50%）", value=False,
                                    help="上影線 / 全日振幅 > 50%，高檔有賣壓")
    trap_n_rising = st.checkbox("連漲 ≥ 3 天", value=False,
                                 help="連漲過久，反轉風險高（需歷史）")
    trap_n_limit_up = st.checkbox("連續漲停 ≥ 3 天", value=False,
                                   help="N 連板高位風險（需歷史）")
    trap_warning = st.checkbox("注意股 / 處置股", value=True,
                                help="有交易限制")

# ===== 大盤判斷 =====
with st.sidebar.expander("📈 大盤條件", expanded=False):
    market_strong_only = st.checkbox("僅大盤紅 K 時推薦", value=False)
    market_above_ma5 = st.checkbox("大盤須 > 5 日線", value=False,
                                    help="需歷史資料")

# ===== 類股輪動 =====
with st.sidebar.expander("🏭 類股輪動", expanded=False):
    use_top_sectors = st.checkbox("僅限當日強勢類股", value=False)
    top_n_sectors = st.slider("取前 N 名類股", 1, 10, 3) if use_top_sectors else 3

# ===== 市場 =====
st.sidebar.markdown("---")
market_filter = st.sidebar.multiselect(
    "市場", options=["上市", "上櫃", "ETF"],
    default=["上市", "上櫃"],
    help="ETF 隔日沖通常波動不夠，預設不勾"
)

# ===== 最低總分 =====
min_score = st.sidebar.slider("最低總分", 0.0, 7.5, 4.0, 0.5,
                                help="5 項必要 + 5 項加分 × 0.5 = 滿分 7.5")

st.sidebar.caption("📡 資料來源：TWSE + TPEx OpenAPI（每日盤後排程）")


# ============================================================
# 一鍵模式顯示
# ============================================================
quick_mode = st.session_state.get("quick_mode")
quick_label = None
if quick_mode == "near":
    quick_label = "🔥 接近漲停模式"
elif quick_mode == "locked":
    quick_label = "🔒 鎖死漲停模式"


# ============================================================
# 大盤狀態
# ============================================================
strong_day = is_market_strong_day(market_df)
above_ma5 = is_market_above_ma5(market_df)

cols = st.columns(4)
if strong_day is True:
    cols[0].success("📈 大盤紅 K")
elif strong_day is False:
    cols[0].error("📉 大盤黑 K")
else:
    cols[0].info("📊 大盤資料無")

if above_ma5 is True:
    cols[1].success("📈 大盤 > MA5")
elif above_ma5 is False:
    cols[1].warning("⚠️ 大盤 < MA5")
else:
    cols[1].info("MA5 資料不足")

# 大盤條件不符時提醒
block_for_market = False
if market_strong_only and strong_day is False:
    cols[2].error("🚫 大盤黑 K，建議空手")
    block_for_market = True
if market_above_ma5 and above_ma5 is False:
    cols[3].error("🚫 跌破 MA5，建議空手")
    block_for_market = True


# ============================================================
# 篩選執行
# ============================================================
# 市場過濾
df = df[df["市場"].isin(market_filter)].copy()

# 類股輪動過濾
if use_top_sectors and sector_df is not None and not sector_df.empty:
    sectors = top_sectors(sector_df, latest_date, top_n_sectors)
    if sectors:
        st.info(f"🏭 今日強勢類股 TOP {top_n_sectors}：{'、'.join(sectors)}")
        df = df[cond_in_top_sectors(df, sector_df, latest_date, top_n_sectors)]

# 一鍵模式
if quick_mode == "near":
    mask = quick_near_limit_up(df)
    candidates = df[mask].copy()
    candidates["score"] = 5.0
elif quick_mode == "locked":
    mask = quick_locked_limit_up(df)
    candidates = df[mask].copy()
    candidates["score"] = 5.0
else:
    params = {
        "min_rise_pct": min_rise_pct,
        "min_volume": min_volume,
        "min_turnover": min_turnover,
        "min_price": min_price,
        "max_price": max_price,
        "min_capital_yi": min_capital_yi,
        "max_capital_yi": max_capital_yi,
        "min_vol_ratio": min_vol_ratio,
        "min_foreign_lots": min_foreign_lots,
        "min_trust_lots": min_trust_lots,
    }
    scored = score_candidates(df, params)
    candidates = scored[scored["score"] >= min_score].copy()

# 地雷排除
trap_flags = {
    "long_upper_shadow": trap_long_shadow,
    "n_days_rising": trap_n_rising,
    "n_days_limit_up": trap_n_limit_up,
    "warning": trap_warning,
}
before_traps = len(candidates)
candidates = apply_traps(candidates, trap_flags)
removed = before_traps - len(candidates)


# ============================================================
# 主要顯示
# ============================================================
if quick_label:
    st.markdown(f"### {quick_label}")

# 統計
c1, c2, c3, c4 = st.columns(4)
c1.metric("📊 全市場", f"{len(df):,}")
c2.metric("🎯 通過漲幅", f"{(df['漲幅%'] >= min_rise_pct).sum():,}")
c3.metric("🚫 地雷排除", f"{removed:,}")
c4.metric("✅ 最終候選", f"{len(candidates):,}")

st.markdown("---")

# 大盤封鎖警告
if block_for_market:
    st.error("🚫 大盤條件不符，**建議今日空手**，以下清單僅供參考")

# 候選清單
st.subheader("🎯 候選清單")
if len(candidates) == 0:
    st.warning("⚠️ 今日無符合條件的標的，可放寬條件再試")
else:
    candidates = candidates.sort_values(
        by=["score", "漲幅%", "成交金額"],
        ascending=[False, False, False]
    )

    display_cols = ["股號", "股名", "市場", "收盤", "漲幅%",
                    "成交量", "成交金額", "score"]
    # 動態加入有的欄位
    for opt in ["產業別", "股本(億)", "量比", "連漲", "連板",
                "外資買賣超", "投信買賣超", "上影線比例", "突破前高", "注意股"]:
        if opt in candidates.columns:
            display_cols.append(opt)

    display_df = candidates[display_cols].copy()

    # 格式化
    if "成交量" in display_df:
        display_df["成交量"] = (display_df["成交量"] / 1000).round(0).astype("Int64").astype(str) + " 張"
    if "成交金額" in display_df:
        display_df["成交金額"] = (display_df["成交金額"] / 10000).round(0).astype("Int64").astype(str) + " 萬"
    if "外資買賣超" in display_df:
        display_df["外資買賣超"] = (display_df["外資買賣超"] / 1000).round(0).astype("Int64").astype(str) + " 張"
    if "投信買賣超" in display_df:
        display_df["投信買賣超"] = (display_df["投信買賣超"] / 1000).round(0).astype("Int64").astype(str) + " 張"

    display_df = display_df.rename(columns={"score": "總分"})

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
        file_name=f"候選清單_{latest_date.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

# ============================================================
# 操作建議
# ============================================================
st.markdown("---")
st.subheader("💡 操作 SOP")
st.markdown("""
1. **盤後 15:30 後**：GitHub Actions 已自動抓資料，本頁直接看候選清單
2. **15:40-22:00**：人工複核 — 看 K 線型態、看新聞、看法人籌碼
3. **隔日盤前 08:30 前**：用大戶投 App 設智慧單
   - **觸價買單**：開盤跌破 -1% 就放棄
   - **母子單**：成交後自動掛賣
   - **移動停利**：高點回檔 2% 出場
4. **隔日 09:00-09:30**：黃金出場窗口
5. **隔日 10:00 前**：一定要出場（過了慣性消失）

**風險紀律：**
- 單筆部位 ≤ 總資金 **20%**
- 停損 **-2% 到 -3%** 嚴守
- 停利目標 **+3% 到 +5%**
- 連虧 3 次強制休息一週
""")

st.markdown("---")
st.caption("⚠️ 本工具僅供研究參考，投資有風險，請自行評估後操作")
