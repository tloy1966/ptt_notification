#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTT Monitor Script
監控 PTT 指定看板的文章，並在發現包含關鍵字的文章時發送 Discord 通知。
"""

import os
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

TAIPEI_TZ = timezone(timedelta(hours=8))


def load_processed_ids(filename='processed_ids.txt'):
    """讀取已處理過的文章 ID（含時間戳）"""
    if not os.path.exists(filename):
        return {}

    with open(filename, 'r', encoding='utf-8') as f:
        processed = {}
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '|' in line:
                article_id, ts = line.split('|', 1)
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=TAIPEI_TZ)
                except ValueError:
                    dt = None
            else:
                article_id = line
                dt = None
            processed[article_id] = dt
        return processed


def save_processed_ids(processed_ids, filename='processed_ids.txt'):
    """儲存已處理過的文章 ID（含時間戳）"""
    with open(filename, 'w', encoding='utf-8') as f:
        for article_id in sorted(processed_ids):
            dt = processed_ids.get(article_id)
            if dt:
                f.write(f"{article_id}|{dt.isoformat()}\n")
            else:
                f.write(f"{article_id}\n")


def get_user_agent():
    """取得隨機的 User-Agent 字串以避免被封鎖"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    return random.choice(user_agents)


def fetch_ptt_page_with_retry(url, max_retries=3, session=None):
    """
    使用重試機制取得 PTT 頁面
    包含指數退避策略和隨機 User-Agent
    """
    cookies = {'over18': '1'}
    
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': get_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
            }
            
            # 增加延遲以避免被封鎖
            if attempt > 0:
                delay = (2 ** attempt) + random.uniform(0, 1)
                print(f"  重試 {attempt + 1}/{max_retries}，等待 {delay:.1f} 秒...")
                time.sleep(delay)
            else:
                # 第一次請求也加入小延遲，模擬真實瀏覽器行為
                time.sleep(random.uniform(0.5, 1.5))
            
            client = session or requests
            response = client.get(url, cookies=cookies, headers=headers, timeout=15)
            response.raise_for_status()
            return response
            
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                print(f"錯誤：無法取得 PTT 頁面（嘗試 {max_retries} 次後失敗）：{e}")
                return None
            else:
                print(f"  警告：第 {attempt + 1} 次嘗試失敗：{e}")
    
    return None


def get_ptt_articles(board, cutoff=None, session=None):
    """
    爬取 PTT 指定看板的文章
    
    Args:
        board: 看板名稱
        cutoff: 截止時間（datetime），提供後會一路往前爬到早於 cutoff 為止
    
    Returns:
        文章列表
    
    Note:
        PTT 分頁邏輯：
        - 最新頁面：index.html
        - 上一頁按鈕指向：index{N}.html（例如 index4000.html）
        - 再上一頁：index{N-1}.html（例如 index3999.html）
    """
    articles = []
    current_url = f'https://www.ptt.cc/bbs/{board}/index.html'
    current_index_num = None
    page_num = 0

    while True:
        if page_num > 0:
            print(f"正在爬取第 {page_num + 1} 頁...")

        response = fetch_ptt_page_with_retry(current_url, session=session)
        if not response:
            print(f"警告：無法取得第 {page_num + 1} 頁，停止爬取")
            break

        soup = BeautifulSoup(response.text, 'html.parser')

        # 解析文章
        page_articles = []
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
                article = {
                    'id': article_id,
                    'title': title,
                    'url': f'https://www.ptt.cc{href}'
                }
                if cutoff is not None:
                    article['datetime'] = fetch_article_datetime(article['url'], session=session)
                page_articles.append(article)

        articles.extend(page_articles)

        if cutoff is None:
            break

        parsed_dates = [a.get('datetime') for a in page_articles if a.get('datetime')]
        if not parsed_dates:
            print("警告：此頁面無法解析任何文章時間，停止爬取")
            break
        if max(parsed_dates) < cutoff:
            break

        # 取得下一頁（更舊）
        if current_index_num is None:
            # 只參考 index.html 的上一頁連結
            prev_link = soup.find('a', string='‹ 上頁')
            if prev_link and prev_link.get('href'):
                href = prev_link['href']
                # href 形式: /bbs/{board}/index{N}.html
                try:
                    filename = href.split('/')[-1]
                    index_part = filename.replace('index', '').replace('.html', '')
                    current_index_num = int(index_part)
                except (ValueError, AttributeError):
                    current_index_num = None
            else:
                print("警告：找不到上一頁連結，停止爬取")
                break

            if current_index_num is None:
                print("警告：無法解析上一頁頁碼，停止爬取")
                break

            current_url = f"https://www.ptt.cc{href}"
        else:
            # 已取得 index{N}.html，往更舊頁面遞減
            current_index_num -= 1
            if current_index_num < 0:
                print("警告：頁碼已小於 0，停止爬取")
                break
            current_url = f"https://www.ptt.cc/bbs/{board}/index{current_index_num}.html"

        page_num += 1

    return articles


def fetch_article_datetime(article_url, session=None):
    """
    取得文章頁面的發文時間（datetime, naive in local time）
    PTT 文章通常在 header 內有一行 "時間  Mon Feb  3 12:34:56 2026"
    """
    response = fetch_ptt_page_with_retry(article_url, max_retries=2, session=session)
    if not response:
        print(f"警告：無法取得文章頁面：{article_url}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # PTT header meta: <span class="article-meta-tag">時間</span>
    meta_tags = soup.select('span.article-meta-tag')
    meta_values = soup.select('span.article-meta-value')
    for tag, val in zip(meta_tags, meta_values):
        if tag.get_text(strip=True) == '時間':
            time_str = val.get_text(strip=True)
            # Example: "Mon Feb  3 12:34:56 2026"
            try:
                return datetime.strptime(time_str, '%a %b %d %H:%M:%S %Y').replace(tzinfo=TAIPEI_TZ)
            except ValueError:
                # Sometimes day can be space-padded; %d handles 01-31, but PTT often uses two spaces.
                # datetime.strptime still works with %d for space-padded day on most platforms,
                # but keep a fallback just in case.
                try:
                    return datetime.strptime(time_str, '%a %b %e %H:%M:%S %Y').replace(tzinfo=TAIPEI_TZ)  # may not work on all OS
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
    session = requests.Session()
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

    now_tz = datetime.now(TAIPEI_TZ)
    cutoff = now_tz - timedelta(days=days)
    print(f"監控看板：{board}")
    print(f"關鍵字：{', '.join(keywords)}")
    print(f"時間範圍：今天往回 {days} 天（>= {cutoff}）")
    print("-" * 50)

    processed_ids = load_processed_ids()
    print(f"已載入 {len(processed_ids)} 個已處理的文章 ID")

    articles = get_ptt_articles(board, cutoff=cutoff, session=session)
    print(f"取得 {len(articles)} 篇文章")

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
        post_dt = article.get('datetime') or fetch_article_datetime(article['url'], session=session)
        if post_dt is None:
            # If can't parse time, skip (or choose to process anyway)
            processed_ids[article_id] = now_tz
            continue

        if post_dt < cutoff:
            # too old; skip and mark processed to avoid refetching every run
            processed_ids[article_id] = post_dt
            continue

        matched = any(keyword.lower() in title.lower() for keyword in keywords)
        if matched:
            print(f"發現匹配文章：{title}")
            send_discord_notification(webhook_url, article)
            processed_ids[article_id] = post_dt
            new_matches += 1
        else:
            processed_ids[article_id] = post_dt

    if days > 0:
        processed_ids = {
            article_id: dt
            for article_id, dt in processed_ids.items()
            if dt is None or dt >= cutoff
        }

    save_processed_ids(processed_ids)
    print(f"已儲存 {len(processed_ids)} 個文章 ID")
    print(f"本次發現 {new_matches} 篇新匹配文章")


if __name__ == '__main__':
    main()
