# PTT Notification System

自動監控 PTT 看板文章，當發現包含指定關鍵字的文章時，透過 Discord Webhook 發送通知。

## 功能特色

- 🔍 自動爬取 PTT 指定看板的文章
- 🔔 關鍵字匹配後發送 Discord 通知
- 🚫 防止重複通知（使用 `processed_ids.txt` 記錄已處理文章）
- ⏰ 每 20 分鐘自動執行（透過 GitHub Actions）
- 🛠️ 支援手動觸發執行

## 設定方式

### 1. 設定 Discord Webhook

1. 在 Discord 伺服器中建立一個頻道
2. 進入頻道設定 > 整合 > Webhooks
3. 建立新的 Webhook 並複製 Webhook URL

### 2. 設定 GitHub Secrets

在 GitHub Repository 中設定以下 Secret：

- `DISCORD_WEBHOOK`: Discord Webhook URL

路徑：Settings > Secrets and variables > Actions > New repository secret

### 3. 修改監控設定

編輯 `.github/workflows/main.yml` 檔案中的環境變數：

```yaml
env:
  PTT_BOARD: 'Gossiping'          # 要監控的看板名稱
  PTT_KEYWORDS: '地震,颱風'        # 關鍵字（逗號分隔）
  DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
```

## 環境變數說明

- `PTT_BOARD`: PTT 看板名稱（例如：Gossiping、Baseball、Stock）
- `PTT_KEYWORDS`: 關鍵字列表，使用逗號分隔（例如：地震,颱風,停電）
- `PTT_DAYS`: 監控文章的天數範圍（預設為 1 天，表示只看最近 1 天的文章）。會持續往前翻頁直到超過時間範圍為止
- `DISCORD_WEBHOOK`: Discord Webhook URL

## 本地測試

```bash
# 安裝相依套件
pip install -r requirements.txt

# 設定環境變數並執行
export PTT_BOARD="Gossiping"
export PTT_KEYWORDS="地震,颱風"
export PTT_DAYS="1"
export DISCORD_WEBHOOK="your_webhook_url"

python ptt_monitor.py
```

## 技術改進

### v2.0 更新內容

1. **改進連線穩定性**
   - 新增重試機制（最多 3 次）
   - 指數退避策略避免過度請求
   - 隨機 User-Agent 以避免被封鎖

2. **支援多頁爬取**
   - 依 `PTT_DAYS` 自動往前翻頁到時間範圍外停止
   - 自動處理 PTT 分頁邏輯（index.html → indexN.html → indexN-1.html）

3. **增加請求延遲**
   - 模擬真實瀏覽器行為
   - 降低被 PTT 伺服器封鎖的風險
```

## 工作流程

1. 腳本每 20 分鐘執行一次（或手動觸發）
2. 爬取指定 PTT 看板的第一頁文章
3. 檢查文章標題是否包含關鍵字
4. 發現匹配的新文章時發送 Discord 通知
5. 將文章 ID 記錄到 `processed_ids.txt` 避免重複通知
6. 自動 commit 並 push `processed_ids.txt` 的變更

## 技術架構

- **Python 3.11**: 主要程式語言
- **requests**: HTTP 請求處理
- **BeautifulSoup4**: HTML 解析
- **GitHub Actions**: 自動化執行平台

## 注意事項

- 某些看板（如 Gossiping）需要滿 18 歲驗證，腳本會自動處理
- 建議不要設定過多關鍵字，以免漏失通知
- `processed_ids.txt` 會自動更新並提交到 repository（包含時間戳，格式為 `文章ID|ISO時間`）

## License

MIT