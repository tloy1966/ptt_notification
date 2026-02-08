# PTT Notification Configuration Example
# 這個檔案展示如何設定環境變數

# ===========================================
# 環境變數設定範例（本地測試用）
# ===========================================

# 要監控的 PTT 看板
export PTT_BOARD="Gossiping"

# 關鍵字列表（逗號分隔）
export PTT_KEYWORDS="地震,颱風,停電"

# Discord Webhook URL
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# ===========================================
# 使用方式
# ===========================================

# 1. 複製此檔案並修改為 .env 或直接在終端機執行：
#    source example_config.sh

# 2. 然後執行腳本：
#    python ptt_monitor.py

# ===========================================
# GitHub Actions 設定
# ===========================================

# 在 GitHub Actions 中，請在 .github/workflows/main.yml 中設定：
# 
# env:
#   PTT_BOARD: 'Gossiping'
#   PTT_KEYWORDS: '地震,颱風'
#   DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
#
# 並在 GitHub Repository Settings > Secrets 中設定：
# - DISCORD_WEBHOOK: 你的 Discord Webhook URL

# ===========================================
# 常用 PTT 看板
# ===========================================

# PTT_BOARD="Gossiping"    # 八卦板
# PTT_BOARD="Baseball"     # 棒球板
# PTT_BOARD="Stock"        # 股票板
# PTT_BOARD="Tech_Job"     # 科技業板
# PTT_BOARD="Soft_Job"     # 軟體工作板
# PTT_BOARD="NBA"          # NBA 板
# PTT_BOARD="LOL"          # 英雄聯盟板
