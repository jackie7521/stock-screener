# 部署完整教學（v2 - Google Sheet 版）

> 從零開始，照著做就能部署完成。預估時間 30-45 分鐘。

## 📋 你需要準備

- GitHub 帳號（免費）
- Google 帳號（免費）
- Streamlit Community Cloud 帳號（免費，用 GitHub 登入）

---

## Step 1：建立 Google Sheet（5 分鐘）

1. 開啟 [Google Sheets](https://sheets.google.com/)，**新增一個空白試算表**
2. 命名為「**股票資料**」（名稱隨意，自己記得就好）
3. **新增 6 張工作表**，名稱必須完全一樣（區分大小寫）：

   | 工作表名 | 用途 |
   |---|---|
   | `daily_quotes` | 每日 K |
   | `institutional` | 三大法人 |
   | `market_index` | 加權指數 |
   | `sector_index` | 類股指數 |
   | `stock_info` | 公司基本資料 |
   | `warning_stocks` | 注意股 |

   👉 不需要先填表頭，`fetch_daily.py` 第一次跑會自動建立。

4. **取得 Sheet ID**：看網址：
   ```
   https://docs.google.com/spreadsheets/d/【這串就是 Sheet ID】/edit
   ```
   複製起來，等等會用到。**這就是 `SHEET_ID`**。

5. **取得每張工作表的 gid**：點到每張工作表時，網址後面會有 `#gid=xxxx`，記下來：
   - daily_quotes → gid = ?
   - institutional → gid = ?
   - market_index → gid = ?
   - sector_index → gid = ?
   - stock_info → gid = ?
   - warning_stocks → gid = ?

6. **設為「知道連結的所有人皆可檢視」**
   - 右上「共用」→ 一般存取權改成「知道連結的使用者」→ 角色「檢視者」
   - 這樣 Streamlit 不用 auth 也能讀（資料都是公開股市資料，無隱私風險）

---

## Step 2：建立 Google Service Account（寫入權限，10 分鐘）

GitHub Actions 要把資料寫進 Google Sheet，需要服務帳號。

1. 開 [Google Cloud Console](https://console.cloud.google.com/)
2. **建立新專案**（左上專案選擇 → 新增專案）→ 名稱「stock-screener」
3. 啟用 API：
   - 左側選單「API 和服務」→「程式庫」
   - 搜尋「**Google Sheets API**」→ 啟用
   - 搜尋「**Google Drive API**」→ 啟用
4. 建立 Service Account：
   - 左側「IAM 與管理員」→「服務帳戶」
   - 點「+ 建立服務帳戶」→ 名稱「stock-bot」→ 建立
   - 角色不用選，直接「完成」
5. 建立金鑰：
   - 進入剛建立的 service account → 上方「金鑰」分頁
   - 「新增金鑰」→「建立新的金鑰」→ JSON → 下載
   - **這個 JSON 檔保管好，不要 commit 到 GitHub**
6. **複製 service account 的 email**（長得像 `stock-bot@xxx.iam.gserviceaccount.com`）
7. 回到 Google Sheet 的「共用」→ 把這個 email 加入 → 角色「**編輯者**」

---

## Step 3：Fork 本 Repo 到自己的 GitHub（1 分鐘）

1. 進 GitHub repo 頁面
2. 右上「Fork」→ Fork 到自己的帳號
3. 把 repo Clone 到本機（如果想本機跑），或直接在線上編輯

---

## Step 4：設定 GitHub Secrets（5 分鐘）

GitHub Actions 跑排程時要讀 Secrets。

1. 在自己 fork 的 repo 進「Settings」→「Secrets and variables」→「Actions」
2. 點「New repository secret」分別新增兩個：

   **Secret 1：`SHEET_ID`**
   - Name: `SHEET_ID`
   - Secret: 貼上 Step 1.4 那串 Sheet ID

   **Secret 2：`GOOGLE_CREDENTIALS`**
   - Name: `GOOGLE_CREDENTIALS`
   - Secret: 把 Step 2.5 下載的 JSON **整個檔案的內容**（含大括號）貼進去

---

## Step 5：手動觸發第一次抓資料（3 分鐘）

不用等到隔天 15:30，可以馬上觸發測試：

1. 進 repo 上方「Actions」分頁
2. 左側點「Daily Fetch (15:30 TPE)」
3. 右上「Run workflow」→ 綠色按鈕
4. 等 2-3 分鐘 → 點進剛跑的 run 看 log
5. 看到 `✅ daily_quotes: 寫入 X 筆` 之類就成功了
6. 回 Google Sheet 看，6 張表應該都有資料了

如果看到錯誤：
- `❌ 缺少環境變數` → Step 4 沒做完
- API 抓取失敗 → 可能是非交易日（週末/假日），改週一晚上再試
- 寫入失敗 → Service Account 沒加入 Sheet 共用清單（Step 2.7）

**同樣的方式也手動跑一次「Weekly Fetch」**，把 `stock_info` 也建好。

---

## Step 6：部署到 Streamlit Cloud（5 分鐘）

1. 進 https://share.streamlit.io/
2. 用 GitHub 登入
3. 「New app」→ 選擇 repo、branch（main）、主檔案填 `stock_screener.py`
4. **點開「Advanced settings」→ Secrets 區塊**，貼入：

   ```toml
   SHEET_ID = "你的 Sheet ID"

   [SHEET_GIDS]
   daily_quotes = "0"
   institutional = "111111111"
   market_index = "222222222"
   sector_index = "333333333"
   stock_info = "444444444"
   warning_stocks = "555555555"
   ```

   👉 把上面每個 gid 替換成 Step 1.5 記下來的對應值

5. 點「Deploy」→ 等 2-3 分鐘
6. 部署完成後可以從手機開網址，新增到主畫面 = 一鍵打開選股結果

---

## Step 7：驗證（2 分鐘）

開啟你的 Streamlit 網址，應該看到：

- ✅ 標題「🚀 隔日沖選股儀表板」
- ✅ 「📅 最新資料日期：YYYY-MM-DD　全市場 X,XXX 檔」
- ✅ 大盤狀態顯示（紅 K / 黑 K）
- ✅ 候選清單表格

如果顯示「❌ 沒有資料」：
- 檢查 Streamlit Cloud Secrets 是否設好
- 檢查 Google Sheet 是否「知道連結的人皆可檢視」
- 檢查 gid 是否填對

---

## 🎉 完成！日常使用流程

- **不需要手動做什麼**，每天 15:30 GitHub Actions 自動抓
- 盤後想看候選股 → 開網址 → 瞬間載入
- 想調整篩選 → sidebar 拉一拉
- 想下載清單 → 點 CSV 下載

---

## 🛠️ 常見問題

### Q1：GitHub Actions 沒跑？
- Actions 分頁看是否有顯示綠勾
- 免費版 repo 60 天無活動會自動停掉排程 → push 個小修改即可重啟

### Q2：上櫃股票沒出現？
- TPEx API 偶爾欄位變動，看 `fetch_daily.py` log 是否抓到上櫃資料
- 程式有寫 `try-except`，TPEx 失敗不影響上市

### Q3：量比 / 連漲 / 突破前高都空白？
- 第一次部署 → 沒有歷史資料 → 這些指標要累積後才會有值
- 累積 1 週後「連漲」會有值
- 累積 1 個月後「量比、突破前高」會穩定

### Q4：想加自己的條件？
- 改 `filters.py`（純函式）
- 改 `stock_screener.py` 的 sidebar UI
- 兩處改完就生效

### Q5：Streamlit Cloud 免費版會睡眠？
- 7 天無人開會休眠
- 你每天會開所以不會發生
- 醒來首次載入慢一點點，後續正常

---

## 🔐 安全提醒

- ✅ Google Sheet 只放公開股市資料，設為公開檢視 OK
- ✅ Service Account JSON 只在 GitHub Secrets，不要 commit
- ❌ 不要把 Service Account JSON 上傳到 repo（已在 `.gitignore`）
- ❌ 不要把任何含個資的東西放進 Google Sheet
