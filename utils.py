#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PTT Monitor utilities.
"""

import random
import time
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

TAIPEI_TZ = timezone(timedelta(hours=8))


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
