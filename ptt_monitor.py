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
from datetime import datetime, timezone, timedelta


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
    """
    url = f'https://www.ptt.cc/bbs/{board}/index.html'

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

    for entry in soup.find_all('div', class_='r-ent'):
        title_tag = entry.find('div', class_='title')
        if not title_tag:
            continue

        link_tag = title_tag.find('a')
        if not link_tag:
            continue

        title = link_tag.text.strip()
        href = link_tag.get('href', '')

        article_id = href.split('/')[-1].replace('.html', '') if href else ''

        if article_id:
            articles.append({
                'id': article_id,
                'title': title,
                'url': f'https://www.ptt.cc{href}'
            })

    return articles


def fetch_article_datetime(article_url):
    """
    取得文章頁面的發文時間（datetime, naive in local time）
    PTT 文章通常在 header 內有一行 "時間  Mon Feb  3 12:34:56 2026"
    """
    cookies = {'over18': '1'}
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        r = requests.get(article_url, cookies=cookies, headers=headers, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"警告：無法取得文章頁面：{article_url} ({e})")
        return None

    soup = BeautifulSoup(r.text, 'html.parser')

    # PTT header meta: <span class="article-meta-tag">時間</span>
    meta_tags = soup.select('span.article-meta-tag')
    meta_values = soup.select('span.article-meta-value')
    for tag, val in zip(meta_tags, meta_values):
        if tag.get_text(strip=True) == '時間':
            time_str = val.get_text(strip=True)
            # Example: "Mon Feb  3 12:34:56 2026"
            try:
                return datetime.strptime(time_str, '%a %b %d %H:%M:%S %Y')
            except ValueError:
                # Sometimes day can be space-padded; %d handles 01-31, but PTT often uses two spaces.
                # datetime.strptime still works with %d for space-padded day on most platforms,
                # but keep a fallback just in case.
                try:
                    return datetime.strptime(time_str, '%a %b %e %H:%M:%S %Y')  # may not work on all OS
                except Exception:
                    print(f"警告：無法解析時間字串：{time_str} ({article_url})")
                    return None

    print(f"警告：找不到文章時間欄位：{article_url}")
    return None


def send_discord_notification(webhook_url, article):
    """發送 Discord 通知"""
    payload = {
        'embeds': [{
            'title': article['title'],
            'url': article['url'],
            'color': 5814783,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'footer': {'text': 'PTT 關鍵字通知'}
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
    board = os.environ.get('PTT_BOARD')
    keywords_str = os.environ.get('PTT_KEYWORDS')
    webhook_url = os.environ.get('DISCORD_WEBHOOK')

    days_str = os.environ.get('PTT_DAYS', '1')
    try:
        days = int(days_str)
    except ValueError:
        print(f"錯誤：PTT_DAYS 必須是整數，目前是：{days_str}")
        sys.exit(1)
    if days < 0:
        print("錯誤：PTT_DAYS 不能小於 0")
        sys.exit(1)

    if not board:
        print("錯誤：未設定 PTT_BOARD 環境變數")
        sys.exit(1)
    if not keywords_str:
        print("錯誤：未設定 PTT_KEYWORDS 環境變數")
        sys.exit(1)
    if not webhook_url:
        print("錯誤：未設定 DISCORD_WEBHOOK 環境變數")
        sys.exit(1)

    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
    if not keywords:
        print("錯誤：PTT_KEYWORDS 沒有有效的關鍵字")
        sys.exit(1)

    cutoff = datetime.now() - timedelta(days=days)
    print(f"監控看板：{board}")
    print(f"關鍵字：{', '.join(keywords)}")
    print(f"時間範圍：今天往回 {days} 天（>= {cutoff}）")
    print("-" * 50)

    processed_ids = load_processed_ids()
    print(f"已載入 {len(processed_ids)} 個已處理的文章 ID")

    articles = get_ptt_articles(board)
    print(f"取得 {len(articles)} 篇文章（索引頁）")

    if not articles:
        print("警告：未取得任何文章")
        return

    new_matches = 0
    for article in articles:
        article_id = article['id']
        title = article['title']

        if article_id in processed_ids:
            continue

        # Filter by datetime (requires fetching article page)
        post_dt = fetch_article_datetime(article['url'])
        if post_dt is None:
            # If can't parse time, skip (or choose to process anyway)
            processed_ids.add(article_id)
            continue

        if post_dt < cutoff:
            # too old; skip and mark processed to avoid refetching every run
            processed_ids.add(article_id)
            continue

        matched = any(keyword.lower() in title.lower() for keyword in keywords)
        if matched:
            print(f"發現匹配文章：{title}")
            send_discord_notification(webhook_url, article)
            processed_ids.add(article_id)
            new_matches += 1
        else:
            processed_ids.add(article_id)

    save_processed_ids(processed_ids)
    print(f"已儲存 {len(processed_ids)} 個文章 ID")
    print(f"本次發現 {new_matches} 篇新匹配文章")


if __name__ == '__main__':
    main()
