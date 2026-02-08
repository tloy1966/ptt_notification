# PTT Notification System - Quick Start Guide

## 快速設定步驟

### 1️⃣ 取得 Discord Webhook URL

1. 開啟你的 Discord 伺服器
2. 選擇要接收通知的頻道
3. 點擊頻道設定 ⚙️ > 整合 > Webhooks
4. 點擊「新增 Webhook」
5. 自訂 Webhook 名稱和頭像（選填）
6. 複製 Webhook URL

### 2️⃣ 設定 GitHub Secret

1. 前往你的 GitHub Repository
2. 點擊 `Settings` > `Secrets and variables` > `Actions`
3. 點擊 `New repository secret`
4. 名稱：`DISCORD_WEBHOOK`
5. 值：貼上你的 Discord Webhook URL
6. 點擊 `Add secret`

### 3️⃣ 修改監控設定

編輯 `.github/workflows/main.yml` 檔案：

```yaml
env:
  PTT_BOARD: 'Gossiping'          # 改成你要監控的看板
  PTT_KEYWORDS: '地震,颱風'        # 改成你要監控的關鍵字
  PTT_DAYS: '1'                   # 監控最近幾天的文章（預設 1 天）
  PTT_PAGES: '2'                  # 爬取幾頁（預設 1 頁，最多 5 頁）
  DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
```

### 4️⃣ 測試執行

1. 前往 GitHub Repository 的 `Actions` 頁籤
2. 選擇 `PTT Monitor` workflow
3. 點擊 `Run workflow` > `Run workflow`
4. 查看執行結果和 Discord 通知

## 📝 注意事項

- ⏰ Workflow 會每 20 分鐘自動執行一次
- 📂 `processed_ids.txt` 會自動更新並提交
- 🔄 不會重複通知相同的文章
- ⚡ 支援多個關鍵字（用逗號分隔）

## 🎯 常見問題

### Q: 如何更改檢查頻率？

編輯 `.github/workflows/main.yml` 中的 cron 設定：

```yaml
schedule:
  - cron: '*/20 * * * *'  # 每 20 分鐘
  # - cron: '0 * * * *'   # 每小時
  # - cron: '*/5 * * * *' # 每 5 分鐘
```

### Q: 如何監控多個看板？

目前每個 workflow 只能監控一個看板。若要監控多個看板，可以：
1. 複製 `main.yml` 為 `main2.yml`、`main3.yml`
2. 分別設定不同的看板

### Q: 關鍵字是否區分大小寫？

不區分。關鍵字比對時會自動轉換為小寫。

### Q: Discord 沒收到通知？

檢查：
1. ✅ Webhook URL 是否正確
2. ✅ GitHub Secret 是否已設定
3. ✅ 看板名稱是否正確
4. ✅ 最近是否有符合關鍵字的文章
5. ✅ 查看 Actions 執行記錄中的錯誤訊息

## 🔧 本地測試

```bash
# 安裝套件
pip install -r requirements.txt

# 設定環境變數
export PTT_BOARD="Gossiping"
export PTT_KEYWORDS="地震,颱風"
export PTT_DAYS="1"
export PTT_PAGES="2"
export DISCORD_WEBHOOK="your_webhook_url"

# 執行腳本
python ptt_monitor.py
```

## 🆕 v2.0 更新

### 改進功能

1. **增強連線穩定性**
   - ✅ 自動重試機制（最多 3 次）
   - ✅ 指數退避策略
   - ✅ 隨機 User-Agent 避免封鎖

2. **支援多頁爬取**
   - ✅ 新增 `PTT_PAGES` 環境變數
   - ✅ 自動處理 PTT 特殊的分頁邏輯
   - ✅ 每頁約 20 篇文章

3. **更友善的錯誤處理**
   - ✅ 詳細的錯誤訊息
   - ✅ 重試時顯示進度
   - ✅ 避免因暫時性錯誤而中斷
```

## 📚 更多資訊

請參閱 [README.md](README.md) 了解詳細說明。
