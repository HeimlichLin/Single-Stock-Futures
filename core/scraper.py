import requests
import datetime
import re
import asyncio
import aiohttp
from .config import MONTH_CODES, NAME_MAPPING, CONCURRENCY_LIMIT

import math

# 全域變數
ALL_STOCKS = []

def get_tick_size(price):
    """取得價格對應的跳動單位 (Tick Size)"""
    if price < 10: return 0.01
    elif price < 50: return 0.05
    elif price < 100: return 0.1
    elif price < 500: return 0.5
    elif price < 1000: return 1
    else: return 5

def calculate_limits(prev_close):
    """計算漲停價與跌停價"""
    # 漲停: 昨收 * 1.10，無條件捨去至 Tick
    raw_up = prev_close * 1.10
    tick_up = get_tick_size(raw_up)
    # 處理邊界: 若 raw_up 剛好在轉折點 (例如 100)，tick 取決於它所在的區間
    # 這裡簡化邏輯: 直接用 raw_up 判斷 tick
    limit_up = math.floor(raw_up / tick_up) * tick_up
    
    # 跌停: 昨收 * 0.90，無條件進位至 Tick
    raw_down = prev_close * 0.90
    tick_down = get_tick_size(raw_down)
    limit_down = math.ceil(raw_down / tick_down) * tick_down
    
    return limit_up, limit_down

def fetch_ssf_list():
    """
    下載期交所清單，並提取股票代號 (StockCode)
    """
    url = "https://openapi.taifex.com.tw/v1/SSFLists"
    print(f"[系統] 下載清單中: {url}")
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        
        # 1. 先收集所有資料
        raw_items = []
        for item in data:
            c = item.get('Contract')   # 期貨代號 (Ex: CDF)
            n = item.get('StockName')  # 名稱 (Ex: 台積電)
            sc = item.get('StockCode') # 股票代號 (Ex: 2330)
            
            if c and n:
                s_code = sc if sc else "9999"
                raw_items.append({'Code': c, 'Name': n, 'StockCode': s_code})

        # 2. 依股票代號分組，處理「小型」期貨名稱
        # 邏輯：若同一檔股票有多個期貨，代碼排序較後的通常是小型期貨
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in raw_items:
            grouped[item['StockCode']].append(item)

        final_res = []
        for s_code, items in grouped.items():
            # 依期貨代號排序 (Ex: CDF < QFF)
            items.sort(key=lambda x: x['Code'])
            
            for i, item in enumerate(items):
                # 1. 優先使用對照表 (config.py)
                if item['Code'] in NAME_MAPPING:
                    item['Name'] = NAME_MAPPING[item['Code']]
                
                # 2. 自動判斷小型期貨
                # 條件A: 代碼以 'Q' 開頭 (期交所慣例: Q開頭多為小型)
                # 條件B: 同一檔股票有多個合約，且排序在後 (經驗法則: 標準型代碼 < 小型代碼)
                # 修正: 若只有一個合約，即使是 Q 開頭 (如 QOF 長興)，也不應視為小型，除非名稱已有 "小"
                elif not item['Name'].startswith("小"):
                    is_small = False
                    
                    # 只有在有多個合約時，才啟用 Q 開頭判斷
                    if len(items) > 1:
                        if item['Code'].startswith('Q') or i > 0:
                            is_small = True
                    
                    if is_small:
                        item['Name'] = f"小{item['Name']}"
                
                final_res.append(item)
        
        print(f"[系統] 下載成功，共 {len(final_res)} 檔")
        return final_res
    except Exception as e:
        print(f"[錯誤] {e}")
        # 發生錯誤時的回退資料 (僅作範例，避免程式崩潰)
        return []

def get_target_contracts():
    """計算當月與下月 (含排序用的 Key)"""
    now = datetime.datetime.now()
    first_day = datetime.date(now.year, now.month, 1)
    w = first_day.weekday()
    first_wed = 1 + (2 - w) if w <= 2 else 1 + (2 - w) + 7
    third_wed = first_wed + 14
    
    is_next = now.day > third_wed
    start_m = now.month + 1 if is_next else now.month
    start_y = now.year
    
    contracts = []
    for i in range(2):
        m = start_m + i
        y = start_y
        if m > 12: m-=12; y+=1
        
        s = f"{MONTH_CODES[m]}{str(y)[-1]}"
        
        # 產生 MonthKey (例如 202512, 202601) 用於排序
        month_key = y * 100 + m
        
        contracts.append({
            'suffix': s, 
            'label': f"{m}月", 
            'month_key': month_key
        })
    return contracts

async def fetch_yahoo_html(session, task):
    """非同步爬蟲 (含重試機制)"""
    symbol = task['symbol']
    url = f"https://tw.stock.yahoo.com/quote/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 404:
                    return None
                
                if response.status != 200:
                    # 若非 200 (如 429, 500, 503)，等待後重試
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1 + attempt)
                        continue
                    return None

                html = await response.text()
                
                # 嘗試抓取價格
                price = None
                m = re.search(r'itemprop="price" content="([0-9.]+)"', html)
                if m: price = float(m.group(1))
                else:
                    m2 = re.search(r'class="Fz\(32px\)[^>]*>([0-9,.]+)<', html)
                    if m2: price = float(m2.group(1).replace(',', ''))
                
                # 1. 抓取昨收價 (Previous Close) - 即使沒抓到現價也要抓昨收
                prev_close = None
                # 嘗試多種 Regex
                patterns = [
                    r'昨收</span>.*?<span[^>]*>([0-9,.]+)<',
                    r'>昨收<.*?<span[^>]*>([0-9,.]+)<',
                    r'昨收.*?<span[^>]*>([0-9,.]+)<'
                ]
                for p in patterns:
                    m_prev = re.search(p, html, re.DOTALL)
                    if m_prev:
                        try:
                            prev_close = float(m_prev.group(1).replace(',', ''))
                            break
                        except:
                            pass

                # 若沒抓到價格，且沒抓到昨收，才檢查是否查無資料
                if price is None and prev_close is None:
                    if "查無" in html or "沒有找到" in html:
                        return None

                # 若有昨收但無現價，視為尚未成交，使用昨收作為參考價
                if price is None and prev_close is not None:
                    price = prev_close

                if price is not None:
                    # 計算漲跌幅: (現價 - 昨收) / 昨收 * 100
                    change_percent = 0.0
                    is_limit_up = False
                    is_limit_down = False

                    if prev_close and prev_close > 0:
                        change_percent = round(((price - prev_close) / prev_close) * 100, 2)
                        
                        # 計算漲跌停
                        limit_up, limit_down = calculate_limits(prev_close)
                        
                        # 比較價格 (使用 epsilon 避免浮點數誤差)
                        if abs(price - limit_up) < 0.005:
                            is_limit_up = True
                        elif abs(price - limit_down) < 0.005:
                            is_limit_down = True

                    # 2. 抓取開盤價 (Open)
                    open_price = 0.0
                    # 尋找 "開盤" 關鍵字後的數字
                    # 結構通常是: <span ...>開盤</span><span ...>1,395</span>
                    m_open = re.search(r'>開盤</span>.*?<span[^>]*>([0-9,.]+)<', html)
                    
                    if m_open:
                        try:
                            open_price = float(m_open.group(1).replace(',', ''))
                        except:
                            pass

                    return {
                        "Symbol": symbol,
                        "Name": task['name'],
                        "Price": price,
                        "Open": open_price,
                        "PrevClose": prev_close if prev_close else 0, # 新增昨收欄位
                        "ChangePercent": change_percent,
                        "IsLimitUp": is_limit_up,
                        "IsLimitDown": is_limit_down,
                        "Url": url,
                        # 以下是用來排序的關鍵欄位
                        "StockCode": task['stock_code'],   # 排序 1: 2330
                        "FuturesCode": task['futures_code'], # 排序 2: CDF vs QFF
                        "MonthKey": task['month_key']      # 排序 3: 202512 vs 202601
                    }
                
                # 若沒抓到價格但頁面正常，可能是載入不完全，重試
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue

        except Exception as e:
            # 網路錯誤或 Timeout，重試
            if attempt < max_retries - 1:
                await asyncio.sleep(1 + attempt)
                continue
            # print(f"[Error] {symbol}: {e}") # Optional logging
            return None
    return None

async def run_all_tasks(excluded_list=None):
    global ALL_STOCKS
    if not ALL_STOCKS: ALL_STOCKS = fetch_ssf_list()
    
    if excluded_list is None:
        excluded_list = []
    
    contracts = get_target_contracts()
    tasks_info = []
    
    for stock in ALL_STOCKS:
        if stock['StockCode'] in excluded_list:
            continue

        for c in contracts:
            full_sym = f"W{stock['Code']}{c['suffix']}"
            display = f"{stock['Name']} {c['label']}"
            
            tasks_info.append({
                'symbol': full_sym,
                'name': display,
                'stock_code': stock['StockCode'],
                'futures_code': stock['Code'],
                'month_key': c['month_key']
            })

    connector = aiohttp.TCPConnector(limit=CONCURRENCY_LIMIT)
    async with aiohttp.ClientSession(connector=connector) as session:
        pending_tasks = [fetch_yahoo_html(session, t) for t in tasks_info]
        for coro in asyncio.as_completed(pending_tasks):
            result = await coro
            if result:
                yield result
