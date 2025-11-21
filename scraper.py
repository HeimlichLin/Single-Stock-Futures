import requests
import datetime
import re
import asyncio
import aiohttp
from config import MONTH_CODES, NAME_MAPPING, CONCURRENCY_LIMIT

# 全域變數
ALL_STOCKS = []

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
                elif not item['Name'].startswith("小"):
                    is_small = False
                    
                    if item['Code'].startswith('Q'):
                        is_small = True
                    elif len(items) > 1 and i > 0:
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
    """非同步爬蟲"""
    symbol = task['symbol']
    url = f"https://tw.stock.yahoo.com/quote/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status != 200: return None
            html = await response.text()
            
            price = None
            m = re.search(r'itemprop="price" content="([0-9.]+)"', html)
            if m: price = float(m.group(1))
            else:
                m2 = re.search(r'class="Fz\(32px\)[^>]*>([0-9,.]+)<', html)
                if m2: price = float(m2.group(1).replace(',', ''))
            
            if price is not None:
                return {
                    "Symbol": symbol,
                    "Name": task['name'],
                    "Price": price,
                    "Url": url,
                    # 以下是用來排序的關鍵欄位
                    "StockCode": task['stock_code'],   # 排序 1: 2330
                    "FuturesCode": task['futures_code'], # 排序 2: CDF vs QFF
                    "MonthKey": task['month_key']      # 排序 3: 202512 vs 202601
                }
            return None
    except:
        return None

async def run_all_tasks():
    global ALL_STOCKS
    if not ALL_STOCKS: ALL_STOCKS = fetch_ssf_list()
    
    contracts = get_target_contracts()
    tasks_info = []
    
    for stock in ALL_STOCKS:
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
