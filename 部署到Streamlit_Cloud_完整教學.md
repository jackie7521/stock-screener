# 🚀 部署到 Streamlit Cloud 完整教學

> 從 GitHub 上傳到網頁上線，全程約 30 分鐘
> 完全免費

---

## 📋 部署前準備清單

需要的檔案（我已經幫你產好了）：

```
你的資料夾/
├── stock_screener.py       ← 主程式
├── requirements.txt        ← 套件清單
├── .gitignore              ← 排除不上傳的檔案
├── README.md               ← GitHub 首頁
└── secrets.toml.example    ← Secrets 範例（這個會上傳）
```

⚠️ **注意**：`.streamlit/secrets.toml`（真實金鑰）**絕對不要上傳**，已被 `.gitignore` 排除。

---

## 🎯 Step 1：建立 GitHub Repository（5 分鐘）

### 1-1 登入 GitHub
打開 https://github.com 並登入

### 1-2 建立新 Repo
1. 右上角點 **「+」** → **「New repository」**
2. 填寫：
   - **Repository name**：`stock-screener`（或任何你想要的名字）
   - **Description**：`隔日沖選股儀表板`（可選）
   - **Public**（必選，Streamlit Cloud 免費版限定）
   - ❌ **不要**勾「Add a README file」（我們有自己的）
   - ❌ **不要**勾「Add .gitignore」（我們有自己的）
3. 點 **「Create repository」**

### 1-3 建好後你會看到一個空 repo 的指引頁

---

## 📤 Step 2：上傳檔案到 GitHub（10 分鐘）

### 方法 A：用網頁拖曳上傳（最簡單，推薦新手）

1. 在 repo 頁面點 **「uploading an existing file」** 連結
   （或直接訪問 `https://github.com/你的帳號/stock-screener/upload/main`）
2. 把這 5 個檔案**全部拖進去**：
   - `stock_screener.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
   - `secrets.toml.example`
3. 下方 **Commit changes** 區域：
   - 填 commit message：`Initial commit`
   - 點 **「Commit changes」**

✅ 完成上傳，refresh 頁面就能看到所有檔案了

### 方法 B：用 Git 指令（給之後想學的人）

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的帳號/stock-screener.git
git branch -M main
git push -u origin main
```

---

## ☁️ Step 3：註冊 Streamlit Cloud（5 分鐘）

### 3-1 註冊
1. 打開 https://share.streamlit.io
2. 點 **「Continue with GitHub」**
3. GitHub 會跳授權頁，點 **「Authorize streamlit」**

### 3-2 第一次使用會問你一些問題
- 用途：選 **「Personal project」**
- 工作角色：隨便填
- 點 **「Continue」**

---

## 🚢 Step 4：部署你的 App（5 分鐘）

### 4-1 建立新 App
1. 進入 Streamlit Cloud 後，點右上角 **「Create app」** 或 **「New app」**
2. 選 **「Deploy a public app from GitHub」**

### 4-2 填寫設定
| 欄位 | 填什麼 |
|---|---|
| **Repository** | `你的帳號/stock-screener` |
| **Branch** | `main` |
| **Main file path** | `stock_screener.py` |
| **App URL** | 自訂網址（例：`my-stock-app`） |

### 4-3 點 **「Deploy!」**

等 2–5 分鐘，Streamlit Cloud 會：
1. Clone 你的 repo
2. 自動讀 `requirements.txt` 裝套件
3. 執行 `stock_screener.py`
4. 給你一個網址，例如：
   ```
   https://my-stock-app.streamlit.app
   ```

✅ **完成！這個網址手機、平板都能打開**

---

## 🔐 Step 5（選用）：設定 Secrets

如果你之後升級 FinMind 付費版有 token，要這樣設定：

1. 在 Streamlit Cloud 找到你的 App
2. 右下角點 **「⋮」**（三個點）→ **「Settings」**
3. 左側選 **「Secrets」**
4. 貼上：
   ```toml
   FINMIND_TOKEN = "你的真實 token"
   ```
5. 點 **「Save」**

App 會自動 reboot，3 秒內套用新 secrets。

---

## 🔄 Step 6：之後怎麼更新程式？

### 方法 A：在 GitHub 網頁直接編輯
1. 點要改的檔案（例如 `stock_screener.py`）
2. 右上角點鉛筆圖示 ✏️
3. 改完底下點 **「Commit changes」**
4. **Streamlit Cloud 會自動偵測並重新部署**（約 1–2 分鐘）

### 方法 B：本機改完用 Git push
```bash
git add .
git commit -m "更新篩選邏輯"
git push
```

---

## 🚨 常見問題排雷

### Q1：部署失敗，顯示 `ModuleNotFoundError`
👉 檢查 `requirements.txt` 是否有上傳，套件名稱是否拼錯

### Q2：部署成功但網頁打不開，顯示 `Error running app`
👉 點右下角 **「Manage app」** 看 logs，通常是程式有錯誤

### Q3：FinMind 連線失敗
👉 FinMind 免費版有 600 次/小時限制，等一小時再試；或註冊免費 token 拿到更高額度

### Q4：可以改成 Private repo 嗎？
👉 Streamlit Cloud 免費版只支援 Public repo。要 Private 要升級（$20/月）
👉 替代方案：repo 設 Public，但**程式不要寫敏感資料**，金鑰全放 Secrets

### Q5：App 會不會被亂操？
👉 預設網址是公開的，但別人不知道網址就找不到
👉 若擔心，可在程式裡加密碼登入（用 `st.text_input(type="password")`）

### Q6：放著沒人用會不會自動關掉？
👉 會！**閒置 7 天**會自動進入睡眠
👉 重新打開網址會自動喚醒（等 30 秒），不影響資料

### Q7：可以排程每天自動跑嗎？
👉 Streamlit Cloud **本身不排程**，它只是「使用者打開時才跑」
👉 要排程要搭配 **GitHub Actions**（免費）或 **cron-job.org**（免費）
👉 這個進階版我可以幫你寫

---

## 🎁 加分技巧

### 技巧 1：自訂網址
部署時 App URL 可填好記的名字，例如：
- ❌ 隨機：`https://app-xj4k8.streamlit.app`
- ✅ 自訂：`https://3zebra-stock.streamlit.app`

### 技巧 2：加到手機桌面
在手機瀏覽器打開網址 → 「加到主畫面」 → **變成像 App 一樣的圖示**

### 技巧 3：分享給其他人
直接傳網址給朋友，他們不用註冊任何東西就能用

### 技巧 4：埋追蹤碼看使用情況
可以接 Google Analytics 看誰在用、用多久（進階）

---

## 📊 部署後的下一步

| 階段 | 動作 |
|---|---|
| 第 1 週 | 每天 15:30 打開網頁看候選清單 |
| 第 2 週 | 對比實際隔日漲跌，調整參數 |
| 第 1 個月 | 加入更多篩選條件（例如三大法人） |
| 第 2 個月 | 接 Line Notify 自動推播 |
| 第 3 個月 | 接 Shioaji 半自動下單 |

---

## ✅ 部署完成檢查表

完成後請依序確認：

- [ ] GitHub repo 建好且檔案都上傳
- [ ] `.streamlit/secrets.toml` **沒有**被上傳（檢查 repo 看不到）
- [ ] Streamlit Cloud 部署成功，網址可開啟
- [ ] 網頁能正常顯示候選清單
- [ ] sidebar 滑桿可調整參數
- [ ] CSV 下載按鈕能用
- [ ] 手機開網址也能正常顯示
- [ ] 網址加到手機桌面

---

**祝部署順利！** 🚀

有任何步驟卡住，把錯誤訊息截圖貼給我，幫你 debug。
