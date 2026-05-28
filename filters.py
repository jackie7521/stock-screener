"""
篩選邏輯模組
============
所有篩選條件抽成純函式。
吃 DataFrame + params，回傳「布林 Series（True 表示通過）」或評分。
"""

import pandas as pd
import numpy as np


# ============================================================
# 必要條件
# ============================================================
def cond_rise(df, min_pct):
    """漲幅 ≥ min_pct%。"""
    return df["漲幅%"] >= min_pct


def cond_volume(df, min_volume_lots):
    """成交量 ≥ min_volume_lots 張。"""
    return df["成交量"] >= min_volume_lots * 1000


def cond_turnover(df, min_turnover_wan):
    """成交金額 ≥ min_turnover_wan 萬。"""
    return df["成交金額"] >= min_turnover_wan * 10000


def cond_red_k(df):
    """收紅 K：收盤 > 開盤。"""
    return df["收盤"] > df["開盤"]


def cond_price_range(df, low, high):
    """股價區間。"""
    return (df["收盤"] >= low) & (df["收盤"] <= high)


# ============================================================
# 加分條件
# ============================================================
def cond_capital_range(df, low_yi, high_yi):
    """股本區間（億）。需要 stock_info 合併過。"""
    if "股本(億)" not in df.columns:
        return pd.Series(True, index=df.index)
    cap = df["股本(億)"].fillna(-1)
    return (cap >= low_yi) & (cap <= high_yi)


def cond_volume_ratio(df, min_ratio):
    """量比 ≥ min_ratio（當日量 / 5 日均量）。"""
    if "量比" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["量比"].fillna(0) >= min_ratio


def cond_break_high(df):
    """突破 20 日前高。"""
    if "突破前高" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["突破前高"].fillna(False)


def cond_foreign_buy(df, min_lots):
    """外資買超 ≥ min_lots 張（單日）。"""
    if "外資買賣超" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["外資買賣超"].fillna(0) >= min_lots * 1000


def cond_trust_buy(df, min_lots):
    """投信買超 ≥ min_lots 張（單日）。"""
    if "投信買賣超" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["投信買賣超"].fillna(0) >= min_lots * 1000


# ============================================================
# 一鍵快速篩選
# ============================================================
def quick_near_limit_up(df):
    """🔥 接近漲停：漲幅 ≥ 9% + 紅 K + 成交金額 ≥ 5000 萬。"""
    return (
        (df["漲幅%"] >= 9.0)
        & cond_red_k(df)
        & cond_turnover(df, 5000)
    )


def quick_locked_limit_up(df):
    """🔒 鎖死漲停：收盤 = 最高（沒打開過）+ 漲幅 ≥ 9.5%。"""
    # 簡化版（不精確算漲停價，避免最小升降單位問題）
    return (
        (df["漲幅%"] >= 9.5)
        & (df["收盤"] == df["最高"])
        & cond_turnover(df, 5000)
    )


# ============================================================
# 地雷排除（True 表示「踩到地雷」要排除）
# ============================================================
def trap_long_upper_shadow(df, threshold=0.5):
    """上影線過長（比例 > threshold）。"""
    if "上影線比例" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["上影線比例"].fillna(0) > threshold


def trap_n_days_rising(df, n=3):
    """連漲 ≥ n 天。"""
    if "連漲" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["連漲"].fillna(0) >= n


def trap_n_days_limit_up(df, n=3):
    """連續漲停 ≥ n 天。"""
    if "連板" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["連板"].fillna(0) >= n


def trap_warning_stock(df):
    """注意股 / 處置股 / 警示股。"""
    if "注意股" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["注意股"].fillna(False)


# ============================================================
# 大盤強勢日判斷
# ============================================================
def is_market_strong_day(market_df):
    """加權指數收紅 K（單日）。"""
    if market_df is None or market_df.empty:
        return None
    latest = market_df.sort_values("日期").iloc[-1]
    if pd.isna(latest.get("漲幅%")):
        return None
    return float(latest["漲跌"]) > 0


def is_market_above_ma5(market_df):
    """加權指數收盤 > 5 日均線。"""
    if market_df is None or market_df.empty:
        return None
    latest = market_df.sort_values("日期").iloc[-1]
    if pd.isna(latest.get("MA5")):
        return None
    return float(latest["加權指數"]) > float(latest["MA5"])


# ============================================================
# 產業類股輪動：取漲幅前 N 名類股
# ============================================================
def top_sectors(sector_df, latest_date, top_n=3):
    """取最新交易日漲幅前 N 名的類股名稱清單。"""
    if sector_df is None or sector_df.empty:
        return []
    today = sector_df[sector_df["日期"] == latest_date].copy()
    if today.empty:
        return []
    today = today.sort_values("漲跌幅%", ascending=False)
    return today.head(top_n)["類股名稱"].tolist()


def cond_in_top_sectors(df, sector_df, latest_date, top_n=3):
    """個股的產業別在當日漲幅前 N 名類股內。"""
    if "產業別" not in df.columns:
        return pd.Series(True, index=df.index)
    sectors = top_sectors(sector_df, latest_date, top_n)
    if not sectors:
        return pd.Series(True, index=df.index)
    return df["產業別"].astype(str).isin(sectors)


# ============================================================
# 綜合評分
# ============================================================
def score_candidates(df, params):
    """
    套用必要 / 加分條件並評分。
    回傳 df 加上各 cond 欄位 + 'score'。
    """
    # 必要條件
    df["c_rise"] = cond_rise(df, params["min_rise_pct"]).astype(int)
    df["c_volume"] = cond_volume(df, params["min_volume"]).astype(int)
    df["c_turnover"] = cond_turnover(df, params["min_turnover"]).astype(int)
    df["c_red_k"] = cond_red_k(df).astype(int)
    df["c_price"] = cond_price_range(df, params["min_price"], params["max_price"]).astype(int)

    # 加分條件（如資料齊備）
    df["c_capital"] = cond_capital_range(df, params["min_capital_yi"],
                                          params["max_capital_yi"]).astype(int)
    df["c_vol_ratio"] = cond_volume_ratio(df, params["min_vol_ratio"]).astype(int)
    df["c_break_high"] = cond_break_high(df).astype(int)
    df["c_foreign"] = cond_foreign_buy(df, params["min_foreign_lots"]).astype(int)
    df["c_trust"] = cond_trust_buy(df, params["min_trust_lots"]).astype(int)

    # 評分（必要條件權重 1，加分條件權重 0.5）
    base = (df["c_rise"] + df["c_volume"] + df["c_turnover"]
            + df["c_red_k"] + df["c_price"])
    bonus = 0.5 * (df["c_capital"] + df["c_vol_ratio"] + df["c_break_high"]
                   + df["c_foreign"] + df["c_trust"])
    df["score"] = (base + bonus).round(1)

    return df


def apply_traps(df, trap_flags):
    """套用地雷排除，回傳排除後的 DataFrame。"""
    if trap_flags.get("long_upper_shadow"):
        df = df[~trap_long_upper_shadow(df)]
    if trap_flags.get("n_days_rising"):
        df = df[~trap_n_days_rising(df, n=trap_flags.get("n_rising", 3))]
    if trap_flags.get("n_days_limit_up"):
        df = df[~trap_n_days_limit_up(df, n=trap_flags.get("n_limit_up", 3))]
    if trap_flags.get("warning"):
        df = df[~trap_warning_stock(df)]
    return df
