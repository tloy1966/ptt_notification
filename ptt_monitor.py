#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTT Monitor Script
監控 PTT 指定看板的文章，並在發現包含關鍵字的文章時發送 Discord 通知。
"""

import os
import sys
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from utils import TAIPEI_TZ, fetch_article_datetime, fetch_ptt_page_with_retry


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

            date_tag = entry.find('div', class_='date')
            list_date = date_tag.get_text(strip=True) if date_tag else ''

            article_id = href.split('/')[-1].replace('.html', '') if href else ''

            if article_id:
                article = {
                    'id': article_id,
                    'title': title,
                    'url': f'https://www.ptt.cc{href}',
                    'list_date': list_date
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


def send_discord_notification(webhook_url, article):
    """發送 Discord 通知"""
    list_date = article.get('list_date') or '未知'
    title = article.get('title', '')
    url = article.get('url', '')
    content = f"{list_date} | {title} {url}".strip()
    payload = {
        'content': content
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

    articles = get_ptt_articles(board, cutoff=cutoff, session=session)
    print(f"取得 {len(articles)} 篇文章")

    if not articles:
        print("警告：未取得任何文章")
        return

    new_matches = 0
    for article in articles:
        article_id = article['id']
        title = article['title']

        # Filter by datetime (requires fetching article page)
        post_dt = article.get('datetime') or fetch_article_datetime(article['url'], session=session)
        if post_dt is None:
            # If can't parse time, skip (or choose to process anyway)
            continue

        if post_dt < cutoff:
            # too old; skip and mark processed to avoid refetching every run
            continue

        matched = any(keyword.lower() in title.lower() for keyword in keywords)
        if matched:
            print(f"發現匹配文章：{title}")
            send_discord_notification(webhook_url, article)
            new_matches += 1
    print(f"本次發現 {new_matches} 篇新匹配文章")


if __name__ == '__main__':
    main()
