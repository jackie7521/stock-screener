# 🚀 隔日沖選股儀表板 v2

> 台股全市場隔日沖候選股篩選工具，**API → Google Sheet → Streamlit** 三層架構，
> 歷史資料逐日累積，量比 / 連漲 / 突破前高等指標自動算出。

## ✨ 功能特色

- 📊 **每日自動排程**：GitHub Actions 15:30 抓 TWSE/TPEx 全市場資料寫入 Google Sheet
- ⚡ **網頁瞬間載入**：Streamlit 從 Google Sheet 讀取，不再每次打 API
- 📈 **歷史累積**：自動算出量比、連漲天數、突破前高、5/10/20 日均線
- 🎯 **多層篩選**：必要條件 / 加分條件 / 地雷排除 / 大盤判斷 / 類股輪動
- 🔥 **一鍵快速篩**：接近漲停、鎖死漲停一鍵切換
- 🏷️ **三類市場**：上市 / 上櫃 / ETF 可獨立選擇
- 💼 **法人籌碼**：三大法人買賣超（單日）
- 📥 **下載 CSV**：候選清單可匯出
- 🌐 **手機可看**：部署到 Streamlit Community Cloud

## 🛠️ 技術架構

```
[每日 15:30]                       [使用者開頁時]
GitHub Actions 排程                  Streamlit 從 Sheet 讀
    ↓                                       ↓
fetch_daily.py 抓 API                 瞬間顯示候選清單
    ↓                                  (不打 API，不會被 ban)
寫入 Google Sheet
（保留歷史，能算量比、連漲）
```

- **前端**：Streamlit
- **資料源**：TWSE OpenAPI + TPEx OpenAPI（免註冊、免 token）
- **儲存**：Google Sheets
- **排程**：GitHub Actions（每日 15:30、每週日 02:00）
- **語言**：Python 3.11
- **部署**：Streamlit Community Cloud

## 📁 檔案說明

| 檔案 | 用途 |
|---|---|
| `stock_screener.py` | Streamlit 主程式（UI + 篩選邏輯入口） |
| `data_loader.py` | 從 Google Sheet 載入資料（含快取） |
| `filters.py` | 所有篩選條件純函式 |
| `fetch_daily.py` | 每日盤後抓資料（GitHub Actions 用） |
| `fetch_weekly.py` | 每週抓公司基本資料（股本、產業別） |
| `.github/workflows/daily.yml` | 每日 15:30 排程設定 |
| `.github/workflows/weekly.yml` | 每週日 02:00 排程設定 |
| `部署到Streamlit_Cloud_完整教學.md` | 從零開始的部署步驟 |

## 📋 篩選條件（共 5 層）

### 1️⃣ 必要條件（缺一不可，每項 1 分）
- 漲幅 ≥ 5%
- 成交量 ≥ 1000 張
- 成交金額 ≥ 5000 萬
- 收紅 K（收盤 > 開盤）
- 股價區間（10-500 元）

### 2️⃣ 加分條件（每項 0.5 分）
- 股本 5-50 億
- 量比 ≥ 1.5（需歷史）
- 突破 20 日前高（需歷史）
- 外資 / 投信買超

### 3️⃣ 地雷排除（可勾選）
- 上影線過長（> 50%）
- 連漲 ≥ 3 天（需歷史）
- 連續漲停 ≥ 3 天（需歷史）
- 注意股 / 處置股 / 警示股

### 4️⃣ 大盤條件
- 僅大盤紅 K 時推薦
- 大盤須 > 5 日線（需歷史）

### 5️⃣ 類股輪動
- 僅限當日漲幅前 N 名強勢類股

## ⏰ 排程時程

| 排程 | 時間 | 內容 |
|---|---|---|
| 每日 | 週一 ~ 週五 15:30 TPE | 抓日 K、法人、大盤、類股、警示股 |
| 每週 | 週日 02:00 TPE | 抓公司基本資料（股本、產業別） |

## 🚀 部署

詳見 [部署到Streamlit_Cloud_完整教學.md](部署到Streamlit_Cloud_完整教學.md)

簡要步驟：
1. Clone 本 repo 到自己的 GitHub
2. 建立 Google Sheet 與 Service Account
3. 設定 GitHub Secrets（`GOOGLE_CREDENTIALS`、`SHEET_ID`）
4. 在 Streamlit Cloud 部署，並設定 Secrets
5. 等 GitHub Actions 跑第一次後，網頁即可看到資料

## 💡 操作 SOP

- **15:00** 收盤
- **15:30** GitHub Actions 自動抓資料
- **15:40 ~ 22:00** 開網頁看候選 → 人工複核
- **隔日盤前 08:30 前** 設好智慧單
- **隔日 09:00-09:30** 黃金出場
- **隔日 10:00 前** 一定要出場

## ⚠️ 風險紀律

- 單筆部位 ≤ 總資金 **20%**
- 停損 **-2% 到 -3%** 嚴守
- 停利目標 **+3% 到 +5%**
- 連虧 3 次強制休息一週

## 📄 License

MIT

## ⚠️ 免責聲明

本工具僅供研究參考，不構成投資建議。投資有風險，請自行評估後操作。
