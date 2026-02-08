#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTT Monitor Script
監控 PTT 指定看板的文章，並在發現包含關鍵字的文章時發送 Discord 通知。
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def load_processed_ids(filename='processed_ids.txt'):
    """讀取已處理過的文章 ID"""
    if not os.path.exists(filename):
        return set()
    
    with open(filename, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip() and not line.strip().startswith('#'))


def save_processed_ids(processed_ids, filename='processed_ids.txt'):
    """儲存已處理過的文章 ID"""
    with open(filename, 'w', encoding='utf-8') as f:
        for article_id in sorted(processed_ids):
            f.write(f"{article_id}\n")


def get_ptt_articles(board):
    """
    爬取 PTT 指定看板的第一頁文章
    
    Args:
        board: 看板名稱（例如：Gossiping）
    
    Returns:
        List of dict: 包含文章資訊的列表
    """
    url = f'https://www.ptt.cc/bbs/{board}/index.html'
    
    # PTT 需要設定 cookie 才能查看某些看板（例如 Gossiping）
    cookies = {'over18': '1'}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, cookies=cookies, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"錯誤：無法取得 PTT 頁面：{e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # 找到所有文章列表項目
    for entry in soup.find_all('div', class_='r-ent'):
        title_tag = entry.find('div', class_='title')
        if not title_tag:
            continue
        
        link_tag = title_tag.find('a')
        if not link_tag:
            continue
        
        title = link_tag.text.strip()
        href = link_tag.get('href', '')
        
        # 從連結中提取文章 ID
        # 例如：/bbs/Gossiping/M.1234567890.A.123.html
        article_id = href.split('/')[-1].replace('.html', '') if href else ''
        
        if article_id:
            articles.append({
                'id': article_id,
                'title': title,
                'url': f'https://www.ptt.cc{href}'
            })
    
    return articles


def send_discord_notification(webhook_url, article):
    """
    發送 Discord 通知
    
    Args:
        webhook_url: Discord Webhook URL
        article: 文章資訊字典
    """
    payload = {
        'embeds': [{
            'title': article['title'],
            'url': article['url'],
            'color': 5814783,  # 藍綠色
            'timestamp': datetime.utcnow().isoformat(),
            'footer': {
                'text': 'PTT 關鍵字通知'
            }
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✓ 已發送通知：{article['title']}")
    except requests.RequestException as e:
        print(f"錯誤：無法發送 Discord 通知：{e}")


def main():
    """主程式"""
    # 讀取環境變數
    board = os.environ.get('PTT_BOARD')
    keywords_str = os.environ.get('PTT_KEYWORDS')
    webhook_url = os.environ.get('DISCORD_WEBHOOK')
    
    # 檢查必要環境變數
    if not board:
        print("錯誤：未設定 PTT_BOARD 環境變數")
        sys.exit(1)
    
    if not keywords_str:
        print("錯誤：未設定 PTT_KEYWORDS 環境變數")
        sys.exit(1)
    
    if not webhook_url:
        print("錯誤：未設定 DISCORD_WEBHOOK 環境變數")
        sys.exit(1)
    
    # 解析關鍵字
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    
    if not keywords:
        print("錯誤：PTT_KEYWORDS 沒有有效的關鍵字")
        sys.exit(1)
    
    print(f"監控看板：{board}")
    print(f"關鍵字：{', '.join(keywords)}")
    print("-" * 50)
    
    # 讀取已處理過的文章 ID
    processed_ids = load_processed_ids()
    print(f"已載入 {len(processed_ids)} 個已處理的文章 ID")
    
    # 爬取文章
    articles = get_ptt_articles(board)
    print(f"取得 {len(articles)} 篇文章")
    
    if not articles:
        print("警告：未取得任何文章")
        return
    
    # 檢查文章標題是否包含關鍵字
    new_matches = 0
    for article in articles:
        article_id = article['id']
        title = article['title']
        
        # 如果已經處理過，跳過
        if article_id in processed_ids:
            continue
        
        # 檢查是否包含任何關鍵字
        matched = False
        for keyword in keywords:
            if keyword.lower() in title.lower():
                matched = True
                break
        
        if matched:
            print(f"發現匹配文章：{title}")
            send_discord_notification(webhook_url, article)
            processed_ids.add(article_id)
            new_matches += 1
        else:
            # 即使不匹配也加入已處理列表，避免重複檢查
            processed_ids.add(article_id)
    
    # 儲存已處理的文章 ID
    save_processed_ids(processed_ids)
    print(f"已儲存 {len(processed_ids)} 個文章 ID")
    print(f"本次發現 {new_matches} 篇新匹配文章")


if __name__ == '__main__':
    main()
