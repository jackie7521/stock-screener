# 🚀 隔日沖選股儀表板

> 一個基於 Streamlit + FinMind 的台股隔日沖候選股票自動篩選工具

## ✨ 功能特色

- 📊 每日自動掃描全市場上市櫃股票
- 🎯 套用 5 大隔日沖篩選條件（漲幅、量比、成交金額、紅 K、股本）
- 📥 一鍵下載候選清單 CSV
- 🌐 部署到 Streamlit Cloud，手機隨時可看
- 💡 內建操作 SOP 提醒

## 🛠️ 技術架構

- **前端**：Streamlit
- **資料**：FinMind API（盤後資料）
- **語言**：Python 3.10+
- **部署**：Streamlit Community Cloud

## 📦 本機執行

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 執行
streamlit run stock_screener.py
```

瀏覽器會自動開啟 `http://localhost:8501`

## ☁️ 部署到 Streamlit Cloud

1. Fork 或 Clone 本 repo
2. 到 [share.streamlit.io](https://share.streamlit.io) 用 GitHub 帳號登入
3. New app → 選擇此 repo → 主檔案填 `stock_screener.py`
4. 點 Deploy，等 2–3 分鐘就上線

## 🔐 環境變數設定

如果有 FinMind 付費版 token，到 Streamlit Cloud 的 App Settings → Secrets 加入：

```toml
FINMIND_TOKEN = "你的token"
```

## 📋 5 大篩選條件

| 條件 | 預設值 | 說明 |
|---|---|---|
| 最小漲幅 | 5% | 當日漲幅門檻 |
| 最小量比 | 1.5 倍 | 當日量 vs 5 日均量 |
| 最小成交金額 | 5000 萬 | 避免雞蛋水餃股 |
| 收紅 K | 必須 | 收盤 > 開盤 |
| 總分 | 4/5 | 至少符合 4 項條件 |

## ⏰ 建議使用時段

- **15:30** 跑篩選（盤後資料齊備）
- **15:40** 設定隔日的智慧單
- **隔日 09:00–09:30** 黃金出場窗口

## ⚠️ 免責聲明

本工具僅供研究參考，不構成投資建議。投資有風險，請自行評估後操作。

## 📄 License

MIT
